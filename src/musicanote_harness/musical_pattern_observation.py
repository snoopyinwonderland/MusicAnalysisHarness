"""Literal, research-only score windows, not accompaniment templates or roles.

The original IR stays immutable. Slots carry exact rational timing and the
complete original event, including spelling/notation. Linked tie/chord/grace
notes outside the window are context, not silently extended musical targets.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

VERSION = "musical-pattern-observation-0.1.0"
SCHEMA_NAME = "musicanote-musical-pattern-observation"
SCHEMA_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[2]
CORE_SCHEMA_PATH = ROOT / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"
SCHEMA_PATH = ROOT / "docs/harmony/schemas/musical_pattern_observation.schema.json"
COLLECTIONS = {"note_events": "note_id", "rest_events": "rest_id",
               "sounding_events": "sounding_event_id", "tie_chains": "tie_chain_id",
               "attack_events": "attack_event_id", "chord_onset_groups": "chord_onset_group_id",
               "parts": "part_id", "staves": "staff_id", "voices": "voice_id",
               "measures": "measure_id", "source_references": "source_ref_id",
               "source_files": "source_file_id"}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def f(value):
    if set(value) != {"numerator", "denominator"} or any(type(x) is not int for x in value.values()):
        raise ValueError("invalid_rational")
    if value["denominator"] <= 0:
        raise ValueError("invalid_rational_denominator")
    return Fraction(value["numerator"], value["denominator"])


def q(value):
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def span_bounds(span):
    start, end = f(span["start"]), f(span["end"])
    if start < 0 or end <= start:
        raise ValueError("invalid_positive_half_open_span")
    return start, end


@lru_cache(maxsize=1)
def validators():
    core = json.loads(CORE_SCHEMA_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(core)
    Draft202012Validator.check_schema(schema)
    registry = Registry().with_resource(core["$id"], Resource.from_contents(core))
    return Draft202012Validator(core), Draft202012Validator(schema, registry=registry)


def validate_core(ir):
    validators()[0].validate(ir)
    indices = {}
    all_ids = set()
    for name, key in COLLECTIONS.items():
        rows = ir[name]
        indices[name] = {row[key]: row for row in rows}
        if len(indices[name]) != len(rows) or all_ids.intersection(indices[name]):
            raise ValueError("duplicate_core_id:" + name)
        all_ids.update(indices[name])
    for event in [*ir["note_events"], *ir["rest_events"]]:
        for field, name in (("part_id", "parts"), ("voice_id", "voices"),
                            ("display_staff_id", "staves"), ("measure_id", "measures"),
                            ("source_ref_id", "source_references")):
            if event[field] not in indices[name]:
                raise ValueError("dangling_event_reference:" + field)
        if event["score_id"] != ir["score"]["score_id"]:
            raise ValueError("event_score_mismatch")
        if f(event["global_onset_quarter"]) < 0 or f(event["notated_duration_quarter"]) < 0:
            raise ValueError("negative_event_time")
        source = indices["source_references"][event["source_ref_id"]]
        if source["source_file_id"] not in indices["source_files"]:
            raise ValueError("dangling_source_file")
        measure = indices["measures"][event["measure_id"]]
        if f(event["global_onset_quarter"]) != f(measure["global_start_quarter"]) + f(event["onset_in_measure"]):
            raise ValueError("event_local_global_mismatch")
    notes = indices["note_events"]
    for event in ir["note_events"]:
        anchor = event["grace"].get("anchor_note_id")
        if anchor is not None and anchor not in notes:
            raise ValueError("dangling_grace_anchor")
        group = event.get("chord_onset_group_id")
        if group is not None and group not in indices["chord_onset_groups"]:
            raise ValueError("dangling_chord_group")
    for name in ("sounding_events", "tie_chains", "chord_onset_groups"):
        for row in ir[name]:
            ids = row.get("source_note_ids", row.get("note_ids"))
            if len(ids) != len(set(ids)) or not set(ids).issubset(notes):
                raise ValueError("dangling_or_duplicate_linked_notes:" + name)
            if "span" in row:
                start, end = f(row["span"]["start"]), f(row["span"]["end"])
                grace_point = name == "sounding_events" and all(notes[item]["grace"]["is_grace"] for item in ids)
                if start < 0 or end < start or (start == end and not grace_point):
                    raise ValueError("invalid_linked_span")
            if "attack_note_id" in row and row["attack_note_id"] not in ids:
                raise ValueError("attack_not_source_member")
    for row in ir["attack_events"]:
        if row["note_id"] not in notes or row["sounding_event_id"] not in indices["sounding_events"]:
            raise ValueError("dangling_attack_reference")
    return indices


def _relation(start, end, bounds):
    left, right = bounds
    if start == end:
        return "point_inside" if left <= start < right else "linked_context_only"
    return "overlap" if start < right and end > left else "linked_context_only"


def _payload(ir, scope):
    indices = validate_core(ir)
    target = span_bounds(scope["target_span"])
    context = span_bounds(scope["context_span"])
    if not (context[0] <= target[0] < target[1] <= context[1] <= f(ir["score"]["duration_quarters"])):
        raise ValueError("target_or_context_outside_score")
    if (scope["score_id"] != ir["score"]["score_id"] or scope["ir_document_id"] != ir["ir_document_id"]
            or scope["ir_content_sha256"] != digest(ir) or scope["source_files"] != ir["source_files"]):
        raise ValueError("stale_or_foreign_scope")
    events = [*ir["note_events"], *ir["rest_events"]]
    selected = set()
    for event in events:
        start = f(event["global_onset_quarter"])
        end = start + f(event["notated_duration_quarter"])
        if _relation(start, end, context) != "linked_context_only":
            selected.add(event.get("note_id", event.get("rest_id")))
    linked = {name: [] for name in ("sounding_events", "tie_chains", "attack_events", "chord_onset_groups")}
    # Close ties/chord groups/grace anchors without reclassifying their outside
    # members as target events. A grace anchor may have its own linked group.
    previous = None
    while previous != selected:
        previous = set(selected)
        for name in ("sounding_events", "tie_chains", "chord_onset_groups"):
            linked[name] = [row for row in ir[name]
                            if selected.intersection(row.get("source_note_ids", row.get("note_ids")))]
            for row in linked[name]:
                selected.update(row.get("source_note_ids", row.get("note_ids")))
        for event_id in list(selected):
            if event_id in indices["note_events"]:
                anchor = indices["note_events"][event_id]["grace"].get("anchor_note_id")
                if anchor:
                    selected.add(anchor)
    sound_ids = {row["sounding_event_id"] for row in linked["sounding_events"]}
    linked["attack_events"] = [row for row in ir["attack_events"] if row["sounding_event_id"] in sound_ids]
    slots, lanes = [], defaultdict(list)
    # Preserve input occurrence order for simultaneous notes; IDs are never
    # sorted as a substitute for source order.
    ordered = sorted(enumerate(events), key=lambda pair: (f(pair[1]["global_onset_quarter"]), pair[0]))
    for _, event in ordered:
        event_id = event.get("note_id", event.get("rest_id"))
        if event_id not in selected:
            continue
        start = f(event["global_onset_quarter"])
        end = start + f(event["notated_duration_quarter"])
        overlap = None if end <= target[0] or start >= target[1] or start == end else {
            "start": q(max(start, target[0])), "end": q(min(end, target[1]))}
        slots.append({"event_id": event_id, "event_kind": "note" if "note_id" in event else "rest",
                      "relative_onset_quarter": q(start - target[0]),
                      "target_relation": _relation(start, end, target),
                      "context_relation": _relation(start, end, context),
                      "target_overlap": overlap, "core_event": deepcopy(event)})
        lanes[(event["part_id"], event["voice_id"])].append(event_id)
    source_ids = {row["core_event"]["source_ref_id"] for row in slots}
    projection = {
        "source_files": deepcopy(ir["source_files"]),
        "source_references": [deepcopy(row) for row in ir["source_references"] if row["source_ref_id"] in source_ids],
        # These are original document catalogs; references to unselected events
        # in voices remain full-document references, not fragment members.
        "parts": deepcopy(ir["parts"]), "staves": deepcopy(ir["staves"]),
        "voices": deepcopy(ir["voices"]), "measures": deepcopy(ir["measures"]),
        **deepcopy(linked), "parser_manifest": deepcopy(ir["parser_manifest"]),
    }
    return {"schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION, "producer_version": VERSION,
            "scope": deepcopy(scope), "slots": slots, "core_projection": projection,
            "raw_lanes": [{"part_id": part, "voice_id": voice, "event_ids": ids}
                          for (part, voice), ids in sorted(lanes.items())],
            "semantics": {"kind": "literal_notated_observation", "roles_assigned": False,
                          "chord_relative_degrees_assigned": False, "generation_ready": False,
                          "catalog_refs": "original_full_document_not_fragment",
                          "pitch_basis": "original_IR_not_independent_concert_pitch_certification"},
            "use_policy": {"research_only": True, "training_eligible": False, "gold_status": "not_established"}}


def observe(ir, scope):
    record = _payload(ir, scope)
    record["record_sha256"] = digest(record)
    record["record_id"] = "mpo_" + record["record_sha256"][:24]
    validate_observation(record)
    return record


def validate_observation(record, *, ir=None, scope=None):
    validators()[1].validate(record)
    payload = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    expected = digest(payload)
    if record["record_sha256"] != expected or record["record_id"] != "mpo_" + expected[:24]:
        raise ValueError("pattern_seal_mismatch")
    if scope is not None and record["scope"] != scope:
        raise ValueError("pattern_scope_mismatch")
    if ir is not None and payload != _payload(ir, record["scope"]):
        raise ValueError("pattern_reconstruction_mismatch")


def reconstruct(record):
    """Return original scoped notated events; NOT a complete MusicXML export."""
    validate_observation(record)
    return [deepcopy(slot["core_event"]) for slot in record["slots"]]
