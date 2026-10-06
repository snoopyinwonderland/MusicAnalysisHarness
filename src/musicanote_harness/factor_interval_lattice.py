"""Native all-interval DAG and explicit complete multi-slot comparisons.

This is a new proposal universe, not an enlargement of an fmeh/fmiidx path.
Every interval has a fresh inclusive supplier. Counts do not enumerate paths.
One registered full-scope witness supports ALL transitions of a comparison.
Provider ornament output is never credited as same-witness NCT evidence here.
"""
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import hmac
from math import comb
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_expanded_hypotheses as kernels
from . import factor_expanded_scope as expanded
from . import factor_indexed_hypotheses as owned
from . import factor_progression_context as context
from . import harmony_candidate_catalog as catalog
from . import harmony_factorized_voice_paths as geometry
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-interval-lattice-0.1.0"
PREFIX = "fmilat_"
ORIGIN_PREFIX = "fmilorigin_"
BUNDLE_PREFIX = "fmilbundle_"
COMPARISON_PREFIX = "fmilcompare_"
DEFAULTS = dict(max_cut_coordinates=64, max_catalogs=1024,
                max_variants=200000, max_dp_work=200000)
_SESSIONS = WeakKeyDictionary()
_BUNDLES = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    flags = context._flags()
    # These are phase-specific activity declarations, not safety policies.
    # Native paths/completions and actual first-change routes are created here;
    # retaining a parent's "not created/evaluated" flag would be misleading.
    for name in ("new_key_path_or_completion_created", "delayed_resolution_evaluated",
                 "same_pitch_delayed_resolution_evaluated", "functional_delayed_obligations_evaluated"):
        flags.pop(name, None)
    return {**flags, "old_key_path_or_completion_extended": False,
            "all_grid_paths_materialized": False,
            "all_transition_assumptions_evaluated": False,
            "provider_ornaments_used_as_joint_NCT_proof": False}


def _contract():
    modules = (expanded, kernels, catalog, geometry, owned, context)
    return {"version": VERSION,
        "sources": [{"module": __name__, "sha256": sha256(Path(__file__).read_bytes()).hexdigest()}]
            + [{"module": m.__name__, "sha256": sha256(Path(m.__file__).read_bytes()).hexdigest()}
               for m in modules],
        "supplier_contract": kernels._contract(), "scope_contract": expanded._contract(),
        "context_kernel_contract": context._contract()}


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_lattice_limit_required:" + name)


def _caps(values):
    if set(values) != set(DEFAULTS):
        raise ValueError("closed_lattice_limits_required")
    for name, value in values.items():
        _integer(value, name)


def _seal(body, prefix):
    return kernels._seal(body, prefix)


def _ref(record):
    return kernels._ref(record)


def _points(scope):
    start, end = span_bounds(scope["analysis_span"])
    return [start, *sorted({f(s["span"][side]) for s in scope["sound_facts"]
                           for side in ("start", "end")
                           if start < f(s["span"][side]) < end}), end]


def _count_universe(weights, point_count, key_count):
    """Exact slot-count DAG DP. None is unavailable, never a zero supplier.

    Known weighted subtotal and unknown nonzero skeleton denominator coexist.
    A certified zero edge annihilates even an unknown prefix.
    """
    if type(point_count) is not int or point_count < 2:
        raise ValueError("at_least_two_exact_coordinates_required")
    _integer(key_count, "key_count")
    for indices, weight in weights.items():
        if (type(indices) is not tuple or len(indices) != 2
                or any(type(v) is not int for v in indices)
                or not 0 <= indices[0] < indices[1] < point_count):
            raise ValueError("exact_positive_coordinate_pair_required")
        if weight is not None and (type(weight) is not int or weight < 0):
            raise ValueError("exact_nonnegative_span_weight_required")
    last = point_count - 1
    known = [[0] * (last + 1) for _ in range(point_count)]
    unknown = [[0] * (last + 1) for _ in range(point_count)]
    certified = [[0] * (last + 1) for _ in range(point_count)]
    known[0][0] = certified[0][0] = 1
    for j in range(1, point_count):
        for slots in range(1, j + 1):
            for i in range(slots - 1, j):
                weight = weights.get((i, j))
                if weight == 0:
                    continue
                if weight is None:
                    unknown[j][slots] += certified[i][slots - 1] + unknown[i][slots - 1]
                else:
                    known[j][slots] += known[i][slots - 1] * weight
                    certified[j][slots] += certified[i][slots - 1]
                    unknown[j][slots] += unknown[i][slots - 1]
    rows = []
    for slots in range(1, last + 1):
        count = None if unknown[last][slots] else known[last][slots]
        rows.append({"slots": slots, "partition_skeletons": comb(last - 1, slots - 1),
            "known_nonzero_skeletons": certified[last][slots],
            "unknown_nonzero_skeletons": unknown[last][slots],
            "known_path_subtotal": known[last][slots], "logical_paths": count,
            "logical_path_keys": None if count is None else count * key_count,
            "slot_occurrences": None if count is None else count * slots,
            "internal_transition_occurrences": None if count is None else count * (slots - 1),
            "internal_function_shape_rows": None if count is None else count * key_count * (slots - 1) * 10,
            "terminal_inclusive_function_shape_rows": None if count is None else count * key_count * slots * 10})
    paths = None if any(r["logical_paths"] is None for r in rows) else sum(r["logical_paths"] for r in rows)
    slots_total = None if paths is None else sum(r["slot_occurrences"] for r in rows)
    return {"by_slot_count": rows, "partition_skeletons": 2 ** (last - 1),
        "known_path_subtotal": sum(r["known_path_subtotal"] for r in rows),
        "unknown_nonzero_skeletons": sum(r["unknown_nonzero_skeletons"] for r in rows),
        "logical_paths": paths, "logical_path_keys": None if paths is None else paths * key_count,
        "slot_occurrences": slots_total,
        "internal_transition_occurrences": None if paths is None else slots_total - paths,
        "internal_function_shape_rows": None if paths is None else (slots_total - paths) * key_count * 10,
        "terminal_inclusive_function_shape_rows": None if paths is None else slots_total * key_count * 10,
        "key_hypotheses": key_count,
        "transition_assumption_vectors_materialized": 0,
        "semantics": "all_complete_partitions_over_observed_grid_not_all_musical_segmentations"}


