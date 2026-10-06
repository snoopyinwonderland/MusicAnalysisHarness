"""Versioned phase29 archive-to-shared-source bridge using one read account.

Only COMPLETE upfront ordered byte declarations can issue a reader. A held
plan has caller-declared denominators, not authenticated original membership.
Metadata validation derives original creation/ancestor/source/request identity;
body joins and shared intrinsic groups earn separate coverage. No old loader,
native producer, old private admission handle, pair runner or winner is used.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from weakref import WeakKeyDictionary

from . import cross_batch_progression_admission as kernels
from . import cross_batch_read_budget as budget
from . import shared_source_progression_contrast as shared
from .musical_pattern_observation import digest

old, sealed, replay, join = kernels.old, kernels.sealed, kernels.replay, kernels.legacy_join
VERSION = "shared-source-archive-bridge-0.1.0"
AUTHORITY = "historical_saved_membership_not_live_native_or_winning_harmony"
_PLANS, _ARCHIVES = WeakKeyDictionary(), WeakKeyDictionary()


def _flags():
    return {name: False for name in ("full_contrast_evaluated", "native_authority_claimed",
        "native_or_role_producer_replayed", "independent_completions_unioned",
        "winning_harmony_selected", "musical_accuracy_measured", "production_modified",
        "training_eligible", "gold_eligible", "generation_ready", "UI_connected")}


class ArchivePlan:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("archive_plan_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_immutable_archive_plan")

    def record(self):
        data = _plan(self)
        return {"version": VERSION, "authority": "caller_declared_read_plan_not_original_membership",
            "directory": data["directory"], "read_plan": data["read_plan"].record(),
            "original_membership_authenticated": False, "flags": _flags()}


class SavedArchive:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("saved_archive_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_saved_archive")


def _plan(handle):
    if type(handle) is not ArchivePlan or handle not in _PLANS:
        raise ValueError("owned_archive_plan_required_not_external_summary")
    return _PLANS[handle]


def _archive(handle):
    if type(handle) is not SavedArchive or handle not in _ARCHIVES:
        raise ValueError("owned_saved_archive_required_not_external_summary")
    return _ARCHIVES[handle]


class ArchiveFailure(ValueError):
    def __init__(self, reason, *, plan=None, reader=None, metadata=None):
        self.report = {"version": VERSION, "reason": reason,
            "plan": None if plan is None else plan.record(),
            "read_ledger": None if reader is None else budget.read_ledger(reader),
            "metadata": deepcopy(metadata), "flags": _flags()}
        super().__init__(reason)


def plan_archive_reads(directory, reads, *, original_denominators, registered_sha256,
        inventory_roots, output_directory=None, read_limits=None, admission_limits=None,
        source_limits=None, group_limits=None):
    """No discovery parsing: all metadata AND body occurrences must be planned.

    registered_sha256 must later equal the archive-derived original closure,
    including its report. New current bridge dependencies are added separately;
    they never retrospectively extend historical code creation membership.
    """
    directory = str(budget._path(directory))
    if type(inventory_roots) is not tuple or not inventory_roots:
        raise ValueError("explicit_registered_historical_inventory_roots_required")
    settings = kernels._settings({} if admission_limits is None else admission_limits)
    # Byte settings belong to one new account, never separate frozen loaders.
    if admission_limits and any(k in admission_limits for k in
            ("max_file_bytes", "max_decoded_file_bytes", "max_total_decoded_bytes")):
        raise ValueError("byte_limits_must_belong_to_one_cumulative_read_account")
    source_limits = shared.SourceLimits() if source_limits is None else source_limits
    group_limits = shared.GroupLimits() if group_limits is None else group_limits
    if type(source_limits) is not shared.SourceLimits or type(group_limits) is not shared.GroupLimits:
        raise ValueError("typed_shared_source_and_group_limits_required")
    registered = deepcopy(registered_sha256)
    current = {}
    for module in (__import__(__name__, fromlist=["__file__"]), kernels, budget, shared):
        path = str(Path(module.__file__).resolve())
        sha = old._file_sha(path)
        if path in registered and registered[path] != sha:
            raise ValueError("current_bridge_dependency_conflicts_with_registered_SHA")
        current[path] = sha
    protected = {**registered, **current}
    read_plan = budget.plan_read_run(reads, original_denominators=original_denominators,
        registered_sha256=protected, inventory_roots=inventory_roots,
        source_archive_roots=(directory,), output_directory=output_directory, limits=read_limits)
    handle = object.__new__(ArchivePlan)
    _PLANS[handle] = {"directory": directory, "read_plan": read_plan,
        "registered": registered, "roots": deepcopy(inventory_roots), "current": current,
        "settings": settings, "source_limits": source_limits, "group_limits": group_limits}
    return handle


def _record(info, prefix, reader, hashes):
    old._closed(info, join.INFO_KEYS, "registered_shared_bridge_record")
    if hashes.get(info["artifact"]) != info["sha256"]:
        raise ValueError("exact_registered_record_physical_SHA_required")
    record = reader.read(info["artifact"])
    sealed._check(record, prefix)
    if sealed._ref(record) != info["record_ref"] or record["status"] != info["status"]:
        raise ValueError("registered_record_ref_or_status_mismatch")
    return record


def _merge(values):
    result = {}
    for mapping in values:
        old._protect_map(result, mapping)
    return result


def _inventory(root, report, supplied):
    path = str(Path(root).resolve(strict=True))
    expected = {**report["artifact_hashes"]}
    report_path = str(Path(path) / "report.json")
    if report_path not in supplied:
        raise ValueError("registered_historical_report_SHA_required")
    expected[report_path] = supplied[report_path]
    if any(not budget._inside(Path(p), Path(path)) for p in expected):
        raise ValueError("archive_artifact_cannot_escape_registered_root")
    return {"directory": path, "registered_sha256": expected}


def _phase28_metadata(reader, directory, parent_report, parent_plan, rows, replay_plan, hashes, roots):
    """Exact creation-bound parent/ancestor declarations, no today's code glob."""
    old._closed(parent_report, replay.ARCHIVE_REPORT_KEYS, "original_phase28_report")
    old._closed(parent_plan, replay.ARCHIVE_PLAN_KEYS, "original_phase28_plan")
    old._closed(replay_plan, replay.REPLAY_PLAN_KEYS, "original_phase28_replay_plan")
    for name in ("fresh_native_preparations", "native_replay_evaluations_performed",
            "distinct_registered_sources", "registered_policy_completion_rows", "saved_source_proposals",
            "computed_source_proposals", "whole_source_proposal_holds", "native_replay_planned_completion_requests"):
        old._limit(parent_report[name], "original_phase28_report." + name)
    old._limit(parent_plan["fresh_native_preparations"], "original_phase28_plan.fresh_native_preparations")
    for name in ("native_evaluations_performed", "fresh_native_sessions_prepared", "planned_completion_requests",
            "retained_control_selector_occurrences"):
        old._limit(replay_plan[name], "original_phase28_replay_plan." + name)
    old._closed(parent_report["denominators"], join.DENOMINATOR_KEYS, "original_phase28_cohort")
    for value in parent_report["denominators"].values():
        old._limit(value, "original_phase28_cohort")
    if (any(v["version"] != replay.parent.VERSION for v in (parent_report, parent_plan, replay_plan))
            or parent_report["status"] != "saved_source_proposal_probe_complete_not_evaluated"
            or any(parent_report[k] is not True for k in ("computation_integrity_passed", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or any(parent_report[k] != [] for k in ("changed_inputs_or_code", "changed_artifacts", "failures"))
            or any(parent_report[k] is not False or parent_plan[k] is not False for k in replay.ARCHIVE_FALSE)
            or any(v["source_authority"] != replay.parent.engine.AUTHORITY for v in (parent_report, parent_plan, replay_plan))
            or parent_report["parent_source_authority"] != replay.parent.AUTHORITY
            or parent_plan["parent_source_authority"] != replay.parent.AUTHORITY
            or parent_report["selected"] is not None or parent_plan["selected"] is not None
            or parent_report["fresh_native_preparations"] != 0 or parent_plan["fresh_native_preparations"] != 0
            or parent_report["native_replay_evaluations_performed"] != 0
            or replay_plan["native_evaluations_performed"] != 0 or replay_plan["fresh_native_sessions_prepared"] != 0
            or replay_plan["same_completion_resolution_evaluated"] is not False or replay_plan["winning_harmony_selected"] is not False
            or parent_report["denominators"] != parent_plan["denominators"]):
        raise ValueError("completed_unselected_original_phase28_metadata_required")
    denoms = parent_report["denominators"]
    if (denoms["selected_contexts"] != 2 or denoms["registered_context_pool"] != 5
            or denoms["unexecuted_declared_contexts"] != denoms["declared_contexts"] - 2
            or denoms["unexecuted_declared_original_raw_lanes"] != denoms["declared_original_raw_lanes"] - denoms["selected_original_raw_lanes"]):
        raise ValueError("whole_original_cohort_complements_required")
    ancestors = []
    path = Path(parent_plan["parent"]).resolve(strict=True)
    for version, report_keys, plan_keys in (
            (replay.parent.parent.VERSION, replay.parent.REPORT_KEYS, replay.parent.PLAN_KEYS),
            (replay.parent.parent.parent.VERSION, replay.parent.parent.REPORT_KEYS, replay.parent.parent.PLAN_KEYS),
            (replay.parent.parent.parent.parent.VERSION, replay.parent.parent.parent.REPORT_KEYS, replay.parent.parent.parent.PLAN_KEYS)):
        report, plan, ancestor_rows = (reader.read(path / name) for name in
            ("report.json", "run-plan.json", "context-index.json"))
        old._closed(report, report_keys, "registered_ancestor_report")
        old._closed(plan, plan_keys, "registered_ancestor_creation_plan")
        if (report["version"] != version or plan["version"] != version
                or report["denominators"] != parent_report["denominators"]
                or plan["denominators"] != parent_report["denominators"]
                or any(hashes.get(p) != sha for m in (report["artifact_hashes"], plan["inputs"], plan["code"]) for p, sha in m.items())):
            raise ValueError("exact_ancestor_version_cohort_creation_SHA_required")
        roots.append(_inventory(path, report, hashes))
        ancestors.append((report, plan, ancestor_rows))
        if len(ancestors) < 3:
            path = Path(plan["parent"]).resolve(strict=True)
    _historical_phase28_code(parent_plan, ancestors[0][1])
    expected = [{"directory": r["directory"], "files": len(r["registered_sha256"])} for r in roots[2:]]
    if (parent_plan["parent_inventories"] != expected
            or [len(r["registered_sha256"]) for r in roots[1:]] != [6, 7, 7, 148]
            or hashes.get(str(Path(roots[2]["directory"]) / "report.json")) != parent_plan["parent_report_sha256"]
            or parent_report["parent_policy_summary"] != ancestors[0][0]["summary"]
            or parent_plan["parent_policy_summary"] != ancestors[0][0]["summary"]
            or parent_plan["parent_source_size_manifest"] != ancestors[0][1]["parent_source_size_manifest"]
            or parent_plan["parent_selected_contexts"] != ancestors[2][1]["selected_contexts"]):
        raise ValueError("ordered_original_6_7_7_148_ancestor_membership_required")
    return ancestors


def _historical_phase28_code(parent_plan, ancestor_plan):
    historical_code = dict(ancestor_plan["code"])
    for path in replay.parent._new_code_paths():
        name = str(path.resolve())
        if name not in parent_plan["code"]:
            raise ValueError("original_phase28_extension_code_required")
        if name in historical_code and historical_code[name] != parent_plan["code"][name]:
            raise ValueError("historical_phase28_code_extension_hash_conflict")
        historical_code[name] = parent_plan["code"][name]
    if parent_plan["code"] != historical_code:
        raise ValueError("exact_original_phase28_historical_code_extension_required")


def _cases(rows, reader, hashes, settings, parent_plan, ancestors, parent_report, replay_plan):
    if type(rows) is not list or len(rows) != 2 or len(rows) > settings["max_contexts"]:
        raise ValueError("whole_original_two_source_membership_required")
    cases, records, expected_jobs = [], [], []
    for row in rows:
        old._closed(row, replay.ARCHIVE_ROW_KEYS, "original_phase28_source")
        info = row["full_IR"]
        old._closed(info, join.IR_INFO_KEYS, "original_full_IR")
        if (row["error"] is not None or hashes.get(info["artifact"]) != info["sha256"]
                or info["binding_match"] is not True or info["registered_full_IR_not_projection"] is not True):
            raise ValueError("exact_registered_original_full_IR_required")
        ir = reader.read(info["artifact"])
        if ir["ir_document_id"] != info["ir_document_id"] or digest(ir) != info["ir_content_sha256"]:
            raise ValueError("original_full_IR_content_hash_mismatch")
        scope = _record(row["scope"], old.expanded.PREFIX, reader, hashes)
        lattice = _record(row["native_lattice"], replay.engine.native.PREFIX, reader, hashes)
        panel = _record(row["prior_panel"], replay.parent.engine.prior.PREFIX, reader, hashes)
        proposal = _record(row["proposal"], replay.parent.engine.PREFIX, reader, hashes)
        inventory = kernels._bounded_source_inventory(lattice, panel, scope, settings)
        case = {"ir": ir, "scope": scope, "lattice": lattice, "panel": panel, "proposal": proposal,
            "context_key": deepcopy(row["context_key"]), "source_identity_sha256": row["source_identity_sha256"],
            "completion_controls": deepcopy(row["completion_controls"]), "original_row": deepcopy(row)}
        replay.engine._validate_saved(scope, lattice, proposal, panel)
        replay.parent._validate_result(proposal, case, parent_plan["settings"])
        identity = digest({"context_key": row["context_key"], "full_IR": info, "scope": row["scope"],
            "native_lattice": row["native_lattice"], "source_panel": row["prior_panel"]})
        if (scope["binding"] != old.expanded._binding(ir) or row["source_identity_sha256"] != identity
                or any(c["source_identity_sha256"] == identity for c in cases)
                or row["original_source_files"] != ir["source_files"] or row["native_inventory"] != inventory
                or any(row[k] != proposal[k] for k in ("summary", "query_plan", "status", "reasons"))):
            raise ValueError("original_source_identity_proposal_and_inventory_required")
        policies = [r for r in ancestors[0][2] if r["context_key"] == row["context_key"]]
        source_rows = [r for r in ancestors[2][2] if r["context_key"] == row["context_key"]]
        if len(policies) != 2 or row["parent_policy_rows"] != policies or len(source_rows) != 1:
            raise ValueError("both_original_policy_rows_and_single_source_required")
        controls, source_controls = row["completion_controls"], source_rows[0]["completion_batches"]
        if type(controls) is not list or len(controls) != 2 or len(source_controls) != 2:
            raise ValueError("both_original_completion_controls_required")
        for control, policy, original in zip(controls, policies, source_controls):
            old._closed(control, replay.COMPLETION_CONTROL_KEYS, "original_completion_control")
            if (any(policy[k] != row[k] for k in ("full_IR", "scope", "native_lattice", "original_source_files"))
                    or policy["source_panel"] != row["prior_panel"]
                    or control["kind"] != original["kind"] or control["bundle"] != original["bundle"]
                    or control["required_links"] != original["required_links"]
                    or control["policy"] != policy["policy"] or control["policy_status"] != policy["status"]
                    or control["native_and_role_replay_executed"] is not False):
                raise ValueError("original_completion_links_and_policy_identity_required")
            join._edge_signature(control["required_links"])
            if any(hashes.get(control[k]["artifact"]) != control[k]["sha256"] for k in ("bundle", "policy")):
                raise ValueError("original_completion_creation_SHA_required")
            expected_jobs.append(replay._expected_job(row, proposal, control))
        case["native_counts"] = inventory
        cases.append(case)
        records.append(proposal)
    summary, known, unknown = replay.parent._aggregate(records)
    planned = None if any(j["planned_selector_occurrences"] is None for j in expected_jobs) else sum(j["planned_selector_occurrences"] for j in expected_jobs)
    if (replay_plan["jobs"] != expected_jobs or replay_plan["planned_completion_requests"] != 4
            or replay_plan["planned_selector_occurrences"] != planned
            or replay_plan["retained_control_selector_occurrences"] != sum(j["retained_control_selector_occurrences"] for j in expected_jobs)
            or parent_report["summary"] != summary or parent_report["known_summary_subtotal"] != known
            or parent_report["unknown_summary_context_occurrences"] != unknown
            or parent_report["distinct_registered_sources"] != 2 or parent_report["registered_policy_completion_rows"] != 4
            or parent_report["saved_source_proposals"] != 2 or parent_report["native_replay_planned_completion_requests"] != 4
            or parent_report["native_replay_planned_selector_occurrences"] != planned
            or parent_report["admitted_native_inventory"] != {k: sum(c["native_counts"][k] for c in cases) for k in cases[0]["native_counts"]}
            or parent_report["computed_source_proposals"] != sum(r["status"] == "computed_source_progression_proposals_not_evaluated" for r in rows)
            or parent_report["whole_source_proposal_holds"] != sum(r["status"] == "whole_source_proposal_hold" for r in rows)
            or parent_report["submitted_source_proposal_computation_complete"] is not
                all(r["status"] == "computed_source_progression_proposals_not_evaluated" for r in rows)
            or sum(len(c["scope"]["raw_lanes"]) for c in cases) != parent_report["denominators"]["selected_original_raw_lanes"]):
        raise ValueError("all_original_phase28_terminal_summary_and_jobs_required")
    return cases


def _completion(row, case, binding, plan, control, si, ci, reader, hashes, settings, limits):
    """Frozen completion contract with explicit new owned reader, no old IO."""
    old._closed(row, kernels.JOB_KEYS, "indexed_saved_completion")
    if (row["status"] != "computed_native_role_source_requests_not_selected" or row["error"] is not None
            or row["unpersisted_selector_ranges"] != [] or row["persisted_batch_prefix_summary"] is not None
            or row["runtime_activity_after_last_persisted_batch"] is not False):
        raise ValueError("whole_complete_indexed_completion_required")
    n, b = plan["planned_selectors"], plan["planned_batches"]
    if n > settings["max_entries_per_completion"] or b > settings["max_batches_per_completion"]:
        raise kernels.SourceAdmissionHold("whole_completion_count_hold", {"planned_entries": n, "planned_batches": b})
    if (row["completion_kind"] != control["kind"] or row["original_control"] != control
            or any(type(row[k]) is not int or row[k] != value for k, value in
                (("planned_selector_occurrences", n), ("planned_batches", b), ("received_batch_packets", b)))
            or type(row["batches"]) is not list or len(row["batches"]) != b):
        raise ValueError("exact_original_completion_denominators_required")
    bundle = _record(row["bundle"], replay.engine.native.BUNDLE_PREFIX, reader, hashes)
    header = row["header"]
    old._closed(header, {"binding_ref", "plan_ref", "status", "reasons"}, "saved_header")
    if header["plan_ref"] != sealed._ref(plan):
        raise ValueError("original_header_plan_ref_required")
    replay._header({"packet_type": "header", "binding_ref": header["binding_ref"], "plan": plan,
        "bundle": bundle, "status": header["status"], "reasons": header["reasons"]}, case, binding, plan, control, limits)
    terminal = _record(row["job"], replay.engine.PREFIX, reader, hashes)
    refs = []
    for expected, batch in zip(plan["batches"], row["batches"]):
        old._closed(batch, kernels.BATCH_KEYS, "indexed_saved_batch")
        if any(type(batch[k]) is not int or batch[k] != expected[k] for k in replay.PLAN_BATCH_KEYS):
            raise ValueError("all_ordered_original_batch_positions_required")
        for name in ("comparison", "explanation"):
            old._closed(batch[name], join.INFO_KEYS, "indexed_body_info")
            if hashes.get(batch[name]["artifact"]) != batch[name]["sha256"]:
                raise ValueError("exact_registered_body_SHA_required")
        refs.append({**deepcopy(expected), "comparison_ref": deepcopy(batch["comparison"]["record_ref"]),
            "explanation_ref": deepcopy(batch["explanation"]["record_ref"])})
    if row["plan"]["record_ref"] != sealed._ref(plan) or row["summary"] != terminal["summary"]:
        raise ValueError("original_plan_and_terminal_summary_join_required")
    declared = deepcopy(row["summary"])
    replay._job(terminal, case, binding, plan, bundle, control, refs, declared, limits, [])
    if (declared["native_computed_paths"] != n or declared["role_computed_paths"] != n
            or declared["completed_batches"] != b or any(declared[k] != 0 for k in
                ("withheld_native_paths", "withheld_role_paths", "uncomputed_role_accounts"))):
        raise ValueError("all_original_saved_body_position_counts_required")
    request = sealed._seal({"version": kernels.VERSION, "source_identity_sha256": case["source_identity_sha256"],
        "source_index": si, "completion_index": ci, "original_control": deepcopy(control),
        "proposal_ref": sealed._ref(case["proposal"]), "terminal_job_ref": sealed._ref(terminal),
        "selector_inventory_sha256": digest(case["proposal"]["selectors"]),
        "status": "original_saved_completion_request_not_selected", "selected": None}, kernels.REQUEST_PREFIX)
    groups = []
    for key in case["lattice"]["keys"]:
        indices = [i for i, s in enumerate(case["proposal"]["selectors"]) if s["key_id"] == key["record_id"]]
        full, tail = divmod(len(indices), settings["block_size"])
        grid = full + bool(tail)
        tasks = grid * (grid - 1) // 2 + full * (settings["block_size"] > 1) + (tail > 1)
        groups.append({"key_ref": sealed._ref(key), "bundle_ref": sealed._ref(bundle),
            "completion_request_ref": sealed._ref(request), "selector_indices": indices,
            "planned_entries": len(indices), "planned_pairs": len(indices) * (len(indices) - 1) // 2,
            "planned_block_tasks": tasks, "block_size": settings["block_size"]})
    if sorted(i for g in groups for i in g["selector_indices"]) != list(range(n)):
        raise ValueError("all_original_selector_key_membership_required")
    return {"row": deepcopy(row), "case": case, "bundle": bundle, "terminal": terminal,
        "request": request, "plan": plan, "binding": binding, "groups": groups,
        "declared_summary": declared, "iterator_started": False, "consumed": False,
        "validated_batches": 0, "entries": []}


def _load_metadata(data, reader):
    directory, settings = Path(data["directory"]), data["settings"]
    report, plan, rows = (reader.read(directory / name) for name in
        ("report.json", "run-plan.json", "context-index.json"))
    old._closed(report, kernels.REPORT_KEYS, "saved_phase29_report")
    old._closed(plan, kernels.PLAN_KEYS, "saved_phase29_plan")
    for record in (report, plan):
        if record["version"] != replay.VERSION:
            raise ValueError("original_phase29_version_required")
        kernels._unpromoted(record)
    count_names = ("planned_distinct_sources", "planned_completion_requests", "planned_selector_occurrences", "planned_batches")
    for name in count_names:
        old._limit(plan[name], name)
        if type(report[name]) is not int or report[name] != plan[name]:
            raise ValueError("original_report_plan_denominator_mismatch")
    for name in ("saved_terminal_jobs", "computed_completion_requests", "fresh_bridge_preparation_calls_attempted",
            "verified_fresh_native_preparations", "whole_completion_holds", "incomplete_or_unstarted_completion_requests",
            "missing_terminal_completion_requests"):
        old._limit(report[name], "saved_phase29_report." + name)
    if (report["status"] != "fresh_source_replay_saved_not_selected"
            or any(report[k] is not True for k in ("computation_integrity_passed", "inputs_and_code_unchanged", "artifacts_unchanged"))
            or any(report[k] != [] for k in ("changed_inputs_or_code", "changed_artifacts", "failures", "partial_output_files", "persisted_partial_batch_summaries"))
            or any(type(report[k]) is not int or report[k] != 0 for k in
                ("whole_completion_holds", "incomplete_or_unstarted_completion_requests", "missing_terminal_completion_requests"))
            or report["computed_completion_requests"] != plan["planned_completion_requests"]
            or report["saved_terminal_jobs"] != plan["planned_completion_requests"]
            or report["denominators"] != plan["denominators"]
            or type(rows) is not list or len(rows) != plan["planned_distinct_sources"] or len(rows) > settings["max_contexts"]
            or report["submitted_nonempty_requests_completed"] is not (plan["planned_selector_occurrences"] > 0)
            or report["known_empty_request_set"] is not (plan["planned_selector_occurrences"] == 0)):
        raise ValueError("complete_original_phase29_report_required_no_prefix")
    declared = data["read_plan"].record()["original_denominators"]
    expected_declared = {"denominators": plan["denominators"], **{k: plan[k] for k in count_names}}
    if declared != expected_declared:
        raise ValueError("caller_read_denominators_must_equal_authenticated_original_plan")
    hashes = _merge((plan["inputs"], plan["code"], report["artifact_hashes"]))
    report_path = str(directory / "report.json")
    if report_path not in data["registered"]:
        raise ValueError("original_phase29_report_registration_required")
    hashes[report_path] = data["registered"][report_path]
    if hashes != data["registered"]:
        raise ValueError("exact_original_creation_artifact_SHA_closure_required_not_extra_registration")
    roots = [_inventory(directory, report, hashes)]
    parent_dir = Path(plan["parent"]).resolve(strict=True)
    parent_report, parent_plan, parent_rows, parent_replay = (reader.read(parent_dir / name) for name in
        ("report.json", "run-plan.json", "context-index.json", "native-replay-plan.json"))
    if (hashes.get(str(parent_dir / "report.json")) != plan["parent_report_sha256"]
            or plan["parent_source_authority"] != parent_report["source_authority"]
            or parent_report["denominators"] != report["denominators"]):
        raise ValueError("exact_original_phase28_parent_required")
    kernels._historical_creation(plan, parent_plan, parent_report, parent_dir)
    closure = _merge((parent_plan["inputs"], parent_plan["code"], parent_report["artifact_hashes"]))
    closure[str(parent_dir / "report.json")] = hashes[str(parent_dir / "report.json")]
    if closure != plan["inputs"]:
        raise ValueError("exact_original_phase28_input_closure_required")
    roots.append(_inventory(parent_dir, parent_report, hashes))
    ancestors = _phase28_metadata(reader, parent_dir, parent_report, parent_plan, parent_rows,
        parent_replay, hashes, roots)
    supplied_roots = [{"directory": r.directory, "registered_sha256": r.registered_sha256} for r in data["roots"]]
    if supplied_roots != roots:
        raise ValueError("exact_ordered_original_archive_and_ancestor_inventories_required")
    cases = _cases(parent_rows, reader, hashes, settings, parent_plan, ancestors, parent_report, parent_replay)
    if len(cases) != len(rows):
        raise ValueError("all_original_source_positions_required")
    replay_limits = {k: plan["settings"][k] for k in replay.engine.DEFAULTS}
    replay._settings(plan["settings"])
    jobs = []
    for si, (row, case) in enumerate(zip(rows, cases)):
        old._closed(row, kernels.ROW_KEYS, "original_saved_source_index")
        original = case["original_row"]
        for target, source in (("context_key", "context_key"), ("source_identity_sha256", "source_identity_sha256"),
                ("full_IR", "full_IR"), ("scope", "scope"), ("archived_lattice", "native_lattice"),
                ("prior_panel", "prior_panel"), ("source_proposal", "proposal"),
                ("original_source_files", "original_source_files"), ("parent_policy_rows", "parent_policy_rows"),
                ("native_inventory", "native_inventory")):
            if row[target] != original[source]:
                raise ValueError("exact_original_source_index_registration_join_required")
        if row["error"] is not None or row["status"] != "ready_fresh_source_proposal_replay":
            raise ValueError("complete_original_source_rebind_required")
        fresh = _record(row["fresh_lattice"], replay.engine.native.PREFIX, reader, hashes)
        binding = _record(row["binding"], replay.engine.BINDING_PREFIX, reader, hashes)
        saved_plan = _record(row["plan"], replay.engine.PLAN_PREFIX, reader, hashes)
        replay._binding(binding, case, fresh)
        replay._plan(saved_plan, case, replay_limits)
        if type(row["jobs"]) is not list or len(row["jobs"]) != len(case["completion_controls"]):
            raise ValueError("all_original_completion_positions_required")
        for ci, (job, control) in enumerate(zip(row["jobs"], case["completion_controls"])):
            if job["plan"] != row["plan"]:
                raise ValueError("exact_original_same_source_plan_reference_required")
            jobs.append(_completion(job, case, binding, saved_plan, control, si, ci, reader, hashes, settings, replay_limits))
    groups = [g for j in jobs for g in j["groups"]]
    if (len(groups) > settings["max_groups"] or len(jobs) != plan["planned_completion_requests"]
            or sum(j["plan"]["planned_selectors"] for j in jobs) != plan["planned_selector_occurrences"]
            or sum(j["plan"]["planned_batches"] for j in jobs) != plan["planned_batches"]
            or replay._aggregate([j["declared_summary"] for j in jobs]) != report["summary"]):
        raise ValueError("all_original_request_group_terminal_denominators_required")
    return {"report": report, "plan": plan, "cases": cases, "jobs": jobs, "hashes": hashes,
        "inventories": roots, "replay_limits": replay_limits, "metadata_authenticated": True}


def open_archive(plan):
    data = _plan(plan)
    reader = budget.begin_reads(data["read_plan"])
    try:
        metadata = _load_metadata(data, reader)
        _complete_original_read_membership(data, reader, metadata)
    except BaseException as exc:
        raise ArchiveFailure("archive_metadata_failure:" + str(exc), plan=plan, reader=reader) from exc
    handle = object.__new__(SavedArchive)
    _ARCHIVES[handle] = {**data, **metadata, "reader": reader, "sources": {}, "groups": {},
        "next_completion": 0, "active_iterator": False, "failure": None, "finished": False,
        "source_holds": [], "group_holds": []}
    return handle


def _complete_original_read_membership(data, reader, metadata):
    """An admitted caller prefix cannot authorize body or source/group work."""
    planned = data["read_plan"].record()["reads"]
    consumed = reader.read_files
    if any(r["phase"] != "metadata" for r in planned[:consumed]):
        raise ValueError("all_consumed_metadata_reads_must_be_declared_metadata_phase")
    expected = [batch[name] for job in metadata["jobs"] for batch in job["row"]["batches"]
        for name in ("comparison", "explanation")]
    remaining = planned[consumed:]
    if len(remaining) != len(expected):
        raise ValueError("whole_original_remaining_body_read_inventory_required_no_prefix")
    for occurrence, info in zip(remaining, expected):
        encoding = "gzip-json" if Path(info["artifact"]).suffix == ".gz" else "json"
        if (occurrence["path"] != info["artifact"] or occurrence["sha256"] != info["sha256"]
                or occurrence["phase"] != "body" or occurrence["encoding"] != encoding
                or occurrence["physical_bytes"] is None or occurrence["decoded_bytes"] is None):
            raise ValueError("exact_whole_original_ordered_body_read_membership_required")


def metadata_prepared(handle):
    state = _archive(handle)
    plan = state["plan"]
    return {"version": VERSION, "authority": AUTHORITY,
        "original_metadata_membership_authenticated": state["metadata_authenticated"],
        "original_denominators": deepcopy(state["read_plan"].record()["original_denominators"]),
        "original_creation_code_files": len(plan["code"]),
        "original_parent_inventory_counts": [len(r["registered_sha256"]) for r in state["inventories"][1:]],
        "groups": [deepcopy(g) for j in state["jobs"] for g in j["groups"]],
        "original_group_declarations": [{"source_index": j["request"]["source_index"],
            "completion_index": j["request"]["completion_index"], "group_index": gi,
            "original": {"source_identity_sha256": j["case"]["source_identity_sha256"],
                "scope_ref": sealed._ref(j["case"]["scope"]), "lattice_ref": sealed._ref(j["case"]["lattice"]),
                **deepcopy(g)}} for j in state["jobs"] for gi, g in enumerate(j["groups"])],
        "planned_pairs": sum(g["planned_pairs"] for j in state["jobs"] for g in j["groups"]),
        "planned_block_tasks": sum(g["planned_block_tasks"] for j in state["jobs"] for g in j["groups"]),
        "planned_selector_occurrences": plan["planned_selector_occurrences"],
        "body_join_complete": False, "source_intrinsic_groups_complete": False,
        "snapshot_scope": "metadata_stage_observation_current_coverage_only_in_finish_archive",
        "read_ledger": budget.read_ledger(state["reader"]), "flags": _flags()}


def source_prepared(handle, source_index):
    state = _archive(handle)
    old._limit(source_index, "original_source_index")
    if source_index >= len(state["cases"]):
        raise ValueError("exact_original_source_index_required")
    if state["finished"] or state["failure"]:
        raise ValueError("terminal_or_failed_archive_cannot_issue_cached_source_authority")
    if source_index not in state["sources"]:
        if state["finished"] or state["failure"]:
            raise ValueError("terminal_archive_cannot_prepare_new_source")
        case = state["cases"][source_index]
        bundles = {j["bundle"]["record_id"]: j["bundle"] for j in state["jobs"] if j["request"]["source_index"] == source_index}
        try:
            state["sources"][source_index] = shared.prepare_saved_source(case["scope"], case["lattice"],
                bundles=bundles, limits=state["source_limits"])
        except shared.WholeSourceHold as exc:
            held = {"source_index": source_index, "source_identity_sha256": case["source_identity_sha256"],
                "offending_source_plan": exc.plan.record()}
            state["source_holds"].append(deepcopy(held))
            raise ArchiveFailure("whole_original_source_hold_no_denominator_shrink", reader=state["reader"],
                metadata={**held, "whole_original": metadata_prepared(handle)}) from exc
    return state["sources"][source_index]


def iter_completion_entries(handle, source_index, completion_index):
    """Exact original job order; early iterator close cannot be restarted."""
    state = _archive(handle)
    for value in (source_index, completion_index):
        old._limit(value, "original_completion_position")
    if state["finished"] or state["failure"] or state["active_iterator"]:
        raise ValueError("archive_terminal_failed_or_iterator_active")
    position = state["next_completion"]
    if position >= len(state["jobs"]):
        raise ValueError("all_original_completions_already_consumed")
    job = state["jobs"][position]
    if (job["request"]["source_index"], job["request"]["completion_index"]) != (source_index, completion_index) or job["iterator_started"]:
        raise ValueError("exact_next_original_completion_required_no_restart_or_reorder")
    job["iterator_started"], state["active_iterator"] = True, True
    case, bundle, plan = job["case"], job["bundle"], job["plan"]
    counts = replay._empty_counts(plan["planned_selectors"], plan["planned_batches"])
    counts["fresh_bundle_registrations"] = 1
    origins = {o["record_id"]: o for c in case["lattice"]["catalog_inventory"] for o in c["origins"]}
    keys = {k["record_id"]: k for k in case["lattice"]["keys"]}
    refs, seen = [], set()
    try:
        for batch in job["row"]["batches"]:
            planned = {k: batch[k] for k in replay.PLAN_BATCH_KEYS}
            lo, hi = batch["selector_start"], batch["selector_end_exclusive"]
            selectors = case["proposal"]["selectors"][lo:hi]
            comparison = _record(batch["comparison"], replay.engine.native.COMPARISON_PREFIX, state["reader"], state["hashes"])
            explanation = _record(batch["explanation"], replay.engine.roles.PREFIX, state["reader"], state["hashes"])
            replay._batch(comparison, explanation, selectors, case, bundle, planned, state["replay_limits"])
            if len(comparison["paths"]) != len(selectors) or len(explanation["paths"]) != len(selectors):
                raise ValueError("all_original_native_role_batch_positions_required")
            entries = []
            for ordinal, (selector, path, role) in enumerate(zip(selectors, comparison["paths"], explanation["paths"])):
                if role["native_path_ref"] != sealed._ref(path):
                    raise ValueError("exact_original_native_role_array_ordinal_required")
                identity = digest(path["logical_tuple"])
                if identity in seen:
                    raise ValueError("duplicate_original_logical_tuple_not_signature_alias")
                seen.add(identity)
                entry = join._entry(path, role, selector, comparison, explanation,
                    case["lattice"], case["scope"], bundle, origins, keys)
                entries.append({"selector_index": lo + ordinal, "entry": entry})
            replay._add_batch(counts, comparison, explanation, bundle)
            refs.append({**deepcopy(planned), "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)})
            job["validated_batches"] += 1
            job["entries"].extend(entries)
            yield {"completion_request_ref": sealed._ref(job["request"]), "batch_index": batch["batch_index"],
                "selector_start": lo, "selector_end_exclusive": hi, "entries": deepcopy(entries)}
            if state["finished"] or state["failure"]:
                raise ValueError("terminal_archive_iterator_cannot_resume_or_promote")
        if state["finished"] or state["failure"]:
            raise ValueError("terminal_archive_cannot_validate_completion_after_finish")
        replay._job(job["terminal"], case, job["binding"], plan, bundle, job["row"]["original_control"],
            refs, counts, state["replay_limits"], [])
        if state["finished"] or state["failure"]:
            raise ValueError("terminal_archive_cannot_promote_completion_after_validation")
        job["consumed"] = True
        state["next_completion"] += 1
    except BaseException as exc:
        state["failure"] = state["failure"] or "original_completion_failure:" + type(exc).__name__
        raise
    finally:
        state["active_iterator"] = False
        if not job["consumed"]:
            state["failure"] = state["failure"] or "original_completion_closed_before_terminal_validation"


def prepare_original_groups(handle, source_index, completion_index):
    state = _archive(handle)
    for value in (source_index, completion_index):
        old._limit(value, "original_completion_position")
    if state["finished"] or state["failure"]:
        raise ValueError("terminal_or_failed_archive_cannot_issue_cached_group_authority")
    matches = [j for j in state["jobs"] if (j["request"]["source_index"], j["request"]["completion_index"]) ==
        (source_index, completion_index)]
    if len(matches) != 1 or not matches[0]["consumed"]:
        raise ValueError("complete_original_completion_body_membership_required")
    job = matches[0]
    source = source_prepared(handle, source_index)
    by_index = {r["selector_index"]: r["entry"] for r in job["entries"]}
    if sorted(by_index) != list(range(job["plan"]["planned_selectors"])):
        raise ValueError("exact_all_original_selector_ordinals_required")
    result = []
    for gi, group in enumerate(job["groups"]):
        key = (source_index, completion_index, gi)
        if key not in state["groups"]:
            if state["finished"] or state["failure"]:
                raise ValueError("terminal_archive_cannot_prepare_new_group")
            try:
                prepared = shared.prepare_saved_group(source, [by_index[i] for i in group["selector_indices"]],
                    completion_request_ref=group["completion_request_ref"], selector_indices=group["selector_indices"],
                    key_ref=group["key_ref"], bundle_ref=group["bundle_ref"], block_size=group["block_size"], limits=state["group_limits"])
            except shared.WholeGroupHold as exc:
                state["group_holds"].append({"source_index": source_index, "completion_index": completion_index,
                    "group_index": gi, "original_group": deepcopy(group), "offending_group_plan": exc.plan.record()})
                raise ArchiveFailure("whole_original_group_hold_no_denominator_shrink", reader=state["reader"],
                    metadata={"original_group": group, "whole_original": metadata_prepared(handle), "offending_group_plan": exc.plan.record()}) from exc
            state["groups"][key] = prepared
        result.append(state["groups"][key])
    return tuple(result)


def finish_archive(handle):
    state = _archive(handle)
    if state["active_iterator"]:
        state["failure"] = state["failure"] or "terminal_archive_called_while_completion_iterator_active"
    state["finished"] = True
    ledger = budget.finish_reads(state["reader"])
    body_complete = bool(state["jobs"]) and all(j["consumed"] for j in state["jobs"])
    group_count = sum(len(j["groups"]) for j in state["jobs"])
    complete = not state["failure"] and ledger["submitted_read_set_complete"] and body_complete
    intrinsic = complete and len(state["sources"]) == len(state["cases"]) and len(state["groups"]) == group_count
    return {"version": VERSION, "authority": AUTHORITY,
        "original_metadata_membership_authenticated": state["metadata_authenticated"],
        "all_original_indexed_batches_join_validated": complete,
        "all_original_source_intrinsic_groups_validated": intrinsic,
        "original_denominators": deepcopy(state["read_plan"].record()["original_denominators"]),
        "planned_groups": group_count, "prepared_groups": len(state["groups"]),
        "planned_pairs": sum(g["planned_pairs"] for j in state["jobs"] for g in j["groups"]),
        "validated_batches": sum(j["validated_batches"] for j in state["jobs"]),
        "completed_original_completions": sum(j["consumed"] for j in state["jobs"]),
        "incomplete_original_completions": sum(not j["consumed"] for j in state["jobs"]),
        "source_holds": deepcopy(state["source_holds"]), "group_holds": deepcopy(state["group_holds"]),
        "failure": state["failure"], "read_ledger": ledger, "selected": None, "flags": _flags()}
