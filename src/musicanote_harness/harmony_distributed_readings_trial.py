"""Paired temporal/vertical coverage audit; no change to the selected analyzer."""
import argparse
from fractions import Fraction as F
import html
from pathlib import Path
import re
import shutil
from music21 import converter,pitch
from .formal_ir import q,FormalIRAdapter
from .canonical import CanonicalIRBuilder
from .harmony_joint import f
from .harmony_figure_trial import fixture_xml
from .harmony_arpeggio_benchmark import write,digest,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_shared_tone_review import observe as vertical
from .harmony_distributed_readings import observe,VERSION,WIDTHS

KINDS=('sequential_change','same_notes_seventh','common_start','root_pedal','silence')


def fixture(kind,tr=0,scale=F(1)):
    if kind not in KINDS:raise ValueError('unknown_kind')
    names=['C3','E3','G3','C3']+(['G3','B3','E3','G3'] if kind=='common_start' else ['E3','G3','B3','E3'])
    events=[{'pitch':pitch.Pitch(p).transpose(tr).nameWithOctave,'start':q(F(i,2)*scale),
             'duration':q((F(1,4) if kind=='silence' and i==3 else F(1,2))*scale),'voice':'1'} for i,p in enumerate(names)]
    if kind=='root_pedal':events.append({'pitch':pitch.Pitch('C2').transpose(tr).nameWithOctave,'start':q(0),'duration':q(4*scale),'voice':'2'})
    return {'kind':kind,'events':events,'duration':q(4*scale),'beat_type':int(4/scale),
            'scale':q(scale),'transpose':tr,'intended_boundary':q(2*scale),
            'boundary_review_expected':kind in KINDS[:3],
            'author_interpretation':kind,'oracle':'candidate_coverage_not_harmonic_gold'}


def verify_costs(result):
    for a in result['alternatives']:
        assert a['selected_hypothesis'] is None
        for key in ('merged_seventh','split_triads'):
            for path in a[key]:
                total=sum(sum(s['cost_parts'].values()) for s in path['segments'])+sum(path.get('transition_parts',{}).values())
                if abs(total-path['local_cost'])>1e-9:raise ValueError('cost_mismatch')
    audit=result['gate_audit']
    assert audit['window_pairs']==sum(audit['first_failed_gate'].values())+len(result['alternatives'])


