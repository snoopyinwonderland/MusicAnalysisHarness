"""Read-only correction of stage104 validation; NEVER performs inference.

Keep original status/score/raw artifacts. Corrected eligibility uses the same
source duration equation as harmony_test_a.read_score, including measure ends.
"""
import argparse
from collections import Counter
import gzip
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'tests'))
sys.path.insert(0, str(ROOT/'scripts'))
from musicanote_harness.harmony_execution import atomic_json
from musicanote_harness.harmony_test_a import digest, fraction, validated_spans, score_submissions, aggregate

RUN = ROOT/'output/harmony-owned-whole-score-2026-10-06-r2'
SEALED_IR = ROOT/'output/harmony-frozen-test-a-2026-10-06-r1/jobs'
BASE = ROOT/'output/harmony-whole-score-units-2026-10-06-r1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def source_duration(ir):
    # Identical deterministic equation used by ORIGINAL read_score; not a
    # new musical-time rule or an extension of the inference window.
    return max([fraction(ir['score']['duration_quarters'])] + [
        fraction(m['global_start_quarter'])+fraction(m['actual_duration_quarter']) for m in ir['measures']])


def main(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    log = io.StringIO()
    test = unittest.TextTestRunner(stream=log, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_harmony_owned_result_audit'))
    (output/'validation.txt').write_text(log.getvalue(), encoding='utf-8')
    atomic_json(output/'validation.json', dict(tests=test.testsRun, passed=test.wasSuccessful(),
        failures=len(test.failures), errors=len(test.errors)))
    if not test.wasSuccessful():
        raise SystemExit('correction_validation_failed')
    original_freeze = read(RUN/'freeze.json')
    prediction_freeze = read(RUN/'prediction-freeze.json')
    original_pins = original_freeze['pins'] | prediction_freeze['predictions']
    for p, expected in original_pins.items():
        if digest(p) != expected:
            raise ValueError('original_pinned_source_or_prediction_changed')
    paths = set(p for p in RUN.rglob('*') if p.is_file())
    paths.update((Path(__file__), ROOT/'tests/test_harmony_owned_result_audit.py'))
    pins = {str(p):digest(p) for p in sorted(paths)}
    atomic_json(output/'freeze.json', dict(pins=pins, original_run=str(RUN), inference_calls=0,
        source_clock_equation='max(score.duration, measure.global_start + measure.actual_duration)',
        reason='original_parent_validator_omitted_measure_ends', raw_result_mutations=0))
    statuses = read(RUN/'statuses.json')
    corrections = []
    for entry in original_freeze['selected']:
        index = entry['index']
        ir = json.loads(gzip.decompress((SEALED_IR/f'{index:03d}-engine.ir.json.gz').read_bytes()))
        total = source_duration(ir)
        for arm in ('engine','control'):
            row = next(r for r in statuses[arm] if r['index'] == index)
            directory = RUN/'jobs'/f'{index:03d}-{arm}'
            execution = read(directory/'execution.json')
            if row['status'] != 'artifact_validation_error' or not execution['prediction_eligible']:
                continue
            worker = read(directory/'worker.json')
            new_ir = json.loads(gzip.decompress((directory/'worker.ir.json.gz').read_bytes()))
            if new_ir != ir or fraction(worker['score_duration']) != total:
                raise ValueError('corrected_source_clock_does_not_match')
            if worker['source_file'] != entry['source_file'] or worker['source_sha256'] != original_pins[entry['source_file']]:
                raise ValueError('corrected_source_reference_does_not_match')
            validated_spans(worker['spans'], total)
            json.loads(gzip.decompress((directory/'worker.catalogs.json.gz').read_bytes()))
            corrections.append(dict(index=index, title=entry['title'], arm=arm,
                original_status=row['status'], corrected_status='complete',
                ir_score_duration=ir['score']['duration_quarters'], actual_source_duration=str(total),
                worker_duration=worker['score_duration'], source_ir_all_fields_identical=True,
                execution_timely_normal=True, raw_sha256=digest(directory/'worker.json')))
            row.update(worker)
            row['status'] = 'complete'
            row['output_verification'] = dict(passed=True, corrected_by_source_measure_extent=True)
    submissions = dict(baseline=read(BASE/'baseline-submission.json'))
    for arm in ('engine','control'):
        submissions[arm] = dict(engine='owned-whole-score-corrected-eligibility-'+arm, benchmark='A',
            songs={r['title']:r['spans'] for r in statuses[arm] if r['status']=='complete'})
        atomic_json(output/f'{arm}-submission.json', submissions[arm])
    atomic_json(output/'statuses.json', statuses)
    atomic_json(output/'corrections.json', dict(rows=corrections, new_inference=0, original_raw_predictions_modified=0))
    prediction_pins = {str(output/f'{a}-submission.json'):digest(output/f'{a}-submission.json') for a in ('engine','control')}
    atomic_json(output/'prediction-freeze.json', dict(predictions=prediction_pins, all_fixed_before_scoring=True))
    # Reuse the original already-disclosed cohort. No new labels/cases selected.
    report = score_submissions(RUN/'pilot-gold.json', submissions, statuses, output/'score.json')
    common = set(submissions['engine']['songs']) & set(submissions['control']['songs'])
    report.update(scope='read_only_source_clock_validation_correction', independent_test=False,
        original_score_preserved=str(RUN/'score.json'), new_inference=0,
        connection_decision='not_authorized_by_development_pilot',
        common_completed={a:aggregate([r for r in data['rows'] if r['title'] in common]) for a,data in report['reports'].items()})
    atomic_json(output/'score.json', report)
    diagnostics = []
    for directory in sorted((RUN/'jobs').iterdir()):
        execution = read(directory/'execution.json')
        phase_path = directory/'worker.phases.json'
        trace = (directory/'trace.txt').read_text(encoding='utf-8', errors='replace')
        diagnostics.append(dict(job=directory.name, status=execution['status'],
            returncode=execution['process_returncode'], cleanup=execution['cleanup'],
            timings=execution['timings'], native_access_violation_exit=execution['process_returncode']==3221225477,
            traceback_timer_markers=trace.count('Timeout (0:00:05)!'),
            windows_access_violation_markers=trace.count('Windows fatal exception: access violation'),
            phase_receipt=read(phase_path) if phase_path.exists() else None))
    atomic_json(output/'execution-diagnosis.json', dict(rows=diagnostics,
        statuses=dict(Counter(r['status'] for r in diagnostics)),
        native_access_violation_exit_count=sum(r['native_access_violation_exit'] for r in diagnostics),
        timer_causality_proven=False, original_gold_inferred=False, music_accuracy_not_zero_due_to_missing_results=True))
    changed = [p for p, expected in (original_pins | pins | prediction_pins).items() if digest(p) != expected]
    atomic_json(output/'audit.json', dict(passed=not changed, checked=len(original_pins | pins | prediction_pins),
        mismatches=changed, original_score_statuses_raw_code_all_preserved=True, new_inference=0))
    print(json.dumps(dict(corrections=corrections, completed=report['completed_songs'],
        summaries={a:d['summary'] for a,d in report['reports'].items()},
        numerical_gate=report['numerical_gate_passed'], audit_passed=not changed)), flush=True)
    if changed:
        raise SystemExit('original_or_corrected_prediction_changed')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    main(ap.parse_args().output)
