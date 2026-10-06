"""Music-facing, non-selecting review of frozen progression evidence.

Saved evidence is not live native authority. Literal projections are rechecked
by the frozen policy validator; role predicates remain archived conditional
evidence. No explanation count, pooled pitch coverage or nominal cadence votes
become a winner, confidence, annotation or training label here.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction

from . import factor_expanded_hypotheses as sealed
from . import lossless_json_dag_v2 as dag
from . import native_progression_contrast as parent
from . import native_progression_policy as policy
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "progression-evidence-review-0.1.0"


def _tri(value):
    if value is not None and type(value) is not bool:
        raise ValueError("exact_tri_truth_required")
    return value


def review_facet(facet, key):
    """Project already validated archived evidence into independent axes.

    This pure projection is NOT a public authenticity/validation gate. The
    archive adapter below checks source, references and literal arithmetic.
    """
    if any(facet[k] is not None for k in ("selected", "rank", "confidence")):
        raise ValueError("unselected_archived_evidence_required")
    cats = facet["account"]["note_time_quarters"]
    if set(cats) != set(parent.CATEGORIES):
        raise ValueError("closed_note_time_categories_required")
    values = {c: f(v) for c, v in cats.items()}
    raw = f(facet["account"]["raw_total_note_time_quarters"])
    if any(v < 0 for v in values.values()) or sum(values.values(), Fraction()) != raw:
        raise ValueError("conserved_nonnegative_note_time_required")
    unresolved = sum((values[c] for c in parent.CATEGORIES[2:]), Fraction())
    known_key = bool(key["segments"]) and all(
        s["tonic"] is not None and s["mode"] != "unknown" for s in key["segments"])
    slots = []
    for s in facet["slot_presentations"]:
        missing = s["missing_guarded_spellings"]
        root_seen = None if s["root"] is None else any(
            p["spelling"] == s["root"] and p["first_guarded_observed_time"] is not None
            for p in s["member_presentations"])
        cells = [c for c in facet["bass_cells"] if c["slot_index"] == s["slot_index"]]
        # Silence is not an absent chord member; only active cells contribute.
        active = [c for c in cells if not c["silence"]]
        simultaneous = any(c["strict_guard_missing_spellings"] == [] for c in active)
        bass = [{"span": c["span"], "sound_refs": c["bass_refs"],
                 "member_indices": c["conditional_bass_member_indices"],
                 "conditional_inversions": c["conditional_inversions"],
                 "inversion_basis": c["inversion_basis"],
                 "membership_status": c["bass_membership_status"],
                 "source_guard": c["strict_bass_source_guards_passed"]} for c in cells]
        slots.append({"slot_index": s["slot_index"], "origin_ref": s["origin_ref"],
            "span": s["span"], "root": s["root"], "members": s["members"],
            "guarded_root_observed": root_seen,
            "missing_guarded_spellings": missing,
            "constituent_state": "unassessed" if missing is None else
                "missing_requires_additional_evidence" if missing else "all_observed_over_span",
            "all_members_simultaneously_observed_in_some_active_cell": simultaneous,
            "pooled_without_simultaneous_core": missing == [] and not simultaneous,
            "pooled_presence_confirms_arpeggio_or_hold": False,
            "member_observations": s["member_presentations"], "literal_bass_timeline": bass})
    transitions = []
    for i, (assumption, ev, template) in enumerate(zip(facet["transition_assumptions"],
            facet["actual_transition_evidence"], facet["ordinary_templates"])):
        joint, whole = _tri(ev["joint_conditional_functional_evidence"]), _tri(template["satisfied"])
        axes = ev["prerequisite_axes"]
        if axes is not None:
            for value in axes.values():
                _tri(value)
        shape_conflicts = [] if axes is None else [a for a in (
            "source_shape_compatible", "target_triad_core_shape_compatible") if axes[a] is False]
        roles = [] if ev["ordinary_strategy"] is None else ev["ordinary_strategy"]["role_assessments"]
        individual = any(r["satisfied_under_this_bundle"] is True for r in roles)
        state = ("undeclared" if assumption is None else "declared_shape_conflict" if shape_conflicts
                 else "conditional_joint_supported" if joint is True and whole is True
                 else "held_under_same_completion")
        transitions.append({"cut_index": i, "time": facet["partition"][i + 1]["start"],
            "assumption": assumption, "context_ref": ev["context_ref"], "state": state,
            "shape_conflicts": shape_conflicts, "prerequisite_axes": axes,
            "joint_support": joint, "whole_ordinary_template_support": whole,
            "individual_role_support_without_whole_template": individual and whole is not True,
            "role_assessments": roles,
            "function_shape": ev["function_shape"],
            "shape_conflict_rejects_all_chord_interpretations": False})
    cadences = []
    for boundary in facet["boundary_contexts"]:
        for family, c in sorted(boundary["cadence_prerequisites"].items()):
            nominal = _tri(c["nominal_harmonic_and_literal_extreme_prerequisites"])
            if c["confirmed"] is not False or c["nominal_prerequisites_are_cadence_confirmation"] is not False:
                raise ValueError("nominal_cadence_cannot_be_confirmed")
            cadences.append({"time": boundary["boundary_time"], "family": family,
                "nominal_prerequisites": nominal, "missing_semantic_premises": c["missing_premises"],
                "status": "held_missing_semantic_premises", "confirmed": False,
                "literal_prerequisite_axes": c["literal_prerequisite_axes"]})
    issues = []
    def issue(rule, reason):
        issues.append({"rule_id": rule, "reason": reason})
    if values["membership_unknown"] or values["source_or_hypothesis_unsupported"]:
        issue("ER01", "source_or_spelling_uncertainty")
    if not known_key:
        issue("ER02", "key_coordinate_unknown_not_signature_proof")
    if any(s["missing_guarded_spellings"] is None or s["missing_guarded_spellings"] for s in slots):
        issue("ER03", "missing_constituents_need_omission_or_redistribution_evidence")
    if any(s["pooled_without_simultaneous_core"] for s in slots):
        issue("ER04", "pooled_members_need_temporal_harmony_test_not_vertical_gate")
    if unresolved:
        issue("ER05", "nonmembers_or_source_time_still_unresolved")
    if transitions and any(t["state"] != "conditional_joint_supported" for t in transitions):
        issue("ER06", "declared_progression_not_fully_supported")
    if any(t["individual_role_support_without_whole_template"] for t in transitions):
        issue("ER06", "individual_resolution_does_not_establish_whole_template")
    if any(c["same_assumed_ordered_root_members"] for c in facet["cut_signature_observations"]):
        issue("ER07", "same_signature_cut_needs_independent_boundary_evidence")
    if any(c["nominal_prerequisites"] is True for c in cadences):
        issue("ER08", "nominal_cadence_needs_key_structural_voice_and_closure_evidence")
    zero_unresolved_missing = not unresolved and any(s["missing_guarded_spellings"] for s in slots)
    if zero_unresolved_missing:
        issue("ER09", "zero_unresolved_time_does_not_establish_missing_member_chord")
    return {"version": VERSION, "entry_refs": {k: facet[k] for k in (
        "native_path_ref", "role_path_ref", "comparison_ref", "explanation_ref")},
        "fixed_premise_id": digest([facet["key_ref"], facet["bundle_ref"],
            facet["partition"], facet["transition_assumptions"]]),
        "key_ref": facet["key_ref"], "bundle_ref": facet["bundle_ref"],
        "key_coordinate_available": known_key, "key_inferred": False,
        "partition": facet["partition"], "note_time_account": facet["account"],
        "unresolved_note_time_quarters": q(unresolved), "slots": slots,
        "transitions": transitions, "cadence_candidates": cadences, "issues": issues,
        "no_internal_transition_is_not_hold_failure": not transitions,
        "zero_unresolved_time_with_missing_constituents": zero_unresolved_missing,
        "evidence_dependence_groups": {
            "same_source_membership": ["raw_membership", "pooled_presence", "note_time_account"],
            "same_completion_resolution": ["individual_roles", "whole_template", "joint_support"],
            "same_boundary_context": ["nominal_cadence", "literal_extremes"]},
        "status": "reviewed_conditional_evidence_not_selected",
        "selected": None, "rank": None, "confidence": None, "flags": parent._flags()}


def review_catalog(catalog, source):
    """Read an externally pinned codec exchange, not a restored capability.

    Import validates the typed lossless DAG. Existing literal validator checks
    raw membership, coverage, attack/tie, bass, function and credit arithmetic.
    Cadence premises and role predicates are still archived, not re-inferred.
    """
    if catalog["source_catalog_ref"] != sealed._ref(source):
        raise ValueError("foreign_saved_source_catalog")
    scope, lattice, bundles = source["source_scope"], source["lattice"], source["bundles"]
    keys = parent._lookup(lattice["keys"], "review_key")
    origins = parent._lookup([o for c in lattice["catalog_inventory"] for o in c["origins"]], "review_origin")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    if len(sounds) != len(scope["sound_facts"]):
        raise ValueError("duplicate_review_source_sound")
    cache = {"profiles": {}, "guards": {sid: {
        "strict": not sealed._source_blockers(s) and not parent.temporal._guard_codes(s),
        "role_blocked": bool(parent.temporal._guard_codes(s))} for sid, s in sounds.items()}}
    handle = dag.import_record(catalog["payload"])
    group = catalog["group"]
    count = len(group["entry_refs"])
    if (count != len(catalog["pair_index"]) or count != len(group["original_selector_indices"])
            or count != len(catalog["all_original_facet_roots"])):
        raise ValueError("complete_ordered_catalog_inventory_required")
    rows, summary = [], Counter()
    for i, ref in enumerate(group["entry_refs"]):
        facet = dag.value_at(handle, ("facets", i))
        if (dag.node_at(handle, ("facets", i)) != catalog["all_original_facet_roots"][i]
                or facet["key_ref"] != group["key_ref"] or facet["bundle_ref"] != group["bundle_ref"]
                or {k: facet["account"][k] for k in catalog["pair_index"][i]["account"]}
                    != catalog["pair_index"][i]["account"]):
            raise ValueError("catalog_facet_binding_mismatch")
        key = policy._validate_facet(facet, ref, scope, keys, bundles, origins, sounds, cache)
        row = review_facet(facet, key)
        row.update(entry_index=i, original_selector_index=group["original_selector_indices"][i],
                   catalog_ref=sealed._ref(catalog), source_facet_pointer=["facets", i])
        for issue in row["issues"]:
            summary[issue["reason"]] += 1
        summary["reviewed_candidates"] += 1
        summary["zero_unresolved_time_with_missing_constituents"] += row["zero_unresolved_time_with_missing_constituents"]
        summary["all_internal_transitions_conditionally_supported"] += bool(row["transitions"]) and all(
            t["state"] == "conditional_joint_supported" for t in row["transitions"])
        summary["nominal_cadence_occurrences_not_verdicts"] += sum(
            c["nominal_prerequisites"] is True for c in row["cadence_candidates"])
        rows.append(row)
    return {"version": VERSION, "catalog_ref": sealed._ref(catalog),
        "source_catalog_ref": sealed._ref(source), "group": deepcopy(group),
        "key_hypothesis": deepcopy(keys[group["key_ref"]["record_id"]]),
        "summary": dict(summary), "candidate_reviews": rows,
        "selected": None, "rank": None, "confidence": None, "flags": parent._flags()}


def audit_pair_block(block, catalog, *, task):
    """Check complete ordered pair coverage and independent rational margins.

    Frozen pair pointers are retained in their original block; this does not
    replay pointer materialization, role predicates or the pair producer.
    """
    for field, expected in (("catalog_ref", sealed._ref(catalog)),
            ("source_catalog_ref", catalog["source_catalog_ref"]), ("group_ref", catalog["group_ref"]),
            ("refinement_sha256", catalog["refinement_sha256"]),
            ("entry_inventory_sha256", catalog["entry_inventory_sha256"]), ("task", task)):
        if block[field] != expected:
            raise ValueError("foreign_review_pair_block:" + field)
    expected = [(i, j) for i in range(task["row_start"], task["row_end"])
        for j in range(task["column_start"], task["column_end"]) if i < j]
    if (block["status"] != "computed_saved_block_not_selected" or block["reasons"]
            or block["computed_pairs"] != task["expected_pairs"] or block["withheld_pairs"] != 0
            or len(expected) != len(block["pairs"]) or block["planned_pairs"] != len(expected)):
        raise ValueError("whole_complete_pair_block_required")
    counts = Counter()
    for indices, pair in zip(expected, block["pairs"]):
        if pair["entry_indices"] != list(indices):
            raise ValueError("complete_original_pair_order_required")
        i, j = indices
        for field in ("catalog_ref", "source_catalog_ref", "group_ref", "refinement_sha256"):
            if pair[field] != block[field]:
                raise ValueError("pair_reference_disagrees_with_block")
        if (pair["original_selector_indices"] != [catalog["group"]["original_selector_indices"][k] for k in indices]
                or pair["raw_time_conserved"] is not True
                or any(pair[k] is not None for k in ("selected", "rank", "confidence", "musical_outcome"))):
            raise ValueError("original_unselected_conserved_pair_required")
        left, right = (catalog["pair_index"][k] for k in indices)
        partition = left["partition_node"] == right["partition_node"]
        vector = left["transition_node"] == right["transition_node"]
        signatures = left["signature_nodes"] == right["signature_nodes"]
        kind = "partition" if not partition else "candidate_only" if vector else "transition_only" if signatures else "candidate_and_transition"
        if (pair["comparison_kind"] != kind or pair["same_partition"] is not partition
                or pair["alias_control"] is not (partition and vector and signatures)):
            raise ValueError("pair_comparison_premises_mismatch")
        margins = {side: {c: Fraction() for c in parent.CATEGORIES} for side in ("left", "right")}
        for transfer in pair["category_transfer_note_time"]:
            dur = f(transfer["duration_quarters"])
            if dur <= 0:
                raise ValueError("positive_category_transfer_required")
            for side in margins:
                margins[side][transfer[side]] += dur
        for side, record in (("left", left), ("right", right)):
            account = record["account"]
            if (margins[side] != {c: f(account["note_time_quarters"][c]) for c in parent.CATEGORIES}
                    or f(pair["raw_total_note_time_quarters"]) != f(account["raw_total_note_time_quarters"])):
                raise ValueError("pair_transfer_source_margin_mismatch")
        delta = {c: q(margins["right"][c] - margins["left"][c]) for c in parent.CATEGORIES}
        lc, rc = (v["account"]["conditional_explanation_note_time_quarters"] for v in (left, right))
        credit = None if lc is None or rc is None else q(f(rc) - f(lc))
        if pair["note_time_delta_right_minus_left"] != delta or pair["conditional_credit_delta_right_minus_left"] != credit:
            raise ValueError("pair_rational_delta_mismatch")
        counts[kind] += 1
        counts["alias_controls"] += pair["alias_control"]
        counts["same_accounts_different_signature_or_partition"] += left["account"] == right["account"] and (not signatures or not partition)
    return {"audited_pairs": len(expected), "pair_kind_counts": dict(counts),
        "musical_winner_inferred": False, "producer_replayed": False}
