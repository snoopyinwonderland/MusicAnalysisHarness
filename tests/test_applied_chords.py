import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.applied_chords import hypothesis, target_reference, source_applied, source_harmony, contextualize, observe
from musicanote_harness.applied_chords_audit import build
from musicanote_harness.seventh_context import chord
from musicanote_harness.harmony_curriculum import concepts


def fixture(rows):
    ir={'note_events':[],'sounding_events':[]}
    for i,(s,a,o,x,y,v) in enumerate(rows):
        ir['note_events'].append({'note_id':f'n{i}','part_id':'p','voice_id':v,'display_staff_id':'s'})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','attack_note_id':f'n{i}','source_note_ids':[f'n{i}'],
            'pitch':{'step':s,'alter':q(a),'octave':o,'midi_pitch':12*(o+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[s]+a},
            'span':{'start':q(x),'end':q(y)}})
    return ir


def run(ir,h=None,end=1):
    return observe(ir,{'start':q(0),'end':q(end)},{'start':q(0),'end':q(4)},h or hypothesis(['G',0],'M','V7'))


def ann(**kw):
    return {'raw_fields':{'localkey_is_minor':'0','numeral':'V','form':'','chord_type':'Mm7','figbass':'65','relativeroot':'ii',**kw}}


class AppliedChordsTest(unittest.TestCase):
    def test_v_and_vii_target_spelling(self):
        self.assertEqual(hypothesis(['G',0],'M','V7')['chord']['members'],[['D',0],['F',1],['A',0],['C',0]])
        self.assertEqual(hypothesis(['G',0],'M','vii7')['chord']['members'],[['F',1],['A',0],['C',0],['E',-1]])

    def test_minor_target_leading_tone_and_double_accidental(self):
        h=hypothesis(['D',1],'m','vii7');self.assertEqual(h['leading_tone'],['C',2])
        self.assertEqual(h['chord']['members'][-1],['B',0])

    def test_half_minor_profile_not_universal_ban(self):
        h=hypothesis(['D',0],'m','vii_half7')
        self.assertEqual(h['textbook_profile'],'outside_basic_target_profile');self.assertFalse(h['profile_is_universal_prohibition'])

    def test_diminished_target_not_basic_tonic(self):
        with self.assertRaises(ValueError):hypothesis(['B',0],'o','V7')
        for token in ('viio','V/ii','unknown'):
            with self.assertRaises(ValueError):target_reference(token,'C')

    def test_all_inversions(self):
        for f in ('V','V7','vii','vii7','vii_half7'):
            n=3 if f in ('V','vii') else 4
            for i in range(n):
                h=hypothesis(['G',0],'M',f,i);self.assertEqual(h['chord']['expected_bass'],h['chord']['members'][i])
            with self.assertRaises(ValueError):hypothesis(['G',0],'M',f,n)

    def test_minor_diatonic_applied_no_accidental_required(self):
        t=target_reference('III','C',mode='minor');h=hypothesis(t['root'],t['quality'],'V7')
        cx=contextualize(h,home=('C',0,'minor'))
        self.assertTrue(all(c['alteration_from_home_form']==0 for c in cx['home_coordinates']))

    def test_source_minor_target_convention(self):
        h=source_applied(ann(numeral='#vii',form='o',chord_type='o7',figbass='7'),'C')
        self.assertEqual(h['chord']['root'],['C',1]);self.assertEqual(h['target']['root'],['D',0])
        self.assertIsNone(source_applied(ann(numeral='vii',form='o',chord_type='o7',figbass='7'),'C'))

    def test_source_major_target_and_lowered_target(self):
        h=source_applied(ann(relativeroot='bVI'),'C')
        self.assertEqual(h['target']['root'],['A',-1]);self.assertEqual(h['chord']['root'],['E',-1])
        h=source_applied(ann(relativeroot='V',numeral='vii',form='%',chord_type='%7',figbass='43'),'C')
        self.assertEqual(h['family'],'vii_half7')

    def test_source_modifiers_and_nested_not_erased(self):
        for k,v in [('changes','4'),('added_tones','2'),('pedal','I'),('special','Ger'),('relativeroot','V/vi'),('chord_type','Ger')]:
            self.assertIsNone(source_applied(ann(**{k:v}),'C'))

    def test_source_harmony_plain_and_applied(self):
        self.assertEqual(source_harmony(ann(),'C')['root'],['A',0])
        self.assertEqual(source_harmony(ann(relativeroot='',numeral='I',chord_type='M',figbass=''),'C')['root'],['C',0])

    def test_following_target_and_inversion(self):
        h=hypothesis(['G',0],'M','V7');cx=contextualize(h,following=chord(['G',0],'Mm7',2))
        self.assertTrue(cx['following_has_target_triad_core']);self.assertIsNone(cx['tonicization']);self.assertIsNone(cx['modulation'])

    def test_wrong_quality_not_target(self):
        h=hypothesis(['G',0],'M','V7');self.assertFalse(contextualize(h,following=chord(['G',0],'m'))['following_has_target_triad_core'])

    def test_repeated_target_and_back_relation(self):
        h=hypothesis(['D',0],'m','V');d=chord(['D',0],'m')
        self.assertIn('connects_statements_of_target',contextualize(h,d,d)['role_candidates'])
        self.assertIn('back_relating_possible_needs_larger_context',contextualize(h,d,chord(['G',0],'M'))['role_candidates'])

    def test_unknown_neighbor_not_negative(self):
        h=hypothesis(['G',0],'M','V7');cx=contextualize(h)
        self.assertIsNone(cx['following_has_target_triad_core']);self.assertEqual(cx['role_candidates'],[])

    def test_applied_extension_not_immediate_failure(self):
        h=hypothesis(['G',0],'M','vii',1)
        cx=contextualize(h,following=hypothesis(['G',0],'M','vii7',1)['chord'])
        self.assertFalse(cx['following_has_target_triad_core'])
        self.assertEqual(cx['following_applied_family_compatibility'],['vii7'])
        self.assertIn('continues_applied_family_candidate',cx['role_candidates'])
        self.assertIsNone(cx['applied_function'])

    def test_tonic_triad_and_secondary_mixture_alternatives(self):
        cx=contextualize(hypothesis(['F',0],'M','V'),home=('C',0,'major'))
        self.assertIn('identical_to_home_tonic_triad_not_applied_proof',cx['warnings'])
        cx=contextualize(hypothesis(['A',0],'m','V7'),following=chord(['F',0],'M'),home=('C',0,'major'))
        self.assertIn('altered_mediant_or_secondary_mixture_competes',cx['warnings'])
        self.assertIsNone(cx['applied_function'])

    def test_perfect_fifth_not_tritone(self):
        h=hypothesis(['B',0],'M','V')
        self.assertEqual(h['chord']['root'],['F',1]);self.assertNotEqual(h['chord']['root'],['F',0])

    def test_independent_leading_seventh_paths(self):
        r=run(fixture([('F',1,4,0,1,'v'),('G',0,4,1,2,'v'),('C',0,5,0,1,'w'),('B',0,4,1,2,'w')]))
        self.assertEqual({t for p in r['critical_paths'] for t in p['geometry_tags']},{'leading_tone_to_target_root','seventh_descending_step'})
        self.assertTrue(all(p['destination_in_target_triad'] for p in r['critical_paths']))
        self.assertIsNone(r['function_confirmed'])

    def test_triads_supported_without_fabricated_seventh(self):
        r=run(fixture([('F',1,4,0,1,'v'),('G',0,4,1,2,'v')]),hypothesis(['G',0],'M','vii',1))
        self.assertEqual([p['role'] for p in r['critical_paths']],['leading_tone'])

    def test_enharmonic_root_not_leading_tone(self):
        r=run(fixture([('G',-1,4,0,1,'v'),('G',0,4,1,2,'v')]))
        self.assertEqual(r['critical_paths'],[])

    def test_internal_departure_and_octave(self):
        r=run(fixture([('F',1,4,0,1,'v'),('G',0,4,1,2,'v')]),end=2)
        self.assertFalse(r['critical_paths'][0]['at_or_after_supplied_end'])
        r=run(fixture([('F',1,4,0,1,'v'),('G',0,5,1,2,'v')]))
        self.assertEqual(r['critical_paths'][0]['geometry_tags'],[])

    def test_gap_overlap_and_other_voice_abstain(self):
        for rows,status in [([('F',1,4,0,1,'v'),('G',0,4,2,3,'v')],'no_touching_event'),
                            ([('F',1,4,0,1,'v'),('A',0,4,0,1,'v')],'ambiguous_voice'),
                            ([('F',1,4,0,1,'v'),('G',0,4,1,2,'w')],'no_touching_event')]:
            self.assertEqual(run(fixture(rows))['critical_paths'][0]['departure_status'],status)

    def test_full_tie_restrike_and_immutable(self):
        ir=fixture([('F',1,4,0,2,'v'),('F',1,4,2,3,'v'),('G',0,4,3,4,'v')]);n=copy.deepcopy(ir['note_events'][0]);n['note_id']='tie';n['display_staff_id']='s2';ir['note_events'].append(n);ir['sounding_events'][0]['source_note_ids'].append('tie');before=copy.deepcopy(ir)
        p=run(ir)['critical_paths'][0];self.assertEqual(len(p['same_pitch_chain']),2);self.assertEqual(p['event']['original_span']['end'],q(2));self.assertEqual(ir,before)

    def test_arpeggio_union_not_vertical(self):
        r=run(fixture([('D',0,4,0,1,'v'),('F',1,4,1,2,'v'),('A',0,4,2,3,'v'),('C',0,5,3,4,'v')]),end=4)
        self.assertFalse(r['missing_spellings']);self.assertFalse(any(s['complete_supplied_match'] for s in r['surface']['slices']))

    def test_vertical_extra_grace(self):
        rows=[('D',0,3,0,1,'b'),('F',1,4,0,1,'f'),('A',0,4,0,1,'a'),('C',0,5,0,1,'c')]
        self.assertTrue(run(fixture(rows))['surface']['slices'][0]['complete_supplied_match'])
        ir=fixture(rows+[('E',0,4,0,1,'g')]);self.assertEqual(run(ir)['extra_event_refs'],['e4'])
        ir['note_events'][4]['grace']={'is_grace':True};r=run(ir)
        self.assertEqual(r['excluded_grace_event_ids'],['e4']);self.assertTrue(r['surface']['slices'][0]['complete_supplied_match'])

    def test_invalid_ir_time_refs_duplicate(self):
        for kind in ('time','refs','duplicate','zero'):
            ir=fixture([('F',1,4,0,1,'v')])
            if kind=='time':ir['sounding_events'][0]['span']['end']=1.0
            if kind=='refs':ir['sounding_events'][0]['source_note_ids']=['missing']
            if kind=='duplicate':ir['sounding_events']*=2
            if kind=='zero':ir['sounding_events'][0]['span']['end']=q(0)
            with self.assertRaises(ValueError):run(ir)

    def test_rights_and_catalog(self):
        self.assertEqual(len(next(c for c in concepts() if c['concept_id']=='hvl.unit26')['reviewed_sections']),20)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'m.json';p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','rights':{'internal_research_use':False},'work_family_id':'w','score_sha256':'s','annotation_sha256':'a'}]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(p,Path(t)/'out')


if __name__=='__main__':unittest.main()
