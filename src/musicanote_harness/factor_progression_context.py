"""Native contextual premises for unchanged complete progression hypotheses.

The owned phase-20 comparison is the authority: this layer neither adapts an
expanded scope into a legacy fmview nor creates a key, segment or completion.
Literal extremes, candidate coordinates and one completion's ordinary motion
remain separate premises.  No chord, secondary function or cadence is selected.
"""
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import hmac
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_progression_evidence as progression
from . import factor_indexed_hypotheses as indexed
from . import factor_expanded_hypotheses as frozen
from . import factor_temporal_explanations as temporal
from . import factor_cadence_prerequisites as cadence
from . import tonal_foundations as tonal
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-progression-context-0.1.0"
PREFIX = "fmpctx_"
PATH_PREFIX = "fmpctxpath_"
BOUNDARY_PREFIX = "fmpctxboundary_"
FUNCTION_PREFIX = "fmpctxfunction_"
CAPS = ("max_hypotheses", "max_boundary_observations", "max_transition_pairs", "query_work_budget")
DEFAULTS = dict(zip(CAPS, (64, 2048, 4096, 200000)))
MISSING_PREMISES = tuple(cadence.MISSING_PREMISES)
LETTERS = "CDEFGAB"
BASE = dict(zip(LETTERS, (0, 2, 4, 5, 7, 9, 11)))
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    return {**progression._flags(), **{name: False for name in (
        "secondary_function_confirmed", "tonicization_confirmed", "modulation_confirmed",
        "structural_bass_confirmed", "structural_melody_confirmed", "inversion_confirmed",
        "perceived_accent_certified", "meter_source_certified", "consonance_certified",
        "phrase_terminal_certified", "performed_timing_certified", "raw_note_time_modified",
        "new_key_path_or_completion_created", "legacy_view_or_path_fabricated",
        "context_endpoint_is_silence_or_cadence_proof", "independent_completions_unioned")}}


def _contract():
    return {"version": VERSION, "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "progression_contract": progression._contract(),
        "premise_sources": [{"module": module.__name__,
            "sha256": sha256(Path(module.__file__).read_bytes()).hexdigest()}
            for module in (cadence, tonal)]}


def _seal(body, prefix):
    return frozen._seal(body, prefix)


def _ref(record):
    return frozen._ref(record)


def _caps(values):
    for name in CAPS:
        indexed._integer(values[name], name)


class _PreparedContext:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    data: object
    upstream_session: object
    upstream_state: object
    upstream_source_state: object
    contract_sha256: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, indexed._encoded([id(handle), id(state), id(state.data),
        id(state.upstream_session), id(state.upstream_state), id(state.upstream_source_state),
        state.contract_sha256]), "sha256")


def _issued(handle):
    if type(handle) is not _PreparedContext or handle not in _SESSIONS:
        raise ValueError("internally_issued_progression_context_session_required")
    state = _SESSIONS[handle]
    if (type(state) is not _State or not isinstance(state.data, MappingProxyType)
            or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _auth(handle, state))):
        raise ValueError("context_session_current_contract_or_owned_state_changed")
    authority, source = progression._issued(state.upstream_session)
    if authority is not state.upstream_state or source is not state.upstream_source_state:
        raise ValueError("context_owned_upstream_authority_changed")
    return state, source


def prepare_context_prepared(comparison_session, record):
    """Replay an exact phase-20 result once under authentic owned authority.

    The new handle owns the fresh immutable comparison and lightweight parent
    identities, not a second copy of the large transitive source payload.
    Caller seals, skip flags and structurally similar handles grant no waiver.
    """
    authority, source = progression._issued(comparison_session)
    contract, before = _contract(), digest(record)
    if type(record) is not dict:
        raise ValueError("typed_progression_context_parent_record_required")
    frozen._check(record, progression.PREFIX)
    if record.get("version") != progression.VERSION:
        raise ValueError("current_progression_context_parent_required")
    limits = record.get("resource_limits")
    progression._closed(limits, progression.CAPS, "context_parent_resource_limits")
    progression._caps(limits)
    fresh = progression.compare_prepared(comparison_session, record.get("selectors"),
        record.get("bundle_id"), **limits)
    if not indexed._same(fresh, record):
        raise ValueError("stale_foreign_modified_or_promoting_context_parent_comparison")
    current, current_source = progression._issued(comparison_session)
    if (current is not authority or current_source is not source or before != digest(record)
            or not indexed._same(contract, _contract())):
        raise ValueError("context_parent_inputs_authority_or_code_changed_during_preparation")
    handle = _PreparedContext()
    state = _State(indexed._freeze({"comparison": fresh}), comparison_session, authority,
        source, digest(contract), b"")
    object.__setattr__(state, "authentication", _auth(handle, state))
    _SESSIONS[handle] = state
    _issued(handle)
    return handle


def prepare_context(ir, scope, hypotheses, index, relations, grounding,
                    temporal_record, boundary_record, obligations_record, comparison_record):
    """Fresh public preparation replays all nine original source parents."""
    caller = [ir, scope, hypotheses, index, relations, grounding, temporal_record,
        boundary_record, obligations_record, comparison_record]
    before, contract = digest(caller), _contract()
    session = progression.prepare_comparison(*caller[:9])
    result = prepare_context_prepared(session, comparison_record)
    if before != digest(caller) or not indexed._same(contract, _contract()):
        raise ValueError("context_raw_parent_inputs_or_code_changed")
    return result


def _span(a, b):
    return {"start": q(a), "end": q(b)}


def _height(pitch):
    return 12 * (pitch["octave"] + 1) + BASE[pitch["step"]] + f(pitch["alter"])


def _guards(sound):
    return {"source_clock_passed": sound["source_clock_passed"],
        "source_pitch_consistency_passed": sound["source_pitch_consistency_passed"],
        "source_attack_consistency_passed": sound.get("source_attack_consistency_passed"),
        "eligible_as_analysis_source": sound["eligible_as_analysis_source"],
        "source_diagnostics": deepcopy(sound["source_diagnostics"]),
        "blockers": sorted(set(temporal._guard_codes(sound) + frozen._source_blockers(sound)))}


def _slots(scope):
    return scope["literal_observation"]["slots"]


def _facts(scope):
    return {s["sound_ref"]: s for s in scope["sound_facts"]}


def _positive(scope):
    return [s for s in scope["sound_facts"] if not s["point"]]


