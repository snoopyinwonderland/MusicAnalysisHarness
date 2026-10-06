import json
import unittest
from copy import deepcopy

from test_harmony_distributed_resolution import fixture
from test_harmony_bass_return import setup as bass_setup
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_bass_return import compare_chain
from musicanote_harness.harmony_repeated_bass import chains
from musicanote_harness.harmony_incomplete_triads import augment_chain as omissions
from musicanote_harness.harmony_incomplete_triads import run as baseline
from musicanote_harness.harmony_omission_voice_context import (
    geometry, cut_movements, neighbor_returns, contextual_neighbors,
    relation_options, constrain_neighbors, augment_chain, run,
)
from musicanote_harness.harmony_distributed_resolution import joint_paths


def graph_fixture(specs, end=3):
    lattice, _, ir = fixture(specs)
    graph = geometry(lattice, ir, {'start': q(0), 'end': q(end)})
    return lattice, ir, graph, {s['sounding_event_id']: s for s in lattice['events']}


def event_ref(events, pitch, start):
    return next(sid for sid, s in events.items()
                if s['pitch']['spelling'] == pitch and f(s['span']['start']) == f(q(start)))


def resolution_fixture(specs=None):
    lattice, path, ir = fixture(specs)
    graph = geometry(lattice, ir, {'start': q(0), 'end': q(3)})
    readings = [lattice['edges'][p['edge']]['readings'][p['reading']] for p in path]
    return lattice, ir, graph, {s['sounding_event_id']: s for s in lattice['events']}, readings


def return_fixture():
    # C bass is held by reattacks; G7's B and F have actual C/E arrivals.
    specs = [('C3', 0, 1, 'bass'), ('C3', 1, 2, 'bass'), ('C3', 2, 3, 'bass'),
             ('C4', 0, 1, 'lead'), ('B3', 1, 2, 'lead'), ('C4', 2, 3, 'lead'),
             ('E4', 0, 1, 'seventh'), ('F4', 1, 2, 'seventh'), ('E4', 2, 3, 'seventh'),
             ('G4', 0, 3, 'held'), ('D4', 1, 2, 'fifth')]
    lattice, _, ir = fixture(specs)
    forms = [(['C', 0], [['C', 0], ['E', 0], ['G', 0]]),
             (['G', 0], [['G', 0], ['B', 0], ['D', 0], ['F', 0]])]
    for edge in lattice['edges']:
        template = edge['readings'][0]
        edge['readings'] = [{**deepcopy(template), 'candidate_ref': str(i),
                             'root_spelling': root, 'members': members}
                            for i, (root, members) in enumerate(forms)]
    bass = chains(lattice, ir)['chains'][0]
    chain = omissions(compare_chain(lattice, bass))
    return lattice, ir, bass, chain


