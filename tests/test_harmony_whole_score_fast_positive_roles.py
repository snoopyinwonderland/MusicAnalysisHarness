"""Post-run positive-branch checks; no frozen inference file is modified."""
import unittest
from fractions import Fraction as F
from musicanote_harness import harmony_whole_score_units as original
from musicanote_harness.harmony_whole_score_fast import FastSearch
from test_harmony_whole_score_fast import prepare,C
from test_harmony_bounded_recovery import fixture


class PositiveRoleChecks(unittest.TestCase):
    def test_true_conditional_passing_credit_is_identical_and_positive(self):
        ir=fixture([('C3',0,4,'b'),('E3',0,4,'i'),('G3',0,4,'j'),
            ('C4',0,F(1,2),'lead'),('D4',F(1,2),1,'lead'),('E4',1,4,'lead')])
        p,ev,args=prepare(ir);slow=original.UnitSearch(p,ev,original.model_weights(),**args)
        fast=FastSearch(p,ev,original.model_weights(),**args)
        left=slow.index.features(F(),F(4),C)[0];right=fast.index.features(F(),F(4),C)[0]
        name='conditional_step_ornament_exposure'
        self.assertGreater(left[name],0);self.assertEqual(left[name],right[name])
        self.assertEqual(slow.run_cost(0,len(p.points)-1,C),fast.run_cost(0,len(p.points)-1,C))

    def test_prepared_late_third_credit_is_identical_and_positive(self):
        ir=fixture([('C3',0,4,'b'),('G3',1,4,'i'),('F4',0,3,'lead'),('E4',3,4,'lead')])
        p,ev,args=prepare(ir);slow=original.UnitSearch(p,ev,original.model_weights(),**args)
        fast=FastSearch(p,ev,original.model_weights(),**args)
        name='late_identifying_member_exposure'
        left=slow.index.features(F(1),F(4),C)[0];right=fast.index.features(F(1),F(4),C)[0]
        self.assertEqual(left[name],F(1,8));self.assertEqual(left[name],right[name])
        i=p.points.index(F(1));j=p.points.index(F(4))
        self.assertEqual(slow.run_cost(i,j,C),fast.run_cost(i,j,C))


if __name__=='__main__':unittest.main()
