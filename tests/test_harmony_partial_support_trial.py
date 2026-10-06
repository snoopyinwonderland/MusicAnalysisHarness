from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_partial_support_trial as s
from test_harmony_context_joint_decoder import toy,paths
from test_harmony_source_context_scoring import weights


class PartialSupportTrialTests(unittest.TestCase):
    def test_vector_keeps_partial_cost_separate_from_gradient(self):
        def receipt(value,known):
            return dict(previous35_cost=s.q(value),partial_support=dict(
                availability=dict.fromkeys(s.score.FEATURES,known),
                scored_available_feature_sums=dict.fromkeys(s.score.FEATURES,s.q(value))))
        result=s.vector({'contrast_id':'x'},receipt(F(1,3),True),receipt(F(1,7),False))
        self.assertTrue(all(s.f(v)==0 for v in result['delta'].values()))
        self.assertTrue(all(s.f(v)==F(4,21) for v in result['scored_partial_delta'].values()))

    def test_uncached_independent_cost_receipt_matches(self):
        graph,ev,_=toy(cap=1);sc=s.score.Scorer(graph,ev,weights())
        ids=next(ids for ids in paths(graph) if len(ids)==1)
        self.assertTrue(s.t.train.same_json(s.independent_receipt(sc,ids),sc.path_receipt(ids)))

