import copy
import json
from pathlib import Path
import tempfile
import unittest
from musicanote_harness.formal_ir import q
from musicanote_harness.predominant_seventh import assess
from musicanote_harness.predominant_seventh_audit import build, source_family
from musicanote_harness.harmony_curriculum import concepts


def span(a, b):
    return {'start': q(a), 'end': q(b)}


def ir_of(rows):
    ir = {'note_events': [], 'sounding_events': []}
    for i, (pitch, a, b, voice) in enumerate(rows):
        step, alter, octave = pitch
        nid, sid = 'n'+str(i), 's'+str(i)
        ir['note_events'].append({'note_id': nid, 'part_id': 'p', 'voice_id': voice})
        ir['sounding_events'].append({'sounding_event_id': sid, 'attack_note_id': nid,
            'source_note_ids': [nid], 'span': span(a, b),
            'pitch': {'step': step, 'alter': q(alter), 'octave': octave,
                      'midi_pitch': 12*(octave+1)+dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)[step]+alter}})
    return ir


C, B, D, E, Eb = ('C',0,4), ('B',0,3), ('D',0,4), ('E',0,4), ('E',-1,4)


class MotionTest(unittest.TestCase):
    def run_rows(self, rows, target=(1,2), context=(0,5), family='supertonic', tonic='C', alter=0, mode='major'):
        return assess(ir_of(rows), span(*target), span(*context), family, tonic, alter, mode)

    def test_tied_preparation_downward_and_immutability(self):
        ir = ir_of([(C,0,2,'v'), (B,2,3,'v')])
        before = copy.deepcopy(ir)
        r = assess(ir, span(1,2), span(0,4), 'supertonic', 'C')['records'][0]
        self.assertEqual(r['entry']['status'], 'held_across_target_start')
        self.assertEqual(r['departure']['status'], 'descending_step')
        self.assertIsNone(r['resolution_verified'])
        self.assertEqual(r['original_span'], span(0,2))
        self.assertEqual(ir, before)

    def test_repeated_entry_not_verified_preparation(self):
        r = self.run_rows([(C,0,1,'v'),(C,1,2,'v'),(B,2,3,'v')])['records'][0]
        self.assertEqual(r['entry']['status'], 'repeated_same_pitch')
        self.assertIsNone(r['preparation_verified'])

    def test_step_entry_and_inside_target_not_final_resolution(self):
        r = self.run_rows([(D,0,1,'v'),(C,1,2,'v'),(B,2,3,'v')], target=(1,3))['records'][0]
        self.assertEqual(r['entry']['status'], 'descending_step')
        self.assertEqual(r['departure_position'], 'inside_target')

    def test_delayed_departure_not_failed_at_harmonic_boundary(self):
        r = self.run_rows([(C,0,3,'v'),(B,3,4,'v')])['records'][0]
        self.assertEqual(r['departure_position'], 'after_target_end')
        self.assertEqual(r['departure']['status'], 'descending_step')

    def test_gap_not_skipped_to_desired_resolution(self):
        r = self.run_rows([(C,1,2,'v'),(B,3,4,'v')])['records'][0]
        self.assertEqual(r['departure']['status'], 'no_touching_event')

    def test_context_censor_and_repeated_departure(self):
        r = self.run_rows([(C,1,2,'v'),(C,2,3,'v'),(B,3,4,'v')])['records'][0]
        self.assertEqual(r['departure']['status'], 'repeated_same_pitch')
        r = self.run_rows([(C,1,5,'v'),(B,5,6,'v')])['records'][0]
        self.assertEqual(r['departure']['status'], 'context_censored')

    def test_polyphonic_voice_and_missing_voice_abstain(self):
        r = self.run_rows([(C,1,2,'v'),(E,1,2,'v'),(B,2,3,'v')])['records'][0]
        self.assertEqual(r['departure']['status'], 'ambiguous_voice')
        r = self.run_rows([(C,1,2,None)])['records'][0]
        self.assertEqual(r['entry']['status'], 'missing_or_inconsistent_voice')

    def test_destination_chord_is_not_pitch_sorted(self):
        r = self.run_rows([(C,1,2,'v'),(B,2,3,'v'),(E,2,3,'v')])['records'][0]
        self.assertEqual(r['departure']['status'], 'ambiguous_voice')

    def test_octave_and_enharmonic_false_resolution(self):
        for p in [('B',0,4),('A',2,3)]:
            r = self.run_rows([(C,1,2,'v'),(p,2,3,'v')])['records'][0]
            self.assertEqual(r['departure']['status'], 'other_motion')
        self.assertEqual(self.run_rows([(('B',1,3),1,2,'v')])['records'], [])

    def test_minor_subdominant_and_transposition(self):
        r = self.run_rows([(Eb,1,2,'v'),(D,2,3,'v')], family='subdominant', mode='minor')['records'][0]
        self.assertEqual(r['departure']['status'], 'descending_step')
        self.assertEqual(self.run_rows([(E,1,2,'v')], family='subdominant', mode='minor')['records'], [])
        r = self.run_rows([(('F',1,4),1,2,'v'),(('E',1,4),2,3,'v')], tonic='F', alter=1)['records'][0]
        self.assertEqual(r['departure']['status'], 'descending_step')

    def test_parts_do_not_share_voice_identity(self):
        ir = ir_of([(C,1,2,'v'),(B,2,3,'v')])
        ir['note_events'][1]['part_id'] = 'p2'
        r = assess(ir,span(1,2),span(0,4),'supertonic','C')['records'][0]
        self.assertEqual(r['departure']['status'], 'no_touching_event')

    def test_validation_and_half_open_bounds(self):
        self.assertEqual(self.run_rows([(C,0,1,'v'),(C,2,3,'v')])['records'], [])
        with self.assertRaisesRegex(ValueError,'invalid_context'):
            self.run_rows([(C,1,2,'v')], context=(2,3))
        ir = ir_of([(C,1,2,'v')]); ir['sounding_events'][0]['pitch']['midi_pitch']=61
        with self.assertRaisesRegex(ValueError,'pitch_spelling'):
            assess(ir,span(1,2),span(0,3),'supertonic','C')
        ir = ir_of([(C,1,2,'v')]); ir['sounding_events'][0]['source_note_ids']=['missing']
        with self.assertRaisesRegex(ValueError,'broken_source'):
            assess(ir,span(1,2),span(0,3),'supertonic','C')

    def test_fraction_contract_and_cross_staff(self):
        ir = ir_of([(C,1,2,'v'),(B,2,3,'v')])
        ir['note_events'][0]['staff_id'] = 'upper'
        ir['note_events'][1]['staff_id'] = 'lower'
        r=assess(ir,span(1,2),span(0,4),'supertonic','C')['records'][0]
        self.assertEqual(r['departure']['status'],'descending_step')
        with self.assertRaisesRegex(ValueError,'rational_time_required'):
            assess(ir,{'start':1.0,'end':2.0},span(0,4),'supertonic','C')
        ir['sounding_events'][0]['span']['start']={'numerator':1.0,'denominator':1}
        with self.assertRaisesRegex(ValueError,'rational_time_required'):
            assess(ir,span(1,2),span(0,4),'supertonic','C')


