"""Score-derived evidence for imported RomanText labels.

This scorer never rewrites a source label and never turns a heuristic band into
gold.  It asks only whether the notated sounding evidence is compatible with
the pitch-class template implied by a Roman numeral and key.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from music21 import key, roman

from .formal_ir import q


VERSION = "romantext-source-evidence-0.1.1"


def _f(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _overlap(a: Fraction, b: Fraction, c: Fraction, d: Fraction) -> Fraction:
    return max(Fraction(0), min(b, d) - max(a, c))


def _band(presence: float, purity: float, bass_matches: bool | None) -> str:
    if presence >= 0.75 and purity >= 0.70 and bass_matches is not False:
        return "strong_support"
    if presence >= 2 / 3 and purity >= 0.55:
        return "moderate_support"
    if presence >= 0.50 or purity >= 0.40:
        return "mixed_evidence"
    return "weak_evidence"


def evaluate_source_harmony(package: dict[str, Any]) -> dict[str, Any]:
    ir = package["ir"]
    annotations = {row["annotation_id"]: row for row in package["annotations"]}
    sounds = {row["sounding_event_id"]: row for row in ir["sounding_events"]}
    records: list[dict[str, Any]] = []
    for alignment in package["alignments"]:
        annotation = annotations[alignment["annotation_id"]]
        base = {
            "annotation_id": annotation["annotation_id"],
            "raw_label": annotation["raw_label"],
            "key_raw": annotation["components"].get("key", ""),
            "mapping_status": alignment["mapping_status"],
        }
        if alignment["mapping_status"] != "exact" or not annotation.get("target"):
            records.append({**base, "status": "unscorable", "support_band": "unscorable", "diagnostics": ["alignment_not_exact"]})
            continue
        try:
            rn = roman.RomanNumeral(annotation["raw_label"], key.Key(base["key_raw"]))
            expected = sorted({pitch.pitchClass for pitch in rn.pitches})
            expected_spellings = [pitch.name.replace("-", "♭") for pitch in rn.pitches]
            expected_bass = rn.bass().pitchClass
            expected_bass_spelling = rn.bass().name.replace("-", "♭")
        except Exception as exc:
            records.append({**base, "status": "unscorable", "support_band": "unscorable", "diagnostics": [f"roman_parse_failed:{type(exc).__name__}"]})
            continue
        span = annotation["target"]["span"]
        start, end = _f(span["start"]), _f(span["end"])
        weights: dict[int, Fraction] = {}
        attack_weights: dict[int, Fraction] = {}
        active_at_start = []
        for sound_id in alignment.get("sounding_event_ids", []):
            sound = sounds.get(sound_id)
            if not sound:
                continue
            sound_start, sound_end = _f(sound["span"]["start"]), _f(sound["span"]["end"])
            amount = _overlap(start, end, sound_start, sound_end)
            if amount <= 0:
                continue
            pc = int(sound["pitch"]["pitch_class"])
            weights[pc] = weights.get(pc, Fraction(0)) + amount
            if start <= sound_start < end:
                attack_weights[pc] = attack_weights.get(pc, Fraction(0)) + amount
            if sound_start <= start < sound_end:
                active_at_start.append(sound)
        total = sum(weights.values(), Fraction(0))
        if not weights or total <= 0:
            records.append({**base, "status": "unscorable", "support_band": "unscorable", "diagnostics": ["no_sounding_evidence"]})
            continue
        observed = set(weights)
        present = sorted(observed.intersection(expected))
        missing = sorted(set(expected).difference(observed))
        foreign = sorted(observed.difference(expected))
        chord_weight = sum((value for pc, value in weights.items() if pc in expected), Fraction(0))
        presence = len(present) / len(expected) if expected else 0.0
        purity = float(chord_weight / total)
        start_bass_midi = min((int(sound["pitch"]["midi_pitch"]) for sound in active_at_start), default=None)
        start_bass_pc = None if start_bass_midi is None else start_bass_midi % 12
        bass_matches = None if start_bass_pc is None else start_bass_pc == expected_bass
        attack_total = sum(attack_weights.values(), Fraction(0))
        attack_chord = sum((value for pc, value in attack_weights.items() if pc in expected), Fraction(0))
        attack_purity = None if attack_total == 0 else float(attack_chord / attack_total)
        band = _band(presence, purity, bass_matches)
        diagnostics = []
        if missing:
            diagnostics.append("expected_pitch_classes_missing")
        if foreign:
            diagnostics.append("foreign_pitch_classes_present_possible_nct_or_label_mismatch")
        if bass_matches is False:
            diagnostics.append("start_bass_differs_from_notated_inversion")
        records.append(
            {
                **base,
                "status": "scored",
                "support_band": band,
                "span": span,
                "expected_pitch_classes": expected,
                "expected_pitch_spellings": expected_spellings,
                "present_expected_pitch_classes": present,
                "missing_expected_pitch_classes": missing,
                "foreign_pitch_classes": foreign,
                "expected_tone_presence_ratio": round(presence, 6),
                "chord_tone_duration_ratio": round(purity, 6),
                "attack_chord_tone_duration_ratio": None if attack_purity is None else round(attack_purity, 6),
                "expected_bass_pitch_class": expected_bass,
                "expected_bass_spelling": expected_bass_spelling,
                "observed_bass_pitch_class_at_start": start_bass_pc,
                "bass_matches_notated_inversion": bass_matches,
                "observed_pitch_class_weights": [
                    {"pitch_class": pc, "duration_weight": q(value)} for pc, value in sorted(weights.items())
                ],
                "diagnostics": diagnostics,
                "interpretation": "compatibility_evidence_not_harmony_correctness_or_confidence",
            }
        )
    bands = ["strong_support", "moderate_support", "mixed_evidence", "weak_evidence", "unscorable"]
    return {
        "schema_name": "musicanote-romantext-source-evidence",
        "schema_version": "0.1.0",
        "engine_version": VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "input_policy": "source_labels_visible_to_separate_evidence_scorer",
        "interpretation": "Heuristic score compatibility bands; not correctness, confidence, validation, or training eligibility",
        "summary": {
            "record_count": len(records),
            "support_band_counts": {band: sum(row["support_band"] == band for row in records) for band in bands},
        },
        "records": records,
    }
