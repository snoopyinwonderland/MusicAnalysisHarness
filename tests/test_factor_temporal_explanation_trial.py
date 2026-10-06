"""Append-only temporal observations retain authentic grounding and abstentions."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_temporal_explanation_trial as trial
from musicanote_harness import factor_grounded_relation_trial as grounded_trial
from musicanote_harness import factor_grounded_relations as grounded
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_trial as storage
from test_factor_grounded_relations import GroundedRelationsFixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyTemporalTrialGuardTests(unittest.TestCase):
    def test_output_and_all_limits_are_checked_before_parent_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/old"
            old.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), \
                    patch.object(trial, "load_inputs", side_effect=AssertionError("parent read")):
                for destination in (root, old, root / "output/nested/child"):
                    with self.subTest(destination=destination), self.assertRaises(ValueError):
                        trial.run("absent", destination)
                for name in ("max_geometry_candidates", "max_membership_relations", "max_new_bundles",
                             "max_account_templates", "query_work_budget"):
                    for value in (True, False, -1, 1.5, None, "1"):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("absent", root / "output/new", **{name: value})


class TemporalFixture:
    """One genuine case; bypass only the already-tested older loader traversal."""
    @classmethod
    def setUpClass(cls):
        factory = GroundedRelationsFixture()
        factory.addCleanup = cls.addClassCleanup
        factory.setUp()
        cls.real_case = factory.frozen_case()
        cls.real_grounding = grounded.build_grounding(*cls.real_case[0], *cls.real_case[1:])

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.producer = self.root / "src/musicanote_harness/fixture_producer.py"
        self.producer.parent.mkdir(parents=True)
        write_json(self.producer, {"producer_fixture": "current protected snapshot"})
        case = deepcopy(self.real_case)
        ir, scope = case[0]
        h, index, relations = case[1:]
        node_names = ("family", "prerequisite", "expanded", "indexed", "relations")
        nodes = {}
        for name in node_names:
            directory = self.root / "output" / name
            directory.mkdir(parents=True)
            path = directory / "report.json"
            write_json(path, {"fixture_prior_loader_handoff": name})
            nodes[name] = {"directory": directory, "hashes": {str(path): sha(path)},
                           "inventory": {str(path.resolve())}}
        nodes["prerequisite"]["family"] = nodes["family"]
        nodes["expanded"]["prerequisites"] = nodes["prerequisite"]
        nodes["indexed"]["expanded"] = nodes["expanded"]
        nodes["relations"]["indexed"] = nodes["indexed"]
        self.prior = nodes["relations"]
        relation_artifacts = {}
        relation_path = storage._save(self.prior["directory"],
            "relations/" + relations["record_id"] + ".json.gz", relations,
            relation_artifacts, compressed=True)
        sample_path = self.prior["directory"] / "function-samples/fixture.json"
        sample_path.parent.mkdir(parents=True)
        write_json(sample_path, {"fixture_prior_queries": []})
        self.prior["hashes"].update(relation_artifacts)
        self.prior["hashes"][str(sample_path)] = sha(sample_path)
        self.prior["inventory"] = set(self.prior["hashes"])
        key = ["fixture:tiny", "frozen-context"]
        self.original_row = {"context_key": key,
            "old_groups": [{"source_group": "original", "planned_paths": None}],
            "old_lane_refs": deepcopy(scope["raw_lanes"]),
            "old_hypothesis_counts": {"original_path_product": None},
            "old_assessment_counts": {"held": 1},
            "expanded_scope": {"record_ref": frozen._ref(scope)},
            "hypotheses": {"record_ref": frozen._ref(h)},
            "indexed_universe": {"record_ref": frozen._ref(index)},
            "index_counts": deepcopy(index["summary"]),
            "relations": {"artifact": str(relation_path), "sha256": sha(relation_path),
                          "record_ref": frozen._ref(relations), "status": relations["status"]},
            "relation_counts": deepcopy(relations["summary"]),
            "function_samples": {"artifact": str(sample_path), "sha256": sha(sample_path),
                                 "requests": 0, "queries": 0},
            "status": "relations_and_function_queries_saved_not_selected", "error": None}
        count = index["summary"]
        summary = {"contexts": 1, "old_raw_lanes": len(scope["raw_lanes"]), "old_groups": 1,
            "indexed_groups": count["groups"], "logical_paths": count["logical_paths"],
            "logical_path_key_tuples": count["logical_path_key_tuples"],
            "logical_function_rows": count["logical_function_shapes"],
            "unknown_logical_groups": count["unknown_product_groups"],
            "origin_variants": count["indexed_variants"],
            "shared_profile_descriptors": count["shared_profile_descriptors"],
            "old_planned_paths": None, "old_unknown_path_group_counts": 1}
        selected = [key]
        self.prior.update(report={"summary": summary}, rows=[self.original_row],
            plan={"declared_contexts": selected + [["fixture:unexecuted", "frozen-context"]],
                  "declared_units": ["first-lane", "unexecuted-lane"],
                  "selected_contexts": selected, "selection": {"fixture": "original"}},
            cases={tuple(key): ({"packet": "protected"}, ir, {"extension": "protected"},
                               scope, h, {"assessment": "protected"}, index, relations)})
        for target, name, value in ((grounded_trial, "ROOT", self.root),
                                    (trial, "ROOT", self.root),
                                    (grounded_trial.parent, "_code_paths", lambda: [self.producer]),
                                    (grounded_trial, "load_inputs", lambda directory: self.prior)):
            patched = patch.object(target, name, value)
            patched.start()
            self.addCleanup(patched.stop)
        self.grounding_parent = self.root / "output/grounded-parent"
        with patch.object(grounded, "build_grounding", return_value=deepcopy(self.real_grounding)), \
                redirect_stdout(io.StringIO()):
            report = grounded_trial.run(self.prior["directory"], self.grounding_parent)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.parent_report = read_json(self.grounding_parent / "report.json")
        self.parent_rows = read_json(self.grounding_parent / "context-index.json")
        self.output = self.root / "output/temporal-child"

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.grounding_parent, self.output, **kwargs)

    def refresh_parent(self):
        path = self.grounding_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def reject_before_output(self, expression=""):
        with self.assertRaisesRegex(ValueError, expression):
            self.execute()
        self.assertFalse(self.output.exists())

    @staticmethod
    def counted_explanations(*args, **kwargs):
        return frozen._seal({"version": "temporal-trial-counting-fixture-0.1.0",
            "status": "fixture_temporal_observations_not_musical_claim",
            "summary": {"known_zero": 0, "computed_accounts": 2, "unknown_relations": None,
                        "not_an_integer_metric": False, "nested_breakdown": {"held": 1}}}, "fmtefixture_")

    def execute_counted(self, **kwargs):
        with patch("musicanote_harness.factor_temporal_explanations.build_explanations_prepared",
                   side_effect=self.counted_explanations):
            return self.execute(**kwargs)


class TemporalParentGuardTests(TemporalFixture, unittest.TestCase):
    def mutate_rows(self, mutate):
        path = self.grounding_parent / "context-index.json"
        rows = read_json(path)
        mutate(rows)
        write_json(path, rows)
        self.refresh_parent()

    def test_parent_bytes_changed_before_output(self):
        path = self.grounding_parent / "context-index.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.reject_before_output("hash_mismatch")

    def test_registered_parent_deleted_before_output(self):
        Path(self.parent_rows[0]["grounding"]["artifact"]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_extra_parent_file_and_rehashed_extra_are_rejected(self):
        extra = self.grounding_parent / "unregistered.json"
        write_json(extra, {})
        self.reject_before_output("inventory")
        path = self.grounding_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"][str(extra)] = sha(extra)
        write_json(path, report)
        self.reject_before_output("inventory")

    def test_foreign_grounding_folder_is_not_authority(self):
        original = Path(self.parent_rows[0]["grounding"]["artifact"])
        foreign = self.grounding_parent / "foreign" / original.name
        foreign.parent.mkdir(parents=True)
        write_gzip(foreign, read_gzip(original))
        self.mutate_rows(lambda rows: rows[0]["grounding"].update(artifact=str(foreign), sha256=sha(foreign)))
        original.unlink()
        path = self.grounding_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"].pop(str(original))
        report["artifact_hashes"][str(foreign)] = sha(foreign)
        write_json(path, report)
        self.refresh_parent()
        self.reject_before_output("foreign_or_unregistered")

    def test_grounding_ref_status_and_sha_cannot_be_substituted(self):
        for changes in ({"status": "confirmed"}, {"sha256": "0" * 64},
                        {"record_ref": {"record_id": "fmgr_" + "0" * 24, "record_sha256": "0" * 64}}):
            with self.subTest(changes=changes):
                rows = deepcopy(self.parent_rows)
                rows[0]["grounding"].update(changes)
                write_json(self.grounding_parent / "context-index.json", rows)
                self.refresh_parent()
                self.reject_before_output()

    def test_contexts_origins_and_counts_remain_exact(self):
        for changed in ([], [dict(deepcopy(self.parent_rows[0]), old_row_sha256="0" * 64)],
                        [dict(deepcopy(self.parent_rows[0]), grounding_counts={})]):
            with self.subTest(changed=changed):
                write_json(self.grounding_parent / "context-index.json", changed)
                self.refresh_parent()
                self.reject_before_output()

    def test_closed_plan_full_closure_and_source_lineage(self):
        path = self.grounding_parent / "run-plan.json"
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
        changed["coverage"] = "all_harmony_correct"
        variants.append(changed)
        changed = deepcopy(original)
        changed["unregistered_semantics"] = True
        variants.append(changed)
        for plan in variants:
            with self.subTest(plan=plan):
                write_json(path, plan)
                self.refresh_parent()
                self.reject_before_output()

    def test_report_policies_and_exact_parent_summary(self):
        path = self.grounding_parent / "report.json"
        original = read_json(path)
        for name, value in (("selected", "chosen"), ("training_eligible", True), ("conditional_NCT_evaluated", True),
                            ("scope_calculation_complete", False), ("parent_summary", {}), ("summary", {}),
                            ("unregistered_semantics", True)):
            with self.subTest(name=name):
                report = deepcopy(original)
                report[name] = value
                write_json(path, report)
                self.reject_before_output()

    def test_producer_and_prior_input_bytes_are_protected(self):
        for path in (self.producer, self.prior["directory"] / "report.json"):
            original = path.read_bytes()
            with self.subTest(path=path):
                path.write_bytes(original + b" ")
                self.reject_before_output("hash_mismatch")
            path.write_bytes(original)

    def test_resealed_grounding_does_not_bypass_fresh_body_validation(self):
        old_path = Path(self.parent_rows[0]["grounding"]["artifact"])
        value = read_gzip(old_path)
        value["summary"]["literal_profiles_computed"] += 1
        value.pop("record_id")
        value.pop("record_sha256")
        changed = frozen._seal(value, grounded.PREFIX)
        new_path = old_path.parent / (changed["record_id"] + ".json.gz")
        write_gzip(new_path, changed)
        self.mutate_rows(lambda rows: rows[0].update(
            grounding={"artifact": str(new_path), "sha256": sha(new_path), "record_ref": frozen._ref(changed),
                       "status": changed["status"]}, grounding_counts=changed["summary"]))
        old_path.unlink()
        path = self.grounding_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"].pop(str(old_path))
        report["artifact_hashes"][str(new_path)] = sha(new_path)
        write_json(path, report)
        self.refresh_parent()
        self.reject_before_output()


class TemporalRunTests(TemporalFixture, unittest.TestCase):
    def assert_denominators(self, report):
        for name in trial.DENOMINATORS:
            self.assertEqual(report["summary"][name], self.parent_report["summary"][name])
        self.assertEqual(report["parent_summary"], self.parent_report["summary"])
        self.assertEqual(report["summary"]["unexecuted_original_contexts"], 1)
        self.assertEqual(report["summary"]["unexecuted_original_raw_lanes"], 1)
        self.assertIsNone(report["selected"])
        for name in (*trial.POLICY_FALSE, "cohort_complete", "all_logical_paths_evaluated",
                     "boundary_NCT_evaluated", "delayed_resolution_evaluated"):
            self.assertIs(report[name], False, name)

    def test_typed_prepared_cache_and_no_second_parent_replay(self):
        data = trial.load_inputs(self.grounding_parent)
        self.assertEqual(len(data["grounded_sessions"]), 1)
        with patch.object(trial.previous, "load_case", side_effect=AssertionError("second source replay")):
            case = trial.load_case(data, data["rows"][0])
            self.assertEqual(len(case), 9)
            self.assertIs(trial.load_case(data, data["rows"][0]), case)
            self.assertEqual(frozen._ref(case[-1]), self.parent_rows[0]["grounding"]["record_ref"])

    def test_real_engine_preserves_append_only_parent_bytes_and_exact_inventory(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute(max_new_bundles=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        row = read_json(self.output / "context-index.json")[0]
        value = read_gzip(row["temporal_explanations"]["artifact"])
        self.assertEqual(row["temporal_counts"], value["summary"])
        self.assertEqual(row["temporal_explanations"]["record_ref"], frozen._ref(value))
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertTrue(all(sha(p) == expected for p, expected in report["artifact_hashes"].items()))

    def test_known_zero_none_bool_and_nested_metrics_are_not_conflated(self):
        report = self.execute_counted()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["temporal_integer_subtotals"], {"known_zero": 0, "computed_accounts": 2})
        self.assertEqual(report["summary"]["temporal_unknown_metric_contexts"], {"unknown_relations": 1})
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["temporal_counts"]["known_zero"], 0)
        self.assertIsNone(row["temporal_counts"]["unknown_relations"])

    def test_all_limits_forwarded_and_registered(self):
        settings = {name: i for i, name in enumerate(trial.SETTINGS)}
        with patch("musicanote_harness.factor_temporal_explanations.build_explanations_prepared",
                   side_effect=self.counted_explanations) as build:
            report = self.execute(**settings)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertEqual(build.call_args.kwargs, settings)
        self.assertEqual(read_json(self.output / "run-plan.json")["settings"], settings)

    def test_calculation_failure_keeps_original_origins_counts_and_unknowns(self):
        with patch("musicanote_harness.factor_temporal_explanations.build_explanations_prepared",
                   side_effect=ValueError("deliberate temporal failure")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["temporal_saved_contexts"], 0)
        self.assertEqual(report["summary"]["temporal_failed_contexts"], 1)
        self.assertEqual(report["summary"]["temporal_integer_subtotals"], {})
        row = read_json(self.output / "context-index.json")[0]
        self.assertIsNone(row["temporal_explanations"])
        self.assertIsNone(row["temporal_counts"])
        for name in (*trial.INHERITED_ROW_FIELDS, "grounding", "grounding_counts"):
            self.assertEqual(row[name], self.parent_rows[0][name])

    def test_failure_cannot_hide_cached_parent_mutation(self):
        old = trial.load_case
        cache = []
        def remember(data, row):
            value = old(data, row)
            cache.append(value)
            return value
        def mutate(*args, **kwargs):
            cache[0][1]["note_events"][0]["notation"]["runner_test_mutation"] = True
            raise ValueError("deliberate after mutation")
        with patch.object(trial, "load_case", side_effect=remember), \
                patch("musicanote_harness.factor_temporal_explanations.build_explanations_prepared", side_effect=mutate):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(any("parent_or_IR_mutated" in row["error"] for row in report["failures"]))
        self.assert_denominators(report)

    def test_creation_hash_not_refreshed_after_output_mutation(self):
        old = storage._save
        def mutate(output, relative, value, artifacts, **kwargs):
            path = old(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.write_bytes(path.read_bytes() + b" ")
            return path
        with patch.object(storage, "_save", side_effect=mutate):
            report = self.execute_counted()
        path = self.output / "context-index.json"
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(path), report["changed_artifacts"])
        self.assertNotEqual(report["artifact_hashes"][str(path)], sha(path))

    def test_artifact_inventory_addition_and_deletion_are_reported(self):
        old = storage._save
        def mutate(output, relative, value, artifacts, **kwargs):
            path = old(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.unlink()
                write_json(output / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=mutate):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_parent_input_and_current_code_inventory_additions_not_absorbed(self):
        old = storage._save
        added = self.root / "src/musicanote_harness/extra.py"
        original_code_paths = trial.parent._code_paths
        def mutate(output, relative, value, artifacts, **kwargs):
            path = old(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(self.grounding_parent / "unregistered.json", {})
                write_json(added, {})
            return path
        with patch.object(storage, "_save", side_effect=mutate), \
                patch.object(trial.parent, "_code_paths", side_effect=lambda:
                    [*original_code_paths(), *([added] if added.exists() else [])]):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("grounding_parent_inventory_changed", report["changed_inputs_or_code"])
        self.assertIn("current_code_inventory_changed", report["changed_inputs_or_code"])
        self.assertNotIn(str(added), read_json(self.output / "run-plan.json")["code"])

    def test_protected_input_change_and_producer_deletion_during_run(self):
        old = storage._save
        changed = self.prior["directory"] / "report.json"
        def mutate(output, relative, value, artifacts, **kwargs):
            path = old(output, relative, value, artifacts, **kwargs)
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
