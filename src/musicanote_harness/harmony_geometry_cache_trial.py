"""Replay every saved breadth survey with geometry reuse and exact equality.

Earlier continuous/contrast/lattice stages are frozen inputs, NOT rerun here.
This is an implementation-equivalence/performance trial, not musical accuracy.
"""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_progression_evidence_trial import digest, load, write
from .harmony_voice_geometry_cache import VoiceGeometryCache, fingerprint
from . import harmony_candidate_relation_survey as relations
from . import harmony_hold_change_context as hold_change

VERSION = 'geometry-cache-equivalence-trial-0.1.1'


def logical_hash(value):
    return fingerprint(value)


def compare_sample(ir, saved):
    before = fingerprint(ir)
    saved_before = fingerprint(saved)
    planned = relations.plan(saved['stages']['lattice'])
    policy = relations.geometry_cache_policy(saved['stages']['lattice'], planned)
    active = policy['enabled'] and planned['status'] == 'ready' and len(planned['pairs']) <= 512
    cache = VoiceGeometryCache(ir) if active else None
    started = perf_counter()
    observed = relations.run(saved['stages']['lattice'], ir, temporal=True,
                             geometry_cache=cache)
    relation_seconds = perf_counter()-started
    final = hold_change.run(saved['stages']['lattice'], observed, ir)
    if fingerprint(ir) != before:
        raise ValueError('cache_replay_mutated_ir')
    if fingerprint(saved) != saved_before:
        raise ValueError('cache_replay_mutated_frozen_stages')
    checks = {'relations_equal':observed == saved['stages']['relations'],
              'hold_change_equal':final == saved['stages']['hold_change']}
    return {'version':VERSION, 'sample':deepcopy(saved['sample']),
            'status':'equal' if all(checks.values()) else 'semantic_mismatch',
            'checks':checks, 'cache':cache.stats() if cache is not None else {
                'prepares':0,'span_hits':0,'span_misses':0,'evictions':0,
                'cached_spans':0,'harmonic_results_cached':False},
            'cache_policy':policy, 'cache_active':active,
            'relation_seconds':relation_seconds,
            'reference_logical_sha256':{stage:logical_hash(saved['stages'][stage])
                                       for stage in ('relations', 'hold_change')},
            'observed_logical_sha256':{'relations':logical_hash(observed),
                                      'hold_change':logical_hash(final)},
            'relations':observed, 'hold_change':final,
            'accuracy_measured':False, 'source_labels_used':False,
            'selected':None, 'production_modified':False}


def benchmark(ir, lattice, repeats=2):
    """Same input/code, opposite order in two rounds, no old full-run comparison."""
    if type(repeats) is not int or repeats < 1:
        raise ValueError('invalid_benchmark_repeats')
    before = fingerprint(ir); lattice_before = fingerprint(lattice)
    rounds = []; expected = None
    for round_index in range(repeats):
        order = (False, True) if round_index % 2 == 0 else (True, False)
        timings = {}
        for cached in order:
            started = perf_counter()
            result = relations.run(lattice, ir, temporal=True, use_geometry_cache=cached)
            timings['cached' if cached else 'uncached'] = perf_counter()-started
            if fingerprint(ir) != before or fingerprint(lattice) != lattice_before:
                raise ValueError('benchmark_mutated_input')
            if expected is None:
                expected = result
            elif result != expected:
                raise ValueError('benchmark_semantic_mismatch')
        rounds.append({'round':round_index, 'order':['cached' if x else 'uncached' for x in order],
                       'seconds':timings})
    if fingerprint(ir) != before:
        raise ValueError('benchmark_mutated_ir')
    cached = sum(r['seconds']['cached'] for r in rounds)/repeats
    uncached = sum(r['seconds']['uncached'] for r in rounds)/repeats
    return {'rounds':rounds, 'cached_mean_seconds':cached, 'uncached_mean_seconds':uncached,
            'uncached_over_cached':uncached/cached if cached else None,
            'all_results_equal':True, 'cache_policy':relations.geometry_cache_policy(lattice),
            'cached_mode':'automatic geometry-only reuse guard',
            'scope':'same relation survey only, not full analysis or UI latency',
            'musical_accuracy_measured':False}


def inputs(reference):
    """Check the frozen reference/policy and include ALL selected windows."""
    report_path, plan_path, contract_path = (reference/name for name in
        ('report.json', 'frozen-plan.json', 'run-contract.json'))
    report, plan, original_contract = map(load, (report_path, plan_path, contract_path))
    if report.get('complete') is not True or report.get('inputs_unchanged') is not True:
        raise ValueError('incomplete_or_changed_reference')
    if digest(plan_path) != original_contract['frozen_plan_sha256']:
        raise ValueError('reference_plan_changed')
    if report.get('source_labels_used') is not False or report.get('accuracy_measured') is not False:
        raise ValueError('invalid_label_blind_reference')
    hashes = {str(p.resolve()):digest(p) for p in (report_path, plan_path, contract_path)}
    hashes.update(original_contract['input_hashes'])
    packages = {}; chosen = {}
    for item in plan['packages']:
        source = item['source']; policy = source['manifest_entry']
        if policy['split'] not in ('train', 'dev') or policy['rights']['internal_research_use'] is not True:
            raise ValueError('protected_or_unauthorized_reference')
        if source['pitch_policy']['harmonic_replay_allowed'] is not True:
            raise ValueError('unconverted_transposition_reference')
        pair = item['pair_id']
        if pair in packages:
            raise ValueError('duplicate_reference_package')
        packages[pair] = item
        hashes.update(source['source_files'])
        hashes.update({source['preparation_path']:source['preparation_sha256'],
                       source['original_ir_path']:source['ir_sha256'],
                       source['frozen_ir_path']:source['ir_sha256']})
        for row in item['plan']['selected_samples']:
            key = (pair, row['sample']['sample_id'], row['plan_index'])
            if key in chosen:
                raise ValueError('duplicate_frozen_sample')
            chosen[key] = row['sample']
    seen = set()
    for row in report['records']:
        key = (row['pair_id'], row['sample_id'], row['plan_index'])
        if key not in chosen or key in seen or row['status'] == 'execution_error':
            raise ValueError('invalid_reference_sample')
        seen.add(key); hashes[row['artifact']] = row['sha256']
    if seen != set(chosen):
        raise ValueError('reference_sample_coverage_mismatch')
    for path, expected in hashes.items():
        if digest(Path(path)) != expected:
            raise ValueError('reference_input_changed:' + path)
    return report, packages, chosen, hashes


