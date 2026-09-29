"""Unit33 conditional enharmonic alternatives, not automatic modulation.

Templates, literal event continuity, and interpretation remain separate. A
source key change is not a ground-truth modulation. No score-specific rules.
"""
from .applied_chords import offset
from .augmented_sixth import hypothesis as augmented, pc
from .chromatic_voice_leading import _blocks, _midi
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .seventh_context import chord
from .tonal_foundations import spelled_interval

VERSION = 'chromatic-tonal-context-0.1.0'


def canonical_shape(h):
    if h is None:
        return None
    c = (augmented(h['key'], h['family'], h['bass_role']) if h.get('family')
         else chord(h['root'], h['quality'], h['inversion']))
    if h['members'] != c['members'] or h['expected_bass'] != c['expected_bass']:
        raise ValueError('inconsistent_supplied_shape')
    return c


def compare_shapes(first, second):
    a, b = canonical_shape(first), canonical_shape(second)
    if a is None or b is None:
        return None
    aps, bps = {pc(p) for p in a['members']}, {pc(p) for p in b['members']}
    spell = {tuple(p) for p in a['members']} & {tuple(p) for p in b['members']}
    # Index changes can represent chord-factor changes; they are not yet
    # musical function changes. Keep all spellings rather than rewriting IR.
    mapping = [{'first_index': i, 'second_index': j, 'first': x, 'second': y,
                'same_spelling': x == y}
               for i, x in enumerate(a['members']) for j, y in enumerate(b['members']) if pc(x) == pc(y)]
    return {'common_pitch_classes': sorted(aps & bps),
            'common_spellings': [list(p) for p in sorted(spell)],
            'same_pitch_class_set': aps == bps,
            'same_spelling_set': {tuple(p) for p in a['members']} == {tuple(p) for p in b['members']},
            'member_mapping': mapping, 'functional_reinterpretation': None}


def reinterpretations(h):
    """12-TET pitch-class alternatives, with original spellings retained.

    The generated spelling is only one explicit hypothesis. No probability,
    destination-key estimate, or evidence of an actual pivot is supplied.
    """
    c = canonical_shape(h)
    if c is None:
        return []
    alternatives = []
    if c.get('quality') == 'o7':
        for root in c['members']:
            other = chord(root, 'o7')
            inv = next(i for i, p in enumerate(other['members']) if pc(p) == pc(c['expected_bass']))
            alternatives.append(('diminished_seventh_leading_tone_shape',
                                 offset(root, 1, 1), chord(root, 'o7', inv)))
    elif c.get('quality') == 'Mm7':
        tonic = offset(c['root'], 2, 4)
        other = augmented([*tonic, 'minor'], 'Ger')
        bass_role = next(role for role, p in other['roles'].items() if pc(p) == pc(c['expected_bass']))
        alternatives.append(('dominant7_to_German6_shape', tonic,
                             augmented([*tonic, 'minor'], 'Ger', bass_role)))
    elif c.get('family') == 'Ger':
        root = c['roles']['flat6']
        other = chord(root, 'Mm7')
        inv = next(i for i, p in enumerate(other['members']) if pc(p) == pc(c['expected_bass']))
        alternatives.append(('German6_to_dominant7_shape', offset(root, 3, 5), chord(root, 'Mm7', inv)))
    return [{'kind': kind, 'target_tonic_spelling': tonic, 'target_modes': ['major', 'minor'],
             'alternative_shape': other, 'shape_comparison': compare_shapes(c, other),
             'actual_modulation': None, 'enharmonic_function_change': None,
             'caveat': 'PC-equivalent template only; original orientation, voice resolution and sustained key context required'}
            for kind, tonic, other in alternatives]


