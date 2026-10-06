"""Storage-only policy runner tests: synthetic archive, never music accuracy.

The prior storage TestCase is composed only as a temporary-file fixture factory,
not inherited or rediscovered. Its tiny XML->IR is genuine, but contrasts and
policy results here are explicitly mocked saved evidence, not native authority.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import native_progression_policy_trial as trial
import test_native_progression_contrast_trial as fixtures


class SavedPolicyStorageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SavedContrastStorageTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.parent = self.fixture.output
        self.output = self.root / "output/policy"
        self.code = self.root / "new-policy-producer-fixture.txt"
        self.code.write_text("storage-only policy producer fixture", encoding="utf-8")
        self.patchers = [patch.object(trial, "ROOT", self.root),
            patch.object(trial.parent, "ROOT", self.root),
            patch.object(trial.parent, "_code_paths", return_value=[self.fixture.producer]),
            patch.object(trial, "_code_paths", return_value=[self.fixture.producer, self.code])]
        for item in self.patchers:
            item.start()
            self.addCleanup(item.stop)
        with patch.object(trial.parent.engine, "compare", side_effect=self.contrast_fixture):
            self.parent_report = trial.parent.run(self.fixture.parent, self.parent)
        self.assertTrue(self.parent_report["computation_integrity_passed"])
        self.parent_plan = self.read(self.parent / "run-plan.json")
        self.parent_rows = self.read(self.parent / "context-index.json")

    def read(self, path):
        path = Path(path)
        with (gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")) as stream:
            return json.load(stream)

    def reseal(self, value, prefix):
        return fixtures.seal({k: v for k, v in value.items() if k not in ("record_id", "record_sha256")}, prefix)

    def contrast_fixture(self, scope, lattice, entries, **limits):
        value = self.fixture.result(scope, lattice, entries, **limits)
        origins = {o["record_id"]: o for c in lattice["catalog_inventory"] for o in c["origins"]}
        for facet, entry in zip(value["facets"], entries):
            native, role = entry["native_path"], entry["role_path"]
            facet.update({k: deepcopy(native[k]) for k in ("key_ref", "bundle_ref", "partition")})
            facet["transition_assumptions"] = deepcopy(role["transition_assumptions"])
            facet["slot_presentations"] = [{"slot_index": i, "origin_ref": ref, **deepcopy(origins[ref["record_id"]])}
                for i, ref in enumerate(native["origin_refs"])]
            categories = {key: trial.parent.parent.q(4 if key == "source_guarded_member" else 0)
                for key in trial.parent.engine.CATEGORIES}
            facet["account"] = {"raw_total_note_time_quarters": trial.parent.parent.q(4),
                "raw_state_note_time_quarters": {"member": trial.parent.parent.q(4),
                    "nonmember_not_confirmed_nct": trial.parent.parent.q(0), "spelling_unresolved": trial.parent.parent.q(0)},
                "note_time_quarters": categories, "raw_time_conserved": True, "union_counted_once": True}
        return self.reseal(value, trial.parent.engine.PREFIX)

    def refresh_parent(self):
        fixtures.write(self.parent / "context-index.json", self.parent_rows)
        fixtures.write(self.parent / "run-plan.json", self.parent_plan)
        for name in ("context-index.json", "run-plan.json"):
            path = str(self.parent / name)
            self.parent_report["artifact_hashes"][path] = trial.old._file_sha(path)
        fixtures.write(self.parent / "report.json", self.parent_report)

    def replace_contrast(self, position, value):
        info = self.parent_rows[position]["contrast"]
        fixtures.write(Path(info["artifact"]), value)
        info.update(sha256=trial.old._file_sha(info["artifact"]), record_ref=trial.sealed._ref(value), status=value["status"])
        self.parent_report["artifact_hashes"][info["artifact"]] = info["sha256"]
        self.parent_rows[position].update(summary=value["summary"], query_plan=value["query_plan"],
            status=value["status"], reasons=value["reasons"])
        self.refresh_parent()

    def evaluate_fixture(self, scope, lattice, contrast, *, bundles, work_budget):
        facets, entries = contrast["facets"], contrast["submitted_entry_refs"]
        held = work_budget == 0 or contrast["status"] == "whole_saved_contrast_hold"
        alternatives, groups = [], []
        grouped = defaultdict(list)
        for i, entry in enumerate(entries):
            facet = facets[i] if not held else None
            premise = {k: deepcopy(facet[k]) for k in ("key_ref", "bundle_ref", "partition", "transition_assumptions")} if facet else None
            alternative = {"entry_refs": deepcopy(entry), "premises": premise,
                "status": "held_whole_request" if held else trial.policy.STATUSES[1],
                "diagnostics": [] if held else [{"rule_id": "P07", "reason": "storage_fixture_not_music_inference",
                    "effect": "hold", "target": {}}], "transition_assessments": [],
                "account_pointer": None if held else {"parent_native_path_ref": facet["native_path_ref"],
                    "parent_role_path_ref": facet["role_path_ref"], "field": "account", "sha256": trial.digest(facet["account"])},
                "claim_scope": "no_partial_policy_evaluation" if held else
                    "declared_strategy_under_this_saved_completion_not_harmony_verdict",
                "selected": None, "rank": None, "confidence": None}
            alternatives.append(alternative)
            if not held:
                grouped[trial.digest(premise)].append(i)
        for checksum, indices in grouped.items():
            groups.append({"group_id": "nppgroup_" + checksum[:24], "premises": alternatives[indices[0]]["premises"],
                "alternative_indices": indices, "conditional_support_indices": [], "held_indices": indices,
                "declared_requirement_not_supported_indices": [],
                "competition": "fixed_premise_conditional_alternatives_no_unique_winner", "selected": None})
        summary = {"submitted_entries": len(entries), "evaluated_entries": 0 if held else len(entries),
            "withheld_entries": len(entries) if held else 0, "fixed_premise_groups": None if held else len(groups),
            "conditional_function_supported_alternatives": None if held else 0,
            "held_alternatives": None if held else len(entries),
            "declared_requirement_not_supported_alternatives": None if held else 0,
            "diagnostic_reason_counts": None if held else {"storage_fixture_not_music_inference": len(entries)} if entries else {}}
        return fixtures.seal({"version": trial.policy.VERSION, "rule_version": trial.policy.RULE_VERSION,
            "rules": trial.policy.RULES, "source_authority": trial.AUTHORITY,
            "parent_contrast_ref": trial.sealed._ref(contrast), "scope_ref": trial.sealed._ref(scope),
            "lattice_ref": trial.sealed._ref(lattice), "binding": scope["binding"], "analysis_span": scope["analysis_span"],
            "logical_universe": contrast["logical_universe"], "submitted_entry_refs": entries,
            "query_plan": {"planned_work": 1000, "literal_profile_and_reference_work": 100,
                "source_credit_cover_work": 10, "submitted_entries": len(entries),
                "planned_groups": len(grouped) if facets or not entries else None,
                "semantics": "storage_fixture_not_actual_policy_cost"},
            "resource_limits": {"work_budget": work_budget}, "alternatives": alternatives,
            "fixed_premise_groups": groups, "summary": summary, "reasons": ["mock_whole_request_hold"] if held else [],
            "status": "whole_saved_policy_hold" if held else "computed_saved_progression_policy_not_selected" if entries else "empty_saved_policy_request",
            "selected": None, "rank": None, "confidence": None,
            "flags": {key: False for key in trial.parent.RESULT_FLAGS}, "limitations": ["mock storage fixture"]}, trial.policy.PREFIX)

    def run_mock(self, **limits):
        with patch.object(trial.policy, "evaluate", side_effect=self.evaluate_fixture) as evaluate:
            report = trial.run(self.parent, self.output, **limits)
        return report, evaluate

    def test_append_only_and_every_strict_cap_precede_loading(self):
        self.output.mkdir()
        with patch.object(trial, "load_inputs") as loader:
            for target in (self.output, self.root, self.root / "output/nested/policy"):
                with self.assertRaises(ValueError):
                    trial.run(self.parent, target)
            self.output.rmdir()
            for key in trial.SETTINGS:
                for value in (True, -1, 1.5, "2", None):
                    with self.assertRaises(ValueError):
                        trial.run(self.parent, self.output, **{key: value})
            with self.assertRaises(ValueError):
                trial.run(self.parent, self.output, undeclared_limit=1)
            loader.assert_not_called()

    def test_registered_archive_has_all_four_controls_without_old_load_or_producers(self):
        forbidden = AssertionError("old/native producer replay forbidden")
        with patch.object(trial.parent, "load_inputs", side_effect=forbidden), \
                patch.object(trial.parent.engine, "compare", side_effect=forbidden), \
                patch.object(trial.parent.parent.native, "prepare_lattice", side_effect=forbidden), \
                patch.object(trial.parent.parent.roles, "prepare_explanations", side_effect=forbidden):
            data = trial.load_inputs(self.parent)
        self.assertEqual(len(data["cases"]), 4)
        self.assertEqual([len(c["contrast"]["facets"]) for c in data["cases"]], [50] * 4)
        self.assertEqual([len(i) for p, i in data["inventories"]], [7, 148])
        self.assertEqual(len(data["report"]["artifact_hashes"]), 6)
        self.assertFalse(self.output.exists())

    def test_changed_hash_and_exact_parent_inventory_are_required(self):
        path = Path(self.parent_rows[0]["contrast"]["artifact"])
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaises(ValueError):
            trial.load_inputs(self.parent)
        extra = self.parent / "unregistered.json"
        extra.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inventory"):
            trial.load_inputs(self.parent)

    def test_creation_collision_and_historical_code_inventory_cannot_be_resealed(self):
        key = str(self.fixture.producer)
        self.parent_plan["code"][key] = "0" * 64
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "conflicting"):
            trial.load_inputs(self.parent)
        self.parent_plan["code"][key] = trial.old._file_sha(key)
        self.parent_plan["code"][str(self.code)] = trial.old._file_sha(self.code)
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "historical"):
            trial.load_inputs(self.parent)

    def test_byte_group_entry_pair_caps_fail_before_output_and_evaluate(self):
        for limits in ({"max_file_bytes": 0}, {"max_decoded_file_bytes": 0}, {"max_total_decoded_bytes": 0},
                {"max_completion_groups": 3}, {"max_entries_per_completion": 49}, {"max_pairs_per_completion": 224}):
            with patch.object(trial.policy, "evaluate") as evaluate:
                with self.assertRaises(ValueError):
                    trial.run(self.parent, self.output, **limits)
                evaluate.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_strict_JSON_duplicates_NaN_and_decompressed_whole_caps(self):
        reader = trial.parent.BoundedReader(trial._settings({}))
        path = self.root / "malformed.json"
        for raw in ('{"duplicate":1,"duplicate":2}', '{"value":NaN}', '{"value":Infinity}'):
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(ValueError):
                reader.read(path)
        path = self.root / "oversized.json.gz"
        fixtures.write(path, {"value": "x" * 2000})
        with self.assertRaisesRegex(ValueError, "decoded"):
            trial.parent.BoundedReader(trial._settings({"max_decoded_file_bytes": 20})).read(path)

    def test_resealed_foreign_pair_ref_is_rejected_at_admission(self):
        value = self.read(self.parent_rows[0]["contrast"]["artifact"])
        value["pairs"][0]["left_role_path_ref"]["record_sha256"] = "0" * 64
        self.replace_contrast(0, self.reseal(value, trial.parent.engine.PREFIX))
        with self.assertRaisesRegex(ValueError, "pair_content_refs"):
            trial.load_inputs(self.parent)

    def test_resealed_reordered_facet_or_cross_key_cannot_change_submission(self):
        value = self.read(self.parent_rows[0]["contrast"]["artifact"])
        value["facets"][0], value["facets"][1] = value["facets"][1], value["facets"][0]
        self.replace_contrast(0, self.reseal(value, trial.parent.engine.PREFIX))
        with self.assertRaisesRegex(ValueError, "facet"):
            trial.load_inputs(self.parent)

    def test_full_IR_content_and_original_source_snapshots_are_not_synthesized(self):
        self.parent_rows[0]["original_source_files"] = []
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "source_snapshots"):
            trial.load_inputs(self.parent)

    def test_mock_policy_saves_all_alternatives_and_fixed_premise_groups(self):
        report, evaluate = self.run_mock()
        self.assertTrue(report["computation_integrity_passed"])
        self.assertTrue(report["submitted_policy_evaluation_complete"])
        self.assertEqual(evaluate.call_count, 4)
        self.assertEqual(report["summary"]["submitted_entries"], 200)
        self.assertEqual(report["summary"]["evaluated_entries"], 200)
        self.assertEqual(report["summary"]["fixed_premise_groups"], 100)
        self.assertEqual(report["summary"]["conditional_function_supported_alternatives"], 0)
        self.assertEqual(report["summary"]["held_alternatives"], 200)
        self.assertEqual(report["denominators"], self.parent_report["denominators"])
        self.assertEqual(len([p for p in self.output.rglob("*") if p.is_file()]), 7)
        self.assertTrue(all(report[k] is False for k in trial.POLICY_FALSE))
        self.assertEqual(report["fresh_native_preparations"], 0)
        rows = self.read(self.output / "context-index.json")
        for row in rows:
            self.assertEqual(len(self.read(row["policy"]["artifact"])["alternatives"]), 50)

    def test_whole_work_hold_retains_all_refs_and_unknown_counts(self):
        report, evaluate = self.run_mock(work_budget=0)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_policy_evaluation_complete"])
        self.assertEqual(evaluate.call_count, 4)
        self.assertEqual(report["whole_policy_holds"], 4)
        self.assertEqual(report["summary"]["evaluated_entries"], 0)
        self.assertEqual(report["summary"]["withheld_entries"], 200)
        for key in trial.NULLABLE_COUNT_FIELDS | {"diagnostic_reason_counts"}:
            self.assertIsNone(report["summary"][key])
            self.assertEqual(report["unknown_summary_completion_occurrences"][key], 4)
        for row in self.read(self.output / "context-index.json"):
            record = self.read(row["policy"]["artifact"])
            self.assertEqual(len(record["alternatives"]), 50)
            self.assertTrue(all(a["premises"] is None and a["account_pointer"] is None for a in record["alternatives"]))

    def test_mixed_hold_counts_are_unknown_not_successful_prefix(self):
        count = 0
        def mixed(*args, **kwargs):
            nonlocal count
            count += 1
            value = self.evaluate_fixture(*args, **kwargs)
            if count == 1:
                value = self.evaluate_fixture(*args, **{**kwargs, "work_budget": 0})
                value["resource_limits"]["work_budget"] = kwargs["work_budget"]
                value = self.reseal(value, trial.policy.PREFIX)
            return value
        with patch.object(trial.policy, "evaluate", side_effect=mixed):
            report = trial.run(self.parent, self.output)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_policy_evaluation_complete"])
        self.assertEqual(report["summary"]["evaluated_entries"], 150)
        self.assertEqual(report["summary"]["withheld_entries"], 50)
        self.assertIsNone(report["summary"]["held_alternatives"])
        self.assertEqual(report["known_computed_summary_subtotal"]["held_alternatives"], 150)

    def test_malformed_typed_policy_summary_or_promotion_is_failure(self):
        def invalid(*args, **kwargs):
            value = self.evaluate_fixture(*args, **kwargs)
            value["summary"]["evaluated_entries"] = True
            return self.reseal(value, trial.policy.PREFIX)
        with patch.object(trial.policy, "evaluate", side_effect=invalid):
            report = trial.run(self.parent, self.output)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(len(report["failures"]), 4)
        self.assertFalse(report["submitted_policy_evaluation_complete"])

    def test_returned_account_pointer_tamper_or_unique_winner_is_not_accepted(self):
        def invalid(*args, **kwargs):
            value = self.evaluate_fixture(*args, **kwargs)
            value["alternatives"][0]["account_pointer"]["sha256"] = "0" * 64
            return self.reseal(value, trial.policy.PREFIX)
        with patch.object(trial.policy, "evaluate", side_effect=invalid):
            report = trial.run(self.parent, self.output)
        self.assertEqual(len(report["failures"]), 4)
        self.assertIsNone(report["summary"])
        self.assertEqual(len(list((self.output / "policies").glob("*"))) if (self.output / "policies").exists() else 0, 0)

    def test_input_mutation_cannot_pass_with_saved_success(self):
        def mutate(scope, *args, **kwargs):
            value = self.evaluate_fixture(scope, *args, **kwargs)
            scope["unexpected_mutation"] = True
            return value
        with patch.object(trial.policy, "evaluate", side_effect=mutate):
            report = trial.run(self.parent, self.output)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(len(report["failures"]), 4)

    def test_closed_query_plan_new_cost_fields_are_strict_integers(self):
        case = trial.load_inputs(self.parent)["cases"][0]
        value = self.evaluate_fixture(case["scope"], case["lattice"], case["contrast"],
            bundles={case["bundle"]["record_id"]: case["bundle"]}, work_budget=2000000)
        for key in ("literal_profile_and_reference_work", "source_credit_cover_work"):
            for bad in (True, None, -1, 0.5, "1"):
                damaged = deepcopy(value)
                damaged["query_plan"][key] = bad
                with self.assertRaises(ValueError):
                    trial._validate_result(self.reseal(damaged, trial.policy.PREFIX), case, trial._settings({}))
        damaged = deepcopy(value)
        damaged["query_plan"]["unexpected"] = 0
        with self.assertRaises(ValueError):
            trial._validate_result(self.reseal(damaged, trial.policy.PREFIX), case, trial._settings({}))

    def test_source_file_mutation_is_protected_until_report(self):
        def mutate(*args, **kwargs):
            value = self.evaluate_fixture(*args, **kwargs)
            self.code.write_text("mutated", encoding="utf-8")
            return value
        with patch.object(trial.policy, "evaluate", side_effect=mutate):
            report = trial.run(self.parent, self.output)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIsNone(report["summary"])

    def test_output_byte_cap_never_saves_a_partial_policy(self):
        report, evaluate = self.run_mock(max_output_record_bytes=0)
        self.assertEqual(evaluate.call_count, 4)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(len(report["failures"]), 4)
        self.assertEqual(len([p for p in self.output.rglob("*") if p.is_file()]), 3)

    def test_known_empty_policy_validation_does_not_fabricate_evaluated_work(self):
        case = trial.load_inputs(self.parent)["cases"][0]
        case = deepcopy(case)
        contrast = case["contrast"]
        contrast.update(facets=[], pairs=[], submitted_entry_refs=[])
        contrast["summary"]["submitted_entries"] = 0
        contrast = self.reseal(contrast, trial.parent.engine.PREFIX)
        case["contrast"] = contrast
        value = self.evaluate_fixture(case["scope"], case["lattice"], contrast,
            bundles={case["bundle"]["record_id"]: case["bundle"]}, work_budget=2000000)
        trial._validate_result(value, case, trial._settings({}))
        self.assertEqual(value["status"], "empty_saved_policy_request")
        self.assertEqual(value["summary"]["evaluated_entries"], 0)
        self.assertEqual(value["summary"]["diagnostic_reason_counts"], {})


if __name__ == "__main__":
    unittest.main()
