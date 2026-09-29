"""Train-only new score trial with frozen source, labels and complete engraving."""
import argparse
from collections import Counter
from pathlib import Path
import html
import json
import shutil
from .formal_ir import q
from .harmony_joint import f
from .harmony_shared_tone_trial import load
from .harmony_arpeggio_benchmark import write,digest
from .harmony_distributed_readings import observe
from .harmony_path_explanation import explain
from .harmony_path_explanation_trial import review,verify
from .harmony_conditional_ornaments import assess,VERSION
from .harmony_ownership_diagnostic_review import position


def panel(folder,ir,results):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']};cards=[];payload=[]
    statuses={'conditional_ornament_compatible':'조건부 장식음과 양립','all_three_are_candidate_members':'세 음 모두 화음 구성음',
        'context_unresolved':'문맥 조건 부족','crosses_candidate_chord_change':'세 음 사이에 가정한 화음이 바뀜',
        'membership_or_spelling_not_sufficient':'양끝 구성음/가운데 비구성음 조건 부족'}
    for result in results:
        for row in result['records']:
            index=len(payload);payload.append([sounds[sid]['source_note_ids'] for sid in row['event_refs']])
            names=' → '.join(sounds[sid]['pitch']['spelling'].replace('-','♭') for sid in row['event_refs'])
            roles=' / '.join(('유지 가설' if p['path_ref'].startswith('merged') else '교체 가설')+': '+statuses[p['status']]+(' (전후 연장 가정 포함)' if p['uses_edge_extension_assumption'] else '') for p in row['path_explanations'])
            compatible=any(p['status']=='conditional_ornament_compatible' for p in row['path_explanations'])
            cards.append('<article><button data-ornament="'+str(index)+'">'+html.escape(position(ir,row['span']['start'])+' · '+names)+'</button><p>'+html.escape(roles)+'</p><p>'+('조건부 경과/보조 설명 가능' if compatible else '현재 장식음 판정 보류')+' · 확정 비화성음이 아닙니다. 원음·음가·화음 선택은 유지합니다.</p></article>')
    section='<section><h2>이번 추가: 경과·보조 형태 검토</h2><p>성립 후보뿐 아니라 판정하지 못한 음형도 표시합니다. 파랑=앞 음, 보라=중간음, 주황=뒤 음이며 색 자체는 구성음/비화성음 판정이 아닙니다.</p>'+(''.join(cards) or '<p>이번 저장 범위에서 연속 세 음 형태가 관측되지 않았습니다.</p>')+'</section>'
    script='<style>.orn-source{fill:#1971c2!important;color:#1971c2!important}.orn-middle{fill:#8e44ad!important;color:#8e44ad!important}.orn-target{fill:#c05600!important;color:#c05600!important}</style><script>const ornaments='+json.dumps(payload)+';'+r'''
const ornClasses=['orn-source','orn-middle','orn-target'];
const clearOrnaments=()=>document.querySelectorAll('.scorepage .note').forEach(n=>n.classList.remove(...ornClasses));
document.querySelectorAll('[data-case]').forEach(b=>b.addEventListener('click',clearOrnaments));
document.querySelectorAll('[data-ornament]').forEach(b=>b.addEventListener('click',()=>{
 clearOrnaments();document.querySelectorAll('.scorepage .note').forEach(n=>n.classList.remove('both_members','merged_only_member','split_only_member','neither_member','spelling_unresolved','mixed'));
 const ids=ornaments[+b.dataset.ornament];let first=null;
 for(const n of document.querySelectorAll('.scorepage .note')){const id=n.dataset.id||n.id;
  ids.forEach((refs,i)=>{if(refs.includes(id)){n.classList.add(ornClasses[i]);first=first||n;}});}
 if(first){first.scrollIntoView({block:'center',behavior:'smooth'});document.querySelector('#page-select').value=first.closest('.scorepage').id;}
}));</script>'''
    page=(folder/'whole-score.html').read_text(encoding='utf-8').replace('<aside>','<aside>'+section).replace('</html>',script+'</html>')
    (folder/'whole-score.html').write_text(page,encoding='utf-8')


