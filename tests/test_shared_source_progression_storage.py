"""Small genuine XML and explicitly mock geometry/IO source-once controls."""
from copy import deepcopy
from dataclasses import asdict, replace
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import shared_source_progression_storage as storage
from musicanote_harness import shared_source_progression_contrast as core
from musicanote_harness import cross_batch_progression_storage as frozen_storage
from musicanote_harness import cross_batch_read_budget as reads
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness.musical_pattern_observation import digest, q
import test_native_progression_contrast as fixture_module
from test_cross_batch_progression_contrast import request_ref
from test_factor_musical_view import reseal


def original(prepared, *, upstream_grid=False):
    group, plan = prepared.export_catalog()["group"], prepared.preflight_plan
    n, size = plan.entry_count, plan.block_size
    grid = (n + size - 1) // size
    return {"source_identity_sha256": digest(prepared.source_ref),
        **{name: deepcopy(group[name]) for name in
            ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref")},
        "selector_indices": deepcopy(group["original_selector_indices"]),
        "planned_entries": n, "planned_pairs": n * (n - 1) // 2,
        "planned_block_tasks": grid * (grid + 1) // 2 if upstream_grid else plan.planned_blocks,
        "block_size": size}


class StoragePureControls(unittest.TestCase):
    def test_closed_limits_and_authority(self):
        for name in asdict(storage.StorageLimits()):
            for value in (True, -1, 0.5, "2", None):
                with self.assertRaises(ValueError): storage.StorageLimits(**{name: value})
        limits = storage.StorageLimits()
        self.assertEqual((limits.max_output_bytes, limits.max_source_encoded_bytes), (2147483648, 268435456))
        self.assertTrue(all(v is False for v in storage._flags().values()))

    def test_empty_requires_manifest_reservation_before_writes(self):
        for limits in (storage.StorageLimits(max_manifest_bytes=0), storage.StorageLimits(max_output_bytes=0),
                storage.StorageLimits(max_plan_bytes=0)):
            plan = storage.plan_saved_run([], original_denominators={"original_pairs": 1652640}, limits=limits)
            self.assertTrue(plan.record()["reasons"])
            with tempfile.TemporaryDirectory() as root:
                output = Path(root) / "not-created"
                with self.assertRaises(storage.WholeRunHold): storage.begin_storage(plan, output)
                self.assertFalse(output.exists())

    def test_owned_plan_exports_and_forgery(self):
        plan = storage.plan_saved_run([], original_denominators={"original_entries": 8050})
        exported = plan.record(); exported["original_denominators"]["original_entries"] = 0
        self.assertEqual(plan.record()["original_denominators"]["original_entries"], 8050)
        with self.assertRaises(AttributeError): plan.complete = True
        for cls in (storage.StoragePlan, storage.StorageRun):
            with self.assertRaises(ValueError): cls()
        for fake in (exported, object.__new__(storage.StoragePlan)):
            with self.assertRaises(ValueError): storage.begin_storage(fake, "unused")
        for fake in ({}, object.__new__(storage.StorageRun)):
            with self.assertRaises(ValueError): storage.finish(fake)
        state = storage._PLANS[plan]
        storage._PLANS[plan] = replace(state, record=b"{}")
        try:
            with self.assertRaisesRegex(ValueError, "state_changed"): plan.record()
        finally: storage._PLANS[plan] = state


class SourceOnceStorageControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(fixture_module.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = fixture_module.SavedProgressionContrastTests()
        cls.sources = {}
        cls.synthetic = {}

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sequence = 0

    def prepare(self, n=2, *, request=0, control=False, limits=None, block_size=64, fresh_source=False):
        scope, lattice, entries, bundles = self.fixture.inputs(control=control)
        if control not in self.sources:
            self.sources[control] = core.prepare_saved_source(scope, lattice, bundles=bundles)
        source = core.prepare_saved_source(scope, lattice, bundles=bundles) if fresh_source else self.sources[control]
        prepared = core.prepare_saved_group(source, entries[:n], completion_request_ref=request_ref(request),
            selector_indices=list(range(3, 3 + n)), key_ref=entries[0]["native_path"]["key_ref"],
            bundle_ref=entries[0]["native_path"]["bundle_ref"], limits=limits, block_size=block_size)
        return source, prepared

    def mock_geometry(self, n):
        if n not in self.synthetic:
            source, seed = self.prepare()
            catalog = seed.export_catalog()
            entries = []
            for i in range(n):
                entry = deepcopy(catalog["entries"][i % 2])
                entry["native_path"]["logical_tuple"]["synthetic_storage_occurrence"] = i
                entry["native_path"] = reseal(entry["native_path"], "fmilpath_")
                entries.append(entry)
            # Explicit mock intrinsic admission: only geometry/serialization
            # coverage, NOT n genuine new musical hypotheses.
            with (patch.object(core.legacy, "_validate_entry", return_value=None),
                    patch.object(core.legacy, "_facet", return_value=catalog["facets"][0])):
                prepared = core.prepare_saved_group(source, entries, completion_request_ref=request_ref(n),
                    selector_indices=list(range(100, 100 + n)))
            self.synthetic[n] = source, prepared
        return self.synthetic[n]

    def begin(self, source, prepared=None, *, item=None, **options):
        if item is None: item = storage.GroupInput(original(prepared), source, prepared)
        plan = storage.plan_saved_run([item], original_denominators={"whole_original_entries": 8050,
            "whole_original_pairs": 1652640, "original_requests": 4}, **options)
        self.sequence += 1
        return plan, storage.begin_storage(plan, self.root / f"out-{self.sequence}")

    def assert_complements(self, report):
        values = report["summary"]
        self.assertEqual(values["planned_pairs"], values["computed_pairs"] + values["held_pairs"] + values["uncomputed_pairs"])
        self.assertEqual(values["planned_pairs"], values["persisted_pairs"] + values["unpersisted_pairs"])
        self.assertEqual(values["computed_unpersisted_pairs"], values["computed_pairs"] - values["persisted_pairs"])
        self.assertTrue(all(v is False for v in report["flags"].values()))
        self.assertEqual(report["original_denominators"]["whole_original_entries"], 8050)

    def test_genuine_source_local_block_compressed_exact_roundtrip(self):
        source, prepared = self.prepare()
        plan, run = self.begin(source, prepared, compressed=True)
        with (patch.object(native, "prepare_lattice", side_effect=AssertionError("no producer")),
                patch.object(native, "compare_prepared", side_effect=AssertionError("no producer")),
                patch.object(roles, "explain_prepared", side_effect=AssertionError("no producer")),
                patch.object(frozen_storage, "begin_storage", side_effect=AssertionError("no frozen adapter"))):
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
        self.assertTrue(report["submitted_group_set_complete"], report["errors"])
        self.assertEqual(report["persisted_shared_sources"], 1)
        self.assert_complements(report)
        for attempt in report["artifact_attempts"]:
            raw = Path(attempt["artifact"]).read_bytes()
            self.assertEqual(attempt["physical_sha256"], hashlib.sha256(raw).hexdigest())
            if attempt["kind"] == "source_catalog": self.assertEqual(json.loads(gzip.decompress(raw)), source.export_source())
            elif attempt["kind"] == "local_catalog": self.assertEqual(json.loads(gzip.decompress(raw)), prepared.export_catalog())
            elif attempt["kind"] == "block":
                block = json.loads(gzip.decompress(raw))
                self.assertEqual(block, core.compare_block(prepared, next(prepared.iter_blocks())))
                core.materialize_pair(prepared, block["pairs"][0])
            elif attempt["kind"] == "final_manifest": self.assertFalse(json.loads(raw)["submitted_group_set_complete"])
        self.assertLessEqual(report["attempted_output_bytes"], plan.record()["output_reserved_bytes_before_pair_calculation"])

    def test_same_owned_source_serialized_and_written_once_for_independentrequests(self):
        source, first = self.prepare(request=1)
        second_source, second = self.prepare(request=2)
        self.assertIs(source, second_source)
        real_export = core.PreparedSource.export_source
        with patch.object(core.PreparedSource, "export_source", autospec=True, side_effect=real_export) as export:
            plan = storage.plan_saved_run([storage.GroupInput(original(first), source, first),
                storage.GroupInput(original(second), source, second)], original_denominators={"whole_original_entries": 8050})
            self.assertEqual(export.call_count, 1)
        self.assertEqual(plan.record()["planned_shared_sources"], 1)
        run = storage.begin_storage(plan, self.root / "shared")
        for index in (0, 1): storage.write_prepared_group(run, index)
        report = storage.finish(run)
        self.assertTrue(report["submitted_group_set_complete"])
        self.assertEqual(sum(a["kind"] == "source_catalog" for a in report["artifact_attempts"]), 1)
        self.assertEqual(report["summary"]["planned_pairs"], 2)
        self.assertNotEqual(report["groups"][0]["group_ref"], report["groups"][1]["group_ref"])

    def test_equal_source_record_different_ownedhandles_not_dedupauthority(self):
        source, first = self.prepare(request=1)
        other, second = self.prepare(request=2, fresh_source=True)
        self.assertEqual(source.source_ref, other.source_ref)
        self.assertIsNot(source, other)
        with self.assertRaisesRegex(ValueError, "same_owned_handle"):
            storage.plan_saved_run([storage.GroupInput(original(first), source, first),
                storage.GroupInput(original(second), other, second)], original_denominators={})
        with self.assertRaisesRegex(ValueError, "same_owned_shared_source"):
            storage.plan_saved_run([storage.GroupInput(original(first), other, first)], original_denominators={})

    def test_same_original_source_identity_split_bundle_catalogs_rejected(self):
        source, first = self.prepare(request=1)
        scope, lattice, entries, bundles = self.fixture.inputs()
        _, _, _, other_bundles = self.fixture.inputs(control=True)
        other = core.prepare_saved_source(scope, lattice, bundles={**bundles, **other_bundles})
        second = core.prepare_saved_group(other, entries, completion_request_ref=request_ref(2), selector_indices=[3, 4])
        self.assertNotEqual(source.source_ref, other.source_ref)
        declared = original(second)
        declared["source_identity_sha256"] = original(first)["source_identity_sha256"]
        with self.assertRaisesRegex(ValueError, "same_declared_source_identity"):
            storage.plan_saved_run([storage.GroupInput(original(first), source, first),
                storage.GroupInput(declared, other, second)], original_denominators={})

    def test_zero_single_and_exact_tail_task_geometry(self):
        for n in (0, 1, 64, 65):
            source, prepared = self.prepare(n) if n < 2 else self.mock_geometry(n)
            item = storage.GroupInput(original(prepared, upstream_grid=True), source, prepared)
            _, run = self.begin(source, item=item)
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
            self.assertTrue(report["submitted_group_set_complete"], report["errors"])
            self.assertEqual(report["summary"]["persisted_pairs"], n * (n - 1) // 2)
            self.assertEqual(report["planned_submitted_nonempty_tasks"], 0 if n < 2 else 1 if n == 64 else 2)
            self.assertEqual(report["groups"][0]["declared_zero_pair_tasks"], n == 1 or n == 65)
            self.assertEqual(report["groups"][0]["original"], item.original)
            self.assert_complements(report)

    def test_whole_source_output_manifest_and_positive_taskcaps_before_write_or_pair(self):
        source, prepared = self.prepare()
        for limits in (storage.StorageLimits(max_output_bytes=1), storage.StorageLimits(max_manifest_bytes=1),
                storage.StorageLimits(max_source_encoded_bytes=1), storage.StorageLimits(max_block_encoded_bytes=0)):
            with patch.object(core, "compare_block", side_effect=AssertionError("no prefix")):
                plan = storage.plan_saved_run([storage.GroupInput(original(prepared), source, prepared)],
                    original_denominators={"entries": 8050}, limits=limits)
                self.assertTrue(plan.record()["reasons"])
                self.assertEqual(plan.record()["planned_submitted_pairs"], 1)
                with self.assertRaises(storage.WholeRunHold): storage.begin_storage(plan, self.root / "notcreated")
                self.assertFalse((self.root / "notcreated").exists())

    def test_count_gate_before_source_local_exports_or_taskexpansion(self):
        source, prepared = self.mock_geometry(65)
        declared = original(prepared)
        with (patch.object(core.PreparedSource, "export_source", side_effect=AssertionError("no source export")),
                patch.object(core.SharedPreparedGroup, "export_catalog", side_effect=AssertionError("no local export")),
                patch.object(core.SharedPreparedGroup, "iter_blocks", side_effect=AssertionError("no tasks"))):
            plan = storage.plan_saved_run([storage.GroupInput(declared, source, prepared)], original_denominators={},
                limits=storage.StorageLimits(max_tasks=1))
        self.assertEqual(plan.record()["planned_submitted_nonempty_tasks"], 2)
        self.assertIsNone(plan.record()["sources"][0]["source_encoded_bound"])
        self.assertIsNone(plan.record()["groups"][0]["catalog_encoded_bound"])

    def test_ordered_next_task_counter_missing_duplicate_foreign_boolean_rejected(self):
        source, prepared = self.mock_geometry(65)
        _, run = self.begin(source, prepared)
        tasks = list(prepared.iter_blocks())
        for task in (tasks[1], replace(tasks[0], source_sha256="0" * 64),
                replace(tasks[0], expected_pairs=True), replace(tasks[0], row_start=False)):
            with patch.object(core, "compare_block", side_effect=AssertionError("invalid pair")):
                with self.assertRaises(ValueError): storage.write_block(run, 0, task)
        storage.write_block(run, 0, tasks[0])
        with self.assertRaises(ValueError): storage.write_block(run, 0, tasks[0])
        report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertEqual(report["summary"]["uncomputed_pairs"], 64)
        self.assertEqual(report["groups"][0]["uncomputed_task_ranges"], [asdict(tasks[1])])
        self.assert_complements(report)

    def test_group_writer_does_not_recopy_whole_ledger_each_block(self):
        source, prepared = self.mock_geometry(65)
        _, run = self.begin(source, prepared)
        with patch.object(storage, "ledger", wraps=storage.ledger) as ledger:
            storage.write_prepared_group(run, 0)
            self.assertEqual(ledger.call_count, 1)
        self.assertTrue(storage.finish(run)["submitted_group_set_complete"])

    def test_held_group_is_not_knownempty(self):
        source, prepared = self.prepare()
        declared = original(prepared)
        item = storage.GroupInput(declared, source, hold_reasons=("missing_original_body",))
        _, run = self.begin(source, item=item)
        with patch.object(core, "compare_block", side_effect=AssertionError("held")):
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertEqual(report["summary"]["held_pairs"], 1)
        self.assertIsNone(report["groups"][0]["catalog_encoded_bound"])
        self.assert_complements(report)

    def test_computed_unpersisted_runtime_overflow_and_corehold_distinct(self):
        source, prepared = self.prepare()
        _, run = self.begin(source, prepared, task_encoded_caps={(0, 0): 512})
        storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertEqual((report["summary"]["computed_pairs"], report["summary"]["persisted_pairs"]), (1, 0))
        self.assertEqual(report["summary"]["storage_held_pairs"], 1)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assert_complements(report)
        source, held = self.prepare(limits=replace(core.GroupLimits(), max_pair_record_bytes=512))
        _, run = self.begin(source, held)
        storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertEqual((report["summary"]["computed_pairs"], report["summary"]["held_pairs"]), (0, 1))
        self.assertEqual(report["summary"]["uncomputed_pairs"], 0)
        self.assert_complements(report)

    def test_partial_source_local_block_and_plan_writes_keep_nonrefundable_fragments(self):
        source, prepared = self.prepare()
        real = storage._write_payload
        for target in ("run-plan", "source-", "group-0000-catalog", "-block-"):
            self.sequence += 1
            plan = storage.plan_saved_run([storage.GroupInput(original(prepared), source, prepared)], original_denominators={})
            def fail(path, raw):
                if target in path.name:
                    with path.open("xb") as stream: stream.write(raw[:23])
                    raise OSError("mock partial write")
                return real(path, raw)
            with patch.object(storage, "_write_payload", side_effect=fail):
                run = storage.begin_storage(plan, self.root / f"partial-{self.sequence}")
                if target != "run-plan": storage.write_prepared_group(run, 0)
                report = storage.finish(run)
            attempt = next(a for a in report["artifact_attempts"] if a["error"])
            self.assertEqual(attempt["physical_bytes"], 23)
            self.assertGreater(attempt["attempted_bytes"], 23)
            self.assertEqual(attempt["physical_sha256"], hashlib.sha256(Path(attempt["artifact"]).read_bytes()).hexdigest())
            self.assertFalse(report["submitted_group_set_complete"])
            self.assertFalse(report["storage_integrity_passed"])
            self.assertEqual(report["summary"]["computed_unpersisted_pairs"], target == "-block-")

    def test_finalmanifest_fullwrite_failure_does_not_selfcertify(self):
        source, prepared = self.prepare()
        _, run = self.begin(source, prepared)
        storage.write_prepared_group(run, 0)
        real = storage._write_payload
        def fail(path, raw):
            real(path, raw)
            if path.name == "report.json": raise OSError("mock post-write failure")
        with patch.object(storage, "_write_payload", side_effect=fail): report = storage.finish(run)
        self.assertTrue(report["all_planned_pairs_computed"])
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertFalse(report["terminal_persisted"])
        attempt = next(a for a in report["artifact_attempts"] if a["kind"] == "final_manifest")
        self.assertFalse(json.loads(Path(attempt["artifact"]).read_bytes())["submitted_group_set_complete"])
        self.assert_complements(report)

    def test_coreinterrupt_unconfirmed_not_known_nevercomputedzero(self):
        source, prepared = self.prepare()
        _, run = self.begin(source, prepared)
        with patch.object(core, "compare_block", side_effect=KeyboardInterrupt("small mock")):
            storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertEqual(report["summary"]["computed_pairs"], 0)
        self.assertEqual(report["summary"]["unconfirmed_computation_pairs"], 1)
        self.assertTrue(report["groups"][0]["task_ledger"][0]["calculation_attempted"])
        self.assert_complements(report)

    def test_packet_missing_duplicate_foreign_falseflags_and_selection_rejected(self):
        source, prepared = self.prepare()
        task = next(prepared.iter_blocks())
        valid = core.compare_block(prepared, task)
        for mode in ("missing", "duplicate", "foreign_source", "falseflags", "selected", "boolindex"):
            block = deepcopy(valid)
            if mode == "missing": block["pairs"].clear()
            elif mode == "duplicate": block["pairs"].append(deepcopy(block["pairs"][0]))
            elif mode == "foreign_source": block["source_catalog_ref"]["record_sha256"] = "0" * 64
            elif mode == "falseflags": block["flags"][next(iter(block["flags"]))] = 0
            elif mode == "selected": block["selected"] = "winner"
            else:
                block["pairs"][0]["entry_indices"][0] = False
                block["pairs"][0] = reseal(block["pairs"][0], core.PAIR_PREFIX)
            block = reseal(block, core.BLOCK_PREFIX)
            _, run = self.begin(source, prepared)
            with patch.object(core, "compare_block", return_value=block): storage.write_block(run, 0, task)
            report = storage.finish(run)
            self.assertFalse(report["submitted_group_set_complete"], mode)
            self.assertEqual(report["summary"]["persisted_pairs"], 0)

    def test_original_declaration_source_request_key_selector_and_fakehandles_rejected(self):
        source, prepared = self.prepare()
        for name, value in (("selector_indices", [4, 5]), ("planned_entries", 1), ("planned_pairs", True),
                ("completion_request_ref", request_ref(99))):
            declared = original(prepared); declared[name] = value
            with self.assertRaises(ValueError): storage.plan_saved_run([storage.GroupInput(declared, source, prepared)], original_denominators={})
        for fake in (prepared.export_catalog(), object.__new__(core.SharedPreparedGroup)):
            with self.assertRaises(ValueError): storage.plan_saved_run([storage.GroupInput(original(prepared), source, fake)], original_denominators={})
        for fake in (source.export_source(), object.__new__(core.PreparedSource)):
            with self.assertRaises(ValueError): storage.plan_saved_run([storage.GroupInput(original(prepared), fake, prepared)], original_denominators={})
        with self.assertRaises(ValueError): storage.plan_saved_run([storage.GroupInput(original(prepared), source)], original_denominators={})
        with self.assertRaisesRegex(ValueError, "duplicate_declared"):
            storage.plan_saved_run([storage.GroupInput(original(prepared), source, prepared)] * 2, original_denominators={})

    def registration(self):
        archive = self.root / "archive"; archive.mkdir()
        file = archive / "source.json"
        file.write_bytes(b'{"source":1}')
        sha = storage._file_sha(file)
        return archive, file, {str(file.resolve()): sha}, reads.InventoryRoot(str(archive.resolve()), {str(file.resolve()): sha})

    def test_expected_root_registration_not_currentglob_output_exclusion_and_guard(self):
        source, prepared = self.prepare()
        archive, file, registered, root = self.registration()
        plan = storage.plan_saved_run([storage.GroupInput(original(prepared), source, prepared)], original_denominators={},
            protected_sha256=registered, protected_roots=(root,))
        with self.assertRaisesRegex(ValueError, "outside_registered"):
            storage.begin_storage(plan, archive / "output")
        self.assertFalse((archive / "output").exists())
        run = storage.begin_storage(plan, self.root / "outside")
        storage.write_prepared_group(run, 0)
        (archive / "new-unregistered.json").write_bytes(b"{}")
        report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertIn(str(archive), report["changed_protected_paths"])
        with self.assertRaises(ValueError):
            storage.plan_saved_run([], original_denominators={}, protected_roots=(root,))

    def test_original_file_mutation_detected_terminal_not_perblock_stat_rescan(self):
        source, prepared = self.prepare()
        archive, file, registered, root = self.registration()
        _, run = self.begin(source, prepared, protected_sha256=registered, protected_roots=(root,))
        file.write_bytes(b'{"source":2}')
        storage.write_prepared_group(run, 0)
        provisional = storage.ledger(run)
        self.assertEqual(provisional["summary"]["persisted_pairs"], 1)
        self.assertTrue(provisional["persisted_counts_are_provisional_until_terminal_closure"])
        report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertIn(str(file), report["changed_protected_paths"])
        self.assertFalse(report["physical_closure_verified_terminally"])

    def test_existingdirectory_and_input_changed_before_begin_refused(self):
        source, prepared = self.prepare()
        archive, file, registered, root = self.registration()
        plan = storage.plan_saved_run([storage.GroupInput(original(prepared), source, prepared)], original_denominators={},
            protected_sha256=registered, protected_roots=(root,))
        existing = self.root / "existing-empty"; existing.mkdir()
        with self.assertRaises(FileExistsError): storage.begin_storage(plan, existing)
        with self.assertRaisesRegex(ValueError, "contain_or_replace_registered_input"):
            storage.begin_storage(plan, self.root)
        file.write_bytes(b"changed")
        with self.assertRaises(ValueError): storage.begin_storage(plan, self.root / "new")
        self.assertFalse((self.root / "new").exists())

    def test_guard_interruptions_fail_closed_with_unknown_observation(self):
        source, prepared = self.prepare()
        archive, file, registered, root = self.registration()
        real_sha = storage._file_sha
        for target, when in (("registered", "finish"), ("output", "finish"), ("output", "after"), ("code", "block")):
            _, run = self.begin(source, prepared, protected_sha256=registered, protected_roots=(root,))
            if when != "block": storage.write_prepared_group(run, 0)
            if when == "after": self.assertTrue(storage.finish(run)["submitted_group_set_complete"])
            def interrupt(path):
                name = str(path)
                if ((target == "registered" and name == str(file.resolve()))
                        or (target == "output" and "-block-" in Path(path).name)
                        or (target == "code" and name == str(Path(storage.__file__).resolve()))):
                    raise KeyboardInterrupt("explicit guard interruption")
                return real_sha(path)
            with patch.object(storage, "_file_sha", side_effect=interrupt):
                if when == "block": storage.write_prepared_group(run, 0)
                report = storage.ledger(run) if when == "after" else storage.finish(run)
            self.assertFalse(report["submitted_group_set_complete"], (target, when))
            self.assertFalse(report["physical_closure_verified_terminally"])
            self.assertGreater(report["unconfirmed_guard_observations"], 0)
            self.assertTrue(any("KeyboardInterrupt" in e["error"] for e in report["guard_observation_errors"]))
            self.assertIn("guard_observation_unconfirmed", report["errors"])
            self.assert_complements(report)

    def test_output_alias_or_nonregular_file_cannot_certify_identical_bytes(self):
        source, prepared = self.prepare()
        for method in ("is_symlink", "is_file"):
            _, run = self.begin(source, prepared)
            storage.write_prepared_group(run, 0)
            report = storage.ledger(run)
            target = next(a["artifact"] for a in report["artifact_attempts"] if a["kind"] == "block")
            real = getattr(Path, method)
            def marked(path):
                if str(path) == target: return method == "is_symlink"
                return real(path)
            # Portable explicit metadata mock: no Windows symlink privilege or
            # actual output replacement required to verify fail-closed guard.
            with patch.object(Path, method, autospec=True, side_effect=marked): report = storage.finish(run)
            self.assertFalse(report["submitted_group_set_complete"])
            self.assertIn(target, report["changed_output_paths"])
            self.assertFalse(report["physical_closure_verified_terminally"])

    def test_source_local_block_or_foreign_output_mutation_terminal_and_afterterminal(self):
        source, prepared = self.prepare()
        for kind, when in (("source_catalog", "before"), ("local_catalog", "before"), ("block", "after"), ("foreign", "before")):
            _, run = self.begin(source, prepared)
            storage.write_prepared_group(run, 0)
            if when == "after": self.assertTrue(storage.finish(run)["submitted_group_set_complete"])
            report = storage.ledger(run)
            directory = Path(report["artifact_attempts"][0]["artifact"]).parent
            if kind == "foreign": (directory / "foreign.json").write_bytes(b"{}")
            else:
                path = Path(next(a["artifact"] for a in report["artifact_attempts"] if a["kind"] == kind))
                with path.open("ab") as stream: stream.write(b"corrupted")
            report = storage.finish(run)
            self.assertFalse(report["submitted_group_set_complete"])
            self.assertTrue(report["changed_output_paths"])

    def test_encodingfailure_unknown_bytes_and_unreadable_fragment(self):
        source, prepared = self.prepare()
        _, run = self.begin(source, prepared, compressed=True)
        with patch.object(storage.gzip, "compress", side_effect=MemoryError("mock encoding failure")):
            storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertTrue(report["sources"][0]["encoding_attempted"])
        self.assertIsNone(report["sources"][0]["encoded_bytes"])
        self.assertEqual(report["summary"]["uncomputed_pairs"], 1)
        _, run = self.begin(source, prepared)
        real_write, real_sha = storage._write_payload, storage._file_sha
        def fail_write(path, raw):
            if "-block-" in path.name:
                with path.open("xb") as stream: stream.write(raw[:17])
                raise OSError("mock partial block")
            return real_write(path, raw)
        def fail_sha(path):
            if "-block-" in Path(path).name: raise OSError("mock unreadable")
            return real_sha(path)
        with (patch.object(storage, "_write_payload", side_effect=fail_write),
                patch.object(storage, "_file_sha", side_effect=fail_sha)):
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
        attempt = next(a for a in report["artifact_attempts"] if a["kind"] == "block")
        self.assertIsNone(attempt["physical_bytes"])
        self.assertIsNone(attempt["physical_sha256"])
        self.assertEqual(report["unknown_physical_output_attempts"], 1)
        self.assert_complements(report)

    def test_null_and_knownzero_survive_storage(self):
        # Reuse genuine grace/withheld fixtures from the new codec's suite.
        import test_shared_source_progression_contrast as source_tests
        helper = source_tests.SharedSourceContrastTests()
        helper.fixture = self.fixture
        fixture = self.fixture.fixture
        primary = fixture.selector("grace"); variant = deepcopy(primary)
        scope = fixture.case("grace")[0][1]
        alternative = next(o for c in fixture.record("grace")["catalog_inventory"] if c["span"] == scope["analysis_span"]
            for o in c["origins"] if o["record_id"] not in primary["origin_ids"])
        variant["origin_ids"] = [alternative["record_id"]]
        source, unknown = helper.entries_from(fixture, "grace", [primary, variant], withheld=True)
        known_source, known = self.prepare(control=True)
        for source, prepared, expected in ((source, unknown, None), (known_source, known, q(0))):
            _, run = self.begin(source, prepared)
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
            path = Path(next(a["artifact"] for a in report["artifact_attempts"] if a["kind"] == "block"))
            self.assertEqual(json.loads(path.read_bytes())["pairs"][0]["conditional_credit_delta_right_minus_left"], expected)

    def test_UTF8_caps_and_foreign_cap_positions(self):
        source, prepared = self.prepare()
        plan = storage.plan_saved_run([storage.GroupInput(original(prepared), source, prepared)],
            original_denominators={"설명": "원래 분모" * 50}, task_encoded_caps={(0, 0): 4096})
        run = storage.begin_storage(plan, self.root / "UTF8")
        attempt = storage.ledger(run)["artifact_attempts"][0]
        raw = Path(attempt["artifact"]).read_bytes()
        self.assertEqual(attempt["attempted_bytes"], len(raw))
        self.assertGreater(len(raw), len(raw.decode("utf-8")))
        for caps in ({(0, 0): True}, {(False, 0): 4096}, {(0, 8): 4096}, {(0, 0): 67108865}):
            with self.assertRaises(ValueError): storage.plan_saved_run([storage.GroupInput(original(prepared), source, prepared)],
                original_denominators={}, task_encoded_caps=caps)


if __name__ == "__main__": unittest.main()
