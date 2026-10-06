from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_exact_beat_train_trial as t
from test_harmony_member_role_scoring import toy
from test_harmony_joint_balance_learning import initial


def evaluation(selected=True, hit=True, duration=4):
    q = t.benchmark.rational
    components = {f: dict(eligible=q(duration), matched=q(duration if hit else 0),
        covered=q(duration if selected else 0), grid_eligible=duration*8,
        grid_matched=duration*8 if hit else 0, grid_covered=duration*8 if selected else 0)
        for f in t.benchmark.FIELDS}
    return dict(context_time=q(duration), selected=selected, fully_evaluable=True,
        selected_hit=hit, semantic_boundary_exact=dict(matched=0, extra=0, missed=0), components=components)


class ExactBeatTrainTests(unittest.TestCase):
    def test_proof_must_be_sealed_before_loading_train(self):
        def read(p, expected): return dict(complete=False)
        with patch.object(t.train, 'context', side_effect=AssertionError('unsealed')):
            with self.assertRaisesRegex(ValueError, 'proof_not_sealed'): t.context(read)

    def test_no_overwrite_precedes_validation_or_input_reads(self):
        with TemporaryDirectory() as d, patch.object(t.io, 'digest', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d, 'missing')

    def test_failed_validation_rejected_before_context(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'validation.json'; t.io.write(p, dict(passed=False))
            with patch.object(t, 'context', side_effect=AssertionError('read')):
                with self.assertRaisesRegex(ValueError, 'validation_not_passed'): t.run(Path(d)/'out', p)

    def test_same_model_metadata_exact_winner_and_operations(self):
        graph, ev, _ = toy(); model = {'model_id': 'frozen-test'}
        old = t.train.select(t.train.prior.prior.Scorer(graph, ev, initial()), model, 'same-sha')
        new = t.select(t.cache.Scorer(graph, ev, initial()), model, 'same-sha', timer=lambda: 0)
        self.assertTrue(t.train.refresh.parent.compatibility(old, new))
        self.assertEqual(old['selected']['proposal_id'], new['selected']['proposal_id'])
        self.assertNotIn('joint_balance_contract', new)
        identity = new['frozen_model_ref']
        self.assertEqual(identity['model_sha256'], 'same-sha'); self.assertFalse(identity['fit_performed_this_selection'])
        self.assertFalse(identity['source_labels_used_for_selection']); self.assertFalse(identity['operational_promotion'])

    def test_wall_abstention_retains_cache_diagnostics_not_partial_winner(self):
        graph, ev, _ = toy(); sc = t.cache.Scorer(graph, ev, initial()); ticks = iter(range(100000))
        before = sc.scalar_values
        r = t.select(sc, {'model_id': 'frozen'}, 'sha', wall_seconds=8, timer=lambda: next(ticks))
        self.assertEqual(r['status'], 'context_wall_budget_abstention'); self.assertIsNone(r['selected'])
        self.assertIsNone(r['transitions']); self.assertFalse(r['partial_winner_returned'])
        self.assertFalse(r['exact_optimum_under_declared_score']); self.assertEqual(sc.scalar_values, before)
        self.assertEqual(r['exact_beat_cache_diagnostics'], t.cache_snapshot(sc))
        self.assertTrue(r['exact_beat_cache_contract']['same_sealed_dp_bytecode'])

    def test_transition_budget_stays_separate_from_wall_and_cache(self):
        graph, ev, _ = toy(); sc = t.cache.Scorer(graph, ev, initial())
        r = t.select(sc, {'model_id': 'frozen'}, 'sha', transition_budget=1, timer=lambda: 0)
        self.assertEqual(r['status'], 'transition_budget_abstention'); self.assertIsNone(r['selected'])
        self.assertFalse(r['exact_optimum_under_declared_score']); self.assertEqual(r['resource_guard']['transition_budget'], 1)

    def test_source_and_independent_receipts_cannot_change(self):
        graph, ev, _ = toy(); weights = initial()
        old, new = t.train.prior.prior.Scorer(graph, ev, weights), t.cache.Scorer(graph, ev, weights)
        r = t.select(new, {'model_id': 'frozen'}, 'sha', timer=lambda: 0)
        archived = deepcopy(r['selected']['context_score'])
        receipts, count = t.replay(old, new, {'post_search_cost_receipts': {'fresh': archived}}, r)
        self.assertEqual(set(receipts), {'historical_fresh', 'fresh'})
        archived['cost']['numerator'] += 1
        with self.assertRaisesRegex(ValueError, 'archived_cost_changed'):
            t.replay(old, new, {'post_search_cost_receipts': {'fresh': archived}}, r)
        a = {k: 'source' for k in t.train.refresh.SOURCE_FIELDS}; b = deepcopy(a); b['original_edge_count'] = 12
        with self.assertRaisesRegex(ValueError, 'original_source_changed'): t.assert_source(a, b)

    def test_common_denominator_not_all_new_completed(self):
        def row(name, old, new, hit, previous_hit, duration):
            return dict(sample_id=name, work_family_id='family', prior_selected_ids=old, selected_ids=new,
                prior_status='selected' if old else 'context_wall_budget_abstention',
                status='selected' if new else 'context_wall_budget_abstention', same_completed_winner=bool(old and new),
                evaluation=evaluation(bool(new), hit, duration), prior_evaluation=evaluation(bool(old), previous_hit, duration))
        rows = [row('common', ['x'], ['x'], True, True, 1),
                row('recovered_wrong', None, ['y'], False, False, 3),
                row('lost_correct', ['z'], None, False, True, 4)]
        s = t.summaries(rows)
        self.assertEqual(s['common_completed']['count'], 1); self.assertEqual(s['all_original']['cached']['contexts'], 3)
        self.assertEqual(s['resources']['recovered_ids'], ['recovered_wrong'])
        self.assertEqual(s['resources']['lost_ids'], ['lost_correct']); self.assertEqual(s['resources']['lost_previous_reference_hit'], 1)
        self.assertEqual(s['resources']['recovered_reference_wrong'], 1)
        self.assertEqual(s['all_original']['cached']['components']['root_members']['time_agreement'], 1/8)
        self.assertEqual(s['all_original']['historical']['components']['root_members']['time_agreement'], 5/8)
        self.assertEqual(s['musical_changes_on_common'], dict(changed_paths=0, newly_correct=0, lost_correct=0))

    def test_fresh_cache_is_not_shared_between_scopes(self):
        graph, ev, _ = toy(); a = t.cache.Scorer(graph, ev, initial()); b = t.cache.Scorer(graph, ev, initial())
        a.beat_cache.extent(ev.source, 0, 1)
        self.assertEqual(t.cache_snapshot(b), dict(calls=0, hits=0, integrations=0, entries=0))

    def test_all_predictions_frozen_before_evaluation_no_fit_and_history_retained(self):
        graph, ev, _ = toy(); weights = initial(); model = dict(model_id='tiny-frozen')
        result = t.train.select(t.train.prior.prior.Scorer(graph, ev, weights), model, t.proof.profile.PINS['model.json.gz'])
        sample = dict(sample_id='tiny', pair_id='pair', work_family_id='family', sample_span={}, split='train')
        saved = {k: sample.get(k, 'source') for k in t.train.refresh.SOURCE_FIELDS}
        saved['original_edge_count'] = len(graph.edges)
        with TemporaryDirectory() as d:
            dest = Path(d)/'out'; oldpath = Path(d)/'old.json.gz'; validation = Path(d)/'validation.json'
            original = saved | dict(result=result, post_search_cost_receipts={'fresh': result['selected']['context_score']})
            t.io.write_packet(oldpath, original)
            prev = dict(artifact=str(oldpath), sha256=t.io.digest(oldpath), status=result['status'],
                selected_ids=list(t.train.s.fresh.path_ids(result['selected'])), evaluation=evaluation())
            ctx = dict(rows=[sample], beat_model=model, beat_weights=weights, beat_previous={'tiny': prev},
                beat_proof={'path_witnesses': 1}, refs={'tiny': {}}, protection_report={'excluded_parent_scopes_preserved': []})
            t.io.write(validation, dict(passed=True, previous_validation_sha256=t.PRIOR_VALIDATION_SHA,
                test_modules=['test_harmony_exact_beat_train_trial']))
            def evaluate(*args):
                f = t.load(dest/'prediction-freeze.json'); self.assertTrue(f['complete'])
                self.assertFalse(f['reference_evaluation_started']); self.assertEqual(len(f['predictions']), 1)
                self.assertFalse(t.load(f['predictions'][0]['artifact'])['reference_evaluation_performed'])
                return evaluation()
            with patch.object(t, 'context', return_value=ctx), patch.object(t, 'prepare', return_value=(saved, {}, graph, ev, None, {})), \
                 patch.object(t.train.refresh, 'clear'), patch.object(t.train, 'evaluate', side_effect=evaluate), \
                 patch.object(t.train.learning, 'fit', side_effect=AssertionError('fit')):
                report = t.run(dest, validation)
            self.assertFalse(report['fit_performed']); self.assertEqual(report['ordinary_fresh_attempts'], 1)
            case = t.load(report['records'][0]['artifact'])
            self.assertEqual(set(case['post_search_cost_receipts']), {'historical_fresh', 'fresh'})
            self.assertTrue(case['full_source_not_clipped']); self.assertFalse(case['human_validated'])
            self.assertTrue(case['same_completed_winner']); self.assertEqual(report['archived_witnesses_preserved'], 1)


if __name__ == '__main__': unittest.main()
