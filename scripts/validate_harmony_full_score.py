"""Prior 666 related checks plus full score/calibration/runner checks."""
import argparse
import json
from pathlib import Path
import io
import unittest
from contextlib import redirect_stdout
from time import perf_counter
from musicanote_harness.harmony_expanded_benchmark import write


def run(prior_validation, output):
    original = json.loads(Path(prior_validation).read_text(encoding='utf-8'))
    modules = original['test_modules']+['test_harmony_full_score', 'test_harmony_full_score_learning', 'test_harmony_full_score_trial']
    if len(modules) != len(set(modules)): raise ValueError('duplicate_test_module')
    if Path(output).exists(): raise ValueError('output_exists_no_overwrite')
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules); buffer = io.StringIO(); tick = perf_counter()
    with redirect_stdout(buffer): result = unittest.TextTestRunner(stream=buffer).run(suite)
    receipt = {'passed': result.wasSuccessful(), 'tests': result.testsRun, 'modules': len(modules), 'test_modules': modules,
        'failures': len(result.failures), 'errors': len(result.errors), 'elapsed_seconds': perf_counter()-tick,
        'output': buffer.getvalue(), 'repository_entire_suite': False}
    write(Path(output), receipt); return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--prior-validation', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); r = run(a.prior_validation, a.output)
    print(json.dumps({k: v for k, v in r.items() if k != 'output'}, indent=2), flush=True)
    raise SystemExit(0 if r['passed'] else 1)
