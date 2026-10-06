"""Rebuild sealed original-source receipts; do not rerun search or fitting."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_context_joint_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report, contract = t.load(root/'report.json'), t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    def check():
        for p, sha in pins.items():
            if t.io.digest(p) != sha: raise ValueError('joint_audit_sha_changed:'+p)
    check()
    if (report['complete'] is not True or report['fit_performed'] is not False
            or report['dev_inference_or_evaluation'] is not False or report['operational_weights_changed'] is not False
            or report['production_modified'] is not False or report['new_prediction_selection_reads_labels'] is not False
            or report['signed_stress_coefficients'] != contract['signed_stress_coefficients']):
        raise ValueError('joint_audit_scope_changed')
    reads = set()
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); sha = t.io.digest(p)
        if pins.get(name) != sha or expected is not None and sha != expected:
            raise ValueError('joint_audit_unsealed_input:'+name)
        reads.add(name); return None if raw else t.load(p)
    ctx = t.context(read)
    if contract['stress_cohort'] != ctx['stress_ids'] or contract['cohort'] != [r['sample_id'] for r in ctx['rows']]:
        raise ValueError('joint_audit_inventory_changed')
    paths = transitions = figures = fresh = edges = scopes = 0; sources = set()
    for i, (row, saved) in enumerate(zip(ctx['rows'], report['records']), 1):
        packet = read(saved['artifact'], saved['sha256']); rebuilt = t.build_sample(ctx, row, read, search=False)
        a = {k: v for k, v in packet.items() if k not in ('fresh_predictions', 'fresh_search_elapsed_seconds')}
        b = {k: v for k, v in rebuilt.items() if k not in ('fresh_predictions', 'fresh_search_elapsed_seconds')}
        if not t.prior.prior.seals.same_json(a, b): raise ValueError('joint_audit_replay_changed:'+row['sample_id'])
        _, _, graph, ev, clock, args = t.prepare_sample(ctx, row, read)
        original = t.s.Scorer(graph, ev, ctx['weights'], **args)
        zero = t.joint.Scorer(original, t.joint.ZERO, **args); stress = t.joint.Scorer(original, t.STRESS, context=zero.context)
        predictions = packet['fresh_predictions']
        expected = {'zero_delegate', 'zero_delayed', 'signed_stress_delayed'} if row['sample_id'] in ctx['stress_ids'] else {'zero_delegate'}
        if set(predictions) != expected: raise ValueError('joint_audit_prediction_inventory_changed')
        for arm, result in predictions.items():
            selected = result['selected']
            if selected is None:
                if arm != 'signed_stress_delayed' or result['status'] != 'transition_budget_abstention':
                    raise ValueError('joint_audit_unexpected_abstention')
                continue
            ids = t.s.fresh.path_ids(selected); sc = stress if arm == 'signed_stress_delayed' else zero
            receipt = sc.path_receipt(ids)
            if (not t.prior.prior.seals.same_json(receipt, selected['context_score'])
                    or selected['score_cost'] != receipt['cost'] or selected['source_labels_used_for_selection'] is not False
                    or result['exact_optimum_under_declared_score'] is not True):
                raise ValueError('joint_audit_prediction_cost_changed')
            fresh += 1
        clock.check_source(); edges += len(graph.edges); scopes += 1; sources.add(ev.source.source_ir_content_sha256)
        for arm in rebuilt['arms'].values():
            if arm['selected']:
                paths += 1; ts = arm['stress_receipt']['context']['transitions']; transitions += len(ts)
                figures += sum(len(p['conditional_figures']) for p in ts)
        ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        print(f'[delayed context audit {i}/{len(ctx["rows"])}]', flush=True)
    if (scopes != report['scopes'] or paths != report['stored_paths_replayed'] or edges != report['original_edges']
            or transitions != report['transitions_replayed'] or figures != report['conditional_figures_replayed']
            or len(sources) != report['full_source_packages']): raise ValueError('joint_audit_counts_changed')
    check()
    result = {'passed': True, 'version': t.VERSION, 'report_sha256': t.io.digest(root/'report.json'),
        'run_contract_sha256': t.io.digest(root/'run-contract.json'), 'audit_code_sha256': t.io.digest(Path(__file__)),
        'sha_checks': len(pins), 'sealed_inputs_reloaded': len(reads), 'replayed_scopes': scopes,
        'source_packages': len(sources), 'original_edges': edges, 'stored_path_costs_and_profiles_replayed': paths,
        'transitions_replayed': transitions, 'conditional_figures_replayed': figures,
        'fresh_prediction_cost_receipts_replayed': fresh, 'new_search_fit_or_dev': False,
        'original_core_and_operational_model_unchanged': True}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
