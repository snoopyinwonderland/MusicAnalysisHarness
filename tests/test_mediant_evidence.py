import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.mediant_evidence import observe, mediant_reference
from musicanote_harness.mediant_audit import anchor_kind, mediant_regions, build
from musicanote_harness.harmony_curriculum import concepts


def span(a=0, b=1):
    return {'start': q(a), 'end': q(b)}


def score(pitches):
    return {'sounding_events': [{'sounding_event_id': str(i), 'span': span(),
            'pitch': {'step': s, 'alter': q(a), 'octave': o,
                      'midi_pitch': 12*(o+1)+dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[s]+a}}
            for i, (s,a,o) in enumerate(pitches)]}


def readings(result):
    return {v for cell in result['slices'] for sh in cell['complete_shapes'] for v in sh['compatible_readings']}


class MediantTest(unittest.TestCase):
    def test_references_preserve_spelling_and_mode(self):
        for args, result in [(('A',0,'minor'),('C',0,'major')), (('F',0,'minor'),('A',-1,'major')),
                             (('C',0,'major'),('E',0,'minor')), (('C',-1,'minor'),('E',-2,'major')),
                             (('B',1,'major'),('D',2,'minor'))]:
            self.assertEqual(mediant_reference(*args),result)

    def test_natural_minor_relative_major_same_collection_not_modulation(self):
        r=observe(score([(s,0,4) for s in 'ABCDEFG']),span(),'A')
        self.assertTrue(all(e['home']['diatonic_to_candidate'] and e['mediant']['diatonic_to_candidate'] for e in r['event_coordinates']))
        self.assertIsNone(r['modulation']);self.assertIsNone(r['tonicization'])

    def test_natural_vii_two_readings(self):
        r=observe(score([('G',0,3),('B',0,3),('D',0,4)]),span(),'A')
        self.assertEqual(readings(r),{'natural_VII','V_of_III'})
        self.assertIsNone(r['slices'][0]['complete_shapes'][0]['selected_reading'])

    def test_vii7_two_readings(self):
        r=observe(score([('G',0,3),('B',0,3),('D',0,4),('F',0,4)]),span(),'A')
        self.assertEqual(readings(r),{'natural_VII7','V7_of_III'})

    def test_raised_seventh_is_not_subtonic(self):
        r=observe(score([('G',1,3),('B',0,3),('D',0,4)]),span(),'A')
        self.assertEqual(readings(r),{'leading_tone_triad_of_home'})
        self.assertEqual(r['leading_tone_event_refs'],['0']);self.assertEqual(r['subtonic_event_refs'],[])

    def test_natural_sign_can_be_raised_seventh(self):
        r=observe(score([('E',0,4),('E',-1,4)]),span(),'F')
        self.assertEqual(r['leading_tone_event_refs'],['0']);self.assertEqual(r['subtonic_event_refs'],['1'])

    def test_ii_diminished_can_lead_to_iii(self):
        r=observe(score([('D',0,3),('F',0,3),('B',0,3)]),span(),'A')
        self.assertEqual(readings(r),{'ii_diminished','leading_tone_triad_of_III'})
        self.assertEqual(r['slices'][0]['complete_shapes'][0]['inversion'],1)

    def test_augmented_iii_not_automatic_mediant_function(self):
        r=observe(score([('C',0,4),('E',0,4),('G',1,4)]),span(),'A')
        self.assertEqual(readings(r),{'augmented_mediant_shape_requires_dominant_context_review'})
        self.assertIsNone(r['selected_function'])

    def test_major_mediant_not_relative_major(self):
        r=observe(score([('E',0,4),('G',0,4),('B',0,4)]),span(),'C',mode='major')
        self.assertEqual(readings(r),{'iii','i_in_mediant_minor'})
        self.assertEqual(r['subtonic_event_refs'],[])

    def test_enharmonic_spelling_not_interchangeable(self):
        r=observe(score([('A',-1,3),('B',0,3),('D',0,4)]),span(),'A')
        self.assertEqual(readings(r),set());self.assertEqual(r['leading_tone_event_refs'],[])

    def test_major_applied_mediant_requires_chromatic_quality(self):
        r=observe(score([('B',0,3),('D',1,4),('F',1,4)]),span(),'C',mode='major')
        self.assertEqual(readings(r),{'V_of_iii'})
        self.assertIsNone(r['tonicization'])
        r=observe(score([('B',0,3),('D',0,4),('F',0,4)]),span(),'C',mode='major')
        self.assertEqual(readings(r),{'leading_tone_triad_of_home'})

    def test_arpeggios_and_decorations_not_silently_reduced(self):
        ir=score([('G',0,3),('B',0,3),('D',0,4)])
        for i,e in enumerate(ir['sounding_events']):e['span']=span(i,i+1)
        self.assertEqual(readings(observe(ir,span(0,3),'A')),set())
        self.assertEqual(readings(observe(score([('G',0,3),('B',0,3),('D',0,4),('C',0,5)]),span(),'A')),set())

    def test_half_open_held_and_immutable(self):
        ir=score([('G',0,3),('G',1,3)])
        ir['sounding_events'][0]['span']=span(0,3)
        ir['sounding_events'][1]['span']=span(2,4)
        before=copy.deepcopy(ir);r=observe(ir,span(1,2),'A')
        self.assertEqual(r['held_at_start_ids'],['0']);self.assertEqual(r['leading_tone_event_refs'],[])
        self.assertEqual(ir,before)

    def test_invalid_input(self):
        with self.assertRaisesRegex(ValueError,'major_or_minor'):observe(score([]),span(),'A',mode='dorian')
        with self.assertRaisesRegex(ValueError,'rational_time'):observe(score([]),{'start':0.0,'end':1},'A')
        ir=score([('C',0,4)]);ir['sounding_events'][0]['span']=span(2,1)
        with self.assertRaisesRegex(ValueError,'nonnegative_sounding'):observe(ir,span(),'A')
        ir=score([('C',0,4)]);ir['sounding_events'][0]['pitch']['midi_pitch']=61
        with self.assertRaisesRegex(ValueError,'spelling_midi'):observe(ir,span(),'A')

    def test_zero_duration_grace_reference_without_invented_timing(self):
        ir=score([('G',0,3),('B',0,3),('D',0,4),('C',0,5)])
        ir['sounding_events'][3]['span']=span(0,0)
        r=observe(ir,span(),'A')
        self.assertEqual(r['zero_duration_event_refs'],['3'])
        self.assertEqual(readings(r),{'natural_VII','V_of_III'})


