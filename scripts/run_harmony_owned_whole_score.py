"""One fixed six-song comparison, preserving raw workers and whole deadlines."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from threading import Event
from time import perf_counter
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'tests'))
from musicanote_harness.harmony_execution import atomic_json, run_owned

PRIOR = ROOT/'output/harmony-whole-score-phase-2026-10-06-r1/comparison'
INPUTS = ROOT/'output/harmony-whole-score-intervals-2026-10-06-r1/inputs'
SEALED_IR = ROOT/'output/harmony-frozen-test-a-2026-10-06-r1/jobs'
BASE = ROOT/'output/harmony-whole-score-units-2026-10-06-r1'
MODEL = ROOT/'output/harmony-adversarial-score-2026-10-05-r1/model.json.gz'
MODEL_SHA = '2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf'
GOLD = Path('K:/Music Composition/docs/handoff/harmony_eval/harmony_benchmark_gold.json')
VERSION = 'owned-whole-score-execution-0.1.0'
FIELDS = ('selected_path','page_inventory','score_cost','feature_values','feature_availability',
          'actual_harmonic_runs','states_discarded','operations','spans')
TESTS = ('test_harmony_whole_score','test_harmony_whole_score_units',
         'test_harmony_whole_score_diagnosis','test_harmony_whole_score_fast',
         'test_harmony_whole_score_fast_positive_roles','test_harmony_whole_score_compiled',
         'test_harmony_phase_checkpoint','test_harmony_whole_score_intervals','test_harmony_test_a',
         'test_harmony_execution','test_harmony_owned_score_worker')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def compressed(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def raw_result(path):
    if not path.exists():
        return {}
    try:
        value = read(path)
        if not isinstance(value, dict):
            raise ValueError('non_object_raw_result')
        return value
    except (ValueError, OSError) as exc:
        return dict(status='unreadable_raw_result', diagnostic_error=f'{type(exc).__name__}: {exc}')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one(entry, arm, output, env, abort, source_shas):
    directory = output/'jobs'/f'{entry["index"]:03d}-{arm}'
    meta = dict(index=entry['index'], title=entry['title'], arm=arm)
    if abort.is_set():
        return meta | dict(status='not_run_after_cleanup_failure', spans=[])
    nonce = uuid.uuid4().hex
    action = 'intervals' if arm == 'engine' else 'compiled'
    argv = [sys.executable,'-B','-m','musicanote_harness.harmony_owned_score_worker',
            '--child',directory,'--nonce',nonce,'--action',action,'--source',entry['source_file']]
    execution = run_owned(argv, directory, seconds=60, env=env, nonce=nonce)
    if execution['cleanup'] and not execution['cleanup'].get('tree_cleanup_confirmed', False):
        abort.set()
    status = execution['status']
    result = dict(spans=[])
    verification = dict(passed=False, checked=False)
    if execution['prediction_eligible']:
        # No golden labels. Verify the full source representation and output
        # contract; music correctness is scored only after all predictions seal.
        try:
            from musicanote_harness.harmony_test_a import validated_spans, fraction
            result = read(directory/'worker.json')
            old_ir = compressed(SEALED_IR/f'{entry["index"]:03d}-engine.ir.json.gz')
            new_ir = compressed(directory/'worker.ir.json.gz')
            if new_ir != old_ir:
                raise ValueError('full_source_ir_changed')
            total = fraction(old_ir['score']['duration_quarters'])
            if fraction(result['score_duration']) != total:
                raise ValueError('full_score_duration_changed')
            if result['source_file'] != entry['source_file'] or result['source_sha256'] != source_shas[entry['source_file']]:
                raise ValueError('source_reference_changed')
            validated_spans(result['spans'], total)
            compressed(directory/'worker.catalogs.json.gz')
            verification = dict(passed=True, checked=True, full_ir_all_fields_identical=True,
                                full_catalog_loaded=True, full_span_contract_valid=True)
            status = 'complete'
        except (ValueError, OSError, KeyError) as exc:
            status = 'artifact_validation_error'
            verification = dict(passed=False, checked=True, error=f'{type(exc).__name__}: {exc}')
            result = dict(spans=[])
    else:
        result = dict(spans=[])  # Raw worker stays untouched, even if complete.
    row = result | meta | dict(status=status, execution=execution, output_verification=verification,
                              wall_seconds=execution['timings']['process_wall_seconds'],
                              raw_worker_file=str(directory/'worker.json'))
    atomic_json(directory/'status.json', row)
    return row


def main(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    validation_log = io.StringIO()
    t = perf_counter()
    # The isolated-import contract test must run BEFORE constructing/loading
    # any musical TestSuite, not merely before its test methods are called.
    validations = []
    validations.append(unittest.TextTestRunner(stream=validation_log, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_harmony_execution')))
    if validations[0].wasSuccessful():
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name)
                                   for name in TESTS if name != 'test_harmony_execution')
        validations.append(unittest.TextTestRunner(stream=validation_log, verbosity=2).run(suite))
    (output/'validation.txt').write_text(validation_log.getvalue(), encoding='utf-8')
    validation_receipt = dict(tests=sum(v.testsRun for v in validations),
        failures=sum(len(v.failures) for v in validations), errors=sum(len(v.errors) for v in validations),
        passed=all(v.wasSuccessful() for v in validations), seconds=perf_counter()-t,
        isolation_tests_before_music_module_import=True)
    atomic_json(output/'validation.json', validation_receipt)
    print('validation', json.dumps(validation_receipt), flush=True)
    if not validation_receipt['passed']:
        raise SystemExit('preflight_failed_no_music_execution')
    entries = read(PRIOR/'freeze.json')['selected']
    if {e['index'] for e in entries} != {158,110,61,156,211,59} or len(entries) != 6:
        raise ValueError('cohort_changed')
    if digest(MODEL) != MODEL_SHA or not read(INPUTS/'audit.json')['passed']:
        raise ValueError('model_or_input_audit_changed')
    prior_input_pins = read(INPUTS/'freeze.json')['pins']
    if any(digest(p) != expected for p, expected in prior_input_pins.items()):
        raise ValueError('previous_audited_input_changed')
    paths = set((ROOT/'src/musicanote_harness').glob('*.py'))
    paths.update(ROOT/'tests'/f'{name}.py' for name in TESTS)
    paths.update((Path(__file__).resolve(), ROOT/'tests/_harmony_execution_worker_fixture.py',
                  ROOT/'docs/harmony/OWNED_WHOLE_SCORE_PLAN.md', MODEL, GOLD,
                  PRIOR/'freeze.json', PRIOR/'audit.json', PRIOR/'equivalence.json',
                  INPUTS/'freeze.json', INPUTS/'audit.json',
                  BASE/'baseline-submission.json', BASE/'statuses.json',
                  ROOT/'output/harmony-execution-stability-2026-10-06-r2/report.json',
                  ROOT/'output/harmony-execution-stability-2026-10-06-r2/audit.json',
                  ROOT/'.venv/Lib/site-packages/music21/common/misc.py'))
    paths.update(Path(e['source_file']) for e in entries)
    paths.update(SEALED_IR/f'{e["index"]:03d}-engine.ir.json.gz' for e in entries)
    paths.update((PRIOR/'jobs').glob('*-engine*'))
    pins = {str(p): digest(p) for p in sorted(paths) if p.is_file()}
    source_shas = {e['source_file']: pins[e['source_file']] for e in entries}
    atomic_json(output/'freeze.json', dict(version=VERSION, selected=entries, pins=pins,
        validation=validation_receipt, model_sha256=MODEL_SHA, workers=4, seconds=60, retries=0,
        beam_width=8, operation_budget=2_000_000, page_cells=12, windows_label=False,
        execution_environment='approved_unsandboxed_owned_processes_only',
        baseline_reused_from_sealed_stage99=True, baseline_timing_measured_this_run=False,
        independent_test=False, connection_authorized=False, direct_scorer_original_stage99=True,
        music_rules_changed=False, private_atomic_final_writer_both_arms=True))
    (output/'jobs').mkdir()
    env = os.environ.copy()
    env.update(PYTHONPATH=str(ROOT/'src'), PYTHONDONTWRITEBYTECODE='1')
    abort = Event()
    statuses = dict(engine=[], control=[])
    t = perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(one, e, a, output, env, abort, source_shas) for e in entries for a in statuses]
        for n, future in enumerate(as_completed(futures), 1):
            row = future.result()
            statuses[row['arm']].append(row)
            print(f'[{n}/12] {row["arm"]} {row["index"]} {row["title"]}: {row["status"]} {row.get("wall_seconds")}', flush=True)
    execution_wall = perf_counter()-t
    for arm in statuses:
        statuses[arm].sort(key=lambda row: row['index'])
    from musicanote_harness.harmony_test_a import score_submissions, aggregate
    statuses['baseline'] = read(BASE/'statuses.json')['baseline']
    submissions = dict(baseline=read(BASE/'baseline-submission.json'))
    for arm in ('engine', 'control'):
        submissions[arm] = dict(engine=VERSION+'-'+arm, benchmark='A', songs={
            r['title']: r['spans'] for r in statuses[arm] if r['status']=='complete'})
        atomic_json(output/f'{arm}-submission.json', submissions[arm])
    atomic_json(output/'statuses.json', statuses)
    prediction_paths = [output/f'{a}-submission.json' for a in ('engine','control')]
    prediction_paths += list((output/'jobs').rglob('*'))
    prediction_pins = {str(p):digest(p) for p in prediction_paths if p.is_file()}
    prediction_pins[str(BASE/'baseline-submission.json')] = digest(BASE/'baseline-submission.json')
    atomic_json(output/'prediction-freeze.json', dict(predictions=prediction_pins, all_fixed_before_scoring=True))
    comparisons = []
    for e in entries:
        i = e['index']; engine_dir = output/'jobs'/f'{i:03d}-engine'
        control_dir = output/'jobs'/f'{i:03d}-control'
        er = raw_result(engine_dir/'worker.json')
        cr = raw_result(control_dir/'worker.json')
        row = dict(index=i, title=e['title'], raw_engine_status=er.get('status'), raw_control_status=cr.get('status'),
                   engine_status=next(r['status'] for r in statuses['engine'] if r['index']==i),
                   control_status=next(r['status'] for r in statuses['control'] if r['index']==i))
        for label, other, catalog in (
                ('control',cr,control_dir/'worker.catalogs.json.gz'),
                ('previous101',read(PRIOR/'jobs'/f'{i:03d}-engine.json'),PRIOR/'jobs'/f'{i:03d}-engine.catalogs.json.gz')):
            if er.get('status') == other.get('status') == 'complete':
                diff = [k for k in FIELDS if er.get(k) != other.get(k)]
                if compressed(engine_dir/'worker.catalogs.json.gz') != compressed(catalog):
                    diff.append('full_catalogs')
                row[label+'_mismatches'] = diff
        comparisons.append(row)
    raw_pairs = sum('control_mismatches' in r for r in comparisons)
    timely_pairs = sum(r['engine_status']==r['control_status']=='complete' for r in comparisons)
    equivalent = not any(v for r in comparisons for k,v in r.items() if k.endswith('_mismatches'))
    atomic_json(output/'equivalence.json', dict(passed=equivalent if raw_pairs else None,
        raw_complete_pairs=raw_pairs, timely_complete_pairs=timely_pairs,
        no_pairs_is_not_equivalence_proof=True, rows=comparisons))
    # FIRST gold content read, after all prediction and raw artifact pins.
    gold = read(GOLD); titles = {e['title'] for e in entries}
    gold['songs'] = [s for s in gold['songs'] if s['title'] in titles]
    if len(gold['songs']) != 6:
        raise ValueError('gold_cohort_changed')
    atomic_json(output/'pilot-gold.json', gold)
    report = score_submissions(output/'pilot-gold.json', submissions, statuses, output/'score.json')
    common = set(submissions['engine']['songs']) & set(submissions['control']['songs'])
    report.update(scope='owned_execution_fixed_six_development_songs', independent_test=False,
        execution_wall_seconds=execution_wall, baseline_timing_measured_this_run=False,
        connection_decision='not_authorized_by_development_pilot',
        common_completed={a:aggregate([r for r in data['rows'] if r['title'] in common]) for a,data in report['reports'].items()})
    atomic_json(output/'score.json', report)
    changed = [p for p, expected in (pins | prediction_pins).items() if digest(p) != expected]
    atomic_json(output/'audit.json', dict(passed=not changed, checked=len(pins | prediction_pins), mismatches=changed,
        prediction_freeze_before_gold_read=True, execution=VERSION))
    print(json.dumps(dict(completed=report['completed_songs'], summaries={a:d['summary'] for a,d in report['reports'].items()},
                         numerical_gate=report['numerical_gate_passed'], audit_passed=not changed,
                         raw_equivalence=equivalent if raw_pairs else None)), flush=True)
    if changed or not equivalent:
        raise SystemExit('frozen_input_or_prediction_equivalence_failed')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    main(ap.parse_args().output)
