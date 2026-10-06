from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_context_scalar_trial as t
from test_harmony_context_scalar_index import fast, toy, joint


class ScalarTrialTests(unittest.TestCase):
    def test_guard_covers_lazy_index_and_restores_all_hooks(self):
        graph, ev, _ = toy(); sc = fast(graph, ev, dict.fromkeys(joint.FEATURES, F(1, 3)))
        before = (sc.original.source_scorer.base_run, sc.original.source_scorer.member_features,
                  sc.transition_profile, sc.scalar_values)
        ticks = iter(range(10000))
        r = t.select(sc, 'test-model', wall_seconds=15, timer=lambda: next(ticks))
        self.assertIsNone(r['selected']); self.assertFalse(r['exact_optimum_under_declared_score'])
        self.assertFalse(r['partial_winner_returned']); self.assertIsNone(r['transitions'])
        self.assertEqual(before, (sc.original.source_scorer.base_run, sc.original.source_scorer.member_features,
                                  sc.transition_profile, sc.scalar_values))

    def test_complete_result_and_tiny_budget_keep_original_contract(self):
        graph, ev, _ = toy(); extra = dict.fromkeys(joint.FEATURES, F(1, 3))
        a = t.select(fast(graph, ev, extra), 'test-model', timer=lambda: 0)
        b = t.select(fast(graph, ev, extra), 'test-model', timer=lambda: 0, transition_budget=1)
        self.assertIsNotNone(a['selected']); self.assertTrue(a['exact_optimum_under_declared_score'])
        self.assertIsNone(b['selected']); self.assertEqual(b['status'], 'transition_budget_abstention')
        self.assertFalse(a['frozen_model_ref']['fit_performed_this_run'])

    def test_clock_scalar_hook_and_exception_restoration(self):
        graph, ev, _ = toy(); sc = fast(graph, ev, dict.fromkeys(joint.FEATURES, F(1)))
        previous = sc.scalar_values
        def failure(*a, **kw): raise RuntimeError('synthetic_scalar_failure')
        sc.scalar_values = failure
        with self.assertRaisesRegex(RuntimeError, 'synthetic_scalar_failure'):
            t.select(sc, 'test-model', timer=lambda: 0)
        self.assertIs(sc.scalar_values, failure)
        sc.scalar_values = previous
        for wall in (0, -1, True, None):
            with self.assertRaises(ValueError): t.select(sc, 'test-model', wall_seconds=wall)

    def test_compatibility_rejects_changed_winner_or_operation_count(self):
        graph, ev, _ = toy(); extra = dict.fromkeys(joint.FEATURES, F(1, 3))
        a = fast(graph, ev, extra).decode(); b = fast(graph, ev, extra).decode()
        self.assertTrue(t.compatibility(a, b))
        b['transitions'] += 1
        with self.assertRaises(ValueError): t.compatibility(a, b)
        self.assertFalse(t.compatibility({'selected': None}, a))


if __name__ == '__main__': unittest.main()
