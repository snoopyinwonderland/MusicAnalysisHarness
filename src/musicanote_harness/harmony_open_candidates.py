"""Non-exhaustive window proposals with inclusive tertian candidates, no winner.

Two observed pitch classes are a proposal gate, not a harmonic diagnosis.
Residual sounds are never deleted or implicitly called ornaments.
"""
from fractions import Fraction as F
from .formal_ir import q
from .harmony_joint import f
from .harmony_surface import TEMPLATES, PITCH_NAMES
from .harmony_candidate_explanation import spelling_evidence
from .harmony_reading_voice_context import spelled_height
from .harmony_path_contrast import token
from .harmony_conditional_ornaments import assess

VERSION='inclusive-harmony-candidates-0.1.0'
WIDTHS=(F(1,2),F(1),F(2))


def window(ir, span):
    a,b=f(span['start']),f(span['end'])
    if a<0 or b<=a:raise ValueError('invalid_span')
    sounds=sorted((s for s in ir['sounding_events'] if f(s['span']['start'])<b and f(s['span']['end'])>a),key=lambda s:s['sounding_event_id'])
    valid=[s for s in sounds if spelled_height(s['pitch']) is not None]
    observed={s['pitch']['midi_pitch']%12 for s in valid}
    unsupported=[s['sounding_event_id'] for s in sounds if s not in valid]
    points=sorted({a,b}|{max(a,f(s['span']['start'])) for s in sounds}|{min(b,f(s['span']['end'])) for s in sounds})
    cells=[]
    for lo,hi in zip(points,points[1:]):
        active=[s for s in sounds if f(s['span']['start'])<hi and f(s['span']['end'])>lo]
        bass=min((s['pitch']['midi_pitch'] for s in active if s in valid),default=None)
        cells.append({'span':{'start':q(lo),'end':q(hi)},'event_refs':[s['sounding_event_id'] for s in active],
            'attack_refs':[s['sounding_event_id'] for s in active if f(s['span']['start'])==lo],
            'continued_refs':[s['sounding_event_id'] for s in active if f(s['span']['start'])<lo],
            'bass_refs':[s['sounding_event_id'] for s in active if s in valid and s['pitch']['midi_pitch']==bass],
            'silence':not active})
    blockers=[]
    if unsupported:blockers.append('unsupported_pitch')
    if any(n.get('grace',{}).get('is_grace') and a<=f(n['global_onset_quarter'])<b for n in ir['note_events']):blockers.append('grace_timing')
    measures=sorted(ir['measures'],key=lambda m:f(m['global_start_quarter']))
    touched=[m for m in measures if f(m['global_start_quarter'])<b and f(m['global_start_quarter'])+f(m['actual_duration_quarter'])>a]
    signatures={(m['time_signature'].get('beats'),m['time_signature'].get('beat_type')) for m in touched}
    if not touched or len(signatures)>1 or any(None in s for s in signatures):blockers.append('meter_missing_or_changed')
    for m in touched:
        bar=m.get('repeat_barline') or {}
        t=f(m['global_start_quarter'])+(0 if bar.get('location')=='left' else f(m['actual_duration_quarter']))
        if a<t<b and any(bar.get(k) for k in ('repeat_direction','ending_number')):blockers.append('repeat_barrier')
    if any(c['silence'] for c in cells):blockers.append('silence_inside_window')
    candidates=[];paths=[];byid={s['sounding_event_id']:s for s in sounds}
    for root in range(12):
        for quality,intervals in TEMPLATES:
            pcs={(root+i)%12 for i in intervals}
            if len(pcs&observed)<2:continue
            candidate={'root':root,'label':PITCH_NAMES[root]+':'+quality,'pcs':sorted(pcs)}
            spelling=spelling_evidence({'sounding_events':valid},span,candidate)
            members={s['sounding_event_id'] for s in valid if s['pitch']['midi_pitch']%12 in pcs}
            roots=[r for r in spelling['candidates'] if members<=set(r['supported_event_refs'])]
            states={}
            for s in sounds:
                sid=s['sounding_event_id'];p=s['pitch']
                if sid in unsupported:state='spelling_unresolved'
                elif p['midi_pitch']%12 not in pcs:state='nonmember_not_confirmed_nct'
                elif not roots:state='spelling_unresolved'
                else:state='member'
                states[sid]=state
            cid='open_'+token([str(a),str(b),root,quality,sorted(byid)])
            residual=[sid for sid,state in states.items() if state=='nonmember_not_confirmed_nct']
            candidate.update({'candidate_id':cid,'missing_member_pcs':sorted(pcs-observed),'residual_event_refs':residual,
                'event_states':states,'root_hypotheses':roots,'spelling_status':spelling['status'],
                'template_fully_observed':pcs<=observed,'selected':None})
            candidates.append(candidate)
            paths.append({'path_ref':cid,'cells':[{'candidate':{k:candidate[k] for k in ('root','label','pcs')},
                'states':{sid:states[sid] for sid in cell['event_refs']},'outside_extension_assumption':False} for cell in cells]})
    wid='owin_'+token([str(a),str(b),sorted(byid)])
    evidence=assess(ir,{'candidate_ref':wid,'comparison_span':span,'cells':cells,'paths':paths,'abstention_reasons':sorted(set(blockers))})
    return {'window_id':wid,'span':span,'observed_pitch_classes':sorted(observed),'event_refs':sorted(byid),
        'event_units':{sid:{'pitch':s['pitch'],'span':s['span'],'source_note_ids':s['source_note_ids']} for sid,s in byid.items()},
        'cells':cells,'candidates':candidates,'conditional_figures':evidence,'abstention_reasons':sorted(set(blockers)),
        'selected':None,'score':None,'no_chord_change_within_window_is_test_assumption':True}


