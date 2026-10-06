from copy import deepcopy
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_window_workspace_trial as trial
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.formal_ir import q
from test_harmony_bounded_recovery import fixture, sample


def tied_fixture():
    ir = fixture(); n = ir["note_events"][0]; sound = ir["sounding_events"][0]
    n["notated_duration_quarter"] = q(2)
    tail = deepcopy(n); tail.update(note_id="tail", global_onset_quarter=q(2))
    ir["note_events"].append(tail); sound["source_note_ids"].append("tail")
    sound["tie_chain_id"] = "tie"
    return ir


class WorkspaceTrialTests(unittest.TestCase):
    def test_full_tied_release_and_source_notes(self):
        ir = tied_fixture(); old = deepcopy(ir); result = trial.tie_audit(ir)
        self.assertEqual(result["passed"], 1); self.assertEqual(result["failed"], 0)
        self.assertEqual(result["records"][0]["span"], {"start": q(0), "end": q(4)})
        self.assertEqual(ir, old)

    def test_shortened_tie_rejected_not_repaired(self):
        ir = tied_fixture(); ir["sounding_events"][0]["span"]["end"] = q(2)
        got = trial.tie_audit(ir)
        self.assertEqual(got["failed"], 1)
        self.assertIn("release_mismatch", got["records"][0]["reasons"])

    def test_missing_note_or_wrong_attack_diagnosed(self):
        for mode in ("note", "attack"):
            ir = tied_fixture()
            if mode == "note": ir["sounding_events"][0]["source_note_ids"] = ["absent", "tail"]
            else: ir["sounding_events"][0]["attack_note_id"] = "tail"
            self.assertEqual(trial.tie_audit(ir)["failed"], 1)

    def disk_trial(self, mode):
        with TemporaryDirectory() as name:
            root = Path(name); source = root/"j3d"; source.mkdir(); planroot = root/"j3b"; planroot.mkdir()
            output = root/"out"; ir = fixture(); frozen = sample(); irpath = planroot/"ir.json.gz"
            trial.write_packet(irpath, ir)
            chosen = {"source_labels_used_for_selection": False, "segments": [{"span": frozen["span"],
                      "root_spelling": ("C", 0), "members": (("C", 0), ("E", 0), ("G", 0))}]}
            packet = {key: None for key in trial.UNCHANGED}
            packet.update(pair_id="pair", sample_id="frozen", work_family_id="family", collection_id="c",
                sample_span=frozen["span"], plan_index=0, frontier_attempted=mode != "control", elapsed_seconds=1,
                selected_prediction=chosen, reference_binding_verified=True, status="selected_untrained_hypothesis")
            pred = source/"pred.json.gz"; trial.write_packet(pred, packet)
            trial.write(planroot/"frozen-plan.json", {"packages": [{"entry": {"pair_id": "pair"},
                "observation_ir_path": str(irpath), "observation_ir_content_sha256": _hash(ir),
                "plan": {"selected_samples": [{"sample": frozen, "plan_index": 0}]}}]})
            trial.write(source/"run-contract.json", {"frozen_plan_source": str(planroot), "code_pins": {},
                                                     "source_labels_used_at_inference": False})
            trial.write(source/"prediction-freeze.json", {"contexts": 1, "labels_read": False,
                                                         "prediction_hashes": {str(pred): trial.digest(pred)}})
            record = deepcopy(packet)
            record["reference_cells"] = [{"span": frozen["span"], "signature": [["C", 0], [["C", 0], ["E", 0], ["G", 0]]], "reason": None}]
            record["candidate_ceiling"] = {"lattice_hit": True}
            record["evaluation"] = evaluate(native_reference(record), native_prediction(chosen, frozen["span"]),
                                             frozen["span"], selected=True)
            trial.write(source/"report.json", {"records": [record], "table": summarize([record]),
                "input_hashes": {str(irpath): trial.digest(irpath)}, "code_hashes": {}, "artifact_hashes": {}})
            real_load = trial.load
            def load(p):
                if Path(p) == source/"report.json":
                    seal = real_load(output/"prediction-freeze.json")
                    self.assertFalse(seal["labels_read"])
                    for path, sha in seal["prediction_hashes"].items(): self.assertEqual(trial.digest(path), sha)
                return real_load(p)
            def infer(observation, target):
                self.assertFalse((output/"prediction-freeze.json").exists()); self.assertEqual(target, frozen)
                self.assertNotIn("reference_cells", observation)
                if mode == "tamper": trial.write_packet(irpath, {"tamper": True})
                result = {k: deepcopy(packet[k]) for k in trial.UNCHANGED}
                result["window_reuse"] = {"synthetic": True}
                if mode == "changed": result["selected_prediction"]["segments"][0]["members"] = (("C", 0),)
                return result, None
            with patch.object(trial, "BASELINE_REPORT_SHA", trial.digest(source/"report.json")), \
                    patch.object(trial, "load", side_effect=load), patch.object(trial, "infer", side_effect=infer) as mocked:
                if mode in ("changed", "tamper"):
                    with self.assertRaisesRegex(ValueError, "computation_replay_changed|baseline_artifact_changed"):
                        trial.run(source, output)
                else:
                    got = trial.run(source, output)
                    self.assertEqual(got["unchanged_predictions"], 1)
                    self.assertEqual(got["table"], summarize([record]))
                    self.assertEqual(mocked.call_count, int(mode != "control"))

    def test_replay_physically_sealed_before_reference_and_tuple_json_equal(self): self.disk_trial("retry")
    def test_control_is_not_recomputed(self): self.disk_trial("control")
    def test_changed_selection_rejected(self): self.disk_trial("changed")
    def test_changed_source_rejected(self): self.disk_trial("tamper")

    def test_seal_order_and_no_overwrite(self):
        code = inspect.getsource(trial.run)
        self.assertLess(code.index('save(output/"prediction-freeze.json"'), code.index('baseline = read(source/"report.json"'))
        with TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "output_exists"): trial.run("missing", t)


if __name__ == "__main__": unittest.main()
