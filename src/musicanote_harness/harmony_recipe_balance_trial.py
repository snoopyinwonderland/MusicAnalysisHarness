"""Joint choice on all 72 exposed Dev scopes; no new candidate or Dev fit."""
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json

from . import harmony_support_balance_trial as parent
from . import harmony_recipe_balance as scoring
from . import harmony_recipe_balance_training as training
from . import harmony_recipe_balance_learning as learning
from .harmony_source_clock import SourceClockGuard
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_progression_search import _hash

VERSION = 'harmony-recipe-balance-trial-0.1.0'
ARMS = ('support_calibrated', 'recipe_calibrated')
BASELINE_REPORT_SHA = '8039377b21f798a4b60077eabe7a636d5bcbf00bf5c233ad51dddd627247abee'
load, expanded, prior = parent.load, parent.expanded, parent.prior


def path_receipt(scorer, ids):
    values, available = scorer.path_features(ids)
    return {'existing_path_ids': ids, 'base_cost': scoring.support.q(scorer.base_cost(ids)),
        'trained_cost': scoring.support.q(scorer.score_path(ids)),
        'support_features': {k: scoring.support.q(v) for k, v in values.items()}, 'availability': available,
        'source_support': [d for a, b, sig in scoring.support.completed_runs(scorer.problem, ids)
                           for d in scoring.features(scorer.problem, scorer.ev.source, a, b, sig)[1]],
        'source_labels_used_to_create_this_path': False}


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    started = perf_counter(); guards = {}; artifacts = {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); sha = expanded.digest(p); name = str(p.resolve())
        if expected is not None and sha != expected: raise ValueError('pinned_input_changed:'+str(p))
        if name in guards and guards[name] != sha: raise ValueError('input_changed_during_read')
        guards[name] = sha
        return None if raw else load(p)
    contract = read(source/'run-contract.json'); freeze = read(source/'prediction-freeze.json')
    if freeze['labels_read'] is not False or contract['source_labels_used_at_inference'] is not False:
        raise ValueError('unsealed_baseline')
    for p, h in contract['code_pins'].items(): read(p, h, raw=True)
    packets = [read(p, h) for p, h in sorted(freeze['prediction_hashes'].items())]
    keys = {(p['pair_id'], p['sample_id']) for p in packets}
    if len(packets) != len(keys) or len(keys) != freeze['contexts']:
        raise ValueError('scope_denominator_changed')
    for packet in packets: prior.check_prediction(packet)
    code = {str(p.resolve()): expanded.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in [*Path('tests').glob('test_harmony_recipe_balance*.py'),
              Path('scripts/audit_harmony_recipe_balance.py'), Path('scripts/validate_harmony_recipe_balance.py')]:
        if p.exists(): code[str(p.resolve())] = expanded.digest(p)
    output.mkdir(parents=True); (output/'predictions').mkdir(); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (expanded.write_packet if compressed else expanded.write)(p, value)
        artifacts[str(p.resolve())] = expanded.digest(p)
        return str(p.resolve())
    train_started = perf_counter()
    model, use_contract, manifest, dataset, fixed = training.prepare(read, save, output)
    residual = learning.model_weights(model, use_contract, manifest, training.PARENT_SHA)
    values = fixed | residual; control = fixed | {scoring.FEATURE: scoring.F()}
    model_sha = expanded.digest(output/'model.json'); train_seconds = perf_counter()-train_started
    save(output/'run-contract.json', {'version': VERSION, 'baseline_source': str(source.resolve()),
        'baseline_report_expected_sha256': BASELINE_REPORT_SHA, 'code_pins': code, 'arms': ARMS,
        'model_sha256': model_sha, 'frozen_support_model_path': str(Path(training.SUPPORT_MODEL).resolve()),
        'frozen_support_model_sha256': training.SUPPORT_MODEL_SHA,
        'coefficients': {k: scoring.support.q(v) for k, v in values.items()},
        'same_original_dev_graphs': True, 'old_abstentions_not_retried': True, 'transition_budget': 2_000_000,
        'training_scope': 'approved_Train_historical_path_contrasts_only', 'only_new_recipe_coefficient_fitted': True,
        'dev_labels_used_for_training_or_parameter_selection': False, 'source_labels_used_at_inference': False,
        'parameter_sweep': False, 'independent_test_accuracy_measured': False, 'production_modified': False})
    rows = []; cache = {}
    for old in packets:
        key = old['pair_id'], old['sample_id']
        row = {k: deepcopy(old[k]) for k in ('pair_id', 'sample_id', 'sample_span', 'plan_index',
            'collection_id', 'work_family_id', 'reference_binding_verified', 'source_clock_gate',
            'attempted', 'known_prior_diagnostic')}
        row['arms'] = {}
        if row['attempted']:
            packet = read(old['graph_artifact'], old['graph_sha256']); prior.check_prediction(packet)
            if (packet['pair_id'], packet['sample_id'], packet['span']) != (*key, row['sample_span']):
                raise ValueError('graph_scope_changed')
            graph = prior.prior.graph_from_packet(packet['problem'])
            if _hash(prior.prior.graph_packet(graph)) != _hash(packet['problem']):
                raise ValueError('graph_codec_changed')
            row.update(graph_artifact=old['graph_artifact'], graph_sha256=old['graph_sha256'], source=packet['source'])
            if key[0] not in cache:
                src = packet['source']; ir = read(src['canonical_ir_path'])
                if _hash(ir) != src['original_ir_content_sha256']: raise ValueError('case_ir_changed')
                read(src['source_musicxml_path'], src['original_musicxml_sha256'], raw=True)
                view, grace = prior.prior.bounded.grace_projection(ir)
                cache[key[0]] = ir, view, grace, SourceClockGuard(ir)
            ir, view, grace, clock = cache[key[0]]
            gate = clock.scope(row['sample_span'])
            if not gate['accepted'] or _hash(gate) != _hash(row['source_clock_gate']):
                raise ValueError('source_clock_gate_changed')
            ev, args = prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            for arm in ARMS:
                tick = perf_counter()
                scorer = scoring.Scorer(graph, ev, values if arm == 'recipe_calibrated' else control, **args)
                result = scorer.decode()
                if arm == 'support_calibrated' and _hash(prior.prior.musical_value(result['selected'])) != _hash(
                        prior.prior.musical_value(old['arms']['train_calibrated']['selected_prediction'])):
                    raise ValueError('fresh_support_control_changed')
                if result['selected'] is not None:
                    result['status'] = 'selected_train_calibrated_research_hypothesis'
                    result['selected']['support_balance']['model_sha256'] = (
                        model_sha if arm == 'recipe_calibrated' else training.SUPPORT_MODEL_SHA)
                row['arms'][arm] = {'status': result['status'], 'selected_prediction': result['selected'],
                    'elapsed_seconds': perf_counter()-tick, 'transitions': result['transitions'],
                    'exact_optimum_under_declared_score': result['exact_optimum_under_declared_score'],
                    'search_diagnostics': result['search_diagnostics'],
                    'recipe_balance_contract': result['recipe_balance_contract']}
            clock.check_source()
        else:
            row['arms'] = {a: {'status': old['arms']['train_calibrated']['status'], 'selected_prediction': None,
                'elapsed_seconds': 0, 'reused_old_abstention': True} for a in ARMS}
        row['prediction_artifact'] = save(output/'predictions'/(_hash(key)[:20]+'.json.gz'), row, True)
        rows.append(row)
        save(output/'progress.json', {'complete': False, 'phase': 'Dev_predictions_before_reference_read',
                                     'scopes': len(rows), 'elapsed_seconds': perf_counter()-started})
        print(f"[recipe balance {len(rows)}/{len(packets)}] {key[0]}: "+', '.join(a+':'+v['status'] for a, v in row['arms'].items()), flush=True)
    if expanded.digest(output/'model.json') != model_sha: raise ValueError('model_changed_after_training')
    save(output/'prediction-freeze.json', {'version': VERSION, 'labels_read': False, 'dev_labels_read': False,
        'training_reference_labels_used': True, 'model_sha256': model_sha, 'contexts': len(rows),
        'prediction_hashes': {r['prediction_artifact']: artifacts[r['prediction_artifact']] for r in rows}})
    baseline = read(source/'report.json', BASELINE_REPORT_SHA)
    for p, h in (baseline['input_hashes'] | baseline['code_hashes'] | baseline['artifact_hashes']).items():
        read(p, h, raw=True)
    refs = {(r['pair_id'], r['sample_id']): r for r in baseline['records']}
    if set(refs) != keys: raise ValueError('reference_scope_changed')
    old_cases = {(r['pair_id'], r['sample_id']) for r in baseline['cases']}
    changed = []; cases = []
    for row in rows:
        key = row['pair_id'], row['sample_id']; ref = refs[key]
        row['reference_cells'] = deepcopy(ref['reference_cells'])
        row['candidate_ceiling'] = deepcopy(ref['candidate_ceiling'])
        for arm, result in row['arms'].items():
            result['evaluation'] = evaluate(native_reference(row), native_prediction(result['selected_prediction'],
                row['sample_span']), row['sample_span'], selected=result['selected_prediction'] is not None)
        a, b = (row['arms'][arm] for arm in ARMS)
        different = _hash(native_prediction(a['selected_prediction'], row['sample_span'])) != _hash(
            native_prediction(b['selected_prediction'], row['sample_span']))
        if different:
            changed.append({'pair_id': key[0], 'sample_id': key[1], 'matched_time_delta': scoring.support.q(
                scoring.support.f(b['evaluation']['components']['root_members']['matched'])-
                scoring.support.f(a['evaluation']['components']['root_members']['matched']))})
        if row['attempted'] and (different or key in old_cases or row['known_prior_diagnostic']):
            graph = prior.prior.graph_from_packet(read(row['graph_artifact'])['problem'])
            ir, view, grace, clock = cache[key[0]]
            ev, args = prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            scorer = scoring.Scorer(graph, ev, values, **args)
            case = {'record': row, 'source': row['source'], 'model_sha256': model_sha,
                'scored_selected_paths': {a: path_receipt(scorer, prior.prior.path_ids(v['selected_prediction']))
                    for a, v in row['arms'].items() if v['selected_prediction'] is not None},
                'human_validated': False, 'independent_test_case': False,
                'reference_witness_never_used_for_inference': True}
            witness = ref['candidate_ceiling'].get('oracle_reference_witness') if ref['candidate_ceiling'] else None
            if witness:
                case['reference_witness_scores'] = path_receipt(scorer, witness)
                case['reference_witness_scores']['source_labels_used_to_create_this_path'] = True
            cases.append({'pair_id': key[0], 'sample_id': key[1],
                'case_path': save(output/'cases'/(_hash(key)[:20]+'.json.gz'), case, True)})
    tables = {a: summarize([r | r['arms'][a] for r in rows]) for a in ARMS}
    if tables['support_calibrated'] != baseline['tables']['train_calibrated']:
        raise ValueError('support_control_metric_changed')
    for p, h in (guards | code | artifacts).items():
        if expanded.digest(p) != h: raise ValueError('guard_changed:'+p)
    train_families = set(model['training_families']); dev_families = {r['work_family_id'] for r in rows}
    report = {'version': VERSION, 'complete': True, 'contexts': len(rows),
        'fresh_selected_scopes': sum(r['attempted'] for r in rows), 'full_source_packages': len(cache),
        'tables': tables, 'previous_step66_control_table': baseline['tables']['control'],
        'changed': changed, 'cases': cases, 'records': rows, 'model_sha256': model_sha,
        'training_counts': dataset['counts'], 'training_families': sorted(train_families),
        'dev_families': sorted(dev_families), 'named_family_overlap': sorted(train_families & dev_families),
        'full_duplicate_audit_performed': False, 'input_hashes': guards, 'code_hashes': code,
        'artifact_hashes': artifacts, 'status_counts': {a: dict(Counter(r['arms'][a]['status'] for r in rows)) for a in ARMS},
        'all_dev_predictions_sealed_before_reference_report_read': True, 'model_frozen_before_dev_predictions': True,
        'training_performed': True, 'training_reference_labels_used': True, 'historical_negative_pool_complete': False,
        'fresh_adversary_search': False, 'source_labels_used_at_inference': False,
        'dev_labels_used_for_training_or_parameter_selection': False, 'parameter_sweep': False,
        'independent_test_accuracy_measured': False, 'full_roman_accuracy_measured': False,
        'complete_nct_accuracy_measured': False, 'new_rules_adopted_for_production': False,
        'production_modified': False, 'dev_graph_generation_performed': False,
        'training_seconds': train_seconds, 'elapsed_seconds': perf_counter()-started}
    expanded.write(output/'report.json', report)
    return {k: v for k, v in report.items() if k not in ('records', 'input_hashes', 'code_hashes',
             'artifact_hashes', 'tables', 'previous_step66_control_table', 'changed', 'cases')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); print(json.dumps(run(a.source, a.output), ensure_ascii=False, indent=2), flush=True)
