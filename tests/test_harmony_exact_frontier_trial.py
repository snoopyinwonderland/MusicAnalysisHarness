from copy import deepcopy
from fractions import Fraction as F
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_exact_frontier_trial as trial
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.harmony_scored_decoder import Problem
from test_harmony_bounded_recovery import fixture, sample


class ExactFrontierTrialTests(unittest.TestCase):
    def disk_trial(self, mode):
        with TemporaryDirectory() as name:
            root = Path(name); source = root/"j3c"; source.mkdir()
            planned_root = root/"j3b"; planned_root.mkdir(); output = root/"output"
            ir = fixture(); s = sample(); ir_path = planned_root/"observation.json.gz"
            trial.write_packet(ir_path, ir)
            chosen = {"source_labels_used_for_selection": False, "segments": [{"span": s["span"],
                "root_spelling": ["C", 0], "members": [["C", 0], ["E", 0], ["G", 0]]}]}
            status = {"control": "selected_untrained_hypothesis", "source": "source_preflight_abstention",
                      "context": "bounded_plan_abstention"}.get(mode, "transition_budget_abstention")
            row = {"pair_id": "dcml:c:w", "work_family_id": "family", "collection_id": "c",
                "sample_id": s["sample_id"], "sample_span": s["span"], "plan_index": 0,
                "reference_binding_verified": mode != "source", "status": status,
                "selected_prediction": deepcopy(chosen) if mode == "control" else None, "elapsed_seconds": 1.0}
            packet = source/"prediction.json.gz"; trial.write_packet(packet, row)
            item = {"entry": {"pair_id": row["pair_id"]}, "observation_ir_path": str(ir_path),
                "observation_ir_content_sha256": _hash(ir), "blockers": ["source"] if mode == "source" else [],
                "plan": {"selected_samples": [{"sample": s, "plan_index": 0}]}}
            trial.write(planned_root/"frozen-plan.json", {"packages": [item]})
            trial.write(source/"run-contract.json", {"source_labels_used_at_inference": False,
                "baseline_source": str(planned_root), "code_pins": {}})
            trial.write(source/"prediction-freeze.json", {"contexts": 1, "labels_read": False,
                "prediction_hashes": {str(packet): trial.digest(packet)}})
            reference = [{"span": s["span"], "signature": None if mode == "source" else
                          [["C", 0], [["C", 0], ["E", 0], ["G", 0]]], "reason": None}]
            report_row = dict(row, reference_cells=reference, candidate_ceiling={"lattice_hit": None, "outcome": "unavailable"})
            report_row["evaluation"] = evaluate(native_reference(report_row), native_prediction(row["selected_prediction"], s["span"]),
                s["span"], selected=row["selected_prediction"] is not None)
            trial.write(source/"report.json", {"records": [report_row], "table": summarize([report_row]),
                "input_hashes": {str(ir_path): trial.digest(ir_path)}, "code_hashes": {}, "artifact_hashes": {}})
            real_load = trial.load
            def read(path):
                if Path(path) == source/"report.json":
                    seal = real_load(output/"prediction-freeze.json")
                    self.assertFalse(seal["labels_read"]); self.assertEqual(seal["contexts"], 1)
                    for p, h in seal["prediction_hashes"].items(): self.assertEqual(trial.digest(p), h)
                return real_load(path)
            def infer(observation, frozen):
                self.assertFalse((output/"prediction-freeze.json").exists())
                self.assertNotIn("reference_cells", observation); self.assertEqual(frozen, s)
                if mode == "error": raise ValueError("synthetic_error")
                if mode == "tamper": trial.write_packet(ir_path, {"tampered": True})
                return {"status": "selected_untrained_hypothesis", "selected_prediction": deepcopy(chosen)}, Problem((), (), 0, F(), "unavailable")
            with patch.object(trial, "BASELINE_REPORT_SHA", trial.digest(source/"report.json")), \
                    patch.object(trial, "load", side_effect=read), patch.object(trial, "infer", side_effect=infer) as mocked:
                if mode == "tamper":
                    with self.assertRaisesRegex(ValueError, "baseline_source_or_artifact_changed"): trial.run(source, output)
                    return
                summary = trial.run(source, output)
                self.assertEqual(mocked.call_count, int(mode not in ("control", "source", "context")))
            result = real_load(output/"report.json")
            self.assertEqual(result["records"][0]["reference_cells"], reference)
            if mode == "control": self.assertEqual(result["records"][0]["selected_prediction"], row["selected_prediction"])
            self.assertEqual(summary["table"]["contexts"], 1)
            if mode == "error": self.assertEqual(summary["status_counts"], {"execution_error": 1})
            else: self.assertEqual(summary["recovered_selections"], int(mode == "retry"))

    def test_predictions_sealed_before_reference_and_no_resampling(self):
        code = inspect.getsource(trial.run)
        self.assertLess(code.index('save(output/"prediction-freeze.json"'), code.index('baseline = read(source/"report.json"'))
        self.assertNotIn("freeze_score(", code)
        with TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "output_exists"): trial.run("missing", t)

    def test_budget_retry_recovers_without_reference(self): self.disk_trial("retry")
    def test_existing_selected_control_immutable(self): self.disk_trial("control")
    def test_source_preflight_not_retried(self): self.disk_trial("source")
    def test_long_context_limit_not_retried(self): self.disk_trial("context")
    def test_execution_error_keeps_denominator(self): self.disk_trial("error")
    def test_physical_source_tampering_rejected(self): self.disk_trial("tamper")


if __name__ == "__main__": unittest.main()
