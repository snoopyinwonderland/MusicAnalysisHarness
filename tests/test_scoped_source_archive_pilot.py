"""Genuine packet bodies with explicitly mocked whole ancestry metadata.

The fixture does NOT prove real 40-read historical metadata admission; the root
actual pilot must verify that through the unpatched pure metadata consumer.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import scoped_source_archive_pilot as pilot
from musicanote_harness import shared_source_archive_bridge as frozen_bridge
from musicanote_harness import cross_batch_read_budget as budget
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import native_progression_contrast as legacy
from test_shared_source_archive_bridge import BridgePacketFixture
import test_source_progression_replay_trial as factory


class ScopedPacketFixture(BridgePacketFixture):
    def selected_reads(self, source_index=0, completion_index=0):
        paths = [batch[name]["artifact"] for batch in self.rows[source_index]["jobs"][completion_index]["batches"]
            for name in ("comparison", "explanation")]
        by_path = {r.path: r for r in self.reads[self.metadata_count:]}
        return [*self.reads[:self.metadata_count], *[by_path[p] for p in paths]]

    def scoped_plan(self, *, source_index=0, completion_index=0, reads=None, **options):
        return pilot.plan_scoped_reads(str(self.fixture.output), self.selected_reads(source_index, completion_index) if reads is None else reads,
            source_index=source_index, completion_index=completion_index,
            original_denominators=self.denominators, registered_sha256=self.registered,
            inventory_roots=self.roots, **options)

    def scoped_open(self, plan=None):
        with patch.object(pilot, "_load_metadata", side_effect=self.mocked_metadata):
            return pilot.open_scoped_archive(self.scoped_plan() if plan is None else plan)


class ScopedPilotControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory.ReplayPacketStorageTests.setUpClass()
        cls.addClassCleanup(factory.ReplayPacketStorageTests.doClassCleanups)

    def setUp(self): self.data = ScopedPacketFixture(self)

    def assert_counts(self, report):
        self.assertEqual(report["original_denominators"], self.data.denominators)
        whole, selected, omitted = [report[k] for k in ("whole_original", "selected_completion", "omitted_completions")]
        for name in whole: self.assertEqual(whole[name], selected[name] + omitted[name], name)
        self.assertEqual((whole["completion_requests"], selected["completion_requests"], omitted["completion_requests"]), (4, 1, 3))
        self.assertFalse(any(report["flags"].values()))

    def test_one_completion_whole_metadata_same_account_all_bundles_source_once(self):
        handle = self.data.scoped_open()
        initial = pilot.metadata_prepared(handle)
        self.assert_counts(initial)
        self.assertEqual(initial["metadata_read_occurrences"], self.data.metadata_count)
        source = pilot.source_prepared(handle)
        self.assertIs(source, pilot.source_prepared(handle))
        bundle_ids = {j["bundle"]["record_ref"]["record_id"] for j in self.data.rows[0]["jobs"]}
        self.assertEqual(set(source.export_source()["bundles"]), bundle_ids)
        self.assertFalse(initial["selected_body_terminal_validated"])
        batches = list(pilot.iter_selected_entries(handle))
        self.assertEqual(len(batches), len(self.data.rows[0]["jobs"][0]["batches"]))
        groups = pilot.prepare_selected_groups(handle)
        self.assertEqual(groups, pilot.prepare_selected_groups(handle))
        self.assertTrue(all(shared._issued(group).source is source for group in groups))
        final = pilot.finish_scoped_archive(handle)
        self.assert_counts(final)
        self.assertTrue(final["selected_completion_body_join_complete"])
        self.assertTrue(final["selected_source_intrinsic_groups_complete"])
        self.assertFalse(final["full_archive_complete"])
        self.assertFalse(final["all_original_indexed_batches_join_validated"])
        reads = self.data.selected_reads()
        self.assertEqual(final["read_ledger"]["completed_read_occurrences"], len(reads))
        self.assertEqual(final["read_ledger"]["decoded_attempt_bytes"], sum(r.decoded_bytes for r in reads))
        actual = [a["path"] for a in final["read_ledger"]["attempts"]]
        self.assertEqual(actual, [r.path for r in reads])
        self.assertEqual(final["omitted_original_completion_requests"], 3)

    def test_other_original_completion_selection_preserves_exact_request_and_groups(self):
        handle = self.data.scoped_open(self.data.scoped_plan(source_index=1, completion_index=1))
        before = pilot.metadata_prepared(handle)
        self.assertEqual(before["selection"], [1, 1])
        declarations = before["selected_group_declarations"]
        self.assertEqual(len(before["original_group_declarations"]), before["whole_original"]["groups"])
        list(pilot.iter_selected_entries(handle))
        groups = pilot.prepare_selected_groups(handle)
        sounds = {s["sound_ref"]: s for s in pilot.source_prepared(handle).export_source()["source_scope"]["sound_facts"]}
        for declaration, group in zip(declarations, groups):
            catalog = group.export_catalog()
            original = declaration["original"]
            self.assertEqual(catalog["group"]["original_selector_indices"], original["selector_indices"])
            for key in ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref"):
                self.assertEqual(catalog["group"][key], original[key])
            for task in group.iter_blocks():
                for pair in shared.compare_block(group, task)["pairs"]:
                    i, j = pair["entry_indices"]
                    self.assertEqual(shared.materialize_pair(group, pair), legacy._pair(catalog["facets"][i], catalog["facets"][j], sounds))
        self.assertTrue(pilot.finish_scoped_archive(handle)["selected_source_intrinsic_groups_complete"])

    def test_skip_reorder_extra_metadataonly_wrongphase_rejected_before_source_or_body(self):
        full = self.data.selected_reads()
        m = self.data.metadata_count
        altered = [full[:-1], [*full, replace(full[0], read_id="extra")], full[:m],
            [*full[:m], full[m + 1], full[m], *full[m + 2:]],
            [*full[:m], replace(full[m], phase="metadata"), *full[m + 1:]],
            # Fixture jobs intentionally share content-addressed body files.
            # Substitute a genuinely different registered metadata artifact.
            [*full[:m], replace(full[0], read_id="foreign-registered-body", phase="body"), *full[m + 1:]]]
        for reads in altered:
            with self.subTest(paths=[r.path for r in reads[m:]]):
                with patch.object(shared, "prepare_saved_source", side_effect=AssertionError("no prefix source")):
                    with self.assertRaises(pilot.ScopedFailure) as failed:
                        self.data.scoped_open(self.data.scoped_plan(reads=reads))
                self.assertEqual(failed.exception.report["read_ledger"]["completed_read_occurrences"], m)
                self.assertFalse(failed.exception.report["read_ledger"]["submitted_read_set_complete"] and len(reads) != m)
                self.assertEqual(failed.exception.report["plan"]["read_plan"]["original_denominators"], self.data.denominators)

    def test_unknown_or_cumulative_hold_precedes_all_metadata_parsing(self):
        reads = self.data.selected_reads()
        plans = [self.data.scoped_plan(read_limits=budget.ReadLimits(max_total_decoded_bytes=0)),
            self.data.scoped_plan(reads=[*reads[:-1], replace(reads[-1], decoded_bytes=None)])]
        with patch.object(pilot, "_load_metadata", side_effect=AssertionError("no metadata prefix")) as parser:
            for plan in plans:
                with self.assertRaises(budget.WholeReadHold): pilot.open_scoped_archive(plan)
                self.assertEqual(plan.record()["read_plan"]["original_denominators"], self.data.denominators)
            parser.assert_not_called()

    def test_unpatched_metadata_consumer_rejects_boolean_count_before_ancestor(self):
        # This uses the REAL metadata entry point, but is only an early reject,
        # not a substitute for the root's full real 40-read ancestry admission.
        report_path = self.data.fixture.output / "report.json"
        report = deepcopy(self.data.report); report["saved_terminal_jobs"] = True
        report_path.write_text(json.dumps(report), encoding="utf-8")
        self.data.registered[str(report_path)] = frozen_bridge.old._file_sha(report_path)
        roots = tuple(budget.InventoryRoot(r.directory, {p: self.data.registered[p] for p in r.registered_sha256})
            for r in self.data.roots)
        reads = []
        for i, path in enumerate(self.data.fixture.output / name for name in ("report.json", "run-plan.json", "context-index.json")):
            raw = path.read_bytes()
            reads.append(budget.ReadInput("real-metadata-" + str(i), str(path), self.data.registered[str(path)],
                len(raw), len(raw), phase="metadata"))
        plan = pilot.plan_scoped_reads(str(self.data.fixture.output), reads, source_index=0, completion_index=0,
            original_denominators=self.data.denominators, registered_sha256=self.data.registered, inventory_roots=roots)
        with self.assertRaises(pilot.ScopedFailure) as failed: pilot.open_scoped_archive(plan)
        self.assertIn("integer", str(failed.exception))
        self.assertEqual(failed.exception.report["read_ledger"]["completed_read_occurrences"], 3)

    def test_one_reader_only_and_no_growing_ledger_copy_each_batch(self):
        with patch.object(budget, "begin_reads", wraps=budget.begin_reads) as readers:
            handle = self.data.scoped_open()
            with patch.object(budget, "read_ledger", wraps=budget.read_ledger) as ledgers:
                list(pilot.iter_selected_entries(handle))
                self.assertEqual(ledgers.call_count, 0)
            pilot.prepare_selected_groups(handle)
            final = pilot.finish_scoped_archive(handle)
            self.assertEqual(readers.call_count, 1)
        self.assertTrue(final["selected_source_intrinsic_groups_complete"])

    def test_invalid_or_boolean_selection_closed_types_and_forged_handles(self):
        for source, completion in ((True, 0), (0, False), (-1, 0), (0, 0.0)):
            with self.assertRaises(ValueError):
                self.data.scoped_plan(source_index=source, completion_index=completion, reads=self.data.selected_reads())
        plan = self.data.scoped_plan(source_index=20, reads=self.data.selected_reads())
        with self.assertRaises(pilot.ScopedFailure): self.data.scoped_open(plan)
        plan = self.data.scoped_plan()
        copy = plan.record(); copy["read_plan"]["reads"].clear()
        handle = self.data.scoped_open(plan)
        metadata = pilot.metadata_prepared(handle); metadata["original_group_declarations"].clear()
        self.assertTrue(pilot.metadata_prepared(handle)["original_group_declarations"])
        for fake in (copy, {}, object.__new__(pilot.ScopedPlan)):
            with self.assertRaises(ValueError): pilot.open_scoped_archive(fake)
        for fake in (metadata, {}, object.__new__(pilot.ScopedArchive)):
            with self.assertRaises(ValueError): pilot.finish_scoped_archive(fake)
        for cls in (pilot.ScopedPlan, pilot.ScopedArchive):
            with self.assertRaises(ValueError): cls()
        with self.assertRaises(AttributeError): plan.selection = [0, 1]
        with self.assertRaises(ValueError): self.data.scoped_open(plan)

    def test_finish_after_lastyield_cannot_resume_promote_or_issue_cached_capability(self):
        handle = self.data.scoped_open()
        source = pilot.source_prepared(handle)
        iterator = pilot.iter_selected_entries(handle)
        for _ in self.data.rows[0]["jobs"][0]["batches"]: next(iterator)
        final = pilot.finish_scoped_archive(handle)
        self.assertTrue(final["read_ledger"]["submitted_read_set_complete"])
        self.assertFalse(final["selected_completion_body_join_complete"])
        self.assertFalse(final["selected_body_terminal_validated"])
        with self.assertRaises(ValueError): next(iterator)
        for fn in (pilot.source_prepared, pilot.source_preflight, pilot.preflight_selected_groups, pilot.prepare_selected_groups):
            with self.assertRaises(ValueError): fn(handle)
        self.assertFalse(pilot.finish_scoped_archive(handle)["selected_completion_body_join_complete"])

    def test_earlyclose_and_active_concurrency_do_not_restart_or_join_prefix(self):
        handle = self.data.scoped_open()
        iterator = pilot.iter_selected_entries(handle)
        next(iterator)
        with self.assertRaises(ValueError): next(pilot.iter_selected_entries(handle))
        with self.assertRaises(ValueError): pilot.prepare_selected_groups(handle)
        iterator.close()
        with self.assertRaises(ValueError): list(pilot.iter_selected_entries(handle))
        with self.assertRaises(ValueError): pilot.source_prepared(handle)
        self.assertFalse(pilot.finish_scoped_archive(handle)["selected_completion_body_join_complete"])

    def test_body_runtime_read_failure_nonrefundable_and_cached_source_forbidden(self):
        reads = self.data.selected_reads(); m = self.data.metadata_count
        changed = [*reads[:m], replace(reads[m], decoded_bytes=reads[m].decoded_bytes + 1), *reads[m + 1:]]
        handle = self.data.scoped_open(self.data.scoped_plan(reads=changed))
        pilot.source_prepared(handle)
        with self.assertRaises(budget.ReadFailure): list(pilot.iter_selected_entries(handle))
        with self.assertRaises(ValueError): pilot.source_prepared(handle)
        report = pilot.finish_scoped_archive(handle)
        self.assertEqual(report["read_ledger"]["failed_read_occurrences"], 1)
        self.assertGreater(report["read_ledger"]["decoded_attempt_bytes"], sum(r.decoded_bytes for r in reads[:m]))
        self.assertFalse(report["selected_source_intrinsic_groups_complete"])
        self.assert_counts(report)

    def test_body_array_ordinal_and_terminal_failure_cannot_issue_groups(self):
        for phase in ("ordinal", "terminal"):
            handle = self.data.scoped_open()
            if phase == "terminal":
                with patch.object(pilot, "_job", side_effect=ValueError("mock terminal disagreement")):
                    with self.assertRaises(ValueError): list(pilot.iter_selected_entries(handle))
            else:
                real_record = frozen_bridge._record
                def swapped(info, prefix, reader, hashes):
                    result = real_record(info, prefix, reader, hashes)
                    if prefix == pilot.replay.engine.roles.PREFIX:
                        result["paths"] = list(reversed(result["paths"]))
                    return result
                with patch.object(pilot, "_batch", return_value=None), patch.object(pilot, "_record", side_effect=swapped):
                    with self.assertRaises(ValueError): list(pilot.iter_selected_entries(handle))
            with self.assertRaises(ValueError): pilot.prepare_selected_groups(handle)
            self.assertFalse(pilot.finish_scoped_archive(handle)["selected_completion_body_join_complete"])

    def test_source_and_all_group_preflights_report_cap_holds_without_shrink(self):
        handle = self.data.scoped_open(self.data.scoped_plan(source_limits=shared.SourceLimits(max_source_record_bytes=0)))
        plan = pilot.source_preflight(handle)
        self.assertTrue(plan["reasons"])
        with self.assertRaises(pilot.ScopedFailure) as held: pilot.source_prepared(handle)
        self.assert_counts(held.exception.report["metadata"])
        self.assertEqual(pilot.finish_scoped_archive(handle)["prepared_groups"], 0)
        handle = self.data.scoped_open(self.data.scoped_plan(group_limits=shared.GroupLimits(max_entries=0)))
        list(pilot.iter_selected_entries(handle))
        plans = pilot.preflight_selected_groups(handle)
        self.assertEqual(len(plans), pilot.metadata_prepared(handle)["selected_completion"]["groups"])
        self.assertTrue(any(p["plan"]["reasons"] for p in plans))
        with patch.object(shared, "prepare_saved_group", side_effect=AssertionError("no favourable prefix")):
            with self.assertRaises(pilot.ScopedFailure) as held: pilot.prepare_selected_groups(handle)
        metadata = held.exception.report["metadata"]
        self.assert_counts(metadata)
        self.assertEqual(metadata["prepared_groups"], 0)
        self.assertEqual(len(metadata["group_preflights"]), len(plans))
        with self.assertRaises(ValueError): pilot.source_prepared(handle)
        report = pilot.finish_scoped_archive(handle)
        self.assertTrue(report["selected_completion_body_join_complete"])
        self.assertFalse(report["selected_source_intrinsic_groups_complete"])

    def test_terminal_rechecks_registered_roots_and_stops_cached_groups(self):
        handle = self.data.scoped_open()
        list(pilot.iter_selected_entries(handle)); pilot.prepare_selected_groups(handle)
        self.assertTrue(pilot.finish_scoped_archive(handle)["selected_source_intrinsic_groups_complete"])
        (self.data.fixture.output / "foreign.json").write_bytes(b"{}")
        report = pilot.finish_scoped_archive(handle)
        self.assertFalse(report["selected_completion_body_join_complete"])
        self.assertFalse(report["selected_source_intrinsic_groups_complete"])
        with self.assertRaises(ValueError): pilot.prepare_selected_groups(handle)

    def test_never_calls_old_factories_registries_producers_or_pair_runner(self):
        forbidden = AssertionError("not an old authority or producer bridge")
        with (patch.object(frozen_bridge, "open_archive", side_effect=forbidden),
                patch.object(frozen_bridge, "plan_archive_reads", side_effect=forbidden),
                patch.object(frozen_bridge, "_archive", side_effect=forbidden),
                patch.object(frozen_bridge.kernels, "load_saved_plan", side_effect=forbidden),
                patch.object(frozen_bridge.kernels, "_issued", side_effect=forbidden),
                patch.object(pilot.replay.engine, "prepare_replay", side_effect=forbidden),
                patch.object(pilot.replay.engine.native, "prepare_lattice", side_effect=forbidden),
                patch.object(pilot.replay.engine.roles, "prepare_explanations", side_effect=forbidden),
                patch.object(shared, "compare_block", side_effect=forbidden)):
            handle = self.data.scoped_open()
            list(pilot.iter_selected_entries(handle))
            pilot.prepare_selected_groups(handle)
            self.assertTrue(pilot.finish_scoped_archive(handle)["selected_source_intrinsic_groups_complete"])


if __name__ == "__main__": unittest.main()
