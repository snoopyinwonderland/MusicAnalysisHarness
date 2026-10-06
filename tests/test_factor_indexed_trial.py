"""Saved fresh-scope inputs remain protected by an append-only lazy index run."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_indexed_trial as trial
from musicanote_harness import factor_musical_trial as storage
import test_factor_expanded_trial as expanded_fixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyIndexedGuardTests(unittest.TestCase):
    def test_output_and_limits_are_checked_before_parent_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/old"
            old.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), \
                    patch.object(trial, "load_inputs", side_effect=AssertionError("read")):
                for destination in (root, old, root / "output/nested/child"):
                    with self.subTest(destination=destination), self.assertRaises(ValueError):
                        trial.run("absent", destination)
                for name in ("max_variants", "max_motion_pairs"):
                    for value in (True, False, -1, 1.5, None, "1"):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("absent", root / "output/new", **{name: value})

    def test_samples_keep_storage_endpoints_deduplicated_with_one_cyclic_key(self):
        index = {"keys": [{"record_id": "k0"}, {"record_id": "k1"}], "path_groups": [
            {"group_id": "held", "status": "source_supplier_hold", "slots": []},
            {"group_id": "singleton", "status": "ready_factorized_group", "slots": [
                {"variant_ids": ["only"]}]},
            {"group_id": "double", "status": "ready_factorized_group", "slots": [
                {"variant_ids": ["a", "b"]}, {"variant_ids": ["c", "d"]}]},
        ]}
        hypotheses = {"keys": deepcopy(index["keys"]), "catalog_inventory": [], "path_groups": []}
        for group in index["path_groups"]:
            refs = []
            for position, slot in enumerate(group["slots"]):
                ref = group["group_id"] + ":" + str(position)
                refs.append(ref)
                hypotheses["catalog_inventory"].append({"catalog_id": ref, "supplier_catalog": {},
                    "variants": [{"record_id": variant} for variant in slot["variant_ids"]]})
            hypotheses["path_groups"].append({"group_id": group["group_id"], "catalog_refs": refs})
        before = deepcopy(index)
        self.assertEqual(trial.sample_requests(hypotheses, index), [
            {"group_id": "singleton", "variant_ids": ["only"], "key_id": "k1"},
            {"group_id": "double", "variant_ids": ["a", "c"], "key_id": "k0"},
            {"group_id": "double", "variant_ids": ["b", "d"], "key_id": "k0"},
        ])
        self.assertEqual(index, before)


class IndexedTrialTests(unittest.TestCase):
    def setUp(self):
        # The synthetic saved family contains one intact old hold context.
        # Its catalog-budget hold must not erase that context or become a
        # demand to rerun the historical selector/evaluator.
        fixture = expanded_fixture.ExpandedTrialTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        report = fixture.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.expanded = fixture.output
        self.output = self.root / "output/indexed"
        patched = patch.object(trial, "ROOT", self.root)
        patched.start()
        self.addCleanup(patched.stop)

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.expanded, self.output, **kwargs)

    def refresh_parent(self):
        path = self.expanded / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def use_supplied_parent(self):
        # Supply catalogs, while holding the old path and comparison products.
        # Only the new namespace may lift that representation bottleneck.
        self.expanded = self.root / "output/expanded-supplied"
        with redirect_stdout(io.StringIO()):
            report = expanded_fixture.trial.run(self.fixture.prerequisites, self.expanded,
                max_catalogs=128, path_budget=1, pair_budget=0, overlay_pair_budget=0,
                max_motion_pairs=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        rows = read_json(self.expanded / "context-index.json")
        self.assertGreater(sum(read_gzip(row["hypotheses"]["artifact"])["summary"]["spelling_variants"]
                               for row in rows), 0)

    def reject_before_output(self, expression=""):
        with self.assertRaisesRegex(ValueError, expression):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_parent_inventory_and_all_old_denominators_remain_append_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute(max_variants=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertTrue(report["selected_denominators_complete"])
        self.assertFalse(report["cohort_complete"])
        self.assertFalse(report["all_logical_paths_evaluated"])
        self.assertIsNone(report["selected"])
        for name in ("harmony_confirmed", "cadence_confirmed", "musical_accuracy_measured",
                     "training_eligible", "gold_eligible", "generation_ready",
                     "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                     "core_or_production_modified"):
            self.assertIs(report[name], False)
        old = read_json(self.expanded / "context-index.json")
        rows = read_json(self.output / "context-index.json")
        self.assertEqual([r["context_key"] for r in rows], [r["context_key"] for r in old])
        unknown_groups = 0
        for row, original in zip(rows, old):
            for name in ("old_groups", "old_lane_refs", "expanded_scope", "hypotheses"):
                self.assertEqual(row[name], original[name])
            self.assertEqual(row["old_hypothesis_counts"], original["hypothesis_counts"])
            self.assertEqual(row["old_assessment_counts"], original["assessment_counts"])
            self.assertIsNotNone(row["indexed_universe"])
            index = read_gzip(row["indexed_universe"]["artifact"])
            unknown_groups += sum(group["logical_path_count"] is None for group in index["path_groups"])
            self.assertTrue(index["path_groups"])
            self.assertTrue(all(group["logical_path_count"] is None for group in index["path_groups"]))
            samples = read_gzip(row["query_samples"]["artifact"])
            self.assertEqual(samples["requests"], [])
            self.assertEqual(samples["queries"], [])
            self.assertEqual(samples["same_bundle_comparisons"], [])
            self.assertIsNone(samples["shared_control_bundle_ref"])
            self.assertFalse(samples["all_logical_paths_evaluated"])
            self.assertIsNone(samples["selected"])
        self.assertEqual(report["summary"]["old_unknown_path_group_counts"],
                         read_json(self.expanded / "report.json")["summary"]["unknown_path_group_counts"])
        self.assertEqual(report["summary"]["unknown_logical_groups"], unknown_groups)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertTrue(all(sha(p) == expected for p, expected in report["artifact_hashes"].items()))

    def test_saved_old_analysis_and_selector_are_not_reexecuted(self):
        self.use_supplied_parent()
        with patch("musicanote_harness.factor_functional_trial.evaluate_groups", side_effect=AssertionError("old functional")), \
             patch("musicanote_harness.factor_functional_comparison.compare_functional", side_effect=AssertionError("old comparison")), \
             patch("musicanote_harness.factor_cadence_prerequisites.observe_all_prerequisites", side_effect=AssertionError("old cadence")), \
             patch("musicanote_harness.factor_expanded_hypotheses.build_hypotheses", side_effect=AssertionError("old hypotheses")), \
             patch("musicanote_harness.factor_expanded_hypotheses.evaluate_hypotheses", side_effect=AssertionError("old evaluation")), \
             patch("musicanote_harness.harmony_candidate_catalog.propose", side_effect=AssertionError("old supplier")):
            self.assertTrue(self.execute()["scope_calculation_complete"])

    def test_supplied_factorized_universe_is_distinct_from_first_last_technical_queries(self):
        self.use_supplied_parent()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        rows = read_json(self.output / "context-index.json")
        total_queries = total_tuples = total_paths = total_functions = 0
        for row in rows:
            index = read_gzip(row["indexed_universe"]["artifact"])
            samples = read_gzip(row["query_samples"]["artifact"])
            self.assertEqual(samples["index_ref"], row["indexed_universe"]["record_ref"])
            self.assertFalse(samples["all_logical_paths_evaluated"])
            self.assertTrue(all(value is False for value in index["flags"].values()))
            expected = []
            for position, group in enumerate(index["path_groups"]):
                if group["logical_path_count"] is not None:
                    total_tuples += group["logical_tuple_count"]
                    total_paths += group["logical_path_count"]
                    total_functions += group["logical_function_count"]
                if (group["status"] != "ready_factorized_group" or not index["keys"]
                        or any(not slot["variant_ids"] for slot in group["slots"])):
                    continue
                endpoints = [tuple(slot["variant_ids"][endpoint] for slot in group["slots"])
                             for endpoint in (0, -1)]
                for variant_ids in dict.fromkeys(endpoints):
                    expected.append({"group_id": group["group_id"], "variant_ids": list(variant_ids),
                        "key_id": index["keys"][position % len(index["keys"])]["record_id"]})
            self.assertEqual(samples["requests"], expected)
            self.assertEqual(len(samples["queries"]), len(expected))
            self.assertEqual(len(samples["same_bundle_comparisons"]), len(expected))
            for comparison in samples["same_bundle_comparisons"]:
                self.assertEqual(comparison["bundle_ref"], samples["shared_control_bundle_ref"])
                self.assertEqual(comparison["computed_counts"]["compatibility_tuples"], 1)
                self.assertGreater(comparison["unqueried_logical_tuple_count"], 0)
                self.assertTrue(all(value is False for value in comparison["flags"].values()))
            for query in samples["queries"]:
                self.assertTrue(all(value is False for value in query["flags"].values()))
                self.assertIsNone(query.get("selected"))
                self.assertIsNone(query.get("rank"))
                self.assertIsNone(query.get("confidence"))
            total_queries += len(expected)
        self.assertGreater(total_queries, 0)
        self.assertGreater(total_tuples, total_queries)
        self.assertEqual(report["summary"]["queried_path_key_tuples"], total_queries)
        self.assertEqual(report["summary"]["same_bundle_technical_comparisons"], total_queries)
        self.assertEqual(report["summary"]["logical_paths"], total_paths)
        self.assertEqual(report["summary"]["logical_path_key_tuples"], total_tuples)
        self.assertEqual(report["summary"]["logical_function_rows"], total_functions)
        self.assertFalse(report["all_logical_paths_evaluated"])
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_zero_variant_budget_does_not_query_a_materialized_prefix(self):
        self.use_supplied_parent()
        report = self.execute(max_variants=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        for row in read_json(self.output / "context-index.json"):
            index = read_gzip(row["indexed_universe"]["artifact"])
            samples = read_gzip(row["query_samples"]["artifact"])
            self.assertEqual(index["variant_inventory"], [])
            self.assertTrue(all(group["logical_path_count"] is not None for group in index["path_groups"]))
            self.assertEqual(samples["requests"], [])
            self.assertEqual(samples["queries"], [])

    def test_index_calculation_failure_preserves_every_old_context_group_and_lane(self):
        with patch("musicanote_harness.factor_indexed_hypotheses.build_index", side_effect=ValueError("deliberate")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        row = read_json(self.output / "context-index.json")[0]
        old = read_json(self.expanded / "context-index.json")[0]
        self.assertEqual(row["status"], "calculation_failure")
        self.assertEqual(row["old_groups"], old["old_groups"])
        self.assertEqual(row["old_lane_refs"], old["old_lane_refs"])
        self.assertIsNone(row["indexed_universe"])
        self.assertIsNone(row["query_samples"])
        self.assertTrue(report["failures"])

    def test_query_failure_retains_completed_index_and_known_symbolic_denominators(self):
        self.use_supplied_parent()
        with patch("musicanote_harness.factor_indexed_hypotheses.query_prepared", side_effect=ValueError("deliberate")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        rows = read_json(self.output / "context-index.json")
        self.assertTrue(all(row["status"] == "calculation_failure" for row in rows))
        self.assertTrue(all(row["indexed_universe"] is not None and row["query_samples"] is None for row in rows))
        groups = [group for row in rows for group in read_gzip(row["indexed_universe"]["artifact"])["path_groups"]]
        self.assertEqual(report["summary"]["logical_paths"], sum(g["logical_path_count"] for g in groups))
        self.assertEqual(report["summary"]["logical_path_key_tuples"], sum(g["logical_tuple_count"] for g in groups))
        self.assertEqual(report["summary"]["logical_function_rows"], sum(g["logical_function_count"] for g in groups))

    def test_engine_failure_does_not_hide_in_memory_parent_mutation(self):
        def changed(ir, scope, hypotheses, **kwargs):
            ir["note_events"][0]["notation"]["unrelated_prose"] = "mutated by failing index engine"
            raise ValueError("deliberate after mutation")
        with patch("musicanote_harness.factor_indexed_hypotheses.build_index", side_effect=changed):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["status"], "calculation_failure")
        self.assertIn("parent_or_IR_mutated", row["error"])
        self.assertTrue(any("parent_or_IR_mutated" in failure["error"] for failure in report["failures"]))

    def test_parent_hash_mutation_is_rejected_before_new_output(self):
        path = self.expanded / "context-index.json"
        with path.open("ab") as stream:
            stream.write(b" ")
        self.reject_before_output("hash_mismatch")

    def test_extra_parent_file_is_rejected_before_new_output(self):
        write_json(self.expanded / "extra.json", {})
        self.reject_before_output("inventory_mismatch")

    def test_rehashed_registered_extra_parent_file_is_not_prerequisite_evidence(self):
        extra = self.expanded / "extra.json"
        write_json(extra, {})
        path = self.expanded / "report.json"
        report = read_json(path)
        report["artifact_hashes"][str(extra)] = sha(extra)
        write_json(path, report)
        self.reject_before_output("inventory")

    def test_current_source_bytes_remain_protected_by_full_prerequisite_chain(self):
        plan = read_json(self.expanded / "run-plan.json")
        path = next(Path(p) for p in plan["inputs"] if p.endswith(".musicxml"))
        with path.open("ab") as stream:
            stream.write(b" ")
        self.reject_before_output("hash_mismatch")

    def test_historical_registered_code_cannot_be_refreshed_by_new_trial(self):
        plan = read_json(self.expanded / "run-plan.json")
        path = next(Path(p) for p in plan["code"] if p.endswith(".py"))
        with path.open("ab") as stream:
            stream.write(b"\n")
        self.reject_before_output("hash_mismatch")

    def test_rehashed_parent_plan_source_policy_promotion_is_rejected(self):
        path = self.expanded / "run-plan.json"
        plan = read_json(path)
        plan["source_labels_used_for_inference"] = True
        write_json(path, plan)
        self.refresh_parent()
        self.reject_before_output("policy_mismatch")

    def test_rehashed_context_deletion_cannot_hide_selected_denominator(self):
        index_path = self.expanded / "context-index.json"
        rows = read_json(index_path)
        report_path = self.expanded / "report.json"
        report = read_json(report_path)
        for row in rows:
            for stage in ("expanded_scope", "hypotheses", "assessment"):
                path = Path(row[stage]["artifact"])
                path.unlink()
                report["artifact_hashes"].pop(str(path))
        write_json(index_path, [])
        write_json(report_path, report)
        self.refresh_parent()
        self.reject_before_output("denominator")

    def test_rehashed_old_lane_removal_cannot_hide_protected_parent(self):
        path = self.expanded / "context-index.json"
        rows = read_json(path)
        rows[0]["old_lane_refs"] = []
        write_json(path, rows)
        self.refresh_parent()
        self.reject_before_output()

    def test_rehashed_old_group_removal_cannot_hide_protected_parent(self):
        path = self.expanded / "context-index.json"
        rows = read_json(path)
        rows[0]["old_groups"] = []
        write_json(path, rows)
        self.refresh_parent()
        self.reject_before_output()

    def test_parent_musical_source_or_selected_promotion_is_rejected(self):
        path = self.expanded / "report.json"
        original = read_json(path)
        for name, value in (("musical_accuracy_measured", True), ("gold_eligible", True),
                            ("training_eligible", True), ("generation_ready", True),
                            ("source_labels_used_for_inference", True), ("selected", "winner")):
            with self.subTest(name=name):
                report = deepcopy(original)
                report[name] = value
                write_json(path, report)
                self.reject_before_output()
        write_json(path, original)

    def test_rehashed_foreign_scope_reference_is_rejected(self):
        path = self.expanded / "context-index.json"
        rows = read_json(path)
        rows[0]["expanded_scope"]["record_ref"]["record_id"] = "fmes_" + "0" * 24
        write_json(path, rows)
        self.refresh_parent()
        self.reject_before_output()

    def test_rehashed_hypothesis_body_requires_actual_intrinsic_seal(self):
        rows = read_json(self.expanded / "context-index.json")
        path = Path(rows[0]["hypotheses"]["artifact"])
        value = read_gzip(path)
        value["flags"]["cadence_confirmed"] = True
        write_gzip(path, value)
        rows[0]["hypotheses"]["sha256"] = sha(path)
        write_json(self.expanded / "context-index.json", rows)
        self.refresh_parent()
        self.reject_before_output()

    def test_rehashed_assessment_body_requires_actual_intrinsic_seal(self):
        rows = read_json(self.expanded / "context-index.json")
        path = Path(rows[0]["assessment"]["artifact"])
        value = read_gzip(path)
        value["flags"]["resolution_confirmed"] = True
        write_gzip(path, value)
        rows[0]["assessment"]["sha256"] = sha(path)
        write_json(self.expanded / "context-index.json", rows)
        self.refresh_parent()
        self.reject_before_output()

    def test_generated_creation_hash_is_not_refreshed_after_mutation(self):
        original = storage._save
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                with path.open("ab") as stream:
                    stream.write(b" ")
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute(max_variants=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])

    def test_extra_generated_artifact_cannot_hide_in_registered_hashes(self):
        original = storage._save
        def added(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(output / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=added):
            report = self.execute(max_variants=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_deleted_generated_artifact_is_reported_not_rehashed(self):
        original = storage._save
        def deleted(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.unlink()
            return path
        with patch.object(storage, "_save", side_effect=deleted):
            report = self.execute(max_variants=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_input_mutation_during_output_is_detected_at_completion(self):
        original = storage._save
        source = self.expanded / "context-index.json"
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                with source.open("ab") as stream:
                    stream.write(b" ")
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute(max_variants=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIn(str(source), report["changed_inputs_or_code"])

    def test_input_inventory_addition_during_output_is_detected(self):
        original = storage._save
        def added(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(self.expanded / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=added):
            report = self.execute(max_variants=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("expanded_parent_inventory_changed", report["changed_inputs_or_code"])


if __name__ == "__main__":
    unittest.main()
