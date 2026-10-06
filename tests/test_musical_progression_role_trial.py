from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_progression_context as progression_context
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness import musical_progression_role_trial as trial
from musicanote_harness.musical_progression_role_link import validate_link
from musicanote_harness.musical_role_evidence import validate_evidence
import test_musical_role_evidence as literal_fixture
import test_musical_role_evidence_trial as parent_fixture


def held_unit(lane, reason="synthetic isolated unit hold"):
    return {"lane": deepcopy(lane), "status": "synthetic_abstention", "reasons": [reason],
            "links": [], "planned_role_links": None,
            "role_link_inventory_complete": False, "selected": None}


class MusicalProgressionRoleTrialTests(unittest.TestCase):
    def setUp(self):
        # Compose the independently generated, sealed G1 parent fixture without
        # inheriting or rediscovering that module's tests or altering its files.
        self.parent = parent_fixture.MusicalRoleEvidenceTrialTests(
            methodName="test_existing_output_is_rejected_without_overwriting_marker")
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.root = self.parent.root
        self.alignment = self.parent.alignment
        self.destination = self.root / "output/progression-run"
        self.root_patch = patch.object(trial, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def unit_fixture(self, name, lanes):
        folder = self.root / name
        folder.mkdir()
        ir = literal_fixture.make_ir(folder, lanes)
        observation = pattern.observe(ir, literal_fixture.scope_for(ir))
        lane = [observation["raw_lanes"][0][key] for key in ("part_id", "voice_id")]
        score = folder / "score.musicxml"
        policy = trial.source_transposition(score)
        policy.update(source_path=str(score), source_sha256=trial.file_digest(score),
                      ir_content_sha256=pattern.digest(ir), pitch_basis="written_IR_not_concert_certified")
        return ir, observation, lane, policy

    def config(self, **options):
        return {**trial.DEFAULT_CONFIG, "max_segments": 2, "max_complete_paths": 2, **options}

    def read_units(self, destination=None):
        return parent_fixture.read_json((destination or self.destination) / "unit-index.json")

    def test_unit_normal_links_every_proposal_assignment_without_source_rn_provider(self):
        ir, observation, lane, policy = self.unit_fixture("normal", [
            [literal_fixture.event(["C4", "E4", "G4"], 0, 4)],
            [literal_fixture.event("C2", 0, 4)]])
        original = deepcopy((ir, observation, lane, policy))
        with (
                patch.object(progression_context, "propose", wraps=progression_context.propose) as provider,
                patch.object(trial, "prepare_context", wraps=trial.prepare_context) as preparer,
                patch.object(trial, "link_prepared", wraps=trial.link_prepared) as linker,
                patch.object(trial, "validate_link_prepared", wraps=trial.validate_link_prepared) as validator):
            unit = trial._unit(ir, observation, lane, policy, self.config())
        self.assertEqual((ir, observation, lane, policy), original)
        self.assertEqual(unit["status"], "conditional_links_not_verdict")
        self.assertTrue(unit["role_link_inventory_complete"])
        self.assertIsNone(unit["selected"])
        self.assertFalse(unit["musical_accuracy_measured"])
        proposals = unit["search"]["proposals"]
        assignments = unit["voice_inventory"]["assignments"]
        self.assertTrue(proposals)
        self.assertEqual(unit["planned_role_links"], len(proposals) * len(assignments))
        self.assertEqual(len(unit["links"]), unit["planned_role_links"])
        preparer.assert_called_once()
        self.assertEqual(linker.call_count, unit["planned_role_links"])
        self.assertEqual(validator.call_count, unit["planned_role_links"])
        expected_pairs = [(proposal["proposal_id"], assignment["assignment_id"])
                          for proposal in proposals for assignment in assignments]
        self.assertEqual([(call.args[1]["proposal_id"], call.args[2])
                          for call in linker.call_args_list], expected_pairs)
        prepared = linker.call_args_list[0].args[0]
        self.assertTrue(all(call.args[0] is prepared for call in linker.call_args_list))
        self.assertTrue(all(call.args[1] is prepared for call in validator.call_args_list))
        lattice = unit["bundle"]["stages"]["lattice"]
        self.assertEqual({row["sounding_event_id"] for row in lattice["events"]},
                         {row["sounding_event_id"] for row in ir["sounding_events"]})
        expected_lanes = {(row["part_id"], row["voice_id"]) for row in observation["raw_lanes"]}
        proposal_by_id = {row["proposal_id"]: row for row in proposals}
        self.assertFalse(unit["bundle"]["source_labels_used"])
        self.assertFalse(lattice["source_labels_used"])
        self.assertIsNone(unit["bundle"]["selected"])
        for value in unit["links"]:
            nested = value["role_evidence"]
            self.assertEqual({(row["lane"]["part_id"], row["lane"]["voice_id"])
                              for row in nested["literal"]["pitch_episodes"]}, expected_lanes)
            self.assertFalse(value["semantics"]["assignments_merged"])
            self.assertFalse(value["semantics"]["harmony_selected"])
            self.assertFalse(value["semantics"]["roles_validated"])
            self.assertIsNone(value["harmony_assumption_track"]["provenance"]["source_document_sha256"])
            validate_link(value, ir=ir, observation=observation, bundle=unit["bundle"],
                          proposal=proposal_by_id[value["proposal"]["proposal_id"]],
                          assignment_ref=value["shared_assignment"]["assignment_id"], pitch_policy=policy,
                          search_result=unit["search"])
        self.assertTrue(provider.called)
        for call in provider.call_args_list:
            self.assertEqual(len(call.args), 3)
            self.assertIs(call.args[0], ir)
            self.assertEqual(call.args[2], observation["scope"]["context_span"])
            self.assertEqual(call.kwargs, {})
            self.assertNotIn("source_statement_ref", call.args[1])

    def test_assignment_and_role_link_budgets_hold_entire_unit_without_subset(self):
        ir, observation, lane, policy = self.unit_fixture("budget", [[
            literal_fixture.event("C4", 0, 1), literal_fixture.event("E4", 1, 1),
            literal_fixture.event("G4", 2, 2)]])
        with (patch.object(trial, "prepare_context") as preparer,
              patch.object(trial, "link_prepared") as linker,
              patch.object(trial, "build_lattice") as builder):
            unit = trial._unit(ir, observation, lane, policy, self.config(max_assignments=1))
        self.assertEqual(unit["status"], "assignment_budget_abstention")
        self.assertIn("entire_assignment_inventory_held_before_candidate_computation", unit["reasons"])
        self.assertGreater(len(unit["voice_inventory"]["assignments"]), 1)
        self.assertIsNone(unit["planned_role_links"])
        self.assertIsNone(unit["bundle"])
        self.assertIsNone(unit["search"])
        self.assertEqual(unit["links"], [])
        self.assertFalse(unit["role_link_inventory_complete"])
        builder.assert_not_called()
        preparer.assert_not_called()
        linker.assert_not_called()
        with (patch.object(trial, "prepare_context") as preparer,
              patch.object(trial, "link_prepared") as linker):
            unit = trial._unit(ir, observation, lane, policy, self.config(max_role_links=1))
        self.assertEqual(unit["status"], "role_link_budget_abstention")
        self.assertGreater(unit["planned_role_links"], 1)
        self.assertEqual(unit["links"], [])
        self.assertFalse(unit["role_link_inventory_complete"])
        self.assertIn("entire_proposal_assignment_inventory_held_no_subset", unit["reasons"])
        preparer.assert_not_called()
        linker.assert_not_called()
        self.assertGreater(len(unit["voice_inventory"]["assignments"]), 1)

    def test_voice_endpoint_hold_and_rest_only_lane_are_not_dropped(self):
        ir, observation, lane, policy = self.unit_fixture("voice-hold", [[
            literal_fixture.event(["C4", "D4", "E4", "F4", "G4"], 0, 2),
            literal_fixture.event(["C4", "D4", "E4", "F4", "G4"], 2, 2)]])
        with patch.object(trial, "build_lattice") as builder:
            unit = trial._unit(ir, observation, lane, policy, self.config())
        self.assertEqual(unit["status"], "voice_inventory_abstention")
        self.assertIn("endpoint_limit_no_pruning", unit["reasons"])
        self.assertEqual(unit["links"], [])
        self.assertFalse(unit["voice_inventory"]["enumeration_complete"])
        builder.assert_not_called()
        ir, observation, _, policy = self.unit_fixture("rest-lane", [
            [literal_fixture.event("C4", 0, 4)], [literal_fixture.event(None, 0, 4)]])
        rest = ir["rest_events"][0]
        lane = [rest["part_id"], rest["voice_id"]]
        self.assertIn({"part_id": lane[0], "voice_id": lane[1]},
                      [{key: row[key] for key in ("part_id", "voice_id")} for row in observation["raw_lanes"]])
        unit = trial._unit(ir, observation, lane, policy, self.config())
        self.assertEqual(unit["lane"], lane)
        self.assertEqual(unit["status"], "voice_inventory_abstention")
        self.assertIn("empty_lane", unit["reasons"])

    def test_edge_budget_hold_keeps_complete_geometry_and_emits_no_links(self):
        ir, observation, lane, policy = self.unit_fixture("edge-hold", [[
            literal_fixture.event("C4", 0, 1), literal_fixture.event("E4", 1, 1),
            literal_fixture.event("G4", 2, 2)]])
        with (patch.object(trial, "prepare_context") as preparer,
              patch.object(trial, "link_prepared") as linker):
            unit = trial._unit(ir, observation, lane, policy, self.config(max_edges=1))
        self.assertEqual(unit["status"], "lattice_abstention")
        self.assertEqual(unit["reasons"], ["edge_budget_abstention_no_pruning"])
        self.assertEqual(unit["links"], [])
        lattice = unit["bundle"]["stages"]["lattice"]
        self.assertEqual(len(lattice["events"]), len(ir["sounding_events"]))
        self.assertEqual(lattice["edges"], [])
        self.assertGreater(len(lattice["plan"]["intervals"]), 1)
        preparer.assert_not_called()
        linker.assert_not_called()

    def test_pitch_and_grace_holds_happen_before_voice_enumeration(self):
        ir, observation, lane, policy = self.unit_fixture("grace-hold", [[
            literal_fixture.event("B3", 0, 0, grace=True), literal_fixture.event("C4", 0, 4)]])
        for allowed, status, reason in (
                (False, "source_pitch_abstention", "source_transposition_not_supported"),
                (True, "grace_context_abstention", "legacy_progression_geometry_does_not_support_grace_points")):
            held_policy = {**policy, "harmonic_replay_allowed": allowed}
            with self.subTest(allowed=allowed), patch.object(trial, "observe_voice") as observer:
                unit = trial._unit(ir, observation, lane, held_policy, self.config())
            self.assertEqual(unit["status"], status)
            self.assertEqual(unit["reasons"], [reason])
            self.assertEqual(unit["links"], [])
            self.assertIsNone(unit["voice_inventory"])
            observer.assert_not_called()

    def test_run_preserves_every_raw_lane_and_manifest_without_source_importer(self):
        original_files = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with patch.object(parent_fixture.trial, "import_romantext", side_effect=AssertionError("source RN forbidden")) as importer:
            report = trial.run(self.alignment, self.destination, max_edges=1)
        importer.assert_not_called()
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["observations"], 2)
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(report["summary"]["role_link_instances"], 0)
        self.assertEqual(report["summary"]["status_counts"], {"lattice_abstention": 4})
        expected = {(row["record_id"], (lane["part_id"], lane["voice_id"]))
                    for row, observation in zip(self.parent.index, self.parent.observations)
                    for lane in observation["raw_lanes"]}
        rows = self.read_units()
        self.assertEqual({(row["observation_ref"]["record_id"], tuple(row["lane"])) for row in rows}, expected)
        for row in rows:
            self.assertEqual(trial.file_digest(row["artifact"]), row["sha256"])
            packet = json.loads(gzip.decompress(Path(row["artifact"]).read_bytes()).decode("utf-8"))
            self.assertEqual(packet["unit"]["lane"], row["lane"])
            self.assertFalse(packet["source_labels_used_for_inference"])
            self.assertFalse(packet["training_eligible"])
            self.assertFalse(packet["generation_ready"])
            self.assertIsNone(packet["selected"])
        literal_paths = list(self.destination.glob("observations/*/literal-role-evidence.json"))
        self.assertEqual(len(literal_paths), 2)
        for path in literal_paths:
            evidence = parent_fixture.read_json(path)
            observation = next(row for row in self.parent.observations
                               if trial.ref(row) == evidence["observation_ref"])
            validate_evidence(evidence, ir=self.parent.ir, observation=observation, tracks=[])
            self.assertEqual(evidence["conditional"], [])
        plan = parent_fixture.read_json(self.destination / "run-plan.json")
        self.assertEqual(plan["harmony_source"], "label_blind_existing_candidate_catalog_not_source_RomanText")
        self.assertFalse(plan["source_labels_used_for_inference"])
        self.assertEqual(plan["config"]["max_edges"], 1)
        self.assertEqual(len(plan["pattern_refs"]), 2)
        self.assertEqual(len(plan["code"]), 3)
        for path, payload in original_files.items():
            self.assertEqual(Path(path).read_bytes(), payload)
        for path, digest in report["artifact_hashes"].items():
            self.assertEqual(trial.file_digest(path), digest)

    def test_incomplete_source_transpose_declaration_holds_every_lane_not_implicit_zero(self):
        declaration = {"harmonic_replay_allowed": True, "source_transpose_elements": [{"diatonic": "0"}]}
        with patch.object(trial, "source_transposition", return_value=declaration) as probe:
            report = trial.run(self.alignment, self.destination)
        self.assertEqual(probe.call_count, 1)
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(report["summary"]["status_counts"], {"source_pitch_abstention": 4})
        self.assertEqual(len(self.read_units()), 4)
        for row in self.read_units():
            packet = json.loads(gzip.decompress(Path(row["artifact"]).read_bytes()).decode("utf-8"))
            self.assertFalse(packet["pitch_policy"]["harmonic_replay_allowed"])
            self.assertEqual(packet["pitch_policy"]["reason"], "incomplete_source_transpose_declaration")
            self.assertEqual(packet["unit"]["links"], [])
            self.assertIsNone(packet["unit"]["voice_inventory"])

    def test_output_existing_root_outside_and_nested_paths_are_rejected(self):
        self.destination.mkdir()
        marker = self.destination / "marker.txt"
        marker.write_text("preserve", encoding="utf-8")
        for destination in (self.destination, self.root / "output", self.root / "outside-run",
                            self.alignment / "nested-run"):
            with self.subTest(destination=destination), self.assertRaisesRegex(ValueError, "new_workspace_output"):
                trial.run(self.alignment, destination)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        self.assertEqual(list(self.destination.iterdir()), [marker])
        self.assertFalse((self.root / "outside-run").exists())
        self.assertFalse((self.alignment / "nested-run").exists())

    def test_unknown_boolean_nonpositive_and_noninteger_budgets_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown_role_trial_option"):
            trial.run(self.alignment, self.destination, invented_budget=1)
        for value in (True, False, 0, -1, 1.5, None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "invalid_role_trial_budget"):
                trial.run(self.alignment, self.destination, max_role_links=value)
            self.assertFalse(self.destination.exists())

    def test_parent_inventory_and_observation_denominator_mismatches_fail_before_write(self):
        original = self.parent.analysis.read_bytes()
        for mode, reason in (("changed", "upstream_artifact_changed"),
                             ("missing", "inventory_mismatch"),
                             ("extra", "inventory_mismatch")):
            extra = self.alignment / "unregistered.txt"
            if mode == "changed":
                self.parent.analysis.write_bytes(original + b"\nNote: changed\n")
            elif mode == "missing":
                self.parent.analysis.unlink()
            else:
                extra.write_text("unregistered", encoding="utf-8")
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, reason):
                trial.run(self.alignment, self.destination)
            self.assertFalse(self.destination.exists())
            self.parent.analysis.write_bytes(original)
            if extra.exists():
                extra.unlink()
        report_path = self.alignment / "report.json"
        report = parent_fixture.read_json(report_path)
        report["summary"]["literal_pattern_observations"] = 3
        parent_fixture.write_json(report_path, report)
        with self.assertRaisesRegex(ValueError, "pattern_denominator_mismatch"):
            trial.run(self.alignment, self.destination)
        self.assertFalse(self.destination.exists())

    def test_missing_source_alignment_binding_is_refused(self):
        parent_fixture.write_json(self.alignment / "alignment-attempts.json", self.parent.attempts[1:])
        self.parent.refresh_parent_report()
        with self.assertRaisesRegex(ValueError, "missing_or_duplicate_observation_source_or_alignment"):
            trial.run(self.alignment, self.destination, max_edges=1)
        self.assertFalse((self.destination / "report.json").exists())

    def test_unit_exception_retains_all_observation_lane_denominator_rows(self):
        with patch.object(trial, "_unit", side_effect=ValueError("synthetic unit failure")) as unit:
            report = trial.run(self.alignment, self.destination)
        self.assertEqual(unit.call_count, 4)
        self.assertFalse(report["complete"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertFalse(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(report["summary"]["status_counts"], {"integrity_or_computation_abstention": 4})
        self.assertEqual(len(self.read_units()), 4)
        self.assertTrue(all("synthetic unit failure" in row["reasons"][0] for row in self.read_units()))
        self.assertTrue(all(row["links"] == 0 for row in self.read_units()))
        literal_paths = list(self.destination.glob("observations/*/literal-role-evidence.json"))
        self.assertEqual(len(literal_paths), 2)
        for path in literal_paths:
            evidence = parent_fixture.read_json(path)
            observation = next(row for row in self.parent.observations
                               if trial.ref(row) == evidence["observation_ref"])
            validate_evidence(evidence, ir=self.parent.ir, observation=observation, tracks=[])

    def test_unit_mutation_of_ir_or_observation_aborts_without_complete_report(self):
        for mode in ("ir", "observation"):
            destination = self.root / "output" / ("mutation-" + mode)

            def mutate(ir, observation, lane, policy, config):
                if mode == "ir":
                    ir["score"]["metadata"]["mutated_by_unit"] = True
                else:
                    observation["scope"]["case_id"] = "mutated-by-unit"
                return held_unit(lane)

            with self.subTest(mode=mode), patch.object(trial, "_unit", side_effect=mutate):
                with self.assertRaisesRegex(ValueError, "mutated_ir_or_observation"):
                    trial.run(self.alignment, destination)
            self.assertFalse((destination / "report.json").exists())

    def test_external_input_change_during_run_marks_report_incomplete(self):
        calls = []

        def external_change(ir, observation, lane, policy, config):
            if not calls:
                self.parent.analysis.write_text(self.parent.analysis.read_text(encoding="utf-8") +
                                                "Note: external edit during unit\n", encoding="utf-8")
            calls.append(lane)
            return held_unit(lane)

        with patch.object(trial, "_unit", side_effect=external_change):
            report = trial.run(self.alignment, self.destination)
        self.assertFalse(report["complete"])
        self.assertIn(str(self.parent.analysis), report["changed_inputs_or_code"])
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(len(self.read_units()), 4)

    def test_code_schema_and_upstream_inventory_changes_mark_report_incomplete(self):
        for mode in ("content", "inventory", "schema", "upstream"):
            destination = self.root / "output" / ("code-change-" + mode)
            calls = []

            def change_code(ir, observation, lane, policy, config):
                if not calls:
                    if mode == "content":
                        path = self.parent.code_path
                        path.write_text(path.read_text(encoding="utf-8") + "# external edit\n", encoding="utf-8")
                    elif mode == "inventory":
                        path = self.parent.code_path.parent / "new_after_manifest.py"
                        path.write_text("# external new source\n", encoding="utf-8")
                    elif mode == "schema":
                        path = self.root / "docs/harmony/schemas/new_after_manifest.schema.json"
                        parent_fixture.write_json(path, {})
                    else:
                        path = self.alignment / "new_after_manifest.txt"
                        path.write_text("external new parent artifact\n", encoding="utf-8")
                calls.append(lane)
                return held_unit(lane)

            with self.subTest(mode=mode), patch.object(trial, "_unit", side_effect=change_code):
                report = trial.run(self.alignment, destination)
            self.assertFalse(report["complete"])
            expected = {"content": str(self.parent.code_path),
                        "inventory": "source_or_schema_inventory_changed",
                        "schema": "source_or_schema_inventory_changed",
                        "upstream": "upstream_artifact_inventory_changed"}[mode]
            self.assertIn(expected, report["changed_inputs_or_code"])
            self.assertEqual(report["summary"]["raw_lane_units"], 4)
            self.assertEqual(len(self.read_units(destination)), 4)


if __name__ == "__main__":
    unittest.main()
