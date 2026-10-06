from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest
from musicanote_harness import harmony_member_timing as s
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C, G, G7

BROAD = (('G', 0), (('B', 0), ('C', 0), ('D', 0), ('F', 0), ('G', 0)))


def late_specs():
    return [('G3', 0, 8, 'b'), ('B3', 0, 8, 'third'), ('D4', 0, 8, 'fifth'), ('F4', 4, 8, 'seventh')]


class TimingTests(unittest.TestCase):
    def value(self, graph, ev, a, b, sig, **args):
        context = s.TimingContext(ev, **args)
        return s.timing_feature(graph, ev.source, F(a), F(b), sig, context=context)

    def test_late_seventh_not_backdated(self):
        graph, ev = problem(fixture(late_specs(), end=8), end=8)
        value, receipt = self.value(graph, ev, 0, 8, G7)
        self.assertEqual(value, F(3, 16))  # (4beats-1)/8beats / two identifying roles
        seventh = next(r for r in receipt if r['role'] == 'seventh')
        self.assertEqual(seventh['first_positive_time'], s.support.q(4))
        self.assertTrue(seventh['arrival_event_ids']); self.assertFalse(seventh['forced_boundary'])
        self.assertFalse(seventh['later_member_proves_earlier_sounding'])

    def test_one_beat_distributed_entry_allowed_not_all_members_simultaneous(self):
        ir = fixture([('G3', 0, F(1, 2), 'v'), ('B3', F(1, 2), 1, 'v'),
                      ('D4', 1, F(3, 2), 'v'), ('F4', F(3, 4), 4, 's')])
        graph, ev = problem(ir)
        self.assertEqual(self.value(graph, ev, 0, 4, G7)[0], 0)

    def test_absence_not_charged_twice_and_release_not_continuity_penalty(self):
        graph, ev = problem(fixture([('G3', 0, 4, 'b'), ('B3', 0, F(1, 2), 't'), ('D4', 0, 4, 'f')]))
        value, receipt = self.value(graph, ev, 0, 4, G7)
        self.assertEqual(value, 0); self.assertTrue(receipt[-1]['member_never_observed'])

    def prepared_case(self, **args):
        ir = fixture([('C3', 0, 5, 'b'), ('G3', 0, 5, 'f'), ('D4', 0, 3, 'lead'), ('E4', 3, 5, 'lead')], end=5)
        graph, ev = problem(ir, end=5)
        return graph, ev, self.value(graph, ev, 1, 5, C, **args)

    def test_prepared_step_halves_cost_without_nct_confirmation(self):
        graph, ev, (v, receipts) = self.prepared_case()
        self.assertEqual(v, F(1, 10))
        self.assertEqual(len(receipts[0]['prepared_resolution_candidates']), 1)
        self.assertFalse(receipts[0]['confirmed_nct'])

    def test_repeat_history_barrier_withholds_discount(self):
        _, _, (v, receipts) = self.prepared_case(context_barriers=(F(2),))
        self.assertEqual(v, F(1, 5)); self.assertFalse(receipts[0]['prepared_resolution_candidates'])

    def test_grace_and_invalid_source_history_withhold_discount(self):
        graph, ev, _ = self.prepared_case(); lane = next(r['identity'] for r in ev.rows if r['token'] == ('E', 0))
        grace = {'part_id': lane[0], 'voice_id': lane[1], 'global_onset_quarter': s.support.q(2)}
        for args in ({'grace_notes': (grace,)}, {'history_gate': lambda a, b: False}):
            self.assertEqual(self.value(graph, ev, 1, 5, C, **args)[0], F(1, 5))

    def test_after_boundary_step_and_wrong_voice_not_preparation(self):
        for start, voice in ((1, 'lead'), (0, 'other')):
            graph, ev = problem(fixture([('C3', 0, 5, 'b'), ('G3', 0, 5, 'f'),
                ('D4', start, 3, voice), ('E4', 3, 5, 'lead')], end=5), end=5)
            self.assertEqual(self.value(graph, ev, 1, 5, C)[0], F(1, 5))

    def test_unequal_overlap_not_false_preparation(self):
        graph, ev = problem(fixture([('C3', 0, 5, 'b'), ('G3', 0, 5, 'f'),
            ('D4', 0, 3, 'lead'), ('F4', 1, 4, 'lead'), ('E4', 3, 5, 'lead')], end=5), end=5)
        self.assertEqual(self.value(graph, ev, 1, 5, C)[0], F(1, 5))

    def test_compound_and_changing_meter(self):
        graph, ev = problem(fixture(late_specs(), end=8), end=8)
        ev.source.measures = tuple((t, (6, 8), key) for t, _, key in ev.source.measures)
        ev.source._metric_cache.clear()
        self.assertEqual(self.value(graph, ev, 0, 8, G7)[0], F(5, 32))
        # Change at q4: four quarter beats, then two half-note beats.
        ev.source.measures = tuple((t, (4, 4) if t == 0 else (2, 2), key)
                                  for t, _, key in ev.source.measures)
        ev.source._metric_cache.clear()
        self.assertEqual(self.value(graph, ev, 0, 8, G7)[0], F(1, 4))
        selected = s.Scorer(graph, ev, s.ZERO | {s.FEATURE: F(1, 3)}).decode()['selected']
        self.assertIsNotNone(selected)  # exact integer scale includes beat normalization

    def test_unknown_meter_shape_and_spelling_remain_unavailable(self):
        graph, ev = problem()
        self.assertIsNone(self.value(graph, ev, 0, 4, BROAD)[0])
        self.assertIsNone(self.value(graph, ev, 0, 4, (None, C[1]))[0])
        ev.source.measures = (); ev.source._measure_times = (); ev.source._metric_cache.clear()
        self.assertIsNone(self.value(graph, ev, 0, 4, C)[0])

    def test_spelling_and_halfopen_tie_onset(self):
        graph, ev = problem(fixture([('G3', 0, 4, 'b'), ('B3', 0, 4, 't'),
            ('D4', 0, 4, 'f'), ('E#4', 2, 4, 's')]))
        self.assertEqual(self.value(graph, ev, 0, 4, G7)[0], 0)  # F never observed, absence handled separately
        self.assertTrue(self.value(graph, ev, 0, 4, G7)[1][-1]['member_never_observed'])
        graph, ev = problem(fixture(late_specs(), end=8), end=8)
        self.assertEqual(self.value(graph, ev, 0, 4, G7)[0], 0)  # arrival at end excluded
        self.assertEqual(self.value(graph, ev, 4, 8, G7)[0], 0)  # already sounding / actual onset included

    def test_direct_indexed_and_partition_invariance_source_preserved(self):
        ir = fixture(late_specs(), end=8); before = deepcopy(ir); graph, ev = problem(ir, end=8)
        scorer = s.Scorer(graph, ev, s.ZERO | {s.FEATURE: F(1, 2)})
        for i, a in enumerate(graph.points):
            for b in graph.points[i+1:]:
                for sig in (C, G7, BROAD):
                    self.assertEqual(scorer.member_features(graph, ev.source, a, b, sig)[0],
                        scorer.member_features(graph, ev.source, a, b, sig, index=scorer.index)[0])
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        whole = (by[F(), F(8), G7],); split = (by[F(), F(4), G7], by[F(4), F(8), G7])
        self.assertEqual(scorer.path_features(whole), scorer.path_features(split))
        self.assertEqual(scorer.score_path(whole), scorer.score_path(split)); self.assertEqual(ir, before)

    def test_zero_weight_exact_step67_control_and_tiny_exhaustive(self):
        graph, ev = problem(); fixed = {k: F(1, 3) for k in s.support.FEATURES}
        old = s.support.Scorer(graph, ev, fixed).decode()['selected']
        new = s.Scorer(graph, ev, fixed | {s.FEATURE: F()}).decode()['selected']
        self.assertEqual(old['segments'], new['segments']); self.assertEqual(old['score_cost'], new['score_cost'])
        rng = random.Random(6901)
        for _ in range(5):
            tiny = replace(graph, edges=tuple(e for e in graph.edges if e.signature in (C, G) and rng.random() < .6), max_segments=3)
            scorer = s.Scorer(tiny, ev, {k: F(rng.randrange(4), 4) for k in s.FEATURES}); paths = []
            def visit(i, ids):
                if i == len(tiny.points)-1: paths.append((scorer.score_path(ids), ids)); return
                if len(ids) >= tiny.max_segments: return
                for e in tiny.edges:
                    if e.start_index == i: visit(e.end_index, ids+(e.group_id,))
            visit(0, ()); chosen = scorer.decode()['selected']
            if not paths: self.assertIsNone(chosen); continue
            self.assertEqual((s.support.f(chosen['score_cost']), tuple(x['semantic_group_ref'] for x in chosen['segments'])), min(paths))

    def test_invalid_coefficients_and_span(self):
        for v in (True, .1, F(-1), F(2)):
            with self.assertRaises(ValueError): s.coefficients(s.ZERO | {s.FEATURE: v})
        graph, ev = problem()
        with self.assertRaises(ValueError): self.value(graph, ev, 0, 0, C)
