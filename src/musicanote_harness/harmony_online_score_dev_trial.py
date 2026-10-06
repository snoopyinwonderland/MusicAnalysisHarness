"""Evaluate the already frozen online model on ALL unchanged exposed Dev scopes.

No fit, coefficient sweep, reference-compatible decoder or candidate changes.
Both ordinary arms are sealed before evaluation reference reports are opened.
Historical lineage containers were already exposed; this is NOT a blind Test.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

from . import harmony_full_score_trial as prior
from . import harmony_online_score_learning as learning
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize

s, io, load = learning.s, prior.io, prior.load
VERSION = 'harmony-online-full-score-dev-trial-0.1.0'
ARMS = ('initial_full_score', 'online_frozen_full_score')
MODEL_ROOT = 'output/harmony-online-score-2026-10-05-r1'
MODEL_PINS = {
    'report.json': '2c442cc37756e26958d550da90c238ecef8fb6792a00cfd9274edf40d75860d1',
    'model.json.gz': '029e2de31ab6e5d9e5fa65eb229c63fe649cce10ddd987dbab4c2b7f3f06f331',
    'model-freeze.json': 'a07e5b902424fd2798cd43fdf55788e37b9ae19f59573a27f80a878cb573ce50',
    'post-seal-audit.json': '6da04003ca3a48617058e8dc3ced1e5975fdc9e5a449a530495d22567f30421f'}
SOURCE_ROOT = 'output/harmony-member-timing-2026-10-05-r1'
SOURCE_PINS = {
    'run-contract.json': 'c83c42419853cd90982da1ea7f71bc27884e1265eac67a2c2c63f8db3a4d4453',
    'prediction-freeze.json': '31145b9d07f4b8373dd888de2b8bca9ac71e4e782c14c754451d5bf2f466821c',
    'report.json': prior.BASELINE_SHA}
PREVIOUS_DEV_ROOT = 'output/harmony-full-score-2026-10-05-r1'
PREVIOUS_DEV_SHA = '3269a812a414d9e59babae34a090aa84ed91c0fbcbf7c244c79f6d1838d57e53'


def check_model_seal(report, audit, freeze, model_sha):
    if (report.get('complete') is not True or audit.get('passed') is not True
            or audit.get('report_sha256') != MODEL_PINS['report.json']
            or report.get('model_sha256') != model_sha
            or freeze.get('model_sha256') != model_sha
            or freeze.get('all_epochs_averaged') is not True
            or freeze.get('dev_labels_used') is not False
            or report.get('dev_used_for_fit') is not False
            or report.get('dev_inference_or_evaluation') is not False
            or report.get('production_modified') is not False):
        raise ValueError('unsealed_or_nontrain_online_model')


def frozen_weights(read):
    """Validate existing Train model/rights without fitting it again."""
    report, model, freeze, audit = [read(Path(MODEL_ROOT)/p, h) for p, h in MODEL_PINS.items()]
    check_model_seal(report, audit, freeze, MODEL_PINS['model.json.gz'])
    for p, h in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items():
        read(p, h, raw=True)
    training = prior.training.parent
    containers = [read(p, h) for p, h in training.old_training.PINS.items()]
    recall, use = containers[1], containers[3]
    manifest = recall['package_manifest']
    approvals = training.validate_use_contract(use, manifest, training.old_training.PARENT_SHA)
    for approval in approvals.values():
        license = approval['source_license']
        for name in ('local_license', 'readme'):
            read(license[name+'_path'], license[name+'_sha256'], raw=True)
    fixed = training.old_training.old_learning.model_weights(
        read(training.old_training.SUPPORT_MODEL, training.old_training.SUPPORT_MODEL_SHA),
        use, manifest, training.old_training.PARENT_SHA)
    timing = training.timing_learning.model_weights(read(training.TIMING_MODEL, training.TIMING_MODEL_SHA),
        use, manifest, training.old_training.PARENT_SHA)
    initial = s.initial_weights(fixed | timing)
    learned = learning.model_weights(model, initial, use, manifest, training.old_training.PARENT_SHA)
    return dict(zip(ARMS, (initial, learned))), model


def packet_keys(packets, expected_count):
    keys = {(r['pair_id'], r['sample_id']) for r in packets}
    if len(packets) != len(keys) or len(keys) != expected_count:
        raise ValueError('dev_scope_inventory_changed')
    # Keep partial, absent-reference-path and original abstained scopes too.
    return keys


def ordinary(graph, evidence, weights, args):
    return s.Scorer(graph, evidence, weights, **args).decode()


def check_initial_control(result, baseline):
    selected = result['selected']
    if ((selected is None) != (baseline is None) or
            (selected is not None and (s.fresh.path_ids(selected) != s.fresh.path_ids(baseline)
                                      or selected['score_cost'] != baseline['score_cost']))):
        raise ValueError('online_dev_initial_control_changed')


def seal_and_open_reference(read, save, output, rows, model_sha):
    save(output/'prediction-freeze.json', {'version': VERSION, 'model_sha256': model_sha,
        'dev_labels_read': False, 'contexts': len(rows), 'fit_performed': False,
        'prediction_hashes': {r['prediction_artifact']: io.digest(r['prediction_artifact']) for r in rows}})
    return read(Path(SOURCE_ROOT)/'report.json', SOURCE_PINS['report.json'])


def changed_rows(rows):
    changed = []
    for row in rows:
        a, b = (row['arms'][arm] for arm in ARMS)
        if native_prediction(a['selected_prediction'], row['sample_span']) != native_prediction(b['selected_prediction'], row['sample_span']):
            changed.append({'pair_id': row['pair_id'], 'sample_id': row['sample_id'],
                'matched_time_delta': s.q(s.f(b['evaluation']['components']['root_members']['matched'])
                                        -s.f(a['evaluation']['components']['root_members']['matched']))})
    return changed


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected: raise ValueError('online_dev_pinned_input_changed:'+name)
        if name in inputs and inputs[name] != h: raise ValueError('online_dev_input_changed:'+name)
        inputs[name] = h
        return None if raw else load(p)
    weights, model = frozen_weights(read)
    old_contract = read(Path(SOURCE_ROOT)/'run-contract.json', SOURCE_PINS['run-contract.json'])
    old_freeze = read(Path(SOURCE_ROOT)/'prediction-freeze.json', SOURCE_PINS['prediction-freeze.json'])
    if old_contract['source_labels_used_at_inference'] is not False or old_freeze['dev_labels_read'] is not False:
        raise ValueError('unsealed_online_dev_baseline')
    for p, h in old_contract['code_pins'].items(): read(p, h, raw=True)
    packets = [read(p, h) for p, h in sorted(old_freeze['prediction_hashes'].items())]
    keys = packet_keys(packets, old_freeze['contexts'])
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in [Path('tests/test_harmony_online_score_dev_trial.py'), Path('scripts/audit_harmony_online_score_dev.py'),
              Path('scripts/validate_harmony_online_score_dev.py')]:
        if p.exists(): code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'predictions').mkdir(); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name
    model_sha = MODEL_PINS['model.json.gz']
    save(output/'run-contract.json', {'version': VERSION, 'code_pins': code, 'arms': ARMS,
        'source_pins': SOURCE_PINS, 'model_pins': MODEL_PINS, 'model_sha256': model_sha,
        'coefficients': {a: {k: s.q(v) for k, v in w.items()} for a, w in weights.items()},
        'model_frozen_before_dev_predictions': True, 'source_labels_used_at_inference': False,
        'fit_performed': False, 'dev_fit_or_checkpoint_selection': False, 'parameter_sweep': False,
        'transition_budget': s.fresh.BUDGET, 'same_original_dev_graphs': True,
        'original_abstentions_not_retried': True, 'reference_reachable_filter_applied': False,
        'purpose': 'local_noncommercial_research', 'production_modified': False})
    rows, cache = [], {}
    for old in packets:
        key = old['pair_id'], old['sample_id']
        row = {k: deepcopy(old[k]) for k in ('pair_id', 'sample_id', 'sample_span', 'plan_index',
            'collection_id', 'work_family_id', 'reference_binding_verified', 'source_clock_gate', 'attempted', 'known_prior_diagnostic')}
        row['arms'] = {}
        if row['attempted']:
            packet = read(old['graph_artifact'], old['graph_sha256']); prior.prior.check_prediction(packet)
            if (packet['pair_id'], packet['sample_id'], packet['span']) != (*key, row['sample_span']):
                raise ValueError('online_dev_graph_scope_changed')
            graph = prior.prior.prior.graph_from_packet(packet['problem'])
            if prior.content_hash(prior.prior.prior.graph_packet(graph)) != prior.content_hash(packet['problem']):
                raise ValueError('online_dev_graph_codec_changed')
            row.update(graph_artifact=old['graph_artifact'], graph_sha256=old['graph_sha256'], source=packet['source'])
            if key[0] not in cache:
                src = packet['source']; ir = read(src['canonical_ir_path'])
                if prior.content_hash(ir) != src['original_ir_content_sha256']: raise ValueError('online_dev_ir_changed')
                read(src['source_musicxml_path'], src['original_musicxml_sha256'], raw=True)
                view, grace = prior.prior.prior.bounded.grace_projection(ir)
                cache[key[0]] = ir, view, grace, prior.SourceClockGuard(ir)
            ir, view, grace, clock = cache[key[0]]
            if clock.scope(row['sample_span']) != row['source_clock_gate'] or not row['source_clock_gate']['accepted']:
                raise ValueError('online_dev_clock_changed')
            ev, args = prior.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            for arm in ARMS:
                tick = perf_counter(); result = ordinary(graph, ev, weights[arm], args)
                if arm == ARMS[0]: check_initial_control(result, old['arms']['timing_calibrated']['selected_prediction'])
                if result['selected'] is not None:
                    result['selected']['full_score']['model_sha256'] = model_sha if arm == ARMS[1] else None
                row['arms'][arm] = {'status': result['status'], 'selected_prediction': result['selected'],
                    'elapsed_seconds': perf_counter()-tick, 'transitions': result['transitions'],
                    'exact_optimum_under_declared_score': result['exact_optimum_under_declared_score'],
                    'search_diagnostics': result['search_diagnostics']}
            clock.check_source()
        else:
            row['arms'] = {a: {'status': old['arms']['timing_calibrated']['status'], 'selected_prediction': None,
                'elapsed_seconds': 0, 'reused_old_abstention': True} for a in ARMS}
        row['prediction_artifact'] = save(output/'predictions'/(prior.content_hash(key)[:20]+'.json.gz'), row, True)
        rows.append(row)
        save(output/'progress.json', {'complete': False, 'phase': 'Dev_predictions_before_reference_report_read',
            'scopes': len(rows), 'total': len(packets), 'elapsed_seconds': perf_counter()-begun})
        print(f'[online frozen Dev {len(rows)}/{len(packets)}] {key[0]}', flush=True)
    baseline = seal_and_open_reference(read, save, output, rows, model_sha)
    for p, h in (baseline['input_hashes'] | baseline['code_hashes'] | baseline['artifact_hashes']).items(): read(p, h, raw=True)
    refs = {(r['pair_id'], r['sample_id']): r for r in baseline['records']}
    if set(refs) != keys or len(refs) != len(baseline['records']): raise ValueError('online_dev_reference_inventory_changed')
    previous = read(Path(PREVIOUS_DEV_ROOT)/'report.json', PREVIOUS_DEV_SHA)
    old_cases = {(r['pair_id'], r['sample_id']): r for r in previous['cases']}
    for item in old_cases.values(): read(item['case_path'], previous['artifact_hashes'][item['case_path']], raw=True)
    cases = []
    for row in rows:
        key = row['pair_id'], row['sample_id']; ref = refs[key]
        row['reference_cells'] = deepcopy(ref['reference_cells']); row['candidate_ceiling'] = deepcopy(ref['candidate_ceiling'])
        for result in row['arms'].values():
            result['evaluation'] = evaluate(native_reference(row), native_prediction(result['selected_prediction'], row['sample_span']),
                row['sample_span'], selected=result['selected_prediction'] is not None)
        a, b = (row['arms'][a] for a in ARMS)
        different = native_prediction(a['selected_prediction'], row['sample_span']) != native_prediction(b['selected_prediction'], row['sample_span'])
        if row['attempted'] and (different or key in old_cases or row['known_prior_diagnostic']):
            graph = prior.prior.prior.graph_from_packet(read(row['graph_artifact'])['problem'])
            ir, view, grace, clock = cache[key[0]]
            ev, args = prior.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            scorers = {a: s.Scorer(graph, ev, w, **args) for a, w in weights.items()}
            case = {'record': row, 'source': row['source'], 'model_sha256': model_sha,
                'selected_path_receipts': {a: scorers[a].receipt(s.fresh.path_ids(v['selected_prediction']))
                    for a, v in row['arms'].items() if v['selected_prediction'] is not None},
                'human_validated': False, 'independent_test_case': False, 'reference_witness_never_used_for_inference': True,
                'previous_case_artifact': old_cases[key]['case_path'] if key in old_cases else None}
            witness = ref['candidate_ceiling'].get('oracle_reference_witness') if ref['candidate_ceiling'] else None
            if witness: case['reference_witness_receipts'] = {a: sc.receipt(witness, target=True) for a, sc in scorers.items()}
            cases.append({'pair_id': key[0], 'sample_id': key[1],
                'case_path': save(output/'cases'/(prior.content_hash(key)[:20]+'.json.gz'), case, True)})
    tables = {a: summarize([r | r['arms'][a] for r in rows]) for a in ARMS}
    if tables[ARMS[0]] != baseline['tables']['timing_calibrated']: raise ValueError('online_dev_initial_metric_changed')
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('online_dev_guard_changed:'+p)
    train_families = set(model['training_families']); dev_families = {r['work_family_id'] for r in rows}
    changed = changed_rows(rows)
    final = {'version': VERSION, 'complete': True, 'contexts': len(rows), 'fresh_dev_scopes': sum(r['attempted'] for r in rows),
        'full_dev_source_packages': len(cache), 'model_sha256': model_sha, 'tables': tables,
        'records': rows, 'cases': cases, 'changed': changed,
        'previously_correct_lost': sum(r['arms'][ARMS[0]]['evaluation']['selected_hit'] is True and
            r['arms'][ARMS[1]]['evaluation']['selected_hit'] is not True for r in rows),
        'newly_correct': sum(r['arms'][ARMS[0]]['evaluation']['selected_hit'] is not True and
            r['arms'][ARMS[1]]['evaluation']['selected_hit'] is True for r in rows),
        'training_families': sorted(train_families), 'dev_families': sorted(dev_families),
        'named_family_overlap': sorted(train_families & dev_families), 'full_duplicate_audit_performed': False,
        'model_frozen_before_dev_predictions': True, 'all_dev_predictions_sealed_before_reference_report_read': True,
        'loaded_parent_containers_include_exposed_Dev': True, 'independent_test_accuracy_measured': False,
        'fit_performed': False, 'dev_fit_or_checkpoint_selection': False, 'parameter_sweep': False,
        'full_roman_or_nct_accuracy_measured': False, 'candidate_policy_changed': False, 'production_modified': False,
        'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'status_counts': {a: dict(Counter(r['arms'][a]['status'] for r in rows)) for a in ARMS},
        'elapsed_seconds': perf_counter()-begun}
    io.write(output/'report.json', final)
    return {k: v for k, v in final.items() if k not in ('records', 'cases', 'changed', 'input_hashes', 'code_hashes', 'artifact_hashes')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); print(json.dumps(run(a.output), ensure_ascii=False, indent=2), flush=True)
