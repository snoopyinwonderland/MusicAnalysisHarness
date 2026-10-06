"""Retain Stage94 regressions and validate independent partial run evidence."""
import argparse
import contextlib
import io
from pathlib import Path
from time import perf_counter
import unittest
from musicanote_harness import harmony_partial_support_trial as parent


def run(prior,output):
    if Path(output).exists():raise ValueError('output_exists_no_overwrite')
    if parent.io.digest(prior)!=parent.PRIOR_VALIDATION_SHA:raise ValueError('partial_support_prior_validation_changed')
    base=parent.load(prior)
    if not base['passed'] or base['tests']!=1042:raise ValueError('partial_support_prior_not_passed')
    modules=base['test_modules']+['test_harmony_partial_support','test_harmony_partial_support_scoring',
        'test_harmony_partial_support_learning','test_harmony_partial_support_trial']
    stream=io.StringIO();tick=perf_counter()
    with contextlib.redirect_stdout(stream):
        result=unittest.TextTestRunner(stream=stream).run(unittest.TestLoader().loadTestsFromNames(modules))
    report=dict(passed=result.wasSuccessful(),tests=result.testsRun,modules=len(modules),test_modules=modules,
        failures=len(result.failures),errors=len(result.errors),elapsed_seconds=perf_counter()-tick,
        previous_validation_sha256=parent.PRIOR_VALIDATION_SHA,output=stream.getvalue(),repository_entire_suite=False)
    parent.io.write(output,report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prior-validation',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=run(a.prior_validation,a.output)
    print({k:r[k] for k in ('passed','tests','failures','errors','elapsed_seconds')})
    raise SystemExit(0 if r['passed'] else 1)
