from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_full_score_learning as l
from test_harmony_structured_learning import entry, contract

s = l.s


def initial(): return s.initial_weights(s.fresh.timing.ZERO)


def row(e=None):
    delta = dict.fromkeys(s.FEATURES, F()); delta['extra_member_complexity'] = F(-1)
    return {'entry': e or entry(), 'sample_id': 'a', 'contrast_id': 'c',
        'feature_delta': {k: s.q(v) for k, v in delta.items()},
        'feature_available': dict.fromkeys(s.FEATURES, True), 'loss': s.q(F(1, 4)),
        'initial_score_gap': s.q(s.feature_cost(delta, initial()))}


class FullLearningTests(unittest.TestCase):
    def test_deterministic_bounded_train_only_and_no_mutation(self):
        rows = [row()]; before = deepcopy(rows); manifest = [entry()]; c = contract(manifest)
        model = l.fit(rows, initial(), c, manifest, 'parent')
        self.assertEqual(model, l.fit(rows, initial(), c, manifest, 'parent'))
        weights = l.model_weights(model, initial(), c, manifest, 'parent')
        self.assertLess(weights['extra_member_complexity'], initial()['extra_member_complexity'])
        self.assertEqual(rows, before)
        for k in s.FIXED: self.assertEqual(weights[k], initial()[k])
        self.assertFalse(model['dev_labels_used']); self.assertFalse(model['fresh_adversary_search_during_fit'])
        self.assertLess(s.f(model['margin_violation_sum_after']), s.f(model['margin_violation_sum_before']))

    def test_unavailable_comparison_cannot_drive_gradient(self):
        r = row(); r['feature_available']['extra_member_complexity'] = False
        manifest = [entry()]; model = l.fit([r], initial(), contract(manifest), manifest, 'parent')
        self.assertEqual(model['weights'], model['initial_weights'])
        self.assertEqual(model['updates'], [])
        self.assertEqual(model['epochs'][0]['statuses']['known_feature_collision'], 1)

    def test_fixed_zero_delta_is_collision_not_success(self):
        r = row(); r['feature_delta'] = {k: s.q(0) for k in s.FEATURES}; r['initial_score_gap'] = s.q(0)
        manifest = [entry()]; model = l.fit([r], initial(), contract(manifest), manifest, 'parent')
        self.assertEqual(model['updates'], []); self.assertEqual(model['margin_violation_sum_after'], model['margin_violation_sum_before'])

    def test_dev_unapproved_and_entry_change_rejected(self):
        manifest = [entry(), entry('dev', 'dev')]
        for e in (manifest[1], entry('absent'), entry() | {'title': 'changed'}):
            with self.assertRaises(ValueError): l.fit([row(e)], initial(), contract(manifest), manifest, 'parent')

    def test_duplicate_missing_nonpositive_loss_and_tampered_gap(self):
        manifest = [entry()]; c = contract(manifest)
        with self.assertRaisesRegex(ValueError, 'duplicate'): l.fit([row(), row()], initial(), c, manifest, 'parent')
        for bad in (row() | {'loss': s.q(0)}, row() | {'initial_score_gap': s.q(999)}, row() | {'feature_available': {}}):
            with self.assertRaises(ValueError): l.fit([bad], initial(), c, manifest, 'parent')
        with self.assertRaises(ValueError): l.fit([], initial(), c, manifest, 'parent')
        with self.assertRaises(ValueError): l.fit([row()], initial(), c, manifest, 'parent', epochs=True)

    def test_model_tampering_and_rights_expansion_rejected(self):
        manifest = [entry()]; c = contract(manifest); model = l.fit([row()], initial(), c, manifest, 'parent')
        for bad in (model | {'production_deployment': True}, model | {'weights': {}}, model | {'dev_labels_used': True}):
            with self.assertRaises(ValueError): l.model_weights(bad, initial(), c, manifest, 'parent')
        c['restrictions']['commercial_use'] = True
        with self.assertRaises(ValueError): l.fit([row()], initial(), c, manifest, 'parent')
