from copy import deepcopy
import unittest
from test_harmony_boundary_observations import fixture
from test_harmony_boundary_figures import pair_fixture, F, C
from musicanote_harness.harmony_boundary_figures import augment as figures
from musicanote_harness.harmony_boundary_observations import augment as observations, observe
from musicanote_harness.harmony_boundary_assessment import assess_support, augment


def support_case(specs, members=None):
    ir, r = fixture(specs, members=members)
    e = observe(ir, r, 0)
    p = e['candidate_support_profiles'][e['reading_profile_refs']['hold'][0]]
    return assess_support(p, e['cells'])


def suspension():
    r = figures(pair_fixture([('F4', 0, 2), ('E4', 2, 3)], F, C))
    return observations({'measures': []}, r)


class BoundaryAssessmentTests(unittest.TestCase):
    def test_arpeggio_not_rejected_for_no_simultaneity(self):
        a = support_case([('C4', 0, 1, 'v'), ('E4', 1, 2, 'v'), ('G4', 2, 3, 'v')])
        self.assertEqual(a['status'], 'all_members_observed_with_delay')
        self.assertEqual(a['delayed_members'], [['E', 0], ['G', 0]])
        self.assertFalse(a['arpeggiation_confirmed']); self.assertFalse(a['candidate_rejected'])

    def test_missing_member_differs_from_delayed(self):
        a = support_case([('C4', 0, 1, 'v'), ('E4', 1, 3, 'v')])
        self.assertEqual(a['status'], 'partial_members_observed')
        self.assertEqual(a['unobserved_members'], [['G', 0]])
        self.assertEqual(a['delayed_members'], [['E', 0]])

    def test_no_member_observed(self):
        a = support_case([('F4', 0, 3, 'v')])
        self.assertEqual(a['status'], 'no_members_observed')
        self.assertFalse(a['candidate_rejected'])

    def test_all_at_entry(self):
        a = support_case([('C4', 0, 3, 'a'), ('E4', 0, 3, 'b'), ('G4', 0, 3, 'c')])
        self.assertEqual(a['status'], 'all_members_at_entry')

    def test_unknown_pitch_limits_absence_claim(self):
        ir, r = fixture([('C4', 0, 3, 'v')]); r['events'][0]['pitch']['midi_pitch'] = None
        e = observe(ir, r, 0); p = next(iter(e['candidate_support_profiles'].values()))
        a = assess_support(p, e['cells'])
        self.assertEqual(a['status'], 'unknown_pitch_limits_support'); self.assertFalse(a['absence_certain'])

    def test_enharmonic_not_substituted(self):
        a = support_case([('Gb4', 0, 3, 'v')], [['F', 1]])
        self.assertEqual(a['status'], 'no_members_observed')

    def test_repeated_member_first_observation_only(self):
        a = support_case([('C4', 0, 1, 'v'), ('C4', 1, 3, 'v')], [['C', 0]])
        self.assertEqual(len(a['first_observations']), 1)

    def test_suspension_kept_but_not_confirmed(self):
        r = suspension(); a = augment(r)['boundaries'][0]['boundary_assessment']
        self.assertEqual(len(a['patterns']), 1)
        p = a['patterns'][0]; self.assertEqual(p['status'], 'abstain')
        self.assertIn('boundary_dissonance_unconfirmed', p['abstention_reasons'])
        self.assertEqual(p['competing_member_reading_indices']['hold'], [0])
        self.assertFalse(p['confirmed']); self.assertFalse(p['remove_note'])

    def test_blocked_competing_harmony_not_offered(self):
        r = suspension(); r['hold_readings'][0]['condition']['abstention_reasons'] = ['blocked']
        p = augment(r)['boundaries'][0]['boundary_assessment']['patterns'][0]
        self.assertFalse(p['competing_member_reading_indices']['hold'])

    def test_prior_json_not_changed(self):
        r = suspension(); saved = deepcopy(r); a = augment(r)
        self.assertEqual(r, saved); a.pop('boundary_assessment_version')
        for b in a['boundaries']: b.pop('boundary_assessment')
        self.assertEqual(a, r)

    def test_missing_temporal_evidence_abstains(self):
        r = suspension(); r['boundaries'][0].pop('temporal_observations')
        a = augment(r)['boundaries'][0]['boundary_assessment']
        self.assertEqual(a['status'], 'evidence_unavailable')

    def test_deterministic(self):
        self.assertEqual(augment(suspension()), augment(suspension()))

    def test_alternative_membership_not_forced_into_nct(self):
        r = suspension(); b = r['boundaries'][0]; alt = deepcopy(r['hold_readings'][0])
        alt['span'] = deepcopy(b['right']['readings'][0]['span'])
        b['right']['readings'].append(alt)
        r = observations({'measures': []}, r)
        p = augment(r)['boundaries'][0]['boundary_assessment']['patterns'][0]
        self.assertEqual(p['competing_member_reading_indices']['right'], [1])
        self.assertFalse(p['confirmed'])

    def test_missing_lowest_adds_reason_not_false_interval(self):
        r = suspension(); e = r['boundaries'][0]['temporal_observations']
        e['cells'][e['after_cell_index']]['bass_status'] = 'unknown_pitch_present'
        e['cells'][e['after_cell_index']]['intervals_from_lowest'] = []
        p = augment(r)['boundaries'][0]['boundary_assessment']['patterns'][0]
        self.assertIn('boundary_lowest_pitch_unavailable', p['abstention_reasons'])
        self.assertFalse(p['checkpoints'][1]['intervals'])

    def test_non_suspension_patterns_not_relabelled(self):
        r = figures(pair_fixture([('F4', 0, 2)], C, F, end=2))
        r = observations({'measures': []}, r)
        self.assertTrue(r['boundaries'][0]['boundary_figures']['patterns'])
        self.assertFalse(augment(r)['boundaries'][0]['boundary_assessment']['patterns'])

    def test_denominator_grid_is_not_automatic_accent(self):
        r = suspension(); e = r['boundaries'][0]['temporal_observations']
        e['cells'][e['after_cell_index']]['meter']['on_denominator_grid'] = True
        p = augment(r)['boundaries'][0]['boundary_assessment']['patterns'][0]
        self.assertIn('accent_and_style_unconfirmed', p['abstention_reasons'])


if __name__ == '__main__': unittest.main()
