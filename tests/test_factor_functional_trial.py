"""Generic key cues, whole budgets and protected append-only trial boundary."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_functional_trial as trial
from musicanote_harness import factor_musical_trial as meaning
from musicanote_harness import harmony_frozen_context_lineage_trial as lineage
from musicanote_harness import factor_musical_view as common
from test_factor_musical_view import make_view, span
from test_musical_role_evidence import make_ir, event
from test_harmony_frozen_context_lineage_trial import fixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class KeyCandidateAndBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ir = make_ir(self.temp.name, [[event("C4", 0, 4)]])

    def view(self):
        return make_view(self.ir, span())

    def test_signature_all_five_candidates_plus_no_final_key(self):
        self.ir["measures"][0]["key_signature"] = {"fifths": 2, "mode_hint": "major"}
        result = trial.key_candidates(self.view())
        segments = [t["segments"][0] for t in result["tracks"]]
        self.assertEqual(len(segments), 5)
        self.assertEqual(segments[0]["tonic"], {"step": "D", "alter": common.q(0)})
        self.assertEqual([s["scale_form"] for s in segments],
            ["major", "natural_minor", "harmonic_minor", "melodic_minor_ascending", "unknown"])
        self.assertEqual(segments[1]["tonic"], {"step": "B", "alter": common.q(0)})
        self.assertIsNone(segments[-1]["tonic"])
        self.assertFalse(result["key_inferred"])
        self.assertFalse(result["mode_hint_used_as_key"])
        self.assertFalse(result["exhaustive_local_key_universe"])

    def test_flat_sharp_circle_spelling_preserved_not_enharmonic(self):
        for fifths, expected in [(-7, ("C", -1)), (-6, ("G", -1)), (-1, ("F", 0)),
                                 (0, ("C", 0)), (6, ("F", 1)), (7, ("C", 1))]:
            self.ir["measures"][0]["key_signature"] = {"fifths": fifths, "mode_hint": None}
            row = trial.key_candidates(self.view())["tracks"][0]["segments"][0]
            self.assertEqual(row["tonic"], {"step": expected[0], "alter": common.q(expected[1])})

    def test_missing_boolean_nonstandard_signature_only_unknown(self):
        for signature in (None, {"fifths": None, "mode_hint": None},
                          {"fifths": True, "mode_hint": None}, {"fifths": 8, "mode_hint": None}):
            self.ir["measures"][0]["key_signature"] = signature
            # Invalid Core-like declarations are deliberate cue-policy probes;
            # a validated view is normally created by the separate adapter.
            raw = self.view_with_mock_signature(signature)
            with patch.object(common, "validate_view", return_value=True):
                result = trial.key_candidates(raw)
            self.assertEqual(result["status"], "unknown_only")
            self.assertEqual(len(result["tracks"]), 1)

    def view_with_mock_signature(self, signature):
        self.ir["measures"][0]["key_signature"] = {"fifths": 0, "mode_hint": None}
        raw = self.view()
        raw["measure_snapshots"][0]["key_signature"] = signature
        return raw

    def test_changing_signature_inside_context_not_first_signature(self):
        self.ir["measures"][0]["key_signature"] = {"fifths": 0, "mode_hint": None}
        raw = self.view()
        first, second = deepcopy(raw["measure_snapshots"][0]), deepcopy(raw["measure_snapshots"][0])
        first["actual_duration_quarter"] = common.q(2)
        second.update(measure_id="second", global_start_quarter=common.q(2),
                      actual_duration_quarter=common.q(2), key_signature={"fifths": 1, "mode_hint": None})
        raw["measure_snapshots"] = [first, second]
        with patch.object(common, "validate_view", return_value=True):
            result = trial.key_candidates(raw)
        self.assertEqual(result["status"], "unknown_only")
        self.assertEqual(len(result["declarations"]), 2)

    def test_outside_measure_declaration_not_used(self):
        self.ir["measures"][0]["key_signature"] = {"fifths": 0, "mode_hint": None}
        raw = self.view()
        extra = deepcopy(raw["measure_snapshots"][0])
        extra.update(measure_id="outside", global_start_quarter=common.q(4),
                     key_signature={"fifths": -5, "mode_hint": None})
        raw["measure_snapshots"].append(extra)
        with patch.object(common, "validate_view", return_value=True):
            result = trial.key_candidates(raw)
        self.assertEqual(result["status"], "signature_compatible_hypotheses_and_unknown")
        self.assertEqual(len(result["declarations"]), 1)

    def test_gap_or_overlapping_measure_cues_leave_key_unknown(self):
        self.ir["measures"][0]["key_signature"] = {"fifths": 0, "mode_hint": None}
        for ambiguous in ("gap", "overlap"):
            raw = self.view()
            if ambiguous == "gap":
                raw["measure_snapshots"][0]["actual_duration_quarter"] = common.q(2)
            else:
                raw["measure_snapshots"].append(deepcopy(raw["measure_snapshots"][0]))
            with patch.object(common, "validate_view", return_value=True):
                result = trial.key_candidates(raw)
            self.assertFalse(result["unambiguous_measure_coverage"])
            self.assertEqual(result["status"], "unknown_only")

    def test_prior_withheld_groups_not_promoted(self):
        group = {"group_id": "old", "status": "withheld_path_budget", "planned_paths": 129,
                 "paths": [], "controls": []}
        with patch.object(trial.functional, "compile_functions", side_effect=AssertionError("must not compile")):
            result = trial.evaluate_group({}, group, {}, [])
        self.assertEqual(result["status"], "withheld_path_budget")
        self.assertEqual(result["overlays"], [])

    def test_pair_and_whole_function_caps_before_compilation(self):
        paths = [{"record_id": "p" + str(i), "segments": [{}, {}]} for i in range(4)]
        group = {"group_id": "new", "status": "paths_prepared", "planned_paths": 4,
                 "paths": paths, "controls": []}
        with patch.object(trial.functional, "compile_functions", side_effect=AssertionError("cap before compilation")):
            pair = trial.evaluate_group({}, group, {"tracks": [{}, {}]}, [], pair_budget=5)
            functional = trial.evaluate_group({}, group, {"tracks": [{}, {}]}, [], functional_budget=159)
            overlays = trial.evaluate_group({}, group, {"tracks": [{}, {}]}, [], overlay_pair_budget=27)
        self.assertEqual(pair["planned_comparison_pairs"], 6)
        self.assertEqual(pair["status"], "withheld_comparison_pair_budget")
        self.assertEqual(functional["planned_function_rows"], 160)
        self.assertEqual(functional["status"], "withheld_whole_function_inventory_budget")
        self.assertEqual(overlays["planned_interpretation_pairs"], 28)
        self.assertEqual(overlays["status"], "withheld_whole_interpretation_pair_budget")

    def test_joint_scope_doubling_is_choices_not_automatic_all_voice_and(self):
        path = {"record_id": "p", "record_sha256": "1" * 64}
        overlay = {"functions": {"path_ref": common.ref(path)},
                   "key_track": {"record_id": "k", "record_sha256": "2" * 64}}
        rows = [{"resolution_id": name, "function_ref": "f", "critical_role": role,
                 "status": "conditional_resolution_shape"}
                for name, role in [("lt1", "leading_tone"), ("lt2", "leading_tone"), ("s7", "seventh")]]
        compiled = {"record_id": "r", "record_sha256": "3" * 64, "rules": rows}
        result = trial._requests([(overlay, compiled)], [(path, [{"rule_id": "n"}])], 10)
        self.assertEqual(result["planned_requests"], 10)  # 3 singleton + 2 pairs, each alone or one NCT
        self.assertEqual(len(result["requests"]), 10)
        self.assertFalse(result["all_multi_rule_subsets_exhaustive"])
        self.assertTrue(all(len(r["requested_resolution_refs"]) <= 2 for r in result["requests"]))
        self.assertFalse(any({x["resolution_id"] for x in r["requested_resolution_refs"]} == {"lt1", "lt2"}
                             for r in result["requests"]))
        held = trial._requests([(overlay, compiled)], [(path, [{"rule_id": "n"}])], 9)
        self.assertEqual(held["requests"], [])
        self.assertEqual(held["planned_requests"], 10)

    def test_output_reuse_nested_and_invalid_budgets_before_read(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "output/old"
            existing.mkdir(parents=True)
            with patch.object(trial, "ROOT", root):
                for output in (root, existing, root / "output/nested/new"):
                    with self.assertRaises(ValueError):
                        trial.run("missing", "missing", "missing", output)
                for budget in (True, 0, -1, 1.5):
                    with self.assertRaises(ValueError):
                        trial.run("missing", "missing", "missing", root / "output/new", request_budget=budget)

    def test_unknown_or_inventory_never_consumes_successful_branch_subset(self):
        branch = {"status": "joint_possible", "completion_bundle": {"record_id": "bundle"}}
        solution = {"status": "unassessed", "all_requested_branches_assessed": False, "branches": [branch]}
        before = deepcopy(solution)
        self.assertEqual(trial._assessed_bundles(solution), [])
        self.assertEqual(solution, before)
        solution["status"] = "joint_possible"
        self.assertEqual(trial._assessed_bundles(solution), [])
        solution["all_requested_branches_assessed"] = True
        self.assertEqual(trial._assessed_bundles(solution), [branch["completion_bundle"]])

    def test_one_group_failure_retains_all_other_groups_and_original_inventory(self):
        groups = [{"group_id": str(i), "status": "paths_prepared", "planned_paths": 10 + i} for i in range(3)]
        with patch.object(trial, "evaluate_group", side_effect=[{"group_id": "0"}, ValueError("bad binding"), {"group_id": "2"}]):
            results, errors = trial.evaluate_groups({}, groups, {}, [])
        self.assertEqual([r["group_id"] for r in results], ["0", "1", "2"])
        self.assertEqual(results[1]["original_status"], "paths_prepared")
        self.assertEqual(results[1]["planned_paths"], 11)
        self.assertEqual(results[1]["status"], "calculation_failure")
        self.assertEqual(errors, ["1:ValueError:bad binding"])


class FrozenFunctionalTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for module in (trial, meaning, lineage):
            self.stack.enter_context(patch.object(module, "ROOT", self.root))
        with redirect_stdout(io.StringIO()):
            lineage.run(self.data["baseline"], self.data["output"])
            self.data["lineage"] = self.data["output"]
            self.data["meaning"] = self.root / "output/meaning"
            meaning.run(self.data["baseline"], self.data["lineage"], self.data["meaning"])
        self.output = self.root / "output/functional"

    def run_fixture(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.data["baseline"], self.data["lineage"], self.data["meaning"], self.output, **kwargs)

    def refresh_meaning(self):
        path = self.data["meaning"] / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def test_all_denominators_statuses_source_and_previous_files_preserved(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.run_fixture()
        self.assertTrue(report["complete"], report)
        previous = read_json(self.data["meaning"] / "report.json")["summary"]
        for key in ("contexts", "raw_lanes", "old_geometry_status_counts", "source_gate_counts"):
            self.assertEqual(report["summary"][key], previous[key])
        for p, content in before.items():
            self.assertEqual(p.read_bytes(), content)
        for p, expected in report["artifact_hashes"].items():
            self.assertEqual(sha(p), expected)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertFalse(report["musical_accuracy_measured"])
        self.assertIsNone(report["selected"])
        self.assertTrue(all(report["summary"][k] == 0 for k in
                        ("human_validated", "training_eligible", "gold_eligible", "generation_ready")))

    def test_no_legacy_engine_or_geometry_recomputation(self):
        with patch("musicanote_harness.harmony_breadth_trial.analyze_sample", side_effect=AssertionError("legacy")), \
             patch("musicanote_harness.harmony_factorized_voice_paths.factorize", side_effect=AssertionError("geometry")), \
             patch("musicanote_harness.harmony_voice_paths.observe", side_effect=AssertionError("independent legacy")):
            report = self.run_fixture()
        self.assertTrue(report["complete"])

    def test_meaning_byte_change_fails_before_new_output(self):
        path = self.data["meaning"] / "context-index.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "input_hash_mismatch"):
            self.run_fixture()
        self.assertFalse(self.output.exists())

    def test_rehashed_meaning_plan_inputs_or_policy_not_trusted(self):
        path = self.data["meaning"] / "run-plan.json"
        original = read_json(path)
        for field, value in [("inputs", {}), ("expected_lanes", -1),
                             ("source_annotation_labels_used", True), ("all_denominators_retained", False)]:
            changed = deepcopy(original)
            changed[field] = value
            write_json(path, changed)
            self.refresh_meaning()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "meaning_plan_input_binding"):
                trial.load_inputs(self.data["baseline"], self.data["lineage"], self.data["meaning"])
        write_json(path, original)
        self.refresh_meaning()

    def test_rehashed_meaning_context_inventory_requires_fresh_full_replay(self):
        index_path = self.data["meaning"] / "context-index.json"
        index = read_json(index_path)
        path = Path(index[0]["artifact"])
        packet = read_gzip(path)
        packet["old_stage_statuses"]["invented"] = "ready"
        write_gzip(path, packet)
        index[0]["sha256"] = sha(path)
        write_json(index_path, index)
        self.refresh_meaning()
        with self.assertRaisesRegex(ValueError, "meaning_context_fresh_candidate_replay"):
            self.run_fixture()


if __name__ == "__main__":
    unittest.main()
