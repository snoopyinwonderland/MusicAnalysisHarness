"""Run the previous 553 checks plus the selected-transition NCT checks."""
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
    modules+=['test_harmony_joint_nct_scoring','test_harmony_joint_nct_trial','test_audit_harmony_joint_nct']
    if len(modules)!=len(set(modules)):raise ValueError('duplicate_test_module')
    suite=unittest.defaultTestLoader.loadTestsFromNames(modules);buffer=io.StringIO();tick=perf_counter()
    with redirect_stdout(buffer):result=unittest.TextTestRunner(stream=buffer).run(suite)
    receipt={'passed':result.wasSuccessful(),'tests':result.testsRun,'modules':len(modules),'test_modules':modules,
        'failures':len(result.failures),'errors':len(result.errors),'elapsed_seconds':perf_counter()-tick,
        'output':buffer.getvalue(),'repository_entire_suite':False}
    write(output,receipt);return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prior-validation',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();r=run(args.prior_validation,args.output)
    print(json.dumps({k:v for k,v in r.items() if k!='output'},indent=2),flush=True)
    raise SystemExit(0 if r['passed'] else 1)
