"""Disk-backed runner guards; no source labels enter revision calculations."""
import gzip
import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from musicanote_harness import source_locator_revision_trial as trial
from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.dcml_import import parse_score_without_imported_harmony
from musicanote_harness.formal_ir import FormalIRAdapter, q
from musicanote_harness.harmony_relation_case_trial import context, source_index
from test_source_locator_revision import XML


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def read_json(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_inputs(root, with_case=True):
    """Tiny actual score, full parent IR, and one frozen padded case."""
    source_path = root / 'source.musicxml'
    source_path.write_text(XML, encoding='utf-8')
    score, _, _ = parse_score_without_imported_harmony(source_path)
    ir = FormalIRAdapter().convert(CanonicalIRBuilder().build(score, source_path), source_path)
    original = root / 'parent_ir.json'; frozen = root / 'frozen_ir.json'
    write_json(original, ir); frozen.write_bytes(original.read_bytes())
    prep = root / 'preparation.json'; write_json(prep, {'source_note_mapping': {'complete': False}})
    labels = root / 'annotations.tsv'; labels.write_bytes(b'labels are frozen bytes, not parsed\n')
    entry = {'split': 'train', 'rights': {'internal_research_use': True,
             'model_training_approved': False, 'external_api_transmission_approved': False},
             'work_family_id': 'family_fixture', 'score_sha256': sha(source_path),
             'score_source_path': str(source_path), 'score_id': ir['score']['score_id'],
             'ir_document_id': ir['ir_document_id']}
    package = {'pair_id': 'fixture:piece:1', 'source': {
        'manifest_entry': entry, 'source_files': {str(source_path): sha(source_path), str(labels): sha(labels)},
        'frozen_ir_path': str(frozen), 'original_ir_path': str(original), 'ir_sha256': sha(original),
        'preparation_path': str(prep), 'preparation_sha256': sha(prep),
        'pitch_policy': {'nonzero_source_transposition': False, 'harmonic_replay_allowed': True}}}
    plan = root / 'frozen-plan.json'; write_json(plan, {'packages': [package]})
    previous = root / 'previous'; previous.mkdir()
    report = {'complete': True, 'inputs_unchanged': True, 'snapshots_unchanged': True,
              'failed_rechecks': [], 'source_labels_used': False, 'accuracy_measured': False,
              'frozen_packages': 1, 'supported_samples': int(with_case), 'records': []}
    case_path = previous / 'case.json.gz'
    if with_case:
        span = {'start': q(0), 'cut': q('1/2'), 'end': q(1)}
        value = {'sample': {'sample_id': 'sample_fixture'},
                 'source_snapshot': {'manifest_entry': deepcopy(entry),
                     'source_xml': str(source_path), 'source_xml_sha256': sha(source_path),
                     'canonical_ir': str(frozen), 'canonical_ir_sha256': sha(frozen)},
                 'groups': [{'span': span}], 'group_contexts': [context(ir, span, source_index(source_path.read_bytes()))]}
        case_path.write_bytes(gzip.compress(json.dumps(value).encode('utf-8'), mtime=0))
        report['records'].append({'pair_id': package['pair_id'], 'sample_id': 'sample_fixture', 'plan_index': 0,
                                 'artifact': str(case_path), 'sha256': sha(case_path)})
    write_json(previous / 'report.json', report)
    return {'plan': plan, 'previous': previous, 'case': case_path, 'source': source_path,
            'original': original, 'frozen': frozen, 'prep': prep, 'labels': labels, 'ir': ir,
            'output': root / 'revision'}


def alter_case(data, update):
    case = json.loads(gzip.decompress(data['case'].read_bytes()))
    update(case)
    data['case'].write_bytes(gzip.compress(json.dumps(case).encode('utf-8'), mtime=0))
    report = read_json(data['previous'] / 'report.json')
    report['records'][0]['sha256'] = sha(data['case'])
    write_json(data['previous'] / 'report.json', report)


class SourceLocatorRevisionTrialTests(unittest.TestCase):
    def run_fixture(self, data):
        return trial.run(data['plan'], data['previous'], data['output'])

    def test_train_and_dev_are_allowed_without_rights_promotion(self):
        for split in ('train', 'dev'):
            entry = {'split': split, 'rights': {'internal_research_use': True},
                     'work_family_id': 'family_fixture', 'score_sha256': 'a' * 64}
            before = deepcopy(entry); trial.validate_policy(entry); self.assertEqual(entry, before)

    def test_protected_unassigned_and_unknown_splits_rejected(self):
        for split in ('holdout', 'blind', 'test', None, '', 'future'):
            entry = {'split': split, 'rights': {'internal_research_use': True},
                     'work_family_id': 'family_fixture', 'score_sha256': 'a' * 64}
            with self.subTest(split=split), self.assertRaisesRegex(ValueError, 'protected_or_unassigned_split'):
                trial.validate_policy(entry)

    def test_rights_must_be_explicit_boolean_true(self):
        for approval in (False, None, 1, 'true'):
            entry = {'split': 'train', 'rights': {'internal_research_use': approval},
                     'work_family_id': 'family_fixture', 'score_sha256': 'a' * 64}
            with self.subTest(approval=approval), self.assertRaisesRegex(ValueError, 'internal_research_not_approved'):
                trial.validate_policy(entry)

    def test_family_and_score_policy_identity_required(self):
        for field in ('work_family_id', 'score_sha256'):
            entry = {'split': 'train', 'rights': {'internal_research_use': True},
                     'work_family_id': 'family_fixture', 'score_sha256': 'a' * 64}
            del entry[field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'missing_frozen_policy_identity'):
                trial.validate_policy(entry)

    def test_existing_output_never_overwritten_before_input_reads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); marker = root / 'keep.txt'; marker.write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'output_exists_no_overwrite'):
                trial.run(root / 'missing', root / 'missing', root)
            self.assertEqual(marker.read_bytes(), b'keep')

    def test_actual_revision_preserves_parent_bytes_and_parent_analysis_binding(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); before = {key: data[key].read_bytes()
                for key in ('plan', 'case', 'source', 'original', 'frozen', 'prep', 'labels')}
            result = self.run_fixture(data)
            self.assertTrue(result['complete']); self.assertTrue(result['inputs_unchanged'])
            self.assertTrue(result['artifacts_unchanged']); self.assertEqual(result['summary']['packages'], 1)
            self.assertEqual(result['summary']['revision_statuses'], {'candidate_ready': 1})
            for field in ('source_labels_used', 'accuracy_measured', 'engine_recomputed',
                          'production_modified', 'annotation_retargeted', 'gate_changed'):
                self.assertIs(result[field], False)
            record = result['records'][0]; snapshot = record['snapshot']
            self.assertEqual(Path(snapshot['parent_ir']).read_bytes(), before['frozen'])
            self.assertEqual(Path(snapshot['source_xml']).read_bytes(), before['source'])
            candidate = read_json(snapshot['candidate_ir'])
            self.assertNotEqual(candidate['ir_document_id'], data['ir']['ir_document_id'])
            for field in ('score', 'parts', 'staves', 'voices', 'measures', 'sounding_events',
                          'tie_chains', 'attack_events', 'chord_onset_groups', 'parser_manifest'):
                self.assertEqual(candidate[field], data['ir'][field])
            ctxrow = result['contexts'][0]
            replay = json.loads(gzip.decompress(Path(ctxrow['artifact']).read_bytes()))
            self.assertEqual(replay['parent_analysis_ir_document_id'], data['ir']['ir_document_id'])
            self.assertEqual(replay['context_ir_document_id'], candidate['ir_document_id'])
            self.assertFalse(replay['harmonic_analysis_recomputed'])
            self.assertEqual(replay['parent_sha256'], sha(data['case']))
            self.assertEqual(replay['group_contexts'][0]['source_fields_status'], 'source_note_fields_rechecked')
            for path, expected in result['artifact_hashes'].items(): self.assertEqual(sha(path), expected)
            for key, value in before.items(): self.assertEqual(data[key].read_bytes(), value)

    def test_empty_supported_case_cohort_is_not_fabricated(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp), with_case=False); result = self.run_fixture(data)
            self.assertEqual(result['summary']['previous_case_samples_retained'], 0)
            self.assertEqual(result['contexts'], []); self.assertFalse(result['accuracy_measured'])

    def test_previous_completion_and_no_accuracy_flags_are_gates(self):
        for field in ('complete', 'inputs_unchanged', 'snapshots_unchanged', 'source_labels_used', 'accuracy_measured'):
            with TemporaryDirectory() as tmp:
                data = frozen_inputs(Path(tmp)); report = read_json(data['previous'] / 'report.json')
                report[field] = not report[field]; write_json(data['previous'] / 'report.json', report)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'invalid_previous_case_audit'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_previous_failed_recheck_blocks_before_output(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); report = read_json(data['previous'] / 'report.json')
            report['failed_rechecks'] = ['example']; write_json(data['previous'] / 'report.json', report)
            with self.assertRaisesRegex(ValueError, 'invalid_previous_case_audit'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_duplicate_or_missing_frozen_package_rejected(self):
        for duplicate in (True, False):
            with TemporaryDirectory() as tmp:
                data = frozen_inputs(Path(tmp)); plan = read_json(data['plan'])
                plan['packages'] = plan['packages'] * 2 if duplicate else []; write_json(data['plan'], plan)
                with self.subTest(duplicate=duplicate), self.assertRaisesRegex(ValueError, 'frozen_package_coverage_mismatch'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_runner_rejects_protected_plan_even_without_supported_cases(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp), with_case=False); plan = read_json(data['plan'])
            plan['packages'][0]['source']['manifest_entry']['split'] = 'holdout'; write_json(data['plan'], plan)
            with self.assertRaisesRegex(ValueError, 'protected_or_unassigned_split'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_source_and_annotation_bytes_are_hash_guarded(self):
        for field in ('source', 'labels'):
            with TemporaryDirectory() as tmp:
                data = frozen_inputs(Path(tmp)); data[field].write_bytes(data[field].read_bytes() + b'changed')
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'source_file_hash_mismatch'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_source_score_path_must_be_inside_the_frozen_source_map(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); plan = read_json(data['plan'])
            del plan['packages'][0]['source']['source_files'][str(data['source'])]
            write_json(data['plan'], plan)
            with self.assertRaisesRegex(ValueError, 'score_path_not_frozen_in_source_files'):
                self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_frozen_ir_original_ir_and_preparation_bytes_are_hash_guarded(self):
        for field, message in (('frozen', 'input_hash_mismatch'), ('original', 'original_ir_hash_mismatch'),
                               ('prep', 'input_hash_mismatch')):
            with TemporaryDirectory() as tmp:
                data = frozen_inputs(Path(tmp)); data[field].write_bytes(data[field].read_bytes() + b' ')
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, message): self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_manifest_parent_document_and_score_identity_are_checked(self):
        for field in ('ir_document_id', 'score_id'):
            with TemporaryDirectory() as tmp:
                data = frozen_inputs(Path(tmp)); plan = read_json(data['plan'])
                plan['packages'][0]['source']['manifest_entry'][field] = 'changed'; write_json(data['plan'], plan)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'manifest_parent_identity_mismatch'):
                    self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_compressed_case_consumed_bytes_must_match_record_hash(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); data['case'].write_bytes(b'not frozen gzip bytes')
            with self.assertRaisesRegex(ValueError, 'input_hash_mismatch'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_matching_byte_hash_does_not_replace_gzip_integrity_check(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); payload = bytearray(data['case'].read_bytes()); payload[-8] ^= 1
            data['case'].write_bytes(payload); report = read_json(data['previous'] / 'report.json')
            report['records'][0]['sha256'] = sha(data['case']); write_json(data['previous'] / 'report.json', report)
            with self.assertRaises((gzip.BadGzipFile, OSError, EOFError)): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_case_sample_identity_and_snapshot_policy_checked(self):
        for kind, message in (('sample', 'case_identity_mismatch'), ('policy', 'case_snapshot_policy_mismatch'),
                              ('irhash', 'case_snapshot_policy_mismatch')):
            with TemporaryDirectory() as tmp:
                data = frozen_inputs(Path(tmp))
                def change(case):
                    if kind == 'sample': case['sample']['sample_id'] = 'different'
                    elif kind == 'policy': case['source_snapshot']['manifest_entry']['split'] = 'dev'
                    else: case['source_snapshot']['canonical_ir_sha256'] = '0' * 64
                alter_case(data, change)
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, message): self.run_fixture(data)
                self.assertFalse(data['output'].exists())

    def test_snapshot_source_bytes_are_hash_checked(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); changed = Path(tmp) / 'changed.musicxml'; changed.write_bytes(b'<bad/>')
            alter_case(data, lambda case: case['source_snapshot'].__setitem__('source_xml', str(changed)))
            with self.assertRaisesRegex(ValueError, 'case_snapshot_hash_mismatch'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_self_consistent_snapshot_cannot_substitute_a_different_score(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); changed = Path(tmp) / 'other.musicxml'
            changed.write_bytes(b'<score-partwise/>')
            def replace(case):
                case['source_snapshot']['source_xml'] = str(changed)
                case['source_snapshot']['source_xml_sha256'] = sha(changed)
            alter_case(data, replace)
            with self.assertRaisesRegex(ValueError, 'case_snapshot_policy_mismatch'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_duplicate_case_identity_is_not_counted_as_another_sample(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); report = read_json(data['previous'] / 'report.json')
            report['records'].append(deepcopy(report['records'][0])); report['supported_samples'] = 2
            write_json(data['previous'] / 'report.json', report)
            with self.assertRaisesRegex(ValueError, 'duplicate_case_sample_identity'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_different_cases_cannot_overwrite_the_same_output_basename(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); report = read_json(data['previous'] / 'report.json')
            other = Path(tmp) / 'other'; other.mkdir(); copy = other / data['case'].name
            copy.write_bytes(data['case'].read_bytes())
            row = deepcopy(report['records'][0]); row.update(plan_index=1, artifact=str(copy))
            report['records'].append(row); report['supported_samples'] = 2
            write_json(data['previous'] / 'report.json', report)
            with self.assertRaisesRegex(ValueError, 'duplicate_case_output_basename'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_sample_count_mismatch_rejected(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); report = read_json(data['previous'] / 'report.json')
            report['supported_samples'] = 2; write_json(data['previous'] / 'report.json', report)
            with self.assertRaisesRegex(ValueError, 'case_sample_coverage_mismatch'): self.run_fixture(data)
            self.assertFalse(data['output'].exists())

    def test_context_geometry_change_is_not_silently_accepted(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); actual_context = trial.context
            def changed(*args):
                value = actual_context(*args); value['note_events'][0]['notated_duration_quarter'] = q(99)
                return value
            with patch.object(trial, 'context', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'case_musical_geometry_changed'): self.run_fixture(data)
            self.assertFalse((data['output'] / 'report.json').exists())

    def test_blocked_revision_keeps_parent_and_case_reference_without_candidate(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); parent = data['frozen'].read_bytes(); case = data['case'].read_bytes()
            def blocked(old, source):
                ids = [note['note_id'] for note in old['note_events']]
                return None, {'status': 'blocked', 'blockers': ['incomplete_or_ambiguous_note_mapping'],
                    'before_checks': {nid: {'status': 'mismatch'} for nid in ids}, 'after_checks': {},
                    'changed_note_ids': [], 'changed_source_ref_ids': [],
                    'mapping': {'matched_count': 0, 'unmatched_ir_note_ids': ids,
                                'voice_hint_disagreements': [], 'complete': False}}
            with patch.object(trial, 'revise', side_effect=blocked): result = self.run_fixture(data)
            self.assertEqual(result['summary']['revision_statuses'], {'blocked': 1})
            record = result['records'][0]; self.assertIsNone(record['snapshot']['candidate_ir'])
            self.assertIsNone(record['snapshot']['candidate_ir_sha256']); self.assertEqual(record['fixed_notes'], 0)
            self.assertEqual(record['blockers'], ['incomplete_or_ambiguous_note_mapping'])
            self.assertEqual(Path(record['snapshot']['parent_ir']).read_bytes(), parent)
            ctx = result['contexts'][0]
            self.assertEqual(ctx['status'], 'candidate_blocked_parent_retained')
            self.assertEqual(ctx['parent_sha256'], sha(data['case'])); self.assertEqual(ctx['context_count'], 1)
            self.assertEqual(result['summary']['context_counts'], {'blocked_contexts': 1})
            self.assertEqual(data['case'].read_bytes(), case)
            self.assertFalse((data['output'] / 'contexts').exists())

    def test_input_mutation_during_revision_is_reported_not_stable_success(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp)); actual_revise = trial.revise
            def mutate(old, source):
                result = actual_revise(old, source); data['labels'].write_bytes(b'outside writer')
                return result
            with patch.object(trial, 'revise', side_effect=mutate): result = self.run_fixture(data)
            self.assertFalse(result['inputs_unchanged'])
            self.assertIn(str(data['labels'].resolve()), result['changed_input_paths'])
            self.assertFalse(result['source_labels_used'])

    def test_blocked_after_independent_recheck_keeps_diagnostics_without_candidate_double_count(self):
        with TemporaryDirectory() as tmp:
            data = frozen_inputs(Path(tmp))
            def blocked(old, source):
                ids = [note['note_id'] for note in old['note_events']]
                return None, {'status': 'blocked', 'blockers': ['independent_source_note_geometry_mismatch'],
                    'before_checks': {nid: {'status': 'exact'} for nid in ids},
                    'after_checks': {nid: {'status': 'mismatch' if i == 0 else 'exact'} for i, nid in enumerate(ids)},
                    'changed_note_ids': [], 'changed_source_ref_ids': [],
                    'mapping': {'matched_count': len(ids), 'unmatched_ir_note_ids': [],
                                'voice_hint_disagreements': [], 'complete': True}}
            with patch.object(trial, 'revise', side_effect=blocked): result = self.run_fixture(data)
            self.assertEqual(result['summary']['revision_statuses'], {'blocked': 1})
            self.assertEqual(result['summary']['after_candidate_note_checks'], {})
            self.assertEqual(sum(result['summary']['blocked_attempted_after_note_checks'].values()),
                             len(data['ir']['note_events']))
            self.assertEqual(result['summary']['noncandidate_notes'], len(data['ir']['note_events']))
            record = result['records'][0]
            self.assertEqual(sum(record['after_counts'].values()), len(data['ir']['note_events']))
            self.assertEqual(record['after_counts']['mismatch'], 1)
            self.assertEqual(record['fixed_notes'], 0); self.assertIsNone(record['snapshot']['candidate_ir'])
            self.assertEqual(result['contexts'][0]['status'], 'candidate_blocked_parent_retained')
            self.assertEqual(result['summary']['context_counts'], {'blocked_contexts': 1})


if __name__ == '__main__': unittest.main()
