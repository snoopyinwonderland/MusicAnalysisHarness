import copy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.chromatic_embellishment import (mixture_routes, augmented_source,
    altered_dominant, common_tone_comparison, direct_paths, observe_augmented, observe_common_tone)
from musicanote_harness.chromatic_embellishment_audit import build
from musicanote_harness.seventh_context import chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_curriculum import concepts

C=('C',0,'major')


def span(a,b):return {'start':q(a),'end':q(b)}


def fixture(rows):
    ir={'note_events':[],'sounding_events':[]}
    for i,(s,a,o,x,y,v) in enumerate(rows):
        ir['note_events'].append({'note_id':f'n{i}','part_id':'p','voice_id':v})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','source_note_ids':[f'n{i}'],'attack_note_id':f'n{i}',
            'pitch':{'step':s,'alter':q(a),'octave':o,'midi_pitch':12*(o+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[s]+a},
            'span':span(x,y)})
    return ir


def ann(**kw):
    r={'numeral':'I','chord_type':'+','form':'+','figbass':'','localkey_is_minor':'0'};r.update(kw)
    return {'raw_fields':r}


RISE=[('G',0,4,0,1,'s'),('G',1,4,1,2,'s'),('A',0,4,2,3,'s')]
CT=chord(['D',1],'o7');TARGET=chord(['C',0],'M')
CT_ROWS=[('C',0,3,0,3,'b'),('D',1,4,0,1,'a'),('E',0,4,1,2,'a'),
         ('F',1,4,0,1,'t'),('G',0,4,1,2,'t'),('A',0,4,0,1,'s'),('G',0,4,1,2,'s')]


def augmented(rows):return observe_augmented(fixture(rows),span(1,2),span(0,4),chord(['C',0],'+'))
def ct(rows):return observe_common_tone(fixture(rows),span(0,1),span(1,2),span(0,4),CT,TARGET)


