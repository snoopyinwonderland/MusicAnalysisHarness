"""Resumable corpus audit of score evidence for aligned RomanText labels."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from typing import Any

from .romantext_context_evidence import VERSION as CONTEXT_EVIDENCE_VERSION
from .romantext_evidence import VERSION as EVIDENCE_VERSION
from .romantext_import import prepare_romantext


BATCH_VERSION = "romantext-source-evidence-batch-0.2.0"


def _category(row: dict[str, Any]) -> list[str]:
    if row["status"] != "scored":
        return list(row.get("diagnostics") or ["unscorable"])
    result = []
    if row.get("missing_expected_pitch_classes"):
        result.append("expected_tones_missing")
    if row.get("foreign_pitch_classes"):
        result.append("foreign_tones_possible_nct_or_mismatch")
    if row.get("bass_matches_notated_inversion") is False:
        result.append("start_bass_mismatch")
    if row.get("chord_tone_duration_ratio", 1) < 0.55:
        result.append("low_chord_tone_duration_ratio")
    return result or ["no_flag"]


def _audit_one(source: dict[str, Any]) -> dict[str, Any]:
    try:
        package = prepare_romantext(source["analysis_path"], source["score_path"])
        evidence = package["source_evidence"]
        context_evidence = package["context_evidence"]
        context_by_annotation = {row["annotation_id"]: row for row in context_evidence["records"]}
        annotations = {row["annotation_id"]: row for row in package["annotations"]}
        scored = [row for row in evidence["records"] if row["status"] == "scored"]
        categories = Counter(category for row in evidence["records"] for category in _category(row))
        candidates = []
        priority = {"weak_evidence": 0, "mixed_evidence": 1, "moderate_support": 2, "strong_support": 3, "unscorable": 4}
        for row in sorted(
            evidence["records"],
            key=lambda item: (priority[item["support_band"]], item.get("chord_tone_duration_ratio", 2)),
        ):
            if row["support_band"] not in {"weak_evidence", "mixed_evidence", "unscorable"}:
                continue
            annotation = annotations[row["annotation_id"]]
            context = context_by_annotation.get(row["annotation_id"], {})
            candidates.append(
                {
                    "annotation_id": row["annotation_id"],
                    "label": row["raw_label"],
                    "key": row["key_raw"],
                    "support_band": row["support_band"],
                    "measure": annotation["native_target"]["measure"],
                    "local_onset_quarter": annotation["native_target"]["local_onset_quarter"],
                    "source_line": annotation["source_locator"]["line"],
                    "expected_tone_presence_ratio": row.get("expected_tone_presence_ratio"),
                    "chord_tone_duration_ratio": row.get("chord_tone_duration_ratio"),
                    "bass_matches_notated_inversion": row.get("bass_matches_notated_inversion"),
                    "categories": _category(row),
                    "previous_label": context.get("previous_raw_label"),
                    "next_label": context.get("next_raw_label"),
                    "observed_bass_motion_semitones": context.get("observed_bass_motion_semitones"),
                    "stepwise_edge_count": context.get("stepwise_edge_count"),
                    "possible_nct_resolution_count": context.get("possible_nct_resolution_count"),
                }
            )
        context_scored = [row for row in context_evidence["records"] if row["status"] == "scored"]
        context_categories = Counter()
        for row in context_scored:
            bass_motion = row.get("observed_bass_motion_semitones")
            if row.get("possible_nct_resolution_count", 0):
                context_categories["possible_nct_resolution_boundary"] += 1
            if bass_motion is None:
                context_categories["bass_motion_unavailable"] += 1
            elif abs(bass_motion) <= 2:
                context_categories["stepwise_or_static_bass_boundary"] += 1
            elif abs(bass_motion) % 12 in {5, 7}:
                context_categories["fourth_or_fifth_bass_boundary"] += 1
            else:
                context_categories["other_bass_motion_boundary"] += 1
        return {
            "pair_id": source["pair_id"],
            "analysis_path": source["analysis_path"],
            "score_path": source["score_path"],
            "corpus": source["corpus"],
            "analysis_sha256": source.get("analysis_sha256"),
            "score_sha256": source.get("score_sha256"),
            "evidence_version": EVIDENCE_VERSION,
            "context_evidence_version": CONTEXT_EVIDENCE_VERSION,
            "status": "complete",
            "record_count": evidence["summary"]["record_count"],
            "support_band_counts": evidence["summary"]["support_band_counts"],
            "category_counts": dict(categories),
            "context_summary": context_evidence["summary"],
            "context_category_counts": dict(context_categories),
            "stepwise_voice_leading_edges": sum(row.get("stepwise_edge_count", 0) for row in context_scored),
            "mean_expected_tone_presence_ratio": round(sum(row["expected_tone_presence_ratio"] for row in scored) / len(scored), 6) if scored else None,
            "mean_chord_tone_duration_ratio": round(sum(row["chord_tone_duration_ratio"] for row in scored) / len(scored), 6) if scored else None,
            "review_candidate_count": len(candidates),
            "review_candidates": candidates[:20],
        }
    except Exception as exc:
        return {
            "pair_id": source["pair_id"],
            "analysis_path": source["analysis_path"],
            "score_path": source.get("score_path"),
            "corpus": source["corpus"],
            "analysis_sha256": source.get("analysis_sha256"),
            "score_sha256": source.get("score_sha256"),
            "evidence_version": EVIDENCE_VERSION,
            "context_evidence_version": CONTEXT_EVIDENCE_VERSION,
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _cache_valid(row: dict[str, Any], source: dict[str, Any]) -> bool:
    return (
        row.get("evidence_version") == EVIDENCE_VERSION
        and row.get("context_evidence_version") == CONTEXT_EVIDENCE_VERSION
        and row.get("analysis_sha256") == source.get("analysis_sha256")
        and row.get("score_sha256") == source.get("score_sha256")
    )


def audit_romantext_evidence(
    records_path: str | Path,
    output: str | Path,
    limit: int | None = None,
    corpus: str | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    output = Path(output)
    cache_dir = output / "pair_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    sources = []
    for line in Path(records_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if corpus and row.get("corpus") != corpus:
            continue
        if not row.get("score_path") or row.get("status_counts", {}).get("exact_coordinate", 0) <= 0:
            continue
        pair_id = (row.get("analysis_sha256") or Path(row["analysis_path"]).stem)[:20]
        sources.append(
            {
                "pair_id": pair_id,
                "analysis_path": row["analysis_path"],
                "score_path": row["score_path"],
                "corpus": row.get("corpus", "unknown"),
                "analysis_sha256": row.get("analysis_sha256"),
                "score_sha256": row.get("score_sha256"),
            }
        )
    if limit is not None:
        sources = sources[:limit]
    results: list[dict[str, Any]] = []
    pending = []
    for source in sources:
        cache = cache_dir / f'{source["pair_id"]}.json'
        if cache.is_file():
            try:
                cached = json.loads(cache.read_text(encoding="utf-8"))
                if _cache_valid(cached, source):
                    cached["cache_reused"] = True
                    results.append(cached)
                    continue
            except (json.JSONDecodeError, OSError):
                pass
        pending.append(source)
    if workers <= 1:
        fresh = (_audit_one(source) for source in pending)
        for row in fresh:
            (cache_dir / f'{row["pair_id"]}.json').write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(row)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_audit_one, source): source for source in pending}
            for future in as_completed(futures):
                row = future.result()
                (cache_dir / f'{row["pair_id"]}.json').write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
                results.append(row)
    results.sort(key=lambda row: (row["corpus"], row["analysis_path"]))
    band_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    context_category_counts: Counter[str] = Counter()
    context_totals: Counter[str] = Counter()
    corpus_summary: dict[str, dict[str, Any]] = defaultdict(lambda: {"pairs": 0, "errors": 0, "records": 0, "support_band_counts": Counter()})
    candidates = []
    for row in results:
        group = corpus_summary[row["corpus"]]
        group["pairs"] += 1
        if row["status"] != "complete":
            group["errors"] += 1
            continue
        group["records"] += row["record_count"]
        band_counts.update(row["support_band_counts"])
        category_counts.update(row["category_counts"])
        context_category_counts.update(row["context_category_counts"])
        context_totals["records"] += row["context_summary"]["record_count"]
        context_totals["scored_boundaries"] += row["context_summary"]["scored_boundaries"]
        context_totals["possible_nct_resolution_edges"] += row["context_summary"]["possible_nct_resolution_edges"]
        context_totals["stepwise_voice_leading_edges"] += row["stepwise_voice_leading_edges"]
        group["support_band_counts"].update(row["support_band_counts"])
        for candidate in row["review_candidates"]:
            candidates.append({"pair_id": row["pair_id"], "corpus": row["corpus"], "analysis_path": row["analysis_path"], **candidate})
    summary = {
        "schema_name": "musicanote-romantext-source-evidence-batch-audit",
        "schema_version": "0.1.0",
        "batch_version": BATCH_VERSION,
        "evidence_version": EVIDENCE_VERSION,
        "context_evidence_version": CONTEXT_EVIDENCE_VERSION,
        "input_records": str(Path(records_path)),
        "eligible_pairs": len(sources),
        "processed_pairs": len(results),
        "complete_pairs": sum(row["status"] == "complete" for row in results),
        "error_pairs": sum(row["status"] == "error" for row in results),
        "cache_reused_pairs": sum(row.get("cache_reused") is True for row in results),
        "support_band_counts": dict(band_counts),
        "category_counts": dict(category_counts),
        "context_totals": dict(context_totals),
        "context_category_counts": dict(context_category_counts),
        "corpora": {name: {**value, "support_band_counts": dict(value["support_band_counts"])} for name, value in corpus_summary.items()},
        "interpretation": "Corpus triage evidence only; not annotation accuracy, confidence, gold status, or training eligibility",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "romantext_evidence_pair_records.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8"
    )
    (output / "romantext_evidence_review_candidates.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in candidates), encoding="utf-8"
    )
    (output / "romantext_evidence_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
