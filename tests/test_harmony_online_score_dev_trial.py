from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_online_score_dev_trial as t
from test_harmony_exact_frontier import problem


def seal():
    sha = t.MODEL_PINS['model.json.gz']
    return ({'complete': True, 'model_sha256': sha, 'dev_used_for_fit': False,
             'dev_inference_or_evaluation': False, 'production_modified': False},
            {'passed': True, 'report_sha256': t.MODEL_PINS['report.json']},
            {'model_sha256': sha, 'all_epochs_averaged': True, 'dev_labels_used': False}, sha)


class FrozenDevTests(unittest.TestCase):
    def test_no_overwrite_precedes_model_or_dev_reads(self):
        with TemporaryDirectory() as d, patch.object(t, 'frozen_weights', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)

    def test_completed_train_only_seal_is_required(self):
        values = seal(); t.check_model_seal(*values)
        mutations = [(0, 'complete', False), (0, 'dev_used_for_fit', True),
            (0, 'dev_inference_or_evaluation', True), (0, 'production_modified', True),
            (1, 'passed', False), (1, 'report_sha256', 'changed'),
            (2, 'all_epochs_averaged', False), (2, 'dev_labels_used', True),
            (2, 'model_sha256', 'changed')]
        for index, key, value in mutations:
            with self.subTest(key=key):
                broken = deepcopy(values); broken[index][key] = value
                with self.assertRaisesRegex(ValueError, 'unsealed'): t.check_model_seal(*broken)

    def test_all_scope_types_kept_without_reference_filter(self):
        rows = [{'pair_id': 'a', 'sample_id': 'i', 'attempted': False},
                {'pair_id': 'a', 'sample_id': 'j', 'fully_evaluable': False},
                {'pair_id': 'b', 'sample_id': 'j', 'candidate_ceiling': {'reachable': False}}]
        before = deepcopy(rows)
        self.assertEqual(len(t.packet_keys(rows, 3)), 3); self.assertEqual(rows, before)

    def test_duplicate_or_missing_inventory_rejected(self):
        row = {'pair_id': 'a', 'sample_id': 'i'}
        for rows, count in (([row, row], 2), ([row], 2)):
            with self.assertRaisesRegex(ValueError, 'inventory'): t.packet_keys(rows, count)

    def test_ordinary_decode_is_blind_and_does_not_fit(self):
        graph, ev = problem(); w = t.s.initial_weights(t.s.fresh.timing.ZERO)
        before = deepcopy(w)
        with patch.object(t.learning, 'fit', side_effect=AssertionError('fit forbidden')):
            result = t.ordinary(graph, ev, w, {})
        self.assertEqual(w, before); self.assertIsNotNone(result['selected'])
        self.assertFalse(result['selected']['source_labels_used_for_selection'])
        self.assertFalse(result['selected'].get('training_reference_labels_used', False))
        self.assertFalse(result['selected']['human_validated'])

    def test_initial_control_path_and_cost_and_abstention_must_match(self):
        graph, ev = problem(); result = t.ordinary(graph, ev, t.s.initial_weights(t.s.fresh.timing.ZERO), {})
        t.check_initial_control(result, result['selected'])
        t.check_initial_control({'selected': None}, None)
        with self.assertRaisesRegex(ValueError, 'control_changed'): t.check_initial_control(result, None)
        wrong = deepcopy(result['selected']); wrong['score_cost'] = t.s.q(t.s.f(wrong['score_cost'])+1)
        with self.assertRaisesRegex(ValueError, 'control_changed'): t.check_initial_control(result, wrong)

    def test_all_predictions_sealed_before_reference_open(self):
        events = []; expected = {'reference': 'evaluation only'}
        def save(path, value):
            events.append('seal'); self.assertFalse(value['dev_labels_read'])
            self.assertFalse(value['fit_performed']); self.assertEqual(value['contexts'], 2)
        def read(path, sha):
            self.assertEqual(events, ['seal']); self.assertEqual(sha, t.SOURCE_PINS['report.json'])
            events.append('read'); return expected
        rows = [{'prediction_artifact': 'p1'}, {'prediction_artifact': 'p2'}]
        with patch.object(t.io, 'digest', return_value='h'):
            result = t.seal_and_open_reference(read, save, Path('new'), rows, 'model')
        self.assertIs(result, expected); self.assertEqual(events, ['seal', 'read'])

    def test_model_and_source_lineage_are_pinned(self):
        self.assertEqual(t.ARMS, ('initial_full_score', 'online_frozen_full_score'))
        for values in (t.MODEL_PINS, t.SOURCE_PINS):
            self.assertTrue(all(len(h) == 64 for h in values.values()))
        self.assertIn('post-seal-audit.json', t.MODEL_PINS)
        self.assertEqual(t.s.FIXED, ('blocker_exposure', 'unresolved_spelling_exposure'))

