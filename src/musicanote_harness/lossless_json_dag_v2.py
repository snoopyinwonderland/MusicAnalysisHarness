"""Versioned lossless JSON snapshots; codec proof is not domain authority.

All recursive workers are module-level functions, never self-capturing closures.
Their temporary banks are explicitly cleared even when a traceback is retained.
An owned proof binds exact immutable typed nodes, logical multiplicity and costs;
JSON summaries, imported exchanges and foreign handles cannot restore a proof.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

SCHEMA_NAME = "musicanote-lossless-json-dag"
VERSION = "0.2.0"
_DAGS = WeakKeyDictionary()
_PROOFS = WeakKeyDictionary()
_OWNER_SECRET = secrets.token_bytes(32)


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("exact_nonnegative_integer_required:" + name)


@dataclass(frozen=True, slots=True)
class DagLimits:
    max_input_visits: int = 1000000000
    max_work_units: int = 1000000000
    max_nodes: int = 1000000
    max_encoded_bytes: int = 268435456
    max_expanded_bytes: int = 268435456
    max_depth: int = 128

    def __post_init__(self):
        for name, value in asdict(self).items():
            _integer(value, name)
        if self.max_depth > 256:
            raise ValueError("safe_codec_depth_cannot_exceed_256")


class DagHold(ValueError):
    def __init__(self, reason, diagnostics):
        self.diagnostics = deepcopy(diagnostics)
        super().__init__(reason)


class JsonDag:
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("json_dag_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_immutable_lossless_json_dag")

    def record(self):
        data = _dag(self)
        return _record(data["nodes"], data["root"])

    def json_bytes(self):
        return _dag(self)["raw"]

    def stats(self):
        return deepcopy(dict(_dag(self)["stats"]))


class JsonProof:
    """Opaque immutable owned snapshot; no public constructor or import path."""
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise ValueError("json_proof_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("owned_immutable_lossless_json_proof")

    def stats(self):
        return deepcopy(dict(_proof(self)["stats"]))


@dataclass(frozen=True, slots=True)
class _OwnerState:
    nodes: tuple
    costs: tuple
    root: int
    limits: DagLimits
    stats: MappingProxyType
    raw: bytes | None
    seal: str = ""

    def __getitem__(self, key):
        if key not in ("nodes", "costs", "root", "limits", "stats", "raw"):
            raise KeyError(key)
        return getattr(self, key)


def _owner_seal(owner, state):
    identity = (id(owner), id(state.nodes), id(state.costs), state.root,
        id(state.limits), id(state.stats), id(state.raw))
    return hmac.new(_OWNER_SECRET, repr(identity).encode("ascii"), hashlib.sha256).hexdigest()


def _owned_state(owner, nodes, costs, root, limits, stats, raw=None):
    state = _OwnerState(tuple(nodes), tuple(costs), root, limits,
        MappingProxyType(dict(stats)), raw)
    return _OwnerState(state.nodes, state.costs, state.root, state.limits,
        state.stats, state.raw, _owner_seal(owner, state))


def _checked_state(owner, state, *, proof):
    if (type(state) is not _OwnerState or type(state.nodes) is not tuple or type(state.costs) is not tuple
            or type(state.root) is not int or type(state.limits) is not DagLimits
            or type(state.stats) is not MappingProxyType
            or type(state.seal) is not str
            or (state.raw is not None if proof else type(state.raw) is not bytes)
            or not hmac.compare_digest(state.seal, _owner_seal(owner, state))):
        raise ValueError("owned_immutable_codec_state_binding_required")
    return state


def _dag(handle):
    if type(handle) is not JsonDag or handle not in _DAGS:
        raise ValueError("owned_json_dag_required_not_external_summary")
    return _checked_state(handle, _DAGS[handle], proof=False)


def _proof(handle):
    if type(handle) is not JsonProof or handle not in _PROOFS:
        raise ValueError("owned_json_proof_required_not_external_summary")
    return _checked_state(handle, _PROOFS[handle], proof=True)


def _limits(limits):
    limits = DagLimits() if limits is None else limits
    if type(limits) is not DagLimits:
        raise ValueError("exact_DagLimits_required")
    return limits


def _bytes(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (UnicodeError, ValueError, TypeError) as exc:
        raise ValueError("exact_plain_JSON_with_valid_UTF8_strings_required") from exc


def _string_bytes(value, limits):
    if len(value) > limits.max_expanded_bytes:
        raise DagHold("scalar_expanded_bytes_limit", {"expanded_bytes_lower_bound": len(value)})
    _work_gate(len(value) + 3, limits)
    if 6 * len(value) + 2 > min(limits.max_expanded_bytes, max(limits.max_work_units - 1, 0)):
        width = 2
        for character in value:
            if character in ('"', "\\", "\b", "\f", "\n", "\r", "\t"):
                width += 2
            elif ord(character) < 32:
                width += 6
            else:
                try:
                    width += len(character.encode("utf-8"))
                except UnicodeError as exc:
                    raise ValueError("exact_plain_JSON_with_valid_UTF8_strings_required") from exc
            if width > limits.max_expanded_bytes:
                raise DagHold("scalar_expanded_bytes_limit_before_serialization",
                    {"expanded_bytes_lower_bound": width})
            _work_gate(width + 1, limits)
    raw = None
    try:
        raw = _bytes(value)
        if len(raw) > limits.max_expanded_bytes:
            raise DagHold("scalar_expanded_bytes_limit_before_hash", {"expanded_bytes_lower_bound": len(raw)})
        _work_gate(len(raw) + 1, limits)
        return raw
    finally:
        raw = None


def _scalar(value, limits):
    cls = type(value)
    if value is None:
        kind = "null"
    elif cls is bool:
        kind = "bool"
    elif cls is int:
        kind = "int"
    elif cls is str:
        kind = "str"
    else:
        raise ValueError("plain_JSON_only_no_float_subclass_or_nonfinite")
    minimum = (4 if value is None else (4 if value else 5)) if kind in ("null", "bool") else 1
    if kind == "int":
        minimum = max((value.bit_length() - 1) * 30102 // 100000 + 1, 1) + (1 if value < 0 else 0)
    _cost_gate((minimum, 1, 1, ""), limits)
    _work_gate(minimum + 1, limits)
    raw = None
    try:
        raw = _string_bytes(value, limits) if kind == "str" else _bytes(value)
        _cost_gate((len(raw), 1, 1, ""), limits)
        _work_gate(len(raw) + 1, limits)
        fingerprint = hashlib.sha256(kind.encode("ascii") + b":" + raw).hexdigest()
        return (kind, value), (len(raw), 1, 1, fingerprint)
    finally:
        raw = None


def _cost_gate(cost, limits):
    if cost[0] > limits.max_expanded_bytes:
        reason = "logical_expanded_bytes_limit_before_materialization"
    elif cost[1] > limits.max_input_visits:
        reason = "logical_expanded_visits_limit_before_materialization"
    elif cost[2] > limits.max_depth:
        reason = "logical_depth_limit_before_materialization"
    else:
        return
    raise DagHold(reason, {"expanded_bytes_lower_bound": cost[0],
        "expanded_visits_lower_bound": cost[1], "depth_lower_bound": cost[2], "limits": asdict(limits)})


def _work_gate(work, limits):
    if work > limits.max_work_units:
        raise DagHold("codec_total_work_limit_no_prefix", {"charged_work_units_lower_bound": work,
            "limits": asdict(limits)})


def _combine(node, costs, limits):
    # No child-cost bank: incremental gates precede a full logical expansion.
    try:
        kind, content = node
        size, visits, depth = 2, 1, 1
        sha = hashlib.sha256(kind.encode("ascii") + b":")
        for ordinal, value in enumerate(content):
            child = costs[value if kind == "list" else value[1]]
            if kind == "dict":
                key_raw = _string_bytes(value[0], limits)
                size += len(key_raw) + 1
                visits += 1
                sha.update(str(len(key_raw)).encode("ascii") + b":" + key_raw)
            size += child[0] + (1 if ordinal else 0)
            visits += child[1]
            depth = max(depth, child[2] + 1)
            _cost_gate((size, visits, depth, ""), limits)
            sha.update(child[3].encode("ascii"))
        result = (size, visits, depth, sha.hexdigest())
        _cost_gate(result, limits)
        return result
    finally:
        node = costs = content = child = key_raw = value = None


class _ScanState:
    __slots__ = ("active", "memo", "visits", "__weakref__")

    def __init__(self):
        self.active, self.memo, self.visits = set(), {}, 0

    def clear(self):
        self.active.clear()
        self.memo.clear()


def _container_gate(item, cls, limits):
    try:
        if len(item) > limits.max_input_visits:
            raise DagHold("input_container_count_limit", {"container_items": len(item)})
        minimum_size = 2 + (5 if cls is dict else 2) * len(item) - (1 if item else 0)
        minimum_visits = 1 + (2 if cls is dict else 1) * len(item)
        _cost_gate((minimum_size, minimum_visits, 1, ""), limits)
        _work_gate(minimum_size + minimum_visits, limits)
        if cls is dict and any(type(key) is not str for key in item):
            raise ValueError("exact_string_dictionary_keys_required")
    finally:
        item = None


def _scan_visit(item, depth, limits, state):
    state.visits += 1
    _work_gate(state.visits, limits)
    if state.visits > limits.max_input_visits or depth > limits.max_depth:
        raise DagHold("input_traversal_or_depth_limit", {"visited_values": state.visits,
            "current_depth": depth, "limits": asdict(limits)})
    cls = type(item)
    if cls not in (list, dict):
        _, result = _scalar(item, limits)
        _cost_gate(result, limits)
        return result
    identity = id(item)
    if identity in state.active:
        raise ValueError("cyclic_input_not_plain_JSON")
    if identity in state.memo:
        result = state.memo[identity]
        if depth - 1 + result[2] > limits.max_depth:
            raise DagHold("logical_depth_limit_before_materialization",
                {"depth_lower_bound": depth - 1 + result[2]})
        return result
    state.active.add(identity)
    keys = None
    try:
        _container_gate(item, cls, limits)
        size, count, height = 2, 1, 1
        sha = hashlib.sha256(("list" if cls is list else "dict").encode("ascii") + b":")
        keys = sorted(item) if cls is dict else None
        for ordinal in range(len(item)):
            if cls is dict:
                key = keys[ordinal]
                state.visits += 1
                key_raw = _string_bytes(key, limits)
                size += len(key_raw) + 1
                count += 1
                sha.update(str(len(key_raw)).encode("ascii") + b":" + key_raw)
                child = item[key]
            else:
                child = item[ordinal]
            child_cost = _scan_visit(child, depth + 1, limits, state)
            size += child_cost[0] + (1 if ordinal else 0)
            count += child_cost[1]
            height = max(height, child_cost[2] + 1)
            sha.update(child_cost[3].encode("ascii"))
            _cost_gate((size, count, height, ""), limits)
            _work_gate(size + count, limits)
        result = (size, count, height, sha.hexdigest())
        _cost_gate(result, limits)
        state.memo[identity] = result
        return result
    finally:
        state.active.discard(identity)
        if keys is not None:
            keys.clear()
        key_raw = child_cost = None


def _preflight(value, limits):
    """Identity DP; its memo is cleared on BaseException and retained traceback."""
    state = _ScanState()
    try:
        cost = _scan_visit(value, 1, limits, state)
        work = cost[0] + cost[1]
        _work_gate(work, limits)
        return cost, state.visits, work
    finally:
        state.clear()


def _cost_report(cost, actual, work):
    return {"expanded_bytes": cost[0], "expanded_visits": cost[1], "depth": cost[2],
        "structural_sha256": cost[3], "visited_input_values_and_keys": actual,
        "charged_work_units": work, "cost_scope": "full_logical_JSON_tree_with_child_occurrence_multiplicity",
        "codec_authority_only_not_archive_or_music": True}


def preflight_json(value, *, limits=None):
    return _cost_report(*_preflight(value, _limits(limits)))


def _node_record(index, node):
    children = None
    complete = False
    try:
        kind, content = node
        if kind == "list":
            children = list(content)
        elif kind == "dict":
            children = []
            for ordinal in range(len(content)):
                key, child = content[ordinal]
                children.append([key, child])
        else:
            return {"id": index, "type": kind, "value": content}
        result = {"id": index, "type": kind, "children": children}
        complete = True
        return result
    finally:
        if not complete and children is not None:
            children.clear()
        node = content = None


def _record(nodes, root):
    records = []
    complete = False
    try:
        for index in range(len(nodes)):
            node = nodes[index]
            records.append(_node_record(index, node))
        result = {"schema_name": SCHEMA_NAME, "schema_version": VERSION, "root": root,
            "nodes": records}
        complete = True
        return result
    finally:
        if not complete:
            records.clear()
        nodes = node = None


def _fragment_size(index, node):
    fragment = None
    try:
        fragment = _node_record(index, node)
        return len(_bytes(fragment)) + 1
    finally:
        if fragment is not None:
            if "children" in fragment:
                fragment["children"].clear()
            fragment.clear()
        node = None


def _encoded_size(fragment_bytes_with_commas, root):
    metadata = _bytes({"root": root, "schema_name": SCHEMA_NAME, "schema_version": VERSION})
    return len(b'{"nodes":[') + fragment_bytes_with_commas + len(metadata)


def _exchange_bytes(nodes, root):
    exchange = None
    try:
        exchange = _record(nodes, root)
        return _bytes(exchange)
    finally:
        if exchange is not None:
            exchange["nodes"].clear()
            exchange.clear()
        nodes = None


class _BuildState:
    __slots__ = ("nodes", "costs", "intern", "memo", "active", "visits", "stored",
        "base_work", "size_work", "__weakref__")

    def __init__(self, base_work=0):
        self.nodes, self.costs, self.intern, self.memo, self.active = [], [], {}, {}, set()
        self.visits = self.stored = 0
        self.base_work = base_work
        self.size_work = 0

    def clear(self):
        self.nodes.clear()
        self.costs.clear()
        self.intern.clear()
        self.memo.clear()
        self.active.clear()


def _string_width(value):
    width = 2
    for character in value:
        if character in ('"', "\\", "\b", "\f", "\n", "\r", "\t"):
            width += 2
        elif ord(character) < 32:
            width += 6
        else:
            try:
                width += len(character.encode("utf-8"))
            except UnicodeError as exc:
                raise ValueError("exact_plain_JSON_with_valid_UTF8_strings_required") from exc
    return width


def _fragment_bound(index, node, cost):
    """Exact compact sorted-key fragment length without a large record copy."""
    try:
        kind, content = node
        digits = len(str(index))
        if kind not in ("list", "dict"):
            size = len(b'{"id":') + digits + len(b',"type":') + len(kind) + 2 + len(b',"value":') + cost[0] + 1
            return size + 1, digits + len(kind) + 2
        size = len(b'{"children":[') + len(b'],"id":') + digits + len(b',"type":') + len(kind) + 2 + 1
        measured = digits + len(kind) + 2
        for ordinal, value in enumerate(content):
            child = value if kind == "list" else value[1]
            child_width = len(str(child))
            size += child_width + (1 if ordinal else 0)
            measured += child_width + 1
            if kind == "dict":
                size += _string_width(value[0]) + 3
                measured += len(value[0]) + 1
        return size + 1, measured
    finally:
        node = content = value = cost = None


def _append_node(node, cost, limits, state):
    try:
        if node in state.intern:
            return state.intern[node]
        if len(state.nodes) >= limits.max_nodes:
            raise DagHold("DAG_node_table_limit_no_prefix", {"nodes_lower_bound": len(state.nodes) + 1})
        index = len(state.nodes)
        fragment_size, measured = _fragment_bound(index, node, cost)
        next_stored = state.stored + fragment_size
        next_size_work = state.size_work + measured
        _work_gate(state.base_work + next_size_work + next_stored, limits)
        if next_stored > limits.max_encoded_bytes:
            raise DagHold("encoded_DAG_node_bytes_limit_no_prefix", {"encoded_bytes_lower_bound": next_stored})
        if _fragment_size(index, node) != fragment_size:
            raise ValueError("internal_exact_fragment_size_contract_mismatch")
        state.stored, state.size_work = next_stored, next_size_work
        state.nodes.append(node)
        state.costs.append(cost)
        state.intern[node] = index
        return index
    finally:
        node = cost = None


def _snapshot_visit(item, depth, limits, state):
    state.visits += 1
    _work_gate(state.stored + state.visits, limits)
    if state.visits > limits.max_input_visits or depth > limits.max_depth:
        raise DagHold("intern_traversal_or_depth_limit", {"visited_values": state.visits, "depth": depth})
    cls = type(item)
    if cls in (list, dict):
        identity = id(item)
        if identity in state.active:
            raise ValueError("cyclic_input_not_plain_JSON")
        if identity in state.memo:
            return state.memo[identity]
        state.active.add(identity)
        values, keys = [], None
        try:
            _container_gate(item, cls, limits)
            if cls is dict:
                keys = sorted(item)
                for key in keys:
                    state.visits += 1
                    values.append((key, _snapshot_visit(item[key], depth + 1, limits, state)))
            else:
                for child in item:
                    values.append(_snapshot_visit(child, depth + 1, limits, state))
            node = ("dict" if cls is dict else "list", tuple(values))
            cost = _combine(node, state.costs, limits)
            index = _append_node(node, cost, limits, state)
            state.memo[identity] = index
            return index
        finally:
            state.active.discard(identity)
            values.clear()
            if keys is not None:
                keys.clear()
            node = cost = None
    try:
        node, cost = _scalar(item, limits)
        _cost_gate(cost, limits)
        return _append_node(node, cost, limits, state)
    finally:
        node = cost = None


def _issue_proof(state, root, limits, stats):
    cost = state.costs[root]
    encoded = _encoded_size(state.stored, root)
    if encoded > limits.max_encoded_bytes:
        raise DagHold("encoded_DAG_bytes_limit_no_prefix", {"encoded_bytes": encoded, "limits": asdict(limits)})
    work = stats["charged_work_units"]
    _work_gate(work, limits)
    handle = object.__new__(JsonProof)
    _PROOFS[handle] = _owned_state(handle, state.nodes, state.costs, root, limits,
        {**stats, "table_nodes": len(state.nodes),
            "node_fragment_serialization_work_units": state.stored,
            "node_fragment_size_measurement_work_units": state.size_work,
            "encoding_work_upper_bound": 2 * encoded, "encoded_bytes": encoded,
            "expanded_bytes": cost[0], "expanded_visits": cost[1], "depth": cost[2],
            "structural_sha256": cost[3], "schema_name": SCHEMA_NAME, "schema_version": VERSION,
            "cost_scope": "full_logical_JSON_tree_with_child_occurrence_multiplicity",
            "original_logical_occurrences_preserved": True,
            "codec_authority_only_not_archive_or_music": True})
    return handle


def freeze_json(value, *, limits=None):
    """Pre-gated freeze binds its measured immutable content, not caller identity.

    Preflight and snapshot costs/fingerprint must agree. Once the snapshot exists,
    later caller mutation is irrelevant: no mutable tree is used by encode_proof.
    This is not an atomic cross-thread transaction or music/source validation.
    """
    limits = _limits(limits)
    before, pre_visits, _ = _preflight(value, limits)
    base_work = 2 * (before[0] + before[1])
    _work_gate(base_work, limits)
    state = _BuildState(base_work)
    try:
        root = _snapshot_visit(value, 1, limits, state)
        if state.costs[root] != before:
            raise ValueError("caller_input_changed_between_preflight_and_owned_snapshot")
        work = base_work + state.size_work + state.stored
        return _issue_proof(state, root, limits, {"origin": "owned_validated_immutable_JSON_snapshot",
            "preflight_visited_values_and_keys": pre_visits,
            "intern_visited_values_and_keys": state.visits, "input_guard_passes": 1,
            "snapshot_validation_passes": 1, "postflight_visited_values_and_keys": 0,
            "reserved_input_guard_and_intern_work_units": base_work,
            "incremental_work_units": work, "inherited_proof_creation_work_units": 0,
            "charged_work_units": work})
    finally:
        state.clear()


def _proof_admission(data, limits):
    try:
        _cost_gate(data["costs"][data["root"]], limits)
        if len(data["nodes"]) > limits.max_nodes:
            raise DagHold("DAG_node_table_limit_no_prefix", {"nodes_lower_bound": len(data["nodes"])})
        if data["stats"]["encoded_bytes"] > limits.max_encoded_bytes:
            raise DagHold("encoded_DAG_bytes_limit_no_prefix", {"encoded_bytes": data["stats"]["encoded_bytes"]})
    finally:
        data = None


def _issue(nodes, costs, root, limits, stats):
    raw = None
    try:
        encoded_size = _encoded_size(stats["node_fragment_serialization_work_units"], root)
        if encoded_size > limits.max_encoded_bytes:
            raise DagHold("encoded_DAG_bytes_limit_no_prefix", {"encoded_bytes": encoded_size, "limits": asdict(limits)})
        total_work = stats["charged_work_units"] + 2 * encoded_size
        _work_gate(total_work, limits)
        raw = _exchange_bytes(nodes, root)
        if len(raw) != encoded_size:
            raise ValueError("internal_exact_encoded_size_contract_mismatch")
        handle = object.__new__(JsonDag)
        _DAGS[handle] = _owned_state(handle, nodes, costs, root, limits,
            {**stats, "charged_work_units": total_work,
                "incremental_encoding_work_units": 2 * len(raw),
                "codec_sha256_work_units": len(raw),
                "final_exchange_serialization_work_units": len(raw), "table_nodes": len(nodes),
                "encoded_bytes": len(raw), "expanded_bytes": costs[root][0],
                "expanded_visits": costs[root][1], "depth": costs[root][2],
                "structural_sha256": costs[root][3], "codec_sha256": hashlib.sha256(raw).hexdigest(),
                "schema_name": SCHEMA_NAME, "schema_version": VERSION,
                "codec_authority_only_not_archive_or_music": True}, raw)
        return handle
    finally:
        nodes = costs = raw = None


def encode_proof(proof, *, limits=None):
    """Serialize the exact owned snapshot without remeasuring a mutable tree.

    charged_work_units includes proof creation; incremental_encoding_work_units
    is final exchange serialization plus its actual codec SHA pass (2*E), not
    a second freeze. encoded_bytes remains the exchange size E.
    """
    data = None
    try:
        data = _proof(proof)
        limits = data["limits"] if limits is None else _limits(limits)
        _proof_admission(data, limits)
        return _issue(data["nodes"], data["costs"], data["root"], limits,
            {**data["stats"], "origin": "encoded_owned_immutable_JSON_snapshot",
                "immutable_proof_creation_work_units": data["stats"]["charged_work_units"],
                "input_remeasurement_passes": 0})
    finally:
        data = proof = None


def encode_json(value, *, limits=None):
    proof = None
    try:
        proof = freeze_json(value, limits=limits)
        return encode_proof(proof)
    finally:
        # An encode failure may preserve this frame; do not retain a new proof.
        proof = None


def compose_proofs(fields, *, limits=None):
    """Build an exact dictionary of owned proof roots without tree revalidation.

    Work counts inherited proof construction once per supplied owned handle,
    every visited typed node/child edge, root key hashing, and exact copied node
    fragments. Expanded output gates still count every logical occurrence.
    """
    limits = _limits(limits)
    if type(fields) is not dict or any(type(key) is not str for key in fields):
        raise ValueError("exact_dictionary_of_owned_proofs_required")
    bindings = None
    data_by_handle, root_costs, root_content = {}, [], []
    state = _BuildState()
    mappings = {}
    try:
        _container_gate(fields, dict, limits)
        bindings = tuple((key, fields[key]) for key in sorted(fields))
        if any(type(key) is not str for key, _ in bindings):
            raise ValueError("exact_dictionary_of_owned_proofs_required")
        for key, handle in bindings:
            data = _proof(handle)
            data_by_handle[handle] = data
            root_content.append((key, len(root_costs)))
            root_costs.append(data["costs"][data["root"]])
        combined = _combine(("dict", tuple(root_content)), root_costs, limits)
        inherited = sum(data["stats"]["charged_work_units"] for data in data_by_handle.values())
        root_hash_work = 1 + len(bindings)
        for key, _ in bindings:
            root_hash_work += len(_string_bytes(key, limits)) + 64
        table_work = root_hash_work
        for data in data_by_handle.values():
            table_work += len(data["nodes"])
            for kind, content in data["nodes"]:
                if kind in ("list", "dict"):
                    table_work += len(content)
        state.base_work = inherited + table_work
        _work_gate(state.base_work, limits)  # Reserve reindex work before node copy.
        for handle, data in data_by_handle.items():
            mapping = []
            mappings[handle] = mapping
            for old_index, (kind, content) in enumerate(data["nodes"]):
                if kind == "list":
                    node = (kind, tuple(mapping[child] for child in content))
                elif kind == "dict":
                    node = (kind, tuple((key, mapping[child]) for key, child in content))
                else:
                    node = (kind, content)
                mapping.append(_append_node(node, data["costs"][old_index], limits, state))
        root_content.clear()
        for key, handle in bindings:
            data = data_by_handle[handle]
            root_content.append((key, mappings[handle][data["root"]]))
        root = _append_node(("dict", tuple(root_content)), combined, limits, state)
        incremental = table_work + state.size_work + state.stored
        return _issue_proof(state, root, limits, {"origin": "composed_owned_immutable_JSON_snapshots",
            "preflight_visited_values_and_keys": 0, "intern_visited_values_and_keys": table_work,
            "input_guard_passes": 0, "snapshot_validation_passes": 0,
            "postflight_visited_values_and_keys": 0, "input_remeasurement_passes": 0,
            "reserved_input_guard_and_intern_work_units": table_work,
            "typed_node_reindex_and_root_hash_work_units": table_work,
            "incremental_work_units": incremental,
            "inherited_proof_creation_work_units": inherited,
            "charged_work_units": inherited + incremental})
    finally:
        state.clear()
        for mapping in mappings.values():
            mapping.clear()
        mappings.clear()
        data_by_handle.clear()
        root_costs.clear()
        root_content.clear()
        data = handle = node = bindings = fields = None


def _closed(value, keys, name):
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value) != set(keys):
        raise ValueError("closed_exact_DAG_schema_required:" + name)


def import_record(record, *, limits=None):
    """Validate exchange only. This deliberately never issues a JsonProof."""
    limits = _limits(limits)
    _closed(record, ("schema_name", "schema_version", "root", "nodes"), "document")
    if (type(record["schema_name"]) is not str or type(record["schema_version"]) is not str
            or record["schema_name"] != SCHEMA_NAME or record["schema_version"] != VERSION
            or type(record["nodes"]) is not list):
        raise ValueError("exact_versioned_DAG_document_required")
    raw_nodes = record["nodes"]
    if not raw_nodes or len(raw_nodes) > limits.max_nodes:
        raise DagHold("whole_DAG_node_table_required_within_cap", {"table_nodes": len(raw_nodes)})
    state = _BuildState()
    reachable, pending, content, keys = set(), [], [], []
    reachability_visits = 0
    try:
        for i, item in enumerate(raw_nodes):
            if type(item) is not dict or type(item.get("type")) is not str:
                raise ValueError("exact_typed_DAG_node_required")
            kind = item["type"]
            _closed(item, ("id", "type", "children") if kind in ("list", "dict") else
                ("id", "type", "value"), "node")
            if type(item["id"]) is not int or item["id"] != i:
                raise ValueError("exact_ordered_node_id_required")
            state.visits += 1
            if state.visits > limits.max_input_visits:
                raise DagHold("DAG_table_traversal_limit", {"visited_node_fields": state.visits})
            _work_gate(state.stored + state.visits, limits)
            if kind in ("list", "dict"):
                values = item["children"]
                if type(values) is not list:
                    raise ValueError("exact_child_array_required")
                if state.visits + len(values) > limits.max_input_visits:
                    raise DagHold("DAG_table_traversal_limit",
                        {"visited_node_fields_lower_bound": state.visits + len(values)})
                _work_gate(state.stored + state.visits + len(values), limits)
                content.clear()
                keys.clear()
                for value in values:
                    state.visits += 1
                    _work_gate(state.stored + state.visits, limits)
                    if kind == "dict":
                        if type(value) is not list or len(value) != 2 or type(value[0]) is not str:
                            raise ValueError("exact_dictionary_key_child_pair_required")
                        key, child = value
                        _scalar(key, limits)
                        keys.append(key)
                        content.append((key, child))
                    else:
                        child = value
                        content.append(child)
                    if type(child) is not int or child < 0 or child >= i:
                        raise ValueError("bottom_up_existing_child_id_required_no_cycle_or_forward_ref")
                if kind == "dict" and (keys != sorted(keys) or len(keys) != len(set(keys))):
                    raise ValueError("unique_canonical_sorted_dictionary_keys_required")
                node = (kind, tuple(content))
                cost = _combine(node, state.costs, limits)
            else:
                node, cost = _scalar(item["value"], limits)
                if node[0] != kind:
                    raise ValueError("typed_scalar_kind_value_mismatch")
                _cost_gate(cost, limits)
            if node in state.intern:
                raise ValueError("canonical_DAG_cannot_contain_duplicate_structural_nodes")
            state.base_work = state.visits
            _append_node(node, cost, limits, state)
        root = record["root"]
        if type(root) is not int or root != len(state.nodes) - 1:
            raise ValueError("canonical_root_must_be_final_existing_node")
        pending.append(root)
        while pending:
            current = pending.pop()
            reachability_visits += 1
            _work_gate(state.stored + state.visits + reachability_visits, limits)
            if current in reachable:
                continue
            reachable.add(current)
            kind, node_content = state.nodes[current]
            if kind == "list":
                pending.extend(node_content)
            elif kind == "dict":
                pending.extend(child for _, child in node_content)
        if len(reachable) != len(state.nodes):
            raise ValueError("unreachable_foreign_DAG_nodes_not_allowed")
        cost = state.costs[root]
        work = cost[0] + cost[1] + state.size_work + state.stored + state.visits + reachability_visits
        _work_gate(work, limits)
        return _issue(state.nodes, state.costs, root, limits,
            {"origin": "validated_codec_exchange_not_domain_authority",
                "table_visited_node_fields": state.visits, "charged_work_units": work,
                "reachability_visits": reachability_visits,
                "node_fragment_serialization_work_units": state.stored,
                "node_fragment_size_measurement_work_units": state.size_work,
                "original_logical_occurrences_preserved": True})
    finally:
        state.clear()
        reachable.clear()
        pending.clear()
        content.clear()
        keys.clear()
        node = node_content = cost = None


def _node_at(data, path):
    try:
        if type(path) is not tuple or len(path) > data["limits"].max_depth:
            raise ValueError("bounded_exact_tuple_JSON_path_required")
        current = data["root"]
        for step in path:
            kind, content = data["nodes"][current]
            if kind == "list" and type(step) is int and 0 <= step < len(content):
                current = content[step]
            elif kind == "dict" and type(step) is str:
                lo, hi = 0, len(content)
                while lo < hi:
                    middle = (lo + hi) // 2
                    if content[middle][0] < step:
                        lo = middle + 1
                    else:
                        hi = middle
                if lo >= len(content) or content[lo][0] != step:
                    raise ValueError("exact_existing_dictionary_path_required")
                current = content[lo][1]
            else:
                raise ValueError("exact_list_index_or_dictionary_key_required_no_bool_alias")
        return current
    finally:
        data = content = None


def node_at(handle, path=()):
    try:
        return _node_at(_dag(handle), path)
    finally:
        handle = None


def proof_node_at(proof, path=()):
    try:
        return _node_at(_proof(proof), path)
    finally:
        proof = None


def _subtree_stats(data, path):
    try:
        node = _node_at(data, path)
        cost = data["costs"][node]
        return {"node_id": node, "type": data["nodes"][node][0], "expanded_bytes": cost[0],
            "expanded_visits": cost[1], "depth": cost[2], "structural_sha256": cost[3],
            "materialization_work_units": cost[0] + cost[1],
            "container_length": len(data["nodes"][node][1]) if data["nodes"][node][0] in ("list", "dict") else None}
    finally:
        data = cost = None


def subtree_stats(handle, path=()):
    try:
        return _subtree_stats(_dag(handle), path)
    finally:
        handle = None


def proof_subtree_stats(proof, path=()):
    try:
        return _subtree_stats(_proof(proof), path)
    finally:
        proof = None


def _decode_visit(nodes, index):
    result = None
    complete = False
    try:
        kind, content = nodes[index]
        if kind not in ("list", "dict"):
            return content
        result = [] if kind == "list" else {}
        if kind == "list":
            for child in content:
                result.append(_decode_visit(nodes, child))
        else:
            for key, child in content:
                result[key] = _decode_visit(nodes, child)
        complete = True
        return result
    finally:
        if not complete and result is not None:
            result.clear()
        nodes = content = None


def _value_at(data, path):
    try:
        root = _node_at(data, path)
        cost = data["costs"][root]
        _cost_gate(cost, data["limits"])
        _work_gate(cost[0] + cost[1], data["limits"])
        return _decode_visit(data["nodes"], root)
    finally:
        data = cost = None


def value_at(handle, path=()):
    """Per-call bounded materialization; caller owns cumulative read/pair work."""
    try:
        return _value_at(_dag(handle), path)
    finally:
        handle = None


def proof_value_at(proof, path=()):
    try:
        return _value_at(_proof(proof), path)
    finally:
        proof = None


def decode_json(handle):
    try:
        return value_at(handle)
    finally:
        handle = None


def _hash_visit(nodes, index, sha, omit_root_keys=()):
    try:
        kind, content = nodes[index]
        if kind not in ("list", "dict"):
            sha.update(_bytes(content))
            return
        sha.update(b"[" if kind == "list" else b"{")
        ordinal = 0
        for value in content:
            if kind == "dict" and value[0] in omit_root_keys:
                continue
            if ordinal:
                sha.update(b",")
            if kind == "dict":
                sha.update(_bytes(value[0]))
                sha.update(b":")
                child = value[1]
            else:
                child = value
            _hash_visit(nodes, child, sha)
            ordinal += 1
        sha.update(b"]" if kind == "list" else b"}")
    finally:
        nodes = content = sha = value = None


def proof_canonical_sha256(proof, path=(), *, limits=None, omit_root_keys=()):
    """Canonical JSON SHA, not Merkle SHA; charge exact bytes+visits to caller.

    Streams every expanded occurrence. It does not claim that snapshot validation
    or this hash pass was free and does not promote a codec proof to authority.
    """
    try:
        data = _proof(proof)
        limits = data["limits"] if limits is None else _limits(limits)
        root = _node_at(data, path)
        if (type(omit_root_keys) is not tuple or any(type(key) is not str for key in omit_root_keys)
                or len(set(omit_root_keys)) != len(omit_root_keys)):
            raise ValueError("exact_unique_tuple_root_key_omissions_required")
        if omit_root_keys:
            kind, content = data["nodes"][root]
            if kind != "dict" or not set(omit_root_keys).issubset(key for key, _ in content):
                raise ValueError("existing_dictionary_root_key_omissions_required")
        cost = data["costs"][root]
        _cost_gate(cost, limits)
        _work_gate(cost[0] + cost[1], limits)
        sha = hashlib.sha256()
        _hash_visit(data["nodes"], root, sha, omit_root_keys)
        return sha.hexdigest()
    finally:
        proof = data = content = cost = sha = None
