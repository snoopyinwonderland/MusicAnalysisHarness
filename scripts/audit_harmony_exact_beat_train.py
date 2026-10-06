"""Independent full-source receipt/metric replay of the frozen cached trial.

No search or fit. A saved winner is a witness, never decoded here.
"""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_exact_beat_train_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = {}; reads = set()
    for group in ('input_hashes', 'artifact_hashes', 'code_hashes'):
        for p, sha in report[group].items():
            if p in pins and pins[p] != sha: raise ValueError('beat_train_audit_conflicting_pin')
            pins[p] = sha
    def check():
        for p, sha in pins.items():
            if t.io.digest(p) != sha: raise ValueError('beat_train_audit_pin_changed:'+p)
    def read(p, expected=None, compressed=False, raw=False):
        key = str(Path(p).resolve()); sha = t.io.digest(p)
        if pins.get(key) != sha or expected is not None and expected != sha:
            raise ValueError('beat_train_audit_unsealed_input:'+key)
        reads.add(key); return None if raw else t.load(p)
    check(); ctx = t.context(read); model = ctx['beat_model']; weights = ctx['beat_weights']
    freeze = read(root/'prediction-freeze.json', report['prediction_freeze_sha256'])
    if (report['complete'] is not True or not all(t.train.same_json(contract[k], report[k]) for k in contract)
            or report['cohort'] != [r['sample_id'] for r in ctx['rows']]
            or freeze['cohort'] != report['cohort'] or freeze['predictions'] != report['predictions']
            or freeze['reference_evaluation_started'] is not False or freeze['complete'] is not True
            or freeze['model_sha256'] != report['model_sha256'] or freeze['code_pins'] != report['code_hashes']
            or any(report[k] is not False for k in ('fit_performed', 'reference_conditioned_prediction',
                'current_dev_inference', 'production_modified', 'operational_weights_changed', 'independent_accuracy_claimed'))
            or len(report['records']) != len(ctx['rows']) or len(report['predictions']) != len(ctx['rows'])):
        raise ValueError('beat_train_audit_contract_changed')
    records = []; sources = set(); edges = costs = projections = historical = common = 0
    for i, (row, rec, pred) in enumerate(zip(ctx['rows'], report['records'], report['predictions']), 1):
        packet = read(rec['artifact'], rec['sha256']); prediction = read(pred['artifact'], pred['sha256'])
        previous = ctx['beat_previous'][row['sample_id']]; original = read(previous['artifact'], previous['sha256'])
        saved, entry, graph, ev, clock, args = t.prepare(ctx, row, read)
        t.assert_source(saved, packet); t.assert_source(saved, prediction)
        if (prediction['reference_evaluation_performed'] is not False or not t.train.same_json(prediction['result'], packet['result'])
                or packet['prediction_ref'] != pred['artifact'] or packet['prediction_sha256'] != pred['sha256']
                or packet['prediction_freeze_sha256'] != report['prediction_freeze_sha256']
                or packet['historical_case_ref'] != previous['artifact'] or packet['historical_case_sha256'] != previous['sha256']
                or pred['sample_id'] != row['sample_id']): raise ValueError('beat_train_audit_prediction_changed')
        result = packet['result']; guard = result['resource_guard']; selected = result['selected']
        identity = result['frozen_model_ref']; cache = result['exact_beat_cache_diagnostics']
        if (identity['model_id'] != model['model_id'] or identity['model_sha256'] != report['model_sha256']
                or identity['fit_performed_this_selection'] is not False or identity['source_labels_used_for_selection'] is not False
                or guard['wall_seconds'] != 20 or guard['transition_budget'] != 2_000_000
                or guard['raw_segment_cap'] != 6 or graph.max_segments != 6 or 'joint_balance_contract' in result
                or result['exact_beat_cache_contract']['version'] != t.cache.VERSION
                or cache['calls'] != cache['hits']+cache['integrations'] or cache['entries'] != cache['integrations']):
            raise ValueError('beat_train_audit_selection_contract_changed')
        same = t.train.refresh.parent.compatibility(original['result'], result); common += same
        if same != packet['same_completed_winner']: raise ValueError('beat_train_audit_common_changed')
        if selected is None:
            if (result['exact_optimum_under_declared_score'] is not False
                    or result['status'] not in ('context_wall_budget_abstention', 'transition_budget_abstention')
                    or result.get('partial_winner_returned', False)):
                raise ValueError('beat_train_audit_abstention_changed')
        elif (result['exact_optimum_under_declared_score'] is not True
                or selected['source_labels_used_for_selection'] is not False):
            raise ValueError('beat_train_audit_winner_not_exact')
        old = t.train.prior.prior.Scorer(graph, ev, weights, **args); new = t.cache.Scorer(graph, ev, weights, **args)
        receipts, count = t.replay(old, new, original, result)
        if not t.train.same_json(receipts, packet['post_search_cost_receipts']) or count != packet['scalar_and_role_transitions']:
            raise ValueError('beat_train_audit_detailed_cost_changed')
        evaluation = t.train.evaluate(selected, ctx['refs'][row['sample_id']])
        if (evaluation != packet['evaluation']
                or not t.train.same_json(t.record(row, packet, rec['artifact'], rec['sha256'], previous), rec)):
            raise ValueError('beat_train_audit_record_or_metric_changed')
        records.append(rec); sources.add(saved['source_ir_content_sha256']); edges += len(graph.edges)
        costs += len(receipts); projections += count; historical += len(original['post_search_cost_receipts'])
        t.train.refresh.clear(ev, clock)
        if i % 10 == 0 or i == len(ctx['rows']): print(f'[beat Train audit {i}/{len(ctx["rows"])}]', flush=True)
    if (not t.train.same_json(t.summaries(records), report['tables']) or len(sources) != report['full_source_packages']
            or edges != report['original_edges'] or costs != report['path_witnesses']
            or projections != report['scalar_and_role_transitions'] or historical != report['archived_witnesses_preserved']
            or report['excluded_parent_scopes_preserved'] != ctx['protection_report']['excluded_parent_scopes_preserved']):
        raise ValueError('beat_train_audit_total_changed')
    check(); outcome = dict(passed=True, version=t.VERSION, report_sha256=t.io.digest(root/'report.json'),
        model_sha256=report['model_sha256'], unique_pins=len(pins), sealed_inputs_reloaded=len(reads),
        source_scopes_replayed=len(records), source_packages=len(sources), original_edges=edges,
        detailed_receipts_replayed=costs, historical_receipts_preserved=historical,
        scalar_and_role_transitions_replayed=projections, same_completed_winners=common,
        new_decoder_search=0, fit_performed=False, original_and_operational_artifacts_unchanged=True)
    t.io.write(dest, outcome); return outcome


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
