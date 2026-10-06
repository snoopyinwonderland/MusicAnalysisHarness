"""Reproducible microtime audit of the same train contexts, plus XML controls."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import html
from pathlib import Path
import shutil
from .formal_ir import q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_candidate_catalog import propose
from .harmony_catalog_microtime import plan, scan, enrich, VERSION
from .harmony_catalog_resolution import compare
from .harmony_catalog_resolution_trial import page, label, control_specs


def controls(output):
    from music21 import converter, pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    from .engraving import musicxml_with_canonical_ids
    rows=[]
    for kind in ('direct','delayed','sequential','wrong','gap'):
        specs=control_specs('wrong' if kind=='wrong' else 'resolution')
        if kind in ('delayed','sequential','wrong','gap'):
            specs=[(p,F(5,2) if a==2 and v in ('2','4') else a,b,v) for p,a,b,v in specs]
        if kind=='sequential':specs=[('D4' if p=='G4' else p,a,F(5,2) if p=='G3' else b,v) for p,a,b,v in specs]
        if kind=='gap':specs=[(p,F(5,2) if a>=2 else a,b,v) for p,a,b,v in specs]
        signature=None
        for name,transpose,scale in [('base',False,F(1)),('M2',True,F(1)),('half',False,F(1,2))]:
            dst=output/(kind+'-'+name);dst.mkdir(parents=True)
            fixture={'scale':q(scale),'beat_type':int(4/scale),'events':[
                {'pitch':(pitch.Pitch(p).transpose('M2') if transpose else pitch.Pitch(p)).nameWithOctave,
                 'start':q(a*scale),'duration':q((b-a)*scale),'voice':v} for p,a,b,v in specs]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(fixture),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(fixture,ir);_,mapping=musicxml_with_canonical_ids(xml,ir);assert mapping['complete']
            left=propose(ir,{'start':q(0),'end':q(2*scale)});right=propose(ir,{'start':q(2*scale),'end':q(4*scale)})
            r=enrich(ir,left,right);base=compare(ir,left,right)
            for new,old in zip(r['edges'],base['edges']):assert {k:new[k] for k in old}==old
            e=next(e for e in r['edges'] if e['source_provider']==e['target_provider']=='base'
                   and e['family']=='V7' and e['target_root']==['A' if transpose else 'G',0]
                   and e['target_quality']=='M' and not e['target_missing_spellings'])
            expected_status='resolution_supported_hypothesis' if kind=='direct' else 'blocked_context' if kind=='gap' else 'shape_relation_only'
            assert e['status']==expected_status
            expected_time=(F(2) if kind=='direct' else F(5,2))*scale
            assert e['target_arrival']['cumulative_identity_time']==q(expected_time)
            assert (e['target_arrival']['first_simultaneous_identity_time'] is None)==(kind=='sequential')
            count=len(e['delayed_endpoint_hypotheses'])
            assert count==(0 if kind=='direct' else 1 if kind in ('wrong','sequential') else 2),(kind,count)
            current=(e['status'],count)
            if signature is None:signature=current
            else:assert signature==current
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',r)
            rows.append({'case':dst.name,'passed':True,'xml_sha256':digest(xml),'direct_status':e['status'],'delayed_relations':count})
    return rows


def coordinate(ir,t):
    m=next((m for m in ir['measures'] if f(m['global_start_quarter'])<=t<f(m['global_start_quarter'])+f(m['actual_duration_quarter'])),None)
    if not m:return 'quarter '+str(t)
    return str(m['printed_measure_number'])+'마디 +'+str(t-f(m['global_start_quarter']))+' quarter'


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);oldreport=load(source/'report.json')
    report={'version':VERSION,'real':[],'accuracy_measured':False,'production_modified':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.css','catalog_resolution.js'):shutil.copyfile(assets/name,output/name)
    for name in ('Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    write(output/'run-contract.json',{'version':VERSION,'baseline_report_sha256':digest(source/'report.json'),
          'selection':'all sounding attack/release anchors in same frozen first-eight-measure train contexts',
          'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
          'rights':'local research only; no redistribution approval'})
    for oldrow in oldreport['real']:
        cid=oldrow['case_id'];src=source/'real-cases'/cid;snap=src/'source-snapshot'
        prov=load(snap/'case-provenance.json')['manifest_entry']
        assert prov['split']=='train' and prov['rights']['internal_research_use']
        for name,h in oldrow['source_hashes'].items():assert digest(snap/name)==h
        ir=load(snap/'candidate_revision_ir.json');before=deepcopy(ir)
        manifests=load(src/'manifest.json')
        span={'start':manifests[0]['span']['start'],'end':manifests[-1]['span']['end']}
        dst=output/'real-cases'/cid;dst.mkdir(parents=True);(dst/'pairs').mkdir();(dst/'catalogs').mkdir()
        shutil.copytree(snap,dst/'source-snapshot')
        write(dst/'plan.json',plan(ir,span));manifest=[];counts=Counter();used=set();highlights=[]
        direct_pairs=set();delayed_pairs=set()
        for i,(spec,left,right,r) in enumerate(scan(ir,span)):
            counts.update(e['status'] for e in r['edges']);counts['edges']+=len(r['edges'])
            counts['late_cumulative_edges']+=sum(e['target_arrival']['cumulative_identity_time'] is not None and f(e['target_arrival']['cumulative_identity_time'])>f(spec['boundary']) for e in r['edges'])
            counts['delayed_endpoint_occurrences']+=sum(len(e['delayed_endpoint_hypotheses']) for e in r['edges'])
            for edge in r['edges']:
                if edge['status']=='resolution_supported_hypothesis':
                    direct_pairs.update(tuple(s['source_refs']) for s in edge['direct_voice_support'])
                delayed_pairs.update(tuple(s['source_refs']) for s in edge['delayed_endpoint_hypotheses'])
            r['display_notes']={}
            for side,cat in (('source',left),('target',right)):
                write(dst/'catalogs'/f'{i}-{side}.json',cat)
                cs={c['candidate_id']:c for c in cat['candidates']}
                for edge in r['edges']:edge[side+'_display_label']=label(cat,cs[edge[side+'_candidate_ref']],edge[side+'_alternative_index'])
                ids={nid for u in cat['providers']['base']['event_units'].values() for nid in u['source_note_ids']}
                r['display_notes'][side]=[n['note_id'] for n in ir['note_events'] if n['note_id'] in ids
                    and f(n['global_onset_quarter'])<f(cat['span']['end']) and f(n['global_onset_quarter'])+f(n['notated_duration_quarter'])>f(cat['span']['start'])]
                used.update(r['display_notes'][side])
            r['anchor']=spec;write(dst/'pairs'/f'{i}.json',r)
            manifest.append({'display':coordinate(ir,f(spec['boundary']))+' 경계 앞뒤 각 1분모박 · '+str(len(r['edges']))+'가설','span':r['span']})
            interesting=[j for j,e in enumerate(r['edges']) if e['status']=='resolution_supported_hypothesis' or e['delayed_endpoint_hypotheses']]
            if interesting:highlights.append({'pair':i,'edges':interesting})
        rendered=page(src,dst,manifest,oldrow['title'],'전체 악장 · 기존 첫 8개 물리 마디 안의 모든 실제 attack/release 시점 앞뒤 각 1분모박 비교. 검사 창은 확정 화음 범위가 아닙니다.')
        assert used<=rendered and ir==before
        write(dst/'manifest.json',manifest)
        row={'case_id':cid,'title':oldrow['title'],'windows':len(manifest),**dict(counts),'highlights':highlights,
             'source_hashes':oldrow['source_hashes'],'source_ir_unchanged':True,
             'direct_supported_unique_pairs':[list(p) for p in sorted(direct_pairs)],
             'delayed_unique_pairs':[list(p) for p in sorted(delayed_pairs)]}
        report['real'].append(row);print(row['title'],len(manifest),dict(counts),flush=True)
    report['xml_controls']=controls(output/'controls');write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html?pair='+str(r['highlights'][0]['pair'] if r['highlights'] else 0)+'">'+html.escape(r['title'])+'</a></li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>미세 시간축의 화음 후보 근거</h1><p>분산 도착의 관측 시점과 지연 연결은 직접 해결/최종 화음과 구별합니다. 후보 수는 정확도가 아닙니다.</p><ul>'+links+'</ul>',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
