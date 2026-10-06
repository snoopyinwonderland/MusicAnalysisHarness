"""Prior related 580 checks plus the support balance implementation checks."""
import argparse
import io
import json
from pathlib import Path
from time import perf_counter
import unittest
from contextlib import redirect_stdout
from musicanote_harness.harmony_expanded_benchmark import write


def run(prior_validation,output):
    output=Path(output)
    if output.exists():raise ValueError('output_exists_no_overwrite')
    modules=json.loads(Path(prior_validation).read_text(encoding='utf-8'))['test_modules']
    modules+=['test_harmony_support_balance','test_harmony_support_balance_learning','test_harmony_support_balance_trial']
    if len(modules)!=len(set(modules)):raise ValueError('duplicate_test_module')
    suite=unittest.defaultTestLoader.loadTestsFromNames(modules);buffer=io.StringIO();tick=perf_counter()
    with redirect_stdout(buffer):result=unittest.TextTestRunner(stream=buffer).run(suite)
    receipt={'passed':result.wasSuccessful(),'tests':result.testsRun,'modules':len(modules),'test_modules':modules,
        'failures':len(result.failures),'errors':len(result.errors),'elapsed_seconds':perf_counter()-tick,
        'output':buffer.getvalue(),'repository_entire_suite':False}
    write(output,receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prior-validation',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=run(a.prior_validation,a.output)
    print(json.dumps({k:v for k,v in r.items() if k!='output'},indent=2),flush=True)
    raise SystemExit(0 if r['passed'] else 1)
