from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_source_clock_trial as trial
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.formal_ir import q
from test_harmony_bounded_recovery import fixture, sample
from test_harmony_source_clock import tied, span


class SourceClockTrialTests(unittest.TestCase):
    def disk_trial(self, mode):
        with TemporaryDirectory() as name:
            root = Path(name); source = root/"j3e"; source.mkdir()
            prior = root/"j3d"; prior.mkdir(); planroot = root/"j3b"; planroot.mkdir(); output = root/"out"
            ir = tied() if mode in ("invalid", "unaffected") else fixture()
            if mode in ("invalid", "unaffected"): ir["note_events"][1]["global_onset_quarter"] = q(2)
            frozen = sample()
            if mode == "unaffected": frozen["span"] = span(3, 4)
            irpath = planroot/"ir.json.gz"; trial.write_packet(irpath, ir)
            xml = planroot/"source.musicxml"; xml.write_bytes(b"<score-partwise version='4.0'/>")
            chosen = {"source_labels_used_for_selection": False, "segments": [{"span": frozen["span"],
                      "root_spelling": ("C", 0), "members": (("C", 0), ("E", 0), ("G", 0))}]}
            packet = {"pair_id": "pair", "sample_id": "frozen", "work_family_id": "family", "collection_id": "c",
                "sample_span": frozen["span"], "plan_index": 0, "selected_prediction": chosen,
                "reference_binding_verified": True, "status": "selected_untrained_hypothesis"}
            if mode == "contamination": packet["reference_cells"] = []
            pred = source/"pred.json.gz"; trial.write_packet(pred, packet)
            trial.write(planroot/"frozen-plan.json", {"packages": [{"entry": {"pair_id": "pair"},
                "observation_ir_path": str(irpath), "observation_ir_content_sha256": _hash(ir),
                "preparation": {"source_paths": {"score": str(xml)}, "source_sha256": {"score": trial.digest(xml)}},
                "plan": {"selected_samples": [{"sample": frozen, "plan_index": 0}]}}]})
            pins = {str(Path(trial.__file__).resolve()): "wrong"} if mode == "code" else {}
            trial.write(source/"run-contract.json", {"baseline_source": str(prior), "code_pins": pins,
                                                     "source_labels_used_at_inference": False})
            trial.write(prior/"run-contract.json", {"frozen_plan_source": str(planroot)})
            trial.write(source/"prediction-freeze.json", {"contexts": 1, "labels_read": False,
                                                         "prediction_hashes": {str(pred): trial.digest(pred)}})
            record = deepcopy(packet)
            record["reference_cells"] = [{"span": frozen["span"], "signature": [["C", 0], [["C", 0], ["E", 0], ["G", 0]]], "reason": None}]
            record["candidate_ceiling"] = {"lattice_hit": True}
            record["evaluation"] = evaluate(native_reference(record), native_prediction(chosen, frozen["span"]),
                                             frozen["span"], selected=True)
            trial.write(source/"report.json", {"records": [record], "table": summarize([record]),
                "input_hashes": {str(irpath): trial.digest(irpath)}, "code_hashes": {}, "artifact_hashes": {}})
            if mode == "source": trial.write_packet(irpath, dict(ir, tampered=True))
            if mode == "packet": trial.write_packet(pred, dict(packet, tampered=True))
            real_load = trial.load
            def load(p):
                if Path(p) == source/"report.json":
                    seal = real_load(output/"prediction-freeze.json")
                    self.assertFalse(seal["labels_read"])
                    for path, sha in (seal["prediction_hashes"] | seal["source_audit_and_case_hashes"]).items():
                        self.assertEqual(trial.digest(path), sha)
                return real_load(p)
            expected = "wrong" if mode == "report" else trial.digest(source/"report.json")
            with patch.object(trial, "BASELINE_REPORT_SHA", expected), patch.object(trial, "load", side_effect=load):
                if mode in ("source", "packet", "code", "contamination", "report"):
                    with self.assertRaisesRegex(ValueError, "changed|contamination"):
                        trial.run(source, output)
                    return
                got = trial.run(source, output)
            stored = real_load(output/"report.json"); row = stored["records"][0]
            self.assertEqual(got["contexts"], 1)
            self.assertEqual(got["table"]["fully_evaluable_contexts"], 1)
            if mode == "invalid":
                self.assertEqual(got["new_clock_abstentions"], 1)
                self.assertIsNone(row["selected_prediction"]); self.assertIsNone(row["candidate_ceiling"])
                self.assertEqual(row["historical_candidate_ceiling"], record["candidate_ceiling"])
                self.assertEqual(got["table"]["components"]["root_members"]["time_agreement"], 0)
                self.assertEqual(row["transitions"], 0)
                case = real_load(got["cases"][0]["case_path"])
                self.assertEqual(case["source_clock_gaps"][0]["old_false_sounding_exposure_quarters"], q(1))
                self.assertTrue(case["clean_neighbor_control"]["same_entire_candidate_graph"])
                self.assertEqual(real_load(case["canonical_ir_path"]), ir)
                self.assertEqual(Path(case["source_musicxml_path"]).read_bytes(), xml.read_bytes())
            else:
                self.assertEqual(got["new_clock_abstentions"], 0)
                self.assertEqual(got["table"], summarize([record]))
                self.assertEqual(_hash(row["selected_prediction"]), _hash(chosen))

    def test_reuse_sealed_before_reference_and_exact_same_values(self): self.disk_trial("control")
    def test_bad_source_scope_withheld_without_denominator_loss(self): self.disk_trial("invalid")
    def test_same_bad_source_does_not_block_unaffected_scope(self): self.disk_trial("unaffected")
    def test_changed_ir_rejected(self): self.disk_trial("source")
    def test_changed_packet_rejected(self): self.disk_trial("packet")
    def test_changed_code_rejected(self): self.disk_trial("code")
    def test_annotation_contaminated_prediction_rejected(self): self.disk_trial("contamination")
    def test_changed_reference_report_rejected(self): self.disk_trial("report")
    def test_existing_output_never_overwritten(self):
        with TemporaryDirectory() as name:
            with self.assertRaisesRegex(ValueError, "output_exists"): trial.run("missing", name)


if __name__ == "__main__": unittest.main()