def _extremes(rows):
    if not rows:
        return {"lowest_sound_refs": [], "highest_sound_refs": [],
            "lowest_written_height": None, "highest_written_height": None,
            "lowest_spelling_ambiguous": False, "highest_spelling_ambiguous": False,
            "structural_bass": "unassessed", "structural_melody": "unassessed",
            "concert_pitch_certified": False}
    low, high = min(_height(s["pitch"]) for s in rows), max(_height(s["pitch"]) for s in rows)
    lowest = [s for s in rows if _height(s["pitch"]) == low]
    highest = [s for s in rows if _height(s["pitch"]) == high]
    return {"lowest_sound_refs": sorted(s["sound_ref"] for s in lowest),
        "highest_sound_refs": sorted(s["sound_ref"] for s in highest),
        "lowest_written_height": q(low), "highest_written_height": q(high),
        "lowest_spelling_ambiguous": len({frozen._pitch_key(s["pitch"]) for s in lowest}) > 1,
        "highest_spelling_ambiguous": len({frozen._pitch_key(s["pitch"]) for s in highest}) > 1,
        "structural_bass": "unassessed", "structural_melody": "unassessed",
        "concert_pitch_certified": False}


def _boundary_indices(scope, when):
    c, d = span_bounds(scope["analysis_span"])
    if not c <= when <= d:
        raise ValueError("native_context_boundary_outside_exact_analysis_span")
    positive = _positive(scope)
    before = [s for s in positive if f(s["observed_span"]["start"]) < when <= f(s["observed_span"]["end"])]
    at = [s for s in positive if f(s["observed_span"]["start"]) <= when < f(s["observed_span"]["end"])] if when < d else []
    return before, at, _extremes(before), _extremes(at)


def _metric(scope, when):
    rows = []
    for measure in scope["literal_observation"]["core_projection"]["measures"]:
        a = f(measure["global_start_quarter"])
        b = a + f(measure["actual_duration_quarter"])
        if a <= when < b:
            signature = measure["time_signature"]
            unit = Fraction(4, signature["beat_type"])
            offset = when - a
            rows.append({"measure_id": measure["measure_id"],
                "printed_measure_number": measure["printed_measure_number"],
                "sequential_measure_index": measure["sequential_measure_index"],
                "measure_span": _span(a, b), "time_signature": deepcopy(signature),
                "offset_quarter": q(offset), "notated_beat_unit_quarter": q(unit),
                "notated_beat_coordinate": q(offset / unit + 1),
                "at_notated_measure_start": offset == 0, "pickup": measure["pickup"],
                "perceived_accent": "unassessed"})
    rows.sort(key=lambda r: (f(r["measure_span"]["start"]), f(r["measure_span"]["end"]), r["measure_id"]))
    return {"status": "exact_IR_notated_coordinates" if rows else "notated_coordinate_unavailable",
        "coordinates": rows, "ambiguous_measure_inventory": len(rows) > 1,
        "meter_source_certified": False, "perceived_accent_certified": False,
        "basis": "bound_IR_notated_denominator_unit_not_certified_XML_meter_or_conducting_beat"}


def _boundary(scope, when):
    """Pure native source observation, never a fabricated legacy view."""
    if isinstance(when, dict):
        when = f(when)
    elif type(when) is int or isinstance(when, Fraction):
        when = Fraction(when)
    else:
        raise ValueError("exact_native_boundary_time_required")
    before, at, lower, upper = _boundary_indices(scope, when)
    c, d = span_bounds(scope["analysis_span"])
    positive = _positive(scope)
    points = [s for s in scope["sound_facts"] if s["point"] and f(s["span"]["start"]) == when]
    notes = {r["event_id"]: r["core_event"] for r in _slots(scope) if r["event_kind"] == "note"}
    attacks = sorted(s["attack_note_ref"] for s in [*positive, *points]
        if s["attack_note_ref"] in notes and f(notes[s["attack_note_ref"]]["global_onset_quarter"]) == when)
    following_rests = []
    for slot in _slots(scope):
        if slot["event_kind"] != "rest":
            continue
        rest = slot["core_event"]
        a, b = f(rest["global_onset_quarter"]), f(rest["global_onset_quarter"]) + f(rest["notated_duration_quarter"])
        if max(a, when, c) < min(b, d):
            following_rests.append({"rest_ref": rest["rest_id"], "source_ref_id": rest["source_ref_id"],
                "lane": [rest["part_id"], rest["voice_id"]], "full_span": _span(a, b),
                "observed_following_span": _span(max(a, when, c), min(b, d)),
                "hidden": rest["hidden"], "overlap_is_silence_confirmation": False})
    guarded = {s["sound_ref"]: s for s in [*before, *at, *points]}
    return _seal({"version": VERSION, "scope_ref": _ref(scope), "binding": deepcopy(scope["binding"]),
        "analysis_span": deepcopy(scope["analysis_span"]), "boundary_time": q(when),
        "observation_status": "inside_observed_analysis_span" if when < d else "analysis_endpoint_not_following_observation",
        "positive_sound_refs_before": sorted(s["sound_ref"] for s in before),
        "positive_sound_refs_at": sorted(s["sound_ref"] for s in at),
        "full_sound_start_refs": sorted(s["sound_ref"] for s in positive if f(s["span"]["start"]) == when),
        "full_sound_end_refs": sorted(s["sound_ref"] for s in positive if f(s["span"]["end"]) == when),
        "full_sound_continuing_refs": sorted(s["sound_ref"] for s in positive if f(s["span"]["start"]) < when < f(s["span"]["end"])),
        "point_sound_refs_at": sorted(s["sound_ref"] for s in points), "attack_note_refs_at": attacks,
        "source_guards": [{"sound_ref": sid, **_guards(s)} for sid, s in sorted(guarded.items())],
        "lowest_highest_before": lower, "lowest_highest_at": upper, "notated_metric": _metric(scope, when),
        "following": {"observed_positive_sound_refs": sorted(s["sound_ref"] for s in positive if f(s["observed_span"]["end"]) > when),
            "observed_later_attack_note_refs": sorted(s["attack_note_ref"] for s in scope["sound_facts"]
                if s["attack_note_ref"] in notes and when < f(notes[s["attack_note_ref"]]["global_onset_quarter"]) < d),
            "observed_following_rest_spans": sorted(following_rests, key=lambda r: (f(r["full_span"]["start"]), r["rest_ref"])),
            "known_full_sound_refs_extending_beyond_analysis": sorted(s["sound_ref"] for s in positive if f(s["span"]["end"]) > d),
            "analysis_ends_here": when == d, "phrase_closure": "unassessed",
            "empty_following_inventory_is_silence_or_cadence_proof": False}, "flags": _flags()}, BOUNDARY_PREFIX)


