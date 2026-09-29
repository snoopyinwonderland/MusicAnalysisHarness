"""Archive and display bounded delayed links on the prior frozen cohort."""
import argparse
from collections import Counter
import html
from math import comb, factorial
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write, digest
from .harmony_shared_tone_trial import load
from .harmony_delayed_links import observe, VERSION
from .harmony_polyphonic_trial import render
from .harmony_reading_voice_context import relation
from .harmony_joint import f
from .formal_ir import q
from .harmony_ownership_diagnostic_review import position


def role_comparisons(candidate, voice, observed):
    """Use each actual arrival time, not the first chord of a pooled window."""
    rows=[]
    for kind in ('merged_seventh','split_triads'):
        for index,path in enumerate(candidate[kind]):
            def at(t,release):
                inside=[s for s in path['segments'] if (f(s['span']['start'])<t<=f(s['span']['end']) if release else f(s['span']['start'])<=t<f(s['span']['end']))]
                if inside:return [{'span':s['span'],'candidate':s['candidate'],'type':'frozen_reading'} for s in inside]
                side='preceding' if release else 'following'
                return [{'span':s['span'],'candidate':s['candidate'],'type':'external_pooled_shape'} for s in voice['external_shape_candidates'] if s['side']==side and
                    (f(s['span']['start'])<t<=f(s['span']['end']) if release else f(s['span']['start'])<=t<f(s['span']['end']))]
            for group in observed['groups']:
                for edge in group['edges']:
                    for src in at(f(edge['source_span']['end']),True):
                        for dst in at(f(edge['target_span']['start']),False):
                            tags=relation(edge,src['candidate'],dst['candidate'])
                            rows.append({'reading_type':kind,'reading_index':index,'group_id':group['group_id'],
                                'source_refs':edge['source_refs'],'source_chord_context':src,'target_chord_context':dst,
                                'endpoint_compatible_relations':tags,'original_cost':path['local_cost'],
                                'status':'endpoint_role_compatibility_only_not_observed_resolution',
                                'rest_refs':group['rest_refs'],'intervening_attack_refs':edge['intervening_attack_refs'],
                                'selected':False,'function_confirmed':False,'used_for_ranking':False})
    return rows


def verify(ir, observed):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};notes={n['note_id']:n for n in ir['note_events']}
    count=0
    for g in observed['groups']:
        n,m=len(g['source_refs']),len(g['target_refs']);expected=sum(comb(n,k)*comb(m,k)*factorial(k) for k in range(min(n,m)+1))
        assert len(g['assignments'])==expected
        seen=set()
        for a in g['assignments']:
            pairs=[tuple(g['edges'][i]['source_refs']) for i in a['edge_indices']]
            assert len({s for s,t in pairs})==len(pairs)==len({t for s,t in pairs})
            key=tuple(sorted(pairs));assert key not in seen;seen.add(key)
            assert set(a['unmatched_source_refs'])==set(g['source_refs'])-{s for s,t in pairs}
            assert set(a['unmatched_target_refs'])==set(g['target_refs'])-{t for s,t in pairs}
            assert not a['selected']
        assert () in seen
        release,first,end,unit=map(f,(g['time'],g['first_attack'],g['target_window_end'],g['beat_unit_quarter']))
        assert 0<first-release<=2*unit and first<end<=first+unit
        lane=[s for s in sounds.values() if {(notes[n]['part_id'],notes[n]['voice_id']) for n in s['source_note_ids']}=={(g['part_id'],g['voice_id'])}
              and f(s['span']['end'])>f(s['span']['start']) and not any(notes[n].get('grace',{}).get('is_grace') for n in s['source_note_ids'])]
        assert min(f(s['span']['start']) for s in lane if f(s['span']['start'])>release)==first
        assert {s['sounding_event_id'] for s in lane if first<=f(s['span']['start'])<end}==set(g['target_refs'])
        assert not any(f(s['span']['start'])==release for s in lane)
        for e in g['edges']:
            s,d=[sounds[x] for x in e['source_refs']]
            assert e['source_pitch']==s['pitch'] and e['target_pitch']==d['pitch']
            assert f(s['span']['end'])==release and first<=f(d['span']['start'])<end
            assert f(e['delay_quarters'])==f(d['span']['start'])-release
            assert set(e['intervening_attack_refs'])=={x for x in g['target_refs'] if f(sounds[x]['span']['start'])<f(d['span']['start'])}
        assert g['selected_assignment'] is None and not g['eligible_as_direct_resolution']
        count+=expected
    return {'passed':True,'groups':len(observed['groups']),'assignments_verified':count}


