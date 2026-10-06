from copy import deepcopy
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import harmony_online_score_trial as t
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C


def row(sample, reachable=True, accepted=True):
    return {'sample_id': sample, 'split': 'train', 'work_family_id': 'f',
        'candidate_ceiling': {'reachable': reachable}, 'source_clock_gate': {'accepted': accepted}}


class OnlineTrialTests(unittest.TestCase):
    def test_cohort_includes_correct_and_incorrect_not_only_old_errors(self):
        rows = [row('a') | {'previous_correct': True}, row('b'), row('c', False), row('d', None), row('e', True, False)]
        before = deepcopy(rows)
        self.assertEqual([r['sample_id'] for r in t.cohort(rows)], ['a', 'b'])
        self.assertEqual(rows, before)

    def test_nontrain_and_duplicate_cohort_rejected(self):
        for rows in ([row('a'), row('a')], [row('a') | {'split': 'dev'}]):
            with self.assertRaises(ValueError): t.cohort(rows)

    def test_current_winner_and_compatible_target_source_features(self):
        graph, ev = problem(); w = t.s.initial_weights(t.s.fresh.timing.ZERO)
        cells = ({'start': graph.points[0], 'end': graph.points[-1], 'signature': C},)
        gold, ceiling = t.s.fresh.reachable_target(graph, cells)
        self.assertTrue(ceiling['reachable'])
        sc, ts = t.s.Scorer(graph, ev, w), t.s.Scorer(gold, ev, w)
        value = t.comparison(sc, ts, sc.decode(), ts.decode(), t.prior.training_loss(graph, cells))
        self.assertFalse(value['resource_abstention'])
        self.assertEqual(set(value['feature_delta']), set(t.s.FEATURES))
        self.assertFalse(value['ordinary_source_labels_used'])
        self.assertEqual(t.s.f(value['negative_cost'])-t.s.f(value['target_cost']),
            t.s.feature_cost({k: t.s.f(v) for k, v in value['feature_delta'].items()}, w))

    def test_abstention_has_no_partial_contrast(self):
        value = t.comparison(None, None, {'selected': None, 'status': 'budget'}, {'selected': {}, 'status': 'selected'}, None)
        self.assertTrue(value['resource_abstention']); self.assertNotIn('feature_delta', value)

    def test_no_overwrite(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)
