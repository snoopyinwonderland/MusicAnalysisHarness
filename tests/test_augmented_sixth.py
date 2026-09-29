import copy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.augmented_sixth import hypothesis, source_reference, observe, pc
from musicanote_harness.augmented_sixth_audit import build
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_curriculum import concepts

C=('C',0,'minor')


def fixture(rows):
    ir={'note_events':[],'sounding_events':[]}
    for i,(s,a,o,x,y,v) in enumerate(rows):
        ir['note_events'].append({'note_id':f'n{i}','part_id':'p','voice_id':v})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','source_note_ids':[f'n{i}'],'attack_note_id':f'n{i}',
            'pitch':{'step':s,'alter':q(a),'octave':o,'midi_pitch':12*(o+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[s]+a},
            'span':{'start':q(x),'end':q(y)}})
    return ir


def inspect(rows, family='It', bass='flat6', span=(0,1)):
    return observe(fixture(rows),dict(zip(('start','end'),map(q,span))),{'start':q(0),'end':q(4)},hypothesis(C,family,bass))


def ann(**kw):
    r={'special':'It','chord':'It6','numeral':'vii','chord_type':'It','form':'o','figbass':'6',
       'changes':'b3','relativeroot':'V','localkey_is_minor':'1'};r.update(kw)
    return {'raw_fields':r}


PAIR=[('A',-1,3,0,1,'b'),('F',1,4,0,1,'s'),('G',0,3,1,2,'b'),('G',0,4,1,2,'s')]
TRIAD=[('A',-1,3,0,1,'b'),('C',0,4,0,1,'a'),('F',1,4,0,1,'s')]


