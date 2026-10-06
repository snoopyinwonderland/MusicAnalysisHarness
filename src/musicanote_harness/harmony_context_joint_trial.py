"""Train source replay, zero-score compatibility, small-graph exact stress.

No fitting, Dev, reference accuracy claim, or operational weight choice.
Small graph stress is selected by edge count and distinct source SHA only,
BEFORE any new prediction. Its signed coefficients are numerical test values.
"""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_context_competition_trial_v2 as prior
from . import harmony_context_joint_decoder as joint

VERSION = 'harmony-context-joint-compatibility-train-0.1.0'
ROOT = 'K:/Music Analysis/output/harmony-context-competition-2026-10-05-r3'
PINS = {'report.json': 'f2cec47280f3101a4b56b51c655ec7e8ec018b7d696b34b71022dc7d86583924',
        'run-contract.json': '2e5bef988d7442a615d3017681c81e3c04c515c93048500ec332d53d7ed8f7dc',
        'post-seal-audit.json': '5d44c73906a89db05c00ee25b53fb8d04ff930268b965941bc90642701a9c286'}
s, io, load = prior.s, prior.io, prior.load
STRESS = {k: F(1 if i % 2 == 0 else -1, 8) for i, k in enumerate(joint.FEATURES)}


def select_stress(packets, count=8, max_edges=100):
    rows = sorted((p['original_edge_count'], p['sample_id'], p['source_ir_content_sha256']) for p in packets
                  if p['original_edge_count'] <= max_edges)
    seen = set(); chosen = []
    for _, ident, source in rows:
        if source in seen: continue
        seen.add(source); chosen.append(ident)
        if len(chosen) >= count: break
    return chosen


def context(read):
    report, contract, audit = [read(Path(ROOT)/p, sha) for p, sha in PINS.items()]
    if report['complete'] is not True or audit['passed'] is not True or report['fit_performed'] is not False:
        raise ValueError('joint_parent_not_completed')
    for p, sha in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items(): read(p, sha, raw=True)
    ctx = prior.context(read)
    packets = [read(row['artifact'], row['sha256']) for row in report['records']]
    if ([p['sample_id'] for p in packets] != [r['sample_id'] for r in ctx['rows']]
            or contract['cohort'] != [r['sample_id'] for r in ctx['rows']]):
        raise ValueError('joint_parent_inventory_changed')
    ctx['competition_packets'] = {p['sample_id']: p for p in packets}
    ctx['stress_ids'] = select_stress(packets)
    return ctx


def check_profile(receipt, profile):
    c = receipt['context']
    if (not prior.prior.seals.same_json(c['observed_feature_sums'], profile['observed_feature_sums'])
            or c['availability'] != profile['availability'] or len(c['transitions']) != len(profile['transitions'])):
        raise ValueError('joint_local_full_context_vector_mismatch')
    for a, b in zip(c['transitions'], profile['transitions']):
        if not prior.prior.seals.same_json(a, b): raise ValueError('joint_local_full_transition_mismatch')
    for k in joint.FEATURES:
        known = sum((s.f(p['features'][k]) for p in profile['transitions'] if p['features'][k] is not None), F())
        if s.q(known) != c['scored_available_feature_sums'][k]: raise ValueError('joint_unknown_local_cost_policy_mismatch')


def prepare_sample(ctx, row, read):
    sample = row['sample_id']; saved = ctx['competition_packets'][sample]; ref = ctx['refs'][sample]
    entry, graph, ev, clock, args = prior.prior.parent.parent.old_training.prior.prepare_context(
        ctx['before'][sample], ref, ctx['manifest'], ctx['integration'], read)
    original = read(row['scope_artifact'], row['scope_sha256'])
    if (not clock.scope(ref['sample_span'])['accepted'] or not prior.prior.seals.same_json(entry, saved['entry'])
            or not prior.prior.seals.same_json(prior.prior.parent.parent.graph_packet(graph), original['problem'])
            or ev.source.source_ir_content_sha256 != saved['source_ir_content_sha256']):
        raise ValueError('joint_source_clock_graph_changed')
    return saved, entry, graph, ev, clock, args


