"""Genuine archived-fixture policy tests, not saved-loader mock accuracy tests."""
from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import native_progression_policy as policy
from musicanote_harness import native_progression_contrast as parent
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as sealed
from musicanote_harness.musical_pattern_observation import digest, f
import test_native_progression_contrast as factories
from test_factor_musical_view import reseal


class ProgressionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factories.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(factories.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = factories.SavedProgressionContrastTests()

    def inputs(self, name='ordinary', mode='single', control=False, **limits):
        scope, lattice, entries, bundles = self.fixture.inputs(name, mode, control)
        record = parent.compare(scope, lattice, entries, bundles=bundles, **limits)
        return scope, lattice, record, bundles

    def result(self, name='ordinary', mode='single', control=False, **limits):
        scope, lattice, record, bundles = self.inputs(name, mode, control)
        return policy.evaluate(scope, lattice, record, bundles=bundles, **limits)

    def custom(self, name, selectors):
        fx = self.fixture.fixture
        scope, lattice = fx.case(name)[0][1], fx.record(name)
        session, comparison, bundle = fx.comparison(name, selectors=selectors)
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{'native_path': p, 'role_path': r, 'comparison_ref': sealed._ref(comparison),
                    'explanation_ref': sealed._ref(explained)} for p, r in zip(comparison['paths'], explained['paths'])]
        bundles = {bundle['record_id']: bundle}
        return scope, lattice, parent.compare(scope, lattice, entries, bundles=bundles), bundles

    @staticmethod
    def reasons(result):
        return {d['reason'] for a in result['alternatives'] for d in a['diagnostics']}

    def test_supported_is_conditional_not_selected_ranked_or_gold(self):
        result = self.result()
        self.assertEqual(result['summary']['conditional_function_supported_alternatives'], 1)
        self.assertEqual(result['alternatives'][0]['status'], policy.STATUSES[0])
        self.assertTrue(all(v is False for v in result['flags'].values()))
        self.assertTrue(all(result[k] is None for k in ('selected', 'rank', 'confidence')))
        self.assertNotIn('tentative_proposal_ref', result)

    def test_inputs_and_parent_records_unchanged(self):
        scope, lattice, record, bundles = self.inputs()
        before = digest([scope, lattice, record, bundles])
        result = policy.evaluate(scope, lattice, record, bundles=bundles)
        self.assertEqual(before, digest([scope, lattice, record, bundles]))
        self.assertEqual(result['parent_contrast_ref'], sealed._ref(record))
        self.assertEqual(result['logical_universe'], record['logical_universe'])

    def test_policy_never_replays_native_role_or_contrast_producers(self):
        scope, lattice, record, bundles = self.inputs()
        with patch.object(native, 'prepare_lattice', side_effect=AssertionError('replay')), \
             patch.object(native, 'compare_prepared', side_effect=AssertionError('replay')), \
             patch.object(roles, 'prepare_explanations', side_effect=AssertionError('replay')), \
             patch.object(roles, 'explain_prepared', side_effect=AssertionError('replay')), \
             patch.object(parent, 'compare', side_effect=AssertionError('replay')):
            self.assertEqual(policy.evaluate(scope, lattice, record, bundles=bundles)['summary']['evaluated_entries'], 1)

    def test_unknown_key_holds_even_literal_members_are_present(self):
        fx = self.fixture.fixture
        scope, lattice, record, bundles = self.custom('ordinary', [fx.selector('ordinary', unknown=True)])
        result = policy.evaluate(scope, lattice, record, bundles=bundles)
        self.assertEqual(result['summary']['held_alternatives'], 1)
        self.assertIn('explicit_key_coordinate_unavailable', self.reasons(result))

    def test_unknown_and_known_keys_remain_separate(self):
        result = self.result('passing', mode='key')
        self.assertEqual(result['summary']['fixed_premise_groups'], 2)
        self.assertNotEqual(*[g['premises']['key_ref'] for g in result['fixed_premise_groups']])

    def test_no_link_control_is_completion_failure_not_global_chord_rejection(self):
        result = self.result(control=True)
        self.assertEqual(result['summary']['held_alternatives'], 1)
        self.assertEqual(result['summary']['declared_requirement_not_supported_alternatives'], 0)
        self.assertIn('whole_role_template_not_satisfied_under_this_completion', self.reasons(result))
        blockers = [b for role in result['alternatives'][0]['transition_assessments'][0]['individual_roles']
                    for occurrence in role['occurrences'] for b in occurrence['blockers']]
        self.assertIn('first_changed_endpoint_not_linked_in_this_complete_witness', blockers)

    def test_individual_resolution_cannot_replace_whole_ordinary_template(self):
        result = self.result('ordinary_first_adverse')
        ev = result['alternatives'][0]['transition_assessments'][0]
        self.assertTrue(any(r['satisfied_under_this_bundle'] is True for r in ev['individual_roles']))
        self.assertIs(ev['ordinary_template_support'], False)
        self.assertEqual(result['summary']['conditional_function_supported_alternatives'], 0)

    def test_declared_target_quality_mismatch_only_filters_that_requirement(self):
        fx = self.fixture.fixture
        scope, lattice, record, bundles = self.custom('ordinary', [fx.selector('ordinary', assumptions=[{'family': 'V7', 'quality': 'm'}])])
        result = policy.evaluate(scope, lattice, record, bundles=bundles)
        self.assertEqual(result['summary']['declared_requirement_not_supported_alternatives'], 1)
        self.assertIn('target_triad_core_shape_compatible_false', self.reasons(result))
        self.assertEqual(len(result['alternatives']), 1)
        self.assertIn('not_harmony_verdict', result['alternatives'][0]['claim_scope'])

    def test_full_hold_not_vacuous_ordinary_support(self):
        result = self.result('single')
        self.assertEqual(result['summary']['held_alternatives'], 1)
        self.assertIn('no_internal_functional_relation_not_vacuous_support', self.reasons(result))

    def test_none_transition_not_vacuous_functional_support(self):
        result = self.result('ordinary', mode='transition')
        self.assertEqual(result['summary']['conditional_function_supported_alternatives'], 1)
        self.assertEqual(result['summary']['held_alternatives'], 1)
        self.assertEqual(result['summary']['fixed_premise_groups'], 2)

    def test_same_signature_extra_cut_is_hold_not_automatic_merge(self):
        result = self.result('passing', mode='partition')
        self.assertIn('same_signature_cut_requires_independent_boundary_evidence', self.reasons(result))
        self.assertEqual(len(result['alternatives']), 2)
        self.assertEqual(result['summary']['fixed_premise_groups'], 2)

    def test_different_member_counts_do_not_rank_or_propose_full_hold(self):
        result = self.result('passing', mode='candidate')
        self.assertEqual(result['summary']['conditional_function_supported_alternatives'], 0)
        self.assertTrue(all(a['rank'] is None and a['selected'] is None for a in result['alternatives']))
        self.assertEqual(result['fixed_premise_groups'][0]['alternative_indices'], [0, 1])

    def test_cross_completion_not_unioned(self):
        scope, lattice, entries, bundles = self.fixture.inputs('ordinary', 'single')
        _, _, controls, other = self.fixture.inputs('ordinary', 'single', True)
        record = parent.compare(scope, lattice, entries + controls, bundles={**bundles, **other})
        result = policy.evaluate(scope, lattice, record, bundles={**bundles, **other})
        self.assertEqual(result['summary']['fixed_premise_groups'], 2)
        self.assertEqual(result['summary']['conditional_function_supported_alternatives'], 1)
        self.assertEqual(result['summary']['held_alternatives'], 1)

    def test_fractional_source_ranges_preserved(self):
        scope, lattice, record, bundles = self.inputs('rational', mode='single')
        policy.evaluate(scope, lattice, record, bundles=bundles)
        points = [f(r['span']['start']) for fa in record['facets'] for rows in fa['source_segments'].values() for r in rows]
        self.assertIn(Fraction(1, 3), points)

    def test_tie_and_reattack_source_closure_are_not_rewritten(self):
        for name in ('suspension_tie', 'suspension_reattack'):
            with self.subTest(name=name):
                scope, lattice, record, bundles = self.inputs(name)
                before = digest(record)
                policy.evaluate(scope, lattice, record, bundles=bundles)
                self.assertEqual(digest(record), before)

    def test_empty_is_known_zero_not_complete_analysis(self):
        scope, lattice, _, bundles = self.inputs()
        record = parent.compare(scope, lattice, [], bundles=bundles)
        result = policy.evaluate(scope, lattice, record, bundles=bundles)
        self.assertEqual(result['status'], 'empty_saved_policy_request')
        self.assertEqual(result['summary']['evaluated_entries'], 0)
        self.assertEqual(result['summary']['conditional_function_supported_alternatives'], 0)

    def test_parent_whole_hold_preserves_all_refs_and_unknown_counts(self):
        scope, lattice, record, bundles = self.inputs('passing', mode='candidate', max_pairs=0)
        result = policy.evaluate(scope, lattice, record, bundles=bundles)
        self.assertEqual(result['status'], 'whole_saved_policy_hold')
        self.assertEqual([a['entry_refs'] for a in result['alternatives']], record['submitted_entry_refs'])
        self.assertIsNone(result['summary']['conditional_function_supported_alternatives'])
        self.assertEqual(result['summary']['withheld_entries'], 2)

    def test_policy_whole_budget_hold_not_favorable_prefix(self):
        scope, lattice, record, bundles = self.inputs('passing', mode='candidate')
        result = policy.evaluate(scope, lattice, record, bundles=bundles, work_budget=0)
        self.assertEqual(result['summary']['evaluated_entries'], 0)
        self.assertEqual(len(result['alternatives']), 2)
        self.assertEqual(result['fixed_premise_groups'], [])
        self.assertIsNone(result['summary']['diagnostic_reason_counts'])

    def test_exact_planned_work_boundary(self):
        scope, lattice, record, bundles = self.inputs()
        work = policy.evaluate(scope, lattice, record, bundles=bundles)['query_plan']['planned_work']
        self.assertEqual(policy.evaluate(scope, lattice, record, bundles=bundles, work_budget=work)['summary']['evaluated_entries'], 1)
        self.assertEqual(policy.evaluate(scope, lattice, record, bundles=bundles, work_budget=work - 1)['summary']['evaluated_entries'], 0)

    def test_bool_negative_float_budgets_rejected(self):
        scope, lattice, record, bundles = self.inputs()
        for bad in (True, -1, 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                policy.evaluate(scope, lattice, record, bundles=bundles, work_budget=bad)

    def test_resealed_ordered_facet_entry_mismatch_rejected(self):
        scope, lattice, record, bundles = self.inputs('passing', mode='candidate')
        record['facets'].reverse()
        with self.assertRaisesRegex(ValueError, 'entry_reference_mismatch'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_resealed_foreign_source_binding_rejected(self):
        scope, lattice, record, bundles = self.inputs()
        record['binding']['source_file_id'] = 'foreign'
        with self.assertRaises(ValueError):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_resealed_foreign_source_sound_rejected(self):
        scope, lattice, record, bundles = self.inputs()
        rows = record['facets'][0]['source_segments']
        rows['foreign'] = rows.pop(next(iter(rows)))
        with self.assertRaisesRegex(ValueError, 'sound_coverage_mismatch'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_resealed_source_atom_gap_rejected(self):
        scope, lattice, record, bundles = self.inputs()
        next(iter(record['facets'][0]['source_segments'].values()))[0]['span']['start']['numerator'] += 1
        with self.assertRaises(ValueError):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_resealed_account_pointer_data_mismatch_rejected(self):
        scope, lattice, record, bundles = self.inputs()
        record['facets'][0]['account']['note_time_quarters']['source_guarded_member']['numerator'] += 1
        with self.assertRaisesRegex(ValueError, 'source_account_mismatch'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_resealed_attack_note_reference_mismatch_rejected(self):
        scope, lattice, record, bundles = self.inputs()
        record['facets'][0]['slot_presentations'][0]['member_presentations'][0]['observations'][0]['attack_note_ref'] = 'foreign'
        with self.assertRaisesRegex(ValueError, 'literal_member_projection_mismatch'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_resealed_bool_like_axis_rejected(self):
        scope, lattice, record, bundles = self.inputs()
        record['facets'][0]['actual_transition_evidence'][0]['prerequisite_axes']['known_explicit_key_coordinate'] = 1
        with self.assertRaisesRegex(ValueError, 'strict_tristate'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_order_reversal_does_not_change_path_statuses(self):
        scope, lattice, entries, bundles = self.fixture.inputs('passing', 'candidate')
        results = [policy.evaluate(scope, lattice, parent.compare(scope, lattice, order, bundles=bundles), bundles=bundles)
                   for order in (entries, list(reversed(entries)))]
        mapped = [{a['entry_refs']['native_path_ref']['record_id']: a['status'] for a in r['alternatives']} for r in results]
        self.assertEqual(*mapped)

    def test_member_presence_none_cannot_erase_a_literal_projection(self):
        scope, lattice, record, bundles = self.inputs()
        record['facets'][0]['slot_presentations'][0]['missing_guarded_spellings'] = None
        with self.assertRaisesRegex(ValueError, 'literal_member_projection'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_positive_support_cannot_borrow_another_slots_observed_time(self):
        scope, lattice, record, bundles = self.inputs()
        observed = record['facets'][0]['slot_presentations'][0]['member_presentations'][0]['observations'][0]
        observed['observed_span'] = deepcopy(record['facets'][0]['partition'][1])
        with self.assertRaisesRegex(ValueError, 'literal_member_projection'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_resealed_atom_and_account_collusion_cannot_hide_nonmember(self):
        scope, lattice, record, bundles = self.inputs(control=True)
        fa = record['facets'][0]
        for rows in fa['source_segments'].values():
            for row in rows:
                if row['category'] == 'unexplained_nonmember_under_this_completion':
                    duration = f(row['span']['end']) - f(row['span']['start'])
                    old = row['category']
                    row['category'], row['raw_state'] = 'source_guarded_member', 'member'
                    totals = fa['account']['note_time_quarters']
                    from musicanote_harness.musical_pattern_observation import q
                    totals[old] = q(f(totals[old]) - duration)
                    totals['source_guarded_member'] = q(f(totals['source_guarded_member']) + duration)
                    with self.assertRaisesRegex(ValueError, 'raw_membership_or_credit'):
                        policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)
                    return
        self.fail('genuine nonmember fixture required')

    def test_positive_template_cannot_override_false_role_truths(self):
        scope, lattice, record, bundles = self.inputs(control=True)
        record['facets'][0]['ordinary_templates'][0]['satisfied'] = True
        with self.assertRaisesRegex(ValueError, 'whole_template_join'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_joint_true_cannot_override_false_axis(self):
        scope, lattice, record, bundles = self.inputs(control=True)
        record['facets'][0]['actual_transition_evidence'][0]['joint_conditional_functional_evidence'] = True
        with self.assertRaisesRegex(ValueError, 'shape_axes_or_joint'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_matching_shape_labels_cannot_hide_foreign_origin(self):
        scope, lattice, record, bundles = self.inputs()
        record['facets'][0]['actual_transition_evidence'][0]['function_shape']['source_segment_ref'] = 'foreign'
        with self.assertRaisesRegex(ValueError, 'shape_axes_or_joint'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_literal_bass_guard_unknown_cannot_be_forged_as_support(self):
        scope, lattice, record, bundles = self.inputs()
        record['facets'][0]['bass_cells'][0]['strict_bass_source_guards_passed'] = None
        with self.assertRaisesRegex(ValueError, 'literal_bass_projection'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_empty_query_plan_group_count_known_zero(self):
        scope, lattice, _, bundles = self.inputs()
        record = parent.compare(scope, lattice, [], bundles=bundles)
        self.assertEqual(policy.evaluate(scope, lattice, record, bundles=bundles)['query_plan']['planned_groups'], 0)

    def test_member_time_cannot_be_claimed_as_nonmember_credit(self):
        scope, lattice, record, bundles = self.inputs()
        fa = record['facets'][0]
        sid, rows = next(iter(fa['source_segments'].items()))
        fa['account']['explained_intervals_by_sound'].append({'sound_ref': sid, 'spans': [rows[0]['span']]})
        with self.assertRaisesRegex(ValueError, 'credit_union_atom_closure'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_unknown_credit_account_cannot_claim_assessed_support(self):
        scope, lattice, record, bundles = self.inputs()
        record['facets'][0]['account']['conditional_explanation_note_time_quarters'] = None
        with self.assertRaisesRegex(ValueError, 'credit_account_mismatch'):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_zero_flags_are_not_boolean_false(self):
        scope, lattice, record, bundles = self.inputs()
        record['flags']['ranking_computed'] = 0
        with self.assertRaises(ValueError):
            policy.evaluate(scope, lattice, reseal(record, parent.PREFIX), bundles=bundles)

    def test_authentic_incomplete_bundle_holds_instead_of_failing_template_coverage(self):
        fx = self.fixture.fixture
        scope, lattice = fx.case('ordinary')[0][1], fx.record('ordinary')
        session = fx.session('ordinary')
        links = fx.links('ordinary')
        # An impossible self-link is admitted as an authentic withheld witness;
        # budget=0 alone need not withhold a fully forced zero-search query.
        bundle = native.compile_bundle_prepared(session, [*links, [links[0][0], links[0][0]]])
        comparison = native.compare_prepared(session, [fx.selector('ordinary')], bundle['record_id'])
        explanation = roles.explain_prepared(roles.prepare_explanations(session, comparison))
        entries = [{'native_path': p, 'role_path': r, 'comparison_ref': sealed._ref(comparison),
                    'explanation_ref': sealed._ref(explanation)} for p, r in zip(comparison['paths'], explanation['paths'])]
        record = parent.compare(scope, lattice, entries, bundles={bundle['record_id']: bundle})
        result = policy.evaluate(scope, lattice, record, bundles={bundle['record_id']: bundle})
        self.assertEqual(result['status'], 'whole_saved_policy_hold')
        self.assertIn('saved_completion_witness_withheld_whole_policy_hold', result['reasons'])
        self.assertEqual(result['summary']['withheld_entries'], 1)
        self.assertIsNone(result['summary']['conditional_function_supported_alternatives'])

    def test_source_guard_diagnostics_not_rescanned_for_every_active_cell(self):
        scope, lattice, record, bundles = self.inputs('passing', mode='partition')
        original = parent.temporal._guard_codes
        visits = []
        def measured(sound):
            visits.append(sound['sound_ref'])
            return original(sound)
        with patch.object(parent.temporal, '_guard_codes', side_effect=measured):
            policy.evaluate(scope, lattice, record, bundles=bundles)
        self.assertEqual(len(visits), len(scope['sound_facts']))
        self.assertEqual(len(set(visits)), len(visits))


if __name__ == '__main__':
    unittest.main()
