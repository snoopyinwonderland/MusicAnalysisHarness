"""Freeze Train calibration, seal all 72 Dev predictions, then evaluate."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

from . import harmony_member_timing_trial as parent
from . import harmony_full_score as s
from . import harmony_full_score_training as training
from . import harmony_full_score_learning as learning
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_source_clock import SourceClockGuard
from .harmony_structured_learning import content_hash

VERSION = 'harmony-full-score-trial-0.1.0'
BASELINE_SHA = 'c6bced83e4c63681543cf54b84a5de243cec7f8af2d8fc024385460cb9d4ecd4'
ARMS = ('initial_full_score', 'trained_full_score')
load, io, prior = parent.load, parent.expanded, parent.prior


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected: raise ValueError('pinned_input_changed:'+name)
        if name in inputs and inputs[name] != h: raise ValueError('input_changed_during_run:'+name)
        inputs[name] = h
        return None if raw else load(p)
    old_contract = read(source/'run-contract.json'); old_freeze = read(source/'prediction-freeze.json')
    if old_contract['source_labels_used_at_inference'] is not False or old_freeze['dev_labels_read'] is not False:
        raise ValueError('unsealed_baseline')
    for p, h in old_contract['code_pins'].items(): read(p, h, raw=True)
    packets = [read(p, h) for p, h in sorted(old_freeze['prediction_hashes'].items())]
    keys = {(r['pair_id'], r['sample_id']) for r in packets}
    if len(packets) != len(keys) or len(keys) != old_freeze['contexts']: raise ValueError('dev_denominator_changed')
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in [*Path('tests').glob('test_harmony_full_score*.py'), Path('scripts/audit_harmony_full_score.py'),
              Path('scripts/validate_harmony_full_score.py')]:
        if p.exists(): code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'predictions').mkdir(); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        artifacts[str(p.resolve())] = io.digest(p)
        return str(p.resolve())
    train_tick = perf_counter()
    model, use, manifest, dataset, initial = training.prepare(read, save, output)
    trained = learning.model_weights(model, initial, use, manifest, training.parent.old_training.PARENT_SHA)
    weights = dict(zip(ARMS, (initial, trained)))
    model_sha = io.digest(output/'model.json'); train_seconds = perf_counter()-train_tick
    save(output/'run-contract.json', {'version': VERSION, 'baseline_expected_sha256': BASELINE_SHA, 'code_pins': code,
        'arms': ARMS, 'model_sha256': model_sha, 'coefficients': {a: {k: s.q(v) for k, v in w.items()} for a, w in weights.items()},
        'training_pool_report_sha256': training.PINS[training.ROOT+'/report.json'],
        'transition_budget': s.fresh.BUDGET, 'source_labels_used_at_inference': False,
        'training_scope': 'all_65_sealed_current_Train_winner_contrasts',
        'all_existing_score_terms_exposed': True, 'fixed_terms': s.FIXED,
        'known_both_paths_gradient_only': True, 'unknown_domain_not_imputed': True,
        'same_original_dev_graphs': True, 'old_abstentions_not_retried': True,
        'dev_fit_or_checkpoint_selection': False, 'parameter_sweep': False, 'production_modified': False})
    rows, cache = [], {}
    for old in packets:
        key = old['pair_id'], old['sample_id']
        row = {k: deepcopy(old[k]) for k in ('pair_id', 'sample_id', 'sample_span', 'plan_index',
            'collection_id', 'work_family_id', 'reference_binding_verified', 'source_clock_gate', 'attempted', 'known_prior_diagnostic')}
        row['arms'] = {}
        if row['attempted']:
            packet = read(old['graph_artifact'], old['graph_sha256']); prior.check_prediction(packet)
            if (packet['pair_id'], packet['sample_id'], packet['span']) != (*key, row['sample_span']): raise ValueError('graph_scope_changed')
            graph = prior.prior.graph_from_packet(packet['problem'])
            if content_hash(prior.prior.graph_packet(graph)) != content_hash(packet['problem']): raise ValueError('graph_codec_changed')
            row.update(graph_artifact=old['graph_artifact'], graph_sha256=old['graph_sha256'], source=packet['source'])
            if key[0] not in cache:
                src = packet['source']; ir = read(src['canonical_ir_path'])
                if content_hash(ir) != src['original_ir_content_sha256']: raise ValueError('case_ir_changed')
                read(src['source_musicxml_path'], src['original_musicxml_sha256'], raw=True)
                view, grace = prior.prior.bounded.grace_projection(ir)
                cache[key[0]] = ir, view, grace, SourceClockGuard(ir)
            ir, view, grace, clock = cache[key[0]]
            if clock.scope(row['sample_span']) != row['source_clock_gate'] or not row['source_clock_gate']['accepted']:
                raise ValueError('source_clock_changed')
            ev, args = prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            for arm in ARMS:
                begun = perf_counter(); result = s.Scorer(graph, ev, weights[arm], **args).decode()
                if arm == ARMS[0]:
                    baseline = old['arms']['timing_calibrated']['selected_prediction']
                    if ((result['selected'] is None) != (baseline is None) or
                            (baseline is not None and (s.fresh.path_ids(result['selected']) != s.fresh.path_ids(baseline)
                             or result['selected']['score_cost'] != baseline['score_cost']))):
                        raise ValueError('initial_full_score_control_changed')
                if result['selected'] is not None:
                    result['status'] = 'selected_full_score_calibrated_research_hypothesis'
                    result['selected']['full_score']['model_sha256'] = model_sha
                row['arms'][arm] = {'status': result['status'], 'selected_prediction': result['selected'],
                    'elapsed_seconds': perf_counter()-begun, 'transitions': result['transitions'],
                    'exact_optimum_under_declared_score': result['exact_optimum_under_declared_score'],
                    'search_diagnostics': result['search_diagnostics']}
            clock.check_source()
        else:
            row['arms'] = {a: {'status': old['arms']['timing_calibrated']['status'], 'selected_prediction': None,
                'elapsed_seconds': 0, 'reused_old_abstention': True} for a in ARMS}
        row['prediction_artifact'] = save(output/'predictions'/(content_hash(key)[:20]+'.json.gz'), row, True)
        rows.append(row)
        save(output/'progress.json', {'complete': False, 'phase': 'Dev_predictions_before_reference_report_read',
            'scopes': len(rows), 'total': len(packets), 'elapsed_seconds': perf_counter()-tick})
        print(f'[full score Dev {len(rows)}/{len(packets)}] {key[0]}', flush=True)
    if io.digest(output/'model.json') != model_sha: raise ValueError('model_changed_after_training')
    save(output/'prediction-freeze.json', {'version': VERSION, 'model_sha256': model_sha, 'dev_labels_read': False,
        'training_reference_labels_used': True, 'contexts': len(rows),
        'prediction_hashes': {r['prediction_artifact']: artifacts[r['prediction_artifact']] for r in rows}})
    baseline = read(source/'report.json', BASELINE_SHA)
    for p, h in (baseline['input_hashes'] | baseline['code_hashes'] | baseline['artifact_hashes']).items(): read(p, h, raw=True)
    refs = {(r['pair_id'], r['sample_id']): r for r in baseline['records']}
    if set(refs) != keys: raise ValueError('reference_scope_changed')
    old_cases = {(r['pair_id'], r['sample_id']) for r in baseline['cases']}
    changed, cases = [], []
    for row in rows:
        key = row['pair_id'], row['sample_id']; ref = refs[key]
        row['reference_cells'] = deepcopy(ref['reference_cells']); row['candidate_ceiling'] = deepcopy(ref['candidate_ceiling'])
        for a, result in row['arms'].items():
            result['evaluation'] = evaluate(native_reference(row), native_prediction(result['selected_prediction'], row['sample_span']),
                row['sample_span'], selected=result['selected_prediction'] is not None)
        a, b = (row['arms'][a] for a in ARMS)
        different = native_prediction(a['selected_prediction'], row['sample_span']) != native_prediction(b['selected_prediction'], row['sample_span'])
        if different:
            changed.append({'pair_id': key[0], 'sample_id': key[1], 'matched_time_delta': s.q(
                s.f(b['evaluation']['components']['root_members']['matched'])-s.f(a['evaluation']['components']['root_members']['matched']))})
        if row['attempted'] and (different or key in old_cases or row['known_prior_diagnostic']):
            graph = prior.prior.graph_from_packet(read(row['graph_artifact'])['problem'])
            ir, view, grace, clock = cache[key[0]]; ev, args = prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            scorers = {a: s.Scorer(graph, ev, w, **args) for a, w in weights.items()}
            case = {'record': row, 'source': row['source'], 'model_sha256': model_sha,
                'selected_path_receipts': {a: scorers[a].receipt(s.fresh.path_ids(v['selected_prediction']))
                    for a, v in row['arms'].items() if v['selected_prediction'] is not None},
                'human_validated': False, 'independent_test_case': False, 'reference_witness_never_used_for_inference': True}
            witness = ref['candidate_ceiling'].get('oracle_reference_witness') if ref['candidate_ceiling'] else None
            if witness: case['reference_witness_receipts'] = {a: sc.receipt(witness, target=True) for a, sc in scorers.items()}
            cases.append({'pair_id': key[0], 'sample_id': key[1], 'case_path': save(output/'cases'/(content_hash(key)[:20]+'.json.gz'), case, True)})
    tables = {a: summarize([r | r['arms'][a] for r in rows]) for a in ARMS}
    if tables[ARMS[0]] != baseline['tables']['timing_calibrated']: raise ValueError('initial_full_score_metric_changed')
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('guard_changed:'+p)
    train_families = set(model['training_families']); dev_families = {r['work_family_id'] for r in rows}
    report = {'version': VERSION, 'complete': True, 'contexts': len(rows), 'fresh_dev_scopes': sum(r['attempted'] for r in rows),
        'full_dev_source_packages': len(cache), 'tables': tables, 'changed': changed, 'cases': cases, 'records': rows,
        'model_sha256': model_sha, 'training_counts': dataset['counts'], 'training_families': sorted(train_families),
        'dev_families': sorted(dev_families), 'named_family_overlap': sorted(train_families & dev_families),
        'full_duplicate_audit_performed': False, 'model_frozen_before_dev_predictions': True,
        'all_current_dev_predictions_sealed_before_reference_report_read': True,
        'loaded_parent_containers_include_exposed_Dev': True, 'independent_test_accuracy_measured': False,
        'dev_fit_or_checkpoint_selection': False, 'parameter_sweep': False, 'full_roman_or_nct_accuracy_measured': False,
        'fresh_adversary_search_during_fit': False, 'candidate_policy_changed': False, 'production_modified': False,
        'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'status_counts': {a: dict(Counter(r['arms'][a]['status'] for r in rows)) for a in ARMS},
        'training_seconds': train_seconds, 'elapsed_seconds': perf_counter()-tick}
    io.write(output/'report.json', report)
    return {k: v for k, v in report.items() if k not in ('records', 'input_hashes', 'code_hashes', 'artifact_hashes', 'tables', 'changed', 'cases')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--source', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); print(json.dumps(run(a.source, a.output), ensure_ascii=False, indent=2), flush=True)
