"""Additive pre/post score facts for an unchanged frozen musical view.

The public MPO scope requires admitted source-statement/alignment references,
which a frozen unlabeled window does not supply.  This adapter therefore uses
the exact literal projection kernel, its own typed parent references and a new
fmctx_ contract.  It never enlarges an mfco, harmony path or completion bundle.
Endpoint adjacency in one raw lane is observed timing, not an inferred voice.
"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from . import factor_musical_view as common
from . import frozen_context_observation as frozen
from . import musical_pattern_observation as pattern
from . import sounding_lineage_audit as lineage

VERSION = "factor-context-observation-0.1.0"
PREFIX = "fmctx_"
LETTERS = "CDEFGAB"
NATURAL = dict(zip(LETTERS, (0, 2, 4, 5, 7, 9, 11)))


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_required:" + name)


def _contract():
    modules = (common, frozen, pattern, lineage)
    sources = [{"module": __name__, "sha256": sha256(Path(__file__).read_bytes()).hexdigest()}]
    sources.extend({"module": module.__name__,
                    "sha256": sha256(Path(module.__file__).read_bytes()).hexdigest()}
                   for module in modules)
    schemas = [{"kind": "view_core", "sha256": sha256(common._schema_bytes()).hexdigest()}]
    schemas.extend({"kind": name, "sha256": sha256(path.read_bytes()).hexdigest()}
                   for name, path in (("pattern_core", pattern.CORE_SCHEMA_PATH),
                                      ("literal_pattern", pattern.SCHEMA_PATH),
                                      ("frozen_core", frozen.CORE_SCHEMA_PATH),
                                      ("frozen_observation", frozen.SCHEMA_PATH)))
    return {"version": VERSION, "sources": sources, "schemas": schemas}


def _measure_envelope(ir, view, pre, post):
    """Union actual clock groups; printed numbers are display-only metadata.

    Equal start/end clocks are one physical group, retaining every measure ID.
    Distinct overlapping clocks remain distinct and are ordered by exact start,
    then end.  Every clock touching the old span is included before padding.
    For a span in a clock gap, nearest preceding/following groups are explicit
    padding only. Zero-duration groups remain metadata and may consume a slot.
    """
    original = common.span_bounds(view["context_span"])
    duration = common.f(ir["score"]["duration_quarters"])
    groups = defaultdict(list)
    diagnostics = []
    for measure in ir["measures"]:
        start = common.f(measure["global_start_quarter"])
        actual = common.f(measure["actual_duration_quarter"])
        if start < 0 or actual < 0:
            raise ValueError("negative_physical_measure_clock")
        groups[(start, start + actual)].append(measure["measure_id"])
        if actual == 0:
            diagnostics.append("zero_duration_measure_clock:" + measure["measure_id"])
        if start + actual > duration:
            diagnostics.append("measure_clock_exceeds_score_clamped_for_envelope:" + measure["measure_id"])
        if actual != common.f(measure["nominal_duration_quarter"]):
            diagnostics.append("actual_and_nominal_duration_differ:" + measure["measure_id"])
    ordered = sorted(groups)
    latest_end = None
    for start, end in ordered:
        if latest_end is not None and start < latest_end and end > start:
            diagnostics.append("overlapping_distinct_measure_clocks")
        if latest_end is not None and start > latest_end:
            diagnostics.append("gap_between_physical_measure_clocks")
        if end > start:
            latest_end = max(end, latest_end) if latest_end is not None else end
    lo, hi = original
    touched = [i for i, (a, b) in enumerate(ordered)
               if (lo <= a < hi if a == b else a < hi and b > lo)]
    if touched:
        selected = list(range(max(0, min(touched) - pre), min(len(ordered), max(touched) + post + 1)))
    else:
        diagnostics.append("original_context_has_no_overlapping_measure_clock")
        preceding = [i for i, (_, b) in enumerate(ordered) if b <= lo]
        following = [i for i, (a, _) in enumerate(ordered) if a >= hi]
        selected = sorted(set((preceding[-pre:] if pre else []) + following[:post]))
    start = max(0, min([lo, *[ordered[i][0] for i in selected]]))
    end = min(duration, max([hi, *[ordered[i][1] for i in selected]]))
    envelope = {"start": common.q(start), "end": common.q(end)}
    if not start <= lo < hi <= end:
        raise ValueError("physical_measure_envelope_lost_original_context")
    clock_rows = [{"clock_index": i, "span": {"start": common.q(a), "end": common.q(b)},
                   "measure_refs": sorted(groups[(a, b)]), "touches_original_context": i in touched,
                   "selected": i in selected}
                  for i, (a, b) in enumerate(ordered)]
    return envelope, {"policy": "union_all_actual_clock_groups_touching_original_then_ordered_neighbors",
                      "clock_order": "exact_global_start_then_actual_end_not_printed_number",
                      "duplicate_clocks": "group_equal_start_end_keep_all_measure_refs",
                      "overlaps": "keep_all_distinct_clocks_union_no_clock_repair",
                      "zero_duration": "metadata_clock_group_can_consume_neighbor_slot",
                      "gaps": "original_span_preserved_no_nominal_duration_fill",
                      "score_clamp": True, "pre_measures": pre, "post_measures": post,
                      "clock_groups": clock_rows, "diagnostics": sorted(set(diagnostics))}


def _placement(span, scopes):
    a, b = common.span_bounds(span) if common.f(span["start"]) != common.f(span["end"]) else (
        common.f(span["start"]), common.f(span["end"]))
    result = {}
    for name, scope in scopes.items():
        lo, hi = common.span_bounds(scope)
        result[name] = {"overlap": common.clipped(span, scope),
                        "onset_inside": lo <= a < hi,
                        "point_inside": a == b and lo <= a < hi,
                        "full_positive_span_contained": lo <= a < b <= hi,
                        "active_at_start_right_limit": a <= lo < b,
                        "active_at_end_left_limit": a < hi <= b,
                        "release_at_start": b == lo,
                        "release_at_end": b == hi}
    return result


def _lane(sound, notes):
    owners = {(notes[nid]["part_id"], notes[nid]["voice_id"]) for nid in sound["source_note_ids"]}
    return next(iter(owners)) if len(owners) == 1 else None


def _neighbor_plans(ir, view):
    notes = {n["note_id"]: n for n in ir["note_events"]}
    sounds = {s["sounding_event_id"]: s for s in ir["sounding_events"]}
    lanes = defaultdict(list)
    unlocated = []
    for sound in ir["sounding_events"]:
        lane = _lane(sound, notes)
        if common.f(sound["span"]["start"]) < common.f(sound["span"]["end"]):
            if lane is None:
                unlocated.append(sound["sounding_event_id"])
            else:
                lanes[lane].append(sound)
    plans = []
    selected = {s["sounding_event_id"] for s in view["linked_sound_snapshots"]}
    selected.update(unlocated)
    for seed in view["sounds"]:
        sound = sounds[seed["sound_id"]]
        a, b = common.span_bounds(sound["span"])
        lane = _lane(sound, notes)
        if lane is None or list(lane) != seed["lane"]:
            raise ValueError("old_positive_sound_raw_lane_changed")
        options = lanes[lane]
        next_times = [common.f(s["span"]["start"]) for s in options if common.f(s["span"]["start"]) >= b]
        previous_times = [common.f(s["span"]["end"]) for s in options if common.f(s["span"]["end"]) <= a]
        after = min(next_times) if next_times else None
        before = max(previous_times) if previous_times else None
        successors = sorted(s["sounding_event_id"] for s in options if after is not None and common.f(s["span"]["start"]) == after)
        predecessors = sorted(s["sounding_event_id"] for s in options if before is not None and common.f(s["span"]["end"]) == before)
        held_at_attack = sorted(s["sounding_event_id"] for s in options if common.f(s["span"]["start"]) < a < common.f(s["span"]["end"]))
        held_at_release = sorted(s["sounding_event_id"] for s in options if common.f(s["span"]["start"]) < b < common.f(s["span"]["end"]))
        selected.update([seed["sound_id"], *successors, *predecessors, *held_at_attack, *held_at_release])
        plans.append({"seed_sound_ref": seed["sound_id"], "lane": list(lane),
                      "source_onset": common.q(a), "source_release": common.q(b),
                      "successor_refs": successors, "successor_onset": None if after is None else common.q(after),
                      "successor_gap": None if after is None else common.q(after - b),
                      "predecessor_refs": predecessors, "predecessor_release": None if before is None else common.q(before),
                      "predecessor_gap": None if before is None else common.q(a - before),
                      "held_at_attack_refs": held_at_attack, "held_at_release_refs": held_at_release,
                      "successor_status": "no_full_lane_endpoint_successor_under_policy" if after is None else "touching_endpoints_not_voice_edge" if after == b else "first_later_onset_group_gap_not_voice_edge",
                      "predecessor_status": "no_full_lane_endpoint_predecessor_under_policy" if before is None else "touching_endpoints_not_voice_edge" if before == a else "last_earlier_release_group_gap_not_voice_edge",
                      "lookup_basis": "entire_bound_IR_same_raw_part_and_voice_positive_sounds",
                      "full_raw_lane_lookup_has_unlocated_sound_unknowns": bool(unlocated),
                      "missing_pitch_globally_proved": False, "voice_edge_established": False})
    return plans, selected, sorted(unlocated)


def _snapshot_closure(ir, sound_ids, literal):
    """Exact source closure for neighbor snapshots, including outside metadata."""
    note_ids = {r["event_id"] for r in literal["slots"] if r["event_kind"] == "note"}
    note_ids.update(nid for s in ir["sounding_events"] if s["sounding_event_id"] in sound_ids for nid in s["source_note_ids"])
    notes = {n["note_id"]: n for n in ir["note_events"]}
    previous = None
    chosen = {}
    while previous != note_ids:
        previous = set(note_ids)
        for name in ("sounding_events", "tie_chains", "chord_onset_groups"):
            chosen[name] = [row for row in ir[name] if note_ids.intersection(row.get("source_note_ids", row.get("note_ids")))]
            note_ids.update(nid for row in chosen[name] for nid in row.get("source_note_ids", row.get("note_ids")))
        note_ids.update(notes[nid]["grace"]["anchor_note_id"] for nid in list(note_ids) if notes[nid]["grace"]["anchor_note_id"] is not None)
    chosen_ids = {s["sounding_event_id"] for s in chosen["sounding_events"]}
    rows = [n for n in ir["note_events"] if n["note_id"] in note_ids]
    rests = [slot["core_event"] for slot in literal["slots"] if slot["event_kind"] == "rest"]
    source_ids = {n["source_ref_id"] for n in [*rows, *rests]}
    return {"note_events": rows, "rest_events": rests,
            "source_references": [r for r in ir["source_references"] if r["source_ref_id"] in source_ids],
            "attack_events": [r for r in ir["attack_events"] if r["sounding_event_id"] in chosen_ids], **chosen}


def _motion(left, right):
    p, r = left["pitch"], right["pitch"]
    degree = 7 * (r["octave"] - p["octave"]) + LETTERS.index(r["step"]) - LETTERS.index(p["step"])
    semitones = 12 * (r["octave"] - p["octave"]) + NATURAL[r["step"]] - NATURAL[p["step"]] + common.f(r["alter"]) - common.f(p["alter"])
    integral = common.f(p["alter"]).denominator == common.f(r["alter"]).denominator == 1
    return {"diatonic_steps": degree, "semitones": common.q(semitones),
            "same_written_pitch_and_register": degree == 0 and semitones == 0,
            "integer_spelling_supported": integral, "tonal_resolution_evaluated": False,
            "diagnostics": [] if integral else ["microtonal_motion_not_tonal_resolution_support"]}


def observe_context(ir, view, mfco, audit, *, pre_measures=1, post_measures=1,
                    max_events=4096, max_relations=65536):
    """Retain complete source facts and bounded optional temporal motion rows.

    Event budget counts unique notated snapshots plus unique sound snapshots,
    including outside-envelope metadata and linked closure.  A whole-budget
    hold keeps inventories/refs/snapshots/audits; it materializes no subset of
    motion relations. Budgets do not assert a bounded output-byte/RSS size.
    """
    options = {"pre_measures": pre_measures, "post_measures": post_measures,
               "max_events": max_events, "max_relations": max_relations}
    for name, value in options.items():
        _integer(value, name)
    before = pattern.digest([ir, view, mfco, audit])
    contract = _contract()
    pattern.validate_core(ir)
    common.validate_view(view, ir=ir, observation=mfco, audit=audit)
    envelope, clock_policy = _measure_envelope(ir, view, pre_measures, post_measures)
    scope = {"score_id": view["binding"]["score_id"], "ir_document_id": view["binding"]["ir_document_id"],
             "ir_content_sha256": view["binding"]["ir_content_sha256"],
             "source_files": ir["source_files"], "target_span": view["target_span"], "context_span": envelope}
    slots, projection, raw_lanes = common._selected_literal(ir, scope)
    literal = {"scope": scope, "slots": slots, "core_projection": projection, "raw_lanes": raw_lanes,
               "kind": "literal_context_projection_not_MPO_or_mfco",
               "source_statement_or_alignment_refs_invented": False}
    plans, seed_neighbors, unlocated = _neighbor_plans(ir, view)
    registry = _snapshot_closure(ir, seed_neighbors, literal)
    sounds = {s["sounding_event_id"]: s for s in registry["sounding_events"]}
    notes = {n["note_id"]: n for n in registry["note_events"]}
    sound_ids = list(sounds)
    new_audit = lineage.audit_sounding_lineage(ir, sound_ids=sound_ids, context_span=envelope)
    audited = {r["sounding_event_ref"]: r for r in new_audit["sounding_audits"]}
    scopes = {"original_target": view["target_span"], "original_context": view["context_span"], "envelope": envelope}
    facts = []
    for sid, sound in sounds.items():
        owner = _lane(sound, notes)
        point = common.f(sound["span"]["start"]) == common.f(sound["span"]["end"])
        is_grace = any(notes[nid]["grace"]["is_grace"] for nid in sound["source_note_ids"])
        written = common.pitch_key(sound["pitch"], True)
        pitch_passed = all(common.pitch_key(notes[nid]["written_pitch"], True) == written for nid in sound["source_note_ids"])
        pitch_passed = pitch_passed and common.pitch_key(notes[sound["attack_note_id"]]["written_pitch"], True) == written
        codes = list(audited[sid]["diagnostics"])
        if not pitch_passed:
            codes.append("source_written_pitch_mismatch")
        if owner is None:
            codes.append("ambiguous_raw_lane_ownership")
        if common.f(sound["pitch"]["alter"]).denominator != 1:
            codes.append("microtonal_motion_not_tonal_resolution_support")
        placement = _placement(sound["span"], scopes)
        inside = placement["envelope"]["overlap"] is not None or placement["envelope"]["point_inside"]
        facts.append({"sound_ref": sid, "source_note_refs": list(sound["source_note_ids"]),
                      "attack_note_ref": sound["attack_note_id"], "tie_chain_ref": sound.get("tie_chain_id"),
                      "lane": None if owner is None else list(owner), "span": sound["span"], "pitch": sound["pitch"],
                      "placement": placement, "point": point, "grace": is_grace,
                      "outside_envelope_metadata_only": not inside,
                      "observed_positive_sound_in_envelope": inside and not point,
                      "eligible_as_envelope_source": inside and not point and not is_grace and owner is not None and audited[sid]["source_clock_consistency_passed"] and pitch_passed,
                      "source_clock_passed": audited[sid]["source_clock_consistency_passed"],
                      "source_pitch_consistency_passed": pitch_passed,
                      "source_audit_row_sha256": pattern.digest(audited[sid]),
                      "diagnostics": sorted(set(codes)), "voice_identity_confirmed": False,
                      "harmony_membership_evaluated": False, "resolution_eligible": False})
    fact_index = {row["sound_ref"]: row for row in facts}
    event_slots = len(registry["note_events"]) + len(registry["rest_events"]) + len(sounds)
    relation_slots = sum(len(plan["predecessor_refs"]) + len(plan["successor_refs"]) for plan in plans)
    reasons = []
    if event_slots > max_events:
        reasons.append("whole_snapshot_event_inventory_exceeds_budget_no_pruning")
    if relation_slots > max_relations:
        reasons.append("whole_temporal_relation_inventory_exceeds_budget_no_partial_relations")
    relations = []
    if not reasons:
        for plan in plans:
            seed = plan["seed_sound_ref"]
            for direction, neighbors in (("predecessor", plan["predecessor_refs"]), ("successor", plan["successor_refs"])):
                for other in neighbors:
                    left, right = (other, seed) if direction == "predecessor" else (seed, other)
                    gap = common.f(sounds[right]["span"]["start"]) - common.f(sounds[left]["span"]["end"])
                    guards = sorted(set(fact_index[left]["diagnostics"] + fact_index[right]["diagnostics"]))
                    available = all(not fact_index[sid]["outside_envelope_metadata_only"] for sid in (left, right))
                    relations.append({"seed_sound_ref": seed, "direction": direction,
                                      "left_sound_ref": left, "right_sound_ref": right, "lane": plan["lane"],
                                      "gap": common.q(gap), "touching_full_endpoints": gap == 0,
                                      "outside_envelope_metadata_only": not available,
                                      "motion": _motion(sounds[left], sounds[right]), "source_guard_diagnostics": guards,
                                      "source_clock_and_pitch_passed": all(fact_index[sid]["source_clock_passed"] and fact_index[sid]["source_pitch_consistency_passed"] for sid in (left, right)),
                                      "voice_edge_established": False, "completion_condition_created": False,
                                      "resolution_eligible": False, "status": "literal_temporal_relation_not_resolution"})
    original_lanes = [[r["part_id"], r["voice_id"]] for r in view["raw_lanes"]]
    extended_lanes = [[r["part_id"], r["voice_id"]] for r in raw_lanes]
    body = {"version": VERSION, "contract": contract, "binding": view["binding"],
            "original_view_ref": common.ref(view), "observation_ref": common.ref(mfco), "audit_ref": common.ref(audit),
            "original_context_span": view["context_span"], "original_target_span": view["target_span"],
            "envelope_span": envelope, "options": options, "measure_policy": clock_policy,
            "literal_observation": literal, "snapshot_registry": registry, "sound_facts": facts,
            "extended_source_audit": new_audit, "neighbor_inventory": plans, "relations": relations,
            "unlocated_full_IR_positive_sound_refs": unlocated,
            "neighbor_lookup_policy": {"full_IR_scan": True, "positive_sounds_only_for_endpoints": True,
                                       "all_equal_onsets_or_releases_retained": True,
                                       "unlocated_full_IR_sounds": "preserved_unknown_metadata_not_assigned_to_a_lane",
                                       "endpoint_adjacency_is_not_notated_voice_next": True},
            "point_sound_refs": [r["sound_ref"] for r in facts if r["point"]],
            "grace_sound_refs": [r["sound_ref"] for r in facts if r["grace"]],
            "raw_lane_scope": {"original_lanes": original_lanes, "envelope_lanes": extended_lanes,
                               "added_lanes": [lane for lane in extended_lanes if lane not in original_lanes],
                               "selection_by_source_note_part_and_voice": True,
                               "same_raw_lane_does_not_certify_voice_continuity": True},
            "counts": {"old_positive_sounds": len(plans), "literal_slots": len(slots),
                       "snapshot_notated_events": len(registry["note_events"]) + len(registry["rest_events"]),
                       "snapshot_sounds": len(sounds), "whole_event_slots": event_slots,
                       "planned_relations": relation_slots, "materialized_relations": len(relations)},
            "status": "whole_budget_abstention" if reasons else "ready_literal_context_not_analysis",
            "reasons": reasons, "inventories_complete": True, "snapshot_closure_complete": True,
            "relations_complete": not reasons, "partial_relation_selection_performed": False,
            "truncated": False, "full_score_motion_or_pitch_absence_certified": False,
            "original_window_or_path_or_bundle_extended": False, "source_annotations_used": False,
            "selected": None, "preferred": None, "counts_are_confidence": False,
            "harmony_confirmed": False, "function_confirmed": False, "resolution_confirmed": False,
            "cadence_confirmed": False, "nct_confirmed": False, "training_eligible": False,
            "gold_eligible": False, "generation_ready": False,
            "limits": ["Full same-raw-lane endpoint groups are timing observations, never an inferred voice edge.",
                       "Outside-envelope exact snapshots are metadata, not enlarged harmonic/source targets.",
                       "Before/after groups do not supply a missing critical source inside an original harmonic span.",
                       "No source statement, alignment admission, harmony/key selection or completion is fabricated.",
                       "Whole budgets hold all motion materialization, preserving full inventories and source facts.",
                       "Missing endpoints under this policy do not prove missing pitch, motion or resolution globally."]}
    if pattern.digest([ir, view, mfco, audit]) != before or _contract() != contract:
        raise ValueError("context_observation_inputs_or_contract_changed")
    return common.seal(body, PREFIX)


def validate_context(record, *, ir, view, observation, audit, pre_measures=1, post_measures=1,
                     max_events=4096, max_relations=65536):
    """Rebuild all exact parent, source-clock, projection and neighbor facts."""
    common.check(record, PREFIX)
    if record != observe_context(ir, view, observation, audit, pre_measures=pre_measures,
                                 post_measures=post_measures, max_events=max_events,
                                 max_relations=max_relations):
        raise ValueError("stale_foreign_or_modified_context_observation")
    return True
