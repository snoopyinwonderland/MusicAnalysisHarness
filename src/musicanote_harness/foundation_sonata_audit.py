"""Train-only sonata stress audit of observed triadic shapes, not harmony accuracy."""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import html
import json
from pathlib import Path

from .formal_ir import q
from .harmony_case_retrieval import _f, load_prepared_package
from .harmony_curriculum import QUALITIES, same_span
from .tonal_foundations import spelled_triad_shapes

VERSION = 'foundation-sonata-audit-0.1.0'


def pitch_tuple(sound):
    p = sound['pitch']
    alter = _f(p['alter'])
    if alter.denominator != 1:
        raise ValueError('microtonal_not_supported')
    expected = 12*(p['octave']+1) + {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[p['step']] + int(alter)
    if p.get('midi_pitch') != expected:
        raise ValueError('pitch_spelling_midi_mismatch')
    return p['step'], int(alter), p['octave']


def inspect_span(ir, span):
    a,b = _f(span['start']),_f(span['end'])
    if b <= a:
        raise ValueError('nonpositive_span')
    notes = {n['note_id']:n for n in ir['note_events']}
    rows = [(s,_f(s['span']['start']),_f(s['span']['end'])) for s in ir['sounding_events']
            if _f(s['span']['start'])<b and _f(s['span']['end'])>a]
    if not rows:
        raise ValueError('no_pitched_events')
    points = sorted({a,b,*[max(a,x) for _,x,y in rows],*[min(b,y) for _,x,y in rows]})
    slices=[]
    for x,y in zip(points,points[1:]):
        active=[s for s,on,off in rows if on<=x<off]
        shapes=spelled_triad_shapes([pitch_tuple(s) for s in active])
        slices.append({'start':q(x),'end':q(y),'shapes':shapes,
                       'event_ids':[s['sounding_event_id'] for s in active]})
    union=spelled_triad_shapes([pitch_tuple(s) for s,_,_ in rows])
    voices={notes[n]['voice_id'] for s,_,_ in rows for n in s['source_note_ids'] if n in notes}
    density=float(Fraction(sum(a<=x<b for _,x,_ in rows),1)/(b-a))
    maximum=max(len(s['event_ids']) for s in slices)
    # Observable ranking proxy, never a musical-quality/difficulty claim.
    complexity=density+len(voices)+maximum
    return {'union_shapes':union,'slices':slices,'voice_count':len(voices),
            'attack_density_per_quarter':density,'max_simultaneous_events':maximum,
            'complexity_proxy':complexity,'event_count':len(rows),
            'note_ids':sorted({n for s,_,_ in rows for n in s['source_note_ids']}),
            'span':span}


def compare(annotation, observation):
    raw=annotation['raw_fields']
    quality=QUALITIES[raw['chord_type']]
    inversion={'':0,'6':1,'64':2}[raw.get('figbass','')]
    duration=sum((_f(s['end'])-_f(s['start']) for s in observation['slices']),Fraction())
    shape_time=sum((_f(s['end'])-_f(s['start']) for s in observation['slices'] if s['shapes']),Fraction())
    agree_time=sum((_f(s['end'])-_f(s['start']) for s in observation['slices']
                    if any(c['quality']==quality and c['inversion']==inversion for c in s['shapes'])),Fraction())
    return {'source_quality':quality,'source_inversion':inversion,
            'complete_shape_duration_ratio':float(shape_time/duration),
            'quality_inversion_agreement_duration_ratio':float(agree_time/duration),
            'root_compared':False,'harmonic_accuracy_measured':False,
            'union_quality_agrees':any(c['quality']==quality for c in observation['union_shapes'])}


def write_review(entry, ir, rows, destination):
    from .engraving import render_musicxml_pages
    pages,mapping=render_musicxml_pages(entry['score_source_path'],ir)
    # Incomplete traceability disables highlighting rather than pointing to wrong notes.
    enabled=mapping['complete']
    payload=json.dumps([{'id':r['annotation_id'],'notes':r['observation']['note_ids'],
                         'label':r['source_label'],'comparison':r['comparison'],
                         'span':r['observation']['span'],'measure':r['printed_measure'],
                         'complexity':r['observation']['complexity_proxy']} for r in rows],ensure_ascii=False).replace('<','\\u003c')
    title=html.escape(entry['collection_id']+' / '+Path(entry['package_path']).name)
    page='''<!doctype html><meta charset="utf-8"><title>3화음 기초 검증</title>
<style>body{font:16px system-ui;margin:0;display:grid;grid-template-columns:minmax(0,1fr) 380px;background:#f4f5f7}main{padding:35px}aside{position:sticky;top:0;height:100vh;overflow:auto;background:white;padding:16px;box-sizing:border-box}.page{background:white;margin:20px 0}.page svg{width:100%;height:auto}button{display:block;text-align:left;margin:8px 0;padding:12px;width:100%;cursor:pointer}g.note.focus{fill:#d35400!important;stroke:#d35400!important}pre{white-space:pre-wrap;font-size:13px}.notice{padding:16px;background:#fff2c7}</style>
<main><h1>'''+title+'''</h1><div class="notice">원자료 주석과 표면 음집합 비교 · 자동 화성 정답 아님 · train 진단 · 목록 클릭 시 구간 음표 표시</div>'''+''.join('<div class="page">'+p+'</div>' for p in pages)+'''</main><aside><h2>복잡도 상위 검토 구간</h2><p>전위 모양이 같아도 실제 화성 기능은 다를 수 있습니다.</p><div id="list"></div><pre id="detail"></pre></aside>
<script>const rows='''+payload+''', enabled='''+json.dumps(enabled)+''';
for(const r of rows){const b=document.createElement('button');b.textContent=`마디 ${r.measure} · 원주석 ${r.label} · 관찰 복잡도 ${r.complexity.toFixed(2)}`;b.onclick=()=>{document.querySelectorAll('.focus').forEach(e=>e.classList.remove('focus'));document.getElementById('detail').textContent=JSON.stringify(r,null,2)+(enabled?'':' — 음표 연결 검증 미통과: 강조 비활성');if(enabled){let first;for(const id of r.notes){for(const e of document.querySelectorAll(`[data-id="${id}"], [id="${id}"]`)){e.classList.add('focus');first ||= e;}}first?.scrollIntoView({block:'center',behavior:'smooth'});}};document.getElementById('list').append(b);}
</script>'''
    destination.write_text(page,encoding='utf-8')
    return mapping


def build(manifest_path, output, render=False):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    records=[];errors=[];skips=Counter();summaries=[];ranked={}
    for entry in manifest['entries']:
        collection=entry['collection_id']
        if collection not in ('mozart-sonatas','beethoven-sonatas') or entry['split']!='train':
            continue
        package=load_prepared_package(entry['package_path']);ir=package['ir']
        if ir['ir_document_id']!=entry['ir_document_id'] or ir['score']['score_id']!=entry['score_id']:
            errors.append({'package':entry['package_path'],'error':'identity_mismatch'});continue
        actual=hashlib.sha256(Path(entry['score_source_path']).read_bytes()).hexdigest()
        if actual!=entry['score_sha256']:
            errors.append({'package':entry['package_path'],'error':'source_hash_mismatch'});continue
        if any(a.get('source_asset_sha256')!=entry['annotation_sha256'] for a in package['annotations']):
            errors.append({'package':entry['package_path'],'error':'annotation_hash_identity_mismatch'});continue
        aligned={}
        for a in package['alignments']:aligned.setdefault(a['annotation_id'],[]).append(a)
        score_rows=[]
        for annotation in package['annotations']:
            raw=annotation.get('raw_fields',{})
            if raw.get('chord_type') not in QUALITIES or raw.get('figbass','') not in ('','6','64') or any(raw.get(k) for k in ('changes','added_tones','special')):
                skips['non_basic_triad']+=1;continue
            target=annotation.get('target',{})
            alignment=aligned.get(annotation['annotation_id'],[])
            if len(alignment)!=1 or alignment[0]['mapping_status'] not in ('exact','verified_transform') or target.get('score_id')!=ir['score']['score_id'] or target.get('ir_document_id')!=ir['ir_document_id'] or not target.get('span') or not same_span(alignment[0]['target']['span'],target['span']):
                skips['alignment_not_verified']+=1;continue
            try:
                observation=inspect_span(ir,target['span'])
                record={'annotation_id':annotation['annotation_id'],'collection':collection,
                        'package':entry['package_path'],'source_label':annotation['raw_label'],
                        'printed_measure':raw.get('mn'),'source_locator':annotation['source_locator'],
                        'source_asset_sha256':annotation['source_asset_sha256'],
                        'score_sha256':actual,'ir_document_id':ir['ir_document_id'],
                        'identity':{k:entry[k] for k in ('work_family_id','split','annotation_lineage_id')},
                        'observation':observation,'comparison':compare(annotation,observation)}
                score_rows.append(record)
            except (ValueError,KeyError,TypeError) as exc:
                errors.append({'annotation_id':annotation['annotation_id'],'error':str(exc)})
        records.extend(score_rows)
        summaries.append({'collection':collection,'score':Path(entry['package_path']).name,'spans':len(score_rows)})
        # Choose each composer's most dense/polyphonic sampled span without labels in ranking.
        if score_rows:
            ordered=sorted(score_rows,key=lambda r:(-r['observation']['complexity_proxy'],r['annotation_id']))
            if collection not in ranked or ordered[0]['observation']['complexity_proxy']>ranked[collection][0]:
                ranked[collection]=(ordered[0]['observation']['complexity_proxy'],entry,ordered[:8])
    reviews=[]
    if render:
        for collection,(_,entry,rows) in ranked.items():
            ir=json.loads((Path(entry['package_path'])/'canonical_music_ir.json').read_text(encoding='utf-8'))
            dest=out/(collection+'-review.html')
            mapping=write_review(entry,ir,rows,dest)
            reviews.append({'path':str(dest.resolve()),'score':Path(entry['package_path']).name,
                            'mapping':mapping,'selected_annotations':[r['annotation_id'] for r in rows]})
    stats={}
    for collection in ('beethoven-sonatas','mozart-sonatas'):
        group=[r for r in records if r['collection']==collection]
        stats[collection]={'spans':len(group),'union_complete':sum(bool(r['observation']['union_shapes']) for r in group),
                           'no_complete_vertical_shape':sum(r['comparison']['complete_shape_duration_ratio']==0 for r in group),
                           'qualities':dict(Counter(r['comparison']['source_quality'] for r in group))}
    report={'version':VERSION,'scores':summaries,'stats':stats,'skipped':dict(skips),'errors':errors,
            'reviews':reviews,'manifest_sha256':hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
            'policy':'train_only; source-defined spans; no root/function accuracy claim; no production changes'}
    (out/'records.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);p.add_argument('--render',action='store_true')
    args=p.parse_args();r=build(args.manifest,args.output,args.render)
    print(json.dumps({k:v for k,v in r.items() if k!='reviews'},ensure_ascii=False,indent=2))
