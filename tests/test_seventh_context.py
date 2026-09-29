import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.seventh_context import chord, source_chord, succession, observe
from musicanote_harness.seventh_context_audit import build
from musicanote_harness.harmony_curriculum import concepts


def fixture(rows):
    ir={'note_events':[],'sounding_events':[]}
    for i,(step,alter,octave,start,end,voice) in enumerate(rows):
        ir['note_events'].append({'note_id':f'n{i}','part_id':'p','voice_id':voice,'display_staff_id':'s'})
        ir['sounding_events'].append({'sounding_event_id':f'e{i}','attack_note_id':f'n{i}','source_note_ids':[f'n{i}'],
            'pitch':{'step':step,'alter':q(alter),'octave':octave,'midi_pitch':12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter},
            'span':{'start':q(start),'end':q(end)}})
    return ir


def run(ir,h=None,end=1,nxt=None):
    return observe(ir,{'start':q(0),'end':q(end)},{'start':q(0),'end':q(4)},h or chord(['D',0],'mm7',1),nxt)


def ann(**kw):
    return {'raw_fields':{'localkey_is_minor':'0','numeral':'ii','form':'','chord_type':'mm7','figbass':'65',**kw}}


class SeventhContextTest(unittest.TestCase):
    def test_spelling_inversion(self):
        h=chord(['D',0],'mm7',1)
        self.assertEqual(h['members'],[['D',0],['F',0],['A',0],['C',0]])
        self.assertEqual(h['expected_bass'],['F',0])

    def test_double_accidental(self):
        self.assertEqual(chord(['B',-1],'o7')['members'][-1],['A',-2])

    def test_invalid_hypothesis(self):
        for args in [(['C',False],'M',0),(['C',0],'bad',0),(['C',0],'M',3),(['C',0],'mm7',True)]:
            with self.assertRaises(ValueError):chord(*args)

    def test_source_minor_convention(self):
        h=source_chord(ann(localkey_is_minor='1',numeral='#vii',form='o',chord_type='o7',figbass='43'),'C',mode='minor')
        self.assertEqual(h['root'],['B',0])

    def test_source_major_seventh_form(self):
        h=source_chord(ann(numeral='IV',form='M',chord_type='MM7',figbass='7'),'C')
        self.assertEqual(h['members'][-1],['E',0])
        self.assertIsNone(source_chord(ann(numeral='IV',form='',chord_type='MM7'),'C'))

    def test_adapter_does_not_erase_modifiers(self):
        for k in ('changes','added_tones','relativeroot','pedal','special'):
            self.assertIsNone(source_chord(ann(**{k:'x'}),'C'))
        self.assertIsNone(source_chord(ann(numeral='II'),'C'))
        self.assertIsNone(source_chord(ann(figbass='9'),'C'))

    def test_interlocking_fifths(self):
        hs=[chord([s,0],qual) for s,qual in [('A','mm7'),('D','mm7'),('G','Mm7'),('C','MM7')]]
        r=succession(hs)
        self.assertEqual(r['pattern_candidates'],['descending_fifth_root_chain'])
        self.assertTrue(all(x['third_can_be_next_seventh'] for x in r['relations']))
        self.assertIsNone(r['sequence_confirmed'])

    def test_thirds_and_two_chords_not_sequence(self):
        hs=[chord([s,0],qual) for s,qual in [('C','MM7'),('A','mm7'),('F','MM7'),('D','mm7')]]
        self.assertEqual(succession(hs)['pattern_candidates'],['descending_third_root_chain'])
        self.assertEqual(succession(hs[:2])['pattern_candidates'],[])

    def test_five_six_variant(self):
        hs=[chord(['C',0],'M'),chord(['A',0],'mm7',1),chord(['D',0],'m'),chord(['B',0],'%7',1)]
        self.assertEqual(succession(hs)['pattern_candidates'],['ascending_five_six_variant'])

    def test_apparent_alternative_with_upward_root(self):
        r=run(fixture([('D',0,4,0,1,'v'),('E',0,4,1,2,'v')]))
        self.assertEqual(r['apparent_alternatives'][0]['role'],'triad_with_added_sixth')
        self.assertEqual(r['apparent_alternatives'][0]['upward_motion_event_refs'],['e0'])
        self.assertIsNone(r['apparent_chord_confirmed'])
        self.assertTrue(r['missing_spellings'])

    def test_added_fourth_and_dominant_not_consonant_triad(self):
        ir=fixture([('D',0,4,0,1,'v')])
        self.assertEqual(run(ir,chord(['D',0],'mm7',2))['apparent_alternatives'][0]['role'],'first_inversion_triad_with_added_fourth')
        self.assertEqual(run(ir,chord(['G',0],'Mm7',1))['apparent_alternatives'],[])

    def test_seventh_step_arrival_not_confirmed(self):
        r=run(fixture([('C',0,5,0,1,'v'),('B',0,4,1,2,'v')]),nxt=chord(['G',0],'M'))['paths'][0]
        self.assertIn('seventh_down_step',r['geometry_tags']);self.assertTrue(r['destination_in_following_members'])
        self.assertTrue(r['at_or_after_target_end']);self.assertIsNone(r['resolution_confirmed'])

    def test_internal_movement_not_exit(self):
        r=run(fixture([('C',0,5,0,1,'v'),('B',0,4,1,2,'v')]),end=2)['paths'][0]
        self.assertFalse(r['at_or_after_target_end'])

    def test_handoff_separate_from_resolution(self):
        r=run(fixture([('C',0,5,0,1,'v'),('C',0,5,1,2,'w'),('B',0,4,1,2,'x')]))['paths'][0]
        self.assertEqual({x['kind'] for x in r['cross_voice_coincidences']},{'same_pitch_seventh_handoff','same_register_descending_step'})
        self.assertTrue(all(not x['verified'] for x in r['cross_voice_coincidences']))
        self.assertEqual(r['departure_status'],'no_touching_event')

    def test_octave_displacement_not_direct_step(self):
        r=run(fixture([('C',0,5,0,1,'v'),('B',0,3,1,2,'w')]))['paths'][0]
        self.assertEqual(r['cross_voice_coincidences'],[])

    def test_gap_and_overlap_abstain(self):
        for rows,status in [([('C',0,5,0,1,'v'),('B',0,4,2,3,'v')],'no_touching_event'),
                            ([('C',0,5,0,1,'v'),('E',0,4,0,1,'v'),('B',0,4,1,2,'v')],'ambiguous_voice')]:
            self.assertEqual(run(fixture(rows))['paths'][0]['departure_status'],status)

    def test_tie_restrike_and_full_span(self):
        ir=fixture([('C',0,5,0,2,'v'),('C',0,5,2,3,'v'),('B',0,4,3,4,'v')]);n=copy.deepcopy(ir['note_events'][0]);n['note_id']='tie';ir['note_events'].append(n);ir['sounding_events'][0]['source_note_ids'].append('tie')
        r=run(ir)['paths'][0]
        self.assertEqual(len(r['chain']),2);self.assertEqual(r['event']['original_span']['end'],q(2))
        self.assertEqual(r['event']['source_note_ids'],['n0','tie'])

    def test_halfopen_boundary_and_grace(self):
        ir=fixture([('C',0,5,0,1,'v'),('D',0,5,1,2,'v'),('D',0,4,0,0,'v')]);ir['note_events'][2]['grace']={'is_grace':True}
        r=run(ir);self.assertEqual(len(r['events']),1);self.assertEqual(r['excluded_grace_event_ids'],['e2'])

    def test_union_not_vertical(self):
        ir=fixture([(s,0,4,i,i+1,'v') for i,s in enumerate('DFAC')]);r=run(ir,end=4)
        self.assertFalse(r['missing_spellings']);self.assertFalse(any(c['complete_supplied_match'] for c in r['vertical_cells']))

    def test_exact_vertical_and_extra_note(self):
        rows=[('F',0,3,0,1,'bass'),('A',0,4,0,1,'a'),('C',0,5,0,1,'c'),('D',0,5,0,1,'d')]
        self.assertTrue(run(fixture(rows))['vertical_cells'][0]['complete_supplied_match'])
        r=run(fixture(rows+[('E',0,5,0,1,'e')]))
        self.assertFalse(r['vertical_cells'][0]['complete_supplied_match']);self.assertEqual(r['extra_event_refs'],['e4'])

    def test_immutability_and_cross_staff(self):
        ir=fixture([('C',0,5,0,1,'v'),('B',0,4,1,2,'v')]);ir['note_events'][1]['display_staff_id']='s2';before=copy.deepcopy(ir)
        self.assertIn('seventh_down_step',run(ir)['paths'][0]['geometry_tags']);self.assertEqual(ir,before)

    def test_invalid_ir(self):
        original=fixture([('C',0,5,0,1,'v')])
        for field,value in [('source_note_ids',['missing']),('span',{'start':q(1),'end':q(0)})]:
            ir=copy.deepcopy(original);ir['sounding_events'][0][field]=value
            with self.assertRaises(ValueError):run(ir)
        ir=copy.deepcopy(original);ir['sounding_events']*=2
        with self.assertRaises(ValueError):run(ir)
        with self.assertRaises(ValueError):run(original,end=5)

    def test_rights_and_catalog(self):
        c=next(x for x in concepts() if x['concept_id']=='hvl.unit25');self.assertEqual(len(c['reviewed_sections']),16)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'manifest.json';p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','rights':{'internal_research_use':False},'work_family_id':'w','score_sha256':'s','annotation_sha256':'a'}]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'):build(p,Path(t)/'out')


if __name__=='__main__':unittest.main()