def load_hashed_json(path, expected, compressed=False):
    payload = Path(path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError('consumed_input_hash_mismatch:' + str(path))
    return json.loads(gzip.decompress(payload) if compressed else payload)


def run(reference, output, benchmark_samples=2):
    reference, output = Path(reference), Path(output)
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    if type(benchmark_samples) is not int or benchmark_samples < 0:
        raise ValueError('invalid_benchmark_samples')
    report, packages, chosen, hashes = inputs(reference)
    code = {str(p.resolve()):digest(p) for p in Path(__file__).parent.glob('*.py')}
    output.mkdir(parents=True, exist_ok=False)
    write(output/'run-contract.json', {'version':VERSION, 'reference':str(reference.resolve()),
        'input_hashes':hashes, 'code_hashes':code, 'source_labels_used':False,
        'earlier_stages_recomputed':False, 'protected_data_promoted':False,
        'benchmark_selection':'first nonempty ready survey in frozen order per collection; bounded count',
        'benchmark_samples':benchmark_samples, 'production_modified':False})
    records = []; benchmarks = []; benchmarked = set(); current_pair = None
    ir = None; started = perf_counter()
    for index, row in enumerate(report['records'], 1):
        pair = row['pair_id']; item = packages[pair]
        if pair != current_pair:
            ir = load_hashed_json(item['source']['frozen_ir_path'], item['source']['ir_sha256'])
            current_pair = pair
        original = load_hashed_json(row['artifact'], row['sha256'], compressed=True)
        if original['sample'] != chosen[(pair, row['sample_id'], row['plan_index'])]:
            raise ValueError('reference_sample_identity_changed')
        observed = compare_sample(ir, original)
        destination = output/'samples'/Path(row['artifact']).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(gzip.compress(json.dumps(observed, ensure_ascii=False,
            separators=(',', ':')).encode('utf-8'), mtime=0))
        records.append({'pair_id':pair, 'sample_id':row['sample_id'],
            'plan_index':row['plan_index'], 'status':observed['status'], 'checks':observed['checks'],
            'cache':observed['cache'], 'cache_policy':observed['cache_policy'],
            'cache_active':observed['cache_active'], 'relation_seconds':observed['relation_seconds'],
            'artifact':str(destination.resolve()), 'sha256':digest(destination),
            'source_artifact_sha256':row['sha256']})
        collection = item['source']['manifest_entry']['collection_id']
        if (len(benchmarks) < benchmark_samples and collection not in benchmarked
            and row.get('executed_relation_pairs', 0) > 0):
            benchmarks.append({'pair_id':pair, 'sample_id':row['sample_id'],
                               **benchmark(ir, original['stages']['lattice'])})
            benchmarked.add(collection)
        if index % 20 == 0 or index == len(report['records']):
            print(f'[{index}/{len(report["records"])}] cache equivalence replay', flush=True)
            write(output/'progress.json', {'complete':False, 'records':records})
    changed = [path for path, expected in {**hashes, **code}.items() if digest(Path(path)) != expected]
    current_code = {str(p.resolve()) for p in Path(__file__).parent.glob('*.py')}
    changed.extend(sorted(current_code.symmetric_difference(code)))
    result = {'version':VERSION, 'complete':True, 'replayed_surveys':len(records),
        'unique_packages':len(packages), 'unique_work_families':report['unique_work_families'],
        'status_counts':dict(Counter(r['status'] for r in records)),
        'cache_active_surveys':sum(r['cache_active'] for r in records),
        'cache_totals':{key:sum(r['cache'][key] for r in records)
                        for key in ('prepares', 'span_hits', 'span_misses', 'evictions')},
        'records':records, 'benchmarks':benchmarks, 'changed_input_paths':changed,
        'inputs_unchanged':not changed, 'earlier_stages_recomputed':False,
        'accuracy_measured':False, 'source_labels_used':False,
        'production_modified':False, 'elapsed_seconds':perf_counter()-started}
    write(output/'report.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--benchmark-samples', type=int, default=2)
    args = p.parse_args(); result = run(args.reference, args.output, args.benchmark_samples)
    print(json.dumps({k:result[k] for k in ('replayed_surveys', 'status_counts', 'cache_totals', 'inputs_unchanged')}))
    if not result['inputs_unchanged'] or set(result['status_counts']) != {'equal'}:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
