"""New context evidence cannot silently extend a saved harmony experiment."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_context_prerequisite_trial as trial
from musicanote_harness import factor_musical_trial as storage
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_frozen_context_lineage_trial as parent
import test_factor_functional_batch as batch_fixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyTrialGuardTests(unittest.TestCase):
    def test_output_and_limit_guards_precede_input_loading(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/old"
            old.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), patch.object(trial, "load_batch", side_effect=AssertionError("read")):
                for destination in (root, old, root / "output/nested/child"):
                    with self.subTest(destination=destination), self.assertRaises(ValueError):
                        trial.run("absent", destination)
                for name in ("pre_measures", "post_measures", "max_events", "max_relations", "max_records", "max_pairs"):
                    for value in (True, -1, 1.5):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("absent", root / "output/new", **{name: value})


class ContextPrerequisiteTrialTests(unittest.TestCase):
    def setUp(self):
        # Reuse the protected-parent construction, not its test methods or
        # production selector. It explicitly schedules a synthetic hold-only
        # case; tests of real family/change selection remain in the batch suite.
        fixture = batch_fixture.FrozenBatchTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        with redirect_stdout(io.StringIO()):
            report = fixture.execute()
        self.assertTrue(report["batch_complete"], report)
        self.family_batch = fixture.output
        self.output = self.root / "output/context-prerequisites"
        self.patch = patch.object(trial, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.family_batch, self.output, **kwargs)

    def refresh(self):
        path = self.family_batch / "batch-report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def test_every_old_group_lane_overlay_bundle_survives_and_artifacts_are_append_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertFalse(report["cohort_complete"])
        self.assertIsNone(report["selected"])
        for flag in ("harmony_confirmed", "cadence_confirmed", "musical_accuracy_measured",
                     "training_eligible", "gold_eligible", "generation_ready", "old_paths_or_bundles_extended"):
            self.assertIs(report[flag], False)
        index = read_json(self.output / "context-index.json")
        original = read_json(self.family_batch / "context-index.json")
        self.assertEqual([r["context_key"] for r in index], [r["context_key"] for r in original])
        for row, old in zip(index, original):
            saved = read_gzip(old["artifact"])
            self.assertEqual(row["lane_inventory"], saved["lane_inventory"])
            self.assertEqual([(g["group_id"], g["old_status"]) for g in row["groups"]],
                             [(g["group_id"], g["status"]) for g in saved["groups"]])
            self.assertEqual(row["view_ref"], common.ref(saved["context"]["view"]))
            for new_group, old_group in zip(row["groups"], saved["groups"]):
                self.assertEqual(new_group["old_overlay_count"], len(old_group["overlays"]))
                self.assertEqual(len(new_group["records"]), len(old_group["comparisons"]))
                for rec in new_group["records"]:
                    self.assertEqual(rec["planned_records"], len(old_group["overlays"]))
                    self.assertEqual(rec["saved_records"], rec["planned_records"])
        for p, content in before.items():
            self.assertEqual(p.read_bytes(), content)
        for p, expected in report["artifact_hashes"].items():
            self.assertEqual(sha(p), expected)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})

    def test_old_geometry_selector_and_comparison_are_not_reexecuted(self):
        with patch("musicanote_harness.factor_functional_comparison.compare_functional", side_effect=AssertionError("old comparison")), \
             patch("musicanote_harness.harmony_factorized_voice_paths.factorize", side_effect=AssertionError("geometry")), \
             patch("musicanote_harness.factor_functional_trial.evaluate_groups", side_effect=AssertionError("old evaluator")):
            self.assertTrue(self.execute()["scope_calculation_complete"])

    def test_whole_new_record_budget_hold_keeps_original_inventory(self):
        report = self.execute(max_records=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertGreater(report["summary"]["planned_prerequisite_records"], 0)
        self.assertEqual(report["summary"]["saved_prerequisite_records"], 0)
        index = read_json(self.output / "context-index.json")
        self.assertTrue(index[0]["groups"])
        self.assertTrue(all(r["status"] == "withheld_whole_record_budget"
                            for row in index for g in row["groups"] for r in g["records"]))

    def test_case_error_preserves_all_groups_and_reports_incomplete_not_success(self):
        with patch("musicanote_harness.factor_cadence_prerequisites.observe_all_prerequisites", side_effect=ValueError("deliberate")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assertTrue(report["failures"])
        row = read_json(self.output / "context-index.json")[0]
        self.assertTrue(row["groups"][0]["errors"])
        self.assertEqual(row["groups"][0]["records"], [])

    def test_context_producer_failure_is_recorded_not_lost_or_promoted(self):
        with patch("musicanote_harness.factor_context_observation.observe_context", side_effect=ValueError("deliberate context")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["context_observation"]["status"], "calculation_failure")
        self.assertIsNone(row["context_observation"]["record_ref"])
        self.assertTrue(row["lane_inventory"])
        self.assertTrue(row["groups"])
        self.assertTrue(all(not g["records"] for g in row["groups"]))

    def test_extra_parent_file_and_changed_creation_artifact_rejected(self):
        extra = self.family_batch / "extra.json"
        write_json(extra, {})
        with self.assertRaisesRegex(ValueError, "inventory_mismatch"):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_creation_time_child_hash_is_not_refreshed_to_hide_mutation(self):
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
        self.assertEqual(report["changed_artifacts"], [str(self.output / "context-index.json")])

    def test_extra_generated_file_is_not_hidden_by_registered_hashes(self):
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

    def test_parent_denominator_forgery_is_rejected_even_if_rehashed(self):
        path = self.family_batch / "unit-index.json"
        write_json(path, [])
        self.refresh()
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_rehashed_context_projection_is_not_literal_score_evidence(self):
        index = read_json(self.family_batch / "context-index.json")
        path = Path(index[0]["artifact"])
        packet = read_gzip(path)
        packet["context"]["view"]["record_sha256"] = "0" * 64
        write_gzip(path, packet)
        index[0]["sha256"] = sha(path)
        write_json(self.family_batch / "context-index.json", index)
        self.refresh()
        with self.assertRaises(ValueError):
            self.execute()
        self.assertFalse((self.output / "report.json").exists())

    def test_rehashed_group_count_cannot_drop_old_candidates(self):
        index = read_json(self.family_batch / "context-index.json")
        path = Path(index[0]["artifact"])
        packet = read_gzip(path)
        packet["groups"] = []
        write_gzip(path, packet)
        index[0]["sha256"] = sha(path)
        write_json(self.family_batch / "context-index.json", index)
        self.refresh()
        with self.assertRaisesRegex(ValueError, "group_denominator"):
            self.execute()

    def test_rehashed_comparison_removal_cannot_hide_previous_experiment(self):
        index = read_json(self.family_batch / "context-index.json")
        path = Path(index[0]["artifact"])
        packet = read_gzip(path)
        packet["groups"][0]["comparisons"] = []
        write_gzip(path, packet)
        index[0]["sha256"] = sha(path)
        write_json(self.family_batch / "context-index.json", index)
        self.refresh()
        with self.assertRaisesRegex(ValueError, "comparison_status_or_denominator"):
            self.execute()

    def test_rehashed_comparison_body_requires_actual_intrinsic_seal(self):
        index = read_json(self.family_batch / "context-index.json")
        path = Path(index[0]["artifact"])
        packet = read_gzip(path)
        packet["groups"][0]["comparisons"][0]["flags"]["cadence_confirmed"] = True
        write_gzip(path, packet)
        index[0]["sha256"] = sha(path)
        write_json(self.family_batch / "context-index.json", index)
        self.refresh()
        with self.assertRaises(ValueError):
            self.execute()

    def test_rehashed_ready_graph_inventory_cannot_disagree_with_old_lanes(self):
        index = read_json(self.family_batch / "context-index.json")
        path = Path(index[0]["artifact"])
        packet = read_gzip(path)
        packet["ready_graphs"] = []
        write_gzip(path, packet)
        index[0]["sha256"] = sha(path)
        write_json(self.family_batch / "context-index.json", index)
        self.refresh()
        with self.assertRaisesRegex(ValueError, "ready_graph_inventory"):
            self.execute()

    def test_completed_parent_is_not_accepted_as_musical_gold(self):
        path = self.family_batch / "batch-report.json"
        report = read_json(path)
        report["musical_accuracy_measured"] = True
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "research_family_batch"):
            self.execute()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
