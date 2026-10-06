"""Train-only computational diagnosis of the sealed Stage88 score.

Instrumentation changes runtime: these are NOT speed or accuracy benchmarks.
No fit, new candidate, label-conditioned pruning or extended resource guard.
"""
import argparse
import cProfile
from collections import Counter
from pathlib import Path
import json
import pstats
from time import perf_counter

from . import harmony_ordinal_protection_trial as train

VERSION = 'harmony-frozen-compute-profile-0.1.0'
ROOT = Path('K:/Music Analysis/output/harmony-ordinal-protection-2026-10-06-r1')
PINS = {
    'report.json': '8dad89e1130a0e2c742172a942a72732f0d09e3d0d7a2abc0ed9b45041f2435e',
    'model.json.gz': 'b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38',
    'post-seal-audit.json': '6e6eee39d55d0b73250b748ad50ee964833071ae629b86c3d1705c605b24227e',
}
s, io, load = train.s, train.io, train.load


def cohort(records, sizes, controls=4):
    """All historical wall scopes plus largest completed in distinct families.

    No correctness, reference labels, new runtime or profile outcome in choice.
    """
    if type(controls) is not int or controls <= 0:
        raise ValueError('invalid_control_count')
    ids = [r['sample_id'] for r in records]
    if len(ids) != len(set(ids)) or set(sizes) != set(ids):
        raise ValueError('profile_inventory_changed')
    if any(type(n) is not int or n <= 0 for n in sizes.values()):
        raise ValueError('invalid_graph_size')
    walls = [r for r in records if r['selected_ids'] is None]
    if any(r['status'] != 'context_wall_budget_abstention' for r in walls):
        raise ValueError('unexpected_historical_abstention')
    completed = sorted((r for r in records if r['selected_ids'] is not None),
                       key=lambda r: (-sizes[r['sample_id']], r['sample_id']))
    seen = set(); chosen = []
    for r in completed:
        if r['work_family_id'] in seen: continue
        seen.add(r['work_family_id']); chosen.append(r)
        if len(chosen) == controls: break
    if len(chosen) != controls: raise ValueError('insufficient_distinct_completed_controls')
    return [(r, 'historical_wall') for r in walls]+[(r, 'completed_control') for r in chosen]


def profile_rows(profiler):
    rows = []
    for (file, line, name), (primitive, calls, own, cumulative, callers) in pstats.Stats(profiler).stats.items():
        rows.append(dict(file=file, line=line, function=name, primitive_calls=primitive,
            calls=calls, own_seconds=own, cumulative_seconds=cumulative,
            callers=[dict(file=k[0], line=k[1], function=k[2], stats=list(v))
                     for k, v in sorted(callers.items())]))
    return sorted(rows, key=lambda r: (-r['cumulative_seconds'], r['file'], r['line'], r['function']))