class AuditTest(unittest.TestCase):
    def test_source_dialect_and_scope(self):
        r={'localkey_is_minor':'1','numeral':'VII','form':'','figbass':'','chord_type':'M'}
        self.assertEqual(anchor_kind({'raw_fields':r}),'source_natural_VII')
        r['numeral']='bVII';self.assertIsNone(anchor_kind({'raw_fields':r}))
        r.update(numeral='#vii',form='o',chord_type='o',figbass='6')
        self.assertEqual(anchor_kind({'raw_fields':r}),'source_leading_tone_triad')
        r['relativeroot']='V';self.assertIsNone(anchor_kind({'raw_fields':r}))
        r.update(numeral='V',form='',chord_type='Mm7',figbass='65',relativeroot='III')
        self.assertEqual(anchor_kind({'raw_fields':r}),'applied_dominant_to_mediant')
        r['changes']='#5';self.assertIsNone(anchor_kind({'raw_fields':r}))

    def test_major_iii_not_chromatic_III(self):
        r={'localkey_is_minor':'0','numeral':'iii','form':'','chord_type':'m','figbass':'6'}
        self.assertEqual(anchor_kind({'raw_fields':r}),'source_mediant_triad')
        r.update(numeral='III',chord_type='M');self.assertIsNone(anchor_kind({'raw_fields':r}))

    def test_source_regions_do_not_bridge_gaps_or_key_changes(self):
        def a(start,end,home='f',local='III'):
            return {'raw_fields':{'globalkey':home,'localkey':local,'localkey_is_minor':'0'},'target':{'span':span(start,end)}}
        xs=[a(0,1),a(1,2),a(2,3,local='I'),a(3,4),a(5,6),a(6,7,home='g'),a(7,8,home='F')]
        self.assertEqual(mediant_regions(xs),[[0,1],[3],[4],[5]])

    def test_holdout_rights_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaisesRegex(ValueError,'output_exists'):build('missing',p)
            e={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
               'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            m=p/'m.json';m.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(m,p/'out')['summary']['case_count'],0)
            e['split']='train';m.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(m,p/'bad')

    def test_catalog(self):
        u=next(x for x in concepts() if x['concept_id']=='hvl.unit16')
        self.assertEqual(u['reviewed_sections'],list(range(1,13)))
        self.assertEqual(u['rule_status'],'candidate_not_production')


if __name__=='__main__':unittest.main()
