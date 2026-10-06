"""Storage-only native-runner fixtures; NOT authentic IR/corpus replay tests.

Native engine preparation, bundle issuance and path calculations are mocked.
The real storage hashes, seals, panel selection and denominator checks run.
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

from musicanote_harness import factor_interval_lattice_trial as trial
from musicanote_harness import factor_interval_lattice as engine
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_progression_context as old_engine
from musicanote_harness import factor_progression_context_trial as previous


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def read_json(path):
    return json.loads(path.read_bytes())


def read_gzip(path):
    return json.loads(gzip.decompress(path.read_bytes()))


class EarlyGuardTests(unittest.TestCase):
    def test_output_and_caps_reject_before_registered_loader(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            existing = root / "output/existing"
            existing.mkdir(parents=True)
            with patch.object(trial, "ROOT", root), patch.object(trial, "load_inputs", side_effect=AssertionError("loader called")):
                for path in (root, existing, root / "output/nested/new", root / "other/new"):
                    with self.subTest(path=path), self.assertRaises(ValueError):
                        trial.run("missing", path)
                for name in trial.SETTINGS:
                    for value in (True, False, -1, 1.5, None, "1"):
                        with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                            trial.run("missing", root / "output/new", **{name: value})
                for extra in ({"unknown_cap": 1}, {"include_greedy_bundle": 1},
                              {"max_hypotheses": 65}, {"max_greedy_links": 21}):
                    with self.subTest(extra=extra), self.assertRaises(ValueError):
                        trial.run("missing", root / "output/new", **extra)
            self.assertFalse((root / "output/new").exists())

    def test_absolute_closed_hash_maps(self):
        for value in ([], {"relative.json": "0" * 64}, {str(Path.cwd() / "x"): "G" * 64},
                      {str(Path.cwd() / "x"): True}, {1: "0" * 64}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                trial._hash_map(value, "storage-fixture")


class StorageFixture:
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.parent_dir = self.root / "output/registered-phase21"
        self.predecessor_dir = self.root / "output/phase20-metadata"
        self.scope_dir = self.root / "output/registered-scopes"
        self.output = self.root / "output/native-lattice-child"
        self.parent_dir.mkdir(parents=True)
        self.producer = self.root / "fixture-producer.json"
        write_json(self.producer, {"storage_only_fixture": True})
        self.predecessor_plan = {"inputs": {}, "code": {str(self.producer): trial.parent.file_digest(self.producer)}}
        write_json(self.predecessor_dir / "run-plan.json", self.predecessor_plan)
        self.predecessor_report = {"summary": {"metadata_fixture_not_original_authority": True},
            "artifact_hashes": {str(self.predecessor_dir / "run-plan.json"): trial.parent.file_digest(self.predecessor_dir / "run-plan.json")}}
        write_json(self.predecessor_dir / "report.json", self.predecessor_report)
        self.inputs = {str(self.producer): trial.parent.file_digest(self.producer),
            str(self.predecessor_dir / "run-plan.json"): trial.parent.file_digest(self.predecessor_dir / "run-plan.json"),
            str(self.predecessor_dir / "report.json"): trial.parent.file_digest(self.predecessor_dir / "report.json")}
        self.rows, self.scopes, self.irs, self.ir_paths, self.values = [], [], [], [], []
        self.artifacts = {}
        keys = [["fixture:piece-" + str(i), i, "context-" + str(i)] for i in range(5)]
        deferred = ["fixture:deferred", 9, "context-9"]
        units = [{"context_key": k, "lane": ["part", "voice"]} for k in (*keys, deferred)]
        for i, key in enumerate(keys):
            ir = {"ir_document_id": "full-ir-" + str(i), "score": {"score_id": "score-" + str(i),
                "source_file_id": "source-" + str(i)}, "source_files": [{"original_name": "piece-" + str(i) + ".musicxml",
                "source_file_id": "source-" + str(i), "sha256": "0" * 64}],
                "genuine_saved_fixture_full_IR_not_native_validated": True}
            ir_path = self.root / "output/IR/piece-" / str(i) / "canonical_music_ir.json"
            write_json(ir_path, ir)
            self.inputs[str(ir_path)] = trial.parent.file_digest(ir_path)
            scope = frozen._seal({"binding": trial.expanded._binding(ir), "analysis_span": frozen._span(0, 3),
                "status": "ready_expanded_scope", "graphs": [{"lane": ["part", "voice"], "factors": [
                    {"time": trial.q(1), "source_refs": ["a", "b"], "target_refs": ["c", "d"]},
                    {"time": trial.q(2), "source_refs": ["c", "d"], "target_refs": ["e", "f"]}]}],
                "sound_facts": [], "raw_lanes": [{"part_id": "part", "voice_id": "voice"}],
                "context_sound_inventory_complete": True}, trial.expanded.PREFIX)
            scope_path = trial.storage._save(self.scope_dir, scope["record_id"] + ".json.gz", scope, self.inputs, compressed=True)
            counts = {"logical_paths": 10, "logical_path_key_tuples": 50,
                      "logical_function_rows": 1000, "fixture_nullable_metric": None, "fixture_boolean_not_metric": False}
            old = frozen._seal({"version": old_engine.VERSION, "scope_ref": frozen._ref(scope),
                "analysis_span": deepcopy(scope["analysis_span"]), "resource_limits": deepcopy(previous.SETTINGS),
                "summary": counts, "status": "computed_conditional_context_prerequisites_not_selected",
                "selected": None, "flags": old_engine._flags()}, old_engine.PREFIX)
            old_path = trial.storage._save(self.parent_dir, "progression-contexts/" + old["record_id"] + ".json.gz",
                                          old, self.artifacts, compressed=True)
            row = {"context_key": key, "old_row_sha256": trial.digest({"fixture_parent": i}),
                **{k: {"storage_only_fixture": k} for k in previous.INHERITED_ROW_FIELDS},
                "old_groups": [{"group_id": "group"}], "old_lane_refs": [{"lane": ["part", "voice"],
                    "old_status": "ready", "old_graph_ref": {"record_id": "fixture_graph", "record_sha256": "0" * 64}}],
                "index_counts": {"groups": 1, "logical_paths": 10, "logical_path_key_tuples": 50,
                    "logical_function_shapes": 1000, "unknown_product_groups": 0, "indexed_variants": 4,
                    "shared_profile_descriptors": 3},
                "expanded_scope": {"artifact": str(scope_path), "sha256": self.inputs[str(scope_path)],
                    "record_ref": frozen._ref(scope), "status": scope["status"]},
                "progression_context": {"artifact": str(old_path), "sha256": self.artifacts[str(old_path)],
                    "record_ref": frozen._ref(old), "status": old["status"]},
                "context_counts": deepcopy(counts), "status": "progression_context_saved_not_selected",
                "error": None, "elapsed_seconds": 0.0}
            self.rows.append(row)
            self.scopes.append(scope)
            self.irs.append(ir)
            self.ir_paths.append(ir_path)
            self.values.append(old)
        self.plan = {"version": previous.VERSION, "progression": str(self.predecessor_dir),
            "parent_report_sha256": trial.parent.file_digest(self.predecessor_dir / "report.json"),
            "inputs": deepcopy(self.inputs), "code": {**self.predecessor_plan["code"],
                **{str(Path(m.__file__).resolve()): trial.parent.file_digest(m.__file__) for m in (previous, old_engine)}},
            "settings": deepcopy(previous.SETTINGS), "declared_contexts": [*keys, deferred],
            "declared_units": units, "selected_contexts": deepcopy(keys), "selection": {"storage_fixture": True},
            "coverage": previous.COVERAGE, "parent_panel_policy": previous.previous.PANEL_POLICY,
            "conditional_progression_context_stage_enabled": True,
            **{k: False for k in ("cohort_complete", "old_selector_or_analysis_reexecuted", "all_logical_paths_evaluated",
                "source_labels_used_for_inference", "old_paths_or_bundles_extended", "production_modified", "sample_is_accuracy_evaluation")}}
        # The exact historical closure is metadata-only, not original authority.
        self.predecessor_plan["inputs"] = {p: h for p, h in self.inputs.items()
            if p not in (str(self.producer), str(self.predecessor_dir / "run-plan.json"), str(self.predecessor_dir / "report.json"))}
        write_json(self.predecessor_dir / "run-plan.json", self.predecessor_plan)
        self.predecessor_report["artifact_hashes"][str(self.predecessor_dir / "run-plan.json")] = trial.parent.file_digest(self.predecessor_dir / "run-plan.json")
        write_json(self.predecessor_dir / "report.json", self.predecessor_report)
        self.inputs[str(self.predecessor_dir / "run-plan.json")] = trial.parent.file_digest(self.predecessor_dir / "run-plan.json")
        self.inputs[str(self.predecessor_dir / "report.json")] = trial.parent.file_digest(self.predecessor_dir / "report.json")
        self.plan["inputs"] = deepcopy(self.inputs)
        self.plan["parent_report_sha256"] = self.inputs[str(self.predecessor_dir / "report.json")]
        totals, metric, unknown = Counter(), Counter(), Counter()
        for row, value in zip(self.rows, self.values):
            trial.cohort._add_denominators(totals, row)
            for name, count in value["summary"].items():
                if type(count) is int:
                    metric[name] += count
                elif count is None:
                    unknown[name] += 1
        summary = {**dict(totals), "context_integer_subtotals": dict(metric), "context_unknown_metric_contexts": dict(unknown),
            "context_saved_contexts": 5, "context_failed_contexts": 0,
            **trial.cohort._cohort_counts(self.plan, totals), "context_status_counts": {"progression_context_saved_not_selected": 5}}
        self.report = {"version": previous.VERSION, **{k: True for k in ("scope_calculation_complete", "computation_integrity_passed",
            "selected_denominators_complete", "inputs_and_code_unchanged", "artifacts_unchanged", "conditional_progression_context_stage_enabled")},
            "changed_inputs_or_code": [], "changed_artifacts": [], "failures": [], "artifact_hashes": {},
            "parent_summary": deepcopy(self.predecessor_report["summary"]), "summary": summary, "selected": None,
            **{k: False for k in (*previous.POLICY_FALSE, "cohort_complete", "all_logical_paths_evaluated",
                "conditional_NCT_evaluated", "boundary_NCT_evaluated", "delayed_resolution_confirmed", "sample_is_accuracy_evaluation")},
            "elapsed_seconds": 0.0, "limits": ["storage-only fixture not corpus validation"]}
        self.refresh_parent()

    def refresh_parent(self):
        write_json(self.parent_dir / "run-plan.json", self.plan)
        write_json(self.parent_dir / "context-index.json", self.rows)
        self.artifacts.update({str(self.parent_dir / n): trial.parent.file_digest(self.parent_dir / n)
                               for n in ("run-plan.json", "context-index.json")})
        self.report["artifact_hashes"] = deepcopy(self.artifacts)
        write_json(self.parent_dir / "report.json", self.report)

    def mock_lattice(self, ir, scope, **caps):
        coordinates = [trial.q(i) for i in range(4)]
        entries = []
        for i in range(3):
            for j in range(i + 1, 4):
                origins = [frozen._seal({"fixture": n, "binding": deepcopy(scope["binding"]), "span": frozen._span(i, j)},
                                       engine.ORIGIN_PREFIX) for n in (1, 0)]
                entries.append({"point_indices": [i, j], "origins": origins})
        return frozen._seal({"version": engine.VERSION, "resource_limits": deepcopy(caps),
            "coordinate_times": coordinates, "catalog_inventory": entries,
            "keys": [{"record_id": "key-" + str(i)} for i in reversed(range(5))],
            "planned_catalogs": 6, "origin_count": 12, "materialized_origins": 12,
            "universe": engine._count_universe({(i, j): 2 for i in range(3) for j in range(i + 1, 4)}, 4, 5),
            "status": "ready_native_interval_lattice", "scope_ref": frozen._ref(scope)}, engine.PREFIX)

    def fake_prepare(self, ir, scope, **caps):
        return {"scope": deepcopy(scope), "lattice": self.mock_lattice(ir, scope, **caps)}

    def fake_bundle(self, session, links, **caps):
        return frozen._seal({"lattice_ref": frozen._ref(session["lattice"]), "required_links": deepcopy(links),
            "covered_lanes": [["part", "voice"]], "resource_limits": deepcopy(caps),
            "status": "complete_all_lane_witness"}, engine.BUNDLE_PREFIX)

    def fake_compare(self, session, selectors, bundle_id, **caps):
        paths = [{"origin_refs": [{"record_id": oid} for oid in s["origin_ids"]], "key_ref": {"record_id": s["key_id"]},
            "boundaries": [{}] * (len(s["origin_ids"]) + 1), "whole_path_account": {"raw_time_conserved": True}}
                 for s in selectors]
        # The actual issued native bundle is mocked; this is only storage logic.
        links = [] if not hasattr(self, "last_mock_bundle") else self.last_mock_bundle["required_links"]
        bundle = self.fake_bundle(session, links, geometry_work_budget=trial.SETTINGS["geometry_work_budget"])
        if bundle["record_id"] != bundle_id:
            raise AssertionError("fixture bundle request mismatch")
        return frozen._seal({"bundle_ref": frozen._ref(bundle), "selectors": deepcopy(selectors), "paths": paths,
            "resource_limits": deepcopy(caps), "summary": {"planned_selectors": len(selectors),
                "computed_selectors": len(paths), "computed_internal_transitions": sum(len(s["origin_ids"]) - 1 for s in selectors)},
            "status": "computed_native_multi_slot_comparison_not_selected", "reasons": []}, engine.COMPARISON_PREFIX)

    def issue_fake_bundle(self, *args, **kwargs):
        self.last_mock_bundle = self.fake_bundle(*args, **kwargs)
        return self.last_mock_bundle

    def run_mocked(self, **kwargs):
        with ExitStack() as stack:
            stack.enter_context(patch.object(trial, "ROOT", self.root))
            stack.enter_context(patch.object(trial, "_code_paths", return_value=[self.producer]))
            stack.enter_context(patch.object(previous, "load_inputs", side_effect=AssertionError("forbidden old cold loader")))
            stack.enter_context(patch.object(engine, "prepare_lattice", side_effect=self.fake_prepare))
            stack.enter_context(patch.object(engine, "lattice_prepared", side_effect=lambda s: deepcopy(s["lattice"])))
            stack.enter_context(patch.object(engine, "compile_bundle_prepared", side_effect=self.issue_fake_bundle))
            stack.enter_context(patch.object(engine, "compare_prepared", side_effect=self.fake_compare))
            stack.enter_context(redirect_stdout(io.StringIO()))
            return trial.run(self.parent_dir, self.output, **kwargs)


class RegisteredMetadataTests(StorageFixture, unittest.TestCase):
    def test_valid_registered_hashes_and_cohort_without_old_loader(self):
        with patch.object(previous, "load_inputs", side_effect=AssertionError("old cold loader")):
            data = trial.load_inputs(self.parent_dir)
        self.assertEqual(len(data["rows"]), 5)
        self.assertEqual(data["report"]["summary"]["declared_contexts"], 6)
        self.assertEqual(data["report"]["summary"]["unexecuted_original_raw_lanes"], 1)
        self.assertEqual(data["inventory"], {str(p.resolve()) for p in self.parent_dir.rglob("*") if p.is_file()})

    def test_report_closed_header_and_boolean_policies(self):
        for name, value in (("version", "foreign"), ("selected", 0), ("harmony_confirmed", True),
                            ("scope_calculation_complete", 1), ("conditional_NCT_evaluated", 0)):
            original = deepcopy(self.report)
            self.report[name] = value
            self.refresh_parent()
            with self.subTest(name=name), self.assertRaises(ValueError):
                trial.load_inputs(self.parent_dir)
            self.report = original
        self.report["foreign_header"] = True
        self.refresh_parent()
        with self.assertRaises(ValueError):
            trial.load_inputs(self.parent_dir)

    def test_plan_closed_header_policy_and_typed_caps(self):
        for name, value in (("coverage", "foreign"), ("parent_panel_policy", "foreign"),
                            ("source_labels_used_for_inference", True), ("sample_is_accuracy_evaluation", 0)):
            original = deepcopy(self.plan)
            self.plan[name] = value
            self.refresh_parent()
            with self.subTest(name=name), self.assertRaises(ValueError):
                trial.load_inputs(self.parent_dir)
            self.plan = original
        self.plan["settings"]["max_hypotheses"] = True
        self.refresh_parent()
        with self.assertRaises(ValueError):
            trial.load_inputs(self.parent_dir)

    def test_changed_registered_input_hash_rejected(self):
        write_json(self.ir_paths[0], {"changed": True})
        with self.assertRaisesRegex(ValueError, "input_hash_mismatch"):
            trial.load_inputs(self.parent_dir)

    def test_changed_historical_code_hash_rejected(self):
        write_json(self.producer, {"changed": True})
        with self.assertRaisesRegex(ValueError, "input_hash_mismatch"):
            trial.load_inputs(self.parent_dir)

    def test_missing_registered_input_rejected(self):
        self.ir_paths[0].unlink()
        with self.assertRaises(FileNotFoundError):
            trial.load_inputs(self.parent_dir)

    def test_unregistered_parent_artifact_rejected(self):
        write_json(self.parent_dir / "unexpected.json", {"unexpected": True})
        with self.assertRaisesRegex(ValueError, "inventory"):
            trial.load_inputs(self.parent_dir)

    def test_foreign_parent_artifact_rejected(self):
        self.report["artifact_hashes"][str(self.producer)] = trial.parent.file_digest(self.producer)
        write_json(self.parent_dir / "report.json", self.report)
        with self.assertRaisesRegex(ValueError, "outside_registered_directory"):
            trial.load_inputs(self.parent_dir)

    def test_exact_creation_closure_does_not_gain_future_child(self):
        self.plan["code"][str(Path(trial.__file__).resolve())] = trial.parent.file_digest(trial.__file__)
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "creation_hash_closure"):
            trial.load_inputs(self.parent_dir)

    def test_phase21_producer_is_required_not_arbitrary_metadata(self):
        self.plan["code"].pop(str(Path(previous.__file__).resolve()))
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "producer_not_registered"):
            trial.load_inputs(self.parent_dir)

    def test_exact_rows_and_original_lane_denominators(self):
        self.rows[0]["old_lane_refs"][0]["lane"] = ["foreign", "voice"]
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "raw_lane_denominator"):
            trial.load_inputs(self.parent_dir)

    def test_original_lane_reference_closed_shape(self):
        self.rows[0]["old_lane_refs"][0]["extra"] = True
        self.refresh_parent()
        with self.assertRaises(ValueError):
            trial.load_inputs(self.parent_dir)

    def test_duplicate_declared_unit_is_not_hidden(self):
        self.plan["declared_units"].append(deepcopy(self.plan["declared_units"][0]))
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "unique_declared_original"):
            trial.load_inputs(self.parent_dir)

    def test_bool_index_counts_are_not_integers(self):
        self.rows[0]["index_counts"]["groups"] = True
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "integer"):
            trial.load_inputs(self.parent_dir)

    def test_saved_counts_mismatch_rejected_even_with_new_storage_hash(self):
        self.rows[0]["context_counts"]["logical_paths"] += 1
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "counts_mismatch"):
            trial.load_inputs(self.parent_dir)

    def test_resealed_foreign_scope_pointer_rejected(self):
        old = self.values[0]
        body = {k: deepcopy(v) for k, v in old.items() if k not in ("record_id", "record_sha256")}
        body["scope_ref"] = frozen._ref(self.scopes[1])
        body["fixture_foreign_scope_pointer"] = True
        changed = frozen._seal(body, old_engine.PREFIX)
        old_path = Path(self.rows[0]["progression_context"]["artifact"])
        old_path.unlink()
        self.artifacts.pop(str(old_path))
        path = trial.storage._save(self.parent_dir, "progression-contexts/" + changed["record_id"] + ".json.gz",
                                  changed, self.artifacts, compressed=True)
        self.rows[0]["progression_context"] = {"artifact": str(path), "sha256": self.artifacts[str(path)],
            "record_ref": frozen._ref(changed), "status": changed["status"]}
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "scope_metadata_pointer"):
            trial.load_inputs(self.parent_dir)

    def test_full_registered_IR_binding_not_original_name(self):
        data = trial.load_inputs(self.parent_dir)
        ir, scope, info = trial.load_case(data, data["rows"][0])
        self.assertEqual(ir, self.irs[0])
        self.assertEqual(scope, self.scopes[0])
        self.assertEqual(info["artifact"], str(self.ir_paths[0]))
        self.assertTrue(info["registered_full_IR_not_projection"])

    def test_wrong_same_score_IR_is_not_substituted_or_synthesized(self):
        data = trial.load_inputs(self.parent_dir)
        ir = deepcopy(self.irs[0])
        ir["ir_document_id"] = "same_score_wrong_revision"
        write_json(self.ir_paths[0], ir)
        data["hashes"][str(self.ir_paths[0])] = trial.parent.file_digest(self.ir_paths[0])
        with self.assertRaisesRegex(ValueError, "not_found_no_synthesis"):
            trial.load_case(data, data["rows"][0])


class PanelTests(StorageFixture, unittest.TestCase):
    def lattice(self):
        return self.mock_lattice(self.irs[0], self.scopes[0], **engine.DEFAULTS)

    def test_all_five_keys_full_half_thirds_None_and_explicit_vector(self):
        lattice = self.lattice()
        before = trial.digest(lattice)
        panel = trial.technical_panel(lattice)
        self.assertEqual(panel["planned_selectors"], 25)
        self.assertEqual(panel["available_selectors"], 25)
        self.assertEqual(Counter(len(s["origin_ids"]) for s in panel["selectors"]), {1: 5, 2: 10, 3: 10})
        self.assertEqual({s["key_id"] for s in panel["selectors"]}, {"key-" + str(i) for i in range(5)})
        triples = [s for s in panel["selectors"] if len(s["origin_ids"]) == 3]
        self.assertEqual(sum(s["transition_assumptions"] == [None, None] for s in triples), 5)
        self.assertEqual(sum(s["transition_assumptions"] == [{"family": "V7", "quality": "M"}] * 2 for s in triples), 5)
        for row in panel["rows"]:
            for oid, pair in zip(row["native_origin_ids"], zip(row["point_indices"], row["point_indices"][1:])):
                entry = next(e for e in lattice["catalog_inventory"] if tuple(e["point_indices"]) == pair)
                self.assertEqual(oid, min(o["record_id"] for o in entry["origins"]))
        self.assertEqual(before, trial.digest(lattice))

    def test_nearest_exact_coordinate_tie_chooses_earlier(self):
        panel = trial.technical_panel(self.lattice())
        self.assertEqual(panel["rows"][1]["point_indices"], [0, 1, 3])
        self.assertEqual(panel["rows"][2]["point_indices"], [0, 1, 2, 3])

    def test_missing_internal_origin_keeps_whole_request_denominator(self):
        lattice = self.lattice()
        next(e for e in lattice["catalog_inventory"] if e["point_indices"] == [1, 2])["origins"] = []
        panel = trial.technical_panel(lattice)
        self.assertEqual(panel["planned_selectors"], 25)
        self.assertEqual(panel["available_selectors"], 15)
        self.assertEqual(panel["rows"][2]["status"], "whole_requested_partition_withheld")

    def test_whole_lattice_hold_has_no_favorable_prefix(self):
        lattice = self.lattice()
        lattice["status"] = "whole_lattice_hold"
        lattice["catalog_inventory"] = []
        panel = trial.technical_panel(lattice)
        self.assertEqual(panel["planned_selectors"], 25)
        self.assertEqual(panel["selectors"], [])
        self.assertTrue(all(r["status"] == "whole_requested_partition_withheld" for r in panel["rows"]))

    def test_colliding_thirds_are_not_replaced_with_other_cuts(self):
        lattice = self.lattice()
        lattice["coordinate_times"] = [trial.q(i) for i in (0, 1, 3)]
        panel = trial.technical_panel(lattice)
        self.assertIsNone(panel["rows"][2]["point_indices"])
        self.assertEqual(panel["rows"][2]["available_selectors"], 0)
        self.assertEqual(panel["planned_selectors"], 25)

    def test_greedy_probe_is_bounded_branch_and_merge_free(self):
        result = trial.greedy_links(self.scopes[0], 3)
        self.assertEqual(len(result), 3)
        self.assertEqual(len({a for a, _ in result}), 3)
        self.assertEqual(len({b for _, b in result}), 3)
        self.assertEqual(trial.greedy_links(self.scopes[0], 0), [])
        with self.assertRaises(ValueError):
            trial.greedy_links(self.scopes[0], 21)


class RunStorageTests(StorageFixture, unittest.TestCase):
    def test_append_only_artifacts_and_separate_denominators(self):
        before = {str(p): trial.parent.file_digest(p) for p in self.parent_dir.rglob("*") if p.is_file()}
        report = self.run_mocked()
        self.assertTrue(report["scope_calculation_complete"])
        self.assertEqual(report["summary"]["selected_contexts"], 5)
        self.assertEqual(report["summary"]["declared_contexts"], 6)
        self.assertEqual(report["summary"]["native_integer_subtotals"]["planned_panel_selector_occurrences"], 250)
        self.assertEqual(report["summary"]["native_integer_subtotals"]["computed_selector_occurrences"], 250)
        self.assertEqual(report["summary"]["native_integer_subtotals"]["computed_distinct_origin_path_keys"], 75)
        self.assertEqual(len(report["artifact_hashes"]), 27)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         {*report["artifact_hashes"], str(self.output / "report.json")})
        for path, checksum in report["artifact_hashes"].items():
            self.assertEqual(trial.parent.file_digest(path), checksum)
        self.assertEqual(before, {str(p): trial.parent.file_digest(p) for p in self.parent_dir.rglob("*") if p.is_file()})
        rows = read_json(self.output / "context-index.json")
        for original, row in zip(self.rows, rows):
            self.assertEqual(row["registered_parent_metadata"], original)
            self.assertEqual(row["registered_parent_row_sha256"], trial.digest(original))
            self.assertEqual(len(row["bundle_comparisons"]), 2)
            for pair in row["bundle_comparisons"]:
                self.assertTrue(pair["bundle"]["record_ref"]["record_id"].startswith(engine.BUNDLE_PREFIX))
        self.assertTrue(all(report[k] is False for k in trial.POLICY_FALSE))

    def test_no_greedy_control_only_does_not_duplicate_bundles(self):
        report = self.run_mocked(include_greedy_bundle=False)
        self.assertEqual(len(report["artifact_hashes"]), 17)
        counts = report["summary"]["native_integer_subtotals"]
        self.assertEqual(counts["registered_bundles"], 5)
        self.assertEqual(counts["computed_selector_occurrences"], 125)

    def test_failure_rows_remain_in_selected_and_declared_denominators(self):
        original = self.fake_prepare

        def fail_first(ir, scope, **caps):
            if ir["ir_document_id"] == self.irs[0]["ir_document_id"]:
                raise ValueError("fixture_calculation_failure")
            return original(ir, scope, **caps)

        self.fake_prepare = fail_first
        report = self.run_mocked()
        self.assertFalse(report["scope_calculation_complete"])
        self.assertEqual(report["summary"]["native_failed_contexts"], 1)
        self.assertEqual(report["summary"]["selected_contexts"], 5)
        self.assertEqual(report["summary"]["unexecuted_original_contexts"], 1)
        self.assertEqual(report["summary"]["native_integer_subtotals"]["computed_selector_occurrences"], 200)

    def test_IR_mutation_is_failed_not_successfully_aggregated(self):
        original = self.fake_prepare

        def mutate_first(ir, scope, **caps):
            session = original(ir, scope, **caps)
            if ir["ir_document_id"] == self.irs[0]["ir_document_id"]:
                ir["changed"] = True
            return session

        self.fake_prepare = mutate_first
        report = self.run_mocked()
        self.assertFalse(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["native_saved_contexts"], 4)
        self.assertEqual(report["summary"]["native_failed_contexts"], 1)
        self.assertEqual(report["summary"]["native_integer_subtotals"]["computed_selector_occurrences"], 200)

    def test_no_overwrite_after_success(self):
        self.run_mocked()
        before = {str(p): trial.parent.file_digest(p) for p in self.output.rglob("*") if p.is_file()}
        with self.assertRaisesRegex(ValueError, "new_direct_workspace_child"):
            self.run_mocked()
        self.assertEqual(before, {str(p): trial.parent.file_digest(p) for p in self.output.rglob("*") if p.is_file()})

    def test_explicit_shared_query_budget_preserved(self):
        report = self.run_mocked(query_work_budget=2000000)
        self.assertTrue(report["scope_calculation_complete"])
        plan = read_json(self.output / "run-plan.json")
        self.assertEqual(plan["settings"]["query_work_budget"], 2000000)
        for row in read_json(self.output / "context-index.json"):
            for pair in row["bundle_comparisons"]:
                comparison = read_gzip(Path(pair["comparison"]["artifact"]))
                self.assertEqual(comparison["resource_limits"]["query_work_budget"], 2000000)

    def test_whole_lattice_unknowns_are_not_zero_supplier_paths(self):
        original = self.mock_lattice

        def held(ir, scope, **caps):
            value = original(ir, scope, **caps)
            body = {k: deepcopy(v) for k, v in value.items() if k not in ("record_id", "record_sha256")}
            body.update(status="whole_lattice_hold", catalog_inventory=[], origin_count=None, materialized_origins=0,
                        universe=engine._count_universe({}, 4, 5))
            return frozen._seal(body, engine.PREFIX)

        self.mock_lattice = held
        report = self.run_mocked()
        self.assertTrue(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["native_unknown_metric_contexts"]["logical_paths"], 5)
        self.assertNotIn("logical_paths", report["summary"]["native_integer_subtotals"])
        self.assertEqual(report["summary"]["native_integer_subtotals"]["planned_panel_selector_occurrences"], 250)
        self.assertEqual(report["summary"]["native_integer_subtotals"]["computed_selector_occurrences"], 0)

    def test_whole_query_hold_preserves_submitted_and_unexecuted_requests(self):
        original = self.fake_compare

        def held(*args, **kwargs):
            value = original(*args, **kwargs)
            body = {k: deepcopy(v) for k, v in value.items() if k not in ("record_id", "record_sha256")}
            body["paths"] = []
            body["summary"]["computed_selectors"] = 0
            body["summary"]["computed_internal_transitions"] = 0
            body["status"] = "whole_comparison_hold"
            body["reasons"] = ["whole_query_work_request_exceeds_budget_no_prefix"]
            return frozen._seal(body, engine.COMPARISON_PREFIX)

        self.fake_compare = held
        report = self.run_mocked(query_work_budget=0)
        counts = report["summary"]["native_integer_subtotals"]
        self.assertEqual(counts["submitted_panel_selector_occurrences"], 250)
        self.assertEqual(counts["computed_selector_occurrences"], 0)
        self.assertEqual(counts["whole_comparison_holds"], 10)
        self.assertEqual(report["summary"]["selected_contexts"], 5)

    def test_invalid_native_output_seal_is_recorded_failure_without_drop(self):
        original = self.mock_lattice

        def invalid(ir, scope, **caps):
            value = original(ir, scope, **caps)
            value["status"] = "tampered_without_reseal"
            return value

        self.mock_lattice = invalid
        report = self.run_mocked()
        self.assertFalse(report["computation_integrity_passed"])
        self.assertEqual(report["summary"]["native_failed_contexts"], 5)
        self.assertEqual(report["summary"]["selected_contexts"], 5)
        self.assertEqual(report["summary"]["native_saved_contexts"], 0)


if __name__ == "__main__":
    unittest.main()
