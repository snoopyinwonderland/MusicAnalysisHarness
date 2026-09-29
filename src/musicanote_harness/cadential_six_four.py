"""Unit 11 conditional surface/motion evidence, never a cadence classifier.

Source spelling and sounding spans remain unchanged. A caller supplies a key
hypothesis and two instants; no source harmony/cadence labels enter this function.
Polyphonic MusicXML voices are not assumed to be individual melodic strands.
"""
from collections import defaultdict
from .formal_ir import q
from .harmony_case_retrieval import _f
from .foundation_sonata_audit import pitch_tuple
from .tonal_foundations import scale_degree, LETTERS, NATURAL

VERSION = 'cadential-six-four-evidence-0.1.0'


def assess(ir, before_time, after_time, tonic_step, tonic_alter=0, mode='major'):
    a, b = _f(before_time), _f(after_time)
    if a >= b:
        raise ValueError('ordered_instants_required')
    if mode not in ('major', 'minor'):
        raise ValueError('major_or_minor_required')
    notes = {n['note_id']: n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']):
        raise ValueError('duplicate_note_id')
    rows, ids = [], set()
    for s in ir['sounding_events']:
        eid = s['sounding_event_id']
        if eid in ids:
            raise ValueError('duplicate_sounding_id')
        ids.add(eid)
        x, y = _f(s['span']['start']), _f(s['span']['end'])
        if y < x:
            raise ValueError('negative_duration')
        if not (x <= a < y or x <= b < y):
            continue
        step, alter, octave = pitch_tuple(s)
        coord = scale_degree(step, alter, tonic_step, tonic_alter,
                             'major' if mode == 'major' else 'harmonic_minor')
        note = notes.get(s.get('attack_note_id'))
        if note is None:
            raise ValueError('missing_attack_note_reference')
        rows.append({'event_id': eid, 'pitch': [step, alter, octave],
                     'midi': 12*(octave+1)+NATURAL[LETTERS.index(step)]+alter,
                     'degree': coord['degree'], 'diatonic': coord['diatonic_to_candidate'],
                     'voice_id': note.get('voice_id'), 'part_id': note.get('part_id'),
                     'source_note_ids': s.get('source_note_ids', []),
                     'original_span': s['span'], 'on': x, 'off': y})

    def snapshot(t):
        active = [r for r in rows if r['on'] <= t < r['off']]
        low = min((r['midi'] for r in active), default=None)
        bass = [r for r in active if r['midi'] == low]
        degrees = {r['degree'] for r in active}
        valid = bool(active) and all(r['diatonic'] for r in active)
        bass5 = bool(bass) and all(r['degree'] == 5 and r['diatonic'] for r in bass)
        return active, {'at': q(t), 'event_refs': [r['event_id'] for r in active],
            'degree_set': sorted(degrees), 'bass_event_refs': [r['event_id'] for r in bass],
            'bass_on_degree5': bass5,
            'complete_tonic_six_four_shape': bool(valid and bass5 and degrees == {1,3,5}),
            'dominant_shape': ('V' if degrees == {5,7,2} else
                               'V7' if degrees == {5,7,2,4} else
                               'V7_missing_fifth' if degrees == {5,7,4} else None)
                              if valid and bass5 else None}
    left, l = snapshot(a)
    right, r = snapshot(b)
    groups = [defaultdict(list), defaultdict(list)]
    for group, active in zip(groups, (left, right)):
        for row in active:
            if row['voice_id'] and row['part_id']:
                group[(row['part_id'], row['voice_id'])].append(row)
    motions, ambiguous = [], []
    for identity in sorted(set(groups[0]) & set(groups[1])):
        x, y = groups[0][identity], groups[1][identity]
        if len(x) != 1 or len(y) != 1:
            ambiguous.append(list(identity))
            continue
        x, y = x[0], y[0]
        # Do not leap across an intervening note and call it direct resolution.
        continuous = x['event_id'] == y['event_id'] or x['off'] == y['on']
        step = y['midi'] - x['midi']
        relation = None
        if continuous and x['diatonic'] and y['diatonic']:
            if (x['degree'], y['degree']) == (1,7) and step == -1:
                relation = '4_to_3'
            elif (x['degree'], y['degree']) == (3,2) and step in (-1,-2):
                relation = '6_to_5'
            elif (x['degree'], y['degree']) == (3,4) and step in (1,2):
                relation = '6_to_7_alternative'
        motions.append({'voice_ref': list(identity), 'event_refs': [x['event_id'], y['event_id']],
                        'direct_temporal_connection': continuous, 'semitones': step,
                        'relation': relation})
    shapes = l['complete_tonic_six_four_shape'] and r['dominant_shape'] is not None
    links = {m['relation'] for m in motions}
    support = shapes and '4_to_3' in links and bool(links & {'6_to_5','6_to_7_alternative'})
    return {'version': VERSION,
        'key_hypothesis': {'tonic_step': tonic_step, 'tonic_alter': tonic_alter, 'mode': mode},
        'observations': [l, r], 'motion_evidence': motions, 'ambiguous_voice_refs': ambiguous,
        'events': [{k:v for k,v in row.items() if k not in ('on','off')} for row in rows],
        'surface_pair_supported': shapes, 'direct_resolution_geometry_supported': bool(support),
        'metric_relation': 'unassessed', 'preparation': 'unassessed',
        'preceding_harmonic_function': 'unassessed', 'cadence': None,
        'functional_verdict': None, 'production_enabled': False,
        'limitations': ['two_instants_not_whole_episode', 'no_inner_voice_separation',
                       'geometry_does_not_establish_cadence', 'key_is_supplied_not_inferred']}
