"""Owned source/catalog streams and schema-derived compact block bounds.

Descriptors are advisory numbers, never authority or a restoration API. The
writer must retain the exact issued handles. No whole source/catalog thaw, DAG
export, pair computation or compression sample is used by this module.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from types import MappingProxyType

from . import lossless_json_dag_v2 as dag
from . import proof_shared_source_progression_contrast as core
from . import shared_source_progression_contrast as shared

VERSION = "proof-shared-progression-streaming-0.1.0"
DEFAULT_CHUNK_BYTES = 1048576
DEFAULT_MAX_WORK = 1000000000
DEFAULT_MAX_BLOCK_BYTES = 67108864
MAX_DEPTH = 256


class StreamHold(ValueError):
    def __init__(self, reason, diagnostics):
        self.diagnostics = dict(diagnostics)
        super().__init__(reason)


def _integer(value, name, positive=False):
    if type(value) is not int or value < int(positive):
        raise ValueError("exact_nonnegative_stream_integer_required:" + name)


def _work_gate(work, maximum):
    if work > maximum:
        raise StreamHold("whole_stream_planning_work_hold_no_prefix",
            {"inspection_work_lower_bound": work, "max_work": maximum})


class _Measure:
    __slots__ = ("work", "visits", "maximum", "__weakref__")

    def __init__(self, maximum):
        self.work = self.visits = 0
        self.maximum = maximum

    def charge(self, count):
        _work_gate(self.work + count, self.maximum)
        self.work += count


def _digits(value, meter=None):
    if type(value) is not int:
        raise ValueError("exact_plain_stream_integer_required")
    lower = max(1, (value.bit_length() - 1) * 30102 // 100000 + 1) + int(value < 0)
    if meter is not None:
        _work_gate(meter.work + lower, meter.maximum)
    text = None
    try:
        text = str(value)
        width = len(text)
        if meter is not None:
            meter.charge(width)
        return width
    finally:
        text = None


def _string_width(value, meter=None):
    try:
        if type(value) is not str:
            raise ValueError("exact_plain_stream_string_required")
        if meter is not None:
            _work_gate(meter.work + len(value) + 2, meter.maximum)
            meter.charge(2)
        width = 2
        for character in value:
            if character in ('"', "\\", "\b", "\f", "\n", "\r", "\t"):
                addition = 2
            elif ord(character) < 32:
                addition = 6
            else:
                try:
                    addition = len(character.encode("utf-8"))
                except UnicodeError as exc:
                    raise ValueError("valid_UTF8_stream_string_required") from exc
            width += addition
            if meter is not None:
                meter.charge(addition)
        return width
    finally:
        value = None


def _measure_owned(value, meter, depth=1):
    keys = None
    try:
        if depth > MAX_DEPTH:
            raise StreamHold("whole_stream_depth_hold", {"depth_lower_bound": depth})
        meter.visits += 1
        meter.charge(1)
        cls = type(value)
        if cls is MappingProxyType or cls is dict:
            if any(type(key) is not str for key in value):
                raise ValueError("exact_stream_dictionary_keys_required")
            punctuation = 2 + len(value) + max(0, len(value) - 1)
            meter.charge(punctuation)
            size = punctuation
            keys = sorted(value)
            for key in keys:
                size += _measure_owned(key, meter, depth + 1)
                size += _measure_owned(value[key], meter, depth + 1)
            return size
        if cls is tuple or cls is list:
            punctuation = 2 + max(0, len(value) - 1)
            meter.charge(punctuation)
            size = punctuation
            for ordinal in range(len(value)):
                size += _measure_owned(value[ordinal], meter, depth + 1)
            return size
        if cls is str:
            return _string_width(value, meter)
        if cls is int:
            return _digits(value, meter)
        if value is None:
            meter.charge(4)
            return 4
        if cls is bool:
            width = 4 if value else 5
            meter.charge(width)
            return width
        raise ValueError("closed_exact_plain_stream_JSON_required_no_float_subclass")
    finally:
        if keys is not None:
            keys.clear()
        value = key = None


def _scalar_bytes(value):
    if type(value) not in (str, int, bool, type(None)):
        raise ValueError("closed_exact_plain_stream_scalar_required")
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (UnicodeError, ValueError, TypeError) as exc:
        raise ValueError("valid_plain_UTF8_stream_scalar_required") from exc


def _owned_fragments(value, string_characters):
    """Small scalar fragments; module-level recursive generators close cleanly."""
    keys = None
    try:
        cls = type(value)
        if cls is MappingProxyType:
            keys = sorted(value)
            yield b"{"
            for ordinal in range(len(keys)):
                key = keys[ordinal]
                if ordinal:
                    yield b","
                yield from _owned_fragments(key, string_characters)
                yield b":"
                yield from _owned_fragments(value[key], string_characters)
            yield b"}"
        elif cls is tuple:
            yield b"["
            for ordinal in range(len(value)):
                if ordinal:
                    yield b","
                yield from _owned_fragments(value[ordinal], string_characters)
            yield b"]"
        elif cls is str:
            yield b'"'
            for start in range(0, len(value), string_characters):
                # JSON string escaping is context independent between codepoints.
                piece = value[start:start + string_characters]
                yield _scalar_bytes(piece)[1:-1]
                piece = None
            yield b'"'
        else:
            yield _scalar_bytes(value)
    finally:
        if keys is not None:
            keys.clear()
        value = key = piece = None


def _catalog_fragments(catalog, payload, chunk_bytes, string_characters):
    keys = None
    raw = None
    try:
        keys = sorted((*catalog, "payload"))
        yield b"{"
        for ordinal in range(len(keys)):
            key = keys[ordinal]
            if ordinal:
                yield b","
            yield from _owned_fragments(key, string_characters)
            yield b":"
            if key == "payload":
                raw = payload.json_bytes()  # Already owned immutable cached bytes.
                for start in range(0, len(raw), chunk_bytes):
                    yield raw[start:start + chunk_bytes]
                raw = None
            else:
                yield from _owned_fragments(catalog[key], string_characters)
        yield b"}"
    finally:
        if keys is not None:
            keys.clear()
        catalog = payload = raw = key = None


def _pack_chunks(fragments, chunk_bytes):
    buffer = bytearray()
    fragment = None
    try:
        for fragment in fragments:
            start = 0
            while start < len(fragment):
                take = min(chunk_bytes - len(buffer), len(fragment) - start)
                buffer.extend(fragment[start:start + take])
                start += take
                if len(buffer) == chunk_bytes:
                    yield bytes(buffer)
                    buffer.clear()
            fragment = None
        if buffer:
            yield bytes(buffer)
    finally:
        buffer.clear()
        fragment = None
        try:
            fragments.close()
        finally:
            fragments = None


def _ref(record):
    return {"record_id": record["record_id"], "record_sha256": record["record_sha256"]}


def source_stream_info(source, *, max_work=DEFAULT_MAX_WORK):
    """Measure canonical owned source, not an exported mutable copy or raw SHA."""
    state = meter = None
    try:
        _integer(max_work, "max_work")
        state = shared._source_issued(source)
        maximum = min(max_work, state.limits.max_source_work)
        bound = state.plan.source_record_byte_upper_bound
        _work_gate(bound, maximum)  # Pre-reserve existing authenticated byte bound.
        meter = _Measure(maximum)
        size = _measure_owned(state.catalog, meter)
        if size > bound or size > state.limits.max_source_record_bytes:
            raise ValueError("owned_source_exceeded_original_stream_byte_contract")
        return {"version": VERSION, "source_ref": _ref(state.catalog),
            "canonical_bytes": size, "canonical_byte_upper_bound": bound,
            "logical_visits": meter.visits, "planning_work": meter.work,
            "serialization_work_upper_bound": 4 * size + meter.visits,
            "iteration_work_upper_bound": meter.work + 4 * size + meter.visits,
            "raw_sha256_work_upper_bound": size, "owned_source_identity": id(source),
            "descriptor_is_not_authority": True, "full_archive_or_music_accuracy_claimed": False}
    finally:
        source = state = meter = None


def catalog_stream_info(prepared, *, max_work=DEFAULT_MAX_WORK):
    state = meter = None
    try:
        _integer(max_work, "max_work")
        state = core._issued(prepared)
        maximum = min(max_work, state.limits.max_work)
        bound = state.plan.catalog_byte_upper_bound
        _work_gate(bound, maximum)
        meter = _Measure(maximum)
        metadata = _measure_owned(state.catalog, meter)
        payload_bytes = len(state.payload.json_bytes())
        # Add one canonical key, its colon and comma, and cached raw value.
        size = metadata + _string_width("payload") + 2 + payload_bytes
        meter.charge(_string_width("payload") + 4)
        meter.visits += 2
        if size != state.plan.actual_catalog_bytes or size > bound or size > state.limits.max_catalog_bytes:
            raise ValueError("owned_catalog_exact_stream_byte_contract_mismatch")
        return {"version": VERSION, "source_ref": _ref(shared._source_issued(state.source).catalog),
            "group_ref": _ref(state.catalog["group"]), "catalog_ref": _ref(state.catalog),
            "refinement_sha256": state.catalog["refinement_sha256"],
            "entry_inventory_sha256": state.catalog["entry_inventory_sha256"],
            "entry_count": state.plan.entry_count, "planned_pairs": state.plan.planned_pairs,
            "planned_blocks": state.plan.planned_blocks, "block_size": state.plan.block_size,
            "original_selector_indices": list(state.catalog["group"]["original_selector_indices"]),
            "canonical_bytes": size, "canonical_byte_upper_bound": bound, "payload_bytes": payload_bytes,
            "logical_metadata_visits": meter.visits, "planning_work": meter.work,
            "serialization_work_upper_bound": 4 * size + meter.visits,
            "iteration_work_upper_bound": meter.work + 4 * size + meter.visits,
            "raw_sha256_work_upper_bound": size, "owned_source_identity": id(state.source),
            "owned_group_identity": id(prepared), "descriptor_is_not_authority": True,
            "full_archive_or_music_accuracy_claimed": False}
    finally:
        prepared = state = meter = None


def _stream_arguments(chunk_bytes, max_work):
    _integer(chunk_bytes, "chunk_bytes", True)
    _integer(max_work, "max_work")
    if chunk_bytes > DEFAULT_CHUNK_BYTES:
        raise ValueError("stream_chunks_cannot_exceed_one_MiB")


def iter_source_json(source, *, chunk_bytes=DEFAULT_CHUNK_BYTES, max_work=DEFAULT_MAX_WORK):
    state = packed = info = None
    try:
        _stream_arguments(chunk_bytes, max_work)
        info = source_stream_info(source, max_work=max_work)
        state = shared._source_issued(source)
        _work_gate(info["iteration_work_upper_bound"], min(max_work, state.limits.max_source_work))
        packed = _pack_chunks(_owned_fragments(state.catalog, min(4096, max(1, chunk_bytes // 6))), chunk_bytes)
        yield from packed
    finally:
        try:
            if packed is not None:
                packed.close()
        finally:
            source = state = packed = info = None


def iter_catalog_json(prepared, *, chunk_bytes=DEFAULT_CHUNK_BYTES, max_work=DEFAULT_MAX_WORK):
    state = packed = info = None
    try:
        _stream_arguments(chunk_bytes, max_work)
        info = catalog_stream_info(prepared, max_work=max_work)
        state = core._issued(prepared)
        _work_gate(info["iteration_work_upper_bound"], min(max_work, state.limits.max_work))
        fragments = _catalog_fragments(state.catalog, state.payload, chunk_bytes,
            min(4096, max(1, chunk_bytes // 6)))
        packed = _pack_chunks(fragments, chunk_bytes)
        yield from packed
    finally:
        try:
            if packed is not None:
                packed.close()
        finally:
            prepared = state = packed = fragments = info = None


def _object_bound(fields):
    return 2 + max(0, len(fields) - 1) + sum(_string_width(key) + 1 + size for key, size in fields.items())


def _array_bound(count, item_size):
    return 2 + count * item_size + max(0, count - 1)


def _rational(value, meter):
    if (type(value) is not MappingProxyType or set(value) != {"numerator", "denominator"}
            or any(type(item) is not int for item in value.values()) or value["denominator"] <= 0):
        raise ValueError("owned_exact_rational_required")
    meter.charge(3)
    return (_digits(value["numerator"], meter), _digits(value["denominator"], meter))


def _q_bound(numerator_digits, denominator_digits):
    return _object_bound({"numerator": numerator_digits, "denominator": denominator_digits})


def _delta_bound(left, right):
    # |nL*dR - nR*dL| <= |nL|*dR + |nR|*dL; sign/carry included.
    numerator = max(left[0] + right[1], right[0] + left[1]) + 2
    denominator = left[1] + right[1]
    return _q_bound(numerator, denominator)


def _task_binding(prepared, state, task):
    try:
        if type(task) is not core.BlockTask:
            raise ValueError("exact_owned_compact_BlockTask_required")
        values = (task.row_start, task.row_end, task.column_start, task.column_end, task.expected_pairs)
        if any(type(value) is not int for value in values):
            raise ValueError("foreign_or_modified_compact_block_task")
        n, size = state.plan.entry_count, state.plan.block_size
        rows = task.row_end - task.row_start
        expected = rows * (rows - 1) // 2 if task.row_start == task.column_start else rows * (task.column_end - task.column_start)
        source_ref = _ref(shared._source_issued(state.source).catalog)
        group_ref = _ref(state.catalog["group"])
        if (not 0 <= task.row_start <= task.column_start < n or task.row_start % size or task.column_start % size
                or task.row_end != min(task.row_start + size, n) or task.column_end != min(task.column_start + size, n)
                or expected <= 0 or task.expected_pairs != expected
                or any(type(value) is not str for value in (task.source_sha256, task.group_sha256,
                    task.refinement_sha256, task.entry_inventory_sha256))
                or task.source_sha256 != source_ref["record_sha256"] or task.group_sha256 != group_ref["record_sha256"]
                or task.refinement_sha256 != state.catalog["refinement_sha256"]
                or task.entry_inventory_sha256 != state.catalog["entry_inventory_sha256"]):
            raise ValueError("foreign_or_modified_compact_block_task")
        return source_ref, group_ref
    finally:
        prepared = state = task = None


def _entry_summary(state, index, meter):
    try:
        view = state.catalog["pair_index"][index]
        meter.charge(32 + len(view["source_rows"]) + len(view["cuts"]) * 8)
        maximum_rows = max((len(rows) for rows in view["source_rows"].values()), default=0)
        maximum_assumption = maximum_time = 0
        for cut in view["cuts"]:
            time = _rational(cut["time"], meter)
            maximum_time = max(maximum_time, _q_bound(*time))
            stat = dag.subtree_stats(state.payload, ("facets", index, "transition_assumptions", cut["assumption_index"]))
            maximum_assumption = max(maximum_assumption, stat["expanded_bytes"])
            meter.charge(128)  # Bound tuple-path binary-search/inspection, not decode.
        account = view["account"]
        result = {"source_row_digits": _digits(max(0, maximum_rows - 1), meter),
            "bass_row_digits": _digits(max(0, len(view["bass_rows"]) - 1), meter),
            "selector_digits": _digits(state.catalog["group"]["original_selector_indices"][index], meter),
            "cut_count": len(view["cuts"]), "time_bytes": maximum_time,
            "assumption_bytes": maximum_assumption,
            "raw": _rational(account["raw_total_note_time_quarters"], meter),
            "note_time": {category: _rational(account["note_time_quarters"][category], meter) for category in core.CATEGORIES},
            "conditional": None if account["conditional_explanation_note_time_quarters"] is None else
                _rational(account["conditional_explanation_note_time_quarters"], meter)}
        return result
    finally:
        state = view = account = cut = None


def _pair_bound(atom_count, i, j, left, right, global_, refs):
    source_ref_bytes, catalog_ref_bytes, group_ref_bytes = refs
    shared_count = min(left["cut_count"], right["cut_count"])
    shared_item = _object_bound({"time": max(left["time_bytes"], right["time_bytes"]),
        "left": left["assumption_bytes"], "right": right["assumption_bytes"], "same_assumption": 5})
    change_size = 2 + 4 + global_["sound_index_digits"] + 2 * global_["point_index_digits"] + left["source_row_digits"] + right["source_row_digits"]
    bass_size = 2 + 3 + 2 * global_["bass_point_digits"] + left["bass_row_digits"] + right["bass_row_digits"]
    categories = core.CATEGORIES
    transfer_item = _object_bound({"left": max(_string_width(c) for c in categories),
        "right": max(_string_width(c) for c in categories), "duration_quarters": global_["transfer_rational_bytes"]})
    conditional = 4 if left["conditional"] is None or right["conditional"] is None else _delta_bound(left["conditional"], right["conditional"])
    fields = {"version": _string_width(core.VERSION), "codec": _string_width(core.ENCODING),
        "source_catalog_ref": source_ref_bytes, "catalog_ref": catalog_ref_bytes, "group_ref": group_ref_bytes,
        "refinement_sha256": 66, "entry_indices": 3 + len(str(i)) + len(str(j)),
        "original_selector_indices": 3 + left["selector_digits"] + right["selector_digits"],
        "comparison_kind": max(_string_width(kind) for kind in core.legacy.KINDS),
        "same_partition": 5, "alias_control": 5,
        "shared_cut_assumptions": _array_bound(shared_count, shared_item),
        "left_only_cuts": _array_bound(left["cut_count"], left["time_bytes"]),
        "right_only_cuts": _array_bound(right["cut_count"], right["time_bytes"]),
        "raw_total_note_time_quarters": _q_bound(*left["raw"]), "raw_time_conserved": 4,
        "note_time_delta_right_minus_left": _object_bound({c: _delta_bound(left["note_time"][c], right["note_time"][c]) for c in categories}),
        "conditional_credit_delta_right_minus_left": conditional,
        "category_transfer_note_time": _array_bound(min(len(categories) ** 2, global_["sound_atoms"]), transfer_item),
        "changed_source_segment_pointers": _array_bound(global_["sound_atoms"], change_size),
        "aligned_bass_cell_pointers": _array_bound(global_["bass_atoms"], bass_size),
        "logical_atom_visits": len(str(atom_count)),
        "status": _string_width("computed_saved_pair_contrast_not_selected"),
        "musical_outcome": 4, "selected": 4, "rank": 4, "confidence": 4,
        "record_id": _string_width(core.PAIR_PREFIX) + 24, "record_sha256": 66}
    return _object_bound(fields)


def _refinement_summary(refinement, meter):
    """Pure rational-width/count inspection, never pair runs or outcomes."""
    try:
        sound_count, sound_atoms, denominator_digits, numerator_digits, max_points = len(refinement["sounds"]), 0, 0, 1, 0
        meter.charge(sound_count * 8)
        for sound in refinement["sounds"]:
            points = sound["points"]
            sound_atoms += max(0, len(points) - 1)
            max_points = max(max_points, len(points))
            meter.charge(len(points) * 4)
            for point in points:
                nd, dd = _rational(point, meter)
                numerator_digits = max(numerator_digits, nd)
                if point["denominator"] != 1:
                    denominator_digits += dd
        bass_points = refinement["bass"]["points"]
        bass_atoms = max(0, len(bass_points) - 1)
        meter.charge(len(bass_points) * 4)
        # A sum of <=atoms differences has magnitude <=2*atoms*max|n|.
        # Its denominator divides the product of all sound point denominators.
        d_width = max(1, denominator_digits)
        n_width = numerator_digits + d_width + len(str(max(1, 2 * sound_atoms))) + 1
        return {"sound_atoms": sound_atoms, "bass_atoms": bass_atoms,
            "sound_index_digits": len(str(max(0, sound_count - 1))), "point_index_digits": len(str(max(0, max_points - 1))),
            "bass_point_digits": len(str(max(0, len(bass_points) - 1))),
            "transfer_rational_bytes": _q_bound(n_width, d_width),
            "transfer_denominator_decimal_digits_upper_bound": d_width,
            "transfer_numerator_decimal_digits_upper_bound": n_width}
    finally:
        refinement = sound = points = point = bass_points = None


def task_stream_bound(prepared, task, *, max_work=DEFAULT_MAX_WORK, max_block_bytes=DEFAULT_MAX_BLOCK_BYTES):
    """Whole compact BlockTask byte bound BEFORE any outcome/atom pair work.

    Inspection is O(endpoints + affected entry summaries + expected pairs), not
    O(pairs*atoms). Denominator products are bounded by decimal widths, without
    computing enormous products, transfers, runs, assumptions or pair outputs.
    """
    state = meter = None
    summaries, global_ = {}, {}
    try:
        _integer(max_work, "max_work")
        _integer(max_block_bytes, "max_block_bytes")
        state = core._issued(prepared)
        source_ref, group_ref = _task_binding(prepared, state, task)
        maximum = min(max_work, state.limits.max_work)
        meter = _Measure(maximum)
        # Includes all fixed schema-key/literal width inspections per pair,
        # arithmetic/count operations and small wrappers. Dynamic selector and
        # assumption widths are inspected once in affected entry summaries.
        meter.charge(512 + task.expected_pairs * (4096 + len(core.CATEGORIES) * 256))
        global_.update(_refinement_summary(state.catalog["refinement"], meter))
        sound_atoms, bass_atoms = global_["sound_atoms"], global_["bass_atoms"]
        for index in range(task.row_start, task.row_end):
            summaries[index] = _entry_summary(state, index, meter)
        for index in range(task.column_start, task.column_end):
            if index not in summaries:
                summaries[index] = _entry_summary(state, index, meter)
        ref_sizes = []
        for ref in (source_ref, _ref(state.catalog), group_ref):
            ref_sizes.append(_measure_owned(ref, meter))
        pair_total = maximum_pair = pair_count = 0
        for i in range(task.row_start, task.row_end):
            for j in range(task.column_start, task.column_end):
                if i < j:
                    size = _pair_bound(state.catalog["actual_refinement_atoms"], i, j, summaries[i], summaries[j], global_, ref_sizes)
                    pair_total += size
                    maximum_pair = max(maximum_pair, size)
                    pair_count += 1
        if pair_count != task.expected_pairs:
            raise ValueError("whole_task_exact_pair_denominator_mismatch")
        task_bytes = _measure_owned(asdict(task), meter)
        flags_bytes = _measure_owned(core.legacy._flags(), meter)
        reasons = ("whole_block_pair_bytes_exceeds_limit_no_prefix", "whole_block_buffer_bytes_exceeds_limit_no_prefix",
            "whole_block_encoded_bytes_exceeds_limit_no_prefix")
        reason_bound = 2 + sum(_string_width(reason) for reason in reasons) + len(reasons) - 1
        count_width = len(str(task.expected_pairs))
        fields = {"version": _string_width(core.VERSION), "source_catalog_ref": ref_sizes[0],
            "catalog_ref": ref_sizes[1], "group_ref": ref_sizes[2], "refinement_sha256": 66,
            "entry_inventory_sha256": 66, "task": task_bytes, "planned_pairs": count_width,
            "computed_pairs": count_width, "withheld_pairs": count_width,
            "pairs": 2 + pair_total + max(0, pair_count - 1), "reasons": reason_bound,
            "status": max(_string_width(value) for value in ("whole_saved_block_hold", "computed_saved_block_not_selected")),
            "whole_group_complete": 5, "musical_outcome": 4, "selected": 4, "rank": 4, "confidence": 4,
            "flags": flags_bytes, "record_id": _string_width(core.BLOCK_PREFIX) + 24, "record_sha256": 66}
        bound = _object_bound(fields)
        cap = min(max_block_bytes, state.limits.max_block_record_bytes)
        holds = []
        if maximum_pair > state.limits.max_pair_record_bytes:
            holds.append("whole_pair_schema_byte_bound_hold_no_prefix")
        if bound > cap:
            holds.append("whole_block_schema_byte_bound_hold_no_prefix")
        return {"version": VERSION, "schema_scope": "compact_compare_block_not_materialized_legacy_pair",
            "source_ref": source_ref, "group_ref": group_ref, "catalog_ref": _ref(state.catalog),
            "refinement_sha256": state.catalog["refinement_sha256"], "entry_inventory_sha256": state.catalog["entry_inventory_sha256"],
            "task": asdict(task), "expected_pairs": pair_count, "raw_block_byte_upper_bound": bound,
            "maximum_pair_byte_upper_bound": maximum_pair, "inspection_work": meter.work,
            "planning_work_upper_bound": meter.work, "sound_pointer_count_upper_bound_per_pair": sound_atoms,
            "bass_pointer_count_upper_bound_per_pair": bass_atoms, "transfer_rational_byte_upper_bound": global_["transfer_rational_bytes"],
            "max_block_bytes": cap, "reasons": holds,
            "status": "whole_block_stream_bound_hold" if holds else "admissible_whole_block_stream_bound",
            "descriptor_is_not_authority": True, "pair_outputs_computed": 0,
            "full_archive_or_music_accuracy_claimed": False}
    except StreamHold as error:
        return {"version": VERSION, "schema_scope": "compact_compare_block_not_materialized_legacy_pair",
            "expected_pairs": task.expected_pairs if type(task) is core.BlockTask else None,
            "raw_block_byte_upper_bound": None, "maximum_pair_byte_upper_bound": None,
            "inspection_work": error.diagnostics["inspection_work_lower_bound"], "planning_work_upper_bound": None,
            "reasons": [str(error)], "status": "whole_block_stream_bound_hold",
            "descriptor_is_not_authority": True, "pair_outputs_computed": 0,
            "full_archive_or_music_accuracy_claimed": False}
    finally:
        summaries.clear()
        global_.clear()
        prepared = task = state = meter = points = point = refinement = sound = bass_points = None
