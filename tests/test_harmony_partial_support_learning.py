from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_partial_support_learning as s


def row(key='a',old=-1,delta=(1,0,0,0),loss=1):
    return dict(contrast_id=key,split='train',work_family_id='toy',old_gap=s.q(F(old)),
        delta={k:s.q(F(v)) for k,v in zip(s.score.FEATURES,delta)},
        available=dict.fromkeys(s.score.FEATURES,True),loss=s.q(F(loss)))


class PartialSupportLearningTests(unittest.TestCase):
    def test_fixed_625_grid_and_effective_cost(self):
        result=s.fit([row()])
        self.assertEqual(result['configuration']['configurations'],625)
        self.assertEqual(s.f(result['weights'][s.score.FEATURES[0]]),2)
        self.assertLess(s.f(result['objective_after']),s.f(result['objective_before']))

    def test_actual_partial_costs_protect_known_old_margin(self):
        protected=row('b',old=F(1,10),delta=(0,0,0,0),loss=0)
        protected['available'][s.score.FEATURES[0]]=False
        protected['scored_partial_delta']={k:s.q(F(-1) if i==0 else F()) for i,k in enumerate(s.score.FEATURES)}
        result=s.fit([row(),protected])
        self.assertEqual(s.f(result['weights'][s.score.FEATURES[0]]),F(1,20))

    def test_unavailable_dimension_not_fitted(self):
        unknown=row('b');unknown['available']=dict.fromkeys(s.score.FEATURES,False)
        result=s.fit([row(),unknown])
        self.assertEqual(result['unknown_rows_excluded'],1);self.assertEqual(result['unknown_dimensions_excluded'],4)

    def test_no_gain_zero_and_dev_or_duplicates_rejected(self):
        result=s.fit([row(delta=(0,0,0,0))])
        self.assertTrue(all(s.f(v)==0 for v in result['weights'].values()))
        bad=row();bad['split']='dev'
        with self.assertRaises(ValueError):s.fit([bad])
        with self.assertRaises(ValueError):s.fit([row(),row()])

