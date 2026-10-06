"""Replay sealed Train source features, exact update arithmetic and metrics.

No new adversary/ordinary/target search. Replaying the saved training visits
is an arithmetic integrity check, not a second fit/checkpoint choice.
"""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_adversarial_score_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract, model, freeze = [t.load(root/n) for n in ('report.json', 'run-contract.json', 'model.json.gz', 'model-freeze.json')]
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('adversarial_audit_guard_changed:'+p)
    check()
    if (report['complete'] is not True or report['dev_used_for_fit'] is not False
            or report['dev_inference_or_evaluation'] is not False
            or freeze['model_sha256'] != report['model_sha256']
            or report['model_sha256'] != t.io.digest(root/'model.json.gz')
            or freeze['postfit_train_selection_started'] is not False):
        raise ValueError('unsealed_adversarial_training')
    def read(p, expected=None, compressed=False, raw=False):
        if expected is not None and t.io.digest(p) != expected: raise ValueError('adversarial_source_sha_changed')
        return None if raw else t.load(p)
    original, old_model_report, integration, use, manifest, initial, before, refs, rows = t.context(read)
    by_sample = {r['sample_id']: r for r in rows}; old_rows = {r['sample_id']: r for r in old_model_report['records']}
    weights = t.learning.model_weights(model, initial, use, manifest, t.parent.old_training.PARENT_SHA)
    if (contract['cohort'] != [r['sample_id'] for r in rows]
            or [r['sample_id'] for r in report['records']] != contract['cohort']
            or contract['initial_weights'] != {k: t.s.q(v) for k, v in initial.items()}):
        raise ValueError('adversarial_cohort_or_initial_changed')
    visits = {(v['epoch'], v['sample_id']): v for v in model['visits']}
    if len(visits) != t.learning.EPOCHS*len(rows): raise ValueError('adversarial_visit_count_changed')
    scopes = []; sources = set(); contrasts = costs = receipts = edges = 0
    for i, row in enumerate(report['records'], 1):
        sample = row['sample_id']; ref = refs[sample]; old = by_sample[sample]
        packet, entry, graph, gold, ev, clock, args, loss = t.prior.prepare(sample, old, ref, before, manifest, integration, read)
        scopes.append({k: row[k] for k in ('sample_id', 'split', 'work_family_id')} | {'entry': entry})
        for epoch in range(1, t.learning.EPOCHS+1):
            visit = visits[epoch, sample]; value = visit['observation']
            raw = read(value['artifact_path'], value['artifact_sha256'])
            if (raw['sample_id'] != sample or raw['epoch'] != epoch or raw['weights'] != visit['weights_before']
                    or raw['entry'] != entry or raw['source_ir_content_sha256'] != ev.source.source_ir_content_sha256
                    or raw['original_scope_artifact'] != old['scope_artifact']
                    or raw['original_scope_sha256'] != old['scope_sha256']):
                raise ValueError('adversarial_visit_source_binding_changed')
            current = {k: t.s.f(v) for k, v in visit['weights_before'].items()}
            sc, ts = t.s.Scorer(graph, ev, current, **args), t.s.Scorer(gold, ev, current, **args)
            actual = t.prior.contrast(sc, ts, raw['ordinary'], raw['adversary'], raw['target'], loss)
            if (actual != raw['contrast'] or actual != {k: v for k, v in value.items() if k not in ('artifact_path', 'artifact_sha256')}):
                raise ValueError('adversarial_full_source_contrast_changed')
            t.learning.validate_observation(value, current)
            for name in ('ordinary', 'adversary', 'target'):
                chosen = raw[name]['selected']
                if chosen is None: continue
                ids = t.s.fresh.path_ids(chosen); fv, mask = sc.path_features(ids)
                if (chosen['score_cost'] != t.s.q(sc.score_path(ids))
                        or chosen['full_score']['observed_feature_sums'] != {k: t.s.q(v) for k, v in fv.items()}
                        or chosen['full_score']['availability'] != mask
                        or chosen['source_labels_used_for_selection'] != (name != 'ordinary')):
                    raise ValueError('adversarial_visit_cost_feature_or_blindness_changed')
                if name == 'target' and not set(ids) <= {e.group_id for e in gold.edges}:
                    raise ValueError('adversarial_target_outside_original_gold')
                costs += 1
            contrasts += not actual['resource_abstention']
        post = read(row['postfit_artifact'], row['postfit_sha256'])
        old_post = read(old_rows[sample]['postfit_artifact'], old_rows[sample]['postfit_sha256'])
        if (post['entry'] != entry or post['source_ir_content_sha256'] != ev.source.source_ir_content_sha256
                or post['model_sha256'] != report['model_sha256']):
            raise ValueError('adversarial_postfit_binding_changed')
        sc = t.s.Scorer(graph, ev, weights, **args); chosen = post['result']['selected']
        ids = t.s.fresh.path_ids(chosen) if chosen is not None else []
        old_ids = t.s.fresh.path_ids(old_post['result']['selected']) if old_post['result']['selected'] is not None else []
        for name, path_ids in (('new_ordinary', ids), ('previous_ordinary', old_ids)):
            if not path_ids: continue
            if t.online.content_hash(sc.receipt(path_ids)) != t.online.content_hash(post['same_frozen_weight_path_receipts'][name]):
                raise ValueError('adversarial_same_weight_source_receipt_changed')
            receipts += 1
        if chosen is not None:
            fv, mask = sc.path_features(ids)
            if (chosen['score_cost'] != t.s.q(sc.score_path(ids)) or chosen['source_labels_used_for_selection'] is not False
                    or chosen['full_score']['observed_feature_sums'] != {k: t.s.q(v) for k, v in fv.items()}
                    or chosen['full_score']['availability'] != mask):
                raise ValueError('adversarial_postfit_cost_or_blindness_changed')
            costs += 1
        evaluation = t.online.evaluate(t.online.native_reference(ref), t.online.native_prediction(chosen, ref['sample_span']),
            ref['sample_span'], selected=chosen is not None)
        if (evaluation != post['evaluation'] or evaluation != row['evaluation'] or ids != row['selected_ids']
                or old_ids != row['previous_ordinary_ids']
                or row['baseline_evaluation'] != old['arms']['timing_calibrated']['evaluation']
                or row['previous_ordinary_evaluation'] != old_rows[sample]['evaluation']):
            raise ValueError('adversarial_evaluation_or_parent_paths_changed')
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges)
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        if i % 20 == 0 or i == len(rows): print(f'[audit adversarial Train] {i}/{len(rows)}', flush=True)
    def replay(scope, current, epoch):
        saved = visits[epoch, scope['sample_id']]
        if saved['weights_before'] != {k: t.s.q(v) for k, v in current.items()}:
            raise ValueError('adversarial_online_state_changed')
        return saved['observation']
    repeated = t.learning.fit(scopes, initial, use, manifest, t.parent.old_training.PARENT_SHA, replay)
    if t.online.content_hash(repeated) != t.online.content_hash(model): raise ValueError('adversarial_update_or_averaging_changed')
    if t.tables(report['records']) != report['tables'] or t.counts(original, report['records'], model, sources) != report['counts']:
        raise ValueError('adversarial_aggregate_changed')
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'train_scopes': len(rows),
        'full_source_packages': len(sources), 'original_edges_roundtripped': edges,
        'visits_replayed': len(visits), 'complete_contrasts_recomputed': contrasts,
        'independent_path_costs': costs, 'same_weight_source_receipts': receipts,
        'update_and_all_visit_averaging_arithmetic_replayed': True, 'ordinary_metrics_replayed': True,
        'new_decoder_search': False, 'new_fit_or_checkpoint_selection': False, 'dev_inference_or_evaluation': False,
        'report_sha256': t.io.digest(root/'report.json'), 'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
