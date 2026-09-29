"""Unit 18 conditional chord patterns and separate, conservative IR geometry.

No key inference, harmonic verdict, latent voice separation or boundary merging.
"""
from collections import defaultdict
from .dominant_area_evidence import _exact
from .formal_ir import q
from .foundation_sonata_audit import pitch_tuple
from .root_position_context import candidate, root_relation, source_symbol
from .tonal_foundations import LETTERS, NATURAL

VERSION = 'diatonic-sequence-0.1.0'
MODELS = {
    'descending_fifths': ((3, 3, 3), 6, [6, 7]),
    'ascending_fifths': ((4, 4, 4), 1, [8, 9, 10]),
    'ascending_five_six': ((5, 3, 5), 1, [11, 12]),
    'descending_five_six': ((4, 1, 4), 5, [13, 14]),
}


def source_triad(annotation):
    """Only plain root/first-inversion triads; retain original annotation intact."""
    raw = annotation['raw_fields']
    figure = raw.get('figbass', '')
    if figure not in ('', '6'):
        return None
    symbol = source_symbol({'raw_fields': {**raw, 'figbass': ''}})
    return (symbol, int(figure == '6')) if symbol else None


def propose(symbols, inversions, tonic, alter=0, mode='major'):
    if len(symbols) != 4 or len(inversions) != 4:
        raise ValueError('four_supplied_triads_required')
    if any(type(i) is not int or i not in (0, 1) for i in inversions):
        raise ValueError('root_or_first_inversion_required')
    cs = [{**candidate(s, tonic, alter, mode), 'inversion': inv}
          for s, inv in zip(symbols, inversions)]
    relations = [root_relation(a, b) for a, b in zip(cs, cs[1:])]
    steps = tuple(r['diatonic_steps_up_mod7'] for r in relations)
    patterns = []
    for name, (model, shift, sections) in MODELS.items():
        if steps != model:
            continue
        allowed = [(0, 0, 0, 0), (0, 1, 0, 1)]
        if name.endswith('fifths'):
            allowed.append((1, 0, 1, 0))
        if tuple(inversions) not in allowed:
            continue
        patterns.append({'pattern': name, 'status': 'candidate', 'sections': sections,
                         'pair_shift_diatonic_steps_up_mod7': shift,
                         'inversion_pattern': inversions,
                         'needs_evidence': ['score_support_for_harmonic_hypotheses',
                                           'phrase_context_and_goal',
                                           'voice_leading_and_rhythmic_pattern']})
    return {'version': VERSION, 'basis': 'supplied_hypotheses_not_blind_detection',
            'key_hypothesis': {'tonic_step': tonic, 'tonic_alter': alter, 'mode': mode},
            'candidates': cs, 'root_relations': relations, 'pattern_candidates': patterns,
            'minor_raised_seventh_harmony_present': mode == 'minor' and any(s in ('V', '#viio') for s in symbols),
            'selected_pattern': None, 'sequence_confirmed': None, 'modulation': None,
            'cadence': None, 'phrase_boundary': None, 'merge_recommended': None,
            'production_enabled': False,
            'limitations': ['two adjacent two-chord statements only; not a universal unit length',
                            'chordal or melodic sequencing can occur without the other',
                            'natural minor variants retained; raised seventh needs contextual review',
                            'omitted pairs, corrective insertions and seventh chords not reconstructed',
                            'no match is not evidence against musical sequencing']}


def _bounds(span):
    a, b = _exact(span['start']), _exact(span['end'])
    if a < 0 or b <= a:
        raise ValueError('positive_nonnegative_span_required')
    return a, b


def _block(rows, bounds):
    a, b = bounds
    active = sorted((r for r in rows if r['onset'] < b and r['release'] > a),
                    key=lambda r: (r['onset'], r['event_id']))
    reasons = []
    if any(r['onset'] < a or r['release'] > b for r in active):
        reasons.append('sounding_event_crosses_block_boundary')
    if any(x['release'] > y['onset'] for x, y in zip(active, active[1:])):
        reasons.append('polyphonic_notated_voice')
    if len(active) < 2:
        reasons.append('fewer_than_two_sounding_events')
    return {'events': [{'event_id': r['event_id'], 'source_note_ids': r['source_note_ids'],
                        'pitch': r['pitch'], 'onset': q(r['onset']), 'release': q(r['release']),
                        'relative_onset': q((r['onset']-a)/(b-a)),
                        'relative_duration': q((r['release']-r['onset'])/(b-a))}
                       for r in active], 'abstention_reasons': reasons}


