"""Four preregistered stdlib probes, once each; no musical inference or gold."""
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
from musicanote_harness.harmony_execution import atomic_json, run_owned
from musicanote_harness.harmony_stack_diagnostic import PROBE_SECONDS

PROBES = (('cpu-timer', 'cpu', True), ('cpu-passive', 'cpu', False),
          ('sleep-timer', 'sleep', True), ('sleep-passive', 'sleep', False))
LIMIT = 12


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    log = io.StringIO()
    receipts = []
    # The fresh-import tests must run BEFORE constructing a musical suite.
    for name in ('test_harmony_execution.BindingTests', 'test_harmony_execution.EventTests',
                 'test_harmony_owned_score_worker',
                 'test_harmony_stack_diagnostic'):
        test = unittest.TextTestRunner(stream=log, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromName(name))
        receipts.append(dict(module=name, tests=test.testsRun, passed=test.wasSuccessful(),
                             failures=len(test.failures), errors=len(test.errors)))
        if not test.wasSuccessful():
            break
    (output/'validation.txt').write_text(log.getvalue(), encoding='utf-8')
    validation = dict(suites=receipts, tests=sum(r['tests'] for r in receipts),
        passed=all(r['passed'] for r in receipts), seconds=perf_counter()-started,
        scope='in_process_contract_tests_only_not_process_stability',
        music21_loaded=any(n == 'music21' or n.startswith('music21.') for n in sys.modules))
    atomic_json(output/'validation.json', validation)
    print('validation', json.dumps(validation), flush=True)
    if not validation['passed'] or validation['music21_loaded']:
        raise SystemExit('preflight_failed_no_probes')
    paths = {ROOT/p for p in (
        'src/musicanote_harness/harmony_execution.py',
        'src/musicanote_harness/harmony_windows_import.py',
        'src/musicanote_harness/harmony_owned_score_worker.py',
        'src/musicanote_harness/harmony_stack_diagnostic.py',
        'src/musicanote_harness/harmony_whole_score_intervals.py',
        'src/musicanote_harness/harmony_phase_checkpoint.py',
        'docs/harmony/STACK_DIAGNOSTIC_PLAN.md',
        'tests/test_harmony_execution.py', 'tests/test_harmony_owned_score_worker.py',
        'tests/test_harmony_stack_diagnostic.py',
        'output/harmony-adversarial-score-2026-10-05-r1/model.json.gz')}
    paths.add(Path(__file__).resolve())
    previous_preflight = ROOT/'output/harmony-stack-diagnostic-2026-10-06-r1'
    paths.update(p for p in previous_preflight.rglob('*') if p.is_file())
    prior_failure = json.loads((previous_preflight/'validation.json').read_text(encoding='utf-8'))
    for previous in ('harmony-owned-whole-score-2026-10-06-r2',
                     'harmony-owned-whole-score-2026-10-06-correction-r1'):
        paths.update(p for p in (ROOT/'output'/previous).rglob('*') if p.is_file())
    pins = {str(p): sha(p) for p in sorted(paths)}
    atomic_json(output/'freeze.json', dict(pins=pins, probes=PROBES,
        workload_seconds=PROBE_SECONDS, whole_process_deadline=LIMIT,
        sequential=True, retries=0, score_inputs_read=0, gold_read=0,
        model_content_read=False, source_music_code_changed=False,
        executable=sys.executable, base_executable=sys._base_executable, python_version=sys.version))
    env = os.environ.copy()
    env.update(PYTHONPATH=str(ROOT/'src'), PYTHONDONTWRITEBYTECODE='1')
    rows = []
    probe_start = perf_counter()
    for name, kind, periodic in PROBES:
        directory = output/name
        nonce = uuid.uuid4().hex
        argv = [sys.executable, '-B', '-m', 'musicanote_harness.harmony_stack_diagnostic',
                '--child', directory, '--nonce', nonce, '--action', kind]
        if periodic:
            argv.append('--periodic-snapshots')
        execution = run_owned(argv, directory, seconds=LIMIT, env=env, nonce=nonce)
        trace = (directory/'trace.txt').read_text(encoding='utf-8', errors='replace')
        raw = directory/'worker.json'
        rows.append(dict(name=name, kind=kind, periodic_snapshots=periodic,
            execution=execution, timer_markers=trace.count('Timeout (0:00:05)!'),
            access_violation_markers=trace.count('Windows fatal exception: access violation'),
            result=json.loads(raw.read_text(encoding='utf-8')) if raw.exists() else None))
        print(name, execution['status'], execution['process_returncode'], flush=True)
        if execution.get('cleanup') and not execution['cleanup'].get('tree_cleanup_confirmed', False):
            break
    complete = [r for r in rows if r['execution']['status'] == 'complete']
    checksums = {r['result']['kernel_sha256'] for r in complete}
    kernel_consistent = bool(complete) and len(checksums) == 1 and all(
        r['result']['kernel_verified'] for r in complete)
    report = dict(scope='bounded_synthetic_stdlib_diagnostic', rows=rows,
        planned=4, executed=len(rows), completed=len(complete), retries=0,
        wall_seconds=perf_counter()-probe_start, completed_kernel_consistent=kernel_consistent,
        native_exit_count=sum(r['execution']['process_returncode'] in (3221225477, -1073741819) for r in rows),
        original_music_crash_cause_proven=False, music_inference_calls=0,
        accuracy_measured=False, whole_score_stability_certified=False,
        prior_process_preflight=prior_failure, prior_failures_resolved=False,
        periodic_default_in_new_adapter=False, old_runner_changed=False)
    atomic_json(output/'report.json', report)
    changed = [p for p, expected in pins.items() if sha(Path(p)) != expected]
    artifacts = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    atomic_json(output/'audit.json', dict(passed=not changed, checked=len(pins),
        mismatches=changed, artifacts=artifacts, previous_results_preserved=not changed))
    print('report', json.dumps({k:v for k,v in report.items() if k != 'rows'}), flush=True)
    if changed or not kernel_consistent:
        raise SystemExit('audit_or_kernel_failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
