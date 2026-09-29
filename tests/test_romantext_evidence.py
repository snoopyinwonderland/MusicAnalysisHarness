import tempfile
import unittest
from pathlib import Path

from music21 import chord, meter, stream

from musicanote_harness.romantext_import import prepare_romantext


class RomanTextEvidenceTest(unittest.TestCase):
    def test_compatible_and_incompatible_source_labels_are_evidence_bands_not_gold(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            score = stream.Score()
            part = stream.Part(id="P1")
            for number, pitches in ((1, ["C3", "E4", "G4"]), (2, ["D#3", "F#4", "A#4"])):
                measure = stream.Measure(number=number)
                if number == 1:
                    measure.timeSignature = meter.TimeSignature("4/4")
                measure.append(chord.Chord(pitches, quarterLength=4))
                part.append(measure)
            score.append(part)
            score_path = folder / "score.musicxml"
            score.write("musicxml", fp=str(score_path))
            analysis = folder / "analysis_automatic.rntxt"
            analysis.write_text("Time Signature: 4/4\n\nm1 C: I\nm2 I\n", encoding="utf-8")

            package = prepare_romantext(analysis, score_path)
            evidence = package["source_evidence"]
            self.assertEqual(evidence["input_policy"], "source_labels_visible_to_separate_evidence_scorer")
            self.assertEqual(evidence["records"][0]["support_band"], "strong_support")
            self.assertEqual(evidence["records"][0]["expected_tone_presence_ratio"], 1.0)
            self.assertEqual(evidence["records"][1]["support_band"], "weak_evidence")
            self.assertIn("not correctness", evidence["interpretation"])
            context = package["context_evidence"]
            self.assertEqual(context["records"][0]["next_raw_label"], "I")
            self.assertEqual(context["records"][0]["status"], "scored")
            self.assertEqual(context["records"][0]["observed_bass_motion_semitones"], 3)
            self.assertIn("does not revise labels", context["interpretation"])


if __name__ == "__main__":
    unittest.main()
