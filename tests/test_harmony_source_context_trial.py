from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_source_context_trial as s


class SourceContextTrialTests(unittest.TestCase):
    def receipt(self,value,known=True):
        return dict(previous35_cost=s.q(value),source_context=dict(
            availability=dict.fromkeys(s.score.FEATURES,known),
            scored_available_feature_sums=dict.fromkeys(s.score.FEATURES,s.q(value))))

    def test_known_and_unknown_learning_vectors_keep_score_partials_separate(self):
        a=self.receipt(F(1));b=self.receipt(F(0),False)
        r=s.vector(dict(contrast_id='toy'),a,b)
        self.assertEqual(s.f(r['old_gap']),1)
        self.assertTrue(all(s.f(v)==0 for v in r['delta'].values()))
        self.assertTrue(all(s.f(v)==1 for v in r['scored_partial_delta'].values()))
        self.assertFalse(r['source_labels_for_features'])

    def test_available_vector_is_exact_negative_minus_target(self):
        r=s.vector({},self.receipt(F(1,3)),self.receipt(F(1,7)))
        self.assertTrue(all(s.f(v)==F(4,21) for v in r['delta'].values()))
