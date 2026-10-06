import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from musicanote_harness.harmony_validation_coverage import audit, run, write, digest, _package_identity


def entry(work, movement='1', *, collection='mozart-sonatas', split='train', blind=False):
    return {
        'corpus_id': 'dcmlab', 'collection_id': collection,
        'work_family_id': f'family-{collection}-{work}', 'work_family_source_key': work,
        'movement_id': movement, 'work_family_confidence': 'derived_conservative',
        'score_sha256': f'score-{collection}-{work}-{movement}',
        'annotation_sha256': f'annotation-{collection}-{work}-{movement}',
        'split': split, 'rights': {'internal_research_use': True, 'model_training_approved': False},
        'eligibility': {'blind_evaluation': blind, 'automatic_training': False},
    }


def inputs():
    pilot = entry('K280')
    other = entry('K283')
    track = {'pair_id': 'dcml:mozart-sonatas:K283-1', 'alignment_quality': 'validated_complete',
             'alignment_eligible': True, 'human_review_status': 'unverified',
             'canonical_ir_path': 'other.json', 'report_path': 'report.json',
             'exact_alignments': 4, 'verified_transform_alignments': 2}
    return {
        'latest': {'records': [{'case_id': 'a', 'sample': 0, 'status': 'ready'},
                              {'case_id': 'a', 'sample': 16, 'status': 'ready'}]},
        'shared': {'real': [{'case_id': 'a', 'title': 'pilot', 'samples': 43}]},
        'provenances': {'a': {'manifest_entry': pilot}}, 'tracks': [track],
        'manifest': {'entries': [pilot, other]},
        'identities': {track['pair_id']: other},
    }


