"""Train-only seventh/short-change/geometry review queue. Not gold annotations."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from .formal_ir import q
from .harmony_joint import f
from .harmony_review_cohort import validate_split
from .harmony_case_retrieval import load_prepared_package
from .harmony_curriculum import same_span
from .counterpoint_evidence import extract
from .predominant_sonata_audit import span_observation
from .tonal_foundations import spelled_seventh_shapes

SEVENTHS={'Mm7':'major_minor_seventh','MM7':'major_seventh','mm7':'minor_seventh',
          'o7':'diminished_seventh','%7':'half_diminished_seventh'}


def select_pools(pools,cap):
    selected={};strata={};coverage={}
    for tag,rs in sorted(pools.items()):
        byfamily=Counter();chosen=[]
        for r in sorted(rs,key=lambda x:x['case_id']):
            fam=r['work_family_id']
            if byfamily[fam]>=cap:continue
            byfamily[fam]+=1;chosen.append(r['case_id']);selected[r['case_id']]=r
        strata[tag]=chosen;coverage[tag]={'available':len(rs),'selected':len(chosen),'families':len(byfamily)}
    return selected,strata,coverage


def verified_annotations(package, entry):
    links=defaultdict(list)
    for x in package['alignments']:links[x['annotation_id']].append(x)
    valid=[];skips=Counter();seen=set()
    for a in package['annotations']:
        if a['annotation_id'] in seen:raise ValueError('duplicate_annotation_id')
        seen.add(a['annotation_id'])
        t=a.get('target') or {};align=links[a['annotation_id']]
        if (a.get('source_asset_sha256')!=entry['annotation_sha256'] or
            t.get('score_id')!=entry['score_id'] or t.get('ir_document_id')!=entry['ir_document_id'] or
            not t.get('span') or len(align)!=1 or align[0]['mapping_status'] not in ('exact','verified_transform') or
            not same_span(align[0]['target']['span'],t['span'])):
            skips['unverified_alignment']+=1;continue
        if f(t['span']['end'])<=f(t['span']['start']):
            skips['nonpositive_span']+=1;continue
        valid.append(a)
    return sorted(valid,key=lambda a:(f(a['target']['span']['start']),a['annotation_id'])),skips


def short_change(previous,current,following,ir):
    """One conventional notated beat or shorter, with BOTH adjacent labels changed."""
    ps,cs,ns=[a['target']['span'] for a in (previous,current,following)]
    if f(ps['end'])!=f(cs['start']) or f(cs['end'])!=f(ns['start']):return None
    def identity(a):
        r=a['raw_fields']
        return tuple(r.get(k,'') for k in ('globalkey','localkey','chord','relativeroot','pedal'))
    if not current['raw_fields'].get('chord') or identity(current) in (identity(previous),identity(following)):return None
    a,b=f(cs['start']),f(cs['end'])
    meters=[]
    for m in ir.get('measures',[]):
        x=f(m['global_start_quarter']);y=x+f(m['actual_duration_quarter'])
        if x<b and y>a:
            ts=m['time_signature'];meters.append((x,y,int(ts['beats']),int(ts['beat_type'])))
    if not meters or min(x for x,y,n,d in meters)>a or max(y for x,y,n,d in meters)<b:return None
    if len({(n,d) for x,y,n,d in meters})!=1:return None
    n,d=meters[0][2:];beat=Fraction(4,d)*(3 if n in (6,9,12) else 1)
    return {'duration_in_notated_beats':q((b-a)/beat),'beat_quarters':q(beat),
            'policy':'conventional_grouping_not_perceived_pulse'} if b-a<=beat else None


def context_excerpt(ir,span):
    a,b=f(span['start']),f(span['end'])
    grid=sorted({(f(m['global_start_quarter']),f(m['global_start_quarter'])+f(m['actual_duration_quarter'])) for m in ir['measures']})
    indices=[i for i,(x,y) in enumerate(grid) if x<b and y>a]
    left,right=(grid[max(0,indices[0]-1)][0],grid[min(len(grid)-1,indices[-1]+1)][1]) if indices else (max(Fraction(0),a-4),b+4)
    sounds=[s for s in ir['sounding_events'] if f(s['span']['start'])<right and f(s['span']['end'])>left]
    ids={nid for s in sounds for nid in s.get('source_note_ids',[])}
    return {'schema_name':'harmony-review-context-excerpt','schema_version':'0.1.0',
        'is_full_canonical_ir':False,'target_span':span,'context_span':{'start':q(left),'end':q(right)},
        'score_id':ir['score']['score_id'],'ir_document_id':ir['ir_document_id'],
        'sounding_events':sounds,'note_events':[n for n in ir['note_events'] if n['note_id'] in ids],
        'rest_events':[r for r in ir.get('rest_events',[]) if r.get('measure_id') in
                       {m['measure_id'] for m in ir['measures'] if f(m['global_start_quarter'])<right and f(m['global_start_quarter'])+f(m['actual_duration_quarter'])>left}],
        'measures':[m for m in ir['measures'] if f(m['global_start_quarter'])<right and f(m['global_start_quarter'])+f(m['actual_duration_quarter'])>left],
        'policy':'original global coordinates; full event durations retained; original XML needed for full engraving'}


def build(manifest_path,output,cap=3):
    if cap<1:raise ValueError('positive_cap_required')
    raw=Path(manifest_path).read_bytes();entries=json.loads(raw)['entries'];validate_split(entries)
    pools=defaultdict(list);packages={};errors=[];skips=Counter();source_fields=Counter();counts=[]
    for e in entries:
        if e['split']!='train':continue
        try:
            p=load_prepared_package(e['package_path']);ir=p['ir']
            if (ir['ir_document_id']!=e['ir_document_id'] or ir['score']['score_id']!=e['score_id'] or
                hashlib.sha256(Path(e['score_source_path']).read_bytes()).hexdigest()!=e['score_sha256']):
                raise ValueError('source_identity_mismatch')
            annotations,skip=verified_annotations(p,e);skips.update(skip)
            geometry=extract(ir)['records'];packages[e['package_path']]=(p,e)
            def add(identity,span,tags,refs,evidence):
                cid='reviewx_'+hashlib.sha256((ir['ir_document_id']+'|'+identity).encode()).hexdigest()[:20]
                r={'case_id':cid,'package_path':e['package_path'],'score_id':e['score_id'],
                    'ir_document_id':ir['ir_document_id'],'work_family_id':e['work_family_id'],
                    'collection':e['collection_id'],'split':'train','target_span':span,'tags':tags,
                    'source_annotation_refs':refs,'evidence':evidence,'rights':e['rights'],
                    'score_sha256':e['score_sha256'],'annotation_sha256':e['annotation_sha256'],
                    'source_musicxml':e['score_source_path'],'review_status':'unreviewed',
                    'musical_gold':False,'training_eligible':False}
                for tag in tags:pools[tag].append(r)
            for i,a in enumerate(annotations):
                r=a['raw_fields'];tags=[];ev={}
                source_fields.update(k for k,v in r.items() if v and any(x in k.lower() for x in ('nct','nonchord','non_chord','susp','passing','neighbor')))
                if r.get('chord_type') in SEVENTHS and not any(r.get(k) for k in ('changes','added_tones','special')):
                    tags.append('source_seventh_'+r['chord_type']);ev['source_seventh_quality']=SEVENTHS[r['chord_type']]
                if 0<i<len(annotations)-1:
                    short=short_change(annotations[i-1],a,annotations[i+1],ir)
                    if short:tags.append('source_short_change_candidate');ev['short_change']=short
                if tags:
                    context=annotations[max(0,i-1):i+2]
                    add(a['annotation_id'],a['target']['span'],tags,context,ev)
            for g in geometry:
                add('geometry|'+'|'.join(g['event_refs']),g['span'],['geometry_'+g['pattern']],[],g)
            counts.append({'package':e['package_path'],'annotations':len(annotations),'geometry':len(geometry)})
        except (ValueError,KeyError,TypeError,OSError) as exc:errors.append({'package':e['package_path'],'error':str(exc)})
    selected,strata,coverage=select_pools(pools,cap)
    out=Path(output);out.mkdir(parents=True,exist_ok=True);ctx=out/'contexts';ctx.mkdir(exist_ok=True)
    shape_count=0
    for r in selected.values():
        p,e=packages[r['package_path']];ir=p['ir'];excerpt=context_excerpt(ir,r['target_span'])
        path=ctx/(r['case_id']+'.json');content=json.dumps(excerpt,ensure_ascii=False,indent=2).encode('utf-8');path.write_bytes(content)
        r['context_excerpt_path']=str(path.resolve());r['context_sha256']=hashlib.sha256(content).hexdigest()
        r['ir_sha256']=hashlib.sha256((Path(r['package_path'])/'canonical_music_ir.json').read_bytes()).hexdigest()
        if 'source_seventh_quality' in r['evidence']:
            obs=span_observation(ir,r['target_span']);quality=r['evidence']['source_seventh_quality']
            shapes=[{'span':s['span'],'shapes':spelled_seventh_shapes([tuple(n['pitch']) for n in s['events']])} for s in obs['slices']]
            matched=any(any(x['quality']==quality for x in s['shapes']) for s in shapes)
            r['evidence']['vertical_seventh_shapes']=shapes;r['evidence']['source_quality_shape_present']=matched
            r['evidence']['root_function_compared']=False;shape_count+=int(matched)
    report={'version':'harmony-review-supplement-0.1.0','manifest_sha256':hashlib.sha256(raw).hexdigest(),
        'packages':counts,'errors':errors,'skipped':dict(skips),'coverage':coverage,'unique_selected':len(selected),
        'selected_seventh_with_matching_vertical_quality':shape_count,'nct_like_nonempty_source_field_names':dict(source_fields),
        'unfilled':['human_verified_nct','human_verified_omission','approved_blind_evaluation'],
        'reserved_contents_read':False,'production_enabled':False,'per_family_per_tag_cap':cap,
        'policy':'source harmonic labels, observed geometry, and human validation kept separate; no model/API training'}
    (out/'cases.jsonl').write_text(''.join(json.dumps(selected[k],ensure_ascii=False)+'\n' for k in sorted(selected)),encoding='utf-8')
    (out/'strata.json').write_text(json.dumps(strata,indent=2),encoding='utf-8')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:v for k,v in report.items() if k!='packages'}


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--manifest',required=True);a.add_argument('--output',required=True)
    args=a.parse_args();print(json.dumps(build(args.manifest,args.output),indent=2))