class AugmentedSixthTest(unittest.TestCase):
    def test_three_families(self):
        self.assertEqual(hypothesis(C,'It')['members'],[['A',-1],['C',0],['F',1]])
        self.assertEqual(hypothesis(C,'Ger')['roles']['flat3'],['E',-1])
        self.assertEqual(hypothesis(C,'Fr')['roles']['natural2'],['D',0])

    def test_major_minor_same_shape(self):
        self.assertEqual(hypothesis(C,'Ger')['members'],hypothesis(('C',0,'major'),'Ger')['members'])

    def test_no_forced_root(self):self.assertIsNone(hypothesis(C,'It')['root'])

    def test_german43_spelling_distinct_sound_same(self):
        a=hypothesis(C,'Ger');b=hypothesis(C,'Ger43')
        self.assertNotEqual(a['members'],b['members']);self.assertEqual({pc(p) for p in a['members']},{pc(p) for p in b['members']})
        self.assertEqual(b['roles']['sharp2'],['D',1])

    def test_double_accidentals(self):
        self.assertEqual(hypothesis(('F',1,'minor'),'It')['roles']['sharp4'],['B',1])
        self.assertEqual(hypothesis(('C',1,'major'),'Ger43')['roles']['sharp2'],['D',2])

    def test_other_bass(self):self.assertEqual(hypothesis(C,'It','sharp4')['expected_bass'],['F',1])

    def test_invalid_inputs(self):
        for k,f,b in [(C,'Other','flat6'),(C,'It','flat3'),(('C',0,'dorian'),'It','flat6')]:
            with self.assertRaises(ValueError):hypothesis(k,f,b)

    def test_source_expanded_special_not_modifier_erasure(self):
        a=ann();old=copy.deepcopy(a);self.assertEqual(source_reference(a,C)['family'],'It');self.assertEqual(a,old)
        self.assertEqual(source_reference(ann(special='Ger',chord='Ger6',chord_type='Ger',figbass='65'),C)['family'],'Ger')

    def test_source_slash_and_modifiers_abstain(self):
        for kw in ({'relativeroot':'V/vi','chord':'It6/vi'},{'pedal':'V'},{'added_tones':'1'},{'changes':'b3+4'},
                   {'localkey_is_minor':'0'},{'form':''},{'chord':'It65'},{'special':'Fr'}):
            self.assertIsNone(source_reference(ann(**kw),C))

    def test_vertical_support(self):
        c=inspect(TRIAD)['surface']['slices'][0]
        self.assertTrue(c['spelled_family_complete']);self.assertTrue(c['supplied_bass_matches'])

    def test_arpeggio_union_not_vertical(self):
        r=inspect([('A',-1,3,0,F(1,3),'b'),('C',0,4,F(1,3),F(2,3),'a'),('F',1,4,F(2,3),1,'s')])
        self.assertEqual(r['missing_spellings'],[]);self.assertFalse(any(c['spelled_family_complete'] for c in r['surface']['slices']))

    def test_german_dominant_enharmonic_competes(self):
        r=inspect([TRIAD[0],TRIAD[1],('G',-1,4,0,1,'s'),('E',-1,4,0,1,'t')],'Ger')
        self.assertTrue(r['surface']['slices'][0]['enharmonic_only']);self.assertIsNone(r['function'])
        self.assertEqual(r['missing_spellings'],[['F',1]])

    def test_italian_tonic_doubling_count(self):
        r=inspect(TRIAD+[('C',0,5,0,1,'t')]);self.assertEqual(r['surface']['slices'][0]['tonic_count'],2)

    def test_synchronous_outward(self):
        r=inspect(PAIR);self.assertEqual(r['joint_geometry'][0]['kind'],'augmented_sixth_outward_to_octaves')
        self.assertIsNone(r['joint_geometry'][0]['harmonic_resolution_verified'])

    def test_compound_outward(self):
        rows=copy.deepcopy(PAIR);rows[0]=('A',-1,2,0,1,'b');rows[2]=('G',0,2,1,2,'b')
        self.assertEqual(inspect(rows)['joint_geometry'][0]['after_interval']['semitones'],24)

    def test_inward_diminished_third(self):
        r=inspect([('A',-1,4,0,1,'s'),('F',1,4,0,1,'b'),('G',0,4,1,2,'s'),('G',0,4,1,2,'b')],bass='sharp4')
        self.assertEqual(r['joint_geometry'][0]['kind'],'diminished_third_inward_to_unison_or_octaves')

    def test_independent_arrivals_not_joint(self):
        r=inspect([PAIR[0],('F',1,4,0,2,'s'),PAIR[2],('G',0,4,2,3,'s')])
        self.assertEqual(sum(p['semitone_to_goal'] for p in r['critical_paths']),2);self.assertEqual(r['joint_geometry'],[])

    def test_disjoint_sources_not_joint(self):
        r=inspect([PAIR[0],PAIR[2],('F',1,4,2,3,'s'),('G',0,4,3,4,'s')],span=(0,3))
        self.assertEqual(r['joint_geometry'],[])

    def test_wrong_octave_not_step(self):
        r=inspect([PAIR[0],PAIR[1],('G',0,4,1,2,'b'),PAIR[3]])
        self.assertEqual(r['joint_geometry'],[]);self.assertFalse(r['critical_paths'][0]['semitone_to_goal'])

    def test_v7_elision_not_error_or_invented_resolution(self):
        r=inspect([PAIR[0],PAIR[1],PAIR[2],('F',0,4,1,2,'s')])
        self.assertEqual(r['joint_geometry'],[]);self.assertIsNone(r['function'])

    def test_bass_inflection_not_error(self):
        r=inspect([PAIR[0],('A',0,3,1,2,'b'),('G',0,3,2,3,'b')])
        self.assertFalse(r['critical_paths'][0]['semitone_to_goal']);self.assertIsNone(r['function'])

    def test_polyphonic_voice_abstains(self):
        r=inspect(PAIR+[('C',0,4,0,1,'s')]);self.assertEqual(r['joint_geometry'],[])
        self.assertIn('ambiguous_voice',[p['departure_status'] for p in r['critical_paths']])

    def test_rest_gap_abstains(self):
        r=inspect([PAIR[0],('G',0,3,2,3,'b')]);self.assertEqual(r['critical_paths'][0]['departure_status'],'no_touching_event')

    def test_missing_voice_abstains(self):
        r=inspect([('A',-1,3,0,1,None)]);self.assertEqual(r['critical_paths'][0]['departure_status'],'missing_voice')

    def test_tied_sound_preserved(self):
        ir=fixture([('A',-1,3,0,5,'b')]);ir['note_events'].append({'note_id':'tie','part_id':'p','voice_id':'b'});ir['sounding_events'][0]['source_note_ids'].append('tie')
        r=observe(ir,{'start':q(1),'end':q(2)},{'start':q(0),'end':q(4)},hypothesis(C,'It'))
        self.assertEqual(r['critical_paths'][0]['departure_status'],'context_censored');self.assertEqual(r['critical_paths'][0]['event']['span']['end'],q(5))

    def test_grace_excluded(self):
        ir=fixture(TRIAD);ir['note_events'][2]['grace']={'is_grace':True}
        r=observe(ir,{'start':q(0),'end':q(1)},{'start':q(0),'end':q(4)},hypothesis(C,'It'))
        self.assertEqual(r['excluded_grace_refs'],['e2']);self.assertEqual(r['missing_spellings'],[['F',1]])

    def test_repeated_paths_joint_deduplicated(self):
        rows=[('A',-1,3,0,1,'b'),('A',-1,3,1,2,'b'),('F',1,4,0,2,'s'),('G',0,3,2,3,'b'),('G',0,4,2,3,'s')]
        self.assertEqual(len(inspect(rows,span=(0,2))['joint_geometry']),1)

    def test_invalid_ir(self):
        for kind in ('ref','pitch','zero','duplicate','float'):
            ir=fixture(PAIR)
            if kind=='ref':ir['sounding_events'][0]['source_note_ids']=[]
            if kind=='pitch':ir['sounding_events'][0]['pitch']['midi_pitch']=2
            if kind=='zero':ir['sounding_events'][0]['span']['end']=q(0)
            if kind=='duplicate':ir['sounding_events'].append(ir['sounding_events'][0])
            if kind=='float':ir['sounding_events'][0]['span']['end']=0.5
            with self.assertRaises(ValueError):observe(ir,{'start':q(0),'end':q(1)},{'start':q(0),'end':q(4)},hypothesis(C,'It'))

    def test_rights_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.json';out=Path(d)/'out'
            p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','work_family_id':'w','score_sha256':'s','annotation_sha256':'a','rights':{'internal_research_use':False}}]}))
            with self.assertRaises(ValueError):build(p,out)
            self.assertFalse(out.exists())

    def test_catalog(self):
        r=next(c for c in concepts() if c['concept_id']=='hvl.unit30');self.assertEqual(r['reviewed_sections'],list(range(1,26)))


if __name__=='__main__':unittest.main()
