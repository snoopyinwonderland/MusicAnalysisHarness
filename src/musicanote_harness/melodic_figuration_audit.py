"""Revisit fixed Unit20 train windows, deduplicating adjacent annotation pairs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .melodic_figuration import VERSION, compare_blocks, condition_on_triads


def build(source, output):
    src,out=Path(source),Path(output)
    if out.exists(): raise ValueError('output_exists')
    report=json.loads((src/'report.json').read_text(encoding='utf-8'))
    contract=json.loads((src/'run-contract.json').read_text(encoding='utf-8'))
    if digest(src/'run-contract.json')!=report['contract_sha256']: raise ValueError('source_contract_hash_mismatch')
    entries=contract['entries']; validate_split(entries)
    if any(e['split']!='train' or e['rights'].get('internal_research_use') is not True for e in entries):
        raise ValueError('train_research_entries_required')
    if len({e['ir_document_id'] for e in entries})!=len(entries): raise ValueError('duplicate_ir_identity')
    entry_map={e['ir_document_id']:e for e in entries}
    cache={}; pairs={}
    for row in report['records']:
        path=src/(row['case_id']+'.json')
        if digest(path)!=row['json_sha256']: raise ValueError('source_case_hash_mismatch')
        case=json.loads(path.read_text(encoding='utf-8')); e=case['identity']
        if entry_map.get(e['ir_document_id'])!=e: raise ValueError('source_entry_mismatch')
        if e['ir_document_id'] not in cache:
            folder=Path(e['package_path'])
            if digest(e['score_source_path'])!=e['score_sha256']: raise ValueError('score_hash_mismatch')
            for name,value in case['package_hashes'].items():
                if digest(folder/name)!=value: raise ValueError('package_hash_mismatch')
            package=load_prepared_package(folder); ir=package['ir']
            if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']: raise ValueError('ir_identity_mismatch')
            valid,_=verified_annotations(package,e)
            cache[e['ir_document_id']]=(package,{a['annotation_id'] for a in valid})
        package,valid_ids=cache[e['ir_document_id']]
        for j in range(2):
            ids=case['target_annotation_ids'][j:j+2]
            if any(i not in valid_ids for i in ids): raise ValueError('unverified_source_annotation')
            sequence=[a['annotation_id'] for a in package['annotations']]
            k=sequence.index(ids[0])
            if sequence[k:k+2]!=ids: raise ValueError('nonadjacent_source_pair')
            key=(e['ir_document_id'],*ids)
            pairs.setdefault(key,{'case':case,'index':j,'parents':[]})['parents'].append(row['case_id'])
    out.mkdir(parents=True)
    modules=['melodic_figuration.py','melodic_figuration_audit.py','diatonic_sequence.py','counterpoint_evidence.py',
             'harmony_joint.py','dominant_area_evidence.py','formal_ir.py','foundation_sonata_audit.py',
             'tonal_foundations.py','harmony_case_retrieval.py','harmony_review_cohort.py',
             'harmony_review_supplement.py','cadential_six_four_audit.py','harmony_curriculum.py']
    run={'version':VERSION,'parent_report_sha256':digest(src/'report.json'),'parent_contract_sha256':report['contract_sha256'],
         'parent_directory':str(src.resolve()),'entries':entries,'selection':'all unique adjacent pairs from fixed Unit20 triples, including nonmatches',
         'source_conditioned':True,'blind_accuracy_measured':False,'production_enabled':False,
         'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[]; abstentions=Counter(); geometry=Counter()
    for key,item in pairs.items():
        parent,j=item['case'],item['index']; package,_=cache[key[0]]; ir=package['ir']
        anns={a['annotation_id']:a for a in package['annotations']}; group=[anns[x] for x in key[1:]]
        spans=[a['target']['span'] for a in group]
        observed=compare_blocks(ir,*spans)
        conditional=condition_on_triads(observed,*parent['conditional_roles']['candidates'][j:j+2])
        cid='u21_'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:16]
        span={'start':spans[0]['start'],'end':spans[1]['end']}
        record={'case_id':cid,'concept_id':'hvl.unit21','identity':parent['identity'],
                'package_hashes':parent['package_hashes'],'parent_case_ids':item['parents'],
                'target_annotation_ids':list(key[1:]),'source_annotations':group,
                'target_span':span,'context_excerpt':context_excerpt(ir,span),
                'observation':observed,'conditional_harmony_links':conditional,
                'source_conditioned':True,'training_eligible':False,'production_enabled':False}
        path=out/(cid+'.json');path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        for v in observed['voices']:
            abstentions.update(v['abstention_reasons']); geometry.update(g['pattern'] for g in v['adjacent_melodic_geometry'])
        projected=sum(v['compound_correspondence_candidate'] for v in observed['voices'])
        resolved=sum(len(v['compound_resolution_candidates']) for v in conditional['voices'])
        records.append({'case_id':cid,'score':Path(parent['identity']['package_path']).name,
                        'collection':parent['identity']['collection_id'],'parent_case_ids':item['parents'],
                        'printed_measures':[a['raw_fields'].get('mn') for a in group],
                        'source_labels':[a['raw_label'] for a in group],
                        'compound_correspondence_voice_candidates':projected,
                        'compound_resolution_candidates':resolved,'json_sha256':digest(path)})
    summary={'score_count':len(cache),'pair_count':len(records),
             'pairs_with_compound_correspondence':sum(r['compound_correspondence_voice_candidates']>0 for r in records),
             'compound_correspondence_voice_candidates':sum(r['compound_correspondence_voice_candidates'] for r in records),
             'compound_resolution_candidates':sum(r['compound_resolution_candidates'] for r in records)}
    result={'version':VERSION,'summary':summary,'records':records,'voice_abstention_counts':dict(abstentions),
            'adjacent_geometry_counts':dict(geometry),'contract_sha256':digest(out/'run-contract.json'),
            'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();print(json.dumps(build(args.source,args.output)['summary'],indent=2))
