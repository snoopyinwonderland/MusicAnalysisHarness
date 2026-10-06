"""Genuine small saved controls and explicitly injected storage failures.

No actual corpus read/run; imported fixture modules do not add TestCases to this
module's discovery count. Saved JSON is checked as output, never reauthorized.
"""
from copy import deepcopy
from dataclasses import asdict, replace
import gc
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import weakref

from musicanote_harness import transfer_bound_progression_storage as storage
from musicanote_harness import proof_shared_source_progression_contrast as core
from musicanote_harness import proof_shared_progression_streaming as streaming
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import cross_batch_progression_contrast as codec
from musicanote_harness import shared_source_progression_storage as frozen_storage
from musicanote_harness import proof_shared_progression_storage as previous_storage
from musicanote_harness import cross_batch_read_budget as reads
import test_proof_shared_source_progression_contrast as fixture_module


def original(group, *, upstream_grid=False):
    header = codec._copy(core._issued(group).catalog["group"])
    plan = group.preflight_plan
    n, size = plan.entry_count, plan.block_size
    grid = (n + size - 1) // size
    return {"source_identity_sha256": hashlib.sha256(storage._raw(group.source_ref)).hexdigest(),
        **{name: header[name] for name in
            ("scope_ref", "lattice_ref", "completion_request_ref", "key_ref", "bundle_ref")},
        "selector_indices": header["original_selector_indices"], "planned_entries": n,
        "planned_pairs": n * (n - 1) // 2,
        "planned_block_tasks": grid * (grid + 1) // 2 if upstream_grid else plan.planned_blocks,
        "block_size": size}


class StoragePureControls(unittest.TestCase):
    def test_defaults_closed_types_and_flags(self):
        limits = storage.StorageLimits()
        self.assertEqual((limits.max_output_bytes, limits.max_plan_bytes, limits.max_manifest_bytes,
            limits.max_block_encoded_bytes, limits.max_source_encoded_bytes),
            (2147483648, 2097152, 16777216, 67108864, 268435456))
        for name in asdict(limits):
            for invalid in (True, -1, None, "1", .5):
                with self.assertRaises(ValueError): storage.StorageLimits(**{name: invalid})
        self.assertTrue(all(v is False for v in storage._flags().values()))

    def test_compression_explicitly_unsupported(self):
        with self.assertRaisesRegex(ValueError, "compressed_streaming_unsupported"):
            storage.plan_saved_run([], original_denominators={}, compressed=True)

    def test_every_storage_limit_may_only_tighten_defaults(self):
        for name, default in asdict(storage.StorageLimits()).items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "may_only_tighten_defaults"):
                    storage.StorageLimits(**{name: default + 1})
                self.assertEqual(getattr(storage.StorageLimits(**{name: default - 1}), name), default - 1)

    def test_previous_plan_and_JSON_do_not_authorize_new_storage(self):
        previous = previous_storage.plan_saved_run([], original_denominators={})
        current = storage.plan_saved_run([], original_denominators={})
        with tempfile.TemporaryDirectory() as directory:
            for foreign in (previous, previous.record(), current.record()):
                with self.assertRaisesRegex(ValueError, "owned_shared_storage_plan_required_not_JSON"):
                    storage.begin_storage(foreign, Path(directory) / "must-not-exist")
            self.assertFalse((Path(directory) / "must-not-exist").exists())

    def test_owned_empty_plan_copies_and_registry_replay_rejected(self):
        plan = storage.plan_saved_run([], original_denominators={"archive_entries": 8050})
        record = plan.record(); record["original_denominators"]["archive_entries"] = 0
        self.assertEqual(plan.record()["original_denominators"]["archive_entries"], 8050)
        for cls in (storage.StoragePlan, storage.StorageRun):
            with self.assertRaises(ValueError): cls()
        foreign = object.__new__(storage.StoragePlan)
        storage._PLANS[foreign] = storage._PLANS[plan]
        with self.assertRaisesRegex(ValueError, "state_changed"): foreign.record()
        saved = storage._PLANS[plan]
        storage._PLANS[plan] = replace(saved, record=b"{}")
        try:
            with self.assertRaisesRegex(ValueError, "state_changed"): plan.record()
        finally:
            storage._PLANS[plan] = saved
        for value in ({}, object.__new__(storage.StorageRun)):
            with self.assertRaises(ValueError): storage.ledger(value)

    def test_zero_reservations_never_create_output(self):
        for limits in (storage.StorageLimits(max_output_bytes=0), storage.StorageLimits(max_manifest_bytes=0)):
            plan = storage.plan_saved_run([], original_denominators={"whole_pairs": 1652640}, limits=limits)
            self.assertTrue(plan.record()["reasons"])
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "no-prefix"
                with self.assertRaises(storage.WholeRunHold): storage.begin_storage(plan, target)
                self.assertFalse(target.exists())
        with self.assertRaises(ValueError):
            storage.plan_saved_run([], original_denominators={}, limits=storage.StorageLimits(max_plan_bytes=0))

    def test_known_empty_run_does_not_claim_original_archive_completion(self):
        plan = storage.plan_saved_run([], original_denominators={"whole_archive_pairs": 1652640})
        with tempfile.TemporaryDirectory() as directory:
            run = storage.begin_storage(plan, Path(directory) / "empty")
            report = storage.finish(run)
            self.assertTrue(report["submitted_group_set_complete"])
            self.assertEqual(report["planned_submitted_groups"], 0)
            self.assertEqual(report["original_denominators"]["whole_archive_pairs"], 1652640)
            self.assertTrue(all(v is False for v in report["flags"].values()))
            foreign = object.__new__(storage.StorageRun)
            storage._STORES[foreign] = storage._STORES[run]
            with self.assertRaisesRegex(ValueError, "state_changed"): storage.ledger(foreign)

    def test_released_empty_plan_run_with_gc_disabled(self):
        before = gc.isenabled(); gc.disable()
        try:
            plan = storage.plan_saved_run([], original_denominators={})
            observed = weakref.ref(plan)
            del plan
            self.assertIsNone(observed())
            with tempfile.TemporaryDirectory() as directory:
                plan = storage.plan_saved_run([], original_denominators={})
                run = storage.begin_storage(plan, Path(directory) / "released")
                storage.finish(run)
                observed = weakref.ref(run)
                del run
                self.assertIsNone(observed())
        finally:
            if before: gc.enable()


class ProofSourceOnceStorageControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.ProofSharedSourceContrastTests.setUpClass()
        cls.addClassCleanup(fixture_module.ProofSharedSourceContrastTests.doClassCleanups)
        cls.fixture = fixture_module.ProofSharedSourceContrastTests()
        cls.source, cls.entries = cls.fixture.inputs()
        cls.groups = {}

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sequence = 0

    def group(self, n=2, *, request=0, block_size=1):
        key = n, request, block_size
        if key not in self.groups:
            source, entries = self.source, self.entries[:n]
            if n == 3:
                fixture = self.fixture.fixture.fixture.fixture
                members = fixture_module.shared_fixture.fixture_module.fixture_module.members("C", "E", "G")
                selectors = [fixture.selector("three_slots"),
                    fixture.selector("three_slots", partitions=[(fixture_module.span(0, 4), ("C", fixture_module.Fraction()), members)], assumptions=[]),
                    fixture.selector("three_slots", partitions=[(fixture_module.span(0, 1), ("C", fixture_module.Fraction()), members),
                        (fixture_module.span(1, 4), ("C", fixture_module.Fraction()), members)], assumptions=[None])]
                source, entries, _ = self.fixture.from_selectors("three_slots", selectors)
            self.groups[key] = core.prepare_saved_group(source, entries,
                completion_request_ref=fixture_module.request_ref(request),
                key_ref=(entries or self.entries)[0]["native_path"]["key_ref"],
                bundle_ref=(entries or self.entries)[0]["native_path"]["bundle_ref"],
                selector_indices=list(range(3, 3 + n)), block_size=block_size)
        return self.groups[key]

    def plan(self, *groups, **options):
        return storage.plan_saved_run([storage.GroupInput(original(group), core._issued(group).source, group) for group in groups],
            original_denominators={"whole_original_entries": 8050, "whole_original_pairs": 1652640}, **options)

    def begin(self, group=None, **options):
        group = self.group() if group is None else group
        plan = self.plan(group, **options)
        self.sequence += 1
        return plan, storage.begin_storage(plan, self.root / f"out-{self.sequence}")

    def assert_complements(self, report):
        s = report["summary"]
        self.assertEqual(s["planned_pairs"], s["computed_pairs"] + s["held_pairs"] + s["uncomputed_pairs"])
        self.assertEqual(s["planned_pairs"], s["persisted_pairs"] + s["unpersisted_pairs"])
        self.assertEqual(s["computed_unpersisted_pairs"], s["computed_pairs"] - s["persisted_pairs"])
        self.assertTrue(all(value is False for value in report["flags"].values()))

    def test_proof_prepared_once_and_task_bounds_use_same_owned_group(self):
        group = self.group(3)
        real_prepare = storage.transfer_bounds.prepare_transfer_bounds
        real_bound = storage.transfer_bounds.task_stream_bound
        with (patch.object(storage.transfer_bounds, "prepare_transfer_bounds", wraps=real_prepare) as factory,
                patch.object(storage.transfer_bounds, "task_stream_bound", wraps=real_bound) as bound,
                patch.object(core, "compare_block", side_effect=AssertionError("no pair during planning"))):
            plan = self.plan(group)
        record = plan.record()
        self.assertEqual(record["reasons"], [])
        proof = storage._plan(plan).transfer_proofs[0]
        self.assertIs(storage.transfer_bounds._issued(proof).prepared, group)
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(bound.call_count, group.preflight_plan.planned_blocks)
        self.assertTrue(all(call.args[0] is proof for call in bound.call_args_list))
        row = record["groups"][0]
        catalog_work = storage._plan(plan).catalog_infos[0]["planning_work"]
        expected = (record["metadata_snapshot_work"] + 65536 + 4 * len(storage._raw(row["original"]))
            + catalog_work + row["transfer_proof_work_once"]
            + sum(item["inspection_work"] for item in row["task_stream_bounds"]))
        self.assertEqual(row["stream_planning_work"], expected)
        self.assertEqual(row["transfer_proof_work_once"], row["transfer_proof_diagnostic"]["preparation_work_once"])
        self.assertTrue(all(item["bound_strategy"] == "owned_category_support_exact_lcm"
            for item in row["task_stream_bounds"]))
        self.assertIn(str(Path(storage.transfer_bounds.__file__).resolve()), record["protected_sha256"])
        self.assertIn("no_outcome_sampling", record["transfer_bound_policy"])

    def test_tighter_whole_reservation_releases_old_hold_without_candidate_removal(self):
        group = self.group(3)
        baseline = self.plan(group).record()
        maximum = baseline["output_reserved_bytes_before_pair_calculation"]
        limits = storage.StorageLimits(max_output_bytes=maximum)
        current = self.plan(group, limits=limits)
        old = previous_storage.plan_saved_run([
            previous_storage.GroupInput(original(group), core._issued(group).source, group)],
            original_denominators=baseline["original_denominators"],
            limits=previous_storage.StorageLimits(max_output_bytes=maximum))
        self.assertEqual(current.record()["reasons"], [])
        self.assertIn("whole_output_reservation_exceeds_limit_no_prefix", old.record()["reasons"])
        self.assertGreater(old.record()["output_reserved_bytes_before_pair_calculation"], maximum)
        for field in ("original_denominators", "planned_submitted_groups", "planned_submitted_entries",
                "planned_submitted_pairs", "planned_submitted_nonempty_tasks", "planned_declared_upstream_tasks"):
            self.assertEqual(current.record()[field], old.record()[field])
        self.assertEqual(current.record()["groups"][0]["original"], old.record()["groups"][0]["original"])
        run = storage.begin_storage(current, self.root / "same-complete-group")
        storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertTrue(report["submitted_group_set_complete"])
        self.assertEqual(report["summary"]["persisted_pairs"], 3)
        self.assertLessEqual(report["physical_output_bytes"], maximum)
        self.assert_complements(report)

    def test_proof_preparation_work_hold_keeps_whole_original_and_unknown_bounds(self):
        group = self.group(3)
        # Explicit failure injection, not an actual corpus resource finding.
        error = storage.transfer_bounds.TransferBoundHold("explicit_test_proof_work_hold", 37)
        with (patch.object(storage.transfer_bounds, "prepare_transfer_bounds", side_effect=error),
                patch.object(core, "compare_block", side_effect=AssertionError("no held pair"))):
            plan = self.plan(group)
            record = plan.record()
            with self.assertRaises(storage.WholeRunHold):
                storage.begin_storage(plan, self.root / "no-provisional-prefix")
        self.assertFalse((self.root / "no-provisional-prefix").exists())
        self.assertIn("whole_transfer_proof_preparation_hold_no_prefix", record["reasons"])
        self.assertEqual((record["planned_submitted_entries"], record["planned_submitted_pairs"],
            record["planned_submitted_nonempty_tasks"]), (3, 3, 3))
        self.assertEqual(record["groups"][0]["original"], original(group))
        self.assertIsNone(record["output_reserved_bytes_before_pair_calculation"])
        self.assertIsNone(record["groups"][0]["task_stream_bounds"])
        self.assertEqual(record["groups"][0]["transfer_proof_work_once"], 37)
        self.assertGreater(record["groups"][0]["stream_planning_work"], 37)

    def test_proof_failure_before_comparison_is_known_uncomputed_not_unknown_computation(self):
        group = self.group(3)
        _, run = self.begin(group)
        with (patch.object(storage.transfer_bounds, "_issued", side_effect=ValueError("explicit proof binding failure")),
                patch.object(core, "compare_block", side_effect=AssertionError("proof must precede pair"))):
            report = storage.write_block(run, 0, next(group.iter_blocks()))
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertEqual(report["summary"]["computed_pairs"], 0)
        self.assertEqual(report["summary"]["unconfirmed_computation_pairs"], 0)
        self.assertEqual(report["summary"]["uncomputed_pairs"], 3)
        self.assertEqual(len(report["groups"][0]["uncomputed_task_ranges"]), 3)
        first = report["groups"][0]["task_ledger"][0]
        self.assertFalse(first["calculation_attempted"])
        self.assertEqual(first["status"], "interrupted_before_comparison")
        self.assert_complements(report)

    def test_owned_proof_lifetime_is_plan_bounded_without_gc_cycle(self):
        group = self.group()
        before = gc.isenabled()
        gc.disable()
        try:
            plan = self.plan(group)
            proof = storage._plan(plan).transfer_proofs[0]
            observed = weakref.ref(proof)
            del proof
            self.assertIsNotNone(observed())
            del plan
            self.assertIsNone(observed())
        finally:
            if before:
                gc.enable()

    def test_genuine_streamed_source_cached_DAG_and_block_exact_roundtrip(self):
        group = self.group()
        expected_source, expected_catalog = self.source.export_source(), group.export_catalog()
        with (patch.object(shared.PreparedSource, "export_source", side_effect=AssertionError("no full source export")),
                patch.object(core.CompactPreparedGroup, "export_catalog", side_effect=AssertionError("no full DAG export")),
                patch.object(core.CompactPreparedGroup, "export_entry", side_effect=AssertionError("no entry expansion")),
                patch.object(core.CompactPreparedGroup, "export_facet", side_effect=AssertionError("no facet expansion")),
                patch.object(core, "materialize_pair", side_effect=AssertionError("no legacy pair expansion")),
                patch.object(frozen_storage, "begin_storage", side_effect=AssertionError("no registry adapter")),
                patch.object(core.native, "compare_prepared", side_effect=AssertionError("no producer"))):
            plan, run = self.begin(group)
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
        self.assertTrue(report["submitted_group_set_complete"], report["errors"])
        self.assert_complements(report)
        for attempt in report["artifact_attempts"]:
            raw = Path(attempt["artifact"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), attempt["physical_sha256"])
            saved = json.loads(raw)
            if attempt["kind"] == "source_catalog": self.assertEqual(saved, expected_source)
            elif attempt["kind"] == "local_catalog": self.assertEqual(saved, expected_catalog)
            elif attempt["kind"] == "block": self.assertEqual(saved, core.compare_block(group, next(group.iter_blocks())))
            elif attempt["kind"] == "final_manifest":
                self.assertFalse(saved["submitted_group_set_complete"])
                self.assertFalse(saved["terminal_persisted"])
                self.assertIn("cannot_self_certify", saved["terminal_commit_contract"])
        self.assertLessEqual(report["physical_output_bytes"], plan.record()["output_reserved_bytes_before_pair_calculation"])
        self.assertEqual(report["canonical_stream_account"]["iteration_completed"], 2)
        self.assertGreater(report["file_hash_IO"]["physical_hash_bytes"], 0)

    def test_same_owned_source_iteration_once_independent_groups(self):
        first, second = self.group(request=1), self.group(request=2)
        real = streaming.iter_source_json
        with patch.object(streaming, "iter_source_json", wraps=real) as iterator:
            plan = self.plan(first, second)
            run = storage.begin_storage(plan, self.root / "one-source")
            for index in (0, 1): storage.write_prepared_group(run, index)
            report = storage.finish(run)
            self.assertEqual(iterator.call_count, 1)
        self.assertTrue(report["submitted_group_set_complete"])
        self.assertEqual(report["canonical_stream_account"]["source_iteration_attempts"], 1)
        self.assertEqual(report["persisted_shared_sources"], 1)
        self.assertEqual(sum(a["kind"] == "source_catalog" for a in report["artifact_attempts"]), 1)
        state = storage._plan(plan)
        self.assertIs(state.sources[0], self.source)
        self.assertIs(state.handles[0], first)
        self.assertFalse(hasattr(state, "source_raw"))
        self.assertFalse(hasattr(state, "catalog_raw"))
        with self.assertRaises(TypeError): state.source_infos[0]["canonical_bytes"] = 0

    def test_default_schema_reservation_not_blanket_64MiB_per_task(self):
        plan = self.plan(self.group(n=3))
        record = plan.record()
        self.assertFalse(record["reasons"], record["reasons"])
        row = record["groups"][0]
        self.assertEqual(len(row["tasks"]), 3)
        self.assertLess(sum(row["task_encoded_caps"]), 3 * storage.StorageLimits().max_block_encoded_bytes)
        self.assertTrue(record["output_reservation_complete"])
        self.assertEqual(record["plan_finalization_account"]["canonical_serialization_passes"], 1)
        self.assertGreater(record["plan_finalization_account"]["size_measurement_work"], 0)

    def test_mutable_declarations_denominators_and_caps_are_not_later_authority(self):
        group = self.group(); declared = original(group); denominator = {"whole": 8050}
        plan = storage.plan_saved_run([storage.GroupInput(declared, self.source, group)], original_denominators=denominator)
        declared["selector_indices"].clear(); denominator["whole"] = 0
        self.assertEqual(plan.record()["groups"][0]["original"]["selector_indices"], [3, 4])
        self.assertEqual(plan.record()["original_denominators"], {"whole": 8050})

    def test_all_original_membership_checks_even_count_wholehold(self):
        group = self.group()
        for key, value in (("selector_indices", [9, 10]), ("completion_request_ref", fixture_module.request_ref(99)),
                ("planned_entries", 1), ("planned_pairs", True)):
            declared = original(group); declared[key] = value
            with self.assertRaises(ValueError):
                storage.plan_saved_run([storage.GroupInput(declared, self.source, group)], original_denominators={},
                    limits=storage.StorageLimits(max_groups=0))

    def test_held_absent_foreign_v1_JSON_and_duplicate_groups_rejected(self):
        group = self.group(); declared = original(group)
        for item in (storage.GroupInput(declared, self.source), storage.GroupInput(declared, self.source, {}),
                storage.GroupInput(declared, self.source, object.__new__(core.CompactPreparedGroup)),
                storage.GroupInput(declared, {}, group)):
            with self.assertRaises(ValueError): storage.plan_saved_run([item], original_denominators={})
        with self.assertRaisesRegex(ValueError, "duplicate_declared"):
            self.plan(group, group)
        v1 = shared.prepare_saved_group(self.source, self.entries, completion_request_ref=fixture_module.request_ref())
        with self.assertRaises(ValueError):
            storage.plan_saved_run([storage.GroupInput(declared, self.source, v1)], original_denominators={})

    def test_equal_record_other_handle_not_source_once_authority(self):
        other, _ = self.fixture.inputs()
        self.assertEqual(other.source_ref, self.source.source_ref)
        with self.assertRaisesRegex(ValueError, "same_owned_source"):
            storage.plan_saved_run([storage.GroupInput(original(self.group()), other, self.group())], original_denominators={})
        group = core.prepare_saved_group(other, self.entries, completion_request_ref=fixture_module.request_ref(22))
        with self.assertRaisesRegex(ValueError, "same_owned_handle"):
            storage.plan_saved_run([storage.GroupInput(original(self.group()), self.source, self.group()),
                storage.GroupInput(original(group), other, group)], original_denominators={})

    def test_whole_byte_source_manifest_task_and_lowered_cap_holds_no_pair_prefix(self):
        group = self.group()
        options = [{"limits": storage.StorageLimits(max_output_bytes=1)},
            {"limits": storage.StorageLimits(max_manifest_bytes=1)},
            {"limits": storage.StorageLimits(max_source_encoded_bytes=1)},
            {"limits": storage.StorageLimits(max_block_encoded_bytes=0)}, {"task_encoded_caps": {(0, 0): 512}}]
        for option in options:
            with patch.object(core, "compare_block", side_effect=AssertionError("no pair prefix")):
                plan = self.plan(group, **option)
                self.assertTrue(plan.record()["reasons"])
                self.assertEqual(plan.record()["planned_submitted_pairs"], 1)
                with self.assertRaises(storage.WholeRunHold): storage.begin_storage(plan, self.root / "not-created")
                self.assertFalse((self.root / "not-created").exists())

    def test_count_gate_no_source_scan_or_task_expansion_and_unknown_reserve_not_zero(self):
        group = self.group(n=3)
        with (patch.object(streaming, "source_stream_info", side_effect=AssertionError("no scan")),
                patch.object(core.CompactPreparedGroup, "iter_blocks", side_effect=AssertionError("no task expansion"))):
            plan = self.plan(group, limits=storage.StorageLimits(max_tasks=1))
        record = plan.record()
        self.assertEqual(record["planned_submitted_nonempty_tasks"], 3)
        self.assertFalse(record["output_reservation_complete"])
        self.assertIsNone(record["output_reserved_bytes_before_pair_calculation"])
        self.assertGreater(record["partial_accounted_output_reservation_bytes"], 0)

    def test_workhold_unknown_bound_is_wholehold_not_TypeError(self):
        group = self.group()
        real = storage.transfer_bounds.task_stream_bound
        def workhold(proof, task, **options):
            return real(proof, task, max_work=0, max_block_bytes=options["max_block_bytes"])
        with patch.object(storage.transfer_bounds, "task_stream_bound", side_effect=workhold): plan = self.plan(group)
        record = plan.record()
        self.assertTrue(record["reasons"])
        self.assertEqual(record["groups"][0]["task_stream_bounds"][0]["expected_pairs"], 1)
        self.assertIsNone(record["output_reserved_bytes_before_pair_calculation"])

    def test_foreign_boolean_caps_and_tasks_rejected(self):
        group = self.group(n=3)
        for cap in ({(0, 0): True}, {(False, 0): 1024}, {(0, 99): 1024}, {(0, 0): 67108865}):
            with self.assertRaises(ValueError): self.plan(group, task_encoded_caps=cap)
        _, run = self.begin(group)
        tasks = list(group.iter_blocks())
        for task in (tasks[1], replace(tasks[0], row_start=False), replace(tasks[0], expected_pairs=True),
                replace(tasks[0], source_sha256="0" * 64)):
            with self.assertRaises(ValueError): storage.write_block(run, 0, task)
        storage.write_block(run, 0, tasks[0])
        with self.assertRaises(ValueError): storage.write_block(run, 0, tasks[0])
        report = storage.finish(run)
        self.assertEqual(report["summary"]["uncomputed_pairs"], 2)
        self.assert_complements(report)

    def test_zero_single_and_known_empty_groups_keep_upstream_denominators(self):
        for n in (0, 1):
            group = self.group(n=n)
            plan = storage.plan_saved_run([storage.GroupInput(original(group, upstream_grid=True), self.source, group)],
                original_denominators={"archive_pairs": 1652640})
            run = storage.begin_storage(plan, self.root / f"zero-{n}")
            storage.write_prepared_group(run, 0)
            report = storage.finish(run)
            self.assertTrue(report["submitted_group_set_complete"])
            self.assertEqual(report["summary"]["planned_pairs"], 0)
            self.assertEqual(report["groups"][0]["declared_zero_pair_tasks"], n)
            self.assert_complements(report)

    def test_group_writer_single_ledger_copy_and_no_historical_output_scan_per_block(self):
        group = self.group(n=3); _, run = self.begin(group)
        with (patch.object(storage, "ledger", wraps=storage.ledger) as ledger,
                patch.object(storage, "_outputs", side_effect=AssertionError("no output history scan"))):
            storage.write_prepared_group(run, 0)
            self.assertEqual(ledger.call_count, 1)
        self.assertTrue(storage.finish(run)["submitted_group_set_complete"])

    def test_core_interrupt_retained_traceback_unknown_and_GC_disabled_cleanup(self):
        _, run = self.begin(); observed = []; tracebacks = []
        class LargeTemporary: pass
        def interrupted(prepared, task):
            temporary = LargeTemporary(); temporary.data = bytearray(2 * 1048576)
            observed.append(weakref.ref(temporary))
            try: raise KeyboardInterrupt("explicit interruption")
            except BaseException as exc:
                tracebacks.append(exc.__traceback__)
                raise
        before = gc.isenabled(); gc.disable()
        try:
            with patch.object(core, "compare_block", side_effect=interrupted): storage.write_prepared_group(run, 0)
            self.assertIsNone(observed[0]())
        finally:
            if before: gc.enable()
        report = storage.finish(run)
        self.assertEqual(report["summary"]["unconfirmed_computation_pairs"], 1)
        self.assertEqual(report["summary"]["computed_pairs"], 0)
        self.assert_complements(report)

    def fault_open(self, target, *, partial=False, post_flush=False):
        real = Path.open
        class Fault:
            def __init__(self, file): self.file = file
            def write(self, raw):
                if partial:
                    self.file.write(raw[:23]); raise OSError("explicit partial write")
                return self.file.write(raw)
            def flush(self):
                self.file.flush()
                if post_flush: raise OSError("explicit post-write failure")
            def fileno(self): return self.file.fileno()
            def close(self): return self.file.close()
        def opened(path, mode="r", *args, **kwargs):
            file = real(path, mode, *args, **kwargs)
            return Fault(file) if mode == "xb" and target in path.name else file
        return patch.object(Path, "open", new=opened)

    def test_partial_run_plan_source_catalog_block_nonrefundable_fragments(self):
        group = self.group()
        for target in ("run-plan", "source-", "group-0000-catalog", "-block-"):
            plan = self.plan(group); self.sequence += 1
            with self.fault_open(target, partial=True):
                run = storage.begin_storage(plan, self.root / f"partial-{self.sequence}")
                if target != "run-plan": storage.write_prepared_group(run, 0)
                report = storage.finish(run)
            attempt = next(a for a in report["artifact_attempts"] if a["error"])
            self.assertEqual(attempt["physical_bytes"], 23)
            self.assertGreater(attempt["attempted_bytes"], 23)
            self.assertFalse(attempt["persisted"])
            self.assertFalse(report["submitted_group_set_complete"])
            self.assertEqual(report["summary"]["computed_unpersisted_pairs"], int(target == "-block-"))
            self.assert_complements(report)

    def test_iterator_interrupt_keeps_unknown_hash_and_no_computation(self):
        _, run = self.begin()
        def interrupted(source, **options):
            yield b"{" * 23
            raise KeyboardInterrupt("explicit source stream stop")
        with patch.object(streaming, "iter_source_json", new=interrupted): storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        attempt = next(a for a in report["artifact_attempts"] if a["kind"] == "source_catalog")
        self.assertFalse(attempt["stream_complete"])
        self.assertIsNone(attempt["complete_stream_sha256"])
        self.assertEqual(attempt["physical_bytes"], 23)
        self.assertEqual(report["summary"]["uncomputed_pairs"], 1)
        self.assertEqual(report["canonical_stream_account"]["iteration_unknown"], 1)

    def test_final_manifest_full_write_failure_never_self_certifies(self):
        _, run = self.begin(); storage.write_prepared_group(run, 0)
        with self.fault_open("report.json", post_flush=True): report = storage.finish(run)
        self.assertTrue(report["all_planned_pairs_computed"])
        self.assertFalse(report["terminal_persisted"])
        self.assertFalse(report["submitted_group_set_complete"])
        attempt = next(a for a in report["artifact_attempts"] if a["kind"] == "final_manifest")
        self.assertTrue(attempt["stream_complete"])
        self.assertFalse(json.loads(Path(attempt["artifact"]).read_bytes())["submitted_group_set_complete"])

    def registration(self):
        archive = self.root / "archive"; archive.mkdir()
        file = archive / "mock-registered.json"; file.write_bytes(b'{"mock_saved":1}')
        checksum = hashlib.sha256(file.read_bytes()).hexdigest()
        hashes = {str(file.resolve()): checksum}
        return archive, file, hashes, reads.InventoryRoot(str(archive.resolve()), hashes)

    def test_input_root_snapshot_terminal_foreign_file_and_output_exclusion(self):
        archive, file, hashes, root = self.registration()
        plan = self.plan(self.group(), protected_sha256=hashes, protected_roots=(root,))
        with self.assertRaisesRegex(ValueError, "outside_registered"): storage.begin_storage(plan, archive / "output")
        run = storage.begin_storage(plan, self.root / "outside")
        storage.write_prepared_group(run, 0)
        (archive / "foreign.json").write_bytes(b"{}")
        report = storage.finish(run)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertIn(str(archive), report["changed_protected_paths"])

    def test_begin_fresh_guard_missing_input_and_exclusive_destination(self):
        archive, file, hashes, root = self.registration()
        plan = self.plan(self.group(), protected_sha256=hashes, protected_roots=(root,))
        file.write_bytes(b'{"mock_saved":2}')
        with self.assertRaises(ValueError): storage.begin_storage(plan, self.root / "unchanged-output")
        self.assertFalse((self.root / "unchanged-output").exists())
        existing = self.root / "exists"; existing.mkdir()
        plan = self.plan(self.group())
        with self.assertRaises(FileExistsError): storage.begin_storage(plan, existing)

    def test_owned_output_modified_after_terminal_revokes_completion(self):
        _, run = self.begin(); storage.write_prepared_group(run, 0)
        report = storage.finish(run)
        self.assertTrue(report["submitted_group_set_complete"])
        block = next(a for a in report["artifact_attempts"] if a["kind"] == "block")
        Path(block["artifact"]).write_bytes(b"{}")
        observed = storage.ledger(run)
        self.assertFalse(observed["submitted_group_set_complete"])
        self.assertFalse(observed["storage_integrity_passed"])
        self.assertIn(block["artifact"], observed["changed_output_paths"])

    def test_guard_KeyboardInterrupt_is_unconfirmed_and_no_pair_computation(self):
        _, run = self.begin(); real = storage._file_observe
        def interrupted(path, io, phase):
            if phase == "per_block_current_code": raise KeyboardInterrupt("explicit guard stop")
            return real(path, io, phase)
        with (patch.object(storage, "_file_observe", new=interrupted),
                patch.object(core, "compare_block", side_effect=AssertionError("guard must precede pair"))):
            report = storage.write_prepared_group(run, 0)
        self.assertFalse(report["submitted_group_set_complete"])
        self.assertGreater(report["unconfirmed_guard_observations"], 0)
        self.assertEqual(report["summary"]["uncomputed_pairs"], 1)

    def test_identical_byte_symlink_owned_output_cannot_pass_terminal(self):
        _, run = self.begin(); storage.write_prepared_group(run, 0)
        report = storage.ledger(run)
        block = next(a for a in report["artifact_attempts"] if a["kind"] == "block")
        path = Path(block["artifact"]); copy = self.root / "identical-copy.json"
        copy.write_bytes(path.read_bytes())
        path.unlink()
        try: os.symlink(copy, path)
        except OSError as exc:
            path.write_bytes(copy.read_bytes())
            self.skipTest("OS symlink permission unavailable: " + str(exc))
        observed = storage.finish(run)
        self.assertFalse(observed["submitted_group_set_complete"])
        self.assertIn(str(path), observed["changed_output_paths"])


if __name__ == "__main__":
    unittest.main()
