from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import inspect
import random
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness import harmony_exact_frontier as frontier
from musicanote_harness.harmony_evidence_scoring import run_features
from musicanote_harness.harmony_functional_scoring import decode, score_path, supply
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.harmony_scored_decoder import Problem
from test_harmony_bounded_recovery import fixture, sample, add_grace
from test_harmony_functional_scoring import example, C, G, G7, F64


def problem(ir=None, end=4):
    ir = ir or fixture(end=end)
    view, grace = bounded.grace_projection(ir)
    plan = bounded.tile_plan(view, sample(end)["span"])
    ev, functional, _ = bounded.bound_evidence(view, sample(end)["span"], grace)
    graph, _ = bounded.build_problem(view, plan, ev)
    graph, _ = supply(graph, functional)
    return graph, functional


def exhaustive(graph, ev):
    paths = []
    def visit(index, ids):
        if index == len(graph.points)-1:
            paths.append((score_path(graph, ev, ids), ids)); return
        if len(ids) >= graph.max_segments: return
        for e in graph.edges:
            if e.start_index == index: visit(e.end_index, ids+(e.group_id,))
    visit(0, ())
    return min(paths) if paths else None


class ExactFrontierTests(unittest.TestCase):
    def check_index(self, graph, ev, signatures=None):
        indexed = frontier.RunIndex(graph, ev.source)
        for i, a in enumerate(graph.points):
            for b in graph.points[i+1:]:
                for sig in signatures or {e.signature for e in graph.edges}:
                    self.assertEqual(indexed.features(a, b, sig), run_features(graph, ev.source, a, b, sig))

    def check_decoder(self, graph, ev, use_exhaustive=False):
        expected = decode(graph, ev)
        actual = frontier.decode(graph, ev)
        self.assertEqual(actual["selected"], expected["selected"])
        self.assertEqual(actual["status"], expected["status"])
        self.assertTrue(actual["exact_optimum_under_declared_score"])
        if actual["selected"]:
            selected = actual["selected"]
            ids = tuple(s["semantic_group_ref"] for s in selected["segments"])
            self.assertEqual(bounded.f(selected["score_cost"]), score_path(graph, ev, ids))
            if use_exhaustive:
                self.assertEqual((bounded.f(selected["score_cost"]), ids), exhaustive(graph, ev))
        return actual

    def test_every_interval_feature_and_pattern_equals_original(self):
        graph, ev = problem(); self.check_index(graph, ev)

    def test_missing_meter_key_rows_and_unresolved_preserve_none(self):
        graph, ev = problem()
        ev.source.measures = (); ev.source._measure_times = (); ev.source._metric_cache.clear()
        ev.source.rows.pop(ev.source.events[0].event_id)
        ev.source.events = (replace(ev.source.events[1], pitch=None),)+ev.source.events[2:]
        ev.source._feature_cache.clear()
        self.check_index(graph, ev, [C, (None, C[1])])

    def test_empty_cells_and_changing_key_signature(self):
        ir = fixture([(p, 0, 2, v) for p, v in (("C3", "b"), ("E3", "i"), ("G3", "j"))]
                     + [("D4", 5, 8, "lead")], end=8)
        # Use source binding even though the candidate context disallows meter changes.
        graph, ev = problem(ir, end=8)
        ev.source.measures = tuple((t, meter, 2 if t == 4 else key) for t, meter, key in ev.source.measures)
        self.check_index(graph, ev, [C, G7, (None, C[1])])

    def test_tied_original_onset_and_clipped_context_exposure(self):
        graph, ev = problem()
        graph = replace(graph, points=(F(1), F(2), F(4)),
            total_note_time=sum((min(e.end, F(4))-max(e.start, F(1)) for e in ev.source.events if e.start < 4 and 1 < e.end), F()))
        ev.source.events = tuple(e for e in ev.source.events if e.start < 4 and 1 < e.end)
        self.check_index(graph, ev, [C, G7])

    def test_triplet_and_neighbor_like_original_clock(self):
        ir = fixture([("C3", 0, 2, "b"), ("E3", 0, 2, "i"), ("G3", 0, 2, "j"),
            ("C4", 0, F(1, 3), "lead"), ("D4", F(1, 3), F(2, 3), "lead"),
            ("C4", F(2, 3), 2, "lead")], end=2)
        graph, ev = problem(ir, end=2); self.check_index(graph, ev, [C, G])
        self.assertTrue(frontier.RunIndex(graph, ev.source).features(F(0), F(2), C)[1])

    def test_grace_withholding_is_not_undone(self):
        ir = fixture(); add_grace(ir)
        graph, ev = problem(ir); self.check_index(graph, ev)
        self.assertFalse(frontier.RunIndex(graph, ev.source).features(F(0), F(4), C)[1])

    def test_fine_grid_required_no_rounding(self):
        graph, ev = problem()
        with self.assertRaisesRegex(ValueError, "observation_boundary"):
            frontier.RunIndex(replace(graph, points=(F(0), F(4))), ev.source)
        ev.source._measure_times = (F(0), F(3, 2))
        with self.assertRaisesRegex(ValueError, "measure_boundary"):
            frontier.RunIndex(graph, ev.source)

    def test_exact_original_selection(self):
        graph, ev = problem(); self.check_decoder(graph, ev)

    def test_functional_six_four_and_direct_resolution(self):
        _, _, _, graph, ev = example(); graph, _ = supply(graph, ev)
        self.check_index(graph, ev, [C, G, F64]); self.check_decoder(graph, ev, True)

    def test_functional_disabled_matches_original(self):
        _, _, _, graph, ev = example(); graph, _ = supply(graph, ev)
        self.assertEqual(frontier.decode(graph, ev, functional_evidence=False)["selected"],
                         decode(graph, ev, functional_evidence=False)["selected"])

    def test_random_tiny_graphs_match_exhaustive_cost_and_lexicographic_path(self):
        graph, ev = problem(fixture(end=3), end=3)
        chosen = tuple(e for e in graph.edges if e.signature in (C, G))
        rng = random.Random(81329)
        for _ in range(30):
            edges = tuple(e for e in chosen if rng.random() < .65)
            duplicates = tuple(replace(e, group_id="alias_"+e.group_id) for e in edges[:3])
            tiny = replace(graph, edges=edges+duplicates, max_segments=rng.choice((1, 2, 3, 4, 6)))
            self.check_decoder(tiny, ev, True)

    def test_cap_dominance_does_not_discard_more_expensive_short_path(self):
        low_count = (5, ("expensive",)); cheap_more_count = (2, ("cheap", "path"))
        current = {(1, 0, C): low_count, (2, 0, C): cheap_more_count, (3, 0, C): (3, ("worse",))}
        kept, n = frontier.pareto(current)
        self.assertEqual(n, 1); self.assertIn((1, 0, C), kept); self.assertIn((2, 0, C), kept)

    def test_equal_cost_lexicographic_better_longer_path_retained(self):
        kept, n = frontier.pareto({(1, 0, C): (2, ("z",)), (2, 0, C): (2, ("a", "x")), (3, 0, C): (2, ("b", "y"))})
        self.assertEqual(n, 1); self.assertEqual(len(kept), 2)

    def test_different_run_starts_or_spelling_never_dominate(self):
        sharp = (("F", 1), (("A", 1), ("C", 1), ("F", 1)))
        flat = (("G", -1), (("B", -1), ("D", -1), ("G", -1)))
        current = {(1, 0, sharp): (0, ("x",)), (2, 0, flat): (3, ("y",)), (2, 1, sharp): (3, ("z",))}
        self.assertEqual(frontier.pareto(current), (current, 0))

    def test_edge_alias_tie_break_and_origin_receipt(self):
        graph, ev = problem(); e = graph.edges[0]
        alias = replace(e, group_id="a_alias", adapter={"another_origin": "retained_in_full_graph"})
        graph = replace(graph, edges=graph.edges+(alias,))
        edges, receipts = frontier.canonical_edges(graph)
        self.assertEqual(len(edges), len(graph.edges)-1)
        self.assertTrue(any(r["representative_group_id"] == "a_alias" for r in receipts))
        self.check_decoder(graph, ev)

    def test_blockers_attacks_source_ids_and_spelling_not_merged(self):
        graph, _ = problem(); e = graph.edges[0]
        variants = [replace(e, group_id="different_blocker", blockers=("unknown",)),
            replace(e, group_id="different_exposure", features={"blocker_exposure": F(1, 2)}),
            replace(e, group_id="different_attack", attack_spellings=frozenset()),
            replace(e, group_id="different_source", source_event_ids=("other",))]
        edges, _ = frontier.canonical_edges(replace(graph, edges=(e,)+tuple(variants)))
        self.assertEqual(len(edges), 5)

    def test_nonready_budget_and_disconnected_graph_abstain(self):
        graph, ev = problem()
        self.assertEqual(frontier.decode(replace(graph, status="source_failure"), ev)["status"], "source_failure")
        capped = frontier.decode(graph, ev, transition_budget=1)
        self.assertEqual(capped["status"], "transition_budget_abstention"); self.assertIsNone(capped["selected"])
        self.assertFalse(capped["exact_optimum_under_declared_score"])
        self.check_decoder(replace(graph, edges=()), ev)

    def test_invalid_budgets_geometry_duplicate_ids_rejected(self):
        graph, ev = problem()
        for cap in (0, -1, True, 1.5):
            with self.assertRaisesRegex(ValueError, "invalid_transition_budget"):
                frontier.decode(graph, ev, transition_budget=cap)
        with self.assertRaisesRegex(ValueError, "duplicate_frontier"):
            frontier.decode(replace(graph, edges=graph.edges+(graph.edges[0],)), ev)
        with self.assertRaisesRegex(ValueError, "invalid_frontier_edge"):
            frontier.decode(replace(graph, edges=(replace(graph.edges[0], start=F(-1)),)), ev)
        with self.assertRaisesRegex(ValueError, "unscorable_empty"):
            frontier.decode(replace(graph, edges=(replace(graph.edges[0], signature=(None, ())),)), ev)

    def test_original_feature_check_fails_closed(self):
        graph, ev = problem(); real = frontier.RunIndex.features
        def broken(self, *args):
            values, patterns = real(self, *args); values["nonmember_exposure"] += 1
            return values, patterns
        with patch.object(frontier.RunIndex, "features", broken):
            with self.assertRaisesRegex(ValueError, "winner_score_or_path_mismatch"):
                frontier.decode(graph, ev)

    def test_inference_inputs_and_parent_score_preserved(self):
        ir = fixture(); before = deepcopy(ir)
        result, graph = frontier.infer(ir, sample())
        self.assertEqual(ir, before)
        self.assertEqual(tuple(inspect.signature(frontier.infer).parameters), ("ir", "sample"))
        ir["score"]["title"] = "GOLD_V7"; ir["annotations"] = ["V7/V"]; ir["extensions"] = {"gold": "I"}
        self.assertEqual(frontier.infer(ir, sample())[0]["selected_prediction"], result["selected_prediction"])
        self.assertEqual(frontier.infer(before, sample())[1], graph)

    def test_tile_seams_are_not_independent_winners(self):
        specs = [("C3", 0, 4, "b"), ("E3", 0, 4, "i"), ("G3", 0, 4, "j")]
        specs += [("C4", F(i, 2), F(i+1, 2), "lead") for i in range(8)]
        with patch.object(bounded, "CONFIG", dict(bounded.CONFIG, tile_cells=2)):
            graph, ev = problem(fixture(specs))
        actual = self.check_decoder(graph, ev)
        self.assertEqual(len(actual["selected"]["harmonic_runs"]), 1)
        self.assertGreater(actual["search_diagnostics"]["pareto_states_removed"], 0)


if __name__ == "__main__": unittest.main()
