"""A lossless factorized index and lazy queries over frozen fmeh proposals.

Logical tuples are represented by catalogue products, not eagerly allocated
paths. Profile descriptors are shared assumptions, not already evaluated facts.
An opaque prepared session owns immutable verified source/index snapshots.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import hmac
import json
from pathlib import Path
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import factor_expanded_hypotheses as frozen
from . import factor_expanded_scope as expanded
from . import harmony_candidate_catalog as catalog
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "factor-indexed-hypotheses-0.1.0"
PREFIX = "fmiidx_"
PROFILE_PREFIX = "fmiprofile_"
QUERY_PREFIX = "fmiquery_"
BUNDLE_PREFIX = "fmibundle_"
TUPLE_PREFIX = "fmituple_"
ASSESSMENT_PREFIX = "fmiassess_"
_SESSIONS = WeakKeyDictionary()
_PROFILE_CACHES = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _flags():
    return {**frozen._flags(), "voice_identity_confirmed": False,
        "source_artifact_authority_established": False,
        "all_logical_tuples_evaluated": False, "old_statuses_modified": False,
        "Cartesian_paths_materialized": False}


def _contract():
    modules = (frozen, expanded, catalog)
    sources = [{"module": __name__, "sha256": sha256(Path(__file__).read_bytes()).hexdigest()}]
    sources.extend({"module": module.__name__, "sha256": sha256(Path(module.__file__).read_bytes()).hexdigest()}
                   for module in modules)
    return {"version": VERSION, "sources": sources,
        "frozen_contract": frozen._contract(), "expanded_contract": expanded._contract()}


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_index_limit_required:" + name)


def _encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _same(left, right):
    """Canonical equality rejects Python's bool/int and int/float aliases."""
    return _encoded(left) == _encoded(right)


def _seal(body, prefix):
    return frozen._seal(body, prefix)


def _ref(record):
    return frozen._ref(record)


