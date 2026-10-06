"""Survey all ordinary-family candidate pairs on touching lattice intervals.

The plan is shape-only, never a winning progression. Duplicate candidate origins
are retained; a query budget abstains rather than choosing a favorite subset.
"""
from collections import defaultdict, Counter
from copy import deepcopy
from contextlib import nullcontext
from .harmony_joint import f
from .applied_chords import hypothesis, FAMILIES
from .seventh_context import chord
from .harmony_resolution_constraints import analyze as constraints

VERSION='candidate-relation-survey-0.2.0'
MINIMUM_GEOMETRY_SPAN_REUSES=16


def geometry_cache_policy(result,planned=None):
    """Geometry-only cost guard, never a harmonic/candidate pruning rule."""
    p=plan(result) if planned is None else planned
    spans=Counter()
    for pair in p['pairs']:
        left=result['edges'][pair['source']['edge']]
        right=result['edges'][pair['target']['edge']]
        spans[(f(left['span']['start']),f(right['span']['end']))]+=1
    reuse=sum(count-1 for count in spans.values())
    return {'enabled':reuse>=MINIMUM_GEOMETRY_SPAN_REUSES,
            'planned_queries':len(p['pairs']),'unique_context_spans':len(spans),
            'repeated_span_queries':reuse,'minimum_span_reuses':MINIMUM_GEOMETRY_SPAN_REUSES,
            'selection_uses_harmonic_labels':False,'queries_removed':0}


def signature(root,members):
    return (tuple(root),tuple(sorted(tuple(m) for m in members))) if root is not None else None


def plan(result):
    if result['status']!='ready':return {'status':result['status'],'pairs':[]}
    sources=defaultdict(list)
    for ei,edge in enumerate(result['edges']):
        for ri,r in enumerate(edge['readings']):
            key=signature(r.get('root_spelling'),r['members'])
            if key is not None:sources[(edge['to'],key)].append({'edge':ei,'reading':ri})
    pairs=[]
    for ei,edge in enumerate(result['edges']):
        for ri,r in enumerate(edge['readings']):
            root=r.get('root_spelling')
            if root is None:continue
            members={tuple(m) for m in r['members']}
            for quality in ('M','m'):
                if not {tuple(m) for m in chord(root,quality)['members']}<=members:continue
                for family in FAMILIES:
                    h=hypothesis(root,quality,family)['chord']
                    for src in sources[(edge['from'],signature(h['root'],h['members']))]:
                        pairs.append({'source':src,'target':{'edge':ei,'reading':ri},
                                      'family':family,'target_quality':quality})
    return {'version':VERSION,'status':'ready','pairs':pairs,
            'selection':'all touching intervals and all exact spelled ordinary-family pairs; blocked candidates retained',
            'selected':None,'source_labels_used':False}


def local_query(result,pair,ir,temporal=False,*,geometry_cache=None):
    left=result['edges'][pair['source']['edge']];right=result['edges'][pair['target']['edge']]
    lr=left['readings'][pair['source']['reading']];rr=right['readings'][pair['target']['reading']]
    a,b=f(left['span']['start']),f(right['span']['end'])
    if left['to']!=right['from']:raise ValueError('nonadjacent_interval_pair')
    points=result['plan']['points'][left['from']:right['to']+1]
    cells=[c for c in result['cells'] if a<=f(c['span']['start']) and f(c['span']['end'])<=b]
    events=[s for s in result['events'] if f(s['span']['start'])<b and f(s['span']['end'])>a]
    cut=left['to']-left['from'];last=len(points)-1
    local={'status':'ready','plan':{'context_span':{'start':points[0],'end':points[-1]},'points':points},
           'events':events,'cells':cells,'patterns':[],'withheld_pattern_reasons':{},
           'assignments':[{'assignment_id':'survey-no-links','links':[]}],
           'edges':[{'from':0,'to':cut,'span':left['span'],'readings':[lr]},
                    {'from':cut,'to':last,'span':right['span'],'readings':[rr]}]}
    try:
        engine=constraints
        if temporal:
            from .harmony_distributed_resolution import analyze as engine
        answer=engine(local,[{'edge':0,'reading':0},{'edge':1,'reading':0}],'survey-no-links',ir,
                      geometry_cache=geometry_cache)
    except ValueError as exc:
        if str(exc)!='nonpositive_sound_duration':raise
        # Grace/invalid zero timing is retained as an explicit unsupported case.
        # The constraint engine has already checked the IR/event identity.
        answer={'status':'nonpositive_sound_duration_unsupported','queries':[],
                'unsupported_event_refs':[s['sounding_event_id'] for s in events
                    if f(s['span']['end'])<=f(s['span']['start'])]}
    matching=[q for q in answer['queries'] if q['family']==pair['family']]
    temporal_matching=[q for q in answer.get('temporal_queries',[]) if q['family']==pair['family']]
    if answer['status']=='ready' and len(matching)!=1:raise ValueError('planned_relation_not_reproduced')
    if temporal and answer['status']=='ready' and len(temporal_matching)!=1:raise ValueError('planned_temporal_relation_not_reproduced')
    return {'status':answer['status'],'query':matching[0] if matching else None,
            'temporal_query':temporal_matching[0] if temporal_matching else None,
            'unsupported_event_refs':answer.get('unsupported_event_refs',[]),
            'local_context_span':local['plan']['context_span'],
            'parent_context_span':deepcopy(result['plan']['context_span']),
            'source_candidate_ref':lr['candidate_ref'],'source_alternative_index':lr['alternative_index'],
            'target_candidate_ref':rr['candidate_ref'],'target_alternative_index':rr['alternative_index'],
            'scope':'pair relationship evidence only; no final NCT, function or segmentation claim'}


def run(result,ir,max_pairs=512,temporal=False,*,geometry_cache=None,use_geometry_cache=True):
    if type(max_pairs) is not int or max_pairs<1:raise ValueError('invalid_pair_budget')
    p=plan(result);out={'version':VERSION,'plan':p,'results':[],'selected':None,'production_modified':False,'temporal_enabled':temporal}
    if p['status']!='ready':return {**out,'status':p['status']}
    if len(p['pairs'])>max_pairs:return {**out,'status':'pair_budget_abstention_no_pruning','max_pairs':max_pairs}
    if not p['pairs']:
        return {**out,'status':'ready','summary':{},'temporal_summary':{},'accuracy_measured':False}
    if type(use_geometry_cache) is not bool:raise ValueError('invalid_geometry_cache_flag')
    if geometry_cache is not None and not use_geometry_cache:raise ValueError('conflicting_geometry_cache_options')
    if use_geometry_cache and geometry_cache is None and geometry_cache_policy(result,p)['enabled']:
        from .harmony_voice_geometry_cache import VoiceGeometryCache
        geometry_cache=VoiceGeometryCache(ir)
    # Full IR identity is still checked in every query. Only geometry is reused,
    # within a snapshot-guarded session; no reference labels or winners are read.
    counts=Counter();temporal_counts=Counter()
    with geometry_cache.scope(ir) if geometry_cache is not None else nullcontext():
        for pair in p['pairs']:
            answer=local_query(result,pair,ir,temporal,geometry_cache=geometry_cache)
            counts[answer['query']['status'] if answer['query'] else answer['status']]+=1
            if temporal:temporal_counts[answer['temporal_query']['status'] if answer['temporal_query'] else answer['status']]+=1
            out['results'].append({'pair':pair,**answer})
    return {**out,'status':'ready','summary':dict(counts),'temporal_summary':dict(temporal_counts),'accuracy_measured':False}
