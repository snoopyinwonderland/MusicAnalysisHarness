"""Conservative score-coordinate audit for RomanText harmony analyses.

This module does not treat a parseable analysis as gold.  It verifies whether
each RomanNumeral can be placed on a unique printed score measure and exact
rational local offset.  Semantic chord accuracy is deliberately out of scope.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

from music21 import converter, meter, roman, stream

from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter


VERSION = "romantext-score-alignment-audit-0.1.0"
SCORE_PREFERENCE = (".musicxml", ".mxl", ".mei", ".krn", ".mscx", ".mscz")


def _fraction(value: Any) -> Fraction:
    result = Fraction(value).limit_denominator(16384)
    if abs(float(result) - float(value)) > 1e-10:
        raise ValueError(f"unsupported_non_rational_time:{value}")
    return result


def _q(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def choose_score(path: Path, sibling_names: list[str]) -> Path | None:
    candidates = [path.parent / name for name in sibling_names if (path.parent / name).is_file()]
    by_suffix = {suffix: sorted(item for item in candidates if item.suffix.lower() == suffix)
                 for suffix in SCORE_PREFERENCE}
    for suffix in SCORE_PREFERENCE:
        if by_suffix[suffix]:
            return by_suffix[suffix][0]
    return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _line_by_measure(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line_number, text in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        stripped = text.lstrip()
        if not stripped.startswith("m"):
            continue
        token = stripped.split(maxsplit=1)[0][1:]
        # The parser can expand ranges/copies.  The beginning label remains a
        # useful source-line locator without pretending to identify a token.
        label = token.split("-", 1)[0]
        if label:
            result.setdefault(label, line_number)
    return result


def align_romantext(path: str | Path, score_path: str | Path,
                    include_events: bool = False) -> dict[str, Any]:
    path, score_path = Path(path), Path(score_path)
    # RomanText sibling scores are not DCML exports and can legitimately use
    # music21's own multi-staff part expansion.  Do not apply the DCML-specific
    # source-part remapping contract here.
    score = converter.parse(score_path)
    legacy = CanonicalIRBuilder().build(score, score_path)
    ir = FormalIRAdapter().convert(legacy, score_path)
    analysis = converter.parse(path, format="romanText")
    analysis_part = analysis.parts[0]
    line_by_measure = _line_by_measure(path)

    printed: dict[str, list[dict[str, Any]]] = {}
    for item in ir["measures"]:
        printed.setdefault(str(item["printed_measure_number"]), []).append(item)

    status_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    examples = []
    events = []
    event_count = 0
    for source_measure in analysis_part.getElementsByClass(stream.Measure):
        label = source_measure.measureNumberWithSuffix()
        candidates = printed.get(str(label), [])
        source_signature = source_measure.getContextByClass(meter.TimeSignature)
        for item in source_measure.recurse().getElementsByClass(roman.RomanNumeral):
            event_count += 1
            reasons = []
            target = None
            if len(candidates) != 1:
                reasons.append("printed_measure_not_unique_in_score" if candidates else "printed_measure_missing_in_score")
            else:
                target_measure = candidates[0]
                target_signature = target_measure["time_signature"]
                if source_signature is not None and (
                    source_signature.numerator != target_signature["beats"]
                    or source_signature.denominator != target_signature["beat_type"]
                ):
                    reasons.append("time_signature_mismatch")
                try:
                    local = _fraction(item.getOffsetInHierarchy(source_measure))
                    duration = _fraction(item.quarterLength)
                    actual = Fraction(
                        target_measure["actual_duration_quarter"]["numerator"],
                        target_measure["actual_duration_quarter"]["denominator"],
                    )
                    if local < 0 or duration < 0 or local >= actual or local + duration > actual:
                        reasons.append("event_outside_measure")
                    else:
                        start = Fraction(
                            target_measure["global_start_quarter"]["numerator"],
                            target_measure["global_start_quarter"]["denominator"],
                        ) + local
                        target = {"start_quarter": _q(start), "end_quarter": _q(start + duration)}
                except (TypeError, ValueError, ZeroDivisionError):
                    reasons.append("invalid_event_time")
            status = "exact_coordinate" if not reasons else "ambiguous"
            status_counts[status] += 1
            reason_counts.update(reasons)
            if len(examples) < 20 and (reasons or event_count <= 3):
                examples.append({
                    "measure": str(label),
                    "line": line_by_measure.get(str(label)),
                    "figure": item.figure,
                    "key": item.key.tonicPitchNameWithCase,
                    "target": target,
                    "status": status,
                    "diagnostics": reasons,
                })
            if include_events:
                try:
                    local_text = _q(_fraction(item.getOffsetInHierarchy(source_measure)))
                    duration_text = _q(_fraction(item.quarterLength))
                except (TypeError, ValueError, ZeroDivisionError):
                    local_text = ""
                    duration_text = ""
                events.append({
                    "event_index": event_count,
                    "measure": str(label),
                    "line": line_by_measure.get(str(label)),
                    "figure": item.figure,
                    "key": item.key.tonicPitchNameWithCase,
                    "local_onset_quarter": local_text,
                    "duration_quarter": duration_text,
                    "measure_id": candidates[0]["measure_id"] if len(candidates) == 1 else None,
                    "target": target,
                    "status": status,
                    "diagnostics": reasons,
                })

    result = {
        "alignment_version": VERSION,
        "analysis_path": str(path),
        "score_path": str(score_path),
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "score_measures": len(ir["measures"]),
        "roman_events": event_count,
        "status_counts": dict(status_counts),
        "diagnostic_counts": dict(reason_counts),
        "examples": examples,
        "interpretation": "Coordinate audit only; chord correctness, human-gold status, and rights clearance are not implied",
    }
    if include_events:
        result["events"] = events
        result["ir"] = ir
    return result


def _audit_source(source: dict[str, Any], cache_directory: str) -> dict[str, Any]:
    path = Path(source["path"])
    score_path = choose_score(path, source["sibling_score_files"])
    row = {
        "analysis_path": str(path),
        "corpus": source["corpus"],
        "automatic_filename": source["automatic_filename"],
        "analyst": source.get("headers", {}).get("Analyst", ""),
        "score_path": str(score_path) if score_path else None,
    }
    if score_path is None:
        row["status"] = "no_supported_score_candidate"
        return row
    analysis_sha256, score_sha256 = _sha256(path), _sha256(score_path)
    cache_path = Path(cache_directory) / f"{hashlib.sha1(str(path).encode('utf-8')).hexdigest()}.json"
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if (cached.get("alignment_version") == VERSION
                    and cached.get("analysis_sha256") == analysis_sha256
                    and cached.get("score_sha256") == score_sha256):
                cached["cache_reused"] = True
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    row.update({"alignment_version": VERSION, "analysis_sha256": analysis_sha256, "score_sha256": score_sha256})
    try:
        result = align_romantext(path, score_path)
        row.update(result)
        ambiguous = result["status_counts"].get("ambiguous", 0)
        row["status"] = "aligned_complete" if not ambiguous else "aligned_partial"
    except Exception as error:  # per-file process isolation; class is retained
        row["status"] = "parse_or_alignment_error"
        row["error"] = f"{type(error).__name__}: {error}"
    row["cache_reused"] = False
    cache_path.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    return row


def audit_romantext_alignments(records_path: str | Path, output: str | Path,
                               limit: int | None = None, corpus: str | None = None,
                               workers: int = 1) -> dict[str, Any]:
    records_path, output = Path(records_path), Path(output)
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if not 1 <= workers <= 4:
        raise ValueError("workers must be between 1 and 4")
    output.mkdir(parents=True, exist_ok=True)
    cache_directory = output / "pair_cache"
    cache_directory.mkdir(exist_ok=True)
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line]
    eligible = [
        row for row in records
        if row.get("status") == "shape_readable"
        and row.get("sibling_score_files")
        and (corpus is None or row.get("corpus") == corpus)
    ]
    selected = eligible[:limit] if limit is not None else eligible
    pair_status: Counter[str] = Counter()
    event_status: Counter[str] = Counter()
    diagnostics: Counter[str] = Counter()
    cache_reused = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        aligned_rows = pool.map(
            _audit_source,
            selected,
            [str(cache_directory)] * len(selected),
        )
    with (output / "romantext_alignment_records.jsonl").open("w", encoding="utf-8") as handle:
        for row in aligned_rows:
            if "status_counts" in row:
                event_status.update(row["status_counts"])
                diagnostics.update(row["diagnostic_counts"])
            cache_reused += bool(row.get("cache_reused"))
            pair_status[row["status"]] += 1
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "schema_name": "musicanote-romantext-score-alignment-audit",
        "schema_version": "0.1.0",
        "alignment_version": VERSION,
        "source_records": len(records),
        "eligible_records": len(eligible),
        "selected_records": len(selected),
        "corpus_filter": corpus,
        "workers": workers,
        "cache_reused": cache_reused,
        "pair_status_counts": dict(pair_status),
        "event_status_counts": dict(event_status),
        "diagnostic_counts": dict(diagnostics),
        "interpretation": "Coordinate audit only; no harmony-prediction accuracy, human-gold status, or rights clearance implied",
    }
    (output / "romantext_alignment_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
