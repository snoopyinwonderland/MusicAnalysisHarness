import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.added_dissonance import source_reference, observe
from musicanote_harness.added_dissonance_audit import build
from musicanote_harness.seventh_context import chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_curriculum import concepts


def fixture(rows):
    ir={'note_events':[],'sounding_events':[]}
    for i,(step,alter,octave,start,end,voice) in enumerate(rows):
        ir['note_events'].append({'note_id':f'n{i}','part_id':'p','voice_id':voice,'display_staff_id':'s'})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','attack_note_id':f'n{i}','source_note_ids':[f'n{i}'],
            'pitch':{'step':step,'alter':q(alter),'octave':octave,'midi_pitch':12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter},
            'span':{'start':q(start),'end':q(end)}})
    return ir


CORE=[('G',0,2,0,3,'bass'),('B',0,3,0,3,'tenor'),('D',0,4,0,3,'alto'),('F',0,4,0,3,'seventh')]


def inspect(rows,span=(1,2),context=(0,4),base=None):
    return observe(fixture(rows),dict(zip(('start','end'),map(q,span))),dict(zip(('start','end'),map(q,context))),base or chord(['G',0],'Mm7'))


def ann(**kw):
    raw={'numeral':'V','chord_type':'Mm7','form':'','figbass':'7','localkey_is_minor':'0','changes':'','added_tones':'','relativeroot':''}
    raw.update(kw);return {'annotation_id':'a','raw_fields':raw}


