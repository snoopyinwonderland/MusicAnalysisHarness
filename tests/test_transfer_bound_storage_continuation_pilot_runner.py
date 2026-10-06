"""Explicit mocked orchestration checks, not corpus or music validation."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import test_transfer_bound_request_storage_pilot_runner as fixture

SPEC = importlib.util.spec_from_file_location("continuation_runner_under_test",
    Path(__file__).resolve().parents[1] / "tmp/transfer_bound_storage_continuation_pilot_20261003.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerControls(unittest.TestCase):
    def setUp(self):
        self.prepared = fixture.PreparedDouble()
        self.checkpoint = object()
        self.record = {"reasons": [], "remaining_tasks": [
            {"group_index": 0, "task_index": 1, "task": fixture.admitted_record()["storage_plan"]["groups"][0]["tasks"][1]}]}
        self.plan = fixture.PreparedDouble(self.record)
        self.terminal = {"summary": {"computed_pairs": 6, "persisted_pairs": 6},
            "new_summary": {"computed_pairs": 3, "persisted_pairs": 3}, "storage_integrity_passed": True,
            "selected_request_storage_complete": True}
        self.events = []

    def execute(self, **options):
        return runner.execute_storage(self.prepared, self.checkpoint, Path("unused-mocked-output"),
            emit=lambda *a, **k: self.events.append((a, k)), protected_sha256={}, **options)

    def mocks(self):
        return patch.multiple(runner.continuation,
            plan_continuation=unittest.mock.DEFAULT, begin_continuation=unittest.mock.DEFAULT,
            write_block=unittest.mock.DEFAULT, finish=unittest.mock.DEFAULT, ledger=unittest.mock.DEFAULT)

    def arrange(self, mocks):
        mocks["plan_continuation"].return_value = self.plan
        mocks["begin_continuation"].return_value = object()
        mocks["write_block"].return_value = deepcopy(self.terminal)
        mocks["finish"].return_value = deepcopy(self.terminal)
        mocks["ledger"].return_value = deepcopy(self.terminal)

    def test_only_remaining_task_called_new_and_combined_counts_separate(self):
        with self.mocks() as mocks:
            self.arrange(mocks); result = self.execute(clock=lambda: 0)
            self.assertEqual(mocks["write_block"].call_count, 1)
            self.assertEqual(mocks["plan_continuation"].call_args.args, (self.prepared, self.checkpoint))
            self.assertEqual(result["pairs_evaluated"], 3)
            self.assertEqual(result["combined_pairs_evaluated"], 6)
            self.assertEqual(result["status"], "selected_request_storage_complete_not_selected")

    def test_later_physical_ledger_overrides_earlier_finish_copy(self):
        with self.mocks() as mocks:
            self.arrange(mocks)
            mocks["ledger"].return_value["selected_request_storage_complete"] = False
            result = self.execute(clock=lambda: 0)
            self.assertEqual(result["status"], "incomplete_or_failed_continuation")

    def test_wall_expiry_preserves_uncomputed_not_success(self):
        times = iter([0, 601, 602])
        with self.mocks() as mocks:
            self.arrange(mocks); result = self.execute(clock=lambda: next(times))
            mocks["write_block"].assert_not_called()
            mocks["finish"].assert_called_once()
            self.assertEqual(result["status"], "partial_continuation_wall_budget_reached")
            self.assertFalse(result["atomic_block_wall_time_bounded"])

    def test_whole_hold_precedes_new_output(self):
        self.plan._record["reasons"] = ["whole output hold"]
        with self.mocks() as mocks:
            self.arrange(mocks); result = self.execute()
            mocks["begin_continuation"].assert_not_called()
            self.assertEqual(result["pairs_evaluated"], 0)

    def test_compute_interrupt_keeps_terminal_failure_and_no_success(self):
        with self.mocks() as mocks:
            self.arrange(mocks); mocks["write_block"].side_effect = KeyboardInterrupt("interrupt")
            result = self.execute(clock=lambda: 0)
            mocks["finish"].assert_called_once()
            self.assertIn("KeyboardInterrupt", result["failure"])
            self.assertEqual(result["status"], "incomplete_or_failed_continuation")

    def test_terminal_unconfirmed_is_not_complete(self):
        with self.mocks() as mocks:
            self.arrange(mocks); mocks["finish"].side_effect = OSError("no manifest")
            result = self.execute(clock=lambda: 0)
            self.assertIsNone(result["storage_terminal"])
            self.assertIsNone(result["pairs_evaluated"])
            self.assertIn("terminal_unconfirmed", result["failure"])

    def test_boolean_or_negative_wall_budget_rejected(self):
        for value in (True, 0, -1, 1.0):
            with self.assertRaises(ValueError): self.execute(wall_seconds=value)

    def test_whole_original_coverage_validation_remains_enabled(self):
        self.prepared._record["whole_original"]["pairs"] += 1
        with self.mocks() as mocks:
            self.arrange(mocks)
            with self.assertRaises(ValueError): self.execute()
            mocks["plan_continuation"].assert_not_called()


if __name__ == "__main__": unittest.main()
