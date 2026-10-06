"""Fit refreshed full-score adversaries on Train; freeze; ordinary Train eval.

Same initial coefficients/cohort/order/three epochs as the ordinary learner.
No frozen contrast reuse, Dev selection, candidate injection or UI promotion.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from . import harmony_full_score_adversary_trial as prior
from . import harmony_adversarial_score_learning as learning

s, online, parent, io, load = prior.s, prior.online, prior.parent, prior.io, prior.load
VERSION = 'harmony-adversarial-full-score-trial-0.1.0'
ROOT = 'output/harmony-full-score-adversary-2026-10-05-r1'
PINS = {ROOT+'/report.json': 'c924e50e3b6c1b663766bd0412acd7ba3885f6cc374645af5975c85892d3d71d',
        ROOT+'/post-seal-audit.json': 'd9f8acb584d37092fd5e578a1a228ec563078d486a6e51972e0aa009abb5b971'}


def context(read):
    diagnostic, audit = [read(p, h) for p, h in PINS.items()]
    if not diagnostic['complete'] or not audit['passed'] or audit['report_sha256'] != PINS[ROOT+'/report.json']:
        raise ValueError('unsealed_adversarial_parent')
    for p, h in (diagnostic['input_hashes'] | diagnostic['code_hashes'] | diagnostic['artifact_hashes']).items(): read(p, h, raw=True)
    original = read(online.prior.ROOT+'/report.json', online.prior.PINS[online.prior.ROOT+'/report.json'])
    ordinary_report = read(prior.ROOT+'/report.json', prior.PINS[prior.ROOT+'/report.json'])
    previous, recall, integration, use, historical, learned = [read(p, h) for p, h in parent.old_training.PINS.items()]
    if online.content_hash(historical) != learned['model_content_sha256']: raise ValueError('historical_model_changed')
    manifest = recall['package_manifest']; approvals = online.validate_use_contract(use, manifest, parent.old_training.PARENT_SHA)
    for row in approvals.values():
        for name in ('local_license', 'readme'):
            lic = row['source_license']; read(lic[name+'_path'], lic[name+'_sha256'], raw=True)
    fixed = parent.old_training.old_learning.model_weights(read(parent.old_training.SUPPORT_MODEL, parent.old_training.SUPPORT_MODEL_SHA),
        use, manifest, parent.old_training.PARENT_SHA)
    timing = parent.timing_learning.model_weights(read(parent.TIMING_MODEL, parent.TIMING_MODEL_SHA), use, manifest, parent.old_training.PARENT_SHA)
    initial = s.initial_weights(fixed | timing)
    before, refs = parent.train_records(previous, learned, approvals)
    rows = online.cohort(original['records'])
    if ([r['sample_id'] for r in rows] != [r['sample_id'] for r in diagnostic['records']]
            or [r['sample_id'] for r in rows] != [r['sample_id'] for r in ordinary_report['records']]):
        raise ValueError('adversarial_parent_cohort_changed')
    return original, ordinary_report, integration, use, manifest, initial, before, {r['sample_id']: r for r in refs}, rows


def counts(original, rows, model, source_ids):
    return {'parent_train_scopes': len(original['records']), 'reachable_train_scopes': len(rows),
        'excluded_preserved_scopes': len(original['records'])-len(rows),
        'full_source_packages': len(source_ids), 'work_families': len(model['training_families']),
        'training_visits': len(model['visits']),
        'visit_statuses': dict(Counter(v['update']['status'] for v in model['visits'])),
        'ordinary_correct_positive_margin_visits': sum(v['observation'].get('ordinary_correct_positive_margin', False) for v in model['visits']),
        'initial_correct_lost': sum(r['baseline_evaluation']['selected_hit'] is True and r['evaluation']['selected_hit'] is not True for r in rows),
        'initial_newly_correct': sum(r['baseline_evaluation']['selected_hit'] is not True and r['evaluation']['selected_hit'] is True for r in rows),
        'previous_ordinary_correct_lost': sum(r['previous_ordinary_evaluation']['selected_hit'] is True and r['evaluation']['selected_hit'] is not True for r in rows),
        'previous_ordinary_newly_correct': sum(r['previous_ordinary_evaluation']['selected_hit'] is not True and r['evaluation']['selected_hit'] is True for r in rows),
        'previous_ordinary_path_changed': sum(r['previous_ordinary_ids'] != r['selected_ids'] for r in rows)}


def tables(rows):
    return {'initial': online.summarize([r | {'evaluation': r['baseline_evaluation']} for r in rows]),
        'previous_ordinary_learning': online.summarize([r | {'evaluation': r['previous_ordinary_evaluation']} for r in rows]),
        'postfit': online.summarize(rows)}


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected: raise ValueError('adversarial_input_sha_mismatch:'+name)
        if name in inputs and inputs[name] != h: raise ValueError('adversarial_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    original, old_model_report, integration, use, manifest, initial, before, refs, rows = context(read)
    old = {r['sample_id']: r for r in rows}; old_model_rows = {r['sample_id']: r for r in old_model_report['records']}
    scopes = [{k: r[k] for k in ('sample_id', 'split', 'work_family_id')} |
        {'entry': read(r['scope_artifact'], r['scope_sha256'])['entry']} for r in rows]
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in [*Path('tests').glob('test_harmony_adversarial_score*.py'),
              Path('scripts/validate_harmony_adversarial_score.py'), Path('scripts/audit_harmony_adversarial_score.py')]:
        code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'visits').mkdir(); (output/'postfit').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    save(output/'run-contract.json', {'version': VERSION, 'code_pins': code,
        'cohort': [r['sample_id'] for r in scopes], 'initial_weights': {k: s.q(v) for k, v in initial.items()},
        'epochs': learning.EPOCHS, 'update_cap': s.q(learning.UPDATE_CAP), 'trust_factor': s.q(learning.TRUST_FACTOR),
        'negative_search': 'fresh_exact_loss_augmented_each_visit', 'latent_target_refreshed_each_visit': True,
        'model_selection': 'average_all_visits_not_best_epoch', 'same_initial_as_ordinary_learner': True,
        'max_raw_edges': 6, 'transition_budget': s.fresh.BUDGET,
        'adversary_operation_unit': 'feasible_state_raw_edge_comparison', 'ordinary_batched_operation_unit_is_different': True,
        'boundary_loss_weight': s.q(s.fresh.BOUNDARY_WEIGHT), 'resource_abstention_policy': 'no_update_still_average_visit',
        'dev_fit_inference_or_evaluation': False, 'purpose': 'local_noncommercial_research',
        'use_contract_sha256': online.content_hash(use), 'production_modified': False})
    prepared = {}; source_ids = set()
    def prepare(sample):
        if sample not in prepared:
            prepared[sample] = prior.prepare(sample, old[sample], refs[sample], before, manifest, integration, read)
            source_ids.add(prepared[sample][4].source.source_ir_content_sha256)
        return prepared[sample]
    def clean(ev, clock):
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
    def visit(scope, weights, epoch):
        tick = perf_counter(); sample = scope['sample_id']
        packet, entry, graph, gold, ev, clock, args, loss = prepare(sample)
        sc, ts = s.Scorer(graph, ev, weights, **args), s.Scorer(gold, ev, weights, **args)
        ordinary = sc.decode(); target = ts.decode(); negative = prior.adversary.decode(sc, loss)
        if target['selected'] is not None:
            target['selected'].update(source_labels_used_for_selection=True, training_reference_labels_used=True, target_only=True)
        value = prior.contrast(sc, ts, ordinary, negative, target, loss)
        path, h = save(output/'visits'/f'{epoch}-{sample}.json.gz', {
            'sample_id': sample, 'epoch': epoch, 'weights': {k: s.q(v) for k, v in weights.items()},
            'ordinary': ordinary, 'adversary': negative, 'target': target, 'contrast': value,
            'entry': entry, 'source_ir_content_sha256': ev.source.source_ir_content_sha256,
            'original_scope_artifact': old[sample]['scope_artifact'], 'original_scope_sha256': old[sample]['scope_sha256'],
            'full_source_not_clipped': True, 'human_validated': False, 'elapsed_seconds': perf_counter()-tick}, True)
        clean(ev, clock)
        return value | {'artifact_path': path, 'artifact_sha256': h}
    def progress(epoch, sample, status, ticks):
        save(output/'progress.json', {'complete': False, 'phase': 'adversarial_train', 'epoch': epoch,
            'visits': ticks, 'total_visits': learning.EPOCHS*len(scopes), 'elapsed_seconds': perf_counter()-begun})
        print(f'[adversarial Train {ticks}/{learning.EPOCHS*len(scopes)}] epoch{epoch} {sample}: {status}', flush=True)
    model = learning.fit(scopes, initial, use, manifest, parent.old_training.PARENT_SHA, visit, progress=progress)
    _, model_sha = save(output/'model.json.gz', model, True)
    weights = learning.model_weights(model, initial, use, manifest, parent.old_training.PARENT_SHA)
    fit_seconds = perf_counter()-begun
    save(output/'model-freeze.json', {'model_sha256': model_sha, 'fit_visits': len(model['visits']),
        'all_epochs_averaged': True, 'postfit_train_selection_started': False, 'dev_labels_used': False})
    results = []
    for r in scopes:
        sample = r['sample_id']; ref = refs[sample]
        packet, entry, graph, gold, ev, clock, args, loss = prepare(sample)
        sc = s.Scorer(graph, ev, weights, **args); result = sc.decode()
        evaluation = online.evaluate(online.native_reference(ref), online.native_prediction(result['selected'], ref['sample_span']),
            ref['sample_span'], selected=result['selected'] is not None)
        old_row = old_model_rows[sample]; old_raw = read(old_row['postfit_artifact'], old_row['postfit_sha256'])
        selected_ids = s.fresh.path_ids(result['selected']) if result['selected'] is not None else []
        old_ids = s.fresh.path_ids(old_raw['result']['selected']) if old_raw['result']['selected'] is not None else []
        receipts = {name: sc.receipt(ids) for name, ids in (('new_ordinary', selected_ids), ('previous_ordinary', old_ids)) if ids}
        path, h = save(output/'postfit'/(sample+'.json.gz'), {'sample_id': sample, 'entry': entry,
            'source_ir_content_sha256': ev.source.source_ir_content_sha256, 'model_sha256': model_sha,
            'result': result, 'evaluation': evaluation, 'same_frozen_weight_path_receipts': receipts,
            'previous_ordinary_artifact': old_row['postfit_artifact'], 'previous_ordinary_sha256': old_row['postfit_sha256'],
            'original_scope_artifact': old[sample]['scope_artifact'], 'original_scope_sha256': old[sample]['scope_sha256'],
            'full_source_not_clipped': True, 'original_full_musicxml_ir_context_inherited': True,
            'human_validated': False, 'independent_test_case': False}, True)
        results.append({k: ref[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {
            'scope_artifact': old[sample]['scope_artifact'], 'scope_sha256': old[sample]['scope_sha256'],
            'baseline_evaluation': old[sample]['arms']['timing_calibrated']['evaluation'],
            'previous_ordinary_evaluation': old_row['evaluation'], 'evaluation': evaluation,
            'selected_ids': selected_ids, 'previous_ordinary_ids': old_ids,
            'postfit_artifact': path, 'postfit_sha256': h})
        clean(ev, clock)
        print(f'[postfit adversarial ordinary Train {len(results)}/{len(scopes)}] {sample}: {evaluation["selected_hit"]}', flush=True)
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('adversarial_guard_changed:'+p)
    final = {'version': VERSION, 'complete': True, 'records': results,
        'tables': tables(results), 'counts': counts(original, results, model, source_ids),
        'model_sha256': model_sha, 'fit_seconds': fit_seconds, 'elapsed_seconds': perf_counter()-begun,
        'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'postfit_ordinary_reselected': True, 'train_in_sample_diagnostic_not_independent_accuracy': True,
        'dev_inference_or_evaluation': False, 'dev_used_for_fit': False,
        'loaded_parent_containers_include_exposed_Dev': True, 'production_modified': False,
        'candidate_policy_changed': False, 'independent_test_or_full_roman_nct_accuracy_measured': False}
    io.write(output/'report.json', final)
    return {k: v for k, v in final.items() if k not in ('records', 'input_hashes', 'code_hashes', 'artifact_hashes')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); print(json.dumps(run(a.output), ensure_ascii=False, indent=2), flush=True)
