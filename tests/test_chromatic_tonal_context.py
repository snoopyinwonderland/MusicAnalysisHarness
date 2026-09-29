import copy
import json
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction as F
from musicanote_harness.chromatic_tonal_context import (
    reinterpretations, compare_shapes, compare_following, observe_transition, common_tone_support)
from musicanote_harness.chromatic_tonal_context_audit import build
from musicanote_harness.augmented_sixth import hypothesis, pc
from musicanote_harness.seventh_context import chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_curriculum import concepts


def span(a, b): return {'start': q(a), 'end': q(b)}


def fixture(events):
    ir = {'note_events': [], 'sounding_events': []}
    for i, (pitch, start, end, voice) in enumerate(events):
        step, alter, octave = pitch
        ir['note_events'].append({'note_id': f'n{i}', 'part_id': 'p', 'voice_id': voice})
        ir['sounding_events'].append({'sounding_event_id': f'e{i}', 'attack_note_id': f'n{i}',
            'source_note_ids': [f'n{i}'], 'span': span(start, end),
            'pitch': {'step': step, 'alter': q(alter), 'octave': octave,
                      'midi_pitch': 12*(octave+1)+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter}})
    return ir


def observe(ir): return observe_transition(ir, span(0, 1), span(1, 2))
C = ('C', 0, 4)


