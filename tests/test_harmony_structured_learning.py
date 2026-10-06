from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_scored_decoder import DEFAULT_WEIGHTS, Problem, decode, evaluation_path
from musicanote_harness.harmony_structured_learning import (
    RESTRICTIONS, USE_CONTRACT_VERSION, TrainingExample, compatible_problem,
    content_hash, fit, infer, path_features, quantize, validate_use_contract,
)
from musicanote_harness.harmony_structured_learning_trial import run, research_contract
from musicanote_harness.harmony_scored_decoder_trial import run as baseline_run
from test_harmony_lattice_recall import C, D, cell
from test_harmony_scored_decoder import manual_edge, physical_fixture


def entry(key="m0", split="train", family="family"):
    return {"manifest_entry_id": key, "work_family_id": family, "split": split,
            "rights": {"internal_research_use": True, "model_training_approved": False},
            "eligibility": {"automatic_training": False}}


def contract(manifest):
    return {"version": USE_CONTRACT_VERSION, "parent_recall_sha256": "parent",
            "purpose": "local_noncommercial_research",
            "human_scope_confirmation": {"status": "confirmed", "source": "direct_user_message",
                                         "text": "SYNTHETIC test authorization, not real corpus approval", "confirmed_at": "fixture"},
            "restrictions": {k: False for k in RESTRICTIONS},
            "approved_entries": [{"manifest_entry_id": e["manifest_entry_id"], "manifest_entry_sha256": content_hash(e),
                                  "source_license": {"spdx": "CC-BY-NC-SA-4.0", "reference_url": "synthetic",
                                      "local_license_path": "synthetic", "local_license_sha256": "synthetic",
                                      "readme_path": "synthetic", "readme_sha256": "synthetic",
                                      "attribution_reference": "synthetic"}} for e in manifest if e["split"] == "train"]}


def training_example(sample="sample", e=None):
    # Wrong cheap C, correct D costs more. Learning must LOWER target cost.
    problem = Problem((F(0), F(2)), (manual_edge("a_wrong", 0, 1, C),
        replace(manual_edge("b_gold", 0, 1, D, F(1)), end=F(2)),), 1, F(1), "ready")
    # manual_edge uses point indices as time; correct first edge's time too.
    problem = replace(problem, edges=tuple(replace(x, end=F(2)) for x in problem.edges))
    return TrainingExample(sample, e or entry(), problem, (cell(0, 2, D),))