class HarmonyValidationCoverageTests(unittest.TestCase):
    def test_python_test_count_does_not_become_works_or_accuracy(self):
        result = audit(**inputs(), unit_test_count=1804)
        self.assertEqual(result['code_tests']['count'], 1804)
        self.assertEqual(result['latest_real_pilot']['unique_movements'], 1)
        self.assertEqual(result['latest_real_pilot']['sample_records'], 2)
        self.assertFalse(result['accuracy_measured'])
        self.assertFalse(result['code_tests']['harmony_accuracy_metric'])

    def test_shared_windows_not_added_to_unique_works(self):
        result = audit(**inputs())
        self.assertEqual(result['earlier_shared_context']['sample_windows'], 43)
        self.assertEqual(result['latest_real_pilot']['unique_work_families'], 1)

    def test_complete_alignment_not_gold_or_training_permission(self):
        result = audit(**inputs())
        member = result['cohort_plan']['selected'][0]['members'][0]
        self.assertEqual(member['human_review_status'], 'unverified')
        self.assertIsNone(member['gold_eligibility'])
        self.assertFalse(member['training_eligibility_promoted'])
        self.assertFalse(member['existing_blind_evaluation_eligibility'])

    def test_same_pilot_family_other_movement_is_excluded(self):
        data = inputs()
        other = entry('K280', '2')
        data['manifest']['entries'].append(other)
        data['identities'][data['tracks'][0]['pair_id']] = other
        result = audit(**data)
        self.assertEqual(result['cohort_plan']['selected'], [])

    def test_unknown_cross_manifest_split_blocks_proposal(self):
        data = inputs()
        data['manifest']['entries'].pop()
        result = audit(**data)
        proposal = result['cohort_plan']['selected'][0]
        self.assertFalse(proposal['internal_development_replay_eligible'])
        self.assertIn('unknown_cross_manifest_split_or_identity', proposal['blockers'])
        self.assertIsNone(proposal['members'][0]['manifest_entry'])

    def test_same_score_but_different_annotation_not_policy_match(self):
        data = inputs()
        data['identities'][data['tracks'][0]['pair_id']] = deepcopy(data['manifest']['entries'][1])
        data['identities'][data['tracks'][0]['pair_id']]['annotation_sha256'] = 'different'
        self.assertFalse(audit(**data)['cohort_plan']['selected'][0]['internal_development_replay_eligible'])

    def test_holdout_is_protected_even_if_blind_flag_true(self):
        data = inputs()
        data['manifest']['entries'][1]['split'] = 'holdout'
        data['manifest']['entries'][1]['eligibility']['blind_evaluation'] = True
        result = audit(**data)
        member = result['cohort_plan']['selected'][0]['members'][0]
        self.assertTrue(member['existing_blind_evaluation_eligibility'])
        self.assertFalse(member['internal_development_replay_eligible'])
        self.assertIn('protected_holdout_not_replayed_by_this_planner', member['blockers'])

    def test_split_conflict_any_movement_blocks_entire_family(self):
        data = inputs()
        data['manifest']['entries'].append(entry('K283', '2', split='holdout'))
        result = audit(**data)
        self.assertIn('work_family_split_conflict', result['cohort_plan']['selected'][0]['blockers'])

    def test_unknown_policy_member_blocks_known_member_family(self):
        data = inputs()
        track2 = {**data['tracks'][0], 'pair_id': 'second'}
        data['tracks'].append(track2)
        data['identities']['second'] = entry('K283', '2')
        proposal = audit(**data)['cohort_plan']['selected'][0]
        self.assertFalse(proposal['internal_development_replay_eligible'])
        self.assertEqual(len(proposal['members']), 2)

    def test_partial_and_quarantined_not_proposed(self):
        for quality in ('validated_partial', 'quarantined'):
            data = inputs()
            data['tracks'][0]['alignment_quality'] = quality
            result = audit(**data)
            self.assertEqual(result['cohort_plan']['selected'], [])
            self.assertEqual(result['prepared_data']['alignment_quality_counts'], {quality: 1})

    def test_no_internal_rights_blocks(self):
        data = inputs()
        data['manifest']['entries'][1]['rights']['internal_research_use'] = False
        self.assertFalse(audit(**data)['cohort_plan']['selected'][0]['internal_development_replay_eligible'])

    def test_deterministic_bounded_known_first_without_policy_mutation(self):
        data = inputs()
        track2 = {**data['tracks'][0], 'pair_id': 'unknown'}
        data['tracks'].insert(0, track2)
        data['identities']['unknown'] = entry('K279')
        original = deepcopy(data)
        result = audit(**data, family_limit=1)
        self.assertEqual(result['cohort_plan']['selected'][0]['work_family_source_key'], 'K283')
        self.assertEqual(data, original)
        data['tracks'].reverse()
        self.assertEqual(result['cohort_plan'], audit(**data, family_limit=1)['cohort_plan'])

    def test_latest_identity_requires_provenance_and_hash_match(self):
        data = inputs()
        data['provenances'] = {}
        with self.assertRaisesRegex(ValueError, 'missing_provenance'):
            audit(**data)
        data = inputs()
        data['provenances']['a']['manifest_entry'] = deepcopy(data['provenances']['a']['manifest_entry'])
        data['provenances']['a']['manifest_entry']['movement_id'] = '2'
        with self.assertRaisesRegex(ValueError, 'identity_not_verified'):
            audit(**data)

    def test_missing_prepared_identity_fails_not_guessed(self):
        data = inputs()
        data['identities'] = {}
        with self.assertRaisesRegex(ValueError, 'identity_missing'):
            audit(**data)

    def test_invalid_metrics_rejected(self):
        for count in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                audit(**inputs(), unit_test_count=count)
        with self.assertRaises(ValueError):
            audit(**inputs(), family_limit=0)

    def test_duplicate_samples_counted_but_not_new_movements(self):
        data = inputs()
        data['latest']['records'].append(data['latest']['records'][0])
        result = audit(**data)['latest_real_pilot']
        self.assertEqual(result['sample_records'], 3)
        self.assertEqual(result['unique_sample_keys'], 2)
        self.assertEqual(result['unique_movements'], 1)

    def test_score_and_annotation_hash_split_conflicts_block(self):
        for field in ('score_sha256', 'annotation_sha256'):
            data = inputs()
            unrelated = entry('K999', split='holdout')
            unrelated[field] = data['manifest']['entries'][1][field]
            data['manifest']['entries'].append(unrelated)
            proposal = audit(**data)['cohort_plan']['selected'][0]
            self.assertFalse(proposal['internal_development_replay_eligible'])
            blocker = 'score_hash_split_conflict' if field == 'score_sha256' else 'annotation_hash_split_conflict'
            self.assertIn(blocker, proposal['blockers'])

    def test_new_family_name_cannot_hide_pilot_hash_overlap(self):
        data = inputs()
        identity = deepcopy(data['identities'][data['tracks'][0]['pair_id']])
        identity['annotation_sha256'] = data['manifest']['entries'][0]['annotation_sha256']
        data['identities'][data['tracks'][0]['pair_id']] = identity
        result = audit(**data)['cohort_plan']
        self.assertEqual(result['selected'], [])
        self.assertEqual(result['excluded_pilot_score_or_annotation_overlap'], [data['tracks'][0]['pair_id']])

    def test_cli_hash_freeze_and_existing_output_refused(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            prepared_root = root / 'prepared' / 'pairs'
            folder = prepared_root / 'mozart-sonatas' / 'K283-1'
            preparation = {'source_paths': {'score': str(root / 'K283-1.musicxml')},
                           'source_sha256': {'score': 'score283', 'harmonies': 'ann283'}}
            identity = _package_identity(folder, prepared_root, preparation)
            other = {**identity, 'split': 'train', 'rights': {'internal_research_use': True},
                     'eligibility': {'blind_evaluation': False}}
            pilot = entry('K280')
            manifest_path = root / 'manifest.json'
            write(manifest_path, {'entries': [pilot, other]})
            prep_path = folder / 'preparation_report.json'
            ir_path = folder / 'canonical_music_ir.json'
            write(prep_path, preparation)
            write(ir_path, {'fixture': True})
            track = {'pair_id': 'dcml:mozart-sonatas:K283-1', 'alignment_quality': 'validated_complete',
                     'alignment_eligible': True, 'human_review_status': 'unverified',
                     'report_path': str(prep_path), 'canonical_ir_path': str(ir_path),
                     'source_sha256': preparation['source_sha256']}
            tracks_path = root / 'prepared' / 'prepared_tracks.jsonl'
            tracks_path.write_text(json.dumps(track), encoding='utf-8')
            shared_path = root / 'shared' / 'report.json'
            snapshot = shared_path.parent / 'real-cases' / 'a' / 'source-snapshot'
            prov_path = snapshot / 'case-provenance.json'
            write(prov_path, {'manifest_entry': pilot})
            write(shared_path, {'real': [{'case_id': 'a', 'samples': 43,
                                         'source_hashes': {'case-provenance.json': digest(prov_path)}}]})
            artifact = root / 'latest' / 'artifact.json'
            write(artifact, {'fixture': True})
            latest_path = artifact.parent / 'report.json'
            write(latest_path, {'records': [{'case_id': 'a', 'sample': 0, 'status': 'ready',
                                            'artifact': str(artifact), 'sha256': digest(artifact)}]})
            output = root / 'output'
            source_hashes = {p: digest(p) for p in (manifest_path, tracks_path, shared_path, latest_path, prep_path, ir_path)}
            result = run(latest_path, shared_path, tracks_path, manifest_path, output)
            self.assertEqual(result['cohort_plan']['selected_internal_replay_eligible_families'], 1)
            self.assertTrue((output / 'run-contract.json').is_file())
            self.assertEqual(source_hashes, {p: digest(p) for p in source_hashes})
            with self.assertRaises(FileExistsError):
                run(latest_path, shared_path, tracks_path, manifest_path, output)



if __name__ == '__main__':
    unittest.main()
