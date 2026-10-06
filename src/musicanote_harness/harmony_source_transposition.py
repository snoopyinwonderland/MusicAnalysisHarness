"""Source-only written-to-sounding pitch probes, not a Canonical IR migration.

Only initial, unambiguous transpose declarations are applied to a bounded set
of exactly located XML notes.  No duration/onset parser, instrument-name guess,
or implicit concert certification is provided.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable
import xml.etree.ElementTree as ET

import music21
from music21 import interval, pitch

from .harmony_orchestral_readiness import _child, _tag, _text, _xml_payload, local_cases
from .harmony_progression_evidence_trial import digest, write


VERSION = "harmony-source-transposition-probe-0.1.1"
STEPS = "CDEFGAB"
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
OFFICIAL_REFERENCES = {
    name: "https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/" + name + "/"
    for name in ("transpose", "diatonic", "chromatic", "octave-change", "attributes", "staff", "concert-score", "double")
}
OFFICIAL_REFERENCES["xsd"] = "https://www.w3.org/2021/06/musicxml40/listings/musicxml.xsd/"
REFERENCE_INTERPRETATION = {
    "direction": "Add source transpose to source written pitch, not the inverse.",
    "diatonic_steps": "diatonic + 7 * octave-change",
    "semitones": "chromatic + 12 * octave-change",
    "staff_scope": "Absent transpose number applies to all staves of the source part.",
    "position": "Mid-measure attributes use score order, not XML document order; later changes are deferred.",
    "optional_diatonic": "Legal in MusicXML but unsupported here: no enharmonic spelling is guessed.",
}


def _integer(text: str | None, field: str) -> int:
    if text is None or re.fullmatch(r"[+-]?\d+", text) is None:
        raise ValueError(f"missing_or_invalid_{field}")
    return int(text)


def _decimal(text: str | None, field: str) -> Fraction:
    if text is None or re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text) is None:
        raise ValueError(f"missing_or_invalid_{field}")
    return Fraction(text)


def _record(step: str, alter: int, octave: int) -> dict[str, Any]:
    midi = 12 * (octave + 1) + NATURAL[step] + alter
    symbol = "#" * alter if alter >= 0 else "b" * -alter
    return {"step": step, "alter": {"numerator": alter, "denominator": 1},
            "octave": octave, "spelling": f"{step}{symbol}{octave}", "midi_pitch": midi,
            "pitch_class": midi % 12}


def _deferred(reason: str, **extra: Any) -> dict[str, Any]:
    return {"status": "deferred", "reason": reason, "concert_pitch": None, **extra}


def parse_written_pitch(note: ET.Element) -> dict[str, Any]:
    pitch_nodes = [node for node in note if _tag(node) == "pitch"]
    if not pitch_nodes:
        return _deferred("no_pitched_note")
    if len(pitch_nodes) != 1:
        return _deferred("duplicate_source_pitch_elements", source_pitch_element_count=len(pitch_nodes),
                         source_pitch_xmls=[ET.tostring(node, encoding="unicode") for node in pitch_nodes])
    node = pitch_nodes[0]
    raw = {name: _text(node, name) for name in ("step", "alter", "octave")}
    counts = {name: sum(_tag(child) == name for child in node) for name in raw}
    presence = {name: count > 0 for name, count in counts.items()}
    source_fields = {"source_pitch_fields": raw, "source_pitch_field_presence": presence,
                     "source_pitch_field_counts": counts}
    duplicates = [name for name, count in counts.items() if count > 1]
    if duplicates:
        return _deferred("duplicate_source_pitch_fields", duplicate_fields=duplicates, **source_fields)
    try:
        if raw["step"] not in NATURAL:
            raise ValueError("invalid_written_step")
        octave = _integer(raw["octave"], "written_octave")
        if not 0 <= octave <= 9:
            raise ValueError("written_octave_outside_musicxml_range")
        # Only an absent optional element defaults to zero. An explicitly
        # empty element is malformed source, not a natural pitch observation.
        alter = _decimal(raw["alter"] if presence["alter"] else "0", "written_alter")
        if alter.denominator != 1:
            return _deferred("microtonal_written_pitch_unsupported", **source_fields)
        if abs(alter) > 2:
            return _deferred("written_accidental_beyond_double_unsupported", **source_fields)
        value = _record(raw["step"], int(alter), octave)
        if not 0 <= value["midi_pitch"] <= 127:
            return _deferred("written_midi_outside_supported_range", **source_fields)
        return {"status": "source_written_pitch_observed", "pitch_role": "written",
                "input_origin": "raw_source_xml_pitch_no_score_converter", **source_fields,
                "written_pitch": value}
    except (TypeError, ValueError, ZeroDivisionError) as error:
        return _deferred(str(error), **source_fields)


def declaration_interval(declaration: dict[str, Any]) -> dict[str, Any]:
    """Parse only explicit integer/12-TET declarations; never guess diatonic."""
    raw = declaration["source_fields"]
    duplicates = [name for name, count in declaration.get("source_field_counts", {}).items() if count > 1]
    if duplicates:
        return _deferred("duplicate_source_transpose_fields", duplicate_fields=duplicates)
    if declaration.get("double") is not None:
        return _deferred("octave_doubling_unsupported")
    try:
        diatonic = _integer(raw.get("diatonic"), "diatonic")
        chromatic = _decimal(raw.get("chromatic"), "chromatic")
        # The pure-helper convention treats None as absent when no source
        # presence map is supplied. XML scans always supply that map so an
        # explicit <octave-change/> cannot acquire an implicit zero.
        octave_present = declaration.get("source_field_presence", {}).get(
            "octave-change", raw.get("octave-change") is not None)
        octave = _integer(raw.get("octave-change") if octave_present else "0", "octave_change")
        if chromatic.denominator != 1:
            return _deferred("microtonal_transposition_unsupported")
        return {"status": "explicit_interval_supported", "diatonic": diatonic,
                "chromatic": int(chromatic), "octave_change": octave,
                "effective_diatonic_steps": diatonic + 7 * octave,
                "effective_semitones": int(chromatic) + 12 * octave,
                "octave_change_default": "absent_optional_element_is_zero" if not octave_present else None}
    except (ValueError, ZeroDivisionError) as error:
        return _deferred(str(error))


def transpose_written_pitch(written: dict[str, Any], declared: dict[str, Any]) -> dict[str, Any]:
    """Pure helper; input must be raw-source-observed written pitch, never concert."""
    if (written.get("status") != "source_written_pitch_observed"
            or written.get("pitch_role") != "written"
            or written.get("input_origin") != "raw_source_xml_pitch_no_score_converter"):
        return _deferred("written_input_not_verified")
    if declared.get("status") != "explicit_interval_supported":
        return _deferred(declared.get("reason", "explicit_interval_unavailable"))
    source = written["written_pitch"]
    try:
        alter = Fraction(source["alter"]["numerator"], source["alter"]["denominator"])
        if alter.denominator != 1:
            return _deferred("microtonal_written_pitch_unsupported")
        source_checked = _record(source["step"], int(alter), source["octave"])
        if source_checked != source:
            return _deferred("written_pitch_record_inconsistent")
        steps = declared["effective_diatonic_steps"]
        semitones = declared["effective_semitones"]
        if type(steps) is not int or type(semitones) is not int:
            return _deferred("interval_effective_values_not_integers")
        if (steps != declared["diatonic"] + 7 * declared["octave_change"]
                or semitones != declared["chromatic"] + 12 * declared["octave_change"]):
            return _deferred("declared_interval_record_inconsistent")
        target_coordinate = 7 * source["octave"] + STEPS.index(source["step"]) + steps
        octave, step_index = divmod(target_coordinate, 7)
        step = STEPS[step_index]
        target_midi = source["midi_pitch"] + semitones
        target_alter = target_midi - (12 * (octave + 1) + NATURAL[step])
        if not 0 <= octave <= 9 or not 0 <= target_midi <= 127:
            return _deferred("concert_pitch_outside_supported_range")
        if abs(target_alter) > 2:
            return _deferred("concert_accidental_beyond_double_unsupported")
        manual = _record(step, target_alter, octave)
        source_object = pitch.Pitch()
        source_object.step, source_object.octave = source["step"], source["octave"]
        source_object.accidental = pitch.Accidental(int(alter))
        if (source_object.step != source["step"] or source_object.octave != source["octave"]
                or Fraction(str(source_object.accidental.alter)) != alter or source_object.ps != source["midi_pitch"]):
            return _deferred("music21_written_input_mismatch")
        generic = 1 if steps == 0 else (abs(steps) + 1) * (1 if steps > 0 else -1)
        movement = interval.intervalFromGenericAndChromatic(interval.GenericInterval(generic),
                                                           interval.ChromaticInterval(semitones))
        # Disable music21's accidental-limit enharmonic respelling.  If it
        # cannot preserve our exact spelling, defer rather than substitute.
        target_object = movement.transposePitch(source_object, inPlace=False, maxAccidental=None)
        library_alter = Fraction(str(target_object.accidental.alter if target_object.accidental else 0))
        library = _record(target_object.step, int(library_alter), target_object.octave) if library_alter.denominator == 1 else None
        if library != manual or target_object.ps != target_midi:
            return _deferred("manual_music21_transposition_disagreement", manual_candidate=manual,
                             music21_candidate=library)
        return {"status": "probe_cross_check_passed", "written_pitch": dict(source), "concert_pitch": manual,
                "declared_interval": dict(declared), "cross_check": {"manual_formula_agrees": True,
                "music21_version": music21.__version__, "music21_interval_name": movement.directedName,
                "written_input_verified_before_transposition": True,
                "score_converter_used": False, "transposition_applied_once": True},
                "full_score_concert_normalization_certified": False, "ir_migrated": False}
    except Exception as error:
        return _deferred("transposition_cross_check_error", error_type=type(error).__name__, error=str(error))


def scan_source(path: Path) -> dict[str, Any]:
    payload, member = _xml_payload(path)
    root = ET.fromstring(payload)
    if _tag(root) != "score-partwise":
        raise ValueError("unsupported_source_score_type")
    source_hash = digest(path)
    concert_score = any(_tag(node) == "concert-score" for node in root.iter())
    listed = _child(root, "part-list")
    part_names = {} if listed is None else {node.get("id"): _text(node, "part-name") for node in listed if _tag(node) == "score-part"}
    source_parts = [node for node in root if _tag(node) == "part"]
    parts = []
    for part_index, part in enumerate(source_parts):
        declarations, notes = [], []
        for_part = any(_tag(node) == "for-part" for node in part.iter())
        instrument_change = any(_tag(node) == "instrument-change" for node in part.iter())
        for measure_index, measure in enumerate(node for node in part if _tag(node) == "measure"):
            note_ordinal, attributes_ordinal = 0, 0
            motion_before = False
            for element_index, element in enumerate(measure):
                if _tag(element) == "attributes":
                    attributes_ordinal += 1
                    transposition_ordinal = 0
                    for child in element:
                        if _tag(child) != "transpose":
                            continue
                        transposition_ordinal += 1
                        raw_number = child.get("number")
                        valid_staff = raw_number is None or (re.fullmatch(r"\+?\d+", raw_number) is not None and int(raw_number) > 0)
                        declaration = {
                            "declaration_id": f"tr_{hashlib.sha256(f'{source_hash}:{part_index}:{measure_index}:{element_index}:{transposition_ordinal}'.encode()).hexdigest()[:20]}",
                            "source_fields": {name: _text(child, name) for name in ("diatonic", "chromatic", "octave-change")},
                            "source_field_presence": {name: _child(child, name) is not None for name in ("diatonic", "chromatic", "octave-change")},
                            "source_field_counts": {name: sum(_tag(node) == name for node in child) for name in ("diatonic", "chromatic", "octave-change", "double")},
                            "staff_number": raw_number, "scope": "all_staves" if raw_number is None else "explicit_staff",
                            "staff_number_normalized": int(raw_number) if raw_number is not None and valid_staff else None,
                            "initial_before_timeline_motion": measure_index == 0 and not motion_before,
                            "staff_number_valid": valid_staff,
                            "double": None if _child(child, "double") is None else dict(_child(child, "double").attrib),
                            "source_ref": {"source_sha256": source_hash, "musicxml_archive_member": member,
                                "source_part_id": part.get("id"), "source_part_index": part_index,
                                "printed_measure_number": measure.get("number"), "sequential_measure_index": measure_index,
                                "source_element_index": element_index, "source_attributes_ordinal": attributes_ordinal - 1,
                                "source_transpose_ordinal": transposition_ordinal - 1,
                                "source_xpath": f"/score-partwise/part[{part_index + 1}]/measure[{measure_index + 1}]/attributes[{attributes_ordinal}]/transpose[{transposition_ordinal}]",
                                "source_xml_id": child.get("id") or child.get(XML_ID)},
                            "source_xml": ET.tostring(child, encoding="unicode"),
                        }
                        declaration["interval"] = declaration_interval(declaration)
                        declarations.append(declaration)
                elif _tag(element) == "note":
                    if _child(element, "pitch") is not None:
                        staff_count = sum(_tag(child) == "staff" for child in element)
                        notes.append({"written": parse_written_pitch(element), "source_staff": _text(element, "staff"),
                            "source_staff_element_count": staff_count,
                            "source_ref": {"source_sha256": source_hash, "musicxml_archive_member": member,
                                "source_part_id": part.get("id"), "source_part_index": part_index,
                                "printed_measure_number": measure.get("number"), "sequential_measure_index": measure_index,
                                "source_element_index": element_index, "source_note_ordinal": note_ordinal,
                                "source_xpath": f"/score-partwise/part[{part_index + 1}]/measure[{measure_index + 1}]/note[{note_ordinal + 1}]",
                                "source_xml_id": element.get("id") or element.get(XML_ID)},
                            "source_pitch_xml": ET.tostring(_child(element, "pitch"), encoding="unicode"),
                            "grace": _child(element, "grace") is not None, "chord_member": _child(element, "chord") is not None,
                            "cue": _child(element, "cue") is not None})
                    note_ordinal += 1
                    motion_before = True
                elif _tag(element) in {"backup", "forward"}:
                    motion_before = True
        parts.append({"source_part_id": part.get("id"), "source_part_index": part_index,
                      "part_name": part_names.get(part.get("id")), "declarations": declarations,
                      "pitched_notes": notes, "for_part_present": for_part, "instrument_change_present": instrument_change})
    return {"source_path": str(path), "source_sha256": source_hash, "source_musicxml_version": root.get("version"),
            "musicxml_archive_member": member, "source_part_count": len(parts), "concert_score_present": concert_score,
            "parts": parts}


def verify_note_location(root: ET.Element, probe: dict[str, Any]) -> dict[str, Any]:
    """Independently resolve both child-index and note-ordinal source locators."""
    ref = probe["source_ref"]
    try:
        for key in ("source_part_index", "sequential_measure_index", "source_element_index", "source_note_ordinal"):
            if type(ref[key]) is not int or ref[key] < 0:
                return {"status": "source_locator_mismatch", "reason": "invalid_source_ordinal"}
        part = [node for node in root if _tag(node) == "part"][ref["source_part_index"]]
        measure = [node for node in part if _tag(node) == "measure"][ref["sequential_measure_index"]]
        direct = list(measure)[ref["source_element_index"]]
        ordinal = [node for node in measure if _tag(node) == "note"][ref["source_note_ordinal"]]
        if (direct is not ordinal or _tag(direct) != "note" or part.get("id") != ref["source_part_id"]
                or measure.get("number") != ref["printed_measure_number"]
                or (direct.get("id") or direct.get(XML_ID)) != ref["source_xml_id"]
                or _text(direct, "staff") != probe["source_staff"]
                or sum(_tag(child) == "staff" for child in direct) != probe["source_staff_element_count"]
                or parse_written_pitch(direct) != probe["written"]):
            return {"status": "source_locator_mismatch", "reason": "source_note_identity_mismatch"}
        return {"status": "source_locator_verified", "source_ordinal_and_child_index_agree": True,
                "raw_written_pitch_unchanged": True, "timeline_onset_not_computed": True}
    except (IndexError, KeyError, TypeError):
        return {"status": "source_locator_mismatch", "reason": "source_note_locator_out_of_range"}


def probe_source(path: Path, probes_per_scope: int = 3) -> dict[str, Any]:
    if type(probes_per_scope) is not int or not 1 <= probes_per_scope <= 10:
        raise ValueError("probes_per_scope_must_be_integer_1_to_10")
    source = scan_source(path)
    payload, _ = _xml_payload(path)
    location_root = ET.fromstring(payload)
    part_records = []
    for part in source["parts"]:
        declarations = part["declarations"]
        reasons = []
        if source["concert_score_present"]:
            reasons.append("concert_score_encoding_unsupported_in_this_probe")
        if part["for_part_present"]:
            reasons.append("for_part_encoding_unsupported")
        if part["instrument_change_present"]:
            reasons.append("instrument_change_scope_requires_timeline_review")
        if any(not declaration["initial_before_timeline_motion"] for declaration in declarations):
            reasons.append("later_or_midmeasure_transposition_requires_score_order_timeline")
        if any(not declaration["staff_number_valid"] for declaration in declarations):
            reasons.append("invalid_transpose_staff_number")
        # Keep raw lexical values for traceability, but compare valid scope
        # identities as integers: 1, +1, and 01 are the same source staff.
        scope_keys = [declaration["staff_number_normalized"] for declaration in declarations
                      if declaration["staff_number_valid"]]
        if len(scope_keys) != len(set(scope_keys)) or (None in scope_keys and len(scope_keys) > 1):
            reasons.append("overlapping_or_repeated_transpose_scope")
        probes = []
        if not declarations:
            for note in part["pitched_notes"][:1]:
                probes.append({**note, "source_locator_check": verify_note_location(location_root, note),
                               "result": _deferred("no_source_transpose_declaration_not_concert_certified")})
        else:
            for declaration in declarations:
                valid_note_staff = lambda note: (note["source_staff"] is not None and
                    re.fullmatch(r"\+?\d+", note["source_staff"]) is not None and int(note["source_staff"]) > 0)
                matching = [note for note in part["pitched_notes"] if declaration["staff_number"] is None or
                            (valid_note_staff(note) and int(note["source_staff"]) == declaration["staff_number_normalized"])] if declaration["staff_number_valid"] else []
                declaration["matching_pitched_note_count"] = len(matching)
                declaration["missing_note_staff_count"] = sum(note["source_staff"] is None for note in part["pitched_notes"]) if declaration["staff_number"] is not None else 0
                ambiguous_staff = [note for note in part["pitched_notes"] if not valid_note_staff(note)] if declaration["staff_number"] is not None else []
                declaration["missing_or_invalid_note_staff_count"] = len(ambiguous_staff)
                for note in matching[:probes_per_scope]:
                    locator = verify_note_location(location_root, note)
                    result = (_deferred("exact_source_note_locator_not_verified") if locator["status"] != "source_locator_verified" else
                              _deferred(reasons[0], part_scope_blockers=list(reasons)) if reasons else
                              _deferred("duplicate_source_note_staff_elements") if note["source_staff_element_count"] > 1 else
                              _deferred("invalid_explicit_source_note_staff") if note["source_staff_element_count"] == 1 and not valid_note_staff(note) else
                              transpose_written_pitch(note["written"], declaration["interval"]))
                    probes.append({**note, "source_locator_check": locator,
                                   "declaration_ref": declaration["declaration_id"], "result": result})
                for note in ambiguous_staff[:1]:
                    probes.append({**note, "declaration_ref": declaration["declaration_id"],
                                   "source_locator_check": verify_note_location(location_root, note),
                                   "result": _deferred("missing_or_invalid_source_note_staff_for_staff_scope")})
                if not matching:
                    probes.append({"declaration_ref": declaration["declaration_id"],
                                   "result": _deferred("no_exact_staff_note_probe_available", part_scope_blockers=list(reasons))})
        part_records.append({key: value for key, value in part.items() if key != "pitched_notes"} |
                            {"observed_pitched_note_count": len(part["pitched_notes"]), "scope_blockers": reasons,
                             "probes": probes, "no_declaration_is_not_concert_certification": True})
    source.pop("parts")
    probes = [probe for part in part_records for probe in part["probes"]]
    return {**source, "version": VERSION, "parts": part_records,
            "summary": {"source_transpose_declarations": sum(len(part["declarations"]) for part in part_records),
                        "probe_records": len(probes), "probe_status_counts": dict(Counter(probe["result"]["status"] for probe in probes)),
                        "deferred_reason_counts": dict(Counter(probe["result"]["reason"] for probe in probes if probe["result"]["status"] == "deferred")),
                        "cross_check_passed_probes": sum(probe["result"]["status"] == "probe_cross_check_passed" for probe in probes)},
            "selection": "first bounded XML-order pitched notes per explicit source scope; one no-declaration control per part",
            "probes_per_scope": probes_per_scope, "global_onsets_or_tie_chains_computed": False,
            "full_score_normalization_certified": False, "harmonic_use_eligible": False,
            "ir_migrated": False, "dataset_classification": "unassigned_exploratory"}


def run_audit(corpus_root: Path, output: Path, probes_per_scope: int = 3,
              progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    if type(probes_per_scope) is not int or not 1 <= probes_per_scope <= 10:
        raise ValueError("probes_per_scope_must_be_integer_1_to_10")
    cases = local_cases(corpus_root)
    references = [corpus_root / "when-in-rome/README.md", corpus_root / "beethoven-symphonies/README.md"]
    source_files = [case.full_score_path for case in cases] + references
    code_files = [Path(__file__), Path(__file__).with_name("harmony_orchestral_readiness.py"),
                  Path(__file__).with_name("formal_ir.py"), Path(__file__).with_name("source_enrichment.py"),
                  Path(__file__).with_name("harmony_progression_evidence_trial.py")]
    frozen = {str(path): digest(path) for path in source_files}
    code_hashes = {str(path): digest(path) for path in code_files}
    output.mkdir(parents=True, exist_ok=False)
    contract = {"version": VERSION, "source_sha256": frozen, "code_sha256": code_hashes,
                "official_references": OFFICIAL_REFERENCES, "reference_verified_date": "2026-09-30",
                "implementation_interpretation": REFERENCE_INTERPRETATION, "music21_version": music21.__version__,
                "probes_per_scope": probes_per_scope, "scope": "declaration and bounded exact source note probes only",
                "core_adapter_readiness_policy_ui_modified": False, "source_files_modified": False,
                "ir_migration": False, "harmonic_accuracy_measured": False, "external_score_transmission": False,
                "training_or_gold_promotion": False, "existing_splits_rights_unchanged": True}
    write(output / "run-contract.json", contract)
    records = []
    for case in cases:
        if progress:
            progress(f"{case.case_id}: source transpose / exact written-note probes")
        try:
            result = probe_source(case.full_score_path, probes_per_scope)
            record = {"case_id": case.case_id, "family_source_key": case.family_source_key, "status": "audited", "result": result}
        except Exception as error:
            record = {"case_id": case.case_id, "status": "partial_error", "error_type": type(error).__name__, "error": str(error)}
        write(output / "cases" / f"{case.case_id}.json", record)
        records.append(record)
    changed_sources = [key for key, value in frozen.items() if digest(Path(key)) != value]
    changed_code = [key for key, value in code_hashes.items() if digest(Path(key)) != value]
    summary = {"audited_inventory_pairs": len(records), "audited_inventory_families": len({case.family_source_key for case in cases}),
               "source_declarations": sum(record.get("result", {}).get("summary", {}).get("source_transpose_declarations", 0) for record in records),
               "cross_check_passed_probes": sum(record.get("result", {}).get("summary", {}).get("cross_check_passed_probes", 0) for record in records),
               "probe_status_counts": dict(sum((Counter(record.get("result", {}).get("summary", {}).get("probe_status_counts", {})) for record in records), Counter())),
               "full_score_normalization_certified": 0, "harmonic_use_eligible": 0,
               "harmonic_accuracy_measured": False}
    report = {"schema_name": "musicanote-source-transposition-probe-audit", "schema_version": "0.1.0", "version": VERSION,
              "summary": summary, "records": records, "input_hashes_unchanged": not changed_sources,
              "code_hashes_unchanged": not changed_code, "changed_sources": changed_sources, "changed_code": changed_code,
              "limitations": ["Later/midmeasure and overlapping declaration scopes require a score-order timeline parser.",
                              "No absent declaration, optional diatonic, instrument-name or key-signature transposition guess.",
                              "Double/octave doubling, microtonal, concert-score/for-part and instrument changes are deferred.",
                              "Only bounded source note probes are converted; no all-note, tie, sounding-event, or IR migration.",
                              "No edition, beat-grid, harmony, dataset-policy, rights, split, training or gold validation."]}
    write(output / "report.json", report)
    if changed_sources or changed_code:
        raise ValueError("frozen_source_or_code_hash_changed")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--probes-per-scope", type=int, default=3)
    args = parser.parse_args()
    report = run_audit(args.corpus_root, args.output, args.probes_per_scope,
                       lambda message: print(message, flush=True))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
