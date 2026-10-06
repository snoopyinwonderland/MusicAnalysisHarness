"""All-lane literal geometry and harmony-conditioned role evidence.

Neither a Pedal source tag nor a chord label selects a musical role.  Separate
assumption tracks are evaluated on the same immutable notes.  Candidate shapes
are not semantic voices, confirmed pedals, accompaniment, or generation plans.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .musical_pattern_observation import digest, f, q, span_bounds, validate_observation
from .musical_harmony_assumption import validate_track

VERSION = "musical-role-evidence-0.1.0"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs/harmony/schemas/musical_role_evidence.schema.json"
LETTERS = "CDEFGAB"


def ref(record):
    return {"record_id": record["record_id"], "record_sha256": record["record_sha256"]}


def span(start, end):
    return {"start": q(start), "end": q(end)}


def intersection(left, right):
    a, b = max(left[0], right[0]), min(left[1], right[1])
    return None if a >= b else span(a, b)


def pitch_key(pitch, octave=False):
    key = (pitch["step"], f(pitch["alter"]))
    return key + (pitch["octave"],) if octave else key


def lane_key(row):
    return row["part_id"], row["voice_id"]


def lane(key):
    return {"part_id": key[0], "voice_id": key[1]}


def degree(root, pitch):
    return None if root is None else (LETTERS.index(pitch["step"]) - LETTERS.index(root["step"])) % 7 + 1


def _geometry(observation):
    context = span_bounds(observation["scope"]["context_span"])
    target = span_bounds(observation["scope"]["target_span"])
    notes = {s["event_id"]: s["core_event"] for s in observation["slots"] if s["event_kind"] == "note"}
    attacks = defaultdict(list)
    covered = defaultdict(list)
    for event in observation["core_projection"]["attack_events"]:
        attacks[event["sounding_event_id"]].append(event)
    sounds, points, rests = [], [], []
    onsets = defaultdict(list)
    for sound in observation["core_projection"]["sounding_events"]:
        ns = [notes[nid] for nid in sound["source_note_ids"]]
        attack = notes[sound["attack_note_id"]]
        a, b = f(sound["span"]["start"]), f(sound["span"]["end"])
        if b - a != f(sound["sounding_duration"]):
            raise ValueError("sounding_duration_span_mismatch")
        attack_refs = attacks[sound["sounding_event_id"]]
        if len(attack_refs) != 1 or attack_refs[0]["note_id"] != sound["attack_note_id"] or f(attack_refs[0]["global_onset_quarter"]) != a:
            raise ValueError("sounding_attack_reference_mismatch")
        ordered_notes = sorted(ns, key=lambda n: f(n["global_onset_quarter"]))
        cursor = a
        for n in ordered_notes:
            if f(n["global_onset_quarter"]) != cursor:
                raise ValueError("noncontiguous_sounding_source_notes")
            cursor += f(n["notated_duration_quarter"])
            covered[n["note_id"]].append(sound["sounding_event_id"])
        if cursor != b:
            raise ValueError("sounding_source_note_duration_mismatch")
        keys = {lane_key(n) for n in ns}
        if len(keys) != 1 or any(pitch_key(n["written_pitch"], True) != pitch_key(attack["written_pitch"], True) for n in ns):
            raise ValueError("sounding_lane_or_pitch_inconsistent")
        # Sounding timing is not reconstructed from an arbitrary sorted note.
        if a != f(attack["global_onset_quarter"]):
            raise ValueError("sounding_attack_onset_mismatch")
        key = lane_key(attack)
        if a == b:
            if context[0] <= a < context[1]:
                points.append({"note_ids": list(sound["source_note_ids"]), "sounding_event_id": sound["sounding_event_id"],
                               "lane": lane(key), "onset": q(a), "pitch": deepcopy(attack["written_pitch"])})
            continue
        observed = intersection((a, b), context)
        if observed is None:
            continue
        row = {"sounding_event_id": sound["sounding_event_id"], "source_note_ids": list(sound["source_note_ids"]),
               "attack_note_id": sound["attack_note_id"], "lane": lane(key),
               "pitch": deepcopy(attack["written_pitch"]), "original_span": deepcopy(sound["span"]),
               "observed_span": observed, "target_overlap": intersection((a, b), target),
               "attack_in_context": context[0] <= a < context[1], "attack_in_target": target[0] <= a < target[1],
               "tie_continuation_note_ids": [n["note_id"] for n in ns if n["note_id"] != sound["attack_note_id"]]}
        sounds.append(row)
        if row["attack_in_context"]:
            onsets[(key, a)].append(row)
    for slot in observation["slots"]:
        if slot["event_kind"] == "note":
            if slot["context_relation"] != "linked_context_only" and len(covered[slot["event_id"]]) != 1:
                raise ValueError("missing_or_duplicate_note_sounding_membership")
            continue
        if slot["event_kind"] != "rest":
            continue
        event = slot["core_event"]
        a = f(event["global_onset_quarter"])
        b = a + f(event["notated_duration_quarter"])
        if intersection((a, b), context) is not None:
            rests.append({"event_id": slot["event_id"], "lane": lane(lane_key(event)), "span": span(a, b)})

    # Aggregates retain all ambiguous simultaneous unisons. No arbitrary branch
    # is chosen, and no different raw lane / enharmonic / octave is connected.
    buckets = defaultdict(list)
    for sound in sounds:
        buckets[(lane_key(sound["lane"]), pitch_key(sound["pitch"], True))].append(sound)
    episodes = []
    for (key, _pitch), rows in sorted(buckets.items()):
        ordered = sorted(rows, key=lambda row: (f(row["original_span"]["start"]), f(row["original_span"]["end"]), row["sounding_event_id"]))
        components = []
        for row in ordered:
            a, b = span_bounds(row["original_span"])
            if not components or a > components[-1][0]:
                components.append([b, [row]])
            else:
                components[-1][0] = max(components[-1][0], b)
                components[-1][1].append(row)
        for _end, component in components:
            a = min(f(row["original_span"]["start"]) for row in component)
            b = max(f(row["original_span"]["end"]) for row in component)
            overlap = any(f(x["original_span"]["start"]) < f(y["original_span"]["end"])
                          and f(y["original_span"]["start"]) < f(x["original_span"]["end"])
                          for i, x in enumerate(component) for y in component[i + 1:])
            ids = [row["sounding_event_id"] for row in component]
            eid = "episode_" + digest({"lane": lane(key), "sounds": ids})[:24]
            episodes.append({"episode_id": eid, "lane": lane(key), "pitch": deepcopy(component[0]["pitch"]),
                             "original_span": span(a, b), "observed_span": intersection((a, b), context),
                             "target_overlap": intersection((a, b), target), "sounding_event_ids": ids,
                             "source_note_ids": [nid for row in component for nid in row["source_note_ids"]],
                             "attack_note_ids_context": [row["attack_note_id"] for row in component if row["attack_in_context"]],
                             "tie_continuation_note_ids": [nid for row in component for nid in row["tie_continuation_note_ids"]],
                             "mode": "overlapping_same_pitch" if overlap else "single_sound" if len(component) == 1 else "touching_reattacks",
                             "context_clipped_start": a < context[0], "context_clipped_end": b > context[1],
                             "overlap_ambiguous": overlap})
    groups = [{"lane": lane(key), "onset": q(a), "note_ids": [row["attack_note_id"] for row in rows],
               "sounding_event_ids": [row["sounding_event_id"] for row in rows]}
              for (key, a), rows in sorted(onsets.items())]
    return {"sounds": sounds, "grace_points": points, "pitch_episodes": episodes, "onset_groups": groups,
            "rests": rests, "limits": [
                "Raw part/voice lanes are not independently established musical voices.",
                "Connected exact-spelled exact-octave sounds: no rest bridging or enharmonic/octave substitution.",
                "Intervals are original IR notated/sounding geometry, not certified performed timing.",
                "Grace points have no inferred performed duration; original onset outside target is never reattacked.",
                "No source prose, Pedal pitch token, instrument name or lowest-pitch rule selects a lane."]}


def _pedal_profile(episode, track):
    a, b = span_bounds(episode["observed_span"])
    segments = [s for s in track["segments"] if intersection(span_bounds(s["span"]), (a, b))]
    points = sorted({a, b} | {f(s["span"][edge]) for s in segments for edge in ("start", "end") if a < f(s["span"][edge]) < b})
    cells, shapes = [], set()
    key = pitch_key(episode["pitch"])
    for left, right in zip(points, points[1:]):
        segment = next((s for s in segments if f(s["span"]["start"]) <= left < f(s["span"]["end"])), None)
        usable = segment is not None and segment["status"] == "usable"
        members = {pitch_key(p) for p in segment["members"]} if usable else set()
        if usable:
            shapes.add(tuple(sorted(members)))
        cells.append({"span": span(left, right), "segment_id": None if segment is None else segment["segment_id"],
                      "label": None if segment is None else segment["label"],
                      "membership": "unknown" if not usable else "member" if key in members else "nonmember",
                      "degree": degree(segment["root"], episode["pitch"]) if usable and key in members else None})
    states = [cell["membership"] for cell in cells]
    blockers = []
    if "unknown" in states:
        blockers.append("incomplete_or_blocked_harmony_coverage")
    for segment in segments:
        for reason in segment["blockers"]:
            if reason not in blockers:
                blockers.append(reason)
    if episode["overlap_ambiguous"]:
        blockers.append("ambiguous_same_pitch_overlap")
    if episode["context_clipped_start"] or episode["context_clipped_end"]:
        blockers.append("full_pitch_episode_not_in_context")
    shape = len(shapes) >= 2 and "nonmember" in states
    anchored = shape and states[0] == states[-1] == "member" and not blockers
    return {"episode_id": episode["episode_id"], "cells": cells,
            "status": "anchored_pedal_shape" if anchored else "unanchored_pedal_shape" if shape else "no_pedal_shape",
            "blockers": blockers, "alternatives": ["pedal", "suspension_or_other_nonchord_relation", "different_harmony_assumption"],
            "pedal_confirmed": False}


def _sequential_profiles(geometry, track, context):
    sounds = {row["sounding_event_id"]: row for row in geometry["sounds"]}
    lanes = sorted({lane_key(g["lane"]) for g in geometry["onset_groups"]})
    rows = []
    for segment in track["segments"]:
        observed = intersection(span_bounds(segment["span"]), context)
        if observed is None:
            continue
        a, b = span_bounds(observed)
        usable = segment["status"] == "usable"
        members = {pitch_key(p) for p in segment["members"]} if usable else set()
        for key in lanes:
            groups, seen = [], set()
            for group in geometry["onset_groups"]:
                if lane_key(group["lane"]) != key or not a <= f(group["onset"]) < b:
                    continue
                group = deepcopy(group)
                group.pop("lane")
                group.update(member_note_ids=[], nonmember_note_ids=[], unknown_note_ids=[], degree_by_note={})
                for nid, sid in zip(group["note_ids"], group["sounding_event_ids"]):
                    pitch = sounds[sid]["pitch"]
                    is_member = usable and pitch_key(pitch) in members
                    if is_member:
                        seen.add(pitch_key(pitch))
                    group["unknown_note_ids" if not usable else "member_note_ids" if is_member else "nonmember_note_ids"].append(nid)
                    group["degree_by_note"][nid] = degree(segment["root"], pitch) if is_member else None
                groups.append(group)
            if not groups:
                continue
            blockers = []
            if not usable:
                blockers.append("blocked_harmony_assumption")
                blockers.extend(reason for reason in segment["blockers"] if reason not in blockers)
            if any(g["nonmember_note_ids"] or g["unknown_note_ids"] for g in groups):
                blockers.append("nonmember_or_unknown_attacks_present")
            if any(len(g["note_ids"]) != 1 for g in groups):
                blockers.append("polyphonic_or_simultaneous_onset_groups")
            if len(groups) < 3:
                blockers.append("fewer_than_three_distinct_onsets")
            if len(seen) < 3:
                blockers.append("fewer_than_three_distinct_spelled_members")
            rows.append({"lane": lane(key), "segment_id": segment["segment_id"], "span": observed,
                         "onset_groups": groups, "missing_members": [deepcopy(p) for p in segment["members"] if pitch_key(p) not in seen] if usable else None,
                         "membership_scope": "attacks_only",
                         "onset_deltas_quarter": [q(f(y["onset"]) - f(x["onset"])) for x, y in zip(groups, groups[1:])],
                         "status": "insufficient_shape" if blockers else "broken_chord_shape", "blockers": blockers,
                         "alternatives": ["arpeggio", "chord_tone_melody", "other_texture"], "arpeggio_confirmed": False})
    return rows


def _payload(ir, observation, tracks):
    validate_observation(observation, ir=ir)
    scope = observation["scope"]
    binding = {key: scope[key] for key in ("score_id", "ir_document_id", "ir_content_sha256", "source_files")}
    seen = set()
    for track in tracks:
        validate_track(track, ir=ir)
        if track["binding"] != binding:
            raise ValueError("foreign_harmony_track")
        if track["record_id"] in seen:
            raise ValueError("duplicate_harmony_track")
        seen.add(track["record_id"])
    geometry = _geometry(observation)
    conditional = [{"assumption_ref": ref(track),
                    "pedal_profiles": [_pedal_profile(e, track) for e in geometry["pitch_episodes"]],
                    "sequential_profiles": _sequential_profiles(geometry, track, span_bounds(scope["context_span"]))}
                   for track in tracks]
    return {"schema_name": "musicanote-musical-role-evidence", "schema_version": "0.1.0", "producer_version": VERSION,
            "observation_ref": ref(observation), "scope": deepcopy(scope), "literal": geometry, "conditional": conditional,
            "semantics": {"roles_validated": False, "melody_or_bass_selected": False, "chord_assumption_selected": False, "generation_ready": False},
            "use_policy": {"research_only": True, "training_eligible": False, "gold_status": "not_established"}}


def analyze(ir, observation, tracks=()):
    record = _payload(ir, observation, tracks)
    record["record_sha256"] = digest(record)
    record["record_id"] = "mre_" + record["record_sha256"][:24]
    validate_evidence(record)
    return record


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    from .musical_pattern_observation import CORE_SCHEMA_PATH, SCHEMA_PATH as pattern_schema
    registry = Registry()
    for path in (CORE_SCHEMA_PATH, pattern_schema):
        resource = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(resource["$id"], Resource.from_contents(resource))
    return Draft202012Validator(schema, registry=registry)


def validate_evidence(record, *, ir=None, observation=None, tracks=None):
    _validator().validate(record)
    payload = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    expected = digest(payload)
    if record["record_sha256"] != expected or record["record_id"] != "mre_" + expected[:24]:
        raise ValueError("role_evidence_seal_mismatch")
    if ir is not None or observation is not None or tracks is not None:
        if ir is None or observation is None or tracks is None:
            raise ValueError("role_evidence_replay_requires_all_inputs")
        if payload != _payload(ir, observation, tracks):
            raise ValueError("role_evidence_replay_mismatch")
