from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
import unittest

from musicanote_harness import harmony_batched_frontier as batched
from musicanote_harness import harmony_exact_frontier as frontier
import test_harmony_exact_frontier as proofs
from test_harmony_functional_scoring import C, G, F64, example
from musicanote_harness.harmony_functional_scoring import supply


class BatchedFrontierTests(proofs.ExactFrontierTests):
    """Run all 21 exact-feature/cap/tie/exhaustive proofs against batching."""
    def setUp(self):
        self.patches = [patch.object(frontier, "decode", batched.decode), patch.object(frontier, "infer", batched.infer)]
        for p in self.patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def test_changed_run_groups_do_not_mix_actual_attack_sets(self):
        graph, ev = proofs.problem()
        variants = tuple(replace(e, group_id="attackless_"+e.group_id, attack_spellings=frozenset()) for e in graph.edges)
        self.check_decoder(replace(graph, edges=graph.edges+variants), ev)

    def test_group_predecessor_minimum_ignores_only_destination_constants(self):
        graph, ev = proofs.problem()
        # Different blocker costs and end points must survive factorization.
        changed = tuple(replace(e, features=e.features | {"blocker_exposure": F(e.end_index, 4)}, blockers=("unknown",))
                        if e.signature == G else e for e in graph.edges)
        tiny = replace(graph, edges=tuple(e for e in changed if e.signature in (C, G)), max_segments=3)
        self.check_decoder(tiny, ev, True)

    def test_complete_search_receipt_counts_factored_and_logical_work(self):
        graph, ev = proofs.problem()
        result = batched.decode(graph, ev)
        diag = result["search_diagnostics"]
        self.assertGreater(diag["logical_transitions_represented"], result["transitions"])
        self.assertTrue(diag["numeric_budget_unchanged_operation_unit_changed"])
        self.assertFalse(diag["beam_pruning"])

    def test_functional_scope_keeps_carried_and_extending_original_rows(self):
        _, _, _, graph, ev = example()
        before = tuple(ev.rows)
        scoped = batched.scoped_functional_evidence(graph, ev)
        self.assertEqual(scoped.rows, before)
        self.assertIs(scoped.source, ev.source)
        self.assertEqual(scoped.links, ev.links)
        self.assertEqual(ev.rows, before)


if __name__ == "__main__": unittest.main()
