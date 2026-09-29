"""Unit 10: conditional snapshot evidence, not inferred harmony or cadence.

Caller supplies aligned vertical snapshots and candidate key/chord labels.
Sustained events may occur in both snapshots; new attacks are not required.
Strict complete pitch sets intentionally abstain on ornamented/incomplete chords.
"""
from .tonal_foundations import scale_degree, LETTERS, NATURAL

VERSION = 'predominant-evidence-0.1.0'


def assess_transition(before, after, labels, tonic_step, tonic_alter=0, mode='major'):
    """Each snapshot contains {event_id, pitch:(step,alter,octave)} rows.

    Caller owns time/voice alignment. Reused event IDs must retain exact pitch.
    No duration, metric strength, suspension, resolution or gold truth inferred.
    """
    if mode not in ('major', 'minor'):
        raise ValueError('major_or_minor_required')
    if len(labels) != 2:
        raise ValueError('two_candidates_required')
    iv, ii = ('IV', 'ii') if mode == 'major' else ('iv', 'iio')
    specs = {iv:({4,6,1},4), ii:({2,4,6},2), ii+'6':({2,4,6},4),
             'V':({5,7,2},5), 'V6':({5,7,2},7),
             'V7':({5,7,2,4},5), 'V65':({5,7,2,4},7),
             'V43':({5,7,2,4},2), 'V42':({5,7,2,4},4)}
    if any(label not in specs for label in labels):
        raise ValueError('unsupported_candidate')
    seen = {}
    observations = []
    for rows, label in zip((before, after), labels):
        if not rows:
            raise ValueError('nonempty_snapshot_required')
        ids, pitches, degrees, valid = [], [], [], True
        for row in rows:
            eid, pitch = row['event_id'], tuple(row['pitch'])
            if not isinstance(eid, str) or not eid or eid in ids:
                raise ValueError('unique_nonempty_event_ids_required_per_snapshot')
            step, alter, octave = pitch
            coordinate = scale_degree(step, alter, tonic_step, tonic_alter,
                                      'major' if mode == 'major' else 'harmonic_minor')
            if isinstance(octave, bool) or not isinstance(octave, int):
                raise ValueError('integer_octave_required')
            if eid in seen and seen[eid] != pitch:
                raise ValueError('reused_event_pitch_changed')
            seen[eid] = pitch
            ids.append(eid)
            pitches.append(pitch)
            degrees.append(coordinate['degree'])
            valid = valid and coordinate['diatonic_to_candidate']
        heights = [12*(p[2]+1)+NATURAL[LETTERS.index(p[0])]+p[1] for p in pitches]
        lows = [i for i,h in enumerate(heights) if h == min(heights)]
        tones, bass_degree = specs[label]
        observations.append({'candidate':label, 'event_refs':ids,
            'complete_spelled_support':bool(valid and set(degrees)==tones
                                            and all(degrees[i]==bass_degree for i in lows)),
            'lowest_pitches':[list(pitches[i]) for i in lows],
            'degree4_event_refs':[ids[i] for i,d in enumerate(degrees) if d==4]})
    a,b = observations
    supported = a['complete_spelled_support'] and b['complete_spelled_support']
    same_bass = {tuple(p) for p in a['lowest_pitches']} == {tuple(p) for p in b['lowest_pitches']}
    is_pred = labels[0] in (iv, ii, ii+'6')
    return {'version':VERSION,
        'key_hypothesis':{'tonic_step':tonic_step,'tonic_alter':tonic_alter,'mode':mode},
        'observations':observations,
        'predominant_to_dominant_candidate':bool(supported and is_pred and labels[1].startswith('V')),
        'held_bass_harmony_change_candidate':bool(supported and same_bass and labels[0]!=labels[1]),
        'iv_to_ii6_five_six_candidate':bool(supported and same_bass and tuple(labels)==(iv,ii+'6')),
        'retained_degree4_event_refs':sorted(set(a['degree4_event_refs']) & set(b['degree4_event_refs'])) if supported else [],
        'same_voice_preparation':'unassessed', 'cadence':None, 'nct_label':None,
        'harmony_verified':False, 'production_enabled':False}
