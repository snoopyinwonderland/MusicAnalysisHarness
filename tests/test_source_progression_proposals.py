"""Genuine XML-derived saved proposal tests; no musical accuracy claim."""
from copy import deepcopy
from fractions import Fraction
from itertools import product
from math import prod
import unittest
from unittest.mock import patch

from musicanote_harness import source_progression_proposals as engine
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_source_evidence_panel as prior
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness.musical_pattern_observation import digest, f
import test_factor_source_evidence_panel as fixtures
from test_factor_expanded_hypotheses import ExpandedHypothesisFixture, event, span
from test_factor_musical_view import reseal


class SourceProgressionProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SourceEvidencePanelTests.setUpClass()
        cls.addClassCleanup(fixtures.SourceEvidencePanelTests.doClassCleanups)
        cls.fx = fixtures.SourceEvidencePanelTests()
        cls.factory = ExpandedHypothesisFixture()
        cls.factory.addCleanup = cls.addClassCleanup
        cls.factory.setUp()
        cls.saved, cls.results = {}, {}

    def inputs(self, name='three_chords'):
        if name not in self.saved:
            if name == 'home_to_IV':
                lanes = [[event(['C3', 'E4', 'G4'], 0, 2), event(['F3', 'A4', 'C5'], 2, 2)]]
                ir, scope = self.factory.fixture(lanes, signatures=[{'fifths': 0, 'mode_hint': None}], extent=span(1, 2))
                lattice = native.build_lattice(ir, scope)
                session = native.prepare_lattice(ir, scope, lattice)
                panel = prior.panel_prepared(prior.prepare_panel(session))
            else:
                scope = self.fx.case(name)[1]
                lattice, panel = self.fx.lattice(name), self.fx.result(name)
            self.saved[name] = scope, lattice, panel
        return deepcopy(self.saved[name])

    def result(self, name='three_chords'):
        if name not in self.results:
            self.results[name] = engine.propose(*self.inputs(name), work_budget=100000000)
        return deepcopy(self.results[name])

    def test_genuine_proposals_are_not_native_or_musical_support(self):
        result = self.result()
        self.assertEqual(result['status'], 'computed_source_progression_proposals_not_evaluated')
        self.assertTrue(all(value is False for value in result['flags'].values()))
        self.assertTrue(all(result[key] is None for key in ('selected', 'rank', 'confidence')))
        self.assertEqual(result['native_replay_status'], 'not_executed_requires_fresh_native_session')
        for group in result['shape_request_groups']:
            for cut in group['cuts']:
                self.assertTrue(all(cut[key] is None for key in
                    ('resolution_support', 'secondary_support', 'boundary_support', 'same_completion_ref')))

    def test_original_controls_exact_order_and_additive_dedup(self):
        result, (_, _, panel) = self.result(), self.inputs()
        self.assertEqual(result['retained_control_selectors'], panel['selectors'])
        self.assertEqual(result['selectors'], panel['selectors'] + result['additional_selectors'])
        self.assertGreater(len(result['additional_selectors']), 0)
        fingerprints = [digest(selector) for selector in result['selectors']]
        self.assertEqual(len(set(fingerprints)), len(fingerprints))
        self.assertTrue(any(a['existing_selector']['kind'] == 'retained_control' for a in result['selector_aliases']))

    def test_all_requested_origins_assessed_and_denominators_conserved(self):
        result = self.result()
        scope, lattice, panel = self.inputs()
        catalogs = {e['catalog_id']: e for e in lattice['catalog_inventory']}
        expected = sum(len(catalogs[r['catalog_id']]['origins']) for r in panel['intervals'])
        self.assertEqual(result['summary']['assessed_origin_occurrences'], expected)
        for row in result['intervals']:
            self.assertEqual(row['native_origins'], row['eligible_origins'] + row['rejected_origins'])
            self.assertEqual(row['eligible_origins'], row['proposal_count'] + row['omitted_eligible_origins'])
            self.assertEqual(sum(b['eligible_origins'] for b in row['bucket_representatives']), row['eligible_origins'])
        self.assertEqual(result['logical_universe'], lattice['universe'])

    def test_ordinary_buckets_preserve_multiple_roots_per_quality(self):
        result = self.result()
        roots = {}
        for row in result['intervals']:
            for representative in row['bucket_representatives']:
                bucket = representative['bucket']
                if bucket['kind'] in ('triad', 'seventh'):
                    roots.setdefault((bucket['kind'], bucket['quality']), set()).add(digest(bucket['spelled_root']))
                    self.assertIn(representative['representative_ref'], [p['origin_ref'] for p in row['proposals']])
        self.assertTrue(any(len(values) > 1 for values in roots.values()))
        self.assertEqual({kind for kind, quality in roots}, {'triad', 'seventh'})

    def test_member_order_is_not_set_alias_for_ordinary_classification(self):
        _, lattice, _ = self.inputs()
        origin = next(o for e in lattice['catalog_inventory'] for o in e['origins'] if engine._bucket(o)[0] == 'triad')
        reordered = deepcopy(origin)
        reordered['members'] = list(reversed(reordered['members']))
        self.assertEqual(prior._signature(origin), prior._signature(reordered))
        self.assertEqual(engine._bucket(reordered)[0], 'nonordinary_or_unassessed')

    def test_every_mixed_path_changes_at_most_one_slot_of_a_retained_seed(self):
        result = self.result()
        seeds = self.inputs()[2]['complete_proposal_paths']
        for path in result['complete_proposal_paths']:
            distances = [sum(a != b for a, b in zip(path['origin_ids'], seed['origin_ids']))
                for seed in seeds if path['partition_kind'] == seed['partition_kind']]
            self.assertLessEqual(min(distances), 1)
        self.assertGreater(result['summary']['omitted_eligible_cartesian_origin_paths'], 0)
        self.assertEqual(result['summary']['complete_proposal_paths']
            + result['summary']['omitted_eligible_cartesian_origin_paths'],
            result['summary']['eligible_cartesian_origin_paths'])

    def test_partitions_have_exact_cartesian_counts_not_zipped_coverage(self):
        result = self.result()
        counts = {tuple(r['point_indices']): r['eligible_origins'] for r in result['intervals']}
        for row in result['partitions']:
            if row['point_indices'] is not None:
                expected = prod(counts[p] for p in zip(row['point_indices'], row['point_indices'][1:]))
                self.assertEqual(row['eligible_cartesian_origin_paths'], expected)
                self.assertEqual(expected, row['proposed_paths'] + row['omitted_eligible_cartesian_origin_paths'])

    def test_every_registered_key_including_unknown_has_its_own_requests(self):
        result, (_, lattice, _) = self.result(), self.inputs()
        keys = {key['record_id'] for key in lattice['keys']}
        self.assertEqual({s['key_id'] for s in result['selectors']}, keys)
        self.assertEqual(len(result['shape_request_groups']), len(result['complete_proposal_paths']) * len(keys))
        unknown = next(k['record_id'] for k in lattice['keys'] if k['segments'][0]['mode'] == 'unknown')
        self.assertTrue(any(r['key_ref']['record_id'] == unknown and r['cuts'] for r in result['shape_request_groups']))

    def test_each_shape_request_requires_source_and_target_not_subset_only(self):
        result = self.result()
        for row in result['shape_request_groups']:
            for cut in row['cuts']:
                eligible = [shape['assumption'] for shape in cut['checked_shapes'] if shape['shape_request_eligible']]
                self.assertEqual(cut['request_options'], [None, *eligible])
                self.assertEqual(len(cut['checked_shapes']), 10)
                for shape in cut['checked_shapes']:
                    self.assertEqual(shape['shape_request_eligible'],
                        shape['source_shape_compatible'] is True and shape['target_shape_compatible'] is True)

    def test_same_source_family_does_not_ignore_major_minor_target_mismatch(self):
        result = self.result()
        shapes = [s for r in result['shape_request_groups'] for c in r['cuts'] for s in c['checked_shapes']]
        mismatches = [s for s in shapes if s['source_shape_compatible'] is True and s['target_shape_compatible'] is False]
        self.assertTrue(mismatches)
        self.assertTrue(all(s['shape_request_eligible'] is False for s in mismatches))

    def test_expanded_source_member_superset_is_not_strict_V7_request(self):
        # Pure perturbed-shape counterexample, not a newly issued native origin.
        result = self.result()
        _, lattice, _ = self.inputs()
        origins = {o['record_id']: o for e in lattice['catalog_inventory'] for o in e['origins']}
        group, cut = next((r, c) for r in result['shape_request_groups'] for c in r['cuts']
            if {'family': 'V7', 'quality': 'M'} in c['request_options'])
        source = deepcopy(origins[cut['source_origin_ref']['record_id']])
        target = origins[cut['target_origin_ref']['record_id']]
        step, alter = kernels._old(source['root'])
        next_step = kernels.LETTERS[(kernels.LETTERS.index(step) + 1) % 7]
        next_alter = (kernels.NATURAL[step] + alter + 2 - kernels.NATURAL[next_step]) % 12
        if next_alter > 6:
            next_alter -= 12
        source['members'].append(kernels._pitch((next_step, Fraction(next_alter))))
        key = next(k for k in lattice['keys'] if kernels._ref(k) == group['key_ref'])
        shape = kernels._function(self.inputs()[0], source, target, key['segments'][0], 'V7', 'M')
        self.assertIs(shape['shape_compatible'], False)
        self.assertEqual(engine._bucket(source)[0], 'nonordinary_or_unassessed')

    def test_complete_shape_none_vector_cartesian_is_preserved(self):
        result = self.result()
        actual = {digest(s) for s in result['selectors']}
        for row in result['shape_request_groups']:
            path = result['complete_proposal_paths'][row['path_index']]
            self.assertEqual(row['complete_vector_count'], prod(len(c['request_options']) for c in row['cuts']))
            for vector in product(*(c['request_options'] for c in row['cuts'])):
                selector = {'origin_ids': path['origin_ids'], 'key_id': row['key_ref']['record_id'],
                    'transition_assumptions': list(vector)}
                self.assertIn(digest(selector), actual)

    def test_home_triad_to_IV_preserves_V_shape_and_None_not_secondary_proof(self):
        result = self.result('home_to_IV')
        _, lattice, _ = self.inputs('home_to_IV')
        origins = {o['record_id']: o for e in lattice['catalog_inventory'] for o in e['origins']}
        matching = []
        for row in result['shape_request_groups']:
            path = result['complete_proposal_paths'][row['path_index']]
            if len(path['origin_ids']) != 2:
                continue
            left, right = [origins[i] for i in path['origin_ids']]
            if (kernels._old(left['root']), kernels._old(right['root'])) == (['C', 0], ['F', 0]) and len(left['members']) == len(right['members']) == 3:
                matching.append(row['cuts'][0])
        self.assertTrue(matching)
        self.assertTrue(any({'family': 'V', 'quality': 'M'} in cut['request_options'] for cut in matching))
        self.assertTrue(all(cut['request_options'][0] is None and cut['secondary_support'] is None for cut in matching))

    def test_missing_members_are_preserved_without_virtual_member_or_omission(self):
        result = self.result()
        proposals = [p for row in result['intervals'] for p in row['proposals']]
        self.assertTrue(any(p['missing_guarded_member_spellings'] > 0 for p in proposals))
        self.assertTrue(all(p['simultaneous_core_certified'] is False for p in proposals))
        self.assertFalse(any('omission_confirmed' in p for p in proposals))

    def test_arpeggio_tie_and_rational_source_inputs_unchanged(self):
        for name in ('arpeggio', 'tied', 'rational'):
            with self.subTest(name=name):
                inputs = self.inputs(name)
                before = digest(inputs)
                result = engine.propose(*inputs, work_budget=100000000)
                self.assertEqual(result['status'], 'computed_source_progression_proposals_not_evaluated')
                self.assertEqual(digest(inputs), before)
                self.assertEqual(result['analysis_span'], inputs[0]['analysis_span'])

    def test_saved_consumer_never_calls_native_role_or_prior_producers(self):
        inputs = self.inputs()
        with patch.object(native, 'prepare_lattice', side_effect=AssertionError('native replay')), \
             patch.object(native, 'compare_prepared', side_effect=AssertionError('native replay')), \
             patch.object(roles, 'explain_prepared', side_effect=AssertionError('role replay')), \
             patch.object(prior, 'panel_prepared', side_effect=AssertionError('panel replay')):
            self.assertEqual(engine.propose(*inputs, work_budget=100000000)['status'],
                'computed_source_progression_proposals_not_evaluated')

    def test_source_guard_is_cached_once_per_sound(self):
        inputs = self.inputs()
        with patch.object(kernels, '_source_blockers', wraps=kernels._source_blockers) as guard:
            engine.propose(*inputs, work_budget=100000000)
        self.assertEqual(guard.call_count, len(inputs[0]['sound_facts']))

    def test_whole_work_hold_keeps_controls_but_no_new_prefix(self):
        result = engine.propose(*self.inputs(), work_budget=0)
        self.assertEqual(result['status'], 'whole_source_proposal_hold')
        self.assertEqual(result['selectors'], self.inputs()[2]['selectors'])
        self.assertEqual(result['additional_selectors'], [])
        self.assertIsNone(result['summary']['additional_selectors'])
        self.assertIsNone(result['summary']['assessed_origin_occurrences'])
        self.assertEqual(result['complete_proposal_paths'], [])

    def test_whole_path_and_selector_limits_do_not_choose_favorable_prefix(self):
        for limits in ({'max_paths': 0}, {'max_selectors': 0}):
            result = engine.propose(*self.inputs(), work_budget=100000000, **limits)
            self.assertEqual(result['status'], 'whole_source_proposal_hold')
            self.assertEqual(result['selectors'], self.inputs()[2]['selectors'])
            self.assertEqual(result['intervals'], [])
            self.assertIsNone(result['summary']['eligible_cartesian_origin_paths'])

    def test_known_empty_has_zero_not_unknown_counts(self):
        result = self.result('empty')
        self.assertEqual(result['status'], 'computed_source_progression_proposals_not_evaluated')
        self.assertEqual(result['summary']['complete_proposal_paths'], 0)
        self.assertEqual(result['summary']['additional_selectors'], 0)
        self.assertEqual(result['summary']['total_selectors'], 0)

    def test_bad_limits_rejected(self):
        for value in (True, -1, 1.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                engine.propose(*self.inputs(), work_budget=value)

    def test_modified_sealed_input_rejected(self):
        scope, lattice, panel = self.inputs()
        panel['selectors'].reverse()
        with self.assertRaises(ValueError):
            engine.propose(scope, lattice, panel, work_budget=100000000)

    def test_resealed_wrong_control_rejected(self):
        scope, lattice, panel = self.inputs()
        panel['selectors'].reverse()
        panel = reseal(panel, prior.PREFIX)
        with self.assertRaisesRegex(ValueError, 'exact_prior_source'):
            engine.propose(scope, lattice, panel, work_budget=100000000)

    def test_resealed_foreign_lattice_binding_rejected(self):
        scope, lattice, panel = self.inputs()
        lattice['binding']['score_id'] = 'foreign'
        lattice = reseal(lattice, native.PREFIX)
        with self.assertRaises(ValueError):
            engine.propose(scope, lattice, panel, work_budget=100000000)

    def test_current_contract_content_seal_is_deterministic(self):
        first = engine.propose(*self.inputs(), work_budget=100000000)
        second = engine.propose(*self.inputs(), work_budget=100000000)
        self.assertEqual(first, second)
        kernels._check(first, engine.PREFIX)

    def test_persistent_input_mutation_during_shape_call_rejected(self):
        inputs = self.inputs()
        original = kernels._function
        def changed(*args):
            value = original(*args)
            inputs[0]['source_audit']['test_mutation'] = True
            return value
        with patch.object(kernels, '_function', side_effect=changed), self.assertRaisesRegex(ValueError, 'changed_during_call'):
            engine.propose(*inputs, work_budget=100000000)

    def test_contract_change_during_call_rejected(self):
        inputs = self.inputs()
        contract = engine._contract()
        modified = deepcopy(contract)
        modified['version'] = 'changed'
        with patch.object(engine, '_contract', side_effect=[contract, modified]), self.assertRaisesRegex(ValueError, 'changed_during_call'):
            engine.propose(*inputs, work_budget=100000000)


if __name__ == '__main__':
    unittest.main()
