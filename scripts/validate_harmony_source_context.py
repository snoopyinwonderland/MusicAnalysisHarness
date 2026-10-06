"""Retain all sealed Stage93 regressions and add source-context scoring tests."""
import argparse
import contextlib
import io
from pathlib import Path
from time import perf_counter
import unittest
from musicanote_harness import harmony_large_error_triage as parent

PRIOR_SHA='9ad1ffc432ac09036a3a22abf2f72af39ae70e921c59df60261516255b5472d3'


def run(prior, output):
    if Path(output).exists(): raise ValueError('output_exists_no_overwrite')
    if parent.io.digest(prior)!=PRIOR_SHA: raise ValueError('source_context_prior_validation_changed')
    base=parent.load(prior)
    if not base['passed'] or base['tests']!=1018: raise ValueError('source_context_prior_not_passed')
    modules=base['test_modules']+['test_harmony_terminal_context','test_harmony_source_context_scoring','test_harmony_source_context_learning','test_harmony_source_context_trial']
    stream=io.StringIO(); tick=perf_counter()
    with contextlib.redirect_stdout(stream):
        r=unittest.TextTestRunner(stream=stream).run(unittest.TestLoader().loadTestsFromNames(modules))
    result=dict(passed=r.wasSuccessful(),tests=r.testsRun,modules=len(modules),test_modules=modules,
        failures=len(r.failures),errors=len(r.errors),elapsed_seconds=perf_counter()-tick,
        previous_validation_sha256=PRIOR_SHA,output=stream.getvalue(),repository_entire_suite=False)
    parent.io.write(output,result); return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prior-validation',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=run(a.prior_validation,a.output);print({k:r[k] for k in ('passed','tests','failures','errors','elapsed_seconds')})
    raise SystemExit(0 if r['passed'] else 1)
