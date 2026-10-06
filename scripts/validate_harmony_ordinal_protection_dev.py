"""Retain all Stage88 regression modules and add the frozen ordinal Dev contract."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from time import perf_counter
import unittest
from musicanote_harness.harmony_expanded_benchmark import write

PRIOR_SHA = '4b0d90eee150d4685b4f87d51cc5ed9086f64d28ea2b4a90faa173209b4751b0'


def run(previous, output):
    if Path(output).exists(): raise ValueError('output_exists_no_overwrite')
    raw = Path(previous).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SHA: raise ValueError('prior_validation_changed')
    prior = json.loads(raw)
    if prior['passed'] is not True: raise ValueError('previous_validation_not_passed')
    modules = prior['test_modules']+['test_harmony_ordinal_protection_dev_trial']
    if len(modules) != len(set(modules)): raise ValueError('duplicate_test_module')
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules); buf = io.StringIO(); tick = perf_counter()
    with redirect_stdout(buf): result = unittest.TextTestRunner(stream=buf).run(suite)
    receipt = dict(passed=result.wasSuccessful(), tests=result.testsRun, modules=len(modules), test_modules=modules,
        failures=len(result.failures), errors=len(result.errors), elapsed_seconds=perf_counter()-tick,
        output=buf.getvalue(), repository_entire_suite=False, previous_validation_sha256=PRIOR_SHA)
    write(Path(output), receipt); return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior-validation', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); r = run(a.prior_validation, a.output)
    print(json.dumps({k: v for k, v in r.items() if k not in ('output', 'test_modules')}, indent=2), flush=True)
    raise SystemExit(0 if r['passed'] else 1)
