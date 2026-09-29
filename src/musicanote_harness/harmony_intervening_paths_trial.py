"""Frozen real paths and authored, chord-conditioned MusicXML controls."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
import json
from pathlib import Path
import shutil

from music21 import converter, pitch
from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter, q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_figure_trial import fixture_xml
from .harmony_surface import TEMPLATES, PITCH_NAMES
from .engraving import musicxml_with_canonical_ids
from .source_enrichment import enrich_from_mapped_musicxml
from .source_note_mapping_audit import xml_inventory
from .harmony_delayed_links import observe
from .harmony_link_counterevidence import assess as counters
from .harmony_intervening_paths import assess, VERSION
from .harmony_polyphonic_trial import render
from .harmony_ownership_diagnostic_review import position

KINDS = ('unfolding', 'passing', 'neighbor', 'unexplained', 'enharmonic', 'gapped', 'other_chord', 'restart')
# UI language is Korean; pitch/chord names use the normal text font, not Roman numerals.
TAGS = {'chord_member_unfolding_compatible': '화음 구성음의 펼침과 양립',
        'local_ornament_geometry_compatible': '경과·보조 진행 모양과 조건부 양립'}


def fixture(kind, transpose=0, scale=F(1)):
    names = {'unfolding': ['C4', 'E4', 'G4'], 'passing': ['C4', 'D4', 'E4'],
             'neighbor': ['E4', 'F4', 'E4'], 'unexplained': ['C4', 'F#4', 'G4'],
             'enharmonic': ['C4', 'C##4', 'E4'], 'gapped': ['C4', 'D4', 'E4'],
             'other_chord': ['E4', 'F4', 'E4'], 'restart': ['C4', 'D4', 'E4']}[kind]
    specs = [('B3', F(0), F(1), '1'), ('C3', F(0), F(2), '2')]
    if kind == 'restart':
        specs = [(p, F(i, 4), F(1, 4), '1') for i, p in enumerate(['C4', 'D4', 'E4'])] + [('B3', F(3, 4), F(1, 4), '1'), ('C3', F(0), F(2), '2')]
    for i, p in enumerate(names):
        t = F(5+i, 4) + (F(1, 4) if kind == 'gapped' and i else 0)
        specs.append((p, t, F(1, 4), '1'))
    root = ((5 if kind == 'other_chord' else 0) + transpose) % 12
    expected = ['chord_member_unfolding_compatible'] if kind == 'unfolding' else ['local_ornament_geometry_compatible'] if kind in ('passing', 'neighbor', 'restart') else []
    return {'kind': kind, 'scale': q(scale), 'beat_type': int(4/scale), 'transpose': transpose,
        'events': [{'pitch': (pitch.Pitch(p) if transpose == 0 else pitch.Pitch(p).transpose('M2')).nameWithOctave, 'start': q(t*scale), 'duration': q(d*scale), 'voice': v} for p,t,d,v in specs],
        'candidate_condition': {'root': root, 'label': PITCH_NAMES[root]+':major', 'pcs': sorted((root+i)%12 for i in dict(TEMPLATES)['major'])},
        'expected_tags': expected, 'oracle': 'authored_conditional_contract_not_inferred_harmony_or_gold_NCT'}


def verify(ir, prior, result):
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    notes = {n['note_id']: n for n in ir['note_events']}
    assert len(prior['records']) == len(result['records'])
    for old, r in zip(prior['records'], result['records']):
        assert old['source_refs'] == r['source_refs'] and old['review_reasons'] == r['prior_review_reasons']
        assert r['selected'] is None and not any(r[k] for k in ('voice_connection_confirmed','nct_confirmed','independent_resolution_vote_allowed','used_for_ranking'))
        assert r['all_intervening_refs_preserved']
        ids = {s['event_ref'] for s in r['events']}
        assert set(old['intervening_attack_refs']) <= ids
        src = sounds[r['source_refs'][0]]; n = notes[src['source_note_ids'][0]]
        a,b = f(r['span']['start']), f(r['span']['end'])
        expected = {s['sounding_event_id'] for s in sounds.values() if s['source_note_ids']
                    and all((notes[i].get('part_id'),notes[i].get('voice_id')) == (n['part_id'],n['voice_id']) for i in s['source_note_ids'])
                    and f(s['span']['start']) < b and f(s['span']['end']) > a}
        assert ids == expected
        for event in r['events']:
            s = sounds[event['event_ref']]
            assert event['span'] == s['span'] and event['pitch'] == s['pitch'] and event['source_note_ids'] == s['source_note_ids']
        for e in r['conditional_explanations']:
            if e['compatible_patterns']:
                assert not r['abstention_reasons'] and e['arrival_covered'] and e['coherent_root_spellings']
            if 'chord_member_unfolding_compatible' in e['compatible_patterns']:
                assert len({sounds[i]['pitch']['midi_pitch']%12 for i in r['arrival_event_refs']}) >= 3
                assert all(m['pc_member'] for m in e['membership']) and not r['arrival_gaps']
            for o in e['conditional_ornaments']:
                l,m,t = [sounds[i] for i in o['event_refs']]
                assert f(l['span']['end']) == f(m['span']['start']) and f(m['span']['end']) == f(t['span']['start'])
                pcs=e['candidate']['pcs']
                assert l['pitch']['midi_pitch']%12 in pcs and t['pitch']['midi_pitch']%12 in pcs and m['pitch']['midi_pitch']%12 not in pcs
                assert o['nct_label'] is None
    return {'passed': True, 'paths_checked': len(result['records']), 'all_original_notes_and_warnings_preserved': True}


def panel(ir, result, preferred):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};payload=[];rows=[]
    chosen=[r for r in result['records'] if tuple(r['source_refs']) in preferred]
    if not chosen:
        chosen=[r for r in result['records'] if any(e['compatible_patterns'] for e in r['conditional_explanations'])] or result['records']
    for i,r in enumerate(chosen):
        middle=set(r['arrival_event_refs'])-set(r['source_refs'])
        payload.append({side:[n for sid in ids for n in sounds[sid]['source_note_ids']] for side,ids in [('source',r['source_refs'][:1]),('target',r['source_refs'][1:]),('held',sorted(middle))]})
        path=' → '.join(' + '.join(sounds[s]['pitch']['spelling'].replace('-','♭') for s in g['event_refs']) for g in r['attack_groups'])
        path += ' / 출발 뒤 공백 '+str(f(r['initial_gap']['end'])-f(r['initial_gap']['start']))+' quarter'
        if r['arrival_gaps']:path+=' / 도착 음군 내부에도 공백 '+str(len(r['arrival_gaps']))+'개'
        reasons=[]
        for e in r['conditional_explanations']:
            tags=' / '.join(TAGS[t] for t in e['compatible_patterns']) or ('문맥·철자·성부 조건 부족' if e['status'].startswith('abstain') else '이번 조건으로 설명 미확정')
            label=e['candidate']['label']
            if e['coherent_root_spellings']:label='/'.join(e['coherent_root_spellings'])+':'+label.partition(':')[2]
            reasons.append(html.escape(label+' 가정: '+tags))
        reasons=list(dict.fromkeys(reasons))
        if not reasons:reasons=['대응하는 저장 화음 후보 없음 · 새 화음을 추정하지 않음']
        if r['earlier_target_refs']:reasons.append('목표음이 앞에서 이미 나옴: 뒤 재등장은 별도 해결 아님')
        if r['restart_alternative']:reasons.append('이전 음형 재등장: 새 시작 대안도 유지')
        if r['abstention_reasons']:reasons.append('경로 보류: '+html.escape(', '.join(r['abstention_reasons'])))
        target=sounds[r['source_refs'][1]]
        rows.append('<tr><td><button data-path="'+str(i)+'">경로 '+str(i+1)+' · 도착 '+html.escape(position(ir,target['span']['start']))+'</button><p>'+html.escape(path)+'</p></td><td>'+'<br>'.join(reasons)+'</td></tr>')
    body='<table><tr><th>원음 순서 (+는 동시음)</th><th>화음 후보를 가정한 설명 · 확정 아님</th></tr>'+''.join(rows)+'</table>'
    if len(rows)>8:body='<details><summary>'+str(len(rows))+'경로 펼치기</summary>'+body+'</details>'
    extra='<section id="ordered-path"><h2>중간 음을 생략하지 않은 경로 설명</h2><p>파랑=출발, 주황=도착, 보라=중간 도착음. 쉼 뒤 음들이 화음 구성음이어도 앞 음의 해결로 확정하지 않습니다. 경과·보조 모양은 화음 가정에 따른 후보이며 비화성음 정답이 아닙니다.</p><p>우선 검토 경로 '+str(len(chosen))+'개 / 전체 '+str(len(result['records']))+'개. 같은 설명의 겹치는 창은 화면에서 묶었으며 독립 투표가 아닙니다. 음명 화음 표기는 조성·기능 로마자 판정이 아닙니다.</p>'+body+'<a href="../path-explanations.json">원음·가정·기권 근거 JSON</a></section>'
    script='<script>const orderedPaths='+json.dumps(payload)+';'+r'''
document.querySelectorAll('[data-path]').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.pl-source,.pl-target,.pl-held').forEach(e=>e.classList.remove('pl-source','pl-target','pl-held'));
 const g=orderedPaths[+b.dataset.path];let first=null;
 for(const e of document.querySelectorAll('.system [data-id],.system [id]')){
  const id=e.dataset.id||e.id;for(const s of ['source','target','held'])if(g[s].includes(id)){e.classList.add('pl-'+s);first=first||e;}
 }if(first)first.closest('.system').scrollIntoView({block:'center',behavior:'smooth'});
}));</script>'''
    return extra,script


def build(source, output):
    if output.exists():raise ValueError('choose_new_output_revision')
    output.mkdir(parents=True)
    prior=load(source/'report.json');report={'version':VERSION,'real':[],'controls':[],'accuracy_measured':False,'production_modified':False}
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'source_sha256':digest(source/'report.json'),
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'controls':KINDS,
        'policy':'frozen hypothesis conditioning; no gold labels, new ranking or note deletion'})
    for row in prior['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id']
        for name,sha in row['frozen_files_sha256'].items():
            if digest(src/name)!=sha:raise ValueError('prior_file_changed')
        prov=load(src/'case-provenance.json')
        if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible_case')
        frozen={str(p.relative_to(src)):digest(p) for p in src.rglob('*') if p.is_file()};shutil.copytree(src,dst)
        ir=load(dst/'candidate_revision_ir.json');delayed=load(dst/'delayed-links.json');old=load(dst/'counterevidence.json')
        contexts=[r['context_span'] for r in load(dst/'voice-revision-audit.json')['runs']]
        if observe(ir,contexts)!=delayed['observed']:raise ValueError('baseline_changed')
        fresh=counters(ir,delayed['observed'],contexts)
        if fresh['records']!=old['records']:raise ValueError('counterevidence_changed')
        result=assess(ir,delayed['observed'],old,delayed['roles'],contexts);checked=verify(ir,old,result)
        write(dst/'path-explanations.json',result)
        preferred={tuple(r['source_refs']) for r in old['compatible_endpoint_unique_pairs']}
        view=dst/'path-view';shutil.copytree(dst/'counter-view',view)
        extra,script=panel(ir,result,preferred);page=(view/'polyphonic.html').read_text(encoding='utf-8')
        page=page.replace('<section id="counterevidence">',extra+'<section id="counterevidence">').replace('</html>',script+'</html>')
        (view/'polyphonic.html').write_text(page,encoding='utf-8')
        assert all(digest(src/name)==sha and digest(dst/name)==sha for name,sha in frozen.items())
        report['real'].append({'case_id':row['case_id'],'title':row['title'],'summary':result['summary'],'verification':checked,
            'prior_sha256':frozen,'result_sha256':digest(dst/'path-explanations.json'),'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/')})
        print(row['title'],result['summary'],flush=True)
    for kind in KINDS:
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/'controls'/(kind+'-'+name);dst.mkdir(parents=True);case=fixture(kind,tr,scale);xml=dst/'score.musicxml'
            xml.write_text(fixture_xml(case),encoding='utf-8');ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            expected_spellings=Counter((pitch.Pitch(e['pitch']).step, int(pitch.Pitch(e['pitch']).accidental.alter) if pitch.Pitch(e['pitch']).accidental else 0,
                pitch.Pitch(e['pitch']).octave, f(e['start'])) for e in case['events'])
            actual_spellings=Counter((s['pitch']['step'], f(s['pitch']['alter']), s['pitch']['octave'], f(s['span']['start'])) for s in ir['sounding_events'])
            if expected_spellings!=actual_spellings:raise ValueError('control_spelling_roundtrip_failed')
            mapped,mapping=musicxml_with_canonical_ids(xml,ir)
            if mapping['unmatched_ir_note_ids']:raise ValueError('unmapped_control_note')
            enrich_from_mapped_musicxml(ir,mapped);raw=xml_inventory(xml)
            for ref in ir['source_references']:
                if ref.get('source_xpath') in raw:ref['source_part_id']=raw[ref['source_xpath']]['part']
            contexts=[{'start':q(0),'end':q(4*scale)}];obs=observe(ir,contexts)
            source_midi=pitch.Pitch('B3').transpose(tr).midi;sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
            obs={**obs,'groups':[g for g in obs['groups'] if f(g['time'])==scale and any(sounds[i]['pitch']['midi_pitch']==source_midi for i in g['source_refs'])]}
            old=counters(ir,obs,contexts)
            roles=[{'candidate_ref':'authored_condition_not_gold','comparisons':[{'group_id':r['group_id'],'source_refs':r['source_refs'],'reading_type':'authored_condition','reading_index':0,
                'target_chord_context':{'span':{'start':q(scale),'end':q(3*scale)},'candidate':case['candidate_condition']}} for r in old['records']]}]
            result=assess(ir,obs,old,roles,contexts);checked=verify(ir,old,result)
            chosen=max(result['records'],key=lambda r:f(sounds[r['source_refs'][1]]['span']['start']))
            actual=chosen['conditional_explanations'][0]['compatible_patterns']
            if actual!=case['expected_tags'] or chosen['restart_alternative']!=(kind=='restart'):raise ValueError('control_mismatch:'+kind+name+str(actual))
            for file,data in [('fixture.json',case),('canonical_music_ir.json',ir),('delayed-links.json',obs),('counterevidence.json',old),('path-explanations.json',result)]:write(dst/file,data)
            view=dst/'path-view';view.mkdir();shutil.copyfile(xml,view/xml.name);render(view,view/xml.name,ir,contexts,obs,[],kind+' · 조건부 경로 대조')
            extra,script=panel(ir,result,{tuple(chosen['source_refs'])});page=(view/'polyphonic.html').read_text(encoding='utf-8').replace('href="../../index.html"','href="../../../index.html"').replace('href="polyphonic-links.json"','href="../delayed-links.json"')
            page=page.replace('<section><h2>동시 음군 대응 후보</h2>',extra+'<section><h2>기존 연결 후보</h2>').replace('</html>',script+'</html>');(view/'polyphonic.html').write_text(page,encoding='utf-8')
            report['controls'].append({'case_id':kind+'-'+name,'expected':case['expected_tags'],'observed':actual,'verification':checked,
                'file_sha256':{str(p.relative_to(dst)):digest(p) for p in dst.rglob('*') if p.is_file()},'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/')})
    write(output/'report.json',report);write(output/'verification.json',{'passed':True,'real':[r['verification'] for r in report['real']],
        'controls':[r['verification'] for r in report['controls']],'prior_files_unchanged':True,'baseline_reproduced':True})
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r.get('title',r['case_id']))+'</a></li>' for r in report['real']+report['controls'] if r in report['real'] or r['case_id'].endswith('-base'))
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>중간 음 경로 검증</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto}li,p{line-height:1.8}</style><h1>분산 구성음 · 장식 진행 · 재시작 대안</h1><p>화음 가정별 설명입니다. 같은 원음에 여러 해석이 가능하며, 자동 화성 판정은 변경하지 않았습니다. 대조 악보의 화음은 의도적으로 제공한 테스트 조건이지 자동으로 맞힌 정답이 아닙니다.</p><ul>'+links+'</ul><a href="report.json">결과 JSON</a></html>',encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
