"""Lossless weighted function-SHAPE relations, not literal harmony analysis.

Source kernels, rooted target-core joins and key projections share exact pure
inputs. Their weighted products retain every origin and terminal multiplicity
without constructing Cartesian paths or per-path function inventories. Literal
profiles, endpoints, motion and voice bundles remain explicitly unassessed.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import hmac
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_expanded_hypotheses as frozen
from . import factor_indexed_hypotheses as indexed
from .musical_pattern_observation import digest

VERSION = "factor-function-relations-0.1.0"
PREFIX = "fmfrel_"
TYPE_PREFIX = "fmftype_"
KERNEL_PREFIX = "fmfkernel_"
TARGET_PREFIX = "fmftarget_"
KEY_TYPE_PREFIX = "fmfkeytype_"
PROJECTION_PREFIX = "fmfkeyproj_"
QUERY_PREFIX = "fmfquery_"
SHAPE_STATES = tuple(a + b for a in ("T", "F", "U") for b in ("T", "F", "U"))
FUNCTION_KINDS = ("primary", "parallel", "applied", "unassessed")
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    return {**indexed._flags(), "literal_profiles_evaluated": False,
        "actual_endpoints_evaluated": False, "actual_motion_evaluated": False,
        "same_bundle_compatibility_evaluated": False,
        "all_logical_function_rows_materialized": False}


def _contract():
    return {"version": VERSION,
        "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "indexed_contract": indexed._contract(), "function_contract": frozen._contract()}


def _seal(body, prefix):
    return frozen._seal(body, prefix)


def _ref(record):
    return frozen._ref(record)


def _same(a, b):
    return indexed._same(a, b)


def _limit(value, name):
    indexed._integer(value, name)


def _semantic(variant):
    # Exact order and blockers survive; compatibility alone may use pitch sets.
    return {name: deepcopy(variant[name]) for name in ("root", "members", "blockers")}


def _type(variant):
    return _seal({"version": VERSION, "semantic": _semantic(variant),
        "semantics": "span_independent_exact_root_ordered_members_and_blockers_not_origin_identity",
        "flags": _flags()}, TYPE_PREFIX)


def _key_type(segment):
    return _seal({"version": VERSION,
        "semantic": {name: deepcopy(segment[name]) for name in ("tonic", "mode", "scale_form")},
        "key_inferred": False}, KEY_TYPE_PREFIX)


def _inventories(index):
    types, type_by_semantic, origins, representatives = [], {}, [], {}
    for row in index["variant_inventory"]:
        variant = row["variant"]
        semantic_id = digest(_semantic(variant))
        item = type_by_semantic.get(semantic_id)
        if item is None:
            item = _type(variant)
            type_by_semantic[semantic_id] = item
            types.append(item)
            representatives[item["record_id"]] = variant
        origins.append({"variant_id": row["variant_id"], "variant_ref": _ref(variant),
            "catalog_id": row["catalog_id"], "segment_ref": row["segment_ref"],
            "span": deepcopy(variant["span"]), "profile_ref": deepcopy(row["profile_ref"]),
            "type_ref": _ref(item),
            **{name: deepcopy(variant[name]) for name in ("provider", "supplier_candidate_ref",
                "supplier_record_pointer", "supplier_origin_pointer", "spelling_alternative_index", "provenance")}})
    by_origin = {row["variant_id"]: row for row in origins}
    catalogs = []
    for old in index["catalog_inventory"]:
        weights = Counter(by_origin[ref]["type_ref"]["record_id"] for ref in old["variant_ids"] if ref in by_origin)
        catalogs.append({**deepcopy(old), "type_weights": [
            {"type_id": type_id, "origin_count": count} for type_id, count in weights.items()],
            "types_indexed": len(weights) > 0 or old["variant_count"] == 0})
    key_types, key_by_semantic, key_inventory, key_representatives = [], {}, [], {}
    for key in index["keys"]:
        segment = key["segments"][0]
        item = _key_type(segment)
        if item["record_id"] not in key_by_semantic:
            key_by_semantic[item["record_id"]] = item
            key_types.append(item)
            key_representatives[item["record_id"]] = segment
        key_inventory.append({"key_ref": _ref(key), "key_segment_ref": segment["segment_id"],
            "key_type_ref": _ref(item)})
    return types, origins, catalogs, representatives, key_types, key_inventory, key_representatives


def _kernel(scope, representative, type_record, key_segment, family, quality):
    row = frozen._function(scope, representative, None, key_segment, family, quality)
    remove = {"source_segment_ref", "target_segment_ref", "source_span", "target_span",
        "actual_target_root", "actual_target_members", "target_shape_compatible",
        "function_kind", "key_segment_ref", "key_projection", "status", "blockers"}
    template = {name: deepcopy(value) for name, value in row.items() if name not in remove}
    blockers = sorted((set(row["blockers"]) - {"following_target_segment_not_observed"})
                      | set(representative["blockers"]))
    return {"version": VERSION, "source_type_ref": _ref(type_record),
        "representative_variant_ref": _ref(representative), "family": family,
        "quality": quality, "source_template": template, "source_blockers": blockers}


def _projection_input(kernel, key_type):
    template = kernel["source_template"]
    return {"expected_source_members": deepcopy(template["expected_source_members"]),
        "derived_target_root": deepcopy(template["derived_target_root"]),
        "quality": kernel["quality"], "key_type_ref": _ref(key_type)}


def _compile(scope, types, representatives, key_types, key_representatives, universe):
    resolved, unresolved, rooted = [], [], defaultdict(list)
    for item in types:
        semantic = item["semantic"]
        if semantic["root"] is None or semantic["members"] is None:
            unresolved.append(item["record_id"])
        else:
            resolved.append(item["record_id"])
            rooted[frozen._pitch_key(semantic["root"])].append(item)
    target_universe = _seal({"version": VERSION, "type_refs": [_ref(item) for item in types],
        "resolved_type_ids": resolved, "unresolved_type_ids": unresolved,
        "source_universe_ref": _ref(universe)}, "fmftargetuniverse_")
    targets, target_by_signature, projections, projection_by_input, kernels = [], {}, [], {}, []
    first_key = next(iter(key_representatives.values()))
    for source_type in types:
        representative = representatives[source_type["record_id"]]
        for family in frozen.FAMILIES:
            for quality in ("M", "m"):
                body = _kernel(scope, representative, source_type, first_key, family, quality)
                template = body["source_template"]
                signature = {"root": template["derived_target_root"], "core_members": template["derived_target_members"]}
                signature_id = digest(signature)
                target = target_by_signature.get(signature_id)
                if target is None:
                    true, clean = [], []
                    if signature["root"] is not None:
                        core = {frozen._pitch_key(p) for p in signature["core_members"]}
                        for candidate in rooted.get(frozen._pitch_key(signature["root"]), []):
                            semantic = candidate["semantic"]
                            if core <= {frozen._pitch_key(p) for p in semantic["members"]}:
                                true.append(candidate["record_id"])
                                if not semantic["blockers"]:
                                    clean.append(candidate["record_id"])
                    target = _seal({"version": VERSION, "signature": deepcopy(signature),
                        "target_type_universe_ref": _ref(target_universe), "true_type_ids": true,
                        "clean_true_type_ids": clean,
                        "unknown_partition": "all_target_types" if signature["root"] is None else "unresolved_target_types",
                        "false_partition": "empty" if signature["root"] is None else "resolved_target_types_minus_true_type_ids",
                        "semantics": "exact_spelled_root_and_triad_core_subset_join_with_symbolic_complements_not_literal_membership",
                        "flags": _flags()}, TARGET_PREFIX)
                    target_by_signature[signature_id] = target
                    targets.append(target)
                refs = {}
                for key_type in key_types:
                    projection_input = _projection_input(body, key_type)
                    projection_id = digest(projection_input)
                    projection = projection_by_input.get(projection_id)
                    if projection is None:
                        row = frozen._function(scope, representative, None,
                            key_representatives[key_type["record_id"]], family, quality)
                        projection = _seal({"version": VERSION, "input": projection_input,
                            "function_kind": row["function_kind"], "key_projection": deepcopy(row["key_projection"]),
                            "key_inferred": False, "flags": _flags()}, PROJECTION_PREFIX)
                        projection_by_input[projection_id] = projection
                        projections.append(projection)
                    refs[key_type["record_id"]] = _ref(projection)
                body.update(target_relation_ref=_ref(target), key_projection_refs=refs,
                    semantics="source_template_only_no_actual_profile_or_voice_endpoint", flags=_flags())
                kernels.append(_seal(body, KERNEL_PREFIX))
    return kernels, targets, projections, target_universe


def _state(value):
    return "U" if value is None else "T" if value else "F"


def _group_counts(old, catalogs, types, kernels, targets, projections, key_inventory, hold):
    reasons = list(old["reasons"])
    if hold:
        reasons.append("whole_source_kernel_inventory_exceeds_budget_no_prefix")
    ready = old["status"] == "ready_factorized_group" and not hold
    by_type = {item["record_id"]: item for item in types}
    by_target = {item["record_id"]: item for item in targets}
    by_projection = {item["record_id"]: item for item in projections}
    by_source = defaultdict(list)
    for kernel in kernels:
        by_source[kernel["source_type_ref"]["record_id"]].append(kernel)
    slots = []
    for position, slot in enumerate(old["slots"]):
        source = catalogs[slot["catalog_id"]]
        terminal = position + 1 == len(old["slots"])
        target = None if terminal else catalogs[old["slots"][position + 1]["catalog_id"]]
        opposite = 1
        for i, other in enumerate(old["slots"]):
            if i != position:
                count = catalogs[other["catalog_id"]]["variant_count"]
                opposite = None if opposite is None or count is None else opposite * count
        states = dict.fromkeys(SHAPE_STATES, 0) if ready else None
        statuses = {"conditional_function_shape": 0, "withheld": 0} if ready else None
        kinds = dict.fromkeys(FUNCTION_KINDS, 0) if ready else None
        per_key = {row["key_ref"]["record_id"]: dict.fromkeys(FUNCTION_KINDS, 0) for row in key_inventory} if ready else None
        if ready:
            target_weights = {} if target is None else {row["type_id"]: row["origin_count"] for row in target["type_weights"]}
            target_count = 1 if terminal else target["variant_count"]
            for weight in source["type_weights"]:
                n = weight["origin_count"]
                for kernel in by_source[weight["type_id"]]:
                    relation = by_target[kernel["target_relation_ref"]["record_id"]]
                    if terminal:
                        joined = {"T": 0, "F": 0, "U": opposite}
                        clean_true = 0
                    else:
                        true = sum(target_weights.get(ref, 0) for ref in relation["true_type_ids"])
                        unknown = target_count if relation["unknown_partition"] == "all_target_types" else sum(
                            count for ref, count in target_weights.items()
                            if by_type[ref]["semantic"]["root"] is None or by_type[ref]["semantic"]["members"] is None)
                        joined = {"T": true, "F": target_count - true - unknown, "U": unknown}
                        clean_true = sum(target_weights.get(ref, 0) for ref in relation["clean_true_type_ids"])
                    left = _state(kernel["source_template"]["shape_compatible"])
                    for right, count in joined.items():
                        states[left + right] += n * count * len(key_inventory)
                    compatible = 0 if terminal or kernel["source_blockers"] else n * clean_true * len(key_inventory)
                    total = n * (opposite if terminal else target_count) * len(key_inventory)
                    statuses["conditional_function_shape"] += compatible
                    statuses["withheld"] += total - compatible
                    for key in key_inventory:
                        projection = by_projection[kernel["key_projection_refs"][key["key_type_ref"]["record_id"]]["record_id"]]
                        count = n * (opposite if terminal else target_count)
                        kinds[projection["function_kind"]] += count
                        per_key[key["key_ref"]["record_id"]][projection["function_kind"]] += count
        denominator = None if old["logical_tuple_count"] is None else old["logical_tuple_count"] * 10
        if ready and (sum(states.values()) != denominator or sum(statuses.values()) != denominator or sum(kinds.values()) != denominator):
            raise ValueError("weighted_function_slot_denominator_mismatch")
        slots.append({"slot_index": position, "source_catalog_id": slot["catalog_id"],
            "target_catalog_id": None if terminal else old["slots"][position + 1]["catalog_id"],
            "terminal_target": terminal, "source_origin_count": source["variant_count"],
            "opposite_slot_multiplicity": opposite, "logical_function_rows": denominator,
            "terminal_target_rows": denominator if terminal else 0,
            "shape_state_counts": states, "status_counts": statuses,
            "function_kind_counts": kinds, "key_function_kind_counts": per_key,
            "profiles_endpoints_motion_and_bundles": "unassessed"})
    body = {**deepcopy(old), "indexed_status": old["status"], "indexed_reasons": deepcopy(old["reasons"]),
        "status": "source_index_hold" if old["status"] != "ready_factorized_group" else "whole_kernel_budget_abstention" if hold else "ready_function_shape_relations",
        "reasons": sorted(set(reasons)), "function_slots": slots}
    return {"relation_group_id": "fmfgroup_" + digest(body)[:24], **body}


def _body(scope, index, max_kernels):
    types, origins, catalogs, representatives, key_types, key_inventory, key_representatives = _inventories(index)
    planned = len(types) * len(frozen.FAMILIES) * 2
    hold = planned > max_kernels
    if hold or not types:
        kernels, targets, projections = [], [], []
        target_universe = _seal({"version": VERSION, "type_refs": [_ref(item) for item in types],
            "resolved_type_ids": [item["record_id"] for item in types if item["semantic"]["root"] is not None and item["semantic"]["members"] is not None],
            "unresolved_type_ids": [item["record_id"] for item in types if item["semantic"]["root"] is None or item["semantic"]["members"] is None],
            "source_universe_ref": _ref(index["universe"])}, "fmftargetuniverse_")
    else:
        kernels, targets, projections, target_universe = _compile(
            scope, types, representatives, key_types, key_representatives, index["universe"])
    catalog_map = {row["catalog_id"]: row for row in catalogs}
    groups = [_group_counts(group, catalog_map, types, kernels, targets, projections, key_inventory, hold)
              for group in index["path_groups"]]
    slots = [slot for group in groups for slot in group["function_slots"]]
    totals = Counter()
    shape_totals = dict.fromkeys(SHAPE_STATES, 0)
    kind_totals = dict.fromkeys(FUNCTION_KINDS, 0)
    for slot in slots:
        if slot["status_counts"] is not None:
            totals.update(slot["status_counts"])
            for name, count in slot["shape_state_counts"].items(): shape_totals[name] += count
            for name, count in slot["function_kind_counts"].items(): kind_totals[name] += count
    return {"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "hypotheses_ref": deepcopy(index["hypotheses_ref"]), "index_ref": _ref(index),
        "analysis_span": deepcopy(index["analysis_span"]), "logical_universe": deepcopy(index["universe"]),
        "origin_inventory": origins, "type_inventory": types, "catalog_inventory": catalogs,
        "keys": deepcopy(index["keys"]), "key_types": key_types, "key_inventory": key_inventory,
        "kernels": kernels, "target_relations": targets, "target_type_universe": target_universe,
        "key_projections": projections, "path_groups": groups,
        "resource_limits": {"max_kernels": max_kernels},
        "status": "whole_kernel_budget_abstention" if hold else "function_relations_with_source_index_holds" if any(g["reasons"] for g in groups) else "ready_function_shape_relations",
        "reasons": sorted({reason for group in groups for reason in group["reasons"]}),
        "summary": {"origin_variants": len(origins),
            "stored_origin_id_subtotal": sum(len(c["variant_ids"]) for c in catalogs),
            "unknown_supplier_catalogs": sum(c["variant_count"] is None for c in catalogs),
            "semantic_types": len(types), "catalog_spans": len(catalogs),
            "key_hypotheses": len(index["keys"]), "key_types": len(key_types),
            "planned_source_kernels": planned, "materialized_source_kernels": len(kernels),
            "planned_key_projection_upper_bound": planned * len(key_types), "shared_key_projections": len(projections),
            "shared_target_relations": len(targets), "groups": len(groups),
            "group_statuses": dict(Counter(g["status"] for g in groups)),
            "logical_paths": index["universe"]["logical_paths"], "logical_path_key_tuples": index["universe"]["logical_tuples"],
            "logical_function_rows": sum(g["logical_function_count"] or 0 for g in groups),
            "unknown_product_groups": index["universe"]["unknown_product_groups"],
            "factored_function_rows": sum(sum(slot["status_counts"].values()) for slot in slots if slot["status_counts"] is not None),
            "unassessed_function_rows": sum(slot["logical_function_rows"] or 0 for slot in slots if slot["status_counts"] is None),
            "conditional_function_shape_rows": totals["conditional_function_shape"], "withheld_function_shape_rows": totals["withheld"],
            "shape_state_counts": shape_totals, "function_kind_counts": kind_totals,
            "terminal_target_rows": sum(slot["terminal_target_rows"] or 0 for slot in slots),
            "queried_function_rows": 0, "literal_profiles_computed": 0, "actual_endpoint_pairs_computed": 0,
            "motion_groups_computed": 0, "same_bundle_assessments_computed": 0},
        "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "analysis_scope": "pure_function_shape_target_core_and_key_projection_only",
        "profiles_endpoints_motion_and_bundles": "unassessed",
        "resource_limit_semantics": "max_kernels_bounds_whole_source_type_times_family_quality_inventory_not_bytes_RSS_or_key_projection_upper_bound",
        "validation_semantics": "intrinsic_indexed_lineage_and_full_IR_scope_replay_not_optional_fresh_provider_regeneration_or_parent_file_authority",
        "limits": ["Weighted function-shape counts are exact catalogue assumptions, not confirmed score harmony.",
            "Terminal source multiplicity includes all origins of the opposite slot.",
            "Target false/unknown partitions are symbolic exact complements, not omitted competing origins.",
            "Unknown key projections do not infer local key or veto a conditional chord-shape assumption.",
            "Literal note membership, bass, source eligibility, endpoint motion and same-bundle compatibility are unassessed."]}


def _owned(ir, scope, hypotheses, index, relations=None):
    inputs = [ir, scope, hypotheses, index] + ([] if relations is None else [relations])
    before, contract = digest(inputs), _contract()
    owned = deepcopy(inputs)
    indexed._check_index_lineage(*owned[:4])
    if before != digest(inputs) or not _same(contract, _contract()):
        raise ValueError("relation_inputs_or_current_code_changed_during_owned_validation")
    return owned, before, contract


def build_relations(ir, scope, hypotheses, index, *, max_kernels=65536):
    _limit(max_kernels, "max_kernels")
    owned, before, contract = _owned(ir, scope, hypotheses, index)
    result = _seal(_body(owned[1], owned[3], max_kernels), PREFIX)
    if before != digest([ir, scope, hypotheses, index]) or not _same(contract, _contract()):
        raise ValueError("relation_inputs_or_current_code_changed_during_build")
    return result


def _relation_header(relations):
    indexed._closed(relations, {"version", "contract", "binding", "scope_ref", "hypotheses_ref", "index_ref",
        "analysis_span", "logical_universe", "origin_inventory", "type_inventory", "catalog_inventory", "keys",
        "key_types", "key_inventory", "kernels", "target_relations", "target_type_universe", "key_projections",
        "path_groups", "resource_limits", "status", "reasons", "summary", "selected", "rank", "confidence", "flags",
        "analysis_scope", "profiles_endpoints_motion_and_bundles", "resource_limit_semantics", "validation_semantics",
        "limits", "record_id", "record_sha256"}, "function_relations")
    indexed._closed(relations["resource_limits"], {"max_kernels"}, "relation_limits")
    _limit(relations["resource_limits"]["max_kernels"], "max_kernels")
    for name in ("origin_inventory", "type_inventory", "catalog_inventory", "keys", "key_types",
                 "key_inventory", "kernels", "target_relations", "key_projections", "path_groups", "reasons", "limits"):
        if type(relations[name]) is not list:
            raise ValueError("literal_relation_list_inventory_required:" + name)


def _check_relations(scope, index, relations):
    _relation_header(relations)
    frozen._check(relations, PREFIX)
    expected = _seal(_body(scope, index, **relations["resource_limits"]), PREFIX)
    if not _same(relations, expected):
        raise ValueError("stale_foreign_modified_or_promoting_function_relations")
    return True


def validate_relations(ir, scope, hypotheses, index, relations):
    _relation_header(relations)
    owned, before, contract = _owned(ir, scope, hypotheses, index, relations)
    _check_relations(owned[1], owned[3], owned[4])
    if before != digest([ir, scope, hypotheses, index, relations]) or not _same(contract, _contract()):
        raise ValueError("relation_inputs_or_current_code_changed_during_validation")
    return True


class _PreparedRelations:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _SessionState:
    data: object
    lookups: object
    contract_sha256: str
    authentication: bytes


def _authentication(handle, state):
    return hmac.digest(_SECRET, indexed._encoded([id(handle), id(state), id(state.data),
        id(state.lookups), state.contract_sha256]), "sha256")


def _session(handle):
    if type(handle) is not _PreparedRelations or handle not in _SESSIONS:
        raise ValueError("internally_issued_prepared_relations_required")
    state = _SESSIONS[handle]
    if (type(state) is not _SessionState or not isinstance(state.data, MappingProxyType)
            or not isinstance(state.lookups, MappingProxyType) or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _authentication(handle, state))):
        raise ValueError("prepared_relations_contract_or_owned_state_changed")
    return state


def prepare_relations(ir, scope, hypotheses, index, relations):
    _relation_header(relations)
    owned, before, contract = _owned(ir, scope, hypotheses, index, relations)
    _check_relations(owned[1], owned[3], owned[4])
    # Every lookup comes from the SAME validated owned copy, never caller aliases.
    data = indexed._freeze(owned[4])
    lookup = {}
    for name, field in (("origins", "origin_inventory"), ("types", "type_inventory"),
                        ("kernels", "kernels"), ("targets", "target_relations"),
                        ("projections", "key_projections"), ("keys", "keys")):
        lookup[name] = {(row["variant_id"] if name == "origins" else row["record_id"]): i
                        for i, row in enumerate(data[field])}
    lookup["groups"] = {row["group_id"]: i for i, row in enumerate(data["path_groups"])}
    lookup["key_inventory"] = {row["key_ref"]["record_id"]: i for i, row in enumerate(data["key_inventory"])}
    lookup["source_kernels"] = {(row["source_type_ref"]["record_id"], row["family"], row["quality"]): row["record_id"]
                                for row in data["kernels"]}
    if before != digest([ir, scope, hypotheses, index, relations]) or not _same(contract, _contract()):
        raise ValueError("relation_inputs_or_current_code_changed_during_prepare")
    handle = _PreparedRelations()
    state = _SessionState(data, indexed._freeze(lookup), digest(_contract()), b"")
    object.__setattr__(state, "authentication", _authentication(handle, state))
    _SESSIONS[handle] = state
    return handle


def _selector_types(slot_index, family, quality):
    if type(slot_index) is not int or slot_index < 0:
        raise ValueError("explicit_nonnegative_integer_function_slot_required")
    if type(family) is not str or family not in frozen.FAMILIES or type(quality) is not str or quality not in ("M", "m"):
        raise ValueError("declared_function_family_and_target_quality_required")


def _arguments(state, group_id, variant_ids, key_id, slot_index, family, quality):
    _selector_types(slot_index, family, quality)
    if type(group_id) is not str or group_id not in state.lookups["groups"]:
        raise ValueError("foreign_or_unknown_relation_group")
    if type(key_id) is not str or key_id not in state.lookups["keys"]:
        raise ValueError("foreign_or_unknown_relation_key")
    if not isinstance(variant_ids, (list, tuple)) or any(type(ref) is not str for ref in variant_ids):
        raise ValueError("ordered_explicit_relation_variant_tuple_required")
    group = state.data["path_groups"][state.lookups["groups"][group_id]]
    if len(variant_ids) != len(group["slots"]) or len(set(variant_ids)) != len(variant_ids):
        raise ValueError("complete_unique_ordered_relation_variant_tuple_required")
    for ref, slot in zip(variant_ids, group["slots"]):
        if ref not in slot["variant_ids"]:
            raise ValueError("foreign_variant_or_wrong_relation_partition_slot")
    if slot_index >= len(group["slots"]):
        raise ValueError("explicit_valid_integer_function_slot_required")
    return group


def query_function_prepared(session, group_id, variant_ids, key_id, slot_index, family, quality):
    state = _session(session)
    group = _arguments(state, group_id, variant_ids, key_id, slot_index, family, quality)
    data = state.data
    key = data["keys"][state.lookups["keys"][key_id]]
    logical = _seal({"version": VERSION, "relations_ref": _ref(data), "index_ref": indexed._thaw(data["index_ref"]),
        "group_id": group_id, "relation_group_id": group["relation_group_id"],
        "partition": indexed._thaw(group["partition"]), "variant_ids": list(variant_ids),
        "key_ref": _ref(key), "semantics": "exact_logical_tuple_not_a_materialized_legacy_path"}, "fmftuple_")
    body = {"version": VERSION, "contract": _contract(), "relations_ref": _ref(data),
        "index_ref": indexed._thaw(data["index_ref"]), "scope_ref": indexed._thaw(data["scope_ref"]),
        "symbolic_universe_ref": _ref(data["logical_universe"]), "tuple_ref": _ref(logical), "logical_tuple": logical,
        "group_id": group_id, "variant_ids": list(variant_ids), "key_ref": _ref(key),
        "slot_index": slot_index, "family": family, "quality": quality,
        "source_type_ref": None, "target_type_ref": None, "kernel_ref": None,
        "target_relation_ref": None, "key_projection_ref": None,
        "function": None, "computed_function_rows": 0,
        "logical_function_rows": group["logical_function_count"],
        "status": "withheld_relation_group", "reasons": indexed._thaw(group["reasons"]),
        "profiles_endpoints_motion_and_bundles": "unassessed", "selected": None, "rank": None, "confidence": None,
        "flags": _flags()}
    if group["status"] == "ready_function_shape_relations":
        origins = [data["origin_inventory"][state.lookups["origins"][ref]] for ref in variant_ids]
        if any(row["variant_id"] != ref for row, ref in zip(origins, variant_ids)):
            raise ValueError("owned_origin_lookup_identity_mismatch")
        source = origins[slot_index]
        target = origins[slot_index + 1] if slot_index + 1 < len(origins) else None
        kernel_id = state.lookups["source_kernels"][(source["type_ref"]["record_id"], family, quality)]
        kernel = data["kernels"][state.lookups["kernels"][kernel_id]]
        relation = data["target_relations"][state.lookups["targets"][kernel["target_relation_ref"]["record_id"]]]
        key_info = data["key_inventory"][state.lookups["key_inventory"][key_id]]
        projection_ref = kernel["key_projection_refs"][key_info["key_type_ref"]["record_id"]]
        projection = data["key_projections"][state.lookups["projections"][projection_ref["record_id"]]]
        function = indexed._thaw(kernel["source_template"])
        blockers = list(kernel["source_blockers"])
        compatible, actual_root, actual_members = None, None, None
        if target is None:
            blockers.append("following_target_segment_not_observed")
        else:
            target_type = data["type_inventory"][state.lookups["types"][target["type_ref"]["record_id"]]]
            semantic = target_type["semantic"]
            actual_root, actual_members = indexed._thaw(semantic["root"]), indexed._thaw(semantic["members"])
            if actual_root is None or actual_members is None:
                blockers.append("following_target_spelling_unresolved")
            else:
                blockers.extend("target:" + reason for reason in semantic["blockers"])
                if function["derived_target_root"] is not None:
                    compatible = target_type["record_id"] in relation["true_type_ids"]
                    if not compatible:
                        blockers.append("following_target_triad_core_mismatch")
        function.update(source_segment_ref=source["segment_ref"], source_span=indexed._thaw(source["span"]),
            target_segment_ref=None if target is None else target["segment_ref"],
            target_span=None if target is None else indexed._thaw(target["span"]),
            actual_target_root=actual_root, actual_target_members=actual_members,
            target_shape_compatible=compatible, function_kind=projection["function_kind"],
            key_segment_ref=key_info["key_segment_ref"], key_projection=indexed._thaw(projection["key_projection"]),
            status="conditional_function_shape" if not blockers else "withheld", blockers=sorted(set(blockers)))
        body.update(source_type_ref=indexed._thaw(source["type_ref"]),
            target_type_ref=None if target is None else indexed._thaw(target["type_ref"]),
            kernel_ref=_ref(kernel), target_relation_ref=_ref(relation), key_projection_ref=indexed._thaw(projection_ref),
            function=function, computed_function_rows=1, status="computed_pure_function_shape_not_literal_harmony", reasons=[])
    result = _seal(body, QUERY_PREFIX)
    _session(session)
    return result


def query_function(ir, scope, hypotheses, index, relations, group_id, variant_ids, key_id, slot_index, family, quality):
    _selector_types(slot_index, family, quality)
    session = prepare_relations(ir, scope, hypotheses, index, relations)
    return query_function_prepared(session, group_id, variant_ids, key_id, slot_index, family, quality)


def validate_function(ir, scope, hypotheses, index, relations, group_id, variant_ids, key_id, slot_index, family, quality, result):
    _selector_types(slot_index, family, quality)
    frozen._check(result, QUERY_PREFIX)
    if not _same(result, query_function(ir, scope, hypotheses, index, relations,
            group_id, variant_ids, key_id, slot_index, family, quality)):
        raise ValueError("stale_foreign_modified_or_promoting_function_relation_query")
    return True
