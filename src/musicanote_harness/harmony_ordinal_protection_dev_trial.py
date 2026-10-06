"""Three prespecified frozen scores on every original, already exposed Dev scope.

No fit, sweep, loss-augmented inference, reference-compatible search or retries.
All new predictions are sealed before the current evaluation reference is read.
This is development diagnosis, not an independent/blind Test or model adoption.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from time import perf_counter

from . import harmony_joint_balance_trial as train
from . import harmony_ordinal_protection_trial as ordinal_train
from . import harmony_adversarial_score_dev_trial as previous
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize

VERSION = 'harmony-ordinal-protection-frozen-dev-trial-0.1.0'
ARMS = ('frozen_old26', 'frozen_member_role35', 'frozen_ordinal35')
PAIRS = ((ARMS[0], ARMS[1]), (ARMS[1], ARMS[2]), (ARMS[0], ARMS[2]))
ROOT = Path('K:/Music Analysis/output/harmony-ordinal-protection-2026-10-06-r1')
PINS = {
    'report.json': '8dad89e1130a0e2c742172a942a72732f0d09e3d0d7a2abc0ed9b45041f2435e',
    'model.json.gz': 'b6ff68e73bf6b5b9760107344f66f5c5626da2aa5c8b93ca061c21d6cbc74f38',
    'model-freeze.json': '6ff22448afa8c3c2db45349ff7660883a08f7b31c187aa299bc4bb41e5f03d6e',
    'post-seal-audit.json': '6e6eee39d55d0b73250b748ad50ee964833071ae629b86c3d1705c605b24227e'}
PREVIOUS_ROOT = Path('K:/Music Analysis/output/harmony-adversarial-score-dev-2026-10-05-r1')
PREVIOUS_PINS = {
    'report.json': '6eb4037bfd5c69c24c12acdb17cf32a04885a398853e8cabf48807a3eeb1821c',
    'post-seal-audit.json': '6c1c008c498e32bb2e3b48c130986944d9862f65536d5d9933b4f8a9f5a865af'}
SOURCE_ROOT, SOURCE_PINS = Path(previous.SOURCE_ROOT), previous.SOURCE_PINS
MODEL_SHAS = {ARMS[0]: previous.MODEL_PINS['model.json.gz'],
              ARMS[1]: train.ROLE_PINS['model.json.gz'], ARMS[2]: PINS['model.json.gz']}
FIELDS = ('pair_id', 'sample_id', 'sample_span', 'plan_index', 'collection_id',
          'work_family_id', 'reference_binding_verified', 'source_clock_gate',
          'attempted', 'known_prior_diagnostic')
s, io, load, same_json = train.s, train.io, train.load, train.same_json
WALL_SECONDS = train.prior.prior.old.WALL_SECONDS


def check_seal(report, model, freeze, audit):
    if (report.get('complete') is not True or audit.get('passed') is not True
            or audit.get('report_sha256') != PINS['report.json']
            or audit.get('model_sha256') != PINS['model.json.gz']
            or report.get('model_sha256') != PINS['model.json.gz']
            or freeze.get('model_sha256') != PINS['model.json.gz']
            or freeze.get('dev_used') is not False or model.get('dev_used') is not False
            or model.get('production_deployment') is not False
            or report.get('operational_weights_changed') is not False
            or report.get('current_dev_reconstructed_or_used') is not False
            or freeze.get('all_35_weights_frozen_during_selection') is not True):
        raise ValueError('unsealed_ordinal_dev_model')


def frozen_weights(read):
    ctx = ordinal_train.context(read)
    report, model, freeze, audit = [read(ROOT/n, h) for n, h in PINS.items()]
    check_seal(report, model, freeze, audit)
    for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
        read(p, h, raw=True)
    ordinal = ordinal_train.learning.model_weights(
        model, ctx['active_pool'], ctx['competitors'], ctx['initial35'],
        ctx['use'], ctx['manifest'], ctx['parent_sha'],
        ordinal_train.PINS['training-vectors.json.gz'])
    old = {k: ctx['weights'].get(k, Fraction()) for k in train.ledger.FEATURES}
    return {ARMS[0]: old, ARMS[1]: ctx['initial35'], ARMS[2]: ordinal}, ctx


def ordinary(graph, ev, weights, args, arm, **guard):
    sc = train.Scorer(graph, ev, weights, **args)
    result = train.prior.prior.parent.select(sc, arm, **guard)
    # Parent metadata describes its original Train fit, not this no-fit trial.
    result.pop('joint_balance_contract', None)
    if 'member_role_contract' in result:
        result['member_role_contract']['old26_and_old7_frozen'] = True
    result['frozen_dev_contract'] = {'version': VERSION, 'fit_performed_this_trial': False,
        'all_35_weights_frozen': True, 'arm': arm, 'source_labels_used_for_selection': False,
        'candidate_policy_changed': False, 'operational_promotion': False}
    result['frozen_model_ref'] = {'model_id': arm, 'model_sha256': MODEL_SHAS[arm],
        'fit_performed_this_run': False, 'all_35_weights_frozen': True,
        'reference_labels_used_for_selection': False, 'operational_promotion': False}
    if result['selected'] is not None:
        result['selected']['proposal_id'] = 'frozen_dev_'+previous.prior.content_hash(
            [arm, MODEL_SHAS[arm], s.fresh.path_ids(result['selected']),
             {k: s.q(v) for k, v in weights.items()}])[:24]
    return result


def prepare(row, read, cache):
    packet = read(row['graph_artifact'], row['graph_sha256'])
    previous.prior.prior.check_prediction(packet)
    if not same_json([packet['pair_id'], packet['sample_id'], packet['span']],
                     [row['pair_id'], row['sample_id'], row['sample_span']]):
        raise ValueError('frozen_dev_graph_scope_changed')
    graph = previous.prior.prior.prior.graph_from_packet(packet['problem'])
    if not same_json(previous.prior.prior.prior.graph_packet(graph), packet['problem']):
        raise ValueError('frozen_dev_graph_codec_changed')
    source = packet['source']; pair = row['pair_id']
    if pair not in cache:
        ir = read(source['canonical_ir_path'])
        if previous.prior.content_hash(ir) != source['original_ir_content_sha256']:
            raise ValueError('frozen_dev_ir_changed')
        read(source['source_musicxml_path'], source['original_musicxml_sha256'], raw=True)
        view, grace = previous.prior.prior.prior.bounded.grace_projection(ir)
        cache[pair] = ir, view, grace, previous.prior.SourceClockGuard(ir), source
    ir, view, grace, clock, bound_source = cache[pair]
    if not same_json(source, bound_source): raise ValueError('frozen_dev_source_binding_changed')
    if (not same_json(clock.scope(row['sample_span']), row['source_clock_gate'])
            or row['source_clock_gate']['accepted'] is not True):
        raise ValueError('frozen_dev_source_clock_changed')
    return graph, source, ir, view, grace, clock


def evidence(ir, view, grace, span, clock):
    return previous.prior.prior.evidence_args(ir, view, grace, span, clock)


def original_abstention(old):
    return {'status': old['arms']['timing_calibrated']['status'], 'selected_prediction': None,
            'elapsed_seconds': 0, 'reused_old_abstention': True}


def seal_and_open_reference(read, save, output, rows):
    save(output/'prediction-freeze.json', {'version': VERSION, 'model_sha256_by_arm': MODEL_SHAS,
        'dev_labels_read': False, 'contexts': len(rows), 'fit_performed': False,
        'prediction_hashes': {r['prediction_artifact']: io.digest(r['prediction_artifact']) for r in rows}})
    return read(SOURCE_ROOT/'report.json', SOURCE_PINS['report.json'])


def metrics(rows):
    completed = [r for r in rows if all(r['arms'][a]['selected_prediction'] is not None for a in ARMS)]
    pairs = {}
    for a, b in PAIRS:
        common = [r for r in rows if all(r['arms'][x]['selected_prediction'] is not None for x in (a, b))]
        comparisons = {}
        for name, subset in (('all_original', rows), ('common_completed', common)):
            changed = []
            for r in subset:
                left, right = r['arms'][a], r['arms'][b]
                if native_prediction(left['selected_prediction'], r['sample_span']) != native_prediction(right['selected_prediction'], r['sample_span']):
                    changed.append({'pair_id': r['pair_id'], 'sample_id': r['sample_id'],
                        'matched_time_delta': s.q(s.f(right['evaluation']['components']['root_members']['matched'])
                                                 -s.f(left['evaluation']['components']['root_members']['matched']))})
            comparisons[name] = {'contexts': len(subset), 'changed': changed,
                'previously_correct_lost': sum(r['arms'][a]['evaluation']['selected_hit'] is True and
                    r['arms'][b]['evaluation']['selected_hit'] is not True for r in subset),
                'newly_correct': sum(r['arms'][a]['evaluation']['selected_hit'] is not True and
                    r['arms'][b]['evaluation']['selected_hit'] is True for r in subset)}
        pairs[a+'__to__'+b] = comparisons | {'resource_losses': sum(
            r['arms'][a]['selected_prediction'] is not None and r['arms'][b]['selected_prediction'] is None for r in rows),
            'resource_recoveries': sum(r['arms'][a]['selected_prediction'] is None and
                r['arms'][b]['selected_prediction'] is not None for r in rows)}
    return {'all_original': {a: summarize([r | r['arms'][a] for r in rows]) for a in ARMS},
        'common_completed_count': len(completed),
        'common_completed': {a: summarize([r | r['arms'][a] for r in completed]) for a in ARMS},
        'paired_comparisons': pairs}


def receipts(graph, ir, view, grace, clock, row, weights):
    paths = {a: s.fresh.path_ids(v['selected_prediction']) for a, v in row['arms'].items()
             if v['selected_prediction'] is not None}
    witness = (row['candidate_ceiling'] or {}).get('oracle_reference_witness')
    result = {'same_weight_path_receipts': {}, 'reference_witness_receipts': {},
              'winner_minus_reference_witness': {}}
    projections = 0
    for a in ARMS:
        ev, args = evidence(ir, view, grace, row['sample_span'], clock)
        sc = train.Scorer(graph, ev, weights[a], **args); cross = {}
        for b, ids in paths.items():
            receipt = sc.path_receipt(ids); train.ledger.flatten(receipt, weights[a])
            projections += train.prior.verify_projection(sc, ids, receipt); cross[b] = receipt
            if a == b and not same_json(receipt, row['arms'][a]['selected_prediction']['context_score']):
                raise ValueError('frozen_dev_selected_receipt_changed')
        result['same_weight_path_receipts'][a] = cross
        if witness:
            receipt = sc.path_receipt(witness, target=True); train.ledger.flatten(receipt, weights[a])
            projections += train.prior.verify_projection(sc, witness, receipt)
            result['reference_witness_receipts'][a] = receipt
            if a in cross:
                result['winner_minus_reference_witness'][a] = train.ledger.compare(cross[a], receipt, weights[a])
        train.prior.prior.clear(ev, clock)
    return result, projections


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if (expected is not None and h != expected) or (name in inputs and inputs[name] != h):
            raise ValueError('frozen_dev_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    weights, ctx = frozen_weights(read)
    old_contract = read(SOURCE_ROOT/'run-contract.json', SOURCE_PINS['run-contract.json'])
    old_freeze = read(SOURCE_ROOT/'prediction-freeze.json', SOURCE_PINS['prediction-freeze.json'])
    if old_contract['source_labels_used_at_inference'] is not False or old_freeze['dev_labels_read'] is not False:
        raise ValueError('frozen_dev_source_not_sealed')
    for p, h in old_contract['code_pins'].items(): read(p, h, raw=True)
    packets = [read(p, h) for p, h in sorted(old_freeze['prediction_hashes'].items())]
    keys = previous.packet_keys(packets, old_freeze['contexts'])
    train_families = {r['work_family_id'] for r in ctx['rows']}
    dev_families = {r['work_family_id'] for r in packets}
    if train_families & dev_families: raise ValueError('frozen_dev_named_family_overlap')
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for n in ('tests/test_harmony_ordinal_protection_dev_trial.py', 'scripts/validate_harmony_ordinal_protection_dev.py',
              'scripts/audit_harmony_ordinal_protection_dev.py'):
        code[str(Path(n).resolve())] = io.digest(n)
    output.mkdir(parents=True); (output/'predictions').mkdir(); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name
    contract = {'version': VERSION, 'arms': ARMS, 'arm_order_fixed_before_results': True,
        'model_sha256_by_arm': MODEL_SHAS, 'coefficients': {a: {k: s.q(v) for k, v in w.items()} for a, w in weights.items()},
        'fit_performed': False, 'parameter_sweep': False, 'dev_fit_or_checkpoint_selection': False,
        'loss_augmented_inference': False, 'source_labels_used_at_inference': False,
        'original_abstentions_not_retried': True, 'reference_reachable_filter_applied': False,
        'same_original_dev_graphs': True, 'transition_budget': s.fresh.BUDGET,
        'wall_seconds_per_arm': WALL_SECONDS, 'fresh_feature_cache_per_arm': True,
        'zero_extra_weights_use_exact_legacy_batched_decoder': True,
        'timings_are_not_controlled_speed_benchmark': True, 'purpose': 'local_noncommercial_research',
        'production_modified': False, 'code_pins': code, 'source_pins': SOURCE_PINS, 'model_pins': PINS}
    save(output/'run-contract.json', contract)
    rows, cache = [], {}; edges = 0
    for old in packets:
        row = {k: deepcopy(old[k]) for k in FIELDS}; row['arms'] = {}
        if row['attempted']:
            row |= {k: old[k] for k in ('graph_artifact', 'graph_sha256')}
            graph, src, ir, view, grace, clock = prepare(row, read, cache)
            row['source'] = src; edges += len(graph.edges)
            for arm in ARMS:
                ev, args = evidence(ir, view, grace, row['sample_span'], clock)
                result = ordinary(graph, ev, weights[arm], args, arm)
                row['arms'][arm] = {'status': result['status'], 'selected_prediction': result['selected'],
                    'elapsed_seconds': result['resource_guard']['elapsed_seconds'], 'result': result}
                train.prior.prior.clear(ev, clock)
        else:
            row['arms'] = {a: original_abstention(old) for a in ARMS}
        row['prediction_artifact'] = save(output/'predictions'/(
            previous.prior.content_hash([row['pair_id'], row['sample_id']])[:20]+'.json.gz'), row, True)
        rows.append(row)
        # Progress is intentionally not part of the immutable artifact seal.
        io.write(output/'progress.json', {'complete': False, 'phase': 'predictions_before_current_reference_read',
            'scopes': len(rows), 'total': len(packets), 'elapsed_seconds': perf_counter()-begun})
        print(f'[ordinal frozen Dev {len(rows)}/{len(packets)}] '+json.dumps(
            {a: row['arms'][a]['status'] for a in ARMS}), flush=True)
    baseline = seal_and_open_reference(read, save, output, rows)
    historical, audit = [read(PREVIOUS_ROOT/n, h) for n, h in PREVIOUS_PINS.items()]
    if audit['passed'] is not True or audit['report_sha256'] != PREVIOUS_PINS['report.json']:
        raise ValueError('frozen_dev_previous_audit_failed')
    for report in (baseline, historical):
        for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items(): read(p, h, raw=True)
    refs = {(r['pair_id'], r['sample_id']): r for r in baseline['records']}
    prev = {(r['pair_id'], r['sample_id']): r for r in historical['records']}
    old_cases = {(r['pair_id'], r['sample_id']): r for r in historical['cases']}
    if set(refs) != keys or set(prev) != keys: raise ValueError('frozen_dev_reference_inventory_changed')
    cases = []; control_complete = control_abstain = projections = 0
    for row in rows:
        key = row['pair_id'], row['sample_id']; ref = refs[key]
        row |= {k: deepcopy(ref[k]) for k in ('reference_cells', 'candidate_ceiling')}
        for v in row['arms'].values():
            v['evaluation'] = evaluate(native_reference(row), native_prediction(v['selected_prediction'], row['sample_span']),
                                       row['sample_span'], selected=v['selected_prediction'] is not None)
        old_selected = prev[key]['arms'][previous.ARMS[2]]['selected_prediction']
        fresh = row['arms'][ARMS[0]]['selected_prediction']
        if fresh is not None:
            previous.check_control({'selected': fresh}, old_selected, ARMS[0]); control_complete += 1
        elif old_selected is not None: control_abstain += 1
        if row['attempted']:
            graph, src, ir, view, grace, clock = prepare(row, read, cache)
            replay, n = receipts(graph, ir, view, grace, clock, row, weights); projections += n
            case = {'record': row, 'source': src, 'model_sha256_by_arm': MODEL_SHAS, **replay,
                'human_validated': False, 'independent_test_case': False,
                'reference_witness_never_used_for_inference': True,
                'previous_case_artifact': old_cases[key]['case_path'] if key in old_cases else None}
            cases.append({'pair_id': key[0], 'sample_id': key[1], 'case_path': save(output/'cases'/(
                previous.prior.content_hash(key)[:20]+'.json.gz'), case, True)})
            print(f'[ordinal frozen Dev receipts {len(cases)}/{sum(r["attempted"] for r in rows)}]', flush=True)
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('frozen_dev_final_seal_changed:'+p)
    final = contract | {'complete': True, 'contexts': len(rows), 'fresh_dev_scopes': sum(r['attempted'] for r in rows),
        'full_dev_source_packages': len(cache), 'original_edges': edges, 'tables': metrics(rows),
        'records': rows, 'cases': cases, 'previous_cases_preserved': len(old_cases),
        'old26_completed_controls_identical': control_complete, 'old26_new_resource_abstentions': control_abstain,
        'scalar_detailed_transitions_replayed': projections,
        'training_families': sorted(train_families), 'dev_families': sorted(dev_families), 'named_family_overlap': [],
        'full_duplicate_audit_performed': False, 'all_dev_predictions_sealed_before_reference_report_read': True,
        'historical_parent_containers_include_exposed_dev': True, 'independent_test_accuracy_measured': False,
        'full_roman_or_local_key_or_nct_accuracy_measured': False, 'candidate_policy_changed': False,
        'operational_weights_changed': False, 'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'status_counts': {a: dict(Counter(r['arms'][a]['status'] for r in rows)) for a in ARMS},
        'elapsed_seconds': perf_counter()-begun}
    io.write(output/'report.json', final); return final


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'contexts', 'fresh_dev_scopes', 'full_dev_source_packages',
          'status_counts', 'old26_new_resource_abstentions', 'elapsed_seconds')}, indent=2), flush=True)
