"""Conservative octave-lane links and candidate-conditioned double neighbors.

These are additional hypotheses, not contrapuntal voice reconstruction or NCT
truth. No nearest-pitch matching, skipped rests, or source-label input.
"""
from collections import defaultdict, Counter
from .harmony_joint import f
from .harmony_reading_voice_context import spelled_height
from .harmony_path_contrast import token

VERSION = 'voice-figures-0.1.0'


def lanes(ir):
    notes = {n['note_id']: n for n in ir['note_events']}
    result = defaultdict(list)
    for s in ir['sounding_events']:
        ns = [notes.get(i) for i in s.get('source_note_ids', [])]
        ids = {(n.get('part_id'), n.get('voice_id')) for n in ns if n}
        if not ns or not all(ns) or len(ids) != 1 or not all(next(iter(ids))):
            continue
        # Retain unsupported/grace events as blockers rather than removing them.
        usable = not any(n.get('grace', {}).get('is_grace') for n in ns)
        usable &= spelled_height(s['pitch']) is not None
        usable &= f(s['span']['end']) > f(s['span']['start'])
        result[next(iter(ids))].append({**s, '_usable': usable})
    return result


def octave_links(ir, context):
    """Synchronized, equally sized octave groups, rank-preserving step only."""
    links = []; skipped = Counter()
    for (part, voice), sequence in lanes(ir).items():
        groups = defaultdict(list)
        for s in sequence:
            groups[(f(s['span']['start']), f(s['span']['end']))].append(s)
        ordered = sorted(groups.items())
        for (a, b), source in ordered:
            if a < f(context['start']) or b >= f(context['end']) or len(source) < 2:
                continue
            later = [(times, ss) for times, ss in ordered if times[0] == b]
            if len(later) != 1:
                skipped['no_unique_synchronized_target'] += 1; continue
            (t, end), target = later[0]
            if end > f(context['end']):
                skipped['target_outside_context'] += 1; continue
            if len(source) != len(target):
                skipped['octave_count_changed'] += 1; continue
            ids = {s['sounding_event_id'] for s in source + target}
            if any(s['sounding_event_id'] not in ids and f(s['span']['start']) < end and f(s['span']['end']) > a for s in sequence):
                skipped['other_overlapping_sound'] += 1; continue
            def octave_group(ss):
                return (all(s['_usable'] for s in ss)
                        and len({(s['pitch']['step'], f(s['pitch']['alter'])) for s in ss}) == 1
                        and len({s['pitch']['octave'] for s in ss}) == len(ss))
            if not octave_group(source) or not octave_group(target):
                skipped['not_pure_spelled_octaves'] += 1; continue
            source = sorted(source, key=lambda s:s['pitch']['midi_pitch'])
            target = sorted(target, key=lambda s:s['pitch']['midi_pitch'])
            motions = {(y['pitch']['midi_pitch']-x['pitch']['midi_pitch'], spelled_height(y['pitch'])-spelled_height(x['pitch'])) for x,y in zip(source,target)}
            if len(motions) != 1 or next(iter(motions)) not in {(1,1),(2,1),(-1,-1),(-2,-1)}:
                skipped['not_uniform_step_motion'] += 1; continue
            group_id = 'oct_' + token([[s['sounding_event_id'] for s in source], [s['sounding_event_id'] for s in target]])
            for x,y in zip(source,target):
                semitones,steps = next(iter(motions))
                links.append({'source_refs':[x['sounding_event_id'],y['sounding_event_id']],
                    'source_pitch':x['pitch'],'target_pitch':y['pitch'],
                    'source_span':x['span'],'target_span':y['span'],
                    'part_id':part,'voice_id':voice,'semitones':semitones,'diatonic_steps':steps,
                    'status':'conditional_synchronized_octave_rank_link','dependency_group':group_id,
                    'contrapuntal_voice_identity_confirmed':False})
    return {'version':VERSION,'links':links,'abstentions':dict(skipped),
            'policy':'Equal-count pure spelled octaves; synchronized spans; same explicit lane; uniform step motion. Group members are dependent evidence.'}


