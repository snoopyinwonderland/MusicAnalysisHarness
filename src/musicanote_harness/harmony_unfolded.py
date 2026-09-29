"""Blind short-span harmonic segmentation over unfolded beat evidence.

This pilot links attacks and sustained notes across neighboring notated beats.
It does not infer NCT types, keys, Roman numerals, or cadence.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from .canonical import stable_id
from .formal_ir import q
from .harmony_surface import _f, _rank, analyze_surface


VERSION = "blind-unfolded-harmony-0.1.0"
MAX_BEATS = 4
SEGMENT_COST = 0.20
INCOMPLETE_COST = 0.25


def _merged_weights(windows: list[dict[str, Any]]) -> dict[int, Fraction]:
    start, end = _f(windows[0]["span"]["start"]), _f(windows[-1]["span"]["end"])
    total = end - start
    values: dict[int, Fraction] = {}
    for window in windows:
        duration = _f(window["span"]["end"]) - _f(window["span"]["start"])
        for item in window["pitch_class_weights"]:
            pc = item["pitch_class"]
            values[pc] = values.get(pc, Fraction(0)) + _f(item["weight"]) * duration / total
    return values


def _segment_info(windows: list[dict[str, Any]], ir_document_id: str) -> dict[str, Any]:
    start, end = _f(windows[0]["span"]["start"]), _f(windows[-1]["span"]["end"])
    weights = _merged_weights(windows)
    candidates = _rank(weights)
    fit = candidates[0]["fit_score"] if candidates else 0.0
    if len(weights) < 3:
        status, reason = "abstained", "fewer_than_three_pitch_classes_across_span"
    elif fit < 0.7:
        status, reason = "abstained", "weak_unfolded_template_fit"
    elif len(candidates) > 1 and fit - candidates[1]["fit_score"] < 0.05:
        status, reason = "ambiguous", "candidate_margin_below_0.05"
    else:
        status, reason = "candidate", None
    return {
        "segment_id": f"uhs_{stable_id(ir_document_id, start, end)}",
        "span": {"start": q(start), "end": q(end)},
        "beat_window_ids": [window["window_id"] for window in windows],
        "status": status,
        "abstention_reason": reason,
        "pitch_class_weights": [{"pitch_class": pc, "weight": q(weight)} for pc, weight in sorted(weights.items())],
        "sounding_event_ids": sorted({sid for window in windows for sid in window["sounding_event_ids"]}),
        "note_ids": sorted({nid for window in windows for nid in window["note_ids"]}),
        "candidates": candidates,
        "display_hint_index": 0 if status == "candidate" else None,
        "fit_score": fit,
    }


def _preserves_local_anchors(windows: list[dict[str, Any]], segment: dict[str, Any]) -> bool:
    """Do not let long-span smoothing erase a clear local sonority or bass reset."""
    if len(windows) == 1:
        return True
    anchors = [window for window in windows
               if window["status"] == "candidate" and window["candidates"][0]["fit_score"] >= 0.9]
    if anchors:
        if not segment["candidates"]:
            return False
        selected_pcs = segment["candidates"][0]["template_pitch_classes"]
        if any(window["candidates"][0]["template_pitch_classes"] != selected_pcs for window in anchors):
            return False
    for before, after in zip(windows, windows[1:]):
        a, b = before["bass_midi_at_start"], after["bass_midi_at_start"]
        if a is not None and b is not None and abs(a - b) >= 5 and (before in anchors or after in anchors):
            return False
    return True


def analyze_unfolded(ir: dict[str, Any]) -> dict[str, Any]:
    """Choose 1–4-beat spans by minimum template loss plus segment penalty."""
    surface = analyze_surface(ir)
    beats = surface["windows"]
    segments: list[dict[str, Any]] = []
    start = 0
    while start < len(beats):
        if beats[start]["status"] == "rest":
            start += 1
            continue
        stop = start
        while stop < len(beats) and beats[stop]["status"] != "rest" and (
            stop == start or _f(beats[stop - 1]["span"]["end"]) == _f(beats[stop]["span"]["start"])
        ):
            stop += 1
        run = beats[start:stop]
        count = len(run)
        best_cost = [float("inf")] * (count + 1)
        best_choice: list[tuple[int, dict[str, Any]] | None] = [None] * count
        best_cost[count] = 0.0
        for i in range(count - 1, -1, -1):
            for length in range(1, min(MAX_BEATS, count - i) + 1):
                segment = _segment_info(run[i:i + length], ir["ir_document_id"])
                if not _preserves_local_anchors(run[i:i + length], segment):
                    continue
                fit = segment["fit_score"]
                insufficient = len(segment["pitch_class_weights"]) < 3
                cost = length * (1 - fit) + SEGMENT_COST + (INCOMPLETE_COST if insufficient else 0) + best_cost[i + length]
                if cost < best_cost[i] - 1e-9:
                    best_cost[i] = cost
                    best_choice[i] = (length, segment)
        index = 0
        while index < count:
            choice = best_choice[index]
            if choice is None:
                raise RuntimeError("Unfolded harmonic segmentation failed")
            length, segment = choice
            segments.append(segment)
            index += length
        start = stop

    by_beat = {beat_id: segment for segment in segments for beat_id in segment["beat_window_ids"]}
    projected = []
    for beat in beats:
        segment = by_beat.get(beat["window_id"])
        projected.append({
            **beat,
            "status": segment["status"] if segment else "rest",
            "abstention_reason": segment["abstention_reason"] if segment else "no_sounding_pitches",
            "candidates": segment["candidates"] if segment else [],
            "display_hint_index": segment["display_hint_index"] if segment else None,
            "segment_id": segment["segment_id"] if segment else None,
        })
    counts = {status: sum(window["status"] == status for window in projected)
              for status in ("candidate", "ambiguous", "abstained", "rest")}
    return {
        "schema_name": "musicanote-blind-unfolded-harmony-pilot",
        "schema_version": "0.1.0",
        "engine_version": VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "input_policy": "blind_canonical_ir_only",
        "time_policy": "written_score_one_to_four_notated_beats_half_open",
        "score_policy": "template_fit_plus_segment_penalty_not_calibrated_confidence",
        "interpretation_level": "unfolded_surface_harmony_only_no_nct_key_function_or_cadence",
        "segments": segments,
        "windows": projected,
        "summary": {"segment_count": len(segments), "window_count": len(projected), "status_counts": counts},
    }
