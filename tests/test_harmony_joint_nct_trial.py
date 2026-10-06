from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_joint_nct_trial as trial
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_common_benchmark import evaluate,native_prediction,native_reference,summarize
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture,sample
from test_harmony_exact_frontier import problem


class JointNCTTrialTests(unittest.TestCase):
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
                'span':target['span'],'source':src,'problem':trial.prior.prior.graph_packet(graph),'receipts':{}})
            save_graph();chosen=trial.scoring.component.decode(graph,ev,arm='control')
            arms={'control':{'status':'source_preflight_abstention','selected_prediction':None} if mode=='abstention' else
                {'status':chosen['status'],'selected_prediction':chosen['selected']}}
            packet={'pair_id':'pair','sample_id':target['sample_id'],'sample_span':target['span'],'plan_index':0,
                'collection_id':'c','work_family_id':'family','reference_binding_verified':True,'attempted':mode!='abstention',
                'known_prior_diagnostic':True,'source_clock_gate':SourceClockGuard(ir).scope(target['span']),
                'arms':arms,'graph_artifact':str(gp),'graph_sha256':trial.expanded.digest(gp)}
            if mode=='contamination':packet['arms']['control']['evaluation']={}
            if mode=='graph':packet['graph_sha256']='changed'
            if mode=='source':src['original_musicxml_sha256']='changed';save_graph();packet['graph_sha256']=trial.expanded.digest(gp)
            pred=source/'p.json.gz';trial.expanded.write_packet(pred,packet)
            pins={str(Path(trial.__file__).resolve()):'changed'} if mode=='code' else {}
            trial.expanded.write(source/'run-contract.json',{'code_pins':pins,'source_labels_used_at_inference':False})
            trial.expanded.write(source/'prediction-freeze.json',{'contexts':1,'labels_read':False,'prediction_hashes':{str(pred):trial.expanded.digest(pred)}})
            record=deepcopy(packet);record['reference_cells']=[{'span':target['span'],'signature':[['C',0],[['C',0],['E',0],['G',0]]]}]
            record['candidate_ceiling']={'oracle_reference_witness':None}
            result=record['arms']['control']
            result['evaluation']=evaluate(native_reference(record),native_prediction(result['selected_prediction'],target['span']),target['span'],selected=result['selected_prediction'] is not None)
            tables={'control':summarize([record|result])}
            trial.expanded.write(source/'report.json',{'records':[record],'tables':tables,'input_hashes':{},'code_hashes':{},'artifact_hashes':{},'cases':[]})
            original=trial.load
            def read(p):
                if Path(p)==source/'report.json':
                    seal=original(output/'prediction-freeze.json');self.assertFalse(seal['labels_read'])
                    for path,sha in seal['prediction_hashes'].items():self.assertEqual(trial.expanded.digest(path),sha)
                return original(p)
            with patch.object(trial,'BASELINE_REPORT_SHA',trial.expanded.digest(source/'report.json')),patch.object(trial,'load',side_effect=read),\
                 patch.object(trial.prior.prior,'prepare',side_effect=AssertionError('graph_rebuild_forbidden')):
                if mode in ('contamination','graph','source','code'):
                    with self.assertRaisesRegex(ValueError,'changed|reference_bearing'):trial.run(source,output)
                    return
                result=trial.run(source,output);report=original(output/'report.json')
                self.assertEqual(result['contexts'],1);self.assertFalse(result['graph_generation_performed'])
                self.assertEqual(result['fresh_selected_scopes'],int(mode!='abstention'))
                self.assertEqual(report['tables']['control'],tables['control'])
                self.assertEqual(set(report['tables']),set(trial.scoring.ARMS))
                self.assertFalse(result['complete_nct_accuracy_measured'])
                self.assertFalse(result['new_rules_adopted_for_production'])

    def test_seal_before_reference_read_and_same_graph(self):self.disk('selected')
    def test_old_abstention_keeps_denominator(self):self.disk('abstention')
    def test_nested_reference_contamination_rejected(self):self.disk('contamination')
    def test_graph_hash_required(self):self.disk('graph')
    def test_full_source_hash_required(self):self.disk('source')
    def test_sealed_old_code_required(self):self.disk('code')
    def test_recursive_reference_guard(self):
        with self.assertRaisesRegex(ValueError,'reference_bearing'):trial.prior.check_prediction({'a':[{'oracle_reference_witness':[]}]})
    def test_no_overwrite(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'output_exists'):trial.run('missing',folder)


if __name__=='__main__':unittest.main()
