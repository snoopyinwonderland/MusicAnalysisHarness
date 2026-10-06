"""Availability-based family batches preserve full cohort and selected scope."""
from collections import Counter
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_functional_batch as batch
from musicanote_harness import factor_functional_trial as functional
from musicanote_harness import factor_musical_trial as meaning
from musicanote_harness import harmony_frozen_context_lineage_trial as lineage
from musicanote_harness import factor_musical_view as common
from test_harmony_frozen_context_lineage_trial import fixture
from test_harmony_frozen_context_voice_trial import read_gzip, write_gzip
from test_source_locator_revision_trial import read_json, write_json, sha


def selection_fixture():
    data = {"packages": {}, "contexts": {}}
    rows = []
    for pair, family, collection, prepared in [
            ("a1", "fa", "A", False), ("a2", "fa", "A", True),
            ("b1", "fb", "A", True), ("c1", "fc", "B", True),
            ("d1", "fd", "C", False)]:
        data["packages"][pair] = {"source": {"manifest_entry": {
            "work_family_id": family, "corpus_id": "corpus", "collection_id": collection}}}
        key = (pair, 0, "sample")
        data["contexts"][key] = {}
        group = {"group_id": "change:1", "status": "paths_prepared" if prepared else "withheld_path_budget",
                 "planned_paths": 2 if prepared else 999}
        rows.append({"context_key": list(key), "work_family_id": family,
                     "collection": ["corpus", collection], "groups": [group],
                     "eligible_change_group_ids": ["change:1"] if prepared else []})
    return data, rows


