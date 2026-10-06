"""Fast mocked runner/control tests; these do not prove corpus ancestry.

Real XML/source ownership belongs to the existing coordinator/storage suites.
Here the storage APIs are explicitly mocked so interruption and reporting
contracts can be checked without comparing the real corpus or writing scores.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest import mock


RUNNER_PATH = Path(__file__).resolve().parents[1] / "tmp/proof_shared_request_storage_pilot_20261003.py"
SPEC = importlib.util.spec_from_file_location("proof_shared_request_storage_runner_under_test", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def task(row_start, row_end, column_start, column_end, expected_pairs):
    return {
        "row_start": row_start, "row_end": row_end,
        "column_start": column_start, "column_end": column_end,
        "expected_pairs": expected_pairs,
        "source_sha256": "a" * 64, "group_sha256": "b" * 64,
        "refinement_sha256": "c" * 64, "entry_inventory_sha256": "d" * 64,
    }


def admitted_record():
    selected = {
        "completion_requests": 1, "selector_occurrences": 4, "batches": 1,
        "groups": 1, "pairs": 6, "block_tasks": 2,
    }
    omitted = {**selected, "completion_requests": 2}
    whole = {name: selected[name] + omitted[name] for name in selected}
    tasks = [task(0, 3, 0, 3, 3), task(0, 3, 3, 4, 3)]
    plan = {
        "status": "planned_proof_storage_incomplete", "reasons": [],
        "planned_submitted_groups": 1, "planned_submitted_entries": 4,
        "planned_submitted_pairs": 6, "planned_submitted_nonempty_tasks": 2,
        "planned_declared_upstream_tasks": 2, "planned_shared_sources": 1,
        "output_reservation_complete": True,
        "output_reserved_bytes_before_pair_calculation": 100,
        "partial_accounted_output_reservation_bytes": 100,
        "limits": {"max_output_bytes": 1000, "max_plan_bytes": 10, "max_manifest_bytes": 20},
        "sources": [{"source_encoded_bound": 20}],
        "groups": [{
            "original": {"planned_entries": 4, "planned_pairs": 6,
                "planned_block_tasks": 2, "selector_indices": list(range(4))},
            "tasks": tasks, "catalog_encoded_bound": 20,
            "task_encoded_caps": [15, 15],
        }],
        "flags": {"training_eligible": False, "gold_eligible": False},
    }
    return {
        "selected_completion": selected, "whole_original": whole,
        "omitted_completions": omitted, "prepared_v2_groups": 1,
        "storage_plan": plan, "pairs_evaluated": 0, "full_archive": False,
        "saved_JSON_restores_capability": False,
        "flags": {"training_eligible": False, "gold_eligible": False},
    }


class PreparedDouble:
    """Not an owned preparation: only accepted by explicitly mocked APIs."""
    def __init__(self, record=None):
        self._record = deepcopy(record if record is not None else admitted_record())
        self.storage_plan = object()

    def record(self):
        return deepcopy(self._record)


def terminal(computed=6, persisted=6):
    return {
        "summary": {"planned_pairs": 6, "computed_pairs": computed,
            "persisted_pairs": persisted, "uncomputed_pairs": None if computed is None else 6 - computed},
        "submitted_group_set_complete": computed == persisted == 6,
        "physical_closure_verified_terminally": computed == persisted == 6,
    }


def partial_request_ledger(storage_snapshot=None):
    record = admitted_record()
    return {"selected_request_storage_complete": False, "same_request_storage_coverage": True,
        "full_archive_complete": False,
        "storage": terminal(3, 3) if storage_snapshot is None else storage_snapshot,
        **{name: record[name] for name in ("selected_completion", "whole_original", "omitted_completions")}}


class CoverageContractTests(unittest.TestCase):
    def test_complete_declaration_retains_whole_plan_without_mutation(self):
        record = admitted_record()
        before = deepcopy(record)
        self.assertIs(runner.validate_coverage(record), record["storage_plan"])
        self.assertEqual(record, before)

    def test_denominator_mismatched_key_sets_rejected(self):
        record = admitted_record()
        del record["omitted_completions"]["batches"]
        with self.assertRaises(ValueError):
            runner.validate_coverage(record)

    def test_closed_six_denominator_names_required(self):
        for change in ("remove", "add"):
            with self.subTest(change=change):
                record = admitted_record()
                for field in ("selected_completion", "whole_original", "omitted_completions"):
                    if change == "remove":
                        del record[field]["batches"]
                    else:
                        record[field]["extra_counter"] = 0
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)

    def test_denominator_integer_nonnegative_and_closed(self):
        for value in (True, False, -1, 1.0, "1", None):
            with self.subTest(value=value):
                record = admitted_record()
                record["selected_completion"]["completion_requests"] = value
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)
        record = admitted_record()
        record["whole_original"]["pairs"] += 1
        with self.assertRaises(ValueError):
            runner.validate_coverage(record)

    def test_every_selected_request_coverage_count_must_match(self):
        for field in ("planned_submitted_groups", "planned_submitted_entries",
                "planned_submitted_pairs", "planned_declared_upstream_tasks"):
            with self.subTest(field=field):
                record = admitted_record()
                record["storage_plan"][field] += 1
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)
        record = admitted_record()
        record["prepared_v2_groups"] = 0
        with self.assertRaises(ValueError):
            runner.validate_coverage(record)

    def test_bool_cannot_impersonate_prepared_or_submitted_count(self):
        for location, field in ((None, "prepared_v2_groups"),
                ("storage_plan", "planned_submitted_groups")):
            with self.subTest(field=field):
                record = admitted_record()
                target = record if location is None else record[location]
                target[field] = True  # The declared value is 1; equality alone is unsafe.
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)

    def test_bool_cannot_impersonate_zero_evaluated_pairs(self):
        record = admitted_record()
        record["pairs_evaluated"] = False
        with self.assertRaises(ValueError):
            runner.validate_coverage(record)

    def test_preparation_must_not_claim_archive_capability_analysis_or_training(self):
        for field, value in (("full_archive", True), ("full_archive", 0),
                ("saved_JSON_restores_capability", True), ("pairs_evaluated", 1)):
            with self.subTest(field=field, value=value):
                record = admitted_record()
                record[field] = value
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)
        record = admitted_record()
        record["flags"]["training_eligible"] = True
        with self.assertRaises(ValueError):
            runner.validate_coverage(record)

    def test_success_requires_complete_output_reservation(self):
        for field, value in (("output_reservation_complete", False),
                ("output_reserved_bytes_before_pair_calculation", None),
                ("output_reserved_bytes_before_pair_calculation", True),
                ("output_reserved_bytes_before_pair_calculation", 1001)):
            with self.subTest(field=field, value=value):
                record = admitted_record()
                record["storage_plan"][field] = value
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)

    def test_complete_reservation_requires_all_atomic_task_descriptors(self):
        for value in (None, (), []):
            with self.subTest(tasks=value):
                record = admitted_record()
                record["storage_plan"]["groups"][0]["tasks"] = value
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)
        record = admitted_record()
        record["storage_plan"]["groups"] = []
        with self.assertRaises(ValueError):
            runner.validate_coverage(record)

    def test_atomic_expected_pairs_exact_positive_and_covers_all_selected_pairs(self):
        for value in (True, 0, -1, 3.0, 2):
            with self.subTest(expected_pairs=value):
                record = admitted_record()
                record["storage_plan"]["groups"][0]["tasks"][0]["expected_pairs"] = value
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)

    def test_nonempty_task_count_cannot_be_bool_negative_or_inexact(self):
        for value in (True, -1, 2.0, 1):
            with self.subTest(count=value):
                record = admitted_record()
                record["storage_plan"]["planned_submitted_nonempty_tasks"] = value
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)

    def test_max_output_cap_requires_exact_nonnegative_integer(self):
        for value in (True, -1, 1000.0):
            with self.subTest(cap=value):
                record = admitted_record()
                record["storage_plan"]["limits"]["max_output_bytes"] = value
                with self.assertRaises(ValueError):
                    runner.validate_coverage(record)


class StorageControlTests(unittest.TestCase):
    def setUp(self):
        self.prepared = PreparedDouble()
        self.run = object()
        self.emit = mock.Mock()
        self.api = mock.patch.multiple(runner.storage,
            begin_storage=mock.DEFAULT, write_block=mock.DEFAULT, finish=mock.DEFAULT)
        self.mocks = self.api.start()
        self.addCleanup(self.api.stop)
        self.mocks["begin_storage"].return_value = self.run
        self.mocks["write_block"].return_value = {
            "summary": {"computed_pairs": 3, "persisted_pairs": 3},
            "storage_integrity_passed": True,
        }
        self.mocks["finish"].return_value = terminal()
        self.ledger_patch = mock.patch.object(runner.request, "request_ledger", autospec=True)
        self.request_ledger = self.ledger_patch.start()
        self.addCleanup(self.ledger_patch.stop)
        self.request_ledger.return_value = {
            "selected_request_storage_complete": True, "same_request_storage_coverage": True,
            "full_archive_complete": False, "storage": terminal(),
        }

    def execute(self, **kwargs):
        return runner.execute_storage(self.prepared, Path("mock-output-unused"),
            emit=self.emit, clock=kwargs.pop("clock", lambda: 0), **kwargs)

    def test_positive_integer_wall_budget_required_before_apis(self):
        for value in (0, -1, True, False, 600.0, "600", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.execute(wall_seconds=value)
        for api in self.mocks.values():
            api.assert_not_called()
        self.request_ledger.assert_not_called()

    def test_plan_hold_prohibits_begin_compare_write_and_terminal_calls(self):
        record = admitted_record()
        record["storage_plan"].update(reasons=["whole_output_reservation_exceeds_limit_no_prefix"],
            status="whole_proof_storage_run_hold",
            output_reserved_bytes_before_pair_calculation=1001,
            partial_accounted_output_reservation_bytes=1001)
        self.prepared = PreparedDouble(record)
        result = self.execute()
        self.assertEqual(result["status"], "whole_storage_reservation_hold_no_pair_calculation")
        self.assertEqual(result["pairs_evaluated"], 0)
        self.assertIs(result["storage_started"], False)
        self.assertEqual(result["hold_reasons"], record["storage_plan"]["reasons"])
        for api in self.mocks.values():
            api.assert_not_called()
        self.request_ledger.assert_not_called()

    def test_unknown_whole_reservation_hold_keeps_pairs_zero_without_invented_bound(self):
        record = admitted_record()
        record["storage_plan"].update(reasons=["source_stream_work_hold"],
            status="whole_proof_storage_run_hold", output_reservation_complete=False,
            output_reserved_bytes_before_pair_calculation=None)
        self.prepared = PreparedDouble(record)
        result = self.execute()
        self.assertEqual(result["pairs_evaluated"], 0)
        self.assertIsNone(self.prepared.record()["storage_plan"]["output_reserved_bytes_before_pair_calculation"])
        self.mocks["begin_storage"].assert_not_called()

    def test_complete_uses_exact_preparation_plan_and_owned_request_ledger(self):
        result = self.execute()
        self.mocks["begin_storage"].assert_called_once_with(self.prepared.storage_plan, "mock-output-unused")
        self.assertEqual(self.mocks["write_block"].call_count, 2)
        self.request_ledger.assert_called_once_with(self.prepared, self.run)
        self.mocks["finish"].assert_called_once_with(self.run)
        self.assertEqual(result["status"], "selected_request_storage_complete_not_selected")
        self.assertEqual(result["pairs_evaluated"], 6)
        self.assertEqual(result["returned_atomic_tasks"], 2)
        self.assertIs(result["atomic_block_wall_time_bounded"], False)
        self.assertIsNone(result["failure"])
        self.assertEqual(self.emit.call_count, 2)
        self.assertTrue(all(call.kwargs["provisional"] is True for call in self.emit.call_args_list))

    def test_writer_terminal_complete_does_not_replace_whole_request_completion(self):
        self.request_ledger.return_value = partial_request_ledger()
        result = self.execute()
        self.assertEqual(result["status"], "incomplete_or_failed_storage")
        self.assertIs(result["request_ledger"]["full_archive_complete"], False)

    def test_same_request_coverage_required_even_if_complete_flag_true(self):
        self.request_ledger.return_value["same_request_storage_coverage"] = False
        result = self.execute()
        self.assertEqual(result["status"], "incomplete_or_failed_storage")

    def test_later_postterminal_guard_snapshot_replaces_earlier_finish_copy(self):
        later = terminal(3, 0)
        later["postterminal_changed_paths"] = ["original_file_changed"]
        self.request_ledger.return_value = partial_request_ledger(later)
        result = self.execute()
        self.assertEqual(result["storage_terminal"], later)
        self.assertEqual(result["pairs_evaluated"], 3)
        self.assertEqual(result["status"], "incomplete_or_failed_storage")

    def test_cooperative_budget_is_checked_between_atomic_blocks_partial_retained(self):
        self.mocks["finish"].return_value = terminal(3, 3)
        self.request_ledger.return_value = partial_request_ledger(terminal(3, 3))
        clock = mock.Mock(side_effect=[0, 0, 600, 601])
        result = self.execute(clock=clock)
        self.assertEqual(self.mocks["write_block"].call_count, 1)
        self.assertEqual(result["status"], "partial_storage_wall_budget_reached")
        self.assertEqual(result["returned_atomic_tasks"], 1)
        self.assertEqual(result["pairs_evaluated"], 3)
        self.assertEqual(result["storage_terminal"]["summary"]["uncomputed_pairs"], 3)
        self.assertEqual(result["request_ledger"], partial_request_ledger())
        self.assertIs(result["atomic_block_wall_time_bounded"], False)

    def test_budget_before_first_block_still_finishes_created_run_without_prefix(self):
        self.mocks["finish"].return_value = terminal(0, 0)
        self.request_ledger.return_value = partial_request_ledger(terminal(0, 0))
        result = self.execute(clock=mock.Mock(side_effect=[0, 600, 601]))
        self.mocks["write_block"].assert_not_called()
        self.mocks["finish"].assert_called_once_with(self.run)
        self.assertEqual(result["status"], "partial_storage_wall_budget_reached")
        self.assertEqual(result["pairs_evaluated"], 0)
        self.assertEqual(result["storage_terminal"]["summary"]["uncomputed_pairs"], 6)

    def test_begin_failure_never_claims_zero_confirmed_computation(self):
        self.mocks["begin_storage"].side_effect = RuntimeError("before_owned_run")
        result = self.execute()
        self.assertIsNone(result["pairs_evaluated"])
        self.assertIs(result["storage_started"], False)
        self.assertIn("before_owned_run", result["failure"])
        self.mocks["finish"].assert_not_called()
        self.request_ledger.assert_not_called()

    def test_write_failure_preserves_confirmed_terminal_counts_and_original_denominators(self):
        self.mocks["write_block"].side_effect = RuntimeError("atomic_write_failed")
        self.mocks["finish"].return_value = terminal(3, 0)
        self.request_ledger.return_value = partial_request_ledger(terminal(3, 0))
        result = self.execute()
        self.assertEqual(result["status"], "incomplete_or_failed_storage")
        self.assertEqual(result["pairs_evaluated"], 3)
        self.assertEqual(result["storage_terminal"]["summary"]["persisted_pairs"], 0)
        self.assertEqual(result["request_ledger"]["whole_original"], admitted_record()["whole_original"])
        self.assertIn("atomic_write_failed", result["failure"])
        self.assertEqual(result["returned_atomic_tasks"], 0)

    def test_interrupted_unknown_computation_is_not_reported_as_zero(self):
        self.mocks["write_block"].side_effect = KeyboardInterrupt("unknown_atomic_result")
        self.mocks["finish"].return_value = terminal(None, 0)
        self.request_ledger.return_value = partial_request_ledger(terminal(None, 0))
        result = self.execute()
        self.assertIsNone(result["pairs_evaluated"])
        self.assertIn("KeyboardInterrupt", result["failure"])
        self.mocks["finish"].assert_called_once_with(self.run)

    def test_storage_integrity_failure_stops_before_later_task(self):
        self.mocks["write_block"].return_value["storage_integrity_passed"] = False
        self.mocks["finish"].return_value = terminal(3, 0)
        self.request_ledger.return_value = partial_request_ledger(terminal(3, 0))
        result = self.execute()
        self.assertEqual(self.mocks["write_block"].call_count, 1)
        self.assertEqual(result["failure"], "storage_integrity_not_confirmed")
        self.assertEqual(result["status"], "incomplete_or_failed_storage")

    def test_finish_failure_retains_unknown_not_zero_and_never_complete(self):
        self.mocks["finish"].side_effect = OSError("terminal_write_unknown")
        result = self.execute()
        self.assertEqual(result["status"], "incomplete_or_failed_storage")
        self.assertIsNone(result["storage_terminal"])
        self.assertIsNone(result["pairs_evaluated"])
        self.assertIn("terminal_write_unknown", result["failure"])
        self.request_ledger.assert_not_called()

    def test_request_ledger_failure_cannot_promote_terminal_complete(self):
        self.request_ledger.side_effect = ValueError("foreign_run_rejected")
        result = self.execute()
        self.assertEqual(result["status"], "incomplete_or_failed_storage")
        self.assertEqual(result["pairs_evaluated"], 6)
        self.assertIsNone(result["request_ledger"])
        self.assertIn("foreign_run_rejected", result["failure"])

    def test_failure_cannot_promote_even_if_later_mock_ledger_claims_complete(self):
        self.mocks["write_block"].side_effect = RuntimeError("comparison_or_write_failed")
        result = self.execute()
        self.assertEqual(result["status"], "incomplete_or_failed_storage")
        self.assertIn("comparison_or_write_failed", result["failure"])


if __name__ == "__main__":
    unittest.main()
