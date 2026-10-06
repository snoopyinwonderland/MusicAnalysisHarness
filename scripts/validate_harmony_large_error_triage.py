"""Keep Stage92's 991 tests and add source-member release/error anatomy tests."""
import argparse
import contextlib
import io
import json
from pathlib import Path
from time import perf_counter
import unittest
from musicanote_harness import harmony_large_error_triage as t


def run(prior, output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    if t.io.digest(prior) != t.PRIOR_VALIDATION_SHA: raise ValueError('large_error_prior_validation_changed')
    base = t.load(prior)
    if base['passed'] is not True: raise ValueError('large_error_prior_validation_not_passed')
    modules = base['test_modules']+['test_harmony_member_release', 'test_harmony_large_error_triage']
    if len(modules) != len(set(modules)): raise ValueError('large_error_duplicate_modules')
    suite = unittest.TestLoader().loadTestsFromNames(modules); log = io.StringIO(); begun = perf_counter()
    with contextlib.redirect_stdout(log): result = unittest.TextTestRunner(stream=log, verbosity=1).run(suite)
    value = dict(passed=result.wasSuccessful(), tests=result.testsRun, modules=len(modules),
        failures=len(result.failures), errors=len(result.errors), elapsed_seconds=perf_counter()-begun,
        test_modules=modules, previous_validation_sha256=t.PRIOR_VALIDATION_SHA,
        repository_entire_suite=False, output=log.getvalue())
    t.io.write(output, value); return value


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--prior-validation', required=True)
    p.add_argument('--output', required=True); a = p.parse_args(); r = run(a.prior_validation, a.output)
    print(json.dumps({k: r[k] for k in ('passed','tests','modules','failures','errors','elapsed_seconds')}, indent=2))
    raise SystemExit(0 if r['passed'] else 1)
