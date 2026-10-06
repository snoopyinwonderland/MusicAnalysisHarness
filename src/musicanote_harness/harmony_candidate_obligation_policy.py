"""Non-selecting triad/seventh comparisons over complete saved progressions.

Consumes previously source-validated reviews. This is NOT an authenticity gate,
new native capability, universal resolution law, or final harmony selector.
Literal extra members, conditional NCT coverage and ordinary-strategy failures
remain separate. Disconnected source occurrences are not disproved harmonies.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction

from . import completion_evidence_contrast as accounts
from . import factor_expanded_hypotheses as kernels
from . import factor_temporal_explanations as temporal
from . import native_progression_contrast as parent
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "harmony-candidate-obligation-policy-0.1.0"
TRIADS = {(0, 4, 7): "major", (0, 3, 7): "minor",
          (0, 3, 6): "diminished", (0, 4, 8): "augmented"}
SEVENTHS = {(0, 4, 7, 10): "dominant_seventh", (0, 4, 7, 11): "major_seventh",
    (0, 3, 7, 10): "minor_seventh", (0, 3, 7, 11): "minor_major_seventh",
    (0, 3, 6, 10): "half_diminished_seventh", (0, 3, 6, 9): "diminished_seventh",
    (0, 4, 8, 11): "augmented_major_seventh", (0, 4, 8, 10): "augmented_seventh"}


def chord_shape(slot):
    """Ordered tertian spelling and semitone pattern, never a Roman function."""
    root, members = slot["root"], slot["members"]
    if root is None or members is None:
        return {"kind": "unassessed", "quality": None}
    if len(members) not in (3, 4):
        return {"kind": "other_pitch_pool", "quality": None}
    keys = [kernels._pitch_key(p) for p in members]
    rk = kernels._pitch_key(root)
    if rk is None or any(p is None or p[1].denominator != 1 for p in keys):
        return {"kind": "unsupported_spelling_or_microtone", "quality": None}
    letters = kernels.LETTERS
    if keys[0] != rk or [p[0] for p in keys] != [letters[(letters.index(rk[0]) + 2*i) % 7]
                                                               for i in range(len(keys))]:
        return {"kind": "nontertian_or_unordered_pool", "quality": None}
    intervals = tuple(int((kernels.NATURAL[p[0]] + p[1] - kernels.NATURAL[rk[0]] - rk[1]) % 12)
                      for p in keys)
    quality = (TRIADS if len(keys) == 3 else SEVENTHS).get(intervals)
    return {"kind": "triad" if quality and len(keys) == 3 else "seventh" if quality else "other_tertian_pool",
            "quality": quality, "root_relative_semitones": list(intervals)}


def _strict(sound):
    return not kernels._source_blockers(sound) and not temporal._guard_codes(sound)


def _overlap(a, b):
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo < hi else None


def _span(a, b):
    return {"start": q(a), "end": q(b)}


def _signature(slot):
    return {k: slot[k] for k in ("root", "members", "span")}


def _validate_review(review, scope, sounds, bundles):
    if any(review[k] is not None for k in ("selected", "rank", "confidence")):
        raise ValueError("unselected_obligation_review_required")
    bundle = bundles[review["bundle_ref"]["record_id"]]
    if review["bundle_ref"] != kernels._ref(bundle) or bundle["scope_ref"] != kernels._ref(scope):
        raise ValueError("exact_same_scope_completion_reference_required")
    if bundle["status"] != "complete_all_lane_witness":
        raise ValueError("complete_registered_archived_bundle_required")
    partition, slots = review["partition"], review["slots"]
    if not partition or partition != [s["span"] for s in slots]:
        raise ValueError("complete_slot_partition_required")
    bounds = [span_bounds(s) for s in partition]
    if (bounds[0][0] != span_bounds(scope["analysis_span"])[0]
            or bounds[-1][1] != span_bounds(scope["analysis_span"])[1]
            or any(a >= b for a, b in bounds)
            or any(a[1] != b[0] for a, b in zip(bounds, bounds[1:]))
            or len(review["transitions"]) != len(slots)-1):
        raise ValueError("complete_contiguous_progression_required")
    credit, values = accounts._credit(review, sounds, scope["analysis_span"])
    raw = sum((b-a for s in sounds.values() if not s["point"]
               for a, b in [span_bounds(s["observed_span"])]), Fraction())
    if raw != f(review["note_time_account"]["raw_total_note_time_quarters"]):
        raise ValueError("original_sound_time_inventory_required")
    if f(review["unresolved_note_time_quarters"]) != sum((values[c] for c in parent.CATEGORIES[2:]), Fraction()):
        raise ValueError("exact_unresolved_account_required")
    for i, slot in enumerate(slots):
        if slot["slot_index"] != i:
            raise ValueError("original_slot_order_required")
        members = slot["members"]
        if members is None:
            continue
        if len(slot["member_observations"]) != len(members):
            raise ValueError("complete_member_inventory_required")
        for member, presentation in zip(members, slot["member_observations"]):
            key = kernels._pitch_key(member)
            if presentation["spelling"] != member:
                raise ValueError("exact_member_spelling_required")
            expected = {sid: s for sid, s in sounds.items() if not s["point"]
                and kernels._pitch_key(s["pitch"]) == key
                and _overlap(span_bounds(s["observed_span"]), bounds[i])}
            observations = presentation["observations"]
            if (len(observations) != len(expected) or {o["sound_ref"] for o in observations} != set(expected)
                    or set(presentation["sound_refs"]) != set(expected)
                    or len(presentation["sound_refs"]) != len(expected)):
                raise ValueError("all_literal_member_occurrences_required")
            duration, guarded = Fraction(), []
            for o in observations:
                s = expected[o["sound_ref"]]
                lo, hi = _overlap(span_bounds(s["observed_span"]), bounds[i])
                duration += hi-lo
                if _strict(s):
                    guarded.append(lo)
                if (o["full_sound_span"] != s["span"] or o["observed_span"] != _span(lo, hi)
                        or any(o[k] != s[k] for k in ("source_note_refs", "attack_note_ref", "tie_chain_ref"))
                        or o["attack_before_slot"] is not (span_bounds(s["span"])[0] < bounds[i][0])):
                    raise ValueError("literal_note_attack_tie_span_lineage_required")
            if (f(presentation["source_note_time_quarters"]) != duration or
                    presentation["first_guarded_observed_time"] != (q(min(guarded)) if guarded else None)):
                raise ValueError("literal_member_duration_guard_required")
    for i, transition in enumerate(review["transitions"]):
        if transition["cut_index"] != i or transition["time"] != partition[i+1]["start"]:
            raise ValueError("exact_original_transition_coordinate_required")
        for key in ("joint_support", "whole_ordinary_template_support"):
            accounts._truth(transition[key])
        for role in transition["role_assessments"]:
            accounts._truth(role["satisfied_under_this_bundle"])
            for occurrence in role["occurrences"]:
                route = occurrence["route_sound_refs"]
                if not route or len(set(route)) != len(route) or any(sid not in sounds for sid in route):
                    raise ValueError("original_acyclic_role_route_required")
                edges = [list(e) for e in zip(route, route[1:])]
                if (occurrence["actual_required_links"] != edges or
                        any(e not in bundle["materialized_witness_links"] for e in edges)
                        or occurrence["source_sound_ref"] != route[0]
                        or occurrence["source_note_refs"] != sounds[route[0]]["source_note_refs"]
                        or occurrence["full_sound_spans"] != [sounds[sid]["span"] for sid in route]
                        or occurrence["endpoint_sound_ref"] not in (None, route[-1])):
                    raise ValueError("same_completion_actual_role_route_required")
    return credit


def _route_from(start, sounds, outgoing):
    route, sid = [start], start
    initial = kernels._pitch_key(sounds[start]["pitch"], True)
    while sid in outgoing:
        sid = outgoing[sid]
        if sid in route:
            raise ValueError("acyclic_witness_required")
        route.append(sid)
        if kernels._pitch_key(sounds[sid]["pitch"], True) != initial:
            return route, sid
    return route, None


def _reappearance_probes(occurrence, target, sounds, outgoing):
    """Diagnostic alternatives only; NEVER bridge a gap or skip a first change."""
    if occurrence["endpoint_sound_ref"] is not None:
        return []
    source = sounds[occurrence["source_sound_ref"]]
    key = kernels._pitch_key(source["pitch"], True)
    if key is None:
        return []
    after = span_bounds(sounds[occurrence["route_sound_refs"][-1]]["span"])[1]
    lo, hi = span_bounds(target["span"])
    members = {kernels._pitch_key(p) for p in target["members"] or []}
    rows = []
    for sid, sound in sorted(sounds.items()):
        onset = span_bounds(sound["span"])[0]
        if (not lo <= onset < hi or onset < after or sid in occurrence["route_sound_refs"]
                or sound["lane"] != source["lane"] or source["lane"] is None
                or kernels._pitch_key(sound["pitch"], True) != key):
            continue
        route, endpoint = _route_from(sid, sounds, outgoing)
        motion = None if endpoint is None else kernels._move(sound, sounds[endpoint])
        ordinary = bool(endpoint is not None and motion is not None and motion["diatonic_steps"] == -1
            and f(motion["semitones"]) in (-1, -2)
            and _overlap(span_bounds(sounds[endpoint]["observed_span"]), (lo, hi))
            and kernels._pitch_key(sounds[endpoint]["pitch"]) in members
            and all(_strict(sounds[r]) for r in route))
        rows.append({"reappearing_sound_ref": sid, "source_note_refs": sound["source_note_refs"],
            "same_raw_lane_not_confirmed_musical_voice": True,
            "unconnected_interval": _span(after, onset),
            "interval_is_confirmed_rest": False,
            "actual_downstream_route": route, "endpoint_sound_ref": endpoint,
            "actual_downstream_links": [list(e) for e in zip(route, route[1:])],
            "downstream_ordinary_seventh_shape_under_this_target": ordinary,
            "connection_from_original_occurrence_proven": False,
            "resolution_credit_added": False})
    return rows


def _path_diagnostics(review, sounds, bundle):
    outgoing = dict(bundle["materialized_witness_links"])
    roles = []
    for t in review["transitions"]:
        for role in t["role_assessments"]:
            failed = [o for o in role["occurrences"] if o["satisfied_under_this_bundle"] is not True]
            explanations = []
            for o in failed:
                codes = o["blockers"]
                kind = ("source_guard_withheld" if any(not _strict(sounds[s]) for s in o["route_sound_refs"])
                    else "disconnected_in_this_witness" if o["endpoint_sound_ref"] is None
                    else "endpoint_outside_target_or_nonmember" if "first_changed_endpoint_not_member_inside_target_slot" in codes
                    else "adverse_first_changed_motion" if "ordinary_role_first_change_motion_not_satisfied" in codes
                    else "other_strategy_blocker")
                probes = _reappearance_probes(o, review["slots"][t["cut_index"]+1], sounds, outgoing) if role["role"] == "seventh" else []
                failure_axes = {
                    "source_guard_withheld": any(not _strict(sounds[s]) for s in o["route_sound_refs"]),
                    "disconnected_in_this_witness": o["endpoint_sound_ref"] is None,
                    "endpoint_outside_target_or_nonmember": "first_changed_endpoint_not_member_inside_target_slot" in codes,
                    "adverse_first_changed_motion": "ordinary_role_first_change_motion_not_satisfied" in codes}
                explanations.append({"kind": kind, "failure_axes": failure_axes,
                    "occurrence": deepcopy(o), "reappearance_probes": probes,
                    "ordinary_strategy_failure_rejects_harmony": False})
            roles.append({"cut_index": t["cut_index"], "time": t["time"], "role": role["role"],
                "critical_pitch": role["critical_pitch"], "supported_under_this_completion": role["satisfied_under_this_bundle"],
                "no_observed_source_occurrence": not role["occurrences"], "failed_occurrences": explanations,
                "all_doublings_required": False, "strategy_is_universal_rule": False})
    axes = {
        "explicit_key_coordinate_available": review["key_coordinate_available"],
        "no_source_or_spelling_uncertainty": not any(i["rule_id"] == "ER01" for i in review["issues"]),
        "constituents_observed_or_explicit_omission_evidence": all(s["missing_guarded_spellings"] == [] for s in review["slots"]),
        "no_unresolved_note_time": f(review["unresolved_note_time_quarters"]) == 0,
        "all_internal_transitions_declared": all(t["assumption"] is not None for t in review["transitions"]),
        "all_internal_relations_conditionally_supported": None if not review["transitions"] else
            all(t["joint_support"] is True for t in review["transitions"]),
        "pooled_only_temporal_harmony_evidence_complete": None if any(s["pooled_without_simultaneous_core"] for s in review["slots"]) else True}
    active_axes = [k for k in axes if k != "all_internal_relations_conditionally_supported" or review["transitions"]]
    return {"entry_refs": deepcopy(review["entry_refs"]), "key_ref": review["key_ref"],
        "bundle_ref": review["bundle_ref"], "partition": review["partition"],
        "slot_shapes": [chord_shape(s) for s in review["slots"]], "path_evidence_axes": axes,
        "supported_transition_count": sum(t["joint_support"] is True for t in review["transitions"]),
        "ordinary_role_diagnostics": roles,
        "needs": [k for k in active_axes if axes[k] is not True],
        "no_internal_transition_is_not_hold_failure": not review["transitions"],
        "functional_progression_support_is_not_vacuous": True,
        "cadence_confirmed": False, "harmony_confirmed": False,
        "status": "conditional_path_evidence_complete_not_selected" if all(axes[k] is True for k in active_axes) else "held_path_evidence",
        "selected": None, "rank": None, "confidence": None}


def _pair(triad, seventh, slot_index, sounds, credits):
    left, right = triad["review"], seventh["review"]
    extra = right["slots"][slot_index]["member_observations"][3]
    tc, sc = credits[triad["original_selector_index"]], credits[seventh["original_selector_index"]]
    notes = []
    for o in extra["observations"]:
        sound = sounds[o["sound_ref"]]
        a, b = span_bounds(o["observed_span"])
        intervals = [x for x in (_overlap((a, b), r) for r in tc.get(o["sound_ref"], [])) if x]
        explained = sum((y-x for x, y in intervals), Fraction())
        # The additional spelling is a literal nonmember of the triad, not an
        # NCT just because the triad has fewer ordinary obligations.
        notes.append({**deepcopy(o), "pitch": sound["pitch"], "source_guards_passed": _strict(sound),
            "triad_membership": "nonmember_under_this_triad_not_confirmed_NCT",
            "seventh_membership": "member_under_this_seventh_not_confirmed_harmony",
            "triad_conditional_explanation_spans": [_span(x, y) for x, y in intervals],
            "triad_conditional_explained_quarters": q(explained),
            "triad_not_conditionally_explained_quarters": q(b-a-explained)})
        if any(_overlap((a, b), r) for r in sc.get(o["sound_ref"], [])):
            raise ValueError("seventh_member_cannot_receive_nonmember_credit_inside_its_slot")
    differences = [{"cut_index": i, "time": t["time"], "triad_assumption": t["assumption"],
                    "seventh_assumption": u["assumption"], "triad_joint_support": t["joint_support"],
                    "seventh_joint_support": u["joint_support"],
                    "triad_whole_template": t["whole_ordinary_template_support"],
                    "seventh_whole_template": u["whole_ordinary_template_support"]}
                   for i, (t, u) in enumerate(zip(left["transitions"], right["transitions"]))
                   if t["assumption"] != u["assumption"] or t["joint_support"] != u["joint_support"]
                   or t["whole_ordinary_template_support"] != u["whole_ordinary_template_support"]]
    return {"triad_original_selector_index": triad["original_selector_index"],
        "seventh_original_selector_index": seventh["original_selector_index"], "changed_slot_index": slot_index,
        "key_ref": left["key_ref"], "bundle_ref": left["bundle_ref"], "partition": left["partition"],
        "triad_origin_ref": left["slots"][slot_index]["origin_ref"],
        "seventh_origin_ref": right["slots"][slot_index]["origin_ref"],
        "extra_member": extra["spelling"], "extra_member_first_guarded_time": extra["first_guarded_observed_time"],
        "additional_member_occurrences": notes, "additional_member_source_time_quarters": q(sum(
            (f(n["observed_span"]["end"])-f(n["observed_span"]["start"]) for n in notes), Fraction())),
        "triad_additional_member_unexplained_quarters": q(sum((f(n["triad_not_conditionally_explained_quarters"]) for n in notes), Fraction())),
        "transition_differences": differences,
        "no_extra_member_observation_is_missing_evidence_not_proof_of_triad": not notes,
        "fewer_obligations_selects_triad": False, "extra_member_presence_selects_seventh": False,
        "pooled_presence_backdates_chord": False, "ordinary_failure_eliminates_seventh": False,
        "selected": None, "rank": None, "confidence": None}


def compare_candidates(rows, scope, bundles, *, max_pairs=20000):
    """Preserve every candidate; pair only one-slot exact triad/seventh changes.

    Candidate signatures and unrelated transitions must agree. Adjacent
    transition assumptions may differ and are explicitly reported, NOT silently
    treated as fixed premises. Different keys, partitions or witnesses never
    share credit. Previously validated archives are still conditional evidence.
    """
    if type(max_pairs) is not int or max_pairs < 0:
        raise ValueError("exact_nonnegative_obligation_pair_budget_required")
    positions = [r["original_selector_index"] for r in rows]
    if any(type(i) is not int or i < 0 for i in positions) or len(set(positions)) != len(positions):
        raise ValueError("unique_original_selector_positions_required")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    if len(sounds) != len(scope["sound_facts"]):
        raise ValueError("unique_obligation_source_sounds_required")
    credits, paths, groups = {}, [], defaultdict(lambda: {"triad": [], "seventh": []})
    for row in rows:
        r, pos = row["review"], row["original_selector_index"]
        credits[pos] = _validate_review(r, scope, sounds, bundles)
        diagnostic = _path_diagnostics(r, sounds, bundles[r["bundle_ref"]["record_id"]])
        paths.append({"original_selector_index": pos, **diagnostic})
        for i, slot in enumerate(r["slots"]):
            kind = chord_shape(slot)["kind"]
            if kind not in ("triad", "seventh"):
                continue
            common = {"key": r["key_ref"], "bundle": r["bundle_ref"], "partition": r["partition"],
                "changed_slot": i, "root": slot["root"], "triad_core": slot["members"][:3],
                "unchanged_slots": [_signature(s) for j, s in enumerate(r["slots"]) if i != j],
                "unrelated_transitions": [t["assumption"] for j, t in enumerate(r["transitions"]) if j not in (i-1, i)]}
            groups[digest(common)][kind].append((row, i))
    planned = sum(len(g["triad"])*len(g["seventh"]) for g in groups.values())
    if planned > max_pairs:
        raise ValueError("whole_obligation_pair_budget_exceeded_no_prefix")
    pairs = [_pair(a, b, i, sounds, credits) for key, group in sorted(groups.items())
             for a, i in group["triad"] for b, _ in group["seventh"]]
    summary = Counter(candidate_paths=len(paths), planned_exact_extension_pairs=planned, computed_exact_extension_pairs=len(pairs))
    for path in paths:
        summary[path["status"]] += 1
        for role in path["ordinary_role_diagnostics"]:
            summary["supported_"+role["role"]+"_contexts"] += role["supported_under_this_completion"] is True
            for failure in role["failed_occurrences"]:
                summary[failure["kind"]+"_occurrences"] += 1
                summary["reappearance_probes"] += len(failure["reappearance_probes"])
                summary["downstream_shape_without_original_connection"] += sum(
                    p["downstream_ordinary_seventh_shape_under_this_target"] for p in failure["reappearance_probes"])
    summary["pairs_with_observed_extra_member"] = sum(bool(p["additional_member_occurrences"]) for p in pairs)
    summary["pairs_with_unexplained_extra_under_triad"] = sum(f(p["triad_additional_member_unexplained_quarters"]) > 0 for p in pairs)
    return {"version": VERSION, "source_scope_ref": kernels._ref(scope), "analysis_span": scope["analysis_span"],
        "original_selector_indices": positions, "candidate_paths": paths, "extension_pairs": pairs,
        "summary": dict(summary), "same_completion_credit_only": True, "ordinary_predicates_reinferred": False,
        "key_hypotheses_pooled": False, "boundary_hypotheses_pooled": False,
        "saved_JSON_restores_capability": False, "selected": None, "rank": None, "confidence": None,
        "flags": parent._flags()}
