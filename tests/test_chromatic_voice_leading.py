import copy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.chromatic_voice_leading import observe,pair_geometry
from musicanote_harness.chromatic_voice_leading_audit import build,context_annotations
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_curriculum import concepts


def span(a,b):return {'start':q(a),'end':q(b)}


def fixture(pitches,voice='v',start=0,length=1):
    ir={'note_events':[],'sounding_events':[]}
    for i,(s,a,o) in enumerate(pitches):
        nid=f'{voice}n{i}';sid=f'{voice}e{i}'
        ir['note_events'].append({'note_id':nid,'part_id':'p','voice_id':voice})
        ir['sounding_events'].append({'sounding_event_id':sid,'attack_note_id':nid,'source_note_ids':[nid],
            'span':span(start+i*length,start+(i+1)*length),
            'pitch':{'step':s,'alter':q(a),'octave':o,'midi_pitch':12*(o+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[s]+a}})
    return ir


def combine(*irs):return {k:[x for ir in irs for x in ir[k]] for k in ('note_events','sounding_events')}
def run(ir):return observe(ir,span(0,30))
C=[('C',0,4),('C',1,4),('D',0,4)]
LOW=[('E',0,3),('E',-1,3),('D',0,3),('D',-1,3),('C',0,3)]
HIGH=[('C',0,4),('C',1,4),('D',0,4),('D',1,4),('E',0,4)]


class ChromaticVoiceLeadingTest(unittest.TestCase):
    def test_ascending_semis_and_spelling(self):
        r=run(fixture(C));self.assertEqual(len(r['lines']),1);p=r['lines'][0]
        self.assertEqual(p['semitone_steps'],[1,1]);self.assertEqual([i['generic'] for i in p['intervals']],[1,2])
        self.assertTrue(p['contains_same_letter_inflection']);self.assertIsNone(p['sequence_confirmed'])

    def test_descending(self):self.assertEqual(run(fixture(C[::-1]))['lines'][0]['direction'],'descending')

    def test_two_notes_not_run(self):self.assertEqual(run(fixture(C[:2]))['lines'],[])

    def test_repeated_attack_breaks(self):self.assertEqual(run(fixture([C[0],C[1],C[1],C[2]]))['lines'],[])

    def test_direction_change_breaks(self):self.assertEqual(run(fixture([C[0],C[1],C[0]]))['lines'],[])

    def test_whole_tone_fragment_not_full_scale(self):
        r=run(fixture([('C',0,4),('D',0,4),('E',0,4)]))['lines'][0]
        self.assertEqual(r['pattern'],'equal_step_run');self.assertEqual(r['complete_octave_windows'],[])
        self.assertIsNone(r['scale_usage_confirmed'])

    def test_major_thirds_enharmonic_octave(self):
        r=run(fixture([('C',0,4),('E',0,4),('A',-1,4),('C',0,5)]))['lines'][0]
        self.assertEqual(r['semitone_steps'],[4,4,4]);self.assertEqual(r['complete_octave_windows'],[{'first_index':0,'last_index':3,'spelled_octave':True}])
        self.assertEqual(r['intervals'][1]['name'],'d4')

    def test_equal_sound_not_spelled_octave(self):
        r=run(fixture([('C',0,4),('E',0,4),('G',1,4),('B',1,4)]))['lines'][0]
        self.assertFalse(r['complete_octave_windows'][0]['spelled_octave'])

    def test_minor_thirds_full_octave(self):
        r=run(fixture([('C',0,4),('E',-1,4),('G',-1,4),('A',0,4),('C',0,5)]))['lines'][0]
        self.assertEqual(r['complete_octave_windows'][0]['last_index'],4)

    def test_tritone_full_octave(self):
        r=run(fixture([('C',0,4),('F',1,4),('C',0,5)]))['lines'][0]
        self.assertEqual(len(r['complete_octave_windows']),1)

    def test_alternation_fragment(self):
        r=run(fixture([('C',0,4),('D',0,4),('E',-1,4),('F',0,4)]))['lines'][0]
        self.assertEqual(r['pattern'],'alternating_one_two_run');self.assertEqual(r['complete_octave_windows'],[])

    def test_octatonic_ordered_full_octave(self):
        r=run(fixture([('C',0,4),('D',0,4),('E',-1,4),('F',0,4),('G',-1,4),('A',-1,4),('A',0,4),('B',0,4),('C',0,5)]))['lines'][0]
        self.assertEqual(r['semitone_steps'],[2,1,2,1,2,1,2,1]);self.assertEqual(len(r['complete_octave_windows']),1)

    def test_reordered_collection_not_octatonic_line(self):
        r=run(fixture([('C',0,4),('E',-1,4),('D',0,4),('F',0,4)]))
        self.assertFalse(any(x['pattern']=='alternating_one_two_run' for x in r['lines']))

    def test_gap_blocks(self):
        ir=fixture(C);ir['sounding_events'][1]['span']['end']=q(F(3,2))
        self.assertEqual(run(ir)['lines'],[]);self.assertEqual(run(ir)['diagnostics']['block_breaks']['gap'],1)

    def test_polyphonic_voice_no_topline_invention(self):
        ir=fixture(C);extra=copy.deepcopy(ir['sounding_events'][1]);extra['sounding_event_id']='extra';extra['pitch']['octave']=5;extra['pitch']['midi_pitch']+=12
        ir['sounding_events'].append(extra)
        r=run(ir);self.assertEqual(r['lines'],[]);self.assertEqual(len(r['diagnostics']['ambiguous_voice_event_ids']),2)

    def test_long_overlap_marks_all_enclosed(self):
        ir=fixture(C);ir['sounding_events'][0]['span']['end']=q(4)
        r=run(ir);self.assertEqual(len(r['diagnostics']['ambiguous_voice_event_ids']),3);self.assertEqual(r['lines'],[])

    def test_part_identity_not_merged(self):
        a=fixture(C[:2]);b=fixture(C[2:],'w',start=2)
        b['note_events'][0].update(part_id='other',voice_id='v')
        self.assertEqual(run(combine(a,b))['lines'],[])

    def test_missing_voice_pending(self):
        ir=fixture(C);ir['note_events'][1]['voice_id']=None
        r=run(ir);self.assertEqual(r['diagnostics']['missing_voice_event_ids'],['ve1']);self.assertEqual(r['lines'],[])

    def test_cross_staff_same_voice_preserved(self):
        ir=fixture(C)
        for i,n in enumerate(ir['note_events']):n['display_staff_id']=f's{i%2}'
        self.assertEqual(len(run(ir)['lines']),1)

    def test_tied_sound_one_event_full_duration(self):
        ir=fixture(C);ir['note_events'].append({'note_id':'tie','part_id':'p','voice_id':'v'})
        ir['sounding_events'][1]['source_note_ids'].append('tie')
        self.assertEqual(run(ir)['lines'][0]['events'][1]['source_note_ids'],['vn1','tie'])

    def test_grace_not_automatically_ornamental(self):
        ir=fixture(C);ir['note_events'][1]['grace']={'is_grace':True}
        ir['sounding_events'][1]['span']['end']=q(1)
        r=run(ir);self.assertEqual(r['lines'],[])
        self.assertIsNone(r['diagnostics']['grace_events_pending_role'][0]['structural_role'])

    def test_parallel_actual_voices(self):
        r=run(combine(fixture(C,'lo'),fixture([('E',0,4),('F',0,4),('F',1,4)],'hi')))
        self.assertEqual(r['pairs'][0]['pattern'],'parallel_chromatic_motion')
        self.assertFalse(r['pairs'][0]['stable_spelled_interval'])
        self.assertIsNone(r['pairs'][0]['harmonic_prolongation'])

    def test_six_ten_exchange(self):
        r=run(combine(fixture(LOW,'lo'),fixture(HIGH,'hi')))
        p=r['pairs'][0];self.assertEqual(p['pattern'],'six_ten_exchange_geometry')
        self.assertEqual([x['generic'] for x in p['vertical_intervals']],[6,6,8,8,10])
        self.assertEqual([x['semitones'] for x in p['vertical_intervals']],[8,10,12,14,16])
        self.assertTrue(p['endpoint_exchange_spelling']);self.assertIsNone(p['cadence'])

    def test_reverse_exchange(self):
        p=run(combine(fixture(LOW[::-1],'lo'),fixture(HIGH[::-1],'hi')))['pairs'][0]
        self.assertEqual((p['vertical_intervals'][0]['generic'],p['vertical_intervals'][-1]['generic']),(10,6))

    def test_staggered_not_joint(self):
        self.assertEqual(run(combine(fixture(LOW,'lo'),fixture(HIGH,'hi',start=F(1,2))))['pairs'],[])

    def test_equivalent_rational_coordinates_pair(self):
        a=run(fixture(LOW,'lo'))['lines'][0];b=run(fixture(HIGH,'hi'))['lines'][0]
        b['events'][0]['span']['end']={'numerator':2,'denominator':2}
        self.assertEqual(pair_geometry(a,b)['pattern'],'six_ten_exchange_geometry')

    def test_unmapped_annotation_does_not_block_geometry_audit(self):
        rows=[{'annotation_id':'missing'},{'annotation_id':'null','target':None},
              {'annotation_id':'empty','target':{}},{'annotation_id':'mapped','target':{'span':span(0,1)}}]
        result=context_annotations(rows,set(),span(0,1))
        self.assertEqual(len(result),1);self.assertFalse(result[0]['alignment_verified'])
        self.assertEqual(context_annotations(rows,{'mapped'},span(1,2)),[])

    def test_contrary_not_always_exchange(self):
        self.assertEqual(run(combine(fixture(C,'lo'),fixture([('G',0,5),('G',-1,5),('F',0,5)],'hi')))['pairs'],[])

    def test_source_free_and_no_mutation(self):
        ir=fixture(C);old=copy.deepcopy(ir);r=run(ir)
        self.assertEqual(ir,old);self.assertFalse(r['source_annotations_used_for_detection']);self.assertFalse(r['production_enabled'])

    def test_invalid_inputs(self):
        for k in ('duplicate','duplicate_note','ref','pitch','float','negative','zero'):
            ir=fixture(C)
            if k=='duplicate':ir['sounding_events'].append(ir['sounding_events'][0])
            if k=='duplicate_note':ir['note_events'].append(ir['note_events'][0])
            if k=='ref':ir['sounding_events'][0]['source_note_ids']=[]
            if k=='pitch':ir['sounding_events'][0]['pitch']['midi_pitch']=1
            if k=='float':ir['sounding_events'][0]['span']['end']=0.5
            if k=='negative':ir['sounding_events'][0]['span']['start']=q(-1)
            if k=='zero':ir['sounding_events'][0]['span']['end']=q(0)
            with self.assertRaises(ValueError):run(ir)
        with self.assertRaises(ValueError):observe(fixture(C),span(1,1))

    def test_rights_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.json';out=Path(d)/'out'
            p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas','package_path':'x','work_family_id':'w','score_sha256':'s','annotation_sha256':'a','rights':{'internal_research_use':False}}]}))
            with self.assertRaises(ValueError):build(p,out)
            self.assertFalse(out.exists())

    def test_catalog(self):
        r=next(c for c in concepts() if c['concept_id']=='hvl.unit32');self.assertEqual(r['reviewed_sections'],list(range(1,20)))


if __name__=='__main__':unittest.main()
