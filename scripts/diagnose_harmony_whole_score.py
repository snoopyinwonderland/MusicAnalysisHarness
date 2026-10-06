"""One paired diagnosis per completed sealed song; no new inference or fitting."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from musicanote_harness.harmony_test_a import digest, write, MODEL
from musicanote_harness.harmony_whole_score_diagnosis import diagnose, VERSION


def run(source,output):
    if output.exists():raise ValueError('output_exists_no_overwrite')
    rows=json.loads((source/'statuses.json').read_text(encoding='utf-8'))
    common={r['index'] for r in rows['engine'] if r['status']=='complete'} & {
        r['index'] for r in rows['baseline'] if r['status']=='complete'}
    files=[Path(__file__),ROOT/'docs/harmony/WHOLE_SCORE_OBJECTIVE_SPEC.md',ROOT/'src/musicanote_harness/harmony_whole_score_diagnosis.py',
        ROOT/'tests/test_harmony_whole_score_diagnosis.py',MODEL,source/'statuses.json',
        source/'prediction-freeze.json',source/'audit.json']
    files+=sorted((ROOT/'src/musicanote_harness').glob('*.py'))
    for index in sorted(common):
        files += [source/'jobs'/f'{index:03d}-engine.json',source/'jobs'/f'{index:03d}-baseline.json',
                  source/'jobs'/f'{index:03d}-engine.ir.json.gz']
    pins={str(p):digest(p) for p in files}
    output.mkdir(parents=True)
    write(output/'freeze.json',dict(version=VERSION,pins=pins,paired_indices=sorted(common),
        scope='posthoc_completed_three_only',gold_input=False,new_inference=False))
    t=perf_counter(); results=[]
    for index in sorted(common):
        r=diagnose(source/'jobs'/f'{index:03d}-engine.json',source/'jobs'/f'{index:03d}-baseline.json')
        results.append(r)
        print(r['title'], 'selected',r['selected']['cost'],'counterfactual',
            None if r['baseline_counterfactual'] is None else r['baseline_counterfactual']['cost'],flush=True)
    report=dict(version=VERSION,seconds=perf_counter()-t,results=results,new_inference=False,
        accuracy_measurement=False,production_enabled=False)
    write(output/'diagnosis.json',report)
    mismatches=[p for p,h in pins.items() if digest(p)!=h]
    write(output/'audit.json',dict(passed=not mismatches,checked=len(pins),mismatches=mismatches))
    if mismatches:raise ValueError('frozen_input_changed')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,default=ROOT/'output/harmony-whole-score-pilot-2026-10-06-r1')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();run(args.source,args.output)
