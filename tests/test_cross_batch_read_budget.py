"""Small physical JSON/gzip controls; no corpus or musical-accuracy run."""
from __future__ import annotations

from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_read_budget as budget


class CumulativeReadBudgetControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.archive = self.root / "archive"
        self.archive.mkdir()
        self.registered = {}
        self.reads = []
        self.denominators = {"original_contexts": 322, "completion_requests": 4,
            "planned_entries": 8050, "planned_pairs": 1652640, "selected": None}

    def source(self, name, value=None, *, raw=None, compressed=False, phase="body"):
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode() if raw is None else raw
        physical = gzip.compress(raw, mtime=0) if compressed else raw
        path = self.archive / name
        path.write_bytes(physical)
        sha = hashlib.sha256(physical).hexdigest()
        self.registered[str(path)] = sha
        result = budget.ReadInput("read-" + str(len(self.reads)), str(path), sha,
            len(physical), len(raw), "gzip-json" if compressed else "json", phase)
        self.reads.append(result)
        return result

    def plan(self, *, reads=None, limits=None, roots=True, **extra):
        return budget.plan_read_run(self.reads if reads is None else reads,
            original_denominators=self.denominators, registered_sha256=self.registered,
            inventory_roots=(budget.InventoryRoot(str(self.archive), self.registered),) if roots else (),
            limits=limits, **extra)

    def test_metadata_and_bodies_share_account_repeats_charge_again(self):
        first = self.source("metadata.json", {"elapsed": 1.25}, phase="metadata")
        second = self.source("body.json.gz", {"duration": {"n": 1, "d": 3}}, compressed=True)
        repeat = replace(first, read_id="repeated-metadata")
        plan = self.plan(reads=[first, second, repeat])
        expected = 2 * first.decoded_bytes + second.decoded_bytes
        self.assertEqual(plan.record()["planned_decoded_bytes"], expected)
        self.assertEqual(plan.record()["planned_unique_read_files"], 2)
        reader = budget.begin_reads(plan)
        self.assertEqual(reader.read(first.path), {"elapsed": 1.25})
        self.assertEqual(budget.read_record(reader, second.read_id), {"duration": {"n": 1, "d": 3}})
        self.assertEqual(reader.read(first.path), {"elapsed": 1.25})
        self.assertFalse(budget.read_ledger(reader)["submitted_read_set_complete"])
        final = budget.finish_reads(reader)
        self.assertTrue(final["submitted_read_set_complete"])
        self.assertEqual(final["decoded_attempt_bytes"], expected)
        self.assertEqual(final["body_physical_bytes_returned_lower_bound"],
            2 * first.physical_bytes + second.physical_bytes)
        self.assertEqual(reader.decoded_bytes, expected)
        self.assertEqual(reader.read_files, 3)
        self.assertFalse(any(final["flags"].values()))
        self.assertFalse(final["physical_hash_checks_consume_decoded_budget"])
        self.assertGreater(final["hash_verification_bytes_returned_lower_bound"], expected)

    def test_cumulative_cap_whole_hold_before_parse_preserves_denominators(self):
        first = self.source("one.json", {"one": 1})
        second = self.source("two.json.gz", {"two": 2}, compressed=True)
        limits = budget.ReadLimits(max_total_decoded_bytes=first.decoded_bytes + second.decoded_bytes - 1)
        with patch.object(budget.json, "loads", side_effect=AssertionError("no parsing")):
            plan = self.plan(limits=limits)
        self.assertEqual(plan.record()["status"], "whole_read_hold")
        self.assertIn("whole_cumulative_decoded_limit_no_prefix", plan.record()["reasons"])
        self.assertEqual(plan.record()["original_denominators"], self.denominators)
        self.assertEqual(plan.record()["planned_read_occurrences"], 2)
        with self.assertRaises(budget.WholeReadHold) as held:
            budget.begin_reads(plan)
        self.assertEqual(held.exception.plan["planned_decoded_bytes"], first.decoded_bytes + second.decoded_bytes)

    def test_repeated_paths_not_deduplicated_for_cap(self):
        item = self.source("same.json", {"n": 1})
        duplicate = replace(item, read_id="second-occurrence")
        plan = self.plan(reads=[item, duplicate],
            limits=budget.ReadLimits(max_total_decoded_bytes=item.decoded_bytes))
        self.assertEqual(plan.record()["planned_decoded_bytes"], 2 * item.decoded_bytes)
        self.assertEqual(plan.record()["status"], "whole_read_hold")

    def test_unknown_missing_and_known_zero_are_not_equivalent(self):
        item = self.source("zero.json", raw=b"")
        zero = self.plan()
        self.assertEqual(zero.record()["planned_decoded_bytes"], 0)
        self.assertFalse(zero.record()["known_empty_read_set"])
        reader = budget.begin_reads(zero)
        with self.assertRaises(budget.ReadFailure):
            reader.read(item.path)  # zero physical bytes are not valid JSON.
        self.assertEqual(budget.read_ledger(reader)["decoded_attempt_bytes"], 0)
        unknown = self.plan(reads=[replace(item, decoded_bytes=None)])
        self.assertIsNone(unknown.record()["planned_decoded_bytes"])
        self.assertEqual(unknown.record()["unknown_decoded_occurrences"], 1)
        Path(item.path).unlink()
        missing = self.plan()
        self.assertIn("missing_or_symlink_registered_body_no_prefix", missing.record()["reasons"])
        self.assertEqual(missing.record()["planned_read_occurrences"], 1)

    def test_known_empty_plan_completes_only_submitted_read_scope(self):
        plan = self.plan(reads=[])
        reader = budget.begin_reads(plan)
        final = budget.finish_reads(reader)
        self.assertTrue(final["known_empty_read_set"])
        self.assertTrue(final["submitted_read_set_complete"])
        self.assertEqual(final["decoded_attempt_bytes"], 0)
        self.assertFalse(any(final["flags"].values()))
        self.assertEqual(final["original_denominators"], self.denominators)

    def test_single_owned_account_cannot_restart_reset_or_be_forged(self):
        item = self.source("small.json", [1])
        plan = self.plan()
        reader = budget.begin_reads(plan)
        with self.assertRaisesRegex(ValueError, "one_cumulative_account"):
            budget.begin_reads(plan)
        with self.assertRaises(ValueError):
            budget.ReadPlan()
        with self.assertRaises(ValueError):
            budget.RegisteredReader()
        with self.assertRaises(ValueError):
            budget.begin_reads(object.__new__(budget.ReadPlan))
        with self.assertRaises(ValueError):
            budget.read_ledger(object.__new__(budget.RegisteredReader))
        reader.read(item.path)
        with self.assertRaises(ValueError):
            reader.read(item.path)

    def test_no_reorder_skip_duplicate_or_foreign_occurrence(self):
        a = self.source("a.json", [1])
        b = self.source("b.json", [2])
        reader = budget.begin_reads(self.plan())
        for read_id in (b.read_id, "foreign", True):
            with self.assertRaises(ValueError):
                budget.read_record(reader, read_id)
        with self.assertRaises(ValueError):
            reader.read(b.path)
        self.assertEqual(budget.read_ledger(reader)["attempted_read_occurrences"], 0)
        reader.read(a.path)
        with self.assertRaises(ValueError):
            budget.read_record(reader, a.read_id)
        final = budget.finish_reads(reader)
        self.assertFalse(final["submitted_read_set_complete"])
        self.assertEqual(final["never_attempted_read_occurrences"], 1)
        with self.assertRaises(ValueError):
            reader.read(b.path)

    def test_registration_not_arbitrary_label_or_foreign_map(self):
        item = self.source("registered.json", [1])
        with self.assertRaisesRegex(ValueError, "registered_physical_SHA_membership"):
            self.plan(reads=[replace(item, sha256="0" * 64)])
        with self.assertRaisesRegex(ValueError, "inventory_membership"):
            budget.plan_read_run(self.reads, original_denominators={}, registered_sha256=self.registered,
                inventory_roots=(budget.InventoryRoot(str(self.archive), {item.path: "0" * 64}),))
        with self.assertRaisesRegex(ValueError, "unique_original"):
            self.plan(reads=[item, item])
        with self.assertRaisesRegex(ValueError, "consistent_byte"):
            self.plan(reads=[item, replace(item, read_id="r2", decoded_bytes=item.decoded_bytes + 1)])

    def test_plain_exact_typed_declarations_and_limits(self):
        item = self.source("x.json", [1])
        for bad in (True, -1, 1.5):
            with self.assertRaises(ValueError):
                self.plan(reads=[replace(item, decoded_bytes=bad)])
            with self.assertRaises(ValueError):
                budget.ReadLimits(max_total_decoded_bytes=bad)
        self.denominators["elapsed"] = 1.2
        with self.assertRaises(ValueError):
            self.plan()

    def test_caller_declaration_and_record_copies_do_not_mutate_plan(self):
        item = self.source("fixed.json", [1])
        plan = self.plan()
        self.registered.clear()
        self.denominators["planned_entries"] = 1
        edited = plan.record()
        edited["reads"].clear()
        self.assertEqual(plan.record()["planned_read_occurrences"], 1)
        self.assertEqual(plan.record()["original_denominators"]["planned_entries"], 8050)
        reader = budget.begin_reads(plan)
        reader.read(item.path)
        self.assertTrue(budget.finish_reads(reader)["submitted_read_set_complete"])

    def test_file_caps_and_physical_size_mismatch_hold_before_parse(self):
        item = self.source("data.json.gz", [1, 2], compressed=True)
        physical = self.plan(limits=budget.ReadLimits(max_file_bytes=item.physical_bytes - 1))
        decoded = self.plan(limits=budget.ReadLimits(max_decoded_file_bytes=item.decoded_bytes - 1))
        mismatch = self.plan(reads=[replace(item, physical_bytes=item.physical_bytes + 1)])
        self.assertIn("whole_physical_file_limit_no_prefix", physical.record()["reasons"])
        self.assertIn("whole_decoded_file_limit_no_prefix", decoded.record()["reasons"])
        self.assertIn("declared_physical_size_mismatch_no_prefix", mismatch.record()["reasons"])

    def test_count_cap_holds_original_ordered_denominators(self):
        self.source("one.json", 1)
        plan = self.plan(limits=budget.ReadLimits(max_read_occurrences=0))
        self.assertEqual(plan.record()["planned_read_occurrences"], 1)
        self.assertIn("whole_registered_inventory_count_limit_no_prefix", plan.record()["reasons"])

    def test_registered_count_includes_fixed_current_code(self):
        plan = self.plan(reads=[], limits=budget.ReadLimits(max_registered_files=0))
        self.assertIn("whole_registered_inventory_count_limit_no_prefix", plan.record()["reasons"])

    def test_actual_decode_over_bound_charged_before_no_partial_parse(self):
        item = self.source("over.json.gz", {"abc": 42}, compressed=True)
        reader = budget.begin_reads(self.plan(reads=[replace(item, decoded_bytes=3)]))
        with self.assertRaises(budget.ReadFailure) as failed:
            reader.read(item.path)
        final = failed.exception.ledger
        self.assertEqual(final["decoded_attempt_bytes"], 4)
        self.assertFalse(final["attempts"][0]["JSON_parse_attempted"])
        self.assertIsNotNone(final["attempts"][0]["decoded_prefix_sha256"])
        self.assertFalse(final["submitted_read_set_complete"])
        with self.assertRaises(ValueError):
            reader.read(item.path)

    def test_actual_decode_under_bound_is_not_a_successful_prefix(self):
        item = self.source("under.json", [1])
        reader = budget.begin_reads(self.plan(reads=[replace(item, decoded_bytes=item.decoded_bytes + 1)]))
        with self.assertRaises(budget.ReadFailure):
            reader.read(item.path)
        ledger = budget.finish_reads(reader)
        self.assertEqual(ledger["decoded_attempt_bytes"], item.decoded_bytes)
        self.assertEqual(ledger["completed_read_occurrences"], 0)
        self.assertFalse(ledger["attempts"][0]["JSON_parse_attempted"])

    def test_concatenated_gzip_members_use_actual_stream_not_last_ISIZE(self):
        raw = b'{"n":2}'
        physical = gzip.compress(raw[:5], mtime=0) + gzip.compress(raw[5:], mtime=0)
        item = self.source("members.json.gz", raw=raw)
        Path(item.path).write_bytes(physical)
        sha = hashlib.sha256(physical).hexdigest()
        self.registered[item.path] = sha
        item = replace(item, sha256=sha, physical_bytes=len(physical), encoding="gzip-json")
        reader = budget.begin_reads(self.plan(reads=[item]))
        self.assertEqual(reader.read(item.path), {"n": 2})
        self.assertEqual(budget.finish_reads(reader)["decoded_attempt_bytes"], len(raw))

    def test_stream_failure_unknown_attempt_bytes_and_no_refund(self):
        a = self.source("first.json", [1])
        b = self.source("second.json.gz", [2], compressed=True)
        reader = budget.begin_reads(self.plan())
        reader.read(a.path)
        with patch.object(budget._PhysicalStream, "read", side_effect=OSError("decode IO")):
            with self.assertRaises(budget.ReadFailure) as failed:
                reader.read(b.path)
        ledger = failed.exception.ledger
        self.assertIsNone(ledger["decoded_attempt_bytes"])
        self.assertEqual(ledger["decoded_bytes_returned_lower_bound"], a.decoded_bytes)
        self.assertEqual(ledger["completed_read_occurrences"], 1)
        self.assertEqual(ledger["failed_read_occurrences"], 1)
        self.assertTrue(ledger["attempts"][1]["decoded_bytes_unconfirmed"])
        self.assertFalse(budget.finish_reads(reader)["submitted_read_set_complete"])

    def test_invalid_UTF8_duplicate_keys_nonfinite_and_float_overflow(self):
        for index, raw in enumerate((b"\xff", b'{"a":1,"a":2}', b"NaN", b"Infinity", b"1e400")):
            with self.subTest(raw=raw):
                item = self.source(str(index) + ".json", raw=raw)
                reader = budget.begin_reads(self.plan(reads=[item]))
                with self.assertRaises(budget.ReadFailure):
                    reader.read(item.path)
                ledger = budget.read_ledger(reader)
                self.assertEqual(ledger["decoded_attempt_bytes"], len(raw))
                self.assertEqual(ledger["completed_read_occurrences"], 0)

    def test_pre_read_and_finish_inventory_and_SHA_guards(self):
        item = self.source("guarded.json", [1])
        plan = self.plan()
        reader = budget.begin_reads(plan)
        extra = self.archive / "foreign.txt"
        extra.write_bytes(b"x")
        reader.read(item.path)
        self.assertFalse(budget.finish_reads(reader)["submitted_read_set_complete"])
        self.assertIn("exact_registered_inventory_changed:" + str(self.archive),
            budget.read_ledger(reader)["reasons"])
        extra.unlink()
        reader = budget.begin_reads(self.plan())
        reader.read(item.path)
        self.assertTrue(budget.finish_reads(reader)["submitted_read_set_complete"])
        Path(item.path).write_bytes(b"[2]")
        self.assertFalse(budget.finish_reads(reader)["submitted_read_set_complete"])

    def test_non_target_mutation_is_detected_at_terminal_not_rehashed_each_read(self):
        a = self.source("one.json", [1])
        b = self.source("two.json", [2])
        reader = budget.begin_reads(self.plan(reads=[a]))
        Path(b.path).write_bytes(b"[3]")
        with patch.object(budget, "_guards", wraps=budget._guards) as guards:
            reader.read(a.path)
            self.assertTrue(all(call.kwargs.get("inventories") is False for call in guards.call_args_list))
            self.assertTrue(all(set(call.kwargs["paths"]) == {a.path, str(Path(budget.__file__).resolve())}
                for call in guards.call_args_list))
        self.assertFalse(budget.finish_reads(reader)["submitted_read_set_complete"])

    def test_terminal_guard_interrupt_preserves_unknown_and_terminal_state(self):
        item = self.source("guard-interrupt.json", [1])
        reader = budget.begin_reads(self.plan())
        reader.read(item.path)
        with patch.object(budget, "_hash_stream", side_effect=KeyboardInterrupt()):
            final = budget.finish_reads(reader)
        self.assertFalse(final["submitted_read_set_complete"])
        self.assertIn("terminal_registered_guard_unconfirmed:KeyboardInterrupt", final["reasons"])
        self.assertIsNone(final["hash_verification_attempt_bytes"])
        with self.assertRaises(ValueError):
            reader.read(item.path)

    def test_begin_guard_interrupt_preserves_denominators_and_prevents_restart(self):
        self.source("initial-guard.json", [1])
        plan = self.plan()
        with patch.object(budget, "_guards", side_effect=KeyboardInterrupt()):
            with self.assertRaises(budget.ReadFailure) as failed:
                budget.begin_reads(plan)
        ledger = failed.exception.ledger
        self.assertEqual(ledger["original_denominators"], self.denominators)
        self.assertIsNone(ledger["hash_verification_attempt_bytes"])
        self.assertEqual(ledger["attempted_read_occurrences"], 0)
        self.assertFalse(ledger["submitted_read_set_complete"])
        with self.assertRaisesRegex(ValueError, "one_cumulative_account"):
            budget.begin_reads(plan)

    def test_mutation_during_JSON_parse_post_guard_prevents_completion(self):
        item = self.source("race.json", [1])
        reader = budget.begin_reads(self.plan())
        actual_loads = json.loads

        def change_source(text, *args, **kwargs):
            value = actual_loads(text, *args, **kwargs)
            if text == "[1]":
                Path(item.path).write_bytes(b"[2]")
            return value

        with patch.object(budget.json, "loads", side_effect=change_source):
            with self.assertRaises(budget.ReadFailure):
                reader.read(item.path)
        self.assertEqual(budget.read_ledger(reader)["completed_read_occurrences"], 0)

    def test_output_cannot_live_inside_registered_archive_root(self):
        self.source("source.json", [1])
        with self.assertRaisesRegex(ValueError, "outside_declared_source_archive"):
            self.plan(output_directory=str(self.archive / "new-output"))
        plan = self.plan(output_directory=str(self.root / "separate-output"))
        self.assertEqual(plan.record()["output_directory"], str(self.root / "separate-output"))
        self.assertFalse((self.root / "separate-output").exists())


if __name__ == "__main__":
    unittest.main()
