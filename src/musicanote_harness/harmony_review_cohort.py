"""Reproducible train review queue from audited facts, not musical gold labels."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from .harmony_joint import f


def validate_split(entries):
    seen={}
    for e in entries:
        if e['split'] not in ('train','dev','holdout'):raise ValueError('unknown_split')
        for field in ('work_family_id','score_sha256','annotation_sha256'):
            key=(field,e[field])
            if key in seen and seen[key]!=e['split']:raise ValueError('cross_split_identity:'+field)
            seen[key]=e['split']


def tags(record):
    o=record['observation'];c=record['comparison']
    result=['source_triad_'+c['source_quality']]
    if c['source_inversion']>0:result.append('source_inversion')
    vertical=any(s['shapes'] for s in o['slices'])
    if vertical:result.append('complete_vertical_shape_present')
    if o['union_shapes'] and not vertical:result.append('distributed_complete_shape_candidate')
    if not o['union_shapes'] and not vertical:result.append('no_complete_shape_needs_review')
    return result


def build(manifest_path, records_path, output, per_family=3):
    if per_family<1:raise ValueError('positive_family_cap_required')
    manifest_bytes=Path(manifest_path).read_bytes();records_bytes=Path(records_path).read_bytes()
    manifest=json.loads(manifest_bytes);entries=manifest['entries'];validate_split(entries)
    lookup={e['package_path']:e for e in entries}
    if len(lookup)!=len(entries):raise ValueError('duplicate_package')
    pools=defaultdict(list);skipped=Counter();seen=set()
    for line in records_bytes.decode('utf-8').splitlines():
        r=json.loads(line);e=lookup.get(r['package'])
        if e is None:raise ValueError('unregistered_package')
        if e['split']!='train':raise ValueError('non_train_audit_record')
        if (r['identity']['split']!='train' or r['identity']['work_family_id']!=e['work_family_id']
            or r['score_sha256']!=e['score_sha256'] or r['source_asset_sha256']!=e['annotation_sha256']
            or r['ir_document_id']!=e['ir_document_id']):raise ValueError('audit_identity_mismatch')
        key=(e['ir_document_id'],r['annotation_id'])
        if key in seen:raise ValueError('duplicate_annotation')
        seen.add(key)
        category=tags(r)
        case_id='review_'+hashlib.sha256(('|'.join(key)).encode()).hexdigest()[:20]
        record={'case_id':case_id,'package_path':e['package_path'],'score_id':e['score_id'],
            'ir_document_id':e['ir_document_id'],'work_family_id':e['work_family_id'],
            'collection':e['collection_id'],'split':'train','tags':category,
            'target_span':r['observation']['span'],'annotation_id':r['annotation_id'],
            'source_locator':r['source_locator'],'source_label':r['source_label'],
            'printed_measure':r['printed_measure'],'score_sha256':e['score_sha256'],
            'annotation_sha256':e['annotation_sha256'],'rights':e['rights'],
            'review_status':'unreviewed','musical_gold':False,'training_eligible':False,
            'context_package_ref':e['package_path'],'context_extract_created':False}
        for t in category:pools[t].append(record)
    selections={};selected={};coverage={}
    for tag,rows in sorted(pools.items()):
        families=Counter();chosen=[]
        for r in sorted(rows,key=lambda r:r['case_id']):
            family=r['work_family_id']
            if families[family]>=per_family:continue
            families[family]+=1;chosen.append(r['case_id']);selected[r['case_id']]=r
        selections[tag]=chosen
        coverage[tag]={'available':len(rows),'selected':len(chosen),'families':len(families)}
    # Only manifest metadata: no dev/holdout packages or labels opened.
    reserved=[{k:e[k] for k in ('manifest_entry_id','work_family_id','collection_id','split','eligibility')}
              for e in entries if e['split']!='train']
    report={'version':'harmony-review-cohort-0.1.0','manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),
        'audit_sha256':hashlib.sha256(records_bytes).hexdigest(),'per_family_per_tag_cap':per_family,
        'coverage':coverage,'unique_selected':len(selected),'source_records':len(seen),
        'unfilled_categories':['verified_nct','verified_omission','seventh_chord_controls','short_harmonic_change'],
        'limitations':['Triad audit only; not full corpus','Tags are proxies, not gold labels',
                       'Family diversity may remain low','Rights and blind-evaluation approval not granted'],
        'reserved_metadata':reserved,'reserved_contents_read':False,'production_enabled':False}
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'cases.jsonl').write_text(''.join(json.dumps(selected[k],ensure_ascii=False)+'\n' for k in sorted(selected)),encoding='utf-8')
    (out/'strata.json').write_text(json.dumps(selections,indent=2),encoding='utf-8')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:v for k,v in report.items() if k!='reserved_metadata'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--records',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.manifest,a.records,a.output),indent=2))
