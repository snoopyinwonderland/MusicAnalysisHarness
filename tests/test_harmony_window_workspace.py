from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_window_workspace as work
from musicanote_harness import harmony_candidate_catalog as catalog
from musicanote_harness import harmony_augmented_candidates as aug
from musicanote_harness import harmony_extended_candidates as ext
from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness import harmony_batched_frontier as frontier
from musicanote_harness.formal_ir import q
from test_harmony_bounded_recovery import fixture, sample, add_grace


def span(a=0, b=4):
    return {"start": q(a), "end": q(b)}


class WindowWorkspaceTests(unittest.TestCase):
    def equal_catalog(self, ir, target=None, context=None):
        old = deepcopy(ir)
        target = target or span()
        got = work.WindowWorkspace(ir).propose(target, context)
        self.assertEqual(got, catalog.propose(ir, target, context))
        self.assertEqual(ir, old)
        return got

    def test_complete_catalog_and_conditional_ornaments(self):
        got = self.equal_catalog(fixture())
        self.assertTrue(got["providers"]["base"]["conditional_figures"]["records"])

    def test_augmented_sixth_and_extension_contexts(self):
        for pitches in (("A-3", "C4", "E-4", "F#4"), ("C3", "E3", "G3", "B-3", "D4")):
            ir = fixture([(p, 0, 4, str(i)) for i, p in enumerate(pitches)])
            got = self.equal_catalog(ir, span(0, 1), span())
            self.assertTrue(got["candidates"])

    def test_silence_missing_meter_microtonal_and_grace_blockers(self):
        variants = [fixture([("C4", 0, 1, "v"), ("E4", 2, 4, "v")])]
        ir = fixture(); ir["measures"][0]["time_signature"]["beats"] = None; variants.append(ir)
        ir = fixture(); ir["sounding_events"][0]["pitch"]["alter"] = q(F(1, 2)); variants.append(ir)
        ir = fixture(); add_grace(ir); variants.append(ir)
        for ir in variants:
            self.equal_catalog(ir)

    def test_repeated_requests_reuse_without_global_patch(self):
        ir = fixture(); w = work.WindowWorkspace(ir)
        originals = aug.window, ext.window, catalog.augmented, catalog.extended, bounded.propose
        w.propose(span(0, 1), span()); w.propose(span(0, 1), span())
        self.assertEqual(w.stats["window_requests"], 8)
        self.assertEqual(w.stats["window_computations"], 2)
        self.assertEqual(originals, (aug.window, ext.window, catalog.augmented, catalog.extended, bounded.propose))

    def test_defensive_copy_and_exact_span_representation(self):
        ir = fixture(); w = work.WindowWorkspace(ir)
        got = w.propose(span()); got["providers"]["base"]["event_units"].clear()
        self.assertEqual(w.propose(span()), catalog.propose(ir, span()))
        different = {"start": {"numerator": 0, "denominator": 2}, "end": q(4)}
        self.assertEqual(w.propose(different), catalog.propose(ir, different))
        self.assertEqual(w.stats["window_computations"], 2)

    def test_lru_eviction_recomputes_not_prunes(self):
        ir = fixture(); w = work.WindowWorkspace(ir, max_entries=1)
        a, b = w.propose(span(0, 1), span()), w.propose(span(1, 2), span())
        self.assertEqual(a, catalog.propose(ir, span(0, 1), span()))
        self.assertEqual(b, catalog.propose(ir, span(1, 2), span()))
        self.assertEqual(w.stats["peak_entries"], 1); self.assertGreater(w.stats["evictions"], 0)

    def test_source_mutation_invalidates_lease(self):
        ir = fixture(); w = work.WindowWorkspace(ir); w.propose(span())
        ir["sounding_events"][0]["span"]["end"] = q(3)
        with self.assertRaisesRegex(ValueError, "source_changed"): w.propose(span())
        self.assertFalse(w.valid); self.assertFalse(w.cache)

    def test_foreign_source_is_not_reused(self):
        w = work.WindowWorkspace(fixture())
        with self.assertRaisesRegex(ValueError, "foreign_source"): w._window(fixture(), span())

    def test_operation_detects_provider_mutation(self):
        ir = fixture(); w = work.WindowWorkspace(ir)
        def bad(ir, target, context):
            ir["score"]["duration_quarters"] = q(2)
            return None
        w._catalog = bad
        with self.assertRaisesRegex(ValueError, "source_changed"): w.propose(span())

    def test_exception_does_not_patch_original_dependencies(self):
        originals = aug.window, ext.window
        w = work.WindowWorkspace(fixture())
        with self.assertRaises(ValueError): w.propose(span(2, 1))
        self.assertEqual(originals, (aug.window, ext.window))

    def test_two_workspaces_do_not_share_sources_or_cache(self):
        a, b = fixture(), fixture([("D3", 0, 4, "b"), ("F#3", 0, 4, "v"), ("A3", 0, 4, "j")])
        def run(ir):
            return work.WindowWorkspace(ir).propose(span())
        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(run, (a, b)))
        self.assertEqual(values, [catalog.propose(ir, span()) for ir in (a, b)])

    def test_graph_origins_and_decoder_prediction_identical(self):
        ir = fixture(); view, receipt = bounded.grace_projection(ir)
        ev, _, _ = bounded.bound_evidence(view, span(), receipt)
        plan = bounded.tile_plan(view, span()); oldplan = deepcopy(plan)
        expected, origins = bounded.build_problem(view, oldplan, ev)
        got, gotorigins = work.WindowWorkspace(view).build(plan, ev)
        self.assertEqual(expected, got); self.assertEqual(origins, gotorigins); self.assertEqual(plan, oldplan)
        new, _ = work.infer(ir, sample()); old, _ = frontier.infer(ir, sample())
        for key in old:
            if key != "version": self.assertEqual(new[key], old[key], key)

    def test_unsafe_binding_or_cache_budget_rejected(self):
        for n in (0, -1, True, F(2)):
            with self.assertRaises(ValueError): work.WindowWorkspace(fixture(), max_entries=n)
        with self.assertRaises(ValueError): work.bind(catalog.propose, {"not_a_dependency": None})
        with self.assertRaises(ValueError): work.bind(None, {})


if __name__ == "__main__":
    unittest.main()
