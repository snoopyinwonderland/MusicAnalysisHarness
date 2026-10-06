"""Small genuine XML -> saved bytes -> one reader -> one shared source.

The fixture factory creates synthetic source/native/role bodies before tests.
The saved-only path must not rerun those producers. This is not historical
archive admission, corpus execution, storage integration or musical accuracy.
"""
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_read_budget as budget
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import native_progression_contrast as legacy
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_interval_lattice as native
import test_native_progression_contrast as fixture_module


def request_ref(position):
    return kernels._ref(kernels._seal({"fixture_original_position": position}, "ssreadrequest_"))


class SharedSourceReadIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(fixture_module.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = fixture_module.SavedProgressionContrastTests()
        cls.inputs = cls.fixture.inputs("rational")

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="musicanote-shared-read-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.archive = self.root / "source"
        self.archive.mkdir()
        scope, lattice, entries, bundles = self.inputs
        payloads = {"source": {"scope": scope, "lattice": lattice, "bundles": bundles},
            "entries": {"entries": entries}}
        self.paths, self.lengths, self.hashes = {}, {}, {}
        for name, payload in payloads.items():
            decoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode("utf-8")
            encoded = gzip.compress(decoded, mtime=0)
            path = (self.archive / (name + ".json.gz")).resolve()
            path.write_bytes(encoded)
            self.paths[name] = path
            self.lengths[name] = (len(encoded), len(decoded))
            self.hashes[str(path)] = hashlib.sha256(encoded).hexdigest()
        self.denominators = {"fixture_only": True, "original_completion_requests": 2,
            "original_entry_occurrences": 2 * len(entries), "original_planned_pairs": 2}

    def reads(self):
        result = []
        for identity, name, phase in (("source-once", "source", "metadata"),
                ("request-0-entries", "entries", "body"),
                ("request-1-entries", "entries", "body")):
            path = self.paths[name]
            physical, decoded = self.lengths[name]
            result.append(budget.ReadInput(identity, str(path), self.hashes[str(path)],
                physical, decoded, "gzip-json", phase))
        return result

    def plan(self, *, reads=None, limits=None):
        return budget.plan_read_run(self.reads() if reads is None else reads,
            original_denominators=self.denominators, registered_sha256=self.hashes,
            inventory_roots=(budget.InventoryRoot(str(self.archive), self.hashes),),
            output_directory=str((self.root / "future-output").resolve()), limits=limits)

    def test_repeated_body_reads_keep_two_requests_one_source_and_exact_old_pairs(self):
        plan = self.plan()
        self.assertEqual(plan.record()["reasons"], [])
        source_bytes = self.lengths["source"][1]
        entry_bytes = self.lengths["entries"][1]
        self.assertEqual(plan.record()["planned_decoded_bytes"], source_bytes + 2 * entry_bytes)
        reader = budget.begin_reads(plan)
        forbidden = AssertionError("saved-only read/contrast cannot rerun producers")
        with patch.object(native, "prepare_lattice", side_effect=forbidden), \
                patch.object(roles, "explain_prepared", side_effect=forbidden):
            source_record = budget.read_record(reader, "source-once")
            source = shared.prepare_saved_source(source_record["scope"], source_record["lattice"],
                bundles=source_record["bundles"])
            source_ref = source.source_ref
            groups = []
            for position in (0, 1):
                # Separate metadata/body consumers share this SAME reader.
                saved = reader.read(self.paths["entries"])
                group = shared.prepare_saved_group(source, saved["entries"],
                    completion_request_ref=request_ref(position), selector_indices=[3, 18], block_size=1)
                self.assertEqual(group.source_ref, source_ref)
                self.assertFalse(isinstance(group, shared.codec.PreparedGroup))
                catalog = group.export_catalog()
                self.assertTrue({"lattice", "source_scope", "bundles", "source_sounds"}.isdisjoint(catalog))
                self.assertEqual(catalog["group"]["original_selector_indices"], [3, 18])
                sounds = {s["sound_ref"]: s for s in source_record["scope"]["sound_facts"]}
                block = shared.compare_block(group, next(group.iter_blocks()))
                self.assertEqual(block["computed_pairs"], 1)
                pair = block["pairs"][0]
                self.assertEqual(shared.materialize_pair(group, pair),
                    legacy._pair(catalog["facets"][0], catalog["facets"][1], sounds))
                self.assertEqual(pair["original_selector_indices"], [3, 18])
                self.assertIsNone(pair["musical_outcome"])
                self.assertTrue(all(flag is False for flag in block["flags"].values()))
                groups.append(group)
            self.assertNotEqual(groups[0].group_ref, groups[1].group_ref)
            self.assertEqual(groups[0].export_catalog()["group"]["bundle_ref"],
                groups[1].export_catalog()["group"]["bundle_ref"])
            final = budget.finish_reads(reader)
        self.assertTrue(final["submitted_read_set_complete"])
        self.assertEqual(final["completed_read_occurrences"], 3)
        self.assertEqual(final["decoded_attempt_bytes"], source_bytes + 2 * entry_bytes)
        self.assertEqual(final["original_denominators"], self.denominators)
        self.assertTrue(all(flag is False for flag in final["flags"].values()))
        self.assertFalse(final["flags"]["all_saved_bodies_validated"])
        with self.assertRaisesRegex(ValueError, "no_restart"):
            budget.begin_reads(plan)
        self.assertFalse((self.root / "future-output").exists())
        for name, sha in self.hashes.items():
            self.assertEqual(hashlib.sha256(Path(name).read_bytes()).hexdigest(), sha)

    def test_whole_cumulative_hold_before_read_or_source_prepare_preserves_denominators(self):
        only_one_request_cost = self.lengths["source"][1] + self.lengths["entries"][1]
        with patch.object(budget, "read_record", side_effect=AssertionError("no read prefix")), \
                patch.object(shared, "prepare_saved_source", side_effect=AssertionError("no source prefix")):
            plan = self.plan(limits=budget.ReadLimits(max_total_decoded_bytes=only_one_request_cost))
            record = plan.record()
            self.assertIn("whole_cumulative_decoded_limit_no_prefix", record["reasons"])
            self.assertEqual(record["original_denominators"], self.denominators)
            self.assertEqual(record["planned_read_occurrences"], 3)
            self.assertEqual(record["planned_unique_read_files"], 2)
            self.assertGreater(record["planned_decoded_bytes"], only_one_request_cost)
            record["original_denominators"]["original_entry_occurrences"] = 0
            with self.assertRaises(budget.WholeReadHold) as caught:
                budget.begin_reads(plan)
            self.assertEqual(caught.exception.plan["original_denominators"], self.denominators)
        self.assertFalse((self.root / "future-output").exists())

    def test_underdeclared_body_has_nonrefundable_failure_not_completed_prefix(self):
        declared = self.reads()
        declared[1] = replace(declared[1], decoded_bytes=declared[1].decoded_bytes - 1)
        declared[2] = replace(declared[2], decoded_bytes=declared[1].decoded_bytes)
        reader = budget.begin_reads(self.plan(reads=declared))
        budget.read_record(reader, "source-once")
        with self.assertRaises(budget.ReadFailure):
            budget.read_record(reader, "request-0-entries")
        final = budget.finish_reads(reader)
        self.assertFalse(final["submitted_read_set_complete"])
        self.assertEqual(final["completed_read_occurrences"], 1)
        self.assertEqual(final["failed_read_occurrences"], 1)
        self.assertEqual(final["never_attempted_read_occurrences"], 1)
        self.assertEqual(final["decoded_bytes_returned_lower_bound"],
            self.lengths["source"][1] + self.lengths["entries"][1])
        self.assertEqual(final["original_denominators"], self.denominators)
        with self.assertRaisesRegex(ValueError, "failed_cumulative_reader"):
            reader.read(self.paths["entries"])


if __name__ == "__main__":
    unittest.main()