def _ordinary_shape(variant):
    if variant is None:
        return {"status": "unassessed", "quality": None, "blockers": ["assumed_variant_unavailable"],
            "shape_is_harmony_confirmation": False}
    root, members = variant["root"], variant["members"]
    reasons = list(variant["blockers"])
    if variant["status"] != "conditional_spelled_candidate":
        reasons.append("assumed_variant_spelling_unavailable")
    if root is None or members is None:
        reasons.append("assumed_root_or_members_unavailable")
    pitches = ([] if root is None else [root]) + ([] if members is None else members)
    integral = all(f(p["alter"]).denominator == 1 for p in pitches)
    if not integral:
        reasons.append("ordinary_microtonal_shape_unassessed")
    shapes = []
    if root is not None and members is not None and integral:
        values = [(p["step"], f(p["alter"]).numerator, 4) for p in members]
        candidates = (tonal.spelled_triad_shapes(values) if len(members) == 3 else
            tonal.spelled_seventh_shapes(values) if len(members) == 4 else [])
        shapes = [s for s in candidates if (s["root_step"], s["root_alter"]) == (root["step"], f(root["alter"]).numerator)]
        if len(shapes) != 1:
            reasons.append("complete_ordinary_triad_or_seventh_shape_unestablished")
    return {"status": "conditional_complete_ordinary_shape" if not reasons else "withheld",
        "quality": shapes[0]["quality"] if len(shapes) == 1 else None,
        "blockers": sorted(set(reasons)), "shape_is_harmony_confirmation": False}


def _factor(sound, variant, shape, *, is_lowest, lowest_spelling_ambiguous):
    root, members = (None, None) if variant is None else (variant["root"], variant["members"])
    member = None if members is None else frozen._pitch_key(sound["pitch"]) in {frozen._pitch_key(p) for p in members}
    degree = None if root is None else (LETTERS.index(sound["pitch"]["step"]) - LETTERS.index(root["step"])) % 7 + 1
    reasons = [*shape["blockers"], *_guards(sound)["blockers"]]
    if member is False:
        reasons.append("observed_extreme_outside_assumed_members_not_NCT_confirmation")
    if is_lowest and lowest_spelling_ambiguous:
        reasons.append("equal_lowest_enharmonic_spellings_unresolved")
    inversion = {1: 0, 3: 1, 5: 2, 7: 3}.get(degree) if is_lowest and member is True and not reasons else None
    return {"assumed_variant_ref": None if variant is None else _ref(variant), "assumed_root": deepcopy(root),
        "assumed_members": deepcopy(members), "spelled_member_of_assumption": member,
        "diatonic_factor_from_assumed_root": degree, "ordinary_shape": deepcopy(shape),
        "is_observed_lowest": is_lowest, "conditional_inversion_shape": inversion,
        "inversion_status": "not_a_lowest_sound_observation" if not is_lowest else
            "conditional_on_assumed_chord_and_observed_lowest_not_structural_bass" if inversion is not None else "unassessed_prerequisites",
        "blockers": sorted(set(reasons)), "inversion_confirmed": False, "structural_bass_confirmed": False}


def _degree(pitch, key):
    segment = key["segments"][0] if key is not None and "segments" in key else key
    reasons = []
    if segment is None or segment["tonic"] is None or segment["mode"] == "unknown":
        reasons.append("explicit_registered_key_unknown")
    if segment is not None and segment["scale_form"] not in tonal.SCALES:
        reasons.append("explicit_scale_form_unassessed")
    if f(pitch["alter"]).denominator != 1 or (segment is not None and segment["tonic"] is not None
            and f(segment["tonic"]["alter"]).denominator != 1):
        reasons.append("ordinary_microtonal_scale_coordinate_unassessed")
    coordinate = None
    if not reasons:
        coordinate = tonal.scale_degree(pitch["step"], f(pitch["alter"]).numerator,
            segment["tonic"]["step"], f(segment["tonic"]["alter"]).numerator, form=segment["scale_form"])
    return {"key_segment_ref": None if segment is None else segment.get("segment_id"),
        "coordinate": coordinate, "status": "conditional_scale_coordinate" if coordinate is not None else "unassessed",
        "blockers": reasons, "key_confirmed": False,
        "scale_form_is_not_melodic_direction_rule": True}


def _terminal(scope, sound, when, metric):
    c, d = span_bounds(scope["analysis_span"])
    a, release = span_bounds(sound["span"])
    ratios = [{"measure_id": row["measure_id"], "notated_beat_unit_quarter": deepcopy(row["notated_beat_unit_quarter"]),
        "full_sound_duration_in_notated_units": q((release - a) / f(row["notated_beat_unit_quarter"])),
        "remaining_duration_from_boundary_in_notated_units": q((release - when) / f(row["notated_beat_unit_quarter"])),
        "basis": "IR_notated_denominator_unit_not_certified_meter_or_conducting_beat"} for row in metric["coordinates"]]
    notes = {r["event_id"]: r["core_event"] for r in _slots(scope) if r["event_kind"] == "note"}
    attacks = []
    for s in scope["sound_facts"]:
        note = notes.get(s["attack_note_ref"])
        if note is not None and s["lane"] == sound["lane"]:
            onset = f(note["global_onset_quarter"])
            if release <= onset < d and c <= onset:
                attacks.append({"sound_ref": s["sound_ref"], "attack_note_ref": s["attack_note_ref"],
                    "onset": q(onset), "point": s["point"], "grace": s["grace"], "source_guards": _guards(s)})
    rests = []
    for slot in _slots(scope):
        if slot["event_kind"] != "rest":
            continue
        rest = slot["core_event"]
        lo = f(rest["global_onset_quarter"])
        hi = lo + f(rest["notated_duration_quarter"])
        if [rest["part_id"], rest["voice_id"]] == sound["lane"] and max(lo, release, c) < min(hi, d):
            rests.append({"rest_ref": rest["rest_id"], "source_ref_id": rest["source_ref_id"],
                "full_span": _span(lo, hi), "observed_following_span": _span(max(lo, release, c), min(hi, d)),
                "hidden": rest["hidden"], "overlap_is_silence_confirmation": False})
    later = [{"sound_ref": s["sound_ref"], "full_span": deepcopy(s["span"]),
        "observed_span": deepcopy(s["observed_span"]), "source_guards": _guards(s)}
        for s in _positive(scope) if s["lane"] == sound["lane"] and f(s["observed_span"]["end"]) > release]
    return {"boundary_time": q(when), "candidate_terminal_release_time": q(release),
        "arrival_and_terminal_are_distinct_coordinates": True, "full_sound_span": deepcopy(sound["span"]),
        "full_sound_duration_quarters": q(release - a), "notated_duration_ratios": ratios,
        "observed_horizon": deepcopy(scope["analysis_span"]), "release_inside_observed_horizon": c <= release < d,
        "release_at_context_endpoint": release == d, "release_beyond_observed_horizon": release > d,
        "following_observation_status": "inside_observed_horizon" if c <= release < d else "unassessed_at_or_beyond_context_endpoint",
        "later_same_raw_lane_attacks": sorted(attacks, key=lambda r: (f(r["onset"]), r["sound_ref"])),
        "observed_following_same_raw_lane_rest_spans": sorted(rests, key=lambda r: (f(r["full_span"]["start"]), r["rest_ref"])),
        "later_same_raw_lane_positive_sounds": sorted(later, key=lambda r: r["sound_ref"]),
        "no_observed_later_attack_is_phrase_closure": False,
        "sustain_or_ornament_is_universal_cadence_counterevidence": False,
        "raw_lane_endpoint_is_logical_voice_identity": False,
        "phrase_terminal": "unassessed", "performed_release": "unassessed"}


