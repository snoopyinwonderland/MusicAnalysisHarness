"""Genuine saved packet bodies with an EXPLICITLY mocked ancestry stage.

No real archive is read. The public bridge owns a genuine cumulative reader and
performs original packet/ordinal/terminal and shared intrinsic validation. These
fixtures do not prove that a real 40-read historical ancestry chain is admitted.
"""
from copy import deepcopy
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import shared_source_archive_bridge as bridge
from musicanote_harness import cross_batch_read_budget as budget
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import native_progression_contrast as legacy
import test_source_progression_replay_trial as factory


class BridgePacketFixture:
    """Root tests may compose this fixture; call factory class setup once first."""
    def __init__(self, testcase):
        self.fixture = factory.ReplayPacketStorageTests()
        self.fixture.setUp()
        testcase.addCleanup(self.fixture.doCleanups)
        self.report, _, _ = self.fixture.run_mock()
        self.rows = self.fixture.rows()
        self.original_plan = json.loads((self.fixture.output / "run-plan.json").read_text(encoding="utf8"))
        self.marker = self.fixture.root / "mock-ancestry-stage.json"
        self.marker.write_text('{"mock_ancestry":true}', encoding="utf8")
        self.registered = {**self.fixture.data["hashes"], **self.report["artifact_hashes"]}
        for path in (self.fixture.output / "report.json", self.fixture.parent / "report.json", self.marker):
            self.registered[str(path)] = bridge.old._file_sha(path)
        self.denominators = {"denominators": self.original_plan["denominators"], **{
            k: self.original_plan[k] for k in ("planned_distinct_sources", "planned_completion_requests",
                "planned_selector_occurrences", "planned_batches")}}
        paths = [self.marker]
        for row in self.rows:
            paths.extend(Path(row[k]["artifact"]) for k in ("fresh_lattice", "binding", "plan"))
            for job in row["jobs"]:
                paths.extend(Path(job[k]["artifact"]) for k in ("bundle", "job"))
        self.metadata_count = len(paths)
        for row in self.rows:
            for job in row["jobs"]:
                for batch in job["batches"]:
                    paths.extend(Path(batch[k]["artifact"]) for k in ("comparison", "explanation"))
        self.reads = []
        for i, path in enumerate(paths):
            physical = path.read_bytes()
            raw = gzip.decompress(physical) if path.suffix == ".gz" else physical
            self.reads.append(budget.ReadInput("original-read-" + str(i), str(path), self.registered[str(path)],
                len(physical), len(raw), "gzip-json" if path.suffix == ".gz" else "json",
                "metadata" if i < self.metadata_count else "body"))
        self.roots = tuple(budget.InventoryRoot(str(root), {
            str(p.resolve()): self.registered[str(p.resolve())] for p in root.rglob("*") if p.is_file()})
            for root in (self.fixture.output, self.fixture.parent))

    def plan(self, *, reads=None, **options):
        return bridge.plan_archive_reads(str(self.fixture.output), self.reads if reads is None else reads,
            original_denominators=self.denominators, registered_sha256=self.registered,
            inventory_roots=self.roots, **options)

    def mocked_metadata(self, data, reader):
        """Only ancestry is mocked; all read jobs are owned and bodies genuine."""
        assert reader.read(self.marker) == {"mock_ancestry": True}
        cases, jobs = [], []
        for si, row in enumerate(self.rows):
            case = deepcopy(self.fixture.data["cases"][si])
            case["original_row"] = {}
            cases.append(case)
            fresh = bridge._record(row["fresh_lattice"], bridge.replay.engine.native.PREFIX, reader, self.registered)
            binding = bridge._record(row["binding"], bridge.replay.engine.BINDING_PREFIX, reader, self.registered)
            plan = bridge._record(row["plan"], bridge.replay.engine.PLAN_PREFIX, reader, self.registered)
            bridge.replay._binding(binding, case, fresh)
            bridge.replay._plan(plan, case, self.fixture.limits)
            for ci, (job, control) in enumerate(zip(row["jobs"], case["completion_controls"])):
                jobs.append(bridge._completion(job, case, binding, plan, control, si, ci, reader,
                    self.registered, data["settings"], self.fixture.limits))
        return {"report": deepcopy(self.report), "plan": deepcopy(self.original_plan), "cases": cases,
            "jobs": jobs, "hashes": deepcopy(self.registered), "inventories": [
                {"directory": r.directory, "registered_sha256": deepcopy(r.registered_sha256)} for r in self.roots],
            "replay_limits": self.fixture.limits, "metadata_authenticated": True}

    def open(self, plan=None):
        with patch.object(bridge, "_load_metadata", side_effect=self.mocked_metadata):
            return bridge.open_archive(self.plan() if plan is None else plan)

    def consume(self, handle):
        for si, row in enumerate(self.rows):
            for ci, _ in enumerate(row["jobs"]):
                list(bridge.iter_completion_entries(handle, si, ci))


class BridgePacketControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory.ReplayPacketStorageTests.setUpClass()
        cls.addClassCleanup(factory.ReplayPacketStorageTests.doClassCleanups)

    def setUp(self):
        self.data = BridgePacketFixture(self)

    def test_all_four_original_jobs_use_single_account_and_shared_source_once(self):
        handle = self.data.open()
        initial = bridge.metadata_prepared(handle)
        self.assertEqual(initial["original_denominators"], self.data.denominators)
        self.assertEqual(initial["read_ledger"]["completed_read_occurrences"], self.data.metadata_count)
        original_keys = {"source_identity_sha256", "scope_ref", "lattice_ref", "completion_request_ref",
            "key_ref", "bundle_ref", "selector_indices", "planned_entries", "planned_pairs", "planned_block_tasks", "block_size"}
        for declaration in initial["original_group_declarations"]:
            self.assertEqual(set(declaration["original"]), original_keys)
            self.assertIn(declaration["source_index"], (0, 1))
            self.assertIn(declaration["completion_index"], (0, 1))
        forbidden = AssertionError("bridge must not invoke native or role producer")
        with patch.object(bridge.replay.engine, "prepare_replay", side_effect=forbidden), \
                patch.object(bridge.replay.engine.native, "prepare_lattice", side_effect=forbidden), \
                patch.object(bridge.replay.engine.roles, "prepare_explanations", side_effect=forbidden):
            self.data.consume(handle)
            groups = []
            for si, row in enumerate(self.data.rows):
                first = bridge.source_prepared(handle, si)
                self.assertIs(first, bridge.source_prepared(handle, si))
                for ci, _ in enumerate(row["jobs"]):
                    prepared = bridge.prepare_original_groups(handle, si, ci)
                    self.assertEqual(prepared, bridge.prepare_original_groups(handle, si, ci))
                    groups.extend(prepared)
        final = bridge.finish_archive(handle)
        self.assertTrue(final["all_original_indexed_batches_join_validated"])
        self.assertTrue(final["all_original_source_intrinsic_groups_validated"])
        self.assertEqual(final["completed_original_completions"], 4)
        self.assertEqual(final["read_ledger"]["decoded_attempt_bytes"], sum(r.decoded_bytes for r in self.data.reads))
        self.assertEqual(final["prepared_groups"], len(groups))
        self.assertFalse(any(final["flags"].values()))
        self.assertIsNone(final["selected"])
        self.assertNotEqual(groups[0].group_ref, groups[len(groups) // 4].group_ref)

    def test_shared_group_pair_restores_exact_legacy_and_original_selector_positions(self):
        handle = self.data.open()
        list(bridge.iter_completion_entries(handle, 0, 0))
        groups = bridge.prepare_original_groups(handle, 0, 0)
        source = bridge.source_prepared(handle, 0).export_source()
        sounds = {r["sound_ref"]: r for r in source["source_scope"]["sound_facts"]}
        checked = 0
        for group in groups:
            catalog = group.export_catalog()
            for task in group.iter_blocks():
                for pair in shared.compare_block(group, task)["pairs"]:
                    i, j = pair["entry_indices"]
                    self.assertEqual(shared.materialize_pair(group, pair),
                        legacy._pair(catalog["facets"][i], catalog["facets"][j], sounds))
                    self.assertEqual(pair["original_selector_indices"], [
                        catalog["group"]["original_selector_indices"][i], catalog["group"]["original_selector_indices"][j]])
                    checked += 1
        self.assertGreater(checked, 0)
        self.assertFalse(bridge.finish_archive(handle)["all_original_indexed_batches_join_validated"])

    def test_whole_read_cap_or_unknown_holds_before_ancestry_or_body_parse(self):
        plans = (self.data.plan(read_limits=budget.ReadLimits(max_total_decoded_bytes=0)),
            self.data.plan(reads=[*self.data.reads[:-1], replace(self.data.reads[-1], decoded_bytes=None)]))
        with patch.object(bridge, "_load_metadata", side_effect=AssertionError("must not parse prefix")) as metadata:
            for plan in plans:
                with self.assertRaises(budget.WholeReadHold):
                    bridge.open_archive(plan)
                self.assertEqual(plan.record()["read_plan"]["original_denominators"], self.data.denominators)
                self.assertFalse(plan.record()["original_membership_authenticated"])
            metadata.assert_not_called()

    def test_early_close_after_last_yield_still_not_terminal_or_restartable(self):
        handle = self.data.open()
        iterator = bridge.iter_completion_entries(handle, 0, 0)
        for _ in self.data.rows[0]["jobs"][0]["batches"]:
            next(iterator)
        iterator.close()
        with self.assertRaises(ValueError):
            list(bridge.iter_completion_entries(handle, 0, 0))
        with self.assertRaises(ValueError):
            bridge.prepare_original_groups(handle, 0, 0)
        final = bridge.finish_archive(handle)
        self.assertEqual(final["completed_original_completions"], 0)
        self.assertEqual(final["incomplete_original_completions"], 4)
        self.assertFalse(final["all_original_indexed_batches_join_validated"])

    def test_finish_after_final_yield_cannot_be_promoted_by_generator_resume(self):
        handle = self.data.open()
        for source, completion in ((0, 0), (0, 1), (1, 0)):
            list(bridge.iter_completion_entries(handle, source, completion))
        iterator = bridge.iter_completion_entries(handle, 1, 1)
        for _ in self.data.rows[1]["jobs"][1]["batches"]:
            next(iterator)
        before = bridge.finish_archive(handle)
        self.assertTrue(before["read_ledger"]["submitted_read_set_complete"])
        self.assertEqual(before["completed_original_completions"], 3)
        self.assertFalse(before["all_original_indexed_batches_join_validated"])
        with self.assertRaises(ValueError):
            next(iterator)
        after = bridge.finish_archive(handle)
        self.assertEqual(after["completed_original_completions"], 3)
        self.assertEqual(after["validated_batches"], before["validated_batches"])
        self.assertFalse(after["all_original_indexed_batches_join_validated"])
        self.assertFalse(after["all_original_source_intrinsic_groups_validated"])

    def test_missing_extra_or_reordered_read_occurrences_cannot_complete(self):
        original = self.data.reads
        for index, altered in enumerate((original[:-1], [*original, replace(original[0], read_id="extra")],
                [*original[:self.data.metadata_count], original[self.data.metadata_count + 1], original[self.data.metadata_count],
                    *original[self.data.metadata_count + 2:]])):
            with self.subTest(index=index):
                with patch.object(shared, "prepare_saved_source", side_effect=AssertionError("no prefix source work")):
                    with self.assertRaises(bridge.ArchiveFailure) as failure:
                        self.data.open(self.data.plan(reads=altered))
                self.assertEqual(failure.exception.report["read_ledger"]["completed_read_occurrences"], self.data.metadata_count)
                self.assertEqual(failure.exception.report["plan"]["read_plan"]["original_denominators"], self.data.denominators)

    def test_metadata_only_and_false_body_phase_rejected_before_first_body(self):
        plans = (self.data.reads[:self.data.metadata_count], [*self.data.reads[:self.data.metadata_count],
            replace(self.data.reads[self.data.metadata_count], phase="metadata"), *self.data.reads[self.data.metadata_count + 1:]])
        for reads in plans:
            with self.subTest(reads=len(reads)):
                with self.assertRaises(bridge.ArchiveFailure) as failed:
                    self.data.open(self.data.plan(reads=reads))
                self.assertEqual(failed.exception.report["read_ledger"]["completed_read_occurrences"], self.data.metadata_count)

    def test_mutable_export_and_foreign_handle_cannot_authorize(self):
        plan = self.data.plan()
        copy = plan.record()
        copy["read_plan"]["reads"].clear()
        handle = self.data.open(plan)
        exported = bridge.metadata_prepared(handle)
        exported["groups"].clear()
        self.assertTrue(bridge.metadata_prepared(handle)["groups"])
        for foreign in (None, {}, object(), object.__new__(bridge.SavedArchive)):
            with self.assertRaises(ValueError):
                bridge.finish_archive(foreign)
        with self.assertRaises(ValueError):
            bridge.SavedArchive()
        with self.assertRaises(ValueError):
            self.data.open(plan)

    def test_group_cap_hold_keeps_all_original_group_and_pair_denominators(self):
        handle = self.data.open(self.data.plan(group_limits=shared.GroupLimits(max_entries=0)))
        initial = bridge.metadata_prepared(handle)
        list(bridge.iter_completion_entries(handle, 0, 0))
        with self.assertRaises(bridge.ArchiveFailure) as held:
            bridge.prepare_original_groups(handle, 0, 0)
        self.assertEqual(held.exception.report["metadata"]["whole_original"]["original_denominators"], self.data.denominators)
        self.assertEqual(held.exception.report["metadata"]["whole_original"]["planned_pairs"], initial["planned_pairs"])
        self.assertEqual(len(held.exception.report["metadata"]["whole_original"]["groups"]), len(initial["groups"]))
        self.assertFalse(bridge.finish_archive(handle)["all_original_source_intrinsic_groups_validated"])

    def test_reordered_completion_and_boolean_positions_rejected(self):
        handle = self.data.open()
        for source, completion in ((0, 1), (1, 0), (True, 0), (0, True)):
            with self.assertRaises(ValueError):
                list(bridge.iter_completion_entries(handle, source, completion))
        self.assertEqual(bridge.finish_archive(handle)["completed_original_completions"], 0)

    def test_boolean_group_positions_and_cached_post_terminal_handles_rejected(self):
        handle = self.data.open()
        list(bridge.iter_completion_entries(handle, 0, 0))
        groups = bridge.prepare_original_groups(handle, 0, 0)
        self.assertTrue(groups)
        for source, completion in ((False, 0), (0, False), (0, True)):
            with self.assertRaises(ValueError):
                bridge.prepare_original_groups(handle, source, completion)
        bridge.finish_archive(handle)
        with self.assertRaises(ValueError):
            bridge.prepare_original_groups(handle, 0, 0)
        with self.assertRaises(ValueError):
            bridge.source_prepared(handle, 0)

    def test_whole_source_cap_hold_keeps_all_original_denominators(self):
        handle = self.data.open(self.data.plan(source_limits=shared.SourceLimits(max_source_record_bytes=0)))
        with self.assertRaises(bridge.ArchiveFailure) as held:
            bridge.source_prepared(handle, 0)
        self.assertEqual(held.exception.report["metadata"]["whole_original"]["original_denominators"], self.data.denominators)
        final = bridge.finish_archive(handle)
        self.assertEqual(len(final["source_holds"]), 1)
        self.assertEqual(final["incomplete_original_completions"], 4)
        self.assertFalse(final["all_original_source_intrinsic_groups_validated"])

    def test_historical_phase28_code_collision_and_later_children_not_accepted(self):
        path = Path(self.data.fixture.code).resolve()
        ancestor = {"code": {str(path): "a" * 64, "ancestor": "b" * 64}}
        good = {"code": deepcopy(ancestor["code"])}
        with patch.object(bridge.replay.parent, "_new_code_paths", return_value={path}):
            bridge._historical_phase28_code(good, ancestor)
            bad = deepcopy(good)
            bad["code"][str(path)] = "c" * 64
            with self.assertRaisesRegex(ValueError, "hash_conflict"):
                bridge._historical_phase28_code(bad, ancestor)
            bad = deepcopy(good)
            bad["code"]["later-child"] = "d" * 64
            with self.assertRaisesRegex(ValueError, "historical_code_extension"):
                bridge._historical_phase28_code(bad, ancestor)

    def test_real_metadata_entry_point_rejects_boolean_count_before_ancestor(self):
        report_path = self.data.fixture.output / "report.json"
        report = deepcopy(self.data.report)
        report["saved_terminal_jobs"] = True
        report_path.write_text(json.dumps(report), encoding="utf8")
        self.data.registered[str(report_path)] = bridge.old._file_sha(report_path)
        roots = tuple(budget.InventoryRoot(r.directory, {p: self.data.registered[p] for p in r.registered_sha256})
            for r in self.data.roots)
        paths = [report_path, self.data.fixture.output / "run-plan.json", self.data.fixture.output / "context-index.json"]
        reads = []
        for i, path in enumerate(paths):
            raw = path.read_bytes()
            reads.append(budget.ReadInput("metadata-" + str(i), str(path), self.data.registered[str(path)],
                len(raw), len(raw), phase="metadata"))
        plan = bridge.plan_archive_reads(str(self.data.fixture.output), reads,
            original_denominators=self.data.denominators, registered_sha256=self.data.registered,
            inventory_roots=roots)
        with self.assertRaises(bridge.ArchiveFailure) as failure:
            bridge.open_archive(plan)  # No mocked metadata admission here.
        self.assertIn("integer", str(failure.exception))
        self.assertEqual(failure.exception.report["read_ledger"]["completed_read_occurrences"], 3)

    def test_finish_rechecks_inventory_and_no_new_group_after_terminal(self):
        handle = self.data.open()
        self.data.consume(handle)
        self.assertTrue(bridge.finish_archive(handle)["all_original_indexed_batches_join_validated"])
        (self.data.fixture.output / "foreign.txt").write_bytes(b"x")
        self.assertFalse(bridge.finish_archive(handle)["all_original_indexed_batches_join_validated"])
        with self.assertRaises(ValueError):
            bridge.source_prepared(handle, 0)

    def test_library_does_not_call_frozen_loader_or_private_admission_registry(self):
        forbidden = AssertionError("no frozen loader or forged private handle")
        with patch.object(bridge.kernels, "load_saved_plan", side_effect=forbidden), \
                patch.object(bridge.replay, "load_inputs", side_effect=forbidden), \
                patch.object(bridge.kernels, "_issued", side_effect=forbidden):
            handle = self.data.open()
            self.data.consume(handle)
            self.assertTrue(bridge.finish_archive(handle)["all_original_indexed_batches_join_validated"])


if __name__ == "__main__":
    unittest.main()
