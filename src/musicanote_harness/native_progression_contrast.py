"""Source-aligned contrasts of archived complete progression hypotheses.

This is a saved-evidence adapter, NOT an issuer of live native authority.
It does not re-run chord suppliers or role predicates and never selects a
winner. Raw profiles and union arithmetic are checked against the same source.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
from itertools import combinations

from . import factor_expanded_hypotheses as kernels
from . import factor_interval_lattice as native
from . import factor_native_role_explanations as roles
from . import factor_temporal_explanations as temporal
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "native-progression-contrast-0.1.0"
PREFIX = "npccontrast_"
AUTHORITY = "validated_saved_evidence_not_live_native_session"
CATEGORIES = roles.CATEGORIES
KINDS = ("candidate_only", "transition_only", "candidate_and_transition", "partition")


def _flags():
    return {name: False for name in ("final_harmony_confirmed", "final_NCT_confirmed",
        "key_confirmed", "cadence_confirmed", "ranking_computed", "training_eligible",
        "generation_ready", "production_modified", "live_native_authority_claimed",
        "independent_completions_unioned", "all_logical_paths_evaluated")}


def _span(a, b):
    return {"start": q(a), "end": q(b)}


def _signature(origin):
    return {name: deepcopy(origin[name]) for name in ("root", "members")}


def _lookup(records, name):
    result = {}
    for record in records:
        key = record["record_id"]
        if key in result:
            raise ValueError("duplicate_" + name)
        result[key] = record
    return result


def _plain_ref(ref):
    if (type(ref) is not dict or set(ref) != {"record_id", "record_sha256"}
            or type(ref["record_id"]) is not str or type(ref["record_sha256"]) is not str
            or len(ref["record_sha256"]) != 64):
        raise ValueError("exact_saved_record_reference_required")


def _validate_clause(clause, path, role, origins, sounds, bundle):
    kernels._check(clause, "fmnroleclause_")
    if (clause["native_path_ref"] != kernels._ref(path)
            or clause["key_ref"] != path["key_ref"] or clause["bundle_ref"] != path["bundle_ref"]
            or clause["origin_refs"] != [kernels._ref(origins[i]) for i in clause["slot_indices"]]):
        raise ValueError("foreign_saved_role_clause_reference")
    source = [sounds[sid] for sid in clause["sound_refs"]]
    if (clause["source_note_refs"] != [n for s in source for n in s["source_note_refs"]]
            or clause["full_sound_spans"] != [s["span"] for s in source]):
        raise ValueError("saved_clause_source_closure_mismatch")
    actual = {tuple(edge) for edge in bundle["materialized_witness_links"]}
    if any(tuple(edge) not in actual for edge in clause["actual_required_links"]):
        raise ValueError("saved_clause_link_not_in_same_completion")
    unknown = bool(clause["blockers"])
    failed = sorted(k for k, v in clause["prerequisites"].items() if v is not True)
    truth = None if unknown else not failed
    if (clause["satisfied"] is not truth or clause["qualified"] is not (not unknown)
            or clause["failed_prerequisites"] != failed
            or clause["status"] != ("unassessed" if truth is None else "supported" if truth else "failed")):
        raise ValueError("saved_clause_truth_or_status_mismatch")
    clips_allowed = truth is True and clause.get("whole_ordinary_template_satisfied", True) is True
    if clause["clips"] != (clause["proposed_clips"] if clips_allowed else []):
        raise ValueError("saved_role_credit_prerequisites_mismatch")
    for clip in clause["proposed_clips"]:
        sound = sounds[clip["sound_ref"]]
        a, b = span_bounds(clip["span"])
        lo, hi = span_bounds(sound["span"])
        if clip["sound_ref"] not in clause["sound_refs"] or not lo <= a < b <= hi:
            raise ValueError("saved_credit_outside_source_sound")


def _validate_entry(entry, scope, lattice, origins_by_id, keys, bundles, sounds, cache):
    if type(entry) is not dict or set(entry) != {"native_path", "role_path", "comparison_ref", "explanation_ref"}:
        raise ValueError("closed_saved_contrast_entry_required")
    for name in ("comparison_ref", "explanation_ref"):
        _plain_ref(entry[name])
    path, role = entry["native_path"], entry["role_path"]
    kernels._check(path, "fmilpath_")
    kernels._check(path["logical_tuple"], "fmiltuple_")
    kernels._check(role, "fmnrolepath_")
    key = keys[path["key_ref"]["record_id"]]
    bundle = bundles[path["bundle_ref"]["record_id"]]
    if (path["scope_ref"] != kernels._ref(scope) or path["lattice_ref"] != kernels._ref(lattice)
            or path["key_ref"] != kernels._ref(key) or path["bundle_ref"] != kernels._ref(bundle)
            or role["native_path_ref"] != kernels._ref(path)
            or role["logical_tuple_ref"] != kernels._ref(path["logical_tuple"])
            or role["raw_account_pointer"] != {"parent_path_ref": kernels._ref(path),
                "field": "whole_path_account", "sha256": digest(path["whole_path_account"])}):
        raise ValueError("foreign_saved_path_or_account_pointer")
    identity = path["logical_tuple"]
    for name in ("scope_ref", "lattice_ref", "key_ref", "bundle_ref", "partition", "origin_refs"):
        if identity[name] != path[name]:
            raise ValueError("saved_logical_tuple_identity_mismatch")
    for name in ("partition", "origin_refs", "key_ref", "bundle_ref"):
        if role[name] != path[name]:
            raise ValueError("saved_role_path_identity_mismatch")
    if role["transition_assumptions"] != identity["transition_assumptions"]:
        raise ValueError("saved_transition_vector_mismatch")
    origins = [origins_by_id[ref["record_id"]] for ref in path["origin_refs"]]
    if path["origin_refs"] != [kernels._ref(o) for o in origins]:
        raise ValueError("saved_origin_digest_mismatch")
    lo, hi = span_bounds(scope["analysis_span"])
    cursor = lo
    if (not origins or len(path["partition"]) != len(origins)
            or len(path["profiles"]) != len(origins)
            or len(identity["transition_assumptions"]) != len(origins) - 1):
        raise ValueError("complete_saved_partition_required")
    for extent, origin, profile in zip(path["partition"], origins, path["profiles"]):
        a, b = span_bounds(extent)
        if a != cursor or b > hi or extent != origin["span"]:
            raise ValueError("noncontiguous_or_foreign_saved_partition")
        cursor = b
        if origin["record_id"] not in cache:
            cache[origin["record_id"]] = kernels._profile(scope, origin)
        if profile != cache[origin["record_id"]]:
            raise ValueError("saved_raw_profile_disagrees_with_source")
    if cursor != hi:
        raise ValueError("saved_partition_does_not_cover_full_scope")
    if path["whole_path_account"] != native._account(scope, path["profiles"]):
        raise ValueError("saved_native_raw_account_disagrees_with_source")
    assessed = role["status"] == "assessed_same_completion"
    if role["status"] not in ("assessed_same_completion", "unassessed_completion"):
        raise ValueError("closed_saved_role_status_required")
    if assessed and (scope["context_sound_inventory_complete"] is not True
            or bundle["status"] != "complete_all_lane_witness"):
        raise ValueError("incomplete_source_or_completion_cannot_be_assessed")
    if not assessed and role["clauses"]:
        raise ValueError("unassessed_completion_cannot_emit_role_clauses")
    for clause in role["clauses"]:
        _validate_clause(clause, path, role, origins, sounds, bundle)
    fresh_account = roles._account(path, origins, sounds, role["clauses"], assessed)
    if role["account"] != fresh_account:
        raise ValueError("saved_union_account_disagrees_with_source")
    for record in (path, role, identity):
        if any(record.get(name) is not None for name in ("selected", "rank", "confidence")):
            raise ValueError("saved_contrast_requires_unselected_hypotheses")
    return origins


def _category(sound, origin, state, credited, assessed):
    if origin["blockers"] or temporal._guard_codes(sound):
        return "source_or_hypothesis_unsupported"
    if state == "member":
        return "source_guarded_member"
    if state == "spelling_unresolved":
        return "membership_unknown"
    if not assessed:
        return "unassessed_nonmember"
    return "conditional_explained_nonmember" if credited else "unexplained_nonmember_under_this_completion"


def _facet(entry, scope, origins, sounds):
    path, role = entry["native_path"], entry["role_path"]
    credits = {r["sound_ref"]: r["spans"] for r in role["account"]["explained_intervals_by_sound"]}
    segments = defaultdict(list)
    presentations, cells = [], []
    for slot, (origin, profile) in enumerate(zip(origins, path["profiles"])):
        members = origin["members"]
        presentation = []
        for member in members or []:
            occurrences = [row for row in profile["rows"] if kernels._pitch_key(row["pitch"]) == kernels._pitch_key(member)
                and not kernels._source_blockers(sounds[row["sound_ref"]])
                and not temporal._guard_codes(sounds[row["sound_ref"]]) and not origin["blockers"]]
            presentation.append({"spelling": deepcopy(member),
                "first_guarded_observed_time": q(min(f(r["observed_span"]["start"]) for r in occurrences)) if occurrences else None,
                "source_note_time_quarters": q(sum((f(r["observed_span"]["end"]) - f(r["observed_span"]["start"])
                    for r in occurrences), Fraction())), "sound_refs": [r["sound_ref"] for r in occurrences],
                "observations": [{"sound_ref": row["sound_ref"], "source_note_refs": deepcopy(sounds[row["sound_ref"]]["source_note_refs"]),
                    "full_sound_span": deepcopy(row["full_span"]), "observed_span": deepcopy(row["observed_span"]),
                    "attack_note_ref": sounds[row["sound_ref"]]["attack_note_ref"],
                    "tie_chain_ref": sounds[row["sound_ref"]]["tie_chain_ref"],
                    "attack_before_slot": f(row["full_span"]["start"]) < f(origin["span"]["start"])} for row in occurrences]})
        presentations.append({"slot_index": slot, "origin_ref": kernels._ref(origin),
            "span": deepcopy(origin["span"]), **_signature(origin), "members": deepcopy(members),
            "member_presentations": presentation, "required_member_count": None if members is None else len(members),
            "missing_guarded_spellings": None if members is None else
                [r["spelling"] for r in presentation if r["first_guarded_observed_time"] is None],
            "pooled_support_is_not_arpeggio_confirmation": True})
        for cell in profile["cells"]:
            strict = {kernels._pitch_key(sounds[sid]["pitch"]) for sid in cell["sound_refs"]
                if not kernels._source_blockers(sounds[sid]) and not temporal._guard_codes(sounds[sid])}
            cells.append({"slot_index": slot, "origin_ref": kernels._ref(origin), **deepcopy(cell),
                "strict_guard_missing_spellings": None if members is None or origin["blockers"] else
                    [deepcopy(p) for p in members if kernels._pitch_key(p) not in strict],
                "strict_bass_source_guards_passed": None if not cell["bass_refs"] else all(
                    not kernels._source_blockers(sounds[sid]) and not temporal._guard_codes(sounds[sid]) for sid in cell["bass_refs"])})
        for row in profile["rows"]:
            sid = row["sound_ref"]
            lo, hi = span_bounds(row["observed_span"])
            points = sorted({lo, hi} | {v for clip in credits.get(sid, []) for v in span_bounds(clip) if lo < v < hi})
            for a, b in zip(points, points[1:]):
                credited = any(x <= a < b <= y for x, y in map(span_bounds, credits.get(sid, [])))
                clauses = [kernels._ref(c) for c in role["clauses"] if any(clip["sound_ref"] == sid
                    and f(clip["span"]["start"]) <= a < b <= f(clip["span"]["end"]) for clip in c["clips"])]
                segments[sid].append({"span": _span(a, b), "slot_index": slot, "origin_ref": kernels._ref(origin),
                    "raw_state": row["state"], "category": _category(sounds[sid], origin, row["state"], credited,
                        role["status"] == "assessed_same_completion"), "credited_clause_refs": clauses})
    totals = {category: Fraction() for category in CATEGORIES}
    for rows in segments.values():
        for row in rows:
            a, b = span_bounds(row["span"])
            totals[row["category"]] += b - a
    if {k: q(v) for k, v in totals.items()} != role["account"]["note_time_quarters"]:
        raise ValueError("source_aligned_category_totals_do_not_match_account")
    return {"native_path_ref": kernels._ref(path), "role_path_ref": kernels._ref(role),
        "comparison_ref": deepcopy(entry["comparison_ref"]), "explanation_ref": deepcopy(entry["explanation_ref"]),
        "key_ref": deepcopy(path["key_ref"]), "bundle_ref": deepcopy(path["bundle_ref"]),
        "partition": deepcopy(path["partition"]), "transition_assumptions": deepcopy(role["transition_assumptions"]),
        "account": deepcopy(role["account"]), "slot_presentations": presentations, "bass_cells": cells,
        "cut_signature_observations": [{"time": deepcopy(right["span"]["start"]),
            "same_assumed_ordered_root_members": _signature(left) == _signature(right),
            "left_origin_ref": kernels._ref(left), "right_origin_ref": kernels._ref(right),
            "same_signature_is_not_harmonic_boundary_verdict": True} for left, right in zip(origins, origins[1:])],
        "source_segments": dict(segments), "ordinary_templates": deepcopy(role["ordinary_templates"]),
        "transition_context_refs": [kernels._ref(r) for r in path["transition_contexts"]],
        "actual_transition_evidence": [{"context_ref": kernels._ref(r),
            "function_shape": deepcopy(r["function_shape"]), "ordinary_strategy": deepcopy(r["ordinary_strategy"]),
            "joint_conditional_functional_evidence": deepcopy(r["joint_conditional_functional_evidence"]),
            "prerequisite_axes": deepcopy(r.get("prerequisite_axes")),
            "profile_literal_evidence": deepcopy(r.get("profile_literal_evidence"))}
            for r in path["transition_contexts"]],
        "boundary_contexts": [{"boundary_time": deepcopy(r["boundary_time"]),
            "function_context_ref": deepcopy(r["function_context_ref"]),
            "cadence_prerequisites": deepcopy(r["cadence_prerequisites"]),
            "same_raw_lane_transitions": deepcopy(r["same_raw_lane_transitions"])} for r in path["boundaries"]],
        "all_declared_functional_prerequisites_under_same_bundle": path["all_declared_functional_prerequisites_under_same_bundle"],
        "all_transitions_functionally_assessed": path["all_transitions_functionally_assessed"],
        "selected": None, "rank": None, "confidence": None}


def _cover(rows, a, b):
    matches = [r for r in rows if f(r["span"]["start"]) <= a < b <= f(r["span"]["end"])]
    if len(matches) != 1:
        raise ValueError("exact_single_source_aligned_cover_required")
    return matches[0]


def _kind(left, right):
    if left["partition"] != right["partition"]:
        return "partition"
    vector_same = left["transition_assumptions"] == right["transition_assumptions"]
    signature_same = [_signature(s) for s in left["slot_presentations"]] == [_signature(s) for s in right["slot_presentations"]]
    return "candidate_only" if vector_same else "transition_only" if signature_same else "candidate_and_transition"


def _pair(left, right, sounds):
    transitions = Counter()
    differences = []
    if set(left["source_segments"]) != set(right["source_segments"]):
        raise ValueError("competitors_do_not_cover_same_source_sounds")
    for sid, lrows in sorted(left["source_segments"].items()):
        rrows = right["source_segments"][sid]
        points = sorted({v for row in lrows + rrows for v in span_bounds(row["span"])})
        for a, b in zip(points, points[1:]):
            lrow, rrow = _cover(lrows, a, b), _cover(rrows, a, b)
            transitions[(lrow["category"], rrow["category"])] += b - a
            if lrow["category"] != rrow["category"]:
                differences.append({"sound_ref": sid, "source_note_refs": deepcopy(sounds[sid]["source_note_refs"]),
                    "pitch": deepcopy(sounds[sid]["pitch"]), "full_sound_span": deepcopy(sounds[sid]["span"]),
                    "span": _span(a, b), "left": deepcopy(lrow), "right": deepcopy(rrow)})
    raw = f(left["account"]["raw_total_note_time_quarters"])
    if raw != f(right["account"]["raw_total_note_time_quarters"]) or sum(transitions.values(), Fraction()) != raw:
        raise ValueError("pairwise_raw_note_time_not_conserved")
    points = sorted({v for row in left["bass_cells"] + right["bass_cells"] for v in span_bounds(row["span"])})
    bass = []
    for a, b in zip(points, points[1:]):
        lcell, rcell = _cover(left["bass_cells"], a, b), _cover(right["bass_cells"], a, b)
        if lcell["sound_refs"] != rcell["sound_refs"] or lcell["bass_refs"] != rcell["bass_refs"]:
            raise ValueError("aligned_raw_bass_observations_changed_between_candidates")
        fields = ("origin_ref", "slot_index", "bass_membership_status", "conditional_inversions",
            "conditional_bass_member_indices", "inversion_basis", "source_guard_missing_spellings", "bass_source_guards_passed",
            "strict_guard_missing_spellings", "strict_bass_source_guards_passed")
        bass.append({"span": _span(a, b), "bass_refs": deepcopy(lcell["bass_refs"]),
            "left": {k: deepcopy(lcell[k]) for k in fields}, "right": {k: deepcopy(rcell[k]) for k in fields},
            "bass_is_not_certified_structural_bass": True})
    def cut_map(facet):
        return {f(slot["start"]): vector for slot, vector in zip(facet["partition"][1:], facet["transition_assumptions"])}
    lcuts, rcuts = cut_map(left), cut_map(right)
    common = sorted(lcuts.keys() & rcuts.keys())
    alias = (left["partition"] == right["partition"] and
        [_signature(s) for s in left["slot_presentations"]] == [_signature(s) for s in right["slot_presentations"]] and
        left["transition_assumptions"] == right["transition_assumptions"])
    return {"left_path_ref": left["native_path_ref"], "right_path_ref": right["native_path_ref"],
        "left_role_path_ref": left["role_path_ref"], "right_role_path_ref": right["role_path_ref"],
        "key_ref": left["key_ref"], "bundle_ref": left["bundle_ref"], "comparison_kind": _kind(left, right),
        "same_partition": left["partition"] == right["partition"], "alias_control": alias,
        "shared_cut_assumptions": [{"time": q(t), "left": deepcopy(lcuts[t]), "right": deepcopy(rcuts[t]),
            "same_assumption": lcuts[t] == rcuts[t]} for t in common],
        "left_only_cuts": [q(t) for t in sorted(lcuts.keys() - rcuts.keys())],
        "right_only_cuts": [q(t) for t in sorted(rcuts.keys() - lcuts.keys())],
        "raw_total_note_time_quarters": q(raw), "raw_time_conserved": True,
        "note_time_delta_right_minus_left": {k: q(f(right["account"]["note_time_quarters"][k]) -
            f(left["account"]["note_time_quarters"][k])) for k in CATEGORIES},
        "category_transfer_note_time": [{"left": a, "right": b, "duration_quarters": q(value)}
            for (a, b), value in sorted(transitions.items())],
        "changed_source_segments": differences, "aligned_bass_cells": bass,
        "selected": None, "rank": None, "confidence": None,
        "interpretation": "conditional_evidence_contrast_not_chord_selection"}


def _plan(scope, entries, pair_indices):
    """Charge inner cover/credit scans and repeated source-reference copies.

    Entry lengths are inspected, not role predicates. Counts bound the emitted
    refinements even if every observed row crosses every credited clip end.
    Identity seals/JSON byte admission remain the saved reader's separate cap.
    """
    n = len(scope["sound_facts"])
    refs = {s["sound_ref"]: len(s["source_note_refs"]) for s in scope["sound_facts"]}
    descriptions, work = [], 0
    for entry in entries:
        path, role = entry["native_path"], entry["role_path"]
        rows = Counter(r["sound_ref"] for p in path["profiles"] for r in p["rows"])
        unions = {r["sound_ref"]: len(r["spans"]) for r in role["account"]["explained_intervals_by_sound"]}
        clip_refs = Counter(clip["sound_ref"] for c in role["clauses"] for clip in c["clips"])
        clip_count = sum(clip_refs.values())
        atoms = {sid: count * (1 + 2 * unions.get(sid, 0)) for sid, count in rows.items()}
        cell_count = sum(len(p["cells"]) for p in path["profiles"])
        member_count = max((len(cell["missing_spellings"] or []) + len(cell["sound_refs"])
            for p in path["profiles"] for cell in p["cells"]), default=0)
        # Conservative source/profile/membership cell scans, charged per entry
        # even though identical origin profiles are cached during validation.
        work += len(path["profiles"]) * 4 * (n + 1) * (n + member_count + sum(refs.values()) + 1)
        work += sum(len(c["sound_refs"]) + len(c["source_note_refs"]) + len(c["actual_required_links"])
                    + len(c["proposed_clips"]) + len(c["prerequisites"]) + 1 for c in role["clauses"])
        work += (clip_count + 1) ** 2  # per-sound union sorting and closure
        for sid, count in rows.items():
            # Presentation copies, account clipping, facet clause-clip scan.
            work += count * (member_count + refs.get(sid, 0) + 1)
            # Even failed/unassessed clauses with clips=[] incur an outer visit
            # in each atom's attribution scan; count these separately from clips.
            work += atoms[sid] * (unions.get(sid, 0) + len(role["clauses"]) + clip_count + refs.get(sid, 0) + 1)
        descriptions.append({"atoms": atoms, "clip_refs": clip_refs, "cells": cell_count})
    pair_work = 0
    for i, j in pair_indices:
        left, right = descriptions[i], descriptions[j]
        for sid in left["atoms"].keys() | right["atoms"].keys():
            covers = left["atoms"].get(sid, 0) + right["atoms"].get(sid, 0)
            endpoints = 2 * covers
            # Each refinement calls _cover twice (linear scans), then copies
            # both attributed rows and the original source closure if changed.
            pair_work += endpoints * (covers + left["clip_refs"][sid] + right["clip_refs"][sid]
                + refs.get(sid, 0) + 8)
        cells = left["cells"] + right["cells"]
        pair_work += 2 * cells * (cells + sum(refs.values()) + 12)
    return {"planned_pairs": len(pair_indices), "planned_work": work + pair_work,
        "entry_count": len(entries), "entry_validation_and_facet_work": work,
        "pair_refinement_cover_and_reference_work": pair_work,
        "semantics": "saved_evidence_work_bound_not_CPU_time_or_accuracy"}


def compare(scope, lattice, entries, *, bundles, max_pairs=2000, work_budget=2000000):
    """Contrast all submitted same-key/same-bundle pairs, or hold the WHOLE request.

    Seals check saved content identity; the caller must validate creation hashes
    and parent membership. They are never live issuer authentication.
    """
    for name, value in (("max_pairs", max_pairs), ("work_budget", work_budget)):
        native._integer(value, name)
    if type(entries) is not list or len(entries) > 256 or type(bundles) is not dict:
        raise ValueError("bounded_saved_entry_list_and_bundle_map_required")
    before = digest([scope, lattice, entries, bundles])
    kernels._check(scope, "fmes_")
    kernels._check(lattice, native.PREFIX)
    if lattice["scope_ref"] != kernels._ref(scope) or lattice["binding"] != scope["binding"]:
        raise ValueError("saved_scope_lattice_binding_mismatch")
    for key, bundle in bundles.items():
        kernels._check(bundle, native.BUNDLE_PREFIX)
        if key != bundle["record_id"] or bundle["scope_ref"] != kernels._ref(scope) or bundle["binding"] != scope["binding"]:
            raise ValueError("foreign_saved_completion")
    groups = defaultdict(list)
    for i, entry in enumerate(entries):
        path = entry["native_path"]
        groups[(digest(path["key_ref"]), digest(path["bundle_ref"]))].append(i)
    pair_indices = [pair for group in groups.values() for pair in combinations(group, 2)]
    n = len(scope["sound_facts"])
    plan = _plan(scope, entries, pair_indices)
    reasons = []
    if len(pair_indices) > max_pairs:
        reasons.append("whole_pair_count_exceeds_budget_no_prefix")
    if plan["planned_work"] > work_budget:
        reasons.append("whole_contrast_work_exceeds_budget_no_prefix")
    origins = _lookup([o for catalog in lattice["catalog_inventory"] for o in catalog["origins"]], "origin") if not reasons else {}
    keys = _lookup(lattice["keys"], "key") if not reasons else {}
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    if len(sounds) != n:
        raise ValueError("duplicate_source_sound_reference")
    facets, pairs, cache, seen = [], [], {}, set()
    if not reasons:
        for entry in entries:
            path = entry["native_path"]
            identity = (digest(path["logical_tuple"]), digest(path["bundle_ref"]))
            if identity in seen:
                raise ValueError("duplicate_saved_complete_hypothesis")
            seen.add(identity)
            chosen = _validate_entry(entry, scope, lattice, origins, keys, bundles, sounds, cache)
            facets.append(_facet(entry, scope, chosen, sounds))
        pairs = [_pair(facets[i], facets[j], sounds) for i, j in pair_indices]
    counts = Counter(pair["comparison_kind"] for pair in pairs)
    result = kernels._seal({"version": VERSION, "source_authority": AUTHORITY,
        "scope_ref": kernels._ref(scope), "lattice_ref": kernels._ref(lattice),
        "binding": deepcopy(scope["binding"]), "analysis_span": deepcopy(scope["analysis_span"]),
        "logical_universe": deepcopy(lattice["universe"]), "query_plan": plan,
        "resource_limits": {"max_pairs": max_pairs, "work_budget": work_budget},
        "submitted_entry_refs": [{"native_path_ref": kernels._ref(e["native_path"]),
            "role_path_ref": kernels._ref(e["role_path"]), "comparison_ref": deepcopy(e["comparison_ref"]),
            "explanation_ref": deepcopy(e["explanation_ref"])} for e in entries],
        "facets": facets, "pairs": pairs,
        "summary": {"submitted_entries": len(entries), "planned_same_key_same_bundle_pairs": len(pair_indices),
            "computed_pairs": len(pairs), "withheld_pairs": len(pair_indices) - len(pairs),
            "candidate_only_pairs": counts["candidate_only"], "transition_only_pairs": counts["transition_only"],
            "candidate_and_transition_pairs": counts["candidate_and_transition"], "partition_pairs": counts["partition"],
            "alias_control_pairs": sum(pair["alias_control"] for pair in pairs),
            "raw_time_conserved_entries": len(facets), "pair_kind_counts": dict(sorted(counts.items()))},
        "status": "whole_saved_contrast_hold" if reasons else "computed_saved_progression_contrasts_not_selected",
        "reasons": reasons, "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "limitations": ["Saved role predicates are archived conditional evidence, not independently re-inferred NCT.",
            "Membership, pooled coverage, number of explained notes and extra cuts do not select a harmony.",
            "Partition/transition differences are marked; only candidate_only is a strict fixed-premise contrast.",
            "No cross-key or cross-completion winner, cadence, modulation or generation certification.",
            "Unsubmitted native paths and other fixed-grid partitions remain unevaluated."]}, PREFIX)
    if before != digest([scope, lattice, entries, bundles]):
        raise ValueError("saved_contrast_inputs_modified_during_calculation")
    return result
