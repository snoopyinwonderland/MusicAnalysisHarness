"""One frozen cached ordinal35 score on ALL original, exposed Dev records.

Stage89 controls are historical, not newly timed. Keep original input
abstentions and partial references. Seal all predictions before opening the
current reference report. No fit, retries, new candidates or adoption.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

from . import harmony_exact_beat_train_trial as fresh
from . import harmony_ordinal_protection_dev_trial as dev

VERSION = 'harmony-exact-beat-frozen-dev-trial-0.1.0'
ROOT = Path('K:/Music Analysis/output/harmony-ordinal-protection-dev-2026-10-06-r1')
PINS = {
    'report.json': '82ec2ecd234f4ed6165ddeb3d94392c7b05c9f22b7ac62ddb40de004d5f4f2ee',
    'run-contract.json': '68a87c2f8545eaf7945118b1c20cf131c462f0a104f516b7d9567949b9d9eb88',
    'prediction-freeze.json': '7e256d40056a581a106e541cc1af74a2e1063ccb9596c582a2ea08a16a9af2e5',
    'post-seal-audit.json': '072924e3de0d15baf145a94fd8519d7885e9110e923bc72e85298579bb7505c4',
}
TRAIN_ROOT = Path('K:/Music Analysis/output/harmony-exact-beat-train-2026-10-06-r1')
TRAIN_PINS = {
    'report.json': '09d170b697ca3190c850da76a646946eff75b52fd2585ad10ec8435fb67a9cce',
    'post-seal-audit.json': '5770611df3045023f1a56be21d816fa192101e53b38fc37a5982863ea15027ef',
}
PRIOR_VALIDATION_SHA = 'a8abaf740f7039b2d901754ace6c098ea90f35d75468e4ea264f4ff0704fdb94'
ARM = dev.ARMS[2]
io, load, same = dev.io, dev.load, dev.same_json


def key(row): return row['pair_id'], row['sample_id']


def require_raw(packet):
    if (any(k in packet for k in ('reference_cells', 'candidate_ceiling'))
            or any('evaluation' in a for a in packet['arms'].values())):
        raise ValueError('beat_dev_reference_in_raw_prediction')


def setup(read):
    train_report, train_audit = [read(TRAIN_ROOT/n, sha) for n, sha in TRAIN_PINS.items()]
    if (train_report['complete'] is not True or train_audit['passed'] is not True
            or train_audit['report_sha256'] != TRAIN_PINS['report.json']
            or train_report['model_sha256'] != dev.MODEL_SHAS[ARM]
            or train_report['fit_performed'] is not False or train_report['current_dev_inference'] is not False):
        raise ValueError('beat_dev_train_not_sealed')
    for p, sha in (train_report['input_hashes'] | train_report['artifact_hashes'] | train_report['code_hashes']).items():
        read(p, sha, raw=True)
    ctx = fresh.context(read); weights = ctx['beat_weights']
    contract = read(ROOT/'run-contract.json', PINS['run-contract.json'])
    freeze = read(ROOT/'prediction-freeze.json', PINS['prediction-freeze.json'])
    audit = read(ROOT/'post-seal-audit.json', PINS['post-seal-audit.json'])
    # Only hash the previous reference-containing report now; open it after
    # ALL current predictions are frozen. Earlier sealed containers have
    # exposed Dev history, so this is not an independent blind experiment.
    read(ROOT/'report.json', PINS['report.json'], raw=True)
    if (audit['passed'] is not True or audit['report_sha256'] != PINS['report.json']
            or freeze['dev_labels_read'] is not False or freeze['contexts'] != 72
            or freeze['model_sha256_by_arm'] != dev.MODEL_SHAS
            or contract['source_labels_used_at_inference'] is not False
            or contract['fit_performed'] is not False
            or not same(contract['coefficients'][ARM], {k: dev.s.q(v) for k, v in weights.items()})):
        raise ValueError('beat_dev_previous_not_sealed')
    for p, sha in contract['code_pins'].items(): read(p, sha, raw=True)
    packets = [read(p, sha) | dict(historical_prediction_ref=p, historical_prediction_sha256=sha)
               for p, sha in sorted(freeze['prediction_hashes'].items())]
    dev.previous.packet_keys(packets, 72)
    for packet in packets: require_raw(packet)
    if sum(p['attempted'] for p in packets) != 63: raise ValueError('beat_dev_original_attempted_cohort_changed')
    train_families = {r['work_family_id'] for r in ctx['rows']}
    if train_families & {p['work_family_id'] for p in packets}: raise ValueError('beat_dev_named_family_overlap')
    return ctx, weights, packets


def ordinary(graph, ev, weights, args, **guard):
    sc = fresh.cache.Scorer(graph, ev, weights, **args)
    result = fresh.select(sc, {'model_id': ARM}, dev.MODEL_SHAS[ARM], **guard)
    result.pop('ordinal_protection_contract', None)
    if 'member_role_contract' in result: result['member_role_contract']['old26_and_old7_frozen'] = True
    result['frozen_dev_contract'] = dict(version=dev.VERSION, fit_performed_this_trial=False,
        all_35_weights_frozen=True, arm=ARM, source_labels_used_for_selection=False,
        candidate_policy_changed=False, operational_promotion=False)
    result['frozen_model_ref'] = dict(model_id=ARM, model_sha256=dev.MODEL_SHAS[ARM],
        fit_performed_this_run=False, all_35_weights_frozen=True,
        reference_labels_used_for_selection=False, operational_promotion=False)
    if result['selected'] is not None:
        result['selected']['proposal_id'] = 'frozen_dev_'+dev.previous.prior.content_hash(
            [ARM, dev.MODEL_SHAS[ARM], dev.s.fresh.path_ids(result['selected']),
             {k: dev.s.q(v) for k, v in weights.items()}])[:24]
    return result


def replay(graph, ir, view, grace, clock, row, original_case, weights):
    ev, args = dev.evidence(ir, view, grace, row['sample_span'], clock)
    old = dev.train.Scorer(graph, ev, weights, **args); new = fresh.cache.Scorer(graph, ev, weights, **args)
    receipts = {}; transitions = 0
    archived = {'historical_'+a: v for a, v in original_case['same_weight_path_receipts'][ARM].items()}
    if ARM in original_case['reference_witness_receipts']:
        archived['reference_witness'] = original_case['reference_witness_receipts'][ARM]
    for name, original in archived.items():
        receipt, count = fresh.proof.check_path(old, new, tuple(original['existing_path_ids']), target=name == 'reference_witness')
        if not same(receipt, original): raise ValueError('beat_dev_historical_receipt_changed')
        receipts[name] = receipt; transitions += count
    selected = row['cached']['selected_prediction']
    if selected is not None:
        receipt, count = fresh.proof.check_path(old, new, dev.s.fresh.path_ids(selected))
        if not same(receipt, selected['context_score']) or receipt['cost'] != selected['score_cost']:
            raise ValueError('beat_dev_fresh_receipt_changed')
        receipts['fresh'] = receipt; transitions += count
    dev.train.prior.prior.clear(ev, clock)
    return receipts, transitions, len(archived)


def identity(row): return {k: row[k] for k in ('pair_id', 'sample_id', 'sample_span')}


def compare(rows, historical_arm=ARM):
    def arm(r, name): return r['cached'] if name == 'cached' else r['historical_arms'][name]
    common = [r for r in rows if arm(r, historical_arm)['selected_prediction'] is not None
              and r['cached']['selected_prediction'] is not None]
    recovered = [r for r in rows if arm(r, historical_arm)['selected_prediction'] is None
                 and r['cached']['selected_prediction'] is not None]
    lost = [r for r in rows if arm(r, historical_arm)['selected_prediction'] is not None
            and r['cached']['selected_prediction'] is None]
    tables = {}
    for name, subset in (('all_original', rows), ('common_completed', common)):
        tables[name] = {a: dev.summarize([r | arm(r, name) for r in subset])
                       for a, name in (('historical', historical_arm), ('cached', 'cached'))}
    return tables | dict(resources=dict(common_completed=len(common),
        recovered_previous_abstentions=len(recovered), previous_completion_now_abstention=len(lost),
        recovered=[identity(r) for r in recovered], lost=[identity(r) for r in lost],
        recovered_reference_hit=sum(r['cached']['evaluation']['selected_hit'] is True for r in recovered),
        recovered_reference_wrong=sum(r['cached']['evaluation']['selected_hit'] is False for r in recovered),
        recovered_reference_partial=sum(r['cached']['evaluation']['selected_hit'] is None for r in recovered),
        lost_reference_hit=sum(arm(r, historical_arm)['evaluation']['selected_hit'] is True for r in lost)),
        common_musical_changes=dict(
            changed_raw_paths=sum(not same(dev.s.fresh.path_ids(arm(r, historical_arm)['selected_prediction']),
                                          dev.s.fresh.path_ids(r['cached']['selected_prediction'])) for r in common),
            newly_correct=sum(r['cached']['evaluation']['selected_hit'] is True
                              and arm(r, historical_arm)['evaluation']['selected_hit'] is False for r in common),
            lost_correct=sum(r['cached']['evaluation']['selected_hit'] is False
                             and arm(r, historical_arm)['evaluation']['selected_hit'] is True for r in common)))


def metrics(rows):
    return dict(against_same_frozen_ordinal35=compare(rows), against_historical_old26=compare(rows, dev.ARMS[0]),
        common_completed_identical=sum(r['same_completed_winner'] for r in rows),
        historical_status_counts=dict(Counter(r['historical_arms'][ARM]['status'] for r in rows)),
        cached_status_counts=dict(Counter(r['cached']['status'] for r in rows)),
        original_input_abstentions=sum(not r['attempted'] for r in rows),
        all_abstentions_and_partial_references_retained=True,
        old26_controls_are_historical_not_newly_timed=True, independent_test=False)


def run(output, validation):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs = {}; artifacts = {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); name = str(p.resolve()); sha = inputs.get(name) or io.digest(p)
        if expected is not None and expected != sha: raise ValueError('beat_dev_input_changed:'+name)
        inputs[name] = sha; return None if raw else load(p)
    checked = read(validation)
    if (checked['passed'] is not True or checked['previous_validation_sha256'] != PRIOR_VALIDATION_SHA
            or 'test_harmony_exact_beat_dev_trial' not in checked['test_modules']):
        raise ValueError('beat_dev_validation_not_passed')
    ctx, weights, packets = setup(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for n in ('tests/test_harmony_exact_beat_dev_trial.py', 'scripts/validate_harmony_exact_beat_dev.py',
              'scripts/audit_harmony_exact_beat_dev.py'):
        code[str(Path(n).resolve())] = io.digest(n)
    output.mkdir(parents=True); (output/'predictions').mkdir(); (output/'cases').mkdir()
    def save(name, value, compressed=False):
        p = output/name; (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = dict(version=VERSION, cohort=[list(key(p)) for p in packets], model_sha256=dev.MODEL_SHAS[ARM],
        coefficients={k: dev.s.q(v) for k, v in weights.items()}, train_report_sha256=TRAIN_PINS['report.json'],
        previous_dev_report_sha256=PINS['report.json'], cache_version=fresh.cache.VERSION,
        wall_seconds=20, transition_budget=2_000_000, raw_segment_cap=6,
        fit_performed=False, parameter_sweep=False, dev_checkpoint_selection=False,
        source_candidates_dp_cost_and_operation_unit_unchanged=True, original_input_abstentions_not_retried=True,
        reference_reachable_filter_applied=False, evaluation_after_all_predictions_sealed=True,
        source_labels_used_for_selection=False, fresh_cache_per_scope=True,
        historical_controls_not_newly_timed=True, historical_parent_containers_include_exposed_dev=True,
        production_modified=False, operational_weights_changed=False, work_specific_rules=False,
        independent_test=False, purpose='local_noncommercial_research', code_pins=code)
    save(Path('run-contract.json'), contract)
    source_cache = {}; predictions = []; edges = 0
    for i, original in enumerate(packets, 1):
        row = {k: deepcopy(original[k]) for k in dev.FIELDS}
        row |= {k: original[k] for k in ('historical_prediction_ref', 'historical_prediction_sha256')}
        row['historical_arms'] = deepcopy(original['arms']); row['same_completed_winner'] = False
        if row['attempted']:
            row |= {k: original[k] for k in ('graph_artifact', 'graph_sha256')}
            tick = perf_counter(); graph, src, ir, view, grace, clock = dev.prepare(row, read, source_cache)
            ev, args = dev.evidence(ir, view, grace, row['sample_span'], clock)
            row['preparation_seconds'] = perf_counter()-tick
            if not same(src, original['source']): raise ValueError('beat_dev_original_source_changed')
            result = ordinary(graph, ev, weights, args)
            row['source'] = src; row['same_completed_winner'] = fresh.train.refresh.parent.compatibility(
                original['arms'][ARM]['result'], result)
            row['cached'] = dict(status=result['status'], selected_prediction=result['selected'],
                elapsed_seconds=result['resource_guard']['elapsed_seconds'], result=result)
            edges += len(graph.edges); dev.train.prior.prior.clear(ev, clock)
        else:
            # Preserve the original input rejection, not a fresh DP wall.
            row['cached'] = deepcopy(original['arms'][ARM]); row['preparation_seconds'] = 0
        p, sha = save(Path('predictions')/(dev.previous.prior.content_hash(key(row))[:20]+'.json.gz'), row, True)
        predictions.append(dict(pair_id=row['pair_id'], sample_id=row['sample_id'], artifact=p, sha256=sha))
        io.write(output/'progress.json', dict(complete=False, phase='ordinary_predictions_before_reference',
            scopes=i, total=len(packets), elapsed_seconds=perf_counter()-begun))
        print(f'[beat cached Dev {i}/{len(packets)}] {row["cached"]["status"]}', flush=True)
    freeze_path, freeze_sha = save(Path('prediction-freeze.json'), dict(complete=True, version=VERSION,
        model_sha256=dev.MODEL_SHAS[ARM], predictions=predictions, code_pins=code,
        current_reference_report_opened=False, fit_performed=False))
    # Only now open the current source references and historical evaluations.
    reference = read(dev.SOURCE_ROOT/'report.json', dev.SOURCE_PINS['report.json'])
    previous = read(ROOT/'report.json', PINS['report.json'])
    for report in (reference, previous):
        for p, sha in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
            read(p, sha, raw=True)
    refs = {key(r): r for r in reference['records']}; olds = {key(r): r for r in previous['records']}
    old_cases = {key(r): r for r in previous['cases']}
    keys = {key(p) for p in packets}
    if keys != set(refs) or keys != set(olds): raise ValueError('beat_dev_reference_inventory_changed')
    records = []; cases = []; costs = transitions = historical_costs = 0
    for i, pred in enumerate(predictions, 1):
        row = read(pred['artifact'], pred['sha256']); ref, old = refs[key(row)], olds[key(row)]
        row |= {k: deepcopy(ref[k]) for k in ('reference_cells', 'candidate_ceiling')}
        if not same(row['historical_arms'], {a: {k: v for k, v in value.items() if k != 'evaluation'}
            for a, value in old['arms'].items()}): raise ValueError('beat_dev_historical_prediction_changed')
        row['historical_arms'] = deepcopy(old['arms'])
        selected = row['cached']['selected_prediction']
        row['cached']['evaluation'] = dev.evaluate(dev.native_reference(row), dev.native_prediction(selected, row['sample_span']),
                                                  row['sample_span'], selected=selected is not None)
        row |= dict(prediction_ref=pred['artifact'], prediction_sha256=pred['sha256'],
            prediction_freeze_ref=freeze_path, prediction_freeze_sha256=freeze_sha)
        if row['attempted']:
            graph, src, ir, view, grace, clock = dev.prepare(row, read, source_cache)
            previous_case_path = old_cases[key(row)]['case_path']; previous_case_sha = io.digest(previous_case_path)
            original_case = read(previous_case_path, previous_case_sha)
            receipts, count, old_count = replay(graph, ir, view, grace, clock, row, original_case, weights)
            packet = dict(record=row, source=src, receipts=receipts, scalar_and_role_transitions=count,
                historical_receipts_preserved=old_count, previous_case_ref=previous_case_path,
                previous_case_sha256=previous_case_sha, human_validated=False,
                reference_witness_never_used_for_inference=True, full_score_not_clipped=True)
            p, sha = save(Path('cases')/(dev.previous.prior.content_hash(key(row))[:20]+'.json.gz'), packet, True)
            cases.append(dict(pair_id=row['pair_id'], sample_id=row['sample_id'], artifact=p, sha256=sha))
            costs += len(receipts); transitions += count; historical_costs += old_count
        records.append(row)
        io.write(output/'progress.json', dict(complete=False, phase='post_selection_replay_and_evaluation',
            scopes=i, total=len(packets), elapsed_seconds=perf_counter()-begun))
        if i % 10 == 0 or i == len(packets): print(f'[beat Dev replay {i}/{len(packets)}]', flush=True)
    for p, sha in (inputs | artifacts | code).items():
        if io.digest(p) != sha: raise ValueError('beat_dev_final_seal_changed:'+p)
    report = contract | dict(complete=True, records=records, cases=cases, predictions=predictions,
        prediction_freeze_sha256=freeze_sha, tables=metrics(records),
        original_records=len(records), ordinary_fresh_attempts=sum(r['attempted'] for r in records),
        original_edges=edges, full_source_packages=len(source_cache),
        distinct_ranges=len({(r['pair_id'], dev.previous.prior.content_hash(r['sample_span'])) for r in records if r['attempted']}),
        dev_families=sorted({r['work_family_id'] for r in records}),
        train_families=sorted({r['work_family_id'] for r in ctx['rows']}), named_family_overlap=[],
        full_duplicate_audit_performed=False, path_witnesses=costs,
        historical_receipts_preserved=historical_costs, scalar_and_role_transitions=transitions,
        all_original_cases_preserved=len(old_cases), input_hashes=inputs, artifact_hashes=artifacts, code_hashes=code,
        full_roman_or_local_key_or_nct_accuracy_measured=False, elapsed_seconds=perf_counter()-begun,
        next_required='large_train_harmony_and_nct_error_diagnosis_before_adoption')
    io.write(output/'report.json', report)
    io.write(output/'progress.json', dict(complete=True, phase='sealed', scopes=len(records), total=len(packets),
        report_sha256=io.digest(output/'report.json')))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--validation', required=True); a = p.parse_args(); r = run(a.output, a.validation)
    print(json.dumps({k: r[k] for k in ('complete', 'original_records', 'ordinary_fresh_attempts',
        'full_source_packages', 'path_witnesses', 'elapsed_seconds')}, indent=2), flush=True)
