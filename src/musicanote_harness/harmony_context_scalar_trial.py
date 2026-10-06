"""No-fit Train replay of the frozen Stage80 model with score-only context.

Sealed detailed DP/receipts are unchanged. Same118 original scopes, same20s
cooperative guard, same2M feasible-state/raw-edge comparisons and cap6.
This tests computational efficiency, not promotion of the unadopted model.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from . import harmony_context_score_trial as prior
from . import harmony_context_scalar_index as scalar

VERSION = 'harmony-context-scalar-train-replay-0.1.0'
ROOT = 'K:/Music Analysis/output/harmony-context-score-learning-2026-10-05-r1'
PINS = {'report.json': 'abdcd93b7e1d75bedfb68dbf9e24e71a09793ae7411a3afb95cb86cb33b8e119',
    'run-contract.json': '86cb6902189d746a381bfe92ac9ed6ce9223007ff21a49bae354258de4efae0d',
    'post-seal-audit.json': 'd2efea5f69ae4fa5ef18443ae207ef468d7f944076bda7d94b3ff795b91e5c69',
    'model.json.gz': 'f27db2416de803d3245c960e827f3786f8b3947bc1fa538fc15c9d90f17096f4',
    'model-freeze.json': 'e0284db6ad806b16508e01c21c26f378325628c43da3dd4ea4e19f8003e56c3d'}
s, io, load = prior.s, prior.io, prior.load


def context(read):
    report, contract, audit, model, freeze = [read(Path(ROOT)/p, h) for p, h in PINS.items()]
    if (report['complete'] is not True or audit['passed'] is not True
            or audit['report_sha256'] != PINS['report.json'] or report['model_sha256'] != PINS['model.json.gz']
            or freeze['model_sha256'] != PINS['model.json.gz'] or contract['production_modified'] is not False):
        raise ValueError('scalar_parent_or_frozen_model_not_sealed')
    for p, h in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items(): read(p, h, raw=True)
    ctx = prior.context(read)
    if contract['cohort'] != [r['sample_id'] for r in ctx['rows']]: raise ValueError('scalar_train_cohort_changed')
    ctx['context_weights'] = prior.learning.model_weights(model, ctx['weights'], ctx['use'], ctx['manifest'],
                                                         ctx['parent_sha'], prior.PINS['report.json'])
    if freeze['existing_26_weights'] != {k: s.q(v) for k, v in ctx['weights'].items()}:
        raise ValueError('scalar_frozen_old26_changed')
    ctx['model'] = model; ctx['stage80_report'] = report
    ctx['stage80_records'] = {r['sample_id']: r for r in report['records']}
    return ctx


def select(sc, model_id, *, wall_seconds=prior.WALL_SECONDS, timer=perf_counter, transition_budget=s.fresh.BUDGET):
    if type(wall_seconds) not in (int, float) or wall_seconds <= 0: raise ValueError('invalid_scalar_wall_budget')
    begun = timer(); checks = 0
    def check():
        nonlocal checks
        checks += 1
        if timer()-begun >= wall_seconds: raise prior.WallAbstention()
    def wrap(fn):
        def call(*a, **kw):
            check(); value = fn(*a, **kw); check(); return value
        return call
    source = sc.original.source_scorer
    hooks = ((source, 'base_run'), (source, 'member_features'),
             (sc, 'transition_profile'), (sc, 'scalar_values'))
    original = [(obj, name, getattr(obj, name)) for obj, name in hooks]
    try:
        for obj, name, fn in original: setattr(obj, name, wrap(fn))
        check(); result = sc.decode(transition_budget=transition_budget); check()
    except prior.WallAbstention:
        result = {'status': 'context_wall_budget_abstention', 'selected': None, 'transitions': None,
            'exact_optimum_under_declared_score': False, 'context_joint_contract': sc.contract('delayed_three_run_exact_fraction'),
            'partial_winner_returned': False, 'operation_count_unavailable_after_interrupt': True,
            'scalar_projection_diagnostics': dict(sc.scalar_index.stats) if sc.scalar_index else {}}
    finally:
        for obj, name, fn in original: setattr(obj, name, fn)
    result['context_joint_contract'] |= {'fitted_weights_claimed': True}
    result['frozen_model_ref'] = {'model_id': model_id, 'model_sha256': PINS['model.json.gz'],
        'fit_performed_this_run': False, 'model_was_fitted_on_train': True, 'existing_26_frozen': True,
        'reference_labels_used_for_selection': False, 'operational_promotion': False}
    result['resource_guard'] = {'wall_seconds': wall_seconds, 'elapsed_seconds': timer()-begun,
        'clock_checks': checks, 'cooperative_not_hard_kill': True,
        'transition_budget': transition_budget, 'raw_segment_cap': sc.problem.max_segments,
        'lazy_scalar_index_construction_included': True, 'detailed_winner_replay_included': True}
    return result


def verify_projection(sc, ids, receipt):
    runs = prior.joint.context_features.control.completed_runs(sc.problem, ids)
    if len(runs)-1 != len(receipt['context']['transitions']): raise ValueError('scalar_transition_count_changed')
    for i, p in enumerate(receipt['context']['transitions'], 1):
        v = sc.scalar_values(runs, i)
        if (v['availability'] != p['availability']
                or {k: s.q(x) for k, x in v['observed_feature_sums'].items()} != p['observed_feature_sums']
                or {k: None if x is None else s.q(x) for k, x in v['features'].items()} != p['features']):
            raise ValueError('scalar_original_detailed_feature_mismatch')
    return len(runs)-1


def compatibility(old, new):
    if old['selected'] is None or new['selected'] is None: return False
    a, b = old['selected'], new['selected']
    if (s.fresh.path_ids(a) != s.fresh.path_ids(b) or a['score_cost'] != b['score_cost']
            or not prior.prior.prior.prior.seals.same_json(a['context_score'], b['context_score'])
            or old['transitions'] != new['transitions'] or old['search_diagnostics'] != new['search_diagnostics']):
        raise ValueError('scalar_sealed_dp_winner_or_operation_count_changed')
    return True


def summaries(records):
    counts = Counter()
    for r in records:
        counts['common_completed_identical'] += r['same_completed_winner']
        counts['recovered_previous_abstentions'] += r['prior_selected_ids'] is None and r['selected_ids'] is not None
        counts['previous_completion_now_abstention'] += r['prior_selected_ids'] is not None and r['selected_ids'] is None
        counts[r['status']] += 1
    rows = [r | {'baseline_ids': r['prior_selected_ids'], 'baseline_evaluation': r['prior_evaluation']} for r in records]
    musical = [r | {'baseline_ids': r['original_baseline_ids'], 'baseline_evaluation': r['original_baseline_evaluation']} for r in records]
    return {'resource_counts': dict(counts), 'against_same_model_stage80': prior.compare(rows),
        'against_frozen_old26': prior.compare(musical),
        'historical_wall_timings_are_not_controlled_speed_benchmark': True}


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); name = str(p.resolve()); h = io.digest(p)
        if expected is not None and h != expected or name in inputs and inputs[name] != h:
            raise ValueError('scalar_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for name in ('tests/test_harmony_context_scalar_index.py', 'tests/test_harmony_context_scalar_trial.py',
                 'scripts/validate_harmony_context_scalar.py', 'scripts/audit_harmony_context_scalar.py'):
        p = Path(name); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = {'version': VERSION, 'cohort': [r['sample_id'] for r in ctx['rows']],
        'parent_report_sha256': PINS['report.json'], 'model_sha256': PINS['model.json.gz'],
        'scalar_projection_version': scalar.VERSION, 'fit_performed': False,
        'existing_26_and_new_7_coefficients_unchanged': True,
        'wall_seconds_per_fresh_scope': prior.WALL_SECONDS, 'transition_budget': s.fresh.BUDGET,
        'sealed_dp_and_raw_operation_unit_unchanged': True, 'original_graph_and_cap_preserved': True,
        'dev_inference_or_evaluation': False, 'source_labels_used_for_prediction': False,
        'production_modified': False, 'operational_weights_changed': False,
        'purpose': 'local_noncommercial_research', 'code_pins': code,
        'historical_not_controlled_wall_comparison': True}
    save(output/'run-contract.json', contract)
    records = []; sources = set(); edges = projections = 0
    for i, row in enumerate(ctx['rows'], 1):
        sample = row['sample_id']; tick = perf_counter()
        saved, entry, graph, ev, clock, args = prior.prior.prepare_sample(ctx, row, read)
        sc = scalar.Scorer(s.Scorer(graph, ev, ctx['weights'], **args), ctx['context_weights'], **args)
        preparation = perf_counter()-tick
        result = select(sc, ctx['model']['model_id'])
        previous_record = ctx['stage80_records'][sample]
        previous = read(previous_record['artifact'], previous_record['sha256'])
        same = compatibility(previous['result'], result)
        selected = result['selected']; ids = s.fresh.path_ids(selected) if selected else None
        receipts = {}
        for name, chain in (('fresh', ids), ('prior_selected', previous_record['selected_ids']),
                            ('original_baseline', previous_record['baseline_ids'])):
            if chain is None: continue
            receipt = sc.path_receipt(chain); projections += verify_projection(sc, chain, receipt)
            if name == 'fresh' and not prior.prior.prior.prior.seals.same_json(receipt, selected['context_score']):
                raise ValueError('scalar_fresh_independent_receipt_changed')
            receipts[name] = receipt
        # Reference-derived evaluation ONLY after blind inference. No loss-fit.
        ref = ctx['refs'][sample]
        evaluation = prior.evaluate(prior.native_reference(ref), prior.native_prediction(selected, ref['sample_span']),
                                    ref['sample_span'], selected=selected is not None)
        packet = {k: saved[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split', 'entry',
            'full_source_paths', 'source_provenance', 'source_ir_content_sha256', 'source_clock_gate',
            'original_scope_artifact', 'original_scope_sha256', 'original_graph_sha256', 'original_edge_count')}
        packet.update(result=result, evaluation=evaluation, prior_case_ref=previous_record['artifact'],
            prior_case_sha256=previous_record['sha256'], prior_evaluation=previous_record['evaluation'],
            original_baseline_evaluation=previous_record['baseline_evaluation'], same_completed_winner=same,
            post_search_cost_receipts=receipts, setup_elapsed_seconds=preparation,
            full_source_not_clipped=True, source_labels_used_for_inference=False, human_validated=False)
        p, h = save(output/'cases'/(sample+'.json.gz'), packet, True)
        records.append({k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {
            'artifact': p, 'sha256': h, 'status': result['status'], 'evaluation': evaluation,
            'prior_evaluation': previous_record['evaluation'], 'original_baseline_evaluation': previous_record['baseline_evaluation'],
            'selected_ids': ids, 'prior_selected_ids': previous_record['selected_ids'],
            'original_baseline_ids': previous_record['baseline_ids'], 'same_completed_winner': same,
            'elapsed_seconds': result['resource_guard']['elapsed_seconds'],
            'historical_elapsed_seconds': previous['result']['resource_guard']['elapsed_seconds']})
        sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges)
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        print(f'[scalar Train {i}/{len(ctx["rows"])}] {sample}: {result["status"]}, hit={evaluation["selected_hit"]}', flush=True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h: raise ValueError('scalar_final_guard_changed:'+p)
    report = contract | {'complete': True, 'fresh_ordinary_attempts': len(records), 'full_source_packages': len(sources),
        'original_edges': edges, 'scalar_detailed_transitions_compared': projections, 'tables': summaries(records),
        'excluded_parent_scopes_preserved': ctx['stage80_report']['excluded_parent_scopes_preserved'],
        'independent_accuracy_claimed': False, 'records': records, 'input_hashes': inputs,
        'artifact_hashes': artifacts, 'code_hashes': code, 'elapsed_seconds': perf_counter()-begun,
        'current_dev_reconstructed_or_used': False, 'historical_parent_containers_include_exposed_dev': True}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'fresh_ordinary_attempts', 'full_source_packages',
        'scalar_detailed_transitions_compared', 'tables', 'elapsed_seconds')}, indent=2), flush=True)
