"""Retain the sealed Stage92 986 tests and add original-cap audit regressions."""
import argparse
import contextlib
import io
import json
from pathlib import Path
from time import perf_counter
import unittest
from musicanote_harness import harmony_exact_beat_dev_trial as t

PRIOR_SHA = 'b06400079d88d49c89939d699bfc16644036af527b3eacd782b5852bff612114'


def run(prior, output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    if t.io.digest(prior) != PRIOR_SHA: raise ValueError('audit_v2_prior_validation_changed')
    base = t.load(prior)
    if base['passed'] is not True: raise ValueError('audit_v2_prior_validation_not_passed')
    modules = base['test_modules']+['test_harmony_exact_beat_dev_audit_v2']
    if len(modules) != len(set(modules)): raise ValueError('audit_v2_duplicate_modules')
    suite = unittest.TestLoader().loadTestsFromNames(modules)
    log = io.StringIO(); begun = perf_counter()
    with contextlib.redirect_stdout(log): result = unittest.TextTestRunner(stream=log, verbosity=1).run(suite)
    value = dict(passed=result.wasSuccessful(), tests=result.testsRun, modules=len(modules),
        failures=len(result.failures), errors=len(result.errors), elapsed_seconds=perf_counter()-begun,
        test_modules=modules, repository_entire_suite=False, previous_validation_sha256=PRIOR_SHA,
        output=log.getvalue(), supplemental_audit_only=True, sealed_search_repeated=False)
    t.io.write(output, value); return value


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--prior-validation', required=True)
    p.add_argument('--output', required=True); args = p.parse_args(); r = run(args.prior_validation, args.output)
    print(json.dumps({k: r[k] for k in ('passed','tests','modules','failures','errors','elapsed_seconds',
        'repository_entire_suite','supplemental_audit_only')}, indent=2), flush=True)
    raise SystemExit(0 if r['passed'] else 1)
