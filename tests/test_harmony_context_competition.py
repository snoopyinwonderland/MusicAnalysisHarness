from copy import deepcopy
from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_context_competition as c
from test_harmony_transition_support import evidence, graph
from test_harmony_functional_scoring import C, G, G7, example
from musicanote_harness import harmony_full_score as score

FM = (('F', 0), (('A', 0), ('C', 0), ('F', 0)))


def neighbor(other=(), middle_end=F(3, 2), end=2):
    ev = evidence([('e', ('E', 0), 0, 1, 64, 'v'),
        ('f', ('F', 0), 1, middle_end, 65, 'v'),
        ('e2', ('E', 0), middle_end, end, 64, 'v'),
        ('bass', ('C', 0), 0, end, 48, 'bass'), *other], links=(('e', 'f'), ('f', 'e2')))
    p, ids = graph(((0, 1, C), (1, middle_end, FM), (middle_end, end, C)), end=end)
    return p, ev, ids


class CompetitionTests(unittest.TestCase):
    def test_neighbor_conflict_and_held_bass_not_hard_nct_decision(self):
        p, ev, ids = neighbor(); r = c.observe_path(p, ev, ids)
        t = r['transitions'][0]
        self.assertEqual(t['explained_event_ids'], ['f'])
        self.assertEqual(t['features']['hold_remaining_nonmember_exposure'], c.q(0))
        self.assertGreater(c.f(t['features']['reclassified_ornament_member_exposure']), 0)
        self.assertEqual(t['incoming_resolution_conflicting_pairs'], [['e', 'f']])
        self.assertEqual(t['features']['dominant_credit_with_hold_conflict'], c.q(1))
        self.assertEqual(t['features']['continuing_left_lowest_coverage'], c.q(F(1, 4)))
        self.assertFalse(t['confirmed_nct']); self.assertFalse(t['harmony_held_confirmed'])

    def test_real_new_chord_with_same_neighbor_retains_other_voice_counterevidence(self):
        p, ev, ids = neighbor((('a', ('A', 0), 1, F(3, 2), 57, 'inner'),
                               ('fbass', ('F', 0), 1, F(3, 2), 41, 'low')))
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(t['remaining_held_foreign_ids'], ['a', 'fbass'])
        self.assertEqual(t['new_exclusive_unassigned_ids'], ['a', 'fbass'])
        self.assertGreater(c.f(t['features']['hold_remaining_nonmember_exposure']), 0)
        self.assertEqual(t['features']['continuing_left_lowest_coverage'], c.q(0))

    def test_long_neighbor_is_not_removed_by_short_note_gate(self):
        p, ev, ids = neighbor(middle_end=F(4), end=5)
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(t['conditional_figures'][0]['metric_and_duration'][0]['duration_in_local_beats'], c.q(3))
        self.assertEqual(t['explained_event_ids'], ['f'])
        self.assertFalse(t['harmony_held_confirmed'])

    def test_passing_like_anchors_use_actual_selected_chords(self):
        ev = evidence([('c', ('C', 0), 0, 1, 60, 'v'), ('d', ('D', 0), 1, F(3, 2), 62, 'v'),
                       ('e', ('E', 0), F(3, 2), 2, 64, 'v')], links=(('c', 'd'), ('d', 'e')))
        p, ids = graph(((0, 1, C), (1, F(3, 2), G), (F(3, 2), 2, C)))
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(t['conditional_figures'][0]['kind'], 'passing_like')
        bad, bi = graph(((0, 1, G), (1, F(3, 2), G), (F(3, 2), 2, C)))
        self.assertFalse(c.observe_path(bad, ev, bi)['transitions'][0]['conditional_figures'])

    def test_double_neighbor_retains_both_middle_attacks_and_fractional_durations(self):
        ev = evidence([('c', ('C', 0), 0, F(1, 3), 60, 'v'),
            ('d', ('D', 0), F(1, 3), F(2, 3), 62, 'v'),
            ('b', ('B', 0), F(2, 3), 1, 59, 'v'), ('c2', ('C', 0), 1, 2, 60, 'v')],
            links=(('c', 'd'), ('d', 'b'), ('b', 'c2')))
        p, ids = graph(((0, F(1, 3), C), (F(1, 3), 1, G7), (1, 2, C)))
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(t['explained_event_ids'], ['b', 'd'])
        self.assertEqual(t['conditional_figures'][0]['kind'], 'double_neighbor_like')
        self.assertEqual(t['features']['hold_explained_step_exposure'], c.q(F(1, 3)))

    def test_repeated_or_overlapping_figures_do_not_sum_same_sound_twice(self):
        p, ev, ids = neighbor(); ctx = c.Context(ev); ctx.figures *= 3
        runs = c.completed_runs(p, ids); t = ctx.conflict(runs, 1, F(4))
        self.assertEqual(len(t['conditional_figures']), 3)
        self.assertEqual(t['features']['hold_explained_step_exposure'], c.q(F(1, 8)))
        self.assertEqual(t['features']['dominant_credit_with_hold_conflict'], c.q(1))

    def test_unknown_foreign_voice_not_known_zero_but_member_chord_doubling_allowed(self):
        p, ev, ids = neighbor((('x', ('A', 0), 1, F(3, 2), 57, None),))
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertIsNone(t['features']['hold_explained_step_exposure'])
        self.assertGreater(c.f(t['observed_feature_sums']['hold_explained_step_exposure']), 0)
        p, ev, ids = neighbor((('doubling', ('C', 0), 1, F(3, 2), 60, None),))
        self.assertTrue(c.observe_path(p, ev, ids)['transitions'][0]['availability']['hold_explained_step_exposure'])

    def test_unknown_meter_preserves_geometry_but_not_graded_function(self):
        p, ev, ids = neighbor(); ev.source.measures = ((F(0), (None, 4), None),)
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertEqual(t['explained_event_ids'], ['f'])
        self.assertIsNone(t['conditional_figures'][0]['metric_and_duration'][0]['duration_in_local_beats'])
        self.assertIsNone(t['features']['dominant_credit_with_hold_conflict'])

    def test_grace_barrier_and_source_clock_history_rejection_not_bridged(self):
        p, ev, ids = neighbor()
        kwargs = [{'grace_notes': [{'part_id': 'part', 'voice_id': 'v', 'global_onset_quarter': c.q(F(5, 4))}]},
                  {'context_barriers': (F(5, 4),)}, {'history_gate': lambda a, b: False}]
        for kw in kwargs:
            self.assertFalse(c.observe_path(p, ev, ids, **kw)['transitions'][0]['explained_event_ids'])

    def test_gap_and_overlap_in_explicit_lane_not_guessed_away(self):
        p, ev, ids = neighbor()
        ev.links = ev.links[:1]
        self.assertFalse(c.observe_path(p, ev, ids)['transitions'][0]['explained_event_ids'])
        p, ev, ids = neighbor((('overlap', ('D', 0), F(5, 4), F(7, 4), 62, 'v'),))
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertFalse(t['explained_event_ids']); self.assertIsNone(t['features']['hold_explained_step_exposure'])

    def test_octave_or_enharmonic_return_is_not_same_neighbor(self):
        p, ev, ids = neighbor(); row = next(r for r in ev.rows if r['id'] == 'e2')
        row['pitch'] = 76; row['pitch_data']['octave'] = 5; row['pitch_data']['midi_pitch'] = 76
        self.assertFalse(c.observe_path(p, ev, ids)['transitions'][0]['explained_event_ids'])

    def test_complete_run_raw_subdivision_invariance(self):
        p, ev, ids = neighbor()
        split, si = graph(((0, F(1, 2), C), (F(1, 2), 1, C),
                          (1, F(3, 2), FM), (F(3, 2), 2, C)))
        self.assertEqual(c.observe_path(p, ev, ids), c.observe_path(split, ev, si))

    def test_arpeggio_and_omitted_root_are_not_rejected_or_invented(self):
        ev = evidence([('g', ('G', 0), 0, 1, 55, 'v'), ('c', ('C', 0), 1, F(4, 3), 60, 'v'),
                       ('e', ('E', 0), F(4, 3), F(5, 3), 64, 'v'),
                       ('g2', ('G', 0), F(5, 3), 2, 67, 'v')])
        p, ids = graph(((0, 1, G), (1, 2, C)))
        t = c.observe_path(p, ev, ids)['transitions'][0]
        self.assertFalse(t['explained_event_ids']); self.assertEqual(t['source_window']['coverage']['right_two'], c.q(0))
        self.assertEqual(t['source_window']['right_union_member_count'], 3)
        self.assertFalse(t['harmony_held_confirmed'])

    def test_original_source_and_score_unchanged(self):
        ir, _, _, p, ev = example(); before = deepcopy(ir)
        ids = [e.group_id for e in p.edges]; s = score.Scorer(p, ev, score.initial_weights(score.fresh.timing.ZERO))
        cost = s.score_path(ids); r = c.observe_path(p, ev, ids)
        self.assertEqual(ir, before); self.assertEqual(s.score_path(ids), cost)
        self.assertFalse(r['existing_costs_changed']); self.assertFalse(r['source_labels_used'])

    def test_history_clock_checked_only_for_qualified_figures_and_shared_once(self):
        p, ev, ids = neighbor(); calls = []
        ctx = c.Context(ev, history_gate=lambda a, b: calls.append((a, b)) or True)
        self.assertFalse(calls)
        a = c.observe_path(p, ev, ids, context=ctx); b = c.observe_path(p, ev, ids, context=ctx)
        self.assertEqual(a, b); self.assertEqual(calls, [(F(0), F(2))])
        other = evidence([('x', ('C', 0), 0, 2, 60, 'v')])
        with self.assertRaises(ValueError): c.observe_path(p, other, ids, context=ctx)

    def test_empty_transition_domain_is_zero_and_invalid_path_rejected(self):
        p, ev, _ = neighbor(); one, oi = graph(((0, 2, C),))
        r = c.observe_path(one, ev, oi)
        self.assertTrue(r['empty_transition_domain_known_zero']); self.assertTrue(all(r['availability'].values()))
        self.assertTrue(all(c.f(v) == 0 for v in r['features'].values()))
        with self.assertRaises(ValueError): c.observe_path(p, ev, [])


if __name__ == '__main__': unittest.main()
