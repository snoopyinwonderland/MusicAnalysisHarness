from copy import deepcopy
from fractions import Fraction as F
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_context_refresh_trial as t
from test_harmony_context_scalar_index import toy, fast, joint
from test_harmony_context_score_learning import row, frozen
from test_harmony_structured_learning import entry, contract
from test_harmony_common_benchmark import cell, span, C


def receipt(ids, target=False):
    values = {k: t.s.q(F(i, 10)) for i, k in enumerate(joint.FEATURES)}
    return {'existing_path_ids': ids, 'source_labels_used': False,
        'target_path_created_using_labels': target, 'legacy': {'cost': t.s.q(F(1, 3) if target else F(2, 3))},
        'context': {'availability': dict.fromkeys(joint.FEATURES, True), 'scored_available_feature_sums': values}}


class ContextRefreshTests(unittest.TestCase):
    def test_collect_deduplicates_without_correctness_filter_or_abstention_retry(self):
        original = row() | {'negative_ids': ['x']}; before = deepcopy(original)
        ctx = {'rows': [{'sample_id': 'a'}, {'sample_id': 'b'}],
            'refresh_records': {'a': {'selected_ids': ('x',)}, 'b': {'selected_ids': None}},
            'use': contract([entry()]), 'manifest': [entry()], 'parent_sha': 'parent'}
        def no_read(*a, **kw): raise AssertionError('duplicate or abstention must not load or retry')
        with patch.object(t.old, 'contrasts', return_value=([original], {})):
            rows, counts, proofs = t.collect(ctx, no_read)
        self.assertEqual(original, before); self.assertEqual(len(rows), 1); self.assertEqual(proofs, [])
        self.assertEqual(counts['refresh']['duplicate_blind_paths_not_reweighted'], 1)
        self.assertEqual(counts['refresh']['previous_abstentions_retained_not_retried_for_mining'], 1)

    def test_comparison_canonicalizes_ids_and_keeps_missing_in_full_denominator(self):
        good = t.old.evaluate([cell(0, 2, C)], [cell(0, 2, C)], span(0, 2), selected=True)
        missing = t.old.evaluate([cell(0, 2, C)], [cell(0, 2)], span(0, 2), selected=False)
        a = {'sample_id': 'a', 'work_family_id': 'family', 'status': 'selected', 'selected_ids': ('x',),
            'previous_ids': ['x'], 'baseline_ids': ['x'], 'evaluation': good,
            'previous_evaluation': good, 'baseline_evaluation': good}
        b = a | {'sample_id': 'b', 'selected_ids': None, 'evaluation': missing, 'status': 'abstention'}
        before = deepcopy((a, b)); table = t.comparisons([a, b])
        self.assertEqual(table['against_frozen_old26']['changes']['path_changed_with_complete_selection'], 0)
        self.assertEqual(table['common_completed_scopes'], 1)
        self.assertEqual(table['resource_changes']['previous_completion_now_abstention'], 1)
        self.assertEqual(table['against_frozen_old26']['changes']['abstentions'], 1)
        self.assertEqual(before, (a, b))

    def test_path_identity_normalizes_list_tuple_and_rejects_bad_ids(self):
        self.assertEqual(t.path_key('a', ['x', 'y']), t.path_key('a', ('x', 'y')))
        for path in (None, [], [''], [3], 'x'):
            with self.assertRaises(ValueError): t.path_key('a', path)

    def test_source_bound_contrast_unknown_gradient_and_no_input_mutation(self):
        n, gold = receipt(['n']), receipt(('g',), True); key = joint.FEATURES[0]
        n['context']['availability'][key] = False
        n['context']['scored_available_feature_sums'][key] = t.s.q(9)
        before = deepcopy((n, gold)); e = entry()
        r = t.contrast(e, 'sample', n, gold, {'total': t.s.q(1)}, 'source')
        self.assertEqual(r['score_delta'][key], t.s.q(9)); self.assertIsNone(r['gradient_delta'][key])
        self.assertFalse(r['negative_selection_used_training_labels']); self.assertTrue(r['target_selection_used_training_labels'])
        self.assertEqual(before, (n, gold)); self.assertEqual(r['entry'], e)

    def test_nonblind_receipts_rejected_and_training_rights_still_required(self):
        n, gold = receipt(['n']), receipt(['g'], True)
        for name, change in (('source_labels_used', True), ('target_path_created_using_labels', True)):
            with self.assertRaises(ValueError): t.contrast(entry(), 'a', n | {name: change}, gold, {'total': t.s.q(1)}, 'source')
        r = t.contrast(entry('bad', 'dev'), 'a', n, gold, {'total': t.s.q(0)}, 'source')
        with self.assertRaises(ValueError): t.learning.validate_rows([r], contract([entry()]), [entry()], 'parent')

    def test_same_learning_reset_fixed_old26_and_masked_zero_loss_protection(self):
        rows = [row()]; r = row(); r['contrast_id'] = 'z'; r['loss'] = t.s.q(0); rows.append(r)
        m = t.learning.fit(rows, frozen(), contract([entry()]), [entry()], 'parent', 'new-pool')
        self.assertEqual(m['averaging_ticks'], 6)
        self.assertEqual(m['frozen_existing_weights'], {k: t.s.q(v) for k, v in frozen().items()})
        self.assertEqual(t.configuration()['initialization'], 'zero_not_previous_unadopted_weights')
        self.assertFalse(t.configuration()['correctness_filter'])
        self.assertFalse(t.configuration()['new_seventh_preservation_gate'])

    def test_guard_model_metadata_is_new_not_parent_sha_and_tiny_budget_abstains(self):
        graph, ev, _ = toy(); weights = dict.fromkeys(joint.FEATURES, F(1, 3))
        a = t.select(fast(graph, ev, weights), {'model_id': 'new'}, 'newsha', timer=lambda: 0)
        b = t.select(fast(graph, ev, weights), {'model_id': 'new'}, 'newsha', timer=lambda: 0, transition_budget=1)
        self.assertTrue(a['exact_optimum_under_declared_score'])
        self.assertEqual(a['frozen_model_ref']['model_sha256'], 'newsha')
        self.assertFalse(a['frozen_model_ref']['reference_labels_used_for_selection'])
        self.assertIsNone(b['selected']); self.assertFalse(b['exact_optimum_under_declared_score'])

    def test_guard_restores_hooks_on_failure(self):
        graph, ev, _ = toy(); sc = fast(graph, ev, dict.fromkeys(joint.FEATURES, F(1)))
        def fail(*a, **kw): raise RuntimeError('test')
        sc.scalar_values = fail
        with self.assertRaises(RuntimeError): t.select(sc, {'model_id': 'new'}, 'sha', timer=lambda: 0)
        self.assertIs(sc.scalar_values, fail)

    def test_diagnostic_uses_same_exact_cost_and_margin_is_not_accuracy(self):
        r = row(); weights = joint.ZERO | {joint.FEATURES[0]: F(-1, 4)}
        d = t.pool_diagnostic([r], weights)
        self.assertEqual(d['positive_margin_sum'], t.s.q(F(1, 2)))
        self.assertEqual(d['negative_cheaper_than_target'], 1); self.assertTrue(d['margin_is_not_accuracy'])


if __name__ == '__main__': unittest.main()