def snapshot(sc):
    si = sc.scalar_index
    return dict(scalar=dict(si.stats) if si else {}, scalar_cache_entries=len(si.cache) if si else 0,
        scalar_domain_entries=len(si.domains) if si else 0,
        figure_domain_entries=len(si.figures) if si else 0,
        role_cache_entries=len(sc.role_index.cache),
        full_source_events=len(sc.ev.source.events), context_figures=len(sc.context.figures))


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs = {}; artifacts = {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); key = str(p.resolve())
        # Repeated references reuse a digest; final seal independently rehashes.
        sha = inputs.get(key) or io.digest(p)
        if expected is not None and sha != expected: raise ValueError('profile_input_changed:'+key)
        inputs[key] = sha
        return None if raw else load(p)
    report, model, audit = [read(ROOT/n, sha) for n, sha in PINS.items()]
    if (report['complete'] is not True or audit['passed'] is not True
            or audit['report_sha256'] != PINS['report.json']
            or report['model_sha256'] != PINS['model.json.gz']
            or report['current_dev_reconstructed_or_used'] is not False):
        raise ValueError('profile_parent_not_sealed')
    for p, sha in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
        read(p, sha, raw=True)
    ctx = train.context(read)
    weights = train.learning.model_weights(model, ctx['active_pool'], ctx['competitors'],
        ctx['initial35'], ctx['use'], ctx['manifest'], ctx['parent_sha'], train.PINS['training-vectors.json.gz'])
    if [r['sample_id'] for r in ctx['rows']] != report['cohort']:
        raise ValueError('profile_train_cohort_changed')
    sizes = {r['sample_id']: read(r['artifact'], r['sha256'])['original_edge_count'] for r in report['records']}
    selected = cohort(report['records'], sizes)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for n in ('tests/test_harmony_frozen_compute_profile.py',):
        p = Path(n); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(name, value, compressed=False):
        path = output/name
        (io.write_packet if compressed else io.write)(path, value)
        key = str(path.resolve()); artifacts[key] = io.digest(path)
        return key, artifacts[key]
    contract = dict(version=VERSION, model_sha256=PINS['model.json.gz'],
        parent_report_sha256=PINS['report.json'], original_train_scopes=len(report['records']),
        cohort=[dict(sample_id=r['sample_id'], group=g, original_edges=sizes[r['sample_id']]) for r, g in selected],
        selection='all_historical_walls_plus_4_largest_completed_graphs_in_distinct_work_families',
        wall_seconds=train.prior.WALL_SECONDS, transition_budget=s.fresh.BUDGET, raw_segment_cap=6,
        same_candidates_and_scores=True, cprofile_runtime_instrumented=True,
        timings_are_not_controlled_speed_benchmark=True, accuracy_claimed=False,
        current_dev_inference=False, fit_performed=False, work_specific_rules=False,
        production_modified=False, purpose='local_noncommercial_research', code_pins=code)
    save(Path('run-contract.json'), contract)
    by_id = {r['sample_id']: r for r in ctx['rows']}; records = []
    for i, (previous, group) in enumerate(selected, 1):
        row = by_id[previous['sample_id']]; tick = perf_counter()
        saved, entry, graph, ev, clock, args = train.prior.prior.prior.prior.old.prior.prepare_sample(ctx, row, read)
        preparation = perf_counter()-tick
        tick = perf_counter(); sc = train.prior.prior.Scorer(graph, ev, weights, **args)
        construction = perf_counter()-tick
        profiler = cProfile.Profile(); profiler.enable()
        try: result = train.select(sc, model, PINS['model.json.gz'])
        finally: profiler.disable()
        calls = profile_rows(profiler)
        packet = {k: saved[k] for k in train.refresh.SOURCE_FIELDS} | dict(result=result,
            model_sha256=PINS['model.json.gz'], historical_case_ref=previous['artifact'],
            historical_case_sha256=previous['sha256'], group=group,
            preparation_seconds=preparation, scorer_construction_seconds=construction,
            profile=calls, caches=snapshot(sc), full_source_not_clipped=True,
            source_labels_used_for_selection=False, human_validated=False)
        path, sha = save(Path('cases')/(row['sample_id']+'.json.gz'), packet, True)
        item = {k: row[k] for k in train.refresh.FIELDS} | dict(group=group, artifact=path, sha256=sha,
            original_edges=len(graph.edges), status=result['status'],
            selected_ids=s.fresh.path_ids(result['selected']) if result['selected'] else None,
            historical_selected_ids=previous['selected_ids'],
            elapsed_seconds=result['resource_guard']['elapsed_seconds'],
            preparation_seconds=preparation, scorer_construction_seconds=construction,
            caches=packet['caches'], top_cumulative=calls[:15],
            top_own=sorted(calls, key=lambda r: -r['own_seconds'])[:15])
        records.append(item); train.refresh.clear(ev, clock)
        io.write(output/'progress.json', dict(complete=False, finished=i, total=len(selected), phase='profile',
            last_sample=row['sample_id'], elapsed_seconds=perf_counter()-begun))
        print(f'[profile {i}/{len(selected)}] {row["sample_id"]}: {result["status"]}', flush=True)
    for p, sha in (inputs | artifacts | code).items():
        if io.digest(p) != sha: raise ValueError('profile_final_seal_changed:'+p)
    final = contract | dict(complete=True, records=records,
        status_counts=dict(Counter(r['status'] for r in records)),
        full_source_packages=len({read(r['artifact'], r['sha256'])['source_ir_content_sha256'] for r in records}),
        input_hashes=inputs, artifact_hashes=artifacts, code_hashes=code,
        elapsed_seconds=perf_counter()-begun, optimization_implemented=False,
        accuracy_evaluated=False, independent_test=False)
    io.write(output/'report.json', final)
    io.write(output/'progress.json', dict(complete=True, finished=len(records), total=len(selected), phase='sealed',
        report_sha256=io.digest(output/'report.json'), elapsed_seconds=perf_counter()-begun))
    return final


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'status_counts', 'full_source_packages', 'elapsed_seconds')}, indent=2))
