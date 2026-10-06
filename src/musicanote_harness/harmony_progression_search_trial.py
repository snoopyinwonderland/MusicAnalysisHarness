"""Frozen bounded progression proposals and same-assignment comparisons.

This is an offline proposal experiment, not final score-wide harmony inference.
Every previous context, including abstentions, remains in the denominator.
"""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .source_locator_revision_trial import _load, _write, digest, validate_policy
from .harmony_context_integration_trial import _guard_files, _gzip
from .harmony_progression_search import search, VERSION as SEARCH_VERSION
from .harmony_progression_joint_comparison import compare, VERSION as COMPARISON_VERSION

VERSION = 'harmony-progression-search-trial-0.1.0'


def run(previous_path, output, *, max_segments=6, per_state_limit=6, max_complete_paths=24,
        transition_budget=200000, max_assignments=64, max_evaluations=4096, max_comparisons=8192):
    previous_path, output = Path(previous_path), Path(output)
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    hashes = {}
    previous = _load(previous_path / 'report.json', hashes)
    if (previous.get('complete') is not True or previous.get('inputs_and_code_unchanged') is not True or
            previous.get('artifacts_unchanged') is not True or previous.get('source_labels_used') is not False or
            previous.get('accuracy_measured') is not False or previous.get('production_modified') is not False):
        raise ValueError('invalid_previous_context_trial')
    old_contract = _load(previous_path / 'run-contract.json', hashes, previous['contract_sha256'])
    _guard_files(old_contract['input_hashes'], hashes)
    _guard_files(old_contract['code_hashes'], hashes)
    _guard_files(previous['artifact_hashes'], hashes)
    parents = {r['pair_id']: r for r in previous['measure_revisions']}
    if (not parents or len(parents) != len(previous['measure_revisions']) or
            len(parents) != previous['summary']['packages']):
        raise ValueError('previous_package_inventory_mismatch')
    samples = []; seen = set(); families = set(); pairs = set()
    for row in previous['records']:
        key = row['pair_id'], row['plan_index'], row['sample_id']
        if key in seen or row['pair_id'] not in parents:
            raise ValueError('previous_sample_inventory_mismatch')
        seen.add(key); pairs.add(row['pair_id'])
        packet = _load(row['artifact'], hashes, row['sha256'], compressed=True)
        b = packet['bundle']; provenance = packet['provenance']
        validate_policy(provenance['manifest_entry'])
        families.add(provenance['manifest_entry']['work_family_id'])
        if (packet['pair_id'] != row['pair_id'] or packet['plan_index'] != row['plan_index'] or
                b['sample']['sample_id'] != row['sample_id'] or b['counts'] != row['summary'] or
                b['status'] != row['status'] or b['parent_ir_document_id'] != row['working_ir_document_id'] or
                provenance['working_ir_document_id'] != row['working_ir_document_id'] or
                provenance['working_ir_document_id'] != parents[row['pair_id']]['working_ir_document_id']):
            raise ValueError('previous_context_binding_mismatch')
        if (provenance.get('source_labels_used') is not False or
                provenance.get('extensions_consumed') is not False or
                provenance.get('annotation_retargeted') is not False or
                provenance.get('ir_use_scope') != 'note_rest_measure_core_only' or
                provenance['pitch_policy'].get('harmonic_replay_allowed') is not True):
            raise ValueError('previous_scope_or_policy_not_ready')
        # Some frozen contexts expand to hundreds of MB. Preserve the complete
        # denominator, not all decoded inventories in memory at the same time.
        # Re-reading below rechecks the same frozen file hash before use.
        samples.append((key, row))
        del b, provenance, packet
    if (pairs != set(parents) or len(samples) != previous['summary']['samples'] or
            len(families) != previous['summary']['work_families']):
        raise ValueError('previous_sample_inventory_mismatch')
    search_config = dict(max_segments=max_segments, per_state_limit=per_state_limit,
                         max_complete_paths=max_complete_paths, transition_budget=transition_budget)
    compare_config = dict(max_assignments=max_assignments, max_evaluations=max_evaluations,
                          max_comparisons=max_comparisons)
    for value in (*search_config.values(), *compare_config.values()):
        if type(value) is not int or value < 1:
            raise ValueError('invalid_trial_budget')
    code = {str(p.resolve()): digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    contract = {'version': VERSION, 'search_version': SEARCH_VERSION,
        'comparison_version': COMPARISON_VERSION, 'input_hashes': hashes, 'code_hashes': code,
        'previous_context_trial': str(previous_path.resolve()),
        'search_config': search_config, 'comparison_config': compare_config,
        'selection': 'all previous frozen contexts; automatic bounded full-context proposals, not new score sampling',
        'search_scope': 'stored spelled alternatives only; trimming is approximate proposal computation, not harmonic rejection',
        'comparison_scope': 'complete path under one shared sampled assignment; no union of competing assignments',
        'source_labels_used': False, 'accuracy_measured': False, 'production_modified': False,
        'operating_core_modified': False, 'annotation_retargeted': False,
        'split_rights_changed': False, 'gold_promoted': False, 'training_promoted': False,
        'external_transmission': False, 'confidence_calibrated': False,
        'final_harmony_selected': False, 'score_wide_optimization_performed': False}
    output.mkdir(parents=True, exist_ok=False)
    _write(output / 'run-contract.json', contract)
    artifacts, rows = {}, []
    search_statuses, comparison_statuses = Counter(), Counter()
    prior_statuses, search_counts, comparison_counts = Counter(), Counter(), Counter()
    started = perf_counter()
    for number, (key, old_row) in enumerate(samples, 1):
        old_packet = _load(old_row['artifact'], hashes, old_row['sha256'], compressed=True)
        b = old_packet['bundle']
        before = hashlib.sha256(json.dumps(b, sort_keys=True, ensure_ascii=False,
                                separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        proposals = search(b, **search_config)
        after_search = hashlib.sha256(json.dumps(b, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        if before != after_search:
            raise ValueError('progression_trial_mutated_previous_bundle')
        compared = compare(b, proposals, **compare_config)
        after = hashlib.sha256(json.dumps(b, sort_keys=True, ensure_ascii=False,
                               separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        if before != after:
            raise ValueError('progression_trial_mutated_previous_bundle')
        result = {'version': VERSION, 'pair_id': key[0], 'plan_index': key[1],
            'sample': deepcopy(b['sample']), 'provenance': deepcopy(old_packet['provenance']),
            'previous_context_artifact': old_row['artifact'], 'previous_context_sha256': old_row['sha256'],
            'input_bundle_content_sha256': before, 'search': proposals, 'joint_comparison': compared,
            'selected': None, 'source_labels_used': False, 'accuracy_measured': False,
            'production_modified': False, 'annotation_retargeted': False}
        name = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:20]
        path = output / 'samples' / (name + '.json.gz')
        _gzip(path, result); artifacts[str(path.resolve())] = digest(path)
        search_statuses[proposals['status']] += 1
        comparison_statuses[compared['status']] += 1
        prior_statuses[old_row['previous_status']] += 1
        sc = proposals.get('search_counts', proposals.get('counts', proposals.get('summary', {})))
        cc = compared.get('comparison_counts', compared.get('counts', compared.get('summary', {})))
        for target, data in ((search_counts, sc), (comparison_counts, cc)):
            for field, value in data.items():
                if type(value) is int:
                    target[field] += value
        rows.append({'pair_id': key[0], 'plan_index': key[1], 'sample_id': key[2],
            'previous_status': old_row['previous_status'], 'search_status': proposals['status'],
            'comparison_status': compared['status'], 'search_counts': sc, 'comparison_counts': cc,
            'artifact': str(path.resolve()), 'sha256': digest(path)})
        if number % 20 == 0 or number == len(samples):
            print(f'[{number}/{len(samples)}] progression proposals/comparison: {proposals["status"]} / {compared["status"]}', flush=True)
        del old_packet, b, proposals, compared, result
    if dict(prior_statuses) != previous['summary']['previous_statuses_retained']:
        raise ValueError('previous_abstention_denominator_changed')
    changed = [p for p, sha in {**hashes, **code}.items() if digest(p) != sha]
    changed += sorted(set(str(p.resolve()) for p in Path(__file__).parent.glob('*.py')).symmetric_difference(code))
    artifact_changed = [p for p, sha in artifacts.items() if digest(p) != sha]
    report = {'version': VERSION, 'complete': True,
        'summary': {'packages': len(parents), 'work_families': len(families), 'samples': len(rows),
            'search_statuses': dict(search_statuses), 'comparison_statuses': dict(comparison_statuses),
            'search_counts': dict(search_counts), 'comparison_counts': dict(comparison_counts),
            'previous_statuses_retained': dict(prior_statuses)},
        'records': rows, 'artifact_hashes': artifacts,
        'contract_sha256': digest(output / 'run-contract.json'),
        'inputs_and_code_unchanged': not changed, 'artifacts_unchanged': not artifact_changed,
        'changed_input_paths': changed, 'changed_artifact_paths': artifact_changed,
        **{field: contract[field] for field in ('source_labels_used', 'accuracy_measured', 'production_modified',
            'operating_core_modified', 'annotation_retargeted', 'split_rights_changed', 'gold_promoted',
            'training_promoted', 'external_transmission', 'confidence_calibrated', 'final_harmony_selected',
            'score_wide_optimization_performed')},
        'elapsed_seconds': perf_counter() - started,
        'limits': ['The 322 records are frozen local contexts, not 322 independent pieces or whole-score optimal analyses.',
            'Proposal pruning can omit a musically better path; exact comparison covers proposals only.',
            'Conditional NCT and omission assumptions are not final labels or independent evidence votes.',
            'Comparison abstentions remain local; no candidate quality, voice or unobserved tone is silently waived.',
            'No final confidence, human validation, annotation migration, production engine or score viewer update.']}
    _write(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', required=True)
    parser.add_argument('--output', required=True)
    for name, default in (('max-segments', 6), ('per-state-limit', 6), ('max-complete-paths', 24),
                          ('transition-budget', 200000), ('max-assignments', 64),
                          ('max-evaluations', 4096), ('max-comparisons', 8192)):
        parser.add_argument('--' + name, type=int, default=default)
    args = vars(parser.parse_args())
    report = run(args.pop('previous'), args.pop('output'), **args)
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    return 0 if report['inputs_and_code_unchanged'] and report['artifacts_unchanged'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
