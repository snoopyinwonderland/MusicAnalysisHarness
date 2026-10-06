"""Integrate frozen harmony evidence without selecting a winning progression.

Only physically verified measure revisions are consumed. Existing engines are
not rerun; common-context features and missing-evidence comparisons are new.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .source_locator_revision_trial import _load, _write, digest, validate_policy
from .source_locator_revision import SCHEMA
from .source_physical_measure_revision import revise, validate_revision, VERSION as REVISION_VERSION
from .harmony_context_bundle import bundle, VERSION as BUNDLE_VERSION

VERSION = 'harmony-context-integration-trial-0.1.0'


def _guard_files(paths, hashes):
    for name, expected in paths.items():
        observed = digest(name)
        if observed != expected:
            raise ValueError('input_hash_mismatch:' + str(name))
        key = str(Path(name).resolve())
        if key in hashes and hashes[key] != observed:
            raise ValueError('input_changed_while_loading:' + key)
        hashes[key] = observed


def _gzip(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    path.write_bytes(gzip.compress(data, mtime=0))


def _sample_key(pair, row):
    return pair, row['plan_index'], row['sample']['sample_id']


def run(breadth_path, replay_path, output):
    breadth_path, replay_path, output = map(Path, (breadth_path, replay_path, output))
    if output.exists():
        raise ValueError('output_exists_no_overwrite')
    hashes = {}
    breadth = _load(breadth_path / 'report.json', hashes)
    replay_report = _load(replay_path / 'report.json', hashes)
    if (breadth.get('complete') is not True or breadth.get('inputs_unchanged') is not True or
            breadth.get('source_labels_used') is not False or breadth.get('accuracy_measured') is not False):
        raise ValueError('invalid_frozen_breadth_report')
    if (replay_report.get('complete') is not True or
            replay_report.get('inputs_and_code_unchanged') is not True or
            replay_report.get('artifacts_unchanged') is not True or
            replay_report.get('source_labels_used') is not False or
            replay_report.get('accuracy_measured') is not False or
            replay_report.get('production_modified') is not False):
        raise ValueError('invalid_frozen_replay_report')
    breadth_contract = _load(breadth_path / 'run-contract.json', hashes)
    _load(replay_path / 'run-contract.json', hashes, replay_report['contract_sha256'])
    _guard_files(replay_report['artifact_hashes'], hashes)
    plan = _load(breadth_path / 'frozen-plan.json', hashes, breadth_contract['frozen_plan_sha256'])
    packages = {p['pair_id']: p for p in plan['packages']}
    replays = {r['pair_id']: r for r in replay_report['records']}
    if (not packages or len(packages) != len(plan['packages']) or
            len(replays) != len(replay_report['records']) or set(packages) != set(replays) or
            breadth['frozen_packages'] != len(packages) or
            replay_report['summary']['packages'] != len(packages)):
        raise ValueError('frozen_package_coverage_mismatch')
    expected = {}
    for pair, package in packages.items():
        for row in package['plan']['selected_samples']:
            key = _sample_key(pair, row)
            if key in expected:
                raise ValueError('duplicate_frozen_sample')
            expected[key] = row['sample']
    stored = {}
    for row in breadth['records']:
        key = row['pair_id'], row['plan_index'], row['sample_id']
        if key not in expected or key in stored:
            raise ValueError('frozen_sample_coverage_mismatch')
        value = _load(row['artifact'], hashes, row['sha256'], compressed=True)
        if (value['sample'] != expected[key] or row['lane'] != expected[key]['lane'] or
                row['span'] != expected[key]['span']):
            raise ValueError('frozen_sample_identity_mismatch')
        stored[key] = (row, value)
    if set(stored) != set(expected) or len(stored) != breadth['executed_windows']:
        raise ValueError('frozen_sample_coverage_mismatch')
    parents, replay_packages = {}, {}
    for pair, package in packages.items():
        info = package['source']; entry = info['manifest_entry']
        validate_policy(entry)
        if info['pitch_policy'].get('harmonic_replay_allowed') is not True:
            raise ValueError('source_pitch_policy_not_ready')
        if info['source_files'].get(entry['score_source_path']) != entry['score_sha256']:
            raise ValueError('score_path_not_frozen')
        _guard_files(info['source_files'], hashes)  # Annotation bytes frozen, labels never read.
        _guard_files({info['original_ir_path']: info['ir_sha256']}, hashes)
        parent = _load(info['frozen_ir_path'], hashes, info['ir_sha256'])
        _load(info['preparation_path'], hashes, info['preparation_sha256'])
        if (parent['ir_document_id'] != entry['ir_document_id'] or
                parent['score']['score_id'] != entry['score_id']):
            raise ValueError('parent_identity_mismatch')
        replay_row = replays[pair]
        replay = _load(replay_row['artifact'], hashes, replay_row['sha256'], compressed=True)
        if (replay['pair_id'] != pair or replay['manifest_entry'] != entry or
                replay['pitch_policy'] != info['pitch_policy']):
            raise ValueError('replay_policy_identity_mismatch')
        snapshot = replay['parent_snapshot']
        if (snapshot['parent_ir_sha256'] != info['ir_sha256'] or
                snapshot['source_xml_sha256'] != entry['score_sha256']):
            raise ValueError('replay_parent_identity_mismatch')
        _guard_files({snapshot['parent_ir']: info['ir_sha256'],
                      snapshot['source_xml']: entry['score_sha256']}, hashes)
        parents[pair], replay_packages[pair] = parent, replay
    hashes[str(SCHEMA.resolve())] = digest(SCHEMA)
    code = {str(p.resolve()): digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    contract = {'version': VERSION, 'bundle_version': BUNDLE_VERSION,
        'measure_revision_version': REVISION_VERSION, 'input_hashes': hashes, 'code_hashes': code,
        'breadth_trial': str(breadth_path.resolve()), 'source_replay_trial': str(replay_path.resolve()),
        'selection': 'every frozen package and selected sample; no new sampling or passing-only subset',
        'reused_stages': ['continuous', 'contrast', 'lattice', 'relations', 'hold_change'],
        'new_computation': ['common reading index', 'member and unexplained note-time',
                            'cellwise observed bass roles', 'missing evidence and conditional NCT links'],
        'path_policy': 'no automatically chosen path; only explicit complete path requests may be evaluated',
        'ir_scope': 'note/rest/measure Core only; revision extensions and historical source locators remain parent-bound',
        'source_labels_used': False, 'accuracy_measured': False, 'production_modified': False,
        'annotation_retargeted': False, 'gold_promoted': False, 'training_promoted': False,
        'split_rights_changed': False, 'external_transmission': False, 'engine_recomputed': False,
        'operating_core_modified': False, 'gate_changed': False}
    output.mkdir(parents=True, exist_ok=False)
    _write(output / 'run-contract.json', contract)
    artifacts, revisions, working = {}, [], {}
    started = perf_counter()
    for pair, parent in parents.items():
        candidate, sidecar = revise(parent, replay_packages[pair])
        target = candidate if candidate is not None else parent
        if candidate is not None:
            validate_revision(parent, candidate, sidecar)
        name = hashlib.sha256(pair.encode()).hexdigest()[:20]
        folder = output / 'measure-revisions' / name
        folder.mkdir(parents=True)
        sidecar_path = folder / 'revision.json'
        _write(sidecar_path, sidecar); artifacts[str(sidecar_path.resolve())] = digest(sidecar_path)
        candidate_path = None
        if candidate is not None:
            candidate_path = folder / 'candidate_ir.json'
            _write(candidate_path, candidate); artifacts[str(candidate_path.resolve())] = digest(candidate_path)
        revisions.append({'pair_id': pair, 'status': sidecar['status'],
            'parent_ir_document_id': parent['ir_document_id'], 'working_ir_document_id': target['ir_document_id'],
            'candidate_created': candidate is not None, 'candidate_ir': str(candidate_path.resolve()) if candidate_path else None,
            'sidecar': str(sidecar_path.resolve()), 'summary': sidecar.get('summary', sidecar.get('counts', {}))})
        working[pair] = target
    rows, statuses, previous_statuses, counts = [], Counter(), Counter(), Counter()
    stage_statuses = {}
    revision_by_pair = {r['pair_id']: r for r in revisions}
    for number, (key, (old_row, value)) in enumerate(stored.items(), 1):
        pair, plan_index, sample_id = key
        result = bundle(working[pair], value)
        for stage, original in value['stages'].items():
            if result['stages'][stage] != original:
                raise ValueError('reused_stage_changed:' + stage)
        packet = {'version': VERSION, 'pair_id': pair, 'plan_index': plan_index,
            'provenance': {'manifest_entry': packages[pair]['source']['manifest_entry'],
                'pitch_policy': packages[pair]['source']['pitch_policy'],
                'historical_ir_document_id': parents[pair]['ir_document_id'],
                'working_ir_document_id': working[pair]['ir_document_id'],
                'measure_revision_sidecar': revision_by_pair[pair]['sidecar'],
                'measure_revision_status': revision_by_pair[pair]['status'],
                'ir_use_scope': 'note_rest_measure_core_only',
                'independent_source_occurrence_certified': False,
                'reused_stage_artifact': old_row['artifact'], 'reused_stage_sha256': old_row['sha256'],
                'source_labels_used': False, 'annotation_retargeted': False,
                'extensions_consumed': False, 'source_locator_revision_applied': False},
            'bundle': result, 'selected': None, 'musical_accuracy_measured': False,
            'production_modified': False}
        name = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:20]
        path = output / 'samples' / (name + '.json.gz')
        _gzip(path, packet); artifacts[str(path.resolve())] = digest(path)
        status = result['status']; statuses[status] += 1
        previous_statuses[old_row['status']] += 1
        summary = result['counts']
        for stage, stage_status in result['stage_statuses'].items():
            stage_statuses.setdefault(stage, Counter())[stage_status] += 1
        for field, count in summary.items():
            if type(count) is int:
                counts[field] += count
        rows.append({'pair_id': pair, 'plan_index': plan_index, 'sample_id': sample_id,
            'previous_status': old_row['status'], 'status': status, 'summary': summary,
            'working_ir_document_id': working[pair]['ir_document_id'],
            'artifact': str(path.resolve()), 'sha256': digest(path)})
        if number % 20 == 0 or number == len(stored):
            print(f'[{number}/{len(stored)}] common-context bundle: {status}', flush=True)
    if dict(previous_statuses) != breadth['status_counts']:
        raise ValueError('previous_status_denominator_changed')
    changed = [p for p, sha in {**hashes, **code}.items() if digest(p) != sha]
    changed += sorted(set(str(p.resolve()) for p in Path(__file__).parent.glob('*.py')).symmetric_difference(code))
    artifact_changed = [p for p, sha in artifacts.items() if digest(p) != sha]
    report = {'version': VERSION, 'complete': True, 'summary': {'packages': len(packages),
        'work_families': len({p['source']['manifest_entry']['work_family_id'] for p in packages.values()}),
        'samples': len(rows), 'measure_candidates': sum(r['candidate_created'] for r in revisions),
        'revision_statuses': dict(Counter(r['status'] for r in revisions)),
        'bundle_statuses': dict(statuses), 'previous_statuses_retained': dict(previous_statuses),
        'stage_statuses_retained': {k: dict(v) for k, v in stage_statuses.items()},
        'new_bundle_counts': dict(counts), 'explicit_complete_paths_requested': 0},
        'measure_revisions': revisions, 'records': rows, 'artifact_hashes': artifacts,
        'contract_sha256': digest(output / 'run-contract.json'),
        'inputs_and_code_unchanged': not changed, 'artifacts_unchanged': not artifact_changed,
        'changed_input_paths': changed, 'changed_artifact_paths': artifact_changed,
        **{field: contract[field] for field in ('source_labels_used', 'accuracy_measured', 'production_modified',
            'annotation_retargeted', 'gold_promoted', 'training_promoted', 'split_rights_changed',
            'external_transmission', 'engine_recomputed', 'operating_core_modified', 'gate_changed')},
        'elapsed_seconds': perf_counter() - started,
        'limits': ['Assembly and conservation success are not musical correctness.',
            'Old candidates, NCT alternatives, budgets and abstentions are retained, not final diagnoses.',
            'No progression has been selected or confidence calibrated.',
            'Measure-only candidates do not retarget annotations, extensions or historical source locators.',
            'No operating score viewer, structural analysis or production engine changes.']}
    _write(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--breadth', required=True)
    parser.add_argument('--replay', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = run(args.breadth, args.replay, args.output)
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    return 0 if report['inputs_and_code_unchanged'] and report['artifacts_unchanged'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
