"""Genuine XML-derived reviews, SYNTHETIC parent receipt ancestry only."""
from copy import deepcopy
from dataclasses import replace
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_candidate_obligation_trial as trial
from musicanote_harness import staged_completion_evidence_trial as storage
from musicanote_harness import factor_expanded_hypotheses as sealed
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import progression_evidence_review_trial as saved
import test_harmony_candidate_obligation_policy as fixtures


class ObligationTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ObligationPolicyTests.setUpClass()
        cls.addClassCleanup(fixtures.ObligationPolicyTests.doClassCleanups)
        cls.fixture = fixtures.ObligationPolicyTests()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def prepare(self, mutate=None):
        archive = self.root / "parent"
        archive.mkdir()
        writer = storage.Writer(archive, saved.ReviewLimits())
        rows, scope, bundles = self.fixture.packet()
        controls, _, cb = self.fixture.packet(control=True)
        bundles = {**bundles, **cb}
        keys = self.fixture.fixture.fixture.record("ordinary")["keys"]
        source = {"scope": scope, "bundles": bundles, "lattice": {"keys": keys}, "plans": {}, "terminals": {}}
        batches = {}
        for label, records in (("linked", rows), ("control", controls)):
            plan = sealed._seal({"planned_selectors": 2, "planned_batches": 1, "reasons": [],
                "scope_ref": sealed._ref(scope), "batches": [{"selector_start": 0, "selector_end_exclusive": 2}]}, "npsreplayplan_")
            terminal = sealed._seal({"plan_ref": sealed._ref(plan), "scope_ref": sealed._ref(scope),
                "bundle_ref": records[0]["review"]["bundle_ref"], "reasons": []}, "npsreplayjob_")
            source["plans"][label], source["terminals"][label] = plan, terminal
            batches[label] = {"rows": records, "source_scope_ref": sealed._ref(scope),
                "bundle_ref": terminal["bundle_ref"], "batch_index": 0, "selector_start": 0, "selector_end_exclusive": 2}
        if mutate:
            mutate(source, batches)
        writer.save("source-context.json.gz", source, source=True)
        for label, batch in batches.items():
            writer.save(label+"-0000.json.gz", batch)
        report = {"status": "complete_staged_saved_evidence_review_not_selected", "full_archive_complete": False,
            "physical_inputs_unchanged": True, "selected": None, "rank": None, "confidence": None,
            "summary": {"paired_original_candidates": 2}, "artifacts": writer.artifacts.copy()}
        self.report = archive / "report.json"
        writer.save("report.json", report, compress=False)
        self.pin = saved._hash(self.report)
        self.output = self.root / "out"

    def run_fixture(self, **kwargs):
        return trial.run(self.report, self.output, report_sha256=self.pin, **kwargs)

    def test_complete_both_inventory_no_native_replay(self):
        self.prepare()
        with patch.object(native, "compare_prepared", side_effect=AssertionError("replay")), \
             patch.object(roles, "explain_prepared", side_effect=AssertionError("replay")):
            result = self.run_fixture()
        self.assertEqual(result["complete_candidates_per_completion"], 2)
        self.assertEqual(result["completion_summaries"]["linked"]["computed_exact_extension_pairs"], 1)
        self.assertEqual(set(result["completion_summaries"]), {"linked", "control"})
        self.assertFalse(result["musical_accuracy_measured"])
        self.assertTrue((self.output/"report.json").exists())

    def test_external_pin_not_self_declared(self):
        self.prepare(); self.pin = "0"*64
        with self.assertRaises(ValueError):
            self.run_fixture()
        self.assertFalse(self.output.exists())

    def test_missing_row_cannot_be_shorter_success(self):
        self.prepare(lambda source, batches: batches["linked"]["rows"].pop())
        with self.assertRaisesRegex(ValueError, "position_source_bundle"):
            self.run_fixture()
        self.assertFalse((self.output/"report.json").exists())

    def test_foreign_source_reference_rejected(self):
        self.prepare(lambda source, batches: batches["linked"]["source_scope_ref"].update(record_sha256="0"*64))
        with self.assertRaises(ValueError):
            self.run_fixture()
        self.assertFalse((self.output/"report.json").exists())

    def test_key_coordinate_not_inferred_from_successful_motion(self):
        self.prepare(lambda source, batches: batches["linked"]["rows"][0]["review"].update(key_coordinate_available=False))
        with self.assertRaisesRegex(ValueError, "original_key"):
            self.run_fixture()

    def test_lowered_read_and_output_limits_no_terminal(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.run_fixture(limits=replace(saved.ReviewLimits(), max_total_decoded_bytes=1))
        with self.assertRaises(ValueError):
            self.run_fixture(limits=replace(saved.ReviewLimits(), max_total_output_bytes=1))
        self.assertFalse((self.output/"report.json").exists())

    def test_earlier_input_changed_blocks_final_report(self):
        self.prepare()
        def change_after_control(message):
            if message.startswith("control: {"):
                (self.report.parent/"control-0000.json.gz").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "input_changed_after_read"):
            self.run_fixture(progress=change_after_control)
        self.assertFalse((self.output/"report.json").exists())

    def test_existing_output_not_overwritten(self):
        self.prepare(); self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "new_obligation_output"):
            self.run_fixture()


if __name__ == "__main__":
    unittest.main()