class FamilySelectionTests(unittest.TestCase):
    def test_first_eligible_context_and_collection_round_robin(self):
        data, rows = selection_fixture()
        result = batch.select_families(data, rows, 2)
        self.assertEqual(result["eligible_family_order"], ["fa", "fc", "fb"])
        self.assertEqual(result["selected_family_order"], ["fa", "fc"])
        self.assertEqual(result["selected_contexts"], [["a2", 0, "sample"], ["c1", 0, "sample"]])
        fa = result["family_decisions"][0]
        self.assertEqual(fa["preceding_noneligible_contexts"][0]["context_key"], ["a1", 0, "sample"])
        self.assertEqual(fa["package_ids"], ["a1", "a2"])

    def test_whole_family_deferred_and_no_eligible_remain_distinct(self):
        data, rows = selection_fixture()
        result = batch.select_families(data, rows, 1)
        self.assertEqual(Counter(r["status"] for r in result["family_decisions"]),
                         {"scheduled": 1, "deferred_family_limit": 2, "no_paths_prepared_change_context": 1})
        self.assertEqual(len(result["family_decisions"]), 4)
        fd = result["family_decisions"][-1]
        self.assertEqual(fd["preceding_noneligible_contexts"][0]["groups"][0]["planned_paths"], 999)

    def test_no_key_clock_geometry_or_musical_labels_select_cases(self):
        data, rows = selection_fixture()
        before = batch.select_families(data, rows, 99)
        for row in rows:
            row.update(key_status="unknown", source_clock_passed=False, geometry_status="abstention",
                       roman_label="unrelated source annotation", positive_outcome=False)
        after = batch.select_families(data, rows, 99)
        self.assertEqual(before["selected_contexts"], after["selected_contexts"])
        self.assertFalse(after["source_annotation_labels_used"])
        self.assertFalse(after["outcomes_used_for_selection"])
        self.assertFalse(after["key_or_geometry_or_source_gate_used_for_selection"])

    def test_boolean_zero_negative_fraction_limits_rejected(self):
        data, rows = selection_fixture()
        for limit in (True, 0, -1, 1.5, None):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                batch.select_families(data, rows, limit)

    def test_full_order_and_family_identity_required(self):
        data, rows = selection_fixture()
        with self.assertRaisesRegex(ValueError, "frozen_context_order"):
            batch.select_families(data, list(reversed(rows)), 2)
        rows[0]["work_family_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "family_identity"):
            batch.select_families(data, rows, 2)

    def test_cross_collection_family_ambiguity_and_missing_identity_rejected(self):
        data, rows = selection_fixture()
        data["packages"]["a2"]["source"]["manifest_entry"]["collection_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "cross_collection"):
            batch.select_families(data, rows, 2)
        data, rows = selection_fixture()
        del data["packages"]["a1"]["source"]["manifest_entry"]["work_family_id"]
        with self.assertRaisesRegex(ValueError, "identity_required"):
            batch.select_families(data, rows, 2)

    def test_fake_prepared_change_not_accepted(self):
        data, rows = selection_fixture()
        rows[0]["eligible_change_group_ids"] = ["change:1"]
        with self.assertRaisesRegex(ValueError, "change_availability"):
            batch.select_families(data, rows, 2)

    def test_empty_eligible_is_explicit_not_promoted(self):
        data, rows = selection_fixture()
        for row in rows:
            row["groups"][0]["status"] = "no_complete_spelled_paths"
            row["eligible_change_group_ids"] = []
        result = batch.select_families(data, rows, 5)
        self.assertEqual(result["selected_contexts"], [])
        self.assertEqual(len(result["family_decisions"]), 4)
        self.assertTrue(all(r["status"] == "no_paths_prepared_change_context" for r in result["family_decisions"]))

    def test_output_and_limits_checked_before_loading(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "output/old"
            old.mkdir(parents=True)
            with patch.object(batch, "ROOT", root), \
                 patch.object(functional, "load_inputs", side_effect=AssertionError("must not read")):
                for path in (root, old, root / "output/child/nested"):
                    with self.assertRaises(ValueError):
                        batch.run("missing", "missing", "missing", path)
                for field in ("family_limit", "pair_budget", "overlay_pair_budget", "functional_budget", "request_budget"):
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        batch.run("missing", "missing", "missing", root / "output/new", **{field: True})

    def test_whole_group_result_denominator_and_identity_checked(self):
        groups = [{"group_id": "change:1", "status": "paths_prepared", "planned_paths": 2}]
        result = {"group_id": "change:1", "original_status": "paths_prepared", "planned_paths": 2,
                  "comparisons": []}
        with self.assertRaisesRegex(ValueError, "group_result_denominator_loss"):
            batch._bundles({}, groups, [], [])
        for field, value in (("group_id", "wrong"), ("original_status", "fake"), ("planned_paths", 1)):
            changed = {**result, field: value}
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "group_identity_loss"):
                batch._bundles({}, groups, [changed], [])
        self.assertEqual(batch._bundles({}, groups, [result], []), [])


class FrozenBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for module in (batch, functional, meaning, lineage):
            self.stack.enter_context(patch.object(module, "ROOT", self.root))
        # Historical synthetic parents predate corpus/collection fields.
        # Keep their protected bytes intact; only adapt fixture identity here.
        # Real missing/cross-collection identity rejection is tested above.
        def synthetic_identity(data, pair):
            entry = data["packages"][pair]["source"]["manifest_entry"]
            return entry["work_family_id"], ("synthetic", "fixture")
        self.stack.enter_context(patch.object(batch, "_identity", side_effect=synthetic_identity))
        with redirect_stdout(io.StringIO()):
            lineage.run(self.data["baseline"], self.data["output"])
            self.data["lineage"] = self.data["output"]
            self.data["meaning"] = self.root / "output/meaning"
            meaning.run(self.data["baseline"], self.data["lineage"], self.data["meaning"])
        self.output = self.root / "output/family-batch"

    def execute(self, **kwargs):
        # This historical toy score has only a hold group. Exercise the batch
        # storage/guard/error path on that intact context with an explicit test
        # scheduling adapter. Production change selection is tested separately.
        original_selection = batch.select_families
        def synthetic_scope(data, rows, family_limit):
            result = original_selection(data, rows, family_limit)
            first = rows[0]
            family = first["work_family_id"]
            result["selected_contexts"] = [first["context_key"]]
            result["selected_family_order"] = [family]
            result["selection_policy"] = "synthetic_runtime_fixture_scope_not_production_selection"
            for decision in result["family_decisions"]:
                if decision["work_family_id"] == family:
                    decision["status"] = "scheduled"
                    decision["first_eligible_context"] = deepcopy(first)
            return result
        with redirect_stdout(io.StringIO()), patch.object(batch, "select_families", side_effect=synthetic_scope):
            return batch.run(self.data["baseline"], self.data["lineage"], self.data["meaning"], self.output, **kwargs)

    def test_complete_declared_denominators_scope_snapshots_and_old_bytes(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.execute()
        self.assertTrue(report["batch_complete"], report)
        self.assertFalse(report["cohort_complete"])
        self.assertNotIn("complete", report)
        self.assertFalse(report["musical_accuracy_measured"])
        self.assertIsNone(report["selected"])
        plan = read_json(self.output / "batch-plan.json")
        selected = {tuple(k) for k in plan["selection"]["selected_contexts"]}
        index = read_json(self.output / "context-index.json")
        units = read_json(self.output / "unit-index.json")
        self.assertEqual({tuple(r["context_key"]) for r in index}, selected)
        expected_units = {(tuple(r["context_key"]), tuple(r["lane"]))
                          for r in plan["declared_units"] if tuple(r["context_key"]) in selected}
        self.assertEqual({(tuple(r["context_key"]), tuple(r["lane"])) for r in units}, expected_units)
        for row in index:
            case = read_gzip(row["artifact"])
            self.assertEqual([g["group_id"] for g in case["groups"]],
                             [g["group_id"] for g in case["context"]["groups"]])
            self.assertEqual(len(case["lane_inventory"]), len(case["observation"]["raw_lanes"]))
            self.assertTrue(all(Path(r["artifact"]).is_file() for r in case["score_snapshots"].values()))
            self.assertFalse(case["training_eligible"])
            self.assertFalse(case["generation_ready"])
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        for path, expected in report["artifact_hashes"].items():
            self.assertEqual(sha(path), expected)
        self.assertEqual({str(p.resolve()) for p in self.output.rglob("*") if p.is_file()},
                         set(report["artifact_hashes"]) | {str(self.output / "batch-report.json")})

    def test_no_old_engine_geometry_or_source_annotation_producer(self):
        with patch("musicanote_harness.harmony_factorized_voice_paths.factorize", side_effect=AssertionError("geometry")), \
             patch("musicanote_harness.harmony_breadth_trial.analyze_sample", side_effect=AssertionError("old engine")), \
             patch("musicanote_harness.harmony_voice_paths.observe", side_effect=AssertionError("legacy")):
            report = self.execute()
        self.assertTrue(report["batch_complete"])

    def test_rehashed_parent_catalog_group_cannot_choose_faster_case(self):
        index = read_json(self.data["meaning"] / "context-index.json")
        path = Path(index[0]["artifact"])
        saved = read_gzip(path)
        saved["groups"][0]["status"] = "fake_ready"
        write_gzip(path, saved)
        index[0]["sha256"] = sha(path)
        write_json(self.data["meaning"] / "context-index.json", index)
        report_path = self.data["meaning"] / "report.json"
        report = read_json(report_path)
        report["artifact_hashes"] = {p: sha(p) for p in report["artifact_hashes"]}
        write_json(report_path, report)
        with self.assertRaisesRegex(ValueError, "catalog_fresh_group"):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_catalog_observation_and_audit_refs_are_bound_for_deferred_rows(self):
        data = functional.load_inputs(self.data["baseline"], self.data["lineage"], self.data["meaning"])
        key = next(iter(data["contexts"]))
        original_load = lineage._load
        for field, prefix in (("observation_ref", "mfco_"), ("audit_ref", "msla_"), ("target_span", None)):
            original_index = deepcopy(data["meaning_contexts"][key])
            def changed_ref(path, hashes, **kwargs):
                value = original_load(path, hashes, **kwargs)
                if Path(path).parent == data["meaning"] / "contexts":
                    value = deepcopy(value)
                    view = {k: v for k, v in value["view"].items() if k not in ("record_id", "record_sha256")}
                    if prefix is None:
                        start, end = common.span_bounds(view["context_span"])
                        view[field] = {"start": common.q((start + end) / 2), "end": common.q(end)}
                    else:
                        view[field] = {"record_id": prefix + "0" * 24, "record_sha256": "0" * 64}
                    value["view"] = common.seal(view, common.PREFIX)
                    stored = original_load(data["current"][key]["artifact"], hashes, compressed=True)["bundle"]
                    value["groups"] = meaning.path_groups(value["view"], stored["stages"]["lattice"],
                                                          path_budget=data["meaning_plan"]["path_budget"])
                    data["meaning_contexts"][key]["view_ref"] = common.ref(value["view"])
                return value
            with self.subTest(field=field), patch.object(lineage, "_load", side_effect=changed_ref), \
                 self.assertRaisesRegex(ValueError, "catalog_fresh_group"):
                batch.catalog(data)
            data["meaning_contexts"][key] = original_index

    def test_one_group_error_preserves_scope_and_report_incomplete(self):
        original = functional.evaluate_group
        calls = []
        def fail_first(*args, **kwargs):
            calls.append(args[1]["group_id"])
            if len(calls) == 1:
                raise ValueError("deliberate group failure")
            return original(*args, **kwargs)
        with patch.object(functional, "evaluate_group", side_effect=fail_first):
            report = self.execute()
        self.assertTrue(calls, "fixture must select a prepared change context")
        self.assertFalse(report["batch_complete"])
        self.assertFalse(report["cohort_complete"])
        self.assertEqual(report["summary"]["calculation_failures"], 1)
        self.assertTrue(report["selected_denominators_complete"])
        index = read_json(self.output / "context-index.json")
        first = read_gzip(index[0]["artifact"])
        self.assertEqual(first["groups"][0]["status"], "calculation_failure")
        self.assertEqual(len(first["groups"]), len(first["context"]["groups"]))

    def test_changed_generated_artifact_blocks_success(self):
        original = meaning._save
        changed = []
        def alter_after_registration(output, relative, value, artifacts, **kwargs):
            path = original(output, relative, value, artifacts, **kwargs)
            if relative == "unit-index.json":
                path.write_bytes(path.read_bytes() + b" ")
                changed.append(str(path))
            return path
        with patch.object(meaning, "_save", side_effect=alter_after_registration):
            report = self.execute()
        self.assertFalse(report["batch_complete"])
        self.assertEqual(report["changed_artifacts"], changed)

    def test_selected_source_view_replay_is_required(self):
        original = functional._context
        def stale_selected(*args, **kwargs):
            value = deepcopy(original(*args, **kwargs))
            value["view"]["record_sha256"] = "0" * 64
            return value
        with patch.object(functional, "_context", side_effect=stale_selected):
            with self.assertRaisesRegex(ValueError, "selected_view_changed"):
                self.execute()
        self.assertFalse((self.output / "batch-report.json").exists())


if __name__ == "__main__":
    unittest.main()
