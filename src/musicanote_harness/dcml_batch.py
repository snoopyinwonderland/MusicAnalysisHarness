"""Resumable, bounded DCML import validation across independent subcorpora."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .dcml_import import ADAPTER_VERSION, NON_BLOCKING_ALIGNMENT_DIAGNOSTICS


def blocking_measure_alignment_issues(report: dict[str, Any]) -> dict[str, list[str]]:
    """Return only measure diagnostics that invalidate timeline alignment.

    New reports expose this directly.  The fallback keeps older reports safe
    while allowing a printed-number-only mismatch to remain a warning.
    """
    if "measure_alignment_blocking_issues" in report:
        return report["measure_alignment_blocking_issues"]
    return {
        mc: [code for code in diagnostics if code not in NON_BLOCKING_ALIGNMENT_DIAGNOSTICS]
        for mc, diagnostics in report.get("measure_alignment_issues", {}).items()
        if any(code not in NON_BLOCKING_ALIGNMENT_DIAGNOSTICS for code in diagnostics)
    }


def _round_robin(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    for row in rows:
        groups[row["subcorpus"]].append(row)
    order = sorted(groups)
    result = []
    while any(groups.values()):
        for name in order:
            if groups[name]:
                result.append(groups[name].popleft())
    return result


def quality_reasons(report: dict[str, Any]) -> list[str]:
    """Reasons to quarantine a score-wide track; individual ambiguous spans stay excluded."""
    notes = report["note_alignment"]
    source_count = notes["source_note_rows"]
    ir_count = notes["ir_note_events"]
    matched = notes["matched_note_events"]
    annotations = report["imported_annotations"]
    mapped = report["exact_alignments"] + report["verified_transform_alignments"]
    reasons = []
    if blocking_measure_alignment_issues(report):
        reasons.append("measure_alignment_issues")
    if not source_count or not ir_count or not annotations:
        reasons.append("empty_required_table")
    else:
        if matched / source_count < 0.95 or matched / ir_count < 0.95:
            reasons.append("note_alignment_below_95pct")
        if mapped / annotations < 0.95:
            reasons.append("harmony_alignment_below_95pct")
    return reasons


def alignment_quality(report: dict[str, Any]) -> str:
    """Gate score-wide reuse; ambiguous individual spans remain excluded by the context builder."""
    if quality_reasons(report):
        return "quarantined"
    notes = report["note_alignment"]
    source_count = notes["source_note_rows"]
    ir_count = notes["ir_note_events"]
    matched = notes["matched_note_events"]
    annotations = report["imported_annotations"]
    mapped = report["exact_alignments"] + report["verified_transform_alignments"]
    if (matched == source_count == ir_count and mapped == annotations
            and report["source_note_mapping"]["complete"]):
        return "validated_complete"
    return "validated_partial"


def _source_hashes(paths: dict[str, str]) -> dict[str, str]:
    return {kind: hashlib.sha256(Path(path).read_bytes()).hexdigest() for kind, path in paths.items()}


def validate_dcml_pairs(pair_file: str | Path, output: str | Path, limit: int | None = None,
                        timeout_seconds: int = 90, workers: int = 1) -> dict[str, Any]:
    pair_file, output = Path(pair_file), Path(output)
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if not 1 <= workers <= 4:
        raise ValueError("workers must be between 1 and 4")
    output.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in pair_file.read_text(encoding="utf-8").splitlines() if line]
    eligible = _round_robin([row for row in rows if row["status"] == "complete_files_unaligned"])
    selected = eligible[:limit] if limit is not None else eligible
    def process_pair(row: dict[str, Any]) -> dict[str, Any]:
        pair_id = row["pair_id"]
        target = output / "pairs" / row["subcorpus"] / row["stem"]
        report_path = target / "preparation_report.json"
        if report_path.is_file():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                package_files = ("canonical_music_ir.json", "imported_annotations.jsonl",
                                 "alignment_records.jsonl", "source_harmony_context.json")
                if (report.get("source_paths") == row["paths"]
                        and report.get("adapter_version") == ADAPTER_VERSION
                        and report.get("source_sha256") == _source_hashes(row["paths"])
                        and all((target / name).is_file() for name in package_files)):
                    return {"pair_id": pair_id, "status": "reused_existing", "report_path": str(report_path)}
            except (OSError, json.JSONDecodeError, KeyError):
                pass
        cmd = [sys.executable, "-m", "musicanote_harness.cli", "prepare-dcml"]
        for key in ("score", "measures", "harmonies", "notes"):
            cmd.extend((f"--{key}", row["paths"][key]))
        cmd.extend(("--output", str(target)))
        began = time.monotonic()
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds, check=False)
            elapsed = round(time.monotonic() - began, 3)
            if completed.returncode == 0 and report_path.is_file():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                return {
                    "pair_id": pair_id, "status": "prepared", "seconds": elapsed,
                    "report_path": str(report_path),
                    "score_measures": report["score_measures"],
                    "annotations": report["imported_annotations"],
                    "exact": report["exact_alignments"],
                    "verified_transform": report["verified_transform_alignments"],
                    "ambiguous": report["ambiguous_alignments"],
                }
            else:
                status = "unsupported_repeat_timeline" if "unsupported_written_repeat_timeline" in completed.stderr else "failed"
                return {"pair_id": pair_id, "status": status, "seconds": elapsed,
                        "error_tail": completed.stderr[-1200:]}
        except subprocess.TimeoutExpired:
            return {"pair_id": pair_id, "status": "timeout", "seconds": timeout_seconds}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(process_pair, selected))
    status_counts = Counter(row["status"] for row in outcomes)
    tracks = []
    quality_by_subcorpus: dict[str, Counter[str]] = defaultdict(Counter)
    quarantine_reason_counts: Counter[str] = Counter()
    aggregate: Counter[str] = Counter()
    aggregate_by_quality: dict[str, Counter[str]] = defaultdict(Counter)
    for row in outcomes:
        if row["status"] not in {"prepared", "reused_existing"}:
            continue
        report_path = Path(row["report_path"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        quality = alignment_quality(report)
        reasons = quality_reasons(report)
        subcorpus = row["pair_id"].split(":", 2)[1]
        quality_by_subcorpus[subcorpus][quality] += 1
        quarantine_reason_counts.update(reasons)
        for key in ("score_measures", "imported_annotations", "exact_alignments",
                    "verified_transform_alignments", "ambiguous_alignments"):
            aggregate[key] += report[key]
            aggregate_by_quality[quality][key] += report[key]
        aggregate["source_note_rows"] += report["note_alignment"]["source_note_rows"]
        aggregate["matched_note_events"] += report["note_alignment"]["matched_note_events"]
        aggregate_by_quality[quality]["source_note_rows"] += report["note_alignment"]["source_note_rows"]
        aggregate_by_quality[quality]["matched_note_events"] += report["note_alignment"]["matched_note_events"]
        tracks.append({
            "pair_id": row["pair_id"],
            "score_id": report["score_id"],
            "ir_document_id": report["ir_document_id"],
            "annotation_track_id": report["annotation_track_id"],
            "source_sha256": report["source_sha256"],
            "report_path": str(report_path),
            "canonical_ir_path": str(report_path.parent / "canonical_music_ir.json"),
            "source_harmony_context_path": str(report_path.parent / "source_harmony_context.json"),
            "annotation_input_policy": "source_annotation_conditioned_only",
            "exact_alignments": report["exact_alignments"],
            "verified_transform_alignments": report["verified_transform_alignments"],
            "ambiguous_alignments": report["ambiguous_alignments"],
            "human_review_status": "unverified",
            "alignment_quality": quality,
            "quality_reasons": reasons,
            "alignment_eligible": quality != "quarantined",
        })
    (output / "prepared_tracks.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in tracks), encoding="utf-8"
    )
    summary = {
        "schema_name": "musicanote-dcml-batch-validation",
        "schema_version": "0.1.0",
        "pair_file": str(pair_file),
        "candidate_pairs": len(rows),
        "complete_candidate_pairs": len(eligible),
        "selected_pairs": len(selected),
        "workers": workers,
        "status_counts": dict(status_counts),
        "indexed_prepared_tracks": len(tracks),
        "alignment_quality_counts": dict(Counter(row["alignment_quality"] for row in tracks)),
        "alignment_eligible_tracks": sum(row["alignment_eligible"] for row in tracks),
        "alignment_quality_by_subcorpus": {
            name: dict(counts) for name, counts in sorted(quality_by_subcorpus.items())
        },
        "quarantine_reason_counts": dict(quarantine_reason_counts),
        "aggregate": dict(aggregate),
        "aggregate_by_quality": {
            name: dict(counts) for name, counts in sorted(aggregate_by_quality.items())
        },
        "outcomes": outcomes,
        "interpretation": "Importer validation only; no harmony-prediction accuracy or rights clearance implied",
    }
    (output / "batch_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
