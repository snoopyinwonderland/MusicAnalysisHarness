"""Literal and candidate-conditioned cadence prerequisites, never a verdict.

Every declared path boundary is retained. A harmony arrival and a possible
terminal release are different coordinates. Written extrema, IR meter and one
raw-lane completion do not identify structural voices or certify phrase closure.
"""
from copy import deepcopy

from . import factor_musical_view as common
from . import factor_functional_overlay as overlay
from . import factor_functional_resolution as resolution
from . import factor_functional_comparison as comparison
from .tonal_foundations import scale_degree, spelled_triad_shapes, spelled_seventh_shapes

VERSION = "factor-cadence-prerequisites-0.1.0"
PREFIX = "fmcad_"
BATCH_PREFIX = "fmcpbatch_"
LETTERS = "CDEFGAB"
FLAGS = {"selected": None, "cadence_confirmed": False, "key_confirmed": False,
         "function_confirmed": False, "inversion_confirmed": False,
         "structural_bass_confirmed": False, "structural_melody_confirmed": False,
         "perceived_accent_certified": False, "meter_source_certified": False,
         "consonance_certified": False, "phrase_terminal_certified": False,
         "performed_timing_certified": False, "source_labels_used": False,
         "key_signature_used": False, "training_eligible": False,
         "gold_eligible": False, "generation_ready": False,
         "ranked": False, "counts_are_confidence": False,
         "independent_completions_unioned": False}
MISSING_PREMISES = ["local_key_certified_unestablished", "structural_bass_identity_unestablished",
                    "structural_melody_identity_unestablished", "perceived_accent_unestablished",
                    "consonance_unestablished", "phrase_terminal_unestablished",
                    "performed_timing_unestablished"]


def _span(start, end):
    return {"start": common.q(start), "end": common.q(end)}


def _key_at(track, when, *, before=False):
    return next((s for s in track["segments"]
                 if (common.f(s["span"]["start"]) < when <= common.f(s["span"]["end"]) if before
                     else common.f(s["span"]["start"]) <= when < common.f(s["span"]["end"]))), None)


def _source_guards(sound):
    return {"source_clock_passed": sound["source_clock_passed"],
            "source_pitch_consistency_passed": sound["source_pitch_consistency_passed"],
            "source_diagnostics": deepcopy(sound["source_diagnostics"])}


def _source_blockers(sound):
    reasons = []
    if sound["source_clock_passed"] is not True:
        reasons.append("source_clock_unestablished")
    if sound["source_pitch_consistency_passed"] is not True:
        reasons.append("source_written_pitch_unestablished")
    return reasons


def _ordinary_shape(segment):
    if segment is None:
        return {"status": "unassessed", "quality": None, "blockers": ["assumed_segment_unavailable"]}
    root, members = segment["root"], segment["members"]
    reasons = list(segment["blockers"])
    if segment["status"] != "usable":
        reasons.append("assumed_segment_not_usable")
    if root is None:
        reasons.append("assumed_root_unavailable")
    pitches = [root, *members] if root is not None else members
    if any(common.f(p["alter"]).denominator != 1 for p in pitches):
        reasons.append("ordinary_microtonal_shape_unassessed")
    shapes = []
    if root is not None and not any(common.f(p["alter"]).denominator != 1 for p in pitches):
        values = [(p["step"], common.f(p["alter"]).numerator, 4) for p in members]
        candidates = (spelled_triad_shapes(values) if len(members) == 3 else
                      spelled_seventh_shapes(values) if len(members) == 4 else [])
        shapes = [s for s in candidates if (s["root_step"], s["root_alter"]) ==
                  (root["step"], common.f(root["alter"]).numerator)]
        if len(shapes) != 1:
            reasons.append("complete_ordinary_triad_or_seventh_shape_unestablished")
    return {"status": "conditional_complete_ordinary_shape" if not reasons else "withheld",
            "quality": shapes[0]["quality"] if len(shapes) == 1 else None,
            "blockers": sorted(set(reasons)), "shape_is_harmony_confirmation": False}


