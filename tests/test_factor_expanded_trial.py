"""An explicit new envelope never mutates its historical comparison parents."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_expanded_trial as trial
from musicanote_harness import factor_musical_trial as storage
import test_factor_context_prerequisite_trial as prerequisite_fixture
from test_harmony_frozen_context_voice_trial import read_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyExpandedGuardTests(unittest.TestCase):
    def test_output_and_limits_are_checked_before_parent_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/old"
            old.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), patch.object(trial, "load_inputs", side_effect=AssertionError("read")):
                for destination in (root, old, root / "output/nested/child"):
                    with self.subTest(destination=destination), self.assertRaises(ValueError):
                        trial.run("absent", destination)
                for name in ("max_events", "max_factors", "max_edges", "max_catalogs", "path_budget",
                             "pair_budget", "overlay_pair_budget", "max_motion_pairs"):
                    for value in (True, -1, 1.5):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("absent", root / "output/new", **{name: value})
                with self.assertRaises(ValueError):
                    trial.run("absent", root / "output/new", path_budget=0)


class ExpandedTrialTests(unittest.TestCase):
    def setUp(self):
        fixture = prerequisite_fixture.ContextPrerequisiteTrialTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        report = fixture.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.prerequisites = fixture.output
        self.output = self.root / "output/expanded"
        patched = patch.object(trial, "ROOT", self.root)
        patched.start()
        self.addCleanup(patched.stop)

    def execute(self, **kwargs):
        options = {"max_catalogs": 0, **kwargs}
        with redirect_stdout(io.StringIO()):
            return trial.run(self.prerequisites, self.output, **options)

    def refresh_parent(self):
        path = self.prerequisites / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def test_parent_inventory_and_hashes_preserved_with_new_typed_scope(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertFalse(report["cohort_complete"])
        self.assertIsNone(report["selected"])
        for name in ("harmony_confirmed", "cadence_confirmed", "musical_accuracy_measured", "training_eligible",
                     "gold_eligible", "generation_ready", "source_labels_used_for_inference", "old_paths_or_bundles_extended"):
            self.assertIs(report[name], False)
        old = read_json(self.prerequisites / "context-index.json")
        rows = read_json(self.output / "context-index.json")
        self.assertEqual([r["context_key"] for r in rows], [r["context_key"] for r in old])
        for row, original in zip(rows, old):
            self.assertEqual(row["old_view_ref"], original["view_ref"])
            self.assertEqual(row["old_groups"], original["groups"])
            self.assertEqual([r["lane"] for r in row["old_lane_refs"]], [r["lane"] for r in original["lane_inventory"]])
            scope = read_gzip(row["expanded_scope"]["artifact"])
            self.assertTrue(scope["record_id"].startswith("fmes_"))
            self.assertEqual(scope["anchor_span"], row["old_context_span"])
            self.assertEqual(scope["analysis_span"], row["analysis_span"])
            self.assertIsNotNone(row["hypotheses"])
            self.assertIsNotNone(row["assessment"])
        for p, content in before.items():
            self.assertEqual(p.read_bytes(), content)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertTrue(all(sha(p) == expected for p, expected in report["artifact_hashes"].items()))

    def test_old_selector_functional_and_cadence_calculations_are_not_invoked(self):
        with patch("musicanote_harness.factor_functional_trial.evaluate_groups", side_effect=AssertionError("old functional")), \
             patch("musicanote_harness.factor_functional_comparison.compare_functional", side_effect=AssertionError("old comparison")), \
             patch("musicanote_harness.factor_cadence_prerequisites.observe_all_prerequisites", side_effect=AssertionError("old cadence")):
            self.assertTrue(self.execute()["scope_calculation_complete"])

    def test_source_preparation_error_retains_old_denominator_and_reports_failure(self):
        with patch("musicanote_harness.factor_expanded_scope.prepare_scope", side_effect=ValueError("deliberate")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["status"], "calculation_failure")
        self.assertTrue(row["old_groups"])
        self.assertTrue(row["old_lane_refs"])
        self.assertIsNone(row["expanded_scope"])

    def test_assessment_failure_preserves_completed_new_stages_and_unknown_counts(self):
        with patch("musicanote_harness.factor_expanded_hypotheses.evaluate_hypotheses", side_effect=ValueError("deliberate")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["status"], "calculation_failure")
        self.assertTrue(row["old_groups"])
        self.assertIsNotNone(row["expanded_scope"])
        self.assertIsNotNone(row["hypotheses"])
        self.assertIsNone(row["assessment"])
        proposed = read_gzip(row["hypotheses"]["artifact"])
        self.assertTrue(all(group["planned_paths"] is None for group in proposed["path_groups"]))
        self.assertEqual(report["summary"]["materialized_catalogs"], 0)
        self.assertGreater(report["summary"]["planned_catalog_spans"], 0)
        self.assertGreater(report["summary"]["unknown_path_group_counts"], 0)

    def test_generated_creation_hash_is_not_refreshed_after_mutation(self):
        original = storage._save
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                with path.open("ab") as stream:
                    stream.write(b" ")
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])

    def test_added_or_deleted_artifact_is_reported(self):
        original = storage._save
        def added(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(output / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=added):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_extra_parent_file_rejected_before_new_output(self):
        write_json(self.prerequisites / "extra.json", {})
        with self.assertRaisesRegex(ValueError, "inventory_mismatch"):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_rehashed_parent_lane_or_group_removal_cannot_hide_denominator(self):
        path = self.prerequisites / "context-index.json"
        rows = read_json(path)
        rows[0]["lane_inventory"] = []
        write_json(path, rows)
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_parent_music_gold_or_selected_flag_rejected(self):
        path = self.prerequisites / "report.json"
        report = read_json(path)
        report["musical_accuracy_measured"] = True
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "unselected_context"):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_rehashed_foreign_extension_reference_rejected(self):
        path = self.prerequisites / "context-index.json"
        rows = read_json(path)
        rows[0]["context_observation"]["record_ref"]["record_id"] = "fmctx_" + "0" * 24
        write_json(path, rows)
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "extension_identity"):
            self.execute()