def _origin(scope, entry, candidate, candidate_index, alternative_index):
    # Generate from this freshly supplied interval, never trim an old origin.
    calculation = kernels._variant(scope, entry, candidate, candidate_index, alternative_index)
    body = {k: deepcopy(v) for k, v in calculation.items()
            if k not in ("record_id", "record_sha256", "segment_id")}
    body.update(version=VERSION, provenance={"kind": "fresh_native_interval_inclusive_supplier",
        "source_statement_ref": None, "source_path": None, "source_annotation_labels_used": False},
        source_scope_ref=_ref(scope), legacy_origin_rebound=False)
    body["segment_id"] = ORIGIN_PREFIX + digest(body)[:24]
    return _seal(body, ORIGIN_PREFIX)


def build_lattice(ir, scope, *, max_cut_coordinates=64, max_catalogs=1024,
                  max_variants=200000, max_dp_work=200000):
    limits = dict(max_cut_coordinates=max_cut_coordinates, max_catalogs=max_catalogs,
                  max_variants=max_variants, max_dp_work=max_dp_work)
    _caps(limits)
    before, contract = digest([ir, scope]), _contract()
    expanded.check_scope(scope, ir=ir)
    points = _points(scope)
    size = len(points)
    spans = size * (size - 1) // 2
    dp_work = size * (size - 1) * (size + 1) // 6
    reasons = []
    if size - 2 > max_cut_coordinates:
        reasons.append("whole_observed_cut_grid_exceeds_budget_no_prefix")
    if spans > max_catalogs:
        reasons.append("whole_interval_catalog_inventory_exceeds_budget_no_prefix")
    if dp_work > max_dp_work:
        reasons.append("whole_count_DP_exceeds_budget_no_prefix")
    if scope["context_sound_inventory_complete"] is not True:
        reasons.append("complete_scope_source_inventory_unavailable")
    keys = kernels._key_candidates(ir, scope)
    entries = []
    # No O(grid^2) supplier/pointer materialization when whole planning holds.
    if not reasons:
        for i in range(size - 1):
            for j in range(i + 1, size):
                span = kernels._span(points[i], points[j])
                supplier = catalog.propose(ir, span, scope["analysis_span"])
                catalog.validate(supplier)
                entries.append({"catalog_id": "fmilcat_" + digest([_ref(scope), span])[:24],
                    "point_indices": [i, j], "span": span, "supplier_catalog": supplier,
                    "candidate_count": len(supplier["candidates"]),
                    "variant_count": sum(max(1, len(c["spelling_alternatives"])) for c in supplier["candidates"]),
                    "origins": [], "status": "fresh_supplier_not_yet_indexed", "reasons": []})
    origin_count = None if reasons else sum(e["variant_count"] for e in entries)
    index_hold = origin_count is not None and origin_count > max_variants
    if index_hold:
        reasons.append("whole_native_origin_index_exceeds_budget_no_prefix")
    if not reasons:
        for entry in entries:
            for n, candidate in enumerate(entry["supplier_catalog"]["candidates"]):
                alternatives = range(len(candidate["spelling_alternatives"])) if candidate["spelling_alternatives"] else [None]
                entry["origins"].extend(_origin(scope, entry, candidate, n, a) for a in alternatives)
            entry["status"] = "ready_native_interval"
    elif index_hold:
        for entry in entries:
            entry.update(status="whole_native_origin_index_hold", reasons=list(reasons))
    weights = {tuple(e["point_indices"]): e["variant_count"] for e in entries}
    if dp_work <= max_dp_work and size - 2 <= max_cut_coordinates:
        universe = _count_universe(weights, size, len(keys))
    else:
        universe = {"by_slot_count": [], "partition_skeletons": 2 ** (size - 2),
            "logical_paths": None, "logical_path_keys": None, "slot_occurrences": None,
            "internal_transition_occurrences": None, "internal_function_shape_rows": None,
            "terminal_inclusive_function_shape_rows": None, "known_path_subtotal": None,
            "unknown_nonzero_skeletons": None, "key_hypotheses": len(keys),
            "transition_assumption_vectors_materialized": 0,
            "semantics": "whole_count_DP_hold_not_unknown_as_zero"}
    result = _seal({"version": VERSION, "contract": contract, "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]),
        "coordinate_times": [q(p) for p in points], "catalog_inventory": entries,
        "keys": keys, "universe": universe, "resource_limits": limits,
        "planned_catalogs": spans, "planned_dp_work": dp_work,
        "origin_count": origin_count, "materialized_origins": sum(len(e["origins"]) for e in entries),
        "catalog_inventory_representation": "all_positive_coordinate_pairs_i_less_than_j",
        "status": "whole_lattice_hold" if reasons else "ready_native_interval_lattice",
        "reasons": sorted(set(reasons)), "selected": None, "rank": None, "confidence": None,
        "flags": _flags(), "source_authority": "fresh_IR_scope_source_geometry_replay_not_absent_parent_file_replay",
        "limits": ["Observed sound endpoints are proposals, not certified harmonic boundaries.",
            "No old fmeh/fmiidx index, key path, origin or completion is extended.",
            "Fresh key reference forms include unknown; no new inferred local key.",
            "Supplier/provider ornament output is not a same-witness NCT claim.",
            "Counts and planning units do not measure musical accuracy, CPU time or memory bytes."]}, PREFIX)
    if before != digest([ir, scope]) or not owned._same(contract, _contract()):
        raise ValueError("lattice_inputs_or_contract_changed_during_build")
    return result


