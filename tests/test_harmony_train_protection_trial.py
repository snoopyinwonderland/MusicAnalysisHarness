from copy import deepcopy
from fractions import Fraction as F
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_train_protection_trial as t
from test_harmony_score_balance_ledger import fixture
from test_harmony_train_protection_search import toy, loss, C, FM, by_path


class ProtectionTrialTests(unittest.TestCase):
    def test_no_overwrite_precedes_input_reads(self):
        with TemporaryDirectory() as d, patch.object(t, 'context', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)

    def test_inventory_protects_old_and_new_correct_without_dev(self):
        row = dict(sample_id='a', loss=t.s.q(0), negative_ids=['x'], target_ids=['x'],
                   score_delta={'feature': t.s.q(0)}, gradient_delta={'feature': t.s.q(0)})
        ctx = dict(pool=[row], rows=[dict(sample_id=s, split='train') for s in ('a', 'b', 'c')],
            previous_records={'a': {'evaluation': {'selected_hit': True}}, 'b': {'evaluation': {'selected_hit': True}}},
            joint_records={'c': {'evaluation': {'selected_hit': True}}})
        inert, protected = t.inventory(ctx)
        self.assertEqual(inert, [row]); self.assertEqual(set(protected), {'a', 'b', 'c'})
        bad = deepcopy(ctx); bad['rows'][0]['split'] = 'dev'
        with self.assertRaisesRegex(ValueError, 'nontrain'): t.inventory(bad)
        bad = deepcopy(ctx); bad['pool'][0]['negative_ids'] = ['other']
        with self.assertRaisesRegex(ValueError, 'not_inert'): t.inventory(bad)

    def test_vector_positive_loss_all35_and_unknown_gradient_null(self):
        a, b, weights = fixture(); a['legacy']['availability']['missing_root'] = False
        row, diff = t.vector({'split': 'train'}, 'sample', a, b, {'total': t.s.q(1)}, 'source', weights)
        self.assertEqual(set(row['score_delta']), set(t.learning.FEATURES))
        self.assertIsNone(row['gradient_delta']['missing_root'])
        self.assertEqual(t.learning.gap(row, weights), t.s.f(diff['left_minus_right_cost']))
        self.assertTrue(row['negative_selection_used_training_labels'])
        self.assertFalse(row['features_use_source_labels'])
        with self.assertRaises(ValueError):
            t.vector({}, 's', a, b, {'total': t.s.q(0)}, 'source', weights)

    def test_semantic_dedup_ignores_equal_signature_raw_splits(self):
        graph, _, _ = toy(end=3, cap=3)
        a = by_path(graph, ((0, 3, C),))
        b = by_path(graph, ((0, 1, C), (1, 3, C)))
        self.assertEqual(t.semantic_key(graph, a), t.semantic_key(graph, b))
        self.assertNotEqual(t.semantic_key(graph, a), t.semantic_key(graph, by_path(graph, ((0, 3, FM),))))

    def test_individual_trust_box_bound_is_not_a_fit_or_accuracy(self):
        a, b, weights = fixture()
        row, _ = t.vector({}, 's', a, b, {'total': t.s.q(1)}, 'source', weights)
        before = deepcopy(weights); d = t.diagnostic(row, weights)
        self.assertEqual(weights, before)
        self.assertTrue(d['individual_feasibility_is_not_joint_fit_or_accuracy'])
        self.assertGreaterEqual(t.s.f(d['maximum_gap_under_same_trust_box_known_gradient']), t.learning.gap(row, weights))

    def test_prespecified_miner_is_not_fit_or_ordinary_inference(self):
        conf = t.configuration()
        self.assertFalse(conf['fit']); self.assertFalse(conf['dev']); self.assertFalse(conf['production'])
        self.assertTrue(conf['positive_loss_is_not_loss_augmented_score']); self.assertEqual(conf['retries'], 0)

    def test_complete_small_runner_preserves_noops_and_never_fits(self):
        graph, ev, _ = toy(end=3, cap=2); weights = fixture()[2]
        target = list(by_path(graph, ((0, 3, C),)))
        zero = {k: t.s.q(0) for k in t.learning.FEATURES}
        inert = dict(sample_id='a', contrast_id='old', entry={'split': 'train'},
            negative_ids=target, target_ids=target, loss=t.s.q(0), score_delta=zero,
            gradient_delta=zero, available=dict.fromkeys(t.learning.FEATURES, True))
        row = dict(sample_id='a', pair_id='pair', work_family_id='family', sample_span={}, split='train')
        saved = {k: row.get(k, 'source') for k in t.refresh.SOURCE_FIELDS}
        saved['entry'] = {'split': 'train', 'work_family_id': 'family'}
        ctx = dict(pool=[inert], rows=[row], previous_records={}, joint_records={}, initial35=weights,
            joint_packets={'a': {'arms': {'epoch3_target': {'path_ids': target}}}},
            refs={'a': {}}, use={}, manifest={}, parent_sha='parent',
            joint_report={'excluded_parent_scopes_preserved': []})
        with TemporaryDirectory() as d, patch.object(t, 'context', return_value=ctx), \
                patch.object(t.prior.prior.prior.old.prior, 'prepare_sample',
                    return_value=(saved, saved['entry'], graph, ev, None, {})), \
                patch.object(t.refresh, 'loss_object', return_value=loss(graph, [(0, 3, C)])), \
                patch.object(t.refresh, 'clear'), patch.object(t.learning, 'validate_rows'), \
                patch.object(t.learning, 'fit', side_effect=AssertionError('fit forbidden')):
            r = t.run(Path(d)/'out')
            self.assertTrue(r['complete']); self.assertFalse(r['fit_performed'])
            self.assertEqual(r['counts']['positive_wrong_competitors'], 1)
            self.assertEqual(r['active_contrasts'], 1)
            history = t.load(Path(d)/'out/inactive-original-noops.json.gz')
            self.assertEqual(history['rows'], [inert])
            self.assertEqual(len(r['records']), 1)

    def test_parent_seal_rejection_precedes_deep_context(self):
        def read(path, expected):
            if str(path).endswith('report.json'):
                return {'complete': False}
            return {}
        with patch.object(t.prior, 'context', side_effect=AssertionError('deep read')):
            with self.assertRaisesRegex(ValueError, 'not_sealed_train'): t.context(read)


if __name__ == '__main__': unittest.main()
