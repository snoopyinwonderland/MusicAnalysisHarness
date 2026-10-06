"""Frozen full-score sequence/physical-measure diagnostics; no IR migration."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

import music21
from .source_locator_revision_trial import _load, _write, digest, validate_policy
from .source_sequence_replay_audit import audit, VERSION as AUDIT_VERSION
from .source_locator_revision import SCHEMA
from .source_physical_measure_audit import audit as measure_audit, VERSION as MEASURE_VERSION

VERSION = 'source-sequence-replay-trial-0.1.0'


def run(plan_path, previous_path, output):
    output = Path(output); previous_path = Path(previous_path)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    hashes = {}; plan = _load(plan_path, hashes); previous = _load(previous_path / 'report.json', hashes)
    if (previous.get('complete') is not True or previous.get('inputs_unchanged') is not True or
        previous.get('artifacts_unchanged') is not True or previous.get('source_labels_used') is not False or
        previous.get('accuracy_measured') is not False or previous.get('production_modified') is not False):
        raise ValueError('invalid_previous_locator_audit')
    _load(previous_path / 'run-contract.json', hashes, previous['contract_sha256'])
    for name, expected in previous['artifact_hashes'].items():
        if digest(name) != expected: raise ValueError('previous_artifact_hash_mismatch:' + name)
        hashes[str(Path(name).resolve())] = expected
    packages = {p['pair_id']: p for p in plan['packages']}
    records = {r['pair_id']: r for r in previous['records']}
    if (not packages or len(packages) != len(plan['packages']) or len(records) != len(previous['records']) or
        set(packages) != set(records) or previous['summary']['packages'] != len(packages)):
        raise ValueError('frozen_package_coverage_mismatch')
    if len(previous['contexts']) != previous['summary']['previous_case_samples_retained']:
        raise ValueError('previous_context_inventory_mismatch')
    parents = {}; sources = {}
    for pair, package in packages.items():
        info = package['source']; entry = info['manifest_entry']; validate_policy(entry)
        path = entry['score_source_path']
        if info['source_files'].get(path) != entry['score_sha256']: raise ValueError('score_path_not_frozen')
        for name, expected in info['source_files'].items():
            if digest(name) != expected: raise ValueError('source_file_hash_mismatch:' + name)
            hashes[str(Path(name).resolve())] = expected
        parents[pair] = _load(info['frozen_ir_path'], hashes, info['ir_sha256'])
        if (parents[pair]['ir_document_id'] != entry['ir_document_id'] or
            parents[pair]['score']['score_id'] != entry['score_id']): raise ValueError('parent_identity_mismatch')
        if digest(info['original_ir_path']) != info['ir_sha256']: raise ValueError('original_ir_hash_mismatch')
        hashes[str(Path(info['original_ir_path']).resolve())] = info['ir_sha256']
        _load(info['preparation_path'], hashes, info['preparation_sha256'])
        snapshot = records[pair]['snapshot']
        if (snapshot['parent_ir_sha256'] != info['ir_sha256'] or snapshot['source_xml_sha256'] != entry['score_sha256'] or
            previous['artifact_hashes'].get(snapshot['parent_ir']) != info['ir_sha256'] or
            previous['artifact_hashes'].get(snapshot['source_xml']) != entry['score_sha256']):
            raise ValueError('previous_snapshot_identity_mismatch')
        repair = _load(snapshot['revision'], hashes, snapshot['revision_sha256'])
        if repair['manifest_entry'] != entry or repair['pitch_policy'] != info['pitch_policy'] or repair['pair_id'] != pair:
            raise ValueError('previous_policy_identity_mismatch')
        ids = records[pair]['unmapped_ir_note_ids']
        if (len(set(ids)) != len(ids) or not set(ids) <= {n['note_id'] for n in parents[pair]['note_events']} or
            ids != repair.get('mapping', {}).get('unmatched_ir_note_ids', []) or
            records[pair]['status'] != repair['status'] or records[pair]['blockers'] != repair['blockers']):
            raise ValueError('previous_mapping_inventory_mismatch')
        sources[pair] = Path(path)
    hashes[str(SCHEMA.resolve())] = digest(SCHEMA)
    code = {str(p.resolve()): digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    contract = {'version': VERSION, 'audit_version': AUDIT_VERSION, 'measure_audit_version': MEASURE_VERSION,
        'music21_version': music21.__version__, 'input_hashes': hashes, 'code_hashes': code,
        'frozen_plan': str(Path(plan_path).resolve()), 'previous_locator_audit': str(previous_path.resolve()),
        'selection': 'all frozen parent packages; note and rest full sequences; no label or historical locator assignment',
        'publication': 'diagnostic sidecar only; no candidate Core, aliases applied or annotations retargeted',
        'source_labels_used': False, 'accuracy_measured': False, 'split_rights_changed': False,
        'production_modified': False, 'core_modified': False, 'gold_promoted': False,
        'training_promoted': False, 'external_transmission': False, 'engine_recomputed': False, 'gate_changed': False}
    output.mkdir(parents=True, exist_ok=False); _write(output / 'run-contract.json', contract)
    results = []; totals = Counter(); statuses = Counter(); artifacts = {}; started = perf_counter()
    measure_totals = Counter(); rejected_counts = Counter(); recovered = []; retained = []
    output_paths = set()
    for number, (pair, package) in enumerate(packages.items(), 1):
        old = parents[pair]; replay = audit(old, sources[pair])
        physical = measure_audit(old, replay['raw_measures'], replay['observations'])
        # Rejected fingerprints and source paths are retained, not silently dropped.
        old_unmapped = set(records[pair]['unmapped_ir_note_ids'])
        # Measure-blocked parents have no old trial mapping. The previous voice
        # audit has a different denominator; do not invent old unmapped IDs.
        by_id = {row['event_id']: row for row in replay['observations']}
        newly_observed = sorted(old_unmapped & set(by_id))
        not_observed = sorted(old_unmapped - set(by_id))
        recovered.extend({'pair_id': pair, 'note_id': nid, 'occurrence_status': by_id[nid]['occurrence_status'],
                          'independent_occurrence_certified': False} for nid in newly_observed)
        retained.extend({'pair_id': pair, 'note_id': nid} for nid in not_observed)
        result = {'version': VERSION, 'pair_id': pair, 'manifest_entry': deepcopy(package['source']['manifest_entry']),
            'pitch_policy': deepcopy(package['source']['pitch_policy']), 'parent_snapshot': deepcopy(records[pair]['snapshot']),
            'prior_locator_status': records[pair]['status'], 'prior_locator_blockers': records[pair]['blockers'],
            'prior_unmapped_note_ids': sorted(old_unmapped), 'replayed_prior_unmapped_note_ids': newly_observed,
            'remaining_prior_unmapped_note_ids': not_observed, 'replay': replay, 'physical_measure_audit': physical,
            'old_source_locator_candidates_unchanged': True, 'source_labels_used': False,
            'core_modified': False, 'annotation_retargeted': False, 'engine_recomputed': False}
        path = output / 'packages' / (hashlib.sha256(pair.encode()).hexdigest()[:20] + '.json.gz')
        if path in output_paths: raise ValueError('duplicate_output_basename')
        output_paths.add(path)
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(gzip.compress(json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode(), mtime=0))
        artifacts[str(path.resolve())] = digest(path)
        totals.update(replay['counts']); statuses[replay['status']] += 1
        rejected_counts.update(r['reason'] for r in replay['rejected'])
        measure_totals.update(physical['counts'])
        results.append({'pair_id': pair, 'work_family_id': package['source']['manifest_entry']['work_family_id'],
            'artifact': str(path.resolve()), 'sha256': digest(path), 'status': replay['status'],
            'blockers': replay['blockers'], 'counts': replay['counts'], 'measure_counts': physical['counts'],
            'prior_status': records[pair]['status'], 'replayed_prior_unmapped': len(newly_observed)})
        print(f'[{number}/{len(packages)}] {pair}: {replay["status"]}, {len(replay["observations"])} events', flush=True)
    changed_inputs = [p for p, expected in {**hashes, **code}.items() if digest(p) != expected]
    changed_inputs += sorted(set(str(p.resolve()) for p in Path(__file__).parent.glob('*.py')).symmetric_difference(code))
    changed_artifacts = [p for p, expected in artifacts.items() if digest(p) != expected]
    if (totals['matched_notes'] + totals['matched_rests'] + totals['rejected_events'] + totals['unchecked_events'] !=
        totals['notes'] + totals['rests']): raise ValueError('full_event_inventory_partition_mismatch')
    report = {'version': VERSION, 'complete': True, 'summary': {'packages': len(results),
        'work_families': len({r['work_family_id'] for r in results}), 'replay_statuses': dict(statuses),
        'events': dict(totals), 'physical_measures': dict(measure_totals), 'rejected_reasons': dict(rejected_counts),
        'replayed_prior_unmapped_notes': len(recovered), 'remaining_prior_unmapped_notes': len(retained),
        'previous_locator_candidates_retained': previous['summary']['revision_statuses'],
        'previous_case_samples_retained': previous['summary']['previous_case_samples_retained']},
        'records': results, 'replayed_prior_unmapped': recovered, 'remaining_prior_unmapped': retained,
        'previous_contexts': deepcopy(previous['contexts']), 'artifact_hashes': artifacts,
        'inputs_and_code_unchanged': not changed_inputs, 'artifacts_unchanged': not changed_artifacts,
        'changed_input_paths': changed_inputs, 'changed_artifact_paths': changed_artifacts,
        'contract_sha256': digest(output / 'run-contract.json'), 'source_labels_used': False,
        'accuracy_measured': False, 'independent_occurrence_certified': False,
        'core_modified': False, 'production_modified': False, 'annotation_retargeted': False,
        'gold_promoted': False, 'training_promoted': False, 'split_rights_changed': False,
        'external_transmission': False, 'engine_recomputed': False, 'gate_changed': False,
        'elapsed_seconds': perf_counter() - started,
        'limits': ['Exact pinned parser replay is not independent identity of identical repeated occurrences.',
                   'Physical measure aliases are proposals keyed by old ID plus sequential index; never automatic retarget.',
                   'XML part+voice is source notation, not actual contrapuntal identity or a melodic role.',
                   'No harmonic accuracy, candidate promotion, new NCT labels or operating viewer changes.']}
    _write(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True); parser.add_argument('--previous', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(); result = run(args.plan, args.previous, args.output)
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    return 0 if result['inputs_and_code_unchanged'] and result['artifacts_unchanged'] else 2


if __name__ == '__main__': raise SystemExit(main())
