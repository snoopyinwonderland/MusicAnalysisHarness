from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_candidate_recall import fraction, rational
from musicanote_harness.harmony_margin_learning import (
    fit, infer, loss_augmented_decode, path_loss, training_loss,
)
from musicanote_harness.harmony_margin_learning_trial import ARMS, run
from musicanote_harness.harmony_scored_decoder import (
    DEFAULT_WEIGHTS, Problem, decode, evaluation_path, feature_cost,
)
from musicanote_harness.harmony_scored_decoder_trial import evaluate_selection
from musicanote_harness.harmony_structured_learning import path_features
from musicanote_harness.harmony_structured_learning_trial import run as previous_run
from test_harmony_lattice_recall import C, D, cell
from test_harmony_scored_decoder import manual_edge
import test_harmony_structured_learning as learning_tests
from test_harmony_structured_learning import contract, entry, training_example


def prediction(edges):
    return {"selected": {"proposal_id": "test", "segments": [
        {"semantic_group_ref": e.group_id, "span": {"start": rational(e.start), "end": rational(e.end)},
         "root_spelling": e.signature[0], "members": e.signature[1]} for e in edges]}}


def all_paths(problem):
    def walk(index, path):
        if index == len(problem.points)-1:
            yield tuple(path)
        elif len(path) < problem.max_segments:
            for edge in problem.edges:
                if edge.start_index == index:
                    yield from walk(edge.end_index, path+[edge])
    return list(walk(0, []))


def tiny_problem():
    points = (F(0), F(1, 3), F(2, 3), F(1))
    edges = tuple(replace(manual_edge(f"{i}-{j}-{n}", i, j, sig, F(n, 20)),
                          start=points[i], end=points[j])
                  for i in range(3) for j in range(i+1, 4) for n, sig in enumerate((C, D)))
    return Problem(points, edges, 3, F(1), "ready")


