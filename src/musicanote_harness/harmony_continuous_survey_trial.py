"""Frozen-scope continuous-figure study with full-score inspection."""
import argparse
from collections import Counter
from copy import deepcopy
import html
from pathlib import Path
import re
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_joint import f
from .formal_ir import q
from .harmony_catalog_resolution_trial import label
from .harmony_catalog_microtime_trial import coordinate
from .harmony_continuous_survey import plan,analyze,VERSION


def page(src,dst,title,manifest):
    old=(src/'whole-score.html').read_text(encoding='utf-8')
    score=old[old.index('<section class="scorepage"'):old.index('</div></main>')]
    options=''.join('<option value="'+str(i)+'">'+html.escape(r['display'])+'</option>' for i,r in enumerate(manifest))
    doc='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>연속 음형·조건부 화음</title>
<link rel="stylesheet" href="../../catalog_resolution.css"><style>.ornament-mark,.ornament-mark *{fill:#a036af!important;color:#a036af!important}.range-box.context{border-color:#137786}.candidate-label{position:absolute;right:0;top:-24px;background:white;white-space:nowrap;font:16px system-ui}</style>
<header><a href="../../index.html">검사 목록</a><h1>'''+html.escape(title)+''' · 연속 음형 비교</h1>
<p>화성 정답을 보기 전에 정한 연속 3개 attack 음군. 청록=관찰 범위, 보라=선택한 조건부 장식음. 화음 후보는 범위 전체에 유지된다는 가정이며 정답/화성 경계가 아닙니다. 조성이 미확정이므로 로마자 기능은 붙이지 않습니다.</p></header>
<main><aside><label for="sample">검사 음형 (시간순, 성공 사례만 아님)</label><select id="sample">'''+options+'''</select>
<label for="candidate">화음·철자 후보 (추천 순서 아님)</label><select id="candidate"></select><div id="details"></div></aside>
<div id="score">'''+score+'''</div></main><script src="../../continuous_survey.js"></script></html>'''
    (dst/'whole-score.html').write_text(doc,encoding='utf-8')
    return set(re.findall(r'(?:id|data-id)="([^"]+)"',score))


def build(source,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);old=load(source/'report.json');report={'version':VERSION,'real':[],
        'accuracy_measured':False,'source_labels_used':False,'production_modified':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.css','continuous_survey.js'):shutil.copyfile(assets/name,output/name)
    for name in ('Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    write(output/'run-contract.json',{'version':VERSION,'baseline_report_sha256':digest(source/'report.json'),
        'selection':'every three consecutive attack groups in the same earlier frozen train contexts',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'asset_hashes':{name:digest(output/name) for name in ('catalog_resolution.css','continuous_survey.js')},
        'rights':'local research only'})
    for oldrow in old['real']:
        cid=oldrow['case_id'];src=source/'real-cases'/cid;snap=src/'source-snapshot'
        baseline_hashes={p.name:digest(p) for p in sorted((src/'pairs').glob('*.json'))}
        prov=load(snap/'case-provenance.json')['manifest_entry']
        assert prov['split']=='train' and prov['rights']['internal_research_use']
        for name,h in oldrow['source_hashes'].items():assert digest(snap/name)==h
        ir=load(snap/'candidate_revision_ir.json');before=deepcopy(ir)
        oldmanifest=load(src/'manifest.json')
        span={'start':q(min(f(x['span']['start']) for x in oldmanifest)),
              'end':q(max(f(x['span']['end']) for x in oldmanifest))}
        dst=output/'real-cases'/cid;dst.mkdir(parents=True);(dst/'samples').mkdir()
        shutil.copytree(snap,dst/'source-snapshot')
        selection=plan(ir,span);write(dst/'plan.json',selection) # Frozen BEFORE chord generation.
        plan_hash=digest(dst/'plan.json');counts=Counter();unique=set();highlights=[];manifest=[];used=set()
        lanes=sorted({tuple(s['lane']) for s in selection['samples']})
        for i,spec in enumerate(selection['samples']):
            r=analyze(ir,spec);counts[r['status']]+=1
            if 'catalog' in r:
                cs={c['candidate_id']:c for c in r['catalog']['candidates']}
                counts['catalog_candidates']+=len(cs)
                for c in r['conditions']:c['display_label']=label(r['catalog'],cs[c['candidate_ref']],c['alternative_index'])
            counts['conditions']+=len(r['conditions'])
            counts['blocked_conditions']+=sum(bool(c['abstention_reasons']) for c in r['conditions'])
            found=[]
            for ci,c in enumerate(r['conditions']):
                if c['patterns']:found.append(ci)
                for p in c['patterns']:unique.add((tuple(p['event_refs']),p['conditional_role']))
            if found:highlights.append({'sample':i,'conditions':found})
            a,b=(f(spec['span'][k]) for k in ('start','end'))
            r['display_note_refs']=[n['note_id'] for n in ir['note_events'] if f(n['global_onset_quarter'])<b
                and f(n['global_onset_quarter'])+f(n['notated_duration_quarter'])>a]
            used.update(r['display_note_refs']);write(dst/'samples'/f'{i}.json',r)
            manifest.append({'display':coordinate(ir,a)+' ~ '+coordinate(ir,b)+' · 기보성부 '+str(lanes.index(tuple(spec['lane']))+1),
                             'sample_id':spec['sample_id'],'span':spec['span']})
            if (i+1)%20==0:print(oldrow['title'],i+1,'/',len(selection['samples']),flush=True)
        ids=page(src,dst,oldrow['title'],manifest);assert used<=ids and ir==before and digest(dst/'plan.json')==plan_hash
        # Read-only source regression ledger: existing pair outputs remain untouched.
        hashes={p.name:digest(p) for p in sorted((src/'pairs').glob('*.json'))}
        assert hashes==baseline_hashes
        write(dst/'baseline-pair-hashes.json',hashes);write(dst/'manifest.json',manifest)
        row={'case_id':cid,'title':oldrow['title'],'samples':len(manifest),**dict(counts),
            'samples_with_conditional_patterns':len(highlights),'unique_event_triple_patterns':len(unique),
            'highlights':highlights,'plan_sha256':plan_hash,'baseline_pairs_preserved':len(hashes),
            'source_hashes':oldrow['source_hashes']}
        report['real'].append(row);print({k:v for k,v in row.items() if k not in ('highlights','source_hashes')},flush=True)
    write(output/'report.json',report)
    links=''.join('<li><a href="real-cases/'+r['case_id']+'/whole-score.html?sample='+str(r['highlights'][0]['sample'] if r['highlights'] else 0)+'&candidate='+str(r['highlights'][0]['conditions'][0] if r['highlights'] else 0)+'">'+html.escape(r['title'])+'</a> · '+str(r['samples'])+'구간 / 조건부 형태 '+str(r['samples_with_conditional_patterns'])+'구간</li>' for r in report['real'])
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>실제 연속 음형 검사</h1><p>전체 표본은 라벨 없이 미리 선택했습니다. 아래 바로가기는 출력에서 형태가 나온 첫 사례를 사후 선택한 것으로 정확도 평가 표본이 아닙니다.</p><ul>'+links+'</ul><a href="report.json">보고서</a></html>',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.source,a.output)
