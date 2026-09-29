"""Score-linked review of saved temporal alternatives, never source-label inference."""
import html
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from .formal_ir import q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_ownership_diagnostic_review import position
from .sonata_verification import verified_pages
from .harmony_visual_review import system_fragments


def render(root):
    report=load(root/'report.json');index=[]
    ET.register_namespace('','http://www.w3.org/2000/svg')
    for row in report['real']:
        if not any(row['temporal_counts']):continue
        folder=root/'real-cases'/row['case_id'];ir=load(folder/'canonical_music_ir.json')
        runs=load(folder/'comparison.json')['runs'];run=next(r for r in runs if r['temporal']['alternatives'])
        # First qualifying window in first eligible frozen context; no label-based selection.
        candidate=run['temporal']['alternatives'][0];a,t,b=f(candidate['span']['start']),f(candidate['boundary']),f(candidate['span']['end'])
        notes={n['note_id']:n for n in ir['note_events']};sounding={s['sounding_event_id']:s for s in ir['sounding_events']}
        groups={'left':set(),'right':set()}
        for ref in candidate['event_refs']:
            s=sounding[ref]
            for side,x,y in [('left',a,t),('right',t,b)]:
                if not f(s['span']['start'])<y or not f(s['span']['end'])>x:continue
                for nid in s['source_note_ids']:
                    n=notes[nid];onset=f(n['global_onset_quarter']);duration=f(n['notated_duration_quarter'])
                    if onset<y and onset+duration>x:groups[side].add(nid)
        context={nid for nid,n in notes.items() if f(run['analysis_span']['start'])<=f(n['global_onset_quarter'])<f(run['analysis_span']['end'])}
        context.update(groups['left']|groups['right'])
        subset={**ir,'note_events':[n for n in ir['note_events'] if n['note_id'] in context]}
        entry=load(folder/'case-provenance.json')['manifest_entry'];source=folder/Path(entry['score_source_path']).name
        try:pages,mapping=verified_pages(source,subset)
        except ValueError as exc:
            index.append({'case_id':row['case_id'],'status':'render_blocked','reason':str(exc)});continue
        mapping.update(scope='displayed_context_only',full_score_alignment_claimed=False)
        write(folder/'render-validation.json',mapping)
        markup=[]
        for fragment in system_fragments(pages,context):
            svg=ET.fromstring(fragment['svg'])
            for el in svg.iter():
                nid=el.get('data-id') or el.get('id')
                sides=[s for s in groups if nid in groups[s]]
                if not sides:continue
                color='#8e44ad' if len(sides)==2 else '#1971c2' if sides[0]=='left' else '#c05600'
                el.set('data-window-side',' '.join(sides));el.set('style',f'color:{color};fill:{color};stroke:{color}')
                for child in el.iter():child.set('color',color)
            markup.append('<div class="system">'+ET.tostring(svg,encoding='unicode')+'</div>')
        merge=candidate['merged_seventh'][0];split=candidate['split_triads'][0]
        labels={'merged':merge['segments'][0]['candidate']['label'],
                'left':split['segments'][0]['candidate']['label'],'right':split['segments'][1]['candidate']['label']}
        bounds=position(ir,q(a))+'부터 '+position(ir,q(b))+' 직전 / 분리 후보 '+position(ir,q(t))
        page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>실제 분산 화음 복수 해석</title><style>body{font:16px system-ui;margin:24px;background:#f4f7fa;color:#173047}main{max-width:1300px;margin:auto}.system{background:white;overflow:auto;padding:12px;margin:20px 0}.system>svg{width:100%;min-width:950px;height:auto}p{line-height:1.8}td{padding:10px;border:1px solid #ccd6df}table{border-collapse:collapse}</style><main><a href="../../index.html">목록</a><h1>실제 악보 · 시간 누적 화음 후보</h1>'
        page+='<p>'+html.escape(bounds)+'</p><p>파랑=앞 관찰 창, 주황=뒤 관찰 창, 보라=양쪽에 지속되는 기보 음표. 위의 두 줄은 유지/분리 가설이며 확정 분석이 아닙니다. 절대 화음 이름을 사용합니다.</p>'
        page+=''.join(markup)
        page+='<table><tr><td>유지 가설</td><td>'+html.escape(labels['merged'])+f'</td><td>{merge["local_cost"]:.3f}</td></tr><tr><td>분리 가설</td><td>'+html.escape(labels['left']+' → '+labels['right'])+f'</td><td>{split["local_cost"]:.3f}</td></tr></table>'
        band=candidate['boundary_support_band']
        page+='<p>이전 고유 구성음의 release: '+position(ir,band['start'])+' / 새 고유 구성음의 첫 attack: '+position(ir,band['end'])+f'. 분리 후보부터 새 구성음까지 {float(f(candidate["entry_delay_quarters"])):g} quarter 지연. 이 사이를 모두 확인된 화음 경계라고 해석하지 않습니다.</p>'
        page+='<p>지역 비용이며 외부 문맥 transition은 포함하지 않습니다. 자동 선택/운영 화면/원주석은 변경하지 않았습니다. 원XML 대응은 표시 context만 검증했습니다.</p><a href="comparison.json">전체 후보·음표 ID·비용</a></main>'
        page+='<script>const labels='+json.dumps(labels,ensure_ascii=False)+';'
        page+='''
const ns='http://www.w3.org/2000/svg';
for(const svg of document.querySelectorAll('.system>svg')){
 const g=svg.querySelector('.system');if(!g)continue;
 const transform=svg.getScreenCTM().inverse().multiply(g.getScreenCTM());
 function point(x,y,m){const p=svg.createSVGPoint();p.x=x;p.y=y;return p.matrixTransform(m)}
 function box(el){const b=el.getBBox(),m=svg.getScreenCTM().inverse().multiply(el.getScreenCTM());const p=point(b.x,b.y,m),z=point(b.x+b.width,b.y+b.height,m);return{x:p.x,y:p.y,w:z.x-p.x,h:z.y-p.y}}
 const bounds=box(g);svg.setAttribute('viewBox',`${bounds.x-160} ${bounds.y-1000} ${bounds.w+320} ${bounds.h+1250}`);svg.removeAttribute('width');svg.removeAttribute('height');
 const groupBoxes={};
 for(const side of ['left','right']){const bs=[...svg.querySelectorAll(`[data-window-side~="${side}"]`)].map(box);if(bs.length)groupBoxes[side]={a:Math.min(...bs.map(b=>b.x)),b:Math.max(...bs.map(b=>b.x+b.w))}}
 const all=Object.values(groupBoxes);if(!all.length)continue;
 function short(label){return label.replace(':half-diminished7','ø7').replace(':diminished7','dim7').replace(':diminished','dim').replace(':dominant7','7').replace(':major7','maj7').replace(':minor7','m7').replace(':major','maj').replace(':minor','min')}
 function bracket(a,b,y,label,color){const line=document.createElementNS(ns,'path');line.setAttribute('d',`M ${a} ${y+45} V ${y} H ${b} V ${y+45}`);line.setAttribute('fill','none');line.setAttribute('stroke',color);line.setAttribute('stroke-width','16');svg.appendChild(line);const text=document.createElementNS(ns,'text');text.setAttribute('x',b);text.setAttribute('y',y-35);text.setAttribute('text-anchor','end');text.setAttribute('font-size','230');text.setAttribute('font-family','system-ui');text.setAttribute('fill',color);text.textContent=label;svg.appendChild(text)}
 bracket(Math.min(...all.map(b=>b.a)),Math.max(...all.map(b=>b.b)),bounds.y-600,'유지 '+short(labels.merged),'#475569');
 for(const [side,c] of [['left','#1971c2'],['right','#c05600']]){const b=groupBoxes[side];if(b)bracket(b.a,b.b,bounds.y-160,'분리 '+short(labels[side]),c)}
}
</script>'''
        (folder/'index.html').write_text(page,encoding='utf-8')
        index.append({'case_id':row['case_id'],'status':'rendered','candidate_ref':candidate['evidence_id'],
            'page':'real-cases/'+row['case_id']+'/index.html','html_sha256':digest(folder/'index.html')})
    write(root/'real-gallery.json',{'renderer_sha256':digest(Path(__file__)),'cases':index})
    p=root/'index.html';page=p.read_text(encoding='utf-8')
    page=re.sub(r'<div id="real-cases-links">.*?</div>','',page,flags=re.S)
    links='<div id="real-cases-links"><h2>실제 악보에서 두 해석 비교</h2><ul>'+''.join('<li><a href="'+r['page']+'">'+html.escape(next(x['collection'] for x in report['real'] if x['case_id']==r['case_id']))+' · '+r['case_id']+'</a></li>' for r in index if r['status']=='rendered')+'</ul></div>'
    p.write_text(page.replace('<h2>실제10사례',links+'<h2>실제10사례'),encoding='utf-8')
    manifest=load(root/'gallery-manifest.json');manifest.update(index_sha256=digest(p),real_renderer_sha256=digest(Path(__file__)))
    write(root/'gallery-manifest.json',manifest)
    print(index)


if __name__=='__main__':
    import sys
    render(Path(sys.argv[1]))
