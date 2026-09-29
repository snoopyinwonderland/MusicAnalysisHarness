"""Prepare score-linked DCML harmony annotations without mutating source files.

This is a deliberately small, strict bridge for the written-score timeline. It
keeps imported interpretations separate from the observation-only Canonical IR.
"""

from __future__ import annotations

import csv
from collections import Counter
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from music21 import converter

from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter, q
from .engraving import musicxml_with_canonical_ids
from .source_enrichment import enrich_from_mapped_musicxml


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas"
ADAPTER_VERSION = "dcml-written-score-import-0.3.0"

# DCML's ``mn`` is a printed/display label, while ``mc`` is the chronological
# measure counter used for score alignment.  A disagreement in ``mn`` is not a
# timeline failure when mc, onset, duration, meter, and note events agree.  It
# must still remain visible as a verified coordinate transform.
NON_BLOCKING_ALIGNMENT_DIAGNOSTICS = frozenset({
    "printed_measure_mismatch",
    "harmony_printed_measure_mismatch",
})


def blocking_alignment_diagnostics(diagnostics: list[str]) -> list[str]:
    return [code for code in diagnostics if code not in NON_BLOCKING_ALIGNMENT_DIAGNOSTICS]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fraction(value: str) -> Fraction:
    return Fraction(value.strip())


