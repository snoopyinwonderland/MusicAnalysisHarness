from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import inspect
import unittest

from musicanote_harness.harmony_candidate_recall import fraction
from musicanote_harness.harmony_functional_learning import (
    INITIAL_WEIGHTS, TrainingExample, decode, fit, infer, loss_augmented_decode, path_features, weights_contract,
)
from musicanote_harness.harmony_functional_scoring import decode as fixed_decode, score_path, supply
from musicanote_harness.harmony_margin_learning import path_loss, training_loss
from musicanote_harness.harmony_scored_decoder import feature_cost
from musicanote_harness.harmony_structured_learning import RESTRICTIONS, compatible_problem, content_hash
from test_harmony_functional_scoring import C, F64, G, example, sig
from test_harmony_lattice_recall import cell
from test_harmony_structured_learning import contract, entry


def existing_paths(problem):
    def visit(index, ids):
        if index == len(problem.points)-1:
            yield ids; return
        if len(ids) >= problem.max_segments:
            return
        for e in problem.edges:
            if e.start_index == index:
                yield from visit(e.end_index, ids+(e.group_id,))
    return list(visit(0, ()))


def sample(sample_id="s", reference=C, specs=None, e=None):
    _, _, _, p, ev = example(specs=specs or ((0, 2, C), (0, 2, G)))
    q, _ = supply(p, ev)
    return TrainingExample(sample_id, e or entry(), q, ev, (cell(0, 2, reference),))


