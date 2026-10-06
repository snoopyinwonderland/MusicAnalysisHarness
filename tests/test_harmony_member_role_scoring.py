from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_member_role_scoring as role
from test_harmony_context_joint_decoder import toy, paths, old, joint, C, G, FM
from test_harmony_bounded_recovery import add_grace

AM = (('A', 0), tuple(sorted((('A', 0), ('C', 1), ('E', 0)))))
EM = (('E', 0), tuple(sorted((('E', 0), ('G', 0), ('B', 0)))))
BM = (('B', 0), tuple(sorted((('B', 0), ('D', 0), ('F', 1)))))
FSM = (('F', 1), tuple(sorted((('F', 1), ('A', 0), ('C', 1)))))


def scorer(graph, ev, weights=None, context=None, **kw):
    return role.Scorer(old.Scorer(graph, ev, old.initial_weights(old.fresh.timing.ZERO)),
        joint.ZERO if context is None else context, role.ZERO if weights is None else weights, **kw)


def by_path(graph, runs):
    by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
    return tuple(by[F(a), F(b), sig] for a, b, sig in runs)


class MemberRoleTests(unittest.TestCase):
    def test_surface_root_is_not_forced_to_analysis_root(self):
        functional = FSM[0], BM[1]
        literal, thirds, extensions, basis = role.surface_roles(functional)
        self.assertEqual(literal, ('B', 0)); self.assertIn(('D', 0), thirds)
        self.assertIn(('A', 0), extensions); self.assertIn('distinct', basis)
        self.assertIsNone(role.surface_roles((None, BM[1])))
        self.assertEqual(role.surface_roles(G)[0], ('G', 0))

    def test_extension_with_distributed_root_third_not_a_vertical_gate(self):
        notes = [('A3', 0, F(1, 2), 'bass'), ('C#4', F(1, 2), 1, 'inner'),
                 ('E5', 0, 1, 'lead'), ('G5', 1, F(7, 4), 'lead'), ('E5', F(7, 4), 2, 'lead')]
        graph, ev, _ = toy(notes, end=2, signatures=(AM, EM), cap=3); sc = scorer(graph, ev)
        runs = ((F(0), F(1), AM), (F(1), F(2), EM))
        quick = sc.role_index.observe(runs, 1); detailed = sc.role_index.observe(runs, 1, detailed=True)
        self.assertGreater(quick['features'][role.FEATURES[0]], 0)
        self.assertEqual(quick['features'], detailed['features'])
        self.assertEqual(quick['features'][role.FEATURES[1]], 0)
        self.assertTrue(detailed['surface_root_and_third_observed_in_left_union'])
        self.assertFalse(detailed['left_union_is_vertical_stack'])
        self.assertFalse(detailed['confirmed_extension'])
        for e in detailed['support_source_events']:
            self.assertLess(role.f(e['in_run_span']['start']), role.f(e['in_run_span']['end']))

    def test_missing_third_does_not_invent_supported_extension(self):
        notes = [('A3', 0, 1, 'bass'), ('E5', 0, 1, 'lead'), ('G5', 1, 2, 'lead')]
        graph, ev, _ = toy(notes, end=2, signatures=(AM, EM)); sc = scorer(graph, ev)
        p = sc.role_index.observe(((F(0), F(1), AM), (F(1), F(2), EM)), 1, detailed=True)
        self.assertEqual(p['features'][role.FEATURES[0]], 0)
        self.assertFalse(p['surface_root_and_third_observed_in_left_union'])
        self.assertGreater(p['features'][role.FEATURES[1]], 0)

    def test_durable_nonextension_and_doublings_use_union_time(self):
        notes = [('B3', 0, 1, 'bass'), ('D4', 0, 1, 'inner'), ('F#5', 0, 1, 'lead'),
                 ('F#3', 1, 3, 'bass'), ('C#5', 1, 2, 'lead'), ('C#4', 1, 2, 'inner')]
        graph, ev, _ = toy(notes, end=3, signatures=(BM, FSM)); sc = scorer(graph, ev)
        p = sc.role_index.observe(((F(0), F(1), BM), (F(1), F(3), FSM)), 1)
        self.assertEqual(p['features'][role.FEATURES[0]], 0)
        self.assertEqual(p['features'][role.FEATURES[1]], F(1, 3))

    def test_full_sustain_clipping_is_not_a_new_attack(self):
        notes = [('C3', 0, 3, 'bass'), ('E4', 0, 1, 'lead'), ('A4', F(1, 2), 3, 'inner')]
        graph, ev, _ = toy(notes, end=3, signatures=(C, FM)); sc = scorer(graph, ev)
        p = sc.role_index.observe(((F(0), F(1), C), (F(1), F(3), FM)), 1)
        self.assertEqual(p['features'][role.FEATURES[1]], 0)

    def test_changing_meter_integrated_duration_and_unknown(self):
        notes = [('C3', 0, 1, 'bass'), ('E4', 0, 1, 'lead'), ('A4', 1, 2, 'lead')]
        graph, ev, _ = toy(notes, end=2, signatures=(C, FM)); ev.source.measures = ((F(0), (6, 8), None),)
        ev.source._measure_times = (F(0),); ev.source._metric_cache.clear()
        sc = scorer(graph, ev); runs = ((F(0), F(1), C), (F(1), F(2), FM))
        self.assertEqual(sc.role_index.observe(runs, 1)['features'][role.FEATURES[1]], 0)
        ev.source.measures = ((F(0), (None, 8), None),); ev.source._metric_cache.clear()
        sc = scorer(graph, ev)
        self.assertIsNone(sc.role_index.observe(runs, 1)['features'][role.FEATURES[1]])

    def test_unknown_pitch_voice_and_unsupported_shape_remain_null(self):
        graph, ev, _ = toy(); runs = ((F(0), F(1), C), (F(1), F(4), FM))
        for field, value in (('identity', None), ('clock_valid', False)):
            fresh = deepcopy(ev); fresh.rows[1][field] = value
            sc = scorer(graph, fresh); self.assertIsNone(sc.role_index.observe(runs, 1)['features'][role.FEATURES[0]])
        sc = scorer(graph, ev)
        unknown = ((F(0), F(1), (None, C[1])), runs[1])
        self.assertTrue(all(v is None for v in sc.role_index.observe(unknown, 1)['features'].values()))

    def test_source_ornament_geometry_not_reclassified_as_new_change(self):
        graph, ev, _ = toy(end=4); sc = scorer(graph, ev)
        runs = ((F(0), F(1), C), (F(1), F(2), FM), (F(2), F(4), C))
        p = sc.role_index.observe(runs, 1, detailed=True)
        self.assertTrue(p['conditional_explained_ids']); self.assertFalse(p['new_unexplained_exclusive_attacks'])
        self.assertEqual(p['features'][role.FEATURES[1]], 0)

    def test_every_tiny_path_and_signed_weights_match_exact_dp(self):
        graph, ev, _ = toy(end=3, cap=3, notes=[('C3', 0, 1, 'bass'), ('E4', 0, 1, 'inner'),
            ('G4', 0, 1, 'lead'), ('B-4', 1, 2, 'lead'), ('A4', 2, 3, 'lead')])
        rng = random.Random(8301)
        for _ in range(4):
            weights = {k: rng.choice((F(-1, 2), F(), F(1, 2))) for k in role.FEATURES}
            context = {k: rng.choice((F(-1, 3), F(), F(1, 3))) for k in joint.FEATURES}
            sc = scorer(graph, ev, weights, context)
            for ids in paths(graph):
                runs = joint.context_features.control.completed_runs(graph, ids)
                for i in range(1, len(runs)):
                    a, b = sc.role_index.observe(runs, i), sc.role_index.observe(runs, i, detailed=True)
                    for key in ('features', 'observed_feature_sums', 'availability'):
                        self.assertEqual(a[key], b[key])
            expected = min((sc.score_path(ids), ids) for ids in paths(graph))
            result = sc.decode(force_delayed=True)
            self.assertEqual((role.f(result['selected']['score_cost']), old.fresh.path_ids(result['selected'])), expected)

    def test_raw_partition_invariance_and_zero_control(self):
        graph, ev, _ = toy(); weights = {k: F(1, 3) for k in role.FEATURES}
        sc = scorer(graph, ev, weights)
        a = by_path(graph, ((0, 2, C), (2, 4, FM)))
        b = by_path(graph, ((0, 1, C), (1, 2, C), (2, 3, FM), (3, 4, FM)))
        self.assertEqual(sc.path_receipt(a)['member_role'], sc.path_receipt(b)['member_role'])
        self.assertEqual(sc.score_path(a), sc.score_path(b))
        z = scorer(graph, ev); baseline = role.parent.Scorer(z.original, joint.ZERO).decode()
        control = z.decode()
        self.assertEqual(control['selected']['score_cost'], baseline['selected']['score_cost'])
        self.assertEqual(old.fresh.path_ids(control['selected']), old.fresh.path_ids(baseline['selected']))

    def test_cap_budget_negative_weight_and_no_mutation(self):
        graph, ev, ir = toy(); before = deepcopy((graph, ir, old.BASE_WEIGHTS, old.PAIR_WEIGHTS))
        sc = scorer(graph, ev, {k: F(-1, 2) for k in role.FEATURES})
        self.assertIsNone(sc.decode(transition_budget=1)['selected'])
        self.assertEqual(before, (graph, ir, old.BASE_WEIGHTS, old.PAIR_WEIGHTS))
        for values in ({}, role.ZERO | {role.FEATURES[0]: 0.1}):
            with self.assertRaises(ValueError): role.coefficients(values)
        for intervals in ([(F(0), F(0))], [(F(2), F(1))]):
            with self.assertRaises(ValueError): role.union_width(intervals)

    def test_zero_duration_grace_cannot_request_positive_beat_extent(self):
        notes = [('C3', 0, 3, 'bass'), ('E4', 0, 1, 'lead'), ('A4', 2, 3, 'lead')]
        graph, ev, ir = toy(notes, end=3, signatures=(C, FM))
        n, sound = add_grace(ir, F(3, 2))
        base = next(e for e in ev.source.events if e.pitch == ('A', 0))
        # The full-source projection can retain grace even when the graph view
        # omitted it. Missing positive clock/voice evidence must stay unavailable.
        ev.source.events += (replace(base, event_id=sound['sounding_event_id'],
            start=F(3, 2), end=F(3, 2), source_note_ids=(n['note_id'],)),)
        before = deepcopy(ir)
        sc = scorer(graph, ev); runs = ((F(0), F(1), C), (F(1), F(3), FM))
        quick = sc.role_index.observe(runs, 1); detailed = sc.role_index.observe(runs, 1, detailed=True)
        for k in ('features', 'observed_feature_sums', 'availability'):
            self.assertEqual(quick[k], detailed[k])
        self.assertTrue(detailed['zero_duration_source_ids_retained_not_scored'])
        self.assertNotIn(sound['sounding_event_id'], [e['sounding_event_id'] for e in detailed['new_unexplained_exclusive_attacks']])
        self.assertNotIn((F(3, 2), F(3, 2)), sc.role_index.beats)
        self.assertEqual(before, ir)


if __name__ == '__main__': unittest.main()