class AuditTest(unittest.TestCase):
    def test_annotation_adapter(self):
        def a(n='ii', f='', ct='mm7', **kw):
            return {'raw_fields': dict(numeral=n, form=f, chord_type=ct, figbass='65', **kw)}
        self.assertEqual(source_family(a()), 'supertonic')
        self.assertEqual(source_family(a(f='%',ct='%7')), 'supertonic')
        self.assertEqual(source_family(a(n='IV',f='M',ct='MM7')), 'subdominant')
        self.assertEqual(source_family(a(n='iv')), 'subdominant')
        self.assertIsNone(source_family(a(relativeroot='V')))
        self.assertIsNone(source_family(a(changes='#3')))
        self.assertIsNone(source_family(a(n='IV')))

    def test_rights_split_overwrite_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            with self.assertRaisesRegex(ValueError,'output_exists'): build('not_read',p)
            e={'split':'holdout','work_family_id':'w','score_sha256':'s','annotation_sha256':'a',
               'collection_id':'mozart-sonatas','package_path':'missing','rights':{'internal_research_use':False}}
            manifest=p/'m.json'; manifest.write_text(json.dumps({'entries':[e]}))
            self.assertEqual(build(manifest,p/'out')['summary']['case_count'],0)
            e['split']='train'; manifest.write_text(json.dumps({'entries':[e]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'): build(manifest,p/'other')

    def test_curriculum(self):
        r = next(r for r in concepts() if r['concept_id']=='hvl.unit13')
        self.assertEqual(r['reviewed_sections'], list(range(1,14)))
        self.assertEqual(r['rule_status'], 'candidate_not_production')


if __name__ == '__main__':
    unittest.main()
