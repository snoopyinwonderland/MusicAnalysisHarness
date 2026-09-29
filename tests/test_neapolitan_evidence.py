import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.neapolitan_evidence import hypothesis, source_reference, context_roles, compare_context, observe
from musicanote_harness.neapolitan_audit import build
from musicanote_harness.seventh_context import chord
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


def inspect(rows):return observe(fixture(rows),{'start':q(0),'end':q(1)},{'start':q(0),'end':q(4)},C)
def row(i,h):return {'ref':str(i),'key':C,'verified':True,'span':{'start':q(i),'end':q(i+1)},'hypothesis':h}
def ann(**kw):
    r={'numeral':'bII','chord_type':'M','form':'','figbass':'6','localkey_is_minor':'1'};r.update(kw)
    return {'raw_fields':r}

DIRECT=[('D',-1,5,0,1,'v'),('B',0,4,1,2,'v')]
FILLED=[('D',-1,5,0,1,'v'),('C',0,5,1,2,'v'),('B',0,4,2,3,'v')]


class NeapolitanTest(unittest.TestCase):
    def test_major_minor_same_spelling(self):
        self.assertEqual(hypothesis(C)['members'],[['D',-1],['F',0],['A',-1]])
        self.assertEqual(hypothesis(C),hypothesis(('C',0,'major')))

    def test_all_inversions(self):
        self.assertEqual([hypothesis(C,i)['expected_bass'] for i in range(3)],[['D',-1],['F',0],['A',-1]])

    def test_double_flat_preserved(self):
        self.assertEqual(hypothesis(('G',-1,'major'))['members'],[['A',-2],['C',-1],['E',-2]])

    def test_invalid_key_inversion(self):
        for key,inv in [(('C',0,'phrygian'),1),(C,3),(C,True)]:
            with self.assertRaises(ValueError):hypothesis(key,inv)

    def test_source_adapter_no_mutation(self):
        a=ann();before=copy.deepcopy(a)
        self.assertEqual(source_reference(a,C),hypothesis(C));self.assertEqual(a,before)

    def test_source_modified_or_seventh_abstains(self):
        for kw in ({'pedal':'V'},{'changes':'4'},{'added_tones':'1'},{'relativeroot':'V'},
                   {'special':'N'},{'chord_type':'MM7','form':'M','figbass':'2'},{'numeral':'II'}):
            self.assertIsNone(source_reference(ann(**kw),C))

    def test_direct_diminished_third(self):
        r=inspect(DIRECT);self.assertEqual(r['flat2_paths'][0]['geometry_tags'],['flat2_to_leading_descending_diminished_third'])
        self.assertIsNone(r['cadence']);self.assertIsNone(r['harmonic_function'])

    def test_filled_path(self):
        self.assertEqual(inspect(FILLED)['flat2_paths'][0]['geometry_tags'],['flat2_tonic_leading_filled_diminished_third'])

    def test_enharmonic_sharp1_not_flat2(self):
        self.assertEqual(inspect([('C',1,5,0,1,'v')])['flat2_paths'],[])

    def test_cross_register_not_resolution(self):
        r=inspect([DIRECT[0],('B',0,5,1,2,'v')]);self.assertEqual(r['flat2_paths'][0]['geometry_tags'],[])

    def test_reattack_chain(self):
        r=inspect([DIRECT[0],('D',-1,5,1,2,'v'),('B',0,4,2,3,'v')])
        self.assertEqual(len(r['flat2_paths'][0]['same_pitch_chain']),2)
        self.assertTrue(r['flat2_paths'][0]['geometry_tags'])

    def test_gap_abstains(self):
        self.assertEqual(inspect([DIRECT[0],('B',0,4,2,3,'v')])['flat2_paths'][0]['departure_status'],'no_touching_event')

    def test_polyphony_abstains(self):
        self.assertEqual(inspect(DIRECT+[('F',0,4,0,1,'v')])['flat2_paths'][0]['departure_status'],'ambiguous_voice')

    def test_missing_voice_abstains(self):
        self.assertEqual(inspect([('D',-1,5,0,1,None)])['flat2_paths'][0]['departure_status'],'missing_voice')

    def test_tie_full_duration_context_censored(self):
        ir=fixture([('D',-1,5,0,5,'v')]);ir['note_events'].append({'note_id':'continuation','part_id':'p','voice_id':'v'})
        ir['sounding_events'][0]['source_note_ids'].append('continuation')
        r=observe(ir,{'start':q(0),'end':q(1)},{'start':q(0),'end':q(4)},C)
        p=r['flat2_paths'][0];self.assertEqual(p['departure_status'],'context_censored')
        self.assertEqual(p['event']['span']['end'],q(5));self.assertEqual(len(p['event']['source_note_ids']),2)

    def test_natural2_not_error(self):
        r=inspect([DIRECT[0],('D',0,5,1,2,'v')]);self.assertEqual(r['flat2_paths'][0]['geometry_tags'],['flat2_to_natural2_not_automatic_error'])

    def test_arpeggio_union_not_vertical(self):
        r=inspect([('F',0,3,0,1,'b'),('D',-1,5,0,1,'s')])
        self.assertEqual(r['literal_support']['complete_vertical_matches'],[])
        from fractions import Fraction as F
        r=inspect([('F',0,3,0,F(1,3),'v'),('A',-1,3,F(1,3),F(2,3),'v'),('D',-1,4,F(2,3),1,'v')])
        self.assertEqual(r['literal_support']['missing_spellings'],[]);self.assertEqual(r['literal_support']['complete_vertical_matches'],[])

    def test_vertical_bass_support(self):
        r=inspect([('F',0,3,0,1,'b'),('A',-1,4,0,1,'a'),('D',-1,5,0,1,'s')])
        self.assertTrue(r['literal_support']['complete_vertical_matches'])

    def test_direct_and_decorated_context(self):
        for hs in ([hypothesis(C),chord(['G',0],'Mm7',3)],
                   [hypothesis(C),chord(['F',1],'o7'),chord(['C',0],'m',2),chord(['G',0],'M')]):
            r=compare_context([row(i,h) for i,h in enumerate(hs)],C)
            self.assertEqual(len(r['compatible_paths']),1);self.assertIsNone(r['cadence'])

    def test_leading43_context(self):
        self.assertIn('leading_tone_shape',context_roles(chord(['B',0],'o7',2),C))
        self.assertNotIn('dominant_shape',context_roles(chord(['G',0],'M',2),C))

    def test_unknown_gap_and_changed_key_not_bridged(self):
        for kind in ('unknown','gap','key','unverified'):
            rs=[row(0,hypothesis(C)),row(1,chord(['C',0],'m',2)),row(2,chord(['G',0],'M'))]
            if kind=='unknown':rs[1]['hypothesis']=None
            if kind=='gap':rs[1]['span']['start']=q(0)
            if kind=='key':rs[1]['key']=('D',0,'minor')
            if kind=='unverified':rs[1]['verified']=False
            self.assertEqual(compare_context(rs,C)['compatible_paths'],[])

    def test_tonic_neighbor_not_forced_predominant(self):
        rs=[row(0,hypothesis(C)),row(1,chord(['C',0],'m')),row(2,chord(['G',0],'M'))]
        self.assertEqual(compare_context(rs,C)['compatible_paths'],[])

    def test_grace_excluded(self):
        ir=fixture(DIRECT);ir['note_events'][0]['grace']={'is_grace':True}
        r=observe(ir,{'start':q(0),'end':q(1)},{'start':q(0),'end':q(4)},C)
        self.assertEqual(r['flat2_paths'],[]);self.assertEqual(r['excluded_grace_refs'],['e0'])

    def test_invalid_ir(self):
        for kind in ('ref','pitch','duplicate','zero','float'):
            ir=fixture(DIRECT)
            if kind=='ref':ir['sounding_events'][0]['source_note_ids']=[]
            if kind=='pitch':ir['sounding_events'][0]['pitch']['midi_pitch']=40
            if kind=='duplicate':ir['sounding_events'].append(ir['sounding_events'][0])
            if kind=='zero':ir['sounding_events'][0]['span']['end']=q(0)
            if kind=='float':ir['sounding_events'][0]['span']['end']=0.5
            with self.assertRaises(ValueError):observe(ir,{'start':q(0),'end':q(1)},{'start':q(0),'end':q(4)},C)

    def test_rights_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.json';out=Path(d)/'out'
            p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','work_family_id':'w','score_sha256':'s','annotation_sha256':'a','rights':{'internal_research_use':False}}]}))
            with self.assertRaises(ValueError):build(p,out)
            self.assertFalse(out.exists())

    def test_catalog(self):
        r=next(c for c in concepts() if c['concept_id']=='hvl.unit29')
        self.assertEqual(r['reviewed_sections'],list(range(1,22)))


if __name__=='__main__':unittest.main()
