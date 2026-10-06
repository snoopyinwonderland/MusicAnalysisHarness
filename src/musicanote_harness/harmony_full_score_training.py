"""Recompute the sealed 65 current-winner Train pairs into full vectors."""
from collections import defaultdict, Counter

from . import harmony_fresh_train_trial as parent
from . import harmony_full_score as s
from . import harmony_full_score_learning as learning
from .harmony_margin_learning import training_loss, path_loss
from .harmony_structured_learning import content_hash

ROOT = 'output/harmony-fresh-train-2026-10-05-r1'
PINS = {
    ROOT+'/report.json': 'b542fa2e7e82bc02b49edc70d3f71bfbbad1fb9b951a318200d8d6759381c532',
    ROOT+'/training-contrasts.json.gz': 'f6daa18bdd7296fc86090abf8c61736843a635067e0695eea1012eaef2745d6e',
    ROOT+'/post-seal-audit.json': '828d615429e733796f6e45f98fcbe00eb0bc1f6aea0d92d2defbf65347bce2bb'}


def prepare(read, save, output):
    report, pool, audit = [read(p, h) for p, h in PINS.items()]
    if report['complete'] is not True or audit['passed'] is not True or audit['report_sha256'] != PINS[ROOT+'/report.json']:
        raise ValueError('unsealed_fresh_train_pool')
    for p, h in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items(): read(p, h, raw=True)
    previous, recall, integration, use, historical, learned = [read(p, h) for p, h in parent.old_training.PINS.items()]
    manifest = recall['package_manifest']; approvals = parent.validate_use_contract(use, manifest, parent.old_training.PARENT_SHA)
    before, refs = parent.train_records(previous, learned, approvals); refs = {r['sample_id']: r for r in refs}
    fixed = parent.old_training.old_learning.model_weights(read(parent.old_training.SUPPORT_MODEL, parent.old_training.SUPPORT_MODEL_SHA),
        use, manifest, parent.old_training.PARENT_SHA)
    timing = parent.timing_learning.model_weights(read(parent.TIMING_MODEL, parent.TIMING_MODEL_SHA), use, manifest, parent.old_training.PARENT_SHA)
    extra = fixed | timing; initial = s.initial_weights(extra)
    groups = defaultdict(list)
    for r in pool['rows']: groups[r['sample_id']].append(r)
    if len({r['contrast_id'] for r in pool['rows']}) != len(pool['rows']): raise ValueError('duplicate_fresh_train_contrast')
    rows = []; counts = Counter(); source_ids = set(); scope_refs = {r['sample_id']: r for r in report['records']}
    for i, (sample, items) in enumerate(sorted(groups.items()), 1):
        ref = refs[sample]; scope_ref = scope_refs[sample]
        case = read(scope_ref['scope_artifact'], scope_ref['scope_sha256'])
        entry, graph, ev, clock, args = parent.old_training.prior.prepare_context(before[sample], ref, manifest, integration, read)
        if entry['manifest_entry_id'] not in approvals or not clock.scope(ref['sample_span'])['accepted']:
            raise ValueError('ineligible_full_score_train_scope')
        if content_hash(parent.graph_packet(graph)) != content_hash(case['problem']): raise ValueError('fresh_train_graph_changed')
        scorer = s.Scorer(graph, ev, initial, **args)
        cells = tuple(parent.old_training.prior.old.cells_from_record(ref))
        gold, ceiling = s.fresh.reachable_target(graph, cells)
        if ceiling['reachable'] is not True: raise ValueError('unreachable_full_score_train_target')
        loss = training_loss(graph, cells, s.fresh.BOUNDARY_WEIGHT)
        def loss_of(ids): return path_loss(graph, {'selected': {'segments': [{'semantic_group_ref': j} for j in ids]}}, loss)
        for r in items:
            if (entry != r['entry'] or not set(r['target_ids']) <= {e.group_id for e in gold.edges}
                    or s.f(loss_of(r['target_ids'])['total']) != 0 or loss_of(r['negative_ids']) != r['loss_details']):
                raise ValueError('fresh_train_target_or_loss_changed')
            negative, na = scorer.path_features(r['negative_ids']); target, ta = scorer.path_features(r['target_ids'])
            delta = {k: negative[k]-target[k] for k in s.FEATURES}
            gap = s.feature_cost(delta, initial)
            expected_gap = s.f(r['base_cost_gap'])+s.feature_cost({k: s.f(v) for k, v in r['feature_delta'].items()}, extra)
            if gap != expected_gap: raise ValueError('full_score_initial_cost_not_sealed_score')
            availability = {k: na[k] and ta[k] for k in s.FEATURES}
            row = {k: r[k] for k in ('sample_id', 'contrast_id', 'entry', 'negative_ids', 'target_ids', 'loss', 'loss_details')}
            row.update(feature_delta={k: s.q(v) for k, v in delta.items()}, feature_available=availability,
                negative_features={k: s.q(v) for k, v in negative.items()}, negative_availability=na,
                target_features={k: s.q(v) for k, v in target.items()}, target_availability=ta,
                initial_score_gap=s.q(gap), source_scope_artifact=scope_ref['scope_artifact'],
                source_scope_sha256=scope_ref['scope_sha256'], source_ir_content_sha256=ev.source.source_ir_content_sha256,
                source_receipts={'negative': scorer.receipt(r['negative_ids']), 'target': scorer.receipt(r['target_ids'], target=True)},
                source_labels_used_for_negative_selection=False, training_reference_labels_used_for_target=True)
            rows.append(row)
            counts['known_gradient_collision'] += not any(delta[k] for k in s.TRAINABLE if availability[k])
            for k in s.FEATURES:
                counts['available:'+k] += availability[k]
                counts['informative:'+k] += availability[k] and delta[k] != 0
        clock.check_source(); source_ids.add(ev.source.source_ir_content_sha256)
        counts['original_edges_in_training_scopes'] += len(graph.edges)
        ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        print(f'[full score Train vectors {i}/{len(groups)}] {sample}', flush=True)
    counts.update(contrasts=len(rows), scopes=len(groups), source_packages=len(source_ids))
    dataset = {'version': s.FEATURE_VERSION, 'rows': rows, 'counts': dict(counts),
        'fresh_pool_report_sha256': PINS[ROOT+'/report.json'], 'feature_count': len(s.FEATURES),
        'loaded_parent_containers_include_exposed_Dev': True, 'current_Dev_reconstructed_or_used_for_fit': False,
        'fixed_current_winner_pool_not_online_adversary': True, 'complete_negative_pool': False}
    save(output/'training-vectors.json.gz', dataset, True)
    model = learning.fit(rows, initial, use, manifest, parent.old_training.PARENT_SHA)
    model['training_dataset_content_sha256'] = content_hash(dataset)
    model.pop('model_id'); model['model_id'] = 'full_score_'+content_hash(model)[:24]
    save(output/'model.json', model)
    return model, use, manifest, dataset, initial
