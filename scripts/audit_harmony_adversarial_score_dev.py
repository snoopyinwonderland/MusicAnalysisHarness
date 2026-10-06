"""Replay three frozen Dev arms, exact source costs and metrics; no fit/search."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_adversarial_score_dev_trial as t
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); contract = t.load(root/'run-contract.json'); freeze = t.load(root/'prediction-freeze.json')
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('adversarial_dev_audit_guard_changed:'+p)
    check()
    flags = ('fit_performed', 'parameter_sweep', 'loss_augmented_inference', 'dev_fit_or_checkpoint_selection',
        'candidate_policy_changed', 'production_modified', 'independent_test_accuracy_measured')
    if (report['complete'] is not True or any(report.get(k) is not False for k in flags)
            or freeze['dev_labels_read'] is not False or freeze['fit_performed'] is not False
            or freeze['model_sha256_by_arm'] != t.MODEL_SHAS or report['model_sha256_by_arm'] != t.MODEL_SHAS
            or len(freeze['prediction_hashes']) != report['contexts']
            or contract['source_labels_used_at_inference'] is not False
            or contract['original_abstentions_not_retried'] is not True
            or contract['reference_reachable_filter_applied'] is not False):
        raise ValueError('unsealed_adversarial_dev_report')
    def read(p, expected=None, compressed=False, raw=False):
        if expected and t.io.digest(p) != expected: raise ValueError('adversarial_dev_audit_pin_changed:'+str(p))
        return None if raw else t.load(p)
    weights, model = t.frozen_weights(read)
    if contract['coefficients'] != {a: {k: t.s.q(v) for k, v in w.items()} for a, w in weights.items()}:
        raise ValueError('adversarial_dev_audit_coefficients_changed')
    source = read(Path(t.SOURCE_ROOT)/'report.json', t.SOURCE_PINS['report.json'])
    previous = read(Path(t.PREVIOUS_ROOT)/'report.json', t.PREVIOUS_PINS['report.json'])
    source_freeze = read(Path(t.SOURCE_ROOT)/'prediction-freeze.json', t.SOURCE_PINS['prediction-freeze.json'])
    source_raw = [read(p, h) for p, h in source_freeze['prediction_hashes'].items()]
    refs = {(r['pair_id'], r['sample_id']): r for r in source['records']}
    prev = {(r['pair_id'], r['sample_id']): r for r in previous['records']}
    originals = {(r['pair_id'], r['sample_id']): r for r in source_raw}
    keys = t.packet_keys(report['records'], source_freeze['contexts'])
    if keys != set(refs) or keys != set(prev) or keys != set(originals): raise ValueError('adversarial_dev_audit_inventory_changed')
    tables = {a: [] for a in t.ARMS}; cache, scorers_by_key = {}, {}; costs = edges = abstentions = 0
    for i, row in enumerate(report['records'], 1):
        key = row['pair_id'], row['sample_id']; raw = t.load(row['prediction_artifact']); original = originals[key]
        if not t.same_json(raw['sample_span'], row['sample_span']): raise ValueError('adversarial_dev_audit_raw_span_changed')
        if any(k in raw for k in ('reference_cells', 'candidate_ceiling')) or any('evaluation' in v for v in raw['arms'].values()):
            raise ValueError('adversarial_dev_unsealed_reference_in_prediction')
        if t.io.digest(row['prediction_artifact']) != freeze['prediction_hashes'].get(row['prediction_artifact']):
            raise ValueError('adversarial_dev_prediction_not_frozen')
        for field in ('pair_id', 'sample_id', 'sample_span', 'plan_index', 'collection_id', 'work_family_id',
                      'reference_binding_verified', 'source_clock_gate', 'attempted', 'known_prior_diagnostic'):
            if not t.same_json(row[field], original[field]) or not t.same_json(raw[field], row[field]):
                raise ValueError('adversarial_dev_audit_original_scope_changed:'+field)
        for field in ('reference_cells', 'candidate_ceiling'):
            if not t.same_json(row[field], refs[key][field]): raise ValueError('adversarial_dev_audit_reference_changed')
        if set(row['arms']) != set(t.ARMS): raise ValueError('adversarial_dev_audit_arms_changed')
        if row['attempted']:
            if (row['graph_artifact'], row['graph_sha256']) != (original['graph_artifact'], original['graph_sha256']):
                raise ValueError('adversarial_dev_audit_graph_changed')
            packet = read(row['graph_artifact'], row['graph_sha256']); t.prior.prior.check_prediction(packet)
            if not t.same_json(row['source'], packet['source']): raise ValueError('adversarial_dev_audit_source_binding_changed')
            graph = t.prior.prior.prior.graph_from_packet(packet['problem'])
            if not t.same_json(t.prior.prior.prior.graph_packet(graph), packet['problem']): raise ValueError('adversarial_dev_audit_graph_codec_changed')
            edges += len(graph.edges)
            if key[0] not in cache:
                src = row['source']; ir = read(src['canonical_ir_path'])
                if t.prior.content_hash(ir) != src['original_ir_content_sha256']: raise ValueError('adversarial_dev_audit_ir_changed')
                read(src['source_musicxml_path'], src['original_musicxml_sha256'], raw=True)
                view, grace = t.prior.prior.prior.bounded.grace_projection(ir)
                cache[key[0]] = ir, view, grace, t.prior.SourceClockGuard(ir)
            ir, view, grace, clock = cache[key[0]]
            if clock.scope(row['sample_span']) != row['source_clock_gate']: raise ValueError('adversarial_dev_audit_clock_changed')
            ev, args = t.prior.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            scorers_by_key[key] = {a: t.s.Scorer(graph, ev, w, **args) for a, w in weights.items()}
        else: abstentions += 1
        for a, value in row['arms'].items():
            if not t.same_json(raw['arms'][a], {k: v for k, v in value.items() if k != 'evaluation'}):
                raise ValueError('adversarial_dev_prediction_changed_after_seal')
            selected = value['selected_prediction']
            if a in t.control.ARMS: t.check_control({'selected': selected}, prev[key]['arms'][a]['selected_prediction'], a)
            if not row['attempted']:
                if (selected is not None or value['reused_old_abstention'] is not True
                        or value['status'] != original['arms']['timing_calibrated']['status'] or value['elapsed_seconds'] != 0):
                    raise ValueError('adversarial_dev_original_abstention_retried')
            if selected is not None:
                if (selected['human_validated'] is not False or selected['confidence'] is not None
                        or selected['source_labels_used_for_selection'] is not False
                        or selected.get('training_reference_labels_used', False) is not False
                        or selected['full_score']['model_sha256'] != t.MODEL_SHAS[a]):
                    raise ValueError('adversarial_dev_confirmation_or_inference_labels_changed')
                sc = scorers_by_key[key][a]; ids = t.s.fresh.path_ids(selected); features, available = sc.path_features(ids)
                if t.s.q(sc.score_path(ids)) != selected['score_cost']: raise ValueError('adversarial_dev_cost_changed')
                if (selected['full_score']['observed_feature_sums'] != {k: t.s.q(v) for k, v in features.items()}
                        or selected['full_score']['availability'] != available): raise ValueError('adversarial_dev_features_changed')
                costs += 1
            actual = evaluate(native_reference(row), native_prediction(selected, row['sample_span']),
                row['sample_span'], selected=selected is not None)
            if not t.same_json(actual, value['evaluation']): raise ValueError('adversarial_dev_evaluation_changed')
            tables[a].append(row | {'evaluation': actual})
        if row['attempted']: clock.check_source()
        if i % 20 == 0 or i == report['contexts']: print(f'[audit adversarial frozen Dev] {i}/{report["contexts"]}', flush=True)
    for a, rows in tables.items():
        if not t.same_json(summarize(rows), report['tables'][a]): raise ValueError('adversarial_dev_table_changed')
    if not t.same_json(t.comparisons(report['records']), report['comparisons']): raise ValueError('adversarial_dev_comparison_changed')
    if not t.same_json(report['tables'][t.ARMS[0]], source['tables']['timing_calibrated']): raise ValueError('adversarial_dev_initial_table_changed')
    for a in t.control.ARMS:
        if not t.same_json(report['tables'][a], previous['tables'][a]): raise ValueError('adversarial_dev_previous_table_changed')
    old_cases = {(r['pair_id'], r['sample_id']): r for r in previous['cases']}
    if t.packet_keys(report['cases'], report['fresh_dev_scopes']) != set(scorers_by_key) or not set(old_cases) <= set(scorers_by_key):
        raise ValueError('adversarial_dev_cases_missing')
    if report['previous_cases_preserved'] != len(old_cases): raise ValueError('adversarial_dev_previous_cases_missing')
    case_costs = cross_costs = witness_costs = 0
    for item in report['cases']:
        key = item['pair_id'], item['sample_id']; case = t.load(item['case_path']); row = next(r for r in report['records'] if (r['pair_id'], r['sample_id']) == key)
        if (not t.same_json(case['record'], row) or case['human_validated'] is not False
                or case['independent_test_case'] is not False or case['reference_witness_never_used_for_inference'] is not True
                or case['model_sha256_by_arm'] != t.MODEL_SHAS
                or case['previous_case_artifact'] != (old_cases[key]['case_path'] if key in old_cases else None)):
            raise ValueError('adversarial_dev_case_record_changed')
        for a, receipt in case['selected_path_receipts'].items():
            sc = scorers_by_key[key][a]
            if not t.same_json(sc.receipt(receipt['existing_path_ids']), receipt): raise ValueError('adversarial_dev_case_source_receipt_changed')
            if receipt['cost'] != row['arms'][a]['selected_prediction']['score_cost']: raise ValueError('adversarial_dev_case_cost_changed')
            case_costs += 1
        for a, competitors in case['same_weight_path_receipts'].items():
            sc = scorers_by_key[key][a]
            for b, receipt in competitors.items():
                if (not t.same_json(sc.receipt(receipt['existing_path_ids']), receipt)
                        or tuple(receipt['existing_path_ids']) != t.s.fresh.path_ids(row['arms'][b]['selected_prediction'])):
                    raise ValueError('adversarial_dev_same_weight_receipt_changed')
                if t.s.f(row['arms'][a]['selected_prediction']['score_cost']) > t.s.f(receipt['cost']):
                    raise ValueError('adversarial_dev_selected_cost_above_competitor')
                cross_costs += 1
        for a, receipt in case.get('reference_witness_receipts', {}).items():
            witness = row['candidate_ceiling']['oracle_reference_witness']
            if (not t.same_json(scorers_by_key[key][a].receipt(witness, target=True), receipt)
                    or t.s.f(row['arms'][a]['selected_prediction']['score_cost']) > t.s.f(receipt['cost'])):
                raise ValueError('adversarial_dev_reference_receipt_changed')
            witness_costs += 1
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'model_sha256_by_arm': t.MODEL_SHAS,
        'model_fit_repeated': False, 'dev_prediction_packets': report['contexts'], 'dev_source_packages': len(cache),
        'original_dev_edges_roundtripped': edges, 'original_abstentions_preserved': abstentions,
        'independent_dev_winner_costs': costs, 'source_case_receipt_costs': case_costs,
        'same_weight_competitor_costs': cross_costs, 'evaluation_only_reference_witness_costs': witness_costs,
        'cases_replayed': len(report['cases']), 'previous_cases_preserved': len(old_cases),
        'metrics_replayed': list(tables), 'new_decoder_search': False,
        'comparison_contract': 'canonical_json_preserve_array_order',
        'report_sha256': t.io.digest(root/'report.json'), 'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
