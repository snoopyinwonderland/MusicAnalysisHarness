"""Unit 17 adjacent source-conditioned root-triad windows in train sonatas."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import _f, load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .predominant_sonata_audit import span_observation
from .tonal_foundations import spelled_triad_shapes
from .root_position_context import propose, source_symbol, VERSION


def windows(annotations):
    """Never bridge a missing annotation, time gap, key change or unsupported chord."""
    for i in range(len(annotations)-2):
        group = annotations[i:i+3]
        symbols = [source_symbol(a) for a in group]
        if not all(symbols):
            continue
        keys = [source_key(a) for a in group]
        if keys[0] != keys[1] or keys[1] != keys[2]:
            continue
        if any(_f(a['target']['span']['end']) != _f(b['target']['span']['start']) for a,b in zip(group,group[1:])):
            continue
        yield i, symbols, keys[0]


def build(manifest_path, output):
    out = Path(output)
    if out.exists():
        raise ValueError('output_exists')
    raw = Path(manifest_path).read_bytes()
    entries = json.loads(raw)['entries']
    validate_split(entries)
    selected = [e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected}) != len(selected):
        raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):
        raise ValueError('research_not_permitted')
    out.mkdir(parents=True)
    names = ['root_position_context.py','root_position_audit.py','cadential_six_four_audit.py',
             'harmony_case_retrieval.py','harmony_review_cohort.py','harmony_review_supplement.py',
             'predominant_sonata_audit.py','foundation_sonata_audit.py','tonal_foundations.py','harmony_curriculum.py']
    contract = {'version':VERSION,'entries':selected,'manifest_sha256':hashlib.sha256(raw).hexdigest(),
                'selection':'all immediate touching triples of supported plain root-position triads in same source local key; retain nonmatching patterns',
                'source_conditioned':True,'blind_accuracy_measured':False,'production_enabled':False,
                'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records, scores = [], []
    skipped, role_counts = Counter(), Counter()
    for e in selected:
        folder = Path(e['package_path'])
        hashes = {n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        if digest(e['score_source_path']) != e['score_sha256']:
            raise ValueError('score_hash_mismatch')
        p = load_prepared_package(folder)
        ir = p['ir']
        if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
            raise ValueError('ir_identity_mismatch')
        annotations, rejected = verified_annotations(p,e)
        skipped.update(rejected)
        count = 0
        for i,symbols,key in windows(annotations):
            group = annotations[i:i+3]
            result = propose(symbols,*key)
            span = {'start':group[0]['target']['span']['start'],'end':group[-1]['target']['span']['end']}
            inventories = []
            for a, c in zip(group,result['candidates']):
                inv = span_observation(ir,a['target']['span'])
                for cell in inv['slices']:
                    cell['complete_triad_shapes'] = spelled_triad_shapes([r['pitch'] for r in cell['events']])
                    cell['supplied_shape_supported'] = any(all(sh[k]==c[k] for k in ('root_step','root_alter','quality','inversion')) for sh in cell['complete_triad_shapes'])
                inv['union_is_simultaneous'] = False
                inventories.append(inv)
            cid = 'u17_'+hashlib.sha256((ir['ir_document_id']+'|'+group[0]['annotation_id']).encode()).hexdigest()[:16]
            record = {'case_id':cid,'concept_id':'hvl.unit17','identity':e,'package_hashes':hashes,
                      'target_span':span,'target_annotation_ids':[a['annotation_id'] for a in group],
                      'target_source_labels':[a['raw_label'] for a in group],
                      'printed_measure_range':[group[0]['raw_fields'].get('mn'),group[-1]['raw_fields'].get('mn')],
                      'source_context':annotations[max(0,i-2):i+5], 'context_excerpt':context_excerpt(ir,span),
                      'surface_inventories':inventories,'conditional_role_candidates':result,
                      'source_conditioned':True,'training_eligible':False,'production_enabled':False}
            path = out/(cid+'.json')
            path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            roles = [r['role'] for r in result['role_hypotheses']]
            records.append({'case_id':cid,'score':folder.name,'collection':e['collection_id'],
                            'printed_measure_range':record['printed_measure_range'],'symbols':symbols,'role_candidates':roles,
                            'any_complete_support_per_span':[any(c['supplied_shape_supported'] for c in inv['slices']) for inv in inventories],
                            'json_sha256':digest(path)})
            role_counts.update(roles)
            count += 1
        scores.append({'score':folder.name,'case_count':count,'package_hashes':hashes})
    report = {'version':VERSION,'summary':{'score_count':len(scores),'case_count':len(records),
              'role_candidate_counts':dict(role_counts),'cases_without_pattern':sum(not r['role_candidates'] for r in records),
              'all_three_spans_have_some_complete_support':sum(all(r['any_complete_support_per_span']) for r in records)},
              'records':records,'scores':scores,'skipped':dict(skipped),'contract_sha256':digest(out/'run-contract.json'),
              'blind_accuracy_measured':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
