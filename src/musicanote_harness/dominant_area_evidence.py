"""Unit 15 dual spelled-major coordinates, not key-area or pivot inference."""
from fractions import Fraction
from .tonal_foundations import LETTERS, NATURAL, major_degree, spelled_triad_shapes
from .predominant_sonata_audit import span_observation

VERSION = 'dominant-area-evidence-0.1.0'


def dominant_reference(tonic_step, tonic_alter=0):
    major_degree(tonic_step, tonic_alter, tonic_step, tonic_alter)
    i = LETTERS.index(tonic_step)
    j = (i+4) % 7
    target_natural = NATURAL[j] + (12 if j < i else 0)
    return LETTERS[j], NATURAL[i]+tonic_alter+7-target_natural


def _exact(value):
    if isinstance(value, dict):
        if any(isinstance(value.get(k), bool) or not isinstance(value.get(k), int)
               for k in ('numerator', 'denominator')) or value['denominator'] <= 0:
            raise ValueError('rational_time_required')
        return Fraction(value['numerator'], value['denominator'])
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise ValueError('rational_time_required')
    return Fraction(value)


def observe(ir, span, tonic_step, tonic_alter=0, mode='major'):
    if mode != 'major':
        raise ValueError('unit15_major_home_only')
    target_step, target_alter = dominant_reference(tonic_step, tonic_alter)
    start, end = (_exact(span[k]) for k in ('start', 'end'))
    if start < 0 or end <= start:
        raise ValueError('positive_span_required')
    for s in ir['sounding_events']:
        for k in ('start', 'end'):
            if _exact(s['span'][k]) < 0:
                raise ValueError('negative_event_time')
    inventory = span_observation(ir, span)

    def coordinates(pitch):
        return {'home': major_degree(*pitch[:2], tonic_step, tonic_alter),
                'dominant_area': major_degree(*pitch[:2], target_step, target_alter)}

    events = [{'event_id': r['event_id'], 'pitch': r['pitch'], **coordinates(r['pitch'])}
              for r in inventory['union_events']]
    shared = []
    for cell in inventory['slices']:
        pitches = [r['pitch'] for r in cell['events']]
        shapes = spelled_triad_shapes(pitches)
        if not shapes or not all(all(c['diatonic_to_candidate'] for c in coordinates(p).values()) for p in pitches):
            continue
        shared.append({'span': cell['span'], 'event_refs': [r['event_id'] for r in cell['events']],
                       'shapes': [{**s, 'root_coordinates': coordinates((s['root_step'], s['root_alter']))}
                                  for s in shapes],
                       'pivot_verified': None})
    return {'version': VERSION, 'span': span,
            'home_hypothesis': {'step': tonic_step, 'alter': tonic_alter, 'mode': 'major'},
            'dominant_reference': {'step': target_step, 'alter': target_alter, 'mode': 'major'},
            'event_coordinates': events, 'held_at_start_ids': inventory['held_at_start_ids'],
            'raised_fourth_event_refs': [e['event_id'] for e in events if
                                        (e['home']['degree'], e['home']['alteration_from_major']) == (4, 1)],
            'unaltered_fourth_event_refs': [e['event_id'] for e in events if
                                           (e['home']['degree'], e['home']['alteration_from_major']) == (4, 0)],
            'shared_diatonic_triad_slices': shared, 'key_area': None, 'modulation': None,
            'pivot_span': None, 'cadence': None, 'production_enabled': False,
            'limitations': ['supplied home key, not inferred key',
                            'common triad is compatibility, not an actual pivot',
                            'fourth-degree occurrence is not resolution or return-to-tonic proof',
                            'no duration threshold distinguishes tonicization from modulation',
                            'simultaneous complete shapes only; no NCT deletion or arpeggio union']}
