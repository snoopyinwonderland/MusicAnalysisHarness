"""Apply a frozen experimental gate to prior label-blind windows and XML controls."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
import json
from pathlib import Path
import shutil
from .formal_ir import q
from .harmony_joint import f
from .harmony_change_gate import evaluate,VERSION
from .harmony_arpeggio_benchmark import write,digest,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_ownership_diagnostic_review import position


def controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    specs={
      'actual_change':[('C3',0,2,'1'),('E4',0,2,'2'),('G4',0,2,'3'),('G2',2,2,'1'),('D4',2,2,'2'),('B4',2,2,'3')],
      'passing_hold':[('C3',0,4,'1'),('E3',0,4,'2'),('G3',0,4,'3'),('C4',0,1,'4'),('D4',1,1,'4'),('E4',2,2,'4')],
      'arpeggio':[('C4',0,1,'1'),('E4',1,1,'1'),('G4',2,1,'1'),('C5',3,1,'1')],
      'shared_bass':[('C3',0,4,'1'),('E4',0,2,'2'),('G4',0,2,'3'),('D4',2,2,'2'),('B4',2,2,'3'),('G4',2,2,'4')],
      'repeat_chord':[('C3',0,2,'1'),('E4',0,2,'2'),('G4',0,2,'3'),('C3',2,2,'1'),('E4',2,2,'2'),('G4',2,2,'3')],
      'short_actual_change':[('C3',0,F(1,2),'1'),('E4',0,F(1,2),'2'),('G4',0,F(1,2),'3'),('G2',F(1,2),F(3,2),'1'),('D4',F(1,2),F(3,2),'2'),('B4',F(1,2),F(3,2),'3'),('G2',2,2,'1'),('D4',2,2,'2'),('B4',2,2,'3')]}
    rows=[]
    for kind,events in specs.items():
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            case={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in events]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            result=evaluate(ir,{'start':q(0),'end':q(4*scale)},q((F(1,2) if kind=='short_actual_change' else 2)*scale))
            labels={(r['source_label'].split(':')[1],r['target_label'].split(':')[1]) for r in result['change_proposals']}
            assert bool(result['change_proposals'])==(kind=='actual_change')
            if kind=='passing_hold':assert result['hold_proposals']
            sig=(len(result['change_proposals']),len(result['hold_proposals']),sorted(labels))
            if baseline is None:baseline=sig
            else:assert sig==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'gate.json',result)
            rows.append({'case':dst.name,'passed':True,'signature':sig,'xml_sha256':digest(xml),
                'oracle':'authored eligibility conditions, NOT comprehensive harmonic truth'})
    return rows


def page(src,dst,ir,rows,title):
    original=(src/'whole-score.html').read_text(encoding='utf-8');begin=original.index('<section class="scorepage"');end=original.index('</div></main>',begin)
    payload=[];cards=[]
    for row in rows:
        for p in row['change_proposals']:
            i=len(payload)
            left=next(c for c in row['left_window']['candidates'] if c['candidate_id']==p['source_candidate_ref'])
            right=next(c for c in row['right_window']['candidates'] if c['candidate_id']==p['target_candidate_ref'])
            refs={side:{sid for sid,state in c['event_states'].items() if state=='member'} for side,c in [('before',left),('after',right)]}
            shared=refs['before']&refs['after'];refs['before']-=shared;refs['after']-=shared;refs['shared']=shared
            payload.append({k:sorted({nid for sid in ids for nid in row['event_units'][sid]['source_note_ids']}) for k,ids in refs.items()})
            label=position(ir,row['boundary'])+' · '+p['source_label']+' → '+p['target_label']
            cards.append('<article><button data-proposal="'+str(i)+'">'+html.escape(label)+'</button><p>엄격한 관측 조건 통과 · 최종 화음/경계 확정 아님</p><p>비교 범위 '+html.escape(position(ir,row['span']['start'])+' → '+position(ir,row['span']['end']))+' 직전</p><p>서로 다른 PC 진행 '+str(len(p['distinct_motion_pc_pairs']))+'쌍 · 배타적 구성음 교체/베이스 변화 관측</p><p>미설명음 앞 '+str(p['source_residual_count'])+' / 뒤 '+str(p['target_residual_count'])+'개 — NCT 확정 아님. 같은 경계의 다른 화음명도 통과할 수 있습니다.</p></article>')
    if not cards:cards=['<p>이번 고정 구간에서 엄격한 교체 관문을 통과한 후보가 없습니다. 화음이 유지된다는 뜻은 아닙니다.</p>']
    holds=sum(len(r['hold_proposals']) for r in rows)
    script='const payload='+json.dumps(payload)+';document.querySelectorAll("[data-proposal]").forEach(b=>b.onclick=()=>{let first;const p=payload[+b.dataset.proposal];document.querySelectorAll(".scorepage .note").forEach(n=>{n.classList.remove("before","after","shared");for(const k of ["before","after","shared"])if(p[k].includes(n.dataset.id||n.id)){n.classList.add(k);first=first||n;}});if(first)first.scrollIntoView({block:"center",behavior:"smooth"});});'
    css='body{margin:0;background:#eef2f6;font:15px system-ui;color:#183044}header{padding:16px}main{display:grid;grid-template-columns:420px minmax(0,1fr);gap:12px}aside{position:sticky;top:0;height:96vh;overflow:auto;padding:10px}article,.scorepage{background:white;padding:12px;margin:8px}button{padding:10px;cursor:pointer}svg{width:100%;height:auto}.before{fill:#1971c2!important;color:#1971c2!important}.after{fill:#198754!important;color:#198754!important}.shared{fill:#8e44ad!important;color:#8e44ad!important}@media(max-width:850px){main{display:block}aside{position:static;height:auto}}'
    (dst/'whole-score.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(title)+' · 화음 교체 관문</title><style>'+css+'</style><header><a href="../../index.html">목록</a><h1>'+html.escape(title)+' · 화음 교체 관문</h1><p>파랑=앞 후보 구성음 · 초록=뒤 후보 구성음 · 보라=양쪽에 실제 지속. 조건부 제안이며 확정 화성/기능/전위가 아닙니다.</p><p>첫8개 물리 마디의 내부 attack/release 경계만 검사 · 전체 악장 표시 · 엄격한 관문 탈락은 유지 판정이 아닙니다.</p><p>조건부 장식음 유지 가설 출현 '+str(holds)+'개(중복 가능). <a href="gate-results.json">모든 보류·반례·후보 근거</a></p></header><main><aside>'+''.join(cards)+'</aside><div>'+original[begin:end]+'</div></main><script>'+script+'</script></html>',encoding='utf-8')


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    prior=load(source/'report.json');output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'prior_report_sha256':digest(source/'report.json'),
      'selection':'all interior attack/release boundaries in prior frozen 24 measure windows; no source label or user-feedback selection',
      'threshold':'both sides at least one denominator beat; >=2 new exclusive target PCs, >=1 departing source PC, acoustic bass replacement, >=2 distinct direct voice PC motions; complete spelled hypotheses; no active departing exclusive member; no complete prepared ornament explanation',
      'cohort':'previously used train works; no independent accuracy estimate',
      'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    report={'version':VERSION,'real':[],'production_modified':False,'selected_harmony_changed':False,'accuracy_measured':False}
    for old in prior['real']:
        src=source/'real-cases'/old['case_id'];dst=output/'real-cases'/old['case_id'];dst.mkdir(parents=True)
        snap=src/'source-snapshot';prov=load(snap/'case-provenance.json')
        if prov['manifest_entry']['split']!='train' or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        for n,h in old['source_hashes'].items():
            if digest(snap/n)!=h:raise ValueError('source_changed')
        shutil.copytree(snap,dst/'source-snapshot');ir=load(snap/'candidate_revision_ir.json')
        results=[];source_hashes={};counts=Counter();fail=Counter()
        for file in sorted((src/'windows').glob('*.json'),key=lambda p:int(p.stem)):
            source_hashes[file.name]=digest(file);prior_window=load(file)
            for stage in prior_window['stages'][1:]:
                r=evaluate(ir,prior_window['span'],stage['span']['start']);results.append(r)
                counts['boundaries']+=1;counts['pairs_tested']+=r['pair_count'];counts['change_proposals']+=len(r['change_proposals']);counts['conditional_hold_occurrences']+=len(r['hold_proposals'])
                counts['boundaries_with_change_proposals']+=bool(r['change_proposals']);fail.update(r['failed_gate_counts'])
        assert all(digest(src/'windows'/n)==h for n,h in source_hashes.items())
        write(dst/'gate-results.json',{'version':VERSION,'records':results,'source_window_hashes':source_hashes});page(src,dst,ir,results,old['title'])
        report['real'].append({'case_id':old['case_id'],'title':old['title'],**dict(counts),'failed_gate_counts':dict(fail),'source_hashes':old['source_hashes'],'source_window_hashes':source_hashes})
        print(old['title']+': '+str(dict(counts)),flush=True)
    report['controls']=controls(output/'controls');write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html">'+html.escape(r['title'])+'</a> — '+str(r['change_proposals'])+'개 조건부 교체 제안</li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>화음 유지·교체 판별 관문 실험</h1><p>구성음 완전성만으로 선택하지 않고 실제 교체·베이스·직접 성부 이동·조건부 장식음 설명을 함께 검사합니다. 엄격한 조건의 실험 제안이지 최종 분석/정확도 평가가 아닙니다.</p><ul>'+links+'</ul><a href="report.json">검증 보고서</a></html>',encoding='utf-8')
    print('Controls passed: '+str(len(report['controls'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
