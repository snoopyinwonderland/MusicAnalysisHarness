import copy
import unittest
from test_single_score_melody_review import note
from single_score_skip_paths import propose


class SkipTests(unittest.TestCase):
    def fixture(self):
        ns=[note(i,72+i%3) for i in range(8)]
        for n in ns: n['sourceIds']=[n['id']]
        ns[1]['beams']=[dict(number='1',value='begin')]
        ns[2]['beams']=[dict(number='1',value='end')]
        return ns,dict(pairs=[dict(matches=[[0,5],[3,6],[4,7]],left=[0,5],right=[5,8])])

    def test_complete_beam_makes_unselected_alternative(self):
        ns, d=self.fixture(); before=copy.deepcopy(ns)
        r=propose(ns,d)['proposals'][0]
        self.assertEqual(r['status'],'review-only')
        self.assertEqual(r['omittedIds'],['1','2'])
        self.assertFalse(r['selected']); self.assertEqual(ns,before)

    def test_partial_beam_blocks(self):
        ns,d=self.fixture(); ns[1]['beams'][0]['value']='continue'
        r=propose(ns,d)['proposals'][0]
        self.assertIsNone(r['alternativeEventIds'])

    def test_tie_blocks(self):
        ns,d=self.fixture(); ns[1]['ties']=['start']
        self.assertIn('tie-protected',propose(ns,d)['proposals'][0]['blockers'])

    def test_no_alignment_no_skip(self):
        ns,_=self.fixture()
        self.assertEqual(propose(ns,dict(pairs=[]))['proposals'],[])

    def test_retained_recurrence_protects(self):
        ns,d=self.fixture()
        d['pairs'].append(dict(matches=[[0,4],[1,5],[2,6],[3,7]],left=[0,4],right=[4,8]))
        self.assertIn('retained-in-other-recurrence',propose(ns,d)['proposals'][0]['blockers'])


if __name__=='__main__': unittest.main()
