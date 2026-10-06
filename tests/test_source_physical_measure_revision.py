"""Temp-only immutable measure revisions; no local corpus or production writes."""
from copy import deepcopy
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import source_physical_measure_revision as revision
from musicanote_harness import source_sequence_replay_audit as replay
from musicanote_harness.source_physical_measure_audit import audit as physical
from test_source_sequence_replay_audit import make_parent, pitched


def split_xml():
    header = ('<score-partwise version="4.0"><part-list><score-part id="P1">'
              '<part-name>Piano</part-name></score-part></part-list><part id="P1">')
    attributes = ('<attributes><divisions>1</divisions><time><beats>4</beats>'
                  '<beat-type>4</beat-type></time></attributes>')
    return (header + '<measure number="0" implicit="yes">' + attributes + pitched('G', '1') +
            '</measure><measure number="1">' + pitched('C', '3') +
            '</measure><measure number="X1" implicit="yes">' + pitched('E', '1') +
            pitched('F', None, '<grace/>') + pitched('F', None, '<grace/>') +
            '<backup><duration>1</duration></backup><note><rest/><duration>1</duration>'
            '<voice>2</voice><type>quarter</type></note></measure><measure number="2">' +
            pitched('G', '4') + '</measure></part></score-partwise>')


def package_for(parent, source):
    result = replay.audit(parent, source)
    return {'version': revision.PACKAGE_VERSION, 'pair_id': 'synthetic:physical-split',
            'manifest_entry': {'split': 'train', 'rights': {'internal_research_use': True},
                'ir_document_id': parent['ir_document_id'], 'score_id': parent['score']['score_id'],
                'score_sha256': parent['source_files'][0]['sha256']},
            'parent_snapshot': {'source_xml_sha256': parent['source_files'][0]['sha256']},
            'replay': result,
            'physical_measure_audit': physical(parent, result['raw_measures'], result['observations']),
            'source_labels_used': False, 'core_modified': False,
            'annotation_retargeted': False, 'engine_recomputed': False}


def refresh(parent, package):
    """Refresh a synthetic parent binding, not a source fingerprint or raw row."""
    package['replay']['parent_content_sha256'] = revision._hash(parent)
    package['physical_measure_audit'] = physical(parent, package['replay']['raw_measures'],
                                                package['replay']['observations'])


def extension(old_id, name=revision.SOURCE_DIRECTION_NAMESPACE):
    return {'name': name, 'version': '0.1.0', 'owner': 'musicanote-parser',
            'schema_uri': 'https://schemas.musicanote.com/extensions/source-directions/0.1.0',
            'payload': {'directions': [{'measure_id': old_id, 'words': 'tempo observation'}]}}


class PhysicalMeasureRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.source, cls.base = make_parent(cls.temp.name, split_xml())
        cls.package = package_for(cls.base, cls.source)
        if cls.package['replay']['status'] != 'complete_replay':
            raise AssertionError(cls.package['replay']['blockers'])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.parent = deepcopy(self.base)
        self.proof = deepcopy(self.package)
        self.old_id = self.parent['measures'][1]['measure_id']

    def candidate(self):
        new, sidecar = revision.revise(self.parent, self.proof)
        self.assertIsNotNone(new, sidecar)
        self.assertTrue(revision.validate_revision(self.parent, new, sidecar))
        return new, sidecar

    def blocked(self, reason):
        before = revision.canonical_bytes([self.parent, self.proof])
        new, report = revision.revise(self.parent, self.proof)
        self.assertIsNone(new)
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(any(reason in s for s in report['blockers']), report)
        self.assertIsNone(report['candidate_ir_document_id'])
        self.assertNotIn('candidate_content_sha256', report)
        self.assertEqual(revision.canonical_bytes([self.parent, self.proof]), before)

    def test_exact_bounded_correction(self):
        new, s = self.candidate()
        self.assertEqual(s['status'], 'candidate_core_ready')
        self.assertEqual(s['counts']['duplicate_measure_id_groups'], 1)
        self.assertEqual(s['counts']['changed_measure_ids'], 2)
        self.assertEqual(s['counts']['changed_printed_labels'], 1)
        self.assertEqual(s['counts']['changed_event_measure_refs'], 5)
        self.assertEqual(s['counts']['changed_local_onsets'], 4)
        self.assertEqual([m['printed_measure_number'] for m in new['measures']], ['0', '1', 'X1', '2'])
        self.assertEqual(len({m['measure_id'] for m in new['measures']}), 4)
        self.assertNotEqual(new['ir_document_id'], self.parent['ir_document_id'])
        self.assertEqual(s['protected_projection_sha256'], revision._hash(self.parent))
        self.assertEqual(s['candidate_content_sha256'], revision._hash(new))
        self.assertEqual(s['parent_content_sha256'], revision._hash(self.parent))
        self.assertEqual(s['physical_recheck_content_sha256'], revision._hash(self.proof['physical_measure_audit']))

    def test_qualified_aliases_never_bare_retarget(self):
        _, s = self.candidate()
        self.assertEqual([a['key'] for a in s['qualified_measure_aliases']], [
            {'legacy_measure_id': self.old_id, 'sequential_measure_index': 1},
            {'legacy_measure_id': self.old_id, 'sequential_measure_index': 2}])
        self.assertFalse(s['bare_measure_id_retarget_allowed'])
        self.assertTrue(all(a['requires_explicit_revision_selection'] and
                            a['automatic_annotation_retarget'] is False for a in s['qualified_measure_aliases']))

    def test_deterministic_and_input_immutable(self):
        before = revision.canonical_bytes([self.parent, self.proof])
        first, s1 = self.candidate(); second, s2 = self.candidate()
        self.assertEqual(revision.canonical_bytes(first), revision.canonical_bytes(second))
        self.assertEqual(revision.canonical_bytes(s1), revision.canonical_bytes(s2))
        first['measures'][1]['printed_measure_number'] = 'changed caller copy'
        s1['verification_payload']['replay']['counts']['notes'] = -1
        self.assertEqual(revision.canonical_bytes([self.parent, self.proof]), before)

    def test_all_other_core_fields_array_order_and_source_refs_preserved(self):
        new, _ = self.candidate()
        restored = deepcopy(new); restored['ir_document_id'] = self.parent['ir_document_id']
        for i, old in enumerate(self.parent['measures']):
            restored['measures'][i]['measure_id'] = old['measure_id']
            restored['measures'][i]['printed_measure_number'] = old['printed_measure_number']
        for field in ('note_events', 'rest_events'):
            for i, old in enumerate(self.parent[field]):
                restored[field][i]['measure_id'] = old['measure_id']
                restored[field][i]['onset_in_measure'] = old['onset_in_measure']
        self.assertEqual(revision.canonical_bytes(restored), revision.canonical_bytes(self.parent))

    def test_right_edge_grace_uses_source_physical_membership(self):
        new, s = self.candidate()
        graces = [n for n in new['note_events'] if n['grace']['is_grace']]
        self.assertEqual(len(graces), 2)
        for n in graces:
            self.assertEqual(n['global_onset_quarter'], new['measures'][3]['global_start_quarter'])
            self.assertEqual(n['measure_id'], new['measures'][2]['measure_id'])
            self.assertEqual(n['onset_in_measure'], {'numerator': 1, 'denominator': 1})
            self.assertNotEqual(n['measure_id'], new['measures'][3]['measure_id'])
        self.assertEqual(s['counts']['grace_right_edge_memberships_preserved'], 2)

    def test_order_only_occurrences_remain_uncertified_but_allow_membership(self):
        _, s = self.candidate()
        self.assertEqual(s['counts']['order_only_occurrences_retained'], 2)
        self.assertFalse(s['independent_occurrence_certified'])
        rows = [o for o in s['verification_payload']['replay']['observations']
                if o['occurrence_status'] == 'reproducible_sequence_order_only']
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(o['independent_occurrence_certified'] is False for o in rows))

    def test_parent_bound_registered_extension_not_reinterpreted(self):
        self.parent['extensions'].append(extension(self.old_id)); refresh(self.parent, self.proof)
        new, s = self.candidate()
        self.assertEqual(s['status'], 'candidate_core_ready_parent_bound_residuals')
        self.assertEqual(new['extensions'], self.parent['extensions'])
        self.assertEqual(s['counts']['preserved_parent_bound_extension_refs'], 1)
        r = s['preserved_parent_bound_references'][0]
        self.assertEqual(r['value'], self.old_id)
        self.assertEqual(r['parent_ir_document_id'], self.parent['ir_document_id'])
        self.assertEqual(r['binding'], 'preserved_parent_document_only')
        self.assertFalse(r['rebound'])
        self.assertEqual(s['allowed_scope'], 'note_rest_measure_core_only')
        for flag in ('extensions_rebound', 'annotation_retargeted', 'old_analysis_rebound',
                     'standalone_extension_consumption_allowed', 'fully_portable', 'production_ready'):
            self.assertFalse(s[flag], flag)

    def test_optional_extensions_absent_preserved(self):
        del self.parent['extensions']; refresh(self.parent, self.proof)
        new, s = self.candidate()
        self.assertNotIn('extensions', new)
        self.assertEqual(s['extensions_content_sha256'], revision._hash(None))

    def test_unknown_extension_reference_blocks(self):
        self.parent['extensions'].append(extension(self.old_id, 'com.other.observations'))
        refresh(self.parent, self.proof); self.blocked('additional_ambiguous_measure_reference')

    def test_registered_extension_wrong_owner_blocks(self):
        e = extension(self.old_id); e['owner'] = 'another-parser'
        self.parent['extensions'].append(e); refresh(self.parent, self.proof)
        self.blocked('additional_ambiguous_measure_reference')

    def test_core_pickup_duplicate_reference_blocks(self):
        self.parent['score']['pickup_measure'] = self.old_id
        refresh(self.parent, self.proof); self.blocked('additional_ambiguous_measure_reference:/score/pickup_measure')

    def test_other_core_reference_blocks(self):
        self.parent['score'].setdefault('metadata', {})['extra_measure'] = self.old_id
        refresh(self.parent, self.proof); self.blocked('additional_ambiguous_measure_reference')

    def test_parent_hash_mismatch_blocks(self):
        self.proof['replay']['parent_content_sha256'] = '0' * 64
        self.blocked('parent_replay_binding_mismatch')

    def test_document_and_score_bindings_block(self):
        for field in ('ir_document_id', 'score_id'):
            with self.subTest(field=field):
                self.proof = deepcopy(self.package)
                self.proof['manifest_entry'][field] = 'wrong_identity'
                self.blocked('parent_replay_binding_mismatch')

    def test_source_sha_fields_all_checked(self):
        for target, key in (('replay', 'source_sha256'), ('manifest_entry', 'score_sha256'),
                            ('parent_snapshot', 'source_xml_sha256')):
            with self.subTest(target=target):
                self.proof = deepcopy(self.package); self.proof[target][key] = '0' * 64
                self.blocked('frozen_source_binding_mismatch')

    def test_holdout_unknown_split_and_unapproved_rights_block(self):
        for split in ('holdout', 'unknown', None):
            with self.subTest(split=split):
                self.proof = deepcopy(self.package); self.proof['manifest_entry']['split'] = split
                self.blocked('split_rights_gate')
        for value in (False, None, 1, 'true'):
            with self.subTest(rights=value):
                self.proof = deepcopy(self.package)
                self.proof['manifest_entry']['rights']['internal_research_use'] = value
                self.blocked('split_rights_gate')

    def test_dev_explicit_policy_allowed(self):
        self.proof['manifest_entry']['split'] = 'dev'; self.candidate()

    def test_package_and_replay_versions_block(self):
        self.proof['version'] = 'unknown'; self.blocked('unsupported_replay_package_version')
        self.proof = deepcopy(self.package); self.proof['replay']['version'] = 'unknown'
        self.blocked('unsupported_replay_version')

    def test_package_replay_no_promotion_flags_exact_false(self):
        for flag in ('source_labels_used', 'core_modified', 'annotation_retargeted', 'engine_recomputed'):
            with self.subTest(packageflag=flag):
                self.proof = deepcopy(self.package); self.proof[flag] = 0
                self.blocked('unsafe_replay_package_flag')
        for flag in ('core_modified', 'production_modified', 'annotation_retargeted', 'source_labels_used',
                     'accuracy_measured', 'independent_occurrence_certified',
                     'contrapuntal_identity_certified', 'performed_or_concert_time_verified'):
            with self.subTest(replayflag=flag):
                self.proof = deepcopy(self.package); self.proof['replay'][flag] = True
                self.blocked('unsafe_replay_flag')

    def test_incomplete_or_rejected_replay_blocks(self):
        for key, value in (('status', 'partial_replay'), ('fingerprint_reproduced', False),
                           ('blockers', ['unverified']), ('rejected', [{}]),
                           ('unmatched_source_paths', ['/unused'])):
            with self.subTest(key=key):
                self.proof = deepcopy(self.package); self.proof['replay'][key] = value
                self.blocked('complete_verified_replay_required')

    def test_replay_integer_coverage_counts_no_bool(self):
        for key in self.proof['replay']['counts']:
            with self.subTest(key=key):
                self.proof = deepcopy(self.package); self.proof['replay']['counts'][key] = True
                self.blocked('replay_coverage_count_mismatch')

    def test_partial_observation_partition_blocks(self):
        self.proof['replay']['observations'].pop()
        self.blocked('replay_coverage_count_mismatch')

    def test_audit_spoof_blocks(self):
        self.proof['physical_measure_audit']['counts']['local_onset_mismatches'] = 0
        self.blocked('stored_physical_audit_mismatch')

    def test_geometry_timing_pitch_lane_chord_proofs_rechecked(self):
        fields = ('global_onset', 'voice', 'staff', 'chord_marker')
        for field in fields:
            with self.subTest(field=field):
                self.proof = deepcopy(self.package)
                row = self.proof['replay']['observations'][0]['original']
                row[field] = ('999' if field != 'chord_marker' else True)
                # A parser's absent explicit voice can legally match one raw
                # lane; the frozen lane inventory still catches a changed lane.
                self.blocked('replay_lane_inventory_mismatch' if field == 'voice'
                             else 'physical_membership_recheck_blocked')
        self.proof = deepcopy(self.package)
        token = list(self.proof['replay']['observations'][0]['original']['token'])
        token[2] = ['D', '0', 4]
        self.proof['replay']['observations'][0]['original']['token'] = token
        self.blocked('physical_membership_recheck_blocked')

    def test_source_ref_fingerprint_binding_blocks(self):
        self.proof['replay']['observations'][0]['source_ref_id'] = 'wrong_ref'
        self.blocked('replay_source_ref_binding_mismatch')

    def test_parent_observation_metadata_blocks(self):
        for key, value in (('legacy_measure_id', 'wrong_measure'), ('logical_voice_id', 'wrong_voice'),
                           ('parent_onset_in_measure', '99'), ('parent_local_onset_matches_source', 1),
                           ('source_voice_explicit', 1), ('independent_occurrence_certified', True)):
            with self.subTest(key=key):
                self.proof = deepcopy(self.package); self.proof['replay']['observations'][0][key] = value
                self.blocked('replay_parent_observation_metadata_mismatch')

    def test_lane_inventory_and_count_blocks(self):
        for key, value in (('source_events', 2), ('parser_events', True), ('status', 'partial'),
                           ('contrapuntal_identity_certified', True)):
            with self.subTest(key=key):
                self.proof = deepcopy(self.package); self.proof['replay']['lanes'][0][key] = value
                self.blocked('replay_lane_inventory_mismatch')
        self.proof = deepcopy(self.package); self.proof['replay']['lanes'].pop()
        self.blocked('replay_lane_inventory_mismatch')

    def test_uncertified_order_only_cannot_be_promoted(self):
        self.proof['replay']['observations'][0]['occurrence_status'] = 'certified_same_note'
        self.proof['physical_measure_audit'] = physical(self.parent, self.proof['replay']['raw_measures'],
                                                       self.proof['replay']['observations'])
        self.blocked('occurrence_uncertainty_mismatch')

    def test_json_diff_allowlist_exact_and_rational_only(self):
        _, s = self.candidate()
        self.assertTrue(all(d['pointer'] in s['allowed_json_pointers'] or
                            any(d['pointer'].startswith(p + '/') for p in s['allowed_json_pointers'])
                            for d in s['json_pointer_diffs']))
        self.assertNotIn('/note_events/0/global_onset_quarter', s['allowed_json_pointers'])

    def test_validate_rejects_protected_field_changes(self):
        new, s = self.candidate()
        mutations = [lambda n: n['note_events'][0].update(note_id='wrong_note'),
            lambda n: n['note_events'][0]['written_pitch'].update(step='A'),
            lambda n: n['note_events'][0]['global_onset_quarter'].update(numerator=99),
            lambda n: n['note_events'][0]['notated_duration_quarter'].update(numerator=99),
            lambda n: n['note_events'][0].update(voice_id='wrong_voice'),
            lambda n: n['note_events'][0].update(tie_role='start'),
            lambda n: n['note_events'][0]['grace'].update(is_grace=True),
            lambda n: n['source_references'][0].update(source_element_index=99),
            lambda n: n['parser_manifest'].update(parser_version='changed'),
            lambda n: n['note_events'].reverse(),
            lambda n: n['measures'].reverse(),
            lambda n: n['sounding_events'].clear(),
            lambda n: n['attack_events'].clear(),
            lambda n: n['score'].update(pickup_measure=self.old_id)]
        for i, mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                changed = deepcopy(new); mutation(changed)
                with self.assertRaisesRegex(ValueError, 'forbidden_or_incorrect'):
                    revision.validate_revision(self.parent, changed, s)

    def test_validate_rejects_incorrect_allowed_field_values(self):
        new, s = self.candidate()
        for field in ('measure_id', 'printed_measure_number'):
            with self.subTest(field=field):
                changed = deepcopy(new); changed['measures'][2][field] = 'wrong'
                with self.assertRaises(ValueError): revision.validate_revision(self.parent, changed, s)
        changed = deepcopy(new); changed['ir_document_id'] = self.parent['ir_document_id']
        with self.assertRaises(ValueError): revision.validate_revision(self.parent, changed, s)
        changed = deepcopy(new); changed['rest_events'][0]['onset_in_measure']['numerator'] = 2
        with self.assertRaises(ValueError): revision.validate_revision(self.parent, changed, s)

    def test_validate_sidecar_tampering_cannot_widen_contract(self):
        new, s = self.candidate()
        mutations = [lambda c: c['allowed_json_pointers'].append('/note_events'),
            lambda c: c['counts'].update(changed_event_measure_refs=999),
            lambda c: c.update(protected_projection_sha256='0' * 64),
            lambda c: c['qualified_measure_aliases'][0]['key'].update(sequential_measure_index=99),
            lambda c: c.update(annotation_retargeted=True),
            lambda c: c.update(source_file_bytes_rechecked_by_pure_function=True),
            lambda c: c.update(status='production_ready')]
        for i, mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                changed = deepcopy(s); mutation(changed)
                with self.assertRaisesRegex(ValueError, 'sidecar_mismatch'):
                    revision.validate_revision(self.parent, new, changed)

    def test_validate_residual_list_exact_not_editable_or_omittable(self):
        self.parent['extensions'].append(extension(self.old_id)); refresh(self.parent, self.proof)
        new, s = self.candidate()
        for field, value in (('preserved_parent_bound_references', []),
                             ('extensions_rebound', True), ('standalone_extension_consumption_allowed', True)):
            with self.subTest(field=field):
                changed = deepcopy(s); changed[field] = value
                with self.assertRaisesRegex(ValueError, 'sidecar_mismatch'):
                    revision.validate_revision(self.parent, new, changed)

    def test_source_locator_and_harmonic_accuracy_not_certified(self):
        _, s = self.candidate()
        self.assertFalse(s['source_references_residual']['locators_repaired'])
        self.assertFalse(s['source_references_residual']['complete_source_locator_certification'])
        self.assertEqual(s['source_references_residual']['binding'], 'preserved_parent_document_only')
        for flag in ('source_file_bytes_rechecked_by_pure_function', 'source_labels_used', 'accuracy_measured',
                     'gold_promoted', 'training_promoted', 'production_ready', 'fully_portable'):
            self.assertFalse(s[flag], flag)

    def test_no_duplicate_no_candidate_or_new_document(self):
        with TemporaryDirectory() as directory:
            source, parent = make_parent(directory)
            package = package_for(parent, source)
            before = revision.canonical_bytes(parent)
            new, s = revision.revise(parent, package)
            self.assertIsNone(new)
            self.assertEqual(s['status'], 'not_required', s)
            self.assertIsNone(s['candidate_ir_document_id'])
            self.assertEqual(s['counts']['changed_measure_ids'], 0)
            self.assertEqual(s['json_pointer_diffs'], [])
            self.assertEqual(revision.canonical_bytes(parent), before)

    def test_new_measure_id_collision_blocks(self):
        stable = revision.stable_id
        def collided(*args):
            return 'collision' if len(args) == 4 and args[1] == revision.VERSION else stable(*args)
        with patch.object(revision, 'stable_id', side_effect=collided):
            self.blocked('new_measure_id_collision')

    def test_printed_label_change_outside_duplicate_group_blocked(self):
        self.parent['measures'][0]['printed_measure_number'] = 'wrong_nonduplicate_label'
        refresh(self.parent, self.proof)
        self.blocked('label_change_outside_duplicate_measure_group')

    def test_local_onset_change_outside_duplicate_group_blocked(self):
        note = self.parent['note_events'][0]
        note['onset_in_measure'] = {'numerator': 2, 'denominator': 1}
        row = next(o for o in self.proof['replay']['observations'] if o['event_id'] == note['note_id'])
        row['parent_onset_in_measure'] = '2'; row['parent_local_onset_matches_source'] = False
        self.proof['replay']['counts']['local_onset_mismatches'] += 1
        refresh(self.parent, self.proof)
        self.blocked('local_change_outside_duplicate_measure_group')

    def test_literal_fraction_local_onset_no_float(self):
        xml = split_xml().replace('<divisions>1</divisions>', '<divisions>2</divisions>')
        with TemporaryDirectory() as directory:
            source, parent = make_parent(directory, xml)
            package = package_for(parent, source)
            new, s = revision.revise(parent, package)
            self.assertIsNotNone(new, s)
            self.assertTrue(revision.validate_revision(parent, new, s))
            for n in new['note_events']:
                if n['grace']['is_grace']:
                    self.assertEqual(n['onset_in_measure'], {'numerator': 1, 'denominator': 2})
            self.assertEqual(new['measures'][2]['actual_duration_quarter'], {'numerator': 1, 'denominator': 2})

    def test_missing_proof_keys_fail_closed_not_success(self):
        del self.proof['replay']['observations'][0]['source_ref_id']
        self.blocked('source_ref_id')


if __name__ == '__main__':
    unittest.main()
