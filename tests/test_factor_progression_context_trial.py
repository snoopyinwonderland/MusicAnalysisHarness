"""Small saved-parent runner fixtures, not authentic corpus cold replay."""
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_progression_context_trial as trial
from musicanote_harness import factor_progression_evidence_trial as previous
from musicanote_harness import factor_progression_evidence as progression
from musicanote_harness import factor_progression_context as engine
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_trial as storage
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


class EarlyContextTrialGuardTests(unittest.TestCase):
    def test_destinations_and_exact_caps_are_checked_before_parent_reads(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/existing"
            old.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), patch.object(trial, "load_inputs", side_effect=AssertionError("parent read")):
                self.assertEqual(trial.SETTINGS, {"max_hypotheses": 64,
                    "max_boundary_observations": 2048, "max_transition_pairs": 4096, "query_work_budget": 200000})
                for path in (root, old, root / "output/nested/new", root / "elsewhere/new"):
                    with self.subTest(path=path), self.assertRaises(ValueError):
                        trial.run("missing", path)
                for name in trial.SETTINGS:
                    for value in (True, False, -1, 1.5, None, "1"):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("missing", root / "output/new", **{name: value})
                with self.assertRaises(ValueError):
                    trial.run("missing", root / "output/new", max_comparisons=1)
            self.assertFalse((root / "output/new").exists())