class FunctionalLearningTests(unittest.TestCase):
    def test_twenty_exact_features_and_invalid_weights(self):
        self.assertEqual(len(INITIAL_WEIGHTS), 20)
        for w in ({}, INITIAL_WEIGHTS | {"extra": F()}, INITIAL_WEIGHTS | {"missing_root": 0.1}):
            with self.assertRaisesRegex(ValueError, "weights_contract"):
                weights_contract(w)

    def test_fixed_weight_selection_and_cost_match_pinned_engine(self):
        _, _, _, p, ev = example(); q, _ = supply(p, ev)
        a, b = decode(q, ev), fixed_decode(q, ev)
        self.assertEqual(a["selected"]["segments"], b["selected"]["segments"])
        self.assertEqual(a["selected"]["score_cost"], b["selected"]["score_cost"])
        for ids in existing_paths(q):
            self.assertEqual(feature_cost(path_features(q, ev, ids), INITIAL_WEIGHTS), score_path(q, ev, ids))

    def test_weighted_exact_decoder_matches_exhaustive_arbitrary_signed_weights(self):
        _, _, _, p, ev = example(specs=((0, 2, C), (0, 1, C), (1, 2, G), (1, 2, C)))
        q, _ = supply(p, ev)
        w = {k: F((-1)**i*(i+1), 37) for i, k in enumerate(INITIAL_WEIGHTS)}
        expected = min((feature_cost(path_features(q, ev, ids), w), ids) for ids in existing_paths(q))
        r = decode(q, ev, w)
        self.assertEqual((fraction(r["selected"]["score_cost"]), tuple(s["semantic_group_ref"] for s in r["selected"]["segments"])), expected)

    def test_loss_augmented_exact_decoder_matches_exhaustive(self):
        _, _, _, p, ev = example(specs=((0, 2, C), (0, 1, C), (1, 2, G), (1, 2, C)))
        q, _ = supply(p, ev); loss = training_loss(q, (cell(0, 1, F64), cell(1, 2, G)))
        options = []
        for ids in existing_paths(q):
            r = {"selected": {"segments": [{"semantic_group_ref": gid} for gid in ids]}}
            options.append((feature_cost(path_features(q, ev, ids), INITIAL_WEIGHTS)-fraction(path_loss(q, r, loss)["total"]), ids))
        r = loss_augmented_decode(q, ev, INITIAL_WEIGHTS, loss)
        self.assertTrue(r["selected"]["source_labels_used_for_selection"])
        self.assertTrue(r["selected"]["training_reference_labels_used"])
        self.assertEqual((fraction(r["augmented_cost"]), tuple(s["semantic_group_ref"] for s in r["selected"]["segments"])), min(options))

    def test_partition_invariant_feature_vector_and_role_once(self):
        _, _, _, p, ev = example(specs=((0, 2, C), (0, 1, C), (1, 2, C)))
        whole = (p.edges[0].group_id,); split = tuple(e.group_id for e in p.edges[1:])
        self.assertEqual(path_features(p, ev, whole), path_features(p, ev, split))
        self.assertEqual(path_features(p, ev, split)["harmonic_run_count"], 1)
        # Existing synthetic hypotheses: union scoring itself does not supply
        # candidates based on the reference or demand a vertical chord.
        q = replace(p, edges=tuple(replace(e, signature=F64) for e in p.edges))
        edges = list(q.edges)
        a = next(e for e in edges if e.start == 0 and e.end == 2)
        b = [e for e in edges if e.end-e.start == 1]
        self.assertEqual(path_features(q, ev, (a.group_id,)), path_features(q, ev, tuple(e.group_id for e in b)))
        self.assertEqual(path_features(q, ev, (a.group_id,))["functional_role_complexity"], 1)

    def test_blockers_remain_raw_additive(self):
        x = sample(); p = replace(x.problem, edges=tuple(replace(e, features=e.features | {"blocker_exposure": F(2)}) for e in x.problem.edges))
        self.assertEqual(path_features(p, x.evidence, (p.edges[0].group_id,))["blocker_exposure"], 2)

    def test_unknown_values_remain_unavailable_not_false(self):
        x = sample(); ev = x.evidence; ev.source.measures = (); ev.source._measure_times = (); ev.source._feature_cache.clear()
        r = decode(x.problem, ev)
        for run in r["selected"]["harmonic_runs"]:
            self.assertIsNone(run["features"]["key_signature_foreign_member"])
            self.assertFalse(run["availability"]["key_signature_foreign_member"])
        self.assertEqual(fraction(r["selected"]["feature_vector"]["key_signature_foreign_member"]), 0)

    def test_loss_mismatch_and_incomplete_path_rejected(self):
        x = sample(); loss = training_loss(x.problem, x.cells)
        with self.assertRaisesRegex(ValueError, "problem_mismatch"):
            loss_augmented_decode(x.problem, x.evidence, INITIAL_WEIGHTS, replace(loss, end=F(3)))
        with self.assertRaisesRegex(ValueError, "complete_existing_path"):
            path_features(x.problem, x.evidence, ())

    def test_loss_same_signature_cut_is_not_false_positive(self):
        _, _, _, p, ev = example(specs=((0, 1, C), (1, 2, C)))
        loss = training_loss(p, (cell(0, 2, C),)); r = loss_augmented_decode(p, ev, INITIAL_WEIGHTS, loss)
        self.assertEqual(r["training_loss"]["semantic_boundary_errors"], 0)

    def test_source_candidate_data_not_mutated_and_no_gold_arguments(self):
        x = sample(); before = deepcopy(x.problem)
        decode(x.problem, x.evidence)
        self.assertEqual(x.problem, before)
        for f in (infer, decode):
            self.assertNotIn("loss", inspect.signature(f).parameters)
            self.assertNotIn("reference", inspect.signature(f).parameters)

    def test_resource_abstention_never_returns_approximate_path(self):
        x = sample(); r = decode(x.problem, x.evidence, transition_budget=1)
        self.assertEqual(r["status"], "transition_budget_abstention"); self.assertIsNone(r["selected"])
        self.assertFalse(r["exact_optimum_under_declared_score"])
        with self.assertRaisesRegex(ValueError, "transition_budget"):
            decode(x.problem, x.evidence, transition_budget=True)

    def test_fit_reproducible_bound_averaging_and_label_blind_infer(self):
        a, b = sample("a"), sample("b"); m = [a.entry]; c = contract(m)
        one = fit([a, b], c, m, "parent", epochs=2)
        two = fit([b, a], c, m, "parent", epochs=2)
        self.assertEqual(one, two); self.assertEqual(one["averaging_ticks"], 4)
        self.assertEqual(len(one["weights"]), 20)
        self.assertTrue(all(abs(fraction(v)) <= 4 for v in one["weights"].values()))
        r = infer(a.problem, a.evidence, one)
        self.assertFalse(r["selected"]["source_labels_used_for_selection"])
        self.assertFalse(r["selected"]["training_reference_labels_used"])
        self.assertIsNone(r["selected"]["confidence"])

    def test_missing_gold_is_not_injected(self):
        x = sample(reference=sig(("D", 0), "m")); gold, _ = compatible_problem(x.problem, x.cells)
        self.assertEqual(gold.edges, ())
        with self.assertRaisesRegex(ValueError, "no_reachable"):
            fit([x], contract([x.entry]), [x.entry], "parent")

    def test_dev_unapproved_duplicate_and_pending_rejected_before_fit(self):
        x = sample(); m = [x.entry]; c = contract(m)
        for y in (replace(x, entry=entry("d", "dev")), replace(x, entry=entry("unapproved"))):
            with self.assertRaisesRegex(ValueError, "nontrain"):
                fit([y], c, m, "parent")
        with self.assertRaisesRegex(ValueError, "duplicate_training"):
            fit([x, x], c, m, "parent")
        c["human_scope_confirmation"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "scope_confirmation"):
            fit([x], c, m, "parent")

    def test_restrictions_and_model_content_tampering_rejected(self):
        x = sample(); model = fit([x], contract([x.entry]), [x.entry], "parent", epochs=1)
        for k in RESTRICTIONS:
            bad = deepcopy(model); bad["restrictions"][k] = True
            with self.assertRaisesRegex(ValueError, "unrestricted"):
                infer(x.problem, x.evidence, bad)
        model["weights"]["harmonic_run_count"]["numerator"] += 1
        with self.assertRaisesRegex(ValueError, "content_mismatch"):
            infer(x.problem, x.evidence, model)

    def test_resource_training_skip_still_ticks_average(self):
        x = sample(specs=((0, 2, C), (0, 2, G)))
        model = fit([x], contract([x.entry]), [x.entry], "parent", epochs=2, transition_budget=1)
        self.assertEqual(model["updates"], [])
        self.assertEqual(model["averaging_ticks"], 2)
        self.assertEqual(model["epochs"][0]["statuses"], {"resource_abstention_no_update": 1})

    def test_real_update_sign_and_clipping_without_claiming_target_is_music_truth(self):
        # Deliberately contradictory synthetic target exercises COST update
        # direction. It is not a music-quality or independent accuracy example.
        x = sample(reference=G)
        model = fit([x], contract([x.entry]), [x.entry], "parent", epochs=2)
        self.assertTrue(model["updates"])
        for update in model["updates"]:
            self.assertGreater(fraction(update["tau"]), 0)
            self.assertLess(fraction(update["same_pair_violation_after"]), fraction(update["violation_before"]))
        clipped = fit([x], contract([x.entry]), [x.entry], "parent", epochs=1, weight_bound=F(1, 10))
        self.assertTrue(all(abs(fraction(v)) <= F(1, 10) for v in clipped["weights"].values()))

    def test_invalid_fit_configuration_rejected(self):
        x = sample(); m = [x.entry]
        for kw in ({"epochs": True}, {"epochs": 0}, {"update_cap": F()}, {"weight_bound": 1.0},
                   {"boundary_weight": F(-1)}, {"transition_budget": 0}):
            with self.assertRaises(ValueError):
                fit([x], contract(m), m, "parent", **kw)

    def test_positive_margin_collision_is_logged_not_invented_feature(self):
        x = sample(specs=((0, 2, C), (0, 2, G)))
        # Synthetic feature erasure only: both actual existing signatures remain.
        from unittest.mock import patch
        with patch("musicanote_harness.harmony_functional_learning.path_features", return_value=dict.fromkeys(INITIAL_WEIGHTS, F())), \
             patch("musicanote_harness.harmony_functional_learning._decode") as dec:
            ids = [e.group_id for e in x.problem.edges]
            dec.side_effect = [{"selected": {"segments": [{"semantic_group_ref": ids[0]}]}},
                               {"selected": {"segments": [{"semantic_group_ref": ids[1]}]}, "training_loss": {"total": {"numerator": 1, "denominator": 1}}},
                               {"selected": {"segments": [{"semantic_group_ref": ids[0]}]}}]
            model = fit([x], contract([x.entry]), [x.entry], "parent", epochs=1)
        self.assertEqual(len(model["feature_collisions"]), 1); self.assertEqual(model["updates"], [])


if __name__ == "__main__":
    unittest.main()