class MarginLearningTests(unittest.TestCase):
    def test_additive_loss_equals_whole_path_evaluator_exhaustively(self):
        p = tiny_problem()
        for cells in ((cell(0, 1, C),), (cell(0, F(1, 3), C), cell(F(1, 3), 1, D)),
                      (cell(0, F(1, 3), C), cell(F(1, 3), F(2, 3), D), cell(F(2, 3), 1, C)),
                      (cell(0, F(1, 3), C), cell(F(1, 3), 1, C))):
            loss = training_loss(p, cells)
            for edges in all_paths(p):
                pred = prediction(edges); detail = path_loss(p, pred, loss)
                ev = evaluate_selection(evaluation_path(pred), cells)
                time = 1-fraction(ev["selected_root_members_time"])
                b = ev["semantic_boundary_exact"]
                self.assertEqual(detail["semantic_boundary_errors"], b["extra"]+b["missed"])
                self.assertEqual(fraction(detail["total"]), time+F(1, 4)*F(b["extra"]+b["missed"], loss.boundary_normalizer))

    def test_loss_augmented_exact_optimum_matches_exhaustive_signed_score(self):
        p = tiny_problem(); cells = (cell(0, F(1, 3), C), cell(F(1, 3), 1, D))
        weights = dict(DEFAULT_WEIGHTS); weights["member_turnover"] = F(-2)
        loss = training_loss(p, cells)
        expected = min((feature_cost(path_features(p, prediction(edges)), weights)
                        - fraction(path_loss(p, prediction(edges), loss)["total"]),
                        tuple(e.group_id for e in edges)) for edges in all_paths(p))
        result = loss_augmented_decode(p, weights, loss)
        self.assertEqual(fraction(result["augmented_cost"]), expected[0])
        self.assertEqual(tuple(s["semantic_group_ref"] for s in result["selected"]["segments"]), expected[1])

    def test_loss_sign_prefers_wrong_high_loss_adversary(self):
        x = training_example()
        zero = {k: F() for k in DEFAULT_WEIGHTS}
        result = loss_augmented_decode(x.problem, zero, training_loss(x.problem, x.cells))
        self.assertEqual(result["selected"]["segments"][0]["semantic_group_ref"], "a_wrong")
        self.assertEqual(fraction(result["augmented_cost"]), -1)
        self.assertEqual(fraction(result["selected"]["score_cost"]), 0)

    def test_same_signature_partition_is_not_semantic_boundary(self):
        p = tiny_problem(); loss = training_loss(p, (cell(0, 1, C),))
        edges = [next(e for e in p.edges if e.start_index == i and e.end_index == i+1 and e.signature == C) for i in range(3)]
        self.assertEqual(path_loss(p, prediction(edges), loss)["semantic_boundary_errors"], 0)

    def test_multiple_internal_misses_not_double_counted(self):
        p = tiny_problem()
        loss = training_loss(p, (cell(0, F(1, 3), C), cell(F(1, 3), F(2, 3), D), cell(F(2, 3), 1, C)))
        edge = next(e for e in p.edges if e.start_index == 0 and e.end_index == 3 and e.signature == C)
        detail = path_loss(p, prediction([edge]), loss)
        self.assertEqual(detail["semantic_boundary_errors"], 2)
        self.assertEqual(fraction(detail["normalized_time_error"]), F(1, 3))
        self.assertEqual(fraction(detail["total"]), F(7, 12))

    def test_loss_is_not_probability_and_empty_boundary_denominator_is_one(self):
        p = tiny_problem(); loss = training_loss(p, (cell(0, 1, C),))
        edges = [next(e for e in p.edges if e.start_index == i and e.end_index == i+1
                      and e.signature == (C if i % 2 else D)) for i in range(3)]
        detail = path_loss(p, prediction(edges), loss)
        self.assertEqual(detail["boundary_normalizer"], 1)
        self.assertEqual(fraction(detail["normalized_boundary_error"]), 2)

    def test_time_only_ignores_boundary_errors_but_preserves_diagnostics(self):
        p = tiny_problem(); loss = training_loss(p, (cell(0, 1, C),), F())
        edges = [next(e for e in p.edges if e.start_index == i and e.end_index == i+1
                      and e.signature == (C if i % 2 else D)) for i in range(3)]
        detail = path_loss(p, prediction(edges), loss)
        self.assertEqual(fraction(detail["total"]), F(2, 3))
        self.assertEqual(detail["semantic_boundary_errors"], 2)

    def test_partial_reference_and_invalid_partition_are_rejected(self):
        x = training_example()
        with self.assertRaisesRegex(ValueError, "complete_ready"):
            training_loss(x.problem, (cell(0, 2, None),))
        with self.assertRaisesRegex(ValueError, "partition"):
            training_loss(x.problem, (cell(0, 1, C), cell(F(3, 2), 2, D)))
        with self.assertRaisesRegex(ValueError, "invalid_boundary"):
            training_loss(x.problem, x.cells, 0.25)

    def test_loss_problem_binding_mismatch_rejected(self):
        x = training_example(); loss = training_loss(x.problem, x.cells)
        with self.assertRaisesRegex(ValueError, "problem_mismatch"):
            loss_augmented_decode(replace(x.problem, edges=x.problem.edges[:1]), DEFAULT_WEIGHTS, loss)

    def test_budget_abstains_without_approximate_training_winner(self):
        p = tiny_problem(); result = loss_augmented_decode(p, DEFAULT_WEIGHTS, training_loss(p, (cell(0, 1),)), transition_budget=1)
        self.assertIsNone(result["selected"])
        self.assertFalse(result["exact_optimum_under_declared_score"])
        x = training_example(); model = fit([x], contract([x.entry]), [x.entry], "parent", transition_budget=1)
        self.assertEqual(model["updates"], [])
        self.assertEqual(model["epochs"][0]["statuses"]["resource_abstention_no_update"], 1)

    def test_segment_cap_is_preserved(self):
        p = tiny_problem(); p = replace(p, max_segments=1)
        r = loss_augmented_decode(p, DEFAULT_WEIGHTS, training_loss(p, (cell(0, 1),)))
        self.assertEqual(len(r["selected"]["segments"]), 1)

    def test_margin_update_sign_and_inference_improve_synthetic_case(self):
        x = training_example(); m = [x.entry]
        model = fit([x], contract(m), m, "parent", update_cap=F(2))
        self.assertTrue(model["updates"])
        u = model["updates"][0]
        self.assertLessEqual(fraction(u["same_pair_violation_after"]), fraction(u["violation_before"]))
        self.assertEqual(evaluation_path(infer(x.problem, model))["segments"][0]["signature"], D)
        self.assertFalse(model["configuration"]["dev_checkpoint_selection"])

    def test_identical_features_positive_loss_is_explicit_collision(self):
        x = training_example()
        x = replace(x, problem=replace(x.problem, edges=tuple(replace(e, features={}) for e in x.problem.edges)))
        model = fit([x], contract([x.entry]), [x.entry], "parent")
        self.assertEqual(model["updates"], [])
        self.assertEqual(len(model["feature_collisions"]), 5)
        self.assertEqual(model["epochs"][0]["statuses"]["feature_collision_positive_margin_no_update"], 1)

    def test_clipped_quantized_update_records_actual_residual(self):
        x = training_example(); model = fit([x], contract([x.entry]), [x.entry], "parent", update_cap=F(20), weight_bound=F(1, 10))
        u = model["updates"][0]
        self.assertTrue(u["clipped_weights"])
        self.assertGreater(fraction(u["same_pair_violation_after"]), 0)
        self.assertTrue(all(abs(fraction(w)) <= F(1, 10) for w in model["weights"].values()))

    def test_reproducible_order_no_core_feature_mutation(self):
        a, b = training_example("a"), training_example("b"); m = [a.entry]; before = deepcopy(a.problem.edges)
        first = fit([a, b], contract(m), m, "parent")
        self.assertEqual(first, fit([b, a], contract(m), m, "parent"))
        self.assertEqual(a.problem.edges, before)
        self.assertEqual(set(first["weights"]), set(DEFAULT_WEIGHTS))

    def test_dev_pending_scope_and_duplicate_training_rejected(self):
        x = training_example(); m = [x.entry]; c = contract(m)
        with self.assertRaisesRegex(ValueError, "nontrain"):
            fit([x, training_example("dev", entry("dev", "dev"))], c, m, "parent")
        with self.assertRaisesRegex(ValueError, "duplicate_training"):
            fit([x, x], c, m, "parent")
        c["human_scope_confirmation"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "scope_confirmation"):
            fit([x], c, m, "parent")

    def test_absent_candidate_and_partial_remain_excluded(self):
        x = training_example(); m = [x.entry]
        with self.assertRaisesRegex(ValueError, "no_reachable"):
            fit([replace(x, problem=replace(x.problem, edges=x.problem.edges[:1]))], contract(m), m, "parent")
        partial = replace(x, sample_id="partial", cells=(cell(0, 2, None),))
        model = fit([x, partial], contract(m), m, "parent")
        self.assertEqual(model["reachable_complete_training_contexts"], 1)
        self.assertFalse(model["gold_candidates_injected"])

    def test_inference_has_no_loss_gold_argument_and_tampered_model_rejected(self):
        x = training_example(); m = [x.entry]; model = fit([x], contract(m), m, "parent")
        self.assertEqual(set(inspect.signature(infer).parameters), {"problem", "model", "transition_budget"})
        chosen = infer(x.problem, model)["selected"]
        self.assertIsNone(chosen["confidence"])
        self.assertNotIn("training_loss", chosen)
        self.assertFalse(chosen["source_labels_used_for_selection"])
        model["weights"]["nonmember_exposure"]["numerator"] += 1
        with self.assertRaisesRegex(ValueError, "content_mismatch"):
            infer(x.problem, model)


