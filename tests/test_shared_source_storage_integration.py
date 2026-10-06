"""Genuine small XML saved bodies -> one read account -> source-once storage.

The original request metadata here is explicitly fixture/caller declared.
This does NOT authenticate a historical archive, run a corpus, or evaluate
musical correctness. No native/role producer may run on the saved-only path.
"""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_read_budget as budget
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import shared_source_progression_storage as storage
from musicanote_harness import native_progression_contrast as legacy
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import shared_source_archive_bridge as bridge
import test_shared_source_read_budget_integration as read_fixture
import test_shared_source_archive_bridge as archive_fixture


class SharedSourceStorageIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read_fixture.SharedSourceReadIntegrationTests.setUpClass()
        cls.addClassCleanup(read_fixture.SharedSourceReadIntegrationTests.doClassCleanups)

    def setUp(self):
        self.fixture = read_fixture.SharedSourceReadIntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.denominators = deepcopy(self.fixture.denominators)

    def groups(self):
        reader = budget.begin_reads(self.fixture.plan())
        saved = budget.read_record(reader, "source-once")
        source = shared.prepare_saved_source(saved["scope"], saved["lattice"], bundles=saved["bundles"])
        result = []
        for position in (0, 1):
            entries = reader.read(self.fixture.paths["entries"])["entries"]
            group = shared.prepare_saved_group(source, entries,
                completion_request_ref=read_fixture.request_ref(position), selector_indices=[3, 18], block_size=1)
            info = group.export_catalog()["group"]
            original = {name: deepcopy(info[name]) for name in
                ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref")}
            original.update(source_identity_sha256="0" * 64, selector_indices=[3, 18],
                planned_entries=2, planned_pairs=1, planned_block_tasks=3, block_size=1)
            result.append(storage.GroupInput(original, source, group))
        read_final = budget.finish_reads(reader)
        self.assertTrue(read_final["submitted_read_set_complete"])
        self.assertEqual(read_final["completed_read_occurrences"], 3)
        self.assertEqual(read_final["original_denominators"], self.denominators)
        return result, read_final

    def storage_plan(self, groups, **extra):
        return storage.plan_saved_run(groups, original_denominators=self.denominators,
            protected_sha256=self.fixture.hashes,
            protected_roots=(budget.InventoryRoot(str(self.fixture.archive), self.fixture.hashes),),
            source_archive_roots=(str(self.fixture.archive),), compressed=True, **extra)

    @staticmethod
    def read_gzip(path):
        return json.loads(gzip.decompress(path.read_bytes()))

    def test_saved_read_set_to_two_requests_stores_one_source_and_exact_old_pairs(self):
        forbidden = AssertionError("saved-only integration must not rerun producers")
        with patch.object(native, "prepare_lattice", side_effect=forbidden), \
                patch.object(roles, "explain_prepared", side_effect=forbidden):
            groups, read_final = self.groups()
            self.assertIs(groups[0].source, groups[1].source)
            plan = self.storage_plan(groups)
            self.assertEqual(plan.record()["reasons"], [])
            self.assertEqual(plan.record()["planned_shared_sources"], 1)
            self.assertEqual(plan.record()["planned_declared_upstream_tasks"], 6)
            self.assertEqual(plan.record()["planned_submitted_nonempty_tasks"], 2)
            destination = self.fixture.root / "stored"
            run = storage.begin_storage(plan, destination)
            for i in range(2):
                storage.write_prepared_group(run, i)
            final = storage.finish(run)
        self.assertTrue(final["submitted_group_set_complete"])
        self.assertTrue(final["physical_closure_verified_terminally"])
        self.assertEqual(final["persisted_shared_sources"], 1)
        self.assertEqual(final["summary"]["planned_pairs"], 2)
        self.assertEqual(final["summary"]["persisted_pairs"], 2)
        self.assertEqual(final["summary"]["computed_unpersisted_pairs"], 0)
        self.assertEqual(final["summary"]["uncomputed_pairs"], 0)
        self.assertEqual(final["original_denominators"], self.denominators)
        self.assertEqual(len(list(destination.glob("source-*-catalog.json.gz"))), 1)
        self.assertTrue(all(v is False for v in final["flags"].values()))
        self.assertTrue(all(v is False for v in read_final["flags"].values()))
        self.assertFalse(final["flags"]["physical_original_request_admission"])
        source = self.read_gzip(destination / "source-0000-catalog.json.gz")
        self.assertEqual(source, groups[0].source.export_source())
        sounds = {s["sound_ref"]: s for s in source["source_scope"]["sound_facts"]}
        for i, row in enumerate(groups):
            local = self.read_gzip(destination / f"group-{i:04d}-catalog.json.gz")
            self.assertEqual(local, row.prepared.export_catalog())
            self.assertTrue({"source_scope", "lattice", "bundles", "source_sounds"}.isdisjoint(local))
            self.assertEqual(local["source_catalog_ref"], groups[0].source.source_ref)
            block = self.read_gzip(destination / f"group-{i:04d}-block-000000.json.gz")
            self.assertEqual(block["pairs"][0]["original_selector_indices"], [3, 18])
            self.assertEqual(shared.materialize_pair(row.prepared, block["pairs"][0]),
                legacy._pair(local["facets"][0], local["facets"][1], sounds))
        self.assertNotEqual(groups[0].original["completion_request_ref"], groups[1].original["completion_request_ref"])
        self.assertEqual(groups[0].original["bundle_ref"], groups[1].original["bundle_ref"])
        on_disk = json.loads((destination / "report.json").read_bytes())
        self.assertFalse(on_disk["submitted_group_set_complete"])
        self.assertFalse(on_disk["terminal_persisted"])
        for path, sha in self.fixture.hashes.items():
            self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), sha)

    def test_whole_storage_hold_keeps_two_requests_without_output_or_pair_prefix(self):
        groups, _ = self.groups()
        with patch.object(shared, "compare_block", side_effect=AssertionError("no pair prefix")), \
                patch.object(storage, "_write_payload", side_effect=AssertionError("no output prefix")):
            plan = self.storage_plan(groups, limits=storage.StorageLimits(max_output_bytes=0))
            record = plan.record()
            self.assertIn("whole_output_reservation_exceeds_limit_no_prefix", record["reasons"])
            self.assertEqual(record["planned_submitted_entries"], 4)
            self.assertEqual(record["planned_submitted_pairs"], 2)
            self.assertEqual(record["original_denominators"], self.denominators)
            destination = self.fixture.root / "held"
            with self.assertRaises(storage.WholeRunHold):
                storage.begin_storage(plan, destination)
            self.assertFalse(destination.exists())

    def test_partial_request_storage_cannot_be_promoted_by_completed_read_set(self):
        groups, read_final = self.groups()
        run = storage.begin_storage(self.storage_plan(groups), self.fixture.root / "partial")
        storage.write_prepared_group(run, 0)
        final = storage.finish(run)
        self.assertTrue(read_final["submitted_read_set_complete"])
        self.assertFalse(final["submitted_group_set_complete"])
        self.assertEqual(final["summary"]["persisted_pairs"], 1)
        self.assertEqual(final["summary"]["uncomputed_pairs"], 1)
        self.assertEqual(final["summary"]["unpersisted_pairs"], 1)
        self.assertEqual(final["original_denominators"], self.denominators)
        self.assertFalse(final["flags"]["full_contrast_evaluated"])


