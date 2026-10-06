"""Exclusive saved-only storage of a caller-declared set of admitted groups.

Only core-issued PreparedGroup handles authorize calculations. Original group
metadata and denominators are copied declarations, NOT physical-file or whole
archive admission. No corpus runner, catalog re-admission, producer or winner
is provided. The default two-GiB output cap is deliberately conservative:
reserving the default 64-MiB encoded cap for every task may hold a large run.
Tighter caps require an explicit caller decision; actual overruns hold a WHOLE
block, retaining computed-but-unpersisted counts, never a favorable prefix.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
from weakref import WeakKeyDictionary

from . import cross_batch_progression_contrast as core

VERSION = "cross-batch-progression-storage-0.1.0"
AUTHORITY = "validated_saved_group_storage_not_full_archive_admission"
_PLANS, _STORES = WeakKeyDictionary(), WeakKeyDictionary()
_MAX_DESTINATION_UTF8_BYTES = 1024
_ORIGINAL_KEYS = {"source_identity_sha256", "scope_ref", "lattice_ref",
    "completion_request_ref", "key_ref", "bundle_ref", "selector_indices",
    "planned_entries", "planned_pairs", "planned_block_tasks", "block_size"}


def _flags():
    return {name: False for name in ("physical_original_request_admission",
        "full_contrast_evaluated", "policy_evaluated", "winning_harmony_selected",
        "musical_accuracy_measured", "native_or_role_producer_replayed",
        "live_native_authority_claimed", "independent_completions_unioned",
        "production_modified", "training_eligible", "gold_eligible", "generation_ready")}


def _raw(value):
    core._no_float(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _file_sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest()


def _hex(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("exact_SHA256_required")


def _guard(hashes):
    changed = []
    for path, expected in hashes.items():
        try:
            valid = _file_sha(path) == expected
        except OSError:
            valid = False
        if not valid:
            changed.append(path)
    return changed


@dataclass(frozen=True, slots=True)
class StorageLimits:
    max_output_bytes: int = 2147483648
    max_plan_bytes: int = 2097152
    max_manifest_bytes: int = 16777216
    max_block_encoded_bytes: int = 67108864
    max_groups: int = 128
    max_tasks: int = 8192

    def __post_init__(self):
        for name, value in asdict(self).items():
            core._integer(value, name)


@dataclass(frozen=True, slots=True)
class GroupInput:
    """Original metadata remains caller-declared, including held membership.

    `original` has the closed _ORIGINAL_KEYS schema. A missing handle needs a
    nonempty hold_reasons tuple; an empty handle cannot replace missing entries.
    Original upstream task counts may include known zero-pair diagonal tasks.
    """
    original: dict
    prepared: core.PreparedGroup | None = None
    hold_reasons: tuple[str, ...] = ()


class StoragePlan:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("saved_storage_plan_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_saved_storage_plan")

    def record(self):
        return json.loads(_plan(self)["record"])


class StorageRun:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("saved_storage_run_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_saved_storage_run")


def _plan(handle):
    if type(handle) is not StoragePlan or handle not in _PLANS:
        raise ValueError("owned_storage_plan_required_not_external_summary")
    return _PLANS[handle]


def _store(handle):
    if type(handle) is not StorageRun or handle not in _STORES:
        raise ValueError("owned_storage_run_required_not_external_summary")
    return _STORES[handle]


class WholeRunHold(ValueError):
    def __init__(self, plan):
        self.plan = plan.record()
        super().__init__("whole_saved_storage_run_hold:" + ",".join(self.plan["reasons"]))


def _original(value):
    core._no_float(value)
    if type(value) is not dict or set(value) != _ORIGINAL_KEYS:
        raise ValueError("closed_original_group_declaration_required")
    value = deepcopy(value)
    _hex(value["source_identity_sha256"])
    for name in ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref"):
        core._exact_ref(value[name])
    for name in ("planned_entries", "planned_pairs", "planned_block_tasks", "block_size"):
        core._integer(value[name], name)
    n, size, indices = value["planned_entries"], value["block_size"], value["selector_indices"]
    if not 1 <= size <= 64:
        raise ValueError("block_size_must_be_between_1_and_64")
    if (type(indices) is not list or len(indices) != n
            or any(type(i) is not int or i < 0 for i in indices)
            or indices != sorted(set(indices))):
        raise ValueError("exact_original_selector_membership_required")
    full, tail = divmod(n, size)
    grid = full + bool(tail)
    nonempty = grid * (grid - 1) // 2 + full * (size > 1) + (tail > 1)
    if (value["planned_pairs"] != n * (n - 1) // 2
            or value["planned_block_tasks"] not in (nonempty, grid * (grid + 1) // 2)):
        raise ValueError("exact_declared_original_pair_and_task_denominators_required")
    return value, nonempty


def plan_saved_run(groups, *, original_denominators, protected_sha256=None,
        limits=None, compressed=False, task_encoded_caps=None):
    """Reserve the ENTIRE submitted output before any pair calculation/write.

    task_encoded_caps, if given, maps (group_index, task_index) to explicitly
    lowered stored-byte caps. Compression uses a conservative 2*n+1024 bound
    for catalogs; blocks use declared encoded caps, not observed result sizes.
    Whole-run holds retain all original and submitted denominators. Unknown
    held-group catalog/work costs remain null. Protection covers a fixed current
    two-file code subset and optional caller SHA map, never a historical glob.
    """
    limits = StorageLimits() if limits is None else limits
    if type(limits) is not StorageLimits or type(groups) is not list or type(compressed) is not bool:
        raise ValueError("closed_saved_storage_plan_inputs_required")
    core._no_float(original_denominators)
    if type(original_denominators) is not dict:
        raise ValueError("plain_original_denominators_required")
    protected_sha256 = {} if protected_sha256 is None else protected_sha256
    if type(protected_sha256) is not dict:
        raise ValueError("closed_protected_SHA_map_required")
    hashes = {}
    for path, sha in protected_sha256.items():
        if type(path) is not str:
            raise ValueError("physical_protected_path_required")
        _hex(sha)
        resolved = str(Path(path).resolve(strict=True))
        if resolved in hashes and hashes[resolved] != sha:
            raise ValueError("conflicting_protected_SHA")
        hashes[resolved] = sha
    caller_paths = sorted(hashes)
    for path in (Path(__file__).resolve(), Path(core.__file__).resolve()):
        name, sha = str(path), _file_sha(path)
        if name in hashes and hashes[name] != sha:
            raise ValueError("current_storage_code_SHA_mismatch")
        hashes[name] = sha
    if _guard(hashes):
        raise ValueError("protected_inputs_changed_before_storage_plan")
    declarations, task_count = [], 0
    for item in groups:
        if type(item) is not GroupInput:
            raise ValueError("exact_group_input_required_not_summary")
        original, count = _original(item.original)
        if (type(item.hold_reasons) is not tuple
                or any(type(r) is not str or not r or len(r) > 256 for r in item.hold_reasons)
                or (item.prepared is None) != bool(item.hold_reasons)):
            raise ValueError("explicit_whole_group_hold_or_issued_handle_required")
        declarations.append((original, count, item.prepared, item.hold_reasons))
        task_count += count
    # Caller source identity is preserved metadata, not an authority dimension
    # that can turn one exact scope/request/key/bundle into two submissions.
    # Use ORIGINAL key/bundle refs: empty core groups intentionally have null
    # key/bundle refs and must not collapse distinct declared empty key groups.
    identity = [(o["scope_ref"], o["lattice_ref"],
        o["completion_request_ref"], o["key_ref"], o["bundle_ref"]) for o, _, _, _ in declarations]
    if len({_sha(_raw(i)) for i in identity}) != len(identity):
        raise ValueError("duplicate_declared_original_group")
    reasons = []
    if len(groups) > limits.max_groups or task_count > limits.max_tasks:
        reasons.append("whole_group_or_task_count_exceeds_limit_no_prefix")
    caps = {} if task_encoded_caps is None else task_encoded_caps
    if type(caps) is not dict:
        raise ValueError("closed_per_task_encoded_caps_required")
    for position, cap in caps.items():
        if (type(position) is not tuple or len(position) != 2
                or any(type(i) is not int or i < 0 for i in position)):
            raise ValueError("exact_per_task_cap_position_required")
        core._integer(cap, "task_encoded_cap")
        if cap > limits.max_block_encoded_bytes:
            raise ValueError("per_task_cap_may_only_lower_declared_limit")
    used_caps, rows, handles, catalogs = set(), [], [], []
    # Count gate precedes catalog export and potentially quadratic task lists.
    for gi, (original, count, prepared, held) in enumerate(declarations):
        row = {"original": original, "planned_nonempty_tasks": count,
            "declared_zero_pair_tasks": original["planned_block_tasks"] - count,
            "hold_reasons": list(held), "group_ref": None, "catalog_ref": None,
            "refinement_sha256": None, "entry_inventory_sha256": None,
            "core_preflight": None, "catalog_encoded_bound": None,
            "tasks": None, "task_encoded_caps": None}
        catalog_raw = None
        if not reasons and prepared is not None:
            if type(prepared) is not core.PreparedGroup:
                raise ValueError("issued_prepared_group_required_not_catalog")
            catalog = prepared.export_catalog()  # also authenticates its owned state
            group, cp = catalog["group"], prepared.preflight_plan
            if (cp.entry_count != original["planned_entries"] or cp.block_size != original["block_size"]
                    or group["original_selector_indices"] != original["selector_indices"]
                    or any(group[name] != original[name] for name in
                        ("scope_ref", "lattice_ref", "completion_request_ref"))
                    or (cp.entry_count and any(group[name] != original[name] for name in ("key_ref", "bundle_ref")))
                    or original["bundle_ref"] not in [core.kernels._ref(b) for b in catalog["bundles"].values()]
                    or original["key_ref"] not in [core.kernels._ref(k) for k in catalog["lattice"]["keys"]]):
                raise ValueError("prepared_group_disagrees_with_original_declared_membership")
            tasks = [asdict(task) for task in prepared.iter_blocks()]
            if len(tasks) != count or sum(t["expected_pairs"] for t in tasks) != original["planned_pairs"]:
                raise ValueError("exact_core_nonempty_task_coverage_required")
            encoded_caps = []
            for ti in range(count):
                cap = caps.get((gi, ti), limits.max_block_encoded_bytes)
                core._integer(cap, "task_encoded_cap")
                if cap > limits.max_block_encoded_bytes:
                    raise ValueError("per_task_cap_may_only_lower_declared_limit")
                if (gi, ti) in caps:
                    used_caps.add((gi, ti))
                encoded_caps.append(cap)
                if cap < (18 if compressed else 128):
                    held = (*held, "whole_task_encoded_minimum_exceeds_cap_no_prefix")
            catalog_raw = _raw(catalog)
            row.update(group_ref=prepared.group_ref, catalog_ref=prepared.catalog_ref,
                refinement_sha256=catalog["refinement_sha256"], entry_inventory_sha256=catalog["entry_inventory_sha256"],
                core_preflight=cp.record(), catalog_encoded_bound=(2 * len(catalog_raw) + 1024 if compressed else len(catalog_raw)),
                tasks=tasks, task_encoded_caps=encoded_caps)
            if held:
                reasons.append("whole_task_encoded_minimum_exceeds_cap_no_prefix")
        rows.append(row)
        handles.append(prepared)
        catalogs.append(catalog_raw)
    if not reasons and set(caps) != used_caps:
        raise ValueError("foreign_per_task_encoded_cap")
    reservation = limits.max_plan_bytes + limits.max_manifest_bytes + sum(
        (r["catalog_encoded_bound"] or 0) + sum(r["task_encoded_caps"] or []) for r in rows)
    if reservation > limits.max_output_bytes:
        reasons.append("whole_output_reservation_exceeds_limit_no_prefix")
    record = {"version": VERSION, "source_authority": AUTHORITY,
        "scope": "caller_declared_submitted_group_set_only",
        "original_denominators": deepcopy(original_denominators), "groups": rows,
        "planned_submitted_groups": len(rows), "planned_submitted_entries": sum(o["planned_entries"] for o, _, _, _ in declarations),
        "planned_submitted_pairs": sum(o["planned_pairs"] for o, _, _, _ in declarations),
        "planned_submitted_nonempty_tasks": task_count,
        "planned_declared_upstream_tasks": sum(o["planned_block_tasks"] for o, _, _, _ in declarations),
        "limits": asdict(limits), "compressed": compressed,
        "output_reserved_bytes_before_pair_calculation": reservation,
        "final_manifest_reserved_bytes": limits.max_manifest_bytes,
        "protected_sha256": hashes, "caller_protected_paths": caller_paths,
        "code_protection_scope": "fixed_storage_and_contrast_files_not_full_dependency_or_historical_inventory",
        "status": "whole_saved_storage_run_hold" if reasons else "planned_saved_storage_incomplete",
        "reasons": reasons, "selected": None, "musical_outcome": None, "flags": _flags()}
    # Four copies of all planned metadata, bounded task ledger/attempt/error
    # rows, and bounded absolute paths dominate the terminal encoding. This
    # does NOT predict compressed sizes or permit a too-small final reserve.
    manifest_bound = (4 * len(_raw(record)) + task_count * 4096
        + (task_count + len(rows) + 2) * (_MAX_DESTINATION_UTF8_BYTES + 2048) + 65536)
    record["final_manifest_byte_upper_bound"] = manifest_bound
    record["max_destination_UTF8_bytes"] = _MAX_DESTINATION_UTF8_BYTES
    if manifest_bound > limits.max_manifest_bytes:
        record["reasons"].append("whole_final_manifest_reserve_exceeds_limit_no_prefix")
        record["status"] = "whole_saved_storage_run_hold"
    encoded = _raw(record)
    if len(encoded) > limits.max_plan_bytes:
        record["reasons"].append("whole_run_plan_bytes_exceeds_limit_no_prefix")
        record["status"] = "whole_saved_storage_run_hold"
        encoded = _raw(record)
    handle = object.__new__(StoragePlan)
    _PLANS[handle] = {"record": encoded, "handles": tuple(handles), "catalogs": tuple(catalogs)}
    return handle


def _write_payload(path, raw):
    with path.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("short_exclusive_storage_write")
        stream.flush()
        os.fsync(stream.fileno())


def _attempt(state, name, raw, kind):
    path = state["directory"] / name
    attempt = {"artifact": str(path), "kind": kind, "attempted_bytes": len(raw),
        "attempted_sha256": _sha(raw), "physical_bytes": 0, "physical_sha256": None,
        "persisted": False, "owned_file": False, "error": None}
    state["attempts"].append(attempt)  # charge before open/write, including failures
    existed = path.exists()
    try:
        _write_payload(path, raw)
        if path.stat().st_size != len(raw) or _file_sha(path) != attempt["attempted_sha256"]:
            raise OSError("written_artifact_bytes_or_SHA_disagrees")
        attempt["persisted"] = True
    except BaseException as exc:
        attempt["error"] = (type(exc).__name__ + ":" + str(exc))[:256]
        state["errors"].append(attempt["error"])
        state["stopped"] = True
    if not existed and path.exists():
        attempt["owned_file"] = True
        try:
            attempt["physical_bytes"] = path.stat().st_size
            attempt["physical_sha256"] = _file_sha(path)
        except OSError as exc:
            attempt["physical_bytes"] = None
            attempt["physical_sha256"] = None
            attempt["physical_observation_error"] = (type(exc).__name__ + ":" + str(exc))[:256]
            state["errors"].append("physical_fragment_observation_failed")
            state["stopped"] = True
    return attempt


def _check_guard(state):
    changed = _guard(state["plan"]["protected_sha256"])
    if changed:
        state["changed_protected_paths"] = changed
        if "protected_input_or_current_code_SHA_changed" not in state["errors"]:
            state["errors"].append("protected_input_or_current_code_SHA_changed")
        state["stopped"] = True
    return not changed


def _check_outputs(state):
    expected = {a["artifact"]: a for a in state["attempts"] if a["owned_file"]}
    changed = []
    for path, attempt in expected.items():
        try:
            valid = (Path(path).stat().st_size == attempt["physical_bytes"]
                and _file_sha(path) == attempt["physical_sha256"])
        except OSError:
            valid = False
        if not valid:
            changed.append(path)
    try:
        actual = {str(p) for p in state["directory"].iterdir()}
    except OSError:
        actual = set()
        changed.append(str(state["directory"]))
    if actual != set(expected):
        changed.extend(sorted(actual.symmetric_difference(expected)))
    if changed:
        state["changed_output_paths"] = sorted(set(changed))
        if "output_physical_SHA_or_exact_inventory_changed" not in state["errors"]:
            state["errors"].append("output_physical_SHA_or_exact_inventory_changed")
        state["stopped"] = True
    return not changed


def begin_storage(plan, directory):
    data = _plan(plan)
    record = plan.record()
    if record["reasons"]:
        raise WholeRunHold(plan)
    destination = Path(directory).resolve()
    if len(str(destination).encode("utf-8")) > _MAX_DESTINATION_UTF8_BYTES:
        raise ValueError("bounded_storage_destination_path_required")
    # A NEW directory prevents writing into original archives or user outputs.
    if destination.exists():
        raise FileExistsError("exclusive_new_storage_directory_required:" + str(destination))
    if any(destination == Path(p) or destination in Path(p).parents for p in record["protected_sha256"]):
        raise ValueError("storage_directory_contains_protected_input")
    if _guard(record["protected_sha256"]):
        raise ValueError("protected_inputs_changed_before_storage_begin")
    destination.mkdir(parents=False, exist_ok=False)
    state = {"plan": record, "data": data, "directory": destination, "attempts": [],
        "errors": [], "changed_protected_paths": [], "changed_output_paths": [], "stopped": False, "finished": False,
        "terminal_persisted": False, "groups": []}
    for row in record["groups"]:
        state["groups"].append({"catalog_persisted": False, "catalog_encoding_attempted": False,
            "catalog_encoded_bytes": None, "catalog_encoded_sha256": None, "tasks": [
            {"task": t, "status": "uncomputed", "computed_pairs": 0,
                "persisted_pairs": 0, "held_pairs": 0, "encoded_bytes": None,
                "encoded_sha256": None, "calculation_attempted": False,
                "core_result_confirmed": False, "unconfirmed_computation_pairs": 0}
            for t in row["tasks"] or []]})
    handle = object.__new__(StorageRun)
    _STORES[handle] = state
    _attempt(state, "run-plan.json", data["record"], "run_plan")
    _check_guard(state)
    if state["stopped"]:
        finish(handle)
    return handle


def _encoded(state, raw):
    return gzip.compress(raw, mtime=0) if state["plan"]["compressed"] else raw


def _validate_block(prepared, task, block):
    core._no_float(block)
    core.kernels._check(block, core.BLOCK_PREFIX)
    if (block["version"] != core.VERSION
            or block["task"] != asdict(task) or block["catalog_ref"] != prepared.catalog_ref
            or block["group_ref"] != prepared.group_ref
            or block["refinement_sha256"] != task.refinement_sha256
            or block["entry_inventory_sha256"] != task.entry_inventory_sha256
            or type(block["planned_pairs"]) is not int or block["planned_pairs"] != task.expected_pairs
            or block["whole_group_complete"] is not False or block["selected"] is not None
            or block["rank"] is not None or block["confidence"] is not None
            or block["musical_outcome"] is not None
            or block["flags"] != core.legacy._flags()
            or any(v is not False for v in block["flags"].values())):
        raise ValueError("computed_block_foreign_reference_or_false_flags_required")
    held = block["status"] == "whole_saved_block_hold"
    if (type(block["computed_pairs"]) is not int or type(block["withheld_pairs"]) is not int
            or block["computed_pairs"] + block["withheld_pairs"] != task.expected_pairs
            or (held and (block["pairs"] or block["computed_pairs"] != 0 or not block["reasons"]))
            or (not held and (block["status"] != "computed_saved_block_not_selected"
                or block["reasons"] or block["withheld_pairs"] != 0
                or len(block["pairs"]) != task.expected_pairs))):
        raise ValueError("exact_whole_block_computation_or_hold_required")
    # Shared metadata is immutable; do not export the entire catalog per block.
    indices = core._issued(prepared).catalog["group"]["original_selector_indices"]
    for pair, (i, j) in zip(block["pairs"], task.pair_indices()):
        core.kernels._check(pair, core.PAIR_PREFIX)
        if (pair["version"] != core.VERSION or pair["codec"] != "exact-original-row-refinement-v1"
                or pair["status"] != "computed_saved_pair_contrast_not_selected"
                or type(pair["entry_indices"]) is not list or len(pair["entry_indices"]) != 2
                or any(type(index) is not int for index in pair["entry_indices"])
                or type(pair["original_selector_indices"]) is not list or len(pair["original_selector_indices"]) != 2
                or any(type(index) is not int for index in pair["original_selector_indices"])
                or pair["entry_indices"] != [i, j]
                or pair["original_selector_indices"] != [indices[i], indices[j]]
                or pair["catalog_ref"] != prepared.catalog_ref or pair["group_ref"] != prepared.group_ref
                or pair["refinement_sha256"] != task.refinement_sha256
                or any(pair[k] is not None for k in ("selected", "rank", "confidence", "musical_outcome"))):
            raise ValueError("exact_ordered_block_pair_coverage_required")


def write_block(run, group_index, task):
    """Calculate one exact NEXT task internally; external packets are not accepted."""
    state = _store(run)
    core._integer(group_index, "group_index")
    if state["finished"] or state["stopped"]:
        raise ValueError("storage_run_finished_or_interrupted")
    if group_index >= len(state["groups"]):
        raise ValueError("foreign_submitted_group_index")
    gp, ledger_group = state["plan"]["groups"][group_index], state["groups"][group_index]
    prepared = state["data"]["handles"][group_index]
    ti = next((i for i, t in enumerate(ledger_group["tasks"]) if t["status"] == "uncomputed"), None)
    if (prepared is None or type(task) is not core.BlockTask or ti is None
            or any(type(getattr(task, name)) is not int for name in
                ("row_start", "row_end", "column_start", "column_end", "expected_pairs"))
            or asdict(task) != gp["tasks"][ti]):
        raise ValueError("exact_next_task_required_no_duplicate_missing_reorder_or_foreign")
    if not _check_guard(state) or not _check_outputs(state):
        finish(run)
        return ledger(run)
    if not _write_catalog(state, group_index):
        if state["stopped"]:
            finish(run)
        return ledger(run)
    row = ledger_group["tasks"][ti]
    try:
        row["calculation_attempted"] = True
        block = core.compare_block(prepared, task)
        _validate_block(prepared, task, block)
        row["core_result_confirmed"] = True
        row.update(computed_pairs=block["computed_pairs"], held_pairs=block["withheld_pairs"])
        encoded = _encoded(state, _raw(block))
        row.update(encoded_bytes=len(encoded), encoded_sha256=_sha(encoded))
        if len(encoded) > gp["task_encoded_caps"][ti]:
            row["status"] = "whole_block_storage_bytes_hold_no_prefix"
            # These pairs WERE computed; they are not recast as never computed.
            row["held_pairs"] = task.expected_pairs - row["computed_pairs"]
        else:
            suffix = ".json.gz" if state["plan"]["compressed"] else ".json"
            attempt = _attempt(state, f"group-{group_index:04d}-block-{ti:06d}" + suffix, encoded, "block")
            row["status"] = "held" if block["withheld_pairs"] else "computed_unpersisted"
            if attempt["persisted"]:
                row["persisted_pairs"] = row["computed_pairs"]
                row["status"] = "held" if block["withheld_pairs"] else "computed_persisted"
    except BaseException as exc:
        row["unconfirmed_computation_pairs"] = 0 if row["core_result_confirmed"] else task.expected_pairs
        row["status"] = "interrupted_computed_unpersisted" if row["core_result_confirmed"] else "interrupted_unconfirmed_computation"
        state["errors"].append((type(exc).__name__ + ":" + str(exc))[:256])
        state["stopped"] = True
    _check_guard(state)
    _check_outputs(state)
    if state["stopped"]:
        finish(run)  # best-effort durable interrupt ledger; never masks counts
    return ledger(run)


def _write_catalog(state, group_index):
    group = state["groups"][group_index]
    if group["catalog_persisted"]:
        return True
    raw = state["data"]["catalogs"][group_index]
    if raw is None:
        return False
    group["catalog_encoding_attempted"] = True
    try:
        encoded = _encoded(state, raw)
    except BaseException as exc:
        state["errors"].append(("catalog_encoding_failed:" + type(exc).__name__ + ":" + str(exc))[:256])
        state["stopped"] = True
        return False
    group["catalog_encoded_bytes"], group["catalog_encoded_sha256"] = len(encoded), _sha(encoded)
    if len(encoded) > state["plan"]["groups"][group_index]["catalog_encoded_bound"]:
        state["errors"].append("catalog_exceeded_reserved_encoded_bound")
        state["stopped"] = True
        return False
    suffix = ".json.gz" if state["plan"]["compressed"] else ".json"
    attempt = _attempt(state, f"group-{group_index:04d}-catalog" + suffix, encoded, "catalog")
    group["catalog_persisted"] = attempt["persisted"]
    return attempt["persisted"]


def write_prepared_group(run, group_index):
    state = _store(run)
    core._integer(group_index, "group_index")
    if group_index >= len(state["groups"]):
        raise ValueError("foreign_submitted_group_index")
    if state["stopped"] or state["finished"]:
        raise ValueError("storage_run_finished_or_interrupted")
    if state["data"]["handles"][group_index] is None:
        return ledger(run)
    if _check_guard(state) and _write_catalog(state, group_index):
        for task in state["plan"]["groups"][group_index]["tasks"]:
            write_block(run, group_index, core.BlockTask(**task))
            if state["stopped"]:
                break
    if state["stopped"] and not state["finished"]:
        finish(run)
    return ledger(run)


def ledger(run):
    """Copy exact complements; ranges/indices imply pairs without an all-pair list."""
    state = _store(run)
    if state["finished"]:
        _check_guard(state)
        _check_outputs(state)
    groups, totals = [], {k: 0 for k in ("planned_pairs", "computed_pairs", "persisted_pairs",
        "held_pairs", "storage_held_pairs", "unconfirmed_computation_pairs", "uncomputed_pairs", "unpersisted_pairs", "computed_unpersisted_pairs")}
    for gp, stored in zip(state["plan"]["groups"], state["groups"]):
        planned = gp["original"]["planned_pairs"]
        computed = sum(t["computed_pairs"] for t in stored["tasks"])
        persisted = sum(t["persisted_pairs"] for t in stored["tasks"])
        held = planned if gp["hold_reasons"] else sum(t["held_pairs"] for t in stored["tasks"])
        counts = {"planned_pairs": planned, "computed_pairs": computed,
            "persisted_pairs": persisted, "held_pairs": held,
            "storage_held_pairs": sum(t["task"]["expected_pairs"] for t in stored["tasks"] if t["status"] == "whole_block_storage_bytes_hold_no_prefix"),
            "unconfirmed_computation_pairs": sum(t["unconfirmed_computation_pairs"] for t in stored["tasks"]),
            "uncomputed_pairs": planned - computed - held,
            "unpersisted_pairs": planned - persisted,
            "computed_unpersisted_pairs": computed - persisted}
        for name, value in counts.items():
            totals[name] += value
        groups.append({**deepcopy(gp), **counts, "catalog_persisted": stored["catalog_persisted"],
            "catalog_encoding_attempted": stored["catalog_encoding_attempted"],
            "catalog_encoded_bytes": stored["catalog_encoded_bytes"],
            "catalog_encoded_sha256": stored["catalog_encoded_sha256"],
            "task_ledger": deepcopy(stored["tasks"]),
            "uncomputed_task_ranges": [deepcopy(t["task"]) for t in stored["tasks"] if t["status"] in ("uncomputed", "interrupted_unconfirmed_computation")],
            "unpersisted_task_ranges": [deepcopy(t["task"]) for t in stored["tasks"] if t["persisted_pairs"] != t["task"]["expected_pairs"]]})
    all_computed = totals["computed_pairs"] == totals["planned_pairs"] and all(not g["hold_reasons"] for g in groups)
    ready = (all_computed and totals["persisted_pairs"] == totals["planned_pairs"]
        and all(g["catalog_persisted"] for g in groups) and not state["stopped"])
    complete = ready and state["terminal_persisted"]
    return {"version": VERSION, "source_authority": AUTHORITY,
        "scope": "caller_declared_submitted_group_set_only",
        "original_denominators": deepcopy(state["plan"]["original_denominators"]),
        "planned_submitted_groups": len(groups), "planned_submitted_entries": state["plan"]["planned_submitted_entries"],
        "planned_submitted_nonempty_tasks": state["plan"]["planned_submitted_nonempty_tasks"],
        "planned_declared_upstream_tasks": state["plan"]["planned_declared_upstream_tasks"],
        "groups": groups, "summary": totals, "all_planned_pairs_computed": all_computed,
        "count_semantics": "computed_pairs_are_confirmed_complete_core_records_not_attempted_arithmetic;uncomputed_includes_unconfirmed_computation",
        "submitted_group_set_complete": complete,
        "storage_integrity_passed": not state["errors"],
        "status": "saved_submitted_group_set_complete" if complete else "interrupted_saved_storage" if state["stopped"] else "incomplete_or_held_saved_storage",
        "output_reserved_bytes_before_pair_calculation": state["plan"]["output_reserved_bytes_before_pair_calculation"],
        "attempted_output_bytes": sum(a["attempted_bytes"] for a in state["attempts"]),
        "physical_output_bytes": sum(a["physical_bytes"] for a in state["attempts"] if a["physical_bytes"] is not None),
        "unknown_physical_output_attempts": sum(a["physical_bytes"] is None for a in state["attempts"]),
        "artifact_attempts": deepcopy(state["attempts"]), "errors": list(state["errors"]),
        "changed_protected_paths": list(state["changed_protected_paths"]),
        "changed_output_paths": list(state["changed_output_paths"]),
        "terminal_persisted": state["terminal_persisted"],
        "selected": None, "rank": None, "confidence": None, "musical_outcome": None, "flags": _flags()}


def finish(run):
    """Exclusive final ledger; a failed final write leaves an incomplete owned result.

    The on-disk manifest never self-certifies its own successful write. Its
    pre-terminal coverage is exact; only this owned result, AFTER successful
    physical byte/SHA verification, reports submitted_group_set_complete.
    No reload API treats a catalog/manifest as a computation capability.
    """
    state = _store(run)
    if state["finished"]:
        return ledger(run)
    _check_guard(state)
    _check_outputs(state)
    report = ledger(run)
    report["terminal_commit_contract"] = "manifest_does_not_self_certify_its_write_verify_owned_terminal_result"
    encoded = _raw(report)
    if len(encoded) > state["plan"]["final_manifest_reserved_bytes"]:
        state["errors"].append("final_manifest_exceeded_reserved_bytes")
        state["stopped"] = True
    else:
        attempt = _attempt(state, "report.json", encoded, "final_manifest")
        state["terminal_persisted"] = attempt["persisted"]
    _check_guard(state)
    _check_outputs(state)
    state["finished"] = True
    return ledger(run)
