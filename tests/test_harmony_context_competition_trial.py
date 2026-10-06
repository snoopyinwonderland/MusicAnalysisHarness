from copy import deepcopy
from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_context_competition_trial as t
from test_harmony_context_competition import neighbor


class CompetitionTrialTests(unittest.TestCase):
    def packet(self):
        p, ev, ids = neighbor(); profile = t.observation.observe_path(p, ev, ids)
        a = {'selected': True, 'source_profile': profile,
             'reference_timing_diagnostic': [{'reference_boundary_at_exact_time': False} for _ in profile['transitions']],
             'unchanged_original_training_loss': {'total': t.s.q(1)}}
        return {'arms': {k: deepcopy(a) for k in t.prior.ARMS},
                'jointly_available_arm_minus_target_vectors': {k: t.vector_difference(profile, profile)
                    for k in t.prior.ARMS if k != 'epoch3_target'}}

    def test_vector_delta_unknown_not_zero(self):
        p = self.packet(); a = p['arms']['initial']['source_profile']; b = deepcopy(a)
        b['availability']['hold_explained_step_exposure'] = False
        b['features']['hold_explained_step_exposure'] = None
        delta = t.vector_difference(a, b)
        self.assertIsNone(delta['hold_explained_step_exposure'])
        self.assertEqual(delta['continuing_left_member_exposure'], t.s.q(0))

    def test_nonzero_delta_counted_without_accuracy_claim(self):
        p = self.packet(); p['jointly_available_arm_minus_target_vectors']['initial']['hold_explained_step_exposure'] = t.s.q(F(1, 8))
        r = t.summarize([p]); c = r['arm_minus_train_target']['initial']
        self.assertEqual(c['any_available_nonzero_delta'], 1)
        self.assertEqual(c['all_features_available_and_zero'], 0)
        self.assertTrue(r['new_accuracy_not_measured'])

    def test_abstention_preserved_not_added_to_zero_paths_or_contrasts(self):
        p = self.packet(); p['arms']['epoch3_adversary'] = {'selected': False, 'status': 'limit'}
        p['jointly_available_arm_minus_target_vectors']['epoch3_adversary'] = None
        r = t.summarize([p]); self.assertEqual(r['by_arm']['epoch3_adversary']['preserved_abstentions'], 1)
        self.assertNotIn('paths', r['by_arm']['epoch3_adversary'])
        self.assertNotIn('contrasts', r['arm_minus_train_target']['epoch3_adversary'])

    def test_reference_time_is_diagnostic_only_profile_unchanged(self):
        p = self.packet(); before = deepcopy(p['arms']['initial']['source_profile'])
        p['arms']['initial']['reference_timing_diagnostic'][0]['reference_boundary_at_exact_time'] = True
        r = t.summarize([p]); self.assertEqual(r['by_arm']['initial']['reference_time:dominant_credit_conflict'], 1)
        self.assertEqual(p['arms']['initial']['source_profile'], before)
        self.assertTrue(r['reference_time_match_is_not_correct_chord_or_nct_gold'])

    def test_cost_model_and_old_source_seals_not_promoted(self):
        self.assertEqual(t.prior.PINS['model.json.gz'], '2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf')
        self.assertEqual(len(t.observation.FEATURES), 7)
        self.assertNotIn('decode', t.observation.__dict__)


if __name__ == '__main__': unittest.main()
