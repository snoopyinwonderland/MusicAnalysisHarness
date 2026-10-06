"""Storage-only native-role runner tests, NOT corpus or engine accuracy tests.

Full IR fixtures here are explicitly synthetic storage metadata. Native
preparation, completion issuance, comparison and role explanation are mocked;
real strict JSON, digest seals, artifact hashes and denominator checks run.
"""
from collections import Counter
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import gzip
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_native_role_trial as trial


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def seal(body, prefix):
    return trial.sealed._seal(body, prefix)


def fixture_lattice():
    keys = [seal({"status": "fixture_explicit_key", "value": value}, "newkey_")
            for value in ("unknown", "C-major")]
    entries = []
    for start in range(3):
        for end in range(start + 1, 4):
            origins = [seal({"status": "fixture_native_origin", "point_indices": [start, end], "n": n},
                            "fmilorigin_") for n in (1, 2)]
            entries.append({"point_indices": [start, end], "origins": list(reversed(origins))})
    return seal({"status": "ready_native_interval_lattice", "coordinate_times": [trial.q(i) for i in range(4)],
                 "catalog_inventory": entries, "keys": keys,
                 "universe": {"fixture_logical_universe_not_native_issued": 123}}, trial.native.PREFIX)


def fixture_role_record(comparison, scope, *, hold=False):
    clauses = [{"role": "passing", "status": "supported", "qualified": True, "geometry_id": "shared-geometry"},
               {"role": "neighbor", "status": "failed", "qualified": True, "geometry_id": "shared-geometry"}]
    paths = [] if hold else [{"clauses": deepcopy(clauses), "account": {
        "raw_time_conserved": True, "conditional_explanation_note_time_quarters": trial.q(1),
        "explained_intervals_by_sound": [{"sound_ref": "fixture_sound", "spans": []}]}}
        for _ in comparison["paths"]]
    counts = Counter(clause["status"] for path in paths for clause in path["clauses"])
    result = {"version": trial.roles.VERSION, "status": "whole_explanation_hold" if hold else
              "computed_native_role_explanations_not_selected", "paths": paths,
        "native_comparison_ref": trial.sealed._ref(comparison), "scope_ref": trial.sealed._ref(scope),
        "bundle_ref": deepcopy(comparison["bundle_ref"]), "lattice_ref": deepcopy(comparison["lattice_ref"]),
        "native_request": {key: deepcopy(comparison[key]) for key in (
            "selectors", "resource_limits", "status", "reasons", "summary", "query_plan")},
        "query_plan": {"clause_upper_bound": 100, "planned_query_work": 200},
        "summary": {"planned_paths": comparison["summary"]["planned_selectors"],
            "native_computed_paths": len(comparison["paths"]), "computed_paths": len(paths),
            "planned_clause_upper_bound": 100, "unique_geometry_count": int(bool(paths)),
            "role_clause_occurrences": dict(Counter(clause["role"] for path in paths for clause in path["clauses"])),
            "evaluated_clauses": sum(counts.values()), "qualified_clauses": sum(counts.values()),
            "satisfied_clauses": counts["supported"], "failed_clauses": counts["failed"],
            "unassessed_clauses": counts["unassessed"], "credit_sound_occurrences": len(paths),
            "withheld_paths": comparison["summary"]["planned_selectors"] - len(paths)},
        "reasons": ["whole_explanation_work_exceeds_budget_no_prefix"] if hold else [],
        "selected": None, "rank": None, "confidence": None, "flags": trial.roles._flags()}
    return seal(result, trial.roles.PREFIX)


