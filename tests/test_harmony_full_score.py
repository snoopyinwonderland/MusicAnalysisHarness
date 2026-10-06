from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import random
import unittest

from musicanote_harness import harmony_full_score as s
from musicanote_harness.harmony_common_benchmark import native_prediction
from test_harmony_exact_frontier import problem
from test_harmony_bounded_recovery import fixture
from test_harmony_functional_scoring import C, G, G7


class FullScoreTests(unittest.TestCase):
    def test_initial_exactly_reproduces_sealed_costs_and_paths(self):
        ir = fixture(); before = deepcopy(ir); graph, ev = problem(ir)
        extra = {k: F(1, 3) for k in s.fresh.timing.FEATURES}
        old = s.fresh.direct_scorer(graph, ev, extra)
        new = s.Scorer(graph, ev, s.initial_weights(extra))
        a, b = old.decode()['selected'], new.decode()['selected']
        self.assertEqual(s.fresh.path_ids(a), s.fresh.path_ids(b))
        self.assertEqual(a['score_cost'], b['score_cost'])
        for sig in (C, G, G7):
            ids = tuple(e.group_id for e in graph.edges if e.start == 0 and e.end == 4 and e.signature == sig)
            self.assertEqual(old.score_path(ids), new.score_path(ids))
        self.assertEqual(ir, before)

    def test_random_full_weights_exact_exhaustive_tiny_joint_search(self):
        graph, ev = problem(); rng = random.Random(7101)
        for _ in range(8):
            tiny = replace(graph, edges=tuple(e for e in graph.edges if e.signature in (C, G, G7) and rng.random() < .6), max_segments=3)
            weights = {k: rng.choice((s.bounds(k)[0], s.bounds(k)[1])) for k in s.FEATURES}
            scorer = s.Scorer(tiny, ev, weights); paths = []
            def visit(i, ids):
                if i == len(tiny.points)-1: paths.append((scorer.score_path(ids), ids)); return
                if len(ids) >= tiny.max_segments: return
                for e in tiny.edges:
                    if e.start_index == i: visit(e.end_index, ids+(e.group_id,))
            visit(0, ()); result = scorer.decode()
            if not paths: self.assertIsNone(result['selected']); continue
            self.assertEqual((s.f(result['selected']['score_cost']), s.fresh.path_ids(result['selected'])), min(paths))

    def test_same_signature_raw_partition_does_not_change_run_cost(self):
        graph, ev = problem(); scorer = s.Scorer(graph, ev, s.initial_weights(s.fresh.timing.ZERO))
        by = {(e.start, e.end, e.signature): e.group_id for e in graph.edges}
        a = (by[F(), F(4), C],)
        b = (by[F(), F(2), C], by[F(2), F(4), C])
        self.assertEqual(scorer.path_features(a), scorer.path_features(b))
        self.assertEqual(scorer.score_path(a), scorer.score_path(b))

    def test_no_nonmember_domain_is_known_zero_not_unknown_imputation(self):
        value = {'conditional_step_ornament_exposure': None, 'nonmember_exposure': F(), 'unresolved_spelling_exposure': F()}
        self.assertEqual(s.applicability(value)['conditional_step_ornament_exposure'], F())
        for changed in ({'nonmember_exposure': F(1, 4)}, {'unresolved_spelling_exposure': F(1, 4)}):
            self.assertIsNone(s.applicability(value | changed)['conditional_step_ornament_exposure'])
        self.assertIsNone(value['conditional_step_ornament_exposure'])

    def test_null_unsupported_roles_retained_and_receipts_sum(self):
        graph, ev = problem(); scorer = s.Scorer(graph, ev, s.initial_weights(s.fresh.timing.ZERO))
        e = next(e for e in graph.edges if e.start == 0 and e.end == 4 and e.signature == C)
        receipt = scorer.receipt((e.group_id,))
        self.assertEqual(sum((s.f(v) for v in receipt['term_costs'].values()), F()), s.f(receipt['cost']))
        self.assertTrue(receipt['source_support'])
        self.assertFalse(receipt['source_labels_used_to_create_this_path'])

    def test_target_status_is_not_exportable_as_blind_prediction(self):
        graph, ev = problem(); selected = s.Scorer(graph, ev, s.initial_weights(s.fresh.timing.ZERO)).decode()['selected']
        selected.update(source_labels_used_for_selection=True, training_reference_labels_used=True)
        with self.assertRaisesRegex(ValueError, 'nonblind'):
            native_prediction(selected, {'start': s.q(0), 'end': s.q(4)})

    def test_invalid_paths_bounds_types_and_fixed_terms_rejected(self):
        graph, ev = problem(); w = s.initial_weights(s.fresh.timing.ZERO)
        for k, v in [('harmonic_run_count', F()), ('nonmember_exposure', F(-1)), ('blocker_exposure', F(1)), ('missing_root', 0.1)]:
            with self.assertRaises(ValueError): s.Scorer(graph, ev, w | {k: v})
        scorer = s.Scorer(graph, ev, w)
        for ids in ((), ('missing',), tuple(e.group_id for e in graph.edges[:2])):
            with self.assertRaises(ValueError): scorer.score_path(ids)

    def test_resource_limit_never_returns_partial_winner(self):
        graph, ev = problem()
        result = s.Scorer(graph, ev, s.initial_weights(s.fresh.timing.ZERO)).decode(transition_budget=1)
        self.assertIsNone(result['selected']); self.assertFalse(result['exact_optimum_under_declared_score'])

    def test_original_module_weights_are_not_mutated(self):
        graph, ev = problem(); before = deepcopy((s.BASE_WEIGHTS, s.EVIDENCE_WEIGHTS, s.PAIR_WEIGHTS, s.DEFAULT_WEIGHTS))
        w = s.initial_weights(s.fresh.timing.ZERO) | {'conditional_step_ornament_exposure': F(-1), 'lowest_nonmember_exposure': F(1)}
        s.Scorer(graph, ev, w).decode()
        self.assertEqual((s.BASE_WEIGHTS, s.EVIDENCE_WEIGHTS, s.PAIR_WEIGHTS, s.DEFAULT_WEIGHTS), before)

    def test_coarse_measure_grid_direct_backend_without_point_insertion(self):
        graph, ev = problem(fixture([('G3', 0, 8, 'b'), ('B3', 0, 8, 't'), ('D4', 0, 8, 'f')], end=8), end=8)
        edges = tuple(replace(e, start_index=0, end_index=1) for e in graph.edges if e.start == 0 and e.end == 8)
        coarse = replace(graph, points=(F(), F(8)), edges=edges)
        result = s.Scorer(coarse, ev, s.initial_weights(s.fresh.timing.ZERO)).decode()
        self.assertIsNotNone(result['selected']); self.assertEqual(coarse.points, (F(), F(8)))

    def test_nontertian_shape_does_not_claim_zero_absent_third(self):
        graph, ev = problem(); original = next(e for e in graph.edges if e.start == 0 and e.end == 4)
        odd = replace(original, signature=(('C', 0), (('C', 0), ('D', 0), ('E', 0))))
        tiny = replace(graph, edges=(odd,)); scorer = s.Scorer(tiny, ev, s.initial_weights(s.fresh.timing.ZERO))
        values, availability = scorer.path_features((odd.group_id,))
        self.assertFalse(availability['absent_third_exposure'])
        self.assertFalse(availability['late_identifying_member_exposure'])
        self.assertEqual(s.q(scorer.score_path((odd.group_id,))), scorer.decode()['selected']['score_cost'])
