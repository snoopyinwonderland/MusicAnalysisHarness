from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import musical_role_evidence_trial as trial
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness.musical_harmony_assumption import validate_track
from musicanote_harness.musical_role_evidence import validate_evidence
from musicanote_harness.musical_semantic_alignment import align_statement, prepare_meter_index
from musicanote_harness.musical_semantic_intake import prepare_source_statements
from test_musical_pattern_observation import make_ir, scope_for


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def reseal_observation(record):
    payload = {key: value for key, value in record.items()
               if key not in ("record_id", "record_sha256")}
    record["record_sha256"] = pattern.digest(payload)
    record["record_id"] = "mpo_" + record["record_sha256"][:24]
    return record


class MusicalRoleEvidenceTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root_patch = patch.object(trial, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.output_root = self.root / "output"
        self.output_root.mkdir()
        self.alignment = self.output_root / "g1-parent"
        self.case = self.alignment / "cases" / "synthetic-case"
        self.case.mkdir(parents=True)
        self.ir = make_ir(self.case)
        self.analysis = self.case / "analysis.txt"
        self.analysis.write_text(
            "Time Signature: 4/4\n"
            "Pedal: C m1 b1 m2 b1\n"
            "Pedal: C m2 b1 m3 b1\n"
            "m1 C: I b3 V7\nm2 I\nm3 V\n", encoding="utf-8")
        self.sources = prepare_source_statements(self.analysis, corpus_root=self.alignment)["records"]
        self.assertEqual(len(self.sources), 2)
        self.meter = prepare_meter_index(self.analysis)
        write_json(self.case / "canonical-ir.json", self.ir)
        write_json(self.case / "source-meter-index.json", self.meter)
        write_json(self.case / "source-statements.json", self.sources)
        self.observations, self.index, self.attempts = [], [], []
        for source, start, end, context_end in zip(self.sources, (0, 4), (4, 8), (8, 12)):
            alignment = align_statement(source, self.ir, self.meter)
            self.assertEqual(alignment["status"], "exact_coordinate")
            scope = scope_for(self.ir, start, end, 0, context_end)
            scope["case_id"] = source["case_id"]
            scope["source_statement_ref"] = {
                "record_id": source["record_id"], "record_sha256": source["record_sha256"]}
            scope["alignment_ref"] = trial.ref(alignment)
            observation = pattern.observe(self.ir, scope)
            path = self.case / (observation["record_id"] + ".json")
            write_json(path, observation)
            self.observations.append(observation)
            self.index.append({"record_id": observation["record_id"],
                               "record_sha256": observation["record_sha256"], "path": str(path),
                               "target_span": deepcopy(scope["target_span"]),
                               "context_span": deepcopy(scope["context_span"])})
            self.attempts.append({"source_statement_ref": deepcopy(scope["source_statement_ref"]),
                                  "status": alignment["status"], "alignment": alignment,
                                  "reasons": alignment["reasons"],
                                  "pattern_ref": {**trial.ref(observation), "path": str(path)}})
        write_json(self.alignment / "pattern-index.json", self.index)
        write_json(self.alignment / "alignment-attempts.json", self.attempts)
        # ROOT is an isolated manifest workspace, not the production repository.
        # Validators continue to use their real schema locations independently.
        self.code_path = self.root / "src/musicanote_harness/manifest_fixture.py"
        self.code_path.parent.mkdir(parents=True)
        self.code_path.write_text("# synthetic frozen manifest input\n", encoding="utf-8")
        schema_path = self.root / "docs/harmony/schemas/manifest_fixture.schema.json"
        schema_path.parent.mkdir(parents=True)
        write_json(schema_path, {})
        core_path = self.root / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"
        core_path.parent.mkdir(parents=True)
        write_json(core_path, {})
        self.refresh_parent_report(count=2)
        self.destination = self.output_root / "role-run"

    def refresh_parent_report(self, *, count=None):
        path = self.alignment / "report.json"
        report = read_json(path) if path.exists() else {
            "version": "musical-semantic-alignment-trial-0.1.1", "complete": True,
            "summary": {"literal_pattern_observations": len(self.index)}}
        if count is not None:
            report["summary"]["literal_pattern_observations"] = count
        report["artifact_hashes"] = {
            str(item.resolve()): trial.file_digest(item)
            for item in self.alignment.rglob("*") if item.is_file() and item != path}
        write_json(path, report)
        return report

    def output_index(self):
        return read_json(self.destination / "evidence-index.json")

    def test_success_sidecars_replay_inventory_denominator_and_input_immutability(self):
        originals = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with patch.object(trial, "import_romantext", wraps=trial.import_romantext) as importer:
            report = trial.run(self.alignment, self.destination)
        self.assertEqual(importer.call_count, 1)
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["input_observations"], 2)
        self.assertEqual(report["summary"]["score_files"], 1)
        self.assertEqual(report["summary"]["source_assumption_tracks"], 1)
        self.assertEqual(report["summary"]["literal_evidence_records"], 2)
        self.assertEqual(report["summary"]["status_counts"], {"conditional_evidence": 2})
        for field in ("human_validated", "training_eligible", "gold_eligible", "generation_ready"):
            self.assertEqual(report["summary"][field], 0)
        self.assertIsNone(report["summary"]["independent_piece_count"])
        self.assertEqual(report["changed_inputs_or_code"], [])
        for path, payload in originals.items():
            self.assertEqual(Path(path).read_bytes(), payload)
        plan = read_json(self.destination / "run-plan.json")
        parent = read_json(self.alignment / "report.json")
        expected_inputs = {str(self.alignment / "report.json"): trial.file_digest(self.alignment / "report.json"),
                           **parent["artifact_hashes"]}
        self.assertEqual(plan["inputs"], expected_inputs)
        self.assertEqual(len(plan["code"]), 3)
        self.assertEqual(len(plan["pattern_refs"]), 2)
        self.assertTrue(plan["source_annotation_is_assumption_not_answer"])
        self.assertFalse(plan["external_transmission"])
        self.assertEqual(set(plan["environment"]["packages"]), {"music21", "jsonschema", "referencing"})
        results = self.output_index()
        self.assertEqual(len(results), 2)
        self.assertEqual(len({row["observation_ref"]["record_id"] for row in results}), 2)
        self.assertEqual(len({row["assumption_path"] for row in results}), 1)
        for item in results:
            track = read_json(item["assumption_path"])
            evidence = read_json(item["evidence_path"])
            observation = read_json(item["input_path"])
            validate_track(track, ir=self.ir)
            validate_evidence(evidence, ir=self.ir, observation=observation, tracks=[track])
            self.assertEqual(trial.ref(evidence), item["evidence_ref"])
            self.assertEqual(trial.ref(track), item["assumption_ref"])
            self.assertEqual(len(evidence["conditional"]), 1)
            self.assertFalse(evidence["semantics"]["roles_validated"])
        actual_artifacts = {str(path): trial.file_digest(path) for path in self.destination.rglob("*")
                            if path.is_file() and path.name != "report.json"}
        self.assertEqual(report["artifact_hashes"], actual_artifacts)
        for path, expected in {**plan["inputs"], **plan["code"]}.items():
            self.assertEqual(trial.file_digest(path), expected)

    def test_new_output_guard_rejects_root_outside_and_nested_parent_paths(self):
        for destination in (self.output_root, self.root / "outside-run", self.alignment / "nested-run"):
            with self.subTest(destination=destination), self.assertRaisesRegex(ValueError, "new_workspace_output"):
                trial.run(self.alignment, destination)
        self.assertFalse((self.root / "outside-run").exists())
        self.assertFalse((self.alignment / "nested-run").exists())

    def test_existing_output_is_rejected_without_overwriting_marker(self):
        self.destination.mkdir()
        marker = self.destination / "marker.txt"
        marker.write_text("preserve original", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "new_workspace_output"):
            trial.run(self.alignment, self.destination)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve original")
        self.assertEqual(list(self.destination.iterdir()), [marker])

    def test_unsupported_or_incomplete_parent_is_refused_before_write(self):
        path = self.alignment / "report.json"
        original = read_json(path)
        for field, value in (("version", "unsupported-parent-v0"), ("complete", False)):
            report = deepcopy(original)
            report[field] = value
            write_json(path, report)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "completed_supported_alignment"):
                trial.run(self.alignment, self.destination)
            self.assertFalse(self.destination.exists())
        write_json(path, original)

    def test_missing_changed_or_extra_parent_artifact_is_refused_before_write(self):
        original = self.analysis.read_bytes()
        for mode, reason in (("missing", "inventory_mismatch"),
                             ("changed", "upstream_artifact_changed"),
                             ("extra", "inventory_mismatch")):
            extra = self.alignment / "unregistered.txt"
            if mode == "missing":
                self.analysis.unlink()
            elif mode == "changed":
                self.analysis.write_bytes(original + b"\nNote: modified after freeze\n")
            else:
                extra.write_text("not in parent manifest", encoding="utf-8")
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, reason):
                trial.run(self.alignment, self.destination)
            self.assertFalse(self.destination.exists())
            self.analysis.write_bytes(original)
            if extra.exists():
                extra.unlink()

    def test_parent_observation_denominator_mismatch_is_refused_before_write(self):
        path = self.alignment / "report.json"
        report = read_json(path)
        report["summary"]["literal_pattern_observations"] = 3
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "pattern_denominator_mismatch"):
            trial.run(self.alignment, self.destination)
        self.assertFalse(self.destination.exists())

    def test_duplicate_identity_and_target_or_context_index_mismatch_are_refused(self):
        for mode, reason in (("duplicate", "duplicate_pattern_index_id"),
                             ("identity", "pattern_index_identity_mismatch"),
                             ("target", "pattern_index_scope_mismatch"),
                             ("context", "pattern_index_scope_mismatch")):
            index = deepcopy(self.index)
            if mode == "duplicate":
                index.append(deepcopy(index[0]))
            elif mode == "identity":
                index[0]["record_sha256"] = "f" * 64
            elif mode == "target":
                index[0]["target_span"]["end"] = pattern.q(3)
            else:
                index[0]["context_span"]["end"] = pattern.q(7)
            write_json(self.alignment / "pattern-index.json", index)
            self.refresh_parent_report(count=len(index))
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, reason):
                trial.run(self.alignment, self.destination)
            self.assertFalse(self.destination.exists())

    def test_incomplete_case_source_binding_preserves_blocked_window_and_other_window(self):
        write_json(self.case / "source-statements.json", self.sources[1:])
        self.refresh_parent_report()
        report = trial.run(self.alignment, self.destination)
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["input_observations"], 2)
        self.assertEqual(report["summary"]["status_counts"], {"blocked": 1, "conditional_evidence": 1})
        results = self.output_index()
        blocked = next(row for row in results if row["observation_ref"]["record_id"] == self.index[0]["record_id"])
        self.assertEqual(blocked["status"], "blocked")
        self.assertIsNone(blocked["evidence_ref"])
        self.assertIsNone(blocked["evidence_path"])
        self.assertTrue(any("missing_or_duplicate_observation_source_statement" in value for value in blocked["reasons"]))
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(row["status"] == "conditional_evidence" for row in results), 1)

    def test_importer_failure_retains_every_window_as_replayable_literal_only(self):
        originals = {str(path): path.read_bytes() for path in self.alignment.rglob("*") if path.is_file()}
        with patch.object(trial, "import_romantext", side_effect=ValueError("synthetic importer failure")) as importer:
            report = trial.run(self.alignment, self.destination)
        self.assertEqual(importer.call_count, 1)
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["harmony_import_failed_files"], 1)
        self.assertEqual(report["summary"]["literal_evidence_records"], 2)
        self.assertEqual(report["summary"]["status_counts"], {"literal_only": 2})
        for item in self.output_index():
            self.assertIsNone(item["assumption_ref"])
            self.assertIsNone(item["assumption_path"])
            self.assertTrue(any("synthetic importer failure" in reason for reason in item["reasons"]))
            evidence = read_json(item["evidence_path"])
            self.assertEqual(evidence["conditional"], [])
            validate_evidence(evidence, ir=self.ir, observation=read_json(item["input_path"]), tracks=[])
        for path, payload in originals.items():
            self.assertEqual(Path(path).read_bytes(), payload)

    def test_resealed_observation_omission_is_blocked_by_independent_ir_replay(self):
        observation = deepcopy(self.observations[0])
        observation["slots"].pop()
        reseal_observation(observation)
        pattern.validate_observation(observation)
        write_json(self.index[0]["path"], observation)
        index = deepcopy(self.index)
        index[0].update(trial.ref(observation))
        write_json(self.alignment / "pattern-index.json", index)
        self.refresh_parent_report()
        report = trial.run(self.alignment, self.destination)
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["input_observations"], 2)
        self.assertEqual(report["summary"]["status_counts"], {"blocked": 1, "conditional_evidence": 1})
        blocked = next(row for row in self.output_index() if row["observation_ref"] == trial.ref(observation))
        self.assertEqual(blocked["status"], "blocked")
        self.assertIsNone(blocked["evidence_ref"])
        self.assertTrue(any("reconstruction_mismatch" in reason for reason in blocked["reasons"]))

    def test_missing_duplicate_or_scope_inconsistent_alignment_preserves_blocked_outcome(self):
        for mode, reason in (("missing", "missing_or_duplicate_observation_alignment"),
                             ("duplicate", "missing_or_duplicate_observation_alignment"),
                             ("target", "observation_alignment_binding_mismatch")):
            attempts, index = deepcopy(self.attempts), deepcopy(self.index)
            observation = deepcopy(self.observations[0])
            if mode == "missing":
                attempts = attempts[1:]
            elif mode == "duplicate":
                attempts.append(deepcopy(attempts[0]))
            else:
                scope = deepcopy(observation["scope"])
                scope["target_span"]["end"] = pattern.q(3)
                observation = pattern.observe(self.ir, scope)
                index[0].update(trial.ref(observation), target_span=deepcopy(scope["target_span"]))
            write_json(self.alignment / "alignment-attempts.json", attempts)
            write_json(self.index[0]["path"], observation)
            write_json(self.alignment / "pattern-index.json", index)
            self.refresh_parent_report()
            destination = self.output_root / ("alignment-check-" + mode)
            with self.subTest(mode=mode):
                report = trial.run(self.alignment, destination)
                self.assertTrue(report["complete"])
                self.assertEqual(report["summary"]["input_observations"], 2)
                self.assertEqual(report["summary"]["status_counts"], {"blocked": 1, "conditional_evidence": 1})
                results = read_json(destination / "evidence-index.json")
                blocked = next(row for row in results if row["observation_ref"] == trial.ref(observation))
                self.assertIsNone(blocked["evidence_ref"])
                self.assertTrue(any(reason in value for value in blocked["reasons"]))

    def test_input_changed_during_run_is_reported_incomplete_with_denominator_intact(self):
        original_analyze = trial.analyze
        calls = []

        def analyze_then_external_change(*args, **kwargs):
            evidence = original_analyze(*args, **kwargs)
            if not calls:
                self.analysis.write_text(self.analysis.read_text(encoding="utf-8") +
                                         "Note: external edit during run\n", encoding="utf-8")
            calls.append(True)
            return evidence

        with patch.object(trial, "analyze", side_effect=analyze_then_external_change):
            report = trial.run(self.alignment, self.destination)
        self.assertFalse(report["complete"])
        self.assertIn(str(self.analysis), report["changed_inputs_or_code"])
        self.assertEqual(report["summary"]["input_observations"], 2)
        self.assertEqual(len(self.output_index()), 2)
        self.assertEqual(report["summary"]["status_counts"], {"conditional_evidence": 2})


if __name__ == "__main__":
    unittest.main()
