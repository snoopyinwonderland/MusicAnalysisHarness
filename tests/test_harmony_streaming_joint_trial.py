from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_streaming_joint_trial as trial
from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture, sample


class StreamingTrialTests(unittest.TestCase):
    def test_only_resource_abstentions_eligible(self):
        old = {"status": "bounded_plan_abstention", "tile_plan": {"blockers": ["global_cell_budget_no_truncation"]}}
        self.assertTrue(trial.eligible({}, {}, old, {"accepted": True}))
        for field, value in (("status", "selected_untrained_hypothesis"), ("tile_plan", {"blockers": []}),
                             ("tile_plan", {"blockers": ["repeat_or_ending_barrier"]})):
            changed = deepcopy(old); changed[field] = value
            self.assertFalse(trial.eligible({}, {}, changed, {"accepted": True}))
        self.assertFalse(trial.eligible({"blockers": ["clock"]}, {}, old, {"accepted": True}))
        self.assertFalse(trial.eligible({}, {"abstention_reasons": ["pitch"]}, old, {"accepted": True}))
        self.assertFalse(trial.eligible({}, {}, old, {"accepted": False}))

    def disk_trial(self, mode):
        with TemporaryDirectory() as name:
            root = Path(name); source = root/"prior"; source.mkdir(); plans = root/"plans"; plans.mkdir()
            output = root/"out"; ir = fixture(); target = sample(); frozen = {"sample": target, "plan_index": 0}
            irpath = plans/"ir.json.gz"; trial.write_packet(irpath, ir)
            xml = plans/"source.musicxml"; xml.write_bytes(b"<score-partwise version='4.0'/>")
            oldplan = {"blockers": ["global_cell_budget_no_truncation"]}
            status = "bounded_plan_abstention"
            if mode == "repeat": oldplan["blockers"].append("repeat_or_ending_barrier")
            if mode == "control": status = "selected_untrained_hypothesis"
            prediction = None if mode != "control" else {"source_labels_used_for_selection": False,
                "segments": [{"span": target["span"], "root_spelling": ("C", 0),
                              "members": (("C", 0), ("E", 0), ("G", 0))}]}
            packet = {"pair_id": "pair", "sample_id": target["sample_id"], "sample_span": target["span"],
                "plan_index": 0, "work_family_id": "family", "collection_id": "c", "tile_plan": oldplan,
                "status": status, "selected_prediction": prediction, "source_clock_gate": SourceClockGuard(ir).scope(target["span"]),
                "reference_binding_verified": True}
            if mode == "contamination": packet["reference_cells"] = []
            pred = source/"p.json.gz"; trial.write_packet(pred, packet)
            pins = {str(Path(trial.__file__).resolve()): "changed"} if mode == "code" else {}
            trial.write(source/"run-contract.json", {"frozen_plan_source": str(plans), "code_pins": pins,
                                                     "source_labels_used_at_inference": False})
            trial.write(source/"prediction-freeze.json", {"contexts": 1, "labels_read": False,
                                                         "prediction_hashes": {str(pred): trial.digest(pred)}})
            trial.write(plans/"frozen-plan.json", {"packages": [{"entry": {"pair_id": "pair"}, "blockers": [],
                "observation_ir_path": str(irpath), "observation_ir_content_sha256": _hash(ir),
                "preparation": {"source_paths": {"score": str(xml)}, "source_sha256": {"score": trial.digest(xml)}},
                "plan": {"selected_samples": [frozen]}}]})
            record = deepcopy(packet); record["candidate_ceiling"] = None
            record["reference_cells"] = [{"span": target["span"], "signature": [["C", 0], [["C", 0], ["E", 0], ["G", 0]]], "reason": None}]
            record["evaluation"] = evaluate(native_reference(record), native_prediction(prediction, target["span"]),
                                             target["span"], selected=prediction is not None)
            trial.write(source/"report.json", {"records": [record], "table": summarize([record]),
                                              "input_hashes": {}, "code_hashes": {}, "artifact_hashes": {}})
            if mode == "packet": trial.write_packet(pred, dict(packet, modified=True))
            expected = "changed" if mode == "report" else trial.digest(source/"report.json")
            original_load = trial.load
            def load(p):
                if Path(p) == source/"report.json":
                    seal = original_load(output/"prediction-freeze.json")
                    self.assertFalse(seal["labels_read"])
                    for path, sha in seal["prediction_hashes"].items(): self.assertEqual(trial.digest(path), sha)
                return original_load(p)
            with patch.object(trial, "BASELINE_REPORT_SHA", expected), patch.object(trial, "load", side_effect=load), \
                 patch.dict(bounded.CONFIG, tile_cells=2):
                if mode in ("code", "contamination", "packet", "report"):
                    with self.assertRaisesRegex(ValueError, "changed|contamination"): trial.run(source, output)
                    return
                got = trial.run(source, output)
            row = original_load(output/"report.json")["records"][0]
            self.assertEqual(got["contexts"], 1)
            if mode in ("control", "repeat"):
                self.assertFalse(row["streaming_attempted"]); self.assertEqual(_hash(row["selected_prediction"]), _hash(prediction))
                self.assertEqual(got["table"], summarize([record])); self.assertEqual(got["unchanged_controls"], 1)
            else:
                self.assertTrue(row["streaming_attempted"]); self.assertTrue(row["exact_optimum_under_declared_graph"])
                self.assertEqual(row["checkpoint_disk_resume"]["operations_before"], row["checkpoint_disk_resume"]["operations_after"])
                self.assertTrue(row["candidate_inventory_complete"]); self.assertIsNone(row["candidate_ceiling"])
                case = original_load(got["cases"][0]["case_path"])
                self.assertEqual(original_load(case["canonical_ir_path"]), ir)
                self.assertEqual(Path(case["source_musicxml_path"]).read_bytes(), xml.read_bytes())
                self.assertEqual(got["new_selected_contexts"], 1)

    def test_pages_disk_resume_seal_before_reference(self): self.disk_trial("attempt")
    def test_existing_selection_unchanged(self): self.disk_trial("control")
    def test_repeat_barrier_unchanged(self): self.disk_trial("repeat")
    def test_changed_code_rejected(self): self.disk_trial("code")
    def test_changed_packet_rejected(self): self.disk_trial("packet")
    def test_annotation_in_prediction_rejected(self): self.disk_trial("contamination")
    def test_changed_reference_report_rejected(self): self.disk_trial("report")
    def test_output_never_overwritten(self):
        with TemporaryDirectory() as name:
            with self.assertRaisesRegex(ValueError, "output_exists"): trial.run("missing", name)


if __name__ == "__main__": unittest.main()
