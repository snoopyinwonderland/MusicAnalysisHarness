"""Root orchestration controls; no corpus producer or real pilot is called."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_read_budget as budget

_PATH = Path(__file__).resolve().parents[1] / "tmp/scoped_archive_cost_pilot_20261003.py"
_SPEC = importlib.util.spec_from_file_location("scoped_cost_runner_controls", _PATH)
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


class BootstrapAccountingControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.path, self.output = base / "input.json", base / "receipts"
        self.output.mkdir()
        self.denominators = {"whole_original_completion_requests": 4,
            "whole_original_selector_occurrences": 8050}
        self.discovery = []

    def run_bootstrap(self, body=b"{}", limit=1024):
        self.path.write_bytes(body)  # Generated tiny fixture, never original input.
        registered = {str(self.path): hashlib.sha256(body).hexdigest()}
        return runner.bootstrap([self.path], registered, self.denominators, limit=limit,
            output=self.output, discovery=self.discovery, receipt_name="receipt.json")

    def assert_receipt(self, expected_cost, complete=False):
        self.assertEqual(len(self.discovery), 1)
        record = json.loads((self.output / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(record, self.discovery[0])
        self.assertEqual(record["decoded_attempt_bytes"], expected_cost)
        self.assertIs(record["submitted_read_set_complete"], complete)
        self.assertEqual(record["original_denominators"], self.denominators)
        return record

    def test_normal_bootstrap_charged_once_and_saved_before_return(self):
        records, ledger = self.run_bootstrap(b'{"x": 1}')
        self.assertEqual(records, [{"x": 1}])
        self.assertEqual(ledger, self.assert_receipt(8, True))

    def test_parse_failure_retains_full_attempt_cost_and_terminal_ledger(self):
        with self.assertRaises(budget.ReadFailure):
            self.run_bootstrap(b"{")
        ledger = self.assert_receipt(1)
        self.assertEqual(ledger["failed_read_occurrences"], 1)
        self.assertNotEqual(ledger["reasons"], [])

    def test_whole_plan_hold_is_zero_decode_not_empty_success(self):
        with self.assertRaises(budget.WholeReadHold):
            self.run_bootstrap(limit=0)
        ledger = self.assert_receipt(0)
        self.assertEqual(ledger["status"], "bootstrap_plan_whole_hold")
        self.assertNotEqual(ledger["plan"]["reasons"], [])

    def test_begin_readfailure_snapshot_is_saved_when_no_reader_returned(self):
        self.path.write_bytes(b"{}")
        expected = hashlib.sha256(b"{}").hexdigest()
        plan = budget.plan_read_run([budget.ReadInput("read", str(self.path), expected, 2, 2)],
            original_denominators=self.denominators, registered_sha256={str(self.path): expected})
        owned = budget.begin_reads(plan)
        failure = budget.ReadFailure("injected_begin_failure", owned)
        with patch.object(budget, "begin_reads", side_effect=failure):
            with self.assertRaises(budget.ReadFailure):
                self.run_bootstrap()
        self.assertEqual(self.assert_receipt(0), failure.ledger)
        budget.finish_reads(owned)

    def test_unknown_begin_interrupt_does_not_forge_zero_cost(self):
        with patch.object(budget, "begin_reads", side_effect=KeyboardInterrupt("injected")):
            with self.assertRaises(KeyboardInterrupt):
                self.run_bootstrap()
        self.assertEqual(self.assert_receipt(None)["status"], "bootstrap_cost_unconfirmed")


if __name__ == "__main__":
    unittest.main()