def compare_voices(ir, first_span, second_span):
    """Compare explicit part/voice identities, not highest notes or inferred melody.

    Original sounding durations survive; ties are not new attacks. Cross-staff
    notes keep the same voice. Grace events are listed separately, not harmonized.
    """
    bounds = [_bounds(first_span), _bounds(second_span)]
    if bounds[0][1] != bounds[1][0]:
        raise ValueError('touching_blocks_required')
    notes = {n['note_id']: n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']):
        raise ValueError('duplicate_note_id')
    voices = defaultdict(list)
    graces = []
    seen = set()
    for sound in ir['sounding_events']:
        sid = sound['sounding_event_id']
        if sid in seen:
            raise ValueError('duplicate_sounding_event_id')
        seen.add(sid)
        a, b = _exact(sound['span']['start']), _exact(sound['span']['end'])
        if a < 0 or b < a:
            raise ValueError('invalid_sounding_span')
        if a >= bounds[1][1] or b < bounds[0][0] or (b == bounds[0][0] and b > a):
            continue
        note = notes[sound['attack_note_id']]
        refs = sound['source_note_ids']
        if not refs or sound['attack_note_id'] not in refs or any(n not in notes for n in refs):
            raise ValueError('invalid_source_note_references')
        voice = (note['part_id'], note['voice_id'])
        if any((notes[n]['part_id'], notes[n]['voice_id']) != voice for n in refs):
            raise ValueError('tie_voice_identity_ambiguous')
        if note.get('grace', {}).get('is_grace'):
            graces.append(sid)
            continue
        if a == b:
            raise ValueError('zero_duration_non_grace')
        p = pitch_tuple(sound)
        voices[voice].append({'event_id': sid, 'source_note_ids': refs, 'onset': a,
                              'release': b, 'pitch': p})
    observations = []
    for (part, voice), rows in sorted(voices.items()):
        blocks = [_block(rows, span) for span in bounds]
        a, b = (x['events'] for x in blocks)
        reasons = sorted({r for x in blocks for r in x['abstention_reasons']})
        if len(a) != len(b):
            reasons.append('different_event_counts_no_forced_alignment')
        comparison = None
        if not reasons:
            steps = [(7*y['pitch'][2]+LETTERS.index(y['pitch'][0])) -
                     (7*x['pitch'][2]+LETTERS.index(x['pitch'][0])) for x, y in zip(a, b)]
            semis = [(12*y['pitch'][2]+NATURAL[LETTERS.index(y['pitch'][0])]+y['pitch'][1]) -
                     (12*x['pitch'][2]+NATURAL[LETTERS.index(x['pitch'][0])]+x['pitch'][1]) for x, y in zip(a, b)]
            rhythm = all(x['relative_onset'] == y['relative_onset'] and
                         x['relative_duration'] == y['relative_duration'] for x, y in zip(a, b))
            comparison = {'normalized_rhythm_equal': rhythm,
                          'diatonic_displacements': steps, 'semitone_displacements': semis,
                          'constant_diatonic_displacement': len(set(steps)) == 1,
                          'constant_semitone_displacement': len(set(semis)) == 1,
                          'nonzero_shifted_rhythm_and_spelled_shape': rhythm and len(set(steps)) == 1 and steps[0] != 0,
                          'duration_scale_factor': q((bounds[1][1]-bounds[1][0])/(bounds[0][1]-bounds[0][0])),
                          'diatonic_key_fit_verified': False}
        observations.append({'part_id': part, 'voice_id': voice, 'blocks': blocks,
                             'abstention_reasons': reasons, 'comparison': comparison})
    return {'version': VERSION, 'basis': 'notated_voice_sounding_event_geometry',
            'block_spans': [first_span, second_span], 'voices': observations,
            'excluded_grace_event_ids': sorted(graces), 'sequence_confirmed': None,
            'limitations': ['no reduction, NCT assignment or voice crossing repair',
                           'accidentals preserved but key fit not verified',
                           'exact signatures are support features; mismatch is not rejection',
                           'source-defined block boundaries are not independently detected']}
