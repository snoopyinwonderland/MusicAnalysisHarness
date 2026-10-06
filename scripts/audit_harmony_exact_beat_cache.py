"""Pin and inventory audit; no new fitting/search or reference-conditioned choice."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_exact_beat_replay as t


def run(root, profile_root):
    root, profile_root = Path(root), Path(profile_root)
    output = root/'post-seal-audit.json'
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); profile = t.load(profile_root/'report.json')
    if (report['complete'] is not True or report['new_search'] is not False
            or report['fit_performed'] is not False or report['production_modified'] is not False
            or report['profile_report_sha256'] != t.io.digest(profile_root/'report.json')
            or profile['complete'] is not True or profile['accuracy_evaluated'] is not False):
        raise ValueError('cache_audit_contract_changed')
    pins = {}
    for packet in (report, profile):
        for group in ('input_hashes', 'artifact_hashes', 'code_hashes'):
            for p, sha in packet[group].items():
                if p in pins and pins[p] != sha: raise ValueError('cache_audit_conflicting_pin:'+p)
                if t.io.digest(p) != sha: raise ValueError('cache_audit_pin_changed:'+p)
                pins[p] = sha
    paths = transitions = edges = 0; sources = set()
    for record in report['records']:
        p = t.load(record['artifact']); old = t.load(p['historical_case_ref'])
        if t.io.digest(p['historical_case_ref']) != p['historical_case_sha256']:
            raise ValueError('cache_audit_historical_case_changed')
        if p['fresh_prediction_created'] is not False or p['all_receipts_values_masks_pair_details_and_costs_exact'] is not True:
            raise ValueError('cache_audit_proof_not_exact')
        if set(p['witnesses']) != set(old['post_search_cost_receipts']): raise ValueError('cache_audit_witness_omitted')
        for name, witness in p['witnesses'].items():
            if not t.train.same_json(witness['detailed_receipt'], old['post_search_cost_receipts'][name]):
                raise ValueError('cache_audit_receipt_changed')
            paths += 1; transitions += witness['scalar_and_role_transitions']
        if record['witness_count'] != len(p['witnesses']): raise ValueError('cache_audit_record_count')
        paths_count = sum(w['scalar_and_role_transitions'] for w in p['witnesses'].values())
        if record['transitions'] != paths_count: raise ValueError('cache_audit_transition_count')
        edges += record['original_edges']; sources.add(p['source_ir_content_sha256'])
    if ([r['sample_id'] for r in report['records']] != report['cohort'] or paths != report['path_witnesses']
            or transitions != report['scalar_and_pair_transitions'] or edges != report['original_edges']
            or len(sources) != report['full_source_packages']): raise ValueError('cache_audit_total_changed')
    inventory = {r['sample_id']: r for r in t.load(t.profile.ROOT/'report.json')['records']}
    expected = t.profile.cohort(list(inventory.values()),
        {k: t.load(v['artifact'])['original_edge_count'] for k, v in inventory.items()})
    if [r['sample_id'] for r in profile['records']] != [r['sample_id'] for r, g in expected]:
        raise ValueError('cache_audit_profile_cohort_changed')
    for r in profile['records']:
        p = t.load(r['artifact'])
        if not p['profile'] or p['result']['resource_guard']['wall_seconds'] != 20:
            raise ValueError('cache_audit_profile_empty_or_guard_changed')
    result = dict(passed=True, report_sha256=t.io.digest(root/'report.json'),
        profile_report_sha256=t.io.digest(profile_root/'report.json'), unique_pins=len(pins),
        all_train_scopes=len(report['records']), path_witnesses=paths, scalar_and_pair_transitions=transitions,
        original_edges=edges, full_source_packages=len(sources), profiled_scopes=len(profile['records']),
        proof_receipts_identical=True, fresh_decoder_runs=0, fit_performed=False,
        performance_or_accuracy_gain_claimed=False)
    t.io.write(output, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    p.add_argument('--profile-root', required=True); a = p.parse_args()
    print(json.dumps(run(a.root, a.profile_root), indent=2))