def _closed(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("closed_index_contract_required:" + name)


def _semantic(variant):
    return {"span": deepcopy(variant["span"]), "root": deepcopy(variant["root"]),
        "members": deepcopy(variant["members"]), "blockers": deepcopy(variant["blockers"])}


def _descriptor(scope, variant):
    semantic = _semantic(variant)
    return _seal({"version": VERSION, "scope_ref": _ref(scope),
        "semantic_fingerprint": digest(semantic), "semantic_input": semantic,
        "status": "lazy_profile_descriptor_not_evaluated",
        "profile_materialized": False, "flags": _flags()}, PROFILE_PREFIX)


def _source_supplier_hold(scope, old_group, entries):
    reasons = []
    if not scope["context_sound_inventory_complete"]:
        reasons.append("expanded_literal_source_sound_inventory_incomplete")
    if any(entry["supplier_catalog"] is None for entry in entries):
        reasons.append("stored_supplier_catalog_unavailable")
    # Only the old path-allocation cap is lifted in this NEW representation.
    reasons.extend(reason for reason in old_group["reasons"]
                   if reason != "complete_partition_path_group_exceeds_budget_no_pruning")
    return sorted(set(reasons))


def _check_inputs(ir, scope, hypotheses, *, catalog_checks=True):
    """Intrinsic producer lineage, not a claim of absent parent-file trust."""
    before = digest([ir, scope, hypotheses])
    current_contract = _contract()
    expanded.check_scope(scope, ir=ir)
    frozen._check(hypotheses, frozen.PREFIX)
    _closed(hypotheses, {"version", "contract", "binding", "scope_ref", "analysis_span", "cut_times",
        "catalog_inventory", "path_groups", "keys", "resource_limits", "status", "reasons", "flags",
        "summary", "limits", "record_id", "record_sha256"}, "frozen_hypotheses")
    if any(type(hypotheses[name]) is not list for name in
           ("cut_times", "catalog_inventory", "path_groups", "keys", "reasons", "limits")):
        raise ValueError("frozen_record_list_inventory_required")
    if (hypotheses["version"] != frozen.VERSION or not _same(hypotheses["contract"], frozen._contract())
            or not _same(hypotheses["scope_ref"], _ref(scope)) or not _same(hypotheses["binding"], scope["binding"])
            or not _same(hypotheses["analysis_span"], scope["analysis_span"])
            or not _same(hypotheses["flags"], frozen._flags())
            or any(type(v) is not bool for v in hypotheses["flags"].values())):
        raise ValueError("stale_foreign_or_promoting_frozen_hypotheses")
    limits = hypotheses["resource_limits"]
    _closed(limits, {"max_catalogs", "path_budget"}, "frozen_limits")
    for name, value in limits.items():
        _integer(value, name)
    if limits["path_budget"] == 0:
        raise ValueError("positive_frozen_path_budget_required")
    start, end = span_bounds(scope["analysis_span"])
    cuts = sorted({f(sound["span"][side]) for sound in scope["sound_facts"]
                   for side in ("start", "end") if start < f(sound["span"][side]) < end})
    if not _same(hypotheses["cut_times"], [q(cut) for cut in cuts]):
        raise ValueError("frozen_observed_cut_inventory_mismatch")
    spans = sorted({(start, end)} | {(start, cut) for cut in cuts} | {(cut, end) for cut in cuts})
    if not _same([entry["span"] for entry in hypotheses["catalog_inventory"]],
                 [frozen._span(a, b) for a, b in spans]):
        raise ValueError("frozen_catalogue_span_inventory_mismatch")
    supply_hold = len(spans) > limits["max_catalogs"] or not scope["context_sound_inventory_complete"]
    entries = {}
    sounds = {sound["sounding_event_id"]: sound for sound in ir["sounding_events"]}
    for entry in hypotheses["catalog_inventory"]:
        _closed(entry, {"catalog_id", "span", "supplier_catalog", "candidate_count", "variant_count",
                        "variants", "status", "reasons"}, "frozen_catalogue_entry")
        if type(entry["variants"]) is not list or type(entry["reasons"]) is not list:
            raise ValueError("frozen_catalogue_list_inventory_required")
        expected_id = "fmehcat_" + digest([_ref(scope), entry["span"]])[:24]
        if entry["catalog_id"] != expected_id or expected_id in entries:
            raise ValueError("foreign_or_duplicate_frozen_catalogue")
        entries[expected_id] = entry
        if supply_hold:
            if (entry["supplier_catalog"] is not None or entry["candidate_count"] is not None
                    or entry["variant_count"] is not None or entry["variants"]):
                raise ValueError("partial_frozen_supplier_materialization_forbidden")
            source_hold = not scope["context_sound_inventory_complete"]
            if (entry["status"] != ("source_scope_abstention" if source_hold else "whole_group_budget_abstention")
                    or entry["reasons"] != (["expanded_literal_source_sound_inventory_incomplete"] if source_hold
                                           else ["complete_catalog_inventory_exceeds_budget_no_pruning"])):
                raise ValueError("frozen_supplier_hold_metadata_mismatch")
            continue
        supplier = entry["supplier_catalog"]
        if supplier is None or not _same(supplier["span"], entry["span"]) or not _same(supplier["context_span"], scope["analysis_span"]):
            raise ValueError("stored_frozen_supplier_required")
        if catalog_checks:
            catalog.validate(supplier)
        base = supplier["providers"]["base"]
        a, b = span_bounds(entry["span"])
        units = {sid: {"pitch": sound["pitch"], "span": sound["span"], "source_note_ids": sound["source_note_ids"]}
                 for sid, sound in sounds.items()
                 if f(sound["span"]["start"]) < b and f(sound["span"]["end"]) > a}
        if not _same(base["event_units"], units):
            raise ValueError("frozen_catalogue_literal_source_units_mismatch")
        expected = []
        for candidate_index, candidate in enumerate(supplier["candidates"]):
            alternatives = range(len(candidate["spelling_alternatives"])) if candidate["spelling_alternatives"] else [None]
            expected.extend(frozen._variant(scope, entry, candidate, candidate_index, alternative)
                            for alternative in alternatives)
        if (not _same(entry["variants"], expected) or not _same(entry["candidate_count"], len(supplier["candidates"]))
                or not _same(entry["variant_count"], len(expected)) or entry["status"] != "ready" or entry["reasons"]):
            raise ValueError("dropped_modified_or_duplicate_frozen_variant_origin")
    partitions = [[frozen._span(start, end)]] + [[frozen._span(start, cut), frozen._span(cut, end)] for cut in cuts]
    if not _same([group["partition"] for group in hypotheses["path_groups"]], partitions):
        raise ValueError("frozen_complete_partition_inventory_mismatch")
    by_span = {digest(entry["span"]): entry for entry in entries.values()}
    for group_index, group in enumerate(hypotheses["path_groups"]):
        _closed(group, {"group_id", "kind", "cut", "partition", "catalog_refs", "total_paths", "planned_paths",
                        "status", "reasons", "paths"}, "frozen_path_group")
        if any(type(group[name]) is not list for name in ("partition", "catalog_refs", "reasons", "paths")):
            raise ValueError("frozen_group_list_inventory_required")
        kind = "full_hold" if group_index == 0 else "two_segment"
        cut = None if group_index == 0 else cuts[group_index - 1]
        expected_id = "fmehgroup_" + digest([_ref(scope), kind, cut and q(cut)])[:24]
        group_entries = [by_span[digest(span)] for span in group["partition"]]
        count = None if supply_hold else 1
        if count is not None:
            for entry in group_entries:
                count *= entry["variant_count"]
        if (group["group_id"] != expected_id or group["kind"] != kind
                or not _same(group["cut"], None if cut is None else q(cut))
                or group["catalog_refs"] != [entry["catalog_id"] for entry in group_entries]
                or not _same(group["planned_paths"], count) or not _same(group["total_paths"], count)):
            raise ValueError("frozen_group_identity_or_product_mismatch")
        if not supply_hold:
            over = count > limits["path_budget"]
            expected_reasons = ["complete_partition_path_group_exceeds_budget_no_pruning"] if over else []
            if group["status"] != ("whole_group_budget_abstention" if over else "ready") or group["reasons"] != expected_reasons:
                raise ValueError("frozen_group_materialization_status_mismatch")
            if len(group["paths"]) != (0 if over else count):
                raise ValueError("partial_or_dropped_frozen_materialized_paths")
        else:
            source_hold = not scope["context_sound_inventory_complete"]
            if (group["paths"] or group["status"] != ("source_scope_abstention" if source_hold else "whole_group_budget_abstention")
                    or group["reasons"] != (["expanded_literal_source_sound_inventory_incomplete"] if source_hold
                                           else ["complete_catalog_inventory_unavailable"])):
                raise ValueError("frozen_group_supplier_hold_metadata_mismatch")
        seen = set()
        expected_products = product(*(entry["variants"] for entry in group_entries))
        for path, expected_segments in zip(group["paths"], expected_products):
            frozen._check(path, frozen.PATH_PREFIX)
            if type(path["segments"]) is not list:
                raise ValueError("frozen_path_segment_list_required")
            tuple_ids = tuple(segment["record_id"] for segment in path["segments"])
            if tuple_ids in seen or len(tuple_ids) != len(group_entries):
                raise ValueError("duplicate_or_malformed_frozen_materialized_tuple")
            seen.add(tuple_ids)
            if tuple_ids != tuple(segment["record_id"] for segment in expected_segments):
                raise ValueError("frozen_materialized_tuple_order_mismatch")
            for segment, entry in zip(path["segments"], group_entries):
                if not any(_same(segment, variant) for variant in entry["variants"]):
                    raise ValueError("foreign_frozen_materialized_segment")
            expected_path = frozen._seal({"version": frozen.VERSION, "binding": deepcopy(scope["binding"]),
                "scope_ref": _ref(scope), "analysis_span": deepcopy(scope["analysis_span"]),
                "group_id": group["group_id"], "partition": deepcopy(group["partition"]),
                "segments": deepcopy(path["segments"]),
                "provenance": {"kind": "complete_inclusive_catalog_partition_hypothesis",
                               "source_statement_ref": None, "source_path": None}, "flags": frozen._flags()}, frozen.PATH_PREFIX)
            if not _same(path, expected_path):
                raise ValueError("modified_frozen_materialized_path")
    if not _same(hypotheses["keys"], frozen._key_candidates(ir, scope)):
        raise ValueError("frozen_signature_key_inventory_mismatch")
    groups = hypotheses["path_groups"]
    reasons = sorted({reason for group in groups for reason in group["reasons"]})
    metadata = {
        "status": "source_scope_abstention" if not scope["context_sound_inventory_complete"] else "with_whole_group_budget_holds" if reasons else "ready",
        "reasons": reasons,
        "summary": {"observed_cuts": len(cuts), "catalog_spans": len(spans),
            "supplier_candidates": None if supply_hold else sum(entry["candidate_count"] for entry in entries.values()),
            "spelling_variants": None if supply_hold else sum(entry["variant_count"] for entry in entries.values()),
            "path_groups": len(groups), "path_group_statuses": dict(Counter(group["status"] for group in groups)),
            "complete_paths": sum(len(group["paths"]) for group in groups), "key_hypotheses": len(hypotheses["keys"])},
        "limits": ["Full hold and every one-cut partition only; not exhaustive segmentation.",
            "Every supplier origin and spelling alternative survives; no PC-set deduplication.",
            "Signature-compatible reference forms and unknown are assumptions, not inferred local keys.",
            "SOURCE provenance is absent; the pure builder does not admit or reclassify old parent artifacts."]}
    if not _same({name: hypotheses[name] for name in metadata}, metadata):
        raise ValueError("frozen_top_level_accounting_or_policy_mismatch")
    if before != digest([ir, scope, hypotheses]) or not _same(current_contract, _contract()):
        raise ValueError("index_inputs_or_current_code_changed_during_validation")
    return entries


def validate_inputs_fresh(ir, scope, hypotheses):
    """Optional expensive provider replay; never implicitly done per query."""
    return frozen.validate_hypotheses(ir, scope, hypotheses)


def _group(scope, old, entries, key_count, index_hold):
    sources = [entries[ref] for ref in old["catalog_refs"]]
    hold = _source_supplier_hold(scope, old, sources)
    count = None if hold else 1
    if count is not None:
        for entry in sources:
            count *= entry["variant_count"]
    slots = [{"catalog_id": entry["catalog_id"], "span": deepcopy(entry["span"]),
              "variant_ids": [variant["record_id"] for variant in entry["variants"]]} for entry in sources]
    reasons = list(hold)
    if index_hold:
        reasons.append("whole_variant_index_exceeds_budget_no_prefix")
    body = {"group_id": old["group_id"], "kind": old["kind"], "cut": deepcopy(old["cut"]),
        "partition": deepcopy(old["partition"]), "slots": slots,
        "old_status": old["status"], "old_reasons": deepcopy(old["reasons"]),
        "logical_path_count": count, "total_paths": count,
        "logical_tuple_count": None if count is None else count * key_count,
        "logical_function_count": None if count is None else count * key_count * len(slots) * 10,
        "status": "source_supplier_hold" if hold else "whole_index_budget_hold" if index_hold else "ready_factorized_group",
        "reasons": sorted(set(reasons))}
    return {"indexed_group_id": "fmigroup_" + digest([_ref(scope), body])[:24], **body}


def _body(scope, hypotheses, entries, max_variants):
    variant_count = sum(len(entry["variants"]) for entry in entries.values())
    hold = variant_count > max_variants
    variants, descriptors, semantic_to_descriptor = [], [], {}
    catalogs = []
    for entry in hypotheses["catalog_inventory"]:
        catalogs.append({"catalog_id": entry["catalog_id"], "span": deepcopy(entry["span"]),
            "candidate_count": entry["candidate_count"], "variant_count": entry["variant_count"],
            "variant_ids": [variant["record_id"] for variant in entry["variants"]],
            "old_status": entry["status"], "old_reasons": deepcopy(entry["reasons"]),
            "supplier_sha256": None if entry["supplier_catalog"] is None else digest(entry["supplier_catalog"]),
            "supplier_materialized": entry["supplier_catalog"] is not None})
        if not hold:
            for variant in entry["variants"]:
                semantic = digest(_semantic(variant))
                descriptor = semantic_to_descriptor.get(semantic)
                if descriptor is None:
                    descriptor = _descriptor(scope, variant)
                    semantic_to_descriptor[semantic] = descriptor
                    descriptors.append(descriptor)
                variants.append({"variant_id": variant["record_id"], "segment_ref": variant["segment_id"],
                    "catalog_id": entry["catalog_id"], "profile_ref": _ref(descriptor),
                    "variant": deepcopy(variant)})
    groups = [_group(scope, old, entries, len(hypotheses["keys"]), hold) for old in hypotheses["path_groups"]]
    paths = sum(group["logical_path_count"] or 0 for group in groups)
    tuples = sum(group["logical_tuple_count"] or 0 for group in groups)
    universe_body = {"scope_ref": _ref(scope), "hypotheses_ref": _ref(hypotheses),
        "group_refs": [{"group_id": group["group_id"], "indexed_group_id": group["indexed_group_id"]} for group in groups],
        "key_refs": [_ref(key) for key in hypotheses["keys"]],
        "logical_paths": paths, "logical_tuples": tuples,
        "unknown_product_groups": sum(group["logical_path_count"] is None for group in groups),
        "count_semantics": "known_product_subtotals_plus_explicit_unknown_group_denominator_not_unknown_as_zero",
        "representation": "all_complete_catalogue_products_not_materialized_or_selected_paths"}
    universe = _seal(universe_body, "fmiuniverse_")
    return {"version": VERSION, "contract": _contract(), "binding": deepcopy(scope["binding"]),
        "scope_ref": _ref(scope), "hypotheses_ref": _ref(hypotheses),
        "analysis_span": deepcopy(scope["analysis_span"]), "catalog_inventory": catalogs,
        "variant_inventory": variants, "profile_inventory": descriptors,
        "path_groups": groups, "keys": deepcopy(hypotheses["keys"]), "universe": universe,
        "resource_limits": {"max_variants": max_variants},
        "status": "whole_index_budget_hold" if hold else "factorized_index_with_supplier_holds" if any(g["reasons"] for g in groups) else "ready_factorized_index",
        "reasons": ["whole_variant_index_exceeds_budget_no_prefix"] if hold else sorted({r for g in groups for r in g["reasons"]}),
        "summary": {"catalog_spans": len(catalogs), "supplier_candidates": sum(entry["candidate_count"] or 0 for entry in catalogs),
            "unknown_supplier_catalogs": sum(entry["candidate_count"] is None for entry in catalogs),
            "supplier_count_semantics": "stored_known_candidate_subtotal_with_explicit_unknown_catalogue_denominator",
            "stored_variants": variant_count, "indexed_variants": len(variants),
            "shared_profile_descriptors": len(descriptors), "profiles_materialized": 0,
            "groups": len(groups), "group_statuses": dict(Counter(g["status"] for g in groups)),
            "logical_paths": paths, "logical_path_key_tuples": tuples,
            "logical_function_shapes": sum(group["logical_function_count"] or 0 for group in groups),
            "unknown_product_groups": universe_body["unknown_product_groups"],
            "key_hypotheses": len(hypotheses["keys"]), "queried_tuples": 0},
        "selected": None, "preferred": None, "confidence": None, "flags": _flags(),
        "validation_semantics": "intrinsic_current_producer_lineage_and_full_IR_scope_replay_not_parent_file_authority",
        "limits": ["Logical catalogue products are preserved, not exhaustively evaluated.",
            "Profile descriptors are lazy assumptions; only requested profiles become computed observations.",
            "Only historical path allocation holds are lifted in this new index; old records/statuses remain unchanged.",
            "No old path/completion is invented, ranked, selected or inserted in an inventory.",
            "Byte/RSS and opaque-session lifetime are not bounded by max_variants."]}


def build_index(ir, scope, hypotheses, *, max_variants=65536):
    _integer(max_variants, "max_variants")
    before = digest([ir, scope, hypotheses])
    contract = _contract()
    entries = _check_inputs(ir, scope, hypotheses)
    result = _seal(_body(scope, hypotheses, entries, max_variants), PREFIX)
    if before != digest([ir, scope, hypotheses]) or not _same(contract, _contract()):
        raise ValueError("index_inputs_or_current_code_changed_during_build")
    return result


def validate_index(ir, scope, hypotheses, index):
    frozen._check(index, PREFIX)
    _closed(index["resource_limits"], {"max_variants"}, "index_limits")
    if not _same(index, build_index(ir, scope, hypotheses, **index["resource_limits"])):
        raise ValueError("stale_foreign_or_modified_factorized_index")
    return True


def _check_index_lineage(ir, scope, hypotheses, index):
    """Check all lightweight descriptors/origin associations, no profile work."""
    frozen._check(index, PREFIX)
    if (index["version"] != VERSION or index["contract"] != _contract()
            or index["scope_ref"] != _ref(scope) or index["hypotheses_ref"] != _ref(hypotheses)
            or index["binding"] != scope["binding"] or index["analysis_span"] != scope["analysis_span"]
            or index["flags"] != _flags() or any(type(v) is not bool for v in index["flags"].values())
            or any(index[name] is not None for name in ("selected", "preferred", "confidence"))):
        raise ValueError("stale_foreign_or_promoting_factorized_index")
    _closed(index["resource_limits"], {"max_variants"}, "index_limits")
    _integer(index["resource_limits"]["max_variants"], "max_variants")
    entries = _check_inputs(ir, scope, hypotheses)
    # Compare descriptor lineage directly, without build_index, catalog.propose,
    # frozen._profile, or a Cartesian tuple traversal.
    expected = _body(scope, hypotheses, entries, index["resource_limits"]["max_variants"])
    actual = {k: v for k, v in index.items() if k not in ("record_id", "record_sha256")}
    if not _same(actual, expected):
        raise ValueError("index_origin_profile_partition_or_denominator_lineage_mismatch")
    return True


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


class _PreparedIndex:
    __slots__ = ("__weakref__",)


@dataclass(frozen=True)
class _SessionState:
    data: object
    lookups: object
    contract_sha256: str
    authentication: bytes


def _authentication(handle, state):
    return hmac.digest(_SECRET, _encoded([id(handle), id(state), id(state.data), id(state.lookups),
                                         state.contract_sha256]), "sha256")


def _session(handle):
    if type(handle) is not _PreparedIndex or handle not in _SESSIONS:
        raise ValueError("internally_issued_prepared_index_required")
    state = _SESSIONS[handle]
    if (type(state) is not _SessionState or not isinstance(state.data, MappingProxyType)
            or not isinstance(state.lookups, MappingProxyType)
            or state.contract_sha256 != digest(_contract())
            or not hmac.compare_digest(state.authentication, _authentication(handle, state))):
        raise ValueError("prepared_index_contract_or_owned_state_changed")
    return state


def prepare_index(ir, scope, hypotheses, index):
    """Own immutable verified snapshots; no caller hash or mutable alias trust."""
    before = digest([ir, scope, hypotheses, index])
    contract = _contract()
    _check_index_lineage(ir, scope, hypotheses, index)
    data = _freeze({"scope": deepcopy(scope), "index": deepcopy(index)})
    lookups = _freeze({"variants": {row["variant_id"]: i for i, row in enumerate(index["variant_inventory"])},
        "profiles": {row["record_id"]: i for i, row in enumerate(index["profile_inventory"])},
        "groups": {row["group_id"]: i for i, row in enumerate(index["path_groups"])},
        "keys": {row["record_id"]: i for i, row in enumerate(index["keys"])}})
    if before != digest([ir, scope, hypotheses, index]) or not _same(contract, _contract()):
        raise ValueError("index_inputs_or_current_code_changed_during_prepare")
    handle = _PreparedIndex()
    state = _SessionState(data, lookups, digest(_contract()), b"")
    object.__setattr__(state, "authentication", _authentication(handle, state))
    _SESSIONS[handle] = state
    _PROFILE_CACHES[handle] = {}
    return handle


def _computed_profile(handle, state, variant_row):
    index = state.data["index"]
    profile_id = variant_row["profile_ref"]["record_id"]
    descriptor = _thaw(index["profile_inventory"][state.lookups["profiles"][profile_id]])
    variant = _thaw(variant_row["variant"])
    scope = _thaw(state.data["scope"])
    if not _same(descriptor, _descriptor(scope, variant)) or not _same(_ref(descriptor), _thaw(variant_row["profile_ref"])):
        raise ValueError("selected_profile_descriptor_association_mismatch")
    cache = _PROFILE_CACHES[handle]
    entry = cache.get(profile_id)
    if entry is None:
        profile = frozen._profile(scope, variant)
        core = {key: value for key, value in profile.items() if key not in
                ("segment_ref", "missing_spellings", "missing_pitch_classes", "supplier_event_states")}
        owned = _freeze(core)
        signature = hmac.digest(_SECRET, _encoded([id(handle), profile_id, id(owned), descriptor["semantic_fingerprint"]]), "sha256")
        entry = (owned, signature)
        cache[profile_id] = entry
    owned, signature = entry
    expected_signature = hmac.digest(_SECRET, _encoded([id(handle), profile_id, id(owned), descriptor["semantic_fingerprint"]]), "sha256")
    if not isinstance(owned, MappingProxyType) or not hmac.compare_digest(signature, expected_signature):
        raise ValueError("prepared_profile_cache_owned_state_changed")
    profile = _thaw(owned)
    profile.update(segment_ref=variant["segment_id"], missing_spellings=deepcopy(variant["missing_spellings"]),
                   missing_pitch_classes=deepcopy(variant["missing_pitch_classes"]),
                   supplier_event_states=deepcopy(variant["supplier_event_states"]))
    return profile


def _new_bundle(scope, index, keys, required=()):
    legacy = frozen._bundle(scope, [], keys, required)
    # The low-level geometry completion is reused, not its empty legacy path
    # registry. This NEW seal explicitly binds the complete symbolic universe.
    body = {key: deepcopy(value) for key, value in legacy.items()
            if key not in ("record_id", "record_sha256", "version", "comparison_path_refs", "comparison_key_refs", "flags")}
    body.update(version=VERSION, index_ref=_ref(index), symbolic_universe_ref=_ref(index["universe"]),
        symbolic_universe=deepcopy(index["universe"]), comparison_key_refs=[_ref(key) for key in keys],
        comparison_path_representation="all_indexed_catalogue_products_not_empty_or_legacy_path_registry",
        sparse_compatibility_semantics="required_conditions_checked_against_actual_complete_witness_links_for_requested_tuples",
        flags=_flags())
    return _seal(body, BUNDLE_PREFIX)


def _tuple_identity(index, group, variant_ids, key):
    return _seal({"version": VERSION, "index_ref": _ref(index),
        "symbolic_universe_ref": _ref(index["universe"]),
        "group_id": group["group_id"], "indexed_group_id": group["indexed_group_id"],
        "partition": deepcopy(group["partition"]), "variant_ids": list(variant_ids),
        "key_ref": _ref(key), "selected": None, "rank": None, "confidence": None,
        "semantics": "exact_logical_catalogue_tuple_not_a_fabricated_legacy_path"}, TUPLE_PREFIX)


def _thin_index(state):
    """Copy only the small universe/header, never the variant/profile index."""
    source = state.data["index"]
    return {name: _thaw(source[name]) for name in ("record_id", "record_sha256",
        "hypotheses_ref", "analysis_span", "universe", "keys")}


def query_prepared(session, group_id, variant_ids, key_id, *, max_motion_pairs=65536):
    _integer(max_motion_pairs, "max_motion_pairs")
    state = _session(session)
    if not isinstance(group_id, str) or group_id not in state.lookups["groups"]:
        raise ValueError("foreign_or_unknown_indexed_group")
    if not isinstance(key_id, str) or key_id not in state.lookups["keys"]:
        raise ValueError("foreign_or_unknown_indexed_key")
    if not isinstance(variant_ids, (list, tuple)) or any(not isinstance(ref, str) or not ref for ref in variant_ids):
        raise ValueError("ordered_explicit_variant_tuple_required")
    index = _thin_index(state)
    scope = _thaw(state.data["scope"])
    group = _thaw(state.data["index"]["path_groups"][state.lookups["groups"][group_id]])
    if len(variant_ids) != len(group["slots"]) or len(set(variant_ids)) != len(variant_ids):
        raise ValueError("complete_unique_ordered_variant_tuple_required")
    for ref, slot in zip(variant_ids, group["slots"]):
        if ref not in slot["variant_ids"]:
            raise ValueError("foreign_variant_or_wrong_partition_slot")
    key = index["keys"][state.lookups["keys"][key_id]]
    tuple_record = _tuple_identity(index, group, variant_ids, key)
    base_body = {"version": VERSION, "contract": _contract(), "index_ref": _ref(index),
        "scope_ref": _ref(scope), "hypotheses_ref": deepcopy(index["hypotheses_ref"]),
        "tuple_ref": _ref(tuple_record), "logical_tuple": tuple_record,
        "group_ref": {"group_id": group_id, "indexed_group_id": group["indexed_group_id"]},
        "variant_ids": list(variant_ids), "key_ref": _ref(key),
        "analysis_span": deepcopy(index["analysis_span"]), "logical_universe": deepcopy(index["universe"]),
        "resource_limits": {"max_motion_pairs": max_motion_pairs}, "profiles": [], "functions": [],
        "bundle_inventory": [], "same_bundle_assessments": [],
        "computed_counts": {"queried_tuples": 0, "profile_uses": 0, "function_shapes": 0, "bundles": 0,
                            "conditional_joint_motion_shapes": 0},
        "status": "withheld_logical_tuple", "reasons": deepcopy(group["reasons"]),
        "selected": None, "rank": None, "confidence": None, "flags": _flags()}
    if group["status"] != "ready_factorized_group":
        result = _seal(base_body, QUERY_PREFIX)
        _session(session)
        return result
    rows = [state.data["index"]["variant_inventory"][state.lookups["variants"][ref]] for ref in variant_ids]
    segments = [_thaw(row["variant"]) for row in rows]
    profiles = [_computed_profile(session, state, row) for row in rows]
    baseline = _new_bundle(scope, index, index["keys"])
    bundles = {(): baseline}
    functions = []
    for position, source in enumerate(segments):
        target = segments[position + 1] if position + 1 < len(segments) else None
        for family in frozen.FAMILIES:
            for quality in ("M", "m"):
                function = frozen._function(scope, source, target, key["segments"][0], family, quality)
                function["function_id"] = "fmifunction_" + digest([_ref(tuple_record), position, function])[:24]
                options, blockers, endpoint_count, endpoint_hold = frozen._motion_options(
                    scope, function, source, target, profiles[position:position + 2], max_motion_pairs)
                qualified = [[edge for edge in edges if edge["qualified"]] for edges in options.values()]
                count = None if endpoint_hold else 1
                if count is not None:
                    for edges in qualified:
                        count *= len(edges)
                motion = {"edge_options": options, "total_joint_options": count,
                    "planned_endpoint_pairs": endpoint_count, "joint_options": [],
                    "qualifying_bundle_refs": [], "blockers": blockers,
                    "baseline_bundle_ref": _ref(baseline), "status": "withheld",
                    "same_pitch_delayed_resolution": "unassessed",
                    "cadence_NCT_and_actual_harmony_identity": "unassessed"}
                if endpoint_hold:
                    motion["status"] = "whole_group_budget_abstention"
                elif count > max_motion_pairs:
                    motion.update(status="whole_group_budget_abstention", blockers=sorted(set(blockers + [
                        "complete_joint_motion_group_exceeds_budget_no_pruning"])))
                elif not blockers:
                    for edges in product(*qualified):
                        required = tuple(sorted(set(tuple(edge["required_link"]) for edge in edges)))
                        bundle = bundles.get(required)
                        if bundle is None:
                            bundle = _new_bundle(scope, index, index["keys"], required)
                            bundles[required] = bundle
                        complete = bundle["status"] == "complete_all_lane_witness"
                        motion["joint_options"].append({"required_links": [list(pair) for pair in required],
                            "bundle_ref": _ref(bundle), "status": "conditional_joint_motion_shape" if complete else "withheld",
                            "blockers": deepcopy(bundle["reasons"]), "critical_roles": list(options),
                            "all_critical_roles_in_same_bundle": complete})
                        if complete:
                            motion["qualifying_bundle_refs"].append(_ref(bundle))
                    if motion["qualifying_bundle_refs"]:
                        motion["status"] = "conditional_joint_motion_shape"
                function["motion"] = motion
                functions.append(function)
    assessments = []
    for bundle in bundles.values():
        links = {tuple(pair) for entry in bundle["entries"] if entry["witness"] is not None
                 for pair in entry["witness"]["assignment"]["links"]}
        satisfied = [function["function_id"] for function in functions if any(
            bundle["status"] == "complete_all_lane_witness" and option["status"] == "conditional_joint_motion_shape"
            and {tuple(pair) for pair in option["required_links"]} <= links
            for option in function["motion"]["joint_options"])]
        assessments.append({"bundle_ref": _ref(bundle), "tuple_ref": _ref(tuple_record),
            "joint_motion_shape_refs": satisfied,
            "symbolic_universe_ref": _ref(index["universe"]),
            "same_complete_bundle_for_all_function_assumptions": bundle["status"] == "complete_all_lane_witness",
            "link_basis": "actual_materialized_completion_links_in_all_declared_lanes",
            "unqueried_tuple_compatibility": "unassessed_not_false_not_materialized",
            "sparse_universe_predicate": "query_any_exact_indexed_tuple_under_this_same_complete_bundle",
            "selected": None})
    base_body.update(profiles=profiles, functions=functions, bundle_inventory=list(bundles.values()),
        same_bundle_assessments=assessments, status="computed_logical_tuple_not_selected", reasons=[],
        computed_counts={"queried_tuples": 1, "profile_uses": len(profiles), "function_shapes": len(functions),
            "bundles": len(bundles), "conditional_joint_motion_shapes": sum(
                function["motion"]["status"] == "conditional_joint_motion_shape" for function in functions)})
    result = _seal(base_body, QUERY_PREFIX)
    _session(session)
    return result


def query(ir, scope, hypotheses, index, group_id, variant_ids, key_id, *, max_motion_pairs=65536):
    _integer(max_motion_pairs, "max_motion_pairs")
    session = prepare_index(ir, scope, hypotheses, index)
    return query_prepared(session, group_id, variant_ids, key_id, max_motion_pairs=max_motion_pairs)


def validate_query(ir, scope, hypotheses, index, group_id, variant_ids, key_id, result, *, max_motion_pairs=65536):
    _integer(max_motion_pairs, "max_motion_pairs")
    frozen._check(result, QUERY_PREFIX)
    if not _same(result, query(ir, scope, hypotheses, index, group_id, variant_ids, key_id, max_motion_pairs=max_motion_pairs)):
        raise ValueError("stale_foreign_or_modified_indexed_query")
    return True


def assess_prepared(session, bundle, group_id, variant_ids, key_id, *, max_motion_pairs=65536):
    """Compute one competitor under an EXISTING complete all-lane witness.

    Symbolic universe membership is not an affirmative compatibility result.
    This accessor evaluates the requested tuple's guarded critical-role sets
    against actual witness links, without declaring other tuples evaluated.
    """
    _integer(max_motion_pairs, "max_motion_pairs")
    state = _session(session)
    frozen._check(bundle, BUNDLE_PREFIX)
    before = digest(bundle)
    index = _thin_index(state)
    scope = _thaw(state.data["scope"])
    required = bundle.get("required_links")
    if (not isinstance(required, list) or any(not isinstance(pair, list) or len(pair) != 2
            or any(not isinstance(ref, str) for ref in pair) for pair in required)):
        raise ValueError("exact_complete_bundle_required_link_inventory_required")
    expected = _new_bundle(scope, index, index["keys"], required)
    if not _same(bundle, expected):
        raise ValueError("foreign_stale_or_modified_indexed_complete_bundle")
    # A withheld all-lane bundle remains a recorded blocker, not a selected
    # subset of its healthy lanes. Replaying it does not promote its status.
    result = query_prepared(session, group_id, variant_ids, key_id, max_motion_pairs=max_motion_pairs)
    links = {tuple(pair) for entry in bundle["entries"] if entry["witness"] is not None
             for pair in entry["witness"]["assignment"]["links"]}
    complete = bundle["status"] == "complete_all_lane_witness"
    rows = []
    for function in result["functions"]:
        motion = function["motion"]
        options = motion["edge_options"]
        roles = list(options)
        matched = {role: [deepcopy(edge["required_link"]) for edge in edges
                         if edge["qualified"] and tuple(edge["required_link"]) in links]
                   for role, edges in options.items()}
        blockers = deepcopy(motion["blockers"])
        if not complete:
            blockers.extend(bundle["reasons"])
            blockers.append("existing_complete_all_lane_bundle_withheld")
        if motion["status"] == "whole_group_budget_abstention":
            status = "whole_group_budget_abstention"
        elif complete and not blockers and roles and all(matched[role] for role in roles):
            status = "conditional_joint_motion_shape_under_existing_bundle"
        else:
            status = "withheld_under_existing_bundle"
            blockers.extend(role + "_required_link_absent_from_existing_actual_witness"
                            for role in roles if not matched[role])
        rows.append({"function_id": function["function_id"], "family": function["family"],
            "target_quality": function["target_quality"], "source_segment_ref": function["source_segment_ref"],
            "status": status, "critical_roles": roles, "matched_actual_links_by_role": matched,
            "all_critical_roles_in_same_complete_bundle": status == "conditional_joint_motion_shape_under_existing_bundle",
            "blockers": sorted(set(blockers)), "function_confirmed": None,
            "cadence_NCT_and_actual_harmony_identity": "unassessed"})
    body = {"version": VERSION, "contract": _contract(), "scope_ref": _ref(scope), "index_ref": _ref(index),
        "query_ref": _ref(result), "tuple_ref": deepcopy(result["tuple_ref"]),
        "group_ref": deepcopy(result["group_ref"]), "variant_ids": list(variant_ids), "key_ref": deepcopy(result["key_ref"]),
        "bundle_ref": _ref(bundle), "symbolic_universe_ref": _ref(index["universe"]),
        "logical_universe": deepcopy(index["universe"]), "resource_limits": {"max_motion_pairs": max_motion_pairs},
        "rows": rows, "joint_motion_shape_refs": [row["function_id"] for row in rows
            if row["status"] == "conditional_joint_motion_shape_under_existing_bundle"],
        "computed_counts": {"compatibility_tuples": result["computed_counts"]["queried_tuples"],
            "function_shapes": len(rows), "conditional_joint_motion_shapes": sum(
                row["status"] == "conditional_joint_motion_shape_under_existing_bundle" for row in rows)},
        "unqueried_logical_tuple_count": max(0, index["universe"]["logical_tuples"] - result["computed_counts"]["queried_tuples"]),
        "unknown_product_groups": index["universe"]["unknown_product_groups"],
        "unqueried_tuple_compatibility": "unassessed_not_false_not_materialized",
        "link_basis": "actual_materialized_completion_links_in_all_declared_lanes",
        "same_complete_bundle_for_all_function_assumptions": complete,
        "bundle_status": bundle["status"], "all_no_link_control": bundle["all_no_link_control"],
        "status": "computed_compatibility_under_existing_bundle" if rows else "withheld_logical_tuple",
        "reasons": deepcopy(result["reasons"]), "selected": None, "rank": None, "confidence": None, "flags": _flags()}
    assessment = _seal(body, ASSESSMENT_PREFIX)
    if before != digest(bundle):
        raise ValueError("existing_bundle_changed_during_assessment")
    _session(session)
    return assessment


def assess(ir, scope, hypotheses, index, bundle, group_id, variant_ids, key_id, *, max_motion_pairs=65536):
    _integer(max_motion_pairs, "max_motion_pairs")
    session = prepare_index(ir, scope, hypotheses, index)
    return assess_prepared(session, bundle, group_id, variant_ids, key_id, max_motion_pairs=max_motion_pairs)


def validate_assessment(ir, scope, hypotheses, index, bundle, group_id, variant_ids, key_id, result, *, max_motion_pairs=65536):
    _integer(max_motion_pairs, "max_motion_pairs")
    frozen._check(result, ASSESSMENT_PREFIX)
    if not _same(result, assess(ir, scope, hypotheses, index, bundle, group_id, variant_ids, key_id,
                               max_motion_pairs=max_motion_pairs)):
        raise ValueError("stale_foreign_or_modified_indexed_same_bundle_assessment")
    return True
