"""Train-only measurement of new hold/change vectors on SEALED stored paths.

No fit, decoder, pool reranking, Dev evaluation or UI change. Test whether
these new conditional interactions actually distinguish existing contrasts
before integrating a future-dependent term into capped exact joint search.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter
from . import harmony_transition_support_trial as prior
from . import harmony_context_competition as observation

s, io, load = prior.s, prior.io, prior.load
VERSION = 'harmony-context-competition-train-0.1.0'
ROOT = 'C:/Users/snoop/.codex/visualizations/2026/08/14/019fffe2-e831-7f32-a7d1-2b93c5a39b2c/harmony-transition-support-2026-10-05-r2'
PINS = {'report.json': '7e9830ebab3a14dfd466fce18effce19f66bd6cb5e83d7f2a499a12198e9a172',
    'run-contract.json': '25e73acc5da63cefff68ab089287f7d9329243c44a041cbfe6324763bb2689a5',
    'post-seal-audit.json': '9f302f80c00a241876502a367e17b2c5b5cd270e3464fe8725c08aa9bfd77cb4'}


def context(read):
    parent, contract, audit = [read(Path(ROOT)/p, h) for p, h in PINS.items()]
    if parent['complete'] is not True or audit['passed'] is not True or parent['fit_performed'] is not False:
        raise ValueError('competition_parent_not_completed')
    for p, h in (parent['input_hashes'] | parent['code_hashes'] | parent['artifact_hashes']).items(): read(p, h, raw=True)
    ctx = prior.context(read)
    if ([r['sample_id'] for r in ctx['rows']] != contract['cohort']
            or contract['source_profile_reads_reference_labels'] is not False):
        raise ValueError('competition_original_train_inventory_changed')
    ctx['stored'] = {r['sample_id']: r for r in parent['records']}
    return ctx


def vector_difference(a, b):
    """Only jointly available differences are usable for later learning."""
    return {k: s.q(s.f(a['features'][k])-s.f(b['features'][k]))
            if a['availability'][k] and b['availability'][k] else None for k in observation.FEATURES}


def build_sample(ctx, row, read):
    sample = row['sample_id']; old = ctx['stored'][sample]; saved = read(old['artifact'], old['sha256'])
    ref = ctx['refs'][sample]
    entry, graph, ev, clock, args = prior.parent.parent.old_training.prior.prepare_context(
        ctx['before'][sample], ref, ctx['manifest'], ctx['integration'], read)
    original = read(row['scope_artifact'], row['scope_sha256'])
    if (not clock.scope(ref['sample_span'])['accepted'] or not prior.seals.same_json(entry, saved['entry'])
            or not prior.seals.same_json(prior.parent.parent.graph_packet(graph), original['problem'])
            or ev.source.source_ir_content_sha256 != saved['source_ir_content_sha256']):
        raise ValueError('competition_source_clock_graph_changed')
    scorer = s.Scorer(graph, ev, ctx['weights'], **args); arms = {}
    shared_context = observation.Context(ev, **args)
    for arm in prior.ARMS:
        path = saved['arms'][arm]
        if not path['selected']:
            arms[arm] = {'selected': False, 'status': path['status'], 'retried': False}; continue
        profile = observation.observe_path(graph, ev, path['path_ids'], context=shared_context)
        receipt = scorer.receipt(path['path_ids'], target=arm == 'epoch3_target')
        if not prior.seals.same_json(receipt, path['same_frozen_weights_receipt']):
            raise ValueError('competition_original_cost_changed')
        # Reference timing is attached only AFTER the label-blind vector.
        diagnostic = [{'boundary': t['span']['start'], 'reference_boundary_at_exact_time':
            s.f(t['span']['start']) in {s.f(b) for b in saved['reference_boundaries']}} for t in profile['transitions']]
        arms[arm] = {'selected': True, 'path_ids': path['path_ids'], 'source_profile': profile,
            'unchanged_original_cost_receipt': receipt, 'reference_timing_diagnostic': diagnostic,
            'unchanged_original_training_loss': path['training_loss'],
            'path_selection_uses_training_labels': path['training_labels_used_for_original_path_selection'],
            'analysis_export_allowed': False}
    differences = {arm: vector_difference(arms[arm]['source_profile'], arms['epoch3_target']['source_profile'])
                   if arms[arm]['selected'] else None for arm in prior.ARMS if arm != 'epoch3_target'}
    clock.check_source()
    result = {k: saved[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split', 'entry',
        'full_source_paths', 'source_provenance', 'source_ir_content_sha256', 'source_clock_gate',
        'original_scope_artifact', 'original_scope_sha256', 'original_graph_sha256', 'original_edge_count')}
    result.update(prior_transition_artifact=old['artifact'], prior_transition_sha256=old['sha256'],
        arms=arms, jointly_available_arm_minus_target_vectors=differences,
        full_source_not_clipped=True, new_fit_or_search=False, human_validated=False, independent_test_case=False)
    ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
    return result


def summarize(packets):
    arms = {a: Counter() for a in prior.ARMS}; contrasts = {a: Counter() for a in prior.ARMS if a != 'epoch3_target'}
    for p in packets:
        for arm, a in p['arms'].items():
            c = arms[arm]; c['scopes'] += 1
            if not a['selected']: c['preserved_abstentions'] += 1; continue
            profile = a['source_profile']; c['paths'] += 1
            c['zero_original_training_loss'] += s.f(a['unchanged_original_training_loss']['total']) == 0
            for k in observation.FEATURES:
                if profile['availability'][k]:
                    c[k+':available_paths'] += 1
                    c[k+':nonzero_paths'] += s.f(profile['features'][k]) != 0
                else: c[k+':unavailable_paths'] += 1
            for t, d in zip(profile['transitions'], a['reference_timing_diagnostic']):
                kind = 'reference_time' if d['reference_boundary_at_exact_time'] else 'extra_time'
                c['transitions'] += 1; c[kind] += 1
                c[kind+':conditional_figures'] += len(t['conditional_figures'])
                c[kind+':transitions_with_conditional_figures'] += bool(t['conditional_figures'])
                for figure in t['conditional_figures']: c[kind+':'+figure['kind']] += 1
                if t['availability']['dominant_credit_with_hold_conflict']:
                    c[kind+':dominant_credit_conflict'] += s.f(t['features']['dominant_credit_with_hold_conflict']) > 0
                else: c[kind+':dominant_conflict_unavailable'] += 1
                if t['conditional_figures']:
                    c[kind+':figures_with_remaining_foreign_notes'] += bool(t['remaining_held_foreign_ids'])
                    c[kind+':figures_with_held_lowest'] += s.f(t['observed_feature_sums']['continuing_left_lowest_coverage']) > 0
        for arm, vector in p['jointly_available_arm_minus_target_vectors'].items():
            c = contrasts[arm]
            if vector is None: c['preserved_abstentions'] += 1; continue
            c['contrasts'] += 1
            c['any_available_nonzero_delta'] += any(v is not None and s.f(v) != 0 for v in vector.values())
            c['all_features_available'] += all(v is not None for v in vector.values())
            c['all_features_available_and_zero'] += all(v is not None and s.f(v) == 0 for v in vector.values())
            for k, v in vector.items():
                c[k+':unavailable' if v is None else k+':nonzero' if s.f(v) else k+':zero'] += 1
    return {'by_arm': {k: dict(v) for k, v in arms.items()}, 'arm_minus_train_target': {k: dict(v) for k, v in contrasts.items()},
        'denominator': 'overlapping_scope_path_transition_occurrences_not_unique_notes_or_works',
        'new_accuracy_not_measured': True, 'reference_time_match_is_not_correct_chord_or_nct_gold': True}


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs = {}; artifacts = {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and expected != h or name in inputs and inputs[name] != h:
            raise ValueError('competition_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in (Path('tests/test_harmony_context_competition.py'), Path('tests/test_harmony_context_competition_trial.py'),
              Path('scripts/validate_harmony_context_competition.py'), Path('scripts/audit_harmony_context_competition.py')):
        code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    contract = {'version': VERSION, 'cohort': [r['sample_id'] for r in ctx['rows']], 'arms': prior.ARMS,
        'features': observation.FEATURES, 'normalization': 'source_sound_overlap_note_time_in_original_scope',
        'code_pins': code, 'prior_completed_report_sha256': PINS['report.json'],
        'original_model_sha256': prior.PINS['model.json.gz'],
        'fit_performed': False, 'fresh_search_performed': False, 'pool_reranking_performed': False,
        'dev_inference_or_evaluation': False, 'weights_changed': False, 'production_modified': False,
        'reference_labels_used_for_new_features': False, 'original_cost_and_abstentions_preserved': True,
        'no_hard_geometry_duration_support_gate': True, 'purpose': 'local_noncommercial_research'}
    save(output/'run-contract.json', contract)
    records = []; packets = []; sources = set(); families = set(); edges = 0
    for i, row in enumerate(ctx['rows'], 1):
        packet = build_sample(ctx, row, read); packets.append(packet)
        sources.add(packet['source_ir_content_sha256']); families.add(row['work_family_id']); edges += packet['original_edge_count']
        p, h = save(output/'cases'/(row['sample_id']+'.json.gz'), packet, True)
        records.append({k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {'artifact': p, 'sha256': h})
        print(f'[Train context competition {i}/{len(ctx["rows"])}] {row["sample_id"]}', flush=True)
    for p, h in (inputs | artifacts | code).items():
        if io.digest(p) != h: raise ValueError('competition_final_guard_changed:'+p)
    report = contract | {'complete': True, 'scopes': len(records), 'full_source_packages': len(sources),
        'work_families': len(families), 'original_edges': edges, 'excluded_parent_scopes_preserved': len(ctx['original']['records'])-len(records),
        'records': records, 'summary': summarize(packets), 'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'elapsed_seconds': perf_counter()-tick, 'current_dev_reconstructed_or_used': False,
        'historical_parent_containers_include_exposed_dev': True,
        'independent_accuracy_or_new_prediction_improvement_claimed': False}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    r = run(p.parse_args().output)
    print(json.dumps({k: r[k] for k in ('complete', 'scopes', 'full_source_packages', 'work_families', 'summary', 'elapsed_seconds')}, indent=2), flush=True)
