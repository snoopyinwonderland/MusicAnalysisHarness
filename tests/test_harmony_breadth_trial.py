import gzip
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from test_harmony_open_candidates import score
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness import harmony_breadth_trial as trial


def policy(stem='K280-1', split='train', collection='mozart-sonatas'):
    return {'manifest_entry_id': 'entry-' + stem, 'corpus_id': 'dcmlab',
            'collection_id': collection, 'score_source_path': stem + '.musicxml',
            'work_family_id': 'family-' + stem.split('-')[0],
            'work_family_confidence': 'derived_conservative', 'movement_id': '1',
            'score_id': 'score-' + stem, 'ir_document_id': 'ir-' + stem,
            'score_sha256': 'a' * 64, 'annotation_sha256': 'b' * 64,
            'split': split, 'rights': {'internal_research_use': True},
            'eligibility': {'automatic_training': False, 'blind_evaluation': split == 'holdout'}}


def track(entry):
    stem = Path(entry['score_source_path']).stem
    return {'pair_id': 'dcml:' + entry['collection_id'] + ':' + stem,
            'score_id': entry['score_id'], 'ir_document_id': entry['ir_document_id'],
            'source_sha256': {'score': entry['score_sha256'], 'harmonies': entry['annotation_sha256']},
            'alignment_eligible': True, 'alignment_quality': 'validated_complete',
            'human_review_status': 'unverified', 'canonical_ir_path': 'unused.json',
            'report_path': 'unused-report.json'}


def planned_ir():
    ir = score([('G4', i, i + 1, 'upper') for i in range(12)] +
               [('C3', i, i + 1, 'bass') for i in range(8)] + [('E4', 0, 12, 'held')])
    ir['score'] = {'score_id': 'synthetic', 'duration_quarters': q(12)}
    ir['parts'] = [{'part_id': 'part1'}]
    ir['measures'][0]['actual_duration_quarter'] = q(12)
    return ir


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def disk_package(root, stem='K280-1', split='train', transpose=False):
    directory = root / stem; directory.mkdir(parents=True)
    xml = directory / (stem + '.musicxml')
    content = '<score-partwise><work><work-title>' + stem + '</work-title></work><part><measure><attributes>'
    if transpose: content += '<transpose><diatonic>1</diatonic><chromatic>2</chromatic></transpose>'
    xml.write_text(content + '</attributes></measure></part></score-partwise>', encoding='utf-8')
    annotation = directory / 'harmonies.tsv'
    # Invalid as JSON: computation may hash this, but must never parse annotation labels.
    annotation.write_text('mc\tchord\n1\tPOISON_REFERENCE_LABEL_' + stem + '\n', encoding='utf-8')
    entry = policy(stem, split)
    entry.update(score_source_path=str(xml), score_sha256=trial.digest(xml),
                 annotation_sha256=trial.digest(annotation))
    item = track(entry); ir = planned_ir()
    ir['score']['score_id'] = entry['score_id']; ir['ir_document_id'] = entry['ir_document_id']
    ir_path = directory / 'canonical_music_ir.json'; write_json(ir_path, ir)
    prep = {'source_paths': {'score': str(xml), 'harmonies': str(annotation)},
            'source_sha256': deepcopy(item['source_sha256']),
            'score_id': entry['score_id'], 'ir_document_id': entry['ir_document_id']}
    report_path = directory / 'preparation_report.json'; write_json(report_path, prep)
    item.update(report_path=str(report_path), canonical_ir_path=str(ir_path))
    return item, entry, ir


def disk_inputs(root, stems=('K280-1',)):
    packages = [disk_package(root, stem) for stem in stems]
    tracks = root / 'tracks.jsonl'
    tracks.write_text('\n'.join(json.dumps(p[0]) for p in packages) + '\n', encoding='utf-8')
    manifest = root / 'manifest.json'; write_json(manifest, {'entries': [p[1] for p in packages]})
    return tracks, manifest, packages


def analyzed(ir, sample):
    return {'summary': {'status': 'ready', 'sample_id': sample['sample_id'],
                        'lane': sample['lane'], 'span': sample['span'],
                        'all_part_event_coverage_verified': True},
            'stages': {'sentinel': 'no_reference_labels'}, 'sample': deepcopy(sample)}


