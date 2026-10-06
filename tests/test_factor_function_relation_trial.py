"""An append-only shape/key relation stage cannot refresh its saved parents."""
from contextlib import redirect_stdout
from collections import Counter
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_function_relation_trial as trial
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_trial as storage
import test_factor_indexed_trial as indexed_fixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyFunctionRelationGuardTests(unittest.TestCase):
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
                for value in (True, False, -1, 1.5, None, "1"):
                    with self.subTest(value=value), self.assertRaises(ValueError):
                        trial.run("absent", root / "output/new", max_kernels=value)

    def test_samples_preserve_endpoints_dedup_and_one_cyclic_key_for_all_slots(self):
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
        before = deepcopy((hypotheses, index))
        expected = []
        for request in [{"group_id": "singleton", "variant_ids": ["only"], "key_id": "k1"},
                        {"group_id": "double", "variant_ids": ["a", "c"], "key_id": "k0"},
                        {"group_id": "double", "variant_ids": ["b", "d"], "key_id": "k0"}]:
            for slot in range(len(request["variant_ids"])):
                for family in frozen.FAMILIES:
                    for quality in ("M", "m"):
                        expected.append({**request, "slot_index": slot, "family": family, "quality": quality})
        self.assertEqual(trial.sample_requests(hypotheses, index), expected)
        self.assertEqual((hypotheses, index), before)


class RelationFixture:
    supplied_parent = False

    def setUp(self):
        fixture = indexed_fixture.IndexedTrialTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        if self.supplied_parent:
            fixture.use_supplied_parent()
        report = fixture.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.indexed_parent = fixture.output
        self.output = self.root / "output/function-relations"
        patched = patch.object(trial, "ROOT", self.root)
        patched.start()
        self.addCleanup(patched.stop)

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.indexed_parent, self.output, **kwargs)

    def refresh_parent(self):
        path = self.indexed_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def reject_before_output(self, expression=""):
        with self.assertRaisesRegex(ValueError, expression):
            self.execute()
        self.assertFalse(self.output.exists())

    def mutate_context(self, mutate):
        path = self.indexed_parent / "context-index.json"
        rows = read_json(path)
        mutate(rows)
        write_json(path, rows)
        self.refresh_parent()

    def mutate_samples(self, mutate):
        rows = read_json(self.indexed_parent / "context-index.json")
        info = rows[0]["query_samples"]
        path = Path(info["artifact"])
        value = read_gzip(path)
        mutate(value)
        write_gzip(path, value)
        info["sha256"] = sha(path)
        write_json(self.indexed_parent / "context-index.json", rows)
        self.refresh_parent()

    def replace_held_index(self, mutate):
        """Cross both byte manifests and intrinsic seals, preserving closure."""
        rows = read_json(self.indexed_parent / "context-index.json")
        info = rows[0]["indexed_universe"]
        sample_info = rows[0]["query_samples"]
        old_path = Path(info["artifact"])
        old_sample_path = Path(sample_info["artifact"])
        body = read_gzip(old_path)
        sample = read_gzip(old_sample_path)
        self.assertEqual(sample["queries"], [])
        self.assertEqual(sample["same_bundle_comparisons"], [])
        mutate(body)
        body.pop("record_id")
        body.pop("record_sha256")
        body = indexed._seal(body, indexed.PREFIX)
        path = old_path.parent / (body["record_id"] + ".json.gz")
        sample_path = old_sample_path.parent / path.name
        write_gzip(path, body)
        sample["index_ref"] = indexed.frozen._ref(body)
        write_gzip(sample_path, sample)
        old_path.unlink()
        old_sample_path.unlink()
        info.update(artifact=str(path), sha256=sha(path), record_ref=indexed.frozen._ref(body))
        sample_info.update(artifact=str(sample_path), sha256=sha(sample_path))
        write_json(self.indexed_parent / "context-index.json", rows)
        report_path = self.indexed_parent / "report.json"
        report = read_json(report_path)
        report["artifact_hashes"].pop(str(old_path))
        report["artifact_hashes"].pop(str(old_sample_path))
        report["artifact_hashes"][str(path)] = sha(path)
        report["artifact_hashes"][str(sample_path)] = sha(sample_path)
        write_json(report_path, report)
        self.refresh_parent()

    def assert_append_only_inventory(self, report, before):
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertTrue(all(sha(p) == expected for p, expected in report["artifact_hashes"].items()))

    def assert_unselected_policy(self, report):
        self.assertFalse(report["cohort_complete"])
        self.assertFalse(report["all_logical_paths_evaluated"])
        self.assertIsNone(report["selected"])
        for name in ("harmony_confirmed", "cadence_confirmed", "musical_accuracy_measured",
                     "training_eligible", "gold_eligible", "generation_ready",
                     "source_labels_used_for_inference", "old_paths_or_bundles_extended",
                     "core_or_production_modified"):
            self.assertIs(report[name], False)
        for name in ("profiles_evaluated", "motion_evaluated", "same_bundle_evaluated"):
            self.assertIs(report[name], False)

    def assert_parent_denominators(self, report):
        old = read_json(self.indexed_parent / "report.json")["summary"]
        for name in ("indexed_groups", "logical_paths", "logical_path_key_tuples",
                     "logical_function_rows", "unknown_logical_groups", "origin_variants",
                     "shared_profile_descriptors", "contexts", "old_raw_lanes", "old_groups",
                     "declared_contexts", "declared_original_raw_lanes",
                     "unexecuted_original_contexts", "unexecuted_original_raw_lanes"):
            self.assertEqual(report["summary"][name], old[name], name)


