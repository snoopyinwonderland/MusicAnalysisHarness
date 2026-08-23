from __future__ import annotations

import hashlib
from fractions import Fraction
from pathlib import Path
from typing import Any

from music21 import pitch

from .canonical import as_fraction, stable_id


SCHEMA_NAME = "musicanote-canonical-music-ir"
SCHEMA_VERSION = "0.1.0"


def q(value: str | Fraction | int) -> dict[str, int]:
    value = as_fraction(str(value)) if not isinstance(value, Fraction) else value
    return {"numerator": value.numerator, "denominator": value.denominator}


def pitch_record(spelling: str) -> dict[str, Any]:
    parsed = pitch.Pitch(spelling)
    alter = Fraction(str(parsed.accidental.alter if parsed.accidental else 0)).limit_denominator(1024)
    return {
        "spelling": spelling,
        "step": parsed.step,
        "alter": q(alter),
        "octave": int(parsed.octave),
        "midi_pitch": int(parsed.midi) if alter.denominator == 1 else None,
        "pitch_class": int(parsed.pitchClass) if alter.denominator == 1 else None,
    }


class FormalIRAdapter:
    """Compatibility adapter from the existing 0.2 prototype to formal IR 0.1.0.

    Fields unavailable from the prototype are explicitly recorded in the parser
    manifest instead of being interpreted musically.
    """

    def convert(self, legacy: dict[str, Any], source: str | Path) -> dict[str, Any]:
        source = Path(source)
        raw_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        source_file_id = f"src_{raw_hash[:20]}"
        score_id = f"score_{raw_hash[:20]}"
        ir_document_id = f"ir_{stable_id(raw_hash, SCHEMA_VERSION)}"

        part_rows = legacy.get("parts", [])
        part_map = {row["part_id"]: f"part_{stable_id(score_id, row['part_id'])}" for row in part_rows}
        segment_rows = legacy.get("notated_note_segments", [])
        rest_rows = legacy.get("rest_events", [])

        staff_keys = sorted({(e["part_id"], e["staff_id"]) for e in [*segment_rows, *rest_rows]})
        staff_map = {key: f"staff_{stable_id(score_id, *key)}" for key in staff_keys}
        voice_keys = sorted({(e["part_id"], e["staff_id"], e["voice_id"]) for e in [*segment_rows, *rest_rows]})
        voice_map = {key: f"voice_{stable_id(score_id, *key)}" for key in voice_keys}

        grids = legacy.get("measure_grid", [])
        first_part = part_rows[0]["part_id"] if part_rows else None
        representative = [m for m in grids if m["part_id"] == first_part] or grids
        measure_map = {
            (m["part_id"], m["measure"]): f"measure_{stable_id(score_id, m['part_id'], i, m['measure'])}"
            for i, m in enumerate(grids)
        }
        display_measure_map = {
            m["measure"]: f"measure_{stable_id(score_id, 'global', i, m['measure'])}"
            for i, m in enumerate(representative)
        }

        source_refs: list[dict[str, Any]] = []
        note_events: list[dict[str, Any]] = []
        rest_events: list[dict[str, Any]] = []
        note_id_by_segment: dict[str, str] = {}
        event_ids_by_voice: dict[str, list[str]] = {value: [] for value in voice_map.values()}

        for ordinal, seg in enumerate(segment_rows):
            note_id = f"note_{stable_id(score_id, seg['segment_id'])}"
            note_id_by_segment[seg["segment_id"]] = note_id
            source_ref_id = f"sref_{stable_id(source_file_id, 'note', ordinal)}"
            source_refs.append(self._source_ref(source_ref_id, source_file_id, seg, ordinal))
            voice_id = voice_map[(seg["part_id"], seg["staff_id"], seg["voice_id"])]
            event_ids_by_voice[voice_id].append(note_id)
            onset = as_fraction(seg["onset_ql"])
            measure_grid = self._grid_for_event(grids, seg)
            measure_start = as_fraction(measure_grid["start_ql"]) if measure_grid else onset - (as_fraction(seg["beat"]) - 1)
            p = pitch_record(seg["pitch_spelling"])
            note_events.append({
                "note_id": note_id, "score_id": score_id,
                "part_id": part_map[seg["part_id"]],
                "display_staff_id": staff_map[(seg["part_id"], seg["staff_id"])],
                "voice_id": voice_id,
                "measure_id": display_measure_map.get(seg["measure"], measure_map.get((seg["part_id"], seg["measure"]))),
                "onset_in_measure": q(onset - measure_start), "global_onset_quarter": q(onset),
                "notated_duration_quarter": q(seg["duration_ql"]), "source_ref_id": source_ref_id,
                "written_pitch": p, "concert_pitch": dict(p),
                "tie_role": seg.get("tie_role", "none"),
                "grace": {"is_grace": as_fraction(seg["duration_ql"]) == 0, "order": None, "anchor_note_id": None, "slash": None},
                "chord_member": seg.get("chord_member_index") is not None,
                "chord_onset_group_id": None,
                "notation": seg.get("notations", {}),
            })

        for ordinal, rest in enumerate(rest_rows):
            rest_id = f"rest_{stable_id(score_id, rest['rest_id'])}"
            source_ref_id = f"sref_{stable_id(source_file_id, 'rest', ordinal)}"
            source_refs.append(self._source_ref(source_ref_id, source_file_id, rest, ordinal))
            voice_id = voice_map[(rest["part_id"], rest["staff_id"], rest["voice_id"])]
            event_ids_by_voice[voice_id].append(rest_id)
            onset = as_fraction(rest["onset_ql"])
            measure_grid = self._grid_for_event(grids, rest)
            measure_start = as_fraction(measure_grid["start_ql"]) if measure_grid else onset - (as_fraction(rest["beat"]) - 1)
            rest_events.append({
                "rest_id": rest_id, "score_id": score_id, "part_id": part_map[rest["part_id"]],
                "display_staff_id": staff_map[(rest["part_id"], rest["staff_id"])], "voice_id": voice_id,
                "measure_id": display_measure_map.get(rest["measure"], measure_map.get((rest["part_id"], rest["measure"]))),
                "onset_in_measure": q(onset - measure_start), "global_onset_quarter": q(onset),
                "notated_duration_quarter": q(rest["duration_ql"]), "source_ref_id": source_ref_id, "hidden": False,
            })

        sounding_events, tie_chains, attack_events = self._sound_contract(
            legacy.get("sounding_events", []), note_id_by_segment, note_events
        )
        chord_groups = self._chord_groups(note_events)
        chord_by_note = {note_id: group["chord_onset_group_id"] for group in chord_groups for note_id in group["note_ids"]}
        for event in note_events:
            event["chord_onset_group_id"] = chord_by_note.get(event["note_id"])

        measures = []
        for index, grid in enumerate(representative):
            time_signature = grid.get("time_signature") or "4/4"
            beats, beat_type = (int(x) for x in time_signature.split("/", 1))
            measures.append({
                "measure_id": display_measure_map[grid["measure"]],
                "printed_measure_number": str(grid["measure"]), "sequential_measure_index": index,
                "global_start_quarter": q(grid["start_ql"]),
                "nominal_duration_quarter": q(grid["nominal_duration_ql"]),
                "actual_duration_quarter": q(grid["actual_duration_ql"]),
                "pickup": bool(grid.get("is_implicit_or_pickup")),
                "time_signature": {"beats": beats, "beat_type": beat_type},
                "key_signature": {"fifths": None, "mode_hint": None}, "repeat_barline": None,
            })

        duration = max((as_fraction(e["sounding_end_ql"]) for e in legacy.get("sounding_events", [])), default=Fraction(0))
        return {
            "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION, "ir_document_id": ir_document_id,
            "source_files": [{"source_file_id": source_file_id, "sha256": raw_hash, "musicxml_version": None, "original_name": source.name}],
            "source_references": source_refs,
            "score": {"score_id": score_id, "source_file_id": source_file_id, "title": source.stem, "composer": None, "movement": None, "part_ids": list(part_map.values()), "measure_count": len(measures), "duration_quarters": q(duration), "pickup_measure": next((m["measure_id"] for m in measures if m["pickup"]), None), "metadata": {}},
            "parts": [{"part_id": part_map[p["part_id"]], "score_id": score_id, "source_part_id": p["part_id"], "instrument_name": p.get("name"), "instrument_family": None, "transposition_semitones": q(0), "staff_ids": [staff_map[k] for k in staff_keys if k[0] == p["part_id"]], "midi_program": None} for p in part_rows],
            "staves": [{"staff_id": staff_map[k], "part_id": part_map[k[0]], "staff_number": int(k[1]) if str(k[1]).isdigit() else 1, "voice_ids": [voice_map[v] for v in voice_keys if v[:2] == k], "clef_timeline": []} for k in staff_keys],
            "voices": [{"voice_id": voice_map[k], "part_id": part_map[k[0]], "default_staff_id": staff_map[k[:2]], "source_voice_number": k[2], "event_ids": event_ids_by_voice[voice_map[k]], "inference": None} for k in voice_keys],
            "measures": measures, "note_events": note_events, "rest_events": rest_events,
            "tie_chains": tie_chains, "sounding_events": sounding_events, "attack_events": attack_events,
            "chord_onset_groups": chord_groups, "extensions": [],
            "parser_manifest": {"parser_name": "musicanote-legacy-0.2-adapter", "parser_version": "0.1.0", "normalization_policy_version": "0.1.0", "options": {"source_schema": legacy.get("schema_version"), "unavailable_fields": ["source_xpath", "key_signature_timeline", "concert_transposition"]}},
            "validation_summary": {},
        }

    @staticmethod
    def _grid_for_event(grids: list[dict[str, Any]], event: dict[str, Any]) -> dict[str, Any] | None:
        return next((g for g in grids if g["part_id"] == event["part_id"] and g["measure"] == event["measure"]), None)

    @staticmethod
    def _source_ref(ref_id: str, source_file_id: str, event: dict[str, Any], ordinal: int) -> dict[str, Any]:
        return {"source_ref_id": ref_id, "source_file_id": source_file_id, "source_part_id": event["part_id"], "source_measure_number": str(event["measure"]), "source_voice": event["voice_id"], "source_staff": int(event["staff_id"]) if str(event["staff_id"]).isdigit() else None, "source_element_index": ordinal, "source_xpath": None, "local_fingerprint": event.get("segment_id") or event.get("rest_id")}

    @staticmethod
    def _sound_contract(legacy_events: list[dict[str, Any]], note_ids: dict[str, str], notes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        note_by_id = {n["note_id"]: n for n in notes}
        sounds, ties, attacks = [], [], []
        for item in legacy_events:
            source_note_ids = [note_ids[x] for x in item["segment_ids"] if x in note_ids]
            if not source_note_ids:
                continue
            sound_id = f"sound_{stable_id(item['sounding_event_id'])}"
            attack_note_id = note_ids[item["attack_segment_id"]]
            start, end = as_fraction(item["attack_onset_ql"]), as_fraction(item["sounding_end_ql"])
            tie_id = f"tie_{stable_id(sound_id)}" if len(source_note_ids) > 1 else None
            p = note_by_id[attack_note_id]["concert_pitch"]
            sounds.append({"sounding_event_id": sound_id, "source_note_ids": source_note_ids, "pitch": p, "span": {"start": q(start), "end": q(end)}, "sounding_duration": q(end - start), "attack_note_id": attack_note_id, "tie_chain_id": tie_id})
            attacks.append({"attack_event_id": f"attack_{stable_id(sound_id)}", "note_id": attack_note_id, "sounding_event_id": sound_id, "global_onset_quarter": q(start)})
            if tie_id:
                ties.append({"tie_chain_id": tie_id, "source_note_ids": source_note_ids, "sounding_pitch": p, "span": {"start": q(start), "end": q(end)}, "total_duration": q(end - start), "attack_note_id": attack_note_id})
        return sounds, ties, attacks

    @staticmethod
    def _chord_groups(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, Fraction], list[str]] = {}
        for note in notes:
            key = (note["voice_id"], Fraction(note["global_onset_quarter"]["numerator"], note["global_onset_quarter"]["denominator"]))
            grouped.setdefault(key, []).append(note["note_id"])
        result = []
        for (voice_id, onset), ids in grouped.items():
            if len(ids) > 1:
                result.append({"chord_onset_group_id": f"nog_{stable_id(voice_id, onset)}", "voice_id": voice_id, "global_onset_quarter": q(onset), "note_ids": ids})
        return result


