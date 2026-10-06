from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_terminal_context as s
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C, F64


def terminal_example():
    ir = fixture([('G3', 0, 3, 'bass'), ('C4', 0, 1, 'a'), ('B3', 1, 3, 'a'),
                  ('E4', 0, 1, 'b'), ('D4', 1, 3, 'b')], end=3)
    return problem(ir, end=1)


class TerminalContextTests(unittest.TestCase):
    def value(self, graph, ev, sig=F64, **kwargs):
        return s.observe(graph, ev, graph.points[0], graph.points[-1], sig, **kwargs)

    def test_original_following_notes_not_a_selected_successor(self):
        graph, ev = terminal_example(); values, r = self.value(graph, ev)
        self.assertEqual(values, dict.fromkeys(s.FEATURES, F(1)))
        self.assertFalse(r['selected_successor_used']); self.assertFalse(r['confirmed_cadence'])
        self.assertEqual(len(r['upper_event_pairs']), 2)
        self.assertEqual(graph.points[-1], 1)

    def test_literal_root_has_known_zero(self):
        graph, ev = terminal_example(); values, r = self.value(graph, ev, C)
        self.assertEqual(values, dict.fromkeys(s.FEATURES, F()))

    def test_nonterminal_uses_existing_selected_pair_only(self):
        graph, ev = terminal_example(); graph = replace(graph, points=(F(0), F(1), F(3)))
        values, r = s.observe(graph, ev, F(0), F(1), F64)
        self.assertEqual(values, dict.fromkeys(s.FEATURES, F()))

    def test_source_end_is_unknown_not_negative_evidence(self):
        graph, ev = terminal_example(); ev.rows = tuple(r for r in ev.rows if r['start'] < 1)
        for r in ev.rows: r['end'] = F(1)
        values, r = self.value(graph, ev)
        self.assertTrue(all(v is None for v in values.values()))

    def test_other_following_chord_not_forced_to_dominant(self):
        graph, ev = terminal_example()
        for r in ev.rows:
            if r['token'] == ('B', 0): r['token'] = ('B', -1)
        self.assertEqual(self.value(graph, ev)[0], dict.fromkeys(s.FEATURES, F()))

    def test_same_pc_different_spelling_not_equivalent_support(self):
        graph, ev = terminal_example()
        for r in ev.rows:
            if r['token'] == ('B', 0): r['token'] = ('C', -1)
        self.assertEqual(self.value(graph, ev)[0], dict.fromkeys(s.FEATURES, F()))

    def test_missing_bass_or_surface_support_stays_zero(self):
        graph, ev = terminal_example(); ev.rows = tuple(r for r in ev.rows if r['token'] != ('G', 0))
        self.assertEqual(self.value(graph, ev)[0], dict.fromkeys(s.FEATURES, F()))

    def test_no_unique_voice_paths_does_not_invent_steps(self):
        graph, ev = terminal_example(); ev.links = ()
        values, r = self.value(graph, ev)
        self.assertEqual(values[s.FEATURES[0]], 1); self.assertEqual(values[s.FEATURES[1]], 0)

    def test_unknown_meter_pitch_or_clock_not_imputed(self):
        graph, ev = terminal_example()
        self.assertTrue(all(v is None for v in self.value(graph, ev, history_gate=lambda a,b: False)[0].values()))
        unknown = deepcopy(ev); unknown.rows[0]['clock_valid'] = False
        self.assertTrue(all(v is None for v in self.value(graph, unknown)[0].values()))
        unknown = deepcopy(ev); unknown.source.measures = ((F(), (0, 0), None),)
        unknown.source._metric_cache.clear()
        self.assertTrue(all(v is None for v in self.value(graph, unknown)[0].values()))

    def test_exact_meter_change_and_compound_horizon(self):
        graph, ev = terminal_example()
        ev.source.measures = ((F(), (4, 4), None), (F(2), (2, 2), None))
        ev.source._measure_times = (F(), F(2)); ev.source._metric_cache.clear()
        self.assertEqual(s.horizon(ev.source, F(1), F(2)), 4)
        ev.source.measures = ((F(), (6, 8), None),); ev.source._measure_times = (F(),)
        ev.source._metric_cache.clear(); self.assertEqual(s.horizon(ev.source, F(1), F(2)), 4)

    def test_short_run_proportional_support_and_no_source_mutation(self):
        graph, ev = terminal_example(); before = deepcopy(ev.rows)
        values, r = s.observe(graph, ev, F(1, 2), F(1), F64)
        self.assertEqual(values[s.FEATURES[0]], F(1, 2)); self.assertEqual(ev.rows, before)

    def test_invalid_span(self):
        graph, ev = terminal_example()
        with self.assertRaises(ValueError): s.observe(graph, ev, F(-1), F(1), F64)
