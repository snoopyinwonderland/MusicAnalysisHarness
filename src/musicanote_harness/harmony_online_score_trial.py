"""Refresh current Train competitors; evaluate frozen model on Train ONLY.

All 118 previously reference-reachable scopes, including 54 correct winners.
No current Dev inference, no production or candidate changes. Preserve full
source contracts and each epoch's original graph/path/cost/nullable features.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from . import harmony_full_score_training as prior
from . import harmony_online_score_learning as learning
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_structured_learning import content_hash, validate_use_contract

s, parent = learning.s, prior.parent
io, load = parent.io, parent.load
VERSION = 'harmony-online-full-score-trial-0.1.0'


def cohort(records):
    if len({r['sample_id'] for r in records}) != len(records):
        raise ValueError('duplicate_online_parent_sample')
    if any(r.get('split') != 'train' for r in records):
        raise ValueError('online_parent_contains_nontrain_scope')
    return sorted([r for r in records if r['source_clock_gate']['accepted']
        and r['candidate_ceiling']['reachable'] is True], key=lambda r: (r['work_family_id'], r['sample_id']))


def comparison(sc, target_sc, ordinary, target, loss):
    if ordinary['selected'] is None or target['selected'] is None:
        return {'resource_abstention': True, 'ordinary_status': ordinary['status'], 'target_status': target['status']}
    nids, tids = s.fresh.path_ids(ordinary['selected']), s.fresh.path_ids(target['selected'])
    details = prior.path_loss(sc.problem, ordinary, loss)
    if s.f(prior.path_loss(sc.problem, target, loss)['total']) != 0:
        raise ValueError('online_target_not_reference_compatible')
    nf, na = sc.path_features(nids); tf, ta = sc.path_features(tids)
    if sc.score_path(tids) != target_sc.score_path(tids):
        raise ValueError('online_target_filtered_graph_changed_cost')
    return {'resource_abstention': False, 'negative_ids': nids, 'target_ids': tids,
        'feature_delta': {k: s.q(nf[k]-tf[k]) for k in s.FEATURES},
        'feature_available': {k: na[k] and ta[k] for k in s.FEATURES},
        'negative_features': {k: s.q(v) for k, v in nf.items()}, 'negative_availability': na,
        'target_features': {k: s.q(v) for k, v in tf.items()}, 'target_availability': ta,
        'loss': details['total'], 'loss_details': details,
        'negative_cost': s.q(sc.score_path(nids)), 'target_cost': s.q(sc.score_path(tids)),
        'ordinary_source_labels_used': False, 'target_training_reference_labels_used': True}


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected: raise ValueError('online_input_sha_mismatch:'+name)
        if name in inputs and inputs[name] != h: raise ValueError('online_input_changed:'+name)
        inputs[name] = h
        return None if raw else load(p)
    report = read(prior.ROOT+'/report.json', prior.PINS[prior.ROOT+'/report.json'])
    audit = read(prior.ROOT+'/post-seal-audit.json', prior.PINS[prior.ROOT+'/post-seal-audit.json'])
    if not report['complete'] or not audit['passed'] or audit['report_sha256'] != prior.PINS[prior.ROOT+'/report.json']:
        raise ValueError('unsealed_online_parent')
    for p, h in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items(): read(p, h, raw=True)
    previous, recall, integration, use, historical, learned = [read(p, h) for p, h in parent.old_training.PINS.items()]
    if content_hash(historical) != learned['model_content_sha256']: raise ValueError('online_historical_model_binding')
    manifest = recall['package_manifest']; approvals = validate_use_contract(use, manifest, parent.old_training.PARENT_SHA)
    for a in approvals.values():
        lic = a['source_license']
        for name in ('local_license', 'readme'): read(lic[name+'_path'], lic[name+'_sha256'], raw=True)
    fixed = parent.old_training.old_learning.model_weights(read(parent.old_training.SUPPORT_MODEL, parent.old_training.SUPPORT_MODEL_SHA),
        use, manifest, parent.old_training.PARENT_SHA)
    timing = parent.timing_learning.model_weights(read(parent.TIMING_MODEL, parent.TIMING_MODEL_SHA), use, manifest, parent.old_training.PARENT_SHA)
    initial = s.initial_weights(fixed | timing)
    before, refs = parent.train_records(previous, learned, approvals); refs = {r['sample_id']: r for r in refs}
    selected = cohort(report['records']); scopes = []
    for r in selected:
        packet = read(r['scope_artifact'], r['scope_sha256'])
        scopes.append({k: r[k] for k in ('sample_id', 'split', 'work_family_id')} | {'entry': packet['entry']})
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in [*Path('tests').glob('test_harmony_online_score*.py'), Path('scripts/audit_harmony_online_score.py'),
              Path('scripts/validate_harmony_online_score.py')]:
        if p.exists(): code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'visits').mkdir(); (output/'postfit').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    save(output/'run-contract.json', {'version': VERSION, 'code_pins': code,
        'configuration': {'epochs': learning.EPOCHS, 'update_cap': s.q(learning.UPDATE_CAP),
            'trust_factor': s.q(learning.TRUST_FACTOR), 'negative_search': 'ordinary_current_winner_each_visit'},
        'cohort': [r['sample_id'] for r in scopes], 'parent_scopes': len(report['records']),
        'included_previously_correct': sum(r['arms']['timing_calibrated']['evaluation']['selected_hit'] is True for r in selected),
        'original_candidates_and_limits': True, 'dev_fit_inference_or_evaluation': False,
        'loss_augmented_search': False, 'purpose': 'local_noncommercial_research',
        'use_contract_sha256': content_hash(use), 'production_modified': False})
    by_sample = {r['sample_id']: r for r in selected}; source_ids = set(); prepared = {}
    def prepare(sample):
        if sample in prepared: return prepared[sample]
        ref = refs[sample]; old = by_sample[sample]
        packet = read(old['scope_artifact'], old['scope_sha256'])
        entry, graph, ev, clock, args = parent.old_training.prior.prepare_context(before[sample], ref, manifest, integration, read)
        if (entry != packet['entry'] or entry['manifest_entry_id'] not in approvals
                or not clock.scope(ref['sample_span'])['accepted']
                or content_hash(parent.graph_packet(graph)) != content_hash(packet['problem'])):
            raise ValueError('online_original_train_scope_changed')
        cells = tuple(parent.old_training.prior.old.cells_from_record(ref))
        gold, ceiling = s.fresh.reachable_target(graph, cells)
        if ceiling != old['candidate_ceiling'] or not ceiling['reachable']:
            raise ValueError('online_train_ceiling_changed')
        source_ids.add(ev.source.source_ir_content_sha256)
        prepared[sample] = ref, packet, graph, gold, ev, clock, args, prior.training_loss(graph, cells, s.fresh.BOUNDARY_WEIGHT)
        return prepared[sample]
    def visit(scope, weights, epoch):
        tick = perf_counter(); sample = scope['sample_id']
        ref, packet, graph, gold, ev, clock, args, loss = prepare(sample)
        sc, ts = s.Scorer(graph, ev, weights, **args), s.Scorer(gold, ev, weights, **args)
        ordinary = sc.decode(); target = ts.decode()
        if target['selected'] is not None:
            target['selected'].update(source_labels_used_for_selection=True, training_reference_labels_used=True, target_only=True)
        value = comparison(sc, ts, ordinary, target, loss)
        artifact, h = save(output/'visits'/f'{epoch}-{sample}.json.gz', {
            'sample_id': sample, 'epoch': epoch, 'weights': {k: s.q(v) for k, v in weights.items()},
            'ordinary': ordinary, 'target': target, 'comparison': value, 'elapsed_seconds': perf_counter()-tick,
            'original_scope_artifact': by_sample[sample]['scope_artifact'],
            'original_scope_sha256': by_sample[sample]['scope_sha256'],
            'source_ir_content_sha256': ev.source.source_ir_content_sha256}, True)
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        return value | {'artifact_path': artifact, 'artifact_sha256': h}
    def progress(epoch, sample, status, ticks):
        save(output/'progress.json', {'complete': False, 'phase': 'online_Train', 'epoch': epoch,
            'visits': ticks, 'total_visits': learning.EPOCHS*len(scopes), 'elapsed_seconds': perf_counter()-begun})
        print(f'[online Train {ticks}/{learning.EPOCHS*len(scopes)}] epoch{epoch} {sample}: {status}', flush=True)
    model = learning.fit(scopes, initial, use, manifest, parent.old_training.PARENT_SHA, visit, progress=progress)
    save(output/'model.json.gz', model, True); model_sha = io.digest(output/'model.json.gz')
    weights = learning.model_weights(model, initial, use, manifest, parent.old_training.PARENT_SHA)
    frozen_fit_seconds = perf_counter()-begun
    save(output/'model-freeze.json', {'model_sha256': model_sha, 'fit_visits': len(model['visits']),
        'all_epochs_averaged': True, 'postfit_train_selection_started': False, 'dev_labels_used': False})
    rows = []
    for r in scopes:
        ref, packet, graph, gold, ev, clock, args, loss = prepare(r['sample_id'])
        result = s.Scorer(graph, ev, weights, **args).decode()
        base = by_sample[r['sample_id']]['arms']['timing_calibrated']
        evaluation = evaluate(native_reference(ref), native_prediction(result['selected'], ref['sample_span']),
            ref['sample_span'], selected=result['selected'] is not None)
        path, h = save(output/'postfit'/(r['sample_id']+'.json.gz'), {'sample_id': r['sample_id'],
            'model_sha256': model_sha, 'result': result, 'evaluation': evaluation}, True)
        rows.append({k: ref[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {
            'baseline_evaluation': base['evaluation'], 'evaluation': evaluation,
            'postfit_artifact': path, 'postfit_sha256': h, 'scope_artifact': by_sample[r['sample_id']]['scope_artifact'],
            'scope_sha256': by_sample[r['sample_id']]['scope_sha256']})
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        print(f'[postfit ordinary Train {len(rows)}/{len(scopes)}] {r["sample_id"]}: {evaluation["selected_hit"]}', flush=True)
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('online_guard_changed:'+p)
    tables = {'initial': summarize([r | {'evaluation': r['baseline_evaluation']} for r in rows]), 'postfit': summarize(rows)}
    counts = {'parent_Train_scopes': len(report['records']), 'reachable_Train_scopes': len(scopes),
        'excluded_scopes_preserved_not_evaluated_with_new_weights': len(report['records'])-len(scopes),
        'full_source_packages': len(source_ids), 'model_families': len(model['training_families']),
        'previously_correct_lost': sum(r['baseline_evaluation']['selected_hit'] is True and r['evaluation']['selected_hit'] is not True for r in rows),
        'newly_correct': sum(r['baseline_evaluation']['selected_hit'] is not True and r['evaluation']['selected_hit'] is True for r in rows),
        'current_winner_visits': len(model['visits']),
        'visit_statuses': dict(Counter(r['update']['status'] for r in model['visits']))}
    final = {'version': VERSION, 'complete': True, 'records': rows, 'tables': tables, 'counts': counts,
        'model_sha256': model_sha, 'fit_seconds': frozen_fit_seconds, 'elapsed_seconds': perf_counter()-begun,
        'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'train_in_sample_diagnostic_not_independent_accuracy': True,
        'postfit_ordinary_reselected': True, 'dev_inference_or_evaluation': False,
        'loaded_parent_containers_include_exposed_Dev': True, 'dev_used_for_fit': False,
        'production_modified': False, 'candidate_policy_changed': False,
        'independent_test_or_full_roman_nct_accuracy_measured': False}
    io.write(output/'report.json', final)
    return {k: v for k, v in final.items() if k not in ('records', 'input_hashes', 'code_hashes', 'artifact_hashes')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); print(json.dumps(run(a.output), ensure_ascii=False, indent=2), flush=True)
