"""Exact temporal/bass evidence, separate from conditional NCT interpretations.

Lowest sounding pitch is not structural bass. Written denominator position is
not inferred accent. Absent simultaneous support never rejects an arpeggio.
"""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_path_contrast import token
from .harmony_reading_voice_context import spelled_height
from .harmony_catalog_resolution import pitch_pair

VERSION='boundary-observations-0.1.0'


def meter_at(ir,time):
    t=f(time)
    ms=[m for m in ir.get('measures',[]) if f(m['global_start_quarter'])<=t<
        f(m['global_start_quarter'])+f(m['actual_duration_quarter'])]
    if len(ms)!=1:return {'status':'missing_or_ambiguous_measure','measure_refs':[m['measure_id'] for m in ms]}
    m=ms[0];offset=t-f(m['global_start_quarter']);ts=m.get('time_signature') or {}
    den=ts.get('beat_type');unit=Fraction(4,den) if type(den) is int and den>0 else None
    regular=not m.get('pickup',False) and m.get('nominal_duration_quarter') is not None and f(m['nominal_duration_quarter'])==f(m['actual_duration_quarter'])
    return {'status':'observed' if unit else 'denominator_missing','measure_ref':m['measure_id'],
        'printed_measure_number':m['printed_measure_number'],'onset_in_measure':q(offset),
        'time_signature':deepcopy(ts),'denominator_unit_quarters':q(unit) if unit else None,
        'denominator_unit_position_zero_based':q(offset/unit) if unit else None,
        'on_denominator_grid':(offset/unit).denominator==1 if unit else None,
        'is_measure_start':offset==0,'measure_start_downbeat':offset==0 if regular else None,
        'pickup':m.get('pickup',False),'accent_assessed':False,
        'limits':['Denominator unit is not an inferred conducting beat; no compound/additive grouping or hypermeter inference.',
                  'Pickup/irregular measure downbeat placement is not inferred; measure-local time signatures only.']}


def snapshot(events,span,ir):
    a,b=f(span['start']),f(span['end'])
    if b<=a:raise ValueError('nonpositive_cell')
    active=[s for s in events if f(s['span']['start'])<=a and f(s['span']['end'])>=b]
    ids=sorted(s['sounding_event_id'] for s in active)
    unknown=[s['sounding_event_id'] for s in active if spelled_height(s['pitch']) is None]
    known=[s for s in active if s['sounding_event_id'] not in unknown]
    # Do not silently select a higher bass after discarding an unknown pitch.
    lowest=min((s['pitch']['midi_pitch'] for s in known),default=None) if not unknown else None
    bass=[s for s in known if s['pitch']['midi_pitch']==lowest] if lowest is not None else []
    intervals=[]
    for lo in bass:
        for hi in known:
            steps=spelled_height(hi['pitch'])-spelled_height(lo['pitch'])
            intervals.append({'bass_ref':lo['sounding_event_id'],'event_ref':hi['sounding_event_id'],
                'semitones':hi['pitch']['midi_pitch']-lo['pitch']['midi_pitch'],
                'diatonic_steps':steps,'generic_interval':steps+1 if steps>=0 else None,
                'consonance_classification':None})
    return {'span':deepcopy(span),'active_event_refs':ids,
        'attacked_event_refs':sorted(s['sounding_event_id'] for s in active if f(s['span']['start'])==a),
        'continued_event_refs':sorted(s['sounding_event_id'] for s in active if f(s['span']['start'])<a),
        'unknown_pitch_refs':sorted(unknown),'silence':not active,
        'observed_spellings':[list(p) for p in sorted({tuple(pitch_pair(s['pitch'])) for s in known})],
        'lowest_midi_pitch':lowest,'lowest_event_refs':sorted(s['sounding_event_id'] for s in bass),
        'bass_status':'unknown_pitch_present' if unknown else 'observed_lowest' if bass else 'silence',
        'intervals_from_lowest':intervals,'meter':meter_at(ir,q(a)),
        'structural_bass_confirmed':False}


