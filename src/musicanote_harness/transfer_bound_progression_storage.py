"""Versioned source-once storage using owned category/LCM transfer proofs.

Source/local/block codecs are distinct from frozen predecessor storage. The
writer never issues/forges a contrast handle, authenticates an original archive
request, selects harmony, or treats saved JSON as a reload capability. Source
catalogs are serialized once per SAME owned source handle. Per-block fast guards
are provisional; exact registered SHA/root/output closure is required terminally.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import os
import hmac
import json
from pathlib import Path
from types import MappingProxyType
import secrets
import traceback
from weakref import WeakKeyDictionary

from . import proof_shared_source_progression_contrast as core
from . import shared_source_progression_contrast as shared
from . import proof_shared_progression_streaming as streaming
from . import proof_shared_transfer_bounds as transfer_bounds
from . import lossless_json_dag_v2 as dag
from . import cross_batch_progression_contrast as codec
from . import cross_batch_progression_storage as file_helpers
from . import cross_batch_read_budget as read_budget
from . import musical_pattern_observation as observations

VERSION = "transfer-bound-progression-storage-0.2.0"
AUTHORITY = "transfer_bound_submitted_group_storage_not_original_archive_admission"
_PLANS, _STORES = WeakKeyDictionary(), WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)
_MAX_PATH_BYTES = 1024
_raw, _sha, _hex = file_helpers._raw, file_helpers._sha, file_helpers._hex
_flags = file_helpers._flags


@dataclass(frozen=True, slots=True)
class StorageLimits:
    max_output_bytes: int = 2147483648
    max_plan_bytes: int = 2097152
    max_manifest_bytes: int = 16777216
    max_block_encoded_bytes: int = 67108864
    max_source_encoded_bytes: int = 268435456
    max_groups: int = 128
    max_tasks: int = 8192
    max_sources: int = 16
    max_protected_files: int = 20000
    max_inventory_roots: int = 16
    max_planning_work_per_group: int = 1000000000
    max_source_planning_work: int = 1000000000
    max_plan_finalization_work: int = 1000000000

    def __post_init__(self):
        for name, value in asdict(self).items():
            codec._integer(value, name)
            if value > type(self).__dataclass_fields__[name].default:
                raise ValueError("transfer_storage_limits_may_only_tighten_defaults:" + name)


@dataclass(frozen=True, slots=True)
class GroupInput:
    original: dict
    source: shared.PreparedSource
    prepared: core.CompactPreparedGroup | None = None


@dataclass(frozen=True, slots=True)
class _PlanState:
    record: bytes
    handles: tuple
    sources: tuple
    source_infos: tuple
    catalog_infos: tuple
    transfer_proofs: tuple
    signature: bytes


@dataclass(frozen=True, slots=True)
class _RunState:
    runtime: dict
    signature: bytes


def _signature(handle, state):
    # Bytes/tuples are immutable. This authenticates object ownership, not a
    # user-provided seal and not an expensive full-source hash per block.
    return hmac.digest(_SECRET, _raw([id(handle), id(state.record), id(state.handles),
        id(state.sources), id(state.source_infos), id(state.catalog_infos), id(state.transfer_proofs)]), "sha256")


class StoragePlan:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("shared_storage_plan_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_shared_storage_plan")

    def record(self):
        return json.loads(_plan(self).record)


class StorageRun:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("shared_storage_run_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_shared_storage_run")


def _plan(handle):
    if type(handle) is not StoragePlan or handle not in _PLANS:
        raise ValueError("owned_shared_storage_plan_required_not_JSON")
    state = _PLANS[handle]
    if (type(state) is not _PlanState or type(state.record) is not bytes
            or any(type(value) is not tuple for value in (state.handles, state.sources, state.source_infos, state.catalog_infos, state.transfer_proofs))
            or not hmac.compare_digest(state.signature, _signature(handle, state))):
        raise ValueError("owned_shared_storage_plan_state_changed")
    if len(state.transfer_proofs) != len(state.handles):
        raise ValueError("whole_owned_transfer_proof_inventory_required")
    for prepared, proof in zip(state.handles, state.transfer_proofs):
        if proof is not None and transfer_bounds._issued(proof).prepared is not prepared:
            raise ValueError("same_owned_group_transfer_proof_required")
    return state


def _store(handle):
    if type(handle) is not StorageRun or handle not in _STORES:
        raise ValueError("owned_shared_storage_run_required_not_JSON")
    owner = _STORES[handle]
    if type(owner) is not _RunState or not hmac.compare_digest(owner.signature,
            hmac.digest(_SECRET, _raw([id(handle), id(owner.runtime)]), "sha256")):
        raise ValueError("owned_shared_storage_run_state_changed")
    return owner.runtime


class WholeRunHold(ValueError):
    def __init__(self, plan):
        self.plan = plan.record()
        super().__init__("whole_shared_storage_run_hold:" + ",".join(self.plan["reasons"]))


def _observation_failure(failures, kind, path, exc):
    if failures is not None:
        item = {"kind": kind, "path": str(path), "error": (type(exc).__name__ + ":" + str(exc))[:256]}
        if item not in failures: failures.append(item)


def _io_account():
    return {"file_hash_attempts": 0, "file_hash_completed": 0, "file_hash_failed": 0,
        "physical_hash_bytes": 0, "unknown_hash_attempts": 0, "phases": {},
        "meaning": "physical_file_hash_IO_separate_from_canonical_stream_work_and_core_music"}


def _file_observe(path, io, phase):
    phase_row = io["phases"].setdefault(phase, {"attempts": 0, "completed": 0, "failed": 0, "bytes": 0})
    io["file_hash_attempts"] += 1
    phase_row["attempts"] += 1
    result = hashlib.sha256()
    complete = False
    try:
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            raise OSError("registered_regular_nonsymlink_file_required")
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1048576)
                if not chunk:
                    break
                io["physical_hash_bytes"] += len(chunk)
                phase_row["bytes"] += len(chunk)
                result.update(chunk)
        complete = True
        io["file_hash_completed"] += 1
        phase_row["completed"] += 1
        return result.hexdigest()
    finally:
        if not complete:
            io["file_hash_failed"] += 1
            io["unknown_hash_attempts"] += 1
            phase_row["failed"] += 1
        path = result = phase_row = chunk = handle = io = None


def _guard_full(record, failures=None, io=None, phase="registered_full"):
    io = _io_account() if io is None else io
    changed = []
    for path, expected in record["protected_sha256"].items():
        try:
            if _file_observe(path, io, phase) != expected:
                changed.append(path)
        except BaseException as exc:
            changed.append(path)
            _observation_failure(failures, "registered_SHA", path, exc)
    for root in record["protected_roots"]:
        directory = Path(root["directory"])
        try:
            if directory.is_symlink() or not directory.is_dir():
                raise OSError("registered_inventory_root_required")
            expected, actual = set(root["registered_sha256"]), set()
            # Stop at the first foreign path; never allocate an unbounded glob.
            for path in directory.rglob("*"):
                if path.is_symlink():
                    raise OSError("registered_root_symlink_changed")
                if path.is_file():
                    name = str(path.resolve())
                    if name not in expected or len(actual) >= len(expected):
                        raise OSError("registered_root_foreign_file")
                    actual.add(name)
            if actual != expected:
                changed.append(root["directory"])
        except BaseException as exc:
            changed.append(root["directory"])
            _observation_failure(failures, "registered_inventory", directory, exc)
    return sorted(set(changed))


def _registration(protected_sha256, protected_roots, source_archive_roots, io):
    protected_sha256 = {} if protected_sha256 is None else protected_sha256
    if type(protected_sha256) is not dict or type(protected_roots) is not tuple or type(source_archive_roots) is not tuple:
        raise ValueError("exact_registered_SHA_map_and_root_tuples_required")
    hashes = {}
    for name, sha in protected_sha256.items():
        read_budget._path(name)
        _hex(sha)
        hashes[name] = sha
    roots = []
    for item in protected_roots:
        if type(item) is not read_budget.InventoryRoot or type(item.registered_sha256) is not dict:
            raise ValueError("expected_registered_InventoryRoot_required_not_current_glob")
        directory = read_budget._path(item.directory)
        subset = {}
        for name, sha in item.registered_sha256.items():
            path = read_budget._path(name)
            if not read_budget._inside(path, directory) or hashes.get(name) != sha:
                raise ValueError("root_membership_must_match_registered_SHA_snapshot")
            subset[name] = sha
        roots.append({"directory": str(directory), "registered_sha256": subset})
    if len({r["directory"] for r in roots}) != len(roots):
        raise ValueError("duplicate_registered_inventory_root")
    archives = sorted({str(read_budget._path(name)) for name in source_archive_roots}
        | {r["directory"] for r in roots})
    # Current computation protection is explicitly distinct from historical
    # creation-code inventories. Include every directly reused helper module.
    code = sorted({str(Path(module.__file__).resolve()) for module in
        (core, codec, file_helpers, read_budget, observations, core.legacy, core.kernels, core.native, core.roles, core.temporal, shared, dag, streaming, transfer_bounds)}
        | {str(Path(__file__).resolve())})
    for name in code:
        sha = _file_observe(name, io, "planning_current_code")
        if name in hashes and hashes[name] != sha:
            raise ValueError("current_dependency_code_SHA_mismatch")
        hashes[name] = sha
    return hashes, roots, archives, code


def _metadata_snapshot(value, byte_cap, work_cap):
    proof = None
    try:
        proof = dag.freeze_json(value, limits=dag.DagLimits(max_input_visits=work_cap,
            max_work_units=work_cap, max_expanded_bytes=byte_cap, max_encoded_bytes=byte_cap * 4 + 1024))
        stats = proof.stats()
        total = stats["charged_work_units"] + stats["expanded_bytes"] + stats["expanded_visits"]
        if total > work_cap:
            raise streaming.StreamHold("whole_metadata_snapshot_and_decode_work_hold_no_prefix",
                {"inspection_work_lower_bound": total, "max_work": work_cap})
        return dag.proof_value_at(proof), total
    finally:
        proof = value = None


def _plan_saved_run(groups, *, original_denominators, protected_sha256=None,
        protected_roots=(), source_archive_roots=(), limits=None, compressed=False,
        task_encoded_caps=None):
    """Whole submitted owned set; schema-derived output before comparison/write.

    Version 0.2 is uncompressed only. Storage planning work and canonical output
    serialization/hash bounds are explicit, distinct from core work and file IO.
    Matching JSON records cannot issue a source/group/storage capability.
    """
    limits = StorageLimits() if limits is None else limits
    if type(limits) is not StorageLimits or type(groups) is not list or type(compressed) is not bool:
        raise ValueError("closed_proof_storage_plan_inputs_required")
    if compressed:
        raise ValueError("compressed_streaming_unsupported_in_version_0_2")
    items = tuple(groups)  # stable handle inventory; caller list is no longer used
    for item in items:
        if type(item) is not GroupInput or type(item.source) is not shared.PreparedSource or type(item.prepared) is not core.CompactPreparedGroup:
            raise ValueError("all_submitted_groups_require_owned_admissible_v2_handles_no_held_prefix")
        state = core._issued(item.prepared)
        if state.source is not item.source or state.plan.reasons or state.plan.stage != "complete":
            raise ValueError("group_requires_same_owned_source_and_complete_v2_preflight")
    owned_metadata, metadata_work = _metadata_snapshot(
        [original_denominators, [item.original for item in items]], limits.max_plan_bytes,
        limits.max_planning_work_per_group)
    denominators, originals = owned_metadata
    if type(denominators) is not dict:
        raise ValueError("plain_original_denominators_required")
    io = _io_account()
    hashes, roots, archives, code = _registration(protected_sha256, protected_roots, source_archive_roots, io)
    declarations, task_count = [], 0
    source_handles, source_positions, source_refs, source_identity, identity_handles = [], {}, {}, {}, {}
    for item, supplied in zip(items, originals):
        original, count = file_helpers._original(supplied)
        source, prepared = item.source, item.prepared
        group = core._issued(prepared).catalog["group"]
        cp = prepared.preflight_plan
        if (cp.entry_count != original["planned_entries"] or cp.block_size != original["block_size"]
                or group["original_selector_indices"] != tuple(original["selector_indices"])
                or any(group[name] != original[name] for name in
                    ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref"))):
            raise ValueError("group_disagrees_with_original_declared_membership")
        ref = source.source_ref
        identity, checksum = original["source_identity_sha256"], ref["record_sha256"]
        if checksum in source_refs and source_refs[checksum] is not source:
            raise ValueError("same_source_reference_requires_same_owned_handle")
        source_refs[checksum] = source
        if identity in identity_handles and identity_handles[identity] is not source:
            raise ValueError("same_declared_source_identity_requires_same_owned_source_handle")
        identity_handles[identity] = source
        if source not in source_positions:
            source_positions[source] = len(source_handles)
            source_handles.append(source)
        si = source_positions[source]
        if si in source_identity and source_identity[si] != identity:
            raise ValueError("same_owned_source_requires_same_declared_source_identity")
        source_identity[si] = identity
        declarations.append((original, count, source, prepared, si))
        task_count += count
    identities = [(o["scope_ref"], o["lattice_ref"], o["completion_request_ref"], o["key_ref"], o["bundle_ref"])
        for o, *_ in declarations]
    if len({_sha(_raw(value)) for value in identities}) != len(identities):
        raise ValueError("duplicate_declared_original_group")
    reasons = []
    if (len(items) > limits.max_groups or task_count > limits.max_tasks or len(source_handles) > limits.max_sources
            or len(hashes) > limits.max_protected_files or len(roots) > limits.max_inventory_roots):
        reasons.append("whole_group_source_task_or_guard_count_exceeds_limit_no_prefix")
    caps = {} if task_encoded_caps is None else deepcopy(task_encoded_caps)
    if type(caps) is not dict:
        raise ValueError("closed_per_task_encoded_caps_required")
    for position, cap in caps.items():
        if type(position) is not tuple or len(position) != 2 or any(type(i) is not int or i < 0 for i in position):
            raise ValueError("exact_per_task_cap_position_required")
        codec._integer(cap, "task_encoded_cap")
        if cap > limits.max_block_encoded_bytes:
            raise ValueError("per_task_cap_may_only_lower_declared_limit")
    sources, source_infos = [], []
    for si, source in enumerate(source_handles):
        info = None
        row = {"source_index": si, "source_catalog_ref": source.source_ref,
            "source_identity_sha256": source_identity[si], "source_encoded_bound": None,
            "source_raw_bytes": None, "source_raw_sha256": None, "stream_planning_work": None,
            "serialization_work_upper_bound": None, "iteration_work_upper_bound": None, "raw_sha256_work_upper_bound": None}
        if not reasons:
            try:
                info = streaming.source_stream_info(source, max_work=limits.max_source_planning_work)
            except streaming.StreamHold as exc:
                reasons.append("whole_source_stream_planning_hold_no_prefix")
                row["stream_hold"] = deepcopy(exc.diagnostics)
            if info is not None:
                row.update(source_encoded_bound=info["canonical_byte_upper_bound"], source_raw_bytes=info["canonical_bytes"],
                    stream_planning_work=info["planning_work"], serialization_work_upper_bound=info["serialization_work_upper_bound"],
                    iteration_work_upper_bound=info["iteration_work_upper_bound"],
                    raw_sha256_work_upper_bound=info["raw_sha256_work_upper_bound"])
                if row["source_encoded_bound"] > limits.max_source_encoded_bytes:
                    reasons.append("whole_source_stream_bytes_exceeds_limit_no_prefix")
                if info["iteration_work_upper_bound"] > min(limits.max_source_planning_work, shared._source_issued(source).limits.max_source_work):
                    reasons.append("whole_source_stream_iteration_work_exceeds_limit_no_prefix")
        sources.append(row); source_infos.append(info)
    rows, handles, catalog_infos, proofs, used_caps = [], [], [], [], set()
    for gi, (original, count, source, prepared, si) in enumerate(declarations):
        row = {"original": original, "source_index": si, "source_catalog_ref": source.source_ref,
            "planned_nonempty_tasks": count, "declared_zero_pair_tasks": original["planned_block_tasks"] - count,
            "hold_reasons": [], "group_ref": prepared.group_ref, "catalog_ref": prepared.catalog_ref,
            "refinement_sha256": None, "entry_inventory_sha256": None, "core_preflight": prepared.preflight_plan.record(),
            "catalog_encoded_bound": None, "catalog_raw_bytes": None, "tasks": None, "task_encoded_caps": None,
            "task_stream_bounds": None, "stream_planning_work": None, "serialization_work_upper_bound": None,
            "iteration_work_upper_bound": None, "raw_sha256_work_upper_bound": None, "block_output_bytes_upper_bound": None,
            "transfer_proof_diagnostic": None, "transfer_proof_work_once": None}
        info = proof = None
        if not reasons:
            declared_work = metadata_work + 65536 + 4 * len(_raw(original))
            try:
                info = streaming.catalog_stream_info(prepared, max_work=max(0, limits.max_planning_work_per_group - declared_work))
                declared_work += info["planning_work"]
                group = core._issued(prepared).catalog["group"]
                cp = prepared.preflight_plan
                if (cp.entry_count != original["planned_entries"] or cp.block_size != original["block_size"]
                        or group["original_selector_indices"] != tuple(original["selector_indices"])
                        or any(group[name] != original[name] for name in
                            ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref"))
                        or info["source_ref"] != source.source_ref):
                    raise ValueError("group_disagrees_with_original_declared_membership")
                tasks = list(prepared.iter_blocks())
                if len(tasks) != count or sum(t.expected_pairs for t in tasks) != original["planned_pairs"]:
                    raise ValueError("exact_v2_core_task_coverage_required")
                remaining = limits.max_planning_work_per_group - declared_work
                if remaining <= 0:
                    raise streaming.StreamHold("whole_transfer_proof_preparation_work_hold", {
                        "inspection_work_lower_bound": declared_work + 1, "max_work": limits.max_planning_work_per_group})
                proof = transfer_bounds.prepare_transfer_bounds(prepared,
                    limits=transfer_bounds.BoundLimits(max_work=remaining))
                diagnostic = transfer_bounds.proof_info(proof)
                declared_work += diagnostic["preparation_work_once"]
                row.update(transfer_proof_diagnostic=diagnostic,
                    transfer_proof_work_once=diagnostic["preparation_work_once"])
                bounds, encoded_caps = [], []
                for ti, task in enumerate(tasks):
                    bound = transfer_bounds.task_stream_bound(proof, task,
                        max_work=max(0, limits.max_planning_work_per_group - declared_work),
                        max_block_bytes=limits.max_block_encoded_bytes)
                    inspection = bound["inspection_work"]
                    declared_work += inspection
                    bounds.append(bound)
                    if bound["reasons"]:
                        reasons.append("whole_task_stream_bound_hold_no_prefix")
                    cap = None if bound["raw_block_byte_upper_bound"] is None else min(
                        bound["raw_block_byte_upper_bound"], caps.get((gi, ti), limits.max_block_encoded_bytes))
                    encoded_caps.append(cap)
                    if (gi, ti) in caps:
                        used_caps.add((gi, ti))
                    if cap is not None and cap < 128:
                        reasons.append("whole_task_encoded_minimum_exceeds_cap_no_prefix")
                    if cap is not None and cap < bound["raw_block_byte_upper_bound"]:
                        reasons.append("whole_task_schema_bound_exceeds_lowered_cap_no_prefix")
                    if bound["raw_block_byte_upper_bound"] is not None and 16 * bound["raw_block_byte_upper_bound"] > limits.max_planning_work_per_group:
                        reasons.append("whole_block_storage_serialization_work_exceeds_limit_no_prefix")
                row.update(refinement_sha256=info["refinement_sha256"], entry_inventory_sha256=info["entry_inventory_sha256"],
                    catalog_encoded_bound=info["canonical_byte_upper_bound"], catalog_raw_bytes=info["canonical_bytes"],
                    tasks=[asdict(t) for t in tasks], task_encoded_caps=encoded_caps, task_stream_bounds=bounds,
                    stream_planning_work=declared_work, serialization_work_upper_bound=info["serialization_work_upper_bound"],
                    iteration_work_upper_bound=info["iteration_work_upper_bound"],
                    raw_sha256_work_upper_bound=info["raw_sha256_work_upper_bound"],
                    block_output_bytes_upper_bound=None if None in encoded_caps else sum(encoded_caps))
                if declared_work > limits.max_planning_work_per_group:
                    reasons.append("whole_group_storage_planning_work_exceeds_limit_no_prefix")
                if info["iteration_work_upper_bound"] > min(limits.max_planning_work_per_group, core._issued(prepared).limits.max_work):
                    reasons.append("whole_catalog_stream_iteration_work_exceeds_limit_no_prefix")
            except streaming.StreamHold as exc:
                reasons.append("whole_catalog_or_task_stream_planning_hold_no_prefix")
                row["stream_hold"] = deepcopy(exc.diagnostics)
            except transfer_bounds.TransferBoundHold as exc:
                reasons.append("whole_transfer_proof_preparation_hold_no_prefix")
                row["transfer_proof_hold"] = deepcopy(exc.diagnostics)
                row["transfer_proof_work_once"] = exc.diagnostics["inspection_work"]
                row["stream_planning_work"] = declared_work + exc.diagnostics["inspection_work"]
        rows.append(row); handles.append(prepared); catalog_infos.append(info); proofs.append(proof)
    if not reasons and set(caps) != used_caps:
        raise ValueError("foreign_per_task_encoded_cap")
    reservation = limits.max_plan_bytes + limits.max_manifest_bytes + sum(r["source_encoded_bound"] or 0 for r in sources) + sum(
        (r["catalog_encoded_bound"] or 0) + sum(cap or 0 for cap in r["task_encoded_caps"] or ()) for r in rows)
    reservation_complete = all(r["source_encoded_bound"] is not None for r in sources) and all(
        r["catalog_encoded_bound"] is not None and r["task_encoded_caps"] is not None
        and None not in r["task_encoded_caps"] for r in rows)
    if reservation > limits.max_output_bytes:
        reasons.append("whole_output_reservation_exceeds_limit_no_prefix")
    record = {"version": VERSION, "source_authority": AUTHORITY, "scope": "caller_declared_submitted_groups_only",
        "original_denominators": denominators, "sources": sources, "groups": rows,
        "planned_shared_sources": len(sources), "planned_submitted_groups": len(rows),
        "planned_submitted_entries": sum(o["planned_entries"] for o, *_ in declarations),
        "planned_submitted_pairs": sum(o["planned_pairs"] for o, *_ in declarations),
        "planned_submitted_nonempty_tasks": task_count,
        "planned_declared_upstream_tasks": sum(o["planned_block_tasks"] for o, *_ in declarations),
        "limits": asdict(limits), "compressed": False, "compression_supported": False,
        "protected_sha256": hashes, "protected_roots": roots, "source_archive_roots": archives,
        "current_code_paths": code, "current_code_scope": "fixed_direct_helpers_not_historical_creation_inventory",
        "guard_schedule": {"plan_begin_finish": "registered_SHA_and_expected_roots",
            "each_block": "fixed_current_code_SHA_and_owned_handle_freshness",
            "output_history": "terminal_exact_SHA_inventory_and_postterminal"},
        "output_reserved_bytes_before_pair_calculation": reservation if reservation_complete else None,
        "output_reservation_complete": reservation_complete,
        "partial_accounted_output_reservation_bytes": reservation,
        "final_manifest_reserved_bytes": limits.max_manifest_bytes, "max_destination_UTF8_bytes": _MAX_PATH_BYTES,
        "metadata_snapshot_work": metadata_work, "planning_file_hash_IO": io,
        "runtime_work_policy": "each_stream_and_whole_block_validation_serialization_separately_bounded_at_declared_1B_not_core_music_or_file_IO",
        "transfer_bound_policy": "same_owned_group_category_support_and_exact_endpoint_lcm_no_outcome_sampling",
        "reasons": sorted(set(reasons)), "selected": None, "musical_outcome": None, "flags": _flags()}
    # Exact byte-width scans do not first allocate canonical full buffers. The
    # three actual scans and ONE serialization below are separately charged;
    # 4096 covers fixed final ledger fields/numeric growth before allocation.
    record["plan_finalization_account"] = {"size_measurement_passes": 3,
        "size_measurement_work": 0, "serialization_work_upper_bound": 0,
        "charged_work_upper_bound": 0, "canonical_serialization_passes": 1}
    meter = streaming._Measure(limits.max_plan_finalization_work)
    first_size = streaming._measure_owned(record, meter)
    measurement_work = meter.work
    manifest_bound = 5 * (first_size + 4096) + task_count * 4096 + (task_count + len(rows) + len(sources) + 2) * (_MAX_PATH_BYTES + 3072) + 131072
    record["final_manifest_byte_upper_bound"] = manifest_bound
    if manifest_bound > limits.max_manifest_bytes:
        record["reasons"].append("whole_final_manifest_reserve_exceeds_limit_no_prefix")
    record["terminal_manifest_serialization_work_upper_bound"] = 16 * manifest_bound
    if 16 * manifest_bound > limits.max_plan_finalization_work:
        record["reasons"].append("whole_terminal_manifest_serialization_work_exceeds_limit_no_prefix")
    if not record["reasons"] and _guard_full(record, io=io, phase="planning_registered_full"):
        raise ValueError("registered_inputs_or_expected_inventory_changed_before_plan")
    record["status"] = "whole_proof_storage_run_hold" if record["reasons"] else "planned_proof_storage_incomplete"
    meter = streaming._Measure(max(0, limits.max_plan_finalization_work - measurement_work))
    second_size = streaming._measure_owned(record, meter)
    measurement_work += meter.work
    if second_size + 4096 > limits.max_plan_bytes:
        record["reasons"].append("whole_run_plan_bytes_exceeds_limit_no_prefix")
        record["status"] = "whole_proof_storage_run_hold"
        # These advisory task bounds are not original entries or declarations.
        # Preserve all original denominators, groups, refs and selectors while
        # avoiding an over-cap serialization just to explain a whole hold.
        for row in record["groups"]:
            row["tasks"] = row["task_encoded_caps"] = row["task_stream_bounds"] = None
        record["advisory_task_descriptors_omitted_for_whole_metadata_hold"] = True
    meter = streaming._Measure(max(0, limits.max_plan_finalization_work - measurement_work))
    final_size = streaming._measure_owned(record, meter)
    measurement_work += meter.work
    serialization_work = 4 * (final_size + 4096) + meter.visits
    total = measurement_work + serialization_work
    if final_size + 4096 > limits.max_plan_bytes or total > limits.max_plan_finalization_work:
        raise streaming.StreamHold("whole_storage_plan_finalization_hold_no_prefix", {
            "inspection_work_lower_bound": total, "plan_byte_upper_bound": final_size + 4096,
            "max_plan_bytes": limits.max_plan_bytes, "planned_submitted_groups": len(rows),
            "planned_submitted_entries": record["planned_submitted_entries"],
            "planned_submitted_pairs": record["planned_submitted_pairs"]})
    record["plan_finalization_account"].update(size_measurement_work=measurement_work,
        serialization_work_upper_bound=serialization_work, charged_work_upper_bound=total)
    encoded = _raw(record)
    if len(encoded) > limits.max_plan_bytes:
        raise ValueError("internal_exact_storage_plan_byte_bound_mismatch")
    handle = object.__new__(StoragePlan)
    state = _PlanState(encoded, tuple(handles), tuple(source_handles),
        tuple(codec._freeze(info) for info in source_infos), tuple(codec._freeze(info) for info in catalog_infos), tuple(proofs), b"")
    _PLANS[handle] = _PlanState(state.record, state.handles, state.sources,
        state.source_infos, state.catalog_infos, state.transfer_proofs, _signature(handle, state))
    return handle


def plan_saved_run(groups, *, original_denominators, protected_sha256=None,
        protected_roots=(), source_archive_roots=(), limits=None, compressed=False,
        task_encoded_caps=None):
    """Plan every submitted owned group, or hold the whole set before writing.

    A metadata snapshot resource failure raises DagHold without issuing a plan;
    later bounded stream/byte holds retain complete declarations in plan.record.
    """
    try:
        return _plan_saved_run(groups, original_denominators=original_denominators,
            protected_sha256=protected_sha256, protected_roots=protected_roots,
            source_archive_roots=source_archive_roots, limits=limits,
            compressed=compressed, task_encoded_caps=task_encoded_caps)
    except BaseException as exc:
        traceback.clear_frames(exc.__traceback__)
        raise
    finally:
        groups = original_denominators = protected_sha256 = protected_roots = source_archive_roots = task_encoded_caps = None


def _error(state, reason):
    if reason not in state["errors"]:
        state["errors"].append(reason)
    state["stopped"] = True


def _caught_error(exc):
    result = (type(exc).__name__ + ":" + str(exc))[:256]
    traceback.clear_frames(exc.__traceback__)
    return result


def _guard(state, *, full=False, phase=None):
    phase = phase or ("terminal_registered_full" if full else "per_block_current_code")
    changed = _guard_full(state["plan"], state["guard_observation_errors"], state["file_hash_IO"], phase) if full else []
    if not full:
        for path in state["plan"]["current_code_paths"]:
            try:
                if _file_observe(path, state["file_hash_IO"], phase) != state["plan"]["protected_sha256"][path]: changed.append(path)
            except BaseException as exc:
                changed.append(path)
                _observation_failure(state["guard_observation_errors"], "current_code_SHA", path, exc)
    if changed:
        state["changed_protected_paths"] = sorted(set(state["changed_protected_paths"] + changed))
        _error(state, "registered_input_or_current_code_or_expected_inventory_changed")
    if state["guard_observation_errors"]: _error(state, "guard_observation_unconfirmed")
    return not changed


def _outputs(state, phase="terminal_outputs"):
    expected = {a["artifact"]: a for a in state["attempts"] if a["owned_file"]}
    changed = []
    for name, attempt in expected.items():
        try:
            path = Path(name)
            if (path.is_symlink() or not path.is_file() or path.stat().st_size != attempt["physical_bytes"]
                    or _file_observe(name, state["file_hash_IO"], phase) != attempt["physical_sha256"]):
                changed.append(name)
        except BaseException as exc:
            changed.append(name)
            _observation_failure(state["guard_observation_errors"], "owned_output_SHA", name, exc)
    try:
        directory = state["directory"]
        if directory.is_symlink() or not directory.is_dir(): changed.append(str(directory))
        actual = set()
        for path in directory.iterdir():
            name = str(path)
            if name not in expected or path.is_symlink() or not path.is_file():
                changed.append(name)
                break  # one foreign path is sufficient, no unbounded inventory
            actual.add(name)
        changed.extend(sorted(set(expected) - actual))
    except BaseException as exc:
        changed.append(str(state["directory"]))
        _observation_failure(state["guard_observation_errors"], "owned_output_inventory", state["directory"], exc)
    if changed:
        state["changed_output_paths"] = sorted(set(state["changed_output_paths"] + changed))
        _error(state, "output_SHA_or_exact_owned_inventory_changed")
    if state["guard_observation_errors"]: _error(state, "guard_observation_unconfirmed")
    return not changed


def _attempt(state, name, chunks, kind, *, byte_bound, exact_bytes=None):
    """Exclusive chunked write; ownership begins ONLY after successful xb open.

    Byte attempts are nonrefundable before write. A failed iterator or syscall
    leaves a bounded known fragment and unknown full canonical hash, never a
    favorable prefix promoted to persistence.
    """
    path = state["directory"] / name
    attempt = {"artifact": str(path), "kind": kind, "attempted_bytes": 0,
        "attempted_sha256": None, "complete_stream_sha256": None,
        "stream_complete": False, "byte_bound": byte_bound, "exact_bytes": exact_bytes,
        "physical_bytes": 0, "physical_sha256": None, "persisted": False, "owned_file": False, "error": None}
    state["attempts"].append(attempt)
    digest = hashlib.sha256()
    iterator = file = chunk = None
    try:
        iterator = iter(chunks)
        file = path.open("xb")
        attempt["owned_file"] = True
        for chunk in iterator:
            if type(chunk) is not bytes or not chunk or len(chunk) > streaming.DEFAULT_CHUNK_BYTES:
                raise ValueError("bounded_nonempty_byte_chunks_required")
            attempt["attempted_bytes"] += len(chunk)
            state["attempted_bytes"] += len(chunk)
            state["canonical_stream_account"]["sha256_attempted_bytes"] += len(chunk)
            if (attempt["attempted_bytes"] > byte_bound or state["attempted_bytes"] >
                    state["plan"]["output_reserved_bytes_before_pair_calculation"]):
                raise ValueError("attempt_exceeded_whole_reserved_output_no_write")
            digest.update(chunk)
            if file.write(chunk) != len(chunk):
                raise OSError("exclusive_short_write")
        attempt["stream_complete"] = True
        attempt["complete_stream_sha256"] = attempt["attempted_sha256"] = digest.hexdigest()
        if exact_bytes is not None and attempt["attempted_bytes"] != exact_bytes:
            raise ValueError("owned_exact_canonical_stream_size_mismatch")
        file.flush()
        os.fsync(file.fileno())
        file.close()
        file = None
        if path.stat().st_size != attempt["attempted_bytes"] or _file_observe(
                path, state["file_hash_IO"], "exclusive_write_verification") != attempt["attempted_sha256"]:
            raise OSError("exclusive_written_bytes_or_SHA_disagrees")
        attempt["persisted"] = True
    except BaseException as exc:
        attempt["error"] = _caught_error(exc)
        _error(state, attempt["error"])
    finally:
        try:
            if file is not None:
                file.close()
        except BaseException as exc:
            _error(state, ("exclusive_close_failed:" + type(exc).__name__ + ":" + str(exc))[:256])
            attempt["persisted"] = False
        try:
            if iterator is not None and hasattr(iterator, "close"):
                iterator.close()
        except BaseException as exc:
            _error(state, ("stream_close_failed:" + type(exc).__name__ + ":" + str(exc))[:256])
            attempt["persisted"] = False
        if attempt["owned_file"]:
            try:
                attempt["physical_bytes"] = path.stat().st_size
                attempt["physical_sha256"] = _file_observe(path, state["file_hash_IO"], "owned_fragment_observation")
            except BaseException as exc:
                attempt["physical_bytes"] = attempt["physical_sha256"] = None
                attempt["persisted"] = False
                attempt["physical_observation_error"] = (type(exc).__name__ + ":" + str(exc))[:256]
                _error(state, "physical_fragment_observation_unconfirmed")
        state = path = chunks = iterator = file = chunk = digest = None
    return attempt


def _bytes_chunks(raw):
    chunk = None
    try:
        for offset in range(0, len(raw), streaming.DEFAULT_CHUNK_BYTES):
            chunk = raw[offset:offset + streaming.DEFAULT_CHUNK_BYTES]
            yield chunk
    finally:
        raw = chunk = None


def begin_storage(plan, directory):
    data, record = _plan(plan), plan.record()
    if record["reasons"]: raise WholeRunHold(plan)
    destination = Path(directory).resolve()
    if len(str(destination).encode("utf-8")) > _MAX_PATH_BYTES:
        raise ValueError("bounded_storage_destination_required")
    if any(read_budget._inside(destination, Path(root)) for root in record["source_archive_roots"]):
        raise ValueError("output_must_be_outside_registered_source_archive_roots")
    if any(destination == Path(path) or destination in Path(path).parents for path in record["protected_sha256"]):
        raise ValueError("output_must_not_contain_or_replace_registered_input")
    if destination.exists(): raise FileExistsError("exclusive_new_storage_directory_required")
    io = _io_account()
    if _guard_full(record, io=io, phase="begin_registered_full"):
        raise ValueError("registered_input_or_expected_inventory_changed_before_begin")
    destination.mkdir(parents=False, exist_ok=False)
    state = {"data": data, "plan": record, "directory": destination,
        "attempts": [], "attempted_bytes": 0, "errors": [], "stopped": False, "finished": False,
        "terminal_persisted": False, "changed_protected_paths": [], "changed_output_paths": [],
        "guard_observation_errors": [], "file_hash_IO": io,
        "canonical_stream_account": {"reserved_nonrefundable_iteration_work_units": 0,
            "reserved_nonrefundable_block_serialization_validation_work_units": 0,
            "sha256_attempted_bytes": 0, "source_iteration_attempts": 0,
            "catalog_iteration_attempts": 0, "iteration_completed": 0, "iteration_unknown": 0,
            "meaning": "bounded_upper_work_reserved_before_stream_or_block_serialization_not_elapsed_time"},
        "sources": [{"persisted": False, "encoding_attempted": False, "encoded_bytes": None,
            "encoded_sha256": None} for _ in record["sources"]], "groups": []}
    for row in record["groups"]:
        state["groups"].append({"catalog_persisted": False, "encoding_attempted": False,
            "encoded_bytes": None, "encoded_sha256": None, "next_task": 0,
            "tasks": [{"task": task, "status": "uncomputed", "computed_pairs": 0, "persisted_pairs": 0,
                "held_pairs": 0, "calculation_attempted": False, "core_result_confirmed": False,
                "unconfirmed_computation_pairs": 0, "encoded_bytes": None, "encoded_sha256": None}
                for task in row["tasks"] or ()]})
    handle = object.__new__(StorageRun)
    _STORES[handle] = _RunState(state, hmac.digest(_SECRET, _raw([id(handle), id(state)]), "sha256"))
    _attempt(state, "run-plan.json", _bytes_chunks(data.record), "run_plan",
        byte_bound=record["limits"]["max_plan_bytes"], exact_bytes=len(data.record))
    _guard(state)
    if state["stopped"]: finish(handle)
    return handle


def _ensure_catalog(state, index, *, source=False):
    records = state["sources"] if source else state["groups"]
    stored = records[index]
    handle = state["data"].sources[index] if source else state["data"].handles[index]
    expected = state["plan"]["sources" if source else "groups"][index]
    if ((source and handle.source_ref != expected["source_catalog_ref"])
            or (not source and (handle.catalog_ref != expected["catalog_ref"]
                or handle.source_ref != expected["source_catalog_ref"]
                or core._issued(handle).source is not state["data"].sources[expected["source_index"]]))):
        _error(state, "owned_source_or_group_identity_changed")
        return False
    persisted_key = "persisted" if source else "catalog_persisted"
    if stored[persisted_key]: return True
    info = state["data"].source_infos[index] if source else state["data"].catalog_infos[index]
    if info is None:
        _error(state, "whole_owned_stream_plan_required_no_unmeasured_catalog")
        return False
    stored["encoding_attempted"] = True
    account = state["canonical_stream_account"]
    account["reserved_nonrefundable_iteration_work_units"] += info["iteration_work_upper_bound"]
    account["source_iteration_attempts" if source else "catalog_iteration_attempts"] += 1
    maximum = state["plan"]["limits"]["max_source_planning_work" if source else "max_planning_work_per_group"]
    chunks = streaming.iter_source_json(handle, max_work=maximum) if source else streaming.iter_catalog_json(handle, max_work=maximum)
    kind = "source_catalog" if source else "local_catalog"
    name = f"source-{index:04d}-catalog" if source else f"group-{index:04d}-catalog"
    attempt = _attempt(state, name + ".json", chunks, kind,
        byte_bound=expected["source_encoded_bound" if source else "catalog_encoded_bound"], exact_bytes=info["canonical_bytes"])
    account["iteration_completed" if attempt["stream_complete"] else "iteration_unknown"] += 1
    stored["encoded_bytes"], stored["encoded_sha256"] = attempt["attempted_bytes"], attempt["complete_stream_sha256"]
    stored[persisted_key] = attempt["persisted"]
    return attempt["persisted"]


def _validate_block(prepared, task, block, indices):
    codec._no_float(block)
    core.kernels._check(block, core.BLOCK_PREFIX)
    if (block["version"] != core.VERSION or block["source_catalog_ref"] != prepared.source_ref
            or block["catalog_ref"] != prepared.catalog_ref or block["group_ref"] != prepared.group_ref
            or block["task"] != asdict(task) or block["refinement_sha256"] != task.refinement_sha256
            or block["entry_inventory_sha256"] != task.entry_inventory_sha256
            or type(block["planned_pairs"]) is not int or block["planned_pairs"] != task.expected_pairs
            or block["whole_group_complete"] is not False or block["flags"] != core.legacy._flags()
            or any(v is not False for v in block["flags"].values())
            or any(block[k] is not None for k in ("selected", "rank", "confidence", "musical_outcome"))):
        raise ValueError("exact_unpromoted_shared_block_metadata_required")
    held = block["status"] == "whole_saved_block_hold"
    if (type(block["computed_pairs"]) is not int or type(block["withheld_pairs"]) is not int
            or block["computed_pairs"] + block["withheld_pairs"] != task.expected_pairs
            or (held and (block["pairs"] or block["computed_pairs"] != 0 or not block["reasons"]))
            or (not held and (block["status"] != "computed_saved_block_not_selected" or block["reasons"]
                or block["withheld_pairs"] != 0 or len(block["pairs"]) != task.expected_pairs))):
        raise ValueError("whole_shared_block_or_exact_pair_coverage_required")
    for pair, (i, j) in zip(block["pairs"], task.pair_indices()):
        core.kernels._check(pair, core.PAIR_PREFIX)
        if (pair["version"] != core.VERSION or pair["codec"] != core.ENCODING
                or pair["status"] != "computed_saved_pair_contrast_not_selected"
                or type(pair["entry_indices"]) is not list or len(pair["entry_indices"]) != 2
                or any(type(v) is not int for v in pair["entry_indices"])
                or type(pair["original_selector_indices"]) is not list or len(pair["original_selector_indices"]) != 2
                or any(type(v) is not int for v in pair["original_selector_indices"])
                or pair["entry_indices"] != [i, j] or pair["original_selector_indices"] != [indices[i], indices[j]]
                or pair["source_catalog_ref"] != prepared.source_ref or pair["catalog_ref"] != prepared.catalog_ref
                or pair["group_ref"] != prepared.group_ref or pair["refinement_sha256"] != task.refinement_sha256
                or any(pair[k] is not None for k in ("selected", "rank", "confidence", "musical_outcome"))):
            raise ValueError("exact_ordered_shared_pair_coverage_required")


def _perform_block(run, group_index, task):
    state = _store(run)
    codec._integer(group_index, "group_index")
    if state["finished"] or state["stopped"]: raise ValueError("storage_run_terminal_or_interrupted")
    if group_index >= len(state["groups"]): raise ValueError("foreign_submitted_group_index")
    gp, stored = state["plan"]["groups"][group_index], state["groups"][group_index]
    prepared, ti = state["data"].handles[group_index], stored["next_task"]
    if (prepared is None or type(task) is not core.BlockTask or ti >= len(stored["tasks"])
            or any(type(getattr(task, name)) is not int for name in
                ("row_start", "row_end", "column_start", "column_end", "expected_pairs"))
            or any(type(getattr(task, name)) is not str for name in
                ("source_sha256", "group_sha256", "refinement_sha256", "entry_inventory_sha256"))
            or asdict(task) != gp["tasks"][ti]):
        raise ValueError("exact_next_task_required_no_duplicate_missing_reorder_or_foreign")
    if not _guard(state):
        finish(run); return
    if not _ensure_catalog(state, gp["source_index"], source=True) or not _ensure_catalog(state, group_index):
        if state["stopped"]: finish(run)
        return
    row = stored["tasks"][ti]
    block = encoded = None
    try:
        proof = state["data"].transfer_proofs[group_index]
        if proof is None or transfer_bounds._issued(proof).prepared is not prepared:
            raise ValueError("same_owned_transfer_proof_required_before_pair_calculation")
        serialization_bound = 16 * gp["task_stream_bounds"][ti]["raw_block_byte_upper_bound"]
        state["canonical_stream_account"]["reserved_nonrefundable_block_serialization_validation_work_units"] += serialization_bound
        row["storage_serialization_validation_work_upper_bound_reserved"] = serialization_bound
        row["calculation_attempted"] = True
        block = core.compare_block(prepared, task)
        _validate_block(prepared, task, block, gp["original"]["selector_indices"])
        row["core_result_confirmed"] = True
        row.update(computed_pairs=block["computed_pairs"], held_pairs=block["withheld_pairs"])
        encoded = _raw(block)
        row.update(encoded_bytes=len(encoded), encoded_sha256=_sha(encoded))
        if len(encoded) > gp["task_encoded_caps"][ti]:
            row["status"] = "whole_block_storage_bytes_hold_no_prefix"
            row["held_pairs"] = task.expected_pairs - row["computed_pairs"]
        else:
            attempt = _attempt(state, f"group-{group_index:04d}-block-{ti:06d}.json", _bytes_chunks(encoded), "block",
                byte_bound=gp["task_encoded_caps"][ti], exact_bytes=len(encoded))
            row["status"] = "held" if block["withheld_pairs"] else "computed_unpersisted"
            if attempt["persisted"]:
                row["persisted_pairs"] = row["computed_pairs"]
                row["status"] = "held" if block["withheld_pairs"] else "computed_persisted"
        stored["next_task"] += 1
    except BaseException as exc:
        row["unconfirmed_computation_pairs"] = task.expected_pairs if row["calculation_attempted"] and not row["core_result_confirmed"] else 0
        row["status"] = "interrupted_before_comparison" if not row["calculation_attempted"] else "interrupted_computed_unpersisted" if row["core_result_confirmed"] else "interrupted_unconfirmed_computation"
        _error(state, _caught_error(exc))
    finally:
        block = encoded = proof = None
    _guard(state)
    if state["stopped"]: finish(run)


def write_block(run, group_index, task):
    """Write one exact next task and return a copied provisional ledger."""
    _perform_block(run, group_index, task)
    return ledger(run)


def write_prepared_group(run, group_index):
    state = _store(run)
    codec._integer(group_index, "group_index")
    if group_index >= len(state["groups"]): raise ValueError("foreign_submitted_group_index")
    if state["stopped"] or state["finished"]: raise ValueError("storage_run_terminal_or_interrupted")
    if state["data"].handles[group_index] is None: return ledger(run)
    gp = state["plan"]["groups"][group_index]
    if (_guard(state) and _ensure_catalog(state, gp["source_index"], source=True)
            and _ensure_catalog(state, group_index)):
        stored = state["groups"][group_index]
        while stored["next_task"] < len(stored["tasks"]):
            _perform_block(run, group_index, core.BlockTask(**gp["tasks"][stored["next_task"]]))
            if state["stopped"]: break
    if state["stopped"] and not state["finished"]: finish(run)
    return ledger(run)


def ledger(run):
    state = _store(run)
    if state["finished"]:
        _guard(state, full=True, phase="postterminal_registered_full"); _outputs(state, "postterminal_outputs")
    totals = {name: 0 for name in ("planned_pairs", "computed_pairs", "persisted_pairs", "held_pairs",
        "storage_held_pairs", "unconfirmed_computation_pairs", "uncomputed_pairs", "unpersisted_pairs", "computed_unpersisted_pairs")}
    groups = []
    for gp, stored in zip(state["plan"]["groups"], state["groups"]):
        planned = gp["original"]["planned_pairs"]
        computed = sum(t["computed_pairs"] for t in stored["tasks"])
        persisted = sum(t["persisted_pairs"] for t in stored["tasks"])
        held = planned if gp["hold_reasons"] else sum(t["held_pairs"] for t in stored["tasks"])
        counts = {"planned_pairs": planned, "computed_pairs": computed, "persisted_pairs": persisted,
            "held_pairs": held, "storage_held_pairs": sum(t["task"]["expected_pairs"] for t in stored["tasks"]
                if t["status"] == "whole_block_storage_bytes_hold_no_prefix"),
            "unconfirmed_computation_pairs": sum(t["unconfirmed_computation_pairs"] for t in stored["tasks"]),
            "uncomputed_pairs": planned - computed - held, "unpersisted_pairs": planned - persisted,
            "computed_unpersisted_pairs": computed - persisted}
        for name, value in counts.items(): totals[name] += value
        groups.append({**deepcopy(gp), **counts, "catalog_persisted": stored["catalog_persisted"],
            "catalog_encoding_attempted": stored["encoding_attempted"], "catalog_encoded_bytes": stored["encoded_bytes"],
            "catalog_encoded_sha256": stored["encoded_sha256"], "task_ledger": deepcopy(stored["tasks"]),
            "uncomputed_task_ranges": [deepcopy(t["task"]) for t in stored["tasks"] if t["status"] in ("uncomputed", "interrupted_unconfirmed_computation", "interrupted_before_comparison")],
            "unpersisted_task_ranges": [deepcopy(t["task"]) for t in stored["tasks"] if t["persisted_pairs"] != t["task"]["expected_pairs"]]})
    all_computed = totals["computed_pairs"] == totals["planned_pairs"] and all(not g["hold_reasons"] for g in groups)
    ready = (all_computed and totals["persisted_pairs"] == totals["planned_pairs"]
        and all(g["catalog_persisted"] for g in groups) and all(s["persisted"] for s in state["sources"])
        and not state["stopped"])
    complete = ready and state["terminal_persisted"]
    return {"version": VERSION, "source_authority": AUTHORITY, "scope": "caller_declared_submitted_groups_only",
        "original_denominators": deepcopy(state["plan"]["original_denominators"]),
        "planned_shared_sources": len(state["sources"]), "persisted_shared_sources": sum(s["persisted"] for s in state["sources"]),
        "sources": [{**deepcopy(p), **deepcopy(s)} for p, s in zip(state["plan"]["sources"], state["sources"])],
        **{name: state["plan"][name] for name in ("planned_submitted_groups", "planned_submitted_entries",
            "planned_submitted_nonempty_tasks", "planned_declared_upstream_tasks")},
        "groups": groups, "summary": totals, "all_planned_pairs_computed": all_computed,
        "submitted_group_set_complete": complete, "storage_integrity_passed": not state["errors"],
        "physical_closure_verified_terminally": state["finished"] and not state["errors"],
        "persisted_counts_are_provisional_until_terminal_closure": not state["finished"],
        "status": "saved_submitted_group_set_complete" if complete else "interrupted_shared_storage" if state["stopped"] else "incomplete_or_held_shared_storage",
        "output_reserved_bytes_before_pair_calculation": state["plan"]["output_reserved_bytes_before_pair_calculation"],
        "attempted_output_bytes": state["attempted_bytes"],
        "physical_output_bytes": sum(a["physical_bytes"] for a in state["attempts"] if a["physical_bytes"] is not None),
        "unknown_physical_output_attempts": sum(a["physical_bytes"] is None for a in state["attempts"]),
        "artifact_attempts": deepcopy(state["attempts"]), "errors": list(state["errors"]),
        "file_hash_IO": deepcopy(state["file_hash_IO"]),
        "canonical_stream_account": deepcopy(state["canonical_stream_account"]),
        "changed_protected_paths": list(state["changed_protected_paths"]), "changed_output_paths": list(state["changed_output_paths"]),
        "guard_observation_errors": deepcopy(state["guard_observation_errors"]),
        "unconfirmed_guard_observations": len(state["guard_observation_errors"]),
        "terminal_persisted": state["terminal_persisted"], "selected": None, "rank": None, "confidence": None,
        "musical_outcome": None, "flags": _flags()}


def finish(run):
    state = _store(run)
    if state["finished"]: return ledger(run)
    _guard(state, full=True, phase="preterminal_registered_full"); _outputs(state, "preterminal_outputs")
    report = encoded = None
    try:
        state["canonical_stream_account"].setdefault("terminal_manifest_serialization_attempts", 0)
        state["canonical_stream_account"]["terminal_manifest_serialization_attempts"] += 1
        state["canonical_stream_account"]["reserved_nonrefundable_terminal_manifest_work_units"] = state["plan"]["terminal_manifest_serialization_work_upper_bound"]
        report = ledger(run)
        report["terminal_commit_contract"] = "manifest_cannot_self_certify_its_own_write_verify_owned_terminal_result"
        encoded = _raw(report)
        if len(encoded) > state["plan"]["final_manifest_reserved_bytes"]:
            _error(state, "final_manifest_exceeded_reserved_bytes")
        else:
            attempt = _attempt(state, "report.json", _bytes_chunks(encoded), "final_manifest",
                byte_bound=state["plan"]["final_manifest_reserved_bytes"], exact_bytes=len(encoded))
            state["terminal_persisted"] = attempt["persisted"]
    except BaseException as exc:
        _error(state, "terminal_manifest_unconfirmed:" + _caught_error(exc))
    finally:
        report = encoded = None
    _guard(state, full=True, phase="terminal_registered_full"); _outputs(state, "terminal_outputs")
    state["finished"] = True
    return ledger(run)
