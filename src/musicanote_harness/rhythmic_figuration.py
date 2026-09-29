"""Unit22 literal boundary retention, then separate conditional membership.

No inferred sustain, NCT verdict, meter/phrase inference, or score mutation.
"""
from collections import defaultdict
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .formal_ir import q
from .tonal_foundations import spelled_interval

VERSION = 'rhythmic-figuration-0.1.0'


def observe(ir, left_span, right_span):
    a, b = (_exact(left_span[k]) for k in ('start', 'end'))
    c, d = (_exact(right_span[k]) for k in ('start', 'end'))
    if not 0 <= a < b == c < d:
        raise ValueError('positive_touching_spans_required')
    notes = {n['note_id']: n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']): raise ValueError('duplicate_note_id')
    voices = defaultdict(list); excluded = []; seen = set()
    for s in ir['sounding_events']:
        sid = s['sounding_event_id']
        if sid in seen: raise ValueError('duplicate_sounding_event_id')
        seen.add(sid)
        x, y = (_exact(s['span'][k]) for k in ('start', 'end'))
        if x < 0 or y < x: raise ValueError('invalid_event_span')
        if x >= d or y < a: continue
        refs = s.get('source_note_ids', [])
        ns = [notes.get(n) for n in refs]
        if not refs or s.get('attack_note_id') not in refs or any(n is None for n in ns):
            raise ValueError('broken_source_note_reference')
        grace = any(n.get('grace', {}).get('is_grace', False) for n in ns)
        if x == y and not grace: raise ValueError('zero_duration_non_grace')
        if grace:
            excluded.append({'event_id': sid, 'reason': 'grace_not_literal_timing'}); continue
        keys = {(n.get('part_id'), n.get('voice_id')) for n in ns}
        if len(keys) != 1 or not all(next(iter(keys))):
            excluded.append({'event_id': sid, 'reason': 'missing_or_mixed_voice_identity'}); continue
        key = next(iter(keys))
        voices[key].append({'event_id': sid, 'pitch': list(pitch_tuple(s)), 'span': s['span'],
                            'source_note_ids': list(refs), 'x': x, 'y': y})

    def public(row): return {k: v for k, v in row.items() if k not in ('x', 'y')}
    results = []
    for (part, voice), rows in sorted(voices.items()):
        rows.sort(key=lambda r: (r['x'], r['y'], r['event_id']))
        def ambiguous(row):
            return any(r is not row and max(r['x'], row['x'], a) < min(r['y'], row['y'], d) for r in rows)
        for current in rows:
            prep = current; mode = None
            if current['x'] < b < current['y']:
                mode = 'literal_sustain_across_boundary'
            elif current['x'] == b:
                previous = [r for r in rows if r['y'] == b and r['pitch'] == current['pitch']]
                if len(previous) == 1:
                    prep = previous[0]; mode = 'same_pitch_restrike_at_boundary'
            if mode is None: continue
            reasons = []
            if ambiguous(prep) or ambiguous(current): reasons.append('polyphonic_or_ambiguous_notated_voice')
            chain = [current]; departure = None; status = 'context_censored'
            if not reasons:
                while chain[-1]['y'] < d:
                    tail = chain[-1]
                    following = [r for r in rows if r['x'] == tail['y']]
                    if not following:
                        status = 'no_touching_event_no_gap_bridging'; break
                    if len(following) != 1 or ambiguous(following[0]):
                        status = 'ambiguous_departure'; break
                    nxt = following[0]
                    if nxt['pitch'] == tail['pitch']:
                        chain.append(nxt); continue
                    departure = public(nxt); status = 'direct_pitch_change'; break
            else: status = 'voice_abstention'
            motion = spelled_interval(current['pitch'], departure['pitch']) if departure else None
            results.append({'part_id': part, 'voice_id': voice, 'boundary_mode': mode,
                'preparation_event': public(prep), 'boundary_event': public(current),
                'retained_attack_chain': [public(r) for r in chain],
                'left_overlap': {'start': q(max(a, prep['x'])), 'end': q(b)},
                'right_retention': {'start': q(b), 'end': q(min(d, chain[-1]['y']))},
                'departure': departure, 'departure_status': status, 'motion': motion,
                'abstention_reasons': reasons, 'relative_accent': 'unassessed',
                'preparation_consonance': 'unassessed', 'suspension_interval_numbers': None})
    return {'version': VERSION, 'basis': 'literal_score_timing_and_supplied_boundary',
            'spans': [left_span, right_span], 'boundary': q(b), 'retentions': results,
            'excluded_events': excluded, 'nct_verdict': None, 'pedal_function': None,
            'production_enabled': False,
            'limitations': ['only explicit monophonic voice paths; cross-staff same voice permitted',
                'no indirect, decorated, transferred, omitted or implied resolution inference',
                'same-pitch restrikes preserve separate attacks; no synthetic ties',
                'sustained common tones are not automatically suspensions or pedals',
                'no accent gate: weak-position and upward-release possibilities remain open',
                'supplied boundaries are not independently detected harmonic changes']}


def condition_on_members(observation, left_members, right_members):
    """Explicit spelled member lists permit triads/sevenths without label parsing.

    Membership is not consonance. In particular a seventh can prepare a delay.
    These tags are compatibility tests under hypotheses, NOT NCT labels.
    """
    templates = []
    for members in (left_members, right_members):
        if not members: raise ValueError('nonempty_spelled_members_required')
        template = set()
        for item in members:
            if len(item) != 2: raise ValueError('step_alter_pairs_required')
            step, alter = item
            spelled_interval((step, alter, 4), (step, alter, 4))
            template.add((step, alter))
        templates.append(template)
    results = []
    for i, r in enumerate(observation['retentions']):
        pitch = tuple(r['boundary_event']['pitch'][:2]); before, after = [pitch in t for t in templates]
        departure = r['departure']; dest = bool(departure and tuple(departure['pitch'][:2]) in templates[1])
        step = bool(r['motion'] and abs(r['motion']['generic']) == 2 and abs(r['motion']['semitones']) in (1, 2))
        tags = []
        if not r['abstention_reasons']:
            if before and after: tags.append('common_member_retention')
            elif not before and after: tags.append('early_arrival_compatible')
            if not after and dest and step:
                tags.append('delayed_step_arrival_compatible')
        results.append({'retention_index': i, 'member_before': before, 'member_after': after,
                        'departure_member_after': dest if departure else None, 'step_motion': step,
                        'compatibility_tags': tags, 'nct_verdict': None})
    return {'basis': 'supplied_spelled_chord_members_not_harmonic_truth',
            'supplied_members': [left_members, right_members], 'records': results,
            'consonance_verified': False, 'cadence': None, 'production_enabled': False}
