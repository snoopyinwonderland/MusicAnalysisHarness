"""Unit 12 train-sonata case links and conditional observations; not blind accuracy."""
import argparse
from collections import Counter
import json
from pathlib import Path
import hashlib
from .cadential_six_four_audit import digest, source_key, span_inventory
from .sixth_degree_evidence import assess_transition, VERSION
from .harmony_case_retrieval import _f, load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt


def source_anchor(annotation):
    r=annotation['raw_fields']
    if any(r.get(k) for k in ('form','changes','added_tones','relativeroot','pedal','special')):
        return False
    return (r.get('numeral'),r.get('figbass','')) in (('vi',''),('VI',''),('IV','6'),('iv','6'))


def build(manifest_path,output):
    out=Path(output)
    if out.exists(): raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes(); entries=json.loads(raw)['entries']; validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected): raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected): raise ValueError('research_not_permitted')
    out.mkdir(parents=True)
    modules=['sixth_degree_audit.py','sixth_degree_evidence.py','cadential_six_four_audit.py',
             'predominant_sonata_audit.py','foundation_sonata_audit.py','harmony_case_retrieval.py',
             'harmony_review_supplement.py','harmony_review_cohort.py','harmony_curriculum.py','tonal_foundations.py']
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
        'selection':'all verified train sonata unmodified root VI/vi or IV6/iv6 anchors and immediate successor; same source key, adjacent spans',
        'checkpoints':['both_source_onsets','last_left_slice_and_first_right_slice'],
        'source_keys_and_ranges_supplied':True,'source_labels_used_for_selection':True,
        'blind_accuracy_measured':False,'production_enabled':False,
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[]; scores=[]; skipped=Counter(); counts=Counter(); relation_counts=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        p=load_prepared_package(folder); ir=p['ir']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']: raise ValueError('ir_identity_mismatch')
        annotations,rejected=verified_annotations(p,e); skipped.update(rejected); n=0
        for i,a in enumerate(annotations):
            if not source_anchor(a): continue
            if i+1==len(annotations): skipped['no_successor']+=1; continue
            b=annotations[i+1]; left,right=a['target']['span'],b['target']['span']
            if _f(left['end'])!=_f(right['start']):skipped['nonadjacent']+=1;continue
            if source_key(a)!=source_key(b):skipped['source_key_change']+=1;continue
            tonic,alter,mode=source_key(a)
            inventories=[span_inventory(ir,s,tonic,alter,mode) for s in (left,right)]
            x,y=inventories
            evidence={name:assess_transition(l['events'],r['events'],tonic,alter,mode)
                for name,l,r in (('onsets',x['slices'][0],y['slices'][0]),
                                  ('boundary',x['slices'][-1],y['slices'][0]))}
            # Coordinates in inventory are harmonic-minor references, not a ban
            # on raised-sixth IV6; classifier uses explicit variants separately.
            active_relations=sorted({k for v in evidence.values() for k,ok in v['relations'].items() if ok})
            relation_counts.update(active_relations)
            span={'start':left['start'],'end':right['end']}
            cid='u12_'+hashlib.sha256((e['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            record={'case_id':cid,'identity':e,'package_hashes':hashes,'target_span':span,
                'labels':[a['raw_label'],b['raw_label']],'printed_measure':a['raw_fields'].get('mn'),
                'target_annotation_ids':[a['annotation_id'],b['annotation_id']],
                'source_context':annotations[max(0,i-1):i+3],
                'source_cadence_fields':[r['raw_fields'].get('cadence','') for r in (a,b)],
                'span_inventories':inventories,'evidence':evidence,'context_excerpt':context_excerpt(ir,span),
                'source_conditioned':True,'cadence_verified':False,'training_eligible':False,'production_enabled':False}
            (out/(cid+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            records.append({'case_id':cid,'score':folder.name,'collection':e['collection_id'],
                'labels':record['labels'],'printed_measure':record['printed_measure'],
                'relations':active_relations,'json_sha256':digest(out/(cid+'.json')),
                'both_complete_at_either_checkpoint':any(all(o['complete_surface_candidates'] for o in v['observations']) for v in evidence.values())})
            counts[e['collection_id']]+=1; n+=1
        scores.append({'score':folder.name,'collection':e['collection_id'],'case_count':n,'package_hashes':hashes})
    summary={'score_count':len(scores),'case_count':len(records),'by_collection':dict(counts),
        'complete_shapes_both_sides_at_either_checkpoint':sum(r['both_complete_at_either_checkpoint'] for r in records),
        'relation_support_counts':dict(relation_counts)}
    report={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
        'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    args=p.parse_args(); print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
