"""Synthetic XML-to-IR replay contracts, not corpus or harmonic accuracy tests.

The non-TestCase XML factory is composed, never inherited. Public fixtures
retain complete genuine saved panels. Explicit mocks below are storage,
budget, or adversarial fault injection; they are not musical witnesses.
"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_source_evidence_panel as prior
from musicanote_harness import source_progression_proposals as proposals
from musicanote_harness import source_progression_replay as replay
from musicanote_harness.musical_pattern_observation import digest, f, q
from test_factor_expanded_hypotheses import ExpandedHypothesisFixture, event, span
from test_factor_musical_view import reseal


class SourceProgressionReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = ExpandedHypothesisFixture()
        cls.factory.addCleanup = cls.addClassCleanup
        cls.factory.setUp()
        cls.inputs_cache, cls.handles, cls.packets_cache = {}, {}, {}

    def inputs(self, name='single'):
        if name not in self.inputs_cache:
            signatures = [{'fifths': 0, 'mode_hint': None}]
            lanes = [[event(['C3', 'E4', 'G4'], 0, 4)]]
            if name == 'ordinary':
                # Absent signature deliberately preserves the genuine unknown
                # key; ordinary motion remains observable, key proof does not.
                signatures = None
                lanes = [[event('B4', 0, 2), event('C5', 2, 2)],
                         [event('F4', 0, 2), event('E4', 2, 2)],
                         [event(['G3', 'D4'], 0, 2), event(['C3', 'G4'], 2, 2)]]
            elif name == 'tied':
                lanes = [[event('C4', 0, 2, tie_role='start'),
                          event('C4', 2, 2, tie_role='stop')],
                         [event(['C3', 'E3', 'G3'], 0, 4)]]
            elif name == 'empty':
                # A real single pitch, NOT silence or a fabricated score clock.
                lanes = [[event('C3', 0, 4)]]
            elif name == 'rational':
                lanes = [[event(['C3', 'E4', 'G4'], 0, Fraction(4, 3))]]
            elif name != 'single':
                raise AssertionError('unknown synthetic fixture: ' + name)
            extent = span(Fraction(1, 3), Fraction(2, 3)) if name == 'rational' else span(1, 2)
            ir, scope = self.factory.fixture(lanes, extent=extent, signatures=signatures)
            lattice = native.build_lattice(ir, scope)
            session = native.prepare_lattice(ir, scope, lattice)
            panel = prior.panel_prepared(prior.prepare_panel(session))
            proposal = proposals.propose(scope, lattice, panel, work_budget=100000000)
            self.inputs_cache[name] = ir, scope, lattice, panel, proposal
        return deepcopy(self.inputs_cache[name])

    def handle(self, name='single'):
        if name not in self.handles:
            ir, scope, lattice, panel, proposal = self.inputs(name)
            self.handles[name] = replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
        return self.handles[name]

    def plan(self, name='single', **limits):
        _, scope, lattice, panel, proposal = self.inputs(name)
        return replay.plan_saved(scope, lattice, proposal, prior_panel=panel, **limits)

    def links(self):
        _, scope, _, _, _ = self.inputs('ordinary')
        def sound(spelling, onset):
            return next(s['sound_ref'] for s in scope['sound_facts']
                        if s['pitch']['spelling'] == spelling and f(s['span']['start']) == onset)
        return [[sound('B4', 0), sound('C5', 2)], [sound('F4', 0), sound('E4', 2)]]

    @staticmethod
    def generous():
        return dict(batch_size=64, max_selectors=4096, native_query_work_budget=1000000000,
                    role_query_work_budget=1000000000, replay_work_budget=1000000000000)

    def packets(self, name='single', linked=False):
        key = name, linked
        if key not in self.packets_cache:
            self.packets_cache[key] = list(replay.stream_prepared(
                self.handle(name), self.links() if linked else [], **self.generous()))
        return deepcopy(self.packets_cache[key])

    def terminal(self, name='single', linked=False):
        return self.packets(name, linked)[-1]['record']

    def small_batches(self):
        key = 'single', False, 3
        if key not in self.packets_cache:
            limits = {**self.generous(), 'batch_size': 3}
            self.packets_cache[key] = list(replay.stream_prepared(self.handle(), [], **limits))
        return deepcopy(self.packets_cache[key])

    def assert_whole_hold(self, **limits):
        with patch.object(native, 'compile_bundle_prepared', side_effect=AssertionError('no bundle on preflight hold')), \
             patch.object(native, 'compare_prepared', side_effect=AssertionError('no query on preflight hold')), \
             patch.object(roles, 'prepare_explanations', side_effect=AssertionError('no role preparation on hold')):
            packets = list(replay.stream_prepared(self.handle(), [], **limits))
        self.assertEqual([p['packet_type'] for p in packets], ['header', 'summary'])
        self.assertIsNone(packets[0]['bundle'])
        result = packets[-1]['record']
        self.assertEqual(result['status'], 'whole_source_replay_request_hold')
        self.assertEqual(result['summary']['native_comparison_calls'], 0)
        self.assertEqual(result['summary']['fresh_bundle_registrations'], 0)
        self.assertIsNone(result['summary']['conditional_explained_note_time_selector_occurrence_sum'])
        self.assertFalse(result['fresh_native_evaluation_performed'])
        self.assertFalse(result['same_completion_resolution_evaluated'])
        return result

    def test_genuine_fresh_rebind_exact_complete_bodies_and_used_origins(self):
        _, _, lattice, _, proposal = self.inputs()
        receipt = replay.binding_prepared(self.handle())
        self.assertEqual(receipt['status'], 'ready_fresh_source_proposal_replay')
        self.assertEqual(replay.lattice_prepared(self.handle()), lattice)
        used = {oid for s in proposal['selectors'] for oid in s['origin_ids']}
        self.assertEqual({m['archived_ref']['record_id'] for m in receipt['origin_mappings']}, used)
        for row in receipt['origin_mappings'] + receipt['key_mappings']:
            self.assertEqual(row['archived_ref'], row['fresh_ref'])
        self.assertTrue(all(m['exact_complete_origin_body_match'] for m in receipt['origin_mappings']))
        self.assertTrue(all(m['exact_complete_key_body_match'] for m in receipt['key_mappings']))

    def test_one_fresh_prepare_never_passes_archive_as_record_or_reprepares_stream(self):
        ir, scope, lattice, panel, proposal = self.inputs()
        with patch.object(native, 'prepare_lattice', wraps=native.prepare_lattice) as spy:
            handle = replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
            self.assertEqual(spy.call_count, 1)
            args, kwargs = spy.call_args
            self.assertEqual(len(args), 2)
            self.assertEqual(kwargs, lattice['resource_limits'])
            list(replay.stream_prepared(handle, [], **self.generous()))
            self.assertEqual(spy.call_count, 1)
        self.assertEqual(replay.binding_prepared(handle)['fresh_native_preparations'], 1)

    def test_planning_is_pure_no_native_authority_or_queries(self):
        with patch.object(native, 'prepare_lattice', side_effect=AssertionError('no prepare')), \
             patch.object(native, 'compile_bundle_prepared', side_effect=AssertionError('no bundle')), \
             patch.object(native, 'compare_prepared', side_effect=AssertionError('no query')):
            plan = self.plan()
        self.assertEqual(plan['status'], 'ready_native_role_batches')
        self.assertTrue(all(v is False for v in plan['flags'].values()))

    def test_ordered_control_additional_unknown_and_none_requests_all_retained(self):
        _, _, lattice, panel, proposal = self.inputs()
        packets = self.packets()
        selectors = [s for b in packets if b['packet_type'] == 'batch' for s in b['comparison']['selectors']]
        self.assertEqual(selectors, proposal['selectors'])
        self.assertEqual(selectors[:len(panel['selectors'])], panel['selectors'])
        self.assertEqual(selectors[len(panel['selectors']):], proposal['additional_selectors'])
        unknown = {k['record_id'] for k in lattice['keys'] if k['segments'][0]['mode'] == 'unknown'}
        self.assertTrue(unknown & {s['key_id'] for s in selectors})
        self.assertTrue(any(s['transition_assumptions'] == [] for s in selectors))

    def test_internal_none_and_declared_vectors_are_not_filtered_after_adverse_results(self):
        _, _, _, panel, proposal = self.inputs('ordinary')
        selectors = [s for b in self.packets('ordinary') if b['packet_type'] == 'batch'
                     for s in b['comparison']['selectors']]
        self.assertEqual(selectors, proposal['selectors'])
        self.assertEqual(selectors[:len(panel['selectors'])], panel['selectors'])
        self.assertTrue(any(None in s['transition_assumptions'] for s in selectors))
        self.assertTrue(any({'family': 'V7', 'quality': 'M'} in s['transition_assumptions'] for s in selectors))

    def test_complete_packet_denominators_and_exact_parent_joins(self):
        ir, scope, lattice, _, proposal = self.inputs()
        packets = self.packets()
        result = packets[-1]['record']
        self.assertEqual(result['status'], 'computed_native_role_source_requests_not_selected')
        self.assertEqual(result['summary']['native_computed_paths'], len(proposal['selectors']))
        self.assertEqual(result['summary']['role_computed_paths'], len(proposal['selectors']))
        self.assertEqual(result['summary']['withheld_native_paths'], 0)
        self.assertEqual(result['summary']['withheld_role_paths'], 0)
        for packet, refs in zip([p for p in packets if p['packet_type'] == 'batch'], result['batch_refs']):
            kernels._check(packet['comparison'], native.COMPARISON_PREFIX)
            kernels._check(packet['explanation'], roles.PREFIX)
            self.assertEqual(refs['comparison_ref'], kernels._ref(packet['comparison']))
            self.assertEqual(refs['explanation_ref'], kernels._ref(packet['explanation']))
            self.assertEqual(packet['explanation']['native_comparison_ref'], refs['comparison_ref'])
            self.assertEqual(packet['comparison']['scope_ref'], kernels._ref(scope))
            self.assertEqual(packet['comparison']['lattice_ref'], kernels._ref(lattice))

    def test_two_native_calls_plus_one_role_charge_and_observed_call_counts(self):
        plan = self.plan(batch_size=3)
        for batch in plan['batches']:
            self.assertEqual(batch['charged_native_comparisons'], 2)
            self.assertEqual(batch['charged_work'], 2 * batch['native_query_work'] + batch['role_query_work'])
        self.assertEqual(plan['planned_replay_work'], plan['native_comparison_work'] + plan['role_explanation_work'])
        with patch.object(native, 'compare_prepared', wraps=native.compare_prepared) as native_spy, \
             patch.object(roles, 'prepare_explanations', wraps=roles.prepare_explanations) as prep_spy, \
             patch.object(roles, 'explain_prepared', wraps=roles.explain_prepared) as role_spy:
            packets = list(replay.stream_prepared(self.handle(), [], **self.generous()))
        result = packets[-1]['record']['summary']
        self.assertEqual(native_spy.call_count, 2 * result['planned_batches'])
        self.assertEqual(prep_spy.call_count, result['planned_batches'])
        self.assertEqual(role_spy.call_count, result['planned_batches'])
        self.assertEqual(result['native_comparison_calls'], native_spy.call_count)

    def test_exact_full_budget_ready_one_below_whole_hold(self):
        plan = self.plan()
        budget = plan['planned_replay_work']
        self.assertGreater(budget, 0)
        self.assertEqual(self.plan(replay_work_budget=budget)['status'], 'ready_native_role_batches')
        self.assertEqual(self.plan(replay_work_budget=budget - 1)['status'], 'whole_source_replay_request_hold')
        self.assert_whole_hold(replay_work_budget=budget - 1)

    def test_exact_native_batch_bound_ready_one_below_whole_hold(self):
        bound = max(b['native_query_work'] for b in self.plan()['batches'])
        self.assertEqual(self.plan(native_query_work_budget=bound)['status'], 'ready_native_role_batches')
        self.assert_whole_hold(native_query_work_budget=bound - 1)

    def test_exact_role_batch_bound_ready_one_below_whole_hold(self):
        bound = max(b['role_query_work'] for b in self.plan()['batches'])
        self.assertEqual(self.plan(role_query_work_budget=bound)['status'], 'ready_native_role_batches')
        self.assert_whole_hold(role_query_work_budget=bound - 1)

    def test_max_selector_hold_has_no_favorable_prefix(self):
        self.assert_whole_hold(max_selectors=len(self.inputs()[-1]['selectors']) - 1)

    def test_max_slots_hold_includes_full_hold_without_vacuous_support(self):
        self.assert_whole_hold(max_slots=0)

    def test_all_limit_types_are_strict_integer_nonnegative(self):
        for key in replay.DEFAULTS:
            for value in (True, False, 1.0, -1, None, '3'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.plan(**{key: value})

    def test_batch_size_bounds_and_closed_limit_names(self):
        for value in (0, 65):
            with self.assertRaises(ValueError):
                self.plan(batch_size=value)
        with self.assertRaises(ValueError):
            self.plan(unregistered_limit=1)
        self.assertEqual(self.plan(batch_size=64)['resource_limits']['batch_size'], 64)

    def test_zero_work_hold_is_unknown_credit_not_zero(self):
        result = self.assert_whole_hold(replay_work_budget=0)
        self.assertEqual(result['summary']['known_conditional_explained_note_time_selector_occurrence_subtotal'], q(0))
        self.assertIsNone(result['summary']['conditional_explained_note_time_selector_occurrence_sum'])

    def test_genuine_known_empty_has_zero_work_zero_credit_and_no_activity(self):
        self.assertEqual(self.inputs('empty')[-1]['selectors'], [])
        plan = self.plan('empty', replay_work_budget=0, native_query_work_budget=0, role_query_work_budget=0)
        self.assertEqual(plan['planned_replay_work'], 0)
        self.assertEqual(plan['planned_batches'], 0)
        result = list(replay.stream_prepared(self.handle('empty'), [], replay_work_budget=0,
                       native_query_work_budget=0, role_query_work_budget=0))[-1]['record']
        self.assertEqual(result['status'], 'computed_native_role_source_requests_not_selected')
        self.assertEqual(result['summary']['conditional_explained_note_time_selector_occurrence_sum'], q(0))
        self.assertEqual(result['summary']['native_comparison_calls'], 0)
        self.assertFalse(result['fresh_native_evaluation_performed'])
        self.assertFalse(result['same_completion_resolution_evaluated'])

    def test_genuine_held_empty_does_not_promote_no_accounts_to_zero_credit(self):
        ir, scope, lattice, panel, _ = self.inputs('empty')
        proposal = proposals.propose(scope, lattice, panel, work_budget=0)
        self.assertEqual(proposal['status'], 'whole_source_proposal_hold')
        self.assertEqual(proposal['selectors'], [])
        with patch.object(native, 'prepare_lattice', side_effect=AssertionError('held parent must not prepare')):
            handle = replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
        receipt = replay.binding_prepared(handle)
        self.assertEqual(receipt['fresh_native_preparations'], 0)
        self.assertFalse(receipt['native_authority_issued'])
        self.assertIsNone(replay.lattice_prepared(handle))
        result = list(replay.stream_prepared(handle, []))[-1]['record']
        self.assertEqual(result['summary']['planned_selectors'], 0)
        self.assertIsNone(result['summary']['conditional_explained_note_time_selector_occurrence_sum'])
        self.assertEqual(result['status'], 'whole_source_replay_request_hold')

    def test_genuine_held_proposal_retains_control_denominator_no_native_prepare(self):
        ir, scope, lattice, panel, _ = self.inputs()
        proposal = proposals.propose(scope, lattice, panel, work_budget=0)
        with patch.object(native, 'prepare_lattice', side_effect=AssertionError('no held rebind')):
            handle = replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
        result = list(replay.stream_prepared(handle, []))[-1]['record']
        self.assertEqual(result['summary']['planned_selectors'], len(panel['selectors']))
        self.assertEqual(result['summary']['withheld_role_paths'], len(panel['selectors']))

    def test_saved_bundle_body_is_not_completion_authority(self):
        bundle = self.packets()[0]['bundle']
        with self.assertRaises(ValueError):
            list(replay.stream_prepared(self.handle(), bundle))
        with self.assertRaises(ValueError):
            list(replay.stream_prepared(self.handle(), bundle['record_id']))

    def test_completion_requires_exact_ordered_registered_same_raw_lane_pairs(self):
        links = self.links()
        invalid = [tuple(links), [tuple(links[0])], [[links[0][0]]],
                   [[links[0][0], links[1][1]]], [['foreign-sound', links[0][1]]], [[True, links[0][1]]]]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                list(replay.stream_prepared(self.handle('ordinary'), value))

    def test_same_physical_source_completions_do_not_borrow_required_links(self):
        linked, control = self.terminal('ordinary', True), self.terminal('ordinary', False)
        self.assertEqual(linked['proposal_ref'], control['proposal_ref'])
        self.assertEqual(linked['scope_ref'], control['scope_ref'])
        self.assertNotEqual(linked['bundle_ref'], control['bundle_ref'])
        self.assertEqual(linked['required_links'], self.links())
        self.assertEqual(control['required_links'], [])
        self.assertGreater(linked['summary']['ordinary_individual_supported_occurrences'], 0)
        self.assertEqual(control['summary']['ordinary_individual_supported_occurrences'], 0)
        self.assertGreater(linked['summary']['whole_ordinary_template_truths']['true'], 0)
        self.assertEqual(control['summary']['whole_ordinary_template_truths']['true'], 0)
        self.assertFalse(linked['flags']['independent_completions_unioned'])

    def test_unknown_key_does_not_suppress_ordinary_motion_or_confirm_function(self):
        paths = [p for b in self.packets('ordinary', True) if b['packet_type'] == 'batch'
                 for p in b['comparison']['paths']]
        supported = [c for p in paths for c in p['transition_contexts']
                     if c['ordinary_strategy'] and c['ordinary_strategy']['whole_ordinary_template_satisfied'] is True]
        self.assertTrue(supported)
        # Unknown is not affirmative key proof. Independent false premises
        # remain false rather than being overwritten by the unknown premise.
        self.assertTrue(all(c['joint_conditional_functional_evidence'] is not True for c in supported))
        self.assertTrue(all(c['prerequisite_axes']['known_explicit_key_coordinate'] is None for c in supported))

    def test_literal_raw_time_and_role_unions_are_conserved_every_submitted_path(self):
        _, scope, _, _, _ = self.inputs('ordinary')
        raw = sum((f(s['observed_span']['end']) - f(s['observed_span']['start'])
                   for s in scope['sound_facts'] if not s['point']), Fraction())
        for b in self.packets('ordinary', True):
            if b['packet_type'] != 'batch':
                continue
            for path in b['comparison']['paths']:
                self.assertEqual(f(path['whole_path_account']['raw_total_note_time_quarters']), raw)
                self.assertTrue(path['whole_path_account']['raw_time_conserved'])
            for path in b['explanation']['paths']:
                account = path['account']
                self.assertEqual(sum((f(v) for v in account['note_time_quarters'].values()), Fraction()), raw)
                self.assertTrue(account['union_counted_once'])

    def test_tied_sound_retains_one_attack_full_span_and_source_note_closure(self):
        _, scope, _, _, _ = self.inputs('tied')
        tied = next(s for s in scope['sound_facts'] if s['tie_chain_ref'] is not None)
        self.assertEqual(tied['span'], span(0, 4))
        self.assertEqual(len(tied['source_note_refs']), 2)
        self.assertIn(tied['attack_note_ref'], tied['source_note_refs'])
        for b in self.packets('tied'):
            if b['packet_type'] != 'batch':
                continue
            for path in b['comparison']['paths']:
                self.assertTrue(path['whole_path_account']['raw_time_conserved'])
                self.assertEqual(f(path['whole_path_account']['raw_total_note_time_quarters']), 16)
                rows = [row for profile in path['profiles'] for row in profile['rows']
                        if row['sound_ref'] == tied['sound_ref']]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['full_span'], tied['span'])
                self.assertEqual(rows[0]['observed_span'], tied['observed_span'])
        self.assertFalse(self.terminal('tied')['same_completion_resolution_evaluated'])

    def test_fractional_source_time_survives_without_float_rounding(self):
        _, scope, _, _, _ = self.inputs('rational')
        raw = sum((f(s['observed_span']['end']) - f(s['observed_span']['start']) for s in scope['sound_facts']), Fraction())
        self.assertEqual(raw, 4)
        for b in self.packets('rational'):
            if b['packet_type'] == 'batch':
                self.assertTrue(all(f(p['whole_path_account']['raw_total_note_time_quarters']) == raw
                                    for p in b['comparison']['paths']))

    def test_activity_counts_equal_actual_contexts_not_refs_or_request_flags(self):
        packets = self.packets('ordinary', True)
        result = packets[-1]['record']
        contexts = [c for b in packets if b['packet_type'] == 'batch'
                    for p in b['comparison']['paths'] for c in p['transition_contexts']]
        declared = sum(c['function_shape'] is not None for c in contexts)
        self.assertEqual(result['summary']['computed_internal_transition_contexts'], len(contexts))
        self.assertEqual(result['summary']['declared_internal_function_contexts'], declared)
        self.assertEqual(result['summary']['resolution_contexts_under_complete_bundle'], declared)
        self.assertEqual(result['same_completion_resolution_evaluated'], declared > 0)
        self.assertFalse(self.terminal()['same_completion_resolution_evaluated'])

    def test_no_winner_accuracy_training_or_full_contrast_promotion(self):
        for result in (self.terminal(), self.terminal('ordinary', True)):
            self.assertTrue(all(v is False for v in result['flags'].values()))
            self.assertTrue(all(result[k] is None for k in ('selected', 'rank', 'confidence')))
            self.assertIn('deferred_whole_competitor', result['full_contrast_status'])
            kernels._check(result, replay.PREFIX)

    def test_original_inputs_remain_unchanged_and_post_prepare_mutation_is_isolated(self):
        values = self.inputs()
        ir, scope, lattice, panel, proposal = values
        before = deepcopy(values)
        handle = replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
        self.assertEqual(values, before)
        receipt = replay.binding_prepared(handle)
        proposal['selectors'].clear(); lattice['keys'].clear(); scope['sound_facts'].clear(); ir['note_events'].clear()
        self.assertEqual(replay.binding_prepared(handle), receipt)
        self.assert_whole_hold(max_selectors=0)
        result = list(replay.stream_prepared(handle, [], **self.generous()))[-1]['record']
        self.assertEqual(result['summary']['planned_selectors'], len(before[-1]['selectors']))

    def test_detached_binding_and_lattice_mutation_cannot_change_owned_state(self):
        receipt, lattice = replay.binding_prepared(self.handle()), replay.lattice_prepared(self.handle())
        baseline = deepcopy(receipt)
        receipt['origin_mappings'].clear(); receipt['flags']['function_confirmed'] = True
        lattice['keys'].clear()
        self.assertEqual(replay.binding_prepared(self.handle()), baseline)
        self.assertTrue(replay.lattice_prepared(self.handle())['keys'])

    def test_detached_header_and_batch_mutation_cannot_change_terminal_snapshots(self):
        stream = replay.stream_prepared(self.handle(), [], **self.generous())
        header = next(stream)
        header['plan']['planned_selectors'] = -1
        header['bundle']['status'] = 'forged'
        batch = next(stream)
        original_comparison_ref = kernels._ref(batch['comparison'])
        batch['comparison']['paths'].clear()
        batch['comparison']['record_id'] = 'forged'
        batch['explanation']['paths'].clear()
        tail = list(stream)
        result = tail[-1]['record']
        self.assertEqual(result['batch_refs'][0]['comparison_ref'], original_comparison_ref)
        self.assertEqual(result['summary']['native_computed_paths'], len(self.inputs()[-1]['selectors']))
        self.assertEqual(result['bundle_status'], 'complete_all_lane_witness')

    def test_original_link_mutation_after_header_is_detected(self):
        links = self.links()
        stream = replay.stream_prepared(self.handle('ordinary'), links, **self.generous())
        next(stream)
        links.clear()
        with self.assertRaises(ValueError):
            next(stream)

    def test_foreign_and_fabricated_handles_are_rejected(self):
        for handle in (object(), {}, self.handle().__class__()):
            with self.assertRaises(ValueError):
                replay.binding_prepared(handle)

    def test_adversarial_replaced_state_identity_rejected_even_equal_data(self):
        handle = self.handle(); state = replay._SESSIONS[handle]
        try:
            replay._SESSIONS[handle] = replace(state)
            with self.assertRaises(ValueError):
                replay.binding_prepared(handle)
        finally:
            replay._SESSIONS[handle] = state

    def test_adversarial_plain_mutable_state_data_is_rejected(self):
        handle = self.handle(); state = replay._SESSIONS[handle]
        try:
            replay._SESSIONS[handle] = replace(state, data=dict(state.data))
            with self.assertRaises(ValueError):
                replay.binding_prepared(handle)
        finally:
            replay._SESSIONS[handle] = state

    def test_adversarial_hmac_tamper_rejected(self):
        handle = self.handle(); state = replay._SESSIONS[handle]
        try:
            replay._SESSIONS[handle] = replace(state, authentication=b'bad')
            with self.assertRaises(ValueError):
                replay.binding_prepared(handle)
        finally:
            replay._SESSIONS[handle] = state

    def test_adversarial_native_parent_state_identity_swap_rejected(self):
        handle = self.handle(); state = replay._SESSIONS[handle]
        old = native._SESSIONS[state.native_session]
        try:
            native._SESSIONS[state.native_session] = replace(old)
            with self.assertRaises(ValueError):
                replay.binding_prepared(handle)
        finally:
            native._SESSIONS[state.native_session] = old

    def test_current_contract_drift_invalidates_owned_handle(self):
        handle = self.handle(); old = replay._contract()
        with patch.object(replay, '_contract', return_value={**old, 'source_sha256': 'changed'}):
            with self.assertRaises(ValueError):
                replay.binding_prepared(handle)

    def test_mutation_during_fresh_preparation_is_rejected(self):
        ir, scope, lattice, panel, proposal = self.inputs()
        original = native.prepare_lattice
        def mutate(*args, **kwargs):
            handle = original(*args, **kwargs)
            proposal['selected'] = 'adversarial mutation'
            return handle
        with patch.object(native, 'prepare_lattice', side_effect=mutate), self.assertRaises(ValueError):
            replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)

    def test_plan_caller_mutation_guard_after_saved_validation(self):
        _, scope, lattice, panel, proposal = self.inputs()
        original = replay._plan
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            proposal['selected'] = 'adversarial mutation'
            return result
        with patch.object(replay, '_plan', side_effect=mutate), self.assertRaises(ValueError):
            replay.plan_saved(scope, lattice, proposal, prior_panel=panel)

    def test_foreign_source_scope_or_tampered_saved_proposal_rejected(self):
        ir, scope, lattice, panel, proposal = self.inputs()
        foreign = self.inputs('tied')[1]
        with self.assertRaises(ValueError):
            replay.prepare_replay(ir, foreign, lattice, proposal, prior_panel=panel)
        proposal['selectors'].reverse()
        with self.assertRaises(ValueError):
            replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)

    def test_resealed_saved_selector_order_tampering_is_not_authority(self):
        ir, scope, lattice, panel, proposal = self.inputs()
        proposal['selectors'].reverse()
        reseal(proposal, proposals.PREFIX)
        with self.assertRaises(ValueError):
            replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)

    def test_fault_injected_fresh_inventory_drift_holds_whole_rebind(self):
        ir, scope, lattice, panel, proposal = self.inputs()
        original = native.lattice_prepared
        def drift(handle):
            result = original(handle)
            result['flags']['production_modified'] = True
            return result
        with patch.object(native, 'lattice_prepared', side_effect=drift):
            handle = replay.prepare_replay(ir, scope, lattice, proposal, prior_panel=panel)
        receipt = replay.binding_prepared(handle)
        self.assertEqual(receipt['status'], 'whole_source_rebind_hold')
        self.assertFalse(receipt['native_authority_issued'])
        self.assertEqual(receipt['origin_mappings'], [])
        self.assertEqual(receipt['key_mappings'], [])

    def test_fault_injected_runtime_native_hold_refs_do_not_claim_actual_activity(self):
        original = native.compare_prepared
        def held(*args, **kwargs):
            return original(*args, **{**kwargs, 'query_work_budget': 0})
        with patch.object(native, 'compare_prepared', side_effect=held):
            packets = list(replay.stream_prepared(self.handle(), [], **self.generous()))
        result = packets[-1]['record']
        self.assertTrue(result['batch_refs'])
        self.assertEqual(result['status'], 'incomplete_native_role_source_replay')
        self.assertEqual(result['summary']['native_computed_paths'], 0)
        self.assertEqual(result['summary']['computed_internal_transition_contexts'], 0)
        self.assertEqual(result['summary']['resolution_contexts_under_complete_bundle'], 0)
        self.assertFalse(result['fresh_native_evaluation_performed'])
        self.assertFalse(result['same_completion_resolution_evaluated'])
        self.assertIsNone(result['summary']['conditional_explained_note_time_selector_occurrence_sum'])

    def test_fault_injected_runtime_role_hold_retains_native_denominator(self):
        original = roles.explain_prepared
        def held(*args, **kwargs):
            return original(*args, **{**kwargs, 'query_work_budget': 0})
        with patch.object(roles, 'explain_prepared', side_effect=held):
            packets = list(replay.stream_prepared(self.handle(), [], **self.generous()))
        result = packets[-1]['record']
        self.assertEqual(result['summary']['native_computed_paths'], len(self.inputs()[-1]['selectors']))
        self.assertEqual(result['summary']['role_computed_paths'], 0)
        self.assertEqual(result['summary']['withheld_role_paths'], len(self.inputs()[-1]['selectors']))
        self.assertTrue(result['fresh_native_evaluation_performed'])
        self.assertIsNone(result['summary']['conditional_explained_note_time_selector_occurrence_sum'])

    def test_batch_size_is_storage_only_native_path_order_and_bodies_match(self):
        def paths(packets):
            return [p for b in packets if b['packet_type'] == 'batch' for p in b['comparison']['paths']]
        small, large = self.small_batches(), self.packets()
        self.assertGreater(len(small[-1]['record']['batch_refs']), len(large[-1]['record']['batch_refs']))
        self.assertEqual(paths(small), paths(large))
        self.assertEqual(small[-1]['record']['summary']['planned_selectors'],
                         large[-1]['record']['summary']['planned_selectors'])

    def test_batch_size_is_storage_only_role_path_order_accounts_and_bodies_match(self):
        def paths(packets):
            return [p for b in packets if b['packet_type'] == 'batch' for p in b['explanation']['paths']]
        small, large = self.small_batches(), self.packets()
        self.assertEqual(paths(small), paths(large))
        self.assertEqual(small[-1]['record']['summary']['conditional_explained_note_time_selector_occurrence_sum'],
                         large[-1]['record']['summary']['conditional_explained_note_time_selector_occurrence_sum'])

    def test_pure_tristate_helper_does_not_coerce_zero_or_unknown_to_false(self):
        self.assertEqual([replay._truth(v) for v in (True, False, None)], ['true', 'false', 'unknown'])
        for value in (0, 1, '', 'unknown', [], {}):
            with self.assertRaises(ValueError):
                replay._truth(value)


if __name__ == '__main__':
    unittest.main()
