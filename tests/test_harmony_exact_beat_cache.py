from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_exact_beat_cache as c
from musicanote_harness import harmony_temporal_scoring as original
from musicanote_harness import harmony_context_joint_decoder as joint
from test_harmony_member_role_scoring import toy, paths, C, G, FM
from test_harmony_member_role_scoring import by_path
from test_harmony_score_balance_ledger import fixture
from test_harmony_functional_scoring import example, F64


class ExactBeatCacheTests(unittest.TestCase):
    def test_exact_all_intervals_and_repeat_hits(self):
        _, ev, _ = toy(); cache = c.BeatCache(ev.source)
        for a in (F(0), F(1, 3), F(1), F(2)):
            for b in (F(7, 3), F(3), F(4)):
                expected = original.beat_extent(ev.source, a, b)
                self.assertEqual(cache.extent(ev.source, a, b), expected)
                self.assertEqual(cache.extent(ev.source, a, b), expected)
        self.assertEqual(cache.stats, dict(calls=24, hits=12, integrations=12))

    def test_changing_compound_and_unknown_meter_not_zero(self):
        _, ev, _ = toy(end=8); source = ev.source
        source.measures = ((F(0), (6, 8), None), (F(3), (2, 2), None))
        source._measure_times = (F(0), F(3)); source._metric_cache.clear()
        cache = c.BeatCache(source)
        self.assertEqual(cache.extent(source, F(0), F(7)), F(4))
        source.measures = ((F(0), (None, 8), None),); source._measure_times = (F(0),)
        source._metric_cache.clear(); cache = c.BeatCache(source)
        self.assertIsNone(cache.extent(source, F(0), F(3)))
        self.assertIsNone(cache.extent(source, F(0), F(3)))
        self.assertEqual(cache.stats['hits'], 1)

    def test_wrong_source_changed_meter_and_bad_span_rejected(self):
        _, ev, _ = toy(); source = ev.source; cache = c.BeatCache(source)
        cache.extent(source, F(0), F(1))
        with self.assertRaisesRegex(ValueError, 'source_or_meter'): cache.extent(deepcopy(source), F(0), F(1))
        for a, b in ((F(1), F(1)), (F(2), F(1))):
            with self.assertRaisesRegex(ValueError, 'invalid_temporal_span'): cache.extent(source, a, b)
        source.measures = ()
        with self.assertRaisesRegex(ValueError, 'source_or_meter'): cache.extent(source, F(0), F(1))

    def test_resolution_values_and_details_exact_for_different_hypotheses(self):
        _, _, _, _, ev = example(); cache = c.BeatCache(ev.source)
        for left, right in ((F64, G), (C, G), (G, C), (C, FM)):
            for start in (F(0), F(1, 2)):
                args = ev, start, F(1), F(2), left, right
                self.assertEqual(cache.resolution(*args), original.resolution_features(*args))
        self.assertEqual(cache.stats['integrations'], 2)
        self.assertEqual(cache.stats['hits'], 6)
        before = deepcopy(cache.stats)
        self.assertEqual(cache.resolution(ev, F(0), F(1), F(2), F64, G, attenuate=False),
                         original.resolution_features(ev, F(0), F(1), F(2), F64, G, attenuate=False))
        self.assertEqual(cache.stats, before)
        with self.assertRaisesRegex(ValueError, 'evidence_source'): cache.resolution(deepcopy(ev), F(0), F(1), F(2), F64, G)

    def test_unknown_meter_resolution_retains_old_credit_and_receipt(self):
        _, _, _, _, ev = example(); ev.source.measures = (); ev.source._measure_times = ()
        ev.source._metric_cache.clear(); cache = c.BeatCache(ev.source)
        args = ev, F(0), F(1), F(2), F64, G
        self.assertEqual(cache.resolution(*args), original.resolution_features(*args))
        self.assertIsNone(cache.values[F(0), F(1)])

    def test_all_tiny_paths_features_masks_cost_and_exact_winner_unchanged(self):
        graph, ev, ir = toy(notes=[('C3', 0, 3, 'bass'), ('E4', 0, 1, 'lead'),
                                  ('F4', 1, 2, 'lead'), ('E4', 2, 3, 'lead')], end=3, cap=3)
        before = deepcopy((graph, ir)); rng = random.Random(9001)
        for j in range(3):
            weights = fixture()[2]
            for k in c.full35.ledger.context.FEATURES: weights[k] = rng.choice((F(-1, 3), F(), F(1, 3)))
            for k in c.full35.ledger.role.FEATURES: weights[k] = rng.choice((F(-1, 2), F(), F(1, 2)))
            old = c.full35.Scorer(graph, ev, weights); new = c.Scorer(graph, ev, weights)
            for ids in paths(graph):
                runs = joint.context_features.control.completed_runs(graph, ids)
                for i in range(1, len(runs)):
                    self.assertEqual(old.scalar_values(runs, i), new.scalar_values(runs, i))
                    self.assertEqual(old.role_index.observe(runs, i), new.role_index.observe(runs, i))
                    self.assertEqual(old.transition_cost(runs, i), new.transition_cost(runs, i))
                self.assertEqual(old.path_receipt(ids), new.path_receipt(ids))
            a, b = old.decode(force_delayed=True), new.decode(force_delayed=True)
            self.assertEqual(a['selected'], b['selected'])
            self.assertEqual(a['search_diagnostics'], b['search_diagnostics'])
            self.assertEqual(a['transitions'], b['transitions'])
        self.assertEqual((graph, ir), before)

    def test_private_bindings_do_not_modify_sealed_globals_or_bytecode(self):
        graph, ev, _ = toy(); old_pair = original.resolution_features
        old_extent = original.beat_extent; old_decode = joint.Scorer._delayed
        old_values = c.scalar.ScalarIndex.values
        new = c.Scorer(graph, ev, fixture()[2]); new.decode()
        self.assertIs(original.resolution_features, old_pair); self.assertIs(original.beat_extent, old_extent)
        self.assertIs(joint.Scorer._delayed, old_decode); self.assertIs(c.scalar.ScalarIndex.values, old_values)
        self.assertIs(new._cached_delayed.__func__.__code__, old_decode.__code__)
        self.assertIs(new.beat_cache._resolution.__code__, old_pair.__code__)
        self.assertIs(old_decode.__globals__['resolution_features'], old_pair)
        self.assertIs(old_values.__globals__['resolution_features'], old_pair)

    def test_budget_abstention_no_partial_winner_and_instance_isolation(self):
        graph, ev, _ = toy(); a = c.Scorer(graph, ev, fixture()[2]); b = c.Scorer(graph, ev, fixture()[2])
        self.assertIsNone(a.decode(transition_budget=1)['selected'])
        a.beat_cache.extent(ev.source, F(0), F(1))
        self.assertEqual(b.beat_cache.values, {})
        for budget in (0, True, 1.5):
            with self.assertRaisesRegex(ValueError, 'invalid_transition_budget'): b.decode(transition_budget=budget)

    def test_saved_path_replay_checks_pair_cost_and_projections(self):
        from musicanote_harness.harmony_exact_beat_replay import check_path
        graph, ev, _ = toy(); weights = fixture()[2]
        old, new = c.full35.Scorer(graph, ev, weights), c.Scorer(graph, ev, weights)
        ids = by_path(graph, ((0, 2, C), (2, 4, FM)))
        receipt, count = check_path(old, new, ids, target=True)
        self.assertEqual(receipt, old.path_receipt(ids, target=True)); self.assertEqual(count, 1)
        self.assertFalse(receipt['source_labels_used'])

    def test_zero_grace_and_unavailable_voice_preserve_scalar_and_role_masks(self):
        graph, ev, _ = toy(); base = ev.source.events[0]
        ev.source.events += (replace(base, event_id='grace_cache_test', start=F(3, 2), end=F(3, 2)),)
        ev.rows[1]['clock_valid'] = False
        weights = fixture()[2]; old = c.full35.Scorer(graph, ev, weights); new = c.Scorer(graph, ev, weights)
        runs = ((F(0), F(1), C), (F(1), F(4), FM))
        self.assertEqual(old.scalar_values(runs, 1), new.scalar_values(runs, 1))
        self.assertEqual(old.role_index.observe(runs, 1), new.role_index.observe(runs, 1))
        self.assertIsNone(new.role_index.observe(runs, 1)['features'][c.full35.ledger.role.FEATURES[0]])
        self.assertNotIn((F(3, 2), F(3, 2)), new.beat_cache.values)


if __name__ == '__main__': unittest.main()
