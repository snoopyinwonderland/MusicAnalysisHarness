"""Frozen 24-window before/after audit; no harmony selection or production writes."""
import argparse
from collections import Counter
from fractions import Fraction as F
import html
from pathlib import Path
import re
import shutil
from .formal_ir import q
from .harmony_arpeggio_benchmark import write, digest, check_roundtrip
from .harmony_shared_tone_trial import load
from .harmony_open_candidates import window
from .harmony_reattack_figures import assess, VERSION


def controls(output):
    from music21 import converter, pitch
    from .canonical import CanonicalIRBuilder
    from .formal_ir import FormalIRAdapter
    from .harmony_path_contrast_trial import control_xml
    half=F(1,2); quarter=F(1,4)
    specs={
        'passing':[('C4',0,1),('D4',1,half),('D4',F(3,2),half),('E4',2,2)],
        'neighbor':[('C4',0,1),('D4',1,half),('D4',F(3,2),half),('C4',2,2)],
        'rest_gap':[('C4',0,1),('D4',1,half),('D4',2,half),('E4',F(5,2),F(3,2))],
        'respelling':[('C4',0,1),('D#4',1,half),('E-4',F(3,2),half),('E4',2,2)]}
    rows=[]
    for kind,melody in specs.items():
        baseline=None
        for variant,tr,scale in [('base',0,F(1)),('transpose',2,F(1)),('scaled',0,half)]:
            dst=output/(kind+'-'+variant);dst.mkdir(parents=True)
            events=[(p,0,4,v) for p,v in [('C3','1'),('E3','2'),('G3','3')]]+[(p,t,d,'4') for p,t,d in melody]
            fixture={'scale':q(scale),'beat_type':int(4/scale),'events':[
                {'pitch':(pitch.Pitch(p).transpose('M2') if tr else pitch.Pitch(p)).nameWithOctave,
                 'start':q(t*scale),'duration':q(d*scale),'voice':v} for p,t,d,v in events]}
            xml=dst/'score.musicxml';xml.write_text(control_xml(fixture),encoding='utf-8')
            ir=FormalIRAdapter().convert(CanonicalIRBuilder().build(converter.parse(xml),xml),xml)
            check_roundtrip(fixture,ir)
            w=window(ir,{'start':q(0),'end':q(4*scale)});r=assess(ir,w)
            c=next(c for c in w['candidates'] if c['root']==tr and c['label'].endswith(':major'))
            roles=[e['conditional_role'] for x in r['records'] for e in x['candidate_explanations']
                   if e['candidate_ref']==c['candidate_id'] and e['conditional_role']]
            assert roles==([kind] if kind in ('passing','neighbor') else [])
            sig=(roles,sorted(g['attack_count'] for g in r['groups']))
            if baseline is None:baseline=sig
            else:assert sig==baseline
            write(dst/'canonical_music_ir.json',ir);write(dst/'result.json',r)
            rows.append({'case':dst.name,'passed':True,'roles':roles,'xml_sha256':digest(xml)})
    return rows


