"""Unit 14: competing roles conditional on supplied harmonic hypotheses.

This is not an audio/score chord classifier. Source annotations may be supplied
only in a declared source-conditioned audit, never passed off as blind inference.
No candidate automatically becomes a cadence, prolongation, or phrase boundary.
"""
VERSION = 'tonal-role-context-0.1.0'


def propose(previous, current, following, mode='major'):
    if mode not in ('major', 'minor'):
        raise ValueError('major_or_minor_required')
    tonic, sub, vi = ('I', 'IV', 'vi') if mode == 'major' else ('i', 'iv', 'VI')
    allowed = {None, tonic, tonic+'6', sub, sub+'6', vi, 'V', 'V7', 'V6', 'V65'}
    if mode == 'minor':
        allowed.add('IV6')  # raised sixth; distinct from iv6
    if any(x not in allowed for x in (previous, current, following)):
        raise ValueError('unsupported_hypothesis_symbol')
    if current is None:
        raise ValueError('current_hypothesis_required')
    roles, cadences = [], []

    def add(role, sections, needed):
        roles.append({'role': role, 'status': 'candidate', 'unit': 14, 'sections': sections,
                      'needs_evidence': ['harmonic_hypotheses_supported_by_score', *needed]})

    tonics = {tonic, tonic+'6'}
    if previous in tonics and current == sub and following in tonics:
        add('tonic_neighbor_expansion', [1], ['same_voice_3_4_3_or_5_6_5_or_held_1',
                                             'tonic_establishment_and_phrase_continuity'])
    if current == sub and following in tonics:
        add('plagal_progression', [1, 2], ['voice_leading', 'larger_tonal_context'])
        if following == tonic:
            cadences.append({'type': 'plagal', 'status': 'unverified_candidate',
                             'needs_evidence': ['cadential_closure_context', 'prior_tonic_establishment',
                                                'metric_and_melodic_arrival']})
    if previous == tonic and current in {sub+'6', vi} and following == tonic+'6':
        add('tonic_passing_expansion', [3, 7], ['actual_bass_1_6_3_descending_register_path',
                                               'same_voice_melodic_3_4_5', 'inner_voice_6_to_5_context'])
    passing_middle = {'IV6'} | ({vi} if mode == 'major' else set())
    if previous in {'V', 'V7'} and current in passing_middle and following in {'V6', 'V65'}:
        add('dominant_passing_expansion', [4, 7], ['same_bass_voice_5_6_7_ascending_steps',
                                                  'seventh_preparation_and_larger_dominant_span'])
    if previous in {'V', 'V7'} and current in {vi, sub+'6'}:
        add('tonic_substitution_or_deflection', [5, 7], ['leading_tone_and_seventh_voice_paths',
                                                        'expected_tonic_and_continuation_context'])
        cadences.append({'type': 'deceptive', 'status': 'unverified_candidate',
                         'needs_evidence': ['authentic_cadence_expectation', 'metric_and_melodic_arrival',
                                            'post_arrival_continuation_not_automatic_phrase_end']})
    return {'version': VERSION, 'basis': 'supplied_harmonic_hypotheses_not_score_detection',
            'mode': mode, 'input_symbols': [previous, current, following],
            'role_hypotheses': roles, 'cadence_hypotheses': cadences,
            'selected_role': None, 'cadence': None, 'phrase_boundary': None,
            'production_enabled': False, 'style_profile': 'common_practice_textbook',
            'policy': 'No matching pattern is not negative evidence; no automatic merge or split.'}


def source_symbol(annotation, mode):
    """Conservative DCML adapter; preserve the original record outside this view."""
    if mode not in ('major', 'minor'):
        raise ValueError('major_or_minor_required')
    r = annotation['raw_fields']
    if any(r.get(k) for k in ('form', 'changes', 'added_tones', 'relativeroot', 'pedal', 'special')):
        return None
    tonic, sub, vi = ('I', 'IV', 'vi') if mode == 'major' else ('i', 'iv', 'VI')
    quality = {'I': 'M', 'i': 'm', 'IV': 'M', 'iv': 'm', 'vi': 'm', 'VI': 'M', 'V': 'M'}
    n, figure, ct = r.get('numeral'), r.get('figbass', ''), r.get('chord_type')
    if n in (tonic, sub) and figure in ('', '6') and ct == quality[n]:
        return n+figure
    if n == vi and figure == '' and ct == quality[n]:
        return n
    if mode == 'minor' and n == 'IV' and figure == '6' and ct == 'M':
        return 'IV6'
    if n == 'V' and ((figure in ('', '6') and ct == 'M') or (figure in ('7', '65') and ct == 'Mm7')):
        return n+figure
    return None