def _from_q(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _source_time(row: dict[str, str], written_all_endings: bool) -> Fraction:
    column = "quarterbeats_all_endings" if written_all_endings else "quarterbeats"
    if not row.get(column):
        raise ValueError(f"Missing {column} for source row")
    return _fraction(row[column])


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _read_tsv(path: Path) -> list[tuple[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"Missing TSV header: {path}")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError(f"Extra TSV columns at line {reader.line_num}: {path}")
            rows.append((reader.line_num, {key: value or "" for key, value in row.items()}))
        return rows


def _require_columns(rows: list[tuple[int, dict[str, str]]], names: set[str], path: Path) -> None:
    if not rows:
        raise ValueError(f"No data rows: {path}")
    missing = names - rows[0][1].keys()
    if missing:
        raise ValueError(f"Missing columns in {path}: {', '.join(sorted(missing))}")


def parse_score_without_imported_harmony(score_path: Path) -> tuple[Any, int, dict[str, str]]:
    """Parse original notes while retaining `<harmony>` only in the source asset.

    music21 currently rejects some valid DCML function strings, such as `f.i{`.
    Removal is limited to the in-memory XML copy. Source part IDs are reapplied
    because music21 can replace both P1/P2 with the shared part-name `piano`.
    """
    root = ET.fromstring(score_path.read_bytes())
    if _tag(root) not in {"score-partwise", "score-timewise"}:
        raise ValueError(f"Expected MusicXML score root, found {_tag(root)}")
    source_part_ids = [part.attrib["id"] for part in root if _tag(part) == "part"]
    if not source_part_ids or len(source_part_ids) != len(set(source_part_ids)):
        raise ValueError("Missing or duplicate source part IDs")
    removed = 0
    for parent in root.iter():
        for child in list(parent):
            if _tag(child) == "harmony":
                parent.remove(child)
                removed += 1
    # music21 expands <rest measure="yes"> to a nominal full bar even when
    # MusicXML explicitly gives a shorter duration in an implicit pickup.
    # Keep the source untouched and let its explicit duration govern parsing.
    for measure in root.iter():
        if _tag(measure) != "measure" or measure.get("implicit") != "yes":
            continue
        for note in measure:
            if _tag(note) != "note" or not any(_tag(item) == "duration" for item in note):
                continue
            for rest in note:
                if _tag(rest) == "rest" and rest.get("measure") == "yes":
                    del rest.attrib["measure"]
    score = converter.parseData(ET.tostring(root, encoding="unicode"), format="musicxml")
    part_mapping: dict[str, str] = {}
    if len(score.parts) == len(source_part_ids):
        for part, source_id in zip(score.parts, source_part_ids):
            part.id = source_id
            part_mapping[source_id] = source_id
    else:
        # music21 may expose the two staves of one MusicXML piano part as
        # P1-Staff1/P1-Staff2. Preserve those distinct internal lanes and
        # record their shared source part rather than quietly merging them.
        for part in score.parts:
            candidates = [source_id for source_id in source_part_ids if str(part.id).startswith(source_id + "-Staff")]
            if len(candidates) != 1 or str(part.id) in part_mapping:
                raise ValueError("Unrecognized MusicXML-to-music21 part split")
            part_mapping[str(part.id)] = candidates[0]
        if set(part_mapping.values()) != set(source_part_ids):
            raise ValueError("A source MusicXML part disappeared during notation parsing")
    return score, removed, part_mapping


def _measure_alignment(
    rows: list[tuple[int, dict[str, str]]], measures: list[dict[str, Any]], written_all_endings: bool = False
) -> dict[int, tuple[dict[str, Any] | None, list[str]]]:
    result: dict[int, tuple[dict[str, Any] | None, list[str]]] = {}
    seen: set[int] = set()
    for _line, row in rows:
        mc = int(row["mc"])
        errors = []
        if mc in seen:
            errors.append("duplicate_mc")
        seen.add(mc)
        measure = measures[mc - 1] if 1 <= mc <= len(measures) else None
        if measure is None:
            errors.append("mc_outside_score")
        else:
            if measure["printed_measure_number"] != row["mn"]:
                errors.append("printed_measure_mismatch")
            if _from_q(measure["global_start_quarter"]) != _source_time(row, written_all_endings):
                errors.append("measure_start_mismatch")
            if _from_q(measure["actual_duration_quarter"]) != _fraction(row["duration_qb"]):
                errors.append("measure_duration_mismatch")
            if row["timesig"]:
                signature = measure["time_signature"]
                if row["timesig"] != f"{signature['beats']}/{signature['beat_type']}":
                    errors.append("time_signature_mismatch")
        result[mc] = (measure, errors)
    return result


def _note_alignment(rows: list[tuple[int, dict[str, str]]], ir: dict[str, Any],
                    written_all_endings: bool = False) -> tuple[dict[str, Any], set[Fraction]]:
    """Check score/TSV note events as a multiset, including pitch and duration.

    DCML decimal spellings such as 0.16666666666666666 represent rational
    tuplets. A reconstructed fraction is accepted only within 1e-10 quarter.
    """
    def native_fraction(value: str) -> Fraction:
        raw = _fraction(value)
        normalized = raw.limit_denominator(16384)
        if abs(raw - normalized) > Fraction(1, 10**10):
            raise ValueError(f"DCML note time is not a supported rational: {value}")
        return normalized

    source_notes = Counter(
        (native_fraction(row["quarterbeats_all_endings"] if written_all_endings else row["quarterbeats"]),
         native_fraction(row["duration_qb"]), int(row["midi"]))
        for _line, row in rows if row["midi"]
    )
    ir_notes = Counter(
        (_from_q(note["global_onset_quarter"]), _from_q(note["notated_duration_quarter"]), note["written_pitch"]["midi_pitch"])
        for note in ir["note_events"] if note["written_pitch"]["midi_pitch"] is not None
    )
    source_only, ir_only = source_notes - ir_notes, ir_notes - source_notes
    mismatch_times = {onset for onset, _duration, _midi in (*source_only.keys(), *ir_only.keys())}
    display = lambda values: [
        {"onset_quarter": str(onset), "duration_quarter": str(duration), "midi": midi, "count": count}
        for (onset, duration, midi), count in values.items()
    ]
    return ({
        "source_note_rows": sum(source_notes.values()),
        "ir_note_events": sum(ir_notes.values()),
        "matched_note_events": sum((source_notes & ir_notes).values()),
        "source_only_note_events": sum(source_only.values()),
        "ir_only_note_events": sum(ir_only.values()),
        "source_only_examples": display(source_only)[:20],
        "ir_only_examples": display(ir_only)[:20],
        "comparison_policy": "onset_duration_midi_multiset_rational_limit_16384_tolerance_1e-10_quarter",
    }, mismatch_times)


def prepare_dcml(
    score_path: str | Path, measure_path: str | Path, harmony_path: str | Path, note_path: str | Path
) -> dict[str, Any]:
    """Return a traceable pilot package; exact rows alone qualify for evaluation."""
    score_path, measure_path, harmony_path, note_path = map(Path, (score_path, measure_path, harmony_path, note_path))
    for path in (score_path, measure_path, harmony_path, note_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    measure_rows = _read_tsv(measure_path)
    harmony_rows = _read_tsv(harmony_path)
    note_rows = _read_tsv(note_path)
    _require_columns(measure_rows, {"mc", "mn", "quarterbeats", "duration_qb", "timesig"}, measure_path)
    _require_columns(
        harmony_rows,
        {"mc", "mn", "quarterbeats", "duration_qb", "label", "chord", "globalkey", "localkey", "cadence", "phraseend"},
        harmony_path,
    )
    # Some DCML subcorpora omit the optional gracenote column entirely.
    # The strict onset/duration/MIDI cross-check does not need that column.
    _require_columns(note_rows, {"quarterbeats", "duration_qb", "midi"}, note_path)
    alternate_ending_measures = [row["mc"] for _line, row in measure_rows
                                 if not row["quarterbeats"] and row.get("quarterbeats_all_endings")]
    written_all_endings = bool(alternate_ending_measures)
    if written_all_endings:
        for name, rows in (("measures", measure_rows), ("notes", note_rows), ("harmonies", harmony_rows)):
            if any(not row.get("quarterbeats_all_endings") for _line, row in rows):
                raise ValueError(f"unsupported_written_repeat_timeline: incomplete {name} all-endings coordinates")

    score, removed, part_mapping = parse_score_without_imported_harmony(score_path)
    legacy = CanonicalIRBuilder().build(score, score_path)
    ir = FormalIRAdapter().convert(legacy, score_path)
    split_staff_by_part: dict[str, int] = {}
    for part in ir["parts"]:
        internal_part = part["source_part_id"]
        match = re.fullmatch(r".+-Staff(\d+)", internal_part)
        if match:
            split_staff_by_part[part["part_id"]] = int(match.group(1))
        part["source_part_id"] = part_mapping[internal_part]
    for staff in ir["staves"]:
        if staff["part_id"] in split_staff_by_part:
            staff["staff_number"] = split_staff_by_part[staff["part_id"]]
    source_staff_by_ref = {
        note["source_ref_id"]: split_staff_by_part[note["part_id"]]
        for note in ir["note_events"]
        if note["part_id"] in split_staff_by_part
    }
    for ref in ir["source_references"]:
        if ref["source_part_id"] in part_mapping:
            ref["source_part_id"] = part_mapping[ref["source_part_id"]]
        if ref["source_ref_id"] in source_staff_by_ref:
            ref["source_staff"] = source_staff_by_ref[ref["source_ref_id"]]
    part_split = len(part_mapping) != len(set(part_mapping.values()))
    mapped_xml, source_note_mapping = musicxml_with_canonical_ids(score_path, ir)
    enrichment_report = enrich_from_mapped_musicxml(ir, mapped_xml)
    formal_schema = json.loads((SCHEMA_DIR / "canonical_music_ir.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(formal_schema).validate(ir)
    measure_map = _measure_alignment(measure_rows, ir["measures"], written_all_endings)
    source_mn_by_mc = {int(row["mc"]): row["mn"] for _line, row in measure_rows}
    printed_measure_aliases = [
        {
            "mc": mc,
            "measure_id": measure["measure_id"],
            "source_printed_measure_number": source_mn_by_mc[mc],
            "ir_printed_measure_number": measure["printed_measure_number"],
        }
        for mc, (measure, diagnostics) in measure_map.items()
        if measure is not None and "printed_measure_mismatch" in diagnostics
    ]
    note_report, note_mismatch_times = _note_alignment(note_rows, ir, written_all_endings)
    source_unmatched_ids = set(source_note_mapping["unmatched_ir_note_ids"])
    source_unmatched_times = {
        _from_q(note["global_onset_quarter"])
        for note in ir["note_events"] if note["note_id"] in source_unmatched_ids
    }
    source_hashes = {name: _sha256(path) for name, path in (
        ("score", score_path), ("measures", measure_path), ("harmonies", harmony_path), ("notes", note_path)
    )}
    track_id = f"dcml_{source_hashes['harmonies'][:20]}"
    score_end = max(
        (_from_q(m["global_start_quarter"]) + _from_q(m["actual_duration_quarter"]) for m in ir["measures"]),
        default=Fraction(0),
    )
    annotations = []
    alignments = []
    for line, row in harmony_rows:
        annotation_id = f"ann_{source_hashes['harmonies'][:12]}_{line}"
        diagnostics = []
        try:
            mc = int(row["mc"])
            start = _source_time(row, written_all_endings)
            duration = _fraction(row["duration_qb"])
            end = start + duration
            if duration < 0:
                diagnostics.append("negative_duration")
            if start < 0 or end > score_end:
                diagnostics.append("span_outside_score")
            measure, measure_errors = measure_map.get(mc, (None, ["mc_missing_in_measure_table"]))
            diagnostics.extend(measure_errors)
            if measure and row["mn"] != source_mn_by_mc.get(mc):
                diagnostics.append("harmony_measure_table_mn_mismatch")
            elif measure and row["mn"] != measure["printed_measure_number"]:
                diagnostics.append("harmony_printed_measure_mismatch")
            if measure:
                measure_start = _from_q(measure["global_start_quarter"])
                measure_end = measure_start + _from_q(measure["actual_duration_quarter"])
                if not (measure_start <= start < measure_end):
                    diagnostics.append("harmony_onset_outside_measure")
        except (ValueError, ZeroDivisionError, KeyError):
            mc, start, end, measure = None, None, None, None
            diagnostics.append("invalid_native_time")

        if start is not None and end is not None and not blocking_alignment_diagnostics(diagnostics):
            if any(start <= time < end if start < end else time == start for time in note_mismatch_times):
                diagnostics.append("source_note_alignment_mismatch_in_span")
            if any(start <= time < end if start < end else time == start for time in source_unmatched_times):
                diagnostics.append("source_note_locator_missing_in_span")

        blocking_diagnostics = blocking_alignment_diagnostics(diagnostics)

        target = ({
            "score_id": ir["score"]["score_id"],
            "ir_document_id": ir["ir_document_id"],
            **({"point": q(start)} if start == end else {"span": {"start": q(start), "end": q(end)}}),
        } if start is not None and end is not None and not any(code in blocking_diagnostics for code in (
            "negative_duration", "span_outside_score", "mc_missing_in_measure_table", "invalid_native_time", "harmony_onset_outside_measure"
        )) else None)
        annotation = {
            "annotation_id": annotation_id,
            "track_id": track_id,
            "source_asset_sha256": source_hashes["harmonies"],
            "source_locator": {"path": str(harmony_path), "line": line},
            "raw_label": row["label"],
            "raw_fields": row,
            "components": {key: row.get(key, "") for key in (
                "globalkey", "localkey", "chord", "special", "numeral", "form", "figbass", "cadence", "phraseend"
            )},
            "native_target": {key: row.get(key, "") for key in (
                "mc", "mn", "quarterbeats", "duration_qb", "mc_onset", "mn_onset", "timesig"
            )},
            "author_origin": "unknown",
            "source_review_status": "unknown",
            "source_confidence": None,
            "target": target,
        }
        overlapping = []
        attacked = []
        if target is not None:
            for sound in ir["sounding_events"]:
                sound_start = _from_q(sound["span"]["start"])
                sound_end = _from_q(sound["span"]["end"])
                if (sound_start <= start < sound_end if start == end else sound_start < end and start < sound_end):
                    overlapping.append(sound["sounding_event_id"])
                    if (sound_start == start if start == end else start <= sound_start < end):
                        attacked.append(sound["sounding_event_id"])
        alignment = {
            "alignment_id": f"align_{annotation_id}",
            "annotation_id": annotation_id,
            "ir_document_id": ir["ir_document_id"],
            "mapping_status": (
                "ambiguous" if target is None or blocking_diagnostics
                else "verified_transform" if part_split or written_all_endings or diagnostics
                else "exact"
            ),
            "method_version": ADAPTER_VERSION,
            "measure_id": measure["measure_id"] if measure else None,
            "target": target,
            "sounding_event_ids": overlapping,
            "attacked_sounding_event_ids": attacked,
            "diagnostics": diagnostics,
        }
        annotations.append(annotation)
        alignments.append(alignment)

    imported_schema = json.loads((SCHEMA_DIR / "imported_annotation.schema.json").read_text(encoding="utf-8"))
    alignment_schema = json.loads((SCHEMA_DIR / "alignment_record.schema.json").read_text(encoding="utf-8"))
    for record in annotations:
        Draft202012Validator(imported_schema).validate(record)
    for record in alignments:
        Draft202012Validator(alignment_schema).validate(record)
    exact = sum(item["mapping_status"] == "exact" for item in alignments)
    transformed = sum(item["mapping_status"] == "verified_transform" for item in alignments)
    report = {
        "adapter_version": ADAPTER_VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "source_paths": {"score": str(score_path), "measures": str(measure_path), "harmonies": str(harmony_path), "notes": str(note_path)},
        "source_sha256": source_hashes,
        "annotation_track_id": track_id,
        "removed_harmony_elements_for_notation_parse": removed,
        "source_part_mapping": part_mapping,
        "music21_part_split": part_split,
        "source_time_coordinate": "quarterbeats_all_endings" if written_all_endings else "quarterbeats",
        "alternate_ending_measure_count": len(alternate_ending_measures),
        "score_measures": len(ir["measures"]),
        "measure_table_rows": len(measure_rows),
        "imported_annotations": len(annotations),
        "exact_alignments": exact,
        "verified_transform_alignments": transformed,
        "ambiguous_alignments": len(alignments) - exact - transformed,
        "measure_alignment_issues": {str(mc): errors for mc, (_measure, errors) in measure_map.items() if errors},
        "measure_alignment_blocking_issues": {
            str(mc): blocking
            for mc, (_measure, errors) in measure_map.items()
            if (blocking := blocking_alignment_diagnostics(errors))
        },
        "measure_alignment_warnings": {
            str(mc): [code for code in errors if code in NON_BLOCKING_ALIGNMENT_DIAGNOSTICS]
            for mc, (_measure, errors) in measure_map.items()
            if any(code in NON_BLOCKING_ALIGNMENT_DIAGNOSTICS for code in errors)
        },
        "printed_measure_aliases": printed_measure_aliases,
        "note_alignment": note_report,
        "source_note_mapping": {
            "matched_count": source_note_mapping["matched_count"],
            "ir_note_count": source_note_mapping["ir_note_count"],
            "unmatched_ir_note_ids": source_note_mapping["unmatched_ir_note_ids"][:20],
            "unmatched_xml_notes": source_note_mapping["unmatched_xml_notes"][:20],
            "complete": source_note_mapping["complete"],
        },
        "source_notation_enrichment": enrichment_report,
        "annotation_input_policy": "import_only_no_analysis",
    }
    return {"ir": ir, "annotations": annotations, "alignments": alignments, "report": report}


def write_dcml_package(package: dict[str, Any], output: str | Path) -> None:
    from .harmony_context import build_source_harmony_context

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "canonical_music_ir.json").write_text(json.dumps(package["ir"], ensure_ascii=False, indent=2), encoding="utf-8")
    for name, records in (("imported_annotations.jsonl", package["annotations"]), ("alignment_records.jsonl", package["alignments"])):
        (output / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    (output / "preparation_report.json").write_text(json.dumps(package["report"], ensure_ascii=False, indent=2), encoding="utf-8")
    context = build_source_harmony_context(package)
    (output / "source_harmony_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
