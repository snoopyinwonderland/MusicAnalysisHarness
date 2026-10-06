from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_ordinal_protection_dev_trial as t
from test_harmony_member_role_scoring import toy, paths
from test_harmony_score_balance_ledger import fixture


def seal():
    return ({'complete': True, 'model_sha256': t.PINS['model.json.gz'],
        'operational_weights_changed': False, 'current_dev_reconstructed_or_used': False},
        {'dev_used': False, 'production_deployment': False},
        {'model_sha256': t.PINS['model.json.gz'], 'dev_used': False,
         'all_35_weights_frozen_during_selection': True},
        {'passed': True, 'report_sha256': t.PINS['report.json'], 'model_sha256': t.PINS['model.json.gz']})


class OrdinalProtectionFrozenDevTests(unittest.TestCase):
    def test_ordinal_weights_replayed_from_exact_train_pool_without_refitting(self):
        report, model, freeze, audit = seal()
        report |= {'input_hashes': {}, 'artifact_hashes': {}, 'code_hashes': {}}
        ctx = {'active_pool': ['vector'], 'competitors': ['wrong'], 'initial35': fixture()[2],
               'use': 'use', 'manifest': 'manifest', 'parent_sha': 'parent',
               'weights': {k: fixture()[2][k] for k in t.train.ledger.old.FEATURES}}
        sealed = dict(zip(t.PINS, (report, model, freeze, audit)))
        expected = (model, ctx['active_pool'], ctx['competitors'], ctx['initial35'],
                    'use', 'manifest', 'parent', t.ordinal_train.PINS['training-vectors.json.gz'])
        with patch.object(t.ordinal_train, 'context', return_value=ctx), \
                patch.object(t.ordinal_train.learning, 'model_weights', return_value=fixture()[2]) as replay, \
                patch.object(t.ordinal_train.learning, 'fit', side_effect=AssertionError('forbidden fit')):
            weights, actual = t.frozen_weights(lambda p, h: sealed[Path(p).name])
        replay.assert_called_once_with(*expected)
        self.assertIs(actual, ctx)
        self.assertEqual(weights[t.ARMS[1]], ctx['initial35'])
        self.assertEqual(weights[t.ARMS[2]], fixture()[2])
        for k in set(t.train.ledger.FEATURES)-set(ctx['weights']):
            self.assertEqual(weights[t.ARMS[0]][k], 0)

    def test_no_overwrite_before_models_are_read(self):
        with TemporaryDirectory() as d, patch.object(t, 'frozen_weights', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)

    def test_frozen_train_model_and_source_audit_required(self):
        good = seal(); t.check_seal(*good)
        for index, key, value in ((0, 'complete', False), (0, 'model_sha256', 'x'),
                (0, 'operational_weights_changed', True), (0, 'current_dev_reconstructed_or_used', True),
                (1, 'dev_used', True), (1, 'production_deployment', True), (2, 'dev_used', True),
                (2, 'model_sha256', 'x'), (2, 'all_35_weights_frozen_during_selection', False),
                (3, 'passed', False), (3, 'report_sha256', 'x'), (3, 'model_sha256', 'x')):
            with self.subTest(key=key):
                bad = deepcopy(good); bad[index][key] = value
                with self.assertRaisesRegex(ValueError, 'unsealed'): t.check_seal(*bad)

    def test_no_fit_exact_small_graph_and_correct_all35_model_metadata(self):
        graph, ev, _ = toy(notes=[('E4', 0, 1, 'lead'), ('F4', 1, 2, 'lead'),
                                 ('E4', 2, 3, 'lead'), ('C3', 0, 3, 'bass')], end=3, cap=3)
        weights = fixture()[2]; before = deepcopy(weights)
        sc = t.train.Scorer(graph, ev, weights)
        best = min((sc.score_path(ids), ids) for ids in paths(graph))
        with patch.object(t.train.learning, 'fit', side_effect=AssertionError('forbidden fit')), \
                patch.object(t.ordinal_train.learning, 'fit', side_effect=AssertionError('forbidden ordinal fit')):
            result = t.ordinary(graph, ev, weights, {}, t.ARMS[2], wall_seconds=60)
        self.assertEqual(weights, before); selected = result['selected']
        self.assertEqual((t.s.f(selected['score_cost']), t.s.fresh.path_ids(selected)), best)
        self.assertEqual(result['frozen_model_ref']['model_sha256'], t.MODEL_SHAS[t.ARMS[2]])
        self.assertFalse(result['frozen_model_ref']['fit_performed_this_run'])
        self.assertTrue(result['frozen_dev_contract']['all_35_weights_frozen'])
        self.assertNotIn('joint_balance_contract', result)
        self.assertFalse(selected['source_labels_used_for_selection']); self.assertFalse(selected['human_validated'])
        self.assertIsNone(selected['confidence']); t.train.ledger.flatten(selected['context_score'], weights)

    def test_zero_extras_have_identical_legacy_winner_and_cost(self):
        graph, ev, _ = toy(); old26 = {k: fixture()[2][k] for k in t.train.ledger.old.FEATURES}
        weights = {k: old26.get(k, F()) for k in t.train.ledger.FEATURES}
        legacy = t.s.Scorer(graph, ev, old26).decode()
        result = t.ordinary(graph, ev, weights, {}, t.ARMS[0], wall_seconds=60)
        t.previous.check_control(result, legacy['selected'], t.ARMS[0])
        self.assertEqual(result['frozen_model_ref']['model_sha256'], t.MODEL_SHAS[t.ARMS[0]])
        t.train.ledger.flatten(result['selected']['context_score'], weights)

    def test_wall_has_no_partial_winner_and_preserves_frozen_identity(self):
        graph, ev, _ = toy(); ticks = iter(range(100000))
        result = t.ordinary(graph, ev, fixture()[2], {}, t.ARMS[1], wall_seconds=.1, timer=lambda: next(ticks))
        self.assertIsNone(result['selected']); self.assertFalse(result['exact_optimum_under_declared_score'])
        self.assertFalse(result['partial_winner_returned'])
        self.assertEqual(result['frozen_model_ref']['model_sha256'], t.MODEL_SHAS[t.ARMS[1]])

    def test_original_abstention_and_incomplete_unreachable_inventory_not_filtered(self):
        old = {'arms': {'timing_calibrated': {'status': 'old_guard_failure'}}}
        before = deepcopy(old); value = t.original_abstention(old)
        self.assertEqual(old, before); self.assertEqual(value['status'], 'old_guard_failure')
        self.assertIsNone(value['selected_prediction']); self.assertEqual(value['elapsed_seconds'], 0)
        rows = [{'pair_id': 'a', 'sample_id': 'a', 'attempted': False},
                {'pair_id': 'a', 'sample_id': 'b', 'fully_evaluable': False},
                {'pair_id': 'a', 'sample_id': 'c', 'candidate_ceiling': {'reachable': False}}]
        self.assertEqual(len(t.previous.packet_keys(rows, 3)), 3)

    def test_all_predictions_sealed_before_current_reference_read(self):
        calls = []
        def save(path, value):
            calls.append('seal'); self.assertFalse(value['dev_labels_read']); self.assertFalse(value['fit_performed'])
            self.assertEqual(value['contexts'], 2); self.assertEqual(value['model_sha256_by_arm'], t.MODEL_SHAS)
        def read(path, sha):
            self.assertEqual(calls, ['seal']); self.assertEqual(sha, t.SOURCE_PINS['report.json'])
            calls.append('read'); return {'test': True}
        with patch.object(t.io, 'digest', return_value='pin'):
            self.assertEqual(t.seal_and_open_reference(read, save, Path('out'),
                [{'prediction_artifact': 'a'}, {'prediction_artifact': 'b'}]), {'test': True})
        self.assertEqual(calls, ['seal', 'read'])

    def test_common_completed_and_resource_loss_are_separate(self):
        def arm(selected, hit):
            return {'selected_prediction': selected, 'evaluation': {'selected_hit': hit,
                'components': {'root_members': {'matched': t.s.q(1 if hit else 0)}}}}
        rows = [{'pair_id': 'x', 'sample_id': 'a', 'sample_span': {},
                 'arms': {a: arm('path', True) for a in t.ARMS}},
                {'pair_id': 'x', 'sample_id': 'b', 'sample_span': {},
                 'arms': {t.ARMS[0]: arm('path', True), t.ARMS[1]: arm(None, False), t.ARMS[2]: arm(None, False)}}]
        with patch.object(t, 'native_prediction', side_effect=lambda p, span: p), \
                patch.object(t, 'summarize', side_effect=lambda rs: {'n': len(rs)}):
            result = t.metrics(rows)
        self.assertEqual(result['common_completed_count'], 1)
        self.assertEqual(result['all_original'][t.ARMS[0]]['n'], 2)
        pair = result['paired_comparisons'][t.ARMS[0]+'__to__'+t.ARMS[2]]
        self.assertEqual(pair['resource_losses'], 1)
        self.assertEqual(pair['all_original']['previously_correct_lost'], 1)
        self.assertEqual(pair['common_completed']['previously_correct_lost'], 0)

    def test_distinct_pinned_models_and_no_empty_metric_success_claim(self):
        self.assertEqual(len(set(t.MODEL_SHAS.values())), 3)
        self.assertTrue(all(len(h) == 64 for h in (*t.MODEL_SHAS.values(), *t.PINS.values(), *t.PREVIOUS_PINS.values())))
        result = t.metrics([]); self.assertEqual(result['common_completed_count'], 0)
        self.assertEqual(len(result['paired_comparisons']), 3)


if __name__ == '__main__': unittest.main()