class StorageFixture(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.native_parent = self.root / "output/phase22"
        self.supplier_parent = self.root / "output/phase23"
        self.output = self.root / "output/new-role-pilot"
        self.native_parent.mkdir(parents=True)
        self.supplier_parent.mkdir(parents=True)
        self.producer = self.root / "fixture-producer.json"
        write_json(self.producer, {"storage_only_mock_producer": True})
        self.ir = {"ir_document_id": "storage-only-ir", "score": {"score_id": "fixture_score",
            "source_file_id": "fixture_source"}, "source_files": [{"source_file_id": "fixture_source"}],
            "fixture_NOT_native_validated_full_IR": True}
        self.ir_path = self.root / "output/registered-ir/full-ir.json"
        write_json(self.ir_path, self.ir)
        self.scope = seal({"binding": trial.expanded._binding(self.ir), "status": "ready_expanded_scope",
            "analysis_span": trial.sealed._span(0, 3), "sound_facts": [],
            "graphs": [{"lane": ["p", "v"], "factors": [{"time": trial.q(1),
                "source_refs": ["a"], "target_refs": ["b"]}]}],
            "raw_lanes": [{"part_id": "p", "voice_id": "v"}], "context_sound_inventory_complete": True},
            trial.expanded.PREFIX)
        self.scope_path = self.root / "output/registered-scope/scope.json.gz"
        self.scope_path.parent.mkdir(parents=True)
        with gzip.open(self.scope_path, "wt", encoding="utf-8") as stream:
            json.dump(self.scope, stream)
        self.context_key = ["fixture:one", 0, "fixture_context"]
        deferred_key = ["fixture:deferred", 1, "fixture_deferred"]
        scope_info = {"artifact": str(self.scope_path), "sha256": trial._file_sha(self.scope_path),
                      "record_ref": trial.sealed._ref(self.scope), "status": self.scope["status"]}
        self.metadata = {"context_key": self.context_key, "expanded_scope": scope_info,
            "old_lane_refs": [{"lane": ["p", "v"], "old_status": "fixture",
                "old_graph_ref": {"record_id": "fixture_graph", "record_sha256": "0" * 64}}]}
        self.row = {key: None for key in trial.NATIVE_ROW_KEYS}
        self.row.update({"context_key": self.context_key, "registered_parent_metadata": deepcopy(self.metadata),
            "registered_parent_row_sha256": trial.digest(self.metadata),
            "status": "native_lattice_probe_saved_not_selected", "error": None,
            "full_IR": {"artifact": str(self.ir_path), "sha256": trial._file_sha(self.ir_path),
                "ir_document_id": self.ir["ir_document_id"], "ir_content_sha256": trial.digest(self.ir),
                "binding_match": True, "registered_full_IR_not_projection": True}})
        self.plan = {key: False for key in trial.NATIVE_PLAN_KEYS}
        self.plan.update({"version": trial.native_trial.VERSION, "inputs": {
            str(self.ir_path): trial._file_sha(self.ir_path), str(self.scope_path): trial._file_sha(self.scope_path)},
            "code": {str(self.producer): trial._file_sha(self.producer)},
            "declared_contexts": [self.context_key, deferred_key], "selected_contexts": [self.context_key],
            "declared_units": [{"context_key": key, "lane": ["p", "v"]}
                               for key in (self.context_key, deferred_key)]})
        self.report = {key: False for key in trial.NATIVE_REPORT_KEYS}
        self.report.update({"version": trial.native_trial.VERSION, "scope_calculation_complete": True,
            "computation_integrity_passed": True, "selected_denominators_complete": True,
            "inputs_and_code_unchanged": True, "artifacts_unchanged": True,
            "failures": [], "changed_inputs_or_code": [], "changed_artifacts": [], "selected": None})
        self.supplier_plan = {key: False for key in trial.SUPPLIER_PLAN_KEYS}
        self.supplier_plan.update({"version": trial.supply_trial.VERSION, "parent": str(self.native_parent),
                                   "protected_sha256": {}})
        self.supplier_report = {key: False for key in trial.SUPPLIER_REPORT_KEYS}
        self.supplier_report.update({"version": trial.supply_trial.VERSION,
            "status": "exact_supplier_equivalence_complete", "changed_protected_paths": []})
        self.refresh()

    def refresh(self):
        write_json(self.native_parent / "run-plan.json", self.plan)
        write_json(self.native_parent / "context-index.json", [self.row])
        self.report["artifact_hashes"] = {str(self.native_parent / name): trial._file_sha(self.native_parent / name)
                                           for name in ("run-plan.json", "context-index.json")}
        write_json(self.native_parent / "report.json", self.report)
        write_json(self.supplier_parent / "run-plan.json", self.supplier_plan)
        self.supplier_report["artifact_sha256"] = {str(self.supplier_parent / "run-plan.json"):
                                                  trial._file_sha(self.supplier_parent / "run-plan.json")}
        write_json(self.supplier_parent / "report.json", self.supplier_report)

    def load(self):
        return trial.load_inputs(self.native_parent, self.supplier_parent, context_position=0)

    def run_mock(self, *, role_hold=False, native_hold=False, malformed_summary=False):
        """No true native/role authority is issued by this storage-only helper."""
        lattice = fixture_lattice()
        issued = {}

        def compile_bundle(session, links, **limits):
            bundle = seal({"status": "complete_all_lane_witness", "required_links": deepcopy(links)},
                          trial.native.BUNDLE_PREFIX)
            issued[bundle["record_id"]] = bundle
            return bundle

        def compare(session, selectors, bundle_id, **limits):
            bundle = issued[bundle_id]
            key_refs = {key["record_id"]: trial.sealed._ref(key) for key in lattice["keys"]}
            origin_refs = {origin["record_id"]: trial.sealed._ref(origin)
                           for entry in lattice["catalog_inventory"] for origin in entry["origins"]}
            paths = [] if native_hold else [{"bundle_ref": trial.sealed._ref(bundle),
                "key_ref": deepcopy(key_refs[selector["key_id"]]),
                "origin_refs": [deepcopy(origin_refs[key]) for key in selector["origin_ids"]]}
                for selector in selectors]
            return seal({"status": "whole_comparison_hold" if native_hold else "computed_native_comparison_not_selected",
                "bundle_ref": trial.sealed._ref(bundle), "lattice_ref": trial.sealed._ref(lattice),
                "selectors": deepcopy(selectors), "paths": paths, "resource_limits": deepcopy(limits),
                "summary": {"planned_selectors": len(selectors)}, "query_plan": {"planned_query_work": 123},
                "reasons": ["mock_whole_native_budget_hold"] if native_hold else []}, trial.native.COMPARISON_PREFIX)

        def explain(handle, **limits):
            result = fixture_role_record(handle, self.scope, hold=role_hold or native_hold)
            if malformed_summary:
                body = trial.sealed._check(result, trial.roles.PREFIX)
                body["summary"]["evaluated_clauses"] = True
                result = seal(body, trial.roles.PREFIX)
            return result

        with ExitStack() as stack:
            stack.enter_context(patch.object(trial, "ROOT", self.root))
            stack.enter_context(patch.object(trial, "_code_paths", return_value=[self.producer]))
            prepare = stack.enter_context(patch.object(trial.native, "prepare_lattice", return_value=object()))
            stack.enter_context(patch.object(trial.native, "lattice_prepared", return_value=lattice))
            stack.enter_context(patch.object(trial.native, "compile_bundle_prepared", side_effect=compile_bundle))
            stack.enter_context(patch.object(trial.native, "compare_prepared", side_effect=compare))
            role_prepare = stack.enter_context(patch.object(trial.roles, "prepare_explanations", side_effect=lambda session, c: c))
            stack.enter_context(patch.object(trial.roles, "explain_prepared", side_effect=explain))
            stack.enter_context(redirect_stdout(io.StringIO()))
            report = trial.run(self.native_parent, self.supplier_parent, self.output, context_position=0)
        return report, prepare, role_prepare


class StorageContractTests(StorageFixture):
    def test_append_only_caps_checked_before_loader(self):
        self.output.mkdir()
        with patch.object(trial, "ROOT", self.root), patch.object(trial, "load_inputs") as loader:
            for output in (self.output, self.root, self.root / "output/nested/new", self.root / "other/new"):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    trial.run("missing", "missing", output)
            valid = self.root / "output/valid-new"
            for key in trial.SETTINGS:
                for value in (True, False, -1, 1.5, None, "1"):
                    with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                        trial.run("missing", "missing", valid, **{key: value})
            for limits in ({"unknown": 1}, {"max_hypotheses": 4}, {"max_slots": 4},
                           {"max_greedy_links": 21}, {"include_greedy_bundle": 1}, {"context_position": True}):
                with self.subTest(limits=limits), self.assertRaises(ValueError):
                    trial.run("missing", "missing", valid, **limits)
            loader.assert_not_called()
        self.assertFalse(valid.exists())

    def test_strict_duplicate_and_nonfinite_json_including_gzip(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            for compressed in (False, True):
                with self.subTest(text=text, compressed=compressed):
                    path = self.root / ("invalid.json.gz" if compressed else "invalid.json")
                    if compressed:
                        with gzip.open(path, "wt", encoding="utf-8") as stream:
                            stream.write(text)
                    else:
                        path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        trial._read(path)

    def test_canonical_absolute_hash_map_and_conflicts(self):
        expected = trial._file_sha(self.producer)
        hashes = {}
        trial._protect(hashes, str(self.producer), expected)
        trial._protect(hashes, str(self.producer), expected)
        for path, checksum in (("relative.json", expected), (1, expected),
                               (str(self.producer), "G" * 64), (str(self.producer), True),
                               (str(self.producer), "0" * 64)):
            with self.subTest(path=path, checksum=checksum), self.assertRaises(ValueError):
                trial._protect(hashes, path, checksum)
        self.assertEqual(hashes, {str(self.producer): expected})

    def test_exact_inventory_and_child_body_seals_collision(self):
        artifacts = {}
        self.output.mkdir()
        record = seal({"status": "fixture_probe", "value": "음악"}, trial.roles.PREFIX)
        first = trial._save_record(self.output, "roles", record, trial.roles.PREFIX, artifacts)
        self.assertEqual(trial._read(first["artifact"]), record)
        self.assertEqual(trial._file_sha(first["artifact"]), first["sha256"])
        with self.assertRaises(FileExistsError):
            trial._save_record(self.output, "roles", record, trial.roles.PREFIX, artifacts)
        modified = deepcopy(record); modified["value"] = "changed"
        with self.assertRaises(ValueError):
            trial._save_record(self.output, "roles", modified, trial.roles.PREFIX, artifacts)
        second = trial._save_record(self.output, "roles-copy", record, trial.roles.PREFIX, artifacts)
        self.assertEqual(first["sha256"], second["sha256"])
        write_json(self.native_parent / "unregistered.json", {})
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.load()

    def test_metadata_loader_only_one_registered_IR_scope_no_native_call(self):
        with patch.object(trial.native, "prepare_lattice", side_effect=AssertionError("cold native called")):
            data = self.load()
        self.assertEqual(data["ir"], self.ir)
        self.assertEqual(data["scope"], self.scope)
        self.assertEqual(data["row"]["context_key"], self.context_key)
        self.assertEqual(data["plan"]["declared_units"], self.plan["declared_units"])
        self.assertEqual(trial._guard(data["hashes"]), [])
        self.assertFalse(self.output.exists())

    def test_changed_hash_and_closed_parent_headers_reject(self):
        write_json(self.ir_path, {**self.ir, "changed": True})
        with self.assertRaisesRegex(ValueError, "changed"):
            self.load()
        write_json(self.ir_path, self.ir)
        self.report["extra_future_unversioned"] = None
        self.refresh()
        with self.assertRaisesRegex(ValueError, "closed"):
            self.load()

    def test_registered_cohort_raw_lane_and_exact_binding_reject(self):
        self.plan["declared_units"].append(deepcopy(self.plan["declared_units"][0]))
        self.refresh()
        with self.assertRaisesRegex(ValueError, "unique_declared_original_raw_lane"):
            self.load()
        self.plan["declared_units"].pop()
        self.row["full_IR"]["ir_content_sha256"] = "0" * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, "binding"):
            self.load()

    def test_panel_selection_is_label_blind_fixed_first_origin_and_key(self):
        lattice = fixture_lattice()
        panel = trial.technical_panel(lattice)
        self.assertEqual(panel["planned_selectors"], 3)
        self.assertEqual([len(s["origin_ids"]) for s in panel["selectors"]], [1, 2, 3])
        first_key = min(key["record_id"] for key in lattice["keys"])
        self.assertEqual({s["key_id"] for s in panel["selectors"]}, {first_key})
        inventory = {tuple(entry["point_indices"]): entry for entry in lattice["catalog_inventory"]}
        for row, selector in zip(panel["rows"], panel["selectors"]):
            expected = [min(o["record_id"] for o in inventory[pair]["origins"])
                        for pair in zip(row["point_indices"], row["point_indices"][1:])]
            self.assertEqual(selector["origin_ids"], expected)
            self.assertEqual(selector["transition_assumptions"], [{"family": "V7", "quality": "M"}]
                             * (len(expected) - 1))
        lattice["keys"].reverse(); lattice["catalog_inventory"].reverse()
        lattice["annotation_label_DO_NOT_USE"] = "winner"
        self.assertEqual(trial.technical_panel(lattice), panel)

    def test_role_summary_closed_int_map_and_real_occurrence_denominators(self):
        comparison = seal({"summary": {"planned_selectors": 1}, "paths": [{}], "selectors": [],
            "bundle_ref": {"record_id": "fixture_bundle", "record_sha256": "0" * 64},
            "lattice_ref": {"record_id": "fixture_lattice", "record_sha256": "0" * 64},
            "resource_limits": {}, "status": "fixture", "reasons": [], "query_plan": {}}, trial.native.COMPARISON_PREFIX)
        record = fixture_role_record(comparison, self.scope)
        trial._validate_role_summary(record, comparison)
        for key, value in (("evaluated_clauses", True), ("role_clause_occurrences", []),
                           ("role_clause_occurrences", {"passing": True}), ("unique_geometry_count", 2),
                           ("withheld_paths", 1), ("satisfied_clauses", 2)):
            mutated = deepcopy(record); mutated["summary"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                trial._validate_role_summary(mutated, comparison)
        mutated = deepcopy(record); mutated["summary"]["new_unversioned_field"] = 0
        with self.assertRaisesRegex(ValueError, "closed"):
            trial._validate_role_summary(mutated, comparison)

    def test_protected_input_current_code_SHA_collision_before_native(self):
        data = self.load()
        data["hashes"][str(self.producer)] = "0" * 64
        with patch.object(trial, "ROOT", self.root), patch.object(trial, "_code_paths", return_value=[self.producer]), \
                patch.object(trial, "load_inputs", return_value=data), patch.object(trial.native, "prepare_lattice") as prepare:
            with self.assertRaisesRegex(ValueError, "conflicting_registered_SHA256"):
                trial.run(self.native_parent, self.supplier_parent, self.output, context_position=0)
            prepare.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_mock_run_exact_append_only_hashes_denominators_one_preparation(self):
        before = {str(path): trial._file_sha(path) for directory in (self.native_parent, self.supplier_parent)
                  for path in directory.rglob("*") if path.is_file()}
        report, prepare, role_prepare = self.run_mock()
        self.assertTrue(report["computation_integrity_passed"])
        self.assertTrue(report["role_calculation_complete"])
        self.assertEqual(prepare.call_count, 1)
        self.assertNotIn("record", prepare.call_args.kwargs)
        self.assertEqual(role_prepare.call_count, 2)
        self.assertEqual(report["denominators"], {"declared_contexts": 2, "declared_original_raw_lanes": 2,
            "registered_phase22_contexts": 1, "selected_contexts": 1, "selected_original_raw_lanes": 1,
            "unexecuted_declared_contexts": 1, "unexecuted_declared_original_raw_lanes": 1})
        self.assertEqual(report["fresh_native_preparations"], 1)
        self.assertEqual(report["counts"]["computed_role_paths"], 6)
        self.assertEqual(report["counts"]["evaluated_clause_occurrences"], 12)
        self.assertEqual(report["counts"]["role_clause_occurrences"], {"passing": 6, "neighbor": 6})
        self.assertEqual(report["counts"]["conditional_explained_note_time_selector_occurrence_sum"], trial.q(6))
        self.assertEqual(len(report["artifact_hashes"]), 9)
        trial._inventory(self.output, report["artifact_hashes"], self.output / "report.json")
        self.assertEqual(trial._guard({**before, **report["artifact_hashes"]}), [])
        self.assertTrue(all(report[key] is False for key in trial.POLICY_FALSE))
        with self.assertRaises(ValueError):
            self.run_mock()

    def test_mock_role_budget_whole_hold_preserves_planned_paths_and_no_credits(self):
        report, prepare, _ = self.run_mock(role_hold=True)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["role_calculation_complete"])
        self.assertEqual(prepare.call_count, 1)
        counts = report["counts"]
        self.assertEqual(counts["computed_selector_occurrences"], 6)
        self.assertEqual(counts["whole_explanation_holds"], 2)
        self.assertEqual(counts["computed_role_paths"], 0)
        self.assertEqual(counts["role_summary_occurrence_subtotals"]["withheld_paths"], 6)
        self.assertEqual(counts["role_clause_occurrences"], {})

    def test_mock_native_budget_whole_hold_no_prefix_or_claimed_role_completion(self):
        report, _, _ = self.run_mock(native_hold=True)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["role_calculation_complete"])
        self.assertEqual(report["counts"]["whole_comparison_holds"], 2)
        self.assertEqual(report["counts"]["computed_selector_occurrences"], 0)
        self.assertEqual(report["counts"]["planned_structural_selector_occurrences"], 6)
        self.assertEqual(report["counts"]["role_summary_occurrence_subtotals"]["withheld_paths"], 6)

    def test_mock_malformed_child_summary_records_failure_never_success_counts(self):
        report, prepare, _ = self.run_mock(malformed_summary=True)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertFalse(report["role_calculation_complete"])
        self.assertIsNone(report["counts"])
        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(len(report["failures"]), 1)
        self.assertIsNone(trial._read(self.output / "context-index.json")[0]["counts"])
        self.assertTrue(report["inputs_and_code_unchanged"])
        self.assertTrue(report["artifacts_unchanged"])

    def test_registered_parent_artifact_hash_conflict_rejects_without_build(self):
        self.plan["inputs"][str(self.producer)] = "0" * 64
        self.refresh()
        with patch.object(trial.native, "prepare_lattice") as prepare:
            with self.assertRaisesRegex(ValueError, "conflicting_registered_SHA256"):
                self.load()
            prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
