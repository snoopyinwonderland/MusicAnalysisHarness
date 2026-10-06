"""Sealed research hypotheses bound to an immutable, written-pitch G1 IR.

Tracks may compete and may leave explicit holes. They never establish gold,
rank a winner, certify concert pitch, or change the score. RomanText is only
imported when explicit source coordinates agree with regular IR measures.
Unsupported events remain held diagnostics; no span or spelling is guessed.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from music21 import converter, meter, roman, stream
from music21.romanText import rtObjects

from .musical_pattern_observation import (
    CORE_SCHEMA_PATH, digest, f, q, span_bounds, validate_core,
)

VERSION = "musical-harmony-assumption-0.1.0"
SCHEMA_NAME = "musicanote-musical-harmony-assumption"
SCHEMA_VERSION = "0.1.0"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs/harmony/schemas/musical_harmony_assumption.schema.json"
PITCH_BASIS = "written_IR_not_concert_certified"
USE_POLICY = {"research_only": True, "training_eligible": False,
              "gold_status": "not_established", "generation_ready": False}
MEASURE_LINE = re.compile(r"^\s*m(\d+[A-Za-z]?)\s+(.+?)\s*$")
METER_DECLARATION = re.compile(r"^\s*Time Signature:", re.MULTILINE | re.IGNORECASE)


@lru_cache(maxsize=1)
def _validator():
    core = json.loads(CORE_SCHEMA_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    registry = Registry().with_resource(core["$id"], Resource.from_contents(core))
    return Draft202012Validator(schema, registry=registry)


def _holes(segments, duration):
    """Uncovered usable-hypothesis intervals, including blocked intervals."""
    cursor, result = Fraction(0), []
    usable = sorted((span_bounds(row["span"]) for row in segments if row["status"] == "usable"))
    for start, end in usable:
        if cursor < start:
            result.append({"start": q(cursor), "end": q(start)})
        cursor = end
    if cursor < duration:
        result.append({"start": q(cursor), "end": q(duration)})
    return result


def _seal(payload):
    result = deepcopy(payload)
    result["record_sha256"] = digest(result)
    result["record_id"] = "mha_" + result["record_sha256"][:24]
    return result


def _build(ir, segments, provenance, diagnostics):
    validate_core(ir)
    payload = {"schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
               "producer_version": VERSION,
               "binding": {"score_id": ir["score"]["score_id"],
                           "ir_document_id": ir["ir_document_id"],
                           "ir_content_sha256": digest(ir),
                           "source_files": deepcopy(ir["source_files"])},
               "provenance": deepcopy(provenance), "segments": deepcopy(segments),
               "coverage_holes": _holes(segments, f(ir["score"]["duration_quarters"])),
               "import_diagnostics": deepcopy(diagnostics), "use_policy": deepcopy(USE_POLICY)}
    result = _seal(payload)
    validate_track(result, ir=ir)
    return result


def build_track(ir, segments, provenance):
    """Copy and seal a caller-supplied hypothesis; never choose among tracks.

    Segment and provenance fields are explicit, schema-validated inputs. No
    pitches, source locations, intervals, or provenance defaults are inferred.
    """
    return _build(ir, segments, provenance, [])


def validate_track(track, ir=None):
    """Check the seal and internal invariants; optional IR verifies its binding.

    Without the IR this cannot independently prove score duration or measure
    references. With it, every span, source locator, and coverage hole is checked.
    """
    _validator().validate(track)
    payload = {key: value for key, value in track.items() if key not in ("record_id", "record_sha256")}
    expected = digest(payload)
    if track["record_sha256"] != expected or track["record_id"] != "mha_" + expected[:24]:
        raise ValueError("harmony_assumption_seal_mismatch")
    sources = track["binding"]["source_files"]
    if len({row["source_file_id"] for row in sources}) != len(sources):
        raise ValueError("duplicate_binding_source_file")
    ids, bounds = set(), []
    for segment in track["segments"]:
        if segment["segment_id"] in ids:
            raise ValueError("duplicate_harmony_segment")
        ids.add(segment["segment_id"])
        bounds.append(span_bounds(segment["span"]))
        members = [(member["step"], f(member["alter"])) for member in segment["members"]]
        if len(members) != len(set(members)):
            raise ValueError("duplicate_harmony_member")
        if segment["root"] is not None:
            f(segment["root"]["alter"])
        if segment["status"] == "usable" and (not members or segment["blockers"]):
            raise ValueError("usable_harmony_segment_requires_members_without_blockers")
        if segment["status"] == "blocked" and not segment["blockers"]:
            raise ValueError("blocked_harmony_segment_requires_blockers")
        locator = segment["source_locator"]
        if locator is not None and track["provenance"]["kind"] != "source_annotation":
            raise ValueError("caller_hypothesis_cannot_claim_source_locator")
        if track["provenance"]["kind"] == "source_annotation" and segment["status"] == "usable":
            if locator is None or locator["line_number"] is None or locator["raw_line"] is None:
                raise ValueError("usable_source_annotation_requires_explicit_locator")
    ordered = sorted(bounds)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        raise ValueError("overlapping_harmony_segments")
    holes = [span_bounds(row) for row in track["coverage_holes"]]
    if holes != sorted(holes) or any(left[1] >= right[0] for left, right in zip(holes, holes[1:])):
        raise ValueError("invalid_harmony_coverage_holes")
    usable = [span_bounds(row["span"]) for row in track["segments"] if row["status"] == "usable"]
    if any(start < hole_end and end > hole_start
           for start, end in usable for hole_start, hole_end in holes):
        raise ValueError("coverage_hole_overlaps_usable_harmony")
    if ir is not None:
        validate_core(ir)
        expected_binding = {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
                            "ir_content_sha256": digest(ir), "source_files": ir["source_files"]}
        if track["binding"] != expected_binding:
            raise ValueError("stale_or_foreign_harmony_assumption_ir")
        duration = f(ir["score"]["duration_quarters"])
        if any(end > duration for _, end in [*bounds, *holes]):
            raise ValueError("harmony_segment_outside_score")
        if track["coverage_holes"] != _holes(track["segments"], duration):
            raise ValueError("harmony_coverage_holes_mismatch")
        for segment in track["segments"]:
            locator = segment["source_locator"]
            if locator is None:
                continue
            matches = [row for row in ir["measures"]
                       if row["printed_measure_number"] == locator["printed_measure_number"]]
            if len(matches) != 1:
                raise ValueError("source_locator_measure_missing_or_not_unique")
            measure = matches[0]
            start, _ = span_bounds(segment["span"])
            left = f(measure["global_start_quarter"])
            if not left <= start < left + f(measure["actual_duration_quarter"]):
                raise ValueError("source_locator_outside_segment_start_measure")


def _pitch(value):
    return {"step": value.step,
            "alter": q(Fraction(value.accidental.alter) if value.accidental is not None else 0)}


def _source_lines(text):
    result = {}
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        match = MEASURE_LINE.fullmatch(raw_line)
        if match:
            label, contents = match.groups()
            result.setdefault(label, []).append({"printed_measure_number": label,
                                                 "line_number": line_number, "raw_line": raw_line,
                                                 "copied": "=" in contents})
    return result


def _locator(label, lines):
    candidates = lines.get(label, [])
    if len(candidates) != 1 or candidates[0]["copied"]:
        return None
    return {key: value for key, value in candidates[0].items() if key != "copied"}


def _source_beat_issue(locator):
    if locator is None:
        return None
    # RomanText can silently normalize .33/.66 to thirds. Keep the same
    # conservative terminating-binary boundary as semantic alignment; never
    # certify parser-rounded source timing as exact source timing.
    for token in re.findall(r"(?:^|\s)b(\d\S*)", locator["raw_line"]):
        try:
            beat = Fraction(token)
        except (ValueError, ZeroDivisionError):
            return "unsupported_source_beat_requires_review"
        if beat.denominator & (beat.denominator - 1):
            return "rounded_or_nonbinary_beat_requires_review"
    return None


def _initial_key_issue(text):
    """Require an inline tonal key before the first literal chord token.

    music21 treats Key Signature headers as notation only, not as analytical
    keys. No header or implicit C fallback certifies chord-member spelling.
    v0.1 holds the entire import if its first chord lacks an explicit key,
    even if a later measure supplies one; no post-hoc propagation is allowed.
    """
    handler = rtObjects.RTHandler()
    for raw_line in text.splitlines():
        match = MEASURE_LINE.fullmatch(raw_line)
        if match is None:
            continue
        for atom in handler.tokenizeAtoms(match.group(2)):
            if isinstance(atom, (rtObjects.RTKey, rtObjects.RTAnalyticKey)):
                return None
            if isinstance(atom, rtObjects.RTChord):
                return "missing_initial_explicit_source_key"
    return "missing_initial_explicit_source_key"


def _measure_alignment(source_measure, ir, meter_index):
    label = str(source_measure.measureNumberWithSuffix())
    candidates = [row for row in ir["measures"] if row["printed_measure_number"] == label]
    source_rows = [row for row in meter_index.get("measures", []) if row["printed_measure_number"] == label]
    if len(candidates) != 1:
        raise ValueError("printed_measure_missing_or_not_unique")
    if len(source_rows) != 1:
        raise ValueError("source_meter_measure_missing_or_not_unique")
    target, source = candidates[0], source_rows[0]
    signature = source_measure.timeSignature or source_measure.getContextByClass(meter.TimeSignature)
    if signature is None:
        raise ValueError("missing_explicit_source_meter")
    if (source["numerator"], source["denominator"]) != (signature.numerator, signature.denominator):
        raise ValueError("meter_index_parsed_source_mismatch")
    if source.get("source_meter") != signature.ratioString:
        raise ValueError("meter_index_parsed_source_mismatch")
    declared = target["time_signature"]
    if (declared["beats"], declared["beat_type"]) != (signature.numerator, signature.denominator):
        raise ValueError("source_score_meter_mismatch")
    nominal = f(target["nominal_duration_quarter"])
    actual = f(target["actual_duration_quarter"])
    if (target["pickup"] or actual != nominal or source_measure.paddingLeft != 0
            or f(source["padding_left_quarter"]) != 0
            or Fraction(source_measure.duration.quarterLength) != Fraction(signature.barDuration.quarterLength)
            or nominal != Fraction(signature.barDuration.quarterLength)):
        raise ValueError("pickup_or_irregular_measure_requires_review")
    return target


def import_romantext(path, ir, meter_index):
    """Import parsed chord spellings only; unsupported coordinates stay held.

    A unique literal mN source line is needed for usable source provenance.
    Copied/range/generated events may retain safe spans as blocked segments,
    but never claim a full source locator. Explicit initial meter is required;
    no music21 fallback/default meter or transposition certification is used.
    An explicit inline tonal key must precede the first chord: otherwise all
    events remain held in v0.1, including events following a later key token.
    """
    validate_core(ir)
    path = Path(path)
    payload = path.read_bytes()
    source_sha256 = sha256(payload).hexdigest()
    if source_sha256 != meter_index.get("source_sha256"):
        raise ValueError("stale_meter_index_source")
    text = payload.decode("utf-8-sig")
    provenance = {"kind": "source_annotation", "engine_version": VERSION,
                  "source_document_sha256": source_sha256, "source_path": str(path.resolve()),
                  "pitch_basis": PITCH_BASIS, "status": "hypothesis_not_gold"}
    segments, diagnostics = [], []

    def held(label, figure, reason, locator=None, local_span=None):
        diagnostics.append({"status": "held", "label": figure,
                            "printed_measure_number": label, "source_locator": deepcopy(locator),
                            "local_span": deepcopy(local_span), "blockers": [reason]})

    initial = METER_DECLARATION.search(text)
    first_measure = re.search(r"^\s*m\d", text, re.MULTILINE)
    meter_issue = None
    if meter_index.get("status") != "parsed_RomanText_meter":
        meter_issue = str(meter_index.get("status", "missing_explicit_source_meter"))
    elif initial is None or (first_measure is not None and initial.start() > first_measure.start()):
        meter_issue = "missing_initial_explicit_source_meter"
    try:
        parsed = converter.parse(path, format="romanText")
    except Exception as exc:
        # A parse error is source evidence to review, not license to synthesize.
        held(None, None, "RomanText_parse_error:" + type(exc).__name__)
        return _build(ir, segments, provenance, diagnostics)
    if len(parsed.parts) != 1:
        held(None, None, "RomanText_requires_one_analysis_part")
        return _build(ir, segments, provenance, diagnostics)
    source_measures = list(parsed.parts[0].getElementsByClass(stream.Measure))
    labels = [str(row.measureNumberWithSuffix()) for row in source_measures]
    lines = _source_lines(text)
    key_issue = _initial_key_issue(text)
    for source_measure, label in zip(source_measures, labels):
        locator = _locator(label, lines)
        chords = list(source_measure.recurse().getElementsByClass(roman.RomanNumeral))
        reason = meter_issue or key_issue or _source_beat_issue(locator)
        target = None
        if reason is None:
            try:
                if labels.count(label) != 1:
                    raise ValueError("source_measure_missing_or_not_unique")
                target = _measure_alignment(source_measure, ir, meter_index)
            except (ValueError, KeyError, TypeError) as exc:
                reason = str(exc) if isinstance(exc, ValueError) else "invalid_source_meter_index"
        if not chords:
            held(label, None, reason or "no_parsed_RomanNumeral_event", locator)
        for chord in chords:
            local_start = Fraction(chord.getOffsetInHierarchy(source_measure))
            local_end = local_start + Fraction(chord.duration.quarterLength)
            local_span = {"start": q(local_start), "end": q(local_end)}
            if reason is not None:
                held(label, chord.figure, reason, locator, local_span)
                continue
            actual = f(target["actual_duration_quarter"])
            if not 0 <= local_start < local_end <= actual:
                held(label, chord.figure, "RomanNumeral_span_outside_regular_measure", locator, local_span)
                continue
            global_start = f(target["global_start_quarter"]) + local_start
            global_end = f(target["global_start_quarter"]) + local_end
            if global_end > f(ir["score"]["duration_quarters"]):
                held(label, chord.figure, "RomanNumeral_span_outside_score", locator, local_span)
                continue
            try:
                root = _pitch(chord.root())
                members = [_pitch(pitch) for pitch in chord.pitches]
            except Exception as exc:
                held(label, chord.figure, "unsupported_RomanNumeral_spelling:" + type(exc).__name__, locator, local_span)
                continue
            if not members or len({(row["step"], f(row["alter"])) for row in members}) != len(members):
                held(label, chord.figure, "empty_or_duplicate_parsed_chord_members", locator, local_span)
                continue
            blockers = [] if locator is not None else ["copied_range_or_unclear_source_locator_requires_review"]
            segment = {"segment_id": "rn_" + str(len(segments) + 1),
                       "span": {"start": q(global_start), "end": q(global_end)},
                       "label": chord.figure, "root": root, "members": members,
                       "status": "blocked" if blockers else "usable", "blockers": blockers,
                       "source_locator": deepcopy(locator)}
            if any(global_start < f(existing["span"]["end"]) and global_end > f(existing["span"]["start"])
                   for existing in segments):
                held(label, chord.figure, "overlapping_parsed_harmony_event_requires_review", locator, local_span)
                continue
            segments.append(segment)
            if blockers:
                held(label, chord.figure, blockers[0], None, local_span)
    if meter_issue and not diagnostics:
        held(None, None, meter_issue)
    return _build(ir, segments, provenance, diagnostics)