class OmissionVoiceContextTests(unittest.TestCase):
    def test_lower_neighbor_has_actual_same_pitch_middle_carry(self):
        _, _, graph, events = graph_fixture([
            ('A4', 0, 1, 'v'), ('G4', 1, '3/2', 'v'),
            ('G4', '3/2', 2, 'v'), ('A4', 2, 3, 'v')])
        a = neighbor_returns(events, graph, [q(1), q(2)])
        self.assertEqual(a['status'], 'ready')
        self.assertEqual(len(a['options']), 1)
        option = a['options'][0]
        self.assertEqual(option['direction'], 'lower_neighbor_contour')
        self.assertEqual(len(option['event_refs']), 4)
        self.assertEqual(len(option['links']), 3)
        self.assertFalse(option['confirmed_nct'])
        self.assertEqual(option['carried_event_refs'], [])

    def test_upper_neighbor_and_membership_remain_conditional(self):
        _, _, graph, events = graph_fixture([
            ('A4', 0, 1, 'v'), ('B-4', 1, 2, 'v'), ('A4', 2, 3, 'v')])
        a = neighbor_returns(events, graph, [q(1), q(2)])
        self.assertEqual(a['options'][0]['direction'], 'upper_neighbor_contour')
        roles = contextual_neighbors(a['options'], [
            {'members': [['A', 0]]}, {'members': [['G', 0]]}, {'members': [['A', 0]]}], events)
        self.assertTrue(roles[0]['outer_member_and_middle_nonmember'])
        self.assertFalse(roles[0]['confirmed_nct'])
        self.assertFalse(a['contour_is_nct_evidence_by_itself'])

    def test_rest_cannot_be_bridged_by_neighbor_search(self):
        _, _, graph, events = graph_fixture([
            ('A4', 0, 1, 'v'), ('G4', 1, '3/2', 'v'), ('A4', 2, 3, 'v')])
        self.assertEqual(neighbor_returns(events, graph, [q(1), q(2)])['options'], [])

    def test_cross_lane_neighbor_not_inferred(self):
        _, _, graph, events = graph_fixture([
            ('A4', 0, 1, 'v'), ('G4', 1, 2, 'other'), ('A4', 2, 3, 'v')])
        self.assertEqual(neighbor_returns(events, graph, [q(1), q(2)])['options'], [])

    def test_octave_displacement_is_not_neighbor_return(self):
        for specs in [[('A4', 0, 1, 'v'), ('G3', 1, 2, 'v'), ('A4', 2, 3, 'v')],
                      [('A4', 0, 1, 'v'), ('G4', 1, 2, 'v'), ('A5', 2, 3, 'v')]]:
            with self.subTest(specs=specs):
                _, _, graph, events = graph_fixture(specs)
                self.assertEqual(neighbor_returns(events, graph, [q(1), q(2)])['options'], [])

    def test_held_cross_cut_is_one_observation_not_self_link(self):
        _, _, graph, events = graph_fixture([
            ('G4', 0, 3, 'v'), ('C3', 0, 1, 'other0'), ('F3', 1, 3, 'other1')])
        a = cut_movements(events, graph, q(1))
        self.assertEqual(len(a['held_sounds']), 1)
        self.assertEqual(a['held_sounds'][0]['kind'], 'held_sound')
        self.assertEqual(a['held_sounds'][0]['source_ref'], a['held_sounds'][0]['target_ref'])
        self.assertEqual(a['touching_options'], [])
        self.assertEqual(graph['links'], [])
        self.assertFalse(a['voice_assignment_selected'])

    def test_enharmonic_upward_letter_but_downward_semitone_not_neighbor(self):
        _, _, graph, events = graph_fixture([
            ('E#4', 0, 1, 'v'), ('F-4', 1, 2, 'v'), ('E#4', 2, 3, 'v')])
        self.assertEqual(neighbor_returns(events, graph, [q(1), q(2)])['options'], [])

    def test_each_neighbor_possible_but_both_share_branch_merge_conflict(self):
        _, _, graph, events = graph_fixture([
            ('C3', 0, 1, 'bass'), ('C3', 1, 2, 'bass'), ('C3', 2, 3, 'bass'),
            ('A4', 0, 1, 'v'), ('G4', 1, 2, 'v'), ('B-4', 1, 2, 'v'), ('A4', 2, 3, 'v')])
        neighbors = neighbor_returns(events, graph, [q(1), q(2)])
        bass = {'links': [[event_ref(events, 'C3', a), event_ref(events, 'C3', b)]
                          for a, b in ((0, 1), (1, 2))], 'carried_event_refs': []}
        a = constrain_neighbors(neighbors, bass)
        self.assertEqual(len(a['options']), 2)
        self.assertTrue(all(o['bass_constrained_query']['status'] == 'temporal_resolution_possible'
                            for o in a['options']))
        self.assertEqual(a['coexistence_status'], 'audited')
        self.assertEqual(len(a['coexistence_queries']), 1)
        self.assertEqual(a['coexistence_queries'][0]['query']['status'], 'no_joint_temporal_witness')
        self.assertTrue(all(not o['confirmed_nct'] for o in a['options']))

    def test_bass_incompatible_contour_retained_not_excused(self):
        _, _, graph, events = graph_fixture([
            ('F3', 0, 1, 'bass'), ('F3', 1, 2, 'bass'), ('F3', 2, 3, 'bass'),
            ('G3', 1, 2, 'bass')])
        neighbors = neighbor_returns(events, graph, [q(1), q(2)])
        bass = {'links': [[event_ref(events, 'F3', a), event_ref(events, 'F3', b)]
                          for a, b in ((0, 1), (1, 2))], 'carried_event_refs': []}
        a = constrain_neighbors(neighbors, bass)
        self.assertEqual(len(a['options']), 1)
        self.assertEqual(a['options'][0]['direction'], 'upper_neighbor_contour')
        self.assertEqual(a['options'][0]['bass_constrained_query']['status'], 'no_joint_temporal_witness')
        self.assertFalse(a['options'][0]['confirmed_nct'])

    def test_pair_budget_preserves_options_but_abstains_whole_coexistence_set(self):
        _, _, graph, events = graph_fixture([
            ('A4', 0, 1, 'v'), ('G4', 1, 2, 'v'), ('B-4', 1, 2, 'v'),
            ('B4', 1, 2, 'v'), ('A4', 2, 3, 'v')])
        neighbors = neighbor_returns(events, graph, [q(1), q(2)])
        a = constrain_neighbors(neighbors, {'links': [], 'carried_event_refs': []}, pair_budget=1)
        self.assertEqual(len(a['options']), 3)
        self.assertEqual(a['coexistence_status'], 'pair_budget_abstention_no_subset')
        self.assertEqual(a['coexistence_queries'], [])

    def test_neighbor_queries_serialize_without_circular_witness_or_input_mutation(self):
        _, _, graph, events = graph_fixture([
            ('A4', 0, 1, 'v'), ('G4', 1, 2, 'v'), ('A4', 2, 3, 'v')])
        neighbors = neighbor_returns(events, graph, [q(1), q(2)])
        bass = {'links': [], 'carried_event_refs': []}
        before = deepcopy((neighbors, bass))
        answer = constrain_neighbors(neighbors, bass)
        self.assertEqual((neighbors, bass), before)
        self.assertEqual(json.loads(json.dumps(answer)), answer)

    def test_exact_leading_up_and_seventh_down_are_possibilities(self):
        _, _, graph, events, readings = resolution_fixture()
        relations = relation_options(events, graph, *readings)
        rel = next(r for r in relations if r['family'] == 'V7')
        self.assertTrue(rel['target_root_and_third_observed'])
        self.assertFalse(rel['function_confirmed'])
        self.assertEqual(rel['status'], 'motion_options_recorded')
        self.assertTrue(rel['required_path_options']['leading_tone_to_target_root'])
        self.assertTrue(rel['required_path_options']['seventh_down_step_to_target_member'])
        query = joint_paths(rel['required_path_options'], set(), 100)
        self.assertEqual(query['status'], 'temporal_resolution_possible')

    def test_e_to_eb_is_not_leading_tone_resolution(self):
        _, _, graph, events, readings = resolution_fixture([
            ('C3', 0, 1, 'b'), ('E4', 0, 1, 'lead'), ('G4', 0, 1, 'g'), ('B-4', 0, 1, 's'),
            ('F3', 1, 3, 'b'), ('E-4', 1, 3, 'lead'), ('A4', 1, 3, 's'), ('C5', 1, 3, 'g')])
        rel = next(r for r in relation_options(events, graph, *readings) if r['family'] == 'V7')
        self.assertEqual(rel['required_path_options']['leading_tone_to_target_root'], [])
        departure = next(m for m in rel['observed_critical_departures']
                         if m['source_pitch']['spelling'] == 'E4')
        self.assertEqual(departure['diatonic_steps'], 0)
        self.assertEqual(departure['semitones'], -1)

    def test_unobserved_critical_note_never_becomes_path_witness(self):
        _, _, graph, events, readings = resolution_fixture([
            ('C3', 0, 1, 'b'), ('G4', 0, 1, 'g'), ('B-4', 0, 1, 's'),
            ('F3', 1, 3, 'b'), ('F4', 1, 3, 'lead'), ('A4', 1, 3, 's'), ('C5', 1, 3, 'g')])
        rel = next(r for r in relation_options(events, graph, *readings) if r['family'] == 'V7')
        self.assertEqual(rel['required_path_options']['leading_tone_to_target_root'], [])
        self.assertEqual(joint_paths(rel['required_path_options'], set(), 100)['status'],
                         'no_joint_temporal_witness')

    def test_relation_rest_cross_lane_and_octave_not_bridged(self):
        base = [('C3', 0, 1, 'b'), ('E4', 0, 1, 'lead'), ('G4', 0, 1, 'g'), ('B-4', 0, 1, 's'),
                ('F3', 1, 3, 'b'), ('F4', 1, 3, 'lead'), ('A4', 1, 3, 's'), ('C5', 1, 3, 'g')]
        for replacement in [('F4', 2, 3, 'lead'), ('F4', 1, 3, 'other'), ('F5', 1, 3, 'lead')]:
            with self.subTest(replacement=replacement):
                specs = deepcopy(base); specs[5] = replacement
                _, _, graph, events, readings = resolution_fixture(specs)
                rel = next(r for r in relation_options(events, graph, *readings) if r['family'] == 'V7')
                self.assertEqual(rel['required_path_options']['leading_tone_to_target_root'], [])

    def test_path_budget_withholds_all_partial_relation_options(self):
        _, _, graph, events, readings = resolution_fixture()
        rel = next(r for r in relation_options(events, graph, *readings, path_budget=1)
                   if r['family'] == 'V7')
        self.assertEqual(rel['status'], 'path_budget_abstention')
        self.assertEqual(rel['required_path_options'], {})

    def test_neighbor_path_budget_withholds_partial_subset(self):
        _, _, graph, events = graph_fixture([
            ('A4', 0, 1, 'v'), ('G4', 1, '3/2', 'v'), ('G4', '3/2', 2, 'v'), ('A4', 2, 3, 'v')])
        a = neighbor_returns(events, graph, [q(1), q(2)], budget=1)
        self.assertEqual(a['status'], 'path_budget_abstention')
        self.assertEqual(a['options'], [])

    def test_edge_budget_has_no_truncated_geometry(self):
        lattice, _, ir = fixture()
        graph = geometry(lattice, ir, {'start': q(0), 'end': q(3)}, edge_budget=1)
        self.assertEqual(graph['status'], 'edge_budget_abstention')
        self.assertEqual(graph['links'], [])

    def test_forced_bass_blocks_borrowed_target_and_branch(self):
        forced = {'links': [['bass0', 'bass1'], ['bass1', 'bass2']], 'carried_event_refs': []}
        for links in [[['lead', 'bass1']], [['bass0', 'other']]]:
            with self.subTest(links=links):
                query = joint_paths({'forced_bass': [forced], 'critical': [
                    {'links': links, 'carried_event_refs': []}]}, set(), 100)
                self.assertEqual(query['status'], 'no_joint_temporal_witness')

    def test_integrated_matching_does_not_confirm_harmony_or_exempt_nonmembers(self):
        lattice, ir, bass, chain = return_fixture()
        answer = augment_chain(lattice, chain, bass, ir)
        audit = answer['comparisons'][0]['voice_context_comparison']
        self.assertEqual(audit['status'], 'audited')
        self.assertTrue(audit['combinations'])
        item = next(c for c in audit['combinations'] if c['reading_indices'] == [0, 1, 0])
        self.assertEqual(item['critical_motion_query']['status'], 'critical_motion_matching_possible')
        self.assertFalse(item['function_confirmed'])
        self.assertFalse(item['witness_is_preferred'])
        for field in ('full_voice_assignment_verified', 'nonmember_coverage_verified',
                      'quality_confirmed', 'omission_confirmed', 'pedal_confirmed', 'bass_nonmembers_explained'):
            self.assertFalse(audit[field])
        self.assertIsNone(audit['selected'])
        self.assertTrue(all(not o['carried_event_refs']
                            for o in item['critical_motion_query']['witness']))
        self.assertEqual(json.loads(json.dumps(answer)), answer)

    def test_combination_budget_whole_abstention_not_pruned_subset(self):
        lattice, ir, bass, chain = return_fixture()
        # Duplicate one eligible origin; this is not a new musical observation.
        comp = chain['comparisons'][0]
        comp['omission_comparison']['reading_groups'][0].append(0)
        comp['omission_comparison']['combination_count'] = 2
        audit = augment_chain(lattice, chain, bass, ir, combination_budget=1)['comparisons'][0]['voice_context_comparison']
        self.assertEqual(audit['status'], 'combination_budget_abstention_no_subset')
        self.assertEqual(audit['combinations'], [])

    def test_joint_query_budget_not_negative_proof(self):
        lattice, ir, bass, chain = return_fixture()
        audit = augment_chain(lattice, chain, bass, ir, query_budget=1)['comparisons'][0]['voice_context_comparison']
        self.assertEqual(audit['combinations'][0]['critical_motion_query']['status'], 'query_budget_abstention')
        self.assertIsNone(audit['combinations'][0]['critical_motion_query']['witness'])

    def test_input_and_strict_baseline_are_unchanged(self):
        lattice, ir, _ = bass_setup(missing=True)
        saved = deepcopy((lattice, ir))
        before = baseline(lattice, {'status': 'ready'}, ir)
        answer = run(lattice, {'status': 'ready'}, ir)
        self.assertEqual((lattice, ir), saved)
        self.assertEqual(answer['baseline_version'], before['version'])
        self.assertEqual(answer['baseline_summary'], before['summary'])
        self.assertFalse(answer['gate_changed'])
        self.assertFalse(answer['production_modified'])
        self.assertFalse(answer['accuracy_measured'])
        for base_chain, chain in zip(before['chain_comparisons'], answer['chain_comparisons']):
            self.assertEqual(chain['interval_tables'], base_chain['interval_tables'])
            for prior, current in zip(base_chain['comparisons'], chain['comparisons']):
                for field in ('status', 'clean_combination_count', 'omission_comparison'):
                    self.assertEqual(current[field], prior[field])

    def test_wrong_ir_coverage_and_identity_rejected(self):
        lattice, ir, _ = bass_setup()
        for change in ('coverage', 'identity'):
            bad = deepcopy(ir)
            if change == 'coverage': bad['sounding_events'].pop()
            else: bad['sounding_events'][0]['pitch']['midi_pitch'] += 1
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, change + '_mismatch'):
                run(lattice, {'status': 'ready'}, bad)

    def test_unexplained_nonmember_never_makes_eligible_triple(self):
        lattice, ir, _ = bass_setup(foreign=True)
        a = run(lattice, {'status': 'ready'}, ir)
        audit = a['chain_comparisons'][0]['comparisons'][0]['voice_context_comparison']
        self.assertEqual(audit['status'], 'no_eligible_conditional_triple')
        self.assertEqual(audit['combinations'], [])
        self.assertFalse(audit['nonmember_coverage_verified'])


if __name__ == '__main__': unittest.main()
