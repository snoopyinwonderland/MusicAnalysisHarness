"""Owned cumulative byte accounting for one ordered saved-JSON read plan.

This is NOT historical archive admission, musical validation or a corpus runner.
Caller-declared decoded lengths are reservations, not measurements: every actual
read must match them. Repeated physical paths remain distinct charged reads.
Frozen loaders are not patched; a future versioned bridge can share one issued
reader through its ``read(path)`` adapter across metadata and body consumers.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
import math
from pathlib import Path
from weakref import WeakKeyDictionary

VERSION = "cross-batch-read-budget-0.1.0"
AUTHORITY = "submitted_ordered_registered_reads_not_historical_archive_admission"
_PLANS, _READERS = WeakKeyDictionary(), WeakKeyDictionary()
_CHUNK = 1048576


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("exact_nonnegative_integer_required:" + name)


def _plain(value, *, floats=False):
    if value is None or type(value) in (str, bool, int):
        return
    if floats and type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _plain(item, floats=floats)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            _plain(item, floats=floats)
        return
    raise ValueError("plain_JSON_required_no_nonfinite_or_declaration_float")


def _raw(value):
    _plain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hex(value):
    if (type(value) is not str or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError("exact_lowercase_SHA256_required")


def _path(value):
    if type(value) is not str:
        raise ValueError("canonical_absolute_path_required")
    result = Path(value)
    if not result.is_absolute() or str(result.resolve()) != value:
        raise ValueError("canonical_absolute_path_required")
    return result


def _inside(path, root):
    return path == root or root in path.parents


def _flags():
    return {name: False for name in ("historical_archive_admission_complete",
        "all_original_archive_membership_verified", "all_saved_bodies_validated",
        "full_contrast_evaluated", "native_authority_claimed", "producer_replayed",
        "music_accuracy_measured", "winning_harmony_selected", "training_eligible",
        "gold_eligible", "generation_ready", "production_modified")}


@dataclass(frozen=True, slots=True)
class ReadLimits:
    max_file_bytes: int = 67108864
    max_decoded_file_bytes: int = 268435456
    max_total_decoded_bytes: int = 1073741824
    max_read_occurrences: int = 10000
    max_registered_files: int = 20000
    max_inventory_roots: int = 16

    def __post_init__(self):
        for name, value in asdict(self).items():
            _integer(value, name)


@dataclass(frozen=True, slots=True)
class ReadInput:
    read_id: str
    path: str
    sha256: str
    physical_bytes: int | None
    decoded_bytes: int | None
    encoding: str = "json"
    phase: str = "body"


@dataclass(frozen=True, slots=True)
class InventoryRoot:
    """Exact root membership supplied separately from the read occurrence list."""
    directory: str
    registered_sha256: dict


class ReadPlan:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("read_plan_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_owned_read_plan")

    def record(self):
        return json.loads(_plan(self)["record"])


class RegisteredReader:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("registered_reader_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_cumulative_reader")

    def read(self, path):
        """Adapter accepts ONLY the exact next planned path; no new budget."""
        state = _reader(self)
        if state["next"] >= len(state["requests"]):
            raise ValueError("no_remaining_planned_read")
        expected = state["requests"][state["next"]]
        if str(Path(path).resolve()) != expected["path"]:
            raise ValueError("exact_next_planned_path_required_no_skip_or_reorder")
        return read_record(self, expected["read_id"])

    @property
    def decoded_bytes(self):
        return _reader(self)["decoded_returned"]

    @property
    def read_files(self):
        return _reader(self)["completed"]


def _plan(handle):
    if type(handle) is not ReadPlan or handle not in _PLANS:
        raise ValueError("owned_read_plan_required_not_external_summary")
    return _PLANS[handle]


def _reader(handle):
    if type(handle) is not RegisteredReader or handle not in _READERS:
        raise ValueError("owned_cumulative_reader_required_not_external_summary")
    return _READERS[handle]


class WholeReadHold(ValueError):
    def __init__(self, plan):
        self.plan = plan.record()
        super().__init__("whole_ordered_read_hold:" + ",".join(self.plan["reasons"]))


class ReadFailure(ValueError):
    def __init__(self, reason, reader):
        self.ledger = read_ledger(reader)
        super().__init__(reason)


def _hash_stream(stream, counters):
    result, count = hashlib.sha256(), 0
    counters["hash_attempts"] += 1
    try:
        for block in iter(lambda: stream.read(_CHUNK), b""):
            count += len(block)
            counters["hash_bytes_returned"] += len(block)
            result.update(block)
    except BaseException:
        counters["hash_bytes_unconfirmed"] = True
        raise
    return result.hexdigest(), count


def _guards(data, counters, *, paths=None, inventories=True):
    errors = []
    selected = data["protected"] if paths is None else {name: data["protected"][name] for name in paths}
    for name, sha in selected.items():
        try:
            with Path(name).open("rb") as stream:
                actual, _ = _hash_stream(stream, counters)
            if actual != sha:
                errors.append("registered_physical_SHA_changed:" + name)
        except OSError:
            errors.append("registered_physical_unreadable:" + name)
    for root in data["roots"] if inventories else ():
        directory = Path(root["directory"])
        try:
            descendants = list(directory.rglob("*"))
            if not directory.is_dir() or any(p.is_symlink() for p in descendants):
                errors.append("exact_inventory_root_missing_or_symlink:" + str(directory))
            actual = sorted(str(p.resolve()) for p in descendants if p.is_file())
            if actual != sorted(root["registered_sha256"]):
                errors.append("exact_registered_inventory_changed:" + str(directory))
        except OSError:
            errors.append("exact_registered_inventory_unreadable:" + str(directory))
    return errors


def plan_read_run(reads, *, original_denominators, registered_sha256,
        inventory_roots=(), source_archive_roots=(), output_directory=None, limits=None):
    """Freeze a COMPLETE submitted ordered plan, then admit or whole-hold it.

    Decoded byte declarations must be measured/derived by the caller and are not
    promoted to historical authority. Unknown costs hold; repeats count again.
    No JSON is parsed here. A held plan still preserves its complete read and
    original denominator inventory, and cannot issue a reader.
    """
    limits = ReadLimits() if limits is None else limits
    if type(limits) is not ReadLimits or type(reads) is not list:
        raise ValueError("exact_read_limits_and_complete_ordered_list_required")
    _plain(original_denominators)
    if type(original_denominators) is not dict or type(registered_sha256) is not dict:
        raise ValueError("plain_original_denominators_and_registered_SHA_map_required")
    if type(inventory_roots) is not tuple or type(source_archive_roots) is not tuple:
        raise ValueError("fixed_inventory_and_archive_root_tuples_required")
    protected = {}
    for path, sha in registered_sha256.items():
        _path(path)
        _hex(sha)
        protected[path] = sha
    roots = []
    for item in inventory_roots:
        if type(item) is not InventoryRoot or type(item.registered_sha256) is not dict:
            raise ValueError("exact_registered_inventory_root_required")
        directory = _path(item.directory)
        subset = {}
        for path, sha in item.registered_sha256.items():
            if not _inside(_path(path), directory) or protected.get(path) != sha:
                raise ValueError("inventory_membership_must_match_registered_physical_SHA")
            subset[path] = sha
        roots.append({"directory": str(directory), "registered_sha256": subset})
    if len({r["directory"] for r in roots}) != len(roots):
        raise ValueError("duplicate_exact_inventory_root")
    archive_roots = sorted({str(_path(p)) for p in source_archive_roots}
        | {r["directory"] for r in roots})
    output = None if output_directory is None else str(_path(output_directory))
    if output is not None:
        if any(_inside(Path(output), Path(root)) for root in archive_roots):
            raise ValueError("output_must_be_outside_declared_source_archive_roots")
        if output in protected:
            raise ValueError("output_must_not_replace_registered_source_file")
    requests, previous, reasons = [], {}, []
    for item in reads:
        if type(item) is not ReadInput or type(item.read_id) is not str or not item.read_id:
            raise ValueError("exact_read_input_with_occurrence_identity_required")
        path = _path(item.path)
        _hex(item.sha256)
        if protected.get(item.path) != item.sha256:
            raise ValueError("every_read_requires_registered_physical_SHA_membership")
        if item.encoding not in ("json", "gzip-json") or item.phase not in ("metadata", "body", "other"):
            raise ValueError("closed_saved_JSON_encoding_and_read_phase_required")
        for name in ("physical_bytes", "decoded_bytes"):
            if getattr(item, name) is not None:
                _integer(getattr(item, name), name)
        record = asdict(item)
        if item.path in previous:
            other = previous[item.path]
            if any(record[k] is not None and other[k] is not None and record[k] != other[k]
                    for k in ("encoding", "physical_bytes", "decoded_bytes")):
                raise ValueError("repeated_physical_source_requires_consistent_byte_declarations")
        previous[item.path] = record
        requests.append(record)
        if item.physical_bytes is None or item.decoded_bytes is None:
            reasons.append("unknown_read_byte_bound_no_prefix")
        if item.physical_bytes is not None and item.physical_bytes > limits.max_file_bytes:
            reasons.append("whole_physical_file_limit_no_prefix")
        if item.decoded_bytes is not None and item.decoded_bytes > limits.max_decoded_file_bytes:
            reasons.append("whole_decoded_file_limit_no_prefix")
        try:
            if path.is_symlink() or not path.is_file():
                reasons.append("missing_or_symlink_registered_body_no_prefix")
            elif item.physical_bytes is not None and path.stat().st_size != item.physical_bytes:
                reasons.append("declared_physical_size_mismatch_no_prefix")
        except OSError:
            reasons.append("unreadable_registered_body_no_prefix")
    if len({r["read_id"] for r in requests}) != len(requests):
        raise ValueError("unique_original_read_occurrence_ids_required")
    unknown = sum(r["decoded_bytes"] is None for r in requests)
    known_sum = sum(r["decoded_bytes"] or 0 for r in requests)
    planned_sum = None if unknown else known_sum
    if known_sum > limits.max_total_decoded_bytes:
        reasons.append("whole_cumulative_decoded_limit_no_prefix")
    own_code = str(Path(__file__).resolve())
    initial_counts = {"hash_attempts": 0, "hash_bytes_returned": 0, "hash_bytes_unconfirmed": False}
    with Path(own_code).open("rb") as stream:
        own_sha, _ = _hash_stream(stream, initial_counts)
    if own_code in protected and protected[own_code] != own_sha:
        reasons.append("current_read_account_code_SHA_mismatch")
    protected[own_code] = own_sha
    if (len(reads) > limits.max_read_occurrences or len(protected) > limits.max_registered_files
            or len(roots) > limits.max_inventory_roots):
        reasons.append("whole_registered_inventory_count_limit_no_prefix")
    data = {"protected": protected, "roots": roots, "own_code": own_code}
    guard_errors = [] if reasons else _guards(data, initial_counts)
    reasons.extend(guard_errors)
    record = {"version": VERSION, "authority": AUTHORITY,
        "scope": "submitted_ordered_read_occurrences_only", "reads": requests,
        "original_denominators": deepcopy(original_denominators), "limits": asdict(limits),
        "planned_read_occurrences": len(requests), "planned_unique_read_files": len(previous),
        "planned_physical_read_bytes": None if any(r["physical_bytes"] is None for r in requests)
            else sum(r["physical_bytes"] for r in requests),
        "known_decoded_reservation_bytes": known_sum, "planned_decoded_bytes": planned_sum,
        "unknown_decoded_occurrences": unknown, "known_empty_read_set": not requests,
        "registered_physical_membership_checked": not reasons,
        "exact_inventory_roots": roots, "declared_source_archive_roots": archive_roots,
        "output_directory": output, "reasons": sorted(set(reasons)),
        "status": "whole_read_hold" if reasons else "read_plan_admitted_not_read_complete",
        "flags": _flags(), "initial_hash_accounting": initial_counts,
        "current_code_protection_scope": [own_code],
        "physical_guard_schedule": {"plan_begin_finish": "all_registered_SHA_and_exact_roots",
            "each_read": "target_and_current_code_pre_decode_post_decode_post_parse",
            "other_registered_mutation_detection": "terminal_guard_before_submitted_complete"}}
    handle = object.__new__(ReadPlan)
    _PLANS[handle] = {**data, "record": _raw(record), "requests": tuple(deepcopy(requests)),
        "limits": limits, "initial_counts": initial_counts}
    return handle


def begin_reads(plan):
    data = _plan(plan)
    if plan.record()["reasons"]:
        raise WholeReadHold(plan)
    if data.get("started"):
        raise ValueError("one_cumulative_account_per_owned_plan_no_restart")
    data["started"] = True
    handle = object.__new__(RegisteredReader)
    state = {**data, "next": 0, "completed": 0, "attempts": [], "reasons": [],
        "decoded_returned": 0, "physical_returned": 0, "bytes_unconfirmed": False,
        "finished": False, **deepcopy(data["initial_counts"])}
    _READERS[handle] = state
    try:
        errors = _guards(state, state)
    except BaseException as exc:
        state["hash_bytes_unconfirmed"] = True
        state["finished"] = True
        state["reasons"].append("initial_registered_guard_unconfirmed:" + type(exc).__name__)
        raise ReadFailure("registered_initial_guard_unconfirmed", handle) from exc
    if errors:
        state["reasons"].extend(errors)
        raise ReadFailure("registered_inputs_changed_before_reads", handle)
    return handle


class _PhysicalStream:
    def __init__(self, stream, state, attempt):
        self.stream, self.state, self.attempt = stream, state, attempt

    def read(self, size=-1):
        try:
            block = self.stream.read(size)
        except BaseException:
            self.state["bytes_unconfirmed"] = True
            self.attempt["physical_bytes_unconfirmed"] = True
            raise
        self.state["physical_returned"] += len(block)
        self.attempt["physical_bytes_returned"] += len(block)
        return block


def _constant(value):
    raise ValueError("nonfinite_saved_JSON_number:" + value)


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite_saved_JSON_float:" + value)
    return result


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_saved_JSON_key:" + key)
        result[key] = value
    return result


def read_record(reader, read_id):
    """Read one exact next occurrence; every failed attempt is nonrefundable."""
    state = _reader(reader)
    if state["finished"] or state["reasons"]:
        raise ValueError("terminal_or_failed_cumulative_reader_not_reusable")
    index = state["next"]
    if index >= len(state["requests"]) or type(read_id) is not str or state["requests"][index]["read_id"] != read_id:
        raise ValueError("exact_next_read_occurrence_required_no_skip_duplicate_or_reorder")
    request = state["requests"][index]
    attempt = {"read_id": read_id, "occurrence_index": index, "phase": request["phase"],
        "path": request["path"], "expected_physical_bytes": request["physical_bytes"],
        "expected_decoded_bytes": request["decoded_bytes"], "physical_bytes_returned": 0,
        "decoded_bytes_returned": 0, "physical_bytes_unconfirmed": False,
        "decoded_bytes_unconfirmed": False, "decoded_prefix_sha256": None,
        "JSON_parse_attempted": False, "completed": False, "error": None}
    state["attempts"].append(attempt)
    chunks, decoded_sha = [], hashlib.sha256()
    failure, result = None, None
    guarded_paths = tuple({request["path"], state["own_code"]})
    try:
        errors = _guards(state, state, paths=guarded_paths, inventories=False)
        if errors:
            raise ValueError("registered_inputs_or_inventory_changed_before_read:" + ",".join(errors))
        with Path(request["path"]).open("rb") as physical:
            physical_sha, physical_size = _hash_stream(physical, state)
            if physical_sha != request["sha256"] or physical_size != request["physical_bytes"]:
                raise ValueError("same_open_file_registered_SHA_or_size_changed")
            physical.seek(0)
            counted = _PhysicalStream(physical, state, attempt)
            stream = gzip.GzipFile(fileobj=counted, mode="rb") if request["encoding"] == "gzip-json" else counted
            cap = min(request["decoded_bytes"], state["limits"].max_decoded_file_bytes,
                state["limits"].max_total_decoded_bytes - state["decoded_returned"])
            try:
                while True:
                    try:
                        block = stream.read(min(_CHUNK, cap - attempt["decoded_bytes_returned"] + 1))
                    except BaseException:
                        # gzip may have produced internal data before raising.
                        state["bytes_unconfirmed"] = True
                        attempt["decoded_bytes_unconfirmed"] = True
                        raise
                    state["decoded_returned"] += len(block)
                    attempt["decoded_bytes_returned"] += len(block)
                    decoded_sha.update(block)
                    if attempt["decoded_bytes_returned"] > cap:
                        raise ValueError("actual_decoded_bytes_exceed_reservation_no_partial_JSON")
                    if not block:
                        break
                    chunks.append(block)
            finally:
                if request["encoding"] == "gzip-json":
                    stream.close()
            physical.seek(0)
            after_sha, after_size = _hash_stream(physical, state)
            if after_sha != request["sha256"] or after_size != request["physical_bytes"]:
                raise ValueError("same_open_file_changed_during_decode")
        if attempt["decoded_bytes_returned"] != request["decoded_bytes"]:
            raise ValueError("exact_decoded_size_mismatch_no_partial_JSON")
        errors = _guards(state, state, paths=guarded_paths, inventories=False)
        if errors:
            raise ValueError("registered_inputs_or_inventory_changed_after_read:" + ",".join(errors))
        attempt["JSON_parse_attempted"] = True
        value = json.loads(b"".join(chunks).decode("utf-8"), parse_constant=_constant,
            parse_float=_float, object_pairs_hook=_object)
        _plain(value, floats=True)
        # A decoder/consumer side effect cannot cross the final physical guard.
        errors = _guards(state, state, paths=guarded_paths, inventories=False)
        if errors:
            raise ValueError("registered_inputs_changed_during_JSON_parse:" + ",".join(errors))
        state["next"] += 1
        state["completed"] += 1
        attempt["completed"] = True
        result = value
    except BaseException as exc:
        failure = exc
        attempt["error"] = type(exc).__name__ + ":" + str(exc)[:512]
        state["reasons"].append("failed_original_read_occurrence_no_prefix_completion:" + read_id)
    finally:
        attempt["decoded_prefix_sha256"] = decoded_sha.hexdigest()
        if failure is not None:
            try:
                state["reasons"].extend(_guards(state, state, paths=guarded_paths, inventories=False))
            except BaseException:
                state["reasons"].append("post_failure_registered_guard_unconfirmed")
    if failure is not None:
        raise ReadFailure("whole_read_runtime_failure:" + read_id, reader) from failure
    return result


def read_ledger(reader):
    state = _reader(reader)
    plan = json.loads(state["record"])
    n, completed = len(state["requests"]), state["completed"]
    complete = state["finished"] and not state["reasons"] and completed == n
    return {"version": VERSION, "authority": AUTHORITY, "scope": plan["scope"],
        "original_denominators": deepcopy(plan["original_denominators"]),
        "planned_read_occurrences": n, "planned_decoded_bytes": plan["planned_decoded_bytes"],
        "known_empty_read_set": n == 0, "attempted_read_occurrences": len(state["attempts"]),
        "completed_read_occurrences": completed, "failed_read_occurrences": len(state["attempts"]) - completed,
        "never_attempted_read_occurrences": n - len(state["attempts"]),
        "held_or_incomplete_read_occurrences": n - completed,
        "decoded_bytes_returned_lower_bound": state["decoded_returned"],
        "decoded_attempt_bytes": None if state["bytes_unconfirmed"] else state["decoded_returned"],
        "body_physical_bytes_returned_lower_bound": state["physical_returned"],
        "hash_verification_attempts": state["hash_attempts"],
        "hash_verification_bytes_returned_lower_bound": state["hash_bytes_returned"],
        "hash_verification_attempt_bytes": None if state["hash_bytes_unconfirmed"] else state["hash_bytes_returned"],
        "physical_hash_checks_consume_decoded_budget": False,
        "submitted_read_set_complete": complete, "status": "submitted_reads_complete" if complete else
            ("whole_read_failed_or_held" if state["reasons"] else "submitted_reads_incomplete"),
        "reasons": list(state["reasons"]), "attempts": deepcopy(state["attempts"]),
        "flags": _flags()}


def finish_reads(reader):
    """Terminal guards and exact original occurrence coverage, never full corpus."""
    state = _reader(reader)
    try:
        state["reasons"].extend(_guards(state, state))
    except BaseException as exc:
        state["hash_bytes_unconfirmed"] = True
        state["reasons"].append("terminal_registered_guard_unconfirmed:" + type(exc).__name__)
    finally:
        state["finished"] = True
    return read_ledger(reader)
