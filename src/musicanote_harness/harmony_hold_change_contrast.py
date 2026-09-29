"""Compare conditional readings on identical note-time cells, without a winner."""
from collections import defaultdict
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_open_candidates import window
from .harmony_residual_audit import audit_pair
from .harmony_reattack_figures import assess
from .harmony_voice_figures import double_neighbors

VERSION = 'hold-change-note-time-contrast-0.1.0'


def fixed_roles(ir, w):
    """All existing strict/complete/repeated figures; not independent votes."""
    roles = {c['candidate_id']: defaultdict(list) for c in w['candidates']}
    for r in w['conditional_figures']['records']:
        for e in r['path_explanations']:
            if e['conditional_role']:
                roles[e['path_ref']][r['middle_ref']].append(e['conditional_role'])
    for r in double_neighbors(ir,w)['records']:
        for e in r['candidate_explanations']:
            if e['status']=='conditional_double_neighbor_compatible':
                for sid in r['neighbor_refs']:
                    roles[e['candidate_ref']][sid].append('double_neighbor')
    repeated = assess(ir,w)
    for r in repeated['records']:
        for e in r['candidate_explanations']:
            if e['conditional_role']:
                for sid in r['middle_refs']:
                    roles[e['candidate_ref']][sid].append('reattack_'+e['conditional_role'])
    return roles, repeated


def profile(whole, segments):
    """Exact rational note-time, separate from elapsed time or confidence.

    One held sound crossing the join becomes two cells, not two independent notes.
    Segments must form an exact non-overlapping partition of the comparison span.
    """
    cursor=f(whole['span']['start']);end=f(whole['span']['end'])
    for s in segments:
        if f(s['span']['start'])!=cursor or f(s['span']['end'])<=cursor:
            raise ValueError('segments_do_not_partition_span')
        cursor=f(s['span']['end'])
    if cursor!=end:raise ValueError('segments_do_not_partition_span')
    totals=defaultdict(Fraction);cells=[];by_event=defaultdict(list)
    for cell in whole['cells']:
        for segment in segments:
            lo=max(f(cell['span']['start']),f(segment['span']['start']))
            hi=min(f(cell['span']['end']),f(segment['span']['end']))
            if lo>=hi:continue
            classified=[]
            for sid in cell['event_refs']:
                state=segment['candidate']['event_states'].get(sid,'spelling_unresolved')
                roles=sorted(set(segment['roles'].get(sid,[])))
                bucket=('member' if state=='member' else
                        'conditional_nct' if state=='nonmember_not_confirmed_nct' and roles else
                        'unexplained' if state=='nonmember_not_confirmed_nct' else 'spelling_unresolved')
                totals[bucket]+=hi-lo
                item={'event_ref':sid,'state':state,'bucket':bucket,'conditional_roles':roles,
                      'span':{'start':q(lo),'end':q(hi)},'duration':q(hi-lo),
                      'candidate_ref':segment['candidate']['candidate_id']}
                classified.append(item);by_event[sid].append(item)
            cells.append({'span':{'start':q(lo),'end':q(hi)},'events':classified})
    return {'note_time_quarters':{k:q(totals[k]) for k in
                ('member','conditional_nct','unexplained','spelling_unresolved')},
            'total_note_time_quarters':q(sum(totals.values(),Fraction())),
            'cells':cells,'event_readings':dict(by_event),
            'missing_members_by_segment':[{'span':s['span'],'label':s['candidate']['label'],
                'missing_member_pcs':s['candidate']['missing_member_pcs']} for s in segments],
            'selected':None,'score':None}


