"""Conservative counterevidence for delayed links, not a continuity classifier.

The absence of these warnings never establishes a voice or a harmonic resolution.
"""
from collections import defaultdict, Counter
from .harmony_joint import f
from .formal_ir import q
from .harmony_reading_voice_context import spelled_height

VERSION = 'delayed-link-counterevidence-0.1.0'


def assess(ir, observed, contexts):
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    notes={n['note_id']:n for n in ir['note_events']};lanes=defaultdict(list)
    spans=[(f(c['start']),f(c['end'])) for c in contexts]
    if any(a<0 or b<=a for a,b in spans):raise ValueError('invalid_context')
    for s in sounds.values():
        ns=[notes.get(n) for n in s.get('source_note_ids',[])];keys={(n.get('part_id'),n.get('voice_id')) for n in ns if n}
        if not ns or any(n is None for n in ns) or len(keys)!=1 or not all(next(iter(keys))):continue
        if f(s['span']['end'])<=f(s['span']['start']) or any(n.get('grace',{}).get('is_grace') for n in ns):continue
        lanes[next(iter(keys))].append(s)
    rows=[]
    for group in observed['groups']:
        release,first,unit=map(f,(group['time'],group['first_attack'],group['beat_unit_quarter']))
        lane=lanes[(group['part_id'],group['voice_id'])];by_onset=defaultdict(list)
        for s in lane:by_onset[f(s['span']['start'])].append(s)
        starts=sorted(by_onset)
        def sequence(start):
            offsets=[t for t in starts if t>=start][:3]
            if len(offsets)!=3 or offsets[0]!=start or any(len(by_onset[t])!=1 for t in offsets):return None
            seq=[by_onset[t][0] for t in offsets];end=f(seq[-1]['span']['end'])
            if not any(a<=start and end<=b and a<release<first<b for a,b in spans):return None
            if offsets[-1]-start>2*unit:return None
            if any(f(a['span']['end'])>f(b['span']['start']) for a,b in zip(seq,seq[1:])):return None
            # A sustained other sound makes an apparently singleton attack path ambiguous.
            if any(s['sounding_event_id'] not in {x['sounding_event_id'] for x in seq} and f(s['span']['start'])<end and f(s['span']['end'])>start for s in lane):return None
            heights=[spelled_height(s['pitch']) for s in seq]
            if any(h is None for h in heights):return None
            pitches=[s['pitch']['midi_pitch'] for s in seq]
            durations=[(f(s['span']['end'])-f(s['span']['start']))/unit for s in seq]
            if len(set(pitches))==1 and len(set(durations))==1:return None
            return {'event_refs':[s['sounding_event_id'] for s in seq], 'start':q(start),'end':q(end),
                'signature':{'semitone_intervals':[b-a for a,b in zip(pitches,pitches[1:])],
                    'diatonic_intervals':[b-a for a,b in zip(heights,heights[1:])],
                    'onset_intervals_beats':[q((b-a)/unit) for a,b in zip(offsets,offsets[1:])],
                    'durations_beats':[q(x) for x in durations]}}
        target_sequence=sequence(first);repeats=[]
        if target_sequence:
            for start in starts:
                if not first-4*unit<=start<release:continue
                prev=sequence(start)
                if not prev or f(prev['end'])>release:continue
                # Do not normalize across meter changes or repeat/ending boundaries.
                intervening=[m for m in ir.get('measures',[]) if start<f(m['global_start_quarter'])<f(target_sequence['end'])]
                current=next((m for m in reversed(sorted(ir.get('measures',[]),key=lambda m:f(m['global_start_quarter']))) if f(m['global_start_quarter'])<=start),None)
                if current is None or any(m['time_signature']!=current['time_signature'] for m in intervening):continue
                barriers=[]
                for m in ir.get('measures',[]):
                    bar=m.get('repeat_barline') or {};t=f(m['global_start_quarter'])+(0 if bar.get('location')=='left' else f(m['actual_duration_quarter']))
                    if start<=t<f(target_sequence['end']) and any(bar.get(k) for k in ('repeat_direction','ending_number')):barriers.append(m)
                if not barriers and prev['signature']==target_sequence['signature']:repeats.append(prev)
        for edge in group['edges']:
            src,dst=[sounds[sid] for sid in edge['source_refs']];target_time=f(dst['span']['start'])
            prior_attacks=sorted((s for s in lane if release<=f(s['span']['start'])<target_time),key=lambda s:(f(s['span']['start']),s['sounding_event_id']))
            exact=lambda s: (spelled_height(s['pitch']),s['pitch']['midi_pitch'])
            earlier=[s['sounding_event_id'] for s in prior_attacks if spelled_height(s['pitch']) is not None and exact(s)==exact(dst)]
            reasons=[]
            if earlier:reasons.append('earlier_identical_target_already_attacked')
            if prior_attacks:reasons.append('intervening_attacks_need_path_explanation')
            if repeats:reasons.append('recurrent_attack_pattern_allows_restart')
            if len(group['source_refs'])>1 or len(by_onset[target_time])>1 or group['held_refs']:reasons.append('polyphonic_voice_identity_unresolved')
            if f(group['first_attack_gap_beats'])>1:reasons.append('longer_gap_reentry_alternative')
            rows.append({'group_id':group['group_id'],'source_refs':edge['source_refs'],
                'source_pitch':src['pitch']['spelling'],'target_pitch':dst['pitch']['spelling'],
                'source_release':src['span']['end'],'target_onset':dst['span']['start'],
                'earlier_identical_target_refs':earlier,'intervening_attack_refs':[s['sounding_event_id'] for s in prior_attacks],
                'target_attack_pattern':target_sequence,'prior_matching_patterns':repeats,'review_reasons':reasons,
                'status':'counterevidence_requires_review' if reasons else 'no_tested_counterevidence_still_unresolved',
                'independent_resolution_vote_allowed':False,'voice_connection_confirmed':False,'restart_confirmed':False,
                'selected':None,'used_for_ranking':False})
    return {'version':VERSION,'records':rows,'summary':{'edges':len(rows),'with_review_reasons':sum(bool(r['review_reasons']) for r in rows),
        'reasons':dict(Counter(reason for r in rows for reason in r['review_reasons']))},
        'source_annotation_used':False,'production_modified':False,
        'limits':['Three unique nonoverlapping attacks; exact transposition-invariant pitch/rhythm signature only',
            'Look back at most four denominator beats in the same context; sequence onset span <= two denominator beats',
            'Pattern recurrence is a restart alternative, never proof of restart or a motif label',
            'Absence of tested counterevidence is not positive proof; all links remain unconfirmed']}
