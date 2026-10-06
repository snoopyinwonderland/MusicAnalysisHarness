"""Replay fixed Dev scores, source bindings, all cases and metrics; no search/fit."""
import argparse
from collections import Counter
import json
from pathlib import Path
from musicanote_harness import harmony_joint_balance_dev_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); contract = t.load(root/'run-contract.json'); freeze = t.load(root/'prediction-freeze.json')
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('frozen_dev_audit_pin_changed:'+p)
    check()
    flags = ('fit_performed', 'parameter_sweep', 'loss_augmented_inference', 'dev_fit_or_checkpoint_selection',
             'candidate_policy_changed', 'production_modified', 'independent_test_accuracy_measured',
             'full_roman_or_local_key_or_nct_accuracy_measured', 'operational_weights_changed')
    if (report['complete'] is not True or any(report.get(k) is not False for k in flags)
            or freeze['dev_labels_read'] is not False or freeze['fit_performed'] is not False
            or freeze['model_sha256_by_arm'] != t.MODEL_SHAS or report['model_sha256_by_arm'] != t.MODEL_SHAS
            or len(freeze['prediction_hashes']) != report['contexts']
            or contract['source_labels_used_at_inference'] is not False
            or contract['original_abstentions_not_retried'] is not True
            or contract['reference_reachable_filter_applied'] is not False
            or contract['wall_seconds_per_arm'] != t.WALL_SECONDS
            or contract['transition_budget'] != t.s.fresh.BUDGET
            or contract['arm_order_fixed_before_results'] is not True
            or contract['fresh_feature_cache_per_arm'] is not True
            or report['all_dev_predictions_sealed_before_reference_report_read'] is not True):
        raise ValueError('frozen_dev_audit_contract_changed')
    def read(p, expected=None, compressed=False, raw=False):
        if expected and t.io.digest(p) != expected: raise ValueError('frozen_dev_audit_expected_pin_changed:'+str(p))
        if str(Path(p).resolve()) not in report['input_hashes']: raise ValueError('frozen_dev_audit_unsealed_input:'+str(p))
        return None if raw else t.load(p)
    weights, ctx = t.frozen_weights(read)
    if not t.same_json(contract['coefficients'], {a: {k: t.s.q(v) for k, v in w.items()} for a, w in weights.items()}):
        raise ValueError('frozen_dev_audit_coefficient_changed')
    source = read(t.SOURCE_ROOT/'report.json', t.SOURCE_PINS['report.json'])
    historical = read(t.PREVIOUS_ROOT/'report.json', t.PREVIOUS_PINS['report.json'])
    original_freeze = read(t.SOURCE_ROOT/'prediction-freeze.json', t.SOURCE_PINS['prediction-freeze.json'])
    originals = {(r['pair_id'], r['sample_id']): r for r in
                 (read(p, h) for p, h in original_freeze['prediction_hashes'].items())}
    refs = {(r['pair_id'], r['sample_id']): r for r in source['records']}
    previous = {(r['pair_id'], r['sample_id']): r for r in historical['records']}
    old_cases = {(r['pair_id'], r['sample_id']): r for r in historical['cases']}
    cases = {(r['pair_id'], r['sample_id']): r for r in report['cases']}
    keys = t.previous.packet_keys(report['records'], original_freeze['contexts'])
    if keys != set(refs) or keys != set(previous) or keys != set(originals): raise ValueError('frozen_dev_audit_inventory_changed')
    attempted = {k for k, r in originals.items() if r['attempted']}
    if (t.previous.packet_keys(report['cases'], len(attempted)) != attempted or not set(old_cases) <= attempted
            or report['previous_cases_preserved'] != len(old_cases)):
        raise ValueError('frozen_dev_audit_source_case_missing')
    cache = {}; costs = cross_costs = witness_costs = projections = edges = abstain = control = control_abstain = 0
    for i, row in enumerate(report['records'], 1):
        key = row['pair_id'], row['sample_id']; original = originals[key]
        path = row['prediction_artifact']; raw = t.load(path)
        if t.io.digest(path) != freeze['prediction_hashes'].get(path): raise ValueError('frozen_dev_audit_prediction_not_frozen')
        if (any(k in raw for k in ('reference_cells', 'candidate_ceiling'))
                or any('evaluation' in v for v in raw['arms'].values())):
            raise ValueError('frozen_dev_audit_labels_in_raw_prediction')
        for k in t.FIELDS:
            if not t.same_json(row[k], original[k]) or not t.same_json(raw[k], row[k]):
                raise ValueError('frozen_dev_audit_original_field_changed:'+k)
        for k in ('reference_cells', 'candidate_ceiling'):
            if not t.same_json(row[k], refs[key][k]): raise ValueError('frozen_dev_audit_reference_changed')
        if set(row['arms']) != set(t.ARMS): raise ValueError('frozen_dev_audit_arms_changed')
        if row['attempted']:
            for k in ('graph_artifact', 'graph_sha256'):
                if row[k] != original[k] or row[k] != raw[k]: raise ValueError('frozen_dev_audit_graph_changed')
            graph, src, ir, view, grace, clock = t.prepare(row, read, cache); edges += len(graph.edges)
            if not t.same_json(src, row['source']) or not t.same_json(src, raw['source']):
                raise ValueError('frozen_dev_audit_source_binding_changed')
            case = t.load(cases[key]['case_path'])
            if (not t.same_json(case['record'], row) or not t.same_json(case['source'], src)
                    or case['human_validated'] is not False or case['independent_test_case'] is not False
                    or case['reference_witness_never_used_for_inference'] is not True
                    or case['model_sha256_by_arm'] != t.MODEL_SHAS
                    or case['previous_case_artifact'] != (old_cases[key]['case_path'] if key in old_cases else None)):
                raise ValueError('frozen_dev_audit_case_binding_changed')
        else: abstain += 1
        paths = {a: t.s.fresh.path_ids(v['selected_prediction']) for a, v in row['arms'].items()
                 if v['selected_prediction'] is not None}
        witness = (row['candidate_ceiling'] or {}).get('oracle_reference_witness')
        for a, value in row['arms'].items():
            if not t.same_json(raw['arms'][a], {k: v for k, v in value.items() if k != 'evaluation'}):
                raise ValueError('frozen_dev_audit_prediction_changed_after_seal')
            selected = value['selected_prediction']
            if not row['attempted']:
                if not t.same_json(value | {}, t.original_abstention(original) | {'evaluation': value['evaluation']}):
                    raise ValueError('frozen_dev_audit_old_abstention_retried')
            else:
                result = value['result']; guard = result['resource_guard']
                if (not t.same_json(result['selected'], selected) or result['status'] != value['status']
                        or guard['wall_seconds'] != t.WALL_SECONDS or guard['transition_budget'] != t.s.fresh.BUDGET
                        or guard['raw_segment_cap'] != graph.max_segments
                        or guard['elapsed_seconds'] != value['elapsed_seconds']
                        or result['frozen_model_ref']['model_sha256'] != t.MODEL_SHAS[a]
                        or result['frozen_dev_contract']['all_35_weights_frozen'] is not True
                        or result['frozen_dev_contract']['fit_performed_this_trial'] is not False
                        or result['frozen_dev_contract']['source_labels_used_for_selection'] is not False):
                    raise ValueError('frozen_dev_audit_arm_contract_changed')
                if selected is None and result.get('partial_winner_returned', False) is not False:
                    raise ValueError('frozen_dev_audit_partial_winner_returned')
                ev, args = t.evidence(ir, view, grace, row['sample_span'], clock)
                sc = t.train.Scorer(graph, ev, weights[a], **args)
                if selected is not None:
                    if (selected['human_validated'] is not False or selected['confidence'] is not None
                            or selected['source_labels_used_for_selection'] is not False
                            or selected.get('training_reference_labels_used', False) is not False
                            or result['exact_optimum_under_declared_score'] is not True):
                        raise ValueError('frozen_dev_audit_confirmation_or_labels_changed')
                    receipt = sc.path_receipt(paths[a]); t.train.ledger.flatten(receipt, weights[a])
                    if not t.same_json(receipt, selected['context_score']) or receipt['cost'] != selected['score_cost']:
                        raise ValueError('frozen_dev_audit_winner_cost_changed')
                    costs += 1
                cross = case['same_weight_path_receipts'][a]
                if set(cross) != set(paths): raise ValueError('frozen_dev_audit_competitor_missing')
                for b, ids in paths.items():
                    receipt = sc.path_receipt(ids); t.train.ledger.flatten(receipt, weights[a])
                    projections += t.train.prior.verify_projection(sc, ids, receipt)
                    if not t.same_json(receipt, cross[b]): raise ValueError('frozen_dev_audit_competitor_receipt_changed')
                    if selected and t.s.f(selected['score_cost']) > t.s.f(receipt['cost']):
                        raise ValueError('frozen_dev_audit_winner_above_competitor')
                    cross_costs += 1
                if witness:
                    receipt = sc.path_receipt(witness, target=True); t.train.ledger.flatten(receipt, weights[a])
                    projections += t.train.prior.verify_projection(sc, witness, receipt)
                    if not t.same_json(receipt, case['reference_witness_receipts'][a]):
                        raise ValueError('frozen_dev_audit_witness_receipt_changed')
                    if selected:
                        if t.s.f(selected['score_cost']) > t.s.f(receipt['cost']):
                            raise ValueError('frozen_dev_audit_winner_above_witness')
                        if not t.same_json(t.train.ledger.compare(cross[a], receipt, weights[a]),
                                           case['winner_minus_reference_witness'][a]):
                            raise ValueError('frozen_dev_audit_witness_gap_changed')
                    witness_costs += 1
                elif case['reference_witness_receipts'] or case['winner_minus_reference_witness']:
                    raise ValueError('frozen_dev_audit_unavailable_witness_fabricated')
                t.train.prior.prior.clear(ev, clock)
            actual = t.evaluate(t.native_reference(row), t.native_prediction(selected, row['sample_span']),
                                row['sample_span'], selected=selected is not None)
            if not t.same_json(actual, value['evaluation']): raise ValueError('frozen_dev_audit_evaluation_changed')
        old_selected = previous[key]['arms'][t.previous.ARMS[2]]['selected_prediction']
        fresh = row['arms'][t.ARMS[0]]['selected_prediction']
        if fresh:
            t.previous.check_control({'selected': fresh}, old_selected, t.ARMS[0]); control += 1
        elif old_selected: control_abstain += 1
        if i % 12 == 0 or i == len(report['records']): print(f'[audit frozen 35 Dev] {i}/{len(report["records"])}', flush=True)
    if not t.same_json(t.metrics(report['records']), report['tables']): raise ValueError('frozen_dev_audit_metrics_changed')
    status = {a: dict(Counter(r['arms'][a]['status'] for r in report['records'])) for a in t.ARMS}
    if not t.same_json(status, report['status_counts']): raise ValueError('frozen_dev_audit_status_changed')
    if (control != report['old26_completed_controls_identical'] or control_abstain != report['old26_new_resource_abstentions']
            or edges != report['original_edges'] or len(cache) != report['full_dev_source_packages']
            or projections != report['scalar_detailed_transitions_replayed']):
        raise ValueError('frozen_dev_audit_counters_changed')
    families = {r['work_family_id'] for r in report['records']}; train = {r['work_family_id'] for r in ctx['rows']}
    if (report['dev_families'] != sorted(families) or report['training_families'] != sorted(train)
            or report['named_family_overlap'] != sorted(families & train) or families & train):
        raise ValueError('frozen_dev_audit_family_overlap')
    check()
    result = {'passed': True, 'report_sha256': t.io.digest(root/'report.json'), 'unique_hashes_checked': len(pins),
        'model_fit_repeated': False, 'new_decoder_search': False, 'contexts_replayed': len(report['records']),
        'original_abstentions_preserved': abstain, 'source_packages': len(cache), 'original_edges': edges,
        'winner_costs_replayed': costs, 'same_weight_competitor_costs': cross_costs,
        'evaluation_only_reference_witness_costs': witness_costs, 'scalar_detailed_transitions': projections,
        'all_attempted_cases_preserved': len(cases), 'previous_cases_preserved': len(old_cases),
        'old26_completed_controls_identical': control, 'old26_new_resource_abstentions': control_abstain,
        'metrics_replayed': True, 'independent_accuracy_claimed': False,
        'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
