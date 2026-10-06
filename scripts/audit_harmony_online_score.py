"""Recompute source-bound Train features/costs and replay every online update.

No fresh decoder search in the audit; sealed ordinary/latent-target paths are
validated against the original graphs and clocks. No current Dev evaluation.
"""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_online_score_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, model, freeze, contract = [t.load(root/n) for n in ('report.json', 'model.json.gz', 'model-freeze.json', 'run-contract.json')]
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('online_audit_guard_changed:'+p)
    check()
    if (report['complete'] is not True or report['dev_inference_or_evaluation'] is not False
            or t.io.digest(root/'model.json.gz') != freeze['model_sha256']
            or report['model_sha256'] != freeze['model_sha256'] or freeze['dev_labels_used'] is not False):
        raise ValueError('unsealed_online_score_report')
    def read(p, expected=None, compressed=False, raw=False):
        if expected is not None and t.io.digest(p) != expected: raise ValueError('online_source_pin_changed')
        return None if raw else t.load(p)
    old_report = read(t.prior.ROOT+'/report.json', t.prior.PINS[t.prior.ROOT+'/report.json'])
    previous, recall, integration, use, historical, learned = [read(p, h) for p, h in t.parent.old_training.PINS.items()]
    manifest = recall['package_manifest']; approvals = t.validate_use_contract(use, manifest, t.parent.old_training.PARENT_SHA)
    before, refs = t.parent.train_records(previous, learned, approvals); refs = {r['sample_id']: r for r in refs}
    fixed = t.parent.old_training.old_learning.model_weights(read(t.parent.old_training.SUPPORT_MODEL, t.parent.old_training.SUPPORT_MODEL_SHA),
        use, manifest, t.parent.old_training.PARENT_SHA)
    timing = t.parent.timing_learning.model_weights(read(t.parent.TIMING_MODEL, t.parent.TIMING_MODEL_SHA), use, manifest, t.parent.old_training.PARENT_SHA)
    initial = t.s.initial_weights(fixed | timing)
    weights = t.learning.model_weights(model, initial, use, manifest, t.parent.old_training.PARENT_SHA)
    old_rows = t.cohort(old_report['records']); by_sample = {r['sample_id']: r for r in old_rows}
    if (contract['cohort'] != [r['sample_id'] for r in old_rows]
            or [r['sample_id'] for r in report['records']] != contract['cohort']):
        raise ValueError('online_train_cohort_changed')
    visits = {(v['epoch'], v['sample_id']): v for v in model['visits']}
    if len(visits) != len(model['visits']) or len(visits) != len(old_rows)*t.learning.EPOCHS:
        raise ValueError('online_visit_denominator_changed')
    scopes = []; vectors = costs = edges = 0; sources = set(); evaluations = []; visit_values = {}
    for i, row in enumerate(report['records'], 1):
        sample = row['sample_id']; old = by_sample[sample]; ref = refs[sample]
        original = read(old['scope_artifact'], old['scope_sha256'])
        entry, graph, ev, clock, args = t.parent.old_training.prior.prepare_context(before[sample], ref, manifest, integration, read)
        if (entry != original['entry'] or t.content_hash(t.parent.graph_packet(graph)) != t.content_hash(original['problem'])
                or not clock.scope(ref['sample_span'])['accepted']): raise ValueError('online_audit_scope_changed')
        cells = tuple(t.parent.old_training.prior.old.cells_from_record(ref))
        gold, ceiling = t.s.fresh.reachable_target(graph, cells)
        if ceiling != old['candidate_ceiling']: raise ValueError('online_audit_ceiling_changed')
        loss = t.prior.training_loss(graph, cells, t.s.fresh.BOUNDARY_WEIGHT)
        scopes.append({k: old[k] for k in ('sample_id', 'split', 'work_family_id')} | {'entry': entry})
        edges += len(graph.edges); sources.add(ev.source.source_ir_content_sha256)
        for epoch in range(1, t.learning.EPOCHS+1):
            v = visits[epoch, sample]; obs = v['observation']; raw = read(obs['artifact_path'], obs['artifact_sha256'])
            w = {k: t.s.f(x) for k, x in v['weights_before'].items()}
            if (raw['epoch'] != epoch or raw['sample_id'] != sample or raw['weights'] != v['weights_before']
                    or raw['original_scope_artifact'] != old['scope_artifact']
                    or raw['original_scope_sha256'] != old['scope_sha256']
                    or raw['source_ir_content_sha256'] != ev.source.source_ir_content_sha256):
                raise ValueError('online_audit_visit_binding_changed')
            sc, ts = t.s.Scorer(graph, ev, w, **args), t.s.Scorer(gold, ev, w, **args)
            actual = t.comparison(sc, ts, raw['ordinary'], raw['target'], loss)
            if t.content_hash(actual) != t.content_hash(raw['comparison']): raise ValueError('online_visit_vector_changed')
            if obs != raw['comparison'] | {'artifact_path': obs['artifact_path'], 'artifact_sha256': obs['artifact_sha256']}:
                raise ValueError('online_model_observation_changed')
            for name, scorer in (('ordinary', sc), ('target', ts)):
                result = raw[name]
                if result['selected'] is not None:
                    selected = result['selected']; ids = t.s.fresh.path_ids(selected)
                    if t.s.q(scorer.score_path(ids)) != selected['score_cost']: raise ValueError('online_selected_cost_changed')
                    values, availability = scorer.path_features(ids)
                    if (selected['full_score']['observed_feature_sums'] != {k: t.s.q(v) for k, v in values.items()}
                            or selected['full_score']['availability'] != availability
                            or selected['source_labels_used_for_selection'] != (name == 'target')):
                        raise ValueError('online_selected_feature_or_blindness_changed')
                    costs += 1
            vectors += not actual['resource_abstention']; visit_values[epoch, sample] = obs
        raw = read(row['postfit_artifact'], row['postfit_sha256']); selected = raw['result']['selected']
        if raw['model_sha256'] != report['model_sha256']: raise ValueError('online_postfit_model_changed')
        if selected is not None:
            sc = t.s.Scorer(graph, ev, weights, **args)
            if t.s.q(sc.score_path(t.s.fresh.path_ids(selected))) != selected['score_cost']:
                raise ValueError('online_postfit_cost_changed')
            costs += 1
        actual = t.evaluate(t.native_reference(ref), t.native_prediction(selected, ref['sample_span']), ref['sample_span'], selected=selected is not None)
        if (raw['evaluation'] != actual or row['evaluation'] != actual
                or row['baseline_evaluation'] != old['arms']['timing_calibrated']['evaluation']):
            raise ValueError('online_train_evaluation_changed')
        evaluations.append(row | {'evaluation': actual})
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        if i % 20 == 0 or i == len(old_rows): print(f'[audit online Train] {i}/{len(old_rows)}', flush=True)
    def replay_visit(scope, w, epoch):
        v = visits[epoch, scope['sample_id']]
        if {k: t.s.q(x) for k, x in w.items()} != v['weights_before']: raise ValueError('online_update_sequence_changed')
        return visit_values[epoch, scope['sample_id']]
    replayed = t.learning.fit(scopes, initial, use, manifest, t.parent.old_training.PARENT_SHA, replay_visit)
    if t.content_hash(replayed) != t.content_hash(model): raise ValueError('online_model_fit_replay_changed')
    tables = {'initial': t.summarize([r | {'evaluation': r['baseline_evaluation']} for r in evaluations]), 'postfit': t.summarize(evaluations)}
    if tables != report['tables']: raise ValueError('online_train_metrics_changed')
    check()
    result = {'passed': True, 'unique_hashes_checked': len(pins), 'train_scopes': len(scopes),
        'train_source_packages': len(sources), 'original_train_edges_roundtripped': edges,
        'fresh_visit_comparisons_recomputed': vectors, 'independent_selected_path_costs': costs,
        'train_model_fit_replayed': True, 'metrics_replayed': list(tables),
        'new_decoder_search': False, 'dev_inference_or_evaluation': False,
        'report_sha256': t.io.digest(root/'report.json'), 'audit_code_sha256': t.io.digest(__file__)}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), ensure_ascii=False, indent=2), flush=True)
