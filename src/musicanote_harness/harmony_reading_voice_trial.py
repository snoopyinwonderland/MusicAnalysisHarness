"""Apply contextual evidence to the frozen distributed-reading cohort."""
import argparse
from collections import Counter
import html
from pathlib import Path
import shutil
from .harmony_shared_tone_trial import load
from .harmony_arpeggio_benchmark import write,digest
from .harmony_reading_voice_context import compare,VERSION
from .harmony_ownership_diagnostic_review import position

RELATIONS={'same_spelled_pitch_reattack':'동일 철자 음 재타격',
 'conditional_seventh_down_step_to_member':'가정한7음이 구성음으로 순차 하행',
 'conditional_diminished_fifth_down_step_to_member':'가정한 감5음이 구성음으로 순차 하행',
 'conditional_dominant_family_leading_tone_up':'도미넌트 계열 가설의 이끎음이 목표 근음으로 반음 상행'}


def summary(records):
    tags=Counter();abstentions=Counter()
    for c in records:
        abstentions.update(c['voice_observations']['abstentions'])
        tags.update(tag for r in c['readings'] for p in r['internal_relations'] for tag in p['relations'])
        tags.update('external:'+tag for r in c['readings'] for e in r['external_comparisons'] for p in e['relations'] for tag in p['relations'])
    return {'candidate_count':len(records),'with_internal_direct_links':sum(bool(r['internal_links']) for r in records),
        'with_conditional_resolution':sum(any(tag.startswith('conditional_') for x in r['readings'] for p in x['internal_relations'] for tag in p['relations']) for r in records),
        'with_external_conditional_resolution':sum(any(tag.startswith('conditional_') for x in r['readings'] for e in x['external_comparisons'] for p in e['relations'] for tag in p['relations']) for r in records),
        'relation_occurrences':dict(tags),'abstention_occurrences':dict(abstentions),
        'occurrences_overlap_windows_and_readings':True}


