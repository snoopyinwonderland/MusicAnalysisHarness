"""Research-only exact window sharing; NOT a native lattice issuer.

Own a JSON snapshot of the FULL IR. Only the fixed context window is retained
between batches. Candidate/theory results remain target-specific. Legacy
catalog payloads are unchanged; provenance and measured work live outside them.
Assumes trusted, single-process code with no concurrent runtime/file mutation.
Pre/post freshness checks do not prove absence of transient A->B->A mutation.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
import hmac
import inspect
import json
from pathlib import Path
from secrets import token_hex
from threading import Lock
from time import perf_counter
from types import CodeType
from weakref import WeakKeyDictionary

from . import harmony_candidate_catalog as legacy
from . import harmony_open_candidates as opened
from . import harmony_candidate_windows_catalog as adapter

VERSION = "shared-candidate-window-supply-0.1.0"
PACKAGE = "musicanote_harness"
ROOT = Path(__file__).resolve().parent
_OWNERS = WeakKeyDictionary()
_OWNERS_LOCK = Lock()
_OWNER_SECRET = bytes.fromhex(token_hex(32))


def canonical_json(value):
    """Preserve array order and JSON types; rational wire values are not reduced."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _json_input(value):
    if value is None or type(value) in (str, int, float, bool):
        return
    if type(value) is list:
        for item in value:
            _json_input(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json_input(item)
        return
    raise ValueError("JSON_only_full_IR_snapshot_required")


def _limit(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("explicit_nonnegative_integer_required:" + name)


def _span(value):
    if type(value) is not dict or set(value) != {"start", "end"}:
        raise ValueError("closed_exact_span_required")
    times = []
    for key in ("start", "end"):
        v = value[key]
        if (type(v) is not dict or set(v) != {"numerator", "denominator"}
                or type(v["numerator"]) is not int or type(v["denominator"]) is not int
                or v["denominator"] <= 0):
            raise ValueError("exact_rational_required")
        times.append(Fraction(v["numerator"], v["denominator"]))
    if not 0 <= times[0] < times[1]:
        raise ValueError("invalid_span")
    return tuple(times)


def _constant(value):
    if value is None or type(value) in (str, int, float, bool):
        return value
    if isinstance(value, Fraction):
        return {"fraction": [value.numerator, value.denominator]}
    if isinstance(value, Path):
        return {"path": str(value)}
    if type(value) is bytes:
        return {"bytes": value.hex()}
    if type(value) is complex:
        return {"complex": [value.real, value.imag]}
    if isinstance(value, CodeType):
        return _code_content(value)
    if type(value) in (list, tuple):
        return {type(value).__name__: [_constant(v) for v in value]}
    if type(value) in (set, frozenset):
        return {type(value).__name__: sorted((_constant(v) for v in value), key=canonical_json)}
    if type(value) is dict:
        return {"dict": sorted([[_constant(k), _constant(v)] for k, v in value.items()],
                               key=canonical_json)}
    # Objects/services are not a portable music producer constant.
    return {"type": type(value).__module__ + "." + type(value).__qualname__}


def _code_content(code):
    # marshal's reference/interning encoding can change after first execution.
    # Hash semantic, unquickened attributes instead; recurse into nested code.
    return {"bytecode": code.co_code.hex(), "constants": [_constant(v) for v in code.co_consts],
            "names": code.co_names, "varnames": code.co_varnames, "freevars": code.co_freevars,
            "cellvars": code.co_cellvars, "argcount": code.co_argcount,
            "posonly": code.co_posonlyargcount, "kwonly": code.co_kwonlyargcount,
            "nlocals": code.co_nlocals, "stacksize": code.co_stacksize, "flags": code.co_flags,
            "filename": code.co_filename, "name": code.co_name, "qualname": code.co_qualname,
            "firstlineno": code.co_firstlineno, "linetable": code.co_linetable.hex(),
            "exceptiontable": code.co_exceptiontable.hex()}


def producer_contract():
    """Conservative relative-import closure plus loaded function/constant checks.

    Includes helpers/observers, not just the facade VERSION. File bytes cover
    dormant relative imports too; loaded callable identities additionally catch
    persistent in-process replacement. Not a sandbox/security certificate.
    """
    pending = [Path(__file__), Path(legacy.__file__), Path(opened.__file__), Path(adapter.__file__)]
    files, runtime = {}, {}
    while pending:
        path = pending.pop().resolve()
        if str(path) in files:
            continue
        raw = path.read_bytes()
        files[str(path)] = sha256(raw).hexdigest()
        tree = ast.parse(raw, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                names = [node.module] if node.module else [n.name for n in node.names]
                for name in names:
                    dependency = ROOT / (name.replace(".", "/") + ".py")
                    if dependency.is_file():
                        pending.append(dependency)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(PACKAGE + "."):
                        dependency = ROOT / (alias.name[len(PACKAGE) + 1:].replace(".", "/") + ".py")
                        if dependency.is_file():
                            pending.append(dependency)
        # Do not import dormant dependencies and change old lazy error branches.
        import sys
        module = sys.modules.get(PACKAGE + "." + path.stem)
        if module is None or path == Path(__file__).resolve():
            continue
        entries = {}
        for name, value in vars(module).items():
            if inspect.isfunction(value) and value.__module__.startswith(PACKAGE):
                entries[name] = {"identity": id(value), "code": _digest(canonical_json(_code_content(value.__code__))),
                                 "defaults": _constant(value.__defaults__),
                                 "kwdefaults": _constant(value.__kwdefaults__)}
            elif name.isupper() and not name.startswith("_"):
                entries[name] = _constant(value)
        runtime[module.__name__] = entries
    return {"version": VERSION, "file_sha256": files, "loaded_runtime": runtime}


@dataclass(frozen=True, eq=False)
class SupplySession:
    """Opaque process-owned identity, not transferable JSON authority."""
    token: str


@dataclass
class _Cache:
    value: str | None = None
    seal: str | None = None


@dataclass(frozen=True)
class _Owned:
    ir_json: str
    context_json: str
    contract_json: str
    binding_json: str
    max_context_window_bytes: int
    cache: _Cache = field(default_factory=_Cache)
    lock: Lock = field(default_factory=Lock)


def _owner_seal(session, state):
    body = [session.token, id(session), id(state), id(state.cache), id(state.lock),
            _digest(state.ir_json), _digest(state.context_json), _digest(state.contract_json),
            state.binding_json, state.max_context_window_bytes]
    return hmac.new(_OWNER_SECRET, canonical_json(body).encode("utf-8"), "sha256").hexdigest()


def _cache_seal(session, state, value):
    return hmac.new(_OWNER_SECRET, canonical_json([
        _owner_seal(session, state), _digest(value)]).encode("utf-8"), "sha256").hexdigest()


def prepare_supply(ir, context_span, *, max_ir_bytes=268435456,
                   max_context_window_bytes=33554432):
    _limit(max_ir_bytes, "max_ir_bytes")
    _limit(max_context_window_bytes, "max_context_window_bytes")
    _span(context_span)
    _json_input(ir)
    before = canonical_json(producer_contract())
    text = canonical_json(ir)
    # Never project out-of-context rows: legacy theory checks some global IDs.
    if type(ir) is not dict or len(text.encode("utf-8")) > max_ir_bytes:
        raise ValueError("full_IR_snapshot_budget_or_type")
    context = canonical_json(context_span)
    if before != canonical_json(producer_contract()):
        raise ValueError("producer_changed_during_prepare")
    binding = {"full_ir_sha256": _digest(text), "context_span_sha256": _digest(context),
               "producer_contract_sha256": _digest(before),
               "max_context_window_bytes": max_context_window_bytes,
               "authority": "owned_full_IR_content_not_original_file_or_parent_replay"}
    session = SupplySession(token_hex(24))
    state = _Owned(text, context, before, canonical_json(binding), max_context_window_bytes)
    with _OWNERS_LOCK:
        _OWNERS[session] = (state, _owner_seal(session, state))
    return session


def _owned(session):
    if type(session) is not SupplySession:
        raise ValueError("issued_supply_session_required")
    with _OWNERS_LOCK:
        registered = _OWNERS.get(session)
    if registered is None:
        raise ValueError("foreign_or_copied_supply_session")
    if type(registered) is not tuple or len(registered) != 2 or type(registered[0]) is not _Owned:
        raise ValueError("invalid_owned_supply_state")
    state, seal = registered
    if type(state.cache) is not _Cache or type(seal) is not str or not hmac.compare_digest(seal, _owner_seal(session, state)):
        raise ValueError("owned_supply_state_changed")
    if state.cache.value is not None and (type(state.cache.value) is not str
            or type(state.cache.seal) is not str
            or not hmac.compare_digest(state.cache.seal, _cache_seal(session, state, state.cache.value))):
        raise ValueError("owned_context_cache_changed")
    if state.cache.value is None and state.cache.seal is not None:
        raise ValueError("owned_context_cache_changed")
    return state


def session_binding(session):
    return json.loads(_owned(session).binding_json)


def supply_catalogs(session, spans, *, max_requests=1024, max_window_calls=1024,
                    max_output_bytes=67108864):
    """Whole batch: either every occurrence is returned, or no catalog prefix.

    Distinct raw spans are calculated once per batch. Base windows/catalogs are
    not retained across batches. Counts for uncomputed catalogs are null, not 0.
    max_output_bytes caps serialized payload, not total RSS or elapsed time.
    """
    started = perf_counter()
    for name, value in (("max_requests", max_requests), ("max_window_calls", max_window_calls),
                        ("max_output_bytes", max_output_bytes)):
        _limit(value, name)
    if type(spans) is not list:
        raise ValueError("closed_span_request_list_required")
    state = _owned(session)
    if not state.lock.acquire(blocking=False):
        raise ValueError("concurrent_supply_on_same_session")
    try:
        contract = canonical_json(producer_contract())
        if contract != state.contract_json:
            raise ValueError("stale_supply_producer")
        context = json.loads(state.context_json)
        left, right = _span(context)
        keys, unique = [], {}
        for span in spans:
            a, b = _span(span)
            if not left <= a < b <= right:
                raise ValueError("span_outside_owned_context")
            key = canonical_json(span)
            keys.append(key)
            unique.setdefault(key, json.loads(key))
        need_context = bool(keys) and state.cache.value is None
        planned_windows = int(need_context) + sum(k != state.context_json for k in unique)
        # Raw-wire-different but numerically equal contexts remain distinct windows.
        stats = {"window_calls": 0, "window_seconds": 0.0, "catalog_seconds": 0.0,
                 "snapshot_load_seconds": 0.0, "serialization_seconds": 0.0,
                 "context_cache_hit": bool(keys) and not need_context}
        receipt = {"version": VERSION, "binding": json.loads(state.binding_json),
                   "requests": len(keys), "distinct_raw_spans": len(unique),
                   "planned_window_calls": planned_windows, "limits": {
                       "max_requests": max_requests, "max_window_calls": max_window_calls,
                       "max_output_bytes": max_output_bytes},
                   "catalog_candidate_counts": None, "status": "held", "hold_reason": None,
                   "payload_sha256": None, "payload_bytes": None,
                   "production_enabled": False, "native_lattice_authority": False,
                   "music_accuracy_evaluated": False, "stats": stats}
        reason = "request_budget" if len(keys) > max_requests else (
                 "window_budget" if planned_windows > max_window_calls else None)
        texts, context_text = {}, state.cache.value
        occurrences = Counter(keys)
        output_bytes = 2 + max(0, len(keys) - 1)
        if reason is None and keys:
            t = perf_counter(); owned_ir = json.loads(state.ir_json)
            stats["snapshot_load_seconds"] += perf_counter() - t
            def calculate_window(span):
                t = perf_counter(); value = opened.window(owned_ir, span)
                stats["window_seconds"] += perf_counter() - t
                stats["window_calls"] += 1
                return value
            if need_context:
                context_window = calculate_window(context)
                context_text = canonical_json(context_window)
                if len(context_text.encode("utf-8")) > state.max_context_window_bytes:
                    reason = "context_window_bytes_budget"
            else:
                context_window = json.loads(context_text)
            for key, span in unique.items():
                if reason is not None:
                    break
                base = context_window if key == state.context_json else calculate_window(span)
                t = perf_counter()
                value = adapter.from_windows(owned_ir, span, context, base, context_window)
                stats["catalog_seconds"] += perf_counter() - t
                t = perf_counter(); texts[key] = canonical_json(value)
                stats["serialization_seconds"] += perf_counter() - t
                output_bytes += len(texts[key].encode("utf-8")) * occurrences[key]
                if output_bytes > max_output_bytes:
                    reason = "output_bytes_budget"
                    break
        # Freshness checked even on budget hold. No failed batch warms the cache.
        if contract != canonical_json(producer_contract()):
            raise ValueError("producer_changed_during_supply")
        catalogs = None
        if reason is None:
            catalogs = [json.loads(texts[k]) for k in keys]
            payload = canonical_json(catalogs)
            if len(payload.encode("utf-8")) > max_output_bytes:
                reason = "output_bytes_budget"
                catalogs = None
            else:
                _owned(session)  # persistent source/cache/identity corruption guard
                if context_text is not None:
                    state.cache.value = context_text
                    state.cache.seal = _cache_seal(session, state, context_text)
                receipt.update(status="complete", payload_sha256=_digest(payload),
                               payload_bytes=len(payload.encode("utf-8")),
                               catalog_candidate_counts=[len(c["candidates"]) for c in catalogs])
        receipt["hold_reason"] = reason
        stats["elapsed_seconds"] = perf_counter() - started
        return {"catalogs": catalogs, "receipt": receipt}
    finally:
        state.lock.release()
