"""Calibrate new source context on Train, freeze, then fresh-decode all 118.

No Dev reading or tuning, candidate changes, production writes, or omitted
resource failures. Keep all predictions sealed before reference evaluation.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from time import perf_counter

from . import harmony_large_error_triage as triage
from . import harmony_source_context_scoring as score
from . import harmony_source_context_learning as learning

VERSION='harmony-source-context-all-train-trial-0.1.0'
t, io, load, q, f = triage.parent, triage.io, triage.load, triage.q, triage.f
VALIDATION_PARENT_SHA='9ad1ffc432ac09036a3a22abf2f72af39ae70e921c59df60261516255b5472d3'
MODEL_ROOT=Path('K:/Music Analysis/output/harmony-ordinal-protection-2026-10-06-r1')
MODEL_SHA='b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38'
CODE_FILES=('src/musicanote_harness/harmony_terminal_context.py',
    'src/musicanote_harness/harmony_source_context_scoring.py',
    'src/musicanote_harness/harmony_source_context_learning.py', __file__,
    'tests/test_harmony_terminal_context.py','tests/test_harmony_source_context_scoring.py',
    'tests/test_harmony_source_context_learning.py','tests/test_harmony_source_context_trial.py',
    'scripts/validate_harmony_source_context.py')


def vector(item, negative, target):
    a,b=negative['source_context'],target['source_context']
    known={k:a['availability'][k] and b['availability'][k] for k in score.FEATURES}
    partial={k:q(f(a['scored_available_feature_sums'][k])-f(b['scored_available_feature_sums'][k])) for k in score.FEATURES}
    return item | dict(old_gap=q(f(negative['previous35_cost'])-f(target['previous35_cost'])),
        delta={k:partial[k] if known[k] else q(0) for k in score.FEATURES},
        scored_partial_delta=partial, available=known, source_labels_for_features=False,
        target_created_using_training_reference=True)


def run(output, validation):
    output=Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick=perf_counter(); inputs={}; artifacts={}
    def read(path, expected=None, compressed=False, raw=False):
        path=Path(path); key=str(path.resolve()); sha=inputs.get(key) or io.digest(path)
        if expected is not None and sha!=expected: raise ValueError('source_context_input_changed:'+key)
        inputs[key]=sha; return None if raw else load(path)
    check=read(validation)
    if (check['passed'] is not True or check['previous_validation_sha256']!=VALIDATION_PARENT_SHA
            or not {'test_harmony_terminal_context','test_harmony_source_context_scoring','test_harmony_source_context_learning'}<=set(check['test_modules'])):
        raise ValueError('source_context_validation_not_passed')
    previous=read(triage.ROOT/'report.json',triage.PINS['report.json'])
    for p,sha in (previous['input_hashes']|previous['artifact_hashes']|previous['code_hashes']).items(): read(p,sha,raw=True)
    ctx=t.context(read); old_model=read(MODEL_ROOT/'model.json.gz',MODEL_SHA)
    if previous['cohort']!=[r['sample_id'] for r in ctx['rows']]: raise ValueError('source_context_cohort_changed')
    code={str(Path(p).resolve()):io.digest(p) for p in CODE_FILES}
    output.mkdir(parents=True)
    for name in ('vectors','predictions','cases'): (output/name).mkdir()
    def save(name,value,compressed=False):
        path=output/name; (io.write_packet if compressed else io.write)(path,value)
        key=str(path.resolve()); artifacts[key]=io.digest(path);return key,artifacts[key]
    contract=dict(version=VERSION,configuration=learning.configuration(),cohort=previous['cohort'],
        old_model_sha256=MODEL_SHA,old_report_sha256=triage.PINS['report.json'],
        all_old35_coefficients_unchanged=True,new_run_cost_dimensions=score.FEATURES,
        same_original_candidates_and_raw_cap=True,wall_seconds=20,transition_budget=2_000_000,
        old_abstentions_not_replaced_by_fallback=True,parallel_heavy_work_during_selection=False,
        predictions_sealed_before_reference_evaluation=True,current_dev_read=False,
        fit_uses_train_only=True,source_labels_used_for_prediction=False,work_specific_rules=False,
        production_modified=False,independent_accuracy_claimed=False,purpose='local_noncommercial_research',code_pins=code)
    save(Path('run-contract.json'),contract)
    old_rows={r['sample_id']:r for r in previous['records']}; pool=defaultdict(list)
    for r in ctx['active_pool']: pool[r['sample_id']].append(r)
    vectors=[]; feature_counts=Counter(); sources=set(); edges=0
    for i,row in enumerate(ctx['rows'],1):
        sample=row['sample_id']; prior=old_rows[sample]; archived=read(prior['artifact'],prior['sha256'])
        saved,entry,graph,ev,clock,args=t.prepare(ctx,row,read); t.assert_source(saved,archived)
        sc=score.Scorer(graph,ev,ctx['beat_weights'],score.ZERO,**args); rows=[]; receipts={}
        def receipt(ids):
            ids=tuple(ids)
            if ids not in receipts:
                r=sc.path_receipt(ids)
                # Independently replay the old35 path; added zero dimensions
                # cannot quietly modify the frozen score or its null policy.
                old=t.cache.Scorer(graph,ev,ctx['beat_weights'],**args).path_receipt(ids)
                if not t.train.same_json(old['cost'],r['previous35_cost']): raise ValueError('source_context_old_cost_changed')
                receipts[ids]=r
            return receipts[ids]
        seen=set()
        for r in pool[sample]:
            if r['entry']['split']!='train' or r['source_ir_content_sha256']!=saved['source_ir_content_sha256']:
                raise ValueError('source_context_wrong_train_source')
            key=tuple(r['negative_ids']),tuple(r['target_ids']);seen.add(key)
            item={k:r[k] for k in ('sample_id','contrast_id','negative_ids','target_ids','loss','source_ir_content_sha256')}
            item.update(split='train',work_family_id=row['work_family_id'],origin='sealed_active_train_pool')
            rows.append(vector(item,receipt(key[0]),receipt(key[1])))
        if prior['selected_ids'] is not None and prior['evaluation']['selected_hit'] is False:
            target=tuple(archived['post_search_cost_receipts']['historical_stored_target']['existing_path_ids'])
            key=tuple(prior['selected_ids']),target
            if key not in seen:
                # Post-selection TRAIN witness only. No labels enter the
                # extractor or subsequent prediction's candidate graph.
                anatomy=triage.compare_runs(triage.completed_runs(graph,key[0]),triage.completed_runs(graph,key[1]))
                loss=sum((f(v) for k,v in anatomy['quarter_totals'].items() if k!='same_signature'), f(q(0)))
                item=dict(sample_id=sample,contrast_id='fresh93_'+sample,negative_ids=key[0],target_ids=key[1],
                    loss=q(loss/(graph.points[-1]-graph.points[0])),source_ir_content_sha256=saved['source_ir_content_sha256'],
                    split='train',work_family_id=row['work_family_id'],origin='sealed_all_train_wrong_winner')
                rows.append(vector(item,receipt(key[0]),receipt(key[1])))
        for r in rows:
            for k in score.FEATURES:
                feature_counts[k+(':unknown' if not r['available'][k] else ':nonzero' if f(r['delta'][k]) else ':zero')]+=1
        save(Path('vectors')/(sample+'.json.gz'),dict(sample_id=sample,rows=rows,
            source_packet_fields={k:saved[k] for k in t.train.refresh.SOURCE_FIELDS},
            path_receipts=[v for v in receipts.values()]),True)
        vectors.extend(rows);sources.add(saved['source_ir_content_sha256']);edges+=len(graph.edges)
        t.train.refresh.clear(ev,clock)
        if i%20==0 or i==len(ctx['rows']):print(f'[source context Train vectors {i}/{len(ctx["rows"])}]',flush=True)
    vector_ref,vector_sha=save(Path('training-vectors.json.gz'),dict(rows=vectors,feature_counts=dict(feature_counts)),True)
    fitted=learning.fit(vectors); fitted.update(old35_model_sha256=MODEL_SHA,train_vector_sha256=vector_sha,
        model_id='source_context_'+t.train.learning.use.content_hash([fitted['weights'],vector_sha])[:24],
        old35_weights={k:q(v) for k,v in ctx['beat_weights'].items()})
    model_ref,model_sha=save(Path('model.json.gz'),fitted,True)
    extra=score.coefficients({k:f(v) for k,v in fitted['weights'].items()})
    freeze_ref,freeze_sha=save(Path('model-freeze.json'),dict(model_ref=model_ref,model_sha256=model_sha,
        old35_model_sha256=MODEL_SHA,train_vector_sha256=vector_sha,reference_evaluation_started=False,
        dev_used=False,all38_weights_frozen=True,code_pins=code))
    print('[source context frozen] '+json.dumps({k:fitted[k] for k in ('rows','usable_rows','unknown_dimensions_excluded','weights','objective_before','objective_after')},ensure_ascii=False),flush=True)
    predictions=[]
    for i,row in enumerate(ctx['rows'],1):
        saved,entry,graph,ev,clock,args=t.prepare(ctx,row,read)
        sc=score.Scorer(graph,ev,ctx['beat_weights'],extra,**args)
        result=t.train.refresh.parent.select(sc,fitted['model_id'])
        result['frozen_model_ref']=dict(model_id=fitted['model_id'],model_sha256=model_sha,
            fit_performed_this_run=False,model_was_fitted_on_train=True,all38_weights_frozen=True,
            reference_labels_used_for_selection=False,operational_promotion=False)
        result['source_context_frozen_model']=dict(model_ref=model_ref,model_sha256=model_sha,
            model_freeze_sha256=freeze_sha,all38_weights_frozen=True,source_labels_used_for_selection=False)
        result['source_context_contract']=dict(version=score.VERSION,same_sealed_dp_bytecode=True,
            private_run_cost_dependency_added=True,old35_weights_unchanged=True,
            new_weights={k:q(v) for k,v in extra.items()},same_candidates_and_raw_cap=True,
            source_labels_used=False,production_modified=False)
        packet={k:saved[k] for k in t.train.refresh.SOURCE_FIELDS}|dict(result=result,
            model_sha256=model_sha,model_freeze_ref=freeze_ref,model_freeze_sha256=freeze_sha,
            previous_case_ref=old_rows[row['sample_id']]['artifact'],previous_case_sha256=old_rows[row['sample_id']]['sha256'],
            source_labels_used_for_prediction=False,reference_evaluation_performed=False)
        p,h=save(Path('predictions')/(row['sample_id']+'.json.gz'),packet,True)
        predictions.append(dict(sample_id=row['sample_id'],artifact=p,sha256=h))
        t.train.refresh.clear(ev,clock)
        io.write(output/'progress.json',dict(complete=False,phase='fresh_ordinary_selection',finished=i,total=len(ctx['rows']),
            last_status=result['status'],elapsed_seconds=perf_counter()-tick))
        print(f'[source context Train {i}/{len(ctx["rows"])}] {row["sample_id"]}: {result["status"]}',flush=True)
    prediction_ref,prediction_sha=save(Path('prediction-freeze.json'),dict(complete=True,predictions=predictions,
        model_sha256=model_sha,reference_evaluation_started=False,code_pins=code))
    records=[]; witness_count=0
    for i,(row,pred) in enumerate(zip(ctx['rows'],predictions),1):
        packet=read(pred['artifact'],pred['sha256']);saved,entry,graph,ev,clock,args=t.prepare(ctx,row,read)
        t.assert_source(saved,packet);prior=old_rows[row['sample_id']]
        archived=read(prior['artifact'],prior['sha256']);t.assert_source(saved,archived)
        sc=score.Scorer(graph,ev,ctx['beat_weights'],extra,**args);selected=packet['result']['selected']
        chains=dict(previous=prior['selected_ids'],target=archived['post_search_cost_receipts']['historical_stored_target']['existing_path_ids'])
        if selected is not None:chains['fresh']=t.train.s.fresh.path_ids(selected)
        receipts={}
        for name,ids in chains.items():
            if ids is None:continue
            r=sc.path_receipt(tuple(ids),target=name=='target');receipts[name]=r;witness_count+=1
            base=t.cache.Scorer(graph,ev,ctx['beat_weights'],**args).path_receipt(tuple(ids))
            if not t.train.same_json(base['cost'],r['previous35_cost']):raise ValueError('source_context_post_seal_old_cost_changed')
            if name=='fresh' and not t.train.same_json(r,selected['context_score']):raise ValueError('source_context_post_seal_winner_cost_changed')
        evaluation=t.train.evaluate(selected,ctx['refs'][row['sample_id']])
        packet=packet|dict(evaluation=evaluation,post_search_cost_receipts=receipts,reference_evaluation_performed=True,
            prediction_ref=pred['artifact'],prediction_sha256=pred['sha256'],prediction_freeze_ref=prediction_ref,
            prediction_freeze_sha256=prediction_sha)
        p,h=save(Path('cases')/(row['sample_id']+'.json.gz'),packet,True)
        ids=t.train.s.fresh.path_ids(selected) if selected is not None else None
        records.append({k:row[k] for k in t.train.refresh.FIELDS}|dict(artifact=p,sha256=h,status=packet['result']['status'],
            selected_ids=ids,evaluation=evaluation,prior_selected_ids=prior['selected_ids'],prior_evaluation=prior['evaluation'],
            prior_status=prior['status'],same_completed_winner=t.train.same_json(ids,prior['selected_ids']),
            elapsed_seconds=packet['result']['resource_guard']['elapsed_seconds']))
        t.train.refresh.clear(ev,clock)
        if i%20==0 or i==len(ctx['rows']):print(f'[source context sealed evaluation {i}/{len(ctx["rows"])}]',flush=True)
    for p,sha in (inputs|artifacts|code).items():
        if io.digest(p)!=sha:raise ValueError('source_context_final_pin_changed:'+p)
    report=contract|dict(complete=True,records=records,summary=t.summaries(records),model_sha256=model_sha,
        training_contrasts=len(vectors),feature_counts=dict(feature_counts),full_source_packages=len(sources),
        original_edges=edges,cost_witnesses_replayed=witness_count,fit_performed=True,fresh_ordinary_attempts=len(predictions),
        operational_promotion=False,input_hashes=inputs,artifact_hashes=artifacts,code_hashes=code,
        elapsed_seconds=perf_counter()-tick)
    io.write(output/'report.json',report)
    reloaded=load(output/'report.json')
    if not t.train.same_json(t.summaries(reloaded['records']),report['summary']):raise ValueError('source_context_serialized_summary_changed')
    io.write(output/'post-seal-audit.json',dict(passed=True,report_sha256=io.digest(output/'report.json'),
        input_pins=len(inputs),artifact_pins=len(artifacts),code_pins=len(code),full_source_packages=len(sources),
        cost_witnesses_replayed=witness_count,predictions_sealed_before_evaluation=True,
        all118_original_scopes_preserved=True,source_feature_accuracy_human_validated=False,production_modified=False))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--validation',required=True)
    a=p.parse_args();r=run(a.output,a.validation)
    print(json.dumps({k:r[k] for k in ('complete','summary','feature_counts','elapsed_seconds')},indent=2),flush=True)
