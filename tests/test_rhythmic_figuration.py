import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.rhythmic_figuration import observe, condition_on_members
from musicanote_harness.rhythmic_figuration_audit import build
from musicanote_harness.cadential_six_four_audit import digest
from musicanote_harness.harmony_curriculum import concepts

C = [['C',0],['E',0],['G',0]]
G7 = [['G',0],['B',0],['D',0],['F',0]]
F = [['F',0],['A',0],['C',0]]


def fixture(rows=None):
    rows = rows or [('F',0,4,0,2,'v'),('E',0,4,2,3,'v')]
    ir = {'note_events': [], 'sounding_events': []}
    for i,(step,alter,octave,start,end,voice) in enumerate(rows):
        nid, sid = f'n{i}', f's{i}'
        ir['note_events'].append({'note_id': nid, 'part_id': 'p', 'voice_id': voice, 'display_staff_id':'staff1'})
        ir['sounding_events'].append({'sounding_event_id': sid, 'attack_note_id': nid, 'source_note_ids':[nid],
            'pitch': {'step':step,'alter':q(alter),'octave':octave,
                      'midi_pitch':12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter},
            'span': {'start':q(start),'end':q(end)}})
    return ir


def run(ir): return observe(ir, {'start':q(0),'end':q(1)}, {'start':q(1),'end':q(4)})
def conditional(ir, left=F, right=C): return condition_on_members(run(ir), left, right)['records'][0]


