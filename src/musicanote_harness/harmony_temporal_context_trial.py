"""Frozen real cases + engraved attack/release counterexamples for review."""
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
from .harmony_path_contrast import compare
from .harmony_path_contrast_trial import control_xml, fixture as prior_fixture
from .harmony_temporal_context import observe, VERSION
from .harmony_candidate_explanation import spelling_evidence
from .harmony_polyphonic_trial import render
from .harmony_ownership_diagnostic_review import position
from .engraving import musicxml_with_canonical_ids
from .source_enrichment import enrich_from_mapped_musicxml
from .source_note_mapping_audit import xml_inventory

KINDS = ('released', 'held', 'reattack', 'exclusive_switch', 'enharmonic', 'cutoff')
STATUS = {'context_unresolved':'문맥/성부 조건 미충족 · 보류', 'spelling_unresolved':'철자 가정 미해결 · 보류',
    'exclusive_membership_switch_not_harmonic_change':'앞뒤 후보별 구성음 소속 교대 · 화음 변경 확정 아님',
    'observed_context_no_decision':'전후 관측 완료 · 화음 유지/변경 미확정'}


def fixture(kind, tr=0, scale=F(1)):
    case = prior_fixture('common', tr, scale)
    extras = {'released': [], 'held':[('E5',1,2,'2')], 'reattack':[('E4',2,F(1,2),'1')],
        'exclusive_switch':[('F#4',2,F(1,2),'2')], 'enharmonic':[('F-4',2,F(1,2),'2')], 'cutoff':[]}[kind]
    case['events'] += [{'pitch':(pitch.Pitch(p) if not tr else pitch.Pitch(p).transpose('M2')).nameWithOctave,
        'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in extras]
    case['kind']=kind
    case['expected_status'] = ('context_unresolved' if kind=='cutoff' else 'spelling_unresolved' if kind=='enharmonic' else
        'exclusive_membership_switch_not_harmonic_change' if kind=='exclusive_switch' else 'observed_context_no_decision')
    return case


def verify(ir, result):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    for row in result['records']:
        if row['status']!='observed': continue
        for w in row['windows'].values():
            lo,hi=f(w['span']['start']),f(w['span']['end'])
            expected={sid for sid,s in sounds.items() if lo<hi and f(s['span']['start'])<hi and f(s['span']['end'])>lo}
            assert set(w['event_refs'])==expected
            for gap in w['all_voice_notated_silence']:
                a,b=f(gap['start']),f(gap['end'])
                assert lo<=a<b<=hi
                assert not any(f(s['span']['start'])<b and f(s['span']['end'])>a for s in sounds.values())
        pool=set().union(*(set(w['event_refs']) for w in row['windows'].values()))
        for boundary in row['boundaries']:
            t=f(boundary['time'])
            assert set(boundary['held_across'])=={sid for sid in pool if f(sounds[sid]['span']['start'])<t<f(sounds[sid]['span']['end'])}
            for p in boundary['same_spelled_pitch_reattack_pairs']:
                a,b=[sounds[i] for i in p['event_refs']]
                assert a['sounding_event_id']!=b['sounding_event_id']
                assert f(a['span']['end'])<=t<=f(b['span']['start'])
                assert f(p['gap_quarters'])==f(b['span']['start'])-f(a['span']['end'])
                assert not p['continuous_sound'] and not p['confirmed_voice_connection']
        for p in row['pairs']:
            assert p['selected'] is None and p['ranking_weight'] is None
            for name,buckets in p['window_memberships'].items():
                ids=[i for v in buckets.values() for i in v]
                assert len(ids)==len(set(ids)) and set(ids)==set(row['windows'][name]['event_refs'])
        assert row['selected'] is None and not row['used_for_ranking']
    for sid,u in result['event_units'].items():
        assert u['original_span']==sounds[sid]['span'] and u['source_note_ids']==sounds[sid]['source_note_ids']
    return {'passed':True, 'original_sound_spans_unchanged':True, 'half_open_window_membership_checked':True,
        'no_selection_or_independent_vote':True, 'paths':len(result['records'])}


def panel(ir, result, contrast):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    prior={r['path_id']:r for r in contrast['records']}; payload=[]; articles=[];seen=set()
    def names(ids):return ', '.join(sounds[i]['pitch']['spelling'].replace('-','♭') for i in ids) or '없음'
    def button(label, mapping):
        index=len(payload)
        payload.append({color:[n for i in ids for n in sounds[i]['source_note_ids']] for color,ids in mapping.items()})
        return '<button data-time-context="'+str(index)+'">'+html.escape(label)+'</button>'
    for row in sorted(result['records'],key=lambda r:(f(r.get('arrival_span',{'start':q(0)})['start']),-f(r.get('arrival_span',{'end':q(0)})['end']))):
        if row['status']!='observed' or not row['pairs']:continue
        sig=json.dumps([row['arrival_span'],row['context_span'],row['pairs']],sort_keys=True)
        if sig in seen:continue
        seen.add(sig)
        w=row['windows']; a=set(w['arrival']['event_refs']);before=set(w['before']['event_refs'])-a;after=set(w['after']['event_refs'])-a
        title=position(ir,row['arrival_span']['start'])+' → '+position(ir,row['arrival_span']['end'])+' 직전'
        buttons=button('전후 음표 색칠: '+title,{'source':sorted(before),'held':sorted(a),'target':sorted(after)})
        boundary_text=''
        for b in row['boundaries']:
            bt=position(ir,b['time']); held=b['held_across']
            boundary_text+='<li><b>'+html.escape(bt)+'</b>: 계속 울리는 동일 sound '+html.escape(names(held))+' / 여기서 끝남 '+html.escape(names(b['released_at']))+' / 새 attack '+html.escape(names(b['attacked_at']))
            if held: boundary_text+=' '+button('지속 음만 보기',{'held':held})
            boundary_text+='</li>'
            if b['same_spelled_pitch_reattack_pairs']:
                boundary_text+='<li>같은 기보 성부·동일 철자 재등장(지속 아님): '+html.escape('; '.join(names(p['event_refs'])+' · 간격 '+str(f(p['gap_quarters']))+' quarter' for p in b['same_spelled_pitch_reattack_pairs']))+'</li>'
        candidates={c['candidate_key']:('/'.join(c['root_spelling_support'])+':'+c['candidate']['label'].partition(':')[2]
            if c['root_spelling_support'] else c['candidate']['label']+' (철자 미확정)') for c in prior[row['path_id']]['conditions']}
        tables=''
        for p in row['pairs']:
            tables+='<p><b>A: '+html.escape(candidates[p['left']])+' / B: '+html.escape(candidates[p['right']])+'</b> — '+STATUS[p['status']]+'</p><table><tr><th>범위</th><th>A에서만 구성음</th><th>B에서만 구성음</th><th>양쪽 공통</th><th>양쪽 비구성음(NCT 미확정)</th><th>철자 보류</th></tr>'
            for key,label in [('before','앞'),('arrival','도착'),('after','뒤')]:
                buckets=p['window_memberships'][key];win=w[key]
                label+= ' (문맥 잘림)' if not win['complete_requested_window'] else ''
                label+=' '+position(ir,win['span']['start'])+' → '+position(ir,win['span']['end'])+' 직전'
                tables+='<tr><td>'+html.escape(label)+'</td>'+''.join('<td>'+html.escape(names(buckets[k]) if win['available'] else '관측 범위 없음')+'</td>' for k in ('left_member_only','right_member_only','shared_member','neither_member','spelling_unresolved'))+'</tr>'
            tables+='</table>'
        articles.append('<article>'+buttons+'<ul>'+boundary_text+'</ul><details><summary>후보별 앞·도착·뒤 구성음 비교 펼치기</summary>'+tables+'</details></article>')
    body=''.join(articles[:3])
    if len(articles)>3:body+='<details><summary>나머지 '+str(len(articles)-3)+'개 전후 비교</summary>'+''.join(articles[3:])+'</details>'
    extra='<section id="temporal-context"><h2>이번 단계: 실제 지속과 재등장을 구별하기</h2><p>도착 앞뒤 각 1분모박을 봅니다. 파랑=앞에서만, 보라=도착 중 울림, 주황=뒤에서만. 원래 음표 전체를 색칠하며 소리를 연장하지 않습니다. 기보 지속이며 페달/실제 연주 길이는 포함하지 않습니다.</p><p>앞뒤 표의 구성음 소속은 <b>도착 화음 후보를 가정한 비교</b>입니다. 앞뒤 구간의 화음을 확정한 표기가 아닙니다. 같은 음의 지속도 화음 유지의 증명은 아닙니다.</p>'+body+'<a href="../temporal-context.json">전체 시간·음표 근거</a></section>'
    script='<script>const timeContextNotes='+json.dumps(payload)+';'+r'''
document.querySelectorAll('[data-time-context]').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.pl-source,.pl-target,.pl-held').forEach(e=>e.classList.remove('pl-source','pl-target','pl-held'));
 const g=timeContextNotes[+b.dataset.timeContext];let first=null;
 for(const e of document.querySelectorAll('.system [data-id],.system [id]')){const id=e.dataset.id||e.id;
  for(const c of ['source','target','held'])if((g[c]||[]).includes(id)){e.classList.add('pl-'+c);first=first||e;}}
 if(first)first.closest('.system').scrollIntoView({block:'center',behavior:'smooth'});
}));</script>'''
    return extra,script


def build(source, output):
    if output.exists():raise ValueError('choose_new_revision')
    output.mkdir(parents=True);previous=load(source/'report.json')
    report={'version':VERSION,'real':[],'controls':[],'production_modified':False,'accuracy_measured':False}
    write(output/'run-contract.json',{'source':str(source.resolve()),'source_sha256':digest(source/'report.json'),
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'control_types':KINDS})
    for old in previous['real']:
        src=source/'real-cases'/old['case_id'];dst=output/'real-cases'/old['case_id']
        if digest(src/'path-contrast.json')!=old['result_sha256']:raise ValueError('prior_result_changed')
        if any(digest(src/n)!=h for n,h in old['prior_sha256'].items()):raise ValueError('prior_inputs_changed')
        provenance=load(src/'case-provenance.json')
        if any(provenance[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not provenance['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible_case')
        frozen={str(p.relative_to(src)):digest(p) for p in src.rglob('*') if p.is_file()};shutil.copytree(src,dst)
        ir=load(dst/'candidate_revision_ir.json');contrast=load(dst/'path-contrast.json');paths=load(dst/'path-explanations.json')
        if compare(ir,paths)!=contrast:raise ValueError('contrast_baseline_changed')
        contexts=[r['context_span'] for r in load(dst/'voice-revision-audit.json')['runs']]
        result=observe(ir,contrast,contexts);checked=verify(ir,result);write(dst/'temporal-context.json',result)
        view=dst/'temporal-view';shutil.copytree(dst/'contrast-view',view);extra,script=panel(ir,result,contrast)
        page=(view/'polyphonic.html').read_text(encoding='utf-8').replace('<section id="all-voice-contrast">',extra+'<details><summary>이전 단계의 비교 근거 펼치기</summary><section id="all-voice-contrast">').replace('<div class="system">','</details><div class="system">',1).replace('</html>',script+'</html>')
        (view/'polyphonic.html').write_text(page,encoding='utf-8')
        assert all(digest(src/n)==h and digest(dst/n)==h for n,h in frozen.items())
        report['real'].append({'case_id':old['case_id'],'title':old['title'],'summary':result['summary'],'verification':checked,
            'prior_sha256':frozen,'result_sha256':digest(dst/'temporal-context.json'),'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/')})
        print(old['title'],result['summary'],flush=True)
    for kind in KINDS:
        baseline_signature = None
        for name,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,F(1,2))]:
            dst=output/'controls'/(kind+'-'+name);dst.mkdir(parents=True);case=fixture(kind,tr,scale);xml=dst/'score.musicxml'
            xml.write_text(control_xml(case),encoding='utf-8');ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml);check_roundtrip(case,ir)
            expected=Counter((pitch.Pitch(e['pitch']).step, int(pitch.Pitch(e['pitch']).accidental.alter) if pitch.Pitch(e['pitch']).accidental else 0, pitch.Pitch(e['pitch']).octave, f(e['start'])) for e in case['events'])
            actual=Counter((s['pitch']['step'],f(s['pitch']['alter']),s['pitch']['octave'],f(s['span']['start'])) for s in ir['sounding_events'])
            if expected!=actual:raise ValueError('spelling_roundtrip_failed')
            mapped,mapping=musicxml_with_canonical_ids(xml,ir)
            if mapping['unmatched_ir_note_ids']:raise ValueError('unmapped_note')
            enrich_from_mapped_musicxml(ir,mapped);raw=xml_inventory(xml)
            for ref in ir['source_references']:
                if ref.get('source_xpath') in raw:ref['source_part_id']=raw[ref['source_xpath']]['part']
            arrivals=[s['sounding_event_id'] for s in ir['sounding_events'] if F(5,4)*scale<=f(s['span']['start'])<2*scale]
            full={'start':q(0),'end':q(4*scale)};explanations=[]
            for c in case['conditions']:
                sp=spelling_evidence(ir,full,c)
                explanations.append({'candidate':c,'span':full,'provenance':[{'type':'authored_test_condition'}],
                    'status':'conditional','spelling_evidence':sp,'coherent_root_spellings':[r['root_spelling'] for r in sp['candidates']],
                    'compatible_patterns':[],'conditional_ornaments':[]})
            paths={'records':[{'path_id':'authored','group_id':'authored','source_refs':[],'arrival_event_refs':arrivals,
                'conditional_explanations':explanations,'abstention_reasons':[],'initial_gap':{'start':q(scale),'end':q(F(5,4)*scale)},'prior_review_reasons':[]}]}
            contrast=compare(ir,paths);contexts=[{'start':q(F(5,4)*scale),'end':q(2*scale)}] if kind=='cutoff' else [full]
            result=observe(ir,contrast,contexts);checked=verify(ir,result);p=result['records'][0]['pairs'][0]
            if p['status']!=case['expected_status']:raise ValueError('unexpected_control_status:'+kind+name+p['status'])
            if kind=='reattack' and not result['records'][0]['boundaries'][1]['same_spelled_pitch_reattack_pairs']:raise ValueError('missing_reattack')
            # Candidate-key order can reverse under transposition. Compare each
            # candidate by quality, not by its hash or arbitrary left/right slot.
            cs={c['candidate_key']:c['candidate']['label'].partition(':')[2] for c in contrast['records'][0]['conditions']}
            sig={'status':p['status'], 'windows':{k:{'shared':len(v['shared_member']), 'neither':len(v['neither_member']), 'unresolved':len(v['spelling_unresolved']), cs[p['left']]:len(v['left_member_only']),cs[p['right']]:len(v['right_member_only'])} for k,v in p['window_memberships'].items()},
                'boundary_counts':[{k:len(b[k]) for k in ('held_across','released_at','attacked_at','released_before','attacked_after','same_spelled_pitch_reattack_pairs')} for b in result['records'][0]['boundaries']]}
            if baseline_signature is None:baseline_signature=sig
            elif sig!=baseline_signature:raise ValueError('transformation_changed_temporal_contract')
            for filename,data in [('fixture.json',case),('canonical_music_ir.json',ir),('path-contrast.json',contrast),('temporal-context.json',result)]:write(dst/filename,data)
            view=dst/'temporal-view';view.mkdir();shutil.copyfile(xml,view/xml.name)
            render(view,view/xml.name,ir,[full],{'groups':[], 'abstentions':[]},[],kind+' · 실제 지속/재등장 비교')
            extra,script=panel(ir,result,contrast);page=(view/'polyphonic.html').read_text(encoding='utf-8')
            page=page.replace('href="../../index.html"','href="../../../index.html"').replace('href="polyphonic-links.json"','href="../temporal-context.json"').replace('<section><h2>동시 음군 대응 후보</h2>',extra+'<details><summary>이전 연결 검토 안내</summary><section><h2>기존 연결 가설</h2>').replace('<div class="system">','</details><div class="system">',1).replace('</html>',script+'</html>')
            (view/'polyphonic.html').write_text(page,encoding='utf-8')
            report['controls'].append({'case_id':kind+'-'+name,'observed':p['status'],'expected':case['expected_status'],'verification':checked,
                'file_sha256':{str(p.relative_to(dst)):digest(p) for p in dst.rglob('*') if p.is_file()},'page':str((view/'polyphonic.html').relative_to(output)).replace('\\','/')})
    write(output/'report.json',report);write(output/'verification.json',{'passed':True,'real':[r['verification'] for r in report['real']],
        'controls':[r['verification'] for r in report['controls']],'prior_files_unchanged':True,'prior_contrast_reproduced':True})
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r.get('title',r['case_id']))+'</a></li>' for r in report['real']+report['controls'] if r in report['real'] or r['case_id'].endswith('-base'))
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>화음 후보 전후의 attack/release</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto}li,p{line-height:1.8}</style><h1>실제 지속과 재등장: 앞뒤 문맥 검토</h1><p>지속음·새 attack·release를 구별합니다. 화음 유지/변경을 확정하거나 운영 결과를 변경하지 않습니다. 대조 악보 화음은 작성한 시험 조건입니다.</p><ul>'+links+'</ul><a href="report.json">전체 결과</a></html>',encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
