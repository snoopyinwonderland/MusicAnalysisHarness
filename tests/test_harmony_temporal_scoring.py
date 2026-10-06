from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_temporal_scoring as temporal
from musicanote_harness import harmony_batched_frontier as old
from musicanote_harness import harmony_functional_scoring as functional
from musicanote_harness.harmony_evidence_scoring import run_features
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C, G, G7, F64, example


class TemporalScoringTests(unittest.TestCase):
    def test_index_matches_unindexed_every_interval(self):
        ir = fixture([("E3", 0, 3, "inner"), ("C3", 1, 2, "bass"), ("G3", 2, 3, "upper")], end=3)
        graph, ev = problem(ir, end=3); index = temporal.TemporalIndex(graph, ev.source)
        for i, a in enumerate(graph.points):
            for b in graph.points[i+1:]:
                for sig in (C, G, G7, (None, C[1])):
                    values, patterns = index.features(a, b, sig)
                    old_values, old_patterns = run_features(graph, ev.source, a, b, sig)
                    self.assertEqual(values, old_values | {"root_deferred_presence": temporal.deferred_root(graph, ev.source, a, b, sig)[0]})
                    self.assertEqual(patterns, old_patterns)

    def test_later_root_not_retroactive_evidence(self):
        graph, ev = problem(fixture([("E3", 0, 4, "inner"), ("C3", 2, 3, "bass")]))
        value, receipt = temporal.deferred_root(graph, ev.source, F(0), F(4), C)
        self.assertEqual(value, F(1, 2)); self.assertEqual(receipt[0]["delay_quarters"], {"numerator": 2, "denominator": 1})
        self.assertFalse(receipt[0]["root_attack_required"])

    def test_root_first_arpeggio_not_continuous_completeness(self):
        graph, ev = problem(fixture([("C3", 0, 1, "bass"), ("E3", 1, 2, "inner"), ("G3", 2, 4, "upper")]))
        self.assertEqual(temporal.deferred_root(graph, ev.source, F(0), F(4), C)[0], 0)

    def test_rootless_not_double_charged_or_rejected(self):
        graph, ev = problem(fixture([("E3", 0, 4, "inner"), ("G3", 0, 4, "upper")]))
        self.assertEqual(temporal.deferred_root(graph, ev.source, F(0), F(4), C), (F(), []))
        self.assertEqual(run_features(graph, ev.source, F(0), F(4), C)[0]["missing_root"], 1)

    def test_carried_root_counts_without_new_attack(self):
        graph, ev = problem(); shifted = replace(graph, points=(F(1), F(2), F(4)))
        self.assertEqual(temporal.deferred_root(shifted, ev.source, F(1), F(4), C)[0], 0)

    def test_unknown_spelling_and_root_stay_unavailable(self):
        graph, ev = problem()
        ev.source.events = (replace(ev.source.events[0], pitch=None),)+ev.source.events[1:]
        self.assertIsNone(temporal.deferred_root(graph, ev.source, F(0), F(4), C)[0])
        self.assertIsNone(temporal.deferred_root(graph, ev.source, F(0), F(4), (None, C[1]))[0])
        self.assertIsNone(temporal.TemporalIndex(graph, ev.source).features(F(0), F(4), C)[0]["root_deferred_presence"])

    def test_spelling_not_just_pitch_class(self):
        graph, ev = problem()
        ev.source.events = tuple(replace(e, pitch=("B", 1)) if e.pitch == ("C", 0) else e for e in ev.source.events)
        self.assertEqual(temporal.deferred_root(graph, ev.source, F(0), F(4), C), (F(), []))

    def test_meter_relative_not_absolute_shortness(self):
        _, ev = problem(); source = ev.source
        self.assertEqual(temporal.beat_extent(source, F(0), F(1, 4)), F(1, 4))
        source.measures = tuple((t, (3, 8), k) for t, m, k in source.measures); source._metric_cache.clear()
        self.assertEqual(temporal.beat_extent(source, F(0), F(1, 4)), F(1, 2))
        source.measures = tuple((t, (6, 8), k) for t, m, k in source.measures); source._metric_cache.clear()
        self.assertEqual(temporal.beat_extent(source, F(0), F(1, 4)), F(1, 6))

    def test_changing_meter_integrated_and_unknown_not_zero(self):
        _, ev = problem(fixture(end=8), end=8); s = ev.source
        s.measures = ((F(0), (4, 4), 0), (F(4), (2, 2), 0)); s._metric_cache.clear()
        self.assertEqual(temporal.beat_extent(s, F(3), F(6)), 2)
        s.measures = (); s._measure_times = (); s._metric_cache.clear()
        self.assertIsNone(temporal.beat_extent(s, F(0), F(1)))
        with self.assertRaisesRegex(ValueError, "invalid_temporal_span"): temporal.beat_extent(s, F(1), F(1))

    def test_short_resolution_credit_softly_attenuated(self):
        _, _, _, _, ev = example()
        original, _ = functional.pair_features(ev, F(0), F(1), F(2), F64, G)
        # A left run starting halfway through the held preparation has half a
        # notated beat of support, but is NOT removed as an invalid short chord.
        raw, _ = functional.pair_features(ev, F(1, 2), F(1), F(2), F64, G)
        graded, details = temporal.resolution_features(ev, F(1, 2), F(1), F(2), F64, G)
        self.assertEqual(graded, {k:v/2 for k,v in raw.items()})
        self.assertTrue(original["six_four_surface_and_held_bass"])
        self.assertFalse(details[-1]["short_chord_rejected"])

    def test_long_resolution_credit_does_not_grow_unbounded(self):
        _, _, _, _, ev = example()
        values, _ = temporal.resolution_features(ev, F(0), F(1), F(2), F64, G)
        self.assertEqual(values, functional.pair_features(ev, F(0), F(1), F(2), F64, G)[0])

    def test_unknown_meter_retains_old_bounded_credit(self):
        _, _, _, _, ev = example(); ev.source.measures = (); ev.source._measure_times = (); ev.source._metric_cache.clear()
        values, details = temporal.resolution_features(ev, F(0), F(1), F(2), F64, G)
        self.assertEqual(values, functional.pair_features(ev, F(0), F(1), F(2), F64, G)[0])
        self.assertFalse(details[-1]["meter_available"])

    def test_baseline_arm_exact_old_selected(self):
        graph, ev = problem()
        self.assertEqual(temporal.decode(graph, ev, arm="baseline")["selected"], old.decode(graph, ev)["selected"])

    def test_private_binding_no_module_globals_or_original_functions_changed(self):
        old_pair = functional.pair_features; old_decode = old.decode; old_run = functional.run_features
        graph, ev = problem(); temporal.decode(graph, ev)
        self.assertIs(functional.pair_features, old_pair); self.assertIs(old.decode, old_decode)
        self.assertIs(functional.run_features, old_run)
        self.assertIs(old.decode.__globals__["pair_features"], old_pair)

    def test_nested_binding_verifies_dependencies(self):
        with self.assertRaisesRegex(ValueError, "not_used"): temporal.bind(functional.decode, {"invented": 1})
        with self.assertRaisesRegex(ValueError, "unsupported"): temporal.bind(123, {})
        self.assertIsNot(temporal.make_decoder("combined"), old.decode)

    def test_invalid_arm_and_budget_and_nonready(self):
        graph, ev = problem()
        with self.assertRaisesRegex(ValueError, "unknown_temporal_arm"): temporal.decode(graph, ev, arm="invented")
        for cap in (0, True, 1.5):
            with self.assertRaisesRegex(ValueError, "invalid_transition_budget"): temporal.decode(graph, ev, transition_budget=cap)
        got = temporal.decode(graph, ev, transition_budget=1)
        self.assertIsNone(got["selected"]); self.assertFalse(got["exact_optimum_under_declared_score"])
        self.assertEqual(temporal.decode(replace(graph, status="source_failure"), ev)["status"], "source_failure")

    def test_functional_disabled_and_source_objects_preserved(self):
        graph, ev = problem(); before = deepcopy(ev.source.events)
        got = temporal.decode(graph, ev, functional_evidence=False)
        ids = tuple(e["semantic_group_ref"] for e in got["selected"]["segments"])
        self.assertEqual(F(**got["selected"]["score_cost"]), temporal.score_path(graph, ev, ids, functional_evidence=False))
        self.assertEqual(ev.source.events, before); self.assertFalse(got["selected"]["human_validated"])

    def test_all_arms_tiny_dags_exact_cost_and_lex_path(self):
        graph, ev = problem(fixture([("E3", 0, 3, "inner"), ("C3", 1, 2, "bass"), ("G3", 2, 3, "upper")], end=3), end=3)
        choices = tuple(e for e in graph.edges if e.signature in (C, G)); rng = random.Random(63819)
        for _ in range(20):
            edges = tuple(e for e in choices if rng.random() < .7)
            tiny = replace(graph, edges=edges, max_segments=rng.choice((1, 2, 3, 4, 6)))
            for arm in temporal.ARMS:
                paths = []
                def visit(index, ids):
                    if index == len(tiny.points)-1:
                        paths.append((temporal.score_path(tiny, ev, ids, arm=arm), ids)); return
                    if len(ids) >= tiny.max_segments: return
                    for e in tiny.edges:
                        if e.start_index == index: visit(e.end_index, ids+(e.group_id,))
                visit(0, ())
                selected = temporal.decode(tiny, ev, arm=arm)["selected"]
                if not paths: self.assertIsNone(selected); continue
                ids = tuple(s["semantic_group_ref"] for s in selected["segments"])
                self.assertEqual((F(**selected["score_cost"]), ids), min(paths))


if __name__ == "__main__": unittest.main()
