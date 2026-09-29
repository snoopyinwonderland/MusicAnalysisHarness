"""Blind dev-set ablation for harmony case retrieval features."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator

from .harmony_case_retrieval import WEIGHT_PROFILES, _f, _key_vector, _movement_vector, _nct_vector, _vector, load_case_records


VERSION = "harmony-case-retrieval-eval-0.1.0"


def _rank_metrics(query: dict[str, Any], order: np.ndarray, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    raw = query["label"]["raw"]
    family = query["label"].get("taxonomy", {}).get("family", "other_or_unresolved")
    raw_rank = None
    family_rank = None
    for rank, index in enumerate(order, 1):
        case = candidates[int(index)]
        if raw_rank is None and case["label"]["raw"] == raw:
            raw_rank = rank
        if family_rank is None and case["label"].get("taxonomy", {}).get("family", "other_or_unresolved") == family:
            family_rank = rank
        if raw_rank is not None and family_rank is not None:
            break
    return {
        "raw_top1": raw_rank == 1,
        "raw_top5": raw_rank is not None and raw_rank <= 5,
        "raw_rr": 1 / raw_rank if raw_rank else 0.0,
        "family_top1": family_rank == 1,
        "family_top5": family_rank is not None and family_rank <= 5,
        "family_rr": 1 / family_rank if family_rank else 0.0,
        "family": family,
    }


def _normalized(values: list[float] | None, width: int) -> tuple[np.ndarray, bool]:
    if values is None:
        return np.zeros(width, dtype=np.float64), False
    array = np.asarray(values, dtype=np.float64)
    norm = float(np.linalg.norm(array))
    return (array / norm, True) if norm else (np.zeros(width, dtype=np.float64), False)


def _candidate_arrays(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    vectors = {
        "current_interval_profile": (lambda f: _vector(f["current"]), 12),
        "before_interval_profile": (lambda f: _vector(f.get("before")), 12),
        "after_interval_profile": (lambda f: _vector(f.get("after")), 12),
        "blind_local_key": (lambda f: _key_vector(f.get("blind_local_key")), 24),
        "entry_voice_leading": (lambda f: _movement_vector(f.get("entry_voice_leading")), 25),
        "exit_voice_leading": (lambda f: _movement_vector(f.get("exit_voice_leading")), 25),
        "nct_geometry": (lambda f: _nct_vector(f.get("nct_geometry")), 7),
    }
    result: dict[str, Any] = {}
    for name, (reader, width) in vectors.items():
        rows, present = zip(*(_normalized(reader(case["feature"]), width) for case in candidates))
        result[name] = np.vstack(rows)
        result[f"{name}_available"] = np.asarray(present, dtype=bool)
    result["duration"] = np.asarray([float(_f(case["feature"]["current"]["duration_quarter"])) for case in candidates])
    result["attack_density"] = np.asarray([case["feature"]["current"]["attack_density"] for case in candidates])
    result["vertical_density"] = np.asarray([case["feature"]["current"]["mean_vertical_count"] for case in candidates])
    result["bass_motion"] = np.asarray([case["feature"]["current"]["bass_motion_semitones"] for case in candidates])
    result["case_ids"] = np.asarray([case["case_id"] for case in candidates])
    result["score_ids"] = np.asarray([case["score_id"] for case in candidates])
    result["work_families"] = np.asarray([case["dataset_identity"]["work_family_id"] for case in candidates])
    result["lineages"] = np.asarray([case["dataset_identity"]["annotation_lineage_id"] for case in candidates])
    return result


def _query_channels(query: dict[str, Any], arrays: dict[str, Any]) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    feature = query["feature"]
    vector_readers = {
        "current_interval_profile": (_vector(feature["current"]), 12),
        "before_interval_profile": (_vector(feature.get("before")), 12),
        "after_interval_profile": (_vector(feature.get("after")), 12),
        "blind_local_key": (_key_vector(feature.get("blind_local_key")), 24),
        "entry_voice_leading": (_movement_vector(feature.get("entry_voice_leading")), 25),
        "exit_voice_leading": (_movement_vector(feature.get("exit_voice_leading")), 25),
        "nct_geometry": (_nct_vector(feature.get("nct_geometry")), 7),
    }
    values: dict[str, np.ndarray] = {}
    available: dict[str, np.ndarray] = {}
    for name, (raw, width) in vector_readers.items():
        vector, present = _normalized(raw, width)
        available[name] = arrays[f"{name}_available"] & present
        values[name] = arrays[name] @ vector if present else np.zeros(len(arrays[name]))
    scalar_queries = {
        "duration": float(_f(feature["current"]["duration_quarter"])),
        "attack_density": feature["current"]["attack_density"],
        "vertical_density": feature["current"]["mean_vertical_count"],
    }
    for name, query_value in scalar_queries.items():
        candidate_values = arrays[name]
        mask = (query_value > 0) & (candidate_values > 0)
        values[name] = np.where(mask, np.minimum(query_value, candidate_values) / np.maximum(query_value, candidate_values), 0.0)
        available[name] = np.asarray(mask if np.ndim(mask) else np.full(len(candidate_values), mask), dtype=bool)
    values["bass_motion"] = np.maximum(0.0, 1 - np.abs(feature["current"]["bass_motion_semitones"] - arrays["bass_motion"]) / 12)
    available["bass_motion"] = np.ones(len(arrays["bass_motion"]), dtype=bool)
    return values, available


def _profile_scores(values: dict[str, np.ndarray], available: dict[str, np.ndarray], profile: str) -> np.ndarray:
    numerator = np.zeros(len(next(iter(values.values()))), dtype=np.float64)
    denominator = np.zeros_like(numerator)
    for channel, weight in WEIGHT_PROFILES[profile].items():
        numerator += weight * values[channel] * available[channel]
        denominator += weight * available[channel]
    return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)


def evaluate_case_retrieval_ablation(
    library_path: str | Path,
    output: str | Path,
    *,
    query_split: str = "dev",
    candidate_split: str = "train",
    limit: int | None = None,
) -> dict[str, Any]:
    cases = load_case_records(library_path)
    queries = [case for case in cases if case.get("dataset_identity", {}).get("split") == query_split]
    candidates = [case for case in cases if case.get("dataset_identity", {}).get("split") == candidate_split]
    queries.sort(key=lambda case: case["case_id"])
    if limit is not None:
        queries = queries[:max(0, limit)]
    arrays = _candidate_arrays(candidates)
    accumulators: dict[str, dict[str, Any]] = {
        profile: {
            "raw_top1": 0, "raw_top5": 0, "raw_rr": 0.0,
            "family_top1": 0, "family_top5": 0, "family_rr": 0.0,
            "evaluated": 0, "no_candidates": 0, "per_family": defaultdict(Counter),
        }
        for profile in WEIGHT_PROFILES
    }
    for query in queries:
        identity = query["dataset_identity"]
        eligible = ((arrays["score_ids"] != query["score_id"])
                    & (arrays["work_families"] != identity["work_family_id"])
                    & (arrays["lineages"] != identity["annotation_lineage_id"]))
        if not np.any(eligible):
            for accumulator in accumulators.values():
                accumulator["no_candidates"] += 1
            continue
        channel_values, channel_available = _query_channels(query, arrays)
        for profile, accumulator in accumulators.items():
            scores = _profile_scores(channel_values, channel_available, profile)
            scores = np.where(eligible, scores, -np.inf)
            order = np.lexsort((arrays["case_ids"], -scores))
            order = order[np.isfinite(scores[order])]
            metrics = _rank_metrics(query, order, candidates)
            accumulator["evaluated"] += 1
            for key in ("raw_top1", "raw_top5", "family_top1", "family_top5"):
                accumulator[key] += int(metrics[key])
            accumulator["raw_rr"] += metrics["raw_rr"]
            accumulator["family_rr"] += metrics["family_rr"]
            family_row = accumulator["per_family"][metrics["family"]]
            family_row["count"] += 1
            family_row["top1"] += int(metrics["family_top1"])

    results = []
    for profile, accumulator in accumulators.items():
        count = accumulator["evaluated"] or 1
        results.append({
            "weight_profile": profile,
            "evaluated_queries": accumulator["evaluated"],
            "no_candidate_queries": accumulator["no_candidates"],
            "raw_top1_accuracy": round(accumulator["raw_top1"] / count, 6),
            "raw_top5_recall": round(accumulator["raw_top5"] / count, 6),
            "raw_mrr": round(accumulator["raw_rr"] / count, 6),
            "family_top1_accuracy": round(accumulator["family_top1"] / count, 6),
            "family_top5_recall": round(accumulator["family_top5"] / count, 6),
            "family_mrr": round(accumulator["family_rr"] / count, 6),
            "per_family": [
                {"family": family, "count": values["count"],
                 "top1_accuracy": round(values["top1"] / values["count"], 6)}
                for family, values in sorted(accumulator["per_family"].items())
            ],
        })
    baseline = next(row for row in results if row["weight_profile"] == "surface_v0.1")
    for row in results:
        row["delta_vs_surface"] = {
            "raw_top1_accuracy": round(row["raw_top1_accuracy"] - baseline["raw_top1_accuracy"], 6),
            "family_top1_accuracy": round(row["family_top1_accuracy"] - baseline["family_top1_accuracy"], 6),
            "family_mrr": round(row["family_mrr"] - baseline["family_mrr"], 6),
        }
    incumbent = next(row for row in results if row["weight_profile"] == "combined_v0.3")
    best = max(results, key=lambda row: (row["family_mrr"], row["family_top1_accuracy"], row["weight_profile"]))
    promotion = (best["family_mrr"] - incumbent["family_mrr"] >= 0.01
                 and best["raw_top1_accuracy"] - incumbent["raw_top1_accuracy"] >= -0.01)
    report = {
        "schema_name": "musicanote-harmony-case-retrieval-ablation",
        "schema_version": "0.1.0",
        "evaluator_version": VERSION,
        "library": str(library_path),
        "query_split": query_split,
        "candidate_split": candidate_split,
        "query_count": len(queries),
        "candidate_count": len(candidates),
        "evaluation_scope": {
            "gold_annotation_span_boundaries_provided": True,
            "source_harmony_label_hidden_from_features_and_ranking": True,
            "metric_is_case_retrieval_not_end_to_end_harmony_analysis": True,
            "holdout_evaluated": query_split == "holdout",
        },
        "label_visibility_policy": {
            "query_label_hidden_during_ranking": True,
            "query_label_used_only_after_ranking_for_metrics": True,
            "same_score_work_family_and_lineage_excluded": True,
        },
        "results": results,
        "dev_selection": {
            "recommended_weight_profile": (best["weight_profile"] if promotion else incumbent["weight_profile"]) if query_split == "dev" else None,
            "best_family_mrr_profile": best["weight_profile"] if query_split == "dev" else None,
            "selection_metric": "family_mrr_with_raw_top1_non_regression_gate" if query_split == "dev" else None,
            "promotion_gate": {
                "minimum_family_mrr_gain": 0.01,
                "maximum_raw_top1_regression": 0.01,
                "challenger_promoted": promotion,
            },
            "holdout_must_remain_closed_until_design_freeze": query_split == "dev",
        },
        "interpretation": "Offline retrieval ablation only; not calibrated harmony accuracy and not authorized to affect structure analysis",
    }
    schema_path = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "harmony_case_retrieval_ablation.schema.json"
    Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(report)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
