"""Bounded raw-source proposals, not harmony answers or accuracy evaluation.

All public music tests compose a non-TestCase XML-to-IR factory and genuinely
issued native sessions. Pure helper and registry-adversarial tests are labelled
explicitly; none creates a counterfeit supplier, session or annotation answer.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from math import prod
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_interval_lattice_trial as native_trial
from musicanote_harness import factor_musical_view as common
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_source_evidence_panel as panel
from test_factor_expanded_hypotheses import ExpandedHypothesisFixture, event, span
from test_factor_musical_view import reseal


def pitch_key(pitch):
    if pitch is None:
        return None
    return pitch['step'], common.f(pitch['alter'])


def signature(origin):
    root, members = origin['root'], origin['members']
    if root is None or not members or any(common.f(p['alter']).denominator != 1
                                           for p in [root, *members]):
        return None
    return pitch_key(root), tuple(sorted({pitch_key(p) for p in members}))


def source_guarded(sound):
    """Independent literal predicate, not the panel's guard implementation."""
    pitch = sound['pitch']
    return (sound['eligible_as_analysis_source'] is True
            and all(sound.get(field) is True for field in
                    ('source_clock_passed', 'source_pitch_consistency_passed', 'source_attack_consistency_passed'))
            and not sound['source_diagnostics'] and not sound['point'] and not sound['grace']
            and pitch is not None and pitch['step'] in 'CDEFGAB'
            and common.f(pitch['alter']).denominator == 1 and type(pitch['octave']) is int)


def independent_evidence(scope, origin):
    """Exact independent arithmetic over ALL raw scope sounds for one origin."""
    shape = signature(origin)
    root, members = (None, ()) if shape is None else shape
    totals = {name: Fraction() for name in ('member', 'nonmember', 'unknown', 'unsupported')}
    observed, evidence, root_duration = set(), [], Fraction()
    lo, hi = (common.f(origin['span'][side]) for side in ('start', 'end'))
    for sound in scope['sound_facts']:
        if sound['point']:
            continue
        start, end = (common.f(sound['span'][side]) for side in ('start', 'end'))
        a, b = max(start, lo), min(end, hi)
        if a >= b:
            continue
        value, key = b - a, pitch_key(sound['pitch'])
        if not source_guarded(sound):
            totals['unsupported'] += value
        elif shape is None or key is None:
            totals['unknown'] += value
        elif key in members:
            totals['member'] += value
            observed.add(key)
            evidence.append({'sound_ref': sound['sound_ref'], 'source_note_refs': sound['source_note_refs'],
                             'full_sound_span': sound['span'], 'observed_span': span(a, b)})
            if key == root:
                root_duration += value
        else:
            totals['nonmember'] += value
    missing = None if shape is None else len(set(members) - observed)
    eligible = not origin['blockers'] and shape is not None and totals['member'] > 0
    order = (missing if missing is not None else 1000000, -totals['member'], -root_duration,
             () if shape is None else shape, origin['record_id'])
    return {'totals': totals, 'root_duration': root_duration, 'missing': missing,
            'evidence': evidence, 'eligible': eligible, 'order': order, 'signature': shape}


class SourceEvidencePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = ExpandedHypothesisFixture()
        cls.factory.addCleanup = cls.addClassCleanup
        cls.factory.setUp()
        cls.cases, cls.lattices, cls.sessions, cls.handles, cls.results = {}, {}, {}, {}, {}

    def case(self, name='passing'):
        if name not in self.cases:
            lanes = [[event('C4', 0, 1), event('D4', 1, 1), event('E4', 2, 2)],
                     [event(['C3', 'E3', 'G3'], 0, 4)]]
            modify, extent = None, span(1, 2)
            if name == 'rational':
                lanes[0] = [event('C4', 0, Fraction(1, 3)), event('D4', Fraction(1, 3), Fraction(1, 3)),
                            event('E4', Fraction(2, 3), Fraction(10, 3))]
            elif name == 'arpeggio':
                lanes = [[event('C3', 0, 1), event('E3', 1, 1), event('G3', 2, 1), event('C4', 3, 1)]]
            elif name == 'tied':
                lanes[0] = [event('C4', 0, 2, tie_role='start'), event('C4', 2, 1, tie_role='stop'),
                            event('E4', 3, 1)]
            elif name == 'grace':
                lanes[0] = [event('C4', 0, 1), event('D4', 1, 0, grace=True), event('E4', 1, 3)]
            elif name == 'microtone':
                lanes[0][1] = event('D~4', 1, 1)
            elif name == 'bad_member_attack':
                lanes = [lanes[0], [event(['C3', 'G3'], 0, 4)],
                         [event('E3', 0, 1), event('E3', 1, 3)]]
                def modify(ir):
                    sound = next(s for s in ir['sounding_events'] if s['pitch']['spelling'] == 'E3'
                                 and common.f(s['span']['start']) == 0)
                    ir['attack_events'] = [a for a in ir['attack_events']
                                           if a['sounding_event_id'] != sound['sounding_event_id']]
                extent = span(3, 4)
            elif name == 'single':
                lanes = [[event(['C3', 'E4', 'G4'], 0, 4)]]
            elif name == 'empty':
                # A single observed pitch does not invent a supplied chord.
                # This is NOT silence or a repair of the rest-only IR clock.
                lanes = [[event('C3', 0, 4)]]
            elif name == 'three_chords':
                lanes = [[event('F4', 0, 1), event('F#4', 1, 1), event('G4', 2, 2)],
                         [event('A3', 0, 1), event('C4', 1, 1), event('B3', 2, 2)],
                         [event('D3', 0, 1), event('D3', 1, 1), event('G3', 2, 2)],
                         [event('A4', 0, 1), event('A4', 1, 1), event('D4', 2, 2)]]
            elif name != 'passing':
                raise AssertionError('unknown genuine XML fixture: ' + name)
            self.cases[name] = self.factory.fixture(lanes, extent=extent,
                                                  signatures=[{'fifths': 0, 'mode_hint': None}], modify=modify)
        return self.cases[name]

    def lattice(self, name='passing'):
        if name not in self.lattices:
            self.lattices[name] = native.build_lattice(*self.case(name))
        return deepcopy(self.lattices[name])

    def session(self, name='passing'):
        if name not in self.sessions:
            self.sessions[name] = native.prepare_lattice(*self.case(name), self.lattice(name))
        return self.sessions[name]

    def handle(self, name='passing'):
        if name not in self.handles:
            self.handles[name] = panel.prepare_panel(self.session(name))
        return self.handles[name]

    def result(self, name='passing'):
        if name not in self.results:
            self.results[name] = panel.panel_prepared(self.handle(name))
        return deepcopy(self.results[name])

    def origin(self, name, reference):
        return next(o for entry in self.lattice(name)['catalog_inventory'] for o in entry['origins']
                    if common.ref(o) == reference)

    def full(self, name='passing'):
        return next(row for row in self.result(name)['intervals'] if row['span'] == span(0, 4))

    def primary(self, name='passing'):
        return self.full(name)['proposals'][0]

    def verify_arithmetic(self, name='passing'):
        result, lattice, scope = self.result(name), self.lattice(name), self.case(name)[1]
        catalogs = {e['catalog_id']: e for e in lattice['catalog_inventory']}
        for row in result['intervals']:
            entry = catalogs[row['catalog_id']]
            self.assertEqual(row['native_origins'], len(entry['origins']))
            expected = [(o, independent_evidence(scope, o)) for o in entry['origins']]
            eligible = sorted(((o, ev) for o, ev in expected if ev['eligible']), key=lambda pair: pair[1]['order'])
            selected = eligible[:1]
            if eligible:
                different = next((item for item in eligible if item[1]['signature'] != eligible[0][1]['signature']), None)
                if different is not None:
                    selected.append(different)
            self.assertEqual(row['eligible_origins'], len(eligible))
            self.assertEqual(row['rejected_origins'], len(expected) - len(eligible))
            self.assertEqual(row['distinct_eligible_spelling_signatures'], len({ev['signature'] for _, ev in eligible}))
            self.assertEqual(row['proposal_count'], len(selected))
            self.assertEqual(row['omitted_eligible_origins'], len(eligible) - len(selected))
            self.assertEqual([p['origin_ref'] for p in row['proposals']], [common.ref(o) for o, _ in selected])
            for proposal, (origin, ev) in zip(row['proposals'], selected):
                self.assertEqual(proposal['root'], origin['root'])
                self.assertEqual(proposal['members'], origin['members'])
                self.assertEqual(proposal['guarded_pooled_member_note_time'], common.q(ev['totals']['member']))
                self.assertEqual(proposal['guarded_root_note_time'], common.q(ev['root_duration']))
                self.assertEqual(proposal['missing_guarded_member_spellings'], ev['missing'])
                self.assertEqual(proposal['raw_note_time_by_support'], {k: common.q(v) for k, v in ev['totals'].items()})
                self.assertEqual(proposal['member_sound_evidence'], ev['evidence'])
                self.assertIs(proposal['simultaneous_core_certified'], False)
                self.assertIs(proposal['eligible'], True)
        self.assertEqual(result['summary']['evaluated_origin_occurrences'], sum(r['native_origins'] for r in result['intervals']))
        self.assertEqual(result['summary']['eligible_origin_occurrences'], sum(r['eligible_origins'] for r in result['intervals']))
        self.assertEqual(result['summary']['rejected_origin_occurrences'], sum(r['rejected_origins'] for r in result['intervals']))

    def test_genuine_xml_owned_native_panel_reproducible(self):
        result = self.result()
        self.assertEqual(result['status'], 'computed_source_evidence_panel_not_selected')
        self.assertEqual(result, panel.panel_prepared(self.handle()))
        self.assertIs(panel.validate_panel_prepared(self.handle(), result), True)

    def test_raw_inputs_lattice_and_supplier_origins_not_mutated(self):
        before = deepcopy((self.case(), self.lattice()))
        self.result()
        self.assertEqual((self.case(), self.lattice()), before)

    def test_every_requested_origin_scanned_and_exact_support_orders_two_proposals(self):
        self.verify_arithmetic()

    def test_rational_triplet_support_and_order_are_exact(self):
        self.verify_arithmetic('rational')
        primary = self.primary('rational')
        self.assertEqual(primary['guarded_pooled_member_note_time'], common.q(Fraction(47, 3)))
        self.assertEqual(primary['guarded_root_note_time'], common.q(Fraction(13, 3)))
        self.assertEqual(primary['raw_note_time_by_support']['nonmember'], common.q(Fraction(1, 3)))

    def test_fullhold_member_time_counts_all_voices_not_elapsed_length(self):
        primary = self.primary()
        self.assertEqual(primary['guarded_pooled_member_note_time'], common.q(15))
        self.assertEqual(primary['guarded_root_note_time'], common.q(5))
        self.assertEqual(sum(common.f(v) for v in primary['raw_note_time_by_support'].values()), 16)
        self.assertEqual(primary['missing_guarded_member_spellings'], 0)

    def test_membership_uses_exact_written_spelling_not_supplier_ornament_state(self):
        self.verify_arithmetic('three_chords')
        for row in self.result('three_chords')['intervals']:
            for proposal in row['proposals']:
                self.assertIs(proposal['source_ornaments_used'], False)
                self.assertIs(proposal['source_annotation_labels_used'], False)

    def test_provider_aliases_do_not_become_distinct_signature_competitors(self):
        self.verify_arithmetic()
        for row in self.result()['intervals']:
            values = [signature(self.origin('passing', p['origin_ref'])) for p in row['proposals']]
            self.assertEqual(len(values), len(set(values)))
            self.assertLessEqual(len(values), 2)

    def test_origin_refs_keep_exact_native_provider_pointer_and_body(self):
        for row in self.result()['intervals']:
            for proposal in row['proposals']:
                origin = self.origin('passing', proposal['origin_ref'])
                self.assertTrue(origin['record_id'].startswith(native.ORIGIN_PREFIX))
                self.assertIs(origin['legacy_origin_rebound'], False)
                self.assertEqual(origin['provenance']['kind'], 'fresh_native_interval_inclusive_supplier')
                self.assertIs(origin['provenance']['source_annotation_labels_used'], False)
                self.assertTrue(origin['supplier_record_pointer'].startswith('/candidates/'))

    def test_source_note_refs_full_spans_and_halfopen_clips_are_not_discarded(self):
        scope = self.case()[1]
        sounds = {s['sound_ref']: s for s in scope['sound_facts']}
        for row in self.result()['intervals']:
            lo, hi = (common.f(row['span'][side]) for side in ('start', 'end'))
            for proposal in row['proposals']:
                for evidence in proposal['member_sound_evidence']:
                    sound = sounds[evidence['sound_ref']]
                    self.assertEqual(evidence['source_note_refs'], sound['source_note_refs'])
                    self.assertEqual(evidence['full_sound_span'], sound['span'])
                    a, b = (common.f(sound['span'][side]) for side in ('start', 'end'))
                    self.assertEqual(evidence['observed_span'], span(max(a, lo), min(b, hi)))
                    self.assertLess(common.f(evidence['observed_span']['start']), common.f(evidence['observed_span']['end']))

    def test_tied_full_sound_has_multiple_source_notes_but_no_duration_duplication(self):
        self.verify_arithmetic('tied')
        tied = next(s for s in self.case('tied')[1]['sound_facts'] if len(s['source_note_refs']) == 2)
        evidence = next(e for e in self.primary('tied')['member_sound_evidence'] if e['sound_ref'] == tied['sound_ref'])
        self.assertEqual(evidence['source_note_refs'], tied['source_note_refs'])
        self.assertEqual(evidence['full_sound_span'], span(0, 3))
        self.assertEqual(self.primary('tied')['guarded_pooled_member_note_time'], common.q(16))

    def test_arpeggiated_pooled_spellings_are_not_simultaneous_core_certificate(self):
        self.verify_arithmetic('arpeggio')
        primary = self.primary('arpeggio')
        self.assertEqual(primary['missing_guarded_member_spellings'], 0)
        self.assertEqual(primary['guarded_pooled_member_note_time'], common.q(4))
        self.assertIs(primary['simultaneous_core_certified'], False)
        self.assertLessEqual(max(len(cell['sound_refs']) for cell in kernels._profile(
            self.case('arpeggio')[1], self.origin('arpeggio', primary['origin_ref']))['cells']), 1)

    def test_grace_point_gets_no_positive_time_source_support(self):
        self.verify_arithmetic('grace')
        grace = {s['sound_ref'] for s in self.case('grace')[1]['sound_facts'] if s['point'] or s['grace']}
        self.assertTrue(grace)
        for row in self.result('grace')['intervals']:
            for proposal in row['proposals']:
                self.assertTrue(grace.isdisjoint(e['sound_ref'] for e in proposal['member_sound_evidence']))

    def test_microtone_is_unsupported_not_enharmonically_rounded_member(self):
        self.verify_arithmetic('microtone')
        full = self.full('microtone')
        self.assertEqual(full['proposals'], [])
        self.assertGreater(full['rejected_origins'], 0)
        # Direct guard-helper inspection of a genuine withheld supplied origin;
        # this body is not a selected public proposal or a musical answer.
        entry = next(e for e in self.lattice('microtone')['catalog_inventory'] if e['span'] == span(0, 4))
        evidence, _, _ = panel._evidence(self.case('microtone')[1], entry['origins'][0])
        self.assertEqual(evidence['raw_note_time_by_support']['unsupported'], common.q(1))

    def test_bad_attack_member_retained_as_unsupported_not_positive_support(self):
        self.verify_arithmetic('bad_member_attack')
        scope = self.case('bad_member_attack')[1]
        bad = next(s for s in scope['sound_facts'] if s['source_attack_consistency_passed'] is not True)
        for row in self.result('bad_member_attack')['intervals']:
            for proposal in row['proposals']:
                self.assertNotIn(bad['sound_ref'], {e['sound_ref'] for e in proposal['member_sound_evidence']})
        entry = next(e for e in self.lattice('bad_member_attack')['catalog_inventory'] if e['span'] == span(0, 4))
        for origin in entry['origins']:
            evidence, _, _ = panel._evidence(scope, origin)
            self.assertEqual(evidence['raw_note_time_by_support']['unsupported'], common.q(1))

    def test_all_registered_keys_including_unknown_retained_per_proposal_path(self):
        result, lattice = self.result(), self.lattice()
        keys = {k['record_id'] for k in lattice['keys']}
        self.assertEqual(result['keys'], [common.ref(k) for k in sorted(lattice['keys'], key=lambda k: k['record_id'])])
        unknown = {k['record_id'] for k in lattice['keys'] if k['segments'][0]['mode'] == 'unknown'}
        self.assertTrue(unknown)
        for path in result['complete_proposal_paths']:
            selectors = [s for s in result['selectors'] if s['origin_ids'] == path['origin_ids']]
            self.assertEqual({s['key_id'] for s in selectors}, keys)
            self.assertTrue(unknown <= {s['key_id'] for s in selectors})

    def test_none_and_uniform_explicit_function_vectors_are_hypotheses_not_inference(self):
        for selector in self.result()['selectors']:
            vector = selector['transition_assumptions']
            self.assertEqual(len(vector), len(selector['origin_ids']) - 1)
            self.assertTrue(not vector or all(v is None for v in vector)
                            or all(v == {'family': 'V7', 'quality': 'M'} for v in vector))

    def test_fixed_observed_partitions_use_positive_literal_coordinates(self):
        lattice, result = self.lattice(), self.result()
        points = [common.f(p) for p in lattice['coordinate_times']]
        expected = panel._partitions(points)
        self.assertEqual([(r['partition_kind'], r['point_indices']) for r in result['partitions']], expected)
        for row in result['partitions']:
            if row['point_indices'] is not None:
                self.assertEqual(row['point_indices'], sorted(set(row['point_indices'])))
                self.assertEqual((row['point_indices'][0], row['point_indices'][-1]), (0, len(points) - 1))

    def test_requested_intervals_are_unique_not_counted_once_per_partition(self):
        result = self.result()
        pairs = {tuple(pair) for row in result['partitions'] if row['point_indices'] is not None
                 for pair in zip(row['point_indices'], row['point_indices'][1:])}
        self.assertEqual({tuple(row['point_indices']) for row in result['intervals']}, pairs)
        self.assertEqual(result['summary']['requested_intervals'], len(pairs))

    def test_two_zipped_paths_are_not_cartesian_cross_slot_combinations(self):
        result = self.result()
        chosen = {tuple(r['point_indices']): r['proposals'] for r in result['intervals']}
        inventories = {tuple(r['point_indices']): r for r in result['intervals']}
        for partition in result['partitions']:
            rows = [p for p in result['complete_proposal_paths'] if p['partition_kind'] == partition['partition_kind']]
            self.assertLessEqual(len(rows), 2)
            if partition['point_indices'] is None:
                self.assertEqual(rows, [])
                continue
            slots = [chosen[tuple(pair)] for pair in zip(partition['point_indices'], partition['point_indices'][1:])]
            entries = [inventories[tuple(pair)] for pair in zip(partition['point_indices'], partition['point_indices'][1:])]
            self.assertEqual(partition['eligible_cartesian_origin_paths'], prod(e['eligible_origins'] for e in entries))
            self.assertEqual(partition['eligible_cartesian_signature_paths'],
                             prod(e['distinct_eligible_spelling_signatures'] for e in entries))
            self.assertEqual(partition['omitted_eligible_cartesian_origin_paths'],
                             partition['eligible_cartesian_origin_paths'] - len(rows))
            for path in rows:
                self.assertEqual(path['origin_ids'], [proposals[min(path['proposal_lane'], len(proposals) - 1)]['origin_ref']['record_id']
                                                     for proposals in slots])
        self.assertEqual(len({tuple(p['origin_ids']) for p in result['complete_proposal_paths']}),
                         len(result['complete_proposal_paths']))

    def test_selector_counts_exact_and_unique_below_whole_plan_bound(self):
        result, lattice = self.result(), self.lattice()
        paths = result['complete_proposal_paths']
        expected = sum(len(lattice['keys']) * (1 if len(p['origin_ids']) == 1 else 2) for p in paths)
        self.assertEqual(result['summary']['submitted_selectors'], expected)
        self.assertEqual(len(result['selectors']), expected)
        self.assertEqual(len({common.digest(s) for s in result['selectors']}), expected)
        self.assertLessEqual(expected, result['query_plan']['selector_upper_bound'])
        self.assertEqual(result['summary']['unsubmitted_selector_bound'], result['query_plan']['selector_upper_bound'] - expected)

    def test_no_internal_endpoints_has_no_fabricated_half_or_thirds_path(self):
        result = self.result('single')
        self.assertGreaterEqual(len(result['complete_proposal_paths']), 1)
        self.assertLessEqual(len(result['complete_proposal_paths']), 2)
        self.assertTrue(all(p['partition_kind'] == 'whole_hold' for p in result['complete_proposal_paths']))
        self.assertTrue(all(p['point_indices'] is None for p in result['partitions'][1:]))
        self.assertEqual(result['status'], 'computed_source_evidence_panel_not_selected')

    def test_two_coordinate_scope_needs_only_fullhold_selector_bound(self):
        result = panel.panel_prepared(self.handle('single'), max_selectors=10)
        self.assertEqual(result['status'], 'computed_source_evidence_panel_not_selected')
        self.assertLessEqual(result['query_plan']['selector_upper_bound'], 10)
        self.assertEqual(result['query_plan']['structural_selector_upper_bound'], 10)
        self.assertEqual(len(result['selectors']), result['summary']['submitted_selectors'])

    def test_genuine_single_pitch_empty_supplier_known_zero_and_work_not_unknown(self):
        lattice = self.lattice('empty')
        self.assertEqual(lattice['status'], 'ready_native_interval_lattice')
        self.assertEqual(lattice['materialized_origins'], 0)
        result = panel.panel_prepared(self.handle('empty'), max_selectors=0, selection_work_budget=0)
        self.assertEqual(result['status'], 'computed_source_evidence_panel_not_selected')
        self.assertEqual(result['selectors'], [])
        for field in ('evaluated_origin_occurrences', 'eligible_origin_occurrences', 'rejected_origin_occurrences',
                      'complete_proposal_paths', 'submitted_selectors', 'planned_selector_upper_bound', 'unsubmitted_selector_bound'):
            self.assertEqual(result['summary'][field], 0)
        for field in ('origin_evaluations', 'source_sound_visits', 'source_reference_visit_upper_bound',
                      'selector_upper_bound', 'planned_selection_work'):
            self.assertEqual(result['query_plan'][field], 0)

    def test_logical_native_universe_is_preserved_not_reduced_to_selected_panel(self):
        result, lattice = self.result(), self.lattice()
        self.assertEqual(result['logical_universe'], lattice['universe'])
        self.assertEqual(result['scope_ref'], common.ref(self.case()[1]))
        self.assertEqual(result['lattice_ref'], common.ref(lattice))
        self.assertGreater(lattice['universe']['logical_path_keys'], len(result['selectors']))

    def test_selector_budget_zero_is_whole_hold_with_no_favorable_prefix(self):
        result = panel.panel_prepared(self.handle(), max_selectors=0)
        self.assertEqual(result['status'], 'whole_source_panel_hold')
        for field in ('intervals', 'partitions', 'selectors', 'complete_proposal_paths'):
            self.assertEqual(result[field], [])
        self.assertIsNone(result['summary']['evaluated_origin_occurrences'])
        self.assertIsNone(result['summary']['eligible_origin_occurrences'])
        self.assertGreater(result['query_plan']['origin_evaluations'], 0)

    def test_selection_work_zero_is_whole_hold_not_known_zero_origins(self):
        result = panel.panel_prepared(self.handle(), selection_work_budget=0)
        self.assertEqual(result['status'], 'whole_source_panel_hold')
        self.assertEqual(result['selectors'], [])
        self.assertIsNone(result['summary']['rejected_origin_occurrences'])
        self.assertGreater(result['query_plan']['planned_selection_work'], 0)

    def test_exact_whole_work_and_selector_bounds_pass_but_one_less_withholds(self):
        full = self.result()
        selectors, work = full['query_plan']['selector_upper_bound'], full['query_plan']['planned_selection_work']
        exact = panel.panel_prepared(self.handle(), max_selectors=selectors, selection_work_budget=work)
        self.assertEqual(exact['status'], 'computed_source_evidence_panel_not_selected')
        self.assertEqual(exact['selectors'], full['selectors'])
        for caps in ({'max_selectors': selectors - 1}, {'selection_work_budget': work - 1}):
            self.assertEqual(panel.panel_prepared(self.handle(), **caps)['status'], 'whole_source_panel_hold')

    def test_whole_lattice_hold_not_misreported_as_known_no_evaluable_candidates(self):
        lattice = native.build_lattice(*self.case(), max_catalogs=0)
        session = native.prepare_lattice(*self.case(), lattice)
        result = panel.panel_prepared(panel.prepare_panel(session))
        self.assertEqual(result['status'], 'whole_source_panel_hold')
        self.assertIsNone(result['summary']['evaluated_origin_occurrences'])
        self.assertEqual(result['selectors'], [])
        self.assertIn('whole_native_lattice_unavailable', result['reasons'])

    def test_observed_cut_grid_hold_preserves_unknown_work_and_native_request(self):
        lattice = native.build_lattice(*self.case(), max_cut_coordinates=0)
        session = native.prepare_lattice(*self.case(), lattice)
        result = panel.panel_prepared(panel.prepare_panel(session))
        self.assertEqual(result['status'], 'whole_source_panel_hold')
        self.assertEqual(result['selectors'], [])
        self.assertEqual(result['native_request'], {key: lattice[key] for key in ('status', 'reasons', 'resource_limits')})
        for field in ('origin_evaluations', 'source_sound_visits', 'source_reference_visit_upper_bound',
                      'selector_upper_bound', 'planned_selection_work'):
            self.assertIsNone(result['query_plan'][field])
        self.assertIsNone(result['summary']['planned_selector_upper_bound'])
        self.assertIsNone(result['summary']['unsubmitted_selector_bound'])
        self.assertEqual(result['query_plan']['available_intervals'], 0)
        self.assertGreater(result['query_plan']['requested_intervals'], 0)

    def test_native_origin_index_hold_not_certified_zero_supplier_or_work(self):
        lattice = native.build_lattice(*self.case(), max_variants=0)
        self.assertGreater(lattice['origin_count'], 0)
        self.assertEqual(lattice['materialized_origins'], 0)
        self.assertTrue(any(e['variant_count'] > 0 and e['origins'] == [] for e in lattice['catalog_inventory']))
        session = native.prepare_lattice(*self.case(), lattice)
        result = panel.panel_prepared(panel.prepare_panel(session))
        self.assertEqual(result['status'], 'whole_source_panel_hold')
        self.assertEqual(result['selectors'], [])
        for field in ('origin_evaluations', 'source_sound_visits', 'selector_upper_bound', 'planned_selection_work'):
            self.assertIsNone(result['query_plan'][field])
        self.assertIsNone(result['summary']['eligible_origin_occurrences'])
        self.assertIsNone(result['summary']['unsubmitted_selector_bound'])

    def test_invalid_caps_rejected_before_unissued_handle_reads(self):
        for field in ('max_selectors', 'selection_work_budget'):
            for value in (-1, True, 1.5, None, '1'):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    panel.panel_prepared(None, **{field: value})

    def test_unissued_native_or_panel_handles_have_no_authority(self):
        for value in (None, {}, object()):
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                panel.prepare_panel(value)
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                panel.panel_prepared(value)

    def test_native_state_identity_change_rejected_even_for_reauthenticated_clone(self):
        session, handle = self.session(), self.handle()
        original = native._SESSIONS[session]
        clone = replace(original)
        object.__setattr__(clone, 'authentication', native._auth(session, clone))
        try:
            native._SESSIONS[session] = clone
            self.assertIs(native._issued(session), clone)
            with self.assertRaises(ValueError):
                panel.panel_prepared(handle)
        finally:
            native._SESSIONS[session] = original
        self.assertEqual(panel.panel_prepared(handle), self.result())

    def test_own_immutable_state_clone_cannot_reuse_authentication(self):
        handle = self.handle()
        original = panel._SESSIONS[handle]
        try:
            panel._SESSIONS[handle] = replace(original)
            with self.assertRaises(ValueError):
                panel.panel_prepared(handle)
        finally:
            panel._SESSIONS[handle] = original

    def test_current_source_bytes_invalidate_prepared_panel(self):
        handle = self.handle()
        original, target = Path.read_bytes, Path(panel.__file__)
        def modified_bytes(path):
            value = original(path)
            return value + b'\n' if path == target else value
        with patch.object(Path, 'read_bytes', modified_bytes), self.assertRaises(ValueError):
            panel.panel_prepared(handle)

    def test_contract_change_during_prepare_prevents_issuance(self):
        original = panel._contract()
        changed = deepcopy(original)
        changed['source_sha256'] = '0' * 64
        with patch.object(panel, '_contract', side_effect=[original, changed]), self.assertRaises(ValueError):
            panel.prepare_panel(self.session())

    def test_returned_mutation_does_not_change_owned_source_or_next_panel(self):
        original = self.result()
        changed = panel.panel_prepared(self.handle())
        changed['selectors'].clear()
        changed['intervals'][0]['proposals'].clear()
        self.assertEqual(panel.panel_prepared(self.handle()), original)

    def test_resealed_modified_panel_is_not_validation_authority(self):
        changed = self.result()
        changed['intervals'][0]['proposals'][0]['guarded_pooled_member_note_time'] = common.q(999)
        changed = reseal(changed, panel.PREFIX)
        with self.assertRaises(ValueError):
            panel.validate_panel_prepared(self.handle(), changed)

    def test_foreign_panel_cannot_validate_against_different_genuine_native_state(self):
        with self.assertRaises(ValueError):
            panel.validate_panel_prepared(self.handle('rational'), self.result())

    def test_native_comparison_and_role_engine_accept_actual_panel_once_positive_control(self):
        session, result, scope = self.session(), self.result(), self.case()[1]
        before = deepcopy((self.case(), self.lattice(), result))
        links = native_trial.greedy_links(scope, 20)
        self.assertTrue(links)
        results = {}
        for kind, requested in (('greedy', links), ('control', [])):
            bundle = native.compile_bundle_prepared(session, requested)
            self.assertEqual(bundle['status'], 'complete_all_lane_witness')
            comparison = native.compare_prepared(session, result['selectors'], bundle['record_id'],
                                                  max_hypotheses=64, max_slots=3, query_work_budget=2000000)
            explanation = roles.explain_prepared(roles.prepare_explanations(session, comparison),
                                                  query_work_budget=100000000)
            # Predeclared synthetic all-50-selector budget. Production trial
            # budget holds must remain holds, never favorable-prefix fallback.
            self.assertEqual(explanation['status'], 'computed_native_role_explanations_not_selected')
            self.assertEqual(comparison['selectors'], result['selectors'])
            self.assertEqual(explanation['bundle_ref'], common.ref(bundle))
            self.assertEqual(len(explanation['paths']), len(result['selectors']))
            for p, original in zip(explanation['paths'], comparison['paths']):
                self.assertIs(p['account']['raw_time_conserved'], True)
                self.assertEqual(p['account']['raw_total_note_time_quarters'],
                                 original['whole_path_account']['raw_total_note_time_quarters'])
            results[kind] = explanation
        self.assertTrue(any(c['role'] == 'local_passing' and c['status'] == 'supported'
                            for p in results['greedy']['paths'] for c in p['clauses']))
        self.assertFalse(any(c['role'] == 'local_passing' and c['status'] == 'supported'
                             for p in results['control']['paths'] for c in p['clauses']))
        self.assertEqual((self.case(), self.lattice(), result), before)

    def test_three_chord_source_fixture_does_not_assert_secondary_key_or_cadence_answer(self):
        self.verify_arithmetic('three_chords')
        result = self.result('three_chords')
        self.assertTrue(result['selectors'])
        self.assertTrue(any(len(p['origin_ids']) == 3 for p in result['complete_proposal_paths']))
        self.assertIsNone(result['selected'])
        self.assertIs(result['flags']['cadence_confirmed'], False)

    def test_pure_helper_supplier_ornament_states_and_labels_cannot_change_order(self):
        # Pure helper perturbation only. A modified origin body is NOT issued
        # native authority and is never submitted to the public panel engine.
        origin = self.origin('passing', self.primary()['origin_ref'])
        changed = deepcopy(origin)
        changed['supplier_event_states'] = [{'state': 'confirmed_passing_tone', 'annotation': 'V7/V'}]
        changed['supplier_note_time_quarters'] = {'non_chord_tone': common.q(999)}
        changed['provenance']['source_path'] = 'fake-human-gold-cadence'
        self.assertEqual(panel._evidence(self.case()[1], origin), panel._evidence(self.case()[1], changed))

    def test_pure_helper_enharmonic_same_pc_not_same_spelling_signature(self):
        # Pure signature helper test, not a supplied or selected new candidate.
        origin = self.origin('passing', self.primary()['origin_ref'])
        changed = deepcopy(origin)
        changed['members'][1] = {'step': 'F', 'alter': common.q(-1)}
        self.assertNotEqual(panel._signature(origin), panel._signature(changed))

    def test_pure_partitions_nearest_exact_tie_uses_earlier_observed_cut(self):
        self.assertEqual(panel._partitions([Fraction(0), Fraction(1), Fraction(3), Fraction(4)])[1],
                         ('nearest_half_two_slots', [0, 1, 3]))
        with self.assertRaises(ValueError):
            panel._partitions([Fraction(0), Fraction(0), Fraction(4)])

    def test_pure_planner_member_and_long_tie_closures_increase_whole_work_bound(self):
        # Pure planning arithmetic over detached inputs, never music authority.
        lattice, scope = self.lattice(), deepcopy(self.case()[1])
        entry = deepcopy(next(e for e in lattice['catalog_inventory'] if e['span'] == span(0, 4)))
        specs = [('pure_whole_hold', entry['point_indices'])]
        keys = len(lattice['keys'])
        base = panel._plan(scope, [entry], keys, specs)
        scope['sound_facts'][0]['source_note_refs'] = ['pure-note-' + str(i) for i in range(101)]
        long_tie = panel._plan(scope, [entry], keys, specs)
        self.assertGreater(long_tie['source_reference_visit_upper_bound'], base['source_reference_visit_upper_bound'])
        self.assertGreater(long_tie['planned_selection_work'], base['planned_selection_work'])
        origin = next(o for o in entry['origins'] if o['members'])
        origin['members'].extend([deepcopy(origin['members'][0]) for _ in range(100)])
        extended = panel._plan(scope, [entry], keys, specs)
        source_size = len(scope['sound_facts']) + sum(len(s['source_note_refs']) for s in scope['sound_facts']) + 1
        self.assertEqual(extended['planned_selection_work'] - long_tie['planned_selection_work'], source_size * 100)

    def test_pure_partial_certified_zero_path_does_not_certify_unknown_complete_scan(self):
        # Detached storage/planning counterexample, not a native public record.
        lattice, scope = self.lattice(), self.case()[1]
        entry = deepcopy(next(e for e in lattice['catalog_inventory'] if e['point_indices'] == [0, 1]))
        entry.update(origins=[], variant_count=0, status='ready_native_interval')
        last = len(lattice['coordinate_times']) - 1
        plan = panel._plan(scope, [entry], len(lattice['keys']), [('pure_two_slots', [0, 1, last])])
        self.assertEqual(plan['selector_upper_bound'], 0)
        self.assertEqual(plan['available_origin_inventory'], 0)
        self.assertIsNone(plan['origin_evaluations'])
        self.assertIsNone(plan['planned_selection_work'])
        self.assertIsNone(plan['sorting_comparison_upper_bound'])

    def test_no_final_harmony_nct_winner_rank_or_training_promotion(self):
        result = self.result()
        for field in ('selected', 'rank', 'confidence'):
            self.assertIsNone(result[field])
        self.assertTrue(all(value is False for value in result['flags'].values()))
        for row in result['intervals']:
            for p in row['proposals']:
                self.assertIsNone(p['selected'])
                self.assertIsNone(p['confidence'])
                self.assertIs(p['simultaneous_core_certified'], False)


if __name__ == '__main__':
    unittest.main()
