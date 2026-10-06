"""Storage-only source-evidence pilot tests; no genuine native cold or accuracy.

The small saved IR/scope fixtures are metadata, not issued native authority.
All native/panel/role calculations are mocked. JSON, hash protection, ordered
batch completeness, null whole holds and bounded per-candidate case storage
are exercised independently from the music-engine tests.
"""
from collections import Counter
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import gzip
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_source_evidence_trial as trial
from test_factor_native_role_trial import StorageFixture, fixture_lattice, seal, write_json


class SourceEvidenceStorageTests(unittest.TestCase):
    def setUp(self):
        base = StorageFixture(methodName="runTest")
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.base = base
        self.root, self.native_parent, self.supplier_parent = base.root, base.native_parent, base.supplier_parent
        self.role_parent = self.root / "output/phase24"
        self.output = self.root / "output/source-evidence"
        self.role_parent.mkdir()
        base.ir["note_events"] = [{"note_id": "n" + str(i), "measure_id": "m", "source_ref_id": "sr" + str(i),
            "written_pitch": {"spelling": "C4", "step": "C", "alter": trial.q(0), "octave": 4, "midi_pitch": 60},
            "global_onset_quarter": trial.q(i), "onset_in_measure": trial.q(i), "notated_duration_quarter": trial.q(1)}
            for i in range(7)]
        base.ir["measures"] = [{"measure_id": "m", "printed_measure_number": "1", "sequential_measure_index": 0,
            "time_signature": {"beats": 6, "beat_type": 4}}]
        base.ir["source_references"] = [{"source_ref_id": "sr" + str(i), "xpath": "/fixture/note[" + str(i + 1) + "]"}
                                       for i in range(7)]
        write_json(base.ir_path, base.ir)
        base.plan["inputs"][str(base.ir_path)] = trial.old._file_sha(base.ir_path)
        self.rows, self.scopes = [], []
        self.keys = [["fixture:source-" + str(i), i, "context-" + str(i)] for i in range(5)]
        for position, (sound_count, internal_count) in enumerate(zip((5, 3, 2, 4, 3), (3, 1, 2, 3, 2))):
            scope = deepcopy(base.scope)
            scope.pop("record_id"); scope.pop("record_sha256")
            scope["binding"] = trial.old.expanded._binding(base.ir)
            scope["analysis_span"] = trial.old.sealed._span(0, 6)
            scope["sound_facts"] = []
            for i in range(sound_count):
                a = i % (internal_count + 1)
                b = a + 1 if a < internal_count else 6
                scope["sound_facts"].append({"sound_ref": "s" + str(i), "source_note_refs": ["n" + str(i)],
                    "pitch": deepcopy(base.ir["note_events"][i]["written_pitch"]),
                    "span": trial.old.sealed._span(a, b), "lane": ["p", "v"],
                    "attack_note_ref": "n" + str(i), "tie_chain_ref": None})
            scope = seal(scope, trial.old.expanded.PREFIX)
            path = self.root / "output/scopes" / (scope["record_id"] + ".json.gz")
            path.parent.mkdir(exist_ok=True)
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                import json
                json.dump(scope, stream)
            info = {"artifact": str(path), "sha256": trial.old._file_sha(path),
                    "record_ref": trial.sealed._ref(scope), "status": scope["status"]}
            base.plan["inputs"][str(path)] = info["sha256"]
            metadata = {**deepcopy(base.metadata), "context_key": self.keys[position], "expanded_scope": info}
            row = deepcopy(base.row)
            row.update({"context_key": self.keys[position], "registered_parent_metadata": metadata,
                "registered_parent_row_sha256": trial.digest(metadata), "elapsed_seconds": float(position + 1),
                "native_counts": {"materialized_origins": 10 + position, "observed_cut_coordinates": internal_count,
                    "stored_interval_catalogs": (internal_count + 2) * (internal_count + 1) // 2}})
            row["full_IR"]["sha256"] = trial.old._file_sha(base.ir_path)
            row["full_IR"]["ir_content_sha256"] = trial.digest(base.ir)
            self.rows.append(row); self.scopes.append(scope)
        base.plan["declared_contexts"] = [*self.keys, ["fixture:unexecuted", 9, "deferred"]]
        base.plan["selected_contexts"] = deepcopy(self.keys)
        base.plan["declared_units"] = [{"context_key": key, "lane": ["p", "v"]} for key in base.plan["declared_contexts"]]
        self.role_plan = {name: False for name in trial.ROLE_PLAN_KEYS}
        self.role_plan.update({"version": trial.old.VERSION, "native_parent": str(self.native_parent),
            "supplier_parent": str(self.supplier_parent), "inputs": deepcopy(base.plan["inputs"]),
            "code": deepcopy(base.plan["code"]), "source_authority": trial.old.AUTHORITY,
            "panel_policy": trial.old.PANEL_POLICY})
        self.role_report = {name: False for name in trial.ROLE_REPORT_KEYS}
        self.role_report.update({"version": trial.old.VERSION, "status": "native_role_probe_complete_not_selected",
            "computation_integrity_passed": True, "inputs_and_code_unchanged": True,
            "artifacts_unchanged": True, "role_calculation_complete": True,
            "changed_inputs_or_code": [], "changed_artifacts": [], "failures": [],
            "selected": None, "fresh_native_preparations": 1})
        self.refresh()

    def refresh(self):
        write_json(self.native_parent / "run-plan.json", self.base.plan)
        write_json(self.native_parent / "context-index.json", self.rows)
        self.base.report["artifact_hashes"] = {str(self.native_parent / name): trial.old._file_sha(self.native_parent / name)
                                               for name in ("run-plan.json", "context-index.json")}
        write_json(self.native_parent / "report.json", self.base.report)
        write_json(self.role_parent / "run-plan.json", self.role_plan)
        write_json(self.role_parent / "context-index.json", {"fixture_not_replayed": True})
        for i in range(7):
            write_json(self.role_parent / ("not-replayed-artifact-" + str(i) + ".json"), {"fixture": i})
        self.role_report["artifact_hashes"] = {str(path): trial.old._file_sha(path) for path in self.role_parent.iterdir()
                                              if path.name != "report.json"}
        write_json(self.role_parent / "report.json", self.role_report)

    def load(self, **kwargs):
        return trial.load_inputs(self.native_parent, self.supplier_parent, self.role_parent, **kwargs)

    def mocks(self, *, panel_hold=False, empty_panel=False, unknown_bound=False, role_hold=False, native_hold=False,
              mutate_IR=False, malformed_panel=False):
        stack = ExitStack()
        stack.enter_context(patch.object(trial, "ROOT", self.root))
        stack.enter_context(patch.object(trial, "_code_paths", return_value=[self.base.producer]))
        sessions, handles, bundles = {}, {}, {}
        lattice0 = fixture_lattice()
        body = trial.sealed._check(lattice0, trial.native.PREFIX)
        body.update(reasons=[], resource_limits=deepcopy(trial.native.DEFAULTS))
        for entry in body["catalog_inventory"]:
            for origin in entry["origins"]:
                origin.update(root={"step": "C", "alter": trial.q(0)}, members=[{"step": "C", "alter": trial.q(0)}],
                              span=trial.old.sealed._span(0, 6), blockers=[])
        # Fixture origins are not native-issued; they only carry lookup fields.
        def prepare(ir, scope, **limits):
            session = object()
            lattice_body = deepcopy(body)
            lattice_body["fixture_scope_ref"] = trial.sealed._ref(scope)
            lattice = seal(lattice_body, trial.native.PREFIX)
            sessions[session] = (ir, scope, lattice)
            if mutate_IR:
                ir["fixture_mutated_after_prepare"] = True
            return session

        def panel(handle, **limits):
            session = handles[handle]
            ir, scope, lattice = sessions[session]
            origin_ids = [origin["record_id"] for entry in lattice["catalog_inventory"] for origin in entry["origins"]]
            keys = [key["record_id"] for key in lattice["keys"]]
            selectors = [] if panel_hold or empty_panel else [{"origin_ids": [origin_ids[i % len(origin_ids)], origin_ids[(i // len(origin_ids)) % len(origin_ids)]],
                "key_id": keys[i % len(keys)], "transition_assumptions": [None]}
                for i in range(50)]
            upper = None if unknown_bound else 0 if empty_panel else 50
            summary = {"native_interval_catalogs": len(lattice["catalog_inventory"]), "native_origins": len(origin_ids),
                "requested_intervals": 6, "complete_proposal_paths": 0 if panel_hold or empty_panel else 2,
                "submitted_selectors": len(selectors), "planned_selector_upper_bound": upper,
                "unsubmitted_selector_bound": None if upper is None else upper - len(selectors),
                "evaluated_origin_occurrences": None if panel_hold else 10,
                "eligible_origin_occurrences": None if panel_hold else 8,
                "rejected_origin_occurrences": None if panel_hold else 2}
            if malformed_panel:
                summary["submitted_selectors"] = True
            return seal({"version": trial.panel_engine.VERSION, "policy": trial.panel_engine.POLICY,
                "scope_ref": trial.sealed._ref(scope), "lattice_ref": trial.sealed._ref(lattice),
                "logical_universe": deepcopy(lattice["universe"]),
                "native_request": {key: deepcopy(lattice[key]) for key in ("status", "reasons", "resource_limits")},
                "query_plan": {"selector_upper_bound": upper, "planned_selection_work": None if unknown_bound else 2000},
                "resource_limits": deepcopy(limits), "selectors": selectors,
                "status": "whole_source_panel_hold" if panel_hold else "computed_source_evidence_panel_not_selected",
                "summary": summary, "flags": {"winning_harmony_selected": False},
                "selected": None, "rank": None, "confidence": None}, trial.panel_engine.PREFIX)

        def prepare_panel(session):
            handle = object(); handles[handle] = session
            return handle

        def compile_bundle(session, links, **limits):
            bundle = seal({"status": "all_lane_witness_withheld" if limits["geometry_work_budget"] == 0 else "complete_all_lane_witness", "required_links": deepcopy(links),
                "scope_ref": trial.sealed._ref(sessions[session][1])}, trial.native.BUNDLE_PREFIX)
            bundles[bundle["record_id"]] = bundle
            return bundle

        def compare(session, selectors, bundle_id, **limits):
            lattice = sessions[session][2]
            origins = {origin["record_id"]: origin for entry in lattice["catalog_inventory"] for origin in entry["origins"]}
            keys = {key["record_id"]: key for key in lattice["keys"]}
            paths = [] if native_hold else [{"origin_refs": [trial.sealed._ref(origins[o]) for o in selector["origin_ids"]],
                "key_ref": trial.sealed._ref(keys[selector["key_id"]]), "bundle_ref": trial.sealed._ref(bundles[bundle_id]),
                "logical_tuple": {"transition_assumptions": deepcopy(selector["transition_assumptions"])},
                "partition": [trial.old.sealed._span(0, 6)]} for selector in selectors]
            return seal({"status": "whole_comparison_hold" if native_hold else "computed_native_comparison_not_selected",
                "bundle_ref": trial.sealed._ref(bundles[bundle_id]), "lattice_ref": trial.sealed._ref(lattice),
                "selectors": deepcopy(selectors), "paths": paths, "summary": {"planned_selectors": len(selectors)},
                "resource_limits": deepcopy(limits), "query_plan": {"planned_query_work": 100},
                "reasons": ["mock_native_whole_hold"] if native_hold else []}, trial.native.COMPARISON_PREFIX)

        def explain(handle, **limits):
            session, comparison = handle
            scope = sessions[session][1]
            paths = []
            if not role_hold and not native_hold:
                for native_path in comparison["paths"]:
                    clauses = []
                    assessed = bundles[native_path["bundle_ref"]["record_id"]]["status"] == "complete_all_lane_witness"
                    sounds = scope["sound_facts"][:2]
                    for role, status in (("local_neighbor", "supported"), ("local_passing", "failed")):
                        if not assessed:
                            continue
                        clauses.append(seal({"role": role, "status": status, "qualified": True,
                            "geometry_id": trial.digest([scope["record_id"], role]),
                            "sound_refs": [sound["sound_ref"] for sound in sounds],
                            "source_note_refs": [note for sound in sounds for note in sound["source_note_refs"]],
                            "full_sound_spans": [sound["span"] for sound in sounds],
                            "actual_required_links": [["s0", "s1"]], "origin_refs": deepcopy(native_path["origin_refs"]),
                            "prerequisites": {"fixture_condition": status == "supported"},
                            "failed_prerequisites": [] if status == "supported" else ["fixture_condition"],
                            "blockers": [], "clips": [{"sound_ref": "s1", "span": sounds[1]["span"]}]
                                if status == "supported" else []}, "fmnroleclause_"))
                    paths.append(seal({**deepcopy(native_path), "clauses": clauses, "account": {
                        "raw_time_conserved": True, "conditional_explanation_note_time_quarters": trial.q(1) if assessed else None,
                        "explained_intervals_by_sound": [{"sound_ref": "s1", "spans": [sounds[1]["span"]]}] if assessed else [],
                        "status": "conditional_account_not_NCT_verdict" if assessed else "unassessed_completion_raw_time_preserved"},
                        "status": "assessed_same_completion" if assessed else "unassessed_completion"}, "fmnrolepath_"))
            clauses = [clause for path in paths for clause in path["clauses"]]
            status_counts = Counter(clause["status"] for clause in clauses)
            held = role_hold or native_hold
            return seal({"version": trial.roles.VERSION, "paths": paths,
                "status": "whole_explanation_hold" if held else "computed_native_role_explanations_not_selected",
                "native_comparison_ref": trial.sealed._ref(comparison), "scope_ref": trial.sealed._ref(scope),
                "bundle_ref": deepcopy(comparison["bundle_ref"]), "lattice_ref": deepcopy(comparison["lattice_ref"]),
                "native_request": {key: deepcopy(comparison[key]) for key in (
                    "selectors", "resource_limits", "status", "reasons", "summary", "query_plan")},
                "query_plan": {"clause_upper_bound": 100, "planned_query_work": 200},
                "summary": {"planned_paths": comparison["summary"]["planned_selectors"],
                    "native_computed_paths": len(comparison["paths"]), "computed_paths": len(paths),
                    "planned_clause_upper_bound": 100,
                    "unique_geometry_count": len({clause["geometry_id"] for clause in clauses}),
                    "role_clause_occurrences": dict(Counter(clause["role"] for clause in clauses)),
                    "evaluated_clauses": len(clauses), "qualified_clauses": len(clauses),
                    "satisfied_clauses": status_counts["supported"], "failed_clauses": status_counts["failed"],
                    "unassessed_clauses": 0, "credit_sound_occurrences": sum(len(path["account"]["explained_intervals_by_sound"]) for path in paths),
                    "withheld_paths": comparison["summary"]["planned_selectors"] - len(paths)},
                "reasons": ["mock_whole_hold"] if held else []}, trial.roles.PREFIX)

        prepare_mock = stack.enter_context(patch.object(trial.native, "prepare_lattice", side_effect=prepare))
        stack.enter_context(patch.object(trial.native, "lattice_prepared", side_effect=lambda session: sessions[session][2]))
        stack.enter_context(patch.object(trial.panel_engine, "prepare_panel", side_effect=prepare_panel))
        stack.enter_context(patch.object(trial.panel_engine, "panel_prepared", side_effect=panel))
        bundle_mock = stack.enter_context(patch.object(trial.native, "compile_bundle_prepared", side_effect=compile_bundle))
        compare_mock = stack.enter_context(patch.object(trial.native, "compare_prepared", side_effect=compare))
        stack.enter_context(patch.object(trial.roles, "prepare_explanations", side_effect=lambda session, c: (session, c)))
        role_mock = stack.enter_context(patch.object(trial.roles, "explain_prepared", side_effect=explain))
        stack.enter_context(redirect_stdout(io.StringIO()))
        return stack, prepare_mock, bundle_mock, compare_mock, role_mock

    def run_mock(self, **mock_options):
        stack, prepare, bundle, compare, role = self.mocks(**mock_options)
        with stack:
            report = trial.run(self.native_parent, self.supplier_parent, self.role_parent, self.output)
        return report, prepare, bundle, compare, role

    def test_append_only_and_strict_caps_before_all_source_loads(self):
        self.output.mkdir()
        with patch.object(trial, "ROOT", self.root), patch.object(trial, "load_inputs") as loader:
            for output in (self.output, self.root, self.root / "output/nested/new"):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    trial.run("missing", "missing", "missing", output)
            for name in trial.SETTINGS:
                for value in (True, -1, 1.5, None, "1"):
                    with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                        trial.run("missing", "missing", "missing", self.root / "output/new", **{name: value})
            for caps in ({"unknown": 1}, {"max_contexts": 3}, {"max_contexts": True}, {"max_selectors": 65},
                         {"max_hypotheses": 4}, {"max_slots": 4}, {"max_greedy_links": 21}):
                with self.subTest(caps=caps), self.assertRaises(ValueError):
                    trial.run("missing", "missing", "missing", self.root / "output/new", **caps)
            loader.assert_not_called()

    def test_source_size_selection_all_five_manifest_without_native_or_role_outcomes(self):
        with patch.object(trial.native, "prepare_lattice", side_effect=AssertionError("native cold")):
            data = self.load()
        self.assertEqual(data["selected_positions"], [1, 2])
        self.assertEqual(len(data["manifest"]), 5)
        self.assertEqual([row["observed_coordinate_count"] for row in data["manifest"]], [5, 3, 4, 5, 4])
        self.assertEqual([row["source_sound_count"] for row in data["manifest"]], [5, 3, 2, 4, 3])
        self.assertEqual(sum(row["selected_for_new_execution"] for row in data["manifest"]), 2)
        self.assertEqual(trial.old._guard(data["hashes"]), [])
        self.assertEqual(len(data["inventories"][str(self.role_parent)]), 10)
        self.assertFalse(self.output.exists())

    def test_phase24_exact_inventory_hash_and_typed_creation_count(self):
        path = self.role_parent / "not-replayed-artifact-0.json"
        write_json(path, {"changed": True})
        with self.assertRaisesRegex(ValueError, "hash_changed"):
            self.load()
        self.refresh()
        self.role_report["fresh_native_preparations"] = True
        self.refresh()
        with self.assertRaisesRegex(ValueError, "integer"):
            self.load()

    def test_phase24_code_input_SHA_conflict_and_extra_artifact_reject(self):
        self.role_plan["inputs"][str(self.base.producer)] = "0" * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, "conflicting_registered_SHA256"):
            self.load()
        self.role_plan["inputs"].pop(str(self.base.producer))
        self.refresh()
        write_json(self.role_parent / "extra.json", {})
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.load()

    def test_exact_source_coordinate_manifest_mismatch_rejects_before_native(self):
        self.rows[2]["native_counts"]["observed_cut_coordinates"] += 1
        self.refresh()
        with patch.object(trial.native, "prepare_lattice") as prepare:
            with self.assertRaisesRegex(ValueError, "coordinate_count_mismatch"):
                self.load()
            prepare.assert_not_called()

    def test_ordered_fifty_selector_batches_are_exact_detached_complete(self):
        selectors = [{"origin_ids": [str(i)], "key_id": "key", "transition_assumptions": []} for i in range(50)]
        batches = trial._batches(selectors)
        self.assertEqual(len(batches), 17)
        self.assertEqual([len(batch) for batch in batches], [3] * 16 + [2])
        self.assertEqual([selector for batch in batches for selector in batch], selectors)
        batches[0][0]["origin_ids"][0] = "mutated"
        self.assertEqual(selectors[0]["origin_ids"], ["0"])

    def test_mock_two_context_all_batches_both_bundles_exact_counts_and_protected_hashes(self):
        old_hashes = {str(path): trial.old._file_sha(path) for directory in (
            self.native_parent, self.supplier_parent, self.role_parent) for path in directory.rglob("*") if path.is_file()}
        report, prepare, bundle, compare, role = self.run_mock()
        self.assertTrue(report["computation_integrity_passed"])
        self.assertTrue(report["submitted_role_calculation_complete"])
        self.assertEqual((prepare.call_count, bundle.call_count, compare.call_count, role.call_count), (2, 4, 68, 68))
        self.assertEqual(report["fresh_native_preparations"], 2)
        self.assertEqual(report["denominators"], {"declared_contexts": 6, "declared_original_raw_lanes": 6,
            "registered_context_pool": 5, "selected_contexts": 2, "selected_original_raw_lanes": 2,
            "unexecuted_declared_contexts": 4, "unexecuted_declared_original_raw_lanes": 4})
        self.assertEqual(report["summary"]["context_occurrence_subtotals"]["computed_role_paths"], 200)
        counts = report["summary"]["context_occurrence_subtotals"]
        self.assertEqual(counts["computed_distinct_origin_key_function_path_tuples"], 100)
        self.assertEqual(counts["computed_distinct_same_completion_logical_tuples"], 200)
        self.assertEqual(counts["computed_distinct_key_hypotheses"], 4)
        self.assertEqual(counts["unique_role_geometries"], 4)
        self.assertEqual(counts["unique_role_geometry_statuses"], 4)
        self.assertEqual(report["summary"]["role_status_occurrences"], {"local_neighbor:supported": 200, "local_passing:failed": 200})
        self.assertEqual(report["summary"]["submitted_batch_occurrences"], 68)
        self.assertEqual(report["summary"]["conditional_explained_note_time_selector_occurrence_sum"], trial.q(200))
        self.assertEqual(trial.old._guard({**old_hashes, **report["artifact_hashes"]}), [])
        self.assertTrue(all(report[key] is False for key in trial.POLICY_FALSE))
        for call in compare.call_args_list:
            self.assertLessEqual(len(call.args[1]), 3)
            self.assertEqual(call.kwargs["query_work_budget"], 2000000)
        self.assertTrue(all(call.kwargs["query_work_budget"] == 100000000 for call in role.call_args_list))
        trial.old._inventory(self.output, report["artifact_hashes"], self.output / "report.json")

    def test_mock_bounded_samples_keep_exact_notes_candidate_interpretations_separate(self):
        report, *_ = self.run_mock()
        samples = trial.old._read(self.output / "case-samples.json")
        self.assertEqual(samples["saved_samples"], 4)
        self.assertEqual(samples["eligible_candidate_occurrences"], 400)
        self.assertFalse(samples["NCT_confirmed"])
        for case in samples["cases"]:
            self.assertNotIn("prerequisites", case)
            self.assertTrue(case["notated_note_snapshots"])
            self.assertEqual(case["notated_note_snapshots"][0]["display"]["notated_denominator_beat_1_based"], trial.q(1))
            self.assertEqual(case["notated_note_snapshots"][0]["notated_duration_quarter"], trial.q(1))
            self.assertIn("full_sounding_duration_quarters", case["sound_snapshots"][0])
            self.assertEqual(len(case["candidate_occurrences"]), 100)
            for occurrence in case["candidate_occurrences"]:
                self.assertIn("prerequisites", occurrence)
                self.assertIn("conditional_credit_clips", occurrence)
                self.assertTrue(occurrence["candidate_spellings"][0]["members"])
                self.assertIn("partition", occurrence)
                self.assertIn("bundle_ref", occurrence)

    def test_mock_panel_budget_whole_hold_known_plan_is_not_failure_or_completed_roles(self):
        report, prepare, bundle, compare, role = self.run_mock(panel_hold=True)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_role_calculation_complete"])
        self.assertEqual((prepare.call_count, bundle.call_count, compare.call_count, role.call_count), (2, 4, 0, 0))
        self.assertEqual(report["summary"]["whole_panel_holds"], 2)
        self.assertEqual(report["summary"]["planned_batch_upper_bound_occurrences"], 68)
        self.assertEqual(report["summary"]["unsubmitted_selector_upper_bound_occurrences"], 200)
        self.assertEqual(report["summary"]["context_occurrence_subtotals"]["computed_selector_occurrences"], 0)

    def test_mock_unknown_panel_bounds_remain_null_with_unknown_denominators(self):
        report, *_ = self.run_mock(panel_hold=True, unknown_bound=True)
        self.assertTrue(report["computation_integrity_passed"])
        summary = report["summary"]
        self.assertIsNone(summary["planned_batch_upper_bound_occurrences"])
        self.assertIsNone(summary["unsubmitted_selector_upper_bound_occurrences"])
        self.assertIsNone(summary["context_occurrence_subtotals"]["planned_structural_selector_occurrences"])
        self.assertEqual(summary["unknown_occurrence_denominator_contexts"], {"planned_structural_selector_occurrences": 2})
        self.assertFalse(report["submitted_role_calculation_complete"])

    def test_mock_zero_context_noop_has_integrity_without_submitted_role_completion(self):
        stack, prepare, bundle, compare, role = self.mocks()
        with stack:
            report = trial.run(self.native_parent, self.supplier_parent, self.role_parent, self.output, max_contexts=0)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_role_calculation_complete"])
        self.assertEqual((prepare.call_count, bundle.call_count, compare.call_count, role.call_count), (0, 0, 0, 0))
        self.assertEqual(report["denominators"]["selected_contexts"], 0)
        self.assertEqual(report["summary"]["submitted_batch_occurrences"], 0)

    def test_mock_known_empty_panel_does_not_claim_submitted_role_completion(self):
        report, prepare, bundle, compare, role = self.run_mock(empty_panel=True)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_role_calculation_complete"])
        self.assertEqual((prepare.call_count, bundle.call_count, compare.call_count, role.call_count), (2, 4, 0, 0))
        self.assertEqual(report["summary"]["whole_panel_holds"], 0)
        self.assertEqual(report["summary"]["submitted_batch_occurrences"], 0)
        self.assertEqual(report["summary"]["planned_batch_upper_bound_occurrences"], 0)

    def test_mock_withheld_completion_null_accounts_never_become_zero_credit(self):
        stack, prepare, bundle, compare, role = self.mocks()
        with stack:
            report = trial.run(self.native_parent, self.supplier_parent, self.role_parent, self.output, geometry_work_budget=0)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_role_calculation_complete"])
        self.assertEqual((prepare.call_count, bundle.call_count, compare.call_count, role.call_count), (2, 4, 68, 68))
        summary = report["summary"]
        self.assertEqual(summary["context_occurrence_subtotals"]["unknown_role_account_occurrences"], 200)
        self.assertEqual(summary["context_occurrence_subtotals"]["uncomputed_role_account_occurrences"], 0)
        self.assertEqual(summary["context_occurrence_subtotals"]["assessed_role_account_occurrences"], 0)
        self.assertIsNone(summary["conditional_explained_note_time_selector_occurrence_sum"])
        self.assertEqual(summary["known_conditional_explained_note_time_selector_occurrence_subtotal"], trial.q(0))
        rows = trial.old._read(self.output / "context-index.json")
        self.assertTrue(all(row["counts"]["conditional_explained_note_time_selector_occurrence_sum"] is None for row in rows))
        self.assertEqual(summary["case_sample_counts"]["saved_samples"], 0)

    def test_mock_native_or_role_hold_all_later_batches_still_saved(self):
        report, _, _, compare, role = self.run_mock(native_hold=True)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_role_calculation_complete"])
        self.assertEqual((compare.call_count, role.call_count), (68, 68))
        self.assertEqual(report["summary"]["role_integer_occurrence_subtotals"]["withheld_paths"], 200)
        self.assertEqual(report["summary"]["context_occurrence_subtotals"]["whole_comparison_holds"], 68)
        self.assertEqual(report["summary"]["context_occurrence_subtotals"]["uncomputed_role_account_occurrences"], 200)
        self.assertIsNone(report["summary"]["conditional_explained_note_time_selector_occurrence_sum"])
        self.assertEqual(report["summary"]["known_conditional_explained_note_time_selector_occurrence_subtotal"], trial.q(0))
        self.assertEqual(report["summary"]["case_sample_counts"]["saved_samples"], 0)

    def test_mock_role_only_hold_preserves_native_paths_without_credits(self):
        report, _, _, compare, role = self.run_mock(role_hold=True)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_role_calculation_complete"])
        self.assertEqual((compare.call_count, role.call_count), (68, 68))
        counts = report["summary"]["context_occurrence_subtotals"]
        self.assertEqual(counts["computed_selector_occurrences"], 200)
        self.assertEqual(counts["computed_role_paths"], 0)
        self.assertEqual(counts["whole_explanation_holds"], 68)
        self.assertEqual(report["summary"]["role_integer_occurrence_subtotals"]["withheld_paths"], 200)
        self.assertEqual(counts["uncomputed_role_account_occurrences"], 200)
        self.assertIsNone(report["summary"]["conditional_explained_note_time_selector_occurrence_sum"])
        self.assertEqual(report["summary"]["known_conditional_explained_note_time_selector_occurrence_subtotal"], trial.q(0))

    def test_mock_source_mutation_invalidates_context_and_discards_partial_samples(self):
        report, prepare, *_ = self.run_mock(mutate_IR=True)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertFalse(report["submitted_role_calculation_complete"])
        self.assertIsNone(report["summary"])
        self.assertEqual(prepare.call_count, 2)
        self.assertEqual(len(report["failures"]), 2)
        self.assertEqual(trial.old._read(self.output / "case-samples.json")["eligible_candidate_occurrences"], 0)

    def test_mock_malformed_panel_or_source_mutation_never_success_counts(self):
        report, prepare, *_ = self.run_mock(malformed_panel=True)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(prepare.call_count, 2)
        self.assertEqual(len(report["failures"]), 2)
        samples = trial.old._read(self.output / "case-samples.json")
        self.assertEqual(samples["eligible_candidate_occurrences"], 0)

    def test_sample_limits_dedup_status_without_collapsing_candidate_prerequisites(self):
        occurrences = []
        for status in ("supported", "failed"):
            for i in range(4):
                for candidate in range(2):
                    occurrences.append({"role": "local_neighbor", "geometry_id": "geometry" + str(i), "status": status,
                        "candidate_occurrence": {"prerequisites": {"value": candidate == 0}, "ordinal": candidate},
                        "context_key": ["fixture", 0, "context"], "full_IR": {"artifact": "fixture_IR"},
                        "scope_ref": {"record_id": "fixture_scope", "record_sha256": "0" * 64},
                        "source_note_refs": ["n0"], "full_sound_spans": [trial.old.sealed._span(0, 1)]})
        samples = trial._case_samples(occurrences)
        self.assertEqual((samples["eligible_candidate_occurrences"], samples["distinct_eligible_role_geometry_status"],
                          samples["saved_samples"], samples["withheld_distinct_eligible_role_geometry_status"]), (16, 8, 6, 2))
        self.assertEqual(samples["saved_sample_counts_by_role_status"], {"local_neighbor:failed": 3, "local_neighbor:supported": 3})
        self.assertTrue(all(len(case["candidate_occurrences"]) == 2 for case in samples["cases"]))

    def test_same_geometry_in_different_contexts_keeps_exact_IR_scope_source_identity(self):
        row = {"role": "local_neighbor", "geometry_id": "shared-geometry", "status": "supported",
            "context_key": ["first", 0, "context"], "full_IR": {"artifact": "first_IR", "sha256": "1" * 64},
            "scope_ref": {"record_id": "first_scope", "record_sha256": "2" * 64},
            "source_note_refs": ["first_note"], "candidate_occurrence": {"ordinal": "first"}}
        other = deepcopy(row)
        other.update(context_key=["second", 0, "context"], full_IR={"artifact": "second_IR", "sha256": "3" * 64},
            scope_ref={"record_id": "second_scope", "record_sha256": "4" * 64}, source_note_refs=["second_note"],
            candidate_occurrence={"ordinal": "second"})
        samples = trial._case_samples([row, other])
        self.assertEqual(samples["distinct_eligible_role_geometry_status"], 2)
        self.assertEqual(samples["saved_samples"], 2)
        by_IR = {case["full_IR"]["artifact"]: case for case in samples["cases"]}
        self.assertEqual(by_IR["first_IR"]["source_note_refs"], ["first_note"])
        self.assertEqual(by_IR["first_IR"]["candidate_occurrences"], [{"ordinal": "first"}])
        self.assertEqual(by_IR["second_IR"]["source_note_refs"], ["second_note"])
        self.assertEqual(by_IR["second_IR"]["candidate_occurrences"], [{"ordinal": "second"}])


if __name__ == "__main__":
    unittest.main()
