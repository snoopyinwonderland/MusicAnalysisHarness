"""Reproducible multi-work member timing audit; no harmony reranking."""
import argparse
from pathlib import Path
from fractions import Fraction as F
import html
import json
import shutil
import re
from .formal_ir import q
from .harmony_joint import f
from .harmony_member_timeline import observe,VERSION
from .harmony_arpeggio_benchmark import digest,write,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_ownership_diagnostic_review import position


def audit(ir, records, page):
    """Check saved references and half-open timing against original IR, not summaries."""
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    rendered=set(re.findall(r'data-id="([^"]+)"[^>]*class="note"',page.read_text(encoding='utf-8')))
    used=set()
    for r in records:
        for sid,u in r['event_units'].items():
            s=sounds[sid]
            assert u['original_span']==s['span'] and u['source_note_ids']==s['source_note_ids']
            assert u['pitch']==s['pitch']
            used.update(u['source_note_ids'])
        for m in r['members']:
            times=[]
            for region,refs in m['refs_by_region'].items():
                lo,hi=(f(r['windows'][region]['span'][k]) for k in ('start','end'))
                expected=set()
                for sid,s in sounds.items():
                    p=s['pitch'];alter=f(p['alter'])
                    if alter.denominator!=1:continue
                    spelling=p['step']+('#'*int(alter) if alter>0 else 'b'*(-int(alter)))
                    if spelling==m['spelling'] and lo<hi and f(s['span']['start'])<hi and f(s['span']['end'])>lo:
                        expected.add(sid)
                assert set(refs)==expected
                if region=='inside':times=[max(lo,f(sounds[sid]['span']['start'])) for sid in refs]
            assert m['first_observed_inside']==(q(min(times)) if times else None)
        assert r['selected'] is None and not r['ranking_performed']
    assert used<=rendered, 'source notes missing from score rendering'
    return {'reference_timing_audit_passed':True,'referenced_notes':len(used),'rendered_notes':len(rendered)}


def controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_candidate_explanation import spelling_evidence
    from .harmony_path_contrast_trial import control_xml
    from .harmony_surface import PITCH_NAMES
    rows=[]
    specs={
        'arpeggio':[('C4',1,F(1,2),'1'),('E4',F(3,2),F(1,2),'1'),('G4',2,1,'1')],
        'vertical':[('C4',1,2,'1'),('E4',1,2,'2'),('G4',1,2,'3')],
        'future_member':[('C4',1,2,'1'),('E4',1,2,'2'),('G4',3,1,'3')],
        'held':[('C4',0,4,'1'),('E4',1,2,'2'),('G4',1,2,'3')],
        'reattack':[('C4',0,1,'1'),('C4',1,2,'1'),('C4',3,1,'1'),('E4',1,2,'2'),('G4',1,2,'3')],
        'enharmonic':[('C4',1,2,'1'),('F-4',1,2,'2'),('G4',1,2,'3')],
        'silence':[('C4',1,F(1,2),'1'),('E4',2,F(1,2),'1'),('G4',F(5,2),F(1,2),'1')]}
    for kind,events in specs.items():
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            case={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in events]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            c={'root':tr,'label':PITCH_NAMES[tr]+':major','pcs':[(i+tr)%12 for i in (0,4,7)]}
            context={'start':q(0),'end':q(4*scale)}
            roots=spelling_evidence(ir,context,c)['candidates']
            result=observe(ir,{'start':q(scale),'end':q(3*scale)},c,roots,context)
            complete=result['pooled_members_first_complete_at'];expected=2 if kind=='arpeggio' else F(5,2) if kind=='silence' else None if kind in ('future_member','enharmonic') else 1
            assert (f(complete)/scale if complete is not None else None)==expected
            assert bool(result['simultaneously_complete_cells'])==(kind in ('vertical','held','reattack'))
            signature=(len(result['missing_inside']),sum(m['missing_inside_but_seen_outside'] for m in result['members']),sum(len(m['held_across_start']) for m in result['members']))
            if baseline is None:baseline=signature
            else:assert signature==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',result)
            rows.append({'case':dst.name,'passed':True,'normalized_complete_at':q(expected) if expected is not None else None,'xml_sha256':digest(xml)})
    return rows