def deterministic_evidence(ir: dict[str, Any]) -> list[dict[str, Any]]:
    """Recomputable vertical slices; no harmony, melody, or NCT labels."""
    points = sorted({Fraction(x["span"][edge]["numerator"], x["span"][edge]["denominator"]) for x in ir["sounding_events"] for edge in ("start", "end")})
    records = []
    for start, end in zip(points, points[1:]):
        active = [x for x in ir["sounding_events"] if Fraction(x["span"]["start"]["numerator"], x["span"]["start"]["denominator"]) <= start < Fraction(x["span"]["end"]["numerator"], x["span"]["end"]["denominator"])]
        attacked = [x for x in active if Fraction(x["span"]["start"]["numerator"], x["span"]["start"]["denominator"]) == start]
        midi = sorted(x["pitch"]["midi_pitch"] for x in active if x["pitch"]["midi_pitch"] is not None)
        records.append({"evidence_id": f"ev_slice_{stable_id(ir['score']['score_id'], start, end)}", "type": "vertical_slice", "span": {"start": q(start), "end": q(end)}, "active_sounding_event_ids": [x["sounding_event_id"] for x in active], "attacked_sounding_event_ids": [x["sounding_event_id"] for x in attacked], "pitch_classes": sorted(set(x % 12 for x in midi)), "bass_pitch": midi[0] if midi else None, "top_pitch": midi[-1] if midi else None, "vertical_note_count": len(active), "algorithm": {"name": "half-open-active-sounding-events", "version": "0.1.0"}})
    return records