def page(src,dst):
    page=(src/'whole-score.html').read_text(encoding='utf-8')
    extra=r'''
box.append(text('h3','반복 재타격을 포함한 음형 (화음 유지 가정)'));
const figures=(data.reattack_figures.records||[]).map(v=>({v,e:v.candidate_explanations.find(e=>e.candidate_ref===r.candidate.candidate_id)}));
box.append(text('p','반복 포함 음형 '+figures.length+'개 · 조건부 설명 '+figures.filter(x=>x.e&&x.e.conditional_role).length+'개. 조건부 설명은 정답/추천 점수가 아닙니다.'));
for(const {v,e} of figures){
const d=document.createElement('details');d.append(text('summary',(e.conditional_role||e.status)+' · '+v.event_refs.length+'번 원 attack'));
const gs=v.group_refs.map(id=>data.reattack_figures.groups.find(g=>g.group_id===id));
d.append(text('p',gs.map(g=>g.pitch.spelling+' × '+g.attack_count).join(' → ')),text('p','그룹은 타이/지속음이 아닙니다. 강세·화성 리듬 미확정.'));
const show=text('button','앞·뒤 초록 / 가운데 주황으로 음형 보기');show.onclick=()=>mark({groups:{other:{member:{event_refs:[...gs[0].event_refs,...gs[2].event_refs]},nonmember_not_confirmed_nct:{event_refs:gs[1].event_refs}}}});
d.append(show,text('p','이 버튼의 색은 음형 안의 위치이며 실제 구성음/NCT 확정이 아닙니다.'));
for(const g of gs)d.append(text('p',g.attacks.map(a=>duration(a.span.start)+' → '+duration(a.span.end)+' quarter').join(' / ')));
box.append(d);}
'''
    needle='data.stages.forEach((s,i)=>'
    assert page.count(needle)==1
    page=page.replace(needle,extra+'\n'+needle)
    page=page.replace('시간별 화성 대안','반복음 포함 음형 대조')
    page=page.replace('</header>','<p>원 attack·음가 보존 / 반복 그룹은 지속음이 아님 / 원 화음 후보·선택 미변경. <a href="reattack-summary.json">전후 비교 결과</a></p></header>')
    (dst/'whole-score.html').write_text(page,encoding='utf-8')
    return set(re.findall(r'data-id="([^"]+)"[^>]*class="note"',page))


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);prior=load(source/'report.json')
    write(output/'run-contract.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),
        'selection':'all same 24 frozen physical-measure windows; no result or label filtering',
        'extra_context':False,'cohort':'same train works, not independent accuracy',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    report={'version':VERSION,'real':[],'production_modified':False,'accuracy_measured':False,'ranking_performed':False}
    for row in prior['real']:
        src=source/'real-cases'/row['case_id'];dst=output/'real-cases'/row['case_id'];dst.mkdir(parents=True)
        prov=load(src/'source-snapshot'/'case-provenance.json')
        if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not prov['manifest_entry']['rights']['internal_research_use']:raise ValueError('ineligible')
        for name,h in row['source_hashes'].items():
            if digest(src/'source-snapshot'/name)!=h:raise ValueError('source_changed')
        shutil.copytree(src/'source-snapshot',dst/'source-snapshot');(dst/'windows').mkdir()
        ir=load(src/'source-snapshot'/'candidate_revision_ir.json');manifest=load(src/'manifest.json')
        counts=Counter();used=set();examples=[];window_hashes={}
        for i,m in enumerate(manifest):
            path=src/'windows'/(str(i)+'.json');window_hashes[path.name]=digest(path)
            old=load(path);w=window(ir,m['span']);r=assess(ir,w);counts['windows']+=1
            assert [c['candidate'] for c in old['fixed_readings']]==w['candidates']
            counts['repeated_groups']+=sum(g['attack_count']>1 for g in r['groups'])
            counts['geometry_figures']+=len(r['records'])
            baseline={(e['path_ref'],v['middle_ref']) for v in w['conditional_figures']['records']
                      for e in v['path_explanations'] if e['conditional_role']}
            new=set();unique_figures=set()
            for v in r['records']:
                for e in v['candidate_explanations']:
                    if not e['conditional_role']:continue
                    counts['conditional_candidate_figure_pairs']+=1;unique_figures.add(v['evidence_id'])
                    new.update((e['candidate_ref'],sid) for sid in v['middle_refs'] if (e['candidate_ref'],sid) not in baseline)
                    examples.append({'window':i,'display':m['display'],'label':e['label'],'role':e['conditional_role'],
                        'figure_ref':v['evidence_id'],'group_pitches':[next(g['pitch']['spelling'] for g in r['groups'] if g['group_id']==gid) for gid in v['group_refs']]})
                for sid in v['event_refs']:used.update(w['event_units'][sid]['source_note_ids'])
            counts['unique_compatible_figures']+=len(unique_figures)
            counts['additional_candidate_sound_pairs']+=len(new)
            for g in r['groups']:
                for attack in g['attacks']:
                    s=next(s for s in ir['sounding_events'] if s['sounding_event_id']==attack['event_ref'])
                    assert attack['span']==s['span'] and attack['source_note_ids']==s['source_note_ids']
            # Enrich a copy only; old fixed candidates, stages, profiles and selection stay identical.
            old['reattack_figures']=r;write(dst/'windows'/path.name,old)
            del old['reattack_figures'];assert old==load(path) and digest(path)==window_hashes[path.name]
        write(dst/'manifest.json',manifest)
        write(dst/'reattack-summary.json',{'counts':dict(counts),'examples':examples,'input_window_hashes':window_hashes})
        rendered=page(src,dst);assert used<=rendered
        result={'case_id':row['case_id'],'title':row['title'],**dict(counts),'source_hashes':row['source_hashes'],
            'rendered_source_refs_verified':len(used),'examples':examples}
        report['real'].append(result);print(row['title']+': '+str(dict(counts)),flush=True)
    report['controls']=controls(output/'controls');write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html">'+html.escape(r['title'])+'</a></li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>반복 재타격을 포함한 조건부 음형</h1><p>같은 24개 창의 비교 · 정확도 평가/화음 선택 아님. 마디와 화음 유지 가설을 골라 반복 포함 음형을 확인합니다.</p><ul>'+links+'</ul><a href="report.json">보고서</a></html>',encoding='utf-8')
    print('Controls passed: '+str(len(report['controls'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.source,args.output)
