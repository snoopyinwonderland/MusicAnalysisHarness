"""Append-only progression evidence authenticates phase 19 and never selects."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_progression_evidence_trial as trial
from musicanote_harness import factor_progression_evidence as engine
from musicanote_harness import factor_delayed_obligation_trial as previous
from musicanote_harness import factor_delayed_obligations as delayed
from musicanote_harness import factor_grounded_relations as grounded
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_trial as storage
from test_factor_delayed_obligation_trial import DelayedFixture
from test_factor_grounded_relations import GroundedRelationsFixture
from test_factor_expanded_hypotheses import event
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyProgressionTrialGuardTests(unittest.TestCase):
    def test_new_direct_output_and_all_caps_checked_before_parent_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/old"
            old.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), \
                    patch.object(trial, "load_inputs", side_effect=AssertionError("parent read")):
                self.assertEqual(trial.SETTINGS, {"max_hypotheses": 64,
                    "max_comparisons": 4096, "query_work_budget": 100000})
                for destination in (root, old, root / "output/nested/child", root / "elsewhere/new"):
                    with self.subTest(destination=destination), self.assertRaises(ValueError):
                        trial.run("absent", destination)
                for name in trial.SETTINGS:
                    for value in (True, False, -1, 1.5, None, "1"):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("absent", root / "output/new", **{name: value})
                with self.assertRaises(ValueError):
                    trial.run("absent", root / "output/new", max_unregistered_claims=1)
            self.assertFalse((root / "output/new").exists())


class TechnicalPanelTests(unittest.TestCase):
    @staticmethod
    def record():
        def ref(name):
            return {"record_id": name, "record_sha256": "0" * 64}
        pair = {"group_id": "pair", "kind": "two_segment", "slots": [
            {"variant_ids": ["source", "source-other"]},
            {"variant_ids": ["target", "target-same", "target-different"]}]}
        seed = {**ref("kernel-b"), "group_id": "pair", "source_variant_ids": ["source"],
            "target_variant_ids": ["target"], "family": "V7", "quality": "M",
            "joint_plan_ref": ref("plan-supported"), "status": "conditional"}
        earlier = {**deepcopy(seed), **ref("kernel-a"), "status": "withheld"}
        later = {**deepcopy(seed), **ref("kernel-c"), "family": "V"}
        return {"obligation_kernel_inventory": [later, earlier, seed],
            "joint_plan_inventory": [{**ref("plan-supported"), "branches": [
                {"status": "unknown", "bundle_ref": ref("unknown-bundle")},
                {"status": "possible", "bundle_ref": ref("possible-bundle")}]}],
            "inherited_bundle_inventory": [{**ref("control-bundle"), "required_links": []}],
            "bundle_inventory": [{**ref("possible-bundle"), "required_links": [["a", "b"]]}],
            "path_groups": [pair, {"group_id": "full", "kind": "full_hold", "slots": [
                {"variant_ids": ["full-first", "full-other"]}]}],
            "keys": [ref("key-" + str(i)) for i in range(5)],
            "origin_inventory": [{"variant_id": "target", "profile_ref": ref("target-profile")},
                {"variant_id": "target-same", "profile_ref": ref("target-profile")},
                {"variant_id": "target-different", "profile_ref": ref("different-profile")}],
            "descriptor_inventory": [{**ref("target-profile"), "semantic_input": {
                "root": {"step": "C", "alter": 0}, "members": [{"step": "C", "alter": 0}]}},
                {**ref("different-profile"), "semantic_input": {
                    "root": {"step": "D", "alter": 0}, "members": [{"step": "D", "alter": 0}]}}]}

    def test_supported_seed_all_keys_functions_fullhold_and_target_alternate(self):
        record = self.record()
        before = deepcopy(record)
        panel = trial.technical_panel(record)
        self.assertEqual(record, before)
        self.assertEqual(panel, trial.technical_panel(deepcopy(record)))
        self.assertEqual(panel["seed_kernel_ref"], frozen._ref(record["obligation_kernel_inventory"][2]))
        self.assertEqual(panel["bundle_id"], "possible-bundle")
        self.assertEqual(panel["selection_policy"], trial.PANEL_POLICY)
        self.assertIs(panel["sampling_is_accuracy_evidence"], False)
        self.assertIs(panel["winning_hypothesis_selected"], False)
        self.assertEqual(len(panel["selectors"]), 60)
        seed_rows = panel["selectors"][:50]
        self.assertEqual({r["key_id"] for r in seed_rows}, {k["record_id"] for k in record["keys"]})
        for key in record["keys"]:
            rows = [r for r in seed_rows if r["key_id"] == key["record_id"]]
            self.assertEqual({(r["transition"]["family"], r["transition"]["quality"]) for r in rows},
                             {(f, q) for f in frozen.FAMILIES for q in ("M", "m")})
            self.assertTrue(all(r["group_id"] == "pair" and r["variant_ids"] == ["source", "target"] for r in rows))
        self.assertTrue(all(r["variant_ids"] == ["full-first"] and r["transition"] is None
                            for r in panel["selectors"][50:55]))
        self.assertTrue(all(r["variant_ids"] == ["source", "target-different"]
                            and r["transition"]["family"] == "V7" and r["transition"]["quality"] == "M"
                            for r in panel["selectors"][55:]))

    def test_first_tt_and_no_link_control_when_no_conditional_support(self):
        record = self.record()
        for kernel in record["obligation_kernel_inventory"]:
            kernel["status"] = "withheld"
        panel = trial.technical_panel(record)
        self.assertEqual(panel["seed_kernel_ref"]["record_id"], "kernel-a")
        self.assertEqual(panel["bundle_id"], "control-bundle")
        self.assertIs(panel["seed_supported_in_saved_phase19"], False)

    def test_fullhold_only_remains_complete_key_panel_not_accuracy_sample(self):
        record = self.record()
        record["obligation_kernel_inventory"] = []
        record["path_groups"] = record["path_groups"][1:]
        panel = trial.technical_panel(record)
        self.assertEqual(len(panel["selectors"]), 5)
        self.assertIsNone(panel["seed_kernel_ref"])
        self.assertTrue(all(r["transition"] is None for r in panel["selectors"]))
        self.assertIs(panel["sampling_is_accuracy_evidence"], False)

    def test_panel_does_not_use_source_labels_to_change_selection(self):
        record = self.record()
        expected = trial.technical_panel(record)
        record["source_labels"] = {"winner": "target-different", "key": "key-4", "family": "vii7"}
        for origin in record["origin_inventory"]:
            origin["provenance"] = {"SOURCE": "gold label says prefer this"}
        self.assertEqual(trial.technical_panel(record), expected)


class ProgressionFixture:
    """Compose the old fixture, not any of its old test classes/methods."""
    @classmethod
    def setUpClass(cls):
        factory = GroundedRelationsFixture()
        factory.addCleanup = cls.addClassCleanup
        factory.setUp()
        cls.real_case = factory.frozen_case(factory.make(
            signatures=[{"fifths": 0, "mode_hint": None}]))
        cls.real_grounding = grounded.build_grounding(*cls.real_case[0], *cls.real_case[1:])

    def setUp(self):
        fixture = DelayedFixture()
        fixture.addCleanup = self.addCleanup
        fixture.assertTrue = self.assertTrue
        fixture.real_case = self.real_case
        fixture.real_grounding = self.real_grounding
        fixture.setUp()
        self.fixture = fixture
        self.root = fixture.root
        self.producer = fixture.producer
        self.prior = fixture.prior
        self.grounding_parent = fixture.grounding_parent
        self.delayed_parent = fixture.output
        with redirect_stdout(io.StringIO()):
            report = previous.run(fixture.boundary_parent, self.delayed_parent)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.parent_report = read_json(self.delayed_parent / "report.json")
        self.parent_rows = read_json(self.delayed_parent / "context-index.json")
        self.output = self.root / "output/progression-child"
        patched = patch.object(trial, "ROOT", self.root)
        patched.start()
        self.addCleanup(patched.stop)

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.delayed_parent, self.output, **kwargs)

    def refresh_parent(self):
        path = self.delayed_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(path, report)

    def mutate_rows(self, mutate):
        path = self.delayed_parent / "context-index.json"
        rows = read_json(path)
        mutate(rows)
        write_json(path, rows)
        self.refresh_parent()

    def reject_before_output(self, expression=""):
        with self.assertRaisesRegex(ValueError, expression):
            self.execute()
        self.assertFalse(self.output.exists())

    @staticmethod
    def counted_comparison(*args, **kwargs):
        return frozen._seal({"version": "progression-counting-fixture-0.1.0",
            "status": "fixture_progression_evidence_not_musical_claim",
            "summary": {"known_zero": 0, "computed_relations": 2, "unknown_comparisons": None,
                "not_an_integer_metric": False, "also_not_an_integer_metric": True,
                "nested_breakdown": {"held": 1}}}, "fmpefixture_")

    def execute_counted(self, **kwargs):
        with patch.object(engine, "compare_prepared", side_effect=self.counted_comparison):
            return self.execute(**kwargs)

    def assert_denominators(self, report):
        for name in (*trial.DENOMINATORS, "declared_contexts", "declared_original_raw_lanes",
                     "unexecuted_original_contexts", "unexecuted_original_raw_lanes"):
            self.assertEqual(report["summary"][name], self.parent_report["summary"][name], name)
        self.assertEqual(report["parent_summary"], self.parent_report["summary"])
        self.assertEqual(report["summary"]["unexecuted_original_contexts"], 1)
        self.assertEqual(report["summary"]["unexecuted_original_raw_lanes"], 1)
        self.assertIsNone(report["selected"])
        self.assertIs(report["conditional_progression_comparison_stage_enabled"], True)
        for name in (*trial.POLICY_FALSE, "cohort_complete", "all_logical_paths_evaluated",
                     "sample_is_accuracy_evaluation"):
            self.assertIs(report[name], False, name)
        rows = read_json(self.output / "context-index.json")
        self.assertEqual([r["context_key"] for r in rows], [r["context_key"] for r in self.parent_rows])
        self.assertEqual(report["summary"]["progression_saved_contexts"],
                         sum(r["progression_comparison"] is not None for r in rows))
        self.assertEqual(report["summary"]["progression_failed_contexts"],
                         sum(r["status"] == "calculation_failure" for r in rows))
        inherited = (*previous.INHERITED_ROW_FIELDS, "boundary_explanations", "boundary_counts",
                     "delayed_obligations", "delayed_counts")
        for row, original in zip(rows, self.parent_rows):
            for name in inherited:
                self.assertEqual(row[name], original[name], name)
            self.assertEqual(row["old_row_sha256"], trial.digest(original))
            self.assertIsNone(row["old_hypothesis_counts"]["original_path_product"])

    def adopt_two_slot_held_parent(self):
        factory = GroundedRelationsFixture()
        factory.addCleanup = self.addCleanup
        factory.setUp()
        case = factory.frozen_case(factory.make([[event(["C3", "E4", "G4"], 0, 2),
            event(["D3", "F4", "A4"], 2, 2)]], signatures=[{"fifths": 0, "mode_hint": None}]))
        ir, scope = case[0]
        hypotheses, index, relations = case[1:]
        original = self.fixture.original_row
        key = tuple(original["context_key"])
        owned = self.prior["cases"][key]
        self.prior["cases"][key] = (owned[0], ir, owned[2], scope, hypotheses, owned[5], index, relations)
        artifacts = {}
        path = storage._save(self.prior["directory"], "relations/" + relations["record_id"] + ".json.gz",
                             relations, artifacts, compressed=True)
        self.prior["hashes"].update(artifacts)
        self.prior["inventory"].update(artifacts)
        original.update(old_lane_refs=deepcopy(scope["raw_lanes"]),
            expanded_scope={"record_ref": frozen._ref(scope)}, hypotheses={"record_ref": frozen._ref(hypotheses)},
            indexed_universe={"record_ref": frozen._ref(index)}, index_counts=deepcopy(index["summary"]),
            relations={"artifact": str(path), "sha256": sha(path), "record_ref": frozen._ref(relations),
                       "status": relations["status"]}, relation_counts=deepcopy(relations["summary"]))
        count = index["summary"]
        self.prior["report"]["summary"].update(old_raw_lanes=len(scope["raw_lanes"]),
            indexed_groups=count["groups"], logical_paths=count["logical_paths"],
            logical_path_key_tuples=count["logical_path_key_tuples"],
            logical_function_rows=count["logical_function_shapes"], unknown_logical_groups=count["unknown_product_groups"],
            origin_variants=count["indexed_variants"], shared_profile_descriptors=count["shared_profile_descriptors"])
        fresh_grounding = self.root / "output/two-slot-grounding"
        fresh_temporal = self.root / "output/two-slot-temporal"
        fresh_boundary = self.root / "output/two-slot-boundary"
        held_delayed = self.root / "output/two-slot-held-delayed"
        with redirect_stdout(io.StringIO()):
            report = previous.previous.previous.previous.run(self.prior["directory"], fresh_grounding)
            self.assertTrue(report["scope_calculation_complete"], report)
            report = previous.previous.previous.run(fresh_grounding, fresh_temporal)
            self.assertTrue(report["scope_calculation_complete"], report)
            report = previous.previous.run(fresh_temporal, fresh_boundary)
            self.assertTrue(report["scope_calculation_complete"], report)
            report = previous.run(fresh_boundary, held_delayed, max_obligation_kernels=0)
            self.assertTrue(report["scope_calculation_complete"], report)
        self.delayed_parent = held_delayed
        self.parent_report = read_json(held_delayed / "report.json")
        self.parent_rows = read_json(held_delayed / "context-index.json")


class ProgressionParentGuardTests(ProgressionFixture, unittest.TestCase):
    def test_parent_bytes_changed_or_registered_record_deleted_before_output(self):
        path = self.delayed_parent / "context-index.json"
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        self.reject_before_output("hash_mismatch")
        path.write_bytes(original)
        Path(self.parent_rows[0]["delayed_obligations"]["artifact"]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_extra_file_and_rehashed_extra_not_absorbed(self):
        extra = self.delayed_parent / "unregistered.json"
        write_json(extra, {})
        self.reject_before_output("inventory")
        path = self.delayed_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"][str(extra)] = sha(extra)
        write_json(path, report)
        self.reject_before_output("inventory")

    def test_foreign_delayed_folder_not_authority(self):
        original = Path(self.parent_rows[0]["delayed_obligations"]["artifact"])
        foreign = self.delayed_parent / "foreign" / original.name
        foreign.parent.mkdir(parents=True)
        write_gzip(foreign, read_gzip(original))
        self.mutate_rows(lambda rows: rows[0]["delayed_obligations"].update(
            artifact=str(foreign), sha256=sha(foreign)))
        original.unlink()
        path = self.delayed_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"].pop(str(original))
        report["artifact_hashes"][str(foreign)] = sha(foreign)
        write_json(path, report)
        self.refresh_parent()
        self.reject_before_output("foreign_or_unregistered")

    def test_registration_reference_status_sha_and_extra_fields_rejected(self):
        for changes in ({"status": "confirmed"}, {"sha256": "0" * 64},
                {"record_ref": {"record_id": delayed.PREFIX + "0" * 24, "record_sha256": "0" * 64}},
                {"unregistered_claim": True}):
            with self.subTest(changes=changes):
                rows = deepcopy(self.parent_rows)
                rows[0]["delayed_obligations"].update(changes)
                write_json(self.delayed_parent / "context-index.json", rows)
                self.refresh_parent()
                self.reject_before_output()

    def test_context_deletion_origin_count_and_typed_count_changes_rejected(self):
        variants = [[], [dict(deepcopy(self.parent_rows[0]), old_row_sha256="0" * 64)],
                    [dict(deepcopy(self.parent_rows[0]), delayed_counts={})]]
        changed = deepcopy(self.parent_rows)
        changed[0]["old_hypothesis_counts"]["original_path_product"] = 0
        variants.append(changed)
        changed = deepcopy(self.parent_rows)
        metric = next(k for k, v in changed[0]["delayed_counts"].items() if type(v) is int)
        changed[0]["delayed_counts"][metric] = float(changed[0]["delayed_counts"][metric])
        variants.append(changed)
        changed = deepcopy(self.parent_rows)
        changed[0]["unregistered_claim"] = True
        variants.append(changed)
        for rows in variants:
            with self.subTest(rows=rows):
                write_json(self.delayed_parent / "context-index.json", rows)
                self.refresh_parent()
                self.reject_before_output()

    def test_closed_plan_full_input_closure_lineage_and_limits(self):
        path = self.delayed_parent / "run-plan.json"
        original = read_json(path)
        extra = self.root / "fake-input.json"
        write_json(extra, {})
        variants = []
        for name, value in (("parent_report_sha256", "0" * 64),
                            ("coverage", "all_music_certified"), ("unregistered_semantics", True),
                            ("source_labels_used_for_inference", True), ("selected_contexts", [])):
            changed = deepcopy(original)
            changed[name] = value
            variants.append(changed)
        changed = deepcopy(original)
        changed["inputs"].pop(next(iter(changed["inputs"])))
        variants.append(changed)
        changed = deepcopy(original)
        changed["inputs"][str(extra)] = sha(extra)
        variants.append(changed)
        changed = deepcopy(original)
        changed["settings"][next(iter(changed["settings"]))] = False
        variants.append(changed)
        for plan in variants:
            with self.subTest(plan=plan):
                write_json(path, plan)
                self.refresh_parent()
                self.reject_before_output()

    def test_closed_report_policy_summary_and_typed_integer_ledger(self):
        path = self.delayed_parent / "report.json"
        original = read_json(path)
        variants = []
        for name, value in (("selected", "chosen"), ("training_eligible", True),
                ("conditional_delayed_obligation_stage_enabled", False), ("delayed_resolution_confirmed", True),
                ("scope_calculation_complete", False), ("parent_summary", {}), ("summary", {}),
                ("unregistered_semantics", True)):
            report = deepcopy(original)
            report[name] = value
            variants.append(report)
        report = deepcopy(original)
        report.pop("selected")
        variants.append(report)
        for value in (True, 0.0):
            report = deepcopy(original)
            ledger = report["summary"]["delayed_integer_subtotals"]
            ledger[next(iter(ledger))] = value
            variants.append(report)
        report = deepcopy(original)
        report["summary"]["unexecuted_original_contexts"] = 0
        variants.append(report)
        for report in variants:
            with self.subTest(report=report):
                write_json(path, report)
                self.reject_before_output()

    def test_producer_and_ancestor_input_bytes_remain_protected(self):
        for path in (self.producer, self.prior["directory"] / "report.json",
                     self.grounding_parent / "context-index.json"):
            original = path.read_bytes()
            with self.subTest(path=path):
                path.write_bytes(original + b" ")
                self.reject_before_output("hash_mismatch")
            path.write_bytes(original)

    def test_empty_foreign_and_missing_unchanged_producer_registration_rejected(self):
        path = self.delayed_parent / "run-plan.json"
        original = read_json(path)
        extra = self.root / "foreign-producer.py"
        write_json(extra, {"not_current_producer": True})
        variants = []
        changed = deepcopy(original)
        changed["code"] = {}
        variants.append(changed)
        changed = deepcopy(original)
        changed["code"][str(extra)] = sha(extra)
        variants.append(changed)
        changed = deepcopy(original)
        changed["code"].pop(str(self.producer))
        variants.append(changed)
        producer_bytes = self.producer.read_bytes()
        for plan in variants:
            with self.subTest(plan=plan):
                write_json(path, plan)
                self.refresh_parent()
                self.reject_before_output("producer_inventory")
                self.assertEqual(self.producer.read_bytes(), producer_bytes)

    def test_resealed_delayed_body_cannot_bypass_fresh_replay(self):
        old_path = Path(self.parent_rows[0]["delayed_obligations"]["artifact"])
        value = read_gzip(old_path)
        metric = next(k for k, v in value["summary"].items() if type(v) is int)
        value["summary"][metric] += 1
        value.pop("record_id")
        value.pop("record_sha256")
        changed = frozen._seal(value, delayed.PREFIX)
        new_path = old_path.parent / (changed["record_id"] + ".json.gz")
        write_gzip(new_path, changed)
        self.mutate_rows(lambda rows: rows[0].update(
            delayed_obligations={"artifact": str(new_path), "sha256": sha(new_path),
                "record_ref": frozen._ref(changed), "status": changed["status"]},
            delayed_counts=changed["summary"]))
        old_path.unlink()
        path = self.delayed_parent / "report.json"
        report = read_json(path)
        report["artifact_hashes"].pop(str(old_path))
        report["artifact_hashes"][str(new_path)] = sha(new_path)
        report["summary"]["delayed_integer_subtotals"][metric] += 1
        write_json(path, report)
        self.refresh_parent()
        self.reject_before_output()


class ProgressionRunTests(ProgressionFixture, unittest.TestCase):
    def test_parent_replay_once_and_cached_issued_tuple_twelve(self):
        with patch.object(previous, "load_inputs", wraps=previous.load_inputs) as parent_load, \
                patch.object(engine, "prepare_comparison_prepared", wraps=engine.prepare_comparison_prepared) as prepare, \
                redirect_stdout(io.StringIO()):
            data = trial.load_inputs(self.delayed_parent)
        self.assertEqual(parent_load.call_count, 1)
        self.assertEqual(prepare.call_count, 1)
        with patch.object(previous, "load_case", side_effect=AssertionError("second source replay")):
            case = trial.load_case(data, data["rows"][0])
            self.assertEqual(len(case), 12)
            self.assertIs(trial.load_case(data, data["rows"][0]), case)
            self.assertEqual(frozen._ref(case[-1]), self.parent_rows[0]["delayed_obligations"]["record_ref"])

    def test_real_engine_preserves_append_only_inputs_and_creation_inventory(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        row = read_json(self.output / "context-index.json")[0]
        value = read_gzip(row["progression_comparison"]["artifact"])
        self.assertEqual(set(row), {"context_key", "old_row_sha256", *trial.INHERITED_ROW_FIELDS,
            "delayed_obligations", "delayed_counts", "progression_comparison", "progression_counts",
            "technical_panel", "status", "error", "elapsed_seconds"})
        self.assertEqual(row["progression_counts"], value["summary"])
        self.assertEqual(row["progression_comparison"]["record_ref"], frozen._ref(value))
        self.assertEqual(row["status"], "progression_contrast_saved_not_selected")
        self.assertEqual(value["selectors"], row["technical_panel"]["selectors"])
        self.assertEqual(value["summary"]["logical_path_key_tuples"],
                         self.parent_rows[0]["delayed_counts"]["logical_path_key_tuples"])
        plan = read_json(self.output / "run-plan.json")
        self.assertIs(plan["source_labels_used_for_inference"], False)
        self.assertIs(plan["sample_is_accuracy_evaluation"], False)
        self.assertEqual(plan["panel_policy"], trial.PANEL_POLICY)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "report.json")})
        self.assertTrue(all(sha(path) == expected for path, expected in report["artifact_hashes"].items()))

    def test_known_zero_none_bool_and_nested_metrics_remain_distinct(self):
        report = self.execute_counted()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["progression_integer_subtotals"],
                         {"known_zero": 0, "computed_relations": 2})
        self.assertEqual(report["summary"]["progression_unknown_metric_contexts"], {"unknown_comparisons": 1})
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(row["progression_counts"]["known_zero"], 0)
        self.assertIsNone(row["progression_counts"]["unknown_comparisons"])
        self.assertIs(row["progression_counts"]["not_an_integer_metric"], False)
        self.assertIs(row["progression_counts"]["also_not_an_integer_metric"], True)

    def test_whole_request_budget_hold_preserves_panel_and_global_unassessed_denominator(self):
        report = self.execute(max_hypotheses=0)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        row = read_json(self.output / "context-index.json")[0]
        value = read_gzip(row["progression_comparison"]["artifact"])
        self.assertEqual(value["status"], "whole_comparison_source_or_work_hold")
        self.assertEqual(len(value["selectors"]), 5)
        self.assertEqual(value["selectors"], row["technical_panel"]["selectors"])
        self.assertEqual(value["hypotheses"], [])
        self.assertEqual(value["contrasts"], [])
        self.assertEqual(value["summary"]["planned_hypotheses"], 5)
        self.assertEqual(value["summary"]["computed_hypotheses"], 0)
        self.assertEqual(value["summary"]["tested_logical_path_key_tuples"], 0)
        self.assertEqual(value["summary"]["unassessed_logical_path_key_tuples"],
                         self.parent_rows[0]["delayed_counts"]["logical_path_key_tuples"])

    def test_held_record_saved_without_unknown_metric_becoming_zero(self):
        def held(*args, **kwargs):
            return frozen._seal({"version": "progression-held-fixture-0.1.0",
                "status": "whole_comparison_source_or_work_hold",
                "summary": {"known_planned_candidates": 4, "computed_candidates": None}}, "fmpeheldfixture_")
        with patch.object(engine, "compare_prepared", side_effect=held):
            report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["progression_saved_contexts"], 1)
        self.assertEqual(report["summary"]["progression_failed_contexts"], 0)
        self.assertEqual(report["summary"]["progression_integer_subtotals"], {"known_planned_candidates": 4})
        self.assertEqual(report["summary"]["progression_unknown_metric_contexts"], {"computed_candidates": 1})

    def test_authentic_two_slot_parent_preserves_held_unknown_and_known_zero_axes(self):
        self.adopt_two_slot_held_parent()
        inherited = self.parent_rows[0]["delayed_counts"]
        self.assertGreater(inherited["touching_pair_groups"], 0)
        self.assertGreater(inherited["planned_obligation_kernels"], 0)
        self.assertEqual(inherited["materialized_obligation_kernels"], 0)
        unknown = self.parent_report["summary"]["delayed_unknown_metric_contexts"]
        self.assertTrue(unknown)
        for name in unknown:
            self.assertIsNone(inherited[name])
        report = self.execute_counted()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assert_denominators(report)
        self.assertEqual(report["parent_summary"]["delayed_unknown_metric_contexts"], unknown)

    def test_all_caps_forwarded_and_registered(self):
        settings = {name: index for index, name in enumerate(trial.SETTINGS)}
        with patch.object(engine, "compare_prepared", side_effect=self.counted_comparison) as compare:
            report = self.execute(**settings)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertEqual(compare.call_args.kwargs, settings)
        self.assertEqual(read_json(self.output / "run-plan.json")["settings"], settings)

    def test_comparison_uses_owned_issued_session_and_declared_panel(self):
        observed = []
        def compare(session, selectors, bundle_id, **settings):
            engine._issued(session)
            observed.append((selectors, bundle_id))
            return self.counted_comparison()
        with patch.object(engine, "prepare_comparison", side_effect=AssertionError("raw replay")), \
                patch.object(delayed, "prepare_obligations", side_effect=AssertionError("raw replay")), \
                patch.object(engine, "compare_prepared", side_effect=compare):
            report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        row = read_json(self.output / "context-index.json")[0]
        self.assertEqual(observed, [(row["technical_panel"]["selectors"], row["technical_panel"]["bundle_id"])])

    def test_calculation_and_cached_case_failures_keep_all_denominators(self):
        with patch.object(engine, "compare_prepared", side_effect=ValueError("deliberate progression failure")):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["progression_saved_contexts"], 0)
        self.assertEqual(report["summary"]["progression_failed_contexts"], 1)
        self.assertEqual(report["summary"]["progression_integer_subtotals"], {})
        self.assertEqual(report["summary"]["progression_unknown_metric_contexts"], {})
        row = read_json(self.output / "context-index.json")[0]
        self.assertIsNone(row["progression_comparison"])
        self.assertIsNone(row["progression_counts"])

    def test_cached_case_failure_keeps_all_denominators(self):
        with patch.object(trial, "load_case", side_effect=ValueError("deliberate cached load failure")):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(report["selected_denominators_complete"])
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["progression_failed_contexts"], 1)

    def test_failed_engine_cannot_hide_cached_parent_mutation(self):
        original = trial.load_case
        cache = []
        def remember(data, row):
            case = original(data, row)
            cache.append(case)
            return case
        def mutate(*args, **kwargs):
            cache[0][1]["note_events"][0]["notation"]["runner_test_mutation"] = True
            raise ValueError("deliberate after mutation")
        with patch.object(trial, "load_case", side_effect=remember), \
                patch.object(engine, "compare_prepared", side_effect=mutate):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertTrue(any("parent_or_IR_mutated" in f["error"] for f in report["failures"]))
        self.assert_denominators(report)

    def test_creation_hash_not_refreshed_after_artifact_mutation(self):
        original = storage._save
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.write_bytes(path.read_bytes() + b" ")
            return path
        with patch.object(storage, "_save", side_effect=mutate):
            report = self.execute_counted()
        path = self.output / "context-index.json"
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(path), report["changed_artifacts"])
        self.assertNotEqual(report["artifact_hashes"][str(path)], sha(path))

    def test_artifact_inventory_addition_and_deletion_reported(self):
        original = storage._save
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                path.unlink()
                write_json(output / "unregistered.json", {})
            return path
        with patch.object(storage, "_save", side_effect=mutate):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])

    def test_parent_and_current_code_inventory_additions_not_absorbed(self):
        original = storage._save
        added = self.root / "src/musicanote_harness/extra.py"
        code_paths = trial.parent._code_paths
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(self.delayed_parent / "unregistered.json", {})
                write_json(added, {})
            return path
        with patch.object(storage, "_save", side_effect=mutate), \
                patch.object(trial.parent, "_code_paths", side_effect=lambda:
                    [*code_paths(), *([added] if added.exists() else [])]):
            report = self.execute_counted()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("delayed_parent_inventory_changed", report["changed_inputs_or_code"])
        self.assertIn("current_code_inventory_changed", report["changed_inputs_or_code"])
        self.assertNotIn(str(added), read_json(self.output / "run-plan.json")["code"])

    def test_original_input_change_and_producer_deletion_during_run(self):
        original = storage._save
        changed = self.prior["directory"] / "report.json"
        def mutate(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
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
