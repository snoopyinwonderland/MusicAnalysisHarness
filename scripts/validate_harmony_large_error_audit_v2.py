"""Retain Stage93's 1014 tests and add supplemental serialized audit checks."""
import argparse
import contextlib
import io
import json
from pathlib import Path
from time import perf_counter
import unittest
from musicanote_harness import harmony_large_error_triage as t

PRIOR_SHA = 'd3b1d2275dc010f8f955de890a8f11c19f546d5d1aa68f120956541792b682eb'


def run(prior, output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    if t.io.digest(prior) != PRIOR_SHA: raise ValueError('large_error_audit_prior_validation_changed')
    base = t.load(prior)
    if base['passed'] is not True or base['tests'] != 1014 or base['previous_validation_sha256'] != t.PRIOR_VALIDATION_SHA:
        raise ValueError('large_error_audit_parent_validation_not_passed')
    modules = base['test_modules']+['test_harmony_large_error_audit_v2']
    if len(set(modules)) != len(modules): raise ValueError('large_error_audit_duplicate_modules')
    log = io.StringIO(); begun = perf_counter()
    with contextlib.redirect_stdout(log):
        result = unittest.TextTestRunner(stream=log, verbosity=1).run(unittest.TestLoader().loadTestsFromNames(modules))
    value = dict(passed=result.wasSuccessful(), tests=result.testsRun, modules=len(modules),
        failures=len(result.failures), errors=len(result.errors), elapsed_seconds=perf_counter()-begun,
        test_modules=modules, previous_validation_sha256=PRIOR_SHA, output=log.getvalue(),
        repository_entire_suite=False, supplemental_audit_only=True, original_source_extraction_repeated=False)
    t.io.write(output, value); return value


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--prior-validation', required=True)
    p.add_argument('--output', required=True); a = p.parse_args(); r = run(a.prior_validation, a.output)
    print(json.dumps({k:r[k] for k in ('passed','tests','modules','failures','errors','elapsed_seconds')}, indent=2))
    raise SystemExit(0 if r['passed'] else 1)
