"""Frozen evidence contrast trial with explicit synthetic positive/negative controls."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
from pathlib import Path
import re
import shutil
from xml.etree import ElementTree as ET
from music21 import converter,pitch
from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter,q
from .harmony_joint import f
from .harmony_figure_trial import fixture_xml
from .harmony_arpeggio_benchmark import write,digest,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_distributed_readings import observe
from .harmony_reading_voice_context import compare as voice_compare
from .harmony_reading_contrast import compare,VERSION

KINDS=('shared','merged','split','none')
STATUS={'shared_between_families':'양쪽 공통 지지 · 구별 근거 아님',
 'merged_seventh_only_conditional_support':'7화음 가설에만 조건부 지지 · 승자 확정 아님',
 'split_triads_only_conditional_support':'분리 가설에만 조건부 지지 · 승자 확정 아님',
 'no_conditional_support':'해결 지지 미확인 · 양쪽 모두 반증 아님',
 'incomplete_comparison':'비교 누락 · 판단 보류'}


def fixture(kind,tr=0,scale=F(1)):
    if kind not in KINDS:raise ValueError('unknown_fixture')
    if kind=='split':names=['B2','D3','F#3','B2','D3','F#3','A3','D3','G3','B3','D4','G3'];upper=('F#4','G4')
    elif kind=='shared':names=['C3','E3','G3','C3','E3','G3','B-3','E3','F3','A3','C4','F3'];upper=('E4','F4')
    else:names=['C3','E3','G3','C3','E3','G3','B3','E3' if kind=='merged' else 'G3','F3','A3','C4','F3'];upper=('B4','A4') if kind=='merged' else ('G4','A4')
    specs=[(p,F(i,2),F(1,2),'1') for i,p in enumerate(names)]+[(upper[0],F(7,2),F(1,2),'2'),(upper[1],F(4),F(2),'2')]
    return {'kind':kind,'events':[{'pitch':pitch.Pitch(p).transpose(tr).nameWithOctave,'start':q(a*scale),'duration':q(d*scale),'voice':v} for p,a,d,v in specs],
        'scale':q(scale),'transpose':tr,'duration':q(6*scale),'beat_type':int(4/scale),
        'oracle':'conditional_evidence_coverage_not_harmonic_gold'}


def panel(records):
    content=[]
    for r in records:
        rows=[]
        for e in r['evidence_units']:
            if e['status']=='no_conditional_support':continue
            m=e['motion'];name=' → '.join(m[k]['spelling'].replace('-','♭') for k in ('source_pitch','target_pitch'))
            rows.append('<tr><td>'+html.escape(name)+'</td><td>'+STATUS[e['status']]+'</td><td>'+html.escape(e['external_candidate']['label'] if e['external_candidate'] else '내부 연결')+'</td></tr>')
        labels='<p>'+ '<br>'.join(('유지: ' if p['reading_type']=='merged_seventh' else '분리: ')+html.escape(' → '.join(p['labels'])) for p in r['readings'])+'</p>'
        bass=r['boundary_observations']['bass']
        facts='<p>최저음 MIDI '+str(bass['before_midi'])+' → '+str(bass['after_midi'])+' / 새 구성음 지연 '+str(f(r['boundary_observations']['entry_delay_beats']))+'분모박. 이 관측은 후보 생성 때 이미 사용했으므로 추가 지지표로 중복 가산하지 않습니다.</p>'
        content.append(labels+'<table>'+(''.join(rows) or '<tr><td>현재 검사한 직접 해결에서는 구별 근거 미확인. 오답이라는 뜻은 아닙니다.</td></tr>')+'</table>'+facts)
    return '<section id="evidence-contrast"><h2>이번 단계: 공통 지지와 구별 근거</h2>'+''.join(content)+'<p>같은 음 연결을 서로 다른 역할로 설명하거나 겹치는 창에서 다시 찾더라도 독립 투표로 세지 않습니다. 한쪽만 조건부 지지가 있어도 다른 해석을 배제하지 않습니다. 화음 선택·비용·기능 확정은 그대로입니다.</p><a href="evidence-contrast.json">전체 근거 대조</a></section>'


def counts(records):
    c=Counter(e['status'] for r in records for e in r['evidence_units'])
    return {'candidate_occurrences':len(records),'status_occurrences':dict(c),
        'with_family_differentiating_support':sum(r['has_family_differentiating_support'] for r in records),
        'overlapping_candidates_not_independent':True}


def build(source,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    prior=load(source/'report.json');output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'source_report_sha256':digest(source/'report.json'),
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'fixture_kinds':KINDS,
        'selection_or_weights_changed':False,'source_annotations_used':False,'production_modified':False})
    report={'version':VERSION,'synthetic':[],'real':[],'controls':[]};all_records={'synthetic':[],'real':[]}
    for group,dirname in [('synthetic','synthetic'),('real','real-cases')]:
        for row in prior[group]:
            src=source/dirname/row['case_id'];dst=output/dirname/row['case_id']
            for name,key in [('canonical_music_ir.json','ir_sha256'),('comparison.json','comparison_sha256'),('voice-context.json','voice_context_sha256')]:
                if digest(src/name)!=row[key]:raise ValueError('frozen_input_mismatch')
            if group=='real':
                prov=load(src/'case-provenance.json')
                if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible_case')
                if digest(src/'trial-results.json')!=row['saved_paths_sha256']:raise ValueError('selected_path_mismatch')
                score_name=Path(prov['manifest_entry']['score_source_path']).name
            else:score_name='score.musicxml'
            if digest(src/score_name)!=row['source_sha256']:raise ValueError('score_hash_mismatch')
            shutil.copytree(src,dst)
            original=load(dst/'comparison.json');voices=load(dst/'voice-context.json')['records']
            candidates=([a for run in original['runs'] for a in run['temporal']['alternatives']] if group=='real' else original['temporal']['alternatives'])
            if len(candidates)!=len(voices):raise ValueError('candidate_count_mismatch')
            records=[compare(c,v) for c,v in zip(candidates,voices)];all_records[group]+=records
            write(dst/'evidence-contrast.json',{'records':records,'summary':counts(records)})
            updated={**row,'contrast_summary':counts(records),'contrast_sha256':digest(dst/'evidence-contrast.json')}
            if row.get('review_page'):
                # Match the prior gallery's deterministic first eligible candidate;
                # other contextual windows remain in JSON, not this score overlay.
                page=(dst/'index.html').read_text(encoding='utf-8').replace('</main>',panel(records[:1])+'</main>')
                (dst/'index.html').write_text(page,encoding='utf-8');updated['html_sha256']=digest(dst/'index.html')
            report[group].append(updated)
    import verovio
    cards=[]
    for kind in KINDS:
        for variant,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            cid=kind+'-'+variant;dst=output/'controls'/cid;dst.mkdir(parents=True);case=fixture(kind,tr,scale)
            xml=ET.fromstring(fixture_xml(case));xml.find('.//time/beats').text='6'
            path=dst/'score.musicxml';path.write_text(ET.tostring(xml,encoding='unicode',xml_declaration=True),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(path),path),path)
            check_roundtrip(case,ir);write(dst/'canonical_music_ir.json',ir);write(dst/'fixture.json',case)
            candidate=next(c for c in observe(ir)['alternatives'] if c['span']=={'start':q(0),'end':q(4*scale)} and c['boundary']==q(2*scale))
            voice=voice_compare(ir,candidate);result=compare(candidate,voice)
            expected={'merged':'merged_seventh_only_conditional_support','split':'split_triads_only_conditional_support','shared':'shared_between_families','none':'no_conditional_support'}[kind]
            statuses={e['status'] for e in result['evidence_units']}
            if expected not in statuses or result['has_family_differentiating_support']!=(kind in ('merged','split')):raise ValueError('control_expectation_failed:'+cid)
            write(dst/'comparison.json',candidate);write(dst/'voice-context.json',voice);write(dst/'evidence-contrast.json',result)
            row={'case_id':cid,'expected_evidence':expected,'observed_statuses':sorted(statuses),
                'files_sha256':{p.name:digest(p) for p in dst.iterdir() if p.is_file()}}
            tk=verovio.toolkit();tk.setOptions({'inputFrom':'musicxml','breaks':'none','adjustPageWidth':True,'adjustPageHeight':True,'scale':45,'header':'none','footer':'none'})
            if not tk.loadFile(str(path)):raise ValueError('render_failed')
            svg=tk.renderToSVG(1);size=re.search(r'<svg width="([0-9.]+)px" height="([0-9.]+)px"',svg)
            if size:svg=svg.replace('<svg ',f'<svg viewBox="0 0 {size[1]} {size[2]}" ',1)
            for i,e in enumerate(sorted(case['events'],key=lambda e:(e['voice'],f(e['start'])))):
                color='#1971c2' if f(e['start'])<2*scale else '#c05600' if f(e['start'])<4*scale else '#087f5b'
                token=f'<g id="fixture_note_{i}" class="note">'
                if token not in svg:raise ValueError('note_render_missing')
                svg=svg.replace(token,token[:-1]+f' style="color:{color};fill:{color};stroke:{color}">')
            (dst/'score.svg').write_text(svg,encoding='utf-8')
            page=header('대조 악보 · '+kind)+'<p>파랑=앞 관찰 창, 주황=뒤 관찰 창, 초록=뒤 문맥. 작곡 의도의 정답이 아니라 증거 분류 테스트입니다.</p><div class="score">'+svg+'</div>'+panel([result])+'</body></html>'
            (dst/'index.html').write_text(page,encoding='utf-8')
            row['files_sha256'].update({n:digest(dst/n) for n in ('score.svg','index.html')});report['controls'].append(row)
            if variant=='base':cards.append('<li><a href="controls/'+cid+'/index.html">'+STATUS[expected]+'</a></li>')
    report['summary']={group:counts(records) for group,records in all_records.items()};report['summary'].update(controls_passed=len(report['controls']),accuracy_measured=False)
    write(output/'report.json',report)
    links=''.join('<li><a href="'+r['review_page']+'">'+html.escape(r['collection']+' · '+r['case_id'])+'</a></li>' for r in report['real'] if r.get('review_page'))
    page=header('공통 근거와 구별 근거 검토')+'<p>양쪽 모두 설명하는 근거를 반복 가산하지 않습니다. 한쪽만 조건부 지지가 있어도 자동 승자를 정하지 않습니다. 원주석/프레이즈/운영 분석은 바뀌지 않았습니다.</p><h2>네 가지 대조 악보</h2><ul>'+''.join(cards)+'</ul><h2>실제 악보</h2><ul>'+links+'</ul><p>실제 겹치는 후보13개에서 한쪽만 지지하는 직접 해결은 '+str(report['summary']['real']['with_family_differentiating_support'])+'개입니다. 정확도 수치가 아닙니다.</p><a href="report.json">전체 보고서</a></body></html>'
    (output/'index.html').write_text(page,encoding='utf-8');print(report['summary'])


def header(title):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:16px system-ui;max-width:1200px;margin:24px auto;padding:16px;color:#173047;background:#f4f7fa}p,li{line-height:1.8}section{padding:18px;background:white;margin:20px 0}.score{overflow:auto;background:white}.score svg{width:100%;min-width:750px;height:auto}td{padding:10px;border:1px solid #ccd6df}table{border-collapse:collapse}</style><body><h1>'+html.escape(title)+'</h1>'


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
