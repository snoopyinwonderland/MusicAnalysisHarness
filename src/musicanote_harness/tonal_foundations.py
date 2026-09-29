"""Conditional major-scale coordinates, NOT key or harmonic-function inference."""
LETTERS = "CDEFGAB"
NATURAL = (0, 2, 4, 5, 7, 9, 11)
MAJOR = (0, 2, 4, 5, 7, 9, 11)

SCALES = {
    "major": MAJOR, "natural_minor": (0,2,3,5,7,8,10),
    "harmonic_minor": (0,2,3,5,7,8,11), "melodic_minor_ascending": (0,2,3,5,7,9,11),
    "dorian": (0,2,3,5,7,9,10), "phrygian": (0,1,3,5,7,8,10),
    "lydian": (0,2,4,6,7,9,11), "mixolydian": (0,2,4,5,7,9,10),
    "locrian": (0,1,3,5,6,8,10),
}


def major_degree(step, alter, tonic_step, tonic_alter=0):
    """Preserve spelling: C# and Db have different degree coordinates in C.

    All results are conditional on a supplied tonic/major-mode hypothesis.
    Semitone alterations are required; unknown spelling is not invented for MIDI.
    """
    if step not in tuple(LETTERS) or tonic_step not in tuple(LETTERS):
        raise ValueError("explicit_pitch_and_tonic_spelling_required")
    if any(isinstance(a, bool) or not isinstance(a, int) for a in (alter, tonic_alter)):
        raise ValueError("integer_semitone_alter_required")
    ti, pi = LETTERS.index(tonic_step), LETTERS.index(step)
    degree = (pi-ti) % 7
    natural_distance = NATURAL[pi] - NATURAL[ti] + (12 if pi < ti else 0)
    alteration = natural_distance + alter - tonic_alter - MAJOR[degree]
    return {"degree": degree+1, "alteration_from_major": alteration,
            "diatonic_to_candidate": alteration == 0,
            "candidate": {"tonic_step": tonic_step, "tonic_alter": tonic_alter, "mode": "major"},
            "basis": "conditional_scale_coordinate", "key_inferred": False}


def scale_degree(step, alter, tonic_step, tonic_alter=0, form="major"):
    """A specified minor form is not a different inferred key or automatic direction rule."""
    if form not in SCALES:
        raise ValueError("explicit_supported_scale_form_required")
    result = major_degree(step, alter, tonic_step, tonic_alter)
    index = result['degree'] - 1
    alteration = result.pop('alteration_from_major') + MAJOR[index] - SCALES[form][index]
    result['alteration_from_scale'] = alteration
    result['diatonic_to_candidate'] = alteration == 0
    result['candidate']['mode'] = form
    return result


