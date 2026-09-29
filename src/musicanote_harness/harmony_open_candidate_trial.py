"""Reproducible inclusive-candidate trial and full-score candidate inspector."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
from fractions import Fraction as F
import re
import shutil
from .formal_ir import q
from .harmony_joint import f
from .harmony_open_candidates import observe,window,VERSION
from .harmony_arpeggio_benchmark import digest,write,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_ownership_diagnostic_review import position


def make_page(source, output, ir, result):
    page=(source/'whole-score.html').read_text(encoding='utf-8')
    page=re.sub(r'<script>.*?</script>','',page,flags=re.S)
    # Use the existing verified whole-score page count, never truncate the movement.
    pages=len(re.findall(r'<section class="scorepage"',page))
    options=''.join('<option value="page-'+str(i)+'">페이지 '+str(i)+'</option>' for i in range(1,pages+1))
    header='<header><h1>화성 후보 확장 실험 · 전체 악장</h1><p>악보 전체 / 계산은 앞 32개 물리 마디. 확정 로마자 분석이 아닙니다. 후보의 구성음(초록), 미설명 음(주황), 철자 미확정(회색)을 구별합니다. 주황은 비화성음 확정이 아닙니다. 구간 밖으로 화음을 연장하지 않습니다.</p><label>전체 악장 페이지 <select id="page-select">'+options+'</select></label> · <a href="report.json">실험 보고서</a></header>'
    page=re.sub(r'<header>.*?</header>',header,page,flags=re.S)
    measure_list=[];index=[]
    for i,r in enumerate(result['records']):
        start=f(r['span']['start']);m=max((m for m in ir['measures'] if f(m['global_start_quarter'])<=start),key=lambda m:f(m['global_start_quarter']))
        key=m['measure_id']
        if key not in [k for k,_ in measure_list]:measure_list.append((key,m['printed_measure_number']))
        index.append({'measure':key,'file':'windows/'+str(i)+'.json','label':position(ir,r['span']['start'])+' → '+position(ir,r['span']['end'])+' 직전','count':len(r['candidates'])})
    panel='<aside><h2>후보를 직접 비교</h2><label>시작 마디 <select id="measure-choice">'+''.join('<option value="'+html.escape(k)+'">'+html.escape(n)+'마디</option>' for k,n in measure_list)+'</select></label><p><label>비교 구간 <select id="window-choice"></select></label></p><p id="window-info"></p><p id="choice-info">화음을 자동 선택하지 않습니다.</p><div id="candidate-list"></div></aside>'
    page=re.sub(r'<aside>.*?</aside>',panel,page,flags=re.S)
    script=r'''
<style>.open-member{fill:#17814c!important;color:#17814c!important}.open-residual{fill:#c05600!important;color:#c05600!important}.open-unresolved{fill:#777!important;color:#777!important}select{max-width:100%}#candidate-list button{display:block;width:100%;text-align:left;margin:6px 0}#choice-info{white-space:pre-line}aside{overflow-x:hidden}</style>
<script>const windowIndex=INDEX;let currentWindow=null,requestId=0;const classes=['open-member','open-residual','open-unresolved'];
function clear(){document.querySelectorAll('.scorepage .note').forEach(n=>n.classList.remove(...classes));}
function choose(c){clear();const notes={};for(const [sid,state] of Object.entries(c.event_states)){for(const id of currentWindow.event_units[sid].source_note_ids)notes[id]=state;}
 let first=null;for(const n of document.querySelectorAll('.scorepage .note')){const state=notes[n.dataset.id||n.id];if(state){n.classList.add(state==='member'?'open-member':state==='nonmember_not_confirmed_nct'?'open-residual':'open-unresolved');first=first||n;}}
 const roleCount=currentWindow.conditional_figures.records.filter(r=>r.path_explanations.some(p=>p.path_ref===c.candidate_id&&p.status==='conditional_ornament_compatible')).length;
 document.querySelector('#choice-info').textContent='선택해 본 후보: '+label(c)+'\n미설명 sound '+c.residual_event_refs.length+' / 미관측 구성음 '+c.missing_member_pcs.length+' / 조건부 경과·보조 형태 '+roleCount+'\n이는 저장된 화음 선택이나 확정 비화성음이 아닙니다.';
 if(first){first.scrollIntoView({block:'center',behavior:'smooth'});document.querySelector('#page-select').value=first.closest('.scorepage').id;}}
function label(c){return c.root_hypotheses.length?c.root_hypotheses.map(r=>r.conditional_label).join(' / '):c.label+' (근음 철자 미확정)';}
async function loadWindow(){const mine=++requestId;clear();currentWindow=null;document.querySelector('#candidate-list').replaceChildren();document.querySelector('#choice-info').textContent='불러오는 중…';
 try{const response=await fetch(document.querySelector('#window-choice').value);if(!response.ok)throw Error('HTTP '+response.status);const r=await response.json();if(mine!==requestId)return;currentWindow=r;
 document.querySelector('#window-info').textContent='후보 '+r.candidates.length+'개 · 후보 순서는 근음/템플릿 순이며 추천 순위가 아닙니다. '+(r.abstention_reasons.length?'문맥 보류: '+r.abstention_reasons.join(', '):'');
 document.querySelector('#choice-info').textContent='비교할 후보를 누르세요. 구간은 시험 창이며 확정 화음 경계가 아닙니다.';
 for(const c of r.candidates){const button=document.createElement('button');button.textContent=label(c)+' · 미설명 '+c.residual_event_refs.length+' · 미관측 '+c.missing_member_pcs.length;button.onclick=()=>choose(c);document.querySelector('#candidate-list').append(button);}
 }catch(e){if(mine===requestId)document.querySelector('#choice-info').textContent='자료를 불러오지 못했습니다: '+e.message;}}
function changeMeasure(){const select=document.querySelector('#window-choice');select.replaceChildren();for(const r of windowIndex.filter(r=>r.measure===document.querySelector('#measure-choice').value)){const o=document.createElement('option');o.value=r.file;o.textContent=r.label;select.append(o);}loadWindow();}
document.querySelector('#measure-choice').onchange=changeMeasure;document.querySelector('#window-choice').onchange=loadWindow;
document.querySelector('#page-select').onchange=e=>document.getElementById(e.target.value).scrollIntoView({block:'start',behavior:'smooth'});changeMeasure();</script>
'''.replace('INDEX',json.dumps(index,ensure_ascii=False))
    (output/'whole-score.html').write_text(page.replace('</html>',script+'</html>'),encoding='utf-8')


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    provenance=load(source/'case-provenance.json');entry=provenance['manifest_entry'];release=provenance['revision']
    if entry['split']!='train' or not entry['rights']['internal_research_use']:raise ValueError('ineligible_case')
    required={**release['hashes'],Path(entry['score_source_path']).name:entry['score_sha256']}
    if any(digest(source/n)!=h for n,h in required.items()):raise ValueError('source_changed')
    ir=load(source/'canonical_music_ir.json');old=load(source/'distributed-readings.json');span=old['analysis_span']
    output.mkdir(parents=True);shutil.copytree(source,output/'source-snapshot');(output/'windows').mkdir()
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'analysis_span':span,'same_span_as_prior':True,
        'source_hashes':required,'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'source_annotation_used':False})
    result=observe(ir,span);write(output/'open-candidates.json',result)
    for i,r in enumerate(result['records']):
        expected=set(r['event_refs'])
        assert all(set(c['event_states'])==expected for c in r['candidates'])
        assert all(not c['silence'] or not c['event_refs'] for c in r['cells'])
        assert f(r['cells'][0]['span']['start'])==f(r['span']['start']) and f(r['cells'][-1]['span']['end'])==f(r['span']['end'])
        write(output/'windows'/(str(i)+'.json'),r)
    signatures=Counter();samples=[]
    for r in result['records']:
        compatible=[c for c in r['candidates'] if c['root_hypotheses'] and c['template_fully_observed']]
        for c in compatible:signatures[c['label'].split(':')[1]]+=1
        if any(c['residual_event_refs'] for c in compatible):samples.append(r['window_id'])
    report={'version':VERSION,'analysis_span':span,**result['summary'],'fully_observed_spelled_candidates_by_quality_not_votes':dict(signatures),
        'windows_with_complete_spelled_template_and_residual':len(samples),'prior_strict_pair_windows':len(old['alternatives']),
        'comparison_warning':'New single-window proposals and old paired-triad windows have different denominators; not accuracy comparison.',
        'retained_all_event_references':True,'selected_harmony_changed':False,'accuracy_measured':False,'production_modified':False,
        'full_score_source':'source-snapshot/whole-score.html','first32_physical_measures_only':True}
    report['xml_controls']=controls(output/'controls')
    write(output/'report.json',report);make_page(source,output,ir,result)
    assert all(digest(source/n)==h and digest(output/'source-snapshot'/n)==h for n,h in required.items())
    write(output/'verification.json',{'passed':True,'source_and_snapshot_hashes_match':True,'all_candidate_event_partitions_complete':True,'all_windows_exact_spans':True})
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


def controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    cases={
        'passing':[('C3',0,4,'2'),('E3',0,4,'3'),('G3',0,4,'4'),('C4',0,1,'1'),('D4',1,1,'1'),('E4',2,2,'1')],
        'real_major7':[('C3',0,4,'2'),('E3',0,4,'3'),('G3',0,4,'4'),('B3',0,4,'1')],
        'double_neighbor_deferred':[('A-3',0,4,'2'),('C4',0,4,'3'),('E-4',0,4,'4'),('A-4',0,1,'1'),('G4',1,1,'1'),('B-4',2,1,'1'),('A-4',3,1,'1')]}
    rows=[]
    for kind,specs in cases.items():
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            case={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in specs]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            r=window(ir,{'start':q(0),'end':q(4*scale)});write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',r)
            signature=sorted(((c['root']-tr)%12,c['label'].split(':')[1],len(c['residual_event_refs']),len(c['missing_member_pcs'])) for c in r['candidates'])
            if baseline is None:baseline=signature
            else:assert signature==baseline
            assert r['conditional_figures']['summary']['conditional_ornament_triples']==(1 if kind=='passing' else 0)
            rows.append({'case':dst.name,'passed':True,'source_sha256':digest(xml),'ir_sha256':digest(dst/'canonical_music_ir.json')})
    return rows


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args();build(a.source,a.output)
