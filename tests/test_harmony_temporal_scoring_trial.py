from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_temporal_scoring_trial as trial
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_exact_frontier import problem
from test_harmony_bounded_recovery import fixture, sample


class TemporalTrialTests(unittest.TestCase):
    def test_graph_codec_retains_all_edges_sources_fractions(self):
        graph, _ = problem()
        self.assertEqual(trial.graph_from_packet(trial.graph_packet(graph)), graph)

    def test_independent_path_scores_baseline_and_new_contract(self):
        graph, ev = problem(); chosen = trial.temporal.decode(graph, ev)["selected"]
        receipt = trial.path_receipt(graph, ev, trial.path_ids(chosen))
        self.assertEqual(receipt["costs"]["combined"], chosen["score_cost"])
        self.assertEqual(set(receipt["costs"]), set(trial.temporal.ARMS))
        self.assertFalse(receipt["source_labels_used_to_create_this_path"])

    def disk_trial(self, mode):
        with TemporaryDirectory() as name:
            root = Path(name); source = root/"prior"; source.mkdir(); plans = root/"plans"; plans.mkdir()
            output = root/"out"; ir = fixture(); target = sample(); graph, ev = problem(ir)
            selected = trial.temporal.decode(graph, ev, arm="baseline")["selected"] if mode != "abstention" else None
            irpath = plans/"ir.json.gz"; trial.expanded.write_packet(irpath, ir)
            xml = plans/"source.musicxml"; xml.write_bytes(b"<score-partwise version='4.0'/>")
            packet = {"pair_id": "pair", "sample_id": target["sample_id"], "sample_span": target["span"],
                "plan_index": 0, "work_family_id": "family", "collection_id": "c", "recovery_attempted": False,
                "status": "selected_untrained_hypothesis" if selected else "source_preflight_abstention",
                "selected_prediction": selected, "source_clock_gate": SourceClockGuard(ir).scope(target["span"]),
                "reference_binding_verified": True}
            if mode == "contamination": packet["evaluation"] = {}
            pred = source/"p.json.gz"; trial.expanded.write_packet(pred, packet)
            pins = {str(Path(trial.__file__).resolve()): "changed"} if mode == "code" else {}
            trial.expanded.write(source/"run-contract.json", {"frozen_plan_source": str(plans), "code_pins": pins,
                "source_labels_used_at_inference": False})
            trial.expanded.write(source/"prediction-freeze.json", {"contexts": 1, "labels_read": False,
                "prediction_hashes": {str(pred): trial.expanded.digest(pred)}})
            trial.expanded.write(plans/"frozen-plan.json", {"packages": [{"entry": {"pair_id": "pair"}, "blockers": [],
                "observation_ir_path": str(irpath), "observation_ir_content_sha256": _hash(ir),
                "preparation": {"source_paths": {"score": str(xml)}, "source_sha256": {"score": trial.expanded.digest(xml)}},
                "plan": {"selected_samples": [{"sample": target, "plan_index": 0}]}}]})
            record = deepcopy(packet); record["candidate_ceiling"] = {"oracle_reference_witness": None}
            record["reference_cells"] = [{"span": target["span"], "signature": [["C", 0], [["C", 0], ["E", 0], ["G", 0]]]}]
            record["evaluation"] = evaluate(native_reference(record), native_prediction(selected, target["span"]),
                target["span"], selected=selected is not None)
            trial.expanded.write(source/"report.json", {"records": [record], "table": summarize([record]),
                "input_hashes": {str(irpath): trial.expanded.digest(irpath)}, "code_hashes": {}, "artifact_hashes": {}})
            real_load = trial.load
            def load(p):
                if Path(p) == source/"report.json":
                    seal = real_load(output/"prediction-freeze.json")
                    self.assertFalse(seal["labels_read"])
                    for path, sha in seal["prediction_hashes"].items(): self.assertEqual(trial.expanded.digest(path), sha)
                return real_load(p)
            def prepare(observation, requested, old):
                self.assertEqual(observation, ir); self.assertEqual(requested, target)
                self.assertNotIn("evaluation", old); self.assertNotIn("reference_cells", old)
                if mode == "tamper": trial.expanded.write_packet(irpath, {"tamper": True})
                return graph, ev, {"synthetic_fixture": True}
            with patch.object(trial, "BASELINE_REPORT_SHA", trial.expanded.digest(source/"report.json")), \
                    patch.object(trial, "load", side_effect=load), patch.object(trial, "prepare", side_effect=prepare) as mocked:
                if mode in ("code", "contamination", "tamper"):
                    with self.assertRaisesRegex(ValueError, "changed|reference_bearing"): trial.run(source, output)
                    return
                got = trial.run(source, output)
                self.assertEqual(mocked.call_count, int(selected is not None))
                self.assertEqual(got["fresh_selected_scopes"], int(selected is not None))
                report = real_load(output/"report.json")
                self.assertEqual(report["tables"]["baseline"], summarize([record]))
                self.assertEqual(set(report["tables"]), set(trial.temporal.ARMS))
                self.assertFalse(got["new_rules_adopted_for_production"])
                if selected is not None:
                    source_ir = next((output/"sources").glob("*/canonical-ir.json.gz"))
                    self.assertEqual(real_load(source_ir), ir)

    def test_four_predictions_physical_seal_before_reference(self): self.disk_trial("selected")
    def test_abstention_denominator_kept_without_recompute(self): self.disk_trial("abstention")
    def test_changed_code_rejected(self): self.disk_trial("code")
    def test_reference_contamination_rejected(self): self.disk_trial("contamination")
    def test_changed_source_rejected(self): self.disk_trial("tamper")
    def test_output_no_overwrite(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "output_exists"): trial.run("missing", folder)


if __name__ == "__main__": unittest.main()
