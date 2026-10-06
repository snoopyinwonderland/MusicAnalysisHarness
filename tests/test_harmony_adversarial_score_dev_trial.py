from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_adversarial_score_dev_trial as t
from test_harmony_exact_frontier import problem


def seal():
    sha = t.MODEL_PINS['model.json.gz']
    return ({'complete': True, 'model_sha256': sha, 'dev_used_for_fit': False,
        'dev_inference_or_evaluation': False, 'production_modified': False, 'candidate_policy_changed': False},
        {'passed': True, 'report_sha256': t.MODEL_PINS['report.json'], 'audit_revision': 2,
         'new_fit_or_checkpoint_selection': False},
        {'model_sha256': sha, 'all_epochs_averaged': True, 'dev_labels_used': False}, sha)


class AdversarialFrozenDevTests(unittest.TestCase):
    def test_no_overwrite_precedes_all_reads(self):
        with TemporaryDirectory() as d, patch.object(t, 'frozen_weights', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)

    def test_completed_train_only_v2_audit_required(self):
        values = seal(); t.check_model_seal(*values)
        for index, key, value in ((0, 'complete', False), (0, 'dev_used_for_fit', True),
                (0, 'dev_inference_or_evaluation', True), (0, 'production_modified', True),
                (0, 'candidate_policy_changed', True), (1, 'passed', False), (1, 'report_sha256', 'x'),
                (1, 'audit_revision', 1), (1, 'new_fit_or_checkpoint_selection', True),
                (2, 'all_epochs_averaged', False), (2, 'dev_labels_used', True), (2, 'model_sha256', 'x')):
            with self.subTest(key=key):
                broken = deepcopy(values); broken[index][key] = value
                with self.assertRaisesRegex(ValueError, 'unsealed'): t.check_model_seal(*broken)

    def test_all_original_scope_types_preserved(self):
        rows = [{'pair_id': 'a', 'sample_id': 'i', 'attempted': False},
            {'pair_id': 'a', 'sample_id': 'j', 'fully_evaluable': False},
            {'pair_id': 'b', 'sample_id': 'j', 'candidate_ceiling': {'reachable': False}}]
        before = deepcopy(rows); self.assertEqual(len(t.packet_keys(rows, 3)), 3); self.assertEqual(rows, before)
        with self.assertRaisesRegex(ValueError, 'inventory'): t.packet_keys(rows+rows[:1], 4)

    def test_no_fit_no_training_labels_in_ordinary_inference(self):
        graph, ev = problem(); weights = t.s.initial_weights(t.s.fresh.timing.ZERO); before = deepcopy(weights)
        with patch.object(t.learning, 'fit', side_effect=AssertionError('fit forbidden')):
            result = t.ordinary(graph, ev, weights, {})
        self.assertEqual(weights, before); selected = result['selected']; self.assertIsNotNone(selected)
        self.assertFalse(selected['source_labels_used_for_selection'])
        self.assertFalse(selected.get('training_reference_labels_used', False)); self.assertFalse(selected['human_validated'])

    def test_both_control_arms_require_same_path_and_cost(self):
        graph, ev = problem(); result = t.ordinary(graph, ev, t.s.initial_weights(t.s.fresh.timing.ZERO), {})
        for arm in t.control.ARMS:
            t.check_control(result, result['selected'], arm); t.check_control({'selected': None}, None, arm)
            with self.assertRaisesRegex(ValueError, 'control_changed'): t.check_control(result, None, arm)
            wrong = deepcopy(result['selected']); wrong['score_cost'] = t.s.q(t.s.f(wrong['score_cost'])+1)
            with self.assertRaisesRegex(ValueError, 'control_changed'): t.check_control(result, wrong, arm)

    def test_three_arm_predictions_sealed_before_reference_read(self):
        events = []; expected = {'reference': 'evaluation only'}
        def save(path, value):
            events.append('seal'); self.assertFalse(value['dev_labels_read']); self.assertFalse(value['fit_performed'])
            self.assertEqual(value['contexts'], 2); self.assertEqual(value['model_sha256_by_arm'], t.MODEL_SHAS)
        def read(path, sha):
            self.assertEqual(events, ['seal']); self.assertEqual(sha, t.SOURCE_PINS['report.json'])
            events.append('read'); return expected
        with patch.object(t.io, 'digest', return_value='h'):
            actual = t.seal_and_open_reference(read, save, Path('new'), [{'prediction_artifact': 'p1'}, {'prediction_artifact': 'p2'}])
        self.assertIs(actual, expected); self.assertEqual(events, ['seal', 'read'])

    def test_canonical_json_comparison_preserves_order_null_and_fractions(self):
        self.assertTrue(t.same_json({'ids': ('a', 'b'), 'x': None}, {'ids': ['a', 'b'], 'x': None}))
        self.assertFalse(t.same_json(['a', 'b'], ['b', 'a']))
        self.assertFalse(t.same_json({'x': None}, {'x': 0}))
        self.assertFalse(t.same_json({'n': 1, 'd': 3}, {'n': 1, 'd': 2}))

    def test_three_pinned_models_and_pairwise_comparisons(self):
        self.assertEqual(len(t.ARMS), 3); self.assertEqual(len(t.PAIRS), 3)
        self.assertIsNone(t.MODEL_SHAS[t.ARMS[0]])
        self.assertNotEqual(t.MODEL_SHAS[t.ARMS[1]], t.MODEL_SHAS[t.ARMS[2]])
        for values in (t.MODEL_PINS, t.PREVIOUS_PINS, t.SOURCE_PINS): self.assertTrue(all(len(h) == 64 for h in values.values()))
        self.assertEqual(t.s.FIXED, ('blocker_exposure', 'unresolved_spelling_exposure'))
        self.assertTrue(all(not v['changed'] and not v['previously_correct_lost'] and not v['newly_correct']
                            for v in t.comparisons([]).values()))