def build(manifest,revision,key,output,measure_limit,regression):
    if output.exists():raise ValueError('choose_new_revision')
    if measure_limit<1:raise ValueError('positive_measure_limit_required')
    manifest_data=load(manifest)
    entries=[e for e in manifest_data['entries'] if e['collection_id']+'--'+Path(e['score_source_path']).stem==key]
    if len(entries)!=1:raise ValueError('score_identity_not_unique')
    entry=entries[0]
    if entry['split']!='train' or not entry['rights']['internal_research_use']:raise ValueError('train_internal_research_required')
    release=next(s for s in load(revision/'candidate_manifest.json')['scores'] if s['score']==key)
    src=revision/key;xml=Path(entry['score_source_path'])
    if digest(xml)!=entry['score_sha256'] or any(digest(src/n)!=h for n,h in release['hashes'].items()):raise ValueError('frozen_input_changed')
    output.mkdir(parents=True);dst=output/'real-cases'/key;shutil.copytree(src,dst);shutil.copyfile(xml,dst/xml.name)
    write(dst/'case-provenance.json',{'manifest_entry':entry,'revision':release,'review_status':'user_requested_training_case_not_blind_evaluation'})
    ir=load(dst/'canonical_music_ir.json');ms=sorted(ir['measures'],key=lambda m:m['sequential_measure_index']);last=ms[min(measure_limit,len(ms))-1]
    end=f(last['global_start_quarter'])+f(last['actual_duration_quarter']);span={'start':ms[0]['global_start_quarter'],'end':q(end)}
    plan={'version':VERSION,'score_key':key,'physical_measure_limit':measure_limit,'analysis_span':span,
        'selection_policy':'first_N_physical_measures_predeclared_no_annotation_label_or_success_filter',
        'manifest_sha256':digest(manifest),'revision_manifest_sha256':digest(revision/'candidate_manifest.json'),
        'source_hashes':{**release['hashes'],xml.name:digest(xml)},'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'annotation_labels_used_for_inference':False,'production_modified':False}
    write(output/'run-contract.json',plan)
    print('observing',key,'first',measure_limit,'physical measures',flush=True)
    observed=observe(ir,span);write(dst/'distributed-readings.json',observed);explanations=[];ornaments=[];checks=[]
    for candidate in observed['alternatives']:
        unit=f(candidate['beat_unit_quarter']);a,b=f(candidate['span']['start']),f(candidate['span']['end'])
        context={'start':q(max(f(span['start']),a-2*unit)),'end':q(min(end,b+2*unit))}
        result=explain(ir,candidate,context);checks.append(verify(ir,result));explanations.append(result);ornaments.append(assess(ir,result))
    write(dst/'path-explanation.json',{'version':VERSION,'records':explanations});write(dst/'conditional-ornaments.json',{'version':VERSION,'records':ornaments})
    rendered=review(dst,dst/xml.name,ir,explanations,key);panel(dst,ir,ornaments)
    unique={tuple(r['event_refs']) for o in ornaments for r in o['records'] if any(p['status']=='conditional_ornament_compatible' for p in r['path_explanations'])}
    regressions=[]
    for old in load(regression/'report.json')['real']:
        case=regression/'real-cases'/old['case_id'];old_ir=load(case/'candidate_revision_ir.json');old_results=load(case/'path-explanation.json')['records']
        if digest(case/'path-explanation.json')!=old['result_sha256']:raise ValueError('regression_input_changed')
        before=digest(case/'path-explanation.json');calculated=[assess(old_ir,r) for r in old_results]
        (output/'regression'/old['case_id']).mkdir(parents=True)
        write(output/'regression'/old['case_id']/'conditional-ornaments.json',{'records':calculated})
        assert digest(case/'path-explanation.json')==before
        regressions.append({'case_id':old['case_id'],'prior_result_sha256':before,'summaries':[r['summary'] for r in calculated]})
    assert all(digest(src/n)==h and digest(dst/n)==h for n,h in release['hashes'].items()) and digest(dst/xml.name)==entry['score_sha256']
    report={'version':VERSION,'score':key,'candidate_windows':len(explanations),'analysis_span':span,'observed_geometry_triples_with_overlap':sum(o['summary']['geometry_triples'] for o in ornaments),
        'conditional_ornament_triples_with_overlap':sum(o['summary']['conditional_ornament_triples'] for o in ornaments),'unique_conditional_triples':len(unique),
        'conditional_counts_are_independent_votes':False,'rendering':rendered,'verification':checks,'regression':regressions,
        'annotation_records_preserved':release['annotations'],'annotation_labels_used_for_inference':False,'accuracy_measured':False,'production_modified':False}
    write(output/'report.json',report);write(output/'verification.json',{'passed':True,'frozen_files_unchanged':True,'new_case_checks':checks})
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>베토벤 소나타 1번 검토</title><h1>새 악보의 조건부 장식음 검토</h1><p>선택된 앞 '+str(measure_limit)+'개 실물 마디를 계산했습니다. 악보는 전체 악장을 표시합니다. 주석과 원음은 보존했으며 자동 판정은 변경하지 않았습니다.</p><a href="real-cases/'+html.escape(key)+'/whole-score.html">'+html.escape(key)+' 전체 악장 보기</a><p><a href="report.json">검증 보고서</a></p></html>',encoding='utf-8')
    print({k:v for k,v in report.items() if k not in ('verification','regression')},flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--revision',type=Path,required=True);ap.add_argument('--score-key',required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--measures',type=int,default=32);ap.add_argument('--regression',type=Path,required=True)
    args=ap.parse_args();build(args.manifest,args.revision,args.score_key,args.output,args.measures,args.regression)
