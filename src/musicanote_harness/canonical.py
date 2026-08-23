from __future__ import annotations

import hashlib
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from music21 import chord, meter, note, stream


IR_SCHEMA_VERSION = "musicanote-canonical-ir-0.2"


def stable_id(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return Fraction(int(value.numerator), int(value.denominator))
    return Fraction(str(float(value))).limit_denominator(16384)


def rational(value: Any) -> str:
    value = fraction(value)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def as_fraction(value: str) -> Fraction:
    return Fraction(value)


def _part_id(part: stream.Part, index: int) -> str:
    return str(part.id or f"P{index + 1}")


def _voice_id(element: Any) -> str:
    voice = element.getContextByClass(stream.Voice)
    return str(voice.id) if voice is not None and voice.id is not None else "voice_0"


def _staff_id(part: stream.Part, element: Any) -> str:
    staff = getattr(element, "staffNumber", None) or getattr(part, "staffNumber", None) or 1
    return str(staff)


def _source_xml_id(element: Any) -> str | None:
    element_id = getattr(element, "id", None)
    if element_id is None or isinstance(element_id, int):
        return None
    return str(element_id)


def _notations(element: Any) -> dict[str, Any]:
    expressions = [x.__class__.__name__ for x in getattr(element, "expressions", [])]
    articulations = [x.__class__.__name__ for x in getattr(element, "articulations", [])]
    return {"articulations": articulations, "expressions": expressions}


def _iter_pitch_members(element: Any) -> Iterable[tuple[int | None, Any, str | None]]:
    if isinstance(element, note.Note):
        yield None, element.pitch, element.tie.type if element.tie else None
    elif isinstance(element, chord.Chord):
        for index, member in enumerate(element.notes):
            yield index, member.pitch, member.tie.type if member.tie else None


class CanonicalIRBuilder:
    """Builds observation-only IR. Musical interpretations belong elsewhere."""

    def build(self, score: stream.Score, source: str | Path) -> dict[str, Any]:
        source = Path(source)
        score_id = f"score_{stable_id(source.name, source.stat().st_size)}"
        parts = list(score.parts)
        segments: list[dict[str, Any]] = []
        rests: list[dict[str, Any]] = []
        measures: list[dict[str, Any]] = []

        for p_index, part in enumerate(parts):
            pid = _part_id(part, p_index)
            measures.extend(self._measure_grid(score, part, pid))
            for element_ordinal, element in enumerate(part.recurse().notesAndRests):
                measure_obj = element.getContextByClass(stream.Measure)
                if measure_obj is None:
                    continue
                measure_no = int(measure_obj.number or 0)
                onset = fraction(element.getOffsetInHierarchy(score))
                duration = fraction(element.quarterLength)
                beat = fraction(element.getOffsetInHierarchy(measure_obj)) + 1
                voice_id = _voice_id(element)
                staff_id = _staff_id(part, element)
                if isinstance(element, note.Rest):
                    rests.append({
                        "rest_id": f"rest_{stable_id(pid, staff_id, voice_id, measure_no, onset, duration, element_ordinal)}",
                        "part_id": pid, "staff_id": staff_id, "voice_id": voice_id,
                        "measure": measure_no, "beat": rational(beat),
                        "onset_ql": rational(onset), "duration_ql": rational(duration),
                        "source_xml_id": _source_xml_id(element),
                    })
                    continue
                for member_index, pitch, tie_role in _iter_pitch_members(element):
                    segment_id = f"seg_{stable_id(pid, staff_id, voice_id, measure_no, onset, pitch.nameWithOctave, element_ordinal, member_index)}"
                    segments.append({
                        "segment_id": segment_id,
                        "source_xml_id": _source_xml_id(element),
                        "part_id": pid, "staff_id": staff_id, "voice_id": voice_id,
                        "measure": measure_no, "beat": rational(beat),
                        "onset_ql": rational(onset), "duration_ql": rational(duration),
                        "end_ql": rational(onset + duration),
                        "pitch_spelling": pitch.nameWithOctave,
                        "pitch_name": pitch.name,
                        "octave": pitch.octave,
                        "midi": pitch.midi,
                        "tie_role": tie_role or "none",
                        "is_notated_attack": tie_role not in {"continue", "stop"},
                        "chord_member_index": member_index,
                        "notations": _notations(element),
                    })

        segments.sort(key=lambda x: (as_fraction(x["onset_ql"]), x["part_id"], x["staff_id"], x["voice_id"], x["midi"]))
        sounding_events, tie_issues = self._sounding_events(segments)
        atoms = self._harmonic_atoms(sounding_events)
        return {
            "schema_version": IR_SCHEMA_VERSION,
            "score_id": score_id,
            "source": {"file_name": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
            "parser_policy": {
                "time_unit": "quarter_length_rational",
                "interval_convention": "half_open_[start,end)",
                "timeline_mode": "notated",
                "pitch_basis": "written_as_imported",
                "ornament_realization": "not_expanded",
                "missing_directions": "preserve_as_null_do_not_infer",
            },
            "parts": [{"part_id": _part_id(p, i), "name": p.partName} for i, p in enumerate(parts)],
            "measure_grid": measures,
            "notated_note_segments": segments,
            "rest_events": rests,
            "sounding_events": sounding_events,
            "harmonic_atoms": atoms,
            "parser_issues": tie_issues,
        }

    def _measure_grid(self, score: stream.Score, part: stream.Part, pid: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        active_ts: meter.TimeSignature | None = None
        for measure_obj in part.getElementsByClass(stream.Measure):
            active_ts = measure_obj.timeSignature or active_ts or measure_obj.getContextByClass(meter.TimeSignature)
            start = fraction(measure_obj.getOffsetInHierarchy(score))
            nominal = fraction(active_ts.barDuration.quarterLength) if active_ts else fraction(measure_obj.barDuration.quarterLength)
            actual = fraction(measure_obj.highestTime)
            padding_left = fraction(getattr(measure_obj, "paddingLeft", 0))
            implicit = bool(getattr(measure_obj, "implicit", False) or padding_left > 0)
            result.append({
                "part_id": pid,
                "measure": int(measure_obj.number or 0),
                "start_ql": rational(start),
                "nominal_duration_ql": rational(nominal),
                "actual_duration_ql": rational(actual),
                "time_signature": active_ts.ratioString if active_ts else None,
                "is_implicit_or_pickup": implicit,
                "padding_left_ql": rational(padding_left),
            })
        return result

    def _sounding_events(self, segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        active: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        events: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []
        for seg in segments:
            key = (seg["part_id"], seg["staff_id"], seg["voice_id"], seg["pitch_spelling"])
            role = seg["tie_role"]
            current = active.get(key)
            if role == "start":
                if current:
                    current_end = as_fraction(current["sounding_end_ql"])
                    new_start = as_fraction(seg["onset_ql"])
                    if new_start < current_end:
                        issues.append({"code": "overlapping_tie_start", "segment_id": seg["segment_id"], "severity": "error"})
                    else:
                        issues.append({
                            "code": "unresolved_tie_in_notated_timeline",
                            "sounding_event_id": current["sounding_event_id"],
                            "severity": "warning",
                            "note": "May resolve across a repeat, ending, coda, or playback jump.",
                        })
                    events.append(current)
                current = self._new_sounding_event(seg, tied=True)
                active[key] = current
            elif role in {"continue", "stop"}:
                if current is None:
                    issues.append({
                        "code": "orphan_tie_continuation", "segment_id": seg["segment_id"], "severity": "warning",
                        "note": "May originate across a repeat, ending, coda, or playback jump.",
                    })
                    current = self._new_sounding_event(seg, tied=True)
                else:
                    current["segment_ids"].append(seg["segment_id"])
                    current["sounding_end_ql"] = seg["end_ql"]
                    current["crosses_measure_boundary"] = current["attack_measure"] != seg["measure"]
                if role == "stop":
                    events.append(current)
                    active.pop(key, None)
                else:
                    active[key] = current
            else:
                events.append(self._new_sounding_event(seg, tied=False))
        for current in active.values():
            issues.append({
                "code": "unresolved_tie_in_notated_timeline", "sounding_event_id": current["sounding_event_id"],
                "severity": "warning", "note": "May resolve across a repeat, ending, coda, or playback jump.",
            })
            events.append(current)
        events.sort(key=lambda x: (as_fraction(x["attack_onset_ql"]), x["pitch_midi"], x["sounding_event_id"]))
        return events, issues

    def _new_sounding_event(self, seg: dict[str, Any], tied: bool) -> dict[str, Any]:
        return {
            "sounding_event_id": f"se_{stable_id(seg['segment_id'], 'tie' if tied else 'single')}",
            "part_id": seg["part_id"], "staff_id": seg["staff_id"], "voice_id": seg["voice_id"],
            "pitch_spelling": seg["pitch_spelling"], "pitch_midi": seg["midi"],
            "segment_ids": [seg["segment_id"]], "attack_segment_id": seg["segment_id"],
            "attack_measure": seg["measure"], "attack_onset_ql": seg["onset_ql"],
            "sounding_end_ql": seg["end_ql"], "crosses_measure_boundary": False,
        }

    def _harmonic_atoms(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        starts: dict[Fraction, list[dict[str, Any]]] = defaultdict(list)
        ends: dict[Fraction, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            starts[as_fraction(event["attack_onset_ql"])].append(event)
            ends[as_fraction(event["sounding_end_ql"])].append(event)
        points = sorted(set(starts) | set(ends))
        atoms: list[dict[str, Any]] = []
        active: dict[str, dict[str, Any]] = {}
        for start, end in zip(points, points[1:]):
            if end <= start:
                continue
            released = ends.get(start, [])
            for event in released:
                active.pop(event["sounding_event_id"], None)
            attacked = starts.get(start, [])
            for event in attacked:
                active[event["sounding_event_id"]] = event
            active_events = list(active.values())
            pitch_midi = {e["pitch_spelling"]: e["pitch_midi"] for e in active_events}
            pitches = sorted(pitch_midi, key=pitch_midi.get)
            atoms.append({
                "atom_id": f"ha_{stable_id(start, end)}", "start_ql": rational(start), "end_ql": rational(end),
                "attacked_event_ids": [e["sounding_event_id"] for e in attacked],
                "active_event_ids": [e["sounding_event_id"] for e in active_events],
                "released_event_ids": [e["sounding_event_id"] for e in released],
                "active_pitches": pitches,
                "bass_pitch": min(active_events, key=lambda e: e["pitch_midi"])["pitch_spelling"] if active_events else None,
                "rest_state": not active_events,
            })
        return atoms
