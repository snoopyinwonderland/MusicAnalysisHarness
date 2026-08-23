import json
import tempfile
import unittest
from pathlib import Path

from music21 import chord, key, meter, note, stream, tie

from musicanote_harness.core import MusicHarness, arrangement_plan, write_package
from musicanote_harness.formal_ir import FormalIRAdapter, deterministic_evidence
from musicanote_harness.engraving import render_musicxml_pages


class HarnessTest(unittest.TestCase):
    def make_score(self, path: Path) -> None:
        score = stream.Score(id="test")
        part = stream.Part(id="melody")
        part.append(meter.TimeSignature("4/4"))
        part.append(key.Key("C"))
        for number, pitches in enumerate((("C4", "E4", "G4"), ("D4", "F4", "G4"), ("B3", "D4", "G4"), ("C4", "E4", "C5")), 1):
            measure = stream.Measure(number=number)
            for pitch in pitches:
                measure.append(note.Note(pitch, quarterLength=1))
            measure.append(note.Rest(quarterLength=1) if number == 4 else chord.Chord(pitches, quarterLength=1))
            part.append(measure)
        score.append(part)
        score.write("musicxml", fp=str(path))

    def test_analysis_package_is_traceable_and_evidence_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.musicxml"
            self.make_score(source)
            result = MusicHarness().analyze(source)
            self.assertEqual(result["schema_version"], "musicanote-analysis-package-0.2")
            self.assertEqual(result["score"]["schema_version"], "musicanote-canonical-ir-0.2")
            self.assertTrue(result["score"]["notated_note_segments"])
            self.assertTrue(result["score"]["sounding_events"])
            self.assertTrue(result["score"]["harmonic_atoms"])
            self.assertEqual(result["score"]["parser_policy"]["interval_convention"], "half_open_[start,end)")
            self.assertTrue(result["analysis"]["harmonic_spans"])
            self.assertTrue(result["analysis"]["harmonic_spans"][0]["selected"]["evidence"])
            self.assertTrue(result["analysis"]["boundary_hypotheses"])
            plan = arrangement_plan(result)
            self.assertTrue(plan["phrases"])
            output = root / "package"
            write_package(result, output)
            for name in ("canonical_ir.json", "analysis_hypotheses.json", "run_manifest.json", "validation_report.json", "arrangement_plan.json"):
                self.assertTrue((output / name).exists())
                json.loads((output / name).read_text(encoding="utf-8"))

    def test_tied_segments_become_one_sounding_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "tied.musicxml"
            score = stream.Score(id="ties")
            part = stream.Part(id="P1")
            first = stream.Measure(number=1)
            first.timeSignature = meter.TimeSignature("4/4")
            attack = note.Note("C4", quarterLength=4)
            attack.tie = tie.Tie("start")
            first.append(attack)
            second = stream.Measure(number=2)
            continuation = note.Note("C4", quarterLength=2)
            continuation.tie = tie.Tie("stop")
            second.append(continuation)
            second.append(note.Rest(quarterLength=2))
            part.append([first, second])
            score.append(part)
            score.write("musicxml", fp=str(source))

            result = MusicHarness().analyze(source)
            ir = result["score"]
            c_segments = [s for s in ir["notated_note_segments"] if s["pitch_spelling"] == "C4"]
            self.assertEqual(len(c_segments), 2)
            self.assertTrue(c_segments[0]["is_notated_attack"])
            self.assertFalse(c_segments[1]["is_notated_attack"])
            c_events = [e for e in ir["sounding_events"] if e["pitch_spelling"] == "C4"]
            self.assertEqual(len(c_events), 1)
            self.assertEqual(len(c_events[0]["segment_ids"]), 2)
            self.assertEqual(c_events[0]["attack_onset_ql"], "0")
            self.assertEqual(c_events[0]["sounding_end_ql"], "6")
            self.assertTrue(c_events[0]["crosses_measure_boundary"])
            self.assertTrue(result["validation"]["valid"])

    def test_formal_adapter_preserves_tie_attack_and_exact_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "formal-tie.musicxml"
            score = stream.Score(id="formal")
            part = stream.Part(id="P1")
            first = stream.Measure(number=1)
            first.timeSignature = meter.TimeSignature("4/4")
            attack = note.Note("F#4", quarterLength=4)
            attack.tie = tie.Tie("start")
            first.append(attack)
            second = stream.Measure(number=2)
            continuation = note.Note("F#4", quarterLength=1)
            continuation.tie = tie.Tie("stop")
            second.append(continuation)
            second.append(note.Rest(quarterLength=3))
            part.append([first, second])
            score.append(part)
            score.write("musicxml", fp=str(source))

            legacy = MusicHarness().parse(source)["score"]
            formal = FormalIRAdapter().convert(legacy, source)
            self.assertEqual(formal["schema_name"], "musicanote-canonical-music-ir")
            self.assertEqual(formal["schema_version"], "0.1.0")
            self.assertEqual(len(formal["note_events"]), 2)
            self.assertEqual(len(formal["tie_chains"]), 1)
            self.assertEqual(len(formal["sounding_events"]), 1)
            self.assertEqual(len(formal["attack_events"]), 1)
            self.assertEqual(formal["note_events"][0]["written_pitch"]["spelling"], "F#4")
            self.assertEqual(formal["tie_chains"][0]["total_duration"], {"numerator": 5, "denominator": 1})
            slices = deterministic_evidence(formal)
            self.assertTrue(slices)
            self.assertEqual(slices[0]["pitch_classes"], [6])
            pages, mapping = render_musicxml_pages(source, formal)
            self.assertTrue(pages)
            self.assertTrue(mapping["complete"])
            self.assertEqual(mapping["rendered_canonical_id_count"], 2)
            self.assertIn(f'data-id="{formal["note_events"][0]["note_id"]}"', "".join(pages))


if __name__ == "__main__":
    unittest.main()