def compare_following(alternatives, following):
    """Record immediate shape compatibility, never skip an unknown chord."""
    h = canonical_shape(following)
    rows = []
    for a in alternatives:
        tonic = a['target_tonic_spelling']
        roles, pc_roles = [], []
        if h and h.get('quality') in ('M', 'm') and h['inversion'] in (0, 1) and h['root'] == tonic:
            roles.append('tonic_triad_shape')
        if h and ((h.get('quality') == 'M' and h['inversion'] in (0, 1)) or h.get('quality') == 'Mm7') and h['root'] == offset(tonic, 4, 7):
            roles.append('dominant_shape')
        if h and h.get('quality') in ('M', 'm') and h['inversion'] in (0, 1) and pc(h['root']) == pc(tonic):
            pc_roles.append('tonic_triad_shape')
        if h and ((h.get('quality') == 'M' and h['inversion'] in (0, 1)) or h.get('quality') == 'Mm7') and pc(h['root']) == pc(offset(tonic, 4, 7)):
            pc_roles.append('dominant_shape')
        rows.append({'kind': a['kind'], 'target_tonic_spelling': tonic,
                     'following_shape_status': 'known' if h else 'unknown',
                     'compatible_roles': roles, 'pitch_class_compatible_roles': pc_roles,
                     'resolution_confirmed': None})
    return rows


def observe_transition(ir, left_span, right_span):
    a, t = (_exact(left_span[k]) for k in ('start', 'end'))
    u, b = (_exact(right_span[k]) for k in ('start', 'end'))
    if not 0 <= a < t == u < b:
        raise ValueError('positive_adjacent_spans_required')
    context = {'start': left_span['start'], 'end': right_span['end']}
    blocks, diagnostics = _blocks(ir, context)
    notes = {n['note_id']: n for n in ir['note_events']}
    held = []
    for s in ir['sounding_events']:
        x, y = (_exact(s['span'][k]) for k in ('start', 'end'))
        if not x < t < y:
            continue
        if any(notes[n].get('grace', {}).get('is_grace') for n in s['source_note_ids']):
            continue
        held.append({'event_id': s['sounding_event_id'], 'source_note_ids': s['source_note_ids'],
                     'pitch': list(pitch_tuple(s)), 'span': s['span']})
    links = []
    for block in blocks:
        for x, y in zip(block, block[1:]):
            if _exact(x['span']['end']) != t or _exact(y['span']['start']) != t:
                continue
            delta = _midi(y['pitch']) - _midi(x['pitch'])
            tags = []
            if delta == 0:
                tags.append('same_pitch_reattack' if x['pitch'] == y['pitch'] else 'enharmonic_reattack')
            if abs(delta) == 1 and x['pitch'][0] == y['pitch'][0] and x['pitch'][2] == y['pitch'][2]:
                tags.append('same_letter_chromatic_inflection')
            links.append({'before': x, 'after': y, 'interval': spelled_interval(x['pitch'], y['pitch']),
                          'tags': tags})
    return {'version': VERSION, 'left_span': left_span, 'right_span': right_span,
            'held_events': held, 'direct_voice_links': links, 'diagnostics': diagnostics,
            'common_tone_modulation': None, 'functional_enharmonic_change': None,
            'notational_enharmonic_only': None, 'cadence': None, 'merge_recommended': None,
            'source_labels_used_for_geometry': False,
            'limits': ['supplied boundary; not automatic segmentation',
                       'held event is literal duration, not a structural common tone or pedal verdict',
                       'direct links require unambiguous explicit IR voice; gaps/transfers/latent voices deferred',
                       'functional enharmonics may be unnotated; respelling alone proves neither function nor modulation']}


def common_tone_support(evidence, first, second):
    comparison = compare_shapes(first, second)
    if comparison is None:
        return None
    pcs = set(comparison['common_pitch_classes'])
    return {'shape_comparison': comparison,
            'held_common_event_ids': [x['event_id'] for x in evidence['held_events'] if pc(x['pitch']) in pcs],
            'reattacked_common_links': [i for i, x in enumerate(evidence['direct_voice_links'])
                if any(t in x['tags'] for t in ('same_pitch_reattack', 'enharmonic_reattack')) and pc(x['before']['pitch']) in pcs],
            'prominent_common_tone': None, 'pivot_absence_confirmed': None, 'common_tone_modulation': None}
