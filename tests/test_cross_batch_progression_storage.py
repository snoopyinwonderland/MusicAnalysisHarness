"""Small saved-only storage controls; no actual corpus or production writes.

Two-entry and null/known-zero cases use genuine XML/native/role fixtures. The
64/65 boundary uses explicitly mocked intrinsic admission over genuine facet
templates, not 65 genuine musical hypotheses or corpus-validation evidence.
"""
from copy import deepcopy
from dataclasses import asdict, replace
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import cross_batch_progression_storage as storage
from musicanote_harness import cross_batch_progression_contrast as core
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness.musical_pattern_observation import digest, q
import test_native_progression_contrast as fixture_module
from test_cross_batch_progression_contrast import request_ref
from test_factor_musical_view import reseal


def original(prepared, *, upstream_grid=False):
    catalog = prepared.export_catalog()
    group, plan = catalog["group"], prepared.preflight_plan
    n, size = plan.entry_count, plan.block_size
    grid = (n + size - 1) // size
    return {"source_identity_sha256": digest(catalog["source_scope"]),
        "scope_ref": deepcopy(group["scope_ref"]), "lattice_ref": deepcopy(group["lattice_ref"]),
        "completion_request_ref": deepcopy(group["completion_request_ref"]),
        "key_ref": deepcopy(group["key_ref"] or kernels._ref(catalog["lattice"]["keys"][0])),
        "bundle_ref": deepcopy(group["bundle_ref"] or kernels._ref(next(iter(catalog["bundles"].values())))),
        "selector_indices": deepcopy(group["original_selector_indices"]),
        "planned_entries": n, "planned_pairs": n * (n - 1) // 2,
        "planned_block_tasks": grid * (grid + 1) // 2 if upstream_grid else plan.planned_blocks,
        "block_size": size}


class StoragePureControls(unittest.TestCase):
    def test_closed_integer_limits_and_flags(self):
        for name in asdict(storage.StorageLimits()):
            for value in (True, -1, 0.5, "2", None):
                with self.assertRaises(ValueError):
                    storage.StorageLimits(**{name: value})
        self.assertTrue(all(v is False for v in storage._flags().values()))
        self.assertEqual(storage.StorageLimits().max_output_bytes, 2147483648)

    def test_even_empty_run_requires_manifest_reservation_before_writes(self):
        with patch.object(core, "compare_block", side_effect=AssertionError("no calculation")):
            for limits in (storage.StorageLimits(max_manifest_bytes=0),
                    storage.StorageLimits(max_output_bytes=0), storage.StorageLimits(max_plan_bytes=0)):
                plan = storage.plan_saved_run([], original_denominators={"original_pairs": 1652640}, limits=limits)
                self.assertTrue(plan.record()["reasons"])
                self.assertEqual(plan.record()["original_denominators"]["original_pairs"], 1652640)
                with tempfile.TemporaryDirectory() as root:
                    destination = Path(root) / "must-not-exist"
                    with self.assertRaises(storage.WholeRunHold):
                        storage.begin_storage(plan, destination)
                    self.assertFalse(destination.exists())

    def test_exports_and_constructor_cannot_become_owned_authority(self):
        plan = storage.plan_saved_run([], original_denominators={"not_submitted": 8050})
        copied = plan.record()
        copied["original_denominators"]["not_submitted"] = 0
        self.assertEqual(plan.record()["original_denominators"]["not_submitted"], 8050)
        for constructor in (storage.StoragePlan, storage.StorageRun):
            with self.assertRaises(ValueError):
                constructor()
        for fake in ({"finished": True}, object(), object.__new__(storage.StorageRun)):
            with self.assertRaises(ValueError):
                storage.finish(fake)
        with self.assertRaises(AttributeError):
            plan.complete = True


class SavedStorageControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(fixture_module.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = fixture_module.SavedProgressionContrastTests()
        cls.prepared_cache = {}

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sequence = 0

    def prepare(self, n=2, *, request=0, control=False, limits=None, block_size=64):
        scope, lattice, entries, bundles = self.fixture.inputs(control=control)
        return core.prepare_saved_group(scope, lattice, entries[:n], bundles=bundles,
            completion_request_ref=request_ref(request), selector_indices=list(range(3, 3 + n)),
            limits=limits, block_size=block_size)

    def synthetic_prepared(self, n):
        if n not in self.prepared_cache:
            seed = self.prepare()
            catalog = seed.export_catalog()
            entries = []
            for i in range(n):
                entry = deepcopy(catalog["entries"][i % 2])
                entry["native_path"]["logical_tuple"]["synthetic_storage_fixture_occurrence"] = i
                entry["native_path"] = reseal(entry["native_path"], "fmilpath_")
                entries.append(entry)
            # Explicit mock intrinsic admission: these are storage geometry
            # controls, not valid new native musical authorities.
            with (patch.object(core.legacy, "_validate_entry", return_value=None),
                  patch.object(core.legacy, "_facet", return_value=catalog["facets"][0])):
                prepared = core.prepare_saved_group(catalog["source_scope"], catalog["lattice"], entries,
                    bundles=catalog["bundles"], completion_request_ref=request_ref(n),
                    selector_indices=list(range(100, 100 + n)))
            self.prepared_cache[n] = prepared
        return self.prepared_cache[n]

    def begin(self, prepared=None, *, group_input=None, **options):
        if group_input is None:
            group_input = storage.GroupInput(original(prepared), prepared)
        self.sequence += 1
        plan = storage.plan_saved_run([group_input], original_denominators={"whole_original_entries": 8050,
            "whole_original_pairs": 1652640, "original_requests": 4, "source_scope": "declared-not-authenticated"}, **options)
        run = storage.begin_storage(plan, self.root / f"output-{self.sequence}")
        return plan, run

    def assert_complements(self, report):
        counts = report["summary"]
        self.assertEqual(counts["planned_pairs"], counts["computed_pairs"] + counts["held_pairs"] + counts["uncomputed_pairs"])
        self.assertEqual(counts["planned_pairs"], counts["persisted_pairs"] + counts["unpersisted_pairs"])
        self.assertEqual(counts["computed_unpersisted_pairs"], counts["computed_pairs"] - counts["persisted_pairs"])
        self.assertEqual(report["original_denominators"]["whole_original_entries"], 8050)
        self.assertTrue(all(v is False for v in report["flags"].values()))
        self.assertIsNone(report["selected"])

    def test_genuine_compressed_catalog_and_block_exact_round_trip(self):
        prepared = self.prepare()
        plan, run = self.begin(prepared, compressed=True)
        with (patch.object(native, "prepare_lattice", side_effect=AssertionError("no producer")),
              patch.object(native, "compare_prepared", side_effect=AssertionError("no producer")),
              patch.object(roles, "explain_prepared", side_effect=AssertionError("no producer"))):
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
        self.assertTrue(report["submitted_group_set_complete"])
        self.assertTrue(report["storage_integrity_passed"])
        self.assertEqual(report["summary"]["persisted_pairs"], 1)
        self.assert_complements(report)
        for attempt in report["artifact_attempts"]:
            raw = Path(attempt["artifact"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), attempt["physical_sha256"])
            self.assertEqual(len(raw), attempt["physical_bytes"])
            if attempt["kind"] == "catalog":
                self.assertEqual(json.loads(gzip.decompress(raw)), prepared.export_catalog())
            elif attempt["kind"] == "block":
                expected = core.compare_block(prepared, next(prepared.iter_blocks()))
                self.assertEqual(json.loads(gzip.decompress(raw)), expected)
            elif attempt["kind"] == "final_manifest":
                # A file cannot authenticate its own successful write.
                self.assertFalse(json.loads(raw)["submitted_group_set_complete"])
        self.assertLessEqual(report["attempted_output_bytes"], plan.record()["output_reserved_bytes_before_pair_calculation"])

    def test_zero_and_single_keep_original_key_request_and_grid_task_counts(self):
        for n in (0, 1):
            prepared = self.prepare(n)
            declared = original(prepared, upstream_grid=True)
            _, run = self.begin(group_input=storage.GroupInput(declared, prepared))
            with patch.object(core, "compare_block", side_effect=AssertionError("zero pairs")):
                storage.write_prepared_group(run, 0)
                report = storage.finish(run)
            self.assertTrue(report["submitted_group_set_complete"])
            self.assertEqual(report["summary"]["planned_pairs"], 0)
            self.assertEqual(report["planned_declared_upstream_tasks"], n)
            self.assertEqual(report["planned_submitted_nonempty_tasks"], 0)
            self.assertEqual(report["groups"][0]["original"], declared)
            self.assert_complements(report)

    def test_mock_64_65_tail_exact_saved_task_coverage(self):
        for n in (64, 65):
            prepared = self.synthetic_prepared(n)
            declared = original(prepared, upstream_grid=True)
            _, run = self.begin(group_input=storage.GroupInput(declared, prepared))
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
            self.assertTrue(report["submitted_group_set_complete"], report["errors"])
            self.assertEqual(report["summary"]["persisted_pairs"], n * (n - 1) // 2)
            self.assertEqual(report["planned_submitted_nonempty_tasks"], 1 if n == 64 else 2)
            self.assertEqual(report["groups"][0]["declared_zero_pair_tasks"], n == 65)
            self.assertEqual(report["groups"][0]["unpersisted_task_ranges"], [])
            self.assert_complements(report)

    def test_duplicate_reordered_foreign_and_modified_tasks_rejected_before_compute(self):
        prepared = self.synthetic_prepared(65)
        _, run = self.begin(prepared)
        tasks = list(prepared.iter_blocks())
        for bad in (tasks[1], replace(tasks[0], group_sha256="0" * 64),
                replace(tasks[0], expected_pairs=True), replace(tasks[0], row_start=1)):
            with patch.object(core, "compare_block", side_effect=AssertionError("no invalid calculation")):
                with self.assertRaisesRegex(ValueError, "exact_next_task"):
                    storage.write_block(run, 0, bad)
        storage.write_block(run, 0, tasks[0])
        with patch.object(core, "compare_block", side_effect=AssertionError("no duplicate calculation")):
            with self.assertRaises(ValueError):
                storage.write_block(run, 0, tasks[0])
        report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertTrue(report["storage_integrity_passed"])
        self.assertEqual(report["summary"]["uncomputed_pairs"], 64)
        self.assertEqual(report["groups"][0]["uncomputed_task_ranges"], [asdict(tasks[1])])
        self.assert_complements(report)

    def test_whole_known_output_cap_and_manifest_cap_before_any_pair_or_write(self):
        prepared = self.prepare()
        for limits in (storage.StorageLimits(max_output_bytes=1),
                storage.StorageLimits(max_manifest_bytes=1), storage.StorageLimits(max_block_encoded_bytes=0)):
            with patch.object(core, "compare_block", side_effect=AssertionError("no favorable prefix")):
                plan = storage.plan_saved_run([storage.GroupInput(original(prepared), prepared)],
                    original_denominators={"entries": 8050}, limits=limits)
                self.assertTrue(plan.record()["reasons"])
                self.assertEqual(plan.record()["planned_submitted_pairs"], 1)
                with self.assertRaises(storage.WholeRunHold):
                    storage.begin_storage(plan, self.root / "never-created")
                self.assertFalse((self.root / "never-created").exists())

    def test_boolean_single_pair_task_rejected_before_core_call(self):
        prepared = self.prepare()
        _, run = self.begin(prepared)
        task = next(prepared.iter_blocks())
        with patch.object(core, "compare_block", side_effect=AssertionError("no boolean task calculation")):
            for altered in (replace(task, expected_pairs=True), replace(task, row_start=False)):
                with self.assertRaises(ValueError):
                    storage.write_block(run, 0, altered)
        self.assertFalse(storage.ledger(run)["groups"][0]["task_ledger"][0]["calculation_attempted"])

    def test_task_count_gate_does_not_export_or_enumerate_catalog(self):
        prepared = self.synthetic_prepared(65)
        declared = original(prepared)
        with (patch.object(core.PreparedGroup, "export_catalog", side_effect=AssertionError("no catalog")),
              patch.object(core.PreparedGroup, "iter_blocks", side_effect=AssertionError("no task expansion"))):
            plan = storage.plan_saved_run([storage.GroupInput(declared, prepared)], original_denominators={},
                limits=storage.StorageLimits(max_tasks=1))
        self.assertEqual(plan.record()["planned_submitted_nonempty_tasks"], 2)
        self.assertIsNone(plan.record()["groups"][0]["catalog_encoded_bound"])
        self.assertIsNone(plan.record()["groups"][0]["core_preflight"])

    def test_unknown_held_group_not_empty_and_not_compute_authority(self):
        prepared = self.prepare()
        declared = original(prepared)
        _, run = self.begin(group_input=storage.GroupInput(declared, hold_reasons=("missing_original_body",)))
        with patch.object(core, "compare_block", side_effect=AssertionError("no held computation")):
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertTrue(report["storage_integrity_passed"])
        self.assertEqual(report["summary"]["held_pairs"], 1)
        self.assertIsNone(report["groups"][0]["catalog_encoded_bound"])
        self.assert_complements(report)

    def test_runtime_encoded_overflow_keeps_computed_unpersisted_whole_block(self):
        prepared = self.prepare()
        _, run = self.begin(prepared, task_encoded_caps={(0, 0): 512})
        storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertEqual(report["summary"]["computed_pairs"], 1)
        self.assertEqual(report["summary"]["persisted_pairs"], 0)
        self.assertEqual(report["summary"]["computed_unpersisted_pairs"], 1)
        self.assertEqual(report["summary"]["storage_held_pairs"], 1)
        self.assertTrue(report["storage_integrity_passed"])
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertTrue(report["groups"][0]["task_ledger"][0]["encoded_bytes"] > 512)
        self.assertEqual([a["kind"] for a in report["artifact_attempts"]], ["run_plan", "catalog", "final_manifest"])
        self.assert_complements(report)

    def test_core_whole_block_hold_separate_from_storage_failure(self):
        prepared = self.prepare(limits=replace(core.Limits(), max_pair_record_bytes=512))
        _, run = self.begin(prepared)
        storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertEqual(report["summary"]["computed_pairs"], 0)
        self.assertEqual(report["summary"]["held_pairs"], 1)
        self.assertEqual(report["summary"]["uncomputed_pairs"], 0)
        self.assertTrue(report["storage_integrity_passed"])
        self.assertFalse(report["submitted_group_set_complete"])
        self.assert_complements(report)

    def test_partial_block_write_preserves_physical_fragment_and_attempt(self):
        prepared = self.prepare()
        _, run = self.begin(prepared)
        real = storage._write_payload
        def fail(path, raw):
            if "-block-" in path.name:
                with path.open("xb") as stream:
                    stream.write(raw[:37])
                raise OSError("synthetic partial block write")
            return real(path, raw)
        with patch.object(storage, "_write_payload", side_effect=fail):
            storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        attempt = next(a for a in report["artifact_attempts"] if a["kind"] == "block")
        self.assertEqual(attempt["physical_bytes"], 37)
        self.assertEqual(attempt["physical_sha256"], hashlib.sha256(Path(attempt["artifact"]).read_bytes()).hexdigest())
        self.assertGreater(attempt["attempted_bytes"], 37)
        self.assertFalse(attempt["persisted"])
        self.assertEqual(report["summary"]["computed_unpersisted_pairs"], 1)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertFalse(report["storage_integrity_passed"])
        self.assert_complements(report)

    def test_partial_catalog_and_run_plan_writes_never_start_pairs(self):
        prepared = self.prepare()
        for failed_name in ("run-plan.json", "catalog"):
            self.sequence += 1
            plan = storage.plan_saved_run([storage.GroupInput(original(prepared), prepared)], original_denominators={})
            real = storage._write_payload
            def fail(path, raw):
                if failed_name in path.name:
                    with path.open("xb") as stream:
                        stream.write(raw[:19])
                    raise OSError("synthetic early write failure")
                return real(path, raw)
            with (patch.object(storage, "_write_payload", side_effect=fail),
                  patch.object(core, "compare_block", side_effect=AssertionError("no calculation"))):
                run = storage.begin_storage(plan, self.root / f"early-{self.sequence}")
                if failed_name == "catalog":
                    storage.write_prepared_group(run, 0)
                report = storage.finish(run)
            self.assertEqual(report["summary"]["computed_pairs"], 0)
            self.assertEqual(report["summary"]["uncomputed_pairs"], 1)
            self.assertFalse(report["submitted_group_set_complete"])
            self.assertEqual(next(a for a in report["artifact_attempts"] if a["error"])["physical_bytes"], 19)

    def test_final_manifest_failure_after_full_bytes_does_not_claim_complete(self):
        prepared = self.prepare()
        _, run = self.begin(prepared)
        storage.write_prepared_group(run, 0)
        real = storage._write_payload
        def fail(path, raw):
            real(path, raw)
            if path.name == "report.json":
                raise OSError("post-write final manifest failure")
        with patch.object(storage, "_write_payload", side_effect=fail):
            report = storage.finish(run)
        self.assertTrue(report["all_planned_pairs_computed"])
        self.assertEqual(report["summary"]["persisted_pairs"], 1)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertFalse(report["terminal_persisted"])
        attempt = next(a for a in report["artifact_attempts"] if a["kind"] == "final_manifest")
        self.assertFalse(json.loads(Path(attempt["artifact"]).read_bytes())["submitted_group_set_complete"])
        self.assert_complements(report)

    def test_interrupt_during_core_has_unknown_attempt_not_known_never_computed_zero(self):
        prepared = self.prepare()
        _, run = self.begin(prepared)
        with patch.object(core, "compare_block", side_effect=KeyboardInterrupt("small mock interrupt")):
            storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertEqual(report["summary"]["computed_pairs"], 0)
        self.assertEqual(report["summary"]["unconfirmed_computation_pairs"], 1)
        self.assertTrue(report["groups"][0]["task_ledger"][0]["calculation_attempted"])
        self.assertFalse(report["submitted_group_set_complete"])
        self.assert_complements(report)

    def test_resealed_missing_duplicate_reordered_foreign_and_promoted_packets_rejected(self):
        prepared = self.synthetic_prepared(64)
        task = next(prepared.iter_blocks())
        valid = core.compare_block(prepared, task)
        for change in ("missing", "duplicate", "reordered", "foreign", "numeric_flag", "selected"):
            block = deepcopy(valid)
            if change == "missing":
                block["pairs"].pop()
            elif change == "duplicate":
                block["pairs"][1] = deepcopy(block["pairs"][0])
            elif change == "reordered":
                block["pairs"].reverse()
            elif change == "foreign":
                block["catalog_ref"]["record_sha256"] = "0" * 64
            elif change == "numeric_flag":
                block["flags"][next(iter(block["flags"]))] = 0
            else:
                block["selected"] = "winner"
            block = reseal(block, core.BLOCK_PREFIX)
            _, run = self.begin(prepared)
            with patch.object(core, "compare_block", return_value=block):
                storage.write_block(run, 0, task)
            report = storage.finish(run)
            self.assertFalse(report["submitted_group_set_complete"], change)
            self.assertEqual(report["summary"]["persisted_pairs"], 0)
            self.assertFalse(report["storage_integrity_passed"])

    def test_original_declarations_cannot_reduce_or_replace_handle_membership(self):
        prepared = self.prepare()
        for name, value in (("selector_indices", [4, 5]), ("planned_entries", 1),
                ("planned_pairs", True), ("completion_request_ref", request_ref(999))):
            declared = original(prepared)
            declared[name] = value
            with self.assertRaises(ValueError):
                storage.plan_saved_run([storage.GroupInput(declared, prepared)], original_denominators={})
        for fake in (prepared.export_catalog(), object.__new__(core.PreparedGroup)):
            with self.assertRaises(ValueError):
                storage.plan_saved_run([storage.GroupInput(original(prepared), fake)], original_denominators={})
        with self.assertRaises(ValueError):
            storage.plan_saved_run([storage.GroupInput(original(prepared))], original_denominators={})

    def test_same_bundle_different_requests_are_separate_submitted_groups(self):
        first, second = self.prepare(request=1), self.prepare(request=2)
        plan = storage.plan_saved_run([storage.GroupInput(original(first), first),
            storage.GroupInput(original(second), second)], original_denominators={"all_requests": 4})
        run = storage.begin_storage(plan, self.root / "two-requests")
        storage.write_prepared_group(run, 0)
        storage.write_prepared_group(run, 1)
        report = storage.finish(run)
        self.assertTrue(report["submitted_group_set_complete"])
        self.assertEqual(report["summary"]["planned_pairs"], 2)
        self.assertNotEqual(report["groups"][0]["group_ref"], report["groups"][1]["group_ref"])
        with self.assertRaisesRegex(ValueError, "duplicate_declared"):
            storage.plan_saved_run([storage.GroupInput(original(first), first)] * 2, original_denominators={})
        altered_source = original(first)
        altered_source["source_identity_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "duplicate_declared"):
            storage.plan_saved_run([storage.GroupInput(original(first), first),
                storage.GroupInput(altered_source, first)], original_denominators={})

    def test_output_mutation_and_foreign_inventory_before_or_after_finish_invalidate(self):
        prepared = self.prepare()
        for when, mutation in (("before", "catalog"), ("before", "foreign"), ("after", "catalog")):
            _, run = self.begin(prepared)
            storage.write_prepared_group(run, 0)
            if when == "after":
                self.assertTrue(storage.finish(run)["submitted_group_set_complete"])
            report = storage.ledger(run)
            directory = Path(report["artifact_attempts"][0]["artifact"]).parent
            if mutation == "foreign":
                with (directory / "foreign.json").open("xb") as stream:
                    stream.write(b"{}")
            else:
                path = Path(next(a["artifact"] for a in report["artifact_attempts"] if a["kind"] == "catalog"))
                with path.open("ab") as stream:
                    stream.write(b"changed synthetic output")
            final = storage.finish(run)
            self.assertFalse(final["submitted_group_set_complete"])
            self.assertFalse(final["storage_integrity_passed"])
            self.assertTrue(final["changed_output_paths"])

    def test_input_SHA_guards_and_exclusive_directory_preserve_original(self):
        prepared = self.prepare()
        source = self.root / "protected-input.txt"
        with source.open("xb") as stream:
            stream.write("한국어 source".encode("utf-8"))
        sha = storage._file_sha(source)
        plan, run = self.begin(prepared, protected_sha256={str(source): sha})
        saved = Path(storage.ledger(run)["artifact_attempts"][0]["artifact"]).parent
        with self.assertRaises(FileExistsError):
            storage.begin_storage(plan, saved)
        with source.open("ab") as stream:
            stream.write(b"caller mutation")
        with patch.object(core, "compare_block", side_effect=AssertionError("guard before compute")):
            storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertIn(str(source), report["changed_protected_paths"])
        self.assertEqual(report["summary"]["computed_pairs"], 0)

    def test_gzip_catalog_encoding_interrupt_keeps_unknown_bytes_and_denominators(self):
        prepared = self.prepare()
        _, run = self.begin(prepared, compressed=True)
        with patch.object(storage.gzip, "compress", side_effect=MemoryError("small mock compression failure")):
            storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertTrue(report["groups"][0]["catalog_encoding_attempted"])
        self.assertIsNone(report["groups"][0]["catalog_encoded_bytes"])
        self.assertEqual(report["summary"]["uncomputed_pairs"], 1)
        self.assert_complements(report)

    def test_fragment_observation_failure_retains_unknown_physical_bytes(self):
        prepared = self.prepare()
        _, run = self.begin(prepared)
        real_write, real_sha = storage._write_payload, storage._file_sha
        def fail_write(path, raw):
            if "-block-" in path.name:
                with path.open("xb") as stream:
                    stream.write(raw[:29])
                raise OSError("partial mock output")
            return real_write(path, raw)
        def fail_observation(path):
            if "-block-" in Path(path).name:
                raise OSError("unreadable mock fragment")
            return real_sha(path)
        with (patch.object(storage, "_write_payload", side_effect=fail_write),
              patch.object(storage, "_file_sha", side_effect=fail_observation)):
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
        attempt = next(a for a in report["artifact_attempts"] if a["kind"] == "block")
        self.assertIsNone(attempt["physical_bytes"])
        self.assertIsNone(attempt["physical_sha256"])
        self.assertEqual(report["unknown_physical_output_attempts"], 1)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assert_complements(report)

    def test_conditional_null_and_computed_zero_survive_saved_JSON(self):
        source_fixture = self.fixture.fixture
        scope = source_fixture.case("grace")[0][1]
        lattice = source_fixture.record("grace")
        selector = source_fixture.selector("grace")
        variant = deepcopy(selector)
        origin = next(o for cat in lattice["catalog_inventory"] if cat["span"] == scope["analysis_span"]
            for o in cat["origins"] if o["record_id"] not in selector["origin_ids"])
        variant["origin_ids"] = [origin["record_id"]]
        session = source_fixture.session("grace")
        bundle = native.compile_bundle_prepared(session, [])
        comparison = native.compare_prepared(session, [selector, variant], bundle["record_id"])
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entries = [{"native_path": p, "role_path": r, "comparison_ref": kernels._ref(comparison),
            "explanation_ref": kernels._ref(explained)} for p, r in zip(comparison["paths"], explained["paths"])]
        unknown = core.prepare_saved_group(scope, lattice, entries, bundles={bundle["record_id"]: bundle}, completion_request_ref=request_ref())
        for prepared, expected in ((unknown, None), (self.prepare(control=True), q(0))):
            _, run = self.begin(prepared)
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
            path = Path(next(a["artifact"] for a in report["artifact_attempts"] if a["kind"] == "block"))
            pair = json.loads(path.read_bytes())["pairs"][0]
            self.assertEqual(pair["conditional_credit_delta_right_minus_left"], expected)
            self.assertEqual(set(pair["note_time_delta_right_minus_left"]), set(core.CATEGORIES))

    def test_encoded_UTF8_bytes_and_explicit_per_task_caps(self):
        prepared = self.prepare()
        denominator = {"설명": "원래 요청" * 50}
        plan = storage.plan_saved_run([storage.GroupInput(original(prepared), prepared)], original_denominators=denominator,
            task_encoded_caps={(0, 0): 4096})
        run = storage.begin_storage(plan, self.root / "UTF8")
        attempt = storage.ledger(run)["artifact_attempts"][0]
        raw = Path(attempt["artifact"]).read_bytes()
        self.assertEqual(attempt["attempted_bytes"], len(raw))
        self.assertGreater(len(raw), len(raw.decode("utf-8")))
        for caps in ({(0, 0): True}, {(False, 0): 4096}, {(0, 8): 4096}, {(0, 0): 67108865}):
            with self.assertRaises(ValueError):
                storage.plan_saved_run([storage.GroupInput(original(prepared), prepared)], original_denominators={}, task_encoded_caps=caps)


if __name__ == "__main__":
    unittest.main()
