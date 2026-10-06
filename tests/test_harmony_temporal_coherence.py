from copy import deepcopy
from fractions import Fraction
import unittest
from test_harmony_boundary_observations import fixture
from test_harmony_boundary_figures import pair_fixture, C, F, G
from test_harmony_segment_contrast import full_assignment
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_boundary_observations import augment as observations
from musicanote_harness.harmony_temporal_coherence import augment, compare, profile_support


def profile(specs, end=3):
    ir, r = fixture(specs, end=end)
    out = augment(observations(ir, r)); b = out['boundaries'][0]
    return b['temporal_coherence']['profiles'][b['temporal_observations']['reading_profile_refs']['hold'][0]]


def paired(notes, left=C, right=G, cut=1, end=3):
    return observations({'measures': []}, pair_fixture(notes, left, right, cut=cut, end=end))


class TemporalCoherenceTests(unittest.TestCase):
    def test_clean_arpeggio_has_no_nonmember_time(self):
        p = profile([('C4', 0, 1, 'v'), ('E4', 1, 2, 'v'), ('G4', 2, 3, 'v')])
        self.assertEqual(p['cell_time_quarters']['member_only'], q(3))
        self.assertEqual(p['first_complete_union_time'], q(2))
        self.assertTrue(p['all_sounding_pitches_are_members']); self.assertFalse(p['arpeggiation_confirmed'])

    def test_same_union_with_intervening_foreign_tone_not_clean(self):
        p = profile([('C4', 0, 1, 'v'), ('D4', 1, 2, 'v'), ('E4', 2, 3, 'v'), ('G4', 3, 4, 'v')], end=4)
        self.assertTrue(p['complete_union_contains_nonmembers'])
        self.assertFalse(p['all_sounding_pitches_are_members'])
        self.assertEqual([r['state'] for r in p['runs']], ['member_only', 'nonmember_only', 'member_only'])

    def test_silence_not_silently_bridged(self):
        p = profile([('C4', 0, 1, 'v'), ('E4', 2, 3, 'v'), ('G4', 3, 4, 'v')], end=4)
        self.assertTrue(p['complete_union_crosses_silence'])
        self.assertEqual(p['cell_time_quarters']['silence'], q(1))

    def test_silence_after_completion_not_prefix_gap(self):
        p = profile([('C4', 0, 1, 'a'), ('E4', 0, 1, 'b'), ('G4', 0, 1, 'c')])
        self.assertFalse(p['complete_union_crosses_silence'])

    def test_doubling_not_double_wallclock(self):
        p = profile([('C4', 0, 3, 'a'), ('C5', 0, 3, 'b')])
        self.assertEqual(p['cell_time_quarters']['member_only'], q(3))
        self.assertIsNone(p['first_complete_union_time'])

    def test_triplet_total_exact(self):
        p = profile([('C4', 0, Fraction(1, 3), 'v'), ('D4', Fraction(1, 3), 3, 'v')])
        self.assertEqual(p['cell_time_quarters']['member_only'], q(Fraction(1, 3)))
        self.assertEqual(p['cell_time_quarters']['nonmember_only'], q(Fraction(8, 3)))

    def test_mixed_polyphony_not_pure_member(self):
        p = profile([('C3', 0, 3, 'bass'), ('F4', 0, 3, 'v')])
        self.assertEqual(p['cell_time_quarters']['mixed'], q(3))
        self.assertEqual(p['lowest_pitch_runs'][0]['membership'], ['member'])

    def test_member_only_arpeggio_can_move_lowest_pitch(self):
        p = profile([('C4', 0, 1, 'v'), ('E4', 1, 2, 'v'), ('G4', 2, 3, 'v')])
        self.assertEqual(len(p['lowest_pitch_runs']), 3)
        self.assertTrue(p['all_sounding_pitches_are_members'])

    def test_unknown_pitch_not_discarded(self):
        ir, r = fixture([('C3', 0, 3, 'a'), ('E4', 0, 3, 'b')])
        r['events'][0]['pitch']['midi_pitch'] = None; b = augment(observations(ir, r))['boundaries'][0]
        p = b['temporal_coherence']['profiles'][b['temporal_observations']['reading_profile_refs']['hold'][0]]
        self.assertEqual(p['cell_time_quarters']['unknown'], q(3))
        self.assertFalse(p['all_sounding_pitches_are_members'])

    def test_two_sided_exclusivity_not_change_verdict(self):
        r = paired([('E4', 0, 1), ('B4', 1, 3)])
        c = compare(r, 0, 0, 0, 0, full_assignment(r))
        self.assertTrue(c['two_sided_differentiating_members']); self.assertFalse(c['harmonic_change_confirmed'])
        self.assertEqual(c['boundary_voice_links'][0]['split_membership'], ['member', 'member'])
        self.assertIsNone(c['preferred'])

    def test_same_member_sets_no_differentiation(self):
        r = paired([('C4', 0, 1), ('G4', 1, 3)], C, C)
        c = compare(r, 0, 0, 0, 0, full_assignment(r))
        self.assertTrue(c['same_member_sets']); self.assertFalse(c['two_sided_differentiating_members'])

    def test_common_sustain_can_coexist_with_change_evidence(self):
        r = paired([('E4', 0, 1), ('B4', 1, 3), ('G3', 0, 3)])
        c = compare(r, 0, 0, 0, 0, full_assignment(r))
        self.assertTrue(c['two_sided_differentiating_members'])
        self.assertIn(('member', 'member'), [(x['left'], x['right']) for x in c['held_memberships']])

    def test_no_link_has_no_invented_voice_motion(self):
        r = paired([('E4', 0, 1), ('B4', 1, 3)])
        aid = next(a['assignment_id'] for a in r['assignments'] if not a['links'])
        self.assertFalse(compare(r, 0, 0, 0, 0, aid)['boundary_voice_links'])

    def test_unknown_assignment_fails(self):
        with self.assertRaisesRegex(ValueError, 'unknown_assignment'):
            compare(paired([('E4', 0, 1), ('B4', 1, 3)]), 0, 0, 0, 0, 'missing')

    def test_previous_data_unchanged(self):
        r = paired([('E4', 0, 1), ('B4', 1, 3)]); old = deepcopy(r); out = augment(r)
        self.assertEqual(r, old); out.pop('temporal_coherence_version')
        for b in out['boundaries']: b.pop('temporal_coherence')
        self.assertEqual(out, r)

    def test_missing_evidence_abstains(self):
        r = paired([('E4', 0, 1), ('B4', 1, 3)]); r['boundaries'][0].pop('temporal_observations')
        self.assertEqual(augment(r)['boundaries'][0]['temporal_coherence']['status'], 'evidence_unavailable')

    def test_held_source_role_after_cut_not_hidden(self):
        r = paired([('F4', 0, 2), ('E4', 2, 3)], F, C)
        c = compare(r, 0, 0, 0, 0, full_assignment(r))
        self.assertEqual(c['boundary_voice_links'][0]['source_membership_after_boundary'], 'nonmember')
        self.assertFalse(c['boundary_voice_links'][0]['at_boundary'])

    def test_enharmonic_pitch_not_member_by_midi_alone(self):
        p = profile([('B#3', 0, 3, 'v')])
        self.assertEqual(p['cell_time_quarters']['nonmember_only'], q(3))

    def test_blocked_candidate_reasons_preserved(self):
        r = paired([('E4', 0, 1), ('B4', 1, 3)])
        r['hold_readings'][0]['condition']['abstention_reasons'] = ['timing_unknown']
        self.assertEqual(compare(r, 0, 0, 0, 0, full_assignment(r))['candidate_abstention_reasons'], ['timing_unknown'])

    def test_invalid_profile_partition_rejected(self):
        ir, r = fixture([('C4', 0, 3, 'v')]); b = observations(ir, r)['boundaries'][0]
        e = b['temporal_observations']; p = deepcopy(e['candidate_support_profiles'][e['reading_profile_refs']['hold'][0]])
        p['cells'].pop(0)
        with self.assertRaisesRegex(ValueError, 'noncontiguous_profile_cells'):
            profile_support(p, e['cells'], {s['sounding_event_id']: s for s in r['events']})


if __name__ == '__main__': unittest.main()
