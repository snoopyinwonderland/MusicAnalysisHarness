from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from musicanote_harness.harmony_source_transposition import (
    declaration_interval, parse_written_pitch, probe_source, scan_source,
    transpose_written_pitch, verify_note_location, run_audit,
)
from musicanote_harness.harmony_orchestral_readiness import AuditCase


def written(step="C", alter="0", octave="4"):
    note = ET.fromstring(f'<note><pitch><step>{step}</step><alter>{alter}</alter><octave>{octave}</octave></pitch></note>')
    return parse_written_pitch(note)


def declaration(d="-1", c="-2", o=None, double=None):
    return {"source_fields": {"diatonic": d, "chromatic": c, "octave-change": o}, "double": double}


def note(step="C", alter="0", octave="4", staff=None, extras="", identity=""):
    staff_xml = "" if staff is None else f"<staff>{staff}</staff>"
    return (f'<note{identity}>{extras}<pitch><step>{step}</step><alter>{alter}</alter><octave>{octave}</octave></pitch>'
            f'<duration>1</duration>{staff_xml}</note>')


def transpose(d="-1", c="-2", o=None, staff=None, double=""):
    number = "" if staff is None else f' number="{staff}"'
    diatonic = "" if d is None else f"<diatonic>{d}</diatonic>"
    octave = "" if o is None else f"<octave-change>{o}</octave-change>"
    return f"<transpose{number}>{diatonic}<chromatic>{c}</chromatic>{octave}{double}</transpose>"


def score(first_content, second_content="", defaults=""):
    second = "" if not second_content else f'<measure number="1">{second_content}</measure>'
    return ('<score-partwise version="4.0">' + defaults + '<part-list><score-part id="P1">'
            '<part-name>Synthetic</part-name></score-part></part-list><part id="P1">'
            f'<measure number="1">{first_content}</measure>{second}</part></score-partwise>')


