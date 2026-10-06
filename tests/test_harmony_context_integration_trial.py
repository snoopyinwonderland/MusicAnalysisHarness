"""Disk-backed integration conserves frozen samples and immutable bindings."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_context_integration_trial as trial
from musicanote_harness import source_sequence_replay_trial as replay_trial
from musicanote_harness.formal_ir import q
from test_source_sequence_replay_trial import inputs
from test_source_locator_revision_trial import read_json, write_json, sha


def frozen_fixture(root):
    """Actual parent XML/replay with two synthetic *stored* evidence outcomes."""
    data = inputs(root, with_case=False)
    replay_trial.run(data['plan'], data['locator'], data['output'])
    data['replay'] = data['output']
    data['output'] = root / 'integrated'
    breadth = root / 'breadth'; breadth.mkdir()
    data['breadth'] = breadth
    plan = read_json(data['plan']); package = plan['packages'][0]
    note = data['ir']['note_events'][0]
    samples = [
        {'sample_id': 'stored_ready', 'lane': {'part_id': note['part_id'], 'voice_id': note['voice_id']},
         'span': {'start': q(0), 'end': q(1)}},
        {'sample_id': 'stored_abstention', 'lane': {'part_id': note['part_id'], 'voice_id': note['voice_id']},
         'span': {'start': q(1), 'end': q(2)}}]
    statuses = ['ready', 'condition_budget_abstention_no_pruning']
    package['plan'] = {'selected_samples': [{'plan_index': i, 'sample': sample}
                                           for i, sample in enumerate(samples)]}
    write_json(breadth / 'frozen-plan.json', plan)
    write_json(breadth / 'run-contract.json', {'fixture': 'frozen evidence, no label parsing',
                                             'frozen_plan_sha256': sha(breadth / 'frozen-plan.json')})
    records = []
    for i, (sample, status) in enumerate(zip(samples, statuses)):
        value = {'sample': deepcopy(sample), 'summary': {'status': status},
                 'stages': {'frozen_sentinel': status}, 'selected': None}
        path = breadth / ('stored-' + str(i) + '.json.gz')
        path.write_bytes(gzip.compress(json.dumps(value).encode('utf-8'), mtime=0))
        records.append({'pair_id': package['pair_id'], 'plan_index': i, 'sample_id': sample['sample_id'],
                        'lane': deepcopy(sample['lane']), 'span': deepcopy(sample['span']),
                        'status': status, 'artifact': str(path), 'sha256': sha(path)})
    report = {'complete': True, 'inputs_unchanged': True, 'source_labels_used': False,
              'accuracy_measured': False, 'frozen_packages': 1, 'executed_windows': 2,
              'status_counts': dict(Counter(statuses)), 'records': records}
    write_json(breadth / 'report.json', report)
    data['samples'] = samples
    return data


def bookkeeping_bundle(ir, stored_sample):
    """Runner test double; deliberately does not imply musical correctness."""
    return {'status': stored_sample['summary']['status'], 'selected': None,
            'ir_document_id': ir['ir_document_id'], 'source_labels_used': False,
            'counts': {'fixture_samples_indexed': 1, 'accuracy_measured': False},
            'stages': deepcopy(stored_sample['stages']),
            'stage_statuses': {'fixture': stored_sample['summary']['status']}}


def replace_plan(data, value):
    """Create a self-consistent fixture contract for downstream guard tests."""
    path = data['breadth'] / 'frozen-plan.json'; write_json(path, value)
    contract_path = data['breadth'] / 'run-contract.json'; contract = read_json(contract_path)
    contract['frozen_plan_sha256'] = sha(path); write_json(contract_path, contract)


class HarmonyContextIntegrationTrialTests(unittest.TestCase):
    def run_fixture(self, data, effect=bookkeeping_bundle):
        with patch.object(trial, 'bundle', side_effect=effect) as engine:
            result = trial.run(data['breadth'], data['replay'], data['output'])
        return result, engine

    def test_all_stored_windows_and_abstentions_retained_without_parent_mutation(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp))
            before = {p: p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}
            result, engine = self.run_fixture(data)
            self.assertEqual(engine.call_count, 2)
            self.assertTrue(result['complete']); self.assertTrue(result['inputs_and_code_unchanged'])
            self.assertTrue(result['artifacts_unchanged'])
            self.assertEqual(result['summary']['packages'], 1)
            self.assertEqual(result['summary']['samples'], 2)
            self.assertEqual(result['summary']['measure_candidates'], 0)
            self.assertEqual(result['summary']['revision_statuses'], {'not_required': 1})
            self.assertEqual(result['summary']['previous_statuses_retained'],
                             read_json(data['breadth'] / 'report.json')['status_counts'])
            self.assertEqual(result['summary']['explicit_complete_paths_requested'], 0)
            self.assertEqual(result['summary']['new_bundle_counts'], {'fixture_samples_indexed': 2})
            for path, payload in before.items(): self.assertEqual(path.read_bytes(), payload)
            revision = result['measure_revisions'][0]
            self.assertIsNone(revision['candidate_ir'])
            self.assertEqual(revision['working_ir_document_id'], data['ir']['ir_document_id'])
            for row in result['records']:
                packet = json.loads(gzip.decompress(Path(row['artifact']).read_bytes()))
                self.assertIsNone(packet['selected']); self.assertIsNone(packet['bundle']['selected'])
                self.assertEqual(packet['provenance']['historical_ir_document_id'], data['ir']['ir_document_id'])
                self.assertEqual(packet['provenance']['working_ir_document_id'], data['ir']['ir_document_id'])
                self.assertFalse(packet['provenance']['extensions_consumed'])
                self.assertFalse(packet['provenance']['annotation_retargeted'])
                self.assertFalse(packet['musical_accuracy_measured'])
            for field in ('source_labels_used', 'accuracy_measured', 'production_modified',
                          'annotation_retargeted', 'gold_promoted', 'training_promoted',
                          'split_rights_changed', 'external_transmission', 'engine_recomputed',
                          'operating_core_modified', 'gate_changed'):
                self.assertIs(result[field], False)
            for path, expected in result['artifact_hashes'].items(): self.assertEqual(sha(path), expected)
            contract = read_json(data['output'] / 'run-contract.json')
            for path, expected in contract['input_hashes'].items(): self.assertEqual(sha(path), expected)

    def test_existing_output_never_overwritten_before_input_reads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); marker = root / 'keep'; marker.write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'output_exists_no_overwrite'):
                trial.run(root / 'absent', root / 'absent', root)
            self.assertEqual(marker.read_bytes(), b'keep')

    def test_invalid_report_flags_block_before_computation(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp))
            for folder, fields, error in (
                ('breadth', ('complete', 'inputs_unchanged', 'source_labels_used', 'accuracy_measured'),
                 'invalid_frozen_breadth_report'),
                ('replay', ('complete', 'inputs_and_code_unchanged', 'artifacts_unchanged',
                            'source_labels_used', 'accuracy_measured', 'production_modified'),
                 'invalid_frozen_replay_report')):
                path = data[folder] / 'report.json'; original = read_json(path)
                for field in fields:
                    value = deepcopy(original); value[field] = not value[field]; write_json(path, value)
                    with self.subTest(folder=folder, field=field), self.assertRaisesRegex(ValueError, error):
                        self.run_fixture(data)
                    self.assertFalse(data['output'].exists())
                    write_json(path, original)

    def test_contract_and_both_artifact_sources_are_hash_guarded(self):
        for kind in ('replay_contract', 'replay_package', 'breadth_sample', 'breadth_plan'):
            with TemporaryDirectory() as tmp:
                data = frozen_fixture(Path(tmp))
                if kind == 'replay_contract': path = data['replay'] / 'run-contract.json'
                elif kind == 'breadth_plan': path = data['breadth'] / 'frozen-plan.json'
                else:
                    folder = data['replay'] if kind == 'replay_package' else data['breadth']
                    path = Path(read_json(folder / 'report.json')['records'][0]['artifact'])
                path.write_bytes(path.read_bytes() + b' ')
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'input_hash_mismatch'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_source_annotation_parent_and_preparation_hashes_guarded(self):
        for field in ('source', 'labels', 'original', 'frozen', 'prep'):
            with TemporaryDirectory() as tmp:
                data = frozen_fixture(Path(tmp)); data[field].write_bytes(data[field].read_bytes() + b' ')
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'input_hash_mismatch'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_holdout_and_non_boolean_internal_approval_rejected(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp)); path = data['breadth'] / 'frozen-plan.json'; original = read_json(path)
            for split, right, error in (('holdout', True, 'protected_or_unassigned_split'),
                                        ('train', 1, 'internal_research_not_approved')):
                value = deepcopy(original); entry = value['packages'][0]['source']['manifest_entry']
                entry['split'] = split; entry['rights']['internal_research_use'] = right; replace_plan(data, value)
                with self.subTest(split=split, right=right), self.assertRaisesRegex(ValueError, error):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_duplicate_or_missing_packages_cannot_shrink_denominator(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp)); path = data['breadth'] / 'frozen-plan.json'; original = read_json(path)
            for packages in ([], original['packages'] * 2):
                value = deepcopy(original); value['packages'] = deepcopy(packages); replace_plan(data, value)
                with self.subTest(packages=len(packages)), self.assertRaisesRegex(ValueError, 'frozen_package_coverage_mismatch'):
                    self.run_fixture(data)

    def test_missing_duplicate_and_unknown_windows_are_rejected(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp)); path = data['breadth'] / 'report.json'; original = read_json(path)
            for mode in ('missing', 'duplicate', 'unknown'):
                value = deepcopy(original)
                if mode == 'missing': value['records'].pop()
                elif mode == 'duplicate': value['records'].append(deepcopy(value['records'][0]))
                else: value['records'][0]['sample_id'] = 'not-in-plan'
                write_json(path, value)
                with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'frozen_sample_coverage_mismatch'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_sample_geometry_and_lane_must_match_frozen_plan(self):
        for mode in ('payload', 'lane', 'span'):
            with TemporaryDirectory() as tmp:
                data = frozen_fixture(Path(tmp)); path = data['breadth'] / 'report.json'; report = read_json(path)
                row = report['records'][0]
                if mode == 'payload':
                    artifact = Path(row['artifact']); stored = json.loads(gzip.decompress(artifact.read_bytes()))
                    stored['sample']['sample_id'] = 'substitute'
                    artifact.write_bytes(gzip.compress(json.dumps(stored).encode(), mtime=0)); row['sha256'] = sha(artifact)
                elif mode == 'lane': row['lane']['voice_id'] = 'another-voice'
                else: row['span']['end'] = q(99)
                write_json(path, report)
                with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'frozen_sample_identity_mismatch'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_changed_annotation_during_bundle_is_reported_not_claimed_stable(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp))
            def changed(ir, stored):
                result = bookkeeping_bundle(ir, stored); data['labels'].write_bytes(b'outside writer')
                return result
            result, _ = self.run_fixture(data, changed)
            self.assertFalse(result['inputs_and_code_unchanged'])
            self.assertIn(str(data['labels'].resolve()), result['changed_input_paths'])
            self.assertFalse(result['source_labels_used'])

    def test_previous_status_inventory_mismatch_prevents_final_success_report(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp)); path = data['breadth'] / 'report.json'; report = read_json(path)
            report['status_counts'] = {'ready': 2}; write_json(path, report)
            with self.assertRaisesRegex(ValueError, 'previous_status_denominator_changed'):
                self.run_fixture(data)
            self.assertFalse((data['output'] / 'report.json').exists())

    def test_literal_pitch_policy_guard_before_replay_and_bundle(self):
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp)); original = read_json(data['breadth'] / 'frozen-plan.json')
            for allowed in (False, None, 1):
                value = deepcopy(original)
                value['packages'][0]['source']['pitch_policy']['harmonic_replay_allowed'] = allowed
                replace_plan(data, value)
                with self.subTest(allowed=allowed), self.assertRaisesRegex(ValueError, 'source_pitch_policy_not_ready'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_real_tiny_pipeline_bundle_keeps_stored_stages_without_selection(self):
        from musicanote_harness import harmony_breadth_trial as breadth_trial
        with TemporaryDirectory() as tmp:
            data = frozen_fixture(Path(tmp))
            selected = breadth_trial.freeze_score(data['ir'], per_lane=1)['selected_samples'][0]
            sample = selected['sample']; stored = breadth_trial.analyze_sample(data['ir'], sample)
            path = data['breadth'] / 'report.json'; report = read_json(path)
            row = report['records'][0]; artifact = Path(row['artifact'])
            artifact.write_bytes(gzip.compress(json.dumps(stored).encode(), mtime=0))
            row.update(sample_id=sample['sample_id'], lane=deepcopy(sample['lane']), span=deepcopy(sample['span']),
                       status=stored['summary']['status'], sha256=sha(artifact))
            report.update(executed_windows=1, records=[row], status_counts={row['status']: 1})
            write_json(path, report)
            plan = read_json(data['breadth'] / 'frozen-plan.json')
            plan['packages'][0]['plan']['selected_samples'] = [{'plan_index': 0, 'sample': sample}]
            replace_plan(data, plan)
            before = data['frozen'].read_bytes()
            result = trial.run(data['breadth'], data['replay'], data['output'])
            self.assertEqual(result['summary']['samples'], 1)
            self.assertEqual(result['summary']['previous_statuses_retained'], {row['status']: 1})
            packet = json.loads(gzip.decompress(Path(result['records'][0]['artifact']).read_bytes()))
            for name, stage in stored['stages'].items(): self.assertEqual(packet['bundle']['stages'][name], stage)
            self.assertEqual(packet['bundle']['status'], 'assembled_diagnostics_not_harmonic_readiness')
            self.assertIsNone(packet['bundle']['selected'])
            self.assertFalse(packet['bundle']['ranking_performed'])
            self.assertFalse(packet['bundle']['harmonic_analysis_confirmed'])
            self.assertEqual(data['frozen'].read_bytes(), before)


if __name__ == '__main__': unittest.main()
