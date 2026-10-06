"""Explicit local-key and ordinary functional SHAPE assumptions, not truth.

All coordinates are conditioned on caller hypotheses outside Canonical Core.
No annotation/key signature, actual voice resolution, consonance or cadence is
inferred here. Unknown context preserves the ordinary-shape inventory.
"""
from copy import deepcopy

from . import factor_musical_view as common
from .applied_chords import hypothesis
from .tonal_foundations import scale_degree

VERSION = "factor-functional-overlay-0.1.0"
KEY_VERSION = "factor-local-key-track-0.1.0"
KEY_PREFIX = "fmkey_"
PREFIX = "fmfunc_"
FAMILIES = ("V", "V7", "vii", "vii7", "vii_half7")
ROOT_INTERVALS = {"V": (4, 7), "V7": (4, 7), "vii": (6, 11),
                  "vii7": (6, 11), "vii_half7": (6, 11)}
KEY_SEGMENT_KEYS = {"segment_id", "span", "tonic", "mode", "scale_form"}
KEY_KEYS = {"version", "binding", "view_ref", "context_span", "segments", "provenance", "use_policy", "flags"}
FUNCTION_KEYS = {"version", "binding", "view_ref", "path_ref", "key_track_ref", "context_span",
                 "max_candidates", "total_candidates", "rows", "status", "reasons", "flags"}
FUNCTION_ROW_KEYS = {"function_id", "source_segment_ref", "source_span", "source_root", "source_members",
                     "family", "target_root", "target_quality", "target_members", "target_span",
                     "target_segment_ref", "target_basis", "key_segment_ref", "key_span", "key_tonic",
                     "key_mode", "scale_form", "function_kind", "leading_tone", "seventh",
                     "shape_compatible", "target_shape_compatible", "prerequisites", "blockers", "status"}
PROVENANCE_KEYS = {"kind", "engine_version", "source_document_sha256", "source_path", "pitch_basis", "status"}
FORMS = {"major": "major", "natural_minor": "natural_minor", "harmonic_minor": "harmonic_minor",
         "melodic_minor_ascending": "melodic_minor_ascending"}


def _flags():
    return {name: False for name in ("key_inferred", "function_confirmed", "cadence_confirmed", "selected",
        "training_eligible", "gold_eligible", "generation_ready", "source_labels_used", "key_signature_used",
        "counts_are_confidence")}


def _closed(value, keys, name):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("closed_functional_contract_required:" + name)


