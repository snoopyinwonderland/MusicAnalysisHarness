from __future__ import annotations

import copy
import re
from collections import defaultdict, deque
from fractions import Fraction
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ET.register_namespace("", "http://www.w3.org/2000/svg")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((x for x in element if _local(x.tag) == name), None)


def _text(element: ET.Element, name: str, default: str | None = None) -> str | None:
    child = _child(element, name)
    return child.text.strip() if child is not None and child.text else default


def _pitch_key(note: ET.Element) -> tuple[str, Fraction, int] | None:
    pitch = _child(note, "pitch")
    if pitch is None:
        return None
    step = _text(pitch, "step")
    octave = _text(pitch, "octave")
    if step is None or octave is None:
        return None
    return step, Fraction(_text(pitch, "alter", "0")), int(octave)


def musicxml_with_canonical_ids(source: str | Path, ir: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return a rendering-only MusicXML copy with Canonical IDs on note elements."""
    source = Path(source)
    root = ET.parse(source).getroot()
    score_id = ir["score"]["score_id"]
    xml_part_ids = [x.get("id") or f"P{index + 1}" for index, x in enumerate(x for x in root if _local(x.tag) == "part")]
    xml_part_names: dict[str, str] = {}
    for score_part in (x for x in root.iter() if _local(x.tag) == "score-part"):
        xml_id = score_part.get("id")
        if xml_id:
            for field in ("part-name", "part-abbreviation"):
                value = _text(score_part, field)
                if value:
                    xml_part_names[value.strip()] = xml_id
    part_source: dict[str, str] = {}
    source_staff: dict[str, str] = {}
    part_by_id = {part["part_id"]: part for part in ir["parts"]}
    for part in ir["parts"]:
        match = re.fullmatch(r"(.+)-Staff(\d+)", part["source_part_id"])
        normalized_part = match.group(1) if match else part["source_part_id"]
        if normalized_part not in xml_part_ids:
            normalized_part = xml_part_names.get(normalized_part, normalized_part)
        if normalized_part not in xml_part_ids and part.get("instrument_name"):
            normalized_part = xml_part_names.get(part["instrument_name"].strip(), normalized_part)
        if normalized_part not in xml_part_ids and len(xml_part_ids) == 1:
            normalized_part = xml_part_ids[0]
        part_source[part["part_id"]] = normalized_part
        for staff_id in part["staff_ids"]:
            source_staff[staff_id] = match.group(2) if match else str(next(x["staff_number"] for x in ir["staves"] if x["staff_id"] == staff_id))
    measure_printed = {measure["measure_id"]: measure["printed_measure_number"] for measure in ir["measures"]}

    candidates: dict[tuple[Any, ...], deque[str]] = defaultdict(deque)
    for event in sorted(ir["note_events"], key=lambda x: x["source_ref_id"]):
        p = event["written_pitch"]
        onset = Fraction(event["onset_in_measure"]["numerator"], event["onset_in_measure"]["denominator"])
        key = (
            part_source[event["part_id"]], measure_printed[event["measure_id"]],
            source_staff[event["display_staff_id"]], onset,
            p["step"], Fraction(p["alter"]["numerator"], p["alter"]["denominator"]), p["octave"],
        )
        candidates[key].append(event["note_id"])

    matched: list[str] = []
    unmatched_xml: list[dict[str, Any]] = []
    for part in (x for x in root.iter() if _local(x.tag) == "part"):
        part_id = part.get("id") or "P1"
        divisions = 1
        for measure in (x for x in part if _local(x.tag) == "measure"):
            measure_number = measure.get("number", "0")
            cursor = Fraction(0)
            previous_onset = Fraction(0)
            for element in measure:
                kind = _local(element.tag)
                if kind == "attributes":
                    raw = _text(element, "divisions")
                    if raw:
                        divisions = int(raw)
                elif kind == "backup":
                    cursor -= Fraction(int(_text(element, "duration", "0")), divisions)
                elif kind == "forward":
                    cursor += Fraction(int(_text(element, "duration", "0")), divisions)
                elif kind == "note":
                    chord_member = _child(element, "chord") is not None
                    grace = _child(element, "grace") is not None
                    onset = previous_onset if chord_member else cursor
                    if not chord_member:
                        previous_onset = onset
                    voice = _text(element, "voice", "voice_0")
                    staff = _text(element, "staff", "1")
                    pkey = _pitch_key(element)
                    if pkey is not None:
                        key = (part_id, measure_number, staff, onset, *pkey)
                        if candidates[key]:
                            note_id = candidates[key].popleft()
                            # Verovio preserves MusicXML's ordinary id attribute as
                            # MEI/SVG xml:id. MusicXML xml:id is not reliably retained.
                            element.set("id", note_id)
                            matched.append(note_id)
                        else:
                            unmatched_xml.append({"part": part_id, "measure": measure_number, "voice": voice, "staff": staff, "onset": str(onset), "pitch": [pkey[0], str(pkey[1]), pkey[2]]})
                    if not chord_member and not grace:
                        cursor += Fraction(int(_text(element, "duration", "0")), divisions)

    unmatched_ir = [note_id for queue in candidates.values() for note_id in queue]
    xml = ET.tostring(copy.deepcopy(root), encoding="unicode", xml_declaration=False)
    return xml, {"score_id": score_id, "matched_note_ids_in_source_order": matched, "matched_count": len(matched), "ir_note_count": len(ir["note_events"]), "unmatched_ir_note_ids": unmatched_ir, "unmatched_xml_notes": unmatched_xml, "complete": not unmatched_ir and not unmatched_xml}


def _mei_pitch(note: ET.Element) -> tuple[str, Fraction | None, int]:
    accidental_codes = {"n": 0, "s": 1, "f": -1, "ss": 2, "x": 2, "ff": -2, "ts": 3, "tf": -3}
    accidental = note.get("accid.ges") or note.get("accid")
    alter = Fraction(accidental_codes.get(accidental, 0)) if accidental is not None else None
    return (note.get("pname", "").upper(), alter, int(note.get("oct", "0")))


def _wrap_note_links(svg: str) -> str:
    root = ET.fromstring(svg)
    parent_by_child = {child: parent for parent in root.iter() for child in parent}
    for group in [x for x in root.iter() if _local(x.tag) == "g" and "note" in x.get("class", "").split() and x.get("data-id", "").startswith("note_")]:
        parent = parent_by_child[group]
        index = list(parent).index(group)
        link = ET.Element("{http://www.w3.org/2000/svg}a", {"href": f"#detail-{group.get('data-id')}", "class": "canonical-note-link"})
        parent.remove(group)
        link.append(group)
        parent.insert(index, link)
    return ET.tostring(root, encoding="unicode")


def render_musicxml_pages(source: str | Path, ir: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Render the original MusicXML with Verovio; do not reconstruct notation from IR."""
    try:
        import verovio
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("Verovio is required for engraved score review") from exc

    toolkit = verovio.toolkit()
    toolkit.setOptions({
        "inputFrom": "musicxml",
        "pageWidth": 1800,
        "pageHeight": 2500,
        "adjustPageHeight": True,
        "scale": 35,
        "breaks": "encoded",
        "svgHtml5": True,
        "removeIds": False,
    })
    rendering_xml, mapping = musicxml_with_canonical_ids(source, ir)
    if not toolkit.loadData(rendering_xml):
        raise ValueError(f"Verovio could not load MusicXML: {source}")
    mei_root = ET.fromstring(toolkit.getMEI())
    mei_notes = [x for x in mei_root.iter() if _local(x.tag) == "note"]
    canonical_by_id = {event["note_id"]: event for event in ir["note_events"]}
    source_order = mapping.pop("matched_note_ids_in_source_order")
    semantic_mismatches: list[dict[str, Any]] = []
    id_map: dict[str, str] = {}
    retained_ids = [mei_note.get(XML_ID) for mei_note in mei_notes]
    direct_id_mapping = len(mei_notes) == len(source_order) and all(note_id in canonical_by_id for note_id in retained_ids)
    if direct_id_mapping:
        for mei_note in mei_notes:
            note_id = mei_note.get(XML_ID)
            id_map[note_id] = note_id
            p = canonical_by_id[note_id]["written_pitch"]
            expected = (p["step"], Fraction(p["alter"]["numerator"], p["alter"]["denominator"]), p["octave"])
            actual = _mei_pitch(mei_note)
            pitch_matches = actual[0] == expected[0] and actual[2] == expected[2] and (actual[1] is None or actual[1] == expected[1])
            if not pitch_matches:
                semantic_mismatches.append({"canonical_note_id": note_id, "mei_id": mei_note.get(XML_ID), "expected": [expected[0], str(expected[1]), expected[2]], "actual": [actual[0], str(actual[1]), actual[2]]})
    elif len(mei_notes) == len(source_order):
        for mei_note, note_id in zip(mei_notes, source_order):
            p = canonical_by_id[note_id]["written_pitch"]
            expected = (p["step"], Fraction(p["alter"]["numerator"], p["alter"]["denominator"]), p["octave"])
            actual = _mei_pitch(mei_note)
            pitch_matches = actual[0] == expected[0] and actual[2] == expected[2] and (actual[1] is None or actual[1] == expected[1])
            if not pitch_matches:
                semantic_mismatches.append({"canonical_note_id": note_id, "mei_id": mei_note.get(XML_ID), "expected": [expected[0], str(expected[1]), expected[2]], "actual": [actual[0], str(actual[1]), actual[2]]})
            elif mei_note.get(XML_ID):
                id_map[mei_note.get(XML_ID)] = note_id
    else:
        semantic_mismatches.append({"code": "note_count_mismatch", "musicxml_mapped_notes": len(source_order), "mei_notes": len(mei_notes)})

    pages = [toolkit.renderToSVG(page_number) for page_number in range(1, toolkit.getPageCount() + 1)]
    if not semantic_mismatches:
        pages = [page for page in pages]
        for mei_id, canonical_id in id_map.items():
            pages = [page.replace(mei_id, canonical_id) for page in pages]
    mapping["mei_note_count"] = len(mei_notes)
    mapping["semantic_mismatches"] = semantic_mismatches
    mapping["direct_canonical_ids_retained"] = direct_id_mapping
    mapping["mei_to_canonical_id_count"] = len(id_map) if direct_id_mapping or not semantic_mismatches else 0
    rendered_ids = {event["note_id"] for event in ir["note_events"] if any(f'id="{event["note_id"]}"' in page or f'data-id="{event["note_id"]}"' in page for page in pages)}
    mapping["rendered_canonical_id_count"] = len(rendered_ids)
    mapping["missing_rendered_note_ids"] = sorted(set(mapping.get("unmatched_ir_note_ids", [])) | ({event["note_id"] for event in ir["note_events"]} - rendered_ids))
    # A retained Canonical ID is authoritative for traceability. Pitch changes
    # made by Verovio (for example octave-shift normalization) remain visible
    # as semantic diagnostics but do not invalidate an exact ID mapping.
    blocking_semantic_mismatch = bool(semantic_mismatches) and not direct_id_mapping
    mapping["complete"] = mapping["complete"] and not blocking_semantic_mismatch and not mapping["missing_rendered_note_ids"]
    return pages, mapping
