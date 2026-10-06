"""Small real-XML saved bodies -> admission -> contrast -> storage.

Ancestor archive admission is mocked by the existing small packet fixture.
This is not physical admission of the real corpus and creates no corpus output.
No producer may run during the saved-only bridge tested here.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_progression_admission as admission
from musicanote_harness import cross_batch_progression_contrast as contrast
from musicanote_harness import cross_batch_progression_storage as storage
import test_cross_batch_progression_admission as admission_fixture


class SavedBodyStorageIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        admission_fixture.SavedBatchJoinControls.setUpClass()
        cls.addClassCleanup(admission_fixture.SavedBatchJoinControls.doClassCleanups)

    def setUp(self):
        self.fixture = admission_fixture.SavedBatchJoinControls()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.handle = self.fixture.handle()

    def groups(self):
        result = []
        for completion_index in (0, 1):
            source = admission.source_prepared(self.handle, 0, completion_index)
            entries = {}
            for packet in admission.iter_validated_completion_entries(self.handle, 0, completion_index):
                for row in packet["entries"]:
                    self.assertNotIn(row["selector_index"], entries)
                    entries[row["selector_index"]] = row["entry"]
            for group in source["groups"]:
                indices = group["selector_indices"]
                original = {
                    **deepcopy(group),
                    "source_identity_sha256": source["completion_request"]["source_identity_sha256"],
                    "scope_ref": contrast.kernels._ref(source["scope"]),
                    "lattice_ref": contrast.kernels._ref(source["lattice"]),
                    "bundle_ref": contrast.kernels._ref(source["bundle"]),
                    "block_size": admission.SETTINGS["block_size"],
                }
                prepared = contrast.prepare_saved_group(
                    source["scope"], source["lattice"], [entries[i] for i in indices],
                    bundles={source["bundle"]["record_id"]: source["bundle"]},
                    completion_request_ref=group["completion_request_ref"],
                    selector_indices=indices, block_size=original["block_size"],
                )
                result.append(storage.GroupInput(original, prepared))
        return result

    def read(self, path):
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                return json.load(stream)
        return json.loads(path.read_text(encoding="utf-8"))

    def test_all_saved_groups_keep_request_membership_and_exact_pair_explanations(self):
        forbidden = AssertionError("saved bridge cannot invoke native or role producers")
        with patch.object(admission.replay.engine, "prepare_replay", side_effect=forbidden), \
                patch.object(admission.replay.engine, "stream_prepared", side_effect=forbidden), \
                patch.object(admission.replay.engine.native, "prepare_lattice", side_effect=forbidden):
            groups = self.groups()
            admitted = admission.finish_admission(self.handle)
            self.assertTrue(admitted["all_indexed_batches_join_validated"])
            self.assertFalse(admitted["flags"]["all_saved_bodies_validated"])
            original = {"fixture_only": True, "completion_requests": 2,
                "entries": 2 * self.fixture.plan["planned_selectors"]}
            plan = storage.plan_saved_run(groups, original_denominators=original,
                protected_sha256=self.fixture.hashes, compressed=True)
            self.assertEqual(plan.record()["reasons"], [])
            self.assertEqual(plan.record()["planned_submitted_entries"], original["entries"])
            directory = self.fixture.fixture.output.parent / "saved-contrast-bridge"
            run = storage.begin_storage(plan, directory)
            for index in range(len(groups)):
                storage.write_prepared_group(run, index)
            final = storage.finish(run)
        self.assertTrue(final["submitted_group_set_complete"])
        self.assertTrue(final["storage_integrity_passed"])
        self.assertEqual(final["original_denominators"], original)
        self.assertEqual(final["summary"]["planned_pairs"], final["summary"]["persisted_pairs"])
        self.assertEqual(final["summary"]["computed_unpersisted_pairs"], 0)
        self.assertEqual(final["summary"]["uncomputed_pairs"], 0)
        self.assertTrue(all(flag is False for flag in final["flags"].values()))
        self.assertFalse(final["flags"]["physical_original_request_admission"])
        self.assertFalse(final["flags"]["full_contrast_evaluated"])
        requests = {json.dumps(g.original["completion_request_ref"], sort_keys=True) for g in groups}
        self.assertEqual(len(requests), 2)
        self.assertEqual(len({json.dumps(g.original["bundle_ref"], sort_keys=True) for g in groups}), 1)
        count = 0
        for index, group in enumerate(groups):
            catalog = group.prepared.export_catalog()
            sounds = {sound["sound_ref"]: sound for sound in catalog["source_sounds"]}
            stored = self.read(directory / f"group-{index:04d}-catalog.json.gz")
            self.assertEqual(stored, catalog)
            for task_index, task in enumerate(group.prepared.iter_blocks()):
                block = self.read(directory / f"group-{index:04d}-block-{task_index:06d}.json.gz")
                self.assertEqual(block["computed_pairs"], task.expected_pairs)
                self.assertFalse(block["whole_group_complete"])
                for pair in block["pairs"]:
                    i, j = pair["entry_indices"]
                    expected = contrast.legacy._pair(catalog["facets"][i], catalog["facets"][j], sounds)
                    self.assertEqual(contrast.materialize_pair(group.prepared, pair), expected)
                    self.assertEqual(pair["original_selector_indices"],
                        [group.original["selector_indices"][i], group.original["selector_indices"][j]])
                    count += 1
        self.assertEqual(count, final["summary"]["planned_pairs"])
        self.assertGreater(count, 0)
        # The manifest describes pre-terminal coverage; it cannot certify its
        # own successful write or grant a reload computation capability.
        manifest = self.read(directory / "report.json")
        self.assertFalse(manifest["submitted_group_set_complete"])
        self.assertFalse(manifest["terminal_persisted"])
        self.assertEqual(manifest["summary"], final["summary"])
        self.assertTrue(admission.finish_admission(self.handle)["all_indexed_batches_join_validated"])

    def test_whole_storage_hold_preserves_all_original_request_denominators(self):
        groups = self.groups()
        original = {"fixture_only": True, "completion_requests": 2,
            "entries": 2 * self.fixture.plan["planned_selectors"]}
        submitted_entries = sum(g.original["planned_entries"] for g in groups)
        submitted_pairs = sum(g.original["planned_pairs"] for g in groups)
        with patch.object(contrast, "compare_block", side_effect=AssertionError("no pair prefix")), \
                patch.object(storage, "_write_payload", side_effect=AssertionError("no output prefix")):
            plan = storage.plan_saved_run(groups, original_denominators=original,
                limits=storage.StorageLimits(max_output_bytes=0), protected_sha256=self.fixture.hashes)
            snapshot = plan.record()
            self.assertEqual(snapshot["planned_submitted_entries"], submitted_entries)
            self.assertEqual(snapshot["planned_submitted_pairs"], submitted_pairs)
            self.assertEqual(snapshot["original_denominators"], original)
            self.assertIn("whole_output_reservation_exceeds_limit_no_prefix", snapshot["reasons"])
            original["entries"] = 0
            snapshot["groups"].clear()
            self.assertEqual(plan.record()["original_denominators"]["entries"], submitted_entries)
            directory = self.fixture.fixture.output.parent / "held-contrast-bridge"
            with self.assertRaises(storage.WholeRunHold) as caught:
                storage.begin_storage(plan, directory)
            self.assertFalse(directory.exists())
            self.assertEqual(caught.exception.plan["planned_submitted_pairs"], submitted_pairs)
            self.assertEqual(len(caught.exception.plan["groups"]), len(groups))
        self.assertTrue(admission.finish_admission(self.handle)["all_indexed_batches_join_validated"])


if __name__ == "__main__":
    unittest.main()
