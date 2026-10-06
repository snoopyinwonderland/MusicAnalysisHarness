"""Add cross-boundary evidence to frozen comparisons without rewriting them."""
import argparse
from collections import Counter
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_boundary_figures import augment,VERSION
from .harmony_joint import f


def run(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);old=load(source/'report.json');report={'version':VERSION,'real':[],
        'source_labels_used':False,'accuracy_measured':False,'production_modified':False}
    for name in ('catalog_resolution.css','Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    asset=Path(__file__).parent/'visual_review_assets'/'segment_contrast.js';shutil.copyfile(asset,output/asset.name)
    write(output/'run-contract.json',{'version':VERSION,'source_report_hash':digest(source/'report.json'),
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'ui_hash':digest(asset),
        'selection':'all frozen prior samples and boundaries; no case/label filter','rights':'local research only'})
    for row in old['real']:
        cid=row['case_id'];src=source/'real-cases'/cid;dst=output/'real-cases'/cid;dst.mkdir(parents=True);(dst/'samples').mkdir()
        provenance=load(src/'source-snapshot'/'case-provenance.json')['manifest_entry']
        assert provenance['split']=='train' and provenance['rights']['internal_research_use']
        for name,h in row['source_hashes'].items():assert digest(src/'source-snapshot'/name)==h
        shutil.copytree(src/'source-snapshot',dst/'source-snapshot')
        for name in ('plan.json','manifest.json','whole-score.html'):shutil.copyfile(src/name,dst/name)
        hashes={p.name:digest(p) for p in (src/'samples').glob('*.json')};counts=Counter();kinds=Counter();unique=set();examples=[]
        for i in range(row['samples']):
            baseline=load(src/'samples'/f'{i}.json');out=augment(baseline)
            # Test the full old contract, not only aggregate statistics.
            oldview={k:v for k,v in out.items() if k not in ('boundary_context_preview','boundary_figures_version')}
            oldview['boundaries']=[{k:v for k,v in b.items() if k!='boundary_figures'} for b in out['boundaries']]
            assert oldview==baseline
            for b in out['boundaries']:
                evidence=b['boundary_figures'];counts['boundaries']+=1;counts['boundary_'+evidence['status']]+=1
                if evidence['patterns']:counts['boundaries_with_patterns']+=1
                for p in evidence['patterns']:
                    kinds[p['kind']]+=1;unique.add((p['kind'],tuple(p['event_refs']),str(p['nonmember_span'])))
            if 'boundary_context_preview' in out:
                counts['previews']+=1;c=out['boundary_context_preview'];assert c['baseline_comparison']==baseline['preview_comparison']
                if c['newly_explained_cells']:counts['previews_with_added_explanation']+=1;examples.append(i)
                assert f(c['split_with_boundary_context']['note_time']['conditional_nonmember'])>=f(c['baseline_comparison']['split']['note_time']['conditional_nonmember'])
            write(dst/'samples'/f'{i}.json',out)
            if (i+1)%20==0:print(row['title'],i+1,'/',row['samples'],flush=True)
        assert hashes=={p.name:digest(p) for p in (src/'samples').glob('*.json')}
        assert digest(src/'plan.json')==digest(dst/'plan.json')==row['plan_sha256']
        write(dst/'baseline-sample-hashes.json',hashes)
        result={'case_id':cid,'title':row['title'],'samples':row['samples'],**dict(counts),'pattern_records_by_kind':dict(kinds),
            'unique_kind_event_extent_records':len(unique),'inspection_samples':examples,'plan_sha256':row['plan_sha256'],'source_hashes':row['source_hashes']}
        report['real'].append(result);print({k:v for k,v in result.items() if k not in ('source_hashes','inspection_samples')},flush=True)
    write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html?sample='+str(r['inspection_samples'][0] if r['inspection_samples'] else 0)+'">'+r['title']+'</a></li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>경계를 넘는 조건부 비화성음</h1><p>기존184표본/분할 가정을 유지합니다. 유지·분할(이전)·분할+경계 문맥을 비교합니다. 추가 설명은 정답 판정이 아니며, 바로가기는 사후 관찰용 사례입니다.</p><ul>'+links+'</ul><a href="report.json">보고서</a>',encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source,a.output)