def build_sample(ctx, row, read, *, search=True):
    sample = row['sample_id']; saved, entry, graph, ev, clock, args = prepare_sample(ctx, row, read)
    base = s.Scorer(graph, ev, ctx['weights'], **args)
    shared = prior.observation.Context(ev, **args)
    zero = joint.Scorer(base, joint.ZERO, context=shared); stress = joint.Scorer(base, STRESS, context=shared)
    arms = {}
    for arm in prior.prior.ARMS:
        a = saved['arms'][arm]
        if not a['selected']:
            arms[arm] = {'selected': False, 'status': a['status'], 'retried': False}; continue
        target = arm == 'epoch3_target'
        z, r = zero.path_receipt(a['path_ids'], target=target), stress.path_receipt(a['path_ids'], target=target)
        check_profile(r, a['source_profile'])
        if (not prior.prior.seals.same_json(z['legacy'], a['unchanged_original_cost_receipt'])
                or z['cost'] != z['legacy']['cost'] or z['context_cost'] != s.q(0)):
            raise ValueError('joint_original_zero_cost_changed')
        arms[arm] = {'selected': True, 'path_ids': a['path_ids'], 'zero_receipt': z, 'stress_receipt': r,
            'path_selection_uses_training_labels': a['path_selection_uses_training_labels'], 'analysis_export_allowed': False}
    fresh = {}; tick = perf_counter()
    if search:
        result = zero.decode(); selected = result['selected']; previous = saved['arms']['adversarial_frozen']
        if selected is None or tuple(previous['path_ids']) != s.fresh.path_ids(selected) or selected['score_cost'] != previous['unchanged_original_cost_receipt']['cost']:
            raise ValueError('joint_fresh_zero_control_changed')
        fresh['zero_delegate'] = result
        if sample in ctx['stress_ids']:
            a, b = zero.decode(force_delayed=True), stress.decode()
            if a['selected'] is None or s.fresh.path_ids(a['selected']) != s.fresh.path_ids(selected) or a['selected']['score_cost'] != selected['score_cost']:
                raise ValueError('joint_forced_delayed_zero_changed')
            fresh['zero_delayed'] = a; fresh['signed_stress_delayed'] = b
    clock.check_source()
    packet = {k: saved[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split', 'entry',
        'full_source_paths', 'source_provenance', 'source_ir_content_sha256', 'source_clock_gate',
        'original_scope_artifact', 'original_scope_sha256', 'original_graph_sha256', 'original_edge_count')}
    packet.update(arms=arms, fresh_predictions=fresh, original_candidate_graph_preserved=True,
        signed_stress_weights_are_not_fitted=True, correctness_or_accuracy_not_evaluated=True,
        fresh_search_elapsed_seconds=perf_counter()-tick, full_source_not_clipped=True, human_validated=False)
    ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
    return packet


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs = {}; artifacts = {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); sha = io.digest(p); name = str(p.resolve())
        if (expected is not None and sha != expected) or (name in inputs and inputs[name] != sha):
            raise ValueError('joint_input_changed:'+name)
        inputs[name] = sha; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for name in ('tests/test_harmony_context_joint_decoder.py', 'tests/test_harmony_context_joint_trial.py',
                 'scripts/validate_harmony_context_joint_decoder.py', 'scripts/audit_harmony_context_joint_trial.py'):
        p = Path(name); code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = {'version': VERSION, 'cohort': [r['sample_id'] for r in ctx['rows']],
        'stress_cohort': ctx['stress_ids'], 'stress_cohort_policy': 'ascending_original_edges_then_sample_id_first_8_distinct_source_sha_max_100_edges',
        'signed_stress_coefficients': {k: s.q(v) for k, v in STRESS.items()}, 'zero_coefficients': {k: s.q(v) for k, v in joint.ZERO.items()},
        'code_pins': code, 'parent_report_sha256': PINS['report.json'],
        'original_model_sha256': prior.prior.PINS['model.json.gz'], 'fit_performed': False,
        'fresh_zero_controls': True, 'fresh_signed_numerical_stress_not_accuracy': True,
        'dev_inference_or_evaluation': False, 'operational_weights_changed': False, 'production_modified': False,
        'new_prediction_selection_reads_labels': False, 'purpose': 'local_noncommercial_research',
        'original_raw_segment_cap_and_2M_budget_preserved': True}
    save(output/'run-contract.json', contract)
    records = []; sources = set(); families = set(); edges = stored_paths = transitions = figures = 0
    for i, row in enumerate(ctx['rows'], 1):
        packet = build_sample(ctx, row, read); sources.add(packet['source_ir_content_sha256']); families.add(packet['work_family_id'])
        edges += packet['original_edge_count']
        for a in packet['arms'].values():
            if a['selected']:
                stored_paths += 1; transitions += len(a['stress_receipt']['context']['transitions'])
                figures += sum(len(t['conditional_figures']) for t in a['stress_receipt']['context']['transitions'])
        p, sha = save(output/'cases'/(row['sample_id']+'.json.gz'), packet, True)
        records.append({k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {'artifact': p, 'sha256': sha})
        print(f'[Train delayed context {i}/{len(ctx["rows"])}] {row["sample_id"]}', flush=True)
    for p, sha in (inputs | artifacts | code).items():
        if io.digest(p) != sha: raise ValueError('joint_final_guard_changed:'+p)
    report = contract | {'complete': True, 'scopes': len(records), 'full_source_packages': len(sources),
        'work_families': len(families), 'original_edges': edges, 'stored_paths_replayed': stored_paths,
        'transitions_replayed': transitions, 'conditional_figures_replayed': figures,
        'fresh_zero_controls_unchanged': len(records), 'fresh_delayed_stress_scopes': len(ctx['stress_ids']),
        'records': records, 'input_hashes': inputs, 'artifact_hashes': artifacts, 'code_hashes': code,
        'elapsed_seconds': perf_counter()-tick, 'independent_accuracy_or_improvement_claimed': False,
        'historical_parent_containers_include_exposed_dev': True, 'current_dev_reconstructed_or_used': False}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'scopes', 'full_source_packages', 'stored_paths_replayed',
        'fresh_zero_controls_unchanged', 'fresh_delayed_stress_scopes', 'elapsed_seconds')}, indent=2), flush=True)
