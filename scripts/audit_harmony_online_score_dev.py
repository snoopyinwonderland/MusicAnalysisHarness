"""Recompute frozen-model Dev costs/source receipts/metrics; no fit/new search."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_online_score_dev_trial as t
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); contract = t.load(root/'run-contract.json'); freeze = t.load(root/'prediction-freeze.json')
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('online_dev_audit_guard_changed:'+p)
    check()
    if (report['complete'] is not True or report['fit_performed'] is not False or report['parameter_sweep'] is not False
            or freeze['dev_labels_read'] is not False or freeze['model_sha256'] != t.MODEL_PINS['model.json.gz']
            or len(freeze['prediction_hashes']) != report['contexts']):
        raise ValueError('unsealed_online_dev_report')
    def read(p, expected=None, compressed=False, raw=False):
        if expected and t.io.digest(p) != expected: raise ValueError('online_dev_audit_pin_changed')
        return None if raw else t.load(p)
    weights, model = t.frozen_weights(read)
    if contract['coefficients'] != {a: {k: t.s.q(v) for k, v in w.items()} for a, w in weights.items()}:
        raise ValueError('online_dev_audit_coefficients_changed')
    tables = {a: [] for a in t.ARMS}; cache, scorers_by_key = {}, {}; costs = edges = 0
    for i, row in enumerate(report['records'], 1):
        key = row['pair_id'], row['sample_id']; raw = t.load(row['prediction_artifact'])
        if raw['sample_span'] != row['sample_span']: raise ValueError('online_dev_audit_raw_span_changed')
        if t.io.digest(row['prediction_artifact']) != freeze['prediction_hashes'][row['prediction_artifact']]:
            raise ValueError('online_dev_prediction_not_frozen')
        if row['attempted']:
            packet = read(row['graph_artifact'], row['graph_sha256'])
            graph = t.prior.prior.prior.graph_from_packet(packet['problem'])
            if t.prior.content_hash(t.prior.prior.prior.graph_packet(graph)) != t.prior.content_hash(packet['problem']):
                raise ValueError('online_dev_audit_graph_codec_changed')
            edges += len(graph.edges)
            if key[0] not in cache:
                src = row['source']; ir = read(src['canonical_ir_path'])
                if t.prior.content_hash(ir) != src['original_ir_content_sha256']: raise ValueError('online_dev_audit_ir_changed')
                read(src['source_musicxml_path'], src['original_musicxml_sha256'], raw=True)
                view, grace = t.prior.prior.prior.bounded.grace_projection(ir)
                cache[key[0]] = ir, view, grace, t.prior.SourceClockGuard(ir)
            ir, view, grace, clock = cache[key[0]]
            if clock.scope(row['sample_span']) != row['source_clock_gate']: raise ValueError('online_dev_audit_clock_changed')
            ev, args = t.prior.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            scorers_by_key[key] = {a: t.s.Scorer(graph, ev, w, **args) for a, w in weights.items()}
        for a, value in row['arms'].items():
            if raw['arms'][a] != {k: v for k, v in value.items() if k != 'evaluation'}:
                raise ValueError('online_dev_prediction_changed_after_seal')
            selected = value['selected_prediction']
            if selected is not None:
                if selected['human_validated'] is not False or selected['confidence'] is not None:
                    raise ValueError('online_dev_confirmation_changed')
                sc = scorers_by_key[key][a]; ids = t.s.fresh.path_ids(selected); features, available = sc.path_features(ids)
                if t.s.q(sc.score_path(ids)) != selected['score_cost']: raise ValueError('online_dev_cost_changed')
                if (selected['full_score']['observed_feature_sums'] != {k: t.s.q(v) for k, v in features.items()}
                        or selected['full_score']['availability'] != available): raise ValueError('online_dev_features_changed')
                costs += 1
            actual = evaluate(native_reference(row), native_prediction(selected, row['sample_span']),
                row['sample_span'], selected=selected is not None)
            if actual != value['evaluation']: raise ValueError('online_dev_evaluation_changed')
            tables[a].append(row | {'evaluation': actual})
        if row['attempted']: clock.check_source()
        if i % 20 == 0 or i == report['contexts']: print(f'[audit online frozen Dev] {i}/{report["contexts"]}', flush=True)
    for a, rows in tables.items():
        if summarize(rows) != report['tables'][a]: raise ValueError('online_dev_table_changed')
    if t.changed_rows(report['records']) != report['changed']: raise ValueError('online_dev_changed_inventory')
    refs = {(r['pair_id'], r['sample_id']): r for r in report['records']}; case_costs = 0
    for item in report['cases']:
        key = item['pair_id'], item['sample_id']; case = t.load(item['case_path'])
        if case['record'] != refs[key] or case['human_validated'] is not False: raise ValueError('online_dev_case_record_changed')
        for a, receipt in case['selected_path_receipts'].items():
            sc = scorers_by_key[key][a]
            if t.prior.content_hash(sc.receipt(receipt['existing_path_ids'])) != t.prior.content_hash(receipt):
                raise ValueError('online_dev_case_source_receipt_changed')
            if receipt['cost'] != refs[key]['arms'][a]['selected_prediction']['score_cost']: raise ValueError('online_dev_case_cost_changed')
            case_costs += 1
        for a, receipt in case.get('reference_witness_receipts', {}).items():
            if t.prior.content_hash(scorers_by_key[key][a].receipt(receipt['existing_path_ids'], target=True)) != t.prior.content_hash(receipt):
                raise ValueError('online_dev_reference_receipt_changed')
            case_costs += 1
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'frozen_model_sha256': t.MODEL_PINS['model.json.gz'],
        'model_fit_repeated': False, 'dev_prediction_packets': report['contexts'], 'dev_source_packages': len(cache),
        'original_dev_edges_roundtripped': edges, 'independent_dev_winner_costs': costs,
        'source_case_receipt_costs': case_costs, 'cases_replayed': len(report['cases']), 'metrics_replayed': list(tables),
        'new_decoder_search': False, 'report_sha256': t.io.digest(root/'report.json'), 'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
