from copy import deepcopy
import unittest
from test_harmony_reading_voice_context import external_fixture,score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_reading_voice_context import compare
from musicanote_harness.harmony_voice_revision_audit import compatibility,link_changes,blocked_examples


class VoiceRevisionAuditTests(unittest.TestCase):
    def test_same_sound_different_voice_compatible(self):
        ir,c=external_fixture();new=deepcopy(ir)
        for n in new['note_events']:n['voice_id']='new_'+n['voice_id']
        self.assertTrue(compatibility(ir,new,c)['compatible'])
        changes=link_changes(compare(ir,c),compare(new,c))
        self.assertFalse(changes['new_pairs']);self.assertFalse(changes['lost_pairs'])

    def test_changed_sound_span_blocks_frozen_hypothesis(self):
        ir,c=external_fixture();new=deepcopy(ir);new['sounding_events'][0]['span']['end']=q(1)
        self.assertFalse(compatibility(ir,new,c)['compatible'])

    def test_changed_sound_membership_blocks_frozen_hypothesis(self):
        ir,c=external_fixture();new=deepcopy(ir);new['sounding_events'][0]['source_note_ids'].append('other')
        self.assertFalse(compatibility(ir,new,c)['compatible'])

    def test_missing_sound_blocks(self):
        ir,c=external_fixture();new=deepcopy(ir);new['sounding_events'].pop(0)
        self.assertFalse(compatibility(ir,new,c)['compatible'])

    def test_changed_external_sound_blocks_context_ablation(self):
        ir,c=external_fixture();new=deepcopy(ir);new['sounding_events'][-1]['span']['end']=q(7)
        self.assertTrue(compatibility(ir,new,c)['compatible'])
        self.assertFalse(compatibility(ir,new,c,{'start':q(0),'end':q(6)})['compatible'])

    def test_pair_diff_ignores_renamed_voice_ids(self):
        a={'voice_observations':{'links':[{'source_refs':['a','b'],'voice_id':'old'}],'abstentions':{}}}
        b=deepcopy(a);b['voice_observations']['links'][0]['voice_id']='new'
        self.assertEqual(link_changes(a,b)['same_pairs'],1)

    def test_polyphony_evidence_contains_source_locators(self):
        ir=score([('C4',0,1,'v'),('E4',0,1,'v'),('G4',1,2,'v')]);ir['source_references']=[]
        for i,n in enumerate(ir['note_events']):
            n['source_ref_id']='r'+str(i)
            ir['source_references'].append({'source_ref_id':n['source_ref_id'],'source_xpath':'/note['+str(i+1)+']','source_voice':'1'})
        observed={'voice_observations':{'event_statuses':[{'event_ref':'s0','status':'polyphonic_source_voice'}]}}
        old=deepcopy(ir);result=blocked_examples(ir,observed)
        self.assertEqual(ir,old);self.assertEqual(result[0]['overlapping_same_ir_voice'][0]['pitch'],'E4')
        self.assertEqual(result[0]['source_locators'],['/note[1]'])


if __name__=='__main__':unittest.main()
