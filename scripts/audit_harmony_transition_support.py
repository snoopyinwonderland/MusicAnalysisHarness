"""Rebuild Train profiles, all stored paths/costs and counts; no fit/search."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_transition_support_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); contract = t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['code_hashes'] | report['artifact_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('transition_support_audit_sha_changed:'+p)
    check()
    flags = ('fit_performed', 'fresh_search_performed', 'dev_inference_or_evaluation', 'production_modified',
             'weights_changed', 'independent_test_accuracy_measured', 'new_prediction_or_accuracy_improvement_claimed')
    if report['complete'] is not True or any(report.get(k) is not False for k in flags):
        raise ValueError('transition_support_audit_contract_changed')
    if (contract['source_profile_reads_reference_labels'] is not False or contract['no_hard_support_gate'] is not True
            or contract['original_abstentions_not_retried'] is not True):
        raise ValueError('transition_support_audit_scope_policy_changed')
    reads = set()
    def read(p, expected=None, compressed=False, raw=False):
        p = str(Path(p).resolve()); h = t.io.digest(p)
        if pins.get(p) != h or expected is not None and expected != h:
            raise ValueError('transition_support_audit_unsealed_input:'+p)
        reads.add(p); return None if raw else t.load(p)
    ctx = t.context(read)
    if (contract['coefficients'] != {k: t.s.q(v) for k, v in ctx['weights'].items()}
            or contract['cohort'] != [r['sample_id'] for r in ctx['rows']]
            or [r['sample_id'] for r in report['records']] != contract['cohort']):
        raise ValueError('transition_support_audit_inventory_changed')
    packets = []; paths = transitions = costs = abstentions = edges = 0; sources = set()
    for i, (row, saved) in enumerate(zip(ctx['rows'], report['records']), 1):
        packet = read(saved['artifact'], saved['sha256']); rebuilt = t.build_sample(ctx, row, read)
        if not t.seals.same_json(packet, rebuilt): raise ValueError('transition_support_audit_replay_changed:'+row['sample_id'])
        packets.append(rebuilt); edges += rebuilt['original_edge_count']; sources.add(rebuilt['source_ir_content_sha256'])
        for arm in rebuilt['arms'].values():
            if not arm['selected']: abstentions += 1; continue
            paths += 1; costs += 1; transitions += len(arm['source_profile']['transitions'])
            if (arm['source_profile']['source_labels_used'] is not False or arm['source_profile']['score_changed'] is not False
                    or arm['source_profile']['source_modified'] is not False):
                raise ValueError('transition_support_audit_source_blindness_changed')
        print(f'[transition support audit {i}/{len(ctx["rows"])}]', flush=True)
    if not t.seals.same_json(t.summarize(packets), report['summary']): raise ValueError('transition_support_audit_summary_changed')
    if (edges != report['original_edges'] or len(sources) != report['full_source_packages']
            or len(packets) != report['scopes']): raise ValueError('transition_support_audit_coverage_changed')
    check()
    result = {'passed': True, 'version': t.VERSION, 'report_sha256': t.io.digest(root/'report.json'),
        'run_contract_sha256': t.io.digest(root/'run-contract.json'),
        'audit_code_sha256': t.io.digest(Path(__file__)), 'sha_checks': len(pins), 'sealed_inputs_reloaded': len(reads),
        'replayed_scopes': len(packets), 'source_packages': len(sources), 'original_edges': edges,
        'stored_paths_and_costs_replayed': paths, 'source_transition_profiles_replayed': transitions,
        'preserved_abstentions': abstentions, 'new_fit_or_search': False, 'dev_used': False,
        'summary_replayed': True, 'source_core_and_old_score_unchanged': True}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    a = p.parse_args(); print(json.dumps(run(a.root), indent=2), flush=True)
