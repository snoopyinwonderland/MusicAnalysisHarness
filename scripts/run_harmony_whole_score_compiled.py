"""Single controlled compilation comparison. No parameter sweeps or retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from musicanote_harness.harmony_test_a import write,digest,MODEL,MODEL_SHA,validated_spans,fraction,score_submissions,aggregate
from musicanote_harness.harmony_whole_score_compiled import VERSION
from musicanote_harness.harmony_progression_search import _hash

PRIOR=ROOT/'output/harmony-whole-score-performance-2026-10-06-r1/comparison'
BASE=ROOT/'output/harmony-whole-score-units-2026-10-06-r1'
GOLD=Path('K:/Music Composition/docs/handoff/harmony_eval/harmony_benchmark_gold.json')
FIELDS=('selected_path','page_inventory','score_cost','feature_values','feature_availability',
        'actual_harmonic_runs','states_discarded','operations','spans')


def catalog_hash(path):return _hash(json.loads(gzip.decompress(path.read_bytes())))


def one(entry,arm,output):
    path=output/'jobs'/f'{entry["index"]:03d}-{arm}.json';t=perf_counter()
    module='harmony_whole_score_compiled' if arm=='engine' else 'harmony_whole_score_phases'
    # Diagnostics do not change source/provider caches. Retain tracebacks even
    # when a long parser never returns, without submitting a partial winner.
    code=('import faulthandler,sys; from pathlib import Path; '
        'from musicanote_harness import '+module+' as m; '
        'faulthandler.enable(); faulthandler.dump_traceback_later(20,repeat=True); '
        'm.worker(Path(sys.argv[1]),Path(sys.argv[2])); faulthandler.cancel_dump_traceback_later()')
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
    try:
        p=subprocess.run([sys.executable,'-B','-c',code,entry['source_file'],str(path)],
            cwd=ROOT,env=env,capture_output=True,timeout=60)
        stderr=p.stderr
        r=json.loads(path.read_text(encoding='utf-8')) if p.returncode==0 and path.exists() else dict(
            status='process_error',error=stderr.decode('utf-8',errors='replace')[-2000:],spans=[])
    except subprocess.TimeoutExpired as exc:
        stderr=exc.stderr or b'';r=dict(status='whole_song_timeout',spans=[])
    path.with_suffix('.trace.txt').write_bytes(stderr)
    r.update(title=entry['title'],index=entry['index'],arm=arm,wall_seconds=perf_counter()-t)
    write(path,r);return r


def run(output):
    if output.exists():raise ValueError('output_exists_no_overwrite')
    if digest(MODEL)!=MODEL_SHA:raise ValueError('model_changed')
    selected=json.loads((PRIOR/'freeze.json').read_text(encoding='utf-8'))['selected']
    if {e['index'] for e in selected}!={158,110,61,156,211,59}:raise ValueError('cohort_changed')
    code=[Path(__file__),ROOT/'docs/harmony/WHOLE_SCORE_COMPILED_PLAN.md',
        ROOT/'tests/test_harmony_whole_score_compiled.py']+sorted((ROOT/'src/musicanote_harness').glob('*.py'))
    diagnosis=output.parent/'diagnosis'
    artifacts=[PRIOR/'freeze.json',PRIOR/'equivalence.json',BASE/'baseline-submission.json',BASE/'statuses.json',GOLD,MODEL,
        diagnosis/'freeze.json',diagnosis/'audit.json',diagnosis/'statuses.json']
    artifacts+=sorted((PRIOR/'jobs').glob('*-engine.json'))+sorted((PRIOR/'jobs').glob('*-engine.catalogs.json.gz'))
    artifacts+=sorted((diagnosis/'jobs').glob('*.phases.json'))
    pins={str(p):digest(p) for p in code+artifacts+[Path(e['source_file']) for e in selected]}
    output.mkdir(parents=True);(output/'jobs').mkdir()
    write(output/'freeze.json',dict(version=VERSION,selected=selected,pins=pins,workers=4,seconds=60,
        retries=0,score_change=False,candidate_change=False,beam_width=8,operation_budget=2_000_000,
        direct_scorer_original_stage99=True,independent_test=False,connection_authorized=False,
        baseline_reused_from_sealed_stage99=True,phase_and_trace_instrumentation_both_arms=True))
    t=perf_counter();statuses={'engine':[],'control':[]}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for n,future in enumerate(as_completed([ex.submit(one,e,a,output) for e in selected for a in statuses]),1):
            r=future.result();statuses[r['arm']].append(r)
            print(f'[{n}/12] {r["arm"]} {r["title"]}: {r["status"]} {r["wall_seconds"]:.2f}s',flush=True)
    statuses['baseline']=json.loads((BASE/'statuses.json').read_text(encoding='utf-8'))['baseline']
    submissions={'baseline':json.loads((BASE/'baseline-submission.json').read_text(encoding='utf-8'))}
    prediction_pins={str(BASE/'baseline-submission.json'):digest(BASE/'baseline-submission.json')}
    for arm in ('engine','control'):
        statuses[arm].sort(key=lambda r:r['index']);songs={}
        for r in statuses[arm]:
            if r['status']=='complete':
                validated_spans(r['spans'],fraction(r['score_duration']));songs[r['title']]=r['spans']
        submissions[arm]=dict(engine=VERSION if arm=='engine' else 'local-beat-0.2.1-performance',benchmark='A',songs=songs)
        path=output/f'{arm}-submission.json';write(path,submissions[arm]);prediction_pins[str(path)]=digest(path)
    write(output/'prediction-freeze.json',dict(predictions=prediction_pins,all_fixed_before_scoring=True))
    write(output/'statuses.json',statuses)
    comparisons=[]
    for r in statuses['engine']:
        row=dict(index=r['index'],title=r['title'],engine_status=r['status'])
        control=next(c for c in statuses['control'] if c['index']==r['index'])
        previous=json.loads((PRIOR/'jobs'/f'{r["index"]:03d}-engine.json').read_text(encoding='utf-8'))
        row['control_status']=control['status']
        if r['status']=='complete':
            for label,other,folder,arm in (('control',control,output/'jobs','control'),('previous100',previous,PRIOR/'jobs','engine')):
                if other['status']=='complete':
                    diff=[k for k in FIELDS if r.get(k)!=other.get(k)]
                    if catalog_hash(output/'jobs'/f'{r["index"]:03d}-engine.catalogs.json.gz')!=catalog_hash(folder/f'{r["index"]:03d}-{arm}.catalogs.json.gz'):
                        diff.append('full_catalogs')
                    row[label+'_mismatches']=diff
        comparisons.append(row)
    equivalent=not any(v for row in comparisons for k,v in row.items() if k.endswith('_mismatches'))
    write(output/'equivalence.json',dict(passed=equivalent,rows=comparisons))
    gold=json.loads(GOLD.read_text(encoding='utf-8'));titles={e['title'] for e in selected}
    gold['songs']=[s for s in gold['songs'] if s['title'] in titles]
    if len(gold['songs'])!=6:raise ValueError('gold_cohort_changed')
    write(output/'pilot-gold.json',gold)
    result=score_submissions(output/'pilot-gold.json',submissions,statuses,output/'score.json')
    common=set(submissions['engine']['songs'])&set(submissions['control']['songs'])
    result.update(scope='single_controlled_compilation_six_development_songs',independent_test=False,
        connection_decision='not_authorized_by_development_pilot',baseline_timing_measured_this_run=False,
        common_completed={a:aggregate([r for r in report['rows'] if r['title'] in common]) for a,report in result['reports'].items()},
        wall_seconds=perf_counter()-t)
    write(output/'score.json',result)
    changed=[p for p,h in (pins|prediction_pins).items() if digest(p)!=h]
    write(output/'audit.json',dict(passed=not changed,checked=len(pins|prediction_pins),mismatches=changed))
    if changed:raise ValueError('frozen_input_changed')
    if not equivalent:raise ValueError('compiled_prediction_changed')
    print(json.dumps({a:r['summary'] for a,r in result['reports'].items()},ensure_ascii=False),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    run(ap.parse_args().output.resolve())
