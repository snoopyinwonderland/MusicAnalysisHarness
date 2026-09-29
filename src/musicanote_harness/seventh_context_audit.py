"""Train-only Unit25 adjacent source-chord diagnostics, not blind evaluation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .seventh_context import VERSION, source_chord, observe, succession
from .dominant_area_evidence import _exact


def build(manifest_path, output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    modules=['seventh_context.py','seventh_context_audit.py','cadential_six_four_audit.py','harmony_case_retrieval.py',
             'harmony_review_cohort.py','harmony_review_supplement.py','foundation_sonata_audit.py',
             'dominant_area_evidence.py','tonal_foundations.py','formal_ir.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
              'selection':'verified unmodified nonapplied sevenths immediately followed by supported triad/seventh in same source key',
              'context':'pair measures plus one before/after; original annotation order, no skipped labels',
              'source_conditioned':True,'blind_accuracy_measured':False,'production_enabled':False,
              'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];scores=[];skipped=Counter();qualities=Counter();tags=Counter();statuses=Counter();cross=Counter();patterns=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p=load_prepared_package(folder);ir=p['ir']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e);skipped.update(rejected);ids={a['annotation_id'] for a in valid}
        anns=p['annotations'];count=0
        for i,a in enumerate(anns[:-1]):
            if a['annotation_id'] not in ids:continue
            key=source_key(a);h=source_chord(a,*key)
            if h is None or len(h['members'])!=4:continue
            n=anns[i+1]
            if n['annotation_id'] not in ids:skipped['next_unverified']+=1;continue
            if source_key(n)!=key:skipped['key_change']+=1;continue
            nxt=source_chord(n,*key)
            if nxt is None:skipped['next_unsupported']+=1;continue
            span=a['target']['span'];ns=n['target']['span']
            if _exact(span['end'])!=_exact(ns['start']):skipped['nonadjacent']+=1;continue
            combined={'start':span['start'],'end':ns['end']};context=context_excerpt(ir,combined)
            evidence=observe(ir,span,context['context_span'],h,nxt)
            chain=[h,nxt]
            for extra in anns[i+2:i+4]:
                prev=anns[i+len(chain)-1]
                if extra['annotation_id'] not in ids or source_key(extra)!=key or _exact(prev['target']['span']['end'])!=_exact(extra['target']['span']['start']):break
                c=source_chord(extra,*key)
                if c is None:break
                chain.append(c)
            relations=succession(chain)
            cid='u25_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']+'|'+n['annotation_id']).encode()).hexdigest()[:16]
            case={'case_id':cid,'concept_id':'hvl.unit25','identity':e,'package_hashes':hashes,
                  'source_annotations':[a,n],'source_context':[{'annotation':v,'alignment_verified':v['annotation_id'] in ids} for v in anns[max(0,i-1):i+4]],
                  'context_excerpt':context,'evidence':evidence,'supplied_chain':chain,'succession':relations,
                  'source_conditioned':True,'training_eligible':False,'production_enabled':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            ts=Counter(t for r in evidence['paths'] for t in r['geometry_tags']);st=Counter(r['departure_status'] for r in evidence['paths'])
            cr=Counter(v['kind'] for r in evidence['paths'] for v in r['cross_voice_coincidences'])
            tags.update(ts);statuses.update(st);cross.update(cr);patterns.update(relations['pattern_candidates']);qualities[h['quality']]+=1;count+=1
            records.append({'case_id':cid,'score':folder.name,'collection':e['collection_id'],'printed_measure':a['raw_fields'].get('mn'),
                            'source_labels':[a['raw_label'],n['raw_label']],'quality':h['quality'],
                            'complete_vertical_match':any(c['complete_supplied_match'] for c in evidence['vertical_cells']),
                            'members_present_in_union':not evidence['missing_spellings'],
                            'apparent_alternative_count':len(evidence['apparent_alternatives']),
                            'apparent_upward_paths':sum('root_up_step' in r['geometry_tags'] for r in evidence['paths']) if evidence['apparent_alternatives'] else 0,
                            'path_tags':dict(ts),'path_statuses':dict(st),'cross_voice_coincidences':dict(cr),
                            'pattern_candidates':relations['pattern_candidates'],'json_sha256':digest(path)})
        scores.append({'score':folder.name,'case_count':count,'package_hashes':hashes})
    summary={'score_count':len(scores),'case_count':len(records),'by_quality':dict(qualities),
             'complete_vertical_matches':sum(r['complete_vertical_match'] for r in records),
             'members_present_in_union':sum(r['members_present_in_union'] for r in records),
             'cases_with_apparent_alternative':sum(r['apparent_alternative_count']>0 for r in records),
             'cases_with_apparent_upward_path':sum(r['apparent_upward_paths']>0 for r in records),
             'path_tags':dict(tags),'path_statuses':dict(statuses),'cross_voice_coincidences':dict(cross),'root_chain_candidates':dict(patterns)}
    result={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
            'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