class BreadthTrialTests(unittest.TestCase):
    def test_unique_exact_hash_pair_inherits_train_and_dev_without_promotion(self):
        for split in ('train', 'dev'):
            entry = policy(split=split); item = track(entry)
            saved = deepcopy((item, entry)); result = trial.cohort([item], {'entries': [entry]})
            row = result['rows'][0]
            self.assertTrue(row['replay_eligible']); self.assertEqual(row['blockers'], [])
            self.assertEqual(row['manifest_entry']['split'], split)
            self.assertFalse(row['training_promoted']); self.assertFalse(row['gold_eligible'])
            self.assertFalse(result['policy_changed']); self.assertEqual((item, entry), saved)

    def test_unknown_or_duplicate_exact_pair_is_blocked(self):
        entry = policy(); item = track(entry)
        for entries in ([], [entry, deepcopy(entry)]):
            result = trial.cohort([item], {'entries': entries})
            self.assertFalse(result['rows'][0]['replay_eligible'])
            self.assertIn('unknown_or_nonunique_manifest_hash_pair', result['rows'][0]['blockers'])

    def test_annotation_hash_must_match_not_only_score(self):
        entry = policy(); item = track(entry); item['source_sha256']['harmonies'] = 'c' * 64
        self.assertFalse(trial.cohort([item], {'entries': [entry]})['rows'][0]['replay_eligible'])

    def test_unknown_split_and_holdout_block_even_when_blind_flag_is_true(self):
        for split in (None, 'unknown', 'holdout'):
            entry = policy(split=split)
            result = trial.cohort([track(entry)], {'entries': [entry]})['rows'][0]
            self.assertFalse(result['replay_eligible'])
            self.assertIn('protected_holdout' if split == 'holdout' else 'unknown_split', result['blockers'])

    def test_family_score_and_annotation_conflict_guard(self):
        for key in ('work_family_id', 'score_sha256', 'annotation_sha256'):
            entry = policy(); holdout = policy('K999-1', split='holdout')
            holdout.update(score_sha256='c' * 64, annotation_sha256='d' * 64)
            holdout[key] = entry[key]
            row = trial.cohort([track(entry)], {'entries': [entry, holdout]})['rows'][0]
            self.assertFalse(row['replay_eligible'])
            self.assertIn(key + '_split_conflict', row['blockers'])

    def test_internal_rights_must_be_literal_true(self):
        for right in (False, None, 1, 'true'):
            entry = policy(); entry['rights']['internal_research_use'] = right
            row = trial.cohort([track(entry)], {'entries': [entry]})['rows'][0]
            self.assertFalse(row['replay_eligible'])
            self.assertIn('internal_research_not_approved', row['blockers'])

    def test_alignment_permission_must_be_literal_true(self):
        for value in (False, None, 'false', 1):
            entry = policy(); item = track(entry); item['alignment_eligible'] = value
            row = trial.cohort([item], {'entries': [entry]})['rows'][0]
            self.assertFalse(row['replay_eligible'])

    def test_all_392_inventory_rows_preserved_regardless_policy(self):
        entries = []; tracks = []
        for i in range(392):
            entry = policy('K' + str(300 + i) + '-1', split='train' if i % 3 == 0 else 'holdout')
            entry.update(score_sha256=f'{i:064x}', annotation_sha256=f'{i + 500:064x}')
            item = track(entry)
            if i % 4 == 0: item['alignment_eligible'] = False
            entries.append(entry); tracks.append(item)
        a = trial.cohort(tracks, {'entries': entries})
        self.assertEqual(a['inventory_packages'], 392)
        self.assertEqual(len(a['rows']), 392)
        self.assertEqual({r['pair_id'] for r in a['rows']}, {r['pair_id'] for r in tracks})
        self.assertTrue(all(not r['gold_eligible'] and not r['training_promoted'] for r in a['rows']))

    def test_duplicate_prepared_pair_id_rejected(self):
        entry = policy(); item = track(entry)
        with self.assertRaisesRegex(ValueError, 'duplicate_prepared_pair_id'):
            trial.cohort([item, deepcopy(item)], {'entries': [entry]})

    def test_wrong_manifest_identity_and_unresolved_family_block(self):
        for field, replacement in [('score_id', 'other'), ('ir_document_id', 'other'),
                                   ('collection_id', 'other'), ('work_family_confidence', 'unresolved_work_family')]:
            entry = policy(); item = track(entry); entry[field] = replacement
            row = trial.cohort([item], {'entries': [entry]})['rows'][0]
            self.assertFalse(row['replay_eligible'])

    def test_selection_raw_ir_only_repeat_deterministic_per_lane(self):
        ir = planned_ir(); before = deepcopy(ir)
        a = trial.freeze_score(ir)
        self.assertEqual(a['scope'], {'start': q(0), 'end': q(12)})
        self.assertEqual(a['planned_samples'], 16)
        self.assertEqual([r['selected_lane_indices'] for r in a['lane_inventory']], [[2, 4], [3, 6]])
        self.assertEqual(len(a['selected_samples']), 4)
        ir['annotations'] = [{'label': 'V7/V'}]; ir['phrases'] = [0, 8]; ir['title'] = 'different'
        self.assertEqual(a, trial.freeze_score(ir))
        ir.pop('annotations'); ir.pop('phrases'); ir.pop('title')
        self.assertEqual(ir, before)
        self.assertFalse(a['source_labels_used']); self.assertFalse(a['all_windows_analyzed'])

    def test_invalid_sample_count_and_empty_score(self):
        for n in (0, -1, True, 1.5):
            with self.assertRaises(ValueError): trial.freeze_score(planned_ir(), n)
        ir = planned_ir(); ir['sounding_events'] = []
        self.assertEqual(trial.freeze_score(ir)['status'], 'empty_score')

    def test_missing_lane_and_grace_windows_not_replaced_by_successes(self):
        ir = planned_ir(); ir['sounding_events'][0]['source_note_ids'] = ['missing']
        ir['sounding_events'][1]['span']['end'] = deepcopy(ir['sounding_events'][1]['span']['start'])
        result = trial.freeze_score(ir)
        self.assertTrue(result['skipped_sounds'])
        self.assertGreater(result['planned_samples'], 0)
        self.assertEqual(len(result['selected_samples']), 4)

    def test_real_pipeline_conserves_other_part_sound_evidence(self):
        ir = score([('G4', 0, 1, 'upper'), ('A4', 1, 2, 'upper'), ('B4', 2, 3, 'upper'),
                    ('C3', 0, 3, 'bass'), ('E4', 0, 3, 'held')])
        ir['score'] = {'score_id': 'synthetic', 'duration_quarters': q(3)}
        notes = {n['note_id']: n for n in ir['note_events']}
        notes[ir['sounding_events'][3]['source_note_ids'][0]]['part_id'] = 'other-part'
        sample = trial.freeze_score(ir, 1)['selected_samples'][0]['sample']
        result = trial.analyze_sample(ir, sample)
        self.assertTrue(result['summary']['all_part_event_coverage_verified'])
        self.assertEqual(result['summary']['all_part_event_count'], 5)
        self.assertEqual(result['summary']['all_part_note_time'], q(9))
        self.assertEqual({s['sounding_event_id'] for s in result['stages']['lattice']['events']},
                         {s['sounding_event_id'] for s in ir['sounding_events']})
        self.assertFalse(result['summary']['accuracy_measured'])

    def test_real_continuous_budget_abstention_reaches_final_unchanged(self):
        ir = planned_ir(); sample = trial.freeze_score(ir, 1)['selected_samples'][0]['sample']
        with patch.object(trial.continuous, 'MAX_CONDITION_ASSIGNMENTS', 0):
            result = trial.analyze_sample(ir, sample)
        self.assertEqual(result['summary']['continuous_status'], 'condition_budget_abstention_no_pruning')
        self.assertEqual(result['summary']['lattice_status'], 'baseline_not_ready')
        self.assertEqual(result['stages']['hold_change']['status'], result['stages']['relations']['status'])

    def test_actual_stage_mutating_in_memory_ir_is_rejected(self):
        ir = planned_ir(); sample = trial.freeze_score(ir, 1)['selected_samples'][0]['sample']
        actual = trial.hold_change.run
        def mutate(lattice, survey, canonical):
            result = actual(lattice, survey, canonical)
            canonical['unexpected_mutation'] = True
            return result
        with patch.object(trial.continuous, 'MAX_CONDITION_ASSIGNMENTS', 0), \
             patch.object(trial.hold_change, 'run', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'analyzer_mutated_canonical_ir'):
                trial.analyze_sample(ir, sample)

    def test_real_relation_pair_budget_not_bypassed_with_fake_ready(self):
        ir = score([('C3', 0, 1, 'b'), ('E4', 0, 1, 'l'), ('G4', 0, 1, 'g'), ('B-4', 0, 1, 's'),
                    ('F3', 1, 2, 'b'), ('F4', 1, 2, 'l'), ('A4', 1, 2, 's'), ('C5', 1, 2, 'g'),
                    ('F3', 2, 3, 'b'), ('F4', 2, 3, 'l'), ('A4', 2, 3, 's'), ('C5', 2, 3, 'g')])
        ir['score'] = {'score_id': 'synthetic', 'duration_quarters': q(3)}
        sample = trial.freeze_score(ir, 1)['selected_samples'][0]['sample']
        actual = trial.relations.run
        def limited(lattice, canonical, temporal):
            self.assertTrue(temporal)
            return actual(lattice, canonical, max_pairs=1, temporal=True)
        with patch.object(trial.relations, 'run', side_effect=limited):
            result = trial.analyze_sample(ir, sample)
        self.assertEqual(result['summary']['relation_status'], 'pair_budget_abstention_no_pruning')
        self.assertEqual(result['summary']['status'], 'pair_budget_abstention_no_pruning')
        self.assertEqual(result['summary']['executed_relation_pairs'], 0)

    def test_run_freezes_all_packages_and_plan_before_first_compute(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, packages = disk_inputs(root, ('K280-1', 'K281-1'))
            output = root / 'result'
            original = {p: trial.digest(p) for p in [tracks, manifest] +
                        [Path(package[0][field]) for package in packages for field in ('report_path', 'canonical_ir_path')]}
            def check(ir, sample):
                self.assertEqual(len(list((output / 'sources').glob('*/canonical_music_ir.json'))), 2)
                plan = trial.load(output / 'frozen-plan.json'); contract = trial.load(output / 'run-contract.json')
                self.assertEqual(len(plan['packages']), 2)
                self.assertEqual(trial.digest(output / 'frozen-plan.json'), contract['frozen_plan_sha256'])
                self.assertNotIn('POISON_REFERENCE_LABEL', json.dumps(ir))
                return analyzed(ir, sample)
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                 patch.object(trial, 'analyze_sample', side_effect=check):
                result = trial.run(tracks, manifest, output)
            self.assertEqual(result['frozen_packages'], 2); self.assertEqual(result['executed_windows'], 8)
            self.assertEqual(result['human_reviewed_windows'], 0); self.assertFalse(result['accuracy_measured'])
            self.assertTrue(result['inputs_unchanged'])
            self.assertTrue(all(trial.digest(p) == expected for p, expected in original.items()))
            for row in result['records']:
                artifact = Path(row['artifact'])
                self.assertEqual(trial.digest(artifact), row['sha256'])
                payload = json.loads(gzip.decompress(artifact.read_bytes()))
                self.assertEqual(payload['stages'], {'sentinel': 'no_reference_labels'})

    def test_source_hash_mismatch_preflight_blocks_execution(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, packages = disk_inputs(root)
            Path(packages[0][1]['score_source_path']).write_text('<changed/>', encoding='utf-8')
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                 patch.object(trial, 'analyze_sample') as engine:
                result = trial.run(tracks, manifest, root / 'result')
            engine.assert_not_called(); self.assertEqual(result['frozen_packages'], 0)
            self.assertIn('source_score_hash_changed', result['preflight'][0]['error'])

    def test_annotation_file_hash_change_preflight_blocks_execution(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, packages = disk_inputs(root)
            report = trial.load(Path(packages[0][0]['report_path']))
            Path(report['source_paths']['harmonies']).write_text('changed', encoding='utf-8')
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                 patch.object(trial, 'analyze_sample') as engine:
                result = trial.run(tracks, manifest, root / 'result')
            engine.assert_not_called(); self.assertEqual(result['frozen_packages'], 0)
            self.assertIn('source_harmonies_hash_changed', result['preflight'][0]['error'])

    def test_schema_validation_failure_preflight_blocks_engine(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, _ = disk_inputs(root)
            validator = Mock(); validator.validate.side_effect = ValueError('invalid_synthetic_schema')
            with patch.object(trial, 'Draft202012Validator', return_value=validator), \
                 patch.object(trial, 'analyze_sample') as engine:
                result = trial.run(tracks, manifest, root / 'result')
            engine.assert_not_called(); self.assertEqual(result['frozen_packages'], 0)
            self.assertIn('invalid_synthetic_schema', result['preflight'][0]['error'])

    def test_each_window_uses_independent_copy_of_frozen_ir(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, _ = disk_inputs(root)
            def mutate_local(ir, sample):
                self.assertNotIn('previous_window_mutation', ir)
                ir['previous_window_mutation'] = True
                return analyzed(ir, sample)
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                 patch.object(trial, 'analyze_sample', side_effect=mutate_local):
                result = trial.run(tracks, manifest, root / 'result')
            self.assertEqual(result['executed_windows'], 4)
            self.assertEqual(result['status_counts'], {'ready': 4})
            self.assertTrue(result['inputs_unchanged'])

    def test_unknown_policy_or_rights_are_inventory_only_no_engine(self):
        for mode in ('no_match', 'no_rights', 'holdout'):
            with self.subTest(mode=mode), TemporaryDirectory() as tmp:
                root = Path(tmp); tracks, manifest, packages = disk_inputs(root)
                entry = packages[0][1]
                if mode == 'no_match': entry['annotation_sha256'] = 'c' * 64
                elif mode == 'no_rights': entry['rights']['internal_research_use'] = False
                else: entry['split'] = 'holdout'
                write_json(manifest, {'entries': [entry]})
                with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                     patch.object(trial, 'analyze_sample') as engine:
                    result = trial.run(tracks, manifest, root / 'result')
                engine.assert_not_called(); self.assertEqual(result['frozen_packages'], 0)
                self.assertEqual(result['inventory']['inventory_packages'], 1)

    def test_nonzero_transposition_blocks_not_repaired(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); item, entry, _ = disk_package(root, transpose=True)
            tracks = root / 'tracks.jsonl'; tracks.write_text(json.dumps(item), encoding='utf-8')
            manifest = root / 'manifest.json'; write_json(manifest, {'entries': [entry]})
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                 patch.object(trial, 'analyze_sample') as engine:
                result = trial.run(tracks, manifest, root / 'result')
            engine.assert_not_called(); self.assertEqual(result['frozen_packages'], 0)
            self.assertEqual(result['preflight'][0]['status'], 'source_transposition_blocked')

    def test_source_mutation_during_computation_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, packages = disk_inputs(root)
            original = Path(packages[0][0]['canonical_ir_path'])
            def mutate(ir, sample):
                original.write_text('{}', encoding='utf-8')
                return analyzed(ir, sample)
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                 patch.object(trial, 'analyze_sample', side_effect=mutate):
                result = trial.run(tracks, manifest, root / 'result')
            self.assertFalse(result['inputs_unchanged'])
            self.assertIn(str(original.resolve()), result['changed_input_paths'])

    def test_frozen_plan_mutation_during_computation_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, _ = disk_inputs(root); output = root / 'result'
            def mutate(ir, sample):
                write_json(output / 'frozen-plan.json', {'mutated': True})
                return analyzed(ir, sample)
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()), \
                 patch.object(trial, 'analyze_sample', side_effect=mutate):
                result = trial.run(tracks, manifest, output)
            self.assertFalse(result['inputs_unchanged'])
            self.assertIn(str((output / 'frozen-plan.json').resolve()), result['changed_input_paths'])

    def test_existing_output_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, _ = disk_inputs(root); output = root / 'result'; output.mkdir()
            sentinel = output / 'sentinel'; sentinel.write_text('keep', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'output_exists_no_overwrite'):
                trial.run(tracks, manifest, output)
            self.assertEqual(sentinel.read_text(encoding='utf-8'), 'keep')

    def test_worker_count_guard_rejects_non_integer_or_outside_bound(self):
        for count in (0, -1, 5, True, 1.5, '2'):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'worker_count_must_be_integer_1_to_4'):
                trial.run('absent-tracks', 'absent-manifest', 'absent-output', workers=count)

    def test_actual_two_worker_temp_execution_keeps_sources_and_deterministic_plan(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); tracks, manifest, _ = disk_inputs(root, ('K280-1', 'K281-1'))
            with patch.object(trial, 'Draft202012Validator', return_value=Mock()):
                result = trial.run(tracks, manifest, root / 'result', per_lane=1, workers=2)
            self.assertEqual(result['frozen_packages'], 2)
            self.assertEqual(result['executed_windows'], 4)
            self.assertNotIn('execution_error', result['status_counts'])
            self.assertTrue(result['inputs_unchanged'])
            contract = trial.load(root / 'result' / 'run-contract.json')
            self.assertEqual(contract['workers'], 2)
            planned = trial.load(root / 'result' / 'frozen-plan.json')
            expected = {p['pair_id']: [r['sample']['sample_id'] for r in p['plan']['selected_samples']]
                        for p in planned['packages']}
            observed = {pair: [r['sample_id'] for r in result['records'] if r['pair_id'] == pair]
                        for pair in expected}
            self.assertEqual(expected, observed)


if __name__ == '__main__': unittest.main()
