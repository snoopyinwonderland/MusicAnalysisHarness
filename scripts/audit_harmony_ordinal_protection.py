"""Replay guarded fit arithmetic and every full-source cost, without search."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_ordinal_protection_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']; reads = set()
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('ordinal_audit_seal_changed:'+p)
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); h = t.io.digest(p)
        if pins.get(name) != h or (expected is not None and h != expected):
            raise ValueError('ordinal_audit_unsealed_input:'+name)
        reads.add(name); return None if raw else t.load(p)
    check(); ctx = t.context(read); rows, competitors = ctx['active_pool'], ctx['competitors']
    if (report['complete'] is not True or report['configuration'] != t.learning.configuration()
            or not all(t.same_json(contract[k], report[k]) for k in contract)
            or report['cohort'] != [r['sample_id'] for r in ctx['rows']]
            or any(report[k] is not False for k in ('source_labels_used_for_prediction',
                'current_dev_reconstructed_or_used', 'production_modified', 'operational_weights_changed',
                'independent_accuracy_claimed'))):
        raise ValueError('ordinal_audit_contract_changed')
    vectors = read(root/'training-vectors.json.gz'); model = read(root/'model.json.gz')
    if not t.same_json(rows, vectors['rows']) or competitors != vectors['competitors']:
        raise ValueError('ordinal_audit_vectors_changed')
    replay = t.learning.fit(rows, competitors, ctx['initial35'], ctx['use'], ctx['manifest'],
                            ctx['parent_sha'], t.PINS['training-vectors.json.gz'])
    if replay != model: raise ValueError('ordinal_audit_fit_arithmetic_changed')
    weights = t.learning.model_weights(model, rows, competitors, ctx['initial35'], ctx['use'], ctx['manifest'],
                                       ctx['parent_sha'], t.PINS['training-vectors.json.gz'])
    freeze = read(root/'model-freeze.json')
    if (freeze['model_sha256'] != report['model_sha256'] or t.io.digest(root/'model.json.gz') != report['model_sha256']
            or freeze['postfit_selection_started'] is not False or freeze['dev_used'] is not False
            or freeze['all_35_weights_frozen_during_selection'] is not True):
        raise ValueError('ordinal_audit_freeze_changed')
    if len(report['records']) != len(ctx['rows']): raise ValueError('ordinal_audit_missing_scope')
    records = []; sources = set(); edges = costs = projections = 0
    for i, (row, record) in enumerate(zip(ctx['rows'], report['records']), 1):
        packet = read(record['artifact'], record['sha256']); sample = row['sample_id']
        saved, entry, graph, ev, clock, args = t.prior.prior.prior.prior.old.prior.prepare_sample(ctx, row, read)
        if not all(t.same_json(packet[k], saved[k]) for k in t.refresh.SOURCE_FIELDS):
            raise ValueError('ordinal_audit_original_source_changed')
        sc = t.prior.prior.Scorer(graph, ev, weights, **args); result = packet['result']; selected = result['selected']
        ids = t.s.fresh.path_ids(selected) if selected else None; guard = result['resource_guard']
        if (result['frozen_model_ref']['model_id'] != model['model_id']
                or result['frozen_model_ref']['model_sha256'] != report['model_sha256']
                or result['frozen_model_ref']['source_labels_used_for_selection'] is not False
                or 'joint_balance_contract' in result or result['ordinal_protection_contract']['version'] != t.VERSION
                or guard['wall_seconds'] != t.prior.WALL_SECONDS or guard['transition_budget'] != t.s.fresh.BUDGET
                or guard['raw_segment_cap'] != graph.max_segments):
            raise ValueError('ordinal_audit_selection_contract_changed')
        expected_chains = t.chains(ctx, sample, ids)
        if set(packet['post_search_cost_receipts']) != {k for k, v in expected_chains.items() if v is not None}:
            raise ValueError('ordinal_audit_receipt_set_changed')
        for name, path in expected_chains.items():
            if path is None: continue
            receipt = sc.path_receipt(path, target=name == 'stored_target'); costs += 1
            projections += t.prior.prior.prior.verify_projection(sc, path, receipt); t.ledger.flatten(receipt, weights)
            if not t.same_json(receipt, packet['post_search_cost_receipts'][name]):
                raise ValueError('ordinal_audit_detailed_cost_changed')
            if name == 'fresh' and (not t.same_json(receipt, selected['context_score'])
                    or selected['score_cost'] != receipt['cost'] or result['exact_optimum_under_declared_score'] is not True
                    or selected['source_labels_used_for_selection'] is not False):
                raise ValueError('ordinal_audit_winner_changed')
        if selected is None and (result['exact_optimum_under_declared_score'] is not False
                or result['status'] not in ('context_wall_budget_abstention', 'transition_budget_abstention')):
            raise ValueError('ordinal_audit_abstention_changed')
        evaluation = t.evaluate(selected, ctx['refs'][sample])
        if evaluation != packet['evaluation'] or not t.same_json(t.record(row, packet, record['artifact'], record['sha256'], ctx), record):
            raise ValueError('ordinal_audit_evaluation_changed')
        records.append(record); sources.add(ev.source.source_ir_content_sha256); edges += len(graph.edges)
        t.refresh.clear(ev, clock)
        print(f'[ordinal audit {i}/{len(ctx["rows"])}]', flush=True)
    if (not t.same_json(t.summarize(records, ctx), report['tables']) or len(sources) != report['full_source_packages']
            or edges != report['original_edges'] or projections != report['scalar_detailed_transitions_compared']
            or report['excluded_parent_scopes_preserved'] != ctx['protection_report']['excluded_parent_scopes_preserved']):
        raise ValueError('ordinal_audit_aggregate_changed')
    check(); outcome = dict(passed=True, version=t.VERSION, report_sha256=t.io.digest(root/'report.json'),
        model_sha256=report['model_sha256'], sha_checks=len(pins), sealed_inputs_reloaded=len(reads),
        training_vectors_replayed=len(rows), fit_arithmetic_replayed_no_additional_model_saved=True,
        protected_competitors=len(competitors), protection_floors=model['after']['protection_floors'],
        protection_floor_violations=model['after']['protection_floor_violations'],
        new_decoder_search_or_dev=False, source_scopes_replayed=len(records), source_packages=len(sources),
        original_edges=edges, independent_detailed_costs_replayed=costs,
        scalar_detailed_transitions_replayed=projections,
        original_core_operational_weights_and_old_artifacts_unchanged=True)
    t.io.write(dest, outcome); return outcome


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
