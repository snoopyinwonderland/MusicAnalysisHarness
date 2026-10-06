"""One bounded phase diagnostic on the two still-incomplete long inputs."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from musicanote_harness.harmony_test_a import write,digest,MODEL,MODEL_SHA


def run(output):
    if output.exists():raise ValueError('output_exists_no_overwrite')
    if digest(MODEL)!=MODEL_SHA:raise ValueError('model_changed')
    prior=ROOT/'output/harmony-whole-score-performance-2026-10-06-r1/comparison/freeze.json'
    selected=[e for e in json.loads(prior.read_text(encoding='utf-8'))['selected'] if e['index'] in (211,59)]
    if len(selected)!=2:raise ValueError('diagnosis_cohort_changed')
    code=[Path(__file__),ROOT/'docs/harmony/WHOLE_SCORE_PHASE_PLAN.md']
    code+=sorted((ROOT/'src/musicanote_harness').glob('*.py'))
    pins={str(p):digest(p) for p in code+[prior,MODEL]+[Path(e['source_file']) for e in selected]}
    output.mkdir(parents=True);(output/'jobs').mkdir()
    write(output/'freeze.json',dict(selected=selected,pins=pins,seconds=60,workers=2,retries=0,
        diagnostic_only=True,labels_read=False,partial_submission=False))
    def one(entry):
        path=output/'jobs'/f'{entry["index"]:03d}-diagnosis.json';t=perf_counter()
        cmd=[sys.executable,'-B','-m','musicanote_harness.harmony_whole_score_phases',
            '--worker',entry['source_file'],'--output',str(path)]
        env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
        try:
            p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=60)
            r=json.loads(path.read_text(encoding='utf-8')) if p.returncode==0 and path.exists() else dict(
                status='process_error',error=p.stderr.decode('utf-8',errors='replace')[-2000:],spans=[])
        except subprocess.TimeoutExpired:r=dict(status='whole_song_timeout',spans=[])
        r.update(title=entry['title'],index=entry['index'],wall_seconds=perf_counter()-t)
        write(path,r);return r
    t=perf_counter();rows=[]
    with ThreadPoolExecutor(max_workers=2) as ex:
        for future in as_completed([ex.submit(one,e) for e in selected]):
            row=future.result();rows.append(row)
            print(f'{row["title"]}: {row["status"]} {row["wall_seconds"]:.2f}s',flush=True)
    write(output/'statuses.json',dict(rows=rows,wall_seconds=perf_counter()-t))
    changed=[p for p,h in pins.items() if digest(p)!=h]
    write(output/'audit.json',dict(passed=not changed,checked=len(pins),mismatches=changed))
    if changed:raise ValueError('diagnosis_frozen_input_changed')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    run(ap.parse_args().output.resolve())
