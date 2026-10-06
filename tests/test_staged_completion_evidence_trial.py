"""Genuine small XML/native bodies, explicitly SYNTHETIC receipt ancestry."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import staged_completion_evidence_trial as trial
from musicanote_harness import factor_expanded_hypotheses as sealed
from musicanote_harness import native_progression_contrast as parent
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import source_progression_replay_trial as replay
from musicanote_harness.musical_pattern_observation import digest
from musicanote_harness.progression_evidence_review_trial import ReviewLimits, _hash
import test_completion_evidence_contrast_trial as fixtures


class StagedTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.CompletionRunnerTests.setUpClass()
        cls.addClassCleanup(fixtures.CompletionRunnerTests.doClassCleanups)
        cls.fixture = fixtures.CompletionRunnerTests

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.archive = self.root / "archive"
        self.archive.mkdir()
        self.registry = {}

    def record(self, name, body):
        p = self.archive / (name + ".json.gz")
        p.write_bytes(gzip.compress(json.dumps(body, sort_keys=True, separators=(",", ":")).encode(), mtime=0))
        sha = _hash(p)
        self.registry[str(p)] = sha
        return {"artifact": str(p), "sha256": sha, "record_ref": sealed._ref(body), "status": body["status"]}

    def prepare(self, mutation=None):
        scope = self.record("scope", self.fixture.scope)
        lattice = self.record("lattice", self.fixture.lattice)
        jobs = []
        for i, (comparison, explanation, bundle) in enumerate(self.fixture.inputs):
            batch = {"batch_index": 0, "selector_start": 0, "selector_end_exclusive": 1,
                "charged_native_comparisons": 2, "native_query_work": comparison["query_plan"]["planned_query_work"],
                "role_query_work": explanation["query_plan"]["planned_query_work"]}
            batch["charged_work"] = 2 * batch["native_query_work"] + batch["role_query_work"]
            settings = {"batch_size": 16, "max_slots": 3, "native_query_work_budget": 2000000,
                        "role_query_work_budget": 100000000}
            plan = sealed._seal({"status": "ready_native_role_batches", "planned_selectors": 1,
                "planned_batches": 1, "batches": [deepcopy(batch)], "reasons": [], "resource_limits": settings,
                "scope_ref": sealed._ref(self.fixture.scope), "lattice_ref": sealed._ref(self.fixture.lattice),
                "proposal_ref": {"record_id": "synthetic", "record_sha256": "a" * 64},
                "selector_inventory_sha256": digest(comparison["selectors"])}, "npsreplayplan_")
            batch["comparison"] = self.record(f"comparison-{i}", comparison)
            batch["explanation"] = self.record(f"explanation-{i}", explanation)
            counts = replay._empty_counts(1, 1)
            counts["fresh_bundle_registrations"] = 1
            replay._add_batch(counts, comparison, explanation, bundle)
            replay._finish_counts(counts)
            refs = [{**{k: batch[k] for k in replay.PLAN_BATCH_KEYS},
                     "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)}]
            terminal = sealed._seal({"status": "computed_native_role_source_requests_not_selected", "reasons": [],
                "bundle_ref": sealed._ref(bundle), "scope_ref": sealed._ref(self.fixture.scope),
                "lattice_ref": sealed._ref(self.fixture.lattice), "plan_ref": sealed._ref(plan),
                "proposal_ref": plan["proposal_ref"], "fresh_registered_links": bundle["materialized_witness_links"],
                "batch_refs": refs, "summary": counts, "selected": None, "rank": None, "confidence": None,
                "flags": parent._flags()}, replay.engine.PREFIX)
            jobs.append({"status": terminal["status"], "error": None, "unpersisted_selector_ranges": [],
                "planned_selector_occurrences": 1, "completion_kind": "synthetic_fixture",
                "bundle": self.record(f"bundle-{i}", bundle), "plan": self.record(f"plan-{i}", plan),
                "job": self.record(f"terminal-{i}", terminal), "batches": [batch], "summary": counts})
        if mutation:
            mutation(jobs)
        context = {"error": None, "scope": scope, "fresh_lattice": lattice,
                   "context_key": ["synthetic_ancestry_not_historical_admission"], "jobs": jobs}
        index = self.archive / "context-index.json"
        index.write_text(json.dumps([context]), encoding="utf-8")
        self.registry[str(index)] = _hash(index)
        rd = self.root / "receipt"
        rd.mkdir()
        self.receipt = rd / "report.json"
        self.receipt.write_text(json.dumps({"storage_execution": {"plan": {"protected_roots": [
            {"directory": str(self.archive), "registered_sha256": self.registry}]}}}), encoding="utf-8")
        self.scope_sha = scope["sha256"]

    def run_fixture(self, **kwargs):
        return trial.run(self.receipt, self.archive, self.root / "result",
            receipt_sha256=_hash(self.receipt), scope_sha256=self.scope_sha, source_index=0, **kwargs)

    def test_all_requests_saved_without_producer_calls(self):
        self.prepare()
        with patch.object(native, "compare_prepared", side_effect=AssertionError("replay")), \
             patch.object(roles, "explain_prepared", side_effect=AssertionError("replay")):
            result = self.run_fixture()
        self.assertEqual(result["summary"]["paired_original_candidates"], 1)
        self.assertEqual([s["stage"] for s in result["stage_accounts"]], ["bootstrap", "control", "linked", "paired"])
        self.assertFalse(result["pipeline_claimed_to_fit_single_read_account"])
        self.assertFalse(result["independent_musical_accuracy_measured"])
        self.assertTrue(all(v is False for v in result["flags"].values()))
        self.assertEqual(result["archived_native_role_summaries"]["control"]["raw_time_conserved_native_paths"], 1)

    def test_no_prefix_if_original_batch_missing(self):
        self.prepare(lambda jobs: jobs[1].update(batches=[]))
        with self.assertRaisesRegex(ValueError, "complete_original"):
            self.run_fixture()
        self.assertFalse((self.root / "result").exists())

    def test_source_pin_not_self_declared_authority(self):
        self.prepare()
        self.scope_sha = "0" * 64
        with self.assertRaisesRegex(ValueError, "external_scope_pin"):
            self.run_fixture()

    def test_changed_earlier_stage_input_prevents_whole_terminal(self):
        self.prepare()
        def change_after_pair(message):
            if message.startswith("paired:"):
                (self.archive / "comparison-0.json.gz").write_bytes(b"changed after control stage")
        with self.assertRaisesRegex(ValueError, "earlier_stage_input_changed"):
            self.run_fixture(progress=change_after_pair)
        self.assertFalse((self.root / "result" / "report.json").exists())

    def test_noncontiguous_original_plan_is_not_a_shorter_success(self):
        self.prepare(lambda jobs: jobs[1]["batches"][0].update(selector_start=1))
        with self.assertRaisesRegex(ValueError, "whole_original_batch_order"):
            self.run_fixture()
        self.assertFalse((self.root / "result").exists())

    def test_same_completion_not_compared(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "no_link_control"):
            self.run_fixture(linked_index=0)

    def test_bool_source_index_rejected(self):
        self.prepare()
        with self.assertRaises(ValueError):
            trial.run(self.receipt, self.archive, self.root / "result", receipt_sha256=_hash(self.receipt),
                      scope_sha256=self.scope_sha, source_index=True)

    def test_existing_output_is_not_overwritten(self):
        self.prepare()
        (self.root / "result").mkdir()
        with self.assertRaisesRegex(ValueError, "new_disjoint"):
            self.run_fixture()

    def test_output_and_read_budgets_fail_without_terminal(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.run_fixture(limits=ReviewLimits(max_total_decoded_bytes=1))
        with self.assertRaisesRegex(ValueError, "output_physical_limit"):
            self.run_fixture(limits=ReviewLimits(max_total_output_bytes=1))
        self.assertFalse((self.root / "result" / "report.json").exists())

    def test_original_position_and_length_required(self):
        ref = {"record_id": "scope", "record_sha256": "a" * 64}
        left = {"source_scope_ref": ref, "batch_index": 0, "selector_start": 0,
                "selector_end_exclusive": 1, "rows": []}
        with self.assertRaisesRegex(ValueError, "every_original_pair"):
            trial._pair_batches(left, deepcopy(left), {}, {})
        left["rows"] = [{"original_selector_index": 1}]
        with self.assertRaisesRegex(ValueError, "exact_original_pair_position"):
            trial._pair_batches(left, deepcopy(left), {}, {})

    def test_gzip_snapshot_has_cumulative_decoded_account(self):
        output = self.root / "snapshots"
        output.mkdir()
        artifact = trial.Writer(output, ReviewLimits()).save("sample.json.gz", {"large": "x" * 10000})
        reader = trial.Reader(ReviewLimits(max_total_decoded_bytes=artifact["decoded_bytes"]))
        self.assertEqual(reader.snapshot(artifact), {"large": "x" * 10000})
        with self.assertRaisesRegex(ValueError, "stage_decoded_read_limit"):
            reader.snapshot(artifact)

    def test_snapshot_decoded_length_and_final_physical_guard(self):
        output = self.root / "snapshots"
        output.mkdir()
        artifact = trial.Writer(output, ReviewLimits()).save("sample.json.gz", {"x": 1})
        wrong = {**artifact, "decoded_bytes": artifact["decoded_bytes"] + 1}
        with self.assertRaisesRegex(ValueError, "decoded_length_mismatch"):
            trial.Reader(ReviewLimits()).snapshot(wrong)
        reader = trial.Reader(ReviewLimits())
        reader.snapshot(artifact)
        Path(artifact["path"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            reader.final_guard()

    def test_source_snapshot_uses_explicit_source_not_generic_file_cap(self):
        output = self.root / "snapshots"
        output.mkdir()
        artifact = trial.Writer(output, ReviewLimits()).save("source.json.gz", {"x": "x" * 10000})
        limits = ReviewLimits(max_json_file_bytes=1024)
        with self.assertRaisesRegex(ValueError, "stage_decoded_read_limit"):
            trial.Reader(limits).snapshot(artifact)
        self.assertEqual(trial.Reader(limits).snapshot(artifact, source=True), {"x": "x" * 10000})

    def test_writer_cannot_escape_output_directory(self):
        with self.assertRaisesRegex(ValueError, "plain_output_filename"):
            trial.Writer(self.root, ReviewLimits()).save("../outside.json.gz", {})


if __name__ == "__main__":
    unittest.main()