class AddedDissonanceTest(unittest.TestCase):
    def test_source_modifiers_preserved_not_full_label(self):
        a=ann(changes='+b9',added_tones='-11');saved=copy.deepcopy(a);r=source_reference(a,('C',0,'major'))
        self.assertEqual(a,saved);self.assertEqual(r['source_modifiers']['changes'],'+b9')
        self.assertFalse(r['source_modifier_semantics_applied']);self.assertEqual(r['base']['members'],[['G',0],['B',0],['D',0],['F',0]])

    def test_applied_reference(self):
        r=source_reference(ann(relativeroot='ii',changes='13'),('C',0,'major'))
        self.assertEqual(r['base']['root'],['A',0])

    def test_unsupported_not_silently_adapted(self):
        for kw in ({'pedal':'V'},{'special':'Ger'},{'relativeroot':'V/ii'},{'chord_type':'M'},{'form':'M'},{'figbass':'9'}):
            self.assertIsNone(source_reference(ann(**kw),('C',0,'major')))

    def test_ninth_fifth_omission(self):
        r=inspect([p for p in CORE if p[0]!='D']+[('A',0,4,1,2,'soprano')]);cell=r['slices'][0]
        self.assertIn('fifth_absent_with_identity_tones_present',cell['alternative_shape_candidates'])
        self.assertIsNone(r['harmonic_label'])

    def test_third_absence_not_fifth_omission(self):
        r=inspect([p for p in CORE if p[0]!='B']+[('A',0,4,1,2,'soprano')]);a=r['slices'][0]['alternative_shape_candidates']
        self.assertIn('upper_supertonic_shape_over_root_pedal_function_unverified',a)
        self.assertNotIn('fifth_absent_with_identity_tones_present',a)

    def test_rootless_not_invented(self):
        r=inspect([p for p in CORE if p[0]!='G']+[('A',-1,4,1,2,'soprano')]);c=r['slices'][0]
        self.assertFalse(c['reference_members_present']['root'])
        self.assertIn('leading_tone_seventh_or_rootless_ninth_compete_no_root_invented',c['alternative_shape_candidates'])

    def test_two_ninth_spellings(self):
        for alter,role in [(0,'major_ninth'),(-1,'minor_ninth')]:
            r=inspect(CORE+[('A',alter,4,1,2,'s')]);self.assertTrue(any(p['role']==role for p in r['paths']))

    def test_enharmonic_not_ninth(self):
        r=inspect(CORE+[('G',1,4,1,2,'s')]);self.assertFalse(any(p['role']=='minor_ninth' for p in r['paths']))
        self.assertIn('e4',r['slices'][0]['unexplained_event_refs'])

    def test_fourth_replacement(self):
        r=inspect([p for p in CORE if p[0]!='B']+[('C',0,5,1,2,'s')])
        self.assertIn('fourth_replacing_third_shape',r['slices'][0]['alternative_shape_candidates'])

    def test_single_extension_not_replacement_chord(self):
        for pitch in ('C','E'):
            r=inspect([(pitch,0,5,1,2,'s')])
            self.assertEqual(r['slices'][0]['alternative_shape_candidates'],[])
            self.assertEqual(len(r['paths']),1)

    def test_sixth_replacement_and_target(self):
        for a,role in [(0,'major_sixth_or_thirteenth'),(-1,'minor_sixth_or_thirteenth')]:
            r=inspect([p for p in CORE if p[0]!='D']+[('E',a,5,1,2,'s'),('D',0,5,2,3,'s')])
            p=next(p for p in r['paths'] if p['role']==role)
            self.assertTrue(p['arrives_at_reference_target_spelling'])

    def test_inside_versus_outside_source_end(self):
        rows=CORE+[('A',0,4,1,2,'s'),('G',0,4,2,3,'s')]
        for span,where in [((1,3),'inside_supplied_span'),((1,2),'at_or_after_supplied_end')]:
            r=inspect(rows,span);p=next(p for p in r['paths'] if p['role']=='major_ninth')
            self.assertEqual(p['departure_position'],where);self.assertIsNone(p['resolution_verified'])

    def test_root_then_seventh_not_forced_resolution(self):
        r=inspect(CORE+[('A',0,4,1,2,'s'),('G',0,4,2,3,'s'),('F',0,4,3,4,'s')])
        p=next(p for p in r['paths'] if p['role']=='major_ninth')
        self.assertTrue(p['root_then_seventh_geometry']);self.assertIsNone(p['resolution_verified'])

    def test_full_tie_and_restrike_preserved(self):
        ir=fixture(CORE+[('A',0,4,0,2,'s'),('A',0,4,2,3,'s'),('G',0,4,3,4,'s')]);old=copy.deepcopy(ir)
        r=observe(ir,{'start':q(1),'end':q(2)},{'start':q(0),'end':q(4)},chord(['G',0],'Mm7'))
        p=next(p for p in r['paths'] if p['role']=='major_ninth')
        self.assertEqual(len(p['same_pitch_chain']),2);self.assertEqual(p['event']['span']['start'],q(0))
        self.assertEqual(ir,old);self.assertTrue(p['retained_to_supplied_end'])

    def test_compound_interval_not_pitchclass(self):
        r=inspect(CORE+[('A',0,4,1,2,'s')]);p=next(p for p in r['paths'] if p['role']=='major_ninth')
        self.assertEqual(p['simultaneous_root_intervals'][0]['interval']['generic'],16)

    def test_register_below_root_retained(self):
        r=inspect(CORE+[('A',0,1,1,2,'s')]);p=next(p for p in r['paths'] if p['role']=='major_ninth')
        self.assertLess(p['simultaneous_root_intervals'][0]['interval']['semitones'],0)
        self.assertFalse(r['slices'][0]['reference_root_is_lowest'])

    def test_gap_and_other_voice_abstain(self):
        for row in [('G',0,4,3,4,'s'),('G',0,4,2,3,'other')]:
            r=inspect(CORE+[('A',0,4,1,2,'s'),row]);p=next(p for p in r['paths'] if p['role']=='major_ninth')
            self.assertEqual(p['departure_status'],'no_touching_event')

    def test_polyphony_abstain(self):
        r=inspect(CORE+[('A',0,4,1,2,'s'),('C',0,5,1,2,'s'),('G',0,4,2,3,'s')])
        self.assertTrue(all(p['departure_status']=='ambiguous_voice' for p in r['paths'] if p['role']!='seventh'))

    def test_context_censored(self):
        r=inspect(CORE+[('A',0,4,1,5,'s')]);p=next(p for p in r['paths'] if p['role']=='major_ninth')
        self.assertEqual(p['departure_status'],'context_censored');self.assertEqual(p['event']['span']['end'],q(5))

    def test_absence_of_direct_resolution_not_failure_label(self):
        r=inspect(CORE+[('A',0,4,1,2,'s'),('E',0,5,2,3,'s')]);p=next(p for p in r['paths'] if p['role']=='major_ninth')
        self.assertFalse(p['arrives_at_reference_target_spelling']);self.assertIsNone(p['resolution_verified'])

    def test_arpeggio_not_vertical(self):
        r=inspect([('G',0,2,1,Fraction(5,4),'a'),('B',0,3,Fraction(5,4),Fraction(3,2),'a'),('F',0,4,Fraction(3,2),Fraction(7,4),'a'),('A',0,4,Fraction(7,4),2,'a')])
        self.assertFalse(any('dominant_seventh_plus_ninth_support_not_verdict' in s['alternative_shape_candidates'] for s in r['slices']))

    def test_nonzero_grace_excluded(self):
        ir=fixture(CORE+[('A',0,4,1,2,'s')]);ir['note_events'][-1]['grace']={'is_grace':True}
        r=observe(ir,{'start':q(1),'end':q(2)},{'start':q(0),'end':q(4)},chord(['G',0],'Mm7'))
        self.assertEqual(r['excluded_grace_refs'],['e4']);self.assertEqual(len(r['paths']),1)

    def test_invalid_time_references_pitch(self):
        for kind in ('time','ref','pitch','duplicate'):
            ir=fixture(CORE)
            if kind=='time':ir['sounding_events'][0]['span']['end']=1.5
            if kind=='ref':ir['sounding_events'][0]['source_note_ids']=[]
            if kind=='pitch':ir['sounding_events'][0]['pitch']['midi_pitch']=99
            if kind=='duplicate':ir['sounding_events'].append(ir['sounding_events'][0])
            with self.assertRaises(ValueError):observe(ir,{'start':q(1),'end':q(2)},{'start':q(0),'end':q(4)},chord(['G',0],'Mm7'))

    def test_invalid_base_and_span(self):
        with self.assertRaises(ValueError):inspect(CORE,base=chord(['G',0],'M'))
        with self.assertRaises(ValueError):inspect(CORE,span=(1,5))

    def test_rights_gate(self):
        with tempfile.TemporaryDirectory() as d:
            m=Path(d)/'m.json';out=Path(d)/'out'
            m.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','work_family_id':'w','score_sha256':'s','annotation_sha256':'a','rights':{'internal_research_use':False}}]}))
            with self.assertRaises(ValueError):build(m,out)
            self.assertFalse(out.exists())

    def test_catalog(self):
        r=next(r for r in concepts() if r['concept_id']=='hvl.unit28')
        self.assertEqual(r['reviewed_sections'],list(range(1,12)));self.assertEqual(r['rule_status'],'candidate_not_production')


if __name__=='__main__':unittest.main()
