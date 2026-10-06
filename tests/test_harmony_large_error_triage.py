from fractions import Fraction as F
import unittest
from musicanote_harness import harmony_large_error_triage as t
from test_harmony_functional_scoring import C, G, G7, F64


class LargeErrorTriageTests(unittest.TestCase):
    def test_same_surface_different_functional_root_not_nct_error(self):
        result = t.compare_runs([(F(), F(2), C)], [(F(), F(2), F64)])
        self.assertEqual(result['quarter_totals'], {'same_members_different_root': t.q(2)})
        self.assertEqual(result['cells'][0]['subtype'], 'functional_six_four_vs_literal_surface')
        self.assertFalse(result['interpretation_confirmed'])

    def test_member_change_and_both_change_are_disjoint(self):
        result = t.compare_runs([(F(), F(3), G7)], [(F(), F(1), G), (F(1), F(3), C)])
        self.assertEqual(result['quarter_totals'], {'same_root_different_members': t.q(1), 'different_root_and_members': t.q(2)})

    def test_raw_partition_does_not_make_false_error(self):
        result = t.compare_runs([(F(), F(1, 3), G), (F(1, 3), F(2), G)], [(F(), F(2), G)])
        self.assertEqual(result['quarter_totals'], {'same_signature': t.q(2)})

    def test_exact_threshold_is_not_calibrated_weight(self):
        a = dict(availability=True, feature=t.q(F(1, 3))); b = dict(availability=True, feature=t.q(0))
        result = t.contrast(a, b, F(-1819, 5000))
        self.assertEqual(t.f(result['single_contrast_equal_cost_weight']), F(5457, 5000))
        self.assertTrue(result['threshold_is_not_fitted_weight']); self.assertTrue(result['fresh_optimum_not_computed'])

    def test_unavailable_not_zero_gradient_and_no_implied_win(self):
        a = dict(availability=False, feature=None); b = dict(availability=True, feature=t.q(0))
        result = t.contrast(a, b, F(-1))
        self.assertIsNone(result['feature_delta']); self.assertIsNone(result['single_contrast_equal_cost_weight'])
        a = dict(availability=True, feature=t.q(0))
        self.assertIsNone(t.contrast(a, b, F(-1))['single_contrast_equal_cost_weight'])

    def test_abstention_not_removed_from_inventory(self):
        result = t.summary([dict(winner_path_ids=None)])
        self.assertEqual(result['counts'], {'records': 1, 'compute_abstentions': 1})
        self.assertFalse(result['new_accuracy_measurement'])


if __name__ == '__main__': unittest.main()
