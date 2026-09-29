"""Archive all-voice contrasts and explicit-condition MusicXML controls."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
import json
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET
from music21 import converter, pitch

from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter, q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_figure_trial import fixture_xml
from .engraving import musicxml_with_canonical_ids
from .source_enrichment import enrich_from_mapped_musicxml
from .source_note_mapping_audit import xml_inventory
from .harmony_delayed_links import observe
from .harmony_link_counterevidence import assess as counters
from .harmony_intervening_paths import assess
from .harmony_path_contrast import compare, VERSION
from .harmony_surface import TEMPLATES, PITCH_NAMES
from .harmony_polyphonic_trial import render
from .harmony_ownership_diagnostic_review import position

KINDS=('common','held_E','held_Fsharp','both','neither_C','enharmonic')
STATUS={'no_observed_membership_difference':'관측된 구성음 소속 차이 없음',
        'observed_membership_difference_not_winner':'구성음 소속 차이 있음 · 승자 미확정',
        'spelling_unresolved':'철자 가정 미해결 · 선택 보류',
        'context_or_voice_unresolved':'성부·문맥 미해결 · 선택 보류'}


def control_xml(case):
    """Written accidentals are explicit as well as the sounding <alter>."""
    root=ET.fromstring(fixture_xml(case))
    labels={-2:'flat-flat',-1:'flat',1:'sharp',2:'double-sharp'}
    for note in root.findall('.//note'):
        alter=note.findtext('pitch/alter')
        if alter is not None and int(alter) in labels:
            ET.SubElement(note,'accidental').text=labels[int(alter)]
    return ET.tostring(root,encoding='unicode',xml_declaration=True)


def fixture(kind,tr=0,scale=F(1)):
    specs=[('E4',0,1,'1'),('G#3',F(5,4),F(1,4),'1'),('D3',F(3,2),F(1,4),'1'),('B3',F(7,4),F(1,4),'1')]
    additions={'common':[],'held_E':['E5'],'held_Fsharp':['F#4'],'both':['E5','F#4'],'neither_C':['C5'],'enharmonic':['F-5']}[kind]
    specs += [(p,1,1,str(i+2)) for i,p in enumerate(additions)]
    chords=[]
    for root,quality in [(4,'dominant7'),(8,'half-diminished7')]:
        r=(root+tr)%12;chords.append({'root':r,'label':PITCH_NAMES[r]+':'+quality,'pcs':sorted((r+i)%12 for i in dict(TEMPLATES)[quality])})
    return {'kind':kind,'scale':q(scale),'beat_type':int(4/scale),'transpose':tr,
        'events':[{'pitch':(pitch.Pitch(p) if tr==0 else pitch.Pitch(p).transpose('M2')).nameWithOctave,'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in specs],
        'conditions':chords,'expected_status':'spelling_unresolved' if kind=='enharmonic' else 'observed_membership_difference_not_winner' if kind in ('held_E','held_Fsharp','both') else 'no_observed_membership_difference',
        'oracle':'authored_comparison_conditions_not_automatically_inferred_harmony'}


def verify(ir,paths,result):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};old={r['path_id']:r for r in paths['records']}
    assert len(result['records'])==len(old)
    for r in result['records']:
        a,b=f(r['comparison_span']['start']),f(r['comparison_span']['end'])
        expected={sid for sid,s in sounds.items() if f(s['span']['start'])<b and f(s['span']['end'])>a}
        assert {e['event_ref'] for e in r['all_voice_events']}==expected
        assert r['prior_review_reasons']==old[r['path_id']]['prior_review_reasons'] and r['selected'] is None and not r['used_for_ranking']
        for fact in r['all_voice_events']:
            s=sounds[fact['event_ref']]
            assert f(fact['overlap_span']['start'])==max(a,f(s['span']['start']))
            assert f(fact['overlap_span']['end'])==min(b,f(s['span']['end']))
            assert result['event_units'][fact['unit_ref']]['original_span']==s['span']
        cs={c['candidate_key']:c for c in r['conditions']}
        for pair in r['pairs']:
            assert pair['selected'] is None and pair['ranking_weight'] is None and not pair['independent_vote']
            buckets=pair['event_buckets'];flat=[sid for ids in buckets.values() for sid in ids]
            assert len(flat)==len(set(flat)) and set(flat)==expected
            l,rhs=cs[pair['left']],cs[pair['right']]
            for name,lm,rm in [('shared_member',True,True),('left_member_only',True,False),('right_member_only',False,True),('neither_member',False,False)]:
                for sid in buckets[name]:
                    pc=sounds[sid]['pitch']['midi_pitch']%12
                    assert (pc in l['candidate']['pcs'])==lm and (pc in rhs['candidate']['pcs'])==rm
            assert set(pair['shared_pattern_refs'])==set(l['pattern_signatures'])&set(rhs['pattern_signatures'])
    return {'passed':True,'paths_checked':len(old),'same_window_all_voices_checked':True,'no_selection_or_independent_vote':True}


def panel(ir,result):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};payload=[];sections=[];seen=set()
    ordered=sorted(result['records'],key=lambda r:(not any(p['shared_pattern_refs'] for p in r['pairs']),
        f(r['comparison_span']['start']),-f(r['comparison_span']['end'])))
    for row in ordered:
        cs={c['candidate_key']:c for c in row['conditions']}
        for pair in row['pairs']:
            sig=json.dumps([row['comparison_span'],pair],sort_keys=True)
            if sig in seen:continue
            seen.add(sig);i=len(payload);b=pair['event_buckets']
            payload.append({side:[n for sid in b[k] for n in sounds[sid]['source_note_ids']] for side,k in [('source','left_member_only'),('target','right_member_only'),('held','shared_member')]})
            def label(c):
                roots=list(c['root_spelling_support'])
                return ('/'.join(roots)+':'+c['candidate']['label'].partition(':')[2]) if roots else c['candidate']['label']+' (철자 미확정)'
            def names(ids):return ', '.join(sounds[s]['pitch']['spelling'].replace('-','♭') for s in ids) or '없음'
            title=position(ir,row['comparison_span']['start'])+' → '+position(ir,row['comparison_span']['end'])+' 직전'
            missing={side:', '.join(PITCH_NAMES[pc] for pc in cs[pair[key]]['unobserved_member_pcs']) or '없음' for side,key in [('A','left'),('B','right')]}
            sections.append('<article><button data-contrast="'+str(i)+'">'+html.escape(title)+'</button><p><b>A: '+html.escape(label(cs[pair['left']]))+'</b> / <b>B: '+html.escape(label(cs[pair['right']]))+'</b></p><p>'+STATUS[pair['status']]+'</p><ul><li>양쪽 공통 구성음(보라): '+html.escape(names(b['shared_member']))+'</li><li>A에서만 구성음(파랑): '+html.escape(names(b['left_member_only']))+'</li><li>B에서만 구성음(주황): '+html.escape(names(b['right_member_only']))+'</li><li>양쪽 모두 비구성음 — NCT 확정 아님: '+html.escape(names(b['neither_member']))+'</li><li>철자 판단 보류: '+html.escape(names(b['spelling_unresolved']))+'</li></ul><p>이 범위에서 미출현한 구성음(대표 음명): A '+html.escape(missing['A'])+' / B '+html.escape(missing['B'])+'</p><p>양쪽 공통 음형 근거 '+str(len(pair['shared_pattern_refs']))+'개 · 독립 투표 아님. 미출현 구성음은 생략 가능성을 남깁니다.</p></article>')
    body=''.join(sections) or '<p>같은 전체 도착 범위를 덮는 서로 다른 화음 후보가 둘 이상 없어 비교를 보류했습니다.</p>'
    if len(sections)>4:body=''.join(sections[:4])+'<details><summary>나머지 '+str(len(sections)-4)+'개 같은 시간창 비교 펼치기</summary>'+''.join(sections[4:])+'</details>'
    extra='<section id="all-voice-contrast"><h2>이번 비교: 다른 성부까지 보면 후보가 구별되는가?</h2><p>동일한 시간 범위의 모든 성부를 비교합니다. 파랑=A에서만 구성음, 주황=B에서만 구성음, 보라=공통 구성음. 구성음 소속 차이는 화음 정답·독립 해결의 증명이 아닙니다. 이전 패널의 색 범례와 다릅니다.</p>'+body+'<a href="../path-contrast.json">전체 비교·시간·음표 ID</a></section>'
    script='<script>const contrastNotes='+json.dumps(payload)+';'+r'''
document.querySelectorAll('[data-contrast]').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.pl-source,.pl-target,.pl-held').forEach(e=>e.classList.remove('pl-source','pl-target','pl-held'));
 const g=contrastNotes[+b.dataset.contrast];let first=null;
 for(const e of document.querySelectorAll('.system [data-id],.system [id]')){const id=e.dataset.id||e.id;
  for(const s of ['source','target','held'])if(g[s].includes(id)){e.classList.add('pl-'+s);first=first||e;}}
 if(first)first.closest('.system').scrollIntoView({block:'center',behavior:'smooth'});
}));</script>'''
    return extra,script


def build(source,output):
    if output.exists():raise ValueError('choose_new_revision')
    output.mkdir(parents=True);prior=load(source/'report.json');report={'version':VERSION,'real':[],'controls':[],'accuracy_measured':False,'production_modified':False}
    write(output/'run-contract.json',{'source':str(source.resolve()),'source_sha256':digest(source/'report.json'),'version':VERSION,
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'control_types':KINDS,'no_automatic_selection':True})
    for row in prior['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id']
        if digest(src/'path-explanations.json')!=row['result_sha256']:raise ValueError('prior_result_changed')
        if any(digest(src/n)!=h for n,h in row['prior_sha256'].items()):raise ValueError('prior_input_changed')
        p=load(src/'case-provenance.json')
        if any(p[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not p['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible_case')
        frozen={str(p.relative_to(src)):digest(p) for p in src.rglob('*') if p.is_file()};shutil.copytree(src,dst)
        ir=load(dst/'candidate_revision_ir.json');paths=load(dst/'path-explanations.json');d=load(dst/'delayed-links.json');ce=load(dst/'counterevidence.json')
        contexts=[r['context_span'] for r in load(dst/'voice-revision-audit.json')['runs']]
        if assess(ir,d['observed'],ce,d['roles'],contexts)!=paths:raise ValueError('path_baseline_changed')
        result=compare(ir,paths);checked=verify(ir,paths,result);write(dst/'path-contrast.json',result)
        view=dst/'contrast-view';shutil.copytree(dst/'path-view',view);extra,script=panel(ir,result)
        page=(view/'polyphonic.html').read_text(encoding='utf-8').replace('<section id="ordered-path">',extra+'<section id="ordered-path">').replace('</html>',script+'</html>')
        (view/'polyphonic.html').write_text(page,encoding='utf-8')
        assert all(digest(src/n)==h and digest(dst/n)==h for n,h in frozen.items())
        report['real'].append({'case_id':row['case_id'],'title':row['title'],'summary':result['summary'],'verification':checked,'prior_sha256':frozen,
            'result_sha256':digest(dst/'path-contrast.json'),'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/')})
        print(row['title'],result['summary'],flush=True)
    for kind in KINDS:
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/'controls'/(kind+'-'+name);dst.mkdir(parents=True);case=fixture(kind,tr,scale);xml=dst/'score.musicxml'
            xml.write_text(control_xml(case),encoding='utf-8');ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            expected=Counter((pitch.Pitch(e['pitch']).step,int(pitch.Pitch(e['pitch']).accidental.alter) if pitch.Pitch(e['pitch']).accidental else 0,pitch.Pitch(e['pitch']).octave,f(e['start'])) for e in case['events'])
            actual=Counter((s['pitch']['step'],f(s['pitch']['alter']),s['pitch']['octave'],f(s['span']['start'])) for s in ir['sounding_events'])
            if expected!=actual:raise ValueError('spelling_roundtrip_failed')
            mapped,mapping=musicxml_with_canonical_ids(xml,ir)
            if mapping['unmatched_ir_note_ids']:raise ValueError('unmapped_note')
            enrich_from_mapped_musicxml(ir,mapped);raw=xml_inventory(xml)
            for ref in ir['source_references']:
                if ref.get('source_xpath') in raw:ref['source_part_id']=raw[ref['source_xpath']]['part']
            contexts=[{'start':q(0),'end':q(4*scale)}];obs=observe(ir,contexts);sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
            obs={**obs,'groups':[g for g in obs['groups'] if f(g['time'])==scale and any(sounds[i]['pitch']['midi_pitch']==64+tr for i in g['source_refs'])]}
            ce=counters(ir,obs,contexts);roles=[{'candidate_ref':'authored_conditions','comparisons':[{'group_id':r['group_id'],'source_refs':r['source_refs'],'reading_type':'condition','reading_index':i,
                'target_chord_context':{'span':{'start':q(0),'end':q(3*scale)},'candidate':c}} for r in ce['records'] for i,c in enumerate(case['conditions'])]}]
            paths=assess(ir,obs,ce,roles,contexts);result=compare(ir,paths);checked=verify(ir,paths,result)
            chosen=max(result['records'],key=lambda r:f(r['comparison_span']['end']));pair=chosen['pairs'][0]
            if pair['status']!=case['expected_status']:raise ValueError('control_status_mismatch:'+kind+name+pair['status'])
            if len(pair['shared_pattern_refs'])!=1:raise ValueError('common_pattern_not_deduplicated')
            for fn,data in [('fixture.json',case),('canonical_music_ir.json',ir),('paths.json',paths),('path-contrast.json',result),('delayed-links.json',obs)]:write(dst/fn,data)
            view=dst/'contrast-view';view.mkdir();shutil.copyfile(xml,view/xml.name);render(view,view/xml.name,ir,contexts,obs,[],kind+' · 같은 시간창 비교')
            extra,script=panel(ir,{'records':[chosen]});page=(view/'polyphonic.html').read_text(encoding='utf-8').replace('href="../../index.html"','href="../../../index.html"').replace('href="polyphonic-links.json"','href="../delayed-links.json"')
            page=page.replace('<section><h2>동시 음군 대응 후보</h2>',extra+'<section><h2>이전 연결 가설</h2>').replace('</html>',script+'</html>');(view/'polyphonic.html').write_text(page,encoding='utf-8')
            report['controls'].append({'case_id':kind+'-'+name,'observed':pair['status'],'expected':case['expected_status'],'verification':checked,
                'file_sha256':{str(p.relative_to(dst)):digest(p) for p in dst.rglob('*') if p.is_file()},'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/')})
    write(output/'report.json',report);write(output/'verification.json',{'passed':True,'real':[r['verification'] for r in report['real']],
        'controls':[r['verification'] for r in report['controls']],'previous_files_unchanged':True,'previous_paths_reproduced':True})
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r.get('title',r['case_id']))+'</a></li>' for r in report['real']+report['controls'] if r in report['real'] or r['case_id'].endswith('-base'))
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>화음 후보의 공통·구별 근거</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto}li,p{line-height:1.8}</style><h1>같은 시간·모든 성부의 후보 비교</h1><p>공통 구성음과 후보별 다른 구성음을 구별합니다. 화음 선택/정확도 향상은 아직 확정하지 않았습니다. 대조 악보의 두 화음은 작성한 시험 조건입니다.</p><ul>'+links+'</ul><a href="report.json">전체 결과</a></html>',encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