def build(source,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    prior=load(source/'report.json');output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'source_report_sha256':digest(source/'report.json'),
        'widths_denominator_beats':[q(w) for w in WIDTHS],'kinds':KINDS,
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'production_modified':False,'source_labels_used':False})
    synthetic=[]
    def run_fixture(cid,case,folder,old=None):
        xml=folder/'score.musicxml'
        if old:
            for name in ('score.musicxml','canonical_music_ir.json','fixture.json'):shutil.copyfile(old/name,folder/name)
            ir=load(folder/'canonical_music_ir.json')
        else:
            xml.write_text(fixture_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(case,ir);write(folder/'canonical_music_ir.json',ir);write(folder/'fixture.json',case)
        before=vertical(ir);after=observe(ir);verify_costs(after)
        if old and before!=load(old/'review.json'):raise ValueError('vertical_refactor_changed_saved_result')
        if not old:
            found=any(a['boundary']==case['intended_boundary'] for a in after['alternatives'])
            if found!=case['boundary_review_expected']:raise ValueError('coverage_contract_failed')
        row={'case_id':cid,'kind':case['kind'],'scale':case['scale'],'transpose':case['transpose'],
             'vertical_count':len(before['alternatives']),'temporal_count':len(after['alternatives']),
             'distinct_boundary_count':len(after['boundary_groups']),
             'source_sha256':digest(xml),'ir_sha256':digest(folder/'canonical_music_ir.json')}
        write(folder/'comparison.json',{'vertical':before,'temporal':after});row['comparison_sha256']=digest(folder/'comparison.json');synthetic.append(row)
    for kind in KINDS:
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            cid=kind+'-'+name;folder=output/'synthetic'/cid;folder.mkdir(parents=True)
            run_fixture(cid,fixture(kind,tr,scale),folder)
    for item in prior['synthetic']:
        cid='prior-'+item['case_id'];old=source/'synthetic'/item['case_id'];folder=output/'synthetic'/cid;folder.mkdir(parents=True)
        if digest(old/'canonical_music_ir.json')!=item['ir_sha256'] or digest(old/'score.musicxml')!=item['source_sha256']:raise ValueError('prior_fixture_hash_mismatch')
        run_fixture(cid,load(old/'fixture.json'),folder,old)
    real=[]
    for item in prior['real']:
        cid=item['case_id'];old=source/'real-cases'/cid;folder=output/'real-cases'/cid;folder.mkdir(parents=True)
        provenance=load(old/'case-provenance.json');entry=provenance['manifest_entry']
        if any(provenance[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not entry['rights']['internal_research_use']:raise ValueError('ineligible_case')
        score_name=Path(entry['score_source_path']).name
        if digest(old/score_name)!=item['source_sha256'] or digest(old/'canonical_music_ir.json')!=item['ir_sha256']:raise ValueError('real_snapshot_mismatch')
        for name in (score_name,'canonical_music_ir.json','case-provenance.json','trial-results.json'):shutil.copyfile(old/name,folder/name)
        ir=load(folder/'canonical_music_ir.json');runs=[]
        for previous in load(old/'review.json')['runs']:
            span=previous['analysis_span'];result=observe(ir,span);verify_costs(result)
            runs.append({'analysis_span':span,'margin_quarters':previous['margin_quarters'],'vertical':previous['review'],'temporal':result})
        write(folder/'comparison.json',{'runs':runs})
        row={'case_id':cid,'collection':item['collection'],'vertical_counts':[len(r['vertical']['alternatives']) for r in runs],
             'temporal_counts':[len(r['temporal']['alternatives']) for r in runs],
             'boundary_counts':[len(r['temporal']['boundary_groups']) for r in runs],
             'gate_audits':[r['temporal']['gate_audit'] for r in runs],
             'source_sha256':digest(folder/score_name),'ir_sha256':digest(folder/'canonical_music_ir.json'),
             'comparison_sha256':digest(folder/'comparison.json'),'saved_paths_sha256':digest(folder/'trial-results.json')}
        if row['saved_paths_sha256']!=item['saved_paths_sha256']:raise ValueError('selected_paths_changed')
        real.append(row);print(cid,row['temporal_counts'],flush=True)
    report={'version':VERSION,'synthetic':synthetic,'real':real,'summary':{'synthetic_inputs':len(synthetic),'real_cases':len(real),
        'real_temporal_contexts':sum(sum(n>0 for n in r['temporal_counts']) for r in real),
        'real_temporal_candidates':sum(sum(r['temporal_counts']) for r in real),'selected_path_modified':False,'accuracy_measured':False}}
    write(output/'report.json',report);render(output);print(report['summary'],flush=True)


def render(root):
    import verovio
    report=load(root/'report.json');cards=[]
    titles={'sequential_change':'분산된 C→Em 후보','same_notes_seventh':'동일 음표 · Cmaj7 펼침 대안',
            'common_start':'공통음 시작 · 새 구성음의 늦은 등장','root_pedal':'근음 페달을 지우지 않는 대조','silence':'쉼을 가로질러 모으지 않는 대조'}
    for row in report['synthetic']:
        if row['case_id'].startswith('prior-') or not row['case_id'].endswith('-base'):continue
        folder=root/'synthetic'/row['case_id'];case=load(folder/'fixture.json');comparison=load(folder/'comparison.json')
        tk=verovio.toolkit();tk.setOptions({'inputFrom':'musicxml','breaks':'none','adjustPageWidth':True,'adjustPageHeight':True,'scale':50,'header':'none','footer':'none'})
        if not tk.loadFile(str(folder/'score.musicxml')):raise ValueError('render_failed')
        svg=tk.renderToSVG(1);size=re.search(r'<svg width="([0-9.]+)px" height="([0-9.]+)px"',svg)
        if size:svg=svg.replace('<svg ',f'<svg viewBox="0 0 {size[1]} {size[2]}" ',1)
        for i,e in enumerate(sorted(case['events'],key=lambda e:(e['voice'],f(e['start'])))):
            a,b=f(e['start']),f(e['start'])+f(e['duration']);color='#8e44ad' if a<2<b else '#1971c2' if a<2 else '#c05600'
            token=f'<g id="fixture_note_{i}" class="note">'
            if token not in svg:raise ValueError('fixture_note_render_missing')
            svg=svg.replace(token,token[:-1]+f' style="color:{color};fill:{color};stroke:{color}">')
        (folder/'score.svg').write_text(svg,encoding='utf-8')
        body='<section><h2>'+titles[row['kind']]+'</h2><div class="score">'+svg+'</div>'
        body+='<p>파랑=3박 이전, 주황=3박 이후, 보라=경계를 지나 지속되는 음. 확정 화성 구분이 아닙니다.</p>'
        options=[a for a in comparison['temporal']['alternatives'] if f(a['boundary'])==2]
        if options:
            a=max(options,key=lambda x:f(x['span']['end'])-f(x['span']['start']))
            body+='<p><strong>기존 수직 방식 후보 없음 → 시간 누적 방식은 두 해석 보존.</strong></p>'
            body+='<p>유지: '+html.escape(a['merged_seventh'][0]['segments'][0]['candidate']['label'])+' / 분리: '+html.escape(' → '.join(s['candidate']['label'] for s in a['split_triads'][0]['segments']))+'</p>'
            body+=f'<p>지역 비용: 유지 {a["merged_seventh"][0]["local_cost"]:.3f}, 분리 {a["split_triads"][0]["local_cost"]:.3f}. 새 구성음 지연 {float(f(a["entry_delay_quarters"])):g} quarter. 자동 선택 없음.</p>'
        else:body+='<p>3박 경계 후보를 만들지 않았습니다. 페달을 제외하거나 쉼을 메워서 화음을 만들지 않습니다.</p>'
        body+=f'<p>전체 검토 후보 {row["temporal_count"]}개 / 서로 다른 경계 위치 {row["distinct_boundary_count"]}개. 겹치는 창 수는 신뢰도가 아닙니다.</p><a href="synthetic/{row["case_id"]}/comparison.json">음표·범위·비용 전체</a></section>';cards.append(body)
    rows=''.join('<tr><td>'+html.escape(r['collection'])+'</td><td>'+str(r['temporal_counts'])+'</td><td><a href="real-cases/'+r['case_id']+'/comparison.json">근거</a></td></tr>' for r in report['real'])
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>분산 화음 · 시간 누적 후보 비교</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px;background:#f4f7fa;color:#173047}p{line-height:1.8}section{background:white;border:1px solid #ccd6df;margin:20px 0;padding:18px}.score{overflow:auto}.score svg{min-width:620px;width:100%;height:auto}td,th{padding:10px;border:1px solid #ccd6df}table{border-collapse:collapse}</style>'
    page+='<h1>수직 화음 없이도 분산된 구성음으로 비교</h1><p>1/2·1·2분모박의 앞뒤 창을 비교합니다. 두3화음과 단일7화음을 모두 보존하며 자동 정답으로 승격하지 않습니다. 첫 두 악보는 음표가 동일합니다. 절대 화음 이름이며 로마자 기능 분석이 아닙니다.</p>'+''.join(cards)
    page+='<h2>실제10사례 · 두 문맥의 후보 수</h2><table><tr><th>자료</th><th>시간 누적 후보 수</th><th>상세</th></tr>'+rows+'</table><p>후보 수 증가는 정확도 향상을 뜻하지 않습니다. 운영/기존 선택 결과는 변경하지 않았습니다.</p><a href="report.json">전체 보고서</a></html>'
    (root/'index.html').write_text(page,encoding='utf-8');write(root/'gallery-manifest.json',{'renderer_sha256':digest(Path(__file__)),'index_sha256':digest(root/'index.html'),'inference_rerun':False})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
