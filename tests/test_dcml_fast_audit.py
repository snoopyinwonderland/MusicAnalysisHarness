import tempfile
import unittest
from pathlib import Path

from musicanote_harness.dcml_fast_audit import audit_pair


class DCMLFastAuditTest(unittest.TestCase):
    def _pair(self, folder: Path, harmony_duration: str):
        score = folder / "score.musicxml"
        measures = folder / "measures.tsv"
        notes = folder / "notes.tsv"
        harmonies = folder / "harmonies.tsv"
        score.write_text(
            '<score-partwise><part id="P1"><measure number="1"/><measure number="2"/></part></score-partwise>',
            encoding="utf-8",
        )
        measures.write_text(
            "mc\tmn\tquarterbeats\tduration_qb\ttimesig\n1\t1\t0\t4\t4/4\n2\t2\t4\t4\t4/4\n",
            encoding="utf-8",
        )
        notes.write_text(
            "mc\tquarterbeats\tduration_qb\tmidi\n1\t0\t4\t60\n2\t4\t4\t62\n",
            encoding="utf-8",
        )
        harmonies.write_text(
            "mc\tmn\tquarterbeats\tduration_qb\tlabel\tchord\tglobalkey\tlocalkey\tcadence\tphraseend\n"
            f"1\t1\t0\t{harmony_duration}\tI\tI\tC\tI\t\t\n",
            encoding="utf-8",
        )
        return {
            "pair_id": "dcml:test:score", "score_format": ".musicxml",
            "paths": {"score": str(score), "measures": str(measures), "notes": str(notes), "harmonies": str(harmonies)},
        }

    def test_consistent_table_is_only_a_preflight_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            result = audit_pair(self._pair(Path(folder), "4"))
            self.assertEqual(result["status"], "table_consistent_needs_score_alignment")
            self.assertEqual(result["harmony_rows"], 1)
            self.assertEqual(result["issue_counts"], {})

    def test_missing_harmony_duration_is_not_assumed_to_be_point(self):
        with tempfile.TemporaryDirectory() as folder:
            result = audit_pair(self._pair(Path(folder), ""))
            self.assertEqual(result["status"], "review_required")
            self.assertEqual(result["issue_counts"]["harmonies:missing_duration"], 1)
            self.assertNotIn("harmonies:invalid_time_or_mc", result["issue_counts"])

    def test_musescore_native_score_gets_table_audit_but_needs_conversion(self):
        with tempfile.TemporaryDirectory() as folder:
            pair = self._pair(Path(folder), "4")
            native = Path(folder) / "score.mscx"
            native.write_text(
                "<museScore><Score><Staff><Measure/><Measure/></Staff></Score></museScore>",
                encoding="utf-8",
            )
            pair["paths"]["score"] = str(native)
            pair["score_format"] = ".mscx"
            result = audit_pair(pair)
            self.assertEqual(result["score_measure_count"], 2)
            self.assertEqual(result["status"], "table_consistent_requires_score_conversion")


if __name__ == "__main__":
    unittest.main()
