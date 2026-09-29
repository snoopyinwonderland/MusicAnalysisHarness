"""Freeze inclusive candidates, attach contextual evidence and inspect on full score."""
import argparse
import json
from pathlib import Path
import shutil
from fractions import Fraction as F
from .formal_ir import q
from .harmony_joint import f
from .harmony_candidate_context import attach,VERSION
from .harmony_open_candidates import window
from .harmony_open_candidate_trial import make_page
from .harmony_shared_tone_trial import load
from .harmony_arpeggio_benchmark import digest,write,check_roundtrip
from .harmony_ownership_diagnostic_review import position
from .harmony_neighbor_contrast import compare as neighbor_contrast, VERSION as CONTRAST_VERSION


def control_cases(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    rows=[]
    for kind in ('resolution','wrong_direction'):
        destination=['E-3','E-4','B-4','G4','D-5'] if kind=='resolution' else ['E-3','G4','B-4','B-4','D-5']
        specs=[(p,0,2,str(i+1)) for i,p in enumerate(['B-3','D4','F4','A-4'])]+[(p,2,2,str(i+1)) for i,p in enumerate(destination)]
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            case={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in specs]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            proposals={'analysis_span':{'start':q(0),'end':q(4*scale)},'records':[window(ir,{'start':q(0),'end':q(2*scale)}),window(ir,{'start':q(2*scale),'end':q(4*scale)})]}
            result=attach(ir,proposals)
            left=next(c for c in result['records'][0]['candidates'] if c['root']==(10+tr)%12 and c['label'].endswith(':dominant7'))
            right=next(c for c in result['records'][1]['candidates'] if c['root']==(3+tr)%12 and c['label'].endswith(':dominant7'))
            edge=next(e for e in result['context_edges'] if e['source_candidate_ref']==left['candidate_id'] and e['target_candidate_ref']==right['candidate_id'])
            tags=sorted({t for support in edge['direct_voice_support'] for t in support['relations']})
            assert bool(tags)==(kind=='resolution')
            if baseline is None:baseline=tags
            else:assert tags==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',result)
            rows.append({'case':dst.name,'relations':tags,'passed':True,'xml_sha256':digest(xml),'ir_sha256':digest(dst/'canonical_music_ir.json')})
    return rows


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    frozen=load(source/'open-candidates.json');ir=load(source/'source-snapshot'/'canonical_music_ir.json')
    provenance=load(source/'source-snapshot'/'case-provenance.json');entry=provenance['manifest_entry'];revision=provenance['revision']
    if entry['split']!='train' or not entry['rights']['internal_research_use']:raise ValueError('ineligible_case')
    required={**revision['hashes'],Path(entry['score_source_path']).name:entry['score_sha256']}
    if any(digest(source/'source-snapshot'/n)!=h for n,h in required.items()):raise ValueError('source_changed')
    frozen_hash=digest(source/'open-candidates.json');output.mkdir(parents=True);(output/'windows').mkdir()
    shutil.copytree(source/'source-snapshot',output/'source-snapshot');shutil.copyfile(source/'open-candidates.json',output/'prior-open-candidates.json')
    write(output/'run-contract.json',{'version':VERSION,'prior_sha256':frozen_hash,'analysis_span':frozen['analysis_span'],
        'source_hashes':required,'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'scope':'same_train_first32_no_source_label_input'})
    result=attach(ir,frozen);byedge={e['edge_id']:e for e in result['context_edges']}
    result['neighbor_contrast_version']=CONTRAST_VERSION
    for r in result['records']:
        r['neighbor_contrast']=neighbor_contrast(ir,r)
        for contrast in r['neighbor_contrast']['records']:
            for stage in contrast['member_stages']:
                stage['display']=position(ir,stage['span']['start'])+' → '+position(ir,stage['span']['end'])+' 직전'
    for old,r in zip(frozen['records'],result['records']):
        assert old['span']==r['span'] and old['event_refs']==r['event_refs']
        assert len(old['candidates'])==len(r['candidates'])
        for oc,c in zip(old['candidates'],r['candidates']):assert {k:v for k,v in c.items() if k!='context_evidence'}==oc
    for i,r in enumerate(result['records']):
        # Window-local edge view; global references remain authoritative.
        refs={eid for c in r['candidates'] for side in ('following_edge_refs','preceding_edge_refs') for eid in c['context_evidence'][side]}
        details={eid:{**byedge[eid],**{side+'_display':position(ir,byedge[eid][side+'_span']['start'])+' → '+position(ir,byedge[eid][side+'_span']['end'])+' 직전' for side in ('source','target')}} for eid in sorted(refs)}
        write(output/'windows'/(str(i)+'.json'),{**r,'context_edge_details':details})
    write(output/'context-candidates.json',result)
    report={'version':VERSION,'analysis_span':result['analysis_span'],'candidate_count_unchanged':result['summary']['candidates'],
        **result['context_summary'],'voice_abstentions':result['voice_observations']['abstentions'],
        'xml_controls':control_cases(output/'controls'),'figure_xml_controls':figure_controls(output/'figure-controls'),
        'neighbor_contrast_version':CONTRAST_VERSION,
        'neighbor_contrast_window_occurrences':sum(len(r['neighbor_contrast']['records']) for r in result['records']),
        'contrast_xml_controls':contrast_controls(output/'contrast-controls'),
        'selected_harmony_changed':False,'accuracy_measured':False,'production_modified':False}
    write(output/'report.json',report);make_page(source/'source-snapshot',output,ir,result)
    page=(output/'whole-score.html').read_text(encoding='utf-8')
    page=page.replace('<h1>화성 후보 확장 실험 · 전체 악장</h1>','<h1>화성 후보의 해결·베이스 근거 · 전체 악장</h1>')
    anchor=" if(first){first.scrollIntoView"
    insert=r'''
 const evidence=c.context_evidence;const factorNames=['근음','3음','5음','7음'];const b=evidence.bass;
 let detail='\n\n구간 시작 최저음: '+(b.cells[0]?.bass_spellings.join(', ').replaceAll('-','♭')||'없음')+' / '+(b.onset_factor_index===null?'화음 내 역할 보류':factorNames[b.onset_factor_index]+' · '+['근음 위치','제1전위','제2전위','제3전위'][b.onset_factor_index]+' 가설')+'\n이는 전위 가설이며 구조적 베이스 확정이 아닙니다.';
 detail+='\n구간의 최저음 역할: '+b.observed_factor_indices.map(i=>factorNames[i]).join(', ');
 for(const [side,title] of [['preceding_edge_refs','앞 구간에서의 관계'],['following_edge_refs','뒤 구간과의 관계']]){
 const edges=evidence[side].map(id=>currentWindow.context_edge_details[id]);detail+='\n\n'+title+' '+edges.length+'개 (독립 투표 아님)';
 for(const edge of edges){const range=side==='following_edge_refs'?edge.target_display:edge.source_display;
 detail+='\n'+edge.source_label+' → '+edge.target_label+' ['+range+'] · '+(edge.direct_voice_support.length?edge.direct_voice_support.map(s=>s.source_pitch.replaceAll('-','♭')+'→'+s.target_pitch.replaceAll('-','♭')+(s.dependency_group?' (옥타브 중복·독립 근거 아님)':'')).join(', '):'근음 관계만 / 직접 해결 미확인')+' · 미관측 구성음 '+edge.source_missing_pcs.length+'/'+edge.target_missing_pcs.length;}}
 const figures=currentWindow.double_neighbor_evidence?.records||[];
 detail+='\n\n이중 보조음 형태 '+figures.length+'개';
 for(const figure of figures){const e=figure.candidate_explanations.find(e=>e.candidate_ref===c.candidate_id);
 const pitches=figure.event_refs.map(id=>currentWindow.event_units[id].pitch.spelling.replaceAll('-','♭')).join(' → ');
 detail+='\n'+pitches+' · '+(e?.conditional_role?'고정 화음 가정 아래 조건부 이중 보조음':e?.status==='incomplete_double_neighbor_hypothesis'?'이중 보조음 부분형 후보 · 선행 기준음 미확인':figure.abstention_reasons.length?'판정 보류: '+figure.abstention_reasons.join(', '):'이 후보에서 구성음/철자 조건 불충족');}
 const count=(p,group,state)=>(p.groups[group][state]?.event_refs||[]).length;
 for(const contrast of currentWindow.neighbor_contrast?.records||[]){
 const fixed=contrast.fixed_harmony_readings.find(h=>h.candidate_ref===c.candidate_id);if(!fixed)continue;
 detail+='\n\n화음 유지 / 구성음 진행 설명 비교 (자동 선택 아님)';
 detail+='\n유지 가정: 이 음형 밖의 다른 음 — 구성음 '+count(fixed.profile,'other','member')+', 미설명 '+count(fixed.profile,'other','nonmember_not_confirmed_nct')+', 철자 보류 '+count(fixed.profile,'other','spelling_unresolved');
 detail+='\n멜로디를 모두 구성음으로 설명할 때 최소 후보 변경 횟수: '+(contrast.minimum_label_changes_if_all_figure_notes_are_members??'계산 보류')+' (적을수록 좋다는 점수가 아님)';
 for(const stage of contrast.member_stages){
 const matching=stage.member_alternatives.filter(o=>count(o.profile,'other','nonmember_not_confirmed_nct')===0&&count(o.profile,'other','spelling_unresolved')===0);
 detail+='\n'+currentWindow.event_units[stage.focus_event_ref].pitch.spelling.replaceAll('-','♭')+' ['+stage.display+'] · 구성음 설명 후보 '+stage.member_alternatives.length+'개';
 detail+='\n'+(stage.member_alternatives.length&&!stage.member_alternatives[0].profile.other_event_evidence_present?'비교할 다른 음 없음 · 반주 적합도 대조 불가':'다른 음도 모두 구성음인 후보: '+(matching.length?matching.map(o=>o.label+' (미관측 '+o.profile.missing_member_pcs.length+(o.origin==='parent_window_hypothesis'?', 문맥 가설':'')+')').join(', '):'없음'));
 }
 detail+='\n시작/끝 문맥은 선택 구간 안에서만 비교합니다. 준비음이나 화음을 구간 밖으로 연장하지 않습니다.';
 }
 document.querySelector('#choice-info').textContent+=detail+'\nSecondary/종지 확정 또는 자동 순위 변경은 하지 않았습니다.';
 document.querySelector('aside').scrollTop=0;
'''
    if anchor not in page:raise ValueError('viewer_hook_missing')
    page=page.replace(anchor,insert+anchor,1)
    (output/'whole-score.html').write_text(page,encoding='utf-8')
    assert digest(source/'open-candidates.json')==frozen_hash and all(digest(output/'source-snapshot'/n)==h for n,h in required.items())
    write(output/'verification.json',{'passed':True,'source_unchanged':True,'all_candidates_and_costs_unchanged':True,'exact_spans_unchanged':True,'xml_controls_passed':6,'figure_xml_controls_passed':len(report['figure_xml_controls']),'contrast_xml_controls_passed':len(report['contrast_xml_controls'])})
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


def figure_controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    from .harmony_voice_figures import octave_links,double_neighbors
    rows=[]
    for kind in ('octave','double_neighbor','neighbor_rest','neighbor_suffix'):
        if kind=='octave':specs=[('D4',0,1,'1'),('D5',0,1,'1'),('E-4',1,1,'1'),('E-5',1,1,'1')]
        else:specs=[('A-3',0,4,'2'),('C4',0,4,'3'),('E-4',0,4,'4'),('A-4',0,F(1,2) if kind=='neighbor_rest' else 1,'1'),('G4',1,1,'1'),('B-4',2,1,'1'),('A-4',3,1,'1')]
        if kind=='neighbor_suffix':specs=[row for row in specs if not (row[0]=='A-4' and row[1]==0)]
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            case={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in specs]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            span={'start':q(0),'end':q(4*scale)}
            evidence=octave_links(ir,span) if kind=='octave' else double_neighbors(ir,window(ir,span))
            value=len(evidence['links']) if kind=='octave' else evidence['conditional_count']
            assert value==({'octave':2,'double_neighbor':1,'neighbor_rest':0,'neighbor_suffix':0}[kind]), (kind,name,value)
            if kind=='neighbor_suffix':assert any(e['status']=='incomplete_double_neighbor_hypothesis' for r in evidence['records'] for e in r['candidate_explanations'])
            if baseline is None:baseline=value
            else:assert value==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'evidence.json',evidence)
            rows.append({'case':dst.name,'passed':True,'count':value,'xml_sha256':digest(xml),'ir_sha256':digest(dst/'canonical_music_ir.json')})
    return rows


def contrast_controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    from .harmony_voice_figures import double_neighbors
    rows=[]
    for kind in ('held_triad','changing_chords'):
        if kind=='held_triad':specs=[('A-3',0,4,'2'),('C4',0,4,'3'),('E-4',0,4,'4'),('G5',0,1,'1'),('B-5',1,1,'1'),('A-5',2,2,'1')]
        else:specs=[('C3',0,1,'2'),('E-4',0,1,'3'),('G4',0,1,'4'),('G5',0,1,'1'),('E-3',1,1,'2'),('G4',1,1,'3'),('B-4',1,1,'4'),('B-5',1,1,'1'),('A-3',2,2,'2'),('C4',2,2,'3'),('E-4',2,2,'4'),('A-5',2,2,'1')]
        baseline=None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            case={'scale':q(scale),'beat_type':int(4/scale),'events':[{'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in specs]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(case),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            w=window(ir,{'start':q(0),'end':q(4*scale)});w['double_neighbor_evidence']=double_neighbors(ir,w)
            result=neighbor_contrast(ir,w);c=next(c for c in w['candidates'] if c['root']==(8+tr)%12 and c['label'].endswith(':major'))
            fixed=next(h for h in result['records'][0]['fixed_harmony_readings'] if h['candidate_ref']==c['candidate_id'])
            duration=f(fixed['profile']['groups']['other'].get('nonmember_not_confirmed_nct',{}).get('duration_quarters',q(0)))/scale
            assert (duration==0)==(kind=='held_triad')
            if baseline is None:baseline=duration
            else:assert duration==baseline
            assert result['selected'] is None
            write(dst/'canonical_music_ir.json',ir);write(dst/'contrast.json',result)
            rows.append({'case':dst.name,'passed':True,'normalized_other_residual_duration':q(duration),'xml_sha256':digest(xml)})
    return rows


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();build(a.source,a.output)
