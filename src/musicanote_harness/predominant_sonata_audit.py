"""Train-only, source-conditioned Unit 10 audit; NOT blind harmony accuracy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from music21 import pitch
from .formal_ir import q
from .harmony_case_retrieval import _f, load_prepared_package
from .foundation_sonata_audit import pitch_tuple
from .harmony_curriculum import same_span
from .predominant_evidence import assess_transition


def span_observation(ir, span):
    """Exact [start,end) sweep, includes held notes; no annotation labels read."""
    a,b = _f(span['start']),_f(span['end'])
    if a >= b:
        raise ValueError('positive_span_required')
    events = []
    ids = set()
    for s in ir['sounding_events']:
        x,y = _f(s['span']['start']),_f(s['span']['end'])
        if y < x:
            raise ValueError('negative_event_duration')
        if x == y or x >= b or y <= a:
            continue
        eid = s['sounding_event_id']
        if eid in ids:
            raise ValueError('duplicate_sounding_id')
        ids.add(eid)
        events.append((x,y,{'event_id':eid,'pitch':list(pitch_tuple(s))}))
    points = sorted({a,b,*[max(a,x) for x,y,r in events],*[min(b,y) for x,y,r in events]})
    return {'span':span,'slices':[{'span':{'start':q(x),'end':q(y)},
            'events':[r for on,off,r in events if on<=x<off]}
            for x,y in zip(points,points[1:])],
            'union_events':[r for x,y,r in events],
            'held_at_start_ids':[r['event_id'] for x,y,r in events if x<a<y]}


def compare_spans(ir, left, right, labels, tonic, alter=0, mode='major'):
    if _f(left['end']) != _f(right['start']):
        raise ValueError('adjacent_spans_required')
    a,b=span_observation(ir,left),span_observation(ir,right)
    def assess(x,y):
        return assess_transition(x,y,labels,tonic,alter,mode) if x and y else None
    return {'before':a,'after':b,
            'boundary_snapshot_evidence':assess(a['slices'][-1]['events'],b['slices'][0]['events']),
            # Union is not a vertical chord, and minimum pitch is not the onset bass.
            'span_union_diagnostic':assess(a['union_events'],b['union_events']),
            'union_is_simultaneous':False,'automatic_harmony_accuracy_measured':False}


def source_candidate(a):
    r=a['raw_fields']
    if any(r.get(k) for k in ('changes','added_tones','special','relativeroot','pedal')):
        return None
    if r.get('localkey') not in ('I','i'):
        return None
    label=r.get('numeral','')+r.get('form','')+r.get('figbass','')
    label={'V2':'V42'}.get(label,label)
    mode='minor' if r.get('globalkey_is_minor')=='1' else 'major'
    supported = ('iv','iio','iio6') if mode=='minor' else ('IV','ii','ii6')
    if label not in (*supported,'V','V6','V7','V65','V43','V42'):
        return None
    return label,r['globalkey'],mode


def build(manifest_path, output):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    records=[]; errors=[]; skipped=Counter(); scores=[]
    for e in manifest['entries']:
        if e['split']!='train' or e['collection_id'] not in ('mozart-sonatas','beethoven-sonatas'):
            continue
        try:
            package=load_prepared_package(e['package_path']); ir=package['ir']
            if (ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']
                or hashlib.sha256(Path(e['score_source_path']).read_bytes()).hexdigest()!=e['score_sha256']):
                raise ValueError('source_identity_mismatch')
            aligns={}
            for row in package['alignments']:
                aligns.setdefault(row['annotation_id'],[]).append(row)
            valid=[]
            for a in package['annotations']:
                t=a.get('target') or {}; links=aligns.get(a['annotation_id'],[])
                if (a.get('source_asset_sha256')!=e['annotation_sha256'] or
                    t.get('score_id')!=e['score_id'] or t.get('ir_document_id')!=e['ir_document_id'] or
                    not t.get('span') or len(links)!=1 or
                    links[0]['mapping_status'] not in ('exact','verified_transform') or
                    not same_span(links[0]['target']['span'],t['span'])):
                    skipped['unverified_annotation']+=1; continue
                valid.append(a)
            valid.sort(key=lambda a:(_f(a['target']['span']['start']),a['annotation_id']))
            count=0
            for a,b in zip(valid,valid[1:]):
                ca,cb=source_candidate(a),source_candidate(b)
                if not ca or not cb or ca[1:]!=cb[1:]:
                    skipped['outside_supported_context']+=1;continue
                if ca[0] not in ('IV','iv','ii','ii6','iio','iio6'):
                    continue
                if _f(a['target']['span']['end'])!=_f(b['target']['span']['start']):
                    skipped['nonadjacent']+=1;continue
                tonic=pitch.Pitch(ca[1].replace('b','-'))
                observation=compare_spans(ir,a['target']['span'],b['target']['span'],
                        [ca[0],cb[0]],tonic.step,int(tonic.accidental.alter) if tonic.accidental else 0,ca[2])
                records.append({'collection':e['collection_id'],'score':Path(e['package_path']).name,
                    'score_id':e['score_id'],'ir_document_id':e['ir_document_id'],
                    'score_sha256':e['score_sha256'],'annotation_sha256':e['annotation_sha256'],
                    'source_refs':[{'annotation_id':x['annotation_id'],'locator':x['source_locator'],
                        'label':x['raw_label'],'measure':x['raw_fields'].get('mn')} for x in (a,b)],
                    'key_and_ranges_from_source':True,'split':'train','observation':observation})
                count+=1
            scores.append({'collection':e['collection_id'],'score':Path(e['package_path']).name,'pairs':count})
        except (ValueError,KeyError,TypeError,OSError) as exc:
            errors.append({'package':e['package_path'],'error':str(exc)})
    stats={}
    for c in ('mozart-sonatas','beethoven-sonatas'):
        group=[r['observation'] for r in records if r['collection']==c]
        stats[c]={'pairs':len(group),'right_span_has_held_notes':sum(bool(r['after']['held_at_start_ids']) for r in group)}
        for field in ('boundary_snapshot_evidence','span_union_diagnostic'):
            stats[c][field+'_supported']=sum(bool(r[field] and all(o['complete_spelled_support'] for o in r[field]['observations'])) for r in group)
    report={'version':'predominant-sonata-audit-0.1.0','scores':scores,'stats':stats,
            'skipped':dict(skipped),'errors':errors,'production_enabled':False,
            'policy':'train; source-conditioned ranges/key/candidates; union is not vertical; no accuracy claim',
            'manifest_sha256':hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()}
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'records.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(build(args.manifest,args.output),ensure_ascii=False,indent=2))
