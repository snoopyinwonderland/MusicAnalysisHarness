"""Append-only fresh replay of every registered saved source proposal.

Archive admission establishes identity, not a live native session. The replay
engine alone owns fresh supplier/native/role authority. Contrast and policy
are deliberately deferred; this runner neither ranks nor selects harmony.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import gzip
import io
import re
from fractions import Fraction
from pathlib import Path
from time import perf_counter

from . import source_progression_proposal_trial as parent
from . import source_progression_replay as engine
from . import factor_native_role_trial as role_storage
from .musical_pattern_observation import digest, f, q

old, sealed = parent.old, parent.sealed
ROOT = parent.ROOT
VERSION = "source-progression-replay-trial-0.1.0"
AUTHORITY = "fresh_native_and_role_replay_not_winning_harmony_or_saved_session_authority"
ARCHIVE_FALSE = parent.POLICY_FALSE
POLICY_FALSE = tuple(k for k in ARCHIVE_FALSE if k not in (
    "fresh_native_preparations", "native_replay_executed", "native_or_role_producer_replayed"))
ARCHIVE_REPORT_KEYS = {"version", "status", "computation_integrity_passed", "inputs_and_code_unchanged",
    "artifacts_unchanged", "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes",
    "denominators", "distinct_registered_sources", "registered_policy_completion_rows", "saved_source_proposals",
    "computed_source_proposals", "whole_source_proposal_holds", "submitted_source_proposal_computation_complete",
    "admitted_native_inventory", "summary", "known_summary_subtotal", "unknown_summary_context_occurrences",
    "parent_policy_summary", "native_replay_planned_completion_requests", "native_replay_planned_selector_occurrences",
    "native_replay_evaluations_performed", "source_authority", "parent_source_authority", "fresh_native_preparations",
    "selected", "elapsed_seconds", "limits", *ARCHIVE_FALSE}
ARCHIVE_PLAN_KEYS = {"version", "parent", "inputs", "code", "settings", "denominators", "parent_report_sha256",
    "parent_inventories", "parent_source_size_manifest", "parent_selected_contexts", "parent_policy_summary",
    "reader_counts", "distinct_registered_sources", "registered_policy_completion_rows", "source_authority",
    "parent_source_authority", "fresh_native_preparations", "selected", *ARCHIVE_FALSE}
ARCHIVE_ROW_KEYS = {"context_key", "source_identity_sha256", "full_IR", "scope", "native_lattice", "prior_panel",
    "original_source_files", "native_inventory", "parent_policy_rows", "completion_controls", "proposal", "summary",
    "query_plan", "status", "reasons", "error"}
REPLAY_PLAN_KEYS = {"version", "source_authority", "jobs", "planned_completion_requests", "planned_selector_occurrences",
    "retained_control_selector_occurrences", "native_evaluations_performed", "fresh_native_sessions_prepared",
    "same_completion_resolution_evaluated", "winning_harmony_selected", "limitations"}
JOB_REQUEST_KEYS = {"context_key", "source_identity_sha256", "full_IR", "scope", "archived_lattice", "source_proposal",
    "archived_completion_control", "selector_field_pointer", "planned_selector_occurrences",
    "retained_control_selector_occurrences", "execution_status", "archived_origins_are_fresh_native_authority",
    "native_path_ids_reused", "native_evaluation_performed"}
COMPLETION_CONTROL_KEYS = {"kind", "bundle", "required_links", "policy", "policy_status", "native_and_role_replay_executed"}
READ_SETTINGS = {"max_contexts": 2, "max_origins": 200000, "max_catalogs": 1024,
    "max_file_bytes": 67108864, "max_decoded_file_bytes": 268435456,
    "max_total_decoded_bytes": 1073741824, "max_output_record_bytes": 134217728,
    "max_total_output_bytes": 2147483648, "manifest_reserve_bytes": 16777216}


def _new_code_paths():
    return {Path(__file__).resolve(), Path(engine.__file__).resolve(),
        ROOT / "tests/test_source_progression_replay.py", ROOT / "tests/test_source_progression_replay_trial.py"}


def _code_paths():
    return sorted({*parent._code_paths(), *(p for p in _new_code_paths() if p.is_file())})


def _settings(limits):
    defaults = {**READ_SETTINGS, **engine.DEFAULTS}
    if set(limits) - set(defaults):
        raise ValueError("closed_source_replay_trial_limits_required")
    settings = {**defaults, **limits}
    for key, value in settings.items():
        old._limit(value, key)
    if not 1 <= settings["batch_size"] <= 64:
        raise ValueError("source_replay_batch_size_1_to_64_required")
    if settings["manifest_reserve_bytes"] > settings["max_total_output_bytes"]:
        raise ValueError("manifest_reserve_exceeds_total_output_cap")
    if settings["max_total_output_bytes"] > 2147483648:
        raise ValueError("approved_total_output_ceiling_is_two_GiB")
    return settings


def _registered_record(info, prefix, reader, protected):
    old._closed(info, parent.parent.parent.INFO_KEYS, "registered_replay_input")
    if protected.get(info["artifact"]) != info["sha256"]:
        raise ValueError("replay_input_requires_original_creation_SHA")
    return parent.parent.parent._record(info, prefix, reader, protected)


def _expected_job(row, proposal, completion):
    held = proposal["status"] == "whole_source_proposal_hold"
    return {"context_key": deepcopy(row["context_key"]), "source_identity_sha256": row["source_identity_sha256"],
        "full_IR": deepcopy(row["full_IR"]), "scope": deepcopy(row["scope"]),
        "archived_lattice": deepcopy(row["native_lattice"]), "source_proposal": deepcopy(row["proposal"]),
        "archived_completion_control": deepcopy(completion),
        "selector_field_pointer": None if held else {"record_ref": sealed._ref(proposal), "field": "selectors"},
        "planned_selector_occurrences": None if held else len(proposal["selectors"]),
        "retained_control_selector_occurrences": len(proposal["retained_control_selectors"]),
        "execution_status": "blocked_whole_source_proposal_hold" if held else "not_executed_requires_fresh_native_session",
        "archived_origins_are_fresh_native_authority": False, "native_path_ids_reused": False,
        "native_evaluation_performed": False}


def load_inputs(directory, **limits):
    """Direct closed phase28 admission; no predecessor loader or producer call."""
    settings = _settings(limits)
    directory = Path(directory).resolve(strict=True)
    reader = parent.parent.parent.BoundedReader(settings)
    report, plan, rows, replay = (reader.read(directory / name) for name in
        ("report.json", "run-plan.json", "context-index.json", "native-replay-plan.json"))
    old._closed(report, ARCHIVE_REPORT_KEYS, "phase28_report")
    old._closed(plan, ARCHIVE_PLAN_KEYS, "phase28_plan")
    old._closed(replay, REPLAY_PLAN_KEYS, "phase28_replay_plan")
    if (report["version"] != parent.VERSION or plan["version"] != parent.VERSION or replay["version"] != parent.VERSION
            or report["status"] != "saved_source_proposal_probe_complete_not_evaluated"
            or any(report[k] is not True for k in ("computation_integrity_passed", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or any(report[k] != [] for k in ("changed_inputs_or_code", "changed_artifacts", "failures"))
            or any(report[k] is not False or plan[k] is not False for k in ARCHIVE_FALSE)
            or any(x["source_authority"] != parent.engine.AUTHORITY for x in (report, plan, replay))
            or report["parent_source_authority"] != parent.AUTHORITY or plan["parent_source_authority"] != parent.AUTHORITY
            or report["selected"] is not None or plan["selected"] is not None
            or report["fresh_native_preparations"] != 0 or plan["fresh_native_preparations"] != 0
            or report["native_replay_evaluations_performed"] != 0
            or replay["native_evaluations_performed"] != 0 or replay["fresh_native_sessions_prepared"] != 0
            or replay["same_completion_resolution_evaluated"] is not False or replay["winning_harmony_selected"] is not False
            or report["denominators"] != plan["denominators"]
            or type(report["artifact_hashes"]) is not dict or len(report["artifact_hashes"]) != 5):
        raise ValueError("completed_unselected_exact_phase28_creation_required")
    parent._settings(plan["settings"])
    for value in (report["distinct_registered_sources"], report["registered_policy_completion_rows"],
            report["saved_source_proposals"], report["computed_source_proposals"], report["whole_source_proposal_holds"],
            report["native_replay_planned_completion_requests"], replay["planned_completion_requests"],
            replay["retained_control_selector_occurrences"]):
        old._limit(value, "saved_phase28_count")
    protected = {}
    for mapping in (plan["inputs"], plan["code"], report["artifact_hashes"]):
        old._protect_map(protected, mapping)
    old._protect(protected, str(directory / "report.json"), old._file_sha(directory / "report.json"))
    inventories = [(directory, old._inventory(directory, report["artifact_hashes"], directory / "report.json"))]
    historical = {str(p.resolve()) for p in _code_paths()} - {str(p.resolve()) for p in _new_code_paths()}
    if set(plan["code"]) != historical:
        raise ValueError("exact_historical_phase28_code_inventory_required")
    if old._guard(protected):
        raise ValueError("registered_phase28_creation_SHA_changed")
    parent_directory = Path(plan["parent"]).resolve(strict=True)
    ancestors = []
    for version, report_keys, plan_keys in ((parent.parent.VERSION, parent.REPORT_KEYS, parent.PLAN_KEYS),
            (parent.parent.parent.VERSION, parent.parent.REPORT_KEYS, parent.parent.PLAN_KEYS),
            (parent.parent.parent.parent.VERSION, parent.parent.parent.REPORT_KEYS, parent.parent.parent.PLAN_KEYS)):
        ancestor_report, ancestor_plan, ancestor_rows = (reader.read(parent_directory / name)
            for name in ("report.json", "run-plan.json", "context-index.json"))
        old._closed(ancestor_report, report_keys, "registered_ancestor_report")
        old._closed(ancestor_plan, plan_keys, "registered_ancestor_plan")
        if (ancestor_report["version"] != version or ancestor_plan["version"] != version
                or ancestor_report["denominators"] != report["denominators"]
                or ancestor_plan["denominators"] != report["denominators"]):
            raise ValueError("unchanged_registered_ancestor_metadata_required")
        for mapping in (ancestor_report["artifact_hashes"], ancestor_plan["inputs"], ancestor_plan["code"]):
            for path, sha in mapping.items():
                if protected.get(path) != sha:
                    raise ValueError("complete_ancestor_creation_SHA_closure_required")
        inventory = old._inventory(parent_directory, ancestor_report["artifact_hashes"], parent_directory / "report.json")
        inventories.append((parent_directory, inventory))
        ancestors.append((ancestor_report, ancestor_plan, ancestor_rows))
        if len(ancestors) < 3:
            parent_directory = Path(ancestor_plan["parent"]).resolve(strict=True)
    if ([len(i) for _, i in inventories] != [6, 7, 7, 148]
            or plan["parent_inventories"] != [{"directory": str(p), "files": len(i)} for p, i in inventories[1:]]
            or protected.get(str(inventories[1][0] / "report.json")) != plan["parent_report_sha256"]):
        raise ValueError("exact_phase28_and_7_7_148_parent_inventories_required")
    if (report["parent_policy_summary"] != ancestors[0][0]["summary"]
            or plan["parent_policy_summary"] != ancestors[0][0]["summary"]
            or plan["parent_source_size_manifest"] != ancestors[0][1]["parent_source_size_manifest"]
            or plan["parent_selected_contexts"] != ancestors[2][1]["selected_contexts"]):
        raise ValueError("original_policy_summary_and_source_selection_must_remain_exact")
    denoms = report["denominators"]
    old._closed(denoms, parent.parent.parent.DENOMINATOR_KEYS, "registered_original_cohort")
    for value in denoms.values():
        old._limit(value, "registered_original_cohort")
    if (denoms["selected_contexts"] != 2 or denoms["registered_context_pool"] != 5
            or denoms["unexecuted_declared_contexts"] != denoms["declared_contexts"] - 2
            or denoms["unexecuted_declared_original_raw_lanes"] != denoms["declared_original_raw_lanes"] - denoms["selected_original_raw_lanes"]
            or type(rows) is not list or len(rows) != 2 or len(rows) > settings["max_contexts"]
            or type(replay["jobs"]) is not list or len(replay["jobs"]) != 4):
        raise ValueError("whole_registered_two_source_four_completion_admission_required")
    cases, records, expected_jobs = [], [], []
    policy_rows, contrast_rows, source_rows = (a[2] for a in ancestors)
    for row in rows:
        old._closed(row, ARCHIVE_ROW_KEYS, "phase28_context_index")
        if row["error"] is not None:
            raise ValueError("failed_saved_proposal_is_not_replay_admission")
        case = {"context_key": deepcopy(row["context_key"]), "source_identity_sha256": row["source_identity_sha256"],
            "full_IR": deepcopy(row["full_IR"]), "scope_info": deepcopy(row["scope"]),
            "lattice_info": deepcopy(row["native_lattice"]), "panel_info": deepcopy(row["prior_panel"]),
            "proposal_info": deepcopy(row["proposal"]), "original_source_files": deepcopy(row["original_source_files"]),
            "completion_controls": deepcopy(row["completion_controls"]), "parent_policy_rows": deepcopy(row["parent_policy_rows"])}
        info = row["full_IR"]
        old._closed(info, parent.parent.parent.IR_INFO_KEYS, "registered_full_IR")
        if (protected.get(info["artifact"]) != info["sha256"] or info["binding_match"] is not True
                or info["registered_full_IR_not_projection"] is not True):
            raise ValueError("registered_original_full_IR_required")
        ir = reader.read(info["artifact"])
        if ir["ir_document_id"] != info["ir_document_id"] or digest(ir) != info["ir_content_sha256"]:
            raise ValueError("registered_full_IR_content_binding_required")
        scope = _registered_record(row["scope"], old.expanded.PREFIX, reader, protected)
        lattice = _registered_record(row["native_lattice"], engine.native.PREFIX, reader, protected)
        panel = _registered_record(row["prior_panel"], parent.engine.prior.PREFIX, reader, protected)
        proposal = _registered_record(row["proposal"], parent.engine.PREFIX, reader, protected)
        case.update(ir=ir, scope=scope, lattice=lattice, panel=panel, proposal=proposal)
        if (scope["binding"] != old.expanded._binding(ir) or lattice["scope_ref"] != sealed._ref(scope)
                or lattice["binding"] != scope["binding"] or lattice["analysis_span"] != scope["analysis_span"]
                or panel["scope_ref"] != sealed._ref(scope) or panel["lattice_ref"] != sealed._ref(lattice)
                or row["original_source_files"] != ir["source_files"]):
            raise ValueError("exact_original_full_IR_scope_lattice_panel_binding_required")
        identity = digest({"context_key": row["context_key"], "full_IR": row["full_IR"], "scope": row["scope"],
            "native_lattice": row["native_lattice"], "source_panel": row["prior_panel"]})
        if identity != row["source_identity_sha256"] or any(c["source_identity_sha256"] == identity for c in cases):
            raise ValueError("two_distinct_exact_registered_source_identities_required")
        case["native_counts"] = parent._inventory(lattice, panel, scope, settings)
        if row["native_inventory"] != case["native_counts"]:
            raise ValueError("registered_native_inventory_count_mismatch")
        parent._validate_result(proposal, case, plan["settings"])
        if (row["summary"] != proposal["summary"] or row["query_plan"] != proposal["query_plan"]
                or row["status"] != proposal["status"] or row["reasons"] != proposal["reasons"]):
            raise ValueError("saved_proposal_row_body_join_required")
        original_policies = [r for r in policy_rows if r["context_key"] == row["context_key"]]
        if len(original_policies) != 2 or row["parent_policy_rows"] != original_policies:
            raise ValueError("both_exact_original_policy_controls_required")
        for original in original_policies:
            if (any(original[k] != row[k] for k in ("full_IR", "scope", "native_lattice", "original_source_files"))
                    or original["source_panel"] != row["prior_panel"]):
                raise ValueError("original_policy_source_registration_join_required")
        source_row = next(r for r in source_rows if r["context_key"] == row["context_key"])
        if len(row["completion_controls"]) != 2:
            raise ValueError("both_registered_completion_controls_required")
        for completion, policy_row, original in zip(row["completion_controls"], original_policies, source_row["completion_batches"]):
            old._closed(completion, COMPLETION_CONTROL_KEYS, "registered_completion_control")
            if (completion["kind"] != original["kind"] or completion["bundle"] != original["bundle"]
                    or completion["required_links"] != original["required_links"]
                    or completion["policy"] != policy_row["policy"] or completion["policy_status"] != policy_row["status"]
                    or completion["native_and_role_replay_executed"] is not False):
                raise ValueError("original_completion_links_and_policy_identity_required")
            parent.parent.parent._edge_signature(completion["required_links"])
            for info in (completion["bundle"], completion["policy"]):
                if protected.get(info["artifact"]) != info["sha256"]:
                    raise ValueError("registered_completion_creation_SHA_required")
            expected_jobs.append(_expected_job(row, proposal, completion))
        cases.append(case)
        records.append(proposal)
    for job in replay["jobs"]:
        old._closed(job, JOB_REQUEST_KEYS, "registered_later_replay_job")
    summary, known, unknown = parent._aggregate(records)
    planned = None if any(j["planned_selector_occurrences"] is None for j in expected_jobs) else sum(j["planned_selector_occurrences"] for j in expected_jobs)
    controls = sum(j["retained_control_selector_occurrences"] for j in expected_jobs)
    if (replay["jobs"] != expected_jobs or replay["planned_completion_requests"] != 4
            or replay["planned_selector_occurrences"] != planned or replay["retained_control_selector_occurrences"] != controls
            or report["summary"] != summary or report["known_summary_subtotal"] != known
            or report["unknown_summary_context_occurrences"] != unknown
            or report["distinct_registered_sources"] != 2 or report["registered_policy_completion_rows"] != 4
            or report["saved_source_proposals"] != 2 or report["native_replay_planned_completion_requests"] != 4
            or report["native_replay_planned_selector_occurrences"] != planned
            or report["computed_source_proposals"] != sum(r["status"] == "computed_source_progression_proposals_not_evaluated" for r in rows)
            or report["whole_source_proposal_holds"] != sum(r["status"] == "whole_source_proposal_hold" for r in rows)
            or report["submitted_source_proposal_computation_complete"] is not (all(r["status"] == "computed_source_progression_proposals_not_evaluated" for r in rows))
            or report["admitted_native_inventory"] != {k: sum(c["native_counts"][k] for c in cases) for k in case["native_counts"]}
            or sum(len(c["scope"]["raw_lanes"]) for c in cases) != denoms["selected_original_raw_lanes"]):
        raise ValueError("all_ordered_replay_jobs_summary_and_denominators_required")
    if old._guard(protected):
        raise ValueError("registered_inputs_changed_during_admission")
    return {"parent": directory, "report": report, "plan": plan, "rows": rows, "replay_plan": replay,
        "cases": cases, "hashes": protected, "inventories": inventories, "settings": settings,
        "reader_counts": {"files_read": reader.read_files, "decoded_bytes": reader.decoded_bytes}}


PLAN_KEYS = {"version", "proposal_ref", "scope_ref", "lattice_ref", "selector_inventory_sha256", "planned_selectors",
    "retained_control_selectors", "additional_selectors", "batches", "planned_batches", "planned_replay_work",
    "native_comparison_work", "role_explanation_work", "resource_limits", "status", "reasons", "flags", "semantics",
    "full_contrast_status", "record_id", "record_sha256"}
PLAN_BATCH_KEYS = {"batch_index", "selector_start", "selector_end_exclusive", "native_query_work", "role_query_work",
    "charged_native_comparisons", "charged_work"}
BINDING_KEYS = {"version", "contract", "source_binding", "scope_ref", "analysis_span", "logical_universe",
    "archived_lattice_ref", "fresh_lattice_ref", "proposal_ref", "prior_panel_ref", "origin_mappings", "key_mappings",
    "retained_control_selectors", "additional_selectors", "total_selectors", "selector_inventory_sha256",
    "fresh_native_preparations", "native_authority_issued", "status", "reasons", "selected", "rank", "confidence",
    "flags", "record_id", "record_sha256"}
JOB_KEYS = {"version", "contract", "binding_ref", "proposal_ref", "scope_ref", "lattice_ref", "analysis_span",
    "logical_universe", "plan_ref", "bundle_ref", "required_links", "fresh_registered_links", "bundle_status",
    "batch_refs", "resource_limits", "summary", "status", "reasons", "fresh_native_evaluation_performed",
    "same_completion_resolution_evaluated", "selected", "rank", "confidence", "flags", "full_contrast_status",
    "limitations", "record_id", "record_sha256"}
TRUTH_FIELDS = {"whole_ordinary_template_truths", "role_whole_ordinary_template_truths", "joint_functional_truths"}
CREDIT_FIELDS = {"known_conditional_explained_note_time_selector_occurrence_subtotal",
    "conditional_explained_note_time_selector_occurrence_sum"}
COUNT_FIELDS = {"planned_selectors", "native_computed_paths", "role_computed_paths", "withheld_native_paths",
    "withheld_role_paths", "planned_batches", "completed_batches", "native_comparison_calls", "role_preparation_calls",
    "role_explanation_calls", "fresh_bundle_registrations", "ordinary_individual_supported_occurrences",
    "raw_time_conserved_native_paths", "raw_time_conserved_role_paths", "unknown_role_accounts", "uncomputed_role_accounts",
    "computed_internal_transition_contexts", "declared_internal_function_contexts", "resolution_contexts_under_complete_bundle"}
SUMMARY_KEYS = COUNT_FIELDS | TRUTH_FIELDS | CREDIT_FIELDS | {"role_clause_status_occurrences"}
DEFERRED = "deferred_whole_competitor_adapter_required_not_batch_comparison"


def _flags(record):
    old._closed(record["flags"], engine._flags(), "unpromoted_replay_flags")
    if any(v is not False for v in record["flags"].values()) or record["version"] != engine.VERSION:
        raise ValueError("unpromoted_current_replay_record_required")


def _plan(record, case, limits):
    sealed._check(record, engine.PLAN_PREFIX)
    old._closed(record, PLAN_KEYS, "replay_plan")
    _flags(record)
    if (record["scope_ref"] != sealed._ref(case["scope"]) or record["lattice_ref"] != sealed._ref(case["lattice"])
            or record["proposal_ref"] != sealed._ref(case["proposal"])
            or record["selector_inventory_sha256"] != digest(case["proposal"]["selectors"])
            or record["resource_limits"] != limits or record["full_contrast_status"] != DEFERRED):
        raise ValueError("exact_all_selector_source_replay_plan_required")
    for key in ("planned_selectors", "retained_control_selectors", "additional_selectors", "planned_batches",
            "planned_replay_work", "native_comparison_work", "role_explanation_work"):
        old._limit(record[key], "replay_plan." + key)
    selectors = case["proposal"]["selectors"]
    if (record["planned_selectors"] != len(selectors)
            or record["retained_control_selectors"] != len(case["proposal"]["retained_control_selectors"])
            or record["additional_selectors"] != len(case["proposal"]["additional_selectors"])
            or type(record["batches"]) is not list or record["planned_batches"] != len(record["batches"])):
        raise ValueError("all_planned_selector_occurrence_denominators_required")
    position = 0
    for index, batch in enumerate(record["batches"]):
        old._closed(batch, PLAN_BATCH_KEYS, "planned_replay_batch")
        for key, value in batch.items():
            old._limit(value, "planned_replay_batch." + key)
        end = min(position + limits["batch_size"], len(selectors))
        if (batch["batch_index"] != index or batch["selector_start"] != position
                or batch["selector_end_exclusive"] != end or end <= position
                or batch["charged_native_comparisons"] != 2
                or batch["charged_work"] != 2 * batch["native_query_work"] + batch["role_query_work"]):
            raise ValueError("ordered_complete_replay_batch_plan_required")
        position = end
    if (position != len(selectors) or record["planned_replay_work"] != sum(b["charged_work"] for b in record["batches"])
            or record["native_comparison_work"] != sum(2 * b["native_query_work"] for b in record["batches"])
            or record["role_explanation_work"] != sum(b["role_query_work"] for b in record["batches"])
            or record["planned_replay_work"] != record["native_comparison_work"] + record["role_explanation_work"]):
        raise ValueError("exact_replay_whole_work_sum_required")
    parent._strings(record["reasons"], "replay_plan.reasons")
    if record["status"] not in ("ready_native_role_batches", "whole_source_replay_request_hold"):
        raise ValueError("typed_whole_replay_plan_status_required")
    if (record["status"] == "ready_native_role_batches") is not (not record["reasons"]):
        raise ValueError("replay_plan_status_reason_consistency_required")


def _binding(record, case, fresh):
    sealed._check(record, engine.BINDING_PREFIX)
    old._closed(record, BINDING_KEYS, "fresh_replay_binding")
    _flags(record)
    if (record["contract"] != engine._contract()
            or record["source_binding"] != case["scope"]["binding"] or record["scope_ref"] != sealed._ref(case["scope"])
            or record["archived_lattice_ref"] != sealed._ref(case["lattice"])
            or record["proposal_ref"] != sealed._ref(case["proposal"]) or record["prior_panel_ref"] != sealed._ref(case["panel"])
            or record["analysis_span"] != case["scope"]["analysis_span"] or record["logical_universe"] != case["lattice"]["universe"]
            or record["selector_inventory_sha256"] != digest(case["proposal"]["selectors"])
            or any(record[k] is not None for k in ("selected", "rank", "confidence"))):
        raise ValueError("exact_original_full_source_replay_binding_required")
    for key in ("retained_control_selectors", "additional_selectors", "total_selectors", "fresh_native_preparations"):
        old._limit(record[key], "fresh_binding." + key)
    if (record["total_selectors"] != len(case["proposal"]["selectors"])
            or record["retained_control_selectors"] != len(case["proposal"]["retained_control_selectors"])
            or record["additional_selectors"] != len(case["proposal"]["additional_selectors"])
            or record["fresh_native_preparations"] not in (0, 1) or type(record["native_authority_issued"]) is not bool):
        raise ValueError("typed_fresh_binding_counts_required")
    ready = record["status"] == "ready_fresh_source_proposal_replay"
    if record["status"] not in ("ready_fresh_source_proposal_replay", "whole_source_rebind_hold"):
        raise ValueError("typed_whole_rebind_status_required")
    if ready:
        if not record["native_authority_issued"] or record["fresh_native_preparations"] != 1 or fresh is None or fresh != case["lattice"]:
            raise ValueError("fresh_complete_supplier_equality_required")
        if record["fresh_lattice_ref"] != sealed._ref(fresh):
            raise ValueError("exact_fresh_lattice_receipt_required")
        used = {oid for s in case["proposal"]["selectors"] for oid in s["origin_ids"]}
        expected_origins = [{"archived_ref": sealed._ref(o), "fresh_ref": sealed._ref(o), "catalog_id": e["catalog_id"],
            "point_indices": deepcopy(e["point_indices"]), "exact_complete_origin_body_match": True}
            for e in fresh["catalog_inventory"] for o in e["origins"] if o["record_id"] in used]
        expected_keys = [{"archived_ref": sealed._ref(k), "fresh_ref": sealed._ref(k), "exact_complete_key_body_match": True} for k in fresh["keys"]]
        if record["origin_mappings"] != expected_origins or record["key_mappings"] != expected_keys:
            raise ValueError("complete_exact_ordered_supplier_origin_and_key_binding_required")
    elif record["native_authority_issued"] or fresh is not None or record["origin_mappings"] or record["key_mappings"]:
        raise ValueError("whole_rebind_hold_cannot_supply_partial_native_authority")
    parent._strings(record["reasons"], "fresh_binding.reasons")
    if ready is not (not record["reasons"]):
        raise ValueError("fresh_binding_status_reason_consistency_required")


def _empty_counts(planned, batches):
    result = {key: 0 for key in COUNT_FIELDS}
    result.update(planned_selectors=planned, planned_batches=batches)
    result.update({key: {name: 0 for name in ("true", "false", "unknown")} for key in TRUTH_FIELDS})
    result.update(role_clause_status_occurrences={}, known_conditional_explained_note_time_selector_occurrence_subtotal=q(0),
        conditional_explained_note_time_selector_occurrence_sum=None if planned else q(0))
    return result


def _truth(value):
    if value is not None and type(value) is not bool:
        raise ValueError("strict_conditional_evidence_tristate_required")
    return "unknown" if value is None else "true" if value else "false"


def _add_batch(counts, comparison, explanation, bundle):
    counts["native_comparison_calls"] += 2
    counts["role_preparation_calls"] += 1
    counts["role_explanation_calls"] += 1
    counts["native_computed_paths"] += len(comparison["paths"])
    counts["role_computed_paths"] += len(explanation["paths"])
    counts["raw_time_conserved_native_paths"] += len(comparison["paths"])
    counts["raw_time_conserved_role_paths"] += len(explanation["paths"])
    if comparison["status"] != "whole_comparison_hold" and explanation["status"] != "whole_explanation_hold":
        counts["completed_batches"] += 1
    for path in comparison["paths"]:
        for context in path["transition_contexts"]:
            counts["computed_internal_transition_contexts"] += 1
            if context["function_shape"] is not None:
                counts["declared_internal_function_contexts"] += 1
                if bundle["status"] == "complete_all_lane_witness":
                    counts["resolution_contexts_under_complete_bundle"] += 1
            counts["joint_functional_truths"][_truth(context["joint_conditional_functional_evidence"])] += 1
            ordinary = context["ordinary_strategy"]
            counts["whole_ordinary_template_truths"][_truth(None if ordinary is None else ordinary["whole_ordinary_template_satisfied"])] += 1
            if ordinary:
                for row in ordinary["role_assessments"]:
                    for occurrence in row["occurrences"]:
                        value = occurrence["satisfied_under_this_bundle"]
                        if type(value) is not bool:
                            raise ValueError("strict_ordinary_occurrence_boolean_required")
                        counts["ordinary_individual_supported_occurrences"] += value
    credit = f(counts["known_conditional_explained_note_time_selector_occurrence_subtotal"])
    for path in explanation["paths"]:
        for template in path["ordinary_templates"]:
            counts["role_whole_ordinary_template_truths"][_truth(template["satisfied"])] += 1
        for clause in path["clauses"]:
            status = clause["status"]
            counts["role_clause_status_occurrences"][status] = counts["role_clause_status_occurrences"].get(status, 0) + 1
        value = path["account"]["conditional_explanation_note_time_quarters"]
        if value is None:
            counts["unknown_role_accounts"] += 1
        else:
            credit += parent._rational(value, "conditional_explanation_credit")
    counts["known_conditional_explained_note_time_selector_occurrence_subtotal"] = q(credit)


def _finish_counts(counts, held=False):
    counts["withheld_native_paths"] = counts["planned_selectors"] - counts["native_computed_paths"]
    counts["withheld_role_paths"] = counts["planned_selectors"] - counts["role_computed_paths"]
    counts["uncomputed_role_accounts"] = counts["withheld_role_paths"]
    counts["conditional_explained_note_time_selector_occurrence_sum"] = None if (held or
        counts["unknown_role_accounts"] or counts["uncomputed_role_accounts"]) else deepcopy(
            counts["known_conditional_explained_note_time_selector_occurrence_subtotal"])


def _summary(summary):
    old._closed(summary, SUMMARY_KEYS, "source_replay_job_summary")
    for key in COUNT_FIELDS:
        old._limit(summary[key], "source_replay_summary." + key)
    for key in TRUTH_FIELDS:
        old._closed(summary[key], {"true", "false", "unknown"}, "conditional_truth_denominators")
        for value in summary[key].values():
            old._limit(value, "conditional_truth_count")
    statuses = summary["role_clause_status_occurrences"]
    if type(statuses) is not dict or set(statuses) - {"supported", "failed", "unassessed"}:
        raise ValueError("typed_role_clause_status_occurrences_required")
    for value in statuses.values():
        old._limit(value, "role_status_count")
    for key in CREDIT_FIELDS:
        if summary[key] is not None and parent._rational(summary[key], key) < 0:
            raise ValueError("nonnegative_exact_credit_required")
    if summary["known_conditional_explained_note_time_selector_occurrence_subtotal"] is None:
        raise ValueError("known_credit_subtotal_cannot_be_unknown")


def _job(record, case, binding, plan, bundle, completion, refs, counts, limits, reasons):
    sealed._check(record, engine.PREFIX)
    old._closed(record, JOB_KEYS, "terminal_replay_job")
    _flags(record)
    reasons = sorted(set(reasons))
    _finish_counts(counts, bool(reasons))
    _summary(record["summary"])
    if (record["contract"] != engine._contract() or record["contract"] != binding["contract"]
            or record["reasons"] != reasons or record["summary"] != counts or record["binding_ref"] != sealed._ref(binding)
            or record["proposal_ref"] != sealed._ref(case["proposal"]) or record["scope_ref"] != sealed._ref(case["scope"])
            or record["lattice_ref"] != sealed._ref(case["lattice"]) or record["plan_ref"] != sealed._ref(plan)
            or record["bundle_ref"] != (None if bundle is None else sealed._ref(bundle))
            or record["analysis_span"] != case["scope"]["analysis_span"] or record["logical_universe"] != case["lattice"]["universe"]
            or record["batch_refs"] != refs or record["required_links"] != completion["required_links"] or record["resource_limits"] != limits
            or record["fresh_registered_links"] != (None if bundle is None else bundle["materialized_witness_links"])
            or record["bundle_status"] != (None if bundle is None else bundle["status"])
            or any(record[k] is not None for k in ("selected", "rank", "confidence"))
            or record["fresh_native_evaluation_performed"] is not (counts["native_computed_paths"] > 0)
            or record["same_completion_resolution_evaluated"] is not (counts["resolution_contexts_under_complete_bundle"] > 0)
            or record["full_contrast_status"] != DEFERRED):
        raise ValueError("exact_all_submitted_terminal_replay_join_and_counts_required")
    parent._strings(record["reasons"], "terminal_replay.reasons")
    complete = not record["reasons"] and counts["completed_batches"] == plan["planned_batches"]
    expected = "computed_native_role_source_requests_not_selected" if complete else (
        "whole_source_replay_request_hold" if not refs else "incomplete_native_role_source_replay")
    if record["status"] != expected:
        raise ValueError("whole_holds_and_partial_batches_are_not_complete")


class OutputBudgetExceeded(ValueError):
    pass


class _Writer:
    """Exclusive new-file writer; reserve final manifests before body writes."""
    def __init__(self, output, settings):
        self.output, self.settings = output, settings
        self.artifacts, self.saved, self.bytes = {}, {}, 0
        self.partial_files = []

    def _encoded(self, value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")

    def _write(self, path, raw, body=False, register=True):
        remaining = self.settings["max_total_output_bytes"] - self.bytes
        if body:
            remaining -= self.settings["manifest_reserve_bytes"]
        if len(raw) > remaining:
            raise OutputBudgetExceeded("total_new_output_byte_budget_before_exclusive_write")
        # Reserve the complete attempt before opening. A partial disk write
        # cannot create an uncharged fragment or free space for later bodies.
        self.bytes += len(raw)
        created = False
        try:
            path.parent.mkdir(exist_ok=True)
            with path.open("xb") as stream:
                created = True
                if stream.write(raw) != len(raw):
                    raise OSError("short_exclusive_output_write")
        except Exception:
            if created and path.is_file():
                self.artifacts[str(path)] = old._file_sha(path)
                self.partial_files.append({"artifact": str(path), "sha256": self.artifacts[str(path)],
                    "physical_bytes": path.stat().st_size, "reserved_attempt_bytes": len(raw)})
            raise
        if register:
            self.artifacts[str(path)] = old._file_sha(path)

    def json(self, name, value, register=True):
        self._write(self.output / name, self._encoded(value), register=register)

    def record(self, folder, value, prefix):
        sealed._check(value, prefix)
        if re.fullmatch(r"[a-z0-9_]+", value["record_id"]) is None or len(value["record_id"]) > 64:
            raise ValueError("closed_generated_record_filename_required")
        raw = self._encoded(value)
        if len(raw) > self.settings["max_output_record_bytes"]:
            raise OutputBudgetExceeded("whole_source_replay_output_record_byte_budget")
        marker, body = (folder, value["record_id"]), digest(value)
        if marker in self.saved:
            prior_digest, info = self.saved[marker]
            if prior_digest != body or old._file_sha(info["artifact"]) != info["sha256"]:
                raise ValueError("source_replay_record_collision_or_changed_artifact")
            return deepcopy(info)
        compressed = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as stream:
            stream.write(raw)
        path = self.output / folder / (value["record_id"] + ".json.gz")
        if len(str(path)) > 4096:
            raise ValueError("bounded_artifact_path_required")
        self._write(path, compressed.getvalue(), body=True)
        info = {"artifact": str(path), "sha256": self.artifacts[str(path)], "record_ref": sealed._ref(value), "status": value["status"]}
        self.saved[marker] = body, info
        return info


def _aggregate(summaries, incomplete_jobs=0):
    total, credit = _empty_counts(0, 0), Fraction()
    unknown_sum = bool(incomplete_jobs)
    for summary in summaries:
        _summary(summary)
        for key in COUNT_FIELDS:
            total[key] += summary[key]
        for key in TRUTH_FIELDS:
            for name, value in summary[key].items():
                total[key][name] += value
        for name, value in summary["role_clause_status_occurrences"].items():
            total["role_clause_status_occurrences"][name] = total["role_clause_status_occurrences"].get(name, 0) + value
        credit += f(summary["known_conditional_explained_note_time_selector_occurrence_subtotal"])
        unknown_sum |= summary["conditional_explained_note_time_selector_occurrence_sum"] is None
    total["known_conditional_explained_note_time_selector_occurrence_subtotal"] = q(credit)
    total["conditional_explained_note_time_selector_occurrence_sum"] = None if unknown_sum else q(credit)
    return total


def _unpromoted(value):
    """Reject promoted nested snapshots, without replaying music predicates."""
    if type(value) is dict:
        verdict_record = str(value.get("record_id", "")).startswith(("fmilpath_", "fmiltuple_", "fmilfunction_", "fmnrolepath_", "fmnroleclause_"))
        for key, item in value.items():
            if key == "flags":
                if type(item) is not dict or any(v is not False for v in item.values()):
                    raise ValueError("unpromoted_nested_batch_flags_required")
            elif key in ("selected", "rank", "confidence") and item is not None and not (
                    key == "selected" and item is False and not verdict_record):
                raise ValueError("no_selected_rank_or_confidence_in_replay_batch")
            else:
                _unpromoted(item)
    elif type(value) is list:
        for item in value:
            _unpromoted(item)


def _batch(comparison, explanation, selectors, case, bundle, planned, limits):
    engine._validate_batch(comparison, explanation, selectors, case["scope"], case["lattice"], bundle)
    for record, module, status, resources in (
            (comparison, engine.native, "computed_native_multi_slot_comparison_not_selected",
                {"max_hypotheses": limits["batch_size"], "max_slots": limits["max_slots"],
                 "query_work_budget": limits["native_query_work_budget"]}),
            (explanation, engine.roles, "computed_native_role_explanations_not_selected",
                {"query_work_budget": limits["role_query_work_budget"]})):
        _unpromoted(record)
        if (record["version"] != module.VERSION or record["contract"] != module._contract()
                or record["resource_limits"] != resources or record["flags"] != module._flags()
                or any(record[k] is not None for k in ("selected", "rank", "confidence"))
                or record["analysis_span"] != case["scope"]["analysis_span"]
                or record["logical_universe"] != case["lattice"]["universe"]):
            raise ValueError("current_exact_batch_contract_resources_and_source_required")
        parent._strings(record["reasons"], "batch.reasons")
        held_status = "whole_comparison_hold" if record is comparison else "whole_explanation_hold"
        if record["status"] not in (status, held_status) or (record["status"] == held_status) is not bool(record["reasons"]):
            raise ValueError("batch_status_reasons_consistency_required")
        if record["status"] == held_status and record["paths"]:
            raise ValueError("whole_batch_hold_cannot_save_favorable_prefix")
        for key, value in record["query_plan"].items():
            if key == "unique_literal_coordinate_times":
                if type(value) is not list:
                    raise ValueError("typed_literal_coordinate_list_required")
                coordinates = [parent._rational(t, "literal_coordinate") for t in value]
                if coordinates != sorted(set(coordinates)):
                    raise ValueError("ordered_unique_literal_coordinates_required")
            elif key != "semantics":
                old._limit(value, "batch_query_plan." + key)
    if (comparison["bundle_status"] != bundle["status"]
            or comparison["query_plan"]["planned_query_work"] != planned["native_query_work"]
            or explanation["query_plan"]["planned_query_work"] != planned["role_query_work"]
            or explanation["native_request"] != {key: comparison[key] for key in (
                "selectors", "resource_limits", "status", "reasons", "summary", "query_plan")}):
        raise ValueError("exact_planned_batch_work_and_native_snapshot_required")
    summary = comparison["summary"]
    old._closed(summary, {"planned_selectors", "computed_selectors", "planned_slot_occurrences", "planned_query_work",
        "computed_internal_transitions", "raw_time_equal_between_competitors", "all_logical_paths_evaluated"}, "native_batch_summary")
    for key in ("planned_selectors", "computed_selectors", "planned_slot_occurrences", "planned_query_work", "computed_internal_transitions"):
        old._limit(summary[key], "native_batch_summary." + key)
    if (summary["planned_selectors"] != len(selectors) or summary["computed_selectors"] != len(comparison["paths"])
            or summary["planned_slot_occurrences"] != sum(len(s["origin_ids"]) for s in selectors)
            or summary["planned_query_work"] != planned["native_query_work"]
            or summary["computed_internal_transitions"] != sum(len(p["transition_contexts"]) for p in comparison["paths"])
            or summary["raw_time_equal_between_competitors"] is not bool(comparison["paths"])
            or summary["all_logical_paths_evaluated"] is not False):
        raise ValueError("exact_native_batch_summary_required")
    role_storage._validate_role_summary(explanation, comparison)


def _header(packet, case, binding, plan, completion, limits):
    old._closed(packet, {"packet_type", "binding_ref", "plan", "bundle", "status", "reasons"}, "replay_header")
    reasons = sorted(set(plan["reasons"] + binding["reasons"]))
    if (packet["packet_type"] != "header" or packet["binding_ref"] != sealed._ref(binding)
            or packet["plan"] != plan or packet["reasons"] != reasons
            or packet["status"] != ("whole_source_replay_request_hold" if reasons else "ready_native_role_batches")):
        raise ValueError("exact_predeclared_header_plan_binding_and_reasons_required")
    bundle = packet["bundle"]
    if reasons:
        if bundle is not None:
            raise ValueError("whole_header_hold_cannot_register_bundle")
        return None, reasons
    sealed._check(bundle, engine.native.BUNDLE_PREFIX)
    normalized = [list(pair) for pair in sorted({tuple(pair) for pair in completion["required_links"]})]
    if (bundle["version"] != engine.native.VERSION or bundle["contract"] != engine.native._contract()
            or bundle["scope_ref"] != sealed._ref(case["scope"]) or bundle["lattice_ref"] != sealed._ref(case["lattice"])
            or bundle["binding"] != case["scope"]["binding"] or bundle["analysis_span"] != case["scope"]["analysis_span"]
            or bundle["required_links"] != normalized or bundle["all_no_link_control"] is not (not normalized)
            or bundle["covered_lanes"] != sorted([r["part_id"], r["voice_id"]] for r in case["scope"]["raw_lanes"])
            or bundle["resource_limits"] != {"geometry_work_budget": limits["geometry_work_budget"]}
            or bundle["all_unrequired_edges_left_unconnected"] is not True or bundle["flags"] != engine.native._flags()):
        raise ValueError("fresh_bundle_exact_original_completion_and_scope_required")
    parent._strings(bundle["reasons"], "fresh_bundle.reasons")
    if (bundle["status"] not in ("complete_all_lane_witness", "all_lane_witness_withheld")
            or (bundle["status"] == "complete_all_lane_witness") is not (not bundle["reasons"])
            or (not bundle["reasons"] and bundle["materialized_witness_links"] != normalized)):
        raise ValueError("fresh_bundle_whole_witness_status_required")
    _unpromoted(bundle)
    return bundle, reasons


def _case_row(case, plan):
    row = {"context_key": deepcopy(case["context_key"]), "source_identity_sha256": case["source_identity_sha256"],
        "full_IR": deepcopy(case["full_IR"]), "scope": deepcopy(case["scope_info"]),
        "archived_lattice": deepcopy(case["lattice_info"]), "prior_panel": deepcopy(case["panel_info"]),
        "source_proposal": deepcopy(case["proposal_info"]), "original_source_files": deepcopy(case["original_source_files"]),
        "parent_policy_rows": deepcopy(case["parent_policy_rows"]), "native_inventory": deepcopy(case["native_counts"]),
        "plan": None, "binding": None, "fresh_lattice": None, "status": "not_started", "error": None, "jobs": []}
    for control in case["completion_controls"]:
        row["jobs"].append({"completion_kind": control["kind"], "original_control": deepcopy(control),
            "plan": None, "header": None, "bundle": None, "job": None, "batches": [], "summary": None,
            "persisted_batch_prefix_summary": None, "status": "not_started", "error": None,
            "planned_selector_occurrences": plan["planned_selectors"], "planned_batches": plan["planned_batches"],
            "unpersisted_selector_ranges": [[0, plan["planned_selectors"]]] if plan["planned_selectors"] else [],
            "received_batch_packets": 0, "runtime_activity_after_last_persisted_batch": None})
    return row


def _error(exc):
    return (type(exc).__name__ + ":" + str(exc))[:1024]


def run(directory, output, *, progress_callback=None, **limits):
    """Fresh bridge once/source, exhaustive ordered streaming, exclusive storage.

    Calling this function executes fresh producers. Merely importing this module
    or admitting an archive does not. Actual corpus execution is caller-owned.
    """
    started, output = perf_counter(), Path(output).resolve()
    settings = _settings(limits)
    if output.exists() or output.parent != (ROOT / "output").resolve() or len(str(output)) > 2048:
        raise ValueError("append_only_new_direct_workspace_output_required")
    if progress_callback is not None and not callable(progress_callback):
        raise ValueError("callable_progress_observer_required")
    observer_errors = []
    def notify(event, **values):
        if progress_callback is not None:
            try:
                progress_callback(deepcopy({"event": event, "elapsed_seconds": perf_counter() - started, **values}))
            except Exception as exc:
                if len(observer_errors) < 8:
                    observer_errors.append(_error(exc))
    notify("admission_started")
    data = load_inputs(directory, **settings)
    code = {str(p.resolve()): old._file_sha(p) for p in _code_paths()}
    protected = deepcopy(data["hashes"])
    old._protect_map(protected, code)
    replay_limits = {key: settings[key] for key in engine.DEFAULTS}
    plans, rows, baselines = [], [], []
    for case in data["cases"]:
        plan = engine.plan_saved(case["scope"], case["lattice"], case["proposal"], prior_panel=case["panel"], **replay_limits)
        _plan(plan, case, replay_limits)
        plans.append(plan)
        rows.append(_case_row(case, plan))
        baselines.append(digest([case[k] for k in ("ir", "scope", "lattice", "panel", "proposal")]))
    planned_jobs = sum(len(row["jobs"]) for row in rows)
    planned_selectors = sum(j["planned_selector_occurrences"] for row in rows for j in row["jobs"])
    planned_batches = sum(j["planned_batches"] for row in rows for j in row["jobs"])
    run_plan = {"version": VERSION, "parent": str(data["parent"]), "inputs": deepcopy(data["hashes"]), "code": code,
        "settings": settings, "denominators": deepcopy(data["report"]["denominators"]),
        "reader_counts": deepcopy(data["reader_counts"]), "parent_report_sha256": old._file_sha(data["parent"] / "report.json"),
        "parent_inventories": [{"directory": str(p), "files": len(i)} for p, i in data["inventories"]],
        "source_authority": AUTHORITY, "parent_source_authority": data["report"]["source_authority"],
        "planned_distinct_sources": len(rows), "planned_completion_requests": planned_jobs,
        "planned_selector_occurrences": planned_selectors, "planned_batches": planned_batches,
        "planned_replay_work_all_completions": sum(len(r["jobs"]) * p["planned_replay_work"] for r, p in zip(rows, plans)),
        "replay_work_budget_scope": "per_original_completion_not_global_CPU_RSS_or_accuracy",
        "full_contrast_status": DEFERRED, "selected": None, "flags": engine._flags()}
    writer = _Writer(output, settings)
    # Bounded metadata rows/summaries/errors plus fixed-size sealed references
    # give a conservative predeclared manifest bound, checked again exactly at
    # finalization. Bodies may never consume this reserved physical capacity.
    if any(len(writer._encoded(row)) > 65536 for row in rows):
        raise OutputBudgetExceeded("bounded_source_metadata_required_before_output")
    manifest_bound = len(writer._encoded(run_plan)) + len(writer._encoded(rows)) + planned_batches * 24576 + planned_jobs * 65536 + len(rows) * 65536 + 262144
    if manifest_bound > settings["manifest_reserve_bytes"]:
        raise OutputBudgetExceeded("predeclared_manifest_reserve_insufficient_before_output")
    if old._guard(protected):
        raise ValueError("registered_inputs_or_code_changed_before_output")
    notify("admission_complete", sources=len(rows), jobs=planned_jobs, selectors=planned_selectors,
        batches=planned_batches, planned_replay_work=run_plan["planned_replay_work_all_completions"])
    output.mkdir()
    writer.json("run-plan.json", run_plan)
    failures, terminal_summaries, stop = [], [], False
    preparation_calls = 0
    for source_index, (case, plan, row, baseline) in enumerate(zip(data["cases"], plans, rows, baselines)):
        if stop:
            row["status"] = "not_started_output_budget_or_write_failure"
            for job in row["jobs"]:
                job["status"] = row["status"]
            continue
        try:
            row["plan"] = writer.record("plans", plan, engine.PLAN_PREFIX)
            notify("source_prepare_started", source_index=source_index, context_key=case["context_key"], output_reserved_bytes=writer.bytes)
            preparation_calls += 1
            handle = engine.prepare_replay(case["ir"], case["scope"], case["lattice"], case["proposal"], prior_panel=case["panel"])
            binding, fresh = engine.binding_prepared(handle), engine.lattice_prepared(handle)
            _binding(binding, case, fresh)
            row["binding"] = writer.record("bindings", binding, engine.BINDING_PREFIX)
            if fresh is not None:
                row["fresh_lattice"] = writer.record("lattices", fresh, engine.native.PREFIX)
            notify("source_prepare_complete", source_index=source_index, binding_status=binding["status"], output_reserved_bytes=writer.bytes)
            row["status"] = binding["status"]
            for job_index, (completion, job) in enumerate(zip(case["completion_controls"], row["jobs"])):
                job["plan"] = deepcopy(row["plan"])
                if stop:
                    job["status"] = "not_started_output_budget_or_write_failure"
                    continue
                counts = _empty_counts(plan["planned_selectors"], plan["planned_batches"])
                refs, bundle, reasons = [], None, []
                stream = None
                notify("job_started", source_index=source_index, job_index=job_index, completion_kind=completion["kind"])
                try:
                    stream = iter(engine.stream_prepared(handle, completion["required_links"], **replay_limits))
                    header = next(stream)
                    bundle, reasons = _header(header, case, binding, plan, completion, replay_limits)
                    job["header"] = {"binding_ref": deepcopy(header["binding_ref"]), "plan_ref": sealed._ref(plan),
                        "status": header["status"], "reasons": deepcopy(reasons)}
                    if bundle is not None:
                        job["bundle"] = writer.record("bundles", bundle, engine.native.BUNDLE_PREFIX)
                        counts["fresh_bundle_registrations"] = 1
                    expected_batches = [] if reasons else plan["batches"]
                    for planned in expected_batches:
                        batch_started = perf_counter()
                        packet = next(stream)
                        old._closed(packet, {"packet_type", "batch_index", "selector_start", "selector_end_exclusive", "comparison", "explanation"}, "replay_batch_packet")
                        job["received_batch_packets"] += 1
                        if (packet["packet_type"] != "batch" or any(type(packet[k]) is not int or packet[k] != planned[k]
                                for k in ("batch_index", "selector_start", "selector_end_exclusive"))):
                            raise ValueError("all_ordered_indexed_packet_positions_required")
                        comparison, explanation = packet["comparison"], packet["explanation"]
                        lo, hi = planned["selector_start"], planned["selector_end_exclusive"]
                        _batch(comparison, explanation, case["proposal"]["selectors"][lo:hi], case, bundle, planned, replay_limits)
                        comparison_info = writer.record("comparisons", comparison, engine.native.COMPARISON_PREFIX)
                        explanation_info = writer.record("explanations", explanation, engine.roles.PREFIX)
                        refs.append({**deepcopy(planned), "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)})
                        _add_batch(counts, comparison, explanation, bundle)
                        job["batches"].append({**deepcopy(planned), "comparison": comparison_info, "explanation": explanation_info})
                        job["unpersisted_selector_ranges"] = [[hi, plan["planned_selectors"]]] if hi < plan["planned_selectors"] else []
                        if comparison["status"] == "whole_comparison_hold" or explanation["status"] == "whole_explanation_hold":
                            reasons.extend(["unexpected_runtime_batch_hold", *comparison["reasons"], *explanation["reasons"]])
                        notify("batch_saved", source_index=source_index, job_index=job_index, batch_index=planned["batch_index"],
                            selector_end_exclusive=hi, planned_selectors=plan["planned_selectors"], batch_seconds=perf_counter() - batch_started,
                            output_reserved_bytes=writer.bytes)
                        del comparison, explanation, packet
                    terminal = next(stream)
                    old._closed(terminal, {"packet_type", "record"}, "terminal_replay_packet")
                    if terminal["packet_type"] != "summary":
                        raise ValueError("terminal_summary_after_all_batches_required")
                    record = terminal["record"]
                    _job(record, case, binding, plan, bundle, completion, refs, counts, replay_limits, reasons)
                    if len(writer._encoded(record["summary"])) > 32768:
                        raise OutputBudgetExceeded("bounded_terminal_summary_metadata_required")
                    try:
                        next(stream)
                    except StopIteration:
                        pass
                    else:
                        raise ValueError("extra_packet_after_terminal_not_complete")
                    job["job"] = writer.record("jobs", record, engine.PREFIX)
                    job["summary"], job["status"] = deepcopy(counts), record["status"]
                    job["runtime_activity_after_last_persisted_batch"] = False
                    terminal_summaries.append(deepcopy(counts))
                    notify("job_finished", source_index=source_index, job_index=job_index, status=record["status"], output_reserved_bytes=writer.bytes)
                except Exception as exc:
                    _finish_counts(counts, True)
                    job["persisted_batch_prefix_summary"] = deepcopy(counts)
                    job["status"], job["error"] = "incomplete_replay_storage_or_stream_failure", _error(exc)
                    failures.append({"source_index": source_index, "job_index": job_index, "error": job["error"]})
                    stop |= isinstance(exc, (OutputBudgetExceeded, OSError))
                    notify("job_failed", source_index=source_index, job_index=job_index, error=job["error"])
                finally:
                    close = getattr(stream, "close", None)
                    if close is not None:
                        close()
                    stream = packet = comparison = explanation = record = None
            del handle, fresh
            if digest([case[k] for k in ("ir", "scope", "lattice", "panel", "proposal")]) != baseline:
                raise ValueError("fresh_replay_modified_registered_source_snapshot")
        except Exception as exc:
            row["status"], row["error"] = "fresh_source_replay_failure", _error(exc)
            failures.append({"source_index": source_index, "job_index": None, "error": row["error"]})
            for job in row["jobs"]:
                if job["status"] == "not_started":
                    job["status"] = "not_started_source_preparation_failure"
            stop |= isinstance(exc, (OutputBudgetExceeded, OSError))
            notify("source_failed", source_index=source_index, error=row["error"])
    jobs = [job for row in rows for job in row["jobs"]]
    changed, changed_artifacts = old._guard(protected), old._guard(writer.artifacts)
    if {str(p.resolve()) for p in _code_paths()} != set(code):
        changed.append("creation_code_inventory_changed")
    for path, inventory in data["inventories"]:
        if {str(p.resolve()) for p in path.rglob("*") if p.is_file()} != inventory:
            changed.append("registered_parent_inventory_changed:" + str(path))
    if {str(p.resolve()) for p in output.rglob("*") if p.is_file()} != set(writer.artifacts):
        changed_artifacts.append("new_artifact_inventory_changed")
    complete = sum(job["status"] == "computed_native_role_source_requests_not_selected" for job in jobs)
    holds = sum(job["status"] == "whole_source_replay_request_hold" for job in jobs)
    missing_terminals = sum(job["job"] is None for job in jobs)
    incomplete = planned_jobs - complete - holds
    integrity = not failures and not changed and not changed_artifacts and not writer.partial_files
    all_position_summaries = []
    for job in jobs:
        summary = job["summary"] or job["persisted_batch_prefix_summary"]
        if summary is None:
            summary = _empty_counts(job["planned_selector_occurrences"], job["planned_batches"])
            _finish_counts(summary, True)
        all_position_summaries.append(summary)
    report = {"version": VERSION, "status": "fresh_source_replay_saved_not_selected" if integrity else "fresh_source_replay_incomplete",
        "source_authority": AUTHORITY, "selected": None, "flags": engine._flags(), "full_contrast_status": DEFERRED,
        "computation_integrity_passed": integrity, "inputs_and_code_unchanged": not changed, "artifacts_unchanged": not changed_artifacts,
        "changed_inputs_or_code": changed, "changed_artifacts": changed_artifacts, "failures": failures,
        "artifact_hashes": deepcopy(writer.artifacts), "denominators": deepcopy(data["report"]["denominators"]),
        "planned_distinct_sources": len(rows), "planned_completion_requests": planned_jobs, "planned_selector_occurrences": planned_selectors,
        "planned_batches": planned_batches, "saved_terminal_jobs": len(terminal_summaries), "computed_completion_requests": complete,
        "whole_completion_holds": holds, "incomplete_or_unstarted_completion_requests": incomplete,
        "missing_terminal_completion_requests": missing_terminals,
        "submitted_nonempty_requests_completed": bool(integrity and planned_selectors and jobs and complete == planned_jobs),
        "known_empty_request_set": bool(integrity and jobs and planned_selectors == 0 and complete == planned_jobs),
        "fresh_bridge_preparation_calls_attempted": preparation_calls,
        "verified_fresh_native_preparations": sum(row["binding"] is not None and row["binding"]["status"] == "ready_fresh_source_proposal_replay" for row in rows),
        "summary": _aggregate(all_position_summaries, missing_terminals),
        "summary_scope": "all_planned_positions_with_verified_saved_batch_subtotals_and_explicit_uncomputed_accounts_not_unknown_runtime_calls",
        "persisted_partial_batch_summaries": [deepcopy(job["persisted_batch_prefix_summary"]) for job in jobs if job["persisted_batch_prefix_summary"] is not None],
        "observer_errors": observer_errors, "partial_output_files": deepcopy(writer.partial_files),
        "elapsed_seconds": perf_counter() - started, "output_reserved_attempt_bytes_before_final_manifests": writer.bytes,
        "limits": ["Old saved outputs are requests, not reused native authority; fresh suppliers are executed once per admitted source.",
            "All original completion/selector positions are retained, including held and uncomputed positions.",
            "Credit counts selector occurrences within separate completions; it is not a union across alternatives.",
            "Whole contrast/policy, winner, final harmony/NCT/cadence, accuracy, UI and training remain unpromoted.",
            "Native/role logical budgets are not elapsed-time/RSS limits; progress is emitted only at stage/packet boundaries."]}
    # Exact final reserve verification, not an assumption that a fixed reserve
    # always fits. Failure leaves an explicitly incomplete new directory.
    final_index = writer._encoded(rows)
    index_path = str(output / "context-index.json")
    from hashlib import sha256
    report["artifact_hashes"][index_path] = sha256(final_index).hexdigest()
    final_report = writer._encoded(report)
    if len(final_index) + len(final_report) > settings["manifest_reserve_bytes"] or len(final_index) + len(final_report) > settings["max_total_output_bytes"] - writer.bytes:
        raise OutputBudgetExceeded("reserved_final_manifest_byte_budget_incomplete_no_completion_claim")
    writer.json("context-index.json", rows)
    writer.json("report.json", report, register=False)
    notify("report_saved", status=report["status"], physical_output_bytes=sum(p.stat().st_size for p in output.rglob("*") if p.is_file()))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for key, value in {**READ_SETTINGS, **engine.DEFAULTS}.items():
        parser.add_argument("--" + key.replace("_", "-"), type=int, default=value)
    args = vars(parser.parse_args())
    directory, output = args.pop("parent"), args.pop("output")
    report = run(directory, output, progress_callback=lambda event: print(json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False), flush=True), **args)
    print(json.dumps({"status": report["status"], "integrity": report["computation_integrity_passed"]}, sort_keys=True), flush=True)
    if not report["computation_integrity_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
