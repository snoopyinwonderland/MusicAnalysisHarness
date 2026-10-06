"""Frozen lineage diagnostics preserve geometry and every raw-lane denominator."""
from copy import deepcopy
from contextlib import ExitStack, redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_frozen_context_lineage_trial as trial
from musicanote_harness import harmony_frozen_context_voice_trial as voice_trial
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness.sounding_lineage_audit import audit_sounding_lineage, validate_audit
from test_harmony_frozen_context_voice_trial import fixture as voice_fixture, read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha
import test_source_locator_revision_trial as source_fixture

GRACE = '<note><grace slash="yes"/><pitch><step>A</step><octave>4</octave></pitch><voice>1</voice><type>16th</type></note>'


def fixture(root, *, unsafe_chain=False, grace=False):
    xml = source_fixture.XML if grace else source_fixture.XML.replace(GRACE, "")
    if unsafe_chain:
        old = '<duration>8</duration><tie type="start"/><voice>1</voice><type>half</type></note>'
        new = ('<duration>4</duration><tie type="start"/><voice>1</voice><type>quarter</type></note>'
               '<note><rest/><duration>4</duration><voice>1</voice><type>quarter</type></note>')
        assert old in xml
        xml = xml.replace(old, new)
    with patch.object(source_fixture, "XML", xml), redirect_stdout(io.StringIO()):
        data = voice_fixture(root, rest_part=True)
        with patch.object(voice_trial, "ROOT", root):
            voice_trial.run(data["integration"], data["output"])
    data["baseline"] = data["output"]
    data["output"] = root / "output/lineage"
    return data


def refresh_baseline(data):
    path = data["baseline"] / "report.json"
    report = read_json(path)
    report["artifact_hashes"] = {name: sha(name) for name in report["artifact_hashes"]}
    write_json(path, report)


class FrozenContextLineageTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)
        root_patch = patch.object(trial, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def run_fixture(self):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.data["baseline"], self.data["output"])

    def reject_before_output(self, error):
        with self.assertRaisesRegex((ValueError, KeyError), error):
            self.run_fixture()
        self.assertFalse(self.data["output"].exists())

    def test_all_contexts_all_raw_lanes_and_geometry_snapshots_are_preserved(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        report = self.run_fixture()
        self.assertTrue(report["complete"])
        self.assertTrue(report["source_clock_consistency_passed"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertTrue(report["artifacts_unchanged"])
        baseline = read_json(self.data["baseline"] / "report.json")
        index = read_json(self.data["output"] / "audit-index.json")
        gates = read_json(self.data["output"] / "gate-index.json")
        self.assertEqual(len(index), baseline["summary"]["contexts"])
        self.assertEqual(len(gates), baseline["summary"]["raw_lane_units"])
        for row in index:
            packet = read_json(row["artifact"])
            observation = read_json(packet["baseline_observation_artifact"])
            audit = packet["audit"]
            self.assertEqual(audit["selection"]["selected_sound_refs"],
                [sound["sounding_event_id"] for sound in observation["core_projection"]["sounding_events"]])
            validate_audit(audit, ir=self.data["ir"], sound_ids=audit["selection"]["sound_ids"],
                           context_span=observation["scope"]["context_span"])
        for gate in gates:
            old = read_gzip(gate["baseline_unit_artifact"])
            self.assertEqual(gate["baseline_unit_file_sha256"], sha(gate["baseline_unit_artifact"]))
            self.assertEqual(gate["baseline_unit_content_sha256"], pattern.digest(old))
            self.assertEqual(gate["geometry_result_content_sha256"], pattern.digest(old["unit"]))
            self.assertEqual(gate["geometry_status"], old["unit"]["status"])
            self.assertEqual(gate["geometry_reasons"], old["unit"]["reasons"])
            self.assertEqual(gate["original_stage_statuses"], old["original_stage_statuses"])
            self.assertIsNone(gate["selected"])
            for flag in ("semantic_eligible", "training_eligible", "gold_eligible", "generation_ready", "geometry_recomputed"):
                self.assertFalse(gate[flag])
        self.assertTrue(any(gate["gate_status"] == "not_applicable_no_positive_sounds" for gate in gates))
        for path, payload in before.items():
            self.assertEqual(path.read_bytes(), payload)
        for name, expected in report["artifact_hashes"].items():
            self.assertEqual(sha(name), expected)
        actual = {str(path.resolve()) for path in self.data["output"].rglob("*") if path.is_file()}
        self.assertEqual(actual, set(report["artifact_hashes"]) | {str(self.data["output"] / "report.json")})

    def test_current_additive_code_inventory_need_not_equal_old_producer_inventory(self):
        path = self.root / "src/musicanote_harness/additive_auditor.py"
        path.write_bytes(b"# new additive code, not an old producer file")
        report = self.run_fixture()
        self.assertTrue(report["complete"])
        old = read_json(self.data["baseline"] / "run-plan.json")
        new = read_json(self.data["output"] / "run-plan.json")
        self.assertNotIn(str(path), old["code"])
        self.assertIn(str(path), new["code"])

    def test_source_clock_conflict_is_successful_diagnostic_not_complete_failure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root, unsafe_chain=True)
            with patch.object(trial, "ROOT", root), redirect_stdout(io.StringIO()):
                report = trial.run(data["baseline"], data["output"])
            self.assertTrue(report["complete"])
            self.assertTrue(report["computation_integrity_passed"])
            self.assertFalse(report["source_clock_consistency_passed"])
            self.assertIn("full_source_timeline_gap", report["summary"]["diagnostic_counts"])
            gates = read_json(data["output"] / "gate-index.json")
            withheld = [g for g in gates if g["gate_status"] == "withheld_source_clock_conflict"]
            self.assertTrue(withheld)
            self.assertTrue(all(g["affected_selected_lane_sound_refs"] for g in withheld))
            self.assertTrue(all(g["geometry_result_preserved"] for g in gates))
            self.assertEqual(len(gates), read_json(data["baseline"] / "report.json")["summary"]["raw_lane_units"])

    def test_grace_diagnostics_never_promote_held_geometry(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root, grace=True)
            with patch.object(trial, "ROOT", root), redirect_stdout(io.StringIO()):
                report = trial.run(data["baseline"], data["output"])
            self.assertTrue(report["complete"])
            self.assertFalse(report["source_clock_consistency_passed"])
            gates = read_json(data["output"] / "gate-index.json")
            held = [g for g in gates if g["geometry_status"] == "abstention"]
            self.assertTrue(held)
            self.assertTrue(all(not g["semantic_eligible"] and not g["generation_ready"] for g in held))
            self.assertTrue(any(g["gate_status"] == "withheld_point_timing_not_assessed" for g in gates))
            self.assertFalse(any(g["gate_status"] == "withheld_source_clock_conflict" for g in gates))

    def test_no_old_engine_selector_legacy_or_xml_callback_is_run(self):
        names = ["musicanote_harness.harmony_breadth_trial.freeze_score",
                 "musicanote_harness.harmony_breadth_trial.analyze_sample",
                 "musicanote_harness.harmony_voice_paths.observe",
                 "musicanote_harness.harmony_polyphonic_links.partial_matchings",
                 "musicanote_harness.source_physical_measure_revision.revise",
                 "musicanote_harness.source_sequence_replay_trial.run",
                 "musicanote_harness.dcml_import.parse_score_without_imported_harmony",
                 "musicanote_harness.harmony_factorized_voice_paths.factorize"]
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(name, side_effect=AssertionError("frozen producer forbidden"))) for name in names]
            report = self.run_fixture()
        self.assertTrue(report["complete"])
        for mock in mocks:
            mock.assert_not_called()

    def test_large_original_stages_are_not_decompressed_and_literal_is_checked_once(self):
        actual_read, actual_validate = trial.read, trial.validate_observation
        read_paths, literal_calls = [], []
        def checked_read(path, **kwargs):
            read_paths.append(Path(path).resolve())
            return actual_read(path, **kwargs)
        def checked_validate(record, **kwargs):
            if kwargs.get("ir") is not None:
                literal_calls.append(record["record_id"])
            return actual_validate(record, **kwargs)
        with patch.object(trial, "read", side_effect=checked_read), patch.object(trial, "validate_observation", side_effect=checked_validate):
            report = self.run_fixture()
        self.assertTrue(report["complete"])
        self.assertEqual(len(literal_calls), report["summary"]["contexts"])
        self.assertEqual(len(literal_calls), len(set(literal_calls)))
        forbidden = [*self.data["breadth"].glob("*.json.gz"), *self.data["integration"].glob("**/*.json.gz")]
        self.assertFalse(set(read_paths).intersection(path.resolve() for path in forbidden))

    def test_existing_nested_and_outside_output_are_rejected(self):
        self.data["output"].mkdir()
        marker = self.data["output"] / "keep"
        marker.write_bytes(b"keep")
        for output in [self.data["output"], self.root / "outside", self.root / "output",
                       self.data["baseline"] / "child", self.data["breadth"] / "child",
                       self.root / "output/new/child"]:
            with self.assertRaisesRegex(ValueError, "output_must_be_new"):
                trial.run(self.data["baseline"], output)
        self.assertEqual(marker.read_bytes(), b"keep")

    def test_unsupported_incomplete_and_promoting_baseline_reports_are_rejected(self):
        path = self.data["baseline"] / "report.json"
        original = read_json(path)
        for field, value in [("version", "other"), ("complete", 1), ("inputs_and_code_unchanged", False),
                             ("computation_integrity_passed", False), ("artifacts_unchanged", False),
                             ("source_labels_used_for_inference", True), ("geometry_recomputed", True)]:
            changed = deepcopy(original)
            changed[field] = value
            if field == "geometry_recomputed":
                # Geometry is represented by the actual producer's legacy flag.
                changed["legacy_inventory_recomputed_or_enumerated"] = True
            write_json(path, changed)
            with self.subTest(field=field):
                self.reject_before_output("completed_supported")
        write_json(path, original)

    def test_missing_changed_and_unregistered_baseline_artifacts_are_rejected(self):
        path = self.data["baseline"] / "observation-index.json"
        payload = path.read_bytes()
        path.write_bytes(payload + b" ")
        self.reject_before_output("input_hash_mismatch")
        path.write_bytes(payload)
        path.unlink()
        self.reject_before_output("baseline_artifact_inventory_mismatch")
        path.write_bytes(payload)
        extra = self.data["baseline"] / "external.json"
        extra.write_bytes(b"{}")
        self.reject_before_output("baseline_artifact_inventory_mismatch")

    def test_registered_source_ir_and_old_producer_hashes_are_protected(self):
        plan = read_json(self.data["baseline"] / "run-plan.json")
        for path in [self.data["source"], self.data["labels"], self.data["frozen"], Path(next(iter(plan["code"])) )]:
            before = path.read_bytes()
            path.write_bytes(before + b" ")
            with self.subTest(path=path.name):
                self.reject_before_output("input_hash_mismatch")
            path.write_bytes(before)

    def test_missing_duplicate_and_unknown_context_and_lane_indices_rejected(self):
        for filename, error in [("observation-index.json", "duplicate_baseline_context"),
                                ("unit-index.json", "duplicate_baseline_raw_lane")]:
            path = self.data["baseline"] / filename
            original = read_json(path)
            duplicate = [*original, deepcopy(original[0])]
            write_json(path, duplicate)
            refresh_baseline(self.data)
            self.reject_before_output(error)
            write_json(path, original[:-1])
            refresh_baseline(self.data)
            self.reject_before_output("denominator_mismatch")
            changed = deepcopy(original)
            changed[0]["context_key"][2] = "unknown"
            write_json(path, changed)
            refresh_baseline(self.data)
            self.reject_before_output("denominator_mismatch")
            write_json(path, original)
            refresh_baseline(self.data)

    def test_resealed_observation_literal_tamper_is_rejected(self):
        index_path = self.data["baseline"] / "observation-index.json"
        rows = read_json(index_path)
        path = Path(rows[0]["path"])
        record = read_json(path)
        next(slot for slot in record["slots"] if slot["event_kind"] == "note")["core_event"]["written_pitch"]["step"] = "B"
        body = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
        record["record_sha256"] = pattern.digest(body)
        record["record_id"] = "mfco_" + record["record_sha256"][:24]
        write_json(path, record)
        rows[0].update(record_id=record["record_id"], record_sha256=record["record_sha256"], sha256=sha(path))
        write_json(index_path, rows)
        refresh_baseline(self.data)
        self.reject_before_output("reconstruction_mismatch")

    def test_unit_packet_index_disagreement_and_stale_observation_ref_rejected(self):
        rows = read_json(self.data["baseline"] / "unit-index.json")
        path = Path(rows[0]["artifact"])
        old = read_gzip(path)
        for mode in ("status", "ref", "promotion"):
            changed = deepcopy(old)
            if mode == "status":
                changed["unit"]["status"] = "not_the_index_status"
            elif mode == "ref":
                changed["observation_ref"]["record_sha256"] = "0" * 64
            else:
                changed["generation_ready"] = True
            write_gzip(path, changed)
            rows[0]["sha256"] = sha(path)
            write_json(self.data["baseline"] / "unit-index.json", rows)
            refresh_baseline(self.data)
            with self.subTest(mode=mode):
                self.reject_before_output("baseline_unit_index_or_packet_binding_mismatch")
        write_gzip(path, old)

    def test_working_ir_scope_and_candidate_selection_fail_closed(self):
        path = self.data["integration"] / "report.json"
        original = read_json(path)
        changed = deepcopy(original)
        changed["measure_revisions"][0]["candidate_created"] = True
        write_json(path, changed)
        plan_path = self.data["baseline"] / "run-plan.json"
        plan = read_json(plan_path)
        plan["inputs"][str(path)] = sha(path)
        write_json(plan_path, plan)
        refresh_baseline(self.data)
        self.reject_before_output("invalid_explicit_revision_selection")

    def test_caught_diagnostic_failure_preserves_entire_denominator(self):
        actual = trial.audit_sounding_lineage
        calls = 0
        def fail_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ValueError("synthetic_diagnostic_failure")
            return actual(*args, **kwargs)
        with patch.object(trial, "audit_sounding_lineage", side_effect=fail_once):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertFalse(report["computation_integrity_passed"])
        self.assertFalse(report["source_clock_consistency_passed"])
        self.assertEqual(calls, report["summary"]["contexts"])
        self.assertEqual(len(read_json(self.data["output"] / "gate-index.json")), report["summary"]["raw_lane_units"])
        self.assertIn("withheld_diagnostic_failure", report["summary"]["gate_status_counts"])

    def test_auditor_mutation_of_caller_ir_is_detected(self):
        actual = trial.audit_sounding_lineage
        def mutate(ir, **kwargs):
            result = actual(ir, **kwargs)
            ir["score"]["title"] = "mutated"
            return result
        with patch.object(trial, "audit_sounding_lineage", side_effect=mutate), self.assertRaisesRegex(ValueError, "diagnostic_inputs_mutated"):
            self.run_fixture()
        self.assertFalse((self.data["output"] / "report.json").exists())

    def test_auditor_mutation_of_explicit_sound_selector_is_detected(self):
        actual = trial.audit_sounding_lineage
        def mutate(ir, *, sound_ids, context_span):
            result = actual(ir, sound_ids=sound_ids, context_span=context_span)
            sound_ids.clear()
            return result
        with patch.object(trial, "audit_sounding_lineage", side_effect=mutate), self.assertRaisesRegex(ValueError, "diagnostic_inputs_mutated"):
            self.run_fixture()
        self.assertFalse((self.data["output"] / "report.json").exists())

    def test_external_input_and_new_code_change_is_reported_incomplete(self):
        actual = trial.audit_sounding_lineage
        changed = False
        def external_change(*args, **kwargs):
            nonlocal changed
            result = actual(*args, **kwargs)
            if not changed:
                changed = True
                self.data["labels"].write_bytes(b"external opaque labels changed")
                (self.root / "src/musicanote_harness/external.py").write_bytes(b"# new external source")
            return result
        with patch.object(trial, "audit_sounding_lineage", side_effect=external_change):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIn(str(self.data["labels"]), report["changed_inputs_or_code"])
        self.assertIn("source_or_schema_inventory_changed", report["changed_inputs_or_code"])

    def test_external_baseline_inventory_addition_is_reported_incomplete(self):
        actual = trial.audit_sounding_lineage
        changed = False
        def add_file(*args, **kwargs):
            nonlocal changed
            result = actual(*args, **kwargs)
            if not changed:
                changed = True
                (self.data["baseline"] / "external.json").write_bytes(b"{}")
            return result
        with patch.object(trial, "audit_sounding_lineage", side_effect=add_file):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertIn("parent_artifact_inventory_changed:" + str(self.data["baseline"]), report["changed_inputs_or_code"])

    def alter_output(self, mode):
        actual = trial.audit_sounding_lineage
        changed = False
        def external_change(*args, **kwargs):
            nonlocal changed
            result = actual(*args, **kwargs)
            if not changed:
                changed = True
                path = self.data["output"] / "run-plan.json"
                if mode == "change":
                    path.write_bytes(path.read_bytes() + b" ")
                elif mode == "delete":
                    path.unlink()
                else:
                    (self.data["output"] / "external.json").write_bytes(b"{}")
            return result
        with patch.object(trial, "audit_sounding_lineage", side_effect=external_change):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertFalse(report["artifacts_unchanged"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertEqual(len(read_json(self.data["output"] / "gate-index.json")), report["summary"]["raw_lane_units"])

    def test_creation_hash_output_change_cannot_be_blessed_by_final_rehash(self):
        self.alter_output("change")

    def test_output_artifact_deletion_is_incomplete(self):
        self.alter_output("delete")

    def test_output_artifact_addition_is_incomplete(self):
        self.alter_output("add")

    def test_full_chain_failure_outside_context_does_not_withhold_unaffected_lane(self):
        data = trial._inputs(self.data["baseline"])
        key = next(iter(data["contexts"]))
        parent, ir, sidecar = trial._working_case(data, key[0])
        observation = trial._observation(data, key, parent, ir, sidecar)
        lane = next([row["part_id"], row["voice_id"]] for row in observation["raw_lanes"]
                    if trial._owned_sound_refs(observation, [row["part_id"], row["voice_id"]])[0])
        positive, points = trial._owned_sound_refs(observation, lane)
        self.assertTrue(positive)
        audit = {"record_id": "msla_synthetic", "record_sha256": "0" * 64,
                 "source_clock_consistency_passed": False,
                 "sounding_audits": [{"sounding_event_ref": "linked_context_only_other_lane", "source_clock_consistency_passed": False}]}
        gate = trial._gate(data, key, observation, lane, audit, Path("synthetic-audit.json"), "0" * 64)
        self.assertFalse(gate["context_full_lineage_source_clock_passed"])
        self.assertEqual(gate["affected_selected_lane_sound_refs"], [])
        self.assertEqual(gate["gate_status"], "source_clock_consistent_not_semantic_approval")
        audit["sounding_audits"].append({"sounding_event_ref": positive[0], "source_clock_consistency_passed": False})
        affected = trial._gate(data, key, observation, lane, audit, Path("synthetic-audit.json"), "0" * 64)
        self.assertEqual(affected["gate_status"], "withheld_source_clock_conflict")
        self.assertEqual(affected["affected_selected_lane_sound_refs"], [positive[0]])

    def test_mixed_point_unknown_and_positive_conflict_retains_conflict_classification(self):
        data = trial._inputs(self.data["baseline"])
        key = next(iter(data["contexts"]))
        parent, ir, sidecar = trial._working_case(data, key[0])
        observation = trial._observation(data, key, parent, ir, sidecar)
        lane = next([row["part_id"], row["voice_id"]] for row in observation["raw_lanes"]
                    if trial._owned_sound_refs(observation, [row["part_id"], row["voice_id"]])[0])
        positive, _ = trial._owned_sound_refs(observation, lane)
        audit = {"record_id": "msla_synthetic", "record_sha256": "0" * 64,
                 "source_clock_consistency_passed": False,
                 "sounding_audits": [{"sounding_event_ref": positive[0], "source_clock_consistency_passed": False,
                                      "timing_status": "positive_notated", "diagnostics": ["full_source_timeline_gap"]},
                                     {"sounding_event_ref": positive[1], "source_clock_consistency_passed": False,
                                      "timing_status": "grace_point_performed_timing_unknown", "diagnostics": ["grace_performed_timing_not_assessed"]}]}
        gate = trial._gate(data, key, observation, lane, audit, Path("synthetic-audit.json"), "0" * 64)
        self.assertEqual(gate["gate_status"], "withheld_source_clock_conflict")
        self.assertEqual(gate["affected_selected_lane_sound_refs"], positive[:2])

    def test_missing_source_note_ownership_is_never_silently_dropped(self):
        data = trial._inputs(self.data["baseline"])
        key = next(iter(data["contexts"]))
        parent, ir, sidecar = trial._working_case(data, key[0])
        observation = trial._observation(data, key, parent, ir, sidecar)
        observation["core_projection"]["sounding_events"][0]["source_note_ids"].append("missing-note")
        with self.assertRaisesRegex(ValueError, "missing_projected_source_note_ownership"):
            trial._owned_sound_refs(observation, ["irrelevant-part", "irrelevant-voice"])


if __name__ == "__main__":
    unittest.main()
