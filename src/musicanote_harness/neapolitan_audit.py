"""Train-only Unit29 source-conditioned audit; preserves unsupported bII cases."""
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
from .neapolitan_evidence import VERSION, source_reference, observe, compare_context


def build(manifest_path, output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    names=['neapolitan_evidence.py','neapolitan_audit.py','diatonic_modulation.py','applied_chords.py',
        'seventh_context.py','cadential_six_four_audit.py','harmony_case_retrieval.py','harmony_review_cohort.py',
        'harmony_review_supplement.py','foundation_sonata_audit.py','predominant_sonata_audit.py',
        'dominant_area_evidence.py','formal_ir.py','tonal_foundations.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
        'selection':'all raw bII/N labels in train 12 sonatas; strict triad adapter or explicit abstention',
        'context':'one measure before/after plus original adjacent annotations; no skipping unknown rows',
        'source_conditioned':True,'training_eligible':False,'production_enabled':False,
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];skipped=Counter();tags=Counter();statuses=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p=load_prepared_package(folder);ir=p['ir'];anns=p['annotations']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e);skipped.update(rejected);ids={a['annotation_id'] for a in valid}
        for i,a in enumerate(anns):
            if a['raw_fields'].get('numeral') not in ('bII','N'):continue
            key=source_key(a);h=source_reference(a,key);ctx=None;ev=None;context=None
            status='unverified_alignment' if a['annotation_id'] not in ids else 'unsupported_source_chord' if h is None else 'observed'
            if a['annotation_id'] in ids:ctx=context_excerpt(ir,a['target']['span'])
            if status=='observed':
                ev=observe(ir,a['target']['span'],ctx['context_span'],key,h['inversion'])
                rs=[]
                for n in anns[max(0,i-1):i+5]:
                    nk=source_key(n);verified=n['annotation_id'] in ids
                    rs.append({'ref':n['annotation_id'],'key':nk,'verified':verified,'span':n['target']['span'],
                        'hypothesis':source_harmony(n,*nk) if nk and verified else None})
                context=compare_context(rs,key)
                tags.update(t for path in ev['flat2_paths'] for t in path['geometry_tags'])
                statuses.update(path['departure_status'] for path in ev['flat2_paths'])
            else:skipped[status]+=1
            cid='u29_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            case={'case_id':cid,'concept_id':'hvl.unit29','identity':e,'package_hashes':hashes,'status':status,
                'source_key':key,'source_annotation':a,'source_context':anns[max(0,i-1):i+5],
                'context_excerpt':ctx,'evidence':ev,'harmonic_context':context,
                'source_conditioned':True,'production_enabled':False,'training_eligible':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            records.append({'case_id':cid,'score':folder.name,'measure':a['raw_fields'].get('mn'),
                'label':a['raw_label'],'status':status,'json_sha256':digest(path),
                'vertical_supported':bool(ev and ev['literal_support']['complete_vertical_matches']),
                'union_complete':not ev['literal_support']['missing_spellings'] if ev else None,
                'context_paths':len(context['compatible_paths']) if context else None})
    summary={'score_count':len(selected),'case_count':len(records),'status_counts':dict(Counter(r['status'] for r in records)),
        'vertical_supported':sum(r['vertical_supported'] for r in records),'union_complete':sum(r['union_complete'] is True for r in records),
        'geometry_tags':dict(tags),'departure_statuses':dict(statuses)}
    result={'version':VERSION,'summary':summary,'records':records,'skipped':dict(skipped),
        'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,
        'coverage_gaps':['major key','root and second inversion','tonicized/pivot/neighbor bII','enharmonic notation','apparent bII65'],
        'production_enabled':False,'training_eligible':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.manifest,a.output)['summary'],indent=2))
