"""Append temporal evidence to every frozen held-boundary comparison."""
import argparse
from collections import Counter
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_boundary_observations import augment,VERSION


def run(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);previous=load(source/'report.json')
    report={'version':VERSION,'real':[],'source_labels_used':False,'accuracy_measured':False,
            'production_modified':False,'previous_hypotheses_unchanged':True}
    for name in ('catalog_resolution.css','Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    asset=Path(__file__).parent/'visual_review_assets'/'segment_contrast.js';shutil.copyfile(asset,output/asset.name)
    write(output/'run-contract.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'ui_sha256':digest(asset),
        'selection':'all 184 prior samples and 117 held-sound cuts; no new selection or candidate generation',
        'rights':'local research only'})
    for row in previous['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id'];dst.mkdir(parents=True);(dst/'samples').mkdir()
        snap=src/'source-snapshot';provenance=load(snap/'case-provenance.json')['manifest_entry']
        assert provenance['split']=='train' and provenance['rights']['internal_research_use']
        for name,h in row['source_hashes'].items():assert digest(snap/name)==h
        assert digest(src/'plan.json')==row['original_plan_sha256']
        assert digest(src/'held-cut-plan.json')==row['held_cut_plan_sha256']
        ir=load(snap/'candidate_revision_ir.json');shutil.copytree(snap,dst/'source-snapshot')
        for name in ('plan.json','held-cut-plan.json','manifest.json','counterfactual-checks.json','whole-score.html'):shutil.copyfile(src/name,dst/name)
        hashes={p.name:digest(p) for p in (src/'samples').glob('*.json')};counts=Counter()
        for i in range(row['samples']):
            baseline=load(src/'samples'/f'{i}.json');out=augment(ir,baseline)
            old={k:v for k,v in out.items() if k!='temporal_observations_version'}
            old['boundaries']=[{k:v for k,v in b.items() if k!='temporal_observations'} for b in out['boundaries']]
            assert old==baseline
            for b in out['boundaries']:
                e=b['temporal_observations'];counts['boundaries']+=1
                if e['status']!='ready':counts['abstentions']+=1;continue
                counts['ready']+=1;counts['cells']+=len(e['cells'])
                counts['lowest_pitch_changes']+=e['lowest_pitch_changed'] is True
                counts['lowest_pitch_unchanged']+=e['lowest_pitch_changed'] is False
                counts['lowest_pitch_change_unknown']+=e['lowest_pitch_changed'] is None
                for c in e['cells']:
                    counts['bass_'+c['bass_status']]+=1;counts['meter_'+c['meter']['status']]+=1
                counts['support_profiles']+=len(e['candidate_support_profiles'])
                counts['pattern_observations']+=len(e['pattern_observations'])
            write(dst/'samples'/f'{i}.json',out)
            if (i+1)%20==0:print(row['title'],i+1,'/',row['samples'],flush=True)
        assert hashes=={p.name:digest(p) for p in (src/'samples').glob('*.json')}
        write(dst/'baseline-sample-hashes.json',hashes)
        result={'case_id':row['case_id'],'title':row['title'],'samples':row['samples'],**dict(counts),
                'inspection_samples':row['inspection_samples'],'source_hashes':row['source_hashes'],
                'original_plan_sha256':row['original_plan_sha256'],'held_cut_plan_sha256':row['held_cut_plan_sha256']}
        report['real'].append(result);print({k:v for k,v in result.items() if k not in ('source_hashes','inspection_samples')},flush=True)
        path=dst/'whole-score.html';doc=path.read_text(encoding='utf8').replace(' · 지속음 내부 경계 검사',' · 경계의 실제 음·베이스·박절 근거')
        doc=doc.replace('<main>','<p>새 근거는 후보를 변경하지 않습니다. 최저음은 구조적 베이스가 아니며, 표기 박자의 분모 단위 위치는 강약 판정이 아닙니다.</p><main>')
        path.write_text(doc,encoding='utf8')
    write(output/'report.json',report)
    doc=(source/'index.html').read_text(encoding='utf8').replace('지속음 내부 경계 검사','경계의 실제 음·베이스·박절 근거')
    (output/'index.html').write_text(doc,encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source,a.output)
