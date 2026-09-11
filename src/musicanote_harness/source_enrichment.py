from __future__ import annotations

from fractions import Fraction
from typing import Any
from xml.etree import ElementTree as ET


XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local(child.tag) == name]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in element if _local(child.tag) == name), None)


def _text(element: ET.Element, name: str, default: str | None = None) -> str | None:
    child = _child(element, name)
    return child.text.strip() if child is not None and child.text else default


def _q(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _written_pitch(note: ET.Element) -> dict[str, Any] | None:
    pitch = _child(note, "pitch")
    if pitch is None or not _text(pitch, "step") or not _text(pitch, "octave"):
        return None
    step = _text(pitch, "step")
    octave = int(_text(pitch, "octave"))
    alter = Fraction(_text(pitch, "alter", "0"))
    symbols = {Fraction(-2): "--", Fraction(-1): "-", Fraction(0): "", Fraction(1): "#", Fraction(2): "##"}
    spelling = f"{step}{symbols.get(alter, f'({alter})')}{octave}"
    natural_pc = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[step]
    midi = 12 * (octave + 1) + natural_pc + int(alter) if alter.denominator == 1 else None
    return {
        "spelling": spelling,
        "step": step,
        "alter": _q(alter),
        "octave": octave,
        "midi_pitch": midi,
        "pitch_class": midi % 12 if midi is not None else None,
    }


def enrich_from_mapped_musicxml(ir: dict[str, Any], mapped_musicxml: str) -> dict[str, Any]:
    """Add directly observed MusicXML notation facts to formal IR in place."""
    root = ET.fromstring(mapped_musicxml)
    ir["source_files"][0]["musicxml_version"] = root.get("version")
    notes = {event["note_id"]: event for event in ir["note_events"]}
    refs = {ref["source_ref_id"]: ref for ref in ir["source_references"]}
    measures = sorted(ir["measures"], key=lambda row: row["sequential_measure_index"])
    measure_by_printed: dict[str, list[dict[str, Any]]] = {}
    for measure in measures:
        measure_by_printed.setdefault(measure["printed_measure_number"], []).append(measure)

    staff_lookup: dict[tuple[str, str], str] = {}
    for part in ir["parts"]:
        source = part["source_part_id"]
        if "-Staff" in source:
            xml_part, number = source.rsplit("-Staff", 1)
        else:
            xml_part, number = source, "1"
        for staff_id in part["staff_ids"]:
            staff_lookup[(xml_part, number)] = staff_id
    if len({part_id for part_id, _ in staff_lookup}) == 1:
        only_xml_part = next(iter({part_id for part_id, _ in staff_lookup}))
    else:
        only_xml_part = None

    clefs: dict[str, list[dict[str, Any]]] = {staff["staff_id"]: [] for staff in ir["staves"]}
    directions: list[dict[str, Any]] = []
    notation_counts: dict[str, int] = {}
    active_key: dict[str, Any] = {"fifths": None, "mode_hint": None}
    active_time: dict[str, int] | None = None

    xml_parts = [element for element in root if _local(element.tag) == "part"]
    for part_index, part in enumerate(xml_parts):
        xml_part_id = part.get("id") or f"P{part_index + 1}"
        if only_xml_part and xml_part_id != only_xml_part:
            xml_part_id = only_xml_part
        printed_occurrences: dict[str, int] = {}
        divisions = 1
        for sequential_index, xml_measure in enumerate(_children(part, "measure")):
            printed = xml_measure.get("number", str(sequential_index + 1))
            occurrence = printed_occurrences.get(printed, 0)
            printed_occurrences[printed] = occurrence + 1
            candidates = measure_by_printed.get(printed, [])
            ir_measure = candidates[min(occurrence, len(candidates) - 1)] if candidates else (measures[sequential_index] if sequential_index < len(measures) else None)
            if ir_measure is None:
                continue
            measure_start = Fraction(ir_measure["global_start_quarter"]["numerator"], ir_measure["global_start_quarter"]["denominator"])
            cursor = Fraction(0)
            previous_onset = Fraction(0)
            note_ordinal = 0
            for element_index, element in enumerate(xml_measure):
                kind = _local(element.tag)
                if kind == "attributes":
                    raw_divisions = _text(element, "divisions")
                    if raw_divisions:
                        divisions = int(raw_divisions)
                    key = _child(element, "key")
                    if key is not None:
                        active_key = {"fifths": int(_text(key, "fifths", "0")), "mode_hint": _text(key, "mode")}
                    time = _child(element, "time")
                    if time is not None and _text(time, "beats") and _text(time, "beat-type"):
                        active_time = {"beats": int(_text(time, "beats", "4")), "beat_type": int(_text(time, "beat-type", "4"))}
                    for clef in _children(element, "clef"):
                        staff_number = clef.get("number", "1")
                        staff_id = staff_lookup.get((xml_part_id, staff_number))
                        if staff_id:
                            clefs[staff_id].append({"global_quarter": _q(measure_start), "sign": _text(clef, "sign"), "line": int(_text(clef, "line")) if _text(clef, "line") else None, "octave_change": int(_text(clef, "clef-octave-change")) if _text(clef, "clef-octave-change") else 0})
                elif kind == "backup":
                    cursor -= Fraction(int(_text(element, "duration", "0")), divisions)
                elif kind == "forward":
                    cursor += Fraction(int(_text(element, "duration", "0")), divisions)
                elif kind == "direction":
                    offset = Fraction(int(_text(element, "offset", "0")), divisions)
                    sound = _child(element, "sound")
                    words = [x.text.strip() for x in element.iter() if _local(x.tag) == "words" and x.text]
                    dynamic_names = [_local(x.tag) for parent in element.iter() if _local(parent.tag) == "dynamics" for x in parent]
                    directions.append({"part_source_id": xml_part_id, "measure_id": ir_measure["measure_id"], "global_quarter": _q(measure_start + cursor + offset), "staff": _text(element, "staff"), "placement": element.get("placement"), "tempo": float(sound.get("tempo")) if sound is not None and sound.get("tempo") else None, "dynamics": dynamic_names, "words": words})
                elif kind == "note":
                    chord_member = _child(element, "chord") is not None
                    grace = _child(element, "grace") is not None
                    onset = previous_onset if chord_member else cursor
                    if not chord_member:
                        previous_onset = onset
                    note_id = element.get("id") or element.get(XML_ID)
                    if note_id in notes:
                        event = notes[note_id]
                        source_written_pitch = _written_pitch(element)
                        if source_written_pitch is not None:
                            event["written_pitch"] = source_written_pitch
                        ref = refs[event["source_ref_id"]]
                        ref["source_part_id"] = xml_part_id
                        ref["source_measure_number"] = printed
                        ref["source_voice"] = _text(element, "voice")
                        ref["source_staff"] = int(_text(element, "staff", "1"))
                        ref["source_element_index"] = note_ordinal
                        ref["source_xpath"] = f"/score-partwise/part[{part_index + 1}]/measure[{sequential_index + 1}]/note[{note_ordinal + 1}]"
                        notation = event["notation"]
                        notation["accidental_display"] = _text(element, "accidental")
                        notation["stem"] = _text(element, "stem")
                        notation["beams"] = [{"number": beam.get("number", "1"), "value": beam.text.strip() if beam.text else None} for beam in _children(element, "beam")]
                        notations = _child(element, "notations")
                        notation["fermata"] = any(_local(x.tag) == "fermata" for x in notations) if notations is not None else False
                        notation["slurs"] = [{"number": x.get("number", "1"), "type": x.get("type")} for x in notations if _local(x.tag) == "slur"] if notations is not None else []
                        notation["tuplets"] = [{"number": x.get("number", "1"), "type": x.get("type")} for x in notations if _local(x.tag) == "tuplet"] if notations is not None else []
                        notation["articulations"] = [_local(x.tag) for container in notations if _local(container.tag) == "articulations" for x in container] if notations is not None else notation.get("articulations", [])
                        time_mod = _child(element, "time-modification")
                        notation["time_modification"] = {"actual_notes": int(_text(time_mod, "actual-notes")), "normal_notes": int(_text(time_mod, "normal-notes"))} if time_mod is not None and _text(time_mod, "actual-notes") and _text(time_mod, "normal-notes") else None
                        grace_element = _child(element, "grace")
                        event["grace"]["slash"] = grace_element.get("slash") == "yes" if grace_element is not None and grace_element.get("slash") else None
                        for field in ("fermata", "slurs", "tuplets", "articulations", "time_modification"):
                            value = notation.get(field)
                            if value:
                                notation_counts[field] = notation_counts.get(field, 0) + 1
                    note_ordinal += 1
                    if not chord_member and not grace:
                        cursor += Fraction(int(_text(element, "duration", "0")), divisions)
                elif kind == "barline":
                    repeat = _child(element, "repeat")
                    ending = _child(element, "ending")
                    ir_measure["repeat_barline"] = {"location": element.get("location"), "bar_style": _text(element, "bar-style"), "repeat_direction": repeat.get("direction") if repeat is not None else None, "repeat_times": int(repeat.get("times")) if repeat is not None and repeat.get("times") else None, "ending_number": ending.get("number") if ending is not None else None, "ending_type": ending.get("type") if ending is not None else None}
            ir_measure["key_signature"] = dict(active_key)
            if active_time is not None:
                ir_measure["time_signature"] = dict(active_time)

    for staff in ir["staves"]:
        staff["clef_timeline"] = clefs[staff["staff_id"]]
    ir["extensions"] = [extension for extension in ir.get("extensions", []) if extension.get("name") != "com.musicanote.source-directions"]
    ir["extensions"].append({"name": "com.musicanote.source-directions", "version": "0.1.0", "owner": "musicanote-parser", "schema_uri": "https://schemas.musicanote.com/extensions/source-directions/0.1.0", "payload": {"directions": directions}})
    return {"musicxml_version": root.get("version"), "note_locator_count": sum(1 for ref in refs.values() if ref.get("source_xpath")), "direction_count": len(directions), "clef_change_count": sum(len(rows) for rows in clefs.values()), "notation_counts": notation_counts}
