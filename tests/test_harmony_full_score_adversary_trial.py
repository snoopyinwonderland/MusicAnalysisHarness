from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import harmony_full_score_adversary_trial as t
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C


class AdversaryTrialTests(unittest.TestCase):
    def test_source_features_and_reference_flags_are_training_only(self):
        graph, ev = problem(); weights = t.s.initial_weights(t.s.fresh.timing.ZERO)
        cells = ({'start': graph.points[0], 'end': graph.points[-1], 'signature': C},)
        gold, _ = t.s.fresh.reachable_target(graph, cells)
        sc, ts = t.s.Scorer(graph, ev, weights), t.s.Scorer(gold, ev, weights)
        loss = t.online.prior.training_loss(graph, cells)
        value = t.contrast(sc, ts, sc.decode(), t.adversary.decode(sc, loss), ts.decode(), loss)
        self.assertFalse(value['resource_abstention'])
        self.assertTrue(value['source_labels_used_for_negative_selection'])
        self.assertNotIn('ordinary_source_labels_used', value)
        self.assertFalse(value['analysis_export_allowed']); self.assertFalse(value['weight_update_performed'])
        self.assertEqual(t.s.f(value['negative_cost'])-t.s.f(value['target_cost']),
            t.s.feature_cost({k: t.s.f(v) for k, v in value['feature_delta'].items()}, weights))

    def test_abstention_never_yields_partial_learning_vector(self):
        result = {'selected': None, 'status': 'budget'}
        value = t.contrast(None, None, result, result, result, None)
        self.assertTrue(value['resource_abstention']); self.assertNotIn('feature_delta', value)

    def test_mismatched_adversary_loss_is_rejected(self):
        graph, ev = problem(); weights = t.s.initial_weights(t.s.fresh.timing.ZERO)
        cells = ({'start': graph.points[0], 'end': graph.points[-1], 'signature': C},)
        gold, _ = t.s.fresh.reachable_target(graph, cells)
        sc, ts = t.s.Scorer(graph, ev, weights), t.s.Scorer(gold, ev, weights)
        loss = t.online.prior.training_loss(graph, cells); negative = t.adversary.decode(sc, loss)
        with self.assertRaisesRegex(ValueError, 'adversary_not_complete'):
            t.contrast(sc, ts, sc.decode(), negative | {'augmented_cost': t.s.q(999)}, ts.decode(), loss)

    def test_output_no_overwrite(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)


if __name__ == '__main__': unittest.main()