def _transition_pair(scope, bundle, left, right, when):
    facts = _facts(scope)
    a, b = left["sound_ref"], right["sound_ref"]
    source, target = facts[a], facts[b]
    lane = source["lane"]
    if lane is None or lane != target["lane"]:
        raise ValueError("native_extreme_transition_requires_same_known_raw_lane")
    graph = next((g for g in scope["graphs"] if g["lane"] == lane), None)
    entry = None if bundle is None else next((e for e in bundle["entries"] if e["lane"] == lane), None)
    complete = bundle is not None and bundle["status"] == "complete_all_lane_witness"
    same = a == b
    guards = sorted(set(_guards(source)["blockers"] + _guards(target)["blockers"]))
    blockers = list(guards)
    if graph is None or graph["status"] != "ready":
        blockers.append("raw_lane_graph_unavailable_or_not_ready")
    if not complete or entry is None or entry.get("witness") is None:
        blockers.append("same_complete_all_raw_lane_completion_unavailable")
    links = set() if not complete else temporal._links(bundle)
    satisfied = None if blockers else same or (a, b) in links
    status = ("literal_same_sound_carry_without_completion_certification" if same and not complete else
        "unassessed_transition_prerequisites" if blockers else
        "literal_same_sound_carry_under_this_complete_bundle" if same else
        "required_link_satisfied_under_this_same_bundle" if satisfied else "not_satisfied_under_this_bundle_not_global_absence")
    return {"source_sound_ref": a, "arrival_sound_ref": b, "raw_lane": deepcopy(lane),
        "source_extreme_axes": deepcopy(left["extreme_axes"]), "arrival_extreme_axes": deepcopy(right["extreme_axes"]),
        "boundary_time": q(when), "same_sound_carry": same, "required_links": [] if same else [[a, b]],
        "observed_direct_temporal_contiguity": same or f(source["span"]["end"]) == f(target["span"]["start"]),
        "same_complete_all_lane_bundle": complete, "satisfied_under_same_completion": satisfied,
        "graph_ref": None if graph is None else _ref(graph), "bundle_ref": None if bundle is None else _ref(bundle),
        "query_ref": None if entry is None else _ref(entry["query"]),
        "witness_ref": None if entry is None or entry.get("witness") is None else _ref(entry["witness"]),
        "status": status, "blockers": sorted(set(blockers)), "true_voice_identity_confirmed": False,
        "absence_is_global": False, "structural_motion_confirmed": False}


def _positions(identity):
    return sorted({f(span[side]) for span in identity["slot_spans"] for side in ("start", "end")})


def _extreme_ids(extremes):
    return sorted(set(extremes["lowest_sound_refs"]) | set(extremes["highest_sound_refs"]))


def _plan(scope, comparison):
    identities = comparison["selector_inventory"]
    cached, plans, probes = {}, [], set()
    facts = _facts(scope)
    boundary_count = pair_count = extreme_count = shape_count = 0
    for identity in identities:
        times = _positions(identity)
        counts = []
        for when in times:
            if when not in cached:
                cached[when] = _boundary_indices(scope, when)
            _, _, before, at = cached[when]
            old_ids, new_ids = _extreme_ids(before), _extreme_ids(at)
            pairs = sum(facts[a]["lane"] is not None and facts[a]["lane"] == facts[b]["lane"] for a in old_ids for b in new_ids)
            counts.append(pairs)
            probes.update((sid, when) for sid in [*old_ids, *new_ids])
            extreme_count += len(old_ids) + len(new_ids)
            pair_count += pairs
        boundary_count += len(times)
        shape_count += 10 * len(identity["slot_spans"])
        plans.append({"times": times, "pair_counts": counts})
    # Logical visits count shared literal/probe inventories once and candidate
    # factor/degree/function projections and every same-lane pair occurrence.
    projection = scope["literal_observation"]["core_projection"]
    snapshot_count = len(scope["sound_facts"]) + len(_slots(scope)) + len(projection["measures"])
    known_work = (len(cached) + len(probes)) * snapshot_count + 2 * extreme_count + shape_count + pair_count
    complete = (not identities or (scope["context_sound_inventory_complete"] is True
        and comparison["status"] == "computed_same_scope_evidence_not_selected"))
    return {"plans": plans, "cached": cached, "probe_keys": probes,
        "planned_boundary_observations": boundary_count,
        "planned_transition_pairs": pair_count if complete else None,
        "known_transition_pair_subtotal": pair_count,
        "planned_query_work_items": known_work if complete else None,
        "known_stored_query_work_subtotal": known_work,
        "planned_unique_literal_boundary_coordinates": len(cached),
        "planned_unique_terminal_probes": len(probes)}


def _variant(source_state, identity, slot):
    vid = identity["origin_variant_ids"][slot]
    if vid not in source_state.lookups["variants"]:
        return None
    return indexed._thaw(source_state.data["index"]["variant_inventory"][source_state.lookups["variants"][vid]]["variant"])


def _key(source_state, identity):
    kid = identity["key_ref"]["record_id"]
    return indexed._thaw(source_state.data["index"]["keys"][source_state.lookups["keys"][kid]])


def _key_context(key):
    segment = key["segments"][0]
    known = (segment["tonic"] is not None and segment["mode"] != "unknown"
        and segment["scale_form"] in tonal.SCALES and f(segment["tonic"]["alter"]).denominator == 1)
    return {"registered_key_ref": _ref(key), "registered_key": deepcopy(key),
        "key_coordinate_prerequisites_available": known,
        "status": "explicit_registered_key_coordinate_assumption" if known else "registered_unknown_key_alternative",
        "provenance": deepcopy(key["provenance"]), "signature_declarations": deepcopy(key["declarations"]),
        "signature_used_for_candidate_universe": key["provenance"]["kind"] == "literal_IR_measure_key_signature_interpretation",
        "signature_is_not_key_proof": True, "exhaustive_local_key_universe": key["exhaustive_local_key_universe"],
        "unknown_covers_signature_external_alternatives": key["unknown_covers_signature_external_alternatives"],
        "key_confirmed": False, "scale_form_is_not_melodic_direction_rule": True}


