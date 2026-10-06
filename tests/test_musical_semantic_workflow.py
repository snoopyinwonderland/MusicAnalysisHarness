"""Independent integration checks: preserved prose -> optional enrichment.

Synthetic input only. These are storage/coverage contracts, not musical gold.
"""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.musical_semantic_enrichment import (
    AXES, append_record, build_bound_claim, plan_coverage, validate_records,
)
from musicanote_harness.musical_semantic_intake import prepare_source_statements


def quarter(value):
    return {"numerator": value, "denominator": 1}


class MusicalSemanticWorkflowTests(unittest.TestCase):
    def prepare(self, directory):
        root = Path(directory) / "corpus"
        root.mkdir()
        path = root / "analysis.txt"
        path.write_text("Form: opening\nm1 I\nNote: passing tone over an arpeggio\nPedal: C m1 m3 b1\nm3 V\n", encoding="utf-8")
        return prepare_source_statements(path, corpus_root=root)

    def test_raw_prose_does_not_become_note_truth_or_missing_negative(self):
        with TemporaryDirectory() as directory:
            prepared = self.prepare(directory)
            originals = deepcopy(prepared)
            coverage = plan_coverage([prepared["case"]], prepared["records"])[0]
            self.assertEqual(prepared, originals)
            self.assertEqual(len(prepared["records"]), 3)
            note = next(record for record in prepared["records"]
                        if record["source_context"]["location"]["locator"]["native_tag"] == "Note")
            self.assertIsNone(note["claim"]["axis"])
            self.assertIsNone(note["claim"]["term"])
            self.assertIsNone(note["binding"])
            self.assertEqual(coverage["axis_states"]["harmonic_role"], "needs_alignment")
            self.assertEqual(coverage["axis_states"]["texture"], "not_assessed")
            self.assertEqual(set(coverage["missing_axes"]), set(AXES))
            for record in prepared["records"]:
                self.assertIsNone(record["confidence"])
                self.assertFalse(record["use_policy"]["training_eligible"])

    def test_old_cases_and_source_cases_keep_separate_denominators(self):
        with TemporaryDirectory() as directory:
            prepared = self.prepare(directory)
            legacy = {"case_id": "legacy-fixture", "case_sha256": "a" * 64,
                      "ir_ref": "old-ir-id", "ir_sha256": None}
            before = deepcopy(legacy)
            source_plan = plan_coverage([prepared["case"]], prepared["records"])
            legacy_plan = plan_coverage([legacy], prepared["records"])
            self.assertEqual(legacy, before)
            self.assertEqual(len(source_plan), 1)
            self.assertEqual(len(legacy_plan), 1)
            self.assertTrue(all(state == "not_assessed"
                                for state in legacy_plan[0]["axis_states"].values()))
            self.assertEqual(legacy_plan, plan_coverage([legacy], prepared["records"]))

    def test_future_bound_role_preserves_original_prose_and_retries(self):
        with TemporaryDirectory() as directory:
            prepared = self.prepare(directory)
            source = next(record for record in prepared["records"] if record["claim"]["axis"] is None)
            original_source = deepcopy(source)
            case = deepcopy(prepared["case"])
            case.update(score_id="synthetic-score", score_sha256="b" * 64,
                        ir_sha256="c" * 64, ir_schema_version="0.1.0", entity_ids=["sound-1"],
                        span={"start": quarter(0), "end": quarter(8)})
            binding = {"score_id": case["score_id"], "score_sha256": case["score_sha256"],
                       "ir_sha256": case["ir_sha256"], "ir_schema_version": case["ir_schema_version"],
                       "alignment_ref": "synthetic-alignment", "harmony_assumption_ref": None,
                       "target": {"entity_refs": ["sound-1"],
                                  "span": {"start": quarter(0), "end": quarter(2)}}}
            provenance = {"kind": "rule", "actor_id": None,
                          "producer": {"name": "synthetic-rule", "version": "0.1.0", "config_sha256": "d" * 64,
                                       "model_ref": None, "schema_ref": {"name": source["schema_name"], "version": "0.1.0"}}}
            bound = build_bound_claim(source_claim=source, binding=binding,
                                      axis="voice_role", term="melody", provenance=provenance)
            validate_records([source, bound], legacy_cases=[case])
            self.assertEqual(source, original_source)
            self.assertEqual(bound["source_context"]["raw_text"], source["source_context"]["raw_text"])
            self.assertEqual(bound["coverage_state"], "pending_review")
            self.assertFalse(bound["use_policy"]["training_eligible"])
            path = Path(directory) / "sidecar.jsonl"
            self.assertTrue(append_record(path, source, legacy_cases=[case]))
            self.assertTrue(append_record(path, bound, legacy_cases=[case]))
            previous_bytes = path.read_bytes()
            self.assertFalse(append_record(path, bound, legacy_cases=[case]))
            self.assertEqual(previous_bytes, path.read_bytes())
            stale = deepcopy(case)
            stale["ir_sha256"] = "e" * 64
            with self.assertRaises(ValueError):
                append_record(path, bound, legacy_cases=[stale])
            self.assertEqual(previous_bytes, path.read_bytes())
            coverage = plan_coverage([stale], [source, bound])[0]
            self.assertTrue(coverage["stale_record_ids"])
            self.assertNotEqual(coverage["axis_states"]["voice_role"], "covered")


if __name__ == "__main__":
    unittest.main()