def _factor(sound, segment, shape, *, is_lowest, lowest_spelling_ambiguous):
    pitch = sound["pitch"]
    root = None if segment is None else segment["root"]
    member = (None if segment is None else
              common.pitch_key(pitch) in {common.pitch_key(p) for p in segment["members"]})
    degree = None if root is None else (LETTERS.index(pitch["step"]) - LETTERS.index(root["step"])) % 7 + 1
    reasons = [*shape["blockers"], *_source_blockers(sound)]
    if member is False:
        reasons.append("observed_extreme_outside_assumed_members_not_NCT_confirmation")
    if lowest_spelling_ambiguous and is_lowest:
        reasons.append("equal_lowest_enharmonic_spellings_unresolved")
    inversion = None
    if is_lowest and member is True and not reasons and degree in (1, 3, 5, 7):
        inversion = {1: 0, 3: 1, 5: 2, 7: 3}[degree]
    return {"assumed_segment_ref": None if segment is None else segment["segment_id"],
            "assumed_root": deepcopy(root),
            "assumed_members": [] if segment is None else deepcopy(segment["members"]),
            "spelled_member_of_assumption": member, "diatonic_factor_from_assumed_root": degree,
            "ordinary_shape": deepcopy(shape), "is_observed_lowest": is_lowest,
            "conditional_inversion_shape": inversion,
            "inversion_status": ("not_a_lowest_sound_observation" if not is_lowest else
                                 "conditional_on_assumed_chord_and_observed_lowest_not_structural_bass"
                                 if inversion is not None else "unassessed_prerequisites"),
            "blockers": sorted(set(reasons)), "inversion_confirmed": False,
            "structural_bass_confirmed": False}


def _degree(sound, key):
    reasons = []
    if key is None or key["tonic"] is None or key["mode"] == "unknown":
        reasons.append("explicit_local_key_unknown")
    if key is not None and key["scale_form"] == "unknown":
        reasons.append("explicit_scale_form_unknown")
    pitch = sound["pitch"]
    if common.f(pitch["alter"]).denominator != 1 or (key is not None and key["tonic"] is not None
            and common.f(key["tonic"]["alter"]).denominator != 1):
        reasons.append("ordinary_microtonal_scale_coordinate_unassessed")
    coordinate = None
    if not reasons:
        coordinate = scale_degree(pitch["step"], common.f(pitch["alter"]).numerator,
                                  key["tonic"]["step"], common.f(key["tonic"]["alter"]).numerator,
                                  form=key["scale_form"])
    return {"key_segment_ref": None if key is None else key["segment_id"],
            "assumed_key": deepcopy(key), "coordinate": coordinate,
            "status": "conditional_scale_coordinate" if coordinate is not None else "unassessed",
            "blockers": reasons, "key_confirmed": False}


def _terminal_probe(view, sound, when, metric, notes):
    c, d = common.span_bounds(view["context_span"])
    start, release = common.span_bounds(sound["span"])
    duration = release - start
    ratios = [{"measure_id": row["measure_id"],
               "notated_beat_unit_quarter": deepcopy(row["notated_beat_unit_quarter"]),
               "full_sound_duration_in_notated_units": common.q(duration / common.f(row["notated_beat_unit_quarter"])),
               "remaining_duration_from_boundary_in_notated_units": common.q((release - when) / common.f(row["notated_beat_unit_quarter"])),
               "basis": "boundary_IR_notated_denominator_unit_not_certified_meter_or_conducting_beat"}
              for row in metric["coordinates"]]
    attacks = []
    for row in [*view["sounds"], *view["points"]]:
        note = notes[row["attack_note_id"]]
        onset = common.f(note["global_onset_quarter"])
        if row["lane"] == sound["lane"] and release <= onset < d and onset >= c:
            attacks.append({"sound_ref": row["sound_id"], "attack_note_ref": row["attack_note_id"],
                            "onset": common.q(onset), "point": row in view["points"],
                            "source_guards": _source_guards(row)})
    attacks.sort(key=lambda row: (common.f(row["onset"]), row["sound_ref"]))
    rests = []
    for rest in view["rest_snapshots"]:
        a = common.f(rest["global_onset_quarter"])
        b = a + common.f(rest["notated_duration_quarter"])
        if [rest["part_id"], rest["voice_id"]] == sound["lane"] and max(a, release, c) < min(b, d):
            rests.append({"rest_ref": rest["rest_id"], "source_ref_id": rest["source_ref_id"],
                          "full_span": _span(a, b), "observed_following_span": _span(max(a, release, c), min(b, d)),
                          "hidden": rest["hidden"], "overlap_is_silence_confirmation": False})
    rests.sort(key=lambda row: (common.f(row["full_span"]["start"]), row["rest_ref"]))
    later_sounds = [{"sound_ref": s["sound_id"], "full_span": deepcopy(s["span"]),
                     "observed_span": deepcopy(s["observed_span"]), "source_guards": _source_guards(s)}
                    for s in view["sounds"] if s["lane"] == sound["lane"]
                    and common.f(s["observed_span"]["end"]) > release]
    return {"boundary_time": common.q(when), "candidate_terminal_release_time": common.q(release),
            "arrival_and_terminal_are_distinct_coordinates": True, "full_sound_span": deepcopy(sound["span"]),
            "full_sound_duration_quarters": common.q(duration), "notated_duration_ratios": ratios,
            "observed_horizon": deepcopy(view["context_span"]),
            "release_inside_observed_horizon": c <= release < d,
            "release_at_context_endpoint": release == d, "release_beyond_observed_horizon": release > d,
            "following_observation_status": "inside_observed_horizon" if c <= release < d else "unassessed_at_or_beyond_context_endpoint",
            "later_same_raw_lane_attacks": attacks, "observed_following_same_raw_lane_rest_spans": rests,
            "later_same_raw_lane_positive_sounds": later_sounds,
            "no_observed_later_attack_is_phrase_closure": False,
            "sustain_or_ornament_is_universal_cadence_counterevidence": False,
            "phrase_terminal": "unassessed", "performed_release": "unassessed"}


