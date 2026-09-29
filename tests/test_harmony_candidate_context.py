from copy import deepcopy
import unittest
from test_harmony_open_candidates import score,run,get
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_candidate_context import attach,bass_evidence,root_relation

def fixture():
    return score([('B-3',0,2,'root'),('D4',0,2,'lead'),('F4',0,2,'inner'),('A-4',0,2,'seventh'),
        ('E-3',2,4,'root'),('E-4',2,4,'lead'),('G4',2,4,'inner'),('G4',2,4,'seventh'),('D-5',2,4,'extra')])
def build(ir):return {'analysis_span':{'start':q(0),'end':q(4)},'records':[run(ir,0,2),run(ir,2,4)]}
def edge(result):return next(e for e in result['context_edges'] if e['source_label']=='Bb:dominant7' and e['target_label']=='Eb:dominant7')

class CandidateContextTests(unittest.TestCase):
    def test_target_seventh_allowed(self):
        ir=fixture();e=edge(attach(ir,build(ir)));tags={t for s in e['direct_voice_support'] for t in s['relations']}
        self.assertIn('conditional_dominant_family_leading_tone_up',tags);self.assertIn('conditional_seventh_down_step_to_member',tags);self.assertFalse(e['applied_function_confirmed'])
    def test_first_inversion(self):
        r=run(score([('D3',0,4,'bass'),('B-3',0,4,'1'),('F4',0,4,'2'),('A-4',0,4,'3')]))
        b=bass_evidence(r,get(r,10,'dominant7'));self.assertEqual(b['onset_factor_index'],1);self.assertTrue(b['uniform_factor']);self.assertFalse(b['inversion_confirmed'])
    def test_arpeggio_does_not_assert_uniform_inversion(self):
        r=run(score([('D-3',0,1,'bass'),('B-3',1,2,'bass'),('F-3',2,3,'bass'),('G3',3,4,'bass')]))
        b=bass_evidence(r,get(r,7,'diminished7'));self.assertEqual(b['onset_factor_index'],2);self.assertFalse(b['uniform_factor'])
    def test_external_bass_not_automatically_removed(self):
        r=run(score([('D3',0,4,'bass'),('C4',0,4,'a'),('E4',0,4,'b'),('G4',0,4,'c')]))
        self.assertIsNone(bass_evidence(r,get(r,0,'major'))['onset_factor_index'])
    def test_no_source_mutation_or_label_input(self):
        ir=fixture();p=build(ir);old=deepcopy(p);r=attach(ir,p);self.assertEqual(old,p);ir['annotations']=['V/V'];self.assertEqual(attach(ir,p),r)
    def test_polyphony_blocks_direct_not_candidate_relation(self):
        ir=fixture()
        for n in ir['note_events']:n['voice_id']='same'
        e=edge(attach(ir,build(ir)));self.assertEqual(e['direct_voice_support'],[]);self.assertFalse(e['lack_of_direct_support_is_counterevidence'])
    def test_wrong_direction_does_not_gain_resolution(self):
        ir=score([('B-3',0,2,'a'),('D4',0,2,'b'),('F4',0,2,'c'),('A-4',0,2,'d'),('E-3',2,4,'a'),('G4',2,4,'b'),('B-4',2,4,'c'),('B-4',2,4,'d')])
        r=attach(ir,build(ir));e=next(e for e in r['context_edges'] if e['source_label']=='Bb:dominant7' and e['target_label']=='Eb:major');self.assertEqual(e['direct_voice_support'],[])
    def test_missing_target_root_not_invented(self):
        ir=fixture();p=build(ir);c=get(p['records'][1],3,'dominant7');c['root_hypotheses']=[]
        self.assertIsNone(root_relation(get(p['records'][0],10,'dominant7'),c))
    def test_no_join_across_gap(self):
        ir=fixture();p=build(ir);p['records'][1]=run(ir,3,4);self.assertEqual(attach(ir,p)['context_edges'],[])
    def test_window_blocker_does_not_delete_candidates(self):
        ir=fixture();p=build(ir);p['records'][0]['abstention_reasons']=['grace_timing'];r=attach(ir,p);self.assertEqual(r['context_edges'],[]);self.assertEqual(len(r['records'][0]['candidates']),len(p['records'][0]['candidates']))
    def test_candidate_refs_all_exist(self):
        ir=fixture();r=attach(ir,build(ir));ids={c['candidate_id'] for w in r['records'] for c in w['candidates']}
        self.assertTrue(all(e['source_candidate_ref'] in ids and e['target_candidate_ref'] in ids for e in r['context_edges']))
    def test_repeat_exactly_at_join_blocks_relation(self):
        ir=fixture();ir['measures'][0]['actual_duration_quarter']=q(2);ir['measures'][0]['repeat_barline']={'location':'right','repeat_direction':'backward'}
        self.assertEqual(attach(ir,build(ir))['context_edges'],[])
    def test_meter_change_exactly_at_join(self):
        ir=fixture();m=deepcopy(ir['measures'][0]);ir['measures'][0]['actual_duration_quarter']=q(2);m['global_start_quarter']=q(2);m['actual_duration_quarter']=q(2);m['time_signature']['beat_type']=8;ir['measures'].append(m)
        self.assertEqual(attach(ir,build(ir))['context_edges'],[])
    def test_root_pitch_class_relation_needs_spelling(self):
        ir=score([('G-3',0,2,'a'),('B-3',0,2,'b'),('D-4',0,2,'c'),('B3',2,4,'a'),('D#4',2,4,'b'),('F#4',2,4,'c')]);p=build(ir)
        self.assertIsNone(root_relation(get(p['records'][0],6,'major'),get(p['records'][1],11,'major')))
