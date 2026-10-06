"""Saved-evidence contrasts, composed genuine XML/native fixtures and pure controls.

The imported TestCase is used as a fixture factory, not inherited or discovered
here. Live parent issuers run only to CREATE synthetic test inputs; the contrast
adapter never issues a live session or re-evaluates role predicates.
"""
from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import native_progression_contrast as contrast
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness.musical_pattern_observation import f, q, digest
import test_factor_native_role_explanations as fixture_module
from test_factor_musical_view import reseal
from test_factor_expanded_hypotheses import span


class SavedProgressionContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.NativeRoleExplanationTests.setUpClass()
        cls.addClassCleanup(fixture_module.NativeRoleExplanationTests.doClassCleanups)
        cls.fixture = fixture_module.NativeRoleExplanationTests()
        cls.cache = {}

    def inputs(self, name='passing', mode='candidate', control=False):
        key = name, mode, control
        if key not in self.cache:
            fixture = self.fixture
            scope = fixture.case(name)[0][1]
            lattice = fixture.record(name)
            selectors = [fixture.selector(name)]
            if mode == 'candidate':
                primary = selectors[0]['origin_ids']
                if len(primary) != 1:
                    raise AssertionError('one-slot candidate factory expected')
                catalog = next(c for c in lattice['catalog_inventory'] if c['span'] == scope['analysis_span'])
                choices = [o for o in catalog['origins'] if o['record_id'] not in primary and not o['blockers']
                    and o['root'] is not None and o['members'] is not None]
                origin = min(choices, key=lambda o: (len(o['members']), o['record_id']))
                selectors.append({**deepcopy(selectors[0]), 'origin_ids': [origin['record_id']]})
            elif mode == 'partition':
                selectors.append(fixture.selector(name, partitions=[
                    (span(0, 2), ('C', Fraction()), fixture_module.members('C', 'E', 'G')),
                    (span(2, 4), ('C', Fraction()), fixture_module.members('C', 'E', 'G'))], assumptions=[None]))
            elif mode == 'transition':
                selectors.append(fixture.selector(name, assumptions=[None] * len(selectors[0]['transition_assumptions'])))
            elif mode == 'key':
                selectors.append(fixture.selector(name, unknown=True))
            elif mode != 'single':
                raise AssertionError(mode)
            session, comparison, bundle = fixture.comparison(name, control=control, selectors=selectors)
            explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
            entries = [{'native_path': p, 'role_path': r, 'comparison_ref': kernels._ref(comparison),
                        'explanation_ref': kernels._ref(explained)} for p, r in zip(comparison['paths'], explained['paths'])]
            self.cache[key] = scope, lattice, entries, {bundle['record_id']: bundle}
        return deepcopy(self.cache[key])

    def result(self, name='passing', mode='candidate', control=False, **limits):
        scope, lattice, entries, bundles = self.inputs(name, mode, control)
        return contrast.compare(scope, lattice, entries, bundles=bundles, **limits)

    def test_candidate_pair_conserves_raw_time_and_no_winner(self):
        result = self.result()
        self.assertEqual(result['summary']['candidate_only_pairs'], 1)
        pair = result['pairs'][0]
        self.assertTrue(pair['raw_time_conserved'])
        self.assertEqual(sum((f(r['duration_quarters']) for r in pair['category_transfer_note_time']), Fraction()),
                         f(pair['raw_total_note_time_quarters']))
        self.assertEqual(sum(map(f, pair['note_time_delta_right_minus_left'].values()), Fraction()), 0)
        self.assertTrue(all(v is False for v in result['flags'].values()))
        self.assertTrue(all(pair[k] is None for k in ('selected', 'rank', 'confidence')))

    def test_fractional_onsets_stay_exact(self):
        result = self.result('rational')
        points = [f(r['span']['start']) for facet in result['facets'] for rows in facet['source_segments'].values() for r in rows]
        self.assertIn(Fraction(1, 3), points)
        self.assertEqual(result['summary']['computed_pairs'], 1)

    def test_reverse_pair_negates_delta_and_swaps_transfers(self):
        scope, lattice, entries, bundles = self.inputs()
        left = contrast.compare(scope, lattice, entries, bundles=bundles)['pairs'][0]
        right = contrast.compare(scope, lattice, list(reversed(entries)), bundles=bundles)['pairs'][0]
        self.assertEqual(left['note_time_delta_right_minus_left'],
                         {k: q(-f(v)) for k, v in right['note_time_delta_right_minus_left'].items()})
        self.assertEqual({(r['left'], r['right']): r['duration_quarters'] for r in left['category_transfer_note_time']},
                         {(r['right'], r['left']): r['duration_quarters'] for r in right['category_transfer_note_time']})

    def test_partition_is_not_fixed_premise_candidate_pair(self):
        result = self.result(mode='partition')
        pair = result['pairs'][0]
        self.assertEqual(pair['comparison_kind'], 'partition')
        self.assertFalse(pair['same_partition'])
        self.assertEqual(pair['right_only_cuts'], [q(2)])
        self.assertEqual(pair['shared_cut_assumptions'], [])
        repeated = result['facets'][1]['cut_signature_observations'][0]
        self.assertTrue(repeated['same_assumed_ordered_root_members'])
        self.assertTrue(repeated['same_signature_is_not_harmonic_boundary_verdict'])

    def test_transition_control_preserves_ordinary_failure(self):
        result = self.result('ordinary_first_adverse', mode='transition')
        self.assertEqual(result['summary']['transition_only_pairs'], 1)
        facet = next(fa for fa in result['facets'] if fa['transition_assumptions'][0] is not None)
        self.assertIs(facet['ordinary_templates'][0]['satisfied'], False)
        evidence = facet['actual_transition_evidence'][0]['ordinary_strategy']
        self.assertIn('role_assessments', evidence)

    def test_reattack_not_relabelled_as_tie(self):
        result = self.result('suspension_reattack', mode='single')
        observations = [o for slot in result['facets'][0]['slot_presentations']
                        for member in slot['member_presentations'] for o in member['observations']]
        self.assertTrue(any(o['tie_chain_ref'] is None for o in observations))
        self.assertEqual(result['summary']['computed_pairs'], 0)

    def test_unknown_key_not_merged_with_known_key(self):
        result = self.result(mode='key')
        self.assertEqual(len(result['facets']), 2)
        self.assertEqual(result['summary']['planned_same_key_same_bundle_pairs'], 0)

    def test_cross_completion_is_never_unioned(self):
        scope, lattice, entries, bundles = self.inputs(mode='single')
        _, _, controls, other_bundles = self.inputs(mode='single', control=True)
        result = contrast.compare(scope, lattice, entries + controls, bundles={**bundles, **other_bundles})
        self.assertEqual(result['summary']['computed_pairs'], 0)
        self.assertNotEqual(result['facets'][0]['bundle_ref'], result['facets'][1]['bundle_ref'])

    def test_empty_is_known_zero_not_role_calculation(self):
        scope, lattice, _, bundles = self.inputs()
        result = contrast.compare(scope, lattice, [], bundles=bundles)
        self.assertEqual(result['summary']['computed_pairs'], 0)
        self.assertEqual(result['facets'], [])

    def test_pair_cap_whole_hold_not_prefix(self):
        result = self.result(max_pairs=0)
        self.assertEqual(result['status'], 'whole_saved_contrast_hold')
        self.assertEqual(result['summary']['withheld_pairs'], 1)
        self.assertEqual(result['facets'], [])
        self.assertEqual(result['pairs'], [])

    def test_work_cap_whole_hold_not_prefix(self):
        result = self.result(work_budget=0)
        self.assertEqual(result['status'], 'whole_saved_contrast_hold')
        self.assertEqual(result['summary']['computed_pairs'], 0)
        self.assertGreater(result['query_plan']['planned_work'], 0)

    def test_exact_planned_budget_boundary(self):
        plan = self.result()['query_plan']['planned_work']
        self.assertEqual(self.result(work_budget=plan)['status'], 'computed_saved_progression_contrasts_not_selected')
        self.assertEqual(self.result(work_budget=plan - 1)['status'], 'whole_saved_contrast_hold')

    def test_inner_linear_cover_visits_are_charged(self):
        scope, lattice, entries, bundles = self.inputs(mode='partition')
        original = contrast._cover
        observed_visits = []
        def measured(rows, a, b):
            observed_visits.append(len(rows))
            return original(rows, a, b)
        with patch.object(contrast, '_cover', side_effect=measured):
            result = contrast.compare(scope, lattice, entries, bundles=bundles)
        self.assertGreater(sum(observed_visits), 0)
        self.assertGreaterEqual(result['query_plan']['pair_refinement_cover_and_reference_work'], sum(observed_visits))

    def test_pure_repeated_source_reference_copies_increase_plan(self):
        scope, _, entries, _ = self.inputs()
        # Planner-only stress control; not a valid new IR or saved-role body.
        small = contrast._plan(scope, entries, [(0, 1)])
        long_closure = deepcopy(scope)
        for sound in long_closure['sound_facts']:
            sound['source_note_refs'] *= 50
        large = contrast._plan(long_closure, entries, [(0, 1)])
        self.assertGreater(large['entry_validation_and_facet_work'], small['entry_validation_and_facet_work'])
        self.assertGreater(large['pair_refinement_cover_and_reference_work'], small['pair_refinement_cover_and_reference_work'])

    def test_boolean_budget_rejected(self):
        with self.assertRaises(ValueError):
            self.result(work_budget=True)

    def test_pure_empty_credit_clause_visits_are_charged_per_atom(self):
        scope, _, entries, _ = self.inputs()
        # Planner-only control: empty-credit clauses still cost attribution visits.
        # These synthetic objects are not submitted as authenticated saved roles.
        small = contrast._plan(scope, entries, [])
        large_entries = deepcopy(entries)
        added = 500
        expected_extra = 0
        for entry in large_entries:
            unions = {r['sound_ref']: len(r['spans'])
                      for r in entry['role_path']['account']['explained_intervals_by_sound']}
            atoms = sum(1 + 2 * unions.get(row['sound_ref'], 0)
                        for profile in entry['native_path']['profiles'] for row in profile['rows'])
            expected_extra += added * (atoms + 1)
            entry['role_path']['clauses'].extend([{'sound_refs': [], 'source_note_refs': [],
                'actual_required_links': [], 'proposed_clips': [], 'prerequisites': {}, 'clips': []}] * added)
        large = contrast._plan(scope, large_entries, [])
        self.assertEqual(large['entry_validation_and_facet_work'] - small['entry_validation_and_facet_work'], expected_extra)

    def test_input_preserved_and_native_producers_not_called(self):
        scope, lattice, entries, bundles = self.inputs()
        before = digest([scope, lattice, entries, bundles])
        with (patch.object(native, 'prepare_lattice', side_effect=AssertionError('no live issuer')),
              patch.object(native, 'compare_prepared', side_effect=AssertionError('no replay')),
              patch.object(roles, 'explain_prepared', side_effect=AssertionError('no role replay'))):
            contrast.compare(scope, lattice, entries, bundles=bundles)
        self.assertEqual(before, digest([scope, lattice, entries, bundles]))

    def test_duplicate_hypothesis_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        with self.assertRaisesRegex(ValueError, 'duplicate_saved_complete'):
            contrast.compare(scope, lattice, entries + [entries[0]], bundles=bundles)

    def test_resealed_raw_profile_tamper_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        path = entries[0]['native_path']
        path['profiles'][0]['rows'][0]['state'] = 'spelling_unresolved'
        changed = reseal(path, 'fmilpath_')
        role = entries[0]['role_path']
        role['native_path_ref'] = kernels._ref(changed)
        role['raw_account_pointer']['parent_path_ref'] = kernels._ref(changed)
        role['clauses'] = []
        entries[0] = {**entries[0], 'native_path': changed, 'role_path': reseal(role, 'fmnrolepath_')}
        with self.assertRaisesRegex(ValueError, 'raw_profile'):
            contrast.compare(scope, lattice, entries, bundles=bundles)

    def test_resealed_account_tamper_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        role = entries[0]['role_path']
        role['account']['raw_total_note_time_quarters'] = q(999)
        entries[0]['role_path'] = reseal(role, 'fmnrolepath_')
        with self.assertRaisesRegex(ValueError, 'union_account'):
            contrast.compare(scope, lattice, entries, bundles=bundles)

    def test_resealed_native_raw_state_tamper_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        path = entries[0]['native_path']
        path['whole_path_account']['raw_state_note_time_quarters']['member'] = q(999)
        changed = reseal(path, 'fmilpath_')
        role = entries[0]['role_path']
        role['native_path_ref'] = kernels._ref(changed)
        role['raw_account_pointer'] = {'parent_path_ref': kernels._ref(changed), 'field': 'whole_path_account',
                                      'sha256': digest(changed['whole_path_account'])}
        role['account']['raw_state_note_time_quarters']['member'] = q(999)
        entries[0] = {**entries[0], 'native_path': changed, 'role_path': reseal(role, 'fmnrolepath_')}
        with self.assertRaisesRegex(ValueError, 'native_raw_account'):
            contrast.compare(scope, lattice, entries, bundles=bundles)

    def test_foreign_scope_reference_rejected(self):
        scope, lattice, entries, bundles = self.inputs()
        path = entries[0]['native_path']
        path['scope_ref']['record_id'] = 'foreign'
        entries[0]['native_path'] = reseal(path, 'fmilpath_')
        with self.assertRaises(ValueError):
            contrast.compare(scope, lattice, entries, bundles=bundles)

    def test_live_seal_alone_not_authority_claim(self):
        result = self.result()
        self.assertEqual(result['source_authority'], contrast.AUTHORITY)
        self.assertFalse(result['flags']['live_native_authority_claimed'])

    def test_bass_uses_literal_cells_not_pooled_note_time(self):
        pair = self.result()['pairs'][0]
        clock = sum((f(c['span']['end']) - f(c['span']['start']) for c in pair['aligned_bass_cells']), Fraction())
        self.assertEqual(clock, 4)
        self.assertGreater(f(pair['raw_total_note_time_quarters']), clock)

    def test_member_presentation_not_arpeggio_confirmation(self):
        facets = self.result()['facets']
        self.assertTrue(all(slot['pooled_support_is_not_arpeggio_confirmation']
                            for facet in facets for slot in facet['slot_presentations']))

    def test_pure_alias_control_does_not_create_member_or_credit_gain(self):
        scope, _, _, _ = self.inputs()
        facet = self.result()['facets'][0]
        # Pure helper control, not a new genuine supplier or parent path.
        alias = deepcopy(facet)
        alias['native_path_ref'] = {'record_id': 'synthetic_alias', 'record_sha256': '0' * 64}
        sounds = {s['sound_ref']: s for s in scope['sound_facts']}
        pair = contrast._pair(facet, alias, sounds)
        self.assertTrue(pair['alias_control'])
        self.assertTrue(all(f(value) == 0 for value in pair['note_time_delta_right_minus_left'].values()))
        self.assertEqual(pair['changed_source_segments'], [])


class PureContrastHelperControls(unittest.TestCase):
    def test_ordered_member_shape_not_set_alias(self):
        left = {'partition': [span(0, 4)], 'transition_assumptions': [],
                'slot_presentations': [{'root': 'C', 'members': ['C', 'E', 'G']}]}
        right = {**deepcopy(left), 'slot_presentations': [{'root': 'C', 'members': ['E', 'C', 'G']}]}
        self.assertEqual(contrast._kind(left, right), 'candidate_only')
        self.assertNotEqual(contrast._signature(left['slot_presentations'][0]),
                            contrast._signature(right['slot_presentations'][0]))

    def test_different_vector_and_members_marked_as_two_changes(self):
        left = {'partition': [span(0, 2), span(2, 4)], 'transition_assumptions': [None],
                'slot_presentations': [{'root': 'C', 'members': ['C']}]}
        right = {**deepcopy(left), 'transition_assumptions': [{'family': 'V7', 'quality': 'M'}],
                 'slot_presentations': [{'root': 'G', 'members': ['G']}]}
        self.assertEqual(contrast._kind(left, right), 'candidate_and_transition')


if __name__ == '__main__':
    unittest.main()
