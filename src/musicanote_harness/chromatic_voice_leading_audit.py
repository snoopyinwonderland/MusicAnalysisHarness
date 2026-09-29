"""Unit32 annotation-independent score geometry and separately linked sources."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations,context_excerpt
from .dominant_area_evidence import _exact
from .formal_ir import q
from .chromatic_voice_leading import VERSION,observe


def context_annotations(annotations,verified_ids,span):
    a,b=(_exact(span[k]) for k in ('start','end'))
    result=[]
    for x in annotations:
        s=(x.get('target') or {}).get('span')
        if s and _exact(s['start'])<b and _exact(s['end'])>a:
            result.append({'annotation':x,'alignment_verified':x['annotation_id'] in verified_ids})
    return result


def build(manifest_path,output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    entries=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in entries})!=len(entries):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in entries):raise ValueError('research_not_permitted')
    names=['chromatic_voice_leading.py','chromatic_voice_leading_audit.py','cadential_six_four_audit.py',
        'harmony_case_retrieval.py','harmony_review_cohort.py','harmony_review_supplement.py',
        'dominant_area_evidence.py','formal_ir.py','foundation_sonata_audit.py','tonal_foundations.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':entries,
        'selection':'all literal run and strict synchronized pair geometries; no annotation/key selection',
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in names},'production_enabled':False,'training_eligible':False}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];scores=[];excluded=Counter()
    for e in entries:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        package=load_prepared_package(folder);ir=package['ir']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        valid,rejected=verified_annotations(package,e);excluded.update(rejected);ids={x['annotation_id'] for x in valid}
        end=max(_exact(m['global_start_quarter'])+_exact(m['actual_duration_quarter']) for m in ir['measures'])
        ev=observe(ir,{'start':q(0),'end':q(end)})
        fullpath=out/(folder.name+'-geometry.json');fullpath.write_text(json.dumps(ev,ensure_ascii=False,indent=2),encoding='utf-8')
        scores.append({'score':folder.name,'identity':e,'package_hashes':hashes,'geometry_path':fullpath.name,'geometry_sha256':digest(fullpath),
            'line_count':len(ev['lines']),'pair_count':len(ev['pairs']),
            'grace_pending':len(ev['diagnostics']['grace_events_pending_role']),
            'ambiguous_events':len(ev['diagnostics']['ambiguous_voice_event_ids'])})
        for g in ev['lines']+ev['pairs']:
            events=g.get('events',g.get('lower_events',[])+g.get('upper_events',[]))
            identity='|'.join([ir['ir_document_id'],g['pattern'],*[x['event_id'] for x in events]])
            cid='u32_'+hashlib.sha256(identity.encode()).hexdigest()[:16];ctx=context_excerpt(ir,g['span'])
            a,b=(_exact(ctx['context_span'][k]) for k in ('start','end'))
            annotations=context_annotations(package['annotations'],ids,ctx['context_span'])
            # context_excerpt deliberately omits zero-length grace; retain the
            # detector's explicit pending-grace records alongside the excerpt.
            graces=[x for x in ev['diagnostics']['grace_events_pending_role'] if a<=_exact(x['span']['start'])<b]
            case={'case_id':cid,'concept_id':'hvl.unit32','identity':e,'package_hashes':hashes,
                'evidence':g,'context_excerpt':ctx,'grace_pending_context':graces,'source_context':annotations,
                'source_annotations_used_for_detection':False,'production_enabled':False,'training_eligible':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            records.append({'case_id':cid,'score':folder.name,'pattern':g['pattern'],'span':g['span'],
                'json_sha256':digest(path),'event_count':len(events),'complete_octave_windows':len(g.get('complete_octave_windows',[]))})
    report={'version':VERSION,'scores':scores,'records':records,'excluded_annotations':dict(excluded),
        'summary':{'score_count':len(scores),'case_count':len(records),'patterns':dict(Counter(x['pattern'] for x in records)),
            'complete_octave_windows':sum(x['complete_octave_windows'] for x in records),
            'grace_events_pending':sum(x['grace_pending'] for x in scores),'ambiguous_voice_events':sum(x['ambiguous_events'] for x in scores)},
        'contract_sha256':digest(out/'run-contract.json'),'blind_harmony_accuracy_measured':False,'production_enabled':False,'training_eligible':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.manifest,a.output)['summary'],indent=2))
