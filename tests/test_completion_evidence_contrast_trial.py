"""Pinned gzip and source-binding controls, not historical admission."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

from musicanote_harness import completion_evidence_contrast_trial as trial
from musicanote_harness.progression_evidence_review_trial import ReviewLimits
from musicanote_harness import factor_expanded_hypotheses as sealed
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import shared_source_progression_contrast as shared
from musicanote_harness import progression_evidence_review as review
from musicanote_harness import native_progression_contrast as parent
from musicanote_harness import source_progression_replay_trial as replay
from musicanote_harness.musical_pattern_observation import digest
import test_native_progression_contrast as genuine


class CompletionReaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def record(self, raw=None):
        record = {"status": "test_fixture", "payload": "x" * 100}
        record = sealed._seal(record, "fixture_")
        raw = json.dumps(record).encode() if raw is None else raw
        p = self.root / "record.json.gz"
        p.write_bytes(gzip.compress(raw, mtime=0))
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        info = {"artifact": str(p), "sha256": sha, "record_ref": sealed._ref(record), "status": record["status"]}
        return info, {str(p): sha}, record, len(raw)

    def test_gzip_pins_decoded_cost_and_final_guard(self):
        info, registry, record, n = self.record()
        reader = trial.Reader(ReviewLimits())
        self.assertEqual(reader.record(info, "fixture_", registry, self.root), record)
        self.assertEqual(reader.bytes, n)
        self.assertEqual(reader.ledger[0]["decoded_bytes"], n)
        reader.final_guard()

    def test_physical_pin_or_foreign_root_rejected(self):
        info, registry, _, _ = self.record()
        registry[info["artifact"]] = "0" * 64
        with self.assertRaises(ValueError):
            trial.Reader(ReviewLimits()).record(info, "fixture_", registry, self.root)
        info, registry, _, _ = self.record()
        with self.assertRaises(ValueError):
            trial.Reader(ReviewLimits()).record(info, "fixture_", registry, self.root / "foreign")

    def test_decoded_not_compressed_size_controls_budget(self):
        info, registry, _, n = self.record()
        reader = trial.Reader(ReviewLimits(max_total_decoded_bytes=n - 1))
        with self.assertRaisesRegex(ValueError, "decoded_archive_read_limit"):
            reader.record(info, "fixture_", registry, self.root)
        self.assertGreaterEqual(reader.bytes, n)
        self.assertEqual(reader.ledger, [])

    def test_one_account_across_repeated_gzip_reads(self):
        info, registry, _, n = self.record()
        reader = trial.Reader(ReviewLimits(max_total_decoded_bytes=n))
        reader.record(info, "fixture_", registry, self.root)
        with self.assertRaises(ValueError):
            reader.record(info, "fixture_", registry, self.root)

    def test_duplicate_and_nonfinite_json_not_accepted(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            info, registry, _, _ = self.record(raw)
            with self.assertRaises(ValueError):
                trial.Reader(ReviewLimits()).record(info, "fixture_", registry, self.root)

    def test_changed_compressed_input_invalidates_terminal(self):
        info, registry, _, _ = self.record()
        reader = trial.Reader(ReviewLimits())
        reader.record(info, "fixture_", registry, self.root)
        Path(info["artifact"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            reader.final_guard()

    def test_source_index_bool_and_wrong_binding_rejected(self):
        scope = {"record_id": "scope", "record_sha256": "a" * 64}
        lattice = {"record_id": "lattice", "record_sha256": "b" * 64}
        with self.assertRaises(ValueError):
            trial._index([], scope, lattice, True)
        row = {"error": None, "scope": {"record_ref": sealed._ref(lattice)}}
        with self.assertRaises(ValueError):
            trial._index([row], scope, lattice, 0)


class CompletionRunnerTests(unittest.TestCase):
    """Genuine XML bodies/physical files; receipt ancestry is SYNTHETIC."""
    @classmethod
    def setUpClass(cls):
        genuine.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(genuine.SavedProgressionContrastTests.doClassCleanups)
        cls.factory = genuine.SavedProgressionContrastTests()
        fixture = cls.factory.fixture
        cls.scope = fixture.case("passing")[0][1]
        cls.lattice = fixture.record("passing")
        cls.inputs = []
        for control in (True, False):
            session, comparison, bundle = fixture.comparison("passing", control=control,
                max_hypotheses=16, max_slots=3, query_work_budget=2000000)
            explanation = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
            cls.inputs.append((comparison, explanation, bundle))
        bundles = {b["record_id"]: b for _, _, b in cls.inputs}
        cls.source = shared.prepare_saved_source(cls.scope, cls.lattice, bundles=bundles).export_source()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.archive, self.prior, self.control = (self.root / n for n in ("archive", "prior", "control"))
        for p in (self.archive, self.prior / "comparison-storage", self.control):
            p.mkdir(parents=True)
        self.registry = {}

    def json(self, p, body):
        raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        p.write_bytes(raw)
        return {"path": str(p), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def record(self, name, body):
        p = self.archive / (name + ".json.gz")
        raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        p.write_bytes(gzip.compress(raw, mtime=0))
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        self.registry[str(p)] = sha
        return {"artifact": str(p), "sha256": sha, "record_ref": sealed._ref(body), "status": body["status"]}

    def prepare(self, mutation=None):
        comparison, explanation, bundle = deepcopy(self.inputs[1])
        settings = {"batch_size": 16, "max_slots": 3, "native_query_work_budget": 2000000,
                    "role_query_work_budget": 100000000}
        selectors = comparison["selectors"]
        plan = sealed._seal({"status": "ready_native_role_batches", "planned_selectors": 1,
            "planned_batches": 1, "reasons": [], "resource_limits": settings,
            "proposal_ref": {"record_id": "fixture_proposal", "record_sha256": "a" * 64},
            "selector_inventory_sha256": digest(selectors)}, "npsreplayplan_")
        batch = {"batch_index": 0, "selector_start": 0, "selector_end_exclusive": 1,
            "charged_native_comparisons": 2,
            "native_query_work": comparison["query_plan"]["planned_query_work"],
            "role_query_work": explanation["query_plan"]["planned_query_work"]}
        batch["charged_work"] = 2 * batch["native_query_work"] + batch["role_query_work"]
        batch["comparison"] = self.record("comparison", comparison)
        batch["explanation"] = self.record("explanation", explanation)
        counts = replay._empty_counts(1, 1)
        counts["fresh_bundle_registrations"] = 1
        replay._add_batch(counts, comparison, explanation, bundle)
        replay._finish_counts(counts)
        refs = [{**{k: batch[k] for k in replay.PLAN_BATCH_KEYS},
                 "comparison_ref": sealed._ref(comparison), "explanation_ref": sealed._ref(explanation)}]
        terminal = sealed._seal({"status": "computed_native_role_source_requests_not_selected", "reasons": [],
            "bundle_ref": sealed._ref(bundle), "scope_ref": sealed._ref(self.scope),
            "lattice_ref": sealed._ref(self.lattice), "plan_ref": sealed._ref(plan),
            "proposal_ref": plan["proposal_ref"], "fresh_registered_links": bundle["materialized_witness_links"],
            "batch_refs": refs, "summary": counts, "selected": None, "rank": None,
            "confidence": None, "flags": parent._flags()}, replay.engine.PREFIX)
        job = {"status": terminal["status"], "error": None, "unpersisted_selector_ranges": [],
            "planned_selector_occurrences": 1, "completion_kind": "genuine_link_fixture",
            "bundle": self.record("bundle", bundle), "plan": self.record("plan", plan),
            "job": self.record("terminal", terminal), "batches": [batch], "summary": counts}
        context = {"error": None, "scope": {"record_ref": sealed._ref(self.scope)},
            "fresh_lattice": {"record_ref": sealed._ref(self.lattice)}, "context_key": ["synthetic_receipt_ancestry"],
            "jobs": [job]}
        if mutation:
            mutation(job)
        index = self.json(self.archive / "context-index.json", [context])
        self.registry[index["path"]] = index["sha256"]
        cp, ce, cb = self.inputs[0]
        entry = {"native_path": cp["paths"][0], "role_path": ce["paths"][0],
                 "comparison_ref": sealed._ref(cp), "explanation_ref": sealed._ref(ce)}
        origins = {o["record_id"]: o for c in self.lattice["catalog_inventory"] for o in c["origins"]}
        sounds = {s["sound_ref"]: s for s in self.scope["sound_facts"]}
        facet = parent._facet(entry, self.scope, [origins[i] for i in selectors[0]["origin_ids"]], sounds)
        key = next(k for k in self.lattice["keys"] if k["record_id"] == facet["key_ref"]["record_id"])
        row = review.review_facet(facet, key)
        row["original_selector_index"] = 0
        catalog_ref = {"record_id": "control_fixture", "record_sha256": "b" * 64}
        artifact = self.json(self.control / "group.json", {"source_catalog_ref": sealed._ref(self.source),
            "catalog_ref": catalog_ref, "candidate_reviews": [row]})
        control_report = {"physical_inputs_unchanged": True, "role_predicates_reinferred": False,
            "selected": None, "rank": None, "confidence": None, "flags": parent._flags(),
            "summary": {"reviewed_candidates": 1}, "selected_completion": {"completion_requests": 1},
            "groups": [{"review_file": "group.json", "catalog_ref": catalog_ref}], "artifacts": [artifact]}
        self.cp = self.json(self.control / "report.json", control_report)
        self.sp = self.json(self.prior / "comparison-storage" / "source.json", self.source)
        receipt = {"storage_execution": {"storage_terminal": {"selected_request_storage_complete": True},
            "plan": {"protected_roots": [{"directory": str(self.archive), "registered_sha256": self.registry},
                {"directory": str(self.prior), "registered_sha256": {self.sp["path"]: self.sp["sha256"]}}]}}}
        self.rp = self.json(self.root / "receipt.json", receipt)
        # Disjoint output cannot be inside the receipt directory itself.
        receipt_dir = self.root / "receipt"
        receipt_dir.mkdir()
        moved = receipt_dir / "report.json"
        Path(self.rp["path"]).replace(moved)
        self.rp["path"] = str(moved)

    def run_fixture(self, output=None, **kwargs):
        return trial.run(self.rp["path"], self.cp["path"], self.archive, self.sp["path"],
            self.root / "result" if output is None else output,
            receipt_sha256=self.rp["sha256"], control_sha256=self.cp["sha256"],
            source_index=0, completion_index=0, **kwargs)

    def test_all_genuine_body_positions_persisted_without_producers(self):
        self.prepare()
        with patch.object(native, "compare_prepared", side_effect=AssertionError("replay")), \
             patch.object(roles, "explain_prepared", side_effect=AssertionError("replay")):
            result = self.run_fixture()
        self.assertEqual(result["summary"]["paired_original_candidates"], 1)
        self.assertEqual(result["completed_batches"], 1)
        self.assertFalse(result["saved_JSON_restores_capability"])
        self.assertTrue((self.root / "result" / "report.json").is_file())

    def test_missing_original_batch_not_successful_prefix(self):
        self.prepare(lambda j: j.update(batches=[]))
        with self.assertRaisesRegex(ValueError, "request_plan_terminal"):
            self.run_fixture()
        self.assertFalse((self.root / "result").exists())

    def test_wrong_original_batch_ordinal_rejected(self):
        self.prepare(lambda j: j["batches"][0].update(selector_start=1))
        with self.assertRaisesRegex(ValueError, "batch_order"):
            self.run_fixture()
        self.assertFalse((self.root / "result" / "report.json").exists())

    def test_existing_output_never_overwritten(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "new_disjoint"):
            self.run_fixture(self.control)

    def test_lowered_read_budget_no_success_report(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.run_fixture(limits=ReviewLimits(max_total_decoded_bytes=1))
        self.assertFalse((self.root / "result").exists())

    def test_lowered_output_budget_no_success_report(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "output_limit"):
            self.run_fixture(limits=ReviewLimits(max_total_output_bytes=1))
        self.assertFalse((self.root / "result" / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