def validate_lattice(ir, scope, record):
    kernels._check(record, PREFIX)
    if not owned._same(record, build_lattice(ir, scope, **record["resource_limits"])):
        raise ValueError("stale_foreign_or_modified_native_lattice")
    return True


class _PreparedLattice:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    data: object
    lookups: object
    contract_digest: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, owned._encoded([id(handle), id(state), id(state.data), id(state.lookups),
                       state.contract_digest]), "sha256")


def _issued(handle):
    if type(handle) is not _PreparedLattice or handle not in _SESSIONS:
        raise ValueError("issued_native_lattice_session_required")
    state = _SESSIONS[handle]
    if (type(state) is not _State or type(state.data) is not MappingProxyType
            or type(state.lookups) is not MappingProxyType):
        raise ValueError("native_lattice_immutable_owned_state_required")
    if state.contract_digest != digest(_contract()) or not hmac.compare_digest(state.authentication, _auth(handle, state)):
        raise ValueError("native_lattice_owned_state_or_contract_changed")
    return state


def prepare_lattice(ir, scope, record=None, **caps):
    original_record = record
    inputs_before, contract = digest([ir, scope, original_record]), _contract()
    if record is not None and caps:
        raise ValueError("saved_lattice_limits_cannot_be_overridden")
    if record is None:
        record = build_lattice(ir, scope, **caps)
    else:
        validate_lattice(ir, scope, record)
    data = owned._freeze({"scope": deepcopy(scope), "lattice": deepcopy(record)})
    origins = {o["record_id"]: o for e in record["catalog_inventory"] for o in e["origins"]}
    if len(origins) != record["materialized_origins"]:
        raise ValueError("duplicate_native_origin_identity")
    lookup = owned._freeze({"origins": origins, "keys": {k["record_id"]: k for k in record["keys"]},
        "sounds": {s["sound_ref"]: s for s in scope["sound_facts"]}})
    if (inputs_before != digest([ir, scope, original_record])
            or not owned._same(contract, _contract())
            or not owned._same(record["contract"], contract)
            or not owned._same(record["scope_ref"], _ref(scope))):
        raise ValueError("native_lattice_inputs_or_contract_changed_during_preparation")
    handle = _PreparedLattice()
    state = _State(data, lookup, digest(contract), b"")
    object.__setattr__(state, "authentication", _auth(handle, state))
    _SESSIONS[handle] = state
    _BUNDLES[handle] = {}
    _issued(handle)
    return handle


