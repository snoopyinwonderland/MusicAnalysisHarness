from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_benchmark_preparation import BASELINE, LEARNED, run
from musicanote_harness.harmony_common_benchmark import evaluate, summarize
from test_harmony_common_benchmark import C, cell, span


def setup(folder):
    def write(path, value):
        path=folder/path;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value),encoding='utf-8');return path
    def entry(family,split):
        return {'manifest_entry_id':family,'work_family_id':family,'split':split,'score_sha256':family+'s',
                'annotation_sha256':family+'a','annotation_lineage_id':family+'l','collection_id':'c',
                'movement_id':'1','work_family_source_key':family,'package_path':'metadata_only_do_not_open',
                'quality':{'source_note_mapping_complete':True},'eligibility':{'blind_evaluation':split=='holdout'},
                'rights':{'internal_research_use':True,'model_training_approved':False}}
    train=entry('train','train');reserve=entry('reserve','holdout')
    identity={'pair_id':'pair','plan_index':0,'sample_id':'s','work_family_id':'train','split':'train',
              'sample_span':span(0,2),'reference_cells':[{'span':span(0,2),'signature':C}]}
    prediction={'source_labels_used_for_selection':False,'segments':[{'span':span(0,2),'root_spelling':C[0],'members':C[1]}]}
    v=evaluate([cell(0,2,C)],[cell(0,2,C)],span(0,2),selected=True)
    s=summarize([{'work_family_id':'train','evaluation':v}])
    oldsummary={k:s[k] for k in ('contexts','selected_contexts','abstained_contexts','fully_evaluable_contexts',
                                  'selected_correct_contexts','selected_context_agreement','semantic_boundary_exact')}
    oldsummary.update(eligible_time=s['components']['root_members']['eligible_time'],
                     selected_root_time_agreement=s['components']['root']['time_agreement'],
                     selected_root_members_time_agreement=s['components']['root_members']['time_agreement'],
                     work_family_macro_root_members_agreement=s['components']['root_members']['work_family_macro'])
    guarded=folder/'guarded.bin';guarded.write_bytes(b'unchanged synthetic source')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=write(Path('manifest.json'),{'entries':[train,reserve]})
    recall=write(Path('recall.json'),{'complete':True,'package_manifest':[train],'records':[identity]})
    baseline=write(Path('baseline.json'),{'complete':True,'records':[identity|{'selected_predictions':{BASELINE:prediction}}],
                                        'summary':{BASELINE:oldsummary}})
    learned=write(Path('learned.json'),{'complete':True,'source_labels_used_at_inference':False,
        'records':[identity|{'selected_prediction':prediction,'expanded_lattice_hit':True,
                            'source_context_artifact':'synthetic source ref','source_context_sha256':'synthetic pin'}],
        'summary':{LEARNED:oldsummary},'input_hashes':{str(guarded):digest(guarded)},'code_hashes':{}})
    evidence=folder/'history.md';evidence.write_text('synthetic historical result',encoding='utf-8')
    ledger=write(Path('ledger.json'),{'history_complete':False,'records':[{'work_family_id':'reserve',
        'musical_result_exposed':True,'evidence_paths':[str(evidence)]}]})
    prep=write(Path('pairs/c/W01-1/preparation_report.json'),{'source_paths':{'score':'W01-1.musicxml'},
        'source_sha256':{'score':'newscore','harmonies':'newannotation'},'imported_annotations':1,
        'ambiguous_alignments':0,'exact_alignments':0,'verified_transform_alignments':1,
        'source_note_mapping':{'complete':True},'measure_alignment_blocking_issues':{}})
    batch=write(Path('batch.json'),{'outcomes':[{'pair_id':'new','report_path':str(prep)}]})
    paths=manifest,recall,baseline,learned,ledger,batch
    return paths,[digest(p) for p in paths],guarded,prep


