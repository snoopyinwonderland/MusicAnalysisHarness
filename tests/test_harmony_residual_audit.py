from copy import deepcopy
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_open_candidates import window
from musicanote_harness.harmony_residual_audit import audit_pair
from test_harmony_open_candidates import score,get


def analyze(ir, a=(0,'major'),b=(7,'major'),t=2):
    left=window(ir,{'start':q(0),'end':q(t)});right=window(ir,{'start':q(t),'end':q(4)})
    return audit_pair(ir,left,right,get(left,*a),get(right,*b))
def anticipation():return score([('C3',0,2,'a'),('E3',0,2,'b'),('G3',0,2,'c'),('C4',0,1,'d'),('D4',1,2,'d'),('D4',2,4,'d'),('G2',2,4,'a'),('B3',2,4,'b')])
def roles(r):return [e['kind'] for side in r['sides'] for note in side['residuals'] for e in note['conditional_nct_explanations']]


class ResidualAuditTests(unittest.TestCase):
    def test_anticipation_conditional(self):self.assertIn('anticipation_reattack_compatible',roles(analyze(anticipation())))
    def test_passing_stays_in_residual_list(self):
        ir=score([('C3',0,4,'a'),('E3',0,4,'b'),('G3',0,4,'c'),('C4',0,0.5,'d'),('D4',0.5,1,'d'),('E4',1,2,'d'),('E4',2,4,'d')])
        r=analyze(ir,b=(0,'major'));self.assertEqual(len(r['sides'][0]['residuals']),1)
        self.assertTrue(r['sides'][0]['residuals'][0]['conditional_nct_explanations'])
    def test_pitch_change_not_anticipation(self):
        ir=anticipation();s=next(s for s in ir['sounding_events'] if s['pitch']['spelling']=='D4' and s['span']['start']==q(2))
        s['pitch']=deepcopy(next(s['pitch'] for s in ir['sounding_events'] if s['pitch']['spelling']=='G3'))
        self.assertNotIn('anticipation_reattack_compatible',roles(analyze(ir)))
    def test_rest_not_skipped(self):
        ir=anticipation();s=next(s for s in ir['sounding_events'] if s['pitch']['spelling']=='D4' and s['span']['start']==q(1));s['span']['end']=q('3/2')
        self.assertNotIn('anticipation_reattack_compatible',roles(analyze(ir)))
    def test_suspension_requires_real_held_sound(self):
        ir=score([('C3',0,2,'a'),('E3',0,2,'b'),('G3',0,2,'c'),('C4',0,3,'d'),('B3',3,4,'d'),('G2',2,4,'a'),('B2',2,4,'b'),('D3',2,4,'c')])
        self.assertIn('prepared_suspension_geometry',roles(analyze(ir)))
    def test_reattack_is_not_suspension(self):
        ir=score([('C3',0,2,'a'),('E3',0,2,'b'),('G3',0,2,'c'),('C4',0,2,'d'),('C4',2,3,'d'),('B3',3,4,'d'),('G2',2,4,'a'),('B2',2,4,'b'),('D3',2,4,'c')])
        self.assertNotIn('prepared_suspension_geometry',roles(analyze(ir)))
    def test_polyphonic_lane_abstains(self):
        ir=anticipation();extra=score([('E4',1,2,'d')])
        for s in extra['sounding_events']:s['sounding_event_id']='extra';s['source_note_ids']=['extra_n']
        for n in extra['note_events']:n['note_id']='extra_n'
        ir['sounding_events']+=extra['sounding_events'];ir['note_events']+=extra['note_events']
        self.assertNotIn('anticipation_reattack_compatible',roles(analyze(ir)))
    def test_local_membership_not_selection(self):
        r=analyze(anticipation());n=r['sides'][0]['residuals'][0]
        self.assertTrue(n['finer_cell_alternatives']);self.assertIsNone(r['selected']);self.assertFalse(r['used_for_ranking'])
    def test_immutable_and_label_independent(self):
        ir=anticipation();old=deepcopy(ir);r=analyze(ir);self.assertEqual(old,ir)
        ir['annotations']=['V7'];self.assertEqual(r,analyze(ir))
    def test_nonadjacent_rejected(self):
        ir=anticipation();left=window(ir,{'start':q(0),'end':q(1)});right=window(ir,{'start':q(2),'end':q(4)})
        with self.assertRaises(ValueError):audit_pair(ir,left,right,get(left,0,'major'),get(right,7,'major'))
