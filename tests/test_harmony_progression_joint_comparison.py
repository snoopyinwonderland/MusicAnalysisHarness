"""Complete-path joint accounts, scope conservation and oversegmentation controls."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_catalog_resolution import pitch_pair
from musicanote_harness.harmony_context_bundle import bundle
from musicanote_harness.harmony_progression_joint_comparison import compare, vector
from test_harmony_progression_context import make, path
from test_harmony_context_bundle import data
from test_harmony_progression_resolution import fixture as resolution_fixture


def packaged(lattice, ir=None):
    lattice = deepcopy(lattice)
    for edge in lattice['edges']:
        edge['unspelled_candidate_refs'] = []
        for ri, reading in enumerate(edge['readings']):
            reading.update(origin_pointer='/synthetic/' + str(ri), provider='synthetic',
                           display_label='synthetic-' + str(ri), root_provenance='synthetic')
            scoped = [s for s in lattice['events'] if f(s['span']['start']) < f(edge['span']['end'])
                      and f(s['span']['end']) > f(edge['span']['start'])]
            observed = {tuple(pitch_pair(s['pitch'])) for s in scoped}
            reading['missing_spellings'] = [m for m in reading['members'] if tuple(m) not in observed]
    stored = {'sample': {'sample_id': 'joint-synthetic', 'span': deepcopy(lattice['plan']['context_span'])},
              'summary': {'source_labels_used': False}, 'stages': {
                  'lattice': lattice, 'relations': {'status': 'ready', 'plan': {'pairs': []}, 'results': []},
                  'hold_change': {'status': 'ready', 'chain_comparisons': []}}}
    return bundle(ir or {'sounding_events': lattice['events']}, stored)


def proposals(*paths):
    return [{'proposal_id': 'proposal-' + str(i), 'path': p} for i, p in enumerate(paths)]


def passing():
    lattice, linked = make()
    hold = path(lattice, [(0, 3, 0)])
    same = path(lattice, [(0, 1, 0), (1, 2, 0), (2, 3, 0)])
    changed = path(lattice, [(0, 1, 0), (1, 2, 2), (2, 3, 0)])
    return packaged(lattice), proposals(hold, same, changed), linked


class JointComparisonTests(unittest.TestCase):
    def test_every_complete_proposal_and_assignment_are_accounted(self):
        b, p, _ = passing(); result = compare(b, p)
        self.assertEqual(len(result['evaluations']), 3 * len(b['stages']['lattice']['assignments']))
        self.assertEqual(len(result['pairwise_comparisons']), 3 * len(b['stages']['lattice']['assignments']))
        self.assertTrue(result['evaluation_inventory_complete'])
        self.assertTrue(result['pairwise_comparison_inventory_complete'])
        self.assertFalse(result['comparison_scope_exhaustive_over_all_harmonies'])
        for row in result['evaluations']:
            self.assertEqual(row['summary']['total_note_time'], q(3))
            self.assertEqual(sum(map(f, row['evidence']['accounting']['note_time'].values())), 3)
            self.assertIsNone(row['selected'])
        self.assertIsNone(result['selected'])

    def test_same_member_split_preserves_conditional_full_path_context(self):
        b, p, linked = passing(); result = compare(b, p[:2])
        row = next(v for v in result['pairwise_comparisons'] if v['assignment_ref'] == linked)
        self.assertEqual(row['boundary_count_delta'], 2)
        self.assertTrue(row['same_spelled_member_sets_on_all_cells'])
        self.assertTrue(row['raw_membership_invariant'])
        self.assertTrue(row['conditional_accounting_invariant_under_same_assignment'])
        self.assertTrue(row['same_member_sets_alone_do_not_establish_change'])
        self.assertIsNone(row['preferred'])

    def test_extra_boundaries_gain_membership_not_accuracy(self):
        b, p, _ = passing(); result = compare(b, [p[0], p[2]])
        for row in result['pairwise_comparisons']:
            self.assertEqual(row['raw_note_time_delta_second_minus_first']['member'], q(1))
            self.assertEqual(row['boundary_count_delta'], 2)
            self.assertTrue(row['membership_gain_with_more_boundaries'])
            self.assertFalse(row['accuracy_measured'])
            self.assertFalse(row['harmonic_change_confirmed'])

    def test_nct_evidence_is_not_union_of_assignments(self):
        b, p, linked = passing(); result = compare(b, p[:1])
        linked_row = next(v for v in result['evaluations'] if v['assignment_ref'] == linked)
        unlinked = next(a['assignment_id'] for a in b['stages']['lattice']['assignments'] if not a['links'])
        none_row = next(v for v in result['evaluations'] if v['assignment_ref'] == unlinked)
        self.assertEqual(linked_row['evidence']['accounting']['note_time']['conditional_nonmember'], q(1))
        self.assertEqual(none_row['evidence']['accounting']['note_time']['conditional_nonmember'], q(0))
        self.assertEqual(none_row['evidence']['accounting']['note_time']['unexplained_nonmember'], q(1))
        self.assertEqual(linked_row['raw_note_time'], none_row['raw_note_time'])
        self.assertEqual(result['pairwise_comparisons'], [])

    def test_pairwise_refs_always_same_assignment(self):
        b, p, _ = passing(); result = compare(b, p)
        by_id = {r['evaluation_id']: r for r in result['evaluations']}
        for row in result['pairwise_comparisons']:
            self.assertEqual(by_id[row['first_evaluation_ref']]['assignment_ref'], row['assignment_ref'])
            self.assertEqual(by_id[row['second_evaluation_ref']]['assignment_ref'], row['assignment_ref'])
            self.assertNotIn('first', row)
            self.assertNotIn('second', row)

    def test_withheld_nonmember_stays_distinct(self):
        b, p, linked = passing()
        lattice = b['stages']['lattice']
        lattice['withheld_pattern_reasons'] = {shape['pattern_id']: ['synthetic_withheld'] for shape in lattice['patterns']}
        row = next(v for v in compare(b, p[:1])['evaluations'] if v['assignment_ref'] == linked)
        self.assertEqual(row['evidence']['accounting']['note_time']['withheld_nonmember'], q(1))
        self.assertEqual(row['evidence']['accounting']['note_time']['conditional_nonmember'], q(0))
        self.assertFalse(row['confirmed_nct'])

    def test_blocked_candidates_do_not_exempt_nonmembers(self):
        b, p, linked = passing(); lattice = b['stages']['lattice']
        lattice['edges'][p[0]['path'][0]['edge']]['readings'][0]['abstention_reasons'] = ['synthetic_blocker']
        row = next(v for v in compare(b, p[:1])['evaluations'] if v['assignment_ref'] == linked)
        self.assertEqual(row['blocked_candidate_note_time'], q(3))
        self.assertEqual(row['evidence']['accounting']['note_time']['conditional_nonmember'], q(0))
        self.assertEqual(row['evidence']['segments'][0]['candidate_blockers'], ['synthetic_blocker'])

    def test_exact_rational_time_is_not_float_rounded(self):
        r, aid = make([('C4', 0, '1/3'), ('D4', '1/3', '2/3'), ('E4', '2/3', 3)])
        b = packaged(r); p = proposals(path(r, [(0, 3, 0)]))
        row = next(v for v in compare(b, p)['evaluations'] if v['assignment_ref'] == aid)
        self.assertEqual(row['raw_note_time']['nonmember_not_confirmed_nct'], q('1/3'))
        self.assertEqual(row['summary']['total_note_time'], q(3))

    def test_vector_once_per_path_assignment(self):
        b, p, _ = passing()
        with patch('musicanote_harness.harmony_progression_joint_comparison.vector', wraps=vector) as called:
            result = compare(b, p)
        self.assertEqual(called.call_count, result['plan']['planned_evaluations'])

    def test_path_fixed_evidence_cached_without_assignment_union(self):
        from musicanote_harness.harmony_progression_joint_comparison import _bass, _missing, _stored_relations
        b, p, _ = passing()
        with (patch('musicanote_harness.harmony_progression_joint_comparison._bass', wraps=_bass) as bass,
                patch('musicanote_harness.harmony_progression_joint_comparison._missing', wraps=_missing) as missing,
                patch('musicanote_harness.harmony_progression_joint_comparison._stored_relations', wraps=_stored_relations) as relations):
            compare(b, p)
        self.assertEqual(bass.call_count, len(p))
        self.assertEqual(missing.call_count, len(p))
        self.assertEqual(relations.call_count, len(p))

    def test_inversion_uses_observed_bass_only_conditionally(self):
        ir, stored, p = data([('E3', 0, 1, 'bass'), ('C4', 0, 1, 'root'), ('G4', 0, 1, 'fifth'),
                              ('B-4', 0, 1, 'seventh'), ('F3', 1, 3, 'bass'), ('F4', 1, 3, 'root'),
                              ('A4', 1, 3, 'third'), ('C5', 1, 3, 'fifth')])
        row = compare(bundle(ir, stored), proposals(p))['evaluations'][0]
        self.assertEqual(row['bass']['bass_roles'][0]['inversion_candidate'], 1)
        self.assertFalse(row['bass']['inversion_confirmed'])
        self.assertFalse(row['bass']['structural_bass_confirmed'])

    def test_same_assignment_direct_resolution_no_source_keys(self):
        lattice, p, ir = resolution_fixture(return_ir=True); b = packaged(lattice, ir)
        rows = compare(b, proposals(p))['evaluations']
        linked = next(r for r in rows if r['assignment_ref'] == 'linked')
        unlinked = next(r for r in rows if r['assignment_ref'] == 'none')
        self.assertEqual(linked['sampled_assignment_resolution']['relations'][0]['status'], 'direct_resolution_supported_hypothesis')
        self.assertEqual(unlinked['sampled_assignment_resolution']['relations'][0]['status'], 'shape_relation_only')
        for row in rows:
            self.assertEqual(row['sampled_assignment_resolution']['reference_key_hypotheses'], [])
            self.assertEqual(row['sampled_assignment_resolution']['resolution_link_scope'], 'sampled_assignment')
            self.assertFalse(row['function_confirmed'])

    def test_stored_temporal_witness_does_not_exempt_foreign_note(self):
        ir, stored, p = data(); b = bundle(ir, stored)
        row = compare(b, proposals(p))['evaluations'][0]
        self.assertTrue(row['stored_adjacency_relations'])
        self.assertGreater(f(row['evidence']['accounting']['note_time']['unexplained_nonmember']), 0)
        relation = row['stored_adjacency_relations'][0]
        self.assertEqual(relation['temporal_status'], 'temporal_resolution_possible')
        self.assertFalse(relation['merged_with_sampled_assignment'])
        self.assertFalse(relation['witness_exempts_other_foreign_notes'])

    def test_missing_tone_not_invented_or_boundary_extended(self):
        ir, stored, p = data([('C3', 0, 1, 'bass'), ('E4', 0, 2, 'lead'), ('B-4', 0, 1, 'seventh'),
                              ('F3', 1, 3, 'bass'), ('F4', 2, 3, 'lead'), ('A4', 1, 3, 'seventh'),
                              ('C5', 1, 3, 'root'), ('G4', 1, 2, 'fifth')])
        row = compare(bundle(ir, stored), proposals(p))['evaluations'][0]
        missing = row['missing_and_omission_by_origin'][0]['missing_members']
        fifth = next(v for v in missing if v['pitch'] == ['G', 0])
        self.assertTrue(fifth['available_elsewhere_in_parent_event_refs'])
        self.assertFalse(fifth['boundary_extension_authorized'])
        self.assertFalse(fifth['omission_confirmed'])
        self.assertFalse(row['missing_and_omission_by_origin'][0]['omission_exempts_foreign_notes'])

    def test_partial_gap_overlap_bad_indices_fail_closed(self):
        b, p, _ = passing()
        malformed = [p[1]['path'][:2], p[1]['path'][1:], p[1]['path'] + p[1]['path'],
                     [{'edge': -1, 'reading': 0}], [{'edge': True, 'reading': 0}],
                     [{'edge': 0, 'reading': 999}], []]
        for bad in malformed:
            with self.subTest(path=bad), self.assertRaises(ValueError): compare(b, proposals(bad))

    def test_budget_preserves_inventory_without_preferred_subset(self):
        b, p, _ = passing()
        for kwargs, status in [({'max_assignments': 1}, 'assignment_budget_abstention_no_pruning'),
                               ({'max_evaluations': 1}, 'evaluation_budget_abstention_no_pruning')]:
            with self.subTest(kwargs=kwargs):
                result = compare(b, p, **kwargs)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['proposal_inventory'], p)
                self.assertEqual(result['assignment_inventory'], b['stages']['lattice']['assignments'])
                self.assertEqual(result['evaluations'], [])
                self.assertFalse(result['evaluation_inventory_complete'])

    def test_pairwise_budget_keeps_all_accounting_without_subset_comparisons(self):
        b, p, _ = passing(); result = compare(b, p, max_comparisons=1)
        self.assertEqual(result['status'], 'evaluated_paths_pairwise_budget_abstention_no_pruning')
        self.assertTrue(result['evaluation_inventory_complete'])
        self.assertFalse(result['pairwise_comparison_inventory_complete'])
        self.assertEqual(len(result['evaluations']), result['plan']['planned_evaluations'])
        self.assertEqual(result['pairwise_comparisons'], [])

    def test_semantic_origin_groups_are_adapters_not_votes(self):
        ir, stored, p = data(); lattice = stored['stages']['lattice']
        for choice in p:
            edge = lattice['edges'][choice['edge']]
            duplicate = deepcopy(edge['readings'][choice['reading']])
            duplicate['candidate_ref'] = 'other-provider-' + str(choice['edge'])
            duplicate['origin_pointer'] = '/other-provider'
            edge['readings'].append(duplicate)
        b = bundle(ir, stored)
        groups = [{'group_id': 'group-' + str(i), 'origin_reading_keys': [choice,
            {'edge': choice['edge'], 'reading': len(lattice['edges'][choice['edge']]['readings']) - 1}]}
            for i, choice in enumerate(p)]
        search = {'status': 'proposals_not_verdict', 'exhaustive': False, 'exclusions': ['cap'],
                  'semantic_groups': groups, 'proposals': [{'proposal_id': 'grouped', 'path': p,
                    'semantic_group_refs': [g['group_id'] for g in groups]}]}
        result = compare(b, search)
        self.assertEqual(result['search_provenance']['semantic_groups'], groups)
        self.assertFalse(result['search_provenance']['exhaustive'])
        self.assertEqual(len(result['evaluations']), len(lattice['assignments']))
        self.assertEqual(len(result['evaluations'][0]['missing_and_omission_by_origin']), 4)
        self.assertFalse(result['evaluations'][0]['stored_adjacency_relations'][0]['same_semantic_pair_origin_variants_are_independent_votes'])

    def test_nonidentical_origin_groups_cannot_merge(self):
        b, p, _ = passing(); path_row = p[0]
        other = {'edge': path_row['path'][0]['edge'], 'reading': 1}
        search = {'semantic_groups': [{'group_id': 'wrong', 'origin_reading_keys': path_row['path'] + [other]}],
                  'proposals': [{**path_row, 'semantic_group_refs': ['wrong']}]}
        with self.assertRaisesRegex(ValueError, 'nonidentical'): compare(b, search)

    def test_inputs_immutable_and_outputs_independent(self):
        b, p, _ = passing(); saved = deepcopy((b, p))
        result = compare(b, p)
        self.assertEqual((b, p), saved)
        result['proposal_inventory'][0]['path'][0]['reading'] = 99
        result['evaluations'][0]['evidence']['cells'][0]['event_refs'].clear()
        self.assertEqual((b, p), saved)

    def test_invalid_budgets_duplicate_id_and_selected_input_rejected(self):
        b, p, _ = passing()
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError): compare(b, p, max_assignments=value)
        with self.assertRaisesRegex(ValueError, 'duplicate_proposal'): compare(b, p + p[:1])
        changed = deepcopy(b); changed['selected'] = 0
        with self.assertRaisesRegex(ValueError, 'selected_input'): compare(changed, p)
        changed = deepcopy(b); changed['source_labels_used'] = True
        with self.assertRaisesRegex(ValueError, 'nonblind'): compare(changed, p)

    def test_no_assignment_or_lattice_abstention_remains_local(self):
        b, p, _ = passing(); b['stages']['lattice']['assignments'] = []
        self.assertEqual(compare(b, p)['status'], 'no_stored_assignments')
        b['stages']['lattice']['status'] = 'edge_budget_abstention_no_pruning'
        self.assertEqual(compare(b, p)['status'], 'preserved_lattice_abstention')
        self.assertEqual(compare(b, p)['proposal_inventory'], p)

    def test_search_artifact_bound_to_same_bundle_and_sample(self):
        from musicanote_harness.harmony_progression_search import search
        b, _, _ = passing(); found = search(b)
        self.assertTrue(compare(b, found)['evaluation_inventory_complete'])
        changed = deepcopy(b); changed['sample']['sample_id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'hash_mismatch'): compare(changed, found)
        broken = deepcopy(found); broken['sample']['sample_id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'sample_mismatch'): compare(b, broken)
        broken = deepcopy(found); broken.pop('input_bundle_content_sha256')
        with self.assertRaisesRegex(ValueError, 'binding_missing'): compare(b, broken)

    def test_nonblind_search_input_cannot_masquerade_as_proposal_search(self):
        b, p, _ = passing()
        with self.assertRaisesRegex(ValueError, 'nonblind'):
            compare(b, {'proposals': p, 'source_labels_used': True})


if __name__ == '__main__': unittest.main()
