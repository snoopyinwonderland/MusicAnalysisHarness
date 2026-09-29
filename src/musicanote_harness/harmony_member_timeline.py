"""When candidate members are actually observed; never backdate harmonic truth."""
from fractions import Fraction as F
from .formal_ir import q
from .harmony_joint import f
from .harmony_reading_voice_context import spelled_height

VERSION='candidate-member-timeline-0.1.0'


def observe(ir, span, candidate, root_hypotheses, frozen_context):
    a,b=(f(span[k]) for k in ('start','end'));ca,cb=(f(frozen_context[k]) for k in ('start','end'))
    if not 0<=ca<=a<b<=cb:raise ValueError('span_outside_frozen_context')
    current=[m for m in ir['measures'] if f(m['global_start_quarter'])<=a]
    onset=max((f(m['global_start_quarter']) for m in current),default=None)
    sigs={str(m['time_signature']) for m in current if f(m['global_start_quarter'])==onset}
    signature=next((m['time_signature'] for m in current if f(m['global_start_quarter'])==onset),{})
    denom=signature.get('beat_type');blocked=[]
    if len(sigs)!=1 or not isinstance(denom,int) or denom<=0:
        unit=None;x,y=a,b;blocked.append('meter_unavailable')
    else:
        unit=F(4,denom);x,y=max(ca,a-unit),min(cb,b+unit)
        if x>a-unit or y<b+unit:blocked.append('requested_context_truncated')
    for m in ir['measures']:
        t=f(m['global_start_quarter']);bar=m.get('repeat_barline') or {}
        if x<t<y and m['time_signature']!=signature:blocked.append('meter_change')
        bt=t if bar.get('location')=='left' else t+f(m['actual_duration_quarter'])
        if x<bt<y and any(bar.get(k) for k in ('repeat_direction','ending_number')):blocked.append('repeat_or_ending_barrier')
    # Roots are frozen by the caller's hypothesis; outside pitches cannot pick a
    # more convenient root spelling. Disagreement is not resolved by a union.
    sets={tuple(h['expected_members']) for h in root_hypotheses}
    expected=list(next(iter(sets))) if len(sets)==1 else []
    if not expected:blocked.append('root_spelling_unobserved_or_ambiguous')
    active=sorted((s for s in ir['sounding_events'] if f(s['span']['start'])<y and f(s['span']['end'])>x),key=lambda s:(f(s['span']['start']),s['sounding_event_id']))
    units={s['sounding_event_id']:{'pitch':s['pitch'],'original_span':s['span'],'source_note_ids':s['source_note_ids']} for s in active}
    def spelling(p):
        if spelled_height(p) is None:return None
        alter=int(f(p['alter']));return p['step']+('#'*alter if alter>0 else 'b'*(-alter))
    invalid=[s['sounding_event_id'] for s in active if spelling(s['pitch']) is None or f(s['span']['end'])<=f(s['span']['start'])]
    if invalid:blocked.append('unsupported_pitch_or_duration')
    grace=[n['note_id'] for n in ir['note_events'] if n.get('grace',{}).get('is_grace') and x<=f(n['global_onset_quarter'])<y]
    if grace:blocked.append('grace_timing_unresolved')
    regions={'before':(x,a),'inside':(a,b),'after':(b,y)};windows={}
    for name,(lo,hi) in regions.items():
        ss=[s for s in active if lo<hi and f(s['span']['start'])<hi and f(s['span']['end'])>lo]
        members={p:[s['sounding_event_id'] for s in ss if spelling(s['pitch'])==p] for p in expected}
        gaps=[];cursor=lo
        for start,end in sorted((max(lo,f(s['span']['start'])),min(hi,f(s['span']['end']))) for s in ss):
            if start>cursor:gaps.append({'start':q(cursor),'end':q(start)})
            cursor=max(cursor,end)
        if cursor<hi:gaps.append({'start':q(cursor),'end':q(hi)})
        windows[name]={'span':{'start':q(lo),'end':q(hi)},'available':lo<hi,'member_refs':members,
            'nonmember_or_unresolved_refs':[s['sounding_event_id'] for s in ss if spelling(s['pitch']) not in expected],
            'all_voice_silence':gaps,
            'rest_refs':[r['rest_id'] for r in ir.get('rest_events',[]) if lo<hi and f(r['global_onset_quarter'])<hi and f(r['global_onset_quarter'])+f(r['notated_duration_quarter'])>lo]}
    byid={s['sounding_event_id']:s for s in active}
    first={p:min((max(a,f(byid[sid]['span']['start'])) for sid in refs),default=None) for p,refs in windows['inside']['member_refs'].items()}
    missing=[p for p in expected if first[p] is None]
    complete=max(first.values()) if expected and not missing else None
    bounds=sorted({a,b}|{max(a,f(s['span']['start'])) for s in active if f(s['span']['start'])<b and f(s['span']['end'])>a}|{min(b,f(s['span']['end'])) for s in active if f(s['span']['start'])<b and f(s['span']['end'])>a})
    simultaneous=[]
    for lo,hi in zip(bounds,bounds[1:]):
        ss=[s for s in active if f(s['span']['start'])<=lo<f(s['span']['end'])]
        if expected and set(expected)<={spelling(s['pitch']) for s in ss}:
            simultaneous.append({'span':{'start':q(lo),'end':q(hi)},'member_refs':[s['sounding_event_id'] for s in ss if spelling(s['pitch']) in expected]})
    per_member=[]
    for p in expected:
        refs={name:w['member_refs'][p] for name,w in windows.items()}
        per_member.append({'spelling':p,'refs_by_region':refs,'first_observed_inside':q(first[p]) if first[p] is not None else None,
            'missing_inside_but_seen_outside':not refs['inside'] and bool(refs['before'] or refs['after']),
            'held_across_start':[sid for sid in refs['inside'] if f(byid[sid]['span']['start'])<a<f(byid[sid]['span']['end'])],
            'held_across_end':[sid for sid in refs['inside'] if f(byid[sid]['span']['start'])<b<f(byid[sid]['span']['end'])]})
    return {'version':VERSION,'candidate':candidate,'candidate_span':span,'frozen_context':frozen_context,
        'observed_context':{'start':q(x),'end':q(y)},'denominator_beat_quarters':q(unit) if unit else None,
        'members':per_member,'windows':windows,'event_units':units,'missing_inside':missing,
        'pooled_members_first_complete_at':q(complete) if complete is not None else None,
        'simultaneously_complete_cells':simultaneous,'abstention_reasons':sorted(set(blocked)),
        'unsupported_refs':invalid,'grace_refs':grace,'selected':None,'ranking_performed':False,
        'limits':['Collected members need not sound simultaneously or belong to one harmony.',
            'Outside observations do not fill inside missing members or backdate a harmonic onset.',
            'Held sound is not confirmed prolongation; different sound IDs remain different attacks.',
            'One denominator beat is not an inferred perceptual beat. Truncated context cannot prove absence.',
            'No source annotations, NCT deletion, pedal inference or harmonic boundary change.']}
