from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from musicanote_harness import harmony_support_balance_trial as trial
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_common_benchmark import evaluate,native_prediction,native_reference,summarize
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture,sample
from test_harmony_exact_frontier import problem
from test_harmony_structured_learning import entry,contract
from test_harmony_support_balance_learning import row as train_row


class BalanceTrialTests(unittest.TestCase):
    def disk(self,mode):
        with TemporaryDirectory() as folder:
            root=Path(folder);source=root/'prior';source.mkdir();output=root/'new'
            ir=fixture();target=sample();graph,ev=problem(ir)
            irpath=source/'ir.json.gz';trial.expanded.write_packet(irpath,ir)
            xml=source/'source.musicxml';xml.write_bytes(b"<score-partwise version='4.0'/>")
            src={'canonical_ir_path':str(irpath),'source_musicxml_path':str(xml),'original_ir_content_sha256':_hash(ir),
                'original_musicxml_sha256':trial.expanded.digest(xml),'full_score_saved_with_surrounding_context':True}
            gp=source/'graph.json.gz'
            def save_graph():trial.expanded.write_packet(gp,{'pair_id':'pair','sample_id':target['sample_id'],
                'span':target['span'],'source':src,'problem':trial.prior.prior.graph_packet(graph)})
            save_graph();chosen=trial.scoring.prior.decode(graph,ev,arm='control')
            arm={'status':'source_preflight_abstention','selected_prediction':None} if mode=='abstention' else {'status':chosen['status'],'selected_prediction':chosen['selected']}
            packet={'pair_id':'pair','sample_id':target['sample_id'],'sample_span':target['span'],'plan_index':0,
                'collection_id':'c','work_family_id':'dev_family','reference_binding_verified':True,'attempted':mode!='abstention',
                'known_prior_diagnostic':True,'source_clock_gate':SourceClockGuard(ir).scope(target['span']),
                'arms':{'control':arm},'graph_artifact':str(gp),'graph_sha256':trial.expanded.digest(gp)}
            if mode=='contamination':packet['arms']['control']['evaluation']={}
            if mode=='graph':packet['graph_sha256']='changed'
            if mode=='source':src['original_musicxml_sha256']='changed';save_graph();packet['graph_sha256']=trial.expanded.digest(gp)
            pred=source/'p.json.gz';trial.expanded.write_packet(pred,packet)
            trial.expanded.write(source/'run-contract.json',{'code_pins':{},'source_labels_used_at_inference':False})
            trial.expanded.write(source/'prediction-freeze.json',{'contexts':1,'labels_read':False,'prediction_hashes':{str(pred):trial.expanded.digest(pred)}})
            record=deepcopy(packet);record['reference_cells']=[{'span':target['span'],'signature':[['C',0],[['C',0],['E',0],['G',0]]]}]
            record['candidate_ceiling']={'oracle_reference_witness':None};result=record['arms']['control']
            result['evaluation']=evaluate(native_reference(record),native_prediction(result['selected_prediction'],target['span']),target['span'],selected=result['selected_prediction'] is not None)
            tables={'control':summarize([record|result])}
            trial.expanded.write(source/'report.json',{'records':[record],'tables':tables,'input_hashes':{},'code_hashes':{},'artifact_hashes':{},'cases':[]})
            original=trial.load
            def read(p):
                if Path(p)==source/'report.json':
                    seal=original(output/'prediction-freeze.json');self.assertFalse(seal['dev_labels_read'])
                    self.assertTrue(seal['training_reference_labels_used'])
                    self.assertEqual(seal['model_sha256'],trial.expanded.digest(output/'model.json'))
                return original(p)
            def prepare(read_fn,save,dest):
                m=[entry()];c=contract(m);c['parent_recall_sha256']=trial.training.PARENT_SHA
                fitted=trial.learning.fit([train_row()],c,m,trial.training.PARENT_SHA)
                save(dest/'model.json',fitted)
                return fitted,c,m,{'counts':{'eligible_contrasts':1}}
            with patch.object(trial,'BASELINE_REPORT_SHA',trial.expanded.digest(source/'report.json')),\
                 patch.object(trial,'load',side_effect=read),patch.object(trial.training,'prepare',side_effect=prepare),\
                 patch.object(trial.prior.prior,'prepare',side_effect=AssertionError('dev_graph_rebuild_forbidden')):
                if mode in ('contamination','graph','source'):
                    with self.assertRaisesRegex(ValueError,'changed|reference_bearing'):trial.run(source,output)
                else:
                    result=trial.run(source,output);report=original(output/'report.json')
                    self.assertFalse(result['dev_graph_generation_performed']);self.assertFalse(result['production_modified'])
                    self.assertEqual(report['tables']['control'],tables['control'])
                    self.assertEqual(result['named_family_overlap'],[])

    def test_seal_model_and_predictions_before_dev_reference(self):self.disk('selected')
    def test_old_abstention_unchanged(self):self.disk('abstention')
    def test_dev_reference_contamination_rejected(self):self.disk('contamination')
    def test_graph_hash_rejected(self):self.disk('graph')
    def test_source_hash_rejected(self):self.disk('source')
    def test_no_overwrite(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'output_exists'):trial.run('missing',d)

    def test_historical_contrasts_deduplicated_across_epochs(self):
        item={'sample_id':'s','epoch':1,'adversary_group_refs':['n'],'training_target_group_refs':['t'],'loss':{'total':1}}
        groups,counts=trial.training.contrasts({'updates':[item,item|{'epoch':2}],'feature_collisions':[]})
        self.assertEqual(len(groups['s']),1);self.assertEqual(counts['historical_update_records'],2)
        with self.assertRaisesRegex(ValueError,'loss_changed'):
            trial.training.contrasts({'updates':[item,item|{'loss':{'total':2}}],'feature_collisions':[]})

