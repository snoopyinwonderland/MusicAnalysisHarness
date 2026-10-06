import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_evidence_scoring_trial import run as previous_run
from musicanote_harness.harmony_functional_scoring_trial import run
from test_harmony_evidence_scoring_trial import setup
from test_harmony_lattice_recall import C, D


def prepared(folder, reference=C):
    paths, pins, ip, *_ = setup(folder, reference)
    previous_run(*paths, folder/"previous", **pins)
    new_paths = folder/"previous"/"report.json", paths[0], paths[3]
    names = "expected_previous_sha", "expected_recall_sha", "expected_integration_sha"
    new_pins = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in zip(names, new_paths)}
    return new_paths, new_pins, ip


class FunctionalTrialTests(unittest.TestCase):
    def test_actual_files_runner_preserves_parent_and_denominator(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip = prepared(folder); before = ip.read_bytes()
            result = run(*paths, folder/"new", **pins)
            self.assertTrue(result["complete"])
            self.assertEqual(result["candidate_coverage"]["old_lattice_hit_contexts"], 1)
            self.assertEqual(result["candidate_coverage"]["expanded_lattice_hit_contexts"], 1)
            self.assertEqual(result["summary"]["functional_supply_and_resolution"]["selected_correct_contexts"], 1)
            self.assertEqual(ip.read_bytes(), before); self.assertFalse(result["training_performed"])
            self.assertEqual(len(list((folder/"new").iterdir())), 2)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(*paths, folder/"new", **pins)

    def test_reference_change_does_not_change_new_predictions(self):
        results = []
        with TemporaryDirectory() as temp:
            for name, ref in (("a", C), ("b", D)):
                folder = Path(temp)/name; folder.mkdir(); paths, pins, _ = prepared(folder, ref)
                results.append(run(*paths, folder/"new", **pins))
        self.assertEqual(results[0]["records"][0]["selected_predictions"], results[1]["records"][0]["selected_predictions"])
        self.assertNotEqual(results[0]["summary"], results[1]["summary"])

    def test_physical_ir_change_rejected(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip = prepared(folder); ip.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "frozen_input_changed"):
                run(*paths, folder/"new", **pins)
            self.assertFalse((folder/"new").exists())

    def test_smoke_is_not_complete_or_full_accuracy(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, _ = prepared(folder)
            result = run(*paths, folder/"smoke", smoke_contexts=1, **pins)
            self.assertFalse(result["complete"]); self.assertFalse(result["independent_test_accuracy_measured"])

    def test_parent_prediction_cost_change_rejected(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, _ = prepared(folder)
            doc = json.loads(paths[0].read_text(encoding="utf-8"))
            doc["records"][0]["selected_predictions"]["source_evidence_music"]["score_cost"]["numerator"] += 1
            paths[0].write_text(json.dumps(doc), encoding="utf-8")
            pins["expected_previous_sha"] = hashlib.sha256(paths[0].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "old_selection_score_changed"):
                run(*paths, folder/"new", **pins)


if __name__ == "__main__":
    unittest.main()
