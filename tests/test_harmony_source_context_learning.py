from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_source_context_learning as s


def row(key='a', old=-1, delta=(1,0,0), loss=1):
    return dict(contrast_id=key, split='train', work_family_id='toy', old_gap=s.q(F(old)),
        delta={k:s.q(F(v)) for k,v in zip(s.score.FEATURES,delta)},
        available=dict.fromkeys(s.score.FEATURES,True), loss=s.q(F(loss)))


class SourceContextLearningTests(unittest.TestCase):
    def test_fixed_grid_chooses_effective_new_evidence(self):
        r=s.fit([row()]); self.assertEqual(s.f(r['weights'][s.score.FEATURES[0]]), 2)
        self.assertLess(s.f(r['objective_after']),s.f(r['objective_before']))

    def test_positive_old_margin_is_protected(self):
        r=s.fit([row(),row('b',old=1,delta=(-2,0,0),loss=0)])
        self.assertLessEqual(s.f(r['weights'][s.score.FEATURES[0]]),F(1,4))

    def test_unknown_row_not_fitted(self):
        unknown=row('b'); unknown['available'][s.score.FEATURES[0]]=False
        r=s.fit([row(),unknown]); self.assertEqual(r['unknown_dimensions_excluded'],1)

    def test_no_effect_prefers_zero_and_dev_rejected(self):
        r=s.fit([row(delta=(0,0,0))]); self.assertTrue(all(s.f(v)==0 for v in r['weights'].values()))
        bad=row(); bad['split']='dev'
        with self.assertRaises(ValueError): s.fit([bad])
