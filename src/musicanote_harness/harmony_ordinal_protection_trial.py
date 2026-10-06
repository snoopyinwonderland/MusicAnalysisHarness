"""One frozen ordinal-protected fit followed by all 118 ordinary Train scopes."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

from . import harmony_train_protection_trial as prior
from . import harmony_ordinal_protection_learning as learning

VERSION = 'harmony-ordinal-protection-trial-0.1.0'
ROOT = Path('K:/Music Analysis/output/harmony-train-protection-2026-10-06-r1')
PINS = {
    'report.json': '9769f95b6fe91e2cc7e60bd18348f8897172f96d4b29c87e6c2b2b282570a2f5',
    'post-seal-audit.json': '658298065027cfd35ce8edc1a2dd559c968b6523781dfc68d41f03aa688b21f5',
    'training-vectors.json.gz': '3c6c138a1c90ff76ae563b4ffa8d788bc27fed1dd97f8107d3d1e58b2abe2573',
}
s, io, load, same_json = prior.s, prior.io, prior.load, prior.same_json
refresh, ledger = prior.refresh, prior.ledger


def context(read):
    report, audit, vectors = [read(ROOT/n, h) for n, h in PINS.items()]
    if (report['complete'] is not True or audit['passed'] is not True
            or audit['report_sha256'] != PINS['report.json'] or report['fit_performed'] is not False
            or report['current_dev_reconstructed_or_used'] is not False):
        raise ValueError('ordinal_parent_not_sealed_train')
    for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items(): read(p, h, raw=True)
    ctx = prior.context(read)
    if report['cohort'] != [r['sample_id'] for r in ctx['rows']]: raise ValueError('ordinal_cohort_changed')
    ctx['active_pool'] = vectors['rows']; ctx['protection_report'] = report
    prior.learning.validate_rows(ctx['active_pool'], ctx['use'], ctx['manifest'], ctx['parent_sha'])
    by_id = {r['contrast_id']: r for r in ctx['active_pool']}; competitors = []; missing = []
    for record in report['records']:
        if not record['attempted']: continue
        if record['status'] != 'selected_train_only_wrong_competitor':
            missing.append({k: record[k] for k in ('sample_id', 'status', 'artifact', 'sha256')}); continue
        packet = read(record['artifact'], record['sha256']); vector = packet['vector']
        key = packet['duplicate_existing_contrast_id'] or vector['contrast_id']
        row = by_id[key]
        if row['sample_id'] != record['sample_id'] or not all(same_json(row[k], vector[k]) for k in (
                'score_delta', 'gradient_delta', 'available', 'loss')):
            raise ValueError('ordinal_competitor_vector_changed')
        competitors.append(dict(sample_id=record['sample_id'], active_contrast_id=key,
            competitor_case_ref=record['artifact'], competitor_case_sha256=record['sha256']))
    ctx['competitors'], ctx['missing_protections'] = competitors, missing
    return ctx


def select(sc, model, model_sha):
    result = refresh.parent.select(sc, model['model_id'])
    # Scorer reuses the sealed 35-cost implementation, not the old fit identity.
    result.pop('joint_balance_contract', None)
    result['ordinal_protection_contract'] = dict(version=VERSION,
        all_35_weights_frozen_during_selection=True, source_features_and_graph_unchanged=True,
        source_labels_used=False, production_modified=False)
    result['frozen_model_ref'] = dict(model_id=model['model_id'], model_sha256=model_sha,
        fit_performed_before_selection=True, fit_performed_this_selection=False,
        all_35_weights_frozen=True, existing_26_frozen_during_fit=False,
        source_labels_used_for_selection=False, operational_promotion=False)
    if result['selected']:
        result['selected']['proposal_id'] = 'ordinal_protection_'+learning.use.content_hash(
            [s.fresh.path_ids(result['selected']), model_sha])[:24]
    return result


def evaluate(selected, ref):
    evaluator = refresh.old
    return evaluator.evaluate(evaluator.native_reference(ref),
        evaluator.native_prediction(selected, ref['sample_span']), ref['sample_span'], selected=selected is not None)


def summarize(records, ctx):
    tables = refresh.comparisons(records)
    joint = [r | dict(previous_ids=ctx['joint_records'][r['sample_id']]['selected_ids'],
        previous_evaluation=ctx['joint_records'][r['sample_id']]['evaluation']) for r in records]
    return dict(against_stage83_historical=tables,
        against_stage85_historical=refresh.comparisons(joint),
        baseline_paths_and_metrics_are_historical_not_newly_timed=True,
        independent_test=False, training_and_evaluation_scopes_overlap=True)


def record(row, packet, path, sha, ctx):
    sample = row['sample_id']; result = packet['result']; previous = ctx['previous_records'][sample]
    baseline = ctx['stage80_records'][sample]
    return {k: row[k] for k in refresh.FIELDS} | dict(artifact=path, sha256=sha, status=result['status'],
        selected_ids=s.fresh.path_ids(result['selected']) if result['selected'] else None,
        previous_ids=previous['selected_ids'], baseline_ids=baseline['baseline_ids'],
        evaluation=packet['evaluation'], previous_evaluation=previous['evaluation'],
        baseline_evaluation=baseline['baseline_evaluation'], elapsed_seconds=result['resource_guard']['elapsed_seconds'])


def chains(ctx, sample, ids):
    return dict(fresh=ids, previous_member_role=ctx['previous_records'][sample]['selected_ids'],
        previous_joint_balance=ctx['joint_records'][sample]['selected_ids'],
        frozen_old26=ctx['stage80_records'][sample]['baseline_ids'],
        stored_target=ctx['joint_packets'][sample]['arms']['epoch3_target']['path_ids'])


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); name = str(p.resolve()); h = io.digest(p)
        if (expected is not None and h != expected) or (name in inputs and inputs[name] != h):
            raise ValueError('ordinal_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for n in ('tests/test_harmony_ordinal_protection_learning.py', 'tests/test_harmony_ordinal_protection_trial.py',
              'scripts/validate_harmony_ordinal_protection.py', 'scripts/audit_harmony_ordinal_protection.py'):
        p = Path(n); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        p = output/p; (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = dict(version=VERSION, configuration=learning.configuration(),
        cohort=[r['sample_id'] for r in ctx['rows']], parent_report_sha256=PINS['report.json'],
        active_pool_sha256=PINS['training-vectors.json.gz'], initial_model_sha256=prior.prior.ROLE_PINS['model.json.gz'],
        missing_protection_competitors=ctx['missing_protections'],
        wall_seconds_per_fresh_scope=prior.WALL_SECONDS, transition_budget=s.fresh.BUDGET,
        same_original_graph_features_and_raw_cap=True, source_labels_used_for_prediction=False,
        current_dev_reconstructed_or_used=False, production_modified=False,
        historical_parent_containers_include_exposed_dev=True,
        purpose='local_noncommercial_research', code_pins=code, work_specific_conditions=False,
        new_negative_or_target_search_during_fit=False, pool_complete=False)
    save(Path('run-contract.json'), contract)
    rows, competitors = ctx['active_pool'], ctx['competitors']
    save(Path('training-vectors.json.gz'), dict(rows=deepcopy(rows), competitors=competitors), True)
    model = learning.fit(rows, competitors, ctx['initial35'], ctx['use'], ctx['manifest'],
                         ctx['parent_sha'], PINS['training-vectors.json.gz'])
    save(Path('model.json.gz'), model, True); model_sha = io.digest(output/'model.json.gz')
    weights = learning.model_weights(model, rows, competitors, ctx['initial35'], ctx['use'], ctx['manifest'],
                                     ctx['parent_sha'], PINS['training-vectors.json.gz'])
    save(Path('model-freeze.json'), dict(model_sha256=model_sha, postfit_selection_started=False,
        all_35_weights_frozen_during_selection=True, dev_used=False))
    print('[ordinal frozen] '+json.dumps(dict(updates=len(model['updates']), before=model['before'],
          after=model['after']), ensure_ascii=False), flush=True)
    records = []; sources = set(); edges = projections = 0
    for i, row in enumerate(ctx['rows'], 1):
        sample = row['sample_id']
        saved, entry, graph, ev, clock, args = prior.prior.prior.prior.old.prior.prepare_sample(ctx, row, read)
        sc = prior.prior.Scorer(graph, ev, weights, **args); result = select(sc, model, model_sha)
        selected = result['selected']; ids = s.fresh.path_ids(selected) if selected else None
        receipts = {}
        for name, path in chains(ctx, sample, ids).items():
            if path is None: continue
            receipt = sc.path_receipt(path, target=name == 'stored_target')
            projections += prior.prior.prior.verify_projection(sc, path, receipt); ledger.flatten(receipt, weights)
            if name == 'fresh' and not same_json(receipt, selected['context_score']):
                raise ValueError('ordinal_fresh_cost_changed')
            receipts[name] = receipt
        packet = {k: saved[k] for k in refresh.SOURCE_FIELDS} | dict(result=result,
            evaluation=evaluate(selected, ctx['refs'][sample]), model_sha256=model_sha,
            post_search_cost_receipts=receipts, human_validated=False,
            full_source_not_clipped=True, source_labels_used_for_inference=False,
            previous_case_ref=ctx['previous_records'][sample]['artifact'],
            previous_case_sha256=ctx['previous_records'][sample]['sha256'])
        p, h = save(Path('cases')/(sample+'.json.gz'), packet, True)
        records.append(record(row, packet, p, h, ctx))
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges); refresh.clear(ev, clock)
        print(f'[ordinal Train {i}/{len(ctx["rows"])}] {sample}: {result["status"]}, '
              f'hit={packet["evaluation"]["selected_hit"]}', flush=True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h: raise ValueError('ordinal_final_seal_changed:'+p)
    report = contract | dict(complete=True, fit_performed=True, model_sha256=model_sha,
        training_contrasts=len(rows), ordinary_fresh_attempts=len(records), full_source_packages=len(sources),
        original_edges=edges, scalar_detailed_transitions_compared=projections,
        tables=summarize(records, ctx), records=records, input_hashes=inputs, artifact_hashes=artifacts,
        code_hashes=code, operational_weights_changed=False, independent_accuracy_claimed=False,
        elapsed_seconds=perf_counter()-tick,
        excluded_parent_scopes_preserved=ctx['protection_report']['excluded_parent_scopes_preserved'])
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'tables', 'elapsed_seconds')}, indent=2), flush=True)
