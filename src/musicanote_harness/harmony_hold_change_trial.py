"""Preserve frozen gates and contrast all their hold/change alternatives."""
import argparse
from collections import Counter
import html
from pathlib import Path
import re
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_hold_change_contrast import compare,VERSION
from .harmony_joint import f


def verify(r,ir):
    lo,hi=(f(r['span'][k]) for k in ('start','end'))
    expected=sum(max(0,min(hi,f(s['span']['end']))-max(lo,f(s['span']['start']))) for s in ir['sounding_events'])
    for reading in r['hold_readings']+r['change_readings']:
        p=reading['profile']
        assert f(p['total_note_time_quarters'])==expected
        assert sum(map(f,p['note_time_quarters'].values()))==expected
    assert r['selected'] is None and not r['ranking_performed']
    assert len(r['comparisons'])==len(r['hold_readings'])*len(r['change_readings'])
    for c in r['comparisons']:
        assert sum(map(f,c['change_minus_hold_note_time'].values()))==0 and c['preferred'] is None


def controls(source,output):
    from music21 import converter
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_change_gate import evaluate
    rows=[]
    for src in sorted((source/'controls').iterdir()):
        xml=src/'score.musicxml'
        if not xml.exists():continue
        dst=output/src.name;dst.mkdir(parents=True);shutil.copyfile(xml,dst/xml.name)
        ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
        old=load(src/'gate.json');gate=evaluate(ir,old['span'],old['boundary'])
        assert gate==old  # Also verify current parsing reproduces the prior control.
        r=compare(ir,gate);verify(r,ir)
        if src.name.startswith('actual_change-'):
            assert any(all(f(v['profile']['note_time_quarters'][k])==0 for k in
                           ('unexplained','spelling_unresolved')) for v in r['change_readings'])
        else:
            assert not r['change_readings']
        if src.name.startswith('passing_hold-'):
            assert any(f(v['profile']['note_time_quarters']['conditional_nct'])>0 for v in r['hold_readings'])
        write(dst/'contrast.json',r)
        rows.append({'case':src.name,'passed':True,'xml_sha256':digest(xml),
                     'comparison_count':len(r['comparisons']),'reused_existing_xml_control':True})
    return rows


