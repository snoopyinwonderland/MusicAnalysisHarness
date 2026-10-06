"""Ordered evidence for arpeggiation versus change, without selecting harmony."""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height

VERSION = 'temporal-coherence-0.1.0'


def membership(event, members):
    if spelled_height(event['pitch']) is None:
        return 'unknown'
    return 'member' if tuple(pitch_pair(event['pitch'])) in members else 'nonmember'


def profile_support(profile, cells, events):
    members = {tuple(m) for m in profile['members']}
    totals = {k: Fraction() for k in ('member_only', 'mixed', 'nonmember_only', 'silence', 'unknown')}
    runs = []; seen = set(); complete_at = None; foreign = set(); bass_runs = []
    cursor = f(profile['span']['start'])
    for row in profile['cells']:
        i = row['cell_index']; c = cells[i]; a, z = f(c['span']['start']), f(c['span']['end'])
        if a != cursor or z <= a: raise ValueError('noncontiguous_profile_cells')
        cursor = z
        refs = c['active_event_refs']
        states = {sid: membership(events[sid], members) for sid in refs}
        state = ('silence' if not refs else 'unknown' if 'unknown' in states.values() else
                 'mixed' if len(set(states.values())) > 1 else
                 'member_only' if next(iter(states.values())) == 'member' else 'nonmember_only')
        totals[state] += z - a
        foreign.update(sid for sid, value in states.items() if value == 'nonmember')
        seen.update(tuple(m) for m in row['present_members'])
        if complete_at is None and members and members <= seen: complete_at = deepcopy(c['span']['start'])
        if runs and runs[-1]['state'] == state:
            runs[-1]['span']['end'] = deepcopy(c['span']['end']); runs[-1]['cell_indices'].append(i)
        else:
            runs.append({'state': state, 'span': deepcopy(c['span']), 'cell_indices': [i]})
        bass = sorted({states[sid] for sid in c['lowest_event_refs']}) if c['bass_status'] == 'observed_lowest' else [c['bass_status']]
        if bass_runs and bass_runs[-1]['membership'] == bass and bass_runs[-1]['midi_pitch'] == c['lowest_midi_pitch']:
            bass_runs[-1]['span']['end'] = deepcopy(c['span']['end'])
        else:
            bass_runs.append({'span': deepcopy(c['span']), 'midi_pitch': c['lowest_midi_pitch'], 'membership': bass})
    if cursor != f(profile['span']['end']): raise ValueError('profile_span_not_covered')
    return {'span': deepcopy(profile['span']), 'runs': runs, 'lowest_pitch_runs': bass_runs,
        'cell_time_quarters': {k: q(v) for k, v in totals.items()},
        'first_complete_union_time': complete_at, 'nonmember_event_refs': sorted(foreign),
        'all_sounding_pitches_are_members': bool(totals['member_only']) and not any(totals[k] for k in ('mixed', 'nonmember_only', 'unknown')),
        'complete_union_contains_nonmembers': complete_at is not None and bool(foreign),
        'complete_union_crosses_silence': complete_at is not None and any(r['state'] == 'silence' and f(r['span']['start']) < f(complete_at) for r in runs),
        'arpeggiation_confirmed': False}


def compare(result, boundary_index, hold_index, left_index, right_index, assignment_ref):
    b = result['boundaries'][boundary_index]
    if b.get('temporal_observations', {}).get('status') != 'ready': raise ValueError('evidence_unavailable')
    assignment = next((a for a in result['assignments'] if a['assignment_id'] == assignment_ref), None)
    if assignment is None: raise ValueError('unknown_assignment')
    h, l, r = result['hold_readings'][hold_index], b['left']['readings'][left_index], b['right']['readings'][right_index]
    sets = [{tuple(m) for m in reading['members']} for reading in (h, l, r)]
    hm, lm, rm = sets; cut = f(b['boundary']); events = {s['sounding_event_id']: s for s in result['events']}
    def observed_exclusive(span, own, other):
        return sorted(sid for sid, s in events.items() if f(s['span']['start']) < f(span['end']) and f(s['span']['end']) > f(span['start'])
                      and membership(s, own) == 'member' and membership(s, other) == 'nonmember')
    left_exclusive = observed_exclusive(l['span'], lm, rm)
    right_exclusive = observed_exclusive(r['span'], rm, lm)
    links = []
    for x, y in assignment['links']:
        a, z = events[x], events[y]
        if f(a['span']['end']) != f(z['span']['start']): raise ValueError('noncontiguous_voice_link')
        if f(a['span']['start']) < cut <= f(z['span']['start']):
            links.append({'source_ref': x, 'target_ref': y,
                'transition_time': deepcopy(z['span']['start']),
                'at_boundary': f(z['span']['start']) == cut,
                'source_membership_after_boundary': membership(a, rm) if f(a['span']['end']) > cut else None,
                'hold_membership': [membership(a, hm), membership(z, hm)],
                'split_membership': [membership(a, lm), membership(z, rm)]})
    held = [{'event_ref': sid, 'left': membership(s, lm), 'right': membership(s, rm)}
            for sid, s in events.items() if f(s['span']['start']) < cut < f(s['span']['end'])]
    reasons = sorted({reason for reading in (h, l, r) for reason in reading['condition']['abstention_reasons']})
    return {'same_member_sets': lm == rm, 'left_exclusive_event_refs': left_exclusive,
        'right_exclusive_event_refs': right_exclusive,
        'two_sided_differentiating_members': bool(left_exclusive and right_exclusive),
        'boundary_voice_links': links, 'held_memberships': held, 'assignment_ref': assignment_ref,
        'candidate_abstention_reasons': reasons, 'preferred': None, 'harmonic_change_confirmed': False,
        'limits': ['Exclusive members may still be NCTs under the competing interpretation; no automatic split.',
                   'Voice links cover the sampled lane only; held common tones do not prove harmonic continuity.']}


def augment(baseline):
    result = deepcopy(baseline); events = {s['sounding_event_id']: s for s in result.get('events', [])}
    for b in result['boundaries']:
        e = b.get('temporal_observations', {})
        c = {'version': VERSION, 'status': 'evidence_unavailable', 'selected': None}
        if e.get('status') == 'ready':
            c.update(status='ready', profiles={pid: profile_support(p, e['cells'], events) for pid, p in e['candidate_support_profiles'].items()})
        b['temporal_coherence'] = c
    p = result.get('preview_selection')
    if p:
        result['temporal_coherence_preview'] = compare(result, p['boundary'], p['hold'], p['left'], p['right'], p['assignment'])
    result['temporal_coherence_version'] = VERSION
    return result