class ContextTrialFixture:
    """Only storage/runner authority is mocked; no old test methods inherited."""
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.parent_dir = self.root / "output/progression"
        self.delayed_dir = self.root / "output/delayed"
        self.parent_dir.mkdir(parents=True)
        self.delayed_dir.mkdir()
        self.output = self.root / "output/context-child"
        self.producer = self.root / "producer.json"
        write_json(self.producer, {"fixture_producer_not_corpus_calculation": True})
        input_path = self.delayed_dir / "input.json"
        write_json(input_path, {"source_ref": "fixture", "data": [1, 2, 3]})
        write_json(self.delayed_dir / "report.json", {"summary": {"saved_parent_fixture": True}})
        keys = [["fixture:one", 1, "ctx-one"], ["fixture:two", 2, "ctx-two"]]
        unexecuted = ["fixture:unexecuted", 3, "ctx-three"]
        units = [{"context_key": keys[0], "lane": ["part", "voice"]},
                 {"context_key": keys[1], "lane": ["part", "voice-1"]},
                 {"context_key": keys[1], "lane": ["part", "voice-2"]},
                 {"context_key": unexecuted, "lane": ["part", "voice"]}]
        settings = deepcopy(previous.SETTINGS)
        self.panels, self.parent_values, self.old_rows, cases, sessions = {}, {}, [], {}, {}
        counts = {"groups": 2, "logical_paths": 10, "logical_path_key_tuples": 50,
                  "logical_function_shapes": 1000, "unknown_product_groups": 0,
                  "indexed_variants": 4, "shared_profile_descriptors": 3}
        self.rows = []
        artifacts = {}
        for position, key in enumerate(keys, 1):
            lane_count = position
            row = {"context_key": deepcopy(key), **{name: {"fixture": name, "position": position}
                for name in (*previous.INHERITED_ROW_FIELDS, "delayed_obligations", "delayed_counts")}}
            row.update(old_lane_refs=[["part", "voice-" + str(i)] for i in range(lane_count)],
                       old_groups=[{"group_id": "old-group"}], index_counts=deepcopy(counts),
                       old_hypothesis_counts={"original_path_product": None})
            self.old_rows.append(row)
            parent19 = frozen._seal({"fixture_context_key": deepcopy(key),
                "analysis_span": {"start": {"numerator": 0, "denominator": 1}, "end": {"numerator": 4, "denominator": 1}},
                "logical_universe": {"fixture_universe": position}, "summary": {
                    "logical_paths": 10, "logical_path_key_tuples": 50, "logical_function_rows": 1000,
                    "unknown_product_groups": 0}}, "fmdo_")
            cases[tuple(key)] = ({"IR": position, "notes": ["source-note"]}, parent19)
            sessions[tuple(key)] = ("comparison-authority", tuple(key))
            panel = {"selectors": [{"group_id": "full", "variant_ids": ["a"], "key_id": "key", "transition": None},
                                    {"group_id": "full", "variant_ids": ["b"], "key_id": "key", "transition": None}],
                     "bundle_id": "registered-bundle", "selection_policy": previous.PANEL_POLICY,
                     "seed_kernel_ref": None, "seed_supported_in_saved_phase19": False,
                     "alternate_target_variant_id": None, "comparison_scope": "same_scope_complete_original_partitions",
                     "sampling_is_accuracy_evidence": False, "winning_hypothesis_selected": False}
            self.panels[tuple(key)] = panel
            value = frozen._seal({"version": progression.VERSION, "resource_limits": settings,
                "analysis_span": {"start": {"numerator": 0, "denominator": 1}, "end": {"numerator": 4, "denominator": 1}},
                "logical_universe": {"fixture_universe": position}, "selectors": deepcopy(panel["selectors"]),
                "bundle_id": panel["bundle_id"], "summary": {"logical_paths": 10, "logical_path_key_tuples": 50,
                    "logical_function_rows": 1000, "unknown_product_groups": 0, "planned_hypotheses": 2,
                    "computed_hypotheses": 2, "known_zero": 0, "unknown_metric": None,
                    "not_an_integer_metric": False},
                "status": "computed_same_scope_evidence_not_selected", "fixture_position": position}, progression.PREFIX)
            self.parent_values[tuple(key)] = value
            path = storage._save(self.parent_dir, "progression-comparisons/" + value["record_id"] + ".json.gz", value, artifacts, compressed=True)
            self.rows.append({"context_key": deepcopy(key), "old_row_sha256": trial.digest(row),
                **{name: deepcopy(row[name]) for name in (*previous.INHERITED_ROW_FIELDS, "delayed_obligations", "delayed_counts")},
                "progression_comparison": {"artifact": str(path), "sha256": sha(path), "record_ref": frozen._ref(value), "status": value["status"]},
                "progression_counts": deepcopy(value["summary"]), "technical_panel": deepcopy(panel),
                "status": "progression_contrast_saved_not_selected", "error": None, "elapsed_seconds": 0.0})
        old_plan = {"code": {str(self.producer): sha(self.producer)}, "declared_contexts": [*keys, unexecuted],
            "declared_units": units, "selected_contexts": keys, "selection": {"scope": "fixture-declared-scope"}}
        old_hashes = {str(path): sha(path) for path in (input_path, self.delayed_dir / "report.json")}
        self.old = {"directory": self.delayed_dir, "hashes": old_hashes,
            "inventory": {str(p.resolve()) for p in self.delayed_dir.rglob("*") if p.is_file()},
            "plan": old_plan, "report": read_json(self.delayed_dir / "report.json"),
            "rows": self.old_rows, "cases": cases, "comparison_sessions": sessions}
        plan = {"version": previous.VERSION, "delayed": str(self.delayed_dir),
            "parent_report_sha256": sha(self.delayed_dir / "report.json"), "inputs": deepcopy(old_hashes),
            "code": deepcopy(old_plan["code"]), "settings": settings,
            **{k: deepcopy(old_plan[k]) for k in ("declared_contexts", "declared_units", "selected_contexts", "selection")},
            "cohort_complete": False, "old_selector_or_analysis_reexecuted": False, "all_logical_paths_evaluated": False,
            "source_labels_used_for_inference": False, "old_paths_or_bundles_extended": False, "production_modified": False,
            "conditional_progression_comparison_stage_enabled": True, "coverage": previous.COVERAGE,
            "panel_policy": previous.PANEL_POLICY, "sample_is_accuracy_evaluation": False}
        storage._save(self.parent_dir, "run-plan.json", plan, artifacts)
        storage._save(self.parent_dir, "context-index.json", self.rows, artifacts)
        self.parent_report = {"version": previous.VERSION, "scope_calculation_complete": True,
            "computation_integrity_passed": True, "selected_denominators_complete": True,
            "inputs_and_code_unchanged": True, "artifacts_unchanged": True,
            "changed_inputs_or_code": [], "changed_artifacts": [], "failures": [], "artifact_hashes": artifacts,
            "parent_summary": deepcopy(self.old["report"]["summary"]), "summary": self.summary(),
            "cohort_complete": False, "all_logical_paths_evaluated": False, "selected": None,
            **{k: False for k in trial.POLICY_FALSE}, "conditional_progression_comparison_stage_enabled": True,
            "conditional_NCT_evaluated": False, "boundary_NCT_evaluated": False, "delayed_resolution_confirmed": False,
            "sample_is_accuracy_evaluation": False, "elapsed_seconds": 0.0, "limits": ["fixture storage only"]}
        write_json(self.parent_dir / "report.json", self.parent_report)
        self.loader_calls, self.prepare_calls, self.build_calls = [], [], []
        for target, name, value in ((trial, "ROOT", self.root), (trial.parent, "_code_paths", lambda: [self.producer]),
            (previous, "load_inputs", self.mock_old), (previous, "_ancestors", lambda old: [("delayed", old)]),
            (previous, "technical_panel", self.mock_panel), (engine, "prepare_context_prepared", self.mock_prepare),
            (engine, "build_context_prepared", self.mock_build)):
            patched = patch.object(target, name, side_effect=value) if name in ("load_inputs", "technical_panel", "prepare_context_prepared", "build_context_prepared") else patch.object(target, name, value)
            patched.start()
            self.addCleanup(patched.stop)

    def summary(self):
        totals, subtotals, unknown = Counter(), Counter(), Counter()
        for row in self.rows:
            trial.cohort._add_denominators(totals, row)
            for name, count in row["progression_counts"].items():
                if type(count) is int:
                    subtotals[name] += count
                elif count is None:
                    unknown[name] += 1
        return {**dict(totals), "progression_integer_subtotals": dict(subtotals),
            "progression_unknown_metric_contexts": dict(unknown), "progression_saved_contexts": len(self.rows),
            "progression_failed_contexts": 0, "declared_contexts": 3, "declared_original_raw_lanes": 4,
            "unexecuted_original_contexts": 1, "unexecuted_original_raw_lanes": 1,
            "context_status_counts": dict(Counter(r["status"] for r in self.rows))}

    def mock_old(self, directory):
        self.loader_calls.append(str(directory))
        self.assertEqual(Path(directory), self.delayed_dir)
        return self.old

    def mock_panel(self, record):
        return deepcopy(self.panels[tuple(record["fixture_context_key"])])

    def mock_prepare(self, session, value):
        key = session[1]
        self.prepare_calls.append(key)
        if not trial.indexed._same(value, self.parent_values[key]):
            raise ValueError("fixture_exact_phase20_replay_rejects_resealed_wrong_body")
        return ("context-authority", key)

    def mock_build(self, session, **settings):
        self.build_calls.append((session, deepcopy(settings)))
        return frozen._seal({"version": engine.VERSION, "summary": {"planned_hypotheses": 2,
            "computed_hypotheses": 2, "known_zero": 0, "unknown_metric": None, "not_integer": False},
            "status": "fixture_conditional_prerequisites_not_music", "resource_limits": settings,
            "fixture_context_key": list(session[1])}, engine.PREFIX)

    def execute(self, **settings):
        with redirect_stdout(io.StringIO()):
            return trial.run(self.parent_dir, self.output, **settings)

    def refresh(self, *, summary=False):
        if summary:
            self.rows = read_json(self.parent_dir / "context-index.json")
        report = read_json(self.parent_dir / "report.json")
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        if summary:
            report["summary"] = self.summary()
        write_json(self.parent_dir / "report.json", report)

    def mutate_report(self, change):
        path = self.parent_dir / "report.json"
        value = read_json(path)
        change(value)
        write_json(path, value)

    def mutate_plan(self, change):
        path = self.parent_dir / "run-plan.json"
        value = read_json(path)
        change(value)
        write_json(path, value)
        self.refresh()

    def mutate_rows(self, change, *, summary=False):
        path = self.parent_dir / "context-index.json"
        value = read_json(path)
        change(value)
        write_json(path, value)
        self.refresh(summary=summary)

    def adopt_runner_probe_hold(self):
        key = tuple(self.rows[0]["context_key"])
        self.panels[key]["selectors"] = self.panels[key]["selectors"][:1]
        prior = self.old["cases"][key][-1]
        value = previous._no_panel(prior, self.panels[key], previous.SETTINGS)
        path = Path(self.rows[0]["progression_comparison"]["artifact"])
        replacement = path.with_name(value["record_id"] + ".json.gz")
        write_gzip(replacement, value)
        def change(rows):
            rows[0]["progression_comparison"] = {"artifact": str(replacement), "sha256": sha(replacement),
                "record_ref": frozen._ref(value), "status": value["status"]}
            rows[0]["progression_counts"] = deepcopy(value["summary"])
            rows[0]["technical_panel"] = deepcopy(self.panels[key])
        self.mutate_rows(change)
        self.rows = read_json(self.parent_dir / "context-index.json")
        report = read_json(self.parent_dir / "report.json")
        del report["artifact_hashes"][str(path)]
        report["artifact_hashes"][str(replacement)] = sha(replacement)
        report["artifact_hashes"][str(self.parent_dir / "context-index.json")] = sha(self.parent_dir / "context-index.json")
        report["summary"] = self.summary()
        write_json(self.parent_dir / "report.json", report)
        path.unlink()
        self.parent_report = report
        self.parent_values[key] = value

    def reject(self, expression=""):
        with self.assertRaisesRegex(ValueError, expression):
            self.execute()
        self.assertFalse(self.output.exists())

    def assert_denominators(self, report):
        for name in (*trial.DENOMINATORS, "declared_contexts", "declared_original_raw_lanes",
                     "unexecuted_original_contexts", "unexecuted_original_raw_lanes"):
            self.assertEqual(report["summary"][name], self.parent_report["summary"][name], name)
        self.assertEqual(report["parent_summary"], self.parent_report["summary"])
        self.assertIsNone(report["selected"])
        for name in (*trial.POLICY_FALSE, "cohort_complete", "all_logical_paths_evaluated", "sample_is_accuracy_evaluation"):
            self.assertIs(report[name], False, name)
        self.assertIs(report["conditional_progression_context_stage_enabled"], True)
        rows = read_json(self.output / "context-index.json")
        self.assertEqual([r["context_key"] for r in rows], [r["context_key"] for r in self.rows])
        for row, original in zip(rows, self.rows):
            self.assertEqual(row["old_row_sha256"], trial.digest(original))
            for name in trial.INHERITED_ROW_FIELDS:
                self.assertEqual(row[name], original[name], name)


