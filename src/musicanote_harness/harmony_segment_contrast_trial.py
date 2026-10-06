"""Replay all frozen continuous-survey samples, with factorized split alternatives."""
import argparse
from collections import Counter
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_continuous_survey_trial import page
from .harmony_catalog_microtime_trial import coordinate
from .harmony_joint import f
from .harmony_segment_contrast import build,compare,VERSION


def run(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);previous=load(source/'report.json');report={'version':VERSION,'real':[],
        'accuracy_measured':False,'production_modified':False,'source_labels_used':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.css','Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    shutil.copyfile(assets/'segment_contrast.js',output/'segment_contrast.js')
    write(output/'run-contract.json',{'version':VERSION,'source_report_hash':digest(source/'report.json'),
        'selection':'all samples in the previously frozen label-blind plans; both internal attack onsets',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'ui_hash':digest(output/'segment_contrast.js'),'rights':'local research only'})
    for old in previous['real']:
        cid=old['case_id'];src=source/'real-cases'/cid;dst=output/'real-cases'/cid
        dst.mkdir(parents=True);(dst/'samples').mkdir()
        snapshot=src/'source-snapshot';provenance=load(snapshot/'case-provenance.json')['manifest_entry']
        assert provenance['split']=='train' and provenance['rights']['internal_research_use']
        for name,h in old['source_hashes'].items():assert digest(snapshot/name)==h
        hashes={p.name:digest(p) for p in (src/'samples').glob('*.json')}
        ir=load(snapshot/'candidate_revision_ir.json');shutil.copytree(snapshot,dst/'source-snapshot')
        for name in ('plan.json','manifest.json'):shutil.copyfile(src/name,dst/name)
        manifest=load(src/'manifest.json');selection=load(src/'plan.json');counts=Counter();previews=[]
        for i in range(len(manifest)):
            baseline=load(src/'samples'/f'{i}.json')
            assert baseline['sample']==selection['samples'][i]
            result=build(ir,baseline);counts[result['status']]+=1
            result['display_note_refs']=baseline['display_note_refs']
            for boundary in result['boundaries']:
                boundary['display_boundary']=coordinate(ir,f(boundary['boundary']))
                counts['boundaries']+=1;counts['boundary_'+boundary['status']]+=1
                counts['virtual_comparisons_not_materialized']+=boundary['virtual_comparison_count']
                for side in ('left','right'):
                    counts['side_conditions']+=len(boundary[side]['readings'])
                    counts['blocked_side_conditions']+=sum(bool(r['condition']['abstention_reasons']) for r in boundary[side]['readings'])
            if result['status']=='ready' and result['hold_readings']:
                # Post-hoc inspection aid only; does not filter the sample plan.
                hi=next((j for j,h in enumerate(result['hold_readings']) if h['condition']['patterns']),0)
                h=result['hold_readings'][hi];patterns=h['condition']['patterns']
                aid=patterns[0]['supporting_assignment_refs'][0] if patterns else result['assignments'][0]['assignment_id']
                for bi,boundary in enumerate(result['boundaries']):
                    if boundary['status']!='ready' or not all(boundary[s]['readings'] for s in ('left','right')):continue
                    li=next((j for j,r in enumerate(boundary['left']['readings']) if r['members']==h['members']),0)
                    ri=next((j for j,r in enumerate(boundary['right']['readings']) if r['members']==h['members']),0)
                    result['preview_selection']={'boundary':bi,'hold':hi,'left':li,'right':ri,'assignment':aid,
                        'policy':'first inspectable boundary; first hold with geometry if available; same member sets on sides if available, otherwise first; not a recommendation'}
                    result['preview_comparison']=compare(result,bi,hi,li,ri,aid)
                    counts['preview_comparisons_checked']+=1
                    if patterns:previews.append(i)
                    break
            write(dst/'samples'/f'{i}.json',result)
            if (i+1)%20==0:print(old['title'],i+1,'/',len(manifest),flush=True)
        page(src,dst,old['title'],manifest)
        path=dst/'whole-score.html';doc=path.read_text(encoding='utf8')
        doc=doc.replace('연속 음형·조건부 화음','동일 음형의 화음 유지·분할 비교').replace(' · 연속 음형 비교',' · 유지·분할 비교')
        doc=doc.replace('<label for="candidate">화음·철자 후보 (추천 순서 아님)</label><select id="candidate"></select>',
            ''.join(f'<label for="{key}">{title}</label><select id="{key}"></select>' for key,title in
            [('boundary','분할 가정 위치 (탐지 결과 아님)'),('hold','유지 가정'),('left','분할: 앞 화음'),('right','분할: 뒤 화음'),('assignment','공통 성부 연결 가정')]))
        doc=doc.replace('continuous_survey.js','segment_contrast.js').replace('보라=선택한 조건부 장식음','보라=두 해석에서 설명이 달라진 음')
        path.write_text(doc,encoding='utf8')
        assert hashes=={p.name:digest(p) for p in (src/'samples').glob('*.json')}
        assert digest(src/'plan.json')==digest(dst/'plan.json')==old['plan_sha256']
        write(dst/'baseline-sample-hashes.json',hashes)
        row={'case_id':cid,'title':old['title'],'samples':len(manifest),**dict(counts),
             'inspection_samples':previews,'plan_sha256':old['plan_sha256'],'source_hashes':old['source_hashes']}
        report['real'].append(row);print({k:v for k,v in row.items() if k not in ('source_hashes','inspection_samples')},flush=True)
    write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html?sample='+str(r['inspection_samples'][0] if r['inspection_samples'] else 0)+'">'+r['title']+'</a> · '+str(r['samples'])+'표본</li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>같은 음형의 화음 유지·분할 비교</h1><p>모든 고정 표본을 보존합니다. 바로가기는 관찰을 돕기 위한 사후 사례 선택이며 정답·추천 후보가 아닙니다. 분할 가정이 실제 화음 교체라는 뜻은 아닙니다.</p><ul>'+links+'</ul><a href="report.json">실행 보고서</a>',encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.source,args.output)
