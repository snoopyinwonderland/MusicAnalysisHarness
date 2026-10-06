from copy import deepcopy
from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_transition_support_trial as t
from test_harmony_transition_support import evidence, graph
from test_harmony_functional_scoring import C, G7


class TransitionSupportTrialTests(unittest.TestCase):
    def packet(self):
        ev = evidence([('b', ('B', 0), 0, 1, 59, 'v'), ('c', ('C', 0), 1, 2, 60, 'v')], links=(('b', 'c'),))
        p, ids = graph(((0, 1, G7), (1, 2, C)))
        profile = t.observation.observe_path(p, ev, ids)
        arm = {'selected': True, 'source_profile': profile,
               'reference_diagnostic': t.diagnose_reference(profile, frozenset()),
               'training_loss': {'total': t.s.q(1), 'normalized_time_error': t.s.q(F(1, 2))}}
        return {'stored_path_changed': False, 'arms': {k: deepcopy(arm) for k in t.ARMS}}

    def test_thin_support_credited_at_extra_time_counted_not_confirmed(self):
        r = t.summarize([self.packet()])['by_arm']['adversarial_frozen']
        self.assertEqual(r['extra_time'], 1)
        self.assertEqual(r['extra_time:complete_run:credited:union_lt_two'], 1)
        self.assertEqual(r['dominant_credited'], 1)

    def test_reference_diagnostics_separate_and_do_not_mutate_source_profile(self):
        p = self.packet()['arms']['initial']['source_profile']; before = deepcopy(p)
        d = t.diagnose_reference(p, frozenset({F(1)}))
        self.assertTrue(d[0]['reference_boundary_at_exact_time']); self.assertEqual(p, before)
        self.assertFalse(p['source_labels_used']); self.assertNotIn('reference_diagnostic', p)

    def test_resource_abstention_kept_not_scored_as_zero(self):
        p = self.packet(); p['arms']['epoch3_adversary'] = {'selected': False, 'status': 'limit'}
        r = t.summarize([p])['by_arm']['epoch3_adversary']
        self.assertEqual(r['preserved_resource_abstentions'], 1); self.assertNotIn('zero_training_loss', r)

    def test_unknown_support_not_thin_zero(self):
        p = self.packet()
        for a in p['arms'].values():
            a['source_profile']['transitions'][0]['right_complete_run']['right_union_member_count'] = None
        r = t.summarize([p])['by_arm']['initial']
        self.assertEqual(r['extra_time:complete_run:unavailable'], 1)
        self.assertNotIn('extra_time:complete_run:credited:union_lt_two', r)

    def test_same_cost_arm_inventory_and_no_decoder_contract(self):
        self.assertEqual(len(t.ARMS), 5)
        self.assertNotIn('decode', t.observation.__dict__)
        self.assertEqual(t.PINS['model.json.gz'], '2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf')


if __name__ == '__main__': unittest.main()