class OriginalPacketStorageIntegrationTests(unittest.TestCase):
    """Ancestry is mocked; genuine saved packets use the public bridge APIs.

    Only the first fixture source's two requests are submitted for storage.
    The original four-request denominators are retained without claiming that
    this subset, or mocked ancestry, authenticates the real historical archive.
    """
    @classmethod
    def setUpClass(cls):
        archive_fixture.factory.ReplayPacketStorageTests.setUpClass()
        cls.addClassCleanup(archive_fixture.factory.ReplayPacketStorageTests.doClassCleanups)

    def test_public_original_membership_to_source_once_subset_storage_keeps_full_denominators(self):
        fixture = archive_fixture.BridgePacketFixture(self)
        handle = fixture.open()
        initial = bridge.metadata_prepared(handle)
        declarations = [d for d in initial["original_group_declarations"] if d["source_index"] == 0]
        forbidden = AssertionError("saved-only packet bridge must not rerun producers")
        with patch.object(bridge.replay.engine, "prepare_replay", side_effect=forbidden), \
                patch.object(bridge.replay.engine.native, "prepare_lattice", side_effect=forbidden), \
                patch.object(bridge.replay.engine.roles, "prepare_explanations", side_effect=forbidden):
            fixture.consume(handle)
            source = bridge.source_prepared(handle, 0)
            prepared = {ci: bridge.prepare_original_groups(handle, 0, ci) for ci in (0, 1)}
            groups = [storage.GroupInput(d["original"], source,
                prepared[d["completion_index"]][d["group_index"]]) for d in declarations]
            archive_final = bridge.finish_archive(handle)
            self.assertTrue(archive_final["all_original_indexed_batches_join_validated"])
            self.assertFalse(archive_final["all_original_source_intrinsic_groups_validated"])
            plan = storage.plan_saved_run(groups, original_denominators=initial["original_denominators"],
                protected_sha256=fixture.registered, protected_roots=fixture.roots,
                source_archive_roots=(str(fixture.fixture.output),), compressed=True)
            self.assertEqual(plan.record()["reasons"], [])
            destination = fixture.fixture.root / "first-source-storage"
            run = storage.begin_storage(plan, destination)
            for i in range(len(groups)):
                storage.write_prepared_group(run, i)
            final = storage.finish(run)
        self.assertTrue(final["submitted_group_set_complete"])
        self.assertEqual(final["planned_shared_sources"], 1)
        self.assertEqual(final["original_denominators"]["planned_completion_requests"], 4)
        self.assertEqual(len({json.dumps(g.original["completion_request_ref"], sort_keys=True) for g in groups}), 2)
        self.assertLess(final["planned_submitted_entries"], initial["planned_selector_occurrences"])
        self.assertEqual(final["summary"]["persisted_pairs"], sum(g.original["planned_pairs"] for g in groups))
        self.assertFalse(final["flags"]["physical_original_request_admission"])
        self.assertFalse(final["flags"]["full_contrast_evaluated"])
        self.assertEqual(len(list(destination.glob("source-*-catalog.json.gz"))), 1)
        self.assertEqual(archive_final["read_ledger"]["decoded_attempt_bytes"], sum(r.decoded_bytes for r in fixture.reads))


if __name__ == "__main__":
    unittest.main()
