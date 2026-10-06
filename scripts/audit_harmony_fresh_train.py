"""Replay source-bound costs, targets, contrasts, ceiling and Train metrics.

No fresh decoder search in the audit. Exact search is tested exhaustively on
small graphs and each actual winner was reconstructed by the sealed decoder.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from musicanote_harness import harmony_fresh_train_trial as t
from musicanote_harness.harmony_common_benchmark import evaluate, native_reference, native_prediction, summarize


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); contract = t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('guard_changed:'+p)
    check()
    previous, recall, integration, use, historical, learned = [t.load(p) for p in t.old_training.PINS]
    approvals = t.validate_use_contract(use, recall['package_manifest'], t.old_training.PARENT_SHA)
    before, refs = t.train_records(previous, learned, approvals)
    if [r['sample_id'] for r in refs] != [r['sample_id'] for r in report['records']]: raise ValueError('train_cohort_changed')
    refs = {r['sample_id']: r for r in refs}
    fixed = t.old_training.old_learning.model_weights(t.load(t.old_training.SUPPORT_MODEL), use,
        recall['package_manifest'], t.old_training.PARENT_SHA)
    new = t.timing_learning.model_weights(t.load(t.TIMING_MODEL), use, recall['package_manifest'], t.old_training.PARENT_SHA)
    weights = {t.s.ARMS[0]: fixed | {t.s.timing.FEATURE: t.s.F()}, t.s.ARMS[1]: fixed | new}
    if contract['coefficients'] != {a: {k: t.s.q(v) for k, v in w.items()} for a, w in weights.items()}:
        raise ValueError('weights_changed')
    dataset = t.load(root/'training-contrasts.json.gz'); remaining = {r['contrast_id']: r for r in dataset['rows']}
    historical_groups, _ = t.old_training.prior.contrasts(historical)
    tables = {a: [] for a in t.s.ARMS}; categories = {a: Counter() for a in t.s.ARMS}
    sources = set(); costs = edges = comparisons = raw_predictions = 0; visited = set()
    def read(p, expected=None, compressed=False, raw=False):
        if expected and t.io.digest(p) != expected: raise ValueError('source_pin_changed')
        return None if raw else t.load(p)
    for index, row in enumerate(report['records'], 1):
        sample = row['sample_id']; ref = refs[sample]; scope = t.load(row['scope_artifact'])
        if scope['record'] != {k: v for k, v in row.items() if k not in ('scope_artifact', 'scope_sha256')}:
            raise ValueError('case_record_changed')
        raw = t.load(row['ordinary_prediction_path'])
        if raw['target_search_not_started'] is not True or raw['source_labels_used_for_selection'] is not False:
            raise ValueError('ordinary_prediction_seal_changed')
        entry, graph, ev, clock, args = t.old_training.prior.prepare_context(before[sample], ref, recall['package_manifest'], integration, read)
        if entry['manifest_entry_id'] not in approvals or row['split'] != 'train': raise ValueError('nontrain_scope')
        if t.content_hash(t.graph_packet(graph)) != t.content_hash(scope['problem']): raise ValueError('original_graph_changed')
        if clock.scope(row['sample_span']) != row['source_clock_gate']: raise ValueError('source_clock_changed')
        cells = tuple(t.old_training.prior.old.cells_from_record(ref)); gold, ceiling = t.s.reachable_target(graph, cells)
        if ceiling != row['candidate_ceiling']: raise ValueError('ceiling_changed')
        edges += len(graph.edges); sources.add(ev.source.source_ir_content_sha256)
        for arm, value in row['arms'].items():
            if raw['arms'][arm] != value['ordinary']: raise ValueError('prediction_changed_after_target_search')
            raw_predictions += 1; selected = value['ordinary']['selected']
            evaluation = evaluate(native_reference(row), native_prediction(selected, row['sample_span']),
                row['sample_span'], selected=selected is not None)
            if evaluation != value['evaluation']: raise ValueError('evaluation_changed')
            if t.classify(row['source_clock_gate'], ceiling, value['ordinary'], evaluation) != value['category']:
                raise ValueError('category_changed')
            categories[arm][value['category']] += 1; tables[arm].append(row | {'evaluation': evaluation})
            if selected is None: continue
            if selected['confidence'] is not None or selected['human_validated']: raise ValueError('confirmation_changed')
            scorer = t.s.direct_scorer(graph, ev, weights[arm], **args); ids = t.s.path_ids(selected)
            if t.s.q(scorer.score_path(ids)) != selected['score_cost']: raise ValueError('ordinary_cost_changed')
            features, available = scorer.path_features(ids)
            if (selected['support_balance']['values'] != {k: t.s.q(v) for k, v in features.items()}
                    or selected['support_balance']['availability'] != available): raise ValueError('ordinary_features_changed')
            costs += 1
            target_result = value['target']
            if target_result is None or target_result['selected'] is None: continue
            target = target_result['selected']; tids = t.s.path_ids(target)
            if target['target_only'] is not True or target['training_reference_labels_used'] is not True:
                raise ValueError('target_mislabeled_as_analysis')
            actual = t.s.contrast(sample, entry, graph, ev, cells, selected, target, weights[arm], **args)
            stored = remaining.get(actual['contrast_id'])
            if stored is None: raise ValueError('missing_fresh_contrast')
            for k, v in actual.items():
                if k == 'current_score_gap' and arm != stored['arms'][0]: continue
                if t.content_hash(v) != t.content_hash(stored[k]): raise ValueError('contrast_changed:'+k)
            historical_items = historical_groups.get(sample, {}).values()
            if stored['exact_historical_negative_path_present'] != any(tuple(x['negative_ids']) == ids for x in historical_items):
                raise ValueError('historical_negative_comparison_changed')
            if stored['exact_historical_contrast_present'] != any(tuple(x['negative_ids']) == ids and tuple(x['target_ids']) == tids for x in historical_items):
                raise ValueError('historical_contrast_comparison_changed')
            nruns = t.s.timing.support.completed_runs(graph, ids)
            truns = t.s.timing.support.completed_runs(graph, tids)
            old_runs = [(t.s.timing.support.completed_runs(graph, x['negative_ids']),
                         t.s.timing.support.completed_runs(graph, x['target_ids'])) for x in historical_items]
            if (stored['historical_semantic_negative_present'] != any(n == nruns for n, _ in old_runs)
                    or stored['historical_semantic_contrast_present'] != any(n == nruns and g == truns for n, g in old_runs)):
                raise ValueError('historical_semantic_comparison_changed')
            for name, path, is_target in [('negative_source_receipt', ids, False), ('target_source_receipt', tids, True)]:
                if t.content_hash(t.s.path_receipt(scorer, path, target=is_target)) != t.content_hash(value[name]):
                    raise ValueError('source_receipt_changed')
            visited.add(actual['contrast_id']); comparisons += 1; costs += 1
        clock.check_source()
        if index % 30 == 0 or index == len(report['records']): print(f'[audit fresh Train] {index}/{len(report["records"])}', flush=True)
    if visited != set(remaining): raise ValueError('unreplayed_contrast')
    for arm, rows in tables.items():
        if summarize(rows) != report['tables'][arm] or dict(categories[arm]) != report['categories'][arm]:
            raise ValueError('train_table_changed')
    if report['counts']['original_edges'] != edges: raise ValueError('edge_denominator_changed')
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'approved_train_scopes': len(refs),
        'source_packages': len(sources), 'original_graph_edges_roundtripped': edges,
        'ordinary_prediction_packets_checked': raw_predictions, 'independent_path_costs_checked': costs,
        'contrast_arm_comparisons': comparisons, 'unique_contrasts_recomputed': len(visited),
        'metrics_replayed': list(tables), 'new_decoder_search': False, 'new_weight_fit': False,
        'report_sha256': t.io.digest(root/'report.json'), 'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
