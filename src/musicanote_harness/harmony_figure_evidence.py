"""Observed attack-cell recurrence and bass continuity, not harmony labels.

Same rhythm and similar contour can accompany DIFFERENT chords. These records
are review evidence only, never a merge instruction or a melody designation.
"""
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
from .formal_ir import q
from .harmony_joint import f, prepare

VERSION = 'attack-figure-evidence-0.1.0'


def observe(ir, analysis_span, boundaries=()):
    lo, hi = f(analysis_span['start']), f(analysis_span['end'])
    if lo < 0 or hi <= lo:
        raise ValueError('invalid_analysis_span')
    rows, _ = prepare(ir)
    rows = [r for r in rows if r['start'] < hi and r['end'] > lo]
    measures = sorted(ir.get('measures', []), key=lambda m: f(m['global_start_quarter']))
    voices = defaultdict(list)
    for r in rows:
        if r['voice']:
            voices[r['voice']].append(r)
    cells = []
    for voice, notes in sorted(voices.items()):
        groups = defaultdict(list)
        for r in notes:
            groups[r['start']].append(r)
        for onset in sorted(groups):
            if onset < lo:
                continue
            measure = next((m for m in reversed(measures) if f(m['global_start_quarter']) <= onset), None)
            if measure is None:
                continue
            origin = f(measure['global_start_quarter']); unit = F(4, measure['time_signature']['beat_type'])
            if (onset-origin) % unit:
                continue
            for beats in (1, 2):
                end = onset+beats*unit
                if end > hi or end > origin+f(measure['actual_duration_quarter']):
                    continue
                times = sorted(t for t in groups if onset <= t < end)
                if len(times) < 3:
                    continue
                sequence = [sorted(groups[t], key=lambda r:(r['pitch'],r['id'])) for t in times]
                melody = [g[0]['pitch'] for g in sequence]  # fixed descriptor, NOT inferred melody
                cells.append({'voice_id': voice, 'span': {'start':q(onset),'end':q(end)},
                              'beat_unit':q(unit), 'width_beats':beats,
                              'relative_attacks':[q((t-onset)/unit) for t in times],
                              'duration_profiles':[[q((r['end']-r['start'])/unit) for r in g] for g in sequence],
                              'lowest_pitch_per_attack':melody,
                              'intervals':[b-a for a,b in zip(melody,melody[1:])],
                              'event_refs':[r['id'] for g in sequence for r in g],
                              'last_sound_crosses_cell_end':any(r['end']>end for g in sequence for r in g)})
    matches = []
    for i,a in enumerate(cells):
        for b in cells[i+1:]:
            if a['voice_id']!=b['voice_id'] or a['width_beats']!=b['width_beats'] or a['beat_unit']!=b['beat_unit']:
                continue
            if f(a['span']['end'])>f(b['span']['start']):
                continue
            if a['relative_attacks']!=b['relative_attacks'] or a['duration_profiles']!=b['duration_profiles']:
                continue
            errors = [abs(x-y) for x,y in zip(a['intervals'],b['intervals'])]
            contour = all((x>0)-(x<0)==(y>0)-(y<0) for x,y in zip(a['intervals'],b['intervals']))
            compatible = contour and max(errors,default=0)<=2
            shifts = [y-x for x,y in zip(a['lowest_pitch_per_attack'],b['lowest_pitch_per_attack'])]
            split = [{'boundary':p, 'cell':side} for p in boundaries for side,c in [('earlier',a),('later',b)]
                     if f(c['span']['start'])<f(p)<f(c['span']['end'])]
            identity = [VERSION,a['event_refs'],b['event_refs'],a['width_beats']]
            matches.append({'evidence_id':'figure_'+hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20],
                            'earlier':a,'later':b,'attack_rhythm_exact':True,
                            'interval_errors_semitones':errors,'contour_matches':contour,
                            'weak_pitch_variation_compatible':compatible,
                            'constant_transposition':shifts[0] if len(set(shifts))==1 else None,
                            'split_by_selected_boundaries':split,
                            'status':'observation_not_harmonic_equivalence'})
    bass = []
    for value in boundaries:
        t = f(value)
        if not lo < t < hi:
            continue
        before = [r for r in rows if r['start']<t and r['end']>=t]
        after = [r for r in rows if r['start']<=t<r['end']]
        p = min((r['pitch'] for r in before), default=None)
        n = min((r['pitch'] for r in after), default=None)
        lows = [r for r in after if r['pitch']==n]
        bass.append({'boundary':value,'before_lowest_midi':p,'after_lowest_midi':n,
                     'motion_semitones':n-p if n is not None and p is not None else None,
                     'new_lowest_attack_refs':[r['id'] for r in lows if r['start']==t],
                     'continuing_lowest_refs':[r['id'] for r in lows if r['start']<t],
                     'status':'observed_lowest_not_structural_bass'})
    return {'version':VERSION,'analysis_span':analysis_span,'cells':cells,'rhythmic_matches':matches,
            'bass_boundaries':bass,'used_for_selection':False,
            'limitations':['Exact within-voice attack/duration matching; no voice inference',
                           'One/two denominator-beat cells are not complete motifs',
                           'Same rhythmic figure does not imply same chord or no harmonic change',
                           'Two-semitone variation threshold is an uncalibrated review heuristic']}
