"""Recompute Train-only features on historical, SHA-bound path contrasts.

Historical negative pool is incomplete and selection-biased. No fresh adversary
search and no Dev labels. Candidate generation only reconstructs old Train DAGs.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
from pathlib import Path
from . import harmony_functional_learning_trial as old
from . import harmony_support_balance as scoring
from . import harmony_support_balance_learning as learning
from .harmony_margin_learning import training_loss,path_loss
from .harmony_structured_learning import compatible_problem,validate_use_contract,content_hash
from .harmony_root_context_trial import barrier_times
from .harmony_source_clock import SourceClockGuard

PINS={
 'output/harmony-functional-scoring-2026-10-04-r1/report.json':'e3983219bc2b53fd102302514cecc74e9e98b54290cc3d295e3023c6e912f661',
 'output/harmony-candidate-recall-2026-10-04-r1/report.json':'f12397eb53544dfa153974a9f0006f7cb06467d09c10ce1ecaf8da2e2d21f0eb',
 'output/harmony-context-integration-trial-2026-09-30-r1/report.json':'22ff64ceb522cfde5039d07dc28935179e8c12add14ed52aaa0295f90e1bcebe',
 'docs/harmony/experiments/2026-10-04-local-research-training-use.json':'46bbd4871cc38e27d14fd19d317956f989a1ead6fa265ecb74d722272db4ee48',
 'output/harmony-functional-learning-2026-10-04-r2/model.json':'062e46ecd529f6c19f2e3cd1e9f967831140561291161cfa2e63cb937dff158c',
 'output/harmony-functional-learning-2026-10-04-r2/report.json':'77350ac9eb04f11e663a6adb6d1d7fd2ff5b98d99b8495c42b8413308fc52594'}
PARENT_SHA=PINS['output/harmony-candidate-recall-2026-10-04-r1/report.json']


def contrasts(model):
    groups=defaultdict(dict);counts=Counter()
    for kind,rows,target_key in (('update',model['updates'],'training_target_group_refs'),
                                 ('collision',model['feature_collisions'],'target_group_refs')):
        for row in rows:
            sample=row['sample_id'];negative=tuple(row['adversary_group_refs']);target=tuple(row[target_key])
            key=content_hash([sample,negative,target]);counts['historical_'+kind+'_records']+=1
            if key in groups[sample]:
                if groups[sample][key]['loss_details']!=row['loss']:raise ValueError('historical_loss_changed')
            else:groups[sample][key]={'contrast_id':key,'negative_ids':negative,'target_ids':target,
                                     'loss_details':row['loss'],'historical_kind':kind}
    return groups,dict(counts)


def prepare_context(previous,ref,manifest,integration,read):
    identity=('pair_id','plan_index','sample_id','split','work_family_id')
    if (tuple(previous[k] for k in identity)!=tuple(ref[k] for k in identity)
            or previous['reference_cells']!=ref['reference_cells'] or previous['sample_span']!=ref['sample_span']):
        raise ValueError('train_parent_reference_changed')
    packet=read(previous['search_artifact'],previous['search_artifact_sha256'],True)
    context=read(previous['source_context_artifact'],previous['source_context_sha256'],True)
    entry=packet['provenance']['manifest_entry'];bundle=context['bundle'];search=packet['search']
    if (entry not in manifest or entry['split']!='train' or ref['split']!='train'
            or entry['work_family_id']!=ref['work_family_id']
            or context['provenance']!=packet['provenance']
            or context['pair_id']!=ref['pair_id'] or packet['pair_id']!=ref['pair_id']
            or context['plan_index']!=ref['plan_index'] or packet['plan_index']!=ref['plan_index']
            or packet['sample']['sample_id']!=ref['sample_id'] or packet['sample']['span']!=ref['sample_span']
            or old._hash(bundle)!=packet['input_bundle_content_sha256']
            or search['input_bundle_content_sha256']!=packet['input_bundle_content_sha256']):
        raise ValueError('train_source_binding_mismatch')
    ir=old.load_ir(dict(entry,pair_id=ref['pair_id']),context['provenance'],bundle,integration,read)
    problem,source=old.prepare_with_evidence(ir,bundle,search)
    ev=old.prepare_functional_evidence(ir,source);graph,receipts=old.supply(problem,ev)
    if (graph.edges[:len(problem.edges)]!=problem.edges or graph.points!=problem.points
            or graph.max_segments!=problem.max_segments or len(problem.edges)!=previous['old_edge_count']
            or len(graph.edges)!=previous['expanded_edge_count']
            or content_hash(receipts)!=content_hash(previous['functional_candidate_receipts'])
            or source.source_ir_content_sha256!=ref['full_ir_content_sha256']
            or content_hash([[e.group_id,e.start_index,e.end_index,e.signature,e.blockers] for e in graph.edges])!=ref['candidate_inventory_content_sha256']):
        raise ValueError('historical_train_inventory_changed')
    clock=SourceClockGuard(ir);cache={}
    def gate(a,b):
        if (a,b) not in cache:cache[a,b]=clock.scope({'start':scoring.q(a),'end':scoring.q(b)})['accepted']
        return cache[a,b]
    args={'grace_notes':tuple(n for n in ir['note_events'] if (n.get('grace') or {}).get('is_grace') is True),
          'context_barriers':barrier_times(ir),'history_gate':gate}
    return entry,graph,ev,clock,args


def contrast_row(item,entry,graph,ev,args,scorer=None,cells=None):
    scorer=scorer or scoring.Scorer(graph,ev,build_index=False,**args)
    allowed,reason=compatible_problem(graph,cells)
    if reason or not set(item['target_ids'])<={e.group_id for e in allowed.edges}:
        raise ValueError('historical_target_not_gold_compatible')
    loss=training_loss(graph,cells,F(1,4))
    def loss_of(ids):return path_loss(graph,{'selected':{'segments':[{'semantic_group_ref':i} for i in ids]}},loss)
    if loss_of(item['negative_ids'])!=item['loss_details'] or scoring.f(loss_of(item['target_ids'])['total'])!=0:
        raise ValueError('historical_path_loss_changed')
    negative,na=scorer.path_features(item['negative_ids']);target,ta=scorer.path_features(item['target_ids'])
    if scorer.index is not None and ((negative,na)!=scorer.path_features(item['negative_ids'],indexed=True) or (target,ta)!=scorer.path_features(item['target_ids'],indexed=True)):
        raise ValueError('train_index_direct_feature_mismatch')
    availability={k:na[k] and ta[k] for k in scoring.FEATURES}
    return item|{'entry':entry,'feature_delta':{k:scoring.q(negative[k]-target[k]) for k in scoring.FEATURES},
        'feature_available':availability,'loss':item['loss_details']['total'],
        'train_feature_backend':'direct_original_events_no_graph_point_insertion',
        'negative_features':{k:scoring.q(v) for k,v in negative.items()},
        'target_features':{k:scoring.q(v) for k,v in target.items()},
        'base_cost_gap':scoring.q(scorer.base_cost(item['negative_ids'])-scorer.base_cost(item['target_ids']))}


def prepare(read,save,output):
    parents={p:read(p,h) for p,h in PINS.items()}
    previous,recall,integration,contract,model,learned=parents.values()
    if content_hash(model)!=learned['model_content_sha256']:raise ValueError('historical_model_binding_changed')
    manifest=recall['package_manifest'];approvals=validate_use_contract(contract,manifest,PARENT_SHA)
    for a in approvals.values():
        lic=a['source_license']
        for name in ('local_license','readme'):read(lic[name+'_path'],lic[name+'_sha256'],raw=True)
    groups,counts=contrasts(model);refs={r['sample_id']:r for r in learned['records']};prev={r['sample_id']:r for r in previous['records']}
    if len(refs)!=len(learned['records']) or len(prev)!=len(previous['records']):raise ValueError('duplicate_training_scope')
    rows=[];eligibility=[];sources=set()
    for sample,items in sorted(groups.items()):
        ref=refs[sample];entry,graph,ev,clock,args=prepare_context(prev[sample],ref,manifest,integration,read)
        if entry['manifest_entry_id'] not in approvals:raise ValueError('unapproved_historical_train_context')
        gate=clock.scope(ref['sample_span']);source_id=ev.source.source_ir_content_sha256;sources.add(source_id)
        receipt={'sample_id':sample,'pair_id':ref['pair_id'],'work_family_id':entry['work_family_id'],
                 'sample_span':ref['sample_span'],'contrasts':len(items),'source_clock_gate':gate,
                 'candidate_inventory_content_sha256':ref['candidate_inventory_content_sha256'],
                 'source_ir_content_sha256':source_id,'eligible_contrasts':0}
        if gate['accepted']:
            scorer=scoring.Scorer(graph,ev,build_index=False,**args);cells=tuple(old.cells_from_record(ref))
            for item in items.values():
                value=contrast_row(item,entry,graph,ev,args,scorer,cells)|{'sample_id':sample}
                if all(value['feature_available'].values()):rows.append(value);receipt['eligible_contrasts']+=1
                else:receipt.setdefault('unavailable_contrasts',[]).append(value['contrast_id'])
        clock.check_source();eligibility.append(receipt)
        print(f"[Train contrasts {len(eligibility)}/{len(groups)}] {sample}: {receipt['eligible_contrasts']}/{len(items)}",flush=True)
    counts.update(unique_historical_contrasts=sum(map(len,groups.values())),historical_samples=len(groups),
                  eligible_contrasts=len(rows),eligible_samples=len({r['sample_id'] for r in rows}),full_source_packages=len(sources))
    dataset={'rows':rows,'eligibility':eligibility,'counts':counts,'historical_negative_pool_complete':False,
             'fresh_adversary_search':False,'dev_labels_used':False,'candidate_policy_changed':False}
    save(output/'training-contrasts.json.gz',dataset,True)
    fitted=learning.fit(rows,contract,manifest,PARENT_SHA)
    fitted['training_dataset_content_sha256']=content_hash(dataset)
    fitted['negative_pool']='deduplicated_sealed_J2f_updates_and_collisions'
    save(output/'model.json',fitted)
    return fitted,contract,manifest,dataset
