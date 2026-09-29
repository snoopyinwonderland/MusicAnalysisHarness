"""Spelling-aware melodic geometry, independent of chord membership and labels.

Strict species rules are not universal validity tests. These observations do not
establish dissonance, harmonic function, suspension, or a removable note.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from .tonal_foundations import spelled_interval
from .harmony_joint import prepare, f
from .formal_ir import q

VERSION = 'counterpoint-evidence-0.1.0'


def pair_motion(lower_before, upper_before, lower_after, upper_after):
    """Two explicitly matched voices, not pitch-sorted notes at each time.

    Names describe intended ordering. Crossing does not swap voice identities.
    Findings are observations, NOT style violations or independence estimates.
    """
    lower = spelled_interval(lower_before, lower_after)
    upper = spelled_interval(upper_before, upper_after)
    before = spelled_interval(lower_before, upper_before)
    after = spelled_interval(lower_after, upper_after)
    a,b = lower['semitones'],upper['semitones']
    if a == b == 0:
        motion = 'stationary'
    elif a == 0 or b == 0:
        motion = 'oblique'
    elif a*b < 0:
        motion = 'contrary'
    elif before['generic'] == after['generic']:
        motion = 'parallel'
    else:
        motion = 'similar'
    def perfect_family(interval):
        name = interval['simple_name']
        if name == 'P5':return 'fifth'
        if name in ('P1','P8'):return 'unison_octave'
        return None
    first,last = perfect_family(before),perfect_family(after)
    return {'motion':motion,'lower_motion':lower,'upper_motion':upper,
            'vertical_before':before,'vertical_after':after,
            'crossed_before':before['semitones'] < 0,
            'crossed_after':after['semitones'] < 0,
            'lower_above_previous_upper':spelled_interval(upper_before,lower_after)['semitones'] > 0,
            'upper_below_previous_lower':spelled_interval(lower_before,upper_after)['semitones'] < 0,
            'parallel_perfect_family':last if motion=='parallel' and first==last else None,
            'similar_arrival_perfect_family':last if motion=='similar' else None,
            'style_violation':None,'voice_independence':'unassessed',
            'basis':'explicit_voice_correspondence_required'}


def melodic_geometry(pitches):
    """Three explicit same-register spelled pitches; no duration/accent exclusion."""
    if len(pitches) != 3:
        raise ValueError('three_pitches_required')
    left = spelled_interval(pitches[0], pitches[1])
    right = spelled_interval(pitches[1], pitches[2])
    steps = [abs(x['generic']) == 2 and abs(x['semitones']) in (1,2)
             for x in (left,right)]
    chromatic_steps = [abs(x['generic']) == 1 and abs(x['semitones']) == 1
                       for x in (left,right)]
    direction_product = left['semitones'] * right['semitones']
    pattern = None
    if all(steps) and pitches[0] == pitches[2]:
        pattern = 'neighbor_geometry'
    elif all(a or b for a,b in zip(steps,chromatic_steps)) and direction_product > 0:
        pattern = 'chromatic_passing_geometry' if any(chromatic_steps) else 'passing_geometry'
    return {'pattern':pattern, 'approach':left, 'departure':right,
            'nct_label':None, 'chord_membership':'unassessed',
            'preparation_and_resolution':'unassessed'}


def extract(ir):
    rows, neighbors = prepare(ir)
    sources = {s['sounding_event_id']:s for s in ir['sounding_events']}
    by_voice = defaultdict(list)
    for r in rows:
        if r['voice']:
            by_voice[r['voice']].append(r)
    # Even a single attack can coincide with a held inner chord member.
    ambiguous = {r['id'] for rs in by_voice.values() for r in rs
                 if sum(x['start'] <= r['start'] < x['end'] for x in rs) != 1}
    records=[]; skipped=Counter()
    for middle in rows:
        previous, following = neighbors.get(middle['id'], (None,None))
        if previous is None or following is None:
            skipped['missing_or_ambiguous_neighbors'] += 1
            continue
        chain=[previous,middle,following]
        if any(r['id'] in ambiguous for r in chain):
            skipped['overlapping_voice'] += 1
            continue
        if previous['end'] != middle['start'] or middle['end'] != following['start']:
            skipped['gap_or_overlap'] += 1
            continue
        pitches=[]
        try:
            for r in chain:
                p=sources[r['id']]['pitch']
                alter=f(p['alter']) if isinstance(p['alter'],dict) else Fraction(p['alter'])
                if alter.denominator != 1:
                    raise ValueError('microtone_unsupported')
                pitches.append((p['step'],int(alter),p['octave']))
            geometry=melodic_geometry(pitches)
        except (ValueError,KeyError,TypeError):
            skipped['unsupported_spelling'] += 1
            continue
        if geometry['pattern'] is None:
            skipped['other_geometry'] += 1
            continue
        records.append({'event_refs':[r['id'] for r in chain], 'voice_id':middle['voice'],
                        'span':{'start':q(previous['start']),'end':q(following['end'])},
                        'durations':[q(r['end']-r['start']) for r in chain],
                        'pitches':[list(p) for p in pitches], **geometry,
                        'status':'observed_geometry_not_confirmed_nct'})
    return {'version':VERSION,'ir_document_id':ir['ir_document_id'],
            'input_policy':'IR_only_no_harmony_annotation_phrase_input',
            'records':records,'counts':dict(Counter(r['pattern'] for r in records)),
            'skipped':dict(skipped),'production_enabled':False,
            'limitations':['Adjacent contiguous monophonic XML voice only',
                           'No latent voice or nonadjacent decorated resolution yet',
                           'No harmonic dissonance or NCT truth inferred',
                           'No accent/duration threshold; feature is not NCT probability']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--ir',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=extract(json.loads(Path(args.ir).read_text(encoding='utf-8')))
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'counts':result['counts'],'skipped':result['skipped']},ensure_ascii=False))
