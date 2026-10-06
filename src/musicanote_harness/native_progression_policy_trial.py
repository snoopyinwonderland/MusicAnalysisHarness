"""Append-only conditional policy probe over registered saved contrasts.

No native/session/role/contrast producer is replayed. Original full IR,
scope, lattice, controls and every saved alternative remain separately bound.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
from time import perf_counter

from . import native_progression_contrast_trial as parent
from . import native_progression_policy as policy
from .musical_pattern_observation import digest, f

old, sealed = parent.old, parent.sealed
ROOT = parent.ROOT
VERSION = "native-progression-policy-trial-0.1.0"
AUTHORITY = parent.AUTHORITY
SETTINGS = {"work_budget": 2000000, "max_completion_groups": 4,
    "max_entries_per_completion": 64, "max_pairs_per_completion": 2000,
    "max_file_bytes": 67108864, "max_decoded_file_bytes": 268435456,
    "max_total_decoded_bytes": 1073741824, "max_output_record_bytes": 67108864}
POLICY_FALSE = (*parent.POLICY_FALSE, "contrast_producer_replayed", "conditional_proposal_is_final_harmony")
REPORT_KEYS = {"version", "status", "computation_integrity_passed", "inputs_and_code_unchanged",
    "artifacts_unchanged", "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes",
    "denominators", "saved_completion_groups", "computed_completion_groups", "whole_contrast_holds",
    "summary", "source_authority", "fresh_native_preparations", "selected", "elapsed_seconds", "limits",
    *parent.POLICY_FALSE}
PLAN_KEYS = {"version", "parent", "inputs", "code", "settings", "denominators", "parent_report_sha256",
    "parent_inventory_files", "parent_source_size_manifest", "parent_selected_contexts", "reader_counts",
    "source_authority", "all_cross_batch_entries_per_saved_completion", "fresh_native_preparations",
    "selected", *parent.POLICY_FALSE}
ROW_KEYS = {"context_key", "kind", "full_IR", "scope", "native_lattice", "source_panel",
    "original_source_files", "bundle", "saved_batch_refs", "submitted_entries", "contrast", "summary",
    "query_plan", "status", "reasons", "error"}
SUMMARY_FIELDS = {"submitted_entries", "evaluated_entries", "withheld_entries", "fixed_premise_groups",
    "conditional_function_supported_alternatives", "held_alternatives",
    "declared_requirement_not_supported_alternatives", "diagnostic_reason_counts"}
KNOWN_COUNT_FIELDS = {"submitted_entries", "evaluated_entries", "withheld_entries"}
NULLABLE_COUNT_FIELDS = SUMMARY_FIELDS - KNOWN_COUNT_FIELDS - {"diagnostic_reason_counts"}
RESULT_KEYS = {"version", "rule_version", "rules", "source_authority", "parent_contrast_ref", "scope_ref",
    "lattice_ref", "binding", "analysis_span", "logical_universe", "submitted_entry_refs", "query_plan",
    "resource_limits", "alternatives", "fixed_premise_groups", "summary", "reasons", "status", "selected",
    "rank", "confidence", "flags", "limitations", "record_id", "record_sha256"}
ALTERNATIVE_KEYS = {"entry_refs", "premises", "status", "diagnostics", "transition_assessments", "account_pointer",
    "claim_scope", "selected", "rank", "confidence"}
GROUP_KEYS = {"group_id", "premises", "alternative_indices", "conditional_support_indices", "held_indices",
    "declared_requirement_not_supported_indices", "competition", "selected"}


def _settings(limits):
    if set(limits) - set(SETTINGS):
        raise ValueError("closed_saved_policy_trial_limits_required")
    result = {**SETTINGS, **limits}
    for key, value in result.items():
        old._limit(value, key)
    return result


def _new_code_paths():
    return {Path(__file__).resolve(), Path(policy.__file__).resolve(),
        ROOT / "tests/test_native_progression_policy.py", ROOT / "tests/test_native_progression_policy_trial.py"}


def _code_paths():
    return sorted({*parent._code_paths(), *(p for p in _new_code_paths() if p.is_file())})


def _registered(info, registration, reader, protected, prefix):
    old._closed(info, parent.INFO_KEYS, "registered_saved_policy_input")
    if registration.get(info["artifact"]) != info["sha256"]:
        raise ValueError("saved_policy_input_not_in_creation_registration")
    return parent._record(info, prefix, reader, protected)


def _ref(value):
    old._closed(value, {"record_id", "record_sha256"}, "saved_policy_reference")
    if (type(value["record_id"]) is not str or not value["record_id"]
            or type(value["record_sha256"]) is not str or len(value["record_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in value["record_sha256"])):
        raise ValueError("closed_saved_content_reference_required")
    return value


def _parent_summary(record):
    summary = record["summary"]
    old._closed(summary, parent.SUMMARY_FIELDS, "phase26_summary")
    for key in parent.SUMMARY_FIELDS - {"pair_kind_counts"}:
        old._limit(summary[key], "phase26_summary." + key)
    kinds = summary["pair_kind_counts"]
    if type(kinds) is not dict or set(kinds) - set(parent.engine.KINDS):
        raise ValueError("closed_saved_pair_kind_counts_required")
    for value in kinds.values():
        old._limit(value, "phase26_pair_kind_count")
    if any(summary[key + "_pairs"] != kinds.get(key, 0) for key in parent.engine.KINDS):
        raise ValueError("saved_parent_pair_kind_totals_mismatch")
    return summary


def _contrast(record, row, scope, lattice, bundle, panel, settings):
    """Validate saved identity/counts without re-running contrast calculation."""
    summary = _parent_summary(record)
    old._closed(record["flags"], parent.RESULT_FLAGS, "phase26_flags")
    held = record["status"] == "whole_saved_contrast_hold"
    if (record["version"] != parent.engine.VERSION or record["source_authority"] != AUTHORITY
            or record["status"] not in ("computed_saved_progression_contrasts_not_selected", "whole_saved_contrast_hold")
            or any(value is not False for value in record["flags"].values())
            or any(record[key] is not None for key in ("selected", "rank", "confidence"))
            or record["scope_ref"] != sealed._ref(scope) or record["lattice_ref"] != sealed._ref(lattice)
            or record["binding"] != scope["binding"] or record["analysis_span"] != scope["analysis_span"]
            or record["logical_universe"] != lattice["universe"]
            or record["summary"] != row["summary"] or record["query_plan"] != row["query_plan"]
            or record["status"] != row["status"] or record["reasons"] != row["reasons"]
            or summary["submitted_entries"] != row["submitted_entries"]):
        raise ValueError("exact_registered_saved_contrast_required")
    if summary["submitted_entries"] != 50:
        raise ValueError("all_fifty_registered_parent_entries_required")
    for key in ("planned_work", "planned_pairs", "entry_count"):
        old._limit(record["query_plan"][key], "phase26_query_plan." + key)
    old._closed(record["resource_limits"], {"work_budget", "max_pairs"}, "phase26_limits")
    for value in record["resource_limits"].values():
        old._limit(value, "phase26_resource_limit")
    if (type(record["submitted_entry_refs"]) is not list or len(record["submitted_entry_refs"]) != 50
            or len(record["facets"]) > settings["max_entries_per_completion"]
            or len(record["pairs"]) > settings["max_pairs_per_completion"]):
        raise ValueError("whole_saved_policy_read_hold:all_entries_and_pairs_no_prefix")
    comparison_refs = {digest(value["comparison"]["record_ref"]) for value in row["saved_batch_refs"]}
    explanation_refs = {digest(value["explanation"]["record_ref"]) for value in row["saved_batch_refs"]}
    for position, refs in enumerate(record["submitted_entry_refs"]):
        old._closed(refs, {"native_path_ref", "role_path_ref", "comparison_ref", "explanation_ref"}, "parent_entry_refs")
        for value in refs.values():
            _ref(value)
        batch = row["saved_batch_refs"][position // 3]
        if (refs["comparison_ref"] != batch["comparison"]["record_ref"]
                or refs["explanation_ref"] != batch["explanation"]["record_ref"]):
            raise ValueError("exact_cross_batch_parent_entry_order_required")
    if len({digest(value["native_path_ref"]) for value in record["submitted_entry_refs"]}) != 50:
        raise ValueError("duplicate_saved_parent_native_path_reference")
    if held:
        if (record["facets"] or record["pairs"] or summary["computed_pairs"]
                or summary["raw_time_conserved_entries"] or summary["withheld_pairs"] != summary["planned_same_key_same_bundle_pairs"]):
            raise ValueError("whole_saved_parent_hold_no_materialized_prefix")
        return
    if len(record["facets"]) != 50 or summary["raw_time_conserved_entries"] != 50:
        raise ValueError("complete_saved_facet_inventory_required")
    origins = {o["record_id"]: o for cat in lattice["catalog_inventory"] for o in cat["origins"]}
    keys = {value["record_id"]: value for value in lattice["keys"]}
    indexed, groups = {}, defaultdict(list)
    for facet, refs, selector in zip(record["facets"], record["submitted_entry_refs"], panel["selectors"]):
        if (any(facet[key] != value for key, value in refs.items())
                or digest(facet["comparison_ref"]) not in comparison_refs
                or digest(facet["explanation_ref"]) not in explanation_refs
                or facet["bundle_ref"] != sealed._ref(bundle)
                or facet["key_ref"] != sealed._ref(keys[selector["key_id"]])
                or [s["origin_ref"] for s in facet["slot_presentations"]] !=
                    [sealed._ref(origins[i]) for i in selector["origin_ids"]]
                or facet["partition"] != [origins[i]["span"] for i in selector["origin_ids"]]
                or facet["transition_assumptions"] != selector["transition_assumptions"]):
            raise ValueError("exact_saved_facet_key_bundle_partition_selector_required")
        raw = f(facet["account"]["raw_total_note_time_quarters"])
        if (facet["account"]["raw_time_conserved"] is not True
                or sum(map(f, facet["account"]["note_time_quarters"].values())) != raw
                or sum(map(f, facet["account"]["raw_state_note_time_quarters"].values())) != raw):
            raise ValueError("saved_facet_raw_rational_conservation_required")
        indexed[facet["native_path_ref"]["record_id"]] = facet
        groups[(digest(facet["key_ref"]), digest(facet["bundle_ref"]))].append(facet["native_path_ref"]["record_id"])
    if len(groups) != len(keys) or any(len(value) != 10 for value in groups.values()):
        raise ValueError("all_five_key_alternatives_required")
    expected = {pair for values in groups.values() for pair in combinations(values, 2)}
    actual = set()
    for pair in record["pairs"]:
        ids = tuple(pair[name]["record_id"] for name in ("left_path_ref", "right_path_ref"))
        if ids not in expected or ids in actual:
            raise ValueError("all_unique_same_key_same_completion_pairs_required")
        actual.add(ids)
        left, right = (indexed[i] for i in ids)
        if (pair["left_path_ref"] != left["native_path_ref"] or pair["right_path_ref"] != right["native_path_ref"]
                or pair["left_role_path_ref"] != left["role_path_ref"] or pair["right_role_path_ref"] != right["role_path_ref"]
                or pair["key_ref"] != left["key_ref"] or pair["key_ref"] != right["key_ref"]
                or pair["bundle_ref"] != sealed._ref(bundle) or pair["raw_time_conserved"] is not True
                or any(pair[key] is not None for key in ("selected", "rank", "confidence"))):
            raise ValueError("saved_pair_content_refs_and_same_completion_required")
    kinds = dict(sorted(Counter(pair["comparison_kind"] for pair in record["pairs"]).items()))
    if (actual != expected or summary["planned_same_key_same_bundle_pairs"] != len(expected)
            or summary["computed_pairs"] != len(actual) or summary["withheld_pairs"] != 0
            or summary["pair_kind_counts"] != kinds
            or summary["alias_control_pairs"] != sum(p["alias_control"] is True for p in record["pairs"])):
        raise ValueError("exact_saved_complete_pair_summary_required")


def load_inputs(directory, **limits):
    """Bounded saved-only admission; never an old producer/session replay."""
    settings = _settings(limits)
    directory = Path(directory).resolve(strict=True)
    reader, protected = parent.BoundedReader(settings), {}
    report_path = directory / "report.json"
    report = reader.read(report_path)
    old._closed(report, REPORT_KEYS, "phase26_report")
    for key in ("fresh_native_preparations", "saved_completion_groups", "computed_completion_groups", "whole_contrast_holds"):
        old._limit(report[key], "phase26_report." + key)
    if (report["version"] != parent.VERSION or report["status"] != "saved_progression_contrast_probe_complete_not_selected"
            or any(report[k] is not True for k in ("computation_integrity_passed", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or any(report[k] != [] for k in ("changed_inputs_or_code", "changed_artifacts", "failures"))
            or any(report[k] is not False for k in parent.POLICY_FALSE) or report["selected"] is not None
            or report["fresh_native_preparations"] != 0 or report["source_authority"] != AUTHORITY
            or type(report["artifact_hashes"]) is not dict or len(report["artifact_hashes"]) != 6):
        raise ValueError("exact_completed_saved_phase26_parent_required")
    old._protect(protected, str(report_path), old._file_sha(report_path))
    old._protect_map(protected, report["artifact_hashes"])
    inventory = old._inventory(directory, report["artifact_hashes"], report_path)
    plan = reader.read(directory / "run-plan.json")
    old._closed(plan, PLAN_KEYS, "phase26_creation_plan")
    old._limit(plan["fresh_native_preparations"], "phase26_plan.fresh_native_preparations")
    old._limit(plan["parent_inventory_files"], "phase26_plan.parent_inventory_files")
    if (plan["version"] != parent.VERSION or plan["source_authority"] != AUTHORITY
            or plan["all_cross_batch_entries_per_saved_completion"] is not True
            or plan["selected"] is not None or plan["fresh_native_preparations"] != 0
            or any(plan[k] is not False for k in parent.POLICY_FALSE)
            or plan["denominators"] != report["denominators"]):
        raise ValueError("exact_saved_parent_creation_policy_required")
    old._protect_map(protected, plan["inputs"])
    old._protect_map(protected, plan["code"])
    historical = {str(p.resolve()) for p in parent._code_paths()} - {str(p.resolve()) for p in _new_code_paths()}
    if set(plan["code"]) != historical:
        raise ValueError("exact_historical_creation_code_inventory_required")
    old._closed(report["denominators"], parent.DENOMINATOR_KEYS, "saved_cohort_denominators")
    denoms = report["denominators"]
    for key, value in denoms.items():
        old._limit(value, "saved_cohort." + key)
    if (denoms["selected_contexts"] != 2 or denoms["registered_context_pool"] != 5
            or denoms["unexecuted_declared_contexts"] != denoms["declared_contexts"] - 2
            or denoms["unexecuted_declared_original_raw_lanes"] != denoms["declared_original_raw_lanes"] - denoms["selected_original_raw_lanes"]):
        raise ValueError("exact_saved_parent_cohort_complement_required")
    changed = old._guard(protected)
    if changed:
        raise ValueError("saved_parent_creation_SHA256_changed:" + repr(changed))
    previous = Path(plan["parent"]).resolve(strict=True)
    p_report_path = previous / "report.json"
    p_report, p_plan, p_rows = (reader.read(previous / name) for name in ("report.json", "run-plan.json", "context-index.json"))
    if protected.get(str(p_report_path)) != plan["parent_report_sha256"] or old._file_sha(p_report_path) != plan["parent_report_sha256"]:
        raise ValueError("phase25_report_creation_hash_required")
    old._closed(p_report, parent.REPORT_KEYS, "phase25_protected_report")
    old._closed(p_plan, parent.PLAN_KEYS, "phase25_protected_plan")
    p_inventory = old._inventory(previous, p_report["artifact_hashes"], p_report_path)
    if len(p_inventory) != plan["parent_inventory_files"] or len(p_inventory) != 148:
        raise ValueError("exact_protected_phase25_inventory_required")
    for declared in (p_report["artifact_hashes"], p_plan["inputs"], p_plan["code"]):
        for path, sha in declared.items():
            if plan["inputs"].get(path) != sha:
                raise ValueError("original_creation_hash_closure_not_preserved")
    if (p_plan["selected_contexts"] != plan["parent_selected_contexts"]
            or p_plan["source_size_manifest"] != plan["parent_source_size_manifest"]
            or p_report["denominators"] != denoms or p_plan["denominators"] != denoms
            or type(p_rows) is not list or len(p_rows) != 2):
        raise ValueError("original_pool_selection_and_cohort_required")
    rows = reader.read(directory / "context-index.json")
    if type(rows) is not list or len(rows) != 4 or len(rows) > settings["max_completion_groups"]:
        raise ValueError("whole_saved_policy_read_hold:four_controls_no_prefix")
    expected_order = [(p["context_key"], c["kind"]) for p in p_rows for c in p["completion_batches"]]
    if [(r["context_key"], r["kind"]) for r in rows] != expected_order:
        raise ValueError("exact_saved_context_completion_order_required")
    cache, cases, summaries = {}, [], []
    for row in rows:
        old._closed(row, ROW_KEYS, "phase26_context_index_row")
        if row["error"] is not None or row["submitted_entries"] != 50:
            raise ValueError("complete_saved_parent_control_required")
        old._limit(row["submitted_entries"], "submitted_entries")
        if row["submitted_entries"] > settings["max_entries_per_completion"]:
            raise ValueError("whole_saved_policy_read_hold:entries_no_prefix")
        prow = next(p for p in p_rows if p["context_key"] == row["context_key"])
        completion = next(c for c in prow["completion_batches"] if c["kind"] == row["kind"])
        expected_refs = [{k: b[k] for k in ("comparison", "explanation")} for b in completion["batches"]]
        if (row["saved_batch_refs"] != expected_refs or len(expected_refs) != 17
                or row["bundle"] != completion["bundle"]
                or any(row[k] != prow[pk] for k, pk in (("full_IR", "full_IR"), ("scope", "scope"),
                    ("native_lattice", "native_lattice"), ("source_panel", "panel")))):
            raise ValueError("exact_original_batch_control_and_source_refs_required")
        for refs in row["saved_batch_refs"]:
            old._closed(refs, {"comparison", "explanation"}, "saved_batch_ref_pair")
            for info in refs.values():
                old._closed(info, parent.INFO_KEYS, "saved_batch_info")
                if protected.get(info["artifact"]) != info["sha256"]:
                    raise ValueError("registered_original_batch_hash_required")
                _ref(info["record_ref"])
        key = digest(row["context_key"])
        if key not in cache:
            old._closed(row["full_IR"], parent.IR_INFO_KEYS, "registered_full_IR")
            info = row["full_IR"]
            if (info["binding_match"] is not True or info["registered_full_IR_not_projection"] is not True
                    or protected.get(info["artifact"]) != info["sha256"]):
                raise ValueError("registered_original_full_IR_required")
            ir = reader.read(info["artifact"])
            if ir["ir_document_id"] != info["ir_document_id"] or digest(ir) != info["ir_content_sha256"]:
                raise ValueError("registered_original_full_IR_content_mismatch")
            scope = _registered(row["scope"], protected, reader, protected, old.expanded.PREFIX)
            lattice = _registered(row["native_lattice"], protected, reader, protected, parent.parent.native.PREFIX)
            panel = _registered(row["source_panel"], protected, reader, protected, parent.parent.panel_engine.PREFIX)
            if (scope["binding"] != old.expanded._binding(ir)
                    or lattice["scope_ref"] != sealed._ref(scope) or lattice["binding"] != scope["binding"]
                    or lattice["analysis_span"] != scope["analysis_span"]
                    or panel["scope_ref"] != sealed._ref(scope) or panel["lattice_ref"] != sealed._ref(lattice)
                    or panel["selectors"] != prow["selected_selectors"] or len(panel["selectors"]) != 50):
                raise ValueError("saved_full_IR_scope_lattice_panel_binding_required")
            cache[key] = scope, lattice, panel, deepcopy(ir["source_files"])
        scope, lattice, panel, sources = cache[key]
        if row["original_source_files"] != sources:
            raise ValueError("original_full_IR_source_snapshots_required")
        bundle = _registered(row["bundle"], protected, reader, protected, parent.parent.native.BUNDLE_PREFIX)
        if (bundle["scope_ref"] != sealed._ref(scope) or bundle["lattice_ref"] != sealed._ref(lattice)
                or bundle["binding"] != scope["binding"]
                or parent._edge_signature(bundle["required_links"]) != parent._edge_signature(completion["required_links"])):
            raise ValueError("exact_original_same_completion_bundle_required")
        contrast = _registered(row["contrast"], report["artifact_hashes"], reader, protected, parent.engine.PREFIX)
        _contrast(contrast, row, scope, lattice, bundle, panel, settings)
        summaries.append(contrast["summary"])
        cases.append({"row": deepcopy(row), "scope": scope, "lattice": lattice, "bundle": bundle, "contrast": contrast})
    if sum(len(value[0]["raw_lanes"]) for value in cache.values()) != denoms["selected_original_raw_lanes"]:
        raise ValueError("exact_original_selected_raw_lane_count_required")
    numeric, kinds = Counter(), Counter()
    for summary in summaries:
        for key, value in summary.items():
            if key == "pair_kind_counts":
                kinds.update(value)
            else:
                numeric[key] += value
    if (report["summary"] != {**dict(numeric), "pair_kind_counts": dict(kinds)}
            or report["saved_completion_groups"] != 4
            or report["computed_completion_groups"] != sum(c["contrast"]["status"] == "computed_saved_progression_contrasts_not_selected" for c in cases)
            or report["whole_contrast_holds"] != sum(c["contrast"]["status"] == "whole_saved_contrast_hold" for c in cases)):
        raise ValueError("exact_parent_report_summary_and_hold_counts_required")
    return {"parent": directory, "report": report, "plan": plan, "cases": cases, "hashes": protected,
        "inventories": [(directory, inventory), (previous, p_inventory)], "settings": settings,
        "reader_counts": {"files_read": reader.read_files, "decoded_bytes": reader.decoded_bytes}}


def _validate_result(record, case, settings):
    """Closed identity/count validation; policy semantic tests are separate."""
    sealed._check(record, policy.PREFIX)
    old._closed(record, RESULT_KEYS, "saved_policy_result")
    old._closed(record["summary"], SUMMARY_FIELDS, "saved_policy_summary")
    old._closed(record["flags"], parent.RESULT_FLAGS, "saved_policy_flags")
    old._closed(record["query_plan"], {"planned_work", "literal_profile_and_reference_work",
        "source_credit_cover_work", "submitted_entries", "planned_groups", "semantics"}, "saved_policy_plan")
    old._closed(record["resource_limits"], {"work_budget"}, "saved_policy_limits")
    summary = record["summary"]
    held = record["status"] == "whole_saved_policy_hold"
    for key in KNOWN_COUNT_FIELDS:
        old._limit(summary[key], "saved_policy_summary." + key)
    for key in NULLABLE_COUNT_FIELDS:
        if held:
            if summary[key] is not None:
                raise ValueError("whole_policy_hold_unknown_counts_must_stay_null")
        else:
            old._limit(summary[key], "saved_policy_summary." + key)
    counts = summary["diagnostic_reason_counts"]
    if held:
        if counts is not None:
            raise ValueError("whole_policy_hold_unknown_diagnostics_must_stay_null")
    else:
        if type(counts) is not dict or any(type(k) is not str or not k for k in counts):
            raise ValueError("closed_policy_reason_count_map_required")
        for value in counts.values():
            old._limit(value, "saved_policy_reason_count")
    if (record["version"] != policy.VERSION or record["source_authority"] != AUTHORITY
            or record["rule_version"] != policy.RULE_VERSION or record["rules"] != policy.RULES
            or record["parent_contrast_ref"] != sealed._ref(case["contrast"])
            or record["scope_ref"] != sealed._ref(case["scope"]) or record["lattice_ref"] != sealed._ref(case["lattice"])
            or record["binding"] != case["scope"]["binding"] or record["analysis_span"] != case["scope"]["analysis_span"]
            or record["logical_universe"] != case["contrast"]["logical_universe"]
            or record["submitted_entry_refs"] != case["contrast"]["submitted_entry_refs"]
            or record["resource_limits"] != {"work_budget": settings["work_budget"]}
            or record["status"] not in ("computed_saved_progression_policy_not_selected", "whole_saved_policy_hold", "empty_saved_policy_request")
            or any(record[key] is not None for key in ("selected", "rank", "confidence"))
            or any(value is not False for value in record["flags"].values())):
        raise ValueError("exact_saved_policy_identity_and_no_promotion_required")
    for key in ("planned_work", "literal_profile_and_reference_work", "source_credit_cover_work", "submitted_entries"):
        old._limit(record["query_plan"][key], "saved_policy_query_plan." + key)
    if type(record["query_plan"]["semantics"]) is not str or not record["query_plan"]["semantics"]:
        raise ValueError("typed_saved_policy_query_semantics_required")
    if record["query_plan"]["planned_groups"] is not None:
        old._limit(record["query_plan"]["planned_groups"], "saved_policy_query_plan.planned_groups")
    submitted = case["contrast"]["summary"]["submitted_entries"]
    evaluated = 0 if held else len(record["alternatives"])
    if (summary["submitted_entries"] != submitted or record["query_plan"]["submitted_entries"] != submitted
            or summary["evaluated_entries"] != evaluated or len(record["alternatives"]) != submitted
            or summary["withheld_entries"] != submitted - evaluated
            or (not held and summary["fixed_premise_groups"] != len(record["fixed_premise_groups"]))):
        raise ValueError("exact_saved_policy_complete_alternative_counts_required")
    if held and record["fixed_premise_groups"]:
        raise ValueError("whole_saved_policy_hold_no_partial_groups")
    if not held and len(record["alternatives"]) != len(case["contrast"]["facets"]):
        raise ValueError("all_parent_alternatives_without_favorable_filter_required")
    if (type(record["reasons"]) is not list or any(type(reason) is not str for reason in record["reasons"])
            or held != bool(record["reasons"])
            or (record["status"] == "empty_saved_policy_request") != (not submitted and not held)):
        raise ValueError("whole_policy_hold_reasons_required")
    count_status, count_reasons = Counter(), Counter()
    for position, alternative in enumerate(record["alternatives"]):
        old._closed(alternative, ALTERNATIVE_KEYS, "saved_policy_alternative")
        if (alternative["entry_refs"] != record["submitted_entry_refs"][position]
                or any(alternative[k] is not None for k in ("selected", "rank", "confidence"))):
            raise ValueError("exact_ordered_policy_alternative_refs_without_winner_required")
        if held:
            if (alternative["status"] != "held_whole_request" or alternative["premises"] is not None
                    or alternative["account_pointer"] is not None or alternative["diagnostics"]
                    or alternative["transition_assessments"] or alternative["claim_scope"] != "no_partial_policy_evaluation"):
                raise ValueError("whole_policy_hold_must_retain_unassessed_alternative")
            continue
        facet = case["contrast"]["facets"][position]
        premises = {key: facet[key] for key in ("key_ref", "bundle_ref", "partition", "transition_assumptions")}
        if (alternative["premises"] != premises or alternative["status"] not in policy.STATUSES
                or alternative["account_pointer"] != {"parent_native_path_ref": facet["native_path_ref"],
                    "parent_role_path_ref": facet["role_path_ref"], "field": "account", "sha256": digest(facet["account"])}
                or alternative["claim_scope"] != "declared_strategy_under_this_saved_completion_not_harmony_verdict"):
            raise ValueError("exact_policy_alternative_same_premise_account_pointer_required")
        for diagnostic in alternative["diagnostics"]:
            old._closed(diagnostic, {"rule_id", "reason", "effect", "target"}, "saved_policy_diagnostic")
            if (diagnostic["rule_id"] not in policy.RULES or type(diagnostic["reason"]) is not str
                    or not diagnostic["reason"] or diagnostic["effect"] not in ("hold", "not_supported_under_declared_requirement")
                    or type(diagnostic["target"]) is not dict):
                raise ValueError("typed_policy_rule_diagnostic_required")
            count_reasons[diagnostic["reason"]] += 1
        count_status[alternative["status"]] += 1
    if not held:
        if (summary["conditional_function_supported_alternatives"] != count_status[policy.STATUSES[0]]
                or summary["held_alternatives"] != count_status[policy.STATUSES[1]]
                or summary["declared_requirement_not_supported_alternatives"] != count_status[policy.STATUSES[2]]
                or counts != dict(sorted(count_reasons.items()))):
            raise ValueError("exact_policy_status_and_diagnostic_counts_required")
        expected_groups = defaultdict(list)
        for i, alternative in enumerate(record["alternatives"]):
            expected_groups[digest(alternative["premises"])].append(i)
        groups = record["fixed_premise_groups"]
        if (len(groups) != len(expected_groups) or (record["query_plan"]["planned_groups"] != len(groups)
                and not (not submitted and record["query_plan"]["planned_groups"] is None))):
            raise ValueError("exact_policy_fixed_premise_group_inventory_required")
        for group, (checksum, indices) in zip(groups, expected_groups.items()):
            old._closed(group, GROUP_KEYS, "saved_policy_fixed_premise_group")
            if (group["group_id"] != "nppgroup_" + checksum[:24] or group["selected"] is not None
                    or group["premises"] != record["alternatives"][indices[0]]["premises"]
                    or group["alternative_indices"] != indices
                    or group["competition"] != "fixed_premise_conditional_alternatives_no_unique_winner"
                    or any(group[key] != [i for i in indices if record["alternatives"][i]["status"] == status]
                        for key, status in (("conditional_support_indices", policy.STATUSES[0]),
                            ("held_indices", policy.STATUSES[1]), ("declared_requirement_not_supported_indices", policy.STATUSES[2])))):
                raise ValueError("same_key_bundle_partition_vector_groups_required")


def _aggregate(summaries):
    known, diagnostics, unknown = Counter(), Counter(), Counter()
    for summary in summaries:
        for key, value in summary.items():
            if value is None:
                unknown[key] += 1
            elif key == "diagnostic_reason_counts":
                diagnostics.update(value)
            else:
                known[key] += value
    combined = {key: None if unknown[key] else known[key] for key in SUMMARY_FIELDS - {"diagnostic_reason_counts"}}
    combined["diagnostic_reason_counts"] = None if unknown["diagnostic_reason_counts"] else dict(diagnostics)
    return combined, {**dict(known), "diagnostic_reason_counts": dict(diagnostics)}, dict(unknown)


def run(directory, output, **limits):
    started, output = perf_counter(), Path(output).resolve()
    if output.exists() or output.parent != ROOT / "output":
        raise ValueError("append_only_new_direct_workspace_output_required")
    settings = _settings(limits)
    data = load_inputs(directory, **settings)
    code = {str(path.resolve()): old._file_sha(path) for path in _code_paths()}
    protected = deepcopy(data["hashes"])
    old._protect_map(protected, code)
    output.mkdir()
    artifacts, rows, failures, summaries = {}, [], [], []
    plan = {"version": VERSION, "parent": str(data["parent"]), "inputs": deepcopy(data["hashes"]), "code": code,
        "settings": settings, "denominators": deepcopy(data["report"]["denominators"]),
        "parent_report_sha256": old._file_sha(data["parent"] / "report.json"),
        "parent_inventories": [{"directory": str(p), "files": len(i)} for p, i in data["inventories"]],
        "parent_source_size_manifest": deepcopy(data["plan"]["parent_source_size_manifest"]),
        "parent_selected_contexts": deepcopy(data["plan"]["parent_selected_contexts"]),
        "parent_contrast_summary": deepcopy(data["report"]["summary"]), "reader_counts": data["reader_counts"],
        "source_authority": AUTHORITY, "all_saved_alternatives_retained": True,
        "fresh_native_preparations": 0, "selected": None, **{key: False for key in POLICY_FALSE}}
    old._save_json(output, "run-plan.json", plan, artifacts)
    admitted_digests = [digest([c["scope"], c["lattice"], c["contrast"], c["bundle"]]) for c in data["cases"]]
    for case, admitted in zip(data["cases"], admitted_digests):
        source = case["row"]
        try:
            before = digest([case["scope"], case["lattice"], case["contrast"], case["bundle"]])
            if before != admitted:
                raise ValueError("registered_saved_policy_inputs_changed_after_admission")
            result = policy.evaluate(case["scope"], case["lattice"], case["contrast"],
                bundles={case["bundle"]["record_id"]: case["bundle"]}, work_budget=settings["work_budget"])
            if before != digest([case["scope"], case["lattice"], case["contrast"], case["bundle"]]):
                raise ValueError("policy_evaluation_modified_registered_saved_inputs")
            _validate_result(result, case, settings)
            encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            if len(encoded) > settings["max_output_record_bytes"]:
                raise ValueError("whole_saved_policy_output_byte_budget_no_partial_save")
            info = old._save_record(output, "policies", result, policy.PREFIX, artifacts)
            summaries.append(deepcopy(result["summary"]))
            rows.append({**{k: deepcopy(source[k]) for k in ("context_key", "kind", "full_IR", "scope", "native_lattice",
                "source_panel", "original_source_files", "bundle", "saved_batch_refs", "contrast")},
                "parent_summary": deepcopy(source["summary"]), "submitted_entries": source["submitted_entries"],
                "policy": info, "summary": deepcopy(result["summary"]), "query_plan": deepcopy(result["query_plan"]),
                "status": result["status"], "reasons": deepcopy(result["reasons"]), "error": None})
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"
            failures.append({"context_key": deepcopy(source["context_key"]), "kind": source["kind"], "error": error})
            rows.append({"context_key": deepcopy(source["context_key"]), "kind": source["kind"], "policy": None,
                "summary": None, "status": "saved_policy_calculation_failure", "error": error})
    old._save_json(output, "context-index.json", rows, artifacts)
    changed = old._guard(protected)
    if {str(p.resolve()) for p in _code_paths()} != set(code):
        changed.append("creation_code_inventory_changed")
    for directory, inventory in data["inventories"]:
        if {str(p.resolve()) for p in directory.rglob("*") if p.is_file()} != inventory:
            changed.append("registered_parent_inventory_changed:" + str(directory))
    changed_artifacts = old._guard(artifacts)
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(artifacts):
        changed_artifacts.append("new_artifact_inventory_changed")
    integrity = not failures and not changed and not changed_artifacts
    combined, known, unknown = _aggregate(summaries)
    complete = bool(integrity and combined["submitted_entries"] and rows
        and combined["evaluated_entries"] == combined["submitted_entries"]
        and all(r["status"] == "computed_saved_progression_policy_not_selected" for r in rows))
    report = {"version": VERSION, "status": "saved_progression_policy_probe_complete_not_selected" if integrity else
        "saved_progression_policy_probe_failed", "computation_integrity_passed": integrity,
        "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": artifacts, "denominators": deepcopy(data["report"]["denominators"]),
        "saved_completion_groups": len(rows), "computed_completion_groups": sum(r["status"] == "computed_saved_progression_policy_not_selected" for r in rows),
        "whole_policy_holds": sum(r["status"] == "whole_saved_policy_hold" for r in rows),
        "submitted_policy_evaluation_complete": complete,
        "summary": combined if integrity else None, "known_computed_summary_subtotal": known if integrity else None,
        "unknown_summary_completion_occurrences": unknown if integrity else None,
        "parent_contrast_summary": deepcopy(data["report"]["summary"]), "source_authority": AUTHORITY,
        "fresh_native_preparations": 0, "selected": None, "elapsed_seconds": perf_counter() - started,
        **{key: False for key in POLICY_FALSE}, "limits": [
            "Saved admission and conditional policy proposals do not issue native authority or final musical judgments.",
            "All saved alternatives and every key/completion remain separate; no winner, score ranking or favorable prefix.",
            "Read/output byte limits and whole policy work holds preserve unknown versus known zero.",
            "Native, role and contrast producers were not replayed; operational UI, training and generation are unchanged."]}
    old.storage.write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-budget", type=int, default=SETTINGS["work_budget"])
    args = parser.parse_args()
    run(args.parent, args.output, work_budget=args.work_budget)


if __name__ == "__main__":
    main()
