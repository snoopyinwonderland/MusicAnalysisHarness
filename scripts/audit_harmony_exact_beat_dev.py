"""Source, winner, receipt and metric audit; no new Dev search or fitting."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_exact_beat_dev_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = {}; reads = set()
    for group in ('input_hashes', 'artifact_hashes', 'code_hashes'):
        for p, sha in report[group].items():
            if p in pins and pins[p] != sha: raise ValueError('beat_dev_audit_conflicting_pin')
            pins[p] = sha
    def check():
        for p, sha in pins.items():
            if t.io.digest(p) != sha: raise ValueError('beat_dev_audit_pin_changed:'+p)
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); sha = t.io.digest(p)
        if pins.get(name) != sha or expected is not None and expected != sha:
            raise ValueError('beat_dev_audit_unsealed_input:'+name)
        reads.add(name); return None if raw else t.load(p)
    check(); ctx, weights, originals = t.setup(read)
    freeze = read(root/'prediction-freeze.json', report['prediction_freeze_sha256'])
    previous = read(t.ROOT/'report.json', t.PINS['report.json'])
    reference = read(t.dev.SOURCE_ROOT/'report.json', t.dev.SOURCE_PINS['report.json'])
    old = {t.key(r): r for r in previous['records']}; refs = {t.key(r): r for r in reference['records']}
    old_cases = {t.key(r): r for r in previous['cases']}; cases = {t.key(r): r for r in report['cases']}
    cohort = {t.key(r): r for r in originals}
    flags = ('fit_performed', 'parameter_sweep', 'dev_checkpoint_selection', 'source_labels_used_for_selection',
             'reference_reachable_filter_applied', 'production_modified', 'operational_weights_changed', 'work_specific_rules',
             'independent_test', 'full_roman_or_local_key_or_nct_accuracy_measured')
    if (report['complete'] is not True or any(report[k] is not False for k in flags)
            or not all(t.same(contract[k], report[k]) for k in contract)
            or report['model_sha256'] != t.dev.MODEL_SHAS[t.ARM]
            or not t.same(report['coefficients'], {k: t.dev.s.q(v) for k, v in weights.items()})
            or freeze['current_reference_report_opened'] is not False or freeze['fit_performed'] is not False
            or freeze['complete'] is not True or freeze['model_sha256'] != report['model_sha256']
            or freeze['predictions'] != report['predictions'] or freeze['code_pins'] != report['code_hashes']
            or len(report['records']) != 72 or len(report['predictions']) != 72
            or report['cohort'] != [list(t.key(r)) for r in originals]
            or set(cases) != {k for k, r in cohort.items() if r['attempted']}
            or not (set(cohort) == set(old) == set(refs))):
        raise ValueError('beat_dev_audit_contract_or_inventory_changed')
    source_cache = {}; costs = transitions = preserved = edges = common = 0; rows = []
    for i, (row, pred) in enumerate(zip(report['records'], report['predictions']), 1):
        k = t.key(row); original = cohort[k]; raw = read(pred['artifact'], pred['sha256'])
        if t.key(pred) != k or t.key(raw) != k: raise ValueError('beat_dev_audit_prediction_order_changed')
        if (any(f in raw for f in ('reference_cells', 'candidate_ceiling')) or 'evaluation' in raw['cached']
                or any('evaluation' in a for a in raw['historical_arms'].values())):
            raise ValueError('beat_dev_audit_reference_in_prediction')
        for f in t.dev.FIELDS:
            if not (t.same(original[f], row[f]) and t.same(raw[f], row[f])):
                raise ValueError('beat_dev_audit_original_field_changed:'+f)
        if (row['historical_prediction_ref'] != original['historical_prediction_ref']
                or row['historical_prediction_sha256'] != original['historical_prediction_sha256']
                or raw['historical_arms'] != original['arms']
                or not t.same(row['historical_arms'], old[k]['arms'])
                or row['prediction_ref'] != pred['artifact'] or row['prediction_sha256'] != pred['sha256']
                or row['prediction_freeze_sha256'] != report['prediction_freeze_sha256']
                or not t.same(raw['cached'], {f: v for f, v in row['cached'].items() if f != 'evaluation'})):
            raise ValueError('beat_dev_audit_history_or_prediction_changed')
        for f in ('reference_cells', 'candidate_ceiling'):
            if not t.same(row[f], refs[k][f]): raise ValueError('beat_dev_audit_reference_changed')
        if row['attempted']:
            for f in ('graph_artifact', 'graph_sha256'):
                if original[f] != row[f] or row[f] != raw[f]: raise ValueError('beat_dev_audit_graph_changed')
            graph, src, ir, view, grace, clock = t.dev.prepare(row, read, source_cache); edges += len(graph.edges)
            if not (t.same(src, original['source']) and t.same(src, raw['source']) and t.same(src, row['source'])):
                raise ValueError('beat_dev_audit_source_changed')
            result = row['cached']['result']; selected = row['cached']['selected_prediction']; guard = result['resource_guard']
            diagnostics = result['exact_beat_cache_diagnostics']; identity = result['frozen_model_ref']
            if (not t.same(selected, result['selected']) or row['cached']['status'] != result['status']
                    or guard['wall_seconds'] != 20 or guard['transition_budget'] != 2_000_000
                    or guard['raw_segment_cap'] != 6 or graph.max_segments != 6
                    or guard['elapsed_seconds'] != row['cached']['elapsed_seconds']
                    or identity['model_sha256'] != report['model_sha256'] or identity['model_id'] != t.ARM
                    or identity['fit_performed_this_run'] is not False or identity['reference_labels_used_for_selection'] is not False
                    or result['frozen_dev_contract']['fit_performed_this_trial'] is not False
                    or result['exact_beat_cache_contract']['version'] != t.fresh.cache.VERSION
                    or 'joint_balance_contract' in result
                    or diagnostics['calls'] != diagnostics['hits']+diagnostics['integrations']
                    or diagnostics['entries'] != diagnostics['integrations']):
                raise ValueError('beat_dev_audit_selection_contract_changed')
            identical = t.fresh.train.refresh.parent.compatibility(original['arms'][t.ARM]['result'], result)
            if identical != row['same_completed_winner']: raise ValueError('beat_dev_audit_common_changed')
            common += identical
            if selected is None:
                if (result['exact_optimum_under_declared_score'] is not False or result.get('partial_winner_returned', False)
                        or result['status'] not in ('context_wall_budget_abstention', 'transition_budget_abstention')):
                    raise ValueError('beat_dev_audit_abstention_changed')
            elif (selected['source_labels_used_for_selection'] is not False or selected['human_validated'] is not False
                    or selected['confidence'] is not None or result['exact_optimum_under_declared_score'] is not True):
                raise ValueError('beat_dev_audit_winner_not_exact')
            case = read(cases[k]['artifact'], cases[k]['sha256'])
            historical_case = read(case['previous_case_ref'], case['previous_case_sha256'])
            if (case['previous_case_ref'] != old_cases[k]['case_path'] or not t.same(case['record'], row)
                    or not t.same(case['source'], src) or case['human_validated'] is not False
                    or case['reference_witness_never_used_for_inference'] is not True):
                raise ValueError('beat_dev_audit_case_binding_changed')
            receipts, count, original_count = t.replay(graph, ir, view, grace, clock, row, historical_case, weights)
            if (not t.same(receipts, case['receipts']) or count != case['scalar_and_role_transitions']
                    or original_count != case['historical_receipts_preserved']):
                raise ValueError('beat_dev_audit_receipt_changed')
            costs += len(receipts); transitions += count; preserved += original_count
        elif (row['cached'] != original['arms'][t.ARM] | {'evaluation': row['cached']['evaluation']}
              or row['same_completed_winner'] is not False):
            raise ValueError('beat_dev_audit_original_abstention_retried')
        for value in (*row['historical_arms'].values(), row['cached']):
            selected = value['selected_prediction']
            evaluation = t.dev.evaluate(t.dev.native_reference(row), t.dev.native_prediction(selected, row['sample_span']),
                                       row['sample_span'], selected=selected is not None)
            if evaluation != value['evaluation']: raise ValueError('beat_dev_audit_evaluation_changed')
        rows.append(row)
        if i % 10 == 0 or i == 72: print(f'[beat Dev audit {i}/72]', flush=True)
    if (not t.same(t.metrics(rows), report['tables']) or edges != report['original_edges']
            or len(source_cache) != report['full_source_packages'] or costs != report['path_witnesses']
            or transitions != report['scalar_and_role_transitions'] or preserved != report['historical_receipts_preserved']
            or report['all_original_cases_preserved'] != len(old_cases)
            or report['train_families'] != sorted({r['work_family_id'] for r in ctx['rows']})
            or report['dev_families'] != sorted({r['work_family_id'] for r in rows})
            or report['distinct_ranges'] != len({(r['pair_id'], t.dev.previous.prior.content_hash(r['sample_span']))
                                               for r in rows if r['attempted']})):
        raise ValueError('beat_dev_audit_total_changed')
    check(); outcome = dict(passed=True, version=t.VERSION, report_sha256=t.io.digest(root/'report.json'),
        model_sha256=report['model_sha256'], unique_pins=len(pins), sealed_inputs_reloaded=len(reads),
        original_records=len(rows), source_scopes=len(cases), source_packages=len(source_cache),
        original_edges=edges, detailed_receipts=costs, historical_receipts_preserved=preserved,
        scalar_and_role_transitions=transitions, same_completed_winners=common,
        original_input_abstentions=sum(not r['attempted'] for r in rows), new_decoder_search=0, fit_performed=False)
    t.io.write(dest, outcome); return outcome


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
