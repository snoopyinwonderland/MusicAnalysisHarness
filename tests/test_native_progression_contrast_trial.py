"""Storage-only contrast runner tests, not live native or music accuracy.

Tiny MusicXML IR is genuine; archived lattice/path/role fixtures are manually
sealed storage data. The contrast calculation is mocked in runner tests.
No old producer, native preparation, role inference or corpus cold is run.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
import gzip
from itertools import combinations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import native_progression_contrast_trial as trial
from test_musical_role_evidence import event, make_ir


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if path.suffix == ".gz":
        with gzip.open(path, "wb") as stream:
            stream.write(raw)
    else:
        path.write_bytes(raw)


def seal(body, prefix):
    return trial.sealed._seal(body, prefix)


class SavedContrastStorageTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.parent = self.root / "output/phase25"
        self.parent.mkdir(parents=True)
        self.output = self.root / "output/contrast"
        self.producer = self.root / "producer-fixture.txt"
        self.producer.write_text("storage fixture, not live native authority", encoding="utf-8")
        self.inputs, self.artifacts, self.rows = {}, {}, []
        self.contexts = [["fixture:sonata", 0, "context-one"], ["fixture:quartet", 0, "context-two"]]
        for position, context_key in enumerate(self.contexts):
            directory = self.root / ("IR" + str(position))
            directory.mkdir()
            ir = make_ir(directory, [[event("C4" if position == 0 else "D4", 0, 4)]])
            ir_path = directory / "canonical_music_ir.json"
            write(ir_path, ir)
            self.inputs[str(ir_path)] = trial.old._file_sha(ir_path)
            sounds = [{"sound_ref": sound["sounding_event_id"], "source_note_refs": sound["source_note_ids"],
                "pitch": sound["pitch"], "span": sound["span"],
                "lane": [ir["note_events"][0]["part_id"], ir["note_events"][0]["voice_id"]],
                "attack_note_ref": sound["attack_note_id"], "tie_chain_ref": sound["tie_chain_id"]}
                for sound in ir["sounding_events"]]
            scope = seal({"status": "ready_expanded_scope", "binding": trial.old.expanded._binding(ir),
                "analysis_span": trial.old.sealed._span(0, 4), "sound_facts": sounds,
                "raw_lanes": [{"part_id": sounds[0]["lane"][0], "voice_id": sounds[0]["lane"][1]}],
                "context_sound_inventory_complete": True}, trial.old.expanded.PREFIX)
            scope_path = self.root / "scopes" / (scope["record_id"] + ".json.gz")
            write(scope_path, scope)
            self.inputs[str(scope_path)] = trial.old._file_sha(scope_path)
            scope_info = self.info(scope_path, scope)
            spans = [trial.old.sealed._span(0, 4), trial.old.sealed._span(0, 2), trial.old.sealed._span(2, 4),
                trial.old.sealed._span(0, Fraction(4, 3)), trial.old.sealed._span(Fraction(4, 3), Fraction(8, 3)),
                trial.old.sealed._span(Fraction(8, 3), 4)]
            catalog = [{"origins": [seal({"span": span, "root": {"step": step, "alter": trial.parent.q(0)},
                "members": [{"step": step, "alter": trial.parent.q(0)}], "blockers": []}, "fmilorigin_")
                for step in ("C", "D")]} for span in spans]
            keys = [seal({"status": "fixture_registered_key", "index": i}, "newkey_") for i in range(5)]
            lattice = seal({"status": "ready_native_interval_lattice", "reasons": [],
                "resource_limits": deepcopy(trial.parent.native.DEFAULTS), "scope_ref": trial.sealed._ref(scope),
                "binding": scope["binding"], "analysis_span": scope["analysis_span"], "catalog_inventory": catalog,
                "keys": keys, "universe": {"fixture_not_live_issued": 123}}, trial.parent.native.PREFIX)
            lattice_info = self.save_record("lattices", lattice)
            origins = {o["record_id"]: o for row in catalog for o in row["origins"]}
            selectors = []
            for indices in ((0,), (1, 2), (3, 4, 5)):
                for variant in range(2):
                    for key in keys:
                        for declared in range(1 if len(indices) == 1 else 2):
                            selectors.append({"origin_ids": [catalog[i]["origins"][variant]["record_id"] for i in indices],
                                "key_id": key["record_id"], "transition_assumptions": [None if not declared else
                                    {"family": "V7", "quality": "M"}] * (len(indices) - 1)})
            panel = seal({"version": trial.parent.panel_engine.VERSION, "policy": trial.parent.panel_engine.POLICY,
                "scope_ref": trial.sealed._ref(scope), "lattice_ref": trial.sealed._ref(lattice),
                "logical_universe": lattice["universe"], "native_request": {k: lattice[k] for k in ("status", "reasons", "resource_limits")},
                "resource_limits": {k: trial.parent.SETTINGS[k] for k in ("max_selectors", "selection_work_budget")},
                "query_plan": {"selector_upper_bound": 50}, "selectors": selectors,
                "summary": {"native_interval_catalogs": 6, "native_origins": 12, "requested_intervals": 6,
                    "complete_proposal_paths": 6, "submitted_selectors": 50, "planned_selector_upper_bound": 50,
                    "unsubmitted_selector_bound": 0, "evaluated_origin_occurrences": 12,
                    "eligible_origin_occurrences": 12, "rejected_origin_occurrences": 0},
                "status": "computed_source_evidence_panel_not_selected", "selected": None, "rank": None,
                "confidence": None, "flags": {"selected": False}}, trial.parent.panel_engine.PREFIX)
            panel_info = self.save_record("panels", panel)
            completions = []
            for completion in range(2):
                request_links = [] if not completion else [["fixture-source-z", "fixture-target-z"], ["fixture-source-a", "fixture-target-a"]]
                bundle = seal({"status": "complete_all_lane_witness", "scope_ref": trial.sealed._ref(scope),
                    "lattice_ref": trial.sealed._ref(lattice), "binding": scope["binding"],
                    "required_links": sorted(request_links)}, trial.parent.native.BUNDLE_PREFIX)
                bundle_info, batches = self.save_record("bundles", bundle), []
                for batch_index, selected in enumerate(trial.parent._batches(selectors)):
                    paths, role_paths = [], []
                    for selector in selected:
                        chosen = [origins[o] for o in selector["origin_ids"]]
                        identity = seal({"scope_ref": trial.sealed._ref(scope), "lattice_ref": trial.sealed._ref(lattice),
                            "origin_refs": [trial.sealed._ref(o) for o in chosen], "partition": [o["span"] for o in chosen],
                            "key_ref": trial.sealed._ref(next(k for k in keys if k["record_id"] == selector["key_id"])),
                            "bundle_ref": trial.sealed._ref(bundle), "transition_assumptions": selector["transition_assumptions"]}, "fmiltuple_")
                        path = seal({**{k: deepcopy(identity[k]) for k in ("scope_ref", "lattice_ref", "origin_refs", "partition", "key_ref", "bundle_ref")},
                            "logical_tuple": identity, "whole_path_account": {"raw_total_note_time_quarters": trial.parent.q(4)},
                            "status": "computed_complete_native_path_not_selected"}, "fmilpath_")
                        paths.append(path)
                        role_paths.append(seal({**{k: deepcopy(path[k]) for k in ("origin_refs", "partition", "key_ref", "bundle_ref")},
                            "native_path_ref": trial.sealed._ref(path), "logical_tuple_ref": trial.sealed._ref(identity),
                            "transition_assumptions": selector["transition_assumptions"], "raw_account_pointer": {
                                "parent_path_ref": trial.sealed._ref(path), "field": "whole_path_account", "sha256": trial.digest(path["whole_path_account"])},
                            "clauses": [], "status": "assessed_same_completion", "account": {"raw_time_conserved": True,
                                "conditional_explanation_note_time_quarters": trial.parent.q(0), "explained_intervals_by_sound": []}}, "fmnrolepath_"))
                    native_summary = {"planned_selectors": len(selected), "computed_selectors": len(selected)}
                    comparison = seal({"scope_ref": trial.sealed._ref(scope), "lattice_ref": trial.sealed._ref(lattice),
                        "bundle_ref": trial.sealed._ref(bundle), "selectors": selected, "paths": paths,
                        "resource_limits": {}, "summary": native_summary, "query_plan": {"planned_query_work": 100},
                        "status": "computed_native_multi_slot_comparison_not_selected", "reasons": []}, trial.parent.native.COMPARISON_PREFIX)
                    role_summary = {name: 0 for name in trial.old.ROLE_SUMMARY_FIELDS if name != "role_clause_occurrences"}
                    role_summary.update(planned_paths=len(selected), native_computed_paths=len(selected), computed_paths=len(selected),
                        planned_clause_upper_bound=100, role_clause_occurrences={})
                    explanation = seal({"native_comparison_ref": trial.sealed._ref(comparison),
                        **{k: deepcopy(comparison[k]) for k in ("scope_ref", "lattice_ref", "bundle_ref")},
                        "native_request": {k: deepcopy(comparison[k]) for k in ("selectors", "resource_limits", "status", "reasons", "summary", "query_plan")},
                        "paths": role_paths, "summary": role_summary, "query_plan": {"clause_upper_bound": 100},
                        "status": "computed_native_role_explanations_not_selected", "reasons": []}, trial.parent.roles.PREFIX)
                    batches.append({"batch_index": batch_index, "selector_start": batch_index * 3,
                        "selector_end_exclusive": batch_index * 3 + len(selected), "selectors": selected,
                        "comparison": self.save_record("comparisons", comparison), "explanation": self.save_record("explanations", explanation),
                        "native_summary": comparison["summary"], "role_summary": explanation["summary"],
                        "native_query_plan": comparison["query_plan"], "role_query_plan": explanation["query_plan"],
                        "status": explanation["status"], "reasons": []})
                completions.append({"kind": "all_no_link_control" if not completion else "bounded_same_raw_lane_greedy_technical_probe",
                    "bundle": bundle_info, "required_links": request_links, "planned_batches": 17,
                    "saved_batches": 17, "batches": batches})
            self.rows.append({"context_key": context_key, "full_IR": {"artifact": str(ir_path), "sha256": trial.old._file_sha(ir_path),
                "ir_document_id": ir["ir_document_id"], "ir_content_sha256": trial.digest(ir), "binding_match": True,
                "registered_full_IR_not_projection": True}, "scope": scope_info, "native_lattice": lattice_info, "panel": panel_info,
                "panel_summary": panel["summary"], "panel_query_plan": panel["query_plan"], "selected_selectors": selectors,
                "batch_count_per_completion": 17, "completion_batches": completions, "counts": {},
                "planned_batch_upper_bound_per_completion": 17, "unsubmitted_selector_upper_bound_per_completion": 0,
                "actual_completion_requests": 2, "status": "source_evidence_probe_saved_not_selected", "error": None})
        denoms = {"declared_contexts": 6, "declared_original_raw_lanes": 6, "registered_context_pool": 5,
            "selected_contexts": 2, "selected_original_raw_lanes": 2, "unexecuted_declared_contexts": 4,
            "unexecuted_declared_original_raw_lanes": 4}
        self.plan = {k: False for k in trial.PLAN_KEYS}
        self.plan.update(version=trial.parent.VERSION, settings=deepcopy(trial.parent.SETTINGS), inputs=self.inputs,
            code={str(self.producer): trial.old._file_sha(self.producer)}, denominators=denoms,
            source_authority=trial.parent.AUTHORITY, selection_policy=trial.parent.SELECTION_POLICY,
            selector_batch_size=3, all_batches_for_both_completions_planned=True, selected=None,
            selected_contexts=self.contexts, source_size_manifest=[], max_contexts=2)
        self.report = {k: False for k in trial.REPORT_KEYS}
        self.report.update(version=trial.parent.VERSION, status="source_evidence_probe_complete_not_selected",
            computation_integrity_passed=True, inputs_and_code_unchanged=True, artifacts_unchanged=True,
            submitted_role_calculation_complete=True, changed_inputs_or_code=[], changed_artifacts=[], failures=[],
            artifact_hashes=self.artifacts, selected=None, fresh_native_preparations=2, denominators=denoms)
        self.refresh()

    def info(self, path, record):
        return {"artifact": str(path), "sha256": trial.old._file_sha(path),
            "record_ref": trial.sealed._ref(record), "status": record["status"]}

    def save_record(self, folder, record):
        path = self.parent / folder / (record["record_id"] + ".json.gz")
        write(path, record)
        self.artifacts[str(path)] = trial.old._file_sha(path)
        return self.info(path, record)

    def refresh(self):
        for name, body in (("run-plan.json", self.plan), ("context-index.json", self.rows), ("case-samples.json", {"fixture": "not read"})):
            path = self.parent / name
            write(path, body)
            self.artifacts[str(path)] = trial.old._file_sha(path)
        write(self.parent / "report.json", self.report)

    def load(self, **limits):
        return trial.load_inputs(self.parent, **limits)

    def result(self, scope, lattice, entries, *, bundles, max_pairs, work_budget):
        groups = defaultdict(list)
        for entry in entries:
            path = entry["native_path"]
            groups[trial.digest(path["key_ref"])].append(entry)
        paired = [(left, right) for group in groups.values() for left, right in combinations(group, 2)]
        held = len(paired) > max_pairs or work_budget == 0
        pairs = [] if held else [{"left_path_ref": trial.sealed._ref(left["native_path"]),
            "right_path_ref": trial.sealed._ref(right["native_path"]),
            "left_role_path_ref": trial.sealed._ref(left["role_path"]), "right_role_path_ref": trial.sealed._ref(right["role_path"]),
            "key_ref": left["native_path"]["key_ref"], "bundle_ref": left["native_path"]["bundle_ref"],
            "comparison_kind": "candidate_only", "alias_control": False, "raw_time_conserved": True,
            "selected": None, "rank": None, "confidence": None}
            for left, right in paired]
        facets = [] if held else [{"native_path_ref": trial.sealed._ref(entry["native_path"]),
            "role_path_ref": trial.sealed._ref(entry["role_path"]), "comparison_ref": entry["comparison_ref"],
            "explanation_ref": entry["explanation_ref"]} for entry in entries]
        summary = {k: 0 for k in trial.SUMMARY_FIELDS if k != "pair_kind_counts"}
        summary.update(submitted_entries=len(entries), planned_same_key_same_bundle_pairs=len(paired), computed_pairs=len(pairs),
            withheld_pairs=len(paired) - len(pairs), candidate_only_pairs=len(pairs), raw_time_conserved_entries=len(facets),
            pair_kind_counts={"candidate_only": len(pairs)} if pairs else {})
        return seal({"version": trial.engine.VERSION, "source_authority": trial.AUTHORITY,
            "scope_ref": trial.sealed._ref(scope), "lattice_ref": trial.sealed._ref(lattice),
            "binding": scope["binding"], "analysis_span": scope["analysis_span"], "logical_universe": lattice["universe"],
            "resource_limits": {"max_pairs": max_pairs, "work_budget": work_budget},
            "submitted_entry_refs": [{"native_path_ref": trial.sealed._ref(e["native_path"]),
                "role_path_ref": trial.sealed._ref(e["role_path"]), "comparison_ref": e["comparison_ref"], "explanation_ref": e["explanation_ref"]} for e in entries],
            "facets": facets, "pairs": pairs, "summary": summary,
            "query_plan": {"planned_pairs": len(paired), "planned_work": 1000, "entry_count": len(entries)},
            "status": "whole_saved_contrast_hold" if held else "computed_saved_progression_contrasts_not_selected",
            "reasons": ["mock_whole_hold"] if held else [], "selected": None, "rank": None, "confidence": None,
            "flags": {k: False for k in trial.RESULT_FLAGS}}, trial.engine.PREFIX)

    def run_mock(self, **limits):
        with patch.object(trial, "ROOT", self.root), patch.object(trial, "_code_paths", return_value=[self.producer]), \
                patch.object(trial.engine, "compare", side_effect=self.result) as compare:
            report = trial.run(self.parent, self.output, **limits)
        return report, compare

    def test_append_only_and_strict_limits_precede_every_parent_read(self):
        self.output.mkdir()
        with patch.object(trial, "ROOT", self.root), patch.object(trial, "load_inputs") as load:
            for output in (self.output, self.root, self.root / "output/nested/new"):
                with self.assertRaises(ValueError):
                    trial.run("missing", output)
            for name in trial.SETTINGS:
                for value in (True, None, -1, 1.5, "1"):
                    with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                        trial.run("missing", self.root / "output/new", **{name: value})
            with self.assertRaises(ValueError):
                trial.run("missing", self.root / "output/new", foreign_limit=1)
            load.assert_not_called()

    def test_exact_saved_all_batches_all_keys_without_live_producers(self):
        with patch.object(trial.parent.native, "prepare_lattice", side_effect=AssertionError("live native")), \
                patch.object(trial.parent.native, "compare_prepared", side_effect=AssertionError("native replay")), \
                patch.object(trial.parent.roles, "prepare_explanations", side_effect=AssertionError("role replay")):
            data = self.load()
        self.assertEqual(len(data["inventory"]), 148)
        self.assertEqual(len(data["contexts"]), 2)
        for case in data["contexts"]:
            self.assertEqual(len(case["jobs"]), 2)
            for job in case["jobs"]:
                self.assertEqual(len(job["entries"]), 50)
                self.assertEqual(len(job["saved_batch_refs"]), 17)
                self.assertEqual(len({e["native_path"]["key_ref"]["record_id"] for e in job["entries"]}), 5)
        self.assertFalse(self.output.exists())
        self.assertEqual(trial.old._guard(data["hashes"]), [])

    def test_changed_artifact_and_extra_parent_inventory_rejected(self):
        path = Path(self.rows[0]["completion_batches"][0]["batches"][0]["comparison"]["artifact"])
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "SHA256_changed"):
            self.load()
        write(self.parent / "extra.json", {})
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.load()

    def test_creation_code_input_hash_collision_never_overwritten(self):
        self.plan["inputs"][str(self.producer)] = "0" * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, "conflicting_registered_SHA256"):
            self.load()

    def test_canonical_bundle_edge_order_preserves_original_greedy_request(self):
        data = self.load()
        job = data["contexts"][0]["jobs"][1]
        request = self.rows[0]["completion_batches"][1]["required_links"]
        self.assertNotEqual(job["bundle"]["required_links"], request)
        self.assertEqual(trial._edge_signature(job["bundle"]["required_links"]), trial._edge_signature(request))

    def test_duplicate_saved_required_edge_is_not_collapsed_into_set(self):
        links = self.rows[0]["completion_batches"][1]["required_links"]
        links.append(deepcopy(links[0]))
        self.refresh()
        with self.assertRaisesRegex(ValueError, "duplicate_saved_required_link"):
            self.load()

    def test_raw_JSON_duplicates_nonfinite_and_decompressed_caps(self):
        path = self.root / "raw.json"
        reader = trial.BoundedReader(trial.SETTINGS)
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                reader.read(path)
        path = self.root / "compressed.json.gz"
        write(path, {"large": "a" * 1000})
        with self.assertRaisesRegex(ValueError, "decoded_bytes"):
            trial.BoundedReader({**trial.SETTINGS, "max_decoded_file_bytes": 100}).read(path)

    def test_read_caps_hold_whole_before_any_output_or_contrast(self):
        for limits in ({"max_file_bytes": 0}, {"max_decoded_file_bytes": 0}, {"max_total_decoded_bytes": 0}, {"max_entries_per_completion": 49}):
            with patch.object(trial, "ROOT", self.root), patch.object(trial.engine, "compare") as compare:
                with self.subTest(limits=limits), self.assertRaisesRegex(ValueError, "whole_saved_read_hold"):
                    trial.run(self.parent, self.output, **limits)
                compare.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_selector_order_is_exact_cross_batch_not_truncated_or_filtered(self):
        self.rows[0]["completion_batches"][0]["batches"][0]["selectors"] = list(reversed(
            self.rows[0]["completion_batches"][0]["batches"][0]["selectors"]))
        self.refresh()
        with self.assertRaisesRegex(ValueError, "selector_order"):
            self.load()

    def test_resealed_foreign_role_account_pointer_is_not_accepted(self):
        info = self.rows[0]["completion_batches"][0]["batches"][0]["explanation"]
        explanation = trial.old._read(info["artifact"])
        role = explanation["paths"][0]
        role["raw_account_pointer"]["sha256"] = "0" * 64
        explanation["paths"][0] = seal({k: v for k, v in role.items() if k not in ("record_id", "record_sha256")}, "fmnrolepath_")
        explanation = seal({k: v for k, v in explanation.items() if k not in ("record_id", "record_sha256")}, trial.parent.roles.PREFIX)
        write(Path(info["artifact"]), explanation)
        info.update(self.info(Path(info["artifact"]), explanation))
        self.artifacts[info["artifact"]] = info["sha256"]
        self.refresh()
        with self.assertRaisesRegex(ValueError, "relationship"):
            self.load()

    def test_full_IR_content_binding_not_just_filename(self):
        self.rows[0]["full_IR"]["ir_content_sha256"] = "0" * 64
        self.refresh()
        with self.assertRaisesRegex(ValueError, "IR_content_binding"):
            self.load()

    def test_mock_four_whole_cross_batch_groups_and_protected_hashes(self):
        protected = {str(p): trial.old._file_sha(p) for p in self.parent.rglob("*") if p.is_file()}
        report, compare = self.run_mock()
        self.assertTrue(report["computation_integrity_passed"])
        self.assertEqual(compare.call_count, 4)
        self.assertEqual(report["saved_completion_groups"], 4)
        self.assertEqual(report["computed_completion_groups"], 4)
        self.assertEqual(report["summary"]["submitted_entries"], 200)
        self.assertEqual(report["summary"]["computed_pairs"], 900)
        self.assertEqual(report["summary"]["withheld_pairs"], 0)
        self.assertEqual(report["fresh_native_preparations"], 0)
        self.assertEqual(report["denominators"], self.report["denominators"])
        self.assertTrue(all(report[k] is False for k in trial.POLICY_FALSE))
        self.assertEqual(trial.old._guard({**protected, **report["artifact_hashes"]}), [])
        self.assertEqual(len(trial.old._inventory(self.output, report["artifact_hashes"], self.output / "report.json")), 7)
        for call in compare.call_args_list:
            self.assertEqual(len(call.args[2]), 50)
            self.assertEqual(len(call.kwargs["bundles"]), 1)
            self.assertEqual(call.kwargs["max_pairs"], 2000)
            self.assertEqual(call.kwargs["work_budget"], 2000000)

    def test_mock_pair_budget_whole_holds_preserve_all_four_requests(self):
        report, compare = self.run_mock(max_pairs=0)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertEqual(compare.call_count, 4)
        self.assertEqual(report["whole_contrast_holds"], 4)
        self.assertEqual(report["summary"]["planned_same_key_same_bundle_pairs"], 900)
        self.assertEqual(report["summary"]["computed_pairs"], 0)
        self.assertEqual(report["summary"]["withheld_pairs"], 900)
        self.assertEqual(report["summary"]["pair_kind_counts"], {})

    def test_mock_work_budget_whole_hold_no_prefix(self):
        report, compare = self.run_mock(work_budget=0)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertEqual(report["whole_contrast_holds"], 4)
        self.assertEqual(report["summary"]["submitted_entries"], 200)
        self.assertEqual(report["summary"]["raw_time_conserved_entries"], 0)
        self.assertEqual(compare.call_count, 4)

    def test_mock_malformed_typed_summary_cannot_create_success_counts(self):
        genuine_mock = self.result
        def malformed(*args, **kwargs):
            record = genuine_mock(*args, **kwargs)
            record["summary"]["computed_pairs"] = True
            return seal({k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}, trial.engine.PREFIX)
        with patch.object(self, "result", side_effect=malformed):
            report, compare = self.run_mock()
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(len(report["failures"]), 4)
        self.assertEqual(compare.call_count, 4)

    def test_mock_parent_source_mutation_invalidates_stored_probe(self):
        mock = self.result
        def changing(*args, **kwargs):
            record = mock(*args, **kwargs)
            self.producer.write_text("changed during storage-only mock", encoding="utf-8")
            return record
        with patch.object(self, "result", side_effect=changing):
            report, _ = self.run_mock()
        self.assertFalse(report["computation_integrity_passed"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIsNone(report["summary"])

    def test_mock_resealed_pair_ref_digest_mismatch_is_not_accepted(self):
        mock = self.result
        def wrong_ref(*args, **kwargs):
            record = mock(*args, **kwargs)
            record["pairs"][0]["left_role_path_ref"]["record_sha256"] = "0" * 64
            return seal({k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}, trial.engine.PREFIX)
        with patch.object(self, "result", side_effect=wrong_ref):
            report, _ = self.run_mock()
        self.assertFalse(report["computation_integrity_passed"])
        self.assertEqual(len(report["failures"]), 4)
        self.assertIsNone(report["summary"])

    def test_mock_output_byte_budget_never_saves_partial_contrast(self):
        report, compare = self.run_mock(max_output_record_bytes=1)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(len(report["failures"]), 4)
        self.assertFalse((self.output / "contrasts").exists())
        self.assertEqual(compare.call_count, 4)


if __name__ == "__main__":
    unittest.main()