def build(source, output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    prior=load(source/'report.json');output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'source_report_sha256':digest(source/'report.json'),
        'code_sha256':{name:digest(Path(__file__).with_name(name)) for name in ('harmony_delayed_links.py','harmony_delayed_trial.py','harmony_polyphonic_trial.py','harmony_reading_voice_context.py')},
        'source_labels_used_for_inference':False,'production_modified':False,'scope':'all prior 3 real cases and 4 XML controls, no success filtering'})
    report={'version':VERSION,'real':[],'controls':[],'production_modified':False,'accuracy_measured':False}
    for kind in ('real','controls'):
        for row in prior[kind]:
            src=source/('real-cases' if kind=='real' else 'controls')/row['case_id']
            dst=output/src.relative_to(source);shutil.copytree(src,dst)
            frozen={p.name:digest(p) for p in src.iterdir() if p.is_file()}
            if kind=='real':
                if digest(src/'polyphonic-links.json')!=row['result_sha256']:raise ValueError('prior_result_changed')
                if any(digest(src/name)!=sha for name,sha in row['frozen_files_sha256'].items()):raise ValueError('frozen_input_changed')
                prov=load(dst/'case-provenance.json');entry=prov['manifest_entry']
                if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not entry['rights']['internal_research_use']:raise ValueError('ineligible_case')
                xml=dst/Path(entry['score_source_path']).name;ir=load(dst/'candidate_revision_ir.json');audit=load(dst/'voice-revision-audit.json')
                contexts=[r['context_span'] for r in audit['runs']];cs=[c for r in load(dst/'comparison.json')['runs'] for c in r['temporal']['alternatives']]
            else:
                xml=dst/'score.musicxml';ir=load(dst/'canonical_music_ir.json');contexts=[{'start':q(0),'end':q(4)}];cs=[]
            observed=observe(ir,contexts);roles=[]
            if cs:
                if len(cs)!=len(audit['runs']):raise ValueError('candidate_count_mismatch')
                for c,r in zip(cs,audit['runs']):
                    if c['evidence_id']!=r['candidate_ref']:raise ValueError('candidate_identity_mismatch')
                    roles.append({'candidate_ref':c['evidence_id'],'comparisons':role_comparisons(c,r['revised_voice'],observed)})
            summary={'groups':len(observed['groups']),'possible_edges':sum(len(g['edges']) for g in observed['groups']),
                'assignments':sum(len(g['assignments']) for g in observed['groups']),'grades':dict(Counter(g['evidence_grade'] for g in observed['groups'])),
                'with_explicit_rest':sum(bool(g['rest_refs']) for g in observed['groups']),
                'with_staggered_arrival':sum(len({f(e['target_span']['start']) for e in g['edges']})>1 for g in observed['groups']),
                'abstentions':dict(Counter(a['reason'] for a in observed['abstentions'])),
                'endpoint_role_compatible_occurrences':sum(any(t.startswith('conditional_') for t in c['endpoint_compatible_relations']) for r in roles for c in r['comparisons'])}
            result={'observed':observed,'roles':roles,'summary':summary,'verification':verify(ir,observed)}
            write(dst/'delayed-links.json',result)
            # Reuse verified original-score renderer but retain the earlier pages.
            scratch=dst/'delayed-view';scratch.mkdir();shutil.copyfile(xml,scratch/xml.name)
            render(scratch,scratch/xml.name,ir,contexts,observed,[],row.get('title',row['case_id'])+' · 시간 간격이 있는 연결')
            page=(scratch/'polyphonic.html').read_text(encoding='utf-8').replace('href="../../index.html"','href="../../../index.html"').replace('href="polyphonic-links.json"','href="../delayed-links.json"')
            if not observed['groups']:
                page=page.replace('음군이 있으나 크기 제한(한쪽 4음 초과)으로 기권했습니다.','현재 문맥에서 시간 간격 연결 조건을 충족한 후보가 없습니다. 기권 사유는 계산 기록에 보존했습니다.').replace('이 문맥에는 정확히 맞닿는 다성부 음군이 없습니다. 장식·쉼을 넘어선 연결은 이번 단계에서 만들지 않았습니다.','현재 문맥에는 지연 연결 후보가 없습니다. 직접 연결은 이전 모듈에서 다룹니다.')
            details='<section><h2>시간 간격 및 중간 음 보존</h2><p>직접 해결이 아닙니다. 음표 사이에 쉼이나 다른 음이 있으므로 끝 음고가 화성 역할과 양립해도 성부 연결이나 화음 변경을 확정하지 않습니다. 단위는 분모박이며 복합박의 큰 박을 추정하지 않습니다.</p><ul>'
            for g in observed['groups']:
                details+='<li>'+html.escape(position(ir,g['time'])+' 끝 → '+position(ir,g['first_attack'])+' 첫 도착')+' · '+str(f(g['first_attack_gap_beats']))+'분모박 간격 · 명시 쉼표 '+str(len(g['rest_refs']))+'개 · '+('1박 초과: 약한 가설' if 'weak' in g['evidence_grade'] else '1박 이내 가설')+'</li>'
            details+='</ul><p>자동 화음·기능·Cadence 선택은 변경하지 않았습니다.</p></section>'
            page=page.replace('<section><h2>동시 음군 대응 후보</h2>',details+'<section><h2>시간 간격이 있는 대응 후보</h2>')
            (scratch/'polyphonic.html').write_text(page,encoding='utf-8')
            if any(digest(src/name)!=sha or digest(dst/name)!=sha for name,sha in frozen.items()):raise ValueError('prior_artifact_changed')
            report[kind].append({'case_id':row['case_id'],'title':row.get('title',row['case_id']),'summary':summary,'verification':result['verification'],
                'page':str((scratch/'polyphonic.html').relative_to(output)).replace('\\','/'),'input_hashes':frozen,'result_sha256':digest(dst/'delayed-links.json')})
            print(kind,row['case_id'],summary,flush=True)
    write(output/'report.json',report)
    links=''.join('<li><a href="'+r['page']+'">'+html.escape(r['title'])+'</a></li>' for r in report['real']+report['controls'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>시간 간격 성부 연결</title><style>body{font:16px system-ui;max-width:1000px;margin:32px auto}li,p{line-height:1.8}</style><h1>쉼·분산 도착의 성부 연결 가설</h1><p>같은 기보 성부의 다음 attack을 제한된 시간 안에서 검토합니다. 쉼과 중간 음은 삭제하지 않고, 연결하지 않는 해석도 보존합니다. 화성 변경이나 정답률 향상이 아닙니다.</p><ul>'+links+'</ul><a href="report.json">전체 결과</a></html>',encoding='utf-8')
    write(output/'verification.json',{'passed':True,'cases':[r['verification'] for kind in ('real','controls') for r in report[kind]],'prior_files_unchanged':True})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();build(a.source,a.output)
