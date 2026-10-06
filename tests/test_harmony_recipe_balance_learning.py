from copy import deepcopy
from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_recipe_balance_learning as s
from musicanote_harness.harmony_structured_learning import content_hash
from test_harmony_structured_learning import entry, contract


def row():
    return {'entry': entry(), 'sample_id': 's', 'contrast_id': 'one',
        'feature_delta': {s.FEATURE: {'numerator': 1, 'denominator': 3}},
        'feature_available': {s.FEATURE: True}, 'loss': {'numerator': 1, 'denominator': 1},
        'base_cost_gap': {'numerator': 0, 'denominator': 1}}


class LearningTests(unittest.TestCase):
    def test_fit_replay_and_one_coefficient_only(self):
        rows = [row()]; before = deepcopy(rows); m = [entry()]; c = contract(m)
        a = s.fit(rows, c, m, c['parent_recall_sha256'])
        b = s.fit(rows, c, m, c['parent_recall_sha256'])
        self.assertEqual(a, b); self.assertEqual(rows, before)
        w = s.model_weights(a, c, m, c['parent_recall_sha256'])
        self.assertEqual(set(w), {s.FEATURE}); self.assertGreater(w[s.FEATURE], 0)
        self.assertFalse(a['dev_labels_used'])

    def test_dev_and_unapproved_rows_rejected(self):
        m = [entry()]; c = contract(m)
        r = row(); r['entry'] = r['entry'] | {'split': 'dev'}
        with self.assertRaisesRegex(ValueError, 'nontrain'): s.fit([r], c, m, c['parent_recall_sha256'])
        r = row(); r['entry'] = r['entry'] | {'work_family_id': 'altered'}
        with self.assertRaisesRegex(ValueError, 'binding'): s.fit([r], c, m, c['parent_recall_sha256'])

    def test_negative_delta_not_incentive_to_increase_penalty(self):
        m = [entry()]; c = contract(m); r = row()
        r['feature_delta'][s.FEATURE] = {'numerator': -1, 'denominator': 3}
        self.assertEqual(s.fit([r], c, m, c['parent_recall_sha256'])['weights'][s.FEATURE],
                         {'numerator': 0, 'denominator': 1})

    def test_missing_feature_and_duplicate_contrasts_rejected(self):
        m = [entry()]; c = contract(m); r = row(); r['feature_available'][s.FEATURE] = False
        with self.assertRaisesRegex(ValueError, 'unavailable'): s.fit([r], c, m, c['parent_recall_sha256'])
        with self.assertRaisesRegex(ValueError, 'duplicate'): s.fit([row(), row()], c, m, c['parent_recall_sha256'])

    def test_model_contract_tampering(self):
        m = [entry()]; c = contract(m); model = s.fit([row()], c, m, c['parent_recall_sha256'])
        with self.assertRaisesRegex(ValueError, 'contract'):
            s.model_weights(model | {'dev_labels_used': True}, c, m, c['parent_recall_sha256'])
