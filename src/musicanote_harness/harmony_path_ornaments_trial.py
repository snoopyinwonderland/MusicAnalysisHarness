"""Candidate-conditioned ornaments on frozen voice-track alternatives."""
import argparse
from copy import deepcopy
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_catalog_resolution_trial import page
from .harmony_candidate_catalog import propose
from .harmony_path_ornaments import augment,VERSION


def stats(paths):
    cs=[c for p in paths.values() for c in p['conditions']]
    return {'conditions':len(cs),'blocked_conditions':sum(bool(c['abstention_reasons']) for c in cs),
            'patterns':sum(len(c['patterns']) for c in cs),
            'common_patterns':sum(p['common_to_all_assignments'] for c in cs for p in c['patterns'])}


def build(source,control_source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);old=load(source/'report.json')
    report={'version':VERSION,'real':[],'accuracy_measured':False,'production_modified':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.js','catalog_resolution.css'):shutil.copyfile(assets/name,output/name)
    for name in ('Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    write(output/'run-contract.json',{'version':VERSION,'baseline_report_sha256':digest(source/'report.json'),
        'control_report_sha256':digest(control_source/'report.json'),
        'selection':'all frozen windows and existing candidate-conditioned paths',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'rights':'local research only'})
    for oldrow in old['real']:
        cid=oldrow['case_id'];src=source/'real-cases'/cid;snap=src/'source-snapshot'
        prov=load(snap/'case-provenance.json')['manifest_entry']
        assert prov['split']=='train' and prov['rights']['internal_research_use']
        for name,h in oldrow['source_hashes'].items():assert digest(snap/name)==h
        ir=load(snap/'candidate_revision_ir.json');saved=deepcopy(ir)
        dst=output/'real-cases'/cid;dst.mkdir(parents=True);(dst/'pairs').mkdir()
        shutil.copytree(snap,dst/'source-snapshot');shutil.copytree(src/'catalogs',dst/'catalogs')
        manifest=load(src/'manifest.json');unique={};used=set();hashes={}
        for i in range(len(manifest)):
            prior=load(src/'pairs'/f'{i}.json');hashes[str(i)]=digest(src/'pairs'/f'{i}.json')
            left,right=[load(src/'catalogs'/f'{i}-{side}.json') for side in ('source','target')]
            result=augment(ir,prior,left,right)
            assert {k:result[k] for k in prior}==prior
            for pid,p in result['path_conditioned_ornaments']['paths'].items():
                unique[pid]=p
                units={sid for c in p['conditions'] for sid in c['event_units']}
                used.update(n for s in ir['sounding_events'] if s['sounding_event_id'] in units for n in s['source_note_ids'])
            write(dst/'pairs'/f'{i}.json',result)
        ids=page(src,dst,manifest,oldrow['title'],'전체 악장 · 성부 경로별 비화성음 설명을 화음 가정과 함께 비교합니다. 음표/음가를 삭제하거나 NCT를 확정하지 않습니다.')
        assert used<=ids and ir==saved
        write(dst/'manifest.json',manifest);write(dst/'input-pair-hashes.json',hashes)
        row={'case_id':cid,'title':oldrow['title'],'windows':len(manifest),'unique_paths':len(unique),
            **stats(unique),'old_results_unchanged':True,'source_hashes':oldrow['source_hashes']}
        report['real'].append(row);print(row,flush=True)
    controls=[]
    for row in old['reparsed_xml_controls']:
        src=control_source/'controls'/row['case']
        assert digest(src/'score.musicxml')==row['source_xml_sha256']
        ir=load(src/'canonical_music_ir.json');base=load(source/'controls'/row['case']/'result.json')
        left,right=[propose(ir,base['edges'][0][side+'_span']) for side in ('source','target')]
        r=augment(ir,base,left,right);assert {k:r[k] for k in base}==base
        summary=stats(r['path_conditioned_ornaments']['paths'])
        kind=row['case'].rsplit('-',1)[0]
        assert bool(summary['patterns'])==(kind in ('passing','neighbor','polyphony')),(row['case'],summary)
        expected_role='neighbor_candidate' if kind=='neighbor' else 'passing_candidate'
        for path in r['path_conditioned_ornaments']['paths'].values():
            for condition in path['conditions']:
                for pattern in condition['patterns']:
                    assert pattern['conditional_role']==expected_role
                    assert len(pattern['supporting_assignment_refs'])<len(condition['assignments'])
        assert not summary['common_patterns']
        dst=output/'controls'/row['case'];dst.mkdir(parents=True);write(dst/'result.json',r)
        controls.append({'case':row['case'],'passed':True,'source_xml_sha256':row['source_xml_sha256'],**summary})
    report['xml_snapshot_controls']=controls;write(output/'report.json',report)
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>경로별 조건부 비화성음</h1><p>경과/보조 형태는 성부와 화음 가정에 종속되며 정답 확정이 아닙니다.</p><a href="real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?pair=5&edge=8">K281 전체 악보</a><p><a href="report.json">검사 보고서</a></p></html>',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--control-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.control_source,a.output)
