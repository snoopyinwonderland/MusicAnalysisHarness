import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from music21 import chord, meter, note, stream

from musicanote_harness.dcml_import import parse_score_without_imported_harmony, prepare_dcml, write_dcml_package
from musicanote_harness.harmony_context import build_source_harmony_context, context_at


class DCMLImportTest(unittest.TestCase):
    def test_implicit_pickup_measure_rest_keeps_explicit_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pickup.musicxml"
            score = stream.Score()
            part = stream.Part(id="P1")
            pickup = stream.Measure(number=0)
            pickup.timeSignature = meter.TimeSignature("4/4")
            pickup.append(note.Rest(quarterLength=2))
            part.append(pickup)
            following = stream.Measure(number=1)
            following.append(note.Note("C4", quarterLength=4))
            part.append(following)
            score.append(part)
            score.write("musicxml", fp=str(path))
            document = ET.parse(path)
            first = document.getroot().find("./part/measure")
            first.set("implicit", "yes")
            first.find("./note/rest").set("measure", "yes")
            for extra in list(first.findall("note"))[1:]:
                first.remove(extra)
            document.write(path, encoding="utf-8", xml_declaration=True)
            original = path.read_bytes()
            parsed, _, _ = parse_score_without_imported_harmony(path)
            measures = list(parsed.parts[0].getElementsByClass(stream.Measure))
            self.assertEqual(measures[0].highestTime, 2)
            self.assertEqual(measures[1].offset, 2)
            self.assertEqual(path.read_bytes(), original)

    def _fixture(self, directory: Path) -> tuple[Path, Path, Path, Path]:
        score = stream.Score()
        for part_id, pitches in (("P1", ("C4", "E4", "G4")), ("P2", ("C3", "E3", "G3"))):
            part = stream.Part(id=part_id)
            part.partName = "piano"
            for number in (1, 2):
                measure = stream.Measure(number=number)
                if number == 1:
                    measure.timeSignature = meter.TimeSignature("4/4")
                measure.append(chord.Chord(pitches, quarterLength=4))
                part.append(measure)
            score.append(part)
        score_path = directory / "score.musicxml"
        score.write("musicxml", fp=str(score_path))
        xml = ET.parse(score_path)
        first_measure = xml.getroot().find("./part/measure")
        harmony = ET.Element("harmony")
        ET.SubElement(harmony, "function").text = "f.i{"
        ET.SubElement(harmony, "kind", text="").text = "none"
        first_measure.insert(1, harmony)
        xml.write(score_path, encoding="utf-8", xml_declaration=True)

        measures = directory / "measures.tsv"
        measures.write_text(
            "mc\tmn\tquarterbeats\tduration_qb\ttimesig\n"
            "1\t1\t0\t4\t4/4\n2\t2\t4\t4\t4/4\n", encoding="utf-8"
        )
        harmonies = directory / "harmonies.tsv"
        harmonies.write_text(
            "mc\tmn\tquarterbeats\tduration_qb\tlabel\tchord\tglobalkey\tlocalkey\tcadence\tphraseend\n"
            "1\t1\t0\t6\tI\tI\tC\tI\t\t\n"
            "2\t2\t4\t0\t{\t\tC\tI\t\t{\n"
            "2\t2\t6\t2\tV\tV\tC\tI\tHC\t}\n", encoding="utf-8"
        )
        notes = directory / "notes.tsv"
        lines = ["quarterbeats\tduration_qb\tmidi\tgracenote"]
        for onset in (0, 4):
            for midi in (60, 64, 67, 48, 52, 55):
                lines.append(f"{onset}\t4\t{midi}\t")
        notes.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return score_path, measures, harmonies, notes

    def test_cross_measure_harmony_and_point_marker_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self._fixture(Path(folder))
            original = paths[0].read_bytes()
            result = prepare_dcml(*paths)
            report = result["report"]
            self.assertEqual(paths[0].read_bytes(), original)
            self.assertEqual(report["score_measures"], 2)
            self.assertEqual(report["removed_harmony_elements_for_notation_parse"], 1)
            self.assertEqual(report["note_alignment"]["matched_note_events"], 12)
            self.assertTrue(report["source_note_mapping"]["complete"])
            self.assertEqual(report["source_notation_enrichment"]["note_locator_count"], 12)
            self.assertIsNone(result["ir"]["measures"][0]["key_signature"]["fifths"])
            self.assertEqual(report["exact_alignments"], 3)
            self.assertEqual(result["annotations"][0]["target"]["span"]["end"], {"numerator": 6, "denominator": 1})
            self.assertEqual(result["annotations"][1]["target"]["point"], {"numerator": 4, "denominator": 1})
            self.assertIsNone(result["annotations"][0]["source_confidence"])
            output = Path(folder) / "output"
            write_dcml_package(result, output)
            self.assertEqual(len((output / "alignment_records.jsonl").read_text().splitlines()), 3)
            self.assertEqual(json.loads((output / "preparation_report.json").read_text())["exact_alignments"], 3)
            context = build_source_harmony_context(result)
            self.assertEqual(context["annotated_duration_quarter"], {"numerator": 8, "denominator": 1})
            self.assertEqual(context_at(context, 5)["source_labels"][0]["raw_label"], "I")
            self.assertEqual(context_at(context, 7)["source_labels"][0]["raw_label"], "V")
            self.assertTrue(any(mark["phrase_mark_raw"] == "{" and mark["point"]["numerator"] == 4 for mark in context["cadence_phrase_marks"]))
            self.assertTrue((output / "source_harmony_context.json").exists())

    def test_note_disagreement_does_not_become_exact_alignment(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self._fixture(Path(folder))
            notes = paths[3]
            notes.write_text(notes.read_text(encoding="utf-8").replace("0\t4\t60\t", "1\t4\t60\t"), encoding="utf-8")
            result = prepare_dcml(*paths)
            self.assertEqual(result["report"]["note_alignment"]["source_only_note_events"], 1)
            self.assertEqual(result["alignments"][0]["mapping_status"], "ambiguous")
            self.assertIn("source_note_alignment_mismatch_in_span", result["alignments"][0]["diagnostics"])
            context = build_source_harmony_context(result)
            self.assertIn(result["annotations"][0]["annotation_id"], context["excluded_ambiguous_annotation_ids"])

    def test_optional_gracenote_column_may_be_absent(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self._fixture(Path(folder))
            notes = paths[3]
            notes.write_text(notes.read_text(encoding="utf-8").replace("\tgracenote", "").replace("\t\n", "\n"), encoding="utf-8")
            result = prepare_dcml(*paths)
            self.assertEqual(result["report"]["note_alignment"]["matched_note_events"], 12)

    def test_printed_measure_alias_is_verified_transform_not_ambiguity(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self._fixture(Path(folder))
            measures, harmonies = paths[1:3]
            measures.write_text(
                measures.read_text(encoding="utf-8").replace("1\t1\t", "1\tA\t", 1),
                encoding="utf-8",
            )
            harmonies.write_text(
                harmonies.read_text(encoding="utf-8").replace("1\t1\t", "1\tA\t", 1),
                encoding="utf-8",
            )
            result = prepare_dcml(*paths)
            self.assertEqual(result["alignments"][0]["mapping_status"], "verified_transform")
            self.assertIn("printed_measure_mismatch", result["alignments"][0]["diagnostics"])
            self.assertIn("harmony_printed_measure_mismatch", result["alignments"][0]["diagnostics"])
            self.assertEqual(result["report"]["measure_alignment_blocking_issues"], {})
            self.assertEqual(result["report"]["printed_measure_aliases"][0]["source_printed_measure_number"], "A")

    def test_harmony_mn_disagreement_with_measure_table_remains_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self._fixture(Path(folder))
            harmonies = paths[2]
            harmonies.write_text(
                harmonies.read_text(encoding="utf-8").replace("1\t1\t", "1\tA\t", 1),
                encoding="utf-8",
            )
            result = prepare_dcml(*paths)
            self.assertEqual(result["alignments"][0]["mapping_status"], "ambiguous")
            self.assertIn("harmony_measure_table_mn_mismatch", result["alignments"][0]["diagnostics"])

    def test_alternate_ending_requires_complete_written_coordinates(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self._fixture(Path(folder))
            measures = paths[1]
            content = measures.read_text(encoding="utf-8")
            content = content.replace("quarterbeats\tduration_qb", "quarterbeats\tquarterbeats_all_endings\tduration_qb")
            content = content.replace("1\t1\t0\t4", "1\t1\t0\t0\t4")
            content = content.replace("2\t2\t4\t4", "2\t2\t\t4\t4")
            measures.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported_written_repeat_timeline"):
                prepare_dcml(*paths)

    def test_all_endings_time_maps_to_written_score_not_performance_time(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self._fixture(Path(folder))
            measures, harmonies, notes = paths[1:]
            measures.write_text(
                "mc\tmn\tquarterbeats\tquarterbeats_all_endings\tduration_qb\ttimesig\n"
                "1\t1\t0\t0\t4\t4/4\n2\t2\t\t4\t4\t4/4\n", encoding="utf-8"
            )
            harmony_lines = harmonies.read_text(encoding="utf-8").splitlines()
            harmony_lines[0] = harmony_lines[0].replace("quarterbeats\tduration_qb", "quarterbeats\tquarterbeats_all_endings\tduration_qb")
            harmony_lines[1] = harmony_lines[1].replace("\t0\t6\t", "\t0\t0\t6\t")
            harmony_lines[2] = harmony_lines[2].replace("\t4\t0\t", "\t\t4\t0\t")
            harmony_lines[3] = harmony_lines[3].replace("\t6\t2\t", "\t\t6\t2\t")
            harmonies.write_text("\n".join(harmony_lines) + "\n", encoding="utf-8")
            note_lines = notes.read_text(encoding="utf-8").splitlines()
            note_lines[0] = note_lines[0].replace("quarterbeats\tduration_qb", "quarterbeats\tquarterbeats_all_endings\tduration_qb")
            for index, line in enumerate(note_lines[1:], 1):
                fields = line.split("\t")
                native = fields[0] if fields[0] == "0" else ""
                note_lines[index] = "\t".join((native, fields[0], *fields[1:]))
            notes.write_text("\n".join(note_lines) + "\n", encoding="utf-8")
            result = prepare_dcml(*paths)
            self.assertEqual(result["report"]["source_time_coordinate"], "quarterbeats_all_endings")
            self.assertEqual(result["report"]["note_alignment"]["matched_note_events"], 12)
            self.assertEqual(result["report"]["verified_transform_alignments"], 3)
            self.assertEqual(result["report"]["ambiguous_alignments"], 0)


if __name__ == "__main__":
    unittest.main()