def lattice_prepared(session):
    return owned._thaw(_issued(session).data["lattice"])


def compile_bundle_prepared(session, required_links=(), *, geometry_work_budget=100000):
    _integer(geometry_work_budget, "geometry_work_budget")
    state = _issued(session)
    if not isinstance(required_links, (list, tuple)):
        raise ValueError("explicit_required_link_collection_required")
    normalized = set()
    sounds = state.lookups["sounds"]
    for pair in required_links:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(type(s) is not str or s not in sounds for s in pair):
            raise ValueError("exact_original_sound_link_required")
        a, b = pair
        if sounds[a]["lane"] is None or sounds[a]["lane"] != sounds[b]["lane"]:
            raise ValueError("required_link_has_foreign_or_different_raw_lane")
        normalized.add((a, b))
    scope, lattice = (owned._thaw(state.data[n]) for n in ("scope", "lattice"))
    by_lane = defaultdict(list)
    for a, b in sorted(normalized):
        by_lane[tuple(sounds[a]["lane"])].append([a, b])
    entries, reasons = [], []
    if not scope["context_sound_inventory_complete"]:
        reasons.append("complete_scope_source_inventory_unavailable")
    for graph in sorted(scope["graphs"], key=lambda g: g["lane"]):
        query = geometry.query(graph, required_links=by_lane.get(tuple(graph["lane"]), []),
                               work_budget=geometry_work_budget)
        witness = (geometry.materialize_witness(graph, query)
                   if query["status"] == "exact_count" and query["possible_assignments"] != "0" else None)
        entries.append({"lane": deepcopy(graph["lane"]), "graph_ref": _ref(graph), "query": query,
                        "witness": witness, "status": "complete" if witness else "lane_withheld"})
        if witness is None:
            reasons.extend(["raw_lane_completion_withheld", *query["reasons"]])
    actual = sorted({tuple(pair) for e in entries if e["witness"] is not None
                     for pair in e["witness"]["assignment"]["links"]})
    expected_lanes = sorted([r["part_id"], r["voice_id"]] for r in scope["raw_lanes"])
    if sorted(e["lane"] for e in entries) != expected_lanes:
        reasons.append("complete_raw_lane_inventory_missing")
    if not reasons and actual != sorted(normalized):
        raise ValueError("sparse_actual_completion_does_not_equal_joint_request")
    result = _seal({"version": VERSION, "contract": _contract(), "scope_ref": _ref(scope),
        "lattice_ref": _ref(lattice), "binding": deepcopy(scope["binding"]),
        "analysis_span": deepcopy(scope["analysis_span"]), "required_links": [list(p) for p in sorted(normalized)],
        "materialized_witness_links": [list(p) for p in actual], "entries": entries,
        "covered_lanes": expected_lanes, "resource_limits": {"geometry_work_budget": geometry_work_budget},
        "status": "complete_all_lane_witness" if not reasons else "all_lane_witness_withheld",
        "reasons": sorted(set(reasons)), "all_no_link_control": not normalized,
        "all_unrequired_edges_left_unconnected": True, "flags": _flags(),
        "semantics": "one_full_scope_all_lane_completion_for_entire_multi_transition_request"}, BUNDLE_PREFIX)
    snapshot = owned._freeze(result)
    signature = hmac.digest(_SECRET, owned._encoded([id(session), result["record_id"], id(snapshot)]), "sha256")
    _BUNDLES[session][result["record_id"]] = snapshot, signature
    _issued(session)
    return result


def _registered_bundle(session, bundle_id):
    if type(bundle_id) is not str or bundle_id not in _BUNDLES[session]:
        raise ValueError("native_session_registered_bundle_required")
    snapshot, signature = _BUNDLES[session][bundle_id]
    expected = hmac.digest(_SECRET, owned._encoded([id(session), bundle_id, id(snapshot)]), "sha256")
    if not hmac.compare_digest(signature, expected):
        raise ValueError("registered_bundle_owned_state_changed")
    return owned._thaw(snapshot)


