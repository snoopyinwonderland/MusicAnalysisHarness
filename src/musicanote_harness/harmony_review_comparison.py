"""Merge provenance-preserving queues and run bounded paired diagnostics, not accuracy."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from .formal_ir import q
from .harmony_joint import f,analyze_joint
from .harmony_temporal_shadow import analyze as temporal
from .harmony_review_cohort import validate_split


def semantic_key(r):
    span=r['target_span']
    if r.get('annotation_id'):
        origin=('annotation',r['annotation_id'])
    elif r.get('source_annotation_refs'):
        matches=[a for a in r['source_annotation_refs'] if a.get('target',{}).get('span') and
                 all(f(a['target']['span'][k])==f(span[k]) for k in ('start','end'))]
        if len(matches)!=1:raise ValueError('ambiguous_target_annotation')
        origin=('annotation',matches[0]['annotation_id'])
    else:
        refs=r.get('evidence',{}).get('event_refs')
        if not refs:raise ValueError('missing_geometry_identity')
        origin=('geometry',*refs)
    return (r['ir_document_id'],str(f(span['start'])),str(f(span['end'])),*origin)


def merge_rows(rows):
    merged={}
    for r in rows:
        if r['split']!='train':raise ValueError('non_train_case')
        key=semantic_key(r)
        if key not in merged:
            merged[key]={'case_id':'reviewm_'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:20],
                         'tags':[],'members':[],'target_span':r['target_span'],
                         **{k:r[k] for k in ('package_path','score_id','ir_document_id','work_family_id','collection','split','score_sha256','annotation_sha256','rights')},
                         'review_status':'unreviewed','musical_gold':False,'training_eligible':False}
        item=merged[key]
        for k in ('score_id','work_family_id','score_sha256','annotation_sha256','rights','package_path'):
            if item[k]!=r[k]:raise ValueError('duplicate_identity_conflict:'+k)
        item['members'].append(r)
        item['tags']=sorted(set(item['tags'])|set(r['tags']))
    for r in merged.values():r['members'].sort(key=lambda m:m['case_id'])
    return sorted(merged.values(),key=lambda r:r['case_id'])


def window_ir(ir,start,end):
    """Explicit experimental cropped input, not a persisted full Canonical IR."""
    if start<0 or end<=start:raise ValueError('invalid_window')
    events=[]
    for s in ir['sounding_events']:
        a,b=f(s['span']['start']),f(s['span']['end'])
        if a<end and b>start:
            events.append({**s,'span':{'start':q(max(a,start)-start),'end':q(min(b,end)-start)}})
    measures=[]
    for m in ir.get('measures',[]):
        a=f(m['global_start_quarter']);b=a+f(m['actual_duration_quarter'])
        if a<end and b>start:
            measures.append({**m,'global_start_quarter':q(max(a,start)-start),
                             'actual_duration_quarter':q(min(b,end)-max(a,start))})
    return {'sounding_events':events,'note_events':ir.get('note_events',[]),'measures':measures}


def target_segments(result,target_span,offset=Fraction(0)):
    """Display projection only: retain the actual inferred span, do not rescore."""
    a,b=f(target_span['start']),f(target_span['end'])
    if a<0 or b<=a:raise ValueError('invalid_target_span')
    projected=[]
    for s in result['segments']:
        x,y=f(s['span']['start'])+offset,f(s['span']['end'])+offset
        if x<b and y>a:
            projected.append({**s,'inferred_absolute_span':{'start':q(x),'end':q(y)},
                              'span':{'start':q(max(a,x)),'end':q(min(b,y))}})
    return projected


def compare_outputs(baseline,experiment,offset=Fraction(0),target_span=None):
    def boundaries(r):
        values={f(s['span']['start'])+offset for s in r['segments'][1:]}
        if target_span is not None:
            values={t for t in values if f(target_span['start'])<t<f(target_span['end'])}
        return values
    def segments(r):return target_segments(r,target_span,offset) if target_span is not None else r['segments']
    def labels(r):return [s['selected']['label'] for s in segments(r)]
    old,new=boundaries(baseline),boundaries(experiment)
    return {'baseline_segments':len(segments(baseline)),'experimental_segments':len(segments(experiment)),
            'added_boundaries':[q(t) for t in sorted(new-old)],'removed_boundaries':[q(t) for t in sorted(old-new)],
            'label_sequence_changed':labels(baseline)!=labels(experiment),
            'more_segments_review_flag':len(segments(experiment))>len(segments(baseline)),
            'musical_improvement':None,'oversegmentation_confirmed':False}


def build(manifest,inputs,output,smoke=False):
    raw=Path(manifest).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    bypackage={e['package_path']:e for e in entries}
    if len(bypackage)!=len(entries):raise ValueError('duplicate_manifest_package')
    rows=[];hashes={}
    for file in inputs:
        data=Path(file).read_bytes();hashes[str(Path(file).resolve())]=hashlib.sha256(data).hexdigest()
        for line in data.decode('utf-8').splitlines():
            r=json.loads(line);e=bypackage[r['package_path']]
            if r['split']!='train' or e['split']!='train':raise ValueError('non_train_case')
            for k in ('split','score_id','ir_document_id','work_family_id','score_sha256','annotation_sha256','rights'):
                if r[k]!=e[k]:raise ValueError('manifest_case_mismatch:'+k)
            if r.get('context_excerpt_path') and hashlib.sha256(Path(r['context_excerpt_path']).read_bytes()).hexdigest()!=r['context_sha256']:
                raise ValueError('context_hash_mismatch')
            rows.append(r)
    merged=merge_rows(rows);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'cases.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in merged),encoding='utf-8')
    plan=[];used=set();skips=Counter();cache={}
    for r in merged:
        if r['collection'] in used:continue
        if f(r['target_span']['end'])-f(r['target_span']['start'])>4:
            skips['target_longer_than_smoke_window']+=1;continue
        package=r['package_path'];entry=bypackage[package]
        if package not in cache:
            path=Path(package)/'canonical_music_ir.json';data=path.read_bytes();ir=json.loads(data)
            if ir['ir_document_id']!=entry['ir_document_id'] or ir['score']['score_id']!=entry['score_id']:
                raise ValueError('live_ir_identity_mismatch')
            if hashlib.sha256(Path(entry['score_source_path']).read_bytes()).hexdigest()!=entry['score_sha256']:
                raise ValueError('live_score_hash_mismatch')
            cache[package]=(ir,hashlib.sha256(data).hexdigest())
        ir,irhash=cache[package]
        if any(m.get('ir_sha256') and m['ir_sha256']!=irhash for m in r['members']):
            raise ValueError('saved_ir_hash_mismatch')
        start=max(Fraction(0),f(r['target_span']['start'])-1)
        end=f(r['target_span']['end'])+1
        analysis_span={'start':q(start),'end':q(end)}
        active=[s for s in ir['sounding_events'] if f(s['span']['start'])<end and f(s['span']['end'])>start]
        # Cost bounded independently of labels; this is a smoke sample, not representative eval.
        points={f(s['span'][k]) for s in active for k in ('start','end') if start<=f(s['span'][k])<=end}
        if len(points)>28 or len(active)>80:
            skips['smoke_complexity_limit']+=1;continue
        item={'case_id':r['case_id'],'collection':r['collection'],'tags':r['tags'],
              'absolute_window':analysis_span,'target_span':r['target_span'],'ir_sha256':irhash,
              'context_policy':'target plus one quarter each side; full-score original nearest voice neighbors',
              'selection':'first_stable_id_per_collection_after_size_filters','split':'train'}
        used.add(r['collection'])
        if smoke:
            baseline=analyze_joint(ir,analysis_span=analysis_span)
            experiment=temporal(ir,cell_divisions=2,analysis_span=analysis_span)
            detail={**item,'baseline':baseline,'experiment':experiment,
                'target_projection':{'baseline':target_segments(baseline,r['target_span']),
                                     'experiment':target_segments(experiment,r['target_span'])},
                'comparison':compare_outputs(baseline,experiment,target_span=r['target_span']),
                'limits':['Absolute score time; uncut events; target-only comparison',
                          'Bounded search is not equivalent to whole-score optimization',
                          'Source annotation span selects diagnostic target, never a required chord boundary',
                          'No boundary or label gold agreement metric','No short-change discount enabled',
                          'Compound pulse and polymeter unresolved; silence included up to requested end']}
            (out/(r['case_id']+'.json')).write_text(json.dumps(detail,indent=2),encoding='utf-8')
            item['comparison']=detail['comparison']
        plan.append(item)
    report={'version':'harmony-review-comparison-0.2.0','input_hashes':hashes,'manifest_sha256':hashlib.sha256(raw).hexdigest(),
            'input_cases':len(rows),'merged_cases':len(merged),'duplicates_combined':len(rows)-len(merged),
            'source_family_count':len({r['work_family_id'] for r in merged}),
            'plan':plan,'smoke_executed':smoke,'skipped':dict(skips),'production_enabled':False,
            'accuracy_measured':False,'reserved_contents_read':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--inputs',nargs='+',required=True);p.add_argument('--output',required=True);p.add_argument('--smoke',action='store_true')
    a=p.parse_args();build(a.manifest,a.inputs,a.output,a.smoke)
