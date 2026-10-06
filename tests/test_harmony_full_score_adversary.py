from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_full_score_adversary as a
from musicanote_harness.harmony_common_benchmark import native_prediction
from musicanote_harness.harmony_margin_learning import training_loss, path_loss
from test_harmony_exact_frontier import problem
from test_harmony_bounded_recovery import fixture
from test_harmony_functional_scoring import C, G, G7, example, supply

s = a.s


def cells(graph, sig=C):
    return ({'start': graph.points[0], 'end': graph.points[-1], 'signature': sig},)


def loss_of(graph, ids, loss):
    return path_loss(graph, {'selected': {'segments': [{'semantic_group_ref': i} for i in ids]}}, loss)


def exhaustive(sc, loss):
    paths = []
    def visit(index, ids):
        if index == len(sc.problem.points)-1:
            paths.append((sc.score_path(ids)-s.f(loss_of(sc.problem, ids, loss)['total']), ids)); return
        if len(ids) >= sc.problem.max_segments: return
        for e in sc.problem.edges:
            if e.start_index == index: visit(e.end_index, ids+(e.group_id,))
    visit(0, ())
    return min(paths) if paths else None


class FullScoreAdversaryTests(unittest.TestCase):
    def scorer(self, graph, ev, weights=None):
        return s.Scorer(graph, ev, weights or s.initial_weights(s.fresh.timing.ZERO))

    def check(self, sc, loss):
        expected = exhaustive(sc, loss); actual = a.decode(sc, loss)
        if expected is None: self.assertIsNone(actual['selected']); return actual
        self.assertEqual((s.f(actual['augmented_cost']), s.fresh.path_ids(actual['selected'])), expected)
        self.assertEqual(actual['ordinary_cost'], actual['selected']['score_cost'])
        self.assertTrue(actual['exact_optimum_under_declared_score'])
        return actual

    def test_random_full_weights_joint_run_search_matches_all_paths(self):
        graph, ev = problem(); rng = random.Random(7401)
        for _ in range(14):
            tiny = replace(graph, edges=tuple(e for e in graph.edges if e.signature in (C, G, G7) and rng.random() < .65), max_segments=rng.choice((1, 2, 3)))
            weights = {k: rng.choice((s.bounds(k)[0], s.bounds(k)[1])) for k in s.FEATURES}
            refs = ({'start': F(), 'end': F(2), 'signature': C}, {'start': F(2), 'end': F(4), 'signature': G})
            self.check(self.scorer(tiny, ev, weights), training_loss(tiny, refs))

    def test_correct_ordinary_winner_still_has_positive_loss_competitor(self):
        graph, ev = problem(); sc = self.scorer(graph, ev)
        ordinary = sc.decode(); ids = s.fresh.path_ids(ordinary['selected'])
        # Use the ordinary semantic runs as a complete reachable TRAIN target.
        by = {e.group_id: e for e in graph.edges}; refs = []
        for i in ids:
            e = by[i]
            if refs and refs[-1]['signature'] == e.signature: refs[-1]['end'] = e.end
            else: refs.append({'start': e.start, 'end': e.end, 'signature': e.signature})
        loss = training_loss(graph, tuple(refs))
        self.assertEqual(s.f(loss_of(graph, ids, loss)['total']), 0)
        adversary = self.check(sc, loss)
        self.assertGreater(s.f(adversary['training_loss']['total']), 0)
        self.assertLess(s.f(adversary['augmented_cost']), sc.score_path(ids))

    def test_same_signature_partition_has_same_cost_and_same_missed_boundary(self):
        graph, ev = problem(); sc = self.scorer(graph, ev)
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        one = (by[F(), F(4), C],); split = (by[F(), F(2), C], by[F(2), F(4), C])
        refs = ({'start': F(), 'end': F(2), 'signature': C}, {'start': F(2), 'end': F(4), 'signature': G})
        loss = training_loss(graph, refs)
        self.assertEqual(sc.score_path(one), sc.score_path(split))
        self.assertEqual(loss_of(graph, one, loss), loss_of(graph, split, loss))
        self.assertEqual(loss_of(graph, split, loss)['semantic_boundary_errors'], 1)
        same = training_loss(graph, cells(graph))
        self.assertEqual(loss_of(graph, split, same)['semantic_boundary_errors'], 0)
        self.check(sc, loss)

    def test_zero_loss_reproduces_ordinary_and_no_reference_export(self):
        graph, ev = problem(); sc = self.scorer(graph, ev); loss = training_loss(graph, cells(graph))
        zero = replace(loss, boundary_weight=F(), edge_time_error=dict.fromkeys(loss.edge_time_error, F()),
                       edge_internal_missed=dict.fromkeys(loss.edge_internal_missed, 0), boundaries=frozenset())
        result = self.check(sc, zero)
        self.assertEqual(s.fresh.path_ids(result['selected']), s.fresh.path_ids(sc.decode()['selected']))
        self.assertFalse(result['analysis_export_allowed'])
        with self.assertRaisesRegex(ValueError, 'nonblind'):
            native_prediction(result['selected'], {'start': s.q(0), 'end': s.q(4)})

    def test_functional_pair_evidence_and_run_start_preserved(self):
        _, _, _, graph, ev = example(); graph, _ = supply(graph, ev)
        self.check(self.scorer(graph, ev), training_loss(graph, cells(graph, G)))

    def test_equivalent_edges_lexicographic_receipt_and_loss_mismatch(self):
        graph, ev = problem(); edge = graph.edges[0]
        alias = replace(edge, group_id='a_alias')
        graph = replace(graph, edges=graph.edges+(alias,)); loss = training_loss(graph, cells(graph))
        result = self.check(self.scorer(graph, ev), loss)
        self.assertTrue(result['search_diagnostics']['equivalence_receipts'])
        with self.assertRaisesRegex(ValueError, 'equivalence_training_loss_mismatch'):
            a.decode(self.scorer(graph, ev), replace(loss, edge_time_error=loss.edge_time_error | {'a_alias': F(1)}))

    def test_budget_nonready_disconnected_and_invalid_contract_fail_closed(self):
        graph, ev = problem(); loss = training_loss(graph, cells(graph)); sc = self.scorer(graph, ev)
        result = a.decode(sc, loss, transition_budget=1)
        self.assertIsNone(result['selected']); self.assertEqual(result['transitions'], 1)
        self.assertFalse(result['exact_optimum_under_declared_score'])
        for budget in (0, -1, True, .1):
            with self.assertRaises(ValueError): a.decode(sc, loss, transition_budget=budget)
        for bad in (replace(loss, end=F(3)), replace(loss, edge_time_error={}), replace(loss, boundary_normalizer=0)):
            with self.assertRaisesRegex(ValueError, 'training_loss_problem_mismatch'): a.decode(sc, bad)
        empty = replace(graph, edges=()); self.check(self.scorer(empty, ev), training_loss(empty, cells(empty)))
        self.assertEqual(a.decode(self.scorer(replace(graph, status='source_failure'), ev), loss)['status'], 'source_failure')

    def test_coarse_grid_changing_meter_and_unavailable_features_not_imputed(self):
        graph, ev = problem(fixture([('G3', 0, 8, 'b'), ('B3', 0, 8, 't'), ('D4', 0, 8, 'f')], end=8), end=8)
        ev.source.measures = ((F(), (4, 4), 0), (F(4), (6, 8), 0))
        ev.source._metric_cache.clear(); ev.source._feature_cache.clear()
        graph = replace(graph, points=(F(), F(8)), edges=tuple(replace(e, start_index=0, end_index=1) for e in graph.edges if e.start == 0 and e.end == 8))
        self.check(self.scorer(graph, ev), training_loss(graph, cells(graph, G)))
        odd = replace(graph.edges[0], signature=(('C', 0), (('C', 0), ('D', 0), ('E', 0))))
        tiny = replace(graph, edges=(odd,)); sc = self.scorer(tiny, ev)
        result = self.check(sc, training_loss(tiny, cells(tiny)))
        self.assertFalse(result['selected']['full_score']['availability']['absent_third_exposure'])
        self.assertFalse(result['selected']['full_score']['availability']['late_identifying_member_exposure'])
        self.assertEqual(graph.points, (F(), F(8)))

    def test_inputs_and_sealed_module_globals_are_unchanged(self):
        ir = fixture(); original = deepcopy(ir); graph, ev = problem(ir)
        old = deepcopy((s.BASE_WEIGHTS, s.EVIDENCE_WEIGHTS, s.PAIR_WEIGHTS, s.DEFAULT_WEIGHTS))
        sc = self.scorer(graph, ev); weights = dict(sc.weights); loss = training_loss(graph, cells(graph)); before = deepcopy(loss)
        a.decode(sc, loss)
        self.assertEqual(ir, original); self.assertEqual(loss, before); self.assertEqual(sc.weights, weights)
        self.assertEqual((s.BASE_WEIGHTS, s.EVIDENCE_WEIGHTS, s.PAIR_WEIGHTS, s.DEFAULT_WEIGHTS), old)


if __name__ == '__main__': unittest.main()
