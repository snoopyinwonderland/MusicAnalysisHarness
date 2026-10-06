"""Disk-backed frozen-context geometry; exact parents, no new semantics."""
from collections import Counter
from copy import deepcopy
from contextlib import ExitStack, redirect_stdout
import gzip
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_frozen_context_voice_trial as trial
from musicanote_harness import harmony_context_integration_trial as integration
from musicanote_harness import harmony_breadth_trial as breadth
from musicanote_harness import harmony_voice_paths as legacy
from musicanote_harness import harmony_polyphonic_links as polyphonic
from musicanote_harness import musical_pattern_observation as pattern
from test_harmony_context_integration_trial import frozen_fixture
from test_source_locator_revision_trial import read_json, write_json, sha
import test_source_locator_revision_trial as source_fixture


def read_gzip(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def write_gzip(path, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    Path(path).write_bytes(gzip.compress(raw, mtime=0))


def fixture(root, *, rest_part=False):
    """Actual XML/IR/replay + selector + stored analysis + integration.

    The older replay fixture lacks annotation-lineage metadata required by this
    additive cohort adapter. Add literal hash/identity metadata to both parent
    manifests, without interpreting the opaque annotation bytes.
    """
    xml = source_fixture.XML
    if rest_part:
        xml = xml.replace("</part-list>", '<score-part id="P2"><part-name>Rest only</part-name></score-part></part-list>')
        second = '<part id="P2">' + "".join(
            f'<measure number="{i}">'
            + ('<attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>' if i == 1 else '')
            + '<note><rest/><duration>16</duration><voice>1</voice><type>whole</type></note></measure>'
            for i in range(1, 4)) + '</part>'
        xml = xml.replace('</score-partwise>', second + '</score-partwise>')
    with patch.object(source_fixture, "XML", xml), redirect_stdout(io.StringIO()):
        data = frozen_fixture(root)
    package_plan = read_json(data["breadth"] / "frozen-plan.json")
    package = package_plan["packages"][0]
    package["source"]["pair_id"] = package["pair_id"]
    entry = package["source"]["manifest_entry"]
    entry.update(manifest_entry_id="literal-test-entry", annotation_sha256=sha(data["labels"]),
                 annotation_lineage_id="opaque-fixture-label-lineage")
    replay_report_path = data["replay"] / "report.json"
    replay_report = read_json(replay_report_path)
    for row in replay_report["records"]:
        blob = read_gzip(row["artifact"])
        blob["manifest_entry"] = deepcopy(entry)
        write_gzip(row["artifact"], blob)
        row["sha256"] = sha(row["artifact"])
        replay_report["artifact_hashes"][row["artifact"]] = row["sha256"]
    write_json(replay_report_path, replay_report)
    package["plan"] = breadth.freeze_score(data["ir"], per_lane=2)
    package_plan["version"] = breadth.VERSION
    # Remove the old deliberately incomplete bookkeeping-only samples.
    for path in data["breadth"].glob("stored-*.json.gz"):
        path.unlink()
    write_json(data["breadth"] / "frozen-plan.json", package_plan)
    write_json(data["breadth"] / "run-contract.json", {"version": breadth.VERSION,
        "samples_per_lane": 2, "frozen_plan_sha256": sha(data["breadth"] / "frozen-plan.json"),
        "input_hashes": {str(data["plan"]): sha(data["plan"]), str(data["labels"]): sha(data["labels"])},
        "code_hashes": {str(Path(breadth.__file__).resolve()): sha(breadth.__file__)}})
    records = []
    for selected in package["plan"]["selected_samples"]:
        sample = selected["sample"]
        stored = breadth.analyze_sample(data["ir"], sample)
        path = data["breadth"] / ("actual-" + str(selected["plan_index"]) + ".json.gz")
        write_gzip(path, stored)
        records.append({"pair_id": package["pair_id"], "plan_index": selected["plan_index"],
            "sample_id": sample["sample_id"], "lane": deepcopy(sample["lane"]),
            "span": deepcopy(sample["span"]), "status": stored["summary"]["status"],
            "artifact": str(path), "sha256": sha(path)})
    write_json(data["breadth"] / "report.json", {"version": breadth.VERSION,
        "complete": True, "inputs_unchanged": True, "source_labels_used": False, "accuracy_measured": False,
        "frozen_packages": 1, "executed_windows": len(records),
        "status_counts": dict(Counter(row["status"] for row in records)), "records": records})
    with redirect_stdout(io.StringIO()):
        integrated_report = integration.run(data["breadth"], data["replay"], data["output"])
    data["integration"] = data["output"]
    data["output"] = root / "output/factorized"
    data["integration_report"] = integrated_report
    # Isolated manifest inventory for the new runner's code/schema guards.
    for path, content in [(root / "src/musicanote_harness/isolated_fixture.py", "# frozen test manifest\n"),
                          (root / "docs/harmony/schemas/isolated.json", "{}"),
                          (root / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json", "{}")]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return data


def refresh_parents(data):
    """Rebind disk fixture changes, so content guards—not stale bytes—are tested."""
    breadth_contract_path = data["breadth"] / "run-contract.json"
    contract = read_json(breadth_contract_path)
    contract["frozen_plan_sha256"] = sha(data["breadth"] / "frozen-plan.json")
    write_json(breadth_contract_path, contract)
    integration_contract_path = data["integration"] / "run-contract.json"
    contract = read_json(integration_contract_path)
    contract["input_hashes"] = {name: sha(name) for name in contract["input_hashes"]}
    write_json(integration_contract_path, contract)
    report_path = data["integration"] / "report.json"
    report = read_json(report_path)
    report["contract_sha256"] = sha(integration_contract_path)
    report["artifact_hashes"] = {name: sha(name) for name in report["artifact_hashes"]}
    for row in report["records"]:
        row["sha256"] = sha(row["artifact"])
    write_json(report_path, report)


class FrozenContextVoiceTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)
        root_patch = patch.object(trial, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def run_fixture(self, **options):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.data["integration"], self.data["output"], **options)

    def reject_before_output(self, error, **options):
        with self.assertRaisesRegex((ValueError, KeyError), error):
            self.run_fixture(**options)
        self.assertFalse(self.data["output"].exists())

    def test_real_pipeline_every_context_and_raw_lane_preserved_immutable(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        report = self.run_fixture()
        self.assertTrue(report["complete"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertTrue(report["computation_integrity_passed"])
        contexts = read_json(self.data["output"] / "observation-index.json")
        units = read_json(self.data["output"] / "unit-index.json")
        self.assertEqual(len(contexts), len(self.data["integration_report"]["records"]))
        self.assertEqual(report["summary"]["contexts"], len(contexts))
        self.assertEqual(report["summary"]["raw_lane_units"], sum(row["raw_lane_count"] for row in contexts))
        self.assertEqual(report["summary"]["original_final_statuses_preserved"],
                         self.data["integration_report"]["summary"]["previous_statuses_retained"])
        self.assertEqual(report["summary"]["original_stage_statuses_preserved"],
                         self.data["integration_report"]["summary"]["stage_statuses_retained"])
        for path, payload in before.items():
            self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(len(units), report["summary"]["raw_lane_units"])
        for row in units:
            packet = read_gzip(row["artifact"])
            self.assertIsNone(packet["selected"])
            self.assertFalse(packet["harmonic_or_role_claim"])
            self.assertFalse(packet["training_eligible"])
            self.assertFalse(packet["generation_ready"])
            comparison = packet["unit"]["legacy_geometry_comparison"]
            self.assertFalse(comparison["prior_inventory_available"])
            self.assertIsNone(comparison["legacy_possible_assignments"])
            self.assertFalse(comparison["legacy_recomputed_or_enumerated"])
            self.assertEqual(row["sha256"], sha(row["artifact"]))
        for name, expected in report["artifact_hashes"].items():
            self.assertEqual(sha(name), expected)
        plan = read_json(self.data["output"] / "run-plan.json")
        self.assertFalse(plan["synthetic_SOURCE_records_created"])
        self.assertFalse(plan["source_annotation_labels_consumed"])
        self.assertEqual(len(plan["expected_context_keys"]), len(contexts))
        self.assertIn("context-observed", plan["lane_inventory"])
        self.assertIsNone(report["summary"]["independent_piece_count"])

    def test_no_runtime_semantic_harmony_or_legacy_enumeration_callbacks(self):
        callbacks = ["musicanote_harness.musical_semantic_alignment.validate_alignment",
                     "musicanote_harness.musical_role_evidence.analyze",
                     "musicanote_harness.musical_harmony_assumption.build_track",
                     "musicanote_harness.harmony_breadth_trial.analyze_sample",
                     "musicanote_harness.harmony_progression_context.build",
                     "musicanote_harness.harmony_voice_paths.observe",
                     "musicanote_harness.harmony_voice_paths.partial_matchings",
                     "musicanote_harness.harmony_polyphonic_links.partial_matchings"]
        with ExitStack() as stack:
            blocked = [stack.enter_context(patch(name, side_effect=AssertionError("new semantics/enumeration forbidden")))
                       for name in callbacks]
            report = self.run_fixture()
        self.assertTrue(report["complete"])
        for callback in blocked:
            callback.assert_not_called()

    def test_existing_output_and_outside_workspace_never_overwritten(self):
        self.data["output"].mkdir(parents=True)
        marker = self.data["output"] / "keep"
        marker.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "output_must_be_new"):
            self.run_fixture()
        self.assertEqual(marker.read_bytes(), b"keep")
        for output in [self.root / "outside", self.root / "output", self.data["integration"] / "child"]:
            with self.assertRaisesRegex(ValueError, "output_must_be_new"):
                trial.run(self.data["integration"], output)
            self.assertFalse(output.exists() and output != self.root / "output")

    def test_configuration_requires_supported_strict_positive_integers(self):
        for options in [{"unknown": 1}, {"max_events": True}, {"max_edges": 0},
                        {"max_factors": -1}, {"work_budget": 1.5}]:
            self.reject_before_output("invalid_factor_trial_budget", **options)

    def test_integration_version_and_strict_report_flags_rejected(self):
        path = self.data["integration"] / "report.json"
        original = read_json(path)
        for field, value, error in [("version", "unknown", "unsupported_integration_version"),
            ("complete", 1, "unsafe_integration_report"), ("inputs_and_code_unchanged", False, "unsafe_integration_report"),
            ("artifacts_unchanged", False, "unsafe_integration_report"),
            ("source_labels_used", True, "unsafe_integration_report"), ("engine_recomputed", True, "unsafe_integration_report"),
            ("training_promoted", True, "unsafe_integration_report"), ("gate_changed", None, "unsafe_integration_report")]:
            changed = deepcopy(original)
            changed[field] = value
            write_json(path, changed)
            with self.subTest(field=field):
                self.reject_before_output(error)
        write_json(path, original)

    def test_upstream_versions_and_strict_report_flags_rejected(self):
        for directory, changes in [
            (self.data["breadth"], [("version", "unknown", "unsupported_upstream_version"),
                ("complete", 1, "unsafe_breadth_report"), ("inputs_unchanged", False, "unsafe_breadth_report"),
                ("source_labels_used", True, "unsafe_breadth_report")]),
            (self.data["replay"], [("version", "unknown", "unsupported_upstream_version"),
                ("complete", 1, "unsafe_replay_report"), ("engine_recomputed", True, "unsafe_replay_report"),
                ("annotation_retargeted", None, "unsafe_replay_report")])]:
            path = directory / "report.json"
            original = read_json(path)
            for field, value, error in changes:
                changed = deepcopy(original)
                changed[field] = value
                write_json(path, changed)
                refresh_parents(self.data)
                with self.subTest(parent=directory.name, field=field):
                    self.reject_before_output(error)
            write_json(path, original)
            refresh_parents(self.data)

    def test_changed_registered_parent_and_source_bytes_rejected(self):
        paths = [self.data["source"], self.data["labels"], self.data["original"], self.data["frozen"], self.data["prep"],
                 self.data["breadth"] / "run-contract.json", self.data["replay"] / "run-contract.json",
                 Path(self.data["integration_report"]["records"][0]["artifact"]),
                 Path(self.data["integration_report"]["measure_revisions"][0]["sidecar"])]
        for path in paths:
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.subTest(path=path.name):
                self.reject_before_output("input_hash_mismatch")
            path.write_bytes(original)

    def test_unregistered_files_cannot_silently_extend_parent_inventory(self):
        for directory in [self.data["integration"], self.data["breadth"], self.data["replay"]]:
            path = directory / "unregistered.txt"
            path.write_bytes(b"unregistered")
            with self.subTest(parent=directory.name):
                self.reject_before_output("parent_artifact_inventory_mismatch")
            path.unlink()

    def test_missing_duplicate_and_unknown_integration_contexts_rejected(self):
        path = self.data["integration"] / "report.json"
        original = read_json(path)
        for mode, error in [("missing", "frozen_context_coverage_mismatch"),
                            ("duplicate", "duplicate_integration_context"),
                            ("unknown", "frozen_context_coverage_mismatch")]:
            changed = deepcopy(original)
            if mode == "missing":
                changed["records"].pop()
            elif mode == "duplicate":
                changed["records"].append(deepcopy(changed["records"][0]))
            else:
                changed["records"][0]["sample_id"] = "not-planned"
            write_json(path, changed)
            with self.subTest(mode=mode):
                self.reject_before_output(error)
        write_json(path, original)

    def test_duplicate_breadth_context_and_plan_context_rejected(self):
        path = self.data["breadth"] / "report.json"
        old = read_json(path)
        changed = deepcopy(old)
        changed["records"].append(deepcopy(changed["records"][0]))
        write_json(path, changed)
        refresh_parents(self.data)
        self.reject_before_output("duplicate_breadth_context")
        write_json(path, old)
        plan_path = self.data["breadth"] / "frozen-plan.json"
        plan = read_json(plan_path)
        plan["packages"][0]["plan"]["selected_samples"].append(deepcopy(plan["packages"][0]["plan"]["selected_samples"][0]))
        write_json(plan_path, plan)
        refresh_parents(self.data)
        self.reject_before_output("duplicate_frozen_context")

    def test_package_missing_duplicate_revision_and_source_identity_rejected(self):
        plan_path = self.data["breadth"] / "frozen-plan.json"
        plan = read_json(plan_path)
        original = deepcopy(plan)
        for mode, error in [("missing", "frozen_package_coverage_mismatch"),
                            ("duplicate", "duplicate_frozen_package"),
                            ("identity", "package_source_identity_mismatch")]:
            changed = deepcopy(original)
            if mode == "missing":
                changed["packages"] = []
            elif mode == "duplicate":
                changed["packages"] *= 2
            else:
                changed["packages"][0]["source"]["pair_id"] = "another"
            write_json(plan_path, changed)
            refresh_parents(self.data)
            with self.subTest(mode=mode):
                self.reject_before_output(error)
        write_json(plan_path, original)
        refresh_parents(self.data)
        path = self.data["integration"] / "report.json"
        report = read_json(path)
        report["measure_revisions"].append(deepcopy(report["measure_revisions"][0]))
        write_json(path, report)
        self.reject_before_output("duplicate_revision")

    def test_replay_missing_duplicate_or_foreign_package_rejected(self):
        path = self.data["replay"] / "report.json"
        original = read_json(path)
        for mode, error in [("missing", "frozen_package_coverage_mismatch"),
                            ("duplicate", "duplicate_replay_package"),
                            ("foreign", "frozen_package_coverage_mismatch")]:
            changed = deepcopy(original)
            if mode == "missing":
                changed["records"] = []
            elif mode == "duplicate":
                changed["records"] *= 2
            else:
                changed["records"][0]["pair_id"] = "foreign-pair"
            write_json(path, changed)
            refresh_parents(self.data)
            with self.subTest(mode=mode):
                self.reject_before_output(error)
        write_json(path, original)

    def test_denominator_status_and_work_family_summary_cannot_drift(self):
        integration_path = self.data["integration"] / "report.json"
        original = read_json(integration_path)
        for field, value, error in [
            ("work_families", 999, "work_family_denominator_mismatch"),
            ("previous_statuses_retained", {"ready": 999}, "integration_original_status_denominator_mismatch")]:
            changed = deepcopy(original)
            changed["summary"][field] = value
            write_json(integration_path, changed)
            with self.subTest(field=field):
                self.reject_before_output(error)
        write_json(integration_path, original)
        path = self.data["breadth"] / "report.json"
        report = read_json(path)
        report["status_counts"] = {"ready": 999}
        write_json(path, report)
        refresh_parents(self.data)
        self.reject_before_output("breadth_original_status_denominator_mismatch")

    def test_historical_breadth_producer_code_is_not_rerun_or_current_certified(self):
        path = self.data["breadth"] / "run-contract.json"
        contract = read_json(path)
        contract["code_hashes"] = {str(Path(breadth.__file__).resolve()): "historical-producer-byte-hash"}
        write_json(path, contract)
        refresh_parents(self.data)
        with patch.object(breadth, "analyze_sample", side_effect=AssertionError("historical engine must not rerun")) as old:
            report = self.run_fixture()
        self.assertTrue(report["complete"])
        old.assert_not_called()
        plan = read_json(self.data["output"] / "run-plan.json")
        self.assertFalse(plan["harmonic_engine_recomputed"])

    def test_known_breadth_diagnostics_frozen_without_inference_and_provenance_checked(self):
        for name in ("inventory.json", "progress.json"):
            (self.data["breadth"] / name).write_bytes(b"opaque diagnostic; not JSON or admission evidence")
        plan = read_json(self.data["breadth"] / "frozen-plan.json")
        source = plan["packages"][0]["source"]
        path = Path(source["frozen_ir_path"]).parent / "provenance.json"
        changed = deepcopy(source)
        changed["pair_id"] = "foreign"
        write_json(path, changed)
        self.reject_before_output("breadth_source_provenance_mismatch")
        write_json(path, source)
        report = self.run_fixture()
        self.assertTrue(report["complete"])
        recorded = read_json(self.data["output"] / "run-plan.json")["inputs"]
        for name in ("inventory.json", "progress.json"):
            path = self.data["breadth"] / name
            self.assertEqual(recorded[str(path.resolve())], sha(path))

    def test_protected_split_non_boolean_research_approval_and_pitch_policy(self):
        path = self.data["breadth"] / "frozen-plan.json"
        original = read_json(path)
        for mode, error in [("split", "protected_or_unassigned_split"),
                            ("rights", "internal_research_not_approved"),
                            ("pitch", "source_policy_or_identity_mismatch")]:
            plan = deepcopy(original)
            source = plan["packages"][0]["source"]
            if mode == "split":
                source["manifest_entry"]["split"] = "holdout"
            elif mode == "rights":
                source["manifest_entry"]["rights"]["internal_research_use"] = 1
            else:
                source["pitch_policy"]["harmonic_replay_allowed"] = False
            write_json(path, plan)
            refresh_parents(self.data)
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, error):
                self.run_fixture()
            self.assertFalse((self.data["output"] / "report.json").exists())
        write_json(path, original)

    def test_selector_reconstruction_rejects_self_consistent_resampling(self):
        path = self.data["breadth"] / "frozen-plan.json"
        plan = read_json(path)
        plan["packages"][0]["plan"]["samples_per_lane"] = 999
        write_json(path, plan)
        refresh_parents(self.data)
        with self.assertRaisesRegex(ValueError, "frozen_selector_reconstruction_mismatch"):
            self.run_fixture()
        self.assertFalse((self.data["output"] / "report.json").exists())

    def test_previous_status_cannot_be_self_consistently_replaced(self):
        path = self.data["integration"] / "report.json"
        report = read_json(path)
        report["records"][0]["previous_status"] = "invented-ready"
        report["summary"]["previous_statuses_retained"] = dict(Counter(row["previous_status"] for row in report["records"]))
        write_json(path, report)
        self.reject_before_output("original_status_changed")

    def test_rebound_packet_source_verdict_flags_still_rejected(self):
        report = read_json(self.data["integration"] / "report.json")
        path = Path(report["records"][0]["artifact"])
        packet = read_gzip(path)
        packet["provenance"]["source_labels_used"] = True
        write_gzip(path, packet)
        refresh_parents(self.data)
        with self.assertRaisesRegex(ValueError, "unsafe_integration_provenance"):
            self.run_fixture()
        self.assertFalse((self.data["output"] / "report.json").exists())

    def test_rebound_revision_candidate_selection_still_replayed(self):
        path = self.data["integration"] / "report.json"
        report = read_json(path)
        report["measure_revisions"][0]["candidate_created"] = 1
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "invalid_explicit_revision_selection"):
            self.run_fixture()
        self.assertFalse((self.data["output"] / "report.json").exists())

    def test_stage_status_inventory_mismatch_prevents_final_success_report(self):
        path = self.data["integration"] / "report.json"
        report = read_json(path)
        report["summary"]["stage_statuses_retained"] = {"invented": {"ready": 500}}
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "original_stage_status_inventory_changed"):
            self.run_fixture()
        self.assertFalse((self.data["output"] / "report.json").exists())

    def test_unit_exception_retains_denominator_but_marks_integrity_incomplete(self):
        actual = trial._unit
        calls = 0
        def failed_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ValueError("explicit-fixture-integrity-failure")
            return actual(*args, **kwargs)
        with patch.object(trial, "_unit", side_effect=failed_once):
            report = self.run_fixture()
        rows = read_json(self.data["output"] / "unit-index.json")
        self.assertEqual(len(rows), calls)
        self.assertFalse(report["complete"])
        self.assertFalse(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["status_counts"]["integrity_or_computation_abstention"], 1)
        packet = read_gzip(rows[0]["artifact"])
        self.assertIsNone(packet["unit"]["graph"])
        self.assertEqual(packet["unit"]["constraint_probes"], [])
        self.assertIn("explicit-fixture-integrity-failure", rows[0]["reasons"][0])

    def test_external_annotation_or_schema_change_during_run_is_not_stable(self):
        actual = trial._unit
        changed = False
        def external_change(*args, **kwargs):
            nonlocal changed
            result = actual(*args, **kwargs)
            if not changed:
                changed = True
                self.data["labels"].write_bytes(b"outside writer changed opaque annotation bytes")
                schema = self.root / "docs/harmony/schemas/isolated.json"
                schema.write_bytes(b'{"external_change":true}')
            return result
        with patch.object(trial, "_unit", side_effect=external_change):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIn(str(self.data["labels"]), report["changed_inputs_or_code"])
        self.assertIn(str(self.root / "docs/harmony/schemas/isolated.json"), report["changed_inputs_or_code"])

    def test_new_source_or_parent_files_during_run_are_inventory_changes(self):
        actual = trial._unit
        changed = False
        def external_inventory_change(*args, **kwargs):
            nonlocal changed
            result = actual(*args, **kwargs)
            if not changed:
                changed = True
                (self.root / "src/musicanote_harness/external.py").write_bytes(b"# external source")
                (self.data["breadth"] / "external.json").write_bytes(b"{}")
            return result
        with patch.object(trial, "_unit", side_effect=external_inventory_change):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIn("source_or_schema_inventory_changed", report["changed_inputs_or_code"])
        self.assertIn("parent_artifact_inventory_changed:" + str(self.data["breadth"].resolve()),
                      report["changed_inputs_or_code"])

    def alter_output_during_unit(self, mode):
        actual = trial._unit
        changed = False
        def external_output_change(*args, **kwargs):
            nonlocal changed
            result = actual(*args, **kwargs)
            if not changed:
                changed = True
                target = self.data["output"] / "run-plan.json"
                if mode == "change":
                    target.write_bytes(target.read_bytes() + b" ")
                elif mode == "delete":
                    target.unlink()
                else:
                    (self.data["output"] / "external-artifact.json").write_bytes(b"{}")
            return result
        with patch.object(trial, "_unit", side_effect=external_output_change):
            report = self.run_fixture()
        self.assertFalse(report["complete"])
        self.assertFalse(report["artifacts_unchanged"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertTrue(report["computation_integrity_passed"])
        if mode == "change":
            self.assertIn(str((self.data["output"] / "run-plan.json").resolve()), report["changed_artifacts"])
        else:
            self.assertIn("output_artifact_inventory_changed", report["changed_artifacts"])
        self.assertEqual(len(read_json(self.data["output"] / "unit-index.json")), report["summary"]["raw_lane_units"])

    def test_output_artifact_change_is_not_finally_rehashed_as_valid(self):
        self.alter_output_during_unit("change")

    def test_output_artifact_deletion_is_incomplete(self):
        self.alter_output_during_unit("delete")

    def test_output_artifact_addition_is_incomplete(self):
        self.alter_output_during_unit("add")

    def test_mutating_observation_from_unit_fails_context_integrity_closed(self):
        actual = trial._unit
        def mutate_observation(ir, observation, lane, config):
            result = actual(ir, observation, lane, config)
            observation["origin"]["target_policy"] = "tampered"
            return result
        with patch.object(trial, "_unit", side_effect=mutate_observation), self.assertRaisesRegex(ValueError, "context_inputs_mutated"):
            self.run_fixture()
        self.assertFalse((self.data["output"] / "report.json").exists())

    def test_raw_lanes_include_context_rest_part_not_only_sample_lane(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root, rest_part=True)
            with patch.object(trial, "ROOT", root), redirect_stdout(io.StringIO()):
                report = trial.run(data["integration"], data["output"])
            self.assertTrue(report["complete"])
            observations = read_json(data["output"] / "observation-index.json")
            units = read_json(data["output"] / "unit-index.json")
            self.assertTrue(all(row["raw_lane_count"] == 2 for row in observations))
            self.assertEqual(len(units), 2 * len(observations))
            self.assertTrue(any("empty_lane" in row["reasons"] for row in units))
            for row in observations:
                observation = read_json(row["path"])
                self.assertEqual(len(observation["raw_lanes"]), 2)
                self.assertFalse(observation["origin"]["source_statement_or_alignment_certified"])


if __name__ == "__main__":
    unittest.main()