class ChromaticTonalContextTest(unittest.TestCase):
    def test_four_diminished_targets(self):
        h = chord(['B', 0], 'o7')
        a = reinterpretations(h)
        self.assertEqual(len(a), 4)
        self.assertEqual({pc(x['target_tonic_spelling']) for x in a}, {0, 3, 6, 9})
        self.assertTrue(all(x['shape_comparison']['same_pitch_class_set'] for x in a))
        self.assertTrue(all(x['actual_modulation'] is None for x in a))

    def test_all_inversions_keep_sounding_bass(self):
        for root in (['B', 0], ['C', 1], ['E', -1]):
            for inv in range(4):
                h = chord(root, 'o7', inv)
                for a in reinterpretations(h):
                    self.assertEqual(pc(h['expected_bass']), pc(a['alternative_shape']['expected_bass']))

    def test_dominant_to_german(self):
        a = reinterpretations(chord(['G', 0], 'Mm7'))[0]
        self.assertEqual(a['target_tonic_spelling'], ['B', 0])
        self.assertIn(['E', 1], a['alternative_shape']['members'])
        self.assertFalse(a['shape_comparison']['same_spelling_set'])

    def test_dominant_inversion_to_german_role(self):
        a = reinterpretations(chord(['G', 0], 'Mm7', 3))[0]
        self.assertEqual(a['alternative_shape']['bass_role'], 'sharp4')
        self.assertEqual(a['alternative_shape']['expected_bass'], ['E', 1])

    def test_german_to_dominant(self):
        a = reinterpretations(hypothesis(['C', 0, 'minor'], 'Ger'))[0]
        self.assertEqual(a['target_tonic_spelling'], ['D', -1])
        self.assertEqual(a['alternative_shape']['root'], ['A', -1])

    def test_unsupported_families_no_false_equivalence(self):
        for family in ('It', 'Fr', 'Ger43'):
            self.assertEqual(reinterpretations(hypothesis(['C', 0, 'minor'], family)), [])
        for quality in ('M', 'm', '%7', 'MM7'):
            self.assertEqual(reinterpretations(chord(['C', 0], quality)), [])

    def test_unknown(self):
        self.assertEqual(reinterpretations(None), [])
        self.assertIsNone(compare_shapes(None, chord(['C',0], 'M')))
        r = compare_following(reinterpretations(chord(['B',0], 'o7')), None)
        self.assertTrue(all(x['following_shape_status'] == 'unknown' and not x['compatible_roles'] for x in r))

    def test_inconsistent_shape_rejected(self):
        h = chord(['G',0], 'Mm7');h['members'][3] = ['F',1]
        with self.assertRaises(ValueError): reinterpretations(h)

    def test_enharmonic_following_separate(self):
        a = reinterpretations(chord(['B',0], 'o7'))
        r = compare_following(a, chord(['A',0], 'm'))[-1]
        self.assertEqual(r['target_tonic_spelling'], ['B',-2])
        self.assertEqual(r['compatible_roles'], [])
        self.assertEqual(r['pitch_class_compatible_roles'], ['tonic_triad_shape'])

    def test_tonic64_not_established_tonic(self):
        a = reinterpretations(chord(['B',0], 'o7'))
        self.assertEqual(compare_following(a, chord(['C',0], 'M', 2))[0]['compatible_roles'], [])

    def test_dominant_destination_not_tonic_arrival(self):
        a = reinterpretations(chord(['B',0], 'o7'))
        r = compare_following(a, chord(['G',0], 'Mm7'))[0]
        self.assertEqual(r['compatible_roles'], ['dominant_shape'])
        self.assertIsNone(r['resolution_confirmed'])

    def test_held_and_reattack_not_confused(self):
        held = observe(fixture([(C,0,2,'v')]))
        attack = observe(fixture([(C,0,1,'v'),(C,1,2,'v')]))
        self.assertEqual(len(held['held_events']), 1)
        self.assertEqual(held['direct_voice_links'], [])
        self.assertEqual(attack['held_events'], [])
        self.assertEqual(attack['direct_voice_links'][0]['tags'], ['same_pitch_reattack'])

    def test_enharmonic_reattack(self):
        r = observe(fixture([(('E',-1,4),0,1,'v'),(('D',1,4),1,2,'v')]))
        self.assertEqual(r['direct_voice_links'][0]['tags'], ['enharmonic_reattack'])
        self.assertIsNone(r['functional_enharmonic_change'])
        self.assertIsNone(r['notational_enharmonic_only'])

    def test_chromatic_inflection(self):
        r = observe(fixture([(('F',0,4),0,1,'v'),(('F',1,4),1,2,'v')]))
        self.assertEqual(r['direct_voice_links'][0]['tags'], ['same_letter_chromatic_inflection'])

    def test_diatonic_semitone_not_inflection(self):
        r = observe(fixture([(('E',0,4),0,1,'v'),(('F',0,4),1,2,'v')]))
        self.assertEqual(r['direct_voice_links'][0]['tags'], [])

    def test_octave_not_same_pitch_hold(self):
        r = observe(fixture([(C,0,1,'v'),(('C',0,5),1,2,'v')]))
        self.assertEqual(r['direct_voice_links'][0]['tags'], [])

    def test_rest_gap_not_bridged(self):
        r = observe(fixture([(C,0,F(1,2),'v'),(C,1,2,'v')]))
        self.assertEqual(r['direct_voice_links'], [])

    def test_voice_changes_not_joined(self):
        self.assertEqual(observe(fixture([(C,0,1,'v1'),(C,1,2,'v2')]))['direct_voice_links'], [])

    def test_polyphonic_overlap_no_invented_line(self):
        r = observe(fixture([(C,0,1,'v'),(('E',0,4),0,1,'v'),(C,1,2,'v')]))
        self.assertEqual(r['direct_voice_links'], [])
        self.assertEqual(len(r['diagnostics']['ambiguous_voice_event_ids']), 2)

    def test_polyphonic_held_event_still_observable(self):
        r = observe(fixture([(C,0,2,'v'),(('E',0,4),0,1,'v'),(('F',0,4),1,2,'v')]))
        self.assertEqual([x['event_id'] for x in r['held_events']], ['e0'])
        self.assertEqual(r['direct_voice_links'], [])

    def test_grace_role_not_discarded(self):
        ir = fixture([(C,1,1,'v')]);ir['note_events'][0]['grace']={'is_grace':True}
        r = observe(ir)
        self.assertIsNone(r['diagnostics']['grace_events_pending_role'][0]['structural_role'])
        self.assertEqual(r['held_events'], [])

    def test_common_tone_needs_membership_both(self):
        ir = fixture([(C,0,2,'v'),(('D',0,4),0,2,'v2')])
        r = common_tone_support(observe(ir), chord(['C',0],'M'), chord(['A',-1],'M'))
        self.assertEqual(r['held_common_event_ids'], ['e0'])
        self.assertIsNone(r['common_tone_modulation'])

    def test_positive_adjacent_contract(self):
        for left, right in ((span(0,1),span(2,3)),(span(0,2),span(1,3)),(span(0,0),span(0,1))):
            with self.assertRaises(ValueError): observe_transition(fixture([]), left, right)

    def test_exact_rational_equivalence(self):
        ir = fixture([(C,0,F(1,3),'v'),(C,F(1,3),1,'v')])
        r = observe_transition(ir, span(0,F(1,3)), {'start':{'numerator':2,'denominator':6},'end':q(1)})
        self.assertEqual(len(r['direct_voice_links']), 1)

    def test_bad_references_and_duration(self):
        ir = fixture([(C,0,2,'v')]);ir['sounding_events'][0]['source_note_ids']=['missing']
        with self.assertRaises(ValueError): observe(ir)
        with self.assertRaises(ValueError): observe(fixture([(C,1,1,'v')]))

    def test_input_immutable(self):
        ir = fixture([(C,0,2,'v')]);before=copy.deepcopy(ir)
        observe(ir);self.assertEqual(ir,before)
        h = chord(['B',0],'o7');old=copy.deepcopy(h)
        reinterpretations(h);self.assertEqual(h,old)

    def test_curriculum_partial(self):
        r = next(x for x in concepts() if x['concept_id']=='hvl.unit33')
        self.assertEqual(r['reviewed_sections'], list(range(1,17)))
        self.assertEqual(r['rule_status'], 'candidate_not_production')

    def test_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'output_exists'): build('missing.json', d)

    def test_rights_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'manifest.json'
            p.write_text(json.dumps({'entries':[{'split':'train','collection_id':'mozart-sonatas',
                'package_path':'not-read','rights':{'internal_research_use':False},
                'work_family_id':'w','score_sha256':'hash','annotation_sha256':'annotation-hash'}]}))
            with self.assertRaisesRegex(ValueError,'research_not_permitted'): build(p,Path(d)/'output')


if __name__ == '__main__': unittest.main()