def _selector(state, value):
    if type(value) is not dict or set(value) != {"origin_ids", "key_id", "transition_assumptions"}:
        raise ValueError("closed_complete_native_selector_required")
    ids, key_id, transitions = (value[n] for n in ("origin_ids", "key_id", "transition_assumptions"))
    if type(ids) is not list or not ids or any(type(v) is not str or v not in state.lookups["origins"] for v in ids):
        raise ValueError("original_native_ordered_origin_inventory_required")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_native_origin_in_complete_partition")
    if type(key_id) is not str or key_id not in state.lookups["keys"]:
        raise ValueError("registered_explicit_key_required")
    origins = [owned._thaw(state.lookups["origins"][v]) for v in ids]
    scope = state.data["scope"]
    a, end = span_bounds(owned._thaw(scope["analysis_span"]))
    cursor = a
    for origin in origins:
        lo, hi = span_bounds(origin["span"])
        if lo != cursor or hi <= lo:
            raise ValueError("gapless_positive_ordered_native_partition_required")
        cursor = hi
    if cursor != end:
        raise ValueError("exact_full_analysis_scope_partition_required")
    if type(transitions) is not list or len(transitions) != len(ids) - 1:
        raise ValueError("complete_internal_transition_assumption_vector_required")
    for t in transitions:
        if t is not None and (type(t) is not dict or set(t) != {"family", "quality"}
                or t["family"] not in kernels.FAMILIES or t["quality"] not in ("M", "m")):
            raise ValueError("explicit_supported_transition_or_unassessed_None_required")
    return deepcopy(value), origins, owned._thaw(state.lookups["keys"][key_id])


def _ordinary(scope, source, target, function, bundle):
    """First *actual-witness* pitch change, without skipping an adverse change.

    Shared/tied sound carry is intrinsic. Reattacks need genuine endpoint
    links. No alternative first-change chain is borrowed from another bundle.
    """
    cut = f(target["span"]["start"])
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    links = {a: b for a, b in bundle["materialized_witness_links"]}
    roles = {"leading_tone": function["leading_tone"]}
    if function["seventh"] is not None:
        roles["seventh"] = function["seventh"]
    rows = []
    for role, critical in roles.items():
        occurrences = []
        for sound in scope["sound_facts"]:
            lo, hi = span_bounds(sound["span"])
            if not lo < cut <= hi or critical is None or kernels._pitch_key(sound["pitch"]) != kernels._pitch_key(critical):
                continue
            route = [sound]
            route_links, endpoint = [], None
            current = sound
            while current["sound_ref"] in links:
                nxt = sounds[links[current["sound_ref"]]]
                route_links.append([current["sound_ref"], nxt["sound_ref"]])
                route.append(nxt)
                if kernels._pitch_key(nxt["pitch"], True) != kernels._pitch_key(sound["pitch"], True):
                    endpoint = nxt
                    break
                current = nxt
            blockers = [b for s in route for b in kernels._source_blockers(s)]
            if endpoint is None:
                blockers.append("first_changed_endpoint_not_linked_in_this_complete_witness")
            else:
                motion = kernels._move(sound, endpoint)
                if kernels._overlap(endpoint["span"], target["span"]) is None or kernels._state(endpoint, target) != "member":
                    blockers.append("first_changed_endpoint_not_member_inside_target_slot")
                correct = (motion is not None and ((role == "leading_tone" and motion["diatonic_steps"] == 1
                    and f(motion["semitones"]) == 1
                    and kernels._pitch_key(endpoint["pitch"]) == kernels._pitch_key(function["derived_target_root"]))
                    or (role == "seventh" and motion["diatonic_steps"] == -1 and f(motion["semitones"]) in (-1, -2))))
                if not correct:
                    blockers.append("ordinary_role_first_change_motion_not_satisfied")
            occurrences.append({"source_sound_ref": sound["sound_ref"], "source_note_refs": deepcopy(sound["source_note_refs"]),
                "route_sound_refs": [s["sound_ref"] for s in route],
                "full_sound_spans": [deepcopy(s["span"]) for s in route], "actual_required_links": route_links,
                "endpoint_sound_ref": None if endpoint is None else endpoint["sound_ref"],
                "timing": "direct" if hi == cut else "held_past_declared_cut",
                "satisfied_under_this_bundle": not blockers and bundle["status"] == "complete_all_lane_witness",
                "blockers": sorted(set(blockers))})
        rows.append({"role": role, "critical_pitch": deepcopy(critical), "occurrences": occurrences,
            "satisfied_under_this_bundle": any(o["satisfied_under_this_bundle"] for o in occurrences),
            "all_doublings_individually_required": False})
    return {"strategy": "ordinary_role_existential_under_one_registered_complete_bundle",
        "role_assessments": rows, "whole_ordinary_template_satisfied": bool(rows) and all(r["satisfied_under_this_bundle"] for r in rows),
        "same_complete_bundle": bundle["status"] == "complete_all_lane_witness",
        "universal_rule_or_harmony_confirmation": False}


