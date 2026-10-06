from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest
from musicanote_harness import harmony_recipe_balance as s
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C, G, G7, F64

BROAD = (("G", 0), (("B", 0), ("C", 0), ("D", 0), ("F", 0), ("G", 0)))


class RecipeTests(unittest.TestCase):
    def test_exact_vocabulary_and_functional_surface_not_penalized(self):
        for sig in (C, G, G7, F64):
            self.assertEqual(s.recipe(sig)[0], 0)

    def test_union_has_separate_residual_not_zero_missing_information(self):
        graph, ev = problem()
        values, receipts = s.features(graph, ev.source, F(), F(4), BROAD)
        self.assertEqual(values[s.FEATURE], F(1, 5))
        self.assertIsNone(values['absent_third_exposure'])
        self.assertEqual({tuple(x) for row in receipts[-1]['equally_close_recipes']
                          for x in row['outside_declared_members']}, {('C', 0)})
        self.assertFalse(receipts[-1]['confirmed_nct'])

    def test_spelling_not_pitch_class(self):
        sharp = (("G", 0), (("B", 0), ("D", 0), ("E", 1), ("G", 0)))
        self.assertGreater(s.recipe(sharp)[0], 0)
        self.assertEqual(s.recipe(G7)[0], 0)  # E# and F must not collapse

    def test_root_unknown_preserved_and_tied_recipes_exposed(self):
        residual, alternatives = s.recipe((None, C[1]))
        self.assertEqual(residual, 0)
        self.assertTrue(alternatives)
        graph, ev = problem()
        row = s.features(graph, ev.source, F(), F(4), (None, C[1]))[1][-1]
        self.assertFalse(row['root_available'])

    def test_distance_not_number_of_members_alone(self):
        bad = (("C", 0), (("C", 0), ("D", 0), ("G", 0)))
        self.assertEqual(s.recipe(C)[0], 0)
        self.assertEqual(s.recipe(bad)[0], F(1, 3))

    def test_unknown_meter_does_not_invent_role_observation(self):
        graph, ev = problem()
        ev.source.measures = (); ev.source._measure_times = (); ev.source._metric_cache.clear()
        values, _ = s.features(graph, ev.source, F(), F(4), BROAD)
        self.assertEqual(values[s.FEATURE], F(1, 5))
        self.assertIsNone(values['durable_nonmember_exposure'])

    def test_direct_indexed_and_partition_invariance(self):
        graph, ev = problem(); before = deepcopy(graph)
        scorer = s.Scorer(graph, ev, s.ZERO | {s.FEATURE: F(1, 2)})
        for i, a in enumerate(graph.points):
            for b in graph.points[i+1:]:
                for sig in (C, G7, BROAD):
                    self.assertEqual(s.features(graph, ev.source, a, b, sig)[0],
                        s.features(graph, ev.source, a, b, sig, index=scorer.index)[0])
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        whole = (by[F(), F(4), C],)
        split = (by[F(), F(1), C], by[F(1), F(2), C], by[F(2), F(4), C])
        self.assertEqual(scorer.path_features(whole), scorer.path_features(split))
        self.assertEqual(scorer.score_path(whole), scorer.score_path(split))
        self.assertEqual(graph, before)

    def test_zero_residual_preserves_frozen_support_score(self):
        ir = fixture(); before = deepcopy(ir); graph, ev = problem(ir)
        weights = {k: F(1, 3) for k in s.support.FEATURES}
        old = s.support.Scorer(graph, ev, weights).decode()
        new = s.Scorer(graph, ev, weights | {s.FEATURE: F()}).decode()
        self.assertEqual(old['selected']['segments'], new['selected']['segments'])
        self.assertEqual(old['selected']['score_cost'], new['selected']['score_cost'])
        self.assertEqual(ir, before)

    def test_soft_residual_keeps_candidates_and_exact_joint_minimum(self):
        graph, ev = problem(); rng = random.Random(6801)
        # Introduce a broad candidate without removing any source notes.
        edges = graph.edges + tuple(replace(e, signature=BROAD, group_id='broad_'+e.group_id)
            for e in graph.edges if e.signature == C)
        for _ in range(5):
            tiny = replace(graph, edges=tuple(e for e in edges if e.signature in (C, G, BROAD)
                                              and rng.random() < .6), max_segments=3)
            scorer = s.Scorer(tiny, ev, {k: F(rng.randrange(4), 4) for k in s.FEATURES})
            paths = []
            def visit(i, ids):
                if i == len(tiny.points)-1:
                    paths.append((scorer.score_path(ids), ids)); return
                if len(ids) >= tiny.max_segments: return
                for e in tiny.edges:
                    if e.start_index == i: visit(e.end_index, ids+(e.group_id,))
            visit(0, ())
            result = scorer.decode()
            if not paths: self.assertIsNone(result['selected']); continue
            selected = result['selected']
            self.assertEqual((s.support.f(selected['score_cost']), tuple(x['semantic_group_ref']
                for x in selected['segments'])), min(paths))

    def test_invalid_inputs(self):
        for v in (True, .1, F(-1), F(2)):
            with self.assertRaises(ValueError): s.coefficients(s.ZERO | {s.FEATURE: v})
        with self.assertRaises(ValueError): s.recipe((('C', 0), ()))
