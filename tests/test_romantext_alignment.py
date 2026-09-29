import tempfile
import unittest
from pathlib import Path

from music21 import meter, note, stream

from musicanote_harness.romantext_alignment import align_romantext, choose_score
from musicanote_harness.harmony_overlay_artifact import _review_metadata
from musicanote_harness.romantext_import import prepare_romantext, write_romantext_package
from musicanote_harness.romantext_review import write_romantext_review_html


class RomanTextAlignmentTest(unittest.TestCase):
    def test_overlay_review_triage_is_sparse_and_evidence_based(self):
        ordinary = _review_metadata(
            {"support_band": "strong_support", "expected_tone_presence_ratio": 1.0,
             "chord_tone_duration_ratio": 0.9, "bass_matches_notated_inversion": True},
            {"possible_nct_resolution_count": 0},
        )
        ambiguous = _review_metadata(
            {"support_band": "mixed_evidence", "expected_tone_presence_ratio": 0.7,
             "chord_tone_duration_ratio": 0.5, "bass_matches_notated_inversion": False},
            {"possible_nct_resolution_count": 1},
        )
        urgent = _review_metadata(
            {"support_band": "weak_evidence", "expected_tone_presence_ratio": 0.4,
             "chord_tone_duration_ratio": 0.3, "bass_matches_notated_inversion": False},
            {},
        )
        self.assertEqual(ordinary, {"review_candidate": False, "review_priority": "none", "review_reasons": []})
        self.assertTrue(ambiguous["review_candidate"])
        self.assertEqual(ambiguous["review_priority"], "medium")
        self.assertIn("possible_nct_resolution", ambiguous["review_reasons"])
        self.assertEqual(urgent["review_priority"], "high")

    def _score(self, folder: Path) -> Path:
        score = stream.Score()
        part = stream.Part(id="P1")
        for number in (1, 2):
            measure = stream.Measure(number=number)
            if number == 1:
                measure.timeSignature = meter.TimeSignature("4/4")
            measure.append(note.Note("C4", quarterLength=4))
            part.append(measure)
        score.append(part)
        path = folder / "score.musicxml"
        score.write("musicxml", fp=str(path))
        return path

    def test_exact_measure_and_beat_coordinates(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            score = self._score(folder)
            analysis = folder / "analysis.rntxt"
            analysis.write_text(
                "Time Signature: 4/4\n\nm1 C: I b3 V\nm2 I\n", encoding="utf-8"
            )
            result = align_romantext(analysis, score)
            self.assertEqual(result["roman_events"], 3)
            self.assertEqual(result["status_counts"], {"exact_coordinate": 3})
            self.assertEqual(result["examples"][0]["target"]["start_quarter"], "0/1")

    def test_missing_printed_measure_stays_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            score = self._score(folder)
            analysis = folder / "analysis.rntxt"
            analysis.write_text("Time Signature: 4/4\n\nm3 C: I\n", encoding="utf-8")
            result = align_romantext(analysis, score)
            self.assertEqual(result["status_counts"], {"ambiguous": 1})
            self.assertEqual(result["diagnostic_counts"], {"printed_measure_missing_in_score": 1})

    def test_uncompressed_musicxml_is_preferred(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            (folder / "score.mxl").write_bytes(b"x")
            (folder / "score.musicxml").write_bytes(b"x")
            analysis = folder / "analysis.rntxt"
            analysis.write_text("m1 C: I\n", encoding="utf-8")
            self.assertEqual(choose_score(analysis, ["score.mxl", "score.musicxml"]).suffix, ".musicxml")

    def test_exact_events_become_external_annotations_and_review(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            score = self._score(folder)
            analysis = folder / "analysis_automatic.rntxt"
            analysis.write_text("Time Signature: 4/4\n\nm1 C: I b3 V\nm2 I\n", encoding="utf-8")
            package = prepare_romantext(analysis, score)
            self.assertEqual(package["report"]["exact_alignments"], 3)
            self.assertEqual(package["report"]["ambiguous_alignments"], 0)
            self.assertEqual(package["annotations"][0]["author_origin"], "machine")
            self.assertEqual(package["annotations"][0]["source_review_status"], "machine_generated_unreviewed")
            self.assertEqual(package["alignments"][0]["mapping_status"], "exact")
            output = folder / "output"
            write_romantext_package(package, output)
            review = write_romantext_review_html(package, ["<svg></svg>"], output / "romantext-review.html")
            self.assertTrue((output / "source_harmony_context.json").is_file())
            review_text = review.read_text(encoding="utf-8")
            self.assertTrue((output / "source_harmony_evidence.json").is_file())
            self.assertTrue((output / "source_harmony_context_evidence.json").is_file())
            self.assertTrue((output / "harmony_overlay_artifact.json").is_file())
            overlay = package["viewer_overlay"]
            self.assertTrue(overlay["layer"]["default_enabled"])
            self.assertEqual(overlay["layer"]["interaction_mode"], "ambiguity_review")
            self.assertEqual(overlay["layer"]["structure_influence"], "none")
            self.assertEqual(
                overlay["source_identity"],
                {
                    "score_sha256": package["report"]["source_sha256"]["score"],
                    "analysis_sha256": package["report"]["source_sha256"]["analysis"],
                },
            )
            self.assertEqual(len(overlay["items"]), 3)
            self.assertEqual(overlay["items"][0]["label"]["font_role"], "harmony_symbol_campania")
            self.assertIn("review_candidate", overlay["items"][0])
            self.assertIn(overlay["items"][0]["review_priority"], {"high", "medium", "none"})
            self.assertIn("RomanText Source Review", review_text)
            self.assertIn("악보 위 화성 구간", review_text)
            self.assertIn("마지막 attack", review_text)
            self.assertIn("악보 호환 증거", review_text)
            self.assertIn("전후 진행·해결 증거", review_text)


if __name__ == "__main__":
    unittest.main()
