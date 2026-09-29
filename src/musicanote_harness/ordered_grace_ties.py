"""Resolve zero-time notated ties using verified source order, not performance.

An entire pitch/time bucket must have one source voice/staff and a balanced,
unambiguous sequence of explicit tie endpoints. Otherwise retain abstention.
"""
from collections import defaultdict
from fractions import Fraction
from .canonical import CanonicalIRBuilder
from .voice_tie_impact import source_tie_graph, check_chains

VERSION = 'ordered-grace-ties-0.1.0'


def resolve(segments):
    base = source_tie_graph(segments)
    by_id = {s['segment_id']: s for s in segments}
    edges = [(e['left'], e['right']) for e in base['edges']]
    resolved = []; abstained = []
    for part, pitch, raw_time in base['grace_barriers']:
        time = Fraction(raw_time); endpoints = []
        for s in segments:
            if s['part_id'] != part or s['pitch_spelling'] != pitch: continue
            incoming = s['tie_role'] in ('stop', 'continue') and Fraction(s['onset_ql']) == time
            outgoing = s['tie_role'] in ('start', 'continue') and Fraction(s['end_ql']) == time
            if incoming or outgoing: endpoints.append((s, incoming, outgoing))
        reason = None
        if any(s.get('source_order') is None for s, _, _ in endpoints): reason = 'missing_verified_source_order'
        elif len({(s['voice_id'], s['staff_id']) for s, _, _ in endpoints}) != 1: reason = 'multiple_source_lanes'
        elif len({tuple(s['source_order']) for s, _, _ in endpoints}) != len(endpoints): reason = 'duplicate_source_order'
        proposed = []; pending = None
        if reason is None:
            for s, incoming, outgoing in sorted(endpoints, key=lambda r: tuple(r[0]['source_order'])):
                if incoming:
                    if pending is None: reason = 'incoming_without_unique_predecessor'; break
                    proposed.append((pending, s['segment_id'])); pending = None
                if outgoing:
                    if pending is not None: reason = 'competing_outgoing_ties'; break
                    pending = s['segment_id']
            if pending is not None and reason is None: reason = 'unclosed_outgoing_tie'
        record = {'part': part, 'pitch': pitch, 'time': raw_time}
        if reason:
            abstained.append({**record, 'reason': reason})
        else:
            edges.extend(proposed); resolved.append({**record, 'edges': proposed})
    successors = {}; predecessors = {}
    for a, b in edges:
        if a in successors or b in predecessors: raise ValueError('branching_tie_graph')
        successors[a] = b; predecessors[b] = a
    sounds = []; issues = []; visited = set(); builder = CanonicalIRBuilder()
    for s in segments:
        sid = s['segment_id']
        if s['tie_role'] in ('start', 'continue') and sid not in successors: issues.append({'code': 'unresolved_outgoing', 'segment_id': sid})
        if s['tie_role'] in ('stop', 'continue') and sid not in predecessors: issues.append({'code': 'unresolved_incoming', 'segment_id': sid})
        if sid in predecessors: continue
        sound = builder._new_sounding_event(s, tied=s['tie_role'] != 'none')
        current = sid; visited.add(current)
        while current in successors:
            current = successors[current]
            if current in visited: raise ValueError('tie_cycle')
            visited.add(current); sound['segment_ids'].append(current)
            sound['sounding_end_ql'] = by_id[current]['end_ql']
            sound['crosses_measure_boundary'] = by_id[current]['measure'] != s['measure']
        sounds.append(sound)
    if visited != set(by_id): raise ValueError('unrooted_tie_cycle')
    sounds.sort(key=lambda s: (Fraction(s['attack_onset_ql']), s['pitch_midi'], s['sounding_event_id']))
    return {'sounds': sounds, 'edges': edges, 'issues': issues, 'resolved_grace_buckets': resolved,
            'abstained_grace_buckets': abstained, 'chain_problems': check_chains(sounds, segments),
            'timing_basis': 'notated_only_no_performed_duration_inference'}