def _account(scope, profiles):
    bysound = defaultdict(list)
    totals = {name: Fraction() for name in catalog.STATES}
    for profile in profiles:
        for name, value in profile["note_time_quarters"].items():
            totals[name] += f(value)
        for row in profile["rows"]:
            bysound[row["sound_ref"]].append(deepcopy(row["observed_span"]))
    raw = sum((f(s["observed_span"]["end"]) - f(s["observed_span"]["start"])
               for s in scope["sound_facts"] if not s["point"]), Fraction())
    total = sum(totals.values(), Fraction())
    if total != raw:
        raise ValueError("complete_partition_raw_note_time_not_conserved")
    return {"raw_total_note_time_quarters": q(raw), "slot_total_note_time_quarters": q(total),
        "raw_state_note_time_quarters": {k: q(v) for k, v in totals.items()},
        "per_sound_slot_intersections": dict(sorted(bysound.items())),
        "raw_time_conserved": True, "NCT_credited_note_time_quarters": None,
        "conditional_NCT_evaluation": "not_integrated_into_native_lattice_yet",
        "provider_ornament_flags_are_not_explanation_credit": True}


def _path(scope, lattice, selection, origins, key, bundle):
    identity = _seal({"version": VERSION, "lattice_ref": _ref(lattice), "scope_ref": _ref(scope),
        "analysis_span": deepcopy(scope["analysis_span"]), "origin_refs": [_ref(o) for o in origins],
        "partition": [deepcopy(o["span"]) for o in origins], "key_ref": _ref(key),
        "bundle_ref": _ref(bundle), "transition_assumptions": deepcopy(selection["transition_assumptions"]),
        "selected": None, "rank": None, "confidence": None}, "fmiltuple_")
    profiles = [kernels._profile(scope, o) for o in origins]
    boundaries, transitions = [], []
    probes = {}
    for pos in range(len(origins) + 1):
        when = f(origins[0]["span"]["start"]) if pos == 0 else f(origins[pos - 1]["span"]["end"])
        literal = context._boundary(scope, when)
        before_origin = None if pos == 0 else origins[pos - 1]
        arrival_origin = None if pos == len(origins) else origins[pos]
        before = context._extreme_inventory(scope, literal, "before", before_origin, key, probes)
        at = context._extreme_inventory(scope, literal, "at", arrival_origin, key, probes)
        pairs = [context._transition_pair(scope, bundle, a, b, when)
                 for a in before["rows"] for b in at["rows"]
                 if a["raw_lane"] is not None and a["raw_lane"] == b["raw_lane"]]
        function_context = None
        if 0 < pos < len(origins):
            assumption = selection["transition_assumptions"][pos - 1]
            if assumption is None:
                function_context = _seal({"version": VERSION, "status": "unassessed_no_declared_ordinary_transition",
                    "joint_conditional_functional_evidence": None, "function_shape": None, "ordinary_strategy": None,
                    "bundle_ref": _ref(bundle), "source_origin_ref": _ref(before_origin), "target_origin_ref": _ref(arrival_origin),
                    "selected": None, "flags": _flags()}, "fmilfunction_")
            else:
                shape = kernels._function(scope, before_origin, arrival_origin, key["segments"][0],
                                          assumption["family"], assumption["quality"])
                ordinary = _ordinary(scope, before_origin, arrival_origin, shape, bundle)
                axes_profiles = [context._profile_axes(profiles[p], origins[p]) for p in (pos - 1, pos)]
                lows = [r for inv in (before, at) for r in inv["rows"] if "lowest" in r["extreme_axes"]]
                bass_guard = None if not lows else all(not r["source_guards"]["blockers"] for r in lows)
                known = context._key_context(key)["key_coordinate_prerequisites_available"]
                coordinate = None if not known else shape["key_projection"]["target_coordinate"] is not None
                axes = {"source_shape_compatible": shape["shape_compatible"],
                    "target_triad_core_shape_compatible": shape["target_shape_compatible"],
                    "function_shape_prerequisites_available": shape["status"] == "conditional_function_shape",
                    "known_explicit_key_coordinate": coordinate,
                    "same_registered_complete_all_raw_lane_bundle": bundle["status"] == "complete_all_lane_witness",
                    "guarded_pooled_literal_core_present": context._truth([a["guarded_pooled_core_present"] for a in axes_profiles]),
                    "observed_lowest_source_guards_passed": bass_guard,
                    "actual_ordinary_role_rows_available": True,
                    "whole_explicit_ordinary_template_satisfied": ordinary["whole_ordinary_template_satisfied"]}
                truth = context._truth(list(axes.values()))
                function_context = _seal({"version": VERSION, "status": "conditional_functional_relation_under_explicit_key_and_same_completion" if truth is True else "withheld_or_unassessed_conditional_function",
                    "joint_conditional_functional_evidence": truth, "function_shape": shape, "ordinary_strategy": ordinary,
                    "prerequisite_axes": axes, "profile_literal_evidence": axes_profiles, "bundle_ref": _ref(bundle),
                    "source_origin_ref": _ref(before_origin), "target_origin_ref": _ref(arrival_origin),
                    "selected": None, "flags": _flags()}, "fmilfunction_")
            transitions.append(function_context)
        cadence = context._cadence_axes(before_origin, arrival_origin, key, before, at,
                                        function_context, pairs, 0 < pos < len(origins))
        boundaries.append({"boundary_time": q(when), "literal_observation": literal,
            "before_extremes": before, "arrival_extremes": at, "same_raw_lane_transitions": pairs,
            "cadence_prerequisites": cadence, "function_context_ref": None if function_context is None else _ref(function_context)})
    functions = [{"slot": n, "source_origin_ref": _ref(o), "terminal": n + 1 == len(origins),
        "alternatives": [kernels._function(scope, o, origins[n + 1] if n + 1 < len(origins) else None,
                    key["segments"][0], family, quality) for family in kernels.FAMILIES for quality in ("M", "m")]}
        for n, o in enumerate(origins)]
    declared = [r["joint_conditional_functional_evidence"] for r in transitions
                if r["function_shape"] is not None]
    return _seal({"version": VERSION, "logical_tuple": identity, "lattice_ref": _ref(lattice),
        "scope_ref": _ref(scope), "partition": [deepcopy(o["span"]) for o in origins],
        "origin_refs": [_ref(o) for o in origins], "key_ref": _ref(key), "bundle_ref": _ref(bundle),
        "profiles": profiles, "whole_path_account": _account(scope, profiles), "function_shapes": functions,
        "transition_contexts": transitions, "boundaries": boundaries,
        "all_declared_functional_prerequisites_under_same_bundle": context._truth(declared) if declared else None,
        "undeclared_transition_count": sum(a is None for a in selection["transition_assumptions"]),
        "all_transitions_functionally_assessed": all(a is not None for a in selection["transition_assumptions"]),
        "status": "computed_complete_native_path_not_selected", "selected": None, "rank": None, "confidence": None,
        "flags": _flags()}, "fmilpath_")


