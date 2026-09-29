"""Narrow blind surface-sonority diagnostic against imported DCML labels.

DCML labels are available only to this scorer. Roman function and surface
pitch-class equality are not the same claim; this is a diagnostic, not accuracy.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from music21 import key, roman


SIMPLE_CHORDS = {"I", "i", "IV", "iv", "V", "v", "ii", "iii", "vi", "VI", "III"}
KEY_PATTERN = re.compile(r"^[A-Ga-g](?:#|b|-)?$")


def _f(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def evaluate_simple_dcml(surface: dict[str, Any], annotations: list[dict[str, Any]], alignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare only unmodified simple Roman labels spanning a complete beat."""
    if surface.get("input_policy") != "blind_canonical_ir_only":
        raise ValueError("This diagnostic requires a blind Canonical-IR-only analyzer result")
    if any(item.get("target") and item["target"].get("score_id") not in (None, surface["score_id"])
           for item in annotations):
        raise ValueError("Annotation score_id differs from blind surface score_id")
    approved = {item["annotation_id"] for item in alignments
                if item["mapping_status"] in {"exact", "verified_transform"}}
    references = []
    for item in annotations:
        if item["annotation_id"] not in approved or not item.get("target") or "span" not in item["target"]:
            continue
        components = item["components"]
        chord = components.get("chord", "")
        global_key = components.get("globalkey", "")
        if chord not in SIMPLE_CHORDS or components.get("localkey") not in {"I", "i"} or not KEY_PATTERN.fullmatch(global_key):
            continue
        try:
            expected = sorted({p.pitchClass for p in roman.RomanNumeral(chord, key.Key(global_key)).pitches})
        except (ValueError, TypeError):
            continue
        span = item["target"]["span"]
        references.append((_f(span["start"]), _f(span["end"]), item["annotation_id"], chord, global_key, expected))

    matched = []
    skipped_overlap = 0
    for window in surface["windows"]:
        start, end = _f(window["span"]["start"]), _f(window["span"]["end"])
        covering = [reference for reference in references if reference[0] <= start and end <= reference[1]]
        if len(covering) != 1:
            if len(covering) > 1:
                skipped_overlap += 1
            continue
        _a, _b, annotation_id, chord, global_key, expected = covering[0]
        candidate_sets = [item["template_pitch_classes"] for item in window["candidates"]]
        matched.append({
            "window_id": window["window_id"], "annotation_id": annotation_id,
            "reference": f"{global_key}:{chord}", "expected_pitch_classes": expected,
            "window_status": window["status"],
            "top_candidate": window["candidates"][0]["label"] if window["candidates"] else None,
            "top1_template_equal": bool(candidate_sets and candidate_sets[0] == expected),
            "top5_template_equal": expected in candidate_sets,
            "displayed_top1_equal": bool(window["display_hint_index"] == 0 and candidate_sets and candidate_sets[0] == expected),
        })

    n = len(matched)
    return {
        "schema_name": "musicanote-surface-dcml-simple-diagnostic",
        "schema_version": "0.1.0",
        "score_id": surface["score_id"],
        "analyzer_input_policy": surface["input_policy"],
        "scorer_input_policy": "source_annotations_visible_to_scorer_only",
        "scope": "fully_covered_single_simple_roman_chord_local_tonic_only",
        "interpretation": "surface_pitch_class_template_agreement_not_functional_harmony_accuracy",
        "eligible_windows": n,
        "skipped_multi_reference_windows": skipped_overlap,
        "top1_template_equal": sum(row["top1_template_equal"] for row in matched),
        "top5_template_equal": sum(row["top5_template_equal"] for row in matched),
        "displayed_top1_equal": sum(row["displayed_top1_equal"] for row in matched),
        "mismatch_examples": [row for row in matched if not row["top1_template_equal"]][:20],
    }
