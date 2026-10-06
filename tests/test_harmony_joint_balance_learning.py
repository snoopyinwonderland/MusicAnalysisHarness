from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_joint_balance_learning as l
from test_harmony_score_balance_ledger import fixture
from test_harmony_structured_learning import entry, contract


def initial(): return fixture()[2]


def row():
    delta = dict.fromkeys(l.FEATURES, l.q(0)); delta['missing_member_fraction'] = l.q(1)
    return {'entry': entry(), 'sample_id': 'sample', 'contrast_id': 'contrast', 'loss': l.q(F(1, 4)),
            'score_delta': delta, 'gradient_delta': deepcopy(delta), 'available': dict.fromkeys(l.FEATURES, True)}


def fit(rows):
    manifest = [entry()]
    return l.fit(rows, initial(), contract(manifest), manifest, 'parent', 'pool')


class JointBalanceLearningTests(unittest.TestCase):
    def test_group_partition_exactly_28_trainable_and_7_fixed(self):
        self.assertEqual(len(l.TRAINABLE), 28); self.assertEqual(len(l.FIXED), 7)
        self.assertEqual(set(l.TRAINABLE) | set(l.FIXED), set(l.FEATURES))
        self.assertFalse(set(l.TRAINABLE) & set(l.FIXED))

    def test_fit_deterministic_immutable_bounded_and_all_visits_averaged(self):
        r = row(); r['loss'] = l.q(99); before = deepcopy(r); m = fit([r]); start = initial()
        self.assertEqual(m, fit([r])); self.assertEqual(r, before); self.assertEqual(m['averaging_ticks'], 3)
        for k, v in m['weights'].items():
            self.assertLessEqual(abs(l.f(v)-start[k]), l.RADIUS)
            if k in l.FIXED: self.assertEqual(l.f(v), start[k])
        self.assertGreater(l.f(m['weights']['missing_member_fraction']), start['missing_member_fraction'])
        self.assertLess(l.f(m['margin_sum_after']), l.f(m['margin_sum_before']))

    def test_fixed_observed_deltas_cannot_update_fixed_coefficients(self):
        r = row(); r['loss'] = l.q(99)
        r['score_delta'] = dict.fromkeys(l.FEATURES, l.q(0)); r['score_delta']['unknown_root'] = l.q(1)
        r['gradient_delta'] = deepcopy(r['score_delta']); m = fit([r])
        self.assertEqual(m['weights'], m['initial_weights']); self.assertEqual(m['updates'], [])

    def test_unknown_partial_score_not_observed_zero_or_gradient(self):
        r = row(); k = 'missing_member_fraction'; r['available'][k] = False
        r['gradient_delta'][k] = None; r['score_delta'][k] = l.q(-99)
        m = fit([r]); self.assertEqual(m['updates'], [])
        self.assertEqual(l.gap(r, initial()), -99*initial()[k])

    def test_zero_loss_controls_remain_in_averaging(self):
        r = row(); r['loss'] = l.q(0); r['contrast_id'] = 'control'
        m = fit([row(), r]); self.assertEqual(m['averaging_ticks'], 6)
        self.assertEqual(m['training_contrasts'], 2)

    def test_other_known_updates_do_not_round_unknown_non_grid_weight(self):
        r = row(); r['loss'] = l.q(99); k = l.ledger.context.FEATURES[0]
        r['available'][k] = False; r['gradient_delta'][k] = None; r['score_delta'][k] = l.q(-1)
        m = fit([r]); self.assertTrue(m['updates'])
        self.assertEqual(m['weights'][k], m['initial_weights'][k])
        self.assertTrue(all(v['weights'][k] == m['initial_weights'][k] for v in m['updates']))

    def test_semantic_bounds_intersect_trust_radius_and_fixed_non_grid_preserved(self):
        start = initial(); start['harmonic_run_count'] = F(1, 10000)
        box = l.bounds(start); self.assertEqual(box['harmonic_run_count'][0], F(1, 10000))
        self.assertEqual(box['conditional_step_ornament_exposure'][1], min(F(), start['conditional_step_ornament_exposure']+l.RADIUS))
        r = row(); r['loss'] = l.q(99); start['dominant_family_seventh_step'] = F(-1, 7)
        manifest = [entry()]; m = l.fit([r], start, contract(manifest), manifest, 'parent', 'pool')
        self.assertEqual(l.f(m['weights']['dominant_family_seventh_step']), F(-1, 7))

    def test_nontrain_mutated_unapproved_duplicate_and_empty_rejected(self):
        for bad in (row() | {'entry': entry(split='dev')}, row() | {'entry': entry() | {'changed': True}},
                    row() | {'entry': entry('absent')}):
            with self.assertRaises(ValueError): fit([bad])
        with self.assertRaises(ValueError): fit([row(), row()])
        with self.assertRaises(ValueError): fit([])

    def test_invalid_keys_mask_gradient_and_loss_rejected(self):
        k = 'missing_member_fraction'; r = row()
        for bad in (r | {'score_delta': {}}, r | {'loss': l.q(-1)},
                    r | {'available': r['available'] | {k: 1}},
                    r | {'gradient_delta': r['gradient_delta'] | {k: None}},
                    r | {'available': r['available'] | {k: False}}):
            with self.assertRaises(ValueError): fit([bad])

    def test_model_binds_initial_pool_use_configuration_and_rejects_deployment(self):
        m = fit([row()]); manifest = [entry()]; c = contract(manifest)
        self.assertEqual(l.model_weights(m, initial(), c, manifest, 'parent', 'pool'), {k: l.f(v) for k, v in m['weights'].items()})
        for bad in (m | {'dev_used': True}, m | {'production_deployment': True}, m | {'weights': {}}, m | {'bounds': {}}):
            with self.assertRaises(ValueError): l.model_weights(bad, initial(), c, manifest, 'parent', 'pool')
        with self.assertRaises(ValueError): l.model_weights(m, initial(), c, manifest, 'parent', 'changed')
        c['restrictions']['commercial_use'] = True
        with self.assertRaises(ValueError): l.model_weights(m, initial(), c, manifest, 'parent', 'pool')


if __name__ == '__main__': unittest.main()
