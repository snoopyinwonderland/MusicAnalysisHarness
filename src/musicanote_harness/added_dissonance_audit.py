"""Unit28 train-only audit, preserving original modifiers and absent base tones."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .dominant_area_evidence import _exact
from .added_dissonance import VERSION, source_reference, observe


def build(manifest_path,output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    names=['added_dissonance.py','added_dissonance_audit.py','applied_chords.py','seventh_context.py',
        'cadential_six_four_audit.py','harmony_case_retrieval.py','harmony_review_cohort.py',
        'harmony_review_supplement.py','foundation_sonata_audit.py','predominant_sonata_audit.py',
        'dominant_area_evidence.py','formal_ir.py','tonal_foundations.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
        'selection':'verified V Mm7 reference spans with observed 9/4/6 classes OR any source changes/added_tones; no pedal/special/nested target',
        'source_modifiers':'retained verbatim; hypothetical V7 anchor is NOT complete source chord or confirmed harmony',
        'context':'source span plus one measure before and after; original adjacent source neighbor only',
        'source_conditioned':True,'production_enabled':False,'training_eligible':False,
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];scores=[];skipped=Counter();roles=Counter();statuses=Counter();alternatives=Counter();examined=0
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p=load_prepared_package(folder);ir=p['ir'];anns=p['annotations']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e);skipped.update(rejected);ids={a['annotation_id'] for a in valid};count=0
        for i,a in enumerate(anns):
            if a['annotation_id'] not in ids:continue
            key=source_key(a);reference=source_reference(a,key)
            if reference is None:
                if a['raw_fields'].get('numeral')=='V' and a['raw_fields'].get('chord_type')=='Mm7':skipped['unsupported_reference']+=1
                continue
            examined+=1;span=a['target']['span'];ctx=context_excerpt(ir,span)
            ev=observe(ir,span,ctx['context_span'],reference['base'])
            extra=[r for r in ev['paths'] if r['role']!='seventh']
            modified=any(a['raw_fields'].get(k) for k in ('changes','added_tones'))
            if not extra and not modified:skipped['no_added_class_or_source_modifier']+=1;continue
            n=anns[i+1] if i+1<len(anns) else None;nr=None
            if n is None:status='absent'
            elif n['annotation_id'] not in ids:status='unverified'
            elif source_key(n)!=key:status='changed_source_key'
            elif _exact(n['target']['span']['start'])!=_exact(span['end']):status='nonadjacent'
            else:nr=source_reference(n,key);status='supported_reference' if nr else 'not_supported_dominant_reference'
            next_info={'status':status,'annotation':n,'base_reference':nr,
                'same_root_and_quality':nr['base']['members']==reference['base']['members'] if nr else None,
                'same_full_harmony':None}
            cid='u28_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            case={'case_id':cid,'concept_id':'hvl.unit28','identity':e,'package_hashes':hashes,
                'source_annotation':a,'source_key':key,'reference':reference,'following_source':next_info,
                'source_context':[{'annotation':x,'alignment_verified':x['annotation_id'] in ids} for x in anns[max(0,i-1):i+3]],
                'context_excerpt':ctx,'evidence':ev,'source_conditioned':True,'training_eligible':False,'production_enabled':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            rs=Counter(x['role'] for x in extra);st=Counter(x['departure_status'] for x in extra)
            al=set(t for cell in ev['slices'] for t in cell['alternative_shape_candidates'])
            roles.update(rs);statuses.update(st);alternatives.update(al);count+=1
            records.append({'case_id':cid,'score':folder.name,'printed_measure':a['raw_fields'].get('mn'),
                'source_label':a['raw_label'],'source_modified':modified,'roles':dict(rs),'departure_status':dict(st),
                'alternative_shapes':sorted(al),'same_following_reference':next_info['same_root_and_quality'],
                'inside_target_steps':sum(x['arrives_at_reference_target_spelling'] and x['departure_position']=='inside_supplied_span' for x in extra),
                'outside_target_steps':sum(x['arrives_at_reference_target_spelling'] and x['departure_position']=='at_or_after_supplied_end' for x in extra),
                'root_then_seventh':sum(x['root_then_seventh_geometry'] for x in extra),'json_sha256':digest(path)})
        scores.append({'score':folder.name,'case_count':count,'package_hashes':hashes})
    summary={'score_count':len(scores),'examined_references':examined,'case_count':len(records),
        'source_modified_cases':sum(r['source_modified'] for r in records),'observed_roles':dict(roles),
        'departure_statuses':dict(statuses),'case_alternative_shapes':dict(alternatives),
        'inside_target_steps':sum(r['inside_target_steps'] for r in records),
        'outside_target_steps':sum(r['outside_target_steps'] for r in records),
        'root_then_seventh':sum(r['root_then_seventh'] for r in records),
        'same_following_reference':sum(r['same_following_reference'] is True for r in records)}
    result={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
        'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,
        'training_eligible':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.manifest,a.output)['summary'],indent=2))
