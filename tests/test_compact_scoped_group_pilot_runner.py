"""Pure root membership/cost checks; these do not restore archive authority."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "tmp/compact_scoped_group_pilot_20261003.py"
SPEC = importlib.util.spec_from_file_location("compact_scoped_runner_tests", PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class CompleteGroupingTests(unittest.TestCase):
    def fixture(self):
        packets = [{"entries": [{"selector_index": i, "entry": {"ordinal": i}} for i in range(4)]}]
        declarations = [{"original": {"selector_indices": s, "planned_entries": 2, "planned_pairs": 1}}
            for s in ([0, 2], [1, 3])]
        return packets, declarations

    def test_all_original_selectors_and_order_preserved(self):
        packets, declarations = self.fixture()
        groups, batches = runner.collect_original_groups(iter(packets), declarations, 4)
        self.assertEqual(batches, 1)
        self.assertEqual([[e["ordinal"] for e in entries] for _, entries in groups], [[0, 2], [1, 3]])

    def test_prefix_or_duplicate_cannot_be_success(self):
        packets, declarations = self.fixture()
        packets[0]["entries"].pop()
        with self.assertRaises(ValueError):
            runner.collect_original_groups(iter(packets), declarations, 4)
        packets, declarations = self.fixture()
        packets[0]["entries"][1]["selector_index"] = 0
        with self.assertRaises(ValueError):
            runner.collect_original_groups(iter(packets), declarations, 4)

    def test_all_groups_cover_exactly_and_pairs_original(self):
        packets, declarations = self.fixture()
        declarations[1]["original"]["selector_indices"] = [0, 3]
        with self.assertRaises(ValueError):
            runner.collect_original_groups(iter(packets), declarations, 4)
        packets, declarations = self.fixture()
        declarations[0]["original"]["planned_pairs"] = 0
        with self.assertRaises(ValueError):
            runner.collect_original_groups(iter(packets), declarations, 4)


class AdvisoryCostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "input.json"
        self.path.write_bytes(b"{}")  # New isolated test fixture, not a source edit.
        self.sha = "a" * 64
        self.o = {"path": str(self.path), "occurrence_index": 0, "completed": True,
            "stream_EOF_reached": True, "same_open_before_after_SHA_verified": True,
            "error": None, "expected_sha256": self.sha, "physical_bytes": 2, "physical_bytes_returned": 2,
            "physical_bytes_unconfirmed": False, "decoded_bytes": 2, "decoded_bytes_returned": 2,
            "decoded_bytes_unconfirmed": False, "encoding": "raw", "decoded_sha256": self.sha}
        self.receipt = {"version": "archive-read-cost-measurement-0.1.0", "phase_complete": True,
            "observations": [self.o], "decoded_attempt_bytes": 2}

    def checked(self, receipt):
        return runner.checked_cost_reads(receipt, [self.path], {str(self.path): self.sha})

    def test_cost_only_not_body_or_capability_authority(self):
        read = self.checked(self.receipt)[0]
        self.assertEqual(read.decoded_bytes, 2)
        self.assertEqual(read.sha256, self.sha)

    def test_incomplete_unknown_bool_and_SHA_rejected(self):
        for key, value in (("completed", False), ("decoded_bytes", None), ("physical_bytes", True),
                ("decoded_bytes_unconfirmed", True), ("expected_sha256", "b" * 64), ("occurrence_index", True)):
            receipt = copy.deepcopy(self.receipt)
            receipt["observations"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.checked(receipt)

    def test_wrong_membership_or_total_rejected(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["observations"] = []
        with self.assertRaises(ValueError):
            self.checked(receipt)
        receipt = copy.deepcopy(self.receipt)
        receipt["decoded_attempt_bytes"] = 0
        with self.assertRaises(ValueError):
            self.checked(receipt)


class FailureAccountingTests(unittest.TestCase):
    def test_open_failure_keeps_read_ledger_without_handle(self):
        error = ValueError("metadata_interrupted")
        error.report = {"read_ledger": {"decoded_attempt_bytes": 123, "submitted_read_set_complete": False}}
        self.assertEqual(runner.failure_evidence(error)["read_ledger"]["decoded_attempt_bytes"], 123)
        error = ValueError("unconfirmed")
        self.assertIsNone(runner.failure_evidence(error)["read_ledger"])
        self.assertIs(runner.failure_evidence(error)["charged_cost_confirmed"], False)

    def test_final_guard_observation_error_is_not_success(self):
        def cannot_hash(path):
            raise PermissionError("test_guard_interruption")
        report = runner.observe_code_guards({str(PATH): "a" * 64}, cannot_hash)
        self.assertIs(report["all_current_SHA_confirmed"], False)
        self.assertEqual(len(report["uncertain_paths"]), 1)


if __name__ == "__main__":
    unittest.main()