class ContextParentGuardTests(ContextTrialFixture, unittest.TestCase):
    def test_report_closed_shape_and_typed_policy_reject_before_output(self):
        self.mutate_report(lambda r: r.update(cadence_confirmed=True))
        self.reject("completed_unselected")

    def test_wrong_report_version_rejected(self):
        self.mutate_report(lambda r: r.update(version="old"))
        self.reject("completed_unselected")

    def test_boolean_integrity_must_not_be_integer_one(self):
        self.mutate_report(lambda r: r.update(scope_calculation_complete=1))
        self.reject("completed_unselected")

    def test_extra_report_field_rejected(self):
        self.mutate_report(lambda r: r.update(accuracy=1))
        self.reject("closed_index")

    def test_stale_artifact_hash_rejected(self):
        write_json(self.parent_dir / "context-index.json", [])
        self.reject("input_hash_mismatch")

    def test_extra_parent_file_rejected(self):
        write_json(self.parent_dir / "extra.json", {})
        self.reject("inventory")

    def test_artifact_outside_parent_directory_rejected(self):
        self.mutate_report(lambda r: r["artifact_hashes"].update({str(self.producer): sha(self.producer)}))
        self.reject("outside_registered")

    def test_empty_historical_code_inventory_rejected(self):
        self.mutate_plan(lambda p: p.update(code={}))
        self.reject("creation_producer")

    def test_foreign_historical_code_inventory_rejected(self):
        self.mutate_plan(lambda p: p["code"].update({str(self.delayed_dir / "input.json"): sha(self.delayed_dir / "input.json")}))
        self.reject("creation_producer")

    def test_historical_stage_adds_exactly_its_two_producers_not_new_child(self):
        child = self.root / "new-child-producer.json"
        write_json(child, {"new_child": True})
        stage = [Path(previous.__file__).resolve(), Path(progression.__file__).resolve()]
        self.mutate_plan(lambda p: p["code"].update({str(path): sha(path) for path in stage}))
        with patch.object(trial.parent, "_code_paths", return_value=[self.producer, *stage, child]):
            with redirect_stdout(io.StringIO()):
                data = trial.load_inputs(self.parent_dir)
        self.assertEqual(len(data["context_sessions"]), 2)
        self.assertNotIn(str(child), data["plan"]["code"])
        self.assertFalse(self.output.exists())

    def test_empty_protected_input_closure_rejected(self):
        self.mutate_plan(lambda p: p.update(inputs={}))
        self.reject("protected_input_closure")

    def test_resealed_foreign_parent_summary_rejected(self):
        self.mutate_report(lambda r: r.update(parent_summary={"selected": True}))
        self.reject("declared_lineage")

    def test_plan_inference_policy_rejected(self):
        self.mutate_plan(lambda p: p.update(source_labels_used_for_inference=True))
        self.reject("plan_policy")

    def test_saved_cap_bool_rejected_before_old_loader(self):
        self.mutate_plan(lambda p: p["settings"].update(query_work_budget=True))
        self.reject("nonnegative_integer")
        self.assertEqual(self.loader_calls, [])

    def test_context_deletion_does_not_change_declared_denominator(self):
        self.mutate_rows(lambda rows: rows.pop())
        self.reject("context_denominator")

    def test_origin_field_mutation_rejected(self):
        self.mutate_rows(lambda rows: rows[0]["old_lane_refs"].append(["foreign", "lane"]))
        self.reject("original_context")

    def test_typed_count_change_rejected(self):
        self.mutate_report(lambda r: r["summary"].update(unexecuted_original_contexts=False))
        self.reject("summary_or_unexecuted")

    def test_parent_counts_resealed_to_match_wrong_saved_body_still_replayed(self):
        row = self.rows[0]
        path = Path(row["progression_comparison"]["artifact"])
        value = read_gzip(path)
        value["summary"]["computed_hypotheses"] = 0
        value = frozen._seal({k: v for k, v in value.items() if k not in ("record_id", "record_sha256")}, progression.PREFIX)
        replacement = path.with_name(value["record_id"] + ".json.gz")
        write_gzip(replacement, value)
        def change(rows):
            rows[0]["progression_comparison"].update(artifact=str(replacement), sha256=sha(replacement), record_ref=frozen._ref(value))
            rows[0]["progression_counts"] = deepcopy(value["summary"])
        self.mutate_rows(change)
        report = read_json(self.parent_dir / "report.json")
        del report["artifact_hashes"][str(path)]
        report["artifact_hashes"][str(replacement)] = sha(replacement)
        report["artifact_hashes"][str(self.parent_dir / "context-index.json")] = sha(self.parent_dir / "context-index.json")
        write_json(self.parent_dir / "report.json", report)
        path.unlink()
        self.reject("exact_phase20_replay")

    def test_foreign_panel_key_rejected_before_child_prepare(self):
        self.mutate_rows(lambda rows: rows[0]["technical_panel"]["selectors"][0].update(key_id="foreign"))
        self.reject("technical_panel")
        self.assertEqual(self.prepare_calls, [])

    def test_registered_ref_but_foreign_artifact_location_rejected(self):
        source = Path(self.rows[0]["progression_comparison"]["artifact"])
        foreign = self.parent_dir / source.name
        foreign.write_bytes(source.read_bytes())
        self.mutate_rows(lambda rows: rows[0]["progression_comparison"].update(artifact=str(foreign)))
        report = read_json(self.parent_dir / "report.json")
        del report["artifact_hashes"][str(source)]
        report["artifact_hashes"][str(foreign)] = sha(foreign)
        write_json(self.parent_dir / "report.json", report)
        source.unlink()
        self.reject("foreign_or_unregistered")

    def test_unknown_metric_and_known_zero_are_not_silently_substituted(self):
        self.mutate_report(lambda r: r["summary"]["progression_unknown_metric_contexts"].update(unknown_metric=0))
        self.reject("summary_or_unexecuted")

    def test_parent_IR_mutation_during_child_preparation_is_rejected_before_output(self):
        original = self.mock_prepare
        def mutate(session, value):
            result = original(session, value)
            self.old["cases"][session[1]][0]["IR"] = "changed"
            return result
        with patch.object(engine, "prepare_context_prepared", side_effect=mutate):
            self.reject("mutated_during_preparation")


