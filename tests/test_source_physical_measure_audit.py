from copy import deepcopy
import unittest

from musicanote_harness.source_physical_measure_audit import audit


def q(n, d=1):
    return {'numerator': n, 'denominator': d}


def fixture():
    ir = {'ir_document_id': 'parent', 'parts': [{'part_id': 'p', 'source_part_id': 'P1'}],
          'staves': [{'staff_id': 's', 'part_id': 'p', 'staff_number': 1}],
          'measures': [], 'source_references': [], 'note_events': [], 'rest_events': []}
    for i, (mid, label) in enumerate((('dup', '1'), ('dup', '1'), ('third', '2'))):
        ir['measures'].append({'measure_id': mid, 'sequential_measure_index': i,
            'printed_measure_number': label, 'global_start_quarter': q(i),
            'actual_duration_quarter': q(1)})
    grid = [{'part': 'P1', 'measure_index': i + 1, 'label': label,
             'start': str(i), 'duration': '1'} for i, label in enumerate(('1', 'X1', '2'))]
    observations = []
    for eid, kind, mi, local, parent_local, duration, grace in (
            ('n1', 'note', 1, 0, 0, 1, False), ('n2', 'note', 2, 0, 1, 1, False),
            ('r1', 'rest', 2, 0, 1, 1, False), ('g', 'note', 2, 1, 2, 0, True),
            ('n3', 'note', 3, 0, 0, 1, False)):
        event = {kind + '_id': eid, 'source_ref_id': 'ref_' + eid, 'part_id': 'p',
                 'display_staff_id': 's', 'voice_id': 'logical',
                 'measure_id': 'dup' if mi < 3 else 'third',
                 'global_onset_quarter': q(mi - 1 + local), 'onset_in_measure': q(parent_local),
                 'notated_duration_quarter': q(duration)}
        pitch = ('C', '0', 4) if kind == 'note' else None
        if kind == 'note':
            event.update(written_pitch={'step': 'C', 'alter': q(0), 'octave': 4},
                         grace={'is_grace': grace}, tie_role='none')
        ir[kind + '_events'].append(event)
        ir['source_references'].append({'source_ref_id': 'ref_' + eid,
                                       'local_fingerprint': 'fp_' + eid, 'source_xpath': 'stale'})
        token = (str(local), str(duration), pitch, grace, 'none')
        raw = {'part': 'P1', 'measure_index': mi, 'measure_label': grid[mi - 1]['label'],
               'staff': '1', 'voice': '1', 'xpath': 'raw_' + eid, 'source_note_ordinal': 1,
               'token': token, 'global_onset': str(mi - 1 + local),
               'chord_marker': False, 'kind': kind}
        parser = {**deepcopy(raw), 'fingerprint': 'fp_' + eid}
        observations.append({'event_id': eid, 'kind': kind, 'original': raw, 'parser': parser,
                             'occurrence_status': 'unique_token_in_source_lane'})
    return ir, grid, observations


