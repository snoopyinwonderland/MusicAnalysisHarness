"""One controlled old-vs-fast comparison, same musical score and six inputs."""
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
from musicanote_harness.harmony_whole_score_fast import VERSION
from musicanote_harness.harmony_progression_search import _hash

OLD=ROOT/'output/harmony-whole-score-units-2026-10-06-r1'
GOLD=Path('K:/Music Composition/docs/handoff/harmony_eval/harmony_benchmark_gold.json')
FIELDS=('selected_path','page_inventory','score_cost','feature_values','feature_availability',
        'actual_harmonic_runs','states_discarded','operations','spans')


def one(entry,arm,output):
    t=perf_counter();path=output/'jobs'/f'{entry["index"]:03d}-{arm}.json'
    module='harmony_whole_score_fast' if arm=='engine' else 'harmony_whole_score_units'
    command=[sys.executable,'-B','-m','musicanote_harness.'+module,'--worker',entry['source_file'],'--output',str(path)]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
    try:
        p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60)
        r=json.loads(path.read_text(encoding='utf-8')) if p.returncode==0 and path.exists() else dict(
            status='process_error',error=p.stderr.decode('utf-8',errors='replace')[-2000:],spans=[])
    except subprocess.TimeoutExpired:r=dict(status='whole_song_timeout',spans=[])
    r.update(title=entry['title'],index=entry['index'],arm=arm,wall_seconds=perf_counter()-t)
    write(path,r);return r


def compare_paths(left,right):
    return [k for k in FIELDS if left.get(k)!=right.get(k)]


def catalog_hash(path):return _hash(json.loads(gzip.decompress(path.read_bytes())))


def run(output):
    if output.exists():raise ValueError('output_exists_no_overwrite')
    if digest(MODEL)!=MODEL_SHA:raise ValueError('model_changed')
    selected=json.loads((OLD/'freeze.json').read_text(encoding='utf-8'))['selected']
    if {e['index'] for e in selected}!={158,110,61,156,211,59}:raise ValueError('cohort_changed')
    code=[Path(__file__),ROOT/'scripts/profile_harmony_whole_score_units.py',
        ROOT/'tests/test_harmony_whole_score_fast.py',ROOT/'docs/harmony/WHOLE_SCORE_PERFORMANCE_PLAN.md']
    code+=sorted((ROOT/'src/musicanote_harness').glob('*.py'))
    artifacts=[OLD/'freeze.json',OLD/'statuses.json',OLD/'baseline-submission.json',GOLD,MODEL]
    artifacts+=sorted((OLD/'jobs').glob('*-engine.json'))
    artifacts+=sorted((OLD/'jobs').glob('*-engine.catalogs.json.gz'))
    profile=output.parent/'profile/profile.json'
    pins={str(p):digest(p) for p in code+artifacts+[profile]+[Path(e['source_file']) for e in selected]}
    output.mkdir(parents=True);(output/'jobs').mkdir()
    write(output/'freeze.json',dict(version=VERSION,selected=selected,source_and_code_pins=pins,
        workers=4,whole_song_seconds=60,retries=0,score_change=False,candidate_change=False,
        beam_width=8,operation_budget=2_000_000,independent_test=False,
        baseline_reused_from_sealed_stage99=True,connection_authorized=False))
    t=perf_counter();statuses={'engine':[],'control':[]}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures=[ex.submit(one,e,a,output) for e in selected for a in statuses]
        for n,future in enumerate(as_completed(futures),1):
            r=future.result();statuses[r['arm']].append(r)
            print(f'[{n}/12] {r["arm"]} {r["title"]}: {r["status"]} {r["wall_seconds"]:.2f}s',flush=True)
    baseline=json.loads((OLD/'baseline-submission.json').read_text(encoding='utf-8'))
    statuses['baseline']=json.loads((OLD/'statuses.json').read_text(encoding='utf-8'))['baseline']
    submissions={'baseline':baseline};prediction_pins={str(OLD/'baseline-submission.json'):digest(OLD/'baseline-submission.json')}
    for arm in ('engine','control'):
        rows=statuses[arm];rows.sort(key=lambda r:r['index']);songs={}
        for r in rows:
            if r['status']=='complete':
                validated_spans(r['spans'],fraction(r['score_duration']));songs[r['title']]=r['spans']
        submissions[arm]=dict(engine=VERSION if arm=='engine' else 'local-beat-0.2.0',benchmark='A',songs=songs)
        p=output/f'{arm}-submission.json';write(p,submissions[arm]);prediction_pins[str(p)]=digest(p)
    write(output/'prediction-freeze.json',dict(predictions=prediction_pins,all_fixed_before_scoring=True))
    write(output/'statuses.json',statuses)
    equivalence=[]
    for r in statuses['engine']:
        control=next(c for c in statuses['control'] if c['index']==r['index'])
        previous=json.loads((OLD/'jobs'/f'{r["index"]:03d}-engine.json').read_text(encoding='utf-8'))
        entry=dict(title=r['title'],index=r['index'],engine_status=r['status'],control_status=control['status'])
        if r['status']=='complete':
            fast_catalog=output/'jobs'/f'{r["index"]:03d}-engine.catalogs.json.gz'
            for label,other,folder,arm in (('control',control,output/'jobs','control'),('previous',previous,OLD/'jobs','engine')):
                if other['status']=='complete':
                    mismatch=compare_paths(r,other)
                    if catalog_hash(fast_catalog)!=catalog_hash(folder/f'{r["index"]:03d}-{arm}.catalogs.json.gz'):
                        mismatch.append('full_catalogs')
                    entry[label+'_mismatches']=mismatch
        equivalence.append(entry)
    write(output/'equivalence.json',dict(rows=equivalence,
        passed=not any(v for row in equivalence for k,v in row.items() if k.endswith('_mismatches'))))
    titles={e['title'] for e in selected};gold=json.loads(GOLD.read_text(encoding='utf-8'))
    gold['songs']=[r for r in gold['songs'] if r['title'] in titles]
    if len(gold['songs'])!=6:raise ValueError('gold_cohort_mismatch')
    write(output/'pilot-gold.json',gold)
    result=score_submissions(output/'pilot-gold.json',submissions,statuses,output/'score.json')
    common=set(submissions['engine']['songs'])&set(submissions['control']['songs'])
    result.update(scope='controlled_performance_six_development_songs',independent_test=False,
        connection_decision='not_authorized_by_development_pilot',
        baseline_timing_measured_this_run=False,
        common_completed={a:aggregate([r for r in report['rows'] if r['title'] in common])
            for a,report in result['reports'].items()},wall_seconds=perf_counter()-t)
    write(output/'score.json',result)
    mismatches=[p for p,h in (pins|prediction_pins).items() if digest(p)!=h]
    write(output/'audit.json',dict(passed=not mismatches,checked=len(pins|prediction_pins),mismatches=mismatches))
    if mismatches:raise ValueError('frozen_run_changed')
    if not json.loads((output/'equivalence.json').read_text(encoding='utf-8'))['passed']:
        raise ValueError('optimization_changed_completed_prediction')
    print(json.dumps({a:r['summary'] for a,r in result['reports'].items()},ensure_ascii=False),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    run(ap.parse_args().output.resolve())
