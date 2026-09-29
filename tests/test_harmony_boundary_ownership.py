from copy import deepcopy
from fractions import Fraction as F
import unittest
from music21 import pitch
from test_harmony_joint import fixture as base_ir
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_multiscale_shadow import analyze, provider
from musicanote_harness.harmony_joint import prepare
from musicanote_harness.harmony_arpeggio_benchmark import fixture
from musicanote_harness.harmony_boundary_ownership import review
from musicanote_harness.harmony_candidate_explanation import explain_path


def score(texture='ascending', change=True, transpose=0, scale=F(1)):
    case = fixture('triad', texture, change, transpose, scale)
    ir = base_ir([(int(pitch.Pitch(e['pitch']).midi), f(e['start']), f(e['start'])+f(e['duration']), e['voice'])
                  for e in case['events']])
    ir['measures'][0].update(actual_duration_quarter=q(4*scale), time_signature={'beat_type': case['beat_type']})
    for s, e in zip(ir['sounding_events'], case['events']):
        p = pitch.Pitch(e['pitch'])
        s['pitch'].update(step=p.step, alter=q(int(p.accidental.alter) if p.accidental else 0), spelling=p.nameWithOctave)
    return ir


def fixed(ir, parts):
    rows, neighbors = prepare(ir)
    choose = provider(ir['measures'], enable_boundary_contrast=True)
    baseline = analyze(ir)
    segments = []
    for a, b, label in parts:
        c = next(c for c in choose(rows, neighbors, F(a), F(b), F(1), limit=None) if c['label'] == label)
        segments.append({'span': {'start': q(a), 'end': q(b)}, 'selected': c, 'beat_unit_quarter': q(1)})
    baseline['segments'] = segments
    baseline['path_cost'] = explain_path(baseline, verify=False)['reconstructed_path_cost']
    return baseline


class OwnershipTests(unittest.TestCase):
    def test_three_delayed_common_root_cases_recovered_as_alternatives(self):
        for texture in ('ascending', 'overlapping', 'delayed_quality'):
            ir = score(texture); result = analyze(ir)
            alts = review(ir, result)['alternatives']
            self.assertEqual(len(alts), 1, texture)
            self.assertEqual(alts[0]['proposed_boundary'], q(2))
            self.assertEqual(alts[0]['proposed_right_label'], 'G:dominant7')
            self.assertAlmostEqual(alts[0]['cost_delta'], 0)
            explain_path({'segments': alts[0]['alternative_segments'], 'path_cost': alts[0]['alternative_path_cost']})

    def test_unchanged_harmony_and_clear_block_change_not_expanded(self):
        for texture in ('block', 'ascending', 'descending', 'alberti', 'held_bass', 'overlapping', 'delayed_quality'):
            ir = score(texture, False)
            self.assertEqual(review(ir, analyze(ir))['alternatives'], [])
        ir = score('block')
        self.assertEqual(review(ir, analyze(ir))['alternatives'], [])

    def test_inputs_immutable_and_labels_ignored(self):
        ir = score(); result = analyze(ir); before = deepcopy((ir, result))
        out = review(ir, result)
        self.assertEqual((ir, result), before)
        self.assertFalse(out['selected_path_changed'])
        self.assertEqual(out, review({**ir, 'annotations': ['wrong'], 'phrases': ['wrong'], 'expected': ['wrong']}, result))

    def test_transposition_and_meter_relative_scaling(self):
        for tr, scale in ((0, F(1)), (2, F(1)), (0, F(1, 2))):
            ir = score(transpose=tr, scale=scale)
            a = review(ir, analyze(ir))['alternatives'][0]
            self.assertEqual(f(a['proposed_boundary'])/scale, 2)
            self.assertEqual((a['alternative_segments'][1]['selected']['root']-tr) % 12, 7)
            self.assertAlmostEqual(a['cost_delta'], 0)

    def test_stable_ids_and_event_references(self):
        ir = score(); result = analyze(ir)
        first = review(ir, result); self.assertEqual(first, review(ir, result))
        refs = {s['sounding_event_id'] for s in ir['sounding_events']}
        evidence = first['alternatives'][0]['evidence']
        for key in ('root_attack_refs', 'prefix_event_refs', 'completion_event_refs', 'new_member_attack_refs'):
            self.assertTrue(set(evidence[key]) <= refs)

    def test_silence_stops_backtracking(self):
        ir = score()
        # Root G ends before B enters; no continuous unfolding evidence.
        ir['sounding_events'][4]['span']['end'] = q(F(9, 4))
        r = fixed(ir, [(0,F(5,2),'C:major'), (F(5,2),4,'B:diminished')])
        self.assertEqual(review(ir, r)['alternatives'], [])

    def test_measure_boundary_not_crossed(self):
        ir = score()
        ir['measures'][0]['actual_duration_quarter'] = q(F(9, 4))
        ir['measures'].append({'global_start_quarter': q(F(9,4)), 'actual_duration_quarter': q(F(7,4)), 'time_signature': {'beat_type': 4}})
        r = fixed(ir, [(0,F(5,2),'C:major'), (F(5,2),4,'B:diminished')])
        self.assertEqual(review(ir, r)['alternatives'], [])

    def test_unattacked_root_and_pedal_bass_not_promoted(self):
        ir = score()
        # Low C continues under the apparent G restart: G is not lowest.
        ir['sounding_events'][0]['span']['end'] = q(4)
        ir['sounding_events'][0]['pitch'].update(midi_pitch=36, spelling='C2')
        r = fixed(ir, [(0,F(5,2),'C:major'), (F(5,2),4,'B:diminished')])
        self.assertEqual(review(ir, r)['alternatives'], [])

    def test_tie_continuation_is_not_a_new_root_attack(self):
        ir = score()
        ir['sounding_events'][4]['span']['start'] = q(0)
        ir['note_events'].append({'note_id': 'tie_continuation', 'voice_id': '1', 'global_onset_quarter': q(2)})
        r = fixed(ir, [(0,F(5,2),'C:major'), (F(5,2),4,'B:diminished')])
        self.assertEqual(review(ir, r)['alternatives'], [])

    def test_long_delayed_quality_exceeds_bound(self):
        ir = score('delayed_quality')
        ir['sounding_events'][4]['span']['end'] = q(5)
        for s in ir['sounding_events'][5:]:
            s['span'] = {'start': q(5), 'end': q(6)}
        ir['measures'][0]['actual_duration_quarter'] = q(6)
        r = fixed(ir, [(0,5,'C:major'), (5,6,'G:dominant7')])
        self.assertEqual(review(ir, r)['alternatives'], [])

    def test_enharmonic_conflict_abstains(self):
        ir = score()
        # B natural respelled as C flat has the same MIDI, not the same chord spelling.
        ir['sounding_events'][5]['pitch'].update(step='C', alter=q(-1), spelling='C-4')
        self.assertEqual(review(ir, analyze(ir))['alternatives'], [])

    def test_late_quality_is_explicit_uncertainty(self):
        ir = score('delayed_quality')
        a = review(ir, analyze(ir))['alternatives'][0]
        self.assertIn('quality_arrives_more_than_one_denominator_beat_later', a['counterevidence'])
        self.assertEqual(a['status'], 'review_candidate_not_selected')

    def test_invalid_engine_rejected_and_empty_supported(self):
        with self.assertRaises(ValueError): review({}, {'engine_version': 'other'})
        self.assertEqual(review({'sounding_events': []}, analyze({'sounding_events': []}))['alternatives'], [])


if __name__ == '__main__': unittest.main()
