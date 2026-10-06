"""No-search exact replay of ALL Stage88 Train path receipts.

This is a numerical/traceability proof, not fresh decoding or accuracy gain.
Archived label-created target paths are only replay witnesses, never winners.
"""
import argparse
from pathlib import Path
import json
from time import perf_counter

from . import harmony_exact_beat_cache as cache
from . import harmony_frozen_compute_profile as profile

train = profile.train
s, io, load = profile.s, profile.io, profile.load
VERSION = 'harmony-exact-beat-path-replay-0.1.0'


def check_path(old, new, ids, *, target=False):
    a = old.path_receipt(ids, target=target); b = new.path_receipt(ids, target=target)
    if not train.same_json(a, b): raise ValueError('beat_replay_detailed_receipt_changed')
    train.ledger.flatten(b, new.joint_weights)
    projected = train.prior.prior.prior.verify_projection(new, ids, b)
    runs = cache.joint.context_features.control.completed_runs(new.problem, ids)
    for i in range(1, len(runs)):
        if old.transition_cost(runs, i) != new.transition_cost(runs, i):
            raise ValueError('beat_replay_context_cost_changed')
        left, right = runs[i-1], runs[i]
        args = new.ev, left[0], left[1], right[1], left[2], right[2]
        if cache.temporal.resolution_features(*args) != new.beat_cache.resolution(*args):
            raise ValueError('beat_replay_pair_value_or_details_changed')
    return b, projected


def run(output, profile_root):
    output = Path(output); profile_root = Path(profile_root)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs = {}; artifacts = {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); key = str(p.resolve()); sha = inputs.get(key) or io.digest(p)
        if expected is not None and sha != expected: raise ValueError('beat_replay_input_changed:'+key)
        inputs[key] = sha; return None if raw else load(p)
    diagnosis = read(profile_root/'report.json')
    if (diagnosis['complete'] is not True or diagnosis['model_sha256'] != profile.PINS['model.json.gz']
            or diagnosis['optimization_implemented'] is not False or diagnosis['fit_performed'] is not False):
        raise ValueError('beat_replay_profile_not_sealed')
    for p, sha in (diagnosis['input_hashes'] | diagnosis['artifact_hashes'] | diagnosis['code_hashes']).items():
        read(p, sha, raw=True)
    parent, model, audit = [read(profile.ROOT/n, sha) for n, sha in profile.PINS.items()]
    if parent['complete'] is not True or audit['passed'] is not True:
        raise ValueError('beat_replay_parent_not_sealed')
    ctx = train.context(read)
    weights = train.learning.model_weights(model, ctx['active_pool'], ctx['competitors'], ctx['initial35'],
        ctx['use'], ctx['manifest'], ctx['parent_sha'], train.PINS['training-vectors.json.gz'])
    if parent['cohort'] != [r['sample_id'] for r in ctx['rows']]:
        raise ValueError('beat_replay_cohort_changed')
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for n in ('tests/test_harmony_exact_beat_cache.py', 'tests/test_harmony_frozen_compute_profile.py',
              'scripts/validate_harmony_exact_beat_cache.py', 'scripts/audit_harmony_exact_beat_cache.py'):
        p = Path(n); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(name, value, compressed=False):
        p = output/name; (io.write_packet if compressed else io.write)(p, value)
        key = str(p.resolve()); artifacts[key] = io.digest(p); return key, artifacts[key]
    contract = dict(version=VERSION, model_sha256=profile.PINS['model.json.gz'],
        profile_report_sha256=io.digest(profile_root/'report.json'), cohort=parent['cohort'],
        all_original_train_scopes=True, new_search=False, fit_performed=False,
        source_features_candidates_dp_and_coefficients_unchanged=True,
        original_detailed_receipts_retained=True, target_paths_are_proof_witnesses_not_predictions=True,
        current_dev_inference=False, accuracy_evaluated=False, resource_recovery_claimed=False,
        production_modified=False, purpose='local_noncommercial_research', code_pins=code)
    save(Path('run-contract.json'), contract)
    by_id = {r['sample_id']: r for r in parent['records']}
    records = []; paths = transitions = edges = 0; source_ids = set()
    for i, row in enumerate(ctx['rows'], 1):
        previous = by_id[row['sample_id']]; packet = read(previous['artifact'], previous['sha256'])
        saved, entry, graph, ev, clock, args = train.prior.prior.prior.prior.old.prior.prepare_sample(ctx, row, read)
        for k in train.refresh.SOURCE_FIELDS:
            if not train.same_json(saved[k], packet[k]): raise ValueError('beat_replay_source_changed:'+k)
        old = train.prior.prior.Scorer(graph, ev, weights, **args)
        new = cache.Scorer(graph, ev, weights, **args)
        witnesses = {}
        for name, original in packet['post_search_cost_receipts'].items():
            receipt, count = check_path(old, new, tuple(original['existing_path_ids']), target=name == 'stored_target')
            if not train.same_json(receipt, original): raise ValueError('beat_replay_archived_cost_changed')
            witnesses[name] = dict(path_ids=receipt['existing_path_ids'], cost=receipt['cost'],
                scalar_and_role_transitions=count, detailed_receipt=receipt)
            paths += 1; transitions += count
        proof = {k: saved[k] for k in train.refresh.SOURCE_FIELDS} | dict(witnesses=witnesses,
            historical_case_ref=previous['artifact'], historical_case_sha256=previous['sha256'],
            beat_cache=dict(new.beat_cache.stats, entries=len(new.beat_cache.values)),
            all_receipts_values_masks_pair_details_and_costs_exact=True, model_sha256=profile.PINS['model.json.gz'],
            fresh_prediction_created=False, full_source_not_clipped=True, human_validated=False)
        p, sha = save(Path('cases')/(row['sample_id']+'.json.gz'), proof, True)
        records.append({k: row[k] for k in train.refresh.FIELDS} | dict(artifact=p, sha256=sha,
            witness_count=len(witnesses), transitions=sum(w['scalar_and_role_transitions'] for w in witnesses.values()),
            original_edges=len(graph.edges), beat_cache=proof['beat_cache']))
        source_ids.add(saved['source_ir_content_sha256']); edges += len(graph.edges)
        train.refresh.clear(ev, clock)
        io.write(output/'progress.json', dict(complete=False, finished=i, total=len(ctx['rows']), phase='exact_replay'))
        if i % 10 == 0 or i == len(ctx['rows']): print(f'[exact beat replay {i}/{len(ctx["rows"])}]', flush=True)
    for p, sha in (inputs | artifacts | code).items():
        if io.digest(p) != sha: raise ValueError('beat_replay_final_seal_changed:'+p)
    report = contract | dict(complete=True, records=records, path_witnesses=paths,
        scalar_and_pair_transitions=transitions, original_edges=edges, full_source_packages=len(source_ids),
        input_hashes=inputs, artifact_hashes=artifacts, code_hashes=code, elapsed_seconds=perf_counter()-begun,
        next_required='fresh_all118_train_then_frozen_dev_same20s_2M_cap6_before_adoption')
    io.write(output/'report.json', report)
    io.write(output/'progress.json', dict(complete=True, finished=len(records), total=len(records), phase='sealed',
        report_sha256=io.digest(output/'report.json')))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--profile-root', required=True); a = p.parse_args()
    r = run(a.output, a.profile_root)
    print(json.dumps({k: r[k] for k in ('complete', 'path_witnesses', 'scalar_and_pair_transitions',
        'original_edges', 'full_source_packages', 'elapsed_seconds')}, indent=2))
