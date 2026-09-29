"""Frozen fixtures and real-context audit for shared-tone competing readings."""
import argparse
from fractions import Fraction as F
import html
import json
from pathlib import Path
import re
import shutil

from music21 import converter,pitch
from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter,q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import check_roundtrip,digest,write
from .harmony_figure_trial import fixture as prior_fixture,fixture_xml
from .harmony_shared_tone_review import observe,VERSION

KINDS=('shared_rearticulated','same_notes_seventh_reading','shared_sustained_common',
       'seventh_root_pedal','seventh_block','seventh_arpeggio','disjoint_change')
TITLES=('두3화음 교체로 작성한 예','동일 음표: 7화음 펼침이라는 대안 해석',
        '공통음 지속 + 바깥 구성음 교체','근음 페달 위의7화음',
        '완전7화음 재타격','한 음씩 펼친7화음','공통음 없는 명확한 교체')


def fixture(kind,transpose=0,scale=F(1)):
    if kind not in KINDS:raise ValueError('unknown_kind')
    case=prior_fixture('change_inside_cell_shared_seventh_union')
    if kind=='disjoint_change':case=prior_fixture('change_inside_cell_disjoint')
    events=case['events']
    def add(p,a,d,v):events.append({'pitch':p,'start':q(a),'duration':q(d),'voice':v})
    if kind=='seventh_root_pedal':add('C2',0,4,'3')
    elif kind=='shared_sustained_common':
        events=[]
        for i in range(4):
            add('C3',i,F(1,2),'1');add('B3',F(i)+F(1,2),F(1,2),'1')
            add('E3',i,1,'2');add('G3',i,1,'3')
    elif kind=='seventh_block':
        events=[]
        for i in range(4):
            for p in ('C3','E3','G3','B3'):add(p,i,1,'1')
    elif kind=='seventh_arpeggio':
        events=[]
        for i in range(4):
            for j,p in enumerate(('C3','E3','G3','B3')):add(p,F(i)+F(j,4),F(1,4),'1')
    events=[{**e,'pitch':pitch.Pitch(e['pitch']).transpose(transpose).nameWithOctave,
             'start':q(f(e['start'])*scale),'duration':q(f(e['duration'])*scale)} for e in events]
    return {'kind':kind,'events':events,'duration':q(4*scale),'beat_type':int(4/scale),
            'scale':q(scale),'transpose':transpose,
            'author_interpretation':('seventh_prolongation_possible' if kind=='same_notes_seventh_reading' else kind),
            'expected_review_candidates':7 if kind in KINDS[:3] else 0,
            'oracle':'candidate_coverage_not_harmonic_gold'}


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def build(source,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    prior=load(source/'report.json')
    output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'source_path':str(source.resolve()),
        'source_report_sha256':digest(source/'report.json'),'kinds':KINDS,
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'min_block_duration_denominator_beats':'1/2','production_modified':False,
        'source_labels_used_for_inference':False,'previous_selected_paths_recalculated':False})
    synthetic=[]
    for kind in KINDS:
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            cid=kind+'-'+name;folder=output/'synthetic'/cid;folder.mkdir(parents=True)
            c=fixture(kind,tr,scale);xml=folder/'score.musicxml';xml.write_text(fixture_xml(c),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(c,ir);write(folder/'canonical_music_ir.json',ir);write(folder/'fixture.json',c)
            result=observe(ir);write(folder/'review.json',result)
            if len(result['alternatives'])!=c['expected_review_candidates']:raise ValueError('fixture_coverage_mismatch')
            row={'case_id':cid,'kind':kind,'transform':name,'candidate_count':len(result['alternatives']),
                 'source_sha256':digest(xml),'ir_sha256':digest(folder/'canonical_music_ir.json'),
                 'review_sha256':digest(folder/'review.json')}
            synthetic.append(row)
    real=[]
    for item in prior['real']:
        cid=item['case_id'];src=source/'real-cases'/cid;folder=output/'real-cases'/cid;folder.mkdir(parents=True)
        provenance=load(src/'case-provenance.json');entry=provenance['manifest_entry'];plan=provenance['frozen_plan']
        if any(provenance[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not entry['rights']['internal_research_use']:
            raise ValueError('ineligible_case')
        score_name=Path(entry['score_source_path']).name
        if digest(src/score_name)!=entry['score_sha256'] or digest(src/'canonical_music_ir.json')!=plan['ir_sha256']:
            raise ValueError('source_snapshot_mismatch')
        for name in (score_name,'canonical_music_ir.json','case-provenance.json','trial-results.json'):
            shutil.copyfile(src/name,folder/name)
        ir=load(folder/'canonical_music_ir.json');runs=[]
        for old in load(folder/'trial-results.json')['runs']:
            review=observe(ir,old['analysis_span'])
            for alt in review['alternatives']:
                t=f(alt['boundary'])
                alt['existing_path_boundary']={arm:any(f(s['span']['start'])==t for s in old[arm]['segments'][1:]) for arm in ('off','on')}
            runs.append({'analysis_span':old['analysis_span'],'margin_quarters':old['margin_quarters'],'review':review})
        write(folder/'review.json',{'runs':runs})
        row={'case_id':cid,'collection':item['collection'],'candidate_counts':[len(r['review']['alternatives']) for r in runs],
             'gate_audits':[r['review']['gate_audit'] for r in runs],
             'source_sha256':digest(folder/score_name),'ir_sha256':digest(folder/'canonical_music_ir.json'),
             'saved_paths_sha256':digest(folder/'trial-results.json'),'review_sha256':digest(folder/'review.json')}
        if row['saved_paths_sha256']!=digest(src/'trial-results.json'):raise ValueError('selected_paths_changed')
        real.append(row);print(cid,row['candidate_counts'],flush=True)
    report={'version':VERSION,'synthetic':synthetic,'real':real,
            'summary':{'synthetic_inputs':len(synthetic),'real_cases':len(real),
                       'real_candidate_contexts':sum(sum(n>0 for n in r['candidate_counts']) for r in real),
                       'real_candidate_occurrences':sum(sum(r['candidate_counts']) for r in real),
                       'selected_paths_changed':False,'accuracy_measured':False}}
    write(output/'report.json',report);render(output);print(report['summary'],flush=True)
    return report


def render(root):
    """Saved observations only; absolute chord names, no Roman-function claim."""
    import verovio
    report=load(root/'report.json');cards=[]
    for row in report['synthetic']:
        if row['transform']!='base':continue
        folder=root/'synthetic'/row['case_id'];review=load(folder/'review.json')
        tk=verovio.toolkit();tk.setOptions({'inputFrom':'musicxml','breaks':'none','adjustPageWidth':True,
            'adjustPageHeight':True,'scale':50,'header':'none','footer':'none'})
        if not tk.loadFile(str(folder/'score.musicxml')):raise ValueError('render_failed')
        svg=tk.renderToSVG(1);size=re.search(r'<svg width="([0-9.]+)px" height="([0-9.]+)px"',svg)
        if size:svg=svg.replace('<svg ',f'<svg viewBox="0 0 {size[1]} {size[2]}" ',1)
        if review['alternatives']:
            c=review['alternatives'][0];a,t,b=f(c['span']['start']),f(c['boundary']),f(c['span']['end'])
            events=sorted(load(folder/'fixture.json')['events'],key=lambda e:(e['voice'],f(e['start'])))
            for i,e in enumerate(events):
                x,y=f(e['start']),f(e['start'])+f(e['duration'])
                if x>=b or y<=a:continue
                color='#8e44ad' if x<t<y else '#1971c2' if x<t else '#c05600'
                token=f'<g id="fixture_note_{i}" class="note">'
                if token not in svg:raise ValueError('fixture_render_note_missing')
                svg=svg.replace(token,token[:-1]+f' style="color:{color};fill:{color};stroke:{color}">')
        (folder/'score.svg').write_text(svg,encoding='utf-8')
        body='<section><h2>'+TITLES[KINDS.index(row['kind'])]+'</h2><div class="score">'+svg+'</div>'
        if review['alternatives']:
            first=review['alternatives'][0];merge=first['merged_seventh'][0];split=first['split_triads'][0]
            def labels(path):return ' → '.join(s['candidate']['label'] for s in path['segments'])
            body+=f'<p>경계 후보 {len(review["alternatives"])}개 중 첫 경계(1마디 1.5박) 비교. 서로 겹치는 검토 창입니다.</p>'
            body+='<p>첫 비교 구간: <span style="color:#1971c2">파랑=앞 음군</span>, <span style="color:#c05600">주황=뒤 음군</span>, <span style="color:#8e44ad">보라=경계를 지나 지속되는 음</span>. 색칠은 화성 확정 판정이 아닙니다.</p>'
            body+='<table><tr><th>유지 가설</th><th>분리 가설</th></tr><tr><td>'+html.escape(labels(merge))+'</td><td>'+html.escape(labels(split))+'</td></tr>'
            body+=f'<tr><td>지역 비용 {merge["local_cost"]:.3f}</td><td>지역 비용 {split["local_cost"]:.3f}</td></tr></table>'
            parts=split['transition_parts'];body+=f'<p>분리에는 추가 구간 비용 0.150과 화음 교체 비용 {parts["label_change"]:.3f}가 들어갑니다. 베이스 MIDI {first["bass"]["before_midi"]}→{first["bass"]["after_midi"]}; 지속 공통음 {len(first["sustained_common_event_refs"])}개.</p>'
            body+='<p><strong>자동 선택하지 않음.</strong> 비용이 낮다고 음악적으로 옳다는 뜻은 아닙니다. 조성·성부 역할·앞뒤 해결을 더 확인해야 합니다.</p>'
        else:body+='<p>이 규칙의 두 완전3화음 교체 조건에 해당하지 않습니다. 분석 성공 또는 화음 유지의 확정 판정이 아닙니다.</p>'
        body+=f'<a href="synthetic/{row["case_id"]}/review.json">음표 근거와 비용 전체</a></section>';cards.append(body)
    realrows=''.join('<tr><td>'+html.escape(r['collection'])+'</td><td>'+str(r['candidate_counts'])+'</td><td><a href="real-cases/'+r['case_id']+'/review.json">근거</a></td></tr>' for r in report['real'])
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>공통음 화음 교체 · 복수 해석</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px;background:#f3f6fa;color:#173047}p{line-height:1.8}section{background:white;padding:18px;border:1px solid #cbd7e0;margin:22px 0}.score{overflow:auto}.score svg{min-width:680px;width:100%;height:auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd7e0;padding:9px;text-align:left}</style>'
    page+='<h1>하나의7화음인가, 두3화음의 교체인가?</h1><p>기존 자동 선택을 바꾸지 않고 두 해석과 비용·음표 근거를 보존하는 연구용 단계입니다. 첫 두 악보는 음표가 같습니다. 설명만 달리해도 다른 결과를 내는 규칙을 만들지 않았습니다. 화음 표기는 절대 이름이며 로마자 기능 분석이 아닙니다.</p>'+''.join(cards)
    page+='<h2>고정 실제10사례 · 두 문맥</h2><p>숫자는 각 문맥에서 발견된 검토 후보 수입니다. 겹치는 후보/문맥을 독립 사례로 세지 않습니다. 기존 선택 결과는 사본 hash로 불변 확인했습니다.</p><table><tr><th>자료</th><th>후보 수</th><th>상세</th></tr>'+realrows+'</table><p><a href="report.json">전체 보고서</a></p></html>'
    (root/'index.html').write_text(page,encoding='utf-8')
    write(root/'gallery-manifest.json',{'renderer_sha256':digest(Path(__file__)),'index_sha256':digest(root/'index.html'),'inference_rerun':False})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
