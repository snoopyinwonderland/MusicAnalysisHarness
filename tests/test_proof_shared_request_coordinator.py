"""Small genuine replay bodies; historical ancestry is explicitly MOCKED.

These controls prove ownership, whole-request coverage, terminal truth and
source-once persistence, NOT real 40-file ancestry admission or music accuracy.
Use module aliases so predecessor TestCase classes are not rediscovered here.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import proof_shared_request_coordinator as request
from musicanote_harness import proof_shared_progression_storage as storage
from musicanote_harness import proof_shared_source_progression_contrast as core
from musicanote_harness import shared_source_progression_contrast as source_core
from musicanote_harness import scoped_source_archive_pilot as scoped
from musicanote_harness import lossless_json_dag_v2 as dag
import test_scoped_source_archive_pilot as fixture_module
import test_source_progression_replay_trial as factory


class SnapshotControls(unittest.TestCase):
    def test_encoding_is_pre_gated_and_done_once_with_exact_size(self):
        value = {"한글": [1, 2, {"x": True}], "end": None}
        stat = dag.preflight_json(value)
        cost = 3 * stat["charged_work_units"]
        with patch.object(request.original_codec, "_raw", wraps=request.original_codec._raw) as encode:
            raw, charged = request._snapshot(value, request.RequestLimits(max_coordination_work=cost), 0)
            self.assertEqual(encode.call_count, 1)
        self.assertEqual(len(raw), stat["expanded_bytes"])
        self.assertEqual(charged, cost)
        with patch.object(request.original_codec, "_raw", side_effect=AssertionError("no whole encoding")):
            with self.assertRaises(dag.DagHold):
                request._snapshot(value, request.RequestLimits(max_coordination_work=cost-1), 0)

    def test_metadata_bytes_hold_precedes_whole_encoding(self):
        with patch.object(request.original_codec, "_raw", side_effect=AssertionError("no whole encoding")):
            with self.assertRaises(dag.DagHold):
                request._snapshot({"x": "x" * 20}, request.RequestLimits(max_metadata_bytes=10), 0)

    def test_request_limits_exact_closed_integers_and_no_constructor(self):
        for bad in (True, -1, 0.0, "1"):
            with self.assertRaises(ValueError): request.RequestLimits(max_groups=bad)
        with self.assertRaises(ValueError): request.RequestPreparation()

    def test_hold_diagnostic_transfer_has_no_hidden_encoding_or_capability(self):
        value = {"diagnostic": "already created"}
        with patch.object(request.json, "dumps", side_effect=AssertionError("no unbudgeted diagnostic encoding")):
            error = request.WholeRequestHold("held", value)
        self.assertIs(error.report, value)
        with self.assertRaises(ValueError): request._issued(error.report)

    def test_packet_shape_order_types_and_terminal_exhaustion_controls_are_explicit_mocks(self):
        original = [{"completion_request_ref": {"mock_ref": "one"}}]
        packet = {"completion_request_ref": {"mock_ref": "one"}, "batch_index": 0,
            "selector_start": 0, "selector_end_exclusive": 2,
            "entries": [{"selector_index": 0, "entry": {"a": 1}}, {"selector_index": 1, "entry": {"a": 2}}]}
        expected = {"batches": 1, "selector_occurrences": 2}
        events = []
        def mocked_packet(value):
            try:
                yield value
                events.append("exhausted")
            finally:
                events.append("closed")
        with patch.object(scoped, "iter_selected_entries", return_value=mocked_packet(packet)):
            result, count = request._collect(object(), original, expected)
        self.assertEqual((len(result), count), (2, 1))
        self.assertEqual(events, ["exhausted", "closed"])
        for field, bad in (("batch_index", True), ("selector_start", False),
                ("completion_request_ref", {"mock_ref": "other"}), ("selector_end_exclusive", 1)):
            changed = deepcopy(packet); changed[field] = bad
            with patch.object(scoped, "iter_selected_entries", return_value=mocked_packet(changed)):
                with self.assertRaises(ValueError): request._collect(object(), original, expected)
        for bad in (True, 0):
            changed = deepcopy(packet); changed["entries"][1]["selector_index"] = bad
            with patch.object(scoped, "iter_selected_entries", return_value=mocked_packet(changed)):
                with self.assertRaises(ValueError): request._collect(object(), original, expected)

    def test_short_packet_set_and_extra_packet_not_whole_request(self):
        original = [{"completion_request_ref": {"mock_ref": "one"}}]
        packet = {"completion_request_ref": {"mock_ref": "one"}, "batch_index": 0,
            "selector_start": 0, "selector_end_exclusive": 0, "entries": []}
        for packets, expected in (([], {"batches": 1, "selector_occurrences": 0}),
                ([packet], {"batches": 0, "selector_occurrences": 0})):
            with patch.object(scoped, "iter_selected_entries", return_value=(p for p in packets)):
                with self.assertRaises(ValueError): request._collect(object(), original, expected)


class WholeRequestControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory.ReplayPacketStorageTests.setUpClass()
        cls.addClassCleanup(factory.ReplayPacketStorageTests.doClassCleanups)

    def setUp(self):
        self.data = fixture_module.ScopedPacketFixture(self)

    def prepare(self, **options):
        archive = self.data.scoped_open()
        return archive, request.prepare_selected_request(archive, **options)

    def assert_original(self, record):
        for name, total in record["whole_original"].items():
            self.assertEqual(total, record["selected_completion"][name] + record["omitted_completions"][name])
        self.assertEqual(record["selected_completion"]["completion_requests"], 1)
        self.assertFalse(any(record["flags"].values()))

    def test_all_owned_groups_same_source_complete_read_not_old_flags_no_pair_or_eager_export(self):
        archive = self.data.scoped_open()
        with patch.object(scoped, "source_prepared", wraps=scoped.source_prepared) as sources, \
                patch.object(core, "compare_block", side_effect=AssertionError("preflight is not comparison")), \
                patch.object(source_core.PreparedSource, "export_source", side_effect=AssertionError("no eager source")), \
                patch.object(core.CompactPreparedGroup, "export_catalog", side_effect=AssertionError("no eager catalog")):
            prepared = request.prepare_selected_request(archive)
        self.assertEqual(sources.call_count, 1)
        record = prepared.record()
        self.assert_original(record)
        self.assertEqual(record["prepared_v2_groups"], record["selected_completion"]["groups"])
        self.assertEqual(record["pairs_evaluated"], 0)
        self.assertFalse(record["full_archive"])
        self.assertFalse(record["saved_JSON_restores_capability"])
        terminal = record["read_terminal"]
        self.assertTrue(terminal["finished"])
        self.assertTrue(terminal["selected_completion_body_join_complete"])
        self.assertTrue(terminal["read_ledger"]["submitted_read_set_complete"])
        self.assertFalse(terminal["selected_source_intrinsic_groups_complete"])
        self.assertEqual(terminal["prepared_groups"], 0)
        state = request._issued(prepared)
        self.assertTrue(all(core._issued(g).source is state.source for g in state.groups))
        self.assertGreater(record["coordination_work_upper_bound"], record["coordination_work_before_final_snapshot"])
        with self.assertRaises(ValueError): request.prepare_selected_request(archive)

    def test_whole_selected_request_storage_complete_source_once_and_separate_original_denominators(self):
        archive, prepared = self.prepare()
        record = prepared.record()
        directory = self.data.fixture.root / "proof-request-storage"
        run = storage.begin_storage(prepared.storage_plan, str(directory))
        state = request._issued(prepared)
        for index in range(len(state.groups)):
            storage.write_prepared_group(run, index)
        terminal = storage.finish(run)
        result = request.request_ledger(prepared, run)
        self.assert_original(result)
        self.assertTrue(result["same_request_storage_coverage"])
        self.assertTrue(result["selected_request_storage_complete"])
        self.assertFalse(result["full_archive_complete"])
        self.assertEqual(terminal["summary"]["persisted_pairs"], record["selected_completion"]["pairs"])
        self.assertEqual(len(list(directory.glob("source-*.json"))), 1)
        self.assertTrue(scoped.metadata_prepared(archive)["finished"])

    def test_partial_storage_never_becomes_whole_original_or_selected_request_success(self):
        _, prepared = self.prepare()
        run = storage.begin_storage(prepared.storage_plan, str(self.data.fixture.root / "partial-storage"))
        group = request._issued(prepared).groups[0]
        storage.write_block(run, 0, next(group.iter_blocks()))
        storage.finish(run)
        record = request.request_ledger(prepared, run)
        self.assertTrue(record["same_request_storage_coverage"])
        self.assertFalse(record["selected_request_storage_complete"])
        self.assertFalse(record["full_archive_complete"])

    def test_all_group_holds_keep_every_declaration_and_never_issue_favourable_prefix(self):
        archive = self.data.scoped_open(self.data.scoped_plan(group_limits=source_core.GroupLimits(max_entries=0)))
        initial = scoped.metadata_prepared(archive)
        with patch.object(core, "prepare_preflight", side_effect=AssertionError("no admitted prefix")):
            with self.assertRaises(request.WholeRequestHold) as failed:
                request.prepare_selected_request(archive)
        report = failed.exception.report
        self.assertEqual(len(report["all_original_group_preflights"]), initial["selected_completion"]["groups"])
        self.assertEqual(report["prepared_v2_groups"], 0)
        self.assertTrue(report["read_terminal"]["selected_completion_body_join_complete"])
        self.assertEqual(report["read_terminal"]["prepared_groups"], 0)

    def test_explicit_group_limits_cannot_relax_owned_scoped_contract(self):
        archive = self.data.scoped_open(self.data.scoped_plan(group_limits=source_core.GroupLimits(max_entries=0)))
        with patch.object(scoped, "iter_selected_entries", side_effect=AssertionError("no body before limit contract")):
            with self.assertRaises(request.RequestFailure) as failed:
                request.prepare_selected_request(archive, group_limits=source_core.GroupLimits())
        self.assertIn("may_only_tighten", str(failed.exception))
        self.assertTrue(failed.exception.report["read_terminal"]["finished"])

    def test_output_hold_does_not_write_or_compare_and_keeps_whole_counts(self):
        with patch.object(core, "compare_block", side_effect=AssertionError("no comparison on planhold")):
            _, prepared = self.prepare(storage_limits=storage.StorageLimits(max_output_bytes=0))
            record = prepared.record()
            self.assertTrue(record["storage_plan"]["reasons"])
            directory = self.data.fixture.root / "held-storage"
            with self.assertRaises(ValueError): storage.begin_storage(prepared.storage_plan, str(directory))
        self.assertFalse(directory.exists())
        self.assertEqual(record["storage_plan"]["planned_submitted_entries"], record["selected_completion"]["selector_occurrences"])

    def test_count_cap_closes_original_reader_before_body_and_source(self):
        archive = self.data.scoped_open()
        with patch.object(scoped, "source_prepared", side_effect=AssertionError("no source prefix")), \
                patch.object(scoped, "iter_selected_entries", side_effect=AssertionError("no body prefix")):
            with self.assertRaises(request.WholeRequestHold) as failed:
                request.prepare_selected_request(archive, limits=request.RequestLimits(max_selector_occurrences=0))
        terminal = failed.exception.report["read_terminal"]
        self.assertTrue(terminal["finished"])
        self.assertFalse(terminal["selected_completion_body_join_complete"])
        self.assertEqual(terminal["read_ledger"]["completed_read_occurrences"], self.data.metadata_count)

    def test_work_cap_closes_original_reader_and_retains_actual_costs(self):
        archive = self.data.scoped_open()
        with patch.object(scoped, "source_prepared", side_effect=AssertionError("no source prefix")):
            with self.assertRaises(request.RequestFailure) as failed:
                request.prepare_selected_request(archive, limits=request.RequestLimits(max_coordination_work=0))
        terminal = failed.exception.report["read_terminal"]
        self.assertTrue(terminal["finished"])
        self.assertGreater(terminal["read_ledger"]["decoded_attempt_bytes"], 0)
        self.assertFalse(terminal["selected_completion_body_join_complete"])

    def test_body_failure_nonrefundable_terminal_and_no_capability(self):
        inputs = self.data.selected_reads()
        m = self.data.metadata_count
        changed = [*inputs[:m], replace(inputs[m], decoded_bytes=inputs[m].decoded_bytes+1), *inputs[m+1:]]
        archive = self.data.scoped_open(self.data.scoped_plan(reads=changed))
        with self.assertRaises(ValueError) as failed: request.prepare_selected_request(archive)
        terminal = failed.exception.report["read_terminal"]
        self.assertEqual(terminal["read_ledger"]["failed_read_occurrences"], 1)
        self.assertFalse(terminal["selected_completion_body_join_complete"])
        self.assertGreater(terminal["read_ledger"]["decoded_attempt_bytes"], sum(r.decoded_bytes for r in inputs[:m]))
        with self.assertRaises(ValueError): scoped.source_prepared(archive)

    def test_terminal_failure_after_last_body_cannot_issue_or_store(self):
        archive = self.data.scoped_open()
        with patch.object(scoped, "_job", side_effect=ValueError("explicit mock terminal mismatch")), \
                patch.object(core, "prepare_preflight", side_effect=AssertionError("no terminal prefix")):
            with self.assertRaises(request.RequestFailure) as failed: request.prepare_selected_request(archive)
        terminal = failed.exception.report["read_terminal"]
        self.assertTrue(terminal["finished"])
        self.assertFalse(terminal["selected_completion_body_join_complete"])
        self.assertIsNotNone(terminal["body_failure"])

    def test_caller_empty_roots_cannot_weaken_original_closed_inventory(self):
        archive, prepared = self.prepare(protected_roots=(), source_archive_roots=())
        plan = prepared.record()["storage_plan"]
        # Independently inspect the protected closure; no registry insertion.
        roots = plan["protected_roots"]
        self.assertEqual({r["directory"] for r in roots}, {str(Path(r.directory).resolve()) for r in self.data.roots})
        self.assertIn(str(self.data.fixture.output.resolve()), plan["source_archive_roots"])
        self.assertTrue(scoped.metadata_prepared(archive)["finished"])

    def test_caller_changed_expected_SHA_or_inventory_rejected_before_body(self):
        for options in ({"protected_sha256": {str(self.data.marker): "0"*64}},
                {"protected_roots": (request.reads.InventoryRoot(self.data.roots[0].directory, {}),)}):
            archive = self.data.scoped_open()
            with patch.object(scoped, "iter_selected_entries", side_effect=AssertionError("no body")):
                with self.assertRaises(request.RequestFailure) as failed:
                    request.prepare_selected_request(archive, **options)
            self.assertTrue(failed.exception.report["read_terminal"]["finished"])
            self.assertEqual(failed.exception.report["read_terminal"]["read_ledger"]["completed_read_occurrences"], self.data.metadata_count)

    def test_saved_JSON_foreign_handle_copy_and_foreign_storage_run_never_restore_authority(self):
        _, prepared = self.prepare()
        saved = prepared.record()
        for fake in (saved, {}, object.__new__(request.RequestPreparation)):
            with self.assertRaises(ValueError): request._issued(fake)
        for fake in (saved["read_terminal"], {}, object.__new__(scoped.ScopedArchive)):
            with self.assertRaises(ValueError): request.prepare_selected_request(fake)
        saved["prepared_v2_groups"] = 0
        self.assertGreater(prepared.record()["prepared_v2_groups"], 0)
        with self.assertRaises(AttributeError): prepared.groups = ()
        other_plan = storage.plan_saved_run([], original_denominators=self.data.denominators)
        other_run = storage.begin_storage(other_plan, str(self.data.fixture.root / "foreign-storage"))
        with self.assertRaises(ValueError): request.request_ledger(prepared, other_run)
        storage.finish(other_run)

    def test_count_and_selector_contract_rejects_bool_duplicate_missing_and_wrong_request(self):
        archive = self.data.scoped_open()
        metadata = scoped.metadata_prepared(archive)
        scoped.finish_scoped_archive(archive)
        changes = []
        bad = deepcopy(metadata); bad["selected_completion"]["pairs"] = True; changes.append(bad)
        bad = deepcopy(metadata); bad["selected_group_declarations"][0]["group_index"] = True; changes.append(bad)
        bad = deepcopy(metadata); bad["selected_group_declarations"][0]["original"]["selector_indices"][0] = True; changes.append(bad)
        bad = deepcopy(metadata); bad["selected_group_declarations"].pop(); changes.append(bad)
        for bad in changes:
            with self.assertRaises(ValueError): request._counts(bad, request.RequestLimits())


if __name__ == "__main__": unittest.main()
