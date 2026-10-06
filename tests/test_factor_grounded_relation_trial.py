"""Literal grounding must not refresh, trim, or promote its saved shape parent."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_grounded_relation_trial as trial
from musicanote_harness import factor_function_relations as shapes
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_trial as storage
import test_factor_function_relation_trial as relation_fixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyGroundedRelationGuardTests(unittest.TestCase):
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
                for name in ("max_profiles", "max_motion_kernels", "max_motion_pairs", "max_joint_options"):
                    for value in (True, False, -1, 1.5, None, "1"):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("absent", root / "output/new", **{name: value})


class GroundedFixture:
    supplied_parent = True

    def setUp(self):
        fixture = (relation_fixture.FunctionRelationPositiveTests() if self.supplied_parent
                   else relation_fixture.FunctionRelationUnknownAndFailureTests())
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        with redirect_stdout(io.StringIO()):
            report = fixture.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.relations = fixture.output
        self.indexed_parent = fixture.indexed_parent
        self.output = self.root / "output/grounded-relations"
        self.original_report = read_json(self.relations / "report.json")
        self.original_rows = read_json(self.relations / "context-index.json")
        patched = patch.object(trial, "ROOT", self.root)
        patched.start()
        self.addCleanup(patched.stop)

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.relations, self.output, **kwargs)

    def refresh_parent(self):
        path = self.relations / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def mutate_context(self, mutate):
        path = self.relations / "context-index.json"
        rows = read_json(path)
        mutate(rows)
        write_json(path, rows)
        self.refresh_parent()

    def mutate_samples(self, mutate):
        rows = read_json(self.relations / "context-index.json")
        info = rows[0]["function_samples"]
        path = Path(info["artifact"])
        samples = read_gzip(path)
        mutate(samples)
        write_gzip(path, samples)
        info["sha256"] = sha(path)
        write_json(self.relations / "context-index.json", rows)
        self.refresh_parent()

    def replace_relation(self, mutate):
        """Cross both byte manifests and intrinsic seals, not just byte checks."""
        rows = read_json(self.relations / "context-index.json")
        row = rows[0]
        info = row["relations"]
        sample_info = row["function_samples"]
        old_path, old_sample_path = Path(info["artifact"]), Path(sample_info["artifact"])
        relation = read_gzip(old_path)
        samples = read_gzip(old_sample_path)
        mutate(relation)
        relation.pop("record_id")
        relation.pop("record_sha256")
        relation = shapes._seal(relation, shapes.PREFIX)
        path = old_path.parent / (relation["record_id"] + ".json.gz")
        sample_path = old_sample_path.parent / path.name
        write_gzip(path, relation)
        samples["relations_ref"] = frozen._ref(relation)
        write_gzip(sample_path, samples)
        old_path.unlink()
        old_sample_path.unlink()
        info.update(artifact=str(path), sha256=sha(path), record_ref=frozen._ref(relation))
        sample_info.update(artifact=str(sample_path), sha256=sha(sample_path))
        row["relation_counts"] = deepcopy(relation["summary"])
        write_json(self.relations / "context-index.json", rows)
        report_path = self.relations / "report.json"
        report = read_json(report_path)
        report["artifact_hashes"].pop(str(old_path))
        report["artifact_hashes"].pop(str(old_sample_path))
        report["artifact_hashes"].update({str(path): sha(path), str(sample_path): sha(sample_path)})
        write_json(report_path, report)
        self.refresh_parent()

    def reject_before_output(self, expression=""):
        with self.assertRaisesRegex(ValueError, expression):
            self.execute()
        self.assertFalse(self.output.exists())

    def assert_denominators(self, report):
        self.assertEqual(report["parent_summary"], self.original_report["summary"])
        for name in (*trial.DENOMINATORS, "declared_contexts", "declared_original_raw_lanes",
                     "unexecuted_original_contexts", "unexecuted_original_raw_lanes"):
            self.assertEqual(report["summary"][name], self.original_report["summary"][name], name)
        rows = read_json(self.output / "context-index.json")
        self.assertEqual([r["context_key"] for r in rows], [r["context_key"] for r in self.original_rows])
        self.assertEqual(report["summary"]["grounding_saved_contexts"],
                         sum(row["grounding"] is not None for row in rows))
        self.assertEqual(report["summary"]["grounding_failed_contexts"],
                         sum(row["status"] == "calculation_failure" for row in rows))
        for row, original in zip(rows, self.original_rows):
            for name in ("old_groups", "old_lane_refs", "old_hypothesis_counts", "old_assessment_counts",
                         "expanded_scope", "hypotheses", "indexed_universe", "index_counts",
                         "relations", "relation_counts", "function_samples"):
                self.assertEqual(row[name], original[name], name)
            self.assertEqual(row["old_row_sha256"], trial.digest(original))

    def assert_unselected(self, report):
        self.assertIsNone(report["selected"])
        for name in (*trial.POLICY_FALSE, "cohort_complete", "all_logical_paths_evaluated",
                     "conditional_NCT_evaluated", "delayed_resolution_evaluated"):
            self.assertIs(report[name], False, name)

    @staticmethod
    def counted_grounding(*args, **kwargs):
        # Mock only new-stage metric accounting; all saved parent loading is real.
        return frozen._seal({"version": "grounded-runner-counting-fixture-0.1.0",
            "status": "fixture_grounding_not_music_claim",
            "summary": {"known_zero": 0, "computed_profiles": 2, "unknown_motion": None,
                        "not_an_integer_metric": False, "nested_breakdown": {"held": 1}}}, "fmgfixture_")

    def execute_counted(self, **kwargs):
        with patch("musicanote_harness.factor_grounded_relations.build_grounding",
                   side_effect=self.counted_grounding):
            return self.execute(**kwargs)


class GroundedRelationParentGuardTests(GroundedFixture, unittest.TestCase):
    def test_parent_bytes_changed_are_rejected_before_output(self):
        path = self.relations / "context-index.json"
        with path.open("ab") as stream:
            stream.write(b" ")
        self.reject_before_output("hash_mismatch")

    def test_missing_registered_relation_is_rejected_before_output(self):
        path = Path(self.original_rows[0]["relations"]["artifact"])
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_extra_unregistered_parent_file_is_not_absorbed(self):
        write_json(self.relations / "extra.json", {})
        self.reject_before_output("inventory")

    def test_rehashed_registered_extra_parent_file_is_not_evidence(self):
        path = self.relations / "extra.json"
        write_json(path, {})
        report_path = self.relations / "report.json"
        report = read_json(report_path)
        report["artifact_hashes"][str(path)] = sha(path)
        write_json(report_path, report)
        self.reject_before_output("inventory")

    def test_registered_relation_in_wrong_folder_is_not_authority(self):
        old_path = Path(self.original_rows[0]["relations"]["artifact"])
        foreign = self.relations / "function-samples" / ("foreign-" + old_path.name)
        write_gzip(foreign, read_gzip(old_path))
        old_path.unlink()
        rows = read_json(self.relations / "context-index.json")
        rows[0]["relations"].update(artifact=str(foreign), sha256=sha(foreign))
        write_json(self.relations / "context-index.json", rows)
        report_path = self.relations / "report.json"
        report = read_json(report_path)
        report["artifact_hashes"].pop(str(old_path))
        report["artifact_hashes"][str(foreign)] = sha(foreign)
        write_json(report_path, report)
        self.refresh_parent()
        self.reject_before_output("foreign_or_unregistered_relation_stage")

    def test_rehashed_relation_ref_status_or_sha_substitution_is_rejected(self):
        original = deepcopy(self.original_rows)
        replacements = ({"record_ref": {"record_id": "fmfrel_" + "0" * 24, "record_sha256": "0" * 64}},
                        {"status": "confirmed"}, {"sha256": "0" * 64})
        for replacement in replacements:
            with self.subTest(replacement=replacement):
                rows = deepcopy(original)
                rows[0]["relations"].update(replacement)
                write_json(self.relations / "context-index.json", rows)
                self.refresh_parent()
                self.reject_before_output()

    def test_closed_plan_and_exact_registered_input_closure_are_required(self):
        path = self.relations / "run-plan.json"
        original = read_json(path)
        extra = self.root / "extra-protected-input.json"
        write_json(extra, {})
        variants = []
        changed = deepcopy(original)
        changed["parent_report_sha256"] = "0" * 64
        variants.append(("lineage", changed))
        changed = deepcopy(original)
        changed["unregistered_semantic_claim"] = True
        variants.append(("saved_function_relation_plan", changed))
        changed = deepcopy(original)
        changed["inputs"].pop(next(iter(changed["inputs"])))
        variants.append(("closure", changed))
        changed = deepcopy(original)
        changed["inputs"][str(extra)] = sha(extra)
        variants.append(("closure", changed))
        for expression, plan in variants:
            with self.subTest(expression=expression, keys=set(plan)):
                write_json(path, plan)
                self.refresh_parent()
                self.reject_before_output(expression)

    def test_rehashed_context_deletion_cannot_hide_protected_denominator(self):
        self.mutate_context(lambda rows: rows.clear())
        self.reject_before_output("denominator")

    def test_resealed_relation_origin_counts_are_not_validated_by_seal_alone(self):
        self.replace_relation(lambda record: record["summary"].update(
            origin_variants=record["summary"]["origin_variants"] + 1))
        self.reject_before_output()

    def test_resealed_shape_query_requires_exact_fresh_body_and_flags(self):
        def changed(samples):
            self.assertTrue(samples["queries"])
            query = samples["queries"][0]
            query["flags"]["source_labels_used_for_inference"] = True
            query.pop("record_id")
            query.pop("record_sha256")
            samples["queries"][0] = shapes._seal(query, shapes.QUERY_PREFIX)
        self.mutate_samples(changed)
        self.reject_before_output("fresh_replay")

    def test_rehashed_shape_samples_cannot_claim_music_accuracy(self):
        self.mutate_samples(lambda samples: samples.update(musical_accuracy_measured=True))
        self.reject_before_output("policy")

    def test_rehashed_sample_request_count_cannot_disagree_with_queries(self):
        self.mutate_context(lambda rows: rows[0]["function_samples"].update(requests=0))
        self.reject_before_output("denominator")

    def test_report_cannot_promote_selection_or_usage_policy(self):
        path = self.relations / "report.json"
        original = read_json(path)
        for name, value in (("selected", "chosen"), ("training_eligible", True),
                            ("generation_ready", True), ("scope_calculation_complete", False),
                            ("unregistered_semantic_claim", True), ("selected", "REMOVE")):
            with self.subTest(name=name):
                report = deepcopy(original)
                if value == "REMOVE":
                    report.pop(name)
                else:
                    report[name] = value
                write_json(path, report)
                self.reject_before_output()

    def test_original_source_and_producer_bytes_remain_protected(self):
        plan = read_json(self.relations / "run-plan.json")
        for kind, collection, suffix in (("source", "inputs", ".musicxml"), ("code", "code", ".py")):
            path = next(Path(p) for p in plan[collection] if p.endswith(suffix))
            self.assertTrue(path.is_relative_to(self.root))
            content = path.read_bytes()
            with self.subTest(kind=kind):
                with path.open("ab") as stream:
                    stream.write(b" ")
                self.reject_before_output("hash_mismatch")
            # Only synthetic temporary fixture bytes are restored.
            path.write_bytes(content)


class GroundedRelationRunTests(GroundedFixture, unittest.TestCase):
    def test_real_grounding_preserves_parent_chain_and_append_only_inventory(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute(max_motion_pairs=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assert_unselected(report)
        rows = read_json(self.output / "context-index.json")
        for row in rows:
            self.assertIsNotNone(row["grounding"])
            grounding = read_gzip(row["grounding"]["artifact"])
            self.assertEqual(row["grounding_counts"], grounding["summary"])
            self.assertEqual(row["grounding"]["record_ref"], frozen._ref(grounding))
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertTrue(all(sha(p) == expected for p, expected in report["artifact_hashes"].items()))

    def test_integer_zero_and_unknown_context_counts_remain_distinct(self):
        report = self.execute_counted()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        contexts = report["summary"]["contexts"]
        self.assertEqual(report["summary"]["grounding_integer_subtotals"],
                         {"known_zero": 0, "computed_profiles": 2 * contexts})
        self.assertEqual(report["summary"]["grounding_unknown_metric_contexts"], {"unknown_motion": contexts})
        for row in read_json(self.output / "context-index.json"):
            self.assertEqual(row["grounding_counts"]["known_zero"], 0)
            self.assertIsNone(row["grounding_counts"]["unknown_motion"])

    def test_load_case_uses_validated_eight_item_cache_without_parent_replay(self):
        data = trial.load_inputs(self.relations)
        with patch.object(trial.previous, "load_case", side_effect=AssertionError("cached parent replay")):
            for row in data["rows"]:
                case = trial.load_case(data, row)
                self.assertEqual(len(case), 8)
                self.assertEqual(frozen._ref(case[-1]), row["relations"]["record_ref"])
                self.assertIs(trial.load_case(data, row), case)

    def test_build_failure_retains_every_parent_count_origin_and_reference(self):
        with patch("musicanote_harness.factor_grounded_relations.build_grounding",
                   side_effect=ValueError("deliberate grounding failure")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertFalse(report["computation_integrity_passed"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assert_unselected(report)
        self.assertEqual(report["summary"]["grounding_integer_subtotals"], {})
        self.assertEqual(report["summary"]["grounding_unknown_metric_contexts"], {})
        self.assertTrue(report["failures"])
        for row in read_json(self.output / "context-index.json"):
            self.assertEqual(row["status"], "calculation_failure")
            self.assertIsNone(row["grounding"])
            self.assertNotIn("grounding_counts", row)

    def test_failing_engine_cannot_hide_in_memory_parent_or_ir_mutation(self):
        def changed(ir, scope, hypotheses, index, relation, **kwargs):
            ir["note_events"][0]["notation"]["runner_test_mutation"] = True
            raise ValueError("deliberate failure after input mutation")
        with patch("musicanote_harness.factor_grounded_relations.build_grounding", side_effect=changed):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assertTrue(any("parent_or_IR_mutated" in row["error"] for row in report["failures"]))

    def test_generated_creation_sha_is_not_refreshed_after_mutation(self):
        original = storage._save
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                with path.open("ab") as stream:
                    stream.write(b" ")
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute_counted()
        path = self.output / "context-index.json"
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(path), report["changed_artifacts"])
        self.assertNotEqual(report["artifact_hashes"][str(path)], sha(path))

    def test_generated_inventory_addition_and_deletion_are_reported(self):
        original = storage._save
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.unlink()
                write_json(output / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_input_and_code_inventory_additions_are_not_absorbed(self):
        original = storage._save
        added_code = self.root / "src/musicanote_harness/grounded_extra_runtime.py"
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(self.relations / "unregistered.json", {})
                write_json(added_code, {})
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("relations_parent_inventory_changed", report["changed_inputs_or_code"])
        self.assertIn("current_code_inventory_changed", report["changed_inputs_or_code"])
        self.assertNotIn(str(added_code), read_json(self.output / "run-plan.json")["code"])

    def test_input_bytes_and_code_deletion_during_run_are_reported(self):
        original = storage._save
        deleted_code = next(Path(p) for p in read_json(self.relations / "run-plan.json")["code"] if p.endswith(".py"))
        self.assertTrue(deleted_code.is_relative_to(self.root))
        source = self.indexed_parent / "context-index.json"
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                with source.open("ab") as stream:
                    stream.write(b" ")
                deleted_code.unlink()
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIn(str(source), report["changed_inputs_or_code"])
        self.assertIn(str(deleted_code), report["changed_inputs_or_code"])
        self.assertIn("current_code_inventory_changed", report["changed_inputs_or_code"])


class GroundedRelationUnknownParentTests(GroundedFixture, unittest.TestCase):
    supplied_parent = False

    def test_unknown_parent_products_and_original_holds_are_not_fake_zero(self):
        report = self.execute(max_profiles=0, max_motion_kernels=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assert_unselected(report)
        self.assertGreater(report["summary"]["unknown_logical_groups"], 0)
        for row, original in zip(read_json(self.output / "context-index.json"), self.original_rows):
            relation = read_gzip(original["relations"]["artifact"])
            self.assertTrue(relation["path_groups"])
            self.assertTrue(all(group["logical_path_count"] is None for group in relation["path_groups"]))
            self.assertEqual(row["relation_counts"], original["relation_counts"])
            self.assertIsNotNone(row["grounding"])


if __name__ == "__main__":
    unittest.main()