class StructuredLearningTests(unittest.TestCase):
    def test_original_manifest_not_mutated_or_implicitly_approved(self):
        m = [entry()]; before = deepcopy(m); c = contract(m)
        validate_use_contract(c, m, "parent")
        self.assertEqual(m, before)
        self.assertFalse(m[0]["rights"]["model_training_approved"])
        self.assertFalse(m[0]["eligibility"]["automatic_training"])

    def test_pending_scope_rejected(self):
        m = [entry()]; c = contract(m); c["human_scope_confirmation"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "scope_confirmation"):
            validate_use_contract(c, m, "parent")

    def test_internal_use_alone_does_not_allow_fit(self):
        with self.assertRaises(ValueError):
            fit([training_example()], {}, [entry()], "parent")

    def test_commercial_or_external_scope_cannot_be_enabled(self):
        for restriction in RESTRICTIONS:
            m = [entry()]; c = contract(m); c["restrictions"][restriction] = True
            with self.assertRaisesRegex(ValueError, "scope_restriction"):
                validate_use_contract(c, m, "parent")

    def test_parent_or_manifest_mutation_rejected(self):
        m = [entry()]; c = contract(m)
        with self.assertRaisesRegex(ValueError, "parent_mismatch"):
            validate_use_contract(c, m, "other")
        m[0]["work_family_id"] = "changed"
        with self.assertRaisesRegex(ValueError, "entry_binding"):
            validate_use_contract(c, m, "parent")

    def test_dev_cannot_enter_approval_or_updates(self):
        m = [entry()]; c = contract(m); d = entry("dev", "dev")
        c["approved_entries"].append({**c["approved_entries"][0], "manifest_entry_id": "dev"})
        with self.assertRaisesRegex(ValueError, "protected"):
            validate_use_contract(c, m+[d], "parent")
        with self.assertRaisesRegex(ValueError, "nontrain"):
            fit([training_example(), training_example("dev", d)], contract(m), m+[d], "parent")

    def test_missing_licence_evidence_cannot_be_inferred(self):
        m = [entry()]; c = contract(m); c["approved_entries"][0]["source_license"].pop("readme_sha256")
        with self.assertRaisesRegex(ValueError, "license_evidence"):
            validate_use_contract(c, m, "parent")

    def test_learning_sign_and_averaged_inference(self):
        x = training_example(); m = [x.entry]
        self.assertEqual(evaluation_path(decode(x.problem))["segments"][0]["signature"], C)
        model = fit([x], contract(m), m, "parent", rate=F(1))
        result = infer(x.problem, model)
        self.assertEqual(evaluation_path(result)["segments"][0]["signature"], D)
        self.assertEqual(result["status"], "selected_learned_research_hypothesis")
        self.assertIsNone(result["selected"]["confidence"])
        self.assertFalse(result["selected"]["source_labels_used_for_selection"])
        self.assertTrue(model["training_performed"])
        self.assertFalse(model["gold_candidates_injected"])

    def test_gold_filter_does_not_create_missing_candidates(self):
        x = training_example(); problem = replace(x.problem, edges=x.problem.edges[:1])
        constrained, _ = compatible_problem(problem, x.cells)
        self.assertEqual(constrained.edges, ())
        with self.assertRaisesRegex(ValueError, "no_reachable"):
            fit([replace(x, problem=problem)], contract([x.entry]), [x.entry], "parent")

    def test_partial_and_unavailable_are_not_training_targets(self):
        x = training_example()
        self.assertEqual(compatible_problem(x.problem, (cell(0, 2, None),))[1], "partial_or_unsupported_reference")
        self.assertEqual(compatible_problem(replace(x.problem, status="baseline_not_ready"), x.cells)[1], "lattice_unavailable")

    def test_partition_cannot_silently_misalign(self):
        x = training_example()
        with self.assertRaisesRegex(ValueError, "context_mismatch"):
            compatible_problem(x.problem, (cell(0, 1, D),))
        with self.assertRaisesRegex(ValueError, "partition"):
            compatible_problem(x.problem, (cell(0, 1, D), cell(F(3, 2), 2, D)))

    def test_crossing_reference_change_is_excluded(self):
        x = training_example()
        gold, _ = compatible_problem(x.problem, (cell(0, 1, C), cell(1, 2, D)))
        self.assertEqual(gold.edges, ())

    def test_missing_features_stay_unavailable(self):
        x = training_example(); before = deepcopy(x.problem.edges[0].features)
        model = fit([x], contract([x.entry]), [x.entry], "parent")
        self.assertEqual(x.problem.edges[0].features, before)
        self.assertNotIn("seventh_resolution", model["weights"])
        self.assertEqual(set(path_features(x.problem, decode(x.problem))), set(DEFAULT_WEIGHTS))

    def test_learning_is_reproducible_and_duplicate_samples_rejected(self):
        a = training_example("a"); b = training_example("b"); m = [a.entry]; c = contract(m)
        self.assertEqual(fit([a, b], c, m, "parent"), fit([b, a], c, m, "parent"))
        with self.assertRaisesRegex(ValueError, "duplicate_training"):
            fit([a, a], c, m, "parent")

    def test_model_mutation_rejected_and_inference_has_no_gold_argument(self):
        x = training_example(); model = fit([x], contract([x.entry]), [x.entry], "parent")
        self.assertNotIn("reference", inspect.signature(infer).parameters)
        model["weights"]["nonmember_exposure"]["numerator"] += 1
        with self.assertRaisesRegex(ValueError, "content_mismatch"):
            infer(x.problem, model)

    def test_quantization_exact_ties_and_signed_bound(self):
        self.assertEqual(quantize(F(1, 2_000_000)), 0)
        self.assertEqual(quantize(F(3, 2_000_000)), F(2, 1_000_000))
        x = training_example(); model = fit([x], contract([x.entry]), [x.entry], "parent", rate=F(100), weight_bound=F(1))
        self.assertTrue(all(abs(F(v["numerator"], v["denominator"])) <= 1 for v in model["weights"].values()))

    def test_resource_abstention_never_updates_from_incomplete_winner(self):
        x = training_example(); model = fit([x], contract([x.entry]), [x.entry], "parent", transition_budget=1)
        self.assertEqual(model["updates"], [])
        self.assertEqual(model["epochs"][0]["statuses"], {"resource_abstention_no_update": 1})


