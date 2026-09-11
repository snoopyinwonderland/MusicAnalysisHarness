"""Lyric-independent harmonic hypotheses over research feature frames.

Scores are template fit values, NOT calibrated probabilities or cadence labels.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import json
from pathlib import Path


def fraction(value):
    return Fraction(value['numerator'], value['denominator'])


def analyze(frames):
    # Collapse duplicate vertical observations from simultaneous voices.
    points = {}
    for frame in frames:
        points.setdefault(fraction(frame['time']), frame)
    ordered = sorted(points.items())
    result = []
    previous = {}
    for index, (time, frame) in enumerate(ordered):
        pcs = {Fraction(p) for p in frame['features']['active_pitch_classes']}
        if not pcs or any(p.denominator != 1 for p in pcs):
            continue
        pcs = {int(p) for p in pcs}
        # Fixed quarter window is explicit and independent of lyric locations.
        histogram = Counter()
        for t, other in ordered[max(0, index-64):index+65]:
            if abs(t-time) <= 16:
                histogram.update(int(Fraction(p)) for p in other['features']['active_pitch_classes'] if Fraction(p).denominator == 1)
        keys = []
        for tonic in range(12):
            for mode, scale in [('major', [0,2,4,5,7,9,11]), ('minor', [0,2,3,5,7,8,10,11])]:
                inside = sum(count for p, count in histogram.items() if (p-tonic)%12 in scale)
                # Minor includes raised leading tone; compensate for extra scale class.
                fit = inside / max(1, sum(histogram.values())) - len(scale)/12
                keys.append({'tonic_pc': tonic, 'mode': mode, 'scale_fit': round(fit, 6)})
        keys.sort(key=lambda k: (-k['scale_fit'], k['tonic_pc'], k['mode']))
        hypotheses = []
        for key in keys[:4]:
            tonic = key['tonic_pc']
            identity = (tonic, key['mode'])
            tonic_set = {(tonic+d)%12 for d in (0,4 if key['mode']=='major' else 3,7)}
            dominant_set = {(tonic+d)%12 for d in (7,11,2)}
            labels = []
            for label, template in [('I' if key['mode']=='major' else 'i', tonic_set), ('V', dominant_set), ('V7', dominant_set | {(tonic+5)%12})]:
                overlap = len(pcs & template)
                fit = overlap / len(pcs | template)
                labels.append({'label': label, 'pitch_set_fit': round(fit, 6), 'complete_template': template <= pcs})
            labels.sort(key=lambda x: -x['pitch_set_fit'])
            chosen = labels[0]
            before = previous.get(identity)
            transition = bool(before and time-before['time'] <= 4 and before['label'] in ('V','V7') and chosen['label'] in ('I','i') and before['complete'] and chosen['complete_template'])
            hypotheses.append({'key': key, 'chord_candidates': labels, 'dominant_to_tonic_candidate': transition, 'previous_time': str(before['time']) if before else None})
            previous[identity] = {'time':time, 'label':chosen['label'], 'complete':chosen['complete_template']}
        result.append({'analysis_id':f'harm_{index}', 'time':frame['time'], 'evidence_frame_id':frame['frame_id'], 'hypotheses':hypotheses, 'selected_hypothesis':None, 'confidence':None, 'status':'uncalibrated_template_candidates', 'engine':{'name':'pitch-set-local-scale-baseline','version':'0.1.0','window_quarters':16,'max_neighbor_onsets':64}})
    return result


def run(source, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    totals = Counter()
    files = []
    for path in sorted(Path(source).glob('*.json')):
        package = json.loads(path.read_text(encoding='utf-8'))
        if 'musical_feature_frames' not in package:
            continue
        frames = package['musical_feature_frames']
        records = analyze(frames)
        by_time = {fraction(r['time']):r for r in records}
        cases = []
        for frame in frames:
            record = by_time.get(fraction(frame['time']))
            if not record:
                continue
            gap = fraction(frame['features']['voice_gap_before']) > 0
            transition = any(h['dominant_to_tonic_candidate'] for h in record['hypotheses'])
            pattern = ('gap' if gap else 'continuous') + ('_with_V_I_candidate' if transition else '_without_V_I_candidate')
            totals[pattern] += 1
            cases.append({'frame_id':frame['frame_id'],'analysis_ref':record['analysis_id'],'pattern':pattern,'status':'comparison_case_not_boundary_label'})
        # Only frames are passed to analyze; weak lyric fields cannot influence it.
        out = {'source_sha256':package['source_sha256'],'analysis_records':records,'musical_comparison_cases':cases,'training_eligible':False}
        (destination/path.name).write_text(json.dumps(out,indent=2),encoding='utf-8')
        files.append({'file':path.name,'harmonic_points':len(records),'cases':len(cases)})
    report = {'files':files,'patterns':dict(totals),'confidence_calibrated':False,'limitations':['Research frame timing and tie/melisma alignment not yet certified','Scale fit is not a validated local-key detector','Chord templates omit most harmonic vocabulary; alternatives may all be wrong','V-I candidates are not cadences or phrase labels','Counts include simultaneous voice frames; not independent phrases']}
    (destination/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    print(json.dumps(run(args.source,args.destination)['patterns'],indent=2))
