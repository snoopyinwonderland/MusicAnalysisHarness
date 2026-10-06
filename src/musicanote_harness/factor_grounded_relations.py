"""Literal profile grounding and joint DIRECT motion, never musical verdicts.

Every stored origin and logical denominator survives.  Exact-value interning
shares literal profile rows/cells without constructing Cartesian paths. Only
conditional function-shape pairs enter direct endpoint compilation; their
false/unknown/terminal complement remains explicitly motion-unassessed.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import hmac
from itertools import product
import math
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_function_relations as relations_engine
from . import factor_indexed_hypotheses as indexed
from . import factor_expanded_hypotheses as frozen
from .musical_pattern_observation import digest, f, span_bounds

VERSION = "factor-grounded-relations-0.1.0"
PREFIX = "fmgr_"
PROFILE_PREFIX = "fmgrprofile_"
ROW_PREFIX = "fmgrrow_"
CELL_PREFIX = "fmgrcell_"
MOTION_PREFIX = "fmgrmotion_"
BUNDLE_PREFIX = "fmgrbundle_"
QUERY_PREFIX = "fmgrquery_"
ASSESSMENT_PREFIX = "fmgrassess_"
_SESSIONS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)
_PROFILE_ORIGIN_FIELDS = ("segment_ref", "missing_spellings", "missing_pitch_classes", "supplier_event_states")
_CAPS = ("max_profiles", "max_motion_kernels", "max_motion_pairs", "max_joint_options")


def _flags():
    return {**indexed._flags(), "nct_evaluated": False,
        "same_pitch_delayed_resolution_evaluated": False,
        "literal_membership_is_harmony_certification": False,
        "joint_direct_motion_is_function_certification": False,
        "independent_witnesses_unioned": False}


def _contract():
    return {"version": VERSION,
        "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "relations_contract": relations_engine._contract()}


def _seal(body, prefix):
    return frozen._seal(body, prefix)


def _ref(record):
    return frozen._ref(record)


def _caps(values):
    for name in _CAPS:
        indexed._integer(values[name], name)


def _inputs(ir, scope, hypotheses, index, relations, grounding=None):
    inputs = [ir, scope, hypotheses, index, relations] + ([] if grounding is None else [grounding])
    before, contract = digest(inputs), _contract()
    owned = deepcopy(inputs)
    indexed._check_index_lineage(*owned[:4])
    relations_engine._check_relations(owned[1], owned[3], owned[4])
    if before != digest(inputs) or not indexed._same(contract, _contract()):
        raise ValueError("grounding_inputs_or_current_code_changed_during_owned_validation")
    return owned, before, contract


def _profile_plan(scope, index):
    representatives = {}
    for item in index["variant_inventory"]:
        representatives.setdefault(item["profile_ref"]["record_id"], item["variant"])
    rows, cells = 0, 0
    for descriptor in index["profile_inventory"]:
        variant = representatives[descriptor["record_id"]]
        a, b = span_bounds(variant["span"])
        times = {a, b}
        for sound in scope["sound_facts"]:
            if sound["point"]:
                continue
            x, y = span_bounds(sound["span"])
            if x < b and y > a:
                rows += 1
                times.update((max(a, x), min(b, y)))
        cells += len(times) - 1
    return representatives, rows, cells


def _profiles(scope, index, representatives, hold):
    profiles, rows, cells = [], [], []
    row_by_value, cell_by_value = {}, {}
    row_uses = cell_uses = 0
    if hold:
        return profiles, rows, cells, row_uses, cell_uses
    for descriptor in index["profile_inventory"]:
        variant = representatives[descriptor["record_id"]]
        profile = frozen._profile(scope, variant)
        interned = []
        for field, prefix, inventory, memo in (("rows", ROW_PREFIX, rows, row_by_value),
                                                ("cells", CELL_PREFIX, cells, cell_by_value)):
            ids = []
            for value in profile[field]:
                checksum = digest(value)
                record = memo.get(checksum)
                if record is None:
                    record = _seal({"version": VERSION, "scope_ref": _ref(scope),
                        "value": deepcopy(value)}, prefix)
                    memo[checksum] = record
                    inventory.append(record)
                ids.append(record["record_id"])
            interned.append(ids)
        row_uses += len(profile["rows"])
        cell_uses += len(profile["cells"])
        core = {k: deepcopy(v) for k, v in profile.items()
                if k not in (*_PROFILE_ORIGIN_FIELDS, "rows", "cells")}
        profiles.append(_seal({"version": VERSION, "descriptor_ref": _ref(descriptor),
            "semantic_input": deepcopy(descriptor["semantic_input"]), "profile_core": core,
            "row_ids": interned[0], "cell_ids": interned[1],
            "status": "computed_literal_profile_not_harmony", "flags": _flags()}, PROFILE_PREFIX))
    return profiles, rows, cells, row_uses, cell_uses


def _restore_profile(profile, variant, rows, cells):
    result = deepcopy(profile["profile_core"])
    result.update(rows=[deepcopy(rows[rid]["value"]) for rid in profile["row_ids"]],
        cells=[deepcopy(cells[rid]["value"]) for rid in profile["cell_ids"]],
        segment_ref=variant["segment_id"],
        missing_spellings=deepcopy(variant["missing_spellings"]),
        missing_pitch_classes=deepcopy(variant["missing_pitch_classes"]),
        supplier_event_states=deepcopy(variant["supplier_event_states"]))
    return result


def _motion_specs(index, relations):
    origins = {o["variant_id"]: o for o in relations["origin_inventory"]}
    catalog_types, representatives = defaultdict(lambda: defaultdict(list)), {}
    for row in index["variant_inventory"]:
        tid = origins[row["variant_id"]]["type_ref"]["record_id"]
        key = (row["catalog_id"], tid)
        catalog_types[row["catalog_id"]][tid].append(row["variant_id"])
        representatives.setdefault(key, row)
    catalogs = {c["catalog_id"]: c for c in relations["catalog_inventory"]}
    targets = {t["record_id"]: t for t in relations["target_relations"]}
    source_kernels = defaultdict(list)
    for kernel in relations["kernels"]:
        source_kernels[kernel["source_type_ref"]["record_id"]].append(kernel)
    specs = []
    unknown = any(g["status"] != "ready_function_shape_relations"
                  and g["logical_function_count"] != 0 for g in relations["path_groups"])
    for group in relations["path_groups"]:
        if group["status"] != "ready_function_shape_relations" or len(group["slots"]) != 2:
            continue
        source_cat, target_cat = [catalogs[s["catalog_id"]] for s in group["slots"]]
        target_weights = {w["type_id"]: w["origin_count"] for w in target_cat["type_weights"]}
        for weight in source_cat["type_weights"]:
            for kernel in source_kernels[weight["type_id"]]:
                if kernel["source_template"]["shape_compatible"] is not True or kernel["source_blockers"]:
                    continue
                relation = targets[kernel["target_relation_ref"]["record_id"]]
                for target_type in relation["clean_true_type_ids"]:
                    if not target_weights.get(target_type):
                        continue
                    source = representatives[(source_cat["catalog_id"], weight["type_id"])]
                    target = representatives[(target_cat["catalog_id"], target_type)]
                    n = weight["origin_count"] * target_weights[target_type]
                    specs.append({"group_id": group["group_id"],
                        "source_catalog_id": source_cat["catalog_id"], "target_catalog_id": target_cat["catalog_id"],
                        "source_type_ref": deepcopy(kernel["source_type_ref"]),
                        "target_type_ref": deepcopy(origins[target["variant_id"]]["type_ref"]),
                        "source_profile_ref": deepcopy(source["profile_ref"]),
                        "target_profile_ref": deepcopy(target["profile_ref"]),
                        "source_representative_variant_ref": _ref(source["variant"]),
                        "target_representative_variant_ref": _ref(target["variant"]),
                        "source_variant_ids": list(catalog_types[source_cat["catalog_id"]][weight["type_id"]]),
                        "target_variant_ids": list(catalog_types[target_cat["catalog_id"]][target_type]),
                        "shape_kernel_ref": _ref(kernel), "family": kernel["family"], "quality": kernel["quality"],
                        "origin_multiplicity": n, "key_multiplicity": len(relations["keys"]),
                        "weighted_function_rows": n * len(relations["keys"])})
    return specs, representatives, unknown


def _universe(scope, index, relations):
    return _seal({"version": VERSION, "scope_ref": _ref(scope), "index_ref": _ref(index),
        "relations_ref": _ref(relations), "indexed_universe_ref": _ref(index["universe"]),
        "logical_paths": index["universe"]["logical_paths"],
        "logical_tuples": index["universe"]["logical_tuples"],
        "logical_function_rows": relations["summary"]["logical_function_rows"],
        "unknown_product_groups": index["universe"]["unknown_product_groups"],
        "representation": "all_original_catalogue_products_keys_and_function_slots_not_materialized_paths",
        "flags": _flags()}, "fmgruniverse_")


def _bundle(scope, index, relations, universe, required=()):
    legacy = frozen._bundle(scope, [], relations["keys"], required)
    body = {k: deepcopy(v) for k, v in legacy.items() if k not in
            ("version", "record_id", "record_sha256", "comparison_path_refs", "comparison_key_refs", "flags")}
    body.update(version=VERSION, contract=_contract(), index_ref=_ref(index),
        relations_ref=_ref(relations), symbolic_universe_ref=_ref(universe),
        comparison_key_refs=[_ref(k) for k in relations["keys"]],
        comparison_path_representation="all_grounded_symbolic_catalogue_products_not_empty_legacy_registry",
        geometry_condition_status=("possible" if legacy["status"] == "complete_all_lane_witness" else
            "impossible" if any(entry["query"]["status"] in ("exact_count", "unsatisfiable_constraints")
                and entry["query"]["possible_assignments"] == "0" for entry in legacy["entries"]) else "unknown"),
        conditional_NCT_and_delayed_resolution="unassessed", flags=_flags())
    return _seal(body, BUNDLE_PREFIX)


def _links(bundle):
    return {tuple(pair) for entry in bundle["entries"] if entry["witness"] is not None
            for pair in entry["witness"]["assignment"]["links"]}


def _motion(scope, spec, source, target, profiles, key_segment, baseline, make_bundle, caps):
    body = {"version": VERSION, **deepcopy(spec), "edge_options": {},
        "planned_endpoint_pairs": None, "planned_joint_options": None, "supported_joint_options": None, "joint_options": [],
        "qualifying_bundle_refs": [], "baseline_bundle_ref": _ref(baseline),
        "status": "unassessed", "blockers": [], "motion_kernel_computed": False,
        "conditional_NCT_and_delayed_resolution": "unassessed", "flags": _flags()}
    function = frozen._function(scope, source, target, key_segment, spec["family"], spec["quality"])
    # The real first declared key supplies this pure function body. Direct
    # motion reads no key field; original key bodies are restored at query.
    options, blockers, pairs, held = frozen._motion_options(scope, function, source, target,
        profiles, caps["max_motion_pairs"])
    body.update(edge_options=options, planned_endpoint_pairs=pairs,
        blockers=blockers, motion_kernel_computed=True)
    if held:
        body["status"] = "whole_endpoint_motion_budget_abstention"
        return body
    qualified = [[edge for edge in edges if edge["qualified"]] for edges in options.values()]
    count = math.prod(len(edges) for edges in qualified)
    body["planned_joint_options"] = count
    if count > caps["max_joint_options"]:
        body.update(status="whole_joint_motion_budget_abstention",
            blockers=sorted(set(blockers + ["complete_joint_direct_motion_product_exceeds_budget_no_prefix"])))
    elif blockers:
        body.update(status="withheld_direct_motion_prerequisites", supported_joint_options=0)
    else:
        unknown = False
        for edges in product(*qualified):
            required = tuple(sorted({tuple(edge["required_link"]) for edge in edges}))
            bundle = make_bundle(required)
            complete = bundle["status"] == "complete_all_lane_witness"
            unknown |= bundle["geometry_condition_status"] == "unknown"
            body["joint_options"].append({"required_links": [list(pair) for pair in required],
                "bundle_ref": _ref(bundle), "status": "conditional_joint_direct_motion_shape" if complete else
                    "incompatible_joint_required_links" if bundle["geometry_condition_status"] == "impossible" else "unassessed_complete_bundle",
                "blockers": deepcopy(bundle["reasons"]), "critical_roles": list(options),
                "all_critical_roles_in_same_complete_bundle": complete})
            if complete:
                body["qualifying_bundle_refs"].append(_ref(bundle))
        if unknown:
            body.update(status="whole_joint_completion_abstention", blockers=sorted(set(
                blockers + ["one_or_more_complete_lane_bundle_queries_withheld_no_partial_success"])))
        elif body["qualifying_bundle_refs"]:
            body.update(status="conditional_joint_direct_motion_shape", supported_joint_options=len(body["qualifying_bundle_refs"]))
        else:
            body.update(status="withheld_joint_direct_motion", supported_joint_options=0)
    return body


def _kernel_partition(kernel):
    if kernel["status"] == "conditional_joint_direct_motion_shape":
        return "conditional"
    if kernel["status"] in ("withheld_direct_motion_prerequisites", "withheld_joint_direct_motion"):
        return "withheld"
    return "unassessed"


def _incidence(kernel, bundle):
    links = _links(bundle)
    matched = {role: [deepcopy(edge["required_link"]) for edge in edges
                     if edge["qualified"] and tuple(edge["required_link"]) in links]
               for role, edges in kernel["edge_options"].items()}
    complete = bundle["status"] == "complete_all_lane_witness"
    if _kernel_partition(kernel) == "unassessed" or bundle["geometry_condition_status"] == "unknown":
        status = "unassessed_under_existing_bundle"
    elif not complete:
        status = "not_satisfied_incompatible_existing_bundle_not_musical_absence"
    elif kernel["blockers"]:
        status = "withheld_direct_motion_prerequisites_under_existing_bundle"
    elif matched and all(matched.values()):
        status = "conditional_joint_direct_motion_under_existing_bundle"
    else:
        status = "not_satisfied_under_this_bundle_not_global_absence"
    return status, matched


def _body(scope, index, relations, caps):
    representatives, planned_rows, planned_cells = _profile_plan(scope, index)
    descriptor_inventory_complete = (index["status"] != "whole_index_budget_hold"
        and relations["summary"]["unknown_supplier_catalogs"] == 0)
    profile_hold = len(index["profile_inventory"]) > caps["max_profiles"]
    profiles, rows, cells, row_uses, cell_uses = _profiles(scope, index, representatives, profile_hold)
    if not profile_hold and (row_uses != planned_rows or cell_uses != planned_cells):
        raise ValueError("grounded_literal_profile_use_denominator_mismatch")
    profile_map = {p["descriptor_ref"]["record_id"]: p for p in profiles}
    row_map, cell_map = ({r["record_id"]: r for r in inventory} for inventory in (rows, cells))
    specs, variant_representatives, unknown_motion_plan = _motion_specs(index, relations)
    motion_hold = len(specs) > caps["max_motion_kernels"]
    universe = _universe(scope, index, relations)
    bundles, baseline = {}, None
    def make_bundle(required):
        if required not in bundles:
            bundles[required] = _bundle(scope, index, relations, universe, required)
        return bundles[required]
    if not profile_hold and not motion_hold and descriptor_inventory_complete and not unknown_motion_plan:
        baseline = make_bundle(())
    kernels = []
    for spec in specs:
        if profile_hold or motion_hold or baseline is None:
            reason = "whole_literal_profile_inventory_exceeds_budget_no_prefix" if profile_hold else "whole_positive_motion_kernel_inventory_exceeds_budget_no_prefix" if motion_hold else "source_profile_or_relation_inventory_not_complete"
            body = {"version": VERSION, **deepcopy(spec), "edge_options": {},
                "planned_endpoint_pairs": None, "planned_joint_options": None, "supported_joint_options": None, "joint_options": [],
                "qualifying_bundle_refs": [], "baseline_bundle_ref": None,
                "status": "whole_profile_budget_abstention" if profile_hold else "whole_motion_kernel_budget_abstention" if motion_hold else "source_inventory_abstention",
                "blockers": [reason], "motion_kernel_computed": False,
                "conditional_NCT_and_delayed_resolution": "unassessed", "flags": _flags()}
        else:
            source = variant_representatives[(spec["source_catalog_id"], spec["source_type_ref"]["record_id"])]["variant"]
            target = variant_representatives[(spec["target_catalog_id"], spec["target_type_ref"]["record_id"])]["variant"]
            ps = []
            for descriptor in (spec["source_profile_ref"], spec["target_profile_ref"]):
                profile = profile_map[descriptor["record_id"]]
                ps.append({"cells": [deepcopy(cell_map[profile["cell_ids"][0]]["value"]),
                                     deepcopy(cell_map[profile["cell_ids"][-1]]["value"])]})
            body = _motion(scope, spec, source, target, ps, relations["keys"][0]["segments"][0], baseline, make_bundle, caps)
        kernels.append(_seal(body, MOTION_PREFIX))
    weighted, by_group = Counter(), defaultdict(Counter)
    for kernel in kernels:
        state = _kernel_partition(kernel)
        weighted[state] += kernel["weighted_function_rows"]
        by_group[kernel["group_id"]][state] += kernel["weighted_function_rows"]
    groups = []
    for old in relations["path_groups"]:
        n = old["logical_function_count"]
        known = by_group[old["group_id"]]
        conditional, withheld = known["conditional"], known["withheld"]
        unassessed = None if n is None else n - conditional - withheld
        groups.append({**deepcopy(old), "grounding_counts": {
            "logical_function_rows": n, "conditional_direct_motion_shape_rows": conditional,
            "withheld_direct_motion_rows": withheld, "unassessed_direct_motion_rows": unassessed},
            "direct_motion_complement": "false_unknown_terminal_and_blocked_function_assumptions_unassessed_not_false",
            "conditional_NCT_and_delayed_resolution": "unassessed"})
    assessments = []
    for bundle in bundles.values():
        compatible, totals = [], Counter()
        for kernel in kernels:
            status, matched = _incidence(kernel, bundle)
            state = "conditional" if status == "conditional_joint_direct_motion_under_existing_bundle" else "unassessed" if status == "unassessed_under_existing_bundle" else "withheld"
            totals[state] += kernel["weighted_function_rows"]
            if state == "conditional":
                compatible.append(_ref(kernel))
        logical = relations["summary"]["logical_function_rows"]
        assessments.append({"bundle_ref": _ref(bundle), "symbolic_universe_ref": _ref(universe),
            "same_complete_bundle_for_all_competing_function_assumptions": bundle["status"] == "complete_all_lane_witness",
            "compatible_motion_kernel_refs": compatible, "logical_function_rows": logical,
            "conditional_direct_motion_shape_rows": totals["conditional"],
            "withheld_direct_motion_rows": totals["withheld"],
            "unassessed_direct_motion_rows": logical - totals["conditional"] - totals["withheld"],
            "assessed_motion_kernels": len(kernels),
            "link_basis": "actual_materialized_links_of_this_one_complete_all_lane_bundle",
            "unassessed_complement": "all_false_unknown_terminal_blocked_function_assumptions_and_resource_holds",
            "selected": None})
    reasons = []
    if profile_hold: reasons.append("whole_literal_profile_inventory_exceeds_budget_no_prefix")
    if motion_hold: reasons.append("whole_positive_motion_kernel_inventory_exceeds_budget_no_prefix")
    if unknown_motion_plan: reasons.append("source_relation_function_inventory_not_fully_assessed")
    if not descriptor_inventory_complete: reasons.append("source_profile_descriptor_inventory_not_complete")
    reasons.extend(reason for kernel in kernels if _kernel_partition(kernel) == "unassessed" for reason in kernel["blockers"])
    logical = relations["summary"]["logical_function_rows"]
    summary = {"origin_variants": len(relations["origin_inventory"]),
        "planned_profiles": len(index["profile_inventory"]) if descriptor_inventory_complete else None,
        "known_stored_profile_descriptors": len(index["profile_inventory"]), "literal_profiles_computed": len(profiles),
        "planned_profile_row_uses": planned_rows if descriptor_inventory_complete else None,
        "planned_profile_cell_uses": planned_cells if descriptor_inventory_complete else None,
        "known_profile_row_use_subtotal": planned_rows, "known_profile_cell_use_subtotal": planned_cells,
        "literal_profile_row_uses": row_uses, "literal_profile_cell_uses": cell_uses,
        "normalized_profile_rows": len(rows), "normalized_profile_cells": len(cells),
        "planned_motion_kernels": None if unknown_motion_plan else len(specs),
        "known_positive_motion_kernel_descriptors": len(specs),
        "motion_kernels_computed": sum(k["motion_kernel_computed"] for k in kernels),
        "actual_endpoint_pairs_computed": sum(k["planned_endpoint_pairs"] for k in kernels
            if k["planned_endpoint_pairs"] is not None and k["status"] != "whole_endpoint_motion_budget_abstention"),
        "planned_endpoint_pair_subtotal": sum(k["planned_endpoint_pairs"] or 0 for k in kernels),
        "unknown_endpoint_pair_kernels": sum(k["planned_endpoint_pairs"] is None for k in kernels),
        "planned_joint_options": sum(k["planned_joint_options"] or 0 for k in kernels),
        "unknown_joint_option_kernels": sum(k["planned_joint_options"] is None for k in kernels),
        "joint_options_computed": sum(len(k["joint_options"]) for k in kernels),
        "supported_joint_option_subtotal": sum(k["supported_joint_options"] or 0 for k in kernels),
        "unknown_joint_support_kernels": sum(k["supported_joint_options"] is None for k in kernels),
        "completion_bundles_computed": len(bundles),
        "same_bundle_assessments_computed": sum(a["assessed_motion_kernels"] for a in assessments),
        "logical_paths": index["universe"]["logical_paths"],
        "logical_path_key_tuples": index["universe"]["logical_tuples"],
        "logical_function_rows": logical, "unknown_product_groups": index["universe"]["unknown_product_groups"],
        "unknown_supplier_catalogs": relations["summary"]["unknown_supplier_catalogs"],
        "shape_conditional_function_rows": relations["summary"]["conditional_function_shape_rows"],
        "shape_withheld_function_rows": relations["summary"]["withheld_function_shape_rows"],
        "motion_ineligible_function_prerequisite_rows": relations["summary"]["withheld_function_shape_rows"],
        "grounded_conditional_direct_motion_shape_rows": weighted["conditional"],
        "grounded_withheld_direct_motion_rows": weighted["withheld"],
        "unassessed_direct_motion_rows": logical - weighted["conditional"] - weighted["withheld"],
        "terminal_target_rows": relations["summary"]["terminal_target_rows"],
        "literal_profiles_complete": descriptor_inventory_complete and not profile_hold,
        "positive_motion_kernel_inventory_complete": not unknown_motion_plan and all(_kernel_partition(k) != "unassessed" for k in kernels),
        "conditional_NCT_rules_computed": 0, "delayed_resolution_chains_computed": 0,
        "queried_logical_tuples": 0,
        "motion_kernel_status_counts": dict(Counter(k["status"] for k in kernels))}
    return {"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "hypotheses_ref": deepcopy(index["hypotheses_ref"]),
        "index_ref": _ref(index), "relations_ref": _ref(relations),
        "analysis_span": deepcopy(scope["analysis_span"]), "logical_universe": universe,
        "origin_inventory": deepcopy(relations["origin_inventory"]),
        "catalog_inventory": deepcopy(relations["catalog_inventory"]), "keys": deepcopy(relations["keys"]),
        "source_inventory": [_seal({"version": VERSION, "scope_ref": _ref(scope), "sound": deepcopy(s)}, "fmgrsource_") for s in scope["sound_facts"]],
        "profile_inventory": profiles, "row_inventory": rows, "cell_inventory": cells,
        "motion_kernel_inventory": kernels, "bundle_inventory": list(bundles.values()),
        "same_bundle_assessments": assessments, "baseline_bundle_ref": None if baseline is None else _ref(baseline),
        "path_groups": groups, "parent_summary": deepcopy(relations["summary"]),
        "resource_limits": deepcopy(caps), "summary": summary,
        "status": "whole_profile_budget_abstention" if profile_hold else "whole_motion_kernel_budget_abstention" if motion_hold else "grounded_relations_with_holds" if reasons else "ready_grounded_relations",
        "reasons": sorted(set(reasons)), "selected": None, "rank": None, "confidence": None,
        "flags": _flags(), "conditional_NCT_and_delayed_resolution": "unassessed",
        "resource_limit_semantics": "whole_descriptor_and_positive_kernel_inventories_then_whole_per_kernel_endpoint_and_joint_products_not_byte_RSS_or_lifetime_caps",
        "normalization_semantics": "exact_value_interned_profile_rows_and_cells_with_exact_descriptor_order_and_per_origin_restoration",
        "validation_semantics": "fresh_full_IR_scope_and_intrinsic_frozen_parent_replay_not_optional_supplier_regeneration_or_parent_file_authority",
        "limits": ["Raw note-time membership is not NCT, consonance or confirmed harmony.",
            "Only conditional function-shape pairs have direct-motion kernels; false/unknown/terminal complements remain unassessed.",
            "Each LT/seventh conjunction uses one complete all-raw-lane bundle; independent witnesses are never combined.",
            "A failed direct boundary prerequisite does not establish absence of delayed or embellished resolution.",
            "NCT, delayed carries, actual harmony identity, cadence and final key/function remain unassessed."]}


def build_grounding(ir, scope, hypotheses, index, relations, *, max_profiles=65536,
                    max_motion_kernels=65536, max_motion_pairs=65536, max_joint_options=65536):
    caps = dict(zip(_CAPS, (max_profiles, max_motion_kernels, max_motion_pairs, max_joint_options)))
    _caps(caps)
    owned, before, contract = _inputs(ir, scope, hypotheses, index, relations)
    result = _seal(_body(owned[1], owned[3], owned[4], caps), PREFIX)
    if before != digest([ir, scope, hypotheses, index, relations]) or not indexed._same(contract, _contract()):
        raise ValueError("grounding_inputs_or_current_code_changed_during_build")
    return result


def _header(grounding):
    indexed._closed(grounding, {"version", "contract", "binding", "scope_ref", "hypotheses_ref", "index_ref",
        "relations_ref", "analysis_span", "logical_universe", "origin_inventory", "catalog_inventory", "keys",
        "source_inventory", "profile_inventory", "row_inventory", "cell_inventory", "motion_kernel_inventory",
        "bundle_inventory", "same_bundle_assessments", "baseline_bundle_ref", "path_groups", "parent_summary",
        "resource_limits", "summary", "status", "reasons", "selected", "rank", "confidence", "flags",
        "conditional_NCT_and_delayed_resolution", "resource_limit_semantics", "normalization_semantics",
        "validation_semantics", "limits", "record_id", "record_sha256"}, "grounded_relations")
    indexed._closed(grounding["resource_limits"], set(_CAPS), "grounding_limits")
    _caps(grounding["resource_limits"])
    for name in ("origin_inventory", "catalog_inventory", "keys", "source_inventory", "profile_inventory",
                 "row_inventory", "cell_inventory", "motion_kernel_inventory", "bundle_inventory",
                 "same_bundle_assessments", "path_groups", "reasons", "limits"):
        if type(grounding[name]) is not list:
            raise ValueError("literal_grounding_list_required:" + name)


def _check_grounding(scope, index, relations, grounding):
    _header(grounding)
    frozen._check(grounding, PREFIX)
    expected = _seal(_body(scope, index, relations, grounding["resource_limits"]), PREFIX)
    if not indexed._same(expected, grounding):
        raise ValueError("stale_foreign_modified_or_promoting_grounded_relations")
    return True


def validate_grounding(ir, scope, hypotheses, index, relations, grounding):
    _header(grounding)
    owned, before, contract = _inputs(ir, scope, hypotheses, index, relations, grounding)
    _check_grounding(owned[1], owned[3], owned[4], owned[5])
    if before != digest([ir, scope, hypotheses, index, relations, grounding]) or not indexed._same(contract, _contract()):
        raise ValueError("grounding_inputs_or_current_code_changed_during_validation")
    return True


class _PreparedGrounding:
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
    if type(handle) is not _PreparedGrounding or handle not in _SESSIONS:
        raise ValueError("internally_issued_prepared_grounding_required")
    state = _SESSIONS[handle]
    if (type(state) is not _SessionState or not isinstance(state.data, MappingProxyType)
            or not isinstance(state.lookups, MappingProxyType) or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _authentication(handle, state))):
        raise ValueError("prepared_grounding_contract_or_owned_state_changed")
    return state


def prepare_grounding(ir, scope, hypotheses, index, relations, grounding):
    _header(grounding)
    owned, before, contract = _inputs(ir, scope, hypotheses, index, relations, grounding)
    _check_grounding(owned[1], owned[3], owned[4], owned[5])
    data = indexed._freeze({"index": owned[3], "relations": owned[4], "grounding": owned[5]})
    lookup = {}
    for name, field, parent in (("variants", "variant_inventory", "index"), ("groups", "path_groups", "grounding"),
            ("keys", "keys", "index"), ("profiles", "profile_inventory", "grounding"),
            ("rows", "row_inventory", "grounding"), ("cells", "cell_inventory", "grounding"),
            ("bundles", "bundle_inventory", "grounding"), ("origins", "origin_inventory", "relations"),
            ("types", "type_inventory", "relations"), ("projections", "key_projections", "relations")):
        lookup[name] = {(row["variant_id"] if name in ("variants", "origins") else row["group_id"] if name == "groups"
            else row["descriptor_ref"]["record_id"] if name == "profiles" else row["record_id"]): i
            for i, row in enumerate(data[parent][field])}
    lookup["key_inventory"] = {r["key_ref"]["record_id"]: i for i, r in enumerate(data["relations"]["key_inventory"])}
    lookup["shape_kernels"] = {(r["source_type_ref"]["record_id"], r["family"], r["quality"]): i
        for i, r in enumerate(data["relations"]["kernels"])}
    lookup["motion_kernels"] = {(r["group_id"], r["source_profile_ref"]["record_id"],
        r["target_profile_ref"]["record_id"], r["family"], r["quality"]): i
        for i, r in enumerate(data["grounding"]["motion_kernel_inventory"])}
    if before != digest([ir, scope, hypotheses, index, relations, grounding]) or not indexed._same(contract, _contract()):
        raise ValueError("grounding_inputs_or_current_code_changed_during_prepare")
    handle = _PreparedGrounding()
    state = _SessionState(data, indexed._freeze(lookup), digest(_contract()), b"")
    object.__setattr__(state, "authentication", _authentication(handle, state))
    _SESSIONS[handle] = state
    return handle


def _arguments(state, group_id, variant_ids, key_id):
    if type(group_id) is not str or group_id not in state.lookups["groups"]:
        raise ValueError("foreign_or_unknown_grounding_group")
    if type(key_id) is not str or key_id not in state.lookups["keys"]:
        raise ValueError("foreign_or_unknown_grounding_key")
    if not isinstance(variant_ids, (list, tuple)) or any(type(v) is not str for v in variant_ids):
        raise ValueError("ordered_explicit_grounding_variant_tuple_required")
    group = state.data["grounding"]["path_groups"][state.lookups["groups"][group_id]]
    if len(variant_ids) != len(group["slots"]) or len(set(variant_ids)) != len(variant_ids):
        raise ValueError("complete_unique_ordered_grounding_variant_tuple_required")
    for ref, slot in zip(variant_ids, group["slots"]):
        if ref not in slot["variant_ids"]:
            raise ValueError("foreign_variant_or_wrong_grounding_partition_slot")
    return group


def _function(state, source_id, target_id, key_id, family, quality):
    data = state.data["relations"]
    source = data["origin_inventory"][state.lookups["origins"][source_id]]
    target = None if target_id is None else data["origin_inventory"][state.lookups["origins"][target_id]]
    kernel_key = (source["type_ref"]["record_id"], family, quality)
    if kernel_key not in state.lookups["shape_kernels"]:
        return None
    kernel = data["kernels"][state.lookups["shape_kernels"][kernel_key]]
    key = data["key_inventory"][state.lookups["key_inventory"][key_id]]
    projection = data["key_projections"][state.lookups["projections"][kernel["key_projection_refs"][key["key_type_ref"]["record_id"]]["record_id"]]]
    body = indexed._thaw(kernel["source_template"])
    blockers = list(kernel["source_blockers"])
    root, members, compatible = None, None, None
    if target is None:
        blockers.append("following_target_segment_not_observed")
    else:
        semantic = data["type_inventory"][state.lookups["types"][target["type_ref"]["record_id"]]]["semantic"]
        root, members = indexed._thaw(semantic["root"]), indexed._thaw(semantic["members"])
        if root is None or members is None:
            blockers.append("following_target_spelling_unresolved")
        else:
            blockers.extend("target:" + reason for reason in semantic["blockers"])
            if body["derived_target_root"] is not None:
                compatible = (frozen._pitch_key(root) == frozen._pitch_key(body["derived_target_root"])
                    and {frozen._pitch_key(p) for p in body["derived_target_members"]} <= {frozen._pitch_key(p) for p in members})
                if not compatible:
                    blockers.append("following_target_triad_core_mismatch")
    body.update(source_segment_ref=source["segment_ref"], source_span=indexed._thaw(source["span"]),
        target_segment_ref=None if target is None else target["segment_ref"], target_span=None if target is None else indexed._thaw(target["span"]),
        actual_target_root=root, actual_target_members=members, target_shape_compatible=compatible,
        function_kind=projection["function_kind"], key_segment_ref=key["key_segment_ref"], key_projection=indexed._thaw(projection["key_projection"]),
        status="conditional_function_shape" if not blockers else "withheld", blockers=sorted(set(blockers)))
    return body


def query_grounded_prepared(session, group_id, variant_ids, key_id):
    state = _session(session)
    group = _arguments(state, group_id, variant_ids, key_id)
    grounding, index = state.data["grounding"], state.data["index"]
    key = index["keys"][state.lookups["keys"][key_id]]
    logical = _seal({"version": VERSION, "grounding_ref": _ref(grounding), "index_ref": _ref(index),
        "group_id": group_id, "partition": indexed._thaw(group["partition"]), "variant_ids": list(variant_ids),
        "key_ref": _ref(key), "semantics": "exact_logical_tuple_not_fabricated_legacy_path"}, "fmgrtuple_")
    profiles, functions = [], []
    variants = [None if ref not in state.lookups["variants"] else index["variant_inventory"][state.lookups["variants"][ref]] for ref in variant_ids]
    for variant in variants:
        if variant is None:
            profiles.append(None)
            continue
        pid = variant["profile_ref"]["record_id"]
        profile = None if pid not in state.lookups["profiles"] else indexed._thaw(grounding["profile_inventory"][state.lookups["profiles"][pid]])
        if profile is None:
            profiles.append(None)
        else:
            rows = {rid: indexed._thaw(grounding["row_inventory"][state.lookups["rows"][rid]]) for rid in profile["row_ids"]}
            cells = {rid: indexed._thaw(grounding["cell_inventory"][state.lookups["cells"][rid]]) for rid in profile["cell_ids"]}
            profiles.append(_restore_profile(profile, indexed._thaw(variant["variant"]), rows, cells))
    for position, source_id in enumerate(variant_ids):
        target_id = variant_ids[position + 1] if position + 1 < len(variant_ids) else None
        for family in frozen.FAMILIES:
            for quality in ("M", "m"):
                function = None if group["status"] != "ready_function_shape_relations" or variants[position] is None or (target_id is not None and variants[position + 1] is None) else _function(state, source_id, target_id, key_id, family, quality)
                kernel = None
                if function is not None and target_id is not None:
                    lookup_key = (group_id, variants[position]["profile_ref"]["record_id"], variants[position + 1]["profile_ref"]["record_id"], family, quality)
                    if lookup_key in state.lookups["motion_kernels"]:
                        kernel = grounding["motion_kernel_inventory"][state.lookups["motion_kernels"][lookup_key]]
                functions.append({"slot_index": position, "family": family, "quality": quality,
                    "function": function, "motion_kernel_ref": None if kernel is None else _ref(kernel),
                    "motion": None if kernel is None else indexed._thaw(kernel),
                    "motion_status": "unassessed_function_shape_prerequisites" if kernel is None else kernel["status"],
                    "conditional_NCT_and_delayed_resolution": "unassessed"})
    result = _seal({"version": VERSION, "contract": _contract(), "grounding_ref": _ref(grounding),
        "scope_ref": indexed._thaw(grounding["scope_ref"]), "index_ref": _ref(index),
        "relations_ref": indexed._thaw(grounding["relations_ref"]), "symbolic_universe_ref": _ref(grounding["logical_universe"]),
        "tuple_ref": _ref(logical), "logical_tuple": logical, "group_id": group_id,
        "variant_ids": list(variant_ids), "key_ref": _ref(key), "profiles": profiles, "functions": functions,
        "baseline_bundle_ref": indexed._thaw(grounding["baseline_bundle_ref"]),
        "computed_counts": {"queried_tuples": 1, "profile_uses": sum(p is not None for p in profiles),
            "pure_function_rows": sum(r["function"] is not None for r in functions),
            "grounded_motion_kernel_uses": sum(r["motion"] is not None and r["motion"]["motion_kernel_computed"] for r in functions)},
        "logical_function_rows": group["logical_function_count"],
        "status": "computed_grounded_tuple_not_selected" if group["status"] == "ready_function_shape_relations" else "withheld_source_relation_tuple",
        "reasons": [] if group["status"] == "ready_function_shape_relations" else indexed._thaw(group["reasons"]),
        "selected": None, "rank": None, "confidence": None,
        "flags": _flags(), "conditional_NCT_and_delayed_resolution": "unassessed"}, QUERY_PREFIX)
    _session(session)
    return result


def query_grounded(ir, scope, hypotheses, index, relations, grounding, group_id, variant_ids, key_id):
    return query_grounded_prepared(prepare_grounding(ir, scope, hypotheses, index, relations, grounding), group_id, variant_ids, key_id)


def validate_query(ir, scope, hypotheses, index, relations, grounding, group_id, variant_ids, key_id, result):
    frozen._check(result, QUERY_PREFIX)
    if not indexed._same(result, query_grounded(ir, scope, hypotheses, index, relations, grounding, group_id, variant_ids, key_id)):
        raise ValueError("stale_foreign_modified_or_promoting_grounded_query")
    return True


def assess_grounded_prepared(session, bundle, group_id, variant_ids, key_id):
    state = _session(session)
    frozen._check(bundle, BUNDLE_PREFIX)
    if bundle["record_id"] not in state.lookups["bundles"]:
        raise ValueError("existing_bundle_not_in_same_grounded_universe")
    registered = state.data["grounding"]["bundle_inventory"][state.lookups["bundles"][bundle["record_id"]]]
    if not indexed._same(bundle, indexed._thaw(registered)):
        raise ValueError("foreign_or_modified_existing_grounded_bundle")
    query = query_grounded_prepared(session, group_id, variant_ids, key_id)
    rows = []
    for row in query["functions"]:
        kernel = row["motion"]
        status, matched = ("unassessed_function_shape_prerequisites", {}) if kernel is None else _incidence(kernel, bundle)
        rows.append({"slot_index": row["slot_index"], "family": row["family"], "quality": row["quality"],
            "motion_kernel_ref": row["motion_kernel_ref"], "status": status,
            "matched_actual_links_by_role": matched,
            "all_critical_roles_in_same_complete_bundle": status == "conditional_joint_direct_motion_under_existing_bundle",
            "function_confirmed": None, "conditional_NCT_and_delayed_resolution": "unassessed"})
    result = _seal({"version": VERSION, "contract": _contract(), "grounding_ref": _ref(state.data["grounding"]),
        "query_ref": _ref(query), "tuple_ref": query["tuple_ref"], "bundle_ref": _ref(bundle),
        "symbolic_universe_ref": query["symbolic_universe_ref"], "group_id": group_id,
        "variant_ids": list(variant_ids), "key_ref": query["key_ref"], "rows": rows,
        "same_complete_bundle_for_all_competing_function_assumptions": bundle["status"] == "complete_all_lane_witness",
        "computed_counts": {"queried_tuples": 1, "function_assumptions": len(rows),
            "conditional_joint_direct_motion_shapes": sum(r["all_critical_roles_in_same_complete_bundle"] for r in rows)},
        "logical_function_rows": query["logical_function_rows"], "status": "computed_under_existing_same_bundle_not_selected",
        "selected": None, "rank": None, "confidence": None, "flags": _flags(),
        "conditional_NCT_and_delayed_resolution": "unassessed"}, ASSESSMENT_PREFIX)
    _session(session)
    return result


def assess_grounded(ir, scope, hypotheses, index, relations, grounding, bundle, group_id, variant_ids, key_id):
    return assess_grounded_prepared(prepare_grounding(ir, scope, hypotheses, index, relations, grounding), bundle, group_id, variant_ids, key_id)


def validate_assessment(ir, scope, hypotheses, index, relations, grounding, bundle, group_id, variant_ids, key_id, result):
    frozen._check(result, ASSESSMENT_PREFIX)
    if not indexed._same(result, assess_grounded(ir, scope, hypotheses, index, relations, grounding, bundle, group_id, variant_ids, key_id)):
        raise ValueError("stale_foreign_modified_or_promoting_grounded_assessment")
    return True
