"""New runner wiring/regression and whole-group gates, not archive authority."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "tmp/proof_shared_scoped_group_pilot_20261003.py"
SPEC = importlib.util.spec_from_file_location("proof_shared_scoped_runner_tests", PATH)
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


class BaselineResourceTests(unittest.TestCase):
    def fixture(self):
        return {"selection":[1,0],"validated_selected_entries":1710,"validated_selected_batches":107,
            "resource_observations":[],"all_group_preflights":[],"elapsed_seconds":None}

    def test_unobserved_resource_is_not_zero_or_authority(self):
        record = runner.baseline_resource_summary(self.fixture())
        self.assertIsNone(record["peak_working_set_bytes"])
        self.assertIsNone(record["elapsed_seconds"])
        self.assertIn("not_music_or_saved_capability",record["authority"])

    def test_other_scope_prefix_bool_rejected(self):
        for field,value in (("selection",[0,0]),("validated_selected_entries",1709),
                ("validated_selected_batches",True)):
            report = self.fixture()
            report[field] = value
            with self.subTest(field=field),self.assertRaises(ValueError):
                runner.baseline_resource_summary(report)


class WholeGroupReadinessTests(unittest.TestCase):
    def fixture(self):
        declarations = [{"original":{"planned_entries":2,"planned_pairs":1,"planned_block_tasks":1}} for _ in range(2)]
        records = [{"entry_count":2,"planned_pairs":1,"planned_blocks":1,"stage":"complete",
            "reasons":[],"all_original_entries_retained":True} for _ in range(2)]
        return records, declarations

    def test_every_original_group_ready(self):
        records, declarations = self.fixture()
        self.assertIs(runner.whole_group_readiness(records,declarations),True)

    def test_one_hold_never_promotes_prefix(self):
        records, declarations = self.fixture()
        records[1].update(stage="canonicalization",reasons=["whole_work_exceeds_limit_no_prefix"],
            all_original_entries_retained=False)
        self.assertIs(runner.whole_group_readiness(records,declarations),False)

    def test_empty_prefix_unknown_bool_and_incomplete_rejected(self):
        records, declarations = self.fixture()
        for actual, original in (([],[]),(records[:1],declarations)):
            with self.assertRaises(ValueError):
                runner.whole_group_readiness(actual,original)
        for field,value in (("reasons",None),("entry_count",True),("planned_pairs",0),
                ("stage","canonicalization"),("all_original_entries_retained",False)):
            changed = copy.deepcopy(records)
            changed[1][field] = value
            with self.subTest(field=field),self.assertRaises(ValueError):
                runner.whole_group_readiness(changed,declarations)

    def test_no_explicit_gc_workaround_in_runner(self):
        import ast
        tree = ast.parse(PATH.read_text(encoding="utf-8-sig"))
        calls = [n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name)
            and n.func.value.id == "gc" and n.func.attr == "collect" for n in calls))


if __name__ == "__main__":
    unittest.main()
