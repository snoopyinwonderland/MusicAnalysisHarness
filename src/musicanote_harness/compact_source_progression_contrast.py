"""Lossless saved groups, exact rational refinements, and source-once contrasts.

Structural interning is a storage codec, never musical/provenance deduplication.
The issued source remains the source authority; this module grants no historical
archive membership, live native authority, winner, or production capability.
Admission is staged: every whole group keeps its original count on a hold. The
work units are logical traversal/reference/arithmetic visits, not CPU or RSS.
Serialized byte admission is independent of the work ledger.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
import hmac
import json
import secrets
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import cross_batch_progression_contrast as codec
from . import factor_expanded_hypotheses as kernels
from . import lossless_json_dag as dag
from . import native_progression_contrast as legacy
from . import shared_source_progression_contrast as shared
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "compact-source-progression-contrast-0.1.0"
ENCODING = "lossless-structural-dag-original-row-refinement-v1"
PLAN_PREFIX, GROUP_PREFIX = "cspcplan_", "cspcgroup_"
CATALOG_PREFIX, PAIR_PREFIX, BLOCK_PREFIX = "cspccatalog_", "cspcpair_", "cspcblock_"
GroupLimits = shared.GroupLimits
CATEGORIES = legacy.CATEGORIES
_PLANS, _GROUPS = WeakKeyDictionary(), WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)
_validate_entry, _facet = legacy._validate_entry, legacy._facet


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False)
class GroupPlan:
    entry_count: int
    planned_pairs: int
    planned_blocks: int
    block_size: int
    stage: str = "counts"
    local_input_json_bytes: int | None = None
    input_visits: int | None = None
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
    reasons: tuple[str, ...] = ()

    @property
    def status(self):
        return "whole_compact_group_hold" if self.reasons else "admissible_compact_group_preflight"

    def record(self):
        return shared._seal({"version": VERSION, **asdict(self), "reasons": list(self.reasons),
            "status": self.status, "exact_union_not_sum_bound": self.refinement_atom_upper_bound is not None,
            "all_original_entries_retained": self.stage == "complete" and not self.reasons,
            "old_pair_semantics": "exact_legacy_pair_including_original_row_attribution_and_source_multiplicity",
            "semantics": "logical_traversal_and_encoded_bytes_not_CPU_RSS_or_accuracy",
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
    return hmac.digest(_SECRET, json.dumps([id(owner), id(state.source), state.source.source_ref,
        id(state.payload), id(state.catalog), state.catalog["record_sha256"],
        digest(asdict(owner if type(owner) is GroupPlan else state.plan)),
        digest(asdict(state.limits))], separators=(",", ":")).encode(), "sha256")


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


def preflight_saved_group(source, entries, *, completion_request_ref, selector_indices=None,
        key_ref=None, bundle_ref=None, block_size=64, limits=None):
    """Validate/pack a complete group, returning a hold or an owned draft plan.

    An admissible plan can be issued with prepare_preflight without repeating
    expensive validation. A JSON copy of a plan never grants that capability.
    No prepared group is issued when any later stage is held.
    """
    state = shared._source_issued(source)
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
    largest = max(block_size * (block_size - 1) // 2 if full else 0, tail * (tail - 1) // 2,
        block_size ** 2 if full >= 2 else 0, block_size * tail if full and tail else 0)
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
    original = [entries, completion_request_ref, selector_indices, key_ref, bundle_ref]
    try:
        measured = _measure(original, limits, limits.max_work)
    except dag.DagHold as error:
        return _held(plan, "input_measurement", ("whole_input_traversal_exceeds_limit_no_prefix",), codec_hold_reason=str(error))
    raw_bytes, visits = measured["expanded_bytes"], measured["expanded_visits"]
    # Measurement and caller identity guards, plus path/role/nested clause seals
    # consume raw bytes irrespective of structural compression.
    work = raw_bytes * 8 + visits
    plan = _work_hold(plan, "input_identity", work, limits,
        local_input_json_bytes=raw_bytes, input_visits=visits)
    if plan.reasons:
        return plan
    before = digest(original)
    effective_key, effective_bundle = shared._premises(state, entries, key_ref, bundle_ref)
    origin_ids = set()
    seen = set()
    for entry in entries:
        if type(entry) is not dict or set(entry) != {"native_path", "role_path", "comparison_ref", "explanation_ref"}:
            raise ValueError("closed_saved_contrast_entry_required")
        path = entry["native_path"]
        if path["key_ref"] != effective_key or path["bundle_ref"] != effective_bundle:
            raise ValueError("one_exact_key_bundle_completion_group_required")
        identity = digest(path["logical_tuple"])
        if identity in seen:
            raise ValueError("duplicate_saved_complete_hypothesis")
        seen.add(identity)
        for ref in path["origin_refs"]:
            codec._exact_ref(ref)
            if ref["record_id"] not in state.origins or ref != kernels._ref(state.origins[ref["record_id"]]):
                raise ValueError("foreign_saved_origin_reference")
            origin_ids.add(ref["record_id"])
    try:
        key_bytes, key_scan = _owned_bytes(state.keys[effective_key["record_id"]], limits.max_work - work)
        bundle_bytes, bundle_scan = _owned_bytes(state.catalog["bundles"][effective_bundle["record_id"]],
            limits.max_work - work - key_scan)
    except ValueError as error:
        if str(error) != "selected_projection_measurement_exceeds_work":
            raise
        return _held(plan, "source_projection", ("whole_selected_projection_scan_work_exceeds_limit_no_prefix",))
    projection = state.scope_bytes + sum(state.origin_bytes[oid] for oid in origin_ids) \
        + key_scan + bundle_scan + key_bytes + bundle_bytes
    plan = _work_hold(plan, "source_projection", work + projection, limits, projection_work=projection)
    if plan.reasons:
        return plan
    work += projection
    scope = codec._copy(state.catalog["source_scope"])
    origins = {oid: codec._copy(state.origins[oid]) for oid in origin_ids}
    keys = {effective_key["record_id"]: codec._copy(state.keys[effective_key["record_id"]])}
    bundles = {effective_bundle["record_id"]: codec._copy(state.catalog["bundles"][effective_bundle["record_id"]])}
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    validation = legacy._plan(scope, entries, [])["planned_work"]
    plan = _work_hold(plan, "intrinsic_validation", work + validation, limits,
        validation_and_facet_work=validation)
    if plan.reasons:
        return plan
    work += validation
    facets, cache = [], {}
    for entry in entries:
        chosen = _validate_entry(entry, scope, kernels._ref(state.catalog["lattice"]), origins,
            keys, bundles, sounds, cache)
        facets.append(_facet(entry, scope, chosen, sounds))
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
        (("refinement_atoms", atoms, limits.max_refinement_atoms), ("vector_cells", vectors, limits.max_vector_cells))
        if value > cap]
    plan = replace(plan, stage="exact_refinement", refinement_atom_upper_bound=atoms, vector_cell_upper_bound=vectors)
    if reasons:
        return _held(plan, "exact_refinement", reasons)
    composite = {"entries": entries, "facets": facets}
    try:
        measured = _measure(composite, limits, limits.max_work - work)
    except dag.DagHold as error:
        return _held(plan, "canonicalization", ("whole_payload_traversal_exceeds_limit_no_prefix",), codec_hold_reason=str(error))
    # The independent measurement plus the DAG's two guards and intern pass
    # are ALL charged. The helper also dynamically charges encoded node bytes.
    canonical = (measured["expanded_bytes"] + measured["expanded_visits"]) * 4
    # Vector sweep/sort and small index construction are reserved before either
    # vectors or payload/index allocation. No sum-of-all-endpoints multiplier.
    refine_work = vectors + row_count * (max(1, row_count.bit_length()) + 8)
    # Transition values can be large saved JSON, not necessarily a short enum.
    # Charge the actual logical sizes before any quadratic pair computation.
    transition_stats = []
    transition_measurement = 0
    try:
        for fa in facets:
            stat = _measure(fa["transition_assumptions"], limits, limits.max_work - work - transition_measurement)
            transition_stats.append(stat)
            transition_measurement += stat["charged_work_units"]
    except dag.DagHold as error:
        return _held(plan, "pair_reservation", ("whole_transition_traversal_work_exceeds_limit_no_prefix",), codec_hold_reason=str(error))
    work += transition_measurement
    max_transition = max((s["expanded_bytes"] + s["expanded_visits"] for s in transition_stats), default=0)
    # Full original-row arithmetic/run scans, pointer/list/map construction,
    # and fixed compact record/hash field visits, plus copied cut assumptions.
    pair_work = pairs * (atoms * 48 + 1024 + max_transition * 2)
    plan = _work_hold(plan, "canonicalization", work + canonical + refine_work + pair_work, limits,
        canonicalization_work=canonical, pair_work=pair_work,
        dag_expanded_bytes=measured["expanded_bytes"], dag_expanded_visits=measured["expanded_visits"])
    if plan.reasons:
        return plan
    # This pre-encoding bound accounts for integer row pointers, exact rational
    # endpoints, pair indexes and immutable header/seal; DAG has its own byte
    # cap reduced by this reserve. Source bodies are NOT retained here.
    index_upper = row_count * 384 + vectors * 24 + atoms * 192 + n * 16384 + 32768
    plan = replace(plan, catalog_byte_upper_bound=index_upper)
    if index_upper >= limits.max_catalog_bytes:
        return _held(plan, "compact_catalog_reservation", ("whole_index_bytes_exceeds_limit_no_prefix",))
    try:
        payload = dag.encode_json(composite, limits=dag.DagLimits(max_input_visits=measured["expanded_visits"],
            max_work_units=limits.max_work - work - measured["charged_work_units"] - refine_work - pair_work,
            max_expanded_bytes=measured["expanded_bytes"], max_encoded_bytes=limits.max_catalog_bytes - index_upper))
    except dag.DagHold as error:
        return _held(plan, "compact_catalog_encoding", ("whole_dag_bytes_or_traversal_exceeds_limit_no_prefix",), codec_hold_reason=str(error))
    encoded = len(payload.json_bytes())
    observed_canonical = measured["charged_work_units"] + payload.stats()["charged_work_units"]
    observed_work = plan.planned_work_upper_bound - canonical + observed_canonical
    plan = _work_hold(plan, "compact_catalog_encoding", observed_work, limits,
        canonicalization_work=observed_canonical, dag_encoded_bytes=encoded,
        catalog_byte_upper_bound=encoded + index_upper)
    if plan.reasons:
        return plan
    refinement = _refinement(facets, sound_points, bass_points)
    pair_index = _pair_index(payload, facets)
    group = shared._seal({"version": VERSION, "source_catalog_ref": source.source_ref,
        "scope_ref": kernels._ref(state.catalog["source_scope"]), "lattice_ref": kernels._ref(state.catalog["lattice"]),
        "key_ref": effective_key, "bundle_ref": effective_bundle,
        "completion_request_ref": codec._copy(completion_request_ref), "original_selector_indices": codec._copy(indices),
        "entry_refs": [{"native_path_ref": kernels._ref(e["native_path"]), "role_path_ref": kernels._ref(e["role_path"]),
            "comparison_ref": codec._copy(e["comparison_ref"]), "explanation_ref": codec._copy(e["explanation_ref"])}
            for e in entries]}, GROUP_PREFIX)
    plan = replace(plan, stage="complete")
    extras = {"version": VERSION, "codec": ENCODING, "source_authority": legacy.AUTHORITY,
        "source_catalog_ref": source.source_ref, "group": group, "group_ref": kernels._ref(group),
        "pair_index": pair_index, "refinement": refinement,
        "refinement_sha256": digest(refinement), "entry_inventory_sha256": digest(group["entry_refs"]),
        "all_original_entry_roots": [dag.node_at(payload, ("entries", i)) for i in range(n)],
        "all_original_facet_roots": [dag.node_at(payload, ("facets", i)) for i in range(n)],
        "actual_refinement_atoms": atoms, "preflight_plan": plan.record(),
        "selected": None, "rank": None, "confidence": None, "flags": legacy._flags()}
    # Exact scalar lengths in original refs/accounts and rational endpoints are
    # measured here, before the whole DAG table is exported or catalog hashed.
    # The earlier index reserve is only an encoding-stage conservative reserve;
    # the final bound uses actual extra JSON bytes rather than fixed point sizes.
    try:
        extra_stats = _measure(extras, limits, limits.max_work - plan.planned_work_upper_bound)
    except dag.DagHold as error:
        return _held(plan, "catalog_finalization", ("whole_catalog_extra_traversal_exceeds_limit_no_prefix",), codec_hold_reason=str(error))
    upper = encoded + extra_stats["expanded_bytes"] + 512
    finalization = extra_stats["charged_work_units"] + upper * 4
    plan = _work_hold(plan, "catalog_finalization", plan.planned_work_upper_bound + finalization,
        limits, catalog_finalization_work=finalization, catalog_byte_upper_bound=upper)
    if plan.reasons:
        return plan
    if upper > limits.max_catalog_bytes:
        return _held(plan, "catalog_finalization", ("whole_catalog_bytes_exceeds_limit_no_prefix",))
    plan = replace(plan, stage="complete")
    body = {**extras, "payload": payload.record(), "preflight_plan": plan.record()}
    catalog = shared._seal(body, CATALOG_PREFIX)
    actual = codec._bytes(catalog)
    # The scalar actual byte field isn't embedded recursively into its own
    # catalog seal. The plan property is the exact observed catalog size.
    plan = replace(plan, actual_catalog_bytes=actual)
    if actual > plan.catalog_byte_upper_bound or actual > limits.max_catalog_bytes:
        return _held(plan, "compact_catalog_actual", ("whole_actual_catalog_bytes_exceeds_limit_no_prefix",))
    frozen = codec._freeze(catalog)
    if before != digest(original):
        raise ValueError("saved_group_inputs_modified_during_preparation")
    shared._source_issued(source)
    # The weak plan registry must not retain its own key through state.plan.
    # Issued groups retain the scalar plan, but an abandoned draft is reclaimed.
    owned = _State(source, payload, frozen, None, limits, b"")
    _PLANS[plan] = replace(owned, signature=_signature(plan, owned))
    return plan


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
        return codec._copy(_issued(self).catalog)

    def export_entry(self, index):
        state = _issued(self)
        _index(state, index)
        return dag.value_at(state.payload, ("entries", index))

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
