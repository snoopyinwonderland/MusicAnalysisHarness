"""Unit 17 supplied root-position hypotheses, geometry and unselected roles."""
from .tonal_foundations import LETTERS, NATURAL, SCALES, major_degree

VERSION = 'root-position-context-0.1.0'
TABLE = {
    'major': {'I': (1,0,'major'), 'ii': (2,0,'minor'), 'iii': (3,0,'minor'),
              'IV': (4,0,'major'), 'V': (5,0,'major'), 'vi': (6,0,'minor'), 'viio': (7,0,'diminished')},
    'minor': {'i': (1,0,'minor'), 'iio': (2,0,'diminished'), 'III': (3,0,'major'),
              'iv': (4,0,'minor'), 'v': (5,0,'minor'), 'V': (5,0,'major'),
              'VI': (6,0,'major'), 'VII': (7,0,'major'), '#viio': (7,1,'diminished')},
}


def candidate(symbol, tonic, alter=0, mode='major'):
    if mode not in TABLE:
        raise ValueError('major_or_minor_required')
    if symbol not in TABLE[mode]:
        raise ValueError('unsupported_root_position_triad')
    major_degree(tonic, alter, tonic, alter)
    degree, change, quality = TABLE[mode][symbol]
    i = LETTERS.index(tonic)
    j = (i+degree-1) % 7
    scale = SCALES['major' if mode == 'major' else 'natural_minor']
    ra = NATURAL[i]+alter+scale[degree-1]+change-NATURAL[j]-(12 if j < i else 0)
    return {'symbol': symbol, 'root_step': LETTERS[j], 'root_alter': ra,
            'quality': quality, 'inversion': 0, 'degree': degree,
            'basis': 'supplied_harmonic_hypothesis'}


def root_relation(left, right):
    """Octave-free root relation; not the direction of the actual bass voice."""
    for c in (left, right):
        major_degree(c['root_step'], c['root_alter'], 'C')
    a, b = (LETTERS.index(c['root_step']) for c in (left,right))
    steps = (b-a) % 7
    semitones = (NATURAL[b]+right['root_alter']-NATURAL[a]-left['root_alter']) % 12
    return {'diatonic_steps_up_mod7': steps, 'semitones_up_mod12': semitones,
            'family': {3:'descending_fifth_or_ascending_fourth',4:'ascending_fifth_or_descending_fourth',
                       5:'descending_third_or_ascending_sixth',2:'ascending_third_or_descending_sixth'}.get(steps, 'other'),
            'tritone': semitones == 6, 'actual_bass_direction': None}


def propose(symbols, tonic, alter=0, mode='major'):
    if len(symbols) != 3:
        raise ValueError('three_supplied_hypotheses_required')
    cs = [candidate(s,tonic,alter,mode) for s in symbols]
    relations = [root_relation(a,b) for a,b in zip(cs,cs[1:])]
    roles = []
    def add(role, sections, needs):
        roles.append({'role': role, 'status':'candidate', 'unit':17, 'sections':sections,
                      'needs_evidence':['score_support_for_all_harmonic_hypotheses', *needs]})
    if relations[0]['family'] == relations[1]['family'] != 'other':
        add('root_chain_'+relations[0]['family'], [1,2,3],
            ['actual_bass_register_path','metric_and_melodic_hierarchy','larger_progression_and_arrival'])
    returns = all(cs[0][k] == cs[2][k] for k in ('root_step','root_alter','quality'))
    if returns:
        distance = relations[0]['diatonic_steps_up_mod7']
        if distance == 4 and relations[0]['semitones_up_mod12'] == 7:
            add('upper_fifth_expansion', [4], ['governing_harmony_established','bass_chordal_motion','no_intervening_cadential_closure'])
        if distance == 2 and relations[0]['semitones_up_mod12'] in (3,4):
            add('upper_third_expansion', [5], ['governing_harmony_established','voice_leading_and_style','no_intervening_cadential_closure'])
        if distance in (3,5):
            add('upper_voice_neighbor_support', [9], ['same_voice_neighbor_return','style_and_duration','no_independent_cadence'])
        if distance in (1,6):
            add('bass_neighbor_support', [10], ['actual_bass_step_out_and_return','register_continuity','larger_harmonic_context'])
    tonic_symbol, sub, vi = ('I','IV','vi') if mode == 'major' else ('i','iv','VI')
    if symbols == [sub,tonic_symbol,'V']:
        add('apparent_tonic_supporting_passing_third', [7], ['same_upper_voice_4_3_2','relative_metric_weakness','continuation_toward_dominant'])
    if symbols == [tonic_symbol,'v','VI'] and mode == 'minor':
        add('minor_v_supporting_descending_natural_seventh', [11,12,13], ['same_voice_8_natural7_6','no_automatic_deceptive_cadence','motivic_context'])
    return {'version':VERSION, 'basis':'supplied_hypotheses_not_blind_detection',
            'key_hypothesis':{'tonic_step':tonic,'tonic_alter':alter,'mode':mode},
            'candidates':cs, 'root_relations':relations, 'role_hypotheses':roles,
            'selected_role':None, 'cadence':None, 'phrase_boundary':None, 'merge_recommended':None,
            'sequence_confirmed':None, 'production_enabled':False,
            'limitations':['root-position triads only; no skipped or collapsed intervening chords',
                           'root relation is not actual bass direction or voice-leading verification',
                           'pattern match cannot distinguish a prolongation from multiple phrases',
                           'minor v is retained, not forced to major V or treated as an error']}


def source_symbol(annotation):
    r = annotation['raw_fields']
    if r.get('localkey_is_minor') not in ('0','1'):
        return None
    mode = 'minor' if r['localkey_is_minor']=='1' else 'major'
    if any(r.get(k) for k in ('figbass','changes','added_tones','relativeroot','pedal','special')):
        return None
    symbol = r.get('numeral','')+r.get('form','')
    item = TABLE[mode].get(symbol)
    if item and r.get('chord_type') == {'major':'M','minor':'m','diminished':'o'}[item[2]]:
        return symbol
    return None
