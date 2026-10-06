"""Six size-stratified, predeclared development songs; no tuning or retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from musicanote_harness.harmony_test_a import write, digest, MODEL, MODEL_SHA, validated_spans, fraction, score_submissions
from musicanote_harness.harmony_whole_score import VERSION, CONFIG

OLD = ROOT/'output/harmony-frozen-test-a-2026-10-06-r1'
GOLD = Path('K:/Music Composition/docs/handoff/harmony_eval/harmony_benchmark_gold.json')


def one(entry, arm, output):
    t = perf_counter()
    path = output/'jobs'/f'{entry["index"]:03d}-{arm}.json'
    command = [sys.executable, '-B', '-m',
        'musicanote_harness.harmony_whole_score' if arm == 'engine' else 'musicanote_harness.harmony_test_a',
        '--worker', entry['source_file'], '--output', str(path)]
    if arm == 'baseline':
        command += ['--arm', 'baseline']
    env = dict(os.environ, PYTHONPATH=str(ROOT/'src'), PYTHONDONTWRITEBYTECODE='1')
    try:
        p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=60)
        r = json.loads(path.read_text(encoding='utf-8')) if p.returncode == 0 and path.exists() else dict(
            status='process_error', error=p.stderr.decode('utf-8', errors='replace')[-2000:], spans=[])
    except subprocess.TimeoutExpired:
        r = dict(status='whole_song_timeout', spans=[])
    r.update(title=entry['title'], index=entry['index'], arm=arm, wall_seconds=perf_counter()-t)
    write(path, r)
    return r


def run(output):
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    if digest(MODEL) != MODEL_SHA:
        raise ValueError('model_changed')
    old = json.loads((OLD/'statuses.json').read_text(encoding='utf-8'))['engine']
    pool = [r for r in old if r['status'] == 'native_whole_scope_abstention']
    selected = []
    for target in (90, 200, 300, 600, 1000, 1600):
        r = min(pool, key=lambda r: (abs(r['native_cells']-target), r['index']))
        selected.append({k: r[k] for k in ('index', 'title', 'source_file', 'native_cells')})
        pool.remove(r)
    code = [Path(__file__), ROOT/'docs/harmony/WHOLE_SCORE_PATH_PILOT_PLAN.md', ROOT/'tests/test_harmony_whole_score.py']
    code += sorted((ROOT/'src/musicanote_harness').glob('*.py'))
    pins = {str(p): digest(p) for p in code+[MODEL, GOLD]+[Path(e['source_file']) for e in selected]}
    output.mkdir(parents=True)
    (output/'jobs').mkdir()
    write(output/'freeze.json', dict(version=VERSION, config=CONFIG, source_and_code_pins=pins,
        selected=selected, selection='nearest_native_cells_90_200_300_600_1000_1600',
        retries=0, workers=4, whole_song_seconds=60, no_fitting=True, independent_test=False))
    t = perf_counter()
    statuses = {'engine': [], 'baseline': []}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(one, e, a, output) for e in selected for a in statuses]
        for n, future in enumerate(as_completed(futures), 1):
            r = future.result(); statuses[r['arm']].append(r)
            print(f'[{n}/12] {r["arm"]} {r["title"]}: {r["status"]} {r["wall_seconds"]:.2f}s', flush=True)
    submissions, prediction_pins = {}, {}
    for arm, rows in statuses.items():
        rows.sort(key=lambda r: r['index'])
        songs = {}
        for r in rows:
            if r['status'] == 'complete':
                validated_spans(r['spans'], fraction(r['score_duration']))
                songs[r['title']] = r['spans']
        submissions[arm] = dict(engine=VERSION if arm == 'engine' else 'denominator-beat-template-v1', benchmark='A', songs=songs)
        p = output/f'{arm}-submission.json'; write(p, submissions[arm]); prediction_pins[str(p)] = digest(p)
    write(output/'prediction-freeze.json', dict(predictions=prediction_pins, both_arms_fixed_before_scoring=True))
    write(output/'statuses.json', statuses)
    # Gold labels are first consumed after inference and the prediction seal.
    titles = {e['title'] for e in selected}
    gold = json.loads(GOLD.read_text(encoding='utf-8'))
    gold['songs'] = [r for r in gold['songs'] if r['title'] in titles]
    write(output/'pilot-gold.json', gold)
    result = score_submissions(output/'pilot-gold.json', submissions, statuses, output/'score.json')
    result.update(scope='six_size_stratified_development_songs_not_full_234', independent_test=False,
        connection_decision='not_authorized_by_pilot', wall_seconds=perf_counter()-t)
    write(output/'score.json', result)
    mismatches = [p for p, h in (pins|prediction_pins).items() if digest(p) != h]
    write(output/'audit.json', dict(passed=not mismatches, checked=len(pins|prediction_pins), mismatches=mismatches))
    if mismatches:
        raise ValueError('frozen_run_changed')
    print(json.dumps({a: r['summary'] for a, r in result['reports'].items()}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--output', type=Path, required=True)
    run(ap.parse_args().output.resolve())