def review(src,dst,ir,records,title):
    original=(src/'whole-score.html').read_text(encoding='utf-8')
    begin=original.index('<section class="scorepage"');end=original.index('</div></main>',begin)
    score=original[begin:end];cards=[];payload=[]
    for i,r in enumerate(records):
        colors={k:set() for k in ('before','inside','after','crossing')}
        for m in r['members']:
            for region,refs in m['refs_by_region'].items():colors[region].update(refs)
        colors['crossing']={sid for sid in r['event_units'] if sum(sid in colors[k] for k in ('before','inside','after'))>1}
        for region in ('before','inside','after'):colors[region]-=colors['crossing']
        payload.append({color:sorted({n for sid in refs for n in r['event_units'][sid]['source_note_ids']}) for color,refs in colors.items()})
        p=lambda t:position(ir,t)
        rows=''
        for m in r['members']:
            cells=[]
            for region in ('before','inside','after'):
                refs=m['refs_by_region'][region]
                cells.append(', '.join(p(r['event_units'][sid]['original_span']['start'])+' '+r['event_units'][sid]['pitch']['spelling'].replace('-','♭') for sid in refs) or '미관측')
            rows+='<tr><th>'+html.escape(m['spelling'])+'</th>'+''.join('<td>'+html.escape(v)+'</td>' for v in cells)+'</tr>'
        complete=r['pooled_members_first_complete_at']
        cards.append('<article><button data-probe="'+str(i)+'">'+html.escape(r['candidate']['label']+' · '+p(r['candidate_span']['start'])+' → '+p(r['candidate_span']['end'])+' 직전')+'</button><p>구간 안에서 모은 구성음이 처음 갖춰진 시각: '+html.escape(p(complete) if complete else '갖춰지지 않음 / 철자 보류')+'</p><p>동시에 모두 울린 셀: '+str(len(r['simultaneously_complete_cells']))+' · 구간 안 미관측: '+html.escape(', '.join(r['missing_inside']) or '없음')+'</p><p>보류 조건: '+html.escape(', '.join(r['abstention_reasons']) or '없음 — 화음 유지/교체 확정은 아님')+'</p><table><tr><th>구성음</th><th>앞</th><th>구간 안</th><th>뒤</th></tr>'+rows+'</table></article>')
    style='body{margin:0;background:#edf2f7;color:#183044;font:15px system-ui}header{padding:16px}main{display:grid;grid-template-columns:420px minmax(0,1fr);gap:12px}aside{position:sticky;top:0;height:96vh;overflow:auto}article,.scorepage{background:white;padding:12px;margin:8px}svg{width:100%;height:auto}button{padding:10px;cursor:pointer}table{font-size:12px;border-collapse:collapse;width:100%}td,th{border:1px solid #ccd5df;padding:4px;overflow-wrap:anywhere}.mt-before{fill:#1971c2!important;color:#1971c2!important}.mt-inside{fill:#1b8a5a!important;color:#1b8a5a!important}.mt-after{fill:#c05600!important;color:#c05600!important}.mt-crossing{fill:#8e44ad!important;color:#8e44ad!important}@media(max-width:850px){main{display:block}aside{position:static;height:auto}}'
    script=r'''const payload=PAYLOAD;document.querySelectorAll('[data-probe]').forEach(b=>b.addEventListener('click',()=>{const colors=['before','inside','after','crossing'];const p=payload[+b.dataset.probe];let first=null;document.querySelectorAll('.scorepage .note').forEach(n=>{n.classList.remove(...colors.map(c=>'mt-'+c));for(const c of colors)if(p[c].includes(n.dataset.id||n.id)){n.classList.add('mt-'+c);first=first||n;}});if(first)first.scrollIntoView({block:'center',behavior:'smooth'});}));'''.replace('PAYLOAD',json.dumps(payload))
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(title)+' · 구성음 시간 추적</title><style>'+style+'</style><header><a href="../../index.html">목록</a><h1>'+html.escape(title)+' · 구성음의 실제 출현 시각</h1><p>파랑=앞 문맥 · 초록=구간 안 · 주황=뒤 문맥 · 보라=같은 sound가 경계를 넘어 지속. 후보 구성음의 관찰이며 확정 화성/비화성음 표시는 아닙니다.</p><p>뒤에서 나타난 음으로 앞 화음을 완성하거나, 모인 음을 모두 동시 화음으로 취급하지 않습니다. 각 표는 원래 onset을 표시합니다. 전체 악보를 표시하되 계산은 기존 고정 검토 구간만입니다.</p><a href="member-timeline.json">정확한 원음·시간·쉼·보류 근거</a></header><main><aside>'+''.join(cards)+'</aside><div>'+score+'</div></main><script>'+script+'</script></html>'
    (dst/'whole-score.html').write_text(page,encoding='utf-8')
    return {'pages':score.count('class="scorepage"'),'probes':len(records)}


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    old=load(source/'report.json');output.mkdir(parents=True)
    report={'version':VERSION,'real':[],'controls':[],'source_annotations_used':False,'production_modified':False,'accuracy_measured':False}
    write(output/'run-contract.json',{'source':str(source.resolve()),'source_report_sha256':digest(source/'report.json'),'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'selection':'all prior frozen path segments in the three existing train cases; no user-measure filtering'})
    for row in old['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id'];dst.mkdir(parents=True)
        if digest(src/'path-explanation.json')!=row['result_sha256']:raise ValueError('prior_result_changed')
        prov=load(src/'case-provenance.json')
        if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible_source')
        names=['candidate_revision_ir.json','path-explanation.json','case-provenance.json',Path(prov['manifest_entry']['score_source_path']).name]
        hashes={n:digest(src/n) for n in names}
        for n in names:
            expected=row['result_sha256'] if n=='path-explanation.json' else row['prior_sha256'][n]
            if hashes[n]!=expected:raise ValueError('frozen_input_changed:'+n)
        snapshot=dst/'source-snapshot';snapshot.mkdir()
        for n in names:shutil.copyfile(src/n,snapshot/n)
        ir=load(src/'candidate_revision_ir.json');seen={};records=[]
        for prior in load(src/'path-explanation.json')['records']:
            for path in prior['paths']:
                for segment in path['segments']:
                    key=json.dumps([segment['span'],segment['candidate'],segment['root_hypotheses'],prior['comparison_span']],sort_keys=True)
                    alias={'candidate_ref':prior['candidate_ref'],'path_ref':path['path_ref']}
                    if key in seen:records[seen[key]]['prior_refs'].append(alias);continue
                    result=observe(ir,segment['span'],segment['candidate'],segment['root_hypotheses'],prior['comparison_span'])
                    result['prior_refs']=[alias];seen[key]=len(records);records.append(result)
        write(dst/'member-timeline.json',{'version':VERSION,'records':records})
        source_page_hash=digest(src/'whole-score.html')
        rendered=review(src,dst,ir,records,row['title'])
        rendered.update(audit(ir,records,dst/'whole-score.html'))
        assert digest(src/'whole-score.html')==source_page_hash
        assert all(digest(src/n)==h and digest(snapshot/n)==h for n,h in hashes.items())
        report['real'].append({'case_id':row['case_id'],'title':row['title'],'probes':len(records),
            'pooled_complete':sum(r['pooled_members_first_complete_at'] is not None for r in records),
            'outside_only_member_observations':sum(m['missing_inside_but_seen_outside'] for r in records for m in r['members']),
            'abstaining_probes':sum(bool(r['abstention_reasons']) for r in records),'source_hashes':hashes,'rendering':rendered,
            'source_page_sha256':source_page_hash,
            'page':str((dst/'whole-score.html').relative_to(output)).replace('\\','/')})
    report['controls']=controls(output/'controls');write(output/'report.json',report)
    write(output/'verification.json',{'passed':True,'source_files_unchanged':True,'real_cases':len(report['real']),'xml_controls_passed':len(report['controls']),'automatic_selection_changed':False})
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r['title'])+'</a> — '+str(r['probes'])+'개 기존 가설 구간</li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>화음 구성음 시간 추적</h1><p>베토벤/모차르트의 기존 세 사례를 그대로 사용했습니다. 관측 결과이며 자동 화음 선택은 변경하지 않았습니다.</p><p>표본 제한: 구성음이 모인 기존 후보에서 출발하므로 누락 구성음 검출률이나 일반 정확도를 측정한 표본이 아닙니다. 구간 밖 구성음을 빌려 오지 않는 동작은 별도 MusicXML 대조군으로 검사했습니다.</p><ul>'+links+'</ul><a href="report.json">검증 보고서</a></html>',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
