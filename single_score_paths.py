"""Offline competing upper-staff paths; never a selected melody label."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from single_score_melody_review import parse_source, sounding, fq

VERSION = 'single-score-paths/0.1'


def paths(events):
    notes, warnings = sounding(events)
    if not notes:
        return dict(version=VERSION, candidates=[], sounding=[], warnings=warnings)
    part = next(e['part'] for e in events if e['pitch'] is not None)
    staff = min((n['staff'] for n in notes if n['part'] == part), key=int)
    scoped = [n for n in notes if n['part'] == part and n['staff'] == staff]
    groups = defaultdict(list)
    for n in scoped:
        groups[fq(n['onset'])].append(n)
    ordered = [sorted(g, key=lambda n: n['id']) for _, g in sorted(groups.items())]
    baseline = [max(g, key=lambda n: (n['pitch'], fq(n['duration']))) for g in ordered]
    candidates = []

    def add(name, selected, policy):
        ids = [n['id'] for n in selected]
        transitions = []
        for a, b in zip(selected, selected[1:]):
            gap = fq(b['onset']) - fq(a['onset']) - fq(a['duration'])
            transitions.append(dict(leftId=a['id'], rightId=b['id'],
                interval=b['pitch'] - a['pitch'], voiceChanged=a['voice'] != b['voice'],
                gapQuarters=str(max(gap, 0)), overlapQuarters=str(max(-gap, 0))))
        candidates.append(dict(name=name, policy=policy, selected=False, eventIds=ids,
            omittedScopeIds=[n['id'] for n in scoped if n['id'] not in set(ids)],
            transitions=transitions, sameAsBaseline=ids == [n['id'] for n in baseline]))

    add('highest-onset', baseline, 'Highest written pitch at each attack onset; not melody truth.')
    for voice in sorted(set(n['voice'] for n in scoped)):
        selected = [max(v, key=lambda n: (n['pitch'], fq(n['duration'])))
                    for g in ordered if (v := [n for n in g if n['voice'] == voice])]
        add('source-voice-' + voice, selected, 'Fixed source voice, highest chord member; gaps retained.')

    # Global dynamic programming, one real note at each onset. No invented sustain,
    # no skipped attacks, and no source mutation. Scores are costs, not confidence.
    for register_weight in (0.15, 0.5):
        costs, parents = [], []
        for i, group in enumerate(ordered):
            top = max(n['pitch'] for n in group)
            row, links = [], []
            for n in group:
                register_cost = register_weight * (top - n['pitch'])
                if not i:
                    row.append(register_cost); links.append(None); continue
                options = []
                for j, previous in enumerate(ordered[i-1]):
                    leap = abs(n['pitch'] - previous['pitch']) / 12
                    switch = 2.0 if n['voice'] != previous['voice'] else 0.0
                    options.append(costs[-1][j] + leap + switch + register_cost)
                best = min(range(len(options)), key=lambda j: (options[j], j))
                row.append(options[best]); links.append(best)
            costs.append(row); parents.append(links)
        cursor = min(range(len(costs[-1])), key=lambda j: (costs[-1][j], j))
        selected = []
        for i in range(len(ordered)-1, -1, -1):
            selected.append(ordered[i][cursor]); cursor = parents[i][cursor]
        add(f'continuity-register-{register_weight}', list(reversed(selected)),
            f'DP: absolute leap/12 + voice switch 2 + distance below onset top * {register_weight}. Experimental weights, not calibrated.')
    return dict(version=VERSION, scope=dict(part=part, staff=staff), sounding=notes,
        candidates=candidates, warnings=warnings,
        limitations=['written-pitch-only', 'upper-staff-only', 'source-voice-is-not-semantic-melody',
            'no-skipping-in-continuity-path', 'no-recurrence-or-harmony-scoring', 'not-production-canonical-ir'])


def run(sources, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    summaries = []
    for index, source in enumerate(sources, 1):
        data = Path(source).read_bytes()
        digest, events, warnings = parse_source(data)
        result = paths(events)
        folder = out / str(index)
        folder.mkdir()
        (folder / 'source.musicxml').write_bytes(data)
        report = dict(source=Path(source).name, sourceHash=digest, events=events,
            parseWarnings=warnings, result=result,
            codeHashes={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ('single_score_paths.py', 'single_score_melody_review.py')})
        (folder / 'review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        baseline = set(result['candidates'][0]['eventIds']) if result['candidates'] else set()
        summary = dict(source=Path(source).name, candidates=[dict(name=c['name'], notes=len(c['eventIds']),
            differentFromBaseline=len(set(c['eventIds']) - baseline), omittedBaseline=len(baseline - set(c['eventIds'])),
            positiveGaps=sum(t['gapQuarters'] != '0' for t in c['transitions'])) for c in result['candidates']])
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False))
    (out / 'summary.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('sources', nargs='+')
    args = parser.parse_args()
    run(args.sources, args.out)
