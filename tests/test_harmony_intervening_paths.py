from copy import deepcopy
from fractions import Fraction as F
import unittest

from test_harmony_reading_voice_context import score, chord
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_delayed_links import observe
from musicanote_harness.harmony_link_counterevidence import assess as counters
from musicanote_harness.harmony_intervening_paths import assess


def fixture(names=('C4', 'E4', 'G4')):
    return score([('B3', 0, 1, 'v'), ('C3', 0, 3, 'bass')] +
                 [(p, F(5+i, 4), F(6+i, 4), 'v') for i, p in enumerate(names)])


def run(ir, root=0, quality='major', span=None, observation_ir=None):
    contexts = [{'start': q(0), 'end': q(8)}]
    baseline = observation_ir or ir
    obs = observe(baseline, contexts); prior = counters(baseline, obs, contexts)
    roles = [{'candidate_ref': 'test-hypothesis', 'comparisons': [
        {'group_id': r['group_id'], 'source_refs': r['source_refs'], 'reading_type': 'test', 'reading_index': 0,
         'target_chord_context': {'span': span or {'start': q(1), 'end': q(3)}, 'candidate': chord(root, quality)}}
        for r in prior['records']]}]
    result = assess(ir, obs, prior, roles, contexts)
    return next(r for r in result['records'] if r['source_refs'] == ['s0', 's4'])


class InterveningPathsTest(unittest.TestCase):
    def test_unfolding_preserves_intermediate_and_initial_gap(self):
        r = run(fixture())
        self.assertEqual(r['arrival_event_refs'], ['s2', 's3', 's4'])
        self.assertEqual(r['initial_gap'], {'start': q(1), 'end': q(F(5, 4))})
        self.assertEqual(r['conditional_explanations'][0]['compatible_patterns'], ['chord_member_unfolding_compatible'])
        self.assertFalse(r['voice_connection_confirmed'])
        self.assertFalse(r['independent_resolution_vote_allowed'])

    def test_passing_geometry_requires_nonmember_middle(self):
        r = run(fixture(('C4', 'D4', 'E4')))
        e = r['conditional_explanations'][0]
        self.assertEqual(e['conditional_ornaments'][0]['conditional_role'], 'passing_candidate')
        self.assertFalse(r['nct_confirmed'])

    def test_neighbor_condition_changes_with_harmony(self):
        ir = fixture(('E4', 'F4', 'E4'))
        self.assertEqual(run(ir)['conditional_explanations'][0]['conditional_ornaments'][0]['conditional_role'], 'neighbor_candidate')
        self.assertEqual(run(ir, 5)['conditional_explanations'][0]['conditional_ornaments'], [])

    def test_unexplained_leap_not_forced_into_nct(self):
        r = run(fixture(('C4', 'F#4', 'G4')))
        self.assertEqual(r['conditional_explanations'][0]['unexplained_nonmember_refs'], ['s3'])
        self.assertEqual(r['conditional_explanations'][0]['compatible_patterns'], [])

    def test_enharmonic_shortcut_not_passing(self):
        self.assertEqual(run(fixture(('C4', 'C##4', 'E4')))['conditional_explanations'][0]['compatible_patterns'], [])

    def test_enharmonic_member_needs_coherent_spelling(self):
        r = run(fixture(('C4', 'F-4', 'G4')))
        self.assertEqual(r['conditional_explanations'][0]['compatible_patterns'], [])

    def test_gap_inside_arrival_blocks_triplet_geometry(self):
        ir = fixture(('C4', 'D4', 'E4')); ir['sounding_events'][2]['span']['end'] = q(F(11, 8))
        r = run(ir)
        self.assertTrue(r['arrival_gaps']); self.assertEqual(r['arrival_geometry'], [])

    def test_sustained_same_lane_prevents_fictional_melody(self):
        ir = fixture(); ir['note_events'][1]['voice_id'] = 'v'
        r = run(ir)
        self.assertIn('arrival_polyphony_or_sustained_overlap', r['abstention_reasons'])
        self.assertEqual(r['conditional_explanations'][0]['compatible_patterns'], [])

    def test_partial_chord_context_not_extended(self):
        r = run(fixture(), span={'start': q(F(3, 2)), 'end': q(3)})
        self.assertFalse(r['conditional_explanations'][0]['arrival_covered'])
        self.assertEqual(r['conditional_explanations'][0]['compatible_patterns'], [])

    def test_no_root_spelling_invented(self):
        ir = fixture(('E4', 'G4', 'E5'))
        ir['sounding_events'][1]['span']['end'] = q(1)
        self.assertEqual(run(ir)['conditional_explanations'][0]['coherent_root_spellings'], [])

    def test_no_geometry_across_meter_change(self):
        ir = fixture(); m = deepcopy(ir['measures'][0]); m.update(global_start_quarter=q(F(3, 2)), time_signature={'beat_type': 8}); ir['measures'].append(m)
        self.assertIn('meter_unavailable_or_changed', run(ir, observation_ir=fixture())['abstention_reasons'])

    def test_repeat_barrier_is_preserved(self):
        ir = fixture(); ir['measures'][0].update(actual_duration_quarter=q(F(3, 2)), repeat_barline={'repeat_direction': 'backward'})
        self.assertIn('repeat_or_ending_barrier', run(ir, observation_ir=fixture())['abstention_reasons'])

    def test_grace_prevents_unqualified_geometry(self):
        ir = fixture(); n = deepcopy(ir['note_events'][2]); n.update(note_id='grace', global_onset_quarter=q(F(3, 2)), grace={'is_grace': True}); ir['note_events'].append(n)
        self.assertIn('grace_timing_unresolved', run(ir)['abstention_reasons'])

    def test_input_immutable_and_labels_irrelevant(self):
        ir = fixture(); old = deepcopy(ir); a = run(ir)
        self.assertEqual(ir, old)
        self.assertEqual(a, run({**ir, 'annotations': [{'label': 'V7'}], 'phrases': [123]}))

    def test_source_polyphony_does_not_make_arrival_connection_certain(self):
        ir = fixture(); ir['note_events'][1]['voice_id'] = 'v'; ir['sounding_events'][1]['span']['end'] = q(1)
        r = run(ir)
        self.assertIn('polyphonic_voice_identity_unresolved', r['prior_review_reasons'])
        self.assertFalse(r['voice_connection_confirmed'])