def _string(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError("nonempty_functional_string_required:" + name)


def _pc(value):
    _closed(value, {"step", "alter"}, "pitch_class")
    common.pitch_key(value)


def _bounds(value):
    _closed(value, {"start", "end"}, "span")
    return common.span_bounds(value)


def _provenance(value):
    _closed(value, PROVENANCE_KEYS, "caller_hypothesis_provenance")
    _string(value["engine_version"], "engine_version")
    if (value["kind"] != "caller_hypothesis" or value["source_document_sha256"] is not None
            or value["source_path"] is not None or value["pitch_basis"] != "written_IR_not_concert_certified"
            or value["status"] != "hypothesis_not_gold"):
        raise ValueError("explicit_caller_key_hypothesis_without_SOURCE_required")


def _key_segments(segments, context):
    if not isinstance(segments, list) or not segments:
        raise ValueError("complete_key_partition_required")
    cursor, end = _bounds(context)
    ids = set()
    for row in segments:
        _closed(row, KEY_SEGMENT_KEYS, "key_segment")
        _string(row["segment_id"], "key_segment_id")
        if row["segment_id"] in ids:
            raise ValueError("duplicate_key_segment_id")
        ids.add(row["segment_id"])
        start, stop = _bounds(row["span"])
        if start != cursor or stop > end:
            raise ValueError("complete_ordered_key_partition_required")
        cursor = stop
        if row["tonic"] is not None:
            _pc(row["tonic"])
        mode, form = row["mode"], row["scale_form"]
        if mode not in ("major", "minor", "unknown"):
            raise ValueError("supported_explicit_key_mode_required")
        allowed = {"major": {"major", "unknown"},
                   "minor": {"natural_minor", "harmonic_minor", "melodic_minor_ascending", "unknown"},
                   "unknown": {"unknown"}}
        if form not in allowed[mode] or (mode != "unknown" and row["tonic"] is None):
            raise ValueError("explicit_compatible_key_tonic_and_scale_form_required")
    if cursor != end:
        raise ValueError("complete_ordered_key_partition_required")


def make_key_track(view, segments, provenance):
    common.validate_view(view)
    _key_segments(segments, view["context_span"])
    _provenance(provenance)
    return common.seal({"version": KEY_VERSION, "binding": deepcopy(view["binding"]),
        "view_ref": common.ref(view), "context_span": deepcopy(view["context_span"]),
        "segments": deepcopy(segments), "provenance": deepcopy(provenance),
        "use_policy": deepcopy(common.POLICY), "flags": _flags()}, KEY_PREFIX)


def validate_key_track(view, record):
    common.validate_view(view)
    body = common.check(record, KEY_PREFIX)
    _closed(body, KEY_KEYS, "key_track")
    if (body["version"] != KEY_VERSION or body["binding"] != view["binding"]
            or body["view_ref"] != common.ref(view) or body["context_span"] != view["context_span"]
            or body["use_policy"] != common.POLICY or body["flags"] != _flags()
            or any(type(v) is not bool for v in body["use_policy"].values())
            or any(type(v) is not bool for v in body["flags"].values())):
        raise ValueError("stale_foreign_or_promoting_key_track")
    _provenance(body["provenance"])
    _key_segments(body["segments"], body["context_span"])
    return True


def _integer(pitch):
    return pitch is not None and common.f(pitch["alter"]).denominator == 1


def _old(pitch):
    # No int(Fraction) truncation: every caller must establish this domain.
    if not _integer(pitch):
        raise ValueError("integer_spelling_required_for_ordinary_helper")
    return [pitch["step"], common.f(pitch["alter"]).numerator]


def _pitch(pair):
    return {"step": pair[0], "alter": common.q(pair[1])}


def _derived_target(root, family):
    step, alter = _old(root)
    letters, natural = "CDEFGAB", (0, 2, 4, 5, 7, 9, 11)
    steps, semitones = ROOT_INTERVALS[family]
    index = letters.index(step)
    target = index - steps
    return [letters[target % 7], natural[index] + alter - semitones
            - natural[target % 7] - 12 * (target // 7)]


def _members(values):
    return {common.pitch_key(p) for p in values}


def _project(key, root, quality, source_members, source, target):
    unassessed = []
    relation_end = common.f(source["span"]["end"] if target is None else target["span"]["end"])
    lo, hi = _bounds(key["span"])
    covers = lo <= common.f(source["span"]["start"]) and relation_end <= hi
    if key["mode"] == "unknown" or key["tonic"] is None:
        unassessed.append("explicit_local_key_unknown")
    if not covers:
        unassessed.append("key_span_does_not_cover_relation")
    if key["tonic"] is not None and not _integer(key["tonic"]):
        unassessed.append("microtonal_key_projection_not_supported")
    if root is None:
        unassessed.append("ordinary_target_spelling_unknown")
    kind, coordinate, chromatic = "unassessed", None, None
    known = not unassessed
    if known:
        same = common.pitch_key(root) == common.pitch_key(key["tonic"])
        home = "M" if key["mode"] == "major" else "m"
        kind = ("primary" if quality == home else "parallel") if same else "applied"
        form = FORMS.get(key["scale_form"])
        if form is not None:
            coordinate = scale_degree(*_old(root), *_old(key["tonic"]), form=form)
            chromatic = [deepcopy(p) for p in source_members
                         if not scale_degree(*_old(p), *_old(key["tonic"]), form=form)["diatonic_to_candidate"]]
        else:
            unassessed.append("scale_form_coordinate_unassessed")
    return kind, {"key_projection_assessed": known, "key_covers_relation_span": covers,
        "target_coordinate": coordinate, "chromatic_source_members": chromatic,
        "key_unassessed_reasons": unassessed,
        "scale_form_reference_policy": ("explicit_melodic_minor_ascending_reference_not_direction_rule"
                                        if key["scale_form"] == "melodic_minor_ascending" else "explicit_form_or_unknown")}


def _row(view, path, key_track, source, target, key, family, quality):
    blockers = ["source_harmony:" + reason for reason in source["blockers"]]
    if source["status"] != "usable":
        blockers.append("source_harmony_segment_not_usable")
    source_integer = _integer(source["root"]) and all(_integer(p) for p in source["members"])
    target_root = None
    target_members, leading, seventh, expected_source = [], None, None, []
    shape = None
    profile = None
    if source["root"] is None:
        blockers.append("source_root_not_supplied")
    elif not source_integer:
        blockers.append("microtonal_source_shape_not_supported")
    else:
        # Invert the supplied family's root interval. The target is a derived
        # shape assumption, not a fabricated observed harmony or key.
        root = _derived_target(source["root"], family)
        h = hypothesis(root, quality, family)
        target_root = _pitch(h["target"]["root"])
        target_members = [_pitch(p) for p in h["target"]["members"]]
        expected_source = [_pitch(p) for p in h["chord"]["members"]]
        leading = _pitch(h["leading_tone"])
        seventh = _pitch(h["chord"]["members"][3]) if len(h["chord"]["members"]) == 4 else None
        profile = h["textbook_profile"]
        shape = (_members(source["members"]) == _members(expected_source)
                 and common.pitch_key(source["root"]) == common.pitch_key(_pitch(h["chord"]["root"])))
        if not shape:
            blockers.append("source_ordinary_family_shape_mismatch")
    compatible, missing, additional = None, None, None
    if target is None:
        blockers.append("next_target_segment_not_observed")
    else:
        blockers.extend("target_harmony:" + reason for reason in target["blockers"])
        if target["status"] != "usable":
            blockers.append("target_harmony_segment_not_usable")
        if target["root"] is None:
            blockers.append("next_target_root_not_supplied")
        elif not _integer(target["root"]) or any(not _integer(p) for p in target["members"]):
            blockers.append("microtonal_target_shape_not_supported")
        elif target_root is not None:
            expected, actual = _members(target_members), _members(target["members"])
            missing = [deepcopy(p) for p in target_members if common.pitch_key(p) not in actual]
            additional = [deepcopy(p) for p in target["members"] if common.pitch_key(p) not in expected]
            compatible = common.pitch_key(target["root"]) == common.pitch_key(target_root) and expected <= actual
            if not compatible:
                blockers.append("next_target_triad_core_shape_mismatch")
    kind, projection = _project(key, target_root, quality, expected_source, source, target)
    if key["tonic"] is not None and not _integer(key["tonic"]):
        blockers.append("microtonal_key_projection_not_supported")
    body = {"source_segment_ref": source["segment_id"], "source_span": deepcopy(source["span"]),
        "source_root": deepcopy(source["root"]), "source_members": deepcopy(source["members"]),
        "family": family, "target_root": target_root, "target_quality": quality, "target_members": target_members,
        "target_span": None if target is None else deepcopy(target["span"]),
        "target_segment_ref": None if target is None else target["segment_id"],
        "target_basis": "derived_target_without_next" if target is None else "next_path_segment",
        "key_segment_ref": key["segment_id"], "key_span": deepcopy(key["span"]), "key_tonic": deepcopy(key["tonic"]),
        "key_mode": key["mode"], "scale_form": key["scale_form"], "function_kind": kind,
        "leading_tone": leading, "seventh": seventh, "shape_compatible": shape,
        "target_shape_compatible": compatible,
        "prerequisites": {**projection, "key_coverage_span": common.clipped(source["span"], key["span"]),
            "actual_target": deepcopy(target), "expected_source_core": expected_source,
            "target_core_missing_members": missing, "target_additional_members": additional,
            "target_quality_is_triad_core_assumption": True, "textbook_profile": profile,
            "profile_is_universal_prohibition": False,
            "pitch_basis": "written_IR_not_concert_certified",
            "actual_motion": "unassessed", "actual_target_identity": "unassessed",
            "source_clock_and_written_pitch": "required_per_involved_sound_by_resolution_consumer",
            "consonance": "unassessed", "accent": "unassessed", "cadence": "unassessed",
            "chromatic_member_is_not_function_proof": True},
        "blockers": sorted(set(blockers)), "status": "withheld" if blockers else "conditional_function_shape"}
    return {"function_id": "fmfunction_" + common.digest([common.ref(view), common.ref(path), common.ref(key_track), body])[:24], **body}


def compile_functions(view, path, key_track, max_candidates=512):
    common.validate_path(view, path)
    validate_key_track(view, key_track)
    if type(max_candidates) is not int or max_candidates < 0:
        raise ValueError("nonnegative_integer_function_candidate_budget_required")
    # Count the whole formal inventory before constructing any success subset.
    count = sum(2 * len(FAMILIES) for source in path["segments"] for key in key_track["segments"]
                if common.clipped(source["span"], key["span"]) is not None)
    rows = []
    exceeded = count > max_candidates
    if not exceeded:
        for index, source in enumerate(path["segments"]):
            target = path["segments"][index + 1] if index + 1 < len(path["segments"]) else None
            for key in key_track["segments"]:
                if common.clipped(source["span"], key["span"]) is None:
                    continue
                for family in FAMILIES:
                    for quality in ("M", "m"):
                        rows.append(_row(view, path, key_track, source, target, key, family, quality))
        rows.sort(key=lambda row: row["function_id"])
        if len(rows) != count or len({r["function_id"] for r in rows}) != count:
            raise ValueError("function_inventory_cardinality_or_identity_mismatch")
    return common.seal({"version": VERSION, "binding": deepcopy(view["binding"]),
        "view_ref": common.ref(view), "path_ref": common.ref(path), "key_track_ref": common.ref(key_track),
        "context_span": deepcopy(view["context_span"]), "max_candidates": max_candidates,
        "total_candidates": count, "rows": rows, "status": "candidate_budget_abstention" if exceeded else "ready",
        "reasons": ["whole_function_inventory_exceeds_budget_no_pruning"] if exceeded else [], "flags": _flags()}, PREFIX)


def validate_functions(view, path, key_track, record, max_candidates=512):
    body = common.check(record, PREFIX)
    _closed(body, FUNCTION_KEYS, "functions")
    for row in body["rows"]:
        _closed(row, FUNCTION_ROW_KEYS, "function_row")
    if record != compile_functions(view, path, key_track, max_candidates=max_candidates):
        raise ValueError("stale_foreign_or_modified_functional_overlay")
    return True

