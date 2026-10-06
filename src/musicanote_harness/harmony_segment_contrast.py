"""Factorized, unranked hold/split readings on one fixed sounding-time grid.

All hypotheses share the same global voice assignment. Segment-local NCT
coverage is narrower than hold coverage; its absence is never a change penalty.
"""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_candidate_catalog import propose
from .harmony_catalog_resolution import pitch_pair
from .harmony_catalog_resolution_trial import label
from .harmony_reading_voice_context import spelled_height
from .harmony_path_ornaments import explain

VERSION='common-candidate-segment-contrast-0.1.0'
MAX_SIDE_CONDITION_ASSIGNMENTS=20000
STATES=('member','conditional_nonmember','unexplained_nonmember','spelling_unresolved')


def grid(events,span,boundary):
    a,b=f(span['start']),f(span['end']);cut=f(boundary)
    if not a<cut<b:raise ValueError('boundary_outside_span')
    points=sorted({a,b,cut}|{max(a,min(b,f(s['span'][k]))) for s in events for k in ('start','end')})
    return [{'span':{'start':q(lo),'end':q(hi)},
             'event_refs':[s['sounding_event_id'] for s in events if f(s['span']['start'])<hi and f(s['span']['end'])>lo]}
            for lo,hi in zip(points,points[1:])]


def readings(catalog,conditions,events):
    cs={c['candidate_id']:c for c in catalog['candidates']};out=[]
    for condition in conditions:
        c=cs[condition['candidate_ref']];i=condition['alternative_index'];members=c['spelling_alternatives'][i]['members']
        a,b=(f(c['span'][k]) for k in ('start','end'))
        states={s['sounding_event_id']:('spelling_unresolved' if spelled_height(s['pitch']) is None else
                'member' if pitch_pair(s['pitch']) in members else 'nonmember_not_confirmed_nct')
                for s in events if f(s['span']['start'])<b and f(s['span']['end'])>a}
        out.append({'candidate_ref':c['candidate_id'],'alternative_index':i,'span':deepcopy(c['span']),
            'display_label':label(catalog,c,i),'members':deepcopy(members),'event_states':states,
            'missing_spellings':deepcopy(c['missing_spellings_by_alternative'][i]),
            'condition':deepcopy(condition)})
    return out


def profile(cells,span,segments,assignment_ref):
    cursor=f(span['start']);totals={s:Fraction() for s in STATES};items=[]
    for r in segments:
        if f(r['span']['start'])!=cursor or f(r['span']['end'])<=cursor:raise ValueError('invalid_partition')
        cursor=f(r['span']['end'])
    if cursor!=f(span['end']):raise ValueError('invalid_partition')
    for cell in cells:
        a,b=(f(cell['span'][k]) for k in ('start','end'))
        active=[r for r in segments if f(r['span']['start'])<=a and b<=f(r['span']['end'])]
        if len(active)!=1:raise ValueError('grid_not_partitioned')
        r=active[0];cond=r['condition'];assignments={x['assignment_ref']:x for x in cond['assignments']}
        if not cond['abstention_reasons'] and assignment_ref not in assignments:raise ValueError('missing_shared_assignment')
        explained=set(assignments.get(assignment_ref,{}).get('conditionally_explained_nonmember_refs',[])) if not cond['abstention_reasons'] else set()
        for sid in cell['event_refs']:
            if sid not in r['event_states']:raise ValueError('missing_event_state')
            state=r['event_states'][sid]
            if state not in ('member','nonmember_not_confirmed_nct','spelling_unresolved'):raise ValueError('unknown_state')
            bucket=('conditional_nonmember' if sid in explained else 'unexplained_nonmember') if state=='nonmember_not_confirmed_nct' else state
            totals[bucket]+=b-a
            items.append({'event_ref':sid,'span':deepcopy(cell['span']),'bucket':bucket,'candidate_ref':r['candidate_ref']})
    return {'note_time':{k:q(v) for k,v in totals.items()},'total_note_time':q(sum(totals.values(),Fraction())),
            'items':items,'assignment_ref':assignment_ref,'selected':None}


def compare(result,boundary_index,hold_index,left_index,right_index,assignment_ref):
    if result['status']!='ready':raise ValueError('comparison_not_ready')
    if assignment_ref not in {a['assignment_id'] for a in result['assignments']}:raise ValueError('unknown_assignment')
    boundary=result['boundaries'][boundary_index]
    if boundary['status']!='ready':raise ValueError('boundary_not_ready')
    h=result['hold_readings'][hold_index];l=boundary['left']['readings'][left_index];r=boundary['right']['readings'][right_index]
    hp=profile(boundary['cells'],result['span'],[h],assignment_ref)
    cp=profile(boundary['cells'],result['span'],[l,r],assignment_ref)
    if hp['total_note_time']!=cp['total_note_time'] or hp['total_note_time']!=result['total_note_time']:raise ValueError('unequal_evidence')
    changes=[]
    for hi,ci in zip(hp['items'],cp['items']):
        if (hi['event_ref'],hi['span'])!=(ci['event_ref'],ci['span']):raise ValueError('unequal_cells')
        if hi['bucket']!=ci['bucket']:changes.append({'event_ref':hi['event_ref'],'span':hi['span'],'hold':hi['bucket'],'split':ci['bucket']})
    return {'hold':hp,'split':cp,'changed_readings':changes,
        'split_minus_hold':{k:q(f(cp['note_time'][k])-f(hp['note_time'][k])) for k in STATES},
        'same_member_spelling_sets':sorted(l['members'])==sorted(r['members']),
        'preferred':None,'probability':None,'harmonic_change_confirmed':False,
        'warning':'Segment-local NCT cannot cover cross-boundary figures; deltas are not likelihoods or segmentation scores.'}


