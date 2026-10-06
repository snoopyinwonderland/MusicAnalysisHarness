"""Factored three-interval comparisons on a continuous repeated-lowest chain.

Every candidate stays visible. A clean membership-return witness is not a pedal
verdict, and no global voice/NCT assignment is selected by this module.
"""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_missing_evidence import validate_ir
from .harmony_repeated_bass import chains, compare_interval

VERSION='bass-return-comparison-0.1.0'


def upper_cells(lattice, chain):
    events={s['sounding_event_id']:s for s in lattice['events']}; rows=[]
    lo,hi=f(chain['observed_span']['start']),f(chain['observed_span']['end'])
    points=[p for p in lattice['plan']['points'] if lo<=f(p)<=hi]
    for a,b in zip(points,points[1:]):
        active=[s for s in events.values() if f(s['span']['start'])<f(b) and f(s['span']['end'])>f(a)]
        other=[s for s in active if s['sounding_event_id'] not in chain['event_refs']]
        rows.append({'span':{'start':deepcopy(a),'end':deepcopy(b)},
            'bass_event_refs':[s['sounding_event_id'] for s in active if s['sounding_event_id'] in chain['event_refs']],
            'other_event_refs':[s['sounding_event_id'] for s in other],
            'other_spellings':[list(p) for p in sorted({tuple(pitch_pair(s['pitch'])) for s in other})]})
    return rows


def compare_chain(lattice, chain, partition_budget=256):
    if type(partition_budget) is not int or partition_budget<1:raise ValueError('invalid_partition_budget')
    span=chain['observed_span'];points=lattice['plan']['points']
    start=next(i for i,p in enumerate(points) if f(p)==f(span['start']))
    end=next(i for i,p in enumerate(points) if f(p)==f(span['end']))
    cuts=list(combinations(range(start+1,end),2))
    out={'chain_ref':chain['chain_id'],'span':deepcopy(span),'upper_cells':upper_cells(lattice,chain),
         'planned_cut_pairs':[list(c) for c in cuts],'comparisons':[],'interval_tables':{},
         'pedal_confirmed':False,'selected':None,'bass_exempted':False}
    if len(cuts)>partition_budget:return {**out,'status':'partition_budget_abstention_no_pruning'}
    edges={(e['from'],e['to']):i for i,e in enumerate(lattice['edges'])}

    def table(a,b):
        if (a,b) not in edges:raise ValueError('missing_interval_edge')
        index=edges[(a,b)];key=str(index)
        if key not in out['interval_tables']:
            out['interval_tables'][key]=compare_interval(lattice,index,chain)
        return key,out['interval_tables'][key]

    def group(t,bass_member,clean):
        return [r['reading_index'] for r in t['readings'] if r['bass_is_member']==bass_member and
                (not clean or (not r['missing_members'] and not r['other_nonmember_refs'] and not r['candidate_blockers']))]

    whole_ref,whole=table(start,end)
    out['whole_interval_ref']=whole_ref
    out['whole_interval_clean_bass_member_indices']=group(whole,True,True)
    for first,second in cuts:
        refs=[];tables=[]
        for a,b in ((start,first),(first,second),(second,end)):
            ref,t=table(a,b);refs.append(ref);tables.append(t)
        shape=[group(t,member,False) for t,member in zip(tables,(True,False,True))]
        clean=[group(t,member,True) for t,member in zip(tables,(True,False,True))]
        bass_member_competition=[group(t,True,True) for t in tables]
        # These independent factors deliberately do not instantiate all triples.
        # Cross-interval voice/function consistency remains a separate obligation.
        product_count=lambda gs:len(gs[0])*len(gs[1])*len(gs[2])
        out['comparisons'].append({'cut_indices':[first,second],
            'cut_times':[deepcopy(points[first]),deepcopy(points[second])], 'interval_refs':refs,
            'shape_return_reading_groups':shape,'shape_combination_count':product_count(shape),
            'clean_return_reading_groups':clean,'clean_combination_count':product_count(clean),
            'clean_bass_member_competitor_groups':bass_member_competition,
            'clean_bass_member_competitor_count':product_count(bass_member_competition),
            'status':'clean_membership_return_possible' if all(clean) else 'membership_return_shape_only' if all(shape) else 'no_membership_return_shape',
            'joint_voice_assignment_verified':False,'nct_confirmed':False,'harmonic_change_confirmed':False,
            'clean_gate':'all spelled members observed; no other nonmembers or candidate blockers; middle bass not exempted'})
    return {**out,'status':'ready'}


def run(lattice,survey,ir):
    out={'version':VERSION,'status':survey['status'],'chain_comparisons':[],
         'gate_changed':False,'production_modified':False,'accuracy_measured':False}
    if survey['status']!='ready':return out
    validate_ir(lattice,ir);out['geometry']=chains(lattice,ir);counts=Counter()
    for chain in out['geometry']['chains']:
        answer=compare_chain(lattice,chain);out['chain_comparisons'].append(answer)
        counts['chains']+=1;counts['planned_partitions']+=len(answer['planned_cut_pairs'])
        for comparison in answer['comparisons']:counts[comparison['status']]+=1
    out.update(summary=dict(counts),limits=[
        'All two-cut partitions within each observed chain; not all score-wide harmonic paths.',
        'Factored membership triples preserve origins; joint voice/NCT/functional consistency not yet verified.',
        'Clean is a narrow observational contract, not a necessary condition for musical pedal or omitted chords.',
        'A whole-interval and all-bass-member competitors remain visible; no scoring by raw coverage.',
        'Observed chain can be truncated at context edges; no full pedal preparation/resolution claim.'])
    return out
