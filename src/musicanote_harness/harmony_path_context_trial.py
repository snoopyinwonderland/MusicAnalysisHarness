"""Append bounded observations to every frozen path-review window."""
import argparse
from copy import deepcopy
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_catalog_resolution_trial import page
from .harmony_path_context import augment,VERSION


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True)
    old=load(source/'report.json')
    report={'version':VERSION,'real':[],'accuracy_measured':False,'production_modified':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.js','catalog_resolution.css'):shutil.copyfile(assets/name,output/name)
    for name in ('Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    write(output/'run-contract.json',{'version':VERSION,'baseline_report_sha256':digest(source/'report.json'),
        'selection':'all frozen windows, new observations only for existing delayed paths',
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
            result=augment(ir,prior)
            assert {k:result[k] for k in prior}==prior
            for pid,p in result['bounded_path_context']['paths'].items():
                unique[pid]=p
                ids=set(p['context_policy']['sound_refs'])
                used.update(n for s in ir['sounding_events'] if s['sounding_event_id'] in ids for n in s['source_note_ids'])
            write(dst/'pairs'/f'{i}.json',result)
        ids=page(src,dst,manifest,oldrow['title'],'전체 악장 · 관찰 문맥만 제한적으로 확장했습니다. 기존 화음 범위와 판정은 유지하며 다성음 연결은 복수 대안입니다.')
        assert used<=ids and ir==saved
        write(dst/'manifest.json',manifest);write(dst/'input-pair-hashes.json',hashes)
        groups={g['group_id']:g for p in unique.values() for g in p.get('polyphonic_observation',{}).get('groups',[])}
        row={'case_id':cid,'title':oldrow['title'],'windows':len(manifest),'unique_paths':len(unique),
             'accepted_contexts':sum(p['context_policy']['accepted'] for p in unique.values()),
             'polyphonic_groups':len(groups),'partial_assignments':sum(len(g['assignments']) for g in groups.values()),
             'local_cells':sum(len(p.get('alternative_cell_catalog_refs',[])) for p in unique.values()),
             'old_results_unchanged':True,'source_hashes':oldrow['source_hashes']}
        report['real'].append(row);print(row,flush=True)
    # Re-run the extension on all 18 previously parsed XML control snapshots.
    controls=[]
    for row in old['xml_controls']:
        src=source/'controls'/row['case']
        assert digest(src/'score.musicxml')==row['xml_sha256']
        ir=load(src/'canonical_music_ir.json');base=load(src/'result.json');r=augment(ir,base)
        assert {k:r[k] for k in base}==base
        for p in r['bounded_path_context']['paths'].values():
            assert p['context_policy']['accepted'] and p['observation']['all_intervening_refs_preserved']
        dst=output/'controls'/row['case'];dst.mkdir(parents=True)
        write(dst/'result.json',r)
        controls.append({'case':row['case'],'passed':True,'source_xml_sha256':row['xml_sha256']})
    report['xml_snapshot_controls']=controls;write(output/'report.json',report)
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>관찰 범위 확장·성부 복수 대응</h1><p>기존 화음 판정은 불변입니다. 대응 수는 확률이 아닙니다.</p><a href="real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?pair=5&edge=8">K281 전체 악보</a><p><a href="report.json">검사 보고서</a></p></html>',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
