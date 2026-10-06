"""Re-mine ALL approved Train scopes; freeze scores, do not tune on Dev.

Historical parent containers include exposed Dev records. They are read for
SHA lineage but only approved Train records enter reconstruction/evaluation.
This is an in-sample diagnostic and pool refresh, NOT independent accuracy.
"""
import argparse
from collections import Counter
from pathlib import Path
from time import perf_counter
import json

from . import harmony_fresh_train_negatives as s
from . import harmony_member_timing_training as old_training
from . import harmony_member_timing_learning as timing_learning
from .harmony_structured_learning import validate_use_contract, content_hash
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_temporal_scoring_trial import graph_packet, graph_from_packet
from .harmony_bounded_recovery_trial import load
from . import harmony_expanded_benchmark as io

VERSION = 'harmony-fresh-train-trial-0.1.0'
TIMING_MODEL = 'output/harmony-member-timing-2026-10-05-r1/model.json'
TIMING_MODEL_SHA = 'c979d364221f7f802ea3b317a0dceea664fbd39fe10c79e15174d8a6f15c481d'


def train_records(previous, learned, approvals):
    before = {r['sample_id']: r for r in previous['records']}
    after = {r['sample_id']: r for r in learned['records']}
    if len(before) != len(previous['records']) or len(after) != len(learned['records']):
        raise ValueError('duplicate_parent_scope')
    if set(before) != set(after): raise ValueError('parent_scope_set_changed')
    rows = [r for r in after.values() if r['split'] == 'train']
    # prepare_context later verifies manifest membership and approval identity.
    families = {a['manifest_entry_id'] for a in approvals.values()}
    if not families: raise ValueError('no_approved_training_entries')
    return before, sorted(rows, key=lambda r: (r['work_family_id'], r['sample_id']))


