"""Complete-path proposals with exact geometry and explicit approximation."""
from copy import deepcopy
from fractions import Fraction
import unittest

from musicanote_harness.formal_ir import q
from musicanote_harness.harmony_joint import f
from musicanote_harness.harmony_context_bundle import bundle
from musicanote_harness.harmony_progression_context import evaluate
from musicanote_harness.harmony_progression_search import search
from test_harmony_context_bundle import data


def fixture(specs=None):
    ir, stored, _ = data(specs)
    return bundle(ir, stored)


def full(result):
    return search(result, max_segments=30, per_state_limit=10000, max_complete_paths=10000, transition_budget=1000000)


def pattern(result, suffix='a', start=1, end=2, assignment='none'):
    lattice = result['stages']['lattice']
    sid = next(s['sounding_event_id'] for s in lattice['events'] if s['pitch']['spelling'] == 'E4')
    return {'pattern_id': 'synthetic-' + suffix, 'kind': 'held_candidate', 'event_refs': [sid],
        'affected_event_ref': sid, 'nonmember_span': {'start': q(start), 'end': q(end)},
        'supporting_assignment_refs': [assignment], 'requirements': [
            {'event_ref': sid, 'state': 'member', 'span': {'start': q('1/2'), 'end': q(1)}},
            {'event_ref': sid, 'state': 'nonmember_not_confirmed_nct', 'span': {'start': q(1), 'end': q(2)}}]}


