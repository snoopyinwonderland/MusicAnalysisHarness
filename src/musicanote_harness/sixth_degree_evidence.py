"""Unit 12: conditional complete vertical shapes and lowest-pitch geometry.

Not harmonic segmentation, inferred bass strands, phrase boundaries or cadence.
No annotation labels enter assess_transition. A tonic/mode hypothesis is supplied.
"""
from .tonal_foundations import major_degree, LETTERS, NATURAL

VERSION = 'sixth-degree-evidence-0.1.0'


def assess_transition(before, after, tonic_step, tonic_alter=0, mode='major'):
    if mode not in ('major','minor'):
        raise ValueError('major_or_minor_required')
    minor = mode == 'minor'
    third, sixth = (-1,-1) if minor else (0,0)
    tonic = 'i' if minor else 'I'
    vi = 'VI' if minor else 'vi'
    sub = 'iv' if minor else 'IV'
    ii = 'iio' if minor else 'ii'
    # Coordinates relative to a spelled major scale; minor variants explicit.
    specs = {
        tonic: ({(1,0),(3,third),(5,0)},(1,0)),
        vi: ({(6,sixth),(1,0),(3,third)},(6,sixth)),
        sub: ({(4,0),(6,sixth),(1,0)},(4,0)),
        sub+'6': ({(4,0),(6,sixth),(1,0)},(6,sixth)),
        ii: ({(2,0),(4,0),(6,sixth)},(2,0)),
        ii+'6': ({(2,0),(4,0),(6,sixth)},(4,0)),
        'V': ({(5,0),(7,0),(2,0)},(5,0)),
        'V6': ({(5,0),(7,0),(2,0)},(7,0)),
        'V7': ({(5,0),(7,0),(2,0),(4,0)},(5,0)),
        'V65': ({(5,0),(7,0),(2,0),(4,0)},(7,0)),
    }
    if minor:
        specs['IV6'] = ({(4,0),(6,0),(1,0)},(6,0))
    seen = {}

    def observe(rows):
        ids, pitches, coordinates, heights = [], [], [], []
        for row in rows:
            eid, p = row['event_id'], tuple(row['pitch'])
            if not isinstance(eid,str) or not eid or eid in ids:
                raise ValueError('unique_event_id_required_per_snapshot')
            if eid in seen and seen[eid] != p:
                raise ValueError('reused_event_pitch_changed')
            step,alter,octave = p
            degree = major_degree(step,alter,tonic_step,tonic_alter)
            if not isinstance(octave,int) or isinstance(octave,bool):
                raise ValueError('integer_octave_required')
            seen[eid] = p; ids.append(eid); pitches.append(p)
            coordinates.append((degree['degree'],degree['alteration_from_major']))
            heights.append(12*(octave+1)+NATURAL[LETTERS.index(step)]+alter)
        low = min(heights,default=None)
        lows = [i for i,h in enumerate(heights) if h == low]
        bass = {coordinates[i] for i in lows}
        shapes = [name for name,(tones,root) in specs.items()
                  if set(coordinates)==tones and bass=={root}]
        return {'event_refs':ids,'spelled_pitches':[list(p) for p in pitches],
            'degree_coordinates':[list(p) for p in coordinates],
            'lowest_midi':low, 'lowest_event_refs':[ids[i] for i in lows],
            'lowest_degree_coordinates':[list(c) for c in sorted(bass)],
            'complete_surface_candidates':shapes, 'empty_snapshot':not bool(ids)}

    a,b = observe(before),observe(after)
    left,right = set(a['complete_surface_candidates']),set(b['complete_surface_candidates'])
    delta = b['lowest_midi']-a['lowest_midi'] if a['lowest_midi'] is not None and b['lowest_midi'] is not None else None
    source = bool(left & {vi,sub+'6','IV6'})
    return {'version':VERSION,
        'key_hypothesis':{'tonic_step':tonic_step,'tonic_alter':tonic_alter,'mode':mode},
        'observations':[a,b], 'observed_lowest_pitch_change_semitones':delta,
        'relations':{
            'vi_to_subdominant_or_supertonic6_surface':vi in left and bool(right & {sub,ii+'6'}),
            'vi_to_root_supertonic_surface':vi in left and ii in right,
            'sixth_degree_bass_to_root_dominant_surface':source and bool(right & {'V','V7'}),
            'sixth_degree_bass_to_inverted_dominant_surface':source and bool(right & {'V6','V65'}),
            'vi_to_iv6_same_lowest_pitch_surface':vi in left and sub+'6' in right and delta==0,
            'iv6_to_iv_surface':sub+'6' in left and sub in right,
            'minor_iv6_v_phrygian_surface':minor and 'iv6' in left and 'V' in right and delta==-1,
            'minor_raised_iv6_to_inverted_dominant_surface':minor and 'IV6' in left and bool(right & {'V6','V65'}) and delta==2,
        },
        'minor_lowered6_to_leading_tone_augmented_second_observation':bool(minor and delta==3 and
            a['lowest_degree_coordinates']==[[6,-1]] and b['lowest_degree_coordinates']==[[7,0]]),
        'same_voice_connection':'unassessed','metric_and_phrase_context':'unassessed',
        'cadence':None,'functional_verdict':None,'production_enabled':False,
        'policy':'complete vertical shapes only; lowest-pitch change is not a verified bass voice; no NCT removal'}
