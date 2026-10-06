"""Lossless typed structural sharing, not music/archive/annotation authority.

Equal JSON subtrees may share representation nodes; original list occurrences,
ordinals, labels, aliases and reference strings remain exactly recoverable.
Input and decode costs count the expanded logical tree, not just stored nodes.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
from weakref import WeakKeyDictionary

SCHEMA_NAME = "musicanote-lossless-json-dag"
VERSION = "0.1.0"
_DAGS = WeakKeyDictionary()


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
        return _record(_dag(self)["nodes"], _dag(self)["root"])

    def json_bytes(self):
        return _dag(self)["raw"]

    def stats(self):
        return deepcopy(_dag(self)["stats"])


def _dag(handle):
    if type(handle) is not JsonDag or handle not in _DAGS:
        raise ValueError("owned_json_dag_required_not_external_summary")
    return _DAGS[handle]


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
    # A tiny encoded allowance cannot cause a many-times-larger escaped copy.
    if len(value) > limits.max_expanded_bytes:
        raise DagHold("scalar_expanded_bytes_limit", {"expanded_bytes_lower_bound": len(value)})
    if 6 * len(value) + 2 > limits.max_expanded_bytes:
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
                raise DagHold("scalar_expanded_bytes_limit_before_serialization", {"expanded_bytes_lower_bound": width})
    raw = _bytes(value)
    if len(raw) > limits.max_expanded_bytes:
        raise DagHold("scalar_expanded_bytes_limit_before_hash", {"expanded_bytes_lower_bound": len(raw)})
    return raw


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
    raw = _string_bytes(value, limits) if kind == "str" else _bytes(value)
    fingerprint = hashlib.sha256(kind.encode("ascii") + b":" + raw).hexdigest()
    return (kind, value), (len(raw), 1, 1, fingerprint)


def _combine(node, costs, limits):
    kind, content = node
    child_ids = content if kind == "list" else tuple(i for _, i in content)
    child_costs = [costs[i] for i in child_ids]
    visits = 1 + sum(c[1] for c in child_costs) + (len(content) if kind == "dict" else 0)
    size = 2 + sum(c[0] for c in child_costs) + max(len(content) - 1, 0)
    depth = 1 + max((c[2] for c in child_costs), default=0)
    sha = hashlib.sha256(kind.encode("ascii") + b":")
    for ordinal, child in enumerate(child_costs):
        if kind == "dict":
            key_raw = _string_bytes(content[ordinal][0], limits)
            size += len(key_raw) + 1
            sha.update(str(len(key_raw)).encode("ascii") + b":" + key_raw)
        sha.update(child[3].encode("ascii"))
    result = (size, visits, depth, sha.hexdigest())
    _cost_gate(result, limits)
    return result


def _cost_gate(cost, limits):
    diagnostics = {"expanded_bytes_lower_bound": cost[0], "expanded_visits_lower_bound": cost[1],
        "depth_lower_bound": cost[2], "limits": asdict(limits)}
    if cost[0] > limits.max_expanded_bytes:
        raise DagHold("logical_expanded_bytes_limit_before_materialization", diagnostics)
    if cost[1] > limits.max_input_visits:
        raise DagHold("logical_expanded_visits_limit_before_materialization", diagnostics)
    if cost[2] > limits.max_depth:
        raise DagHold("logical_depth_limit_before_materialization", diagnostics)


def _work_gate(work, limits):
    if work > limits.max_work_units:
        raise DagHold("codec_total_work_limit_no_prefix", {"charged_work_units_lower_bound": work,
            "limits": asdict(limits)})


def _preflight(value, limits):
    """Object-identity DP computes logical multiplicity without expanding it."""
    active, memo, actual_visits = set(), {}, 0
    def visit(item, depth):
        nonlocal actual_visits
        actual_visits += 1
        if actual_visits > limits.max_input_visits or depth > limits.max_depth:
            raise DagHold("input_traversal_or_depth_limit", {"visited_values": actual_visits,
                "current_depth": depth, "limits": asdict(limits)})
        cls = type(item)
        if cls not in (list, dict):
            _, result = _scalar(item, limits)
            _cost_gate(result, limits)
            return result
        identity = id(item)
        if identity in active:
            raise ValueError("cyclic_input_not_plain_JSON")
        if identity in memo:
            result = memo[identity]
            if depth - 1 + result[2] > limits.max_depth:
                raise DagHold("logical_depth_limit_before_materialization", {"depth_lower_bound": depth - 1 + result[2]})
            return result
        active.add(identity)
        try:
            size, count, height = 2, 1, 1
            sha = hashlib.sha256(("list" if cls is list else "dict").encode("ascii") + b":")
            if len(item) > limits.max_input_visits:
                raise DagHold("input_container_count_limit", {"container_items": len(item)})
            minimum_size = 2 + (5 if cls is dict else 2) * len(item) - (1 if item else 0)
            minimum_visits = 1 + (2 if cls is dict else 1) * len(item)
            _cost_gate((minimum_size, minimum_visits, 1, ""), limits)
            if cls is dict:
                if any(type(k) is not str for k in item):
                    raise ValueError("exact_string_dictionary_keys_required")
                keys = sorted(item)
                iterator = ((key, item[key]) for key in keys)
            else:
                iterator = ((None, child) for child in item)
            for ordinal, (key, child) in enumerate(iterator):
                if key is not None:
                    actual_visits += 1
                    key_raw = _string_bytes(key, limits)
                    size += len(key_raw) + 1
                    count += 1
                    sha.update(str(len(key_raw)).encode("ascii") + b":" + key_raw)
                child_cost = visit(child, depth + 1)
                size += child_cost[0] + (1 if ordinal else 0)
                count += child_cost[1]
                height = max(height, child_cost[2] + 1)
                sha.update(child_cost[3].encode("ascii"))
                _cost_gate((size, count, height, ""), limits)
            result = (size, count, height, sha.hexdigest())
            _cost_gate(result, limits)
            memo[identity] = result
            return result
        finally:
            active.remove(identity)
    result = visit(value, 1)
    work = result[0] + result[1]
    _work_gate(work, limits)
    return result, actual_visits, work


def preflight_json(value, *, limits=None):
    limits = _limits(limits)
    cost, actual, work = _preflight(value, limits)
    return {"expanded_bytes": cost[0], "expanded_visits": cost[1], "depth": cost[2],
        "structural_sha256": cost[3], "visited_input_values_and_keys": actual,
        "charged_work_units": work, "cost_scope": "full_logical_JSON_tree_with_child_occurrence_multiplicity",
        "codec_authority_only_not_archive_or_music": True}


def _node_record(index, node):
    kind, content = node
    if kind in ("list", "dict"):
        return {"id": index, "type": kind, "children": list(content) if kind == "list" else
            [[key, child] for key, child in content]}
    return {"id": index, "type": kind, "value": content}


def _record(nodes, root):
    return {"schema_name": SCHEMA_NAME, "schema_version": VERSION, "root": root,
        "nodes": [_node_record(i, node) for i, node in enumerate(nodes)]}


def _encoded_size(fragment_bytes_with_commas, root):
    metadata = _bytes({"root": root, "schema_name": SCHEMA_NAME, "schema_version": VERSION})
    return len(b'{"nodes":[') + fragment_bytes_with_commas + len(metadata)


def _issue(nodes, costs, root, limits, stats):
    encoded_size = _encoded_size(stats["node_fragment_serialization_work_units"], root)
    if encoded_size > limits.max_encoded_bytes:
        raise DagHold("encoded_DAG_bytes_limit_no_prefix", {"encoded_bytes": encoded_size, "limits": asdict(limits)})
    total_work = stats["charged_work_units"] + encoded_size
    _work_gate(total_work, limits)
    raw = _bytes(_record(nodes, root))
    if len(raw) != encoded_size:
        raise ValueError("internal_exact_encoded_size_contract_mismatch")
    handle = object.__new__(JsonDag)
    _DAGS[handle] = {"nodes": tuple(nodes), "costs": tuple(costs), "root": root, "limits": limits,
        "raw": raw, "stats": {**stats, "charged_work_units": total_work,
            "final_exchange_serialization_work_units": len(raw), "table_nodes": len(nodes), "encoded_bytes": len(raw),
            "expanded_bytes": costs[root][0], "expanded_visits": costs[root][1], "depth": costs[root][2],
            "structural_sha256": costs[root][3], "codec_sha256": hashlib.sha256(raw).hexdigest(),
            "schema_name": SCHEMA_NAME, "schema_version": VERSION,
            "codec_authority_only_not_archive_or_music": True}}
    return handle


def encode_json(value, *, limits=None):
    limits = _limits(limits)
    before, pre_visits, pre_work = _preflight(value, limits)
    base_work = 3 * (before[0] + before[1])
    _work_gate(base_work, limits)  # Both input guards + intern reserved before interning.
    nodes, costs, intern, physical_memo, active = [], [], {}, {}, set()
    visits, stored_bytes = 0, 0
    def visit(item, depth):
        nonlocal visits, stored_bytes
        visits += 1
        _work_gate(stored_bytes + visits, limits)
        if visits > limits.max_input_visits or depth > limits.max_depth:
            raise DagHold("intern_traversal_or_depth_limit", {"visited_values": visits, "depth": depth})
        cls = type(item)
        if cls in (list, dict):
            identity = id(item)
            if identity in active:
                raise ValueError("cyclic_input_not_plain_JSON")
            if identity in physical_memo:
                return physical_memo[identity]
            active.add(identity)
            try:
                if cls is dict:
                    if any(type(k) is not str for k in item):
                        raise ValueError("exact_string_dictionary_keys_required")
                    values = []
                    for key in sorted(item):
                        visits += 1
                        values.append((key, visit(item[key], depth + 1)))
                    node = ("dict", tuple(values))
                else:
                    node = ("list", tuple(visit(child, depth + 1) for child in item))
                cost = _combine(node, costs, limits)
            finally:
                active.remove(identity)
        else:
            node, cost = _scalar(item, limits)
            _cost_gate(cost, limits)
        if node in intern:
            index = intern[node]
        else:
            if len(nodes) >= limits.max_nodes:
                raise DagHold("DAG_node_table_limit_no_prefix", {"nodes_lower_bound": len(nodes) + 1})
            index = len(nodes)
            stored_bytes += len(_bytes(_node_record(index, node))) + 1
            _work_gate(base_work + stored_bytes, limits)
            if stored_bytes > limits.max_encoded_bytes:
                raise DagHold("encoded_DAG_node_bytes_limit_no_prefix", {"encoded_bytes_lower_bound": stored_bytes})
            nodes.append(node)
            costs.append(cost)
            intern[node] = index
        if cls in (list, dict):
            physical_memo[id(item)] = index
        return index
    root = visit(value, 1)
    if costs[root] != before:
        raise ValueError("caller_input_changed_between_preflight_and_intern")
    after, post_visits, post_work = _preflight(value, limits)
    if after != before:
        raise ValueError("caller_input_changed_during_codec_freeze")
    work = base_work + stored_bytes
    _work_gate(work, limits)
    return _issue(nodes, costs, root, limits, {"origin": "encoded_plain_JSON",
        "preflight_visited_values_and_keys": pre_visits, "intern_visited_values_and_keys": visits,
        "postflight_visited_values_and_keys": post_visits, "input_guard_passes": 2,
        "charged_work_units": work, "reserved_input_guard_and_intern_work_units": base_work,
        "node_fragment_serialization_work_units": stored_bytes,
        "original_logical_occurrences_preserved": True})


def _closed(value, keys, name):
    if type(value) is not dict or any(type(k) is not str for k in value) or set(value) != set(keys):
        raise ValueError("closed_exact_DAG_schema_required:" + name)


def import_record(record, *, limits=None):
    """Validate a codec exchange only; never promote it to domain authority."""
    limits = _limits(limits)
    _closed(record, ("schema_name", "schema_version", "root", "nodes"), "document")
    if (type(record["schema_name"]) is not str or type(record["schema_version"]) is not str
            or record["schema_name"] != SCHEMA_NAME or record["schema_version"] != VERSION
            or type(record["nodes"]) is not list):
        raise ValueError("exact_versioned_DAG_document_required")
    raw_nodes = record["nodes"]
    if not raw_nodes or len(raw_nodes) > limits.max_nodes:
        raise DagHold("whole_DAG_node_table_required_within_cap", {"table_nodes": len(raw_nodes)})
    nodes, costs, unique, visits, stored_bytes = [], [], set(), 0, 0
    for i, item in enumerate(raw_nodes):
        if type(item) is not dict or type(item.get("type")) is not str:
            raise ValueError("exact_typed_DAG_node_required")
        kind = item["type"]
        _closed(item, ("id", "type", "children") if kind in ("list", "dict") else ("id", "type", "value"), "node")
        if type(item["id"]) is not int or item["id"] != i:
            raise ValueError("exact_ordered_node_id_required")
        visits += 1
        if visits > limits.max_input_visits:
            raise DagHold("DAG_table_traversal_limit", {"visited_node_fields": visits})
        _work_gate(stored_bytes + visits, limits)
        if kind in ("list", "dict"):
            values = item["children"]
            if type(values) is not list:
                raise ValueError("exact_child_array_required")
            if visits + len(values) > limits.max_input_visits:
                raise DagHold("DAG_table_traversal_limit", {"visited_node_fields_lower_bound": visits + len(values)})
            _work_gate(stored_bytes + visits + len(values), limits)
            content, keys = [], []
            for value in values:
                visits += 1
                _work_gate(stored_bytes + visits, limits)
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
                if visits > limits.max_input_visits:
                    raise DagHold("DAG_table_traversal_limit", {"visited_node_fields": visits})
            if kind == "dict" and (keys != sorted(keys) or len(keys) != len(set(keys))):
                raise ValueError("unique_canonical_sorted_dictionary_keys_required")
            node = (kind, tuple(content))
            cost = _combine(node, costs, limits)
        else:
            node, cost = _scalar(item["value"], limits)
            if node[0] != kind:
                raise ValueError("typed_scalar_kind_value_mismatch")
            _cost_gate(cost, limits)
        if node in unique:
            raise ValueError("canonical_DAG_cannot_contain_duplicate_structural_nodes")
        stored_bytes += len(_bytes(_node_record(i, node))) + 1
        _work_gate(stored_bytes + visits, limits)
        if stored_bytes > limits.max_encoded_bytes:
            raise DagHold("encoded_DAG_node_bytes_limit_no_prefix", {"encoded_bytes_lower_bound": stored_bytes})
        unique.add(node)
        nodes.append(node)
        costs.append(cost)
    root = record["root"]
    if type(root) is not int or root != len(nodes) - 1:
        raise ValueError("canonical_root_must_be_final_existing_node")
    reachable, pending, reachability_visits = set(), [root], 0
    while pending:
        current = pending.pop()
        reachability_visits += 1
        _work_gate(stored_bytes + visits + reachability_visits, limits)
        if current in reachable:
            continue
        reachable.add(current)
        kind, content = nodes[current]
        if kind == "list":
            pending.extend(content)
        elif kind == "dict":
            pending.extend(i for _, i in content)
    if len(reachable) != len(nodes):
        raise ValueError("unreachable_foreign_DAG_nodes_not_allowed")
    work = costs[root][0] + costs[root][1] + stored_bytes + visits + reachability_visits
    _work_gate(work, limits)
    return _issue(nodes, costs, root, limits, {"origin": "validated_codec_exchange_not_domain_authority",
        "table_visited_node_fields": visits, "charged_work_units": work,
        "reachability_visits": reachability_visits,
        "node_fragment_serialization_work_units": stored_bytes,
        "original_logical_occurrences_preserved": True})


def node_at(handle, path=()):
    data = _dag(handle)
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


def subtree_stats(handle, path=()):
    data = _dag(handle)
    node = node_at(handle, path)
    cost = data["costs"][node]
    return {"node_id": node, "type": data["nodes"][node][0], "expanded_bytes": cost[0],
        "expanded_visits": cost[1], "depth": cost[2], "structural_sha256": cost[3]}


def value_at(handle, path=()):
    """Bounded per-call materialization; caller owns cumulative pair/read work."""
    data = _dag(handle)
    root = node_at(handle, path)
    cost = data["costs"][root]
    _cost_gate(cost, data["limits"])
    _work_gate(cost[0] + cost[1], data["limits"])
    def decode(index):
        kind, content = data["nodes"][index]
        if kind == "list":
            return [decode(child) for child in content]
        if kind == "dict":
            return {key: decode(child) for key, child in content}
        return content
    return decode(root)


def decode_json(handle):
    return value_at(handle)
