"""Literal, source-clock guarded inputs and explicit caller harmony paths.

A seal establishes internal integrity, not original-source authority. Optional
fresh validation binds the view to its exact IR, frozen observation and audit.
No SOURCE records, harmony defaults, confidence or musical selections exist.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
import hashlib
import json

from jsonschema import Draft202012Validator

from .frozen_context_observation import validate_observation
from .musical_pattern_observation import digest, f, q, span_bounds, CORE_SCHEMA_PATH, COLLECTIONS
from .sounding_lineage_audit import audit_sounding_lineage, validate_audit

VERSION = "factor-musical-view-0.1.0"
PREFIX = "fmview_"
PATH_VERSION = "factor-musical-harmony-path-0.1.0"
PATH_PREFIX = "fmhp_"
POLICY = {"research_eligible": False, "training_eligible": False,
          "gold_eligible": False, "generation_ready": False}
BINDING_KEYS = {"score_id", "ir_document_id", "source_file_id", "ir_content_sha256", "source_files"}
VIEW_KEYS = {"version", "binding", "context_span", "target_span", "observation_ref", "audit_ref",
             "sounds", "points", "linked_sound_snapshots", "note_snapshots", "rest_snapshots",
             "measure_snapshots", "source_reference_snapshots", "tie_chain_snapshots", "attack_snapshots",
             "raw_lanes", "use_policy"}
PATH_KEYS = {"version", "binding", "view_ref", "context_span", "segments", "provenance", "use_policy"}
SEGMENT_KEYS = {"segment_id", "span", "root", "members", "status", "blockers"}
PROVENANCE_KEYS = {"kind", "engine_version", "source_document_sha256", "source_path", "pitch_basis", "status"}


def seal(body, prefix):
    if not isinstance(body, dict) or {"record_id", "record_sha256"}.intersection(body):
        raise ValueError("body_without_seal_fields_required")
    if not isinstance(prefix, str) or not prefix or not prefix.endswith("_"):
        raise ValueError("explicit_record_prefix_required")
    body = deepcopy(body)
    sha = digest(body)
    return {**body, "record_id": prefix + sha[:24], "record_sha256": sha}


def check(record, prefix):
    if not isinstance(record, dict) or not {"record_id", "record_sha256"} <= set(record):
        raise ValueError("sealed_record_required")
    body = {key: value for key, value in record.items() if key not in ("record_id", "record_sha256")}
    sha = digest(body)
    if record["record_sha256"] != sha or record["record_id"] != prefix + sha[:24]:
        raise ValueError("invalid_record_seal_or_namespace")
    return body


def ref(record):
    return {"record_id": record["record_id"], "record_sha256": record["record_sha256"]}


def _closed(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("closed_contract_required:" + name)


def _string(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError("nonempty_string_required:" + name)


def _index(rows, key):
    if not isinstance(rows, list):
        raise ValueError("snapshot_list_required:" + key)
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("snapshot_object_required:" + key)
        identity = row.get(key)
        _string(identity, key)
        if identity in result:
            raise ValueError("duplicate_snapshot_id:" + key)
        result[identity] = row
    return result


def _reference(value, prefix):
    _closed(value, {"record_id", "record_sha256"}, "reference")
    sha = value["record_sha256"]
    if (not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha)
            or value["record_id"] != prefix + sha[:24]):
        raise ValueError("invalid_reference_or_namespace")


def _schema_bytes():
    return CORE_SCHEMA_PATH.read_bytes()


@lru_cache(maxsize=4)
def _definitions(schema_bytes):
    schema = json.loads(schema_bytes)
    Draft202012Validator.check_schema(schema)
    return schema["$defs"]


@lru_cache(maxsize=64)
def _literal_validator(name, schema_bytes):
    return Draft202012Validator({"$defs": _definitions(schema_bytes), "$ref": "#/$defs/" + name})


def _literal(rows, id_key, schema, schema_bytes=None):
    schema_bytes = _schema_bytes() if schema_bytes is None else schema_bytes
    result = _index(rows, id_key)
    for row in rows:
        _literal_validator(schema, schema_bytes).validate(row)
        if schema in ("note", "rest"):
            base = set(_definitions(schema_bytes)["eventBase"]["properties"])
            extension = set(_definitions(schema_bytes)[schema]["allOf"][1]["properties"])
            if set(row) - base - extension:
                raise ValueError("unknown_literal_event_fields")
    return result


def _binding(value, schema_bytes=None):
    _closed(value, BINDING_KEYS, "binding")
    for key in ("score_id", "ir_document_id", "source_file_id"):
        _string(value[key], key)
    sha = value["ir_content_sha256"]
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("full_IR_digest_required")
    files = _literal(value["source_files"], "source_file_id", "sourceFile", schema_bytes)
    if not files or value["source_file_id"] not in files:
        raise ValueError("score_source_file_binding_required")


def _bounds(span, *, point=False):
    _closed(span, {"start", "end"}, "span")
    start, end = f(span["start"]), f(span["end"])
    if start < 0 or end < start or (not point and start == end):
        raise ValueError("invalid_literal_span")
    return start, end


def clipped(span, context):
    a, b = _bounds(span, point=True)
    c, d = _bounds(context)
    return {"start": q(max(a, c)), "end": q(min(b, d))} if max(a, c) < min(b, d) else None


def pitch_key(pitch, octave=False):
    if (type(octave) is not bool or not isinstance(pitch, dict)
            or not isinstance(pitch.get("step"), str) or pitch["step"] not in set("ABCDEFG")):
        raise ValueError("explicit_written_pitch_required")
    alter = f(pitch["alter"])
    if octave:
        if type(pitch.get("octave")) is not int:
            raise ValueError("explicit_pitch_octave_required")
        return pitch["step"], alter, pitch["octave"]
    return pitch["step"], alter


def _relation(a, b, bounds):
    c, d = bounds
    return ("point_inside" if c <= a < d else "linked_context_only") if a == b else (
        "overlap" if a < d and b > c else "linked_context_only")


def _selected_literal(ir, scope):
    """Minimal exact closure replay; never full-Core validation per context."""
    indices = {name: _index(ir[name], key) for name, key in COLLECTIONS.items()}
    context, target = _bounds(scope["context_span"]), _bounds(scope["target_span"])
    events = [*ir["note_events"], *ir["rest_events"]]
    selected = {event.get("note_id", event.get("rest_id")) for event in events
                if _relation(f(event["global_onset_quarter"]),
                             f(event["global_onset_quarter"]) + f(event["notated_duration_quarter"]), context)
                != "linked_context_only"}
    linked = {}
    previous = None
    while previous != selected:
        previous = set(selected)
        for name in ("sounding_events", "tie_chains", "chord_onset_groups"):
            linked[name] = [row for row in ir[name] if selected.intersection(row.get("source_note_ids", row.get("note_ids")))]
            for row in linked[name]:
                ids = row.get("source_note_ids", row.get("note_ids"))
                if any(nid not in indices["note_events"] for nid in ids):
                    raise ValueError("missing_linked_source_note")
                selected.update(ids)
        for nid in list(selected):
            if nid in indices["note_events"]:
                anchor = indices["note_events"][nid]["grace"].get("anchor_note_id")
                if anchor:
                    if anchor not in indices["note_events"]:
                        raise ValueError("missing_grace_anchor")
                    selected.add(anchor)
    sound_ids = {row["sounding_event_id"] for row in linked["sounding_events"]}
    linked["attack_events"] = [row for row in ir["attack_events"] if row["sounding_event_id"] in sound_ids]
    slots, lanes = [], defaultdict(list)
    ordered = sorted(enumerate(events), key=lambda item: (f(item[1]["global_onset_quarter"]), item[0]))
    for _, event in ordered:
        eid = event.get("note_id", event.get("rest_id"))
        if eid not in selected:
            continue
        a = f(event["global_onset_quarter"])
        b = a + f(event["notated_duration_quarter"])
        slots.append({"event_id": eid, "event_kind": "note" if "note_id" in event else "rest",
                      "relative_onset_quarter": q(a - target[0]), "target_relation": _relation(a, b, target),
                      "context_relation": _relation(a, b, context),
                      "target_overlap": clipped({"start": q(a), "end": q(b)}, scope["target_span"]),
                      "core_event": event})
        lanes[(event["part_id"], event["voice_id"])].append(eid)
    source_ids = {row["core_event"]["source_ref_id"] for row in slots}
    if any(sid not in indices["source_references"] for sid in source_ids):
        raise ValueError("missing_selected_source_reference")
    projection = {"source_files": ir["source_files"],
                  "source_references": [r for r in ir["source_references"] if r["source_ref_id"] in source_ids],
                  **{name: ir[name] for name in ("parts", "staves", "voices", "measures", "parser_manifest")}, **linked}
    raw_lanes = [{"part_id": part, "voice_id": voice, "event_ids": ids} for (part, voice), ids in sorted(lanes.items())]
    return slots, projection, raw_lanes


def _payload(binding, context, target, observation_ref, audit_ref, snapshots, raw_lanes, *, schema_bytes=None):
    schema_bytes = _schema_bytes() if schema_bytes is None else schema_bytes
    _binding(binding, schema_bytes)
    c, d = _bounds(context)
    a, b = _bounds(target)
    if not c <= a < b <= d:
        raise ValueError("target_outside_context")
    _reference(observation_ref, "mfco_")
    _reference(audit_ref, "msla_")
    notes = _literal(snapshots["note_snapshots"], "note_id", "note", schema_bytes)
    rests = _literal(snapshots["rest_snapshots"], "rest_id", "rest", schema_bytes)
    sounds = _literal(snapshots["linked_sound_snapshots"], "sounding_event_id", "sounding", schema_bytes)
    ties = _literal(snapshots["tie_chain_snapshots"], "tie_chain_id", "tieChain", schema_bytes)
    attacks = _literal(snapshots["attack_snapshots"], "attack_event_id", "attack", schema_bytes)
    measures = _literal(snapshots["measure_snapshots"], "measure_id", "measure", schema_bytes)
    sources = _literal(snapshots["source_reference_snapshots"], "source_ref_id", "sourceRef", schema_bytes)
    files = {row["source_file_id"] for row in binding["source_files"]}
    all_ids = [*notes, *rests, *sounds, *ties, *attacks, *measures, *sources]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("snapshot_ID_namespace_collision")
    for event in [*notes.values(), *rests.values()]:
        if (event["score_id"] != binding["score_id"] or event["measure_id"] not in measures
                or event["source_ref_id"] not in sources or sources[event["source_ref_id"]]["source_file_id"] not in files):
            raise ValueError("missing_or_foreign_literal_reference")
        if f(event["global_onset_quarter"]) != f(measures[event["measure_id"]]["global_start_quarter"]) + f(event["onset_in_measure"]):
            raise ValueError("literal_measure_clock_mismatch")
        if f(event["global_onset_quarter"]) < 0 or f(event["notated_duration_quarter"]) < 0:
            raise ValueError("negative_literal_clock")
        if "note_id" in event and event["grace"].get("anchor_note_id") not in (None, *notes):
            raise ValueError("missing_literal_grace_anchor")
    for tid, tie in ties.items():
        if len(tie["source_note_ids"]) != len(set(tie["source_note_ids"])) or not set(tie["source_note_ids"]) <= set(notes):
            raise ValueError("missing_or_duplicate_tie_source_note")
        _bounds(tie["span"])
    for sid, sound in sounds.items():
        if len(sound["source_note_ids"]) != len(set(sound["source_note_ids"])) or not set(sound["source_note_ids"]) <= set(notes):
            raise ValueError("missing_or_duplicate_sound_source_note")
        if sound["attack_note_id"] not in sound["source_note_ids"]:
            raise ValueError("missing_literal_sound_attack")
        tid = sound.get("tie_chain_id")
        if tid is not None and (tid not in ties or any(sound[key] != ties[tid][key] for key in ("source_note_ids", "attack_note_id", "span"))):
            raise ValueError("missing_or_mismatched_literal_tie")
        _bounds(sound["span"], point=True)
    for attack in attacks.values():
        if (attack["note_id"] not in notes or attack["sounding_event_id"] not in sounds
                or attack["note_id"] != sounds[attack["sounding_event_id"]]["attack_note_id"]
                or attack["global_onset_quarter"] != notes[attack["note_id"]]["global_onset_quarter"]):
            raise ValueError("missing_or_mismatched_literal_attack")
    if {r["sounding_event_id"] for r in attacks.values()} != set(sounds):
        raise ValueError("incomplete_literal_attack_inventory")
    if len(attacks) != len(sounds):
        raise ValueError("duplicate_literal_sound_attack")
    duration = max([d, *[f(s["span"]["end"]) for s in sounds.values()],
                    *[f(n["global_onset_quarter"]) + f(n["notated_duration_quarter"]) for n in notes.values()]])
    snapshot_ir = {"ir_document_id": binding["ir_document_id"],
                   "score": {"score_id": binding["score_id"], "duration_quarters": q(duration)},
                   "source_files": binding["source_files"], "note_events": list(notes.values()),
                   "sounding_events": list(sounds.values())}
    clock = audit_sounding_lineage(snapshot_ir, sound_ids=list(sounds), context_span=context)
    clock_rows = {r["sounding_event_ref"]: r for r in clock["sounding_audits"]}
    active, points = [], []
    for sid, sound in sounds.items():
        owners = {(notes[nid]["part_id"], notes[nid]["voice_id"]) for nid in sound["source_note_ids"]}
        if len(owners) != 1:
            raise ValueError("ambiguous_sound_raw_lane_ownership")
        lo, hi = _bounds(sound["span"], point=True)
        observed = clipped(sound["span"], context)
        is_point = lo == hi and c <= lo < d
        if observed is None and not is_point:
            continue
        facts = clock_rows[sid]
        written_key = pitch_key(sound["pitch"], octave=True)
        pitch_consistent = all(pitch_key(notes[nid]["written_pitch"], octave=True) == written_key
                               for nid in sound["source_note_ids"])
        pitch_consistent = pitch_consistent and pitch_key(notes[sound["attack_note_id"]]["written_pitch"], octave=True) == written_key
        diagnostics = list(facts["diagnostics"])
        if not pitch_consistent:
            diagnostics.append("source_written_pitch_mismatch")
        row = {"sound_id": sid, "source_note_ids": deepcopy(sound["source_note_ids"]),
               "attack_note_id": sound["attack_note_id"], "lane": list(next(iter(owners))),
               "pitch": deepcopy(sound["pitch"]), "span": deepcopy(sound["span"]),
               "observed_span": deepcopy(sound["span"]) if is_point else observed,
               "source_clock_passed": facts["source_clock_consistency_passed"],
               "source_pitch_consistency_passed": pitch_consistent,
               "source_diagnostics": sorted(set(diagnostics))}
        (points if is_point else active).append(row)
    events = [*notes.values(), *rests.values()]
    lane_ids = defaultdict(list)
    for _, event in sorted(enumerate(events), key=lambda item: (f(item[1]["global_onset_quarter"]), item[0])):
        lane_ids[(event["part_id"], event["voice_id"])].append(event.get("note_id", event.get("rest_id")))
    expected_lanes = [{"part_id": p, "voice_id": v, "event_ids": ids} for (p, v), ids in sorted(lane_ids.items())]
    if raw_lanes != expected_lanes:
        raise ValueError("raw_lane_snapshot_denominator_mismatch")
    return {"version": VERSION, "binding": deepcopy(binding), "context_span": deepcopy(context),
            "target_span": deepcopy(target), "observation_ref": deepcopy(observation_ref), "audit_ref": deepcopy(audit_ref),
            "sounds": active, "points": points, **deepcopy(snapshots), "raw_lanes": deepcopy(raw_lanes),
            "use_policy": deepcopy(POLICY)}


def prepare(ir, mfco, lineage_audit):
    validate_observation(mfco)  # Schema/seal only; no full-Core validator here.
    scope = mfco["scope"]
    binding = {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
               "source_file_id": ir["score"]["source_file_id"], "ir_content_sha256": digest(ir),
               "source_files": deepcopy(ir["source_files"])}
    if {k: scope[k] for k in ("score_id", "ir_document_id", "ir_content_sha256", "source_files")} != {k: binding[k] for k in scope if k in binding}:
        raise ValueError("stale_or_foreign_observation_IR_binding")
    if _bounds(scope["context_span"])[1] > f(ir["score"]["duration_quarters"]):
        raise ValueError("context_outside_IR_duration")
    slots, projection, lanes = _selected_literal(ir, scope)
    if mfco["slots"] != slots or mfco["core_projection"] != projection or mfco["raw_lanes"] != lanes:
        raise ValueError("literal_observation_IR_snapshot_mismatch")
    sound_ids = [row["sounding_event_id"] for row in projection["sounding_events"]]
    validate_audit(lineage_audit, ir=ir, sound_ids=sound_ids, context_span=scope["context_span"])
    snapshots = {"note_snapshots": [r["core_event"] for r in slots if r["event_kind"] == "note"],
                 "rest_snapshots": [r["core_event"] for r in slots if r["event_kind"] == "rest"],
                 "linked_sound_snapshots": projection["sounding_events"], "measure_snapshots": projection["measures"],
                 "source_reference_snapshots": projection["source_references"],
                 "tie_chain_snapshots": projection["tie_chains"], "attack_snapshots": projection["attack_events"]}
    body = _payload(binding, scope["context_span"], scope["target_span"], ref(mfco), ref(lineage_audit), snapshots, lanes)
    return seal(body, PREFIX)


@lru_cache(maxsize=32)
def _validate_intrinsic_cached(serialized_record, schema_sha256, schema_bytes):
    """Positive-only immutable content memo; never trust a caller's SHA field."""
    if hashlib.sha256(schema_bytes).hexdigest() != schema_sha256:
        raise ValueError("schema_snapshot_hash_mismatch")
    view = json.loads(serialized_record)
    body = check(view, PREFIX)
    _closed(body, VIEW_KEYS, "view")
    if body["version"] != VERSION or body["use_policy"] != POLICY or any(type(v) is not bool for v in body["use_policy"].values()):
        raise ValueError("unsupported_or_promoting_view")
    snapshots = {k: body[k] for k in VIEW_KEYS if k.endswith("_snapshots")}
    rebuilt = _payload(body["binding"], body["context_span"], body["target_span"],
                       body["observation_ref"], body["audit_ref"], snapshots, body["raw_lanes"], schema_bytes=schema_bytes)
    if body != rebuilt:
        raise ValueError("view_payload_reconstruction_mismatch")
    return True


