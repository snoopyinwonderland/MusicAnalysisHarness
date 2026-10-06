"""Frozen disk-backed replay contracts; previous revisions stay immutable."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import source_sequence_replay_trial as trial
from musicanote_harness import source_locator_revision_trial as locator
from test_source_locator_revision_trial import frozen_inputs, read_json, write_json, sha


def inputs(root, with_case=False):
    data = frozen_inputs(root, with_case=with_case)
    locator.run(data['plan'], data['previous'], data['output'])
    data['locator'] = data['output']; data['output'] = root / 'replay'
    return data


class SourceSequenceReplayTrialTests(unittest.TestCase):
    def run_fixture(self, data): return trial.run(data['plan'], data['locator'], data['output'])

    def test_actual_replay_preserves_all_inputs_and_old_revision_bindings(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp), with_case=True)
            before = {p: p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}
            result = self.run_fixture(data)
            self.assertTrue(result['complete']); self.assertTrue(result['inputs_and_code_unchanged'])
            self.assertTrue(result['artifacts_unchanged'])
            self.assertEqual(result['summary']['replay_statuses'], {'complete_replay': 1})
            self.assertEqual(result['summary']['previous_case_samples_retained'], 1)
            previous = read_json(data['locator'] / 'report.json')
            self.assertEqual(result['previous_contexts'], previous['contexts'])
            self.assertEqual(result['summary']['previous_locator_candidates_retained'], previous['summary']['revision_statuses'])
            for name, payload in before.items(): self.assertEqual(name.read_bytes(), payload)
            for field in ('source_labels_used', 'accuracy_measured', 'independent_occurrence_certified',
                          'core_modified', 'production_modified', 'annotation_retargeted', 'gold_promoted',
                          'training_promoted', 'split_rights_changed', 'external_transmission', 'engine_recomputed', 'gate_changed'):
                self.assertIs(result[field], False)
            row = result['records'][0]; blob = json.loads(gzip.decompress(Path(row['artifact']).read_bytes()))
            self.assertEqual(row['sha256'], sha(row['artifact']))
            self.assertEqual(blob['parent_snapshot'], previous['records'][0]['snapshot'])
            self.assertEqual(blob['replay']['parent_ir_document_id'], data['ir']['ir_document_id'])
            self.assertEqual(len(blob['replay']['observations']), len(data['ir']['note_events']) + len(data['ir']['rest_events']))
            contract = read_json(data['output'] / 'run-contract.json')
            self.assertEqual(result['contract_sha256'], sha(data['output'] / 'run-contract.json'))
            for path, expected in contract['input_hashes'].items(): self.assertEqual(sha(path), expected)

    def test_existing_output_rejected_before_reading_inputs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); marker = root / 'keep'; marker.write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'output_exists_no_overwrite'):
                trial.run(root / 'missing', root / 'missing', root)
            self.assertEqual(marker.read_bytes(), b'keep')

    def test_previous_completion_and_policy_flags_checked(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); path = data['locator'] / 'report.json'; original = read_json(path)
            for field in ('complete', 'inputs_unchanged', 'artifacts_unchanged', 'source_labels_used', 'accuracy_measured', 'production_modified'):
                value = deepcopy(original); value[field] = not value[field]; write_json(path, value)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'invalid_previous_locator_audit'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_previous_contract_hash_is_checked(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); path = data['locator'] / 'run-contract.json'; path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'input_hash_mismatch'): self.run_fixture(data)

    def test_every_previous_artifact_is_hash_guarded_even_if_not_used_for_assignment(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp), with_case=True); previous = read_json(data['locator'] / 'report.json')
            path = Path(previous['contexts'][0]['artifact']); path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'previous_artifact_hash_mismatch'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_frozen_source_and_annotation_bytes_guarded(self):
        for field in ('source', 'labels'):
            with TemporaryDirectory() as tmp:
                data = inputs(Path(tmp)); data[field].write_bytes(data[field].read_bytes() + b' ')
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'source_file_hash_mismatch'):
                    self.run_fixture(data)

    def test_original_frozen_and_preparation_bytes_guarded(self):
        for field, error in (('original', 'original_ir_hash_mismatch'), ('frozen', 'input_hash_mismatch'), ('prep', 'input_hash_mismatch')):
            with TemporaryDirectory() as tmp:
                data = inputs(Path(tmp)); data[field].write_bytes(data[field].read_bytes() + b' ')
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, error): self.run_fixture(data)

    def test_protected_split_and_non_boolean_approval_rejected(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); original = read_json(data['plan'])
            for split, rights, error in (('holdout', True, 'protected_or_unassigned_split'),
                                         ('train', 1, 'internal_research_not_approved')):
                value = deepcopy(original); entry = value['packages'][0]['source']['manifest_entry']
                entry['split'] = split; entry['rights']['internal_research_use'] = rights; write_json(data['plan'], value)
                with self.subTest(split=split, rights=rights), self.assertRaisesRegex(ValueError, error): self.run_fixture(data)

    def test_duplicate_missing_or_unknown_package_never_silently_dropped(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); original = read_json(data['plan'])
            for mode in ('duplicate', 'empty', 'different'):
                value = deepcopy(original)
                if mode == 'duplicate': value['packages'] *= 2
                elif mode == 'empty': value['packages'] = []
                else: value['packages'][0]['pair_id'] = 'other'
                write_json(data['plan'], value)
                with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'frozen_package_coverage_mismatch'):
                    self.run_fixture(data)

    def test_score_path_must_be_frozen(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); plan = read_json(data['plan'])
            del plan['packages'][0]['source']['source_files'][str(data['source'])]; write_json(data['plan'], plan)
            with self.assertRaisesRegex(ValueError, 'score_path_not_frozen'): self.run_fixture(data)

    def test_parent_identity_cannot_be_substituted(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); plan = read_json(data['plan'])
            plan['packages'][0]['source']['manifest_entry']['ir_document_id'] = 'other'; write_json(data['plan'], plan)
            with self.assertRaisesRegex(ValueError, 'parent_identity_mismatch'): self.run_fixture(data)

    def test_self_consistent_prior_snapshot_cannot_change_source_identity(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); path = data['locator'] / 'report.json'; previous = read_json(path)
            previous['records'][0]['snapshot']['source_xml_sha256'] = '0' * 64; write_json(path, previous)
            with self.assertRaisesRegex(ValueError, 'previous_snapshot_identity_mismatch'): self.run_fixture(data)

    def test_prior_unmapped_inventory_must_be_unique_and_from_parent(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); path = data['locator'] / 'report.json'; original = read_json(path)
            for ids in (['unknown'], [data['ir']['note_events'][0]['note_id']] * 2):
                value = deepcopy(original); value['records'][0]['unmapped_ir_note_ids'] = ids; write_json(path, value)
                with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, 'previous_mapping_inventory_mismatch'):
                    self.run_fixture(data)

    def test_previous_context_inventory_count_not_fabricated(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); path = data['locator'] / 'report.json'; previous = read_json(path)
            previous['summary']['previous_case_samples_retained'] = 1; write_json(path, previous)
            with self.assertRaisesRegex(ValueError, 'previous_context_inventory_mismatch'): self.run_fixture(data)

    def test_partial_replay_keeps_all_exclusions_without_candidate_or_promotion(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); actual = trial.audit
            def partial(old, source):
                value = actual(old, source); row = value['observations'].pop(); value['status'] = 'partial_replay'
                value['rejected'].append({'fingerprint': row['parser']['fingerprint'], 'reason': 'fixture_ambiguous'})
                value['unmatched_source_paths'].append(row['original']['xpath'])
                value['counts']['matched_' + ('notes' if row['kind'] == 'note' else 'rests')] -= 1
                value['counts']['rejected_events'] += 1; value['counts']['unmatched_source_events'] += 1
                return value
            with patch.object(trial, 'audit', side_effect=partial): result = self.run_fixture(data)
            self.assertEqual(result['summary']['replay_statuses'], {'partial_replay': 1})
            self.assertEqual(result['summary']['rejected_reasons'], {'fixture_ambiguous': 1})
            artifact = json.loads(gzip.decompress(Path(result['records'][0]['artifact']).read_bytes()))
            self.assertEqual(len(artifact['replay']['unmatched_source_paths']), 1)
            self.assertFalse(result['core_modified']); self.assertFalse(result['independent_occurrence_certified'])
            self.assertFalse(list(data['output'].rglob('*candidate*')))

    def test_input_changed_during_replay_reported_not_stable_success(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); actual = trial.audit
            def changed(old, source):
                value = actual(old, source); data['labels'].write_bytes(b'outside change'); return value
            with patch.object(trial, 'audit', side_effect=changed): result = self.run_fixture(data)
            self.assertFalse(result['inputs_and_code_unchanged'])
            self.assertIn(str(data['labels'].resolve()), result['changed_input_paths'])

    def test_bad_replay_partition_blocks_final_report(self):
        with TemporaryDirectory() as tmp:
            data = inputs(Path(tmp)); actual = trial.audit
            def bad_count(old, source):
                value = actual(old, source); value['counts']['matched_notes'] += 1; return value
            with patch.object(trial, 'audit', side_effect=bad_count):
                with self.assertRaisesRegex(ValueError, 'full_event_inventory_partition_mismatch'): self.run_fixture(data)
            self.assertFalse((data['output'] / 'report.json').exists())


if __name__ == '__main__': unittest.main()
