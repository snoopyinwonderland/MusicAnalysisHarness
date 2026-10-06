"""Inspect all reachable Train scopes with a FROZEN model; do not fit.

Generate exact loss-augmented competitors before integrating margin updates.
Every ordinary/target/adversary cost is measured under the SAME fixed weights.
This diagnoses training margins, not improved accuracy or a Dev evaluation.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_online_score_trial as online
from . import harmony_full_score_adversary as adversary

s, parent, io, load = online.s, online.parent, online.io, online.load
VERSION = 'harmony-full-score-adversary-trial-0.1.0'
ROOT = 'output/harmony-online-score-2026-10-05-r1'
PINS = {
    ROOT+'/report.json': '2c442cc37756e26958d550da90c238ecef8fb6792a00cfd9274edf40d75860d1',
    ROOT+'/model.json.gz': '029e2de31ab6e5d9e5fa65eb229c63fe649cce10ddd987dbab4c2b7f3f06f331',
    ROOT+'/post-seal-audit.json': '6da04003ca3a48617058e8dc3ced1e5975fdc9e5a449a530495d22567f30421f'}


def contrast(sc, target_sc, ordinary, negative, target, loss):
    if any(r['selected'] is None for r in (ordinary, negative, target)):
        return {'resource_abstention': True, 'ordinary_status': ordinary['status'],
                'adversary_status': negative['status'], 'target_status': target['status']}
    value = online.comparison(sc, target_sc, negative, target, loss)
    value.pop('ordinary_source_labels_used')
    value.update(negative_kind='exact_loss_augmented_train_path',
        source_labels_used_for_negative_selection=True, analysis_export_allowed=False)
    ordinary_loss = online.prior.path_loss(sc.problem, ordinary, loss)
    target_cost, negative_cost = s.f(value['target_cost']), s.f(value['negative_cost'])
    violation = s.f(value['loss'])-(negative_cost-target_cost)
    if (negative['training_loss'] != value['loss_details']
            or s.f(negative['augmented_cost']) != negative_cost-s.f(value['loss'])
            or s.f(negative['augmented_cost']) > sc.score_path(s.fresh.path_ids(ordinary['selected']))-s.f(ordinary_loss['total'])
            or violation < 0):
        raise ValueError('adversary_not_complete_loss_augmented_optimum')
    gradient = {k: s.f(value['feature_delta'][k]) if value['feature_available'][k] and k in s.TRAINABLE else F()
                for k in s.FEATURES}
    norm = sum((v*v for v in gradient.values()), F())
    return value | {'ordinary_ids': s.fresh.path_ids(ordinary['selected']),
        'ordinary_loss': ordinary_loss, 'ordinary_cost': ordinary['selected']['score_cost'],
        'margin_violation': s.q(violation), 'known_trainable_norm_squared': s.q(norm),
        'ordinary_correct_positive_margin': s.f(ordinary_loss['total']) == 0 and violation > 0,
        'positive_margin_known_feature_collision': violation > 0 and norm == 0,
        'adversary_differs_from_ordinary': value['negative_ids'] != s.fresh.path_ids(ordinary['selected']),
        'gradient_eligible': violation > 0 and norm > 0, 'weight_update_performed': False}


def prepare(sample, old, ref, before, manifest, integration, read):
    packet = read(old['scope_artifact'], old['scope_sha256'])
    entry, graph, ev, clock, args = parent.old_training.prior.prepare_context(before[sample], ref, manifest, integration, read)
    if (entry != packet['entry'] or not clock.scope(ref['sample_span'])['accepted']
            or online.content_hash(parent.graph_packet(graph)) != online.content_hash(packet['problem'])):
        raise ValueError('adversary_original_train_scope_changed')
    cells = tuple(parent.old_training.prior.old.cells_from_record(ref))
    gold, ceiling = s.fresh.reachable_target(graph, cells)
    if ceiling != old['candidate_ceiling'] or not ceiling['reachable']:
        raise ValueError('adversary_train_ceiling_changed')
    return packet, entry, graph, gold, ev, clock, args, online.prior.training_loss(graph, cells, s.fresh.BOUNDARY_WEIGHT)


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    begun = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if expected is not None and h != expected: raise ValueError('adversary_input_sha_mismatch:'+name)
        if name in inputs and inputs[name] != h: raise ValueError('adversary_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    old_report, model, audit = [read(p, h) for p, h in PINS.items()]
    if not old_report['complete'] or not audit['passed'] or audit['report_sha256'] != PINS[ROOT+'/report.json']:
        raise ValueError('unsealed_adversary_parent')
    for p, h in (old_report['input_hashes'] | old_report['code_hashes'] | old_report['artifact_hashes']).items(): read(p, h, raw=True)
    original = read(online.prior.ROOT+'/report.json', online.prior.PINS[online.prior.ROOT+'/report.json'])
    previous, recall, integration, use, historical, learned = [read(p, h) for p, h in parent.old_training.PINS.items()]
    manifest = recall['package_manifest']; approvals = online.validate_use_contract(use, manifest, parent.old_training.PARENT_SHA)
    for row in approvals.values():
        for name in ('local_license', 'readme'):
            lic = row['source_license']; read(lic[name+'_path'], lic[name+'_sha256'], raw=True)
    fixed = parent.old_training.old_learning.model_weights(read(parent.old_training.SUPPORT_MODEL, parent.old_training.SUPPORT_MODEL_SHA),
        use, manifest, parent.old_training.PARENT_SHA)
    timing = parent.timing_learning.model_weights(read(parent.TIMING_MODEL, parent.TIMING_MODEL_SHA), use, manifest, parent.old_training.PARENT_SHA)
    initial = s.initial_weights(fixed | timing)
    weights = online.learning.model_weights(model, initial, use, manifest, parent.old_training.PARENT_SHA)
    before, refs = parent.train_records(previous, learned, approvals); refs = {r['sample_id']: r for r in refs}
    rows = online.cohort(original['records']); old_rows = {r['sample_id']: r for r in old_report['records']}
    if [r['sample_id'] for r in rows] != list(old_rows): raise ValueError('adversary_parent_cohort_changed')
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in [*Path('tests').glob('test_harmony_full_score_adversary*.py'),
              Path('scripts/audit_harmony_full_score_adversary.py'), Path('scripts/validate_harmony_full_score_adversary.py')]:
        code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'scopes').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        name = str(p.resolve()); artifacts[name] = io.digest(p); return name, artifacts[name]
    save(output/'run-contract.json', {'version': VERSION, 'code_pins': code,
        'cohort': [r['sample_id'] for r in rows], 'frozen_model_sha256': PINS[ROOT+'/model.json.gz'],
        'weights': {k: s.q(v) for k, v in weights.items()}, 'fit_performed': False,
        'negative_search': 'exact_run_aware_loss_augmented_train_only',
        'time_loss_weight': s.q(F(1)), 'boundary_loss_weight': s.q(s.fresh.BOUNDARY_WEIGHT),
        'max_raw_edges': 6, 'transition_budget': s.fresh.BUDGET,
        'adversary_operation_unit': 'feasible_state_raw_edge_comparison',
        'ordinary_batched_operation_unit_is_different': True,
        'dev_inference_or_evaluation': False, 'purpose': 'local_noncommercial_research',
        'use_contract_sha256': online.content_hash(use), 'production_modified': False})
    records = []; sources = set(); edge_count = 0
    for old in rows:
        tick = perf_counter(); sample = old['sample_id']; ref = refs[sample]
        packet, entry, graph, gold, ev, clock, args, loss = prepare(sample, old, ref, before, manifest, integration, read)
        if entry['manifest_entry_id'] not in approvals: raise ValueError('unapproved_adversary_training_entry')
        sources.add(ev.source.source_ir_content_sha256); edge_count += len(graph.edges)
        sc, ts = s.Scorer(graph, ev, weights, **args), s.Scorer(gold, ev, weights, **args)
        ordinary = sc.decode(); target = ts.decode(); negative = adversary.decode(sc, loss)
        if target['selected'] is not None:
            target['selected'].update(source_labels_used_for_selection=True, training_reference_labels_used=True, target_only=True)
        old_postfit = read(old_rows[sample]['postfit_artifact'], old_rows[sample]['postfit_sha256'])
        old_selected = old_postfit['result']['selected']
        if ((ordinary['selected'] is None) != (old_selected is None) or
                ordinary['selected'] is not None and (s.fresh.path_ids(ordinary['selected']) != s.fresh.path_ids(old_selected)
                    or ordinary['selected']['score_cost'] != old_selected['score_cost'])):
            raise ValueError('frozen_ordinary_path_or_cost_changed')
        value = contrast(sc, ts, ordinary, negative, target, loss)
        receipts = {name: sc.receipt(s.fresh.path_ids(result['selected']), target=name != 'ordinary')
                    for name, result in (('ordinary', ordinary), ('adversary', negative), ('target', target)) if result['selected'] is not None}
        path, h = save(output/'scopes'/(sample+'.json.gz'), {
            'sample_id': sample, 'sample_span': ref['sample_span'], 'entry': entry,
            'source_ir_content_sha256': ev.source.source_ir_content_sha256,
            'original_scope_artifact': old['scope_artifact'], 'original_scope_sha256': old['scope_sha256'],
            'ordinary': ordinary, 'adversary': negative, 'target': target, 'contrast': value,
            'path_receipts': receipts, 'frozen_model_sha256': PINS[ROOT+'/model.json.gz'],
            'elapsed_seconds': perf_counter()-tick, 'full_source_not_clipped': True,
            'original_full_musicxml_ir_context_inherited': True, 'human_validated': False,
            'independent_test_case': False}, True)
        records.append({k: ref[k] for k in ('sample_id', 'pair_id', 'split', 'work_family_id', 'sample_span')} | {
            'scope_artifact': path, 'scope_sha256': h, 'original_scope_artifact': old['scope_artifact'],
            'original_scope_sha256': old['scope_sha256'], 'contrast': value,
            'evaluation': old_rows[sample]['evaluation'],
            'search_status': negative['status'], 'adversary_transitions': negative['transitions']})
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        save(output/'progress.json', {'complete': False, 'scopes': len(records), 'total_scopes': len(rows), 'elapsed_seconds': perf_counter()-begun})
        print(f'[Train adversary {len(records)}/{len(rows)}] {sample}: {negative["status"]}; eligible={value.get("gradient_eligible")}', flush=True)
    ready = [r['contrast'] for r in records if not r['contrast']['resource_abstention']]
    counts = {'parent_train_scopes': len(original['records']), 'reachable_train_scopes': len(records),
        'excluded_unreachable_or_ineligible_scopes': len(original['records'])-len(records),
        'full_source_packages': len(sources), 'work_families': len({r['work_family_id'] for r in records}),
        'original_edges': edge_count, 'ordinary_correct_scopes': sum(r['evaluation']['selected_hit'] is True for r in records),
        'complete_contrasts': len(ready), 'search_statuses': dict(Counter(r['search_status'] for r in records)),
        'positive_margin': sum(s.f(v['margin_violation']) > 0 for v in ready),
        'ordinary_correct_positive_margin': sum(v['ordinary_correct_positive_margin'] for v in ready),
        'positive_margin_known_feature_collisions': sum(v['positive_margin_known_feature_collision'] for v in ready),
        'gradient_eligible': sum(v['gradient_eligible'] for v in ready),
        'adversary_differs_from_ordinary': sum(v['adversary_differs_from_ordinary'] for v in ready),
        'positive_adversary_loss': sum(s.f(v['loss']) > 0 for v in ready), 'weights_changed': 0}
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('adversary_guard_changed:'+p)
    final = {'version': VERSION, 'complete': True, 'records': records, 'counts': counts,
        'unchanged_ordinary_train_metrics': online.summarize(records),
        'frozen_model_sha256': PINS[ROOT+'/model.json.gz'], 'fit_performed': False,
        'elapsed_seconds': perf_counter()-begun, 'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'dev_inference_or_evaluation': False, 'dev_used_for_fit': False,
        'loaded_parent_containers_include_exposed_Dev': True, 'accuracy_improvement_claimed': False,
        'training_adversaries_are_not_analysis_predictions': True,
        'production_modified': False, 'candidate_policy_changed': False}
    io.write(output/'report.json', final)
    return {k: v for k, v in final.items() if k not in ('records', 'input_hashes', 'code_hashes', 'artifact_hashes')}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); print(json.dumps(run(a.output), ensure_ascii=False, indent=2), flush=True)
