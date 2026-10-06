"""Previous sealed regression inventory plus new context-vector tests."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from time import perf_counter
import unittest
from musicanote_harness.harmony_expanded_benchmark import write


def run(prior_validation, output):
    previous = json.loads(Path(prior_validation).read_text(encoding='utf-8'))
    modules = previous['test_modules']+['test_harmony_context_competition', 'test_harmony_context_competition_trial']
    if len(modules) != len(set(modules)): raise ValueError('duplicate_test_module')
    if Path(output).exists(): raise ValueError('output_exists_no_overwrite')
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules); buf = io.StringIO(); tick = perf_counter()
    with redirect_stdout(buf): result = unittest.TextTestRunner(stream=buf).run(suite)
    receipt = {'passed': result.wasSuccessful(), 'tests': result.testsRun, 'modules': len(modules), 'test_modules': modules,
        'failures': len(result.failures), 'errors': len(result.errors), 'elapsed_seconds': perf_counter()-tick,
        'output': buf.getvalue(), 'repository_entire_suite': False}
    write(Path(output), receipt); return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--prior-validation', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); r = run(a.prior_validation, a.output)
    print(json.dumps({k: v for k, v in r.items() if k not in ('output', 'test_modules')}, indent=2), flush=True)
    raise SystemExit(0 if r['passed'] else 1)
