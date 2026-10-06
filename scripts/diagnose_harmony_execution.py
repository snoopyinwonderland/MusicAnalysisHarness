"""Bounded import-only diagnosis. No score/gold/weights loaded; zero retries."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from time import perf_counter
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'tests'))
from musicanote_harness.harmony_execution import atomic_json, run_owned, read_events

PROBES = (('noop', 'noop', 5, False),
          ('platform-system', 'platform_system', 10, False),
          ('guarded-engine-import', 'engine_import', 15, True),
          ('default-engine-import', 'engine_import', 15, False))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    log = io.StringIO()
    validation = unittest.TextTestRunner(stream=log, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_harmony_execution'))
    (output/'validation.txt').write_text(log.getvalue(), encoding='utf-8')
    receipt = dict(tests=validation.testsRun, failures=len(validation.failures),
                   errors=len(validation.errors), passed=validation.wasSuccessful(),
                   seconds=perf_counter()-started,
                   parent_music21_imported=any(x == 'music21' or x.startswith('music21.') for x in sys.modules))
    atomic_json(output/'validation.json', receipt)
    print('validation', json.dumps(receipt), flush=True)
    if not receipt['passed'] or receipt['parent_music21_imported']:
        raise SystemExit('preflight_failed_no_probes_executed')
    paths = set((ROOT/'src/musicanote_harness').glob('*.py'))
    paths.update((Path(__file__).resolve(), ROOT/'tests/test_harmony_execution.py',
                  ROOT/'tests/_harmony_execution_worker_fixture.py',
                  ROOT/'docs/harmony/EXECUTION_STABILITY_PLAN.md',
                  ROOT/'output/harmony-whole-score-intervals-2026-10-06-r1/comparison/score.json',
                  ROOT/'output/harmony-whole-score-intervals-2026-10-06-r1/comparison/audit.json',
                  ROOT/'output/harmony-whole-score-intervals-2026-10-06-r1/comparison/execution-interpretation.json',
                  ROOT/'.venv/Lib/site-packages/music21/common/misc.py',
                  Path(sys._base_executable).parent/'Lib/platform.py'))
    pins = {str(p): sha(p) for p in sorted(paths)}
    freeze = dict(scope='stdlib_and_import_only_no_music_inference', pins=pins,
                  probes=[dict(name=n, action=a, seconds=s, windows_label=w) for n,a,s,w in PROBES],
                  source_scores_read=0, gold_read=0, weights_read=0, retries=0,
                  python_executable=sys.executable, base_executable=sys._base_executable,
                  python_version=sys.version, python_prefix=sys.prefix, validation=receipt)
    atomic_json(output/'freeze.json', freeze)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT/'src')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    reports = []
    probe_started = perf_counter()
    for name, action, seconds, windows_label in PROBES:
        directory = output/name
        nonce = uuid.uuid4().hex
        argv = [sys.executable, '-B', '-m', 'musicanote_harness.harmony_execution',
                '--child', directory, '--nonce', nonce, '--action', action]
        if windows_label:
            argv.append('--windows-label')
        result = run_owned(argv, directory, seconds=seconds, env=env, nonce=nonce)
        events, issues = read_events(directory/'events.jsonl', nonce)
        result['name'] = name
        result['returned_facts'] = [r for r in events if r['event'] in ('module_loaded','platform_query_returned','probe_returned')]
        reports.append(result)
        print(name, result['status'], json.dumps(result['timings']), flush=True)
        if result.get('cleanup') and not result['cleanup'].get('tree_cleanup_confirmed', False):
            print('cleanup_not_confirmed_remaining_probes_not_run', flush=True)
            break
    report = dict(scope=freeze['scope'], probes=reports, planned_probe_count=4,
                  executed_probe_count=len(reports), probe_wall_seconds=perf_counter()-probe_started,
                  model_accuracy_measured=False, whole_song_inference_executed=False,
                  retries=0, parent_music21_imported='music21' in sys.modules)
    atomic_json(output/'report.json', report)
    changed = [p for p, expected in pins.items() if sha(Path(p)) != expected]
    artifacts = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    audit = dict(passed=not changed, pinned_files=len(pins), mismatches=changed,
                 artifacts=artifacts, original_stage102_results_preserved=not any(
                     'whole-score-intervals-2026-10-06-r1' in p for p in changed))
    atomic_json(output/'audit.json', audit)
    print('audit', audit['passed'], 'pins', audit['pinned_files'], flush=True)
    if changed:
        raise SystemExit('source_or_prior_result_changed')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True, type=Path)
    main(ap.parse_args().output)
