"""Label-blind fixed-measure coverage audit, not a held-out accuracy benchmark."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
import json
from pathlib import Path
import re
import shutil
from .formal_ir import q
from .harmony_joint import f
from .harmony_temporal_readings import compare, VERSION
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_ownership_diagnostic_review import position


def verify(ir, result):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    a,b=(f(result['span'][k]) for k in ('start','end'))
    expected={sid for sid,s in sounds.items() if f(s['span']['start'])<b and f(s['span']['end'])>a}
    assert set(result['event_units'])==expected
    cursor=a
    for stage in result['stages']:
        lo,hi=(f(stage['span'][k]) for k in ('start','end'))
        assert cursor==lo and lo<hi;cursor=hi
        refs={sid for sid,s in sounds.items() if f(s['span']['start'])<hi and f(s['span']['end'])>lo}
        assert set(stage['event_refs'])==refs
        for p in list(stage['fixed_profiles'].values())+[v['profile'] for v in stage['alternatives']]:
            got=[sid for e in p['groups']['other'].values() for sid in e['event_refs']]
            assert len(got)==len(set(got)) and set(got)==refs
            for e in p['groups']['other'].values():
                duration=sum((min(hi,f(sounds[sid]['span']['end']))-max(lo,f(sounds[sid]['span']['start'])) for sid in e['event_refs']),F(0))
                assert f(e['duration_quarters'])==duration
    assert cursor==b
    for r in result['fixed_readings']:
        combined=Counter()
        for s in result['stages']:
            for state,e in s['fixed_profiles'][r['candidate']['candidate_id']]['groups']['other'].items():
                combined[state]+=f(e['duration_quarters'])
        assert dict(combined)=={k:f(v['duration_quarters']) for k,v in r['profile']['groups']['other'].items()}
    assert result['selected'] is None and not result['ranking_performed']


def controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    specs={
      'passing_over_hold':[('C3',0,4,'1'),('E3',0,4,'2'),('G3',0,4,'3'),('C4',0,1,'4'),('D4',1,1,'4'),('E4',2,2,'4')],
      'real_change':[('C3',0,2,'1'),('E3',0,2,'2'),('G3',0,2,'3'),('G2',2,2,'1'),('B3',2,2,'2'),('D4',2,2,'3')],
      'missing_fifth':[('C3',0,4,'1'),('E3',0,4,'2')],
      'rootless':[('E3',0,4,'1'),('G3',0,4,'2')],
      'future_member':[('C3',0,2,'1'),('E3',0,2,'2'),('G3',2,2,'1')],
      'actual_major7':[('C3',0,4,'1'),('E3',0,4,'2'),('G3',0,4,'3'),('B3',0,4,'4')]}
    rows=[]
    for kind,events in specs.items():
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            case={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in events]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            span={'start':q(0),'end':q(4*scale)};r=compare(ir,span,span);verify(ir,r)
            c=next(c for c in r['fixed_readings'] if c['candidate']['root']==tr and c['candidate']['label'].endswith(':major'))
            if kind=='passing_over_hold':assert c['conditional_ornaments']
            if kind=='missing_fifth':assert len(c['timeline']['missing_inside'])==1
            if kind=='rootless':assert 'root_spelling_unobserved_or_ambiguous' in c['abstention_reasons']
            if kind=='future_member':
                stage=next(v for v in r['stages'][0]['alternatives'] if v['label']==c['candidate']['label'])
                assert len(stage['timeline']['missing_inside'])==1
            if kind=='actual_major7':
                seventh=next(v for v in r['fixed_readings'] if v['candidate']['root']==tr and v['candidate']['label'].endswith(':major7'))
                assert not seventh['candidate']['residual_event_refs'] and c['candidate']['residual_event_refs']
            if kind=='real_change':
                last=r['stages'][-1]
                retained=last['fixed_profiles'][c['candidate']['candidate_id']]
                assert retained['groups']['other']['nonmember_not_confirmed_nct']['event_refs']
                destination=next(v for v in last['alternatives'] if v['timeline']['candidate']['root']==(7+tr)%12 and v['label'].endswith(':major'))
                assert not destination['profile']['groups']['other'].get('nonmember_not_confirmed_nct')
            sig=(len(r['fixed_readings']),len(r['stages']),len(c['conditional_ornaments']),len(c['timeline']['missing_inside']))
            if baseline is None:baseline=sig
            else:assert sig==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',r)
            rows.append({'case':dst.name,'passed':True,'xml_sha256':digest(xml),'signature':sig})
    return rows


def page(src,dst,ir,manifest,title):
    original=(src/'whole-score.html').read_text(encoding='utf-8')
    begin=original.index('<section class="scorepage"');end=original.index('</div></main>',begin)
    score=original[begin:end]
    options=''.join('<option value="'+str(i)+'">'+html.escape(r['display'])+'</option>' for i,r in enumerate(manifest))
    script=r'''
const $=id=>document.getElementById(id);let data,serial=0;
const duration=q=>q?`${q.numerator}/${q.denominator}`:'—';
function text(tag,s){const n=document.createElement(tag);n.textContent=s;return n;}
function clearMark(){document.querySelectorAll('.note.member,.note.residual,.note.unresolved').forEach(n=>n.classList.remove('member','residual','unresolved'));}
function mark(p){clearMark();let first;
for(const [state,e] of Object.entries(p.groups.other)){const ids=new Set(e.event_refs.flatMap(s=>data.event_units[s].source_note_ids));for(const n of document.querySelectorAll('.scorepage .note'))if(ids.has(n.dataset.id||n.id)){n.classList.add(state==='member'?'member':state==='nonmember_not_confirmed_nct'?'residual':'unresolved');first=first||n;}}
if(first)first.scrollIntoView({block:'center',behavior:'smooth'});}
function profileText(p){return Object.entries(p.groups.other).map(([k,e])=>`${k==='member'?'구성음':k==='nonmember_not_confirmed_nct'?'미설명음':'철자 보류'} ${e.event_refs.length}음 / ${duration(e.duration_quarters)} quarter`).join(' · ')||'울리는 음 없음';}
function describe(v){return profileText(v.profile)+' | 미관측 '+(v.timeline.missing_inside.join(', ')||(v.timeline.members.length?'없음':'철자 보류로 계산 불가'))+' | 보류: '+(v.abstention_reasons.join(', ')||'없음');}
function draw(){clearMark();const box=$('details');box.replaceChildren();const r=data.fixed_readings[+$('candidate').value];if(!r){box.append(text('p','두 pitch class 이상인 후보가 없습니다. 화음 부재 확정은 아닙니다.'));return;}
box.append(text('h3','한 화음 유지 가설: '+r.candidate.label),text('p',describe(r)),text('p','조건부 장식음 설명 '+r.conditional_ornaments.length+'개 · NCT 확정/음 삭제 아님'));
const fixed=text('button','유지 가설의 전체 음표 보기');fixed.onclick=()=>mark(r.profile);box.append(fixed);
data.stages.forEach((s,i)=>{const d=document.createElement('details');d.append(text('summary',s.display+' · '+s.event_refs.length+'음'+(s.silence?' / 쉼':'')));
const hold=text('button','같은 화음 유지 가정으로 색칠');hold.onclick=()=>mark(s.fixed_profiles[r.candidate.candidate_id]);d.append(hold,text('p','유지 가정: '+profileText(s.fixed_profiles[r.candidate.candidate_id])));
for(const v of s.alternatives){const p=document.createElement('p');const b=text('button',v.label);b.onclick=()=>mark(v.profile);p.append(b,text('span',' '+(v.origin==='carried_whole_window_hypothesis'?'전체 창에서 가져온 가설':'이 셀의 관측 후보')+' · '+describe(v)));d.append(p);}box.append(d);});}
async function load(){const request=++serial;clearMark();$('candidate').disabled=true;$('details').textContent='불러오는 중…';try{const response=await fetch('windows/'+$('range').value+'.json');if(!response.ok)throw Error('HTTP '+response.status);const value=await response.json();if(request!==serial)return;data=value;$('candidate').replaceChildren(...data.fixed_readings.map((r,i)=>{const n=text('option',r.candidate.label+(r.candidate.missing_member_pcs.length?' · 불완전 후보':''));n.value=i;return n;}));$('candidate').disabled=false;draw();}catch(e){if(request===serial)$('details').textContent='읽기 실패: '+e.message;}}
$('range').onchange=load;$('candidate').onchange=draw;load();
'''
    css='body{margin:0;background:#eef2f6;font:15px system-ui;color:#183044}header{padding:16px}main{display:grid;grid-template-columns:430px minmax(0,1fr);gap:10px}aside{height:96vh;position:sticky;top:0;overflow:auto;padding:10px;background:white}select{width:100%;padding:8px;margin-bottom:10px}button,summary{padding:8px;cursor:pointer}details{border-top:1px solid #bbb;padding:8px}p{overflow-wrap:anywhere}.scorepage{background:white;padding:12px;margin:8px}svg{width:100%;height:auto}.member{fill:#198754!important;color:#198754!important}.residual{fill:#d2691e!important;color:#d2691e!important}.unresolved{fill:#8e44ad!important;color:#8e44ad!important}@media(max-width:850px){main{display:block}aside{position:static;height:auto}}'
    (dst/'whole-score.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(title)+' · 시간별 화성 대안</title><style>'+css+'</style><header><a href="../../index.html">목록</a><h1>'+html.escape(title)+' · 시간별 화성 대안</h1><p>처음8개 물리 마디 고정 검사 · 전체 악장 표시 · 정확도 평가/최종 화음 선택 아님</p><p>초록=가정한 화음의 구성음 · 주황=미설명음(NCT 확정 아님) · 보라=철자 보류. 음의 시작/끝으로 나눈 셀은 화음 경계가 아닙니다.</p></header><main><aside><label for="range">검토 마디</label><select id="range">'+options+'</select><label for="candidate">화음 유지 가설 (추천 순서 아님)</label><select id="candidate"></select><div id="details"></div></aside><div>'+score+'</div></main><script>'+script+'</script></html>',encoding='utf-8')
    return {'pages':score.count('class="scorepage"'),'rendered_note_ids':set(re.findall(r'data-id="([^"]+)"[^>]*class="note"',score))}


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);old=load(source/'report.json')
    write(output/'run-contract.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),
        'selection':'all first 8 unique physical measure starts, with next measure available for context; no labels, candidate-completeness or user-measure filtering',
        'cohort_status':'three previously used train works; coverage audit, NOT independent holdout',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    report={'version':VERSION,'real':[],'source_annotations_used':False,'accuracy_measured':False,'production_modified':False}
    for row in old['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id'];dst.mkdir(parents=True);(dst/'windows').mkdir()
        prov=load(src/'case-provenance.json')
        if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        names=['candidate_revision_ir.json','case-provenance.json',Path(prov['manifest_entry']['score_source_path']).name]
        hashes={n:digest(src/n) for n in names}
        for n,h in hashes.items():
            if h!=row['prior_sha256'][n]:raise ValueError('input_changed')
        snap=dst/'source-snapshot';snap.mkdir()
        for n in names:shutil.copyfile(src/n,snap/n)
        ir=load(src/'candidate_revision_ir.json');starts=sorted({f(m['global_start_quarter']) for m in ir['measures']})
        end=max(f(m['global_start_quarter'])+f(m['actual_duration_quarter']) for m in ir['measures'])
        context={'start':q(starts[0]),'end':q(starts[9] if len(starts)>9 else end)}
        manifest=[];counts=Counter();used=set()
        for i,a in enumerate(starts[:8]):
            b=starts[i+1] if i+1<len(starts) else end
            r=compare(ir,{'start':q(a),'end':q(b)},context);verify(ir,r)
            r['display']=position(ir,q(a))+' → '+position(ir,q(b))+' 직전'
            for s in r['stages']:s['display']=position(ir,s['span']['start'])+' → '+position(ir,s['span']['end'])+' 직전'
            write(dst/'windows'/(str(i)+'.json'),r);manifest.append({'span':r['span'],'display':r['display']})
            counts['windows']+=1;counts['fixed_candidates']+=len(r['fixed_readings']);counts['cells']+=len(r['stages'])
            for c in r['fixed_readings']:
                counts['with_missing_pitch_classes']+=bool(c['candidate']['missing_member_pcs'])
                counts['with_unresolved_root_spelling']+=not bool(c['candidate']['root_hypotheses'])
                counts['with_conditional_ornament']+=bool(c['conditional_ornaments'])
                counts['with_abstention']+=bool(c['abstention_reasons'])
            counts['cell_alternatives']+=sum(len(s['alternatives']) for s in r['stages'])
            counts['cell_outside_only_member_occurrences']+=sum(m['missing_inside_but_seen_outside'] for s in r['stages'] for c in s['alternatives'] for m in c['timeline']['members'])
            for u in r['event_units'].values():used.update(u['source_note_ids'])
        write(dst/'manifest.json',manifest);render=page(src,dst,ir,manifest,row['title'])
        assert used<=render.pop('rendered_note_ids')
        assert all(digest(src/n)==h and digest(snap/n)==h for n,h in hashes.items())
        report['real'].append({'case_id':row['case_id'],'title':row['title'],**dict(counts),'source_hashes':hashes,
            'source_page_sha256':digest(src/'whole-score.html'),'referenced_notes_mapped':len(used),'rendering':render,'audit_passed':True})
        print(row['title']+': '+str(dict(counts)),flush=True)
    report['controls']=controls(output/'controls');write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html">'+html.escape(r['title'])+'</a></li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>불완전 후보를 포함한 유지·교체 근거 비교</h1><p>세 train 악장의 처음8마디를 결과와 무관하게 고정했습니다. 같은 작품의 이전 연구가 있으므로 독립 holdout/정확도 평가가 아닙니다.</p><p>추천 순위/화음 경계/최종 선택은 아직 없으며, 조건부 비화성음과 구성음 대안의 근거를 비교합니다.</p><ul>'+links+'</ul><a href="report.json">검증 보고서</a></html>',encoding='utf-8')
    print('Controls passed: '+str(len(report['controls'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
