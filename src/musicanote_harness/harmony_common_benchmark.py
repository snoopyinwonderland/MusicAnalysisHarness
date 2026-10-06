"""J3 common metric contract; evaluation only, never a harmony selector.

Exact quarter-time and 32nd-note sampling are separate measures. Missing
predictions stay in the reference-supported denominator. Unsupported reference
components are reported, not invented from a root or a Roman numeral.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction

from .harmony_candidate_recall import fraction, rational, spelling

VERSION = "harmony-common-benchmark-0.1.0"
FIELDS = ("root", "root_members", "quality", "inversion", "local_key", "degree", "roman")
GRID = Fraction(1, 8)  # 32nd note, NOT 1/32 of a quarter
CONTRACT = {
    "version": VERSION,
    "clock": "canonical_global_quarter",
    "span_convention": "[start,end)",
    "root_equality": "exact_step_and_integer_alter_not_enharmonic_pitch_class",
    "root_members_equality": "root_plus_unordered_unique_spelled_members",
    "other_components": "explicit_adapter_labels_only_no_inference_or_alias_rewriting",
    "unknown_prediction": "zero_match_and_zero_prediction_coverage_not_denominator_exclusion",
    "unsupported_reference": "component_specific_unavailable_time_reported",
    "boundary": "exact_root_members_changes_full_reference_contexts_only",
    "grid": {"step_quarter": rational(GRID), "phase_quarter": rational(Fraction()),
             "sample_rule": "k/8_in_[start,end)_label_active_at_sample",
             "paper_reproduction_validated": False},
    "context_time_may_overlap": True,
    "full_roman_accuracy_inferred_from_root_members": False,
}


def _label(field, value):
    if value is None:
        return None
    if field == "root":
        return spelling(value)
    if field == "root_members":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("invalid_root_members_label")
        root, members = value
        if root is None or not isinstance(members, (list, tuple)) or not members:
            raise ValueError("invalid_root_members_label")
        return spelling(root), tuple(sorted({spelling(p) for p in members}))
    if field == "inversion":
        if type(value) is not int or value not in range(4):
            raise ValueError("invalid_inversion_label")
        return value
    if field == "local_key":
        if (not isinstance(value, dict) or set(value) != {"tonic", "mode"}
                or value["mode"] not in ("major", "minor")):
            raise ValueError("invalid_local_key_label")
        return spelling(value["tonic"]), value["mode"]
    if not isinstance(value, str) or not value.strip() or value.lower() == "unknown":
        raise ValueError("use_null_for_unavailable_component:" + field)
    return value


def partition(rows, span):
    """A complete ordered partition, with explicit unknown cells when necessary."""
    start, end = fraction(span["start"]), fraction(span["end"])
    if start < 0 or end <= start:
        raise ValueError("invalid_benchmark_span")
    result, cursor = [], start
    for row in rows:
        a, b = fraction(row["span"]["start"]), fraction(row["span"]["end"])
        labels = row["labels"]
        if a != cursor or b <= a or b > end:
            raise ValueError("invalid_benchmark_partition")
        if not isinstance(labels, dict) or set(labels) - set(FIELDS):
            raise ValueError("unknown_component")
        normalized = {field: _label(field, labels.get(field)) for field in FIELDS}
        if (normalized["root"] is not None and normalized["root_members"] is not None
                and normalized["root"] != normalized["root_members"][0]):
            raise ValueError("inconsistent_root_components")
        result.append({"start": a, "end": b, "labels": normalized})
        cursor = b
    if cursor != end:
        raise ValueError("incomplete_benchmark_partition")
    return result


def onset_prediction(rows, span, *, clock):
    """Extend an explicit quarter-onset label to the next onset or score end.

    Native model beats/floats must first be mapped with source-bound clock
    evidence. An unlabelled prefix is unknown, not filled from the first label.
    """
    if clock != "canonical_global_quarter":
        raise ValueError("external_clock_mapping_required")
    a, b = fraction(span["start"]), fraction(span["end"])
    if a < 0 or b <= a:
        raise ValueError("invalid_benchmark_span")
    if not rows:
        return [{"span": span, "labels": {}}]
    points = [fraction(r["onset"]) for r in rows]
    if points != sorted(set(points)) or points[0] < a or points[-1] >= b:
        raise ValueError("invalid_or_duplicate_prediction_onset")
    result = []
    if points[0] > a:
        result.append({"span": {"start": rational(a), "end": rational(points[0])}, "labels": {}})
    for index, row in enumerate(rows):
        result.append({"span": {"start": rational(points[index]),
                                "end": rational(points[index+1] if index+1 < len(points) else b)},
                       "labels": row["labels"]})
    partition(result, span)
    return result


def native_reference(record):
    """Existing DCML projection only; do not invent quality/key/inversion/RN."""
    result = []
    for cell in record["reference_cells"]:
        sig = cell["signature"]
        labels = {} if sig is None or sig[0] is None else {"root": sig[0], "root_members": sig}
        result.append({"span": cell["span"], "labels": labels})
    return result


def native_prediction(prediction, span):
    if prediction is None:
        return [{"span": span, "labels": {}}]
    if prediction.get("source_labels_used_for_selection") is not False:
        raise ValueError("nonblind_prediction")
    if prediction.get("training_reference_labels_used", False) is not False:
        raise ValueError("training_adversary_is_not_prediction")
    result = []
    for seg in prediction["segments"]:
        root, members = seg["root_spelling"], seg["members"]
        result.append({"span": seg["span"], "labels": {} if root is None else
                       {"root": root, "root_members": [root, members]}})
    partition(result, span)
    return result


def _grid_count(start, end):
    # ceil(end/step) - ceil(start/step), so a sample on end is excluded.
    ceil = lambda x: -(-x.numerator // x.denominator)
    return ceil(end/GRID) - ceil(start/GRID)


def evaluate(reference, prediction, span, *, selected):
    ref, pred = partition(reference, span), partition(prediction, span)
    if type(selected) is not bool:
        raise ValueError("invalid_selection_status")
    if not selected and any(v is not None for row in pred for v in row["labels"].values()):
        raise ValueError("abstention_with_labels")
    total = fraction(span["end"]) - fraction(span["start"])
    components = {f: {"eligible": Fraction(), "matched": Fraction(), "covered": Fraction(),
                      "grid_eligible": 0, "grid_matched": 0, "grid_covered": 0} for f in FIELDS}
    i = j = 0
    while i < len(ref) and j < len(pred):
        r, p = ref[i], pred[j]
        a, b = max(r["start"], p["start"]), min(r["end"], p["end"])
        time, points = b-a, _grid_count(a, b)
        for field, counts in components.items():
            gold, guess = r["labels"][field], p["labels"][field]
            if gold is None:
                continue
            counts["eligible"] += time; counts["grid_eligible"] += points
            if guess is not None:
                counts["covered"] += time; counts["grid_covered"] += points
                if guess == gold:
                    counts["matched"] += time; counts["grid_matched"] += points
        if r["end"] <= p["end"]: i += 1
        if p["end"] <= r["end"]: j += 1
    def changes(rows):
        return {l["end"] for l, r in zip(rows, rows[1:])
                if l["labels"]["root_members"] != r["labels"]["root_members"]}
    full = components["root_members"]["eligible"] == total
    boundary = None
    if full:
        gold, guess = changes(ref), changes(pred) if selected else set()
        boundary = {"matched": len(gold & guess), "extra": len(guess-gold), "missed": len(gold-guess)}
    return {"context_time": rational(total), "fully_evaluable": full, "selected": selected,
            "selected_hit": components["root_members"]["matched"] == total if full else None,
            "semantic_boundary_exact": boundary,
            "components": {f: {k: rational(v) if isinstance(v, Fraction) else v for k, v in d.items()}
                           for f, d in components.items()}}


def summarize(rows):
    """Micro time agreement and per-family macro, never average percentages."""
    sums = {f: Counter() for f in FIELDS}; families = defaultdict(lambda: defaultdict(Counter))
    boundaries = Counter(); total = Fraction(); selected = full = hits = 0
    for row in rows:
        v = row["evaluation"]
        total += fraction(v["context_time"]); selected += v["selected"]
        full += v["fully_evaluable"]; hits += v["selected_hit"] is True
        if v["semantic_boundary_exact"] is not None: boundaries.update(v["semantic_boundary_exact"])
        for f, values in v["components"].items():
            for k, raw in values.items():
                val = fraction(raw) if isinstance(raw, dict) else raw
                sums[f][k] += val; families[row["work_family_id"]][f][k] += val
    components = {}
    for f, d in sums.items():
        eligible = d["eligible"]
        macro = [v[f]["matched"]/v[f]["eligible"] for v in families.values() if v[f]["eligible"]]
        components[f] = {"eligible_time": rational(Fraction(eligible)),
                         "unavailable_reference_time": rational(total-eligible),
                         "matched_time": rational(Fraction(d["matched"])),
                         "prediction_covered_time": rational(Fraction(d["covered"])),
                         "time_agreement": float(d["matched"]/eligible) if eligible else None,
                         "prediction_coverage": float(d["covered"]/eligible) if eligible else None,
                         "work_family_macro": float(sum(macro, Fraction())/len(macro)) if macro else None,
                         "supported_work_families": len(macro),
                         "grid_eligible": d["grid_eligible"], "grid_matched": d["grid_matched"],
                         "grid_prediction_covered": d["grid_covered"],
                         "grid_agreement": d["grid_matched"]/d["grid_eligible"] if d["grid_eligible"] else None}
    tp, fp, fn = (boundaries[k] for k in ("matched", "extra", "missed"))
    return {"contexts": len(rows), "work_families": len(families), "context_time": rational(total),
            "selected_contexts": selected, "abstained_contexts": len(rows)-selected,
            "fully_evaluable_contexts": full, "selected_correct_contexts": hits,
            "selected_context_agreement": hits/full if full else None, "components": components,
            "semantic_boundary_exact": {"matched": tp, "extra": fp, "missed": fn,
                "precision": tp/(tp+fp) if tp+fp else None, "recall": tp/(tp+fn) if tp+fn else None,
                "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}}


def identity_overlap(candidate, exposed):
    """Family and byte/lineage aliases; no title-specific music rules."""
    fields = ("work_family_id", "score_sha256", "annotation_sha256", "annotation_lineage_id")
    return [field for field in fields if candidate.get(field) is not None
            and any(e.get(field) == candidate[field] for e in exposed)]


def readiness(entries, exposed, exposure_ledger):
    """Metadata audit only. No new rights, split changes, or blind approval."""
    result = []
    for e in entries:
        if e["split"] != "holdout": continue
        overlaps = identity_overlap(e, exposed)
        history = [h for h in exposure_ledger if h["work_family_id"] == e["work_family_id"]]
        reasons = []
        if overlaps: reasons.append("known_development_identity_overlap")
        if any(h["musical_result_exposed"] for h in history): reasons.append("prior_musical_result_exposed")
        if not e["quality"].get("source_note_mapping_complete"): reasons.append("incomplete_source_note_mapping")
        if not e.get("eligibility", {}).get("blind_evaluation"): reasons.append("original_blind_eligibility_absent")
        if not e.get("rights", {}).get("internal_research_use"): reasons.append("internal_research_use_absent")
        result.append({"manifest_entry_id": e["manifest_entry_id"], "work_family_id": e["work_family_id"],
            "collection_id": e["collection_id"], "movement_id": e["movement_id"],
            "work_family_source_key": e["work_family_source_key"], "package_path": e["package_path"],
            "known_overlap_fields": overlaps, "history": history, "reasons": reasons,
            "known_exposure_excluded": "prior_musical_result_exposed" in reasons or bool(overlaps),
            "status": "excluded_or_source_blocked" if reasons else "metadata_candidate_not_blind_approved",
            "remaining_gates": ["full_exposure_history_audit", "source_binding_and_annotation_sanitization",
                                "alignment_revision_validation", "frozen_model_and_execution_policy",
                                "external_checkpoint_training_overlap_audit"],
            "original_eligibility": e["eligibility"], "original_rights": e["rights"],
            "blind_evaluation_approved_by_this_audit": False})
    return result