def observe(ir,span):
    a,b=f(span['start']),f(span['end'])
    if a<0 or b<=a:raise ValueError('invalid_span')
    grid=sorted((f(m['global_start_quarter']),F(4,m['time_signature']['beat_type'])) for m in ir['measures'])
    def unit(t):
        found=[u for start,u in grid if start<=t]
        if not found:raise ValueError('missing_meter')
        return found[-1]
    points={a,b}
    for s in ir['sounding_events']:
        points.update(f(s['span'][k]) for k in ('start','end') if a<=f(s['span'][k])<=b)
    for m in ir['measures']:
        t=f(m['global_start_quarter']);end=t+f(m['actual_duration_quarter'])
        while t<end:
            if a<=t<=b:points.add(t)
            t+=F(4,m['time_signature']['beat_type'])
    spans={(t,t+w*unit(t)) for t in points if t<b for w in WIDTHS if t+w*unit(t)<=b}
    records=[window(ir,{'start':q(x),'end':q(y)}) for x,y in sorted(spans)]
    return {'version':VERSION,'analysis_span':span,'records':records,'proposal_policy':{'anchors':'attack_release_and_denominator_grid','widths_denominator_beats':[q(w) for w in WIDTHS],'min_observed_template_pcs':2,'ranking_or_confidence':False},
        'summary':{'windows':len(records),'candidates':sum(len(r['candidates']) for r in records),
            'with_residual':sum(bool(c['residual_event_refs']) for r in records for c in r['candidates']),
            'with_missing_members':sum(bool(c['missing_member_pcs']) for r in records for c in r['candidates']),
            'conditional_figure_occurrences_not_independent':sum(r['conditional_figures']['summary']['conditional_ornament_triples'] for r in records)},
        'source_labels_used':False,'production_modified':False,'limits':['Proposal recall experiment, not accuracy or automatic harmony.',
            'Two observed pitch classes admit many incompatible candidates; no root required; no top-k pruning.',
            'Window proposals are not exhaustive boundaries. Suspensions, double neighbors and functional harmony are deferred.',
            'Residual notes retained; no NCT deletion. No invented pedal or edge extension.']}
