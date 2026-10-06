from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import json
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_streaming_joint as stream
from musicanote_harness import harmony_exact_frontier as old
from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness.harmony_functional_scoring import decode as reference
from musicanote_harness.harmony_progression_search import _hash
from test_harmony_bounded_recovery import fixture, sample
import test_harmony_exact_frontier as proofs


class StreamingCompatibilityTests(proofs.ExactFrontierTests):
    """Inherited exhaustive/cap/sign/pitch/feature proofs, no old code edit."""
    def setUp(self):
        p = patch.object(old, "decode", stream.decode); p.start(); self.addCleanup(p.stop)

    def test_nonready_budget_and_disconnected_graph_abstain(self):
        graph, ev = proofs.problem()
        self.assertEqual(stream.decode(replace(graph, status="source_failure"), ev)["status"], "source_failure")
        actual = stream.decode(graph, ev, transition_budget=1)
        self.assertEqual(actual["status"], "stream_operation_budget_abstention")
        self.assertEqual(actual["transitions"], 1); self.assertIsNone(actual["selected"])
        self.check_decoder(replace(graph, edges=()), ev)


def pages():
    specs = [("C3", 0, 4, "b"), ("E3", 0, 4, "i"), ("G3", 0, 4, "j")]
    specs += [("C4", F(i, 2), F(i+1, 2), "lead") for i in range(8)]
    ir = fixture(specs)
    with patch.object(bounded, "CONFIG", dict(bounded.CONFIG, tile_cells=2)):
        view, grace = bounded.grace_projection(ir); plan = bounded.tile_plan(view, sample()["span"])
        graph, ev = proofs.problem(ir)
    ranges = [(t["start_index"], t["end_index"]) for t in plan["tiles"]]
    batches = [replace(graph, edges=tuple(e for e in graph.edges if a <= e.start_index < e.end_index <= b)) for a,b in ranges]
    return graph, ev, ranges, batches


class StreamingPageTests(unittest.TestCase):
    def test_codec_preserves_all_edge_semantics(self):
        graph, _ = proofs.problem()
        for e in graph.edges:
            encoded = json.loads(json.dumps(stream.encode_edge(e)))
            self.assertEqual(stream.decode_edge(encoded), e)

    def test_same_run_survives_pages_and_no_tile_winner(self):
        graph, ev, ranges, batches = pages(); expected = reference(graph, ev)
        actual = stream.JointStream(graph, ev, ranges, memo_entries=1)
        by_id = {e.group_id: e for e in graph.edges}
        for page in batches:
            self.assertIsNone(actual.consume(page)["selected"])
        got = actual.finish(lambda ids: [by_id[i] for i in ids])
        self.assertEqual(got["selected"], expected["selected"])
        self.assertEqual(len(got["selected"]["harmonic_runs"]), 1)
        self.assertGreater(got["cache_evictions"], 0)

    def test_disk_style_checkpoint_restore_exact_winner_and_cumulative_work(self):
        graph, ev, ranges, batches = pages(); uninterrupted = stream.JointStream(graph, ev, ranges)
        resumed = stream.JointStream(graph, ev, ranges); before = 0
        for page in batches:
            uninterrupted.consume(page); resumed.consume(page)
            cp = json.loads(json.dumps(resumed.snapshot()))
            self.assertGreater(cp["operations"], before); before = cp["operations"]
            resumed = stream.JointStream(graph, ev, ranges, checkpoint=cp)
            self.assertEqual(resumed.operations, uninterrupted.operations)
        load = lambda ids: [next(e for e in graph.edges if e.group_id == i) for i in ids]
        self.assertEqual(resumed.finish(load)["selected"], uninterrupted.finish(load)["selected"])

    def test_checkpoint_scope_source_score_and_counter_tamper_rejected(self):
        graph, ev, ranges, batches = pages(); s = stream.JointStream(graph, ev, ranges); s.consume(batches[0])
        cp = s.snapshot()
        for field, value in (("operations", 0), ("next_page", 0), ("binding_sha256", "bad")):
            changed = deepcopy(cp); changed[field] = value
            with self.assertRaisesRegex(ValueError, "binding_or_seal"):
                stream.JointStream(graph, ev, ranges, checkpoint=changed)
        with self.assertRaisesRegex(ValueError, "binding_or_seal"):
            stream.JointStream(replace(graph, max_segments=graph.max_segments+1), ev, ranges, checkpoint=cp)
        ev.rows = tuple(ev.rows[1:])
        with self.assertRaisesRegex(ValueError, "binding_or_seal"):
            stream.JointStream(graph, ev, ranges, checkpoint=cp)

    def test_incomplete_and_aborted_streams_never_yield_prediction(self):
        graph, ev, ranges, batches = pages(); s = stream.JointStream(graph, ev, ranges, operation_budget=1)
        s.consume(batches[0]); self.assertIsNone(s.finish(lambda _: ())["selected"])
        with self.assertRaisesRegex(ValueError, "checkpointable"): s.snapshot()
        with self.assertRaisesRegex(ValueError, "terminal"): s.consume(batches[1])
        s = stream.JointStream(graph, ev, ranges); s.consume(batches[0])
        with self.assertRaisesRegex(ValueError, "incomplete"): s.finish(lambda _: ())

    def test_page_topology_and_global_objective_not_rebased(self):
        graph, ev, ranges, batches = pages()
        s = stream.JointStream(graph, ev, ranges)
        with self.assertRaisesRegex(ValueError, "objective_changed"):
            s.consume(replace(batches[0], total_note_time=F(1)))
        with self.assertRaisesRegex(ValueError, "crosses_partition"):
            s.consume(batches[-1])

    def test_prepared_source_mutation_invalidates_live_stream(self):
        graph, ev, ranges, batches = pages(); s = stream.JointStream(graph, ev, ranges)
        ev.source.neighbors.clear()
        # This fixture may have no eligible neighbor: explicitly change a source row.
        next(iter(ev.source.rows.values()))["pitch"] += 1
        with self.assertRaisesRegex(ValueError, "evidence_changed"): s.consume(batches[0])

    def test_wrong_winner_ledger_rejected(self):
        graph, ev = proofs.problem(); s = stream.JointStream(graph, ev, [(0,len(graph.points)-1)])
        s.consume(graph)
        with self.assertRaisesRegex(ValueError, "ledger_changed"): s.finish(lambda _: ())

    def test_only_storage_limits_superseded_repeat_retained(self):
        ir = fixture(end=80); span = sample(80)["span"]
        p = stream.streaming_plan(ir, span)
        self.assertEqual(p["status"], "ready")
        self.assertIn("global_cell_budget_no_truncation", p.get("superseded_global_storage_guards", [])) if len(p["points"])-1>64 else None
        ir["measures"][4]["repeat_barline"] = {"location":"right","repeat_direction":"backward"}
        p = stream.streaming_plan(ir, span)
        self.assertEqual(p["status"], "bounded_plan_abstention")
        self.assertIn("repeat_or_ending_barrier", p["blockers"])


if __name__ == "__main__": unittest.main()
