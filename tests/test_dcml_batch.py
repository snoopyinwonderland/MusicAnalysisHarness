import unittest

from musicanote_harness.dcml_batch import alignment_quality, quality_reasons


class DCMLBatchQualityTest(unittest.TestCase):
    def _report(self):
        return {
            "measure_alignment_issues": {},
            "note_alignment": {"source_note_rows": 100, "ir_note_events": 100, "matched_note_events": 100},
            "imported_annotations": 100,
            "exact_alignments": 100,
            "verified_transform_alignments": 0,
            "source_note_mapping": {"complete": True},
        }

    def test_quality_categories(self):
        report = self._report()
        self.assertEqual(alignment_quality(report), "validated_complete")
        report["exact_alignments"] = 97
        self.assertEqual(alignment_quality(report), "validated_partial")
        report["measure_alignment_issues"] = {"2": ["measure_start_mismatch"]}
        self.assertEqual(alignment_quality(report), "quarantined")
        self.assertEqual(quality_reasons(report), ["measure_alignment_issues"])

    def test_large_note_or_annotation_disagreement_is_quarantined(self):
        report = self._report()
        report["note_alignment"]["matched_note_events"] = 94
        self.assertEqual(alignment_quality(report), "quarantined")
        report = self._report()
        report["exact_alignments"] = 94
        self.assertEqual(alignment_quality(report), "quarantined")

    def test_printed_measure_mismatch_alone_is_not_quarantined(self):
        report = self._report()
        report["measure_alignment_issues"] = {"2": ["printed_measure_mismatch"]}
        report["exact_alignments"] = 0
        report["verified_transform_alignments"] = 100
        self.assertEqual(quality_reasons(report), [])
        self.assertEqual(alignment_quality(report), "validated_complete")


if __name__ == "__main__":
    unittest.main()
