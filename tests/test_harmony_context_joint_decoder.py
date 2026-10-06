from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_context_joint_decoder as joint
from musicanote_harness import harmony_context_competition_v2 as context
from musicanote_harness import harmony_full_score as old
from test_harmony_bounded_recovery import fixture
from test_harmony_exact_frontier import problem
from test_harmony_functional_scoring import C, G, G7
from test_harmony_context_competition import FM


def toy(notes=None, end=4, signatures=(C, G, FM), cap=4):
    ir = fixture(notes or [('E4', 0, 1, 'lead'), ('F4', 1, 2, 'lead'),
                          ('E4', 2, 3, 'lead'), ('D4', 3, end, 'lead'),
                          ('C3', 0, end, 'bass')], end=end)
    graph, ev = problem(ir, end=end); template = graph.edges[0]; edges = []
    for i, a in enumerate(graph.points):
        for j, b in enumerate(graph.points[i+1:], i+1):
            for k, sig in enumerate(signatures):
                edges.append(replace(template, group_id=f'e{i}_{j}_{k}', start_index=i, end_index=j,
                    start=a, end=b, signature=sig, features={'blocker_exposure': F()}, blockers=(),
                    attack_spellings=frozenset(e.pitch for e in ev.source.events if e.start == a),
                    source_event_ids=tuple(e.event_id for e in ev.source.events if e.start < b and a < e.end)))
    return replace(graph, edges=tuple(edges), max_segments=cap), ev, ir


def paths(graph):
    result = []
    def visit(i, ids):
        if i == len(graph.points)-1: result.append(ids); return
        if len(ids) >= graph.max_segments: return
        for e in graph.edges:
            if e.start_index == i: visit(e.end_index, ids+(e.group_id,))
    visit(0, ()); return result


def scorer(graph, ev, weights=None, extra=None, **kwargs):
    return joint.Scorer(old.Scorer(graph, ev, weights or old.initial_weights(old.fresh.timing.ZERO)),
                        joint.ZERO if extra is None else extra, **kwargs)


