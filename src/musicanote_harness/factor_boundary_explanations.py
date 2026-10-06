"""Conditional roles across authentic adjacent indexed slots, never NCT verdicts.

Every edge-dependent role needs its entire carry/resolution chain in ONE actual
all-raw-lane completion. A genuinely held sound needs no invented self-link.
Only the affected literal nonmember interval is credited; raw time is unchanged.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import hmac
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_temporal_explanations as temporal
from . import factor_grounded_relations as grounded
from . import factor_indexed_hypotheses as indexed
from . import factor_expanded_hypotheses as frozen
from . import harmony_factorized_voice_paths as geometry
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-boundary-explanations-0.1.0"
PREFIX = "fmbe_"
GEOMETRY_PREFIX = "fmbegeom_"
PARTITION_PREFIX = "fmbepart_"
RELATION_PREFIX = "fmberel_"
BUNDLE_PREFIX = "fmbebundle_"
QUERY_PREFIX = "fmbequery_"
CAPS = ("max_geometry_candidates", "max_chain_edges", "max_membership_relations", "max_new_bundles", "query_work_budget")
DEFAULTS = dict(zip(CAPS, (4096, 16, 65536, 4096, 100000)))
CATEGORIES = ("source_guarded_member", "conditional_boundary_explained_nonmember",
    "unexplained_nonmember_under_this_completion", "unassessed_nonmember",
    "membership_unknown", "source_or_hypothesis_unsupported")
_INPUTS = WeakKeyDictionary()
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    return {**temporal._flags(), "boundary_nct_confirmed": False,
        "functional_delayed_obligations_evaluated": False, "local_plus_boundary_accounts_combined": False,
        "intrinsic_carry_requires_fabricated_self_link": False}


def _contract():
    return {"version": VERSION, "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "temporal_contract": temporal._contract()}


def _seal(body, prefix): return frozen._seal(body, prefix)
def _ref(record): return frozen._ref(record)
def _caps(caps):
    for name in CAPS: indexed._integer(caps[name], name)


class _PreparedInputs:
    __slots__ = ("__weakref__",)


class _PreparedExplanations:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    data: object
    lookups: object
    contract_sha256: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, indexed._encoded([id(handle), id(state), id(state.data),
        id(state.lookups), state.contract_sha256]), "sha256")


def _issued(handle, registry, cls):
    if type(handle) is not cls or handle not in registry:
        raise ValueError("internally_issued_boundary_session_required")
    state = registry[handle]
    if (type(state) is not _State or not isinstance(state.data, MappingProxyType)
            or not isinstance(state.lookups, MappingProxyType)
            or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _auth(handle, state))):
        raise ValueError("boundary_session_current_contract_or_owned_state_changed")
    return state


def _issue(cls, registry, data, lookups):
    handle = cls()
    state = _State(indexed._freeze(data), indexed._freeze(lookups), digest(_contract()), b"")
    object.__setattr__(state, "authentication", _auth(handle, state))
    registry[handle] = state
    return handle


def prepare_inputs_prepared(temporal_input_session, temporal_record):
    """Only an authentic issued temporal supplier can avoid duplicate parent replay."""
    state = temporal._issued(temporal_input_session, temporal._INPUTS, temporal._PreparedInputs)
    before, contract = digest(temporal_record), _contract()
    owned_record = deepcopy(temporal_record)
    temporal._header(owned_record); frozen._check(owned_record, temporal.PREFIX)
    fresh = temporal.build_explanations_prepared(temporal_input_session, **owned_record["resource_limits"])
    if not indexed._same(fresh, owned_record): raise ValueError("boundary_requires_exact_current_temporal_parent")
    data = indexed._thaw(state.data)
    data["temporal"] = owned_record
    temporal._issued(temporal_input_session, temporal._INPUTS, temporal._PreparedInputs)
    if before != digest(temporal_record) or not indexed._same(contract, _contract()):
        raise ValueError("boundary_inputs_or_code_changed_during_owned_parent_replay")
    return _issue(_PreparedInputs, _INPUTS, data, {})


def prepare_inputs(ir, scope, hypotheses, index, relations, grounding, temporal_record):
    before, contract = digest([ir, scope, hypotheses, index, relations, grounding, temporal_record]), _contract()
    result = prepare_inputs_prepared(temporal.prepare_inputs(ir, scope, hypotheses, index, relations, grounding), temporal_record)
    if before != digest([ir, scope, hypotheses, index, relations, grounding, temporal_record]) or not indexed._same(contract, _contract()):
        raise ValueError("boundary_inputs_or_code_changed_during_owned_parent_replay")
    return result


def _pair_groups(index):
    origins = defaultdict(lambda: defaultdict(list))
    for row in index["variant_inventory"]:
        origins[row["catalog_id"]][row["profile_ref"]["record_id"]].append(row["variant_id"])
    result = []
    for group in index["path_groups"]:
        slots = group["slots"]
        if len(slots) != 2: continue
        if f(slots[0]["span"]["end"]) != f(slots[1]["span"]["start"]):
            raise ValueError("original_indexed_adjacent_slots_must_touch")
        incidence = [[{"descriptor_id": did, "origin_variant_ids": ids, "origin_multiplicity": len(ids)}
            for did, ids in origins[slot["catalog_id"]].items()] for slot in slots]
        result.append({"group_id": group["group_id"], "indexed_group_id": group["indexed_group_id"],
            "original_group": deepcopy(group), "slots": deepcopy(slots),
            "pair_span": temporal._span(f(slots[0]["span"]["start"]), f(slots[1]["span"]["end"])),
            "cut": deepcopy(slots[0]["span"]["end"]), "descriptor_origin_incidence": incidence,
            "descriptor_origin_inventory_complete": all(sum(r["origin_multiplicity"] for r in incidence[i]) == len(s["variant_ids"])
                for i, s in enumerate(slots)), "key_count": len(index["keys"]),
            "logical_path_count": group["logical_path_count"], "logical_tuple_count": group["logical_tuple_count"],
            "logical_function_count": group["logical_function_count"]})
    return result


def _same(a, b):
    key = frozen._pitch_key(a["pitch"], True)
    return key is not None and key == frozen._pitch_key(b["pitch"], True)


def _ordinary_down(a, b):
    move = frozen._move(a, b)
    return (move is not None and move["diatonic_steps"] == -1 and f(move["semitones"]) in (-1, -2)
        and frozen._integer_pitch(a["pitch"]) and frozen._integer_pitch(b["pitch"]))


def _graph_tables(scope):
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    result = []
    for graph in sorted(scope["graphs"], key=lambda g: g["lane"]):
        outgoing = defaultdict(set)
        for factor in graph["factors"]:
            for src in factor["source_refs"]: outgoing[src].update(factor["target_refs"])
        outgoing = {sid: sorted(targets) for sid, targets in outgoing.items()}
        result.append((graph, outgoing))
    return sounds, result


def _leaf_plan(start, outgoing, sounds):
    """DP pre-count all same-written-register carries to first change/terminal."""
    pitch = frozen._pitch_key(sounds[start]["pitch"], True)
    memo = {}
    pending = [(start, False)]
    while pending:
        sid, complete = pending.pop()
        if sid in memo: continue
        successors = outgoing.get(sid, ())
        carries = [t for t in successors if pitch is not None and frozen._pitch_key(sounds[t]["pitch"], True) == pitch]
        if not complete and any(t not in memo for t in carries):
            pending.append((sid, True)); pending.extend((t, False) for t in carries if t not in memo); continue
        leaves = sum(memo[t][0] if t in carries else 1 for t in successors) if successors else 1
        depth = max((1 + (memo[t][1] if t in carries else 0) for t in successors), default=0)
        memo[sid] = (leaves, depth)
    return memo[start]


def _leaves(prefix, outgoing, sounds):
    pitch = frozen._pitch_key(sounds[prefix[0]]["pitch"], True)
    pending = [tuple(prefix)]
    while pending:
        chain = pending.pop(); successors = outgoing.get(chain[-1], ())
        if not successors:
            yield chain, False; continue
        for target in reversed(successors):
            extended = (*chain, target)
            if pitch is not None and frozen._pitch_key(sounds[target]["pitch"], True) == pitch:
                pending.append(extended)
            else: yield extended, True


def _geometry_record(scope, pair, graph, family, chain, changed, sounds):
    involved = [sounds[sid] for sid in chain]
    cut = f(pair["cut"]); a, b = span_bounds(pair["pair_span"])
    source = involved[0]; sa, sb = span_bounds(source["span"])
    codes = ["source:" + s["sound_ref"] + ":" + reason for s in involved for reason in temporal._guard_codes(s)]
    codes.extend(reason for s in involved for reason in frozen._source_blockers(s))
    if not a <= sa < cut: codes.append("preparation_attack_not_in_left_slot")
    if not all(a <= x < y <= b for x, y in (span_bounds(s["span"]) for s in involved)):
        codes.append("all_involved_full_sound_spans_not_inside_pair_envelope")
    anticipation = family.startswith("anticipation")
    if family == "anticipation_reattack" and not _same(involved[0], involved[1]):
        codes.append("anticipation_reattack_not_identical_written_register")
    if not anticipation:
        if not changed: codes.append("first_changed_resolution_not_observed_terminal_carry")
        elif not _ordinary_down(involved[-2], involved[-1]): codes.append("first_changed_resolution_not_downward_ordinary_spelled_step")
        if changed and not cut <= f(involved[-1]["span"]["start"]) < b:
            codes.append("resolution_attack_not_in_right_half_open_slot")
    required = [[x, y] for x, y in zip(chain, chain[1:])]
    carries = involved if anticipation or not changed else involved[:-1]
    explained = []
    for s in ([source] if anticipation else carries):
        x, y = span_bounds(s["span"])
        lo, hi = (max(a, x), min(cut, y)) if anticipation else (max(cut, x), min(b, y))
        if lo < hi: explained.append({"sound_ref": s["sound_ref"], "span": temporal._span(lo, hi)})
    left_refs = [source["sound_ref"]]
    right_refs = ([involved[-1]["sound_ref"]] if anticipation else [s["sound_ref"] for s in carries if f(s["span"]["end"]) > cut]
        + ([involved[-1]["sound_ref"]] if changed else []))
    expected = ["member"] if anticipation else ["nonmember_not_confirmed_nct"] * (len(right_refs) - int(changed)) + (["member"] if changed else [])
    return _seal({"version": VERSION, "scope_ref": _ref(scope), "group_id": pair["group_id"],
        "indexed_group_id": pair["indexed_group_id"], "pair_span": deepcopy(pair["pair_span"]), "cut": deepcopy(pair["cut"]),
        "slot_catalog_ids": [s["catalog_id"] for s in pair["slots"]], "graph_ref": _ref(graph), "raw_lane": deepcopy(graph["lane"]),
        "family": family, "involved_sound_refs": list(chain), "source_note_refs": [nid for s in involved for nid in s["source_note_refs"]],
        "full_sound_spans": [deepcopy(s["span"]) for s in involved], "preparation_attack_time": deepcopy(source["span"]["start"]),
        "actually_held_same_sound": family in ("anticipation_held", "prepared_held_suspension"),
        "preparation_sound_crosses_boundary": sa < cut < sb,
        "whole_chain_is_one_sounding_event": len(chain) == 1,
        "edge_kinds": ["same_written_register_rearticulation_not_tie" if _same(x, y) else "first_changed_endpoint"
            for x, y in zip(involved, involved[1:])],
        "same_pitch_rearticulation_is_not_tie_or_sustain": family in ("anticipation_reattack", "rearticulated_suspension_like"),
        "initial_boundary_presentation": "one_physically_held_sound" if sa < cut < sb else "distinct_sound_rearticulation_at_cut",
        "held_and_rearticulation_booleans_describe_initial_cut_not_whole_chain": True,
        "first_changed_endpoint_observed": changed, "chain_edges": len(required), "required_links": required,
        "left_membership_sound_refs": left_refs, "right_membership_sound_refs": right_refs,
        "left_expected_states": ["nonmember_not_confirmed_nct" if anticipation else "member"], "right_expected_states": expected,
        "explained_side": "left" if anticipation else "right", "explained_items": explained,
        "motions": [frozen._move(x, y) for x, y in zip(involved, involved[1:])],
        "status": "conditional_boundary_geometry" if not codes else "withheld_boundary_geometry", "blockers": sorted(set(codes)),
        "accent": "unassessed", "consonance": "unassessed", "complete_NCT_classification": "unassessed",
        "delayed_functional_obligations": "unassessed", "flags": _flags()}, GEOMETRY_PREFIX)


def _geometries(scope, pairs, cap, max_edges):
    sounds, graphs = _graph_tables(scope)
    count = 0; depth = 0; unknown = bool(pairs) and any(g["status"] != "ready" for g, _ in graphs)
    def specifications():
        for pair in pairs:
            cut = f(pair["cut"])
            for graph, outgoing in graphs:
                if graph["status"] != "ready": continue
                for sid in sorted(s["sounding_event_id"] for s in graph["events"]):
                    if sid not in sounds: raise ValueError("boundary_graph_sound_not_in_source_inventory")
                    a, b = span_bounds(sounds[sid]["span"])
                    if a < cut < b: yield pair, graph, outgoing, "held", (sid,)
                    elif a < cut == b:
                        for target in outgoing.get(sid, ()):
                            yield pair, graph, outgoing, "reattack" if _same(sounds[sid], sounds[target]) else "different_cut_pitch", (sid, target)
    plans = {}
    for pair, graph, outgoing, kind, prefix in specifications():
        count += 1
        if kind != "different_cut_pitch":
            key = (graph["record_id"], prefix[-1])
            if key not in plans: plans[key] = _leaf_plan(prefix[-1], outgoing, sounds)
            leaves, edges = plans[key]
            count += leaves; depth = max(depth, len(prefix) - 1 + edges)
        else: depth = max(depth, 1)
    held = unknown or count > cap or depth > max_edges
    rows = []
    if not held:
        for pair, graph, outgoing, kind, prefix in specifications():
            family = "anticipation_held" if kind == "held" else "anticipation_reattack"
            rows.append(_geometry_record(scope, pair, graph, family, prefix, False, sounds))
            if kind != "different_cut_pitch":
                for chain, changed in _leaves(prefix, outgoing, sounds):
                    rows.append(_geometry_record(scope, pair, graph,
                        "prepared_held_suspension" if kind == "held" else "rearticulated_suspension_like", chain, changed, sounds))
        if len(rows) != count: raise ValueError("boundary_geometry_leaf_denominator_loss")
    return rows, None if unknown else count, count, depth, held


def _partition_sides(geom, pair, descriptors, sounds):
        sides = []
        for position, side in enumerate(("left", "right")):
            groups = {}
            refs = geom[side + "_membership_sound_refs"]
            expected = geom[side + "_expected_states"]
            for row in pair["descriptor_origin_incidence"][position]:
                descriptor = descriptors[row["descriptor_id"]]; semantic = descriptor["semantic_input"]
                states = tuple(frozen._state(sounds[sid], semantic) for sid in refs)
                key = (states, tuple(semantic["blockers"]))
                if key not in groups:
                    groups[key] = {"version": VERSION, "geometry_ref": _ref(geom), "group_id": pair["group_id"],
                        "side": side, "slot_index": position, "catalog_id": pair["slots"][position]["catalog_id"],
                        "span": deepcopy(pair["slots"][position]["span"]), "membership_sound_refs": list(refs),
                        "membership_states": list(states), "expected_states": list(expected), "hypothesis_blockers": list(semantic["blockers"]),
                        "descriptor_origin_incidence": [], "flags": _flags()}
                groups[key]["descriptor_origin_incidence"].append(deepcopy(row))
            side_rows = []
            for body in groups.values():
                body["descriptor_count"] = len(body["descriptor_origin_incidence"])
                body["origin_count"] = sum(r["origin_multiplicity"] for r in body["descriptor_origin_incidence"])
                side_rows.append(body)
            sides.append(side_rows)
        return sides


def _relation_state(geom, left, right):
    codes = list(geom["blockers"])
    for part in (left, right): codes.extend("hypothesis:" + code for code in part["hypothesis_blockers"])
    unknown = any("spelling_unresolved" in part["membership_states"] for part in (left, right))
    if unknown: codes.append("boundary_membership_unknown")
    elif any(part["membership_states"] != part["expected_states"] for part in (left, right)):
        codes.append("boundary_membership_prerequisites_not_met")
    status = "conditional_boundary_shape" if not codes else "unknown_boundary_membership" if unknown else "withheld_boundary_prerequisites"
    return status, sorted(set(codes))


def _membership(scope, index, pairs, geometries, ready, cap):
    descriptors = {d["record_id"]: d for d in index["profile_inventory"]}
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    by_group = {p["group_id"]: p for p in pairs}
    partitions = []; relations = []; counts = Counter(); weighted = Counter()
    if not ready: return [], [], None, counts, weighted, True
    planned = 0
    # Pre-count a geometry's finite partitions, then discard them. No sealed
    # partition/rectangle prefix is allocated when the whole inventory is held.
    for geom in geometries:
        pair = by_group[geom["group_id"]]
        sides = _partition_sides(geom, pair, descriptors, sounds)
        planned += len(sides[0]) * len(sides[1])
        for left in sides[0]:
            for right in sides[1]:
                status, _ = _relation_state(geom, left, right)
                n = left["descriptor_count"] * right["descriptor_count"]
                origin_n = left["origin_count"] * right["origin_count"] * pair["key_count"]
                counts[status] += n; weighted[status] += origin_n
        expected = len(pair["descriptor_origin_incidence"][0]) * len(pair["descriptor_origin_incidence"][1])
        if sum(p["descriptor_count"] for p in sides[0]) * sum(p["descriptor_count"] for p in sides[1]) != expected:
            raise ValueError("boundary_partition_descriptor_product_loss")
    if planned > cap: return [], [], planned, counts, weighted, True
    for geom in geometries:
        pair = by_group[geom["group_id"]]
        sides = [[_seal(body, PARTITION_PREFIX) for body in side]
            for side in _partition_sides(geom, pair, descriptors, sounds)]
        partitions.extend(sides[0]); partitions.extend(sides[1])
        for left in sides[0]:
            for right in sides[1]:
                status, codes = _relation_state(geom, left, right)
                n = left["descriptor_count"] * right["descriptor_count"]
                origin_n = left["origin_count"] * right["origin_count"] * pair["key_count"]
                relations.append(_seal({"version": VERSION, "group_id": pair["group_id"], "geometry_ref": _ref(geom),
                    "left_partition_ref": _ref(left), "right_partition_ref": _ref(right), "descriptor_pair_count": n,
                    "origin_pair_key_count": origin_n, "status": status, "blockers": codes, "flags": _flags()}, RELATION_PREFIX))
    if len(relations) != planned: raise ValueError("boundary_rectangle_denominator_loss")
    return partitions, relations, planned, counts, weighted, False


def _universe(scope, index, grounding, temporal_record):
    return _seal({"version": VERSION, "scope_ref": _ref(scope), "index_ref": _ref(index),
        "grounding_universe_ref": _ref(grounding["logical_universe"]), "temporal_universe_ref": _ref(temporal_record["logical_universe"]),
        "logical_paths": grounding["summary"]["logical_paths"], "logical_path_key_tuples": grounding["summary"]["logical_path_key_tuples"],
        "logical_function_rows": grounding["summary"]["logical_function_rows"],
        "all_original_competitors_preserved": True, "all_logical_paths_materialized_or_evaluated": False,
        "flags": _flags()}, "fmbeuniverse_")


def _new_bundle(scope, index, grounding, universe, required, work):
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    by_lane = defaultdict(list); reasons = []; entries = []
    for src, dst in required:
        if src not in sounds or dst not in sounds or sounds[src]["lane"] != sounds[dst]["lane"]:
            raise ValueError("boundary_request_has_foreign_or_cross_lane_edge")
        by_lane[tuple(sounds[src]["lane"])].append([src, dst])
    for graph in sorted(scope["graphs"], key=lambda g: g["lane"]):
        result = geometry.query(graph, required_links=by_lane.get(tuple(graph["lane"]), []), work_budget=work)
        witness = geometry.materialize_witness(graph, result) if result["status"] == "exact_count" and result["possible_assignments"] != "0" else None
        entries.append({"lane": deepcopy(graph["lane"]), "graph_ref": _ref(graph), "query": result,
            "witness": witness, "status": "complete" if witness is not None else "lane_withheld"})
        if witness is None:
            reasons.extend("lane_query:" + reason for reason in result["reasons"])
            if not result["reasons"]:
                reasons.append("lane_query:certified_zero_assignments" if result["possible_assignments"] == "0"
                    else "lane_query:completion_not_available")
    covered = sorted(e["lane"] for e in entries)
    expected = sorted([[r["part_id"], r["voice_id"]] for r in scope["raw_lanes"]])
    if covered != expected: reasons.append("complete_raw_lane_graph_inventory_missing")
    links = sorted({tuple(pair) for e in entries if e["witness"] is not None for pair in e["witness"]["assignment"]["links"]})
    if not reasons and links != list(required): raise ValueError("boundary_whole_chain_witness_required_links_mismatch")
    condition = ("possible" if not reasons else "impossible" if any(e["query"]["status"] in
        ("exact_count", "unsatisfiable_constraints") and e["query"]["possible_assignments"] == "0" for e in entries) else "unknown")
    return _seal({"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]), "index_ref": _ref(index),
        "grounding_ref": _ref(grounding), "symbolic_universe_ref": _ref(universe),
        "comparison_key_refs": [_ref(k) for k in grounding["keys"]],
        "comparison_representation": "full_original_symbolic_universe_not_empty_or_fabricated_paths",
        "required_links": [list(p) for p in required], "materialized_witness_links": [list(p) for p in links],
        "entries": entries, "covered_lanes": covered, "status": "complete_all_lane_witness" if not reasons else "all_lane_witness_withheld",
        "geometry_condition_status": condition, "reasons": sorted(set(reasons)), "query_work_budget": work,
        "all_unrequired_edges_left_unconnected": True, "all_no_link_control": not required,
        "boundary_completion_semantics": "fresh_entire_required_carry_and_resolution_chain_not_union_of_independent_witnesses",
        "flags": _flags()}, BUNDLE_PREFIX)


def _body(scope, index, relations, grounding, temporal_record, caps):
    pairs = _pair_groups(index)
    geometries, planned_geometry, known_geometry, max_depth, geometry_hold = _geometries(scope, pairs,
        caps["max_geometry_candidates"], caps["max_chain_edges"])
    empty_pair_product = not pairs or all(p["logical_path_count"] == 0 for p in pairs)
    upstream_ready = empty_pair_product or (grounding["summary"]["literal_profiles_complete"] is True
        and all(p["descriptor_origin_inventory_complete"] for p in pairs))
    partitions, rels, planned_rel, counts, weighted, relation_hold = _membership(scope, index, pairs, geometries,
        empty_pair_product or (upstream_ready and not geometry_hold), caps["max_membership_relations"])
    universe = _universe(scope, index, grounding, temporal_record)
    geoms = {g["record_id"]: g for g in geometries}
    requests = {}; new_bundles = []; request_rows = []
    for row in rels:
        if row["status"] == "conditional_boundary_shape":
            geom = geoms[row["geometry_ref"]["record_id"]]
            required = tuple(sorted(tuple(p) for p in geom["required_links"]))
            requests.setdefault(required, set()).add(geom["record_id"])
    planned_new = None if relation_hold else len(requests)
    bundle_hold = len(requests) > caps["max_new_bundles"]
    for required, ids in requests.items():
        bundle = None if bundle_hold else _new_bundle(scope, index, grounding, universe, required, caps["query_work_budget"])
        if bundle is not None: new_bundles.append(bundle)
        request_rows.append(_seal({"version": VERSION, "required_links": [list(p) for p in required],
            "geometry_refs": [_ref(geoms[gid]) for gid in sorted(ids)], "symbolic_universe_ref": _ref(universe),
            "bundle_ref": None if bundle is None else _ref(bundle),
            "status": "whole_new_boundary_completion_inventory_budget_hold" if bundle is None else bundle["geometry_condition_status"],
            "flags": _flags()}, "fmbebundlereq_"))
    inherited = deepcopy(temporal_record["inherited_bundle_inventory"] + temporal_record["bundle_inventory"])
    incidence = []
    for bundle in inherited + new_bundles:
        links = temporal._links(bundle)
        supported = [r for r in rels if r["status"] == "conditional_boundary_shape"
            and bundle["status"] == "complete_all_lane_witness"
            and all(tuple(p) in links for p in geoms[r["geometry_ref"]["record_id"]]["required_links"])]
        incidence.append({"bundle_ref": _ref(bundle), "same_complete_all_lane_bundle": bundle["status"] == "complete_all_lane_witness",
            "supported_relation_refs": [_ref(r) for r in supported], "represented_relation_count": len(rels),
            "assessed_relation_count": 0 if relation_hold or bundle["status"] != "complete_all_lane_witness" else len(rels),
            "unassessed_relation_count": len(rels) if relation_hold or bundle["status"] != "complete_all_lane_witness" else 0,
            "conditional_relation_count": len(supported), "intrinsic_held_anticipation_needs_no_self_link": True})
    summary = {"touching_pair_groups": len(pairs), "fullhold_groups_without_boundary": len(index["path_groups"]) - len(pairs),
        "known_origin_variants": len(index["variant_inventory"]), "planned_geometry_candidates": planned_geometry,
        "known_geometry_candidate_subtotal": known_geometry, "materialized_geometry_candidates": len(geometries),
        "max_planned_chain_edges": max_depth, "planned_membership_relations": planned_rel, "materialized_membership_relations": len(rels),
        "materialized_membership_partitions": len(partitions), "known_descriptor_pair_geometry_incidence_subtotal": sum(counts.values()),
        "planned_new_bundles": planned_new, "materialized_new_bundles": len(new_bundles), "inherited_bundles": len(inherited),
        "new_complete_bundles": sum(b["geometry_condition_status"] == "possible" for b in new_bundles),
        "new_impossible_bundles": sum(b["geometry_condition_status"] == "impossible" for b in new_bundles),
        "new_unknown_bundles": sum(b["geometry_condition_status"] == "unknown" for b in new_bundles),
        "actual_bundle_relation_assessments": sum(i["assessed_relation_count"] for i in incidence),
        "conditional_bundle_relation_assessments": sum(i["conditional_relation_count"] for i in incidence),
        **{k: grounding["summary"][k] for k in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups")},
        "pair_accounts_computed": 0, "boundary_queries_computed": 0, "delayed_functional_obligations_computed": 0,
        "local_plus_boundary_combined_accounts_computed": 0, "membership_inventory_complete": not relation_hold}
    for label, status in (("conditional", "conditional_boundary_shape"), ("withheld", "withheld_boundary_prerequisites"), ("unknown", "unknown_boundary_membership")):
        summary[label + "_descriptor_pair_geometry_incidences"] = None if relation_hold else counts[status]
        summary["known_" + label + "_descriptor_pair_geometry_incidence_subtotal"] = counts[status]
        summary[label + "_origin_pair_key_geometry_incidences"] = None if relation_hold else weighted[status]
    reasons = []
    if not upstream_ready: reasons.append("upstream_literal_profiles_or_origin_inventory_not_complete")
    if geometry_hold: reasons.append("whole_geometry_inventory_unknown_or_candidate_or_chain_depth_budget_hold")
    if relation_hold: reasons.append("whole_membership_relation_inventory_unknown_or_budget_hold")
    if bundle_hold: reasons.append("whole_new_boundary_completion_inventory_budget_hold")
    if any(b["status"] != "complete_all_lane_witness" for b in inherited + new_bundles): reasons.append("one_or_more_actual_completions_withheld")
    return {"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]), "analysis_span": deepcopy(scope["analysis_span"]),
        "scope_ref": _ref(scope), "hypotheses_ref": deepcopy(index["hypotheses_ref"]), "index_ref": _ref(index),
        "relations_ref": _ref(relations), "grounding_ref": _ref(grounding), "temporal_ref": _ref(temporal_record), "logical_universe": universe,
        "origin_inventory": deepcopy(grounding["origin_inventory"]), "catalog_inventory": deepcopy(grounding["catalog_inventory"]),
        "keys": deepcopy(grounding["keys"]), "source_inventory": deepcopy(grounding["source_inventory"]),
        "descriptor_inventory": deepcopy(index["profile_inventory"]), "path_groups": deepcopy(index["path_groups"]), "pair_groups": pairs,
        "geometry_inventory": geometries, "membership_partition_inventory": partitions, "membership_relation_inventory": rels,
        "inherited_bundle_inventory": inherited, "bundle_requests": request_rows, "bundle_inventory": new_bundles,
        "bundle_relation_incidence": incidence, "parent_summary": deepcopy(relations["summary"]),
        "grounding_summary": deepcopy(grounding["summary"]), "temporal_summary": deepcopy(temporal_record["summary"]),
        "resource_limits": deepcopy(caps), "summary": summary, "status": "boundary_explanations_with_holds" if reasons else "ready_conditional_boundary_explanations",
        "reasons": sorted(set(reasons)), "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "functional_delayed_obligations": "unassessed", "local_plus_boundary_combined_accounting": "unassessed",
        "validation_semantics": "owned_serial_immutable_inputs_authentic_temporal_replay_not_atomic_concurrent_ABA",
        "resource_limit_semantics": "whole_geometry_leaf_and_chain_depth_partition_rectangle_and_new_bundle_caps_no_prefix_not_byte_RSS_lifetime_caps",
        "limits": ["Boundary membership and carry/downward-step shapes are conditional, not complete NCT or harmony.",
            "Preparation attack is in the left slot; all involved full sounding spans are within the original adjacent pair envelope.",
            "Every required carry and resolution edge must coexist in one actual all-raw-lane completion.",
            "A truly held sound persists without a fabricated self-link, including under no-link control.",
            "Credit only intersects the literal affected nonmember clip: anticipation left, suspension right.",
            "Local-plus-boundary union, metric/consonance certification and delayed leading-tone/seventh functional obligations are unassessed."]}


def build_explanations_prepared(input_session, **caps):
    if set(caps) - set(CAPS): raise TypeError("unknown_boundary_limit")
    limits = {**DEFAULTS, **caps}; _caps(limits)
    state = _issued(input_session, _INPUTS, _PreparedInputs); data = indexed._thaw(state.data)
    result = _seal(_body(data["scope"], data["index"], data["relations"], data["grounding"], data["temporal"], limits), PREFIX)
    _issued(input_session, _INPUTS, _PreparedInputs)
    return result


def build_explanations(ir, scope, hypotheses, index, relations, grounding, temporal_record, **caps):
    if set(caps) - set(CAPS): raise TypeError("unknown_boundary_limit")
    _caps({**DEFAULTS, **caps})
    return build_explanations_prepared(prepare_inputs(ir, scope, hypotheses, index, relations, grounding, temporal_record), **caps)


def _header(record):
    indexed._closed(record, {"version", "contract", "binding", "analysis_span", "scope_ref", "hypotheses_ref", "index_ref",
        "relations_ref", "grounding_ref", "temporal_ref", "logical_universe", "origin_inventory", "catalog_inventory", "keys",
        "source_inventory", "descriptor_inventory", "path_groups", "pair_groups", "geometry_inventory", "membership_partition_inventory",
        "membership_relation_inventory", "inherited_bundle_inventory", "bundle_requests", "bundle_inventory", "bundle_relation_incidence",
        "parent_summary", "grounding_summary", "temporal_summary", "resource_limits", "summary", "status", "reasons", "selected", "rank",
        "confidence", "flags", "functional_delayed_obligations", "local_plus_boundary_combined_accounting", "validation_semantics",
        "resource_limit_semantics", "limits", "record_id", "record_sha256"}, "boundary_explanations")
    indexed._closed(record["resource_limits"], set(CAPS), "boundary_resource_limits"); _caps(record["resource_limits"])
    for name in ("origin_inventory", "catalog_inventory", "keys", "source_inventory", "descriptor_inventory", "path_groups", "pair_groups",
        "geometry_inventory", "membership_partition_inventory", "membership_relation_inventory", "inherited_bundle_inventory",
        "bundle_requests", "bundle_inventory", "bundle_relation_incidence", "reasons", "limits"):
        if type(record[name]) is not list: raise ValueError("boundary_inventory_list_required:" + name)


def validate_explanations(ir, scope, hypotheses, index, relations, grounding, temporal_record, record):
    _header(record); frozen._check(record, PREFIX)
    if not indexed._same(record, build_explanations(ir, scope, hypotheses, index, relations, grounding, temporal_record, **record["resource_limits"])):
        raise ValueError("stale_foreign_modified_or_promoting_boundary_explanations")
    return True


def prepare_explanations_prepared(supplier, record):
    _header(record); frozen._check(record, PREFIX)
    _issued(supplier, _INPUTS, _PreparedInputs)
    before, contract = digest(record), _contract(); owned_record = deepcopy(record)
    if not indexed._same(owned_record, build_explanations_prepared(supplier, **owned_record["resource_limits"])):
        raise ValueError("stale_foreign_modified_or_promoting_boundary_explanations")
    data = indexed._thaw(_issued(supplier, _INPUTS, _PreparedInputs).data); data["boundary"] = owned_record
    data["registered_bundles"] = owned_record["inherited_bundle_inventory"] + owned_record["bundle_inventory"]
    lookup = {"groups": {g["group_id"]: i for i, g in enumerate(data["index"]["path_groups"])},
        "pairs": {p["group_id"]: i for i, p in enumerate(owned_record["pair_groups"])},
        "variants": {v["variant_id"]: i for i, v in enumerate(data["index"]["variant_inventory"])},
        "profiles": {p["descriptor_ref"]["record_id"]: i for i, p in enumerate(data["grounding"]["profile_inventory"])},
        "rows": {p["record_id"]: i for i, p in enumerate(data["grounding"]["row_inventory"])},
        "cells": {p["record_id"]: i for i, p in enumerate(data["grounding"]["cell_inventory"])},
        "descriptors": {d["record_id"]: i for i, d in enumerate(data["index"]["profile_inventory"])},
        "bundles": {b["record_id"]: i for i, b in enumerate(data["registered_bundles"])}}
    by_group = defaultdict(list)
    for i, geom in enumerate(owned_record["geometry_inventory"]): by_group[geom["group_id"]].append(i)
    lookup["group_geometries"] = dict(by_group)
    _issued(supplier, _INPUTS, _PreparedInputs)
    if before != digest(record) or not indexed._same(contract, _contract()):
        raise ValueError("boundary_inputs_or_code_changed_during_owned_session_preparation")
    return _issue(_PreparedExplanations, _SESSIONS, data, lookup)


def prepare_explanations(ir, scope, hypotheses, index, relations, grounding, temporal_record, record):
    caller = [ir, scope, hypotheses, index, relations, grounding, temporal_record, record]
    before, contract = digest(caller), _contract()
    result = prepare_explanations_prepared(prepare_inputs(ir, scope, hypotheses, index, relations, grounding, temporal_record), record)
    if before != digest(caller) or not indexed._same(contract, _contract()):
        raise ValueError("boundary_inputs_or_code_changed_during_owned_session_preparation")
    return result


def _profile(state, variant_id):
    data = state.data
    if variant_id not in state.lookups["variants"]: return None, None
    origin = data["index"]["variant_inventory"][state.lookups["variants"][variant_id]]
    did = origin["profile_ref"]["record_id"]
    if did not in state.lookups["profiles"]: return None, origin
    profile = indexed._thaw(data["grounding"]["profile_inventory"][state.lookups["profiles"][did]])
    rows = {rid: indexed._thaw(data["grounding"]["row_inventory"][state.lookups["rows"][rid]]) for rid in profile["row_ids"]}
    cells = {cid: indexed._thaw(data["grounding"]["cell_inventory"][state.lookups["cells"][cid]]) for cid in profile["cell_ids"]}
    return grounded._restore_profile(profile, indexed._thaw(origin["variant"]), rows, cells), origin


def _side_account(profile, descriptor, sounds, explained, assessed):
    totals = {k: Fraction() for k in CATEGORIES}; intervals = defaultdict(list)
    for item in explained: intervals[item["sound_ref"]].append(item["span"])
    unions = {sid: temporal._union(spans) for sid, spans in intervals.items()}
    credited = []
    for row in profile["rows"]:
        sid = row["sound_ref"]; a, b = span_bounds(row["observed_span"]); duration = b - a
        if descriptor["semantic_input"]["blockers"] or temporal._guard_codes(sounds[sid]) or frozen._source_blockers(sounds[sid]):
            totals["source_or_hypothesis_unsupported"] += duration
        elif row["state"] == "member": totals["source_guarded_member"] += duration
        elif row["state"] == "spelling_unresolved": totals["membership_unknown"] += duration
        elif not assessed: totals["unassessed_nonmember"] += duration
        else:
            clipped = temporal._union([temporal._span(max(a, x), min(b, y)) for x, y in (span_bounds(s) for s in unions.get(sid, ())) if max(a, x) < min(b, y)])
            credit = temporal._duration(clipped)
            if clipped: credited.append({"sound_ref": sid, "spans": clipped})
            totals["conditional_boundary_explained_nonmember"] += credit
            totals["unexplained_nonmember_under_this_completion"] += duration - credit
    if sum(totals.values(), Fraction()) != f(profile["total_note_time_quarters"]): raise ValueError("boundary_side_note_time_loss")
    return {"raw_note_time": deepcopy(profile["note_time_quarters"]), "total_note_time": deepcopy(profile["total_note_time_quarters"]),
        "note_time": {k: q(v) for k, v in totals.items()}, "credited_intervals_by_sound": credited,
        "conditional_explanation_note_time": q(totals["conditional_boundary_explained_nonmember"]) if assessed else None,
        "local_plus_boundary_combined_accounting": "unassessed"}


def query_pair_prepared(session, group_id, left_variant_id, right_variant_id, bundle_id):
    state = _issued(session, _SESSIONS, _PreparedExplanations); data = state.data; record = data["boundary"]
    if type(group_id) is not str or group_id not in state.lookups["groups"]: raise ValueError("explicit_original_indexed_group_required")
    group = data["index"]["path_groups"][state.lookups["groups"][group_id]]
    if group_id not in state.lookups["pairs"]: raise ValueError("touching_original_two_slot_group_required_no_fullhold_boundary")
    variants = (left_variant_id, right_variant_id)
    if any(type(v) is not str or v not in slot["variant_ids"] for v, slot in zip(variants, group["slots"])):
        raise ValueError("ordered_original_slot_variant_ids_required")
    if left_variant_id == right_variant_id: raise ValueError("duplicate_boundary_origin_not_allowed")
    no_bundle = bundle_id is None and not state.lookups["bundles"]
    if not no_bundle and (type(bundle_id) is not str or bundle_id not in state.lookups["bundles"]): raise ValueError("actual_registered_same_universe_boundary_bundle_required")
    bundle = None if no_bundle else data["registered_bundles"][state.lookups["bundles"][bundle_id]]
    restored = [_profile(state, v) for v in variants]; profiles = [p for p, _ in restored]; origins = [o for _, o in restored]
    known_work = len(state.lookups["group_geometries"].get(group_id, ())) + sum(len(p["rows"]) for p in profiles if p is not None)
    work = known_work if all(p is not None for p in profiles) and record["summary"]["membership_inventory_complete"] else None
    hold = work is None or work > record["resource_limits"]["query_work_budget"]
    assessed = not hold and record["summary"]["membership_inventory_complete"] and bundle is not None and bundle["status"] == "complete_all_lane_witness"
    sounds = {s["sound_ref"]: indexed._thaw(s) for s in data["scope"]["sound_facts"]}; links = set() if bundle is None else temporal._links(bundle)
    supported = []; explanation = [[], []]; rows = []
    if not hold:
        for i in state.lookups["group_geometries"].get(group_id, ()):
            geom = record["geometry_inventory"][i]; codes = list(geom["blockers"]); states = []
            for position, side in enumerate(("left", "right")):
                origin = origins[position]; descriptor = indexed._thaw(data["index"]["profile_inventory"][state.lookups["descriptors"][origin["profile_ref"]["record_id"]]])
                actual = [frozen._state(sounds[sid], descriptor["semantic_input"]) for sid in geom[side + "_membership_sound_refs"]]
                states.append(actual); codes.extend("hypothesis:" + c for c in descriptor["semantic_input"]["blockers"])
                if "spelling_unresolved" in actual: codes.append("boundary_membership_unknown")
                elif actual != list(geom[side + "_expected_states"]): codes.append("boundary_membership_prerequisites_not_met")
            satisfied = assessed and not codes and all(tuple(p) in links for p in geom["required_links"])
            if satisfied:
                supported.append(_ref(geom)); explanation[0 if geom["explained_side"] == "left" else 1].extend(indexed._thaw(geom["explained_items"]))
            rows.append({"geometry_ref": _ref(geom), "membership_states": states, "blockers": sorted(set(codes)),
                "status": "conditional_boundary_under_this_same_completion" if satisfied else "unassessed_boundary_axis" if not assessed else
                    "withheld_boundary_prerequisites" if codes else "not_satisfied_under_this_completion_not_global_absence"})
    accounts = []
    if not hold:
        for position, (profile, origin) in enumerate(restored):
            descriptor = indexed._thaw(data["index"]["profile_inventory"][state.lookups["descriptors"][origin["profile_ref"]["record_id"]]])
            accounts.append(_side_account(profile, descriptor, sounds, explanation[position], assessed))
    result = _seal({"version": VERSION, "contract": _contract(), "explanations_ref": _ref(record),
        "scope_ref": indexed._thaw(record["scope_ref"]), "index_ref": indexed._thaw(record["index_ref"]),
        "symbolic_universe_ref": _ref(record["logical_universe"]), "group_id": group_id,
        "origin_variant_ids": list(variants), "origin_refs": [None if o is None else _ref(o["variant"]) for o in origins],
        "bundle_ref": None if bundle is None else _ref(bundle), "same_complete_all_lane_bundle": bundle is not None and bundle["status"] == "complete_all_lane_witness",
        "profiles": profiles, "boundary_accounts": accounts if not hold else None, "geometry_assessments": rows if not hold else None,
        "supported_geometry_refs": supported if not hold else None, "planned_query_work_items": work,
        "known_stored_query_work_subtotal": known_work,
        "status": "whole_boundary_query_source_or_work_inventory_hold" if hold else "computed_conditional_boundary_axes_not_selected",
        "local_plus_boundary_combined_accounting": "unassessed", "functional_delayed_obligations": "unassessed",
        "selected": None, "rank": None, "confidence": None, "flags": _flags()}, QUERY_PREFIX)
    _issued(session, _SESSIONS, _PreparedExplanations)
    return result


def query_pair(ir, scope, hypotheses, index, relations, grounding, temporal_record, record,
               group_id, left_variant_id, right_variant_id, bundle_id):
    return query_pair_prepared(prepare_explanations(ir, scope, hypotheses, index, relations, grounding, temporal_record, record),
        group_id, left_variant_id, right_variant_id, bundle_id)


def validate_pair_query(ir, scope, hypotheses, index, relations, grounding, temporal_record, record,
                        group_id, left_variant_id, right_variant_id, bundle_id, result):
    frozen._check(result, QUERY_PREFIX)
    if not indexed._same(result, query_pair(ir, scope, hypotheses, index, relations, grounding, temporal_record, record,
            group_id, left_variant_id, right_variant_id, bundle_id)):
        raise ValueError("stale_foreign_modified_boundary_pair_query")
    return True
