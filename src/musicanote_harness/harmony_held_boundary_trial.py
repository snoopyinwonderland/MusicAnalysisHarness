"""Add held-sound boundary coverage, retaining every previous sample and file."""
import argparse
from collections import Counter
from pathlib import Path
import html
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .harmony_held_boundary_audit import plan,invalidate_condition,VERSION
from .harmony_segment_contrast import build
from .harmony_boundary_figures import augment,observe,compare
from .harmony_catalog_microtime_trial import coordinate
from .harmony_joint import f


def run(source,survey,output):
    if output.exists():raise ValueError('choose_new_output')
    output.mkdir(parents=True);previous=load(source/'report.json')
    report={'version':VERSION,'real':[],'source_labels_used':False,'production_modified':False,
            'accuracy_measured':False,'selection_is_independent_evaluation':False}
    assets=Path(__file__).parent/'visual_review_assets'
    for name in ('catalog_resolution.css','Campania.woff','Campania.LICENSE.txt'):shutil.copyfile(source/name,output/name)
    shutil.copyfile(assets/'segment_contrast.js',output/'segment_contrast.js')
    write(output/'run-contract.json',{'version':VERSION,'source_report_sha256':digest(source/'report.json'),
        'survey_report_sha256':digest(survey/'report.json'),'rights':'local research only',
        'code_hashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'ui_hash':digest(output/'segment_contrast.js'),
        'selection':'all held-sound crossed attacks in previous ready samples; no pitch/label filtering; new cuts only'})
    # Freeze ALL new cut plans before computing any new harmonic hypotheses.
    for old in previous['real']:
        src=source/'real-cases'/old['case_id'];dst=output/'real-cases'/old['case_id'];dst.mkdir(parents=True)
        write(dst/'held-cut-plan.json',[plan(load(src/'samples'/f'{i}.json')) for i in range(old['samples'])])
    for old in previous['real']:
        cid=old['case_id'];src=source/'real-cases'/cid;base=survey/'real-cases'/cid;dst=output/'real-cases'/cid
        snap=src/'source-snapshot';provenance=load(snap/'case-provenance.json')['manifest_entry']
        assert provenance['split']=='train' and provenance['rights']['internal_research_use']
        for name,h in old['source_hashes'].items():assert digest(snap/name)==h==digest(base/'source-snapshot'/name)
        assert digest(src/'plan.json')==digest(base/'plan.json')==old['plan_sha256']
        hashes={key:{p.name:digest(p) for p in (root/'samples').glob('*.json')} for key,root in [('previous',src),('survey',base)]}
        cut_hash=digest(dst/'held-cut-plan.json');plans=load(dst/'held-cut-plan.json')
        ir=load(snap/'candidate_revision_ir.json');shutil.copytree(snap,dst/'source-snapshot');(dst/'samples').mkdir()
        for name in ('plan.json','manifest.json','whole-score.html'):shutil.copyfile(src/name,dst/name)
        counts=Counter();kinds=Counter();unique=set();inspection=[];checks=[]
        for i,p in enumerate(plans):
            old_result=load(src/'samples'/f'{i}.json');baseline=load(base/'samples'/f'{i}.json')
            cuts=[c['boundary'] for c in p['cuts'] if not c['already_tested']]
            counts['old_held_cuts']+=sum(c['already_tested'] for c in p['cuts']);counts['new_held_cuts']+=len(cuts)
            if cuts:
                result=augment(build(ir,baseline,boundary_offsets=cuts))
                assert result['events']==old_result['events'] and result['assignments']==old_result['assignments']
                assert result['hold_readings']==old_result['hold_readings'] and result['total_note_time']==old_result['total_note_time']
            else:
                result={'status':'no_additional_held_boundary','baseline_status':old_result['status'],
                    'boundaries':[],'hold_readings':[],
                    'no_boundary_reason':'이 표본에는 추가로 검사할 지속음 내부 attack이 없습니다. 기존 분석은 이전 실험에 보존됩니다.'}
            result['display_note_refs']=old_result['display_note_refs'];result['held_cut_plan']=p
            result['previous_sample_sha256']=hashes['previous'][f'{i}.json']
            preview=None
            for bi,b in enumerate(result['boundaries']):
                b['display_boundary']=coordinate(ir,f(b['boundary']));counts['boundary_'+b['status']]+=1
                pats=b['boundary_figures']['patterns']
                if pats:counts['boundaries_with_patterns']+=1
                for pat in pats:
                    kinds[pat['kind']]+=1;unique.add((pat['kind'],tuple(pat['event_refs']),str(pat['nonmember_span'])))
                    li,ri,aid=pat['left_reading_indices'][0],pat['right_reading_indices'][0],pat['supporting_assignment_refs'][0]
                    c=compare(result,bi,0,li,ri,aid)
                    assert pat['pattern_id'] in {x['pattern_id'] for x in c['active_patterns']}
                    # Every real candidate must disappear when either required factor abstains.
                    for side,j in [('left',li),('right',ri)]:
                        blocked=observe(invalidate_condition(result,bi,side,j,'counterfactual_abstention'),bi)
                        assert not any(x['pattern_id']==pat['pattern_id'] and j in x[side+'_reading_indices'] for x in blocked['patterns'])
                    no_link=next(a['assignment_id'] for a in result['assignments'] if not a['links'])
                    nc=compare(result,bi,0,li,ri,no_link)
                    survives=pat['pattern_id'] in {x['pattern_id'] for x in nc['active_patterns']}
                    assert survives==(pat['kind']=='anticipation_held_candidate')
                    checks.append({'sample':i,'boundary':bi,'pattern_ref':pat['pattern_id'],'candidate_abstention_checked':True,
                                   'no_link_survives':survives,'time_conserved':True})
                    # Post-hoc inspection only; no candidate winner or label validation.
                    if preview is None or (pat['kind']=='prepared_suspension_candidate' and preview[1]!='prepared_suspension_candidate'):
                        preview=({'boundary':bi,'hold':0,'left':li,'right':ri,'assignment':aid,
                                  'policy':'post-hoc first suspension if present, otherwise first pattern; not best harmony'},pat['kind'])
            if preview:
                sel,kind=preview;result['preview_selection']=sel
                c=compare(result,sel['boundary'],sel['hold'],sel['left'],sel['right'],sel['assignment'])
                result['preview_comparison']=c['baseline_comparison'];result['boundary_context_preview']=c
                inspection.append({'sample':i,'kind':kind})
            write(dst/'samples'/f'{i}.json',result)
            if (i+1)%20==0:print(old['title'],i+1,'/',len(plans),flush=True)
        assert hashes=={key:{p.name:digest(p) for p in (root/'samples').glob('*.json')} for key,root in [('previous',src),('survey',base)]}
        assert digest(dst/'held-cut-plan.json')==cut_hash
        write(dst/'baseline-sample-hashes.json',hashes);write(dst/'counterfactual-checks.json',checks)
        doc=(dst/'whole-score.html').read_text(encoding='utf8').replace(' · 유지·분할 비교',' · 지속음 내부 경계 검사')
        doc=doc.replace('<main>','<p>이번 추가 검사: 관찰 성부가 음을 유지하는 동안 다른 음이 시작하는 경계. 기존 표본·화음 후보 생성 규칙·성부 연결은 유지합니다. 기본 선택은 사후 검사 예시이며 음악적 정답이 아닙니다.</p><main>')
        (dst/'whole-score.html').write_text(doc,encoding='utf8')
        row={'case_id':cid,'title':old['title'],'samples':len(plans),**dict(counts),
             'pattern_records_by_kind':dict(kinds),'unique_kind_event_extent_records':len(unique),
             'counterfactual_checks':len(checks),'inspection_samples':inspection,
             'held_cut_plan_sha256':cut_hash,'original_plan_sha256':old['plan_sha256'],'source_hashes':old['source_hashes']}
        report['real'].append(row);print({k:v for k,v in row.items() if k not in ('source_hashes','inspection_samples')},flush=True)
    write(output/'report.json',report)
    links=[]
    for r in report['real']:
        picks=r['inspection_samples'];pick=next((p for p in picks if p['kind']=='prepared_suspension_candidate'),picks[0] if picks else {'sample':0})
        links.append('<li><a href="real-cases/'+r['case_id']+'/whole-score.html?sample='+str(pick['sample'])+'">'+html.escape(r['title'])+'</a> · 새 경계 '+str(r['new_held_cuts'])+'</li>')
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><h1>지속음 내부 경계 검사</h1><p>기존184표본 범위 유지. 새 경계는 화성 정답이 아닌 다른 음의 실제 attack입니다. 조건부 후보 수는 정확도가 아닙니다. 링크는 사후 선택한 검사 예시입니다.</p><ul>'+''.join(links)+'</ul><a href="report.json">보고서</a>',encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--survey',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.source,a.survey,a.output)
