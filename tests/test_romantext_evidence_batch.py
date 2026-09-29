import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from music21 import chord, meter, stream

from musicanote_harness.romantext_evidence_batch import audit_romantext_evidence


class RomanTextEvidenceBatchTest(unittest.TestCase):
    def test_resumable_batch_writes_summary_and_candidates(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            score = stream.Score()
            part = stream.Part(id="P1")
            measure = stream.Measure(number=1)
            measure.timeSignature = meter.TimeSignature("4/4")
            measure.append(chord.Chord(["C3", "E4", "G4"], quarterLength=4))
            part.append(measure)
            score.append(part)
            score_path = folder / "score.musicxml"
            score.write("musicxml", fp=str(score_path))
            analysis = folder / "analysis_automatic.rntxt"
            analysis.write_text("Time Signature: 4/4\n\nm1 C: I\n", encoding="utf-8")
            digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            records = folder / "records.jsonl"
            records.write_text(
                json.dumps(
                    {
                        "analysis_path": str(analysis),
                        "score_path": str(score_path),
                        "corpus": "when-in-rome",
                        "status_counts": {"exact_coordinate": 1},
                        "analysis_sha256": digest(analysis),
                        "score_sha256": digest(score_path),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = folder / "audit"
            first = audit_romantext_evidence(records, output)
            self.assertEqual(first["complete_pairs"], 1)
            self.assertEqual(first["support_band_counts"]["strong_support"], 1)
            self.assertEqual(first["context_totals"]["records"], 1)
            self.assertEqual(first["context_totals"]["scored_boundaries"], 0)
            self.assertTrue((output / "romantext_evidence_pair_records.jsonl").is_file())
            second = audit_romantext_evidence(records, output)
            self.assertEqual(second["cache_reused_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