def _query_plan(scope, selections):
    """Source-size-aware logical planning, not wall-time/RSS certification.

    Boundary snapshots are currently recomputed per path, whereas terminal
    probes are shared only inside a path.  Charge those actual occurrences;
    do not claim cross-path cache savings the implementation does not make.
    Ordinary chain visits and profile intersections use a whole-request upper
    bound.  Planning inspects facts only, never restores large source snapshots.
    """
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    n = len(sounds)
    literal = scope["literal_observation"]
    projection = literal["core_projection"]
    source_inventory = len(literal["slots"]) + sum(len(rows) for rows in projection.values()
                                                   if isinstance(rows, list))
    snapshot_inventory = n + source_inventory
    boundary_cache = {}
    boundary_count = pair_count = extreme_count = probe_count = declared_count = 0
    slots = sum(len(origins) for _, origins, _ in selections)
    for selection, origins, _ in selections:
        times = [f(origins[0]["span"]["start"]), *(f(o["span"]["end"]) for o in origins)]
        probes = set()
        for when in times:
            if when not in boundary_cache:
                boundary_cache[when] = context._boundary_indices(scope, when)
            _, _, before, at = boundary_cache[when]
            old_ids, new_ids = context._extreme_ids(before), context._extreme_ids(at)
            pair_count += sum(sounds[a]["lane"] is not None and sounds[a]["lane"] == sounds[b]["lane"]
                              for a in old_ids for b in new_ids)
            extreme_count += len(old_ids) + len(new_ids)
            probes.update((sid, when) for sid in [*old_ids, *new_ids])
        probe_count += len(probes)
        boundary_count += len(times)
        declared_count += sum(t is not None for t in selection["transition_assumptions"])
    profile_bound = slots * (2 * n * n + n)
    route_bound = declared_count * 2 * n * (n + 1)
    snapshot_visits = (boundary_count + probe_count + extreme_count) * snapshot_inventory
    # _transition_pair rebuilds the fact map and inspects its lane entry/links.
    pair_visits = pair_count * (n + len(scope["graphs"]) + 1)
    shape_rows = slots * 10
    work = profile_bound + route_bound + snapshot_visits + pair_visits + shape_rows + 2 * extreme_count
    return {"planned_boundary_observations": boundary_count,
        "planned_same_raw_lane_pairs": pair_count,
        "planned_extreme_row_occurrences": extreme_count,
        "planned_terminal_probe_occurrences": probe_count,
        "unique_literal_coordinate_times": [q(t) for t in sorted(boundary_cache)],
        "source_snapshot_inventory_items": snapshot_inventory,
        "planned_function_shape_rows": shape_rows,
        "profile_intersection_visit_upper_bound": profile_bound,
        "ordinary_actual_route_visit_upper_bound": route_bound,
        "source_snapshot_visit_units": snapshot_visits,
        "same_lane_pair_visit_units": pair_visits,
        "planned_query_work": work,
        "semantics": "source_inventory_logical_visits_and_route_bounds_not_CPU_RSS_or_bytes"}


