"""Train-only, source-conditioned Unit20 windows; no role accuracy claims."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .dominant_area_evidence import _exact
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .predominant_sonata_audit import span_observation
from .six_three_context import observe_surface
from .six_four_context import VERSION, source_triad, propose, assess_direct
from .tonal_foundations import spelled_triad_shapes


def windows(annotations, verified_ids=None):
    for i in range(len(annotations)-2):
        group=annotations[i:i+3]
        if verified_ids is not None and any(a['annotation_id'] not in verified_ids for a in group): continue
        items=[source_triad(a) for a in group]
        if not all(items) or not any(x[1]==2 for x in items): continue
        keys=[source_key(a) for a in group]
        if any(k!=keys[0] for k in keys): continue
        spans=[a['target']['span'] for a in group]
        if any(_exact(s['start'])<0 or _exact(s['end'])<=_exact(s['start']) for s in spans): continue
        if any(_exact(a['end'])!=_exact(b['start']) for a,b in zip(spans,spans[1:])): continue
        yield i,[x[0] for x in items],[x[1] for x in items],keys[0]


def build(manifest_path, output):
    out=Path(output)
    if out.exists(): raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes()
    entries=json.loads(raw)['entries']; validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected): raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected): raise ValueError('research_not_permitted')
    out.mkdir(parents=True)
    names=['six_four_context.py','six_four_audit.py','six_three_context.py','root_position_context.py',
           'diatonic_sequence.py','dominant_area_evidence.py','formal_ir.py','cadential_six_four_audit.py',
           'harmony_case_retrieval.py','harmony_review_cohort.py','harmony_review_supplement.py',
           'predominant_sonata_audit.py','foundation_sonata_audit.py','tonal_foundations.py','harmony_curriculum.py']
    contract={'version':VERSION,'entries':selected,'manifest_sha256':hashlib.sha256(raw).hexdigest(),
              'selection':'immediate verified touching supported triad triples, some second inversion, same supplied key; retain nonmatches',
              'probe_policy':'each nonfinal 64 span: onset and last slice start against next span onset; deduplicate instants within pair',
              'source_conditioned':True,'blind_accuracy_measured':False,'production_enabled':False,
              'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records,scores=[],[]; skipped,roles=Counter(),Counter()
    for e in selected:
        folder=Path(e['package_path'])
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        if digest(e['score_source_path'])!=e['score_sha256']: raise ValueError('score_hash_mismatch')
        p=load_prepared_package(folder); ir=p['ir']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']: raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e); skipped.update(rejected)
        anns=p['annotations']; count=0
        for i,symbols,inversions,key in windows(anns,{a['annotation_id'] for a in valid}):
            group=anns[i:i+3]; result=propose(symbols,inversions,*key)
            span={'start':group[0]['target']['span']['start'],'end':group[-1]['target']['span']['end']}
            inventories,surfaces,probes=[],[],[]
            for a,c in zip(group,result['candidates']):
                inv=span_observation(ir,a['target']['span'])
                for cell in inv['slices']:
                    cell['complete_triad_shapes']=spelled_triad_shapes([r['pitch'] for r in cell['events']])
                    cell['supplied_shape_supported']=any(all(sh[k]==c[k] for k in ('root_step','root_alter','quality','inversion')) for sh in cell['complete_triad_shapes'])
                inv['union_is_simultaneous']=False
                inventories.append(inv); surfaces.append(observe_surface(inv,c))
            for j in range(2):
                if inversions[j]!=2: continue
                times={_exact(inventories[j]['span']['start']),_exact(inventories[j]['slices'][-1]['span']['start'])}
                for t in sorted(times):
                    probes.append({'source_pair_indices':[j,j+1],
                                   'observation':assess_direct(ir,t,group[j+1]['target']['span']['start'])})
            cid='u20_'+hashlib.sha256((ir['ir_document_id']+'|'+group[0]['annotation_id']).encode()).hexdigest()[:16]
            record={'case_id':cid,'concept_id':'hvl.unit20','identity':e,'package_hashes':hashes,
                    'target_span':span,'target_annotation_ids':[a['annotation_id'] for a in group],
                    'target_source_labels':[a['raw_label'] for a in group],
                    'printed_measure_range':[group[0]['raw_fields'].get('mn'),group[-1]['raw_fields'].get('mn')],
                    'source_context':anns[max(0,i-2):i+5],'context_excerpt':context_excerpt(ir,span),
                    'conditional_roles':result,'surface_inventories':inventories,'surface_observations':surfaces,
                    'direct_motion_probes':probes,'source_conditioned':True,'training_eligible':False,'production_enabled':False}
            path=out/(cid+'.json'); path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            tags=[r['role'] for r in result['role_candidates']]; roles.update(tags)
            records.append({'case_id':cid,'score':folder.name,'collection':e['collection_id'],'symbols':symbols,
                            'inversions':inversions,'role_candidates':tags,'printed_measure_range':record['printed_measure_range'],
                            'matching_lowest_duration_ratios':[s['matching_lowest_duration_ratio'] for s in surfaces],
                            'any_complete_support_per_span':[any(c['supplied_shape_supported'] for c in inv['slices']) for inv in inventories],
                            'probe_count':len(probes),'supported_direct_probe_count':sum(x['observation']['direct_resolution_geometry_supported'] for x in probes),
                            'json_sha256':digest(path)})
            count+=1
        scores.append({'score':folder.name,'case_count':count,'package_hashes':hashes})
    summary={'score_count':len(scores),'case_count':len(records),'role_candidate_counts':dict(roles),
             'cases_without_roles':sum(not r['role_candidates'] for r in records),
             'probe_count':sum(r['probe_count'] for r in records),
             'supported_direct_probe_count':sum(r['supported_direct_probe_count'] for r in records),
             'augmented_III_windows':sum('III+' in r['symbols'] for r in records)}
    report={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
            'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--manifest',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args(); print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