class LearningTrialTests(unittest.TestCase):
    def setup_files(self, folder, leak=False):
        recall, lattice, rs, ls, packet = physical_fixture(folder, split="train")
        if leak:
            body = json.loads(recall.read_text(encoding="utf-8"))
            other = deepcopy(body["package_manifest"][0]); other.update(manifest_entry_id="dev", split="dev")
            body["package_manifest"].append(other)
            recall.write_text(json.dumps(body), encoding="utf-8")
            rs = hashlib.sha256(recall.read_bytes()).hexdigest()
        bp = folder/"baseline"; baseline_run(recall, lattice, bp, rs, ls)
        baseline = bp/"report.json"; manifest = json.loads(recall.read_text(encoding="utf-8"))["package_manifest"]
        c = contract(manifest); c["parent_recall_sha256"] = rs
        lic, readme = folder/"LICENSE", folder/"README"
        lic.write_text("SYNTHETIC local evidence fixture", encoding="utf-8")
        readme.write_text("SYNTHETIC local evidence fixture", encoding="utf-8")
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        c["approved_entries"][0]["source_license"].update(local_license_path=str(lic), local_license_sha256=digest(lic),
                                                       readme_path=str(readme), readme_sha256=digest(readme))
        cp = folder/"contract.json"; cp.write_text(json.dumps(c), encoding="utf-8")
        return recall, lattice, baseline, cp, {"expected_recall_sha": rs, "expected_lattice_sha": ls,
            "expected_baseline_sha": digest(baseline), "expected_contract_sha": digest(cp)}, packet

    def test_physical_runner_and_old_predictions_preserved(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); r, l, b, c, pins, _ = self.setup_files(folder)
            report = run(r, l, b, c, folder/"out", **pins)
            self.assertEqual(report["summary"]["learned_joint_music"]["selected_correct_contexts"], 1)
            self.assertTrue(report["training_performed"])
            self.assertFalse(report["development_labels_used_for_updates_or_checkpoint_selection"])
            self.assertEqual(hashlib.sha256(b.read_bytes()).hexdigest(), pins["expected_baseline_sha"])
            self.assertTrue((folder/"out/model.json").exists())
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(r, l, b, c, folder/"out", **pins)

    def test_pending_scope_rejected_before_artifact_loading(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); r, l, b, c, pins, packet = self.setup_files(folder)
            body = json.loads(c.read_text()); body["human_scope_confirmation"]["status"] = "pending"
            c.write_text(json.dumps(body), encoding="utf-8"); pins["expected_contract_sha"] = hashlib.sha256(c.read_bytes()).hexdigest()
            packet.unlink()
            with self.assertRaisesRegex(ValueError, "scope_confirmation"):
                run(r, l, b, c, folder/"out", **pins)
            self.assertFalse((folder/"out").exists())

    def test_changed_license_evidence_rejected(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); r, l, b, c, pins, _ = self.setup_files(folder)
            (folder/"LICENSE").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen_input_changed"):
                run(r, l, b, c, folder/"out", **pins)
            self.assertFalse((folder/"out").exists())

    def test_work_family_leakage_rejected_before_fitting(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); r, l, b, c, pins, _ = self.setup_files(folder, leak=True)
            with self.assertRaisesRegex(ValueError, "family_split_leakage"):
                run(r, l, b, c, folder/"out", **pins)
            self.assertFalse((folder/"out").exists())


if __name__ == "__main__":
    unittest.main()
