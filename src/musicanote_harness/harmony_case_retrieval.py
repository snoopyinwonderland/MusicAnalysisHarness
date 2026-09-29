"""Transposition-invariant retrieval of source-linked harmony cases.

The query side reads Canonical IR facts only. Retrieved source labels remain
evidence candidates; they are never copied into the query score as facts.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .canonical import stable_id
from .formal_ir import q
from .harmony_label_taxonomy import classify_harmony_label
from .harmony_dataset_manifest import load_manifest_index


VERSION = "harmony-case-retrieval-0.4.0"

MAJOR_KEY_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_KEY_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
WEIGHT_PROFILES = {
    "surface_v0.1": {
        "current_interval_profile": 0.50, "before_interval_profile": 0.12, "after_interval_profile": 0.12,
        "duration": 0.06, "attack_density": 0.08, "vertical_density": 0.06, "bass_motion": 0.06,
    },
    "local_key_v0.2": {
        "current_interval_profile": 0.44, "before_interval_profile": 0.10, "after_interval_profile": 0.10,
        "blind_local_key": 0.14, "duration": 0.05, "attack_density": 0.07,
        "vertical_density": 0.05, "bass_motion": 0.05,
    },
    "voice_leading_v0.2": {
        "current_interval_profile": 0.42, "before_interval_profile": 0.10, "after_interval_profile": 0.10,
        "entry_voice_leading": 0.06, "exit_voice_leading": 0.12, "duration": 0.05,
        "attack_density": 0.06, "vertical_density": 0.05, "bass_motion": 0.04,
    },
    "combined_v0.3": {
        "current_interval_profile": 0.36, "before_interval_profile": 0.09, "after_interval_profile": 0.09,
        "blind_local_key": 0.14, "entry_voice_leading": 0.06, "exit_voice_leading": 0.12,
        "duration": 0.04, "attack_density": 0.04, "vertical_density": 0.03, "bass_motion": 0.03,
    },
    "combined_nct_geometry_v0.4": {
        "current_interval_profile": 0.32, "before_interval_profile": 0.08, "after_interval_profile": 0.08,
        "blind_local_key": 0.14, "entry_voice_leading": 0.06, "exit_voice_leading": 0.11,
        "nct_geometry": 0.10, "duration": 0.03, "attack_density": 0.03,
        "vertical_density": 0.025, "bass_motion": 0.025,
    },
}


def _f(value: dict[str, int] | Fraction | int | str) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, dict):
        return Fraction(value["numerator"], value["denominator"])
    return Fraction(value)


def _sounds(ir: dict[str, Any]) -> list[tuple[Fraction, Fraction, int, str, str]]:
    rows = []
    for sound in ir["sounding_events"]:
        midi = sound["pitch"].get("midi_pitch")
        start, end = _f(sound["span"]["start"]), _f(sound["span"]["end"])
        if midi is not None and end > start:
            rows.append((start, end, int(midi), sound["sounding_event_id"], sound["pitch"]["spelling"]))
    return rows


def _profile(sounds: list[tuple[Fraction, Fraction, int, str, str]], start: Fraction, end: Fraction) -> dict[str, Any] | None:
    active = [row for row in sounds if row[0] < end and start < row[1]]
    if not active or end <= start:
        return None
    at_start = [row for row in active if row[0] <= start < row[1]]
    anchor_rows = at_start or [row for row in active if row[0] == min(item[0] for item in active)]
    bass_midi = min(row[2] for row in anchor_rows)
    weights: dict[int, Fraction] = defaultdict(Fraction)
    spellings: set[str] = set()
    weighted_vertical = Fraction(0)
    edges = sorted({start, end, *(max(start, row[0]) for row in active), *(min(end, row[1]) for row in active)})
    for row_start, row_end, midi, _sid, spelling in active:
        overlap = min(end, row_end) - max(start, row_start)
        if overlap > 0:
            weights[(midi - bass_midi) % 12] += overlap
            spellings.add(spelling)
    for left, right in zip(edges, edges[1:]):
        count = sum(row_start < right and left < row_end for row_start, row_end, *_ in active)
        weighted_vertical += (right - left) * count
    total = sum(weights.values(), Fraction(0))
    attacks = sorted({row[0] for row in active if start <= row[0] < end})
    last_rows = [row for row in active if row[0] == max((item[0] for item in active), default=start)]
    last_bass = min((row[2] for row in last_rows), default=bass_midi)
    duration = end - start
    return {
        "interval_profile": [
            {"interval_class": interval, "weight": q(weight / total)}
            for interval, weight in sorted(weights.items())
        ],
        "bass_midi": bass_midi,
        "bass_spelling": min((row[4] for row in anchor_rows if row[2] == bass_midi), default=""),
        "bass_motion_semitones": last_bass - bass_midi,
        "duration_quarter": q(duration),
        "attack_count": len(attacks),
        "attack_density": round(len(attacks) / float(duration), 6),
        "mean_vertical_count": round(float(weighted_vertical / duration), 6),
        "pitch_spellings": sorted(spellings),
        "sounding_event_ids": sorted({row[3] for row in active}),
    }


def _key_signature_at(ir: dict[str, Any], onset: Fraction) -> dict[str, Any] | None:
    selected = None
    for measure in ir.get("measures", []):
        if _f(measure["global_start_quarter"]) <= onset:
            selected = measure.get("key_signature") or selected
        else:
            break
    return selected


def _blind_local_key_candidates(
    ir: dict[str, Any], sounds: list[tuple[Fraction, Fraction, int, str, str]],
    start: Fraction, end: Fraction, bass_midi: int,
) -> dict[str, Any]:
    score_end = max((row[1] for row in sounds), default=end)
    radius = min(Fraction(8), max(Fraction(4), (end - start) * 2))
    left, right = max(Fraction(0), start - radius), min(score_end, end + radius)
    weights = [0.0] * 12
    for row_start, row_end, midi, _sid, _spelling in sounds:
        overlap = min(right, row_end) - max(left, row_start)
        if overlap > 0:
            weights[midi % 12] += float(overlap)
    norm = math.sqrt(sum(value * value for value in weights)) or 1.0
    signature = _key_signature_at(ir, start)
    candidates = []
    for mode, template in (("major", MAJOR_KEY_PROFILE), ("minor", MINOR_KEY_PROFILE)):
        template_norm = math.sqrt(sum(value * value for value in template))
        for tonic in range(12):
            rotated = [template[(pc - tonic) % 12] for pc in range(12)]
            similarity = sum(left_value * right_value for left_value, right_value in zip(weights, rotated)) / (norm * template_norm)
            prior = 0.0
            if signature and isinstance(signature.get("fifths"), int):
                major_tonic = (7 * int(signature["fifths"])) % 12
                signature_tonic = major_tonic if mode == "major" else (major_tonic + 9) % 12
                if tonic == signature_tonic:
                    prior += 0.025
                if signature.get("mode_hint") == mode:
                    prior += 0.01
            candidates.append({
                "tonic_pitch_class": tonic,
                "mode": mode,
                "relative_tonic_to_observed_bass": (tonic - bass_midi) % 12,
                "fit_score": round(similarity + prior, 6),
            })
    candidates.sort(key=lambda row: (-row["fit_score"], row["mode"], row["tonic_pitch_class"]))
    return {
        "method": "duration_weighted_pitch_class_profile_with_weak_key_signature_prior",
        "window": {"start": q(left), "end": q(right)},
        "candidates": candidates[:5],
        "score_is_not_calibrated_confidence": True,
        "source_harmony_label_used": False,
    }


def _boundary_voice_leading(
    sounds: list[tuple[Fraction, Fraction, int, str, str]], boundary: Fraction, *, direction: str,
) -> dict[str, Any] | None:
    if direction == "entry":
        left = [row for row in sounds if row[0] < boundary <= row[1]]
        right = [row for row in sounds if row[0] <= boundary < row[1]]
    else:
        left = [row for row in sounds if row[0] < boundary <= row[1]]
        right = [row for row in sounds if row[0] <= boundary < row[1]]
    if not right:
        next_onset = min((row[0] for row in sounds if row[0] >= boundary), default=None)
        if next_onset is not None and next_onset - boundary <= 2:
            right = [row for row in sounds if row[0] <= next_onset < row[1]]
    if not left or not right:
        return None
    left_pitches, right_pitches = sorted({row[2] for row in left}), sorted({row[2] for row in right})
    motions: Counter[int] = Counter()
    for pitch in left_pitches:
        target = min(right_pitches, key=lambda candidate: (abs(candidate - pitch), candidate - pitch))
        motions[max(-12, min(12, target - pitch))] += 1
    return {
        "boundary": q(boundary),
        "motion_histogram": [{"semitones": motion, "count": count} for motion, count in sorted(motions.items())],
        "common_tone_count": motions[0],
        "descending_semitone_count": motions[-1],
        "ascending_semitone_count": motions[1],
        "bass_motion_semitones": min(right_pitches) - min(left_pitches),
        "left_sounding_event_ids": sorted({row[3] for row in left}),
        "right_sounding_event_ids": sorted({row[3] for row in right}),
        "interpretation": "Deterministic nearest-motion evidence; not an NCT or harmonic-function label",
    }


def _nct_sequences(ir: dict[str, Any]) -> list[list[tuple[Fraction, int, str]]]:
    notes = {note["note_id"]: note for note in ir.get("note_events", [])}
    voice_onsets: dict[str, dict[Fraction, list[tuple[int, str]]]] = defaultdict(lambda: defaultdict(list))
    for sound in ir.get("sounding_events", []):
        attack_id = sound.get("attack_note_id")
        note = notes.get(attack_id)
        midi = sound.get("pitch", {}).get("midi_pitch")
        if note and midi is not None:
            voice_onsets[note["voice_id"]][_f(sound["span"]["start"])].append((int(midi), sound["sounding_event_id"]))
    sequences = []
    for onsets in voice_onsets.values():
        sequence = [(onset, rows[0][0], rows[0][1]) for onset, rows in onsets.items() if len(rows) == 1]
        sequence.sort(key=lambda row: (row[0], row[1], row[2]))
        sequences.append(sequence)
    return sequences


def _nct_geometry(sequences: list[list[tuple[Fraction, int, str]]], start: Fraction, end: Fraction) -> dict[str, Any]:
    counts = Counter()
    refs: dict[str, list[str]] = defaultdict(list)
    considered = 0
    for sequence in sequences:
        for index in range(1, len(sequence) - 1):
            onset, pitch, sound_id = sequence[index]
            if not start <= onset < end:
                continue
            previous, following = sequence[index - 1], sequence[index + 1]
            approach, departure = pitch - previous[1], following[1] - pitch
            considered += 1
            flags = []
            if approach and departure and abs(approach) <= 2 and abs(departure) <= 2 and (approach > 0) == (departure > 0):
                flags.append("stepwise_same_direction")
            if approach and departure and abs(approach) <= 2 and departure == -approach:
                flags.append("step_away_and_return")
            if approach == 0:
                flags.append("repeated_preparation")
            if abs(departure) <= 2 and departure != 0:
                flags.append("stepwise_departure")
            if departure == -1:
                flags.append("descending_semitone_departure")
            if departure == 1:
                flags.append("ascending_semitone_departure")
            if abs(approach) >= 3 and 0 < abs(departure) <= 2 and (approach > 0) != (departure > 0):
                flags.append("leap_then_reverse_step")
            for flag in flags:
                counts[flag] += 1
                if len(refs[flag]) < 12:
                    refs[flag].append(sound_id)
    names = [
        "stepwise_same_direction", "step_away_and_return", "repeated_preparation", "stepwise_departure",
        "descending_semitone_departure", "ascending_semitone_departure", "leap_then_reverse_step",
    ]
    return {
        "voice_event_count": considered,
        "counts": {name: counts[name] for name in names},
        "example_sounding_event_ids": {name: refs[name] for name in names if refs[name]},
        "interpretation": "Melodic preparation/departure geometry only; no NCT type is asserted",
    }


def extract_case_feature(
    ir: dict[str, Any], span: dict[str, Any], *, prepared_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    start, end = _f(span["start"]), _f(span["end"])
    if end <= start:
        raise ValueError("Case span must have positive duration")
    context = prepared_context or {"sounds": _sounds(ir), "nct_sequences": _nct_sequences(ir)}
    sounds = context["sounds"]
    current = _profile(sounds, start, end)
    if current is None:
        raise ValueError("Case span has no sounding events")
    context_length = min(Fraction(2), end - start)
    score_end = max((row[1] for row in sounds), default=end)
    before = _profile(sounds, max(Fraction(0), start - context_length), start) if start > 0 else None
    after = _profile(sounds, end, min(score_end, end + context_length)) if end < score_end else None
    return {
        "feature_version": VERSION,
        "span": {"start": q(start), "end": q(end)},
        "current": current,
        "before": before,
        "after": after,
        "blind_local_key": _blind_local_key_candidates(ir, sounds, start, end, current["bass_midi"]),
        "entry_voice_leading": _boundary_voice_leading(sounds, start, direction="entry") if start > 0 else None,
        "exit_voice_leading": _boundary_voice_leading(sounds, end, direction="exit") if end < score_end else None,
        "nct_geometry": _nct_geometry(context["nct_sequences"], start, end),
        "invariance": "pitch_classes_relative_to_observed_bass_at_span_start",
    }


def _dataset_identity(package: dict[str, Any], manifest_entry: dict[str, Any] | None) -> dict[str, Any]:
    if manifest_entry:
        return {
            "manifest_entry_id": manifest_entry["manifest_entry_id"],
            "corpus_id": manifest_entry["corpus_id"],
            "collection_id": manifest_entry["collection_id"],
            "work_family_id": manifest_entry["work_family_id"],
            "movement_id": manifest_entry["movement_id"],
            "edition_id": manifest_entry["edition_id"],
            "annotation_lineage_id": manifest_entry["annotation_lineage_id"],
            "split": manifest_entry["split"],
            "identity_status": manifest_entry["work_family_confidence"],
        }
    ir = package["ir"]
    annotation_hash = package["report"]["source_sha256"].get("harmonies", "unknown")
    return {
        "manifest_entry_id": None,
        "corpus_id": "unknown",
        "collection_id": "unknown",
        "work_family_id": f'workfam_{stable_id("score_fallback", ir["score"]["score_id"])}',
        "movement_id": None,
        "edition_id": None,
        "annotation_lineage_id": f'annlin_{stable_id("source_fallback", annotation_hash)}',
        "split": "unassigned",
        "identity_status": "manifest_missing_score_scoped_fallback",
    }


def build_case_records(package: dict[str, Any], manifest_entry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ir = package["ir"]
    feature_context = {"sounds": _sounds(ir), "nct_sequences": _nct_sequences(ir)}
    dataset_identity = _dataset_identity(package, manifest_entry)
    alignments = {row["annotation_id"]: row for row in package["alignments"]}
    evidence = {row["annotation_id"]: row for row in package.get("source_evidence", {}).get("records", [])}
    records = []
    for annotation in package["annotations"]:
        alignment = alignments.get(annotation["annotation_id"], {})
        target = annotation.get("target")
        if alignment.get("mapping_status") != "exact" or not target or "span" not in target:
            continue
        try:
            feature = extract_case_feature(ir, target["span"], prepared_context=feature_context)
        except ValueError:
            continue
        records.append({
            "schema_name": "musicanote-harmony-case-record",
            "schema_version": "0.2.0",
            "case_id": f'hcase_{stable_id(ir["ir_document_id"], annotation["annotation_id"])}',
            "score_id": ir["score"]["score_id"],
            "ir_document_id": ir["ir_document_id"],
            "annotation_id": annotation["annotation_id"],
            "label": {
                "raw": annotation["raw_label"],
                "chord_raw": annotation["components"].get("chord", ""),
                "key_raw": annotation["components"].get("key", ""),
                "taxonomy": classify_harmony_label(annotation["raw_label"], annotation["components"]),
            },
            "feature": feature,
            "dataset_identity": dataset_identity,
            "source_evidence": {
                "support_band": evidence.get(annotation["annotation_id"], {}).get("support_band", "unscorable"),
                "status": evidence.get(annotation["annotation_id"], {}).get("status", "unscorable"),
            },
            "provenance": {
                "source_asset_sha256": annotation["source_asset_sha256"],
                "score_sha256": package["report"]["source_sha256"]["score"],
                "source_locator": annotation["source_locator"],
                "author_origin": annotation["author_origin"],
                "source_review_status": annotation["source_review_status"],
                "score_source_path": package["report"].get("source_paths", {}).get("score", ""),
            },
            "training_eligible": False,
        })
    return records


def _vector(profile: dict[str, Any] | None) -> list[float] | None:
    if profile is None:
        return None
    values = [0.0] * 12
    for row in profile["interval_profile"]:
        values[row["interval_class"]] = float(_f(row["weight"]))
    return values


def _cosine(left: dict[str, Any] | None, right: dict[str, Any] | None) -> float | None:
    a, b = _vector(left), _vector(right)
    if a is None or b is None:
        return None
    denominator = math.sqrt(sum(value * value for value in a) * sum(value * value for value in b))
    return sum(x * y for x, y in zip(a, b)) / denominator if denominator else None


def _ratio(left: float, right: float) -> float:
    return min(left, right) / max(left, right) if left > 0 and right > 0 else 0.0


def _key_vector(value: dict[str, Any] | None) -> list[float] | None:
    if not value:
        return None
    vector = [0.0] * 24
    candidates = value.get("candidates", [])
    if not candidates:
        return None
    floor = min(row["fit_score"] for row in candidates)
    for row in candidates:
        index = row["relative_tonic_to_observed_bass"] + (12 if row["mode"] == "minor" else 0)
        vector[index] = max(0.000001, row["fit_score"] - floor + 0.01)
    return vector


def _movement_vector(value: dict[str, Any] | None) -> list[float] | None:
    if not value:
        return None
    vector = [0.0] * 25
    for row in value.get("motion_histogram", []):
        vector[int(row["semitones"]) + 12] = float(row["count"])
    return vector


def _nct_vector(value: dict[str, Any] | None) -> list[float] | None:
    if not value or not value.get("voice_event_count"):
        return None
    names = [
        "stepwise_same_direction", "step_away_and_return", "repeated_preparation", "stepwise_departure",
        "descending_semitone_departure", "ascending_semitone_departure", "leap_then_reverse_step",
    ]
    return [float(value.get("counts", {}).get(name, 0)) for name in names]


def _vector_cosine(left: list[float] | None, right: list[float] | None) -> float | None:
    if left is None or right is None:
        return None
    denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else None


def feature_channel_values(query: dict[str, Any], candidate: dict[str, Any]) -> dict[str, float | None]:
    return {
        "current_interval_profile": _cosine(query["current"], candidate["current"]),
        "before_interval_profile": _cosine(query.get("before"), candidate.get("before")),
        "after_interval_profile": _cosine(query.get("after"), candidate.get("after")),
        "blind_local_key": _vector_cosine(_key_vector(query.get("blind_local_key")), _key_vector(candidate.get("blind_local_key"))),
        "entry_voice_leading": _vector_cosine(_movement_vector(query.get("entry_voice_leading")), _movement_vector(candidate.get("entry_voice_leading"))),
        "exit_voice_leading": _vector_cosine(_movement_vector(query.get("exit_voice_leading")), _movement_vector(candidate.get("exit_voice_leading"))),
        "nct_geometry": _vector_cosine(_nct_vector(query.get("nct_geometry")), _nct_vector(candidate.get("nct_geometry"))),
        "duration": _ratio(float(_f(query["current"]["duration_quarter"])), float(_f(candidate["current"]["duration_quarter"]))),
        "attack_density": _ratio(query["current"]["attack_density"], candidate["current"]["attack_density"]),
        "vertical_density": _ratio(query["current"]["mean_vertical_count"], candidate["current"]["mean_vertical_count"]),
        "bass_motion": max(0.0, 1 - abs(query["current"]["bass_motion_semitones"] - candidate["current"]["bass_motion_semitones"]) / 12),
    }


def score_channel_values(values: dict[str, float | None], weight_profile: str = "combined_v0.3") -> dict[str, Any]:
    if weight_profile not in WEIGHT_PROFILES:
        raise ValueError(f"Unknown harmony retrieval weight profile: {weight_profile}")
    weights = WEIGHT_PROFILES[weight_profile]
    channels: list[tuple[str, float, float | None]] = [
        (name, weight, values[name]) for name, weight in weights.items()
    ]
    available = [(name, weight, value) for name, weight, value in channels if value is not None]
    total_weight = sum(weight for _name, weight, _value in available) or 1
    score = sum(weight * float(value) for _name, weight, value in available) / total_weight
    details = {name: round(float(value), 6) if value is not None else None for name, _weight, value in channels}
    strongest = sorted(((value, name) for name, _weight, value in available), reverse=True)[:3]
    weakest = sorted((value, name) for name, _weight, value in available)[:2]
    return {
        "similarity": round(score, 6),
        "weight_profile": weight_profile,
        "channels": details,
        "similar_reasons": [name for _value, name in strongest],
        "difference_reasons": [name for _value, name in weakest if _value < 0.75],
    }


def weighted_similarity(values: dict[str, float | None], weight_profile: str = "combined_v0.3") -> float:
    if weight_profile not in WEIGHT_PROFILES:
        raise ValueError(f"Unknown harmony retrieval weight profile: {weight_profile}")
    available = [(weight, values[name]) for name, weight in WEIGHT_PROFILES[weight_profile].items()
                 if values[name] is not None]
    total_weight = sum(weight for weight, _value in available) or 1.0
    return round(sum(weight * float(value) for weight, value in available) / total_weight, 6)


def compare_features(
    query: dict[str, Any], candidate: dict[str, Any], *, weight_profile: str = "combined_v0.3",
) -> dict[str, Any]:
    return score_channel_values(feature_channel_values(query, candidate), weight_profile)


def retrieve_cases(
    query_ir: dict[str, Any], query_span: dict[str, Any], cases: Iterable[dict[str, Any]],
    *, limit: int = 12, exclude_score_id: str | None = None, per_score_limit: int = 2,
    query_dataset_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    feature = extract_case_feature(query_ir, query_span)
    excluded = exclude_score_id or query_ir["score"]["score_id"]
    matches = []
    excluded_family = (query_dataset_identity or {}).get("work_family_id")
    excluded_lineage = (query_dataset_identity or {}).get("annotation_lineage_id")
    query_split = (query_dataset_identity or {}).get("split")
    allowed_candidate_splits = {"train"} if query_split in {"dev", "holdout"} else None
    for case in cases:
        if case["score_id"] == excluded:
            continue
        identity = case.get("dataset_identity", {})
        if allowed_candidate_splits and identity.get("split") not in allowed_candidate_splits:
            continue
        if excluded_family and identity.get("work_family_id") == excluded_family:
            continue
        if excluded_lineage and identity.get("annotation_lineage_id") == excluded_lineage:
            continue
        comparison = compare_features(feature, case["feature"])
        matches.append({
            "case_id": case["case_id"],
            "score_id": case["score_id"],
            "annotation_id": case["annotation_id"],
            "label": case["label"],
            "source_evidence": case["source_evidence"],
            "provenance": case["provenance"],
            "dataset_identity": identity,
            "comparison": comparison,
        })
    matches.sort(key=lambda row: (-row["comparison"]["similarity"], row["case_id"]))
    diversified = []
    score_counts: dict[str, int] = defaultdict(int)
    for match in matches:
        if score_counts[match["score_id"]] >= max(1, per_score_limit):
            continue
        score_counts[match["score_id"]] += 1
        diversified.append(match)
        if len(diversified) >= max(1, min(int(limit), 100)):
            break
    matches = diversified
    hypotheses: dict[str, dict[str, Any]] = {}
    for match in matches:
        label = match["label"]["raw"]
        row = hypotheses.setdefault(label, {"label": label, "case_count": 0, "similarity_sum": 0.0, "case_refs": []})
        row["case_count"] += 1
        row["similarity_sum"] += match["comparison"]["similarity"]
        row["case_refs"].append(match["case_id"])
    alternatives = sorted(({
        "label": row["label"],
        "case_count": row["case_count"],
        "mean_similarity": round(row["similarity_sum"] / row["case_count"], 6),
        "case_refs": row["case_refs"],
    } for row in hypotheses.values()), key=lambda row: (-row["mean_similarity"], -row["case_count"], row["label"]))
    families: dict[str, dict[str, Any]] = {}
    for match in matches:
        family = match["label"].get("taxonomy", {}).get("family", "other_or_unresolved")
        row = families.setdefault(family, {"family": family, "case_count": 0, "similarity_sum": 0.0, "case_refs": []})
        row["case_count"] += 1
        row["similarity_sum"] += match["comparison"]["similarity"]
        row["case_refs"].append(match["case_id"])
    family_alternatives = sorted(({
        "family": row["family"], "case_count": row["case_count"],
        "mean_similarity": round(row["similarity_sum"] / row["case_count"], 6), "case_refs": row["case_refs"],
    } for row in families.values()), key=lambda row: (-row["mean_similarity"], -row["case_count"], row["family"]))
    return {
        "schema_name": "musicanote-harmony-case-retrieval-result",
        "schema_version": "0.2.0",
        "engine_version": VERSION,
        "query": {
            "query_id": f'hquery_{stable_id(query_ir["ir_document_id"], _f(query_span["start"]), _f(query_span["end"]), VERSION)}',
            "score_id": query_ir["score"]["score_id"],
            "ir_document_id": query_ir["ir_document_id"],
            "feature": feature,
        },
        "policy": {
            "same_score_excluded": True,
            "same_work_family_excluded": bool(excluded_family),
            "same_annotation_lineage_excluded": bool(excluded_lineage),
            "query_split": query_split or "unassigned",
            "allowed_candidate_splits": sorted(allowed_candidate_splits) if allowed_candidate_splits else "all",
            "per_score_result_limit": max(1, per_score_limit),
            "labels_hidden_from_query_features": True,
            "retrieved_labels_are_evidence_not_predictions": True,
            "similarity_is_not_calibrated": True,
        },
        "matches": matches,
        "label_alternatives": alternatives,
        "family_alternatives": family_alternatives,
        "interpretation": "Retrieved source-linked analogies and counterexamples; no label is copied to the query score",
    }


def load_prepared_package(folder: str | Path) -> dict[str, Any]:
    folder = Path(folder)
    read_jsonl = lambda name: [json.loads(line) for line in (folder / name).read_text(encoding="utf-8").splitlines() if line]
    evidence_path = folder / "source_harmony_evidence.json"
    return {
        "ir": json.loads((folder / "canonical_music_ir.json").read_text(encoding="utf-8")),
        "annotations": read_jsonl("imported_annotations.jsonl"),
        "alignments": read_jsonl("alignment_records.jsonl"),
        "source_evidence": json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.is_file() else {"records": []},
        "report": json.loads((folder / "preparation_report.json").read_text(encoding="utf-8")),
    }


def build_case_library(
    source: str | Path, output: str | Path, limit: int | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    source, output = Path(source), Path(output)
    folders = sorted(path.parent for path in source.rglob("canonical_music_ir.json"))
    if limit is not None:
        folders = folders[: max(0, limit)]
    schema_path = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "harmony_case_record.schema.json"
    validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    output.mkdir(parents=True, exist_ok=True)
    manifest_index = load_manifest_index(manifest_path) if manifest_path else {}
    records_path = output / "harmony_case_records.jsonl"
    processed = 0
    case_count = 0
    errors = []
    score_counts = []
    with records_path.open("w", encoding="utf-8") as handle:
        for folder in folders:
            try:
                package = load_prepared_package(folder)
                records = build_case_records(package, manifest_index.get(package["ir"]["ir_document_id"]))
                for record in records:
                    validator.validate(record)
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                processed += 1
                case_count += len(records)
                score_counts.append({"package": str(folder), "case_count": len(records)})
            except Exception as exc:
                errors.append({"package": str(folder), "error": f"{type(exc).__name__}: {exc}"})
    report = {
        "schema_name": "musicanote-harmony-case-library-report",
        "schema_version": "0.2.0",
        "builder_version": VERSION,
        "source": str(source),
        "dataset_manifest": str(manifest_path) if manifest_path else None,
        "packages_discovered": len(folders),
        "packages_processed": processed,
        "case_count": case_count,
        "error_count": len(errors),
        "score_counts": score_counts,
        "errors": errors,
        "policy": {
            "training_eligible": False,
            "labels_are_retrieval_evidence": True,
            "same_score_queries_must_be_excluded": True,
            "same_work_and_lineage_exclusion_available": bool(manifest_path),
        },
        "identity_coverage": {
            "manifest_linked_scores": sum(bool(row.get("manifest_entry_id")) for row in manifest_index.values()),
            "manifest_required_for_blind_evaluation": True,
        },
    }
    (output / "case_library_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def load_case_records(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
