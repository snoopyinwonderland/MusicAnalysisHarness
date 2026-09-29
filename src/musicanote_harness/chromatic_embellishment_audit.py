"""Unit31 source-conditioned train audit with negative common-tone comparisons."""
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
from .dominant_area_evidence import _exact
from .diatonic_modulation import observe_support
from .chromatic_embellishment import (VERSION, mixture_routes, augmented_source,
    observe_augmented, observe_common_tone)


def build(manifest_path,output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    names=['chromatic_embellishment.py','chromatic_embellishment_audit.py','augmented_sixth.py',
        'diatonic_modulation.py','applied_chords.py','seventh_context.py','cadential_six_four_audit.py',
        'harmony_case_retrieval.py','harmony_review_cohort.py','harmony_review_supplement.py',
        'foundation_sonata_audit.py','predominant_sonata_audit.py','dominant_area_evidence.py',
        'formal_ir.py','tonal_foundations.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
        'selection':'all augmented triads, selected major-mode mixture shapes, all raw o7 records (including nonmatching/unsupported following context)',
        'context':'one measure before/after; original next annotation, never skip unknown or changed keys',
        'source_conditioned':True,'production_enabled':False,'training_eligible':False,
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in names}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];skipped=Counter();types=Counter();geometries=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        p=load_prepared_package(folder);ir=p['ir'];anns=p['annotations']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(p,e);skipped.update(rejected);ids={a['annotation_id'] for a in valid}
        for i,a in enumerate(anns):
            key=source_key(a);h=source_harmony(a,*key);routes=mixture_routes(h,key);raw_type=a['raw_fields'].get('chord_type')
            kind='augmented' if raw_type=='+' else 'diminished7_comparison' if raw_type=='o7' else 'mixture' if routes else None
            if kind is None:continue
            n=anns[i+1] if i+1<len(anns) else None;nh=None
            if a['annotation_id'] not in ids:ns='current_unverified'
            elif n is None:ns='absent'
            elif n['annotation_id'] not in ids:ns='next_unverified'
            elif source_key(n)!=key:ns='changed_key'
            elif _exact(n['target']['span']['start'])!=_exact(a['target']['span']['end']):ns='nonadjacent'
            else:nh=source_harmony(n,*key);ns='supported' if nh else 'unsupported'
            ctx=context_excerpt(ir,a['target']['span']) if a['annotation_id'] in ids else None
            ev=None;status='observed'
            if ctx is None:status='unverified_alignment'
            elif kind=='augmented':
                h=augmented_source(a,key)
                if h:ev=observe_augmented(ir,a['target']['span'],ctx['context_span'],h)
                else:status='unsupported_augmented_source'
            elif kind=='mixture':ev={'routes':routes,'literal_support':observe_support(ir,a['target']['span'],h),'mixture_confirmed':None}
            elif h is None:status='unsupported_diminished_source'
            elif ns!='supported' or nh['quality'] not in ('M','m','Mm7'):status='unsupported_following_context'
            elif _exact(ctx['context_span']['end'])<=_exact(a['target']['span']['end']):status='following_context_censored'
            else:ev=observe_common_tone(ir,a['target']['span'],n['target']['span'],ctx['context_span'],h,nh)
            if status!='observed':skipped[status]+=1
            cid='u31_'+hashlib.sha256((ir['ir_document_id']+'|'+a['annotation_id']).encode()).hexdigest()[:16]
            case={'case_id':cid,'concept_id':'hvl.unit31','kind':kind,'identity':e,'package_hashes':hashes,
                'source_key':key,'source_annotation':a,'status':status,'context_excerpt':ctx,'evidence':ev,
                'source_context':[{'annotation':x,'alignment_verified':x['annotation_id'] in ids} for x in anns[max(0,i-1):i+3]],
                'following_source':{'status':ns,'annotation':n,'hypothesis':nh},
                'source_conditioned':True,'production_enabled':False,'training_eligible':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            tags=[t for pth in ev['fifth_paths']['paths'] for t in pth['geometry_tags']] if ev and kind=='augmented' else []
            geometries.update(tags);types.update(r['name'] for r in routes)
            records.append({'case_id':cid,'score':folder.name,'measure':a['raw_fields'].get('mn'),'label':a['raw_label'],
                'kind':kind,'status':status,'json_sha256':digest(path),'geometry_tags':tags,
                'common_tone_pc_candidate':ev['comparison']['pitch_class_shape_match'] if ev and kind=='diminished7_comparison' else None,
                'common_root_links':len(ev['common_root_links']) if ev and kind=='diminished7_comparison' else 0,
                'target_steps':sum(pth['step_into_supplied_target_span'] for pth in ev['voice_paths']['paths']) if ev and kind=='diminished7_comparison' else 0})
    summary={'score_count':len(selected),'case_count':len(records),'kinds':dict(Counter(r['kind'] for r in records)),
        'status_counts':dict(Counter(r['status'] for r in records)),'mixture_shape_routes':dict(types),'augmented_geometry':dict(geometries),
        'common_tone_pc_candidates':sum(r['common_tone_pc_candidate'] is True for r in records),
        'common_root_links':sum(r['common_root_links'] for r in records),'target_steps':sum(r['target_steps'] for r in records)}
    result={'version':VERSION,'summary':summary,'records':records,'skipped':dict(skipped),
        'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,
        'production_enabled':False,'training_eligible':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.manifest,a.output)['summary'],indent=2))
