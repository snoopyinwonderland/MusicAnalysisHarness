"""Replay full Train vectors/fit and sealed Dev costs/metrics, no new search."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_full_score_trial as t
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); contract = t.load(root/'run-contract.json'); freeze = t.load(root/'prediction-freeze.json')
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('guard_changed:'+p)
    check()
    if report['complete'] is not True or t.io.digest(root/'model.json') != freeze['model_sha256']:
        raise ValueError('unsealed_full_score_report')
    if freeze['dev_labels_read'] is not False or len(freeze['prediction_hashes']) != report['contexts']:
        raise ValueError('dev_freeze_changed')
    generated = {}
    def read(p, expected=None, compressed=False, raw=False):
        if expected and t.io.digest(p) != expected: raise ValueError('training_pin_changed')
        return None if raw else t.load(p)
    def capture(p, value, compressed=False): generated[Path(p).name] = value
    model, use, manifest, dataset, initial = t.training.prepare(read, capture, root)
    for name, value in generated.items():
        if t.content_hash(value) != t.content_hash(t.load(root/name)): raise ValueError('train_vectors_or_model_replay_changed:'+name)
    learned = t.learning.model_weights(model, initial, use, manifest, t.training.parent.old_training.PARENT_SHA)
    weights = dict(zip(t.ARMS, (initial, learned)))
    if contract['coefficients'] != {a: {k: t.s.q(v) for k, v in w.items()} for a, w in weights.items()}:
        raise ValueError('inference_coefficients_changed')
    tables = {a: [] for a in t.ARMS}; cache = {}; scorers_by_key = {}; costs = edges = 0
    changed = []
    for i, row in enumerate(report['records'], 1):
        key = row['pair_id'], row['sample_id']; raw = t.load(row['prediction_artifact'])
        if raw['sample_span'] != row['sample_span']: raise ValueError('raw_prediction_span_changed')
        if row['attempted']:
            packet = read(row['graph_artifact'], row['graph_sha256']); graph = t.prior.prior.graph_from_packet(packet['problem'])
            if t.content_hash(t.prior.prior.graph_packet(graph)) != t.content_hash(packet['problem']): raise ValueError('graph_codec_changed')
            edges += len(graph.edges)
            if key[0] not in cache:
                source = row['source']; ir = read(source['canonical_ir_path'])
                if t.content_hash(ir) != source['original_ir_content_sha256']: raise ValueError('source_ir_changed')
                read(source['source_musicxml_path'], source['original_musicxml_sha256'], raw=True)
                view, grace = t.prior.prior.bounded.grace_projection(ir)
                cache[key[0]] = ir, view, grace, t.SourceClockGuard(ir)
            ir, view, grace, clock = cache[key[0]]
            if clock.scope(row['sample_span']) != row['source_clock_gate']: raise ValueError('source_clock_changed')
            ev, args = t.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
            scorers_by_key[key] = {a: t.s.Scorer(graph, ev, w, **args) for a, w in weights.items()}
        for a, value in row['arms'].items():
            if raw['arms'][a] != {k: v for k, v in value.items() if k != 'evaluation'}: raise ValueError('ordinary_prediction_changed_after_seal')
            selected = value['selected_prediction']
            if selected is not None:
                if selected['human_validated'] is not False or selected['confidence'] is not None: raise ValueError('confirmation_changed')
                sc = scorers_by_key[key][a]; ids = t.s.fresh.path_ids(selected); features, available = sc.path_features(ids)
                if t.s.q(sc.score_path(ids)) != selected['score_cost']: raise ValueError('dev_cost_changed')
                if (selected['full_score']['observed_feature_sums'] != {k: t.s.q(v) for k, v in features.items()}
                        or selected['full_score']['availability'] != available): raise ValueError('dev_features_changed')
                costs += 1
            actual = evaluate(native_reference(row), native_prediction(selected, row['sample_span']), row['sample_span'], selected=selected is not None)
            if actual != value['evaluation']: raise ValueError('dev_evaluation_changed')
            tables[a].append(row | {'evaluation': actual})
        a, b = (row['arms'][a] for a in t.ARMS)
        if native_prediction(a['selected_prediction'], row['sample_span']) != native_prediction(b['selected_prediction'], row['sample_span']):
            changed.append({'pair_id': key[0], 'sample_id': key[1], 'matched_time_delta': t.s.q(
                t.s.f(b['evaluation']['components']['root_members']['matched'])-t.s.f(a['evaluation']['components']['root_members']['matched']))})
        if row['attempted']: clock.check_source()
        if i % 20 == 0 or i == report['contexts']: print(f'[audit full score Dev] {i}/{report["contexts"]}', flush=True)
    for a, rows in tables.items():
        if summarize(rows) != report['tables'][a]: raise ValueError('full_score_table_changed')
    if changed != report['changed']: raise ValueError('changed_case_inventory_changed')
    refs = {(r['pair_id'], r['sample_id']): r for r in report['records']}; case_costs = 0
    for item in report['cases']:
        key = item['pair_id'], item['sample_id']; case = t.load(item['case_path'])
        if case['record'] != refs[key] or case['human_validated'] is not False: raise ValueError('case_record_changed')
        for a, receipt in case['selected_path_receipts'].items():
            sc = scorers_by_key[key][a]
            if t.content_hash(sc.receipt(receipt['existing_path_ids'])) != t.content_hash(receipt): raise ValueError('case_source_receipt_changed')
            if receipt['cost'] != refs[key]['arms'][a]['selected_prediction']['score_cost']: raise ValueError('case_cost_changed')
            case_costs += 1
        for a, receipt in case.get('reference_witness_receipts', {}).items():
            if t.content_hash(scorers_by_key[key][a].receipt(receipt['existing_path_ids'], target=True)) != t.content_hash(receipt):
                raise ValueError('witness_receipt_changed')
            case_costs += 1
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'train_vectors_recomputed': len(dataset['rows']),
        'train_scopes': dataset['counts']['scopes'], 'train_source_packages': dataset['counts']['source_packages'],
        'train_model_fit_replayed': True, 'dev_prediction_packets': report['contexts'], 'dev_source_packages': len(cache),
        'original_dev_edges_roundtripped': edges, 'independent_dev_winner_costs': costs,
        'source_case_receipt_costs': case_costs, 'cases_replayed': len(report['cases']), 'metrics_replayed': list(tables),
        'new_decoder_search': False, 'report_sha256': t.io.digest(root/'report.json'), 'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
