from copy import deepcopy
import unittest
from test_harmony_progression_context import make, path
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_progression_evidence import vector, compare, lowest


class EvidenceTests(unittest.TestCase):
    def test_oversegmentation_gain_is_not_winner(self):
        r, aid = make()
        c = compare(r, path(r, [(0,3,0)]), path(r, [(0,1,0),(1,2,2),(2,3,0)]), aid)
        self.assertEqual(c['note_time_delta_second_minus_first']['member'], q(1))
        self.assertEqual(c['boundary_count_delta'], 2)
        self.assertIsNone(c['preferred'])

    def test_same_members_preserve_observations(self):
        r, aid = make()
        c = compare(r, path(r, [(0,3,0)]), path(r, [(0,1,0),(1,2,0),(2,3,0)]), aid)
        self.assertEqual(c['first']['cells'], c['second']['cells'])
        self.assertTrue(all(v == q(0) for v in c['note_time_delta_second_minus_first'].values()))

    def test_bass_change_not_harmonic_change(self):
        r, aid = make()
        v = vector(r, path(r, [(0,1,0),(1,3,0)]), aid)
        self.assertTrue(v['boundaries'][0]['observed_lowest_changed'])
        self.assertFalse(v['boundaries'][0]['harmonic_change_confirmed'])
        self.assertTrue(v['boundaries'][0]['same_member_sets'])

    def test_silence_not_bass_change(self):
        r, aid = make([('C4',0,1),('E4',2,3)])
        v = vector(r, path(r, [(0,1,0),(1,3,0)]), aid)
        self.assertIsNone(v['boundaries'][0]['observed_lowest_changed'])
        self.assertEqual(v['cells'][1]['lowest']['status'], 'silence')

    def test_member_union_does_not_prove_arpeggio(self):
        r, aid = make([('C4',0,1),('E4',1,2),('G4',2,3)])
        s = vector(r, path(r, [(0,3,0)]), aid)['segments'][0]
        self.assertEqual(s['first_complete_union_time_in_evaluation'], q(2))
        self.assertFalse(s['arpeggiation_confirmed'])

    def test_blockers_not_erased(self):
        r, aid = make(); p = path(r, [(0,3,0)])
        r['edges'][p[0]['edge']]['readings'][0]['abstention_reasons'] = ['fixture_blocker']
        self.assertEqual(vector(r,p,aid)['segments'][0]['candidate_blockers'], ['fixture_blocker'])

    def test_projection_keeps_external_context(self):
        r, aid = make()
        v = vector(r,path(r,[(0,3,0)]),aid,{'start':q(1),'end':q(2)})
        self.assertEqual(len(v['cells']),1)
        self.assertEqual(v['accounting']['note_time']['conditional_nonmember'],q(1))
        self.assertEqual(v['segments'][0]['cell_time']['nonmember_only'],q(1))

    def test_duplicate_lowest_refs_preserved(self):
        r,_ = make(); s = deepcopy(r['events'][0]); s['sounding_event_id']='duplicate'
        self.assertEqual(len(lowest([s,r['events'][0]])['event_refs']),2)

    def test_unknown_pitch_cannot_choose_lowest(self):
        r,_ = make(); r['events'][0]['pitch']['midi_pitch']=None
        self.assertEqual(lowest(r['events'])['status'],'unknown_pitch')

    def test_does_not_mutate_input(self):
        r, aid = make(); saved=deepcopy(r)
        vector(r,path(r,[(0,3,0)]),aid)
        self.assertEqual(r,saved)


if __name__ == '__main__': unittest.main()
