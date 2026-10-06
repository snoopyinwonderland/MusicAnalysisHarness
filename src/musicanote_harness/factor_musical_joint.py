"""Joint direct-edge hypotheses and same-completion musical accounts.

No independent witnesses, OR counts, or explanation durations are summed.
The voice completion and harmonic members are explicit research assumptions;
these records do not choose voices, harmony, NCT, or generative roles.
"""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations, product
import json
import math

from . import harmony_factorized_voice_paths as factors
from . import factor_musical_view as views
from . import factor_musical_rules as compiler
from .musical_pattern_observation import digest

VERSION = "factor-musical-joint-0.1.0"
CATEGORIES = ("member", "conditional_explained", "unexplained", "unknown", "unsupported")
RAW = ("member", "nonmember", "unknown")


def _flags():
    return {"selected": None, "preferred": None, "confidence_generated": False,
            "musical_accuracy_measured": False, "harmony_confirmed": False,
            "nct_confirmed": False, "arpeggio_confirmed": False, "pedal_confirmed": False,
            "structural_bass_confirmed": False, "function_confirmed": False,
            "cadence_confirmed": False, "training_eligible": False,
            "gold_eligible": False, "generation_ready": False,
            "production_modified": False, "source_annotations_used": False,
            "legacy_assignment_inventory_inserted": False}


