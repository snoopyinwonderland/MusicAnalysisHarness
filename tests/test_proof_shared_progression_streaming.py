"""Owned canonical stream and conservative pre-pair schema-bound controls."""
from dataclasses import replace
from fractions import Fraction
import gc
import hashlib
import inspect
import json
from types import MappingProxyType
import unittest
from unittest.mock import patch
import weakref

from musicanote_harness import proof_shared_progression_streaming as streaming
from musicanote_harness import proof_shared_source_progression_contrast as core
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import lossless_json_dag_v2 as dag
from musicanote_harness import cross_batch_progression_contrast as codec
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness.musical_pattern_observation import q
import test_shared_source_progression_contrast as fixture_module
from test_cross_batch_progression_contrast import request_ref
from test_factor_expanded_hypotheses import span


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class ProofSharedProgressionStreamingControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.SharedSourceContrastTests.setUpClass()
        cls.addClassCleanup(fixture_module.SharedSourceContrastTests.doClassCleanups)
        fixture = fixture_module.SharedSourceContrastTests()
        cls.fixture = fixture
        cls.groups = {}
        for name, mode in (("passing", "candidate"), ("rational", "candidate"), ("ordinary_first_adverse", "transition")):
            scope, lattice, entries, bundles = fixture.inputs(name, mode)
            source = shared.prepare_saved_source(scope, lattice, bundles=bundles)
            group = core.prepare_saved_group(source, entries, completion_request_ref=request_ref(), selector_indices=[3, 18000], block_size=1)
            cls.groups[name] = (source, group)

    def test_source_stream_byte_exact_sha_and_chunk_bounds_no_export(self):
        source, _ = self.groups["passing"]
        expected = raw(source.export_source())
        with patch.object(shared.PreparedSource, "export_source", side_effect=AssertionError("no thaw/export")), \
                patch.object(codec, "_copy", side_effect=AssertionError("no raw copy")):
            info = streaming.source_stream_info(source)
            for chunk_bytes in (1, 127, 4096, streaming.DEFAULT_CHUNK_BYTES):
                chunks = list(streaming.iter_source_json(source, chunk_bytes=chunk_bytes))
                self.assertTrue(all(0 < len(chunk) <= chunk_bytes for chunk in chunks))
                self.assertEqual(b"".join(chunks), expected)
        self.assertEqual(info["canonical_bytes"], len(expected))
        self.assertLessEqual(len(expected), info["canonical_byte_upper_bound"])
        self.assertEqual(hashlib.sha256(expected).hexdigest(), hashlib.sha256(b"".join(chunks)).hexdigest())
        self.assertTrue(info["descriptor_is_not_authority"])

    def test_catalog_stream_byte_exact_without_dag_record_export_or_decode(self):
        _, group = self.groups["passing"]
        expected = raw(group.export_catalog())
        with patch.object(core.CompactPreparedGroup, "export_catalog", side_effect=AssertionError("no whole catalog")), \
                patch.object(dag.JsonDag, "record", side_effect=AssertionError("no table export")), \
                patch.object(dag, "decode_json", side_effect=AssertionError("no tree decode")), \
                patch.object(codec, "_copy", side_effect=AssertionError("no thaw")):
            info = streaming.catalog_stream_info(group)
            chunks = list(streaming.iter_catalog_json(group, chunk_bytes=257))
        self.assertTrue(all(0 < len(chunk) <= 257 for chunk in chunks))
        self.assertEqual(b"".join(chunks), expected)
        self.assertEqual(info["canonical_bytes"], len(expected))
        self.assertEqual(info["original_selector_indices"], [3, 18000])
        self.assertEqual(info["owned_source_identity"], id(self.groups["passing"][0]))
        self.assertEqual(info["raw_sha256_work_upper_bound"], len(expected))

    def test_typed_stream_escaping_unicode_key_order_and_small_string_fragments(self):
        value = {"쉼": "😀\x00\b\f\n\r\t\\\"" * 8000, "a": [None, False, 0, True, -3], "𐀀": {"x": []}}
        frozen = codec._freeze(value)
        expected = raw(value)
        fragments = list(streaming._owned_fragments(frozen, 31))
        self.assertLessEqual(max(map(len, fragments)), 31 * 6)
        self.assertEqual(b"".join(fragments), expected)
        chunks = list(streaming._pack_chunks(streaming._owned_fragments(frozen, 31), 53))
        self.assertEqual(b"".join(chunks), expected)
        self.assertLessEqual(max(map(len, chunks)), 53)
        meter = streaming._Measure(10000000)
        size = streaming._measure_owned(frozen, meter)
        self.assertEqual(size, len(expected))
        self.assertEqual(meter.work, size + meter.visits)

    def test_stream_rejects_float_subclass_bad_utf8_and_exact_chunk_limits(self):
        class Text(str): pass
        for value in (1.0, Text("x"), "\ud800", MappingProxyType({1: 0})):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    streaming._measure_owned(value, streaming._Measure(100000))
        source, group = self.groups["passing"]
        for chunk in (0, True, -1, 1.0, streaming.DEFAULT_CHUNK_BYTES + 1):
            for action, owner in ((streaming.iter_source_json, source), (streaming.iter_catalog_json, group)):
                with self.subTest(chunk=chunk, action=action.__name__):
                    with self.assertRaises(ValueError):
                        next(action(owner, chunk_bytes=chunk))

    def test_stream_work_gate_before_first_output_and_unknown_is_not_zero(self):
        source, group = self.groups["passing"]
        for action, owner in ((streaming.source_stream_info, source), (streaming.catalog_stream_info, group)):
            with self.assertRaises(streaming.StreamHold):
                action(owner, max_work=1)
        for action, owner in ((streaming.iter_source_json, source), (streaming.iter_catalog_json, group)):
            with patch.object(streaming, "_pack_chunks", side_effect=AssertionError("no stream prefix")):
                with self.assertRaises(streaming.StreamHold):
                    next(action(owner, max_work=1))
        task = next(group.iter_blocks())
        held = streaming.task_stream_bound(group, task, max_work=1)
        self.assertEqual(held["expected_pairs"], task.expected_pairs)
        self.assertIsNone(held["raw_block_byte_upper_bound"])
        self.assertIsNone(held["planning_work_upper_bound"])
        self.assertEqual(held["pair_outputs_computed"], 0)

    def test_foreign_handles_descriptors_and_modified_tasks_cannot_authorize(self):
        source, group = self.groups["passing"]
        for owner in (source.export_source(), streaming.source_stream_info(source), object.__new__(shared.PreparedSource)):
            with self.assertRaises(ValueError):
                streaming.source_stream_info(owner)
        for owner in (group.export_catalog(), streaming.catalog_stream_info(group), object.__new__(core.CompactPreparedGroup)):
            with self.assertRaises(ValueError):
                streaming.catalog_stream_info(owner)
        task = next(group.iter_blocks())
        for changed in (replace(task, expected_pairs=True), replace(task, source_sha256="0" * 64),
                replace(task, entry_inventory_sha256="0" * 64), replace(task, row_start=1), dict(task=task)):
            with self.assertRaises(ValueError):
                streaming.task_stream_bound(group, changed)

    def test_whole_task_bound_before_pair_output_no_sampling_or_atom_runs(self):
        _, group = self.groups["passing"]
        task = next(group.iter_blocks())
        with patch.object(core, "compare_block", side_effect=AssertionError("no pair output")), \
                patch.object(core, "_compact_pair", side_effect=AssertionError("no pair output")), \
                patch.object(codec, "_runs", side_effect=AssertionError("no atom pair walk")), \
                patch.object(dag, "value_at", side_effect=AssertionError("no assumption decode")):
            bound = streaming.task_stream_bound(group, task)
        self.assertEqual(bound["status"], "admissible_whole_block_stream_bound")
        self.assertEqual(bound["expected_pairs"], task.expected_pairs)
        self.assertEqual(bound["pair_outputs_computed"], 0)
        block = core.compare_block(group, task)
        self.assertLessEqual(len(raw(block)), bound["raw_block_byte_upper_bound"])
        self.assertLessEqual(max(map(lambda p: len(raw(p)), block["pairs"])), bound["maximum_pair_byte_upper_bound"])

    def test_genuine_rational_and_transition_blocks_respect_complete_schema_bound(self):
        for name, (_, group) in self.groups.items():
            with self.subTest(name=name):
                for task in group.iter_blocks():
                    bound = streaming.task_stream_bound(group, task)
                    block = core.compare_block(group, task)
                    self.assertEqual(block["computed_pairs"], task.expected_pairs)
                    self.assertLessEqual(len(raw(block)), bound["raw_block_byte_upper_bound"])
                    for pair in block["pairs"]:
                        self.assertLessEqual(len(raw(pair)), bound["maximum_pair_byte_upper_bound"])
                    self.assertEqual(bound["schema_scope"], "compact_compare_block_not_materialized_legacy_pair")

    def test_tiny_byte_cap_holds_whole_task_without_pair_computation(self):
        _, group = self.groups["passing"]
        task = next(group.iter_blocks())
        with patch.object(core, "_compact_pair", side_effect=AssertionError("no pair computation")):
            held = streaming.task_stream_bound(group, task, max_block_bytes=1)
        self.assertEqual(held["expected_pairs"], task.expected_pairs)
        self.assertEqual(held["status"], "whole_block_stream_bound_hold")
        self.assertGreater(held["raw_block_byte_upper_bound"], 1)
        self.assertEqual(held["pair_outputs_computed"], 0)

    def test_rational_width_bound_covers_large_denominators_sign_and_sum_carry(self):
        meter = streaming._Measure(100000)
        for left, right in ((Fraction(999999, 97), Fraction(-999999, 89)),
                (Fraction(0), Fraction(1, 99991)), (Fraction(-1, 99989), Fraction(1, 99991))):
            lq, rq = codec._freeze(q(left)), codec._freeze(q(right))
            bound = streaming._delta_bound(streaming._rational(lq, meter), streaming._rational(rq, meter))
            self.assertLessEqual(len(raw(q(left - right))), bound)

    def test_coprime_transfer_denominator_growth_and_escaped_assumption_bytes(self):
        points = [[Fraction(1, 3), Fraction(2, 5), Fraction(7, 11)], [Fraction(3, 13), Fraction(4, 7)]]
        refinement = codec._freeze({"sounds": [{"points": list(map(q, rows))} for rows in points],
            "bass": {"points": [q(0), q(1)]}})
        summary = streaming._refinement_summary(refinement, streaming._Measure(100000))
        transfer = sum((b - a for rows in points for a, b in zip(rows, rows[1:])), Fraction())
        self.assertLessEqual(len(raw(q(transfer))), summary["transfer_rational_bytes"])
        self.assertGreater(summary["transfer_rational_bytes"], max(len(raw(q(p))) for rows in points for p in rows))
        self.assertGreaterEqual(summary["transfer_denominator_decimal_digits_upper_bound"], len(str(transfer.denominator)))
        assumption = {"text": "quote\" slash\\ control\x00 쉼 😀" * 100}
        payload = dag.encode_json(assumption)
        exact = dag.subtree_stats(payload)["expanded_bytes"]
        self.assertEqual(exact, len(raw(assumption)))
        one = {"source_row_digits": 1, "bass_row_digits": 1, "selector_digits": 1,
            "cut_count": 1, "time_bytes": len(raw(q(Fraction(1, 3)))), "assumption_bytes": exact,
            "raw": (1, 1), "note_time": {c: (1, 1) for c in core.CATEGORIES}, "conditional": None}
        none = dict(one, cut_count=0, time_bytes=0, assumption_bytes=0)
        full = streaming._pair_bound(4, 0, 1, one, one, summary, (100, 100, 100))
        empty = streaming._pair_bound(4, 0, 1, none, none, summary, (100, 100, 100))
        self.assertGreaterEqual(full - empty, 2 * exact)

    def test_three_entries_third_endpoint_whole_task_pair_sum_and_commas(self):
        fixture = self.fixture.fixture.fixture
        members = fixture_module.fixture_module.fixture_module.members("C", "E", "G")
        selectors = [fixture.selector("three_slots"),
            fixture.selector("three_slots", partitions=[(span(0, 4), ("C", Fraction()), members)], assumptions=[]),
            fixture.selector("three_slots", partitions=[(span(0, 1), ("C", Fraction()), members),
                (span(1, 4), ("C", Fraction()), members)], assumptions=[None])]
        session, comparison, bundle = fixture.comparison("three_slots", selectors=selectors)
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": path, "role_path": role, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for path, role in zip(comparison["paths"], explained["paths"])]
        source = shared.prepare_saved_source(fixture.case("three_slots")[0][1], fixture.record("three_slots"),
            bundles={bundle["record_id"]: bundle})
        group = core.prepare_saved_group(source, entries, completion_request_ref=request_ref(), block_size=3)
        task = next(group.iter_blocks())
        self.assertEqual(task.expected_pairs, 3)
        with patch.object(core, "_compact_pair", side_effect=AssertionError("bound cannot compute outcomes")), \
                patch.object(codec, "_runs", side_effect=AssertionError("bound cannot walk atom pairs")):
            bound = streaming.task_stream_bound(group, task)
        block = core.compare_block(group, task)
        self.assertEqual(block["computed_pairs"], 3)
        self.assertLessEqual(len(raw(block)), bound["raw_block_byte_upper_bound"])
        for pair in block["pairs"]:
            self.assertLessEqual(len(raw(pair)), bound["maximum_pair_byte_upper_bound"])
        self.assertGreater(bound["raw_block_byte_upper_bound"], sum(len(raw(pair)) for pair in block["pairs"]))

    def test_generators_module_level_and_early_close_cleanup_gc_disabled(self):
        was = gc.isenabled()
        gc.disable()
        try:
            for name in ("_owned_fragments", "_catalog_fragments", "_pack_chunks"):
                worker = getattr(streaming, name)
                self.assertEqual(worker.__code__.co_freevars, ())
                self.assertIsNone(worker.__closure__)
            value = codec._freeze({"key": ["text"] * 100})
            gen = streaming._owned_fragments(value, 17)
            gen_ref = weakref.ref(gen)
            next(gen)
            gen.close()
            self.assertIsNone(gen.gi_frame)
            del gen
            self.assertIsNone(gen_ref())
            for action, owner in ((streaming.iter_source_json, self.groups["passing"][0]),
                    (streaming.iter_catalog_json, self.groups["passing"][1])):
                gen = action(owner, chunk_bytes=17)
                next(gen)
                gen.close()
                self.assertIsNone(gen.gi_frame)
            self.assertNotIn("gc.collect", inspect.getsource(streaming))
        finally:
            if was: gc.enable()

    def fresh_group(self):
        source, original = self.groups["passing"]
        entries = [original.export_entry(i) for i in range(original.preflight_plan.entry_count)]
        return core.prepare_saved_group(source, entries, completion_request_ref=request_ref(), block_size=1)

    def test_saved_stream_interruption_releases_new_group_without_gc(self):
        was = gc.isenabled()
        gc.disable()
        try:
            group = self.fresh_group()
            reference = weakref.ref(group)
            actual = streaming._scalar_bytes
            calls = 0
            def interrupted(value):
                nonlocal calls
                try:
                    calls += 1
                    if calls == 20:
                        raise KeyboardInterrupt("synthetic canonical stream interruption")
                    return actual(value)
                finally:
                    value = None
            gen = streaming.iter_catalog_json(group, chunk_bytes=17)
            with patch.object(streaming, "_scalar_bytes", new=interrupted):
                try:
                    list(gen)
                except KeyboardInterrupt as exc:
                    error = exc
                else:
                    self.fail("expected stream interruption")
            self.assertIsNone(gen.gi_frame)
            group = gen = None
            self.assertIsNone(reference())
            frame = error.__traceback__
            checked = 0
            while frame is not None:
                name = frame.tb_frame.f_code.co_name
                locals_ = frame.tb_frame.f_locals
                if name == "iter_catalog_json":
                    checked += 1
                    self.assertIsNone(locals_["prepared"])
                    self.assertIsNone(locals_["state"])
                if name == "_pack_chunks":
                    self.assertEqual(locals_["buffer"], bytearray())
                    self.assertIsNone(locals_["fragments"])
                if name == "_catalog_fragments":
                    self.assertIsNone(locals_["catalog"])
                    self.assertIsNone(locals_["payload"])
                    self.assertIsNone(locals_["raw"])
                frame = frame.tb_next
            self.assertEqual(checked, 1)
        finally:
            if was: gc.enable()

    def test_saved_task_binding_error_releases_new_group_without_gc(self):
        was = gc.isenabled()
        gc.disable()
        try:
            group = self.fresh_group()
            reference = weakref.ref(group)
            task = replace(next(group.iter_blocks()), source_sha256="0" * 64)
            try:
                streaming.task_stream_bound(group, task)
            except ValueError as exc:
                error = exc
            else:
                self.fail("expected invalid task")
            group = None
            self.assertIsNone(reference())
            self.assertIsNotNone(error.__traceback__)
        finally:
            if was: gc.enable()

    def test_stream_iteration_work_reserved_including_repeated_measurement(self):
        for action, info_action, owner in ((streaming.iter_source_json, streaming.source_stream_info, self.groups["passing"][0]),
                (streaming.iter_catalog_json, streaming.catalog_stream_info, self.groups["passing"][1])):
            info = info_action(owner)
            self.assertEqual(info["iteration_work_upper_bound"], info["planning_work"] + info["serialization_work_upper_bound"])
            self.assertGreater(info["iteration_work_upper_bound"], info["canonical_byte_upper_bound"])
            with patch.object(streaming, "_pack_chunks", side_effect=AssertionError("no prefix before full stream-work reservation")):
                with self.assertRaises(streaming.StreamHold):
                    next(action(owner, max_work=info["iteration_work_upper_bound"] - 1))


if __name__ == "__main__":
    unittest.main()
