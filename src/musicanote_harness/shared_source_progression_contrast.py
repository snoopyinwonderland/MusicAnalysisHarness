"""Saved contrasts with one immutable source catalog shared by local groups.

This versioned codec does not issue native authority, rerun role predicates,
select harmony, or authenticate archive membership. A source seal is checked
once; exact saved profiles, clauses and union accounts are checked per group.
Only the local entries/facets/refinement are retained in each group catalog.
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
from . import native_progression_contrast as legacy
from .musical_pattern_observation import digest, f, q

VERSION = "shared-source-progression-contrast-0.1.0"
SOURCE_PREFIX = "sspcsource_"
GROUP_PREFIX = "sspcgroup_"
CATALOG_PREFIX = "sspccatalog_"
PAIR_PREFIX = "sspcpair_"
BLOCK_PREFIX = "sspcblock_"
PLAN_PREFIX = "sspcplan_"
AUTHORITY = legacy.AUTHORITY
CATEGORIES = legacy.CATEGORIES
_SOURCES, _GROUPS = WeakKeyDictionary(), WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)


def _seal(body, prefix):
    # Inputs are read-only until freeze. Unlike the legacy general-purpose
    # sealer, do not make a second whole-source deepcopy here.
    checksum = digest(body)
    return {**body, "record_id": prefix + checksum[:24], "record_sha256": checksum}


@dataclass(frozen=True, slots=True)
class SourceLimits:
    max_catalogs: int = 1024
    max_origins: int = 200000
    max_sounds: int = 100000
    max_keys: int = 128
    max_bundles: int = 128
    max_source_record_bytes: int = 268435456
    max_source_work: int = 1000000000

    def __post_init__(self):
        for name, value in asdict(self).items():
            codec._integer(value, name)


@dataclass(frozen=True, slots=True)
class SourcePlan:
    catalog_count: int
    origin_count: int
    sound_count: int
    key_count: int
    bundle_count: int
    input_json_bytes: int | None
    source_record_byte_upper_bound: int | None
    planned_work_upper_bound: int | None
    reasons: tuple[str, ...]

    @property
    def status(self):
        return "whole_saved_source_hold" if self.reasons else "admissible_saved_source_preflight"

    def record(self):
        return _seal({"version": VERSION, **asdict(self), "reasons": list(self.reasons),
            "status": self.status, "semantics": "source_once_logical_encoded_bounds_not_RSS_or_accuracy"}, PLAN_PREFIX)


class WholeSourceHold(ValueError):
    def __init__(self, plan):
        self.plan = plan
        super().__init__("whole_saved_source_hold:" + ",".join(plan.reasons))


def preflight_saved_source(scope, lattice, *, bundles, limits=None):
    limits = SourceLimits() if limits is None else limits
    if (type(limits) is not SourceLimits or type(scope) is not dict
            or type(lattice) is not dict or type(bundles) is not dict
            or type(lattice.get("catalog_inventory")) is not list
            or type(lattice.get("keys")) is not list
            or type(scope.get("sound_facts")) is not list):
        raise ValueError("closed_saved_source_inputs_required")
    catalogs = lattice["catalog_inventory"]
    if any(type(c) is not dict or type(c.get("origins")) is not list for c in catalogs):
        raise ValueError("closed_saved_origin_inventory_required")
    counts = (len(catalogs), sum(len(c["origins"]) for c in catalogs),
        len(scope["sound_facts"]), len(lattice["keys"]), len(bundles))
    names = ("catalogs", "origins", "sounds", "keys", "bundles")
    caps = (limits.max_catalogs, limits.max_origins, limits.max_sounds,
        limits.max_keys, limits.max_bundles)
    reasons = tuple("whole_" + name + "_exceeds_source_limit_no_prefix"
        for name, count, cap in zip(names, counts, caps) if count > cap)
    if reasons:
        return SourcePlan(*counts, None, None, None, reasons)
    codec._no_float([scope, lattice, bundles])
    input_bytes = codec._bytes([scope, lattice, bundles])
    # The retained record wraps these bodies once. Metadata consists only of
    # fixed field names, references and this fixed-size numeric plan, not an
    # origin/ref inventory repeated next to the original lattice.
    bound = input_bytes + 16384
    work = input_bytes * 8 + sum(counts) * 64
    reasons = tuple("whole_" + name + "_exceeds_source_limit_no_prefix"
        for name, value, cap in (("source_record_bytes", bound, limits.max_source_record_bytes),
            ("source_work", work, limits.max_source_work)) if value > cap)
    return SourcePlan(*counts, input_bytes, bound, work, reasons)


@dataclass(frozen=True, slots=True)
class _SourceState:
    catalog: object
    origins: object
    keys: object
    sounds: object
    origin_member_counts: object
    origin_bytes: object
    scope_bytes: int
    plan: SourcePlan
    limits: SourceLimits
    signature: bytes


def _source_signature(handle, state):
    body = [id(handle), id(state.catalog), state.catalog["record_sha256"],
        id(state.origins), id(state.keys), id(state.sounds), id(state.origin_member_counts),
        id(state.origin_bytes), state.scope_bytes,
        digest(asdict(state.plan)), digest(asdict(state.limits))]
    return hmac.digest(_SECRET, json.dumps(body, separators=(",", ":")).encode(), "sha256")


def _source_issued(handle):
    if type(handle) is not PreparedSource or handle not in _SOURCES:
        raise ValueError("registered_validated_shared_source_required")
    state = _SOURCES[handle]
    if (type(state) is not _SourceState or type(state.catalog) is not MappingProxyType
            or any(type(v) is not MappingProxyType for v in (state.origins, state.keys,
                state.sounds, state.origin_member_counts, state.origin_bytes))
            or type(state.plan) is not SourcePlan or type(state.limits) is not SourceLimits
            or not hmac.compare_digest(state.signature, _source_signature(handle, state))):
        raise ValueError("owned_validated_shared_source_state_changed")
    return state


class PreparedSource:
    """Owned saved source. Exported JSON cannot reconstruct this authority."""
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise ValueError("validated_shared_source_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_shared_source")

    @property
    def source_ref(self):
        return kernels._ref(_source_issued(self).catalog)

    @property
    def preflight_plan(self):
        return _source_issued(self).plan

    def export_source(self):
        return codec._copy(_source_issued(self).catalog)


def prepare_saved_source(scope, lattice, *, bundles, limits=None):
    limits = SourceLimits() if limits is None else limits
    plan = preflight_saved_source(scope, lattice, bundles=bundles, limits=limits)
    if plan.reasons:
        raise WholeSourceHold(plan)
    before = digest([scope, lattice, bundles])
    kernels._check(scope, "fmes_")
    kernels._check(lattice, native.PREFIX)
    if (lattice["scope_ref"] != kernels._ref(scope) or lattice["binding"] != scope["binding"]
            or lattice["analysis_span"] != scope["analysis_span"]):
        raise ValueError("saved_scope_lattice_binding_mismatch")
    origins = legacy._lookup([o for c in lattice["catalog_inventory"] for o in c["origins"]], "origin")
    keys = legacy._lookup(lattice["keys"], "key")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    if len(sounds) != len(scope["sound_facts"]):
        raise ValueError("duplicate_source_sound_reference")
    for containing in lattice["catalog_inventory"]:
        for origin in containing["origins"]:
            kernels._check(origin, native.ORIGIN_PREFIX)
            if (origin["source_scope_ref"] != kernels._ref(scope)
                    or origin["scope_ref"] != kernels._ref(scope)
                    or origin["catalog_id"] != containing["catalog_id"]
                    or origin["span"] != containing["span"]):
                raise ValueError("foreign_saved_origin_scope_or_catalog")
    for key in keys.values():
        kernels._check(key, kernels.KEY_PREFIX)
        if (key["scope_ref"] != kernels._ref(scope) or key["binding"] != scope["binding"]
                or key["analysis_span"] != scope["analysis_span"]
                or len(key["segments"]) != 1 or key["segments"][0]["span"] != scope["analysis_span"]):
            raise ValueError("foreign_saved_key_scope")
    for identity, bundle in bundles.items():
        kernels._check(bundle, native.BUNDLE_PREFIX)
        if (identity != bundle["record_id"] or bundle["scope_ref"] != kernels._ref(scope)
                or bundle["binding"] != scope["binding"] or bundle["lattice_ref"] != kernels._ref(lattice)
                or bundle["analysis_span"] != scope["analysis_span"]):
            raise ValueError("foreign_saved_completion")
    catalog = _seal({"version": VERSION, "codec": "source-shared-original-row-refinement-v1",
        "source_authority": AUTHORITY, "source_scope": scope, "lattice": lattice,
        "bundles": bundles, "preflight_plan": plan.record(),
        "selected": None, "rank": None, "confidence": None, "flags": legacy._flags()}, SOURCE_PREFIX)
    if codec._bytes(catalog) > plan.source_record_byte_upper_bound:
        raise ValueError("source_record_exceeded_declared_byte_upper_bound")
    origin_bytes = MappingProxyType({key: codec._bytes(o) for key, o in origins.items()})
    scope_bytes = codec._bytes(scope)
    handle = object.__new__(PreparedSource)
    frozen = codec._freeze(catalog)
    if before != digest([scope, lattice, bundles]):
        raise ValueError("saved_source_inputs_modified_during_preparation")
    # Index values point INTO the frozen single catalog; no origin copies.
    indexed_origins = MappingProxyType({o["record_id"]: o for c in frozen["lattice"]["catalog_inventory"] for o in c["origins"]})
    indexed_keys = MappingProxyType({k["record_id"]: k for k in frozen["lattice"]["keys"]})
    indexed_sounds = MappingProxyType({s["sound_ref"]: s for s in frozen["source_scope"]["sound_facts"]})
    members = MappingProxyType({key: len(o["members"] or ()) for key, o in indexed_origins.items()})
    state = _SourceState(frozen, indexed_origins, indexed_keys, indexed_sounds, members,
        origin_bytes, scope_bytes, plan, limits, b"")
    _SOURCES[handle] = replace(state, signature=_source_signature(handle, state))
    return handle


@dataclass(frozen=True, slots=True)
class GroupLimits:
    max_entries: int = 1024
    max_refinement_atoms: int = 200000
    max_vector_cells: int = 10000000
    max_pairs: int = 2000000
    max_work: int = 1000000000
    max_block_pairs: int = 4096
    max_catalog_bytes: int = 268435456
    max_pair_record_bytes: int = 4194304
    max_block_record_bytes: int = 67108864

    def __post_init__(self):
        for name, value in asdict(self).items():
            codec._integer(value, name)


@dataclass(frozen=True, slots=True)
class GroupPlan:
    entry_count: int
    planned_pairs: int
    planned_blocks: int
    refinement_atom_upper_bound: int | None
    vector_cell_upper_bound: int | None
    planned_work_upper_bound: int | None
    local_input_json_bytes: int | None
    catalog_byte_upper_bound: int | None
    block_size: int
    reasons: tuple[str, ...]

    @property
    def status(self):
        return "whole_shared_group_hold" if self.reasons else "admissible_shared_group_preflight"

    def record(self):
        return _seal({"version": VERSION, **asdict(self), "reasons": list(self.reasons),
            "status": self.status, "semantics": "local_group_logical_encoded_bounds_not_source_copy_or_RSS"}, PLAN_PREFIX)


class WholeGroupHold(ValueError):
    def __init__(self, plan):
        self.plan = plan
        super().__init__("whole_shared_group_hold:" + ",".join(plan.reasons))


def _premises(state, entries, key_ref, bundle_ref):
    if entries:
        first = entries[0]["native_path"]
        key_ref = first["key_ref"] if key_ref is None else key_ref
        bundle_ref = first["bundle_ref"] if bundle_ref is None else bundle_ref
    if key_ref is None or bundle_ref is None:
        raise ValueError("empty_group_requires_original_key_and_bundle_refs")
    for ref, records in ((key_ref, state.keys), (bundle_ref, state.catalog["bundles"])):
        codec._exact_ref(ref)
        if ref["record_id"] not in records or ref != kernels._ref(records[ref["record_id"]]):
            raise ValueError("foreign_shared_group_key_or_bundle")
    return deepcopy(key_ref), deepcopy(bundle_ref)


def preflight_saved_group(source, entries, *, completion_request_ref, selector_indices=None,
        key_ref=None, bundle_ref=None, block_size=64, limits=None):
    state = _source_issued(source)
    limits = GroupLimits() if limits is None else limits
    if type(limits) is not GroupLimits or type(entries) is not list:
        raise ValueError("closed_shared_group_inputs_required")
    codec._integer(block_size, "block_size", positive=True)
    if block_size > 64:
        raise ValueError("block_size_must_be_between_1_and_64")
    codec._exact_ref(completion_request_ref)
    count = len(entries)
    pairs = count * (count - 1) // 2
    full, tail = divmod(count, block_size)
    grid = full + bool(tail)
    blocks = grid * (grid - 1) // 2 + full * (block_size > 1) + (tail > 1)
    max_pairs = max(block_size * (block_size - 1) // 2 if full else 0,
        tail * (tail - 1) // 2, block_size ** 2 if full >= 2 else 0,
        block_size * tail if full and tail else 0)
    reasons = ["whole_" + name + "_exceeds_limit_no_prefix" for name, value, cap in
        (("entries", count, limits.max_entries), ("pairs", pairs, limits.max_pairs),
         ("block_pairs", max_pairs, limits.max_block_pairs)) if value > cap]
    if pairs and limits.max_pair_record_bytes < 64:
        reasons.append("whole_pair_record_minimum_bytes_exceeds_limit_no_prefix")
    if pairs and limits.max_block_record_bytes < 128:
        reasons.append("whole_block_record_minimum_bytes_exceeds_limit_no_prefix")
    if reasons:
        return GroupPlan(count, pairs, blocks, None, None, None, None, None, block_size, tuple(reasons))
    indices = list(range(count)) if selector_indices is None else selector_indices
    if (type(indices) is not list or len(indices) != count or
            any(type(i) is not int or i < 0 for i in indices) or indices != sorted(set(indices))):
        raise ValueError("unique_ordered_original_selector_indices_required")
    codec._no_float([entries, completion_request_ref, key_ref, bundle_ref])
    atom_bound = cell_bound = presentation_bound = attribution_bound = 0
    for entry in entries:
        if type(entry) is not dict or set(entry) != {"native_path", "role_path", "comparison_ref", "explanation_ref"}:
            raise ValueError("closed_saved_contrast_entry_required")
        codec._exact_ref(entry["comparison_ref"])
        codec._exact_ref(entry["explanation_ref"])
        path, role = entry["native_path"], entry["role_path"]
        if not path.get("profiles") or "account" not in role:
            raise ValueError("missing_or_held_entry_is_not_known_empty")
        if len(path["profiles"]) != len(path["origin_refs"]):
            raise ValueError("complete_saved_profile_inventory_required")
        unions = {r["sound_ref"]: len(r["spans"]) for r in role["account"]["explained_intervals_by_sound"]}
        for profile, origin in zip(path["profiles"], path["origin_refs"]):
            rows = len(profile["rows"])
            if origin["record_id"] not in state.origins:
                raise ValueError("foreign_saved_origin_reference")
            presentation_bound += rows * max(1, state.origin_member_counts[origin["record_id"]])
            cell_bound += len(profile["cells"])
            atoms = sum(1 + 2 * unions.get(r["sound_ref"], 0) for r in profile["rows"])
            atom_bound += atoms
            attribution_bound += atoms * len(role.get("clauses", []))
    actual_key, actual_bundle = _premises(state, entries, key_ref, bundle_ref)
    refinement = 2 * (atom_bound + cell_bound)
    vectors = count * refinement
    # Scope projection is small and has no lattice; source is never exported.
    scope = codec._copy(state.catalog["source_scope"])
    projected_ids = {ref["record_id"] for e in entries for ref in e["native_path"]["origin_refs"]}
    projection_work = state.scope_bytes * 8 + sum(state.origin_bytes[oid] for oid in projected_ids) * 4
    work = legacy._plan(scope, entries, [])["planned_work"] + projection_work + vectors + pairs * (2 * refinement + 32)
    input_bytes = codec._bytes([entries, completion_request_ref, indices, source.source_ref, actual_key, actual_bundle])
    max_sound_bytes = max((codec._bytes(s) for s in scope["sound_facts"]), default=0)
    bound = input_bytes * 8 + (atom_bound + cell_bound) * 2048 + attribution_bound * 256 \
        + presentation_bound * (max_sound_bytes + 2048) + vectors * 32 + refinement * 512 + 16384
    reasons = tuple("whole_" + name + "_exceeds_limit_no_prefix" for name, value, cap in
        (("refinement_atoms", refinement, limits.max_refinement_atoms),
         ("vector_cells", vectors, limits.max_vector_cells), ("work", work, limits.max_work),
         ("catalog_bytes", bound, limits.max_catalog_bytes)) if value > cap)
    return GroupPlan(count, pairs, blocks, refinement, vectors, work, input_bytes, bound, block_size, reasons)


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


def plan_blocks(entry_count, block_size=64):
    for task in codec.plan_blocks(entry_count, block_size):
        yield BlockTask(task.row_start, task.row_end, task.column_start, task.column_end, task.expected_pairs)


@dataclass(frozen=True, slots=True)
class _GroupState:
    source: PreparedSource
    catalog: object
    plan: GroupPlan
    limits: GroupLimits
    sound_points: tuple
    bass_points: tuple
    signature: bytes


def _group_signature(handle, state):
    body = [id(handle), id(state.source), state.source.source_ref, id(state.catalog),
        state.catalog["record_sha256"], digest(asdict(state.plan)), digest(asdict(state.limits)),
        id(state.sound_points), id(state.bass_points)]
    return hmac.digest(_SECRET, json.dumps(body, separators=(",", ":")).encode(), "sha256")


def _issued(handle):
    if type(handle) is not SharedPreparedGroup or handle not in _GROUPS:
        raise ValueError("registered_validated_shared_group_required")
    state = _GROUPS[handle]
    if (type(state) is not _GroupState or type(state.catalog) is not MappingProxyType
            or type(state.plan) is not GroupPlan or type(state.limits) is not GroupLimits
            or not hmac.compare_digest(state.signature, _group_signature(handle, state))):
        raise ValueError("owned_validated_shared_group_state_changed")
    _source_issued(state.source)
    return state


class SharedPreparedGroup:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise ValueError("validated_shared_group_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_shared_group")

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

    def iter_blocks(self):
        state = _issued(self)
        for task in plan_blocks(state.plan.entry_count, state.plan.block_size):
            yield replace(task, source_sha256=state.source.source_ref["record_sha256"],
                group_sha256=state.catalog["group_ref"]["record_sha256"],
                refinement_sha256=state.catalog["refinement_sha256"],
                entry_inventory_sha256=state.catalog["entry_inventory_sha256"])


def prepare_saved_group(source, entries, *, completion_request_ref, selector_indices=None,
        key_ref=None, bundle_ref=None, block_size=64, limits=None):
    limits = GroupLimits() if limits is None else limits
    plan = preflight_saved_group(source, entries, completion_request_ref=completion_request_ref,
        selector_indices=selector_indices, key_ref=key_ref, bundle_ref=bundle_ref,
        block_size=block_size, limits=limits)
    if plan.reasons:
        raise WholeGroupHold(plan)
    state = _source_issued(source)
    before = digest([entries, completion_request_ref, selector_indices, key_ref, bundle_ref])
    input_key_ref, input_bundle_ref = key_ref, bundle_ref
    key_ref, bundle_ref = _premises(state, entries, key_ref, bundle_ref)
    # Only needed source projections are thawed. The exact lattice identity
    # header is sufficient for legacy validator; it is never resealed or public.
    scope = codec._copy(state.catalog["source_scope"])
    lattice_header = kernels._ref(state.catalog["lattice"])
    origin_ids = {ref["record_id"] for e in entries for ref in e["native_path"]["origin_refs"]}
    origins = {oid: codec._copy(state.origins[oid]) for oid in origin_ids}
    keys = {key_ref["record_id"]: codec._copy(state.keys[key_ref["record_id"]])}
    bundles = {bundle_ref["record_id"]: codec._copy(state.catalog["bundles"][bundle_ref["record_id"]])}
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    facets, cache, seen = [], {}, set()
    for entry in entries:
        path = entry["native_path"]
        if path["key_ref"] != key_ref or path["bundle_ref"] != bundle_ref:
            raise ValueError("one_exact_key_bundle_completion_group_required")
        identity = digest(path["logical_tuple"])
        if identity in seen:
            raise ValueError("duplicate_saved_complete_hypothesis")
        seen.add(identity)
        chosen = legacy._validate_entry(entry, scope, lattice_header, origins, keys, bundles, sounds, cache)
        facets.append(legacy._facet(entry, scope, chosen, sounds))
    indices = list(range(len(entries))) if selector_indices is None else deepcopy(selector_indices)
    group = _seal({"version": VERSION, "source_authority": AUTHORITY,
        "source_catalog_ref": source.source_ref, "scope_ref": kernels._ref(state.catalog["source_scope"]),
        "lattice_ref": kernels._ref(state.catalog["lattice"]), "key_ref": key_ref, "bundle_ref": bundle_ref,
        "completion_request_ref": deepcopy(completion_request_ref), "original_selector_indices": indices,
        "entry_refs": [{"native_path_ref": kernels._ref(e["native_path"]),
            "role_path_ref": kernels._ref(e["role_path"]), "comparison_ref": deepcopy(e["comparison_ref"]),
            "explanation_ref": deepcopy(e["explanation_ref"])} for e in entries]}, GROUP_PREFIX)
    refinement = codec._refine(facets)
    atoms = sum(max(0, len(s["points"]) - 1) for s in refinement["sounds"]) \
        + max(0, len(refinement["bass"]["points"]) - 1)
    if atoms > plan.refinement_atom_upper_bound:
        raise ValueError("refinement_exceeded_declared_upper_bound")
    catalog = _seal({"version": VERSION, "codec": "source-shared-original-row-refinement-v1",
        "source_authority": AUTHORITY, "source_catalog_ref": source.source_ref,
        "group": group, "group_ref": kernels._ref(group), "entries": entries, "facets": facets,
        "refinement": refinement, "refinement_sha256": digest(refinement),
        "entry_inventory_sha256": digest(group["entry_refs"]), "preflight_plan": plan.record(),
        "actual_refinement_atoms": atoms, "selected": None, "rank": None, "confidence": None,
        "flags": legacy._flags()}, CATALOG_PREFIX)
    actual = codec._bytes(catalog)
    if actual > plan.catalog_byte_upper_bound:
        raise ValueError("catalog_exceeded_declared_byte_upper_bound")
    if actual > limits.max_catalog_bytes:
        raise WholeGroupHold(replace(plan, reasons=("whole_actual_catalog_bytes_exceeds_limit_no_prefix",)))
    handle = object.__new__(SharedPreparedGroup)
    frozen = codec._freeze(catalog)
    points = tuple(tuple((p["numerator"], p["denominator"]) for p in s["points"]) for s in frozen["refinement"]["sounds"])
    bass_points = tuple((p["numerator"], p["denominator"]) for p in frozen["refinement"]["bass"]["points"])
    # Freeze and all caller-derived copies must finish BEFORE the final input
    # guard; no mutable caller body is touched after this guard.
    if before != digest([entries, completion_request_ref, selector_indices, input_key_ref, input_bundle_ref]):
        raise ValueError("saved_group_inputs_modified_during_preparation")
    _source_issued(source)
    owned = _GroupState(source, frozen, plan, limits, points, bass_points, b"")
    _GROUPS[handle] = replace(owned, signature=_group_signature(handle, owned))
    return handle


def _compact_pair(prepared, i, j):
    state = _issued(prepared)
    catalog = state.catalog
    left, right = catalog["facets"][i], catalog["facets"][j]
    transfers, changes = Counter(), []
    for si, sound in enumerate(catalog["refinement"]["sounds"]):
        points = tuple(Fraction(n, d) for n, d in state.sound_points[si])
        sid = sound["sound_ref"]
        for a, b, li, ri in codec._runs(points, sound["vectors"][i], sound["vectors"][j]):
            lrow, rrow = left["source_segments"][sid][li], right["source_segments"][sid][ri]
            transfers[(lrow["category"], rrow["category"])] += points[b] - points[a]
            if lrow["category"] != rrow["category"]:
                changes.append([si, a, b, li, ri])
    raw = f(left["account"]["raw_total_note_time_quarters"])
    if raw != f(right["account"]["raw_total_note_time_quarters"]) or sum(transfers.values(), Fraction()) != raw:
        raise ValueError("pairwise_raw_note_time_not_conserved")
    bass = catalog["refinement"]["bass"]
    bass_runs = []
    for a, b, li, ri in codec._runs(bass["points"], bass["vectors"][i], bass["vectors"][j]):
        lcell, rcell = left["bass_cells"][li], right["bass_cells"][ri]
        if lcell["sound_refs"] != rcell["sound_refs"] or lcell["bass_refs"] != rcell["bass_refs"]:
            raise ValueError("aligned_raw_bass_observations_changed_between_candidates")
        bass_runs.append([a, b, li, ri])
    lcuts = {f(s["start"]): v for s, v in zip(left["partition"][1:], left["transition_assumptions"])}
    rcuts = {f(s["start"]): v for s, v in zip(right["partition"][1:], right["transition_assumptions"])}
    ls = [(s["root"], s["members"]) for s in left["slot_presentations"]]
    rs = [(s["root"], s["members"]) for s in right["slot_presentations"]]
    partition = left["partition"] == right["partition"]
    vector = left["transition_assumptions"] == right["transition_assumptions"]
    kind = "partition" if not partition else "candidate_only" if vector else "transition_only" if ls == rs else "candidate_and_transition"
    lc, rc = (fa["account"]["conditional_explanation_note_time_quarters"] for fa in (left, right))
    return _seal({"version": VERSION, "codec": "source-shared-original-row-refinement-v1",
        "source_catalog_ref": prepared.source_ref, "catalog_ref": prepared.catalog_ref, "group_ref": prepared.group_ref,
        "refinement_sha256": catalog["refinement_sha256"], "entry_indices": [i, j],
        "original_selector_indices": [catalog["group"]["original_selector_indices"][i], catalog["group"]["original_selector_indices"][j]],
        "comparison_kind": kind, "same_partition": partition, "alias_control": partition and vector and ls == rs,
        "shared_cut_assumptions": [{"time": q(t), "left": codec._copy(lcuts[t]), "right": codec._copy(rcuts[t]),
            "same_assumption": lcuts[t] == rcuts[t]} for t in sorted(lcuts.keys() & rcuts.keys())],
        "left_only_cuts": [q(t) for t in sorted(lcuts.keys() - rcuts.keys())],
        "right_only_cuts": [q(t) for t in sorted(rcuts.keys() - lcuts.keys())],
        "raw_total_note_time_quarters": q(raw), "raw_time_conserved": True,
        "note_time_delta_right_minus_left": {c: q(f(right["account"]["note_time_quarters"][c]) - f(left["account"]["note_time_quarters"][c])) for c in CATEGORIES},
        "conditional_credit_delta_right_minus_left": None if lc is None or rc is None else q(f(rc) - f(lc)),
        "category_transfer_note_time": [{"left": a, "right": b, "duration_quarters": q(v)} for (a, b), v in sorted(transfers.items())],
        "changed_source_segment_pointers": changes, "aligned_bass_cell_pointers": bass_runs,
        "logical_atom_visits": sum(len(s["vectors"][i]) for s in catalog["refinement"]["sounds"]) + len(bass["vectors"][i]),
        "status": "computed_saved_pair_contrast_not_selected", "musical_outcome": None,
        "selected": None, "rank": None, "confidence": None}, PAIR_PREFIX)


def compare_block(prepared, task):
    state = _issued(prepared)
    if type(task) is not BlockTask:
        raise ValueError("validated_shared_group_and_exact_block_task_required")
    n, size = state.plan.entry_count, state.plan.block_size
    values = (task.row_start, task.row_end, task.column_start, task.column_end, task.expected_pairs)
    row_size = task.row_end - task.row_start if all(type(v) is int for v in values) else -1
    expected = row_size * (row_size - 1) // 2 if task.row_start == task.column_start else row_size * (task.column_end - task.column_start) if row_size >= 0 else -1
    if (any(type(v) is not int for v in values) or not 0 <= task.row_start <= task.column_start < n
            or task.row_start % size or task.column_start % size
            or task.row_end != min(task.row_start + size, n) or task.column_end != min(task.column_start + size, n)
            or task.expected_pairs != expected or expected <= 0
            or any(type(v) is not str for v in (task.source_sha256, task.group_sha256,
                task.refinement_sha256, task.entry_inventory_sha256))
            or task.source_sha256 != prepared.source_ref["record_sha256"]
            or task.group_sha256 != state.catalog["group_ref"]["record_sha256"]
            or task.refinement_sha256 != state.catalog["refinement_sha256"]
            or task.entry_inventory_sha256 != state.catalog["entry_inventory_sha256"]):
        raise ValueError("foreign_or_modified_shared_block_task")
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
    body = {"version": VERSION, "source_catalog_ref": prepared.source_ref,
        "catalog_ref": prepared.catalog_ref, "group_ref": prepared.group_ref,
        "refinement_sha256": state.catalog["refinement_sha256"], "entry_inventory_sha256": state.catalog["entry_inventory_sha256"],
        "task": asdict(task), "planned_pairs": task.expected_pairs, "computed_pairs": len(pairs),
        "withheld_pairs": task.expected_pairs - len(pairs), "pairs": pairs, "reasons": reasons,
        "status": "whole_saved_block_hold" if reasons else "computed_saved_block_not_selected",
        "whole_group_complete": False, "musical_outcome": None,
        "selected": None, "rank": None, "confidence": None, "flags": legacy._flags()}
    if pairs and codec._bytes(body) + 256 > state.limits.max_block_record_bytes:
        body.update(pairs=[], computed_pairs=0, withheld_pairs=task.expected_pairs,
            reasons=["whole_block_encoded_bytes_exceeds_limit_no_prefix"], status="whole_saved_block_hold")
    return _seal(body, BLOCK_PREFIX)


def materialize_pair(prepared, pair):
    """Exact old explanation reconstructed from an owned source and local rows."""
    state = _issued(prepared)
    if type(pair) is not dict:
        raise ValueError("closed_saved_pair_record_required")
    codec._no_float(pair)
    kernels._check(pair, PAIR_PREFIX)
    if (pair["source_catalog_ref"] != prepared.source_ref or pair["catalog_ref"] != prepared.catalog_ref
            or pair["group_ref"] != prepared.group_ref):
        raise ValueError("foreign_saved_pair_source_or_catalog")
    i, j = pair["entry_indices"]
    if type(i) is not int or type(j) is not int or not 0 <= i < j < state.plan.entry_count:
        raise ValueError("ordered_group_pair_indices_required")
    if pair != _compact_pair(prepared, i, j):
        raise ValueError("saved_pair_disagrees_with_validated_catalog")
    catalog = state.catalog
    left, right = catalog["facets"][i], catalog["facets"][j]
    sounds = _source_issued(state.source).sounds
    differences = []
    for si, a, b, li, ri in pair["changed_source_segment_pointers"]:
        sound = catalog["refinement"]["sounds"][si]
        sid, points = sound["sound_ref"], sound["points"]
        differences.append({"sound_ref": sid, "source_note_refs": codec._copy(sounds[sid]["source_note_refs"]),
            "pitch": codec._copy(sounds[sid]["pitch"]), "full_sound_span": codec._copy(sounds[sid]["span"]),
            "span": {"start": codec._copy(points[a]), "end": codec._copy(points[b])},
            "left": codec._copy(left["source_segments"][sid][li]), "right": codec._copy(right["source_segments"][sid][ri])})
    bass, points = [], catalog["refinement"]["bass"]["points"]
    for a, b, li, ri in pair["aligned_bass_cell_pointers"]:
        lcell, rcell = left["bass_cells"][li], right["bass_cells"][ri]
        bass.append({"span": {"start": codec._copy(points[a]), "end": codec._copy(points[b])},
            "bass_refs": codec._copy(lcell["bass_refs"]),
            "left": {k: codec._copy(lcell[k]) for k in codec._BASS_FIELDS},
            "right": {k: codec._copy(rcell[k]) for k in codec._BASS_FIELDS},
            "bass_is_not_certified_structural_bass": True})
    fields = ("comparison_kind", "same_partition", "alias_control", "shared_cut_assumptions",
        "left_only_cuts", "right_only_cuts", "raw_total_note_time_quarters", "raw_time_conserved",
        "note_time_delta_right_minus_left", "category_transfer_note_time")
    return {"left_path_ref": codec._copy(left["native_path_ref"]), "right_path_ref": codec._copy(right["native_path_ref"]),
        "left_role_path_ref": codec._copy(left["role_path_ref"]), "right_role_path_ref": codec._copy(right["role_path_ref"]),
        "key_ref": codec._copy(left["key_ref"]), "bundle_ref": codec._copy(left["bundle_ref"]),
        **{k: deepcopy(pair[k]) for k in fields}, "changed_source_segments": differences, "aligned_bass_cells": bass,
        "selected": None, "rank": None, "confidence": None,
        "interpretation": "conditional_evidence_contrast_not_chord_selection"}
