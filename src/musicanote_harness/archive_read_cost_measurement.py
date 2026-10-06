"""Byte-only, explicitly separate measurement phases; never parser admission.

Unknown decoded lengths are the reason to measure, not permission to parse.
Each submitted ordered phase has one non-restartable account. Completed file
observations in an interrupted/capped phase cannot make that phase complete.
Receipts bind measured bytes to physical SHA, code SHA, occurrence order and
terminal inventory guards. They do not authenticate historical membership,
issue a JSON reader, validate music, or replace a later reader's accounting.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
from weakref import WeakKeyDictionary

VERSION = "archive-read-cost-measurement-0.1.0"
AUTHORITY = "submitted_byte_measurement_phases_not_archive_or_parser_admission"
_CHUNK = 1048576
_PLANS, _SESSIONS, _RECEIPTS = WeakKeyDictionary(), WeakKeyDictionary(), WeakKeyDictionary()


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("exact_nonnegative_integer_required:" + name)


def _text(value, name):
    if type(value) is not str or not value:
        raise ValueError("nonempty_string_required:" + name)


def _plain(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is list:
        for item in value:
            _plain(item)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            _plain(item)
        return
    raise ValueError("plain_JSON_declaration_required_no_float_or_nonfinite")


def _raw(value):
    _plain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value):
    return hashlib.sha256(_raw(value)).hexdigest()


def _hex(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
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


def _linked(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _flags():
    return {name: False for name in ("historical_archive_admission_complete",
        "all_original_archive_membership_verified", "parser_reader_issued", "body_JSON_parsed",
        "all_saved_bodies_validated", "native_authority_claimed", "producer_replayed",
        "full_contrast_evaluated", "winning_harmony_selected", "music_accuracy_measured",
        "training_eligible", "gold_eligible", "generation_ready", "production_modified",
        "process_peak_memory_measured")}


@dataclass(frozen=True, slots=True)
class MeasurementLimits:
    max_file_bytes: int = 67108864
    max_decoded_file_bytes: int = 268435456
    max_phase_decoded_bytes: int = 1073741824
    max_measurement_occurrences: int = 10000
    max_registered_files: int = 20000
    max_inventory_roots: int = 16

    def __post_init__(self):
        for name, value in asdict(self).items():
            _integer(value, name)


@dataclass(frozen=True, slots=True)
class MeasurementInput:
    measurement_id: str
    path: str
    expected_sha256: str
    encoding: str = "raw"


@dataclass(frozen=True, slots=True)
class InventoryRoot:
    directory: str
    registered_sha256: dict


class MeasurementPlan:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("measurement_plan_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_immutable_measurement_plan")

    def record(self):
        return deepcopy(_plan(self)["record"])


class MeasurementSession:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("measurement_session_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_cumulative_measurement_session")

    def record(self):
        return measurement_ledger(self)


class MeasurementReceipt:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("measurement_receipt_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_immutable_measurement_receipt")

    def record(self):
        return deepcopy(_receipt(self)["record"])

    def json_bytes(self):
        """Exchange bytes only; this library never writes an archive or receipt."""
        return _receipt(self)["json"]


def _plan(handle):
    if type(handle) is not MeasurementPlan or handle not in _PLANS:
        raise ValueError("owned_measurement_plan_required_not_external_summary")
    return _PLANS[handle]


def _session(handle):
    if type(handle) is not MeasurementSession or handle not in _SESSIONS:
        raise ValueError("owned_measurement_session_required_not_external_summary")
    return _SESSIONS[handle]


def _receipt(handle):
    if type(handle) is not MeasurementReceipt or handle not in _RECEIPTS:
        raise ValueError("owned_measurement_receipt_required_not_external_summary")
    return _RECEIPTS[handle]


class WholeMeasurementHold(ValueError):
    def __init__(self, plan):
        self.plan = plan.record()
        super().__init__("whole_measurement_phase_hold:" + ",".join(self.plan["reasons"]))


class MeasurementFailure(ValueError):
    def __init__(self, reason, session):
        self.session = session  # Needed to finish guards and retain failed phase receipt.
        self.ledger = measurement_ledger(session)
        super().__init__(reason)


def _hash_stream(stream, counters):
    result, count = hashlib.sha256(), 0
    counters["hash_attempts"] += 1
    try:
        for block in iter(lambda: stream.read(_CHUNK), b""):
            count += len(block)
            counters["hash_returned"] += len(block)
            result.update(block)
    except BaseException:
        counters["hash_unconfirmed"] = True
        raise
    return result.hexdigest(), count


def _guards(data, counters, *, target_only=None, inventories=True):
    errors = []
    selected = data["protected"] if target_only is None else {
        path: data["protected"][path] for path in target_only}
    for name, sha in selected.items():
        try:
            path = Path(name)
            if _linked(path):
                errors.append("registered_target_link_changed:" + name)
                continue
            with path.open("rb") as stream:
                actual, _ = _hash_stream(stream, counters)
            if actual != sha:
                errors.append("registered_physical_SHA_changed:" + name)
        except OSError:
            errors.append("registered_physical_unreadable:" + name)
    for root in data["roots"] if inventories else ():
        path = Path(root["directory"])
        try:
            descendants = list(path.rglob("*"))
            if not path.is_dir() or _linked(path) or any(_linked(p) for p in descendants):
                errors.append("exact_inventory_root_missing_or_link:" + str(path))
            actual = sorted(str(p.resolve()) for p in descendants if p.is_file())
            if actual != sorted(root["registered_sha256"]):
                errors.append("exact_registered_inventory_changed:" + str(path))
        except OSError:
            errors.append("exact_registered_inventory_unreadable:" + str(path))
    return errors


def plan_measurement_phase(inputs, *, phase_id, logical_run_id, original_denominators,
        registered_sha256, inventory_roots, source_archive_roots=(), output_directory=None, limits=None):
    """Freeze complete CALLER-declared phase, without parsing source JSON.

    Every input is an occurrence: repeated files are not deduplicated. Decoded
    costs are deliberately unknown until streaming EOF. Historical membership
    and future parser admission remain outside this byte-only phase.
    """
    _text(phase_id, "phase_id")
    _text(logical_run_id, "logical_run_id")
    _plain(original_denominators)
    limits = MeasurementLimits() if limits is None else limits
    if (type(inputs) is not list or type(limits) is not MeasurementLimits
            or type(original_denominators) is not dict or type(registered_sha256) is not dict
            or type(inventory_roots) is not tuple or not inventory_roots
            or type(source_archive_roots) is not tuple):
        raise ValueError("complete_typed_phase_and_explicit_registered_inventory_roots_required")
    protected, roots, requests, reasons = {}, [], [], []
    for path, sha in registered_sha256.items():
        _path(path)
        _hex(sha)
        protected[path] = sha
    for item in inventory_roots:
        if type(item) is not InventoryRoot or type(item.registered_sha256) is not dict:
            raise ValueError("exact_registered_measurement_inventory_root_required")
        directory, subset = _path(item.directory), {}
        for path, sha in item.registered_sha256.items():
            if not _inside(_path(path), directory) or protected.get(path) != sha:
                raise ValueError("inventory_membership_must_match_registered_physical_SHA")
            subset[path] = sha
        roots.append({"directory": str(directory), "registered_sha256": subset})
    if len({r["directory"] for r in roots}) != len(roots):
        raise ValueError("duplicate_exact_measurement_inventory_root")
    archive_roots = sorted({str(_path(p)) for p in source_archive_roots}
        | {r["directory"] for r in roots})
    output = None if output_directory is None else str(_path(output_directory))
    if output is not None and (output in protected or any(_inside(Path(output), Path(p)) for p in archive_roots)):
        raise ValueError("measurement_output_must_be_outside_registered_source_archive_roots")
    encodings = {}
    for item in inputs:
        if type(item) is not MeasurementInput:
            raise ValueError("exact_measurement_input_required")
        _text(item.measurement_id, "measurement_id")
        path = _path(item.path)
        _hex(item.expected_sha256)
        if protected.get(item.path) != item.expected_sha256:
            raise ValueError("every_measurement_requires_registered_physical_SHA_membership")
        if item.encoding not in ("raw", "gzip"):
            raise ValueError("closed_byte_only_raw_or_gzip_encoding_required")
        if item.path in encodings and encodings[item.path] != item.encoding:
            raise ValueError("repeated_target_encoding_must_be_consistent")
        encodings[item.path] = item.encoding
        physical = None
        try:
            if _linked(path) or not path.is_file():
                reasons.append("missing_or_linked_registered_measurement_target")
            else:
                physical = path.stat().st_size
                if physical > limits.max_file_bytes:
                    reasons.append("whole_physical_file_limit_no_prefix_measurement")
        except OSError:
            reasons.append("unreadable_registered_measurement_target")
        requests.append({**asdict(item), "observed_physical_bytes_at_plan": physical,
            "decoded_bytes": None})
    if len({r["measurement_id"] for r in requests}) != len(requests):
        raise ValueError("unique_measurement_occurrence_ids_required")
    counts = {"hash_attempts": 0, "hash_returned": 0, "hash_unconfirmed": False}
    own_code = str(Path(__file__).resolve())
    with Path(own_code).open("rb") as stream:
        code_sha, _ = _hash_stream(stream, counts)
    if own_code in protected and protected[own_code] != code_sha:
        reasons.append("current_measurement_code_SHA_mismatch")
    protected[own_code] = code_sha
    if (len(requests) > limits.max_measurement_occurrences or len(protected) > limits.max_registered_files
            or len(roots) > limits.max_inventory_roots):
        reasons.append("whole_measurement_inventory_count_limit_no_prefix")
    data = {"protected": protected, "roots": roots, "own_code": own_code}
    if not reasons:
        reasons.extend(_guards(data, counts))
    record = {"version": VERSION, "authority": AUTHORITY, "phase_id": phase_id,
        "logical_run_id": logical_run_id, "scope": "caller_declared_ordered_measurement_occurrences_only",
        "original_denominators": deepcopy(original_denominators), "inputs": requests,
        "planned_occurrences": len(requests), "planned_unique_files": len(encodings),
        "unknown_decoded_occurrences": len(requests), "known_empty_measurement_set": not requests,
        "declared_complete_measurement_phase": True, "decoded_byte_reservation": None if requests else 0,
        "registered_sha256": deepcopy(protected), "exact_inventory_roots": roots,
        "source_archive_roots": archive_roots, "output_directory": output,
        "limits": asdict(limits), "code_sha256": code_sha, "code_path": own_code,
        "initial_hash_accounting": deepcopy(counts), "reasons": sorted(set(reasons)),
        "status": "whole_measurement_hold" if reasons else "measurement_plan_ready_not_measured",
        "physical_guard_schedule": {"plan_begin_finish": "all_registered_SHA_and_exact_roots",
            "each_occurrence": "target_and_fixed_code_before_and_after_plus_same_open_SHA"},
        "flags": _flags()}
    record["plan_ref"] = "mcplan_" + _digest(record)
    handle = object.__new__(MeasurementPlan)
    _PLANS[handle] = {**data, "record": record, "requests": tuple(deepcopy(requests)),
        "limits": limits, "initial_counts": counts}
    return handle


def begin_measurements(plan):
    data = _plan(plan)
    if data["record"]["reasons"]:
        raise WholeMeasurementHold(plan)
    if data.get("started"):
        raise ValueError("one_account_per_owned_measurement_phase_no_restart")
    data["started"] = True
    handle = object.__new__(MeasurementSession)
    state = {**data, "next": 0, "attempts": [], "reasons": [], "finished": False,
        "decoded_returned": 0, "physical_returned": 0, "decoded_unconfirmed": False,
        "physical_unconfirmed": False, "max_block": 0,
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "started_ns": time.monotonic_ns(),
        "finished_ns": None, "terminal_guards_passed": False, "receipt": None,
        **deepcopy(data["initial_counts"])}
    _SESSIONS[handle] = state
    try:
        state["reasons"].extend(_guards(state, state))
    except BaseException as exc:
        state["hash_unconfirmed"] = True
        state["reasons"].append("initial_measurement_guard_unconfirmed:" + type(exc).__name__)
    if state["reasons"]:
        raise MeasurementFailure("registered_inputs_changed_before_measurement", handle)
    return handle


class _PhysicalStream:
    def __init__(self, stream, state, attempt):
        self.stream, self.state, self.attempt = stream, state, attempt

    def read(self, size=-1):
        try:
            block = self.stream.read(size)
        except BaseException:
            self.state["physical_unconfirmed"] = True
            self.attempt["physical_bytes_unconfirmed"] = True
            raise
        self.state["physical_returned"] += len(block)
        self.attempt["physical_bytes_returned"] += len(block)
        return block


def measure_next(session, measurement_id):
    """Discard streaming bytes, return provisional observation, never parse JSON."""
    state = _session(session)
    if state["finished"] or state["reasons"]:
        raise ValueError("terminal_or_failed_measurement_phase_not_reusable")
    index = state["next"]
    if (index >= len(state["requests"]) or type(measurement_id) is not str
            or state["requests"][index]["measurement_id"] != measurement_id):
        raise ValueError("exact_next_measurement_occurrence_required_no_skip_duplicate_or_reorder")
    request = state["requests"][index]
    attempt = {"measurement_id": measurement_id, "occurrence_index": index,
        "path": request["path"], "expected_sha256": request["expected_sha256"],
        "encoding": request["encoding"], "physical_bytes": None, "decoded_bytes": None,
        "physical_bytes_returned": 0, "decoded_bytes_returned": 0,
        "physical_bytes_unconfirmed": False, "decoded_bytes_unconfirmed": False,
        "decoded_prefix_sha256": None, "decoded_sha256": None,
        "stream_EOF_reached": False, "same_open_before_after_SHA_verified": False,
        "completed": False, "error": None}
    state["attempts"].append(attempt)
    decoded_hash, failure = hashlib.sha256(), None
    paths = tuple({request["path"], state["own_code"]})
    try:
        errors = _guards(state, state, target_only=paths, inventories=False)
        if errors:
            raise ValueError("registered_target_or_fixed_code_changed_before_measurement:" + ",".join(errors))
        with Path(request["path"]).open("rb") as physical:
            sha, physical_size = _hash_stream(physical, state)
            if sha != request["expected_sha256"] or physical_size != request["observed_physical_bytes_at_plan"]:
                raise ValueError("same_open_registered_SHA_or_physical_size_changed")
            if physical_size > state["limits"].max_file_bytes:
                raise ValueError("runtime_physical_file_limit_no_prefix")
            attempt["physical_bytes"] = physical_size
            physical.seek(0)
            counted = _PhysicalStream(physical, state, attempt)
            stream = gzip.GzipFile(fileobj=counted, mode="rb") if request["encoding"] == "gzip" else counted
            remaining = state["limits"].max_phase_decoded_bytes - state["decoded_returned"]
            cap = min(state["limits"].max_decoded_file_bytes, remaining)
            try:
                while True:
                    try:
                        block = stream.read(min(_CHUNK, cap - attempt["decoded_bytes_returned"] + 1))
                    except BaseException:
                        state["decoded_unconfirmed"] = True
                        attempt["decoded_bytes_unconfirmed"] = True
                        raise
                    length = len(block)
                    state["decoded_returned"] += length
                    attempt["decoded_bytes_returned"] += length
                    state["max_block"] = max(state["max_block"], length)
                    decoded_hash.update(block)
                    if attempt["decoded_bytes_returned"] > cap:
                        if request["encoding"] == "gzip":
                            state["decoded_unconfirmed"] = True
                            attempt["decoded_bytes_unconfirmed"] = True
                        raise ValueError("runtime_decoded_phase_or_file_limit_no_prefix")
                    if not block:
                        attempt["stream_EOF_reached"] = True
                        break
            finally:
                if request["encoding"] == "gzip":
                    stream.close()
            physical.seek(0)
            after_sha, after_size = _hash_stream(physical, state)
            if after_sha != sha or after_size != physical_size:
                raise ValueError("same_open_target_changed_during_measurement")
            attempt["same_open_before_after_SHA_verified"] = True
        errors = _guards(state, state, target_only=paths, inventories=False)
        if errors:
            raise ValueError("registered_target_or_fixed_code_changed_after_measurement:" + ",".join(errors))
        attempt["decoded_bytes"] = attempt["decoded_bytes_returned"]
        attempt["decoded_sha256"] = decoded_hash.hexdigest()
        attempt["completed"] = True
        state["next"] += 1
    except BaseException as exc:
        failure = exc
        attempt["error"] = type(exc).__name__ + ":" + str(exc)[:512]
        state["reasons"].append("failed_measurement_occurrence_no_prefix_completion:" + measurement_id)
    finally:
        attempt["decoded_prefix_sha256"] = decoded_hash.hexdigest()
        if failure is not None:
            try:
                state["reasons"].extend(_guards(state, state, target_only=paths, inventories=False))
            except BaseException:
                state["hash_unconfirmed"] = True
                state["reasons"].append("post_failure_measurement_guard_unconfirmed")
    if failure is not None:
        raise MeasurementFailure("whole_measurement_runtime_failure:" + measurement_id, session) from failure
    return deepcopy(attempt)


def measurement_ledger(session):
    state = _session(session)
    plan, n = state["record"], len(state["requests"])
    complete = state["finished"] and state["terminal_guards_passed"] and not state["reasons"] and state["next"] == n
    end = state["finished_ns"] if state["finished_ns"] is not None else time.monotonic_ns()
    return {"version": VERSION, "authority": AUTHORITY, "plan_ref": plan["plan_ref"],
        "phase_id": plan["phase_id"], "logical_run_id": plan["logical_run_id"], "scope": plan["scope"],
        "original_denominators": deepcopy(plan["original_denominators"]), "limits": deepcopy(plan["limits"]),
        "planned_occurrences": n, "known_empty_measurement_set": n == 0,
        "attempted_occurrences": len(state["attempts"]), "completed_occurrences": state["next"],
        "failed_occurrences": len(state["attempts"]) - state["next"],
        "never_attempted_occurrences": n - len(state["attempts"]), "incomplete_occurrences": n - state["next"],
        "remaining_measurement_ids": [r["measurement_id"] for r in state["requests"][state["next"]:]],
        "never_attempted_measurement_ids": [r["measurement_id"] for r in state["requests"][len(state["attempts"]):]],
        "planned_measurement_ids": [r["measurement_id"] for r in state["requests"]],
        "decoded_bytes_returned_lower_bound": state["decoded_returned"],
        "decoded_attempt_bytes": None if state["decoded_unconfirmed"] else state["decoded_returned"],
        "measured_complete_phase_decoded_bytes": state["decoded_returned"] if complete else None,
        "physical_bytes_returned_lower_bound": state["physical_returned"],
        "physical_attempt_bytes": None if state["physical_unconfirmed"] else state["physical_returned"],
        "hash_verification_attempts": state["hash_attempts"],
        "hash_verification_bytes_returned_lower_bound": state["hash_returned"],
        "hash_verification_attempt_bytes": None if state["hash_unconfirmed"] else state["hash_returned"],
        "physical_hash_checks_consume_decoded_budget": False,
        "started_at_utc": state["started_at_utc"], "elapsed_nanoseconds": end - state["started_ns"],
        "maximum_returned_decoded_block_bytes": state["max_block"], "stream_chunk_bytes": _CHUNK,
        "process_peak_memory_bytes": None, "streamed_payload_retained_for_JSON": False,
        "terminal_guards_passed": state["terminal_guards_passed"], "phase_complete": complete,
        "status": "submitted_measurement_phase_complete" if complete else
            ("whole_measurement_failed_or_held" if state["reasons"] else "submitted_measurement_phase_incomplete"),
        "observations": deepcopy(state["attempts"]), "reasons": list(state["reasons"]),
        "flags": _flags(), "later_parser_reads_are_separate_charged_work": True}


def finish_measurements(session):
    """Idempotent immutable receipt; final guards cannot promote a prefix."""
    state = _session(session)
    if state["receipt"] is not None:
        return state["receipt"]
    try:
        errors = _guards(state, state)
        state["reasons"].extend(errors)
        state["terminal_guards_passed"] = not errors
    except BaseException as exc:
        state["hash_unconfirmed"] = True
        state["reasons"].append("terminal_measurement_guard_unconfirmed:" + type(exc).__name__)
    finally:
        state["finished"] = True
        state["finished_ns"] = time.monotonic_ns()
    record = measurement_ledger(session)
    record["provenance"] = {"plan": deepcopy(state["record"]),
        "byte_contract": "physical_SHA_and_streaming_EOF_without_JSON_parse",
        "authority_boundary": "no_archive_membership_or_parser_admission_or_decoder_reuse"}
    record["receipt_ref"] = "mcreceipt_" + _digest(record)
    receipt = object.__new__(MeasurementReceipt)
    _RECEIPTS[receipt] = {"record": record, "json": _raw(record)}
    state["receipt"] = receipt
    return receipt


def aggregate_measurements(receipts, *, logical_run_id, original_denominators,
        expected_phase_ids, expected_measurement_ids):
    """Explicit separate phases: report total; never reset a parser budget.

    Only in-process owned receipts are accepted. Saved exchange JSON remains
    evidence requiring its own verification; it cannot recreate an owned
    measurement session or parser reader. Both complete phase and occurrence
    lists are caller declarations, not historical archive authentication.
    """
    _text(logical_run_id, "logical_run_id")
    _plain(original_denominators)
    if (type(receipts) is not list or type(expected_phase_ids) is not list
            or type(expected_measurement_ids) is not list or type(original_denominators) is not dict):
        raise ValueError("complete_ordered_phase_and_occurrence_aggregate_declarations_required")
    for values, name in ((expected_phase_ids, "phase_id"), (expected_measurement_ids, "measurement_id")):
        for value in values:
            _text(value, name)
        if len(set(values)) != len(values):
            raise ValueError("unique_declared_aggregate_" + name + "s_required")
    records = [_receipt(r)["record"] for r in receipts]
    if any(r["logical_run_id"] != logical_run_id or r["original_denominators"] != original_denominators for r in records):
        raise ValueError("same_logical_measurement_run_and_whole_denominators_required")
    actual_phases = [r["phase_id"] for r in records]
    actual_ids = [i for r in records for i in r["planned_measurement_ids"]]
    if len(set(actual_phases)) != len(actual_phases) or len(set(actual_ids)) != len(actual_ids):
        raise ValueError("duplicate_phase_or_occurrence_receipt_cannot_reset_logical_account")
    exact = actual_phases == expected_phase_ids and actual_ids == expected_measurement_ids
    complete = exact and all(r["phase_complete"] for r in records)
    decoded_lower = sum(r["decoded_bytes_returned_lower_bound"] for r in records)
    result = {"version": VERSION, "authority": AUTHORITY,
        "scope": "explicit_separate_measurement_phases_not_one_resettable_parser_read_run",
        "logical_run_id": logical_run_id, "original_denominators": deepcopy(original_denominators),
        "expected_phase_ids": list(expected_phase_ids), "observed_phase_ids": actual_phases,
        "expected_measurement_ids": list(expected_measurement_ids), "observed_measurement_ids": actual_ids,
        "missing_phase_ids": [p for p in expected_phase_ids if p not in actual_phases],
        "missing_measurement_ids": [i for i in expected_measurement_ids if i not in actual_ids],
        "exact_declared_ordered_phase_and_occurrence_coverage": exact,
        "all_declared_measurement_phases_complete": complete,
        "decoded_bytes_returned_lower_bound": decoded_lower,
        "decoded_attempt_bytes": None if any(r["decoded_attempt_bytes"] is None for r in records)
            else sum(r["decoded_attempt_bytes"] for r in records),
        "measured_complete_logical_decoded_bytes": decoded_lower if complete else None,
        "physical_bytes_returned_lower_bound": sum(r["physical_bytes_returned_lower_bound"] for r in records),
        "hash_verification_bytes_returned_lower_bound": sum(r["hash_verification_bytes_returned_lower_bound"] for r in records),
        "elapsed_nanoseconds_sum": sum(r["elapsed_nanoseconds"] for r in records),
        "default_parser_total_decoded_limit": MeasurementLimits().max_phase_decoded_bytes,
        "measured_lower_bound_exceeds_default_parser_total_limit": decoded_lower > MeasurementLimits().max_phase_decoded_bytes,
        "same_parser_read_run_may_not_reset_budget_per_measurement_phase": True,
        "measurement_and_later_parser_costs_must_be_reported_separately": True,
        "receipt_refs": [r["receipt_ref"] for r in records], "phase_receipts": deepcopy(records),
        "flags": _flags()}
    result["aggregate_ref"] = "mcaggregate_" + _digest(result)
    return result
