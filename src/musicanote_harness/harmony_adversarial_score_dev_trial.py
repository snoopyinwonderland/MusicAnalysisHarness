"""Three frozen ordinary decoders on ALL original, already exposed Dev scopes.

No fitting, loss-augmented inference, reference-compatible search, checkpoint
selection, new candidates or retries. Seal predictions before evaluation labels.
This is a paired Dev diagnostic, NOT an independent/blind Test.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

from . import harmony_online_score_dev_trial as control
from . import harmony_adversarial_score_learning as learning
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize

s, prior, io, load = control.s, control.prior, control.io, control.load
VERSION = 'harmony-adversarial-full-score-dev-trial-0.1.0'
ARMS = (*control.ARMS, 'adversarial_frozen_full_score')
PAIRS = ((ARMS[0], ARMS[1]), (ARMS[1], ARMS[2]), (ARMS[0], ARMS[2]))
MODEL_ROOT = 'output/harmony-adversarial-score-2026-10-05-r1'
MODEL_PINS = {
    'report.json': '9146c3783006ae433041e3bc05d1db2266e6f9cb03d6b8771e6d046705b96034',
    'model.json.gz': '2df7bb4802e14b48fbb70c8d0952b0c0bee5a96c0e4d258ee6cc88fd183838cf',
    'model-freeze.json': '4f237683c0eb1f1aa3b5afdf87f16682bd204903f3769c4f37874da5452e453f',
    'post-seal-audit.json': '2b315941ef3c180edbd29565d5cc6299652675167358842f462f054c65157b34'}
MODEL_SHAS = {ARMS[0]: None, ARMS[1]: control.MODEL_PINS['model.json.gz'],
              ARMS[2]: MODEL_PINS['model.json.gz']}
SOURCE_ROOT, SOURCE_PINS = control.SOURCE_ROOT, control.SOURCE_PINS
PREVIOUS_ROOT = 'output/harmony-online-score-dev-2026-10-05-r1'
PREVIOUS_PINS = {
    'run-contract.json': '23915c3b9bd2a2418c6a3b0fe631a3fdaeb537e4c4f7b7f4d1c5c3f4b5d46b47',
    'prediction-freeze.json': '999aa6b02dbf4505fed277a9b1d6d45fab00b2048db8ca21c4e8e577b4f0b434',
    'report.json': '9bdd36259ed5dad8ab5edd34786a6adeb54c0a956a26bb37f79e2f2bf60f8443',
    'post-seal-audit.json': 'a32167145f04217d5aba2b71212500deb46f19c897636bb7a047698de170809e'}
packet_keys, ordinary = control.packet_keys, control.ordinary


def same_json(a, b):
    """JSON tuple/list normalization preserves order, rational values and null."""
    return prior.content_hash(a) == prior.content_hash(b)


def check_model_seal(report, audit, freeze, model_sha):
    if (report.get('complete') is not True or audit.get('passed') is not True
            or audit.get('report_sha256') != MODEL_PINS['report.json']
            or audit.get('audit_revision') != 2 or audit.get('new_fit_or_checkpoint_selection') is not False
            or report.get('model_sha256') != model_sha or freeze.get('model_sha256') != model_sha
            or freeze.get('all_epochs_averaged') is not True or freeze.get('dev_labels_used') is not False
            or report.get('dev_used_for_fit') is not False or report.get('dev_inference_or_evaluation') is not False
            or report.get('production_modified') is not False or report.get('candidate_policy_changed') is not False):
        raise ValueError('unsealed_or_nontrain_adversarial_model')


def frozen_weights(read):
    weights, previous_model = control.frozen_weights(read)
    report, model, freeze, audit = [read(Path(MODEL_ROOT)/p, h) for p, h in MODEL_PINS.items()]
    check_model_seal(report, audit, freeze, MODEL_PINS['model.json.gz'])
    for p, h in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items():
        read(p, h, raw=True)
    training = prior.training.parent
    containers = [read(p, h) for p, h in training.old_training.PINS.items()]
    manifest, use = containers[1]['package_manifest'], containers[3]
    weights[ARMS[2]] = learning.model_weights(model, weights[ARMS[0]], use, manifest, training.old_training.PARENT_SHA)
    if model['training_families'] != previous_model['training_families']:
        raise ValueError('frozen_models_train_family_inventory_changed')
    return weights, model


def check_control(result, baseline, arm):
    try:
        control.check_initial_control(result, baseline)
    except ValueError as error:
        raise ValueError('adversarial_dev_control_changed:'+arm) from error


def seal_and_open_reference(read, save, output, rows):
    save(output/'prediction-freeze.json', {'version': VERSION, 'model_sha256_by_arm': MODEL_SHAS,
        'dev_labels_read': False, 'contexts': len(rows), 'fit_performed': False,
        'prediction_hashes': {r['prediction_artifact']: io.digest(r['prediction_artifact']) for r in rows}})
    return read(Path(SOURCE_ROOT)/'report.json', SOURCE_PINS['report.json'])


def comparisons(rows):
    result = {}
    for a, b in PAIRS:
        changed = []
        for row in rows:
            old, new = row['arms'][a], row['arms'][b]
            if native_prediction(old['selected_prediction'], row['sample_span']) != native_prediction(new['selected_prediction'], row['sample_span']):
                changed.append({'pair_id': row['pair_id'], 'sample_id': row['sample_id'],
                    'matched_time_delta': s.q(s.f(new['evaluation']['components']['root_members']['matched'])
                                             -s.f(old['evaluation']['components']['root_members']['matched']))})
        result[a+'__to__'+b] = {'changed': changed,
            'previously_correct_lost': sum(r['arms'][a]['evaluation']['selected_hit'] is True and
                r['arms'][b]['evaluation']['selected_hit'] is not True for r in rows),
            'newly_correct': sum(r['arms'][a]['evaluation']['selected_hit'] is not True and
                r['arms'][b]['evaluation']['selected_hit'] is True for r in rows)}
    return result


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected: raise ValueError('adversarial_dev_pinned_input_changed:'+name)
        if name in inputs and inputs[name] != h: raise ValueError('adversarial_dev_input_changed:'+name)
        inputs[name] = h
        return None if raw else load(p)
    weights, model = frozen_weights(read)
    old_contract = read(Path(SOURCE_ROOT)/'run-contract.json', SOURCE_PINS['run-contract.json'])
    old_freeze = read(Path(SOURCE_ROOT)/'prediction-freeze.json', SOURCE_PINS['prediction-freeze.json'])
    previous_contract = read(Path(PREVIOUS_ROOT)/'run-contract.json', PREVIOUS_PINS['run-contract.json'])
    previous_freeze = read(Path(PREVIOUS_ROOT)/'prediction-freeze.json', PREVIOUS_PINS['prediction-freeze.json'])
    if (old_contract['source_labels_used_at_inference'] is not False or old_freeze['dev_labels_read'] is not False
            or previous_freeze['dev_labels_read'] is not False or previous_contract['fit_performed'] is not False
            or previous_freeze['model_sha256'] != MODEL_SHAS[ARMS[1]]):
        raise ValueError('unsealed_adversarial_dev_baseline')
    for contract in (old_contract, previous_contract):
        for p, h in contract['code_pins'].items(): read(p, h, raw=True)
    packets = [read(p, h) for p, h in sorted(old_freeze['prediction_hashes'].items())]
    old_predictions = [read(p, h) for p, h in sorted(previous_freeze['prediction_hashes'].items())]
    keys = packet_keys(packets, old_freeze['contexts'])
    if packet_keys(old_predictions, len(packets)) != keys: raise ValueError('previous_dev_inventory_changed')
    controls = {(r['pair_id'], r['sample_id']): r for r in old_predictions}
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for name in ('tests/test_harmony_adversarial_score_dev_trial.py', 'scripts/audit_harmony_adversarial_score_dev.py',
                 'scripts/validate_harmony_adversarial_score_dev.py'):
        p = Path(name); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'predictions').mkdir(); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name
    save(output/'run-contract.json', {'version': VERSION, 'code_pins': code, 'arms': ARMS,
        'source_pins': SOURCE_PINS, 'model_pins': MODEL_PINS, 'previous_dev_pins': PREVIOUS_PINS,
        'model_sha256_by_arm': MODEL_SHAS,
        'coefficients': {a: {k: s.q(v) for k, v in w.items()} for a, w in weights.items()},
        'model_frozen_before_dev_predictions': True, 'source_labels_used_at_inference': False,
        'fit_performed': False, 'dev_fit_or_checkpoint_selection': False, 'parameter_sweep': False,
        'loss_augmented_inference': False, 'transition_budget': s.fresh.BUDGET, 'same_original_dev_graphs': True,
        'original_abstentions_not_retried': True, 'reference_reachable_filter_applied': False,
        'purpose': 'local_noncommercial_research', 'production_modified': False})
    rows, cache = [], {}
    for old in packets:
        key = old['pair_id'], old['sample_id']; previous = controls[key]
        row = {k: deepcopy(old[k]) for k in ('pair_id', 'sample_id', 'sample_span', 'plan_index', 'collection_id',
            'work_family_id', 'reference_binding_verified', 'source_clock_gate', 'attempted', 'known_prior_diagnostic')}
        if not same_json(row['sample_span'], previous['sample_span']) or row['attempted'] != previous['attempted']:
            raise ValueError('previous_dev_scope_changed')
        row['arms'] = {}
        if row['attempted']:
            packet = read(old['graph_artifact'], old['graph_sha256']); prior.prior.check_prediction(packet)
            if (packet['pair_id'], packet['sample_id'], packet['span']) != (*key, row['sample_span']):
                raise ValueError('adversarial_dev_graph_scope_changed')
            graph = prior.prior.prior.graph_from_packet(packet['problem'])
            if not same_json(prior.prior.prior.graph_packet(graph), packet['problem']):
                raise ValueError('adversarial_dev_graph_codec_changed')
            row.update(graph_artifact=old['graph_artifact'], graph_sha256=old['graph_sha256'], source=packet['source'])
            if key[0] not in cache:
                src = packet['source']; ir = read(src['canonical_ir_path'])
                if prior.content_hash(ir) != src['original_ir_content_sha256']: raise ValueError('adversarial_dev_ir_changed')
                read(src['source_musicxml_path'], src['original_musicxml_sha256'], raw=True)
                view, grace = prior.prior.prior.bounded.grace_projection(ir)
                cache[key[0]] = ir, view, grace, prior.SourceClockGuard(ir)
            ir, view, grace, clock = cache[key[0]]
            if clock.scope(row['sample_span']) != row['source_clock_gate'] or not row['source_clock_gate']['accepted']:
                raise ValueError('adversarial_dev_clock_changed')
            ev, args = prior.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            for arm in ARMS:
                tick = perf_counter(); result = ordinary(graph, ev, weights[arm], args)
                if arm in control.ARMS:
                    check_control(result, previous['arms'][arm]['selected_prediction'], arm)
                if arm == ARMS[0]: check_control(result, old['arms']['timing_calibrated']['selected_prediction'], arm)
                if result['selected'] is not None: result['selected']['full_score']['model_sha256'] = MODEL_SHAS[arm]
                row['arms'][arm] = {'status': result['status'], 'selected_prediction': result['selected'],
                    'elapsed_seconds': perf_counter()-tick, 'transitions': result['transitions'],
                    'exact_optimum_under_declared_score': result['exact_optimum_under_declared_score'],
                    'search_diagnostics': result['search_diagnostics']}
            clock.check_source()
        else:
            row['arms'] = {a: {'status': old['arms']['timing_calibrated']['status'], 'selected_prediction': None,
                'elapsed_seconds': 0, 'reused_old_abstention': True} for a in ARMS}
            for a in control.ARMS: check_control({'selected': None}, previous['arms'][a]['selected_prediction'], a)
        row['prediction_artifact'] = save(output/'predictions'/(prior.content_hash(key)[:20]+'.json.gz'), row, True)
        rows.append(row)
        save(output/'progress.json', {'complete': False, 'phase': 'Dev_predictions_before_reference_report_read',
            'scopes': len(rows), 'total': len(packets), 'elapsed_seconds': perf_counter()-begun})
        print(f'[adversarial frozen Dev {len(rows)}/{len(packets)}] {key[0]}', flush=True)
    baseline = seal_and_open_reference(read, save, output, rows)
    previous = read(Path(PREVIOUS_ROOT)/'report.json', PREVIOUS_PINS['report.json'])
    audit = read(Path(PREVIOUS_ROOT)/'post-seal-audit.json', PREVIOUS_PINS['post-seal-audit.json'])
    if audit.get('passed') is not True or audit.get('report_sha256') != PREVIOUS_PINS['report.json']:
        raise ValueError('previous_dev_audit_failed')
    for report in (baseline, previous):
        for p, h in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items(): read(p, h, raw=True)
    refs = {(r['pair_id'], r['sample_id']): r for r in baseline['records']}
    if set(refs) != keys or len(refs) != len(baseline['records']): raise ValueError('adversarial_dev_reference_inventory_changed')
    old_cases = {(r['pair_id'], r['sample_id']): r for r in previous['cases']}; cases = []
    # Preserve every attempted scope, not just successes or reference-reachable cases.
    for row in rows:
        key = row['pair_id'], row['sample_id']; ref = refs[key]
        row['reference_cells'] = deepcopy(ref['reference_cells']); row['candidate_ceiling'] = deepcopy(ref['candidate_ceiling'])
        for value in row['arms'].values():
            value['evaluation'] = evaluate(native_reference(row), native_prediction(value['selected_prediction'], row['sample_span']),
                row['sample_span'], selected=value['selected_prediction'] is not None)
        if row['attempted']:
            graph = prior.prior.prior.graph_from_packet(read(row['graph_artifact'])['problem'])
            ir, view, grace, clock = cache[key[0]]; ev, args = prior.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            scorers = {a: s.Scorer(graph, ev, w, **args) for a, w in weights.items()}
            paths = {a: s.fresh.path_ids(v['selected_prediction']) for a, v in row['arms'].items() if v['selected_prediction'] is not None}
            case = {'record': row, 'source': row['source'], 'model_sha256_by_arm': MODEL_SHAS,
                'selected_path_receipts': {a: scorers[a].receipt(ids) for a, ids in paths.items()},
                'same_weight_path_receipts': {a: {b: sc.receipt(ids) for b, ids in paths.items()} for a, sc in scorers.items()},
                'human_validated': False, 'independent_test_case': False, 'reference_witness_never_used_for_inference': True,
                'previous_case_artifact': old_cases[key]['case_path'] if key in old_cases else None}
            witness = ref['candidate_ceiling'].get('oracle_reference_witness') if ref['candidate_ceiling'] else None
            if witness: case['reference_witness_receipts'] = {a: sc.receipt(witness, target=True) for a, sc in scorers.items()}
            cases.append({'pair_id': key[0], 'sample_id': key[1],
                'case_path': save(output/'cases'/(prior.content_hash(key)[:20]+'.json.gz'), case, True)})
            clock.check_source()
    tables = {a: summarize([r | r['arms'][a] for r in rows]) for a in ARMS}
    if not same_json(tables[ARMS[0]], baseline['tables']['timing_calibrated']): raise ValueError('adversarial_dev_initial_metric_changed')
    for a in control.ARMS:
        if not same_json(tables[a], previous['tables'][a]): raise ValueError('adversarial_dev_previous_metric_changed:'+a)
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('adversarial_dev_guard_changed:'+p)
    train = set(model['training_families']); dev = {r['work_family_id'] for r in rows}
    final = {'version': VERSION, 'complete': True, 'contexts': len(rows), 'fresh_dev_scopes': sum(r['attempted'] for r in rows),
        'full_dev_source_packages': len(cache), 'model_sha256_by_arm': MODEL_SHAS, 'tables': tables, 'records': rows,
        'cases': cases, 'comparisons': comparisons(rows), 'previous_cases_preserved': len(old_cases),
        'training_families': sorted(train), 'dev_families': sorted(dev), 'named_family_overlap': sorted(train & dev),
        'full_duplicate_audit_performed': False, 'model_frozen_before_dev_predictions': True,
        'all_dev_predictions_sealed_before_reference_report_read': True, 'loaded_parent_containers_include_exposed_Dev': True,
        'independent_test_accuracy_measured': False, 'fit_performed': False, 'dev_fit_or_checkpoint_selection': False,
        'parameter_sweep': False, 'loss_augmented_inference': False, 'full_roman_or_nct_accuracy_measured': False,
        'candidate_policy_changed': False, 'production_modified': False, 'input_hashes': inputs, 'code_hashes': code,
        'artifact_hashes': artifacts, 'status_counts': {a: dict(Counter(r['arms'][a]['status'] for r in rows)) for a in ARMS},
        'elapsed_seconds': perf_counter()-begun}
    io.write(output/'report.json', final)
    return final


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); r = run(a.output)
    print(json.dumps({k: r[k] for k in ('complete', 'contexts', 'fresh_dev_scopes', 'full_dev_source_packages',
        'previous_cases_preserved', 'status_counts', 'elapsed_seconds')}, ensure_ascii=False, indent=2), flush=True)
