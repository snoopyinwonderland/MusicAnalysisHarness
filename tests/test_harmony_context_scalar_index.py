from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest
from types import SimpleNamespace

from musicanote_harness import harmony_context_scalar_index as scalar
from test_harmony_context_joint_decoder import toy, paths, scorer, joint, old, C, G, FM
from test_harmony_context_competition_v2 import extended_passing
from test_harmony_context_competition import neighbor


def fast(graph, ev, extra, weights=None, **kw):
    return scalar.Scorer(old.Scorer(graph, ev, weights or old.initial_weights(old.fresh.timing.ZERO)), extra, **kw)


def profile_only(graph, ev):
    original = SimpleNamespace(problem=graph, ev=ev)
    return joint.Scorer(original, joint.ZERO), scalar.Scorer(original, joint.ZERO)


class ScalarIndexTests(unittest.TestCase):
    def compare_values(self, slow, quick, ids):
        runs = joint.context_features.control.completed_runs(slow.problem, ids)
        for i in range(1, len(runs)):
            a = slow.transition_profile(runs, i); b = quick.scalar_values(runs, i)
            self.assertEqual({k: joint.f(v) for k, v in a['observed_feature_sums'].items()}, b['observed_feature_sums'])
            self.assertEqual(a['availability'], b['availability'])
            self.assertEqual({k: None if v is None else joint.f(v) for k, v in a['features'].items()}, b['features'])
            self.assertEqual(slow.transition_cost(runs, i), quick.transition_cost(runs, i))

    def test_all_tiny_path_values_signed_weights_and_exhaustive_winner(self):
        graph, ev, _ = toy(cap=3); rng = random.Random(8101)
        for _ in range(4):
            extra = {k: rng.choice((F(-2), F(), F(1, 7), F(2))) for k in joint.FEATURES}
            sub = replace(graph, edges=tuple(e for e in graph.edges if rng.random() < .8))
            slow, quick = scorer(sub, ev, extra=extra), fast(sub, ev, extra)
            candidates = paths(sub)
            for ids in candidates: self.compare_values(slow, quick, ids)
            expected = min((slow.score_path(ids), ids) for ids in candidates)
            r = quick.decode(force_delayed=True)
            self.assertEqual((joint.f(r['selected']['score_cost']), old.fresh.path_ids(r['selected'])), expected)
            self.assertEqual(r['selected']['context_score'], slow.path_receipt(expected[1]))

    def test_future_signature_is_projection_only_but_end_is_not(self):
        graph, ev, _ = toy(); extra = dict.fromkeys(joint.FEATURES, F(1))
        slow, quick = scorer(graph, ev, extra=extra), fast(graph, ev, extra)
        a = ((F(0), F(1), C), (F(1), F(2), FM), (F(2), F(3), C))
        b = a[:2]+((F(2), F(3), G),)
        self.assertEqual(quick.scalar_values(a, 1), quick.scalar_values(b, 1))
        self.assertEqual(slow.transition_cost(a, 1), quick.transition_cost(b, 1))
        c = a[:2]+((F(2), F(5, 2), G),)
        self.assertNotEqual(quick.scalar_values(a, 1), quick.scalar_values(c, 1))
        self.assertEqual(slow.transition_cost(c, 1), quick.transition_cost(c, 1))

    def test_unknown_voice_clock_pitch_and_bass_not_scored_as_partial(self):
        for field, value in (('identity', None), ('clock_valid', False)):
            graph, ev, _ = toy(); ev.rows[1][field] = value
            slow, quick = scorer(graph, ev), fast(graph, ev, joint.ZERO)
            for ids in paths(replace(graph, max_segments=2)): self.compare_values(slow, quick, ids)
        graph, ev, _ = toy(); missing = ev.source.events[1]
        ev.source.events = tuple(replace(e, pitch=None) if e.event_id == missing.event_id else e for e in ev.source.events)
        slow, quick = scorer(graph, ev), fast(graph, ev, joint.ZERO)
        for ids in paths(replace(graph, max_segments=2)): self.compare_values(slow, quick, ids)
        graph, ev, _ = toy(); ev.rows = ev.rows[:1]+ev.rows[2:]
        slow, quick = scorer(graph, ev), fast(graph, ev, joint.ZERO)
        for ids in paths(replace(graph, max_segments=2)): self.compare_values(slow, quick, ids)

    def test_meter_history_gate_grace_and_overlap_ambiguity(self):
        graph, ev, _ = toy(); ev.source.measures += ((F(2), (6, 8), None),)
        ev.source._measure_times += (F(2),); ev.source._metric_cache.clear()
        for kwargs in ({}, {'context_barriers': (F(3, 2),)}, {'history_gate': lambda a, b: False},
                       {'grace_notes': ({'part_id': ev.rows[1]['identity'][0],
                                         'voice_id': ev.rows[1]['identity'][1], 'global_onset_quarter': joint.q(F(3, 2))},)}):
            slow, quick = scorer(graph, ev, **kwargs), fast(graph, ev, joint.ZERO, **kwargs)
            for ids in paths(replace(graph, max_segments=2)): self.compare_values(slow, quick, ids)
        for sc in (slow, quick): sc.context.ambiguous.add(ev.rows[1]['id'])
        for ids in paths(replace(graph, max_segments=2)): self.compare_values(slow, quick, ids)

    def test_split_invariance_terminal_flush_and_all_dp_counters(self):
        notes = [(p, i, i+1, 'lead') for i, p in enumerate(('E4', 'F4', 'E4', 'D4', 'E4', 'F4'))]
        graph, ev, _ = toy(notes+[('C3', 0, 6, 'bass')], end=6, signatures=(C, FM), cap=6)
        graph = replace(graph, edges=tuple(e for e in graph.edges if e.end-e.start <= 2))
        extra = {k: F(-1 if i % 2 else 1, 3) for i, k in enumerate(joint.FEATURES)}
        slow, quick = scorer(graph, ev, extra=extra), fast(graph, ev, extra)
        a, b = slow.decode(force_delayed=True), quick.decode(force_delayed=True)
        self.assertEqual(a['selected'], b['selected']); self.assertEqual(a['transitions'], b['transitions'])
        self.assertEqual(a['search_diagnostics'], b['search_diagnostics'])
        for ids in paths(graph): self.compare_values(slow, quick, ids)

    def test_ties_fractional_silence_and_clipped_source_sounds(self):
        notes = [('E4', 0, F(1, 3), 'lead'), ('F4', F(1, 3), F(2, 3), 'lead'),
                 ('E4', F(2, 3), F(5, 3), 'lead'), ('G4', 2, 5, 'lead'), ('C3', 0, 4, 'bass')]
        graph, ev, _ = toy(notes, cap=2)
        slow, quick = scorer(graph, ev), fast(graph, ev, joint.ZERO)
        for ids in paths(graph): self.compare_values(slow, quick, ids)
        local = ((F(1, 6), F(1, 2), C), (F(1, 2), F(5, 2), FM), (F(5, 2), F(7, 2), G))
        for i in (1, 2):
            a, b = slow.transition_profile(local, i), quick.scalar_values(local, i)
            self.assertEqual({k: joint.f(v) for k, v in a['observed_feature_sums'].items()}, b['observed_feature_sums'])
            self.assertEqual(a['availability'], b['availability'])

    def test_budget_no_path_zero_delegate_and_no_mutation(self):
        graph, ev, ir = toy(cap=3); before = deepcopy((graph, ir, old.BASE_WEIGHTS, old.PAIR_WEIGHTS))
        extra = dict.fromkeys(joint.FEATURES, F(1, 7))
        r = fast(graph, ev, extra).decode(transition_budget=1)
        self.assertIsNone(r['selected']); self.assertFalse(r['exact_optimum_under_declared_score'])
        z = fast(graph, ev, joint.ZERO).decode()
        self.assertEqual(z['selected'], scorer(graph, ev).decode()['selected'])
        graph2 = replace(graph, edges=tuple(e for e in graph.edges if e.end-e.start == 1), max_segments=2)
        self.assertIsNone(fast(graph2, ev, extra).decode()['selected'])
        self.assertEqual(before, (graph, ir, old.BASE_WEIGHTS, old.PAIR_WEIGHTS))

    def test_nonzero_resolution_credit_and_partial_known_unknown(self):
        for build in (neighbor, extended_passing, lambda: neighbor((('x', ('A', 0), 1, F(3, 2), 57, None),))):
            graph, ev, ids = build(); slow, quick = profile_only(graph, ev)
            self.compare_values(slow, quick, ids)
            runs = joint.context_features.control.completed_runs(graph, ids)
            c = quick.scalar_values(runs, 1)
            self.assertGreater(c['observed_feature_sums']['dominant_credit_with_hold_conflict'], 0)
            if any(r['identity'] is None for r in ev.rows):
                self.assertIsNone(c['features']['hold_explained_step_exposure'])
                self.assertGreater(c['observed_feature_sums']['hold_explained_step_exposure'], 0)

    def test_unknown_meter_and_duplicate_figures_do_not_inflate_credit(self):
        graph, ev, ids = neighbor(); ev.source.measures = ((F(0), (None, 4), None),)
        slow, quick = profile_only(graph, ev)
        slow.context.figures *= 3; quick.context.figures *= 3
        self.compare_values(slow, quick, ids)
        runs = joint.context_features.control.completed_runs(graph, ids)
        self.assertIsNone(quick.scalar_values(runs, 1)['features']['dominant_credit_with_hold_conflict'])

    def test_equal_cost_lexical_tie_duplicate_and_coarse_grid(self):
        graph, ev, _ = toy(cap=2)
        graph = replace(graph, edges=(replace(graph.edges[0], group_id='000-duplicate'),)+graph.edges)
        weights = old.initial_weights(old.fresh.timing.ZERO)
        for k in old.TRAINABLE: weights[k] = max(old.bounds(k)[0], F())
        for extra in (joint.ZERO, dict.fromkeys(joint.FEATURES, F(1, 3))):
            slow, quick = scorer(graph, ev, weights, extra), fast(graph, ev, extra, weights)
            self.assertEqual(slow.decode(force_delayed=True)['selected'], quick.decode(force_delayed=True)['selected'])
        kept = (F(0), F(2), F(4))
        coarse = replace(graph, points=kept, edges=tuple(replace(e, start_index=kept.index(e.start), end_index=kept.index(e.end))
            for e in graph.edges if e.start in kept and e.end in kept))
        slow, quick = scorer(coarse, ev), fast(coarse, ev, joint.ZERO)
        for ids in paths(coarse): self.compare_values(slow, quick, ids)

    def test_bad_geometry_and_different_context_semantics_rejected(self):
        graph, ev, _ = toy(); quick = fast(graph, ev, joint.ZERO)
        for runs in (((F(0), F(1), C), (F(2), F(3), FM)),
                     ((F(-1), F(1), C), (F(1), F(2), FM))):
            with self.assertRaises(ValueError): quick.scalar_values(runs, 1)
        class Other(joint.context_features.Context): pass
        quick = fast(graph, ev, joint.ZERO, context=Other(ev))
        with self.assertRaises(ValueError): quick.scalar_values(((F(0), F(1), C), (F(1), F(2), FM)), 1)


if __name__ == '__main__': unittest.main()
