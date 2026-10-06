import itertools
import unittest
from dataclasses import replace
from fractions import Fraction as F

from musicanote_harness.harmony_whole_score import CellSearch, model_weights, geometry
from musicanote_harness.harmony_bounded_recovery import grace_projection, bound_evidence
from musicanote_harness.harmony_scored_decoder import Problem, Edge
from musicanote_harness.harmony_full_score import Scorer
from musicanote_harness.formal_ir import q
from test_harmony_bounded_recovery import fixture

C = (('C', 0), (('C', 0), ('E', 0), ('G', 0)))
G = (('G', 0), (('B', 0), ('D', 0), ('G', 0)))


def problem():
    ir = fixture()
    view, grace = grace_projection(ir)
    _, ev, _ = bound_evidence(view, {'start': q(0), 'end': q(4)}, grace)
    points = tuple(map(F, (0, 1, 2, 4)))
    p = Problem(points, (), 3, sum((e.end-e.start for e in ev.source.events), F()), 'ready')
    batches = []
    for i in range(3):
        active = [e for e in ev.source.events if e.start < points[i+1] and points[i] < e.end]
        attacks = frozenset(e.pitch for e in active if e.start == points[i])
        batches.append(tuple(Edge(f'{i}_{j}', i, i+1, points[i], points[i+1], sig, {},
            attacks, tuple(e.event_id for e in active), (), {}) for j, sig in enumerate((C, G))))
    return p, ev, batches


class WholeScoreTests(unittest.TestCase):
    def test_wide_beam_matches_exhaustive_original_frozen_cost(self):
        p, ev, batches = problem()
        graph = replace(p, edges=tuple(e for batch in batches for e in batch))
        sc = Scorer(graph, ev, model_weights())
        expected = min((sc.score_path(tuple(e.group_id for e in path)), tuple(e.group_id for e in path))
                       for path in itertools.product(*batches))
        s = CellSearch(p, ev, model_weights(), beam_width=128)
        for batch in batches:
            s.consume(batch)
        r = s.finish()
        self.assertEqual((F(r['score_cost']), r['selected']), expected)
        self.assertEqual(r['states_discarded'], 0)
        self.assertTrue(r['independently_rescored'])

    def test_narrow_beam_reports_loss_not_exact_optimum(self):
        p, ev, batches = problem()
        s = CellSearch(p, ev, model_weights(), beam_width=1)
        for batch in batches:
            s.consume(batch)
        r = s.finish()
        self.assertGreater(r['states_discarded'], 0)
        self.assertFalse(r['exact_optimum_claimed'])
        self.assertTrue(r['independently_rescored'])

    def test_held_run_keeps_start_across_computational_pages(self):
        p, ev, batches = problem()
        s = CellSearch(p, ev, model_weights())
        for batch in batches:
            s.consume((batch[0],))
            self.assertEqual(next(iter(s.frontier))[0], 0)
        r = s.finish()
        self.assertEqual(r['status'], 'complete')

    def test_incomplete_path_cannot_be_submitted(self):
        p, ev, batches = problem()
        s = CellSearch(p, ev, model_weights())
        s.consume(batches[0])
        with self.assertRaisesRegex(ValueError, 'partial_path'):
            s.finish()

    def test_operation_abort_never_returns_partial_winner(self):
        p, ev, batches = problem()
        s = CellSearch(p, ev, model_weights(), operations=1)
        s.consume(batches[0])
        self.assertEqual(s.finish()['status'], 'operation_budget_abstention')
        self.assertIsNone(s.finish()['selected'])

    def test_invalid_geometry_and_budget(self):
        p, ev, batches = problem()
        with self.assertRaisesRegex(ValueError, 'budget'):
            CellSearch(p, ev, model_weights(), beam_width=0)
        s = CellSearch(p, ev, model_weights())
        with self.assertRaisesRegex(ValueError, 'nonatomic'):
            s.consume((replace(batches[0][0], end_index=2),))

    def test_original_fractional_coordinates_and_measure_pages(self):
        ir = fixture([('C3', 0, 8, 'b'), ('E3', 0, 8, 'i'), ('G3', 0, 8, 'j'),
                      ('C4', F(1, 3), F(2, 3), 'lead')], end=8)
        points, pages = geometry(ir, F(8))
        self.assertIn(F(1, 3), points)
        self.assertIn(F(2, 3), points)
        self.assertTrue(any(points[hi] == 4 for _, hi in pages))
        self.assertEqual(points[0], 0)
        self.assertEqual(points[-1], 8)


if __name__ == '__main__':
    unittest.main()
