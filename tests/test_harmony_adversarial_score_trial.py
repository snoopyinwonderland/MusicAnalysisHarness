from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import harmony_adversarial_score_trial as t
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C


class AdversarialTrialTests(unittest.TestCase):
    def test_real_run_aware_adversary_contrast_satisfies_learning_contract(self):
        graph, ev = problem(); w = t.s.initial_weights(t.s.fresh.timing.ZERO)
        cells = ({'start': graph.points[0], 'end': graph.points[-1], 'signature': C},)
        gold, _ = t.s.fresh.reachable_target(graph, cells)
        sc, ts = t.s.Scorer(graph, ev, w), t.s.Scorer(gold, ev, w)
        loss = t.online.prior.training_loss(graph, cells)
        value = t.prior.contrast(sc, ts, sc.decode(), t.prior.adversary.decode(sc, loss), ts.decode(), loss)
        t.learning.validate_observation(value, w)
        self.assertFalse(value['analysis_export_allowed'])
        if not value['resource_abstention']: self.assertTrue(value['source_labels_used_for_negative_selection'])

    def test_existing_output_is_never_overwritten(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(root)


if __name__ == '__main__': unittest.main()
