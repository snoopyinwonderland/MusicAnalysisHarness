"""Exhaustive bounded partitions into continuous hypothetical voice tracks.

Local partial matchings are not votes. Every sounding event remains in exactly
one track, including isolated events, held notes, and unmatched endpoints.
"""
from copy import deepcopy
from itertools import product
from math import prod
from .formal_ir import q
from .harmony_joint import f
from .harmony_path_contrast import token
from .harmony_polyphonic_links import partial_matchings, MAX_ENDPOINTS

VERSION = 'continuous-voice-paths-0.1.0'
MAX_GLOBAL_ASSIGNMENTS = 1024


def partition(events, links):
    """Validate a disjoint union of forward chains; retain isolated events."""
    sounds = {s['sounding_event_id']:s for s in events}
    if len(sounds)!=len(events):raise ValueError('duplicate_sound_id')
    if any(f(s['span']['end'])<=f(s['span']['start']) for s in events):
        raise ValueError('nonpositive_sound_duration')
    incoming={};outgoing={}
    for a,b in links:
        if a not in sounds or b not in sounds:raise ValueError('missing_event_reference')
        if a in outgoing or b in incoming:raise ValueError('branch_or_merge_not_allowed')
        if f(sounds[a]['span']['end'])!=f(sounds[b]['span']['start']):
            raise ValueError('gap_overlap_or_backward_connection')
        outgoing[a]=b;incoming[b]=a
    chains=[];used=set()
    for start in sorted((sid for sid in sounds if sid not in incoming),
                        key=lambda sid:(f(sounds[sid]['span']['start']),sid)):
        chain=[];sid=start
        while sid is not None:
            if sid in used:raise ValueError('cycle_or_reused_event')
            used.add(sid);chain.append(sid);sid=outgoing.get(sid)
        chains.append(chain)
    if used!=set(sounds):raise ValueError('event_loss_or_cycle')
    return chains


def observe(ir, span, lane):
    a,b=f(span['start']),f(span['end'])
    if a<0 or b<=a:raise ValueError('invalid_context')
    notes={n['note_id']:n for n in ir['note_events']}
    events=[];unknown=[]
    for s in ir['sounding_events']:
        if f(s['span']['start'])>=b or f(s['span']['end'])<=a:continue
        ns=[notes.get(n) for n in s['source_note_ids']]
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns if n}
        if not ns or not all(ns) or len(keys)!=1 or not all(next(iter(keys))):
            unknown.append(s['sounding_event_id']);continue
        if next(iter(keys))==tuple(lane):events.append(s)
    events.sort(key=lambda s:(f(s['span']['start']),s['sounding_event_id']))
    reasons=[]
    if unknown:reasons.append('unlocated_context_sounds_no_silent_exclusion')
    if not events:reasons.append('empty_lane')
    if len(events)>128:reasons.append('lane_sound_limit_no_pruning')
    if any(f(s['span']['end'])<=f(s['span']['start']) for s in events):reasons.append('nonpositive_duration')
    boundaries=[]
    times=sorted({f(s['span']['end']) for s in events}&{f(s['span']['start']) for s in events})
    for t in times:
        if not a<t<b:continue
        left=[s['sounding_event_id'] for s in events if f(s['span']['end'])==t]
        right=[s['sounding_event_id'] for s in events if f(s['span']['start'])==t]
        held=[s['sounding_event_id'] for s in events if f(s['span']['start'])<t<f(s['span']['end'])]
        choices=[]
        if max(len(left),len(right))>MAX_ENDPOINTS:
            reasons.append('endpoint_limit_no_pruning')
        else:choices=partial_matchings(left,right)
        boundaries.append({'boundary_id':'vbound_'+token([lane,q(t),left,right]),'time':q(t),
            'source_refs':left,'target_refs':right,'held_refs':held,
            'choices':[[list(pair) for pair in c] for c in choices]})
    possible=prod(len(g['choices']) for g in boundaries)
    if possible>MAX_GLOBAL_ASSIGNMENTS:reasons.append('global_assignment_limit_no_beam_pruning')
    duration=sum((min(b,f(s['span']['end']))-max(a,f(s['span']['start'])) for s in events),f(q(0)))
    result={'version':VERSION,'span':deepcopy(span),'lane':list(lane),
        'events':deepcopy(events),'unlocated_sound_refs':unknown,'boundaries':boundaries,
        'possible_assignments':possible,'max_global_assignments':MAX_GLOBAL_ASSIGNMENTS,
        'abstention_reasons':sorted(set(reasons)),'assignments':[],
        'total_observed_note_time':q(duration),'enumeration_complete':not reasons,
        'selected_assignment':None,'counts_are_confidence':False,'used_for_ranking':False,
        'voice_identity_confirmed':False,'harmonic_labels_used':False}
    if reasons:return result
    for indices in product(*(range(len(g['choices'])) for g in boundaries)):
        links=[pair for g,i in zip(boundaries,indices) for pair in g['choices'][i]]
        tracks=partition(events,links)
        sounds={s['sounding_event_id']:s for s in events}
        total=sum((min(b,f(sounds[sid]['span']['end']))-max(a,f(sounds[sid]['span']['start']))
                   for track in tracks for sid in track),f(q(0)))
        if total!=duration:raise ValueError('note_time_not_preserved')
        result['assignments'].append({'assignment_id':'vpaths_'+token([lane,span,links]),
            'local_choice_indices':list(indices),'links':links,'tracks':tracks,
            'all_events_used_once':True,'note_time_preserved':True,
            'selected':False})
    return result


def augment(ir, baseline):
    result=deepcopy(baseline);rows={};notes={n['note_id']:n for n in ir['note_events']}
    sounds={s['sounding_event_id']:s for s in ir['sounding_events']}
    for pid,p in baseline['bounded_path_context']['paths'].items():
        if not p['context_policy']['accepted']:
            rows[pid]={'status':'context_not_accepted','assignments':[]};continue
        src,dst=p['observation']['source_refs']
        identities={(notes[n]['part_id'],notes[n]['voice_id']) for n in sounds[src]['source_note_ids']}
        if len(identities)!=1:raise ValueError('ambiguous_source_lane')
        row=observe(ir,p['context_policy']['proposed_span'],next(iter(identities)))
        row['endpoint_refs']=[src,dst]
        row['endpoint_same_track_assignments']=sum(any(src in t and dst in t for t in a['tracks']) for a in row['assignments'])
        row['endpoint_continuity_observed']=False
        row['path_warnings']=p['observation']['abstention_reasons']
        rows[pid]=row
    result['continuous_voice_paths']={'version':VERSION,'paths':rows,
        'production_modified':False,'harmonic_results_changed':False,
        'limits':['Tracks are continuity hypotheses, not persistent contrapuntal voice identities.',
                  'No rest bridging, cross-lane links, voice splitting/merging, missing-note removal or ranking.',
                  'All partial matchings combined up to an explicit limit; over limit yields no partial selection.',
                  'Candidate membership totals cannot change merely by repartitioning the same notes.']}
    return result