class ChromaticEmbellishmentTest(unittest.TestCase):
    def test_mixture_routes(self):
        for root,quality,name in [(['E',-1],'M','simple_bIII'),(['G',0],'m','simple_v'),(['B',-1],'M','simple_bVII'),
                (['E',0],'M','secondary_III'),(['A',0],'M','secondary_VI'),(['D',-1],'m','double_bii'),
                (['E',-1],'m','double_biii'),(['A',-1],'m','double_bvi'),(['B',-1],'m','double_bvii')]:
            r=mixture_routes(chord(root,quality),C);self.assertEqual(r[0]['name'],name)
            self.assertFalse(r[0]['selected']);self.assertIsNone(r[0]['mixture_confirmed'])

    def test_double_flat_transposition(self):
        self.assertEqual(mixture_routes(chord(['E',-2],'m'),('D',-1,'major'))[0]['name'],'double_bii')

    def test_mixture_scope_no_seventh_or_minor(self):
        for h,k in [(TARGET,C),(chord(['E',0],'Mm7'),C),(TARGET,('C',0,'minor')),(None,C)]:
            self.assertEqual(mixture_routes(h,k),[])

    def test_augmented_source_not_mutated(self):
        a=ann();old=copy.deepcopy(a);self.assertEqual(augmented_source(a,C)['members'],[['C',0],['E',0],['G',1]])
        self.assertEqual(a,old)

    def test_augmented_source_applied_root(self):
        h=augmented_source(ann(numeral='V',relativeroot='IV',figbass='6'),('B',-1,'major'))
        self.assertEqual(h['root'],['B',-1]);self.assertEqual(h['inversion'],1)

    def test_augmented_source_rejects_unsupported(self):
        for kw in ({'changes':'5'},{'pedal':'I'},{'relativeroot':'V/ii'},{'form':''},{'figbass':'7'},{'added_tones':'6'}):
            self.assertIsNone(augmented_source(ann(**kw),C))

    def test_altered_dominant_templates(self):
        a=altered_dominant(['G',0],1);b=altered_dominant(['G',0],-1,2)
        self.assertEqual(a['members'][2],['D',1]);self.assertEqual(b['expected_bass'],['D',-1])
        self.assertEqual(a['base_reference']['members'][2],['D',0]);self.assertIsNone(a['function'])
        for value in (True,0,2):
            with self.assertRaises(ValueError):altered_dominant(['C',0],value)

    def test_fifth_rise_geometry(self):
        p=augmented(RISE)['fifth_paths']['paths'][0]
        self.assertEqual(len(p['geometry_tags']),2);self.assertIsNone(p['nct_verdict'])

    def test_contracted_entry_not_required(self):
        p=augmented(RISE[1:])['fifth_paths']['paths'][0]
        self.assertEqual(p['geometry_tags'],['augmented5_to_sixth_semitone_rise'])

    def test_wrong_register_not_step(self):
        p=augmented(RISE[:2]+[('A',0,5,2,3,'s')])['fifth_paths']['paths'][0]
        self.assertNotIn('augmented5_to_sixth_semitone_rise',p['geometry_tags'])

    def test_enharmonic_not_augmented_fifth(self):
        self.assertEqual(augmented([('A',-1,4,1,2,'s')])['fifth_paths']['paths'],[])

    def test_gap_no_invented_path(self):
        p=augmented(RISE[:2]+[('A',0,4,3,4,'s')])['fifth_paths']['paths'][0]
        self.assertEqual(p['departure_status'],'no_touching_event')

    def test_polyphonic_voice_abstains(self):
        p=augmented(RISE+[('C',0,5,1,2,'s')])['fifth_paths']['paths'][0]
        self.assertEqual(p['departure_status'],'ambiguous_voice');self.assertEqual(p['geometry_tags'],[])

    def test_missing_voice(self):
        p=augmented([('G',1,4,1,2,None)])['fifth_paths']['paths'][0]
        self.assertEqual(p['departure_status'],'missing_voice')

    def test_grace_excluded(self):
        ir=fixture(RISE);ir['note_events'][1]['grace']={'is_grace':True}
        p=observe_augmented(ir,span(1,2),span(0,4),chord(['C',0],'+'))['fifth_paths']
        self.assertEqual(p['paths'],[]);self.assertEqual(p['excluded_grace_refs'],['e1'])

    def test_tie_span_not_truncated(self):
        ir=fixture([('G',1,4,0,5,'s')]);ir['note_events'].append({'note_id':'tie','part_id':'p','voice_id':'s'})
        ir['sounding_events'][0]['source_note_ids'].append('tie')
        p=observe_augmented(ir,span(1,2),span(0,4),chord(['C',0],'+'))['fifth_paths']['paths'][0]
        self.assertEqual(p['event']['span']['end'],q(5));self.assertEqual(p['departure_status'],'context_censored')

    def test_common_tone_spelling_competition(self):
        a=common_tone_comparison(CT,TARGET);b=common_tone_comparison(chord(['F',1],'o7'),TARGET)
        self.assertTrue(a['usual_spelling_match']);self.assertTrue(b['flat3_variant_match'])
        self.assertFalse(b['usual_spelling_match']);self.assertIsNone(a['common_tone_function'])

    def test_enharmonic_shape_not_spelling(self):
        a=common_tone_comparison(chord(['C',0],'o7'),TARGET)
        self.assertTrue(a['pitch_class_shape_match']);self.assertFalse(a['usual_spelling_match']);self.assertFalse(a['flat3_variant_match'])

    def test_normal_leading_tone_negative_control(self):
        a=common_tone_comparison(chord(['B',0],'o7'),TARGET)
        self.assertFalse(a['pitch_class_shape_match']);self.assertFalse(a['target_root_common_pitch_class'])

    def test_dominant7_target_all_upper_semitones(self):
        rows=[('G',0,3,0,3,'b'),('A',1,4,0,1,'a'),('B',0,4,1,2,'a'),
              ('C',1,5,0,1,'t'),('D',0,5,1,2,'t'),('E',0,5,0,1,'s'),('F',0,5,1,2,'s')]
        r=observe_common_tone(fixture(rows),span(0,1),span(1,2),span(0,4),chord(['A',1],'o7'),chord(['G',0],'Mm7'))
        self.assertTrue(r['comparison']['usual_spelling_match'])
        self.assertEqual(sum(p['step_into_supplied_target_span'] for p in r['voice_paths']['paths']),3)
        self.assertIsNone(r['common_tone_function'])

    def test_arpeggiated_union_not_vertical_chord(self):
        rows=[('C',0,4,1,F(4,3),'s'),('E',0,4,F(4,3),F(5,3),'s'),('G',1,4,F(5,3),2,'s')]
        support=augmented(rows)['literal_support']
        self.assertEqual(support['missing_spellings'],[]);self.assertEqual(support['complete_vertical_matches'],[])
        self.assertFalse(support['union_is_simultaneous'])

    def test_minor_and_64_cautions(self):
        self.assertTrue(common_tone_comparison(CT,chord(['C',0],'m'))['target_minor_caution'])
        self.assertTrue(common_tone_comparison(CT,chord(['C',0],'M',2))['target64_not_stable_tonic'])

    def test_actual_held_root_and_steps(self):
        r=ct(CT_ROWS);self.assertEqual(r['common_root_links'][0]['kind'],'held_sounding_event')
        self.assertEqual(sum(p['step_into_supplied_target_span'] for p in r['voice_paths']['paths']),3)
        self.assertIsNone(r['cadence']);self.assertIsNone(r['common_tone_function'])

    def test_hypothetical_common_root_is_not_held_evidence(self):
        r=ct(CT_ROWS[1:]);self.assertTrue(r['comparison']['target_root_common_spelling']);self.assertEqual(r['common_root_links'],[])

    def test_repeated_root_not_sustain_deduplicated(self):
        r=ct([('C',0,3,0,F(1,2),'b'),('C',0,3,F(1,2),1,'b'),('C',0,3,1,2,'b')])
        self.assertEqual(len(r['common_root_links']),1);self.assertTrue(r['common_root_links'][0]['not_sustained_proof'])
        self.assertEqual(r['common_root_links'][0]['event_refs'],['e0','e1','e2'])

    def test_common_root_gap(self):
        self.assertEqual(ct([('C',0,3,0,F(1,2),'b'),('C',0,3,1,2,'b')])['common_root_links'],[])

    def test_departure_before_target_not_target_step(self):
        r=ct([('D',1,4,0,F(1,2),'s'),('E',0,4,F(1,2),2,'s')])
        self.assertFalse(r['voice_paths']['paths'][0]['step_into_supplied_target_span'])

    def test_departure_after_target_not_target_step(self):
        r=ct([('D',1,4,0,2,'s'),('E',0,4,2,3,'s')])
        self.assertFalse(r['voice_paths']['paths'][0]['step_into_supplied_target_span'])

    def test_nonadjacent_or_censored_target_rejected(self):
        for nxt,ctx in [(span(2,3),span(0,4)),(span(1,2),span(0,1))]:
            with self.assertRaises(ValueError):observe_common_tone(fixture(CT_ROWS),span(0,1),nxt,ctx,CT,TARGET)

    def test_invalid_ir(self):
        for kind in ('ref','pitch','zero','duplicate','duplicate_note','float'):
            ir=fixture(RISE)
            if kind=='ref':ir['sounding_events'][0]['source_note_ids']=[]
            if kind=='pitch':ir['sounding_events'][0]['pitch']['midi_pitch']=1
            if kind=='zero':ir['sounding_events'][0]['span']['end']=q(0)
            if kind=='duplicate':ir['sounding_events'].append(ir['sounding_events'][0])
            if kind=='duplicate_note':ir['note_events'].append(ir['note_events'][0])
            if kind=='float':ir['sounding_events'][0]['span']['end']=0.5
            with self.assertRaises(ValueError):direct_paths(ir,span(1,2),span(0,4),[['G',1]])

    def test_rights_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.json';out=Path(d)/'out'
            p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','work_family_id':'w','score_sha256':'s','annotation_sha256':'a','rights':{'internal_research_use':False}}]}))
            with self.assertRaises(ValueError):build(p,out)
            self.assertFalse(out.exists())

    def test_catalog(self):
        r=next(c for c in concepts() if c['concept_id']=='hvl.unit31');self.assertEqual(r['reviewed_sections'],list(range(1,19)))


if __name__=='__main__':unittest.main()
