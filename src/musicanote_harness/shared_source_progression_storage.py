"""Exclusive source-once storage for caller-declared shared contrast groups.

Source/local/block codecs are distinct from frozen predecessor storage. The
writer never issues/forges a contrast handle, authenticates an original archive
request, selects harmony, or treats saved JSON as a reload capability. Source
catalogs are serialized once per SAME owned source handle. Per-block fast guards
are provisional; exact registered SHA/root/output closure is required terminally.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import gzip
import hmac
import json
from pathlib import Path
import secrets
from weakref import WeakKeyDictionary

from . import shared_source_progression_contrast as core
from . import cross_batch_progression_contrast as codec
from . import cross_batch_progression_storage as file_helpers
from . import cross_batch_read_budget as read_budget
from . import musical_pattern_observation as observations

VERSION = "shared-source-progression-storage-0.1.0"
AUTHORITY = "shared_source_submitted_group_storage_not_original_archive_admission"
_PLANS, _STORES = WeakKeyDictionary(), WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)
_MAX_PATH_BYTES = 1024
_raw, _sha, _hex = file_helpers._raw, file_helpers._sha, file_helpers._hex
_file_sha, _write_payload = file_helpers._file_sha, file_helpers._write_payload
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

    def __post_init__(self):
        for name, value in asdict(self).items():
            codec._integer(value, name)


@dataclass(frozen=True, slots=True)
class GroupInput:
    original: dict
    source: core.PreparedSource
    prepared: core.SharedPreparedGroup | None = None
    hold_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _PlanState:
    record: bytes
    handles: tuple
    sources: tuple
    source_raw: tuple
    catalog_raw: tuple
    signature: bytes


def _signature(handle, state):
    # Bytes/tuples are immutable. This authenticates object ownership, not a
    # user-provided seal and not an expensive full-source hash per block.
    return hmac.digest(_SECRET, _raw([id(handle), id(state.record), id(state.handles),
        id(state.sources), id(state.source_raw), id(state.catalog_raw)]), "sha256")


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
            or any(type(value) is not tuple for value in (state.handles, state.sources, state.source_raw, state.catalog_raw))
            or not hmac.compare_digest(state.signature, _signature(handle, state))):
        raise ValueError("owned_shared_storage_plan_state_changed")
    return state


def _store(handle):
    if type(handle) is not StorageRun or handle not in _STORES:
        raise ValueError("owned_shared_storage_run_required_not_JSON")
    return _STORES[handle]


class WholeRunHold(ValueError):
    def __init__(self, plan):
        self.plan = plan.record()
        super().__init__("whole_shared_storage_run_hold:" + ",".join(self.plan["reasons"]))


def _observation_failure(failures, kind, path, exc):
    if failures is not None:
        item = {"kind": kind, "path": str(path), "error": (type(exc).__name__ + ":" + str(exc))[:256]}
        if item not in failures: failures.append(item)


def _guard_full(record, failures=None):
    changed = []
    for path, expected in record["protected_sha256"].items():
        try:
            if _file_sha(path) != expected:
                changed.append(path)
        except BaseException as exc:
            changed.append(path)
            _observation_failure(failures, "registered_SHA", path, exc)
    for root in record["protected_roots"]:
        directory = Path(root["directory"])
        try:
            descendants = list(directory.rglob("*"))
            if (directory.is_symlink() or not directory.is_dir() or any(p.is_symlink() for p in descendants)
                    or sorted(str(p.resolve()) for p in descendants if p.is_file()) != sorted(root["registered_sha256"])):
                changed.append(root["directory"])
        except BaseException as exc:
            changed.append(root["directory"])
            _observation_failure(failures, "registered_inventory", directory, exc)
    return sorted(set(changed))


def _registration(protected_sha256, protected_roots, source_archive_roots):
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
        (core, codec, file_helpers, read_budget, observations, core.legacy, core.kernels, core.native)}
        | {str(Path(__file__).resolve())})
    for name in code:
        sha = _file_sha(name)
        if name in hashes and hashes[name] != sha:
            raise ValueError("current_dependency_code_SHA_mismatch")
        hashes[name] = sha
    return hashes, roots, archives, code


def plan_saved_run(groups, *, original_denominators, protected_sha256=None,
        protected_roots=(), source_archive_roots=(), limits=None, compressed=False,
        task_encoded_caps=None):
    """Reserve all submitted sources/local catalogs/blocks/terminal metadata.

    Root inventories are supplied EXPECTED SHA snapshots, never today's glob.
    Unknown held-group costs remain null. A caller-declared held group may be
    reported but cannot be converted into an empty successful group.
    """
    limits = StorageLimits() if limits is None else limits
    if type(limits) is not StorageLimits or type(groups) is not list or type(compressed) is not bool:
        raise ValueError("closed_shared_storage_plan_inputs_required")
    read_budget._plain(original_denominators)
    if type(original_denominators) is not dict:
        raise ValueError("plain_original_denominators_required")
    hashes, roots, archives, code = _registration(protected_sha256, protected_roots, source_archive_roots)
    declarations, task_count = [], 0
    source_handles, source_positions, source_ref_handles, source_identity, identity_handles = [], {}, {}, {}, {}
    for item in groups:
        if type(item) is not GroupInput:
            raise ValueError("exact_shared_group_input_required")
        original, count = file_helpers._original(item.original)
        if (type(item.hold_reasons) is not tuple or any(type(r) is not str or not r or len(r) > 256 for r in item.hold_reasons)
                or (item.prepared is None) != bool(item.hold_reasons)):
            raise ValueError("explicit_whole_group_hold_or_issued_handle_required")
        # Owned source capability must be shared physically, not a resealed
        # equal catalog and not a second factory instance with identical bytes.
        source_ref = item.source.source_ref if type(item.source) is core.PreparedSource else None
        if source_ref is None:
            raise ValueError("issued_shared_source_required")
        key = source_ref["record_sha256"]
        if key in source_ref_handles and source_ref_handles[key] is not item.source:
            raise ValueError("same_source_reference_requires_same_owned_handle")
        source_ref_handles[key] = item.source
        identity = original["source_identity_sha256"]
        if identity in identity_handles and identity_handles[identity] is not item.source:
            raise ValueError("same_declared_source_identity_requires_same_owned_source_handle")
        identity_handles[identity] = item.source
        if item.source not in source_positions:
            source_positions[item.source] = len(source_handles)
            source_handles.append(item.source)
        si = source_positions[item.source]
        if si in source_identity and source_identity[si] != original["source_identity_sha256"]:
            raise ValueError("same_owned_source_requires_same_declared_source_identity")
        source_identity[si] = original["source_identity_sha256"]
        declarations.append((original, count, item.source, item.prepared, item.hold_reasons, si))
        task_count += count
    identities = [(o["scope_ref"], o["lattice_ref"], o["completion_request_ref"], o["key_ref"], o["bundle_ref"])
        for o, *_ in declarations]
    if len({_sha(_raw(value)) for value in identities}) != len(identities):
        raise ValueError("duplicate_declared_original_group")
    reasons = []
    if (len(groups) > limits.max_groups or task_count > limits.max_tasks or len(source_handles) > limits.max_sources
            or len(hashes) > limits.max_protected_files or len(roots) > limits.max_inventory_roots):
        reasons.append("whole_group_source_task_or_guard_count_exceeds_limit_no_prefix")
    caps = {} if task_encoded_caps is None else task_encoded_caps
    if type(caps) is not dict:
        raise ValueError("closed_per_task_encoded_caps_required")
    for position, cap in caps.items():
        if type(position) is not tuple or len(position) != 2 or any(type(i) is not int or i < 0 for i in position):
            raise ValueError("exact_per_task_cap_position_required")
        codec._integer(cap, "task_encoded_cap")
        if cap > limits.max_block_encoded_bytes:
            raise ValueError("per_task_cap_may_only_lower_declared_limit")
    sources, source_raw = [], []
    for si, source in enumerate(source_handles):
        raw = None
        row = {"source_index": si, "source_catalog_ref": source.source_ref,
            "source_identity_sha256": source_identity[si], "source_encoded_bound": None,
            "source_raw_bytes": None, "source_raw_sha256": None}
        if not reasons:
            raw = _raw(source.export_source())
            bound = len(raw) * 2 + 1024 if compressed else len(raw)
            row.update(source_encoded_bound=bound, source_raw_bytes=len(raw), source_raw_sha256=_sha(raw))
            if bound > limits.max_source_encoded_bytes:
                reasons.append("whole_shared_source_encoded_bound_exceeds_limit_no_prefix")
        sources.append(row)
        source_raw.append(raw)
    rows, handles, catalogs, used_caps = [], [], [], set()
    # Count gates precede full source/local export and task materialization.
    for gi, (original, count, source, prepared, held, si) in enumerate(declarations):
        row = {"original": original, "source_index": si, "source_catalog_ref": source.source_ref,
            "planned_nonempty_tasks": count, "declared_zero_pair_tasks": original["planned_block_tasks"] - count,
            "hold_reasons": list(held), "group_ref": None, "catalog_ref": None,
            "refinement_sha256": None, "entry_inventory_sha256": None, "core_preflight": None,
            "catalog_encoded_bound": None, "tasks": None, "task_encoded_caps": None}
        raw = None
        if not reasons and prepared is not None:
            if type(prepared) is not core.SharedPreparedGroup or core._issued(prepared).source is not source:
                raise ValueError("group_requires_same_owned_shared_source")
            catalog = prepared.export_catalog()
            group, cp = catalog["group"], prepared.preflight_plan
            if (cp.entry_count != original["planned_entries"] or cp.block_size != original["block_size"]
                    or group["original_selector_indices"] != original["selector_indices"]
                    or any(group[name] != original[name] for name in
                        ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref"))
                    or catalog["source_catalog_ref"] != source.source_ref):
                raise ValueError("group_disagrees_with_original_declared_membership")
            tasks = [asdict(task) for task in prepared.iter_blocks()]
            if len(tasks) != count or sum(t["expected_pairs"] for t in tasks) != original["planned_pairs"]:
                raise ValueError("exact_shared_core_task_coverage_required")
            encoded_caps = []
            for ti in range(count):
                cap = caps.get((gi, ti), limits.max_block_encoded_bytes)
                encoded_caps.append(cap)
                if (gi, ti) in caps: used_caps.add((gi, ti))
                if cap < (18 if compressed else 128):
                    reasons.append("whole_task_encoded_minimum_exceeds_cap_no_prefix")
            raw = _raw(catalog)
            row.update(group_ref=prepared.group_ref, catalog_ref=prepared.catalog_ref,
                refinement_sha256=catalog["refinement_sha256"], entry_inventory_sha256=catalog["entry_inventory_sha256"],
                core_preflight=cp.record(), catalog_encoded_bound=2 * len(raw) + 1024 if compressed else len(raw),
                tasks=tasks, task_encoded_caps=encoded_caps)
        rows.append(row); handles.append(prepared); catalogs.append(raw)
    if not reasons and set(caps) != used_caps:
        raise ValueError("foreign_per_task_encoded_cap")
    reservation = limits.max_plan_bytes + limits.max_manifest_bytes \
        + sum(row["source_encoded_bound"] or 0 for row in sources) \
        + sum((r["catalog_encoded_bound"] or 0) + sum(r["task_encoded_caps"] or ()) for r in rows)
    if reservation > limits.max_output_bytes:
        reasons.append("whole_output_reservation_exceeds_limit_no_prefix")
    record = {"version": VERSION, "source_authority": AUTHORITY, "scope": "caller_declared_submitted_groups_only",
        "original_denominators": deepcopy(original_denominators), "sources": sources, "groups": rows,
        "planned_shared_sources": len(sources), "planned_submitted_groups": len(rows),
        "planned_submitted_entries": sum(o["planned_entries"] for o, *_ in declarations),
        "planned_submitted_pairs": sum(o["planned_pairs"] for o, *_ in declarations),
        "planned_submitted_nonempty_tasks": task_count,
        "planned_declared_upstream_tasks": sum(o["planned_block_tasks"] for o, *_ in declarations),
        "limits": asdict(limits), "compressed": compressed, "protected_sha256": hashes,
        "protected_roots": roots, "source_archive_roots": archives, "current_code_paths": code,
        "current_code_scope": "fixed_direct_helpers_not_full_dependency_or_historical_creation_inventory",
        "guard_schedule": {"plan_begin_finish": "all_registered_SHA_and_exact_expected_roots",
            "each_block": "fixed_current_code_SHA_owned_source_group_freshness_and_new_artifact_SHA",
            "other_registered_input_mutation_detection": "terminal_full_SHA_and_expected_inventory_before_complete",
            "output_history": "SHA_and_exact_inventory_terminal_and_post_terminal"},
        "output_reserved_bytes_before_pair_calculation": reservation,
        "final_manifest_reserved_bytes": limits.max_manifest_bytes,
        "max_destination_UTF8_bytes": _MAX_PATH_BYTES,
        "reasons": sorted(set(reasons)), "selected": None, "musical_outcome": None, "flags": _flags()}
    bound = 4 * len(_raw(record)) + task_count * 4096 \
        + (task_count + len(rows) + len(sources) + 2) * (_MAX_PATH_BYTES + 2048) + 65536
    record["final_manifest_byte_upper_bound"] = bound
    if bound > limits.max_manifest_bytes:
        record["reasons"].append("whole_final_manifest_reserve_exceeds_limit_no_prefix")
    if not record["reasons"] and _guard_full(record):
        raise ValueError("registered_inputs_or_expected_inventory_changed_before_plan")
    record["status"] = "whole_shared_storage_run_hold" if record["reasons"] else "planned_shared_storage_incomplete"
    encoded = _raw(record)
    if len(encoded) > limits.max_plan_bytes:
        record["reasons"].append("whole_run_plan_bytes_exceeds_limit_no_prefix")
        record["status"] = "whole_shared_storage_run_hold"
        encoded = _raw(record)
    handle = object.__new__(StoragePlan)
    state = _PlanState(encoded, tuple(handles), tuple(source_handles), tuple(source_raw), tuple(catalogs), b"")
    _PLANS[handle] = _PlanState(state.record, state.handles, state.sources, state.source_raw,
        state.catalog_raw, _signature(handle, state))
    return handle


def _error(state, reason):
    if reason not in state["errors"]:
        state["errors"].append(reason)
    state["stopped"] = True


def _guard(state, *, full=False):
    changed = _guard_full(state["plan"], state["guard_observation_errors"]) if full else []
    if not full:
        for path in state["plan"]["current_code_paths"]:
            try:
                if _file_sha(path) != state["plan"]["protected_sha256"][path]: changed.append(path)
            except BaseException as exc:
                changed.append(path)
                _observation_failure(state["guard_observation_errors"], "current_code_SHA", path, exc)
    if changed:
        state["changed_protected_paths"] = sorted(set(state["changed_protected_paths"] + changed))
        _error(state, "registered_input_or_current_code_or_expected_inventory_changed")
    if state["guard_observation_errors"]: _error(state, "guard_observation_unconfirmed")
    return not changed


def _outputs(state):
    expected = {a["artifact"]: a for a in state["attempts"] if a["owned_file"]}
    changed = []
    for name, attempt in expected.items():
        try:
            path = Path(name)
            if (path.is_symlink() or not path.is_file() or path.stat().st_size != attempt["physical_bytes"]
                    or _file_sha(name) != attempt["physical_sha256"]):
                changed.append(name)
        except BaseException as exc:
            changed.append(name)
            _observation_failure(state["guard_observation_errors"], "owned_output_SHA", name, exc)
    try:
        directory = state["directory"]
        if directory.is_symlink() or not directory.is_dir(): changed.append(str(directory))
        children = list(directory.iterdir())
        actual = {str(p) for p in children}
        changed.extend(str(p) for p in children if p.is_symlink() or not p.is_file())
        changed.extend(sorted(actual.symmetric_difference(expected)))
    except BaseException as exc:
        changed.append(str(state["directory"]))
        _observation_failure(state["guard_observation_errors"], "owned_output_inventory", state["directory"], exc)
    if changed:
        state["changed_output_paths"] = sorted(set(state["changed_output_paths"] + changed))
        _error(state, "output_SHA_or_exact_owned_inventory_changed")
    if state["guard_observation_errors"]: _error(state, "guard_observation_unconfirmed")
    return not changed


def _attempt(state, name, raw, kind):
    path = state["directory"] / name
    attempt = {"artifact": str(path), "kind": kind, "attempted_bytes": len(raw),
        "attempted_sha256": _sha(raw), "physical_bytes": 0, "physical_sha256": None,
        "persisted": False, "owned_file": False, "error": None}
    state["attempts"].append(attempt)
    state["attempted_bytes"] += len(raw)  # nonrefundable BEFORE open/write
    existed = path.exists()
    try:
        if state["attempted_bytes"] > state["plan"]["output_reserved_bytes_before_pair_calculation"]:
            raise ValueError("attempt_exceeded_whole_reserved_output_no_write")
        _write_payload(path, raw)
        if path.stat().st_size != len(raw) or _file_sha(path) != attempt["attempted_sha256"]:
            raise OSError("exclusive_written_bytes_or_SHA_disagrees")
        attempt["persisted"] = True
    except BaseException as exc:
        attempt["error"] = (type(exc).__name__ + ":" + str(exc))[:256]
        _error(state, attempt["error"])
    if not existed and path.exists():
        attempt["owned_file"] = True
        try:
            attempt["physical_bytes"], attempt["physical_sha256"] = path.stat().st_size, _file_sha(path)
        except BaseException as exc:
            attempt["physical_bytes"] = attempt["physical_sha256"] = None
            attempt["physical_observation_error"] = (type(exc).__name__ + ":" + str(exc))[:256]
            _error(state, "physical_fragment_observation_unconfirmed")
    return attempt


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
    if _guard_full(record): raise ValueError("registered_input_or_expected_inventory_changed_before_begin")
    destination.mkdir(parents=False, exist_ok=False)
    state = {"data": data, "plan": record, "directory": destination,
        "attempts": [], "attempted_bytes": 0, "errors": [], "stopped": False, "finished": False,
        "terminal_persisted": False, "changed_protected_paths": [], "changed_output_paths": [],
        "guard_observation_errors": [],
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
    _STORES[handle] = state
    _attempt(state, "run-plan.json", data.record, "run_plan")
    _guard(state)
    if state["stopped"]: finish(handle)
    return handle


def _encoded(state, raw):
    return gzip.compress(raw, mtime=0) if state["plan"]["compressed"] else raw


def _ensure_catalog(state, index, *, source=False):
    records = state["sources"] if source else state["groups"]
    stored = records[index]
    handle = state["data"].sources[index] if source else state["data"].handles[index]
    expected = state["plan"]["sources" if source else "groups"][index]
    if ((source and handle.source_ref != expected["source_catalog_ref"])
            or (not source and (handle.catalog_ref != expected["catalog_ref"]
                or handle.source_ref != expected["source_catalog_ref"]))):
        _error(state, "owned_source_or_group_identity_changed")
        return False
    persisted_key = "persisted" if source else "catalog_persisted"
    if stored[persisted_key]: return True
    raw = state["data"].source_raw[index] if source else state["data"].catalog_raw[index]
    if raw is None: return False
    stored["encoding_attempted"] = True
    try: encoded = _encoded(state, raw)
    except BaseException as exc:
        _error(state, ("catalog_encoding_failed:" + type(exc).__name__ + ":" + str(exc))[:256])
        return False
    stored["encoded_bytes"], stored["encoded_sha256"] = len(encoded), _sha(encoded)
    bound = state["plan"]["sources" if source else "groups"][index]["source_encoded_bound" if source else "catalog_encoded_bound"]
    if len(encoded) > bound:
        _error(state, "catalog_exceeded_whole_reserved_encoded_bound")
        return False
    suffix = ".json.gz" if state["plan"]["compressed"] else ".json"
    kind = "source_catalog" if source else "local_catalog"
    name = f"source-{index:04d}-catalog" if source else f"group-{index:04d}-catalog"
    attempt = _attempt(state, name + suffix, encoded, kind)
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
        if (pair["version"] != core.VERSION or pair["codec"] != "source-shared-original-row-refinement-v1"
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
    try:
        row["calculation_attempted"] = True
        block = core.compare_block(prepared, task)
        _validate_block(prepared, task, block, gp["original"]["selector_indices"])
        row["core_result_confirmed"] = True
        row.update(computed_pairs=block["computed_pairs"], held_pairs=block["withheld_pairs"])
        encoded = _encoded(state, _raw(block))
        row.update(encoded_bytes=len(encoded), encoded_sha256=_sha(encoded))
        if len(encoded) > gp["task_encoded_caps"][ti]:
            row["status"] = "whole_block_storage_bytes_hold_no_prefix"
            row["held_pairs"] = task.expected_pairs - row["computed_pairs"]
        else:
            suffix = ".json.gz" if state["plan"]["compressed"] else ".json"
            attempt = _attempt(state, f"group-{group_index:04d}-block-{ti:06d}" + suffix, encoded, "block")
            row["status"] = "held" if block["withheld_pairs"] else "computed_unpersisted"
            if attempt["persisted"]:
                row["persisted_pairs"] = row["computed_pairs"]
                row["status"] = "held" if block["withheld_pairs"] else "computed_persisted"
        stored["next_task"] += 1
    except BaseException as exc:
        row["unconfirmed_computation_pairs"] = 0 if row["core_result_confirmed"] else task.expected_pairs
        row["status"] = "interrupted_computed_unpersisted" if row["core_result_confirmed"] else "interrupted_unconfirmed_computation"
        _error(state, (type(exc).__name__ + ":" + str(exc))[:256])
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
        _guard(state, full=True); _outputs(state)
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
            "uncomputed_task_ranges": [deepcopy(t["task"]) for t in stored["tasks"] if t["status"] in ("uncomputed", "interrupted_unconfirmed_computation")],
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
        "changed_protected_paths": list(state["changed_protected_paths"]), "changed_output_paths": list(state["changed_output_paths"]),
        "guard_observation_errors": deepcopy(state["guard_observation_errors"]),
        "unconfirmed_guard_observations": len(state["guard_observation_errors"]),
        "terminal_persisted": state["terminal_persisted"], "selected": None, "rank": None, "confidence": None,
        "musical_outcome": None, "flags": _flags()}


def finish(run):
    state = _store(run)
    if state["finished"]: return ledger(run)
    _guard(state, full=True); _outputs(state)
    report = ledger(run)
    report["terminal_commit_contract"] = "manifest_cannot_self_certify_its_own_write_verify_owned_terminal_result"
    encoded = _raw(report)
    if len(encoded) > state["plan"]["final_manifest_reserved_bytes"]:
        _error(state, "final_manifest_exceeded_reserved_bytes")
    else:
        attempt = _attempt(state, "report.json", encoded, "final_manifest")
        state["terminal_persisted"] = attempt["persisted"]
    _guard(state, full=True); _outputs(state)
    state["finished"] = True
    return ledger(run)
