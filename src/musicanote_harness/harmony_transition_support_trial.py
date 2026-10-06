"""Train-only source diagnosis of stored paths; NO fit or fresh path search."""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from . import harmony_adversarial_score_trial as parent
from . import harmony_adversarial_score_dev_trial as seals
from . import harmony_transition_support as observation
from .harmony_margin_learning import training_loss, path_loss

s, io, load = parent.s, parent.io, parent.load
VERSION = 'harmony-transition-support-train-diagnostic-0.1.0'
ROOT, PINS = seals.MODEL_ROOT, seals.MODEL_PINS
ARMS = ('initial', 'ordinary_frozen', 'adversarial_frozen', 'epoch3_adversary', 'epoch3_target')


def context(read):
    original, ordinary, integration, use, manifest, initial, before, refs, rows = parent.context(read)
    report, model, freeze, audit = [read(Path(ROOT)/p, h) for p, h in PINS.items()]
    seals.check_model_seal(report, audit, freeze, PINS['model.json.gz'])
    for p, h in (report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']).items(): read(p, h, raw=True)
    weights = parent.learning.model_weights(model, initial, use, manifest, parent.parent.old_training.PARENT_SHA)
    if ([r['sample_id'] for r in rows] != [r['sample_id'] for r in report['records']]
            or any(r['split'] != 'train' for r in rows)):
        raise ValueError('transition_support_train_inventory_changed')
    return {'original': original, 'ordinary': {r['sample_id']: r for r in ordinary['records']},
        'fitted': {r['sample_id']: r for r in report['records']}, 'weights': weights,
        'integration': integration, 'manifest': manifest, 'before': before, 'refs': refs, 'rows': rows}


def diagnose_reference(profile, boundaries):
    """Separate AFTER source extraction. Exact reference positions, not NCT gold."""
    return [{'boundary': t['boundary'], 'reference_boundary_at_exact_time': s.f(t['boundary']) in boundaries}
            for t in profile['transitions']]


def build_sample(ctx, row, read):
    sample = row['sample_id']; ref = ctx['refs'][sample]
    packet = read(row['scope_artifact'], row['scope_sha256'])
    entry, graph, ev, clock, args = parent.parent.old_training.prior.prepare_context(
        ctx['before'][sample], ref, ctx['manifest'], ctx['integration'], read)
    if (not clock.scope(ref['sample_span'])['accepted'] or not seals.same_json(entry, packet['entry'])
            or not seals.same_json(parent.parent.graph_packet(graph), packet['problem'])):
        raise ValueError('transition_support_original_clock_graph_changed')
    old, new = ctx['ordinary'][sample], ctx['fitted'][sample]
    op = read(old['postfit_artifact'], old['postfit_sha256'])
    np = read(new['postfit_artifact'], new['postfit_sha256'])
    vp = Path(ROOT)/'visits'/('3-'+sample+'.json.gz')
    visit = read(vp)
    if (visit['sample_id'] != sample or visit['epoch'] != 3
            or visit['source_ir_content_sha256'] != ev.source.source_ir_content_sha256
            or not seals.same_json(visit['entry'], entry)):
        raise ValueError('transition_support_visit_changed')
    results = {'initial': packet['record']['arms']['timing_calibrated']['ordinary'],
        'ordinary_frozen': op['result'], 'adversarial_frozen': np['result'],
        'epoch3_adversary': visit['adversary'], 'epoch3_target': visit['target']}
    scorer = s.Scorer(graph, ev, ctx['weights'], **args)
    arms = {}
    # Source-only profiles are computed BEFORE per-path reference diagnostics.
    for arm, result in results.items():
        selected = result.get('selected')
        if selected is None:
            arms[arm] = {'status': result['status'], 'selected': False, 'retried': False}; continue
        ids = s.fresh.path_ids(selected)
        profile = observation.observe_path(graph, ev, ids)
        receipt = scorer.receipt(ids, target=arm == 'epoch3_target')
        for k in observation.PAIR_WEIGHTS:
            observed_sum = sum((s.f(t['credited_resolution_features'][k]) for t in profile['transitions']), F())
            if observed_sum != s.f(receipt['observed_feature_sums'][k]):
                raise ValueError('transition_support_pair_credit_not_exact_existing_score')
        arms[arm] = {'status': result['status'], 'selected': True, 'path_ids': ids,
            'source_profile': profile, 'same_frozen_weights_receipt': receipt,
            'path_selection_model': 'epoch3_last_visit_not_averaged' if arm.startswith('epoch3') else arm,
            'training_labels_used_for_original_path_selection': arm.startswith('epoch3'),
            'analysis_export_allowed': False}
    cells = tuple(parent.parent.old_training.prior.old.cells_from_record(ref))
    loss = training_loss(graph, cells, s.fresh.BOUNDARY_WEIGHT)
    for arm, r in arms.items():
        if not r['selected']: continue
        r['reference_diagnostic'] = diagnose_reference(r['source_profile'], loss.boundaries)
        r['training_loss'] = path_loss(graph, results[arm], loss)
        if arm == 'epoch3_target' and s.f(r['training_loss']['total']) != 0:
            raise ValueError('transition_support_stored_target_not_reference_compatible')
    a, b = arms['ordinary_frozen'], arms['adversarial_frozen']
    delta = {k: s.q(s.f(b['same_frozen_weights_receipt']['term_costs'][k])
                     -s.f(a['same_frozen_weights_receipt']['term_costs'][k])) for k in s.FEATURES}
    changed = a['path_ids'] != b['path_ids']
    clock.check_source()
    # Keep the original whole MusicXML/IR and context artifact references. No
    # clipping, reparsing or invention of excerpt IDs is necessary to replay.
    original_binding = read(ctx['before'][sample]['search_artifact'], ctx['before'][sample]['search_artifact_sha256'])['provenance']
    revision = read(original_binding['measure_revision_sidecar'])
    snap = revision['verification_payload']['parent_snapshot']
    working = next(r for r in ctx['integration']['measure_revisions'] if r['pair_id'] == row['pair_id'])
    source_paths = {'whole_musicxml_path': snap['source_xml'], 'whole_musicxml_sha256': entry['score_sha256'],
        'parent_ir_path': snap['parent_ir'], 'parent_ir_sha256': snap['parent_ir_sha256'],
        'working_ir_path': working['candidate_ir'] if working['candidate_created'] else snap['parent_ir']}
    source_paths['working_ir_sha256'] = io.digest(source_paths['working_ir_path'])
    result = {k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')}
    result.update(entry=entry, source_provenance=original_binding,
        source_ir_content_sha256=ev.source.source_ir_content_sha256,
        full_source_paths=source_paths, source_clock_gate=clock.scope(ref['sample_span']),
        original_scope_artifact=row['scope_artifact'], original_scope_sha256=row['scope_sha256'],
        original_graph_sha256=parent.online.content_hash(packet['problem']), original_edge_count=len(graph.edges),
        epoch3_visit_artifact=str(vp.resolve()), epoch3_visit_sha256=io.digest(vp),
        arms=arms, stored_path_changed=changed,
        new_minus_previous_term_costs_under_same_frozen_weights=delta,
        reference_boundaries=[s.q(t) for t in sorted(loss.boundaries)],
        full_source_not_clipped=True, human_validated=False, independent_test_case=False)
    ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
    return result


def summarize(packets):
    summary = {a: Counter() for a in ARMS}; changes = Counter()
    for packet in packets:
        changes['scopes'] += 1; changes['stored_paths_changed'] += packet['stored_path_changed']
        a, b = packet['arms']['ordinary_frozen'], packet['arms']['adversarial_frozen']
        change = s.f(b['training_loss']['normalized_time_error'])-s.f(a['training_loss']['normalized_time_error'])
        changes['time_error_increased' if change > 0 else 'time_error_decreased' if change < 0 else 'time_error_equal'] += 1
        for arm, path in packet['arms'].items():
            c = summary[arm]; c['scopes'] += 1
            if not path['selected']: c['preserved_resource_abstentions'] += 1; continue
            c['selected_paths'] += 1
            c['zero_training_loss'] += s.f(path['training_loss']['total']) == 0
            for transition, reference in zip(path['source_profile']['transitions'], path['reference_diagnostic']):
                match = reference['reference_boundary_at_exact_time']; kind = 'reference_time' if match else 'extra_time'
                c['transitions'] += 1; c[kind] += 1
                raw = transition['credited_resolution_features']
                credited = any(s.f(raw[k]) > 0 for k in ('dominant_family_leading_tone', 'dominant_family_seventh_step'))
                c['dominant_credited'] += credited; c[kind+':dominant_credited'] += credited
                for name, w in (('first_beat', transition['right_first_beat']), ('complete_run', transition['right_complete_run'])):
                    prefix = kind+':'+name+':'
                    if w is None or w['right_union_member_count'] is None:
                        c[prefix+'unavailable'] += 1; continue
                    c[prefix+'available'] += 1
                    thin = w['right_union_member_count'] < 2
                    no_exclusive = w['right_union_exclusive_count'] == 0
                    dispersed = w['right_union_member_count'] >= 2 and s.f(w['coverage']['right_two']) == 0
                    left_more = s.f(w['coverage']['left_two']) > s.f(w['coverage']['right_two'])
                    for label, flag in (('union_lt_two', thin), ('no_exclusive_member', no_exclusive),
                                        ('distributed_without_vertical_two', dispersed), ('left_support_longer', left_more)):
                        c[prefix+label] += flag
                        c[prefix+'credited:'+label] += credited and flag
                c['held_common_at_boundary'] += bool(transition['held_common_event_ids'])
    return {'by_arm': {k: dict(v) for k, v in summary.items()}, 'stored_path_comparison': dict(changes),
        'denominator': 'scope_boundary_occurrences_overlap_contexts_not_unique_notes_or_works',
        'reference_time_match_does_not_confirm_selected_chord': True,
        'evidence_flags_are_diagnostics_not_harmony_or_nct_gold': True}


def run(output):
    output = Path(output)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs, artifacts = {}, {}
    def read(p, expected=None, compressed=False, raw=False):
        p = Path(p); h = io.digest(p); name = str(p.resolve())
        if (expected is not None and h != expected) or (name in inputs and inputs[name] != h):
            raise ValueError('transition_support_input_changed:'+name)
        inputs[name] = h; return None if raw else load(p)
    ctx = context(read)
    code = {str(p.resolve()): io.digest(p) for p in Path(__file__).parent.glob('*.py')}
    for p in (Path('tests/test_harmony_transition_support.py'), Path('tests/test_harmony_transition_support_trial.py'),
              Path('scripts/validate_harmony_transition_support.py'), Path('scripts/audit_harmony_transition_support.py')):
        code[str(p.resolve())] = io.digest(p)
    output.mkdir(parents=True); (output/'cases').mkdir()
    def save(p, value, compressed=False):
        (io.write_packet if compressed else io.write)(p, value)
        path = str(p.resolve()); artifacts[path] = io.digest(p); return path, artifacts[path]
    contract = {'version': VERSION, 'cohort': [r['sample_id'] for r in ctx['rows']], 'arms': ARMS,
        'coefficients': {k: s.q(v) for k, v in ctx['weights'].items()}, 'model_sha256': PINS['model.json.gz'],
        'code_pins': code, 'fit_performed': False, 'fresh_search_performed': False,
        'dev_inference_or_evaluation': False, 'stored_target_and_adversary_train_only': True,
        'source_profile_reads_reference_labels': False, 'same_frozen_weights_for_all_cost_receipts': True,
        'no_hard_support_gate': True, 'original_abstentions_not_retried': True,
        'purpose': 'local_noncommercial_research', 'production_modified': False}
    save(output/'run-contract.json', contract)
    rows = []; packets = []; sources = set(); families = set(); edges = 0
    for i, row in enumerate(ctx['rows'], 1):
        packet = build_sample(ctx, row, read); packets.append(packet)
        sources.add(packet['source_ir_content_sha256']); families.add(row['work_family_id']); edges += packet['original_edge_count']
        p, h = save(output/'cases'/(row['sample_id']+'.json.gz'), packet, True)
        rows.append({k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {'artifact': p, 'sha256': h})
        print(f'[Train transition support {i}/{len(ctx["rows"])}] {row["sample_id"]}', flush=True)
    for p, h in (inputs | code | artifacts).items():
        if io.digest(p) != h: raise ValueError('transition_support_final_guard_changed:'+p)
    report = contract | {'complete': True, 'records': rows, 'summary': summarize(packets),
        'parent_train_scopes': len(ctx['original']['records']), 'scopes': len(rows),
        'excluded_scopes_preserved': len(ctx['original']['records'])-len(rows),
        'full_source_packages': len(sources), 'work_families': len(families), 'original_edges': edges,
        'elapsed_seconds': perf_counter()-tick, 'input_hashes': inputs, 'code_hashes': code, 'artifact_hashes': artifacts,
        'loaded_historical_parent_containers_include_exposed_Dev': True,
        'current_Dev_reconstructed_or_used_for_diagnostic': False, 'weights_changed': False,
        'independent_test_accuracy_measured': False, 'new_prediction_or_accuracy_improvement_claimed': False,
        'training_targets_are_not_analysis_predictions': True}
    io.write(output/'report.json', report); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    a = p.parse_args(); r = run(a.output)
    print(json.dumps({k: r[k] for k in ('complete', 'scopes', 'full_source_packages', 'work_families', 'original_edges', 'summary', 'elapsed_seconds')}, indent=2), flush=True)
