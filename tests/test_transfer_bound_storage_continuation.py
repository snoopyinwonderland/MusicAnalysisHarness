"""Real small writer packets; historical archive ancestry explicitly mocked.

These unit fixtures cannot establish the actual corpus's provenance or accuracy.
The independently pinned actual runner is needed for that admission check.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import transfer_bound_storage_continuation as resume
from musicanote_harness import transfer_bound_progression_storage as storage
from musicanote_harness import transfer_bound_request_coordinator as request
from musicanote_harness import proof_shared_source_progression_contrast as core
import test_scoped_source_archive_pilot as fixtures
import test_source_progression_replay_trial as factory


class ContinuationControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory.ReplayPacketStorageTests.setUpClass()
        cls.addClassCleanup(factory.ReplayPacketStorageTests.doClassCleanups)

    def setUp(self):
        self.data = fixtures.ScopedPacketFixture(self)
        self.prepared = request.prepare_selected_request(self.data.scoped_open())
        self.root = self.data.fixture.root / "pinned-prior"
        self.root.mkdir()
        self.oldrun = storage.begin_storage(self.prepared.storage_plan, str(self.root / "comparison-storage"))
        state = storage._store(self.oldrun)
        # Genuine borrowed catalog artifacts, without computing future tasks.
        for si in range(len(state["sources"])): storage._ensure_catalog(state, si, source=True)
        for gi in range(len(state["groups"])): storage._ensure_catalog(state, gi)
        first = next(request._issued(self.prepared).groups[0].iter_blocks())
        storage.write_block(self.oldrun, 0, first)
        terminal = storage.finish(self.oldrun)
        self.assertTrue(terminal["physical_closure_verified_terminally"])
        self.report = {"failure": None, "current_code_final_guard": {"all_current_SHA_confirmed": True,
            "changed_paths": [], "uncertain_paths": []}, "artifacts": [],
            "whole_request_preparation": self.prepared.record(),
            "storage_execution": {"failure": None, "storage_terminal": terminal}}
        self.path = self.root / "pilot-report.json"
        self.path.write_bytes(storage._raw(self.report))
        self.pin = storage._sha(self.path.read_bytes())

    def checkpoint(self): return resume.load_checkpoint(self.path, self.pin)
    def plan(self, **options): return resume.plan_continuation(self.prepared, self.checkpoint(), **options)
    def begin(self): return resume.begin_continuation(self.plan(), self.data.fixture.root / "continuation")
    def complete(self, run):
        record = resume.ledger(run)
        for t in record["remaining_task_ledger"]:
            resume.write_block(run, t["group_index"], core.BlockTask(**t["task"]))
        return resume.finish(run)

    def test_fresh_handle_reuses_only_prefix_new_pairs_are_identical_no_old_registry_restore(self):
        new = request.prepare_selected_request(self.data.scoped_open())
        self.assertIsNot(new, self.prepared)
        old_registry = len(storage._STORES)
        plan = resume.plan_continuation(new, self.checkpoint())
        record = plan.record()
        run = resume.begin_continuation(plan, self.data.fixture.root / "continuation")
        with patch.object(core, "compare_block", wraps=core.compare_block) as calculate:
            final = self.complete(run)
        self.assertEqual(calculate.call_count, len(record["remaining_tasks"]))
        self.assertEqual(len(storage._STORES), old_registry)
        self.assertTrue(final["selected_request_storage_complete"])
        self.assertFalse(final["full_archive_complete"])
        self.assertEqual(final["summary"]["persisted_pairs"], new.record()["selected_completion"]["pairs"])
        self.assertEqual(final["prior_persisted_pairs"] + final["new_summary"]["persisted_pairs"], final["summary"]["persisted_pairs"])
        self.assertFalse(final["prior_block_contents_decoded_or_recomputed"])
        self.assertLessEqual(final["prior_storage_physical_bytes"] + final["new_physical_output_bytes"],
            final["combined_output_reserved_bytes_before_pair_calculation"])
        self.assertEqual(sum(a["kind"] == "block" for a in final["artifact_attempts"]), len(record["remaining_tasks"]))
        self.assertFalse(any(a["kind"].endswith("catalog") for a in final["artifact_attempts"]))
        for t in record["remaining_tasks"]:
            p = self.data.fixture.root / "continuation" / f'group-{t["group_index"]:04d}-block-{t["task_index"]:06d}.json'
            expected = core.compare_block(request._issued(new).groups[t["group_index"]], core.BlockTask(**t["task"]))
            self.assertEqual(p.read_bytes(), storage._raw(expected))

    def test_copies_and_forged_handles_never_authorize(self):
        checkpoint = self.checkpoint(); plan = resume.plan_continuation(self.prepared, checkpoint)
        for fake in (checkpoint.record(), object.__new__(resume.Checkpoint)):
            with self.assertRaises((ValueError, AttributeError)): resume.plan_continuation(self.prepared, fake)
        for fake in (self.prepared.record(), object()):
            with self.assertRaises(ValueError): resume.plan_continuation(fake, checkpoint)
        for fake in (plan.record(), object.__new__(resume.ContinuationPlan)):
            with self.assertRaises(ValueError): resume.begin_continuation(fake, self.root / "foreign")
        for fake in ({}, self.oldrun, object.__new__(resume.ContinuationRun)):
            with self.assertRaises(ValueError): resume.finish(fake)
        copy = plan.record(); copy["remaining_tasks"].clear()
        self.assertTrue(plan.record()["remaining_tasks"])
        for cls in (resume.Checkpoint, resume.ContinuationPlan, resume.ContinuationRun):
            with self.assertRaises(ValueError): cls()
        with self.assertRaises(AttributeError): plan.selection = [1, 0]

    def test_wrong_pin_and_resealed_receipt_under_original_pin_fail(self):
        with self.assertRaises(ValueError): resume.load_checkpoint(self.path, "0" * 64)
        self.report["storage_execution"]["storage_terminal"]["summary"]["persisted_pairs"] += 1
        self.path.write_bytes(storage._raw(self.report))
        with self.assertRaises(ValueError): resume.load_checkpoint(self.path, self.pin)

    def test_even_externally_repinned_diagnostic_cannot_override_fresh_binding(self):
        self.report["whole_request_preparation"]["storage_plan"]["groups"][0]["original"]["selector_indices"].reverse()
        self.path.write_bytes(storage._raw(self.report)); pin = storage._sha(self.path.read_bytes())
        checkpoint = resume.load_checkpoint(self.path, pin)
        with self.assertRaises(ValueError): resume.plan_continuation(self.prepared, checkpoint)

    def test_prior_artifact_changed_or_foreign_inventory_rejected(self):
        attempt = self.report["storage_execution"]["storage_terminal"]["artifact_attempts"][-1]
        target = Path(attempt["artifact"])
        original = target.read_bytes(); target.write_bytes(original + b" ")
        with self.assertRaises(ValueError): self.checkpoint()
        target.write_bytes(original)
        (self.root / "unregistered.txt").write_bytes(b"foreign")
        with self.assertRaises(ValueError): self.checkpoint()

    def test_clean_terminal_flags_required(self):
        self.report["storage_execution"]["storage_terminal"]["terminal_persisted"] = False
        self.path.write_bytes(storage._raw(self.report)); self.pin = storage._sha(self.path.read_bytes())
        with self.assertRaises(ValueError): self.checkpoint()

    def test_foreign_artifact_path_and_missing_task_prefix_rejected(self):
        self.report["storage_execution"]["storage_terminal"]["artifact_attempts"][0]["artifact"] = str(self.data.fixture.output / "report.json")
        self.path.write_bytes(storage._raw(self.report)); self.pin = storage._sha(self.path.read_bytes())
        with self.assertRaises(ValueError): self.checkpoint()

    def test_read_limit_cumulative_and_exact_integer_controls(self):
        with self.assertRaises(ValueError): resume.load_checkpoint(self.path, self.pin, already_decoded_bytes=True)
        with self.assertRaises(ValueError): resume.load_checkpoint(self.path, self.pin, already_decoded_bytes=1073741824)
        cp = self.checkpoint()
        self.assertEqual(cp.record()["read_ledger"]["decoded_attempt_bytes"], self.path.stat().st_size)
        with self.assertRaises(ValueError): storage.StorageLimits(max_output_bytes=2147483649)

    def test_combined_reservation_includes_old_physical_and_both_new_metadata_caps(self):
        plan = self.plan(); p = plan.record()
        self.assertEqual(p["output_reserved_bytes_before_pair_calculation"],
            2097152 + 16777216 + sum(t["byte_cap"] for t in p["remaining_tasks"]))
        self.assertEqual(p["combined_output_reserved_bytes_before_pair_calculation"],
            p["prior_storage_physical_bytes"] + p["output_reserved_bytes_before_pair_calculation"])
        hold = self.plan(limits=storage.StorageLimits(max_output_bytes=p["combined_output_reserved_bytes_before_pair_calculation"] - 1))
        with patch.object(core, "compare_block", side_effect=AssertionError("no comparison during hold")):
            with self.assertRaises(ValueError): resume.begin_continuation(hold, self.data.fixture.root / "hold")
        self.assertFalse((self.data.fixture.root / "hold").exists())

    def test_order_duplicate_foreign_and_boolean_task_rejected(self):
        run = self.begin(); remaining = resume.ledger(run)["remaining_task_ledger"]
        first = remaining[0]; task = core.BlockTask(**first["task"])
        with self.assertRaises(ValueError): resume.write_block(run, True, task)
        with self.assertRaises(ValueError): resume.write_block(run, first["group_index"], replace(task, row_start=True))
        if len(remaining) > 1:
            last = remaining[-1]
            with self.assertRaises(ValueError): resume.write_block(run, last["group_index"], core.BlockTask(**last["task"]))
        resume.write_block(run, first["group_index"], task)
        with self.assertRaises(ValueError): resume.write_block(run, first["group_index"], task)

    def test_uncomputed_prefix_partial_finish_is_not_complete(self):
        final = resume.finish(self.begin())
        self.assertTrue(final["storage_integrity_passed"])
        self.assertTrue(final["terminal_persisted"])
        self.assertFalse(final["selected_request_storage_complete"])
        self.assertEqual(final["new_summary"]["computed_pairs"], 0)
        self.assertTrue(final["unpersisted_task_ranges"])

    def test_unknown_computation_and_before_comparison_failure_are_separate(self):
        run = self.begin(); row = resume.ledger(run)["remaining_task_ledger"][0]
        with patch.object(core, "compare_block", side_effect=RuntimeError("unknown comparison")):
            result = resume.write_block(run, row["group_index"], core.BlockTask(**row["task"]))
        self.assertEqual(result["new_summary"]["unconfirmed_computation_pairs"], row["task"]["expected_pairs"])
        self.assertFalse(resume.finish(run)["selected_request_storage_complete"])

    def test_postterminal_prior_input_and_new_output_changes_revoke_completion(self):
        run = self.begin(); final = self.complete(run)
        self.assertTrue(final["selected_request_storage_complete"])
        (self.data.fixture.root / "continuation" / "foreign.txt").write_bytes(b"foreign")
        self.assertFalse(resume.ledger(run)["selected_request_storage_complete"])
        self.path.write_bytes(self.path.read_bytes() + b" ")
        later = resume.ledger(run)
        self.assertIn(str(self.path), later["changed_protected_paths"])
        self.assertFalse(later["storage_integrity_passed"])

    def test_existing_or_protected_destination_never_overwritten(self):
        plan = self.plan()
        for path in (self.root / "foreign", self.root, self.data.fixture.output):
            with self.assertRaises((ValueError, FileExistsError)): resume.begin_continuation(plan, path)

    def test_terminal_write_failure_does_not_promote(self):
        run = self.begin()
        def fail_open(path, mode="r", *args, **kwargs):
            if mode == "xb" and path.name == "report.json": raise OSError("terminal failure")
            return original(path, mode, *args, **kwargs)
        original = Path.open
        with patch.object(Path, "open", new=fail_open): final = resume.finish(run)
        self.assertFalse(final["terminal_persisted"])
        self.assertFalse(final["selected_request_storage_complete"])
        self.assertTrue(final["errors"])

    def test_finite_diagnostic_float_projection_not_music_and_nan_rejected(self):
        self.report["storage_execution"]["storage_elapsed_seconds"] = 1.125
        self.report["resource_observations"] = [{"elapsed_seconds": 2.5}]
        self.path.write_bytes(json.dumps(self.report, allow_nan=False).encode("utf-8"))
        self.pin = storage._sha(self.path.read_bytes())
        self.assertTrue(resume.plan_continuation(self.prepared, self.checkpoint()).record()["remaining_tasks"])
        self.path.write_bytes(self.path.read_bytes().replace(b"1.125", b"NaN"))
        self.pin = storage._sha(self.path.read_bytes())
        with self.assertRaises(ValueError): self.checkpoint()

    def test_complete_clean_checkpoint_requires_zero_new_comparisons(self):
        root = self.data.fixture.root / "pinned-full"; root.mkdir()
        old = storage.begin_storage(self.prepared.storage_plan, str(root / "comparison-storage"))
        for gi in range(len(request._issued(self.prepared).groups)): storage.write_prepared_group(old, gi)
        report = deepcopy(self.report); report["storage_execution"]["storage_terminal"] = storage.finish(old)
        path = root / "pilot-report.json"; path.write_bytes(storage._raw(report))
        cp = resume.load_checkpoint(path, storage._sha(path.read_bytes()))
        plan = resume.plan_continuation(self.prepared, cp)
        self.assertEqual(plan.record()["remaining_tasks"], [])
        with patch.object(core, "compare_block", side_effect=AssertionError("already computed")):
            run = resume.begin_continuation(plan, self.data.fixture.root / "empty-new")
            final = resume.finish(run)
        self.assertTrue(final["selected_request_storage_complete"])
        self.assertEqual(final["new_summary"]["computed_pairs"], 0)
        self.assertEqual(len(final["artifact_attempts"]), 2)

    def test_before_comparison_proof_failure_is_known_uncomputed(self):
        run = self.begin(); state = resume._run(run)
        first = state["tasks"][0]
        original = resume.bounds._issued; calls = [0]
        def once(proof):
            calls[0] += 1
            if calls[0] == len(state["data"].transfer_proofs) + 1:
                raise RuntimeError("before compare proof failure")
            return original(proof)
        with patch.object(resume.bounds, "_issued", side_effect=once), \
                patch.object(core, "compare_block", side_effect=AssertionError("no comparison")) as compare:
            result = resume.write_block(run, first["group_index"], core.BlockTask(**first["task"]))
            compare.assert_not_called()
        self.assertEqual(result["new_summary"]["unconfirmed_computation_pairs"], 0)
        self.assertEqual(result["remaining_task_ledger"][0]["status"], "interrupted_before_comparison")

    def test_partial_block_write_retains_computed_unpersisted(self):
        run = self.begin(); first = resume.ledger(run)["remaining_task_ledger"][0]
        original = Path.open
        class ShortWriter:
            def __init__(self, file): self.file = file
            def write(self, data): return self.file.write(data[:-1])
            def close(self): self.file.close()
        def changed(path, mode="r", *args, **kwargs):
            result = original(path, mode, *args, **kwargs)
            return ShortWriter(result) if mode == "xb" and "-block-" in path.name else result
        with patch.object(Path, "open", new=changed):
            result = resume.write_block(run, first["group_index"], core.BlockTask(**first["task"]))
        self.assertGreater(result["new_summary"]["computed_unpersisted_pairs"], 0)
        self.assertEqual(result["new_summary"]["unconfirmed_computation_pairs"], 0)
        self.assertFalse(result["artifact_attempts"][-1]["persisted"])
        self.assertGreater(result["artifact_attempts"][-1]["physical_bytes"], 0)
        self.assertFalse(resume.finish(run)["selected_request_storage_complete"])

    def test_core_held_output_not_a_completed_task(self):
        run = self.begin(); first = resume.ledger(run)["remaining_task_ledger"][0]
        task = core.BlockTask(**first["task"])
        prepared = resume._run(run)["data"].handles[first["group_index"]]
        block = core.compare_block(prepared, task)
        block = {k: v for k, v in block.items() if k not in ("record_id", "record_sha256")}
        block.update(computed_pairs=0, withheld_pairs=task.expected_pairs, pairs=[],
            reasons=["explicit mocked core hold"], status="whole_saved_block_hold")
        held = core.shared._seal(block, core.BLOCK_PREFIX)
        with patch.object(core, "compare_block", return_value=held):
            result = resume.write_block(run, first["group_index"], task)
        self.assertEqual(result["new_summary"]["held_pairs"], task.expected_pairs)
        self.assertEqual(result["new_summary"]["computed_pairs"], 0)
        self.assertFalse(resume.finish(run)["selected_request_storage_complete"])

    def test_plan_guard_change_precedes_new_output(self):
        plan = self.plan()
        self.path.write_bytes(self.path.read_bytes() + b" ")
        destination = self.data.fixture.root / "changed-input"
        with self.assertRaises(ValueError): resume.begin_continuation(plan, destination)
        self.assertFalse(destination.exists())

    def test_manifest_and_inventory_tightening_hold_before_comparison(self):
        hold = self.plan(limits=storage.StorageLimits(max_manifest_bytes=2048))
        self.assertIn("whole_continuation_manifest_byte_hold", hold.record()["reasons"])
        with self.assertRaises(ValueError): resume.begin_continuation(hold, self.data.fixture.root / "tiny-manifest")
        with self.assertRaises(ValueError): self.plan(limits=storage.StorageLimits(max_groups=0))

    def test_boolean_prior_computed_count_cannot_impersonate_integer(self):
        self.report["storage_execution"]["storage_terminal"]["groups"][0]["task_ledger"][0]["computed_pairs"] = True
        self.path.write_bytes(storage._raw(self.report)); self.pin = storage._sha(self.path.read_bytes())
        with self.assertRaises(ValueError): self.plan()


if __name__ == "__main__": unittest.main()
