"""Recompute sealed Train costs, loss, features, source receipts and margins.

No fit or fresh decoder search. Exact search correctness is independently
tested by exhaustive tiny-DAG paths; this audit checks real source integrity.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from musicanote_harness import harmony_full_score_adversary_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract = [t.load(root/n) for n in ('report.json', 'run-contract.json')]
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('adversary_audit_guard_changed:'+p)
    check()
    if (report['complete'] is not True or report['fit_performed'] is not False
            or report['dev_inference_or_evaluation'] is not False
            or report['accuracy_improvement_claimed'] is not False
            or contract['frozen_model_sha256'] != t.PINS[t.ROOT+'/model.json.gz']):
        raise ValueError('unsealed_adversary_report')
    def read(p, expected=None, compressed=False, raw=False):
        if expected is not None and t.io.digest(p) != expected: raise ValueError('adversary_source_pin_changed')
        return None if raw else t.load(p)
    original = read(t.online.prior.ROOT+'/report.json', t.online.prior.PINS[t.online.prior.ROOT+'/report.json'])
    old_report, model, audit = [read(p, h) for p, h in t.PINS.items()]
    previous, recall, integration, use, historical, learned = [read(p, h) for p, h in t.parent.old_training.PINS.items()]
    manifest = recall['package_manifest']; approvals = t.online.validate_use_contract(use, manifest, t.parent.old_training.PARENT_SHA)
    before, refs = t.parent.train_records(previous, learned, approvals); refs = {r['sample_id']: r for r in refs}
    fixed = t.parent.old_training.old_learning.model_weights(read(t.parent.old_training.SUPPORT_MODEL, t.parent.old_training.SUPPORT_MODEL_SHA),
        use, manifest, t.parent.old_training.PARENT_SHA)
    timing = t.parent.timing_learning.model_weights(read(t.parent.TIMING_MODEL, t.parent.TIMING_MODEL_SHA), use, manifest, t.parent.old_training.PARENT_SHA)
    initial = t.s.initial_weights(fixed | timing)
    weights = t.online.learning.model_weights(model, initial, use, manifest, t.parent.old_training.PARENT_SHA)
    rows = t.online.cohort(original['records']); by_sample = {r['sample_id']: r for r in rows}
    old_rows = {r['sample_id']: r for r in old_report['records']}
    if (contract['cohort'] != [r['sample_id'] for r in rows]
            or [r['sample_id'] for r in report['records']] != contract['cohort']
            or contract['weights'] != {k: t.s.q(v) for k, v in weights.items()}):
        raise ValueError('adversary_frozen_cohort_or_weights_changed')
    sources = set(); edges = costs = contrasts = receipts = 0; evaluations = []
    for i, row in enumerate(report['records'], 1):
        sample = row['sample_id']; old = by_sample[sample]; ref = refs[sample]
        packet, entry, graph, gold, ev, clock, args, loss = t.prepare(sample, old, ref, before, manifest, integration, read)
        raw = read(row['scope_artifact'], row['scope_sha256'])
        if (raw['entry'] != entry or entry['manifest_entry_id'] not in approvals
                or raw['source_ir_content_sha256'] != ev.source.source_ir_content_sha256
                or raw['original_scope_artifact'] != old['scope_artifact']
                or raw['original_scope_sha256'] != old['scope_sha256']
                or raw['frozen_model_sha256'] != t.PINS[t.ROOT+'/model.json.gz']):
            raise ValueError('adversary_source_or_model_binding_changed')
        sc, ts = t.s.Scorer(graph, ev, weights, **args), t.s.Scorer(gold, ev, weights, **args)
        actual = t.contrast(sc, ts, raw['ordinary'], raw['adversary'], raw['target'], loss)
        if t.online.content_hash(actual) != t.online.content_hash(raw['contrast']) or raw['contrast'] != row['contrast']:
            raise ValueError('adversary_contrast_changed')
        for name in ('ordinary', 'adversary', 'target'):
            chosen = raw[name]['selected']
            if chosen is None: continue
            ids = t.s.fresh.path_ids(chosen); values, mask = sc.path_features(ids)
            if (chosen['score_cost'] != t.s.q(sc.score_path(ids))
                    or chosen['full_score']['observed_feature_sums'] != {k: t.s.q(v) for k, v in values.items()}
                    or chosen['full_score']['availability'] != mask
                    or chosen['source_labels_used_for_selection'] != (name != 'ordinary')):
                raise ValueError('adversary_cost_feature_or_blindness_changed')
            if name == 'target' and not set(ids) <= {e.group_id for e in gold.edges}:
                raise ValueError('adversary_target_not_compatible')
            expected = sc.receipt(ids, target=name != 'ordinary')
            if t.online.content_hash(expected) != t.online.content_hash(raw['path_receipts'][name]):
                raise ValueError('adversary_full_source_receipt_changed')
            costs += 1; receipts += 1
        old_raw = read(old_rows[sample]['postfit_artifact'], old_rows[sample]['postfit_sha256'])
        if (t.s.fresh.path_ids(raw['ordinary']['selected']) != t.s.fresh.path_ids(old_raw['result']['selected'])
                or raw['ordinary']['selected']['score_cost'] != old_raw['result']['selected']['score_cost']):
            raise ValueError('adversary_ordinary_baseline_changed')
        actual_evaluation = t.online.evaluate(t.online.native_reference(ref),
            t.online.native_prediction(raw['ordinary']['selected'], ref['sample_span']),
            ref['sample_span'], selected=raw['ordinary']['selected'] is not None)
        if actual_evaluation != row['evaluation'] or row['evaluation'] != old_rows[sample]['evaluation']:
            raise ValueError('adversary_ordinary_evaluation_changed')
        if row['search_status'] != raw['adversary']['status'] or row['adversary_transitions'] != raw['adversary']['transitions']:
            raise ValueError('adversary_search_receipt_changed')
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges); contrasts += not actual['resource_abstention']
        evaluations.append(row | {'evaluation': actual_evaluation})
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        if i % 20 == 0 or i == len(rows): print(f'[audit Train adversary] {i}/{len(rows)}', flush=True)
    ready = [r['contrast'] for r in report['records'] if not r['contrast']['resource_abstention']]
    counts = {'parent_train_scopes': len(original['records']), 'reachable_train_scopes': len(rows),
        'excluded_unreachable_or_ineligible_scopes': len(original['records'])-len(rows),
        'full_source_packages': len(sources), 'work_families': len({r['work_family_id'] for r in rows}),
        'original_edges': edges, 'ordinary_correct_scopes': sum(r['evaluation']['selected_hit'] is True for r in evaluations),
        'complete_contrasts': contrasts, 'search_statuses': dict(Counter(r['search_status'] for r in report['records'])),
        'positive_margin': sum(t.s.f(v['margin_violation']) > 0 for v in ready),
        'ordinary_correct_positive_margin': sum(v['ordinary_correct_positive_margin'] for v in ready),
        'positive_margin_known_feature_collisions': sum(v['positive_margin_known_feature_collision'] for v in ready),
        'gradient_eligible': sum(v['gradient_eligible'] for v in ready),
        'adversary_differs_from_ordinary': sum(v['adversary_differs_from_ordinary'] for v in ready),
        'positive_adversary_loss': sum(t.s.f(v['loss']) > 0 for v in ready), 'weights_changed': 0}
    if counts != report['counts'] or t.online.summarize(evaluations) != report['unchanged_ordinary_train_metrics']:
        raise ValueError('adversary_counts_or_metrics_changed')
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'train_scopes': len(rows),
        'full_source_packages': len(sources), 'original_edges_roundtripped': edges,
        'contrasts_recomputed': contrasts, 'independent_path_costs': costs, 'full_source_receipts_replayed': receipts,
        'loss_and_margins_replayed': True, 'ordinary_metrics_replayed': True,
        'fit_performed': False, 'new_decoder_search': False, 'dev_inference_or_evaluation': False,
        'report_sha256': t.io.digest(root/'report.json'), 'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
