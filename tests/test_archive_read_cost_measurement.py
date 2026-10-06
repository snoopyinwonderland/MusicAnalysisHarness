"""Small byte streams only; no corpus, JSON body parser or native producers."""
from __future__ import annotations

from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import archive_read_cost_measurement as cost
from musicanote_harness import cross_batch_read_budget as read_budget


class ArchiveReadCostControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.archive = self.root / "archive"
        self.archive.mkdir()
        self.registered, self.inputs = {}, []
        self.denominators = {"original_contexts": 322, "original_completion_requests": 4,
            "original_selectors": 8050, "selected": None}

    def source(self, name, raw=b"", *, compressed=False, physical=None):
        stored = physical if physical is not None else gzip.compress(raw, mtime=0) if compressed else raw
        path = self.archive / name
        path.write_bytes(stored)
        sha = hashlib.sha256(stored).hexdigest()
        self.registered[str(path)] = sha
        item = cost.MeasurementInput("occurrence-" + str(len(self.inputs)), str(path), sha,
            "gzip" if compressed else "raw")
        self.inputs.append(item)
        return item

    def plan(self, inputs=None, **options):
        return cost.plan_measurement_phase(self.inputs if inputs is None else inputs,
            phase_id=options.pop("phase_id", "metadata-and-one-original-completion"),
            logical_run_id="declared-measurement-run", original_denominators=self.denominators,
            registered_sha256=self.registered,
            inventory_roots=(cost.InventoryRoot(str(self.archive), self.registered),), **options)

    def consume(self, plan):
        session = cost.begin_measurements(plan)
        for item in plan.record()["inputs"]:
            cost.measure_next(session, item["measurement_id"])
        return session, cost.finish_measurements(session)

    def test_raw_and_multimember_gzip_measured_without_JSON_parse(self):
        raw = b'{"x":NaN,"x":Infinity}\xff'
        first = self.source("invalid-json.bin", raw)
        member1, member2 = b"arbitrary bytes\xff", b"\x00not JSON"
        second = self.source("multi.bin.gz", compressed=True,
            physical=gzip.compress(member1, mtime=0) + gzip.compress(member2, mtime=0))
        with patch.object(cost.json, "loads", side_effect=AssertionError("no JSON parsing")), \
                patch.object(read_budget, "begin_reads", side_effect=AssertionError("no reader admission")):
            plan = self.plan()
            session, receipt = self.consume(plan)
            result = receipt.record()
        self.assertTrue(result["phase_complete"])
        self.assertEqual(result["measured_complete_phase_decoded_bytes"], len(raw) + len(member1) + len(member2))
        self.assertEqual(result["observations"][0]["decoded_bytes"], len(raw))
        self.assertEqual(result["observations"][1]["decoded_bytes"], len(member1) + len(member2))
        self.assertEqual(result["observations"][1]["decoded_sha256"], hashlib.sha256(member1 + member2).hexdigest())
        self.assertTrue(all(o["same_open_before_after_SHA_verified"] for o in result["observations"]))
        self.assertFalse(any(result["flags"].values()))
        self.assertTrue(result["later_parser_reads_are_separate_charged_work"])
        self.assertEqual(result["original_denominators"], self.denominators)

    def test_repeated_files_are_occurrences_and_charged_again(self):
        item = self.source("same.gz", b"0123456789", compressed=True)
        repeat = replace(item, measurement_id="repeated-occurrence")
        plan = self.plan([item, repeat])
        self.assertEqual(plan.record()["planned_occurrences"], 2)
        self.assertEqual(plan.record()["planned_unique_files"], 1)
        session, receipt = self.consume(plan)
        result = receipt.record()
        self.assertEqual(result["decoded_attempt_bytes"], 20)
        self.assertEqual(result["physical_attempt_bytes"], 2 * Path(item.path).stat().st_size)
        self.assertGreater(result["hash_verification_attempt_bytes"], result["physical_attempt_bytes"])
        self.assertFalse(result["physical_hash_checks_consume_decoded_budget"])

    def test_unknown_zero_empty_and_missing_are_distinct(self):
        item = self.source("zero", b"")
        plan = self.plan()
        self.assertEqual(plan.record()["unknown_decoded_occurrences"], 1)
        self.assertIsNone(plan.record()["decoded_byte_reservation"])
        session, receipt = self.consume(plan)
        result = receipt.record()
        self.assertFalse(result["known_empty_measurement_set"])
        self.assertEqual(result["observations"][0]["decoded_bytes"], 0)
        self.assertEqual(result["decoded_attempt_bytes"], 0)
        empty = self.plan([])
        _, empty_receipt = self.consume(empty)
        self.assertTrue(empty_receipt.record()["known_empty_measurement_set"])
        Path(item.path).unlink()
        held = self.plan()
        self.assertEqual(held.record()["status"], "whole_measurement_hold")
        with self.assertRaises(cost.WholeMeasurementHold) as exc:
            cost.begin_measurements(held)
        self.assertEqual(exc.exception.plan["planned_occurrences"], 1)
        self.assertEqual(exc.exception.plan["original_denominators"], self.denominators)

    def test_phase_cap_failure_preserves_prefix_failure_and_remaining_no_reset(self):
        a = self.source("a", b"123456")
        b = self.source("b", b"123456")
        c = self.source("c", b"last")
        plan = self.plan(limits=cost.MeasurementLimits(max_phase_decoded_bytes=10))
        session = cost.begin_measurements(plan)
        cost.measure_next(session, a.measurement_id)
        with self.assertRaises(cost.MeasurementFailure) as exc:
            cost.measure_next(session, b.measurement_id)
        self.assertEqual(exc.exception.ledger["decoded_bytes_returned_lower_bound"], 11)
        receipt = cost.finish_measurements(session)
        result = receipt.record()
        self.assertFalse(result["phase_complete"])
        self.assertIsNone(result["measured_complete_phase_decoded_bytes"])
        self.assertEqual(result["completed_occurrences"], 1)
        self.assertEqual(result["failed_occurrences"], 1)
        self.assertEqual(result["never_attempted_occurrences"], 1)
        self.assertEqual(result["remaining_measurement_ids"], [b.measurement_id, c.measurement_id])
        self.assertEqual(result["never_attempted_measurement_ids"], [c.measurement_id])
        with self.assertRaises(ValueError):
            cost.measure_next(session, c.measurement_id)
        with self.assertRaisesRegex(ValueError, "no_restart"):
            cost.begin_measurements(plan)

    def test_gzip_decoded_cap_and_corruption_keep_unknown_not_false_zero(self):
        item = self.source("big.gz", b"a" * 100, compressed=True)
        plan = self.plan(limits=cost.MeasurementLimits(max_decoded_file_bytes=12))
        session = cost.begin_measurements(plan)
        with self.assertRaises(cost.MeasurementFailure):
            cost.measure_next(session, item.measurement_id)
        result = cost.finish_measurements(session).record()
        self.assertEqual(result["decoded_bytes_returned_lower_bound"], 13)
        self.assertIsNone(result["decoded_attempt_bytes"])
        self.assertIsNone(result["observations"][0]["decoded_bytes"])
        self.assertFalse(result["phase_complete"])

    def test_invalid_gzip_and_stream_interrupt_are_charged_and_terminal(self):
        item = self.source("invalid.gz", compressed=True, physical=b"not a gzip stream")
        session = cost.begin_measurements(self.plan())
        with self.assertRaises(cost.MeasurementFailure):
            cost.measure_next(session, item.measurement_id)
        result = cost.finish_measurements(session).record()
        self.assertIsNone(result["decoded_attempt_bytes"])
        self.assertGreater(result["physical_bytes_returned_lower_bound"], 0)
        self.assertEqual(result["attempted_occurrences"], 1)
        self.assertEqual(result["completed_occurrences"], 0)
        self.assertEqual(result["remaining_measurement_ids"], [item.measurement_id])

    def test_small_stream_exception_unknown_and_postfailure_guards(self):
        item = self.source("raw", b"abcdef")
        session = cost.begin_measurements(self.plan())
        original = cost._PhysicalStream.read
        calls = []
        def interrupted(stream, size=-1):
            calls.append(size)
            if len(calls) == 1:
                return original(stream, 2)
            raise KeyboardInterrupt("interrupted after internal decoding")
        with patch.object(cost._PhysicalStream, "read", interrupted):
            with self.assertRaises(cost.MeasurementFailure):
                cost.measure_next(session, item.measurement_id)
        result = cost.finish_measurements(session).record()
        self.assertEqual(result["decoded_bytes_returned_lower_bound"], 2)
        self.assertIsNone(result["decoded_attempt_bytes"])
        self.assertEqual(result["physical_bytes_returned_lower_bound"], 2)
        self.assertIn("KeyboardInterrupt", result["observations"][0]["error"])

    def test_plan_physical_and_count_limits_hold_whole_before_decode(self):
        item = self.source("raw", b"12345")
        for limits in (cost.MeasurementLimits(max_file_bytes=4),
                cost.MeasurementLimits(max_measurement_occurrences=0),
                cost.MeasurementLimits(max_registered_files=1),
                cost.MeasurementLimits(max_inventory_roots=0)):
            with self.subTest(limits=limits):
                with patch.object(cost._PhysicalStream, "read", side_effect=AssertionError("no decode")):
                    plan = self.plan(limits=limits)
                    with self.assertRaises(cost.WholeMeasurementHold):
                        cost.begin_measurements(plan)
                self.assertEqual(plan.record()["planned_occurrences"], 1)
                self.assertEqual(plan.record()["original_denominators"], self.denominators)

    def test_owned_handles_and_no_skip_reorder_duplicate(self):
        a = self.source("a", b"a")
        b = self.source("b", b"b")
        plan = self.plan()
        session = cost.begin_measurements(plan)
        for identity in (True, b.measurement_id, "foreign"):
            with self.assertRaises(ValueError):
                cost.measure_next(session, identity)
        self.assertEqual(session.record()["attempted_occurrences"], 0)
        cost.measure_next(session, a.measurement_id)
        with self.assertRaises(ValueError):
            cost.measure_next(session, a.measurement_id)
        for cls in (cost.MeasurementPlan, cost.MeasurementSession, cost.MeasurementReceipt):
            with self.assertRaises(ValueError):
                cls()
        with self.assertRaises(ValueError):
            cost.begin_measurements(object.__new__(cost.MeasurementPlan))
        with self.assertRaises(ValueError):
            cost.finish_measurements(object.__new__(cost.MeasurementSession))
        with self.assertRaises(ValueError):
            object.__new__(cost.MeasurementReceipt).record()

    def test_exact_root_and_hash_changes_at_plan_begin_and_finish(self):
        item = self.source("body", b"123")
        extra = self.archive / "extra"
        extra.write_bytes(b"not registered")
        held = self.plan()
        self.assertIn("exact_registered_inventory_changed:" + str(self.archive), held.record()["reasons"])
        extra.unlink()
        plan = self.plan()
        Path(item.path).write_bytes(b"changed")
        with self.assertRaises(cost.MeasurementFailure) as exc:
            cost.begin_measurements(plan)
        self.assertEqual(exc.exception.ledger["attempted_occurrences"], 0)
        self.assertFalse(cost.finish_measurements(exc.exception.session).record()["phase_complete"])

    def test_finish_rechecks_other_registered_file_and_inventory(self):
        item = self.source("body", b"123")
        other = self.source("other", b"abc")
        session = cost.begin_measurements(self.plan([item]))
        cost.measure_next(session, item.measurement_id)
        Path(other.path).write_bytes(b"xyz")
        result = cost.finish_measurements(session).record()
        self.assertEqual(result["completed_occurrences"], 1)
        self.assertFalse(result["phase_complete"])
        self.assertIsNone(result["measured_complete_phase_decoded_bytes"])
        self.assertIn("registered_physical_SHA_changed:" + other.path, result["reasons"])

    def test_target_mutation_during_stream_fails_without_refunding_decoded_bytes(self):
        item = self.source("body", b"123")
        session = cost.begin_measurements(self.plan())
        original = cost._PhysicalStream.read
        def changed(stream, size=-1):
            block = original(stream, size)
            if block:
                Path(item.path).write_bytes(b"xyz")
            return block
        with patch.object(cost._PhysicalStream, "read", changed):
            with self.assertRaises(cost.MeasurementFailure):
                cost.measure_next(session, item.measurement_id)
        result = cost.finish_measurements(session).record()
        self.assertEqual(result["decoded_bytes_returned_lower_bound"], 3)
        self.assertFalse(result["phase_complete"])
        self.assertIsNone(result["observations"][0]["decoded_bytes"])

    def test_terminal_receipt_immutable_no_late_promotion_and_exchange_self_seal(self):
        a = self.source("a", b"a")
        b = self.source("b", b"b")
        plan = self.plan()
        session = cost.begin_measurements(plan)
        cost.measure_next(session, a.measurement_id)
        receipt = cost.finish_measurements(session)
        self.assertIs(receipt, cost.finish_measurements(session))
        before = receipt.record()
        exported = receipt.record()
        exported["remaining_measurement_ids"].clear()
        exported["observations"][0]["decoded_bytes"] = 999
        self.assertEqual(receipt.record(), before)
        self.assertFalse(before["phase_complete"])
        with self.assertRaises(ValueError):
            cost.measure_next(session, b.measurement_id)
        self.assertEqual(receipt.record(), before)
        exchange = json.loads(receipt.json_bytes())
        ref = exchange.pop("receipt_ref")
        self.assertEqual(ref, "mcreceipt_" + cost._digest(exchange))
        with self.assertRaises(AttributeError):
            receipt.note = "changed"

    def test_finished_receipt_is_historical_snapshot_later_reader_rechecks_source(self):
        item = self.source("body.json", b'{"x":1}')
        session, receipt = self.consume(self.plan())
        before = receipt.record()
        Path(item.path).write_bytes(b'{"x":2}')
        self.assertIs(receipt, cost.finish_measurements(session))
        self.assertEqual(receipt.record(), before)
        observation = before["observations"][0]
        parser_plan = read_budget.plan_read_run([
            read_budget.ReadInput("later-parser-read", item.path, item.expected_sha256,
                observation["physical_bytes"], observation["decoded_bytes"], "json", "body")],
            original_denominators=self.denominators, registered_sha256=self.registered,
            inventory_roots=(read_budget.InventoryRoot(str(self.archive), self.registered),))
        self.assertEqual(parser_plan.record()["status"], "whole_read_hold")
        with self.assertRaises(read_budget.WholeReadHold):
            read_budget.begin_reads(parser_plan)

    def test_caller_mutation_does_not_shrink_frozen_scope_or_registered_closure(self):
        a = self.source("a", b"abc")
        b = self.source("b", b"def")
        plan = self.plan()
        self.inputs.clear()
        self.registered.clear()
        exported = plan.record()
        exported["inputs"].clear()
        exported["registered_sha256"].clear()
        session, receipt = self.consume(plan)
        self.assertTrue(receipt.record()["phase_complete"])
        self.assertEqual(receipt.record()["planned_measurement_ids"], [a.measurement_id, b.measurement_id])
        self.assertEqual(receipt.record()["decoded_attempt_bytes"], 6)

    def test_decoding_is_bounded_streaming_no_body_retention_or_peak_RSS_claim(self):
        raw = b"x" * (2 * 1048576 + 17)
        self.source("large.gz", raw, compressed=True)
        session, receipt = self.consume(self.plan())
        result = receipt.record()
        self.assertEqual(result["measured_complete_phase_decoded_bytes"], len(raw))
        self.assertLessEqual(result["maximum_returned_decoded_block_bytes"], 1048576)
        self.assertFalse(result["streamed_payload_retained_for_JSON"])
        self.assertIsNone(result["process_peak_memory_bytes"])
        self.assertEqual(type(result["elapsed_nanoseconds"]), int)
        self.assertGreaterEqual(result["elapsed_nanoseconds"], 0)

    def test_declaration_types_registration_roots_and_output_placement(self):
        item = self.source("body", b"x")
        for value in (True, 1.0, -1):
            with self.assertRaises(ValueError):
                cost.MeasurementLimits(max_phase_decoded_bytes=value)
        with self.assertRaises(ValueError):
            self.plan([replace(item, expected_sha256="0" * 64)])
        with self.assertRaises(ValueError):
            self.plan([replace(item, encoding="json")])
        with self.assertRaises(ValueError):
            self.plan([item, item])
        with self.assertRaises(ValueError):
            self.plan(output_directory=str(self.archive / "reviews"))
        with self.assertRaises(ValueError):
            self.plan(source_archive_roots=(str(self.root),), output_directory=str(self.root / "reports"))
        okay = self.plan(output_directory=str(self.root / "reports"))
        self.assertEqual(okay.record()["output_directory"], str(self.root / "reports"))

    def test_explicit_phases_aggregate_without_forging_reset_or_archive_success(self):
        a = self.source("a", b"123")
        b = self.source("b.gz", b"4567", compressed=True)
        _, ra = self.consume(self.plan([a], phase_id="metadata"))
        _, rb = self.consume(self.plan([b], phase_id="one-original-request"))
        result = cost.aggregate_measurements([ra, rb], logical_run_id="declared-measurement-run",
            original_denominators=self.denominators, expected_phase_ids=["metadata", "one-original-request"],
            expected_measurement_ids=[a.measurement_id, b.measurement_id])
        self.assertTrue(result["all_declared_measurement_phases_complete"])
        self.assertEqual(result["measured_complete_logical_decoded_bytes"], 7)
        self.assertEqual(result["default_parser_total_decoded_limit"], 1073741824)
        self.assertTrue(result["same_parser_read_run_may_not_reset_budget_per_measurement_phase"])
        self.assertFalse(any(result["flags"].values()))
        incomplete = cost.aggregate_measurements([ra], logical_run_id="declared-measurement-run",
            original_denominators=self.denominators, expected_phase_ids=["metadata", "one-original-request"],
            expected_measurement_ids=[a.measurement_id, b.measurement_id])
        self.assertFalse(incomplete["all_declared_measurement_phases_complete"])
        self.assertIsNone(incomplete["measured_complete_logical_decoded_bytes"])
        self.assertEqual(incomplete["missing_measurement_ids"], [b.measurement_id])
        with self.assertRaises(ValueError):
            cost.aggregate_measurements([ra, ra], logical_run_id="declared-measurement-run",
                original_denominators=self.denominators, expected_phase_ids=["metadata"],
                expected_measurement_ids=[a.measurement_id])
        with self.assertRaises(ValueError):
            cost.aggregate_measurements([ra.record()], logical_run_id="declared-measurement-run",
                original_denominators=self.denominators, expected_phase_ids=["metadata"],
                expected_measurement_ids=[a.measurement_id])

    def test_failed_phase_or_reorder_does_not_aggregate_to_complete(self):
        a = self.source("a", b"123")
        b = self.source("b", b"123")
        _, ra = self.consume(self.plan([a], phase_id="phase-a"))
        session = cost.begin_measurements(self.plan([b], phase_id="phase-b",
            limits=cost.MeasurementLimits(max_phase_decoded_bytes=2)))
        with self.assertRaises(cost.MeasurementFailure):
            cost.measure_next(session, b.measurement_id)
        rb = cost.finish_measurements(session)
        for receipts in ([ra, rb], [rb, ra]):
            result = cost.aggregate_measurements(receipts, logical_run_id="declared-measurement-run",
                original_denominators=self.denominators, expected_phase_ids=["phase-a", "phase-b"],
                expected_measurement_ids=[a.measurement_id, b.measurement_id])
            self.assertFalse(result["all_declared_measurement_phases_complete"])
            self.assertEqual(result["decoded_bytes_returned_lower_bound"], 6)
            self.assertIsNone(result["measured_complete_logical_decoded_bytes"])

    def test_initial_and_terminal_guard_interrupts_cannot_hide_unknown_cost(self):
        self.source("raw", b"x")
        plan = self.plan()
        with patch.object(cost, "_guards", side_effect=KeyboardInterrupt("guard interrupted")):
            with self.assertRaises(cost.MeasurementFailure) as exc:
                cost.begin_measurements(plan)
            receipt = cost.finish_measurements(exc.exception.session)
        result = receipt.record()
        self.assertFalse(result["phase_complete"])
        self.assertIsNone(result["hash_verification_attempt_bytes"])
        self.assertEqual(result["never_attempted_occurrences"], 1)
        self.assertEqual(result["original_denominators"], self.denominators)

    def test_current_code_guard_is_separate_from_historical_input_closure(self):
        item = self.source("raw", b"x")
        plan = self.plan()
        code = plan.record()["code_path"]
        self.assertNotIn(code, self.registered)
        self.assertIn(code, plan.record()["registered_sha256"])
        self.assertEqual(plan.record()["code_sha256"], hashlib.sha256(Path(code).read_bytes()).hexdigest())
        self.assertEqual(plan.record()["exact_inventory_roots"][0]["registered_sha256"], self.registered)


if __name__ == "__main__":
    unittest.main()