def _extreme_inventory(view, evidence, side, segment, key, notes, probe_cache):
    value = evidence["lowest_highest_" + side]
    low, high = set(value["lowest_sound_refs"]), set(value["highest_sound_refs"])
    sounds = {s["sound_id"]: s for s in view["sounds"]}
    ambiguous = len({common.pitch_key(sounds[sid]["pitch"]) for sid in low}) > 1
    shape = _ordinary_shape(segment)
    source_refs = {r["source_ref_id"]: r for r in view["source_reference_snapshots"]}
    literal = {r["sounding_event_id"]: r for r in view["linked_sound_snapshots"]}
    ties = {r["tie_chain_id"]: r for r in view["tie_chain_snapshots"]}
    result = []
    for sid in sorted(low | high):
        sound = sounds[sid]
        source_notes = [deepcopy(notes[nid]) for nid in sound["source_note_ids"]]
        original = literal[sid]
        tid = original.get("tie_chain_id")
        probe_key = (sid, common.f(evidence["boundary_time"]))
        if probe_key not in probe_cache:
            probe_cache[probe_key] = _terminal_probe(view, sound, probe_key[1], evidence["notated_metric"], notes)
        result.append({"sound_ref": sid, "extreme_axes": [name for name, ids in (("lowest", low), ("highest", high)) if sid in ids],
                       "raw_lane": deepcopy(sound["lane"]), "written_pitch": deepcopy(sound["pitch"]),
                       "source_note_refs": deepcopy(sound["source_note_ids"]), "attack_note_ref": sound["attack_note_id"],
                       "full_sound_snapshot": deepcopy(original), "source_note_snapshots": source_notes,
                       "source_reference_snapshots": [deepcopy(source_refs[rid]) for rid in sorted({n["source_ref_id"] for n in source_notes})],
                       "tie_chain_snapshot": None if tid is None else deepcopy(ties[tid]),
                       "source_guards": _source_guards(sound),
                       "candidate_factor": _factor(sound, segment, shape, is_lowest=sid in low, lowest_spelling_ambiguous=ambiguous),
                       "candidate_scale_degree": _degree(sound, key),
                       "terminal_probe": deepcopy(probe_cache[probe_key])})
    return {"rows": result, "lowest_spelling_ambiguous": ambiguous,
            "raw_extreme_sound_count": len(result), "ordinary_assumed_shape": shape,
            "structural_bass": "unassessed", "structural_melody": "unassessed"}


