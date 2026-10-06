"""Explicit ordinary direct/delayed strategies, not universal voice-leading law.

Physical occurrences, rule assumptions and one-completion compatibility remain
separate. Raw memberships and all original functional competitors survive.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from itertools import product
import hmac
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_boundary_explanations as boundary
from . import factor_temporal_explanations as temporal
from . import factor_grounded_relations as grounded
from . import factor_expanded_hypotheses as frozen
from . import factor_indexed_hypotheses as indexed
from . import harmony_factorized_voice_paths as geometry
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-delayed-obligations-0.1.0"
PREFIX = "fmdo_"
ROUTE_PREFIX = "fmdoroute_"
OCCURRENCE_PREFIX = "fmdoocc_"
ROLE_PREFIX = "fmdorole_"
KERNEL_PREFIX = "fmdokernel_"
PLAN_PREFIX = "fmdoplan_"
BUNDLE_PREFIX = "fmdobundle_"
QUERY_PREFIX = "fmdoquery_"
COMPILE_PREFIX = "fmdocompile_"
CAPS = ("max_route_candidates", "max_chain_edges", "max_obligation_kernels", "max_role_options", "max_joint_options", "max_new_bundles", "query_work_budget")
DEFAULTS = dict(zip(CAPS, (4096, 16, 65536, 65536, 65536, 65536, 100000)))
SPEC_FIELDS = ("group_id", "source_catalog_id", "target_catalog_id", "source_type_ref", "target_type_ref",
    "source_profile_ref", "target_profile_ref", "source_representative_variant_ref", "target_representative_variant_ref",
    "source_variant_ids", "target_variant_ids", "shape_kernel_ref", "family", "quality", "origin_multiplicity", "key_multiplicity", "weighted_function_rows")
CATEGORIES = ("source_guarded_member", "conditional_combined_explained_nonmember", "unexplained_nonmember_under_this_completion",
    "unassessed_nonmember", "membership_unknown", "source_or_hypothesis_unsupported")
_INPUTS = WeakKeyDictionary()
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    return {**boundary._flags(), "ordinary_strategy_is_universal_prohibition": False,
        "existential_proof_resolves_all_doublings": False, "all_optional_NCT_completions_evaluated": False,
        "delayed_resolution_confirmed": False, "pooled_target_core_certifies_harmony": False}


def _contract():
    return {"version": VERSION, "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "boundary_contract": boundary._contract()}


def _seal(body, prefix): return frozen._seal(body, prefix)
def _ref(record): return frozen._ref(record)
def _caps(values):
    for name in CAPS: indexed._integer(values[name], name)


class _PreparedInputs:
    __slots__ = ("__weakref__",)


class _PreparedObligations:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _State:
    data: object
    lookups: object
    contract_sha256: str
    authentication: bytes


def _auth(handle, state):
    return hmac.digest(_SECRET, indexed._encoded([id(handle), id(state), id(state.data), id(state.lookups), state.contract_sha256]), "sha256")


def _issued(handle, registry, cls):
    if type(handle) is not cls or handle not in registry: raise ValueError("internally_issued_delayed_session_required")
    state = registry[handle]
    if (type(state) is not _State or not isinstance(state.data, MappingProxyType) or not isinstance(state.lookups, MappingProxyType)
            or state.contract_sha256 != digest(_contract()) or not hmac.compare_digest(state.authentication, _auth(handle, state))):
        raise ValueError("delayed_session_current_contract_or_owned_state_changed")
    return state


def _issue(cls, registry, data, lookups):
    handle = cls(); state = _State(indexed._freeze(data), indexed._freeze(lookups), digest(_contract()), b"")
    object.__setattr__(state, "authentication", _auth(handle, state)); registry[handle] = state
    return handle


def prepare_inputs_prepared(boundary_input_session, boundary_record):
    state = boundary._issued(boundary_input_session, boundary._INPUTS, boundary._PreparedInputs)
    before, contract = digest(boundary_record), _contract(); owned_record = deepcopy(boundary_record)
    boundary._header(owned_record); frozen._check(owned_record, boundary.PREFIX)
    if not indexed._same(owned_record, boundary.build_explanations_prepared(boundary_input_session, **owned_record["resource_limits"])):
        raise ValueError("delayed_requires_exact_current_boundary_parent")
    data = indexed._thaw(state.data); data["boundary"] = owned_record
    boundary._issued(boundary_input_session, boundary._INPUTS, boundary._PreparedInputs)
    if before != digest(boundary_record) or not indexed._same(contract, _contract()):
        raise ValueError("delayed_inputs_or_code_changed_during_owned_parent_replay")
    return _issue(_PreparedInputs, _INPUTS, data, {})


def prepare_inputs(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record):
    caller = [ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record]
    before, contract = digest(caller), _contract()
    result = prepare_inputs_prepared(boundary.prepare_inputs(*caller[:7]), boundary_record)
    if before != digest(caller) or not indexed._same(contract, _contract()): raise ValueError("delayed_parent_inputs_changed")
    return result


def _routes(scope, pairs, caps):
    sounds, graphs = boundary._graph_tables(scope); by_lane = {tuple(g["lane"]): (g, outgoing) for g, outgoing in graphs}
    definitions = []; count = 0; depth = 0; unknown = bool(pairs) and scope["context_sound_inventory_complete"] is not True
    for pair in pairs:
        cut = f(pair["cut"])
        for sound in sorted(scope["sound_facts"], key=lambda s: s["sound_ref"]):
            a, b = f(sound["span"]["start"]), f(sound["span"]["end"])
            if not a < cut <= b: continue
            graph, outgoing = by_lane.get(tuple(sound["lane"] or ()), (None, {}))
            ready = graph is not None and graph["status"] == "ready" and all(e["sounding_event_id"] in sounds for e in graph["events"])
            leaves, edges = boundary._leaf_plan(sound["sound_ref"], outgoing, sounds) if ready else (0, 0)
            count += leaves; depth = max(depth, edges); unknown |= not ready
            definitions.append((pair, sound, graph, outgoing, leaves, ready))
    hold = unknown or count > caps["max_route_candidates"] or depth > caps["max_chain_edges"]
    occurrences = []; routes = []
    for pair, source, graph, outgoing, leaves, ready in definitions:
        occurrence = _seal({"version": VERSION, "group_id": pair["group_id"], "pair_span": deepcopy(pair["pair_span"]),
            "cut": deepcopy(pair["cut"]), "source_sound_ref": source["sound_ref"], "source_snapshot": deepcopy(source),
            "graph_ref": None if graph is None else _ref(graph), "raw_lane": deepcopy(source["lane"]),
            "physically_active_left_limit": True, "planned_routes": leaves if ready else None,
            "source_guard_blockers": sorted(set(temporal._guard_codes(source) + frozen._source_blockers(source))),
            "obligation_assignment": "not_assigned_by_physical_occurrence_alone", "flags": _flags()}, OCCURRENCE_PREFIX)
        occurrences.append(occurrence)
        if hold: continue
        for chain, changed in boundary._leaves((source["sound_ref"],), outgoing, sounds):
            rows = [sounds[sid] for sid in chain]; a, b = span_bounds(pair["pair_span"])
            codes = ["source:" + s["sound_ref"] + ":" + c for s in rows for c in temporal._guard_codes(s)]
            codes.extend(c for s in rows for c in frozen._source_blockers(s))
            if not all(a <= x < y <= b for x, y in (span_bounds(s["span"]) for s in rows)):
                codes.append("all_full_sound_spans_not_inside_original_pair")
            target = rows[-1] if changed else None
            if target is not None and not f(pair["cut"]) <= f(target["span"]["start"]) < b:
                codes.append("first_changed_attack_not_in_right_half_open_slot")
            routes.append(_seal({"version": VERSION, "scope_ref": _ref(scope), "occurrence_ref": _ref(occurrence),
                "group_id": pair["group_id"], "pair_span": deepcopy(pair["pair_span"]), "cut": deepcopy(pair["cut"]),
                "involved_sound_refs": list(chain), "source_sound_ref": chain[0], "raw_lane": deepcopy(source["lane"]),
                "full_sound_spans": [deepcopy(s["span"]) for s in rows], "required_links": [list(e) for e in zip(chain, chain[1:])],
                "chain_edges": len(chain) - 1, "first_changed_endpoint_observed": changed,
                "endpoint_sound_ref": None if target is None else target["sound_ref"],
                "resolution_motion": None if target is None else frozen._move(rows[-2], target),
                "source_physically_held_at_cut": f(source["span"]["start"]) < f(pair["cut"]) < f(source["span"]["end"]),
                "timing": "terminal_no_changed_endpoint" if not changed else "direct_at_cut" if len(chain) == 2 and f(target["span"]["start"]) == f(pair["cut"]) else "same_pitch_delayed",
                "blockers": sorted(set(codes)), "status": "neutral_first_change_route" if not codes else "withheld_neutral_route",
                "flags": _flags()}, ROUTE_PREFIX))
    if not hold and len(routes) != count: raise ValueError("neutral_route_leaf_denominator_loss")
    return occurrences, routes, None if unknown else count, count, depth, hold


def _role_definition(scope, spec, template, role, occurrences, routes, descriptors):
    source = descriptors[spec["source_profile_ref"]["record_id"]]["semantic_input"]
    target = descriptors[spec["target_profile_ref"]["record_id"]]["semantic_input"]
    critical = template["leading_tone" if role == "leading_tone" else "seventh"]
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    matched = []; unknown = []; not_match = 0
    for occurrence in occurrences:
        if occurrence["group_id"] != spec["group_id"]: continue
        key = frozen._pitch_key(occurrence["source_snapshot"]["pitch"])
        if key is None: unknown.append(_ref(occurrence))
        elif key == frozen._pitch_key(critical): matched.append(occurrence)
        else: not_match += 1
    ids = {o["record_id"] for o in matched}; options = []
    for route in routes:
        if route["occurrence_ref"]["record_id"] not in ids: continue
        codes = list(route["blockers"]); left = sounds[route["source_sound_ref"]]
        if frozen._state(left, source) != "member": codes.append("critical_source_not_literal_source_member")
        endpoint = sounds.get(route["endpoint_sound_ref"]); state = None if endpoint is None else frozen._state(endpoint, target)
        move = route["resolution_motion"]; ordinary = False
        if endpoint is None: codes.append("first_changed_endpoint_not_observed_terminal")
        else:
            if state != "member": codes.append("actual_endpoint_membership_unknown" if state == "spelling_unresolved" else "actual_endpoint_not_literal_target_member")
            if move is not None:
                ordinary = (move["diatonic_steps"] == 1 and f(move["semitones"]) == 1
                    and frozen._pitch_key(endpoint["pitch"]) == frozen._pitch_key(template["derived_target_root"])) if role == "leading_tone" else (move["diatonic_steps"] == -1 and f(move["semitones"]) in (-1, -2))
            if not ordinary: codes.append("ordinary_" + role + "_strategy_motion_not_matched")
        options.append({"route_ref": _ref(route), "occurrence_ref": deepcopy(route["occurrence_ref"]),
            "source_sound_ref": route["source_sound_ref"], "endpoint_membership": state,
            "endpoint_in_derived_triad_core": None if endpoint is None or frozen._pitch_key(endpoint["pitch"]) is None else frozen._pitch_key(endpoint["pitch"]) in {frozen._pitch_key(p) for p in template["derived_target_members"]},
            "qualified": not codes, "blockers": sorted(set(codes))})
    uncertain = bool(unknown) or any(_guard_uncertain(o["blockers"]) for o in options)
    return {"version": VERSION, "group_id": spec["group_id"], "source_profile_ref": deepcopy(spec["source_profile_ref"]),
        "target_profile_ref": deepcopy(spec["target_profile_ref"]), "role": role, "critical_pitch": deepcopy(critical),
        "derived_target_root": deepcopy(template["derived_target_root"]), "matching_occurrence_refs": [_ref(o) for o in matched],
        "unknown_pitch_occurrence_refs": unknown, "known_nonmatching_occurrence_count": not_match, "qualified_route_inventory_uncertain": uncertain, "options": options,
        "strategy_semantics": "OR_occurrences_and_routes_for_this_role_not_all_doublings", "flags": _flags()}


def _cut_audit(spec, profiles, cells, descriptors, sounds):
    left = profiles.get(spec["source_profile_ref"]["record_id"]); right = profiles.get(spec["target_profile_ref"]["record_id"])
    def complete_cell(cell, did):
        semantic = descriptors[did]["semantic_input"]; members = semantic["members"]
        eligible = {frozen._pitch_key(sounds[sid]["pitch"]) for sid in cell["sound_refs"] if not temporal._guard_codes(sounds[sid]) and not frozen._source_blockers(sounds[sid])}
        return {"full_source_guard_missing_spellings": None if members is None else [deepcopy(p) for p in members if frozen._pitch_key(p) not in eligible],
            "full_bass_source_guards_passed": None if not cell["bass_refs"] else all(not temporal._guard_codes(sounds[sid]) and not frozen._source_blockers(sounds[sid]) for sid in cell["bass_refs"])}
    source_cell = None if left is None or not left["cell_ids"] else cells[left["cell_ids"][-1]]
    target_cell = None if right is None or not right["cell_ids"] else cells[right["cell_ids"][0]]
    return {"source_cut_cell": None if left is None or not left["cell_ids"] else deepcopy(cells[left["cell_ids"][-1]]),
        "target_cut_cell": None if right is None or not right["cell_ids"] else deepcopy(cells[right["cell_ids"][0]]),
        "source_cut_full_guard_audit": None if source_cell is None else complete_cell(source_cell, spec["source_profile_ref"]["record_id"]),
        "target_cut_full_guard_audit": None if target_cell is None else complete_cell(target_cell, spec["target_profile_ref"]["record_id"]),
        "right_eligible_complete_literal_core_spans": None if right is None else temporal._union([cells[c]["span"] for c in right["cell_ids"]
            if cells[c]["sound_refs"] and cells[c]["source_guard_missing_spellings"] == []]),
        "right_fully_source_guarded_complete_literal_core_spans": None if right is None else temporal._union([cells[c]["span"] for c in right["cell_ids"]
            if cells[c]["sound_refs"] and complete_cell(cells[c], spec["target_profile_ref"]["record_id"])["full_source_guard_missing_spellings"] == []]),
        "guard_basis": "raw_frozen_cells_preserved_separately_from_all_clock_pitch_attack_eligibility_point_grace_lane_guards",
        "boundary_core_is_separate_from_ordinary_motion_strategy": True, "pooled_members_certify_harmony": False}


def _guard_uncertain(codes):
    return any(c.startswith("source:") or c.startswith("source_") or c.startswith("ordinary_motion_pitch_not_supported") for c in codes)


def _universe(data):
    return _seal({"version": VERSION, "scope_ref": _ref(data["scope"]), "index_ref": _ref(data["index"]),
        "boundary_universe_ref": _ref(data["boundary"]["logical_universe"]),
        **{k: data["grounding"]["summary"][k] for k in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups")},
        "all_original_functional_complements_preserved": True, "all_optional_NCT_completions_evaluated": False,
        "flags": _flags()}, "fmdouniverse_")


def _bundle(data, universe, required, work):
    scope = data["scope"]; sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    by_lane = defaultdict(list); entries = []; reasons = []
    for src, dst in required:
        if src not in sounds or dst not in sounds or sounds[src]["lane"] != sounds[dst]["lane"]: raise ValueError("delayed_required_edge_foreign_or_cross_lane")
        by_lane[tuple(sounds[src]["lane"])].append([src, dst])
    for graph in sorted(scope["graphs"], key=lambda g: g["lane"]):
        result = geometry.query(graph, required_links=by_lane.get(tuple(graph["lane"]), []), work_budget=work)
        witness = geometry.materialize_witness(graph, result) if result["status"] == "exact_count" and result["possible_assignments"] != "0" else None
        entries.append({"lane": deepcopy(graph["lane"]), "graph_ref": _ref(graph), "query": result, "witness": witness})
        if witness is None: reasons.extend(result["reasons"] or ["certified_zero_assignments" if result["possible_assignments"] == "0" else "completion_unknown"])
    covered = sorted(e["lane"] for e in entries)
    if covered != sorted([[r["part_id"], r["voice_id"]] for r in scope["raw_lanes"]]): reasons.append("complete_raw_lane_inventory_missing")
    links = sorted({tuple(edge) for e in entries if e["witness"] is not None for edge in e["witness"]["assignment"]["links"]})
    if not reasons and links != list(required): raise ValueError("whole_delayed_chain_actual_links_mismatch")
    condition = "possible" if not reasons else "impossible" if any(e["query"]["status"] in ("exact_count", "unsatisfiable_constraints") and e["query"]["possible_assignments"] == "0" for e in entries) else "unknown"
    return _seal({"version": VERSION, "contract": _contract(), "scope_ref": _ref(scope), "index_ref": _ref(data["index"]),
        "symbolic_universe_ref": _ref(universe), "comparison_key_refs": [_ref(k) for k in data["grounding"]["keys"]],
        "analysis_span": deepcopy(scope["analysis_span"]), "required_links": [list(e) for e in required],
        "materialized_witness_links": [list(e) for e in links], "entries": entries, "covered_lanes": covered,
        "status": "complete_all_lane_witness" if not reasons else "all_lane_witness_withheld", "geometry_condition_status": condition,
        "reasons": sorted(set(reasons)), "all_no_link_control": not required, "all_unrequired_edges_left_unconnected": True,
        "query_work_budget": work, "flags": _flags()}, BUNDLE_PREFIX)


def _required(route_ids, routes):
    return tuple(sorted({tuple(e) for rid in route_ids for e in routes[rid]["required_links"]}))


def _body(data, caps):
    scope, index, grounding = data["scope"], data["index"], data["grounding"]
    pairs = data["boundary"]["pair_groups"]
    occurrences, routes, planned_routes, known_routes, max_depth, route_hold = _routes(scope, pairs, caps)
    route_map = {r["record_id"]: r for r in routes}
    descriptors = {d["record_id"]: d for d in index["profile_inventory"]}
    source_sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    templates = {k["record_id"]: k["source_template"] for k in data["relations"]["kernels"]}
    parents = grounding["motion_kernel_inventory"]
    specs = [{k: deepcopy(p[k]) for k in SPEC_FIELDS} for p in parents]
    profile_table = {p["descriptor_ref"]["record_id"]: p for p in grounding["profile_inventory"]}
    cell_table = {c["record_id"]: c["value"] for c in grounding["cell_inventory"]}
    nonempty_pair_universe = any(p["logical_path_count"] is None or p["logical_path_count"] > 0 for p in pairs)
    unknown_plan = nonempty_pair_universe and (grounding["summary"]["unknown_supplier_catalogs"] != 0 or index["status"] == "whole_index_budget_hold" or grounding["summary"]["planned_motion_kernels"] is None)
    kernel_hold = unknown_plan or (bool(specs) and (len(specs) > caps["max_obligation_kernels"] or grounding["summary"]["literal_profiles_complete"] is not True))
    definitions = {}; assignments = []; option_count = 0
    occurrence_groups = defaultdict(list); route_occurrences = Counter()
    for o in occurrences: occurrence_groups[o["group_id"]].append(o)
    for r in routes: route_occurrences[r["occurrence_ref"]["record_id"]] += 1
    if not route_hold and not kernel_hold:
        for spec in specs:
            template = templates[spec["shape_kernel_ref"]["record_id"]]; ids = []
            for role in ("leading_tone", "seventh"):
                if template[role] is None: continue
                signature = digest([spec["group_id"], spec["source_profile_ref"], spec["target_profile_ref"], role, template[role], template["derived_target_root"], template["derived_target_members"]])
                if signature not in definitions:
                    option_count += sum(route_occurrences[o["record_id"]] for o in occurrence_groups[spec["group_id"]] if frozen._pitch_key(o["source_snapshot"]["pitch"]) == frozen._pitch_key(template[role]))
                    definitions[signature] = (spec, template, role)
                ids.append(signature)
            assignments.append(ids)
    role_source_plan_unknown = kernel_hold or (bool(specs) and route_hold)
    role_hold = role_source_plan_unknown or option_count > caps["max_role_options"]
    roles = [] if role_hold else [_seal(_role_definition(scope, spec, template, role, occurrences, routes, descriptors), ROLE_PREFIX) for spec, template, role in definitions.values()]
    role_by_signature = dict(zip(definitions, roles)); role_map = {r["record_id"]: r for r in roles}
    plan_definitions = {}; kernel_plans = []; joint_count = 0
    if not role_hold:
        for ids in assignments:
            role_ids = tuple(role_by_signature[s]["record_id"] for s in ids)
            if role_ids not in plan_definitions:
                choices = [[o["route_ref"]["record_id"] for o in role_map[rid]["options"] if o["qualified"]] for rid in role_ids]
                n = 1 if choices else 0
                for choice in choices: n *= len(choice)
                joint_count += n
                plan_definitions[role_ids] = {"version": VERSION, "role_option_refs": [_ref(role_map[r]) for r in role_ids],
                    "qualified_route_choices": choices, "planned_joint_options": n,
                    "known_false_required_role": any(not choice and not role_map[r]["qualified_route_inventory_uncertain"] for r, choice in zip(role_ids, choices)),
                    "source_role_inventory_uncertain": any(role_map[r]["qualified_route_inventory_uncertain"] for r in role_ids), "strategy": "ordinary_role_existential", "flags": _flags()}
            kernel_plans.append(role_ids)
    joint_hold = role_hold or joint_count > caps["max_joint_options"]
    required_sets = {}
    if not joint_hold:
        for definition in plan_definitions.values():
            for choices in product(*definition["qualified_route_choices"]):
                required_sets.setdefault(_required(choices, route_map), None)
    bundle_hold = joint_hold or len(required_sets) > caps["max_new_bundles"]
    universe = _universe(data)
    if not bundle_hold:
        for required in required_sets: required_sets[required] = _bundle(data, universe, required, caps["query_work_budget"])
    bundles = [b for b in required_sets.values() if b is not None]
    plans = []; plan_map = {}
    if not joint_hold:
        for key, definition in plan_definitions.items():
            branches = []; unknown_support = (bundle_hold or definition["source_role_inventory_uncertain"]) and not definition["known_false_required_role"]; supported = 0
            for choices in product(*definition["qualified_route_choices"]):
                required = _required(choices, route_map); bundle = required_sets[required]
                status = "whole_bundle_inventory_hold" if bundle is None else bundle["geometry_condition_status"]
                supported += status == "possible"; unknown_support |= status in ("unknown", "whole_bundle_inventory_hold")
                branches.append({"route_refs": [_ref(route_map[r]) for r in choices], "required_links": [list(e) for e in required],
                    "bundle_ref": None if bundle is None else _ref(bundle), "status": status})
            truth = True if supported else None if unknown_support else False
            plan = _seal({**definition, "branches": branches, "supported_joint_options": None if unknown_support else supported, "ordinary_strategy_truth": truth,
                "known_supported_joint_option_subtotal": supported,
                "status": "conditional_ordinary_strategy_given_harmony_hypothesis" if truth is True else "unassessed_joint_completion" if truth is None else "withheld_this_ordinary_strategy_not_music_error"}, PLAN_PREFIX)
            plans.append(plan); plan_map[key] = plan
    kernels = []; weighted = Counter(); groups = defaultdict(Counter); cut_audits = {}; unknown_support_specs = 0
    for i, (spec, parent) in enumerate(zip(specs, parents)):
        plan = None if joint_hold else plan_map[kernel_plans[i]]
        state = "unassessed" if plan is None or plan["ordinary_strategy_truth"] is None else "conditional" if plan["ordinary_strategy_truth"] else "withheld"
        unknown_support_specs += plan is None or plan["supported_joint_options"] is None
        n = spec["weighted_function_rows"]; weighted[state] += n; groups[spec["group_id"]][state] += n
        if kernel_hold: continue
        pair_key = (spec["source_profile_ref"]["record_id"], spec["target_profile_ref"]["record_id"])
        if pair_key not in cut_audits: cut_audits[pair_key] = _cut_audit(spec, profile_table, cell_table, descriptors, source_sounds)
        kernels.append(_seal({"version": VERSION, **spec, "grounded_direct_kernel_ref": _ref(parent), "old_direct_status": parent["status"],
            "role_option_refs": None if role_hold else [_ref(role_by_signature[s]) for s in assignments[i]],
            "joint_plan_ref": None if plan is None else _ref(plan), "literal_core_and_time_audit": deepcopy(cut_audits[pair_key]),
            "status": state, "flags": _flags()}, KERNEL_PREFIX))
    path_groups = []
    for old in data["relations"]["path_groups"]:
        n = old["logical_function_count"]; weights = groups[old["group_id"]]; subtotal = sum(weights.values())
        eligibility_unknown = len(old["slots"]) == 2 and n != 0 and old["status"] != "ready_function_shape_relations"
        path_groups.append({**deepcopy(old), "delayed_strategy_weights": {"conditional": weights["conditional"], "withheld": weights["withheld"],
            "unassessed": None if n is None else n - weights["conditional"] - weights["withheld"]}, "shape_eligible_weighted_rows": subtotal,
            "known_shape_eligible_weighted_subtotal": subtotal, "shape_eligible_weighted_total": None if eligibility_unknown else subtotal,
            "shape_prerequisite_complement_function_rows": None if n is None or eligibility_unknown else n - subtotal})
    logical = grounding["summary"]["logical_function_rows"]; eligible = sum(s["weighted_function_rows"] for s in specs)
    inherited = deepcopy(data["boundary"]["inherited_bundle_inventory"] + data["boundary"]["bundle_inventory"])
    incidence = []
    for bundle in inherited + bundles:
        links = temporal._links(bundle)
        matched = [_ref(p) for p in plans if bundle["status"] == "complete_all_lane_witness" and any(
            all(tuple(e) in links for e in branch["required_links"]) for branch in p["branches"])]
        incidence.append({"bundle_ref": _ref(bundle), "same_complete_all_lane_bundle": bundle["status"] == "complete_all_lane_witness",
            "compatible_plan_refs": matched, "planned_plan_inventory_complete": not joint_hold})
    summary = {"touching_pair_groups": len(pairs), "known_origin_variants": len(index["variant_inventory"]),
        "planned_physical_occurrences": None if pairs and scope["context_sound_inventory_complete"] is not True else len(occurrences), "known_physical_occurrence_subtotal": len(occurrences), "materialized_physical_occurrences": len(occurrences),
        "planned_route_candidates": planned_routes, "known_route_candidate_subtotal": known_routes, "materialized_route_candidates": len(routes), "max_planned_chain_edges": max_depth,
        "planned_obligation_kernels": None if unknown_plan else len(specs), "materialized_obligation_kernels": 0 if kernel_hold else len(kernels),
        "planned_role_options": None if role_source_plan_unknown else option_count, "materialized_role_options": 0 if role_hold else option_count,
        "planned_joint_options": None if role_hold else joint_count, "materialized_joint_options": 0 if joint_hold else joint_count,
        "supported_joint_option_subtotal": sum(p["known_supported_joint_option_subtotal"] for p in plans), "unknown_joint_support_kernels": None if unknown_plan else unknown_support_specs, "known_unknown_joint_support_kernel_subtotal": unknown_support_specs,
        "planned_new_bundles": None if joint_hold else len(required_sets), "materialized_new_bundles": len(bundles), "inherited_bundles": len(inherited),
        **{"new_" + label + "_bundles": sum(b["geometry_condition_status"] == state for b in bundles) for label, state in (("complete", "possible"), ("impossible", "impossible"), ("unknown", "unknown"))},
        **{k: grounding["summary"][k] for k in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups")},
        "weighted_conditional_ordinary_template_function_rows": weighted["conditional"], "weighted_withheld_ordinary_template_function_rows": weighted["withheld"],
        "weighted_unassessed_ordinary_template_function_rows": None if logical is None else logical - weighted["conditional"] - weighted["withheld"],
        "ordinary_template_shape_eligible_function_rows": None if unknown_plan else eligible, "known_shape_eligible_weighted_subtotal": eligible, "shape_prerequisite_complement_function_rows": None if logical is None or unknown_plan else logical - eligible,
        "queried_origin_tuples": 0, "combined_accounts_computed": 0, "declared_occurrence_plans_computed": 0, "exception_strategy_families_computed": 0,
        "route_inventory_complete": not route_hold, "ordinary_template_inventory_complete": not unknown_plan and not joint_hold and not bundle_hold and all(p["supported_joint_options"] is not None for p in plans)}
    reasons = []
    for held, code in ((route_hold, "whole_neutral_route_inventory_source_or_budget_hold"), (kernel_hold, "whole_obligation_kernel_inventory_source_or_budget_hold"),
        (role_hold, "whole_role_option_inventory_source_or_budget_hold"), (joint_hold, "whole_joint_option_inventory_source_or_budget_hold"), (bundle_hold, "whole_unique_bundle_inventory_source_or_budget_hold")):
        if held: reasons.append(code)
    return {"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]), "analysis_span": deepcopy(scope["analysis_span"]),
        "scope_ref": _ref(scope), "hypotheses_ref": deepcopy(index["hypotheses_ref"]), "index_ref": _ref(index), "relations_ref": _ref(data["relations"]),
        "grounding_ref": _ref(grounding), "temporal_ref": _ref(data["temporal"]), "boundary_ref": _ref(data["boundary"]), "logical_universe": universe,
        "origin_inventory": deepcopy(grounding["origin_inventory"]), "catalog_inventory": deepcopy(grounding["catalog_inventory"]), "keys": deepcopy(grounding["keys"]),
        "source_inventory": deepcopy(grounding["source_inventory"]), "descriptor_inventory": deepcopy(index["profile_inventory"]), "path_groups": path_groups,
        "physical_occurrence_inventory": occurrences, "route_inventory": routes, "role_option_inventory": roles, "obligation_specification_inventory": [dict(s, grounded_direct_kernel_ref=_ref(p), old_direct_status=p["status"]) for s, p in zip(specs, parents)], "obligation_kernel_inventory": kernels,
        "joint_plan_inventory": plans, "inherited_bundle_inventory": inherited,
        "bundle_requests": [{"required_links": [list(e) for e in required], "bundle_ref": None if bundle is None else _ref(bundle)} for required, bundle in required_sets.items()],
        "bundle_inventory": bundles, "bundle_plan_incidence": incidence, "parent_summary": deepcopy(data["relations"]["summary"]),
        "grounding_summary": deepcopy(grounding["summary"]), "temporal_summary": deepcopy(data["temporal"]["summary"]), "boundary_summary": deepcopy(data["boundary"]["summary"]),
        "resource_limits": deepcopy(caps), "summary": summary, "status": "delayed_ordinary_obligations_with_holds" if reasons else "ready_delayed_ordinary_obligation_templates",
        "reasons": reasons, "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "strategy_semantics": "physical_ledger_then_explicit_ordinary_role_existential_or_declared_occurrences_not_universal_music_law",
        "limits": ["Strict new fullpair-contained routes preserve old direct results separately; equivalence needs matching guards.",
            "Ordinary template failure is not music error; frustrated-leading-tone, transfers and other strategies remain unassessed.",
            "Target-cut core/bass and later presentation remain separate from conditional ordinary motion given a harmony hypothesis.",
            "Every role/declared occurrence and optional requested clause must coexist in one authentic completion.",
            "Combined explanation intervals are unioned only under that completion; raw membership and weighted complements never change.",
            "Whole inventory caps are not byte/RSS/lifetime bounds; all optional NCT completions, harmony/key/cadence/accuracy/production are unassessed."]}


def build_obligations_prepared(supplier, **caps):
    if set(caps) - set(CAPS): raise TypeError("unknown_delayed_limit")
    limits = {**DEFAULTS, **caps}; _caps(limits); state = _issued(supplier, _INPUTS, _PreparedInputs)
    result = _seal(_body(indexed._thaw(state.data), limits), PREFIX)
    _issued(supplier, _INPUTS, _PreparedInputs)
    return result


def build_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, **caps):
    if set(caps) - set(CAPS): raise TypeError("unknown_delayed_limit")
    _caps({**DEFAULTS, **caps})
    return build_obligations_prepared(prepare_inputs(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record), **caps)


def _header(record):
    indexed._closed(record, {"version", "contract", "binding", "analysis_span", "scope_ref", "hypotheses_ref", "index_ref", "relations_ref",
        "grounding_ref", "temporal_ref", "boundary_ref", "logical_universe", "origin_inventory", "catalog_inventory", "keys", "source_inventory",
        "descriptor_inventory", "path_groups", "physical_occurrence_inventory", "route_inventory", "role_option_inventory", "obligation_specification_inventory", "obligation_kernel_inventory",
        "joint_plan_inventory", "inherited_bundle_inventory", "bundle_requests", "bundle_inventory", "bundle_plan_incidence", "parent_summary",
        "grounding_summary", "temporal_summary", "boundary_summary", "resource_limits", "summary", "status", "reasons", "selected", "rank", "confidence",
        "flags", "strategy_semantics", "limits", "record_id", "record_sha256"}, "delayed_obligations")
    indexed._closed(record["resource_limits"], set(CAPS), "delayed_resource_limits"); _caps(record["resource_limits"])
    for key in ("origin_inventory", "catalog_inventory", "keys", "source_inventory", "descriptor_inventory", "path_groups", "physical_occurrence_inventory",
        "route_inventory", "role_option_inventory", "obligation_specification_inventory", "obligation_kernel_inventory", "joint_plan_inventory", "inherited_bundle_inventory", "bundle_requests",
        "bundle_inventory", "bundle_plan_incidence", "reasons", "limits"):
        if type(record[key]) is not list: raise ValueError("delayed_list_inventory_required:" + key)


def validate_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record):
    _header(record); frozen._check(record, PREFIX)
    if not indexed._same(record, build_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, **record["resource_limits"])):
        raise ValueError("stale_foreign_modified_or_promoting_delayed_obligations")
    return True


def prepare_obligations_prepared(supplier, record):
    _header(record); frozen._check(record, PREFIX); _issued(supplier, _INPUTS, _PreparedInputs)
    before, contract = digest(record), _contract(); owned_record = deepcopy(record)
    if not indexed._same(owned_record, build_obligations_prepared(supplier, **owned_record["resource_limits"])):
        raise ValueError("stale_foreign_modified_or_promoting_delayed_obligations")
    data = indexed._thaw(_issued(supplier, _INPUTS, _PreparedInputs).data); data["obligations"] = owned_record
    data["registered_bundles"] = owned_record["inherited_bundle_inventory"] + owned_record["bundle_inventory"]
    lookup = {"groups": {g["group_id"]: i for i, g in enumerate(data["index"]["path_groups"])},
        "variants": {v["variant_id"]: i for i, v in enumerate(data["index"]["variant_inventory"])},
        "kernels": {(k["group_id"], k["source_profile_ref"]["record_id"], k["target_profile_ref"]["record_id"], k["family"], k["quality"]): i for i, k in enumerate(owned_record["obligation_kernel_inventory"])},
        "roles": {r["record_id"]: i for i, r in enumerate(owned_record["role_option_inventory"])},
        "routes": {r["record_id"]: i for i, r in enumerate(owned_record["route_inventory"])},
        "bundles": {b["record_id"]: i for i, b in enumerate(data["registered_bundles"])},
        "keys": {k["record_id"]: i for i, k in enumerate(data["index"]["keys"])},
        "profiles": {p["descriptor_ref"]["record_id"]: i for i, p in enumerate(data["grounding"]["profile_inventory"])},
        "rows": {p["record_id"]: i for i, p in enumerate(data["grounding"]["row_inventory"])},
        "cells": {p["record_id"]: i for i, p in enumerate(data["grounding"]["cell_inventory"])},
        "descriptors": {p["record_id"]: i for i, p in enumerate(data["index"]["profile_inventory"])},
        "local_geometries": {p["record_id"]: i for i, p in enumerate(data["temporal"]["geometry_inventory"])},
        "boundary_geometries": {p["record_id"]: i for i, p in enumerate(data["boundary"]["geometry_inventory"])} }
    local = defaultdict(list); boundary_groups = defaultdict(list); physical = defaultdict(list)
    for i, r in enumerate(data["temporal"]["membership_relation_inventory"]):
        for did in r["descriptor_ids"]: local[did].append(i)
    for i, g in enumerate(data["boundary"]["geometry_inventory"]): boundary_groups[g["group_id"]].append(i)
    for i, o in enumerate(owned_record["physical_occurrence_inventory"]): physical[o["group_id"]].append(i)
    lookup.update(local_relations=dict(local), group_boundary_geometries=dict(boundary_groups), group_physical_occurrences=dict(physical))
    _issued(supplier, _INPUTS, _PreparedInputs)
    if before != digest(record) or not indexed._same(contract, _contract()): raise ValueError("delayed_inputs_changed_during_owned_session_preparation")
    return _issue(_PreparedObligations, _SESSIONS, data, lookup)


def prepare_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record):
    caller = [ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record]
    before, contract = digest(caller), _contract()
    result = prepare_obligations_prepared(prepare_inputs(*caller[:8]), record)
    if before != digest(caller) or not indexed._same(contract, _contract()): raise ValueError("delayed_parent_inputs_changed")
    return result


def _selection(state, group_id, left_variant_id, right_variant_id, key_id, family, quality):
    data = state.data
    if type(group_id) is not str or group_id not in state.lookups["groups"]: raise ValueError("explicit_original_delayed_group_required")
    group = data["index"]["path_groups"][state.lookups["groups"][group_id]]
    if len(group["slots"]) != 2: raise ValueError("original_touching_two_slot_group_required")
    if any(type(v) is not str or v not in slot["variant_ids"] for v, slot in zip((left_variant_id, right_variant_id), group["slots"])):
        raise ValueError("ordered_original_delayed_variant_ids_required")
    if left_variant_id == right_variant_id: raise ValueError("duplicate_delayed_origin")
    if type(key_id) is not str or key_id not in state.lookups["keys"]: raise ValueError("registered_original_key_required")
    if type(family) is not str or family not in frozen.FAMILIES or type(quality) is not str or quality not in ("M", "m"):
        raise ValueError("ordinary_family_and_quality_required")
    restored = [boundary._profile(state, v) for v in (left_variant_id, right_variant_id)]
    profiles = [p for p, _ in restored]; origins = [None if o is None else indexed._thaw(o) for _, o in restored]
    key = indexed._thaw(data["index"]["keys"][state.lookups["keys"][key_id]])
    function = None if any(o is None for o in origins) else frozen._function({}, origins[0]["variant"], origins[1]["variant"], key["segments"][0], family, quality)
    k = None
    if all(o is not None for o in origins):
        kkey = (group_id, origins[0]["profile_ref"]["record_id"], origins[1]["profile_ref"]["record_id"], family, quality)
        if kkey in state.lookups["kernels"]: k = indexed._thaw(data["obligations"]["obligation_kernel_inventory"][state.lookups["kernels"][kkey]])
    return profiles, origins, key, function, k


def _declarations(state, group_id, strategy, declared):
    if strategy not in ("ordinary_role_existential", "declared_occurrence_set") or type(strategy) is not str: raise ValueError("explicit_supported_obligation_strategy_required")
    if strategy == "ordinary_role_existential":
        if declared is not None: raise ValueError("existential_strategy_does_not_accept_declared_occurrences")
        return None
    if type(declared) is not list or not declared: raise ValueError("nonempty_explicit_declared_occurrence_set_required")
    physical = {state.data["obligations"]["physical_occurrence_inventory"][i]["source_sound_ref"] for i in state.lookups["group_physical_occurrences"].get(group_id, ())}
    seen = set(); result = []
    for row in declared:
        indexed._closed(row, {"role", "sound_ref"}, "declared_occurrence")
        role, sid = row["role"], row["sound_ref"]
        if type(role) is not str or role not in ("leading_tone", "seventh") or type(sid) is not str or sid not in physical: raise ValueError("registered_physical_group_occurrence_and_role_required")
        if (role, sid) in seen: raise ValueError("duplicate_declared_occurrence")
        seen.add((role, sid)); result.append(deepcopy(row))
    return result


def _strategy(state, kernel, strategy, declared, links, complete):
    record = state.data["obligations"]
    roles = [] if kernel is None or kernel["role_option_refs"] is None else [indexed._thaw(record["role_option_inventory"][state.lookups["roles"][r["record_id"]]]) for r in kernel["role_option_refs"]]
    role_map = {r["role"]: r for r in roles}; clauses = []
    if strategy == "ordinary_role_existential":
        for role in roles: clauses.append((role["role"], None, role, [o for o in role["options"] if o["qualified"]]))
    else:
        for declaration in declared:
            role = role_map.get(declaration["role"]); sid = declaration["sound_ref"]
            clauses.append((declaration["role"], sid, role, [] if role is None else [o for o in role["options"] if o["qualified"] and o["source_sound_ref"] == sid]))
    inventory_complete = bool(roles) and record["summary"]["route_inventory_complete"] and kernel["role_option_refs"] is not None
    assessments = []; choices = []; all_matches = []
    for name, sid, role, candidates in clauses:
        codes = []; unknown = role is None and not roles
        if role is None and roles: codes.append("declared_role_not_in_this_ordinary_template")
        if role is not None:
            unknown_refs = {record["physical_occurrence_inventory"][i]["source_sound_ref"] for i in state.lookups["group_physical_occurrences"].get(kernel["group_id"], ())
                if _ref(record["physical_occurrence_inventory"][i]) in role["unknown_pitch_occurrence_refs"]}
            unknown = bool(unknown_refs) if sid is None else sid in unknown_refs
            if sid is not None and sid not in [o["source_sound_ref"] for o in role["options"]]: codes.append("declared_occurrence_does_not_match_ordinary_role_or_has_no_route")
            relevant = role["options"] if sid is None else [o for o in role["options"] if o["source_sound_ref"] == sid]
            if any(_guard_uncertain(o["blockers"]) for o in relevant): unknown = True
        choices.append([o["route_ref"]["record_id"] for o in candidates])
        matched = []
        for option in candidates:
            route = record["route_inventory"][state.lookups["routes"][option["route_ref"]["record_id"]]]
            if complete and all(tuple(e) in links for e in route["required_links"]): matched.append(deepcopy(option["route_ref"]))
        satisfied = True if inventory_complete and complete and matched else None if not inventory_complete or not complete or unknown else False
        all_matches.extend(matched)
        occurrences = []
        if role is not None:
            # Every physical critical doubling survives, including guarded and
            # unrequested occurrences. No existential proof resolves them all.
            for ref in role["matching_occurrence_refs"]:
                occurrence = next(o for o in record["physical_occurrence_inventory"] if o["record_id"] == ref["record_id"])
                options = [o for o in role["options"] if o["source_sound_ref"] == occurrence["source_sound_ref"]]
                occurrences.append({"source_sound_ref": occurrence["source_sound_ref"], "occurrence_ref": indexed._thaw(ref),
                    "declared_in_this_strategy": strategy == "declared_occurrence_set" and sid == occurrence["source_sound_ref"],
                    "role_eligible_for_existential_selection": strategy == "ordinary_role_existential", "occurrence_individually_required": strategy == "declared_occurrence_set" and sid == occurrence["source_sound_ref"],
                    "options": options, "matched_route_refs": [r for r in matched if any(o["route_ref"] == r for o in options)],
                    "blockers": sorted({c for o in options for c in o["blockers"]})})
        assessments.append({"role": name, "declared_source_sound_ref": sid, "critical_pitch": None if role is None else role["critical_pitch"],
            "occurrence_assessments": indexed._thaw(occurrences), "unknown_pitch_occurrence_refs": [] if role is None else role["unknown_pitch_occurrence_refs"],
            "matched_route_refs": matched, "qualified_route_option_refs": [deepcopy(o["route_ref"]) for o in candidates], "choice_inventory_uncertain": unknown,
            "satisfied": satisfied, "blockers": codes})
    expected_roles = set(role_map)
    required_roles = {c[0] for c in clauses}
    coverage = bool(expected_roles) and required_roles == expected_roles
    values = [a["satisfied"] for a in assessments]
    all_satisfied = None if not inventory_complete or not complete else False if False in values else None if None in values else bool(values)
    ordinary = all_satisfied if coverage else False if inventory_complete and complete else None
    unrequired = [{"role": role["role"], "occurrence_ref": deepcopy(ref), "source_sound_ref": next(o["source_sound_ref"] for o in record["physical_occurrence_inventory"] if o["record_id"] == ref["record_id"]),
        "status": "not_individually_required_by_this_explicit_strategy"} for role in roles for ref in role["matching_occurrence_refs"]
        if strategy == "ordinary_role_existential" or not any(d["role"] == role["role"] and d["sound_ref"] == next(o["source_sound_ref"] for o in record["physical_occurrence_inventory"] if o["record_id"] == ref["record_id"]) for d in declared)]
    return {"strategy": strategy, "declared_occurrences": deepcopy(declared), "role_assessments": assessments, "unrequested_critical_occurrences": indexed._thaw(unrequired),
        "required_role_coverage_complete": coverage, "all_declared_obligations_satisfied": all_satisfied if strategy == "declared_occurrence_set" else None,
        "ordinary_role_existential_satisfied": all_satisfied if strategy == "ordinary_role_existential" else None,
        "whole_ordinary_template_satisfied": ordinary, "declared_strategy_satisfied": all_satisfied if strategy == "declared_occurrence_set" else None, "known_matched_route_refs": indexed._thaw(all_matches),
        "inventory_complete": inventory_complete, "status": "conditional_partial_declared_strategy_not_whole_ordinary_template" if strategy == "declared_occurrence_set" and all_satisfied is True and not coverage else "conditional_ordinary_strategy_given_harmony_hypothesis" if ordinary is True else
            "withheld_this_explicit_strategy_not_music_error" if ordinary is False else "unassessed_obligation_strategy",
        "universal_obligation_or_harmony_confirmation": False}, choices


def _explanation_clauses(state, group_id, origins, requested):
    data = state.data; clauses = []; descriptors = []
    for origin in origins:
        descriptors.append(None if origin is None else indexed._thaw(data["index"]["profile_inventory"][state.lookups["descriptors"][origin["profile_ref"]["record_id"]]]))
    sounds = {s["sound_ref"]: indexed._thaw(s) for s in data["scope"]["sound_facts"]}
    for position, descriptor in enumerate(descriptors):
        if descriptor is None: continue
        for i in state.lookups["local_relations"].get(descriptor["record_id"], ()):
            relation = data["temporal"]["membership_relation_inventory"][i]; gid = relation["geometry_ref"]["record_id"]
            geom = indexed._thaw(data["temporal"]["geometry_inventory"][state.lookups["local_geometries"][gid]])
            codes = indexed._thaw(relation["blockers"])
            if any(actual != "spelling_unresolved" and actual != expected for actual, expected in zip(relation["membership_states"], relation["expected_states"])):
                codes.append("member_nonmember_member_prerequisites_not_met")
            if ("ordinary_passing_neighbor_contour_not_met" in geom["blockers"] and all(m is not None for m in geom["motions"])
                    and all(not temporal._guard_codes(sounds[sid]) and not frozen._source_blockers(sounds[sid]) for sid in geom["involved_sound_refs"])):
                codes.append("source_guarded_known_ordinary_passing_neighbor_contour_not_met")
            clauses.append({"stage": "local", "geometry_id": gid, "side": "left" if position == 0 else "right",
                "qualified": relation["status"] == "conditional_contour_shape", "blockers": sorted(set(codes)),
                "required_links": geom["required_links"], "explained_items": [{"sound_ref": geom["explained_sound_ref"], "span": geom["explained_span"]}]})
    for i in state.lookups["group_boundary_geometries"].get(group_id, ()):
        geom = indexed._thaw(data["boundary"]["geometry_inventory"][i]); codes = list(geom["blockers"])
        for position, side in enumerate(("left", "right")):
            descriptor = descriptors[position]
            if descriptor is None: codes.append("origin_descriptor_not_available"); continue
            codes.extend("hypothesis:" + c for c in descriptor["semantic_input"]["blockers"])
            actual = [frozen._state(sounds[sid], descriptor["semantic_input"]) for sid in geom[side + "_membership_sound_refs"]]
            if "spelling_unresolved" in actual: codes.append("boundary_membership_unknown")
            if any(a != "spelling_unresolved" and a != e for a, e in zip(actual, geom[side + "_expected_states"])): codes.append("boundary_membership_prerequisites_not_met")
        clauses.append({"stage": "boundary", "geometry_id": geom["record_id"], "side": geom["explained_side"], "qualified": not codes,
            "blockers": sorted(set(codes)), "required_links": geom["required_links"], "explained_items": geom["explained_items"]})
    full_count = len(clauses)
    if requested is not None:
        if type(requested) is not list: raise ValueError("explicit_explanation_request_list_required")
        seen = set(); selected = []
        for request in requested:
            indexed._closed(request, {"stage", "geometry_id", "side"}, "requested_explanation")
            if any(type(request[k]) is not str for k in request) or request["stage"] not in ("local", "boundary") or request["side"] not in ("left", "right"):
                raise ValueError("typed_local_or_boundary_explanation_request_required")
            key = tuple(request[k] for k in ("stage", "geometry_id", "side"))
            if key in seen: raise ValueError("duplicate_requested_explanation")
            seen.add(key)
            matches = [c for c in clauses if all(c[k] == request[k] for k in request)]
            if len(matches) != 1: raise ValueError("requested_clause_not_registered_for_exact_selected_origin_pair")
            selected.extend(matches)
        clauses = selected
    return clauses, descriptors, sounds, full_count


def _clause_truth(clause):
    if clause["qualified"]: return True
    # Known false literal prerequisites dominate unsupported source/spelling
    # alternatives. Otherwise guards withhold the requested clause, not prove
    # absence of an explanation.
    known_false = ("member_nonmember_member_prerequisites_not_met", "boundary_membership_prerequisites_not_met",
        "all_three_full_sound_spans_not_inside_descriptor", "all_involved_full_sound_spans_not_inside_pair_envelope",
        "preparation_attack_not_in_left_slot", "first_changed_resolution_not_observed_terminal_carry",
        "first_changed_resolution_not_downward_ordinary_spelled_step", "resolution_attack_not_in_right_half_open_slot",
        "anticipation_reattack_not_identical_written_register")
    known_false += ("source_guarded_known_ordinary_passing_neighbor_contour_not_met",)
    return False if any(c in known_false for c in clause["blockers"]) else None


def _account(profile, descriptor, sounds, explained, assessed):
    totals = {k: Fraction() for k in CATEGORIES}; intervals = defaultdict(list); credited = []
    for item in explained: intervals[item["sound_ref"]].append(item["span"])
    unions = {sid: temporal._union(spans) for sid, spans in intervals.items()}
    for row in profile["rows"]:
        sid = row["sound_ref"]; a, b = span_bounds(row["observed_span"]); duration = b - a
        if descriptor["semantic_input"]["blockers"] or temporal._guard_codes(sounds[sid]) or frozen._source_blockers(sounds[sid]): totals["source_or_hypothesis_unsupported"] += duration
        elif row["state"] == "member": totals["source_guarded_member"] += duration
        elif row["state"] == "spelling_unresolved": totals["membership_unknown"] += duration
        elif not assessed: totals["unassessed_nonmember"] += duration
        else:
            spans = temporal._union([temporal._span(max(a, x), min(b, y)) for x, y in (span_bounds(s) for s in unions.get(sid, ())) if max(a, x) < min(b, y)])
            credit = temporal._duration(spans)
            if spans: credited.append({"sound_ref": sid, "spans": spans})
            totals["conditional_combined_explained_nonmember"] += credit; totals["unexplained_nonmember_under_this_completion"] += duration - credit
    if sum(totals.values(), Fraction()) != f(profile["total_note_time_quarters"]): raise ValueError("same_completion_combined_raw_note_time_loss")
    return {"raw_note_time": deepcopy(profile["note_time_quarters"]), "total_note_time": deepcopy(profile["total_note_time_quarters"]),
        "note_time": {k: q(v) for k, v in totals.items()}, "conditional_explanation_note_time": q(totals["conditional_combined_explained_nonmember"]) if assessed else None,
        "credited_intervals_by_sound": credited, "combined_accounting_basis": "per_sound_interval_union_under_this_one_actual_completion_not_sum_of_prior_accounts"}


def _query(state, group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle,
           strategy="ordinary_role_existential", declared_occurrences=None, requested_explanations=None, query_work_budget=None):
    data = state.data; record = data["obligations"]
    profiles, origins, key, function, kernel = _selection(state, group_id, left_variant_id, right_variant_id, key_id, family, quality)
    declared = _declarations(state, group_id, strategy, declared_occurrences)
    links = set() if bundle is None else temporal._links(bundle); complete = bundle is not None and bundle["status"] == "complete_all_lane_witness"
    completion_known_no = bundle is not None and bundle.get("geometry_condition_status") == "impossible"
    ordinary, choices = _strategy(state, kernel, strategy, declared, set() if completion_known_no else links, complete or completion_known_no)
    if completion_known_no:
        ordinary = {**ordinary, "whole_ordinary_template_satisfied": False, "ordinary_role_existential_satisfied": False if strategy == "ordinary_role_existential" else None,
            "declared_strategy_satisfied": False if strategy == "declared_occurrence_set" else None, "all_declared_obligations_satisfied": False if strategy == "declared_occurrence_set" else None,
            "known_matched_route_refs": [], "status": "not_satisfied_incompatible_actual_completion_not_music_error"}
    clauses, descriptors, sounds, all_clause_count = _explanation_clauses(state, group_id, origins, requested_explanations)
    physical_ledger = []
    for i in state.lookups["group_physical_occurrences"].get(group_id, ()):
        occurrence = record["physical_occurrence_inventory"][i]; sid = occurrence["source_sound_ref"]
        for role in ("leading_tone", "seventh"):
            critical = None if function is None else function[role]
            if critical is None: continue
            actual = frozen._pitch_key(sounds[sid]["pitch"]); wanted = frozen._pitch_key(critical)
            physical_ledger.append({"role": role, "source_sound_ref": sid, "occurrence_ref": _ref(occurrence),
                "physical_role_match": None if actual is None or wanted is None else actual == wanted,
                "source_snapshot": indexed._thaw(occurrence["source_snapshot"]), "source_guard_blockers": indexed._thaw(occurrence["source_guard_blockers"]),
                "individually_required": strategy == "declared_occurrence_set" and any(d["role"] == role and d["sound_ref"] == sid for d in declared),
                "role_is_existential_choice_not_individual_obligation": strategy == "ordinary_role_existential"})
    known_work = sum(len(p["rows"]) for p in profiles if p is not None) + len(clauses) + sum(len(a["occurrence_assessments"]) for a in ordinary["role_assessments"]) + sum(len(c) for c in choices)
    shape_ineligible = function is not None and function["status"] != "conditional_function_shape"
    plan_complete = shape_ineligible or ordinary["inventory_complete"]
    work = known_work if all(p is not None for p in profiles) and plan_complete and data["temporal"]["summary"]["local_contour_relation_inventory_complete"] and data["boundary"]["summary"]["membership_inventory_complete"] else None
    budget = record["resource_limits"]["query_work_budget"] if query_work_budget is None else query_work_budget
    hold = work is None or work > budget
    explanation = [[], []]; rows = []
    if not hold:
        for clause in clauses:
            satisfied = complete and clause["qualified"] and all(tuple(e) in links for e in clause["required_links"])
            if satisfied: explanation[0 if clause["side"] == "left" else 1].extend(clause["explained_items"])
            rows.append({"stage": clause["stage"], "geometry_id": clause["geometry_id"], "side": clause["side"], "blockers": clause["blockers"],
                "status": "conditional_explanation_under_this_same_completion" if satisfied else "unassessed_completion" if not complete else "withheld_clause_prerequisites" if not clause["qualified"] else "not_satisfied_under_this_completion_not_global_absence"})
        if complete and (ordinary["whole_ordinary_template_satisfied"] is True or (strategy == "declared_occurrence_set" and ordinary["declared_strategy_satisfied"] is True)):
            cut = f(data["index"]["path_groups"][state.lookups["groups"][group_id]]["slots"][1]["span"]["start"])
            for ref in ordinary["known_matched_route_refs"]:
                route = record["route_inventory"][state.lookups["routes"][ref["record_id"]]]
                for sid in route["involved_sound_refs"][:-1]:
                    a, b = span_bounds(sounds[sid]["span"])
                    if max(a, cut) < b: explanation[1].append({"sound_ref": sid, "span": temporal._span(max(a, cut), b)})
                rows.append({"stage": "delayed_ordinary", "route_ref": indexed._thaw(ref), "side": "right", "status": "conditional_role_route_under_this_same_completion", "blockers": []})
    if hold:
        ordinary = {**ordinary, "status": "whole_delayed_query_source_or_work_inventory_hold", "whole_ordinary_template_satisfied": None,
            "all_declared_obligations_satisfied": None, "declared_strategy_satisfied": None, "ordinary_role_existential_satisfied": None,
            "role_assessments": None, "known_matched_route_refs": None}
    accounts = None if hold else [_account(p, d, sounds, explanation[i], complete) for i, (p, d) in enumerate(zip(profiles, descriptors))]
    return _seal({"version": VERSION, "contract": _contract(), "obligations_ref": _ref(record), "scope_ref": indexed._thaw(record["scope_ref"]),
        "index_ref": indexed._thaw(record["index_ref"]), "symbolic_universe_ref": _ref(record["logical_universe"]), "group_id": group_id,
        "origin_variant_ids": [left_variant_id, right_variant_id], "origin_refs": [None if o is None else _ref(o["variant"]) for o in origins],
        "key_ref": _ref(key), "family": family, "quality": quality, "bundle_ref": None if bundle is None else _ref(bundle),
        "same_complete_all_lane_bundle": complete, "completion_certified_impossible": completion_known_no,
        "same_completion_combined_accounts_computed": accounts is not None, "profiles": profiles, "function": function, "obligation_kernel_ref": None if kernel is None else _ref(kernel),
        "old_direct_kernel_ref": None if kernel is None else kernel["grounded_direct_kernel_ref"], "old_direct_status": None if kernel is None else kernel["old_direct_status"],
        "literal_core_and_time_audit": None if kernel is None else kernel["literal_core_and_time_audit"], "ordinary_strategy": ordinary, "physical_role_binding_ledger": physical_ledger,
        "requested_explanations": deepcopy(requested_explanations), "finite_clause_coverage": "all_registered_for_selected_origins" if requested_explanations is None else "explicit_requested_subset",
        "known_registered_finite_clause_subtotal": all_clause_count, "unrequested_registered_clause_count": all_clause_count - len(clauses),
        "combined_accounts": accounts, "explanation_assessments": None if hold else rows,
        "planned_query_work_items": work, "known_stored_query_work_subtotal": known_work, "query_work_budget": budget,
        "status": "whole_delayed_query_source_or_work_inventory_hold" if hold else "computed_conditional_obligation_axes_not_selected",
        "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "limits": ["Ordinary role templates are declared assumptions, not a universal obligation for every doubling.",
            "Conditional ordinary motion is given an explicit harmony hypothesis; target-cut missing core and raw memberships remain unchanged.",
            "Requested or finite local/boundary/delayed clauses are unioned only under this same completion; full NCT coverage is not claimed."]}, QUERY_PREFIX)


def query_obligations_prepared(session, group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle_id,
                              *, strategy="ordinary_role_existential", declared_occurrences=None, requested_explanations=None):
    state = _issued(session, _SESSIONS, _PreparedObligations)
    no_bundle = bundle_id is None and not state.lookups["bundles"]
    if not no_bundle and (type(bundle_id) is not str or bundle_id not in state.lookups["bundles"]): raise ValueError("registered_actual_same_universe_obligation_bundle_required")
    bundle = None if no_bundle else indexed._thaw(state.data["registered_bundles"][state.lookups["bundles"][bundle_id]])
    result = _query(state, group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle, strategy, declared_occurrences, requested_explanations)
    _issued(session, _SESSIONS, _PreparedObligations)
    return result


def query_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
                      group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle_id, **options):
    return query_obligations_prepared(prepare_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record),
        group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle_id, **options)


def validate_query(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
                   group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle_id, result, **options):
    frozen._check(result, QUERY_PREFIX)
    if not indexed._same(result, query_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
            group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle_id, **options)): raise ValueError("stale_foreign_modified_delayed_query")
    return True


def compile_joint_prepared(session, group_id, left_variant_id, right_variant_id, key_id, family, quality,
                           *, strategy="ordinary_role_existential", declared_occurrences=None, requested_explanations=None, **caps):
    """Compile one declared proof request without changing the bulk artifact.

    Every option is admitted as a whole; geometry zero is not a work hold.
    Optional explanation requests are AND clauses, never independent witnesses.
    """
    if set(caps) - set(CAPS): raise TypeError("unknown_delayed_limit")
    _caps({**DEFAULTS, **caps})
    state = _issued(session, _SESSIONS, _PreparedObligations); data = state.data; record = data["obligations"]
    limits = {**indexed._thaw(record["resource_limits"]), **caps}
    profiles, origins, key, function, kernel = _selection(state, group_id, left_variant_id, right_variant_id, key_id, family, quality)
    declared = _declarations(state, group_id, strategy, declared_occurrences)
    template, choices = _strategy(state, kernel, strategy, declared, set(), True)
    # Assessing absent links gives false incidence but does not erase the
    # qualified route-choice inventory from which a fresh witness is compiled.
    clauses, _, _, _ = _explanation_clauses(state, group_id, origins, requested_explanations if requested_explanations is not None else [])
    inventory_complete = template["inventory_complete"] and all(p is not None for p in profiles)
    known_false_clause = inventory_complete and any(not choice and not a["choice_inventory_uncertain"] for choice, a in zip(choices, template["role_assessments"]))
    uncertain_alternatives = not known_false_clause and any(a["choice_inventory_uncertain"] for a in template["role_assessments"])
    unknown = not inventory_complete or uncertain_alternatives
    known_product = 1 if choices else 0
    for choice in choices: known_product *= len(choice)
    clause_blockers = sorted({c for clause in clauses for c in clause["blockers"]}); clause_values = [_clause_truth(c) for c in clauses]
    if False in clause_values: known_product = 0; known_false_clause = True; unknown = False; uncertain_alternatives = False
    elif None in clause_values and not known_false_clause: unknown = True; uncertain_alternatives = True; known_product = 0
    planned = None if unknown else known_product
    route_map = {rid: data["obligations"]["route_inventory"][i] for rid, i in state.lookups["routes"].items()}
    upstream_override_hold = any(record["summary"][name] is not None and record["summary"][name] > limits[cap] for name, cap in (
        ("planned_route_candidates", "max_route_candidates"), ("max_planned_chain_edges", "max_chain_edges"),
        ("planned_obligation_kernels", "max_obligation_kernels"), ("planned_role_options", "max_role_options")))
    joint_hold = not inventory_complete or upstream_override_hold or (unknown and known_product == 0) or known_product > limits["max_joint_options"]
    specifications = []; required_sets = {}
    if not joint_hold and known_product:
        for selected in product(*choices):
            required = tuple(sorted(set(_required(selected, route_map)) | {tuple(e) for clause in clauses for e in clause["required_links"]}))
            specifications.append((selected, required)); required_sets.setdefault(required, None)
    bundle_hold = joint_hold or len(required_sets) > limits["max_new_bundles"]
    bundles = []
    if not bundle_hold:
        minimal = {"scope": indexed._thaw(data["scope"]), "index": data["index"], "grounding": data["grounding"]}
        universe = indexed._thaw(record["logical_universe"])
        for required in required_sets:
            bundle = _bundle(minimal, universe, required, limits["query_work_budget"])
            required_sets[required] = bundle; bundles.append(bundle)
    branches = []; assessments = []; supported = 0; support_unknown = (bundle_hold or uncertain_alternatives) and not known_false_clause
    for selected, required in specifications:
        bundle = required_sets[required]; condition = "whole_unique_bundle_inventory_hold" if bundle is None else bundle["geometry_condition_status"]
        supported += condition == "possible"; support_unknown |= condition in ("unknown", "whole_unique_bundle_inventory_hold")
        branches.append({"route_refs": [_ref(route_map[r]) for r in selected], "required_links": [list(e) for e in required],
            "bundle_ref": None if bundle is None else _ref(bundle), "status": condition})
    for bundle in bundles:
        assessments.append(_query(state, group_id, left_variant_id, right_variant_id, key_id, family, quality, bundle,
            strategy, declared, requested_explanations, limits["query_work_budget"]))
    reasons = (["source_or_role_inventory_unknown"] if unknown else []) + (["whole_lazy_joint_product_budget_hold_no_prefix"] if known_product > limits["max_joint_options"] else [])
    if upstream_override_hold: reasons.append("whole_lazy_upstream_inventory_limit_hold_no_prefix")
    if not joint_hold and len(required_sets) > limits["max_new_bundles"]: reasons.append("whole_lazy_unique_bundle_budget_hold_no_prefix")
    if clause_blockers: reasons.append("requested_explanation_prerequisites_withheld")
    result = _seal({"version": VERSION, "contract": _contract(), "obligations_ref": _ref(record),
        "scope_ref": indexed._thaw(record["scope_ref"]), "index_ref": indexed._thaw(record["index_ref"]), "symbolic_universe_ref": _ref(record["logical_universe"]),
        "group_id": group_id, "origin_variant_ids": [left_variant_id, right_variant_id], "key_ref": _ref(key), "family": family, "quality": quality,
        "strategy": strategy, "declared_occurrences": declared, "requested_explanations": deepcopy(requested_explanations),
        "resource_limits": limits, "summary": {"planned_joint_options": planned, "known_qualified_joint_option_subtotal": known_product,
            "materialized_joint_options": 0 if joint_hold else len(specifications), "planned_new_bundles": None if joint_hold else len(required_sets),
            "materialized_new_bundles": len(bundles), "supported_joint_options": None if support_unknown else supported,
            "known_supported_joint_option_subtotal": supported, "impossible_bundles": sum(b["geometry_condition_status"] == "impossible" for b in bundles),
            "unknown_bundles": sum(b["geometry_condition_status"] == "unknown" for b in bundles), "queried_origin_tuples": len(assessments),
            "combined_accounts_computed": sum(a["combined_accounts"] is not None for a in assessments)},
        "branches": branches, "bundle_inventory": bundles, "assessments": assessments, "requested_clause_blockers": clause_blockers,
        "status": "whole_lazy_joint_compilation_hold" if reasons and (joint_hold or bundle_hold) else "computed_lazy_joint_compilation_not_selected",
        "reasons": reasons, "bulk_artifact_mutated": False, "selected": None, "rank": None, "confidence": None, "flags": _flags()}, COMPILE_PREFIX)
    _issued(session, _SESSIONS, _PreparedObligations)
    return result


def compile_joint(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
                  group_id, left_variant_id, right_variant_id, key_id, family, quality, **options):
    return compile_joint_prepared(prepare_obligations(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record),
        group_id, left_variant_id, right_variant_id, key_id, family, quality, **options)


def validate_compilation(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
                         group_id, left_variant_id, right_variant_id, key_id, family, quality, result, **options):
    frozen._check(result, COMPILE_PREFIX)
    if not indexed._same(result, compile_joint(ir, scope, hypotheses, index, relations, grounding, temporal_record, boundary_record, record,
        group_id, left_variant_id, right_variant_id, key_id, family, quality, **options)): raise ValueError("stale_foreign_modified_delayed_joint_compilation")
    return True
