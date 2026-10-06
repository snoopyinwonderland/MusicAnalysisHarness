"""Bounded contrasts of validated saved paths, without native authority or selection.

The caller authenticates physical files and original parent membership separately.
This module validates saved body seals/source accounts once, freezes the admitted
group, and compares original row indices over exact rational global refinements.
Refinement atoms are an acceleration structure, NEVER new musical segmentation.
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

from . import factor_expanded_hypotheses as kernels
from . import factor_interval_lattice as native
from . import native_progression_contrast as legacy
from .musical_pattern_observation import digest, f, q, span_bounds

VERSION = "cross-batch-progression-contrast-0.1.0"
CATALOG_PREFIX = "cbpcatalog_"
PAIR_PREFIX = "cbppair_"
BLOCK_PREFIX = "cbpblock_"
GROUP_PREFIX = "cbpgroup_"
PLAN_PREFIX = "cbpplan_"
AUTHORITY = legacy.AUTHORITY
CATEGORIES = legacy.CATEGORIES
_GROUPS = WeakKeyDictionary()
_SECRET = secrets.token_bytes(32)
_BASS_FIELDS = ("origin_ref", "slot_index", "bass_membership_status",
    "conditional_inversions", "conditional_bass_member_indices", "inversion_basis",
    "source_guard_missing_spellings", "bass_source_guards_passed",
    "strict_guard_missing_spellings", "strict_bass_source_guards_passed")


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if type(value) in (list, tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _copy(value):
    if isinstance(value, MappingProxyType):
        return {k: _copy(v) for k, v in value.items()}
    if type(value) is tuple:
        return [_copy(v) for v in value]
    return deepcopy(value)


def _bytes(value):
    return len(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8"))


def _integer(value, name, *, positive=False):
    if type(value) is not int or value < int(positive):
        raise ValueError("invalid_integer_limit:" + name)


def _exact_ref(ref):
    legacy._plain_ref(ref)
    if any(c not in "0123456789abcdef" for c in ref["record_sha256"]):
        raise ValueError("exact_hex_saved_reference_required")


def _no_float(value):
    if type(value) is float:
        raise ValueError("float_in_saved_rational_contract")
    if type(value) is dict:
        for child in value.values():
            _no_float(child)
    elif type(value) in (list, tuple):
        for child in value:
            _no_float(child)
    elif type(value) not in (str, bool, int, type(None)):
        raise ValueError("closed_plain_json_value_required")


@dataclass(frozen=True, slots=True)
class Limits:
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
            _integer(value, name)


@dataclass(frozen=True, slots=True)
class BlockTask:
    row_start: int
    row_end: int
    column_start: int
    column_end: int
    expected_pairs: int
    group_sha256: str | None = None
    refinement_sha256: str | None = None
    entry_inventory_sha256: str | None = None

    def pair_indices(self):
        for i in range(self.row_start, self.row_end):
            for j in range(self.column_start, self.column_end):
                if i < j:
                    yield i, j


def plan_blocks(entry_count, block_size=64):
    """Return ranges, not O(N**2) pair objects. Empty/single groups are known zero."""
    _integer(entry_count, "entry_count")
    _integer(block_size, "block_size", positive=True)
    if block_size > 64:
        raise ValueError("block_size_must_be_between_1_and_64")
    for row in range(0, entry_count, block_size):
        row_end = min(row + block_size, entry_count)
        for col in range(row, entry_count, block_size):
            col_end = min(col + block_size, entry_count)
            size = row_end - row
            pairs = size * (size - 1) // 2 if row == col else size * (col_end - col)
            if pairs:
                yield BlockTask(row, row_end, col, col_end, pairs)


@dataclass(frozen=True, slots=True)
class PreflightPlan:
    entry_count: int
    planned_pairs: int
    planned_blocks: int
    refinement_atom_upper_bound: int | None
    vector_cell_upper_bound: int | None
    planned_work_upper_bound: int | None
    input_json_bytes: int | None
    catalog_byte_upper_bound: int | None
    block_size: int
    reasons: tuple[str, ...]

    @property
    def status(self):
        return "whole_saved_group_hold" if self.reasons else "admissible_saved_group_preflight"

    def record(self):
        return kernels._seal({"version": VERSION, **asdict(self),
            "reasons": list(self.reasons), "status": self.status,
            "semantics": "logical_and_encoded_upper_bounds_not_CPU_RSS_or_accuracy"}, PLAN_PREFIX)


class WholeGroupHold(ValueError):
    """No validation facets or prefix contrast were issued; retain original plan."""
    def __init__(self, plan):
        self.plan = plan
        super().__init__("whole_saved_group_hold:" + ",".join(plan.reasons))


def preflight_saved_group(scope, lattice, entries, *, bundles,
        completion_request_ref, selector_indices=None, block_size=64, limits=None):
    """Logical/catalog admission, NOT whole-corpus storage or writer admission.

    Bodies are not authenticated by this estimate. Root admission must preserve
    held/missing ORIGINAL positions instead of removing them from this list.
    Total encoded output/storage and final manifest reserve remain unresolved
    until the separate writer plan; this result does not authorize a full run.
    """
    limits = Limits() if limits is None else limits
    if type(limits) is not Limits or type(entries) is not list or type(bundles) is not dict:
        raise ValueError("closed_saved_group_inputs_required")
    _integer(block_size, "block_size", positive=True)
    if block_size > 64:
        raise ValueError("block_size_must_be_between_1_and_64")
    _exact_ref(completion_request_ref)
    count = len(entries)
    pairs = count * (count - 1) // 2
    full, tail = divmod(count, block_size)
    grid = full + bool(tail)
    block_count = grid * (grid - 1) // 2 + full * (block_size > 1) + (tail > 1)
    max_block_pairs = max(block_size * (block_size - 1) // 2 if full else 0,
        tail * (tail - 1) // 2, block_size ** 2 if full >= 2 else 0,
        block_size * tail if full and tail else 0)
    count_reasons = ["whole_" + name + "_exceeds_limit_no_prefix"
        for name, value, cap in (("entries", count, limits.max_entries),
            ("pairs", pairs, limits.max_pairs), ("block_pairs", max_block_pairs, limits.max_block_pairs)) if value > cap]
    # Every computed sealed pair/block necessarily needs a positive body plus
    # at least a 64-character checksum. Do not perform costly facet work when
    # even this indisputable minimum cannot be written.
    if pairs and limits.max_pair_record_bytes < 64:
        count_reasons.append("whole_pair_record_minimum_bytes_exceeds_limit_no_prefix")
    if pairs and limits.max_block_record_bytes < 128:
        count_reasons.append("whole_block_record_minimum_bytes_exceeds_limit_no_prefix")
    if count_reasons:
        # O(1) count admission cannot inspect a forbidden giant entry list or
        # materialize its O(blocks**2) plan. Unknown fine-grained cost is null,
        # not zero; the ORIGINAL pair/block denominators remain exact.
        return PreflightPlan(count, pairs, block_count, None, None, None, None,
            None, block_size, tuple(count_reasons))
    indices = list(range(len(entries))) if selector_indices is None else selector_indices
    if (type(indices) is not list or len(indices) != len(entries)
            or any(type(i) is not int or i < 0 for i in indices)
            or indices != sorted(set(indices))):
        raise ValueError("unique_ordered_original_selector_indices_required")
    origin_member_counts = {o["record_id"]: len(o.get("members") or [])
        for catalog in lattice["catalog_inventory"] for o in catalog["origins"]}
    atom_bound, cell_bound, presentation_bound, attribution_bound = 0, 0, 0, 0
    for entry in entries:
        if type(entry) is not dict or set(entry) != {"native_path", "role_path", "comparison_ref", "explanation_ref"}:
            raise ValueError("closed_saved_contrast_entry_required")
        path, role = entry["native_path"], entry["role_path"]
        if not path.get("profiles") or "account" not in role:
            raise ValueError("missing_or_held_entry_is_not_known_empty")
        union_counts = {r["sound_ref"]: len(r["spans"])
            for r in role["account"]["explained_intervals_by_sound"]}
        for profile, origin in zip(path["profiles"], path["origin_refs"]):
            rows = len(profile["rows"])
            presentation_bound += rows * max(1, origin_member_counts.get(origin["record_id"], 0))
            cell_bound += len(profile["cells"])
            atoms = sum(1 + 2 * union_counts.get(row["sound_ref"], 0) for row in profile["rows"])
            atom_bound += atoms
            attribution_bound += atoms * len(role.get("clauses", []))
    # Two endpoints per original attributed segment / literal bass cell are a
    # safe global refinement count bound. Each sound keeps its own multiplicity.
    refinement = 2 * (atom_bound + cell_bound)
    vectors = len(entries) * refinement
    # Legacy count-only entry planner includes account/profile validation scans;
    # no role predicate, native issuer, facet or pair is computed here.
    entry_work = legacy._plan(scope, entries, [])["planned_work"]
    # Charge local Fraction reconstruction AND the atom/run scan explicitly.
    work = entry_work + vectors + pairs * (2 * refinement + 32)
    input_bytes = _bytes([scope, lattice, entries, bundles, completion_request_ref, indices])
    max_sound_bytes = max((_bytes(s) for s in scope["sound_facts"]), default=0)
    # Facets retain mostly subsets of existing bodies. Added segments contain
    # bounded references, and presentations contain complete source closures.
    catalog_bytes = input_bytes * 8 + (atom_bound + cell_bound) * 2048 \
        + attribution_bound * 256 + presentation_bound * (max_sound_bytes + 2048) \
        + vectors * 32 + refinement * 512 + 16384
    reasons = []
    for name, actual, cap in (("entries", len(entries), limits.max_entries),
            ("refinement_atoms", refinement, limits.max_refinement_atoms),
            ("vector_cells", vectors, limits.max_vector_cells), ("pairs", pairs, limits.max_pairs),
            ("work", work, limits.max_work), ("catalog_bytes", catalog_bytes, limits.max_catalog_bytes),
            ("block_pairs", max_block_pairs, limits.max_block_pairs)):
        if actual > cap:
            reasons.append("whole_" + name + "_exceeds_limit_no_prefix")
    return PreflightPlan(len(entries), pairs, block_count, refinement, vectors, work,
        input_bytes, catalog_bytes, block_size, tuple(reasons))


def _row_vector(rows, points):
    """One linear original-row sweep; all atoms must have exactly one cover."""
    ordered = sorted(enumerate(rows), key=lambda p: span_bounds(p[1]["span"]))
    bounds = [(index, *span_bounds(row["span"])) for index, row in ordered]
    cursor, result = 0, []
    for a, b in zip(points, points[1:]):
        while cursor < len(bounds) and bounds[cursor][2] <= a:
            cursor += 1
        if cursor >= len(bounds) or not bounds[cursor][1] <= a < b <= bounds[cursor][2]:
            raise ValueError("exact_single_source_aligned_cover_required")
        if cursor + 1 < len(bounds) and bounds[cursor + 1][1] < b:
            raise ValueError("overlapping_source_rows_in_refinement")
        result.append(bounds[cursor][0])
    return result


def _refine(facets):
    if not facets:
        return {"sounds": [], "bass": {"points": [], "vectors": []}}
    sound_ids = sorted(facets[0]["source_segments"])
    if any(sorted(fa["source_segments"]) != sound_ids for fa in facets):
        raise ValueError("competitors_do_not_cover_same_source_sounds")
    sounds = []
    for sid in sound_ids:
        points = sorted({v for fa in facets for row in fa["source_segments"][sid] for v in span_bounds(row["span"])})
        sounds.append({"sound_ref": sid, "points": [q(v) for v in points],
            "vectors": [_row_vector(fa["source_segments"][sid], points) for fa in facets]})
    points = sorted({v for fa in facets for row in fa["bass_cells"] for v in span_bounds(row["span"])})
    bass = {"points": [q(v) for v in points],
        "vectors": [_row_vector(fa["bass_cells"], points) for fa in facets]}
    return {"sounds": sounds, "bass": bass}


@dataclass(frozen=True, slots=True)
class _State:
    catalog: object
    plan: PreflightPlan
    limits: Limits
    sound_points: tuple
    bass_points: tuple
    signature: bytes


def _signature(handle, catalog, plan, limits, sound_points, bass_points):
    body = [id(handle), id(catalog), catalog["record_sha256"],
        digest(asdict(plan)), digest(asdict(limits)), id(sound_points), id(bass_points)]
    return hmac.digest(_SECRET, json.dumps(body, separators=(",", ":")).encode(), "sha256")


def _issued(handle):
    if type(handle) is not PreparedGroup or handle not in _GROUPS:
        raise ValueError("registered_validated_saved_group_required")
    state = _GROUPS[handle]
    if (type(state) is not _State or type(state.catalog) is not MappingProxyType
            or type(state.plan) is not PreflightPlan or type(state.limits) is not Limits
            or not hmac.compare_digest(state.signature,
                _signature(handle, state.catalog, state.plan, state.limits,
                    state.sound_points, state.bass_points))):
        raise ValueError("owned_validated_saved_group_state_changed")
    return state


class PreparedGroup:
    """Immutable validated saved catalog. This is not a native session/issuer."""
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise ValueError("validated_saved_group_factory_required")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_saved_group")

    @property
    def group_ref(self):
        return _copy(_issued(self).catalog["group_ref"])

    @property
    def catalog_ref(self):
        return kernels._ref(_issued(self).catalog)

    @property
    def preflight_plan(self):
        return _issued(self).plan

    def export_catalog(self):
        return _copy(_issued(self).catalog)

    def iter_blocks(self):
        state = _issued(self)
        for task in plan_blocks(state.plan.entry_count, state.plan.block_size):
            yield replace(task, group_sha256=state.catalog["group_ref"]["record_sha256"],
                refinement_sha256=state.catalog["refinement_sha256"],
                entry_inventory_sha256=state.catalog["entry_inventory_sha256"])


def prepare_saved_group(scope, lattice, entries, *, bundles, completion_request_ref,
        selector_indices=None, block_size=64, limits=None):
    limits = Limits() if limits is None else limits
    plan = preflight_saved_group(scope, lattice, entries, bundles=bundles,
        completion_request_ref=completion_request_ref, selector_indices=selector_indices,
        block_size=block_size, limits=limits)
    if plan.reasons:
        raise WholeGroupHold(plan)
    _no_float([scope, lattice, entries, bundles])
    before = digest([scope, lattice, entries, bundles])
    kernels._check(scope, "fmes_")
    kernels._check(lattice, native.PREFIX)
    if lattice["scope_ref"] != kernels._ref(scope) or lattice["binding"] != scope["binding"]:
        raise ValueError("saved_scope_lattice_binding_mismatch")
    for key, bundle in bundles.items():
        kernels._check(bundle, native.BUNDLE_PREFIX)
        if key != bundle["record_id"] or bundle["scope_ref"] != kernels._ref(scope) or bundle["binding"] != scope["binding"]:
            raise ValueError("foreign_saved_completion")
    origins = legacy._lookup([o for cat in lattice["catalog_inventory"] for o in cat["origins"]], "origin")
    keys = legacy._lookup(lattice["keys"], "key")
    sounds = {s["sound_ref"]: s for s in scope["sound_facts"]}
    if len(sounds) != len(scope["sound_facts"]):
        raise ValueError("duplicate_source_sound_reference")
    facets, cache, seen = [], {}, set()
    group_key = None
    for entry in entries:
        path = entry["native_path"]
        current_key = (digest(path["key_ref"]), digest(path["bundle_ref"]))
        if group_key is not None and current_key != group_key:
            raise ValueError("one_exact_key_bundle_completion_group_required")
        group_key = current_key
        identity = digest(path["logical_tuple"])
        if identity in seen:
            raise ValueError("duplicate_saved_complete_hypothesis")
        seen.add(identity)
        chosen = legacy._validate_entry(entry, scope, lattice, origins, keys, bundles, sounds, cache)
        facets.append(legacy._facet(entry, scope, chosen, sounds))
    indices = list(range(len(entries))) if selector_indices is None else deepcopy(selector_indices)
    group = kernels._seal({"version": VERSION, "source_authority": AUTHORITY,
        "scope_ref": kernels._ref(scope), "lattice_ref": kernels._ref(lattice),
        "binding": deepcopy(scope["binding"]), "analysis_span": deepcopy(scope["analysis_span"]),
        "key_ref": deepcopy(entries[0]["native_path"]["key_ref"]) if entries else None,
        "bundle_ref": deepcopy(entries[0]["native_path"]["bundle_ref"]) if entries else None,
        "completion_request_ref": deepcopy(completion_request_ref),
        "original_selector_indices": indices,
        "entry_refs": [{"native_path_ref": kernels._ref(e["native_path"]),
            "role_path_ref": kernels._ref(e["role_path"]),
            "comparison_ref": deepcopy(e["comparison_ref"]),
            "explanation_ref": deepcopy(e["explanation_ref"])} for e in entries]}, GROUP_PREFIX)
    refinement = _refine(facets)
    actual_atoms = sum(max(0, len(s["points"]) - 1) for s in refinement["sounds"]) \
        + max(0, len(refinement["bass"]["points"]) - 1)
    if actual_atoms > plan.refinement_atom_upper_bound:
        raise ValueError("refinement_exceeded_declared_upper_bound")
    catalog = kernels._seal({"version": VERSION, "codec": "exact-original-row-refinement-v1",
        "source_authority": AUTHORITY, "group": group, "group_ref": kernels._ref(group),
        "source_scope": deepcopy(scope), "lattice": deepcopy(lattice), "bundles": deepcopy(bundles),
        "entries": deepcopy(entries), "facets": facets, "source_sounds": list(sounds.values()),
        "refinement": refinement, "refinement_sha256": digest(refinement),
        "entry_inventory_sha256": digest(group["entry_refs"]),
        "preflight_plan": plan.record(), "actual_refinement_atoms": actual_atoms,
        "selected": None, "rank": None, "confidence": None, "flags": legacy._flags()}, CATALOG_PREFIX)
    actual_bytes = _bytes(catalog)
    if actual_bytes > plan.catalog_byte_upper_bound:
        raise ValueError("catalog_exceeded_declared_byte_upper_bound")
    if actual_bytes > limits.max_catalog_bytes:
        raise WholeGroupHold(PreflightPlan(**{**asdict(plan),
            "reasons": ("whole_actual_catalog_bytes_exceeds_limit_no_prefix",)}))
    if before != digest([scope, lattice, entries, bundles]):
        raise ValueError("saved_group_inputs_modified_during_preparation")
    handle = object.__new__(PreparedGroup)
    frozen = _freeze(catalog)
    # Fraction exposes private mutable slots. Owned caches therefore contain
    # only immutable builtin integer pairs, never Fraction objects. Arithmetic
    # creates local Fractions and its per-atom visits are included in preflight.
    points = tuple(tuple((p["numerator"], p["denominator"]) for p in sound["points"])
        for sound in catalog["refinement"]["sounds"])
    bass_points = tuple((p["numerator"], p["denominator"])
        for p in catalog["refinement"]["bass"]["points"])
    _GROUPS[handle] = _State(frozen, plan, limits, points, bass_points,
        _signature(handle, frozen, plan, limits, points, bass_points))
    return handle


def _runs(points, left, right):
    """Coalesce ONLY identical original row-index pairs, never category equality."""
    if len(left) != len(points) - 1 or len(right) != len(left):
        raise ValueError("refinement_vector_length_mismatch")
    start = 0
    for end in range(1, len(left) + 1):
        if end == len(left) or (left[end], right[end]) != (left[start], right[start]):
            yield start, end, left[start], right[start]
            start = end


def _compact_pair(prepared, i, j):
    state = _issued(prepared)
    catalog = state.catalog
    left, right = catalog["facets"][i], catalog["facets"][j]
    transfers, changes = Counter(), []
    for sindex, sound in enumerate(catalog["refinement"]["sounds"]):
        points = tuple(Fraction(n, d) for n, d in state.sound_points[sindex])
        sid = sound["sound_ref"]
        for a, b, li, ri in _runs(points, sound["vectors"][i], sound["vectors"][j]):
            lrow, rrow = left["source_segments"][sid][li], right["source_segments"][sid][ri]
            transfers[(lrow["category"], rrow["category"])] += points[b] - points[a]
            if lrow["category"] != rrow["category"]:
                changes.append([sindex, a, b, li, ri])
    raw = f(left["account"]["raw_total_note_time_quarters"])
    if raw != f(right["account"]["raw_total_note_time_quarters"]) or sum(transfers.values(), Fraction()) != raw:
        raise ValueError("pairwise_raw_note_time_not_conserved")
    bass = catalog["refinement"]["bass"]
    bass_runs = []
    for a, b, li, ri in _runs(bass["points"], bass["vectors"][i], bass["vectors"][j]):
        lcell, rcell = left["bass_cells"][li], right["bass_cells"][ri]
        if lcell["sound_refs"] != rcell["sound_refs"] or lcell["bass_refs"] != rcell["bass_refs"]:
            raise ValueError("aligned_raw_bass_observations_changed_between_candidates")
        bass_runs.append([a, b, li, ri])
    lcuts = {f(s["start"]): v for s, v in zip(left["partition"][1:], left["transition_assumptions"])}
    rcuts = {f(s["start"]): v for s, v in zip(right["partition"][1:], right["transition_assumptions"])}
    ls = [(s["root"], s["members"]) for s in left["slot_presentations"]]
    rs = [(s["root"], s["members"]) for s in right["slot_presentations"]]
    same_partition = left["partition"] == right["partition"]
    same_vector = left["transition_assumptions"] == right["transition_assumptions"]
    kind = "partition" if not same_partition else "candidate_only" if same_vector else \
        "transition_only" if ls == rs else "candidate_and_transition"
    lc = left["account"]["conditional_explanation_note_time_quarters"]
    rc = right["account"]["conditional_explanation_note_time_quarters"]
    return kernels._seal({"version": VERSION, "codec": "exact-original-row-refinement-v1",
        "catalog_ref": kernels._ref(catalog), "group_ref": _copy(catalog["group_ref"]),
        "refinement_sha256": catalog["refinement_sha256"], "entry_indices": [i, j],
        "original_selector_indices": [catalog["group"]["original_selector_indices"][i],
            catalog["group"]["original_selector_indices"][j]],
        "comparison_kind": kind, "same_partition": same_partition,
        "alias_control": same_partition and same_vector and ls == rs,
        "shared_cut_assumptions": [{"time": q(t), "left": _copy(lcuts[t]), "right": _copy(rcuts[t]),
            "same_assumption": lcuts[t] == rcuts[t]} for t in sorted(lcuts.keys() & rcuts.keys())],
        "left_only_cuts": [q(t) for t in sorted(lcuts.keys() - rcuts.keys())],
        "right_only_cuts": [q(t) for t in sorted(rcuts.keys() - lcuts.keys())],
        "raw_total_note_time_quarters": q(raw), "raw_time_conserved": True,
        "note_time_delta_right_minus_left": {c: q(f(right["account"]["note_time_quarters"][c])
            - f(left["account"]["note_time_quarters"][c])) for c in CATEGORIES},
        "conditional_credit_delta_right_minus_left": None if lc is None or rc is None else q(f(rc) - f(lc)),
        "category_transfer_note_time": [{"left": a, "right": b, "duration_quarters": q(v)}
            for (a, b), v in sorted(transfers.items())],
        "changed_source_segment_pointers": changes, "aligned_bass_cell_pointers": bass_runs,
        "logical_atom_visits": sum(len(s["vectors"][i]) for s in catalog["refinement"]["sounds"])
            + len(bass["vectors"][i]),
        "status": "computed_saved_pair_contrast_not_selected", "musical_outcome": None,
        "selected": None, "rank": None, "confidence": None}, PAIR_PREFIX)


def compare_block(prepared, task):
    if type(prepared) is not PreparedGroup or type(task) is not BlockTask:
        raise ValueError("validated_group_and_exact_block_task_required")
    state = _issued(prepared)
    n, size = state.plan.entry_count, state.plan.block_size
    ranges = (task.row_start, task.row_end, task.column_start, task.column_end, task.expected_pairs)
    if any(type(v) is not int for v in ranges):
        raise ValueError("foreign_or_modified_block_task")
    row_size = task.row_end - task.row_start
    expected = row_size * (row_size - 1) // 2 if task.row_start == task.column_start \
        else row_size * (task.column_end - task.column_start)
    if (not 0 <= task.row_start <= task.column_start < n
            or task.row_start % size or task.column_start % size
            or task.row_end != min(task.row_start + size, n)
            or task.column_end != min(task.column_start + size, n)
            or task.expected_pairs != expected or expected <= 0
            or task.group_sha256 != state.catalog["group_ref"]["record_sha256"]
            or task.refinement_sha256 != state.catalog["refinement_sha256"]
            or task.entry_inventory_sha256 != state.catalog["entry_inventory_sha256"]):
        raise ValueError("foreign_or_modified_block_task")
    pairs = []
    reasons = []
    buffered_bytes = 0
    for i, j in task.pair_indices():
        pair = _compact_pair(prepared, i, j)
        pair_bytes = _bytes(pair)
        if pair_bytes > state.limits.max_pair_record_bytes:
            reasons.append("whole_block_pair_bytes_exceeds_limit_no_prefix")
            break
        # At most one bounded pair beyond the admitted block byte buffer is
        # constructed. Never retain max_block_pairs * max_pair_bytes blindly.
        if buffered_bytes + pair_bytes > state.limits.max_block_record_bytes:
            reasons.append("whole_block_buffer_bytes_exceeds_limit_no_prefix")
            break
        pairs.append(pair)
        buffered_bytes += pair_bytes
    if reasons:
        pairs = []
    body = {"version": VERSION, "catalog_ref": prepared.catalog_ref,
        "group_ref": prepared.group_ref, "refinement_sha256": state.catalog["refinement_sha256"],
        "entry_inventory_sha256": state.catalog["entry_inventory_sha256"],
        "task": asdict(task), "planned_pairs": task.expected_pairs, "computed_pairs": len(pairs),
        "withheld_pairs": task.expected_pairs - len(pairs), "pairs": pairs, "reasons": reasons,
        "status": "whole_saved_block_hold" if reasons else "computed_saved_block_not_selected",
        "whole_group_complete": False, "musical_outcome": None,
        "selected": None, "rank": None, "confidence": None, "flags": legacy._flags()}
    if pairs and _bytes(body) + 256 > state.limits.max_block_record_bytes:
        body.update(pairs=[], computed_pairs=0, withheld_pairs=task.expected_pairs,
            reasons=["whole_block_encoded_bytes_exceeds_limit_no_prefix"], status="whole_saved_block_hold")
    return kernels._seal(body, BLOCK_PREFIX)


def materialize_pair(prepared, pair):
    """Restore the exact legacy pair shape from immutable original row pointers.

    Only a PreparedGroup accepted; an exported summary/catalog is not a validated
    handle. Re-admission of catalogs belongs to a separately authenticated reader.
    """
    if type(prepared) is not PreparedGroup:
        raise ValueError("validated_saved_group_required")
    state = _issued(prepared)
    _no_float(pair)
    kernels._check(pair, PAIR_PREFIX)
    if pair["catalog_ref"] != prepared.catalog_ref or pair["group_ref"] != prepared.group_ref:
        raise ValueError("foreign_saved_pair_catalog")
    i, j = pair["entry_indices"]
    if type(i) is not int or type(j) is not int or not 0 <= i < j < state.plan.entry_count:
        raise ValueError("ordered_group_pair_indices_required")
    # Saved pair seals alone are not sufficient: pointers, deltas and summaries
    # must match the deterministic admitted catalog, not a resealed fabrication.
    if pair != _compact_pair(prepared, i, j):
        raise ValueError("saved_pair_disagrees_with_validated_catalog")
    catalog = state.catalog
    left, right = catalog["facets"][i], catalog["facets"][j]
    sounds = {s["sound_ref"]: s for s in catalog["source_sounds"]}
    differences = []
    for si, a, b, li, ri in pair["changed_source_segment_pointers"]:
        sound = catalog["refinement"]["sounds"][si]
        sid, points = sound["sound_ref"], sound["points"]
        differences.append({"sound_ref": sid, "source_note_refs": _copy(sounds[sid]["source_note_refs"]),
            "pitch": _copy(sounds[sid]["pitch"]), "full_sound_span": _copy(sounds[sid]["span"]),
            "span": {"start": _copy(points[a]), "end": _copy(points[b])},
            "left": _copy(left["source_segments"][sid][li]), "right": _copy(right["source_segments"][sid][ri])})
    bass = []
    points = catalog["refinement"]["bass"]["points"]
    for a, b, li, ri in pair["aligned_bass_cell_pointers"]:
        lcell, rcell = left["bass_cells"][li], right["bass_cells"][ri]
        bass.append({"span": {"start": _copy(points[a]), "end": _copy(points[b])},
            "bass_refs": _copy(lcell["bass_refs"]),
            "left": {k: _copy(lcell[k]) for k in _BASS_FIELDS},
            "right": {k: _copy(rcell[k]) for k in _BASS_FIELDS},
            "bass_is_not_certified_structural_bass": True})
    fields = ("comparison_kind", "same_partition", "alias_control", "shared_cut_assumptions",
        "left_only_cuts", "right_only_cuts", "raw_total_note_time_quarters", "raw_time_conserved",
        "note_time_delta_right_minus_left", "category_transfer_note_time")
    return {"left_path_ref": _copy(left["native_path_ref"]), "right_path_ref": _copy(right["native_path_ref"]),
        "left_role_path_ref": _copy(left["role_path_ref"]), "right_role_path_ref": _copy(right["role_path_ref"]),
        "key_ref": _copy(left["key_ref"]), "bundle_ref": _copy(left["bundle_ref"]),
        **{k: deepcopy(pair[k]) for k in fields}, "changed_source_segments": differences,
        "aligned_bass_cells": bass, "selected": None, "rank": None, "confidence": None,
        "interpretation": "conditional_evidence_contrast_not_chord_selection"}
