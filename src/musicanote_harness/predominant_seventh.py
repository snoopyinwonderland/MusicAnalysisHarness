"""Unit 13 conditional seventh motion; not chord, preparation, or NCT truth."""
from collections import defaultdict
from .foundation_sonata_audit import pitch_tuple
from .harmony_case_retrieval import _f
from .tonal_foundations import scale_degree, spelled_interval

VERSION = 'predominant-seventh-motion-0.1.0'


def _time(value):
    if isinstance(value, (float, bool)):
        raise ValueError('rational_time_required')
    if isinstance(value, dict) and any(isinstance(value.get(k), bool) or
                                      not isinstance(value.get(k), int) for k in ('numerator', 'denominator')):
        raise ValueError('rational_time_required')
    return _f(value)


def assess(ir, target_span, context_span, family, tonic_step, tonic_alter=0, mode='major'):
    """Trace only touching, unambiguous notated voices within a bounded context.

    A voice containing chord members is NOT separated by pitch sorting. Sounding
    events are never clipped: tied notes keep their original start and release.
    Supplied family/key are hypotheses, even when obtained from source labels.
    """
    if family not in ('supertonic', 'subdominant') or mode not in ('major', 'minor'):
        raise ValueError('unsupported_family_or_mode')
    # Validate even an empty excerpt's key hypothesis.
    scale_degree(tonic_step, tonic_alter, tonic_step, tonic_alter)
    a, b = (_time(target_span[k]) for k in ('start', 'end'))
    left, right = (_time(context_span[k]) for k in ('start', 'end'))
    if not (0 <= left <= a < b <= right):
        raise ValueError('invalid_context_or_target_span')
    notes = {n['note_id']: n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']):
        raise ValueError('duplicate_note_id')
    rows, voices, seen = [], defaultdict(list), set()
    for s in ir['sounding_events']:
        sid = s['sounding_event_id']
        if sid in seen:
            raise ValueError('duplicate_sounding_event_id')
        seen.add(sid)
        x, y = (_time(s['span'][k]) for k in ('start', 'end'))
        if x < 0 or y < x:
            raise ValueError('invalid_event_span')
        if x == y or x >= right or y <= left:
            continue
        pitch = pitch_tuple(s)
        refs = s.get('source_note_ids', [])
        ns = [notes.get(n) for n in refs]
        if not refs or s.get('attack_note_id') not in refs or any(n is None for n in ns):
            raise ValueError('broken_source_note_reference')
        keys = {(n.get('part_id'), n.get('voice_id')) for n in ns}
        key = next(iter(keys)) if len(keys) == 1 else None
        if key is not None and not all(key):
            key = None
        row = {'id': sid, 'pitch': pitch, 'start': x, 'end': y, 'voice': key,
               'span': s['span'], 'source_note_ids': refs}
        rows.append(row)
        if key is not None:
            voices[key].append(row)

    def overlaps(row, others):
        return any(o['id'] != row['id'] and o['start'] < row['end'] and o['end'] > row['start']
                   for o in others)

    def neighbor(row, direction):
        group = voices[row['voice']]
        edge = row['start'] if direction == 'entry' else row['end']
        if (direction == 'entry' and edge <= left) or (direction == 'departure' and edge >= right):
            return {'status': 'context_censored'}
        candidates = [o for o in group if o['id'] != row['id'] and
                      (o['end'] == edge if direction == 'entry' else o['start'] == edge)]
        if not candidates:
            return {'status': 'no_touching_event'}
        if len(candidates) != 1 or overlaps(candidates[0], group):
            return {'status': 'ambiguous_voice'}
        other = candidates[0]
        first, second = (other, row) if direction == 'entry' else (row, other)
        interval = spelled_interval(first['pitch'], second['pitch'])
        repeated = first['pitch'] == second['pitch']
        down = interval['generic'] == -2 and interval['semitones'] in (-1, -2)
        status = ('repeated_same_pitch' if repeated else
                  'descending_step' if down else 'other_motion')
        return {'status': status, 'neighbor_event_id': other['id'], 'interval': interval}

    records = []
    for row in rows:
        if row['start'] >= b or row['end'] <= a:
            continue
        degree = scale_degree(*row['pitch'][:2], tonic_step, tonic_alter,
                              'major' if mode == 'major' else 'harmonic_minor')
        if degree['degree'] != (1 if family == 'supertonic' else 3) or not degree['diatonic_to_candidate']:
            continue
        if row['voice'] is None:
            entry = departure = {'status': 'missing_or_inconsistent_voice'}
        elif overlaps(row, voices[row['voice']]):
            entry = departure = {'status': 'ambiguous_voice'}
        else:
            entry = ({'status': 'held_across_target_start'} if row['start'] < a else neighbor(row, 'entry'))
            departure = neighbor(row, 'departure')
        records.append({'event_id': row['id'], 'source_note_ids': row['source_note_ids'],
                        'pitch': row['pitch'], 'original_span': row['span'],
                        'voice': row['voice'], 'entry': entry, 'departure': departure,
                        'departure_position': ('inside_target' if row['end'] < b else
                                               'at_target_end' if row['end'] == b else 'after_target_end'),
                        'seventh_membership': 'conditional_on_harmonic_hypothesis',
                        'preparation_verified': None, 'resolution_verified': None})
    return {'version': VERSION, 'target_span': target_span, 'context_span': context_span,
            'hypothesis': {'family': family, 'tonic_step': tonic_step, 'tonic_alter': tonic_alter, 'mode': mode},
            'records': records, 'harmonic_support': 'unassessed', 'cadence': None, 'nct': None,
            'production_enabled': False,
            'limitations': ['entry consonance and metric hierarchy unassessed',
                            'immediate touching event only; delayed/ornamented resolution not inferred',
                            'notated voice may contain polyphony; ambiguous paths abstain',
                            'missing seventh observations are not evidence against the hypothesis']}
