"""Fresh expanded-scope chord/key/continuity comparisons, without a winner.

The supplier catalog is an inclusive proposal envelope, not SOURCE provenance.
Only the full hold and every observed one-cut partition are proposed here.  No
old view, path, key track or completion bundle is enlarged or re-labelled.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import product
from pathlib import Path

from . import factor_expanded_scope as expanded
from . import harmony_candidate_catalog as catalog
from . import harmony_factorized_voice_paths as geometry
from . import applied_chords as applied
from . import tonal_foundations as tonal
from .applied_chords import hypothesis
from .musical_pattern_observation import digest, f, q, span_bounds
from .tonal_foundations import scale_degree

VERSION = "factor-expanded-hypotheses-0.1.0"
PREFIX = "fmeh_"
EVALUATION_PREFIX = "fmehc_"
PATH_PREFIX = "fmehpath_"
KEY_PREFIX = "newkey_"
BUNDLE_PREFIX = "fmehbundle_"
FAMILIES = ("V", "V7", "vii", "vii7", "vii_half7")
ROOT_INTERVALS = {"V": (4, 7), "V7": (4, 7), "vii": (6, 11),
                  "vii7": (6, 11), "vii_half7": (6, 11)}
LETTERS = "CDEFGAB"
NATURAL = dict(zip(LETTERS, (0, 2, 4, 5, 7, 9, 11)))
MAJOR_TONICS = (("C", -1), ("G", -1), ("D", -1), ("A", -1), ("E", -1),
                ("B", -1), ("F", 0), ("C", 0), ("G", 0), ("D", 0),
                ("A", 0), ("E", 0), ("B", 0), ("F", 1), ("C", 1))
MINOR_TONICS = (("A", -1), ("E", -1), ("B", -1), ("F", 0), ("C", 0),
                ("G", 0), ("D", 0), ("A", 0), ("E", 0), ("B", 0),
                ("F", 1), ("C", 1), ("G", 1), ("D", 1), ("A", 1))


def _flags():
    return {key: False for key in ("selected", "preferred", "key_inferred",
        "harmony_confirmed", "function_confirmed", "resolution_confirmed",
        "cadence_confirmed", "nct_confirmed", "training_eligible", "gold_eligible",
        "generation_ready", "source_labels_used", "production_modified",
        "counts_are_confidence", "old_path_or_bundle_reused", "musical_accuracy_measured")}


def _contract():
    modules = (expanded, catalog, geometry, applied, tonal)
    sources = [{"module": __name__, "sha256": sha256(Path(__file__).read_bytes()).hexdigest()}]
    sources.extend({"module": module.__name__, "sha256": sha256(Path(module.__file__).read_bytes()).hexdigest()}
                   for module in modules)
    # These provider modules contain the actual inclusive gate/templates; a
    # catalog facade's unchanged bytes alone do not establish their freshness.
    from . import harmony_augmented_candidates, harmony_extended_candidates
    from . import harmony_open_candidates, harmony_surface, harmony_candidate_explanation
    sources.extend({"module": module.__name__, "sha256": sha256(Path(module.__file__).read_bytes()).hexdigest()}
                   for module in (harmony_augmented_candidates, harmony_extended_candidates,
                                  harmony_open_candidates, harmony_surface, harmony_candidate_explanation))
    return {"version": VERSION, "sources": sources}


def _budget(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_budget_required:" + name)


def _seal(body, prefix):
    if "record_id" in body or "record_sha256" in body:
        raise ValueError("unsealed_body_required")
    body = deepcopy(body)
    checksum = digest(body)
    return {**body, "record_id": prefix + checksum[:24], "record_sha256": checksum}


def _check(record, prefix):
    body = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    checksum = digest(body)
    if record.get("record_sha256") != checksum or record.get("record_id") != prefix + checksum[:24]:
        raise ValueError("invalid_expanded_record_seal")
    return body


def _ref(record):
    return {key: record[key] for key in ("record_id", "record_sha256")}


def _span(start, end):
    return {"start": q(start), "end": q(end)}


def _overlap(left, right):
    a, b = span_bounds(left)
    c, d = span_bounds(right)
    return _span(max(a, c), min(b, d)) if max(a, c) < min(b, d) else None


def _pitch_key(pitch, octave=False):
    if (not isinstance(pitch, dict) or pitch.get("step") not in LETTERS
            or not isinstance(pitch.get("alter"), dict)):
        return None
    try:
        alteration = f(pitch["alter"])
    except (TypeError, ValueError, KeyError, ZeroDivisionError):
        return None
    result = (pitch["step"], alteration)
    if octave:
        if type(pitch.get("octave")) is not int:
            return None
        result += (pitch["octave"],)
    return result


def _pitch(pair):
    return None if pair is None else {"step": pair[0], "alter": q(pair[1])}


def _integer_pitch(pitch):
    key = _pitch_key(pitch)
    return key is not None and key[1].denominator == 1


def _old(pitch):
    if not _integer_pitch(pitch):
        raise ValueError("integer_spelling_required_for_ordinary_shape")
    return [pitch["step"], f(pitch["alter"]).numerator]


def _scope(ir, scope):
    # Fresh expanded literal extraction is required. This does not certify the
    # caller's old parent files; the runner separately replays those parents.
    expanded.check_scope(scope, ir=ir)
    if not scope["record_id"].startswith("fmes_"):
        raise ValueError("fresh_expanded_scope_required")


def _variant(scope, entry, candidate, candidate_index, alternative_index):
    alternatives = candidate["spelling_alternatives"]
    alternative = None if alternative_index is None else alternatives[alternative_index]
    blockers = list(candidate["abstention_reasons"])
    if alternative is None:
        blockers.append("supplier_spelling_unresolved_no_root_invented")
    body = {"scope_ref": _ref(scope), "span": deepcopy(entry["span"]),
        "catalog_id": entry["catalog_id"], "supplier_candidate_ref": candidate["candidate_id"],
        "provider": candidate["provider"], "supplier_record_pointer": "/candidates/" + str(candidate_index),
        "supplier_origin_pointer": candidate["origin_pointer"],
        "spelling_alternative_index": alternative_index,
        "root": None if alternative is None else _pitch(alternative["root_spelling"]),
        "members": None if alternative is None else [_pitch(p) for p in alternative["members"]],
        "member_pitch_classes": deepcopy(candidate["member_pitch_classes"]),
        "tonal_coordinate": deepcopy(candidate["tonal_coordinate"]),
        "missing_spellings": None if alternative is None else [
            _pitch(p) for p in candidate["missing_spellings_by_alternative"][alternative_index]],
        "missing_pitch_classes": deepcopy(candidate["missing_pitch_classes"]),
        "supplier_event_states": deepcopy(candidate["event_states"]),
        "supplier_note_time_quarters": deepcopy(candidate["note_time_quarters"]),
        "status": "spelling_withheld" if alternative is None else "conditional_spelled_candidate",
        "blockers": sorted(set(blockers)),
        "provenance": {"kind": "inclusive_catalog_proposal", "source_statement_ref": None,
                       "source_path": None, "source_annotation_labels_used": False},
        "selected": None}
    body["segment_id"] = "fmehseg_" + digest(body)[:24]
    return _seal(body, "fmehseg_")


def _key_candidates(ir, scope):
    start, end = span_bounds(scope["analysis_span"])
    declarations = []
    for measure in ir["measures"]:
        a = f(measure["global_start_quarter"])
        b = a + f(measure["actual_duration_quarter"])
        if max(start, a) < min(end, b):
            declarations.append({"measure_ref": measure["measure_id"],
                "measure_span": _span(a, b), "signature": deepcopy(measure.get("key_signature"))})
    declarations.sort(key=lambda row: (f(row["measure_span"]["start"]),
                                       f(row["measure_span"]["end"]), row["measure_ref"]))
    # Equal physical clock copies are retained, but do not create an overlap.
    clocks = sorted({span_bounds(row["measure_span"]) for row in declarations})
    cursor, covered, clock_ambiguous = start, True, False
    for a, b in clocks:
        lo, hi = max(start, a), min(end, b)
        if lo != cursor:
            covered = False
            clock_ambiguous |= lo < cursor
        cursor = max(cursor, hi)
    covered &= cursor == end
    values = [row["signature"].get("fifths") if isinstance(row["signature"], dict) else None
              for row in declarations]
    standard = bool(values) and all(type(v) is int and -7 <= v <= 7 for v in values)
    same = standard and len(set(values)) == 1
    usable = covered and not clock_ambiguous and same
    reasons = []
    if not covered:
        reasons.append("measure_clock_coverage_incomplete")
    if clock_ambiguous:
        reasons.append("distinct_physical_measure_clocks_overlap")
    if not standard:
        reasons.append("absent_nonstandard_or_microtonal_signature")
    elif not same:
        reasons.append("changing_or_contradictory_signature")
    specs = []
    if usable:
        fifths = values[0]
        major, minor = MAJOR_TONICS[fifths + 7], MINOR_TONICS[fifths + 7]
        specs = [(major, "major", "major"), (minor, "minor", "natural_minor"),
                 (minor, "minor", "harmonic_minor"), (minor, "minor", "melodic_minor_ascending")]
    specs.append((None, "unknown", "unknown"))
    keys = []
    for tonic, mode, form in specs:
        segment = {"segment_id": "newkeyseg_" + digest([_ref(scope), tonic, mode, form])[:24],
            "span": deepcopy(scope["analysis_span"]), "tonic": _pitch(tonic),
            "mode": mode, "scale_form": form}
        keys.append(_seal({"version": VERSION, "binding": deepcopy(scope["binding"]),
            "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]),
            "segments": [segment], "declarations": deepcopy(declarations),
            "status": "unknown_key_alternative" if tonic is None else "signature_compatible_key_hypothesis",
            "provenance": {"kind": "literal_IR_measure_key_signature_interpretation",
                "source_statement_ref": None, "source_path": None,
                "mode_hint_used_as_key": False, "interpretation_only": True,
                "signature_is_not_key_proof": True}, "reasons": sorted(set(reasons)),
            "exhaustive_local_key_universe": False,
            "unknown_covers_signature_external_alternatives": True, "flags": _flags()}, KEY_PREFIX))
    return keys


def build_hypotheses(ir, scope, *, max_catalogs=128, path_budget=128):
    """Keep every supplied candidate in each complete full/one-cut group.

    Budget guards withhold whole groups; they never select a top-k prefix.
    The span supplier is linear in the number of distinct observed cuts.
    """
    _budget(max_catalogs, "max_catalogs")
    _budget(path_budget, "path_budget")
    if path_budget == 0:
        raise ValueError("positive_integer_path_budget_required")
    _scope(ir, scope)
    start, end = span_bounds(scope["analysis_span"])
    cuts = sorted({f(sound["span"][bound]) for sound in scope["sound_facts"]
                   for bound in ("start", "end")
                   if start < f(sound["span"][bound]) < end})
    spans = {(start, end)} | {(start, cut) for cut in cuts} | {(cut, end) for cut in cuts}
    partitions = [("full_hold", None, [(start, end)])] + [
        ("two_segment", cut, [(start, cut), (cut, end)]) for cut in cuts]
    inventory, byspan = [], {}
    exceeded = len(spans) > max_catalogs
    source_scope_held = not scope["context_sound_inventory_complete"]
    supply_held = exceeded or source_scope_held
    for a, b in sorted(spans):
        entry = {"catalog_id": "fmehcat_" + digest([_ref(scope), _span(a, b)])[:24],
            "span": _span(a, b), "supplier_catalog": None, "candidate_count": None,
            "variant_count": None, "variants": [],
            "status": "source_scope_abstention" if source_scope_held else "whole_group_budget_abstention" if exceeded else "ready",
            "reasons": (["expanded_literal_source_sound_inventory_incomplete"] if source_scope_held else
                        ["complete_catalog_inventory_exceeds_budget_no_pruning"] if exceeded else [])}
        if not supply_held:
            supplier = catalog.propose(ir, entry["span"], scope["analysis_span"])
            catalog.validate(supplier)
            entry["supplier_catalog"] = supplier
            entry["candidate_count"] = len(supplier["candidates"])
            for index, candidate in enumerate(supplier["candidates"]):
                alternatives = range(len(candidate["spelling_alternatives"])) if candidate["spelling_alternatives"] else [None]
                entry["variants"].extend(_variant(scope, entry, candidate, index, alt) for alt in alternatives)
            entry["variant_count"] = len(entry["variants"])
        inventory.append(entry)
        byspan[a, b] = entry
    groups = []
    for kind, cut, partition in partitions:
        entries = [byspan[bounds] for bounds in partition]
        count = None if supply_held else 1
        if count is not None:
            for entry in entries:
                count *= entry["variant_count"]
        over_paths = count is not None and count > path_budget
        reasons = (["expanded_literal_source_sound_inventory_incomplete"] if source_scope_held else
                   ["complete_catalog_inventory_unavailable"] if exceeded else
                   ["complete_partition_path_group_exceeds_budget_no_pruning"] if over_paths else [])
        group = {"group_id": "fmehgroup_" + digest([_ref(scope), kind, cut and q(cut)])[:24],
            "kind": kind, "cut": None if cut is None else q(cut),
            "partition": [_span(a, b) for a, b in partition],
            "catalog_refs": [entry["catalog_id"] for entry in entries],
            "total_paths": count, "planned_paths": count,
            "status": "source_scope_abstention" if source_scope_held else "whole_group_budget_abstention" if reasons else "ready",
            "reasons": reasons, "paths": []}
        if not reasons:
            for segments in product(*(entry["variants"] for entry in entries)):
                group["paths"].append(_seal({"version": VERSION, "binding": deepcopy(scope["binding"]),
                    "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]),
                    "group_id": group["group_id"], "partition": deepcopy(group["partition"]),
                    "segments": list(segments),
                    "provenance": {"kind": "complete_inclusive_catalog_partition_hypothesis",
                        "source_statement_ref": None, "source_path": None}, "flags": _flags()}, PATH_PREFIX))
        groups.append(group)
    keys = _key_candidates(ir, scope)
    reasons = sorted({reason for group in groups for reason in group["reasons"]})
    return _seal({"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]),
        "cut_times": [q(cut) for cut in cuts], "catalog_inventory": inventory,
        "path_groups": groups, "keys": keys,
        "resource_limits": {"max_catalogs": max_catalogs, "path_budget": path_budget},
        "status": "source_scope_abstention" if source_scope_held else "with_whole_group_budget_holds" if reasons else "ready",
        "reasons": reasons, "flags": _flags(),
        "summary": {"observed_cuts": len(cuts), "catalog_spans": len(spans),
            "supplier_candidates": None if supply_held else sum(e["candidate_count"] for e in inventory),
            "spelling_variants": None if supply_held else sum(e["variant_count"] for e in inventory),
            "path_groups": len(groups), "path_group_statuses": dict(Counter(g["status"] for g in groups)),
            "complete_paths": sum(len(g["paths"]) for g in groups), "key_hypotheses": len(keys)},
        "limits": ["Full hold and every one-cut partition only; not exhaustive segmentation.",
            "Every supplier origin and spelling alternative survives; no PC-set deduplication.",
            "Signature-compatible reference forms and unknown are assumptions, not inferred local keys.",
            "SOURCE provenance is absent; the pure builder does not admit or reclassify old parent artifacts."]}, PREFIX)


def validate_hypotheses(ir, scope, record):
    _check(record, PREFIX)
    if record != build_hypotheses(ir, scope, **record["resource_limits"]):
        raise ValueError("stale_foreign_or_modified_expanded_hypotheses")
    return True


def _height(pitch):
    key = _pitch_key(pitch, True)
    return None if key is None else 12 * (key[2] + 1) + NATURAL[key[0]] + key[1]


def _state(sound, segment):
    key = _pitch_key(sound["pitch"])
    if key is None or segment["members"] is None:
        return "spelling_unresolved"
    return "member" if key in {_pitch_key(p) for p in segment["members"]} else "nonmember_not_confirmed_nct"


def _ordinary_tertian(segment):
    """Verify ordered conventional 3/4-tone spelling, not provider PC labels."""
    root, members = segment["root"], segment["members"]
    if root is None or members is None or len(members) not in (3, 4):
        return False
    if not all(_integer_pitch(p) for p in [root, *members]):
        return False
    origin = _pitch_key(root)
    if _pitch_key(members[0]) != origin:
        return False
    letter_indices = [(LETTERS.index(p["step"]) - LETTERS.index(root["step"])) % 7 for p in members]
    if letter_indices != ([0, 2, 4] if len(members) == 3 else [0, 2, 4, 6]):
        return False
    base = NATURAL[origin[0]] + origin[1]
    intervals = tuple((NATURAL[p["step"]] + f(p["alter"]) - base) % 12 for p in members[1:])
    allowed = ({(4, 7), (3, 7), (3, 6), (4, 8)} if len(members) == 3 else
               {(4, 7, 11), (3, 7, 10), (4, 7, 10), (3, 6, 9), (3, 6, 10), (4, 8, 11), (3, 7, 11)})
    return intervals in allowed


def _profile(scope, segment):
    sounds = [sound for sound in scope["sound_facts"] if not sound["point"]
              and _overlap(sound["span"], segment["span"]) is not None]
    rows, totals = [], {state: Fraction() for state in catalog.STATES}
    for sound in sounds:
        clip = _overlap(sound["span"], segment["span"])
        state = _state(sound, segment)
        duration = f(clip["end"]) - f(clip["start"])
        totals[state] += duration
        rows.append({"sound_ref": sound["sound_ref"], "full_span": deepcopy(sound["span"]),
            "observed_span": clip, "state": state, "pitch": deepcopy(sound["pitch"]),
            "source_clock_passed": sound["source_clock_passed"],
            "source_pitch_consistency_passed": sound["source_pitch_consistency_passed"],
            "source_diagnostics": deepcopy(sound["source_diagnostics"]),
            "eligible_as_analysis_source": sound["eligible_as_analysis_source"]})
    a, b = span_bounds(segment["span"])
    points = sorted({a, b} | {max(a, f(s["span"]["start"])) for s in sounds}
                    | {min(b, f(s["span"]["end"])) for s in sounds})
    cells = []
    for lo, hi in zip(points, points[1:]):
        active = [sound for sound in sounds if f(sound["span"]["start"]) < hi
                  and f(sound["span"]["end"]) > lo]
        heights = {s["sound_ref"]: _height(s["pitch"]) for s in active}
        known = [height for height in heights.values() if height is not None]
        basses = [s for s in active if known and heights[s["sound_ref"]] == min(known)]
        members = None if segment["members"] is None else [_pitch_key(p) for p in segment["members"]]
        indices = sorted({members.index(_pitch_key(s["pitch"])) for s in basses
                          if members is not None and _pitch_key(s["pitch"]) in members})
        bass_status = ("unknown" if not basses or any(v is None for v in heights.values()) or members is None
                       else "nonmember_bass_not_confirmed_nct" if any(_pitch_key(s["pitch"]) not in members for s in basses)
                       else "conditional_member_bass")
        conventional = _ordinary_tertian(segment)
        inversions = indices if conventional and bass_status == "conditional_member_bass" else []
        observed = {_pitch_key(s["pitch"]) for s in active}
        eligible_observed = {_pitch_key(s["pitch"]) for s in active if s["eligible_as_analysis_source"]}
        cells.append({"span": _span(lo, hi), "sound_refs": [s["sound_ref"] for s in active],
            "bass_refs": [s["sound_ref"] for s in basses],
            "bass_membership_status": bass_status, "conditional_inversions": inversions,
            "conditional_bass_member_indices": indices,
            "bass_source_guards_passed": (all(s["eligible_as_analysis_source"] for s in basses)
                                           if basses else None),
            "inversion_basis": ("conditional_complete_ordinary_tertian_template" if conventional
                                 else "rootless_extended_or_nontertian_inversion_unassessed"),
            "missing_spellings": None if members is None else [deepcopy(p) for p in segment["members"]
                                                                  if _pitch_key(p) not in observed],
            "source_guard_missing_spellings": None if members is None else [deepcopy(p) for p in segment["members"]
                                                                             if _pitch_key(p) not in eligible_observed],
            "silence": not active})
    return {"segment_ref": segment["segment_id"], "span": deepcopy(segment["span"]),
        "rows": rows, "cells": cells,
        "note_time_quarters": {state: q(value) for state, value in totals.items()},
        "total_note_time_quarters": q(sum(totals.values(), Fraction())),
        "missing_spellings": deepcopy(segment["missing_spellings"]),
        "missing_pitch_classes": deepcopy(segment["missing_pitch_classes"]),
        "supplier_event_states": deepcopy(segment["supplier_event_states"]),
        "blockers": deepcopy(segment["blockers"]),
        "semantics": "raw_spelled_membership_under_hypothesis_not_NCT_or_confirmed_harmony"}


def _bundle(scope, paths, keys, required=()):
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    by_lane = defaultdict(list)
    reasons = []
    for source, target in sorted(set(tuple(pair) for pair in required)):
        if source not in sounds or target not in sounds:
            reasons.append("required_link_has_foreign_sound")
            continue
        lane = sounds[source]["lane"]
        if lane is None or lane != sounds[target]["lane"]:
            reasons.append("required_link_crosses_or_has_unknown_raw_lane")
            continue
        by_lane[tuple(lane)].append([source, target])
    entries = []
    graph_lanes = set()
    for graph in sorted(scope["graphs"], key=lambda g: g["lane"]):
        lane = tuple(graph["lane"])
        graph_lanes.add(lane)
        query = geometry.query(graph, required_links=by_lane.get(lane, []))
        witness = geometry.materialize_witness(graph, query) if query["status"] == "exact_count" and query["possible_assignments"] != "0" else None
        entries.append({"lane": list(lane), "graph_ref": _ref(graph), "query": query,
                        "witness": witness, "status": "complete" if witness else "lane_withheld"})
        if witness is None:
            reasons.extend("lane_query:" + reason for reason in query["reasons"])
    if set(by_lane) - graph_lanes:
        reasons.append("required_raw_lane_not_in_graph_inventory")
    expected_lanes = {tuple([row["part_id"], row["voice_id"]]) for row in scope["raw_lanes"]}
    if graph_lanes != expected_lanes:
        reasons.append("complete_raw_lane_graph_inventory_missing")
    actual_links = sorted({tuple(pair) for entry in entries if entry["witness"] is not None
                           for pair in entry["witness"]["assignment"]["links"]})
    if not reasons and actual_links != sorted(set(tuple(pair) for pair in required)):
        raise ValueError("materialized_sparse_witness_links_do_not_match_joint_request")
    return _seal({"version": VERSION, "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]),
        "comparison_path_refs": [_ref(path) for path in paths],
        "comparison_key_refs": [_ref(key) for key in keys],
        "required_links": [list(pair) for pair in sorted(set(tuple(p) for p in required))],
        "materialized_witness_links": [list(pair) for pair in actual_links],
        "entries": entries, "covered_lanes": sorted([list(lane) for lane in graph_lanes]),
        "status": "complete_all_lane_witness" if not reasons else "all_lane_witness_withheld",
        "reasons": sorted(set(reasons)), "flags": _flags(),
        "semantics": "one_query_completion_per_raw_lane_joint_required_edges_not_independent_lane_votes",
        "all_unrequired_edges_left_unconnected": True,
        "all_no_link_control": not required, "possible_assignments_is_confidence": False}, BUNDLE_PREFIX)


def _target(root, family):
    step, alter = _old(root)
    steps, semitones = ROOT_INTERVALS[family]
    index = LETTERS.index(step)
    target_index = index - steps
    letter = LETTERS[target_index % 7]
    return [letter, NATURAL[step] + alter - semitones - NATURAL[letter] - 12 * (target_index // 7)]


def _function(scope, source, target, key, family, quality):
    blockers = list(source["blockers"])
    expected, target_members, target_root, leading, seventh = [], [], None, None, None
    shape, compatible, profile = None, None, None
    if source["root"] is None:
        blockers.append("source_root_not_spelled")
    elif source["members"] is None or not all(_integer_pitch(p) for p in [source["root"], *source["members"]]):
        blockers.append("ordinary_source_spelling_unknown_or_microtonal")
    else:
        value = hypothesis(_target(source["root"], family), quality, family)
        target_root = _pitch(value["target"]["root"])
        target_members = [_pitch(p) for p in value["target"]["members"]]
        expected = [_pitch(p) for p in value["chord"]["members"]]
        leading = _pitch(value["leading_tone"])
        seventh = _pitch(value["chord"]["members"][3]) if len(value["chord"]["members"]) == 4 else None
        profile = value["textbook_profile"]
        shape = {_pitch_key(p) for p in source["members"]} == {_pitch_key(p) for p in expected}
        if not shape:
            blockers.append("source_ordinary_family_shape_mismatch")
    if target is None:
        blockers.append("following_target_segment_not_observed")
    elif target["root"] is None or target["members"] is None:
        blockers.append("following_target_spelling_unresolved")
    else:
        blockers.extend("target:" + reason for reason in target["blockers"])
        if target_root is not None:
            compatible = (_pitch_key(target["root"]) == _pitch_key(target_root)
                          and {_pitch_key(p) for p in target_members} <= {_pitch_key(p) for p in target["members"]})
            if not compatible:
                blockers.append("following_target_triad_core_mismatch")
    coordinate, chromatic, kind, key_reasons = None, None, "unassessed", []
    if key["mode"] == "unknown" or key["tonic"] is None:
        key_reasons.append("explicit_key_unknown")
    elif target_root is not None:
        tonic = _old(key["tonic"])
        coordinate = scale_degree(*_old(target_root), *tonic, form=key["scale_form"])
        chromatic = [deepcopy(p) for p in expected
                     if not scale_degree(*_old(p), *tonic, form=key["scale_form"])["diatonic_to_candidate"]]
        same = _pitch_key(target_root) == _pitch_key(key["tonic"])
        kind = ("primary" if quality == ("M" if key["mode"] == "major" else "m") else "parallel") if same else "applied"
    else:
        key_reasons.append("ordinary_target_spelling_unknown")
    return {"source_segment_ref": source["segment_id"],
        "target_segment_ref": None if target is None else target["segment_id"],
        "source_span": deepcopy(source["span"]), "target_span": None if target is None else deepcopy(target["span"]),
        "family": family, "target_quality": quality, "expected_source_members": expected,
        "derived_target_root": target_root, "derived_target_members": target_members,
        "actual_target_root": None if target is None else deepcopy(target["root"]),
        "actual_target_members": None if target is None else deepcopy(target["members"]),
        "leading_tone": leading, "seventh": seventh, "shape_compatible": shape,
        "target_shape_compatible": compatible, "function_kind": kind,
        "key_segment_ref": key["segment_id"], "key_projection": {
            "target_coordinate": coordinate, "chromatic_source_members": chromatic,
            "unassessed_reasons": key_reasons, "chromatic_is_not_applied_function_proof": True,
            "scale_form_is_not_motion_direction_rule": True},
        "textbook_profile": profile, "profile_is_universal_prohibition": False,
        "status": "conditional_function_shape" if not blockers else "withheld",
        "blockers": sorted(set(blockers)), "function_confirmed": None,
        "tonicization": None, "modulation": None, "cadence": None}


def _source_blockers(sound):
    blockers = []
    if sound["eligible_as_analysis_source"] is not True:
        blockers.append("involved_source_not_eligible:" + sound["sound_ref"])
    if sound["source_clock_passed"] is not True:
        blockers.append("source_clock_not_passed:" + sound["sound_ref"])
    if sound["source_pitch_consistency_passed"] is not True:
        blockers.append("source_written_pitch_not_passed:" + sound["sound_ref"])
    if sound.get("source_attack_consistency_passed") is not True:
        blockers.append("source_attack_lineage_not_passed:" + sound["sound_ref"])
    if sound["point"] or sound["grace"]:
        blockers.append("point_or_grace_endpoint_not_supported:" + sound["sound_ref"])
    if not _integer_pitch(sound["pitch"]) or _pitch_key(sound["pitch"], True) is None:
        blockers.append("ordinary_motion_pitch_not_supported:" + sound["sound_ref"])
    return blockers


def _move(source, target):
    left, right = _pitch_key(source["pitch"], True), _pitch_key(target["pitch"], True)
    if left is None or right is None:
        return None
    return {"diatonic_steps": 7 * (right[2] - left[2]) + LETTERS.index(right[0]) - LETTERS.index(left[0]),
        "semitones": q(12 * (right[2] - left[2]) + NATURAL[right[0]] - NATURAL[left[0]] + right[1] - left[1])}


def _motion_options(scope, row, source, target, profiles, max_motion_pairs):
    blockers = list(row["blockers"])
    roles = {"leading_tone": row["leading_tone"]}
    if row["seventh"] is not None:
        roles["seventh"] = row["seventh"]
    options = {role: [] for role in roles}
    boundary = None if target is None else f(target["span"]["start"])
    if row["shape_compatible"] is not True or row["target_shape_compatible"] is not True or boundary is None:
        blockers.append("actual_source_and_target_shape_prerequisites_withheld")
        return options, sorted(set(blockers)), 0, False
    source_cells, target_cells = profiles[0]["cells"], profiles[1]["cells"]
    for name, cell in (("source", source_cells[-1]), ("target", target_cells[0])):
        if cell["bass_membership_status"] != "conditional_member_bass":
            blockers.append(name + "_actual_member_bass_unknown_or_nonmember")
        if cell["bass_source_guards_passed"] is not True:
            blockers.append(name + "_actual_bass_source_guards_not_passed")
        if cell["missing_spellings"]:
            blockers.append(name + "_core_not_fully_sounded_at_boundary")
        if cell["source_guard_missing_spellings"]:
            blockers.append(name + "_core_source_guards_not_fully_established_at_boundary")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    planned_pairs = 0
    for graph in scope["graphs"]:
        for factor in graph["factors"]:
            if f(factor["time"]) != boundary:
                continue
            for src in factor["source_refs"]:
                left = sounds[src]
                if _overlap(left["span"], source["span"]) is None or _state(left, source) != "member":
                    continue
                planned_pairs += sum(len(factor["target_refs"]) for critical in roles.values()
                                     if critical is not None and _pitch_key(left["pitch"]) == _pitch_key(critical))
    if planned_pairs > max_motion_pairs:
        return options, sorted(set(blockers + ["complete_endpoint_motion_pair_group_exceeds_budget_no_pruning"])), planned_pairs, True
    for graph in scope["graphs"]:
        for factor in graph["factors"]:
            if f(factor["time"]) != boundary:
                continue
            for src in factor["source_refs"]:
                left = sounds[src]
                if _overlap(left["span"], source["span"]) is None or _state(left, source) != "member":
                    continue
                for role, critical in roles.items():
                    if critical is None or _pitch_key(left["pitch"]) != _pitch_key(critical):
                        continue
                    for dst in factor["target_refs"]:
                        right = sounds[dst]
                        motion = _move(left, right)
                        edge_blockers = _source_blockers(left) + _source_blockers(right)
                        if _overlap(right["span"], target["span"]) is None or _state(right, target) != "member":
                            edge_blockers.append("endpoint_not_spelled_member_of_actual_target")
                        direct = False
                        if motion is not None and not edge_blockers:
                            if role == "leading_tone":
                                direct = (motion["diatonic_steps"] == 1 and f(motion["semitones"]) == 1
                                          and _pitch_key(right["pitch"]) == _pitch_key(row["derived_target_root"]))
                            else:
                                direct = motion["diatonic_steps"] == -1 and f(motion["semitones"]) in (-1, -2)
                        if not direct:
                            edge_blockers.append(role + "_direct_spelled_motion_not_met")
                        options[role].append({"source_ref": src, "target_ref": dst, "lane": deepcopy(graph["lane"]),
                            "required_link": [src, dst], "motion": motion, "qualified": direct,
                            "blockers": sorted(set(edge_blockers)), "source_member": True,
                            "target_member": _state(right, target) == "member"})
    for role, edges in options.items():
        if not edges:
            blockers.append(role + "_touching_source_member_endpoint_not_observed")
        elif not any(edge["qualified"] for edge in edges):
            blockers.append(role + "_qualifying_direct_motion_not_observed")
    return options, sorted(set(blockers)), planned_pairs, False


def evaluate_hypotheses(ir, scope, hypotheses, *, pair_budget=4096,
                        overlay_pair_budget=65536, max_motion_pairs=65536):
    """Compare all competitors in one fresh, explicitly shared witness universe.

    The no-link bundle is a control.  A resolution-shape row needs its entire
    critical-edge set in one complete all-lane bundle; unrelated favorable
    leading-tone and seventh edges cannot be combined after evaluation.
    """
    for name, value in (("pair_budget", pair_budget), ("overlay_pair_budget", overlay_pair_budget),
                        ("max_motion_pairs", max_motion_pairs)):
        _budget(value, name)
    validate_hypotheses(ir, scope, hypotheses)
    paths = [path for group in hypotheses["path_groups"] for path in group["paths"]]
    keys = hypotheses["keys"]
    baseline = _bundle(scope, paths, keys)
    bundles = {baseline["record_id"]: baseline}
    by_required = {(): baseline}
    profiles = {segment["segment_id"]: _profile(scope, segment)
                for group in hypotheses["path_groups"] for path in group["paths"] for segment in path["segments"]}
    groups = []
    for candidate_group in hypotheses["path_groups"]:
        count = None if candidate_group["total_paths"] is None else candidate_group["total_paths"] * len(keys)
        overlay_count = None if count is None else count * len(candidate_group["partition"]) * 2 * len(FAMILIES)
        reasons = list(candidate_group["reasons"])
        if count is not None and count > pair_budget:
            reasons.append("complete_path_key_pair_group_exceeds_budget_no_pruning")
        if overlay_count is not None and overlay_count > overlay_pair_budget:
            reasons.append("complete_function_overlay_group_exceeds_budget_no_pruning")
        group = {"group_id": candidate_group["group_id"], "kind": candidate_group["kind"],
            "cut": deepcopy(candidate_group["cut"]), "partition": deepcopy(candidate_group["partition"]),
            "total_path_key_pairs": count, "total_function_shapes": overlay_count,
            "status": "whole_group_budget_abstention" if reasons else "ready",
            "reasons": sorted(set(reasons)), "shared_bundle_ref": _ref(baseline), "rows": []}
        if not reasons:
            for path in candidate_group["paths"]:
                path_profiles = [profiles[segment["segment_id"]] for segment in path["segments"]]
                for key in keys:
                    functions = []
                    for index, source in enumerate(path["segments"]):
                        target = path["segments"][index + 1] if index + 1 < len(path["segments"]) else None
                        for family in FAMILIES:
                            for quality in ("M", "m"):
                                function = _function(scope, source, target, key["segments"][0], family, quality)
                                function["function_id"] = "fmehfunc_" + digest([_ref(scope), _ref(path), _ref(key), function])[:24]
                                options, blockers, endpoint_count, endpoint_hold = _motion_options(
                                    scope, function, source, target, path_profiles[index:index + 2], max_motion_pairs)
                                qualified = [[edge for edge in edges if edge["qualified"]] for edges in options.values()]
                                motion_count = None if endpoint_hold else 1
                                if motion_count is not None:
                                    for edges in qualified:
                                        motion_count *= len(edges)
                                motion = {"edge_options": options, "total_joint_options": motion_count,
                                    "planned_endpoint_pairs": endpoint_count,
                                    "joint_options": [], "qualifying_bundle_refs": [],
                                    "blockers": blockers, "baseline_bundle_ref": _ref(baseline),
                                    "status": "withheld", "same_pitch_delayed_resolution": "unassessed",
                                    "cadence_NCT_and_actual_harmony_identity": "unassessed"}
                                if endpoint_hold:
                                    motion["status"] = "whole_group_budget_abstention"
                                elif motion_count > max_motion_pairs:
                                    motion.update(status="whole_group_budget_abstention",
                                                  blockers=sorted(set(blockers + ["complete_joint_motion_group_exceeds_budget_no_pruning"])))
                                elif not blockers:
                                    for edges in product(*qualified):
                                        required = tuple(sorted(set(tuple(edge["required_link"]) for edge in edges)))
                                        bundle = by_required.get(required)
                                        if bundle is None:
                                            bundle = _bundle(scope, paths, keys, required)
                                            by_required[required] = bundle
                                            bundles[bundle["record_id"]] = bundle
                                        complete = bundle["status"] == "complete_all_lane_witness"
                                        motion["joint_options"].append({"required_links": [list(pair) for pair in required],
                                            "bundle_ref": _ref(bundle), "status": "conditional_joint_motion_shape" if complete else "withheld",
                                            "blockers": deepcopy(bundle["reasons"]),
                                            "critical_roles": list(options), "all_critical_roles_in_same_bundle": complete})
                                        if complete:
                                            motion["qualifying_bundle_refs"].append(_ref(bundle))
                                    if motion["qualifying_bundle_refs"]:
                                        motion["status"] = "conditional_joint_motion_shape"
                                function["motion"] = motion
                                functions.append(function)
                    group["rows"].append({"path_ref": _ref(path), "key_ref": _ref(key),
                        "shared_bundle_ref": _ref(baseline), "profiles": deepcopy(path_profiles),
                        "functions": functions, "selected": None, "rank": None,
                        "status": "conditional_comparison", "cadence": None, "NCT": None})
        groups.append(group)
    # Every shared bundle is registered against precisely the same full path
    # and key universe. This compact incidence map makes every candidate's
    # SAME-bundle assessment explicit without duplicating large literal rows.
    for group in groups:
        group["planned_same_bundle_assessments"] = (None if group["total_path_key_pairs"] is None
                                                    else len(bundles) * group["total_path_key_pairs"])
        if group["rows"] and group["planned_same_bundle_assessments"] > pair_budget:
            group["rows"] = []
            group["status"] = "whole_group_budget_abstention"
            group["reasons"] = sorted(set(group["reasons"] + [
                "complete_all_bundle_comparison_group_exceeds_budget_no_pruning"]))
    assessments = []
    for bundle in bundles.values():
        chosen = {tuple(pair) for entry in bundle["entries"] if entry["witness"] is not None
                  for pair in entry["witness"]["assignment"]["links"]}
        rows = []
        for group in groups:
            for comparison in group["rows"]:
                compatible = []
                for function in comparison["functions"]:
                    for option in function["motion"]["joint_options"]:
                        if (bundle["status"] == "complete_all_lane_witness"
                                and option["status"] == "conditional_joint_motion_shape"
                                and {tuple(pair) for pair in option["required_links"]} <= chosen):
                            compatible.append(function["function_id"])
                            break
                rows.append({"path_ref": comparison["path_ref"], "key_ref": comparison["key_ref"],
                             "joint_motion_shape_refs": compatible, "selected": None})
        assessments.append({"bundle_ref": _ref(bundle), "rows": rows,
            "same_complete_bundle_for_all_competitors": True,
            "link_basis": "actual_materialized_completion_links_in_all_declared_lanes",
            "optional_unrequired_links_present": False,
            "budget_held_comparison_groups": [g["group_id"] for g in groups if not g["rows"]]})
    return _seal({"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "hypotheses_ref": _ref(hypotheses),
        "analysis_span": deepcopy(scope["analysis_span"]), "groups": groups,
        "baseline_bundle_ref": _ref(baseline), "bundle_inventory": list(bundles.values()),
        "same_bundle_assessments": assessments,
        "resource_limits": {"pair_budget": pair_budget, "overlay_pair_budget": overlay_pair_budget,
                            "max_motion_pairs": max_motion_pairs},
        "status": "with_whole_group_budget_holds" if any(g["reasons"] for g in groups) else "ready",
        "reasons": sorted({r for g in groups for r in g["reasons"]}), "flags": _flags(),
        "summary": {"groups": len(groups), "group_statuses": dict(Counter(g["status"] for g in groups)),
            "comparison_rows": sum(len(g["rows"]) for g in groups),
            "function_shapes": sum(len(row["functions"]) for g in groups for row in g["rows"]),
            "complete_joint_motion_shapes": sum(function["motion"]["status"] == "conditional_joint_motion_shape"
                for g in groups for row in g["rows"] for function in row["functions"]),
            "bundles": len(bundles), "all_lane_bundles": sum(b["status"] == "complete_all_lane_witness" for b in bundles.values())},
        "limits": ["Membership duration is raw accounting, not an objective or ranking.",
            "Conditional inversion is per literal cell; a span union is not a simultaneity.",
            "Only direct release=attack critical motions are assessed; repeated/delayed chains remain open.",
            "A complete joint witness never establishes contrapuntal voice identity or observed harmony.",
            "PAC, HC, NCT, tonicization and modulation are unassessed; no gold, training or production promotion."]}, EVALUATION_PREFIX)


def validate_evaluation(ir, scope, hypotheses, record):
    _check(record, EVALUATION_PREFIX)
    if record != evaluate_hypotheses(ir, scope, hypotheses, **record["resource_limits"]):
        raise ValueError("stale_foreign_or_modified_expanded_evaluation")
    return True
