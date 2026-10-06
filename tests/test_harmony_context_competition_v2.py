from copy import deepcopy
from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_context_competition_v2 as v2
from musicanote_harness import harmony_context_competition as v1
from musicanote_harness import harmony_context_competition_trial_v2 as trial
from test_harmony_context_competition import neighbor, FM
from test_harmony_transition_support import evidence, graph
from test_harmony_functional_scoring import C, G


def extended_passing(extra=()):
    ev = evidence([('e', ('E', 0), 0, 1, 64, 'v'), ('f', ('F', 0), 1, F(5, 4), 65, 'v'),
        ('g', ('G', 0), F(5, 4), F(3, 2), 67, 'v'),
        ('a', ('A', 0), F(3, 2), F(7, 4), 69, 'v'),
        ('b', ('B', 0), F(7, 4), 2, 71, 'v'),
        ('bass', ('C', 0), 0, 2, 48, 'bass'), *extra],
        links=(('e', 'f'), ('f', 'g'), ('g', 'a'), ('a', 'b')))
    p, ids = graph(((0, 1, C), (1, F(7, 4), FM), (F(7, 4), 2, C)))
    return p, ev, ids


class AlternativeAnchorTests(unittest.TestCase):
    def test_hypothesis_not_vetoed_by_selected_nonmember_anchor(self):
        p, ev, ids = extended_passing()
        old = v1.observe_path(p, ev, ids); new = v2.observe_path(p, ev, ids)
        self.assertFalse(old['transitions'][0]['conditional_figures'])
        t = new['transitions'][0]
        self.assertEqual(t['explained_event_ids'], ['f'])
        self.assertTrue(t['conditional_figures'][0]['current_path_anchor_is_nonmember_somewhere'])
        self.assertEqual(t['conditional_figures'][0]['anchor_role_alternatives'][1]['selected_path_cells'][0]['is_selected_member'], False)
        self.assertEqual(t['features']['dominant_credit_with_hold_conflict'], v2.q(1))
        self.assertFalse(t['confirmed_nct']); self.assertFalse(t['harmony_held_confirmed'])

    def test_unexplained_next_notes_not_swallowed_by_extended_pattern(self):
        p, ev, ids = extended_passing()
        t = v2.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(t['remaining_held_foreign_ids'], ['a'])
        self.assertEqual(t['new_exclusive_unassigned_ids'], ['a'])
        self.assertGreater(v2.f(t['features']['hold_remaining_nonmember_exposure']), 0)

    def test_other_voices_continue_to_support_real_chord_change(self):
        p, ev, ids = extended_passing((('fbass', ('F', 0), 1, F(7, 4), 41, 'low'),))
        t = v2.observe_path(p, ev, ids)['transitions'][0]
        self.assertIn('fbass', t['remaining_held_foreign_ids'])
        self.assertEqual(t['features']['continuing_left_lowest_coverage'], v2.q(0))
        self.assertFalse(t['harmony_held_confirmed'])

    def test_old_compatible_neighbor_vector_unchanged_but_roles_preserved(self):
        p, ev, ids = neighbor(); old = v1.observe_path(p, ev, ids); new = v2.observe_path(p, ev, ids)
        self.assertEqual(old['features'], new['features'])
        self.assertTrue(new['selected_anchor_membership_is_alternative_not_veto'])
        self.assertFalse(new['transitions'][0]['conditional_figures'][0]['current_path_anchor_is_nonmember_somewhere'])

    def test_wrong_held_anchor_membership_still_rejected_and_source_unchanged(self):
        p, ev, ids = extended_passing(); before = deepcopy(ev.rows)
        bad, bi = graph(((0, 1, G), (1, F(7, 4), FM), (F(7, 4), 2, C)))
        t = v2.observe_path(bad, ev, bi)['transitions'][0]
        self.assertNotIn('f', t['explained_event_ids'])
        self.assertIn('a', t['explained_event_ids'])  # G-A-B is compatible with held G, unlike E-F-G.
        self.assertEqual(ev.rows, before)

    def test_grace_history_and_voice_barriers_still_apply(self):
        p, ev, ids = extended_passing()
        self.assertFalse(v2.observe_path(p, ev, ids, context_barriers=(F(9, 8),))['transitions'][0]['conditional_figures'])
        self.assertFalse(v2.observe_path(p, ev, ids, history_gate=lambda a, b: False)['transitions'][0]['conditional_figures'])

    def test_strict_context_rejected_and_raw_split_invariant(self):
        p, ev, ids = neighbor()
        with self.assertRaises(ValueError): v2.observe_path(p, ev, ids, context=v1.Context(ev))
        split, si = graph(((0, F(1, 2), C), (F(1, 2), 1, C), (1, F(3, 2), FM), (F(3, 2), 2, C)))
        self.assertEqual(v2.observe_path(p, ev, ids), v2.observe_path(split, ev, si))

    def test_unknown_delta_not_substituted_by_zero(self):
        p, ev, ids = extended_passing(); a = v2.observe_path(p, ev, ids); b = deepcopy(a)
        b['features']['hold_explained_step_exposure'] = None; b['availability']['hold_explained_step_exposure'] = False
        self.assertIsNone(trial.vector_difference(a, b)['hold_explained_step_exposure'])
        self.assertFalse(a['selection_changed']); self.assertFalse(a['source_labels_used'])


if __name__ == '__main__': unittest.main()
