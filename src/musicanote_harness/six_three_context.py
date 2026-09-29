"""Unit 19 conditional first-inversion roles; surface shape is not function."""
from fractions import Fraction
from .root_position_context import candidate, root_relation
from .diatonic_sequence import source_triad as plain_source_triad
from .dominant_area_evidence import _exact
from .formal_ir import q
from .tonal_foundations import LETTERS, NATURAL, spelled_interval

VERSION = 'six-three-context-0.1.0'


def source_triad(annotation):
    raw = annotation['raw_fields']
    if (raw.get('localkey_is_minor') == '1' and raw.get('numeral') == 'III'
            and raw.get('form') == '+' and raw.get('chord_type') == '+'
            and raw.get('figbass', '') in ('', '6')
            and not any(raw.get(k) for k in ('changes','added_tones','relativeroot','pedal','special'))):
        return ('III+', int(raw.get('figbass') == '6'))
    return plain_source_triad(annotation)


def triad(symbol, inversion, tonic, alter=0, mode='major'):
    if type(inversion) is not int or inversion not in (0, 1):
        raise ValueError('root_or_first_inversion_required')
    if symbol == 'III+' and mode == 'minor':
        c = {**candidate('III', tonic, alter, mode), 'symbol': symbol, 'quality': 'augmented'}
    else:
        c = candidate(symbol, tonic, alter, mode)
    c['inversion'] = inversion
    i = LETTERS.index(c['root_step'])
    j = (i+2*inversion) % 7
    third = 4 if c['quality'] in ('major','augmented') else 3
    bass_alter = NATURAL[i]+c['root_alter']+third*inversion-NATURAL[j]-(12 if j < i else 0)
    c['expected_bass_spelling'] = [LETTERS[j], bass_alter]
    return c


def propose(symbols, inversions, tonic, alter=0, mode='major'):
    if len(symbols) != 3 or len(inversions) != 3:
        raise ValueError('three_supplied_triads_required')
    inversions = list(inversions)
    cs = [triad(s, i, tonic, alter, mode) for s, i in zip(symbols, inversions)]
    relations = [root_relation(a,b) for a,b in zip(cs,cs[1:])]
    roles = []
    def add(role, indices, sections, needs, **extra):
        roles.append({'role': role, 'indices': indices, 'sections': sections, 'status': 'candidate',
                      'needs_evidence': ['actual_score_support','metric_and_formal_context', *needs], **extra})
    steps = [r['diatonic_steps_up_mod7'] for r in relations]
    if inversions == [1,1,1] and steps[0] == steps[1] and steps[0] in (1,6,2,5):
        add('linear_first_inversion_chain', [0,1,2], [1,2,3,4,7],
            ['explicit_voice_correspondence','outer_sixths_and_inner_motion','goal_and_articulation'],
            nominal_root_motion={1:'step_up',6:'step_down',2:'third_up',5:'third_down'}[steps[0]])
    bass = [{'root_step':c['expected_bass_spelling'][0], 'root_alter':c['expected_bass_spelling'][1]} for c in cs]
    br = [root_relation(a,b) for a,b in zip(bass,bass[1:])]
    bs = [r['diatonic_steps_up_mod7'] for r in br]
    is_step = all((r['diatonic_steps_up_mod7'], r['semitones_up_mod12']) in
                  ((1,1),(1,2),(6,10),(6,11)) for r in br)
    same_outer = all(cs[0][k] == cs[2][k] for k in ('root_step','root_alter','quality','inversion'))
    if inversions[1] == 1 and is_step:
        if same_outer and bs[0] != bs[1]:
            add('neighboring_first_inversion', [0,1,2], [5,9], ['same_bass_voice_out_and_return','upper_voice_support'])
        if bs[0] == bs[1]:
            add('passing_first_inversion', [0,1,2], [6,9], ['same_register_stepwise_bass','nonindependent_middle_role','upper_voice_support'])
    for i,c in enumerate(cs):
        target = None
        if c['inversion'] == 1:
            if c['symbol'] == ('vi' if mode == 'major' else 'VI'):
                target = 'I' if mode == 'major' else 'i'
            elif (mode == 'major' and c['symbol'] == 'iii') or (mode == 'minor' and c['symbol'] == 'III+'):
                target = 'V'
        if target:
            add('sixth_decorating_or_replacing_fifth', [i], [8,9],
                ['governing_harmony_established','same_voice_fifth_sixth_path_or_contextual_substitution',
                 'retain_independent_first_inversion_alternative'],
                governing_harmony_candidate=target, original_triad_candidate=c['symbol'])
    return {'version': VERSION, 'basis':'supplied_hypotheses_not_blind_detection',
            'key_hypothesis':{'tonic_step':tonic,'tonic_alter':alter,'mode':mode},
            'candidates':cs,'root_relations':relations,'nominal_bass_relations':br,'role_candidates':roles,
            'selected_role':None,'parallel_voice_motion_verified':False,'cadence':None,
            'phrase_boundary':None,'merge_recommended':None,'production_enabled':False,
            'limitations':['chord-derived bass spellings do not establish register or an actual voice path',
                           'consecutive first inversions do not prove parallel voices or transition function',
                           'three-chord local window is not a complete sequence detector',
                           'surface vi6/iii6/III+6 retained; no automatic tonic/dominant relabeling',
                           'voice exchanges, corrective insertions and applied chords not reconstructed']}


