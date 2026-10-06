"""Frozen source-locator revision trial; parent datasets/analyses stay immutable."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .source_locator_revision import revise, VERSION as REVISION_VERSION, SCHEMA
from .harmony_relation_case_trial import source_index, context

VERSION = 'source-locator-revision-trial-0.1.1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path, hashes, expected=None, compressed=False):
    path = Path(path); payload = path.read_bytes(); observed = hashlib.sha256(payload).hexdigest()
    if expected is not None and observed != expected: raise ValueError('input_hash_mismatch:' + str(path))
    key = str(path.resolve())
    if key in hashes and hashes[key] != observed: raise ValueError('input_changed_while_loading:' + key)
    hashes[key] = observed
    return json.loads(gzip.decompress(payload) if compressed else payload)


def _write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def validate_policy(entry):
    if entry.get('split') not in ('train', 'dev'): raise ValueError('protected_or_unassigned_split')
    if entry.get('rights', {}).get('internal_research_use') is not True: raise ValueError('internal_research_not_approved')
    if not entry.get('work_family_id') or not entry.get('score_sha256'): raise ValueError('missing_frozen_policy_identity')


def _event_projection(context_value):
    value = deepcopy(context_value)
    for note in value['note_events']:
        note.pop('notation'); note['grace'].pop('slash', None)
    return {field: value[field] for field in ('span', 'measures', 'note_events', 'rest_events', 'sounding_events')}


def run(plan_path, previous_path, output):
    output = Path(output); previous_path = Path(previous_path)
    if output.exists(): raise ValueError('output_exists_no_overwrite')
    hashes = {}; plan = _load(plan_path, hashes); previous = _load(previous_path / 'report.json', hashes)
    if (previous.get('complete') is not True or previous.get('inputs_unchanged') is not True or
        previous.get('snapshots_unchanged') is not True or previous.get('failed_rechecks') or
        previous.get('source_labels_used') is not False or previous.get('accuracy_measured') is not False):
        raise ValueError('invalid_previous_case_audit')
    packages = {p['pair_id']: p for p in plan['packages']}
    if len(packages) != len(plan['packages']) or len(packages) != previous['frozen_packages']:
        raise ValueError('frozen_package_coverage_mismatch')
    for package in packages.values(): validate_policy(package['source']['manifest_entry'])
    # Freeze every consumed original, including labels as bytes only; no labels
    # enter the mapping, correction selection or local cursor/geometry checks.
    parents = {}; sources = {}
    for pair, package in packages.items():
        source = package['source']; entry = source['manifest_entry']; path = entry['score_source_path']
        if source['source_files'].get(path) != entry['score_sha256']:
            raise ValueError('score_path_not_frozen_in_source_files')
        for name, expected in source['source_files'].items():
            if digest(name) != expected: raise ValueError('source_file_hash_mismatch:' + name)
            hashes[str(Path(name).resolve())] = expected
        parents[pair] = _load(source['frozen_ir_path'], hashes, source['ir_sha256'])
        if parents[pair]['ir_document_id'] != entry['ir_document_id'] or parents[pair]['score']['score_id'] != entry['score_id']:
            raise ValueError('manifest_parent_identity_mismatch')
        if digest(source['original_ir_path']) != source['ir_sha256']: raise ValueError('original_ir_hash_mismatch')
        hashes[str(Path(source['original_ir_path']).resolve())] = source['ir_sha256']
        _load(source['preparation_path'], hashes, source['preparation_sha256'])
        if digest(path) != entry['score_sha256']: raise ValueError('source_score_hash_mismatch')
        sources[pair] = Path(path)
    oldcases = []; sample_keys = set(); output_names = set()
    for row in previous['records']:
        key = (row['pair_id'], row['sample_id'], row['plan_index'])
        if key in sample_keys: raise ValueError('duplicate_case_sample_identity')
        sample_keys.add(key)
        name = Path(row['artifact']).name
        if name in output_names: raise ValueError('duplicate_case_output_basename')
        output_names.add(name)
        case = _load(row['artifact'], hashes, row['sha256'], compressed=True)
        if row['pair_id'] not in packages or case['sample']['sample_id'] != row['sample_id']:
            raise ValueError('case_identity_mismatch')
        snapshot = case['source_snapshot']; source = packages[row['pair_id']]['source']
        if (snapshot['manifest_entry'] != source['manifest_entry'] or snapshot['canonical_ir_sha256'] != source['ir_sha256'] or
            snapshot['source_xml_sha256'] != source['manifest_entry']['score_sha256']):
            raise ValueError('case_snapshot_policy_mismatch')
        for field in ('source_xml', 'canonical_ir'):
            if digest(snapshot[field]) != snapshot[field + '_sha256']: raise ValueError('case_snapshot_hash_mismatch')
            hashes[str(Path(snapshot[field]).resolve())] = snapshot[field + '_sha256']
        oldcases.append((row, case))
    if len(oldcases) != previous['supported_samples']: raise ValueError('case_sample_coverage_mismatch')
    hashes[str(SCHEMA.resolve())] = digest(SCHEMA)
    code = {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob('*.py')}
    contract = {'version': VERSION, 'revision_version': REVISION_VERSION, 'input_hashes': hashes, 'code_hashes': code,
                'frozen_plan': str(Path(plan_path).resolve()), 'previous_case_audit': str(previous_path.resolve()),
                'selection': 'all frozen packages; all previous supported case contexts retained including blocked candidates',
                'source_labels_used': False, 'split_rights_changed': False, 'production_modified': False,
                'annotation_retargeted': False, 'gold_promoted': False, 'training_promoted': False,
                'external_transmission': False, 'engine_recomputed': False, 'gate_changed': False}
    output.mkdir(parents=True, exist_ok=False); _write(output / 'run-contract.json', contract)
    records = []; revisions = {}; snapshots = {}; artifact_hashes = {}; started = perf_counter()
    before_counts = Counter(); after_counts = Counter(); blocked_after_counts = Counter(); mapping_counts = Counter(); checks = Counter()
    fixed = []; disagreements = 0
    for number, (pair, package) in enumerate(packages.items(), 1):
        old = parents[pair]; candidate, repair = revise(old, sources[pair])
        folder = output / 'sources' / hashlib.sha256(pair.encode()).hexdigest()[:20]; folder.mkdir(parents=True)
        # Preserve raw bytes: not the renderer's XML with replaced note IDs.
        source_bytes = sources[pair].read_bytes(); parent_path = Path(package['source']['frozen_ir_path'])
        (folder / 'source.musicxml').write_bytes(source_bytes)
        (folder / 'parent_ir.json').write_bytes(parent_path.read_bytes())
        bcounts = Counter(r['status'] for r in repair['before_checks'].values())
        acounts = Counter(r['status'] for r in repair['after_checks'].values())
        before_counts.update(bcounts)
        if candidate is not None: after_counts.update(acounts)
        else: blocked_after_counts.update(acounts)
        mapping = repair.get('mapping', {}); mapping_counts.update({'notes': len(old['note_events']),
            'attempted_notes': len(old['note_events']) if mapping else 0,
            'unattempted_notes': 0 if mapping else len(old['note_events']),
            'mapped': mapping.get('matched_count', 0), 'unmapped': len(mapping.get('unmatched_ir_note_ids', []))})
        disagreements += len(mapping.get('voice_hint_disagreements', []))
        current_fixed = [nid for nid, result in repair['before_checks'].items()
                         if result['status'] != 'exact' and repair['after_checks'].get(nid, {}).get('status') == 'exact']
        if candidate is None: current_fixed = []
        fixed.extend({'pair_id': pair, 'note_id': nid} for nid in current_fixed)
        if candidate is not None:
            _write(folder / 'candidate_ir.json', candidate); revisions[pair] = candidate
        repair.update(pair_id=pair, parent_ir_path=str((folder / 'parent_ir.json').resolve()),
                      parent_ir_sha256=package['source']['ir_sha256'], manifest_entry=deepcopy(package['source']['manifest_entry']),
                      pitch_policy=deepcopy(package['source']['pitch_policy']), fixed_note_ids=current_fixed,
                      candidate_ir_path=str((folder / 'candidate_ir.json').resolve()) if candidate else None,
                      candidate_ir_sha256=digest(folder / 'candidate_ir.json') if candidate else None)
        _write(folder / 'revision.json', repair)
        snapshot = {'source_xml': str((folder / 'source.musicxml').resolve()), 'source_xml_sha256': digest(folder / 'source.musicxml'),
                    'parent_ir': repair['parent_ir_path'], 'parent_ir_sha256': repair['parent_ir_sha256'],
                    'candidate_ir': repair['candidate_ir_path'], 'candidate_ir_sha256': repair['candidate_ir_sha256'],
                    'revision': str((folder / 'revision.json').resolve()), 'revision_sha256': digest(folder / 'revision.json')}
        snapshots[pair] = snapshot
        for field in ('source_xml', 'parent_ir', 'candidate_ir', 'revision'):
            if snapshot[field]: artifact_hashes[snapshot[field]] = snapshot[field + '_sha256']
        record = {'pair_id': pair, 'work_family_id': package['source']['manifest_entry']['work_family_id'],
                  'status': repair['status'], 'blockers': repair['blockers'], 'snapshot': snapshot,
                  'before_counts': dict(bcounts), 'after_counts': dict(acounts), 'fixed_notes': len(current_fixed),
                  'changed_source_refs': len(repair['changed_source_ref_ids']) if candidate is not None else 0,
                  'changed_note_notation': len(repair['changed_note_ids']) if candidate is not None else 0,
                  'voice_hint_disagreements': len(mapping.get('voice_hint_disagreements', [])),
                  'unmapped_ir_note_ids': mapping.get('unmatched_ir_note_ids', []),
                  'note_count': len(old['note_events'])}
        records.append(record); checks[repair['status']] += 1
        print(f'[{number}/{len(packages)}] {pair}: {repair["status"]} ({len(current_fixed)} fixed)', flush=True)
    contexts = []; unique = {}; repeated = Counter(); counts = Counter()
    for row, case in oldcases:
        pair = row['pair_id']; candidate = revisions.get(pair)
        if candidate is None:
            contexts.append({'pair_id': pair, 'sample_id': row['sample_id'], 'status': 'candidate_blocked_parent_retained',
                             'parent_artifact': row['artifact'], 'parent_sha256': row['sha256'],
                             'context_count': len(case['group_contexts'])}); counts['blocked_contexts'] += len(case['group_contexts'])
            continue
        raw = source_index(sources[pair].read_bytes()); values = []
        if len(case['group_contexts']) != len(case['groups']): raise ValueError('case_context_group_count_mismatch')
        for group, old_context in zip(case['groups'], case['group_contexts']):
            value = context(candidate, group['span'], raw)
            if _event_projection(old_context) != _event_projection(value): raise ValueError('case_musical_geometry_changed')
            repeated.update(t['status'] for t in value['source_note_trace'])
            for trace in value['source_note_trace']: unique[(pair, trace['note_id'])] = trace['status']
            counts['rechecked_contexts'] += 1
            if not value['source_field_issue_note_ids']: counts['consistent_contexts'] += 1
            values.append(value)
        result = {'version': VERSION, 'record_kind': 'source_locator_context_recheck_not_new_harmony_analysis',
                  'pair_id': pair, 'sample': case['sample'], 'parent_artifact': row['artifact'], 'parent_sha256': row['sha256'],
                  'parent_analysis_ir_document_id': parents[pair]['ir_document_id'],
                  'context_ir_document_id': candidate['ir_document_id'], 'snapshot': snapshots[pair],
                  'group_spans': [g['span'] for g in case['groups']], 'group_contexts': values,
                  'harmonic_analysis_recomputed': False, 'annotation_retargeted': False, 'gate_changed': False}
        dest = output / 'contexts' / Path(row['artifact']).name; dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(gzip.compress(json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode(), mtime=0))
        artifact_hashes[str(dest.resolve())] = digest(dest)
        contexts.append({'pair_id': pair, 'sample_id': row['sample_id'], 'status': 'context_rechecked',
                         'artifact': str(dest.resolve()), 'sha256': digest(dest), 'context_count': len(values)})
    changed_inputs = [name for name, expected in {**hashes, **code}.items() if digest(name) != expected]
    changed_inputs += sorted(set(str(p.resolve()) for p in Path(__file__).parent.glob('*.py')).symmetric_difference(code))
    changed_artifacts = [name for name, expected in artifact_hashes.items() if digest(name) != expected]
    summary = {'packages': len(packages), 'work_families': len({r['work_family_id'] for r in records}),
               'revision_statuses': dict(checks), 'note_mapping': dict(mapping_counts),
               'before_full_score_note_checks': dict(before_counts),
               'before_unchecked_notes': mapping_counts['notes'] - sum(before_counts.values()),
               'after_candidate_note_checks': dict(after_counts),
               'blocked_attempted_after_note_checks': dict(blocked_after_counts),
               'noncandidate_notes': sum(r['note_count'] for r in records if r['status'] != 'candidate_ready'),
               'fixed_note_links': len(fixed), 'voice_hint_disagreements': disagreements,
               'changed_source_refs': sum(r['changed_source_refs'] for r in records),
               'changed_note_notation': sum(r['changed_note_notation'] for r in records),
               'previous_case_samples_retained': len(contexts), 'context_counts': dict(counts),
               'source_trace_counts': dict(repeated), 'unique_source_trace_counts': dict(Counter(unique.values()))}
    report = {'version': VERSION, 'complete': True, 'summary': summary, 'records': records, 'contexts': contexts,
              'fixed_note_refs': fixed, 'changed_input_paths': changed_inputs, 'changed_artifact_paths': changed_artifacts,
              'inputs_unchanged': not changed_inputs, 'artifacts_unchanged': not changed_artifacts,
              'contract_sha256': digest(output / 'run-contract.json'), 'artifact_hashes': artifact_hashes,
              'source_labels_used': False, 'accuracy_measured': False, 'engine_recomputed': False,
              'production_modified': False, 'annotation_retargeted': False, 'gate_changed': False,
              'elapsed_seconds': perf_counter() - started,
              'limits': ['Complete note mapping is not source-voice or harmonic certification.',
                         'Rest/source global times/repeats/concert pitch and unlisted notation stay on the parent contract.',
                         'All old source annotations and harmonic analyses remain bound to the parent revision.',
                         'Blocked packages are preserved, not silently dropped or partially published.']}
    if (mapping_counts['attempted_notes'] + mapping_counts['unattempted_notes'] != mapping_counts['notes'] or
        mapping_counts['mapped'] + mapping_counts['unmapped'] != mapping_counts['attempted_notes'] or
        summary['before_unchecked_notes'] < 0 or sum(after_counts.values()) + summary['noncandidate_notes'] != mapping_counts['notes'] or
        counts['rechecked_contexts'] + counts['blocked_contexts'] != sum(len(c['group_contexts']) for _, c in oldcases)):
        raise ValueError('trial_coverage_partition_mismatch')
    _write(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path); parser.add_argument('--previous', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(); report = run(args.plan, args.previous, args.output)
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    if not report['inputs_unchanged'] or not report['artifacts_unchanged']: raise SystemExit(1)


if __name__ == '__main__': main()
