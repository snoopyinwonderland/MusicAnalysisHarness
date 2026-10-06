"""Replay the established Train/model safety tests for the new feature."""
from musicanote_harness import harmony_member_timing_learning as s
from musicanote_harness.harmony_temporal_scoring import bind
import unittest
import test_harmony_recipe_balance_learning as template


def row():
    return bind(template.row, {'s': s})()


class LearningTests(unittest.TestCase):
    def test_fit_replay_and_one_coefficient_only(self):
        bind(template.LearningTests.test_fit_replay_and_one_coefficient_only, {'s': s, 'row': row})(self)
    def test_dev_and_unapproved_rows_rejected(self):
        bind(template.LearningTests.test_dev_and_unapproved_rows_rejected, {'s': s, 'row': row})(self)
    def test_negative_delta_not_incentive_to_increase_penalty(self):
        bind(template.LearningTests.test_negative_delta_not_incentive_to_increase_penalty, {'s': s, 'row': row})(self)
    def test_missing_feature_and_duplicate_contrasts_rejected(self):
        bind(template.LearningTests.test_missing_feature_and_duplicate_contrasts_rejected, {'s': s, 'row': row})(self)
    def test_model_contract_tampering(self):
        bind(template.LearningTests.test_model_contract_tampering, {'s': s, 'row': row})(self)
