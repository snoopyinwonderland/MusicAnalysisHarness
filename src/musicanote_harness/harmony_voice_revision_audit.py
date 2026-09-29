"""Frozen voice-provenance ablation, not production migration or voice inference."""
import argparse
from collections import Counter
import html
from pathlib import Path
import shutil
from .harmony_arpeggio_benchmark import write,digest
from .harmony_shared_tone_trial import load
from .source_note_mapping_audit import compare as xml_compare,xml_inventory
from .source_sequence_audit import xml_rows
from .harmony_joint import f
from .harmony_reading_voice_context import compare as voice_compare
from .harmony_reading_contrast import compare as contrast_compare

VERSION='harmony-voice-revision-audit-0.1.0'


def compatibility(before,after,candidate,context_span=None):
    """Only compare frozen hypotheses when every referenced sound is identical."""
    old={s['sounding_event_id']:s for s in before['sounding_events']}
    new={s['sounding_event_id']:s for s in after['sounding_events']}
    referenced=set(candidate['event_refs'])
    if context_span:
        a,b=f(context_span['start']),f(context_span['end'])
        referenced.update(sid for sounds in (old,new) for sid,s in sounds.items() if f(s['span']['start'])<b and f(s['span']['end'])>a)
    changed=[ref for ref in sorted(referenced) if ref not in old or new.get(ref)!=old[ref]]
    return {'compatible':not changed,'changed_or_missing_sound_refs':changed}


def link_changes(before,after):
    a={tuple(p['source_refs']):p for p in before['voice_observations']['links']}
    b={tuple(p['source_refs']):p for p in after['voice_observations']['links']}
    return {'same_pairs':len(a.keys() & b.keys()),'lost_pairs':[a[k] for k in sorted(a.keys()-b.keys())],
            'new_pairs':[b[k] for k in sorted(b.keys()-a.keys())],
            'before_abstentions':before['voice_observations']['abstentions'],
            'after_abstentions':after['voice_observations']['abstentions']}


def blocked_examples(ir,voice):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    notes={n['note_id']:n for n in ir['note_events']};refs={r['source_ref_id']:r for r in ir['source_references']}
    identities={}
    for sid,s in sounds.items():
        keys={(notes[n]['part_id'],notes[n]['voice_id']) for n in s['source_note_ids']}
        if len(keys)==1:identities[sid]=next(iter(keys))
    result=[]
    for observation in voice['voice_observations']['event_statuses']:
        if observation['status']!='polyphonic_source_voice':continue
        sid=observation['event_ref'];s=sounds[sid]
        overlap=[t for tid,t in sounds.items() if tid!=sid and identities.get(tid)==identities.get(sid)
                 and f(t['span']['start'])<f(s['span']['end']) and f(t['span']['end'])>f(s['span']['start'])]
        result.append({'event_ref':sid,'pitch':s['pitch']['spelling'],'span':s['span'],
            'source_locators':[refs[notes[n]['source_ref_id']]['source_xpath'] for n in s['source_note_ids']],
            'source_voice_numbers':sorted({str(refs[notes[n]['source_ref_id']]['source_voice']) for n in s['source_note_ids']}),
            'overlapping_same_ir_voice':[{'event_ref':t['sounding_event_id'],'pitch':t['pitch']['spelling'],
                'span':t['span'],'source_locators':[refs[notes[n]['source_ref_id']]['source_xpath'] for n in t['source_note_ids']]} for t in overlap],
            'interpretation':'real_notational_polyphony_no_unique_inner_voice_assignment'})
    return result


