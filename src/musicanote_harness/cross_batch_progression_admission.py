"""Read-only admission of complete phase29 archives for saved-only contrasts.

Metadata admission is NOT validation of every native/role body. Bodies are
read one batch at a time; an exhausted completion iterator alone verifies its
terminal counters. No native issuer, music producer, writer or winner exists
in this module. The old reader's one-GiB cumulative cap remains the default.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from weakref import WeakKeyDictionary

from . import source_progression_replay_trial as replay
from . import native_progression_contrast_trial as legacy_join
from .musical_pattern_observation import digest

old, sealed = replay.old, replay.sealed
VERSION = "cross-batch-progression-admission-0.1.0"
AUTHORITY = "validated_saved_metadata_not_live_native_or_completed_contrast"
REQUEST_PREFIX = "cbprequest_"
SETTINGS = {"max_contexts": 2, "max_origins": 200000, "max_catalogs": 1024,
    "max_file_bytes": 67108864, "max_decoded_file_bytes": 268435456,
    "max_total_decoded_bytes": 1073741824, "max_groups": 128,
    "max_entries_per_completion": 4096, "max_batches_per_completion": 2048,
    "block_size": 64}
REPORT_KEYS = {"version", "status", "source_authority", "selected", "flags", "full_contrast_status",
    "computation_integrity_passed", "inputs_and_code_unchanged", "artifacts_unchanged",
    "changed_inputs_or_code", "changed_artifacts", "failures", "artifact_hashes", "denominators",
    "planned_distinct_sources", "planned_completion_requests", "planned_selector_occurrences",
    "planned_batches", "saved_terminal_jobs", "computed_completion_requests", "whole_completion_holds",
    "incomplete_or_unstarted_completion_requests", "missing_terminal_completion_requests",
    "submitted_nonempty_requests_completed", "known_empty_request_set",
    "fresh_bridge_preparation_calls_attempted", "verified_fresh_native_preparations", "summary",
    "summary_scope", "persisted_partial_batch_summaries", "observer_errors", "partial_output_files",
    "elapsed_seconds", "output_reserved_attempt_bytes_before_final_manifests", "limits"}
PLAN_KEYS = {"version", "parent", "inputs", "code", "settings", "denominators", "reader_counts",
    "parent_report_sha256", "parent_inventories", "source_authority", "parent_source_authority",
    "planned_distinct_sources", "planned_completion_requests", "planned_selector_occurrences",
    "planned_batches", "planned_replay_work_all_completions", "replay_work_budget_scope",
    "full_contrast_status", "selected", "flags"}
ROW_KEYS = {"context_key", "source_identity_sha256", "full_IR", "scope", "archived_lattice",
    "prior_panel", "source_proposal", "original_source_files", "parent_policy_rows", "native_inventory",
    "plan", "binding", "fresh_lattice", "status", "error", "jobs"}
JOB_KEYS = {"completion_kind", "original_control", "plan", "header", "bundle", "job", "batches",
    "summary", "persisted_batch_prefix_summary", "status", "error", "planned_selector_occurrences",
    "planned_batches", "unpersisted_selector_ranges", "received_batch_packets",
    "runtime_activity_after_last_persisted_batch"}
BATCH_KEYS = replay.PLAN_BATCH_KEYS | {"comparison", "explanation"}
_ADMISSIONS = WeakKeyDictionary()


class _AdmittedArchive:
    __slots__ = ("__weakref__",)


def _issued(handle):
    if type(handle) is not _AdmittedArchive or handle not in _ADMISSIONS:
        raise ValueError("owned_saved_metadata_handle_required_not_external_summary")
    return _ADMISSIONS[handle]


class SourceAdmissionHold(ValueError):
    """An incomplete upstream request retains its declared denominators."""
    def __init__(self, reason, plan):
        self.plan = deepcopy(plan)
        super().__init__(reason)


def _settings(limits):
    if set(limits) - set(SETTINGS):
        raise ValueError("closed_cross_batch_admission_limits_required")
    result = {**SETTINGS, **limits}
    for name, value in result.items():
        old._limit(value, name)
    if not 1 <= result["block_size"] <= 64:
        raise ValueError("cross_batch_block_size_1_to_64_required")
    return result


def _unpromoted(value):
    old._closed(value["flags"], replay.engine._flags(), "saved_replay_flags")
    if any(v is not False for v in value["flags"].values()) or value["selected"] is not None:
        raise ValueError("unpromoted_saved_replay_required")
    if value["source_authority"] != replay.AUTHORITY or value["full_contrast_status"] != replay.DEFERRED:
        raise ValueError("exact_saved_replay_authority_and_deferred_contrast_required")


def _registered(info, prefix, reader, hashes):
    if type(info) is not dict or hashes.get(info.get("artifact")) != info.get("sha256"):
        raise ValueError("saved_record_requires_registered_physical_SHA")
    return legacy_join._record(info, prefix, reader, hashes)


def _flags():
    return {name: False for name in ("all_saved_bodies_validated", "full_contrast_evaluated",
        "policy_evaluated", "winning_harmony_selected", "musical_accuracy_measured",
        "native_or_role_producer_replayed", "live_native_authority_claimed",
        "independent_completions_unioned", "production_modified", "training_eligible",
        "gold_eligible", "generation_ready")}


def _historical_creation(plan, parent_plan, parent_report, parent_dir):
    """Derive old code and ancestor inventories from the actual parent snapshot."""
    original_code = {**parent_plan["code"]}
    for path in replay._new_code_paths():
        path = str(path.resolve())
        if path not in plan["code"]:
            raise ValueError("original_replay_code_creation_inventory_required")
        if path in original_code and original_code[path] != plan["code"][path]:
            raise ValueError("historical_creation_code_hash_conflict")
        original_code[path] = plan["code"][path]
    if plan["code"] != original_code:
        raise ValueError("exact_historical_replay_code_inventory_required")
    expected = [{"directory": str(parent_dir), "files": len(parent_report["artifact_hashes"]) + 1},
        *deepcopy(parent_plan["parent_inventories"])]
    if plan["parent_inventories"] != expected:
        raise ValueError("exact_ordered_historical_ancestor_inventory_required")


def _bounded_source_inventory(lattice, panel, scope, settings):
    catalogs = lattice["catalog_inventory"]
    if type(catalogs) is not list:
        raise ValueError("typed_whole_saved_catalog_inventory_required")
    count = sum(len(catalog["origins"]) for catalog in catalogs)
    declared = {"planned_catalogs": len(catalogs), "planned_origins": count}
    if len(catalogs) > settings["max_catalogs"] or count > settings["max_origins"]:
        raise SourceAdmissionHold("whole_saved_source_inventory_budget_no_prefix", declared)
    # Original intrinsic inventory checks execute only after the count gate.
    return replay.parent._inventory(lattice, panel, scope, settings)


def _original_cases(parent_dir, parent_rows, reader, hashes, settings):
    """Direct creation-bound source reconstruction; no historical loader call.

    Old loaders enumerate today's modules. Calling them after adding a child
    would retrospectively extend a historical creation inventory. We validate
    its actual registered hashes and exact source body joins instead.
    """
    cases = []
    if type(parent_rows) is not list or len(parent_rows) > settings["max_contexts"]:
        raise ValueError("whole_registered_source_inventory_required")
    for row in parent_rows:
        old._closed(row, replay.ARCHIVE_ROW_KEYS, "original_phase28_source")
        if row["error"] is not None:
            raise ValueError("failed_source_proposal_not_comparable")
        info = row["full_IR"]
        old._closed(info, legacy_join.IR_INFO_KEYS, "original_full_IR")
        if (hashes.get(info["artifact"]) != info["sha256"] or info["binding_match"] is not True
                or info["registered_full_IR_not_projection"] is not True):
            raise ValueError("original_full_IR_creation_binding_required")
        ir = reader.read(info["artifact"])
        if ir["ir_document_id"] != info["ir_document_id"] or digest(ir) != info["ir_content_sha256"]:
            raise ValueError("original_full_IR_content_hash_mismatch")
        scope = _registered(row["scope"], old.expanded.PREFIX, reader, hashes)
        lattice = _registered(row["native_lattice"], replay.engine.native.PREFIX, reader, hashes)
        panel = _registered(row["prior_panel"], replay.parent.engine.prior.PREFIX, reader, hashes)
        proposal = _registered(row["proposal"], replay.parent.engine.PREFIX, reader, hashes)
        inventory = _bounded_source_inventory(lattice, panel, scope, settings)
        if inventory != row["native_inventory"]:
            raise ValueError("exact_original_source_inventory_counts_required")
        replay.engine._validate_saved(scope, lattice, proposal, panel)
        identity = digest({"context_key": row["context_key"], "full_IR": info, "scope": row["scope"],
            "native_lattice": row["native_lattice"], "source_panel": row["prior_panel"]})
        if (scope["binding"] != old.expanded._binding(ir) or row["source_identity_sha256"] != identity
                or row["original_source_files"] != ir["source_files"]
                or row["summary"] != proposal["summary"] or row["query_plan"] != proposal["query_plan"]
                or row["status"] != proposal["status"] or row["reasons"] != proposal["reasons"]
                or any(c["source_identity_sha256"] == identity for c in cases)):
            raise ValueError("exact_distinct_original_source_and_proposal_join_required")
        controls = row["completion_controls"]
        if type(controls) is not list or not controls:
            raise ValueError("original_completion_requests_required")
        for control in controls:
            old._closed(control, replay.COMPLETION_CONTROL_KEYS, "original_completion_control")
            legacy_join._edge_signature(control["required_links"])
            if control["native_and_role_replay_executed"] is not False:
                raise ValueError("original_control_not_saved_native_authority")
            for record_info in (control["bundle"], control["policy"]):
                if hashes.get(record_info["artifact"]) != record_info["sha256"]:
                    raise ValueError("original_completion_control_creation_hash_required")
        case = {"ir": ir, "scope": scope, "lattice": lattice, "panel": panel, "proposal": proposal,
            "context_key": deepcopy(row["context_key"]), "source_identity_sha256": identity,
            "completion_controls": deepcopy(controls), "original_row": deepcopy(row)}
        cases.append(case)
    return cases


def _completion(row, case, binding, plan, control, source_index, job_index, reader, hashes, settings, limits):
    old._closed(row, JOB_KEYS, "indexed_saved_completion")
    if (row["status"] != "computed_native_role_source_requests_not_selected" or row["error"] is not None
            or row["unpersisted_selector_ranges"] != [] or row["persisted_batch_prefix_summary"] is not None
            or row["runtime_activity_after_last_persisted_batch"] is not False):
        raise ValueError("complete_indexed_completion_no_missing_prefix_required")
    n, b = plan["planned_selectors"], plan["planned_batches"]
    if n > settings["max_entries_per_completion"] or b > settings["max_batches_per_completion"]:
        raise SourceAdmissionHold("whole_saved_completion_read_budget_no_prefix", {"planned_entries": n, "planned_batches": b})
    if (row["completion_kind"] != control["kind"] or row["original_control"] != control
            or row["planned_selector_occurrences"] != n or type(row["planned_selector_occurrences"]) is not int
            or row["planned_batches"] != b or type(row["planned_batches"]) is not int
            or row["received_batch_packets"] != b or type(row["received_batch_packets"]) is not int
            or type(row["batches"]) is not list or len(row["batches"]) != b):
        raise ValueError("exact_original_indexed_completion_denominators_required")
    bundle = _registered(row["bundle"], replay.engine.native.BUNDLE_PREFIX, reader, hashes)
    header = row["header"]
    old._closed(header, {"binding_ref", "plan_ref", "status", "reasons"}, "indexed_saved_header")
    if header["plan_ref"] != sealed._ref(plan):
        raise ValueError("indexed_header_original_plan_ref_required")
    replay._header({"packet_type": "header", "binding_ref": header["binding_ref"], "plan": plan,
        "bundle": bundle, "status": header["status"], "reasons": header["reasons"]},
        case, binding, plan, control, limits)
    terminal = _registered(row["job"], replay.engine.PREFIX, reader, hashes)
    refs = []
    for expected, batch in zip(plan["batches"], row["batches"]):
        old._closed(batch, BATCH_KEYS, "indexed_saved_batch")
        if any(type(batch[k]) is not int or batch[k] != expected[k] for k in replay.PLAN_BATCH_KEYS):
            raise ValueError("exact_all_original_batch_positions_and_work_required")
        for name in ("comparison", "explanation"):
            old._closed(batch[name], legacy_join.INFO_KEYS, "indexed_saved_body_info")
            if hashes.get(batch[name]["artifact"]) != batch[name]["sha256"]:
                raise ValueError("indexed_body_not_registered_in_exact_archive")
        refs.append({**deepcopy(expected), "comparison_ref": deepcopy(batch["comparison"]["record_ref"]),
            "explanation_ref": deepcopy(batch["explanation"]["record_ref"])})
    if row["plan"]["record_ref"] != sealed._ref(plan) or row["summary"] != terminal["summary"]:
        raise ValueError("indexed_plan_and_terminal_summary_join_required")
    declared = deepcopy(row["summary"])
    replay._job(terminal, case, binding, plan, bundle, control, refs, declared, limits, [])
    if (declared["native_computed_paths"] != n or declared["role_computed_paths"] != n
            or declared["completed_batches"] != b or declared["withheld_native_paths"] != 0
            or declared["withheld_role_paths"] != 0 or declared["uncomputed_role_accounts"] != 0):
        raise ValueError("all_saved_position_counts_required_not_only_integrity_true")
    request = sealed._seal({"version": VERSION, "source_identity_sha256": case["source_identity_sha256"],
        "source_index": source_index, "completion_index": job_index, "original_control": deepcopy(control),
        "proposal_ref": sealed._ref(case["proposal"]), "terminal_job_ref": sealed._ref(terminal),
        "selector_inventory_sha256": digest(case["proposal"]["selectors"]),
        "status": "original_saved_completion_request_not_selected", "selected": None}, REQUEST_PREFIX)
    counts = Counter(s["key_id"] for s in case["proposal"]["selectors"])
    groups = []
    for key in case["lattice"]["keys"]:
        positions = [i for i, s in enumerate(case["proposal"]["selectors"]) if s["key_id"] == key["record_id"]]
        size = settings["block_size"]
        blocks = (len(positions) + size - 1) // size
        groups.append({"key_ref": sealed._ref(key), "completion_request_ref": sealed._ref(request),
            "selector_indices": positions, "planned_entries": len(positions),
            "planned_pairs": len(positions) * (len(positions) - 1) // 2,
            "planned_block_tasks": blocks * (blocks + 1) // 2})
    if set(counts) - {k["record_id"] for k in case["lattice"]["keys"]}:
        raise ValueError("unknown_original_selector_key")
    return {"row": deepcopy(row), "bundle": bundle, "terminal": terminal, "request": request, "groups": groups,
        "declared_summary": declared, "case": case, "binding": binding, "plan": plan,
        "validated_entry_batches": 0, "all_entry_batches_consumed": False}


def _load_saved_plan_data(directory, **limits):
    """Admit complete metadata and exact SHA closure, never all body semantics."""
    settings = _settings(limits)
    directory = Path(directory).resolve(strict=True)
    reader = legacy_join.BoundedReader(settings)
    report = reader.read(directory / "report.json")
    plan = reader.read(directory / "run-plan.json")
    rows = reader.read(directory / "context-index.json")
    old._closed(report, REPORT_KEYS, "saved_phase29_report")
    old._closed(plan, PLAN_KEYS, "saved_phase29_creation_plan")
    for record in (report, plan):
        if record["version"] != replay.VERSION:
            raise ValueError("current_saved_phase29_version_required")
        _unpromoted(record)
    for name in ("planned_distinct_sources", "planned_completion_requests", "planned_selector_occurrences", "planned_batches"):
        old._limit(plan[name], name)
        if type(report[name]) is not int or report[name] != plan[name]:
            raise ValueError("report_original_plan_denominator_mismatch")
    for name in ("saved_terminal_jobs", "computed_completion_requests", "fresh_bridge_preparation_calls_attempted",
            "verified_fresh_native_preparations", "whole_completion_holds",
            "incomplete_or_unstarted_completion_requests", "missing_terminal_completion_requests"):
        old._limit(report[name], name)
    missing = {"planned_entries": plan["planned_selector_occurrences"], "planned_completion_requests": plan["planned_completion_requests"],
        "planned_batches": plan["planned_batches"], "denominators": deepcopy(plan["denominators"]), "known_empty": False}
    if type(rows) is list and len(rows) > settings["max_contexts"]:
        raise SourceAdmissionHold("whole_context_inventory_budget_no_prefix", missing)
    if (report["status"] != "fresh_source_replay_saved_not_selected"
            or any(report[k] is not True for k in ("computation_integrity_passed", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or any(report[k] != [] for k in ("changed_inputs_or_code", "changed_artifacts", "failures", "partial_output_files", "persisted_partial_batch_summaries"))
            or any(type(report[k]) is not int or report[k] != 0 for k in ("whole_completion_holds", "incomplete_or_unstarted_completion_requests", "missing_terminal_completion_requests"))
            or report["computed_completion_requests"] != plan["planned_completion_requests"]
            or report["saved_terminal_jobs"] != plan["planned_completion_requests"]):
        raise SourceAdmissionHold("upstream_whole_hold_or_incomplete_preserve_original_denominators", missing)
    nonempty = plan["planned_selector_occurrences"] > 0
    if (report["submitted_nonempty_requests_completed"] is not nonempty
            or report["known_empty_request_set"] is not (not nonempty)
            or type(rows) is not list or len(rows) != plan["planned_distinct_sources"]
            or len(rows) > settings["max_contexts"] or report["denominators"] != plan["denominators"]):
        raise ValueError("typed_complete_saved_request_and_source_denominators_required")
    hashes = {}
    for values in (plan["inputs"], plan["code"], report["artifact_hashes"]):
        old._protect_map(hashes, values)
    old._protect(hashes, str(directory / "report.json"), old._file_sha(directory / "report.json"))
    inventory = old._inventory(directory, report["artifact_hashes"], directory / "report.json")
    if old._guard(hashes):
        raise ValueError("original_saved_creation_or_body_physical_SHA_changed")
    parent_dir = Path(plan["parent"]).resolve(strict=True)
    parent_report = reader.read(parent_dir / "report.json")
    parent_plan = reader.read(parent_dir / "run-plan.json")
    parent_rows = reader.read(parent_dir / "context-index.json")
    old._closed(parent_report, replay.ARCHIVE_REPORT_KEYS, "original_phase28_report")
    old._closed(parent_plan, replay.ARCHIVE_PLAN_KEYS, "original_phase28_creation_plan")
    if (parent_report["version"] != replay.parent.VERSION or parent_plan["version"] != replay.parent.VERSION
            or hashes.get(str(parent_dir / "report.json")) != plan["parent_report_sha256"]
            or plan["parent_source_authority"] != parent_report["source_authority"]
            or parent_report["denominators"] != report["denominators"]):
        raise ValueError("original_phase28_parent_and_cohort_required")
    _historical_creation(plan, parent_plan, parent_report, parent_dir)
    closure = {}
    for mapping in (parent_plan["inputs"], parent_plan["code"], parent_report["artifact_hashes"]):
        old._protect_map(closure, mapping)
    old._protect(closure, str(parent_dir / "report.json"), old._file_sha(parent_dir / "report.json"))
    if plan["inputs"] != closure:
        raise ValueError("exact_original_phase28_input_closure_required")
    inventories = [(directory, inventory)]
    for info in plan["parent_inventories"]:
        old._closed(info, {"directory", "files"}, "original_parent_inventory")
        path = Path(info["directory"]).resolve(strict=True)
        parent_meta = reader.read(path / "report.json")
        if any(hashes.get(p) != sha for p, sha in parent_meta["artifact_hashes"].items()):
            raise ValueError("original_ancestor_artifact_closure_required")
        actual = old._inventory(path, parent_meta["artifact_hashes"], path / "report.json")
        if type(info["files"]) is not int or len(actual) != info["files"]:
            raise ValueError("original_ancestor_exact_inventory_count_required")
        inventories.append((path, actual))
    try:
        cases = _original_cases(parent_dir, parent_rows, reader, hashes, settings)
    except SourceAdmissionHold as exc:
        raise SourceAdmissionHold(str(exc), {**missing, "offending_source_inventory": exc.plan}) from exc
    if len(cases) != len(rows):
        raise ValueError("all_original_source_positions_required")
    jobs = []
    replay_limits = {k: plan["settings"][k] for k in replay.engine.DEFAULTS}
    replay._settings(plan["settings"])
    for source_index, (row, case) in enumerate(zip(rows, cases)):
        old._closed(row, ROW_KEYS, "saved_source_index")
        original = case["original_row"]
        for target, source in (("context_key", "context_key"), ("source_identity_sha256", "source_identity_sha256"),
                ("full_IR", "full_IR"), ("scope", "scope"), ("archived_lattice", "native_lattice"),
                ("prior_panel", "prior_panel"), ("source_proposal", "proposal"),
                ("original_source_files", "original_source_files"), ("parent_policy_rows", "parent_policy_rows"),
                ("native_inventory", "native_inventory")):
            if row[target] != original[source]:
                raise ValueError("original_source_index_registration_join_required")
        if row["error"] is not None or row["status"] != "ready_fresh_source_proposal_replay":
            raise SourceAdmissionHold("source_rebind_incomplete_not_comparable", missing)
        fresh = _registered(row["fresh_lattice"], replay.engine.native.PREFIX, reader, hashes)
        binding = _registered(row["binding"], replay.engine.BINDING_PREFIX, reader, hashes)
        saved_plan = _registered(row["plan"], replay.engine.PLAN_PREFIX, reader, hashes)
        replay._binding(binding, case, fresh)
        replay._plan(saved_plan, case, replay_limits)
        if type(row["jobs"]) is not list or len(row["jobs"]) != len(case["completion_controls"]):
            raise ValueError("all_original_completion_positions_required")
        for job_index, (job, control) in enumerate(zip(row["jobs"], case["completion_controls"])):
            if job["plan"] != row["plan"]:
                raise ValueError("same_source_plan_physical_reference_required")
            try:
                jobs.append(_completion(job, case, binding, saved_plan, control, source_index, job_index,
                    reader, hashes, settings, replay_limits))
            except SourceAdmissionHold as exc:
                raise SourceAdmissionHold(str(exc), {**missing, "offending_completion": {
                    "source_index": source_index, "completion_index": job_index, **exc.plan}}) from exc
    groups = [g for job in jobs for g in job["groups"]]
    if len(groups) > settings["max_groups"]:
        raise SourceAdmissionHold("whole_group_inventory_read_budget_no_prefix", {**missing, "planned_groups": len(groups)})
    if (len(jobs) != plan["planned_completion_requests"]
            or sum(j["plan"]["planned_selectors"] for j in jobs) != plan["planned_selector_occurrences"]
            or sum(j["plan"]["planned_batches"] for j in jobs) != plan["planned_batches"]
            or replay._aggregate([j["declared_summary"] for j in jobs]) != report["summary"]):
        raise ValueError("all_original_terminal_summary_and_position_denominators_required")
    if old._guard(hashes):
        raise ValueError("original_saved_inputs_changed_during_metadata_admission")
    return {"version": VERSION, "source_authority": AUTHORITY, "directory": directory,
        "settings": settings, "reader": reader, "hashes": hashes, "inventories": inventories,
        "report": report, "plan": plan, "cases": cases, "jobs": jobs,
        "summary": {"metadata_admitted_completion_requests": len(jobs),
            "planned_entries": plan["planned_selector_occurrences"], "planned_groups": len(groups),
            "planned_pairs": sum(g["planned_pairs"] for g in groups),
            "planned_block_tasks": sum(g["planned_block_tasks"] for g in groups),
            "computed_pairs": 0, "validated_entry_batches": 0, "validated_entry_occurrences": 0,
            "all_saved_bodies_validated": False}, "flags": _flags(), "replay_limits": replay_limits}


def load_saved_plan(directory, **limits):
    """Return an owned saved-only handle; no public writable completion ledger."""
    data = _load_saved_plan_data(directory, **limits)
    handle = _AdmittedArchive()
    _ADMISSIONS[handle] = data
    return handle


def metadata_prepared(handle):
    data = _issued(handle)
    return {"version": VERSION, "source_authority": AUTHORITY, "summary": deepcopy(data["summary"]),
        "denominators": deepcopy(data["plan"]["denominators"]), "flags": _flags(),
        "groups": [deepcopy(group) for job in data["jobs"] for group in job["groups"]],
        "reader_counts": {"files_read": data["reader"].read_files, "decoded_bytes": data["reader"].decoded_bytes}}


def source_prepared(handle, source_index, completion_index):
    """Copy immutable source/one-completion input; this is not a native session."""
    data = _issued(handle)
    for value in (source_index, completion_index):
        old._limit(value, "original_completion_position")
    jobs = [j for j in data["jobs"] if j["request"]["source_index"] == source_index
        and j["request"]["completion_index"] == completion_index]
    if len(jobs) != 1:
        raise ValueError("exact_original_completion_position_required")
    job = jobs[0]
    return deepcopy({"scope": job["case"]["scope"], "lattice": job["case"]["lattice"],
        "bundle": job["bundle"], "completion_request": job["request"], "groups": job["groups"]})


def iter_validated_completion_entries(handle, source_index, completion_index):
    """Yield one exact batch of saved entries; early close NEVER means complete.

    Each entry remains unselected saved evidence. The new contrast core must
    validate source profiles/clauses/union before constructing its facet.
    """
    admission = _issued(handle)
    for value in (source_index, completion_index):
        old._limit(value, "original_completion_position")
    matches = [j for j in admission["jobs"] if j["request"]["source_index"] == source_index
        and j["request"]["completion_index"] == completion_index]
    if len(matches) != 1:
        raise ValueError("exact_original_completion_position_required")
    job = matches[0]
    if job["all_entry_batches_consumed"] or job["validated_entry_batches"]:
        raise ValueError("single_pass_completion_iterator_required_no_prefix_restart")
    case, bundle, plan = job["case"], job["bundle"], job["plan"]
    counts = replay._empty_counts(plan["planned_selectors"], plan["planned_batches"])
    counts["fresh_bundle_registrations"] = 1
    origins = {o["record_id"]: o for c in case["lattice"]["catalog_inventory"] for o in c["origins"]}
    keys = {k["record_id"]: k for k in case["lattice"]["keys"]}
    seen, refs = set(), []
    for batch in job["row"]["batches"]:
        planned = {k: batch[k] for k in replay.PLAN_BATCH_KEYS}
        lo, hi = batch["selector_start"], batch["selector_end_exclusive"]
        selectors = case["proposal"]["selectors"][lo:hi]
        comparison = _registered(batch["comparison"], replay.engine.native.COMPARISON_PREFIX,
            admission["reader"], admission["hashes"])
        explanation = _registered(batch["explanation"], replay.engine.roles.PREFIX,
            admission["reader"], admission["hashes"])
        replay._batch(comparison, explanation, selectors, case, bundle, planned, admission["replay_limits"])
        if len(comparison["paths"]) != len(selectors) or len(explanation["paths"]) != len(selectors):
            raise ValueError("no_missing_native_or_role_position_in_saved_batch")
        entries = []
        for ordinal, (selector, path, role) in enumerate(zip(selectors, comparison["paths"], explanation["paths"])):
            if role["native_path_ref"] != sealed._ref(path):
                raise ValueError("exact_native_role_array_ordinal_required")
            entry = legacy_join._entry(path, role, selector, comparison, explanation,
                case["lattice"], case["scope"], bundle, origins, keys)
            identity = digest(path["logical_tuple"])
            if identity in seen:
                raise ValueError("duplicate_original_logical_tuple_not_signature_alias")
            seen.add(identity)
            entries.append({"selector_index": lo + ordinal, "entry": entry})
        replay._add_batch(counts, comparison, explanation, bundle)
        refs.append({**deepcopy(planned), "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)})
        job["validated_entry_batches"] += 1
        admission["summary"]["validated_entry_batches"] += 1
        admission["summary"]["validated_entry_occurrences"] += len(entries)
        yield {"completion_request_ref": sealed._ref(job["request"]), "batch_index": batch["batch_index"],
            "selector_start": lo, "selector_end_exclusive": hi, "entries": entries}
        del comparison, explanation, entries
    replay._job(job["terminal"], case, job["binding"], plan, bundle, job["row"]["original_control"],
        refs, counts, admission["replay_limits"], [])
    if old._guard(admission["hashes"]):
        raise ValueError("saved_archive_changed_during_completion_read")
    job["all_entry_batches_consumed"] = True


def finish_admission(handle):
    """No contrast completion claim: exact body positions must all be consumed."""
    admission = _issued(handle)
    for path, inventory in admission["inventories"]:
        if {str(p.resolve()) for p in path.rglob("*") if p.is_file()} != inventory:
            raise ValueError("original_inventory_changed_during_saved_read")
    if old._guard(admission["hashes"]):
        raise ValueError("original_hash_closure_changed_during_saved_read")
    complete = bool(admission["jobs"]) and all(j["all_entry_batches_consumed"] for j in admission["jobs"])
    summary = deepcopy(admission["summary"])
    summary["all_saved_bodies_validated"] = False
    return {"version": VERSION, "source_authority": AUTHORITY, "summary": summary,
        "all_indexed_batches_join_validated": complete,
        "known_empty_request_set": bool(complete and summary["planned_entries"] == 0),
        "source_profile_clause_union_validation": "required_in_contrast_core_not_claimed_by_batch_join",
        "full_contrast_status": "not_executed", "selected": None, "flags": _flags(),
        "reader_counts": {"files_read": admission["reader"].read_files,
            "decoded_bytes": admission["reader"].decoded_bytes}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", required=True)
    parser.add_argument("--max-total-decoded-bytes", type=int, default=SETTINGS["max_total_decoded_bytes"])
    args = parser.parse_args()
    data = load_saved_plan(args.parent, max_total_decoded_bytes=args.max_total_decoded_bytes)
    report = finish_admission(data)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
