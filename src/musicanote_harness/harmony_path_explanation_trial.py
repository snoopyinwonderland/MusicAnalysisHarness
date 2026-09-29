"""Whole-movement review of frozen competing harmonic explanations."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
import json
from pathlib import Path
import shutil
from music21 import converter,pitch
from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter,q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import write,digest,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_path_contrast_trial import control_xml
from .harmony_path_explanation import explain,VERSION
from .harmony_surface import TEMPLATES,PITCH_NAMES
from .harmony_ownership_diagnostic_review import position
from .sonata_verification import verified_pages

KINDS=('both_fit','extra_seventh','pedal','enharmonic','silence')


def unique_records(records, key):
    """Only identical duplicates may collapse; never overwrite a conflicting ID."""
    result={}
    for record in records:
        ident=record[key]
        if ident in result and result[ident]!=record:raise ValueError('conflicting_frozen_id:'+ident)
        result[ident]=record
    return result


def fixture(kind,tr=0,scale=F(1)):
    specs=[('C3',0,F(1,2) if kind=='silence' else 1,'2')]
    specs += [(p,1+F(i,4),F(1,4),'1') for i,p in enumerate(['C4','E4','G4','C4','E4','G4','B4','E4'])]
    specs += [('E3',3,1,'2')]
    specs += {'both_fit':[],'extra_seventh':[('B3',1,1,'3')],'pedal':[('C2',0,4,'3')],'enharmonic':[('F-4',3,1,'3')],'silence':[]}[kind]
    def c(root,quality):
        root=(root+tr)%12
        return {'root':root,'label':PITCH_NAMES[root]+':'+quality,'pcs':sorted((root+i)%12 for i in dict(TEMPLATES)[quality])}
    def seg(a,b,ch):return {'span':{'start':q(a*scale),'end':q(b*scale)},'candidate':ch}
    candidate={'evidence_id':'authored','span':{'start':q(scale),'end':q(3*scale)},'boundary':q(2*scale),'beat_unit_quarter':q(scale),
        'merged_seventh':[{'segments':[seg(1,3,c(0,'major7'))]}],
        'split_triads':[{'segments':[seg(1,2,c(0,'major')),seg(2,3,c(4,'minor'))]}]}
    return {'kind':kind,'beat_type':int(4/scale),'scale':q(scale),'events':[{'pitch':(pitch.Pitch(p) if tr==0 else pitch.Pitch(p).transpose('M2')).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in specs],
        'candidate':candidate,'context':{'start':q(0),'end':q(4*scale)},'oracle':'authored_candidate_paths_not_gold_harmony',
        'expected_status':'different_explanation_not_winner' if kind in ('extra_seventh','pedal') else 'spelling_unresolved' if kind=='enharmonic' else 'same_observed_membership_not_equivalent_harmony'}


def verify(ir,r):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};cells=r['cells']
    assert cells[0]['span']['start']==r['comparison_span']['start'] and cells[-1]['span']['end']==r['comparison_span']['end']
    assert all(l['span']['end']==rr['span']['start'] for l,rr in zip(cells,cells[1:]))
    for cell in cells:
        a,b=f(cell['span']['start']),f(cell['span']['end'])
        expected={sid for sid,s in sounds.items() if f(s['span']['start'])<b and f(s['span']['end'])>a}
        assert set(cell['event_refs'])==expected
    for pair in r['pairs']:
        assert pair['selected'] is None and pair['ranking_weight'] is None
        for cell,comp in zip(cells,pair['cells']):
            ids=[i for refs in comp['event_buckets'].values() for i in refs]
            assert len(ids)==len(set(ids)) and set(ids)==set(cell['event_refs'])
    for sid,u in r['event_units'].items():assert u['original_span']==sounds[sid]['span']
    assert r['selected'] is None and not r['used_for_ranking']
    return {'passed':True,'cells':len(cells),'original_spans_and_all_event_time_partitions_checked':True}


def review(folder,xml,ir,results,title):
    pages,mapping=verified_pages(xml,ir);write(folder/'whole-score-render-validation.json',mapping)
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    payload=[];cards=[]
    for r in results:
        paths={p['path_ref']:p for p in r['paths']}
        for pair in r['pairs']:
            groups={k:set() for k in ('both_members','merged_only_member','split_only_member','neither_member','spelling_unresolved')}
            for cell in pair['cells']:
                for k,ids in cell['event_buckets'].items():groups[k].update(ids)
            # Whole noteheads cannot show sub-note duration changes. Keep mixed
            # classifications distinct, and disclose precise cells in the table.
            mixed={sid for sid in r['event_units'] if sum(sid in ids for ids in groups.values())>1}
            for ids in groups.values():ids.difference_update(mixed)
            groups['mixed']=mixed
            idx=len(payload);payload.append({k:sorted({n for sid in ids for n in sounds[sid]['source_note_ids']}) for k,ids in groups.items()})
            def labels(p):return ' → '.join('/'.join(rt['root_spelling'] for rt in seg['root_hypotheses'])+':'+seg['candidate']['label'].partition(':')[2] if seg['root_hypotheses'] else seg['candidate']['label']+' (철자 보류)' for seg in p['segments'])
            title_range=position(ir,r['core_span']['start'])+' → '+position(ir,r['core_span']['end'])+' 직전'
            details=''
            for cell,comp in zip(r['cells'],pair['cells']):
                notes=' / '.join(k+': '+', '.join(sounds[sid]['pitch']['spelling'] for sid in ids) for k,ids in comp['event_buckets'].items() if ids) or '기보상 모든 성부 쉼'
                region={'before':'앞(연장 가정)','core':'원 비교 범위','after':'뒤(연장 가정)'}[cell['region']]
                details+='<li>'+html.escape(position(ir,cell['span']['start'])+' → '+position(ir,cell['span']['end'])+' 직전 · '+region+' · '+notes)+'</li>'
            status={'context_unresolved':'문맥 조건 부족 · 보류','spelling_unresolved':'철자 미해결 · 보류','different_explanation_not_winner':'구성음 설명 차이 있음 · 승자 미선택','same_observed_membership_not_equivalent_harmony':'양쪽 모두 같은 구성음 설명 · 화성 해석은 미확정'}[pair['status']]
            cards.append('<article><button data-case="'+str(idx)+'">'+html.escape(title_range)+' — 악보에서 보기</button><p><b>유지 가설:</b> '+html.escape(labels(paths[pair['merged_ref']]))+'<br><b>교체 가설:</b> '+html.escape(labels(paths[pair['split_ref']]))+'</p><p>'+status+'</p><details><summary>정확한 시간별 설명</summary><ul>'+details+'</ul></details></article>')
    content=''.join('<section class="scorepage" id="page-'+str(i)+'"><h2>페이지 '+str(i)+'</h2>'+svg+'</section>' for i,svg in enumerate(pages,1))
    options=''.join('<option value="page-'+str(i)+'">페이지 '+str(i)+'</option>' for i in range(1,len(pages)+1))
    style='body{font:16px system-ui;margin:0;background:#eef2f6;color:#183044}header{padding:16px}main{display:grid;grid-template-columns:340px minmax(0,1fr);gap:14px;padding:14px}aside{max-height:90vh;overflow:auto;position:sticky;top:8px}article,.scorepage{background:white;padding:12px;margin-bottom:14px}button{padding:10px;cursor:pointer}p,li{line-height:1.6}.scorepage svg{width:100%;height:auto}.both_members{fill:#1b8a5a!important;color:#1b8a5a!important}.merged_only_member{fill:#1971c2!important;color:#1971c2!important}.split_only_member{fill:#c05600!important;color:#c05600!important}.neither_member{fill:#c0392b!important;color:#c0392b!important}.spelling_unresolved,.mixed{fill:#8e44ad!important;color:#8e44ad!important}@media(max-width:850px){main{display:block}aside{position:static;max-height:none}}'
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · 전체 악장 검토</title><style>'+style+'</style><header><a href="../../index.html">사례 목록</a><h1>'+html.escape(title)+' · 전체 악장</h1><p>악보는 전체를 표시합니다. 분석 비교는 왼쪽의 검토 구간에만 있습니다. 원자료 화성 주석과 새 실험을 혼동하지 않도록 원본 harmony 표시는 숨겼습니다.</p><p>초록=양쪽 구성음 · 파랑=유지 가설에서만 · 주황=교체 가설에서만 · 빨강=양쪽 비구성음(비화성음 확정 아님) · 보라=철자 보류 또는 시간에 따라 소속이 바뀌는 한 음표.</p><p>앞뒤 1분모박은 첫/끝 화음을 연장해 본 가정입니다. 큰 화음의 높은 구성음 일치율을 정답 점수로 사용하지 않습니다.</p><label>전체 악장 페이지 이동 <select id="page-select">'+options+'</select></label> <a href="'+html.escape(xml.name)+'">원 MusicXML</a> · <a href="path-explanation.json">전체 계산 근거</a></header><main><aside>'+''.join(cards)+'</aside><div>'+content+'</div></main><script>const caseNotes='+json.dumps(payload)+';'+r'''
const colors=['both_members','merged_only_member','split_only_member','neither_member','spelling_unresolved','mixed'];
document.querySelectorAll('[data-case]').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.scorepage .note').forEach(n=>n.classList.remove(...colors));
 const p=caseNotes[+b.dataset.case];let first=null;
 for(const n of document.querySelectorAll('.scorepage .note')){const id=n.dataset.id||n.id;
  for(const color of colors)if(p[color].includes(id)){n.classList.add(color);first=first||n;}}
 if(first){first.scrollIntoView({block:'center',behavior:'smooth'});document.querySelector('#page-select').value=first.closest('.scorepage').id;}
}));
document.querySelector('#page-select').addEventListener('change',e=>document.getElementById(e.target.value).scrollIntoView({block:'start',behavior:'smooth'}));
</script></html>'''
    (folder/'whole-score.html').write_text(page,encoding='utf-8')
    return {'page_count':len(pages),'rendered_notes':mapping['rendered_canonical_id_count'],'whole_movement':True}


def build(source,output):
    if output.exists():raise ValueError('choose_new_revision')
    output.mkdir(parents=True);old=load(source/'report.json');report={'version':VERSION,'real':[],'controls':[],'production_modified':False,'accuracy_measured':False}
    write(output/'run-contract.json',{'source':str(source.resolve()),'source_sha256':digest(source/'report.json'),'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    for row in old['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id']
        if digest(src/'temporal-context.json')!=row['result_sha256'] or any(digest(src/n)!=h for n,h in row['prior_sha256'].items()):raise ValueError('prior_inputs_changed')
        provenance=load(src/'case-provenance.json')
        if any(provenance[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not provenance['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible_case')
        hashes={str(p.relative_to(src)):digest(p) for p in src.rglob('*') if p.is_file()};shutil.copytree(src,dst)
        ir=load(dst/'candidate_revision_ir.json')
        context_rows=unique_records([{'candidate_ref':r['candidate_ref'],'context_span':r['context_span']} for r in load(dst/'voice-revision-audit.json')['runs']],'candidate_ref')
        contexts={k:r['context_span'] for k,r in context_rows.items()}
        raw_candidates=[c for run in load(dst/'comparison.json')['runs'] for c in run['temporal']['alternatives']]
        candidates=unique_records(raw_candidates,'evidence_id')
        results=[explain(ir,c,contexts[cid]) for cid,c in sorted(candidates.items())];checks=[verify(ir,r) for r in results]
        write(dst/'path-explanation.json',{'version':VERSION,'records':results})
        xml=dst/Path(provenance['manifest_entry']['score_source_path']).name
        rendered=review(dst,xml,ir,results,row['title'])
        assert all(digest(src/n)==h and digest(dst/n)==h for n,h in hashes.items())
        statuses=dict(Counter(p['status'] for r in results for p in r['pairs']))
        report['real'].append({'case_id':row['case_id'],'title':row['title'],'candidates':len(results),'input_candidate_rows':len(raw_candidates),'identical_duplicates_collapsed':len(raw_candidates)-len(results),'pair_statuses_not_votes':statuses,'verification':checks,'rendering':rendered,'prior_sha256':hashes,'result_sha256':digest(dst/'path-explanation.json'),'page':str((dst/'whole-score.html').relative_to(output)).replace('\\','/')})
        print(row['title'],statuses,rendered,flush=True)
    for kind in KINDS:
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/'controls'/(kind+'-'+name);dst.mkdir(parents=True);case=fixture(kind,tr,scale);xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            expected=Counter((pitch.Pitch(e['pitch']).step,int(pitch.Pitch(e['pitch']).accidental.alter) if pitch.Pitch(e['pitch']).accidental else 0,pitch.Pitch(e['pitch']).octave,f(e['start'])) for e in case['events'])
            actual=Counter((s['pitch']['step'],f(s['pitch']['alter']),s['pitch']['octave'],f(s['span']['start'])) for s in ir['sounding_events'])
            if expected!=actual:raise ValueError('spelling_roundtrip_failed')
            r=explain(ir,case['candidate'],case['context']);checked=verify(ir,r);pair=r['pairs'][0]
            if pair['status']!=case['expected_status']:raise ValueError('control_failed:'+kind+name+pair['status'])
            sig={region:{k:f(v)/scale for k,v in counts.items()} for region,counts in pair['diagnostic_pc_quarter_exposure'].items()}
            if baseline is None:baseline=sig
            elif sig!=baseline:raise ValueError('transposition_or_scaling_failed')
            for n,data in [('fixture.json',case),('canonical_music_ir.json',ir),('path-explanation.json',{'records':[r]})]:write(dst/n,data)
            # Standard adapter lacks enriched XML-reference fields needed by the
            # strict real-score renderer; controls are preserved as XML+IR here.
            report['controls'].append({'case_id':kind+'-'+name,'status':pair['status'],'verification':checked,'source_sha256':digest(xml),'ir_sha256':digest(dst/'canonical_music_ir.json')})
    write(output/'report.json',report);write(output/'verification.json',{'passed':True,'original_files_unchanged':True,'real_cases':len(report['real']),'controls':len(report['controls'])})
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r['title'])+' — 전체 악장 '+str(r['rendering']['page_count'])+'페이지</a></li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>전체 악장 화음 가설 검토</title><h1>전체 악장에서 유지/교체 가설 비교</h1><p>분석은 선택된 검토 구간에만 있습니다. 운영 결과 및 정답 선택은 변경하지 않았습니다.</p><ul>'+links+'</ul><a href="report.json">계산 보고서</a></html>',encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
