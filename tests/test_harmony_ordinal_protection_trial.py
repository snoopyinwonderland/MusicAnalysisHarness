from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_ordinal_protection_trial as t
from test_harmony_member_role_scoring import toy, by_path, C
from test_harmony_joint_balance_learning import initial, row as vector
from test_harmony_structured_learning import entry, contract


class OrdinalTrialTests(unittest.TestCase):
    def test_no_overwrite_precedes_deep_input_reads(self):
        with TemporaryDirectory() as d, patch.object(t, 'context', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d)

    def test_parent_seal_rejection_before_context(self):
        def read(p, expected):
            return {'complete': False} if str(p).endswith('report.json') else {}
        with patch.object(t.prior, 'context', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'not_sealed'): t.context(read)

    def test_small_trial_freezes_before_ordinary_selection_and_preserves_cases(self):
        graph, ev, _ = toy(); ids = by_path(graph, ((0, 4, C),))
        v = vector(); e = entry(); scope = dict(sample_id='sample', pair_id='pair',
            work_family_id='family', sample_span={}, split='train')
        historical = dict(selected_ids=list(ids), evaluation={'selected_hit': True}, artifact='old', sha256='oldsha')
        saved = {k: scope.get(k, 'source') for k in t.refresh.SOURCE_FIELDS}; saved['entry'] = e
        ctx = dict(rows=[scope], active_pool=[v], competitors=[], missing_protections=[], initial35=initial(),
            use=contract([e]), manifest=[e], parent_sha='parent', refs={'sample': {}},
            previous_records={'sample': historical}, joint_records={'sample': historical},
            stage80_records={'sample': dict(baseline_ids=list(ids), baseline_evaluation={'selected_hit': True})},
            joint_packets={'sample': {'arms': {'epoch3_target': {'path_ids': list(ids)}}}},
            protection_report={'excluded_parent_scopes_preserved': []})
        def select(sc, model, sha):
            self.assertTrue((dest/'model-freeze.json').is_file())
            self.assertEqual(t.io.digest(dest/'model.json.gz'), sha)
            return dict(status='selected', selected={'segments': [{'semantic_group_ref': x} for x in ids],
                'context_score': sc.path_receipt(ids)}, resource_guard={'elapsed_seconds': 0})
        with TemporaryDirectory() as d:
            dest = Path(d)/'out'
            with patch.object(t, 'context', return_value=ctx), \
                 patch.object(t.prior.prior.prior.prior.old.prior, 'prepare_sample',
                    return_value=(saved, e, graph, ev, None, {})), \
                 patch.object(t, 'select', side_effect=select), patch.object(t.refresh, 'clear'), \
                 patch.object(t, 'evaluate', return_value={'selected_hit': True}), \
                 patch.object(t, 'summarize', return_value={'synthetic': True}):
                r = t.run(dest)
            self.assertEqual(r['ordinary_fresh_attempts'], 1); self.assertTrue(r['fit_performed'])
            self.assertFalse(r['current_dev_reconstructed_or_used']); self.assertFalse(r['production_modified'])
            case = t.load(Path(r['records'][0]['artifact']))
            self.assertTrue(case['full_source_not_clipped']); self.assertFalse(case['human_validated'])
            self.assertEqual(set(case['post_search_cost_receipts']),
                {'fresh', 'previous_member_role', 'previous_joint_balance', 'frozen_old26', 'stored_target'})

    def test_selection_identity_not_old_fit_and_labels_absent(self):
        graph, ev, _ = toy(); sc = t.prior.prior.Scorer(graph, ev, initial())
        r = t.select(sc, {'model_id': 'new'}, 'newsha')
        self.assertNotIn('joint_balance_contract', r)
        self.assertEqual(r['frozen_model_ref']['model_sha256'], 'newsha')
        self.assertFalse(r['frozen_model_ref']['source_labels_used_for_selection'])
        self.assertTrue(r['ordinal_protection_contract']['all_35_weights_frozen_during_selection'])


if __name__ == '__main__': unittest.main()
