"""Unit30 train-only audit. Imported labels select cases, not prove predictions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .applied_chords import source_harmony
from .neapolitan_evidence import context_roles
from .dominant_area_evidence import _exact
from .augmented_sixth import VERSION, source_reference, observe


def build(manifest_path, output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    names=['augmented_sixth.py','augmented_sixth_audit.py','neapolitan_evidence.py','diatonic_modulation.py','applied_chords.py',
        'seventh_context.py','cadential_six_four_audit.py','harmony_case_retrieval.py','harmony_review_cohort.py',
        'harmony_review_supplement.py','foundation_sonata_audit.py','predominant_sonata_audit.py',
        'dominant_area_evidence.py','formal_ir.py','tonal_foundations.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
        'selection':'all It/Ger/Fr special labels in train 12 sonatas; preserve unsupported cases',
        'context':'one measure before/after; original immediate following source annotation only',
        'source_conditioned':True,'training_eligible':False,'production_enabled':False,
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];skipped=Counter();paths=Counter();pairs=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p=load_prepared_package(folder);ir=p['ir'];anns=p['annotations']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e);skipped.update(rejected);ids={a['annotation_id'] for a in valid}
        for i,a in enumerate(anns):
            if a['raw_fields'].get('special') not in ('It','Ger','Fr'):continue
            key=source_key(a);h=source_reference(a,key);ctx=None;ev=None
            status='unverified_alignment' if a['annotation_id'] not in ids else 'unsupported_source_chord' if h is None else 'observed'
            if a['annotation_id'] in ids:ctx=context_excerpt(ir,a['target']['span'])
            if status=='observed':
                ev=observe(ir,a['target']['span'],ctx['context_span'],h)
                paths.update(r['departure_status'] for r in ev['critical_paths'])
                pairs.update(r['kind'] for r in ev['joint_geometry'])
            else:skipped[status]+=1
            n=anns[i+1] if i+1<len(anns) else None;nh=None
            if n is None:ns='absent'
            elif n['annotation_id'] not in ids:ns='unverified'
            elif source_key(n)!=key:ns='changed_source_key'
            elif _exact(n['target']['span']['start'])!=_exact(a['target']['span']['end']):ns='nonadjacent'
            else:nh=source_harmony(n,*key);ns='supported_shape' if nh else 'unsupported_shape'
            cid='u30_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            case={'case_id':cid,'concept_id':'hvl.unit30','identity':e,'package_hashes':hashes,'status':status,
                'source_key':key,'source_annotation':a,
                'source_context':[{'annotation':x,'alignment_verified':x['annotation_id'] in ids} for x in anns[max(0,i-1):i+3]],
                'following_source':{'status':ns,'annotation':n,'hypothesis':nh,'shape_candidates':context_roles(nh,key) if nh else None},
                'context_excerpt':ctx,'evidence':ev,'source_conditioned':True,'production_enabled':False,'training_eligible':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            cells=ev['surface']['slices'] if ev else []
            records.append({'case_id':cid,'score':folder.name,'measure':a['raw_fields'].get('mn'),
                'family':a['raw_fields']['special'],'label':a['raw_label'],'status':status,'json_sha256':digest(path),
                'vertical_supported':any(c['spelled_family_complete'] and c['supplied_bass_matches'] for c in cells),
                'enharmonic_only':any(c['enharmonic_only'] for c in cells),
                'union_complete':not ev['missing_spellings'] if ev else None,
                'joint_geometry_count':len(ev['joint_geometry']) if ev else 0,
                'goal_steps':sum(r['semitone_to_goal'] for r in ev['critical_paths']) if ev else 0,
                'following_status':ns})
    summary={'score_count':len(selected),'case_count':len(records),'families':dict(Counter(r['family'] for r in records)),
        'status_counts':dict(Counter(r['status'] for r in records)),
        'vertical_supported':sum(r['vertical_supported'] for r in records),'union_complete':sum(r['union_complete'] is True for r in records),
        'enharmonic_only_cases':sum(r['enharmonic_only'] for r in records),'joint_geometry':dict(pairs),
        'goal_steps':sum(r['goal_steps'] for r in records),'departure_statuses':dict(paths)}
    result={'version':VERSION,'summary':summary,'records':records,'skipped':dict(skipped),
        'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,
        'coverage_gaps':['French source examples','German43 spelling','nonstandard bass','non-dominant goals','enharmonic reinterpretation'],
        'production_enabled':False,'training_eligible':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.manifest,a.output)['summary'],indent=2))
