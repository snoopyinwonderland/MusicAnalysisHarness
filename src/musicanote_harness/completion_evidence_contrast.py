"""Compare archived role evidence with identical music and different links.

This is an assumption-sensitivity test, not voice inference or a winner. Input
reviews must have been source-validated by the adapter. Independent completions
are NEVER combined into one explanation or accepted as validated musical voices.
"""
from copy import deepcopy
from fractions import Fraction

from . import native_progression_contrast as parent
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "completion-evidence-contrast-0.1.0"


def _credit(review, sounds, analysis_span):
    account = review["note_time_account"]
    if set(account["note_time_quarters"]) != set(parent.CATEGORIES):
        raise ValueError("closed_completion_account_required")
    values = {k: f(v) for k, v in account["note_time_quarters"].items()}
    if (any(v < 0 for v in values.values()) or
            sum(values.values(), Fraction()) != f(account["raw_total_note_time_quarters"])):
        raise ValueError("conserved_completion_account_required")
    lo, hi = span_bounds(analysis_span)
    credit = {}
    for row in account["explained_intervals_by_sound"]:
        sid = row["sound_ref"]
        if sid not in sounds or sid in credit:
            raise ValueError("unique_original_completion_sound_required")
        a, b = span_bounds(sounds[sid]["span"])
        ranges = [span_bounds(s) for s in row["spans"]]
        if (not ranges or any(not max(a, lo) <= x < y <= min(b, hi) for x, y in ranges)
                or any(x[1] >= y[0] for x, y in zip(ranges, ranges[1:]))):
            raise ValueError("canonical_original_sound_credit_ranges_required")
        credit[sid] = ranges
    total = sum((b - a for spans in credit.values() for a, b in spans), Fraction())
    if total != values["conditional_explained_nonmember"]:
        raise ValueError("completion_credit_union_account_mismatch")
    reported = account["conditional_explanation_note_time_quarters"]
    if reported is not None and f(reported) != total:
        raise ValueError("completion_credit_report_mismatch")
    return credit, values


def _truth(value):
    if value is not None and type(value) is not bool:
        raise ValueError("exact_completion_tri_truth_required")
    return "unknown" if value is None else "true" if value else "false"


def compare_reviews(left, right, scope, bundles):
    """Pure contrast of already validated reviews; no authentication capability."""
    for row in (left, right):
        if any(row[k] is not None for k in ("selected", "rank", "confidence")):
            raise ValueError("unselected_completion_review_required")
        ref = row["bundle_ref"]
        bundle = bundles[ref["record_id"]]
        if ref != {k: bundle[k] for k in ("record_id", "record_sha256")}:
            raise ValueError("exact_completion_reference_required")
    if left["bundle_ref"] == right["bundle_ref"]:
        raise ValueError("distinct_completion_assumptions_required")
    # Roots/members, attacks, tie release, literal bass and key cannot change
    # merely because a witness link was supplied. This also prevents ordinal
    # matching from silently comparing different candidates.
    for field in ("key_ref", "partition", "slots", "key_coordinate_available"):
        if left[field] != right[field]:
            raise ValueError("identical_source_harmony_premises_required:" + field)
    if ([t["assumption"] for t in left["transitions"]] !=
            [t["assumption"] for t in right["transitions"]]):
        raise ValueError("identical_transition_assumptions_required")
    if len(left["transitions"]) != len(right["transitions"]):
        raise ValueError("identical_transition_inventory_required")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    if len(sounds) != len(scope["sound_facts"]):
        raise ValueError("unique_source_sound_inventory_required")
    lc, lv = _credit(left, sounds, scope["analysis_span"])
    rc, rv = _credit(right, sounds, scope["analysis_span"])
    # Raw membership is independent of completion, unlike NCT explanation.
    if (left["note_time_account"]["raw_total_note_time_quarters"] !=
            right["note_time_account"]["raw_total_note_time_quarters"] or
            left["note_time_account"]["raw_state_note_time_quarters"] !=
            right["note_time_account"]["raw_state_note_time_quarters"]):
        raise ValueError("identical_raw_music_account_required")
    differences = []
    for sid in sorted(set(lc) | set(rc)):
        points = sorted({v for bounds in lc.get(sid, []) + rc.get(sid, []) for v in bounds})
        for a, b in zip(points, points[1:]):
            lp = any(x <= a < b <= y for x, y in lc.get(sid, []))
            rp = any(x <= a < b <= y for x, y in rc.get(sid, []))
            if lp != rp:
                sound = sounds[sid]
                differences.append({"sound_ref": sid, "source_note_refs": sound["source_note_refs"],
                    "pitch": sound["pitch"], "full_sound_span": sound["span"],
                    "span": {"start": q(a), "end": q(b)}, "duration_quarters": q(b - a),
                    "left_conditional_credit": lp, "right_conditional_credit": rp})
    transitions = []
    for a, b in zip(left["transitions"], right["transitions"]):
        if any(a[k] != b[k] for k in ("cut_index", "time", "function_shape", "shape_conflicts")):
            raise ValueError("identical_literal_function_shape_required")
        transitions.append({"cut_index": a["cut_index"], "time": a["time"],
            "left_state": a["state"], "right_state": b["state"],
            "joint_truth_change": [_truth(a["joint_support"]), _truth(b["joint_support"])],
            "whole_template_truth_change": [_truth(a["whole_ordinary_template_support"]),
                                            _truth(b["whole_ordinary_template_support"])],
            "role_evidence_changed": a["role_assessments"] != b["role_assessments"],
            "literal_shape_conflicts": a["shape_conflicts"],
            "left_context_ref": a["context_ref"], "right_context_ref": b["context_ref"]})
    delta = {k: q(rv[k] - lv[k]) for k in parent.CATEGORIES}
    credit_delta = rv["conditional_explained_nonmember"] - lv["conditional_explained_nonmember"]
    signed_difference = sum((f(r["duration_quarters"]) * (1 if r["right_conditional_credit"] else -1)
                             for r in differences), Fraction())
    if credit_delta != signed_difference:
        raise ValueError("source_credit_difference_conservation_required")
    return {"version": VERSION, "same_premise_id": digest([left["key_ref"], left["partition"],
        [s["origin_ref"] for s in left["slots"]], [t["assumption"] for t in left["transitions"]]]),
        "left_entry_refs": deepcopy(left["entry_refs"]), "right_entry_refs": deepcopy(right["entry_refs"]),
        "key_ref": left["key_ref"], "left_bundle_ref": left["bundle_ref"], "right_bundle_ref": right["bundle_ref"],
        "partition": left["partition"], "raw_source_music_unchanged": True,
        "category_delta_right_minus_left": delta, "conditional_credit_delta_quarters": q(credit_delta),
        "changed_sound_credit_spans": differences, "transition_contrasts": transitions,
        "left_cadence_candidates": left["cadence_candidates"], "right_cadence_candidates": right["cadence_candidates"],
        "more_explained_time_is_not_a_winner": True, "completion_links_are_not_validated_musical_voices": True,
        "missing_constituents_not_filled_by_voice_links": True, "independent_completions_unioned": False,
        "selected": None, "rank": None, "confidence": None, "flags": parent._flags()}