def legacy_analysis_records(ir: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose provisional legacy harmony/key results through the v0.1 interface."""
    score_id = ir["score"]["score_id"]
    records: list[dict[str, Any]] = []
    global_key = analysis.get("global_key")
    if global_key:
        hypotheses = [{"label": global_key["label"], "confidence": max(0.0, min(1.0, float(global_key.get("correlation", 0))))}]
        hypotheses.extend({"label": x["label"], "confidence": max(0.0, min(1.0, float(x.get("correlation", 0))))} for x in global_key.get("alternatives", []))
        records.append({"schema_version": "0.1.0", "analysis_id": f"ana_key_{stable_id(score_id)}", "analysis_type": "global_key", "score_id": score_id, "target": {"span": {"start": q(0), "end": ir["score"]["duration_quarters"]}}, "hypotheses": hypotheses, "selected_hypothesis": 0, "evidence_refs": [], "status": "candidate", "engine": {"name": "music21-key-adapter", "version": "0.1.0", "config_hash": "default"}})
    for span in analysis.get("harmonic_spans", []):
        selected = span["selected"]
        hypotheses = [{"label": selected["label"], "confidence": selected["confidence"], "rationale": None}]
        hypotheses.extend({"label": x["label"], "confidence": x["confidence"], "rationale": None} for x in span.get("alternatives", []))
        records.append({"schema_version": "0.1.0", "analysis_id": f"ana_harmony_{stable_id(score_id, span['span_id'])}", "analysis_type": "harmony", "score_id": score_id, "target": {"span": {"start": q(Fraction(str(span["range"]["start_offset_ql"])).limit_denominator(16384)), "end": q(Fraction(str(span["range"]["end_offset_ql"])).limit_denominator(16384))}}, "hypotheses": hypotheses, "selected_hypothesis": 0, "evidence_refs": [], "status": "candidate", "engine": {"name": "music21-roman-adapter", "version": "0.1.0", "config_hash": "default"}})
    return records