def compare(ir, gate):
    whole=window(ir,gate['span']);left=gate['left_window'];right=gate['right_window']
    if left['span']['start']!=whole['span']['start'] or right['span']['end']!=whole['span']['end'] or left['span']['end']!=right['span']['start']:
        raise ValueError('mismatched_comparison_windows')
    boundary=f(gate['boundary'])
    if boundary!=f(right['span']['start']):raise ValueError('mismatched_boundary')
    # Use the same grid even if a caller supplies a join inside a held sound.
    cells=[]
    for cell in whole['cells']:
        a,b=(f(cell['span'][k]) for k in ('start','end'))
        points=[a,boundary,b] if a<boundary<b else [a,b]
        cells.extend({**cell,'span':{'start':q(lo),'end':q(hi)}} for lo,hi in zip(points,points[1:]))
    whole['cells']=cells
    roles,repeated=fixed_roles(ir,whole)
    holds=[]
    for c in whole['candidates']:
        holds.append({'candidate':c,'profile':profile(whole,[{'span':whole['span'],'candidate':c,'roles':roles[c['candidate_id']]}]),
                      'assumption':'same candidate throughout comparison window'})
    side_roles=[fixed_roles(ir,w)[0] for w in (left,right)]
    changes=[];cache={}
    for p in gate['change_proposals']:
        cs=[next(c for c in w['candidates'] if c['candidate_id']==p[key]) for w,key in
            [(left,'source_candidate_ref'),(right,'target_candidate_ref')]]
        audit=audit_pair(ir,left,right,*cs,cache)
        segments=[]
        for w,c,base,side in zip((left,right),cs,side_roles,audit['sides']):
            rs={sid:list(v) for sid,v in base[c['candidate_id']].items()}
            for n in side['residuals']:
                rs.setdefault(n['event_ref'],[]).extend(e['kind'] for e in n['conditional_nct_explanations'])
            if gate['abstention_reasons']:rs={}
            segments.append({'span':w['span'],'candidate':c,'roles':rs})
        changes.append({'proposal':p,'profile':profile(whole,segments),
                        'assumption':'asserted change at frozen boundary',
                        'abstention_reasons':audit['abstention_reasons']})
    comparisons=[]
    # Compare every hold with every saved eligible change; not a best-match filter.
    for hold in holds:
        hp=hold['profile']
        for change in changes:
            cp=change['profile'];assert hp['total_note_time_quarters']==cp['total_note_time_quarters']
            transitions=[]
            for hc,cc in zip(hp['cells'],cp['cells']):
                assert hc['span']==cc['span']
                for h,c in zip(hc['events'],cc['events']):
                    assert h['event_ref']==c['event_ref']
                    if h['bucket']!=c['bucket'] or h['conditional_roles']!=c['conditional_roles']:
                        transitions.append({'event_ref':h['event_ref'],'span':h['span'],
                            'hold_bucket':h['bucket'],'change_bucket':c['bucket'],
                            'hold_roles':h['conditional_roles'],'change_roles':c['conditional_roles']})
            delta={k:q(f(cp['note_time_quarters'][k])-f(hp['note_time_quarters'][k])) for k in hp['note_time_quarters']}
            comparisons.append({'hold_ref':hold['candidate']['candidate_id'],'change_ref':change['proposal']['proposal_id'],
                'change_minus_hold_note_time':delta,'changed_readings':transitions,'preferred':None,
                'interpretation':'A difference in unexplained note-time is not a musical likelihood or a winner.'})
    return {'version':VERSION,'span':whole['span'],'boundary':gate['boundary'],'event_units':whole['event_units'],
            'hold_readings':holds,'change_readings':changes,'comparisons':comparisons,
            'repeated_figures':repeated,'abstention_reasons':gate['abstention_reasons'],
            'selected':None,'ranking_performed':False,'source_annotation_used':False,
            'limits':['All profiles cover identical sounding-note time, not counts of independent notes.',
                'Held sound may change role at a candidate chord boundary; original onset/release is preserved.',
                'NCT roles remain conditional on incompatible harmony assumptions.',
                'Missing members, unexplained notes and spelling uncertainty remain distinct.',
                'No probability, optimal harmonic rhythm, local key or cadence is inferred.',
                'Only prior strict change proposals are contrasted; their absence is not proof of hold.']}
