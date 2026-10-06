import json
import unittest
from copy import deepcopy
from fractions import Fraction

from test_harmony_omission_voice_context import graph_fixture, return_fixture, event_ref
from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_omission_voice_context import (
    neighbor_returns, augment_chain as voice_chain, run as voice_run)
from musicanote_harness.harmony_hold_change_context import (
    assignments, compare, augment_chain, run, reading_timeline, cells)


def reading(members, start=0, end=3, candidate='hold', blockers=None):
    return {'candidate_ref': candidate, 'alternative_index': 0,
            'root_spelling': deepcopy(members[0]), 'members': deepcopy(members),
            'span': {'start': q(start), 'end': q(end)},
            'candidate_blockers': list(blockers or [])}


def simple(extra=None, specs=None, end=3, cuts=(1, 2)):
    specs = specs or [('A4', 0, 1, 'v'), ('G4', 1, 2, 'v'), ('A4', 2, 3, 'v')]
    lattice, ir, graph, events = graph_fixture(specs + list(extra or []), end=end)
    catalog = neighbor_returns(events, graph, [q(c) for c in cuts])
    hold = reading([['A', 0], ['C', 0], ['E', 0]], 0, end)
    path = [reading(hold['members'], 0, cuts[0], 'left'),
            reading([['G', 0], ['B', 0], ['D', 0]], cuts[0], cuts[1], 'middle'),
            reading(hold['members'], cuts[1], end, 'right')]
    links = deepcopy(catalog['options'][0]['links']) if catalog['options'] else []
    assignment = {'assignment_id': 'explicit', 'links': links}
    return lattice, ir, graph, events, catalog, hold, path, assignment


def answer(data, assignment=None):
    lattice, _, graph, _, catalog, hold, path, selected = data
    return compare(lattice, graph, deepcopy(hold['span']), hold, path,
                   selected if assignment is None else assignment, catalog)


