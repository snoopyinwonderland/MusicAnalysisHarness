"""Replay sealed source vectors, unchanged costs and Train contrast counts."""
import argparse
import json
from pathlib import Path
from musicanote_harness import harmony_context_competition_trial as t


def run(root):
    root = Path(root); dest = root/'post-seal-audit.json'
    if dest.exists(): raise ValueError('output_exists_no_overwrite')
    report = t.load(root/'report.json'); contract = t.load(root/'run-contract.json')
    pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    def check():
        for p, h in pins.items():
            if t.io.digest(p) != h: raise ValueError('competition_audit_sha_changed:'+p)
    check()
    flags = ('fit_performed', 'fresh_search_performed', 'pool_reranking_performed', 'dev_inference_or_evaluation',
             'weights_changed', 'production_modified', 'reference_labels_used_for_new_features')
    if report['complete'] is not True or any(report[k] is not False or contract[k] is not False for k in flags):
        raise ValueError('competition_audit_scope_changed')
    reads = set()
    def read(p, expected=None, compressed=False, raw=False):
        name = str(Path(p).resolve()); h = t.io.digest(p)
        if pins.get(name) != h or expected is not None and h != expected:
            raise ValueError('competition_audit_unsealed_input:'+name)
        reads.add(name); return None if raw else t.load(p)
    ctx = t.context(read)
    if contract['cohort'] != [r['sample_id'] for r in ctx['rows']]: raise ValueError('competition_audit_cohort_changed')
    packets = []; paths = transitions = figures = abstentions = edges = 0; sources = set()
    for i, (row, saved) in enumerate(zip(ctx['rows'], report['records']), 1):
        packet = read(saved['artifact'], saved['sha256']); rebuilt = t.build_sample(ctx, row, read)
        if not t.prior.seals.same_json(packet, rebuilt): raise ValueError('competition_audit_replay_changed:'+row['sample_id'])
        packets.append(rebuilt); edges += rebuilt['original_edge_count']; sources.add(rebuilt['source_ir_content_sha256'])
        for a in rebuilt['arms'].values():
            if not a['selected']: abstentions += 1; continue
            profile = a['source_profile']; paths += 1; transitions += len(profile['transitions'])
            figures += sum(len(d['conditional_figures']) for d in profile['transitions'])
            if any(profile[k] is not False for k in ('source_labels_used', 'weights_changed', 'selection_changed', 'existing_costs_changed', 'source_modified')):
                raise ValueError('competition_audit_blindness_changed')
        print(f'[context competition audit {i}/{len(ctx["rows"])}]', flush=True)
    if len(packets) != len(ctx['rows']) or len(packets) != report['scopes'] or edges != report['original_edges'] or len(sources) != report['full_source_packages']:
        raise ValueError('competition_audit_coverage_changed')
    if not t.prior.seals.same_json(t.summarize(packets), report['summary']): raise ValueError('competition_audit_counts_changed')
    check()
    result = {'passed': True, 'version': t.VERSION, 'report_sha256': t.io.digest(root/'report.json'),
        'run_contract_sha256': t.io.digest(root/'run-contract.json'), 'audit_code_sha256': t.io.digest(Path(__file__)),
        'sha_checks': len(pins), 'sealed_inputs_reloaded': len(reads), 'replayed_scopes': len(packets),
        'source_packages': len(sources), 'original_edges': edges, 'stored_paths_vectors_and_original_costs_replayed': paths,
        'three_run_profiles_replayed': transitions, 'conditional_figures_replayed': figures, 'preserved_abstentions': abstentions,
        'summary_and_jointly_available_deltas_replayed': True, 'new_fit_search_or_dev': False, 'source_core_and_old_score_unchanged': True}
    t.io.write(dest, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(run(p.parse_args().root), indent=2), flush=True)
