"""Replay Train contrast features/model and Dev winner costs after sealing."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_support_balance_trial as trial
from musicanote_harness.harmony_common_benchmark import evaluate,native_prediction,native_reference,summarize
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_progression_search import _hash
from audit_harmony_temporal_scoring import compare_packet


def check_confirmation(selected):
    if (selected['confidence'] is not None or selected['human_validated'] is not False
            or selected['support_balance']['confirmed_nct'] is not False):
        raise ValueError('unsupported_confirmation')


def run(root):
    root=Path(root);dest=root/'post-seal-audit.json'
    if dest.exists():raise ValueError('output_exists_no_overwrite')
    report=trial.load(root/'report.json');freeze=trial.load(root/'prediction-freeze.json')
    pins=report['input_hashes']|report['code_hashes']|report['artifact_hashes']
    def check():
        for p,h in pins.items():
            if trial.expanded.digest(p)!=h:raise ValueError('guard_changed:'+p)
    check()
    if freeze['dev_labels_read'] is not False or freeze['contexts']!=report['contexts']:raise ValueError('seal_changed')
    contract=trial.load(root/'run-contract.json');model=trial.load(root/'model.json')
    if freeze['model_sha256']!=contract['model_sha256'] or trial.expanded.digest(root/'model.json')!=freeze['model_sha256']:
        raise ValueError('frozen_model_changed')
    parents={p:trial.load(p) for p in trial.training.PINS};previous,recall,integration,use_contract,old_model,learned=parents.values()
    manifest=recall['package_manifest'];weights=trial.learning.model_weights(model,use_contract,manifest,trial.training.PARENT_SHA)
    dataset=trial.load(root/'training-contrasts.json.gz')
    if _hash(dataset)!=model['training_dataset_content_sha256']:raise ValueError('training_dataset_changed')
    replay=trial.learning.fit(dataset['rows'],use_contract,manifest,trial.training.PARENT_SHA)
    replay['training_dataset_content_sha256']=_hash(dataset);replay['negative_pool']=model['negative_pool']
    if _hash(replay)!=_hash(model):raise ValueError('training_model_replay_changed')
    def read(p,expected=None,compressed=False,raw=False):
        if expected and trial.expanded.digest(p)!=expected:raise ValueError('train_input_changed')
        return None if raw else trial.load(p)
    refs={r['sample_id']:r for r in learned['records']};prev={r['sample_id']:r for r in previous['records']}
    grouped={}
    for row in dataset['rows']:grouped.setdefault(row['sample_id'],[]).append(row)
    train_count=0
    for sample,rs in sorted(grouped.items()):
        ref=refs[sample];entry,graph,ev,clock,args=trial.training.prepare_context(prev[sample],ref,manifest,integration,read)
        if not clock.scope(ref['sample_span'])['accepted']:raise ValueError('train_clock_changed')
        scorer=trial.scoring.Scorer(graph,ev,build_index=False,**args);cells=tuple(trial.training.old.cells_from_record(ref))
        for row in rs:
            item={k:row[k] for k in ('contrast_id','negative_ids','target_ids','loss_details','historical_kind')}
            actual=trial.training.contrast_row(item,entry,graph,ev,args,scorer,cells)|{'sample_id':sample}
            if _hash(actual)!=_hash(row):raise ValueError('train_contrast_replay_changed')
            train_count+=1
        clock.check_source()
        if train_count%20< len(rs):print(f'[audit Train] {train_count}/{len(dataset["rows"])} contrasts',flush=True)
    source=Path(contract['baseline_source'])
    prior={(r['pair_id'],r['sample_id']):r for r in map(trial.load,trial.load(source/'prediction-freeze.json')['prediction_hashes'])}
    sealed={(r['pair_id'],r['sample_id']):r for r in map(trial.load,freeze['prediction_hashes'])}
    tables={a:[] for a in trial.ARMS};cache={};scores=edges=0
    for row in report['records']:
        key=row['pair_id'],row['sample_id'];old=prior.pop(key);packet=sealed.pop(key)
        trial.prior.check_prediction(packet);compare_packet(packet,row)
        for a,result in row['arms'].items():
            value=evaluate(native_reference(row),native_prediction(result['selected_prediction'],row['sample_span']),row['sample_span'],selected=result['selected_prediction'] is not None)
            if value!=result['evaluation']:raise ValueError('evaluation_changed')
            tables[a].append(row|result)
        if not row['attempted']:
            if any(r['selected_prediction'] is not None or r['status']!=old['arms']['control']['status'] for r in row['arms'].values()):raise ValueError('old_abstention_changed')
            continue
        if _hash(trial.prior.prior.musical_value(row['arms']['control']['selected_prediction']))!=_hash(trial.prior.prior.musical_value(old['arms']['control']['selected_prediction'])):raise ValueError('control_prediction_changed')
        saved=trial.load(row['graph_artifact']);graph=trial.prior.prior.graph_from_packet(saved['problem'])
        if _hash(trial.prior.prior.graph_packet(graph))!=_hash(saved['problem']):raise ValueError('graph_codec_changed')
        edges+=len(graph.edges);pair=row['pair_id']
        if pair not in cache:
            src=saved['source'];ir=trial.load(src['canonical_ir_path'])
            if _hash(ir)!=src['original_ir_content_sha256'] or trial.expanded.digest(src['source_musicxml_path'])!=src['original_musicxml_sha256']:raise ValueError('source_changed')
            view,grace=trial.prior.prior.bounded.grace_projection(ir);cache[pair]=ir,view,grace,SourceClockGuard(ir)
        ir,view,grace,clock=cache[pair]
        if _hash(clock.scope(row['sample_span']))!=_hash(row['source_clock_gate']):raise ValueError('clock_changed')
        ev,args=trial.prior.evidence_args(ir,view,grace,row['sample_span'],clock)
        for arm,result in row['arms'].items():
            selected=result['selected_prediction']
            if selected is None:continue
            check_confirmation(selected);scorer=trial.scoring.Scorer(graph,ev,weights if arm=='train_calibrated' else None,**args)
            ids=trial.prior.prior.path_ids(selected);values,available=scorer.path_features(ids)
            if trial.scoring.q(scorer.score_path(ids))!=selected['score_cost']:raise ValueError('winner_cost_changed')
            if selected['support_balance']['values']!={k:trial.scoring.q(v) for k,v in values.items()} or selected['support_balance']['availability']!=available:raise ValueError('winner_features_changed')
            scores+=1
        clock.check_source()
    if prior or sealed:raise ValueError('scope_denominator_changed')
    for a,rs in tables.items():
        if summarize(rs)!=report['tables'][a]:raise ValueError('metric_table_changed')
    for saved in report['cases']:
        case=trial.load(saved['case_path']);row=case['record'];graph=trial.prior.prior.graph_from_packet(trial.load(row['graph_artifact'])['problem'])
        ir,view,grace,clock=cache[row['pair_id']];ev,args=trial.prior.evidence_args(ir,view,grace,row['sample_span'],clock)
        scorer=trial.scoring.Scorer(graph,ev,weights,**args)
        if case['human_validated'] or not case['reference_witness_never_used_for_inference']:raise ValueError('case_confirmation_changed')
        for receipt in case['scored_selected_paths'].values():
            if _hash(trial.path_receipt(scorer,receipt['existing_path_ids']))!=_hash(receipt):raise ValueError('case_receipt_changed')
        if 'reference_witness_scores' in case:
            witness=case['reference_witness_scores'];actual=trial.path_receipt(scorer,witness['existing_path_ids'])
            actual['source_labels_used_to_create_this_path']=True
            if _hash(actual)!=_hash(witness):raise ValueError('posthoc_reference_changed')
    check()
    result={'passed':True,'unique_hashes_checked':len(pins),'train_contrasts_recomputed':train_count,
        'model_fit_replayed':True,'scopes':len(report['records']),'graph_edges_roundtripped':edges,
        'independent_winner_costs_checked':scores,'full_source_packages':len(cache),'cases':len(report['cases']),
        'metrics_replayed':list(tables),'report_sha256':trial.expanded.digest(root/'report.json'),
        'audit_code_sha256':trial.expanded.digest(__file__),'new_inference_performed':False}
    trial.expanded.write(dest,result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);a=p.parse_args()
    print(json.dumps(run(a.root),ensure_ascii=False,indent=2),flush=True)
