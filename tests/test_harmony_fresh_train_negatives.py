from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_fresh_train_negatives as s
from musicanote_harness.harmony_common_benchmark import native_prediction
from test_harmony_exact_frontier import problem
from test_harmony_bounded_recovery import fixture
from test_harmony_functional_scoring import C, G, G7


class FreshTests(unittest.TestCase):
    def test_direct_equals_indexed_current_scores_and_source_unchanged(self):
        ir = fixture(); before = deepcopy(ir); graph, ev = problem(ir)
        weights = {k: F(1, 3) for k in s.timing.FEATURES}
        normal = s.timing.Scorer(graph, ev, weights).decode()['selected']
        direct = s.direct_scorer(graph, ev, weights).decode()['selected']
        self.assertEqual(normal, direct); self.assertEqual(ir, before)

    def test_missing_measure_grid_uses_direct_without_adding_candidate_points(self):
        graph, ev = problem(fixture([('G3', 0, 8, 'b'), ('B3', 0, 8, 't'), ('D4', 0, 8, 'f')], end=8), end=8)
        edges = tuple(replace(e, start_index=0, end_index=1) for e in graph.edges if e.start == 0 and e.end == 8)
        coarse = replace(graph, points=(F(), F(8)), edges=edges)
        with self.assertRaisesRegex(ValueError, 'index_missing_measure_boundary'):
            s.timing.Scorer(coarse, ev, s.timing.ZERO)
        scorer = s.direct_scorer(coarse, ev, s.timing.ZERO)
        result = scorer.decode(); self.assertIsNotNone(result['selected'])
        self.assertEqual(coarse.points, (F(), F(8))); self.assertEqual(result['search_diagnostics']['original_edges'], len(edges))
        self.assertEqual(s.q(scorer.score_path(s.path_ids(result['selected']))), result['selected']['score_cost'])

    def test_tiny_exhaustive_joint_optimum_and_cap(self):
        graph, ev = problem(); rng = random.Random(7001)
        for _ in range(8):
            tiny = replace(graph, edges=tuple(e for e in graph.edges if e.signature in (C, G, G7) and rng.random() < .5), max_segments=3)
            scorer = s.direct_scorer(tiny, ev, {k: F(rng.randrange(4), 4) for k in s.timing.FEATURES}); paths = []
            def visit(i, ids):
                if i == len(tiny.points)-1: paths.append((scorer.score_path(ids), ids)); return
                if len(ids) >= tiny.max_segments: return
                for e in tiny.edges:
                    if e.start_index == i: visit(e.end_index, ids+(e.group_id,))
            visit(0, ()); result = scorer.decode()
            if not paths: self.assertIsNone(result['selected']); continue
            self.assertEqual((s.f(result['selected']['score_cost']), s.path_ids(result['selected'])), min(paths))

    def test_ceiling_separates_missing_candidate_and_raw_cap(self):
        graph, ev = problem(); cells = ({'start': F(), 'end': F(2), 'signature': G}, {'start': F(2), 'end': F(4), 'signature': C})
        gold, ceiling = s.reachable_target(graph, cells); self.assertTrue(ceiling['reachable'])
        _, blocked = s.reachable_target(replace(graph, max_segments=1), cells)
        self.assertEqual(blocked['reason'], 'raw_segment_cap_blocks_reference')
        _, absent = s.reachable_target(replace(graph, edges=tuple(e for e in graph.edges if e.signature == C)), cells)
        self.assertEqual(absent['reason'], 'no_compatible_path_in_original_graph')
        self.assertTrue(set(e.group_id for e in gold.edges) <= {e.group_id for e in graph.edges})

    def test_partial_and_unready_ceiling_not_false_negative(self):
        graph, _ = problem(); cells = ({'start': F(), 'end': F(4), 'signature': None},)
        self.assertIsNone(s.reachable_target(graph, cells)[1]['reachable'])
        self.assertEqual(s.reachable_target(replace(graph, status='bad'), cells)[1]['reason'], 'lattice_unavailable')

    def test_compatible_target_never_blind_prediction(self):
        graph, ev = problem(); cells = ({'start': F(), 'end': F(4), 'signature': G},)
        gold, _ = s.reachable_target(graph, cells)
        chosen = s.target_choice(gold, ev, s.timing.ZERO)['selected']
        self.assertTrue(chosen['training_reference_labels_used'])
        with self.assertRaisesRegex(ValueError, 'nonblind_prediction'):
            native_prediction(chosen, {'start': s.q(0), 'end': s.q(4)})

    def pair(self):
        graph, ev = problem(); cells = ({'start': F(), 'end': F(4), 'signature': G},)
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        scorer = s.direct_scorer(graph, ev, s.timing.ZERO)
        def pred(sig):
            ids = (by[F(), F(4), sig],)
            return {'segments': [{'semantic_group_ref': ids[0]}], 'score_cost': s.q(scorer.score_path(ids))}
        return graph, ev, cells, pred(C), pred(G)

    def test_contrast_exact_loss_cost_and_ids(self):
        graph, ev, cells, n, t = self.pair()
        row = s.contrast('sample', {'split': 'train'}, graph, ev, cells, n, t, s.timing.ZERO)
        self.assertGreater(s.f(row['loss']), 0); self.assertEqual(row['current_score_gap'], row['base_cost_gap'])
        self.assertFalse(row['source_labels_used_for_negative_selection'])
        self.assertEqual(set(row['feature_delta']), set(s.timing.FEATURES))

    def test_not_a_negative_when_reference_already_matches(self):
        graph, ev, cells, _, t = self.pair()
        with self.assertRaisesRegex(ValueError, 'positive_loss'):
            s.contrast('sample', {}, graph, ev, cells, t, t, s.timing.ZERO)

    def test_invalid_target_and_tampered_cost_rejected(self):
        graph, ev, cells, n, t = self.pair()
        with self.assertRaisesRegex(ValueError, 'not_compatible'):
            s.contrast('sample', {}, graph, ev, cells, n, n, s.timing.ZERO)
        t['score_cost'] = s.q(999)
        with self.assertRaisesRegex(ValueError, 'cost_mismatch'):
            s.contrast('sample', {}, graph, ev, cells, n, t, s.timing.ZERO)

    def test_receipts_preserve_original_note_ids_and_target_status(self):
        graph, ev, cells, n, _ = self.pair()
        receipt = s.path_receipt(s.direct_scorer(graph, ev, s.timing.ZERO), s.path_ids(n), target=True)
        self.assertTrue(receipt['source_labels_used_to_create_this_path'])
        self.assertTrue(any(r.get('source_note_ids') for r in receipt['source_support']))

    def test_budget_abstention_never_partial_winner(self):
        graph, ev = problem()
        result = s.direct_scorer(graph, ev, s.timing.ZERO).decode(transition_budget=1)
        self.assertIsNone(result['selected']); self.assertFalse(result['exact_optimum_under_declared_score'])
