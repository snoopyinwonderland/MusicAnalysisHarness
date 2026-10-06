"""Independent detailed cost/source/scalar replay, no new search or fit."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_context_scalar_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('scalar_audit_sha_changed:'+p)
    check(); reads = set()
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); h = t.io.digest(p)
        if pins.get(name) != h or expected is not None and h != expected:
            raise ValueError('scalar_audit_unsealed_input:'+name)
        reads.add(name); return None if raw else t.load(p)
    ctx = t.context(read)
    if (report['complete'] is not True or report['fit_performed'] is not False
            or report['production_modified'] is not False or report['operational_weights_changed'] is not False
            or report['source_labels_used_for_prediction'] is not False or report['current_dev_reconstructed_or_used'] is not False
            or report['model_sha256'] != t.PINS['model.json.gz']
            or contract['cohort'] != [r['sample_id'] for r in ctx['rows']] or len(report['records']) != len(ctx['rows'])):
        raise ValueError('scalar_audit_contract_changed')
    records = []; costs = transitions = edges = 0; sources = set()
    for i, (row, record) in enumerate(zip(ctx['rows'], report['records']), 1):
        packet = read(record['artifact'], record['sha256'])
        previous = ctx['stage80_records'][row['sample_id']]
        old_packet = read(previous['artifact'], previous['sha256'])
        saved, entry, graph, ev, clock, args = t.prior.prior.prepare_sample(ctx, row, read)
        sc = t.scalar.Scorer(t.s.Scorer(graph, ev, ctx['weights'], **args), ctx['context_weights'], **args)
        for k in ('sample_id', 'entry', 'original_graph_sha256', 'original_scope_sha256', 'full_source_paths',
                  'original_edge_count', 'source_ir_content_sha256', 'source_provenance'):
            if not t.prior.prior.prior.prior.seals.same_json(packet[k], saved[k]):
                raise ValueError('scalar_audit_source_changed:'+k)
        result = packet['result']; selected = result['selected']; ids = t.s.fresh.path_ids(selected) if selected else None
        same = t.compatibility(old_packet['result'], result)
        if same != record['same_completed_winner']: raise ValueError('scalar_audit_compatibility_changed')
        guard = result['resource_guard']
        if (guard['wall_seconds'] != t.prior.WALL_SECONDS or guard['transition_budget'] != t.s.fresh.BUDGET
                or guard['raw_segment_cap'] != graph.max_segments or guard['lazy_scalar_index_construction_included'] is not True
                or result['frozen_model_ref']['model_sha256'] != t.PINS['model.json.gz']):
            raise ValueError('scalar_audit_model_or_resource_changed')
        for name, path in (('fresh', ids), ('prior_selected', previous['selected_ids']), ('original_baseline', previous['baseline_ids'])):
            if path is None: continue
            receipt = sc.path_receipt(path); transitions += t.verify_projection(sc, path, receipt); costs += 1
            if not t.prior.prior.prior.prior.seals.same_json(receipt, packet['post_search_cost_receipts'][name]):
                raise ValueError('scalar_audit_detailed_cost_changed')
            if name == 'fresh' and (selected['score_cost'] != receipt['cost']
                    or not t.prior.prior.prior.prior.seals.same_json(receipt, selected['context_score'])
                    or result['exact_optimum_under_declared_score'] is not True):
                raise ValueError('scalar_audit_winner_changed')
        if selected is None and (result['exact_optimum_under_declared_score'] is not False
                or result['status'] not in ('context_wall_budget_abstention', 'transition_budget_abstention')):
            raise ValueError('scalar_audit_invalid_abstention')
        ref = ctx['refs'][row['sample_id']]
        evaluation = t.prior.evaluate(t.prior.native_reference(ref), t.prior.native_prediction(selected, ref['sample_span']),
                                      ref['sample_span'], selected=selected is not None)
        if evaluation != packet['evaluation'] or evaluation != record['evaluation']:
            raise ValueError('scalar_audit_metric_changed')
        rebuilt = {k: row[k] for k in ('sample_id', 'pair_id', 'work_family_id', 'sample_span', 'split')} | {
            'artifact': record['artifact'], 'sha256': record['sha256'], 'status': result['status'], 'evaluation': evaluation,
            'prior_evaluation': previous['evaluation'], 'original_baseline_evaluation': previous['baseline_evaluation'],
            'selected_ids': ids, 'prior_selected_ids': previous['selected_ids'], 'original_baseline_ids': previous['baseline_ids'],
            'same_completed_winner': same, 'elapsed_seconds': guard['elapsed_seconds'],
            'historical_elapsed_seconds': old_packet['result']['resource_guard']['elapsed_seconds']}
        if not t.prior.prior.prior.prior.seals.same_json(rebuilt, record): raise ValueError('scalar_audit_record_changed')
        records.append(rebuilt); edges += len(graph.edges); sources.add(ev.source.source_ir_content_sha256)
        clock.check_source(); ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        print(f'[scalar audit {i}/{len(ctx["rows"])}]', flush=True)
    if (edges != report['original_edges'] or len(sources) != report['full_source_packages']
            or transitions != report['scalar_detailed_transitions_compared']
            or not t.prior.prior.prior.prior.seals.same_json(t.summaries(records), report['tables'])):
        raise ValueError('scalar_audit_aggregate_changed')
    check()
    result = {'passed': True, 'version': t.VERSION, 'report_sha256': t.io.digest(root/'report.json'),
        'run_contract_sha256': t.io.digest(root/'run-contract.json'), 'audit_code_sha256': t.io.digest(Path(__file__)),
        'model_sha256': t.PINS['model.json.gz'], 'sha_checks': len(pins), 'sealed_inputs_reloaded': len(reads),
        'source_scopes_replayed': len(records), 'source_packages': len(sources), 'original_edges': edges,
        'independent_detailed_path_costs_replayed': costs, 'scalar_detailed_transitions_replayed': transitions,
        'new_search_fit_or_dev': False, 'original_core_and_operational_weights_unchanged': True}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
