from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score,chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_path_explanation import explain
from musicanote_harness.harmony_conditional_ornaments import assess


def fixture(pitches=('C4','D4','E4'), change=False):
    ir=score([(p,1+F(i,4),1+F(i+1,4),'lead') for i,p in enumerate(pitches)]+[('C3',0,4,'bass'),('E3',0,4,'inner1'),('G3',0,4,'inner2')])
    def seg(a,b,c):return {'span':{'start':q(a),'end':q(b)},'candidate':c}
    c=chord(0,'major');d=chord(2,'minor') if change else c
    candidate={'evidence_id':'control','span':{'start':q(1),'end':q(3)},'boundary':q(F(3,2)),'beat_unit_quarter':q(1),
        'merged_seventh':[{'segments':[seg(1,3,c)]}], 'split_triads':[{'segments':[seg(1,F(3,2),c),seg(F(3,2),3,d)]}]}
    return ir,candidate,{'start':q(0),'end':q(4)}


class ConditionalOrnamentTests(unittest.TestCase):
    def result(self,args):return assess(args[0],explain(*args))
    def test_passing_not_confirmed_nct(self):
        r=self.result(fixture());self.assertEqual(r['summary']['conditional_ornament_triples'],1)
        p=r['records'][0]['path_explanations'][0];self.assertEqual(p['conditional_role'],'passing');self.assertFalse(p['confirmed_nct']);self.assertFalse(p['remove_note'])
    def test_neighbor(self):
        r=self.result(fixture(('C4','D4','C4')));self.assertEqual(r['records'][0]['geometry'],'neighbor_geometry')
    def test_chromatic_passing(self):
        r=self.result(fixture(('E4','F4','F#4')));self.assertEqual(r['records'][0]['geometry'],'chromatic_passing_geometry')
        self.assertEqual(r['summary']['conditional_ornament_triples'],0)
    def test_gap_never_skipped(self):
        args=fixture();args[0]['sounding_events'][0]['span']['end']=q(F(9,8))
        self.assertEqual(self.result(args)['records'],[])
    def test_polyphonic_lane_abstains(self):
        args=fixture();args[0]['note_events'][3]['voice_id']=args[0]['note_events'][0]['voice_id']
        self.assertEqual(self.result(args)['records'],[])
    def test_chord_change_blocks_ornament_under_that_path(self):
        r=self.result(fixture(change=True));p=r['records'][0]['path_explanations']
        self.assertEqual(p[0]['status'],'conditional_ornament_compatible');self.assertEqual(p[1]['status'],'crosses_candidate_chord_change')
    def test_endpoints_must_be_members(self):
        r=self.result(fixture(('D4','E4','F4')));self.assertEqual(r['summary']['conditional_ornament_triples'],0)
    def test_grace_blocks_claim(self):
        args=fixture();args[0]['note_events'].append({'note_id':'gr','global_onset_quarter':q(F(5,4)),'grace':{'is_grace':True}})
        self.assertEqual(self.result(args)['summary']['conditional_ornament_triples'],0)
    def test_original_inputs_and_annotations(self):
        args=fixture();old=deepcopy(args);r=self.result(args);self.assertEqual(args,old)
        args[0]['annotations']=['ii'];self.assertEqual(self.result(args),r)
    def test_ornament_under_one_path_member_under_another(self):
        args=fixture(('C4','B3','C4'))
        for s in args[1]['split_triads'][0]['segments']:s['candidate']=chord(0,'major7')
        r=self.result(args);self.assertTrue(r['records'][0]['competing_member_explanation'])
        self.assertIsNone(r['records'][0]['selected'])
    def test_different_part_does_not_create_line(self):
        args=fixture();args[0]['note_events'][1]['part_id']='other'
        self.assertEqual(self.result(args)['records'],[])
