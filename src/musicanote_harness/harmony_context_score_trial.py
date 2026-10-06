"""Freeze a Train-only context calibration, then attempt every original scope.

No candidates/reference targets enter inference. Full-source evidence and old
26 weights are preserved. Exact results OR explicit no-winner abstentions;
an added cooperative wall guard is separate from the original 2M arc budget.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_context_joint_trial as prior
from . import harmony_context_score_learning as learning
from .harmony_common_benchmark import evaluate, native_reference, native_prediction, summarize
from .harmony_margin_learning import training_loss, path_loss
from .harmony_structured_learning import content_hash

s, io, load, joint = prior.s, prior.io, prior.load, prior.joint
VERSION = 'harmony-context-score-train-trial-0.1.0'
ROOT = 'K:/Music Analysis/output/harmony-context-joint-search-2026-10-05-r1'
PINS = {'report.json': '231e3743ef04ec9edb44f903abf6956d74889d03a831384fb186527c5c5718d8',
    'run-contract.json': '8fd557e0451825abfc4bc726bef5fa387002717bf023b805ce0ec144242d6105',
    'post-seal-audit.json': '48f55f344ce5dc37ba009bc2db7ddb7e318f66a98476c34dea4c9d426ece906e'}
WALL_SECONDS = 20


def context(read):
    report, contract, audit = [read(Path(ROOT)/p, h) for p, h in PINS.items()]
    if (report['complete'] is not True or audit['passed'] is not True
            or audit['report_sha256'] != PINS['report.json'] or report['fit_performed'] is not False):
        raise ValueError('context_learning_parent_not_sealed')
    for p, h in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items(): read(p, h, raw=True)
    ctx = prior.context(read)
    if contract['cohort'] != [r['sample_id'] for r in ctx['rows']]: raise ValueError('context_fit_cohort_changed')
    ctx['joint_packets'] = {r['sample_id']: read(r['artifact'], r['sha256']) for r in report['records']}
    parent = prior.prior.prior.parent
    original, ordinary, integration, use, manifest, initial, before, refs, rows = parent.context(read)
    if manifest != ctx['manifest'] or rows != ctx['rows']: raise ValueError('context_fit_rights_cohort_changed')
    ctx['use'] = use; ctx['parent_sha'] = parent.parent.old_training.PARENT_SHA
    return ctx


def contrasts(ctx):
    result, counts = [], Counter()
    for r in ctx['rows']:
        sample = r['sample_id']; packet = ctx['joint_packets'][sample]
        competition = ctx['competition_packets'][sample]
        target = packet['arms']['epoch3_target']
        if not target['selected']: raise ValueError('context_fit_stored_target_absent')
        t = target['zero_receipt']; seen = set()
        for name, arm in packet['arms'].items():
            if name == 'epoch3_target': continue
            counts['pool_conditions'] += 1
            if not arm['selected']: counts['preserved_resource_abstentions'] += 1; continue
            ids = tuple(arm['path_ids'])
            if ids in seen: counts['duplicate_negative_paths'] += 1; continue
            seen.add(ids); n = arm['zero_receipt']
            if (n['source_labels_used'] is not False or t['source_labels_used'] is not False
                    or t['target_path_created_using_labels'] is not True
                    or n['legacy']['cost'] != competition['arms'][name]['unchanged_original_cost_receipt']['cost']):
                raise ValueError('context_fit_path_provenance_changed')
            available = {k: n['context']['availability'][k] and t['context']['availability'][k] for k in joint.FEATURES}
            delta = {k: s.f(n['context']['scored_available_feature_sums'][k])-s.f(t['context']['scored_available_feature_sums'][k]) for k in joint.FEATURES}
            loss = competition['arms'][name]['unchanged_original_training_loss']['total']
            result.append({'entry': packet['entry'], 'sample_id': sample,
                'contrast_id': 'ctx_'+content_hash([sample, ids, target['path_ids']])[:24],
                'negative_ids': arm['path_ids'], 'target_ids': target['path_ids'],
                'source_ir_content_sha256': packet['source_ir_content_sha256'], 'source_arm': name,
                'legacy_gap': s.q(s.f(n['legacy']['cost'])-s.f(t['legacy']['cost'])),
                'score_delta': {k: s.q(v) for k, v in delta.items()},
                'gradient_delta': {k: s.q(delta[k]) if available[k] else None for k in joint.FEATURES},
                'available': available, 'loss': loss,
                'negative_selection_used_training_labels': arm['path_selection_uses_training_labels'],
                'target_selection_used_training_labels': True, 'features_use_source_labels': False})
            counts['zero_loss_contrasts'] += s.f(loss) == 0
            counts['known_gradient_collision'] += not any(delta[k] for k in joint.FEATURES if available[k])
    return sorted(result, key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id'])), dict(counts)


class WallAbstention(RuntimeError): pass


def select(sc, model_id, *, wall_seconds=WALL_SECONDS, timer=perf_counter, transition_budget=s.fresh.BUDGET):
    """Clock checks at source-run/context calls; restore INSTANCE hooks always.

    No module-global mutation, beam, best-so-far return or old-engine fallback.
    A single indivisible evidence call may overrun the cooperative deadline.
    """
    if type(wall_seconds) not in (int, float) or wall_seconds <= 0:
        raise ValueError('invalid_context_search_wall_budget')
    begun = timer(); checks = 0
    def check():
        nonlocal checks
        checks += 1
        if timer()-begun >= wall_seconds: raise WallAbstention()
    def wrap(fn):
        def call(*a, **kw):
            check(); v = fn(*a, **kw); check(); return v
        return call
    source = sc.original.source_scorer
    old_base, old_member, old_profile = source.base_run, source.member_features, sc.transition_profile
    try:
        source.base_run, source.member_features, sc.transition_profile = wrap(old_base), wrap(old_member), wrap(old_profile)
        check(); result = sc.decode(transition_budget=transition_budget); check()
    except WallAbstention:
        result = {'status': 'context_wall_budget_abstention', 'selected': None,
            'transitions': None, 'exact_optimum_under_declared_score': False,
            'context_joint_contract': sc.contract('delayed_three_run_exact_fraction'),
            'partial_winner_returned': False, 'operation_count_unavailable_after_interrupt': True}
    finally:
        source.base_run, source.member_features, sc.transition_profile = old_base, old_member, old_profile
    result['context_joint_contract'] = result['context_joint_contract'] | {'fitted_weights_claimed': True}
    result['learned_context_model'] = {'model_id': model_id, 'training_performed': True,
        'existing_26_frozen': True, 'reference_labels_used_for_selection': False,
        'purpose': 'local_noncommercial_research', 'operational_promotion': False}
    result['resource_guard'] = {'wall_seconds': wall_seconds, 'elapsed_seconds': timer()-begun,
        'clock_checks': checks, 'cooperative_not_hard_kill': True,
        'transition_budget': transition_budget, 'raw_segment_cap': sc.problem.max_segments}
    return result


def compare(rows):
    counts = Counter()
    for r in rows:
        a, b = r['baseline_evaluation'], r['evaluation']
        counts['previously_correct_lost'] += a['selected_hit'] is True and b['selected_hit'] is not True
        counts['newly_correct'] += a['selected_hit'] is not True and b['selected_hit'] is True
        counts['path_changed_with_complete_selection'] += r['selected_ids'] is not None and r['selected_ids'] != r['baseline_ids']
        counts['abstentions'] += not b['selected']
        counts[r['status']] += 1
    complete = [r for r in rows if r['evaluation']['selected']]
    return {'baseline_all': summarize([r | {'evaluation': r['baseline_evaluation']} for r in rows]),
        'context_all_abstentions_retained': summarize(rows),
        'paired_selected_baseline': summarize([r | {'evaluation': r['baseline_evaluation']} for r in complete]),
        'paired_selected_context': summarize(complete), 'changes': dict(counts),
        'paired_selected_subset_is_resource_biased': True}


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected or name in inputs and inputs[name] != h:
            raise ValueError('context_fit_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for name in ('tests/test_harmony_context_score_learning.py', 'tests/test_harmony_context_score_trial.py',
                 'scripts/validate_harmony_context_score.py', 'scripts/audit_harmony_context_score.py'):
        p = Path(name); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = {'version': VERSION, 'cohort': [r['sample_id'] for r in ctx['rows']],
        'configuration': learning.configuration(), 'wall_seconds_per_fresh_scope': WALL_SECONDS,
        'original_transition_budget': s.fresh.BUDGET, 'original_cap_preserved': True,
        'pool_report_sha256': PINS['report.json'], 'frozen_existing_model_sha256': prior.prior.prior.PINS['model.json.gz'],
        'fresh_search_after_model_freeze': True, 'dev_fit_inference_or_evaluation': False,
        'source_labels_used_for_prediction': False, 'production_modified': False,
        'purpose': 'local_noncommercial_research', 'use_contract_sha256': content_hash(ctx['use']), 'code_pins': code}
    save(output/'run-contract.json', contract)
    vectors, counts = contrasts(ctx)
    save(output/'training-vectors.json.gz', {'rows': vectors, 'counts': counts}, True)
    model = learning.fit(vectors, ctx['weights'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['report.json'])
    save(output/'model.json.gz', model, True); model_sha = io.digest(output/'model.json.gz')
    weights = learning.model_weights(model, ctx['weights'], ctx['use'], ctx['manifest'], ctx['parent_sha'], PINS['report.json'])
    save(output/'model-freeze.json', {'model_sha256': model_sha, 'postfit_selection_started': False,
        'existing_26_weights': {k: s.q(v) for k, v in ctx['weights'].items()}, 'dev_used': False})
    print(f'[context frozen] {len(vectors)} contrasts, {len(model["updates"])} updates', flush=True)
    records = []; sources = set(); edges = 0
    for i, row in enumerate(ctx['rows'], 1):
        sample = row['sample_id']; saved, entry, graph, ev, clock, args = prior.prepare_sample(ctx, row, read)
        original = s.Scorer(graph, ev, ctx['weights'], **args)
        sc = joint.Scorer(original, weights, **args)
        result = select(sc, model['model_id'])
        # Label-derived evaluation is constructed only AFTER blind search.
        ref = ctx['refs'][sample]
        evaluation = evaluate(native_reference(ref), native_prediction(result['selected'], ref['sample_span']),
            ref['sample_span'], selected=result['selected'] is not None)
        baseline = ctx['joint_packets'][sample]['fresh_predictions']['zero_delegate']
        baseline_evaluation = evaluate(native_reference(ref), native_prediction(baseline['selected'], ref['sample_span']),
            ref['sample_span'], selected=True)
        cells = tuple(prior.prior.prior.parent.parent.old_training.prior.old.cells_from_record(ref))
        loss = training_loss(graph, cells, s.fresh.BOUNDARY_WEIGHT)
        selected_ids = s.fresh.path_ids(result['selected']) if result['selected'] else None
        baseline_ids = s.fresh.path_ids(baseline['selected'])
        target_ids = saved['arms']['epoch3_target']['path_ids']
        receipts = {'baseline': sc.path_receipt(baseline_ids), 'stored_target': sc.path_receipt(target_ids, target=True)}
        for arm, ids in (('baseline', baseline_ids), ('stored_target', target_ids)):
            pred = {'selected': {'segments': [{'semantic_group_ref': x} for x in ids]}}
            receipts[arm]['post_prediction_training_loss'] = path_loss(graph, pred, loss)
        packet = {k: saved[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split', 'entry',
            'full_source_paths', 'source_provenance', 'source_ir_content_sha256', 'source_clock_gate',
            'original_scope_artifact', 'original_scope_sha256', 'original_graph_sha256', 'original_edge_count')}
        packet.update(result=result, evaluation=evaluation, baseline_evaluation=baseline_evaluation,
            diagnostic_receipts=receipts, model_sha256=model_sha, original_candidates_preserved=True,
            full_source_not_clipped=True, human_validated=False, source_labels_used_for_inference=False)
        p, h = save(output/'cases'/(sample+'.json.gz'), packet, True)
        records.append({k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {
            'artifact': p, 'sha256': h, 'status': result['status'], 'evaluation': evaluation,
            'baseline_evaluation': baseline_evaluation, 'selected_ids': selected_ids, 'baseline_ids': baseline_ids})
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges)
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        print(f'[context ordinary Train {i}/{len(ctx["rows"])}] {sample}: {result["status"]}, hit={evaluation["selected_hit"]}', flush=True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h: raise ValueError('context_fit_final_guard_changed:'+p)
    report = contract | {'complete': True, 'fit_performed': True, 'fresh_ordinary_attempts': len(records),
        'full_source_packages': len(sources), 'original_edges': edges, 'calibration_counts': counts,
        'training_contrasts': len(vectors), 'model_sha256': model_sha, 'tables': compare(records),
        'excluded_parent_scopes_preserved': len(ctx['original']['records'])-len(records),
        'independent_accuracy_claimed': False, 'margin_is_not_accuracy': True, 'operational_weights_changed': False,
        'records': records, 'input_hashes': inputs, 'artifact_hashes': artifacts, 'code_hashes': code,
        'elapsed_seconds': perf_counter()-begun, 'current_dev_reconstructed_or_used': False,
        'historical_parent_containers_include_exposed_dev': True}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'fresh_ordinary_attempts', 'full_source_packages', 'training_contrasts', 'tables', 'elapsed_seconds')}, indent=2), flush=True)
