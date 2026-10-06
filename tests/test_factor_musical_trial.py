"""All frozen denominators and exact candidate budgets survive the new layer."""
from copy import deepcopy
from contextlib import redirect_stdout
from fractions import Fraction
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_musical_trial as trial
from musicanote_harness import harmony_frozen_context_lineage_trial as lineage
from musicanote_harness.factor_musical_view import prepare, span_bounds, q
from musicanote_harness.musical_pattern_observation import digest
from test_harmony_frozen_context_lineage_trial import fixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class CandidateGroupsTests(unittest.TestCase):
    def test_exact_decimal_or_rational_alter_preserved(self):
        self.assertEqual(trial._alter(.5), q(Fraction(1, 2)))
        self.assertEqual(trial._alter(q(Fraction(-1, 2))), q(Fraction(-1, 2)))
        with self.assertRaises(ValueError):
            trial._alter(True)

    def test_negative_or_boolean_path_budget_rejected(self):
        for value in (-1, 0, True, 1.5):
            with self.assertRaises(ValueError):
                trial.path_groups({}, {}, path_budget=value)

    def test_missing_old_lattice_plan_is_explicit_withheld_not_invented(self):
        view = {"context_span": {"start": q(0), "end": q(4)}}
        old = {"status": "baseline_abstention", "reason": "original budget"}
        groups = trial.path_groups(view, old)
        self.assertEqual(groups[0]["status"], "withheld_stored_lattice_no_plan")
        self.assertIsNone(groups[0]["planned_paths"])
        self.assertEqual(groups[0]["old_lattice_payload"], old)
        with self.assertRaises(ValueError):
            trial.path_groups(view, {"status": "ready"})

    def test_joint_pair_cap_checked_before_combinations_materialization(self):
        group = {"group_id": "mock_group", "status": "paths_prepared", "planned_paths": 1,
                 "paths": [{}], "controls": []}
        compiled = {"rules": [{"status": "conditional_shape", "alternatives": []} for _ in range(2000)]}
        with patch.object(trial, "compile_rules", return_value=compiled), \
             patch.object(trial, "query", return_value={}), \
             patch.object(trial, "materialize_witness", return_value={}), \
             patch.object(trial, "compare_under_completion", return_value={"accounts": []}), \
             patch.object(trial, "combinations", side_effect=AssertionError("cap before allocation")):
            result = trial.evaluate_group({}, group, {"status": "ready"}, joint_pair_budget=256)
        self.assertEqual(result["planned_joint_pairs"], 1999000)
        self.assertEqual(result["joint_pair_status"], "withheld_joint_pair_budget_no_partial_sampling")

    def test_new_output_and_positive_budget_required_before_reads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "output/existing"
            existing.mkdir(parents=True)
            with patch.object(trial, "ROOT", root):
                for target in (root, existing, root / "output/nested/new"):
                    with self.assertRaises(ValueError):
                        trial.run("missing", "missing", target)
                with self.assertRaises(ValueError):
                    trial.run("missing", "missing", root / "output/new", witness_budget=0)


class FrozenMusicalTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)
        with patch.object(lineage, "ROOT", self.root), redirect_stdout(io.StringIO()):
            lineage.run(self.data["baseline"], self.data["output"])
        self.data["lineage"] = self.data["output"]
        self.output = self.root / "output/meaning"
        for module in (trial, lineage):
            ctx = patch.object(module, "ROOT", self.root)
            ctx.start()
            self.addCleanup(ctx.stop)

    def run_fixture(self, **options):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.data["baseline"], self.data["lineage"], self.output, **options)

    def refresh_manifests(self, *, baseline=False):
        """Mutations below cross byte manifests, exercising content guards."""
        if baseline:
            path = self.data["baseline"] / "report.json"
            report = read_json(path)
            report["artifact_hashes"] = {name: sha(name) for name in report["artifact_hashes"]}
            write_json(path, report)
            path = self.data["lineage"] / "run-plan.json"
            plan = read_json(path)
            plan["inputs"] = deepcopy(lineage._inputs(self.data["baseline"])["hashes"])
            write_json(path, plan)
        path = self.data["lineage"] / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {name: sha(name) for name in report["artifact_hashes"]}
        write_json(path, report)

    def loaded_context(self):
        data = trial.load_inputs(self.data["baseline"], self.data["lineage"])
        key = next(iter(data["contexts"]))
        observation = read_json(data["contexts"][key]["path"])
        return data, key, observation

    def test_every_context_lane_preserved_and_inputs_immutable(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.run_fixture()
        self.assertTrue(report["complete"], report)
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertTrue(report["artifacts_unchanged"])
        old = read_json(self.data["baseline"] / "report.json")["summary"]
        self.assertEqual(report["summary"]["contexts"], old["contexts"])
        self.assertEqual(report["summary"]["raw_lanes"], old["raw_lane_units"])
        self.assertEqual(report["summary"]["old_geometry_status_counts"], old["status_counts"])
        for p, content in before.items():
            self.assertEqual(p.read_bytes(), content)
        for p, expected in report["artifact_hashes"].items():
            self.assertEqual(sha(p), expected)
        actual = {str(p.resolve()) for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(actual, set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertIsNone(report["selected"])
        for key in ("human_validated", "training_eligible", "gold_eligible", "generation_ready"):
            self.assertEqual(report["summary"][key], 0)
        original = {tuple(r["context_key"]): r for r in
                    read_json(self.data["baseline"] / "observation-index.json")}
        for row in read_json(self.output / "context-index.json"):
            context = read_gzip(row["artifact"])
            prior = original[tuple(row["context_key"])]
            self.assertEqual(context["old_stage_statuses"], prior["original_stage_statuses"])
            self.assertEqual(context["original_final_status"], prior["original_final_status"])

    def test_lineage_bytes_change_rejected_before_output(self):
        p = self.data["lineage"] / "gate-index.json"
        p.write_bytes(p.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "input_hash_mismatch"):
            self.run_fixture()
        self.assertFalse(self.output.exists())

    def test_no_source_or_legacy_engine_recomputed(self):
        actual_observation = lineage._observation
        def lightweight(*args, **kwargs):
            self.assertIs(kwargs.get("literal"), False)
            return actual_observation(*args, **kwargs)
        with patch("musicanote_harness.harmony_breadth_trial.analyze_sample", side_effect=AssertionError("old engine")), \
             patch("musicanote_harness.harmony_voice_paths.observe", side_effect=AssertionError("legacy")), \
             patch("musicanote_harness.harmony_factorized_voice_paths.factorize", side_effect=AssertionError("geometry rerun")), \
             patch.object(lineage, "_observation", side_effect=lightweight):
            report = self.run_fixture()
        self.assertTrue(report["complete"])

    def test_rehashed_lineage_plan_binding_and_policy_mutations_rejected(self):
        path = self.data["lineage"] / "run-plan.json"
        original = read_json(path)
        mutations = [("version", "unknown"), ("inputs", {}), ("expected_context_keys", []),
                     ("expected_raw_lane_units", -1), ("geometry_recomputed", True),
                     ("old_engines_or_selector_recomputed", True), ("source_xml_inspected", True),
                     ("source_labels_used_for_inference", True)]
        for field, value in mutations:
            changed = deepcopy(original)
            changed[field] = value
            write_json(path, changed)
            self.refresh_manifests()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "lineage_plan_baseline"):
                trial.load_inputs(self.data["baseline"], self.data["lineage"])
        write_json(path, original)
        self.refresh_manifests()

    def test_rehashed_audit_index_ref_hash_and_observation_mutations_rejected(self):
        path = self.data["lineage"] / "audit-index.json"
        original = read_json(path)
        for field, value in [("sha256", "0" * 64), ("audit_ref", {"record_id": "fake", "record_sha256": "0" * 64}),
                             ("observation_ref", {"record_id": "fake", "record_sha256": "0" * 64}),
                             ("error", "injected"), ("source_clock_consistency_passed", False)]:
            changed = deepcopy(original)
            changed[0][field] = value
            write_json(path, changed)
            self.refresh_manifests()
            data, key, obs = self.loaded_context()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "lineage_audit_index_or_packet"):
                trial._audit_packet(data, key, obs)
        write_json(path, original)
        self.refresh_manifests()

    def test_rehashed_audit_packet_version_baseline_and_promotion_rejected(self):
        index_path = self.data["lineage"] / "audit-index.json"
        original_index = read_json(index_path)
        path = Path(original_index[0]["artifact"])
        original = read_json(path)
        for field, value in [("version", "unknown"), ("baseline_observation_file_sha256", "0" * 64),
                             ("baseline_observation_artifact", "foreign"), ("selected", "winner"),
                             ("semantic_eligible", True), ("training_eligible", True),
                             ("generation_ready", True), ("error", "injected")]:
            changed = deepcopy(original)
            changed[field] = value
            write_json(path, changed)
            index = deepcopy(original_index)
            index[0]["sha256"] = sha(path)
            write_json(index_path, index)
            self.refresh_manifests()
            data, key, obs = self.loaded_context()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "lineage_audit_index_or_packet"):
                trial._audit_packet(data, key, obs)
        write_json(path, original)
        write_json(index_path, original_index)
        self.refresh_manifests()

    def test_rehashed_gate_exact_geometry_lineage_and_policy_rejected(self):
        path = self.data["lineage"] / "gate-index.json"
        original = read_json(path)
        mutations = [("baseline_unit_content_sha256", "0" * 64), ("geometry_result_content_sha256", "0" * 64),
                     ("baseline_unit_file_sha256", "0" * 64), ("geometry_reasons", ["invented"]),
                     ("original_final_status", "invented"), ("original_stage_statuses", {}),
                     ("audit_file_sha256", "0" * 64), ("audit_artifact", "foreign"),
                     ("audit_ref", {"record_id": "fake", "record_sha256": "0" * 64}),
                     ("affected_selected_lane_sound_refs", ["fake"]), ("geometry_result_preserved", False),
                     ("geometry_recomputed", True), ("semantic_eligible", True), ("training_eligible", True),
                     ("gold_eligible", True), ("generation_ready", True), ("selected", "winner")]
        for field, value in mutations:
            changed = deepcopy(original)
            changed[0][field] = value
            write_json(path, changed)
            self.refresh_manifests()
            data, key, obs = self.loaded_context()
            audit = trial._audit_packet(data, key, obs)
            lane = changed[0]["lane"]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "lineage_gate_exact_metadata"):
                trial._baseline_unit(data, key, obs, lane, audit)
        write_json(path, original)
        self.refresh_manifests()

    def test_rehashed_baseline_unit_status_and_promotion_rejected(self):
        index_path = self.data["baseline"] / "unit-index.json"
        original_index = read_json(index_path)
        path = Path(original_index[0]["artifact"])
        original = read_gzip(path)
        for field, value in [("version", "unknown"), ("original_final_status", "invented"),
                             ("original_stage_statuses", {}), ("selected", "winner"),
                             ("harmonic_or_role_claim", True), ("training_eligible", True),
                             ("generation_ready", True)]:
            changed = deepcopy(original)
            changed[field] = value
            write_gzip(path, changed)
            index = deepcopy(original_index)
            index[0]["sha256"] = sha(path)
            write_json(index_path, index)
            self.refresh_manifests(baseline=True)
            data, key, obs = self.loaded_context()
            audit = trial._audit_packet(data, key, obs)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "baseline_unit_index_or_packet"):
                trial._baseline_unit(data, key, obs, original_index[0]["lane"], audit)
        write_gzip(path, original)
        original_index[0]["sha256"] = sha(path)
        write_json(index_path, original_index)
        self.refresh_manifests(baseline=True)

    def test_rehashed_observation_index_reference_is_not_trusted(self):
        path = self.data["baseline"] / "observation-index.json"
        rows = read_json(path)
        rows[0]["record_sha256"] = "0" * 64
        write_json(path, rows)
        self.refresh_manifests(baseline=True)
        data = trial.load_inputs(self.data["baseline"], self.data["lineage"])
        pair = next(iter(data["packages"]))
        historical, ir, revision = lineage._working_case(data, pair)
        key = next(iter(data["contexts"]))
        with self.assertRaisesRegex(ValueError, "observation_index_binding_mismatch"):
            lineage._observation(data, key, historical, ir, revision, literal=False)

    def test_path_budget_withholds_entire_named_group_without_losing_lane(self):
        report = self.run_fixture(path_budget=1)
        self.assertTrue(report["complete"])
        contexts = read_json(self.output / "context-index.json")
        groups = [g for r in contexts for g in lineage.read(r["artifact"], compressed=True)["groups"]]
        held = [g for g in groups if g["status"] == "withheld_path_budget"]
        self.assertTrue(held)
        self.assertTrue(all(g["paths"] == [] and g["planned_paths"] > 1 for g in held))
        self.assertEqual(report["summary"]["raw_lanes"],
                         read_json(self.data["baseline"] / "report.json")["summary"]["raw_lane_units"])

    def test_creation_time_output_replacement_detected(self):
        original = trial._save
        replaced = False
        def save(output, relative, value, artifacts, **kwargs):
            nonlocal replaced
            result = original(output, relative, value, artifacts, **kwargs)
            if not replaced and relative.startswith("units/"):
                result.write_bytes(result.read_bytes() + b"extra")
                replaced = True
            return result
        with patch.object(trial, "_save", side_effect=save):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertFalse(report["artifacts_unchanged"])
        self.assertTrue(report["changed_artifacts"])

    def test_evaluator_mutation_is_fatal_not_normal_failed_case(self):
        def mutate(view, group, graph, **kwargs):
            view["context_span"]["end"] = q(12345)
            raise ValueError("injected")
        with patch.object(trial, "evaluate_group", side_effect=mutate), self.assertRaisesRegex(ValueError, "inputs_mutated"):
            self.run_fixture()


if __name__ == "__main__":
    unittest.main()