def spelled_seventh_shapes(pitches):
    """Complete 1/3/5/7 spelling shapes, not proof of an independent harmony.

    The caller distinguishes a vertical slice from a span union. Incomplete or
    decorated sets abstain; major-minor quality does not establish V function.
    """
    if not pitches:
        return []
    for step, alter, octave in pitches:
        major_degree(step, alter, 'C')
        if isinstance(octave, bool) or not isinstance(octave, int):
            raise ValueError('integer_octave_required')
    unique = {(s, a) for s, a, _ in pitches}
    if len(unique) != 4:
        return []
    def height(p):
        return 12*(p[2]+1)+NATURAL[LETTERS.index(p[0])]+p[1]
    low = min(map(height, pitches))
    basses = {(s,a) for s,a,o in pitches if height((s,a,o)) == low}
    templates = {
        (4,7,11): 'major_seventh', (3,7,10): 'minor_seventh',
        (4,7,10): 'major_minor_seventh', (3,6,9): 'diminished_seventh',
        (3,6,10): 'half_diminished_seventh', (4,8,11): 'augmented_major_seventh',
        (3,7,11): 'minor_major_seventh',
    }
    results = []
    for root in sorted(unique):
        ri = LETTERS.index(root[0])
        factors = {(LETTERS.index(s)-ri)%7:(s,a) for s,a in unique}
        if set(factors) != {0,2,4,6}:
            continue
        rpc = NATURAL[ri]+root[1]
        distances = tuple((NATURAL[LETTERS.index(factors[i][0])]+factors[i][1]-rpc)%12
                          for i in (2,4,6))
        quality = templates.get(distances)
        if quality is None:
            continue
        inversions = [i//2 for i,p in factors.items() if p in basses]
        inversion = inversions[0] if len(inversions)==1 else None
        results.append({'root_step':root[0], 'root_alter':root[1], 'quality':quality,
                        'inversion':inversion,
                        'figured_bass':('7','65','43','42')[inversion] if inversion is not None else None,
                        'seventh_spelling':{'step':factors[6][0], 'alter':factors[6][1]},
                        'harmonic_function':'unassessed', 'independent_harmony':'unassessed',
                        'basis':'complete_spelled_shape'})
    return results


def spelled_interval(first, second):
    """(step, integer alter, octave) inputs, preserving compound and directed interval."""
    from music21 import pitch, interval
    pitches = []
    for step, alter, octave in (first, second):
        major_degree(step, alter, 'C')  # validate spelling/12-TET domain
        if isinstance(octave, bool) or not isinstance(octave, int):
            raise ValueError('integer_octave_required')
        p = pitch.Pitch()
        p.step, p.octave, p.accidental = step, octave, pitch.Accidental(alter)
        pitches.append(p)
    value = interval.Interval(*pitches)
    return {'name': value.name, 'simple_name': value.simpleName,
            'directed_name': value.directedName, 'semitones': value.chromatic.semitones,
            'generic': value.generic.directed, 'consonance': 'context_not_assessed'}


def metric_coordinate(onset, duration, beats, beat_type, grouping=None):
    """Exact notated coordinates; grouping is explicit or a documented convention.

    onset is measured from the notated bar origin (caller handles pickup alignment).
    No perceived accent, phrase boundary, or NCT label follows from this coordinate.
    """
    from fractions import Fraction
    if any(isinstance(x, bool) or not isinstance(x,int) or x <= 0 for x in (beats,beat_type)):
        raise ValueError('positive_integer_meter_required')
    if isinstance(onset, float) or isinstance(duration, float):
        raise ValueError('rational_time_required')
    onset, duration = Fraction(onset), Fraction(duration)
    unit = Fraction(4,beat_type)
    if not 0 <= onset < beats*unit or duration < 0:
        raise ValueError('invalid_onset_or_duration')
    if grouping is None:
        if beats in (6,9,12):
            grouping, policy = [3]*(beats//3), 'conventional_compound_not_perceived_pulse'
        elif beats in (2,3,4):
            grouping, policy = [1]*beats, 'conventional_simple'
        else:
            return {'status':'grouping_required','beat_type':beat_type,'beats':beats}
    else:
        policy = 'explicit_grouping'
    if any(isinstance(x,bool) or not isinstance(x,int) or x<=0 for x in grouping) or sum(grouping)!=beats:
        raise ValueError('invalid_grouping')
    cursor = Fraction(0)
    for i, group in enumerate(grouping):
        size = group*unit
        if cursor <= onset < cursor+size:
            return {'status':'computed','group_index':i,'position_in_group':str((onset-cursor)/size),
                    'duration_in_groups':str(duration/size),'on_group_start':onset==cursor,
                    'group_duration_quarters':str(size),'policy':policy,'accent_inferred':False}
        cursor += size


def spelled_triad_shapes(pitches):
    """Complete triadic spelling shapes only, not a harmonic segmentation engine.

    Input may describe a simultaneity or a chosen span; the caller must distinguish
    them. Extra/missing factors abstain rather than being silently removed as NCTs.
    """
    if not pitches:
        return []
    for step, alter, octave in pitches:
        major_degree(step,alter,'C')
        if not isinstance(octave,int) or isinstance(octave,bool):
            raise ValueError('integer_octave_required')
    unique = {(p[0],p[1]) for p in pitches}
    if len(unique) != 3:
        return []
    def midi(p):
        return 12*(p[2]+1)+NATURAL[LETTERS.index(p[0])]+p[1]
    lowest = min(midi(p) for p in pitches)
    basses = {(p[0],p[1]) for p in pitches if midi(p)==lowest}
    templates = {(4,7):'major',(3,7):'minor',(3,6):'diminished',(4,8):'augmented'}
    result = []
    for root in sorted(unique):
        ri = LETTERS.index(root[0])
        factors = {(LETTERS.index(step)-ri)%7:(step,alter) for step,alter in unique}
        if set(factors) != {0,2,4}:
            continue
        rpc = (NATURAL[ri]+root[1])%12
        distances = tuple((NATURAL[LETTERS.index(factors[i][0])]+factors[i][1]-rpc)%12 for i in (2,4))
        quality = templates.get(distances)
        if quality:
            inversions = [{0:0,2:1,4:2}[i] for i,p in factors.items() if p in basses]
            result.append({'root_step':root[0],'root_alter':root[1],'quality':quality,
                           'inversion':inversions[0] if len(inversions)==1 else None,
                           'harmonic_function':'unassessed','basis':'complete_spelled_shape'})
    return result