class ContextRunTests(ContextTrialFixture, unittest.TestCase):
    def test_complete_probe_reuses_one_parent_load_and_one_prepare_each(self):
        before = deepcopy(self.old)
        report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertEqual(len(self.loader_calls), 1)
        self.assertEqual(self.prepare_calls, [tuple(r["context_key"]) for r in self.rows])
        self.assertEqual(len(self.build_calls), 2)
        self.assertEqual(self.old, before)
        self.assert_denominators(report)
        self.assertEqual(report["summary"]["context_integer_subtotals"], {"planned_hypotheses": 4, "computed_hypotheses": 4, "known_zero": 0})
        self.assertEqual(report["summary"]["context_unknown_metric_contexts"], {"unknown_metric": 2})
        self.assertEqual(len(list(self.output.rglob("*.gz"))), 2)
        self.assertEqual(len([p for p in self.output.rglob("*") if p.is_file()]), 5)
        plan = read_json(self.output / "run-plan.json")
        self.assertEqual(plan["parent_panel_policy"], previous.PANEL_POLICY)
        self.assertEqual(plan["settings"], trial.SETTINGS)

    def test_zero_caps_are_explicit_and_passed_without_selecting_prefix(self):
        settings = {name: 0 for name in trial.SETTINGS}
        report = self.execute(**settings)
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertTrue(all(value == settings for _, value in self.build_calls))
        self.assert_denominators(report)

    def test_parent_runner_probe_hold_does_not_fabricate_core_authority(self):
        self.adopt_runner_probe_hold()
        report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertEqual(self.prepare_calls, [tuple(self.rows[1]["context_key"])])
        self.assertEqual(len(self.build_calls), 1)
        rows = read_json(self.output / "context-index.json")
        value = read_gzip(rows[0]["progression_context"]["artifact"])
        self.assertTrue(value["record_id"].startswith("fmpctxprobehold_"))
        self.assertEqual(value["version"], trial.VERSION)
        self.assertEqual(value["contexts"], [])
        self.assertIsNone(value["summary"]["planned_transition_pairs"])
        self.assertIsNone(value["summary"]["planned_boundary_observations"])
        self.assertEqual(value["summary"]["computed_hypotheses"], 0)
        self.assertEqual(value["progression_ref"], frozen._ref(self.parent_values[tuple(self.rows[0]["context_key"])]))
        self.assert_denominators(report)

    def test_core_hold_is_saved_and_unknown_metrics_remain_unknown(self):
        def hold(session, **settings):
            return frozen._seal({"version": engine.VERSION, "summary": {"planned_hypotheses": 2,
                "computed_hypotheses": 0, "planned_transition_pairs": None, "query_budget": None},
                "status": "withheld_whole_parent_or_resource_hold", "resource_limits": settings,
                "fixture_context_key": list(session[1])}, engine.PREFIX)
        with patch.object(engine, "build_context_prepared", side_effect=hold):
            report = self.execute()
        self.assertTrue(report["scope_calculation_complete"], report)
        self.assertEqual(report["summary"]["context_saved_contexts"], 2)
        self.assertEqual(report["summary"]["context_integer_subtotals"]["computed_hypotheses"], 0)
        self.assertEqual(report["summary"]["context_unknown_metric_contexts"], {"planned_transition_pairs": 2, "query_budget": 2})
        self.assert_denominators(report)

    def test_invalid_native_output_seal_is_calculation_failure_not_saved_evidence(self):
        original = self.mock_build
        def corrupt(session, **settings):
            value = original(session, **settings)
            value["summary"]["computed_hypotheses"] += 1
            return value
        with patch.object(engine, "build_context_prepared", side_effect=corrupt):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertEqual(report["summary"]["context_saved_contexts"], 0)
        self.assertEqual(report["summary"]["context_failed_contexts"], 2)
        self.assert_denominators(report)

    def test_resealed_wrong_native_resource_limits_are_not_saved(self):
        original = self.mock_build
        def corrupt(session, **settings):
            value = original(session, **settings)
            body = {k: v for k, v in value.items() if k not in ("record_id", "record_sha256")}
            body["resource_limits"]["max_transition_pairs"] += 1
            return frozen._seal(body, engine.PREFIX)
        with patch.object(engine, "build_context_prepared", side_effect=corrupt):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertEqual(report["summary"]["context_saved_contexts"], 0)
        self.assertEqual(report["summary"]["context_failed_contexts"], 2)
        self.assertTrue(all("native_output_contract" in f["error"] for f in report["failures"]))
        self.assert_denominators(report)

    def test_one_calculation_failure_keeps_both_contexts_and_all_denominators(self):
        def fail_first(session, **settings):
            if session[1] == tuple(self.rows[0]["context_key"]):
                raise ValueError("fixture_failure")
            return self.mock_build(session, **settings)
        with patch.object(engine, "build_context_prepared", side_effect=fail_first):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIs(report["selected_denominators_complete"], True)
        self.assertEqual(report["summary"]["context_failed_contexts"], 1)
        self.assertEqual(report["summary"]["context_saved_contexts"], 1)
        self.assertEqual(len(report["failures"]), 1)
        self.assert_denominators(report)

    def test_mutation_of_loaded_IR_is_failure_not_music_evidence(self):
        def mutate(session, **settings):
            self.old["cases"][session[1]][0]["IR"] = "changed"
            return self.mock_build(session, **settings)
        with patch.object(engine, "build_context_prepared", side_effect=mutate):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertEqual(report["summary"]["context_failed_contexts"], 2)
        self.assertEqual(report["summary"]["context_saved_contexts"], 0)
        self.assertTrue(all("parent_or_IR_mutated" in f["error"] for f in report["failures"]))
        self.assert_denominators(report)

    def test_saved_parent_change_is_detected_after_calculation(self):
        saved = self.mock_build
        def change(session, **settings):
            write_json(self.delayed_dir / "input.json", {"changed": True})
            return saved(session, **settings)
        with patch.object(engine, "build_context_prepared", side_effect=change):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.delayed_dir / "input.json"), report["changed_inputs_or_code"])

    def test_new_unregistered_parent_file_is_detected_after_calculation(self):
        saved = self.mock_build
        def change(session, **settings):
            write_json(self.parent_dir / "unregistered.json", {})
            return saved(session, **settings)
        with patch.object(engine, "build_context_prepared", side_effect=change):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("progression_parent_inventory_changed", report["changed_inputs_or_code"])

    def test_current_code_content_change_is_detected_after_calculation(self):
        saved = self.mock_build
        def change(session, **settings):
            write_json(self.producer, {"producer_changed": True})
            return saved(session, **settings)
        with patch.object(engine, "build_context_prepared", side_effect=change):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.producer), report["changed_inputs_or_code"])

    def test_current_code_inventory_growth_is_detected_after_calculation(self):
        original = storage._save
        child = self.root / "new-producer.json"
        write_json(child, {"producer": True})
        current = [self.producer]
        def save(directory, relative, value, artifacts, **kwargs):
            path = original(directory, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                current.append(child)
            return path
        with patch.object(storage, "_save", side_effect=save), patch.object(trial.parent, "_code_paths", side_effect=lambda: list(current)):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("current_code_inventory_changed", report["changed_inputs_or_code"])

    def test_changed_generated_artifact_rejected_without_dropping_cohort(self):
        original = storage._save
        def save(directory, relative, value, artifacts, **kwargs):
            path = original(directory, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(path, [])
            return path
        with patch.object(storage, "_save", side_effect=save):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn(str(self.output / "context-index.json"), report["changed_artifacts"])
        for name in trial.DENOMINATORS:
            self.assertEqual(report["summary"][name], self.parent_report["summary"][name])

    def test_unknown_output_file_detected(self):
        original = storage._save
        def save(directory, relative, value, artifacts, **kwargs):
            path = original(directory, relative, value, artifacts, **kwargs)
            if relative == "context-index.json":
                write_json(Path(directory) / "foreign.json", {})
            return path
        with patch.object(storage, "_save", side_effect=save):
            report = self.execute()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertIn("generated_artifact_inventory_changed", report["changed_artifacts"])


if __name__ == "__main__":
    unittest.main()