def _transition(left, right, sound_map, entries, graph_by_lane, when):
    a, b = left["sound_ref"], right["sound_ref"]
    lane = tuple(left["raw_lane"])
    entry, graph = entries.get(lane), graph_by_lane.get(lane)
    source, target = sound_map[a], sound_map[b]
    same = a == b
    required = [] if same else [[a, b]]
    observed_contiguous = same or common.f(source["span"]["end"]) == common.f(target["span"]["start"])
    reasons = [*_source_blockers(source), *_source_blockers(target)]
    if graph is None:
        reasons.append("raw_lane_graph_unavailable")
    elif graph["status"] != "ready":
        reasons.append("raw_lane_graph_not_ready")
    if entry is None:
        reasons.append("same_raw_lane_completion_unavailable")
    links = set() if entry is None else {tuple(p) for p in entry["witness"]["assignment"]["links"]}
    satisfied = same or (a, b) in links
    status = ("unassessed_prerequisites" if reasons else "literal_same_sound_carry_under_bundle" if same else
              "required_link_satisfied_under_this_bundle" if satisfied else
              "not_satisfied_under_this_bundle_not_global_absence")
    return {"source_sound_ref": a, "arrival_sound_ref": b, "raw_lane": list(lane),
            "source_extreme_axes": deepcopy(left["extreme_axes"]), "arrival_extreme_axes": deepcopy(right["extreme_axes"]),
            "boundary_time": common.q(when), "same_sound_carry": same,
            "required_links": required, "observed_direct_temporal_contiguity": observed_contiguous,
            "graph_ref": None if graph is None else common.ref(graph),
            "query_ref": None if entry is None else deepcopy(entry["query_ref"]),
            "witness_ref": None if entry is None else deepcopy(entry["witness_ref"]),
            "completion_id": None if entry is None else entry["completion_id"],
            "status": status, "blockers": sorted(set(reasons)),
            "true_voice_identity_confirmed": False, "absence_is_global": False,
            "structural_motion_confirmed": False}