def build(source,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    prior=load(source/'report.json');output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'source_report_sha256':digest(source/'report.json'),
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'context_denominator_beats_each_side':2,'reranking':False,'source_annotations_used':False,'production_modified':False})
    synth=[];real=[];real_records=[];synth_records=[]
    for group,target in [('synthetic',synth),('real',real)]:
        dirname='synthetic' if group=='synthetic' else 'real-cases'
        for row in prior[group]:
            src=source/dirname/row['case_id'];folder=output/dirname/row['case_id'];folder.mkdir(parents=True)
            if digest(src/'comparison.json')!=row['comparison_sha256'] or digest(src/'canonical_music_ir.json')!=row['ir_sha256']:raise ValueError('frozen_input_hash_mismatch')
            if group=='real':
                p=load(src/'case-provenance.json');entry=p['manifest_entry'];score_name=Path(entry['score_source_path']).name
                if any(p[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not entry['rights']['internal_research_use']:raise ValueError('ineligible_case')
                files=(score_name,'canonical_music_ir.json','comparison.json','case-provenance.json','trial-results.json')
            else:score_name='score.musicxml';files=(score_name,'canonical_music_ir.json','comparison.json','fixture.json','score.svg')
            if digest(src/score_name)!=row['source_sha256']:raise ValueError('source_hash_mismatch')
            for name in files:
                if (src/name).exists():shutil.copyfile(src/name,folder/name)
            ir=load(folder/'canonical_music_ir.json');original=load(folder/'comparison.json')
            candidates=([a for run in original['runs'] for a in run['temporal']['alternatives']] if group=='real' else original['temporal']['alternatives'])
            # Keep duplicate contextual occurrences explicit, rather than claim
            # independent examples; the saved evidence IDs still identify them.
            records=[compare(ir,c) for c in candidates]
            write(folder/'voice-context.json',{'records':records,'summary':summary(records)})
            result={**row,'voice_summary':summary(records),'voice_context_sha256':digest(folder/'voice-context.json')}
            if digest(folder/'comparison.json')!=row['comparison_sha256']:raise ValueError('hypotheses_changed')
            if group=='real':
                if digest(folder/'trial-results.json')!=row['saved_paths_sha256']:raise ValueError('selected_path_changed')
                real_records.extend(records)
                if (src/'index.html').exists():
                    shutil.copyfile(src/'render-validation.json',folder/'render-validation.json')
                    ref=next(r['candidate_ref'] for r in load(source/'real-gallery.json')['cases'] if r['case_id']==row['case_id'])
                    chosen=next(r for r in records if r['candidate_ref']==ref)
                    page=(src/'index.html').read_text(encoding='utf-8').replace('</main>',panel(chosen,ir)+'</main>')
                    (folder/'index.html').write_text(page,encoding='utf-8')
                    result['review_page']='real-cases/'+row['case_id']+'/index.html'
                    result['html_sha256']=digest(folder/'index.html')
            else:synth_records.extend(records)
            target.append(result)
            if group=='real':print(row['case_id'],result['voice_summary'],flush=True)
    report={'version':VERSION,'synthetic':synth,'real':real,
            'summary':{'synthetic':summary(synth_records),'real':summary(real_records),'hypotheses_and_costs_changed':False,'accuracy_measured':False}}
    write(output/'report.json',report)
    links=''.join('<li><a href="'+r['review_page']+'">'+html.escape(r['collection']+' · '+r['case_id'])+'</a></li>' for r in real if r.get('review_page'))
    rs=report['summary']['real']
    page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>화음 가설 · 성부 진행 검토</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px;background:#f4f7fa;color:#173047}p,li{line-height:1.8}</style><h1>화음 가설에 성부 진행 근거 연결</h1>'
    page+=f'<p>실제 {rs["candidate_count"]}개 겹치는 후보 중 {rs["with_internal_direct_links"]}개에 내부 직접 성부 연결이 있습니다. 조건부 해결 확인은 내부 {rs["with_conditional_resolution"]}개, 외부 문맥 {rs["with_external_conditional_resolution"]}개입니다. 후보와 비용, 자동 선택은 그대로입니다. 정확도 측정값이 아닙니다.</p>'
    page+='<p>같은 성부의 동시 화음이나 겹치는 음은 임의로 연결하지 않습니다. 해결을 확인하지 못한 것은 해당 가설이 틀렸다는 뜻이 아닙니다.</p><ul>'+links+'</ul><a href="report.json">전체 보고서</a></html>'
    (output/'index.html').write_text(page,encoding='utf-8');print(report['summary'],flush=True)


def panel(record,ir):
    rows=[]
    pairs={tuple(p['source_refs']):p for p in record['voice_observations']['links']}
    def motion(p):
        link=pairs[tuple(p['source_refs'])]
        names=[link[k]['spelling'].replace('-', '♭') for k in ('source_pitch','target_pitch')]
        return ' → '.join(names)+' ('+position(ir,link['target_span']['start'])+' 도착)'
    for r in record['readings']:
        descriptions=[]
        for p in r['internal_relations']:
            for tag in p['relations']:descriptions.append(motion(p)+' — '+RELATIONS[tag])
        for ext in r['external_comparisons']:
            for p in ext['relations']:
                for tag in p['relations']:descriptions.append(('앞 문맥: ' if ext['side']=='preceding' else '뒤 문맥: ')+motion(p)+' — '+RELATIONS[tag]+' / 외부 후보 '+ext['external_candidate']['label']+'; 구성음 누적 완료 '+position(ir,ext['external_members_observed_by']))
        desc=' / '.join(descriptions) or '직접적인 해결 관계 미확인 — 반증 아님'
        rows.append('<tr><td>'+html.escape(' → '.join(r['conditional_labels']))+'</td><td>'+html.escape(desc)+'</td></tr>')
    obs=record['voice_observations']
    return '<section id="voice-context" style="padding:18px;border:1px solid #bbcbd8;margin:24px 0;background:white"><h2>이번 추가: 성부 진행 근거</h2><p>내부 직접 연결 '+str(len(record['internal_links']))+'개, 앞 문맥 연결 '+str(len(record['preceding_links']))+'개, 뒤 문맥 연결 '+str(len(record['following_links']))+'개. 앞뒤1·2분모박의 완전 구성음 후보 '+str(len(record['external_shape_candidates']))+'개도 비교하지만 외부 화음을 확정하지 않습니다.</p><table><tr><th>비교하는 해석</th><th>조건부 근거 · 도착 위치</th></tr>'+''.join(rows)+'</table><p>같은 근거가 양쪽에 있으면 두 해석을 구별하는 증거는 아닙니다. 외부 구성음의 누적 완료 시각은 화음 시작 시각이 아닙니다.</p><p>성부 ID는 IR 기준이며 실제 대위적 성부의 확정이 아닙니다. 화음 내부 성부 대응·쉼표를 건너뛰는 해결은 보류합니다. 기능/종지/Secondary 확정 및 순위 변경 없음.</p><details><summary>성부 연결 보류 사유</summary><pre>'+html.escape(str(obs['abstentions']))+'</pre></details><a href="voice-context.json">성부·철자·음표 ID 근거</a></section>'


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.output)