class DelayedJointTests(unittest.TestCase):
    def check_exhaustive(self, graph, ev, extra, weights=None):
        sc = scorer(graph, ev, weights, extra); candidates = paths(graph)
        result = sc.decode(force_delayed=True)
        if not candidates:
            self.assertIsNone(result['selected']); return result
        expected = min((sc.score_path(ids), ids) for ids in candidates)
        self.assertTrue(result['exact_optimum_under_declared_score'])
        self.assertEqual((joint.f(result['selected']['score_cost']), old.fresh.path_ids(result['selected'])), expected)
        return result

    def test_nonzero_signed_context_weights_match_every_tiny_path(self):
        graph, ev, _ = toy(cap=3); rng = random.Random(7901)
        for _ in range(8):
            extra = {k: rng.choice((F(-2), F(-1, 3), F(), F(1, 7), F(2))) for k in joint.FEATURES}
            sub = replace(graph, edges=tuple(e for e in graph.edges if rng.random() < .72))
            self.check_exhaustive(sub, ev, extra)

    def test_old_weights_and_new_context_both_varied(self):
        graph, ev, _ = toy(cap=3); rng = random.Random(7902)
        for _ in range(4):
            weights = {k: rng.choice(old.bounds(k)) for k in old.FEATURES}
            extra = {k: rng.choice((F(-1), F(), F(1))) for k in joint.FEATURES}
            self.check_exhaustive(graph, ev, extra, weights)

    def test_zero_delegate_and_forced_delayed_reproduce_sealed_choice(self):
        graph, ev, _ = toy(cap=3); sc = scorer(graph, ev)
        sealed = sc.original.decode(); delegated = sc.decode(); forced = sc.decode(force_delayed=True)
        for r in (delegated, forced):
            self.assertEqual(old.fresh.path_ids(r['selected']), old.fresh.path_ids(sealed['selected']))
            self.assertEqual(r['selected']['score_cost'], sealed['selected']['score_cost'])
        self.assertEqual(delegated['context_joint_contract']['backend'], 'legacy_batched_zero_context')

    def test_local_transition_values_equal_full_v2_with_global_normalizers(self):
        graph, ev, _ = toy(); sc = scorer(graph, ev)
        for ids in paths(graph):
            expected = context.observe_path(graph, ev, ids, context=sc.context)
            actual = sc.path_receipt(ids)['context']
            for a, b in zip(actual['transitions'], expected['transitions']):
                self.assertEqual(a['features'], b['features'])
                self.assertEqual(a['availability'], b['availability'])
                self.assertEqual(a['explained_event_ids'], b['explained_event_ids'])
            self.assertEqual(actual['observed_feature_sums'], expected['observed_feature_sums'])
            self.assertEqual(actual['availability'], expected['availability'])

    def test_same_signature_raw_splits_do_not_change_new_score(self):
        graph, ev, _ = toy(); sc = scorer(graph, ev, extra={k: F(1, 3) for k in joint.FEATURES})
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        a = (by[F(0), F(2), C], by[F(2), F(4), FM])
        b = (by[F(0), F(1), C], by[F(1), F(2), C], by[F(2), F(3), FM], by[F(3), F(4), FM])
        self.assertEqual(sc.path_receipt(a)['context'], sc.path_receipt(b)['context'])
        self.assertEqual(sc.score_path(a), sc.score_path(b))

    def test_final_two_transitions_and_one_run_flush(self):
        graph, ev, _ = toy(); by = {(e.start, e.end, e.signature): e for e in graph.edges}
        for specs in (((0, 4, C),), ((0, 1, C), (1, 4, FM)),
                      ((0, 1, C), (1, 2, FM), (2, 4, C)),
                      ((0, 1, C), (1, 2, FM), (2, 3, C), (3, 4, G))):
            chain = replace(graph, edges=tuple(by[F(a), F(b), sig] for a, b, sig in specs))
            r = self.check_exhaustive(chain, ev, {k: F(1) for k in joint.FEATURES})
            self.assertEqual(len(r['selected']['context_score']['context']['transitions']), len(specs)-1)

    def test_competing_four_to_six_run_histories_match_exhaustive(self):
        notes = [(pitch, i, i+1, 'lead') for i, pitch in enumerate(('E4', 'F4', 'E4', 'D4', 'E4', 'F4'))]
        graph, ev, _ = toy(notes+[('C3', 0, 6, 'bass')], end=6, signatures=(C, FM), cap=6)
        graph = replace(graph, edges=tuple(e for e in graph.edges if e.end-e.start <= 2))
        for sign in (F(-1), F(1)):
            self.check_exhaustive(graph, ev, {k: sign*(F(1, 3) if i % 2 else F(1, 7))
                                            for i, k in enumerate(joint.FEATURES)})

    def test_coarse_grid_fractional_clocks_do_not_insert_candidate_points(self):
        notes = [('E4', 0, F(1, 3), 'lead'), ('F4', F(1, 3), F(2, 3), 'lead'),
                 ('E4', F(2, 3), 1, 'lead'), ('G4', 1, 4, 'lead'), ('C3', 0, 4, 'bass')]
        graph, ev, _ = toy(notes, cap=3)
        kept = (F(0), F(1), F(4))
        graph = replace(graph, points=kept, edges=tuple(replace(e, start_index=kept.index(e.start), end_index=kept.index(e.end))
                         for e in graph.edges if e.start in kept and e.end in kept))
        self.check_exhaustive(graph, ev, {k: F(1, 3) for k in joint.FEATURES})
        self.assertEqual(graph.points, kept)

    def test_longer_next_complete_run_changes_pending_geometry(self):
        graph, ev, _ = toy(); sc = scorer(graph, ev)
        short = ((F(0), F(1), C), (F(1), F(2), FM), (F(2), F(5, 2), G))
        long = short[:2]+((F(2), F(3), G),)
        a, b = sc.transition_profile(short, 1), sc.transition_profile(long, 1)
        self.assertFalse(a['explained_event_ids']); self.assertTrue(b['explained_event_ids'])
        self.assertNotEqual(a['features'], b['features'])

    def test_previous_history_must_not_collapse_to_current_run_only(self):
        h1 = ((0, C), (1, FM), (2, C)); h2 = ((0, G), (1, FM), (2, C))
        current = {(3, h1): (F(2), ('a', 'b', 'c')), (3, h2): (F(1), ('d', 'b', 'c')),
                   (4, h1): (F(3), ('x', 'a', 'b', 'c'))}
        kept, removed = joint.history_pareto(current)
        self.assertIn((3, h1), kept); self.assertIn((3, h2), kept); self.assertEqual(removed, 1)

    def test_equal_score_lexical_tie_and_duplicate_raw_edge(self):
        graph, ev, _ = toy(cap=2)
        duplicate = replace(graph.edges[0], group_id='000-duplicate')
        graph = replace(graph, edges=(duplicate,)+graph.edges)
        weights = old.initial_weights(old.fresh.timing.ZERO)
        for k in old.TRAINABLE: weights[k] = max(old.bounds(k)[0], F())
        self.check_exhaustive(graph, ev, joint.ZERO, weights)

    def test_unknown_terms_remain_null_not_partial_sums_in_score(self):
        graph, ev, _ = toy(); ev.rows[1]['identity'] = None; ev.rows[1]['clock_valid'] = False
        sc = scorer(graph, ev, extra={k: F(1) for k in joint.FEATURES})
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        ids = (by[F(0), F(1), C], by[F(1), F(2), FM], by[F(2), F(4), C])
        r = sc.path_receipt(ids); c = r['context']
        self.assertIsNone(c['features']['hold_explained_step_exposure'])
        self.assertFalse(c['availability']['hold_explained_step_exposure'])
        self.assertEqual(c['term_costs']['hold_explained_step_exposure'], joint.q(0))
        self.assertEqual(sum((joint.f(v) for v in c['term_costs'].values()), F()), joint.f(r['context_cost']))
        self.check_exhaustive(graph, ev, sc.weights)

    def test_meter_change_and_grace_history_barriers_preserved(self):
        graph, ev, _ = toy(); ev.source.measures += ((F(2), (6, 8), None),)
        ev.source._measure_times += (F(2),); ev.source._metric_cache.clear()
        self.check_exhaustive(graph, ev, {k: F(1, 3) for k in joint.FEATURES})
        sc = scorer(graph, ev, context_barriers=(F(3, 2),))
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        r = sc.path_receipt((by[F(0), F(1), C], by[F(1), F(2), FM], by[F(2), F(4), C]))
        self.assertFalse(r['context']['transitions'][0]['conditional_figures'])

    def test_no_complete_path_and_raw_cap_are_not_relaxed(self):
        graph, ev, _ = toy(); graph = replace(graph, edges=tuple(e for e in graph.edges if e.end-e.start == 1), max_segments=3)
        r = scorer(graph, ev).decode(force_delayed=True)
        self.assertEqual(r['status'], 'no_complete_path_under_segment_cap'); self.assertIsNone(r['selected'])
        self.assertTrue(r['exact_optimum_under_declared_score'])

    def test_budget_abstention_never_returns_partial_winner(self):
        graph, ev, _ = toy()
        r = scorer(graph, ev).decode(force_delayed=True, transition_budget=1)
        self.assertEqual(r['status'], 'transition_budget_abstention'); self.assertIsNone(r['selected'])
        self.assertFalse(r['exact_optimum_under_declared_score'])

    def test_invalid_weights_types_context_and_paths_rejected(self):
        graph, ev, _ = toy(); sc = scorer(graph, ev)
        for values in ({}, joint.ZERO | {joint.FEATURES[0]: .1}, joint.ZERO | {joint.FEATURES[0]: F(3)}):
            with self.assertRaises(ValueError): scorer(graph, ev, extra=values)
        for value in (0, True, 1.5):
            with self.assertRaises(ValueError): sc.decode(force_delayed=True, transition_budget=value)
        with self.assertRaises(ValueError): sc.score_path(('missing',))
        _, other, _ = toy()
        with self.assertRaises(ValueError): scorer(graph, ev, context=context.Context(other))

    def test_original_source_candidates_ids_and_module_globals_unchanged(self):
        graph, ev, ir = toy(cap=3); before = deepcopy((ir, graph, old.BASE_WEIGHTS, old.PAIR_WEIGHTS))
        r = scorer(graph, ev, extra={k: F(1, 7) for k in joint.FEATURES}).decode()
        self.assertEqual((ir, graph, old.BASE_WEIGHTS, old.PAIR_WEIGHTS), before)
        self.assertFalse(r['selected']['source_labels_used_for_selection'])
        self.assertFalse(r['context_joint_contract']['new_held_candidate_inserted'])
        self.assertTrue(set(old.fresh.path_ids(r['selected'])) <= {e.group_id for e in graph.edges})


if __name__ == '__main__': unittest.main()
