"""Pinned result reuse plus fresh owned request admission; never JSON reload.

The external receipt hash is a trust anchor from a previously observed writer
run, NOT a seal supplied by the receipt itself. Old block contents are protected
by that receipt and physical hashes, not decoded/recomputed in this run. Only a
fresh RequestPreparation authorizes remaining comparisons. No old capability or
private predecessor registry is restored. This snapshot accepts only a clean
prefix checkpoint produced by the frozen v0.2 writer.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hmac
import json
from pathlib import Path
import secrets
from weakref import WeakKeyDictionary

from . import cross_batch_read_budget as reads
from . import transfer_bound_request_coordinator as request
from . import transfer_bound_progression_storage as base
from . import proof_shared_source_progression_contrast as core
from . import proof_shared_progression_streaming as streaming
from . import proof_shared_transfer_bounds as bounds

VERSION = "transfer-bound-storage-continuation-0.1.0"
_SECRET = secrets.token_bytes(32)
_CHECKPOINTS, _PLANS, _RUNS = WeakKeyDictionary(), WeakKeyDictionary(), WeakKeyDictionary()
_raw, _sha = base._raw, base._sha
_COUNTS = ("completion_requests", "selector_occurrences", "batches", "groups", "pairs", "block_tasks")


@dataclass(frozen=True, slots=True)
class _Owned:
    payload: bytes
    attached: tuple
    signature: bytes


class Checkpoint:
    __slots__ = ("__weakref__",)
    def __new__(cls): raise ValueError("pinned_checkpoint_factory_required")
    def __setattr__(self, name, value): raise AttributeError("immutable_checkpoint")
    def record(self): return json.loads(_owned(self, Checkpoint, _CHECKPOINTS).payload)


class ContinuationPlan:
    __slots__ = ("__weakref__",)
    def __new__(cls): raise ValueError("fresh_request_continuation_factory_required")
    def __setattr__(self, name, value): raise AttributeError("immutable_continuation_plan")
    def record(self): return json.loads(_owned(self, ContinuationPlan, _PLANS).payload)


class ContinuationRun:
    __slots__ = ("__weakref__",)
    def __new__(cls): raise ValueError("continuation_run_factory_required")
    def __setattr__(self, name, value): raise AttributeError("owned_continuation_run")


def _signature(handle, payload, attached):
    return hmac.digest(_SECRET, _raw([id(handle), id(payload), id(attached)]), "sha256")


def _owned(handle, kind, registry):
    if type(handle) is not kind or handle not in registry:
        raise ValueError("owned_continuation_handle_required_not_JSON")
    state = registry[handle]
    if (type(state) is not _Owned or type(state.payload) is not bytes or type(state.attached) is not tuple
            or not hmac.compare_digest(state.signature, _signature(handle, state.payload, state.attached))):
        raise ValueError("continuation_handle_state_changed")
    return state


def _issue(kind, registry, payload, attached=()):
    handle = object.__new__(kind)
    registry[handle] = _Owned(payload, attached, _signature(handle, payload, attached))
    return handle


def _integer(value):
    if type(value) is not int or value < 0: raise ValueError("exact_nonnegative_integer_required")
    return value


def _bounded_encode(value, byte_cap, work_cap):
    meter = streaming._Measure(work_cap)
    size = streaming._measure_owned(value, meter)
    charged = meter.work + 4 * size + meter.visits
    if size > byte_cap or charged > work_cap:
        raise ValueError("continuation_metadata_bytes_or_work_hold")
    encoded = _raw(value)
    if len(encoded) != size: raise ValueError("continuation_exact_metadata_size_disagrees")
    return encoded, charged


def load_checkpoint(path, externally_pinned_sha256, *, already_decoded_bytes=0):
    """Bounded receipt read. A newly re-sealed attacker receipt is not trusted.

    Caller must supply the hash from an independent successful writer observation.
    This function cannot establish that external trust, nor confer music authority.
    Its read bytes must be deducted from subsequent fresh admission's SAME budget.
    """
    path = reads._path(str(path)); base._hex(externally_pinned_sha256)
    consumed = _integer(already_decoded_bytes)
    defaults = reads.ReadLimits()
    count = path.stat().st_size
    if consumed > defaults.max_total_decoded_bytes:
        raise ValueError("cumulative_checkpoint_read_hold")
    spec = reads.ReadInput("pinned-prior-writer-receipt", str(path), externally_pinned_sha256,
        count, count, phase="metadata")
    plan = reads.plan_read_run([spec], original_denominators={"pinned_receipts": 1},
        registered_sha256={str(path): externally_pinned_sha256},
        limits=reads.ReadLimits(max_total_decoded_bytes=defaults.max_total_decoded_bytes - consumed))
    reader = reads.begin_reads(plan)
    report = reads.read_record(reader, spec.read_id)
    terminal_read = reads.finish_reads(reader)
    if not terminal_read["submitted_read_set_complete"]:
        raise ValueError("whole_checkpoint_read_required")
    # Timing/memory diagnostics may contain finite floats; they are already
    # checked by the bounded metadata reader but never enter musical authority.
    projection = {k: report[k] for k in ("failure", "current_code_final_guard", "artifacts", "whole_request_preparation")}
    projection["storage_execution"] = {"failure": report["storage_execution"].get("failure"),
        "storage_terminal": report["storage_execution"]["storage_terminal"]}
    receipt, work = base._metadata_snapshot(projection, defaults.max_file_bytes,
        base.StorageLimits().max_plan_finalization_work)
    prior = receipt["storage_execution"]["storage_terminal"]
    if (receipt["failure"] is not None or receipt["storage_execution"].get("failure") is not None
            or receipt["current_code_final_guard"]["all_current_SHA_confirmed"] is not True
            or receipt["current_code_final_guard"]["changed_paths"]
            or receipt["current_code_final_guard"]["uncertain_paths"]
            or prior["version"] != base.VERSION or prior["storage_integrity_passed"] is not True
            or prior["physical_closure_verified_terminally"] is not True or prior["terminal_persisted"] is not True
            or any(prior[k] for k in ("errors", "changed_protected_paths", "changed_output_paths",
                "guard_observation_errors", "unknown_physical_output_attempts", "unconfirmed_guard_observations"))
            or any(v is not False for v in prior["flags"].values())
            or any(prior[k] is not None for k in ("selected", "rank", "confidence", "musical_outcome"))):
        raise ValueError("clean_unpromoted_prior_writer_terminal_required")
    root, hashes, sizes = path.parent, {str(path): externally_pinned_sha256}, {str(path): count}
    storage_attempts = prior["artifact_attempts"]
    limit = base.StorageLimits()
    if type(storage_attempts) is not list or len(storage_attempts) > limit.max_tasks + limit.max_groups + limit.max_sources + 2:
        raise ValueError("bounded_prior_artifact_inventory_required")
    def register(name, sha, size):
        p = reads._path(name); base._hex(sha); _integer(size)
        if not reads._inside(p, root) or str(p) in hashes:
            raise ValueError("unique_prior_artifact_inside_receipt_root_required")
        if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
            raise ValueError("prior_artifact_physical_length_changed")
        hashes[str(p)], sizes[str(p)] = sha, size
    for item in storage_attempts:
        if (any(item[k] is not True for k in ("persisted", "owned_file", "stream_complete")) or item["error"] is not None
                or item["physical_sha256"] != item["complete_stream_sha256"]
                or item["physical_sha256"] != item["attempted_sha256"]
                or item["physical_bytes"] != item["attempted_bytes"]):
            raise ValueError("prior_successful_whole_artifact_required")
        register(item["artifact"], item["physical_sha256"], item["physical_bytes"])
    for item in receipt["artifacts"]:
        register(item["path"], item["sha256"], item["bytes"])
    guard = {"protected_sha256": hashes, "protected_roots": [{"directory": str(root), "registered_sha256": hashes}]}
    io = base._io_account()
    if base._guard_full(guard, io=io, phase="pinned_checkpoint_full"):
        raise ValueError("prior_receipt_or_exact_artifact_inventory_changed")
    info = {"receipt_path": str(path), "externally_pinned_sha256": externally_pinned_sha256,
        "root": str(root), "protected_sha256": hashes, "physical_lengths": sizes,
        "read_ledger": terminal_read, "checkpoint_metadata_snapshot_work": work, "file_hash_IO": io,
        "prior_preparation": receipt["whole_request_preparation"], "prior_storage": prior,
        "prior_storage_physical_bytes": sum(a["physical_bytes"] for a in storage_attempts)}
    if info["prior_storage_physical_bytes"] != prior["physical_output_bytes"]:
        raise ValueError("prior_physical_storage_account_mismatch")
    encoded, charged = _bounded_encode(info, defaults.max_file_bytes, limit.max_plan_finalization_work - work)
    return _issue(Checkpoint, _CHECKPOINTS, encoded)


def plan_continuation(prepared, checkpoint, *, protected_sha256=None, limits=base.StorageLimits()):
    """Join trusted old results to ALL groups of a newly admitted owned request."""
    owner = request._issued(prepared)
    fresh = prepared.record()
    original_plan = base._plan(prepared.storage_plan)
    cp = json.loads(_owned(checkpoint, Checkpoint, _CHECKPOINTS).payload)
    if type(limits) is not base.StorageLimits: raise ValueError("exact_tightened_storage_limits_required")
    old_prep, prior = cp["prior_preparation"], cp["prior_storage"]
    for name in ("selection", "whole_original", "selected_completion", "omitted_completions"):
        if fresh[name] != old_prep[name]: raise ValueError("fresh_original_request_identity_mismatch:" + name)
    for name in _COUNTS:
        w, s, o = (fresh[k][name] for k in ("whole_original", "selected_completion", "omitted_completions"))
        if _integer(w) != _integer(s) + _integer(o): raise ValueError("original_denominator_complement_mismatch")
    record = json.loads(original_plan.record)
    if record["reasons"]: raise ValueError("fresh_whole_request_storage_plan_hold")
    if (len(record["groups"]) > limits.max_groups or len(record["sources"]) > limits.max_sources
            or sum(len(g["tasks"]) for g in record["groups"]) > limits.max_tasks):
        raise ValueError("whole_continuation_inventory_hold")
    old_plan = old_prep["storage_plan"]
    if record["original_denominators"] != old_plan["original_denominators"]:
        raise ValueError("original_storage_denominators_mismatch")
    if record["sources"] != old_plan["sources"] or len(record["groups"]) != len(prior["groups"]):
        raise ValueError("same_complete_source_and_group_inventory_required")
    artifacts = {Path(a["artifact"]).name: a for a in prior["artifact_attempts"]}
    if len(artifacts) != len(prior["artifact_attempts"]): raise ValueError("unique_prior_storage_artifact_names_required")
    old_storage_roots = {str(Path(a["artifact"]).parent) for a in prior["artifact_attempts"]}
    if len(old_storage_roots) != 1: raise ValueError("one_prior_writer_destination_required")
    consumed_artifacts = set()
    def artifact(name, kind, byte_count, sha):
        item = artifacts.get(name)
        if item is None or item["kind"] != kind or item["physical_bytes"] != byte_count or item["physical_sha256"] != sha:
            raise ValueError("prior_artifact_and_bound_ledger_mismatch:" + name)
        consumed_artifacts.add(name)
    for si, row in enumerate(record["sources"]):
        stored = prior["sources"][si]
        if any(row[k] != stored[k] for k in row) or stored["persisted"] is not True:
            raise ValueError("fresh_source_and_prior_catalog_mismatch")
        artifact(f"source-{si:04d}-catalog.json", "source_catalog", row["source_raw_bytes"], stored["encoded_sha256"])
    prior_tasks, remaining, total_pairs = [], [], 0
    saw_uncomputed = False
    for gi, gp in enumerate(record["groups"]):
        previous = prior["groups"][gi]
        for key in ("original", "source_index", "source_catalog_ref", "catalog_ref", "group_ref",
                "refinement_sha256", "entry_inventory_sha256", "tasks"):
            if gp[key] != previous[key] or gp[key] != old_plan["groups"][gi][key]:
                raise ValueError("fresh_all_group_and_task_binding_mismatch:" + key)
        if gp["hold_reasons"] or previous["catalog_persisted"] is not True:
            raise ValueError("whole_group_catalog_required_for_continuation")
        artifact(f"group-{gi:04d}-catalog.json", "local_catalog", gp["catalog_raw_bytes"], previous["catalog_encoded_sha256"])
        rows = previous["task_ledger"]
        if len(rows) != len(gp["tasks"]): raise ValueError("whole_prior_task_ledger_required")
        for ti, (task, tr) in enumerate(zip(gp["tasks"], rows)):
            n = _integer(task["expected_pairs"]); total_pairs += n
            if tr["task"] != task: raise ValueError("exact_prior_task_identity_required")
            if tr["status"] == "computed_persisted":
                if (any(type(tr[k]) is not int for k in ("computed_pairs", "persisted_pairs", "held_pairs", "unconfirmed_computation_pairs"))
                        or saw_uncomputed or tr["calculation_attempted"] is not True or tr["core_result_confirmed"] is not True
                        or tr["computed_pairs"] != n or tr["persisted_pairs"] != n or tr["held_pairs"] != 0
                        or tr["unconfirmed_computation_pairs"] != 0):
                    raise ValueError("prior_only_clean_confirmed_prefix_supported")
                artifact(f"group-{gi:04d}-block-{ti:06d}.json", "block", tr["encoded_bytes"], tr["encoded_sha256"])
                prior_tasks.append({"group_index": gi, "task_index": ti, **deepcopy(tr)})
            elif (tr["status"] == "uncomputed" and tr["calculation_attempted"] is False
                    and tr["core_result_confirmed"] is False
                    and all(tr[k] == 0 and type(tr[k]) is int for k in
                        ("computed_pairs", "persisted_pairs", "held_pairs", "unconfirmed_computation_pairs"))):
                saw_uncomputed = True
                remaining.append({"group_index": gi, "task_index": ti, "task": task,
                    "byte_cap": min(limits.max_block_encoded_bytes, gp["task_encoded_caps"][ti]),
                    "serialization_work_bound": 16 * gp["task_stream_bounds"][ti]["raw_block_byte_upper_bound"]})
            else: raise ValueError("prior_failed_held_or_unconfirmed_task_cannot_resume")
    for name, kind in (("run-plan.json", "run_plan"), ("report.json", "final_manifest")):
        item = artifacts[name]; artifact(name, kind, item["physical_bytes"], item["physical_sha256"])
    if set(artifacts) != consumed_artifacts: raise ValueError("unaccounted_prior_storage_artifact")
    saved = sum(t["persisted_pairs"] for t in prior_tasks)
    if (total_pairs != fresh["selected_completion"]["pairs"] or saved != prior["summary"]["persisted_pairs"]
            or saved != prior["summary"]["computed_pairs"]
            or total_pairs - saved != prior["summary"]["uncomputed_pairs"]
            or any(prior["summary"][k] != 0 for k in
                ("computed_unpersisted_pairs", "held_pairs", "storage_held_pairs", "unconfirmed_computation_pairs"))):
        raise ValueError("prior_and_fresh_whole_pair_account_mismatch")
    hashes = dict(record["protected_sha256"])
    for group in (old_plan["protected_sha256"], cp["protected_sha256"], protected_sha256 or {}):
        for path, sha in group.items():
            if path in hashes and hashes[path] != sha: raise ValueError("prior_and_fresh_protected_SHA_conflict")
            hashes[path] = sha
    # Frozen predecessor code is retained; protect this separately versioned
    # orchestration module and coordinator as CURRENT computation dependencies.
    current = set(record["current_code_paths"]) | set(protected_sha256 or {})
    io = base._io_account()
    for module in (request,):
        p = str(Path(module.__file__).resolve()); current.add(p)
    p = str(Path(__file__).resolve()); current.add(p)
    for p in current:
        observed = base._file_observe(p, io, "continuation_current_code")
        if p in hashes and hashes[p] != observed: raise ValueError("continuation_code_SHA_mismatch")
        hashes[p] = observed
    roots = tuple(reads.InventoryRoot(r["directory"], r["registered_sha256"]) for r in record["protected_roots"])
    roots += (reads.InventoryRoot(cp["root"], cp["protected_sha256"]),)
    hashes, guards, archives, _ = base._registration(hashes, roots, tuple(record["source_archive_roots"]), io)
    if len(hashes) > limits.max_protected_files or len(guards) > limits.max_inventory_roots:
        raise ValueError("continuation_protected_inventory_hold")
    new_reserved = limits.max_plan_bytes + limits.max_manifest_bytes + sum(t["byte_cap"] for t in remaining)
    combined_reserved = cp["prior_storage_physical_bytes"] + new_reserved
    reasons = []
    if combined_reserved > limits.max_output_bytes: reasons.append("combined_prior_and_remaining_output_reservation_hold")
    for t in remaining:
        gp = record["groups"][t["group_index"]]
        if (t["byte_cap"] < gp["task_stream_bounds"][t["task_index"]]["raw_block_byte_upper_bound"]
                or t["serialization_work_bound"] > limits.max_planning_work_per_group):
            reasons.append("whole_remaining_task_bytes_or_work_hold")
    result = {"version": VERSION, "limits": asdict(limits), "reasons": sorted(set(reasons)),
        "selection": fresh["selection"], "whole_original": fresh["whole_original"],
        "selected_completion": fresh["selected_completion"], "omitted_completions": fresh["omitted_completions"],
        "original_denominators": record["original_denominators"], "groups": record["groups"],
        "remaining_tasks": remaining, "prior_confirmed_tasks": prior_tasks,
        "prior_computed_pairs": saved, "prior_persisted_pairs": saved,
        "prior_storage_physical_bytes": cp["prior_storage_physical_bytes"],
        "prior_storage_artifact_count": len(artifacts), "prior_receipt_path": cp["receipt_path"],
        "prior_receipt_external_SHA": cp["externally_pinned_sha256"],
        "prior_result_authority": "externally_pinned_observed_writer_receipt_and_fresh_identity_binding_not_JSON_capability",
        "prior_block_contents_decoded_or_recomputed": False,
        "protected_sha256": hashes, "protected_roots": guards, "source_archive_roots": archives,
        "current_code_paths": sorted(current), "planning_file_hash_IO": io,
        "checkpoint_read_ledger": cp["read_ledger"],
        "output_reserved_bytes_before_pair_calculation": new_reserved,
        "combined_output_reserved_bytes_before_pair_calculation": combined_reserved,
        "final_manifest_reserved_bytes": limits.max_manifest_bytes,
        "flags": base._flags(), "full_archive_complete": False, "saved_JSON_restores_capability": False}
    if base._guard_full(result, io=io, phase="continuation_plan_full"):
        raise ValueError("continuation_inputs_changed_before_plan")
    encoded, work = _bounded_encode(result, limits.max_plan_bytes, limits.max_plan_finalization_work)
    manifest_bound = 5 * (len(encoded) + 4096) + len(remaining) * 4096 + (len(remaining) + 2) * (base._MAX_PATH_BYTES + 3072) + 131072
    result["final_manifest_byte_upper_bound"] = manifest_bound
    result["terminal_manifest_serialization_work_upper_bound"] = 16 * manifest_bound
    # A second pass encodes final accounting fields. Reserve its conservative
    # metadata bound BEFORE executing it rather than reporting only first pass.
    second_work_bound = 16 * (len(encoded) + 4096)
    result["plan_finalization_work_upper_bound"] = work + second_work_bound
    if manifest_bound > limits.max_manifest_bytes: result["reasons"].append("whole_continuation_manifest_byte_hold")
    if 16 * manifest_bound > limits.max_plan_finalization_work:
        result["reasons"].append("whole_continuation_manifest_work_hold")
    if work + second_work_bound > limits.max_plan_finalization_work:
        raise ValueError("whole_continuation_plan_finalization_work_hold")
    encoded, final_work = _bounded_encode(result, limits.max_plan_bytes, second_work_bound)
    return _issue(ContinuationPlan, _PLANS, encoded, (prepared, checkpoint, original_plan))


def _plan(plan):
    state = _owned(plan, ContinuationPlan, _PLANS)
    prepared, checkpoint, original = state.attached
    request._issued(prepared); _owned(checkpoint, Checkpoint, _CHECKPOINTS)
    if base._plan(prepared.storage_plan) is not original:
        raise ValueError("same_fresh_owned_request_plan_required")
    return state, original


def _run(run):
    state = _owned(run, ContinuationRun, _RUNS).attached[0]
    _plan(state["owner"])
    return state


def begin_continuation(plan, directory):
    owner, data = _plan(plan); record = plan.record()
    if record["reasons"]: raise ValueError("whole_continuation_reservation_hold")
    destination = reads._path(str(Path(directory).absolute()))
    if len(str(destination).encode("utf-8")) > base._MAX_PATH_BYTES:
        raise ValueError("bounded_continuation_destination_required")
    if any(reads._inside(destination, Path(r)) for r in record["source_archive_roots"]) or any(
            destination == Path(p) or destination in Path(p).parents for p in record["protected_sha256"]):
        raise ValueError("new_continuation_output_outside_protected_inputs_required")
    io = base._io_account()
    if base._guard_full(record, io=io, phase="continuation_begin_full"):
        raise ValueError("continuation_inputs_changed_before_begin")
    destination.mkdir(parents=False, exist_ok=False)
    state = {"owner": plan, "data": data, "plan": record, "directory": destination,
        "attempts": [], "attempted_bytes": 0, "errors": [], "stopped": False, "finished": False,
        "terminal_persisted": False, "changed_protected_paths": [], "changed_output_paths": [],
        "guard_observation_errors": [], "file_hash_IO": io, "canonical_stream_account": {
            "sha256_attempted_bytes": 0, "reserved_nonrefundable_block_serialization_validation_work_units": 0},
        "next_remaining_task": 0, "tasks": [{**deepcopy(t), "status": "uncomputed",
            "computed_pairs": 0, "persisted_pairs": 0, "held_pairs": 0,
            "calculation_attempted": False, "core_result_confirmed": False,
            "unconfirmed_computation_pairs": 0} for t in record["remaining_tasks"]]}
    run = _issue(ContinuationRun, _RUNS, b"owned_runtime", (state,))
    base._attempt(state, "run-plan.json", base._bytes_chunks(owner.payload), "run_plan",
        byte_bound=record["limits"]["max_plan_bytes"], exact_bytes=len(owner.payload))
    return run


def write_block(run, group_index, task):
    state = _run(run); _integer(group_index)
    if state["finished"] or state["stopped"]: raise ValueError("continuation_terminal_or_interrupted")
    index = state["next_remaining_task"]
    if index >= len(state["tasks"]): raise ValueError("no_remaining_task")
    row = state["tasks"][index]
    if (type(task) is not core.BlockTask or any(type(getattr(task, k)) is not int for k in
            ("row_start", "row_end", "column_start", "column_end", "expected_pairs"))
            or group_index != row["group_index"] or asdict(task) != row["task"]):
        raise ValueError("exact_next_remaining_task_required")
    if not base._guard(state): return ledger(run)
    gi, ti = row["group_index"], row["task_index"]
    prepared = state["data"].handles[gi]
    block = encoded = None
    try:
        proof = state["data"].transfer_proofs[gi]
        if proof is None or bounds._issued(proof).prepared is not prepared:
            raise ValueError("same_fresh_owned_transfer_proof_required")
        state["canonical_stream_account"]["reserved_nonrefundable_block_serialization_validation_work_units"] += row["serialization_work_bound"]
        row["calculation_attempted"] = True
        block = core.compare_block(prepared, task)
        base._validate_block(prepared, task, block, state["plan"]["groups"][gi]["original"]["selector_indices"])
        row["core_result_confirmed"] = True
        row.update(computed_pairs=block["computed_pairs"], held_pairs=block["withheld_pairs"])
        encoded = _raw(block)
        row.update(encoded_bytes=len(encoded), encoded_sha256=_sha(encoded))
        if len(encoded) > row["byte_cap"]: raise ValueError("whole_remaining_block_storage_bytes_hold")
        attempt = base._attempt(state, f"group-{gi:04d}-block-{ti:06d}.json", base._bytes_chunks(encoded), "block",
            byte_bound=row["byte_cap"], exact_bytes=len(encoded))
        row["status"] = "held" if row["held_pairs"] else "computed_unpersisted"
        if attempt["persisted"]:
            row["persisted_pairs"] = row["computed_pairs"]
            row["status"] = "held" if row["held_pairs"] else "computed_persisted"
        state["next_remaining_task"] += 1
    except BaseException as exc:
        row["unconfirmed_computation_pairs"] = task.expected_pairs if row["calculation_attempted"] and not row["core_result_confirmed"] else 0
        row["status"] = "interrupted_before_comparison" if not row["calculation_attempted"] else "interrupted_computed_unpersisted" if row["core_result_confirmed"] else "interrupted_unconfirmed_computation"
        base._error(state, base._caught_error(exc))
    finally:
        block = encoded = None
    base._guard(state)
    return ledger(run)


def ledger(run):
    state = _run(run); plan = state["plan"]
    if state["finished"]:
        base._guard(state, full=True, phase="continuation_postterminal_full")
        base._outputs(state, "continuation_postterminal_outputs")
    totals = {k: sum(t[k] for t in state["tasks"]) for k in
        ("computed_pairs", "persisted_pairs", "held_pairs", "unconfirmed_computation_pairs")}
    new_planned = sum(t["task"]["expected_pairs"] for t in state["tasks"])
    totals.update(planned_pairs=new_planned, uncomputed_pairs=new_planned - totals["computed_pairs"] - totals["held_pairs"],
        computed_unpersisted_pairs=totals["computed_pairs"] - totals["persisted_pairs"],
        unpersisted_pairs=new_planned - totals["persisted_pairs"])
    combined = {**totals, "planned_pairs": plan["selected_completion"]["pairs"],
        "computed_pairs": plan["prior_computed_pairs"] + totals["computed_pairs"],
        "persisted_pairs": plan["prior_persisted_pairs"] + totals["persisted_pairs"]}
    integrity = not state["errors"]
    complete = (state["finished"] and state["terminal_persisted"] and integrity
        and combined["computed_pairs"] == combined["planned_pairs"]
        and combined["persisted_pairs"] == combined["planned_pairs"])
    return {"version": VERSION, "selection": deepcopy(plan["selection"]),
        **{k: deepcopy(plan[k]) for k in ("whole_original", "selected_completion", "omitted_completions")},
        "original_denominators": deepcopy(plan["original_denominators"]),
        "prior_receipt_path": plan["prior_receipt_path"], "prior_receipt_external_SHA": plan["prior_receipt_external_SHA"],
        "prior_result_authority": plan["prior_result_authority"], "prior_block_contents_decoded_or_recomputed": False,
        "prior_confirmed_tasks": deepcopy(plan["prior_confirmed_tasks"]),
        "prior_computed_pairs": plan["prior_computed_pairs"], "prior_persisted_pairs": plan["prior_persisted_pairs"],
        "new_summary": totals, "summary": combined, "remaining_task_ledger": deepcopy(state["tasks"]),
        "unpersisted_task_ranges": [deepcopy(t) for t in state["tasks"] if t["persisted_pairs"] != t["task"]["expected_pairs"]],
        "selected_request_storage_complete": complete, "full_archive_complete": False,
        "storage_integrity_passed": integrity, "physical_closure_verified_terminally": state["finished"] and integrity,
        "terminal_persisted": state["terminal_persisted"], "finished": state["finished"],
        "status": "selected_request_storage_complete_not_selected" if complete else "incomplete_continuation",
        "prior_storage_physical_bytes": plan["prior_storage_physical_bytes"],
        "new_physical_output_bytes": sum(a["physical_bytes"] for a in state["attempts"] if a["physical_bytes"] is not None),
        "unknown_physical_output_attempts": sum(a["physical_bytes"] is None for a in state["attempts"]),
        "attempted_output_bytes": state["attempted_bytes"],
        "output_reserved_bytes_before_pair_calculation": plan["output_reserved_bytes_before_pair_calculation"],
        "combined_output_reserved_bytes_before_pair_calculation": plan["combined_output_reserved_bytes_before_pair_calculation"],
        "artifact_attempts": deepcopy(state["attempts"]), "errors": list(state["errors"]),
        "changed_protected_paths": list(state["changed_protected_paths"]), "changed_output_paths": list(state["changed_output_paths"]),
        "guard_observation_errors": deepcopy(state["guard_observation_errors"]),
        "file_hash_IO": deepcopy(state["file_hash_IO"]), "canonical_stream_account": deepcopy(state["canonical_stream_account"]),
        "saved_JSON_restores_capability": False, "selected": None, "rank": None, "confidence": None,
        "musical_outcome": None, "flags": base._flags()}


def finish(run):
    state = _run(run)
    if state["finished"]: return ledger(run)
    base._guard(state, full=True, phase="continuation_preterminal_full")
    base._outputs(state, "continuation_preterminal_outputs")
    try:
        report = ledger(run)
        report["terminal_commit_contract"] = "manifest_cannot_self_certify_its_own_write_verify_owned_terminal_result"
        encoded, work = _bounded_encode(report, state["plan"]["final_manifest_reserved_bytes"],
            state["plan"]["limits"]["max_plan_finalization_work"])
        state["canonical_stream_account"]["reserved_nonrefundable_terminal_manifest_work_units"] = work
        attempt = base._attempt(state, "report.json", base._bytes_chunks(encoded), "final_manifest",
            byte_bound=state["plan"]["final_manifest_reserved_bytes"], exact_bytes=len(encoded))
        state["terminal_persisted"] = attempt["persisted"]
    except BaseException as exc:
        base._error(state, "terminal_manifest_unconfirmed:" + base._caught_error(exc))
    base._guard(state, full=True, phase="continuation_terminal_full")
    base._outputs(state, "continuation_terminal_outputs")
    state["finished"] = True
    return ledger(run)
