"""Audit Stage84 sealed ledgers, known masks and oracle-free candidate exports.

No fitting or search. Arithmetic is reconstructed from the Stage83 source
receipts, not accepted from the Stage84 totals. Parents are never rewritten.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

from musicanote_harness import harmony_member_role_trial as parent
from musicanote_harness import harmony_score_balance_ledger as l
from musicanote_harness import harmony_arrangement_reference as c


def audit(root):
    tick = perf_counter(); root = Path(root); destination = root/'post-seal-audit.json'
    if destination.exists(): raise ValueError('output_exists_no_overwrite')
    report = parent.load(root/'report.json'); pins = report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']
    for path, sha in pins.items():
        if parent.io.digest(path) != sha: raise ValueError('balance_audit_hash_changed:'+path)
    if not report['complete'] or report['new_fit_or_search'] or report['dev_used'] or report['independent_accuracy_claimed']:
        raise ValueError('balance_audit_claim_changed')
    contract = parent.load(root/'run-contract.json')
    if contract['code_pins'] != report['code_hashes']: raise ValueError('balance_audit_code_seal_changed')
    parent_root = Path('K:/Music Analysis/output/harmony-member-role-interactions-2026-10-05-r2')
    original = parent.load(parent_root/'report.json'); model = parent.load(parent_root/'model.json.gz')
    weights = l.coefficients(model); cases = {r['sample_id']: r for r in original['records']}; counts = Counter(); sources = {}

    def source_terms(receipt):
        result = {}
        for block_name, names in (('legacy', l.old.FEATURES), ('context', l.context.FEATURES), ('member_role', l.role.FEATURES)):
            block = receipt[block_name]
            field = 'observed_feature_sums' if block_name == 'legacy' else 'scored_available_feature_sums'
            for k in names:
                scored = l.f(block[field][k]); known = block['availability'][k]
                result[k] = {'known': known, 'value': l.q(scored) if known else None,
                    'observed_partial_sum': block['observed_feature_sums'][k],
                    'scored_known_local_sum': l.q(scored), 'coefficient': l.q(weights[k]), 'cost': l.q(scored*weights[k])}
        return result

    def verify_flat(flat, receipt):
        expected = source_terms(receipt)
        if flat['terms'] != expected or l.f(flat['cost']) != sum((l.f(t['cost']) for t in expected.values()), F()):
            raise ValueError('balance_audit_term_reconstruction_failed')
        if sum((l.f(v) for v in flat['group_costs'].values()), F()) != l.f(flat['cost']):
            raise ValueError('balance_audit_group_sum_failed')
        if flat['whole_unknown_is_not_zero'] is not True: raise ValueError('balance_audit_unknown_contract')
        counts['cost_receipts_checked'] += 1

    def verify_comparison(comp, a, b):
        expected = {}
        for k in l.FEATURES:
            known = a[k]['known'] and b[k]['known']
            delta = l.f(a[k]['scored_known_local_sum'])-l.f(b[k]['scored_known_local_sum'])
            expected[k] = {'known_both': known, 'value_delta': l.q(delta) if known else None,
                           'scored_partial_delta': l.q(delta), 'cost_delta': l.q(delta*weights[k])}
        total = sum((l.f(v['cost_delta']) for v in expected.values()), F())
        if expected != comp['terms'] or l.f(comp['left_minus_right_cost']) != total:
            raise ValueError('balance_audit_comparison_reconstruction_failed')
        for group, names in l.GROUPS.items():
            if l.f(comp['group_deltas'][group]) != sum((l.f(expected[k]['cost_delta']) for k in names), F()):
                raise ValueError('balance_audit_comparison_group_failed')
        if comp['probability'] is not None or comp['new_fit_or_search'] or comp['candidate_set_complete']:
            raise ValueError('balance_audit_comparison_claim')
        return total

    for row in report['records']:
        source = cases[row['sample_id']]; packet = parent.load(source['artifact'])
        led = parent.load(row['ledger_ref']); exported = parent.load(row['reference_ref']); receipts = packet['post_search_cost_receipts']
        if set(led['paths']) != set(receipts): raise ValueError('balance_audit_receipts_lost')
        for arm, receipt in receipts.items(): verify_flat(led['paths'][arm], receipt)
        for arm in c.ALLOWED_ARMS:
            if arm in receipts:
                verify_comparison(led['comparisons'][arm+'_minus_stored_target'], source_terms(receipts[arm]), source_terms(receipts['stored_target']))
                counts['case_comparisons'] += 1
        paths = packet['full_source_paths']; ir_path = paths['working_ir_path']
        if ir_path not in sources: sources[ir_path] = parent.load(ir_path)
        scope = parent.load(packet['original_scope_artifact'])
        binding = {'verified': True, 'case_sha256': source['sha256'], 'model_sha256': packet['model_sha256'],
                   'scope_artifact_sha256': packet['original_scope_sha256'],
                   'whole_musicxml_sha256': paths['whole_musicxml_sha256'], 'whole_ir_sha256': paths['working_ir_sha256']}
        if exported != c.build(packet, scope['problem'], sources[ir_path], binding=binding):
            raise ValueError('balance_audit_candidate_reconstruction_failed')
        for h in exported['hypotheses']:
            if not set(h['source_arms']) <= set(c.ALLOWED_ARMS) or h['human_validated'] or h['confidence'] is not None:
                raise ValueError('balance_audit_oracle_or_confidence_leak')
        counts['references'] += 1; counts['unresolved_references'] += exported['unresolved']
        counts['exported_hypotheses'] += len(exported['hypotheses'])

    pool = parent.load(parent_root/'training-vectors.json.gz'); rows = {(r['sample_id'], r['contrast_id']): r for r in pool['rows']}
    detailed = parent.load(root/'train-contrasts.json.gz'); proofs = {}; margin = F()
    for row in detailed['rows']:
        key = row['sample_id'], row['contrast_id']; source = rows[key]
        if row['sample_id'] not in proofs:
            proof = parent.load(parent_root/'vectors'/(row['sample_id']+'.json.gz'))
            proofs[row['sample_id']] = {(tuple(v['ids']), v['target']): v['receipt'] for v in proof['path_receipts']}
        paths = proofs[row['sample_id']]
        a = source_terms(paths[tuple(source['negative_ids']), False]); b = source_terms(paths[tuple(source['target_ids']), True])
        gap = verify_comparison(row['comparison'], a, b)
        violation = max(F(), l.f(source['loss'])-gap)
        if row['loss'] != source['loss'] or row['source_arm'] != source['source_arm'] or l.f(row['margin_violation']) != violation:
            raise ValueError('balance_audit_train_loss_changed')
        margin += violation; counts['contrasts_checked'] += 1; counts['margin_violations'] += violation > 0
        counts['zero_loss_protections'] += l.f(source['loss']) == 0
        counts['known_nonzero_35_gradient'] += any(v['known_both'] and l.f(v['value_delta']) for v in row['comparison']['terms'].values())
    if len(rows) != len(detailed['rows']) or margin != l.f(report['margin_violation_sum']) or margin != l.f(model['margin_sum_after']):
        raise ValueError('balance_audit_pool_margin_failed')
    if {k: counts[k] for k in report['counts']} != report['counts'] or len(sources) != report['source_packages']:
        raise ValueError('balance_audit_summary_failed')
    indexes = [parent.load(p['index_ref']) for p in report['piece_indexes']]
    refs = {r['reference_ref']: r['reference_sha256'] for r in report['records']}
    flattened = [s for value in indexes for s in value['scopes']]
    if len(flattened) != len(refs) or {s['reference_ref']: s['reference_sha256'] for s in flattened} != refs:
        raise ValueError('balance_audit_index_coverage_failed')
    if any(v['whole_score_analysis'] or v['generation_ready'] or not v['do_not_merge_into_full_score_chordspans'] for v in indexes):
        raise ValueError('balance_audit_whole_score_false_claim')
    for path, sha in pins.items():
        if parent.io.digest(path) != sha: raise ValueError('balance_audit_final_hash_changed:'+path)
    result = {'passed': True, 'report_sha256': parent.io.digest(root/'report.json'), 'counts': dict(counts),
              'unique_hashes_verified': len(pins), 'margin_reconstructed': l.q(margin),
              'source_packages': len(sources), 'no_search_or_fit': True, 'claude_project_modified': False,
              'independent_musical_accuracy_claimed': False, 'elapsed_seconds': perf_counter()-tick}
    parent.io.write(destination, result); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', required=True)
    print(json.dumps(audit(p.parse_args().root), indent=2), flush=True)
