"""Pre-comparison transfer bounds from an owned group's rows and endpoints.

This prototype changes no candidate, role, pair JSON, or historical writer.
It replaces ONLY the transfer-array term in the frozen stream schema bound.
Descriptors are not authority: retain the exact issued proof and group handle.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import gcd
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import proof_shared_progression_streaming as stream
from . import proof_shared_source_progression_contrast as core

VERSION = "proof-shared-transfer-bounds-0.1.0"


@dataclass(frozen=True, slots=True)
class BoundLimits:
    max_work: int = 1000000000
    max_integer_bits: int = 8192
    max_scratch_bytes: int = 131072
    max_retained_proof_bytes: int = 8388608

    def __post_init__(self):
        for name, value in asdict(self).items():
            stream._integer(value, name, positive=True)


DEFAULT_LIMITS = BoundLimits()


class TransferBoundHold(ValueError):
    def __init__(self, reason, work, **details):
        self.diagnostics = {"reason": reason, "inspection_work": work,
            "raw_block_byte_upper_bound": None, "pair_outputs_computed": 0, **details}
        super().__init__(reason)


class _Budget:
    __slots__ = ("limits", "work", "peak_scratch")

    def __init__(self, limits):
        self.limits, self.work, self.peak_scratch = limits, 0, 0

    @property
    def maximum(self):
        return self.limits.max_work

    def charge(self, work):
        stream._integer(work, "proof_work")
        attempted = self.work + work
        if attempted > self.limits.max_work:
            raise TransferBoundHold("whole_transfer_proof_work_hold_no_prefix", self.work,
                attempted_work_lower_bound=attempted, max_work=self.limits.max_work)
        self.work = attempted

    def bits(self, value):
        if type(value) is not int:
            raise ValueError("exact_transfer_proof_integer_required")
        bits = max(1, value.bit_length())
        if bits > self.limits.max_integer_bits:
            raise TransferBoundHold("whole_transfer_proof_integer_bits_hold", self.work,
                bits_lower_bound=bits, max_integer_bits=self.limits.max_integer_bits)
        self.charge(1)
        return bits

    def reserve(self, bits, work):
        # A conservative arithmetic scratch proxy, not an RSS guarantee.
        if bits > self.limits.max_integer_bits:
            raise TransferBoundHold("whole_transfer_proof_integer_bits_hold", self.work,
                bits_lower_bound=bits, max_integer_bits=self.limits.max_integer_bits)
        scratch = 256 + 32 * ((bits + 7) // 8)
        if scratch > self.limits.max_scratch_bytes:
            raise TransferBoundHold("whole_transfer_proof_scratch_hold", self.work,
                scratch_byte_upper_bound=scratch, max_scratch_bytes=self.limits.max_scratch_bytes)
        self.charge(work)
        self.peak_scratch = max(self.peak_scratch, scratch)

    def common_divisor(self, a, b):
        bits = self.bits(a) + self.bits(b) + 1
        # Euclidean rounds/divisions: explicitly charged BEFORE the gcd call.
        self.reserve(max(self.bits(a), self.bits(b)), 8 * bits ** 3)
        return gcd(a, b)

    def multiply(self, a, b):
        bits = self.bits(a) + self.bits(b)
        self.reserve(bits, 8 * (bits + 1) ** 2)
        return a * b

    def divide(self, a, b):
        bits = max(self.bits(a), self.bits(b))
        self.reserve(bits, 8 * (bits + 1) ** 2)
        return a // b

    def add(self, a, b):
        bits = max(self.bits(a), self.bits(b)) + 1
        self.reserve(bits, 8 * (bits + 1))
        return a + b

    def subtract(self, a, b):
        bits = max(self.bits(a), self.bits(b)) + 1
        self.reserve(bits, 8 * (bits + 1))
        return a - b


def _point(point, budget):
    if (type(point) is not MappingProxyType or set(point) != {"numerator", "denominator"}
            or type(point["numerator"]) is not int or type(point["denominator"]) is not int
            or point["denominator"] <= 0):
        raise ValueError("owned_exact_transfer_endpoint_required")
    budget.charge(4)
    budget.bits(point["numerator"])
    budget.bits(point["denominator"])
    return point["numerator"], point["denominator"]


def _decimal_width(value, budget):
    # Pre-charge a decimal-width upper bound before allocating the text.
    width = max(1, budget.bits(value) * 30103 // 100000 + 2) + int(value < 0)
    budget.charge(width)
    actual = stream._digits(value)
    if actual > width:
        raise ValueError("transfer_proof_decimal_width_contract_mismatch")
    return actual


def _endpoint_lattice(refinement, budget):
    """LCM and whole sound-span numerator; no vectors or pair atom runs.

    Every transfer is a sum of nonnegative disjoint intervals of these sounds.
    Its denominator divides D and its numerator is <= total_span_in_D_units.
    Gaps, if any, only make the span bound more conservative.
    """
    sound = point = previous = first = None
    try:
        denominator, atoms, endpoints = 1, 0, 0
        budget.charge(8 + len(refinement["sounds"]) * 4)
        for sound in refinement["sounds"]:
            atoms += max(0, len(sound["points"]) - 1)
            budget.charge(4)
            for point in sound["points"]:
                _, d = _point(point, budget)
                common = budget.common_divisor(denominator, d)
                denominator = budget.multiply(budget.divide(denominator, common), d)
                endpoints += 1
        magnitude = 0
        for sound in refinement["sounds"]:
            previous = first = None
            for point in sound["points"]:
                n, d = _point(point, budget)
                scaled = budget.multiply(n, budget.divide(denominator, d))
                budget.charge(2)
                if previous is not None and scaled < previous:
                    raise ValueError("monotone_transfer_endpoints_required")
                if first is None:
                    first = scaled
                previous = scaled
            if first is not None:
                magnitude = budget.add(magnitude, budget.subtract(previous, first))
        # Decimal conversion is also bounded/charged, not assumed constant-time.
        nd, dd = _decimal_width(magnitude, budget), _decimal_width(denominator, budget)
        return {"denominator_lcm": denominator, "total_span_numerator_bound": magnitude,
            "sound_atoms": atoms, "endpoint_count": endpoints,
            "transfer_rational_bytes": stream._q_bound(nd, dd),
            "transfer_numerator_digits": nd, "transfer_denominator_digits": dd}
    finally:
        refinement = sound = point = previous = first = None


def _entry_support(view, budget):
    rows = row = category = None
    support = set()
    try:
        budget.charge(256 + len(view["source_rows"]) * 4)
        row_count = 0
        for rows in view["source_rows"].values():
            budget.charge(4 * len(rows))
            for row in rows:
                category = row["category"]
                if type(category) is not str or category not in core.CATEGORIES:
                    raise ValueError("closed_owned_transfer_category_required")
                support.add(category)
                row_count += 1
        # Closed vocabulary bounds this set to six elements, regardless of rows.
        budget.charge(sum(2 + 6 * len(c) for c in support))
        width = max((stream._string_width(c) for c in support), default=0)
        return tuple(sorted(support)), width, row_count
    finally:
        support.clear()
        view = rows = row = category = None


@dataclass(frozen=True, slots=True)
class _State:
    prepared: core.CompactPreparedGroup
    catalog: object
    binding: tuple
    supports: tuple
    rational: tuple
    limits: BoundLimits
    preparation_work: int
    peak_scratch: int
    retained_byte_bound: int


_PROOFS = WeakKeyDictionary()


class TransferProof:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise ValueError("owned_transfer_proof_factory_required_not_JSON")

    def __setattr__(self, name, value):
        raise AttributeError("immutable_owned_transfer_proof")


def _binding(state):
    return (id(state.source), id(state.catalog), state.catalog["record_sha256"],
        state.catalog["refinement_sha256"], state.catalog["entry_inventory_sha256"],
        state.plan.entry_count, state.plan.planned_pairs, state.plan.planned_blocks)


def _issued(proof):
    state = owned = None
    try:
        if type(proof) is not TransferProof or proof not in _PROOFS:
            raise ValueError("owned_transfer_proof_required_not_descriptor")
        state = _PROOFS[proof]
        owned = core._issued(state.prepared)
        if owned.catalog is not state.catalog or _binding(owned) != state.binding:
            raise ValueError("owned_transfer_proof_binding_changed")
        return state
    finally:
        proof = state = owned = None


def prepare_transfer_bounds(prepared, *, limits=None):
    """Issue a one-group proof, without exporting/decoding or selecting roles."""
    state = budget = handle = summary = None
    supports = []
    try:
        limits = DEFAULT_LIMITS if limits is None else limits
        if type(limits) is not BoundLimits or any(getattr(limits, name) > value
                for name, value in asdict(DEFAULT_LIMITS).items()):
            raise ValueError("transfer_proof_limits_may_only_tighten_defaults")
        state = core._issued(prepared)
        limits = BoundLimits(min(limits.max_work, state.limits.max_work),
            limits.max_integer_bits, limits.max_scratch_bytes, limits.max_retained_proof_bytes)
        budget = _Budget(limits)
        # Retained state has only closed sets, integers, and an existing handle.
        # This is a logical allocation bound, not measured process memory.
        retained = 4096 + state.plan.entry_count * (256 + len(core.CATEGORIES) * 128)
        if retained > limits.max_retained_proof_bytes:
            raise TransferBoundHold("whole_transfer_proof_retained_bytes_hold", 0,
                retained_byte_upper_bound=retained)
        budget.charge(128 + state.plan.entry_count * 16)
        summary = _endpoint_lattice(state.catalog["refinement"], budget)
        for view in state.catalog["pair_index"]:
            supports.append(_entry_support(view, budget))
        if len(supports) != state.plan.entry_count:
            raise ValueError("owned_transfer_proof_whole_entry_inventory_required")
        handle = object.__new__(TransferProof)
        _PROOFS[handle] = _State(prepared, state.catalog, _binding(state), tuple(supports),
            tuple(sorted(summary.items())), limits, budget.work, budget.peak_scratch, retained)
        return handle
    finally:
        supports.clear()
        prepared = state = budget = handle = summary = view = None


def proof_info(proof):
    state = None
    try:
        state = _issued(proof)
        return {"version": VERSION, "source_ref": state.prepared.source_ref,
            "group_ref": state.prepared.group_ref, "catalog_ref": state.prepared.catalog_ref,
            "refinement_sha256": state.binding[3], "entry_inventory_sha256": state.binding[4],
            "entry_count": len(state.supports), "planned_pairs": state.binding[6],
            "planned_blocks": state.binding[7], "rational_proof": dict(state.rational),
            "category_support_counts": [len(item[0]) for item in state.supports],
            "inspected_source_rows": sum(item[2] for item in state.supports),
            "preparation_work_once": state.preparation_work,
            "arithmetic_scratch_proxy_upper_bound": state.peak_scratch,
            "retained_proof_byte_upper_bound": state.retained_byte_bound,
            "limits": asdict(state.limits), "descriptor_is_not_authority": True,
            "pair_outputs_computed": 0, "music_accuracy_or_selection_claimed": False}
    finally:
        proof = state = None


def _transfer_component(left, right, sound_atoms, rational_bytes):
    count = min(len(left[0]) * len(right[0]), sound_atoms)
    item = stream._object_bound({"left": left[1], "right": right[1],
        "duration_quarters": rational_bytes})
    return stream._array_bound(count, item), count


def task_stream_bound(proof, task, *, max_work=stream.DEFAULT_MAX_WORK,
                      max_block_bytes=stream.DEFAULT_MAX_BLOCK_BYTES):
    """Substitute a proven upper bound for ONLY the old transfer-array term.

    No pair output, outcome sample, compression, vector runs or role selection.
    The frozen base schema bounds every other field, including nulls and IDs.
    This is not yet wired into the historical writer/coordinator.
    """
    state = budget = baseline = rational = None
    try:
        stream._integer(max_work, "max_work")
        stream._integer(max_block_bytes, "max_block_bytes")
        state = _issued(proof)
        budget = _Budget(BoundLimits(min(max_work, state.limits.max_work),
            state.limits.max_integer_bits, state.limits.max_scratch_bytes,
            state.limits.max_retained_proof_bytes)) if max_work else None
        if budget is None:
            raise TransferBoundHold("whole_transfer_proof_work_hold_no_prefix", 0)
        # Bind before any new pair count/allocation. Base validates again.
        stream._task_binding(state.prepared, core._issued(state.prepared), task)
        budget.charge(128 + task.expected_pairs * 512)
        baseline = stream.task_stream_bound(state.prepared, task,
            max_work=budget.limits.max_work - budget.work, max_block_bytes=max_block_bytes)
        if baseline["raw_block_byte_upper_bound"] is None:
            return {**baseline, "version": VERSION, "bound_strategy": "owned_category_support_exact_lcm",
                "preparation_work_once": state.preparation_work,
                "inspection_work": budget.work + baseline["inspection_work"]}
        budget.charge(baseline["inspection_work"])
        rational = dict(state.rational)
        atoms = rational["sound_atoms"]
        if atoms != baseline["sound_pointer_count_upper_bound_per_pair"]:
            raise ValueError("owned_transfer_proof_sound_atom_inventory_mismatch")
        category_width = max(stream._string_width(c) for c in core.CATEGORIES)
        old_component = stream._array_bound(min(len(core.CATEGORIES) ** 2, atoms),
            stream._object_bound({"left": category_width, "right": category_width,
                "duration_quarters": baseline["transfer_rational_byte_upper_bound"]}))
        savings = 0
        minimum_saving, max_count, pairs = None, 0, 0
        for i, j in task.pair_indices():
            new_component, count = _transfer_component(state.supports[i], state.supports[j],
                atoms, rational["transfer_rational_bytes"])
            # Both terms are proven bounds; their minimum is also a bound.
            saved = old_component - min(old_component, new_component)
            savings += saved
            minimum_saving = saved if minimum_saving is None else min(minimum_saving, saved)
            max_count = max(max_count, count)
            pairs += 1
        if pairs != task.expected_pairs:
            raise ValueError("whole_transfer_task_pair_denominator_mismatch")
        bound = baseline["raw_block_byte_upper_bound"] - savings
        pair_bound = baseline["maximum_pair_byte_upper_bound"] - minimum_saving
        owned = core._issued(state.prepared)
        reasons = []
        if pair_bound > owned.limits.max_pair_record_bytes:
            reasons.append("whole_pair_schema_byte_bound_hold_no_prefix")
        if bound > min(max_block_bytes, owned.limits.max_block_record_bytes):
            reasons.append("whole_block_schema_byte_bound_hold_no_prefix")
        return {**baseline, "version": VERSION, "base_version": baseline["version"],
            "bound_strategy": "owned_category_support_exact_lcm",
            "raw_block_byte_upper_bound": bound, "maximum_pair_byte_upper_bound": pair_bound,
            "legacy_raw_block_byte_upper_bound": baseline["raw_block_byte_upper_bound"],
            "legacy_maximum_pair_byte_upper_bound": baseline["maximum_pair_byte_upper_bound"],
            "transfer_array_byte_savings_bound": savings,
            "maximum_possible_transfer_categories_per_pair": max_count,
            "transfer_rational_byte_upper_bound": rational["transfer_rational_bytes"],
            "legacy_transfer_rational_byte_upper_bound": baseline["transfer_rational_byte_upper_bound"],
            "preparation_work_once": state.preparation_work, "inspection_work": budget.work,
            "planning_work_upper_bound": budget.work, "reasons": reasons,
            "status": "whole_block_stream_bound_hold" if reasons else "admissible_whole_block_stream_bound",
            "historical_writer_or_coordinator_modified": False}
    except TransferBoundHold as error:
        return {"version": VERSION, "status": "whole_block_stream_bound_hold",
            "bound_strategy": "owned_category_support_exact_lcm",
            "expected_pairs": task.expected_pairs if type(task) is core.BlockTask else None,
            "raw_block_byte_upper_bound": None, "maximum_pair_byte_upper_bound": None,
            "planning_work_upper_bound": None, "inspection_work": error.diagnostics["inspection_work"],
            "reasons": [str(error)], "descriptor_is_not_authority": True,
            "pair_outputs_computed": 0, "full_archive_or_music_accuracy_claimed": False}
    finally:
        proof = task = state = budget = baseline = rational = owned = None