class PhysicalMeasureAuditTests(unittest.TestCase):
    def blocked(self, values, reason):
        r = audit(*values)
        self.assertEqual(r['status'], 'blocked')
        self.assertIn(reason, r['blockers'])
        self.assertFalse(r['mapping_usable_for_migration'])
        self.assertFalse(r['candidate_created'])
        return r

    def test_complete_diagnostic_duplicate_identity_and_local_mismatches(self):
        values = fixture(); before = deepcopy(values); r = audit(*values)
        self.assertEqual(values, before)
        self.assertEqual(r['status'], 'complete_parent_event_mapping')
        self.assertEqual(r['counts']['notes'], 4)
        self.assertEqual(r['counts']['rests'], 1)
        self.assertEqual(r['counts']['verified_event_memberships'], 5)
        self.assertEqual(r['counts']['duplicate_measure_id_groups'], 1)
        self.assertEqual(r['counts']['duplicate_id_event_memberships'], 4)
        self.assertEqual(r['counts']['local_onset_mismatches'], 3)
        self.assertEqual(r['counts']['printed_label_mismatches'], 1)
        self.assertEqual(r['counts']['grace_right_edge_memberships'], 1)
        self.assertTrue(all(type(v) is int for v in r['counts'].values()))

    def test_right_edge_grace_stays_in_verified_previous_physical_measure(self):
        r = audit(*fixture()); events = {e['event_id']: e for e in r['events']}
        self.assertEqual(events['g']['global_onset_quarter'], events['n3']['global_onset_quarter'])
        self.assertEqual(events['g']['resolved_physical_measure_ordinal'], 2)
        self.assertEqual(events['n3']['resolved_physical_measure_ordinal'], 3)

    def test_qualified_alias_never_bare_retarget_or_new_candidate_id(self):
        r = audit(*fixture()); aliases = r['qualified_aliases']
        self.assertEqual([a['key'] for a in aliases[:2]], [
            {'legacy_measure_id': 'dup', 'sequential_measure_index': 0},
            {'legacy_measure_id': 'dup', 'sequential_measure_index': 1}])
        self.assertEqual(aliases[1]['source_measure_label'], 'X1')
        self.assertFalse(r['bare_measure_id_retarget_allowed'])
        self.assertTrue(all(not a['retarget_executable'] for a in aliases))
        self.assertNotIn('candidate_ir_document_id', r)

    def test_partial_mapping_is_not_complete_even_if_grid_is_complete(self):
        ir, grid, obs = fixture(); obs.pop()
        r = audit(ir, grid, obs)
        self.assertEqual(r['status'], 'partial_parent_event_mapping')
        self.assertEqual(r['unmapped_event_ids'], ['n3'])
        self.assertEqual(r['counts']['unmapped_parent_events'], 1)
        self.assertFalse(r['source_event_cardinality_verified'])

    def test_empty_observations_retain_all_parent_events(self):
        ir, grid, _ = fixture(); r = audit(ir, grid, [])
        self.assertEqual(r['status'], 'partial_parent_event_mapping')
        self.assertEqual(r['counts']['unmapped_parent_events'], 5)

    def test_stale_old_xpath_never_selects_physical_membership(self):
        values = fixture(); baseline = audit(*values)
        for ref in values[0]['source_references']: ref['source_xpath'] = '/invented/other/measure'
        r = audit(*values)
        self.assertEqual(r['events'], baseline['events'])

    def test_order_only_occurrence_is_not_independently_certified(self):
        values = fixture(); values[2][0]['occurrence_status'] = 'reproducible_sequence_order_only'
        r = audit(*values)
        self.assertEqual(r['events'][0]['occurrence_status'], 'reproducible_sequence_order_only')
        self.assertFalse(r['events'][0]['independent_occurrence_certified'])
        self.assertFalse(r['independent_occurrence_certified'])

    def test_no_analysis_or_annotation_promotion(self):
        r = audit(*fixture())
        for flag in ('core_modified', 'candidate_created', 'annotation_retargeted',
                     'accuracy_measured', 'gold_promoted', 'training_promoted',
                     'source_labels_used', 'performed_or_concert_time_verified'):
            self.assertIs(r[flag], False)

    def test_missing_raw_physical_measure_blocks_not_partial(self):
        values = fixture(); values[1].pop()
        r = self.blocked(values, 'incomplete_or_extra_source_physical_grid')
        self.assertEqual(r['counts']['unmapped_parent_events'], 5)

    def test_duplicate_raw_physical_measure_blocks(self):
        values = fixture(); values[1].append(deepcopy(values[1][0]))
        self.blocked(values, 'duplicate_source_physical_measure')

    def test_duplicate_ir_sequence_index_blocks(self):
        values = fixture(); values[0]['measures'][1]['sequential_measure_index'] = 0
        self.blocked(values, 'noncontiguous_or_duplicate_measure_sequence')

    def test_fractional_grid_and_event_time_are_exact(self):
        values = fixture(); values[1][0]['start'] = 0.0
        self.blocked(values, 'inexact_or_invalid_time')

    def test_source_grid_timeline_disagreement_blocks(self):
        values = fixture(); values[1][1]['start'] = '3/2'
        self.blocked(values, 'noncontiguous_source_physical_grid')

    def test_parent_grid_time_disagreement_blocks(self):
        values = fixture(); values[0]['measures'][1]['actual_duration_quarter'] = q(2)
        self.blocked(values, 'parent_physical_grid_time_mismatch')

    def test_second_source_part_grid_disagreement_blocks(self):
        ir, grid, obs = fixture()
        ir['parts'].append({'part_id': 'p2', 'source_part_id': 'P2'})
        grid += [{**deepcopy(g), 'part': 'P2', 'label': 'different'} for g in grid]
        self.blocked((ir, grid, obs), 'source_part_physical_grid_disagreement')

    def test_duplicate_observation_blocks_and_keeps_verified_partition(self):
        values = fixture(); values[2].append(deepcopy(values[2][0]))
        r = self.blocked(values, 'duplicate_observed_event_identity')
        self.assertEqual(r['counts']['verified_event_memberships'], 5)
        self.assertEqual(r['counts']['unmapped_parent_events'], 0)

    def test_unknown_observed_event_blocks(self):
        values = fixture(); values[2][0]['event_id'] = 'unknown'
        self.blocked(values, 'unknown_observed_event_identity')

    def test_parent_fingerprint_mismatch_blocks(self):
        values = fixture(); values[2][0]['parser']['fingerprint'] = 'wrong'
        self.blocked(values, 'parent_replay_fingerprint_disagreement')

    def test_raw_parser_measure_index_disagreement_blocks(self):
        values = fixture(); values[2][1]['parser']['measure_index'] = 1
        self.blocked(values, 'replay_physical_measure_disagreement')

    def test_raw_parser_voice_disagreement_blocks(self):
        values = fixture(); values[2][0]['parser']['voice'] = '2'
        self.blocked(values, 'replay_source_voice_disagreement')

    def test_missing_parser_voice_is_retained_not_invented(self):
        values = fixture(); values[2][0]['parser']['voice'] = None
        self.assertEqual(audit(*values)['status'], 'complete_parent_event_mapping')

    def test_raw_parser_token_disagreement_blocks(self):
        values = fixture(); token = list(values[2][0]['parser']['token']); token[1] = '1/2'
        values[2][0]['parser']['token'] = token
        self.blocked(values, 'replay_token_disagreement')

    def test_parent_pitch_disagreement_blocks(self):
        values = fixture(); values[0]['note_events'][0]['written_pitch']['alter'] = q(1, 2)
        self.blocked(values, 'parent_source_pitch_grace_tie_disagreement')

    def test_parent_measure_pointer_disagreement_blocks(self):
        values = fixture(); values[0]['note_events'][0]['measure_id'] = 'third'
        self.blocked(values, 'parent_physical_measure_reference_disagreement')

    def test_source_global_local_disagreement_blocks(self):
        values = fixture()
        for field in ('original', 'parser'): values[2][0][field]['global_onset'] = '1/2'
        self.blocked(values, 'source_global_local_disagreement')

    def test_duplicate_verified_locator_blocks(self):
        values = fixture(); values[2][1]['original']['xpath'] = values[2][0]['original']['xpath']
        self.blocked(values, 'duplicate_verified_source_locator')

    def test_shared_parent_source_ref_blocks(self):
        values = fixture(); values[0]['note_events'][1]['source_ref_id'] = 'ref_n1'
        self.blocked(values, 'shared_event_source_reference')

    def test_wrong_source_staff_blocks(self):
        values = fixture(); values[0]['staves'][0]['staff_number'] = 2
        self.blocked(values, 'parent_source_staff_disagreement')

    def test_split_staff_source_part_is_normalized_not_voice_inferred(self):
        ir, grid, obs = fixture()
        ir['parts'][0]['source_part_id'] = 'P1-Staff2'
        for o in obs:
            o['original']['staff'] = '2'; o['parser']['staff'] = '2'
        r = audit(ir, grid, obs)
        self.assertEqual(r['status'], 'complete_parent_event_mapping')
        self.assertEqual(r['counts']['split_source_staff_normalizations'], 5)
        self.assertEqual(r['events'][0]['parent_staff_number'], 1)
        self.assertEqual(r['events'][0]['source_staff_number'], 2)
        self.assertEqual(ir['staves'][0]['staff_number'], 1)

    def test_split_staff_mismatched_actual_source_staff_blocks(self):
        values = fixture(); values[0]['parts'][0]['source_part_id'] = 'P1-Staff2'
        self.blocked(values, 'parent_source_staff_disagreement')

    def test_bool_physical_ordinal_is_not_one(self):
        values = fixture(); values[1][0]['measure_index'] = True
        self.blocked(values, 'invalid_physical_measure_ordinal')

    def test_bool_parent_sequence_index_is_not_zero(self):
        values = fixture(); values[0]['measures'][0]['sequential_measure_index'] = False
        self.blocked(values, 'noncontiguous_or_duplicate_measure_sequence')

    def test_blank_measure_label_does_not_appear_verified(self):
        values = fixture(); values[1][0]['label'] = ' '
        self.blocked(values, 'invalid_source_measure_label')

    def test_bool_rational_numerator_is_not_one(self):
        values = fixture(); values[0]['measures'][0]['actual_duration_quarter']['numerator'] = True
        self.blocked(values, 'invalid_exact_rational')

    def test_blank_source_voice_is_not_missing_or_explicit(self):
        values = fixture()
        for field in ('original', 'parser'): values[2][0][field]['voice'] = ' '
        self.blocked(values, 'invalid_observation_source_voice')

    def test_bool_source_staff_is_not_one(self):
        values = fixture()
        for field in ('original', 'parser'): values[2][0][field]['staff'] = True
        self.blocked(values, 'invalid_observation_source_staff')

    def test_missing_chord_marker_is_not_assumed_false(self):
        values = fixture()
        for field in ('original', 'parser'): del values[2][0][field]['chord_marker']
        self.blocked(values, 'replay_chord_geometry_disagreement')


if __name__ == '__main__':
    unittest.main()
