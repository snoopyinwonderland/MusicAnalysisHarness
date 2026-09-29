"""Paired adversarial controls plus frozen real-score counterevidence review."""
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
from .harmony_figure_trial import fixture_xml
from .engraving import musicxml_with_canonical_ids
from .source_enrichment import enrich_from_mapped_musicxml
from .source_note_mapping_audit import xml_inventory
from .harmony_delayed_links import observe
from .harmony_polyphonic_trial import render
from .harmony_link_counterevidence import assess,VERSION

KINDS=('short_endpoint','intervening','earlier_target','restart')
REASONS={'earlier_identical_target_already_attacked':'같은 목표음이 앞에서 이미 등장',
    'intervening_attacks_need_path_explanation':'중간 음을 건너뛰는 경로 설명 필요',
    'recurrent_attack_pattern_allows_restart':'앞 음형 재등장: 새 시작 해석도 가능',
    'polyphonic_voice_identity_unresolved':'동시음 사이 실제 성부 불확정',
    'longer_gap_reentry_alternative':'긴 간격: 독립 재진입 가능'}


def fixture(kind,transpose=0,scale=F(1)):
    specs=[('B3',F(0),F(1))]
    if kind=='restart':specs=[('C4',F(0),F(1,4)),('D4',F(1,4),F(1,2)),('E4',F(1,2),F(3,4)),('B3',F(3,4),F(1))]
    endings={'short_endpoint':[('C4',F(5,4),F(2))],
        'intervening':[('G4',F(5,4),F(3,2)),('C4',F(3,2),F(2))],
        'earlier_target':[('C4',F(5,4),F(3,2)),('D4',F(3,2),F(7,4)),('C4',F(7,4),F(2))],
        'restart':[('C4',F(5,4),F(3,2)),('D4',F(3,2),F(7,4)),('E4',F(7,4),F(2))]}
    return {'kind':kind,'events':[{'pitch':pitch.Pitch(p).transpose(transpose).nameWithOctave,'start':q(a*scale),'duration':q((b-a)*scale),'voice':'1'} for p,a,b in specs+endings[kind]],
        'scale':q(scale),'beat_type':int(4/scale),'transpose':transpose,
        'oracle':'authored_counterevidence_not_gold_voice_or_harmony'}


def verify_records(ir, observed, result):
    """Check warning provenance from saved events, independently of recurrence search."""
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};groups={g['group_id']:g for g in observed['groups']}
    assert len(result['records'])==sum(len(g['edges']) for g in observed['groups'])
    for r in result['records']:
        g=groups[r['group_id']];a,b=[sounds[x] for x in r['source_refs']]
        assert any(e['source_refs']==r['source_refs'] for e in g['edges'])
        assert r['source_release']==a['span']['end'] and r['target_onset']==b['span']['start']
        assert r['selected'] is None and not r['voice_connection_confirmed'] and not r['restart_confirmed'] and not r['independent_resolution_vote_allowed']
        for sid in r['intervening_attack_refs']:
            s=sounds[sid];assert f(a['span']['end'])<=f(s['span']['start'])<f(b['span']['start'])
        for sid in r['earlier_identical_target_refs']:
            s=sounds[sid];assert sid in r['intervening_attack_refs']
            assert (s['pitch']['step'],s['pitch']['octave'],s['pitch']['midi_pitch'])==(b['pitch']['step'],b['pitch']['octave'],b['pitch']['midi_pitch'])
        for prior in r['prior_matching_patterns']:
            assert prior['signature']==r['target_attack_pattern']['signature'] and f(prior['end'])<=f(g['time'])
            assert not set(prior['event_refs'])&set(r['target_attack_pattern']['event_refs'])
    return {'passed':True,'edges_checked':len(result['records'])}