def support(reading,cells):
    a,b=f(reading['span']['start']),f(reading['span']['end'])
    members=sorted({tuple(m) for m in reading['members']})
    indices=[i for i,c in enumerate(cells) if a<=f(c['span']['start']) and f(c['span']['end'])<=b]
    cursor=a
    for i in indices:
        lo,hi=f(cells[i]['span']['start']),f(cells[i]['span']['end'])
        if lo!=cursor or hi<=lo:raise ValueError('candidate_cell_gap_or_overlap')
        cursor=hi
    if cursor!=b:
        raise ValueError('candidate_cells_do_not_cover_span')
    durations={m:Fraction() for m in members};simultaneous=Fraction();unknown=Fraction();rows=[]
    for i in indices:
        c=cells[i];observed={tuple(p) for p in c['observed_spellings']};dt=f(c['span']['end'])-f(c['span']['start'])
        present=[m for m in members if m in observed];missing=[m for m in members if m not in observed]
        for m in present:durations[m]+=dt  # Time union, never doubled by unison doubling.
        if not missing:simultaneous+=dt
        if c['unknown_pitch_refs']:unknown+=dt
        rows.append({'cell_index':i,'present_members':[list(m) for m in present],
            'not_observed_members':[list(m) for m in missing],
            'absence_certain_from_available_pitches':not bool(c['unknown_pitch_refs'])})
    return {'span':deepcopy(reading['span']),'members':[list(m) for m in members],
        'member_coverage':[{'spelling':list(m),'observed_duration_quarters':q(durations[m])} for m in members],
        'all_members_simultaneous_duration_quarters':q(simultaneous),
        'unknown_pitch_duration_quarters':q(unknown),'cells':rows,'candidate_rejected':False,
        'limits':['Coverage is wall-clock duration per spelled chord member, not note-time or a score.',
                  'Non-simultaneous chord members may support arpeggiation; omissions never automatically reject a candidate.']}


def observe(ir,result,boundary_index):
    boundary=result['boundaries'][boundary_index]
    out={'version':VERSION,'status':boundary['status'],'selected':None,'ranking_performed':False}
    if result['status']!='ready' or boundary['status']!='ready':return out
    events=result['events'];cells=[snapshot(events,c['span'],ir) for c in boundary['cells']]
    for old,new in zip(boundary['cells'],cells):
        if sorted(old['event_refs'])!=new['active_event_refs']:raise ValueError('snapshot_grid_mismatch')
    cut=f(boundary['boundary']);before=next(i for i,c in enumerate(cells) if f(c['span']['end'])==cut)
    after=next(i for i,c in enumerate(cells) if f(c['span']['start'])==cut)
    profiles={};refs={}
    for name,readings in [('hold',result['hold_readings']),('left',boundary['left']['readings']),('right',boundary['right']['readings'])]:
        refs[name]=[]
        for reading in readings:
            pid='support_'+token([reading['span'],sorted(reading['members'])]);refs[name].append(pid)
            if pid not in profiles:profiles[pid]=support(reading,cells)
    patterns=[];sounds={s['sounding_event_id']:s for s in events}
    for p in boundary.get('boundary_figures',{}).get('patterns',[]):
        patterns.append({'pattern_ref':p['pattern_id'],'affected_event_ref':p['affected_event_ref'],
            'nonmember_cell_indices':[i for i,c in enumerate(cells) if f(p['nonmember_span']['start'])<=f(c['span']['start']) and f(c['span']['end'])<=f(p['nonmember_span']['end'])],
            'event_onsets':[{'event_ref':sid,'cell_index':next((i for i,c in enumerate(cells) if f(c['span']['start'])==f(sounds[sid]['span']['start'])),None)} for sid in p['event_refs']],
            'nct_confirmed':False})
    out.update(cells=cells,before_cell_index=before,after_cell_index=after,
        candidate_support_profiles=profiles,reading_profile_refs=refs,pattern_observations=patterns,
        lowest_pitch_changed=(cells[before]['lowest_midi_pitch']!=cells[after]['lowest_midi_pitch'])
            if all(cells[i]['bass_status']=='observed_lowest' for i in (before,after)) else None,
        limits=['Uses actual all-part sounding events, not structural bass, inferred root, or assigned harmony.',
                'Pitch/register basis is inherited from the source IR. Grace/performance timing and pedal not reconstructed.',
                'Meter position and spelled interval alone do not confirm suspension, function, cadence, or change.'])
    return out


def augment(ir,baseline):
    result=deepcopy(baseline)
    for i,b in enumerate(result['boundaries']):b['temporal_observations']=observe(ir,result,i)
    result['temporal_observations_version']=VERSION
    return result
