"""Independent source/detailed receipts, fit arithmetic and metrics; no search."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_member_role_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists():
        raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h:
                raise ValueError('member_role_audit_seal_changed:'+p)
    check(); reads = set()
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); h = t.io.digest(p)
        if pins.get(name) != h or (expected is not None and h != expected):
            raise ValueError('member_role_audit_unsealed_input:'+name)
        reads.add(name); return None if raw else t.load(p)
    ctx = t.context(read)
    if (report['complete'] is not True or report['fit_performed'] is not True
            or report['configuration'] != t.learning.configuration()
            or contract['configuration'] != t.learning.configuration()
            or report['source_labels_used_for_prediction'] is not False
            or report['current_dev_reconstructed_or_used'] is not False
            or report['operational_weights_changed'] is not False or report['production_modified'] is not False
            or contract['cohort'] != [r['sample_id'] for r in ctx['rows']]):
        raise ValueError('member_role_audit_contract_changed')
    rows, counts, proofs, projections = t.collect(ctx, read)
    vectors = read(root/'training-vectors.json.gz')
    if not t.same_json(rows, vectors['rows']) or counts != vectors['counts'] or len(proofs) != len(vectors['proofs']):
        raise ValueError('member_role_audit_vectors_changed')
    for proof, saved in zip(proofs, vectors['proofs']):
        if not t.same_json(proof, read(saved['artifact'], saved['sha256'])):
            raise ValueError('member_role_audit_source_vectors_changed')
    model, freeze = read(root/'model.json.gz'), read(root/'model-freeze.json')
    replay = t.learning.fit(rows, ctx['weights'], ctx['frozen7'], ctx['use'], ctx['manifest'], ctx['parent_sha'], t.PINS['training-vectors.json.gz'])
    if model != replay:
        raise ValueError('member_role_audit_fit_arithmetic_changed')
    weights = t.learning.model_weights(model, ctx['weights'], ctx['frozen7'], ctx['use'], ctx['manifest'], ctx['parent_sha'], t.PINS['training-vectors.json.gz'])
    if (freeze['model_sha256'] != report['model_sha256'] or t.io.digest(root/'model.json.gz') != report['model_sha256']
            or freeze['postfit_selection_started'] is not False or freeze['dev_used'] is not False
            or freeze['old26_and_old7_frozen'] is not True):
        raise ValueError('member_role_audit_freeze_changed')
    records = []; sources = set(); edges = costs = 0
    if len(report['records']) != len(ctx['rows']):
        raise ValueError('member_role_audit_scope_missing')
    for i, (row, record) in enumerate(zip(ctx['rows'], report['records']), 1):
        packet = read(record['artifact'], record['sha256'])
        saved, entry, graph, ev, clock, args = t.prior.old.prior.prepare_sample(ctx, row, read)
        if not all(t.same_json(packet[k], saved[k]) for k in t.prior.SOURCE_FIELDS):
            raise ValueError('member_role_audit_source_changed')
        sc = t.make_scorer(ctx, graph, ev, args, weights); result = packet['result']; selected = result['selected']
        ids = t.s.fresh.path_ids(selected) if selected else None
        previous = ctx['role_parent_records'][row['sample_id']]; baseline = ctx['stage80_records'][row['sample_id']]
        if (result['frozen_model_ref']['model_id'] != model['model_id']
                or result['frozen_model_ref']['model_sha256'] != report['model_sha256']
                or result['frozen_model_ref']['source_labels_used_for_selection'] is not False
                or result['resource_guard']['wall_seconds'] != t.prior.old.WALL_SECONDS
                or result['resource_guard']['transition_budget'] != t.s.fresh.BUDGET
                or result['resource_guard']['raw_segment_cap'] != graph.max_segments):
            raise ValueError('member_role_audit_model_or_resource_changed')
        chains = {'fresh': ids, 'previous_context': previous['selected_ids'], 'frozen_old26': baseline['baseline_ids'],
            'stored_target': ctx['joint_packets'][row['sample_id']]['arms']['epoch3_target']['path_ids']}
        for name, path in chains.items():
            if path is None:
                continue
            receipt = sc.path_receipt(path, target=name == 'stored_target'); costs += 1
            projections += t.verify_projection(sc, path, receipt)
            if not t.same_json(receipt, packet['post_search_cost_receipts'][name]):
                raise ValueError('member_role_audit_independent_cost_changed')
            if name == 'fresh' and (not t.same_json(receipt, selected['context_score'])
                    or selected['score_cost'] != receipt['cost'] or result['exact_optimum_under_declared_score'] is not True
                    or selected['source_labels_used_for_selection'] is not False):
                raise ValueError('member_role_audit_winner_changed')
        if selected is None and (result['exact_optimum_under_declared_score'] is not False
                or result['status'] not in ('context_wall_budget_abstention', 'transition_budget_abstention')):
            raise ValueError('member_role_audit_invalid_abstention')
        ref = ctx['refs'][row['sample_id']]
        evaluation = t.prior.old.evaluate(t.prior.old.native_reference(ref), t.prior.old.native_prediction(selected, ref['sample_span']), ref['sample_span'], selected=selected is not None)
        rebuilt = {k: row[k] for k in t.prior.FIELDS} | {'artifact': record['artifact'], 'sha256': record['sha256'],
            'status': result['status'], 'selected_ids': ids, 'previous_ids': previous['selected_ids'],
            'baseline_ids': baseline['baseline_ids'], 'evaluation': evaluation,
            'previous_evaluation': previous['evaluation'], 'baseline_evaluation': baseline['baseline_evaluation'],
            'elapsed_seconds': result['resource_guard']['elapsed_seconds']}
        if evaluation != packet['evaluation'] or not t.same_json(rebuilt, record):
            raise ValueError('member_role_audit_metrics_changed')
        records.append(rebuilt); sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges); t.prior.clear(ev, clock)
        print(f'[member-role audit {i}/{len(ctx["rows"])}]', flush=True)
    if (not t.same_json(t.prior.comparisons(records), report['tables']) or counts != report['vector_counts']
            or len(sources) != report['full_source_packages'] or edges != report['original_edges']
            or projections != report['scalar_detailed_transitions_compared']):
        raise ValueError('member_role_audit_aggregate_changed')
    check()
    result = {'passed': True, 'version': t.VERSION, 'report_sha256': t.io.digest(root/'report.json'),
        'model_sha256': report['model_sha256'], 'audit_code_sha256': t.io.digest(Path(__file__)),
        'sha_checks': len(pins), 'sealed_inputs_reloaded': len(reads), 'training_vectors_replayed': len(rows),
        'source_vector_packets_replayed': len(proofs), 'fit_arithmetic_replayed_no_additional_model_saved': True,
        'new_decoder_search_or_dev': False, 'source_scopes_replayed': len(records), 'source_packages': len(sources),
        'original_edges': edges, 'independent_detailed_path_costs_replayed': costs,
        'scalar_detailed_transitions_replayed': projections,
        'original_core_operational_weights_and_old_artifacts_unchanged': True}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
