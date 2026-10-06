from copy import deepcopy
from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_support_balance_learning as l
from test_harmony_structured_learning import entry,contract


def row(e=None):
    return {'entry':e or entry(),'sample_id':'a','contrast_id':'c',
            'feature_delta':{k:l.q(F(1) if k==l.FEATURES[0] else F()) for k in l.FEATURES},
            'feature_available':dict.fromkeys(l.FEATURES,True),'loss':l.q(F(1,4)),
            'base_cost_gap':l.q(F())}


class BalanceLearningTests(unittest.TestCase):
    def test_deterministic_bounded_train_only_learning_and_no_mutation(self):
        rows=[row()];before=deepcopy(rows);m=[entry()]
        model=l.fit(rows,contract(m),m,'parent')
        self.assertEqual(model,l.fit(rows,contract(m),m,'parent'))
        self.assertGreater(l.f(model['weights'][l.FEATURES[0]]),0)
        self.assertTrue(all(0<=l.f(v)<=1 for v in model['weights'].values()))
        self.assertLess(l.f(model['margin_violation_sum_after']),l.f(model['margin_violation_sum_before']))
        self.assertFalse(model['dev_labels_used']);self.assertFalse(model['production_deployment'])
        self.assertFalse(model['configuration']['fresh_adversary_search']);self.assertEqual(rows,before)

    def test_dev_or_unapproved_entry_cannot_train(self):
        m=[entry(),entry('dev','dev')]
        for e in (m[1],entry('absent')):
            with self.assertRaisesRegex(ValueError,'nontrain'):l.fit([row(e)],contract(m),m,'parent')

    def test_duplicate_and_missing_feature_rejected(self):
        m=[entry()]
        with self.assertRaisesRegex(ValueError,'duplicate'):l.fit([row(),row()],contract(m),m,'parent')
        r=row();r['feature_available'][l.FEATURES[0]]=False
        with self.assertRaisesRegex(ValueError,'unavailable'):l.fit([r],contract(m),m,'parent')

    def test_empty_zero_loss_and_invalid_epoch_rejected(self):
        m=[entry()]
        with self.assertRaises(ValueError):l.fit([],contract(m),m,'parent')
        r=row();r['loss']=l.q(F())
        with self.assertRaises(ValueError):l.fit([r],contract(m),m,'parent')
        with self.assertRaises(ValueError):l.fit([row()],contract(m),m,'parent',epochs=True)

    def test_zero_delta_logged_as_collision_not_success(self):
        r=row();r['feature_delta']={k:l.q(F()) for k in l.FEATURES};m=[entry()]
        model=l.fit([r],contract(m),m,'parent')
        self.assertEqual(model['updates'],[])
        self.assertEqual(model['epochs'][0]['statuses']['new_feature_collision'],1)
        self.assertEqual(model['margin_violation_sum_before'],model['margin_violation_sum_after'])

    def test_source_contract_change_rejected(self):
        m=[entry()];c=contract(m);c['restrictions']['production_deployment']=True
        with self.assertRaises(ValueError):l.fit([row()],c,m,'parent')
