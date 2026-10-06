"""Bounded pinned reader controls; not musical or historical admission tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from musicanote_harness.progression_evidence_review_trial import Reader, ReviewLimits, run
from dataclasses import asdict
import test_progression_evidence_review as genuine_factory


class ReviewReaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def file(self, value=b'{"ok":true}'):
        path = self.root / "input.json"
        path.write_bytes(value)
        return path, hashlib.sha256(value).hexdigest()

    def test_exact_pin_and_read_ledger(self):
        path, sha = self.file()
        reader = Reader(ReviewLimits())
        self.assertEqual(reader.read(path, sha), {"ok": True})
        self.assertEqual(reader.bytes, path.stat().st_size)
        reader.final_guard()

    def test_wrong_pin_and_length(self):
        path, sha = self.file()
        for checksum, length in (("0" * 64, None), (sha, 1)):
            with self.assertRaises(ValueError):
                Reader(ReviewLimits()).read(path, checksum, length)

    def test_per_file_and_cumulative_cap(self):
        path, sha = self.file()
        with self.assertRaises(ValueError):
            Reader(ReviewLimits(max_json_file_bytes=1)).read(path, sha)
        reader = Reader(ReviewLimits(max_total_decoded_bytes=path.stat().st_size))
        reader.read(path, sha)
        with self.assertRaises(ValueError):
            reader.read(path, sha)

    def test_source_uses_separate_existing_source_cap(self):
        path, sha = self.file()
        reader = Reader(ReviewLimits(max_json_file_bytes=1))
        self.assertEqual(reader.read(path, sha, source=True), {"ok": True})

    def test_changed_input_invalidates_terminal(self):
        path, sha = self.file()
        reader = Reader(ReviewLimits())
        reader.read(path, sha)
        path.write_bytes(b'{"ok":null}')
        with self.assertRaises(ValueError):
            reader.final_guard()

    def test_duplicate_or_nonfinite_JSON_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            path, sha = self.file(raw)
            with self.assertRaises(ValueError):
                Reader(ReviewLimits()).read(path, sha)

    def test_bool_float_negative_and_raised_limits_rejected(self):
        for value in (True, 1.5, -1, 67108865):
            with self.assertRaises(ValueError):
                ReviewLimits(max_json_file_bytes=value)

    def test_existing_output_rejected_before_read(self):
        path, sha = self.file()
        with self.assertRaises(ValueError):
            run(path, path, self.root, prior_sha256=sha, continuation_sha256=sha)


class ReviewSavedRunnerTests(unittest.TestCase):
    """Genuine music/physical files, explicitly synthetic receipt ancestry."""
    @classmethod
    def setUpClass(cls):
        genuine_factory.EvidenceReviewTests.setUpClass()
        cls.addClassCleanup(genuine_factory.EvidenceReviewTests.doClassCleanups)
        cls.fixture = genuine_factory.EvidenceReviewTests()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def archive(self, mutate=None):
        source, catalog, blocks = self.fixture.packet()
        old = self.root / "prior"
        new = self.root / "continuation"
        storage = old / "comparison-storage"
        storage.mkdir(parents=True)
        (new / "comparison-storage").mkdir(parents=True)
        attempts = []
        def save(p, body):
            raw = json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
            p.write_bytes(raw)
            return len(raw), hashlib.sha256(raw).hexdigest()
        for name, kind, body in (("source-0000-catalog.json", "source_catalog", source),
                ("group-0000-catalog.json", "local_catalog", catalog),
                ("group-0000-block-000000.json", "block", blocks[0][1])):
            p = storage / name
            size, sha = save(p, body)
            attempts.append({"artifact": str(p), "kind": kind, "persisted": True,
                "stream_complete": True, "physical_bytes": size, "attempted_bytes": size,
                "physical_sha256": sha, "attempted_sha256": sha})
        task = blocks[0][0]
        a = attempts[-1]
        task_row = {"group_index": 0, "task_index": 0, "task": task, "status": "computed_persisted",
            "persisted_pairs": task["expected_pairs"], "encoded_bytes": a["physical_bytes"],
            "encoded_sha256": a["physical_sha256"]}
        prior = {"storage_execution": {"storage_terminal": {"storage_integrity_passed": True,
            "terminal_persisted": True, "physical_closure_verified_terminally": True,
            "artifact_attempts": attempts}}}
        pp = old / "pilot-report.json"
        _, ps = save(pp, prior)
        current = {"storage_execution": {"plan": {"prior_receipt_external_SHA": ps,
            "prior_receipt_path": str(pp), "groups": [{"catalog_ref": {k: catalog[k] for k in ("record_id", "record_sha256")},
                "source_index": 0, "tasks": [task], "original": {"planned_entries": 2,
                "selector_indices": catalog["group"]["original_selector_indices"], "planned_pairs": 1}}],
            "prior_confirmed_tasks": [task_row], "original_denominators": {"synthetic_fixture": True},
            "whole_original": {"planned_pairs": 1}, "selected_completion": {"planned_pairs": 1},
            "omitted_completions": {"planned_pairs": 0}},
            "storage_terminal": {"storage_integrity_passed": True, "terminal_persisted": True,
                "physical_closure_verified_terminally": True, "selected_request_storage_complete": True,
                "remaining_task_ledger": [], "artifact_attempts": []}}}
        if mutate:
            mutate(current)
        cp = new / "pilot-report.json"
        _, cs = save(cp, current)
        return pp, cp, ps, cs

    def execute(self, files, **options):
        pp, cp, ps, cs = files
        return run(pp, cp, self.root / "review", prior_sha256=ps, continuation_sha256=cs, **options)

    def test_complete_physical_saved_review_end_to_end(self):
        result = self.execute(self.archive())
        self.assertEqual(result["audited_pairs"], 1)
        self.assertEqual(result["summary"]["reviewed_candidates"], 2)
        self.assertFalse(result["saved_JSON_restores_capability"])
        self.assertFalse(result["independent_musical_accuracy_measured"])
        self.assertTrue((self.root / "review" / "source-context.json").exists())
        self.assertTrue((self.root / "review" / "report.json").exists())

    def test_receipt_chain_pin_mismatch(self):
        files = self.archive(lambda c: c["storage_execution"]["plan"].update(prior_receipt_external_SHA="0" * 64))
        with self.assertRaises(ValueError):
            self.execute(files)
        self.assertFalse((self.root / "review").exists())

    def test_incomplete_selected_scope_rejected(self):
        files = self.archive(lambda c: c["storage_execution"]["storage_terminal"].update(selected_request_storage_complete=False))
        with self.assertRaises(ValueError):
            self.execute(files)

    def test_missing_task_rejected_no_successful_prefix(self):
        files = self.archive(lambda c: c["storage_execution"]["plan"].update(prior_confirmed_tasks=[]))
        with self.assertRaises(ValueError):
            self.execute(files)
        self.assertFalse((self.root / "review").exists())

    def test_changed_catalog_rejected(self):
        files = self.archive()
        p = self.root / "prior" / "comparison-storage" / "group-0000-catalog.json"
        p.write_bytes(p.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.execute(files)
        self.assertFalse((self.root / "review" / "report.json").exists())

    def test_whole_read_budget_preflight_before_review_output(self):
        files = self.archive()
        size = sum(p.stat().st_size for p in files[:2])
        with self.assertRaises(ValueError):
            self.execute(files, limits=ReviewLimits(max_total_decoded_bytes=size))
        self.assertFalse((self.root / "review").exists())


if __name__ == "__main__":
    unittest.main()