class MarginTrialTests(unittest.TestCase):
    def files(self, folder, leak=False):
        r, l, b, c, pins, packet = learning_tests.LearningTrialTests().setup_files(folder, leak)
        previous_run(r, l, b, c, folder/"previous", **pins)
        p = folder/"previous/report.json"
        return r, l, b, p, c, pins | {"expected_learned_sha": hashlib.sha256(p.read_bytes()).hexdigest()}, packet

    def test_physical_two_arm_runner_preserves_previous_results(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); r, l, b, p, c, pins, _ = self.files(folder)
            result = run(r, l, b, p, c, folder/"out", **pins)
            for arm in ARMS:
                self.assertEqual(result["summary"][arm]["selected_correct_contexts"], 1)
                self.assertTrue((folder/"out"/(arm+"-model.json")).exists())
            self.assertFalse(result["development_labels_used_for_updates_or_checkpoint_selection"])
            self.assertFalse(result["production_modified"])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), pins["expected_learned_sha"])
            self.assertEqual(result["summary"]["learned_joint_music"], json.loads(p.read_text())["summary"]["learned_joint_music"])
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(r, l, b, p, c, folder/"out", **pins)

    def test_pending_contract_fails_before_missing_artifact(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); r, l, b, p, c, pins, packet = self.files(folder)
            body = json.loads(c.read_text()); body["human_scope_confirmation"]["status"] = "pending"
            c.write_text(json.dumps(body), encoding="utf-8"); pins["expected_contract_sha"] = hashlib.sha256(c.read_bytes()).hexdigest()
            packet.unlink()
            with self.assertRaisesRegex(ValueError, "scope_confirmation"):
                run(r, l, b, p, c, folder/"out", **pins)
            self.assertFalse((folder/"out").exists())

    def test_changed_input_guard_rejects_no_output(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); r, l, b, p, c, pins, packet = self.files(folder)
            packet.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "frozen_input_changed"):
                run(r, l, b, p, c, folder/"out", **pins)
            self.assertFalse((folder/"out").exists())


if __name__ == "__main__":
    unittest.main()
