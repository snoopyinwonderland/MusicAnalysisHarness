import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.leading_tone_seventh import hypothesis, source_candidate, trace_members
from musicanote_harness.leading_tone_seventh_audit import build
from musicanote_harness.harmony_curriculum import concepts


def fixture(rows=None):
    rows=rows or [('B',0,3,0,1,'v1'),('C',0,4,1,2,'v1'),('A',-1,4,0,1,'v2'),('G',0,4,1,2,'v2')]
    ir={'note_events':[],'sounding_events':[]}
    for i,(step,alter,octave,start,end,voice) in enumerate(rows):
        ir['note_events'].append({'note_id':f'n{i}','part_id':'p','voice_id':voice,'display_staff_id':'s'})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','attack_note_id':f'n{i}','source_note_ids':[f'n{i}'],
            'pitch':{'step':step,'alter':q(alter),'octave':octave,
                     'midi_pitch':12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter},
            'span':{'start':q(start),'end':q(end)}})
    return ir


def run(ir, chord=None, end=1):
    return trace_members(ir,{'start':q(0),'end':q(end)},{'start':q(0),'end':q(3)},chord or hypothesis('C'))


class LeadingSeventhTest(unittest.TestCase):
    def test_minor_spelling(self):
        h=hypothesis('C')
        self.assertEqual(h['members'],{'root':['B',0],'third':['D',0],'fifth':['F',0],'seventh':['A',-1]})

    def test_half_diminished_major(self):
        h=hypothesis('C',mode='major',quality='half_diminished_seventh')
        self.assertEqual(h['members']['seventh'],['A',0])
        self.assertEqual(h['textbook_profile'],'unit23_basic_major')

    def test_major_full_and_minor_half_preserved_not_forbidden(self):
        for mode,quality in [('major','diminished_seventh'),('minor','half_diminished_seventh')]:
            self.assertEqual(hypothesis('C',mode=mode,quality=quality)['textbook_profile'],'mixture_or_other_context_requires_review')

    def test_enharmonic_spelling_not_pitch_class_root_choice(self):
        a=hypothesis('C');b=hypothesis('E',-1)
        self.assertNotEqual(a['members'],b['members'])
        self.assertEqual(b['members']['root'],['D',0])
        self.assertEqual(b['members']['seventh'],['C',-1])

    def test_inversions_no_hard_arrival_requirement(self):
        for i in range(4):
            h=hypothesis('C',inversion=i)
            self.assertEqual(h['expected_bass_spelling'],list(h['members'].values())[i])
            self.assertFalse(h['arrival_inversion_is_requirement'])

    def test_root_and_seventh_independent_expected_paths(self):
        r=run(fixture());self.assertEqual({x['member'] for x in r['records'] if x['exit_step_candidate']},{'root','seventh'})
        self.assertIsNone(r['functional_verdict']);self.assertIsNone(r['cadence'])

    def test_seventh_resolution_alone_not_tonic_proof(self):
        r=run(fixture([('A',-1,4,0,1,'v'),('G',0,4,1,2,'v')]))
        self.assertTrue(r['records'][0]['exit_step_candidate']);self.assertIsNone(r['functional_verdict'])

    def test_octave_displacement_not_step(self):
        r=run(fixture([('B',0,3,0,1,'v'),('C',0,5,1,2,'v')]))
        self.assertFalse(r['records'][0]['expected_step_geometry'])

    def test_internal_step_not_exit(self):
        r=run(fixture(),end=2)
        self.assertTrue(r['records'][0]['expected_step_geometry'])
        self.assertFalse(r['records'][0]['exit_step_candidate'])

    def test_tie_full_span_and_refs_kept(self):
        ir=fixture([('B',0,3,0,2,'v'),('C',0,4,2,3,'v')]);n=copy.deepcopy(ir['note_events'][0]);n['note_id']='tie'
        ir['note_events'].append(n);ir['sounding_events'][0]['source_note_ids'].append('tie')
        r=run(ir)['records'][0]
        self.assertEqual(r['event']['original_span']['end'],q(2));self.assertEqual(r['event']['source_note_ids'],['n0','tie'])
        self.assertTrue(r['exit_step_candidate'])

    def test_same_pitch_attacks_not_tied(self):
        r=run(fixture([('B',0,3,0,1,'v'),('B',0,3,1,2,'v'),('C',0,4,2,3,'v')]))['records'][0]
        self.assertEqual(len(r['same_pitch_attack_chain']),2);self.assertTrue(r['exit_step_candidate'])

    def test_gap_not_bridged(self):
        r=run(fixture([('B',0,3,0,1,'v'),('C',0,4,2,3,'v')]))['records'][0]
        self.assertEqual(r['departure_status'],'no_touching_event')

    def test_polyphonic_voice_abstains(self):
        ir=fixture();ir['note_events'][2]['voice_id']='v1'
        r=run(ir)['records'][0];self.assertEqual(r['departure_status'],'ambiguous_voice')

    def test_cross_staff_same_voice_works(self):
        ir=fixture();ir['note_events'][1]['display_staff_id']='s2'
        self.assertTrue(run(ir)['records'][0]['exit_step_candidate'])

    def test_distinct_voices_not_joined(self):
        ir=fixture();ir['note_events'][1]['voice_id']='other'
        self.assertFalse(run(ir)['records'][0]['exit_step_candidate'])

    def test_context_censored(self):
        r=run(fixture([('B',0,3,0,3,'v'),('C',0,4,3,4,'v')]))['records'][0]
        self.assertEqual(r['departure_status'],'context_censored')

    def test_preparation_from_fifth_not_nct_truth(self):
        ir=fixture([('G',0,4,0,1,'v'),('A',-1,4,1,2,'v'),('G',0,4,2,3,'v')])
        r=trace_members(ir,{'start':q(1),'end':q(2)},{'start':q(0),'end':q(3)},hypothesis('C'))['records'][0]
        self.assertEqual(r['seventh_entry_geometry'],'step_from_tonic_fifth');self.assertIsNone(r['resolution_verified'])

    def test_immutable(self):
        ir=fixture();saved=copy.deepcopy(ir);run(ir);self.assertEqual(ir,saved)

    def test_invalid_time_and_refs(self):
        for kind in ('float','duplicate','ref','negative'):
            ir=fixture()
            if kind=='float':ir['sounding_events'][0]['span']['start']=0.0
            if kind=='duplicate':ir['sounding_events'].append(copy.deepcopy(ir['sounding_events'][0]))
            if kind=='ref':ir['sounding_events'][0]['source_note_ids']=['missing']
            if kind=='negative':ir['sounding_events'][0]['span']['end']=q(-1)
            with self.assertRaises(ValueError):run(ir)

    def test_grace_excluded(self):
        ir=fixture();ir['sounding_events'][0]['span']['end']=q(0);ir['note_events'][0]['grace']={'is_grace':True}
        self.assertEqual(run(ir)['excluded_grace_event_ids'],['e0'])

    def test_source_adapter_and_applied_chord_not_guessed(self):
        a={'raw_fields':{'numeral':'#vii','form':'o','chord_type':'o7','figbass':'2','localkey_is_minor':'1'}}
        self.assertEqual(source_candidate(a),('diminished_seventh',3))
        for k,v in [('relativeroot','V'),('added_tones','2'),('numeral','vii'),('form','%')]:
            b=copy.deepcopy(a);b['raw_fields'][k]=v;self.assertIsNone(source_candidate(b))

    def test_invalid_hypotheses_and_catalog(self):
        for args in ({'inversion':True},{'inversion':4},{'quality':'major'},{'mode':'dorian'}):
            with self.assertRaises(ValueError):hypothesis('C',**args)
        self.assertEqual(next(c for c in concepts() if c['concept_id']=='hvl.unit23')['reviewed_sections'],list(range(1,17)))

    def test_audit_rights_guard_before_package_access(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'manifest.json';p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas',
                'package_path':'not-to-open','rights':{'internal_research_use':False},'work_family_id':'x',
                'score_sha256':'s','annotation_sha256':'a'}]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(p,Path(td)/'out')


if __name__=='__main__':unittest.main()