class HoldChangeContextTests(unittest.TestCase):
    def test_same_cells_all_sounds_and_exact_note_time(self):
        data = simple(extra=[('E4', 0, 3, 'held')])
        a = answer(data)
        self.assertEqual(a['hold']['total_note_time'], q(6))
        self.assertEqual(a['change']['total_note_time'], q(6))
        self.assertEqual(a['hold']['total_note_time'], a['change']['total_note_time'])
        for side in ('hold', 'change'):
            for cell in a['shared_cells']:
                actual = [v['event_ref'] for v in a[side]['items'] if v['span'] == cell['span']]
                self.assertEqual(sorted(actual), cell['event_refs'])
            self.assertEqual(sum((f(v) for v in a[side]['note_time'].values()), Fraction()), Fraction(6))
            self.assertEqual(sum((f(v) for v in a[side]['wall_time'].values()), Fraction()), Fraction(3))

    def test_neighbor_under_hold_chord_tone_under_change_same_assignment(self):
        a = answer(simple())
        self.assertEqual(a['hold']['note_time']['conditional_nonmember'], q(1))
        self.assertEqual(a['change']['note_time']['conditional_nonmember'], q(0))
        self.assertEqual(a['change']['note_time']['member'], q(3))
        self.assertEqual(a['hold']['neighbor_roles'][0]['status'], 'conditional_neighbor')
        self.assertEqual(a['change']['neighbor_roles'][0]['status'], 'not_neighbor_under_this_harmony')
        self.assertFalse(a['hold']['confirmed_nct'])
        self.assertFalse(a['change']['confirmed_nct'])
        self.assertFalse(a['harmonic_change_confirmed'])
        self.assertIsNone(a['preferred'])

    def test_empty_and_bass_only_are_distinct_assignments(self):
        lattice, ir, bass, chain = return_fixture()
        voiced = voice_chain(lattice, chain, bass, ir)
        graph = voiced['voice_geometry']; comp = voiced['comparisons'][0]
        events = {s['sounding_event_id']: s for s in lattice['events']}
        catalog = neighbor_returns(events, graph, comp['cut_times'])
        bass_links = comp['voice_context_comparison']['forced_bass_links']
        a = assignments(events, graph, catalog, bass_links)
        empty = next(row for row in a['assignments'] if row['is_empty_assignment'])
        only_bass = next(row for row in a['assignments'] if row['links'] == bass_links)
        self.assertEqual(empty['links'], [])
        self.assertNotEqual(empty['assignment_id'], only_bass['assignment_id'])
        self.assertTrue(any(o == {'contour_indices': [], 'bass_constraint_required': False}
                            for o in empty['constraint_origins']))
        self.assertTrue(any(o == {'contour_indices': [], 'bass_constraint_required': True}
                            for o in only_bass['constraint_origins']))

    def test_all_subsets_keep_branch_conflicts_without_incompatible_union(self):
        data = simple(extra=[('B-4', 1, 2, 'v'),
                             ('C3', 0, 1, 'bass'), ('C3', 1, 2, 'bass'), ('C3', 2, 3, 'bass')])
        _, _, graph, events, catalog, _, _, _ = data
        self.assertEqual(len(catalog['options']), 2)
        bass_links = [[event_ref(events, 'C3', a), event_ref(events, 'C3', b)] for a, b in ((0, 1), (1, 2))]
        a = assignments(events, graph, catalog, bass_links)
        self.assertEqual(a['planned_constraint_sets'], 8)
        self.assertEqual(len(a['assignments']), 6)
        self.assertEqual(len(a['conflicts']), 2)
        self.assertTrue(all(row['contour_indices'] == [0, 1] for row in a['conflicts']))
        self.assertFalse(any(o['contour_indices'] == [0, 1]
                             for row in a['assignments'] for o in row['constraint_origins']))
        self.assertFalse(a['exhaustive_contrapuntal_assignments'])
        self.assertIsNone(a['selected'])

    def test_full_outer_sound_extent_outside_candidate_is_withheld(self):
        data = simple(specs=[('A4', -1, 1, 'v'), ('G4', 1, 2, 'v'), ('A4', 2, 3, 'v')])
        a = answer(data)
        role = a['hold']['neighbor_roles'][0]
        self.assertEqual(role['status'], 'withheld')
        self.assertIn('external_harmonic_context_unassigned', role['reasons'])
        self.assertEqual(a['hold']['note_time']['conditional_nonmember'], q(0))
        self.assertEqual(a['hold']['note_time']['withheld_nonmember'], q(1))
        self.assertEqual(a['hold']['total_note_time'], q(3))

    def test_exact_thirds_are_not_float_aligned(self):
        data = simple(specs=[('A4', 0, '1/3', 'v'), ('G4', '1/3', '2/3', 'v'),
                             ('A4', '2/3', 1, 'v'), ('C3', 1, 3, 'unrelated')],
                      end=1, cuts=('1/3', '2/3'))
        a = answer(data)
        self.assertEqual(a['hold']['total_note_time'], q(1))
        self.assertEqual(a['hold']['note_time']['conditional_nonmember'], q('1/3'))
        self.assertEqual(a['change']['note_time']['member'], q(1))
        self.assertEqual([cell['span']['end'] for cell in a['shared_cells']], [q('1/3'), q('2/3'), q(1)])

    def test_actual_unrelated_nonmember_remains_unexplained(self):
        a = answer(simple(extra=[('F#4', 1, 2, 'foreign')]))
        for side in ('hold', 'change'):
            self.assertEqual(a[side]['note_time']['unexplained_nonmember'], q(1))
        self.assertEqual(a['hold']['note_time']['conditional_nonmember'], q(1))

    def test_missing_fifth_stays_missing_no_virtual_event(self):
        data = simple(extra=[('C5', 0, 3, 'third')])
        a = answer(data)
        observed = a['hold']['candidate_profiles'][0]['observations']
        self.assertEqual(observed['missing_members'], [['E', 0]])
        actual = set(data[3])
        self.assertEqual({v['event_ref'] for v in a['hold']['items']}, actual)
        self.assertEqual({v['event_ref'] for v in a['change']['items']}, actual)
        self.assertEqual(a['hold']['total_note_time'], q(6))

    def test_geometry_cannot_drop_an_unlinked_observed_sound(self):
        data = simple(extra=[('E4', 0, 3, 'held')])
        data[2]['event_refs'].remove(event_ref(data[3], 'E4', 0))
        with self.assertRaisesRegex(ValueError, 'geometry_event_loss'):
            answer(data)

    def test_gap_overlap_backward_and_uncovered_paths_rejected(self):
        for mode in ('gap', 'overlap', 'backward', 'uncovered'):
            data = simple(); path = data[6]
            if mode == 'gap': path[1]['span']['start'] = q('3/2')
            elif mode == 'overlap': path[1]['span']['start'] = q('1/2')
            elif mode == 'backward': path[1]['span']['end'] = q('1/2')
            else: path[-1]['span']['end'] = q('5/2')
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'path_'):
                answer(data)

    def test_duplicate_assignment_link_rejected(self):
        data = simple(); assignment = deepcopy(data[-1])
        assignment['links'].append(assignment['links'][0])
        with self.assertRaisesRegex(ValueError, 'branch_or_merge'):
            answer(data, assignment)

    def test_assignment_branch_rejected_even_when_each_edge_allowed(self):
        data = simple(extra=[('B-4', 1, 2, 'v')])
        graph = data[2]; source = event_ref(data[3], 'A4', 0)
        links = [edge for edge in graph['links'] if edge[0] == source]
        self.assertEqual(len(links), 2)
        with self.assertRaisesRegex(ValueError, 'branch_or_merge'):
            answer(data, {'assignment_id': 'branch', 'links': links})

    def test_assignment_cross_lane_rejected(self):
        data = simple(extra=[('C4', 1, 2, 'other')])
        links = [[event_ref(data[3], 'A4', 0), event_ref(data[3], 'C4', 1)]]
        with self.assertRaisesRegex(ValueError, 'assignment_outside_geometry'):
            answer(data, {'assignment_id': 'crosslane', 'links': links})

    def test_partial_contour_links_cannot_license_coverage(self):
        data = simple()
        a = answer(data, {'assignment_id': 'partial', 'links': data[-1]['links'][:1]})
        self.assertEqual(a['hold']['note_time']['conditional_nonmember'], q(0))
        self.assertEqual(a['hold']['note_time']['unexplained_nonmember'], q(1))
        self.assertEqual(a['hold']['neighbor_roles'][0]['status'], 'links_not_in_shared_assignment')

    def test_candidate_blocker_withholds_contour_evidence(self):
        data = simple(); data[5]['candidate_blockers'] = ['context_unavailable']
        a = answer(data)
        self.assertEqual(a['hold']['note_time']['withheld_nonmember'], q(1))
        self.assertEqual(a['hold']['note_time']['conditional_nonmember'], q(0))
        self.assertIn('context_unavailable', a['hold']['neighbor_roles'][0]['reasons'])

    def test_same_harmony_partition_invariant_under_empty_or_linked_assignment(self):
        for linked in (False, True):
            data = simple(extra=[('E4', 0, 3, 'held')])
            for row in data[6]: row['members'] = deepcopy(data[5]['members'])
            assignment = data[-1] if linked else {'assignment_id': 'empty', 'links': []}
            a = answer(data, assignment)
            for field in ('items', 'cells', 'note_time', 'wall_time', 'neighbor_roles'):
                self.assertEqual(a['hold'][field], a['change'][field])

    def test_assignment_budget_whole_abstention_without_subset(self):
        data = simple(); _, _, graph, events, catalog, _, _, _ = data
        a = assignments(events, graph, catalog, [], assignment_budget=1)
        self.assertEqual(a['status'], 'assignment_budget_abstention_no_subset')
        self.assertEqual(a['assignments'], [])
        self.assertEqual(a['conflicts'], [])

    def test_comparison_budget_whole_abstention_without_subset(self):
        lattice, ir, bass, chain = return_fixture()
        voiced = voice_chain(lattice, chain, bass, ir)
        a = augment_chain(lattice, voiced, comparison_budget=1)
        comp = a['comparisons'][0]['hold_change_context']
        self.assertEqual(comp['status'], 'comparison_budget_abstention_no_subset')
        self.assertEqual(comp['comparisons'], [])
        self.assertEqual(comp['invariance_checks'], 0)

    def test_graph_or_catalog_budget_abstention_not_partial_assignments(self):
        data = simple(); _, _, graph, events, catalog, _, _, _ = data
        for side in ('graph', 'catalog'):
            bad_graph = deepcopy(graph); bad_catalog = deepcopy(catalog)
            if side == 'graph': bad_graph['status'] = 'edge_budget_abstention'
            else: bad_catalog['status'] = 'path_budget_abstention'
            with self.subTest(side=side):
                a = assignments(events, bad_graph, bad_catalog, [])
                self.assertEqual(a['status'], 'geometry_or_catalog_abstention')
                self.assertEqual(a['assignments'], [])

    def test_invalid_budget_rejected_not_silent_fallback(self):
        data = simple(); lattice, _, graph, events, catalog, _, _, _ = data
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, 'invalid_comparison_budget'):
                assignments(events, graph, catalog, [], assignment_budget=limit)

    def test_empty_baseline_keeps_all_sounds_as_individual_tracks(self):
        data = simple(extra=[('E4', 0, 3, 'held')])
        a = answer(data, {'assignment_id': 'empty', 'links': []})
        self.assertEqual(len(a['shared_tracks']), len(data[3]))
        self.assertTrue(all(len(track) == 1 for track in a['shared_tracks']))
        self.assertEqual(a['hold']['note_time']['unexplained_nonmember'], q(1))

    def test_unknown_and_microtonal_pitch_remain_unresolved_not_neighbor(self):
        for mode in ('missing_step', 'fractional_alter'):
            data = simple(); events = deepcopy(data[3]); middle = event_ref(events, 'G4', 1)
            if mode == 'missing_step': events[middle]['pitch'].pop('step')
            else: events[middle]['pitch']['alter'] = q('1/2')
            grid = cells(events, data[5]['span'], data[6])
            with self.subTest(mode=mode):
                result = reading_timeline(events, grid, [data[5]], data[-1], data[4])
                self.assertEqual(result['note_time']['spelling_unresolved'], q(1))
                self.assertEqual(result['note_time']['conditional_nonmember'], q(0))
                self.assertFalse(result['confirmed_nct'])

    def test_inputs_frozen_json_serialization_and_baseline_preserved(self):
        lattice, ir, _, _ = return_fixture(); saved = deepcopy((lattice, ir))
        base = voice_run(lattice, {'status': 'ready'}, ir)
        a = run(lattice, {'status': 'ready'}, ir)
        self.assertEqual((lattice, ir), saved)
        self.assertEqual(a['baseline_version'], base['version'])
        self.assertEqual(a['baseline_summary'], base['summary'])
        self.assertEqual(json.loads(json.dumps(a)), a)
        self.assertFalse(a['gate_changed'])
        self.assertFalse(a['production_modified'])
        self.assertFalse(a['accuracy_measured'])
        for before, after in zip(base['chain_comparisons'], a['chain_comparisons']):
            self.assertEqual(before['interval_tables'], after['interval_tables'])
            for previous, current in zip(before['comparisons'], after['comparisons']):
                self.assertEqual(previous['voice_context_comparison'], current['voice_context_comparison'])
                self.assertGreater(current['hold_change_context']['invariance_checks'], 0)
                self.assertEqual(current['hold_change_context']['status'], 'audited')


if __name__ == '__main__': unittest.main()
