"""Blind, whole-score surface-sonority candidates from Canonical IR facts.

This is H1's first observational baseline, not functional harmony or cadence.
It never reads imported labels, phrase boundaries, or a key guess. Fit scores
rank templates within one window and are not calibrated probabilities.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from .canonical import stable_id
from .formal_ir import q


VERSION = "blind-surface-sonority-0.1.0"
PITCH_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
TEMPLATES = (
    ("major", (0, 4, 7)),
    ("minor", (0, 3, 7)),
    ("diminished", (0, 3, 6)),
    ("augmented", (0, 4, 8)),
    ("dominant7", (0, 4, 7, 10)),
    ("major7", (0, 4, 7, 11)),
    ("minor7", (0, 3, 7, 10)),
    ("half-diminished7", (0, 3, 6, 10)),
    ("diminished7", (0, 3, 6, 9)),
)


def _f(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _rank(weight_by_pc: dict[int, Fraction]) -> list[dict[str, Any]]:
    total = sum(weight_by_pc.values(), Fraction(0))
    if not total:
        return []
    candidates = []
    for root in range(12):
        for quality, intervals in TEMPLATES:
            pcs = {(root + interval) % 12 for interval in intervals}
            matched = sum((weight for pc, weight in weight_by_pc.items() if pc in pcs), Fraction(0))
            purity = matched / total
            completeness = Fraction(len(pcs & weight_by_pc.keys()), len(pcs))
            fit = Fraction(55, 100) * purity + Fraction(45, 100) * completeness
            candidates.append({
                "label": f"{PITCH_NAMES[root]}:{quality}",
                "root_pitch_class": root,
                "quality": quality,
                "template_pitch_classes": sorted(pcs),
                "fit_score": round(float(fit), 6),
                "purity": round(float(purity), 6),
                "completeness": round(float(completeness), 6),
            })
    return sorted(candidates, key=lambda item: (-item["fit_score"], item["label"]))[:5]


def analyze_surface(ir: dict[str, Any]) -> dict[str, Any]:
    """Analyze every notated beat window, including explicit rests/abstentions."""
    sounds = []
    for sound in ir["sounding_events"]:
        midi = sound["pitch"]["midi_pitch"]
        if midi is None:
            continue
        start, end = _f(sound["span"]["start"]), _f(sound["span"]["end"])
        if end > start:
            sounds.append((start, end, midi, sound["sounding_event_id"], sound["source_note_ids"]))

    windows = []
    for measure in sorted(ir["measures"], key=lambda row: row["sequential_measure_index"]):
        start = _f(measure["global_start_quarter"])
        end = start + _f(measure["actual_duration_quarter"])
        beat = Fraction(4, measure["time_signature"]["beat_type"])
        if beat <= 0:
            raise ValueError("Invalid beat unit")
        onset = start
        while onset < end:
            boundary = min(onset + beat, end)
            active = [(a, b, midi, sid, ids) for a, b, midi, sid, ids in sounds if a < boundary and onset < b]
            duration = boundary - onset
            weights: dict[int, Fraction] = {}
            for a, b, midi, _sid, _ids in active:
                pc = midi % 12
                fraction = (min(b, boundary) - max(a, onset)) / duration
                weights[pc] = min(Fraction(1), weights.get(pc, Fraction(0)) + fraction)
            candidates = _rank(weights)
            distinct = len(weights)
            if not active:
                status, reason = "rest", "no_sounding_pitches"
            elif distinct < 3:
                status, reason = "abstained", "fewer_than_three_pitch_classes"
            elif not candidates or candidates[0]["fit_score"] < 0.7:
                status, reason = "abstained", "weak_template_fit"
            elif len(candidates) > 1 and candidates[0]["fit_score"] - candidates[1]["fit_score"] < 0.05:
                status, reason = "ambiguous", "candidate_margin_below_0.05"
            else:
                status, reason = "candidate", None
            midi_at_start = sorted(midi for a, b, midi, _sid, _ids in active if a <= onset < b)
            window = {
                "window_id": f"hsw_{stable_id(ir['ir_document_id'], onset, boundary)}",
                "measure_id": measure["measure_id"],
                "span": {"start": q(onset), "end": q(boundary)},
                "status": status,
                "abstention_reason": reason,
                "pitch_class_weights": [
                    {"pitch_class": pc, "weight": q(weight)} for pc, weight in sorted(weights.items())
                ],
                "bass_midi_at_start": midi_at_start[0] if midi_at_start else None,
                "sounding_event_ids": sorted({sid for _a, _b, _midi, sid, _ids in active}),
                "note_ids": sorted({note_id for _a, _b, _midi, _sid, ids in active for note_id in ids}),
                "candidates": candidates,
                "display_hint_index": 0 if status == "candidate" else None,
            }
            windows.append(window)
            onset = boundary

    counts = {status: sum(window["status"] == status for window in windows)
              for status in ("candidate", "ambiguous", "abstained", "rest")}
    return {
        "schema_name": "musicanote-blind-surface-harmony-pilot",
        "schema_version": "0.1.0",
        "engine_version": VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "input_policy": "blind_canonical_ir_only",
        "time_policy": "written_score_notated_beat_windows_half_open",
        "score_policy": "template_fit_rank_not_calibrated_confidence",
        "interpretation_level": "surface_sonority_only_no_key_function_or_cadence",
        "windows": windows,
        "summary": {"window_count": len(windows), "status_counts": counts},
    }