def _profile_axes(profile, variant):
    if profile is None or variant is None or variant["members"] is None:
        return {"raw_pooled_core_present": None, "guarded_pooled_core_present": None,
            "guarded_simultaneous_core_present": None, "missing_guarded_spellings": None,
            "profile_available": profile is not None, "source_or_hypothesis_blockers": ["literal_profile_or_spelled_members_unavailable"]}
    members = {frozen._pitch_key(p) for p in variant["members"]}
    raw = {frozen._pitch_key(r["pitch"]) for r in profile["rows"] if r["state"] == "member"}
    guarded = {frozen._pitch_key(r["pitch"]) for r in profile["rows"]
        if r["state"] == "member" and r["eligible_as_analysis_source"] is True}
    return {"profile_available": True, "raw_pooled_core_present": members <= raw,
        "guarded_pooled_core_present": members <= guarded,
        "guarded_simultaneous_core_present": any(c["source_guard_missing_spellings"] == [] for c in profile["cells"]),
        "missing_guarded_spellings": [deepcopy(p) for p in variant["members"] if frozen._pitch_key(p) not in guarded],
        "source_or_hypothesis_blockers": deepcopy(profile["blockers"]),
        "pooled_or_simultaneous_presence_is_harmony_confirmation": False}


def _truth(values):
    return False if any(v is False for v in values) else None if any(v is None for v in values) else True


def _function_context(path, variants, key, internal_literal):
    explicit = [r for r in path["function_shapes"] if r["explicit_transition_assumption"]]
    if not explicit:
        return _seal({"version": VERSION, "progression_path_ref": _ref(path), "bundle_ref": deepcopy(path["bundle_ref"]),
            "status": "not_applicable_no_internal_declared_transition", "joint_conditional_functional_evidence": None,
            "function_shape": None, "transition_assumption": None, "ordinary_strategy": None,
            "prerequisite_axes": {}, "missing_semantic_premises": ["following_target_not_declared"],
            "secondary_function_confirmed": False, "tonicization_confirmed": False,
            "modulation_confirmed": False, "cadence_confirmed": False, "flags": _flags()}, FUNCTION_PREFIX)
    if len(explicit) != 1 or len(variants) != 2 or internal_literal is None:
        raise ValueError("exact_single_original_internal_transition_required")
    function = explicit[0]["function"]
    query = path["transition_assessment"]
    ordinary = None if query is None else query["ordinary_strategy"]
    profile_axes = [_profile_axes(p, v) for p, v in zip(path["profiles"], variants)]
    known_key = _key_context(key)["key_coordinate_prerequisites_available"]
    projection = None if function is None else function["key_projection"]
    projection_known = (None if not known_key else projection is not None
        and projection["target_coordinate"] is not None and not projection["unassessed_reasons"])
    facts = internal_literal["source_guards"]
    lows = set(internal_literal["lowest_highest_before"]["lowest_sound_refs"]
        + internal_literal["lowest_highest_at"]["lowest_sound_refs"])
    bass_guards = None if not lows else all(not r["blockers"] for r in facts if r["sound_ref"] in lows)
    shape = None if function is None else function["shape_compatible"]
    target_shape = None if function is None else function["target_shape_compatible"]
    function_usable = None if function is None else function["status"] == "conditional_function_shape"
    actual_rows = None if ordinary is None else (ordinary["inventory_complete"] is True
        and ordinary["role_assessments"] is not None and query["obligation_kernel_ref"] is not None)
    ordinary_truth = None if ordinary is None else ordinary["whole_ordinary_template_satisfied"]
    core = _truth([p["guarded_pooled_core_present"] for p in profile_axes])
    axes = {"source_shape_compatible": shape, "target_triad_core_shape_compatible": target_shape,
        "function_shape_prerequisites_available": function_usable,
        "known_explicit_key_coordinate": projection_known,
        "same_registered_complete_all_raw_lane_bundle": path["axes"]["same_complete_all_lane_bundle"],
        "guarded_pooled_literal_core_present": core, "observed_lowest_source_guards_passed": bass_guards,
        "actual_ordinary_role_rows_available": actual_rows,
        "whole_explicit_ordinary_template_satisfied": ordinary_truth,
        "profile_literal_evidence": profile_axes,
        "literal_core_and_time_audit": None if query is None else deepcopy(query["literal_core_and_time_audit"]),
        "all_critical_doublings_resolved": None,
        "guarded_simultaneous_core_is_required_for_distributed_chords": False}
    truth = _truth([shape, target_shape, function_usable, projection_known,
        axes["same_registered_complete_all_raw_lane_bundle"], core, bass_guards, actual_rows, ordinary_truth])
    return _seal({"version": VERSION, "progression_path_ref": _ref(path), "bundle_ref": deepcopy(path["bundle_ref"]),
        "status": "conditional_functional_relation_under_explicit_key_and_same_completion" if truth is True else
            "withheld_joint_functional_prerequisites_not_music_error" if truth is False else "unassessed_joint_functional_prerequisites",
        "joint_conditional_functional_evidence": truth, "function_shape": deepcopy(function),
        "transition_assumption": deepcopy(path["transition_assumption"]), "ordinary_strategy": deepcopy(ordinary),
        "prerequisite_axes": axes, "conditional_relation_kind": None if function is None else function["function_kind"],
        "key_projection": deepcopy(projection), "function_shape_blockers": [] if function is None else deepcopy(function["blockers"]),
        "missing_semantic_premises": ["harmony_hypotheses_unconfirmed", "local_key_uncertified",
            "logical_voice_identity_unconfirmed", "every_critical_doubling_not_individually_required",
            "tonicization_modulation_and_phrase_closure_unestablished"],
        "applied_target_relation_is_secondary_function_proof": False,
        "chromatic_member_is_secondary_or_modulation_proof": False,
        "secondary_function_confirmed": False, "tonicization_confirmed": False,
        "modulation_confirmed": False, "cadence_confirmed": False, "flags": _flags()}, FUNCTION_PREFIX)


