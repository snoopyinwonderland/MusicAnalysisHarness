"""Unit 16 conditional III/VII spelling evidence; no automatic key or function."""
from .dominant_area_evidence import _exact
from .tonal_foundations import (LETTERS, NATURAL, scale_degree,
                               spelled_triad_shapes, spelled_seventh_shapes)
from .predominant_sonata_audit import span_observation

VERSION = 'mediant-evidence-0.1.0'


def mediant_reference(step, alter=0, mode='minor'):
    if mode not in ('major', 'minor'):
        raise ValueError('explicit_major_or_minor_required')
    scale_degree(step, alter, step, alter)
    i = LETTERS.index(step)
    j = (i+2) % 7
    distance = 3 if mode == 'minor' else 4
    return LETTERS[j], NATURAL[i]+alter+distance-NATURAL[j]-(12 if j < i else 0), ('major' if mode == 'minor' else 'minor')


def shape_readings(shape, home, mode):
    """Compatible readings of a complete shape, not independently verified roles."""
    d, a = home['degree'], home['alteration_from_scale']
    quality = shape['quality']
    if mode == 'minor':
        if (d, a, quality) == (7, 0, 'major'):
            return ['natural_VII', 'V_of_III']
        if (d, a, quality) == (7, 0, 'major_minor_seventh'):
            return ['natural_VII7', 'V7_of_III']
        if (d, a, quality) == (7, 1, 'diminished'):
            return ['leading_tone_triad_of_home']
        if (d, a, quality) == (3, 0, 'major'):
            return ['III', 'I_in_relative_major']
        if (d, a, quality) == (3, 0, 'augmented'):
            return ['augmented_mediant_shape_requires_dominant_context_review']
        if (d, a, quality) == (2, 0, 'diminished'):
            return ['ii_diminished', 'leading_tone_triad_of_III']
    else:
        if (d, a, quality) == (3, 0, 'minor'):
            return ['iii', 'i_in_mediant_minor']
        if (d, a, quality) == (7, 0, 'diminished'):
            return ['leading_tone_triad_of_home']
        if (d, a, quality) == (7, 0, 'major'):
            return ['V_of_iii']
        if (d, a, quality) == (7, 0, 'major_minor_seventh'):
            return ['V7_of_iii']
    return []


def observe(ir, span, tonic_step, tonic_alter=0, mode='minor'):
    ms, ma, mm = mediant_reference(tonic_step, tonic_alter, mode)
    start, end = (_exact(span[k]) for k in ('start', 'end'))
    if start < 0 or end <= start:
        raise ValueError('positive_span_required')
    zero_duration_refs = []
    for event in ir['sounding_events']:
        a, b = (_exact(event['span'][k]) for k in ('start', 'end'))
        if a < 0 or b < a:
            raise ValueError('nonnegative_sounding_span_required')
        if a == b and start <= a < end:
            zero_duration_refs.append(event['sounding_event_id'])
    home_form = 'natural_minor' if mode == 'minor' else 'major'
    target_form = 'natural_minor' if mm == 'minor' else 'major'

    def coordinates(p):
        return {'home': scale_degree(*p[:2], tonic_step, tonic_alter, form=home_form),
                'mediant': scale_degree(*p[:2], ms, ma, form=target_form)}

    inventory = span_observation(ir, span)
    events = [{**e, **coordinates(e['pitch'])} for e in inventory['union_events']]
    cells = []
    for cell in inventory['slices']:
        pitches = [e['pitch'] for e in cell['events']]
        shapes = spelled_triad_shapes(pitches)+spelled_seventh_shapes(pitches)
        for shape in shapes:
            coord = coordinates((shape['root_step'], shape['root_alter']))
            shape['root_coordinates'] = coord
            shape['compatible_readings'] = shape_readings(shape, coord['home'], mode)
            shape['selected_reading'] = None
        cells.append({'span': cell['span'], 'event_refs': [e['event_id'] for e in cell['events']],
                      'complete_shapes': shapes})
    return {'version': VERSION, 'span': span,
            'home_hypothesis': {'step': tonic_step, 'alter': tonic_alter, 'mode': mode},
            'mediant_reference': {'step': ms, 'alter': ma, 'mode': mm},
            'event_coordinates': events, 'held_at_start_ids': inventory['held_at_start_ids'],
            'zero_duration_event_refs': zero_duration_refs,
            'subtonic_event_refs': [e['event_id'] for e in events if mode == 'minor' and
                                   (e['home']['degree'], e['home']['alteration_from_scale']) == (7, 0)],
            'leading_tone_event_refs': [e['event_id'] for e in events if
                                       (e['home']['degree'], e['home']['alteration_from_scale']) == (7, 1 if mode == 'minor' else 0)],
            'slices': cells, 'tonicization': None, 'modulation': None, 'cadence': None,
            'selected_function': None, 'production_enabled': False,
            'limitations': ['supplied home key, not inferred key',
                            'natural minor is a coordinate reference, not an accidental ban',
                            'relative major shares the natural-minor pitch collection; fit cannot prove modulation',
                            'complete vertical shapes only; no union chord or NCT removal',
                            'zero-duration events retained by reference, excluded from sustained vertical slices; performed grace timing unknown',
                            'compatible readings need voice, bass, meter and later arrival evidence',
                            'augmented III and rootless V65 require contextual alternatives, never automatic relabeling']}
