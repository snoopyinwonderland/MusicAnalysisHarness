from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_partial_support_scoring as s
from musicanote_harness import harmony_score_balance_ledger as ledger
from test_harmony_context_joint_decoder import toy,paths
from test_harmony_functional_scoring import C,G7,F64
from test_harmony_source_context_scoring import weights


class PartialSupportScoringTests(unittest.TestCase):
    def test_nonzero_exact_search_matches_exhaustive_paths(self):
        graph,ev,_=toy(cap=3,signatures=(C,G7,F64))
        for extra in (s.ZERO,{k:F(1,4) if i==0 else F(-1,4) for i,k in enumerate(s.FEATURES)}):
            sc=s.Scorer(graph,ev,weights(),extra)
            expected=min((sc.score_path(ids),ids) for ids in paths(graph))
            result=sc.decode(force_delayed=True)['selected']
            self.assertEqual((s.f(result['score_cost']),ledger.old.fresh.path_ids(result)),expected)

    def test_zero_cost_and_old_module_globals_unchanged(self):
        graph,ev,_=toy(cap=3);sc=s.Scorer(graph,ev,weights())
        old=s.parent.Scorer(graph,ev,weights());before=s.joint.Scorer._delayed.__globals__['old_score']
        a,b=sc.decode()['selected'],old.decode()['selected']
        self.assertEqual(a['score_cost'],b['score_cost'])
        self.assertEqual(ledger.old.fresh.path_ids(a),ledger.old.fresh.path_ids(b))
        self.assertIs(s.joint.Scorer._delayed.__globals__['old_score'],before)

    def test_split_union_same_feature_and_cost(self):
        graph,ev,_=toy(cap=4,signatures=(C,));sc=s.Scorer(graph,ev,weights())
        by={(e.start,e.end):e.group_id for e in graph.edges}
        a=sc.path_receipt((by[F(),F(4)],));b=sc.path_receipt((by[F(),F(2)],by[F(2),F(4)]))
        self.assertEqual(a['partial_support'],b['partial_support']);self.assertEqual(a['cost'],b['cost'])

    def test_unknown_role_not_whole_path_zero(self):
        graph,ev,_=toy(cap=1,signatures=(F64,));sc=s.Scorer(graph,ev,weights())
        ids=next(ids for ids in paths(graph) if len(ids)==1)
        r=sc.path_receipt(ids)['partial_support']
        self.assertIsNone(r['features'][s.FEATURES[0]])
        self.assertFalse(r['availability'][s.FEATURES[0]])

    def test_weight_sign_and_operation_guard(self):
        with self.assertRaises(ValueError):s.coefficients(dict.fromkeys(s.FEATURES,F(1)))
        graph,ev,_=toy(cap=3);sc=s.Scorer(graph,ev,weights(),{k:F(1) if i==0 else F() for i,k in enumerate(s.FEATURES)})
        result=sc.decode(transition_budget=1)
        self.assertIsNone(result['selected']);self.assertEqual(result['status'],'transition_budget_abstention')