class HarmonySourceTranspositionTest(unittest.TestCase):
    def test_manual_and_music21_exact_spelling_matrix(self):
        cases = [
            (("C", "0", "4"), ("-1", "-2", None), ("B", -1, 3, 58)),
            (("F", "1", "4"), ("-1", "-2", None), ("E", 0, 4, 64)),
            (("C", "-1", "4"), ("-1", "-2", None), ("B", -2, 3, 57)),
            (("C", "0", "4"), ("-1", "-2", "-1"), ("B", -1, 2, 46)),
            (("C", "0", "4"), ("0", "0", "1"), ("C", 0, 5, 72)),
            (("C", "0", "4"), ("0", "0", "-1"), ("C", 0, 3, 48)),
            (("B", "0", "4"), ("1", "1", None), ("C", 0, 5, 72)),
            (("C", "0", "4"), ("0", "-1", None), ("C", -1, 4, 59)),
            (("C", "0", "4"), ("1", "0", None), ("D", -2, 4, 60)),
            (("C", "0", "4"), ("-1", "0", None), ("B", 1, 3, 60)),
            (("C", "0", "4"), ("-1", "-2", "1"), ("B", -1, 4, 70)),
            (("C", "0", "4"), ("6", "10", "-1"), ("B", -1, 3, 58)),
            (("C", "0", "4"), ("7", "12", "-1"), ("C", 0, 4, 60)),
            (("B", "1", "3"), ("0", "0", None), ("B", 1, 3, 60)),
            (("F", "2", "4"), ("-2", "-3", None), ("D", 2, 4, 64)),
        ]
        for source, shift, expected in cases:
            with self.subTest(source=source, shift=shift):
                result = transpose_written_pitch(written(*source), declaration_interval(declaration(*shift)))
                self.assertEqual(result["status"], "probe_cross_check_passed", result)
                target = result["concert_pitch"]
                self.assertEqual((target["step"], target["alter"]["numerator"], target["octave"], target["midi_pitch"]), expected)
                self.assertTrue(result["cross_check"]["manual_formula_agrees"])
                self.assertTrue(result["cross_check"]["transposition_applied_once"])
                self.assertFalse(result["full_score_concert_normalization_certified"])

    def test_source_and_declared_records_are_not_mutated(self):
        source, shift = written("F", "1"), declaration_interval(declaration("-2", "-3"))
        frozen = deepcopy((source, shift))
        transpose_written_pitch(source, shift)
        self.assertEqual((source, shift), frozen)

    def test_concert_input_is_never_transposed_again(self):
        source = written()
        source["pitch_role"] = "concert"
        result = transpose_written_pitch(source, declaration_interval(declaration()))
        self.assertEqual(result["reason"], "written_input_not_verified")
        self.assertIsNone(result["concert_pitch"])

    def test_imported_converter_input_is_not_accepted_as_raw_written(self):
        source = written()
        source["input_origin"] = "music21_converter"
        self.assertEqual(transpose_written_pitch(source, declaration_interval(declaration()))["reason"], "written_input_not_verified")

    def test_inconsistent_midi_or_interval_is_deferred(self):
        source = written()
        source["written_pitch"]["midi_pitch"] = 61
        self.assertEqual(transpose_written_pitch(source, declaration_interval(declaration()))["reason"], "written_pitch_record_inconsistent")
        shift = declaration_interval(declaration())
        shift["effective_semitones"] = -1
        self.assertEqual(transpose_written_pitch(written(), shift)["reason"], "declared_interval_record_inconsistent")

    def test_missing_optional_diatonic_is_legal_but_not_guessed(self):
        result = declaration_interval(declaration(d=None))
        self.assertEqual(result["status"], "deferred")
        self.assertEqual(result["reason"], "missing_or_invalid_diatonic")

    def test_microtonal_written_or_transpose_are_deferred(self):
        self.assertEqual(written(alter="0.5")["reason"], "microtonal_written_pitch_unsupported")
        self.assertEqual(declaration_interval(declaration(c="-1.5"))["reason"], "microtonal_transposition_unsupported")

    def test_optional_written_alter_absent_is_zero(self):
        source = parse_written_pitch(ET.fromstring('<note><pitch><step>C</step><octave>4</octave></pitch></note>'))
        self.assertEqual(source["status"], "source_written_pitch_observed")
        self.assertEqual(source["written_pitch"]["alter"], {"numerator": 0, "denominator": 1})
        self.assertIsNone(source["source_pitch_fields"]["alter"])
        self.assertFalse(source["source_pitch_field_presence"]["alter"])

    def test_explicit_empty_written_alter_is_not_defaulted(self):
        for empty in ("<alter/>", "<alter></alter>", "<alter>  </alter>"):
            with self.subTest(empty=empty):
                source = parse_written_pitch(ET.fromstring(f'<note><pitch><step>C</step>{empty}<octave>4</octave></pitch></note>'))
                self.assertEqual(source["reason"], "missing_or_invalid_written_alter")
                self.assertTrue(source["source_pitch_field_presence"]["alter"])
                self.assertIsNone(source["concert_pitch"])
                xml = score('<attributes>' + transpose() + '</attributes>'
                            + note().replace("<alter>0</alter>", empty))
                result = self._probe(xml)
                self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                self.assertIn("written_input_not_verified", result["summary"]["deferred_reason_counts"])

    def test_optional_octave_change_absent_is_zero(self):
        result = self._probe(score('<attributes>' + transpose() + '</attributes>' + note()))
        declared = result["parts"][0]["declarations"][0]
        self.assertFalse(declared["source_field_presence"]["octave-change"])
        self.assertIsNone(declared["source_fields"]["octave-change"])
        self.assertEqual(declared["interval"]["octave_change"], 0)
        self.assertEqual(declared["interval"]["octave_change_default"], "absent_optional_element_is_zero")
        self.assertEqual(result["summary"]["cross_check_passed_probes"], 1)

    def test_explicit_empty_octave_change_is_not_defaulted(self):
        for empty in ("<octave-change/>", "<octave-change></octave-change>", "<octave-change>  </octave-change>"):
            with self.subTest(empty=empty):
                source_declaration = transpose().replace("</transpose>", empty + "</transpose>")
                result = self._probe(score('<attributes>' + source_declaration + '</attributes>' + note()))
                declared = result["parts"][0]["declarations"][0]
                self.assertTrue(declared["source_field_presence"]["octave-change"])
                self.assertEqual(declared["interval"]["reason"], "missing_or_invalid_octave_change")
                self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                self.assertIn("missing_or_invalid_octave_change", result["summary"]["deferred_reason_counts"])
                self.assertIsNone(result["parts"][0]["probes"][0]["result"]["concert_pitch"])

    def test_duplicate_transpose_fields_do_not_select_first_value(self):
        repeated = {
            "diatonic": "<diatonic>-1</diatonic><diatonic>0</diatonic>",
            "chromatic": "<chromatic>-2</chromatic><chromatic>0</chromatic>",
            "octave-change": "<octave-change/><octave-change>0</octave-change>",
            "double": "<double/><double above='yes'/>",
        }
        for field, content in repeated.items():
            with self.subTest(field=field):
                source_declaration = transpose()
                if field in {"diatonic", "chromatic"}:
                    value = "-1" if field == "diatonic" else "-2"
                    source_declaration = source_declaration.replace(f"<{field}>{value}</{field}>", content)
                else:
                    source_declaration = source_declaration.replace("</transpose>", content + "</transpose>")
                result = self._probe(score('<attributes>' + source_declaration + '</attributes>' + note()))
                declared = result["parts"][0]["declarations"][0]
                self.assertEqual(declared["source_field_counts"][field], 2)
                self.assertEqual(declared["interval"]["reason"], "duplicate_source_transpose_fields")
                self.assertEqual(declared["interval"]["duplicate_fields"], [field])
                self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                self.assertIsNone(result["parts"][0]["probes"][0]["result"]["concert_pitch"])

    def test_empty_required_transpose_fields_are_deferred(self):
        for field, value in (("diatonic", "-1"), ("chromatic", "-2")):
            for empty in (f"<{field}/>", f"<{field}>  </{field}>"):
                with self.subTest(field=field, empty=empty):
                    content = transpose().replace(f"<{field}>{value}</{field}>", empty)
                    result = self._probe(score('<attributes>' + content + '</attributes>' + note()))
                    self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                    self.assertEqual(result["parts"][0]["declarations"][0]["interval"]["reason"], f"missing_or_invalid_{field}")

    def test_duplicate_pitch_fields_and_pitch_elements_are_deferred(self):
        for field, original, content in (
            ("step", "C", "<step>C</step><step>D</step>"),
            ("alter", "0", "<alter>0</alter><alter>1</alter>"),
            ("alter", "0", "<alter/><alter>0</alter>"),
            ("octave", "4", "<octave>4</octave><octave>5</octave>"),
        ):
            with self.subTest(field=field, content=content):
                pitched_note = note().replace(f"<{field}>{original}</{field}>", content)
                result = self._probe(score('<attributes>' + transpose() + '</attributes>' + pitched_note))
                probe = result["parts"][0]["probes"][0]
                self.assertEqual(probe["written"]["reason"], "duplicate_source_pitch_fields")
                self.assertEqual(probe["written"]["source_pitch_field_counts"][field], 2)
                self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                self.assertIsNone(probe["result"]["concert_pitch"])
        extra_pitch = "<pitch><step>D</step><octave>4</octave></pitch>"
        result = self._probe(score('<attributes>' + transpose() + '</attributes>' + note().replace("</pitch>", "</pitch>" + extra_pitch)))
        probe = result["parts"][0]["probes"][0]
        self.assertEqual(probe["written"]["reason"], "duplicate_source_pitch_elements")
        self.assertEqual(probe["written"]["source_pitch_element_count"], 2)
        self.assertEqual(len(probe["written"]["source_pitch_xmls"]), 2)
        self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)

    def test_empty_required_pitch_fields_are_deferred(self):
        for field, value, reason in (("step", "C", "invalid_written_step"), ("octave", "4", "missing_or_invalid_written_octave")):
            for empty in (f"<{field}/>", f"<{field}>  </{field}>"):
                with self.subTest(field=field, empty=empty):
                    pitched_note = note().replace(f"<{field}>{value}</{field}>", empty)
                    result = self._probe(score('<attributes>' + transpose() + '</attributes>' + pitched_note))
                    self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                    self.assertEqual(result["parts"][0]["probes"][0]["written"]["reason"], reason)

    def test_double_is_not_interpreted_as_one_pitch(self):
        for double in ({}, {"above": "yes"}):
            result = declaration_interval(declaration(double=double))
            self.assertEqual(result["reason"], "octave_doubling_unsupported")

    def test_integer_xsd_fields_do_not_accept_decimal_or_scientific_notation(self):
        for d, c, o in (("1.0", "2", None), ("1", "2e0", None), ("1", "2", "1.0")):
            self.assertEqual(declaration_interval(declaration(d, c, o))["status"], "deferred")

    def test_midi_range_prevents_music21_octave_folding(self):
        self.assertEqual(written("B", "0", "9")["reason"], "written_midi_outside_supported_range")
        result = transpose_written_pitch(written("C", "0", "9"), declaration_interval(declaration("0", "0", "1")))
        self.assertEqual(result["reason"], "concert_pitch_outside_supported_range")

    def test_unsupported_accidental_does_not_silently_respelling(self):
        result = transpose_written_pitch(written("C", "2"), declaration_interval(declaration("0", "1")))
        self.assertEqual(result["reason"], "concert_accidental_beyond_double_unsupported")
        self.assertIsNone(result["concert_pitch"])

    def _probe(self, xml, count=3):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.musicxml"
            path.write_text(xml, encoding="utf-8")
            return probe_source(path, count)

    def test_initial_part_scope_exact_probes_and_raw_declaration(self):
        xml = score('<attributes>' + transpose() + '</attributes><note><rest/><duration>1</duration></note>'
                    + note(identity=' id="exact-note"') + note("D") + note("E") + note("F"))
        result = self._probe(xml, 2)
        self.assertEqual(result["summary"]["cross_check_passed_probes"], 2)
        part = result["parts"][0]
        declaration = part["declarations"][0]
        self.assertEqual(declaration["scope"], "all_staves")
        self.assertEqual(declaration["matching_pitched_note_count"], 4)
        self.assertIn("<chromatic>-2</chromatic>", declaration["source_xml"])
        first = part["probes"][0]
        self.assertEqual(first["source_ref"]["source_note_ordinal"], 1)
        self.assertEqual(first["source_ref"]["source_element_index"], 2)
        self.assertEqual(first["source_ref"]["source_xpath"], "/score-partwise/part[1]/measure[1]/note[2]")
        self.assertEqual(first["source_ref"]["source_xml_id"], "exact-note")
        self.assertEqual(first["source_locator_check"]["status"], "source_locator_verified")
        self.assertFalse(result["ir_migrated"])
        self.assertFalse(result["harmonic_use_eligible"])

    def test_staff_specific_initial_declarations_do_not_cross_staves(self):
        xml = score('<attributes><staves>2</staves>' + transpose(staff="1") + transpose("0", "0", "-1", staff="2")
                    + '</attributes>' + note(staff="1") + '<backup><duration>1</duration></backup>' + note(staff="2"))
        result = self._probe(xml)
        probes = result["parts"][0]["probes"]
        self.assertEqual(len(probes), 2)
        self.assertEqual(probes[0]["source_staff"], "1")
        self.assertEqual(probes[0]["result"]["concert_pitch"]["spelling"], "Bb3")
        self.assertEqual(probes[1]["source_staff"], "2")
        self.assertEqual(probes[1]["result"]["concert_pitch"]["spelling"], "C3")

    def test_all_staves_scope_includes_both_explicit_staves(self):
        result = self._probe(score('<attributes>' + transpose() + '</attributes>' + note(staff="1") + note(staff="2")))
        self.assertEqual(result["summary"]["cross_check_passed_probes"], 2)

    def test_missing_staff_for_specific_scope_is_not_defaulted(self):
        result = self._probe(score('<attributes>' + transpose(staff="2") + '</attributes>' + note()))
        reasons = result["summary"]["deferred_reason_counts"]
        self.assertIn("missing_or_invalid_source_note_staff_for_staff_scope", reasons)
        self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)

    def test_invalid_staff_declaration_or_note_does_not_guess_scope(self):
        bad_declaration = self._probe(score('<attributes>' + transpose(staff="bad") + '</attributes>' + note(staff="1")))
        self.assertIn("invalid_transpose_staff_number", bad_declaration["parts"][0]["scope_blockers"])
        bad_note = self._probe(score('<attributes>' + transpose(staff="1") + '</attributes>' + note(staff="1.0")))
        self.assertEqual(bad_note["summary"]["cross_check_passed_probes"], 0)

    def test_later_or_midmeasure_declaration_defers_even_earlier_probes(self):
        for xml in (
            score('<attributes>' + transpose() + '</attributes>' + note(), '<attributes>' + transpose("0", "0") + '</attributes>' + note()),
            score(note() + '<attributes>' + transpose() + '</attributes>' + note()),
            score('<forward><duration>1</duration></forward><attributes>' + transpose() + '</attributes>' + note()),
        ):
            result = self._probe(xml)
            self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
            self.assertIn("later_or_midmeasure_transposition_requires_score_order_timeline", result["parts"][0]["scope_blockers"])

    def test_overlapping_or_repeated_scope_is_deferred(self):
        for declarations in (transpose() + transpose(staff="1"), transpose(staff="1") + transpose(staff="1")):
            result = self._probe(score('<attributes>' + declarations + '</attributes>' + note(staff="1")))
            self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
            self.assertIn("overlapping_or_repeated_transpose_scope", result["parts"][0]["scope_blockers"])

    def test_lexical_staff_scope_aliases_do_not_bypass_overlap(self):
        for first, second in (("1", "+1"), ("1", "01"), ("+1", "01")):
            with self.subTest(first=first, second=second):
                declarations = transpose(staff=first) + transpose("0", "0", "-1", staff=second)
                result = self._probe(score('<attributes>' + declarations + '</attributes>' + note(staff="1")))
                part = result["parts"][0]
                self.assertEqual([item["staff_number"] for item in part["declarations"]], [first, second])
                self.assertEqual([item["staff_number_normalized"] for item in part["declarations"]], [1, 1])
                self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                self.assertIn("overlapping_or_repeated_transpose_scope", part["scope_blockers"])
                self.assertTrue(all(probe["result"]["concert_pitch"] is None for probe in part["probes"]))

    def test_staff_scope_alias_preserves_raw_and_matches_normalized_staff(self):
        result = self._probe(score('<attributes>' + transpose(staff="+01") + '</attributes>' + note(staff="01")))
        part = result["parts"][0]
        self.assertEqual(part["declarations"][0]["staff_number"], "+01")
        self.assertEqual(part["declarations"][0]["staff_number_normalized"], 1)
        self.assertEqual(part["probes"][0]["source_staff"], "01")
        self.assertEqual(result["summary"]["cross_check_passed_probes"], 1)

    def test_duplicate_and_explicit_empty_note_staff_is_deferred(self):
        for declared_staff in (None, "1"):
            for content in ("<staff>1</staff><staff>2</staff>", "<staff>1</staff><staff>1</staff>", "<staff/><staff>1</staff>", "<staff/>"):
                with self.subTest(declared_staff=declared_staff, content=content):
                    pitched_note = note().replace("</note>", content + "</note>")
                    result = self._probe(score('<attributes>' + transpose(staff=declared_staff) + '</attributes>' + pitched_note))
                    self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
                    self.assertTrue(all(probe["result"]["concert_pitch"] is None for probe in result["parts"][0]["probes"]))

    def test_no_declaration_remains_noncertifying_source_observation(self):
        result = self._probe(score(note()))
        self.assertEqual(result["summary"]["source_transpose_declarations"], 0)
        first = result["parts"][0]["probes"][0]
        self.assertEqual(first["written"]["written_pitch"]["spelling"], "C4")
        self.assertEqual(first["result"]["reason"], "no_source_transpose_declaration_not_concert_certified")
        self.assertIsNone(first["result"]["concert_pitch"])

    def test_concert_score_for_part_and_instrument_changes_are_deferred(self):
        examples = [
            score('<attributes>' + transpose() + '</attributes>' + note(), defaults='<defaults><concert-score/></defaults>'),
            score('<attributes><for-part/></attributes>' + note()),
            score('<attributes>' + transpose() + '</attributes><direction><sound><instrument-change id="other"/></sound></direction>' + note()),
        ]
        for xml in examples:
            result = self._probe(xml)
            self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
            self.assertTrue(result["parts"][0]["scope_blockers"])

    def test_grace_chord_cue_pitch_keeps_exact_source_facts(self):
        result = self._probe(score('<attributes>' + transpose() + '</attributes>' + note(extras='<grace/>')
                                   + note(extras='<chord/>') + note(extras='<cue/>')))
        self.assertEqual(result["summary"]["cross_check_passed_probes"], 3)
        probes = result["parts"][0]["probes"]
        self.assertTrue(probes[0]["grace"])
        self.assertTrue(probes[1]["chord_member"])
        self.assertTrue(probes[2]["cue"])
        self.assertFalse(result["global_onsets_or_tie_chains_computed"])

    def test_duplicate_printed_measures_resolve_by_sequential_source_index(self):
        xml = score('<attributes>' + transpose() + '</attributes>' + note("C"), note("D"))
        result = self._probe(xml)
        probes = result["parts"][0]["probes"]
        self.assertEqual([probe["source_ref"]["printed_measure_number"] for probe in probes], ["1", "1"])
        self.assertEqual([probe["source_ref"]["sequential_measure_index"] for probe in probes], [0, 1])
        self.assertTrue(all(probe["source_locator_check"]["status"] == "source_locator_verified" for probe in probes))

    def test_tampered_source_locator_or_pitch_is_rejected(self):
        xml = score('<attributes>' + transpose() + '</attributes>' + note("C") + note("D"))
        result = self._probe(xml)
        probe = deepcopy(result["parts"][0]["probes"][0])
        root = ET.fromstring(xml)
        probe["source_ref"]["source_note_ordinal"] = 1
        self.assertEqual(verify_note_location(root, probe)["status"], "source_locator_mismatch")
        probe["source_ref"]["source_note_ordinal"] = 0
        probe["written"]["written_pitch"]["midi_pitch"] = 61
        self.assertEqual(verify_note_location(root, probe)["status"], "source_locator_mismatch")

    def test_probe_bound_and_serializable_output(self):
        xml = score('<attributes>' + transpose() + '</attributes>' + note() * 6)
        result = self._probe(xml, 2)
        self.assertEqual(result["summary"]["probe_records"], 2)
        json.dumps(result, ensure_ascii=False)
        for count in (0, 11, True):
            with self.assertRaises(ValueError):
                self._probe(xml, count)

    def test_library_disagreement_or_exception_is_fail_closed(self):
        with patch("musicanote_harness.harmony_source_transposition.interval.intervalFromGenericAndChromatic", side_effect=ValueError("synthetic")):
            result = transpose_written_pitch(written(), declaration_interval(declaration()))
            self.assertEqual(result["reason"], "transposition_cross_check_error")
            self.assertIsNone(result["concert_pitch"])

    def _run_fixture(self, folder, xml):
        path = folder / "score.musicxml"
        path.write_text(xml, encoding="utf-8")
        for name in ("when-in-rome", "beethoven-symphonies"):
            directory = folder / name
            directory.mkdir()
            (directory / "README.md").write_text("Synthetic policy reference; no rights promotion.", encoding="utf-8")
        return AuditCase("synthetic_case", "synthetic_family", "1", folder / "unused_analysis.txt", path)

    def test_new_only_run_preserves_hashes_and_nonpromotion_contract(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            case = self._run_fixture(folder, score('<attributes>' + transpose() + '</attributes>' + note()))
            output = folder / "audit"
            with patch("musicanote_harness.harmony_source_transposition.local_cases", return_value=[case]):
                result = run_audit(folder, output)
                with self.assertRaises(FileExistsError):
                    run_audit(folder, output)
            self.assertTrue(result["input_hashes_unchanged"])
            self.assertTrue(result["code_hashes_unchanged"])
            self.assertEqual(result["summary"]["cross_check_passed_probes"], 1)
            self.assertEqual(result["summary"]["full_score_normalization_certified"], 0)
            contract = json.loads((output / "run-contract.json").read_text(encoding="utf-8"))
            self.assertIn("xsd", contract["official_references"])
            self.assertFalse(contract["core_adapter_readiness_policy_ui_modified"])
            self.assertTrue(contract["existing_splits_rights_unchanged"])

    def test_changed_input_is_detected_without_deleting_partial_result(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            case = self._run_fixture(folder, score('<attributes>' + transpose() + '</attributes>' + note()))
            output = folder / "audit"
            def changed(_message):
                case.full_score_path.write_text(score(note("D")), encoding="utf-8")
            with patch("musicanote_harness.harmony_source_transposition.local_cases", return_value=[case]):
                with self.assertRaisesRegex(ValueError, "frozen_source_or_code_hash_changed"):
                    run_audit(folder, output, progress=changed)
            result = json.loads((output / "report.json").read_text(encoding="utf-8"))
            self.assertFalse(result["input_hashes_unchanged"])
            self.assertEqual(result["changed_sources"], [str(case.full_score_path)])

    def test_parse_failure_is_preserved_and_invalid_probe_budget_writes_nothing(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            case = self._run_fixture(folder, "invalid XML")
            with patch("musicanote_harness.harmony_source_transposition.local_cases", return_value=[case]):
                result = run_audit(folder, folder / "audit")
                with self.assertRaises(ValueError):
                    run_audit(folder, folder / "invalid_budget", probes_per_scope=0)
            self.assertEqual(result["records"][0]["status"], "partial_error")
            self.assertEqual(result["summary"]["cross_check_passed_probes"], 0)
            self.assertFalse((folder / "invalid_budget").exists())


if __name__ == "__main__":
    unittest.main()
