"""Saved admission controls and composed small genuine-XML batch joins.

The original corpus is never read by this suite. Whole historical source
admission is tested separately on the real archive as a read-only check.
The storage fixture mocks ancestor admission, not native/role packet bodies.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_progression_admission as admission
import test_source_progression_replay_trial as fixture_module
from test_factor_musical_view import reseal


class AdmissionPureControls(unittest.TestCase):
    def test_closed_integer_caps_and_block_range(self):
        for name in admission.SETTINGS:
            for value in (True, -1, 1.5, "2", None):
                with self.assertRaises(ValueError):
                    admission._settings({name: value})
        for value in (0, 65):
            with self.assertRaises(ValueError):
                admission._settings({"block_size": value})
        with self.assertRaises(ValueError):
            admission._settings({"unregistered": 3})
        self.assertEqual(admission._settings({})["max_total_decoded_bytes"], 1073741824)

    def test_saved_flags_require_false_not_numeric_zero(self):
        value = {"flags": admission.replay.engine._flags(), "selected": None,
            "source_authority": admission.replay.AUTHORITY, "full_contrast_status": admission.replay.DEFERRED}
        admission._unpromoted(value)
        for flag in value["flags"]:
            altered = deepcopy(value)
            altered["flags"][flag] = 0
            with self.assertRaises(ValueError):
                admission._unpromoted(altered)

    def test_historical_code_snapshot_not_todays_extra_modules(self):
        path = Path(__file__).resolve()
        parent = {"code": {"historical": "a" * 64}, "parent_inventories": [{"directory": "ancestor", "files": 7}]}
        report = {"artifact_hashes": {"p": "b" * 64}}
        root = Path("historical-parent")
        plan = {"code": {**parent["code"], str(path): "c" * 64},
            "parent_inventories": [{"directory": str(root), "files": 2}, *parent["parent_inventories"]]}
        with patch.object(admission.replay, "_new_code_paths", return_value={path}):
            admission._historical_creation(plan, parent, report, root)
            for altered in ({**plan, "code": {**plan["code"], "later-child": "d" * 64}},
                    {**plan, "code": {**plan["code"], "historical": "0" * 64}},
                    {**plan, "parent_inventories": plan["parent_inventories"][:-1]},
                    {**plan, "parent_inventories": list(reversed(plan["parent_inventories"]))}):
                with self.assertRaises(ValueError):
                    admission._historical_creation(altered, parent, report, root)

    def test_hold_preserves_original_plan_copy(self):
        plan = {"planned_entries": 8050, "planned_completion_requests": 4, "known_empty": False}
        held = admission.SourceAdmissionHold("technical budget", plan)
        plan["planned_entries"] = 0
        self.assertEqual(held.plan["planned_entries"], 8050)
        self.assertFalse(held.plan["known_empty"])

    def test_external_summary_cannot_forge_admission_handle(self):
        for value in ({"jobs": [{"all_entry_batches_consumed": True}]}, object(), None,
                admission._AdmittedArchive()):
            with self.assertRaises(ValueError):
                admission.finish_admission(value)

    def test_catalog_and_origin_caps_precede_intrinsic_validation(self):
        lattice = {"catalog_inventory": [{"origins": [object(), object()]}]}
        with patch.object(admission.replay.parent, "_inventory", side_effect=AssertionError("no prefix validation")):
            for caps in ({"max_catalogs": 0}, {"max_origins": 1}):
                with self.assertRaises(admission.SourceAdmissionHold) as caught:
                    admission._bounded_source_inventory(lattice, {}, {}, admission._settings(caps))
                self.assertEqual(caught.exception.plan, {"planned_catalogs": 1, "planned_origins": 2})


class SavedBatchJoinControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.ReplayPacketStorageTests.setUpClass()
        cls.addClassCleanup(fixture_module.ReplayPacketStorageTests.doClassCleanups)

    def setUp(self):
        self.fixture = fixture_module.ReplayPacketStorageTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.report, _, _ = self.fixture.run_mock()
        self.rows = self.fixture.rows()
        self.case = deepcopy(self.fixture.data["cases"][0])
        self.settings = admission._settings({})
        self.reader = admission.legacy_join.BoundedReader(self.settings)
        self.hashes = {**self.fixture.data["hashes"], **self.report["artifact_hashes"]}
        path = self.fixture.output / "report.json"
        self.hashes[str(path)] = admission.old._file_sha(path)
        self.binding = self.record(self.rows[0]["binding"], admission.replay.engine.BINDING_PREFIX)
        self.plan = self.record(self.rows[0]["plan"], admission.replay.engine.PLAN_PREFIX)

    def record(self, info, prefix):
        return admission._registered(info, prefix, self.reader, self.hashes)

    def job(self, index=0, row=None, **caps):
        return admission._completion(deepcopy(row or self.rows[0]["jobs"][index]), self.case,
            self.binding, self.plan, self.case["completion_controls"][index], 0, index,
            self.reader, self.hashes, {**self.settings, **caps}, self.fixture.limits)

    def handle(self):
        jobs = [self.job(0), self.job(1)]
        handle = admission._AdmittedArchive()
        admission._ADMISSIONS[handle] = {"jobs": jobs, "reader": self.reader, "hashes": self.hashes,
            "settings": self.settings, "inventories": [(self.fixture.output,
                {str(p.resolve()) for p in self.fixture.output.rglob("*") if p.is_file()})],
            "replay_limits": self.fixture.limits, "plan": {"denominators": {"fixture": True}},
            "summary": {"planned_entries": 2 * self.plan["planned_selectors"],
                "validated_entry_batches": 0, "validated_entry_occurrences": 0,
                "computed_pairs": 0, "all_saved_bodies_validated": False}}
        return handle

    def test_exact_completion_metadata_and_same_bundle_requests_separate(self):
        first, second = self.job(0), self.job(1)
        self.assertEqual(first["bundle"], second["bundle"])
        self.assertNotEqual(admission.sealed._ref(first["request"]), admission.sealed._ref(second["request"]))
        self.assertEqual(sum(g["planned_entries"] for g in first["groups"]), self.plan["planned_selectors"])
        self.assertEqual(sorted(i for g in first["groups"] for i in g["selector_indices"]),
            list(range(self.plan["planned_selectors"])))

    def test_incomplete_prefix_or_missing_batch_never_admitted(self):
        original = self.rows[0]["jobs"][0]
        changes = {"unpersisted_selector_ranges": [[0, 1]], "batches": original["batches"][:-1],
            "received_batch_packets": True, "runtime_activity_after_last_persisted_batch": None,
            "status": "incomplete_replay_storage_or_stream_failure"}
        for name, value in changes.items():
            row = deepcopy(original)
            row[name] = value
            with self.assertRaises(ValueError):
                self.job(row=row)

    def test_reordered_batch_and_foreign_info_rejected(self):
        row = deepcopy(self.rows[0]["jobs"][0])
        row["batches"][0]["selector_start"] += 1
        with self.assertRaises(ValueError):
            self.job(row=row)
        row = deepcopy(self.rows[0]["jobs"][0])
        row["batches"][0]["comparison"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.job(row=row)

    def test_resealed_reordered_role_array_rejected(self):
        handle = self.handle()
        job = admission._issued(handle)["jobs"][0]
        batch = job["row"]["batches"][0]
        explanation = self.record(batch["explanation"], admission.replay.engine.roles.PREFIX)
        self.assertGreater(len(explanation["paths"]), 1)
        explanation["paths"] = list(reversed(explanation["paths"]))
        explanation = reseal(explanation, admission.replay.engine.roles.PREFIX)
        # Only a temporary genuine-XML fixture is changed. Its seal and file
        # SHA remain valid; original array ordinals still must reject it.
        path = Path(batch["explanation"]["artifact"])
        raw = json.dumps(explanation, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
        if path.suffix == ".gz":
            import gzip
            raw = gzip.compress(raw)
        path.write_bytes(raw)
        sha = admission.old._file_sha(path)
        self.hashes[str(path)] = sha
        batch["explanation"].update(sha256=sha, record_ref=admission.sealed._ref(explanation))
        with self.assertRaisesRegex(ValueError, "ordinal|role|snapshot"):
            next(admission.iter_validated_completion_entries(handle, 0, 0))

    def test_whole_completion_cap_preserves_offending_count(self):
        with self.assertRaises(admission.SourceAdmissionHold) as caught:
            self.job(max_entries_per_completion=0)
        self.assertEqual(caught.exception.plan["planned_entries"], self.plan["planned_selectors"])

    def test_metadata_exports_are_copies_not_earned_ledger(self):
        handle = self.handle()
        exported = admission.metadata_prepared(handle)
        exported["summary"]["validated_entry_occurrences"] = self.plan["planned_selectors"]
        exported["groups"].clear()
        source = admission.source_prepared(handle, 0, 0)
        source["scope"]["analysis_span"] = {}
        final = admission.finish_admission(handle)
        self.assertFalse(final["all_indexed_batches_join_validated"])
        self.assertEqual(final["summary"]["validated_entry_occurrences"], 0)
        self.assertEqual(admission.source_prepared(handle, 0, 0)["scope"]["analysis_span"], self.case["scope"]["analysis_span"])

    def test_exhausted_all_batches_join_without_any_producer(self):
        handle = self.handle()
        forbidden = AssertionError("saved-only iterator may not run producers")
        with patch.object(admission.replay.engine, "prepare_replay", side_effect=forbidden), \
                patch.object(admission.replay.engine, "stream_prepared", side_effect=forbidden), \
                patch.object(admission.replay.engine.native, "prepare_lattice", side_effect=forbidden):
            for job_index in (0, 1):
                positions = []
                for batch in admission.iter_validated_completion_entries(handle, 0, job_index):
                    positions.extend(e["selector_index"] for e in batch["entries"])
                self.assertEqual(positions, list(range(self.plan["planned_selectors"])))
        final = admission.finish_admission(handle)
        self.assertTrue(final["all_indexed_batches_join_validated"])
        self.assertFalse(final["flags"]["all_saved_bodies_validated"])
        self.assertEqual(final["summary"]["validated_entry_occurrences"], 2 * self.plan["planned_selectors"])
        self.assertFalse(final["known_empty_request_set"])

    def test_early_close_even_after_last_yield_is_not_terminal_completion(self):
        handle = self.handle()
        stream = admission.iter_validated_completion_entries(handle, 0, 0)
        for _ in range(self.plan["planned_batches"]):
            next(stream)
        stream.close()
        self.assertFalse(admission.finish_admission(handle)["all_indexed_batches_join_validated"])
        with self.assertRaises(ValueError):
            next(admission.iter_validated_completion_entries(handle, 0, 0))

    def test_changed_file_after_metadata_admission_rejected(self):
        handle = self.handle()
        info = self.rows[0]["jobs"][0]["batches"][0]["comparison"]
        path = Path(info["artifact"])
        path.write_bytes(path.read_bytes() + b"changed fixture")
        with self.assertRaises(ValueError):
            next(admission.iter_validated_completion_entries(handle, 0, 0))
        with self.assertRaises(ValueError):
            admission.finish_admission(handle)

    def test_reader_budget_is_not_a_known_empty_prefix(self):
        handle = self.handle()
        self.reader.settings = {**self.settings, "max_total_decoded_bytes": self.reader.decoded_bytes}
        with self.assertRaisesRegex(ValueError, "decoded_bytes_no_partial_JSON"):
            next(admission.iter_validated_completion_entries(handle, 0, 0))
        result = admission.finish_admission(handle)
        self.assertFalse(result["all_indexed_batches_join_validated"])
        self.assertFalse(result["known_empty_request_set"])


if __name__ == "__main__":
    unittest.main()
