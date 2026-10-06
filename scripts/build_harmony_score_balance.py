"""Stage84: sealed-source 35-cost ledgers and local candidate-only exports.

No fresh inference, fitting, ChordSpan promotion, external API, or writes to
Music Composition. The output is a new directory; parents remain immutable.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
from pathlib import Path
from time import perf_counter
import json

from musicanote_harness import harmony_member_role_trial as prior
from musicanote_harness import harmony_score_balance_ledger as ledger
from musicanote_harness import harmony_arrangement_reference as consumer

ROOT = Path('K:/Music Analysis/output/harmony-member-role-interactions-2026-10-05-r2')
PINS = {'report.json': '641806ea8fbfc94c135446a4134a57ff607e4fc581aad35b2274463102ccd340',
        'post-seal-audit.json': '95221af04e321c7500b3df64182b89ea65252d0c593145a3c2d00e246456f8df',
        'model.json.gz': '3f2c10e7899b3e66696be82bc64e41530829cb48c23707c456dcc3231033d346',
        'training-vectors.json.gz': '02c9a9938513dc4188b84af9b55df3965ce7d712c81d2851ca1931c5fe6da999'}
VERSION = 'harmony-score-balance-and-consumer-trial-0.1.0'


def run(output):
    output = Path(output)
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    tick = perf_counter(); inputs, artifacts, code = {}, {}, {}
    def read(path, expected=None, *, raw=False):
        path = Path(path); key = str(path.resolve()); sha = prior.io.digest(path)
        if (expected is not None and sha != expected) or (key in inputs and inputs[key] != sha):
            raise ValueError('balance_input_changed:'+key)
        inputs[key] = sha
        return None if raw else prior.load(path)
    report, audit, model, vectors = [read(ROOT/n, h) for n, h in PINS.items()]
    if report['complete'] is not True or audit['passed'] is not True or audit['report_sha256'] != PINS['report.json']:
        raise ValueError('balance_parent_unsealed')
    if model['purpose'] != 'local_noncommercial_research' or any(model['restrictions'].values()):
        raise ValueError('balance_model_use_contract_changed')
    for path, sha in (report['input_hashes'] | report['artifact_hashes'] | report['code_hashes']).items():
        read(path, sha, raw=True)
    weights = ledger.coefficients(model)
    for path in (Path(ledger.__file__), Path(consumer.__file__), Path(__file__),
                 Path('tests/test_harmony_score_balance_ledger.py'), Path('tests/test_harmony_arrangement_reference.py'),
                 Path('scripts/validate_harmony_score_balance.py'), Path('scripts/audit_harmony_score_balance.py')):
        code[str(path.resolve())] = prior.io.digest(path)
    output.mkdir(parents=True); (output/'ledgers').mkdir(); (output/'references').mkdir()
    def save(path, value, compressed=False):
        path = output/path
        (prior.io.write_packet if compressed else prior.io.write)(path, value)
        key = str(path.resolve()); artifacts[key] = prior.io.digest(path); return key, artifacts[key]
    save(Path('run-contract.json'), {'version': VERSION, 'parent_report_sha256': PINS['report.json'],
         'cohort': report['cohort'], 'code_pins': code, 'new_fit_or_search': False, 'dev_used': False,
         'purpose': model['purpose'], 'consumer_exports_are_hypotheses_not_chordspans': True,
         'production_modified': False, 'claude_project_modified': False})
    records = []; contrast_rows = []; stats = Counter(); sums = defaultdict(F); families = set(); sources = {}
    pool = defaultdict(list)
    for row in vectors['rows']:
        pool[row['sample_id']].append(row)
    pieces = defaultdict(list)
    for index, record in enumerate(report['records'], 1):
        sample = record['sample_id']; packet = read(record['artifact'], record['sha256'])
        scope = read(packet['original_scope_artifact'], packet['original_scope_sha256'])
        paths = packet['full_source_paths']; ir_path = paths['working_ir_path']
        if ir_path not in sources:
            ir = read(ir_path, paths['working_ir_sha256'])
            read(paths['whole_musicxml_path'], paths['whole_musicxml_sha256'], raw=True)
            sources[ir_path] = ir
        ir = sources[ir_path]
        if packet['model_sha256'] != PINS['model.json.gz']:
            raise ValueError('balance_case_model_changed')
        proof = read(ROOT/'vectors'/(sample+'.json.gz'), report['artifact_hashes'][str((ROOT/'vectors'/(sample+'.json.gz')).resolve())])
        comparisons = {}; flattened = {}
        receipts = packet['post_search_cost_receipts']
        for arm, receipt in receipts.items():
            flattened[arm] = ledger.flatten(receipt, weights); stats['cost_receipts_checked'] += 1
        if 'stored_target' not in receipts:
            raise ValueError('balance_train_target_missing')
        for arm in consumer.ALLOWED_ARMS:
            if arm in receipts:
                comparisons[arm+'_minus_stored_target'] = ledger.compare(receipts[arm], receipts['stored_target'], weights)
        prepared = {(tuple(r['ids']), r['target']): ledger.reweight_roles(r['receipt'], weights) for r in proof['path_receipts']}
        for row in pool[sample]:
            neg = prepared[(tuple(row['negative_ids']), False)]; target = prepared[(tuple(row['target_ids']), True)]
            comp = ledger.compare(neg, target, weights); gap = ledger.f(comp['left_minus_right_cost'])
            old_gap = ledger.f(row['frozen33_gap'])+sum((ledger.f(row['score_delta'][k])*weights[k] for k in prior.scoring.FEATURES), F())
            if gap != old_gap:
                raise ValueError('balance_training_gap_changed')
            violation = max(F(), ledger.f(row['loss'])-gap)
            stats['contrasts_checked'] += 1; stats['margin_violations'] += violation > 0
            stats['zero_loss_protections'] += ledger.f(row['loss']) == 0
            stats['known_nonzero_35_gradient'] += any(t['known_both'] and ledger.f(t['value_delta']) for t in comp['terms'].values())
            sums['margin_violation_sum'] += violation
            contrast_rows.append({'sample_id': sample, 'contrast_id': row['contrast_id'], 'source_arm': row['source_arm'],
                                  'loss': row['loss'], 'margin_violation': ledger.q(violation), 'comparison': comp})
        binding = {'verified': True, 'case_sha256': record['sha256'], 'model_sha256': PINS['model.json.gz'],
                   'scope_artifact_sha256': packet['original_scope_sha256'],
                   'whole_musicxml_sha256': paths['whole_musicxml_sha256'], 'whole_ir_sha256': paths['working_ir_sha256']}
        reference = consumer.build(packet, scope['problem'], ir, binding=binding)
        stats['references'] += 1; stats['unresolved_references'] += reference['unresolved']
        stats['exported_hypotheses'] += len(reference['hypotheses'])
        lp, lh = save(Path('ledgers')/(sample+'.json.gz'), {'sample_id': sample, 'scope': packet['sample_span'],
                         'case_ref': record['artifact'], 'case_sha256': record['sha256'],
                         'paths': flattened, 'comparisons': comparisons, 'new_fit_or_search': False}, True)
        rp, rh = save(Path('references')/(sample+'.json'), reference)
        records.append({'sample_id': sample, 'pair_id': packet['pair_id'], 'work_family_id': packet['work_family_id'],
                        'ledger_ref': lp, 'ledger_sha256': lh, 'reference_ref': rp, 'reference_sha256': rh,
                        'fresh_status': packet['result']['status']})
        pieces[ir['score']['score_id']].append({'reference_ref': rp, 'reference_sha256': rh, 'sample_id': sample,
                                             'scope': packet['sample_span'], 'unresolved': reference['unresolved']})
        families.add(packet['work_family_id'])
        print(f'[balance ledger {index}/{len(report["records"])}] {sample}', flush=True)
    if len(contrast_rows) != report['training_contrasts'] or sums['margin_violation_sum'] != ledger.f(model['margin_sum_after']):
        raise ValueError('balance_pool_summary_changed')
    save(Path('train-contrasts.json.gz'), {'rows': contrast_rows, 'target_is_training_reference_not_prediction': True}, True)
    piece_records = []
    for score_id, refs in sorted(pieces.items()):
        path, sha = save(Path('references')/(score_id+'-index.json'), {'schema_name': 'musicanote-harmony-reference-index',
                        'schema_version': '0.1.0', 'score_id': score_id, 'scopes': refs,
                        'scope_list_may_overlap': True, 'whole_score_analysis': False,
                        'generation_ready': False, 'do_not_merge_into_full_score_chordspans': True})
        piece_records.append({'score_id': score_id, 'index_ref': path, 'sha256': sha})
    for path, sha in (inputs | artifacts | code).items():
        if prior.io.digest(path) != sha:
            raise ValueError('balance_final_seal_changed:'+path)
    final = {'version': VERSION, 'complete': True, 'new_fit_or_search': False, 'dev_used': False,
             'independent_accuracy_claimed': False, 'source_packages': len(sources), 'work_families': len(families),
             'original_edges': report['original_edges'], 'counts': dict(stats),
             'margin_violation_sum': ledger.q(sums['margin_violation_sum']), 'margin_is_not_accuracy': True,
             'records': records, 'piece_indexes': piece_records, 'input_hashes': inputs,
             'artifact_hashes': artifacts, 'code_hashes': code, 'parent_report_sha256': PINS['report.json'],
             'elapsed_seconds': perf_counter()-tick, 'production_modified': False, 'claude_project_modified': False}
    prior.io.write(output/'report.json', final); return final


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True)
    result = run(parser.parse_args().output)
    print(json.dumps({k: result[k] for k in ('complete', 'counts', 'source_packages', 'elapsed_seconds')}, indent=2), flush=True)
