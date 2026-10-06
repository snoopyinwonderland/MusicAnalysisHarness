"""Separate literal evidence axes under one shared completion bundle.

Caller key/function hypotheses and direct-link completions are not selected
analyses.  Written heights, metric coordinates and arrivals do not establish
structural voices, perceived accents, consonance or cadences.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from itertools import combinations

from . import factor_musical_view as common
from . import factor_musical_joint as musical
from . import factor_musical_rules as musical_rules

VERSION = "factor-functional-comparison-0.1.0"
PREFIX = "fmfcmp_"
BOUNDARY_PREFIX = "fmbound_"
BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTERS = "CDEFGAB"
FLAGS = {"selected": None, "ranked": False, "preferred": None,
         "key_confirmed": False, "function_confirmed": False,
         "structural_bass_confirmed": False, "structural_melody_confirmed": False,
         "cadence_confirmed": False, "consonance_certified": False,
         "perceived_accent_certified": False, "phrase_closure_certified": False,
         "source_labels_used": False, "key_signature_used": False,
         "musical_accuracy_measured": False, "training_eligible": False,
         "gold_eligible": False, "generation_ready": False,
         "all_part_lane_accounts_summed": False, "independent_completions_unioned": False}


def _time(value):
    if isinstance(value, dict):
        return common.f(value)
    if type(value) is int or isinstance(value, Fraction):
        return Fraction(value)
    raise ValueError("exact_notated_time_required")


def _height(pitch):
    step, alter, octave = common.pitch_key(pitch, octave=True)
    return Fraction(12 * (octave + 1) + BASE[step]) + alter


def _extent(sound):
    return common.span_bounds(sound["observed_span"])


def _note_end(note):
    return common.f(note["global_onset_quarter"]) + common.f(note["notated_duration_quarter"])


def _metric(view, when):
    rows = []
    for measure in view["measure_snapshots"]:
        start = common.f(measure["global_start_quarter"])
        end = start + common.f(measure["actual_duration_quarter"])
        if not start <= when < end:
            continue
        unit = Fraction(4, measure["time_signature"]["beat_type"])
        offset = when - start
        rows.append({"measure_id": measure["measure_id"],
                     "printed_measure_number": measure["printed_measure_number"],
                     "sequential_measure_index": measure["sequential_measure_index"],
                     "measure_span": {"start": common.q(start), "end": common.q(end)},
                     "time_signature": deepcopy(measure["time_signature"]),
                     "offset_quarter": common.q(offset), "notated_beat_unit_quarter": common.q(unit),
                     "notated_beat_coordinate": common.q(offset / unit + 1),
                     "at_notated_measure_start": offset == 0, "pickup": measure["pickup"],
                     "perceived_accent": "unassessed"})
    return {"status": "exact_notated_coordinates" if rows else "notated_coordinate_unavailable",
            "coordinates": rows, "ambiguous_measure_inventory": len(rows) > 1,
            "perceived_accent_certified": False, "key_signature_used": False}


def _extremes(rows):
    if not rows:
        return {"lowest_sound_refs": [], "highest_sound_refs": [],
                "lowest_written_height": None, "highest_written_height": None,
                "intervals_above_observed_lowest": [], "generic_fourth_and_sixth_present": False,
                "structural_bass": "unassessed", "structural_melody": "unassessed",
                "consonance": "unassessed", "concert_pitch_certified": False}
    low, high = min(_height(r["pitch"]) for r in rows), max(_height(r["pitch"]) for r in rows)
    lowest = [r for r in rows if _height(r["pitch"]) == low]
    intervals = []
    for lower in lowest:
        lower_index = lower["pitch"]["octave"] * 7 + LETTERS.index(lower["pitch"]["step"])
        for upper in rows:
            steps = upper["pitch"]["octave"] * 7 + LETTERS.index(upper["pitch"]["step"]) - lower_index
            intervals.append({"lowest_sound_ref": lower["sound_id"], "sound_ref": upper["sound_id"],
                              "written_diatonic_steps": steps,
                              "written_chromatic_semitones": common.q(_height(upper["pitch"]) - low)})
    classes = {row["written_diatonic_steps"] % 7 for row in intervals}
    return {"lowest_sound_refs": [r["sound_id"] for r in lowest],
            "highest_sound_refs": [r["sound_id"] for r in rows if _height(r["pitch"]) == high],
            "lowest_written_height": common.q(low), "highest_written_height": common.q(high),
            "intervals_above_observed_lowest": intervals,
            "generic_fourth_and_sixth_present": {3, 5} <= classes,
            "structural_bass": "unassessed", "structural_melody": "unassessed",
            "consonance": "unassessed", "concert_pitch_certified": False}


def _boundary_payload(view, when):
    c, d = common.span_bounds(view["context_span"])
    if not c <= when <= d:
        raise ValueError("boundary_outside_context")
    positive = view["sounds"]
    before = [r for r in positive if _extent(r)[0] < when <= _extent(r)[1]]
    at = [r for r in positive if _extent(r)[0] <= when < _extent(r)[1]] if when < d else []
    starts = [r["sound_id"] for r in positive if common.f(r["span"]["start"]) == when]
    ends = [r["sound_id"] for r in positive if common.f(r["span"]["end"]) == when]
    carries = [r["sound_id"] for r in positive if common.f(r["span"]["start"]) < when < common.f(r["span"]["end"])]
    points = [r["sound_id"] for r in view["points"] if common.f(r["span"]["start"]) == when]
    notes = {r["note_id"]: r for r in view["note_snapshots"]}
    attack_ids = [r["attack_note_id"] for r in [*positive, *view["points"]]
                  if common.f(notes[r["attack_note_id"]]["global_onset_quarter"]) == when]
    rests = []
    for rest in view["rest_snapshots"]:
        start, end = common.f(rest["global_onset_quarter"]), _note_end(rest)
        if start < end and max(start, when) < min(end, d):
            rests.append({"rest_id": rest["rest_id"], "lane": [rest["part_id"], rest["voice_id"]],
                          "observed_following_span": {"start": common.q(max(start, when, c)),
                                                      "end": common.q(min(end, d))}})
    later = [r for r in positive if _extent(r)[1] > when]
    later_attacks = [r["attack_note_id"] for r in [*positive, *view["points"]]
                     if when < common.f(notes[r["attack_note_id"]]["global_onset_quarter"]) < d]
    boundary_sound_ids = {x["sound_id"] for x in [*before, *at]}
    point_ids = set(points)
    source_rows = [r for r in [*positive, *view["points"]]
                   if r["sound_id"] in boundary_sound_ids or r["sound_id"] in point_ids]
    guards = [{"sound_ref": r["sound_id"], "source_clock_passed": r["source_clock_passed"],
               "source_pitch_consistency_passed": r["source_pitch_consistency_passed"],
               "source_diagnostics": deepcopy(r["source_diagnostics"])} for r in source_rows]
    return {"version": VERSION, "view_ref": common.ref(view), "binding": deepcopy(view["binding"]),
            "context_span": deepcopy(view["context_span"]), "target_span": deepcopy(view["target_span"]),
            "boundary_time": common.q(when),
            "observation_status": "inside_observed_context" if when < d else "context_endpoint_not_following_observation",
            "positive_sound_refs_before": [r["sound_id"] for r in before],
            "positive_sound_refs_at": [r["sound_id"] for r in at],
            "full_sound_start_refs": starts, "full_sound_end_refs": ends,
            "full_sound_continuing_refs": carries, "point_sound_refs_at": points,
            "attack_note_refs_at": attack_ids, "source_guards": guards,
            "lowest_highest_before": _extremes(before), "lowest_highest_at": _extremes(at),
            "notated_metric": _metric(view, when),
            "following": {"observed_positive_sound_refs": [r["sound_id"] for r in later],
                          "observed_later_attack_note_refs": later_attacks,
                          "observed_following_rest_spans": rests,
                          "known_full_sound_refs_extending_beyond_context": [r["sound_id"] for r in positive
                              if common.f(r["span"]["end"]) > d],
                          "context_ends_here": when == d,
                          "no_observed_positive_after_boundary": not later,
                          "phrase_closure": "unassessed", "performed_timing_certified": False},
            "flags": deepcopy(FLAGS)}


def boundary_evidence(view, time):
    """Literal exact-clock coordinates, never a cadence or structural voice."""
    common.validate_view(view)
    return common.seal(_boundary_payload(view, _time(time)), BOUNDARY_PREFIX)


def validate_boundary_evidence(record, view, time):
    common.check(record, BOUNDARY_PREFIX)
    if record != boundary_evidence(view, time):
        raise ValueError("stale_foreign_or_modified_boundary_evidence")
    return True


def _paths(view, paths):
    values = [paths] if isinstance(paths, dict) else paths
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("explicit_nonempty_competing_paths_required")
    records = {}
    for path in values:
        common.validate_path(view, path)
        identity = path["record_id"]
        if identity in records:
            raise ValueError("duplicate_competing_path")
        records[identity] = path
    return [records[k] for k in sorted(records)]


def _budget(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_comparison_budget_required:" + name)


def _raw_accounts(view, paths):
    """One all-part literal denominator; never sum lane copies of it."""
    start, end = common.span_bounds(view["target_span"])
    boundaries = {start, end}
    for sound in view["sounds"]:
        boundaries.update(t for t in _extent(sound) if start < t < end)
    for path in paths:
        for segment in path["segments"]:
            boundaries.update(t for t in common.span_bounds(segment["span"]) if start < t < end)
    ordered = sorted(boundaries)
    cells = [{"start": common.q(a), "end": common.q(b)} for a, b in zip(ordered, ordered[1:])]
    results = []
    for path in paths:
        totals = {name: Fraction(0) for name in ("member", "nonmember", "unknown")}
        for cell in cells:
            a, b = common.span_bounds(cell)
            segment = next(s for s in path["segments"] if common.f(s["span"]["start"]) <= a < common.f(s["span"]["end"]))
            members = {common.pitch_key(p) for p in segment["members"]}
            for sound in view["sounds"]:
                lo, hi = _extent(sound)
                if lo >= b or hi <= a:
                    continue
                # Raw supplied member arithmetic survives candidate blockers;
                # qualification is a separate axis in the old lane accounts.
                kind = "member" if common.pitch_key(sound["pitch"]) in members else "nonmember"
                totals[kind] += min(b, hi) - max(a, lo)
        results.append({"path_ref": common.ref(path), "raw_note_time": {k: common.q(v) for k, v in totals.items()},
                        "total_all_part_note_time": common.q(sum(totals.values())),
                        "membership_is_consonance": False})
    return cells, results


def _transpose(tonic, steps, semitones):
    index = LETTERS.index(tonic["step"]) + steps
    chromatic = Fraction(BASE[tonic["step"]]) + common.f(tonic["alter"]) + semitones
    return {"step": LETTERS[index % 7],
            "alter": common.q(chromatic - BASE[LETTERS[index % 7]] - 12 * (index // 7))}


def _key_at(track, when):
    return next((row for row in track["segments"]
                 if common.f(row["span"]["start"]) <= when < common.f(row["span"]["end"])), None)


def _triad(tonic, mode):
    return [tonic, _transpose(tonic, 2, 4 if mode == "major" else 3), _transpose(tonic, 4, 7)]


def _profile(value, supporters, blockers):
    reasons = sorted(set(blockers))
    return {"raw_assumed_shape_compatible": value,
            "status": ("withheld_prerequisites" if reasons else
                       "shape_compatible_not_cadence_confirmation" if value is True else
                       "shape_not_compatible" if value is False else "unassessed"),
            "supporting_function_refs": sorted(set(supporters)), "blockers": reasons,
            "cadence_confirmed": False}


def _profiles(view, path, key_track, functions, when, evidence, *, _row_index=None):
    left = next((s for s in path["segments"] if common.f(s["span"]["end"]) == when), None)
    right = next((s for s in path["segments"] if common.f(s["span"]["start"]) == when), None)
    key = _key_at(key_track, when)
    roots = {"left_segment_ref": None if left is None else left["segment_id"],
             "right_segment_ref": None if right is None else right["segment_id"],
             "left_root": None if left is None else deepcopy(left["root"]),
             "right_root": None if right is None else deepcopy(right["root"]),
             "key_segment_ref": None if key is None else key["segment_id"],
             "key_tonic": None if key is None else deepcopy(key["tonic"]),
             "key_mode": None if key is None else key["mode"],
             "scale_form": None if key is None else key["scale_form"]}
    blockers = []
    if right is None:
        blockers.append("next_assumed_segment_not_available_at_boundary")
    elif right["status"] != "usable":
        blockers.extend(["arrival_harmony_segment_blocked", *right["blockers"]])
    if key is None or key["tonic"] is None or key["mode"] == "unknown":
        blockers.append("explicit_local_key_unassessed")
    elif common.f(key["tonic"]["alter"]).denominator != 1:
        blockers.append("ordinary_microtonal_key_profile_not_supported")
    if not evidence["positive_sound_refs_at"]:
        blockers.append("actual_boundary_positive_sounds_not_observed")
    if any(r["source_clock_passed"] is not True for r in evidence["source_guards"]):
        blockers.append("involved_source_clock_not_established")
    if any(r["source_pitch_consistency_passed"] is not True for r in evidence["source_guards"]):
        blockers.append("involved_source_written_pitch_not_established")
    if evidence["point_sound_refs_at"]:
        blockers.append("grace_performed_timing_not_established")
    if functions["status"] != "ready":
        blockers.extend(["function_inventory_not_assessed", *functions["reasons"]])
    ordinary = (right is not None and right["root"] is not None and key is not None
                and key["tonic"] is not None and key["mode"] != "unknown"
                and common.f(key["tonic"]["alter"]).denominator == 1)
    # This optional private index is derived locally AFTER fresh validation;
    # it shares lookup work only, not a prerequisite or validation waiver.
    if _row_index is None:
        _row_index = defaultdict(list)
        for index, row in enumerate(functions["rows"]):
            _row_index[row["source_segment_ref"]].append((index, row))
    left_rows = [] if left is None else _row_index.get(left["segment_id"], [])
    right_rows = [] if right is None else _row_index.get(right["segment_id"], [])
    source_rows = [r for _, r in left_rows
                   if r["shape_compatible"] is True and r["function_kind"] == "primary"
                   and (key is None or r["key_segment_ref"] == key["segment_id"])]
    arrival_rows = [r for _, r in right_rows
                    if r["shape_compatible"] is True and r["function_kind"] == "primary"
                    and r["family"] in ("V", "V7")
                    and (key is None or r["key_segment_ref"] == key["segment_id"])]
    tonic = dominant = deceptive = None
    if ordinary:
        members = {common.pitch_key(p) for p in right["members"]}
        tonic = (common.pitch_key(right["root"]) == common.pitch_key(key["tonic"])
                 and {common.pitch_key(p) for p in _triad(key["tonic"], key["mode"])} <= members)
        dominant = (common.pitch_key(right["root"]) == common.pitch_key(_transpose(key["tonic"], 4, 7))
                    and bool(arrival_rows))
        sixth_semitones = {"major": 9, "natural_minor": 8, "harmonic_minor": 8,
                           "melodic_minor_ascending": 9}.get(key["scale_form"])
        if sixth_semitones is not None:
            deceptive = (bool([r for r in source_rows if r["family"] in ("V", "V7")])
                         and common.pitch_key(right["root"]) == common.pitch_key(_transpose(key["tonic"], 5, sixth_semitones)))
    source_blockers = [reason for r in source_rows for reason in r["blockers"]]
    arrival_blockers = [reason for r in arrival_rows for reason in r["blockers"]]
    profile_rows = {
        "tonic_arrival": _profile(tonic, [r["function_id"] for r in source_rows], blockers + source_blockers),
        "dominant_arrival": _profile(dominant, [r["function_id"] for r in arrival_rows], blockers + arrival_blockers),
        "deceptive_like_arrival": _profile(deceptive, [r["function_id"] for r in source_rows if r["family"] in ("V", "V7")],
            blockers + source_blockers + (["explicit_scale_form_coordinate_unassessed"] if ordinary and deceptive is None else []))}
    unsupported = ["structural_bass_identity_unestablished", "structural_melody_identity_unestablished",
                   "perceived_accent_unestablished", "consonance_unestablished",
                   "phrase_terminal_boundary_unestablished", "performed_timing_unestablished"]
    if evidence["following"]["observed_later_attack_note_refs"] or evidence["full_sound_continuing_refs"]:
        unsupported.append("observed_continuation_does_not_certify_phrase_closure")
    if evidence["lowest_highest_at"]["generic_fourth_and_sixth_present"]:
        unsupported.append("observed_generic_six_four_does_not_certify_consonance")
    candidates = [r for _, r in sorted([*left_rows, *right_rows], key=lambda item: item[0])]
    return {"assumed_harmony_and_key": roots, "compatibility": profile_rows,
            "all_candidate_function_refs": [r["function_id"] for r in candidates],
            "candidate_function_prerequisites": [{"function_ref": r["function_id"],
                "status": r["status"], "function_kind": r["function_kind"],
                "shape_compatible": r["shape_compatible"], "target_shape_compatible": r["target_shape_compatible"],
                "key_projection_assessed": r["prerequisites"]["key_projection_assessed"],
                "key_covers_relation_span": r["prerequisites"]["key_covers_relation_span"],
                "target_basis": r["target_basis"], "blockers": deepcopy(r["blockers"])} for r in candidates],
            "cadence_premises": {"PAC": {"status": "unassessed_missing_structural_and_terminal_premises",
                                         "blockers": unsupported, "confirmed": False},
                                  "HC": {"status": "unassessed_missing_terminal_and_functional_premises",
                                         "blockers": sorted(set([*unsupported, "dominant_arrival_alone_is_not_half_cadence"])),
                                         "confirmed": False}},
            "selected": None}


def compare_functional(view, paths, overlays, bundle, *, max_resolution_candidates=1024,
                       max_chain_edges=8, max_nct_candidates=4096):
    """Compare all declared hypotheses under ONE multi-lane completion bundle.

    Each lane's old all-part account is a separate conditional experiment. Its
    denominator is checked against the one literal raw account, never added to
    another lane's copy. No evidence axis is weighted, ranked or selected.
    """
    from . import factor_functional_overlay as functional
    from . import factor_functional_resolution as resolution
    common.validate_view(view)
    paths = _paths(view, paths)
    for value, name in ((max_resolution_candidates, "resolution_candidates"), (max_chain_edges, "chain_edges"),
                        (max_nct_candidates, "nct_candidates")):
        _budget(value, name)
    if not isinstance(overlays, (list, tuple)) or not overlays:
        raise ValueError("explicit_nonempty_functional_interpretations_required")
    before = common.digest([view, paths, overlays, bundle])
    path_map = {p["record_id"]: p for p in paths}
    interpretations = {}
    for pair in overlays:
        if not isinstance(pair, dict) or set(pair) != {"key_track", "functions"}:
            raise ValueError("closed_key_track_and_functions_interpretation_required")
        record = pair["functions"]
        path = path_map.get(record["path_ref"]["record_id"])
        if path is None or record["path_ref"] != common.ref(path):
            raise ValueError("functional_path_not_in_shared_registry")
        functional.validate_functions(view, path, pair["key_track"], record, max_candidates=record["max_candidates"])
        if record["record_id"] in interpretations:
            raise ValueError("duplicate_functional_interpretation")
        interpretations[record["record_id"]] = pair
    interpretations = [interpretations[k] for k in sorted(interpretations)]
    graphs = [entry["graph"] for entry in bundle["entries"]]
    # A locally issued immutable handle owns the one freshly verified full
    # registry. Per-interpretation compilation remains freshly bound to its
    # own path/key/functions; public comparison validation starts here again.
    prepared = resolution.prepare_bundle(view, paths, graphs, bundle)
    cells, raw = _raw_accounts(view, paths)
    raw_map = {r["path_ref"]["record_id"]: r for r in raw}
    positions_by_path = {path["record_id"]: tuple(sorted(
        {common.f(t) for t in view["target_span"].values()} |
        {common.f(s["span"][k]) for s in path["segments"] for k in ("start", "end")}))
        for path in paths}
    # Immutable view projection is shared by every key/function reading. There
    # is one full boundary record for each exact timestamp, not one per overlay.
    all_positions = {common.f(t) for t in view["target_span"].values()}
    all_positions.update(common.f(s["span"][k]) for path in paths for s in path["segments"] for k in ("start", "end"))
    boundary_records = {when: common.seal(_boundary_payload(view, when), BOUNDARY_PREFIX) for when in sorted(all_positions)}
    lane_comparisons = []
    lane_accounts_by_path = []
    registry = []
    for entry in bundle["entries"]:
        graph, query, witness = entry["graph"], entry["query"], entry["witness"]
        compiled = [musical_rules.compile_rules(view, path, graph, max_candidates=max_nct_candidates) for path in paths]
        account = musical.compare_under_completion(view, paths, graph, query, witness, compiled)
        for row in account["accounts"]:
            if row["raw_note_time"] != raw_map[row["path_ref"]["record_id"]]["raw_note_time"]:
                raise ValueError("lane_copy_raw_membership_denominator_mismatch")
        lane_comparisons.append({"lane": deepcopy(entry["lane"]), "comparison": account,
                                 "compiled_refs": [common.ref(r) for r in compiled]})
        lane_accounts_by_path.append({r["path_ref"]["record_id"]: r for r in account["accounts"]})
        registry.append({k: deepcopy(entry[k]) for k in ("lane", "graph_ref", "query_ref", "witness_ref", "completion_id")})
    evaluations, vectors = [], []
    for pair in interpretations:
        functions, key_track = pair["functions"], pair["key_track"]
        path = path_map[functions["path_ref"]["record_id"]]
        evaluated = resolution._assess_prepared(prepared, path, key_track, functions,
            max_candidates=max_resolution_candidates, max_chain_edges=max_chain_edges)
        evaluations.append(evaluated)
        row_index, assessment_index = defaultdict(list), defaultdict(list)
        for index, row in enumerate(functions["rows"]):
            row_index[row["source_segment_ref"]].append((index, row))
        for index, row in enumerate(evaluated["assessments"]):
            assessment_index[row["function_ref"]].append((index, row))
        boundaries = []
        for when in positions_by_path[path["record_id"]]:
            evidence = boundary_records[when]
            boundary_profiles = _profiles(view, path, key_track, functions, when, evidence, _row_index=row_index)
            candidate_ids = set(boundary_profiles["all_candidate_function_refs"])
            function_ids = {r["function_id"] for r in functions["rows"]
                            if r["function_id"] in candidate_ids
                            and common.f(r["source_span"]["end"]) == when}
            assessments = []
            active_assessments = sorted([indexed for identity in function_ids
                                         for indexed in assessment_index.get(identity, [])], key=lambda indexed: indexed[0])
            for _, row in active_assessments:
                # Full rule/motion snapshots live once in the central sealed
                # evaluation. Keep every outcome/ref, including failed facts.
                item = {k: deepcopy(v) for k, v in row.items() if k != "rule_snapshot"}
                item["rule_snapshot_ref"] = {"evaluation_ref": common.ref(evaluated),
                                             "resolution_ref": row["resolution_ref"]}
                item["literal_motion_observation_refs"] = [o["observation_id"] for o in row["rule_snapshot"]["observations"]]
                assessments.append(item)
            boundaries.append({"boundary_ref": common.ref(evidence), "boundary_time": common.q(when),
                               "functional_profiles": boundary_profiles,
                               "leading_tone_and_seventh_assessments": assessments,
                               "resolution_evaluation_ref": common.ref(evaluated)})
        nct = []
        for lane, account_index in zip(lane_comparisons, lane_accounts_by_path):
            comparison = lane["comparison"]
            account = account_index[path["record_id"]]
            nct.append({"lane": deepcopy(lane["lane"]), "comparison_ref": common.ref(comparison),
                        "path_ref": common.ref(path), "raw_note_time": deepcopy(account["raw_note_time"]),
                        "note_time": deepcopy(account["note_time"]),
                        "total_all_part_note_time": deepcopy(comparison["total_all_part_note_time"]),
                        "sampled_evaluation_note_time": deepcopy(comparison["sampled_evaluation_note_time"]),
                        "lane_accounts_are_not_additive": True})
        vectors.append({"path_ref": common.ref(path), "key_track_ref": common.ref(key_track),
                        "functions_ref": common.ref(functions), "resolution_evaluation_ref": common.ref(evaluated),
                        "raw_membership": deepcopy(raw_map[path["record_id"]]),
                        "nct_accounts_by_lane": nct, "boundary_evidence": boundaries,
                        "function_inventory_status": functions["status"],
                        "resolution_status": evaluated["status"], "selected": None})
    differences = []
    # Keys do not change literal path membership. Retain EVERY pair and its
    # original order, while sharing only the exact rational arithmetic by path.
    raw_values = {identity: {name: common.f(row["raw_note_time"][name])
                            for name in ("member", "nonmember", "unknown")}
                  for identity, row in raw_map.items()}
    difference_values = {}
    for first, second in combinations(vectors, 2):
        pair = (first["path_ref"]["record_id"], second["path_ref"]["record_id"])
        if pair not in difference_values:
            values = {name: raw_values[pair[1]][name] - raw_values[pair[0]][name]
                      for name in ("member", "nonmember", "unknown")}
            difference_values[pair] = {name: (value.numerator, value.denominator) for name, value in values.items()}
        delta = {name: {"numerator": value[0], "denominator": value[1]}
                 for name, value in difference_values[pair].items()}
        differences.append({"first_functions_ref": first["functions_ref"], "second_functions_ref": second["functions_ref"],
                            "raw_note_time_difference": delta, "difference_is_preference": False,
                            "axes_not_weighted_or_combined": True})
    body = {"version": VERSION, "binding": deepcopy(view["binding"]), "view_ref": common.ref(view),
            "context_span": deepcopy(view["context_span"]), "target_span": deepcopy(view["target_span"]),
            "path_refs": [common.ref(p) for p in paths],
            "overlay_refs": [common.ref(p["functions"]) for p in interpretations],
            "key_track_refs": sorted({p["key_track"]["record_id"]: common.ref(p["key_track"]) for p in interpretations}.values(), key=lambda r: r["record_id"]),
            "completion_bundle_ref": common.ref(bundle), "completion_registry": registry,
            "covered_lanes": deepcopy(bundle["covered_lanes"]), "missing_lanes": deepcopy(bundle["missing_lanes"]),
            "literal_target_cells": cells, "raw_membership_by_path": raw,
            "boundary_registry": list(boundary_records.values()),
            "lane_comparisons": lane_comparisons, "resolution_evaluations": evaluations,
            "evidence_vectors": vectors, "pairwise_differences": differences,
            "settings": {"max_resolution_candidates": max_resolution_candidates, "max_chain_edges": max_chain_edges,
                         "max_nct_candidates": max_nct_candidates},
            "flags": deepcopy(FLAGS),
            "limits": ["One shared completion bundle, no per-key or per-path witness choice.",
                       "All-part lane accounts are repeated conditional denominators, never additive.",
                       "Membership is not consonance; notated coordinates are not perceived accents.",
                       "Literal highest/lowest sounds do not identify structural melody/bass.",
                       "Arrival shapes, internal dominant arrivals and observed six-four intervals do not certify cadences.",
                       "Context exhaustion is not phrase closure; full sounding continuations stay visible."]}
    if before != common.digest([view, paths, overlays, bundle]):
        raise ValueError("functional_comparison_inputs_mutated")
    # The complete body above is private, locally owned output: all snapshots
    # crossing from caller inputs were copied, and pure producer results are
    # fresh records. Seal the SAME canonical bytes without copying the entire
    # large output again. No caller-supplied body/hash or validator skip exists.
    sha = common.digest(body)
    return {**body, "record_id": PREFIX + sha[:24], "record_sha256": sha}


def validate_comparison(record, *, view, paths, overlays, bundle):
    body = common.check(record, PREFIX)
    settings = body.get("settings")
    if not isinstance(settings, dict) or set(settings) != {"max_resolution_candidates", "max_chain_edges", "max_nct_candidates"}:
        raise ValueError("closed_comparison_settings_required")
    fresh = compare_functional(view, paths, overlays, bundle, **settings)
    if record != fresh:
        raise ValueError("stale_foreign_or_modified_functional_comparison")
    return True

