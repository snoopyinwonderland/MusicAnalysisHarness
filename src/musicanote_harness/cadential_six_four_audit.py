"""Unit 11 source-conditioned train-sonata audit; not blind detection accuracy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from music21 import key, roman
from .cadential_six_four import assess, VERSION
from .formal_ir import q
from .harmony_case_retrieval import _f, load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .predominant_sonata_audit import span_observation


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_key(annotation):
    """Explicit source-conditioned test input, never inferred or fed to blind scoring."""
    r = annotation['raw_fields']
    if not r.get('globalkey') or not r.get('localkey') or r.get('localkey_is_minor') not in ('0','1'):
        raise ValueError('missing_source_key')
    token = r['globalkey'][:1] + r['globalkey'][1:].replace('b','-')
    tonic = roman.RomanNumeral(r['localkey'], key.Key(token)).root()
    alter = tonic.accidental.alter if tonic.accidental else 0
    if int(alter) != alter:
        raise ValueError('microtonal_key')
    return tonic.step, int(alter), 'minor' if r['localkey_is_minor']=='1' else 'major'


def span_inventory(ir, span, tonic, alter, mode):
    """Observations only: never turn the union into a sounding vertical chord."""
    from .tonal_foundations import scale_degree
    result = span_observation(ir,span)
    result['union_is_simultaneous'] = False
    for cell in result['slices']:
        cell['degrees'] = [scale_degree(*row['pitch'][:2],tonic,alter,
            'major' if mode=='major' else 'harmonic_minor') for row in cell['events']]
    return result


def build(manifest_path, output):
    out = Path(output)
    if out.exists():
        raise ValueError('output_exists')
    raw = Path(manifest_path).read_bytes()
    entries = json.loads(raw)['entries']
    validate_split(entries)
    selected = [e for e in entries if e['split']=='train' and
                e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected}) != len(selected):
        raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):
        raise ValueError('internal_research_not_allowed')
    out.mkdir(parents=True)
    modules = ['cadential_six_four.py','cadential_six_four_audit.py','tonal_foundations.py',
               'foundation_sonata_audit.py','predominant_sonata_audit.py',
               'harmony_review_supplement.py','harmony_review_cohort.py',
               'harmony_case_retrieval.py','formal_ir.py','harmony_curriculum.py']
    contract = {'version':VERSION, 'manifest_sha256':hashlib.sha256(raw).hexdigest(),
        'selection':'all train Mozart/Beethoven sonata source I/i64 records, including non-V followers',
        'sampling':'source starts and last pre-boundary slice start, next annotation start',
        'labels_used_to_select_cases':True, 'keys_and_times_from_source':True,
        'blind_accuracy_measured':False, 'production_enabled':False,
        'module_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules},
        'entries':selected}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records, scores, skipped = [], [], Counter()
    for e in selected:
        folder = Path(e['package_path'])
        hashes = {n:digest(folder/n) for n in
                  ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        if digest(e['score_source_path']) != e['score_sha256']:
            raise ValueError('score_hash_mismatch')
        p = load_prepared_package(folder); ir = p['ir']
        if ir['ir_document_id'] != e['ir_document_id'] or ir['score']['score_id'] != e['score_id']:
            raise ValueError('ir_identity_mismatch')
        annotations, rejects = verified_annotations(p,e); skipped.update(rejects)
        count = 0
        for i,a in enumerate(annotations):
            r = a['raw_fields']
            if r.get('numeral') not in ('I','i') or r.get('figbass') != '64':
                continue
            if r.get('relativeroot'):
                skipped['applied_tonic_six_four_not_supported'] += 1; continue
            if i+1 == len(annotations):
                skipped['no_following_annotation'] += 1; continue
            b = annotations[i+1]
            left,right = a['target']['span'],b['target']['span']
            if _f(left['end']) != _f(right['start']):
                skipped['nonadjacent_source'] += 1; continue
            if source_key(a) != source_key(b):
                skipped['source_key_change'] += 1; continue
            tonic,alter,mode = source_key(a)
            observed = span_observation(ir,left)
            checkpoints = {'onsets': left['start'], 'last_preboundary_slice':observed['slices'][-1]['span']['start']}
            evidence = {name:assess(ir,t,right['start'],tonic,alter,mode) for name,t in checkpoints.items()}
            total_span = {'start':left['start'],'end':right['end']}
            cid = 'u11_'+hashlib.sha256((e['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            record = {'case_id':cid,'collection':e['collection_id'],'score':folder.name,
                'identity':e,'package_hashes':hashes,'target_span':total_span,
                'source_annotations':annotations[max(0,i-1):i+3],
                'target_annotation_ids':[a['annotation_id'],b['annotation_id']],
                'labels':[a['raw_label'],b['raw_label']], 'printed_measure':r.get('mn'),
                'source_modifiers':{n:r.get(n,'') for n in ('changes','added_tones','relativeroot','pedal')},
                'evidence':evidence,'context_excerpt':context_excerpt(ir,total_span),
                'span_inventories':[span_inventory(ir,s,tonic,alter,mode) for s in (left,right)],
                'key_and_ranges_from_source':True, 'automatic_harmony_accuracy_measured':False,
                'cadence_verified':False,'training_eligible':False,'production_enabled':False}
            (out/(cid+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            records.append({'case_id':cid,'collection':e['collection_id'],'score':folder.name,
                'printed_measure':r.get('mn'),'labels':record['labels'],'span':total_span,
                'json_sha256':digest(out/(cid+'.json')),
                'checks':{name:{k:value[k] for k in ('surface_pair_supported','direct_resolution_geometry_supported','ambiguous_voice_refs')}
                          for name,value in evidence.items()}})
            count += 1
        scores.append({'collection':e['collection_id'],'score':folder.name,'cases':count,'package_hashes':hashes})
    summary = {'case_count':len(records),'score_count':len(scores),
        'surface_pair_supported_at_either_checkpoint':sum(any(x['surface_pair_supported'] for x in r['checks'].values()) for r in records),
        'direct_resolution_geometry_at_either_checkpoint':sum(any(x['direct_resolution_geometry_supported'] for x in r['checks'].values()) for r in records),
        'any_ambiguous_voice':sum(any(x['ambiguous_voice_refs'] for x in r['checks'].values()) for r in records)}
    report = {'version':VERSION,'summary':summary,'scores':scores,'records':records,'skipped':dict(skipped),
        'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,
        'source_annotations_are_not_gold':True,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--output',required=True)
    args=p.parse_args(); print(json.dumps(build(args.manifest,args.output)['summary'],indent=2))
