"""Bounded subprocess runner: metadata-only inference, then sealed evaluation."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from musicanote_harness.harmony_test_a import (MODEL, MODEL_SHA, VERSION, SCORER_VERSION,
    digest, write, score_submissions, validated_spans, fraction)

GOLD = Path('K:/Music Composition/docs/handoff/harmony_eval/harmony_benchmark_gold.json')
XML = ROOT / 'MusicXML'


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


def exposure_check(entries):
    # Historical documentation only, never prediction/gold matches. Incomplete
    # history means not-found is NOT a certification of complete independence.
    texts = {}
    for directory in (ROOT / 'docs/harmony', ROOT / 'MUSICANOTE_Canonical_Music_IR'):
        for p in directory.rglob('*.md'):
            if p.name == 'FROZEN_ENGINE_TEST_A_PLAN.md':
                continue
            texts[str(p)] = normalized(p.read_text(encoding='utf-8', errors='replace'))
    rows = []
    for e in entries:
        term = normalized(e['title'])
        matches = [p for p, text in texts.items() if len(term) >= 8 and term in text]
        rows.append(dict(title=e['title'], possible_exposure_docs=matches,
                         exposure_status='possible_documented_exposure' if matches else 'not_found_history_incomplete'))
    return dict(history_complete=False, method='normalized_title_in_existing_harmony_docs', records=rows,
                hash_overlap_check='234 source hashes retained; exhaustive historical source inventory unavailable',
                independent_test_certified=False)


def run_one(entry, arm, output, timeout):
    t = perf_counter()
    index = entry['index']
    target = output / 'jobs' / f'{index:03d}-{arm}.json'
    cmd = [sys.executable, '-B', '-m', 'musicanote_harness.harmony_test_a',
           '--worker', str(XML / entry['piano_solo_file']), '--arm', arm, '--output', str(target)]
    try:
        # Redirect only this child's interpreter path. No global settings edit.
        import os
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
        process = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
        if process.returncode != 0 or not target.exists():
            result = dict(status='process_error', exit_code=process.returncode,
                          error=process.stderr.decode('utf-8', errors='replace')[-2000:])
        else:
            result = json.loads(target.read_text(encoding='utf-8'))
        if process.stderr:
            result['stderr_tail'] = process.stderr.decode('utf-8', errors='replace')[-1000:]
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits for our child on timeout. No broad
        # process-name killing, no running children silently left behind.
        result = dict(status='whole_song_timeout', spans=[], timeout_seconds=timeout)
    result.update(title=entry['title'], index=index, wall_seconds=perf_counter() - t)
    write(target, result)
    return result


def run(output, timeout=60, workers=4):
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    if digest(MODEL) != MODEL_SHA:
        raise ValueError('model_sha_changed')
    metadata_container = json.loads(GOLD.read_text(encoding='utf-8'))
    entries = [dict(index=i, title=s['title'], piano_solo_file=s['piano_solo_file'])
               for i, s in enumerate(metadata_container['songs'])]
    del metadata_container  # workers receive no gold/melody paths or duration
    if len(entries) != 234 or len({e['title'] for e in entries}) != 234:
        raise ValueError('unexpected_benchmark_inventory')
    files = [XML / e['piano_solo_file'] for e in entries]
    if any(not p.is_file() for p in files):
        raise ValueError('missing_score_input')
    pins = {str(p): digest(p) for p in files}
    pins[str(MODEL)] = MODEL_SHA
    pins[str(GOLD)] = digest(GOLD)
    code = [Path(__file__), ROOT / 'docs/harmony/FROZEN_ENGINE_TEST_A_PLAN.md']
    code += sorted((ROOT / 'src/musicanote_harness').glob('*.py'))
    pins.update({str(p): digest(p) for p in code})
    output.mkdir(parents=True)
    (output / 'jobs').mkdir()
    write(output / 'input-manifest.json', dict(entries=entries, source_folder=str(XML), gold_fields_in_manifest=False))
    exposure = exposure_check(entries)
    write(output / 'exposure-check.json', exposure)
    write(output / 'freeze.json', dict(engine=VERSION, model_sha256=MODEL_SHA, scorer=SCORER_VERSION,
          whole_song_timeout_seconds=timeout, workers=workers, retries=0, source_and_code_pins=pins,
          no_fitting=True, no_feature_additions=True, local_winner_stitching=False,
          primary_gain_required=.05, paired_bootstrap_seed=20261006, paired_bootstrap_samples=2000,
          model_use='local_noncommercial_research_only', production_modified=False))
    statuses = {'engine': [], 'baseline': []}
    t = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_one, e, a, output, timeout) for e in entries for a in statuses]
        for done, future in enumerate(as_completed(futures), 1):
            r = future.result()
            arm = 'engine' if r.get('arm') == 'engine' else None
            # Preserve timeout/error arm using the submitted metadata.
            if arm is None:
                # Completed file identity is unambiguous; derive from future.
                submitted = futures.index(future)
                arm = ('engine', 'baseline')[submitted % 2]
                r['arm'] = arm
            statuses[arm].append(r)
            if done % 12 == 0 or done == len(futures):
                print(f'[{done}/{len(futures)} jobs] {perf_counter()-t:.1f}s ' +
                      ' '.join(f'{a}:{dict(Counter(x["status"] for x in rs))}' for a, rs in statuses.items()), flush=True)
                write(output / 'progress.json', dict(complete=False, phase='inference', jobs_done=done,
                     jobs_total=len(futures), elapsed_seconds=perf_counter() - t))
    submissions = {}
    prediction_pins = {}
    for arm, rows in statuses.items():
        rows.sort(key=lambda r: r['index'])
        songs = {}
        for r in rows:
            if r['status'] == 'complete':
                validated_spans(r['spans'], fraction(r['score_duration']))
                songs[r['title']] = r['spans']
        submissions[arm] = dict(engine=VERSION if arm == 'engine' else 'denominator-beat-template-v1',
                                benchmark='A', songs=songs)
        p = output / f'{arm}-submission.json'
        write(p, submissions[arm])
        prediction_pins[str(p)] = digest(p)
    write(output / 'statuses.json', statuses)
    write(output / 'prediction-freeze.json', dict(complete=True, predictions=prediction_pins,
          gold_used_by_worker=False, both_arms_fixed_before_scoring=True))
    result = score_submissions(GOLD, submissions, statuses, output / 'corrected-score.json')
    possible = {r['title'] for r in exposure['records'] if r['possible_exposure_docs']}
    from musicanote_harness.harmony_test_a import aggregate
    result['not_found_history_incomplete_subset'] = {
        a: aggregate([r for r in report['rows'] if r['title'] not in possible])
        for a, report in result['reports'].items()}
    result['exposure_possible_titles'] = sorted(possible)
    result['independence_certified'] = False
    result['wall_seconds'] = perf_counter() - t
    result['status_counts'] = {a: dict(Counter(r['status'] for r in rows)) for a, rows in statuses.items()}
    result['execution_time'] = {}
    for a, rows in statuses.items():
        seconds = sorted(r['wall_seconds'] for r in rows)
        result['execution_time'][a] = dict(median_seconds=seconds[len(seconds)//2],
                                          p95_seconds=seconds[int(.95*(len(seconds)-1))])
    write(output / 'corrected-score.json', result)
    # One fixed-version post-run audit. Do not traverse old experimental pins.
    mismatches = [p for p, h in (pins | prediction_pins).items() if digest(p) != h]
    write(output / 'audit.json', dict(passed=not mismatches, checked=len(pins | prediction_pins), mismatches=mismatches))
    write(output / 'progress.json', dict(complete=not mismatches, phase='scored_and_audited',
          jobs_done=468, jobs_total=468, elapsed_seconds=perf_counter()-t, decision=result['decision']))
    if mismatches:
        raise ValueError('fixed_version_audit_failed')
    print(json.dumps({k: result[k] for k in ('completed_songs', 'triad_delta', 'paired_bootstrap_95_ci', 'decision')},
                     ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    run(args.output.resolve(), args.timeout, args.workers)
