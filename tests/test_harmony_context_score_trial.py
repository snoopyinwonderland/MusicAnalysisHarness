from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_context_score_trial as t
from test_harmony_context_joint_decoder import toy, scorer, paths
from test_harmony_structured_learning import entry


class ContextTrialTests(unittest.TestCase):
    def test_trained_exact_selection_equals_exhaustive_and_restores_instances(self):
        g, ev, _ = toy(cap=3); sc = scorer(g, ev, extra={k: F(1, 5) for k in t.joint.FEATURES})
        a, b, c = sc.original.source_scorer.base_run, sc.original.source_scorer.member_features, sc.transition_profile
        expected = min((sc.score_path(ids), ids) for ids in paths(g))
        r = t.select(sc, 'fixture', wall_seconds=10)
        self.assertEqual((t.s.f(r['selected']['score_cost']), t.s.fresh.path_ids(r['selected'])), expected)
        self.assertTrue(r['context_joint_contract']['fitted_weights_claimed'])
        self.assertEqual((sc.original.source_scorer.base_run, sc.original.source_scorer.member_features, sc.transition_profile), (a, b, c))
        self.assertFalse(r['learned_context_model']['reference_labels_used_for_selection'])

    def test_wall_abstention_is_not_best_so_far_and_hooks_restored(self):
        g, ev, _ = toy(cap=3); sc = scorer(g, ev, extra={k: F(1) for k in t.joint.FEATURES})
        originals = sc.original.source_scorer.base_run, sc.original.source_scorer.member_features, sc.transition_profile
        times = iter((0, 0, 100, 100))
        r = t.select(sc, 'fixture', timer=lambda: next(times), wall_seconds=10)
        self.assertEqual(r['status'], 'context_wall_budget_abstention'); self.assertIsNone(r['selected'])
        self.assertFalse(r['exact_optimum_under_declared_score']); self.assertFalse(r['partial_winner_returned'])
        self.assertEqual((sc.original.source_scorer.base_run, sc.original.source_scorer.member_features, sc.transition_profile), originals)

    def test_original_operation_budget_abstention_no_fallback(self):
        g, ev, _ = toy(cap=3); sc = scorer(g, ev, extra={k: F(1) for k in t.joint.FEATURES})
        r = t.select(sc, 'fixture', transition_budget=1)
        self.assertIsNone(r['selected']); self.assertEqual(r['status'], 'transition_budget_abstention')
        self.assertEqual(r['resource_guard']['raw_segment_cap'], 3)

    def test_pool_dedup_abstention_loss_and_unknown_provenance(self):
        g, ev, _ = toy(cap=3); sc = scorer(g, ev); ids = paths(g)[:2]
        def arm(p, target=False):
            return {'selected': True, 'path_ids': p, 'zero_receipt': sc.path_receipt(p, target=target),
                'path_selection_uses_training_labels': target}
        arms = {'initial': arm(ids[0]), 'ordinary_frozen': arm(ids[0]),
            'adversarial_frozen': {'selected': False}, 'epoch3_adversary': arm(ids[1]), 'epoch3_target': arm(ids[1], True)}
        comp = {k: {'unchanged_original_cost_receipt': a['zero_receipt']['legacy'],
            'unchanged_original_training_loss': {'total': t.s.q(0)}} for k, a in arms.items() if a['selected']}
        ctx = {'rows': [{'sample_id': 'a'}], 'joint_packets': {'a': {'entry': entry(), 'arms': arms,
            'source_ir_content_sha256': 'fixture'}}, 'competition_packets': {'a': {'arms': comp}}}
        before = deepcopy(ctx); rows, counts = t.contrasts(ctx)
        self.assertEqual(len(rows), 2); self.assertEqual(ctx, before)
        self.assertEqual(counts['duplicate_negative_paths'], 1); self.assertEqual(counts['preserved_resource_abstentions'], 1)
        self.assertTrue(all(r['target_selection_used_training_labels'] for r in rows))
        self.assertTrue(all(not r['features_use_source_labels'] for r in rows))


if __name__ == '__main__': unittest.main()