def panel(ir,result,compatible):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};payload=[];rows=[]
    chosen=[r for r in result['records'] if tuple(r['source_refs']) in compatible] or result['records']
    for i,r in enumerate(chosen):
        refs={side:sorted({n for sid in ids for n in sounds[sid]['source_note_ids']}) for side,ids in
            [('source',r['source_refs'][:1]),('target',r['source_refs'][1:]),('held',r['intervening_attack_refs'])]}
        payload.append(refs)
        reason=' / '.join(REASONS[x] for x in r['review_reasons']) or '이번 경고 없음 · 연결 확정 아님'
        rows.append('<tr><td><button data-counter="'+str(i)+'">'+html.escape((r['source_pitch']+' → '+r['target_pitch']).replace('-','♭'))+'</button></td><td>'+html.escape(reason)+'</td></tr>')
    intro='<section id="counterevidence"><h2>이번 검증: 연결을 서둘러 확정하지 않을 근거</h2><p>음쌍 버튼: 파랑=출발음, 주황=도착음, 보라=그 사이에 먼저 등장한 음. 보라는 비화성음 판정이 아닙니다.</p>'
    intro+='<p>'+('앞 단계에서 화성 끝점 역할과 양립했던 음쌍을 표시합니다.' if compatible else '이번 문맥의 연결 후보를 표시합니다.')+' 경고가 없더라도 해결·연속 진행으로 확정하지 않습니다. 원음과 기존 후보는 삭제하지 않았습니다.</p>'
    body='<table><tr><th>음쌍</th><th>추가 검토 근거</th></tr>'+''.join(rows)+'</table>'
    if len(rows)>8:body='<details><summary>'+str(len(rows))+'음쌍 상세 펼치기</summary>'+body+'</details>'
    return intro+body+'<a href="../counterevidence.json">모든 검사 근거</a></section>', '<script>const counterGroups='+json.dumps(payload)+';'+r'''
document.querySelectorAll('[data-counter]').forEach(button=>button.addEventListener('click',()=>{
 document.querySelectorAll('.pl-source,.pl-target,.pl-held').forEach(el=>el.classList.remove('pl-source','pl-target','pl-held'));
 const group=counterGroups[Number(button.dataset.counter)];let first=null;
 for(const el of document.querySelectorAll('.system [data-id],.system [id]')){
  const id=el.dataset.id||el.id;
  for(const side of ['source','target','held'])if(group[side].includes(id)){el.classList.add('pl-'+side);first=first||el;}
 }
 if(first)first.closest('.system').scrollIntoView({block:'center',behavior:'smooth'});
}));</script>'''


