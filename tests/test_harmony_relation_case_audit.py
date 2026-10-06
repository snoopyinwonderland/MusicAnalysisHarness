import json
import unittest
from copy import deepcopy

from test_harmony_distributed_resolution import fixture as distributed_fixture
from test_harmony_progression_multivoice import fixture as direct_fixture
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_progression_context import plan
from musicanote_harness.harmony_catalog_resolution import pitch_pair
from musicanote_harness.harmony_candidate_relation_survey import local_query
from musicanote_harness.harmony_relation_case_audit import audit_pair, run


def case(delayed=True, specs=None):
    lattice, path, ir = distributed_fixture(specs) if delayed else direct_fixture(return_ir=True)
    pair = {'source': deepcopy(path[0]), 'target': deepcopy(path[1]),
            'family': 'V7', 'target_quality': 'M'}
    item = {**local_query(lattice, pair, ir, temporal=True), 'pair': pair}
    return lattice, item, ir


def sound(lattice, sid):
    return next(event for event in lattice['events'] if event['sounding_event_id'] == sid)


def set_sound_field(lattice, ir, sid, field, value):
    for events in (lattice['events'], ir['sounding_events']):
        event = next(event for event in events if event['sounding_event_id'] == sid)
        event[field] = deepcopy(value)


def outside_local_case(kind):
    lattice, _, ir = direct_fixture(return_ir=True)
    templates = deepcopy(lattice['edges'][0]['readings'])
    for event in ir['sounding_events']:
        event['span'] = {key: q(f(value) + 1) for key, value in event['span'].items()}
    for note in ir['note_events']:
        if 'global_onset_quarter' in note: note['global_onset_quarter'] = q(f(note['global_onset_quarter']) + 1)
    extra = deepcopy(ir['sounding_events'][0]); extra['sounding_event_id'] = 'outside-background'
    extra['source_note_ids'] = ['outside-note']
    extra['span'] = {'start': q(0), 'end': q(1) if kind == 'microtonal' else q('1/2')}
    if kind == 'microtonal':
        extra['pitch'].update(step='D', alter=q('1/2'), octave=4, midi_pitch=62.5, spelling='D+4')
    note = deepcopy(ir['note_events'][0]); note['note_id'] = 'outside-note'
    note['global_onset_quarter'] = q(0); note['notated_duration_quarter'] = deepcopy(extra['span']['end'])
    note['voice_id'] = None if kind == 'missing-lane' else 'background'
    ir['note_events'].append(note); ir['sounding_events'].append(extra)
    lattice['events'] = ir['sounding_events']
    lattice['plan'] = plan(lattice['events'], {'start': q(0), 'end': q(4)})
    lattice['edges'] = []
    for edge in lattice['plan']['intervals']:
        readings = deepcopy(templates)
        for reading in readings:
            reading['span'] = deepcopy(edge['span'])
            reading['event_states'] = {event['sounding_event_id']:
                'member' if pitch_pair(event['pitch']) in reading['members'] else 'nonmember_not_confirmed_nct'
                for event in lattice['events'] if f(event['span']['start']) < f(edge['span']['end'])
                and f(event['span']['end']) > f(edge['span']['start'])}
        lattice['edges'].append({**edge, 'readings': readings})
    lattice['cells'] = [{'span': {'start': a, 'end': b}, 'event_refs': [event['sounding_event_id']
        for event in lattice['events'] if f(event['span']['start']) < f(b) and f(event['span']['end']) > f(a)]}
        for a, b in zip(lattice['plan']['points'], lattice['plan']['points'][1:])]
    pair = {'family': 'V7', 'target_quality': 'M'}
    for side, a, b, reading in (('source', 1, 2, 0), ('target', 2, 4, 1)):
        pair[side] = {'edge': next(i for i, edge in enumerate(lattice['edges'])
                                 if edge['span'] == {'start': q(a), 'end': q(b)}), 'reading': reading}
    item = {**local_query(lattice, pair, ir, temporal=True), 'pair': pair}
    return lattice, item, ir


