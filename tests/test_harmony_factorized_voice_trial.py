from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from music21 import converter, meter, note, stream

from musicanote_harness import harmony_factorized_voice_trial as trial
from musicanote_harness import harmony_polyphonic_links as polyphonic
from musicanote_harness import harmony_voice_paths as legacy
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness.harmony_path_contrast import token
import test_musical_role_evidence as literal_fixture
import test_musical_role_evidence_trial as parent_fixture


def write_gzip(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    path.write_bytes(gzip.compress(raw, mtime=0))


def read_gzip(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()).decode("utf-8"))


class HarmonyFactorizedVoiceTrialTests(unittest.TestCase):
    def setUp(self):
        # Reuse independently generated SOURCE/coordinate records, never a
        # production corpus or mocks of parent validation and hash checks.
        self.parent = parent_fixture.MusicalRoleEvidenceTrialTests(
            methodName="test_existing_output_is_rejected_without_overwriting_marker")
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.root = self.parent.root
        self.alignment = self.parent.alignment
        self.baseline = self.root / "output/rolebase"
        self.destination = self.root / "output/factor-run"
        root_patch = patch.object(trial, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.make_baseline()

    def make_baseline(self):
        self.baseline.mkdir(exist_ok=True)
        inputs, _ = trial._inputs(self.alignment)
        # Actual producer source is protected; tests do not alter it. ROOT's
        # three isolated manifest fixtures are the new runner's own inventory.
        source = Path(trial.__file__).resolve()
        parent_fixture.write_json(self.baseline / "run-plan.json", {
            "version": "musical-progression-role-trial-0.1.1", "inputs": inputs,
            "code": {str(source): trial.file_digest(source)}})
        rows = []
        for observation in self.parent.observations:
            for raw_lane in observation["raw_lanes"]:
                lane = [raw_lane[key] for key in ("part_id", "voice_id")]
                status = ("assignment_budget_abstention" if len(rows) % 2 == 0
                          else "lattice_abstention")
                reasons = ["synthetic complete baseline inventory, not successful analysis"]
                unit = {"lane": lane, "status": status, "reasons": reasons, "links": [],
                        "selected": None, "role_link_inventory_complete": False,
                        "voice_inventory": None}
                path = self.baseline / "observations" / observation["record_id"] / (
                    pattern.digest(lane)[:16] + ".json.gz")
                write_gzip(path, {"version": "musical-progression-role-trial-0.1.1",
                                  "observation_ref": trial.ref(observation), "unit": unit})
                rows.append({"observation_ref": trial.ref(observation), "lane": lane,
                             "status": status, "reasons": reasons, "links": 0,
                             "artifact": str(path), "sha256": trial.file_digest(path)})
        parent_fixture.write_json(self.baseline / "unit-index.json", rows)
        parent_fixture.write_json(self.baseline / "report.json", {
            "version": "musical-progression-role-trial-0.1.1", "complete": True,
            "inputs_and_code_unchanged": True, "computation_integrity_passed": True,
            "summary": {"raw_lane_units": len(rows)}})
        self.refresh_baseline_report()
        return rows

    def refresh_baseline_report(self, *, count=None):
        path = self.baseline / "report.json"
        report = parent_fixture.read_json(path)
        if count is not None:
            report["summary"]["raw_lane_units"] = count
        report["artifact_hashes"] = {
            str(item.resolve()): trial.file_digest(item)
            for item in self.baseline.rglob("*") if item.is_file() and item != path}
        parent_fixture.write_json(path, report)
        return report

    def unit_fixture(self, name, lanes):
        folder = self.root / name
        folder.mkdir()
        ir = literal_fixture.make_ir(folder, lanes)
        observation = pattern.observe(ir, literal_fixture.scope_for(ir))
        lane = [observation["raw_lanes"][0][key] for key in ("part_id", "voice_id")]
        return ir, observation, lane

    def read_units(self, destination=None):
        return parent_fixture.read_json((destination or self.destination) / "unit-index.json")

    def expected_keys(self):
        return {(observation["record_id"], (lane["part_id"], lane["voice_id"]))
                for observation in self.parent.observations for lane in observation["raw_lanes"]}

    def freeze_baseline_voice_inventories(self):
        """Create small synthetic legacy snapshots before the new runner runs."""
        rows = parent_fixture.read_json(self.baseline / "unit-index.json")
        observations = {row["record_id"]: row for row in self.parent.observations}
        for row in rows:
            packet = read_gzip(row["artifact"])
            observation = observations[row["observation_ref"]["record_id"]]
            packet["unit"]["voice_inventory"] = legacy.observe(
                self.parent.ir, observation["scope"]["context_span"], row["lane"])
            write_gzip(Path(row["artifact"]), packet)
            row["sha256"] = trial.file_digest(row["artifact"])
        parent_fixture.write_json(self.baseline / "unit-index.json", rows)
        self.refresh_baseline_report()
        return rows

    def test_unit_exact_controls_preserve_geometry_partition_and_query_bound_identity(self):
        ir, observation, lane = self.unit_fixture("small-controls", [[
            literal_fixture.event(["C4", "E4"], 0, 2),
            literal_fixture.event(["D4", "F4"], 2, 2)]])
        frozen = legacy.observe(ir, observation["scope"]["context_span"], lane)
        before = deepcopy((ir, observation, lane, frozen))
        with patch.object(legacy, "observe", side_effect=AssertionError("runtime enumeration forbidden")) as enumerator:
            unit = trial._unit(ir, observation, lane, trial.DEFAULT_CONFIG, frozen)
        enumerator.assert_not_called()
        self.assertEqual((ir, observation, lane, frozen), before)
        graph = unit["graph"]
        self.assertEqual(unit["status"], "ready")
        self.assertEqual(graph["possible_assignments"], "7")
        self.assertTrue(unit["legacy_geometry_comparison"]["events_and_note_time_identical"])
        self.assertTrue(unit["legacy_geometry_comparison"]["prior_inventory_available"])
        self.assertTrue(unit["legacy_geometry_comparison"]["prior_geometry_checked"])
        self.assertTrue(unit["legacy_geometry_comparison"]["legacy_enumeration_complete"])
        self.assertFalse(unit["legacy_geometry_comparison"]["legacy_recomputed_or_enumerated"])
        self.assertFalse(unit["legacy_geometry_comparison"]["old_inventory_replaced"])
        self.assertEqual([probe["probe_kind"] for probe in unit["constraint_probes"]], [
            "unconstrained_count_and_sparse_completion",
            "joint_required_edges_not_independent_witness_union",
            "all_edges_forbidden_no_link_control"])
        counts = [probe["answer"]["possible_assignments"] for probe in unit["constraint_probes"]]
        self.assertEqual(counts, ["7", "2", "1"])
        for probe in unit["constraint_probes"]:
            self.assertFalse(probe["musical_claim"])
            self.assertEqual(probe["answer"]["status"], "exact_count")
            materialized = probe["witness"]
            self.assertFalse(materialized["existing_assignment_inventory_inserted"])
            self.assertFalse(materialized["may_be_combined_with_other_query_witnesses"])
            witness = materialized["assignment"]
            self.assertEqual(witness["tracks"], legacy.partition(graph["events"], witness["links"]))
            self.assertEqual(witness["legacy_geometry_id"],
                             "vpaths_" + token([lane, graph["span"], witness["links"]]))
            completion = "vfcompletion_" + pattern.digest([
                graph["record_sha256"], probe["answer"]["record_sha256"], witness["links"]])[:24]
            self.assertEqual(witness["assignment_id"], completion)
            self.assertEqual(witness["completion_id"], completion)
            self.assertNotEqual(witness["assignment_id"], witness["legacy_geometry_id"])
            self.assertTrue(all(pair in witness["links"] for pair in probe["required_links"]))
            self.assertTrue(all(pair not in witness["links"] for pair in probe["forbidden_links"]))
        self.assertEqual(unit["constraint_probes"][-1]["witness"]["assignment"]["links"], [])
        unconstrained, _, no_link = unit["constraint_probes"]
        self.assertEqual(unconstrained["witness"]["assignment"]["legacy_geometry_id"],
                         no_link["witness"]["assignment"]["legacy_geometry_id"])
        self.assertNotEqual(unconstrained["witness"]["assignment"]["completion_id"],
                            no_link["witness"]["assignment"]["completion_id"])

    def test_joint_required_probe_is_one_compatible_assignment_not_union(self):
        ir, observation, lane = self.unit_fixture("joint-probe", [[
            literal_fixture.event(["C4", "E4"], 0, 1),
            literal_fixture.event(["D4", "F4"], 1, 1),
            literal_fixture.event(["E4", "G4"], 2, 2)]])
        unit = trial._unit(ir, observation, lane, trial.DEFAULT_CONFIG)
        self.assertEqual(unit["graph"]["possible_assignments"], "49")
        joint = unit["constraint_probes"][1]
        self.assertEqual(joint["answer"]["possible_assignments"], "4")
        self.assertEqual(len(joint["required_links"]), 2)
        assignment = joint["witness"]["assignment"]
        self.assertEqual(assignment["tracks"],
                         legacy.partition(unit["graph"]["events"], assignment["links"]))
        self.assertTrue(all(pair in assignment["links"] for pair in joint["required_links"]))

    def test_unit_missing_prior_inventory_stays_not_computed_without_enumeration(self):
        ir, observation, lane = self.unit_fixture("no-prior-inventory", [[
            literal_fixture.event(["C4", "E4"], 0, 2),
            literal_fixture.event(["D4", "F4"], 2, 2)]])
        before = deepcopy((ir, observation, lane))
        with (patch.object(legacy, "observe", side_effect=AssertionError("legacy enumeration forbidden")) as enumerator,
              patch.object(legacy, "partial_matchings", side_effect=AssertionError("legacy choices forbidden")) as local_choices,
              patch.object(polyphonic, "partial_matchings", side_effect=AssertionError("choice enumeration forbidden")) as choices):
            unit = trial._unit(ir, observation, lane, trial.DEFAULT_CONFIG)
        for blocked in (enumerator, local_choices, choices):
            blocked.assert_not_called()
        self.assertEqual((ir, observation, lane), before)
        self.assertEqual(unit["graph"]["possible_assignments"], "7")
        comparison = unit["legacy_geometry_comparison"]
        self.assertTrue(comparison["literal_IR_projection_checked"])
        self.assertFalse(comparison["prior_inventory_available"])
        self.assertFalse(comparison["prior_geometry_checked"])
        self.assertTrue(comparison["prior_inventory_not_computed"])
        self.assertFalse(comparison["legacy_recomputed_or_enumerated"])
        for field in ("legacy_enumeration_complete", "legacy_possible_assignments", "legacy_abstention_reasons"):
            self.assertIsNone(comparison[field])

    def test_frozen_legacy_scope_geometry_note_time_and_exact_count_mismatches_are_rejected(self):
        ir, observation, lane = self.unit_fixture("frozen-mismatches", [[
            literal_fixture.event("C4", 0, 2), literal_fixture.event("D4", 2, 2)]])
        original = legacy.observe(ir, observation["scope"]["context_span"], lane)
        for mode in ("span", "lane", "events", "note_time", "count"):
            frozen = deepcopy(original)
            reason = "factor_graph_lost_frozen_legacy_positive_geometry"
            if mode == "span":
                frozen["span"]["end"] = pattern.q(3)
            elif mode == "lane":
                frozen["lane"] = ["foreign-part", "foreign-voice"]
            elif mode == "events":
                frozen["events"].pop()
            elif mode == "note_time":
                frozen["total_observed_note_time"] = pattern.q(3)
            else:
                frozen["possible_assignments"] += 1
                reason = "factor_count_differs_from_complete_legacy_inventory"
            before = deepcopy(frozen)
            with self.subTest(mode=mode), patch.object(legacy, "observe", side_effect=AssertionError("legacy enumeration forbidden")):
                with self.assertRaisesRegex(ValueError, reason):
                    trial._unit(ir, observation, lane, trial.DEFAULT_CONFIG, frozen)
            self.assertEqual(frozen, before)

    def test_frozen_legacy_abstention_is_preserved_not_completed_or_reenumerated(self):
        ir, observation, lane = self.unit_fixture("frozen-abstention", [[
            literal_fixture.event(["C4", "D4", "E4", "F4", "G4"], 0, 2),
            literal_fixture.event(["D4", "E4", "F4", "G4", "A4"], 2, 2)]])
        frozen = legacy.observe(ir, observation["scope"]["context_span"], lane)
        self.assertFalse(frozen["enumeration_complete"])
        self.assertEqual(frozen["assignments"], [])
        before = deepcopy(frozen)
        with (patch.object(legacy, "observe", side_effect=AssertionError("legacy enumeration forbidden")) as enumerator,
              patch.object(legacy, "partial_matchings", side_effect=AssertionError("legacy choices forbidden")) as choices):
            unit = trial._unit(ir, observation, lane, trial.DEFAULT_CONFIG, frozen)
        enumerator.assert_not_called()
        choices.assert_not_called()
        self.assertEqual(frozen, before)
        self.assertEqual(unit["status"], "ready")
        self.assertEqual(unit["graph"]["possible_assignments"], "1546")
        comparison = unit["legacy_geometry_comparison"]
        self.assertTrue(comparison["prior_geometry_checked"])
        self.assertFalse(comparison["legacy_enumeration_complete"])
        self.assertEqual(comparison["legacy_possible_assignments"], frozen["possible_assignments"])
        self.assertEqual(comparison["legacy_abstention_reasons"], frozen["abstention_reasons"])
        self.assertFalse(comparison["legacy_recomputed_or_enumerated"])

    def test_probe_rejects_corrupt_partition_legacy_and_query_bound_ids(self):
        ir, observation, lane = self.unit_fixture("corrupt-probe", [[
            literal_fixture.event("C4", 0, 2), literal_fixture.event("D4", 2, 2)]])
        graph = trial.factorize(ir, observation["scope"]["context_span"], lane)
        original_materialize = trial.materialize_witness
        for mode, reason in (("tracks", "query_witness_partition_mismatch"),
                             ("legacy", "query_witness_legacy_identity_mismatch"),
                             ("completion", "query_witness_bound_identity_mismatch")):
            def corrupt(*args, **kwargs):
                witness = original_materialize(*args, **kwargs)
                if mode == "tracks":
                    witness["assignment"]["tracks"] = []
                elif mode == "legacy":
                    witness["assignment"]["legacy_geometry_id"] = "not-the-legacy-token"
                else:
                    witness["assignment"]["completion_id"] = "not-the-query-bound-token"
                return witness

            with self.subTest(mode=mode), patch.object(trial, "materialize_witness", side_effect=corrupt):
                with self.assertRaisesRegex(ValueError, reason):
                    trial._probe(graph, [], [], "isolated-integrity-control", 100000)

    def test_graph_budget_abstention_retains_all_positive_geometry(self):
        ir, observation, lane = self.unit_fixture("edge-budget", [[
            literal_fixture.event(["C4", "E4"], 0, 2),
            literal_fixture.event(["D4", "F4"], 2, 2)]])
        frozen = legacy.observe(ir, observation["scope"]["context_span"], lane)
        unit = trial._unit(ir, observation, lane, {**trial.DEFAULT_CONFIG, "max_edges": 1}, frozen)
        self.assertNotEqual(unit["status"], "ready")
        self.assertEqual(unit["constraint_probes"], [])
        self.assertEqual(unit["graph"]["events"], frozen["events"])
        self.assertTrue(unit["legacy_geometry_comparison"]["events_and_note_time_identical"])

    def test_query_budget_is_explicit_probe_abstention_not_integrity_failure(self):
        ir, observation, lane = self.unit_fixture("query-budget", [[
            literal_fixture.event(["C4", "E4", "G4"], 0, 2),
            literal_fixture.event(["D4", "F4", "A4"], 2, 2)]])
        unit = trial._unit(ir, observation, lane, {**trial.DEFAULT_CONFIG, "work_budget": 1})
        self.assertEqual(unit["status"], "ready")
        abstentions = [probe for probe in unit["constraint_probes"]
                       if probe["answer"]["status"] == "abstention"]
        self.assertTrue(abstentions)
        self.assertTrue(all(probe["witness"] is None for probe in abstentions))
        self.assertEqual(len(unit["constraint_probes"]), 3)

    def test_success_preserves_all_raw_lanes_baseline_holds_and_input_bytes(self):
        before = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with (patch.object(parent_fixture.trial, "import_romantext", side_effect=AssertionError("source RN forbidden")) as importer,
              patch.object(legacy, "observe", side_effect=AssertionError("runtime legacy enumeration forbidden")) as enumerator,
              patch.object(legacy, "partial_matchings", side_effect=AssertionError("runtime local choices forbidden")) as choices):
            report = trial.run(self.alignment, self.baseline, self.destination)
        importer.assert_not_called()
        enumerator.assert_not_called()
        choices.assert_not_called()
        self.assertTrue(report["complete"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertTrue(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["observations"], 2)
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(report["summary"]["ready_graphs_without_prior_voice_inventory"], 4)
        self.assertEqual(report["summary"].get("ready_graphs_with_legacy_enumeration_abstention", 0), 0)
        self.assertFalse(report["legacy_inventory_recomputed_or_enumerated"])
        self.assertEqual(report["summary"]["original_status_counts_preserved"], {
            "assignment_budget_abstention": 2, "lattice_abstention": 2})
        rows = self.read_units()
        self.assertEqual({(row["observation_ref"]["record_id"], tuple(row["lane"])) for row in rows}, self.expected_keys())
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(trial.file_digest(row["artifact"]), row["sha256"])
            packet = read_gzip(row["artifact"])
            self.assertEqual(packet["lane"], row["lane"])
            self.assertEqual(packet["baseline_unit"]["status"], row["baseline_status"])
            self.assertEqual(packet["baseline_unit"]["links"], 0)
            comparison = packet["unit"]["legacy_geometry_comparison"]
            self.assertTrue(comparison["prior_inventory_not_computed"])
            self.assertIsNone(comparison["legacy_enumeration_complete"])
            self.assertIsNone(comparison["legacy_possible_assignments"])
            self.assertIsNone(packet["selected"])
            for field in ("harmonic_or_role_claim", "training_eligible", "generation_ready"):
                self.assertFalse(packet[field])
        for name, value in before.items():
            self.assertEqual(Path(name).read_bytes(), value)
        plan = parent_fixture.read_json(self.destination / "run-plan.json")
        self.assertEqual(len(plan["pattern_refs"]), 2)
        self.assertFalse(plan["old_harmony_or_nct_inventory_modified"])
        self.assertFalse(plan["source_labels_used_for_inference"])
        self.assertIn("read_frozen_inventory_only", plan["legacy_comparison"])
        for name, expected in {**plan["inputs"], **plan["code"]}.items():
            self.assertEqual(trial.file_digest(name), expected)
        actual = {str(path): trial.file_digest(path) for path in self.destination.rglob("*")
                  if path.is_file() and path.name != "report.json"}
        self.assertEqual(report["artifact_hashes"], actual)

    def test_run_passes_existing_frozen_inventory_to_unit_without_legacy_enumeration(self):
        baseline_rows = self.freeze_baseline_voice_inventories()
        snapshots = {(row["observation_ref"]["record_id"], tuple(row["lane"])):
                     read_gzip(row["artifact"])["unit"]["voice_inventory"] for row in baseline_rows}
        original_files = {str(path): path.read_bytes() for path in self.baseline.rglob("*") if path.is_file()}
        with (patch.object(legacy, "observe", side_effect=AssertionError("runtime legacy enumeration forbidden")) as enumerator,
              patch.object(legacy, "partial_matchings", side_effect=AssertionError("runtime legacy choices forbidden")) as choices,
              patch.object(trial, "_unit", wraps=trial._unit) as units):
            report = trial.run(self.alignment, self.baseline, self.destination)
        enumerator.assert_not_called()
        choices.assert_not_called()
        self.assertTrue(report["complete"])
        self.assertEqual(units.call_count, 4)
        self.assertEqual(report["summary"].get("ready_graphs_without_prior_voice_inventory", 0), 0)
        for call in units.call_args_list:
            key = call.args[1]["record_id"], tuple(call.args[2])
            self.assertEqual(call.args[4], snapshots[key])
        for row in self.read_units():
            packet = read_gzip(row["artifact"])
            key = row["observation_ref"]["record_id"], tuple(row["lane"])
            comparison = packet["unit"]["legacy_geometry_comparison"]
            self.assertTrue(comparison["prior_inventory_available"])
            self.assertTrue(comparison["prior_geometry_checked"])
            self.assertTrue(comparison["legacy_enumeration_complete"])
            self.assertEqual(comparison["legacy_possible_assignments"], snapshots[key]["possible_assignments"])
            self.assertFalse(comparison["legacy_recomputed_or_enumerated"])
        for name, raw in original_files.items():
            self.assertEqual(Path(name).read_bytes(), raw)

    def test_frozen_inventory_count_mismatch_keeps_failure_and_other_units_in_denominator(self):
        rows = self.freeze_baseline_voice_inventories()
        path = Path(rows[0]["artifact"])
        packet = read_gzip(path)
        packet["unit"]["voice_inventory"]["possible_assignments"] += 1
        write_gzip(path, packet)
        rows[0]["sha256"] = trial.file_digest(path)
        parent_fixture.write_json(self.baseline / "unit-index.json", rows)
        self.refresh_baseline_report()
        with patch.object(legacy, "observe", side_effect=AssertionError("runtime legacy enumeration forbidden")) as enumerator:
            report = trial.run(self.alignment, self.baseline, self.destination)
        enumerator.assert_not_called()
        self.assertFalse(report["complete"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertFalse(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(report["summary"]["status_counts"], {"integrity_or_computation_abstention": 1, "ready": 3})
        held = next(row for row in self.read_units() if row["status"] == "integrity_or_computation_abstention")
        self.assertTrue(any("factor_count_differs_from_complete_legacy_inventory" in reason for reason in held["reasons"]))
        self.assertEqual(len(self.read_units()), 4)

    def test_run_empty_rest_lane_keeps_denominator_and_original_hold(self):
        score = stream.Score()
        for part_number in range(2):
            part = stream.Part(id=f"P{part_number}")
            for number in range(1, 4):
                measure = stream.Measure(number=number)
                if number == 1:
                    measure.append(meter.TimeSignature("4/4"))
                measure.append(note.Rest(quarterLength=4) if part_number == 0
                               else note.Note("G2", quarterLength=4))
                part.append(measure)
            score.append(part)
        path = self.parent.case / "score.musicxml"
        score.write("musicxml", fp=path)
        ir = literal_fixture.FormalIRAdapter().convert(
            literal_fixture.CanonicalIRBuilder().build(converter.parse(path), path), path)
        parent_fixture.write_json(self.parent.case / "canonical-ir.json", ir)
        observations, index, attempts = [], [], []
        for old_row, source, old_observation in zip(self.parent.index, self.parent.sources, self.parent.observations):
            alignment = parent_fixture.align_statement(source, ir, self.parent.meter)
            self.assertEqual(alignment["status"], "exact_coordinate")
            scope = deepcopy(old_observation["scope"])
            scope.update(score_id=ir["score"]["score_id"], ir_document_id=ir["ir_document_id"],
                         ir_content_sha256=pattern.digest(ir), source_files=deepcopy(ir["source_files"]),
                         alignment_ref=trial.ref(alignment))
            observation = pattern.observe(ir, scope)
            parent_fixture.write_json(old_row["path"], observation)
            row = {**old_row, **trial.ref(observation)}
            observations.append(observation)
            index.append(row)
            attempts.append({"source_statement_ref": deepcopy(scope["source_statement_ref"]),
                             "status": "exact_coordinate", "alignment": alignment})
        self.parent.ir, self.parent.observations, self.parent.index = ir, observations, index
        parent_fixture.write_json(self.alignment / "pattern-index.json", index)
        parent_fixture.write_json(self.alignment / "alignment-attempts.json", attempts)
        self.parent.refresh_parent_report()
        # Replace only generated temp baseline artifacts after the parent IR
        # changes, ensuring its new hashes and all four lanes are registered.
        baseline_rows = self.make_baseline()
        report = trial.run(self.alignment, self.baseline, self.destination)
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        rows = self.read_units()
        self.assertEqual({(row["observation_ref"]["record_id"], tuple(row["lane"])) for row in rows}, self.expected_keys())
        packets = [read_gzip(row["artifact"]) for row in rows]
        empty = [packet for packet in packets if not packet["unit"]["graph"]["events"]]
        self.assertEqual(len(empty), 2)
        baseline_by_key = {(row["observation_ref"]["record_id"], tuple(row["lane"])): row
                           for row in baseline_rows}
        for packet in empty:
            key = packet["observation_ref"]["record_id"], tuple(packet["lane"])
            self.assertEqual(packet["baseline_unit"], baseline_by_key[key])

    def test_computation_failure_retains_every_unit_but_not_integrity_completion(self):
        with patch.object(trial, "_unit", side_effect=RuntimeError("synthetic graph computation failure")):
            report = trial.run(self.alignment, self.baseline, self.destination)
        self.assertFalse(report["complete"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertFalse(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(report["summary"]["status_counts"], {"integrity_or_computation_abstention": 4})
        self.assertEqual(len(self.read_units()), 4)
        for row in self.read_units():
            packet = read_gzip(row["artifact"])
            self.assertIsNone(packet["unit"]["graph"])
            self.assertEqual(packet["unit"]["constraint_probes"], [])
            self.assertIn("RuntimeError:synthetic graph computation failure", row["reasons"])

    def test_caller_ir_mutation_is_fatal_not_hidden_as_computation_abstention(self):
        def mutate(ir, observation, lane, config, baseline_voice_inventory=None):
            ir["score"]["metadata"]["forbidden_caller_mutation"] = True
            raise RuntimeError("mutation must not become an ordinary held unit")

        with patch.object(trial, "_unit", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "factor_trial_mutated_input"):
                trial.run(self.alignment, self.baseline, self.destination)
        self.assertFalse((self.destination / "report.json").exists())

    def test_output_guard_existing_outside_and_nested_parent_paths(self):
        self.destination.mkdir()
        marker = self.destination / "marker.txt"
        marker.write_text("preserve", encoding="utf-8")
        for destination in (self.destination, self.root / "outside-run", self.root / "output",
                            self.alignment / "nested-run", self.baseline / "nested-run"):
            with self.subTest(destination=destination), self.assertRaisesRegex(ValueError, "new_workspace_output"):
                trial.run(self.alignment, self.baseline, destination)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        self.assertEqual(list(self.destination.iterdir()), [marker])

    def test_invalid_or_unknown_budget_is_refused_before_output(self):
        for options in ({"max_events": 0}, {"max_factors": -1}, {"max_edges": True},
                        {"work_budget": 1.5}, {"invented_budget": 1}):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, "invalid_factor_trial_budget"):
                trial.run(self.alignment, self.baseline, self.destination, **options)
            self.assertFalse(self.destination.exists())

    def test_unsupported_incomplete_or_failed_baseline_is_refused(self):
        path = self.baseline / "report.json"
        original = parent_fixture.read_json(path)
        for field, value in (("version", "unsupported"), ("complete", False),
                             ("inputs_and_code_unchanged", False), ("computation_integrity_passed", False)):
            report = {**original, field: value}
            parent_fixture.write_json(path, report)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "completed_supported_role_baseline"):
                trial.run(self.alignment, self.baseline, self.destination)
            self.assertFalse(self.destination.exists())
        parent_fixture.write_json(path, original)

    def test_baseline_missing_changed_or_unregistered_artifact_is_refused(self):
        path = self.baseline / "unit-index.json"
        original = path.read_bytes()
        extra = self.baseline / "unregistered.json"
        for mode, reason in (("missing", "baseline_artifact_inventory_mismatch"),
                             ("changed", "baseline_artifact_changed"),
                             ("extra", "baseline_artifact_inventory_mismatch")):
            if mode == "missing":
                path.unlink()
            elif mode == "changed":
                path.write_bytes(original + b"\n")
            else:
                extra.write_text("{}", encoding="utf-8")
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, reason):
                trial.run(self.alignment, self.baseline, self.destination)
            self.assertFalse(self.destination.exists())
            path.write_bytes(original)
            if extra.exists():
                extra.unlink()

    def test_baseline_plan_alignment_inventory_and_actual_producer_hash_are_protected(self):
        path = self.baseline / "run-plan.json"
        original = parent_fixture.read_json(path)
        for mode, reason in (("alignment", "baseline_alignment_inventory_mismatch"),
                             ("version", "baseline_plan_version_mismatch"),
                             ("code", "baseline_producer_source_changed")):
            plan = deepcopy(original)
            if mode == "alignment":
                plan["inputs"].pop(next(iter(plan["inputs"])))
            elif mode == "version":
                plan["version"] = "wrong-version"
            else:
                plan["code"][next(iter(plan["code"]))] = "f" * 64
            parent_fixture.write_json(path, plan)
            self.refresh_baseline_report()
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, reason):
                trial.run(self.alignment, self.baseline, self.destination)
            self.assertFalse(self.destination.exists())
        parent_fixture.write_json(path, original)
        self.refresh_baseline_report()

    def test_duplicate_missing_or_foreign_lane_index_cannot_change_denominator(self):
        path = self.baseline / "unit-index.json"
        original = parent_fixture.read_json(path)
        for mode, reason in (("duplicate", "baseline_duplicate_or_missing_raw_lane"),
                             ("missing", "baseline_and_current_lane_denominator_mismatch"),
                             ("index", "baseline_packet_index_mismatch")):
            rows = deepcopy(original)
            if mode == "duplicate":
                rows.append(deepcopy(rows[0]))
            elif mode == "missing":
                rows.pop()
            else:
                rows[0]["lane"] = ["foreign-part", "foreign-voice"]
            parent_fixture.write_json(path, rows)
            self.refresh_baseline_report(count=len(rows))
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, reason):
                trial.run(self.alignment, self.baseline, self.destination)
            self.assertFalse(self.destination.exists())
        parent_fixture.write_json(path, original)
        self.refresh_baseline_report(count=len(original))

    def test_registered_packet_mismatch_cannot_be_hidden_by_rehashing_manifest(self):
        rows = parent_fixture.read_json(self.baseline / "unit-index.json")
        path = Path(rows[0]["artifact"])
        packet = read_gzip(path)
        packet["unit"]["reasons"] = ["different than the frozen index"]
        write_gzip(path, packet)
        rows[0]["sha256"] = trial.file_digest(path)
        parent_fixture.write_json(self.baseline / "unit-index.json", rows)
        self.refresh_baseline_report()
        with self.assertRaisesRegex(ValueError, "baseline_packet_index_mismatch"):
            trial.run(self.alignment, self.baseline, self.destination)
        self.assertFalse(self.destination.exists())

    def test_baseline_observation_sha_cannot_be_swapped_under_same_id_and_lane(self):
        rows = parent_fixture.read_json(self.baseline / "unit-index.json")
        path = Path(rows[0]["artifact"])
        packet = read_gzip(path)
        stale_ref = {**rows[0]["observation_ref"], "record_sha256": "f" * 64}
        rows[0]["observation_ref"] = stale_ref
        packet["observation_ref"] = deepcopy(stale_ref)
        write_gzip(path, packet)
        rows[0]["sha256"] = trial.file_digest(path)
        parent_fixture.write_json(self.baseline / "unit-index.json", rows)
        self.refresh_baseline_report()
        with self.assertRaisesRegex(ValueError, "baseline.*observation"):
            trial.run(self.alignment, self.baseline, self.destination)
        self.assertFalse(self.destination.exists())

    def test_parent_artifact_changed_is_refused_before_baseline_or_output(self):
        self.parent.analysis.write_text("changed source bytes", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "upstream_artifact_changed"):
            trial.run(self.alignment, self.baseline, self.destination)
        self.assertFalse(self.destination.exists())

    def test_query_budget_run_retains_all_units_and_inventory_completion(self):
        report = trial.run(self.alignment, self.baseline, self.destination, work_budget=1)
        self.assertTrue(report["complete"])
        self.assertTrue(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["raw_lane_units"], 4)
        self.assertEqual(len(self.read_units()), 4)
        self.assertNotIn("integrity_or_computation_abstention", report["summary"]["status_counts"])
        self.assertGreater(report["summary"]["probe_status_counts"].get("abstention", 0), 0)

    def test_changed_input_and_new_code_schema_or_parent_artifact_make_report_incomplete(self):
        original_unit = trial._unit
        for mode, marker in (("input", str(self.parent.analysis)),
                             ("code", "source_or_schema_inventory_changed"),
                             ("schema", "source_or_schema_inventory_changed"),
                             ("alignment", "alignment_artifact_inventory_changed"),
                             ("baseline", "baseline_artifact_inventory_changed")):
            called = []
            added = []
            analysis_before = self.parent.analysis.read_bytes()

            def compute_then_change(*args, **kwargs):
                unit = original_unit(*args, **kwargs)
                if not called:
                    if mode == "input":
                        self.parent.analysis.write_bytes(analysis_before + b"\nexternal edit\n")
                    else:
                        folder = {"code": self.root / "src/musicanote_harness",
                                  "schema": self.root / "docs/harmony/schemas",
                                  "alignment": self.alignment, "baseline": self.baseline}[mode]
                        path = folder / ("new_module.py" if mode == "code" else "new_artifact.json")
                        path.write_text("{}", encoding="utf-8")
                        added.append(path)
                called.append(True)
                return unit

            destination = self.root / "output" / ("changed-" + mode)
            with self.subTest(mode=mode), patch.object(trial, "_unit", side_effect=compute_then_change):
                report = trial.run(self.alignment, self.baseline, destination)
                self.assertFalse(report["complete"])
                self.assertFalse(report["inputs_and_code_unchanged"])
                self.assertTrue(report["computation_integrity_passed"])
                self.assertIn(marker, report["changed_inputs_or_code"])
                self.assertEqual(report["summary"]["raw_lane_units"], 4)
                self.assertEqual(len(self.read_units(destination)), 4)
            self.parent.analysis.write_bytes(analysis_before)
            for path in added:
                path.unlink()


if __name__ == "__main__":
    unittest.main()