def observe_surface(inventory, chord):
    """Time-weighted lowest sounding pitches, NOT an extracted bass voice.

    Full source slice event IDs retained. Sixth incidence is geometric, not a
    parallel-motion or harmony verdict; ties do not become new attacks.
    """
    a,b = (_exact(inventory['span'][k]) for k in ('start','end'))
    if a < 0 or b <= a:
        raise ValueError('positive_span_required')
    cursor, matched, sixths, empty = a, Fraction(), Fraction(), Fraction()
    cells = []
    for cell in inventory['slices']:
        x,y = (_exact(cell['span'][k]) for k in ('start','end'))
        if x != cursor or y <= x or y > b:
            raise ValueError('nonpartitioned_inventory')
        cursor = y
        events = cell['events']
        for event in events:
            spelled_interval(event['pitch'],event['pitch'])
        def height(e):
            s,alt,octave = e['pitch']
            return 12*(octave+1)+NATURAL[LETTERS.index(s)]+alt
        lows = [e for e in events if height(e) == min(map(height,events))] if events else []
        highs = [e for e in events if height(e) == max(map(height,events))] if events else []
        low_spellings = {tuple(e['pitch'][:2]) for e in lows}
        match = bool(lows) and low_spellings == {tuple(chord['expected_bass_spelling'])}
        intervals = [spelled_interval(lo['pitch'],hi['pitch']) for lo in lows for hi in highs]
        sixth = bool(intervals) and all(iv['generic'] > 0 and (iv['generic']-1)%7 == 5 for iv in intervals)
        matched += (y-x)*match
        sixths += (y-x)*sixth
        empty += (y-x)*(not events)
        cells.append({'span':cell['span'],'lowest_event_ids':[e['event_id'] for e in lows],
                      'highest_event_ids':[e['event_id'] for e in highs],
                      'lowest_matches_supplied_bass':match,'outer_intervals':intervals,
                      'all_extrema_pairs_sixth_class':sixth})
    if cursor != b:
        raise ValueError('incomplete_inventory')
    return {'span':inventory['span'],'cells':cells,'expected_bass_spelling':chord['expected_bass_spelling'],
            'matching_lowest_duration_ratio':q(matched/(b-a)), 'sixth_class_extrema_duration_ratio':q(sixths/(b-a)),
            'silence_duration_ratio':q(empty/(b-a)), 'voice_path_verified':False,
            'parallel_motion':None,'selected_function':None}
