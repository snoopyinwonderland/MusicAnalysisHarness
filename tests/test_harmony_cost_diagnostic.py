import unittest
from fractions import Fraction
from test_harmony_joint import fixture
from musicanote_harness.harmony_cost_diagnostic import audit_partition, compare, transition


class DiagnosticTests(unittest.TestCase):
    def test_accounting_and_stable_chord(self):
        ir=fixture([(48,0,4,'b'),(52,0,4,'i'),(55,0,4,'s')])
        r=compare(ir,[0,2,4])
        for name in ('continue','split'):
            self.assertAlmostEqual(sum(r[name]['totals'].values()),r[name]['total_cost'])
        self.assertAlmostEqual(r['split_minus_continue'],.15)

    def test_transition_matches_engine(self):
        a={'label':'G:dominant7','root':7};b={'label':'C:major','root':0}
        self.assertEqual(transition(a,b),(.04,-.06))
        self.assertEqual(transition(b,b),(0,0))

    def test_full_candidates_not_worse(self):
        ir=fixture([(p,a,b,str(i)) for a,b,ps in [(0,1,[48,52,55]),(1,2,[55,59,62,65])] for i,p in enumerate(ps)])
        limited=audit_partition(ir,[0,1,2])
        full=audit_partition(ir,[0,1,2],limit=None)
        self.assertLessEqual(full['total_cost'],limited['total_cost']+1e-10)

    def test_labels_ignored_and_invalid_points(self):
        ir=fixture([(60,0,2,'a'),(64,0,2,'b'),(67,0,2,'c')])
        self.assertEqual(compare(ir,[0,1,2]),compare({**ir,'annotations':['V']},[0,1,2]))
        with self.assertRaises(ValueError):audit_partition(ir,[0,0,2])

    def test_fraction_points(self):
        r=audit_partition(fixture([(60,0,2,'a'),(64,0,2,'b')]),[0,Fraction(1,3),2])
        self.assertEqual(r['points'][1],{'numerator':1,'denominator':3})