def build(source,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    output.mkdir(parents=True);prior=load(source/'report.json')
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'source_report_sha256':digest(source/'report.json'),
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('harmony_link_counterevidence*.py')},
        'controls':KINDS,'transforms':['base','transpose_plus_2','half_duration_double_denominator'],
        'production_modified':False,'source_annotations_used':False,'accuracy_measured':False})
    report={'version':VERSION,'real':[],'controls':[],'accuracy_measured':False}
    for row in prior['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id']
        if digest(src/'delayed-links.json')!=row['result_sha256']:raise ValueError('frozen_result_changed')
        for name,sha in row['input_hashes'].items():
            if digest(src/name)!=sha:raise ValueError('frozen_input_changed')
        prov=load(src/'case-provenance.json')
        if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible_case')
        frozen={str(p.relative_to(src)):digest(p) for p in src.rglob('*') if p.is_file()};shutil.copytree(src,dst)
        ir=load(dst/'candidate_revision_ir.json');saved=load(dst/'delayed-links.json');contexts=[r['context_span'] for r in load(dst/'voice-revision-audit.json')['runs']]
        if observe(ir,contexts)!=saved['observed']:raise ValueError('baseline_not_reproduced')
        result=assess(ir,saved['observed'],contexts);verification=verify_records(ir,saved['observed'],result)
        compatible={tuple(c['source_refs']) for r in saved['roles'] for c in r['comparisons'] if any(t.startswith('conditional_') for t in c['endpoint_compatible_relations'])}
        result['compatible_endpoint_unique_pairs']=[r for r in result['records'] if tuple(r['source_refs']) in compatible]
        write(dst/'counterevidence.json',result)
        view=dst/'counter-view';shutil.copytree(dst/'delayed-view',view)
        extra,script=panel(ir,result,compatible);page=(view/'polyphonic.html').read_text(encoding='utf-8')
        page=page.replace('<section><h2>시간 간격 및 중간 음 보존</h2>',extra+'<section><h2>시간 간격 및 중간 음 보존</h2>').replace('</html>',script+'</html>')
        (view/'polyphonic.html').write_text(page,encoding='utf-8')
        assert all(digest(src/name)==sha and digest(dst/name)==sha for name,sha in frozen.items())
        report['real'].append({'case_id':row['case_id'],'title':row['title'],'summary':result['summary'],'verification':verification,
            'compatible_unique_pairs':len(compatible),'compatible_with_warnings':sum(bool(r['review_reasons']) for r in result['compatible_endpoint_unique_pairs']),
            'frozen_files_sha256':frozen,'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/')})
        print(row['title'],result['summary'],flush=True)
    for kind in KINDS:
        for variant,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/'controls'/(kind+'-'+variant);dst.mkdir(parents=True);case=fixture(kind,tr,scale);xml=dst/'score.musicxml'
            xml.write_text(fixture_xml(case),encoding='utf-8');ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            mapped,mapping=musicxml_with_canonical_ids(xml,ir)
            if mapping['unmatched_ir_note_ids']:raise ValueError('control_mapping_incomplete')
            enrich_from_mapped_musicxml(ir,mapped);raw=xml_inventory(xml)
            for ref in ir['source_references']:
                if ref.get('source_xpath') in raw:ref['source_part_id']=raw[ref['source_xpath']]['part']
            contexts=[{'start':q(0),'end':q(4*scale)}];observed=observe(ir,contexts)
            observed={**observed,'groups':[g for g in observed['groups'] if f(g['time'])==scale]}
            result=assess(ir,observed,contexts);verification=verify_records(ir,observed,result)
            expected={'short_endpoint':set(),'intervening':{'intervening_attacks_need_path_explanation'},
                'earlier_target':{'earlier_identical_target_already_attacked','intervening_attacks_need_path_explanation'},
                'restart':{'recurrent_attack_pattern_allows_restart'}}[kind]
            target=pitch.Pitch('C4').transpose(tr).nameWithOctave
            selected=[r for r in result['records'] if r['target_pitch']==target]
            selected=max(selected,key=lambda r:f(r['target_onset']))
            if set(selected['review_reasons'])!=expected:raise ValueError('control_warning_mismatch:'+kind+variant)
            for name,data in [('canonical_music_ir.json',ir),('fixture.json',case),('counterevidence.json',result),('delayed-links.json',observed)]:write(dst/name,data)
            view=dst/'counter-view';view.mkdir();shutil.copyfile(xml,view/xml.name);render(view,view/xml.name,ir,contexts,observed,[],kind+' · 대조 악보')
            extra,script=panel(ir,result,set());page=(view/'polyphonic.html').read_text(encoding='utf-8').replace('href="../../index.html"','href="../../../index.html"').replace('href="polyphonic-links.json"','href="../delayed-links.json"')
            page=page.replace('<section><h2>동시 음군 대응 후보</h2>',extra+'<section><h2>기존 연결 후보</h2>').replace('</html>',script+'</html>')
            (view/'polyphonic.html').write_text(page,encoding='utf-8')
            report['controls'].append({'case_id':kind+'-'+variant,'expected':sorted(expected),'observed':selected['review_reasons'],'verification':verification,
                'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/'),'file_hashes':{str(p.relative_to(dst)):digest(p) for p in dst.rglob('*') if p.is_file()}})
    write(output/'report.json',report);write(output/'verification.json',{'passed':True,'real':[r['verification'] for r in report['real']],
        'controls':[r['verification'] for r in report['controls']],'frozen_baseline_reproduced':True,'prior_files_unchanged':True,'controls_match_expected_warnings':True})
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r.get('title',r['case_id']))+'</a></li>' for r in report['real']+report['controls'] if r in report['real'] or r['case_id'].endswith('-base'))
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>연결 반례 검토</title><style>body{font:16px system-ui;max-width:1000px;margin:32px auto}li,p{line-height:1.8}</style><h1>성부 연결의 반례·추가 검토 근거</h1><p>같은 끝 음정이라도 중간 음, 이미 도착한 목표음, 반복 음형에 따라 다르게 검토합니다. 경고 없음은 연결 확정이 아닙니다. 화성 선택은 그대로입니다.</p><ul>'+links+'</ul><a href="report.json">전체 결과</a></html>',encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();build(a.source,a.output)