class BenchmarkPreparationTests(unittest.TestCase):
    def test_physical_replay_preserves_inputs_and_no_false_blind_claim(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,guarded,prep=setup(root);before=[p.read_bytes() for p in paths]
            r=run(*paths,root/'out',expected_hashes=pins)
            self.assertEqual([p.read_bytes() for p in paths],before)
            self.assertTrue(r['complete']);self.assertFalse(r['independent_test_accuracy_measured'])
            self.assertFalse(r['reserved_score_or_annotation_contents_read']);self.assertFalse(r['training_performed'])
            self.assertEqual(r['inventory_summary']['staged_families'],1)
            self.assertEqual(r['candidate_diagnostics'][LEARNED],{'selected_correct':1})
            report=json.loads((root/'out/report.json').read_text())
            self.assertTrue(report['original_holdout_audit'][0]['known_exposure_excluded'])
            plan=json.loads((root/'out/independent-evaluation-plan.json').read_text())
            self.assertFalse(plan['blind_approval_granted']);self.assertEqual(plan['new_test_predictions'],0)
            self.assertEqual(len(list((root/'out').iterdir())),3)
            with self.assertRaisesRegex(ValueError,'overwrite'):run(*paths,root/'out',expected_hashes=pins)

    def test_bad_pin_no_output(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,*_=setup(root);pins[0]='wrong'
            with self.assertRaisesRegex(ValueError,'input_sha_mismatch'):run(*paths,root/'out',expected_hashes=pins)
            self.assertFalse((root/'out').exists())

    def test_source_guard_still_enforced(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,guarded,_=setup(root);guarded.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'frozen_input_changed'):run(*paths,root/'out',expected_hashes=pins)
            self.assertFalse((root/'out').exists())

    def test_parent_summary_change_detected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,*_=setup(root)
            body=json.loads(paths[2].read_text());body['summary'][BASELINE]['selected_correct_contexts']=0
            paths[2].write_text(json.dumps(body));pins[2]=hashlib.sha256(paths[2].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'common_metric_replay_mismatch'):run(*paths,root/'out',expected_hashes=pins)

    def test_identity_change_detected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,*_=setup(root)
            body=json.loads(paths[3].read_text());body['records'][0]['split']='dev'
            paths[3].write_text(json.dumps(body));pins[3]=hashlib.sha256(paths[3].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'cohort_identity_changed'):run(*paths,root/'out',expected_hashes=pins)

    def test_true_prediction_with_false_ceiling_rejected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,*_=setup(root)
            body=json.loads(paths[3].read_text());body['records'][0]['expanded_lattice_hit']=False
            paths[3].write_text(json.dumps(body));pins[3]=hashlib.sha256(paths[3].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'outside_ceiling'):run(*paths,root/'out',expected_hashes=pins)

    def test_source_incomplete_not_scheduled(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,_,prep=setup(root)
            body=json.loads(prep.read_text());body['source_note_mapping']['complete']=False;prep.write_text(json.dumps(body))
            r=run(*paths,root/'out',expected_hashes=pins)
            self.assertEqual(r['inventory_summary']['staged_families'],0)

    def test_null_ceiling_is_unavailable_not_confirmed_missing(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,*_=setup(root)
            blank=evaluate([cell(0,2,C)],[cell(0,2)],span(0,2),selected=False)
            s=summarize([{'work_family_id':'train','evaluation':blank}])
            for index,arm in ((2,BASELINE),(3,LEARNED)):
                body=json.loads(paths[index].read_text());row=body['records'][0]
                if index==2:row['selected_predictions'][BASELINE]=None
                else:row['selected_prediction']=None;row['expanded_lattice_hit']=None
                previous=body['summary'][arm]
                for key in ('contexts','selected_contexts','abstained_contexts','fully_evaluable_contexts',
                            'selected_correct_contexts','selected_context_agreement','semantic_boundary_exact'):
                    previous[key]=s[key]
                previous['selected_root_time_agreement']=0.0;previous['selected_root_members_time_agreement']=0.0
                previous['work_family_macro_root_members_agreement']=0.0
                paths[index].write_text(json.dumps(body));pins[index]=hashlib.sha256(paths[index].read_bytes()).hexdigest()
            r=run(*paths,root/'out',expected_hashes=pins)
            self.assertEqual(r['candidate_diagnostics'][LEARNED],{'candidate_ceiling_unavailable':1})

    def test_cap_is_predeclared_not_tuned_after_result(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,*_=setup(root)
            with self.assertRaisesRegex(ValueError,'predeclared'):
                run(*paths,root/'out',expected_hashes=pins,families_per_collection=3)

    def test_split_alias_leakage_rejected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);paths,pins,*_=setup(root)
            body=json.loads(paths[0].read_text());body['entries'][1]['score_sha256']=body['entries'][0]['score_sha256']
            paths[0].write_text(json.dumps(body));pins[0]=hashlib.sha256(paths[0].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'cross_split'):run(*paths,root/'out',expected_hashes=pins)


if __name__=='__main__':unittest.main()
