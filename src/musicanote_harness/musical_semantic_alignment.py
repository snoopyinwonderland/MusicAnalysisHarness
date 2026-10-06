"""Conservative coordinates for native RomanText Pedal statements.

No NCT/voice/texture role is inferred. Note prose stays unaligned; Form has no
explicit end. Pedal end is exclusive per the RomanText specification. The
annotated pitch token is retained literally, not resolved to a score lane.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from music21 import converter, meter, stream

from .musical_semantic_enrichment import record_ref, validate_record
from .musical_pattern_observation import digest, f, q, validate_core

VERSION = "musical-semantic-alignment-0.1.1"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs/harmony/schemas/musical_semantic_alignment.schema.json"
PEDAL = re.compile(r"^\s*(\S+)\s+m(\d+[A-Za-z]?)\s+b(\d+(?:\.\d+)?)\s+m(\d+[A-Za-z]?)\s+b(\d+(?:\.\d+)?)\s*$")


def prepare_meter_index(path):
    path = Path(path)
    payload = path.read_bytes()
    text = payload.decode("utf-8-sig")
    # A parser default is not an observed time signature declaration.
    if not re.search(r"^\s*Time Signature:", text, re.MULTILINE | re.IGNORECASE):
        return {"source_sha256": hashlib.sha256(payload).hexdigest(), "status": "missing_explicit_source_meter", "measures": []}
    initial_meter = re.search(r"^\s*Time Signature:", text, re.MULTILINE | re.IGNORECASE)
    first_measure = re.search(r"^\s*m\d", text, re.MULTILINE)
    if first_measure is not None and initial_meter.start() > first_measure.start():
        return {"source_sha256": hashlib.sha256(payload).hexdigest(), "status": "missing_initial_source_meter", "measures": []}
    part = converter.parse(path, format="romanText").parts[0]
    rows = []
    for measure in part.getElementsByClass(stream.Measure):
        signature = measure.timeSignature or measure.getContextByClass(meter.TimeSignature)
        if signature is None:
            continue
        rows.append({"printed_measure_number": str(measure.measureNumberWithSuffix()),
                     "numerator": signature.numerator, "denominator": signature.denominator,
                     "beat_spans_quarter": [{"start": q(Fraction(start)), "end": q(Fraction(end))}
                                            for start, end in signature.beatSequence.getLevelSpan()],
                     "padding_left_quarter": q(Fraction(measure.paddingLeft)),
                     "source_meter": signature.ratioString})
    return {"source_sha256": hashlib.sha256(payload).hexdigest(), "status": "parsed_RomanText_meter", "measures": rows}


def _endpoint(label, beat_text, ir, index):
    candidates = [row for row in ir["measures"] if row["printed_measure_number"] == label]
    source = [row for row in index["measures"] if row["printed_measure_number"] == label]
    if len(candidates) != 1:
        raise ValueError("printed_measure_missing_or_not_unique")
    if len(source) != 1:
        raise ValueError("source_measure_missing_or_not_unique")
    measure, source = candidates[0], source[0]
    signature = measure["time_signature"]
    if (signature["beats"], signature["beat_type"]) != (source["numerator"], source["denominator"]):
        raise ValueError("source_score_meter_mismatch")
    if measure["pickup"] or f(source["padding_left_quarter"]) != 0 or f(measure["actual_duration_quarter"]) != f(measure["nominal_duration_quarter"]):
        raise ValueError("pickup_or_irregular_measure_requires_review")
    beat = Fraction(beat_text)
    # .33/.66/.67 may be a rounded triplet convention, not an exact decimal.
    # v0.1 accepts only integer or terminating binary fractions, never snaps.
    if beat.denominator & (beat.denominator - 1):
        raise ValueError("rounded_or_nonbinary_beat_requires_review")
    integer = beat.numerator // beat.denominator
    fraction = beat - integer
    grid = source["beat_spans_quarter"]
    if integer < 1 or integer > len(grid):
        raise ValueError("beat_outside_source_grid")
    start, end = f(grid[integer - 1]["start"]), f(grid[integer - 1]["end"])
    local = start + fraction * (end - start)
    if local < 0 or local >= f(measure["actual_duration_quarter"]):
        raise ValueError("beat_outside_score_measure")
    return {"printed_measure_number": label, "measure_id": measure["measure_id"],
            "sequential_measure_index": measure["sequential_measure_index"],
            "source_beat_literal": beat_text, "source_meter": source["source_meter"],
            "source_beat_spans_quarter": deepcopy(grid), "local_quarter": q(local),
            "global_quarter": q(f(measure["global_start_quarter"]) + local)}


def _payload(source, ir, meter_index):
    validate_record(source)
    if source["record_kind"] != "SOURCE":
        raise ValueError("alignment_requires_source_record")
    context = source["source_context"]
    locator = context["location"]["locator"]
    result = {"schema_name": "musicanote-musical-semantic-alignment", "schema_version": "0.1.0",
              "producer_version": VERSION, "source_statement_ref": record_ref(source),
              "source_sha256": context["source_sha256"], "native_tag": locator["native_tag"],
              "binding": None, "status": "deferred", "reasons": [], "endpoints": [],
              "literal_pitch_token": None,
              "semantics": {"coordinate_only": True, "pedal_lane_identified": False,
                            "musical_role_validated": False, "end_exclusive": True},
              "use_policy": {"research_only": True, "training_eligible": False, "gold_status": "not_established"}}
    if context["source_sha256"] != meter_index["source_sha256"]:
        raise ValueError("stale_meter_index_source")
    if locator["native_tag"] != "Pedal":
        result["reasons"] = ["free_prose_requires_review" if locator["native_tag"] == "Note" else "form_anchor_not_complete_extent"]
        return result
    match = PEDAL.fullmatch(locator["raw_value"])
    if match is None:
        result["reasons"] = ["unsupported_pedal_syntax_explicit_two_beats_required"]
        return result
    pitch_token, start_label, start_beat, end_label, end_beat = match.groups()
    result["literal_pitch_token"] = pitch_token
    if meter_index["status"] != "parsed_RomanText_meter":
        result["reasons"] = [meter_index["status"]]
        return result
    try:
        validate_core(ir)
        start = _endpoint(start_label, start_beat, ir, meter_index)
        end = _endpoint(end_label, end_beat, ir, meter_index)
        if f(start["global_quarter"]) >= f(end["global_quarter"]):
            raise ValueError("empty_or_reversed_pedal_range")
        # Do not bridge an unsupported pickup, missing source meter, duplicate
        # measure, or discontinuous score grid merely because endpoints fit.
        covered = [row for row in ir["measures"] if start["sequential_measure_index"] <= row["sequential_measure_index"] <= end["sequential_measure_index"]]
        previous_end = None
        for measure in covered:
            _endpoint(measure["printed_measure_number"], "1", ir, meter_index)
            if previous_end is not None and f(measure["global_start_quarter"]) != previous_end:
                raise ValueError("discontinuous_score_measure_grid")
            previous_end = f(measure["global_start_quarter"]) + f(measure["actual_duration_quarter"])
        result.update(status="exact_coordinate", endpoints=[start, end], binding={
            "score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
            "ir_content_sha256": digest(ir), "source_files": deepcopy(ir["source_files"]),
            "target_span": {"start": start["global_quarter"], "end": end["global_quarter"]}})
    except ValueError as exc:
        result["reasons"] = [str(exc)]
    return result


def align_statement(source, ir, meter_index):
    result = _payload(source, ir, meter_index)
    result["record_sha256"] = digest(result)
    result["record_id"] = "msa_" + result["record_sha256"][:24]
    validate_alignment(result)
    return result


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_alignment(record, *, source=None, ir=None, meter_index=None):
    _validator().validate(record)
    payload = {key: value for key, value in record.items() if key not in ("record_id", "record_sha256")}
    expected = digest(payload)
    if record["record_sha256"] != expected or record["record_id"] != "msa_" + expected[:24]:
        raise ValueError("alignment_seal_mismatch")
    if source is not None or ir is not None or meter_index is not None:
        if source is None or ir is None or meter_index is None:
            raise ValueError("alignment_replay_requires_all_inputs")
        if payload != _payload(source, ir, meter_index):
            raise ValueError("alignment_replay_mismatch")
