from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_member_release as s
from musicanote_harness.harmony_candidate_recall import fraction as f
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C, G, G7, F64


class MemberReleaseTests(unittest.TestCase):
    def make(self, seventh_end=1, end=4, extras=()):
        return problem(fixture([('G3', 0, end, 'bass'), ('B3', 0, end, 'third'),
            ('D4', 0, end, 'fifth'), ('F4', 0, seventh_end, 'seventh'), *extras], end=end), end=end)

    def value(self, graph, ev, sig=G7, **args):
        return s.observe(graph, ev, graph.points[0], graph.points[-1], sig, **args)

    def test_early_release_after_allowance(self):
        graph, ev = self.make(); value, r = self.value(graph, ev)
        self.assertEqual(value, F(1, 2)); self.assertEqual(f(r['last_seventh_release']), 1)
        self.assertEqual(f(r['tail_beats']), 3); self.assertTrue(r['tail_support_event_ids'])
        self.assertFalse(r['confirmed_boundary']); self.assertFalse(r['confirmed_nct'])

    def test_sustained_seventh_does_not_use_attack_duration(self):
        graph, ev = self.make(seventh_end=4)
        # This API consumes canonical sounding spans, not shorter notated notes.
        value, r = self.value(graph, ev)
        self.assertEqual(value, 0); self.assertEqual(r['reason'], 'seventh_still_sounding_at_run_end')

    def test_real_tie_chain_uses_combined_sounding_release(self):
        ir = fixture([('G3', 0, 4, 'bass'), ('B3', 0, 4, 'third'),
                      ('D4', 0, 4, 'fifth'), ('F4', 0, 4, 'seventh')])
        sound = ir['sounding_events'][-1]; first = ir['note_events'][-1]; second = deepcopy(first)
        first['notated_duration_quarter'] = s.q(1)
        second.update(note_id='tie_tail', global_onset_quarter=s.q(1), notated_duration_quarter=s.q(3))
        ir['note_events'].append(second); sound['source_note_ids'].append('tie_tail')
        sound['tie_chain_id'] = 'tie_seventh'
        graph, ev = problem(ir)
        value, r = self.value(graph, ev)
        self.assertEqual(value, 0)
        self.assertEqual(f(r['last_seventh_release']), 4)
        self.assertIn('tie_tail', r['source_note_ids'][sound['sounding_event_id']])

    def test_short_arpeggio_tail_within_one_beat_is_zero(self):
        graph, ev = self.make(seventh_end=3)
        self.assertEqual(self.value(graph, ev)[0], 0)

    def test_repeated_seventh_resets_terminal_tail(self):
        graph, ev = self.make(extras=(('F5', 3, 4, 'another'),))
        self.assertEqual(self.value(graph, ev)[0], 0)

    def test_never_heard_not_charged_twice(self):
        graph, ev = problem(fixture([('G3', 0, 4, 'b'), ('B3', 0, 4, 't'), ('D4', 0, 4, 'f')]))
        value, r = self.value(graph, ev)
        self.assertEqual(value, 0); self.assertIn('existing_absence', r['reason'])

    def test_triad_known_zero_functional_unknown(self):
        graph, ev = self.make()
        self.assertEqual(self.value(graph, ev, G)[0], 0)
        self.assertIsNone(self.value(graph, ev, F64)[0])

    def test_distributed_triad_union_allowed(self):
        graph, ev = problem(fixture([('F4', 0, 1, 's'), ('G3', 1, 2, 'v'),
            ('B3', 2, 3, 'v'), ('D4', 3, 4, 'v')]))
        value, r = self.value(graph, ev)
        self.assertEqual(value, F(1, 2)); self.assertFalse(r['simultaneous_triad_required'])

    def test_incomplete_triad_or_silence_not_forced_change(self):
        graph, ev = problem(fixture([('F4', 0, 1, 's'), ('G3', 1, 4, 'b'), ('B3', 1, 4, 't')]))
        self.assertEqual(self.value(graph, ev)[0], 0)

    def test_unknown_pitch_clock_gate_and_meter_stay_null(self):
        graph, ev = self.make(); altered = deepcopy(ev)
        altered.rows[0]['token'] = None
        self.assertIsNone(self.value(graph, altered)[0])
        altered = deepcopy(ev); altered.rows[0]['clock_valid'] = False
        self.assertIsNone(self.value(graph, altered)[0])
        self.assertIsNone(self.value(graph, ev, history_gate=lambda a, b: False)[0])
        altered = deepcopy(ev); altered.source.measures = tuple((t, (0, 0), k) for t, _, k in ev.source.measures)
        altered.source._metric_cache.clear()
        self.assertIsNone(self.value(graph, altered)[0])

    def test_compound_and_changing_meter(self):
        graph, ev = self.make(end=8)
        ev.source.measures = ((F(), (6, 8), None),); ev.source._measure_times = (F(),)
        self.assertEqual(self.value(graph, ev)[0], F(11, 16))
        ev.source.measures = ((F(), (4, 4), None), (F(4), (2, 2), None))
        ev.source._measure_times = (F(), F(4))
        ev.source._metric_cache.clear()
        self.assertEqual(self.value(graph, ev)[0], F(2, 3))

    def test_exact_fraction_and_octave_doublings_not_extra_credit(self):
        graph, ev = self.make(seventh_end=F(1, 3))
        doubled_graph, doubled = self.make(seventh_end=F(1, 3), extras=(('G4', 0, 4, 'g'), ('B4', 0, 4, 'b')))
        self.assertEqual(self.value(graph, ev)[0], F(2, 3))
        self.assertEqual(self.value(graph, ev)[0], self.value(doubled_graph, doubled)[0])

    def test_spelling_not_pitch_class_substitution(self):
        graph, ev = self.make(); row = next(r for r in ev.rows if r['token'] == ('F', 0))
        row['token'] = ('E', 1)
        self.assertEqual(self.value(graph, ev)[0], 0)

    def test_split_raw_edges_same_union_feature(self):
        graph, ev = self.make()
        edge = replace(graph.edges[0], signature=G7, group_id='whole', start_index=0, end_index=2, start=F(), end=F(4))
        graph = replace(graph, points=(F(), F(2), F(4)), edges=(edge,
            replace(edge, group_id='left', end_index=1, end=F(2)),
            replace(edge, group_id='right', start_index=1, start=F(2))))
        self.assertEqual(s.observe_path(graph, ev, ('whole',)), s.observe_path(graph, ev, ('left', 'right')))

    def test_random_releases_follow_declared_formula(self):
        rng = random.Random(93)
        for _ in range(25):
            release = F(rng.randrange(1, 49), 12)
            graph, ev = self.make(seventh_end=release)
            self.assertEqual(self.value(graph, ev)[0], max(F(), F(4)-release-1)/4)

    def test_invalid_span_rejected_and_source_not_mutated(self):
        graph, ev = self.make(); before = deepcopy(ev)
        for a, b in ((-1, 4), (1, 1), (0, 5)):
            with self.assertRaises(ValueError): s.observe(graph, ev, F(a), F(b), G7)
        self.value(graph, ev); self.assertEqual(ev.rows, before.rows)

    def test_positive_grace_does_not_manufacture_support_and_terminal_rest_is_not_triad(self):
        graph, ev = self.make()
        seventh = next(r for r in ev.rows if r['token'] == ('F', 0))
        seventh['end'] = seventh['start']
        self.assertEqual(self.value(graph, ev)[0], 0)
        graph, ev = problem(fixture([('F4', 0, 1, 's'), ('G3', 1, 2, 'b'),
            ('B3', 1, 2, 't'), ('D4', 1, 2, 'f')]))
        self.assertEqual(self.value(graph, ev)[0], 0)


if __name__ == '__main__': unittest.main()