class RhythmicTest(unittest.TestCase):
    def test_tied_sustain_full_event_and_source_refs(self):
        ir=fixture(); n=copy.deepcopy(ir['note_events'][0]); n['note_id']='tie-end'
        ir['note_events'].append(n);ir['sounding_events'][0]['source_note_ids'].append('tie-end')
        r=run(ir)['retentions'][0]
        self.assertEqual(r['boundary_mode'],'literal_sustain_across_boundary')
        self.assertEqual(r['preparation_event']['span'],{'start':q(0),'end':q(2)})
        self.assertEqual(r['boundary_event']['source_note_ids'],['n0','tie-end'])
        self.assertEqual(r['motion']['semitones'],-1)

    def test_seventh_can_prepare_delay_without_consonance_claim(self):
        r=conditional(fixture(),G7,C)
        self.assertTrue(r['member_before']);self.assertFalse(r['member_after'])
        self.assertEqual(r['compatibility_tags'],['delayed_step_arrival_compatible'])
        self.assertIsNone(r['nct_verdict'])

    def test_nonmember_preparation_not_hard_rejected(self):
        r=conditional(fixture(),C,C)
        self.assertFalse(r['member_before'])
        self.assertIn('delayed_step_arrival_compatible',r['compatibility_tags'])

    def test_upward_release_preserved(self):
        ir=fixture([('B',0,3,0,2,'v'),('C',0,4,2,3,'v')])
        self.assertEqual(run(ir)['retentions'][0]['motion']['generic'],2)
        self.assertIn('delayed_step_arrival_compatible',conditional(ir,G7,C)['compatibility_tags'])

    def test_anticipatory_membership_separate_from_timing(self):
        r=conditional(fixture(),C,F)
        self.assertEqual(r['compatibility_tags'],['early_arrival_compatible'])

    def test_common_tone_not_forced_suspension_or_pedal(self):
        ir=fixture([('C',0,4,0,5,'v')]);r=conditional(ir,C,F)
        self.assertEqual(r['compatibility_tags'],['common_member_retention'])
        self.assertIsNone(run(ir)['pedal_function'])

    def test_restrike_not_synthetic_tie(self):
        ir=fixture([('F',0,4,0,1,'v'),('F',0,4,1,2,'v'),('E',0,4,2,3,'v')])
        r=run(ir)['retentions'][0]
        self.assertEqual(r['boundary_mode'],'same_pitch_restrike_at_boundary')
        self.assertNotEqual(r['preparation_event']['event_id'],r['boundary_event']['event_id'])

    def test_repeated_delay_keeps_each_attack(self):
        ir=fixture([('F',0,4,0,2,'v'),('F',0,4,2,3,'v'),('E',0,4,3,4,'v')])
        r=run(ir)['retentions'][0]
        self.assertEqual(len(r['retained_attack_chain']),2)
        self.assertEqual(r['departure']['event_id'],'s2')

    def test_half_open_end_is_not_retention(self):
        ir=fixture([('F',0,4,0,1,'v'),('E',0,4,1,3,'v')])
        self.assertEqual(run(ir)['retentions'],[])

    def test_gap_not_bridged(self):
        ir=fixture([('F',0,4,0,2,'v'),('E',0,4,3,4,'v')])
        self.assertEqual(run(ir)['retentions'][0]['departure_status'],'no_touching_event_no_gap_bridging')
        self.assertEqual(conditional(ir)['compatibility_tags'],[])

    def test_no_skip_intermediate_leap_to_future_step(self):
        ir=fixture([('F',0,4,0,2,'v'),('A',0,4,2,3,'v'),('E',0,4,3,4,'v')])
        self.assertEqual(run(ir)['retentions'][0]['departure']['event_id'],'s1')
        self.assertEqual(conditional(ir)['compatibility_tags'],[])

    def test_departure_at_end_censored(self):
        ir=fixture([('F',0,4,0,4,'v'),('E',0,4,4,5,'v')])
        self.assertEqual(run(ir)['retentions'][0]['departure_status'],'context_censored')

    def test_polyphonic_voice_abstains(self):
        ir=fixture([('F',0,4,0,2,'v'),('A',0,4,0,2,'v'),('E',0,4,2,3,'v')])
        self.assertEqual(run(ir)['retentions'][0]['departure_status'],'voice_abstention')
        self.assertEqual(conditional(ir)['compatibility_tags'],[])

    def test_other_voice_not_connected(self):
        ir=fixture();ir['note_events'][1]['voice_id']='other'
        self.assertIsNone(run(ir)['retentions'][0]['departure'])

    def test_cross_staff_same_voice_allowed(self):
        ir=fixture();ir['note_events'][1]['display_staff_id']='staff2'
        self.assertEqual(run(ir)['retentions'][0]['departure_status'],'direct_pitch_change')

    def test_ir_and_observations_immutable(self):
        ir=fixture();saved=copy.deepcopy(ir);o=run(ir);obs=copy.deepcopy(o)
        condition_on_members(o,F,C)
        self.assertEqual(ir,saved);self.assertEqual(o,obs)

    def test_exact_triplet_and_reject_float(self):
        ir=fixture(); ir['sounding_events'][0]['span']['end']=q(Fraction(4,3))
        ir['sounding_events'][1]['span']['start']=q(Fraction(4,3))
        self.assertEqual(run(ir)['retentions'][0]['right_retention']['end'],q(Fraction(4,3)))
        ir['sounding_events'][0]['span']['start']=0.0
        with self.assertRaises(ValueError):run(ir)

    def test_invalid_reference_duplicate_and_duration(self):
        for kind in ('ref','duplicate','negative','zero'):
            ir=fixture()
            if kind=='ref':ir['sounding_events'][0]['source_note_ids']=['missing']
            if kind=='duplicate':ir['sounding_events'].append(copy.deepcopy(ir['sounding_events'][0]))
            if kind=='negative':ir['sounding_events'][0]['span']['end']=q(-1)
            if kind=='zero':ir['sounding_events'][0]['span']['end']=q(0)
            with self.assertRaises(ValueError):run(ir)

    def test_grace_explicitly_excluded(self):
        ir=fixture();ir['sounding_events'][0]['span']['end']=q(0)
        ir['note_events'][0]['grace']={'is_grace':True}
        self.assertEqual(run(ir)['excluded_events'][0]['reason'],'grace_not_literal_timing')

    def test_enharmonic_members_not_collapsed(self):
        ir=fixture([('F',1,4,0,2,'v'),('G',0,4,2,3,'v')])
        r=conditional(ir,[['G',-1]],[['G',0]])
        self.assertFalse(r['member_before'])

    def test_catalog(self):
        c=next(c for c in concepts() if c['concept_id']=='hvl.unit22')
        self.assertEqual(c['reviewed_sections'],list(range(1,29)))

    def test_audit_rejects_tampering_before_loading_packages(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'src';src.mkdir();(src/'run-contract.json').write_text('{}')
            (src/'report.json').write_text(json.dumps({'contract_sha256':'bad'}))
            with self.assertRaisesRegex(ValueError,'source_contract_hash_mismatch'):build(src,Path(td)/'out')

    def test_audit_rejects_nontrain_or_rights_before_loading_packages(self):
        for split,rights in [('holdout',True),('train',False)]:
            with tempfile.TemporaryDirectory() as td:
                src=Path(td)/'src';src.mkdir()
                e={'split':split,'rights':{'internal_research_use':rights},'work_family_id':'f',
                   'score_sha256':'s','annotation_sha256':'a','ir_document_id':'ir'}
                (src/'run-contract.json').write_text(json.dumps({'entries':[e]}))
                (src/'report.json').write_text(json.dumps({'contract_sha256':digest(src/'run-contract.json')}))
                with self.assertRaisesRegex(ValueError,'train_research_entries_required'):build(src,Path(td)/'out')


if __name__=='__main__': unittest.main()
