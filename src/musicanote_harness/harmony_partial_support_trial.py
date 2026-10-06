"""Train-only partial evidence trial, zero-cost stop or all-scope fresh search.

Reuse the sealed 241 contrasts and all 118 source scopes; never expand the
infrastructure corpus or tune Dev. Seal model and all predictions before
reference evaluation. Do not call a zero-cost replay a new accuracy trial.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from time import perf_counter

from . import harmony_source_context_trial as parent
from . import harmony_partial_support_scoring as score
from . import harmony_partial_support_learning as learning

VERSION='harmony-partial-support-train-trial-0.1.0'
t,io,load,q,f=parent.t,parent.io,parent.load,parent.q,parent.f
ROOT=Path('K:/Music Analysis/output/harmony-source-context-train-2026-10-06-r1')
PINS={'report.json':'4892ecc786187905cc564cf3ff5656ecbf4b68dd5909cb8fb6666072845e1808',
      'post-seal-audit.json':'048ca0cb4e4abff289c7fbe27cedcf2886b37f78db1ec5dd599e1659b408facf',
      'training-vectors.json.gz':'b967358bcfc3937543c9c34950c036a59619735ae8dc63b22659fc22c30f339c',
      'model.json.gz':'da6501fb4a3b9012029c039b11b6ac95a13378b9f7f9b921a2d3a08ecbdbe89b'}
PRIOR_VALIDATION_SHA='4f572833539f03233a03338b525d0d5b34c5899f1b65a6a6b848829e9184b98c'
CODE_FILES=('src/musicanote_harness/harmony_partial_support.py',
    'src/musicanote_harness/harmony_partial_support_scoring.py',
    'src/musicanote_harness/harmony_partial_support_learning.py',__file__,
    'tests/test_harmony_partial_support.py','tests/test_harmony_partial_support_scoring.py',
    'tests/test_harmony_partial_support_learning.py','tests/test_harmony_partial_support_trial.py',
    'scripts/validate_harmony_partial_support.py')


def vector(item,negative,target):
    a,b=negative['partial_support'],target['partial_support']
    known={k:a['availability'][k] and b['availability'][k] for k in score.FEATURES}
    partial={k:q(f(a['scored_available_feature_sums'][k])-f(b['scored_available_feature_sums'][k])) for k in score.FEATURES}
    return {k:v for k,v in item.items() if k not in ('delta','available','scored_partial_delta','old_gap')}|dict(
        old_gap=q(f(negative['previous35_cost'])-f(target['previous35_cost'])),
        delta={k:partial[k] if known[k] else q(0) for k in score.FEATURES},
        scored_partial_delta=partial,available=known,source_labels_for_features=False,
        target_created_using_training_reference=True)


def independent_receipt(sc,ids,*,target=False):
    """Same old35, independent fresh Context for each completed union run."""
    replay=score.Scorer(sc.problem,sc.ev,sc.joint_weights,sc.extra_weights,**sc.partial_args)
    def direct(a,b,sig):
        return score.evidence.observe(sc.problem,sc.ev,a,b,sig,history_gate=sc.partial.history_gate)
    replay.observe=direct
    receipt=replay.path_receipt(tuple(ids),target=target)
    if not t.train.same_json(receipt,sc.path_receipt(tuple(ids),target=target)):
        raise ValueError('partial_support_uncached_receipt_mismatch')
    return receipt


def run(output,validation):
    output=Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick=perf_counter();inputs={};artifacts={}
    def read(path,expected=None,compressed=False,raw=False):
        path=Path(path);key=str(path.resolve());sha=inputs.get(key) or io.digest(path)
        if expected is not None and sha!=expected: raise ValueError('partial_support_input_changed:'+key)
        inputs[key]=sha;return None if raw else load(path)
    check=read(validation)
    if (check['passed'] is not True or check['previous_validation_sha256']!=PRIOR_VALIDATION_SHA
        or not {'test_harmony_partial_support','test_harmony_partial_support_scoring',
                'test_harmony_partial_support_learning','test_harmony_partial_support_trial'}<=set(check['test_modules'])):
        raise ValueError('partial_support_validation_not_passed')
    previous,audit,pool,model=[read(ROOT/n,sha) for n,sha in PINS.items()]
    if (previous['complete'] is not True or audit['passed'] is not True or audit['report_sha256']!=PINS['report.json']
        or any(f(v) for v in model['weights'].values())): raise ValueError('partial_support_parent_not_zero_sealed')
    for p,sha in (previous['input_hashes']|previous['artifact_hashes']|previous['code_hashes']).items(): read(p,sha,raw=True)
    ctx=t.context(read)
    if previous['cohort']!=[r['sample_id'] for r in ctx['rows']]: raise ValueError('partial_support_cohort_changed')
    code={str(Path(p).resolve()):io.digest(p) for p in CODE_FILES}
    output.mkdir(parents=True)
    for name in ('vectors','predictions','cases'): (output/name).mkdir()
    def save(name,value,compressed=False):
        path=output/name;(io.write_packet if compressed else io.write)(path,value)
        key=str(path.resolve());artifacts[key]=io.digest(path);return key,artifacts[key]
    contract=dict(version=VERSION,configuration=learning.configuration(),cohort=previous['cohort'],
        parent_report_sha256=PINS['report.json'],old35_model_sha256=parent.MODEL_SHA,
        all_old35_coefficients_unchanged=True,prior3_frozen_zero=True,
        same_original_candidates_and_raw_cap=True,wall_seconds=20,transition_budget=2_000_000,
        source_labels_used_for_prediction=False,fit_uses_train_only=True,current_dev_read=False,
        work_specific_rules=False,parallel_heavy_work_during_selection=False,production_modified=False,
        independent_accuracy_claimed=False,purpose='local_noncommercial_research',code_pins=code)
    save(Path('run-contract.json'),contract)
    old_rows={r['sample_id']:r for r in previous['records']};grouped=defaultdict(list)
    for r in pool['rows']: grouped[r['sample_id']].append(r)
    vectors=[];feature_counts=Counter();sources=set();edges=0
    for i,row in enumerate(ctx['rows'],1):
        sample=row['sample_id'];prior=old_rows[sample];archived=read(prior['artifact'],prior['sha256'])
        saved,entry,graph,ev,clock,args=t.prepare(ctx,row,read);t.assert_source(saved,archived)
        sc=score.Scorer(graph,ev,ctx['beat_weights'],score.ZERO,**args);receipts={};rows=[]
        def receipt(ids):
            ids=tuple(ids)
            if ids not in receipts:
                new=sc.path_receipt(ids);old=t.cache.Scorer(graph,ev,ctx['beat_weights'],**args).path_receipt(ids)
                if not t.train.same_json(new['previous35_cost'],old['cost']): raise ValueError('partial_support_old35_changed')
                receipts[ids]=new
            return receipts[ids]
        for item in grouped[sample]:
            if item['split']!='train' or item['source_ir_content_sha256']!=saved['source_ir_content_sha256']:
                raise ValueError('partial_support_wrong_train_source')
            new=vector(item,receipt(item['negative_ids']),receipt(item['target_ids']))
            if new['old_gap']!=item['old_gap']: raise ValueError('partial_support_sealed_gap_changed')
            rows.append(new)
            for k in score.FEATURES:
                feature_counts[k+(':unknown' if not new['available'][k] else ':nonzero' if f(new['delta'][k]) else ':zero')]+=1
        save(Path('vectors')/(sample+'.json.gz'),dict(sample_id=sample,rows=rows,
            source_packet_fields={k:saved[k] for k in t.train.refresh.SOURCE_FIELDS},
            path_receipts=list(receipts.values())),True)
        vectors.extend(rows);sources.add(saved['source_ir_content_sha256']);edges+=len(graph.edges)
        t.train.refresh.clear(ev,clock)
        if i%20==0 or i==len(ctx['rows']): print(f'[partial support Train vectors {i}/{len(ctx["rows"])}]',flush=True)
    if len(vectors)!=len(pool['rows']): raise ValueError('partial_support_contrasts_lost')
    vector_ref,vector_sha=save(Path('training-vectors.json.gz'),dict(rows=vectors,feature_counts=dict(feature_counts)),True)
    fitted=learning.fit(vectors);fitted.update(old35_model_sha256=parent.MODEL_SHA,train_vector_sha256=vector_sha,
        model_id='partial_support_'+t.train.learning.use.content_hash([fitted['weights'],vector_sha])[:24],
        old35_weights={k:q(v) for k,v in ctx['beat_weights'].items()})
    model_ref,model_sha=save(Path('model.json.gz'),fitted,True)
    extra=score.coefficients({k:f(v) for k,v in fitted['weights'].items()});fresh=any(extra.values())
    freeze_ref,freeze_sha=save(Path('model-freeze.json'),dict(model_ref=model_ref,model_sha256=model_sha,
        old35_model_sha256=parent.MODEL_SHA,train_vector_sha256=vector_sha,reference_evaluation_started=False,
        dev_used=False,old35_and_new4_frozen=True,prior3_frozen_zero=True,code_pins=code))
    print('[partial support frozen] '+json.dumps({k:fitted[k] for k in ('rows','usable_rows','weights','objective_before','objective_after')},ensure_ascii=False),flush=True)
    predictions=[]
    if fresh:
        for i,row in enumerate(ctx['rows'],1):
            saved,entry,graph,ev,clock,args=t.prepare(ctx,row,read)
            sc=score.Scorer(graph,ev,ctx['beat_weights'],extra,**args)
            result=t.train.refresh.parent.select(sc,fitted['model_id'])
            result['frozen_model_ref']=dict(model_id=fitted['model_id'],model_sha256=model_sha,
                model_was_fitted_on_train=True,fit_performed_this_run=False,old35_and_new4_frozen=True,
                reference_labels_used_for_selection=False,operational_promotion=False)
            packet={k:saved[k] for k in t.train.refresh.SOURCE_FIELDS}|dict(result=result,
                model_sha256=model_sha,model_freeze_ref=freeze_ref,model_freeze_sha256=freeze_sha,
                previous_case_ref=old_rows[row['sample_id']]['artifact'],
                previous_case_sha256=old_rows[row['sample_id']]['sha256'],
                source_labels_used_for_prediction=False,reference_evaluation_performed=False)
            p,h=save(Path('predictions')/(row['sample_id']+'.json.gz'),packet,True)
            predictions.append(dict(sample_id=row['sample_id'],artifact=p,sha256=h))
            t.train.refresh.clear(ev,clock)
            io.write(output/'progress.json',dict(complete=False,phase='fresh_ordinary_selection',finished=i,
                total=len(ctx['rows']),elapsed_seconds=perf_counter()-tick,last_status=result['status']))
            print(f'[partial support Train {i}/{len(ctx["rows"])}] {row["sample_id"]}: {result["status"]}',flush=True)
    prediction_ref,prediction_sha=save(Path('prediction-freeze.json'),dict(complete=True,predictions=predictions,
        fresh_selection_performed=fresh,model_sha256=model_sha,reference_evaluation_started=False,code_pins=code))
    records=[];witnesses=0
    for i,row in enumerate(ctx['rows'],1):
        prior=old_rows[row['sample_id']];archived=read(prior['artifact'],prior['sha256'])
        saved,entry,graph,ev,clock,args=t.prepare(ctx,row,read);t.assert_source(saved,archived)
        sc=score.Scorer(graph,ev,ctx['beat_weights'],extra,**args)
        target_ids=archived['post_search_cost_receipts']['target']['existing_path_ids']
        chains=dict(target=target_ids,previous=prior['selected_ids']);selected=None;pred=None
        if fresh:
            pred=predictions[i-1];packet=read(pred['artifact'],pred['sha256']);t.assert_source(saved,packet)
            selected=packet['result']['selected']
            if selected: chains['fresh']=t.train.s.fresh.path_ids(selected)
        else:
            packet={k:saved[k] for k in t.train.refresh.SOURCE_FIELDS}|dict(
                previous_case_ref=prior['artifact'],previous_case_sha256=prior['sha256'],
                prior_evaluation=prior['evaluation'],fresh_selection_performed=False,
                prior_selected_ids=prior['selected_ids'],no_new_accuracy_measurement=True)
        receipts={}
        for name,ids in chains.items():
            if ids is None: continue
            r=independent_receipt(sc,ids,target=name=='target');receipts[name]=r;witnesses+=1
            old=t.cache.Scorer(graph,ev,ctx['beat_weights'],**args).path_receipt(tuple(ids))
            if not t.train.same_json(old['cost'],r['previous35_cost']): raise ValueError('partial_support_post_old35_changed')
            if name=='fresh' and not t.train.same_json(r,selected['context_score']): raise ValueError('partial_support_winner_cost_changed')
        if fresh:
            evaluation=t.train.evaluate(selected,ctx['refs'][row['sample_id']])
            packet.update(evaluation=evaluation,prediction_ref=pred['artifact'],prediction_sha256=pred['sha256'])
        packet.update(post_search_cost_receipts=receipts,reference_evaluation_performed=fresh,
            prediction_freeze_ref=prediction_ref,prediction_freeze_sha256=prediction_sha,
            source_window=parent.triage.source_window(ev,row['sample_span']),
            new_features_human_validated=False,production_modified=False)
        p,h=save(Path('cases')/(row['sample_id']+'.json.gz'),packet,True)
        record={k:row[k] for k in t.train.refresh.FIELDS}|dict(artifact=p,sha256=h,
            fresh_selection_performed=fresh,prior_selected_ids=prior['selected_ids'],prior_evaluation=prior['evaluation'])
        if fresh:
            ids=t.train.s.fresh.path_ids(selected) if selected else None
            record.update(selected_ids=ids,evaluation=evaluation,status=packet['result']['status'],
                prior_status=prior['status'],same_completed_winner=t.train.same_json(ids,prior['selected_ids']),
                elapsed_seconds=packet['result']['resource_guard']['elapsed_seconds'])
        records.append(record);t.train.refresh.clear(ev,clock)
        if i%20==0 or i==len(ctx['rows']): print(f'[partial support independent receipts {i}/{len(ctx["rows"])}]',flush=True)
    for p,sha in (inputs|artifacts|code).items():
        if io.digest(p)!=sha: raise ValueError('partial_support_final_pin_changed:'+p)
    report=contract|dict(complete=True,records=records,summary=t.summaries(records) if fresh else None,
        baseline_sealed_summary=previous['summary'],model_sha256=model_sha,training_contrasts=len(vectors),
        feature_counts=dict(feature_counts),full_source_packages=len(sources),original_edges=edges,
        cost_witnesses_replayed=witnesses,fit_performed=True,fresh_ordinary_attempts=len(predictions),
        fresh_selection_performed=fresh,new_accuracy_measured=fresh,
        zero_new_weights_all_path_costs_equal_old35=not fresh,operational_promotion=False,
        input_hashes=inputs,artifact_hashes=artifacts,code_hashes=code,elapsed_seconds=perf_counter()-tick)
    io.write(output/'report.json',report)
    reloaded=load(output/'report.json')
    if fresh and not t.train.same_json(t.summaries(reloaded['records']),report['summary']):
        raise ValueError('partial_support_serialized_summary_changed')
    io.write(output/'post-seal-audit.json',dict(passed=True,report_sha256=io.digest(output/'report.json'),
        input_pins=len(inputs),artifact_pins=len(artifacts),code_pins=len(code),full_source_packages=len(sources),
        cost_witnesses_replayed=witnesses,fresh_selection_performed=fresh,
        predictions_sealed_before_evaluation=True if fresh else None,
        all118_original_scopes_preserved=True,source_feature_accuracy_human_validated=False,production_modified=False))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--validation',required=True)
    a=p.parse_args();r=run(a.output,a.validation)
    print(json.dumps({k:r[k] for k in ('complete','fresh_ordinary_attempts','summary','feature_counts','elapsed_seconds')},indent=2),flush=True)
