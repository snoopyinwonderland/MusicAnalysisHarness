from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_delayed_links import observe
from musicanote_harness.harmony_delayed_trial import verify,role_comparisons
from test_harmony_reading_voice_context import chord

def run(ir, end=8): return observe(ir,[{'start':q(0),'end':q(end)}])
def basic(): return score([('B3',0,1,'v'),('F4',0,1,'v'),('C4',2,3,'v'),('E4',2,3,'v')])

class DelayedLinksTests(unittest.TestCase):
    def test_gap_is_hypothesis_not_resolution(self):
        g=run(basic())['groups'][0]
        self.assertEqual(len(g['assignments']),7);self.assertEqual(g['first_attack_gap_beats'],q(1))
        self.assertFalse(g['eligible_as_direct_resolution']);self.assertIsNone(g['selected_assignment'])
    def test_direct_attack_not_duplicated(self):
        ir=score([('B3',0,1,'v'),('F4',0,1,'v'),('C4',1,2,'v')])
        self.assertFalse(run(ir)['groups'])
    def test_too_long_gap_abstains(self):
        ir=score([('B3',0,1,'v'),('C4',4,5,'v')])
        self.assertFalse(run(ir)['groups'])
    def test_two_beats_is_weaker(self):
        g=run(score([('B3',0,1,'v'),('C4',3,4,'v')]))['groups'][0]
        self.assertIn('weak',g['evidence_grade'])
    def test_distributed_attacks_retained(self):
        ir=score([('B3',0,1,'v'),('F4',0,1,'v'),('G4',2,F(5,2),'v'),('E4',F(5,2),3,'v')])
        g=run(ir)['groups'][0];later=[e for e in g['edges'] if e['target_pitch']['spelling']=='E4']
        self.assertTrue(all(len(e['intervening_attack_refs'])==1 for e in later))
    def test_does_not_skip_first_attack(self):
        ir=score([('B3',0,1,'v'),('G4',2,3,'v'),('C4',3,4,'v')])
        g=run(ir)['groups'][0]
        self.assertEqual([e['target_pitch']['spelling'] for e in g['edges']],['G4'])
    def test_no_cross_voice(self):
        ir=score([('B3',0,1,'v'),('C4',2,3,'other')]);self.assertFalse(run(ir)['groups'])
    def test_explicit_rest_not_erased(self):
        ir=basic();ir['rest_events']=[{'rest_id':'rest','part_id':'part1','voice_id':'v','global_onset_quarter':q(1),'notated_duration_quarter':q(1)}]
        self.assertEqual(run(ir)['groups'][0]['rest_refs'],['rest'])
    def test_endpoint_cap(self):
        ir=score([(p,0,1,'v') for p in ['C3','D3','E3','F3','G3']]+[('C4',2,3,'v')])
        self.assertIn('endpoint_limit_no_silent_pruning',[a['reason'] for a in run(ir)['abstentions']])
    def test_contexts_cannot_be_stitched(self):
        ir=basic();r=observe(ir,[{'start':q(0),'end':q(2)},{'start':q(2),'end':q(4)}])
        self.assertFalse(r['groups'])
    def test_meter_unknown_abstains(self):
        ir=basic();ir['measures']=[];self.assertFalse(run(ir)['groups'])
    def test_duplicate_context_and_input_immutability(self):
        ir=basic();old=deepcopy(ir);span={'start':q(0),'end':q(8)}
        self.assertEqual(observe(ir,[span]),observe(ir,[span,span]));self.assertEqual(ir,old)
        self.assertEqual(run(ir),run({**ir,'annotations':['wrong'],'title':'wrong'}))
    def test_duration_scale_and_meter_denominator(self):
        ir=basic();expected=run(ir)['groups'][0]['first_attack_gap_beats']
        for s in ir['sounding_events']:
            for k in ('start','end'):s['span'][k]=q(F(s['span'][k]['numerator'],s['span'][k]['denominator'])/2)
        ir['measures'][0]['time_signature']['beat_type']=8
        self.assertEqual(run(ir)['groups'][0]['first_attack_gap_beats'],expected)
    def test_invalid_context(self):
        with self.assertRaises(ValueError):observe(basic(),[{'start':q(1),'end':q(0)}])
    def test_null_repeat_metadata(self):
        ir=basic();ir['measures'][0]['repeat_barline']=None
        self.assertTrue(run(ir)['groups'])
    def test_repeat_barrier(self):
        ir=basic();ir['measures'][0].update(actual_duration_quarter=q(2),repeat_barline={'location':'right','repeat_direction':'backward'})
        self.assertFalse(run(ir)['groups'])
    def test_meter_change_barrier(self):
        ir=basic();m=deepcopy(ir['measures'][0]);m['global_start_quarter']=q(F(3,2));m['time_signature']={'beats':3,'beat_type':8};ir['measures'].append(m)
        self.assertFalse(run(ir)['groups'])
    def test_independent_verifier(self):
        ir=basic();self.assertEqual(verify(ir,run(ir))['assignments_verified'],7)
        o=run(ir);o['groups'][0]['assignments'][-1]=deepcopy(o['groups'][0]['assignments'][0])
        with self.assertRaises(AssertionError):verify(ir,o)
    def test_actual_arrival_selects_later_segment(self):
        ir=basic();o=run(ir)
        c={'merged_seventh':[],'split_triads':[{'local_cost':0.2,'segments':[
            {'span':{'start':q(0),'end':q(F(3,2))},'candidate':chord(7,'dominant7')},
            {'span':{'start':q(F(3,2)),'end':q(4)},'candidate':chord(0,'major')}]}]}
        r=role_comparisons(c,{'external_shape_candidates':[]},o)
        self.assertTrue(r);self.assertTrue(all(x['target_chord_context']['candidate']['root']==0 for x in r))
        self.assertTrue(any(x['endpoint_compatible_relations'] for x in r))
        self.assertTrue(all(not x['function_confirmed'] and not x['used_for_ranking'] for x in r))
    def test_held_sound_not_reassigned(self):
        ir=score([('B3',0,1,'v'),('G3',0,4,'v'),('C4',2,3,'v')]);g=run(ir)['groups'][0]
        self.assertEqual(len(g['held_refs']),1)
        self.assertFalse(set(g['held_refs']) & set(g['source_refs']+g['target_refs']))
    def test_context_truncation_explicit(self):
        g=run(basic(),F(5,2))['groups'][0]
        self.assertTrue(g['window_truncated_by_context']);self.assertEqual(g['target_window_end'],q(F(5,2)))
