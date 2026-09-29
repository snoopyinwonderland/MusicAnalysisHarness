from copy import deepcopy
from fractions import Fraction as F
import unittest
from music21 import pitch
from test_harmony_joint import fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_reading_voice_context import voice_links,relation,spelled_height,compare
from musicanote_harness.harmony_surface import TEMPLATES
from musicanote_harness.harmony_distributed_readings import observe


def score(specs):
    ir=fixture([(pitch.Pitch(p).midi,a,b,v) for p,a,b,v in specs])
    for s,n,(p,a,b,v) in zip(ir['sounding_events'],ir['note_events'],specs):
        obj=pitch.Pitch(p);s['source_note_ids']=[n['note_id']]
        s['pitch'].update(step=obj.step,octave=obj.octave,alter=q(int(obj.accidental.alter) if obj.accidental else 0),spelling=obj.nameWithOctave)
        n['part_id']='part1'
    return ir


def chord(root,quality):return {'root':root,'label':str(root)+':'+quality,'pcs':sorted((root+d)%12 for d in dict(TEMPLATES)[quality])}
def links(ir):return voice_links(ir,{'start':q(0),'end':q(8)})


def external_fixture():
    pitches=['C3','E3','G3','C3','E3','G3','B-3','E3','F3','A3','C4','F3']
    ir=score([(p,F(i,2),F(i+1,2),'v') for i,p in enumerate(pitches)]+
             [('B-4',F(7,2),4,'upper'),('A4',4,6,'upper')])
    ir['measures'][0]['actual_duration_quarter']=q(6)
    c=next(c for c in observe(ir)['alternatives'] if c['span']=={'start':q(0),'end':q(4)} and c['boundary']==q(2))
    return ir,c


