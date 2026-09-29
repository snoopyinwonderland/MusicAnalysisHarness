from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score as base_score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_open_candidates import window,observe

def score(specs):
    ir=base_score(specs)
    for m in ir['measures']:m['time_signature']['beats']=4
    return ir
def run(ir,a=0,b=4):return window(ir,{'start':q(a),'end':q(b)})
def get(result,root,quality):return next(c for c in result['candidates'] if c['root']==root and c['label'].endswith(':'+quality))

class OpenCandidatesTests(unittest.TestCase):
    def fixture(self):return score([('C3',0,4,'bass'),('E3',0,4,'inner'),('G3',0,4,'inner2'),('C4',0,1,'lead'),('D4',1,2,'lead'),('E4',2,4,'lead')])
    def test_extra_pitch_does_not_remove_triad(self):
        r=run(self.fixture());c=get(r,0,'major');self.assertEqual(len(c['residual_event_refs']),1);self.assertTrue(c['template_fully_observed'])
        self.assertEqual(r['conditional_figures']['summary']['conditional_ornament_triples'],1)
    def test_real_seventh_and_triad_both_retained(self):
        r=run(score([('C3',0,4,'a'),('E3',0,4,'b'),('G3',0,4,'c'),('B3',0,4,'d')]))
        self.assertFalse(get(r,0,'major7')['residual_event_refs']);self.assertTrue(get(r,0,'major')['residual_event_refs']);self.assertIsNone(r['selected'])
    def test_missing_fifth_allowed(self):
        r=run(score([('C4',0,4,'a'),('E4',0,4,'b')]))
        self.assertEqual(get(r,0,'major')['missing_member_pcs'],[7])
    def test_root_absence_is_not_invented_spelling(self):
        r=run(score([('E4',0,4,'a'),('G4',0,4,'b')]))
        self.assertEqual(get(r,0,'major')['root_hypotheses'],[])
    def test_held_note_not_new_attack(self):
        r=run(score([('B-4',0,3,'a'),('D4',1,4,'b'),('F4',1,4,'c')]),1,3)
        c=get(r,10,'major');self.assertTrue(c['template_fully_observed']);self.assertEqual(len(r['cells'][0]['continued_refs']),1)
    def test_rest_is_preserved_and_blocks_figures(self):
        r=run(score([('C4',0,1,'a'),('E4',2,4,'a')]))
        self.assertTrue(any(c['silence'] for c in r['cells']));self.assertIn('silence_inside_window',r['abstention_reasons'])
    def test_no_label_input_or_mutation(self):
        ir=self.fixture();old=deepcopy(ir);r=run(ir);self.assertEqual(ir,old);ir['annotations']=['V7/V'];self.assertEqual(run(ir),r)
    def test_enharmonic_not_collapsed(self):
        r=run(score([('G3',0,4,'a'),('B-3',0,4,'b'),('D-4',0,4,'c'),('F-4',0,4,'d')]))
        self.assertTrue(get(r,7,'diminished7')['root_hypotheses']);self.assertFalse(get(r,4,'diminished7')['root_hypotheses'])
    def test_no_boundary_extension(self):
        r=run(self.fixture(),1,3);self.assertEqual(r['cells'][0]['span']['start'],q(1));self.assertEqual(r['cells'][-1]['span']['end'],q(3))
    def test_single_pc_cannot_propose_chord(self):
        self.assertEqual(run(score([('C4',0,4,'a')]))['candidates'],[])
    def test_transposition(self):
        ir=self.fixture();shifted=score([('D3',0,4,'bass'),('F#3',0,4,'inner'),('A3',0,4,'inner2'),('D4',0,1,'lead'),('E4',1,2,'lead'),('F#4',2,4,'lead')])
        before={(c['root'],c['label'].split(':')[1]) for c in run(ir)['candidates']}
        after={(c['root'],c['label'].split(':')[1]) for c in run(shifted)['candidates']}
        self.assertEqual({((r+2)%12,k) for r,k in before},after)
    def test_proposals_reproducible(self):
        ir=self.fixture();span={'start':q(0),'end':q(4)};self.assertEqual(observe(ir,span),observe(ir,span))
    def test_scaled_meter_preserves_candidates_and_figures(self):
        from musicanote_harness.harmony_joint import f
        ir=self.fixture();small=deepcopy(ir)
        for s in small['sounding_events']:
            s['span']={k:q(f(v)/2) for k,v in s['span'].items()}
        for m in small['measures']:
            m['global_start_quarter']=q(f(m['global_start_quarter'])/2);m['actual_duration_quarter']=q(f(m['actual_duration_quarter'])/2);m['time_signature']['beat_type']*=2
        a=run(ir);b=run(small,0,2)
        self.assertEqual([c['label'] for c in a['candidates']],[c['label'] for c in b['candidates']])
        self.assertEqual(a['conditional_figures']['summary'],b['conditional_figures']['summary'])
    def test_unknown_meter_blocks_role_not_candidates(self):
        ir=self.fixture();del ir['measures'][0]['time_signature']['beats'];r=run(ir)
        self.assertTrue(r['candidates']);self.assertIn('meter_missing_or_changed',r['abstention_reasons']);self.assertEqual(r['conditional_figures']['summary']['conditional_ornament_triples'],0)
    def test_double_neighbor_not_mislabeled_single_passing(self):
        r=run(score([('A-3',0,4,'bass'),('C4',0,4,'inner'),('E-4',0,4,'inner2'),('A-4',0,1,'lead'),('G4',1,2,'lead'),('B-4',2,3,'lead'),('A-4',3,4,'lead')]))
        self.assertTrue(get(r,8,'major')['residual_event_refs']);self.assertEqual(r['conditional_figures']['summary']['conditional_ornament_triples'],0)
