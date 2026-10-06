"""Source-based Train fit/features, Dev costs/metrics and case receipt replay."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_member_timing_trial as t
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_progression_search import _hash
from audit_harmony_temporal_scoring import compare_packet


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); freeze = t.load(root/'prediction-freeze.json')
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.expanded.digest(p) != h: raise ValueError('guard_changed:'+p)
    check(); contract = t.load(root/'run-contract.json'); model = t.load(root/'model.json')
    if (freeze['dev_labels_read'] is not False or freeze['contexts'] != report['contexts']
            or freeze['model_sha256'] != contract['model_sha256'] or t.expanded.digest(root/'model.json') != freeze['model_sha256']):
        raise ValueError('seal_or_model_changed')
    previous, recall, integration, use, historical, learned = [t.load(p) for p in t.training.PINS]
    manifest = recall['package_manifest']
    fixed = t.training.old_learning.model_weights(t.load(t.training.SUPPORT_MODEL), use, manifest, t.training.PARENT_SHA)
    new = t.learning.model_weights(model, use, manifest, t.training.PARENT_SHA)
    values = fixed | new; control = fixed | {t.scoring.FEATURE: t.scoring.F()}
    dataset = t.load(root/'training-contrasts.json.gz')
    if _hash(dataset) != model['training_dataset_content_sha256']: raise ValueError('training_dataset_changed')
    eligible = [r for r in dataset['rows'] if r['feature_available'][t.scoring.FEATURE]]
    replay = t.learning.fit(eligible, use, manifest, t.training.PARENT_SHA)
    replay.update(training_dataset_content_sha256=_hash(dataset), frozen_support_model_sha256=t.training.SUPPORT_MODEL_SHA,
                  negative_pool=model['negative_pool'])
    if _hash(replay) != _hash(model): raise ValueError('fit_replay_changed')
    def read(p, expected=None, compressed=False, raw=False):
        if expected and t.expanded.digest(p) != expected: raise ValueError('train_input_changed')
        return None if raw else t.load(p)
    refs = {r['sample_id']: r for r in learned['records']}; prev = {r['sample_id']: r for r in previous['records']}
    grouped = {}
    for row in dataset['rows']: grouped.setdefault(row['sample_id'], []).append(row)
    count = 0
    for sample, rows in sorted(grouped.items()):
        ref = refs[sample]
        entry, graph, ev, clock, args = t.training.prior.prepare_context(prev[sample], ref, manifest, integration, read)
        if not clock.scope(ref['sample_span'])['accepted']: raise ValueError('train_clock_changed')
        cells = tuple(t.training.prior.old.cells_from_record(ref))
        for row in rows:
            item = {k: row[k] for k in ('contrast_id', 'negative_ids', 'target_ids', 'loss_details', 'historical_kind')}
            actual = t.training.contrast_row(item, entry, graph, ev, args, fixed, cells) | {'sample_id': sample}
            if _hash(actual) != _hash(row): raise ValueError('train_contrast_replay_changed')
            count += 1
        clock.check_source()
        if count % 20 < len(rows): print(f'[audit Train member timing] {count}/{len(dataset["rows"])}', flush=True)
    baseline = Path(contract['baseline_source'])
    old = {(r['pair_id'], r['sample_id']): r for r in map(t.load, t.load(baseline/'prediction-freeze.json')['prediction_hashes'])}
    sealed = {(r['pair_id'], r['sample_id']): r for r in map(t.load, freeze['prediction_hashes'])}
    tables = {a: [] for a in t.ARMS}; cache = {}; scores = edges = 0
    for row in report['records']:
        key = row['pair_id'], row['sample_id']; previous_row = old.pop(key); packet = sealed.pop(key)
        t.prior.check_prediction(packet); compare_packet(packet, row)
        for arm, result in row['arms'].items():
            e = evaluate(native_reference(row), native_prediction(result['selected_prediction'], row['sample_span']),
                         row['sample_span'], selected=result['selected_prediction'] is not None)
            if e != result['evaluation']: raise ValueError('evaluation_changed')
            tables[arm].append(row | result)
        if not row['attempted']:
            if any(r['selected_prediction'] is not None or r['status'] != previous_row['arms']['train_calibrated']['status']
                   for r in row['arms'].values()): raise ValueError('abstention_changed')
            continue
        if _hash(t.prior.prior.musical_value(row['arms']['support_calibrated']['selected_prediction'])) != _hash(
                t.prior.prior.musical_value(previous_row['arms']['train_calibrated']['selected_prediction'])):
            raise ValueError('support_winner_changed')
        gp = t.load(row['graph_artifact']); graph = t.prior.prior.graph_from_packet(gp['problem'])
        if _hash(t.prior.prior.graph_packet(graph)) != _hash(gp['problem']): raise ValueError('graph_codec_changed')
        edges += len(graph.edges); pair = row['pair_id']
        if pair not in cache:
            src = gp['source']; ir = t.load(src['canonical_ir_path'])
            if _hash(ir) != src['original_ir_content_sha256'] or t.expanded.digest(src['source_musicxml_path']) != src['original_musicxml_sha256']:
                raise ValueError('source_changed')
            view, grace = t.prior.prior.bounded.grace_projection(ir); cache[pair] = ir, view, grace, SourceClockGuard(ir)
        ir, view, grace, clock = cache[pair]
        if _hash(clock.scope(row['sample_span'])) != _hash(row['source_clock_gate']): raise ValueError('clock_changed')
        ev, args = t.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
        for arm, result in row['arms'].items():
            selected = result['selected_prediction']
            if selected is None: continue
            if selected['confidence'] is not None or selected['human_validated'] or selected['support_balance']['confirmed_nct']:
                raise ValueError('unsupported_confirmation')
            scorer = t.scoring.Scorer(graph, ev, values if arm == 'timing_calibrated' else control, **args)
            ids = t.prior.prior.path_ids(selected); features, available = scorer.path_features(ids)
            if t.scoring.support.q(scorer.score_path(ids)) != selected['score_cost']: raise ValueError('winner_cost_changed')
            if (selected['support_balance']['values'] != {k: t.scoring.support.q(v) for k, v in features.items()}
                    or selected['support_balance']['availability'] != available): raise ValueError('winner_features_changed')
            scores += 1
        clock.check_source()
    if old or sealed: raise ValueError('scope_denominator_changed')
    for arm, rows in tables.items():
        if summarize(rows) != report['tables'][arm]: raise ValueError('metric_table_changed')
    for saved in report['cases']:
        case = t.load(saved['case_path']); row = case['record']
        graph = t.prior.prior.graph_from_packet(t.load(row['graph_artifact'])['problem'])
        ir, view, grace, clock = cache[row['pair_id']]
        ev, args = t.prior.evidence_args(ir, view, grace, row['sample_span'], clock)
        scorer = t.scoring.Scorer(graph, ev, values, **args)
        if case['human_validated'] or not case['reference_witness_never_used_for_inference']: raise ValueError('case_confirmation_changed')
        for receipt in case['scored_selected_paths'].values():
            if _hash(t.path_receipt(scorer, receipt['existing_path_ids'])) != _hash(receipt): raise ValueError('case_receipt_changed')
        if 'reference_witness_scores' in case:
            witness = case['reference_witness_scores']; actual = t.path_receipt(scorer, witness['existing_path_ids'])
            actual['source_labels_used_to_create_this_path'] = True
            if _hash(actual) != _hash(witness): raise ValueError('posthoc_witness_changed')
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'train_contrasts_recomputed': count,
        'eligible_train_contrasts': len(eligible), 'model_fit_replayed': True, 'scopes': len(report['records']),
        'graph_edges_roundtripped': edges, 'independent_winner_costs_checked': scores, 'full_source_packages': len(cache),
        'cases': len(report['cases']), 'metrics_replayed': list(tables), 'report_sha256': t.expanded.digest(root/'report.json'),
        'audit_code_sha256': t.expanded.digest(__file__), 'new_inference_performed': False}
    t.expanded.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
