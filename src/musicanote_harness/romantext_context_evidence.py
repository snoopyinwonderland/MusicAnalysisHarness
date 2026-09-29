"""Boundary and voice-leading evidence around imported RomanText spans.

This is source-conditioned diagnostic evidence.  It describes what happens
across a labelled boundary without changing the label or its support band.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any


VERSION = "romantext-context-evidence-0.1.0"


def _f(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _start(annotation: dict[str, Any]) -> Fraction:
    return _f(annotation["target"]["span"]["start"])


def _voice_for(sound: dict[str, Any], notes: dict[str, dict[str, Any]]) -> str | None:
    note = notes.get(sound.get("attack_note_id"))
    return None if note is None else note.get("voice_id")


def _bass_at(
    at: Fraction, sounds: dict[str, dict[str, Any]], sound_ids: list[str]
) -> dict[str, Any] | None:
    active = [
        sounds[sound_id] for sound_id in sound_ids if sound_id in sounds
        and _f(sounds[sound_id]["span"]["start"]) <= at < _f(sounds[sound_id]["span"]["end"])
    ]
    return min(active, key=lambda row: int(row["pitch"]["midi_pitch"]), default=None)


def evaluate_contextual_evidence(
    package: dict[str, Any], source_evidence: dict[str, Any]
) -> dict[str, Any]:
    ir = package["ir"]
    annotations = {
        row["annotation_id"]: row for row in package["annotations"] if row.get("target") and "span" in row["target"]
    }
    alignments = {
        row["annotation_id"]: row for row in package["alignments"] if row["mapping_status"] == "exact"
    }
    evidence = {row["annotation_id"]: row for row in source_evidence["records"]}
    sounds = {row["sounding_event_id"]: row for row in ir["sounding_events"]}
    notes = {row["note_id"]: row for row in ir["note_events"]}
    ordered = sorted(
        (row for annotation_id, row in annotations.items() if annotation_id in alignments),
        key=lambda row: (_start(row), row["annotation_id"]),
    )
    records: list[dict[str, Any]] = []
    for index, current in enumerate(ordered):
        annotation_id = current["annotation_id"]
        current_evidence = evidence.get(annotation_id, {})
        base = {
            "annotation_id": annotation_id,
            "raw_label": current["raw_label"],
            "previous_annotation_id": ordered[index - 1]["annotation_id"] if index else None,
            "previous_raw_label": ordered[index - 1]["raw_label"] if index else None,
            "next_annotation_id": ordered[index + 1]["annotation_id"] if index + 1 < len(ordered) else None,
            "next_raw_label": ordered[index + 1]["raw_label"] if index + 1 < len(ordered) else None,
        }
        if index + 1 >= len(ordered):
            records.append({**base, "status": "no_next_context", "diagnostics": ["last_exact_annotation"]})
            continue
        following = ordered[index + 1]
        next_id = following["annotation_id"]
        next_evidence = evidence.get(next_id, {})
        if current_evidence.get("status") != "scored" or next_evidence.get("status") != "scored":
            records.append({**base, "status": "unscorable", "diagnostics": ["neighbor_surface_evidence_unscorable"]})
            continue

        current_expected = set(current_evidence["expected_pitch_classes"])
        next_expected = set(next_evidence["expected_pitch_classes"])
        current_foreign = set(current_evidence["foreign_pitch_classes"])
        current_alignment, next_alignment = alignments[annotation_id], alignments[next_id]
        current_attacks = [sounds[sid] for sid in current_alignment.get("attacked_sounding_event_ids", []) if sid in sounds]
        next_attacks = [sounds[sid] for sid in next_alignment.get("attacked_sounding_event_ids", []) if sid in sounds]
        last_by_voice: dict[str, dict[str, Any]] = {}
        first_by_voice: dict[str, dict[str, Any]] = {}
        for sound in sorted(current_attacks, key=lambda row: _f(row["span"]["start"])):
            voice = _voice_for(sound, notes)
            if voice:
                last_by_voice[voice] = sound
        for sound in sorted(next_attacks, key=lambda row: _f(row["span"]["start"])):
            voice = _voice_for(sound, notes)
            if voice and voice not in first_by_voice:
                first_by_voice[voice] = sound

        edges = []
        for voice in sorted(last_by_voice.keys() & first_by_voice.keys()):
            before, after = last_by_voice[voice], first_by_voice[voice]
            before_midi, after_midi = int(before["pitch"]["midi_pitch"]), int(after["pitch"]["midi_pitch"])
            interval = after_midi - before_midi
            before_pc, after_pc = before_midi % 12, after_midi % 12
            edges.append({
                "voice_id": voice,
                "from_sounding_event_id": before["sounding_event_id"],
                "to_sounding_event_id": after["sounding_event_id"],
                "from_midi": before_midi,
                "to_midi": after_midi,
                "interval_semitones": interval,
                "stepwise": abs(interval) <= 2,
                "from_is_foreign_to_current_label": before_pc in current_foreign,
                "to_is_expected_in_next_label": after_pc in next_expected,
                "possible_nct_resolution": (
                    before_pc in current_foreign and after_pc in next_expected and 1 <= abs(interval) <= 2
                ),
            })

        current_start, next_start = _start(current), _start(following)
        current_bass = _bass_at(current_start, sounds, current_alignment.get("sounding_event_ids", []))
        next_bass = _bass_at(next_start, sounds, next_alignment.get("sounding_event_ids", []))
        bass_interval = None
        if current_bass and next_bass:
            bass_interval = int(next_bass["pitch"]["midi_pitch"]) - int(current_bass["pitch"]["midi_pitch"])
        resolution_count = sum(edge["possible_nct_resolution"] for edge in edges)
        records.append({
            **base,
            "status": "scored",
            "expected_pitch_class_overlap_with_next": sorted(current_expected & next_expected),
            "expected_pitch_class_change_to_next": sorted(next_expected - current_expected),
            "observed_bass_midi_at_start": None if current_bass is None else int(current_bass["pitch"]["midi_pitch"]),
            "next_observed_bass_midi_at_start": None if next_bass is None else int(next_bass["pitch"]["midi_pitch"]),
            "observed_bass_motion_semitones": bass_interval,
            "boundary_voice_leading_edges": edges,
            "stepwise_edge_count": sum(edge["stepwise"] for edge in edges),
            "possible_nct_resolution_count": resolution_count,
            "possible_nct_resolution_ratio": None if not edges else round(resolution_count / len(edges), 6),
            "diagnostics": [],
            "interpretation": "boundary_context_evidence_not_functional_harmony_correctness",
        })
    return {
        "schema_name": "musicanote-romantext-context-evidence",
        "schema_version": "0.1.0",
        "engine_version": VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "input_policy": "source_labels_visible_to_separate_context_evidence_scorer",
        "interpretation": "Descriptive boundary evidence; does not revise labels, support bands, or gold status",
        "summary": {
            "record_count": len(records),
            "scored_boundaries": sum(row["status"] == "scored" for row in records),
            "possible_nct_resolution_edges": sum(row.get("possible_nct_resolution_count", 0) for row in records),
        },
        "records": records,
    }
