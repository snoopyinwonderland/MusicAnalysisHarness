"""Label-blind partial matchings at simultaneous releases/attacks.

Every matching is a hypothesis, including leaving every endpoint unconnected.
No closest-pitch winner, probability, hidden voice creation or harmonic rerank.
"""
from collections import defaultdict,Counter
from itertools import combinations
import hashlib
from .formal_ir import q
from .harmony_joint import f
from .harmony_reading_voice_context import spelled_height,relation

VERSION='polyphonic-link-hypotheses-0.1.0'
MAX_ENDPOINTS=4


def partial_matchings(left,right):
    """All injective partial maps; empty map preserves the no-link alternative."""
    if len(left)>MAX_ENDPOINTS or len(right)>MAX_ENDPOINTS:raise ValueError('endpoint_limit')
    def walk(index,used,pairs):
        if index==len(left):
            yield list(pairs);return
        yield from walk(index+1,used,pairs)
        for j,target in enumerate(right):
            if j not in used:yield from walk(index+1,used|{j},pairs+[(left[index],target)])
    return list(walk(0,set(),[]))


def observe(ir,contexts):
    notes={n['note_id']:n for n in ir['note_events']};lanes=defaultdict(list);skipped=Counter()
    spans=[(f(c['start']),f(c['end'])) for c in contexts]
    if any(a<0 or b<=a for a,b in spans):raise ValueError('invalid_context')
    for s in ir['sounding_events']:
        if not any(f(s['span']['start'])<b and f(s['span']['end'])>a for a,b in spans):continue
        ns=[notes.get(n) for n in s.get('source_note_ids',[])]
        if not ns or any(n is None for n in ns):skipped['missing_source_identity']+=1;continue
        keys={(n.get('part_id'),n.get('voice_id')) for n in ns}
        if len(keys)!=1 or not all(next(iter(keys))):skipped['missing_or_cross_voice_identity']+=1;continue
        if f(s['span']['end'])<=f(s['span']['start']):skipped['zero_or_negative_duration']+=1;continue
        lanes[next(iter(keys))].append(s)
    groups=[];abstentions=[]
    for (part,voice),events in sorted(lanes.items()):
        # Discontinuous releases are never connected to a later attack here.
        times={f(s['span']['end']) for s in events}&{f(s['span']['start']) for s in events}
        for t in sorted(times):
            if not any(a<t<b for a,b in spans):continue
            source=sorted((s for s in events if f(s['span']['end'])==t),key=lambda s:s['sounding_event_id'])
            target=sorted((s for s in events if f(s['span']['start'])==t),key=lambda s:s['sounding_event_id'])
            held=sorted((s for s in events if f(s['span']['start'])<t<f(s['span']['end'])),key=lambda s:s['sounding_event_id'])
            if max(len(source),len(target))<2:continue
            base={'time':q(t),'part_id':part,'voice_id':voice,'source_refs':[s['sounding_event_id'] for s in source],
                'target_refs':[s['sounding_event_id'] for s in target],'held_refs':[s['sounding_event_id'] for s in held]}
            if max(len(source),len(target))>MAX_ENDPOINTS:
                abstentions.append({**base,'reason':'endpoint_limit_no_silent_pruning'});continue
            edges=[];by_pair={}
            for s in source:
                for d in target:
                    hs,hd=spelled_height(s['pitch']),spelled_height(d['pitch'])
                    pair=(s['sounding_event_id'],d['sounding_event_id'])
                    edge={'source_refs':list(pair),'source_pitch':s['pitch'],'target_pitch':d['pitch'],
                        'source_span':s['span'],'target_span':d['span'],
                        'semitones':d['pitch']['midi_pitch']-s['pitch']['midi_pitch'],
                        'diatonic_steps':None if hs is None or hd is None else hd-hs,
                        'status':'possible_polyphonic_connection_not_observed_voice',
                        'contrapuntal_voice_identity_confirmed':False}
                    by_pair[pair]=len(edges);edges.append(edge)
            assignments=[]
            for pairs in partial_matchings(base['source_refs'],base['target_refs']):
                refs=[by_pair[p] for p in pairs];es=[edges[i] for i in refs]
                crossings=sum((a['source_pitch']['midi_pitch']-b['source_pitch']['midi_pitch'])*(a['target_pitch']['midi_pitch']-b['target_pitch']['midi_pitch'])<0 for a,b in combinations(es,2))
                held_crossings=sum((e['source_pitch']['midi_pitch']-h['pitch']['midi_pitch'])*(e['target_pitch']['midi_pitch']-h['pitch']['midi_pitch'])<0 for e in es for h in held)
                assignments.append({'edge_indices':refs,'unmatched_source_refs':[s for s in base['source_refs'] if all(s!=p[0] for p in pairs)],
                    'unmatched_target_refs':[d for d in base['target_refs'] if all(d!=p[1] for p in pairs)],
                    'motion_semitones':sum(abs(e['semitones']) for e in es),'crossing_count':crossings,'crossing_held_event_count':held_crossings,
                    'large_leap_count':sum(abs(e['semitones'])>12 for e in es),'selected':False})
            gid='plink_'+hashlib.sha256(('|'.join([str(t),part,voice]+base['source_refs']+base['target_refs'])).encode()).hexdigest()[:20]
            groups.append({**base,'group_id':gid,'edges':edges,'assignments':assignments,'selected_assignment':None,
                'harmonic_labels_used':False,'assignment_counts_are_confidence':False})
    return {'version':VERSION,'groups':groups,'abstentions':abstentions,'skipped_sound_reasons':dict(skipped),
        'source_annotations_used':False,'production_enabled':False,
        'limits':['Only exact simultaneous release/attack within one explicit IR part/voice',
            'No rest bridging, distributed arrival, cross-voice matching or voice splitting/merging',
            'Held sounds keep their identity and are not reassigned',
            'All partial injective matchings retained up to 4 endpoints each; no closest-pitch winner',
            'Motion/crossings are observations, not calibrated costs or probabilities']}


def evaluate(group,source_chord,target_chord):
    """Post-hoc conditional roles; never influence generation or assignment order."""
    tags=[relation(e,source_chord,target_chord) for e in group['edges']]
    resolution=[i for i,ts in enumerate(tags) if any(t.startswith('conditional_') for t in ts)]
    supported=[i for i,a in enumerate(group['assignments']) if set(a['edge_indices'])&set(resolution)]
    return {'source_chord':source_chord,'target_chord':target_chord,'edge_relations':tags,
        'conditional_resolution_edge_indices':resolution,'supporting_assignment_indices':supported,
        'assignment_sensitive':bool(supported) and len(supported)<len(group['assignments']),
        'function_confirmed':False,'probability':None,'used_for_ranking':False}
