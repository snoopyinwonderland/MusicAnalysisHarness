from copy import deepcopy
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_score_balance_ledger as l
from test_harmony_member_role_scoring import toy, scorer, by_path, C, FM


def fixture():
    graph, ev, _ = toy()
    sc = scorer(graph, ev, {k: F(1, 3) for k in l.role.FEATURES},
                {k: F(-1, 7) for k in l.context.FEATURES})
    weights = sc.original.weights | {k: F(-1, 7) for k in l.context.FEATURES} | sc.role_weights
    a = sc.path_receipt(by_path(graph, ((0, 2, C), (2, 4, FM))))
    b = sc.path_receipt(by_path(graph, ((0, 4, C),)), target=True)
    return a, b, weights


class ScoreBalanceLedgerTests(unittest.TestCase):
    def test_all_35_features_have_exactly_one_group(self):
        grouped = [k for v in l.GROUPS.values() for k in v]
        self.assertEqual(len(grouped), 35)
        self.assertEqual(len(set(grouped)), 35)
        self.assertEqual(set(grouped), set(l.FEATURES))

    def test_products_subtotals_and_groups_reconstruct_cost(self):
        a, _, weights = fixture(); before = deepcopy(a); flat = l.flatten(a, weights)
        self.assertEqual(sum((l.f(t['cost']) for t in flat['terms'].values()), F()), l.f(a['cost']))
        self.assertEqual(sum((l.f(v) for v in flat['group_costs'].values()), F()), l.f(a['cost']))
        self.assertEqual(a, before)

    def test_signed_comparison_is_cost_not_probability(self):
        a, b, weights = fixture(); diff = l.compare(a, b, weights)
        self.assertEqual(l.f(diff['left_minus_right_cost']), l.f(a['cost'])-l.f(b['cost']))
        self.assertEqual(sum((l.f(v) for v in diff['group_deltas'].values()), F()), l.f(diff['left_minus_right_cost']))
        self.assertEqual(l.f(l.compare(b, a, weights)['left_minus_right_cost']), -l.f(diff['left_minus_right_cost']))
        self.assertIsNone(diff['probability']); self.assertFalse(diff['new_fit_or_search'])

    def test_whole_unknown_retains_known_partial_cost_without_gradient(self):
        a, b, weights = fixture(); k = 'missing_member_fraction'
        a['legacy']['availability'][k] = False
        flat = l.flatten(a, weights); diff = l.compare(a, b, weights)
        self.assertIsNone(flat['terms'][k]['value'])
        self.assertEqual(flat['terms'][k]['scored_known_local_sum'], a['legacy']['observed_feature_sums'][k])
        self.assertEqual(flat['terms'][k]['cost'], a['legacy']['term_costs'][k])
        self.assertFalse(diff['terms'][k]['known_both']); self.assertIsNone(diff['terms'][k]['value_delta'])

    def test_wrong_product_rejected(self):
        a, _, weights = fixture(); a['legacy']['term_costs'][l.old.FEATURES[0]] = l.q(99)
        with self.assertRaisesRegex(ValueError, 'product_mismatch'): l.flatten(a, weights)

    def test_wrong_total_or_parent_identity_rejected(self):
        a, _, weights = fixture()
        for k in ('cost', 'parent_score_cost', 'context_cost', 'member_role_cost'):
            with self.assertRaisesRegex(ValueError, 'cost_identity'):
                l.flatten(a | {k: l.q(999)}, weights)

    def test_missing_keys_and_nonboolean_availability_rejected(self):
        a, _, weights = fixture()
        with self.assertRaises(ValueError): l.flatten(a, {})
        bad = deepcopy(a); bad['legacy']['term_costs'].pop(l.old.FEATURES[0])
        with self.assertRaises(ValueError): l.flatten(bad, weights)
        bad = deepcopy(a); bad['legacy']['availability'][l.old.FEATURES[0]] = 1
        with self.assertRaises(ValueError): l.flatten(bad, weights)

    def test_coefficient_binding_rejected(self):
        a, _, weights = fixture()
        bad = deepcopy(a); bad['context']['coefficients'][l.context.FEATURES[0]] = l.q(999)
        with self.assertRaisesRegex(ValueError, 'coefficients_changed'): l.flatten(bad, weights)

    def test_reweight_only_two_roles_no_search_no_mutation(self):
        a, _, weights = fixture(); before = deepcopy(a)
        changed = weights | {k: F(-1, 4) for k in l.role.FEATURES}
        result = l.reweight_roles(a, changed)
        self.assertEqual(a, before)
        for k in ('legacy', 'context', 'parent_score_cost', 'existing_path_ids'):
            self.assertEqual(result[k], a[k])
        self.assertEqual(l.flatten(result, changed)['cost'], result['cost'])

    def test_model_keys_and_bounds_validated(self):
        _, _, weights = fixture()
        model = {'frozen26': {k: l.q(weights[k]) for k in l.old.FEATURES},
                 'frozen7': {k: l.q(weights[k]) for k in l.context.FEATURES},
                 'weights': {k: l.q(weights[k]) for k in l.role.FEATURES}}
        self.assertEqual(l.coefficients(model), weights)
        with self.assertRaises(ValueError): l.coefficients(model | {'weights': {}})
        bad = deepcopy(model); bad['frozen26']['harmonic_run_count'] = l.q(-1)
        with self.assertRaises(ValueError): l.coefficients(bad)


if __name__ == '__main__': unittest.main()
