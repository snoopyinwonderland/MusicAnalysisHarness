"""One prespecified Train pool refresh, not a seventh-chord hard gate.

Keep old26, source features, masks, graph and exact scalar decoder sealed.
Append ALL newly unique Stage81 blind selections (including zero-loss ones),
then reset seven context coefficients to zero and run the SAME three epochs.
Freeze before fresh inference on every original scope. No Dev or deployment.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_context_scalar_trial as parent

VERSION = 'harmony-context-refreshed-pool-trial-0.1.0'
ROOT = 'K:/Music Analysis/output/harmony-context-scalar-efficiency-2026-10-05-r1'
PINS = {
    'report.json': 'd9a27279ce46407968c354a5e9a36a18bd7e1dfe1eb314a7870f50ef66d38297',
    'run-contract.json': '16e2c2058607c81b91e40532c2b58a47096226e43371b3c0af32d24f607ae7c6',
    'post-seal-audit.json': 'a697a3294e9fc17dc46d0ff7e56d57525bf580b232c1d1459a61c4247e1a2541',
    'post-seal-metric-correction-v2.json': 'c50dc4d5781489e5c531fe349af34742d266e73aba2c4e1a687f201fd4c4e004',
}
s, io, load = parent.s, parent.io, parent.load
old, learning = parent.prior, parent.prior.learning
same_json = old.prior.prior.prior.seals.same_json
FIELDS = ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')
SOURCE_FIELDS = FIELDS + ('entry', 'full_source_paths', 'source_provenance', 'source_ir_content_sha256',
    'source_clock_gate', 'original_scope_artifact', 'original_scope_sha256', 'original_graph_sha256', 'original_edge_count')


def configuration():
    return {'learning': learning.configuration(), 'refresh_rounds': 1,
        'mining': 'all_previous_blind_complete_paths_not_in_original_sample_path_pool',
        'correctness_filter': False, 'zero_loss_paths_retained': True,
        'deduplication': 'sample_id_and_ordered_raw_path_ids',
        'initialization': 'zero_not_previous_unadopted_weights',
        'targets': 'previous_sealed_reference_compatible_train_targets',
        'new_target_or_loss_augmented_search': False, 'work_specific_rules': False,
        'new_seventh_preservation_gate': False, 'dev_checkpoint_selection': False}


def context(read):
    report, contract, audit, correction = [read(Path(ROOT)/p, h) for p, h in PINS.items()]
    if (report['complete'] is not True or audit['passed'] is not True or correction['passed'] is not True
            or audit['report_sha256'] != PINS['report.json']
            or correction['parent_report_sha256'] != PINS['report.json']
            or report['fit_performed'] is not False or contract['production_modified'] is not False):
        raise ValueError('refresh_parent_not_sealed')
    for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
        read(p, h, raw=True)
    for p, h in correction['code_pins'].items(): read(p, h, raw=True)
    ctx = parent.context(read)
    if contract['cohort'] != [r['sample_id'] for r in ctx['rows']]:
        raise ValueError('refresh_original_cohort_changed')
    ctx['refresh_report'] = report
    ctx['refresh_records'] = {r['sample_id']: r for r in report['records']}
    return ctx


def path_key(sample, path):
    if (type(sample) is not str or not sample or type(path) not in (tuple, list)
            or not path or any(type(x) is not str or not x for x in path)):
        raise ValueError('invalid_refresh_path_identity')
    return sample, tuple(path)


def contrast(entry, sample, negative, target, loss, source_sha):
    if (negative['source_labels_used'] is not False or target['source_labels_used'] is not False
            or negative['target_path_created_using_labels'] is not False
            or target['target_path_created_using_labels'] is not True):
        raise ValueError('refresh_receipt_label_provenance_changed')
    keys = old.joint.FEATURES
    available = {k: negative['context']['availability'][k] and target['context']['availability'][k] for k in keys}
    delta = {k: s.f(negative['context']['scored_available_feature_sums'][k])
        - s.f(target['context']['scored_available_feature_sums'][k]) for k in keys}
    ids, targets = negative['existing_path_ids'], target['existing_path_ids']
    path_key(sample, ids); path_key(sample, targets)
    return {'entry': deepcopy(entry), 'sample_id': sample,
        'contrast_id': 'ctx_'+old.content_hash([sample, ids, targets])[:24],
        'negative_ids': list(ids), 'target_ids': list(targets),
        'source_ir_content_sha256': source_sha, 'source_arm': 'stage81_blind_ordinary',
        'legacy_gap': s.q(s.f(negative['legacy']['cost'])-s.f(target['legacy']['cost'])),
        'score_delta': {k: s.q(v) for k, v in delta.items()},
        'gradient_delta': {k: s.q(delta[k]) if available[k] else None for k in keys},
        'available': available, 'loss': loss['total'],
        'negative_selection_used_training_labels': False,
        'target_selection_used_training_labels': True, 'features_use_source_labels': False}


def loss_object(graph, ref):
    cells = tuple(old.prior.prior.prior.parent.parent.old_training.prior.old.cells_from_record(ref))
    return old.training_loss(graph, cells, s.fresh.BOUNDARY_WEIGHT)


def loss_for_ids(graph, loss, ids):
    return old.path_loss(graph, {'selected': {'segments': [{'semantic_group_ref': x} for x in ids]}}, loss)


def clear(ev, clock):
    clock.check_source()
    ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()


def collect(ctx, read, save=None):
    rows, original_counts = old.contrasts(ctx)
    rows = deepcopy(rows)
    seen = {path_key(r['sample_id'], r['negative_ids']) for r in rows}
    if len(seen) != len(rows): raise ValueError('original_pool_duplicate_paths')
    counts = Counter(); proofs = []
    for row in ctx['rows']:
        sample = row['sample_id']; record = ctx['refresh_records'][sample]
        counts['previous_scopes'] += 1
        if record['selected_ids'] is None:
            counts['previous_abstentions_retained_not_retried_for_mining'] += 1; continue
        key = path_key(sample, record['selected_ids'])
        if key in seen:
            counts['duplicate_blind_paths_not_reweighted'] += 1; continue
        previous = read(record['artifact'], record['sha256'])
        saved, entry, graph, ev, clock, args = old.prior.prepare_sample(ctx, row, read)
        if not all(same_json(previous[k], saved[k]) for k in SOURCE_FIELDS):
            raise ValueError('refresh_mined_source_changed')
        sc = parent.scalar.Scorer(s.Scorer(graph, ev, ctx['weights'], **args), ctx['context_weights'], **args)
        ids = s.fresh.path_ids(previous['result']['selected'])
        if ids != key[1] or previous['result']['exact_optimum_under_declared_score'] is not True:
            raise ValueError('refresh_mined_path_not_exact_blind_selection')
        n = sc.path_receipt(ids)
        if not same_json(n, previous['post_search_cost_receipts']['fresh']):
            raise ValueError('refresh_mined_receipt_changed')
        target = ctx['joint_packets'][sample]['arms']['epoch3_target']['zero_receipt']
        target_ids = target['existing_path_ids']
        t = sc.path_receipt(target_ids, target=True)
        if (not same_json(t['legacy'], target['legacy'])
                or not same_json(t['context']['scored_available_feature_sums'], target['context']['scored_available_feature_sums'])
                or t['context']['availability'] != target['context']['availability']):
            raise ValueError('refresh_sealed_target_vector_changed')
        loss = loss_object(graph, ctx['refs'][sample]); nloss = loss_for_ids(graph, loss, ids)
        tloss = loss_for_ids(graph, loss, target_ids)
        if s.f(tloss['total']) != 0: raise ValueError('refresh_target_not_reference_compatible')
        new = contrast(entry, sample, n, t, nloss, saved['source_ir_content_sha256'])
        rows.append(new); seen.add(key)
        counts['new_blind_contrasts'] += 1
        counts['new_zero_loss_protection_contrasts'] += s.f(nloss['total']) == 0
        counts['new_known_gradient_collisions'] += not any(
            s.f(v) for v in new['gradient_delta'].values() if v is not None)
        proof = {k: saved[k] for k in SOURCE_FIELDS} | {
            'previous_case_ref': record['artifact'], 'previous_case_sha256': record['sha256'],
            'negative_receipt': n, 'target_receipt': t, 'negative_loss': nloss, 'target_loss': tloss,
            'contrast': new, 'mining_reads_train_labels_for_loss_only': True,
            'negative_was_blind': True, 'new_search_performed': False, 'human_validated': False}
        if save is not None:
            p, h = save(Path('mined')/(sample+'.json.gz'), proof, True)
            proofs.append({'sample_id': sample, 'artifact': p, 'sha256': h})
        else: proofs.append(proof)
        clear(ev, clock)
    learning.validate_rows(rows, ctx['use'], ctx['manifest'], ctx['parent_sha'])
    rows.sort(key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    return rows, {'original': original_counts, 'refresh': dict(counts)}, proofs


def pool_diagnostic(rows, weights):
    values = [s.f(r['loss'])-learning.gap(r, weights) for r in rows]
    return {'positive_margin_sum': s.q(sum((max(F(), v) for v in values), F())),
        'margin_violations': sum(v > 0 for v in values),
        'negative_cheaper_than_target': sum(learning.gap(r, weights) < 0 for r in rows),
        'margin_is_not_accuracy': True}


def select(sc, model, model_sha, **kwargs):
    result = parent.select(sc, model['model_id'], **kwargs)
    # The sealed guard's parent-model metadata is not valid for this new fit.
    result['frozen_model_ref'] = {'model_id': model['model_id'], 'model_sha256': model_sha,
        'fit_performed_this_selection': False, 'fit_performed_before_selection_this_trial': True,
        'model_was_fitted_on_train': True, 'existing_26_frozen': True,
        'reference_labels_used_for_selection': False, 'operational_promotion': False}
    return result


def comparisons(records):
    # Normalize BEFORE comparison; never compare a tuple winner with a list.
    rows = []
    for r in records:
        r = dict(r)
        for k in ('selected_ids', 'previous_ids', 'baseline_ids'):
            if r[k] is not None: r[k] = path_key(r['sample_id'], r[k])[1]
        rows.append(r)
    previous = [r | {'baseline_ids': r['previous_ids'], 'baseline_evaluation': r['previous_evaluation']} for r in rows]
    common = [r for r in previous if r['selected_ids'] is not None and r['baseline_ids'] is not None]
    return {'against_frozen_old26': old.compare(rows), 'against_previous_context': old.compare(previous),
        'common_completed_previous_context': old.compare(common),
        'common_completed_scopes': len(common),
        'resource_changes': {
            'recovered_previous_abstentions': sum(r['previous_ids'] is None and r['selected_ids'] is not None for r in rows),
            'previous_completion_now_abstention': sum(r['previous_ids'] is not None and r['selected_ids'] is None for r in rows)},
        'subset_resource_bias_and_overlapping_scopes_retained': True}


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); name = str(p.resolve()); h = io.digest(p)
        if (expected is not None and h != expected) or (name in inputs and inputs[name] != h):
            raise ValueError('refresh_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for name in ('tests/test_harmony_context_refresh_trial.py', 'scripts/validate_harmony_context_refresh.py',
                 'scripts/audit_harmony_context_refresh.py'):
        p = Path(name); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir(); (output/'mined').mkdir()
    def save(p, value, compressed=False):
        p = output/p
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = {'version': VERSION, 'configuration': configuration(),
        'cohort': [r['sample_id'] for r in ctx['rows']], 'parent_report_sha256': PINS['report.json'],
        'parent_counter_correction_sha256': PINS['post-seal-metric-correction-v2.json'],
        'wall_seconds_per_fresh_scope': old.WALL_SECONDS, 'transition_budget': s.fresh.BUDGET,
        'original_graph_features_old26_and_cap_preserved': True, 'source_labels_used_for_prediction': False,
        'dev_fit_inference_or_evaluation': False, 'production_modified': False,
        'purpose': 'local_noncommercial_research', 'code_pins': code,
        'use_contract_sha256': old.content_hash(ctx['use'])}
    save(Path('run-contract.json'), contract)
    vectors, counts, proofs = collect(ctx, read, save)
    save(Path('training-vectors.json.gz'), {'rows': vectors, 'counts': counts, 'proofs': proofs}, True)
    model = learning.fit(vectors, ctx['weights'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['report.json'])
    save(Path('model.json.gz'), model, True); model_sha = io.digest(output/'model.json.gz')
    weights = learning.model_weights(model, ctx['weights'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['report.json'])
    save(Path('model-freeze.json'), {'model_sha256': model_sha, 'postfit_selection_started': False,
        'existing_26_weights': {k: s.q(v) for k, v in ctx['weights'].items()}, 'dev_used': False})
    diagnostics = {'zero': pool_diagnostic(vectors, old.joint.ZERO),
        'stage80': pool_diagnostic(vectors, ctx['context_weights']), 'refreshed': pool_diagnostic(vectors, weights)}
    print(f'[refresh frozen] contrasts={len(vectors)}, new={counts["refresh"].get("new_blind_contrasts", 0)}', flush=True)
    records = []; sources = set(); edges = projections = 0
    for i, row in enumerate(ctx['rows'], 1):
        sample = row['sample_id']; saved, entry, graph, ev, clock, args = old.prior.prepare_sample(ctx, row, read)
        sc = parent.scalar.Scorer(s.Scorer(graph, ev, ctx['weights'], **args), weights, **args)
        result = select(sc, model, model_sha)
        selected = result['selected']; ids = s.fresh.path_ids(selected) if selected else None
        previous = ctx['refresh_records'][sample]; baseline = ctx['stage80_records'][sample]
        chains = {'fresh': ids, 'previous_context': previous['selected_ids'],
            'frozen_old26': baseline['baseline_ids'],
            'stored_target': ctx['joint_packets'][sample]['arms']['epoch3_target']['path_ids']}
        receipts = {}
        for name, path in chains.items():
            if path is None: continue
            receipt = sc.path_receipt(path, target=name == 'stored_target')
            projections += parent.verify_projection(sc, path, receipt)
            if name == 'fresh' and not same_json(receipt, selected['context_score']):
                raise ValueError('refresh_fresh_independent_cost_changed')
            receipts[name] = receipt
        ref = ctx['refs'][sample]
        evaluation = old.evaluate(old.native_reference(ref), old.native_prediction(selected, ref['sample_span']),
            ref['sample_span'], selected=selected is not None)
        packet = {k: saved[k] for k in SOURCE_FIELDS} | {
            'result': result, 'evaluation': evaluation, 'model_sha256': model_sha,
            'previous_case_ref': previous['artifact'], 'previous_case_sha256': previous['sha256'],
            'post_search_cost_receipts': receipts, 'full_source_not_clipped': True,
            'source_labels_used_for_inference': False, 'human_validated': False}
        p, h = save(Path('cases')/(sample+'.json.gz'), packet, True)
        records.append({k: row[k] for k in FIELDS} | {'artifact': p, 'sha256': h,
            'status': result['status'], 'selected_ids': ids, 'previous_ids': previous['selected_ids'],
            'baseline_ids': baseline['baseline_ids'], 'evaluation': evaluation,
            'previous_evaluation': previous['evaluation'], 'baseline_evaluation': baseline['baseline_evaluation'],
            'elapsed_seconds': result['resource_guard']['elapsed_seconds']})
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges); clear(ev, clock)
        print(f'[refresh Train {i}/{len(ctx["rows"])}] {sample}: {result["status"]}, hit={evaluation["selected_hit"]}', flush=True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h: raise ValueError('refresh_final_seal_changed:'+p)
    report = contract | {'complete': True, 'fit_performed': True, 'model_sha256': model_sha,
        'training_contrasts': len(vectors), 'calibration_counts': counts, 'pool_diagnostics': diagnostics,
        'fresh_ordinary_attempts': len(records), 'full_source_packages': len(sources), 'original_edges': edges,
        'scalar_detailed_transitions_compared': projections, 'tables': comparisons(records),
        'excluded_parent_scopes_preserved': ctx['refresh_report']['excluded_parent_scopes_preserved'],
        'records': records, 'input_hashes': inputs, 'artifact_hashes': artifacts, 'code_hashes': code,
        'elapsed_seconds': perf_counter()-begun, 'operational_weights_changed': False,
        'independent_accuracy_claimed': False, 'current_dev_reconstructed_or_used': False,
        'historical_parent_containers_include_exposed_dev': True}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'training_contrasts', 'calibration_counts',
        'fresh_ordinary_attempts', 'full_source_packages', 'tables', 'elapsed_seconds')}, indent=2), flush=True)