def build(ir,baseline,*,boundary_offsets=None):
    span=baseline['sample']['span'];result={'version':VERSION,'span':deepcopy(span),'status':'baseline_abstention',
        'baseline_status':baseline['status'],'boundaries':[],'hold_readings':[],'selected':None,
        'production_modified':False,'source_labels_used':False,'ranking_performed':False,
        'limits':['Candidate generation uses all parts; NCT geometry uses the sampled explicit part/voice only.',
                  'Every comparison uses the same global voice assignment including the no-link alternative.',
                  'A split at an attack is a hypothesis, not a detected harmonic boundary.',
                  'Only one internal cut at a time; no multi-change inference.',
                  'Cross-boundary NCT, key/function, harmonic rhythm and inversion verdicts remain open.']}
    if baseline['status']!='evaluated':return result
    voices=baseline['voices'];a,b=(f(span[k]) for k in ('start','end'))
    events=[deepcopy(s) for s in ir['sounding_events'] if f(s['span']['start'])<b and f(s['span']['end'])>a]
    result.update(events=events,assignments=deepcopy(voices['assignments']),lane=deepcopy(voices['lane']),
        total_note_time=q(sum((min(b,f(s['span']['end']))-max(a,f(s['span']['start'])) for s in events),Fraction())))
    result['hold_readings']=readings(baseline['catalog'],baseline['conditions'],events)
    result['hold_candidates_without_spelling_refs']=baseline['candidates_without_spelling_refs']
    cuts=baseline['sample']['attack_group_onsets'][1:] if boundary_offsets is None else boundary_offsets
    if boundary_offsets is not None:
        times=[f(t) for t in cuts]
        observed={f(s['span']['start']) for s in events}
        if times!=sorted(set(times)) or any(not a<t<b or t not in observed for t in times):
            raise ValueError('invalid_observed_boundary_offsets')
        result['boundary_selection']='caller_supplied_observed_attacks_not_detected_harmony'
    for cut in cuts:
        row={'boundary':deepcopy(cut),'boundary_confirmed':False,'status':'ready','cells':grid(events,span,cut)}
        for side,part in [('left',{'start':span['start'],'end':cut}),('right',{'start':cut,'end':span['end']})]:
            cat=propose(ir,part);alts=[(c,i) for c in cat['candidates'] for i in range(len(c['spelling_alternatives']))]
            work=len(alts)*len(voices['assignments']);conditions=[]
            if work>MAX_SIDE_CONDITION_ASSIGNMENTS:row['status']='side_budget_abstention_no_pruning'
            else:conditions=[explain(voices,c,i) for c,i in alts]
            row[side]={'catalog':cat,'readings':readings(cat,conditions,events),'condition_assignment_count':work,
                       'candidates_without_spelling_refs':[c['candidate_id'] for c in cat['candidates'] if not c['spelling_alternatives']]}
        row['empty_reading_factors']=[name for name,rs in [('hold',result['hold_readings']),('left',row['left']['readings']),('right',row['right']['readings'])] if not rs]
        if row['status']=='ready' and row['empty_reading_factors']:row['status']='no_spelled_comparison'
        row['virtual_comparison_count']=len(result['hold_readings'])*len(row['left']['readings'])*len(row['right']['readings'])*len(voices['assignments']) if row['status']=='ready' else 0
        result['boundaries'].append(row)
    result['status']='ready';result['storage']='factorized_all_alternatives_not_materialized_cartesian_product'
    # Each factor partitions the same all-part evidence. Conditional roles never
    # change totals, so conservation is checked without materializing every pair.
    aid=voices['assignments'][0]['assignment_id']
    for row in result['boundaries']:
        for h in result['hold_readings']:
            if profile(row['cells'],span,[h],aid)['total_note_time']!=result['total_note_time']:raise ValueError('hold_time_loss')
        for side in ('left','right'):
            part=row[side]['catalog']['span'];lo,hi=f(part['start']),f(part['end'])
            cells=[c for c in row['cells'] if lo<=f(c['span']['start']) and f(c['span']['end'])<=hi]
            expected=q(sum((min(hi,f(s['span']['end']))-max(lo,f(s['span']['start'])) for s in events if f(s['span']['start'])<hi and f(s['span']['end'])>lo),Fraction()))
            for reading in row[side]['readings']:
                if profile(cells,part,[reading],aid)['total_note_time']!=expected:raise ValueError('side_time_loss')
    return result
