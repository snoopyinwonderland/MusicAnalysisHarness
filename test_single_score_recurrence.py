import unittest
from test_single_score_melody_review import note
from single_score_recurrence import align,discover,assess,long_fill_candidates

class Tests(unittest.TestCase):
    def test_octave_repetition(self):
        a=[note(i,p) for i,p in enumerate([60,62,64,65,67,64])]
        b=[note(i+8,p+12) for i,p in enumerate([60,62,64,65,67,64])]
        path,shift=align(a,b);self.assertEqual(len(path),6);self.assertEqual(shift,0)
    def test_extra_note_does_not_shift_later_correspondence(self):
        a=[note(i,p) for i,p in enumerate([60,62,64,65,67,64])]
        b=[note(i+8,p) for i,p in enumerate([60,62,64,65,67,64])]
        extra=note(9,48);from single_score_melody_review import q
        from fractions import Fraction
        extra['onset']=q(Fraction(19,2));b.insert(2,extra)
        self.assertEqual(len(align(a,b)[0]),6)
    def test_monotone_and_budget(self):
        self.assertFalse(discover([note(i,60) for i in range(30)])['pairs'])
        r=discover([note(i,[60,62,64][i%3]) for i in range(30)],0)
        self.assertEqual(r['status'],'partial')
    def test_repeated_low_material_is_protected(self):
        r=dict(id='x',start=1,endExclusive=2)
        d=dict(pairs=[dict(left=[0,3],right=[8,11],matches=[[0,8],[1,9],[2,10]])])
        self.assertEqual(assess([r],d)[0]['state'],'recurring-material-protect')
    def test_missing_evidence_is_not_negative(self):
        self.assertEqual(assess([dict(id='x',start=1,endExclusive=2)],dict(pairs=[]))[0]['state'],'insufficient-evidence')
    def test_budget_reaches_late_sections(self):
        r=discover([note(i,[60,62,64,65,67,64,62,60][i%8]) for i in range(80)],90)
        self.assertEqual(r['comparisons'],90)
        self.assertTrue(any(b['leftQuarter']>=2 and b['examined'] for b in r['coverageBuckets']))
        self.assertEqual(sum(b['examined']+b['remaining'] for b in r['coverageBuckets']),r['eligibleComparisons'])
    def test_long_run_is_only_a_hypothesis_and_tie_blocks_it(self):
        ns=[note(i,p) for i,p in enumerate([72,60,62,60,74,72,74])]
        for n in ns:n['sourceIds']=[n['id']];n['unresolvedTie']=False
        d=dict(pairs=[dict(matches=[[0,5],[4,6]])])
        before=repr(ns);r=long_fill_candidates(ns,d)
        self.assertEqual(len(r),1);self.assertFalse(r[0]['selected']);self.assertEqual(repr(ns),before)
        ns[2]['ties']=['start'];self.assertEqual(long_fill_candidates(ns,d)[0]['status'],'blocked')

if __name__=='__main__':unittest.main()