class ProgressionSearchTests(unittest.TestCase):
    def test_every_proposal_is_complete_context_and_exact_note_time(self):
        result = fixture(); proposed = search(result)
        total = sum((f(c['span']['end']) - f(c['span']['start'])) * len(c['event_refs'])
                    for c in result['stages']['lattice']['cells'])
        self.assertTrue(proposed['proposals'])
        for p in proposed['proposals']:
            evaluated = evaluate(result['stages']['lattice'], p['path'], 'none')
            self.assertEqual(f(p['objective']['total_note_time']), total)
            self.assertTrue(p['complete_context_path'])
            self.assertEqual(evaluated['context_span'], result['sample']['span'])
            self.assertIsNone(p['selected'])
            self.assertFalse(p['proposal_order_is_harmonic_preference'])
        self.assertIsNone(proposed['selected'])
        self.assertFalse(proposed['confidence_generated'])

    def test_counts_are_exhaustive_only_when_all_stored_semantic_paths_emitted(self):
        result = fixture(); proposed = full(result)
        self.assertTrue(proposed['exhaustive'])
        self.assertEqual(len(proposed['proposals']), proposed['universe']['complete_semantic_paths'])
        self.assertEqual(proposed['exclusions'], [])
        self.assertEqual(proposed['search_counts']['semantic_complete_paths_not_emitted'], 0)

    def test_segment_strata_preserve_hold_and_split_not_automatic_simplification(self):
        result = fixture(); proposed = search(result)
        counts = {p['objective']['segment_count'] for p in proposed['proposals']}
        self.assertIn(1, counts); self.assertIn(2, counts)
        self.assertTrue(proposed['objective']['segment_count_is_diversity_stratum'])
        self.assertIsNone(proposed['objective']['segment_penalty'])

    def test_exact_rational_triplet_membership_is_not_float(self):
        result = fixture([('C3', 0, '1/3', 'bass'), ('E4', '1/3', '2/3', 'lead'),
                          ('G4', '2/3', 1, 'fifth'), ('F3', 1, 3, 'bass'),
                          ('A4', 1, 3, 'lead'), ('C5', 1, 3, 'fifth')])
        proposed = search(result)
        self.assertTrue(any(f(g['objective_increment']['raw_nonmember_note_time']).denominator == 3
                            for g in proposed['semantic_groups']))
        for p in proposed['proposals']:
            for value in p['objective'].values():
                self.assertNotIsInstance(value, float)

    def test_same_spelled_members_split_conserve_raw_note_time(self):
        result = fixture(); proposed = full(result); bank = {g['group_id']: g for g in proposed['semantic_groups']}
        coherent = [p for p in proposed['proposals'] if all(
            bank[gid]['root_spelling'] == ['C', 0] for gid in p['semantic_group_refs'])]
        self.assertGreater(len({p['objective']['segment_count'] for p in coherent}), 1)
        totals = {(f(p['objective']['raw_nonmember_note_time']),
                   f(p['objective']['spelling_unresolved_note_time'])) for p in coherent}
        self.assertEqual(len(totals), 1)

    def test_same_members_split_has_invariant_cell_local_nct_bound(self):
        result = fixture(); result['stages']['lattice']['patterns'] = [pattern(result)]
        proposed = full(result); bank = {g['group_id']: g for g in proposed['semantic_groups']}
        coherent = [p for p in proposed['proposals'] if all(
            bank[gid]['root_spelling'] == ['F', 0] for gid in p['semantic_group_refs'])]
        values = {f(p['objective']['optimistic_local_nct_potential_note_time']) for p in coherent}
        self.assertEqual(values, {Fraction(1)})
        # The preparation required C membership, so all-F whole paths activate no
        # pattern. The search bound deliberately was not an actual NCT exemption.
        for p in coherent:
            evaluated = evaluate(result['stages']['lattice'], p['path'], 'none')
            self.assertEqual(evaluated['active_pattern_refs'], [])
        self.assertFalse(proposed['objective']['local_nct_bound_is_exemption'])

    def test_overlapping_nct_patterns_union_duration_not_double_count(self):
        result = fixture(); lattice = result['stages']['lattice']
        lattice['patterns'] = [pattern(result), pattern(result, 'b', '3/2', 2)]
        proposed = search(result)
        for g in proposed['semantic_groups']:
            inc = g['objective_increment']
            self.assertLessEqual(f(inc['optimistic_local_nct_potential_note_time']), f(inc['raw_nonmember_note_time']))
        whole_f = next(g for g in proposed['semantic_groups'] if g['from'] == 0 and
                       g['to'] == len(lattice['plan']['points']) - 1 and g['root_spelling'] == ['F', 0])
        self.assertEqual(whole_f['objective_increment']['optimistic_local_nct_potential_note_time'], q(1))

    def test_unknown_assignment_and_withheld_pattern_have_no_bound(self):
        result = fixture(); lattice = result['stages']['lattice']
        lattice['patterns'] = [pattern(result, assignment='not-sampled')]
        self.assertTrue(all(f(g['objective_increment']['optimistic_local_nct_potential_note_time']) == 0
                            for g in search(result)['semantic_groups']))
        lattice['patterns'] = [pattern(result)]; lattice['withheld_pattern_reasons']['synthetic-a'] = ['ambiguous_voice']
        self.assertTrue(all(f(g['objective_increment']['optimistic_local_nct_potential_note_time']) == 0
                            for g in search(result)['semantic_groups']))

    def test_duplicate_origins_grouped_but_never_lost_or_preferred(self):
        ir, stored, _ = data(); edge = stored['stages']['lattice']['edges'][0]
        extra = deepcopy(edge['readings'][0]); extra.update(candidate_ref='other-origin', provider='another-provider')
        edge['readings'].append(extra)
        proposed = full(bundle(ir, stored))
        group = next(g for g in proposed['semantic_groups'] if g['edge_index'] == 0 and len(g['origins']) == 2)
        self.assertEqual({o['candidate_ref'] for o in group['origins']}, {'0', 'other-origin'})
        self.assertEqual(len(group['origin_reading_keys']), 2)
        self.assertFalse(group['representative_origin_preferred'])
        self.assertGreater(proposed['universe']['complete_origin_paths'], proposed['universe']['complete_semantic_paths'])

    def test_enharmonic_roots_members_and_blockers_are_not_merged(self):
        ir, stored, _ = data(); edge = stored['stages']['lattice']['edges'][0]
        a = deepcopy(edge['readings'][0]); a['root_spelling'] = ['B', 1]; a['candidate_ref'] = 'enharmonic'
        b = deepcopy(edge['readings'][0]); b['abstention_reasons'] = ['blocked']; b['candidate_ref'] = 'blocked'
        edge['readings'].extend([a, b])
        proposed = search(bundle(ir, stored)); groups = [g for g in proposed['semantic_groups'] if g['edge_index'] == 0]
        self.assertEqual(len(groups), 4)
        blocked = next(g for g in groups if g['candidate_blockers'])
        self.assertGreater(f(blocked['objective_increment']['blocked_note_time']), 0)

    def test_unspelled_candidates_remain_explicit_capability_gap(self):
        ir, stored, _ = data(); stored['stages']['lattice']['edges'][0]['unspelled_candidate_refs'] = ['unspelled-origin']
        proposed = full(bundle(ir, stored))
        self.assertFalse(proposed['exhaustive'])
        self.assertEqual(proposed['unspelled_candidates'][0]['candidate_ref'], 'unspelled-origin')
        self.assertIn('unspelled_candidate_path_capability_missing', [e['reason'] for e in proposed['exclusions']])

    def test_segment_state_output_and_transition_caps_have_ledgers(self):
        result = fixture()
        for kwargs, reason in [({'max_segments': 1}, 'segment_limit_approximation'),
                               ({'per_state_limit': 1}, 'approximate_prefix_frontier'),
                               ({'max_complete_paths': 1}, 'complete_path_capacity_approximation'),
                               ({'transition_budget': 1}, 'transition_budget_approximation')]:
            with self.subTest(kwargs=kwargs):
                proposed = search(result, **kwargs)
                self.assertFalse(proposed['exhaustive'])
                self.assertIn(reason, [e['reason'] for e in proposed['exclusions']])
                self.assertGreater(proposed['search_counts']['semantic_complete_paths_not_emitted'], 0)
                if reason == 'transition_budget_approximation':
                    self.assertEqual(proposed['search_counts']['transitions_executed'], 1)
                    self.assertEqual(proposed['proposals'], [])

    def test_missing_members_not_fragmentation_reward(self):
        result = fixture(); proposed = search(result)
        self.assertFalse(proposed['objective']['missing_member_count_is_objective'])
        self.assertTrue(all('missing_members' not in g['objective_increment'] for g in proposed['semantic_groups']))

    def test_positive_integer_budgets(self):
        result = fixture()
        for value in [0, -1, True, 1.5, None]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'positive_integer'):
                    search(result, per_state_limit=value)

    def test_inventory_loss_geometry_time_and_selected_integrity_fail_closed(self):
        result = fixture()
        for kind in ['inventory', 'time', 'geometry', 'selected', 'labels', 'meaning']:
            broken = deepcopy(result)
            if kind == 'inventory': broken['reading_inventory'].pop()
            elif kind == 'time': broken['reading_inventory'][0]['note_time']['member'] = q(999)
            elif kind == 'geometry': broken['stages']['lattice']['edges'][0]['span']['end'] = q(999)
            elif kind == 'selected': broken['selected'] = 'a-verdict'
            elif kind == 'labels': broken['source_labels_used'] = True
            else: broken['reading_inventory'][0]['root_spelling'] = ['D', 0]
            with self.subTest(kind=kind), self.assertRaises(ValueError): search(broken)

    def test_lattice_abstention_preserved_no_implicit_candidate_search(self):
        result = fixture(); result['stages']['lattice']['status'] = 'edge_budget_abstention_no_pruning'
        proposed = search(result)
        self.assertEqual(proposed['status'], 'preserved_lattice_abstention')
        self.assertEqual(proposed['proposals'], [])
        self.assertFalse(proposed['exhaustive'])

    def test_deterministic_and_inputs_outputs_independent(self):
        result = fixture(); saved = deepcopy(result)
        a = search(result); b = search(result)
        self.assertEqual(a, b); self.assertEqual(result, saved)
        a['semantic_groups'][0]['members'][0][0] = 'changed'
        a['sample']['sample_id'] = 'changed'
        self.assertEqual(result, saved)

    def test_provider_reading_order_cannot_change_semantic_proposal_count_or_objective(self):
        ir, stored, _ = data()
        # Relation survey indices are independent input origin data; this test
        # uses an explicit empty survey rather than relabeling those indices.
        stored['stages']['relations'] = {'status': 'ready', 'plan': {'pairs': []}, 'results': []}
        stored['stages']['hold_change'] = {'status': 'ready', 'chain_comparisons': []}
        first = stored['stages']['lattice']['edges'][0]
        extra = deepcopy(first['readings'][0]); extra['candidate_ref'] = 'additional-origin'
        first['readings'].append(extra)
        a = search(bundle(ir, stored), per_state_limit=2, max_complete_paths=5)
        for edge in stored['stages']['lattice']['edges']: edge['readings'].reverse()
        b = search(bundle(ir, stored), per_state_limit=2, max_complete_paths=5)
        self.assertEqual(a['universe'], b['universe'])
        self.assertEqual([(p['proposal_id'], p['semantic_group_refs'], p['objective']) for p in a['proposals']],
                         [(p['proposal_id'], p['semantic_group_refs'], p['objective']) for p in b['proposals']])
        self.assertEqual(a['search_counts'], b['search_counts'])


if __name__ == '__main__': unittest.main()
