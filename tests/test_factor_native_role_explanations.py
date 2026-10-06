"""Native one-completion role explanations, never NCT or harmony verdicts.

The fixture composes a non-TestCase XML-to-Core factory. Native lattice,
ordered selectors, full-scope bundles and comparisons are genuine public API
results; no explanation handle, selected role, or old parent is fabricated.
"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_musical_view as common
from musicanote_harness import factor_temporal_explanations as temporal
from test_factor_expanded_hypotheses import ExpandedHypothesisFixture, event, span
from test_factor_musical_view import reseal


def members(*names):
    return {(name[0], Fraction(name[1:].count('#') - name[1:].count('b'))) for name in names}


class NativeRoleExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = ExpandedHypothesisFixture()
        cls.factory.addCleanup = cls.addClassCleanup
        cls.factory.setUp()
        cls.cases, cls.lattices, cls.sessions = {}, {}, {}

    def case(self, name='passing'):
        if name not in self.cases:
            partitions = [(span(0, 4), ('C', Fraction()), members('C', 'E', 'G'))]
            assumptions = []
            lanes = [[event('C4', 0, 1), event('D4', 1, 1), event('E4', 2, 2)],
                     [event(['C3', 'E3', 'G3'], 0, 4)]]
            modify = None
            if name == 'neighbor':
                lanes[0][-1] = event('C4', 2, 2)
            elif name == 'branch':
                lanes[0][-1] = event(['C4', 'E4'], 2, 2)
            elif name == 'rational':
                lanes[0] = [event('C4', 0, Fraction(1, 3)),
                            event('D4', Fraction(1, 3), Fraction(1, 3)),
                            event('E4', Fraction(2, 3), Fraction(10, 3))]
            elif name == 'member_competitor':
                lanes.append([event('B3', 0, 4)])
            elif name == 'split_triple':
                partitions = [(span(0, 2), ('C', Fraction()), members('C', 'E', 'G')),
                              (span(2, 4), ('C', Fraction()), members('C', 'E', 'G'))]
                assumptions = [None]
            elif name == 'three_slots':
                lanes = [[event('C4', 0, Fraction(1, 2)), event('D4', Fraction(1, 2), Fraction(1, 2)),
                          event('E4', 1, 1), event('F4', 2, 1), event('G4', 3, 1)],
                         [event(['C3', 'E3', 'G3'], 0, 2), event(['F3', 'A3', 'C4'], 2, 1),
                          event(['G3', 'B3', 'D4'], 3, 1)]]
                partitions = [(span(0, 2), ('C', Fraction()), members('C', 'E', 'G')),
                              (span(2, 3), ('F', Fraction()), members('F', 'A', 'C')),
                              (span(3, 4), ('G', Fraction()), members('G', 'B', 'D'))]
                assumptions = [None, None]
            elif name in ('bad_attack', 'microtone', 'grace', 'leap_local', 'octave_neighbor'):
                if name == 'bad_attack':
                    def modify(ir):
                        sound = next(s for s in ir['sounding_events'] if s['pitch']['spelling'] == 'D4')
                        ir['attack_events'] = [a for a in ir['attack_events']
                                               if a['sounding_event_id'] != sound['sounding_event_id']]
                elif name == 'microtone':
                    lanes[0][1] = event('D~4', 1, 1)
                elif name == 'grace':
                    lanes[0][1] = event('D4', 1, 0, grace=True)
                elif name == 'leap_local':
                    lanes[0][1] = event('F4', 1, 1)
                else:
                    lanes[0][-1] = event('C5', 2, 2)
            elif name.startswith('suspension') or name == 'gap':
                source = [event('F4', 0, 3), event('E4', 3, 1)]
                harmony = [[event(['Bb3', 'D4'], 0, 2), event(['C3', 'G3'], 2, 2)]]
                if name == 'suspension_reattack':
                    source = [event('F4', 0, 2), event('F4', 2, Fraction(1, 2)),
                              event('F4', Fraction(5, 2), Fraction(1, 2)), event('E4', 3, 1)]
                elif name == 'suspension_tie':
                    source = [event('F4', 0, 2, tie_role='start'),
                              event('F4', 2, 1, tie_role='stop'), event('E4', 3, 1)]
                elif name == 'suspension_up':
                    source[-1] = event('G4', 3, 1)
                    harmony[0][-1] = event(['C3', 'E3', 'G3'], 2, 2)
                elif name == 'suspension_leap':
                    source[-1] = event('C4', 3, 1)
                    harmony[0][-1] = event(['C3', 'E3', 'G3'], 2, 2)
                elif name == 'suspension_first_adverse':
                    source = [event('F4', 0, 3), event('G4', 3, Fraction(1, 2)),
                              event('E4', Fraction(7, 2), Fraction(1, 2))]
                elif name == 'suspension_terminal':
                    source = [event('F4', 0, 4)]
                    harmony[0][-1] = event(['C3', 'E3', 'G3'], 2, 2)
                elif name == 'suspension_multicut':
                    harmony[0][0:1] = [event(['Bb3', 'D4'], 0, 1), event(['Bb3', 'D4'], 1, 1)]
                elif name == 'gap':
                    source = [event('F4', 0, 2), event(None, 2, 1), event('E4', 3, 1)]
                lanes = [source, *harmony]
                partitions = [(span(0, 2), ('B', Fraction(-1)), members('Bb', 'D', 'F')),
                              (span(2, 4), ('C', Fraction()), members('C', 'E', 'G'))]
                if name == 'suspension_multicut':
                    partitions = [(span(0, 1), ('B', Fraction(-1)), members('Bb', 'D', 'F')),
                                  (span(1, 2), ('B', Fraction(-1)), members('Bb', 'D', 'F')),
                                  partitions[-1]]
                assumptions = [None] * (len(partitions) - 1)
            elif name.startswith('anticipation'):
                source = [event('D4', 0, 3), event('D4', 3, 1)]
                if name == 'anticipation_reattack':
                    source = [event('D4', 0, 2), event('D4', 2, 2)]
                elif name == 'anticipation_tie':
                    source = [event('D4', 0, 2, tie_role='start'),
                              event('D4', 2, 1, tie_role='stop'), event('D4', 3, 1)]
                elif name == 'anticipation_octave':
                    source = [event('D4', 0, 2), event('D5', 2, 2)]
                elif name == 'anticipation_enharmonic':
                    source = [event('D4', 0, 2), event('C##4', 2, 2)]
                lanes = [source, [event(['C3', 'E3', 'G3'], 0, 2), event(['D3', 'F3', 'A3'], 2, 2)]]
                partitions = [(span(0, 2), ('C', Fraction()), members('C', 'E', 'G')),
                              (span(2, 4), ('D', Fraction()), members('D', 'F', 'A'))]
                assumptions = [None]
            elif name.startswith('ordinary') or name == 'combined':
                leading = [event('B4', 0, 3), event('C5', 3, 1)]
                seventh = [event('F4', 0, 3), event('E4', 3, 1)]
                if name == 'ordinary_first_adverse':
                    leading = [event('B4', 0, 3), event('D5', 3, Fraction(1, 2)),
                               event('C5', Fraction(7, 2), Fraction(1, 2))]
                elif name == 'ordinary_reattack':
                    leading = [event('B4', 0, 2), event('B4', 2, Fraction(1, 2)),
                               event('B4', Fraction(5, 2), Fraction(1, 2)), event('C5', 3, 1)]
                    seventh = [event('F4', 0, 2), event('F4', 2, Fraction(1, 2)),
                               event('F4', Fraction(5, 2), Fraction(1, 2)), event('E4', 3, 1)]
                elif name == 'ordinary_terminal':
                    leading = [event('B4', 0, 4)]
                lanes = [leading, seventh,
                         [event(['G3', 'D4'], 0, 2), event(['C3', 'E3', 'G3'], 2, 2)]]
                if name == 'ordinary_doubled':
                    lanes.append([event('B3', 0, 3), event('A3', 3, 1)])
                elif name == 'combined':
                    lanes.append([event('C5', 0, 2), event('C5', 2, Fraction(1, 2)),
                                  event('D5', Fraction(5, 2), Fraction(1, 2)), event('E5', 3, 1)])
                partitions = [(span(0, 2), ('G', Fraction()), members('G', 'B', 'D', 'F')),
                              (span(2, 4), ('C', Fraction()), members('C', 'E', 'G'))]
                assumptions = [{'family': 'V7', 'quality': 'M'}]
            elif name == 'common_member':
                lanes = [[event('G4', 0, 4)],
                         [event(['C3', 'E3'], 0, 2), event(['C3', 'E3'], 2, 2)]]
                partitions = [(span(0, 2), ('C', Fraction()), members('C', 'E', 'G')),
                              (span(2, 4), ('C', Fraction()), members('C', 'E', 'G'))]
                assumptions = [None]
            elif name == 'single':
                lanes = [[event(['C3', 'E4', 'G4'], 0, 4)]]
            elif name != 'passing':
                raise AssertionError('unknown synthetic fixture: ' + name)
            fx = self.factory.fixture(lanes, extent=span(3, 4) if modify else span(1, 2),
                                      signatures=[{'fifths': 0, 'mode_hint': None}], modify=modify)
            self.cases[name] = fx, partitions, assumptions
        return self.cases[name]

    def record(self, name='passing'):
        key = name, common.digest(native._contract())
        if key not in self.lattices:
            self.lattices[key] = native.build_lattice(*self.case(name)[0])
        return deepcopy(self.lattices[key])

    def session(self, name='passing'):
        key = name, common.digest(native._contract())
        if key not in self.sessions:
            self.sessions[key] = native.prepare_lattice(*self.case(name)[0], self.record(name))
        return self.sessions[key]

    @staticmethod
    def pitch_key(pitch):
        return pitch['step'], common.f(pitch['alter'])

    def selector(self, name='passing', *, unknown=False, partitions=None, assumptions=None):
        _, defaults, default_assumptions = self.case(name)
        record = self.record(name)
        origins = []
        for extent, root, expected in partitions or defaults:
            entry = next(e for e in record['catalog_inventory'] if e['span'] == extent)
            if expected is None:
                # Explicitly request a genuine unresolved supplier alternative;
                # never manufacture the unavailable spelling from its PC set.
                found = [o for o in entry['origins'] if o['members'] is None]
            else:
                found = [o for o in entry['origins'] if o['root'] is not None and self.pitch_key(o['root']) == root
                         and o['members'] is not None and {self.pitch_key(p) for p in o['members']} == expected]
            if not found:
                raise AssertionError('genuine supplier origin unavailable: ' + repr((name, extent, root, expected)))
            origins.append(sorted(found, key=lambda o: bool(o['blockers']))[0])
        key = next(k for k in record['keys'] if k['segments'][0]['mode'] == ('unknown' if unknown else 'major'))
        return {'origin_ids': [o['record_id'] for o in origins], 'key_id': key['record_id'],
                'transition_assumptions': deepcopy(default_assumptions if assumptions is None else assumptions)}

    def sound(self, name, step, onset, *, alter=0, octave=4):
        return next(s for s in self.case(name)[0][1]['sound_facts']
                    if self.pitch_key(s['pitch']) == (step, Fraction(alter))
                    and s['pitch']['octave'] == octave and common.f(s['span']['start']) == onset)

    def edge(self, name, left, right):
        def endpoint(value):
            step, onset = value[:2]
            return self.sound(name, step, onset, octave=value[2] if len(value) == 3 else 4)['sound_ref']
        return [endpoint(left), endpoint(right)]

    def links(self, name='passing'):
        if name in ('passing', 'neighbor', 'branch', 'member_competitor', 'split_triple', 'bad_attack', 'leap_local', 'octave_neighbor'):
            end = 'C' if name == 'neighbor' else 'E'
            if name == 'octave_neighbor':
                return [self.edge(name, ('C', 0), ('D', 1)),
                        self.edge(name, ('D', 1), ('C', 2, 5))]
            if name == 'leap_local':
                return [self.edge(name, ('C', 0), ('F', 1)), self.edge(name, ('F', 1), ('E', 2))]
            return [self.edge(name, ('C', 0), ('D', 1)), self.edge(name, ('D', 1), (end, 2))]
        if name == 'rational':
            return [self.edge(name, ('C', 0), ('D', Fraction(1, 3))),
                    self.edge(name, ('D', Fraction(1, 3)), ('E', Fraction(2, 3)))]
        if name == 'three_slots':
            return [self.edge(name, ('C', 0), ('D', Fraction(1, 2))),
                    self.edge(name, ('D', Fraction(1, 2)), ('E', 1))]
        if name in ('suspension', 'suspension_tie', 'suspension_multicut'):
            return [self.edge(name, ('F', 0), ('E', 3))]
        if name == 'suspension_reattack':
            return [self.edge(name, ('F', 0), ('F', 2)),
                    self.edge(name, ('F', 2), ('F', Fraction(5, 2))),
                    self.edge(name, ('F', Fraction(5, 2)), ('E', 3))]
        if name == 'suspension_up':
            return [self.edge(name, ('F', 0), ('G', 3))]
        if name == 'suspension_leap':
            return [self.edge(name, ('F', 0), ('C', 3))]
        if name == 'suspension_first_adverse':
            return [self.edge(name, ('F', 0), ('G', 3)), self.edge(name, ('G', 3), ('E', Fraction(7, 2)))]
        if name == 'anticipation_reattack':
            return [self.edge(name, ('D', 0), ('D', 2))]
        if name == 'anticipation_octave':
            return [self.edge(name, ('D', 0), ('D', 2, 5))]
        if name in ('ordinary', 'ordinary_doubled', 'combined'):
            result = [self.edge(name, ('B', 0), ('C', 3, 5)), self.edge(name, ('F', 0), ('E', 3))]
            if name == 'ordinary_doubled':
                result.append([self.sound(name, 'B', 0, octave=3)['sound_ref'],
                               self.sound(name, 'A', 3, octave=3)['sound_ref']])
            if name == 'combined':
                result.extend([self.edge(name, ('C', 2, 5), ('D', Fraction(5, 2), 5)),
                               self.edge(name, ('D', Fraction(5, 2), 5), ('E', 3, 5))])
            return result
        if name == 'ordinary_first_adverse':
            return [[self.sound(name, 'B', 0)['sound_ref'], self.sound(name, 'D', 3, octave=5)['sound_ref']],
                    [self.sound(name, 'D', 3, octave=5)['sound_ref'], self.sound(name, 'C', Fraction(7, 2), octave=5)['sound_ref']],
                    self.edge(name, ('F', 0), ('E', 3))]
        if name == 'ordinary_reattack':
            result = []
            for step, end, octave in (('B', 'C', 5), ('F', 'E', 4)):
                for a, b in ((0, 2), (2, Fraction(5, 2))):
                    result.append(self.edge(name, (step, a), (step, b)))
                result.append([self.sound(name, step, Fraction(5, 2))['sound_ref'],
                               self.sound(name, end, 3, octave=octave)['sound_ref']])
            return result
        if name == 'ordinary_terminal':
            return [self.edge(name, ('F', 0), ('E', 3))]
        return []

    def comparison(self, name='passing', *, control=False, required=None, selectors=None, **caps):
        session = self.session(name)
        bundle = native.compile_bundle_prepared(session, [] if control else self.links(name) if required is None else required)
        comparison = native.compare_prepared(session, selectors if selectors is not None else [self.selector(name)],
                                              bundle['record_id'], **caps)
        return session, comparison, bundle

    def explain(self, name='passing', *, control=False, required=None, selectors=None, budget=1000000):
        session, comparison, bundle = self.comparison(name, control=control, required=required, selectors=selectors)
        handle = roles.prepare_explanations(session, comparison)
        return roles.explain_prepared(handle, query_work_budget=budget), comparison, bundle

    @staticmethod
    def clauses(result, role=None):
        return [c for p in result['paths'] for c in p['clauses'] if role is None or c['role'] == role]

    def supported(self, result, role):
        return [c for c in self.clauses(result, role) if c['status'] == 'supported']

    def credit(self, result):
        return sum((common.f(p['account']['conditional_explanation_note_time_quarters'])
                    for p in result['paths']), Fraction())

    def assert_account(self, result, comparison):
        self.assertEqual(len(result['paths']), len(comparison['paths']))
        for row, original in zip(result['paths'], comparison['paths']):
            self.assertEqual(row['native_path_ref'], common.ref(original))
            account = row['account']
            self.assertEqual(set(account['note_time_quarters']), set(temporal.CATEGORIES))
            total = common.f(account['raw_total_note_time_quarters'])
            self.assertEqual(total, common.f(original['whole_path_account']['raw_total_note_time_quarters']))
            self.assertEqual(sum((common.f(v) for v in account['note_time_quarters'].values()), Fraction()), total)
            self.assertIs(account['raw_time_conserved'], True)
            if account['conditional_explanation_note_time_quarters'] is None:
                self.assertEqual(account['explained_intervals_by_sound'], [])
                self.assertEqual(account['note_time_quarters']['conditional_explained_nonmember'], common.q(0))
                continue
            explained = common.f(account['conditional_explanation_note_time_quarters'])
            self.assertEqual(explained, common.f(account['note_time_quarters']['conditional_explained_nonmember']))
            self.assertLessEqual(explained, common.f(original['whole_path_account']['raw_state_note_time_quarters']['nonmember_not_confirmed_nct']))
            unions = account['explained_intervals_by_sound']
            self.assertEqual(explained, sum((common.f(s['end']) - common.f(s['start'])
                                            for item in unions for s in item['spans']), Fraction()))
            for item in unions:
                previous_end = None
                for clip in item['spans']:
                    lo, hi = common.f(clip['start']), common.f(clip['end'])
                    self.assertLess(lo, hi)
                    if previous_end is not None:
                        self.assertLess(previous_end, lo)
                    previous_end = hi
                    raw = [r for p in original['profiles'] for r in p['rows']
                           if r['sound_ref'] == item['sound_ref'] and r['state'] == 'nonmember_not_confirmed_nct']
                    self.assertTrue(any(common.f(r['observed_span']['start']) <= lo < hi <= common.f(r['observed_span']['end']) for r in raw))

    def test_genuine_xml_native_public_result_and_reproducibility(self):
        result, comparison, _ = self.explain()
        self.assertEqual(result['status'], 'computed_native_role_explanations_not_selected')
        self.assert_account(result, comparison)
        second, _, _ = self.explain()
        self.assertEqual(second, result)
        self.assertTrue(self.supported(result, 'local_passing'))

    def test_raw_profiles_native_comparison_and_caller_inputs_not_mutated(self):
        session, comparison, bundle = self.comparison()
        inputs = self.case()[0]
        before = deepcopy((inputs, comparison, bundle))
        handle = roles.prepare_explanations(session, comparison)
        roles.explain_prepared(handle)
        self.assertEqual((inputs, comparison, bundle), before)
        self.assertIsNone(comparison['paths'][0]['whole_path_account']['NCT_credited_note_time_quarters'])

    def test_passing_middle_note_only_gets_positive_time_credit(self):
        result, comparison, _ = self.explain()
        self.assertEqual(self.credit(result), 1)
        middle = self.sound('passing', 'D', 1)['sound_ref']
        self.assertEqual({c['sound_ref'] for row in self.supported(result, 'local_passing') for c in row['clips']}, {middle})
        self.assert_account(result, comparison)

    def test_neighbor_same_written_register_middle_only(self):
        result, comparison, _ = self.explain('neighbor')
        self.assertTrue(self.supported(result, 'local_neighbor'))
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertEqual(self.credit(result), 1)
        self.assert_account(result, comparison)

    def test_no_link_control_cannot_borrow_local_contour_edges(self):
        result, comparison, _ = self.explain(control=True)
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertEqual(self.credit(result), 0)
        self.assert_account(result, comparison)

    def test_one_local_edge_is_not_a_complete_triple(self):
        result, _, _ = self.explain(required=self.links()[:1])
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertEqual(self.credit(result), 0)

    def test_branching_neighbor_and_passing_not_unioned_across_bundles(self):
        passing, _, _ = self.explain('branch')
        neighbor_links = [self.edge('branch', ('C', 0), ('D', 1)), self.edge('branch', ('D', 1), ('C', 2))]
        neighbor, _, _ = self.explain('branch', required=neighbor_links)
        self.assertTrue(self.supported(passing, 'local_passing'))
        self.assertFalse(self.supported(passing, 'local_neighbor'))
        self.assertTrue(self.supported(neighbor, 'local_neighbor'))
        self.assertFalse(self.supported(neighbor, 'local_passing'))

    def test_split_triple_is_not_relabelled_as_descriptor_local(self):
        result, comparison, _ = self.explain('split_triple')
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertEqual(self.credit(result), 0)
        self.assert_account(result, comparison)

    def test_three_native_slots_attach_local_explanation_without_old_pair_ids(self):
        result, comparison, _ = self.explain('three_slots')
        self.assertEqual(len(comparison['paths'][0]['partition']), 3)
        self.assertEqual(self.credit(result), Fraction(1, 2))
        self.assertTrue(self.supported(result, 'local_passing'))
        self.assert_account(result, comparison)

    def test_rational_thirds_are_not_rounded(self):
        result, comparison, _ = self.explain('rational')
        self.assertEqual(self.credit(result), Fraction(1, 3))
        self.assert_account(result, comparison)

    def test_member_competitor_has_no_borrowed_nonmember_credit(self):
        c = self.selector('member_competitor')
        g = self.selector('member_competitor', partitions=[(span(0, 4), ('G', Fraction()), members('G', 'B', 'D'))])
        result, comparison, _ = self.explain('member_competitor', selectors=[c, g])
        self.assertEqual(common.f(result['paths'][0]['account']['conditional_explanation_note_time_quarters']), 1)
        self.assertEqual(common.f(result['paths'][1]['account']['conditional_explanation_note_time_quarters']), 0)
        self.assert_account(result, comparison)

    def test_octave_neighbor_is_not_same_pitch_identity(self):
        result, _, _ = self.explain('octave_neighbor')
        self.assertFalse(self.supported(result, 'local_neighbor'))
        self.assertEqual(self.credit(result), 0)

    def test_local_leap_does_not_get_ordinary_passing_credit(self):
        result, _, _ = self.explain('leap_local')
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertEqual(self.credit(result), 0)

    def test_unknown_key_preserves_conditional_local_geometry(self):
        result, comparison, _ = self.explain(selectors=[self.selector(unknown=True)])
        self.assertEqual(self.credit(result), 1)
        self.assert_account(result, comparison)

    def test_physically_held_suspension_credits_only_right_nonmember_clip(self):
        result, comparison, _ = self.explain('suspension')
        supported = self.supported(result, 'boundary_suspension')
        self.assertTrue(supported)
        self.assertEqual(self.credit(result), 1)
        self.assertTrue(all(common.f(clip['span']['start']) >= 2 for c in supported for clip in c['clips']))
        self.assert_account(result, comparison)

    def test_tied_continuation_is_intrinsic_carry_not_fresh_attack(self):
        result, comparison, _ = self.explain('suspension_tie')
        sound = self.sound('suspension_tie', 'F', 0)
        self.assertEqual(len(sound['source_note_refs']), 2)
        self.assertEqual(len([s for s in self.case('suspension_tie')[0][1]['sound_facts']
                              if s['pitch']['step'] == 'F' and s['pitch']['octave'] == 4]), 1)
        self.assertEqual(self.credit(result), 1)
        self.assertTrue(self.supported(result, 'boundary_suspension'))
        self.assert_account(result, comparison)

    def test_held_suspension_still_needs_actual_resolution_link(self):
        result, _, _ = self.explain('suspension', control=True)
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 0)

    def test_reattack_suspension_needs_entire_same_bundle_chain(self):
        result, comparison, _ = self.explain('suspension_reattack')
        self.assertEqual(self.credit(result), 1)
        self.assertTrue(self.supported(result, 'boundary_suspension'))
        self.assert_account(result, comparison)
        partial, _, _ = self.explain('suspension_reattack', required=self.links('suspension_reattack')[1:])
        self.assertEqual(self.credit(partial), 0)

    def test_held_anticipation_can_be_explained_under_no_link_control(self):
        result, comparison, _ = self.explain('anticipation', control=True)
        self.assertTrue(self.supported(result, 'boundary_anticipation'))
        self.assertEqual(self.credit(result), 2)
        self.assertTrue(all(common.f(clip['span']['end']) <= 2
                            for c in self.supported(result, 'boundary_anticipation') for clip in c['clips']))
        self.assert_account(result, comparison)

    def test_anticipation_tie_does_not_require_self_link(self):
        result, comparison, bundle = self.explain('anticipation_tie', control=True)
        self.assertEqual(bundle['materialized_witness_links'], [])
        self.assertEqual(self.credit(result), 2)
        self.assert_account(result, comparison)

    def test_reattack_anticipation_needs_actual_link(self):
        result, comparison, _ = self.explain('anticipation_reattack')
        self.assertEqual(self.credit(result), 2)
        self.assertTrue(self.supported(result, 'boundary_anticipation'))
        self.assert_account(result, comparison)
        control, _, _ = self.explain('anticipation_reattack', control=True)
        self.assertEqual(self.credit(control), 0)

    def test_octave_reattack_not_intrinsic_anticipation(self):
        result, _, bundle = self.explain('anticipation_octave')
        self.assertTrue(bundle['materialized_witness_links'])
        self.assertFalse(self.supported(result, 'boundary_anticipation'))
        self.assertEqual(self.credit(result), 0)

    def test_enharmonic_reattack_not_identical_written_register(self):
        name = 'anticipation_enharmonic'
        # D and C-double-sharp share MIDI but no exact D-minor spelling
        # alternative is supplied in this mixed-spelling window. Preserve the
        # genuine unresolved right origin rather than inventing a D-minor one.
        selector = self.selector(name, partitions=[(span(0, 2), ('C', Fraction()), members('C', 'E', 'G')),
                                                   (span(2, 4), None, None)])
        required = [[self.sound(name, 'D', 0)['sound_ref'], self.sound(name, 'C', 2, alter=2)['sound_ref']]]
        result, comparison, _ = self.explain(name, selectors=[selector], required=required)
        self.assertFalse(self.supported(result, 'boundary_anticipation'))
        self.assertTrue(all(c['prerequisites']['actual_boundary_carry'] is False
                            for c in self.clauses(result, 'boundary_anticipation')
                            if c['sound_refs'][0] == required[0][0]))
        self.assert_account(result, comparison)

    def test_common_member_is_not_extra_boundary_nonmember_credit(self):
        result, comparison, _ = self.explain('common_member', control=True)
        self.assertEqual(self.credit(result), 0)
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertFalse(self.supported(result, 'boundary_anticipation'))
        self.assert_account(result, comparison)

    def test_suspension_upward_first_change_not_ordinary_resolution(self):
        result, _, _ = self.explain('suspension_up')
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 0)

    def test_suspension_leap_not_ordinary_step(self):
        result, _, _ = self.explain('suspension_leap')
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 0)

    def test_first_adverse_change_not_skipped_to_later_good_suspension_endpoint(self):
        result, _, _ = self.explain('suspension_first_adverse')
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 0)

    def test_terminal_carry_not_resolution_or_cadence(self):
        result, _, _ = self.explain('suspension_terminal', control=True)
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 0)

    def test_rest_gap_is_not_fabricated_carry_or_resolution(self):
        result, _, _ = self.explain('gap', control=True)
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 0)

    def test_multicut_held_context_is_withheld_not_partial_positive_clip(self):
        result, comparison, _ = self.explain('suspension_multicut')
        self.assertEqual(len(comparison['paths'][0]['partition']), 3)
        self.assertFalse(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 0)
        self.assert_account(result, comparison)

    def test_ordinary_leading_and_seventh_roles_are_separate_from_boundary_suspension(self):
        result, comparison, _ = self.explain('ordinary')
        self.assertTrue(self.supported(result, 'delayed_ordinary_leading_tone'))
        self.assertTrue(self.supported(result, 'delayed_ordinary_seventh'))
        self.assertTrue(self.supported(result, 'boundary_suspension'))
        self.assertEqual(self.credit(result), 2)
        self.assert_account(result, comparison)

    def test_ordinary_same_pitch_reattack_chain_requires_all_actual_edges(self):
        result, comparison, _ = self.explain('ordinary_reattack')
        self.assertEqual(self.credit(result), 2)
        self.assertTrue(self.supported(result, 'delayed_ordinary_leading_tone'))
        self.assert_account(result, comparison)
        control, _, _ = self.explain('ordinary_reattack', control=True)
        self.assertEqual(self.credit(control), 0)

    def test_ordinary_first_adverse_change_not_skipped_to_good_later_root(self):
        result, _, _ = self.explain('ordinary_first_adverse')
        self.assertFalse(self.supported(result, 'delayed_ordinary_leading_tone'))

    def test_unknown_key_preserves_motion_without_function_confirmation(self):
        result, comparison, _ = self.explain('ordinary', selectors=[self.selector('ordinary', unknown=True)])
        self.assertTrue(self.supported(result, 'delayed_ordinary_leading_tone'))
        self.assertEqual(self.credit(result), 2)
        self.assertIsNone(comparison['paths'][0]['transition_contexts'][0]['function_shape']['key_projection']['target_coordinate'])
        self.assert_account(result, comparison)

    def test_undeclared_transition_cannot_assign_ordinary_obligations(self):
        result, _, _ = self.explain('ordinary', selectors=[self.selector('ordinary', assumptions=[None])])
        self.assertFalse(self.supported(result, 'delayed_ordinary_leading_tone'))
        self.assertFalse(self.supported(result, 'delayed_ordinary_seventh'))
        self.assertEqual(self.credit(result), 1)

    def test_wrong_family_cannot_promote_physical_route_to_ordinary_credit(self):
        result, _, _ = self.explain('ordinary', selectors=[self.selector('ordinary', assumptions=[{'family': 'V', 'quality': 'M'}])])
        self.assertFalse(self.supported(result, 'delayed_ordinary_leading_tone'))
        self.assertFalse(self.supported(result, 'delayed_ordinary_seventh'))
        self.assertEqual(self.credit(result), 1)
        self.assertIs(result['paths'][0]['ordinary_templates'][0]['satisfied'], False)

    def test_genuine_unresolved_critical_identity_is_unknown_not_known_no_route(self):
        selector = self.selector('ordinary', partitions=[(span(0, 2), None, None),
                                                         (span(2, 4), ('C', Fraction()), members('C', 'E', 'G'))])
        result, comparison, _ = self.explain('ordinary', selectors=[selector])
        context = comparison['paths'][0]['transition_contexts'][0]
        self.assertIsNone(context['function_shape']['leading_tone'])
        self.assertEqual(context['ordinary_strategy']['role_assessments'][0]['occurrences'], [])
        template = result['paths'][0]['ordinary_templates'][0]
        self.assertEqual(template['role_truths'], [None])
        self.assertIsNone(template['satisfied'])
        self.assertFalse(self.supported(result, 'delayed_ordinary_leading_tone'))
        self.assertEqual(self.credit(result), 0)
        self.assert_account(result, comparison)
        # Contrast a genuinely known identity with a complete no-link witness.
        # No linked first change is then known failure, not unknown identity.
        control, _, _ = self.explain('ordinary', control=True)
        template = control['paths'][0]['ordinary_templates'][0]
        self.assertEqual(template['role_truths'], [False, False])
        self.assertIs(template['satisfied'], False)

    def test_doubling_existential_success_does_not_resolve_bad_extra_occurrence(self):
        result, comparison, _ = self.explain('ordinary_doubled')
        extra = self.sound('ordinary_doubled', 'B', 0, octave=3)['sound_ref']
        credited = {c['sound_ref'] for p in result['paths'] for c in p['account']['explained_intervals_by_sound']}
        self.assertNotIn(extra, credited)
        self.assertTrue(self.supported(result, 'delayed_ordinary_leading_tone'))
        self.assert_account(result, comparison)

    def test_combined_local_boundary_ordinary_credits_are_interval_union_not_sum(self):
        result, comparison, _ = self.explain('combined')
        self.assertTrue(self.supported(result, 'local_passing'))
        self.assertTrue(self.supported(result, 'boundary_suspension'))
        self.assertTrue(self.supported(result, 'delayed_ordinary_seventh'))
        self.assertEqual(self.credit(result), Fraction(5, 2))
        self.assert_account(result, comparison)

    def test_source_attack_unknown_cannot_yield_positive_explanation(self):
        result, _, _ = self.explain('bad_attack', control=True)
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertTrue(all(p['account']['conditional_explanation_note_time_quarters'] in (None, common.q(0))
                            for p in result['paths']))

    def test_microtone_retained_without_ordinary_positive_role(self):
        result, _, _ = self.explain('microtone', control=True)
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertTrue(all(p['account']['conditional_explanation_note_time_quarters'] in (None, common.q(0))
                            for p in result['paths']))

    def test_grace_point_not_positive_time_ordinary_role(self):
        result, comparison, _ = self.explain('grace', control=True)
        self.assertFalse(self.supported(result, 'local_passing'))
        self.assertTrue(all(p['account']['conditional_explanation_note_time_quarters'] in (None, common.q(0))
                            for p in result['paths']))
        self.assert_account(result, comparison)

    def test_single_full_hold_known_no_boundary_role_and_zero_credit(self):
        result, comparison, _ = self.explain('single', control=True)
        self.assertEqual(self.credit(result), 0)
        self.assertFalse(self.clauses(result, 'boundary_suspension'))
        self.assertFalse(self.clauses(result, 'boundary_anticipation'))
        self.assert_account(result, comparison)

    def test_whole_budget_hold_has_no_partial_path_or_account_prefix(self):
        result, _, _ = self.explain('combined', budget=0)
        self.assertEqual(result['status'], 'whole_explanation_hold')
        self.assertEqual(result['paths'], [])

    def test_native_whole_hold_preserves_submitted_denominator_and_exact_request(self):
        session, comparison, _ = self.comparison(max_hypotheses=0)
        self.assertEqual(comparison['status'], 'whole_comparison_hold')
        self.assertEqual(comparison['paths'], [])
        self.assertEqual(comparison['summary']['planned_selectors'], 1)
        result = roles.explain_prepared(roles.prepare_explanations(session, comparison))
        self.assertEqual(result['status'], 'whole_explanation_hold')
        self.assertEqual(result['paths'], [])
        self.assertIn('native_comparison_unavailable', result['reasons'])
        self.assertEqual(result['summary']['planned_paths'], 1)
        self.assertEqual(result['summary']['native_computed_paths'], 0)
        self.assertEqual(result['summary']['computed_paths'], 0)
        self.assertEqual(result['summary']['withheld_paths'], 1)
        self.assertEqual(result['native_request'], {key: comparison[key] for key in
                         ('selectors', 'resource_limits', 'status', 'reasons', 'summary', 'query_plan')})
        # A withheld parent body still has the exact one-selector request, so
        # the conservative child request bound is known and positive, not zero.
        self.assertGreater(result['query_plan']['planned_query_work'], 0)
        self.assertGreater(result['query_plan']['clause_upper_bound'], 0)

    def test_captured_native_state_identity_survives_even_reauthenticated_clone_attempt(self):
        session, comparison, _ = self.comparison()
        handle = roles.prepare_explanations(session, comparison)
        original = native._SESSIONS[session]
        clone = replace(original)
        # White-box adversarial registry replacement only; the fixture,
        # original comparison, bundle and child handle are authentic. Even an
        # equivalent reauthenticated parent clone cannot replace the captured
        # exact parent state that granted this child's authority.
        object.__setattr__(clone, 'authentication', native._auth(session, clone))
        try:
            native._SESSIONS[session] = clone
            self.assertIs(native._issued(session), clone)
            with self.assertRaisesRegex(ValueError, 'parent_state_identity_changed'):
                roles.explain_prepared(handle)
        finally:
            native._SESSIONS[session] = original
        self.assertIs(native._issued(session), original)
        self.assertEqual(roles.explain_prepared(handle)['status'],
                         'computed_native_role_explanations_not_selected')

    def test_pure_planner_long_tie_source_closure_is_charged_per_emitted_clause(self):
        # Pure arithmetic helper test, not an authenticated public music claim.
        scope = deepcopy(self.case()[0][1])
        selectors = [{'origin_ids': ['one', 'two', 'three']}]
        base = roles._plan(scope, [], selectors)
        scope['sound_facts'][0]['source_note_refs'] = ['pure-note-' + str(i) for i in range(101)]
        plan = roles._plan(scope, [], selectors)
        n = len(scope['sound_facts'])
        refs = sum(len(s['source_note_refs']) for s in scope['sound_facts'])
        max_refs = max(len(s['source_note_refs']) for s in scope['sound_facts'])
        local, cut_clauses = 3 * n, 2 * 2 * n
        self.assertEqual(plan['source_closure_items'], n + refs)
        self.assertEqual(plan['source_reference_visit_upper_bound'],
                         local * 3 * max_refs + (cut_clauses + cut_clauses) * refs)
        self.assertGreater(plan['source_reference_visit_upper_bound'], base['source_reference_visit_upper_bound'])
        self.assertGreater(plan['planned_query_work'], base['planned_query_work'])

    def test_empty_genuine_native_request_is_known_zero_not_unassessed_or_held(self):
        session, comparison, _ = self.comparison(selectors=[], query_work_budget=0)
        self.assertEqual(comparison['paths'], [])
        self.assertEqual(comparison['summary']['planned_selectors'], 0)
        result = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=0)
        self.assertEqual(result['status'], 'computed_native_role_explanations_not_selected')
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['paths'], [])
        for field in ('planned_paths', 'native_computed_paths', 'computed_paths', 'withheld_paths'):
            self.assertEqual(result['summary'][field], 0)
        for field in ('planned_query_work', 'source_closure_items', 'clause_upper_bound',
                      'source_reference_visit_upper_bound'):
            self.assertEqual(result['query_plan'][field], 0)

    def test_invalid_query_budgets_rejected_before_handle_reads(self):
        for value in (-1, True, 1.5, None, '1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                roles.explain_prepared(None, query_work_budget=value)

    def test_plain_dict_none_and_unissued_object_not_handle_authority(self):
        for handle in ({}, None, object()):
            with self.subTest(kind=type(handle).__name__), self.assertRaises(ValueError):
                roles.explain_prepared(handle)

    def test_forged_native_session_cannot_prepare_explanations(self):
        _, comparison, _ = self.comparison()
        with self.assertRaises(ValueError):
            roles.prepare_explanations(object(), comparison)

    def test_resealed_modified_comparison_not_replay_authority(self):
        session, comparison, _ = self.comparison()
        changed = deepcopy(comparison)
        changed['paths'][0]['profiles'][0]['rows'][0]['state'] = 'spelling_unresolved'
        changed = reseal(changed, native.COMPARISON_PREFIX)
        with self.assertRaises(ValueError):
            roles.prepare_explanations(session, changed)
        compare = native.compare_prepared
        def mutation_after_fresh_replay(*args, **kwargs):
            fresh = compare(*args, **kwargs)
            comparison['selectors'].clear()
            return fresh
        with patch.object(native, 'compare_prepared', mutation_after_fresh_replay), self.assertRaises(ValueError):
            roles.prepare_explanations(session, comparison)

    def test_foreign_registered_comparison_cannot_cross_owned_session(self):
        _, comparison, _ = self.comparison('neighbor')
        with self.assertRaises(ValueError):
            roles.prepare_explanations(self.session('passing'), comparison)

    def test_prepared_snapshot_survives_detached_caller_comparison_mutation(self):
        session, comparison, _ = self.comparison()
        handle = roles.prepare_explanations(session, comparison)
        expected = roles.explain_prepared(handle)
        comparison['paths'].clear()
        comparison['selectors'].clear()
        self.assertEqual(roles.explain_prepared(handle), expected)

    def test_returned_nested_mutation_does_not_change_owned_result(self):
        session, comparison, _ = self.comparison()
        handle = roles.prepare_explanations(session, comparison)
        original = roles.explain_prepared(handle)
        changed = roles.explain_prepared(handle)
        changed['paths'][0]['clauses'].clear()
        changed['paths'][0]['account']['note_time_quarters'].clear()
        self.assertEqual(roles.explain_prepared(handle), original)
        self.assertIs(roles.validate_explanation_prepared(handle, original), True)
        changed = reseal(changed, roles.PREFIX)
        with self.assertRaises(ValueError):
            roles.validate_explanation_prepared(handle, changed)

    def test_current_source_contract_change_invalidates_prepared_handle(self):
        session, comparison, _ = self.comparison()
        handle = roles.prepare_explanations(session, comparison)
        original = Path.read_bytes
        target = Path(roles.__file__)
        def changed_bytes(path):
            value = original(path)
            return value + b'\n' if path == target else value
        with patch.object(Path, 'read_bytes', changed_bytes), self.assertRaises(ValueError):
            roles.explain_prepared(handle)

    def test_no_final_verdict_rank_confidence_or_nct_promotion(self):
        result, comparison, _ = self.explain('combined')
        for key in ('selected', 'rank', 'confidence'):
            self.assertIsNone(result[key])
        for name in ('nct_confirmed', 'harmony_confirmed', 'cadence_confirmed', 'training_eligible', 'generation_ready'):
            self.assertIs(result['flags'][name], False)
        for clause in self.clauses(result):
            self.assertIn(clause['status'], ('supported', 'failed', 'unassessed'))
            self.assertIs(type(clause['qualified']), bool)
            if clause['status'] == 'supported':
                self.assertIs(clause['satisfied'], True)
                self.assertIs(clause['qualified'], True)
        self.assertIsNone(comparison['paths'][0]['whole_path_account']['NCT_credited_note_time_quarters'])


if __name__ == '__main__':
    unittest.main()