def classify(gate, ceiling, result, evaluation):
    if not gate['accepted']: return 'source_clock_quarantined'
    if result['selected'] is None: return 'prediction_abstention'
    if not evaluation['fully_evaluable']: return 'partial_or_unsupported_reference'
    if evaluation['selected_hit']: return 'reference_agreement'
    if ceiling['reachable']: return 'selection_error_with_reference_path'
    if ceiling['reachable'] is False: return 'reference_path_absent_or_cap_blocked'
    return 'reference_path_unresolved'


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected: raise ValueError('input_sha_mismatch:'+name)
        if name in inputs and inputs[name] != h: raise ValueError('input_changed_during_run:'+name)
        inputs[name] = h
        return None if raw else load(p)
    previous, recall, integration, use, historical, learned = [read(p, h) for p, h in old_training.PINS.items()]
    if content_hash(historical) != learned['model_content_sha256']: raise ValueError('historical_model_binding_changed')
    manifest = recall['package_manifest']; approvals = validate_use_contract(use, manifest, old_training.PARENT_SHA)
    for approval in approvals.values():
        lic = approval['source_license']
        for k in ('local_license', 'readme'): read(lic[k+'_path'], lic[k+'_sha256'], raw=True)
    fixed = old_training.old_learning.model_weights(read(old_training.SUPPORT_MODEL, old_training.SUPPORT_MODEL_SHA),
        use, manifest, old_training.PARENT_SHA)
    timing = timing_learning.model_weights(read(TIMING_MODEL, TIMING_MODEL_SHA), use, manifest, old_training.PARENT_SHA)
    weights = {s.ARMS[0]: fixed | {s.timing.FEATURE: s.F()}, s.ARMS[1]: fixed | timing}
    prev, refs = train_records(previous, learned, approvals)
    historical_groups, historical_counts = old_training.prior.contrasts(historical)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in [*Path('tests').glob('test_harmony_fresh_train*.py'),
              Path('scripts/audit_harmony_fresh_train.py'), Path('scripts/validate_harmony_fresh_train.py')]:
        if p.exists(): code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'scopes').mkdir(); (output/'predictions').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        artifacts[str(p.resolve())] = io.digest(p)
        return str(p.resolve())
    save(output/'run-contract.json', {'version': VERSION, 'arms': s.ARMS,
        'coefficients': {a: {k: s.q(v) for k, v in w.items()} for a, w in weights.items()},
        'support_model_sha256': old_training.SUPPORT_MODEL_SHA, 'timing_model_sha256': TIMING_MODEL_SHA,
        'transition_budget': s.BUDGET, 'boundary_loss_weight': s.q(s.BOUNDARY_WEIGHT),
        'candidate_points_inserted': False, 'candidate_policy_changed': False,
        'ordinary_prediction_has_reference_argument': False, 'new_weight_fit': False,
        'dev_inference_or_evaluation': False, 'production_modified': False,
        'purpose': 'local_noncommercial_research', 'use_contract_sha256': content_hash(use),
        'code_pins': code, 'cohort': 'all_approved_Train_records_not_only_historical_updates'})
    summaries = []; contrasts = {}; sources = set(); counts = Counter(); errors = {a: Counter() for a in s.ARMS}
    for ref in refs:
        sample = ref['sample_id']; original = prev[sample]
        entry, graph, ev, clock, args = old_training.prior.prepare_context(original, ref, manifest, integration, read)
        if entry['manifest_entry_id'] not in approvals: raise ValueError('unapproved_train_scope')
        gate = clock.scope(ref['sample_span']); sources.add(ev.source.source_ir_content_sha256)
        bound_graph = graph_packet(graph)
        if content_hash(graph_packet(graph_from_packet(bound_graph))) != content_hash(bound_graph):
            raise ValueError('train_graph_codec_changed')
        ordinary = {}
        for arm, w in weights.items():
            begun = perf_counter()
            result = (s.direct_scorer(graph, ev, w, **args).decode(transition_budget=s.BUDGET)
                if gate['accepted'] and graph.status == 'ready' else
                {'status': 'source_clock_quarantined' if not gate['accepted'] else graph.status,
                 'selected': None, 'transitions': 0, 'exact_optimum_under_declared_score': False})
            ordinary[arm] = result | {'elapsed_seconds': perf_counter()-begun}
        # Seal ordinary label-blind choices BEFORE reference-compatible target search.
        raw_path = save(output/'predictions'/(sample+'.json.gz'), {
            'sample_id': sample, 'split': 'train', 'arms': ordinary,
            'source_labels_used_for_selection': False, 'target_search_not_started': True}, True)
        raw_sha = artifacts[raw_path]
        cells = tuple(old_training.prior.old.cells_from_record(ref))
        gold, ceiling = s.reachable_target(graph, cells)
        details = {}; scope_contrasts = []; historical_items = list(historical_groups.get(sample, {}).values())
        for arm, w in weights.items():
            result = ordinary[arm]
            evaluation = evaluate(native_reference(ref), native_prediction(result['selected'], ref['sample_span']),
                                  ref['sample_span'], selected=result['selected'] is not None)
            category = classify(gate, ceiling, result, evaluation); errors[arm][category] += 1
            details[arm] = {'ordinary': result, 'evaluation': evaluation, 'category': category, 'target': None}
            if not gate['accepted'] or not ceiling['reachable'] or result['selected'] is None: continue
            if evaluation['selected_hit']: continue  # Correct winner is not a hard negative.
            begun = perf_counter(); target = s.target_choice(gold, ev, w, **args)
            details[arm]['target'] = target | {'elapsed_seconds': perf_counter()-begun}
            if target['selected'] is None:
                counts['target_decoder_abstentions'] += 1; continue
            value = s.contrast(sample, entry, graph, ev, cells, result['selected'], target['selected'], w, **args)
            value['arms'] = [arm]
            value['exact_historical_negative_path_present'] = any(tuple(v['negative_ids']) == value['negative_ids'] for v in historical_items)
            value['exact_historical_contrast_present'] = any(tuple(v['negative_ids']) == value['negative_ids']
                and tuple(v['target_ids']) == value['target_ids'] for v in historical_items)
            nruns = s.timing.support.completed_runs(graph, value['negative_ids'])
            truns = s.timing.support.completed_runs(graph, value['target_ids'])
            old_runs = [(s.timing.support.completed_runs(graph, v['negative_ids']),
                         s.timing.support.completed_runs(graph, v['target_ids'])) for v in historical_items]
            value['historical_semantic_negative_present'] = any(n == nruns for n, _ in old_runs)
            value['historical_semantic_contrast_present'] = any(n == nruns and g == truns for n, g in old_runs)
            ident = value['contrast_id']; scope_contrasts.append(ident)
            if ident in contrasts:
                old = contrasts[ident]
                # Arm costs differ, but reusable base/feature/loss contracts must agree.
                for k in ('feature_delta', 'feature_available', 'loss_details', 'base_cost_gap'):
                    if old[k] != value[k]: raise ValueError('fresh_contrast_arm_inconsistency')
                old['arms'].append(arm)
            else: contrasts[ident] = value
            scorer = s.direct_scorer(graph, ev, w, **args)
            details[arm]['negative_source_receipt'] = s.path_receipt(scorer, value['negative_ids'])
            details[arm]['target_source_receipt'] = s.path_receipt(scorer, value['target_ids'], target=True)
        clock.check_source()
        if io.digest(raw_path) != raw_sha: raise ValueError('ordinary_prediction_changed_after_target_search')
        counts['original_edges'] += len(graph.edges); counts['scopes'] += 1
        counts['source_clock_accepted'] += gate['accepted']; counts['candidate_ceiling_reachable'] += ceiling['reachable'] is True
        row = {k: ref[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'plan_index', 'sample_span', 'split',
            'reference_cells', 'full_ir_content_sha256', 'candidate_inventory_content_sha256',
            'source_context_artifact', 'source_context_sha256', 'search_artifact', 'search_artifact_sha256')}
        row.update(source_clock_gate=gate, candidate_ceiling=ceiling, arms=details,
                   ordinary_prediction_path=raw_path, ordinary_prediction_sha256=raw_sha)
        case = {'record': row, 'entry': entry, 'problem': bound_graph, 'contrast_ids': sorted(set(scope_contrasts)),
            'source_ir_and_musicxml_referenced_by_SHA_bound_context': True,
            'full_source_not_clipped': True, 'human_validated': False, 'independent_test_case': False}
        row['scope_artifact'] = save(output/'scopes'/(sample+'.json.gz'), case, True)
        row['scope_sha256'] = artifacts[row['scope_artifact']]
        summaries.append(row)
        ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        save(output/'progress.json', {'complete': False, 'phase': 'fresh_approved_Train_winners_and_targets',
            'scopes': len(summaries), 'total': len(refs), 'elapsed_seconds': perf_counter()-tick})
        print(f'[fresh Train {len(summaries)}/{len(refs)}] {sample}: '+
              ', '.join(a+':'+v['category'] for a, v in details.items()), flush=True)
    values = list(contrasts.values()); counts['full_source_packages'] = len(sources)
    counts['unique_fresh_contrasts'] = len(values)
    counts['all_five_features_available'] = sum(all(r['feature_available'].values()) for r in values)
    counts['positive_loss_feature_collisions'] = sum(r['positive_loss_feature_collision'] for r in values)
    counts['new_negative_paths_vs_historical'] = sum(not r['exact_historical_negative_path_present'] for r in values)
    counts['new_contrasts_vs_historical'] = sum(not r['exact_historical_contrast_present'] for r in values)
    counts['new_semantic_negatives_vs_historical'] = sum(not r['historical_semantic_negative_present'] for r in values)
    counts['new_semantic_contrasts_vs_historical'] = sum(not r['historical_semantic_contrast_present'] for r in values)
    tables = {a: summarize([r | {'evaluation': r['arms'][a]['evaluation']} for r in summaries]) for a in s.ARMS}
    dataset = {'version': VERSION, 'rows': values, 'counts': dict(counts), 'new_weight_fit': False,
        'dev_labels_used': False, 'ordinary_winners_not_loss_augmented_adversaries': True,
        'pool_complete': False, 'historical_counts': historical_counts,
        'historical_unique_contrasts': sum(map(len, historical_groups.values()))}
    save(output/'training-contrasts.json.gz', dataset, True)
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('guard_changed:'+p)
    report = {'version': VERSION, 'complete': True, 'records': summaries, 'counts': dict(counts), 'tables': tables,
        'categories': {a: dict(v) for a, v in errors.items()},
        'candidate_ceiling_reasons': dict(Counter(r['candidate_ceiling']['reason'] for r in summaries)),
        'train_families': sorted({r['work_family_id'] for r in summaries}),
        'new_weight_fit': False, 'ordinary_prediction_source_labels_used': False,
        'training_reference_labels_used_for_target_and_diagnosis': True,
        'loaded_parent_containers_include_historical_Dev_records': True,
        'current_Dev_reconstruction_inference_evaluation_or_fit': False,
        'in_sample_diagnostic_not_generalization_accuracy': True, 'loss_augmented_search': False,
        'candidate_inventory_changed': False, 'production_modified': False,
        'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'elapsed_seconds': perf_counter()-tick}
    io.write(output/'report.json', report)
    return {k: v for k, v in report.items() if k not in ('records', 'input_hashes', 'code_hashes', 'artifact_hashes')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); print(json.dumps(run(a.output), ensure_ascii=False, indent=2), flush=True)
