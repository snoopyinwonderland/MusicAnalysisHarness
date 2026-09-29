from copy import deepcopy
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_change_gate import evaluate
from test_harmony_open_candidates import score

def run(ir,t=2):return evaluate(ir,{'start':q(0),'end':q(4)},q(t))
def fixture():return score([('C3',0,2,'a'),('E4',0,2,'b'),('G4',0,2,'c'),('G2',2,4,'a'),('D4',2,4,'b'),('B4',2,4,'c')])
def cg(r):return [p for p in r['change_proposals'] if p['source_label']=='C:major' and p['target_label']=='G:major']

class ChangeGateTests(unittest.TestCase):
    def test_full_change_passes(self):self.assertTrue(cg(run(fixture())))
    def test_held_harmony_passing_note_supports_hold(self):
        ir=score([('C3',0,4,'a'),('E3',0,4,'b'),('G3',0,4,'c'),('C4',0,1,'d'),('D4',1,2,'d'),('E4',2,4,'d')])
        r=run(ir);self.assertFalse(r['change_proposals']);self.assertTrue(any(p['label']=='C:major' for p in r['hold_proposals']))
    def test_arpeggio_does_not_require_change(self):
        r=run(score([('C4',0,1,'v'),('E4',1,2,'v'),('G4',2,3,'v'),('C5',3,4,'v')]))
        self.assertFalse(r['change_proposals']);self.assertIsNone(r['selected'])
    def test_rootless_does_not_pass(self):
        ir=fixture();ir['sounding_events']=ir['sounding_events'][1:]
        self.assertFalse(cg(run(ir)))
    def test_repeated_chord_no_change(self):
        r=run(score([('C3',0,2,'a'),('E4',0,2,'b'),('G4',0,2,'c'),('C3',2,4,'a'),('E4',2,4,'b'),('G4',2,4,'c')]))
        self.assertFalse(r['change_proposals'])
    def test_shared_bass_is_deferred(self):
        r=run(score([('C3',0,4,'a'),('E4',0,2,'b'),('G4',0,2,'c'),('D4',2,4,'b'),('B4',2,4,'c'),('G4',2,4,'d')]))
        self.assertFalse(cg(r));self.assertIn('bass_replacement_not_supported',r['failed_gate_counts'])
    def test_context_silence_blocks(self):
        ir=fixture();ir['sounding_events'][0]['span']['end']=q(1)
        for s in ir['sounding_events']:
            if s['span']['start']==q(0):s['span']['end']=q(1)
        self.assertFalse(run(ir)['change_proposals'])
    def test_meter_change_at_join_blocks(self):
        ir=fixture();m=deepcopy(ir['measures'][0]);m['global_start_quarter']=q(2);m['time_signature']['beat_type']=8
        ir['measures'].append(m);self.assertFalse(run(ir)['change_proposals'])
    def test_octave_doubling_not_two_motions(self):
        ir=score([('C3',0,2,'a'),('C4',0,2,'b'),('E4',0,4,'c'),('G4',0,4,'d'),('G2',2,4,'a'),('G3',2,4,'b'),('B4',2,4,'e'),('D5',2,4,'f')])
        self.assertFalse(cg(run(ir)))
    def test_no_mutation_or_annotations(self):
        ir=fixture();old=deepcopy(ir);r=run(ir);self.assertEqual(old,ir)
        ir['annotations']=['wrong'];self.assertEqual(r,run(ir));self.assertIsNone(r['selected'])
    def test_threshold_is_meter_relative(self):
        ir=fixture();small=deepcopy(ir)
        from musicanote_harness.harmony_joint import f
        for s in small['sounding_events']:s['span']={k:q(f(v)/4) for k,v in s['span'].items()}
        for m in small['measures']:
            m['global_start_quarter']=q(f(m['global_start_quarter'])/4);m['actual_duration_quarter']=q(f(m['actual_duration_quarter'])/4);m['time_signature']['beat_type']*=4
        result=evaluate(small,{'start':q(0),'end':q(1)},q('1/2'))
        self.assertTrue(cg(result))
    def test_invalid_boundary(self):
        with self.assertRaises(ValueError):run(fixture(),0)
