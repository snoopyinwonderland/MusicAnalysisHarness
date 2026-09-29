"""Conservative, experimental change/ornament-hold gates; never final harmony.

Requires independent kinds of evidence, not a sum of membership scores.
False negatives (sparse voicing, pedal, short harmonic rhythm) stay unresolved.
"""
from collections import Counter
from fractions import Fraction as F
from .formal_ir import q
from .harmony_joint import f
from .harmony_open_candidates import window
from .harmony_reading_voice_context import voice_links
from .harmony_path_contrast import token
from .harmony_voice_figures import double_neighbors

VERSION='conservative-change-gate-0.1.0'


def evaluate(ir, span, boundary):
    a,b=f(span['start']),f(span['end']);t=f(boundary)
    if not 0<=a<t<b:raise ValueError('invalid_boundary')
    left=window(ir,{'start':q(a),'end':q(t)})
    right=window(ir,{'start':q(t),'end':q(b)})
    whole=window(ir,span)
    rows=[m for m in ir['measures'] if f(m['global_start_quarter'])<=t]
    latest=max((f(m['global_start_quarter']) for m in rows),default=None)
    sigs={str(m['time_signature']) for m in rows if f(m['global_start_quarter'])==latest}
    meter=next((m['time_signature'] for m in rows if f(m['global_start_quarter'])==latest),{})
    denom=meter.get('beat_type');unit=F(4,denom) if type(denom) is int and denom>0 and len(sigs)==1 else None
    blocks=sorted(set(left['abstention_reasons']+right['abstention_reasons']+whole['abstention_reasons']))
    # Whole window catches repeats/meter changes exactly at the proposed join.
    if unit is None:blocks.append('meter_unavailable')
    voices=voice_links(ir,span)
    links=[l for l in voices['links'] if f(l['source_span']['end'])==t==f(l['target_span']['start'])]
    lb=left['cells'][-1]['bass_refs'];rb=right['cells'][0]['bass_refs']
    units=whole['event_units']
    pitch=lambda sid:units[sid]['pitch']['midi_pitch']
    bass_changed=bool(lb and rb) and {pitch(s) for s in lb}!={pitch(s) for s in rb}
    # Fully prepared conditional figures only; partial double neighbors do not veto.
    roles={c['candidate_id']:set() for c in whole['candidates']}
    for r in whole['conditional_figures']['records']:
        for e in r['path_explanations']:
            if e['conditional_role']:roles[e['path_ref']].add(r['middle_ref'])
    doubles=double_neighbors(ir,whole)
    for r in doubles['records']:
        for e in r['candidate_explanations']:
            if e['status']=='conditional_double_neighbor_compatible':roles[e['candidate_ref']].update(r['neighbor_refs'])
    bylabel={c['label']:c for c in whole['candidates']}
    holds=[]
    for c in whole['candidates']:
        residual=set(c['residual_event_refs']);covered=roles[c['candidate_id']]
        if not blocks and c['root_hypotheses'] and c['template_fully_observed'] and residual and residual<=covered:
            holds.append({'candidate_ref':c['candidate_id'],'label':c['label'],'residual_refs':sorted(residual),
                          'status':'conditional_ornament_hold_supported','confirmed':False})
    fail=Counter();passed=[];tested=0
    for x in left['candidates']:
        for y in right['candidates']:
            if x['label']==y['label']:continue
            tested+=1;reasons=[]
            if blocks:reasons.append('context_blocked')
            if unit is None or min(t-a,b-t)<unit:reasons.append('less_than_one_denominator_beat_each_side')
            if not x['root_hypotheses'] or not y['root_hypotheses']:reasons.append('root_spelling_unresolved')
            if not x['template_fully_observed'] or not y['template_fully_observed']:reasons.append('incomplete_members')
            departing=[s for s,state in x['event_states'].items() if state=='member' and pitch(s)%12 not in y['pcs']]
            arriving=[s for s,state in y['event_states'].items() if state=='member' and pitch(s)%12 not in x['pcs']]
            new_arriving=[s for s in arriving if f(units[s]['span']['start'])>=t]
            if len({pitch(s)%12 for s in departing})<1 or len({pitch(s)%12 for s in new_arriving})<2:
                reasons.append('insufficient_exclusive_member_replacement')
            if not bass_changed or any(x['event_states'].get(s)!='member' for s in lb) or any(y['event_states'].get(s)!='member' for s in rb):
                reasons.append('bass_replacement_not_supported')
            motion=[l for l in links if x['event_states'].get(l['source_refs'][0])=='member' and y['event_states'].get(l['source_refs'][1])=='member' and l['semitones']!=0]
            independent={(l['source_pitch']['midi_pitch']%12,l['target_pitch']['midi_pitch']%12) for l in motion}
            if len(independent)<2:reasons.append('fewer_than_two_distinct_direct_voice_motions')
            held=[s for s in departing if f(units[s]['span']['end'])>t]
            if held:reasons.append('departing_exclusive_member_still_sounds')
            whole_x=bylabel.get(x['label']);ornaments=roles[whole_x['candidate_id']] if whole_x else set()
            if arriving and set(arriving)<=ornaments:reasons.append('competing_prepared_ornament_explanation')
            if reasons:
                fail.update(set(reasons));continue
            passed.append({'proposal_id':'chg_'+token([left['window_id'],right['window_id'],x['candidate_id'],y['candidate_id']]),
                'source_candidate_ref':x['candidate_id'],'target_candidate_ref':y['candidate_id'],
                'source_label':x['label'],'target_label':y['label'],
                'departing_refs':departing,'arriving_refs':arriving,'new_arriving_refs':new_arriving,'bass_before_refs':lb,'bass_after_refs':rb,
                'direct_voice_links':motion,'distinct_motion_pc_pairs':[list(v) for v in sorted(independent)],
                'source_residual_count':len(x['residual_event_refs']),'target_residual_count':len(y['residual_event_refs']),
                'status':'change_supported_under_strict_conditions','selected':None})
    return {'version':VERSION,'span':span,'boundary':boundary,'denominator_beat_quarters':q(unit) if unit else None,
        'left_window':left,'right_window':right,'event_units':units,'abstention_reasons':blocks,
        'change_proposals':passed,'hold_proposals':holds,'pair_count':tested,'failed_gate_counts':dict(fail),
        'voice_abstentions':voices['abstentions'],'selected':None,'source_annotation_used':False,
        'limits':['Gates are an experimental sufficient-evidence screen, not necessary conditions for harmony.',
            'No passing pair does not imply hold; no ornament hold does not imply change.',
            'Sparse voicing, common bass/pedal, third-related changes and rapid harmony may remain unresolved.',
            'Two distinct PC motions de-duplicate octave doubling, but are not independent statistical votes.',
            'One denominator beat is a conservative test threshold, not a universal perceptual beat.',
            'Other unexplained notes, local key, function, inversion and cadence remain unresolved.',
            'Candidates are not removed; no production ranking or final boundary is changed.']}
