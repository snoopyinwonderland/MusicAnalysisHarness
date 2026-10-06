"""Frozen microtime regression with complete path explanations and XML controls."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import shutil
from .formal_ir import q
from .harmony_arpeggio_benchmark import write,digest,check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_candidate_catalog import propose
from .harmony_catalog_paths import analyze,VERSION
from .harmony_catalog_resolution_trial import page


def control_specs(kind):
    names={'unfolding':('G4','D4','B4'),'passing':('G4','A4','B4'),
           'neighbor':('B4','C5','B4'),'enharmonic':('G4','G##4','B4')}.get(kind,('G4','A4','B4'))
    rows=[('D3',0,1,'1'),('F#3',0,1,'2'),('A3',0,1,'3'),('C5',0,1,'4'),('G3',1,3,'1'),('D4',1,3,'3')]
    rows += [(p,F(5+i,4)+(F(1,8) if kind=='gap' and i>0 else 0),
              F(6+i,4)+(F(1,8) if kind=='gap' and i>0 else 0),'4') for i,p in enumerate(names)]
    if kind=='polyphony':rows.append(('D5',F(5,4),F(3,2),'4'))
    return rows


def controls(output):
    from music21 import converter,pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    from .engraving import musicxml_with_canonical_ids
    rows=[]
    for kind in ('unfolding','passing','neighbor','enharmonic','gap','polyphony'):
        baseline=None
        for name,tr,scale in [('base',False,F(1)),('M2',True,F(1)),('half',False,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            spec={'scale':q(scale),'beat_type':int(4/scale),'events':[
                {'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,
                 'start':q(a*scale),'duration':q((b-a)*scale),'voice':v} for p,a,b,v in control_specs(kind)]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(spec),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            try:check_roundtrip(spec,ir)
            except ValueError as exc:raise ValueError(f'{kind}-{name}: {exc}') from exc
            _,mapping=musicxml_with_canonical_ids(xml,ir);assert mapping['complete']
            left=propose(ir,{'start':q(0),'end':q(scale)});right=propose(ir,{'start':q(scale),'end':q(3*scale)})
            r=analyze(ir,left,right);paths=list(r['arrival_path_assessment']['paths'].values())
            assert paths
            patterns=sorted({tag for p in paths for c in p['conditions'] if c['hypothesis']=='target_arrival_hypothesis' for tag in c['compatible_patterns']})
            expected=['chord_member_unfolding_compatible'] if kind=='unfolding' else ['local_ornament_geometry_compatible'] if kind in ('passing','neighbor') else []
            assert patterns==expected,(kind,name,patterns)
            assert all(p['observation']['all_intervening_refs_preserved'] and not p['observation']['voice_connection_confirmed'] for p in paths)
            if baseline is None:baseline=patterns
            else:assert patterns==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',r)
            rows.append({'case':dst.name,'passed':True,'xml_sha256':digest(xml),'patterns':patterns})
    return rows


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);old=load(source/'report.json')
    report={'version':VERSION,'real':[],'accuracy_measured':False,'production_modified':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.js','catalog_resolution.css'):shutil.copyfile(assets/name,output/name)
    for name in ('Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    write(output/'run-contract.json',{'version':VERSION,'baseline_report_sha256':digest(source/'report.json'),
          'selection':'all frozen 142 microtime windows; path explanations only for existing delayed endpoints',
          'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},'rights':'local research only'})
    for oldrow in old['real']:
        cid=oldrow['case_id'];src=source/'real-cases'/cid;snap=src/'source-snapshot'
        prov=load(snap/'case-provenance.json')['manifest_entry']
        assert prov['split']=='train' and prov['rights']['internal_research_use']
        for name,h in oldrow['source_hashes'].items():assert digest(snap/name)==h
        ir=load(snap/'candidate_revision_ir.json');saved=deepcopy(ir)
        dst=output/'real-cases'/cid;dst.mkdir(parents=True);(dst/'pairs').mkdir()
        shutil.copytree(snap,dst/'source-snapshot');shutil.copytree(src/'catalogs',dst/'catalogs')
        manifest=load(src/'manifest.json');counts=Counter();unique={};used=set();pair_hashes={}
        for i in range(len(manifest)):
            prior=load(src/'pairs'/f'{i}.json');pair_hashes[str(i)]=digest(src/'pairs'/f'{i}.json')
            left,right=[load(src/'catalogs'/f'{i}-{side}.json') for side in ('source','target')]
            result=analyze(ir,left,right)
            assert len(result['edges'])==len(prior['edges'])
            for k,v in result.items():
                if k not in ('edges','arrival_path_assessment'):assert prior[k]==v,k
            for new,e in zip(result['edges'],prior['edges']):
                for k,v in new.items():
                    if k!='arrival_path_refs':assert e[k]==v,k
            result['edges']=[{**a,**b} for a,b in zip(prior['edges'],result['edges'])]
            result={**prior,**result}
            for pid,p in result['arrival_path_assessment']['paths'].items():
                unique[pid]=p
                used.update(nid for e in p['observation']['events'] for nid in e['source_note_ids'])
                counts['condition_occurrences']+=len(p['conditions'])
                counts['compatible_condition_occurrences']+=sum(bool(c['compatible_patterns']) for c in p['conditions'])
                counts['local_cell_catalogs']+=len(p['alternative_cell_catalog_refs'])
            for side in ('source','target'):used.update(result['display_notes'][side])
            write(dst/'pairs'/f'{i}.json',result)
        ids=page(src,dst,manifest,oldrow['title'],'전체 악장 · 기존 미세 시간축 후보와 판정은 유지하고, 지연 연결 사이 실제 음표의 조건부 설명을 추가했습니다. 색칠은 검사 범위이며 확정 화음 경계가 아닙니다.')
        assert used<=ids and ir==saved
        write(dst/'manifest.json',manifest);write(dst/'input-pair-hashes.json',pair_hashes)
        row={'case_id':cid,'title':oldrow['title'],'windows':len(manifest),'unique_paths':len(unique),
             'blocked_unique_paths':sum(bool(p['observation']['abstention_reasons']) for p in unique.values()),
             **dict(counts),'old_results_unchanged':True,'source_hashes':oldrow['source_hashes']}
        report['real'].append(row);print(row,flush=True)
    report['xml_controls']=controls(output/'controls');write(output/'report.json',report)
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>지연 연결의 중간 경로 검토</h1><p>기존 직접/지연 판정은 그대로이며 음표 생략 없이 조건부 해석을 비교합니다.</p><a href="real-cases/reviewm_555ff701230fc0b8ee66/whole-score.html?pair=5&edge=8">모차르트 K281 전체 악보·미확정 경로</a><p><a href="report.json">전체 검사 보고서</a></p></html>',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
