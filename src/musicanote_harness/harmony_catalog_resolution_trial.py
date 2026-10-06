"""Frozen-catalog regression, authored XML controls and full-score review."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import html
from pathlib import Path
import re
import shutil
from .formal_ir import q
from .harmony_joint import f
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_candidate_catalog import propose
from .harmony_catalog_resolution import compare, VERSION


def control_specs(kind):
    events = [('D3',0,2,'1'),('F#4',1 if kind=='late' else 0,2,'2'),
              ('A4',0,2,'3'),('C5',0,2,'4'),('G3',2,4,'1'),
              ('E4' if kind=='wrong' else 'G4',2,4,'2'),('D5',2,4,'3'),('B4',2,4,'4')]
    if kind=='extended':events += [('E5',0,2,'5'),('D5',2,4,'5')]
    if kind=='enharmonic':events[1]=('G-4',0,2,'2')
    if kind=='distributed':events[3]=('C5',0,1,'4');events[1]=('F#4',1,2,'2')
    if kind=='leading7':
        events=[('F#3',0,2,'1'),('A3',0,2,'2'),('C4',0,2,'3'),('E-4',0,2,'4'),
                ('G3',2,4,'1'),('G3',2,4,'2'),('B3',2,4,'3'),('D4',2,4,'4')]
    return events


def controls(output):
    from music21 import converter, pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    from .engraving import musicxml_with_canonical_ids
    rows=[]
    for kind in ('resolution','wrong','late','extended','enharmonic','distributed','leading7'):
        baseline=None
        for variant,tr,scale in [('base',False,F(1)),('transpose',True,F(1)),('scaled',False,F(1,2))]:
            dst=output/(kind+'-'+variant);dst.mkdir(parents=True)
            fixture={'scale':q(scale),'beat_type':int(4/scale),'events':[
                {'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,
                 'start':q(a*scale),'duration':q((b-a)*scale),'voice':v} for p,a,b,v in control_specs(kind)]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(fixture),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(fixture,ir);_,mapping=musicxml_with_canonical_ids(xml,ir)
            assert mapping['complete']
            left=propose(ir,{'start':q(0),'end':q(2*scale)});right=propose(ir,{'start':q(2*scale),'end':q(4*scale)})
            keys=[{'key_id':'test-home','tonic':['D' if tr else 'C',0],'mode':'major','provenance':'authored_test_assumption'}]
            result=compare(ir,left,right,keys)
            provider='extended' if kind=='extended' else 'base';family='vii7' if kind=='leading7' else 'V7'
            edges=[e for e in result['edges'] if e['source_provider']==provider and e['target_provider']=='base'
                   and e['family']==family and e['target_root']==['A' if tr else 'G',0]
                   and e['target_quality']=='M' and not e['target_missing_spellings']]
            if kind=='enharmonic':assert not edges
            else:
                assert edges
                expected='shape_relation_only' if kind in ('wrong','distributed') else 'resolution_supported_hypothesis'
                assert all(e['status']==expected for e in edges),(kind,variant,[e['status'] for e in edges])
                if kind=='late':assert edges[0]['source_time']['terminal_support_span']['start']==q(scale)
            signature=sorted((e['status'],tuple(e['missing_direct_relations'])) for e in edges)
            if baseline is None:baseline=signature
            else:assert baseline==signature
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',result)
            rows.append({'case':dst.name,'xml_sha256':digest(xml),'passed':True,'matching_edges':len(edges),'signature':signature})
    return rows


def label(catalog,c,alternative_index=None):
    from .harmony_candidate_catalog import resolve
    raw=resolve(catalog,c['origin_pointer'])
    if alternative_index is not None and c['spelling_alternatives'][alternative_index]['root_spelling'] is not None:
        step,alter=c['spelling_alternatives'][alternative_index]['root_spelling']
        root=step+('#'*alter if alter>0 else 'b'*-alter)
        quality=raw.get('quality') or raw.get('family') or raw.get('label','').partition(':')[2]
        return root+':'+str(quality)
    return raw.get('label') or str(c['root']['spelling'] or c['tonal_coordinate'])+' '+str(raw.get('quality') or raw.get('family'))


def page(source,dst,manifest,title,introduction=None):
    original=(source/'whole-score.html').read_text(encoding='utf-8')
    start=original.index('<section class="scorepage"');end=original.index('</div></main>',start)
    score=original[start:end]
    options=''.join('<option value="'+str(i)+'">'+html.escape(r['display'])+'</option>' for i,r in enumerate(manifest))
    document='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>화음 후보의 해결 관계</title>
<link rel="stylesheet" href="../../catalog_resolution.css"><header><a href="../../index.html">검토 목록</a><h1>'''+html.escape(title)+''' · 후보의 해결 관계</h1>
<p>전체 악장 · 첫 8개 물리 마디의 인접 구간 비교. 마디선은 검사 좌표이며 새로 탐지한 화음 경계가 아닙니다.</p>
<p>파랑=출발 구간 · 초록=도착 구간 · 주황=두 구간에 지속하는 음. 기호는 도착 화음을 기준으로 한 기능 가설입니다. 곡의 조성·최종 화음·종지 판정은 별도입니다.</p></header>
<main><aside><label for="range">비교 구간</label><select id="range">'''+options+'''</select>
<label for="edge">화음 진행 가설 (추천 순서 아님)</label><select id="edge"></select><button id="show">두 구간을 악보에 표시</button><div id="details"></div></aside>
<div id="score">'''+score+'''</div></main><script src="../../catalog_resolution.js"></script></html>'''
    if introduction:
        document=document.replace('전체 악장 · 첫 8개 물리 마디의 인접 구간 비교. 마디선은 검사 좌표이며 새로 탐지한 화음 경계가 아닙니다.',html.escape(introduction))
    (dst/'whole-score.html').write_text(document,encoding='utf-8')
    return set(re.findall(r'data-id="([^"]+)"[^>]*class="note"',score))


def build(catalog_source,score_source,output,font):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True)
    frozen=load(catalog_source/'report.json');score_report=load(score_source/'report.json')
    report={'version':VERSION,'real':[],'accuracy_measured':False,'source_labels_used':False,'production_modified':False}
    write(output/'run-contract.json',{'version':VERSION,'catalog_report_sha256':digest(catalog_source/'report.json'),
        'score_report_sha256':digest(score_source/'report.json'),'selection':'all 7 adjacent pairs among each of the previous 8 frozen windows; same 3 train works',
        'reference_key_hypotheses':[],'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'rights':'local research artifacts; original sources not approved for redistribution'})
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.js','catalog_resolution.css'):shutil.copyfile(assets/name,output/name)
    shutil.copyfile(font,output/'Campania.woff')
    licence=font.with_name('Campania.LICENSE.txt')
    if licence.exists():shutil.copyfile(licence,output/licence.name)
    for row in score_report['real']:
        cid=row['case_id'];src=score_source/'real-cases'/cid;snap=src/'source-snapshot'
        provenance=load(snap/'case-provenance.json')
        if provenance['manifest_entry']['split']!='train' or not provenance['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        for name,h in row['source_hashes'].items():
            if digest(snap/name)!=h:raise ValueError('source_changed')
        ir=load(snap/'candidate_revision_ir.json');old=deepcopy(ir)
        dst=output/'real-cases'/cid;dst.mkdir(parents=True);(dst/'pairs').mkdir()
        shutil.copytree(snap,dst/'source-snapshot')
        windows=sorted((r for r in frozen['fixed_windows'] if r['case_id']==cid),key=lambda r:r['window'])
        cats=[]
        for w in windows:
            if w['input_sha256']!=digest(snap/'candidate_revision_ir.json'):raise ValueError('catalog_ir_changed')
            cats.append(load(catalog_source/'fixed-windows'/cid/(str(w['window'])+'.json')))
        manifest=[];counts=Counter();used=set()
        for i,(left,right) in enumerate(zip(cats,cats[1:])):
            before=deepcopy((left,right));r=compare(ir,left,right);assert before==(left,right)
            counts.update(e['status'] for e in r['edges']);counts['edges']+=len(r['edges'])
            counts['extended_source_edges']+=sum(e['source_provider']=='extended' for e in r['edges'])
            counts['edges_with_any_direct_support']+=sum(bool(e['direct_voice_support']) for e in r['edges'])
            counts['without_terminal_support']+=sum(not e['source_time']['terminal_support_span'] for e in r['edges'])
            counts['without_target_identity_at_boundary']+=sum(not e['target_identity_at_boundary'] for e in r['edges'])
            counts['without_complete_direct_relations']+=sum(bool(e['missing_direct_relations']) for e in r['edges'])
            display=windows[i]['display']+' ／ '+windows[i+1]['display']
            r['labels']={c['candidate_id']:label(cat,c) for cat in (left,right) for c in cat['candidates']}
            for side,cat in (('source',left),('target',right)):
                candidates={c['candidate_id']:c for c in cat['candidates']}
                for edge in r['edges']:
                    edge[side+'_display_label']=label(cat,candidates[edge[side+'_candidate_ref']],edge[side+'_alternative_index'])
            # Restrict notation highlights to notes overlapping each exact window.
            r['display_notes']={}
            for side,cat in (('source',left),('target',right)):
                ids={nid for u in cat['providers']['base']['event_units'].values() for nid in u['source_note_ids']}
                r['display_notes'][side]=[n['note_id'] for n in ir['note_events'] if n['note_id'] in ids
                    and f(n['global_onset_quarter'])<f(cat['span']['end'])
                    and f(n['global_onset_quarter'])+f(n['notated_duration_quarter'])>f(cat['span']['start'])]
                used.update(r['display_notes'][side])
            write(dst/'pairs'/f'{i}.json',r);manifest.append({'display':display,'span':r['span']})
        rendered=page(src,dst,manifest,row['title']);assert used<=rendered
        assert ir==old
        write(dst/'manifest.json',manifest)
        report['real'].append({'case_id':cid,'title':row['title'],'pairs':len(manifest),**dict(counts),
            'candidate_count_preserved':sum(len(c['candidates']) for c in cats),'source_hashes':row['source_hashes'],
            'referenced_notes_mapped':len(used),'catalog_and_ir_unchanged':True})
        print(row['title'],dict(counts),flush=True)
    report['xml_controls']=controls(output/'controls');write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html">'+html.escape(r['title'])+'</a></li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>공통 후보의 해결 관계 · 전체 악보 검토</h1><p>기존 train 3악장의 고정 24창 / 인접 21쌍. 정확도 평가·최종 분석이 아닌 문맥 근거 검증입니다.</p><ul>'+links+'</ul><a href="report.json">검증 보고서</a></html>',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for k in ('catalog-source','score-source','output','font'):parser.add_argument('--'+k,type=Path,required=True)
    a=parser.parse_args();r=build(a.catalog_source,a.score_source,a.output,a.font)
    print({'real_works':len(r['real']),'controls':len(r['xml_controls']),'output':str(a.output)})
