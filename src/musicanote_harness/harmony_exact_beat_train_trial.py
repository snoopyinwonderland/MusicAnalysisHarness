"""Fresh ALL-Train decoding with the sealed exact beat cache and Stage88 model.

No fitting, profiling, extended guard, new candidate, retry or deployment.
Seal every prediction before post-search reference evaluation. Historical
completed winners must retain IDs, cost, evidence and DP operation counts.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from . import harmony_exact_beat_replay as proof
from . import harmony_common_benchmark as benchmark

train, cache, io, load = proof.train, proof.cache, proof.io, proof.load
VERSION = 'harmony-exact-beat-all-train-trial-0.1.0'
PROOF_ROOT = Path('K:/Music Analysis/output/harmony-exact-beat-replay-2026-10-06-r1')
PROOF_PINS = {
    'report.json': '0257a754d782c81131e64f1f655b9b909b2d2b1cd180321df9adc080db65280a',
    'post-seal-audit.json': '7b82e634c0c5ba39ff43704174b8d0101758edd578f514a745a9d487259718bd',
}
FREEZE_SHA = '6ff22448afa8c3c2db45349ff7660883a08f7b31c187aa299bc4bb41e5f03d6e'
PRIOR_VALIDATION_SHA = '3a32e1e5eca188ebcca922bc285ed3e2ab85bc693ea7dbd013a192fa5d7255cc'
prepare = train.prior.prior.prior.prior.old.prior.prepare_sample


def context(read):
    report, audit = [read(PROOF_ROOT/n, sha) for n, sha in PROOF_PINS.items()]
    if (report['complete'] is not True or audit['passed'] is not True
            or audit['report_sha256'] != PROOF_PINS['report.json']
            or report['model_sha256'] != proof.profile.PINS['model.json.gz']
            or report['new_search'] is not False or report['fit_performed'] is not False):
        raise ValueError('beat_train_proof_not_sealed')
    for p, sha in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
        read(p, sha, raw=True)
    parent, model, parent_audit = [read(proof.profile.ROOT/n, sha) for n, sha in proof.profile.PINS.items()]
    freeze = read(proof.profile.ROOT/'model-freeze.json', FREEZE_SHA)
    if (parent['complete'] is not True or parent_audit['passed'] is not True
            or parent_audit['report_sha256'] != proof.profile.PINS['report.json']
            or freeze['model_sha256'] != proof.profile.PINS['model.json.gz']
            or freeze['all_35_weights_frozen_during_selection'] is not True or freeze['dev_used'] is not False):
        raise ValueError('beat_train_parent_not_sealed')
    ctx = train.context(read)
    ids = [r['sample_id'] for r in ctx['rows']]
    if (ids != parent['cohort'] or ids != report['cohort'] or len(ids) != 118
            or len(set(ids)) != len(ids) or any(r['split'] != 'train' for r in ctx['rows'])):
        raise ValueError('beat_train_original_cohort_changed')
    ctx['beat_weights'] = train.learning.model_weights(model, ctx['active_pool'], ctx['competitors'],
        ctx['initial35'], ctx['use'], ctx['manifest'], ctx['parent_sha'], train.PINS['training-vectors.json.gz'])
    ctx['beat_model'] = model; ctx['beat_parent'] = parent
    ctx['beat_previous'] = {r['sample_id']: r for r in parent['records']}
    ctx['beat_proof'] = report
    return ctx


def cache_snapshot(sc):
    return dict(sc.beat_cache.stats, entries=len(sc.beat_cache.values))


def select(sc, model, model_sha, **guard):
    result = train.refresh.parent.select(sc, model['model_id'], **guard)
    result.pop('joint_balance_contract', None)
    result['ordinal_protection_contract'] = dict(version=train.VERSION,
        all_35_weights_frozen_during_selection=True, source_features_and_graph_unchanged=True,
        source_labels_used=False, production_modified=False)
    result['frozen_model_ref'] = dict(model_id=model['model_id'], model_sha256=model_sha,
        fit_performed_before_selection=True, fit_performed_this_selection=False,
        all_35_weights_frozen=True, existing_26_frozen_during_fit=False,
        source_labels_used_for_selection=False, operational_promotion=False)
    # An interrupted decode never reaches cache.Scorer.decode's return. Keep
    # its cache snapshot as diagnostics, never as a partial prediction.
    result['exact_beat_cache_contract'] = dict(version=cache.VERSION,
        same_sealed_dp_bytecode=True, changed_dependency='resolution_features.beat_extent',
        source_local_cache=True, harmonic_signature_not_in_beat_key=True,
        detailed_receipt_and_independent_winner_check_unchanged=True,
        unknown_meter_remains_null=True, new_candidates=False,
        coefficients_changed=False, production_modified=False)
    result['exact_beat_cache_diagnostics'] = cache_snapshot(sc)
    if result['selected']:
        result['selected']['proposal_id'] = 'ordinal_protection_'+train.learning.use.content_hash(
            [train.s.fresh.path_ids(result['selected']), model_sha])[:24]
    return result


def assert_source(saved, packet):
    if not all(train.same_json(saved[k], packet[k]) for k in train.refresh.SOURCE_FIELDS):
        raise ValueError('beat_train_original_source_changed')


def replay(old, new, original, result):
    receipts = {}; projections = 0
    for name, archived in original['post_search_cost_receipts'].items():
        receipt, count = proof.check_path(old, new, tuple(archived['existing_path_ids']), target=name == 'stored_target')
        if not train.same_json(receipt, archived): raise ValueError('beat_train_archived_cost_changed')
        receipts['historical_'+name] = receipt; projections += count
    if result['selected']:
        ids = train.s.fresh.path_ids(result['selected'])
        receipt, count = proof.check_path(old, new, ids)
        if (not train.same_json(receipt, result['selected']['context_score'])
                or receipt['cost'] != result['selected']['score_cost']):
            raise ValueError('beat_train_fresh_cost_changed')
        receipts['fresh'] = receipt; projections += count
    return receipts, projections


def record(row, packet, path, sha, previous):
    result = packet['result']; selected = result['selected']
    return {k: row[k] for k in train.refresh.FIELDS} | dict(artifact=path, sha256=sha,
        status=result['status'], selected_ids=train.s.fresh.path_ids(selected) if selected else None,
        evaluation=packet['evaluation'], prior_selected_ids=previous['selected_ids'],
        prior_evaluation=previous['evaluation'], prior_status=previous['status'],
        same_completed_winner=packet['same_completed_winner'],
        elapsed_seconds=result['resource_guard']['elapsed_seconds'],
        preparation_seconds=packet['preparation_seconds'], scorer_construction_seconds=packet['scorer_construction_seconds'],
        beat_cache=result['exact_beat_cache_diagnostics'], original_edges=packet['original_edge_count'])


def summaries(records):
    prior = [r | dict(evaluation=r['prior_evaluation']) for r in records]
    common = [r for r in records if r['prior_selected_ids'] is not None and r['selected_ids'] is not None]
    recovered = [r for r in records if r['prior_selected_ids'] is None and r['selected_ids'] is not None]
    lost = [r for r in records if r['prior_selected_ids'] is not None and r['selected_ids'] is None]
    return dict(all_original=dict(historical=benchmark.summarize(prior), cached=benchmark.summarize(records)),
        common_completed=dict(count=len(common), historical=benchmark.summarize(
            [r | dict(evaluation=r['prior_evaluation']) for r in common]), cached=benchmark.summarize(common)),
        resources=dict(historical_status_counts=dict(Counter(r['prior_status'] for r in records)),
            cached_status_counts=dict(Counter(r['status'] for r in records)),
            common_completed_identical=sum(r['same_completed_winner'] for r in common),
            recovered_previous_abstentions=len(recovered), previous_completion_now_abstention=len(lost),
            recovered_ids=[r['sample_id'] for r in recovered], lost_ids=[r['sample_id'] for r in lost],
            recovered_reference_hit=sum(r['evaluation']['selected_hit'] is True for r in recovered),
            recovered_reference_wrong=sum(r['evaluation']['selected_hit'] is False for r in recovered),
            recovered_reference_partial=sum(r['evaluation']['selected_hit'] is None for r in recovered),
            lost_previous_reference_hit=sum(r['prior_evaluation']['selected_hit'] is True for r in lost)),
        musical_changes_on_common=dict(
            changed_paths=sum(not train.same_json(r['selected_ids'], r['prior_selected_ids']) for r in common),
            newly_correct=sum(r['evaluation']['selected_hit'] is True and r['prior_evaluation']['selected_hit'] is False for r in common),
            lost_correct=sum(r['evaluation']['selected_hit'] is False and r['prior_evaluation']['selected_hit'] is True for r in common)),
        all_abstentions_remain_in_denominator=True, current_training_scopes_not_independent_test=True,
        historical_wall_timings_not_controlled_speed_benchmark=True)


def run(output, validation):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs = {}; artifacts = {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); key = str(p.resolve()); sha = inputs.get(key) or io.digest(p)
        if expected is not None and sha != expected: raise ValueError('beat_train_input_changed:'+key)
        inputs[key] = sha; return None if raw else load(p)
    checked = read(validation)
    if (checked['passed'] is not True or checked['previous_validation_sha256'] != PRIOR_VALIDATION_SHA
            or 'test_harmony_exact_beat_train_trial' not in checked['test_modules']):
        raise ValueError('beat_train_validation_not_passed')
    ctx = context(read); model = ctx['beat_model']; weights = ctx['beat_weights']
    model_sha = proof.profile.PINS['model.json.gz']
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for n in ('tests/test_harmony_exact_beat_train_trial.py', 'scripts/validate_harmony_exact_beat_train.py',
              'scripts/audit_harmony_exact_beat_train.py'):
        p = Path(n); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'predictions').mkdir(); (output/'cases').mkdir()
    def save(name, value, compressed=False):
        p = output/name; (io.write_packet if compressed else io.write)(p, value)
        key = str(p.resolve()); artifacts[key] = io.digest(p); return key, artifacts[key]
    contract = dict(version=VERSION, cohort=[r['sample_id'] for r in ctx['rows']], model_sha256=model_sha,
        historical_report_sha256=proof.profile.PINS['report.json'], proof_report_sha256=PROOF_PINS['report.json'],
        cache_version=cache.VERSION, fit_performed=False, all_35_coefficients_unchanged=True,
        source_candidates_dp_cost_and_operation_unit_unchanged=True,
        wall_seconds=20, transition_budget=2_000_000, raw_segment_cap=6,
        cprofile_instrumentation=False, parallel_heavy_work_during_selection=False,
        evaluation_after_all_predictions_sealed=True, reference_conditioned_prediction=False,
        current_dev_inference=False, work_specific_rules=False, production_modified=False,
        operational_weights_changed=False, independent_accuracy_claimed=False,
        purpose='local_noncommercial_research', code_pins=code)
    save(Path('run-contract.json'), contract)
    predictions = []; sources = set(); edges = completed = 0
    for i, row in enumerate(ctx['rows'], 1):
        previous = ctx['beat_previous'][row['sample_id']]; historical = read(previous['artifact'], previous['sha256'])
        tick = perf_counter(); saved, entry, graph, ev, clock, args = prepare(ctx, row, read)
        preparation = perf_counter()-tick; assert_source(saved, historical)
        tick = perf_counter(); sc = cache.Scorer(graph, ev, weights, **args); construction = perf_counter()-tick
        result = select(sc, model, model_sha)
        same = train.refresh.parent.compatibility(historical['result'], result)
        packet = {k: saved[k] for k in train.refresh.SOURCE_FIELDS} | dict(result=result,
            model_sha256=model_sha, historical_case_ref=previous['artifact'], historical_case_sha256=previous['sha256'],
            preparation_seconds=preparation, scorer_construction_seconds=construction,
            same_completed_winner=same, full_source_not_clipped=True, reference_labels_used_for_selection=False,
            human_validated=False, reference_evaluation_performed=False)
        p, sha = save(Path('predictions')/(row['sample_id']+'.json.gz'), packet, True)
        predictions.append(dict(sample_id=row['sample_id'], artifact=p, sha256=sha))
        completed += result['selected'] is not None
        sources.add(saved['source_ir_content_sha256']); edges += len(graph.edges); train.refresh.clear(ev, clock)
        io.write(output/'progress.json', dict(complete=False, phase='ordinary_selection', finished=i,
            total=len(ctx['rows']), last_sample=row['sample_id'], last_status=result['status'],
            completed_predictions=completed,
            elapsed_seconds=perf_counter()-begun))
        print(f'[beat cached Train {i}/{len(ctx["rows"])}] {row["sample_id"]}: {result["status"]}', flush=True)
    freeze_path, freeze_sha = save(Path('prediction-freeze.json'), dict(complete=True, cohort=contract['cohort'],
        predictions=predictions, model_sha256=model_sha, reference_evaluation_started=False,
        fit_performed=False, code_pins=code))
    records = []; witnesses = projections = 0
    for i, (row, pred) in enumerate(zip(ctx['rows'], predictions), 1):
        packet = read(pred['artifact'], pred['sha256']); previous = ctx['beat_previous'][row['sample_id']]
        historical = read(previous['artifact'], previous['sha256'])
        saved, entry, graph, ev, clock, args = prepare(ctx, row, read); assert_source(saved, packet)
        old = train.prior.prior.Scorer(graph, ev, weights, **args); new = cache.Scorer(graph, ev, weights, **args)
        receipts, count = replay(old, new, historical, packet['result'])
        packet = packet | dict(evaluation=train.evaluate(packet['result']['selected'], ctx['refs'][row['sample_id']]),
            post_search_cost_receipts=receipts, scalar_and_role_transitions=count,
            reference_evaluation_performed=True, prediction_ref=pred['artifact'], prediction_sha256=pred['sha256'],
            prediction_freeze_ref=freeze_path, prediction_freeze_sha256=freeze_sha)
        p, sha = save(Path('cases')/(row['sample_id']+'.json.gz'), packet, True)
        records.append(record(row, packet, p, sha, previous)); witnesses += len(receipts); projections += count
        train.refresh.clear(ev, clock)
        io.write(output/'progress.json', dict(complete=False, phase='post_selection_replay_and_evaluation',
            finished=i, total=len(ctx['rows']), elapsed_seconds=perf_counter()-begun))
        if i % 10 == 0 or i == len(ctx['rows']): print(f'[beat Train replay {i}/{len(ctx["rows"])}]', flush=True)
    for p, sha in (inputs | artifacts | code).items():
        if io.digest(p) != sha: raise ValueError('beat_train_final_seal_changed:'+p)
    report = contract | dict(complete=True, records=records, predictions=predictions,
        prediction_freeze_sha256=freeze_sha, tables=summaries(records), ordinary_fresh_attempts=len(records),
        full_source_packages=len(sources), original_edges=edges, path_witnesses=witnesses,
        scalar_and_role_transitions=projections, archived_witnesses_preserved=ctx['beat_proof']['path_witnesses'],
        excluded_parent_scopes_preserved=ctx['protection_report']['excluded_parent_scopes_preserved'],
        input_hashes=inputs, artifact_hashes=artifacts, code_hashes=code, elapsed_seconds=perf_counter()-begun,
        next_required='frozen_dev_same20s_2M_cap6_before_adoption')
    io.write(output/'report.json', report)
    io.write(output/'progress.json', dict(complete=True, phase='sealed', finished=len(records), total=len(records),
        report_sha256=io.digest(output/'report.json')))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--validation', required=True); a = p.parse_args(); r = run(a.output, a.validation)
    print(json.dumps({k: r[k] for k in ('complete', 'tables', 'elapsed_seconds')}, indent=2), flush=True)