def _source_snapshots(scope, sound):
    projection = scope["literal_observation"]["core_projection"]
    notes = {r["event_id"]: r["core_event"] for r in _slots(scope) if r["event_kind"] == "note"}
    source_notes = [deepcopy(notes[nid]) for nid in sound["source_note_refs"]]
    source_ids = {n["source_ref_id"] for n in source_notes}
    literal = next(s for s in projection["sounding_events"] if s["sounding_event_id"] == sound["sound_ref"])
    tid = literal.get("tie_chain_id")
    return {"full_sound_snapshot": deepcopy(literal), "source_note_snapshots": source_notes,
        "source_reference_snapshots": [deepcopy(r) for r in projection["source_references"] if r["source_ref_id"] in source_ids],
        "tie_chain_snapshot": next((deepcopy(r) for r in projection["tie_chains"] if r["tie_chain_id"] == tid), None)}


def _extreme_inventory(scope, evidence, side, variant, key, probes):
    extreme = evidence["lowest_highest_" + side]
    low, high = set(extreme["lowest_sound_refs"]), set(extreme["highest_sound_refs"])
    facts = _facts(scope)
    shape = _ordinary_shape(variant)
    when = f(evidence["boundary_time"])
    rows = []
    for sid in sorted(low | high):
        sound = facts[sid]
        probe_key = (sid, when)
        if probe_key not in probes:
            probes[probe_key] = _terminal(scope, sound, when, evidence["notated_metric"])
        rows.append({"sound_ref": sid, "extreme_axes": [name for name, ids in (("lowest", low), ("highest", high)) if sid in ids],
            "raw_lane": deepcopy(sound["lane"]), "written_pitch": deepcopy(sound["pitch"]),
            "source_note_refs": deepcopy(sound["source_note_refs"]), "attack_note_ref": sound["attack_note_ref"],
            "source_snapshots": _source_snapshots(scope, sound), "source_guards": _guards(sound),
            "candidate_factor": _factor(sound, variant, shape, is_lowest=sid in low,
                lowest_spelling_ambiguous=extreme["lowest_spelling_ambiguous"]),
            "candidate_scale_degree": _degree(sound["pitch"], key), "terminal_probe": deepcopy(probes[probe_key])})
    return {"rows": rows, "raw_extreme_sound_count": len(rows),
        "lowest_spelling_ambiguous": extreme["lowest_spelling_ambiguous"],
        "highest_spelling_ambiguous": extreme["highest_spelling_ambiguous"],
        "ordinary_assumed_shape": shape, "structural_bass": "unassessed", "structural_melody": "unassessed"}


def _coordinate_of_root(variant, key):
    return None if variant is None or variant["root"] is None else _degree(variant["root"], key)["coordinate"]


def _unaltered_degree(coordinate, degree):
    return None if coordinate is None else coordinate["degree"] == degree and coordinate["alteration_from_scale"] == 0


def _cadence_axes(left, arrival, key, before, at, function_context, transitions, internal):
    source_coordinate = _coordinate_of_root(left, key)
    arrival_coordinate = _coordinate_of_root(arrival, key)
    ending_applicable = internal or (left is not None and arrival is None)
    ending = arrival if internal else left if arrival is None else None
    ending_coordinate = _coordinate_of_root(ending, key)
    ending_shape = _ordinary_shape(ending)
    functions = function_context.get("function_shape") if internal else None
    authentic_family = None if functions is None else functions["family"] in ("V", "V7")
    tonic_target = _unaltered_degree(arrival_coordinate, 1)
    mode = key["segments"][0]["mode"]
    home_quality = (None if functions is None or mode == "unknown" else
        functions["target_quality"] == ("M" if mode == "major" else "m"))
    ending_dominant = _unaltered_degree(ending_coordinate, 5)
    major_dominant = None if ending is None or ending_shape["quality"] is None else (
        ending_shape["status"] == "conditional_complete_ordinary_shape" and ending_shape["quality"] in ("major", "major_minor_seventh"))
    before_low = [r for r in before["rows"] if "lowest" in r["extreme_axes"]]
    at_low = [r for r in at["rows"] if "lowest" in r["extreme_axes"]]
    at_high = [r for r in at["rows"] if "highest" in r["extreme_axes"]]
    def root_position(rows):
        values = [r["candidate_factor"]["conditional_inversion_shape"] for r in rows]
        return None if not values or any(v is None for v in values) else all(v == 0 for v in values)
    def tonic_top(rows):
        values = [r["candidate_scale_degree"]["coordinate"] for r in rows]
        return None if not values or any(v is None for v in values) else all(_unaltered_degree(v, 1) for v in values)
    source_root, target_root, top_tonic = root_position(before_low), root_position(at_low), tonic_top(at_high)
    shape_prereq = _truth([authentic_family, tonic_target, home_quality,
        None if functions is None else functions["shape_compatible"],
        None if functions is None else functions["target_shape_compatible"]]) if internal else None
    common_axes = {"internal_declared_transition_applicable": internal,
        "explicit_registered_key_coordinate_available": _key_context(key)["key_coordinate_prerequisites_available"],
        "source_root_coordinate": source_coordinate, "arrival_root_coordinate": arrival_coordinate,
        "candidate_ending_root_coordinate": ending_coordinate,
        "source_ordinary_shape": deepcopy(before["ordinary_assumed_shape"]),
        "arrival_ordinary_shape": deepcopy(at["ordinary_assumed_shape"]),
        "candidate_ending_ordinary_shape": ending_shape,
        "authentic_dominant_family_shape": authentic_family, "home_tonic_target_coordinate": tonic_target,
        "home_tonic_target_quality": home_quality,
        "candidate_ending_observation_applicable": ending_applicable,
        "candidate_ending_role": "internal_arrival_with_separate_full_release_probe" if internal else
            "left_assumption_at_analysis_endpoint" if ending_applicable else "analysis_start_has_no_ending_candidate",
        "candidate_ending_dominant_coordinate": ending_dominant, "candidate_ending_major_dominant_shape": major_dominant,
        "observed_before_lowest_root_position_under_assumption": source_root,
        "observed_arrival_lowest_root_position_under_assumption": target_root,
        "observed_arrival_highest_tonic_degree_under_assumption": top_tonic,
        "same_bundle_extreme_transition_statuses": [r["status"] for r in transitions],
        "ordinary_joint_functional_context_ref": _ref(function_context) if internal else None,
        "ordinary_joint_functional_context_status": function_context["status"] if internal else "not_applicable_no_new_external_transition",
        "arrival_full_release_probe_refs": [{"sound_ref": r["sound_ref"],
            "release": deepcopy(r["terminal_probe"]["candidate_terminal_release_time"]),
            "following_status": r["terminal_probe"]["following_observation_status"]} for r in at["rows"]],
        "before_full_release_probe_refs": [{"sound_ref": r["sound_ref"],
            "release": deepcopy(r["terminal_probe"]["candidate_terminal_release_time"]),
            "following_status": r["terminal_probe"]["following_observation_status"]} for r in before["rows"]],
        "literal_extremes_are_structural_voices": False, "ending_candidate_is_phrase_terminal": False}
    nominal = {"PAC": _truth([shape_prereq, source_root, target_root, top_tonic]) if internal else None,
        "IAC": shape_prereq,
        "HC": _truth([ending_dominant, major_dominant])}
    return {kind: {"status": "unassessed_missing_semantic_prerequisites", "confirmed": False,
        "nominal_harmonic_and_literal_extreme_prerequisites": nominal[kind],
        "nominal_prerequisites_are_cadence_confirmation": False,
        "literal_prerequisite_axes": deepcopy(common_axes), "missing_premises": list(MISSING_PREMISES),
        "IAC_literal_extreme_refinement_unassessed": kind == "IAC"}
        for kind in ("PAC", "HC", "IAC")}


