"""Frozen real-case rejection audit and figure evidence; no automatic correction."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET

from .harmony_arpeggio_benchmark import digest,write
from .harmony_boundary_ownership import review
from .harmony_figure_evidence import observe
from .harmony_joint import f
from .sonata_verification import verified_pages
from .harmony_visual_review import system_fragments

VERSION='ownership-diagnostic-review-0.1.0'
REASONS={
    'no_earlier_attack_within_measure_and_bound':'같은 마디·탐색 한도 안에 앞선 시작음이 없음',
    'prefix_outside_previous_chord':'앞부분 음고가 현재 선택된 앞 화음과 불일치',
    'lowest_not_attacked':'최저음이 새로 타격되지 않고 계속 울림',
    'completion_window_ends_before_new_evidence':'제한한 창 안에서 뒤 구성음까지 도달하지 못함',
    'shortened_previous_chord_incomplete':'앞 구간을 줄이면 기존 화음 구성음이 부족해짐',
    'no_new_pitch_class':'앞 화음 밖의 새로운 음고가 없음',
    'lowest_is_previous_root':'최저음이 앞 화음의 근음과 같음',
    'candidate_rejected_at_complete_lowest_root_shape':'최저음을 근음으로 한 완전 화음이 맞지 않음',
    'eligible':'앞선 시작음 후보가 있어 검사 진행',
}


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def check(path,expected):
    if digest(path)!=expected:raise ValueError('snapshot_changed:'+str(path))


def position(ir,value):
    t=f(value)
    ms=[m for m in ir['measures'] if f(m['global_start_quarter'])<=t]
    if not ms:return str(t)+' quarter'
    m=max(ms,key=lambda x:f(x['global_start_quarter']))
    from fractions import Fraction
    beat=1+(t-f(m['global_start_quarter']))/Fraction(4,m['time_signature']['beat_type'])
    return f"{m['printed_measure_number']}마디 {float(beat):g}박"


def render_case(folder,ir,source,runs):
    interesting=[(r,m) for r in runs for m in r['figure_evidence']['rhythmic_matches']
                 if m['weak_pitch_variation_compatible'] and m['split_by_selected_boundaries']]
    if not interesting:return None
    # The first observed qualifying pair, not a score/title exception.
    run,match=interesting[0]
    sounding={s['sounding_event_id']:s for s in ir['sounding_events']}
    groups={side:[n for ref in match[side]['event_refs'] for n in sounding[ref]['source_note_ids']]
            for side in ('earlier','later')}
    notes={n['note_id']:n for n in ir['note_events']}
    context={nid for nid,n in notes.items() if f(run['analysis_span']['start'])<=f(n['global_onset_quarter'])<f(run['analysis_span']['end'])}
    context.update(n for group in groups.values() for n in group)
    # Historical IR can have unmapped notes elsewhere in the work. Verify and
    # bind ONLY this displayed context; never claim whole-score alignment.
    context_ir={**ir,'note_events':[n for n in ir['note_events'] if n['note_id'] in context]}
    pages,mapping=verified_pages(source,context_ir)
    mapping.update(scope='displayed_context_only',full_score_alignment_claimed=False)
    fragments=system_fragments(pages,context)
    ET.register_namespace('','http://www.w3.org/2000/svg')
    markup=[]
    for fragment in fragments:
        root=ET.fromstring(fragment['svg'])
        for el in root.iter():
            nid=el.get('data-id') or el.get('id')
            for side,color in [('earlier','#1466b8'),('later','#b54c00')]:
                if nid in groups[side]:
                    el.set('style',f'color:{color};fill:{color};stroke:{color}')
                    for child in el.iter():child.set('color',color)
        markup.append('<div class="system">'+ET.tostring(root,encoding='unicode')+'</div>')
    paths=[]
    for r in runs:
        text=' → '.join(position(ir,s['span']['start'])+'〜'+position(ir,s['span']['end'])+'直前 '+s['selected']['label']
                       for s in r['selected_segments'])
        paths.append('<li>'+html.escape(r['frozen_arm']+' / 文脈 '+str(f(r['margin_quarters']))+': '+text)+'</li>')
    pair_text=' / '.join(side+': '+position(ir,match[side]['span']['start'])+'〜'+position(ir,match[side]['span']['end'])+' 직전'
                         for side in ('earlier','later'))
    css='body{font:16px system-ui;margin:24px;background:#f4f7fa;color:#172a3c}main{max-width:1300px;margin:auto}.system{background:white;margin:20px 0;padding:20px;overflow:auto}.system>svg{width:100%;min-width:750px;height:auto}p,li{line-height:1.7}'
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>실제 악보 반복 음형 진단</title><style>'+css+'</style><main><a href="../../index.html">전체 진단</a><h1>실제 악보: 반복 음형과 화음 경계</h1>'
    page+='<p>파랑과 주황은 같은 리듬·비슷한 음정 진행의 음형입니다. 같은 화음이라는 뜻은 아닙니다. 아래 표기는 기존 계산 결과이며 이번에 화음이나 경계를 변경하지 않았습니다.</p><p>'+html.escape(pair_text)+'</p>'
    page+=''.join(markup)+'<h2>기존 문맥·조건별 결과</h2><ul>'+''.join(paths)+'</ul>'
    page+='<p>baseline = 직전 분산 보완 끔 / experiment = 켬. 문맥 숫자는 검토 구간 앞뒤에 추가한 quarter 길이입니다. 음형 내부 경계는 검토 신호일 뿐 자동 병합 지시가 아닙니다.</p><a href="diagnostics.json">전후 상황·음표 ID·탈락 조건</a></main>'
    page=page.replace('直前',' 직전').replace('文脈','문맥')
    page+='''<script>for(const svg of document.querySelectorAll('.system>svg')){const g=svg.querySelector('.system');if(g){const b=g.getBBox(),m=svg.getScreenCTM().inverse().multiply(g.getScreenCTM());const pts=[[b.x,b.y],[b.x+b.width,b.y+b.height]].map(([x,y])=>{const p=svg.createSVGPoint();p.x=x;p.y=y;return p.matrixTransform(m)});const x=pts[0].x,y=pts[0].y,w=pts[1].x-x,h=pts[1].y-y;svg.setAttribute('viewBox',`${x-150} ${y-200} ${w+300} ${h+400}`);svg.removeAttribute('width');svg.removeAttribute('height');}}</script>'''
    (folder/'index.html').write_text(page,encoding='utf-8')
    write(folder/'render-validation.json',mapping)
    return {'path':str(folder.name)+'/index.html','match':match,'mapping':mapping}


def build(source,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    prior=load(source/'report.json')
    # Preserve the original cost engine; the diagnostic callback is new only.
    first=Path(prior['contract']['source_path'])
    for name,sha in load(first/'report.json')['contract']['code_sha256'].items():
        check(Path(__file__).parent/name,sha)
    output.mkdir(parents=True)
    contract={'version':VERSION,'source_path':str(source.resolve()),'source_report_sha256':digest(source/'report.json'),
              'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
              'selected_path_changed':False,'production_modified':False,'source_labels_used_for_inference':False}
    write(output/'run-contract.json',contract)
    synthetic_equal=0
    for row in prior['synthetic']:
        folder=source/row['case_id'];ir=load(folder/'canonical_music_ir.json')
        check(folder/'canonical_music_ir.json',row['ir_sha256'])
        check(folder/'results.json',row['baseline_results_sha256'])
        log=[];new=review(ir,load(folder/'results.json')['runs']['current'],diagnostics=log)
        if new!=load(folder/'ownership-review.json')['review']:raise ValueError('synthetic_output_changed')
        synthetic_equal+=1
    all_counts=Counter();summaries=[];total_runs=0
    for item in prior['real']:
        cid=item['case_id'];src=source/'real-cases'/cid;out=output/'real-cases'/cid
        provenance=load(src/'case-provenance.json');entry=provenance['manifest_entry'];plan=provenance['frozen_plan']
        if any(provenance[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not entry['rights']['internal_research_use']:
            raise ValueError('not_eligible_train_case')
        score_name=Path(entry['score_source_path']).name
        check(src/score_name,entry['score_sha256']);check(src/'canonical_music_ir.json',plan['ir_sha256'])
        check(src/'results.json',item['baseline_results_sha256'])
        out.mkdir(parents=True)
        for name in ('canonical_music_ir.json',score_name,'case-provenance.json','results.json'):
            shutil.copyfile(src/name,out/name)
        ir=load(src/'canonical_music_ir.json');old=load(src/'ownership-review.json')['runs'];runs=[];counts=Counter()
        for r in load(src/'results.json')['runs']:
            for arm in ('baseline','experiment'):
                logs=[];answer=review(ir,r[arm],diagnostics=logs)
                expected=next(x['review'] for x in old if x['margin_quarters']==r['margin_quarters'] and x['frozen_arm']==arm)
                if answer!=expected:raise ValueError('real_review_changed')
                boundaries=[s['span']['start'] for s in r[arm]['segments'][1:]]
                evidence=observe(ir,r['analysis_span'],boundaries)
                counts.update(x['kind']+':'+x['reason'] for x in logs)
                runs.append({'margin_quarters':r['margin_quarters'],'analysis_span':r['analysis_span'],'frozen_arm':arm,
                             'gates':logs,'figure_evidence':evidence,'selected_segments':r[arm]['segments']})
                total_runs+=1
        write(out/'diagnostics.json',{'case_id':cid,'first_failure_counts':dict(counts),'runs':runs})
        try:
            rendered=render_case(out,ir,out/score_name,runs)
            render_error=None
        except ValueError as exc:
            rendered=None;render_error=str(exc)
            write(out/'render-blocked.json',{'status':'blocked','reason':render_error})
        row={'case_id':cid,'collection':item['collection'],'first_failure_counts':dict(counts),
             'rhythmic_match_observations':sum(len(r['figure_evidence']['rhythmic_matches']) for r in runs),
             'runs_with_internal_compatible_figure_boundary':sum(any(m['weak_pitch_variation_compatible'] and m['split_by_selected_boundaries'] for m in r['figure_evidence']['rhythmic_matches']) for r in runs),
             'review_page':('real-cases/'+rendered['path']) if rendered else None,'render_error':render_error}
        summaries.append(row);all_counts.update(counts);print(cid,row['runs_with_internal_compatible_figure_boundary'],flush=True)
    report={'contract':contract,'synthetic_reviews_unchanged':synthetic_equal,'real_runs_unchanged':total_runs,
            'first_failure_counts':dict(all_counts),'cases':summaries,
            'count_warning':'first failing gate only; runs and overlapping windows are not independent music examples'}
    write(output/'report.json',report)
    table=''.join('<tr><td>'+html.escape(REASONS.get(k.split(':',1)[1],k))+'</td><td>'+str(n)+'</td></tr>' for k,n in all_counts.items())
    links=''.join('<li>'+html.escape(r['collection']+' · '+r['case_id'])+' · '+
                  (f'<a href="{r["review_page"]}">실제 악보에서 보기</a>' if r['review_page'] else '추가 검토 음형 없음')+'</li>' for r in summaries)
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>실제 악보 경계 진단</title><style>body{font:16px system-ui;max-width:1050px;margin:32px auto;padding:20px;color:#183047;background:#f6f8fb}td{padding:10px;border-bottom:1px solid #ddd}p,li{line-height:1.8}</style><h1>왜 실제 악보에서는 경계 대안이 나오지 않았나?</h1><p>고정10사례·40조건의 첫 탈락 조건입니다. 중복 문맥/조건이 포함되어 독립적인 오류 건수가 아닙니다. 경계 단계와 그 안의 시작음 후보 단계도 구별해야 합니다. 기존 선택은 모두 그대로 유지했습니다.</p><table>'+table+'</table><h2>반복 음형과 기존 경계 비교</h2><p>같은 리듬에 음정이 조금 변한 음형을 찾고, 그 중간에서 화음이 나뉜 경우를 검토 대상으로 표시했습니다. 반복이 같아도 화음은 바뀔 수 있습니다.</p><ul>'+links+'</ul><a href="report.json">보고서·정확한 단계 구분</a></html>'
    (output/'index.html').write_text(page,encoding='utf-8')
    print(dict(all_counts),flush=True)
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
