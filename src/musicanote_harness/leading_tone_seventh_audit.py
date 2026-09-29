"""Unit23 source-conditioned train sonatas: shapes and independent member paths."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .predominant_sonata_audit import span_observation
from .tonal_foundations import spelled_seventh_shapes
from .leading_tone_seventh import VERSION, source_candidate, hypothesis, trace_members


def build(manifest_path,output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    modules=['leading_tone_seventh.py','leading_tone_seventh_audit.py','cadential_six_four_audit.py',
             'harmony_case_retrieval.py','harmony_review_cohort.py','harmony_review_supplement.py',
             'predominant_sonata_audit.py','foundation_sonata_audit.py','dominant_area_evidence.py',
             'tonal_foundations.py','formal_ir.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
              'selection':'all verified unmodified nonapplied leading-tone diminished/half-diminished sevenths and inversions',
              'context':'target measures plus one before and after; original annotation order and full sounding spans',
              'source_conditioned':True,'blind_accuracy_measured':False,'production_enabled':False,
              'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];scores=[];skipped=Counter();families=Counter();statuses=Counter();motions=Counter()
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
            quality,inversion=candidate;tonic,alter,mode=source_key(a)
            h=hypothesis(tonic,alter,mode,quality,inversion);span=a['target']['span'];context=context_excerpt(ir,span)
            evidence=trace_members(ir,span,context['context_span'],h)
            inv=span_observation(ir,span)
            for cell in inv['slices']:
                shapes=spelled_seventh_shapes([r['pitch'] for r in cell['events']])
                cell['complete_seventh_shapes']=shapes
                cell['supplied_shape_supported']=any(s['quality']==quality and s['inversion']==inversion and
                    [s['root_step'],s['root_alter']]==h['members']['root'] for s in shapes)
            inv['union_is_simultaneous']=False
            cid='u23_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            source_context=[{'annotation':n,'alignment_verified':n['annotation_id'] in valid_ids} for n in p['annotations'][max(0,i-1):i+3]]
            case={'case_id':cid,'concept_id':'hvl.unit23','identity':e,'package_hashes':hashes,
                  'target_annotation_id':a['annotation_id'],'source_annotation':a,'source_context':source_context,
                  'context_excerpt':context,'surface_inventory':inv,'evidence':evidence,
                  'source_conditioned':True,'training_eligible':False,'production_enabled':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            exits=Counter(r['member'] for r in evidence['records'] if r['exit_step_candidate'])
            stats=Counter(r['departure_status'] for r in evidence['records']);statuses.update(stats);motions.update(exits)
            families[quality]+=1;count+=1
            records.append({'case_id':cid,'score':folder.name,'collection':e['collection_id'],
                            'printed_measure':a['raw_fields'].get('mn'),'source_label':a['raw_label'],
                            'quality':quality,'inversion':inversion,'textbook_profile':h['textbook_profile'],
                            'any_complete_surface_match':any(s['supplied_shape_supported'] for s in inv['slices']),
                            'member_exit_candidates':dict(exits),'departure_status_counts':dict(stats),
                            'json_sha256':digest(path)})
        scores.append({'score':folder.name,'case_count':count,'package_hashes':hashes})
    summary={'score_count':len(scores),'case_count':len(records),'by_quality':dict(families),
             'cases_with_complete_surface_match':sum(r['any_complete_surface_match'] for r in records),
             'member_exit_candidate_counts':dict(motions),'departure_status_counts':dict(statuses),
             'cases_with_both_independent_root_and_seventh_exit_candidates':sum(
                 all(r['member_exit_candidates'].get(k,0)>0 for k in ('root','seventh')) for r in records)}
    result={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
            'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
