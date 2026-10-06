"""Owned JSON-proof saved groups and exact source-once contrasts, version 2.

Structural interning is a storage codec, never musical/provenance deduplication.
The issued source remains the source authority; this module grants no historical
archive membership, live native authority, winner, or production capability.
Admission is staged: every whole group keeps its original count on a hold. The
work units are logical traversal/reference/arithmetic visits, not CPU or RSS.
Serialized byte admission is independent of the work ledger.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
import hmac
import json
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import cross_batch_progression_contrast as codec
from . import factor_expanded_hypotheses as kernels
from . import factor_interval_lattice as native
from . import factor_native_role_explanations as roles
from . import lossless_json_dag_v2 as dag
from . import native_progression_contrast as legacy
from . import shared_source_progression_contrast as shared
from . import factor_temporal_explanations as temporal
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "proof-shared-source-progression-contrast-0.2.0"
ENCODING = "owned-json-proof-original-row-refinement-v2"
PLAN_PREFIX, GROUP_PREFIX = "pspcplan_", "pspcgroup_"
CATALOG_PREFIX, PAIR_PREFIX, BLOCK_PREFIX = "pspccatalog_", "pspcpair_", "pspcblock_"
GroupLimits = shared.GroupLimits
CATEGORIES = legacy.CATEGORIES
_PLANS, _GROUPS = WeakKeyDictionary(), WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)
_facet = legacy._facet
_plain_ref = legacy._plain_ref


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False)
class GroupPlan:
    entry_count: int
    planned_pairs: int
    planned_blocks: int
    block_size: int
    stage: str = "counts"
    local_input_json_bytes: int | None = None
    input_visits: int | None = None
    owned_input_snapshot_work: int | None = None
    decoded_entry_work: int | None = None
    seal_validation_work: int | None = None
    proof_composition_work: int | None = None
    input_guard_passes: int | None = None
    snapshot_validation_passes: int | None = None
    seal_hash_passes: int | None = None
    distinct_seal_nodes: int | None = None
    shared_seal_node_hits: int | None = None
    projection_work: int | None = None
    validation_and_facet_work: int | None = None
    canonicalization_work: int | None = None
    catalog_finalization_work: int | None = None
    endpoint_work: int | None = None
    refinement_atom_upper_bound: int | None = None
    vector_cell_upper_bound: int | None = None
    pair_work: int | None = None
    planned_work_upper_bound: int | None = None
    dag_encoded_bytes: int | None = None
    dag_expanded_bytes: int | None = None
    dag_expanded_visits: int | None = None
    catalog_byte_upper_bound: int | None = None
    actual_catalog_bytes: int | None = None
    codec_hold_reason: str | None = None
    codec_hold_diagnostics_json: str | None = None
    reasons: tuple[str, ...] = ()

    @property
    def status(self):
        return "whole_compact_group_hold" if self.reasons else "admissible_compact_group_preflight"

    def record(self):
        return shared._seal({"version": VERSION, **asdict(self), "reasons": list(self.reasons),
            "status": self.status, "exact_union_not_sum_bound": self.refinement_atom_upper_bound is not None,
            "all_original_entries_retained": self.stage == "complete" and not self.reasons,
            "old_pair_semantics": "exact_legacy_pair_including_original_row_attribution_and_source_multiplicity",
            "semantics": "owned_snapshot_and_actual_hash_traversal_not_CPU_RSS_or_accuracy",
            "flags": legacy._flags()}, PLAN_PREFIX)


class WholeGroupHold(ValueError):
    def __init__(self, plan):
        self.plan = plan
        super().__init__("whole_compact_group_hold:" + ",".join(plan.reasons))


def _held(plan, stage, reasons, **fields):
    return replace(plan, stage=stage, reasons=tuple(reasons), **fields)


def _work_hold(plan, stage, work, limits, **fields):
    updated = replace(plan, stage=stage, planned_work_upper_bound=work, **fields)
    return _held(updated, stage, ("whole_work_exceeds_limit_no_prefix",)) if work > limits.max_work else updated


def _codec_hold(plan, stage, reason, error):
    # Preserve exact attempted codec context without presenting its cumulative
    # proof work as an additive whole-group total or unknown costs as zero.
    return _held(plan, stage, (reason,), codec_hold_reason=str(error),
        codec_hold_diagnostics_json=json.dumps(error.diagnostics, sort_keys=True,
            ensure_ascii=False, separators=(",", ":"), allow_nan=False))


def _measure(value, limits, remaining):
    # These are explicit traversal gates, not an increase of the group catalog
    # byte cap: expanded input and retained DAG bytes are different quantities.
    return dag.preflight_json(value, limits=dag.DagLimits(max_input_visits=max(0, remaining),
        max_work_units=max(0, remaining),
        max_expanded_bytes=max(0, remaining), max_encoded_bytes=limits.max_catalog_bytes))


def _owned_bytes(value, remaining):
    """Measure only selected immutable key/bundle, without thawing full source."""
    spent = 0
    def visit(item):
        nonlocal spent
        if type(item) is MappingProxyType:
            size = 2 + max(0, len(item) - 1)
            for key, child in item.items():
                size += visit(key) + 1 + visit(child)
        elif type(item) is tuple:
            size = 2 + max(0, len(item) - 1) + sum(visit(child) for child in item)
        else:
            if type(item) is str and len(item) > remaining - spent:
                raise ValueError("selected_projection_measurement_exceeds_work")
            size = codec._bytes(item)
            spent += size
        spent += 1
        if spent > remaining:
            raise ValueError("selected_projection_measurement_exceeds_work")
        return size
    size = visit(value)
    return size, spent


class _SealProof:
    """Local exact-node proofs; claimed record IDs never identify cache entries."""
    def __init__(self, snapshot, remaining):
        self.snapshot, self.remaining = snapshot, remaining
        self.hashes, self.checks = {}, set()
        self.work = self.passes = self.hits = 0

    def hash(self, at, omit=()):
        key = (dag.proof_node_at(self.snapshot, at), omit)
        if key in self.hashes:
            self.hits += 1
            return self.hashes[key]
        stat = dag.proof_subtree_stats(self.snapshot, at)
        cost = stat["expanded_bytes"] + stat["expanded_visits"]
        if self.work + cost > self.remaining:
            raise dag.DagHold("whole_intrinsic_seal_work_exceeds_limit_no_prefix",
                {"charged_work_units_lower_bound": self.work + cost})
        self.work += cost
        self.passes += 1
        checksum = dag.proof_canonical_sha256(self.snapshot, at, omit_root_keys=omit)
        self.hashes[key] = checksum
        return checksum

    def check(self, record, at, prefix):
        node = dag.proof_node_at(self.snapshot, at)
        key = (node, prefix)
        if key in self.checks:
            self.hits += 1
            return
        checksum = self.hash(at, ("record_id", "record_sha256"))
        if record.get("record_sha256") != checksum or record.get("record_id") != prefix + checksum[:24]:
            raise ValueError("invalid_expanded_record_seal")
        self.checks.add(key)

    def close(self):
        self.hashes.clear()
        self.checks.clear()
        self.snapshot = None


def _validate_clause(clause, path, role, origins, sounds, bundle, proof, at):
    proof.check(clause, at, "fmnroleclause_")
    if (clause["native_path_ref"] != kernels._ref(path)
            or clause["key_ref"] != path["key_ref"] or clause["bundle_ref"] != path["bundle_ref"]
            or clause["origin_refs"] != [kernels._ref(origins[i]) for i in clause["slot_indices"]]):
        raise ValueError("foreign_saved_role_clause_reference")
    source = [sounds[sid] for sid in clause["sound_refs"]]
    if (clause["source_note_refs"] != [n for s in source for n in s["source_note_refs"]]
            or clause["full_sound_spans"] != [s["span"] for s in source]):
        raise ValueError("saved_clause_source_closure_mismatch")
    actual = {tuple(edge) for edge in bundle["materialized_witness_links"]}
    if any(tuple(edge) not in actual for edge in clause["actual_required_links"]):
        raise ValueError("saved_clause_link_not_in_same_completion")
    unknown = bool(clause["blockers"])
    failed = sorted(k for k, v in clause["prerequisites"].items() if v is not True)
    truth = None if unknown else not failed
    if (clause["satisfied"] is not truth or clause["qualified"] is not (not unknown)
            or clause["failed_prerequisites"] != failed
            or clause["status"] != ("unassessed" if truth is None else "supported" if truth else "failed")):
        raise ValueError("saved_clause_truth_or_status_mismatch")
    clips_allowed = truth is True and clause.get("whole_ordinary_template_satisfied", True) is True
    if clause["clips"] != (clause["proposed_clips"] if clips_allowed else []):
        raise ValueError("saved_role_credit_prerequisites_mismatch")
    for clip in clause["proposed_clips"]:
        sound = sounds[clip["sound_ref"]]
        a, b = span_bounds(clip["span"])
        lo, hi = span_bounds(sound["span"])
        if clip["sound_ref"] not in clause["sound_refs"] or not lo <= a < b <= hi:
            raise ValueError("saved_credit_outside_source_sound")


def _validate_entry(entry, scope, lattice, origins_by_id, keys, bundles, sounds, cache, proof, at):
    if type(entry) is not dict or set(entry) != {"native_path", "role_path", "comparison_ref", "explanation_ref"}:
        raise ValueError("closed_saved_contrast_entry_required")
    for name in ("comparison_ref", "explanation_ref"):
        _plain_ref(entry[name])
    path, role = entry["native_path"], entry["role_path"]
    proof.check(path, at + ("native_path",), "fmilpath_")
    proof.check(path["logical_tuple"], at + ("native_path", "logical_tuple"), "fmiltuple_")
    proof.check(role, at + ("role_path",), "fmnrolepath_")
    key = keys[path["key_ref"]["record_id"]]
    bundle = bundles[path["bundle_ref"]["record_id"]]
    if (path["scope_ref"] != kernels._ref(scope) or path["lattice_ref"] != kernels._ref(lattice)
            or path["key_ref"] != kernels._ref(key) or path["bundle_ref"] != kernels._ref(bundle)
            or role["native_path_ref"] != kernels._ref(path)
            or role["logical_tuple_ref"] != kernels._ref(path["logical_tuple"])
            or role["raw_account_pointer"] != {"parent_path_ref": kernels._ref(path),
                "field": "whole_path_account", "sha256": proof.hash(at + ("native_path", "whole_path_account"))}):
        raise ValueError("foreign_saved_path_or_account_pointer")
    identity = path["logical_tuple"]
    for name in ("scope_ref", "lattice_ref", "key_ref", "bundle_ref", "partition", "origin_refs"):
        if identity[name] != path[name]:
            raise ValueError("saved_logical_tuple_identity_mismatch")
    for name in ("partition", "origin_refs", "key_ref", "bundle_ref"):
        if role[name] != path[name]:
            raise ValueError("saved_role_path_identity_mismatch")
    if role["transition_assumptions"] != identity["transition_assumptions"]:
        raise ValueError("saved_transition_vector_mismatch")
    origins = [origins_by_id[ref["record_id"]] for ref in path["origin_refs"]]
    if path["origin_refs"] != [kernels._ref(o) for o in origins]:
        raise ValueError("saved_origin_digest_mismatch")
    lo, hi = span_bounds(scope["analysis_span"])
    cursor = lo
    if (not origins or len(path["partition"]) != len(origins)
            or len(path["profiles"]) != len(origins)
            or len(identity["transition_assumptions"]) != len(origins) - 1):
        raise ValueError("complete_saved_partition_required")
    for extent, origin, profile in zip(path["partition"], origins, path["profiles"]):
        a, b = span_bounds(extent)
        if a != cursor or b > hi or extent != origin["span"]:
            raise ValueError("noncontiguous_or_foreign_saved_partition")
        cursor = b
        if origin["record_id"] not in cache:
            cache[origin["record_id"]] = kernels._profile(scope, origin)
        if profile != cache[origin["record_id"]]:
            raise ValueError("saved_raw_profile_disagrees_with_source")
    if cursor != hi:
        raise ValueError("saved_partition_does_not_cover_full_scope")
    if path["whole_path_account"] != native._account(scope, path["profiles"]):
        raise ValueError("saved_native_raw_account_disagrees_with_source")
    assessed = role["status"] == "assessed_same_completion"
    if role["status"] not in ("assessed_same_completion", "unassessed_completion"):
        raise ValueError("closed_saved_role_status_required")
    if assessed and (scope["context_sound_inventory_complete"] is not True
            or bundle["status"] != "complete_all_lane_witness"):
        raise ValueError("incomplete_source_or_completion_cannot_be_assessed")
    if not assessed and role["clauses"]:
        raise ValueError("unassessed_completion_cannot_emit_role_clauses")
    for ci, clause in enumerate(role["clauses"]):
        _validate_clause(clause, path, role, origins, sounds, bundle, proof, at + ("role_path", "clauses", ci))
    fresh_account = roles._account(path, origins, sounds, role["clauses"], assessed)
    if role["account"] != fresh_account:
        raise ValueError("saved_union_account_disagrees_with_source")
    for record in (path, role, identity):
        if any(record.get(name) is not None for name in ("selected", "rank", "confidence")):
            raise ValueError("saved_contrast_requires_unselected_hypotheses")
    return origins


def _exact_points(facets):
    if not facets:
        return [], []
    ids = sorted(facets[0]["source_segments"])
    if any(sorted(fa["source_segments"]) != ids for fa in facets):
        raise ValueError("competitors_do_not_cover_same_source_sounds")
    sounds = [(sid, sorted({v for fa in facets for row in fa["source_segments"][sid]
        for v in span_bounds(row["span"])})) for sid in ids]
    bass = sorted({v for fa in facets for row in fa["bass_cells"] for v in span_bounds(row["span"])})
    return sounds, bass


def _refinement(facets, sounds, bass):
    return {"sounds": [{"sound_ref": sid, "points": [q(v) for v in points],
        "vectors": [codec._row_vector(fa["source_segments"][sid], points) for fa in facets]}
        for sid, points in sounds], "bass": {"points": [q(v) for v in bass],
        "vectors": [codec._row_vector(fa["bass_cells"], bass) for fa in facets]}}


def _pair_index(payload, facets):
    """Small exact nodes and scalars; no repeated raw bodies or presentations."""
    result = []
    for i, fa in enumerate(facets):
        base = ("facets", i)
        node = lambda *path: dag.node_at(payload, base + path)
        result.append({"partition_node": node("partition"), "transition_node": node("transition_assumptions"),
            "signature_nodes": [[node("slot_presentations", j, "root"), node("slot_presentations", j, "members")]
                for j in range(len(fa["slot_presentations"]))],
            "account": {k: fa["account"][k] for k in ("raw_total_note_time_quarters", "note_time_quarters",
                "conditional_explanation_note_time_quarters")},
            "cuts": [{"time": extent["start"], "assumption_node": node("transition_assumptions", j),
                "assumption_index": j} for j, extent in enumerate(fa["partition"][1:])],
            "source_rows": {sid: [{"row_node": node("source_segments", sid, j), "category": row["category"]}
                for j, row in enumerate(rows)] for sid, rows in fa["source_segments"].items()},
            "bass_rows": [{"row_node": node("bass_cells", j), "sound_refs_node": node("bass_cells", j, "sound_refs"),
                "bass_refs_node": node("bass_cells", j, "bass_refs")} for j in range(len(fa["bass_cells"]))]})
    return result


@dataclass(frozen=True, slots=True)
class _State:
    source: shared.PreparedSource
    payload: dag.JsonDag
    catalog: object
    plan: GroupPlan | None
    limits: GroupLimits
    signature: bytes


def _signature(owner, state):
    try:
        return hmac.digest(_SECRET, json.dumps([id(owner), id(state.source), state.source.source_ref,
            id(state.payload), id(state.catalog), state.catalog["record_sha256"],
            digest(asdict(owner if type(owner) is GroupPlan else state.plan)),
            digest(asdict(state.limits))], separators=(",", ":")).encode(), "sha256")
    finally:
        owner = state = None


def _fresh(owner, registry, cls):
    if type(owner) is not cls or owner not in registry:
        raise ValueError("owned_compact_preflight_or_group_required")
    state = registry[owner]
    if (type(state) is not _State or type(state.catalog) is not MappingProxyType
            or type(state.payload) is not dag.JsonDag or type(state.limits) is not GroupLimits
            or not hmac.compare_digest(state.signature, _signature(owner, state))):
        raise ValueError("owned_compact_state_changed")
    shared._source_issued(state.source)
    # A small owned-handle identity check, not a decode or whole-source export.
    dag.node_at(state.payload, ())
    return state


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


def _catalog_chunks(body, payload):
    """Exact canonical exchange stream, without exporting/freeze-copying DAG."""
    try:
        yield b"{"
        for ordinal, name in enumerate(sorted((*body, "payload"))):
            if ordinal:
                yield b","
            yield _json_bytes(name) + b":"
            yield payload.json_bytes() if name == "payload" else _json_bytes(body[name])
        yield b"}"
    finally:
        body = payload = None


def _seal_catalog(body, payload):
    import hashlib
    checksum = hashlib.sha256()
    for chunk in _catalog_chunks(body, payload):
        checksum.update(chunk)
    value = checksum.hexdigest()
    return {**body, "record_id": CATALOG_PREFIX + value[:24], "record_sha256": value}


def _dispose_projection(scope, origins, keys, bundles, sounds):
    # These maps contain factory-owned thawed copies, NEVER caller/source-owned
    # dictionaries. Empty them even if an inner validator traceback holds them.
    for mapping in (origins, keys, bundles, sounds):
        if type(mapping) is dict:
            for value in mapping.values():
                if type(value) is dict:
                    value.clear()
            mapping.clear()
    if type(scope) is dict:
        scope.clear()


def preflight_saved_group(source, entries, *, completion_request_ref, selector_indices=None,
        key_ref=None, bundle_ref=None, block_size=64, limits=None):
    """Own caller JSON once, validate exact snapshot, and issue a bound draft.

    No raw input is consulted after freeze_json finishes. Imported codec JSON,
    plan records, matching hashes, and copied plans never restore this proof.
    """
    source_state = shared._source_issued(source)
    limits = GroupLimits() if limits is None else limits
    if type(limits) is not GroupLimits or type(entries) is not list:
        raise ValueError("closed_compact_group_inputs_required")
    codec._integer(block_size, "block_size", positive=True)
    if block_size > 64:
        raise ValueError("block_size_must_be_between_1_and_64")
    codec._exact_ref(completion_request_ref)
    n = len(entries)
    pairs = n * (n - 1) // 2
    full, tail = divmod(n, block_size)
    grid = full + bool(tail)
    blocks = grid * (grid - 1) // 2 + full * (block_size > 1) + (tail > 1)
    largest = max(block_size * (block_size - 1) // 2 if full else 0,
        tail * (tail - 1) // 2, block_size ** 2 if full >= 2 else 0,
        block_size * tail if full and tail else 0)
    plan = GroupPlan(n, pairs, blocks, block_size)
    reasons = ["whole_" + name + "_exceeds_limit_no_prefix" for name, value, cap in
        (("entries", n, limits.max_entries), ("pairs", pairs, limits.max_pairs),
            ("block_pairs", largest, limits.max_block_pairs)) if value > cap]
    if pairs and limits.max_pair_record_bytes < 64:
        reasons.append("whole_pair_record_minimum_bytes_exceeds_limit_no_prefix")
    if pairs and limits.max_block_record_bytes < 128:
        reasons.append("whole_block_record_minimum_bytes_exceeds_limit_no_prefix")
    if reasons:
        return _held(plan, "counts", reasons)
    indices = list(range(n)) if selector_indices is None else selector_indices
    if (type(indices) is not list or len(indices) != n or any(type(i) is not int or i < 0 for i in indices)
            or indices != sorted(set(indices))):
        raise ValueError("unique_ordered_original_selector_indices_required")
    # Input snapshot includes ORIGINAL optional values, not only effective refs.
    input_proof = facet_proof = composite_proof = payload = sealproof = entry = None
    facets, cache, seen, origin_ids = [], {}, set(), set()
    scope = origins = keys = bundles = sounds = None
    refinement = pair_index = extras = catalog = frozen = chosen = None
    body = owned = None
    sound_points = bass_points = entry_refs = None
    work = decoded = validation = 0
    operation_stage = "input_snapshot"
    def decode(at):
        nonlocal work, decoded
        stat = dag.proof_subtree_stats(input_proof, at)
        charge = stat["expanded_bytes"] + stat["expanded_visits"]
        if work + charge + (sealproof.work if sealproof is not None else 0) > limits.max_work:
            raise dag.DagHold("whole_owned_snapshot_decode_work_exceeds_limit_no_prefix",
                {"charged_work_units_lower_bound": work + charge})
        work += charge
        decoded += charge
        return dag.proof_value_at(input_proof, at)
    try:
        try:
            input_proof = dag.freeze_json([entries, completion_request_ref, selector_indices, key_ref, bundle_ref],
                limits=dag.DagLimits(max_input_visits=limits.max_work, max_work_units=limits.max_work,
                    max_expanded_bytes=limits.max_work, max_encoded_bytes=limits.max_catalog_bytes))
        except dag.DagHold as error:
            return _codec_hold(plan, "input_snapshot", "whole_input_snapshot_exceeds_limit_no_prefix", error)
        stat = input_proof.stats()
        work = stat["charged_work_units"]
        plan = replace(plan, stage="owned_input_snapshot", local_input_json_bytes=stat["expanded_bytes"],
            input_visits=stat["expanded_visits"], owned_input_snapshot_work=work,
            input_guard_passes=stat["input_guard_passes"],
            snapshot_validation_passes=stat["snapshot_validation_passes"], planned_work_upper_bound=work)
        entry_inventory = dag.proof_subtree_stats(input_proof, (0,))
        if entry_inventory["type"] != "list":
            raise ValueError("closed_compact_group_inputs_required")
        if entry_inventory["container_length"] != n:
            raise ValueError("saved_group_entry_count_changed_before_owned_snapshot")
        # Cheap exact headers are decoded before the selected source projection.
        operation_stage = "input_headers"
        completion = decode((1,))
        original_indices, explicit_key, explicit_bundle = decode((2,)), decode((3,)), decode((4,))
        indices = list(range(n)) if original_indices is None else original_indices
        if (type(indices) is not list or len(indices) != n or any(type(i) is not int or i < 0 for i in indices)
                or indices != sorted(set(indices))):
            raise ValueError("unique_ordered_original_selector_indices_required")
        codec._exact_ref(completion)
        first = [] if not n else [{"native_path": {"key_ref": decode((0, 0, "native_path", "key_ref")),
            "bundle_ref": decode((0, 0, "native_path", "bundle_ref"))}}]
        effective_key, effective_bundle = shared._premises(source_state, first, explicit_key, explicit_bundle)
        for i in range(n):
            if decode((0, i, "native_path", "key_ref")) != effective_key or decode((0, i, "native_path", "bundle_ref")) != effective_bundle:
                raise ValueError("one_exact_key_bundle_completion_group_required")
            for ref in decode((0, i, "native_path", "origin_refs")):
                codec._exact_ref(ref)
                if ref["record_id"] not in source_state.origins or ref != kernels._ref(source_state.origins[ref["record_id"]]):
                    raise ValueError("foreign_saved_origin_reference")
                origin_ids.add(ref["record_id"])
        try:
            key_bytes, key_scan = _owned_bytes(source_state.keys[effective_key["record_id"]], limits.max_work - work)
            bundle_bytes, bundle_scan = _owned_bytes(source_state.catalog["bundles"][effective_bundle["record_id"]],
                limits.max_work - work - key_scan)
        except ValueError as error:
            if str(error) != "selected_projection_measurement_exceeds_work":
                raise
            return _held(plan, "source_projection", ("whole_selected_projection_scan_work_exceeds_limit_no_prefix",))
        projection = source_state.scope_bytes + sum(source_state.origin_bytes[oid] for oid in origin_ids) + key_scan + bundle_scan + key_bytes + bundle_bytes
        plan = _work_hold(plan, "source_projection", work + projection, limits, projection_work=projection)
        if plan.reasons:
            return plan
        work += projection
        scope = codec._copy(source_state.catalog["source_scope"])
        origins = {oid: codec._copy(source_state.origins[oid]) for oid in origin_ids}
        keys = {effective_key["record_id"]: codec._copy(source_state.keys[effective_key["record_id"]])}
        bundles = {effective_bundle["record_id"]: codec._copy(source_state.catalog["bundles"][effective_bundle["record_id"]])}
        sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
        sealproof = _SealProof(input_proof, limits.max_work - work)
        entry_refs = []
        for i in range(n):
            operation_stage = "entry_snapshot_decode"
            entry = decode((0, i))  # one bounded detached entry; never a whole second raw group
            if type(entry) is not dict or set(entry) != {"native_path", "role_path", "comparison_ref", "explanation_ref"}:
                raise ValueError("closed_saved_contrast_entry_required")
            intrinsic = legacy._plan(scope, [entry], [])["planned_work"]
            plan = _work_hold(plan, "intrinsic_validation", work + sealproof.work + intrinsic, limits,
                validation_and_facet_work=validation + intrinsic, decoded_entry_work=decoded)
            if plan.reasons:
                return plan
            work += intrinsic
            validation += intrinsic
            sealproof.remaining = limits.max_work - work
            operation_stage = "intrinsic_seal_validation"
            identity = sealproof.hash((0, i, "native_path", "logical_tuple"))
            if identity in seen:
                raise ValueError("duplicate_saved_complete_hypothesis")
            seen.add(identity)
            chosen = _validate_entry(entry, scope, kernels._ref(source_state.catalog["lattice"]),
                origins, keys, bundles, sounds, cache, sealproof, (0, i))
            facets.append(_facet(entry, scope, chosen, sounds))
            entry_refs.append({"native_path_ref": kernels._ref(entry["native_path"]),
                "role_path_ref": kernels._ref(entry["role_path"]), "comparison_ref": entry["comparison_ref"],
                "explanation_ref": entry["explanation_ref"]})
            entry = None
        work += sealproof.work
        plan = replace(plan, validation_and_facet_work=validation, decoded_entry_work=decoded,
            seal_validation_work=sealproof.work, seal_hash_passes=sealproof.passes,
            distinct_seal_nodes=len(sealproof.checks), shared_seal_node_hits=sealproof.hits)
        # Selected mutable source projections and validation caches end here.
        cache.clear(); seen.clear(); origin_ids.clear()
        _dispose_projection(scope, origins, keys, bundles, sounds)
        scope = origins = keys = bundles = sounds = None
        chosen = None
        row_count = sum(sum(len(rows) for rows in fa["source_segments"].values()) + len(fa["bass_cells"]) for fa in facets)
        endpoint_work = 2 * row_count * (max(1, (2 * row_count).bit_length()) + 4)
        plan = _work_hold(plan, "endpoint_union", work + endpoint_work, limits, endpoint_work=endpoint_work)
        if plan.reasons:
            return plan
        work += endpoint_work
        sound_points, bass_points = _exact_points(facets)
        atoms = sum(max(0, len(points) - 1) for _, points in sound_points) + max(0, len(bass_points) - 1)
        vectors = n * atoms
        reasons = ["whole_" + name + "_exceeds_limit_no_prefix" for name, value, cap in
            (("refinement_atoms", atoms, limits.max_refinement_atoms), ("vector_cells", vectors, limits.max_vector_cells)) if value > cap]
        plan = replace(plan, stage="exact_refinement", refinement_atom_upper_bound=atoms, vector_cell_upper_bound=vectors)
        if reasons:
            return _held(plan, "exact_refinement", reasons)
        transition_stats, transition_measurement = [], 0
        operation_stage = "transition_reservation"
        for fa in facets:
            measured = _measure(fa["transition_assumptions"], limits, limits.max_work - work - transition_measurement)
            transition_stats.append(measured)
            transition_measurement += measured["charged_work_units"]
        work += transition_measurement
        max_transition = max((s["expanded_bytes"] + s["expanded_visits"] for s in transition_stats), default=0)
        pair_work = pairs * (atoms * 48 + 1024 + max_transition * 2)
        refine_work = vectors + row_count * (max(1, row_count.bit_length()) + 8)
        plan = _work_hold(plan, "pair_reservation", work + refine_work + pair_work, limits, pair_work=pair_work)
        if plan.reasons:
            return plan
        reserve = refine_work + pair_work
        index_upper = row_count * 384 + vectors * 24 + atoms * 192 + n * 16384 + 32768
        plan = replace(plan, catalog_byte_upper_bound=index_upper)
        if index_upper >= limits.max_catalog_bytes:
            return _held(plan, "compact_catalog_reservation", ("whole_index_bytes_exceeds_limit_no_prefix",))
        # Only newly constructed facets are frozen; prior raw snapshot is reused.
        operation_stage = "facet_snapshot"
        facet_proof = dag.freeze_json(facets, limits=dag.DagLimits(
            max_work_units=max(0, limits.max_work - work - reserve), max_input_visits=limits.max_work,
            max_expanded_bytes=limits.max_work, max_encoded_bytes=limits.max_catalog_bytes - index_upper))
        facet_work = facet_proof.stats()["charged_work_units"]
        # compose/encode charge inherited proof creation. Reconcile that with
        # spent domain work and reserved pairs BEFORE either node-table copy.
        codec_remaining = limits.max_work - (work - stat["charged_work_units"]) - reserve
        operation_stage = "proof_composition"
        composite_proof = dag.compose_proofs({"inputs": input_proof, "facets": facet_proof},
            limits=dag.DagLimits(max_work_units=max(0, codec_remaining), max_input_visits=limits.max_work,
                max_expanded_bytes=limits.max_work, max_encoded_bytes=limits.max_catalog_bytes - index_upper))
        composite_stats = composite_proof.stats()
        composition_work = composite_stats["incremental_work_units"]
        encoding_work = composite_stats["encoding_work_upper_bound"]
        canonical = facet_work + composition_work + encoding_work
        plan = _work_hold(plan, "canonicalization", work + reserve + canonical, limits,
            canonicalization_work=canonical, proof_composition_work=composition_work,
            dag_expanded_bytes=composite_stats["expanded_bytes"], dag_expanded_visits=composite_stats["expanded_visits"])
        if plan.reasons:
            return plan
        operation_stage = "compact_catalog_encoding"
        payload = dag.encode_proof(composite_proof, limits=dag.DagLimits(
            max_work_units=max(0, codec_remaining), max_input_visits=limits.max_work,
            max_expanded_bytes=limits.max_work, max_encoded_bytes=limits.max_catalog_bytes - index_upper))
        encoded = len(payload.json_bytes())
        if payload.stats()["incremental_encoding_work_units"] != encoding_work:
            raise ValueError("owned_proof_exact_encoding_work_mismatch")
        work = plan.planned_work_upper_bound
        plan = replace(plan, dag_encoded_bytes=encoded, catalog_byte_upper_bound=encoded + index_upper)
        # Encoding shares immutable node tuples; creation proofs can expire now.
        input_proof = facet_proof = composite_proof = None
        sealproof.close()
        refinement = _refinement(facets, sound_points, bass_points)
        pair_index = _pair_index(payload, facets)
        group = shared._seal({"version": VERSION, "source_catalog_ref": source.source_ref,
            "scope_ref": kernels._ref(source_state.catalog["source_scope"]), "lattice_ref": kernels._ref(source_state.catalog["lattice"]),
            "key_ref": effective_key, "bundle_ref": effective_bundle, "completion_request_ref": completion,
            "original_selector_indices": indices, "entry_refs": entry_refs}, GROUP_PREFIX)
        plan = replace(plan, stage="complete")
        extras = {"version": VERSION, "codec": ENCODING, "source_authority": legacy.AUTHORITY,
            "source_catalog_ref": source.source_ref, "group": group, "group_ref": kernels._ref(group),
            "pair_index": pair_index, "refinement": refinement, "refinement_sha256": digest(refinement),
            "entry_inventory_sha256": digest(entry_refs),
            "all_original_entry_roots": [dag.node_at(payload, ("inputs", 0, i)) for i in range(n)],
            "all_original_facet_roots": [dag.node_at(payload, ("facets", i)) for i in range(n)],
            "actual_refinement_atoms": atoms, "preflight_plan": plan.record(),
            "selected": None, "rank": None, "confidence": None, "flags": legacy._flags()}
        operation_stage = "catalog_finalization"
        extra_stats = _measure(extras, limits, limits.max_work - work)
        upper = encoded + extra_stats["expanded_bytes"] + 512
        # One full canonical payload hash, metadata size scan/copy/freeze, and
        # exact output-size traversal. No payload export/hash/freeze copies.
        finalization = extra_stats["charged_work_units"] + encoded + extra_stats["expanded_bytes"] * 4 + 1024
        plan = _work_hold(plan, "catalog_finalization", work + finalization, limits,
            catalog_finalization_work=finalization, catalog_byte_upper_bound=upper)
        if plan.reasons:
            return plan
        if upper > limits.max_catalog_bytes:
            return _held(plan, "catalog_finalization", ("whole_catalog_bytes_exceeds_limit_no_prefix",))
        plan = replace(plan, stage="complete")
        body = {**extras, "preflight_plan": plan.record()}
        catalog = _seal_catalog(body, payload)
        actual = sum(len(chunk) for chunk in _catalog_chunks(catalog, payload))
        plan = replace(plan, actual_catalog_bytes=actual)
        if actual > upper or actual > limits.max_catalog_bytes:
            return _held(plan, "compact_catalog_actual", ("whole_actual_catalog_bytes_exceeds_limit_no_prefix",))
        frozen = codec._freeze(catalog)
        shared._source_issued(source)
        owned = _State(source, payload, frozen, None, limits, b"")
        _PLANS[plan] = replace(owned, signature=_signature(plan, owned))
        return plan
    except dag.DagHold as error:
        # A late incremental gate cannot promote any entry/facet prefix.
        return _codec_hold(plan, operation_stage, "whole_owned_proof_work_or_bytes_exceeds_limit_no_prefix", error)
    finally:
        # Explicitly sever temporaries even when a retained traceback disables
        # normal collection. Caller entries are preserved and never cleared.
        facets.clear(); cache.clear(); seen.clear(); origin_ids.clear()
        if sealproof is not None:
            sealproof.close()
        input_proof = facet_proof = composite_proof = payload = sealproof = entry = None
        _dispose_projection(scope, origins, keys, bundles, sounds)
        scope = origins = keys = bundles = sounds = None
        decode = None
        refinement = pair_index = extras = catalog = frozen = chosen = None
        body = owned = None
        sound_points = bass_points = entry_refs = None


@dataclass(frozen=True, slots=True)
class BlockTask:
    row_start: int
    row_end: int
    column_start: int
    column_end: int
    expected_pairs: int
    source_sha256: str | None = None
    group_sha256: str | None = None
    refinement_sha256: str | None = None
    entry_inventory_sha256: str | None = None

    def pair_indices(self):
        for i in range(self.row_start, self.row_end):
            for j in range(self.column_start, self.column_end):
                if i < j:
                    yield i, j


class CompactPreparedGroup:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise ValueError("owned_compact_group_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_compact_group")

    @property
    def source_ref(self):
        return _issued(self).source.source_ref

    @property
    def group_ref(self):
        return codec._copy(_issued(self).catalog["group_ref"])

    @property
    def catalog_ref(self):
        return kernels._ref(_issued(self).catalog)

    @property
    def preflight_plan(self):
        return _issued(self).plan

    def export_catalog(self):
        state = _issued(self)
        return {**codec._copy(state.catalog), "payload": state.payload.record()}

    def export_entry(self, index):
        state = _issued(self)
        _index(state, index)
        return dag.value_at(state.payload, ("inputs", 0, index))

    def export_facet(self, index):
        state = _issued(self)
        _index(state, index)
        return dag.value_at(state.payload, ("facets", index))

    def iter_blocks(self):
        state = _issued(self)
        for task in codec.plan_blocks(state.plan.entry_count, state.plan.block_size):
            yield BlockTask(task.row_start, task.row_end, task.column_start, task.column_end, task.expected_pairs,
                self.source_ref["record_sha256"], self.group_ref["record_sha256"],
                state.catalog["refinement_sha256"], state.catalog["entry_inventory_sha256"])


def _issued(handle):
    return _fresh(handle, _GROUPS, CompactPreparedGroup)


def _index(state, index):
    if type(index) is not int or not 0 <= index < state.plan.entry_count:
        raise ValueError("exact_original_entry_index_required")


def prepare_preflight(plan):
    if type(plan) is GroupPlan and plan.reasons:
        raise WholeGroupHold(plan)
    state = _fresh(plan, _PLANS, GroupPlan)
    handle = object.__new__(CompactPreparedGroup)
    issued = replace(state, plan=plan)
    _GROUPS[handle] = replace(issued, signature=_signature(handle, issued))
    return handle


def prepare_saved_group(source, entries, **options):
    return prepare_preflight(preflight_saved_group(source, entries, **options))


def _compact_pair(prepared, i, j):
    state = _issued(prepared)
    catalog = state.catalog
    left, right = catalog["pair_index"][i], catalog["pair_index"][j]
    transfers, changes = Counter(), []
    for si, sound in enumerate(catalog["refinement"]["sounds"]):
        points = [f(p) for p in sound["points"]]
        sid = sound["sound_ref"]
        for a, b, li, ri in codec._runs(points, sound["vectors"][i], sound["vectors"][j]):
            lc, rc = left["source_rows"][sid][li]["category"], right["source_rows"][sid][ri]["category"]
            transfers[(lc, rc)] += points[b] - points[a]
            if lc != rc:
                changes.append([si, a, b, li, ri])
    raw = f(left["account"]["raw_total_note_time_quarters"])
    if raw != f(right["account"]["raw_total_note_time_quarters"]) or sum(transfers.values(), Fraction()) != raw:
        raise ValueError("pairwise_raw_note_time_not_conserved")
    bass = catalog["refinement"]["bass"]
    bass_runs = []
    for a, b, li, ri in codec._runs(bass["points"], bass["vectors"][i], bass["vectors"][j]):
        lc, rc = left["bass_rows"][li], right["bass_rows"][ri]
        if lc["sound_refs_node"] != rc["sound_refs_node"] or lc["bass_refs_node"] != rc["bass_refs_node"]:
            raise ValueError("aligned_raw_bass_observations_changed_between_candidates")
        bass_runs.append([a, b, li, ri])
    lcuts = {f(c["time"]): c for c in left["cuts"]}
    rcuts = {f(c["time"]): c for c in right["cuts"]}
    partition = left["partition_node"] == right["partition_node"]
    vector = left["transition_node"] == right["transition_node"]
    signatures = left["signature_nodes"] == right["signature_nodes"]
    kind = "partition" if not partition else "candidate_only" if vector else "transition_only" if signatures else "candidate_and_transition"
    lc, rc = (view["account"]["conditional_explanation_note_time_quarters"] for view in (left, right))
    return shared._seal({"version": VERSION, "codec": ENCODING, "source_catalog_ref": prepared.source_ref,
        "catalog_ref": prepared.catalog_ref, "group_ref": prepared.group_ref,
        "refinement_sha256": catalog["refinement_sha256"], "entry_indices": [i, j],
        "original_selector_indices": [catalog["group"]["original_selector_indices"][i], catalog["group"]["original_selector_indices"][j]],
        "comparison_kind": kind, "same_partition": partition, "alias_control": partition and vector and signatures,
        "shared_cut_assumptions": [{"time": q(t),
            "left": dag.value_at(state.payload, ("facets", i, "transition_assumptions", lcuts[t]["assumption_index"])),
            "right": dag.value_at(state.payload, ("facets", j, "transition_assumptions", rcuts[t]["assumption_index"])),
            "same_assumption": lcuts[t]["assumption_node"] == rcuts[t]["assumption_node"]} for t in sorted(lcuts.keys() & rcuts.keys())],
        "left_only_cuts": [q(t) for t in sorted(lcuts.keys() - rcuts.keys())],
        "right_only_cuts": [q(t) for t in sorted(rcuts.keys() - lcuts.keys())],
        "raw_total_note_time_quarters": q(raw), "raw_time_conserved": True,
        "note_time_delta_right_minus_left": {c: q(f(right["account"]["note_time_quarters"][c]) - f(left["account"]["note_time_quarters"][c])) for c in CATEGORIES},
        "conditional_credit_delta_right_minus_left": None if lc is None or rc is None else q(f(rc) - f(lc)),
        "category_transfer_note_time": [{"left": a, "right": b, "duration_quarters": q(v)} for (a, b), v in sorted(transfers.items())],
        "changed_source_segment_pointers": changes, "aligned_bass_cell_pointers": bass_runs,
        "logical_atom_visits": catalog["actual_refinement_atoms"],
        "status": "computed_saved_pair_contrast_not_selected", "musical_outcome": None,
        "selected": None, "rank": None, "confidence": None}, PAIR_PREFIX)


def compare_block(prepared, task):
    state = _issued(prepared)
    if type(task) is not BlockTask:
        raise ValueError("exact_compact_block_task_required")
    n, size = state.plan.entry_count, state.plan.block_size
    values = (task.row_start, task.row_end, task.column_start, task.column_end, task.expected_pairs)
    if any(type(v) is not int for v in values):
        raise ValueError("foreign_or_modified_compact_block_task")
    rows = task.row_end - task.row_start
    expected = rows * (rows - 1) // 2 if task.row_start == task.column_start else rows * (task.column_end - task.column_start)
    if (not 0 <= task.row_start <= task.column_start < n or task.row_start % size or task.column_start % size
            or task.row_end != min(task.row_start + size, n) or task.column_end != min(task.column_start + size, n)
            or expected <= 0 or task.expected_pairs != expected
            or any(type(v) is not str for v in (task.source_sha256, task.group_sha256, task.refinement_sha256, task.entry_inventory_sha256))
            or task.source_sha256 != prepared.source_ref["record_sha256"] or task.group_sha256 != prepared.group_ref["record_sha256"]
            or task.refinement_sha256 != state.catalog["refinement_sha256"] or task.entry_inventory_sha256 != state.catalog["entry_inventory_sha256"]):
        raise ValueError("foreign_or_modified_compact_block_task")
    pairs, reasons, buffered = [], [], 0
    for i, j in task.pair_indices():
        pair = _compact_pair(prepared, i, j)
        size_bytes = codec._bytes(pair)
        if size_bytes > state.limits.max_pair_record_bytes:
            reasons.append("whole_block_pair_bytes_exceeds_limit_no_prefix")
            break
        if buffered + size_bytes > state.limits.max_block_record_bytes:
            reasons.append("whole_block_buffer_bytes_exceeds_limit_no_prefix")
            break
        pairs.append(pair)
        buffered += size_bytes
    if reasons:
        pairs = []
    body = {"version": VERSION, "source_catalog_ref": prepared.source_ref, "catalog_ref": prepared.catalog_ref,
        "group_ref": prepared.group_ref, "refinement_sha256": state.catalog["refinement_sha256"],
        "entry_inventory_sha256": state.catalog["entry_inventory_sha256"], "task": asdict(task),
        "planned_pairs": task.expected_pairs, "computed_pairs": len(pairs), "withheld_pairs": task.expected_pairs - len(pairs),
        "pairs": pairs, "reasons": reasons, "status": "whole_saved_block_hold" if reasons else "computed_saved_block_not_selected",
        "whole_group_complete": False, "musical_outcome": None, "selected": None, "rank": None, "confidence": None,
        "flags": legacy._flags()}
    if pairs and codec._bytes(body) + 256 > state.limits.max_block_record_bytes:
        body.update(pairs=[], computed_pairs=0, withheld_pairs=task.expected_pairs,
            reasons=["whole_block_encoded_bytes_exceeds_limit_no_prefix"], status="whole_saved_block_hold")
    return shared._seal(body, BLOCK_PREFIX)


def materialize_pair(prepared, pair):
    """Bounded two-entry legacy output, never a full payload/source decode."""
    state = _issued(prepared)
    if type(pair) is not dict:
        raise ValueError("closed_compact_pair_record_required")
    codec._no_float(pair)
    kernels._check(pair, PAIR_PREFIX)
    if (pair["source_catalog_ref"] != prepared.source_ref or pair["catalog_ref"] != prepared.catalog_ref
            or pair["group_ref"] != prepared.group_ref):
        raise ValueError("foreign_compact_pair_source_or_catalog")
    i, j = pair["entry_indices"]
    _index(state, i)
    _index(state, j)
    if i >= j or pair != _compact_pair(prepared, i, j):
        raise ValueError("compact_pair_disagrees_with_validated_catalog")
    # Decode admission uses expanded size, not the tiny node-table encoding.
    paths = [("facets", index, "source_segments", state.catalog["refinement"]["sounds"][si]["sound_ref"], row)
        for si, _, _, li, ri in pair["changed_source_segment_pointers"] for index, row in ((i, li), (j, ri))]
    paths += [("facets", index, "bass_cells", row) for _, _, li, ri in pair["aligned_bass_cell_pointers"]
        for index, row in ((i, li), (j, ri))]
    stats = [dag.subtree_stats(state.payload, path) for path in paths]
    source_state = shared._source_issued(state.source)
    # Every changed segment copies three original sound-closure fields; the
    # once-owned scope byte size bounds each closure without serializing source
    # per pair. Include wrapper/reference overhead before any subtree decode.
    closure_bound = len(pair["changed_source_segment_pointers"]) * source_state.scope_bytes
    point_bytes = 0
    for si, a, b, _, _ in pair["changed_source_segment_pointers"]:
        points = state.catalog["refinement"]["sounds"][si]["points"]
        point_bytes += codec._bytes(codec._copy(points[a])) + codec._bytes(codec._copy(points[b]))
    for a, b, _, _ in pair["aligned_bass_cell_pointers"]:
        points = state.catalog["refinement"]["bass"]["points"]
        point_bytes += codec._bytes(codec._copy(points[a])) + codec._bytes(codec._copy(points[b]))
    wrapper_bound = 4096 + len(paths) * 256 + point_bytes
    if sum(s["expanded_bytes"] for s in stats) + codec._bytes(pair) + closure_bound + wrapper_bound > state.limits.max_pair_record_bytes:
        raise ValueError("whole_materialized_pair_expanded_bytes_exceeds_limit_no_prefix")
    if sum(s["expanded_visits"] for s in stats) + closure_bound + state.catalog["actual_refinement_atoms"] * 4 > state.limits.max_work:
        raise ValueError("whole_materialized_pair_work_exceeds_limit_no_prefix")
    sounds = source_state.sounds
    differences = []
    for si, a, b, li, ri in pair["changed_source_segment_pointers"]:
        sound = state.catalog["refinement"]["sounds"][si]
        sid, points = sound["sound_ref"], sound["points"]
        differences.append({"sound_ref": sid, "source_note_refs": codec._copy(sounds[sid]["source_note_refs"]),
            "pitch": codec._copy(sounds[sid]["pitch"]), "full_sound_span": codec._copy(sounds[sid]["span"]),
            "span": {"start": codec._copy(points[a]), "end": codec._copy(points[b])},
            "left": dag.value_at(state.payload, ("facets", i, "source_segments", sid, li)),
            "right": dag.value_at(state.payload, ("facets", j, "source_segments", sid, ri))})
    bass, points = [], state.catalog["refinement"]["bass"]["points"]
    for a, b, li, ri in pair["aligned_bass_cell_pointers"]:
        lc = dag.value_at(state.payload, ("facets", i, "bass_cells", li))
        rc = dag.value_at(state.payload, ("facets", j, "bass_cells", ri))
        bass.append({"span": {"start": codec._copy(points[a]), "end": codec._copy(points[b])},
            "bass_refs": lc["bass_refs"], "left": {k: lc[k] for k in codec._BASS_FIELDS},
            "right": {k: rc[k] for k in codec._BASS_FIELDS}, "bass_is_not_certified_structural_bass": True})
    refs = state.catalog["group"]["entry_refs"]
    fields = ("comparison_kind", "same_partition", "alias_control", "shared_cut_assumptions", "left_only_cuts",
        "right_only_cuts", "raw_total_note_time_quarters", "raw_time_conserved", "note_time_delta_right_minus_left",
        "category_transfer_note_time")
    result = {"left_path_ref": codec._copy(refs[i]["native_path_ref"]), "right_path_ref": codec._copy(refs[j]["native_path_ref"]),
        "left_role_path_ref": codec._copy(refs[i]["role_path_ref"]), "right_role_path_ref": codec._copy(refs[j]["role_path_ref"]),
        "key_ref": codec._copy(state.catalog["group"]["key_ref"]), "bundle_ref": codec._copy(state.catalog["group"]["bundle_ref"]),
        **{k: codec._copy(pair[k]) for k in fields}, "changed_source_segments": differences, "aligned_bass_cells": bass,
        "selected": None, "rank": None, "confidence": None,
        "interpretation": "conditional_evidence_contrast_not_chord_selection"}
    if codec._bytes(result) > state.limits.max_pair_record_bytes:
        raise ValueError("whole_materialized_pair_encoded_bytes_exceeds_limit_no_prefix")
    return result
