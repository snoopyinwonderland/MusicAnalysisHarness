"""Boundary observations are append-only; parent abstentions remain evidence."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_boundary_explanation_trial as trial
from musicanote_harness import factor_temporal_explanation_trial as previous
from musicanote_harness import factor_temporal_explanations as temporal
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_trial as storage
from test_factor_temporal_explanation_trial import TemporalFixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyBoundaryTrialGuardTests(unittest.TestCase):
    def test_output_and_all_caps_checked_before_parent_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/old"
            old.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), \
                    patch.object(trial, "load_inputs", side_effect=AssertionError("parent read")):
                for destination in (root, old, root / "output/nested/child"):
                    with self.subTest(destination=destination), self.assertRaises(ValueError):
                        trial.run("absent", destination)
                for name in trial.SETTINGS:
                    for value in (True, False, -1, 1.5, None, "1"):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("absent", root / "output/new", **{name: value})

    def test_unknown_cap_checked_before_parent_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(trial, "ROOT", root), \
                    patch.object(trial, "load_inputs", side_effect=AssertionError("parent read")), \
                    self.assertRaises(ValueError):
                trial.run("absent", root / "output/new", max_unregistered_claims=1)
            self.assertFalse((root / "output/new").exists())


class BoundaryFixture(TemporalFixture):
    """Authenticate a real temporal parent; bypass only its older traversal."""
    def setUp(self):
        super().setUp()
        self.grounded_report = self.parent_report
        self.grounded_rows = self.parent_rows
        self.temporal_parent = self.output
        with redirect_stdout(io.StringIO()):
            report = previous.run(self.grounding_parent, self.temporal_parent)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.parent_report = read_json(self.temporal_parent / "report.json")
        self.parent_rows = read_json(self.temporal_parent / "context-index.json")
        self.output = self.root / "output/boundary-child"
        patched = patch.object(trial, "ROOT", self.root)
        patched.start()
        self.addCleanup(patched.stop)

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.temporal_parent, self.output, **kwargs)

    def refresh_parent(self):
        path = self.temporal_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def mutate_rows(self, mutate):
        path = self.temporal_parent / "context-index.json"
        rows = read_json(path)
        mutate(rows)
        write_json(path, rows)
        self.refresh_parent()

    @staticmethod
    def counted_explanations(*args, **kwargs):
        return frozen._seal({"version": "boundary-trial-counting-fixture-0.1.0",
            "status": "fixture_boundary_observations_not_musical_claim",
            "summary": {"known_zero": 0, "computed_relations": 2, "unknown_chains": None,
                        "not_an_integer_metric": False, "nested_breakdown": {"held": 1}}}, "fmbefixture_")

    def execute_counted(self, **kwargs):
        with patch("musicanote_harness.factor_boundary_explanations.build_explanations_prepared",
                   side_effect=self.counted_explanations):
            return self.execute(**kwargs)

    def assert_denominators(self, report):
        for name in trial.DENOMINATORS:
            self.assertEqual(report["summary"][name], self.parent_report["summary"][name], name)
        self.assertEqual(report["parent_summary"], self.parent_report["summary"])
        self.assertEqual(report["summary"]["unexecuted_original_contexts"], 1)
        self.assertEqual(report["summary"]["unexecuted_original_raw_lanes"], 1)
        self.assertIsNone(report["selected"])
        self.assertIs(report["conditional_boundary_role_stage_enabled"], True)
        for name in (*trial.POLICY_FALSE, "cohort_complete", "all_logical_paths_evaluated",
                     "conditional_NCT_evaluated", "boundary_NCT_evaluated", "delayed_resolution_evaluated"):
            self.assertIs(report[name], False, name)
        rows = read_json(self.output / "context-index.json")
        self.assertEqual([row["context_key"] for row in rows],
                         [row["context_key"] for row in self.parent_rows])
        self.assertEqual(report["summary"]["boundary_saved_contexts"],
                         sum(row["boundary_explanations"] is not None for row in rows))
        self.assertEqual(report["summary"]["boundary_failed_contexts"],
                         sum(row["status"] == "calculation_failure" for row in rows))
        for row, original in zip(rows, self.parent_rows):
            for name in (*previous.INHERITED_ROW_FIELDS, "grounding", "grounding_counts",
                         "temporal_explanations", "temporal_counts"):
                self.assertEqual(row[name], original[name], name)
            self.assertEqual(row["old_row_sha256"], trial.digest(original))
            self.assertIsNone(row["old_hypothesis_counts"]["original_path_product"])


class BoundaryParentGuardTests(BoundaryFixture, unittest.TestCase):
    def test_parent_bytes_changed_before_output(self):
        path = self.temporal_parent / "context-index.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.reject_before_output("hash_mismatch")

    def test_registered_temporal_deleted_before_output(self):
        Path(self.parent_rows[0]["temporal_explanations"]["artifact"]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_extra_file_and_rehashed_extra_not_absorbed(self):
        extra = self.temporal_parent / "unregistered.json"
        write_json(extra, {})
        self.reject_before_output("inventory")
        path = self.temporal_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"][str(extra)] = sha(extra)
        write_json(path, report)
        self.reject_before_output("inventory")

    def test_foreign_temporal_folder_not_authority(self):
        original = Path(self.parent_rows[0]["temporal_explanations"]["artifact"])
        foreign = self.temporal_parent / "foreign" / original.name
        foreign.parent.mkdir(parents=True)
        write_gzip(foreign, read_gzip(original))
        self.mutate_rows(lambda rows: rows[0]["temporal_explanations"].update(
            artifact=str(foreign), sha256=sha(foreign)))
        original.unlink()
        path = self.temporal_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"].pop(str(original))
        report["artifact_hashes"][str(foreign)] = sha(foreign)
        write_json(path, report)
        self.refresh_parent()
        self.reject_before_output("foreign_or_unregistered")

    def test_ref_status_sha_and_extra_registration_fields_rejected(self):
        for changes in ({"status": "confirmed"}, {"sha256": "0" * 64},
                        {"record_ref": {"record_id": temporal.PREFIX + "0" * 24, "record_sha256": "0" * 64}},
                        {"unregistered_claim": True}):
            with self.subTest(changes=changes):
                rows = deepcopy(self.parent_rows)
                rows[0]["temporal_explanations"].update(changes)
                write_json(self.temporal_parent / "context-index.json", rows)
                self.refresh_parent()
                self.reject_before_output()

    def test_context_deletion_origin_and_count_changes_rejected(self):
        variants = [[], [dict(deepcopy(self.parent_rows[0]), old_row_sha256="0" * 64)],
                    [dict(deepcopy(self.parent_rows[0]), temporal_counts={})]]
        changed = deepcopy(self.parent_rows)
        changed[0]["old_hypothesis_counts"]["original_path_product"] = 0
        variants.append(changed)
        for rows in variants:
            with self.subTest(rows=rows):
                write_json(self.temporal_parent / "context-index.json", rows)
                self.refresh_parent()
                self.reject_before_output()

    def test_closed_plan_full_closure_and_parent_lineage(self):
        path = self.temporal_parent / "run-plan.json"
        original = read_json(path)
        extra = self.root / "fake-input.json"
        write_json(extra, {})
        variants = []
        changed = deepcopy(original)
        changed["parent_report_sha256"] = "0" * 64
        variants.append(changed)
        changed = deepcopy(original)
        changed["inputs"].pop(next(iter(changed["inputs"])))
        variants.append(changed)
        changed = deepcopy(original)
        changed["inputs"][str(extra)] = sha(extra)
        variants.append(changed)
        changed = deepcopy(original)
        changed["coverage"] = "all_music_certified"
        variants.append(changed)
        changed = deepcopy(original)
        changed["unregistered_semantics"] = True
        variants.append(changed)
        changed = deepcopy(original)
        changed["settings"][next(iter(changed["settings"]))] = False
        variants.append(changed)
        for plan in variants:
            with self.subTest(plan=plan):
                write_json(path, plan)
                self.refresh_parent()
                self.reject_before_output()

    def test_closed_report_policies_parent_summary_and_integer_ledger(self):
        path = self.temporal_parent / "report.json"
        original = read_json(path)
        variants = []
        for name, value in (("selected", "chosen"), ("training_eligible", True),
                            ("conditional_local_contour_stage_enabled", False),
                            ("boundary_NCT_evaluated", True), ("scope_calculation_complete", False),
                            ("parent_summary", {}), ("summary", {}), ("unregistered_semantics", True)):
            report = deepcopy(original)
            report[name] = value
            variants.append(report)
        report = deepcopy(original)
        report.pop("selected")
        variants.append(report)
        report = deepcopy(original)
        ledger = report["summary"]["temporal_integer_subtotals"]
        ledger[next(iter(ledger))] = True
        variants.append(report)
        for report in variants:
            with self.subTest(report=report):
                write_json(path, report)
                self.reject_before_output()

    def test_producer_and_original_input_bytes_remain_protected(self):
        for path in (self.producer, self.prior["directory"] / "report.json",
                     self.grounding_parent / "context-index.json"):
            original = path.read_bytes()
            with self.subTest(path=path):
                path.write_bytes(original + b" ")
                self.reject_before_output("hash_mismatch")
            path.write_bytes(original)

    def test_resealed_temporal_cannot_bypass_fresh_body_replay(self):
        old_path = Path(self.parent_rows[0]["temporal_explanations"]["artifact"])
        value = read_gzip(old_path)
        metric = next(name for name, count in value["summary"].items() if type(count) is int)
        value["summary"][metric] += 1
        value.pop("record_id")
        value.pop("record_sha256")
        changed = frozen._seal(value, temporal.PREFIX)
        new_path = old_path.parent / (changed["record_id"] + ".json.gz")
        write_gzip(new_path, changed)
        self.mutate_rows(lambda rows: rows[0].update(
            temporal_explanations={"artifact": str(new_path), "sha256": sha(new_path),
                "record_ref": frozen._ref(changed), "status": changed["status"]},
            temporal_counts=changed["summary"]))
        old_path.unlink()
        path = self.temporal_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"].pop(str(old_path))
        report["artifact_hashes"][str(new_path)] = sha(new_path)
        report["summary"]["temporal_integer_subtotals"][metric] += 1
        write_json(path, report)
        self.refresh_parent()
        self.reject_before_output()


class BoundaryRunTests(BoundaryFixture, unittest.TestCase):
    def test_cached_issued_tuple_ten_without_second_parent_replay(self):
        from musicanote_harness import factor_boundary_explanations as engine
        with patch.object(engine, "prepare_inputs_prepared", wraps=engine.prepare_inputs_prepared) as prepare:
            data = trial.load_inputs(self.temporal_parent)
        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(len(data["boundary_sessions"]), 1)
        with patch.object(trial.previous, "load_case", side_effect=AssertionError("second source replay")):
            case = trial.load_case(data, data["rows"][0])
            self.assertEqual(len(case), 10)
            self.assertIs(trial.load_case(data, data["rows"][0]), case)
            self.assertEqual(frozen._ref(case[-1]), self.parent_rows[0]["temporal_explanations"]["record_ref"])

    def test_real_engine_preserves_append_only_inputs_and_creation_inventory(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        report = self.execute(max_new_bundles=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        row = read_json(self.output / "context-index.json")[0]
        value = read_gzip(row["boundary_explanations"]["artifact"])
        self.assertEqual(row["boundary_counts"], value["summary"])
        self.assertEqual(row["boundary_explanations"]["record_ref"], frozen._ref(value))
        self.assertEqual(row["status"], "boundary_role_explanations_saved_not_selected")
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual({str(path.resolve()) for path in self.output.rglob("*") if path.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertTrue(all(sha(path) == expected for path, expected in report["artifact_hashes"].items()))

    def test_known_zero_none_bool_and_nested_metrics_remain_distinct(self):
        report = self.execute_counted()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["boundary_integer_subtotals"], {"known_zero": 0, "computed_relations": 2})
        self.assertEqual(report["summary"]["boundary_unknown_metric_contexts"], {"unknown_chains": 1})
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["boundary_counts"]["known_zero"], 0)
        self.assertIsNone(row["boundary_counts"]["unknown_chains"])
        self.assertIs(row["boundary_counts"]["not_an_integer_metric"], False)

    def test_held_record_saved_without_unknown_metric_becoming_zero(self):
        def held(*args, **kwargs):
            return frozen._seal({"version": "boundary-held-fixture-0.1.0",
                "status": "whole_stage_budget_abstention",
                "summary": {"known_planned_candidates": 4, "computed_candidates": None}}, "fmbeheldfixture_")
        with patch("musicanote_harness.factor_boundary_explanations.build_explanations_prepared", side_effect=held):
            report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["boundary_saved_contexts"], 1)
        self.assertEqual(report["summary"]["boundary_failed_contexts"], 0)
        self.assertEqual(report["summary"]["boundary_integer_subtotals"], {"known_planned_candidates": 4})
        self.assertEqual(report["summary"]["boundary_unknown_metric_contexts"], {"computed_candidates": 1})

    def test_authentic_held_parent_unknowns_remain_inherited_not_fake_zero(self):
        held_grounding = self.root / "output/held-grounding-parent"
        held_temporal = self.root / "output/held-temporal-parent"
        with redirect_stdout(io.StringIO()):
            report = previous.previous.run(self.prior["directory"], held_grounding, max_profiles=0)
            self.assertTrue(report["scope_calculation_complete"], report)
            report = previous.run(held_grounding, held_temporal, max_account_templates=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.temporal_parent = held_temporal
        self.parent_report = read_json(held_temporal / "report.json")
        self.parent_rows = read_json(held_temporal / "context-index.json")
        inherited_unknowns = self.parent_report["summary"]["temporal_unknown_metric_contexts"]
        self.assertTrue(inherited_unknowns)
        for metric in inherited_unknowns:
            self.assertIsNone(self.parent_rows[0]["temporal_counts"][metric])
        report = self.execute_counted()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assertEqual(report["parent_summary"]["temporal_unknown_metric_contexts"], inherited_unknowns)

    def test_all_caps_forwarded_and_registered(self):
        settings = {name: index for index, name in enumerate(trial.SETTINGS)}
        with patch("musicanote_harness.factor_boundary_explanations.build_explanations_prepared",
                   side_effect=self.counted_explanations) as build:
            report = self.execute(**settings)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertEqual(build.call_args.kwargs, settings)
        self.assertEqual(read_json(self.output / "run-plan.json")["settings"], settings)

    def test_calculation_failure_keeps_original_counts_origins_and_none(self):
        with patch("musicanote_harness.factor_boundary_explanations.build_explanations_prepared",
                   side_effect=ValueError("deliberate boundary failure")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["boundary_saved_contexts"], 0)
        self.assertEqual(report["summary"]["boundary_failed_contexts"], 1)
        self.assertEqual(report["summary"]["boundary_integer_subtotals"], {})
        self.assertEqual(report["summary"]["boundary_unknown_metric_contexts"], {})
        row = read_json(self.output / "context-index.json")[0]
        self.assertIsNone(row["boundary_explanations"])
        self.assertIsNone(row["boundary_counts"])

    def test_case_load_failure_also_keeps_inherited_denominators(self):
        with patch.object(trial, "load_case", side_effect=ValueError("deliberate cached load failure")):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["boundary_failed_contexts"], 1)

    def test_failed_engine_cannot_hide_cached_parent_mutation(self):
        original = trial.load_case
        cache = []
        def remember(data, row):
            case = original(data, row)
            cache.append(case)
            return case
        def mutate(*args, **kwargs):
            cache[0][1]["note_events"][0]["notation"]["runner_test_mutation"] = True
            raise ValueError("deliberate after mutation")
        with patch.object(trial, "load_case", side_effect=remember), \
                patch("musicanote_harness.factor_boundary_explanations.build_explanations_prepared", side_effect=mutate):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(any("parent_or_IR_mutated" in failure["error"] for failure in report["failures"]))
        self.assert_denominators(report)

    def test_creation_hash_not_refreshed_after_artifact_mutation(self):
        original = storage._save
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.write_bytes(path.read_bytes() + b" ")
            return path
        with patch.object(storage, "_save", side_effect=mutate):
            report = self.execute_counted()
        path = self.output / "context-index.json"
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(path), report["changed_artifacts"])
        self.assertNotEqual(report["artifact_hashes"][str(path)], sha(path))

    def test_artifact_inventory_addition_and_deletion_reported(self):
        original = storage._save
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.unlink()
                write_json(output / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=mutate):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_parent_and_current_code_inventory_additions_not_absorbed(self):
        original = storage._save
        added = self.root / "src/musicanote_harness/extra.py"
        code_paths = trial.parent._code_paths
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(self.temporal_parent / "unregistered.json", {})
                write_json(added, {})
            return path
        with patch.object(storage, "_save", side_effect=mutate), \
                patch.object(trial.parent, "_code_paths", side_effect=lambda:
                    [*code_paths(), *([added] if added.exists() else [])]):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("temporal_parent_inventory_changed", report["changed_inputs_or_code"])
        self.assertIn("current_code_inventory_changed", report["changed_inputs_or_code"])
        self.assertNotIn(str(added), read_json(self.output / "run-plan.json")["code"])

    def test_original_input_change_and_producer_deletion_during_run(self):
        original = storage._save
        changed = self.prior["directory"] / "report.json"
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                changed.write_bytes(changed.read_bytes() + b" ")
                self.producer.unlink()
            return path
        with patch.object(storage, "_save", side_effect=mutate):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(changed), report["changed_inputs_or_code"])
        self.assertIn(str(self.producer), report["changed_inputs_or_code"])


if __name__ == "__main__":
    unittest.main()
