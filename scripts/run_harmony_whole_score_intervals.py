"""One input-equivalence audit, then one bounded stage101/102 comparison."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from musicanote_harness.harmony_test_a import write, digest, MODEL, MODEL_SHA, validated_spans, fraction, score_submissions, aggregate
from musicanote_harness.harmony_whole_score_intervals import VERSION
from musicanote_harness.harmony_progression_search import _hash
from run_harmony_whole_score_compiled import catalog_hash, FIELDS

PRIOR = ROOT/'output/harmony-whole-score-phase-2026-10-06-r1/comparison'
SEALED_IR = ROOT/'output/harmony-frozen-test-a-2026-10-06-r1/jobs'
BASE = ROOT/'output/harmony-whole-score-units-2026-10-06-r1'
GOLD = Path('K:/Music Composition/docs/handoff/harmony_eval/harmony_benchmark_gold.json')


def selected():
    rows = json.loads((PRIOR/'freeze.json').read_text(encoding='utf-8'))['selected']
    if {e['index'] for e in rows} != {158,110,61,156,211,59}:
        raise ValueError('cohort_changed')
    return rows


def code_paths():
    return [Path(__file__), ROOT/'scripts/run_harmony_whole_score_compiled.py',
        ROOT/'docs/harmony/WHOLE_SCORE_INTERVAL_PLAN.md',
        ROOT/'tests/test_harmony_whole_score_intervals.py'] + sorted((ROOT/'src/musicanote_harness').glob('*.py'))


def input_audit(output):
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    entries = selected()
    inputs = code_paths() + [PRIOR/'freeze.json'] + [Path(e['source_file']) for e in entries]
    inputs += [SEALED_IR/f'{e["index"]:03d}-engine.ir.json.gz' for e in entries]
    pins = {str(p):digest(p) for p in inputs}
    output.mkdir(parents=True)
    write(output/'freeze.json',dict(version=VERSION,pins=pins,scope='parse_only',selected=entries,
        labels_read=False,retries=0,source_reference='sealed_stage96_full_ir'))
    env = dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
    rows=[]
    # Separate process per import bounds even a stalled parser. No whole-score
    # inference or golden labels are loaded here. Original sealed IR is reused.
    for e in entries:
        target=output/f'{e["index"]:03d}.json';t=perf_counter()
        code=('import sys,json,gzip; from pathlib import Path; from time import perf_counter; '
            'from musicanote_harness.harmony_context_input import read_score; '
            'from musicanote_harness.harmony_test_a import write; '
            'r={}; t=perf_counter(); ir,total,removed=read_score(Path(sys.argv[1]),receipt=r); '
            'write(Path(sys.argv[2]),dict(total=str(total),removed=removed,seconds=perf_counter()-t,lookup=r)); '
            'Path(sys.argv[2]).with_suffix(".ir.json.gz").write_bytes(gzip.compress(json.dumps(ir,ensure_ascii=False,separators=(",",":")).encode(),mtime=0))')
        try:
            proc=subprocess.run([sys.executable,'-B','-c',code,e['source_file'],str(target)],
                cwd=ROOT,env=env,capture_output=True,timeout=60)
            if proc.returncode: raise ValueError(proc.stderr.decode('utf-8',errors='replace')[-2000:])
            actual=json.loads(gzip.decompress(target.with_suffix('.ir.json.gz').read_bytes()))
            original=json.loads(gzip.decompress((SEALED_IR/f'{e["index"]:03d}-engine.ir.json.gz').read_bytes()))
            receipt=json.loads(target.read_text(encoding='utf-8'))
            # Exact all-fields representation, not just musical note counts.
            different=[k for k in set(original)|set(actual) if original.get(k)!=actual.get(k)]
            row=dict(index=e['index'],title=e['title'],status='pass' if not different else 'mismatch',
                original_ir_sha256=_hash(original),new_ir_sha256=_hash(actual),
                mismatched_top_level_fields=different,**receipt)
        except (ValueError,subprocess.TimeoutExpired) as exc:
            row=dict(index=e['index'],title=e['title'],status='error',error=str(exc))
        row['process_wall_seconds']=perf_counter()-t;rows.append(row)
        print(f'input {e["index"]}: {row["status"]} {row["process_wall_seconds"]:.2f}s',flush=True)
    changed=[p for p,h in pins.items() if digest(p)!=h]
    result=dict(passed=not changed and all(r['status']=='pass' for r in rows),rows=rows,
        checked=len(pins),mismatches=changed)
    write(output/'audit.json',result)
    if not result['passed']: raise ValueError('input_ir_equivalence_failed')


def one(entry, arm, output):
    path=output/'jobs'/f'{entry["index"]:03d}-{arm}.json';t=perf_counter()
    invoke=('from musicanote_harness import harmony_whole_score_intervals as m; '
            'm.worker(Path(sys.argv[1]),Path(sys.argv[2]))') if arm=='engine' else (
            'from musicanote_harness import harmony_phase_checkpoint as m; '
            'm.worker(Path(sys.argv[1]),Path(sys.argv[2]),implementation="compiled")')
    code=('import faulthandler,sys; from pathlib import Path; '
        'faulthandler.enable(); faulthandler.dump_traceback_later(20,repeat=True); '+invoke+
        '; faulthandler.cancel_dump_traceback_later()')
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
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    if digest(MODEL)!=MODEL_SHA: raise ValueError('model_changed')
    entries=selected();audit_folder=output.parent/'inputs'
    audit=json.loads((audit_folder/'audit.json').read_text(encoding='utf-8'))
    if not audit['passed'] or {r['index'] for r in audit['rows']}!={e['index'] for e in entries}:
        raise ValueError('input_audit_not_passed')
    input_freeze=json.loads((audit_folder/'freeze.json').read_text(encoding='utf-8'))
    if any(digest(p)!=h for p,h in input_freeze['pins'].items()): raise ValueError('audited_input_changed')
    artifacts=[PRIOR/'freeze.json',PRIOR/'audit.json',PRIOR/'equivalence.json',
        BASE/'baseline-submission.json',BASE/'statuses.json',GOLD,MODEL]
    artifacts+=sorted((PRIOR/'jobs').glob('*-engine.json'))+sorted((PRIOR/'jobs').glob('*-engine.catalogs.json.gz'))
    artifacts+=sorted(audit_folder.glob('*.json'))+sorted(audit_folder.glob('*.ir.json.gz'))
    pins={str(p):digest(p) for p in code_paths()+artifacts+[Path(e['source_file']) for e in entries]}
    output.mkdir(parents=True);(output/'jobs').mkdir()
    write(output/'freeze.json',dict(version=VERSION,selected=entries,pins=pins,workers=4,seconds=60,
        retries=0,score_change=False,candidate_change=False,beam_width=8,operation_budget=2_000_000,
        page_cells=12,direct_scorer_original_stage99=True,independent_test=False,connection_authorized=False,
        baseline_reused_from_sealed_stage99=True,atomic_checkpoints_and_traces_both_arms=True,
        input_audit=str(audit_folder/'audit.json'),control='stage101_compiled_original_read_score'))
    t=perf_counter();statuses={'engine':[],'control':[]}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures=[ex.submit(one,e,a,output) for e in entries for a in statuses]
        for n,future in enumerate(as_completed(futures),1):
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
        submissions[arm]=dict(engine=VERSION if arm=='engine' else 'local-beat-0.2.2-compiled',benchmark='A',songs=songs)
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
            for label,other,folder,arm in (('control',control,output/'jobs','control'),('previous101',previous,PRIOR/'jobs','engine')):
                if other['status']=='complete':
                    diff=[k for k in FIELDS if r.get(k)!=other.get(k)]
                    if catalog_hash(output/'jobs'/f'{r["index"]:03d}-engine.catalogs.json.gz')!=catalog_hash(folder/f'{r["index"]:03d}-{arm}.catalogs.json.gz'):
                        diff.append('full_catalogs')
                    row[label+'_mismatches']=diff
            ir=json.loads(gzip.decompress((output/'jobs'/f'{r["index"]:03d}-engine.ir.json.gz').read_bytes()))
            row['source_ir_matches_audited']=_hash(ir)==next(s['new_ir_sha256'] for s in audit['rows'] if s['index']==r['index'])
        comparisons.append(row)
    equivalent=not any(v for row in comparisons for k,v in row.items() if k.endswith('_mismatches')) and all(
        row.get('source_ir_matches_audited',True) for row in comparisons)
    write(output/'equivalence.json',dict(passed=equivalent,rows=comparisons))
    gold=json.loads(GOLD.read_text(encoding='utf-8'));titles={e['title'] for e in entries}
    gold['songs']=[s for s in gold['songs'] if s['title'] in titles]
    if len(gold['songs'])!=6: raise ValueError('gold_cohort_changed')
    write(output/'pilot-gold.json',gold)
    result=score_submissions(output/'pilot-gold.json',submissions,statuses,output/'score.json')
    common=set(submissions['engine']['songs'])&set(submissions['control']['songs'])
    result.update(scope='single_controlled_interval_and_static_input_six_development_songs',independent_test=False,
        connection_decision='not_authorized_by_development_pilot',baseline_timing_measured_this_run=False,
        common_completed={a:aggregate([r for r in report['rows'] if r['title'] in common]) for a,report in result['reports'].items()},
        wall_seconds=perf_counter()-t)
    write(output/'score.json',result)
    changed=[p for p,h in (pins|prediction_pins).items() if digest(p)!=h]
    write(output/'audit.json',dict(passed=not changed,checked=len(pins|prediction_pins),mismatches=changed))
    if changed: raise ValueError('frozen_input_changed')
    if not equivalent: raise ValueError('interval_prediction_changed')
    print(json.dumps({a:r['summary'] for a,r in result['reports'].items()},ensure_ascii=False),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--audit-inputs',action='store_true');args=ap.parse_args()
    (input_audit if args.audit_inputs else run)(args.output.resolve())
