"""Synthetic integration contracts; no local corpora or reference labels."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_catalog_resolution import pitch_pair
from musicanote_harness.harmony_candidate_relation_survey import run as relations_run
from musicanote_harness.harmony_hold_change_context import run as hold_run
from musicanote_harness.harmony_context_bundle import bundle, missing_run
from test_harmony_distributed_resolution import fixture


def data(specs=None):
    lattice, path, ir = fixture(specs)
    for edge in lattice['edges']:
        edge['unspelled_candidate_refs'] = []
        for ri, reading in enumerate(edge['readings']):
            reading.update(origin_pointer='/fixture/' + str(ri), provider='synthetic',
                           root_provenance='synthetic_provider_spelling_alternative',
                           display_label='synthetic-' + str(ri))
            scoped = [s for s in lattice['events'] if f(s['span']['start']) < f(edge['span']['end']) and
                      f(s['span']['end']) > f(edge['span']['start'])]
            reading['event_states'] = {s['sounding_event_id']: 'member' if pitch_pair(s['pitch']) in reading['members']
                                       else 'nonmember_not_confirmed_nct' for s in scoped}
            observed = {tuple(pitch_pair(s['pitch'])) for s in scoped}
            reading['missing_spellings'] = [m for m in reading['members'] if tuple(m) not in observed]
    survey = relations_run(lattice, ir, temporal=True)
    hold = hold_run(lattice, survey, ir)
    stored = {'sample': {'sample_id': 'synthetic-context', 'span': deepcopy(lattice['plan']['context_span']),
                         'lane': ['synthetic-part', 'synthetic-voice']},
              'summary': {'source_labels_used': False, 'accuracy_measured': False},
              'stages': {'continuous': {'status': 'evaluated'}, 'contrast': {'status': 'ready'},
                         'lattice': lattice, 'relations': survey, 'hold_change': hold}}
    return ir, stored, path


def request(path, **extra):
    return {'path': path, 'assignment_ref': 'none', **extra}


class ContextBundleTests(unittest.TestCase):
    def test_all_readings_and_actual_missing_evidence_join(self):
        ir, stored, _ = data()
        with patch('musicanote_harness.harmony_context_bundle.missing_run', wraps=missing_run) as called:
            result = bundle(ir, stored)
        called.assert_called_once()
        count = sum(len(e['readings']) for e in stored['stages']['lattice']['edges'])
        self.assertEqual(result['counts']['indexed_readings'], count)
        self.assertEqual(len(result['relation_inventory']), len(stored['stages']['relations']['plan']['pairs']))
        self.assertEqual(result['stages']['missing_evidence']['status'], 'ready')
        self.assertEqual(result['explicit_paths'], [])
        for name, value in stored['stages'].items(): self.assertEqual(result['stages'][name], value)
        self.assertIsNone(result['selected'])
        self.assertFalse(result['confidence_generated'])
        self.assertFalse(result['harmonic_analysis_confirmed'])

    def test_relation_keys_preserve_full_origin_and_status(self):
        ir, stored, _ = data(); result = bundle(ir, stored)
        for row, original in zip(result['relation_inventory'], stored['stages']['relations']['results']):
            self.assertEqual(row['reading_keys'], {s: original['pair'][s] for s in ('source', 'target')})
            self.assertEqual(row['direct_status'], original['query']['status'])
            self.assertEqual(row['temporal_status'], original['temporal_query']['status'])
            for side in ('source', 'target'):
                choice = row['reading_keys'][side]
                reading = stored['stages']['lattice']['edges'][choice['edge']]['readings'][choice['reading']]
                self.assertEqual(row['origins'][side]['members'], reading['members'])
                self.assertEqual(row['origins'][side]['origin_pointer'], reading['origin_pointer'])
            self.assertFalse(row['whole_chord_explanation_confirmed'])

    def test_complete_explicit_path_has_all_three_existing_calculations(self):
        ir, stored, path = data(); result = bundle(ir, stored, [request(path)])
        record = result['explicit_paths'][0]
        self.assertEqual(set(record['stages']), {'evidence', 'bass', 'resolution'})
        self.assertEqual(record['status'], 'explicit_path_diagnostics_not_verdict')
        self.assertEqual(record['stages']['evidence']['path'], path)
        self.assertEqual(record['stages']['resolution']['reference_key_hypotheses'], [])
        self.assertEqual(record['stages']['resolution']['resolution_link_scope'], 'sampled_assignment')
        self.assertIsNone(record['selected'])
        self.assertFalse(record['path_is_preferred'])

    def test_partial_gap_overlap_unknown_assignment_and_bad_indices_are_not_completed(self):
        ir, stored, path = data()
        requests = [request(path[:1]), request(path + path), request(path, assignment_ref='unknown')]
        requests[2] = {'path': path, 'assignment_ref': 'unknown'}
        requests.extend([request([{'edge': -1, 'reading': 0}]), request([{'edge': True, 'reading': 0}]),
                         request([{'edge': 0, 'reading': 999}]), request([])])
        result = bundle(ir, stored, requests)
        self.assertTrue(all(p['status'] == 'invalid_explicit_path_request' for p in result['explicit_paths']))
        self.assertTrue(all(not p['stages'] for p in result['explicit_paths']))
        self.assertEqual(result['counts']['indexed_readings'], sum(len(e['readings']) for e in stored['stages']['lattice']['edges']))

    def test_annotation_keys_not_accepted_as_path_parameters(self):
        ir, stored, path = data()
        record = bundle(ir, stored, [request(path, reference_keys=['C_major'])])['explicit_paths'][0]
        self.assertEqual(record['status'], 'invalid_explicit_path_request')
        self.assertEqual(record['reason'], 'unsupported_path_request_fields')

    def test_evaluation_projection_keeps_full_path_resolution_scope(self):
        ir, stored, path = data()
        r = bundle(ir, stored, [request(path, evaluation_span={'start': q(1), 'end': q(2)})])['explicit_paths'][0]
        self.assertEqual(r['stages']['evidence']['evaluation_span'], {'start': q(1), 'end': q(2)})
        self.assertEqual(r['stages']['resolution']['context_span'], stored['sample']['span'])

    def test_exact_note_time_and_conditional_inversion_are_not_a_score(self):
        ir, stored, _ = data([('E3', 0, 1, 'bass'), ('C4', 0, 1, 'lead'), ('G4', 0, 1, 'fifth'),
                              ('B-4', 0, 1, 'seventh'), ('F3', 1, 3, 'bass'), ('F4', 1, 3, 'lead'),
                              ('A4', 1, 3, 'seventh'), ('C5', 1, 3, 'fifth')])
        result = bundle(ir, stored)
        row = next(r for r in result['reading_inventory'] if r['span'] == {'start': q(0), 'end': q(1)} and
                   r['root_spelling'] == ['C', 0])
        self.assertEqual(row['total_note_time'], q(4))
        self.assertEqual(row['note_time']['member'], q(4))
        self.assertEqual(row['bass_roles'][0]['inversion_candidate'], 1)
        self.assertFalse(row['bass_roles'][0]['inversion_confirmed'])
        self.assertFalse(row['arpeggiation_confirmed'])

    def test_nonmember_bass_is_not_exempted(self):
        ir, stored, _ = data([('D3', 0, 1, 'extra'), ('C4', 0, 1, 'root'), ('E4', 0, 1, 'lead'),
                              ('G4', 0, 1, 'fifth'), ('B-4', 0, 1, 'seventh'), ('F3', 1, 3, 'bass'),
                              ('F4', 1, 3, 'lead'), ('A4', 1, 3, 'seventh'), ('C5', 1, 3, 'fifth')])
        r = bundle(ir, stored)
        row = next(v for v in r['reading_inventory'] if v['span'] == {'start': q(0), 'end': q(1)} and v['root_spelling'] == ['C', 0])
        self.assertEqual(row['note_time']['nonmember_not_confirmed_nct'], q(1))
        self.assertEqual(row['bass_roles'][0]['status'], 'nonmember_bass_role_unresolved')

    def test_pattern_link_alone_does_not_subtract_unexplained_time(self):
        ir, stored, path = data(); lattice = stored['stages']['lattice']
        sid = next(s['sounding_event_id'] for s in lattice['events'] if s['pitch']['spelling'] == 'E4')
        lattice['patterns'] = [{'pattern_id': 'conditional-held-E', 'kind': 'held_candidate',
            'event_refs': [sid], 'affected_event_ref': sid, 'nonmember_span': {'start': q(1), 'end': q(2)},
            'supporting_assignment_refs': ['none'], 'requirements': [
                {'event_ref': sid, 'state': 'member', 'span': {'start': q('1/2'), 'end': q(1)}},
                {'event_ref': sid, 'state': 'nonmember_not_confirmed_nct', 'span': {'start': q(1), 'end': q(2)}}]}]
        r = bundle(ir, stored, [request(path)])
        row = next(v for v in r['reading_inventory'] if v['reading_key'] == path[1])
        self.assertTrue(row['conditional_nct_links'])
        self.assertFalse(row['conditional_nct_links'][0]['standalone_membership_exemption'])
        self.assertGreater(f(row['note_time']['nonmember_not_confirmed_nct']), 0)
        self.assertGreater(f(r['explicit_paths'][0]['stages']['evidence']['accounting']['note_time']['conditional_nonmember']), 0)

    def test_missing_members_have_role_and_no_boundary_extension_permission(self):
        ir, stored, _ = data([('C3', 0, 1, 'bass'), ('E4', 0, 2, 'lead'), ('B-4', 0, 1, 'seventh'),
                              ('F3', 1, 3, 'bass'), ('F4', 2, 3, 'lead'), ('A4', 1, 3, 'seventh'),
                              ('C5', 1, 3, 'root'), ('G4', 1, 2, 'fifth')])
        r = bundle(ir, stored)
        row = next(v for v in r['reading_inventory'] if v['span'] == {'start': q(0), 'end': q(1)} and v['root_spelling'] == ['C', 0])
        missing = next(m for m in row['missing_members'] if m['pitch'] == ['G', 0])
        self.assertEqual(missing['member_role'], 'fifth')
        self.assertTrue(missing['available_elsewhere_in_parent_event_refs'])
        self.assertFalse(missing['omission_confirmed'])
        self.assertFalse(missing['boundary_extension_authorized'])

    def test_duplicate_origin_equivalent_readings_and_unspelled_refs_are_preserved(self):
        ir, stored, _ = data(); lattice = stored['stages']['lattice']
        copy = deepcopy(lattice['edges'][0]['readings'][0]); copy['candidate_ref'] = 'different-provider-origin'
        copy['origin_pointer'] = '/alternative-origin'; lattice['edges'][0]['readings'].append(copy)
        lattice['edges'][0]['unspelled_candidate_refs'] = ['unknown-spelling-a', 'unknown-spelling-b']
        r = bundle(ir, stored)
        same = [v for v in r['reading_inventory'] if v['reading_key']['edge'] == 0 and v['members'] == copy['members']]
        self.assertEqual(len(same), 2)
        self.assertTrue(all(v['observational_competitor_reading_keys'] for v in same))
        self.assertEqual([v['candidate_ref'] for v in r['unspelled_candidates']], ['unknown-spelling-a', 'unknown-spelling-b'])

    def test_omission_assumption_competitors_keep_quality_unconfirmed(self):
        ir, stored, _ = data([('C3', 0, 1, 'bass'), ('E4', 0, 1, 'lead'),
                              ('F3', 1, 3, 'bass'), ('F4', 1, 3, 'lead'), ('A4', 1, 3, 'third'), ('C5', 1, 3, 'fifth')])
        lattice = stored['stages']['lattice']
        for edge in lattice['edges']:
            c = edge['readings'][0]; c['members'] = [['C', 0], ['E', 0], ['G', 0]]
            c['event_states'] = {s['sounding_event_id']: 'member' if pitch_pair(s['pitch']) in c['members'] else 'nonmember_not_confirmed_nct'
                for s in lattice['events'] if f(s['span']['start']) < f(edge['span']['end']) and f(s['span']['end']) > f(edge['span']['start'])}
        # Relations were calculated before this synthetic provider change; empty
        # ready survey is consistent with an explicit empty relation plan.
        stored['stages']['relations'] = {'status': 'ready', 'plan': {'pairs': []}, 'results': []}
        stored['stages']['hold_change'] = {'status': 'ready', 'chain_comparisons': []}
        first = next(e for e in lattice['edges'] if e['span'] == {'start': q(0), 'end': q(1)})
        aug = deepcopy(first['readings'][0]); aug['candidate_ref'] = 'augmented-competitor'; aug['members'][-1] = ['G', 1]
        first['readings'].append(aug)
        r = bundle(ir, stored)
        rows = [v for v in r['reading_inventory'] if v['span'] == {'start': q(0), 'end': q(1)} and v['root_spelling'] == ['C', 0]]
        assumed = next(v for v in rows if v['members'][-1] == ['G', 0])
        self.assertEqual(assumed['omission_hypothesis']['status'], 'ordinary_fifth_omission_assumption')
        self.assertTrue(assumed['omission_hypothesis']['eligible_for_conditional_comparison'])
        self.assertFalse(assumed['omission_hypothesis']['assumption_is_evidence'])
        self.assertTrue(assumed['observational_competitor_reading_keys'])
        self.assertTrue(all(not v['omission_hypothesis']['quality_confirmed'] for v in rows))

    def test_relation_budget_preserves_plans_and_not_executed_refs(self):
        ir, stored, _ = data(); survey = stored['stages']['relations']
        survey['status'] = 'pair_budget_abstention_no_pruning'; survey['results'] = []; survey['max_pairs'] = 1
        stored['stages']['hold_change'] = {'status': survey['status'], 'chain_comparisons': []}
        r = bundle(ir, stored)
        self.assertEqual(r['stages']['relations'], survey)
        self.assertEqual(len(r['relation_inventory']), len(survey['plan']['pairs']))
        self.assertTrue(all(v['relation_data_ref'] is None for v in r['relation_inventory']))
        self.assertIn('relations', r['preserved_stage_abstentions'])

    def test_lattice_budget_and_baseline_abstentions_remain_local(self):
        ir, stored, path = data(); l = stored['stages']['lattice']
        l['status'] = 'edge_budget_abstention_no_pruning'; l['edges'] = []; l.pop('cells'); l['max_edges'] = 1
        status = l['status']; stored['stages']['relations'] = {'status': status, 'plan': {'pairs': []}, 'results': []}
        stored['stages']['hold_change'] = {'status': status, 'chain_comparisons': []}
        r = bundle(ir, stored, [request(path)])
        self.assertEqual(r['stages']['lattice'], l)
        self.assertEqual(r['reading_inventory'], [])
        self.assertEqual(r['explicit_paths'][0]['status'], 'preserved_lattice_abstention')
        stored['stages']['lattice'] = {'status': 'baseline_not_ready', 'selected': None}
        r = bundle(ir, stored)
        self.assertEqual(r['stage_statuses']['lattice'], 'baseline_not_ready')

    def test_integrity_failures_do_not_become_musical_abstentions(self):
        ir, stored, _ = data()
        for what in ('event', 'cell', 'interval', 'member', 'context', 'candidate'):
            with self.subTest(what=what):
                broken = deepcopy(stored); l = broken['stages']['lattice']
                if what == 'event': l['events'].pop()
                elif what == 'cell': l['cells'][0]['event_refs'].pop()
                elif what == 'interval': l['edges'].pop()
                elif what == 'member': next(iter(l['edges'][0]['readings']))['event_states'][next(iter(l['edges'][0]['readings'][0]['event_states']))] = 'spelling_unresolved'
                elif what == 'context': broken['sample']['span']['end'] = q(99)
                else: broken['stages']['relations']['results'][0]['source_candidate_ref'] = 'wrong'
                with self.assertRaises(ValueError): bundle(ir, broken)

    def test_unknown_pattern_assignment_fails_closed(self):
        ir, stored, _ = data(); l = stored['stages']['lattice']; sid = l['events'][0]['sounding_event_id']
        l['patterns'] = [{'pattern_id': 'invented', 'event_refs': [sid], 'affected_event_ref': sid,
                           'supporting_assignment_refs': ['unknown'], 'requirements': []}]
        with self.assertRaisesRegex(ValueError, 'unknown_pattern'): bundle(ir, stored)

    def test_nonblind_or_selected_stored_input_fails_closed(self):
        ir, stored, _ = data()
        for field, value in [('source_labels_used', True), ('accuracy_measured', True), ('selected', 0)]:
            broken = deepcopy(stored); broken['stages']['lattice'][field] = value
            with self.assertRaises(ValueError): bundle(ir, broken)

    def test_inputs_and_outputs_are_independent_and_no_path_api_called_implicitly(self):
        ir, stored, _ = data(); saved = deepcopy((ir, stored))
        with patch('musicanote_harness.harmony_context_bundle.vector', side_effect=AssertionError('implicit path')):
            r = bundle(ir, stored)
        self.assertEqual((ir, stored), saved)
        r['stages']['lattice']['events'][0]['pitch']['step'] = 'D'
        r['reading_inventory'][0]['members'][0][0] = 'D'
        self.assertEqual((ir, stored), saved)


if __name__ == '__main__': unittest.main()