def build(source,revision,output):
    if output.exists():raise ValueError('output_exists_choose_new_revision')
    oldreport=load(source/'report.json');manifest=load(revision/'candidate_manifest.json')
    output.mkdir(parents=True)
    write(output/'run-contract.json',{'version':VERSION,'source':str(source.resolve()),'revision':str(revision.resolve()),
        'source_report_sha256':digest(source/'report.json'),'revision_manifest_sha256':digest(revision/'candidate_manifest.json'),
        'code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},
        'scope':'frozen cohort cases with distributed candidates; not new score selection by result',
        'production_modified':False,'source_annotation_used':False,'frozen_costs_not_recomputed':True})
    results=[]
    for row in oldreport['real']:
        if not row['contrast_summary']['candidate_occurrences']:continue
        src=source/'real-cases'/row['case_id'];prov=load(src/'case-provenance.json');entry=prov['manifest_entry']
        if any(prov[k]['split']!='train' for k in ('case','manifest_entry','frozen_plan')) or not entry['rights']['internal_research_use']:raise ValueError('ineligible_case')
        key=entry['collection_id']+'--'+Path(entry['package_path']).name
        choice=next((s for s in manifest['scores'] if s['score']==key),None)
        if choice is None:
            results.append({'case_id':row['case_id'],'status':'revision_not_available'});continue
        revised=revision/key/'canonical_music_ir.json';oldpath=src/'canonical_music_ir.json';xmlpath=src/Path(entry['score_source_path']).name
        if digest(oldpath)!=row['ir_sha256'] or digest(revised)!=choice['hashes']['canonical_music_ir.json'] or digest(xmlpath)!=row['source_sha256']:raise ValueError('snapshot_hash_mismatch')
        old,new=load(oldpath),load(revised)
        if old['source_files']!=new['source_files']:raise ValueError('different_source_revision')
        raw=xml_inventory(xmlpath);oldcheck=xml_compare(old,raw);newcheck=xml_compare(new,raw)
        rawrows,_=xml_rows(xmlpath);by_path={r['xpath']:r for r in rawrows}
        refs={r['source_ref_id']:r for r in new['source_references']}
        paths=[refs[n['source_ref_id']]['source_xpath'] for n in new['note_events']]
        if len(paths)!=len(set(paths)):raise ValueError('duplicate_note_locator')
        if any(v['status']!='exact' for v in newcheck.values()):raise ValueError('revision_source_note_mismatch')
        for n in new['note_events']:
            rawrow=by_path[refs[n['source_ref_id']]['source_xpath']]
            if str(f(n['global_onset_quarter']))!=rawrow['global_onset']:raise ValueError('source_global_timing_mismatch')
        oldnotes={n['note_id']:n for n in old['note_events']};newnotes={n['note_id']:n for n in new['note_events']}
        if set(oldnotes)!=set(newnotes):raise ValueError('note_identity_changed')
        oldvoices={v['voice_id']:v for v in old['voices']};newvoices={v['voice_id']:v for v in new['voices']}
        disagreements=[];context_ids=set()
        original=load(src/'comparison.json');frozen_voice=load(src/'voice-context.json')['records']
        candidates=[c for run in original['runs'] for c in run['temporal']['alternatives']]
        if len(candidates)!=len(frozen_voice):raise ValueError('candidate_count_mismatch')
        runs=[]
        for c,v in zip(candidates,frozen_voice):
            if voice_compare(old,c)!=v:raise ValueError('baseline_not_reproduced')
            check=compatibility(old,new,c,v['context_span'])
            if not check['compatible']:
                runs.append({'candidate_ref':c['evidence_id'],'status':'sound_membership_changed_reinference_required',**check});continue
            revised_voice=voice_compare(new,c);contrast=contrast_compare(c,revised_voice)
            a,b=f(v['context_span']['start']),f(v['context_span']['end'])
            context_ids.update(n['note_id'] for n in new['note_events'] if f(n['global_onset_quarter'])<b and f(n['global_onset_quarter'])+f(n['notated_duration_quarter'])>a)
            runs.append({'candidate_ref':c['evidence_id'],'status':'compared','context_span':v['context_span'],
                'link_changes':link_changes(v,revised_voice),'revised_voice':revised_voice,'contrast':contrast,
                'polyphony_examples':blocked_examples(new,revised_voice),
                'xml_note_identity_checked':True,'contrapuntal_voice_identity_confirmed':False})
        for nid in sorted(context_ids):
            n=newnotes[nid];oldn=oldnotes[nid];ref=refs[n['source_ref_id']];expected=ref['source_voice']
            oldv=oldvoices[oldn['voice_id']]['source_voice_number'];newv=newvoices[n['voice_id']]['source_voice_number']
            if str(newv)!=str(expected):raise ValueError('revised_voice_disagrees_with_xml')
            if str(oldv)!=str(expected):disagreements.append({'note_id':nid,'source_xpath':ref['source_xpath'],'xml_voice':expected,
                'legacy_voice':oldv,'revised_voice':newv,'pitch':n['written_pitch']['spelling'],'global_onset_quarter':n['global_onset_quarter']})
        dst=output/'real-cases'/row['case_id'];shutil.copytree(src,dst)
        shutil.copyfile(revised,dst/'candidate_revision_ir.json')
        after_reasons=Counter();new_pairs={};polyphony={}
        for r in runs:
            if r['status']!='compared':continue
            after_reasons.update(r['link_changes']['after_abstentions'])
            for p in r['link_changes']['new_pairs']:new_pairs[tuple(p['source_refs'])]=p
            for p in r['polyphony_examples']:polyphony[p['event_ref']]=p
        summary={'context_note_count':len(context_ids),'context_legacy_voice_disagreements':len(disagreements),
            'before_xml_note_statuses':dict(Counter(v['status'] for v in oldcheck.values())),
            'after_xml_note_statuses':dict(Counter(v['status'] for v in newcheck.values())),
            'compared_candidate_occurrences':sum(r['status']=='compared' for r in runs),
            'blocked_candidate_occurrences':sum(r['status']!='compared' for r in runs),
            'lost_link_occurrences':sum(len(r['link_changes']['lost_pairs']) for r in runs if r['status']=='compared'),
            'new_link_occurrences':sum(len(r['link_changes']['new_pairs']) for r in runs if r['status']=='compared'),
            'differentiating_candidate_occurrences':sum(r['contrast']['has_family_differentiating_support'] for r in runs if r['status']=='compared'),
            'new_unique_pairs':len(new_pairs),'unique_polyphonic_source_events':len(polyphony),'after_abstention_occurrences':dict(after_reasons)}
        result={'case_id':row['case_id'],'revision_score':key,'summary':summary,'disagreements':disagreements,'runs':runs,
            'input_hashes':{'original_ir':digest(oldpath),'candidate_revision_ir':digest(revised),'xml':digest(xmlpath)},
            'new_unique_pairs':list(new_pairs.values()),
            'limits':['XML voice is a notational grouping, not a confirmed contrapuntal voice',
                'The corrected revision remains staff/part scoped; cross-staff melodic merging is not inferred',
                'Only eligible identical sounding candidates compared; no new harmonic search or cost reranking',
                'Occurrences overlap contexts; corrected global voice labels need not change local links']}
        write(dst/'voice-revision-audit.json',result)
        if (dst/'index.html').exists():
            text='<section id="voice-revision-audit"><h2>이번 단계: 원XML 성부 대조</h2><p>문맥의 고유 음표 '+str(len(context_ids))+'개 중 구형 성부 번호 불일치 '+str(len(disagreements))+'개. 교정 사본으로 직접 연결을 다시 검사했습니다.</p><p>겹치는 후보별 연결 변화: 추가 '+str(summary['new_link_occurrences'])+'회 / 소실 '+str(summary['lost_link_occurrences'])+'회. 한 계열만 지지하는 후보 '+str(summary['differentiating_candidate_occurrences'])+'개.</p><p>XML voice 확인은 음악적 내성 연결의 확정이 아닙니다. 음표 그룹 안의 성부 연결은 여전히 보류하며 기존 화음·비용·운영 화면은 그대로입니다.</p><a href="voice-revision-audit.json">XML 위치·성부 전후·보류 근거</a></section>'
            details='<p>새 고유 연결 '+str(len(new_pairs))+'개: '+html.escape(' / '.join(p['source_pitch']['spelling']+' → '+p['target_pitch']['spelling'] for p in new_pairs.values()) or '없음')+'</p>'
            if polyphony:
                ex=min(polyphony.values(),key=lambda p:(f(p['span']['start']),p['event_ref']))
                details+='<p>실제 동시 화음 보류 예: '+html.escape(ex['pitch']+' 와 '+', '.join(t['pitch'] for t in ex['overlapping_same_ir_voice']))+'가 같은 기보 성부에서 겹칩니다. 원XML voice '+html.escape(', '.join(ex['source_voice_numbers']))+'를 확인했지만, 이 음들 사이의 내성 진행을 아직 추정하지 않습니다.</p>'
            text=text.replace('</section>',details+'</section>')
            page=(dst/'index.html').read_text(encoding='utf-8').replace('</main>',text+'</main>');(dst/'index.html').write_text(page,encoding='utf-8')
        results.append({'case_id':row['case_id'],'status':'audited','summary':summary,'audit_sha256':digest(dst/'voice-revision-audit.json'),
            'html_sha256':digest(dst/'index.html') if (dst/'index.html').exists() else None})
        print(results[-1],flush=True)
    write(output/'report.json',{'version':VERSION,'cases':results,'production_modified':False,'accuracy_measured':False})
    body=''.join('<li><a href="real-cases/'+r['case_id']+'/index.html#voice-revision-audit">'+html.escape(r['case_id'])+'</a> '+html.escape(str(r.get('summary',{})))+'</li>' for r in results if r['status']=='audited')
    (output/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>XML 성부 대조</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:18px}li{margin:20px 0;line-height:1.7}</style><h1>구형 IR과 교정 성부 revision 비교</h1><p>같은 원본 악보·같은 화음 후보로 성부 연결만 대조합니다. 자동 화성 정답률 검사가 아닙니다.</p><ul>'+body+'</ul><a href="report.json">보고서</a></html>',encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--revision',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();build(args.source,args.revision,args.output)