def _raw_time_snapshot(path):
    account = path["whole_path_account"]
    if account is None:
        return None, None
    reference = {"progression_path_ref": _ref(path), "json_pointer": "/whole_path_account", "value_sha256": digest(account)}
    values = {k: deepcopy(account[k]) for k in ("total_note_time", "raw_note_time", "note_time", "conditional_explanation_note_time")}
    return reference, values


def _path(source_state, scope, path, identity, plan, bundle, literals, probes):
    variants = [_variant(source_state, identity, slot) for slot in range(len(identity["slot_spans"]))]
    key = _key(source_state, identity)
    cut = f(identity["slot_spans"][0]["end"]) if len(variants) == 2 else None
    function = _function_context(path, variants, key, None if cut is None else literals[cut])
    boundaries = []
    for index, when in enumerate(plan["times"]):
        evidence = literals[when]
        left = next((v for v in variants if v is not None and f(v["span"]["end"]) == when), None)
        arrival = next((v for v in variants if v is not None and f(v["span"]["start"]) == when), None)
        before = _extreme_inventory(scope, evidence, "before", left, key, probes)
        at = _extreme_inventory(scope, evidence, "at", arrival, key, probes)
        pairs = [_transition_pair(scope, bundle, a, b, when) for a in before["rows"] for b in at["rows"]
            if a["raw_lane"] is not None and a["raw_lane"] == b["raw_lane"]]
        if len(pairs) != plan["pair_counts"][index]:
            raise ValueError("native_context_whole_transition_pair_plan_mismatch")
        internal = cut is not None and when == cut
        boundaries.append({"boundary_time": q(when), "literal_boundary_ref": _ref(evidence),
            "left_assumed_variant_ref": None if left is None else _ref(left),
            "arrival_assumed_variant_ref": None if arrival is None else _ref(arrival),
            "boundary_role": "internal_declared_transition" if internal else "analysis_start" if when == plan["times"][0] else "analysis_endpoint",
            "function_context_ref": _ref(function) if internal else None,
            "before_extremes": before, "arrival_extremes": at,
            "same_raw_lane_transitions": pairs, "planned_same_raw_lane_pairs": len(pairs),
            "cadence_prerequisites": _cadence_axes(left, arrival, key, before, at, function, pairs, internal),
            "selected": None})
    account_ref, raw = _raw_time_snapshot(path)
    return _seal({"version": VERSION, "progression_path_ref": _ref(path),
        **{name: deepcopy(path[name]) for name in ("logical_tuple", "group_id", "indexed_group_id", "partition",
            "origin_variant_ids", "origin_refs", "profile_refs", "key_ref", "bundle_ref")},
        "scope_ref": deepcopy(path["scope_ref"]), "analysis_span": deepcopy(path["analysis_span"]),
        "key_context": _key_context(key), "function_shapes": deepcopy(path["function_shapes"]),
        "whole_path_account_ref": account_ref, "raw_time_snapshot": raw,
        "function_context": function, "boundaries": boundaries,
        "status": "computed_conditional_context_prerequisites_not_selected", "reasons": [],
        "selected": None, "rank": None, "confidence": None, "flags": _flags()}, PATH_PREFIX)


