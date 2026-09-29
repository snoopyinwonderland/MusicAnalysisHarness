"""Unit26 source-conditioned train sonatas, preserving mismatches and unknowns."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .applied_chords import VERSION, source_applied, source_harmony, contextualize, observe
from .dominant_area_evidence import _exact


def build(manifest_path,output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    modules=['applied_chords.py','applied_chords_audit.py','seventh_context.py','cadential_six_four_audit.py',
             'harmony_case_retrieval.py','harmony_review_cohort.py','harmony_review_supplement.py',
             'foundation_sonata_audit.py','predominant_sonata_audit.py','dominant_area_evidence.py',
             'tonal_foundations.py','formal_ir.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
              'selection':'all verified unmodified applied V/V7/vii/vii7/half7 with single explicit major/minor target',
              'context':'target measures plus one before/after; adjacent original source annotations only; mismatches retained',
              'source_conditioned':True,'blind_accuracy_measured':False,'production_enabled':False,
              'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];scores=[];skipped=Counter();families=Counter();targets=Counter();roles=Counter();tags=Counter();statuses=Counter();neighbor_status=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p=load_prepared_package(folder);ir=p['ir']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e);skipped.update(rejected);ids={a['annotation_id'] for a in valid};anns=p['annotations'];count=0
        for i,a in enumerate(anns):
            if a['annotation_id'] not in ids:continue
            key=source_key(a);h=source_applied(a,*key)
            if h is None:
                if a['raw_fields'].get('relativeroot'):skipped['unsupported_applied_annotation']+=1
                continue
            span=a['target']['span'];context=context_excerpt(ir,span)
            ev=observe(ir,span,context['context_span'],h)
            neighbors={}
            for name,j in [('previous',i-1),('following',i+1)]:
                n=anns[j] if 0<=j<len(anns) else None;nh=None
                if n is None:status='absent'
                elif n['annotation_id'] not in ids:status='unverified'
                elif source_key(n)!=key:status='changed_source_key'
                elif _exact(n['target']['span']['end'] if name=='previous' else n['target']['span']['start'])!=_exact(span['start'] if name=='previous' else span['end']):status='nonadjacent'
                else:
                    nh=source_harmony(n,*key);status='supported' if nh else 'unsupported'
                neighbor_status[name+':'+status]+=1
                neighbors[name]={'status':status,'annotation_id':n['annotation_id'] if n else None,'hypothesis':nh}
            cx=contextualize(h,neighbors['previous']['hypothesis'],neighbors['following']['hypothesis'],key)
            cid='u26_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            case={'case_id':cid,'concept_id':'hvl.unit26','identity':e,'package_hashes':hashes,
                  'source_annotation':a,'source_context':[{'annotation':n,'alignment_verified':n['annotation_id'] in ids} for n in anns[max(0,i-1):i+3]],
                  'source_key':key,'neighbors':neighbors,'context_excerpt':context,'evidence':ev,'contextual_comparison':cx,
                  'source_conditioned':True,'training_eligible':False,'production_enabled':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            ts=Counter(t for r in ev['critical_paths'] for t in r['geometry_tags']);st=Counter(r['departure_status'] for r in ev['critical_paths'])
            tags.update(ts);statuses.update(st);roles.update(cx['role_candidates']);families[h['family']]+=1;targets[a['raw_fields']['relativeroot']]+=1;count+=1
            records.append({'case_id':cid,'score':folder.name,'collection':e['collection_id'],'printed_measure':a['raw_fields'].get('mn'),
                            'source_label':a['raw_label'],'family':h['family'],'target':a['raw_fields']['relativeroot'],
                            'complete_vertical_match':any(s['complete_supplied_match'] for s in ev['surface']['slices']),
                            'members_present_in_union':not ev['missing_spellings'],'role_candidates':cx['role_candidates'],
                            'following_target_match':cx['following_has_target_triad_core'],
                            'critical_path_tags':dict(ts),'critical_path_statuses':dict(st),
                            'json_sha256':digest(path)})
        scores.append({'score':folder.name,'case_count':count,'package_hashes':hashes})
    summary={'score_count':len(scores),'case_count':len(records),'families':dict(families),'targets':dict(targets),
             'complete_vertical_matches':sum(r['complete_vertical_match'] for r in records),
             'members_present_in_union':sum(r['members_present_in_union'] for r in records),
             'following_target_status':dict(Counter('unknown' if r['following_target_match'] is None else 'compatible' if r['following_target_match'] else 'different' for r in records)),
             'role_candidates':dict(roles),'path_tags':dict(tags),'path_statuses':dict(statuses),'neighbor_statuses':dict(neighbor_status)}
    result={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
            'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