def compare_prepared(session, selectors, bundle_id, *, max_hypotheses=64, max_slots=64, query_work_budget=200000):
    for name, value in dict(max_hypotheses=max_hypotheses, max_slots=max_slots, query_work_budget=query_work_budget).items():
        _integer(value, name)
    state = _issued(session)
    if type(selectors) is not list:
        raise ValueError("explicit_complete_native_selector_list_required")
    selectors_before = digest(selectors)
    scope, lattice = (owned._thaw(state.data[n]) for n in ("scope", "lattice"))
    bundle = _registered_bundle(session, bundle_id)
    selections = [_selector(state, s) for s in selectors]
    if len({digest(s[0]) for s in selections}) != len(selections):
        raise ValueError("duplicate_native_selector")
    slots = sum(len(s[1]) for s in selections)
    plan = _query_plan(scope, selections)
    work = plan["planned_query_work"]
    reasons = []
    if lattice["status"] != "ready_native_interval_lattice":
        reasons.append("complete_native_lattice_unavailable")
    if len(selectors) > max_hypotheses:
        reasons.append("whole_selector_request_exceeds_budget_no_prefix")
    if any(len(s[1]) > max_slots for s in selections):
        reasons.append("whole_slot_request_exceeds_budget_no_prefix")
    if work > query_work_budget:
        reasons.append("whole_query_work_request_exceeds_budget_no_prefix")
    paths = [] if reasons else [_path(scope, lattice, selection, origins, key, bundle)
                              for selection, origins, key in selections]
    raw_counts = [f(p["whole_path_account"]["raw_total_note_time_quarters"]) for p in paths]
    if len(set(raw_counts)) > 1:
        raise ValueError("different_raw_time_between_native_competitors")
    result = _seal({"version": VERSION, "contract": _contract(), "scope_ref": _ref(scope),
        "lattice_ref": _ref(lattice), "bundle_ref": _ref(bundle), "bundle_status": bundle["status"],
        "analysis_span": deepcopy(scope["analysis_span"]), "logical_universe": deepcopy(lattice["universe"]),
        "selectors": deepcopy(selectors), "paths": paths,
        "query_plan": plan,
        "resource_limits": dict(max_hypotheses=max_hypotheses, max_slots=max_slots, query_work_budget=query_work_budget),
        "summary": {"planned_selectors": len(selectors), "computed_selectors": len(paths),
            "planned_slot_occurrences": slots, "planned_query_work": work,
            "computed_internal_transitions": sum(len(p["transition_contexts"]) for p in paths),
            "raw_time_equal_between_competitors": bool(paths),
            "all_logical_paths_evaluated": False},
        "status": "whole_comparison_hold" if reasons else "computed_native_multi_slot_comparison_not_selected",
        "reasons": sorted(set(reasons)), "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "limitations": ["No winner or likelihood follows from counts or raw membership.",
            "Optional local/boundary NCT credits and every doubling obligation are not integrated yet.",
            "Local key, structural voices, consonance, phrase closure and performed timing remain unestablished.",
            "Only this registered completion and explicit selectors are assessed; omitted paths are unassessed."]}, COMPARISON_PREFIX)
    _issued(session)
    if selectors_before != digest(selectors):
        raise ValueError("native_selector_request_changed_during_comparison")
    return result


def compare(ir, scope, lattice, selectors, bundle, **caps):
    for name, value in caps.items():
        if name not in ("max_hypotheses", "max_slots", "query_work_budget"):
            raise ValueError("unknown_native_comparison_limit")
        _integer(value, name)
    session = prepare_lattice(ir, scope, lattice)
    kernels._check(bundle, BUNDLE_PREFIX)
    fresh = compile_bundle_prepared(session, bundle["required_links"], **bundle["resource_limits"])
    if not owned._same(bundle, fresh):
        raise ValueError("foreign_stale_or_modified_native_completion")
    return compare_prepared(session, selectors, fresh["record_id"], **caps)


def validate_comparison(ir, scope, lattice, selectors, bundle, result, **caps):
    kernels._check(result, COMPARISON_PREFIX)
    if not owned._same(result, compare(ir, scope, lattice, selectors, bundle, **caps)):
        raise ValueError("stale_foreign_or_modified_native_comparison")
    return True
