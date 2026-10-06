from dataclasses import replace
from fractions import Fraction as F
import unittest

from musicanote_harness import harmony_source_context_scoring as s
from musicanote_harness import harmony_score_balance_ledger as ledger
from test_harmony_context_joint_decoder import toy, paths
from test_harmony_functional_scoring import C, G7, F64
from test_harmony_terminal_context import terminal_example


def weights():
    return ledger.old.initial_weights(ledger.old.fresh.timing.ZERO) | ledger.context.ZERO | ledger.role.ZERO


class SourceContextScoringTests(unittest.TestCase):
    def test_exact_search_matches_every_tiny_path_with_added_run_cost(self):
        graph, ev, _ = toy(cap=3, signatures=(C, G7, F64))
        for extra in (s.ZERO, {s.FEATURES[0]: F(2), s.FEATURES[1]: F(-1), s.FEATURES[2]: F(-2)}):
            sc = s.Scorer(graph, ev, weights(), extra)
            wanted = min((sc.score_path(ids), ids) for ids in paths(graph))
            result = sc.decode(force_delayed=True)
            got = result['selected']
            self.assertEqual((s.f(got['score_cost']), ledger.old.fresh.path_ids(got)), wanted)

    def test_zero_reproduces_old_choice_cost_and_module_globals(self):
        graph, ev, _ = toy(cap=3); old = s.parent.Scorer(graph, ev, weights())
        before = s.joint.Scorer._delayed.__globals__['old_score']
        sc = s.Scorer(graph, ev, weights()); result = sc.decode(); baseline = old.decode()
        self.assertEqual(result['selected']['score_cost'], baseline['selected']['score_cost'])
        self.assertEqual(ledger.old.fresh.path_ids(result['selected']), ledger.old.fresh.path_ids(baseline['selected']))
        self.assertIs(s.joint.Scorer._delayed.__globals__['old_score'], before)

    def test_terminal_source_can_change_actual_functional_choice(self):
        graph, ev = terminal_example(); template = graph.edges[0]
        graph = replace(graph, edges=tuple(replace(template, group_id='c'+str(i), start_index=0,
            end_index=len(graph.points)-1, start=graph.points[0], end=graph.points[-1], signature=sig,
            features={'blocker_exposure': F()}, blockers=()) for i, sig in enumerate((C, F64))))
        sc = s.Scorer(graph, ev, weights(), {s.FEATURES[0]: F(), s.FEATURES[1]: F(-2), s.FEATURES[2]: F(-2)})
        r = sc.decode(); self.assertEqual(r['selected']['harmonic_runs'][0]['root_spelling'], F64[0])
        self.assertEqual(r['selected']['context_score']['legacy']['cost'], r['selected']['legacy_score_cost'])

    def test_partial_unknown_not_complete_feature_zero(self):
        graph, ev, _ = toy(signatures=(F64,), cap=1)
        sc = s.Scorer(graph, ev, weights()); ids = next(ids for ids in paths(graph) if len(ids) == 1)
        receipt = sc.path_receipt(ids)['source_context']
        self.assertIsNone(receipt['features'][s.FEATURES[0]])
        self.assertFalse(receipt['availability'][s.FEATURES[0]])

    def test_split_union_cost_same(self):
        graph, ev, _ = toy(cap=4, signatures=(G7,)); sc = s.Scorer(graph, ev, weights(), {s.FEATURES[0]:F(1),s.FEATURES[1]:F(),s.FEATURES[2]:F()})
        by = {(e.start, e.end): e.group_id for e in graph.edges}
        self.assertEqual(sc.path_receipt((by[F(),F(4)],))['source_context'],
                         sc.path_receipt((by[F(),F(2)],by[F(2),F(4)]))['source_context'])

    def test_coefficient_and_resource_guard_contracts(self):
        with self.assertRaises(ValueError): s.coefficients(dict.fromkeys(s.FEATURES, F(1)))
        graph, ev, _ = toy(cap=3); sc = s.Scorer(graph, ev, weights(), {s.FEATURES[0]:F(1),s.FEATURES[1]:F(),s.FEATURES[2]:F()})
        r = sc.decode(transition_budget=1)
        self.assertIsNone(r['selected']); self.assertEqual(r['status'],'transition_budget_abstention')
