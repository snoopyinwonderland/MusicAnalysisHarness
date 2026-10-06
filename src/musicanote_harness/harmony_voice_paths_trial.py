"""Frozen 142-window regression and re-parsed XML voice-track audit."""
import argparse
from copy import deepcopy
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_catalog_resolution_trial import page
from .harmony_voice_paths import augment,VERSION


def build(source,control_source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);old=load(source/'report.json')
    report={'version':VERSION,'real':[],'accuracy_measured':False,'production_modified':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.js','catalog_resolution.css'):shutil.copyfile(assets/name,output/name)
    for name in ('Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    write(output/'run-contract.json',{'version':VERSION,'baseline_report_sha256':digest(source/'report.json'),
        'control_report_sha256':digest(control_source/'report.json'),
        'selection':'all frozen windows; all accepted delayed-path contexts',
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
            for pid,p in result['continuous_voice_paths']['paths'].items():
                unique[pid]=p
                used.update(n for s in p.get('events',[]) for n in s['source_note_ids'])
            write(dst/'pairs'/f'{i}.json',result)
        ids=page(src,dst,manifest,oldrow['title'],'전체 악장 · 지역 대응을 연속 경로 후보로 조합했습니다. 연결되지 않은 음도 모두 보존하며 기존 화음 판정은 바꾸지 않았습니다.')
        assert used<=ids and ir==saved
        write(dst/'manifest.json',manifest);write(dst/'input-pair-hashes.json',hashes)
        row={'case_id':cid,'title':oldrow['title'],'windows':len(manifest),'unique_paths':len(unique),
            'complete_enumerations':sum(p.get('enumeration_complete',False) for p in unique.values()),
            'assignments':sum(len(p['assignments']) for p in unique.values()),
            'endpoint_same_track_assignments':sum(p.get('endpoint_same_track_assignments',0) for p in unique.values()),
            'old_results_unchanged':True,'source_hashes':oldrow['source_hashes']}
        report['real'].append(row);print(row,flush=True)
    from music21 import converter
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    controls=[]
    for row in old['xml_snapshot_controls']:
        xml=control_source/'controls'/row['case']/'score.musicxml'
        assert digest(xml)==row['source_xml_sha256']
        parsed=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
        saved=load(control_source/'controls'/row['case']/'canonical_music_ir.json')
        # Deterministic musical events/identities, not parser runtime metadata.
        for k in ('sounding_events','note_events','rest_events'):assert parsed[k]==saved[k],(row['case'],k)
        base=load(source/'controls'/row['case']/'result.json');r=augment(parsed,base)
        assert {k:r[k] for k in base}==base
        paths=list(r['continuous_voice_paths']['paths'].values());assert paths
        assert all(p['enumeration_complete'] and p['endpoint_same_track_assignments']==0 for p in paths)
        assert all(a['all_events_used_once'] and a['note_time_preserved'] for p in paths for a in p['assignments'])
        dst=output/'controls'/row['case'];dst.mkdir(parents=True)
        write(dst/'result.json',r)
        controls.append({'case':row['case'],'passed':True,'source_xml_sha256':row['source_xml_sha256'],
                         'assignments':sum(len(p['assignments']) for p in paths)})
    report['reparsed_xml_controls']=controls;write(output/'report.json',report)
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>연속 성부 경로 검토</h1><p>성부 분할은 가설입니다. 화음 판정과 구성음 총량은 바꾸지 않습니다.</p><a href="real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?pair=5&edge=8">K281 전체 악보</a><p><a href="report.json">검사 보고서</a></p></html>',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--control-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.control_source,a.output)
