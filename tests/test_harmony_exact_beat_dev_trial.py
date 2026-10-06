from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_exact_beat_dev_trial as t
from test_harmony_member_role_scoring import toy
from test_harmony_joint_balance_learning import initial
from test_harmony_exact_beat_train_trial import evaluation


class ExactBeatDevTests(unittest.TestCase):
    def test_no_overwrite_before_reads(self):
        with TemporaryDirectory() as d, patch.object(t.io, 'digest', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError, 'output_exists'): t.run(d, 'missing')

    def test_sealed_train_required_before_current_dev_inputs(self):
        with patch.object(t.fresh, 'context', side_effect=AssertionError('context')):
            with self.assertRaisesRegex(ValueError, 'train_not_sealed'): t.setup(lambda p, h: dict(complete=False))

    def test_raw_previous_predictions_have_no_current_reference(self):
        p = dict(arms={a: {'selected_prediction': None} for a in t.dev.ARMS})
        t.require_raw(p)
        for field in ('reference_cells', 'candidate_ceiling'):
            with self.assertRaisesRegex(ValueError, 'reference_in_raw'): t.require_raw(p | {field: []})
        p['arms'][t.ARM]['evaluation'] = {}
        with self.assertRaisesRegex(ValueError, 'reference_in_raw'): t.require_raw(p)

    def test_exact_winner_metadata_and_dp_counts_match_previous_implementation(self):
        graph, ev, _ = toy(); weights = initial(); before = deepcopy(weights)
        old = t.dev.ordinary(graph, ev, weights, {}, t.ARM, timer=lambda: 0)
        with patch.object(t.fresh.train.learning, 'fit', side_effect=AssertionError('fit')):
            new = t.ordinary(graph, ev, weights, {}, timer=lambda: 0)
        self.assertEqual(weights, before); self.assertTrue(t.fresh.train.refresh.parent.compatibility(old, new))
        self.assertEqual(old['selected']['proposal_id'], new['selected']['proposal_id'])
        self.assertEqual(new['frozen_model_ref'], old['frozen_model_ref'])
        self.assertNotIn('joint_balance_contract', new); self.assertNotIn('ordinal_protection_contract', new)
        self.assertEqual(new['exact_beat_cache_contract']['version'], t.fresh.cache.VERSION)

    def test_wall_and_transition_budget_have_no_partial_or_reused_winner(self):
        graph, ev, _ = toy(); ticks = iter(range(10000)); weights = initial()
        wall = t.ordinary(graph, ev, weights, {}, wall_seconds=.1, timer=lambda: next(ticks))
        budget = t.ordinary(graph, ev, weights, {}, transition_budget=1, timer=lambda: 0)
        self.assertEqual(wall['status'], 'context_wall_budget_abstention')
        self.assertFalse(wall['partial_winner_returned']); self.assertIsNone(wall['selected'])
        self.assertEqual(budget['status'], 'transition_budget_abstention'); self.assertIsNone(budget['selected'])
        for r in (wall, budget):
            self.assertFalse(r['exact_optimum_under_declared_score'])
            self.assertEqual(r['frozen_model_ref']['model_sha256'], t.dev.MODEL_SHAS[t.ARM])
            self.assertIn('entries', r['exact_beat_cache_diagnostics'])

    def test_all_historical_paths_and_reference_witness_preserved(self):
        graph, ev, _ = toy(); weights = initial(); result = t.ordinary(graph, ev, weights, {}, timer=lambda: 0)
        sc = t.dev.train.Scorer(graph, ev, weights); ids = t.dev.s.fresh.path_ids(result['selected'])
        case = dict(same_weight_path_receipts={t.ARM:{a:sc.path_receipt(ids) for a in t.dev.ARMS}},
                    reference_witness_receipts={t.ARM:sc.path_receipt(ids, target=True)})
        row = dict(sample_span={}, cached={'selected_prediction':result['selected']})
        with patch.object(t.dev, 'evidence', return_value=(ev, {})), patch.object(t.dev.train.prior.prior, 'clear'):
            receipts, count, original = t.replay(graph, {}, {}, {}, None, row, case, weights)
            self.assertEqual(len(receipts), 5); self.assertEqual(original, 4)
            self.assertIn('reference_witness', receipts); self.assertIn('fresh', receipts)
            case['same_weight_path_receipts'][t.ARM][t.ARM]['cost']['numerator'] += 1
            with self.assertRaisesRegex(ValueError, 'historical_receipt_changed'):
                t.replay(graph, {}, {}, {}, None, row, case, weights)

    def test_common_completed_not_all_new_completed_and_duplicate_identity_not_collapsed(self):
        def row(pair, sample, old, new, old_hit, hit, duration, attempted=True):
            value = lambda selected, correct: dict(selected_prediction=selected, status='complete' if selected else 'wall',
                evaluation=evaluation(selected is not None, correct, duration))
            return dict(pair_id=pair, sample_id=sample, sample_span={}, work_family_id='family', attempted=attempted,
                same_completed_winner=bool(old and new), historical_arms={a:value(old,old_hit) for a in t.dev.ARMS},
                cached=value(new,hit))
        rows=[row('p1','same',['x'],['x'],True,True,1), row('p2','same',None,['y'],False,False,3),
              row('p1','lost',['z'],None,True,False,4), row('p1','blocked',None,None,False,False,2,False)]
        with patch.object(t.dev.s.fresh, 'path_ids', side_effect=lambda x:x): result=t.metrics(rows)
        s=result['against_same_frozen_ordinal35']; self.assertEqual(s['resources']['common_completed'],1)
        self.assertEqual(s['all_original']['cached']['contexts'],4)
        self.assertEqual(s['all_original']['cached']['components']['root_members']['time_agreement'],.1)
        self.assertEqual(s['resources']['recovered_reference_wrong'],1); self.assertEqual(s['resources']['lost_reference_hit'],1)
        self.assertEqual(result['original_input_abstentions'],1); self.assertEqual(t.key(rows[0]),('p1','same'))
        self.assertEqual(t.key(rows[1]),('p2','same'))

    def test_all_predictions_sealed_before_reference_open_and_input_abstention_not_retried(self):
        graph, ev, _ = toy(); weights = initial(); result = t.dev.ordinary(graph, ev, weights, {}, t.ARM, timer=lambda: 0)
        fields = dict(pair_id='p', sample_id='ok', sample_span={}, plan_index=0, collection_id='toy',
            work_family_id='family', reference_binding_verified=True, source_clock_gate={}, attempted=True, known_prior_diagnostic={})
        blocked = fields | dict(sample_id='blocked', attempted=False, plan_index=1)
        arm = dict(status=result['status'], selected_prediction=result['selected'], elapsed_seconds=0, result=result)
        rejection = dict(status='old_input_rejection', selected_prediction=None, elapsed_seconds=0, reused_old_abstention=True)
        with TemporaryDirectory() as d:
            folder=Path(d); dest=folder/'out'; validation=folder/'validation.json'; previous=folder/'previous'
            source=folder/'source'; previous.mkdir(); source.mkdir()
            packets=[fields|dict(arms={a:deepcopy(arm) for a in t.dev.ARMS},graph_artifact='graph',graph_sha256='sha',source={}),
                     blocked|dict(arms={a:deepcopy(rejection) for a in t.dev.ARMS})]
            for i,p in enumerate(packets):
                path=folder/(str(i)+'.json.gz'); t.io.write_packet(path,p)
                p|=dict(historical_prediction_ref=str(path),historical_prediction_sha256=t.io.digest(path))
            hist=[]
            for p in packets:
                r=deepcopy(p); r['arms']={a:v|dict(evaluation=evaluation(r['attempted'],r['attempted'])) for a,v in r['arms'].items()}; hist.append(r)
            t.io.write(previous/'report.json',dict(records=hist,cases=[dict(pair_id='p',sample_id='ok',case_path='oldcase')],
                input_hashes={},artifact_hashes={},code_hashes={}))
            refs=[p|dict(reference_cells=[],candidate_ceiling=None) for p in packets]
            t.io.write(source/'report.json',dict(records=refs,input_hashes={},artifact_hashes={},code_hashes={}))
            t.io.write(validation,dict(passed=True,previous_validation_sha256=t.PRIOR_VALIDATION_SHA,
                test_modules=['test_harmony_exact_beat_dev_trial']))
            real_load=t.load
            def load(path):
                if Path(path) in (source/'report.json',previous/'report.json'):
                    freeze=real_load(dest/'prediction-freeze.json'); self.assertTrue(freeze['complete']); self.assertEqual(len(freeze['predictions']),2)
                    self.assertFalse(freeze['current_reference_report_opened'])
                return real_load(path)
            def prepare(row,*args): self.assertTrue(row['attempted']); return graph,{}, {},{}, {},None
            oldcase=folder/'oldcase'; t.io.write(oldcase,{})
            histpath=t.load(previous/'report.json'); histpath['cases'][0]['case_path']=str(oldcase); t.io.write(previous/'report.json',histpath)
            with patch.object(t,'setup',return_value=({'rows':[{'work_family_id':'train'}]},weights,packets)), \
                 patch.object(t,'ROOT',previous), patch.object(t,'PINS',{'report.json':t.io.digest(previous/'report.json')}), \
                 patch.object(t.dev,'SOURCE_ROOT',source), patch.object(t.dev,'SOURCE_PINS',{'report.json':t.io.digest(source/'report.json')}), \
                 patch.object(t,'load',side_effect=load), patch.object(t.dev,'prepare',side_effect=prepare), \
                 patch.object(t.dev,'evidence',return_value=(ev,{})), patch.object(t.dev.train.prior.prior,'clear'), \
                 patch.object(t.dev,'evaluate',side_effect=lambda *a,**kw:evaluation(kw['selected'],kw['selected'])), \
                 patch.object(t.dev,'native_reference',return_value=[]), patch.object(t.dev,'native_prediction',return_value=[]), \
                 patch.object(t,'replay',return_value=({},0,0)), patch.object(t.fresh.train.learning,'fit',side_effect=AssertionError('fit')):
                report=t.run(dest,validation)
            self.assertEqual(report['original_records'],2); self.assertEqual(report['ordinary_fresh_attempts'],1)
            self.assertEqual(report['records'][1]['cached']['status'],'old_input_rejection')
            self.assertFalse(report['fit_performed']); self.assertEqual(len(report['cases']),1)


if __name__ == '__main__': unittest.main()