class FunctionRelationParentGuardTests(RelationFixture, unittest.TestCase):
    def test_parent_hash_mutation_is_rejected_before_new_output(self):
        path = self.indexed_parent / "context-index.json"
        with path.open("ab") as stream:
            stream.write(b" ")
        self.reject_before_output("hash_mismatch")

    def test_extra_parent_file_is_rejected_before_new_output(self):
        write_json(self.indexed_parent / "extra.json", {})
        self.reject_before_output("inventory")

    def test_rehashed_registered_extra_parent_is_not_prerequisite_evidence(self):
        extra = self.indexed_parent / "extra.json"
        write_json(extra, {})
        path = self.indexed_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"][str(extra)] = sha(extra)
        write_json(path, report)
        self.reject_before_output("inventory")

    def test_missing_registered_parent_artifact_is_rejected(self):
        rows = read_json(self.indexed_parent / "context-index.json")
        missing_path = Path(rows[0]["indexed_universe"]["artifact"])
        missing_path.unlink()
        # The historical guard resolves registered paths strictly before its
        # byte-hash branch; its concrete missing-file failure is preserved.
        with self.assertRaises(FileNotFoundError) as caught:
            self.execute()
        self.assertIn(missing_path.name, str(caught.exception))
        self.assertFalse(self.output.exists())

    def test_current_source_bytes_remain_protected_by_original_chain(self):
        plan = read_json(self.indexed_parent / "run-plan.json")
        path = next(Path(p) for p in plan["inputs"] if p.endswith(".musicxml"))
        with path.open("ab") as stream:
            stream.write(b" ")
        self.reject_before_output("hash_mismatch")

    def test_registered_producer_code_cannot_be_refreshed(self):
        plan = read_json(self.indexed_parent / "run-plan.json")
        path = next(Path(p) for p in plan["code"] if p.endswith(".py"))
        with path.open("ab") as stream:
            stream.write(b"\n")
        self.reject_before_output("hash_mismatch")

    def test_rehashed_parent_plan_cannot_promote_source_policy(self):
        path = self.indexed_parent / "run-plan.json"
        value = read_json(path)
        value["source_labels_used_for_inference"] = True
        write_json(path, value)
        self.refresh_parent()
        self.reject_before_output()

    def test_parent_report_cannot_promote_selection_accuracy_or_use(self):
        path = self.indexed_parent / "report.json"
        original = read_json(path)
        for name, value in (("musical_accuracy_measured", True), ("gold_eligible", True),
                            ("training_eligible", True), ("generation_ready", True),
                            ("source_labels_used_for_inference", True), ("selected", "winner"),
                            ("cohort_complete", True), ("all_logical_paths_evaluated", True),
                            ("source_labels_used_for_inference", 0)):
            with self.subTest(name=name):
                changed = deepcopy(original)
                changed[name] = value
                write_json(path, changed)
                self.reject_before_output()
        write_json(path, original)

    def test_rehashed_context_deletion_cannot_hide_selected_denominator(self):
        rows = read_json(self.indexed_parent / "context-index.json")
        path = self.indexed_parent / "report.json"
        report = read_json(path)
        for row in rows:
            for stage in ("indexed_universe", "query_samples"):
                target = Path(row[stage]["artifact"])
                target.unlink()
                report["artifact_hashes"].pop(str(target))
        write_json(self.indexed_parent / "context-index.json", [])
        write_json(path, report)
        self.refresh_parent()
        self.reject_before_output("denominator")

    def test_rehashed_old_lane_removal_cannot_hide_protected_parent(self):
        self.mutate_context(lambda rows: rows[0].update(old_lane_refs=[]))
        self.reject_before_output()

    def test_rehashed_old_group_removal_cannot_hide_protected_parent(self):
        self.mutate_context(lambda rows: rows[0].update(old_groups=[]))
        self.reject_before_output()

    def test_rehashed_foreign_index_reference_is_rejected(self):
        def changed(rows):
            rows[0]["indexed_universe"]["record_ref"]["record_id"] = "fmiidx_" + "0" * 24
        self.mutate_context(changed)
        self.reject_before_output()

    def test_rehashed_foreign_parent_scope_reference_is_rejected(self):
        def changed(rows):
            rows[0]["expanded_scope"]["record_ref"]["record_id"] = "fmes_" + "0" * 24
        self.mutate_context(changed)
        self.reject_before_output()

    def test_resealed_parent_index_flags_cannot_promote_source_authority(self):
        def changed(value):
            value["flags"]["source_artifact_authority_established"] = True
        self.replace_held_index(changed)
        self.reject_before_output()

    def test_resealed_parent_index_summary_cannot_hide_unknown_groups(self):
        def changed(value):
            value["summary"]["unknown_product_groups"] = 0
        self.replace_held_index(changed)
        self.reject_before_output()

    def test_rehashed_sample_envelope_cannot_claim_music_accuracy(self):
        self.mutate_samples(lambda value: value.update(musical_accuracy_measured=True))
        self.reject_before_output()

    def test_rehashed_sample_envelope_requires_registered_index_identity(self):
        def changed(value):
            value["index_ref"]["record_id"] = "fmiidx_" + "0" * 24
        self.mutate_samples(changed)
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
            report = self.execute(max_kernels=0)
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
            report = self.execute(max_kernels=0)
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
            report = self.execute(max_kernels=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_input_mutation_during_output_is_detected_at_completion(self):
        original = storage._save
        source = self.indexed_parent / "context-index.json"
        def changed(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                with source.open("ab") as stream:
                    stream.write(b" ")
            return path
        with patch.object(storage, "_save", side_effect=changed):
            report = self.execute(max_kernels=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIn(str(source), report["changed_inputs_or_code"])

    def test_input_inventory_addition_during_output_is_detected(self):
        original = storage._save
        def added(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(self.indexed_parent / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=added):
            report = self.execute(max_kernels=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("indexed_parent_inventory_changed", report["changed_inputs_or_code"])

    def test_current_code_inventory_addition_is_not_absorbed_into_creation_hashes(self):
        original = storage._save
        added_path = self.root / "src/musicanote_harness/extra_runtime_source.py"
        def added(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(added_path, {})
            return path
        with patch.object(storage, "_save", side_effect=added):
            report = self.execute(max_kernels=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("current_code_inventory_changed", report["changed_inputs_or_code"])
        self.assertNotIn(str(added_path), read_json(self.output / "run-plan.json")["code"])

    def test_current_code_deletion_is_reported_not_rehashed(self):
        original = storage._save
        plan = read_json(self.indexed_parent / "run-plan.json")
        deleted_path = next(Path(p) for p in plan["code"] if p.endswith(".py"))
        self.assertTrue(deleted_path.is_relative_to(self.root))
        def deleted(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                deleted_path.unlink()
            return path
        with patch.object(storage, "_save", side_effect=deleted):
            report = self.execute(max_kernels=0)
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(deleted_path), report["changed_inputs_or_code"])


class FunctionRelationUnknownAndFailureTests(RelationFixture, unittest.TestCase):
    def test_all_old_contexts_lanes_and_unknown_denominators_remain_append_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute(max_kernels=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_unselected_policy(report)
        self.assert_parent_denominators(report)
        self.assertGreater(report["summary"]["unknown_logical_groups"], 0)
        old = read_json(self.indexed_parent / "context-index.json")
        rows = read_json(self.output / "context-index.json")
        self.assertEqual([r["context_key"] for r in rows], [r["context_key"] for r in old])
        for row, original in zip(rows, old):
            for name in ("old_groups", "old_lane_refs", "old_hypothesis_counts",
                         "old_assessment_counts", "expanded_scope", "hypotheses",
                         "indexed_universe", "index_counts"):
                self.assertEqual(row[name], original[name], name)
            self.assertIsNotNone(row["relations"])
            relation = read_gzip(row["relations"]["artifact"])
            self.assertEqual(row["relation_counts"], relation["summary"])
            self.assertTrue(relation["path_groups"])
            self.assertTrue(all(g["logical_path_count"] is None for g in relation["path_groups"]))
            self.assertEqual(relation["kernels"], [])
            samples = read_gzip(row["function_samples"]["artifact"])
            self.assertEqual(samples["requests"], [])
            self.assertEqual(samples["queries"], [])
            for name in ("profiles_evaluated", "motion_evaluated",
                         "all_logical_paths_evaluated", "musical_accuracy_measured"):
                self.assertIs(samples[name], False)
            self.assertIsNone(samples["selected"])
        self.assert_append_only_inventory(report, before)

    def test_build_failure_retains_every_old_context_group_lane_and_denominator(self):
        with patch("musicanote_harness.factor_function_relations.build_relations",
                   side_effect=ValueError("deliberate relation failure")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_parent_denominators(report)
        rows = read_json(self.output / "context-index.json")
        old = read_json(self.indexed_parent / "context-index.json")
        for row, original in zip(rows, old):
            self.assertEqual(row["status"], "calculation_failure")
            self.assertEqual(row["old_groups"], original["old_groups"])
            self.assertEqual(row["old_lane_refs"], original["old_lane_refs"])
            self.assertEqual(row["indexed_universe"], original["indexed_universe"])
            self.assertIsNone(row["relations"])
            self.assertIsNone(row["function_samples"])
        self.assertTrue(report["failures"])

    def test_failing_engine_cannot_hide_in_memory_parent_mutation(self):
        def changed(ir, scope, hypotheses, index, **kwargs):
            ir["note_events"][0]["notation"]["unrelated_prose"] = "changed by failing relation engine"
            raise ValueError("deliberate after mutation")
        with patch("musicanote_harness.factor_function_relations.build_relations", side_effect=changed):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_parent_denominators(report)
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["status"], "calculation_failure")
        self.assertIn("parent_or_IR_mutated", row["error"])
        self.assertTrue(any("parent_or_IR_mutated" in failure["error"] for failure in report["failures"]))


class FunctionRelationPositiveTests(RelationFixture, unittest.TestCase):
    supplied_parent = True

    @staticmethod
    def reseal_query_and_comparison(sample):
        query = sample["queries"][0]
        query.pop("record_id")
        query.pop("record_sha256")
        query = indexed._seal(query, indexed.QUERY_PREFIX)
        sample["queries"][0] = query
        comparison = sample["same_bundle_comparisons"][0]
        comparison["query_ref"] = frozen._ref(query)
        comparison.pop("record_id")
        comparison.pop("record_sha256")
        sample["same_bundle_comparisons"][0] = indexed._seal(comparison, indexed.ASSESSMENT_PREFIX)

    def test_samples_expand_all_slots_and_ten_function_shapes_without_ranking(self):
        report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_unselected_policy(report)
        self.assert_parent_denominators(report)
        total_queries = 0
        aggregate = Counter()
        shape_states, function_kinds = Counter(), Counter()
        scalar_names = ("semantic_types", "planned_source_kernels", "materialized_source_kernels",
            "shared_target_relations", "shared_key_projections", "factored_function_rows",
            "unassessed_function_rows", "conditional_function_shape_rows", "withheld_function_shape_rows",
            "terminal_target_rows", "literal_profiles_computed", "actual_endpoint_pairs_computed",
            "motion_groups_computed", "same_bundle_assessments_computed")
        data = trial.load_inputs(self.indexed_parent)
        for row in read_json(self.output / "context-index.json"):
            relation = read_gzip(row["relations"]["artifact"])
            self.assertEqual(row["relation_counts"], relation["summary"])
            summary = relation["summary"]
            self.assertEqual(summary["factored_function_rows"], summary["logical_function_rows"])
            self.assertEqual(summary["unassessed_function_rows"], 0)
            self.assertEqual(sum(summary["shape_state_counts"].values()), summary["logical_function_rows"])
            self.assertEqual(sum(summary["function_kind_counts"].values()), summary["logical_function_rows"])
            self.assertEqual(summary["conditional_function_shape_rows"] + summary["withheld_function_shape_rows"],
                             summary["logical_function_rows"])
            self.assertEqual(summary["materialized_source_kernels"], summary["planned_source_kernels"])
            terminal_rows = 0
            for group in relation["path_groups"]:
                for slot in group["function_slots"]:
                    self.assertEqual(sum(slot["shape_state_counts"].values()), slot["logical_function_rows"])
                    if slot["terminal_target"]:
                        terminal_rows += slot["logical_function_rows"]
                        self.assertEqual(sum(slot["shape_state_counts"][name] for name in ("TU", "FU", "UU")),
                                         slot["logical_function_rows"])
            self.assertEqual(summary["terminal_target_rows"], terminal_rows)
            for name in scalar_names:
                aggregate[name] += summary[name]
            shape_states.update(summary["shape_state_counts"])
            function_kinds.update(summary["function_kind_counts"])
            samples = read_gzip(row["function_samples"]["artifact"])
            self.assertEqual(samples["relations_ref"], frozen._ref(relation))
            parent_row = next(r for r in data["rows"] if r["context_key"] == row["context_key"])
            _, _, _, scope, h, _, index = trial.load_case(data, parent_row)
            expected = []
            for request in indexed_fixture.trial.sample_requests(h, index):
                for slot in range(len(request["variant_ids"])):
                    for family in frozen.FAMILIES:
                        for quality in ("M", "m"):
                            expected.append({**request, "slot_index": slot,
                                             "family": family, "quality": quality})
            self.assertEqual(samples["requests"], expected)
            self.assertEqual(len(samples["queries"]), len(expected))
            variants = {v["variant_id"]: v["variant"] for v in index["variant_inventory"]}
            keys = {k["record_id"]: k for k in index["keys"]}
            for request, query in zip(expected, samples["queries"]):
                position = request["slot_index"]
                ids = request["variant_ids"]
                source = variants[ids[position]]
                target = variants[ids[position + 1]] if position + 1 < len(ids) else None
                wanted = frozen._function(scope, source, target, keys[request["key_id"]]["segments"][0],
                                          request["family"], request["quality"])
                self.assertEqual(query["function"], wanted)
                self.assertNotIn("profiles", query)
                self.assertNotIn("motion", query["function"])
                self.assertNotIn("bundle_inventory", query)
                self.assertIsNone(query.get("selected"))
                self.assertIsNone(query.get("rank"))
                self.assertIsNone(query.get("confidence"))
            for name in ("profiles_evaluated", "motion_evaluated",
                         "all_logical_paths_evaluated", "musical_accuracy_measured"):
                self.assertIs(samples[name], False)
            total_queries += len(expected)
        self.assertGreater(total_queries, 0)
        self.assertEqual(report["summary"]["queried_function_rows"], total_queries)
        self.assertGreater(report["summary"]["logical_function_rows"], total_queries)
        for name in scalar_names:
            self.assertEqual(report["summary"][name], aggregate[name], name)
        self.assertEqual(report["summary"]["shape_state_counts"], dict(shape_states))
        self.assertEqual(report["summary"]["function_kind_counts"], dict(function_kinds))
        for name in ("literal_profiles_computed", "actual_endpoint_pairs_computed",
                     "motion_groups_computed", "same_bundle_assessments_computed"):
            self.assertEqual(report["summary"][name], 0)

    def test_shape_key_stage_does_not_reexecute_old_analysis_profile_or_motion(self):
        with patch("musicanote_harness.factor_functional_trial.evaluate_groups", side_effect=AssertionError("old functional")), \
             patch("musicanote_harness.factor_functional_comparison.compare_functional", side_effect=AssertionError("old comparison")), \
             patch("musicanote_harness.factor_cadence_prerequisites.observe_all_prerequisites", side_effect=AssertionError("old cadence")), \
             patch("musicanote_harness.factor_expanded_hypotheses.build_hypotheses", side_effect=AssertionError("old hypotheses")), \
             patch("musicanote_harness.factor_expanded_hypotheses.evaluate_hypotheses", side_effect=AssertionError("old evaluation")), \
             patch("musicanote_harness.harmony_candidate_catalog.propose", side_effect=AssertionError("old supplier")), \
             patch("musicanote_harness.factor_expanded_hypotheses._profile", side_effect=AssertionError("profile")), \
             patch("musicanote_harness.factor_expanded_hypotheses._motion_options", side_effect=AssertionError("motion")), \
             patch.object(indexed, "query_prepared", side_effect=AssertionError("old tuple query")), \
             patch.object(indexed, "assess_prepared", side_effect=AssertionError("old completion")), \
             patch.object(indexed, "_computed_profile", side_effect=AssertionError("indexed profile")):
            report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertGreater(report["summary"]["queried_function_rows"], 0)

    def test_whole_kernel_hold_keeps_all_origin_and_logical_denominators(self):
        report = self.execute(max_kernels=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_parent_denominators(report)
        self.assertEqual(report["summary"]["queried_function_rows"], 0)
        for row in read_json(self.output / "context-index.json"):
            relation = read_gzip(row["relations"]["artifact"])
            self.assertTrue(relation["origin_inventory"])
            self.assertTrue(relation["type_inventory"])
            self.assertEqual(relation["kernels"], [])
            self.assertEqual(relation["target_relations"], [])
            self.assertEqual(relation["key_projections"], [])
            self.assertGreater(relation["summary"]["planned_source_kernels"], 0)
            self.assertEqual(relation["summary"]["factored_function_rows"], 0)
            self.assertEqual(relation["summary"]["unassessed_function_rows"],
                             relation["summary"]["logical_function_rows"])
            self.assertTrue(all(slot["shape_state_counts"] is None for group in relation["path_groups"]
                                for slot in group["function_slots"]))
            samples = read_gzip(row["function_samples"]["artifact"])
            self.assertTrue(samples["requests"])
            self.assertEqual(len(samples["queries"]), len(samples["requests"]))
            self.assertTrue(all(query["function"] is None and query["computed_function_rows"] == 0
                                for query in samples["queries"]))
        self.assertEqual(report["summary"]["factored_function_rows"], 0)
        self.assertEqual(report["summary"]["unassessed_function_rows"], report["summary"]["logical_function_rows"])

    def test_query_failure_retains_relations_and_known_full_denominators(self):
        with patch("musicanote_harness.factor_function_relations.query_function_prepared",
                   side_effect=ValueError("deliberate function query")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_parent_denominators(report)
        self.assertEqual(report["summary"]["factored_function_rows"], report["summary"]["logical_function_rows"])
        self.assertEqual(report["summary"]["unassessed_function_rows"], 0)
        self.assertEqual(sum(report["summary"]["shape_state_counts"].values()),
                         report["summary"]["logical_function_rows"])
        rows = read_json(self.output / "context-index.json")
        self.assertTrue(all(row["status"] == "calculation_failure" for row in rows))
        self.assertTrue(all(row["relations"] is not None and row["function_samples"] is None for row in rows))

    def test_rehashed_nonempty_query_body_requires_its_actual_seal(self):
        def changed(sample):
            sample["queries"][0]["flags"]["source_labels_used_for_inference"] = True
        self.mutate_samples(changed)
        self.reject_before_output()

    def test_resealed_query_flags_cannot_promote_source_labels(self):
        def changed(sample):
            query = sample["queries"][0]
            query["flags"]["source_labels_used_for_inference"] = True
            query.pop("record_id")
            query.pop("record_sha256")
            query = indexed._seal(query, indexed.QUERY_PREFIX)
            sample["queries"][0] = query
            assessment = sample["same_bundle_comparisons"][0]
            assessment["query_ref"] = frozen._ref(query)
            assessment.pop("record_id")
            assessment.pop("record_sha256")
            sample["same_bundle_comparisons"][0] = indexed._seal(assessment, indexed.ASSESSMENT_PREFIX)
        self.mutate_samples(changed)
        self.reject_before_output()

    def test_resealed_query_count_cannot_disagree_with_saved_function_rows(self):
        def changed(sample):
            query = sample["queries"][0]
            query["computed_counts"]["function_shapes"] = 0
            query.pop("record_id")
            query.pop("record_sha256")
            query = indexed._seal(query, indexed.QUERY_PREFIX)
            sample["queries"][0] = query
            assessment = sample["same_bundle_comparisons"][0]
            assessment["query_ref"] = frozen._ref(query)
            assessment.pop("record_id")
            assessment.pop("record_sha256")
            sample["same_bundle_comparisons"][0] = indexed._seal(assessment, indexed.ASSESSMENT_PREFIX)
        self.mutate_samples(changed)
        self.reject_before_output()

    def test_resealed_assessment_cannot_substitute_a_foreign_control_bundle(self):
        def changed(sample):
            assessment = sample["same_bundle_comparisons"][0]
            assessment["bundle_ref"]["record_id"] = "fmibundle_" + "0" * 24
            assessment.pop("record_id")
            assessment.pop("record_sha256")
            sample["same_bundle_comparisons"][0] = indexed._seal(assessment, indexed.ASSESSMENT_PREFIX)
        self.mutate_samples(changed)
        self.reject_before_output()

    def test_resealed_query_cannot_add_unknown_top_level_fields(self):
        def changed(sample):
            sample["queries"][0]["unregistered_semantic_claim"] = {"accepted": True}
            self.reseal_query_and_comparison(sample)
        self.mutate_samples(changed)
        self.reject_before_output()

    def test_resealed_assessment_cannot_add_unknown_top_level_fields(self):
        def changed(sample):
            comparison = sample["same_bundle_comparisons"][0]
            comparison["unregistered_semantic_claim"] = {"accepted": True}
            comparison.pop("record_id")
            comparison.pop("record_sha256")
            sample["same_bundle_comparisons"][0] = indexed._seal(comparison, indexed.ASSESSMENT_PREFIX)
        self.mutate_samples(changed)
        self.reject_before_output()

    def test_resealed_assessment_cannot_claim_conditional_motion_from_no_link_control(self):
        def changed(sample):
            comparison = sample["same_bundle_comparisons"][0]
            row = comparison["rows"][0]
            self.assertEqual(row["status"], "withheld_under_existing_bundle")
            row["status"] = "conditional_joint_motion_shape_under_existing_bundle"
            row["all_critical_roles_in_same_complete_bundle"] = True
            row["blockers"] = []
            comparison["joint_motion_shape_refs"] = [r["function_id"] for r in comparison["rows"]
                if r["status"] == "conditional_joint_motion_shape_under_existing_bundle"]
            comparison["computed_counts"]["conditional_joint_motion_shapes"] = len(comparison["joint_motion_shape_refs"])
            comparison.pop("record_id")
            comparison.pop("record_sha256")
            sample["same_bundle_comparisons"][0] = indexed._seal(comparison, indexed.ASSESSMENT_PREFIX)
        self.mutate_samples(changed)
        self.reject_before_output()

    def test_resealed_query_cannot_erase_same_bundle_incidence(self):
        def changed(sample):
            self.assertTrue(sample["queries"][0]["same_bundle_assessments"])
            sample["queries"][0]["same_bundle_assessments"] = []
            self.reseal_query_and_comparison(sample)
        self.mutate_samples(changed)
        self.reject_before_output()


if __name__ == "__main__":
    unittest.main()
