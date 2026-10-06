"""Review-only skip paths supported by within-score alignment and intact beams."""
import argparse
import hashlib
import json
from pathlib import Path
from single_score_melody_review import fq
from single_score_recurrence import assess

VERSION = 'single-score-skip-paths/0.1'


def beam_unit(run):
    """Require one complete primary beam, not an arbitrary part of a figure."""
    def primary(n):
        return [b['value'] for b in n['beams'] if b.get('number', '1') == '1']
    return len(run) >= 2 and primary(run[0]) == ['begin'] and primary(run[-1]) == ['end'] and all(primary(n) == ['continue'] for n in run[1:-1])


def propose(notes, discovery):
    found = {}
    for pi, pair in enumerate(discovery['pairs']):
        for side in (0, 1):
            matches = sorted((m[side], m[1-side]) for m in pair['matches'])
            for (left, ol), (right, ore) in zip(matches, matches[1:]):
                if not 2 <= right-left-1 <= 16 or ore-ol != 1:
                    continue
                key = (left+1, right)
                if key not in found:
                    mid = notes[left+1:right]
                    run = notes[left:right+1]
                    durations = [fq(n['duration']) for n in mid]
                    blockers = []
                    if not beam_unit(mid): blockers.append('not-complete-primary-beam')
                    if min(durations) <= 0 or max(durations) > 2*min(durations): blockers.append('uneven-or-zero-duration')
                    if len({(n['part'], n['staff'], n['voice']) for n in run}) != 1: blockers.append('source-stream-change')
                    if any(n['ties'] or n.get('unresolvedTie') or len(n['sourceIds']) > 1 for n in mid): blockers.append('tie-protected')
                    if any(fq(a['onset'])+fq(a['duration']) != fq(b['onset']) for a,b in zip(run, run[1:])): blockers.append('gap-or-overlap')
                    found[key] = dict(id=f'skip-{len(found)+1}', start=left+1, endExclusive=right,
                        evidence=['same-score-matched-surrounding-anchors', 'counterpart-adjacent-attacks'],
                        blockers=blockers, supportPairs=[], selected=False)
                found[key]['supportPairs'].append(pi)
    relations = list(found.values())
    checks = assess(relations, discovery)
    for relation, check in zip(relations, checks):
        relation['recurrenceAssessment'] = check
        if check['state'] == 'recurring-material-protect': relation['blockers'].append('retained-in-other-recurrence')
        relation['status'] = 'blocked' if relation['blockers'] else 'review-only'
        a, z = relation['start'], relation['endExclusive']
        relation['contextIds'] = [n['id'] for n in notes[max(0,a-2):z+2]]
        relation['omittedIds'] = [n['id'] for n in notes[a:z]]
        # Each alternative skips only this one unit, never a greedy union.
        relation['alternativeEventIds'] = None if relation['blockers'] else [n['id'] for i,n in enumerate(notes) if not a<=i<z]
    return dict(version=VERSION, baselineEventIds=[n['id'] for n in notes], proposals=relations,
        selected=False, limitations=['not-accompaniment-classification', 'beam-may-be-melodic',
            'rhythm-ratio-is-not-meter-strength', 'cached-partial-recurrence', 'no-harmony-validation'])


def run(inputs, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    summaries = []
    for i, source in enumerate(inputs, 1):
        path = Path(source)
        data = path.read_bytes()
        report = json.loads(data)
        xml = path.with_name('source.musicxml').read_bytes()
        if hashlib.sha256(xml).hexdigest() != report['sourceHash']: raise ValueError('Source hash mismatch')
        base = report['baseline']
        byid = {n['id']: n for n in base['sounding']}
        result = propose([byid[id] for id in base['baseline']], report['recurrence'])
        folder = out / str(i)
        folder.mkdir()
        (folder/'source.musicxml').write_bytes(xml)
        (folder/'input-review.json').write_bytes(data)
        result.update(source=report['source'], sourceHash=report['sourceHash'],
            inputHash=hashlib.sha256(data).hexdigest(),
            codeHashes={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('single_score_skip_paths.py','single_score_recurrence.py','single_score_melody_review.py')})
        (folder/'review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        summary = dict(source=report['source'], runs=len(result['proposals']),
            reviewOnly=sum(p['status']=='review-only' for p in result['proposals']),
            blocked=sum(p['status']=='blocked' for p in result['proposals']),
            blockers={b:sum(b in p['blockers'] for p in result['proposals']) for b in sorted({b for p in result['proposals'] for b in p['blockers']})})
        summaries.append(summary)
        print(json.dumps(summary,ensure_ascii=False))
    (out/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('inputs', nargs='+')
    args=parser.parse_args()
    run(args.inputs,args.out)