class ReadingVoiceTests(unittest.TestCase):
    def test_leading_tone_spelled_step(self):
        ir=score([('B3',0,1,'v'),('C4',1,2,'v')]);p=links(ir)['links'][0]
        self.assertIn('conditional_dominant_family_leading_tone_up',relation(p,chord(7,'dominant7'),chord(0,'major')))

    def test_seventh_down_step(self):
        ir=score([('F4',0,1,'v'),('E4',1,2,'v')]);p=links(ir)['links'][0]
        self.assertIn('conditional_seventh_down_step_to_member',relation(p,chord(7,'dominant7'),chord(0,'major')))

    def test_diminished_fifth_down(self):
        p=links(score([('F4',0,1,'v'),('E4',1,2,'v')]))['links'][0]
        self.assertIn('conditional_diminished_fifth_down_step_to_member',relation(p,chord(11,'diminished'),chord(0,'major')))

    def test_enharmonic_same_letter_not_spelled_resolution(self):
        p=links(score([('C-4',0,1,'v'),('C4',1,2,'v')]))['links'][0]
        self.assertEqual(relation(p,chord(7,'dominant7'),chord(0,'major')),[])

    def test_wrong_register_not_step_resolution(self):
        p=links(score([('B3',0,1,'v'),('C5',1,2,'v')]))['links'][0]
        self.assertEqual(relation(p,chord(7,'dominant7'),chord(0,'major')),[])

    def test_chord_voice_never_guesses_closest_notes(self):
        ir=score([('B3',0,1,'v'),('F4',0,1,'v'),('C4',1,2,'v'),('E4',1,2,'v')])
        result=links(ir);self.assertEqual(result['links'],[])
        self.assertEqual(result['abstentions']['polyphonic_source_voice'],4)

    def test_explicit_separate_voices_allow_parallel_links(self):
        ir=score([('B3',0,1,'v1'),('F4',0,1,'v2'),('C4',1,2,'v1'),('E4',1,2,'v2')])
        self.assertEqual(len(links(ir)['links']),2)

    def test_gap_or_overlap_abstains(self):
        for start in (F(1,2),F(3,2)):
            self.assertEqual(links(score([('B3',0,1,'v'),('C4',start,2,'v')]))['links'],[])

    def test_tied_sounding_event_not_reattack(self):
        ir=score([('B3',0,2,'v'),('C4',2,3,'v')])
        ir['note_events'].append({**ir['note_events'][0],'note_id':'continuation'})
        ir['sounding_events'][0]['source_note_ids'].append('continuation')
        result=links(ir);self.assertEqual(len(result['links']),1)
        ir['note_events'][-1]['voice_id']='other'
        self.assertEqual(links(ir)['links'],[])

    def test_cross_staff_same_voice_allowed(self):
        ir=score([('B3',0,1,'v'),('C4',1,2,'v')]);ir['note_events'][0]['display_staff_id']='s1';ir['note_events'][1]['display_staff_id']='s2'
        self.assertEqual(len(links(ir)['links']),1)

    def test_missing_spelling_keeps_observation_not_resolution(self):
        ir=score([('B3',0,1,'v'),('C4',1,2,'v')]);ir['sounding_events'][0]['pitch'].pop('step')
        p=links(ir)['links'][0];self.assertIsNone(p['diatonic_steps'])
        self.assertEqual(relation(p,chord(7,'dominant7'),chord(0,'major')),[])

    def test_unsupported_pitch_and_inconsistent_spelling(self):
        self.assertIsNone(spelled_height({}))
        self.assertIsNone(spelled_height({'step':'C','octave':4,'alter':q(F(1,2)),'midi_pitch':60.5}))
        self.assertIsNone(spelled_height({'step':'C','octave':4,'alter':q(0),'midi_pitch':61}))

    def test_inputs_immutable_and_annotation_ignored(self):
        ir=score([(p,F(i,2),F(i+1,2),'v') for i,p in enumerate(['C3','E3','G3','C3','E3','G3','B3','E3'])])
        c=observe(ir)['alternatives'][0];old=deepcopy((ir,c));result=compare(ir,c)
        self.assertEqual((ir,c),old);self.assertFalse(result['reranking_performed'])
        self.assertEqual(result,compare({**ir,'annotations':['V'],'phrases':[1]},c))

    def test_same_pitch_reattack_not_tie(self):
        p=links(score([('C4',0,1,'v'),('C4',1,2,'v')]))['links'][0]
        self.assertEqual(relation(p,chord(0,'major'),chord(0,'major')),['same_spelled_pitch_reattack'])

    def test_external_resolution_uses_blind_following_shape(self):
        ir,c=external_fixture();out=compare(ir,c)
        ext=next(e for e in out['external_shape_candidates'] if e['candidate']['root']==5)
        self.assertEqual(ext['span'],{'start':q(4),'end':q(6)})
        self.assertEqual(ext['all_members_observed_by'],q(5))
        merged=next(r for r in out['readings'] if r['reading_type']=='merged_seventh')
        tags=[tag for e in merged['external_comparisons'] for p in e['relations'] for tag in p['relations']]
        self.assertIn('conditional_seventh_down_step_to_member',tags)
        self.assertIn('conditional_dominant_family_leading_tone_up',tags)
        self.assertIsNone(merged['selected']);self.assertFalse(out['function_confirmed'])
        old=deepcopy((ir,c));compare(ir,c);self.assertEqual((ir,c),old)
        self.assertEqual(out,compare({**ir,'annotations':['wrong answer'],'phrases':[{'end':4}]},c))

    def test_external_extra_pitch_not_deleted_as_nct(self):
        ir,c=external_fixture()
        extra=score([('F#2',4,6,'pedal')])
        extra['note_events'][0]['note_id']='pedal_note'
        extra['sounding_events'][0].update(sounding_event_id='pedal_sound',attack_note_id='pedal_note',source_note_ids=['pedal_note'])
        ir['note_events']+=extra['note_events'];ir['sounding_events']+=extra['sounding_events']
        self.assertFalse(any(e['side']=='following' for e in compare(ir,c)['external_shape_candidates']))

    def test_external_different_meter_unit_abstains(self):
        ir,c=external_fixture()
        ir['measures'].append({'global_start_quarter':q(4),'actual_duration_quarter':q(2),'time_signature':{'beat_type':8}})
        self.assertFalse(any(e['side']=='following' for e in compare(ir,c)['external_shape_candidates']))

    def test_missing_part_identity_abstains(self):
        ir=score([('B3',0,1,'v'),('C4',1,2,'v')])
        ir['note_events'][0].pop('part_id')
        self.assertEqual(links(ir)['links'],[])


if __name__=='__main__':unittest.main()