def _budget(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("invalid_nonnegative_budget:" + name)


def _edge_set(rows):
    if not isinstance(rows, (list, tuple)):
        raise ValueError("explicit_direct_edge_list_required")
    result = set()
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 2 or any(
                not isinstance(x, str) or not x for x in row):
            raise ValueError("malformed_direct_edge")
        result.add(tuple(row))
    return result


def _rules(rows):
    if not isinstance(rows, (list, tuple)):
        raise ValueError("explicit_requested_rule_list_required")
    ids = set()
    for row in rows:
        rid = row.get("rule_id")
        if not isinstance(rid, str) or not rid or rid in ids:
            raise ValueError("missing_or_duplicate_requested_rule_id")
        ids.add(rid)
        if row.get("status") not in ("conditional_shape", "withheld"):
            raise ValueError("unsupported_rule_status")
        if not isinstance(row.get("blockers"), list) or not isinstance(row.get("alternatives"), list):
            raise ValueError("malformed_rule_contract")
        for alternative in row["alternatives"]:
            if set(alternative) != {"required_links", "forbidden_links"}:
                raise ValueError("unsupported_link_alternative_fields")
            _edge_set(alternative["required_links"])
            _edge_set(alternative["forbidden_links"])


def solve_joint(graph, rule_records, *, branch_budget=256, work_budget=100000):
    """Solve an explicit requested subset, NOT all inventory rules by default.

    Rule rows are caller hypotheses here. Only compare's fresh compiler replay
    validates their musical prerequisites. Branches retain individual exact
    geometry counts; their overlapping unions are deliberately not counted.
    """
    before = digest([graph, rule_records])
    factors._graph(graph)
    _budget(branch_budget, "branch_budget")
    _budget(work_budget, "work_budget")
    _rules(rule_records)
    count = math.prod(len(row["alternatives"]) for row in rule_records)
    body = {"version": VERSION, "graph_ref": views.ref(graph),
            "requested_rules": json.loads(json.dumps(list(rule_records))),
            "requested_rules_content_sha256": digest(list(rule_records)),
            "branch_budget": branch_budget, "work_budget_per_query": work_budget,
            "possible_branch_count": factors._decimal(count), "branches": [],
            "status": "unassessed", "reasons": [], "all_requested_branches_assessed": False,
            "rule_payload_semantics": "explicit_caller_hypotheses_not_independently_compiled_here",
            "constraint_semantics": "AND_of_requested_rules_OR_of_each_rules_direct_link_alternatives",
            "possible_assignments_union": None, "branch_counts_may_be_summed": False,
            "witnesses_may_be_unioned": False, **_flags()}
    withheld = [row["rule_id"] for row in rule_records
                if row["status"] != "conditional_shape" or row["blockers"] or not row["alternatives"]]
    if withheld:
        body["reasons"] = ["requested_rule_prerequisites_withheld_or_unsupported"]
        body["withheld_requested_rule_refs"] = withheld
    elif graph["status"] != "ready":
        body["reasons"] = ["factor_graph_not_ready", *graph["reasons"]]
    elif count > branch_budget:
        body["reasons"] = ["OR_branch_budget_exceeded_no_partial_success"]
    else:
        unassessed = False
        choices = product(*(range(len(row["alternatives"])) for row in rule_records))
        for indices in choices:
            required, forbidden = set(), set()
            chosen = []
            for row, index in zip(rule_records, indices):
                alt = row["alternatives"][index]
                required.update(_edge_set(alt["required_links"]))
                forbidden.update(_edge_set(alt["forbidden_links"]))
                chosen.append({"rule_ref": row["rule_id"], "alternative_index": index})
            query = factors.query(graph, required_links=[list(p) for p in sorted(required)],
                                  forbidden_links=[list(p) for p in sorted(forbidden)], work_budget=work_budget)
            witness = factors.materialize_witness(graph, query) if query["status"] == "exact_count" else None
            body["branches"].append({"chosen_alternatives": chosen, "query": query, "witness": witness})
            unassessed |= query["status"] not in ("exact_count", "unsatisfiable_constraints")
        body["all_requested_branches_assessed"] = not unassessed
        if unassessed:
            body["reasons"] = ["one_or_more_joint_queries_unassessed_no_partial_success"]
        elif any(branch["witness"] is not None for branch in body["branches"]):
            body["status"] = "joint_possible"
        else:
            body["status"] = "incompatible_joint_constraints"
            body["reasons"] = ["all_explicit_requested_alternative_branches_unsatisfiable"]
    if digest([graph, rule_records]) != before:
        raise ValueError("joint_solver_inputs_mutated")
    return views.seal(body, "fmjs_")


def validate_solution(record, graph, rule_records, *, branch_budget=256, work_budget=100000):
    views.check(record, "fmjs_")
    if record != solve_joint(graph, rule_records, branch_budget=branch_budget, work_budget=work_budget):
        raise ValueError("stale_foreign_or_modified_joint_solution")
    return True


def _lane(value):
    if isinstance(value, dict):
        value = [value.get("part_id"), value.get("voice_id")]
    if not isinstance(value, (list, tuple)) or len(value) != 2 or any(
            not isinstance(x, str) or not x for x in value):
        raise ValueError("explicit_raw_lane_required")
    return tuple(value)


def _bind(view, graph, query, witness):
    views.validate_view(view)
    factors._graph(graph)
    for field in ("score_id", "ir_document_id", "ir_content_sha256", "source_files"):
        if graph["binding"].get(field) != view["binding"].get(field):
            raise ValueError("factor_view_binding_mismatch:" + field)
    if graph["span"] != view["context_span"] or _lane(graph["lane"]) not in {
            _lane(row) for row in view["raw_lanes"]}:
        raise ValueError("factor_view_context_or_lane_mismatch")
    sound_index = {row["sound_id"]: row for row in view["sounds"]}
    sampled = {sid for sid, row in sound_index.items() if _lane(row["lane"]) == _lane(graph["lane"])}
    if sampled != {s["sounding_event_id"] for s in graph["events"]}:
        raise ValueError("factor_view_sampled_sound_partition_mismatch")
    for original in graph["events"]:
        sound = sound_index[original["sounding_event_id"]]
        for field in ("source_note_ids", "attack_note_id", "pitch", "span"):
            if original[field] != sound[field]:
                raise ValueError("factor_view_sound_snapshot_mismatch:" + field)
    request = query["request"]
    factors.validate_query(graph, query, required_links=request["original_required_links"],
                           forbidden_links=request["original_forbidden_links"], work_budget=request["work_budget"])
    if query["status"] != "exact_count" or witness != factors.materialize_witness(graph, query):
        raise ValueError("one_exact_bound_completion_required")


def _applicability(rule, links, compiled_ready):
    reasons = list(rule["blockers"])
    if not compiled_ready:
        reasons.append("compiled_inventory_not_complete")
    matches = [i for i, alt in enumerate(rule["alternatives"])
               if _edge_set(alt["required_links"]) <= links and not _edge_set(alt["forbidden_links"]) & links]
    if rule["status"] != "conditional_shape" or reasons:
        state = "withheld_prerequisites"
    elif matches:
        state = "conditional_shape_under_shared_completion"
    else:
        state = "not_satisfied_under_this_completion_not_global_absence"
    return {"rule_ref": rule["rule_id"], "family": rule["family"], "status": state,
            "matching_alternative_indices": matches, "blockers": reasons,
            "rule": deepcopy(rule), "role_selected": None}


def _covers(rule, sid, span):
    a, b = views.span_bounds(span)
    return any(item["sound_id"] == sid and views.f(item["span"]["start"]) <= a
               and b <= views.f(item["span"]["end"]) for item in rule["explained_items"])


def _lowest(active):
    values = [row["pitch"].get("midi_pitch") for row in active]
    if not active:
        return {"status": "silence", "midi_pitch": None, "sound_refs": [], "structural_bass": "unassessed"}
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        return {"status": "unknown_pitch", "midi_pitch": None, "sound_refs": [], "structural_bass": "unassessed"}
    low = min(values)
    return {"status": "observed_lowest_not_structural_bass", "midi_pitch": low,
            "sound_refs": sorted(row["sound_id"] for row in active if row["pitch"]["midi_pitch"] == low),
            "structural_bass": "unassessed"}


def _raw_membership(segment, pitch):
    try:
        p = views.pitch_key(pitch)
        members = {views.pitch_key(member) for member in segment["members"]}
    except (TypeError, ValueError, KeyError):
        return "unknown"
    return "member" if p in members else "nonmember"


def _relative(root, pitch):
    if root is None:
        return None
    try:
        rk, pk = views.pitch_key(root), views.pitch_key(pitch)
        letters = "CDEFGAB"
        degree = (letters.index(pk[0]) - letters.index(rk[0])) % 7 + 1
        natural = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        semitones = (natural[pk[0]] + pk[1] - natural[rk[0]] - rk[1]) % 12
    except (TypeError, ValueError, KeyError):
        return None
    return {"written_root_relative_generic_degree": degree, "written_pitch_class_semitones": views.q(semitones),
            "basis": "explicit_written_spelling_root_assumption_not_key_or_function"}


def _slot(sound, segment, notes, literal_sounds, ties, sources, attacks):
    start, end = views.f(sound["span"]["start"]), views.f(sound["span"]["end"])
    snapshots = [deepcopy(notes.get(nid)) for nid in sound["source_note_ids"]]
    literal = literal_sounds[sound["sound_id"]]
    tid = literal.get("tie_chain_id")
    return {"sound_ref": sound["sound_id"], "source_note_refs": deepcopy(sound["source_note_ids"]),
            "source_note_snapshots": snapshots, "attack_note_ref": sound["attack_note_id"],
            "attack_note_snapshot": deepcopy(notes.get(sound["attack_note_id"])), "raw_lane": deepcopy(sound["lane"]),
            "literal_sounding_snapshot": deepcopy(literal), "tie_chain_ref": tid,
            "tie_chain_snapshot": deepcopy(ties.get(tid)),
            "source_reference_snapshots": [deepcopy(sources[n["source_ref_id"]]) for n in snapshots],
            "attack_event_snapshots": deepcopy(attacks.get(sound["sound_id"], [])),
            "full_sounding_span": deepcopy(sound["span"]), "original_sounding_onset": views.q(start),
            "original_sounding_duration": deepcopy(literal["sounding_duration"]),
            "span_duration": views.q(end - start), "pitch": deepcopy(sound["pitch"]),
            "octave": sound["pitch"].get("octave"),
            "source_clock_passed": sound["source_clock_passed"],
            "source_pitch_consistency_passed": sound["source_pitch_consistency_passed"],
            "source_diagnostics": deepcopy(sound["source_diagnostics"]),
            "source_tie_roles": [None if n is None else n.get("tie_role") for n in snapshots],
            "assumed_root": deepcopy(segment["root"]), "relative_pitch": _relative(segment["root"], sound["pitch"]),
            "structural_bass": "unassessed", "key": "unassessed", "function": "unassessed", "cadence": "unassessed",
            "roles": "unresolved_alternatives_not_classified"}


def compare_under_completion(view, paths, graph, query, witness, compiled_records):
    """Exact all-part accounts for >=1 complete paths under ONE completion.

    A compiled inventory is not automatically requested as a joint rule set.
    Rules are tested against the supplied completion; unmet alternatives remain
    explicit. The sampled lane is the semantic-link scope, not the all-part
    accounting denominator. Raw assumed membership never changes with NCT.
    """
    inputs = [view, paths, graph, query, witness, compiled_records]
    before = digest(inputs)
    _bind(view, graph, query, witness)
    if not isinstance(paths, (list, tuple)) or not paths or not isinstance(compiled_records, (list, tuple)):
        raise ValueError("explicit_nonempty_paths_and_compilations_required")
    if len(paths) != len(compiled_records) or len({p["record_id"] for p in paths}) != len(paths):
        raise ValueError("unique_one_compilation_per_path_required")
    for path, compiled in zip(paths, compiled_records):
        views.validate_path(view, path)
        compiler.validate_rules(view, path, graph, compiled)
    a, b = views.span_bounds(view["target_span"])
    times = {a, b}
    for sound in view["sounds"]:
        for time in sound["span"].values():
            if a < views.f(time) < b:
                times.add(views.f(time))
    for path, compiled in zip(paths, compiled_records):
        for segment in path["segments"]:
            for time in segment["span"].values():
                if a < views.f(time) < b:
                    times.add(views.f(time))
        for rule in compiled["rules"]:
            for item in rule["explained_items"]:
                for time in item["span"].values():
                    if a < views.f(time) < b:
                        times.add(views.f(time))
    ordered = sorted(times)
    cells = [{"span": {"start": views.q(x), "end": views.q(y)},
              "sound_refs": sorted(s["sound_id"] for s in view["sounds"]
                                   if views.f(s["span"]["start"]) < y and views.f(s["span"]["end"]) > x)}
             for x, y in zip(ordered, ordered[1:])]
    sounds = {s["sound_id"]: s for s in view["sounds"]}
    notes = {n["note_id"]: n for n in view["note_snapshots"]}
    literal_sounds = {s["sounding_event_id"]: s for s in view["linked_sound_snapshots"]}
    ties = {t["tie_chain_id"]: t for t in view["tie_chain_snapshots"]}
    sources = {r["source_ref_id"]: r for r in view["source_reference_snapshots"]}
    attacks = {}
    for row in view["attack_snapshots"]:
        attacks.setdefault(row["sounding_event_id"], []).append(row)
    links = _edge_set(witness["assignment"]["links"])
    scope_lane = _lane(graph["lane"])
    total = sum((min(b, views.f(s["span"]["end"])) - max(a, views.f(s["span"]["start"]))
                 for s in view["sounds"] if views.f(s["span"]["start"]) < b and views.f(s["span"]["end"]) > a), Fraction())
    sampled = sum((min(b, views.f(s["span"]["end"])) - max(a, views.f(s["span"]["start"]))
                   for s in view["sounds"] if _lane(s["lane"]) == scope_lane
                   and views.f(s["span"]["start"]) < b and views.f(s["span"]["end"]) > a), Fraction())
    cell_lowest = [{"span": deepcopy(c["span"]), **_lowest([sounds[sid] for sid in c["sound_refs"]])} for c in cells]
    accounts = []
    for path, compiled in zip(paths, compiled_records):
        assessments = [_applicability(rule, links, compiled["status"] == "ready") for rule in compiled["rules"]]
        totals = {name: Fraction() for name in CATEGORIES}
        raw_totals = {name: Fraction() for name in RAW}
        items = []
        for cell in cells:
            x, y = views.span_bounds(cell["span"])
            # Paths were freshly validated above. Reuse that exact local
            # partition, rather than rehashing/revalidating it per item.
            segment = next((s for s in path["segments"]
                            if views.f(s["span"]["start"]) <= x < views.f(s["span"]["end"])), None)
            if segment is None or not y <= views.f(segment["span"]["end"]):
                raise ValueError("common_cell_not_within_one_path_segment")
            for sid in cell["sound_refs"]:
                sound = sounds[sid]
                raw = _raw_membership(segment, sound["pitch"])
                qualified = raw if segment["status"] == "usable" and not segment["blockers"] else "unknown"
                relevant = [row for row in assessments if _covers(row["rule"], sid, cell["span"])]
                allowed = [row["rule_ref"] for row in relevant if row["status"] == "conditional_shape_under_shared_completion"]
                withheld = [row["rule_ref"] for row in relevant if row["status"] == "withheld_prerequisites"]
                blockers = list(sound["source_diagnostics"])
                if sound["source_clock_passed"] is not True:
                    blockers.append("source_clock_guard_not_passed")
                if sound["source_pitch_consistency_passed"] is not True:
                    blockers.append("source_written_pitch_guard_not_passed")
                if segment["status"] != "usable" or segment["blockers"]:
                    blockers.extend(["harmony_segment_not_usable", *segment["blockers"]])
                if compiled["status"] != "ready":
                    blockers.append("compiled_inventory_not_complete")
                if _lane(sound["lane"]) != scope_lane:
                    allowed = []  # Another raw lane has no inferred links here.
                category = ("unsupported" if blockers else "unknown" if raw == "unknown" else
                            "member" if raw == "member" else "conditional_explained" if allowed else "unexplained")
                if raw == "nonmember" and qualified != "nonmember":
                    allowed = []
                    category = "unsupported" if qualified == "unknown" else category
                conditional_shape_refs = list(allowed)
                if category != "conditional_explained":
                    allowed = []  # Shape association never bypasses raw/source prerequisites.
                totals[category] += y - x
                raw_totals[raw] += y - x
                items.append({"item_id": "fmitem_" + digest([views.ref(view), sid, cell["span"]])[:24],
                              "sound_id": sid, "span": deepcopy(cell["span"]), "segment_ref": segment["segment_id"],
                              "raw_membership": raw, "qualified_membership": qualified,
                              "category": category, "conditional_rule_refs": allowed,
                              "conditional_shape_association_refs": conditional_shape_refs,
                              "withheld_rule_refs": withheld, "blockers": sorted(set(blockers)),
                              "slot": _slot(sound, segment, notes, literal_sounds, ties, sources, attacks)})
        if sum(totals.values(), Fraction()) != total or sum(raw_totals.values(), Fraction()) != total:
            raise ValueError("joint_accounting_note_time_loss")
        if len({item["item_id"] for item in items}) != len(items):
            raise ValueError("duplicate_event_time_accounting_item")
        accounts.append({"path_ref": views.ref(path), "compiled_ref": views.ref(compiled), "items": items,
                         "note_time": {k: views.q(v) for k, v in totals.items()},
                         "raw_note_time": {k: views.q(v) for k, v in raw_totals.items()},
                         "total_note_time": views.q(total), "rule_assessments": assessments,
                         "segment_count": len(path["segments"]), "status": "conditional_account_not_verdict"})
    deltas = [{"first_path_ref": first["path_ref"], "second_path_ref": second["path_ref"],
               "shared_completion_ref": views.ref(witness),
               "note_time_delta_second_minus_first": {k: views.q(views.f(second["note_time"][k]) - views.f(first["note_time"][k])) for k in CATEGORIES},
               "raw_note_time_delta_second_minus_first": {k: views.q(views.f(second["raw_note_time"][k]) - views.f(first["raw_note_time"][k])) for k in RAW},
               "boundary_count_delta": second["segment_count"] - first["segment_count"],
               "interpretation": "membership_or_conditional_gain_is_not_accuracy_gain", "preferred": None}
              for first, second in combinations(accounts, 2)]
    body = {"version": VERSION, "view_ref": views.ref(view), "binding": deepcopy(view["binding"]),
            "context_span": deepcopy(view["context_span"]), "target_span": deepcopy(view["target_span"]),
            "graph_ref": views.ref(graph), "query_ref": views.ref(query), "shared_completion_ref": views.ref(witness),
            "completion_id": witness["assignment"]["completion_id"], "semantic_link_lane": list(scope_lane),
            "accounting_scope": "all_part_positive_sounds_in_target_not_sampled_lane_only",
            "cells": cells, "observed_lowest": cell_lowest, "accounts": accounts, "deltas": deltas,
            "total_all_part_note_time": views.q(total), "sampled_evaluation_note_time": views.q(sampled),
            "graph_sampled_context_note_time": deepcopy(graph["total_observed_note_time"]),
            "point_observations": deepcopy(view["points"]), "measure_snapshots": deepcopy(view["measure_snapshots"]),
            "status": "same_completion_conditional_comparison_not_verdict",
            "alternative_roles_selected": False, "raw_membership_modified_by_explanations": False,
            "counts_are_confidence": False, "explanations_counted_as_extra_note_time": False,
            "limits": ["Only one sampled raw-lane completion supports link-dependent clauses.",
                       "Other lanes retain literal membership and time, not inferred voice links.",
                       "Unmet clauses are absent from this completion, not impossible in all completions.",
                       "Written root-relative pitch is not inferred local key, function, consonance or cadence.",
                       "Broken-chord/held-bass shape alternatives do not exempt nonmembers or certify roles."], **_flags()}
    if digest(inputs) != before:
        raise ValueError("factor_comparison_inputs_mutated")
    return views.seal(body, "fmcmp_")


def validate_comparison(record, view, paths, graph, query, witness, compiled_records):
    views.check(record, "fmcmp_")
    if record != compare_under_completion(view, paths, graph, query, witness, compiled_records):
        raise ValueError("stale_foreign_or_modified_factor_comparison")
    return True
