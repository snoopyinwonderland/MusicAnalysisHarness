"""Unit24 train-only diagnostics; source key/range supplied, not blind accuracy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .mixture_evidence import VERSION, source_candidate, observe


def build(manifest_path,output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    modules=['mixture_evidence.py','mixture_audit.py','cadential_six_four_audit.py','harmony_case_retrieval.py',
             'harmony_review_cohort.py','harmony_review_supplement.py','foundation_sonata_audit.py',
             'dominant_area_evidence.py','tonal_foundations.py','formal_ir.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
              'selection':'all verified unmodified nonapplied source labels supported by Unit24 adapter',
              'context':'target measures plus one before and after; original annotation order',
              'source_labels_used_for_selection_and_posthoc_comparison':True,
              'observation_inputs':'IR, source key, source range; no source chord label',
              'source_conditioned':True,'blind_accuracy_measured':False,'production_enabled':False,
              'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];scores=[];skipped=Counter();families=Counter();paths=Counter();statuses=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p=load_prepared_package(folder);ir=p['ir']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e);skipped.update(rejected);valid_ids={a['annotation_id'] for a in valid};count=0
        for i,a in enumerate(p['annotations']):
            if a['annotation_id'] not in valid_ids:continue
            candidate=source_candidate(a)
            if candidate is None:continue
            family,inversion=candidate;span=a['target']['span'];context=context_excerpt(ir,span)
            evidence=observe(ir,span,context['context_span'],*source_key(a))
            coverage=next(c for c in evidence['template_coverage'] if c['hypothesis']['family']==family)
            matched=any(m['inversion']==inversion for m in coverage['complete_vertical_matches'])
            tags=Counter(t for r in evidence['coordinate_paths'] for t in r['geometry_tags'])
            states=Counter(r['departure_status'] for r in evidence['coordinate_paths'])
            cid='u24_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            source_context=[{'annotation':n,'alignment_verified':n['annotation_id'] in valid_ids} for n in p['annotations'][max(0,i-1):i+3]]
            case={'case_id':cid,'concept_id':'hvl.unit24','identity':e,'package_hashes':hashes,
                  'target_annotation_id':a['annotation_id'],'source_annotation':a,'source_context':source_context,
                  'context_excerpt':context,'evidence':evidence,
                  'posthoc_source_comparison':{'family':family,'inversion':inversion,'complete_vertical_match':matched,
                                               'missing_spellings':coverage['missing_spellings'],'extra_event_refs':coverage['extra_event_refs']},
                  'source_conditioned':True,'training_eligible':False,'production_enabled':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            records.append({'case_id':cid,'score':folder.name,'collection':e['collection_id'],
                            'printed_measure':a['raw_fields'].get('mn'),'source_label':a['raw_label'],'family':family,
                            'inversion':inversion,'complete_vertical_source_match':matched,
                            'source_members_present_in_union':not coverage['missing_spellings'],
                            'coordinate_tagged_events':sum(bool(e['coordinate_tags']) for e in evidence['events']),
                            'path_tags':dict(tags),'path_statuses':dict(states),'json_sha256':digest(path)})
            count+=1;families[family]+=1;paths.update(tags);statuses.update(states)
        scores.append({'score':folder.name,'case_count':count,'package_hashes':hashes})
    summary={'score_count':len(scores),'case_count':len(records),'by_family':dict(families),
             'complete_vertical_source_matches':sum(r['complete_vertical_source_match'] for r in records),
             'source_members_present_in_union':sum(r['source_members_present_in_union'] for r in records),
             'coordinate_tagged_event_occurrences':sum(r['coordinate_tagged_events'] for r in records),
             'path_tags':dict(paths),'path_statuses':dict(statuses)}
    result={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
            'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