def _budget(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_cadence_budget_required:" + name)


def _shared(view, bundle, graphs):
    # Public preparation verifies all declared graphs, even those without a
    # completion. No private handle is consumed or exposed by this module.
    resolution.prepare_bundle(view, bundle["path_registry"], graphs, bundle)
    return {"entries": {tuple(e["lane"]): e for e in bundle["entries"]},
            "graph_by_lane": {tuple(g["lane"]): g for g in graphs},
            "notes": {n["note_id"]: n for n in view["note_snapshots"]},
            "sound_map": {s["sound_id"]: s for s in view["sounds"]},
            "boundaries": {}, "probes": {}}


def _observe_owned(view, path, key_track, functions, bundle, graphs, max_pairs, shared):
    """Private builder using only freshly validated parents of this call."""
    entries, graph_by_lane, notes, sound_map = (shared[name] for name in ("entries", "graph_by_lane", "notes", "sound_map"))
    positions = sorted({common.f(s["span"][k]) for s in path["segments"] for k in ("start", "end")})
    boundaries, planned_pairs = [], 0
    for when in positions:
        left = next((s for s in path["segments"] if common.f(s["span"]["end"]) == when), None)
        right = next((s for s in path["segments"] if common.f(s["span"]["start"]) == when), None)
        if when not in shared["boundaries"]:
            shared["boundaries"][when] = comparison.boundary_evidence(view, when)
        evidence = shared["boundaries"][when]
        previous = _extreme_inventory(view, evidence, "before", left, _key_at(key_track, when, before=True), notes, shared["probes"])
        arrival = _extreme_inventory(view, evidence, "at", right, _key_at(key_track, when), notes, shared["probes"])
        count = sum(a["raw_lane"] == b["raw_lane"] for a in previous["rows"] for b in arrival["rows"])
        planned_pairs += count
        boundaries.append({"boundary_time": common.q(when), "boundary_ref": common.ref(evidence),
                           "literal_boundary_snapshot": deepcopy(evidence),
                           "left_assumed_segment_ref": None if left is None else left["segment_id"],
                           "arrival_assumed_segment_ref": None if right is None else right["segment_id"],
                           "before_extremes": previous, "arrival_extremes": arrival,
                           "planned_same_raw_lane_pairs": count, "same_raw_lane_transitions": [],
                           "cadence_prerequisites": {kind: {"status": "unassessed_missing_semantic_prerequisites",
                               "missing_premises": list(MISSING_PREMISES), "confirmed": False}
                               for kind in ("PAC", "HC", "IAC")},
                           "selected": None})
    exceeded = planned_pairs > max_pairs
    if not exceeded:
        for boundary in boundaries:
            boundary["same_raw_lane_transitions"] = [
                _transition(a, b, sound_map, entries, graph_by_lane, common.f(boundary["boundary_time"]))
                for a in boundary["before_extremes"]["rows"] for b in boundary["arrival_extremes"]["rows"]
                if a["raw_lane"] == b["raw_lane"]]
    for boundary in boundaries:
        boundary["transition_inventory_status"] = "whole_record_pair_budget_abstention" if exceeded else "all_declared_same_raw_lane_pairs_observed"
    return common.seal({"version": VERSION, "binding": deepcopy(view["binding"]),
        "view_ref": common.ref(view), "path_ref": common.ref(path), "key_track_ref": common.ref(key_track),
        "functions_ref": common.ref(functions), "completion_bundle_ref": common.ref(bundle),
        "function_inventory_status": functions["status"],
        "graph_refs": sorted([common.ref(g) for g in graphs], key=lambda r: r["record_id"]),
        "context_span": deepcopy(view["context_span"]), "target_span": deepcopy(view["target_span"]),
        "covered_lanes": deepcopy(bundle["covered_lanes"]), "missing_lanes": deepcopy(bundle["missing_lanes"]),
        "max_pairs": max_pairs, "planned_same_raw_lane_pairs": planned_pairs,
        "observed_same_raw_lane_pairs": 0 if exceeded else planned_pairs,
        "path_boundary_count": len(positions), "boundaries": boundaries,
        "status": "whole_record_pair_budget_abstention" if exceeded else "prerequisite_observations_complete_not_cadence_assessed",
        "reasons": ["whole_same_raw_lane_pair_inventory_exceeds_budget_no_pruning"] if exceeded else [],
        "meter_basis": "IR_notated_coordinates_not_certified_XML_meter_or_perceived_accent",
        "flags": deepcopy(FLAGS),
        "limits": ["All path boundaries, including starts, endpoints and same-member splits, remain visible.",
                   "A harmony arrival and a possible terminal release are distinct coordinates.",
                   "Equal-height spellings and every raw extreme are preserved; no structural voice is chosen.",
                   "One explicit bundle, no union of independent lane or alternative witnesses.",
                   "Written durations and rests are not performed timing or proof of phrase closure.",
                   "Sustain, ornaments and context exhaustion are not universal cadence evidence or counterevidence."]}, PREFIX)


def observe_prerequisites(view, path, key_track, functions, bundle, graphs, *, max_pairs=65536):
    """Retain complete declared boundaries and one supplied completion's axes.

    Source authority remains at the caller's exact view/IR/observation/audit
    replay boundary. This function validates intrinsic records and all explicit
    graph/bundle bindings; no caller checksum grants a validation waiver.
    """
    _budget(max_pairs, "max_pairs")
    before = common.digest([view, path, key_track, functions, bundle, graphs])
    common.validate_path(view, path)
    overlay.validate_key_track(view, key_track)
    overlay.validate_functions(view, path, key_track, functions, max_candidates=functions["max_candidates"])
    shared = _shared(view, bundle, graphs)
    if common.ref(path) not in bundle["path_refs"]:
        raise ValueError("cadence_path_not_in_explicit_completion_registry")
    result = _observe_owned(view, path, key_track, functions, bundle, graphs, max_pairs, shared)
    if common.digest([view, path, key_track, functions, bundle, graphs]) != before:
        raise ValueError("cadence_prerequisite_inputs_mutated")
    return result


def validate_prerequisites(record, *, view, path, key_track, functions, bundle, graphs):
    common.check(record, PREFIX)
    if record != observe_prerequisites(view, path, key_track, functions, bundle, graphs, max_pairs=record["max_pairs"]):
        raise ValueError("stale_foreign_or_modified_cadence_prerequisites")
    return True


def observe_all_prerequisites(view, paths, overlays, bundle, graphs, *, max_records=4096, max_pairs=65536):
    """Validate complete declared parents once, observe every path/key overlay.

    The Cartesian inventory is exact for the explicit supplied key tracks, not
    a claim that all possible musical keys have been inferred or enumerated.
    Shared objects are call-local and freshly validated, never caller handles.
    """
    _budget(max_records, "max_records")
    _budget(max_pairs, "max_pairs")
    before = common.digest([view, paths, overlays, bundle, graphs])
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("explicit_nonempty_cadence_path_registry_required")
    if not isinstance(overlays, (list, tuple)) or not overlays:
        raise ValueError("explicit_nonempty_cadence_overlay_registry_required")
    indexed = {}
    for path in paths:
        common.validate_path(view, path)
        if path["record_id"] in indexed:
            raise ValueError("duplicate_cadence_path")
        indexed[path["record_id"]] = path
    registry = [indexed[identity] for identity in sorted(indexed)]
    if registry != bundle["path_registry"]:
        raise ValueError("cadence_complete_path_registry_mismatch")
    shared = _shared(view, bundle, graphs)
    seen, tracks = set(), {}
    ordered = []
    for pair in overlays:
        if not isinstance(pair, dict) or set(pair) != {"key_track", "functions"}:
            raise ValueError("closed_cadence_overlay_entry_required")
        key_track, functions = pair["key_track"], pair["functions"]
        path = indexed.get(functions.get("path_ref", {}).get("record_id"))
        if path is None or functions["path_ref"] != common.ref(path):
            raise ValueError("cadence_foreign_overlay_path")
        overlay.validate_key_track(view, key_track)
        overlay.validate_functions(view, path, key_track, functions, max_candidates=functions["max_candidates"])
        identity = (path["record_id"], key_track["record_id"])
        if identity in seen:
            raise ValueError("duplicate_cadence_path_key_overlay")
        seen.add(identity)
        tracks[key_track["record_id"]] = key_track
        ordered.append(pair)
    expected = {(p["record_id"], key_id) for p in registry for key_id in tracks}
    if seen != expected:
        raise ValueError("incomplete_cadence_path_key_cartesian_inventory")
    ordered.sort(key=lambda pair: pair["functions"]["record_id"])
    count = len(ordered)
    records = []
    exceeded = count > max_records
    if not exceeded:
        for pair in ordered:
            functions, key_track = pair["functions"], pair["key_track"]
            records.append(_observe_owned(view, indexed[functions["path_ref"]["record_id"]],
                                          key_track, functions, bundle, graphs, max_pairs, shared))
    if common.digest([view, paths, overlays, bundle, graphs]) != before:
        raise ValueError("cadence_bulk_prerequisite_inputs_mutated")
    return common.seal({"version": VERSION, "view_ref": common.ref(view), "binding": deepcopy(view["binding"]),
                       "path_refs": [common.ref(p) for p in registry],
                       "overlay_refs": [common.ref(p["functions"]) for p in ordered],
                       "key_track_refs": [common.ref(tracks[k]) for k in sorted(tracks)],
                       "completion_bundle_ref": common.ref(bundle),
                       "graph_refs": sorted([common.ref(g) for g in graphs], key=lambda r: r["record_id"]),
                       "context_span": deepcopy(view["context_span"]), "target_span": deepcopy(view["target_span"]),
                       "max_records": max_records, "max_pairs": max_pairs, "planned_records": count,
                       "records": records, "record_refs": [common.ref(r) for r in records],
                       "status": "withheld_whole_record_budget" if exceeded else "observed_prerequisite_inventory",
                       "reasons": ["whole_overlay_record_inventory_exceeds_budget_no_pruning"] if exceeded else [],
                       "flags": deepcopy(FLAGS),
                       "scope": "all_explicit_paths_times_all_explicit_key_tracks_under_one_bundle_not_all_possible_music",
                       "limits": ["Shared fresh parent validation does not select a key, chord, voice or cadence.",
                                  "Per-record whole pair guards remain visible, never partial transition successes."]}, BATCH_PREFIX)


def validate_all_prerequisites(record, *, view, paths, overlays, bundle, graphs):
    common.check(record, BATCH_PREFIX)
    fresh = observe_all_prerequisites(view, paths, overlays, bundle, graphs,
                                     max_records=record["max_records"], max_pairs=record["max_pairs"])
    if record != fresh:
        raise ValueError("stale_foreign_or_modified_cadence_prerequisite_batch")
    return True
