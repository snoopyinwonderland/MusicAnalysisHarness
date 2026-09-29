"""Unit27 all adjacent verified source-key changes in the train sonata cohort."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from .cadential_six_four_audit import digest, source_key
from .harmony_case_retrieval import load_prepared_package
from .harmony_review_cohort import validate_split
from .harmony_review_supplement import verified_annotations, context_excerpt
from .applied_chords import source_harmony
from .diatonic_modulation import VERSION, source_key_transitions, compare_context, observe_support


def build(manifest_path, output):
    out=Path(output)
    if out.exists():raise ValueError('output_exists')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    selected=[e for e in entries if e['split']=='train' and e['collection_id'] in ('mozart-sonatas','beethoven-sonatas')]
    if len({e['package_path'] for e in selected})!=len(selected):raise ValueError('duplicate_package')
    if any(e['rights'].get('internal_research_use') is not True for e in selected):raise ValueError('research_not_permitted')
    modules=['diatonic_modulation.py','diatonic_modulation_audit.py','applied_chords.py','seventh_context.py',
        'cadential_six_four_audit.py','harmony_case_retrieval.py','harmony_review_cohort.py',
        'harmony_review_supplement.py','foundation_sonata_audit.py','predominant_sonata_audit.py',
        'dominant_area_evidence.py','tonal_foundations.py','formal_ir.py','harmony_curriculum.py']
    out.mkdir(parents=True)
    contract={'version':VERSION,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'entries':selected,
        'selection':'all adjacent verified changed source keys, including parallel and remote keys',
        'context':'at most 3 original annotations before and 6 after; unknowns retained; full contiguous new-key run metadata',
        'source_conditioned':True,'production_enabled':False,'training_eligible':False,
        'code_hashes':{n:digest(Path(__file__).with_name(n)) for n in modules}}
    (out/'run-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[];scores=[];skipped=Counter()
    for e in selected:
        folder=Path(e['package_path'])
        if digest(e['score_source_path'])!=e['score_sha256']:raise ValueError('score_hash_mismatch')
        hashes={n:digest(folder/n) for n in ('canonical_music_ir.json','imported_annotations.jsonl','alignment_records.jsonl')}
        package=load_prepared_package(folder);ir=package['ir'];anns=package['annotations']
        if ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id']:raise ValueError('ir_identity_mismatch')
        verified,skips=verified_annotations(package,e);skipped.update(skips);valid={a['annotation_id'] for a in verified}
        rows=[];observations={}
        for a in anns:
            ok=a['annotation_id'] in valid;key=None;h=None;reason='unverified'
            if ok:
                try:key=source_key(a)
                except ValueError:reason='unsupported_source_key';skipped[reason]+=1
                else:
                    h=source_harmony(a,*key);reason='supported' if h else 'unsupported_chord'
            rows.append({'ref':a['annotation_id'],'span':(a.get('target') or {}).get('span'),
                         'verified':ok,'key':key,'hypothesis':h,'status':reason,
                         'source_cadence':a['raw_fields'].get('cadence') if ok else None})
        transitions=source_key_transitions(rows)
        for tr in transitions:
            i=tr['start_index'];start=max(0,i-3);stop=min(len(rows),i+6)
            # Stop at missing time, do not remove it and join across the hole.
            missing=[j for j in range(start,stop) if not rows[j]['span']]
            for j in missing:
                if j<i:start=max(start,j+1)
                else:stop=min(stop,j)
            context_rows=rows[start:stop]
            if missing:skipped['context_clipped_at_missing_span']+=1
            cx=compare_context(context_rows,tr['old_key'],tr['new_key'])
            span={'start':context_rows[0]['span']['start'],'end':context_rows[-1]['span']['end']}
            excerpt=context_excerpt(ir,span);support={}
            for r in context_rows:
                if r['hypothesis'] is not None:
                    if r['ref'] not in observations:observations[r['ref']]=observe_support(ir,r['span'],r['hypothesis'])
                    support[r['ref']]=observations[r['ref']]
            cid='u27_'+hashlib.sha256((ir['ir_document_id']+'|'+rows[i]['ref']).encode()).hexdigest()[:16]
            pattern_reviews=[{'refs':refs,
                'source_cadences':[m for m in cx['source_cadence_markers'] if m['ref'] in refs],
                'silent_spans_by_ref':{ref:support[ref]['silent_spans'] for ref in refs if ref in support and support[ref]['silent_spans']},
                'cadence_inferred':None,'warning':'harmonic shapes may cross a cadence, silence or phrase restart'}
                for refs in cx['predominant_dominant_tonic_shape_triples']]
            case={'case_id':cid,'concept_id':'hvl.unit27','identity':e,'package_hashes':hashes,
                'source_key_run':tr,'source_context':[{'annotation':a,'alignment_verified':a['annotation_id'] in valid} for a in anns[start:stop]],
                'source_key_run_annotations':anns[i:tr['stop_index']],
                'comparison_rows':context_rows,'comparison':cx,'pattern_reviews':pattern_reviews,
                'score_support':support,'context_excerpt':excerpt,
                'context_clipped_at_missing_span':bool(missing),
                'run_is_fully_observed':tr['stop_index']<=stop,'source_conditioned':True,
                'training_eligible':False,'production_enabled':False}
            path=out/(cid+'.json');path.write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
            triples=cx['predominant_dominant_tonic_shape_triples']
            records.append({'case_id':cid,'score':folder.name,'printed_measure':anns[i]['raw_fields'].get('mn'),
                'old_key':tr['old_key'],'new_key':tr['new_key'],'relation':cx['relation']['relation'],
                'source_run_duration':tr['duration_quarters'],'source_run_annotation_count':len(tr['annotation_refs']),
                'termination':tr['termination'],'run_is_fully_observed':case['run_is_fully_observed'],
                'common_triad_candidates':sum(r['common_triad_compatible'] is True for r in cx['rows']),
                'dominant_tonic_pairs':len(cx['dominant_tonic_shape_pairs']),'pd_d_t_triples':len(triples),
                'triples_all_have_vertical_support':sum(all(support.get(ref,{}).get('complete_vertical_matches') for ref in refs) for refs in triples),
                'triples_all_have_union_support':sum(all(ref in support and not support[ref]['missing_spellings'] for ref in refs) for refs in triples),
                'unknown_chords':sum(r['hypothesis'] is None for r in context_rows),
                'json_sha256':digest(path)})
        scores.append({'score':folder.name,'transitions':len(transitions),'package_hashes':hashes})
    summary={'score_count':len(scores),'case_count':len(records),
        'relations':dict(Counter(r['relation'] for r in records)),
        'with_common_triad_candidate':sum(r['common_triad_candidates']>0 for r in records),
        'with_dominant_tonic_pair':sum(r['dominant_tonic_pairs']>0 for r in records),
        'with_pd_d_t_triple':sum(r['pd_d_t_triples']>0 for r in records),
        'with_vertical_supported_triple':sum(r['triples_all_have_vertical_support']>0 for r in records),
        'with_union_supported_triple':sum(r['triples_all_have_union_support']>0 for r in records),
        'with_unknown_chord':sum(r['unknown_chords']>0 for r in records),
        'full_run_observed':sum(r['run_is_fully_observed'] for r in records),
        'terminations':dict(Counter(r['termination'] for r in records))}
    result={'version':VERSION,'summary':summary,'records':records,'scores':scores,'skipped':dict(skipped),
        'contract_sha256':digest(out/'run-contract.json'),'blind_accuracy_measured':False,
        'training_eligible':False,'production_enabled':False}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.manifest,a.output)['summary'],indent=2))
