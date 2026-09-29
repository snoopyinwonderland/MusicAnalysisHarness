"""Frozen-cohort trial of possible inner-voice assignments, never a reranker."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
import json
from math import comb, factorial
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET
from .formal_ir import q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import write, digest, source_xml, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_polyphonic_links import observe, evaluate, VERSION
from .harmony_ownership_diagnostic_review import position
from .sonata_verification import verified_pages
from .harmony_visual_review import system_fragments


def compare_readings(candidate, voice, groups):
    """Only exact reading boundaries; other groups remain unscored context."""
    a, t, b = (f(candidate['span']['start']), f(candidate['boundary']), f(candidate['span']['end']))
    result = []
    for kind in ('merged_seventh', 'split_triads'):
        for index, path in enumerate(candidate[kind]):
            first, last = path['segments'][0]['candidate'], path['segments'][-1]['candidate']
            for group in groups:
                time = f(group['time'])
                comparisons = []
                if time == t:
                    comparisons.append({'side': 'internal', 'evaluation': evaluate(group, first, last)})
                for ext in voice['external_shape_candidates']:
                    if ext['side'] == 'preceding' and time == a:
                        pair = (ext['candidate'], first)
                    elif ext['side'] == 'following' and time == b:
                        pair = (last, ext['candidate'])
                    else:
                        continue
                    comparisons.append({'side': ext['side'], 'external_span': ext['span'],
                        'all_members_observed_by': ext['all_members_observed_by'], 'evaluation': evaluate(group, *pair)})
                if comparisons:
                    result.append({'reading_type': kind, 'reading_index': index, 'group_id': group['group_id'],
                        'original_cost': path['local_cost'], 'comparisons': comparisons, 'selected': None})
    return result


def release_coverage(ir, audit, groups):
    """Explain why previously blocked polyphonic sounds yield no new group."""
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    notes = {n['note_id']: n for n in ir['note_events']}
    def lane(s):
        return {(notes[n]['part_id'], notes[n]['voice_id']) for n in s['source_note_ids']}
    examples = {p['event_ref']: p for r in audit['runs'] for p in r.get('polyphony_examples', [])}
    rows = []
    for sid in sorted(examples):
        s = sounds[sid]; end = f(s['span']['end']); identity = lane(s)
        following = [d for d in sounds.values() if len(identity) == 1 and lane(d) == identity and f(d['span']['start']) >= end]
        exact = [d['sounding_event_id'] for d in following if f(d['span']['start']) == end]
        nearest = min((f(d['span']['start']) for d in following), default=None)
        group_ids = [g['group_id'] for g in groups if sid in g['source_refs']]
        rows.append({'event_ref': sid, 'pitch': s['pitch']['spelling'], 'release': s['span']['end'],
            'exact_target_refs': exact, 'next_attack_delay_quarters': q(nearest-end) if nearest is not None else None,
            'group_ids': group_ids, 'status': 'hypotheses_available' if group_ids else
                'no_exact_release_attack' if not exact else 'no_eligible_group_in_frozen_context'})
    return rows


def verify_groups(ir, observed):
    """Independent combinatorial/integrity oracle; does not call the enumerator."""
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    notes = {n['note_id']: n for n in ir['note_events']}
    total = 0
    for g in observed['groups']:
        left, right, held = map(set, (g['source_refs'], g['target_refs'], g['held_refs']))
        assert not (left & right or held & (left | right))
        n, m = len(left), len(right)
        expected = sum(comb(n, k)*comb(m, k)*factorial(k) for k in range(min(n, m)+1))
        assert len(g['assignments']) == expected and len(g['edges']) == n*m
        assert {tuple(e['source_refs']) for e in g['edges']} == {(a, b) for a in left for b in right}
        seen = set()
        for assignment in g['assignments']:
            pairs = [tuple(g['edges'][i]['source_refs']) for i in assignment['edge_indices']]
            signature = tuple(sorted(pairs)); assert signature not in seen; seen.add(signature)
            assert len({a for a, b in pairs}) == len(pairs) == len({b for a, b in pairs})
            assert set(assignment['unmatched_source_refs']) == left-{a for a, b in pairs}
            assert set(assignment['unmatched_target_refs']) == right-{b for a, b in pairs}
            assert not assignment['selected']
        assert () in seen and g['selected_assignment'] is None
        for sid in left | right | held:
            s = sounds[sid]
            assert {(notes[n]['part_id'], notes[n]['voice_id']) for n in s['source_note_ids']} == {(g['part_id'], g['voice_id'])}
            t = f(g['time'])
            assert (f(s['span']['end']) == t if sid in left else f(s['span']['start']) == t if sid in right else f(s['span']['start']) < t < f(s['span']['end']))
        for edge in g['edges']:
            s, d = (sounds[sid] for sid in edge['source_refs'])
            assert edge['source_pitch'] == s['pitch'] and edge['target_pitch'] == d['pitch']
            assert edge['source_span'] == s['span'] and edge['target_span'] == d['span']
            assert edge['semitones'] == d['pitch']['midi_pitch']-s['pitch']['midi_pitch']
        total += expected
    return {'groups': len(observed['groups']), 'assignments_verified': total, 'passed': True}


def header(title):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:16px system-ui;background:#f4f7fa;color:#173047;margin:24px}main{max-width:1250px;margin:auto}p,li{line-height:1.7}section{background:white;padding:18px;margin:16px 0}.system{background:white;overflow:auto;margin:16px 0;padding:12px}.system>svg{width:100%;min-width:800px;height:auto}button{padding:10px;margin:6px;cursor:pointer}table{border-collapse:collapse}td,th{padding:10px;border:1px solid #ccd6df}.pl-source{color:#1971c2!important;fill:#1971c2!important;stroke:#1971c2!important}.pl-target{color:#c05600!important;fill:#c05600!important;stroke:#c05600!important}.pl-held{color:#8e44ad!important;fill:#8e44ad!important;stroke:#8e44ad!important}</style><main><a href="../../index.html">사례 목록</a><h1>'+html.escape(title)+'</h1>'


def render(folder, source, ir, contexts, observed, coverage, title):
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    context_ids = {n['note_id'] for n in ir['note_events'] if any(f(n['global_onset_quarter']) < f(c['end']) and f(n['global_onset_quarter'])+f(n['notated_duration_quarter']) > f(c['start']) for c in contexts)}
    # Include all tied source glyphs of the group; sound identity is not a single notehead.
    for g in observed['groups']:
        context_ids.update(n for sid in g['source_refs']+g['target_refs']+g['held_refs'] for n in sounds[sid]['source_note_ids'])
    subset = {**ir, 'note_events': [n for n in ir['note_events'] if n['note_id'] in context_ids]}
    pages, mapping = verified_pages(source, subset)
    write(folder/'polyphonic-render-validation.json', {**mapping, 'scope': 'display_context_and_group_tie_glyphs'})
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    page = header(title)+'<p>이번 표시는 <b>가능한 성부 연결</b>입니다. 자동 화음의 변경이나 해결 확정이 아닙니다. 파랑=끝나는 음군, 주황=새 음군, 보라=계속 울리는 음. 버튼을 누르면 해당 음표를 색칠합니다.</p>'
    payload = []; rows = []; alternatives = []
    for i, g in enumerate(observed['groups']):
        names = lambda refs: ', '.join(sounds[s]['pitch']['spelling'].replace('-', '♭') for s in refs)
        rows.append('<tr><td><button data-group="'+str(i)+'">'+html.escape(position(ir, g['time']))+'</button></td><td>'+html.escape(names(g['source_refs'])+' → '+names(g['target_refs']))+'</td><td>'+str(len(g['assignments']))+'개 · 미연결 포함</td></tr>')
        payload.append({side: sorted({n for sid in g[side+'_refs'] for n in sounds[sid]['source_note_ids']}) for side in ('source', 'target', 'held')})
        options=[]
        for assignment in g['assignments']:
            edges=[g['edges'][j] for j in assignment['edge_indices']]
            pairs=' / '.join(e['source_pitch']['spelling']+' → '+e['target_pitch']['spelling'] for e in edges) or '아무 음도 연결하지 않음'
            options.append('<li>'+html.escape(pairs.replace('-', '♭'))+' · 음정 이동량 '+str(assignment['motion_semitones'])+'반음 / 교차 '+str(assignment['crossing_count'])+'회</li>')
        alternatives.append('<details><summary>'+html.escape(position(ir,g['time']))+' — 전체 연결 가설 펼치기</summary><p>나열 순서는 우열이 아닙니다. 연결하지 않은 음은 새 성부의 진입·소멸 등 다른 가능성으로 남깁니다.</p><ol>'+''.join(options)+'</ol></details>')
    empty='음군이 있으나 크기 제한(한쪽 4음 초과)으로 기권했습니다.' if observed['abstentions'] else '이 문맥에는 정확히 맞닿는 다성부 음군이 없습니다. 장식·쉼을 넘어선 연결은 이번 단계에서 만들지 않았습니다.'
    page += '<section><h2>동시 음군 대응 후보</h2><table><tr><th>위치</th><th>음군</th><th>전체 부분 대응</th></tr>'+(''.join(rows) or '<tr><td colspan="3">'+empty+'</td></tr>')+'</table><p>대응 개수는 확률이나 신뢰도가 아닙니다. 가까운 음끼리 잇는 해석만 남기거나 화성에 맞는 대응을 선택하지 않습니다.</p>'+''.join(alternatives)+'</section>'
    page += ''.join('<div class="system">'+x['svg']+'</div>' for x in system_fragments(pages, context_ids))
    if coverage:
        page += '<section><h2>이전 보류 음표의 연결 가능 여부</h2><ul>'+''.join('<li>'+html.escape(r['pitch'].replace('-', '♭')+' · 끝 '+position(ir,r['release']))+' · '+('음군 후보 있음' if r['group_ids'] else '끝 시점에 같은 성부의 새 음 없음' if not r['exact_target_refs'] else '해당 문맥에서 음군 조건 미충족')+((' · 다음 attack까지 '+str(f(r['next_attack_delay_quarters']))+' quarter') if r['next_attack_delay_quarters'] is not None and f(r['next_attack_delay_quarters'])>0 else '')+'</li>' for r in coverage)+'</ul></section>'
    page += '<p><a href="polyphonic-links.json">모든 대응·음표 ID·조건부 화성 비교</a> · <a href="'+html.escape(source.name, quote=True)+'">원 MusicXML</a></p></main><script>const groups='+json.dumps(payload)+';'+r'''
for(const svg of document.querySelectorAll('.system>svg')){
 const g=svg.querySelector('.system');if(!g)continue;
 const b=g.getBBox(),m=svg.getScreenCTM().inverse().multiply(g.getScreenCTM());
 const point=(x,y)=>{const p=svg.createSVGPoint();p.x=x;p.y=y;return p.matrixTransform(m)};
 const a=point(b.x,b.y),z=point(b.x+b.width,b.y+b.height);
 svg.setAttribute('viewBox',`${a.x-180} ${a.y-180} ${z.x-a.x+360} ${z.y-a.y+360}`);svg.removeAttribute('width');svg.removeAttribute('height');
}
function show(index){
 document.querySelectorAll('.pl-source,.pl-target,.pl-held').forEach(e=>e.classList.remove('pl-source','pl-target','pl-held'));
 const group=groups[index];if(!group)return;
 let first=null;
 for(const el of document.querySelectorAll('.system [data-id],.system [id]')){
  const id=el.dataset.id||el.id;
  for(const side of ['source','target','held'])if(group[side].includes(id)){el.classList.add('pl-'+side);first=first||el;}
 }
 if(first)first.closest('.system').scrollIntoView({block:'center',behavior:'smooth'});
}
document.querySelectorAll('[data-group]').forEach(b=>b.addEventListener('click',()=>show(Number(b.dataset.group))));
</script></html>'''
    (folder/'polyphonic.html').write_text(page, encoding='utf-8')


def build(source, output):
    if output.exists(): raise ValueError('output_exists_choose_new_revision')
    prior = load(source/'report.json'); output.mkdir(parents=True)
    write(output/'run-contract.json', {'version': VERSION, 'source': str(source.resolve()), 'source_report_sha256': digest(source/'report.json'),
        'code_sha256': {p.name: digest(p) for p in Path(__file__).parent.glob('harmony_polyphonic*.py')},
        'production_modified': False, 'source_labels_used_for_inference': False, 'selection_rule': 'all_three_prior_audited_cases_no_success_filter'})
    report = {'version': VERSION, 'real': [], 'controls': [], 'accuracy_measured': False, 'production_modified': False}
    for row in prior['cases']:
        if row['status'] != 'audited': raise ValueError('unhandled_prior_case')
        src = source/'real-cases'/row['case_id']; dst = output/'real-cases'/row['case_id']
        if digest(src/'voice-revision-audit.json') != row['audit_sha256']: raise ValueError('audit_hash_mismatch')
        audit = load(src/'voice-revision-audit.json'); prov = load(src/'case-provenance.json')
        if any(prov[k]['split'] != 'train' for k in ('case', 'manifest_entry', 'frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']: raise ValueError('ineligible_case')
        xmlname = Path(prov['manifest_entry']['score_source_path']).name
        for name, key in [('canonical_music_ir.json','original_ir'), ('candidate_revision_ir.json','candidate_revision_ir'), (xmlname,'xml')]:
            if digest(src/name) != audit['input_hashes'][key]: raise ValueError('snapshot_hash_mismatch')
        shutil.copytree(src, dst)
        ir = load(dst/'candidate_revision_ir.json'); contexts = [r['context_span'] for r in audit['runs'] if r['status']=='compared']
        candidates = [c for r in load(dst/'comparison.json')['runs'] for c in r['temporal']['alternatives']]
        if len(candidates) != len(audit['runs']): raise ValueError('candidate_count_mismatch')
        observed = observe(ir, contexts); runs = []
        for c, r in zip(candidates, audit['runs']):
            if c['evidence_id'] != r['candidate_ref'] or r['status'] != 'compared': raise ValueError('candidate_identity_or_compatibility')
            runs.append({'candidate_ref': c['evidence_id'], 'readings': compare_readings(c, r['revised_voice'], observed['groups'])})
        coverage = release_coverage(ir, audit, observed['groups'])
        result = {'observed': observed, 'runs': runs, 'release_coverage': coverage, 'verification': verify_groups(ir, observed)}
        result['summary'] = {'unique_groups': len(observed['groups']), 'unique_possible_edges': sum(len(g['edges']) for g in observed['groups']),
            'assignments': sum(len(g['assignments']) for g in observed['groups']), 'compared_reading_group_occurrences': sum(len(r['readings']) for r in runs),
            'conditional_support_occurrences': sum(bool(c['evaluation']['conditional_resolution_edge_indices']) for r in runs for p in r['readings'] for c in p['comparisons']),
            'prior_blocked_source_events': len(coverage), 'release_coverage': dict(Counter(r['status'] for r in coverage))}
        write(dst/'polyphonic-links.json', result)
        render(dst, dst/xmlname, ir, contexts, observed, coverage, audit['revision_score']+' · 성부 연결 후보')
        frozen = {p.name: digest(p) for p in src.iterdir() if p.is_file()}
        if any(digest(dst/name) != sha or digest(src/name) != sha for name, sha in frozen.items()): raise ValueError('frozen_artifact_changed')
        report['real'].append({'case_id': row['case_id'], 'title': audit['revision_score'], 'summary': result['summary'], 'verification': result['verification'],
            'frozen_files_sha256': frozen, 'result_sha256': digest(dst/'polyphonic-links.json'), 'page': 'real-cases/'+row['case_id']+'/polyphonic.html'})
        print(report['real'][-1]['summary'], flush=True)
    # Tiny authored controls traverse MusicXML -> IR, separate from corpus claims.
    from music21 import converter
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .engraving import musicxml_with_canonical_ids
    from .source_enrichment import enrich_from_mapped_musicxml
    from .source_note_mapping_audit import xml_inventory
    for name, left, right, gap in [('two_by_two',['B3','F4'],['C4','E4'],False), ('unequal',['B3','F4'],['C4'],False), ('gap',['B3','F4'],['C4','E4'],True), ('cap',['G3','B3','D4','F4','G4'],['C4','E4'],False)]:
        dst = output/'controls'/name; dst.mkdir(parents=True)
        events = [{'pitch': p,'start':q(0),'duration':q(1),'voice':'1'} for p in left]+[{'pitch':p,'start':q(2 if gap else 1),'duration':q(2),'voice':'1'} for p in right]
        case = {'events':events,'beat_type':4}; xml = dst/'score.musicxml'; xml.write_text(source_xml(case), encoding='utf-8')
        ir = FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml); check_roundtrip(case,ir)
        mapped, mapping = musicxml_with_canonical_ids(xml, ir)
        if mapping['unmatched_ir_note_ids']: raise ValueError('control_source_mapping_incomplete')
        enrich_from_mapped_musicxml(ir, mapped)
        # The basic music21 adapter uses the part name as source ID. For these
        # generated controls only, recover the literal ID through verified XPath.
        raw = xml_inventory(xml)
        for ref in ir['source_references']:
            if ref.get('source_xpath') in raw:
                ref['source_part_id'] = raw[ref['source_xpath']]['part']
        write(dst/'canonical_music_ir.json',ir); contexts=[{'start':q(0),'end':q(4)}]; observed=observe(ir,contexts)
        assert len(observed['groups']) == (0 if name in ('gap','cap') else 1)
        assert len(observed['abstentions']) == (1 if name=='cap' else 0)
        evaluation = [evaluate(g,{'root':7,'label':'G:dominant7','pcs':[7,11,2,5]}, {'root':0,'label':'C:major','pcs':[0,4,7]}) for g in observed['groups']]
        if name=='two_by_two': assert len(evaluation[0]['conditional_resolution_edge_indices'])==2
        result={'observed':observed,'evaluation':evaluation,'verification':verify_groups(ir,observed),'oracle':'constructed_connections_not_real_music_gold'}
        write(dst/'polyphonic-links.json',result); render(dst,xml,ir,contexts,observed,[],name+' · 대조 악보')
        report['controls'].append({'case_id':name,'verification':result['verification'],'page':'controls/'+name+'/polyphonic.html'})
    write(output/'report.json',report)
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r.get('title',r['case_id']))+'</a></li>' for r in report['real']+report['controls'])
    (output/'index.html').write_text(header('동시 화음 안의 성부 연결 — 실험 검토')+'<p>같은 기보 성부 안에서 실제 음표가 어떻게 이어질 수 있는지 복수 대응을 보존합니다. 빈 대응도 포함하며, 화음 가설에 맞춰 성부를 선택하지 않습니다. 기존 화성·비용·원주석·운영 화면은 그대로입니다.</p><ul>'+links+'</ul><a href="report.json">전체 결과</a></main></html>',encoding='utf-8')
    write(output/'verification.json',{'passed':True,'real':[r['verification'] for r in report['real']],'controls':[r['verification'] for r in report['controls']],
        'frozen_copies_unchanged':True,'musicxml_controls_roundtrip':True,'accuracy_measured':False})


if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(); build(args.source,args.output)