class RelationCaseAuditTests(unittest.TestCase):
    def assert_no_promotion(self, row):
        self.assertIsNone(row['selected'])
        self.assertFalse(row['function_confirmed'])
        self.assertFalse(row['gate_changed'])

    def test_direct_positive_rechecked_without_harmony_promotion(self):
        lattice, item, ir = case(delayed=False)
        self.assertEqual(item['query']['status'], 'witness_exists')
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['original_status'], 'witness_exists')
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertTrue(row['direct']['checks'])
        self.assertTrue(row['direct']['limitations'])
        self.assert_no_promotion(row)

    def test_member_array_order_is_not_harmonic_identity(self):
        for side in ('source', 'target'):
            lattice, item, ir = case(delayed=False)
            choice = item['pair'][side]
            lattice['edges'][choice['edge']]['readings'][choice['reading']]['members'].reverse()
            item = {**local_query(lattice, item['pair'], ir, temporal=True), 'pair': item['pair']}
            self.assertEqual(item['query']['status'], 'witness_exists')
            with self.subTest(side=side):
                self.assertEqual(audit_pair(lattice, item, ir)['direct']['status'], 'conditional_witness_rechecked')

    def test_target_seventh_with_reordered_triad_subset_retained(self):
        lattice, item, ir = case(delayed=False)
        choice = item['pair']['target']
        lattice['edges'][choice['edge']]['readings'][choice['reading']]['members'] = [['E', 0], ['C', 0], ['A', 0], ['F', 0]]
        item = {**local_query(lattice, item['pair'], ir, temporal=True), 'pair': item['pair']}
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertEqual(row['temporal']['status'], 'not_supported_in_saved_query')
        self.assertIn(['E', 0], row['diagnostics']['sides']['target']['interval_profile']['missing_members'])

    def test_delayed_positive_stays_distinct_from_direct_control(self):
        lattice, item, ir = case()
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['original_status'], 'no_compatible_witness')
        self.assertEqual(row['direct']['status'], 'not_supported_in_saved_query')
        self.assertEqual(row['temporal']['original_status'], 'temporal_resolution_possible')
        self.assertEqual(row['temporal']['status'], 'conditional_witness_rechecked')
        self.assertTrue(row['temporal']['checks'])
        self.assert_no_promotion(row)

    def test_saved_negative_is_not_recomputed_as_positive(self):
        lattice, item, ir = case(delayed=False)
        item['query'] = {'status': 'no_compatible_witness'}
        item['temporal_query'] = {'status': 'no_joint_temporal_witness'}
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'not_supported_in_saved_query')
        self.assertEqual(row['temporal']['status'], 'not_supported_in_saved_query')
        self.assert_no_promotion(row)

    def test_candidate_identity_mutations_rejected(self):
        for key in ('source_candidate_ref', 'target_candidate_ref',
                    'source_alternative_index', 'target_alternative_index'):
            lattice, item, ir = case()
            item[key] = 999 if key.endswith('index') else 'invented-origin'
            with self.subTest(key=key), self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_wrong_ir_event_identity_rejected(self):
        lattice, item, ir = case(); ir = deepcopy(ir)
        ir['sounding_events'][0]['pitch']['midi_pitch'] += 1
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_positive_direct_unknown_event_rejected(self):
        lattice, item, ir = case(delayed=False)
        item['query']['links'][0][0] = 'missing-note'
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_positive_direct_cross_lane_rejected(self):
        lattice, item, ir = case(delayed=False)
        target = item['query']['links'][0][1]
        target_sound = sound(lattice, target)
        for note in ir['note_events']:
            if note['note_id'] in target_sound['source_note_ids']: note['voice_id'] = 'borrowed-lane'
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_positive_direct_timing_gap_rejected(self):
        lattice, item, ir = case(delayed=False)
        target = item['query']['links'][0][1]
        altered = deepcopy(sound(lattice, target)['span']); altered['start'] = q('3/2')
        set_sound_field(lattice, ir, target, 'span', altered)
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_positive_direct_wrong_octave_or_direction_rejected(self):
        for midi, octave in ((77, 5), (64, 4)):
            lattice, item, ir = case(delayed=False)
            link = item['query']['required_link_options']['leading_tone_to_target_root'][0]
            pitch = deepcopy(sound(lattice, link[1])['pitch'])
            pitch.update(midi_pitch=midi, octave=octave)
            if midi == 64: pitch.update(step='E', spelling='E4')
            set_sound_field(lattice, ir, link[1], 'pitch', pitch)
            with self.subTest(midi=midi), self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_direct_partial_obligation_set_not_full_witness(self):
        lattice, item, ir = case(delayed=False)
        item['query']['links'] = item['query']['links'][:1]
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_temporal_wrong_arrival_or_carry_rejected(self):
        for change in ('arrival', 'carried', 'delayed', 'source'):
            lattice, item, ir = case()
            option = next(option for option in item['temporal_query']['witness']
                          if option['relation'] == 'leading_tone_to_target_root')
            if change == 'arrival': option['arrival'] = q('3/2')
            elif change == 'carried': option['carried_event_refs'] = []
            elif change == 'delayed': option['delayed'] = False
            else: option['source_ref'] = 's0'
            with self.subTest(change=change), self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_temporal_touching_same_pitch_carry_chain_rechecked(self):
        specs = [('C3', 0, 1, 'bass'), ('E4', 0, 1, 'lead'), ('E4', 1, 2, 'lead'),
                 ('G4', 0, 1, 'fifth'), ('B-4', 0, 1, 'seventh'),
                 ('F3', 1, 3, 'bass'), ('F4', 2, 3, 'lead'),
                 ('C5', 1, 3, 'fifth'), ('A4', 1, 3, 'seventh')]
        lattice, item, ir = case(specs=specs)
        self.assertEqual(item['temporal_query']['status'], 'temporal_resolution_possible')
        self.assertEqual(audit_pair(lattice, item, ir)['temporal']['status'], 'conditional_witness_rechecked')
        item['temporal_query']['witness'][0]['links'].pop(0)
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_temporal_partial_roles_never_count_as_complete(self):
        lattice, item, ir = case()
        item['temporal_query']['witness'] = item['temporal_query']['witness'][:1]
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_temporal_actual_cross_lane_or_rest_gap_rejected(self):
        for change in ('lane', 'gap'):
            lattice, item, ir = case()
            target = next(option['target_ref'] for option in item['temporal_query']['witness']
                          if option['relation'] == 'leading_tone_to_target_root')
            if change == 'lane':
                for note in ir['note_events']:
                    if note['note_id'] in sound(lattice, target)['source_note_ids']:
                        note['voice_id'] = 'unrelated-lane'
            else:
                altered = deepcopy(sound(lattice, target)['span']); altered['start'] = q('5/2')
                set_sound_field(lattice, ir, target, 'span', altered)
            with self.subTest(change=change), self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_temporal_carry_register_is_exact_not_just_same_pitch_class(self):
        specs = [('C3', 0, 1, 'bass'), ('E4', 0, 1, 'lead'), ('E4', 1, 2, 'lead'),
                 ('G4', 0, 1, 'fifth'), ('B-4', 0, 1, 'seventh'),
                 ('F3', 1, 3, 'bass'), ('F4', 2, 3, 'lead'),
                 ('C5', 1, 3, 'fifth'), ('A4', 1, 3, 'seventh')]
        lattice, item, ir = case(specs=specs)
        pitch = deepcopy(sound(lattice, 's2')['pitch']); pitch.update(octave=5, midi_pitch=76, spelling='E5')
        set_sound_field(lattice, ir, 's2', 'pitch', pitch)
        with self.assertRaisesRegex(ValueError, 'temporal_carry_not_identical_pitch'):
            audit_pair(lattice, item, ir)

    def test_complete_interval_not_complete_terminal_vertical_chord(self):
        lattice, item, ir = case(); row = audit_pair(lattice, item, ir)
        source = row['diagnostics']['sides']['source']
        self.assertEqual(source['interval_profile']['missing_members'], [])
        self.assertIn(['G', 0], source['missing_boundary_members'])
        self.assertEqual(row['temporal']['status'], 'conditional_witness_rechecked')

    def test_missing_actual_member_is_not_invented_by_audit(self):
        specs = [('C3', 0, 1, 'bass'), ('E4', 0, 2, 'lead'), ('B-4', 0, 1, 'seventh'),
                 ('F3', 1, 3, 'bass'), ('F4', 2, 3, 'lead'), ('A4', 1, 3, 'seventh'),
                 ('C5', 1, 3, 'fifth')]
        lattice, item, ir = case(specs=specs); before = deepcopy((lattice, item, ir))
        row = audit_pair(lattice, item, ir)
        self.assertIn(['G', 0], row['diagnostics']['sides']['source']['interval_profile']['missing_members'])
        self.assertEqual(row['temporal']['status'], 'not_supported_in_saved_query')
        self.assertEqual((lattice, item, ir), before)

    def test_boundary_doublings_keep_every_event_reference(self):
        specs = [('C3', 0, 1, 'bass'), ('E4', 0, 1, 'lead'), ('G4', 0, 1, 'fifth'),
                 ('B-4', 0, 1, 'seventh'), ('F3', 1, 3, 'bass'), ('F4', 1, 3, 'lead'),
                 ('C5', 1, 3, 'fifth'), ('A4', 1, 3, 'seventh')]
        lattice, item, ir = case(specs=specs); row = audit_pair(lattice, item, ir)
        target = row['diagnostics']['sides']['target']
        refs = target['boundary_member_event_refs']
        self.assertEqual(refs[str(('F', 0))], ['s4', 's5'])
        self.assertEqual(target['missing_boundary_members'], [])

    def test_exact_rational_reencoding_preserves_audit(self):
        lattice, item, ir = case()
        expected = audit_pair(lattice, item, ir)
        for option in item['temporal_query']['witness']:
            value = option['arrival']; value['numerator'] *= 3; value['denominator'] *= 3
        actual = audit_pair(lattice, item, ir)
        self.assertEqual(actual['temporal']['status'], expected['temporal']['status'])
        self.assertEqual(actual['diagnostics'], expected['diagnostics'])

    def test_ir_microtonal_background_explicitly_unsupported_not_truncated(self):
        lattice, item, ir = case()
        extra = deepcopy(ir['sounding_events'][0]); extra['sounding_event_id'] = 'microtonal-background'
        extra['source_note_ids'] = ['microtonal-note']; extra['span'] = {'start': q('1/2'), 'end': q('3/4')}
        extra['pitch'].update(step='D', alter=q('1/2'), octave=4, midi_pitch=62.5, spelling='D+4')
        note = deepcopy(ir['note_events'][0]); note['note_id'] = 'microtonal-note'; note['voice_id'] = 'background'
        ir['note_events'].append(note)
        ir['sounding_events'].append(deepcopy(extra))
        if lattice['events'] is not ir['sounding_events']: lattice['events'].append(deepcopy(extra))
        before = deepcopy((lattice, item, ir)); row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'unsupported')
        self.assertEqual(row['temporal']['status'], 'unsupported')
        self.assertEqual(row['temporal']['original_status'], 'temporal_resolution_possible')
        self.assertEqual((lattice, item, ir), before)
        self.assert_no_promotion(row)

    def test_microtonal_parent_background_ending_at_local_start_not_unsupported(self):
        lattice, item, ir = outside_local_case('microtonal'); before = deepcopy((lattice, item, ir))
        self.assertEqual(item['query']['status'], 'witness_exists')
        self.assertEqual(item['temporal_query']['status'], 'temporal_resolution_possible')
        self.assertEqual(item['local_context_span'], {'start': q(1), 'end': q(4)})
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertEqual(row['temporal']['status'], 'conditional_witness_rechecked')
        self.assertNotIn('unsupported_event_refs', row)
        self.assertEqual((lattice, item, ir), before)

    def test_parent_background_missing_lane_outside_local_not_failed_recheck(self):
        lattice, item, ir = outside_local_case('missing-lane'); before = deepcopy((lattice, item, ir))
        self.assertEqual(item['query']['status'], 'witness_exists')
        self.assertEqual(item['temporal_query']['status'], 'temporal_resolution_possible')
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertEqual(row['temporal']['status'], 'conditional_witness_rechecked')
        self.assertEqual((lattice, item, ir), before)
        # Local lane scoping must not weaken whole-parent identity/coverage validation.
        wrong_ir = deepcopy(ir); wrong_ir['sounding_events'].pop()
        with self.assertRaisesRegex(ValueError, 'ir_context_event_coverage_mismatch'):
            audit_pair(lattice, item, wrong_ir)

    def test_all_same_span_competitors_and_saved_controls_preserved(self):
        lattice, item, ir = case(); control = deepcopy(item)
        control['query'] = {'status': 'no_compatible_witness'}
        control['temporal_query'] = {'status': 'no_joint_temporal_witness'}
        items = [item, control, deepcopy(item)]
        survey = {'status': 'ready', 'results': items, 'selected': None,
                  'plan': {'pairs': [deepcopy(entry['pair']) for entry in items]}}
        before = deepcopy((lattice, survey, ir)); report = run(lattice, survey, ir)
        self.assertEqual(len(report['groups']), 1)
        group = report['groups'][0]
        self.assertEqual(group['query_indices'], [0, 1, 2])
        self.assertEqual(group['positive_query_indices'], [0, 2])
        self.assertEqual(group['control_query_indices'], [1])
        self.assertEqual(len(group['audits']), 3)
        self.assertEqual((lattice, survey, ir), before)
        json.dumps(report)

    def test_direct_partial_member_support_is_not_reported_as_complete_chord(self):
        specs = [('E4', 0, 1, 'lead'), ('B-4', 0, 1, 'seventh'),
                 ('F4', 1, 3, 'lead'), ('A4', 1, 3, 'seventh')]
        lattice, item, ir = case(specs=specs)
        self.assertEqual(item['query']['status'], 'witness_exists')
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertEqual(row['temporal']['status'], 'not_supported_in_saved_query')
        source = row['diagnostics']['sides']['source']
        self.assertEqual(source['interval_profile']['missing_members'], [['C', 0], ['G', 0]])
        self.assertEqual(source['missing_boundary_members'], [['C', 0], ['G', 0]])
        self.assertIn('full_membership_not_required', row['direct']['limitations'])
        self.assert_no_promotion(row)

    def test_doubled_tendency_unlinked_event_is_explicitly_unmeasured(self):
        specs = [('C3', 0, 1, 'bass'), ('E4', 0, 1, 'lead'), ('E5', 0, 1, 'other-lead'),
                 ('G4', 0, 1, 'fifth'), ('B-4', 0, 1, 'seventh'),
                 ('F3', 1, 3, 'bass'), ('F4', 1, 3, 'lead'), ('G5', 1, 3, 'other-lead'),
                 ('C5', 1, 3, 'fifth'), ('A4', 1, 3, 'seventh')]
        lattice, item, ir = case(specs=specs); row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertIn('s2', row['diagnostics']['critical_source_events_not_in_direct_witness'])
        self.assertEqual(row['diagnostics']['all_doubled_tendencies_resolved'], 'not_measured')
        self.assertFalse(row['confirmed_nct'])

    def test_zero_duration_background_retains_saved_status_as_unsupported(self):
        lattice, item, ir = case(); event = deepcopy(ir['sounding_events'][0])
        event['sounding_event_id'] = 'zero-duration'; event['span'] = {'start': q('1/2'), 'end': q('1/2')}
        ir['sounding_events'].append(event)
        if lattice['events'] is not ir['sounding_events']: lattice['events'].append(deepcopy(event))
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['temporal']['original_status'], 'temporal_resolution_possible')
        self.assertEqual(row['direct']['status'], 'unsupported')
        self.assertEqual(row['temporal']['status'], 'unsupported')
        self.assertIn({'event_ref': 'zero-duration', 'reason': 'nonpositive_sound_duration'},
                      row['unsupported_event_refs'])

    def test_budget_controls_are_not_positive_or_failed_music(self):
        lattice, item, ir = case()
        item['query'] = {'status': 'query_budget_abstention'}
        item['temporal_query'] = {'status': 'path_budget_abstention'}
        row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['original_status'], 'query_budget_abstention')
        self.assertEqual(row['temporal']['original_status'], 'path_budget_abstention')
        self.assertEqual(row['direct']['status'], 'not_supported_in_saved_query')
        self.assertEqual(row['temporal']['status'], 'not_supported_in_saved_query')
        self.assert_no_promotion(row)

    def test_control_only_spans_stay_in_inventory_without_positive_group(self):
        lattice, item, ir = case(); item['query'] = {'status': 'no_compatible_witness'}
        item['temporal_query'] = {'status': 'no_joint_temporal_witness'}
        survey = {'status': 'ready', 'results': [item], 'plan': {'pairs': [deepcopy(item['pair'])]}}
        row = run(lattice, survey, ir)
        self.assertEqual(row['groups'], [])
        self.assertEqual(len(row['inventory']), 1)
        self.assertEqual(row['inventory'][0]['query_index'], 0)
        self.assertEqual(row['inventory'][0]['temporal'], 'no_joint_temporal_witness')
        self.assertEqual(row['summary']['inventoried_queries'], 1)

    def test_survey_result_count_and_pair_plan_integrity_rejected(self):
        lattice, item, ir = case()
        survey = {'status': 'ready', 'results': [item], 'plan': {'pairs': []}}
        with self.assertRaisesRegex(ValueError, 'survey_incomplete'): run(lattice, survey, ir)
        altered_pair = deepcopy(item['pair']); altered_pair['family'] = 'vii7'
        survey['plan']['pairs'] = [altered_pair]
        with self.assertRaisesRegex(ValueError, 'pair_plan_mismatch'): run(lattice, survey, ir)

    def test_saved_positive_query_relation_metadata_must_match_planned_pair(self):
        for field in ('query', 'temporal_query'):
            for key, value in (('family', 'vii7'), ('source_path_index', 99), ('target_path_index', 99)):
                lattice, item, ir = case(delayed=False)
                item[field][key] = value
                with self.subTest(field=field, key=key), self.assertRaises(ValueError):
                    audit_pair(lattice, item, ir)

    def test_direct_positive_cannot_add_unplanned_noncritical_link(self):
        lattice, item, ir = case(delayed=False)
        item['query']['links'].append(['s0', 's4'])
        with self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_positive_candidate_blockers_are_not_ignored(self):
        for side in ('source', 'target'):
            lattice, item, ir = case(delayed=False); choice = item['pair'][side]
            lattice['edges'][choice['edge']]['readings'][choice['reading']]['abstention_reasons'] = ['blocked']
            with self.subTest(side=side), self.assertRaises(ValueError): audit_pair(lattice, item, ir)

    def test_positive_source_shape_and_target_root_must_match_family(self):
        for side in ('source', 'target'):
            lattice, item, ir = case(); choice = item['pair'][side]
            lattice['edges'][choice['edge']]['readings'][choice['reading']]['root_spelling'] = ['A', 0]
            with self.subTest(side=side), self.assertRaisesRegex(ValueError, 'family_shape_mismatch'):
                audit_pair(lattice, item, ir)

    def test_direct_nonmember_remains_diagnostic_not_exempted(self):
        specs = [('C3', 0, 1, 'bass'), ('E4', 0, 1, 'lead'), ('G4', 0, 1, 'fifth'),
                 ('B-4', 0, 1, 'seventh'), ('D4', '1/2', 1, 'foreign-source'),
                 ('F3', 1, 3, 'bass'), ('F4', 1, 3, 'lead'), ('C5', 1, 3, 'fifth'),
                 ('A4', 1, 3, 'seventh'), ('D5', 1, 3, 'foreign-target')]
        lattice, item, ir = case(specs=specs); row = audit_pair(lattice, item, ir)
        self.assertEqual(row['direct']['status'], 'conditional_witness_rechecked')
        self.assertEqual(row['temporal']['status'], 'not_supported_in_saved_query')
        self.assertEqual(row['diagnostics']['sides']['source']['interval_profile']['unexplained_event_refs'], ['s4'])
        self.assertEqual(row['diagnostics']['sides']['target']['interval_profile']['unexplained_event_refs'], ['s9'])
        self.assertIn('nonmembers_not_explained', row['direct']['limitations'])
        self.assertFalse(row['confirmed_nct'])

    def test_saved_profile_corruption_is_not_silently_replaced(self):
        for side in ('source', 'target'):
            lattice, item, ir = case()
            item['temporal_query'][side + '_profile']['missing_members'] = [['D', 1]]
            with self.subTest(side=side), self.assertRaisesRegex(ValueError, 'saved_profile_mismatch'):
                audit_pair(lattice, item, ir)

    def test_temporal_global_delayed_flag_cannot_be_changed(self):
        lattice, item, ir = case(); item['temporal_query']['has_delayed_arrival'] = False
        with self.assertRaisesRegex(ValueError, 'temporal_delayed_flag_mismatch'): audit_pair(lattice, item, ir)

    def test_labels_are_not_audit_inputs_and_no_training_gold_promotion(self):
        lattice, item, ir = case(); expected = audit_pair(lattice, item, ir)
        ir['source_harmony_annotations'] = {'roman_numeral': 'unrelated label'}
        lattice['gold_label'] = 'unrelated'; item['human_label'] = 'unrelated'
        self.assertEqual(audit_pair(lattice, item, ir), expected)
        self.assertEqual(expected['global_voice_assignment'], 'not_measured')
        self.assertEqual(expected['human_review'], 'not_reviewed')
        self.assertFalse(expected['gold_eligible']); self.assertFalse(expected['training_eligible'])
        self.assertFalse(expected['accuracy_measured'])

    def test_audit_is_deterministic_serializable_and_input_frozen(self):
        lattice, item, ir = case(); before = deepcopy((lattice, item, ir))
        first = audit_pair(lattice, item, ir); second = audit_pair(lattice, item, ir)
        self.assertEqual(first, second); json.dumps(first)
        self.assertEqual((lattice, item, ir), before)


if __name__ == '__main__': unittest.main()
