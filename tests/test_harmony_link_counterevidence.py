from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_harmony_reading_voice_context import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_delayed_links import observe
from musicanote_harness.harmony_link_counterevidence import assess

def run(ir):
    contexts=[{'start':q(0),'end':q(8)}];return assess(ir,observe(ir,contexts),contexts)
def find(rows,a,b):return next(r for r in rows['records'] if r['source_pitch']==a and r['target_pitch']==b)
def restart():return score([('C4',0,F(1,4),'v'),('D4',F(1,4),F(1,2),'v'),('E4',F(1,2),F(3,4),'v'),('B3',F(3,4),1,'v'),('C4',F(5,4),F(3,2),'v'),('D4',F(3,2),F(7,4),'v'),('E4',F(7,4),2,'v')])

class LinkCounterevidenceTests(unittest.TestCase):
    def test_simple_endpoint_is_not_confirmed(self):
        r=find(run(score([('B3',0,1,'v'),('C4',F(5,4),2,'v')])),'B3','C4')
        self.assertEqual(r['review_reasons'],[]);self.assertFalse(r['voice_connection_confirmed']);self.assertFalse(r['independent_resolution_vote_allowed'])
    def test_earlier_same_target_not_independent(self):
        ir=score([('B3',0,1,'v'),('C4',F(5,4),F(3,2),'v'),('D4',F(3,2),F(7,4),'v'),('C4',F(7,4),2,'v')])
        r=run(ir);later=[x for x in r['records'] if x['earlier_identical_target_refs']]
        self.assertEqual(len(later),1);self.assertEqual(later[0]['target_pitch'],'C4')
    def test_intervening_note_not_deleted(self):
        r=find(run(score([('B3',0,1,'v'),('G4',F(5,4),F(3,2),'v'),('C4',F(3,2),2,'v')])),'B3','C4')
        self.assertEqual(len(r['intervening_attack_refs']),1)
    def test_restart_pattern_is_alternative_only(self):
        r=find(run(restart()),'B3','C4')
        self.assertIn('recurrent_attack_pattern_allows_restart',r['review_reasons']);self.assertFalse(r['restart_confirmed'])
    def test_different_rhythm_does_not_match(self):
        ir=restart();ir['sounding_events'][-1]['span']['end']=q(F(9,4))
        self.assertFalse(find(run(ir),'B3','C4')['prior_matching_patterns'])
    def test_wrong_voice_cannot_supply_reference(self):
        ir=restart()
        for n in ir['note_events'][:3]:n['voice_id']='other'
        self.assertFalse(find(run(ir),'B3','C4')['prior_matching_patterns'])
    def test_crossing_meter_does_not_supply_reference(self):
        ir=restart();m=deepcopy(ir['measures'][0]);m['global_start_quarter']=q(1);m['time_signature']={'beats':3,'beat_type':4};ir['measures'].append(m)
        self.assertFalse(find(run(ir),'B3','C4')['prior_matching_patterns'])
    def test_polyphony_is_ambiguous(self):
        ir=score([('B3',0,1,'v'),('F4',0,1,'v'),('C4',F(5,4),2,'v')])
        self.assertIn('polyphonic_voice_identity_unresolved',find(run(ir),'B3','C4')['review_reasons'])
    def test_immutable_and_annotation_blind(self):
        ir=restart();old=deepcopy(ir);a=run(ir);self.assertEqual(ir,old)
        self.assertEqual(a,run({**ir,'annotations':['false'],'title':'false'}))
    def test_context_limit_prevents_reference(self):
        ir=restart();contexts=[{'start':q(F(3,4)),'end':q(8)}]
        self.assertFalse(find(assess(ir,observe(ir,contexts),contexts),'B3','C4')['prior_matching_patterns'])
    def test_repeat_barrier_prevents_pattern_reference(self):
        ir=restart();ir['measures'][0].update(actual_duration_quarter=q(F(3,4)),repeat_barline={'location':'right','repeat_direction':'backward'})
        self.assertFalse(find(run(ir),'B3','C4')['prior_matching_patterns'])
    def test_sustained_polyphony_prevents_monophonic_pattern_claim(self):
        ir=restart();extra=score([('G3',0,F(3,4),'v')]);n=extra['note_events'][0];n['note_id']='heldn'
        s=extra['sounding_events'][0];s.update(sounding_event_id='helds',source_note_ids=['heldn'],attack_note_id='heldn')
        ir['note_events'].append(n);ir['sounding_events'].append(s)
        self.assertFalse(find(run(ir),'B3','C4')['prior_matching_patterns'])