def _summary(comparison, plan, paths, literal_count, probe_count, hold):
    tuples = {p["logical_tuple"]["record_id"] for p in paths}
    requested = {p["logical_tuple"]["record_id"] for p in comparison["selector_inventory"]}
    boundaries = {(p["logical_tuple"]["record_id"], f(b["boundary_time"])) for p in paths for b in p["boundaries"]}
    shapes = {(p["logical_tuple"]["record_id"], s["slot"], s["family"], s["quality"])
        for p in paths for s in p["function_shapes"] if s["function"] is not None}
    evaluated = {(p["logical_tuple"]["record_id"], s["slot"], s["family"], s["quality"])
        for p in paths for s in p["function_shapes"] if s["transition_assumption_evaluated"]}
    motion = {(p["logical_tuple"]["record_id"], s["slot"], s["family"], s["quality"])
        for p in paths for s in p["function_shapes"] if s["motion_assessed"]}
    universe = comparison["logical_universe"]
    total = universe["logical_path_key_tuples"]
    function_total = universe["logical_function_rows"]
    unknown = universe["unknown_product_groups"] != 0
    return {**{k: deepcopy(universe[k]) for k in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups")},
        "planned_hypotheses": len(comparison["selector_inventory"]), "computed_hypotheses": len(paths),
        "planned_boundary_observations": plan["planned_boundary_observations"],
        "observed_boundary_observations": sum(len(p["boundaries"]) for p in paths),
        "planned_transition_pairs": plan["planned_transition_pairs"], "known_transition_pair_subtotal": plan["known_transition_pair_subtotal"],
        "observed_transition_pairs": sum(len(b["same_raw_lane_transitions"]) for p in paths for b in p["boundaries"]),
        "planned_query_work_items": plan["planned_query_work_items"],
        "known_stored_query_work_subtotal": plan["known_stored_query_work_subtotal"],
        "planned_unique_literal_boundary_coordinates": plan["planned_unique_literal_boundary_coordinates"],
        "cached_literal_boundary_coordinates": literal_count,
        "planned_unique_terminal_probes": plan["planned_unique_terminal_probes"], "cached_terminal_probes": probe_count,
        "unique_requested_logical_tuples": len(requested), "tested_logical_path_key_tuples": len(tuples),
        "distinct_tuple_key_boundary_observations": len(boundaries),
        "unassessed_logical_path_key_tuples": None if unknown else total - len(tuples),
        "known_unassessed_logical_path_key_tuple_subtotal": total - len(tuples),
        "restored_function_shape_rows": len(shapes), "evaluated_transition_assumption_rows": len(evaluated),
        "assessed_transition_function_rows": len(motion),
        "unassessed_function_shapes": None if unknown or function_total is None else function_total - len(shapes),
        "known_unassessed_function_shape_subtotal": None if function_total is None else function_total - len(shapes),
        "known_key_coordinate_paths": sum(p["key_context"]["key_coordinate_prerequisites_available"] for p in paths),
        "unknown_key_coordinate_paths": sum(not p["key_context"]["key_coordinate_prerequisites_available"] for p in paths),
        "joint_conditional_functional_relation_paths": sum(p["function_context"]["joint_conditional_functional_evidence"] is True for p in paths),
        "cadence_prerequisite_records": sum(len(b["cadence_prerequisites"]) for p in paths for b in p["boundaries"]),
        "conditional_inversion_observations": sum(r["candidate_factor"]["conditional_inversion_shape"] is not None
            for p in paths for b in p["boundaries"] for side in ("before_extremes", "arrival_extremes") for r in b[side]["rows"]),
        "whole_request_held": hold,
        "count_semantics": "selector_occurrences_distinct_original_tuple_keys_boundaries_and_shared_literal_coordinates_not_accuracy_or_confidence"}


def build_context_prepared(session, *, max_hypotheses=64, max_boundary_observations=2048,
                           max_transition_pairs=4096, query_work_budget=200000):
    """Pre-plan the entire declared sidecar before any candidate assessment."""
    limits = dict(zip(CAPS, (max_hypotheses, max_boundary_observations, max_transition_pairs, query_work_budget)))
    _caps(limits)
    authority, source_state = _issued(session)
    contract = _contract()
    comparison = indexed._thaw(authority.data["comparison"])
    scope = indexed._thaw(source_state.data["scope"])
    before = digest([comparison, scope])
    plan = _plan(scope, comparison)
    reasons = []
    if comparison["status"] != "computed_same_scope_evidence_not_selected":
        reasons.extend(["inherited_whole_progression_comparison_hold", *comparison["reasons"]])
    if len(comparison["selector_inventory"]) > max_hypotheses:
        reasons.append("whole_context_hypothesis_inventory_budget_hold_no_prefix")
    if plan["planned_boundary_observations"] > max_boundary_observations:
        reasons.append("whole_context_boundary_inventory_budget_hold_no_prefix")
    if plan["planned_transition_pairs"] is None or plan["planned_query_work_items"] is None:
        reasons.append("whole_context_source_or_work_inventory_unknown_no_prefix")
    else:
        if plan["planned_transition_pairs"] > max_transition_pairs:
            reasons.append("whole_context_transition_pair_inventory_budget_hold_no_prefix")
        if plan["planned_query_work_items"] > query_work_budget:
            reasons.append("whole_context_query_work_budget_hold_no_prefix")
    paths, literals, probes = [], {}, {}
    bundle_id = comparison["bundle_id"]
    bundle = None if bundle_id is None else indexed._thaw(source_state.data["registered_bundles"][source_state.lookups["bundles"][bundle_id]])
    if not reasons:
        if len(comparison["hypotheses"]) != len(comparison["selector_inventory"]):
            raise ValueError("context_parent_complete_hypothesis_inventory_mismatch")
        literals = {when: _boundary(scope, when) for when in sorted(plan["cached"])}
        paths = [_path(source_state, scope, path, identity, p, bundle, literals, probes)
            for path, identity, p in zip(comparison["hypotheses"], comparison["selector_inventory"], plan["plans"])]
        if set(probes) != plan["probe_keys"]:
            raise ValueError("context_unique_terminal_probe_inventory_mismatch")
    result = _seal({"version": VERSION, "contract": contract, "binding": deepcopy(comparison["binding"]),
        "analysis_span": deepcopy(comparison["analysis_span"]), "comparison_ref": _ref(comparison),
        **{name + "_ref": deepcopy(comparison[name + "_ref"]) for name in ("scope", "index", "obligations")},
        "logical_universe": deepcopy(comparison["logical_universe"]),
        "bundle_ref": deepcopy(comparison["bundle_ref"]), "bundle_id": bundle_id, "bundle_status": comparison["bundle_status"],
        "selector_inventory": deepcopy(comparison["selector_inventory"]), "paths": paths,
        "literal_boundary_inventory": [literals[t] for t in sorted(literals)], "resource_limits": limits,
        "summary": _summary(comparison, plan, paths, len(literals), len(probes), bool(reasons)),
        "status": "whole_context_source_or_work_hold" if reasons else "computed_conditional_context_prerequisites_not_selected",
        "reasons": sorted(set(reasons)), "selected": None, "preferred": None, "winner": None, "rank": None, "confidence": None,
        "flags": _flags(),
        "validation_semantics": "authentic_owned_exact_phase20_replay_then_same_parent_state_and_current_contract_before_and_after",
        "resource_limit_semantics": "whole_request_logical_snapshot_and_projection_visits_no_prefix_not_CPU_byte_RSS_or_lifetime_bound",
        "limits": ["No new key, harmony segmentation, target, voice completion or legacy view is fabricated.",
            "All original function bodies and raw note-time classifications remain unchanged.",
            "Known key coordinates and applied targets are hypotheses, not secondary-function or modulation proof.",
            "Literal extrema and same-completion edges do not certify structural voices or every doubling's resolution.",
            "Harmony arrival, full sound release and phrase closure are distinct premises.",
            "PAC/HC/IAC premise facts retain missing semantics and never confirm a cadence.",
            "Endpoint or absent later observations do not prove silence, closure or cadence."]}, PREFIX)
    current, source = _issued(session)
    if (current is not authority or source is not source_state or before != digest([comparison, scope])
            or not indexed._same(contract, _contract())):
        raise ValueError("context_parent_data_authority_or_code_changed_during_build")
    return result


def build_context(ir, scope, hypotheses, index, relations, grounding, temporal_record,
                  boundary_record, obligations_record, comparison_record, **options):
    if set(options) - set(CAPS):
        raise TypeError("unknown_progression_context_limit")
    _caps({**DEFAULTS, **options})
    return build_context_prepared(prepare_context(ir, scope, hypotheses, index, relations, grounding,
        temporal_record, boundary_record, obligations_record, comparison_record), **options)


def validate_context(ir, scope, hypotheses, index, relations, grounding, temporal_record,
                     boundary_record, obligations_record, comparison_record, context_record, **options):
    """Fresh validation never trusts a caller's re-sealed contextual premises."""
    frozen._check(context_record, PREFIX)
    if not indexed._same(context_record, build_context(ir, scope, hypotheses, index, relations, grounding,
            temporal_record, boundary_record, obligations_record, comparison_record, **options)):
        raise ValueError("stale_foreign_modified_or_promoting_progression_context")
    return True