def double_neighbors(ir, window):
    """Four-note return with opposite step neighbors under each fixed candidate.

Geometry with a rest is retained as an unresolved observation, never repaired.
"""
    records = []; skipped = Counter()
    a,b = (f(window['span'][k]) for k in ('start','end'))
    for (part,voice), sequence in lanes(ir).items():
        ss = sorted(sequence,key=lambda s:(f(s['span']['start']),s['sounding_event_id']))
        for i in range(len(ss)-3):
            four = ss[i:i+4];first,n1,n2,last = four
            if f(first['span']['start']) < a or f(last['span']['end']) > b:continue
            if not all(s['_usable'] for s in four):continue
            pitches = [s['pitch']['midi_pitch'] for s in four]
            heights = [spelled_height(s['pitch']) for s in four]
            if pitches[0] != pitches[3] or heights[0] != heights[3]:continue
            offsets = [heights[j]-heights[0] for j in (1,2)]
            chromatic = [pitches[j]-pitches[0] for j in (1,2)]
            if set(offsets) != {-1,1} or any(abs(v) not in (1,2) for v in chromatic):continue
            if any(d*c <= 0 for d,c in zip(offsets,chromatic)):continue
            refs = [s['sounding_event_id'] for s in four]
            blockers = list(window['abstention_reasons'])
            if any(f(x['span']['end']) != f(y['span']['start']) for x,y in zip(four,four[1:])):blockers.append('gap_or_overlap_inside_figure')
            if any(o['sounding_event_id'] != s['sounding_event_id'] and f(o['span']['start']) < f(s['span']['end']) and f(o['span']['end']) > f(s['span']['start']) for s in four for o in ss):blockers.append('polyphonic_lane')
            explanations = []
            for c in window['candidates']:
                states = [c['event_states'].get(sid) for sid in refs]
                compatible = states == ['member','nonmember_not_confirmed_nct','nonmember_not_confirmed_nct','member']
                status = 'context_unresolved' if blockers else 'conditional_double_neighbor_compatible' if compatible else 'all_candidate_members' if states == ['member']*4 else 'membership_or_spelling_not_sufficient'
                explanations.append({'candidate_ref':c['candidate_id'],'event_states':states,'status':status,
                    'conditional_role':'double_neighbor' if compatible and not blockers else None,
                    'confirmed_nct':False,'remove_notes':False})
            records.append({'evidence_id':'dn_'+token([window['window_id'],refs]),'event_refs':refs,
                'neighbor_refs':refs[1:3],'part_id':part,'voice_id':voice,
                'span':{'start':first['span']['start'],'end':last['span']['end']},
                'geometry':'opposite_step_neighbors_return_to_same_spelled_pitch','preparation_anchor_observed':True,
                'abstention_reasons':sorted(set(blockers)),'candidate_explanations':explanations,
                'selected':None,'used_for_ranking':False})
        covered={tuple(r['event_refs'][-3:]) for r in records if r['part_id']==part and r['voice_id']==voice}
        for triple in zip(ss,ss[1:],ss[2:]):
            n1,n2,last=triple;refs=[s['sounding_event_id'] for s in triple]
            if tuple(refs) in covered or f(n1['span']['start'])<a or f(last['span']['end'])>b:continue
            if not all(s['_usable'] for s in triple):continue
            anchor=last['pitch'];offsets=[spelled_height(s['pitch'])-spelled_height(anchor) for s in triple[:2]]
            chromatic=[s['pitch']['midi_pitch']-anchor['midi_pitch'] for s in triple[:2]]
            if set(offsets)!={-1,1} or any(abs(c) not in (1,2) or d*c<=0 for d,c in zip(offsets,chromatic)):continue
            blockers=list(window['abstention_reasons'])+['preparation_anchor_not_observed_in_window']
            if any(f(x['span']['end'])!=f(y['span']['start']) for x,y in zip(triple,triple[1:])):blockers.append('gap_or_overlap_inside_figure')
            if any(o['sounding_event_id']!=s['sounding_event_id'] and f(o['span']['start'])<f(s['span']['end']) and f(o['span']['end'])>f(s['span']['start']) for s in triple for o in ss):blockers.append('polyphonic_lane')
            explanations=[]
            for c in window['candidates']:
                states=[c['event_states'].get(sid) for sid in refs]
                match=states==['nonmember_not_confirmed_nct','nonmember_not_confirmed_nct','member']
                explanations.append({'candidate_ref':c['candidate_id'],'event_states':states,
                    'status':'incomplete_double_neighbor_hypothesis' if match and len(blockers)==1 else 'context_or_membership_unresolved',
                    'conditional_role':None,'confirmed_nct':False,'remove_notes':False})
            records.append({'evidence_id':'dnpartial_'+token([window['window_id'],refs]),'event_refs':refs,
                'neighbor_refs':refs[:2],'part_id':part,'voice_id':voice,
                'span':{'start':n1['span']['start'],'end':last['span']['end']},
                'geometry':'opposite_step_neighbors_converge_without_observed_preparation',
                'preparation_anchor_observed':False,'abstention_reasons':sorted(set(blockers)),
                'candidate_explanations':explanations,'selected':None,'used_for_ranking':False})
    return {'version':VERSION,'records':records,'skipped':dict(skipped),
        'conditional_count':sum(any(e['conditional_role'] for e in r['candidate_explanations']) for r in records),
        'limits':['A fixed chord across the full figure is an assumption, not a confirmed harmonic span.',
                  'Four events required for full compatibility; three-event suffixes remain incomplete hypotheses. No inferred pre-rest anchor. Polyphony, grace and gaps abstain.',
                  'No metrical/accent inference, score change, note deletion or gold-label promotion.']}
