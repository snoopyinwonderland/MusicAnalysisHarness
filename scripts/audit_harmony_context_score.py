"""Source/cost/metric replay and deterministic calibration arithmetic audit.

No new decoder search, Dev evaluation, operational promotion or extra model.
"""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_context_score_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('context_score_audit_sha_changed:'+p)
    check()
    if (report['complete'] is not True or report['fit_performed'] is not True
            or report['current_dev_reconstructed_or_used'] is not False
            or report['operational_weights_changed'] is not False or report['production_modified'] is not False
            or report['source_labels_used_for_prediction'] is not False
            or report['configuration'] != t.learning.configuration()):
        raise ValueError('context_score_audit_scope_changed')
    reads = set()
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); h = t.io.digest(p)
        if pins.get(name) != h or expected is not None and h != expected:
            raise ValueError('context_score_audit_unsealed_input:'+name)
        reads.add(name); return None if raw else t.load(p)
    ctx = t.context(read)
    rows, counts = t.contrasts(ctx); vectors = read(root/'training-vectors.json.gz')
    if not t.prior.prior.prior.seals.same_json(vectors, {'rows': rows, 'counts': counts}):
        raise ValueError('context_score_audit_training_vectors_changed')
    model = read(root/'model.json.gz'); freeze = read(root/'model-freeze.json')
    if (freeze['model_sha256'] != report['model_sha256'] or t.io.digest(root/'model.json.gz') != report['model_sha256']
            or freeze['postfit_selection_started'] is not False
            or freeze['existing_26_weights'] != {k: t.s.q(v) for k, v in ctx['weights'].items()}):
        raise ValueError('context_score_audit_model_freeze_changed')
    replay = t.learning.fit(rows, ctx['weights'], ctx['use'], ctx['manifest'], ctx['parent_sha'], t.PINS['report.json'])
    if model != replay: raise ValueError('context_score_audit_calibration_arithmetic_changed')
    weights = t.learning.model_weights(model, ctx['weights'], ctx['use'], ctx['manifest'], ctx['parent_sha'], t.PINS['report.json'])
    if contract['cohort'] != [r['sample_id'] for r in ctx['rows']] or len(report['records']) != len(ctx['rows']):
        raise ValueError('context_score_audit_cohort_changed')
    rebuilt_rows = []; costs = scopes = edges = 0; sources = set()
    for i, (row, record) in enumerate(zip(ctx['rows'], report['records']), 1):
        p = read(record['artifact'], record['sha256'])
        saved, entry, graph, ev, clock, args = t.prior.prepare_sample(ctx, row, read)
        sc = t.joint.Scorer(t.s.Scorer(graph, ev, ctx['weights'], **args), weights, **args)
        for k in ('sample_id', 'entry', 'source_ir_content_sha256', 'original_scope_artifact',
                  'original_scope_sha256', 'original_graph_sha256', 'original_edge_count', 'full_source_paths', 'source_provenance'):
            if not t.prior.prior.prior.seals.same_json(p[k], saved[k]): raise ValueError('context_score_audit_source_changed:'+k)
        result = p['result']; selected = result['selected']; ref = ctx['refs'][row['sample_id']]
        if result['learned_context_model']['model_id'] != model['model_id']:
            raise ValueError('context_score_audit_model_ref_changed')
        if (result['resource_guard']['wall_seconds'] != t.WALL_SECONDS
                or result['resource_guard']['transition_budget'] != t.s.fresh.BUDGET
                or result['resource_guard']['raw_segment_cap'] != graph.max_segments):
            raise ValueError('context_score_audit_limits_changed')
        if selected is not None:
            ids = t.s.fresh.path_ids(selected); receipt = sc.path_receipt(ids)
            if (not t.prior.prior.prior.seals.same_json(receipt, selected['context_score'])
                    or selected['score_cost'] != receipt['cost']
                    or selected['source_labels_used_for_selection'] is not False
                    or result['exact_optimum_under_declared_score'] is not True):
                raise ValueError('context_score_audit_fresh_cost_changed')
            costs += 1
        else:
            ids = None
            if result['status'] not in ('context_wall_budget_abstention', 'transition_budget_abstention'):
                raise ValueError('context_score_audit_unexpected_abstention')
            if result['exact_optimum_under_declared_score'] is not False:
                raise ValueError('context_score_audit_abstention_claims_optimum')
        baseline = ctx['joint_packets'][row['sample_id']]['fresh_predictions']['zero_delegate']
        b_ids = t.s.fresh.path_ids(baseline['selected'])
        cells = tuple(t.prior.prior.prior.parent.parent.old_training.prior.old.cells_from_record(ref))
        loss = t.training_loss(graph, cells, t.s.fresh.BOUNDARY_WEIGHT)
        for arm, path in (('baseline', b_ids), ('stored_target', saved['arms']['epoch3_target']['path_ids'])):
            receipt = sc.path_receipt(path, target=arm == 'stored_target')
            receipt['post_prediction_training_loss'] = t.path_loss(graph,
                {'selected': {'segments': [{'semantic_group_ref': x} for x in path]}}, loss)
            if not t.prior.prior.prior.seals.same_json(receipt, p['diagnostic_receipts'][arm]):
                raise ValueError('context_score_audit_diagnostic_receipt_changed')
            costs += 1
        evaluation = t.evaluate(t.native_reference(ref), t.native_prediction(selected, ref['sample_span']),
            ref['sample_span'], selected=selected is not None)
        base_eval = t.evaluate(t.native_reference(ref), t.native_prediction(baseline['selected'], ref['sample_span']),
            ref['sample_span'], selected=True)
        if evaluation != p['evaluation'] or base_eval != p['baseline_evaluation']:
            raise ValueError('context_score_audit_metric_changed')
        rebuilt = {k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {
            'artifact': record['artifact'], 'sha256': record['sha256'], 'status': result['status'],
            'evaluation': evaluation, 'baseline_evaluation': base_eval, 'selected_ids': ids, 'baseline_ids': b_ids}
        if not t.prior.prior.prior.seals.same_json(rebuilt, record): raise ValueError('context_score_audit_record_changed')
        rebuilt_rows.append(rebuilt); clock.check_source(); sources.add(ev.source.source_ir_content_sha256)
        scopes += 1; edges += len(graph.edges)
        ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        print(f'[context score audit {i}/{len(ctx["rows"])}]', flush=True)
    if (scopes != report['fresh_ordinary_attempts'] or edges != report['original_edges']
            or len(sources) != report['full_source_packages'] or counts != report['calibration_counts']
            or not t.prior.prior.prior.seals.same_json(t.compare(rebuilt_rows), report['tables'])):
        raise ValueError('context_score_audit_aggregate_changed')
    check()
    result = {'passed': True, 'version': t.VERSION, 'report_sha256': t.io.digest(root/'report.json'),
        'run_contract_sha256': t.io.digest(root/'run-contract.json'), 'model_sha256': report['model_sha256'],
        'audit_code_sha256': t.io.digest(Path(__file__)), 'sha_checks': len(pins), 'sealed_inputs_reloaded': len(reads),
        'training_vectors_replayed': len(rows), 'deterministic_calibration_arithmetic_replayed': True,
        'fresh_scope_source_and_metrics_replayed': scopes, 'source_packages': len(sources), 'original_edges': edges,
        'independent_path_costs_replayed': costs, 'new_decoder_search_or_dev': False,
        'additional_model_saved': False, 'original_core_and_operational_weights_unchanged': True}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
