from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_joint_balance_trial as t
from test_harmony_member_role_scoring import toy, paths, C, FM, by_path
from test_harmony_score_balance_ledger import fixture
from test_harmony_joint_balance_learning import row
from test_harmony_structured_learning import entry, contract


class JointBalanceTrialTests(unittest.TestCase):
    def test_all_tiny_paths_match_exhaustive_with_changed_old_context_role_weights(self):
        graph, ev, _ = toy(notes=[('E4', 0, 1, 'lead'), ('F4', 1, 2, 'lead'),
                                 ('E4', 2, 3, 'lead'), ('C3', 0, 3, 'bass')], end=3, cap=3)
        weights = fixture()[2]
        weights = weights | {'missing_member_fraction': weights['missing_member_fraction']+F(1, 100)}
        sc = t.Scorer(graph, ev, weights)
        expected = min((sc.score_path(ids), ids) for ids in paths(graph))
        result = sc.decode(force_delayed=True)
        self.assertEqual((t.s.f(result['selected']['score_cost']), t.s.fresh.path_ids(result['selected'])), expected)
        self.assertFalse(result['member_role_contract']['old26_and_old7_frozen'])
        self.assertTrue(result['joint_balance_contract']['all_35_weights_frozen_during_selection'])
        t.ledger.flatten(result['selected']['context_score'], weights)

    def test_initial_path_cost_identical_to_sealed_35_scorer(self):
        graph, ev, _ = toy(); weights = fixture()[2]; sc = t.Scorer(graph, ev, weights)
        from test_harmony_member_role_scoring import scorer
        old = scorer(graph, ev, {k: weights[k] for k in t.ledger.role.FEATURES}, {k: weights[k] for k in t.ledger.context.FEATURES})
        for ids in (by_path(graph, ((0, 4, C),)), by_path(graph, ((0, 2, C), (2, 4, FM)))):
            self.assertEqual(sc.path_receipt(ids), old.path_receipt(ids))

    def test_wall_abstention_has_no_partial_winner_or_wrong_frozen_metadata(self):
        graph, ev, _ = toy(); weights = fixture()[2]; sc = t.Scorer(graph, ev, weights)
        ticks = iter(range(10000))
        result = t.annotate(t.prior.prior.parent.select(sc, 'test', wall_seconds=0.1, timer=lambda: next(ticks)), weights)
        self.assertIsNone(result['selected']); self.assertFalse(result['exact_optimum_under_declared_score'])
        self.assertTrue(result['joint_balance_contract']['all_35_weights_frozen_during_selection'])

    def test_collect_35_known_masks_from_sealed_ledger_deltas(self):
        r = row(); initial = fixture()[2]
        source = r | {'negative_ids': ['a'], 'target_ids': ['b'], 'source_arm': 'blind', 'source_ir_content_sha256': 'source'}
        comp = {'left_minus_right_cost': t.s.q(t.learning.gap(r, initial)),
                'terms': {k: {'scored_partial_delta': r['score_delta'][k], 'value_delta': r['gradient_delta'][k],
                              'known_both': r['available'][k]} for k in t.learning.FEATURES}}
        ctx = {'role_vectors': {('sample', 'contrast'): source}, 'contrast_rows': [{'sample_id': 'sample', 'contrast_id': 'contrast',
               'loss': r['loss'], 'comparison': comp}], 'initial35': initial, 'use': contract([entry()]),
               'manifest': [entry()], 'parent_sha': 'parent'}
        before = deepcopy(ctx); rows, counts = t.collect(ctx)
        self.assertEqual(ctx, before); self.assertEqual(rows[0]['score_delta'], r['score_delta'])
        self.assertEqual(counts['known_nonzero_trainable_gradient'], 1)
        ctx['contrast_rows'][0]['comparison']['left_minus_right_cost'] = t.s.q(999)
        with self.assertRaises(ValueError): t.collect(ctx)

    def test_proposal_identity_changes_when_old_weights_change(self):
        weights = fixture()[2]
        result = {'selected': {'segments': [{'semantic_group_ref': 'a'}]}}
        a = t.annotate(deepcopy(result), weights)['selected']['proposal_id']
        changed = weights | {'missing_member_fraction': weights['missing_member_fraction']+F(1, 100)}
        self.assertNotEqual(a, t.annotate(deepcopy(result), changed)['selected']['proposal_id'])


if __name__ == '__main__': unittest.main()
