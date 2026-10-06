"""Frozen proposal runner contracts and one real synthetic comparison."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_progression_search_trial as trial
from musicanote_harness.harmony_context_bundle import bundle
from test_harmony_context_bundle import data
from test_source_locator_revision_trial import sha, read_json, write_json


def frozen(root):
    ir, stored, _ = data()
    ir['ir_document_id'] = 'fixture_document'
    ir['score'] = {'score_id': 'fixture_score'}
    b = bundle(ir, stored)
    previous = root / 'previous'; previous.mkdir()
    marker = root / 'labels.tsv'; marker.write_bytes(b'frozen bytes, no label parsing')
    provenance = {'manifest_entry': {'split': 'train', 'rights': {'internal_research_use': True},
        'work_family_id': 'fixture_family', 'score_sha256': 'f' * 64},
        'working_ir_document_id': ir['ir_document_id'], 'source_labels_used': False,
        'extensions_consumed': False, 'annotation_retargeted': False,
        'ir_use_scope': 'note_rest_measure_core_only', 'pitch_policy': {'harmonic_replay_allowed': True}}
    packet = {'pair_id': 'fixture_pair', 'plan_index': 0, 'bundle': b, 'provenance': provenance}
    path = previous / 'sample.json.gz'
    path.write_bytes(gzip.compress(json.dumps(packet).encode(), mtime=0))
    write_json(previous / 'run-contract.json', {'input_hashes': {str(marker.resolve()): sha(marker)}, 'code_hashes': {}})
    report = {'complete': True, 'inputs_and_code_unchanged': True, 'artifacts_unchanged': True,
        'source_labels_used': False, 'accuracy_measured': False, 'production_modified': False,
        'contract_sha256': sha(previous / 'run-contract.json'), 'artifact_hashes': {str(path.resolve()): sha(path)},
        'summary': {'packages': 1, 'samples': 1, 'work_families': 1, 'previous_statuses_retained': {'ready': 1}},
        'measure_revisions': [{'pair_id': 'fixture_pair', 'working_ir_document_id': ir['ir_document_id']}],
        'records': [{'pair_id': 'fixture_pair', 'plan_index': 0, 'sample_id': stored['sample']['sample_id'],
            'status': b['status'], 'previous_status': 'ready', 'summary': deepcopy(b['counts']),
            'working_ir_document_id': ir['ir_document_id'], 'artifact': str(path.resolve()), 'sha256': sha(path)}]}
    write_json(previous / 'report.json', report)
    return {'previous': previous, 'output': root / 'new', 'marker': marker, 'sample': path}


def alter_packet(fixture, callback):
    path = fixture['sample']; packet = json.loads(gzip.decompress(path.read_bytes()))
    callback(packet)
    path.write_bytes(gzip.compress(json.dumps(packet).encode(), mtime=0))
    report_path = fixture['previous'] / 'report.json'; report = read_json(report_path)
    report['records'][0]['sha256'] = sha(path); report['artifact_hashes'][str(path.resolve())] = sha(path)
    write_json(report_path, report)


class ProgressionSearchTrialTests(unittest.TestCase):
    def run_fixture(self, fixture, **kwargs):
        return trial.run(fixture['previous'], fixture['output'], **kwargs)

    def test_real_synthetic_search_comparison_preserves_all_inputs(self):
        with TemporaryDirectory() as tmp:
            fixture = frozen(Path(tmp))
            before = {p: p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}
            report = self.run_fixture(fixture, max_complete_paths=4, per_state_limit=3)
            self.assertTrue(report['complete']); self.assertTrue(report['inputs_and_code_unchanged'])
            self.assertTrue(report['artifacts_unchanged']); self.assertEqual(report['summary']['samples'], 1)
            self.assertEqual(report['summary']['previous_statuses_retained'], {'ready': 1})
            for p, payload in before.items(): self.assertEqual(p.read_bytes(), payload)
            record = report['records'][0]
            packet = json.loads(gzip.decompress(Path(record['artifact']).read_bytes()))
            self.assertEqual(sha(record['artifact']), record['sha256'])
            self.assertIsNone(packet['selected']); self.assertIsNone(packet['search']['selected'])
            self.assertIsNone(packet['joint_comparison']['selected'])
            self.assertGreater(report['summary']['search_counts']['complete_proposals'], 0)
            self.assertEqual(report['summary']['search_counts'],
                {k: v for k, v in packet['search']['search_counts'].items() if type(v) is int})
            self.assertGreater(report['summary']['comparison_counts']['executed_evaluations'], 0)
            for flag in ('source_labels_used', 'accuracy_measured', 'production_modified',
                         'final_harmony_selected', 'confidence_calibrated', 'score_wide_optimization_performed'):
                self.assertIs(report[flag], False)

    def test_no_overwrite_before_any_input_reads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); marker = root / 'keep'; marker.write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'output_exists_no_overwrite'):
                trial.run(root / 'missing', root)
            self.assertEqual(marker.read_bytes(), b'keep')

    def test_previous_flags_and_contract_hash_are_required(self):
        for field in ('complete', 'inputs_and_code_unchanged', 'artifacts_unchanged', 'source_labels_used'):
            with TemporaryDirectory() as tmp:
                fixture = frozen(Path(tmp)); path = fixture['previous'] / 'report.json'; r = read_json(path)
                r[field] = not r[field]; write_json(path, r)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'invalid_previous_context_trial'):
                    self.run_fixture(fixture)
        with TemporaryDirectory() as tmp:
            fixture = frozen(Path(tmp)); path = fixture['previous'] / 'run-contract.json'
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'input_hash_mismatch'): self.run_fixture(fixture)

    def test_every_input_and_artifact_hash_is_checked(self):
        for field in ('marker', 'sample'):
            with TemporaryDirectory() as tmp:
                fixture = frozen(Path(tmp)); path = fixture[field]; path.write_bytes(path.read_bytes() + b' ')
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'input_hash_mismatch'):
                    self.run_fixture(fixture)
                self.assertFalse(fixture['output'].exists())

    def test_source_policy_and_parent_binding_not_reinterpreted(self):
        for kind, expected in (('split', 'protected_or_unassigned_split'),
                               ('rights', 'internal_research_not_approved'),
                               ('binding', 'previous_context_binding_mismatch'),
                               ('extensions', 'previous_scope_or_policy_not_ready')):
            with TemporaryDirectory() as tmp:
                fixture = frozen(Path(tmp))
                def changed(packet):
                    p = packet['provenance']
                    if kind == 'split': p['manifest_entry']['split'] = 'holdout'
                    elif kind == 'rights': p['manifest_entry']['rights']['internal_research_use'] = 1
                    elif kind == 'binding': p['working_ir_document_id'] = 'different'
                    else: p['extensions_consumed'] = True
                alter_packet(fixture, changed)
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, expected): self.run_fixture(fixture)

    def test_duplicate_or_missing_samples_never_shrink_denominator(self):
        for kind in ('duplicate', 'missing'):
            with TemporaryDirectory() as tmp:
                fixture = frozen(Path(tmp)); path = fixture['previous'] / 'report.json'; r = read_json(path)
                r['records'] = r['records'] * 2 if kind == 'duplicate' else []
                write_json(path, r)
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'previous_sample_inventory_mismatch'):
                    self.run_fixture(fixture)

    def test_mutating_search_is_rejected_and_no_complete_report_written(self):
        with TemporaryDirectory() as tmp:
            fixture = frozen(Path(tmp)); actual = trial.search
            def changed(b, **kwargs):
                result = actual(b, **kwargs); b['sample']['sample_id'] = 'changed'; return result
            with patch.object(trial, 'search', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'progression_trial_mutated_previous_bundle'):
                    self.run_fixture(fixture, max_complete_paths=3)
            self.assertFalse((fixture['output'] / 'report.json').exists())

    def test_invalid_budget_not_coerced_to_integer(self):
        with TemporaryDirectory() as tmp:
            fixture = frozen(Path(tmp))
            with self.assertRaisesRegex(ValueError, 'invalid_trial_budget'):
                self.run_fixture(fixture, max_segments=True)
            self.assertFalse(fixture['output'].exists())

    def test_mutating_comparison_is_rejected(self):
        with TemporaryDirectory() as tmp:
            fixture = frozen(Path(tmp)); actual = trial.compare
            def changed(b, proposals, **kwargs):
                result = actual(b, proposals, **kwargs); b['sample']['sample_id'] = 'changed'; return result
            with patch.object(trial, 'compare', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'progression_trial_mutated_previous_bundle'):
                    self.run_fixture(fixture, max_complete_paths=3)
            self.assertFalse((fixture['output'] / 'report.json').exists())


if __name__ == '__main__': unittest.main()