def validate_view(view, *, ir=None, observation=None, audit=None):
    # Snapshot actual content before memo lookup. Values/seals/flags mutated by
    # the caller produce a new key; failed validation is never cached.
    serialized = json.dumps(view, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    schema_bytes = _schema_bytes()
    _validate_intrinsic_cached(serialized, hashlib.sha256(schema_bytes).hexdigest(), schema_bytes)
    supplied = [ir is not None, observation is not None, audit is not None]
    if any(supplied) and not all(supplied):
        raise ValueError("all_exact_view_replay_inputs_required")
    if all(supplied) and json.loads(serialized) != prepare(ir, observation, audit):
        raise ValueError("view_exact_replay_mismatch")
    return True


def _path(path):
    body = check(path, PATH_PREFIX)
    _closed(body, PATH_KEYS, "path")
    _binding(body["binding"])
    _reference(body["view_ref"], PREFIX)
    if body["version"] != PATH_VERSION or body["use_policy"] != POLICY or any(type(v) is not bool for v in body["use_policy"].values()):
        raise ValueError("unsupported_or_promoting_path")
    provenance = body["provenance"]
    _closed(provenance, PROVENANCE_KEYS, "caller_hypothesis_provenance")
    _string(provenance["engine_version"], "engine_version")
    if (provenance["kind"] != "caller_hypothesis" or provenance["source_document_sha256"] is not None
            or provenance["source_path"] is not None or provenance["pitch_basis"] != "written_IR_not_concert_certified"
            or provenance["status"] != "hypothesis_not_gold"):
        raise ValueError("caller_hypothesis_without_SOURCE_provenance_required")
    lo, end = _bounds(body["context_span"])
    if not isinstance(body["segments"], list) or not body["segments"]:
        raise ValueError("complete_context_partition_required")
    segment_ids = set()
    for segment in body["segments"]:
        _closed(segment, SEGMENT_KEYS, "segment")
        _string(segment["segment_id"], "segment_id")
        if segment["segment_id"] in segment_ids:
            raise ValueError("duplicate_path_segment_id")
        segment_ids.add(segment["segment_id"])
        start, finish = _bounds(segment["span"])
        if start != lo or finish > end:
            raise ValueError("complete_ordered_context_partition_required")
        lo = finish
        if segment["root"] is not None:
            _closed(segment["root"], {"step", "alter"}, "root")
            pitch_key(segment["root"])
        if not isinstance(segment["members"], list):
            raise ValueError("explicit_members_required")
        keys = []
        for member in segment["members"]:
            _closed(member, {"step", "alter"}, "member")
            keys.append(pitch_key(member))
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate_spelled_pitch_member")
        blockers = segment["blockers"]
        if not isinstance(blockers, list) or any(not isinstance(x, str) or not x for x in blockers) or len(blockers) != len(set(blockers)):
            raise ValueError("explicit_unique_blockers_required")
        if ((segment["status"] == "usable" and (not keys or blockers))
                or (segment["status"] == "blocked" and not blockers)
                or segment["status"] not in ("usable", "blocked")):
            raise ValueError("usable_members_or_blocked_reasons_required")
    if lo != end:
        raise ValueError("complete_ordered_context_partition_required")
    return body


def make_path(view, segments, provenance):
    validate_view(view)
    body = {"version": PATH_VERSION, "binding": deepcopy(view["binding"]), "view_ref": ref(view),
            "context_span": deepcopy(view["context_span"]), "segments": deepcopy(segments),
            "provenance": deepcopy(provenance), "use_policy": deepcopy(POLICY)}
    path = seal(body, PATH_PREFIX)
    validate_path(view, path)
    return path


def validate_path(view, path):
    validate_view(view)
    body = _path(path)
    if body["view_ref"] != ref(view) or body["binding"] != view["binding"] or body["context_span"] != view["context_span"]:
        raise ValueError("foreign_view_or_IR_path_binding")
    return True


def _time(value):
    if isinstance(value, dict):
        return f(value)
    if type(value) is int or isinstance(value, Fraction):
        return Fraction(value)
    raise ValueError("exact_rational_time_required")


def segment_at(path, time):
    body = _path(path)
    when = _time(time)
    return next((deepcopy(row) for row in body["segments"]
                 if f(row["span"]["start"]) <= when < f(row["span"]["end"])), None)


def membership(path, pitch, span):
    body = _path(path)
    start, end = _bounds(span)
    lo, hi = _bounds(body["context_span"])
    if start < lo or end > hi:
        return "unknown"
    identity = pitch_key(pitch)
    values = set()
    for segment in body["segments"]:
        if clipped(segment["span"], span) is None:
            continue
        if segment["status"] != "usable":
            return "unknown"
        values.add(identity in {pitch_key(member) for member in segment["members"]})
    return "member" if values == {True} else "nonmember" if values == {False} else "unknown"