def page(src,dst,title,manifest):
    original=(src/'whole-score.html').read_text(encoding='utf-8')
    start=original.index('<section class="scorepage"');end=original.index('</div></main>',start)
    score=original[start:end]
    options=''.join('<option value="'+str(i)+'">'+html.escape(m['label'])+'</option>' for i,m in enumerate(manifest))
    script=r'''
const $=id=>document.getElementById(id),names={member:'구성음',conditional_nct:'조건부 비화성음 설명',unexplained:'미설명',spelling_unresolved:'철자 미확정'};
const roles={anticipation_reattack_compatible:'선행음 형태',prepared_suspension_geometry:'지연음 형태',reattack_passing:'반복 포함 경과 형태',reattack_neighbor:'반복 포함 보조 형태',passing:'경과 형태',neighbor:'보조 형태',double_neighbor:'이중 보조 형태'};
let data,serial=0;const q=x=>x.denominator===1?''+x.numerator:x.numerator+'/'+x.denominator;
function el(tag,value){const n=document.createElement(tag);n.textContent=value;return n;}
function clear(){document.querySelectorAll('.scorepage .note').forEach(n=>n.classList.remove('member','conditional_nct','unexplained','spelling_unresolved','mixed'));$('mode').textContent='아직 선택한 색칠 없음';}
function mark(profile,name,sid){clear();let first;for(const [id,events] of Object.entries(profile.event_readings)){if(sid&&id!==sid)continue;const states=[...new Set(events.map(x=>x.bucket))],ids=new Set(data.event_units[id].source_note_ids);for(const n of document.querySelectorAll('.scorepage .note'))if(ids.has(n.dataset.id||n.id)){n.classList.add(states.length>1?'mixed':states[0]);first=first||n;}}$('mode').textContent='현재 색칠: '+name+(sid?' · '+data.event_units[sid].pitch.spelling:' · 전체 비교 구간');if(first)first.scrollIntoView({block:'center',behavior:'smooth'});}
function details(profile,sid){return profile.event_readings[sid].map(x=>q(x.span.start)+'–'+q(x.span.end)+'q: '+names[x.bucket]+(x.conditional_roles.length?' ('+x.conditional_roles.map(r=>roles[r]||r).join(', ')+')':'')).join(' / ');}
function draw(){clear();const h=data.hold_readings[+$('hold').value],c=data.change_readings[+$('change').value];const box=$('details');box.replaceChildren();if(!h||!c){box.append(el('p','이번 고정 범위에 비교할 교체 제안이 없습니다. 유지 확정은 아닙니다.'));return;}
const cp=data.comparisons.find(x=>x.hold_ref===h.candidate.candidate_id&&x.change_ref===c.proposal.proposal_id);
box.append(el('h3','동일 범위의 음표×시간 대조'),el('p','합계 '+q(h.profile.total_note_time_quarters)+' quarter-note-time. 다성부 음가를 합한 값이며 곡의 경과 시간·확률·점수가 아닙니다.'));
const table=document.createElement('table');let row=document.createElement('tr');['분류','유지','교체'].forEach(v=>row.append(el('th',v)));table.append(row);for(const k of Object.keys(names)){row=document.createElement('tr');[names[k],q(h.profile.note_time_quarters[k]),q(c.profile.note_time_quarters[k])].forEach(v=>row.append(el('td',v)));table.append(row);}box.append(table);
for(const [name,p] of [['유지',h.profile],['교체',c.profile]]){const b=el('button',name+' 가정의 전체 음 보기');b.onclick=()=>mark(p,name);box.append(b);box.append(el('p',name+'의 미관측 구성음: '+p.missing_members_by_segment.map(s=>s.label+' '+(s.missing_member_pcs.join(',')||'없음')).join(' / ')));}
box.append(el('p','미설명 음가가 적다는 이유만으로 선택하지 않습니다. 준비·해결·강세·화성 리듬과 후보의 타당성은 추가 검증 대상입니다.'));
const ids=[...new Set(cp.changed_readings.map(x=>x.event_ref))];box.append(el('h3','가정에 따라 설명이 달라지는 '+ids.length+'음'));
for(const sid of ids){const d=document.createElement('details');d.append(el('summary',data.event_units[sid].pitch.spelling));for(const [name,p] of [['유지',h.profile],['교체',c.profile]]){d.append(el('p',name+': '+details(p,sid)));const b=el('button',name+'에서 이 음 보기');b.onclick=()=>mark(p,name,sid);d.append(b);}box.append(d);}}
async function load(){clear();const req=++serial;$('details').textContent='불러오는 중…';$('hold').disabled=$('change').disabled=true;try{const resp=await fetch('contrasts/'+$('range').value+'.json');if(!resp.ok)throw Error('HTTP '+resp.status);const value=await resp.json();if(req!==serial)return;data=value;for(const [id,items] of [['hold',data.hold_readings.map(x=>x.candidate.label)],['change',data.change_readings.map(x=>x.proposal.source_label+' → '+x.proposal.target_label)]]){$(id).replaceChildren(...items.map((t,i)=>{const n=el('option',t);n.value=i;return n;}));$(id).disabled=false;}draw();}catch(e){if(req===serial)$('details').textContent='읽기 실패: '+e.message;}}
$('range').onchange=load;$('hold').onchange=draw;$('change').onchange=draw;if($('range').options.length)load();else $('details').textContent='기존 엄격한 교체 관문을 통과한 후보가 없어 이번 대조 대상이 없습니다. 유지 확정은 아닙니다.';
'''
    css='body{margin:0;background:#eef2f6;color:#183044;font:15px system-ui}header{padding:16px}main{display:grid;grid-template-columns:430px minmax(0,1fr);gap:12px}aside{position:sticky;top:0;height:96vh;overflow:auto;background:white;padding:12px}select{width:100%;padding:8px;margin-bottom:10px}button,summary{padding:8px;cursor:pointer}details{border-top:1px solid #ccc}p{overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:6px}.scorepage{background:white;padding:12px;margin:8px}svg{width:100%;height:auto}.member{fill:#198754!important;color:#198754!important}.conditional_nct{fill:#8e44ad!important;color:#8e44ad!important}.unexplained{fill:#c05600!important;color:#c05600!important}.spelling_unresolved{fill:#777!important;color:#777!important}.mixed{fill:#1971c2!important;color:#1971c2!important}@media(max-width:850px){main{display:block}aside{position:static;height:auto}}'
    (dst/'whole-score.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(title)+' · 유지와 교체 대조</title><style>'+css+'</style><header><a href="../../index.html">목록</a><h1>'+html.escape(title)+' · 유지와 교체의 경쟁 설명</h1><p>실험 후보 비교 · 정답/추천 순서 아님 · 기존 첫8마디 연구 중 교체 제안이 있었던 범위만 대조 · 전체 악장 표시</p><p>초록=구성음 · 보라=조건부 NCT 설명 · 주황=미설명 · 회색=철자 미확정 · 파랑=같은 지속음의 구간별 역할 다름</p><p id="mode">아직 선택한 색칠 없음</p><a href="manifest.json">범위 기록</a> · <a href="gate-results.json">원 교체 관문 결과</a></header><main><aside><label for="range">비교 범위</label><select id="range">'+options+'</select><label for="hold">유지 가설</label><select id="hold"></select><label for="change">교체 가설</label><select id="change"></select><div id="details"></div></aside><div>'+score+'</div></main><script>'+script+'</script></html>',encoding='utf-8')
    return set(re.findall(r'data-id="([^"]+)"[^>]*class="note"',score))


def build(source,output):
    from .harmony_ownership_diagnostic_review import position
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);prior=load(source/'report.json')
    write(output/'run-contract.json',{'version':VERSION,'prior_report_sha256':digest(source/'report.json'),
        'selection':'all prior boundaries with change proposals; all full-window holds crossed with all eligible changes',
        'selection_bias':'strict change eligibility cohort, not general recall or accuracy',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    report={'version':VERSION,'real':[],'production_modified':False,'ranking_performed':False,'accuracy_measured':False}
    for old in prior['real']:
        src=source/'real-cases'/old['case_id'];dst=output/'real-cases'/old['case_id'];dst.mkdir(parents=True);(dst/'contrasts').mkdir()
        prov=load(src/'source-snapshot'/'case-provenance.json')
        if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        for n,h in old['source_hashes'].items():
            if digest(src/'source-snapshot'/n)!=h:raise ValueError('source_changed')
        shutil.copytree(src/'source-snapshot',dst/'source-snapshot');shutil.copyfile(src/'gate-results.json',dst/'gate-results.json')
        ir=load(src/'source-snapshot'/'candidate_revision_ir.json');gates=load(src/'gate-results.json')['records']
        counts=Counter();manifest=[];used=set()
        for gate in gates:
            if not gate['change_proposals']:continue
            r=compare(ir,gate);verify(r,ir)
            write(dst/'contrasts'/(str(len(manifest))+'.json'),r)
            manifest.append({'span':r['span'],'boundary':r['boundary'],'label':position(ir,r['span']['start'])+' → '+position(ir,r['span']['end'])+' 직전 / 교체 위치 '+position(ir,r['boundary'])})
            counts['boundaries']+=1;counts['holds']+=len(r['hold_readings']);counts['changes']+=len(r['change_readings']);counts['comparisons']+=len(r['comparisons'])
            for v in r['comparisons']:
                d=f(v['change_minus_hold_note_time']['unexplained'])
                counts['less_unexplained_in_change' if d<0 else 'less_unexplained_in_hold' if d>0 else 'equal_unexplained']+=1
                counts['with_role_difference']+=bool(v['changed_readings'])
            for unit in r['event_units'].values():used.update(unit['source_note_ids'])
        write(dst/'manifest.json',manifest);assert used<=page(src,dst,old['title'],manifest)
        assert digest(src/'gate-results.json')==digest(dst/'gate-results.json')
        row={'case_id':old['case_id'],'title':old['title'],**dict(counts),'source_hashes':old['source_hashes'],
             'prior_gate_sha256':digest(src/'gate-results.json'),'source_refs_verified':len(used)}
        report['real'].append(row);print(row['title']+': '+str(dict(counts)),flush=True)
    report['controls']=controls(source,output/'controls');write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html">'+html.escape(r['title'])+'</a></li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>유지 / 교체 후보의 같은 음표·시간 대조</h1><p>미설명 음가 차이는 정답 확률이 아닙니다. 원 후보와 source XML/IR을 보존합니다.</p><ul>'+links+'</ul><a href="report.json">검증 보고서</a></html>',encoding='utf-8')
    print('Controls passed: '+str(len(report['controls'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
