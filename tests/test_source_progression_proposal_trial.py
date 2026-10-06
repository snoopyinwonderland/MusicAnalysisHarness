"""Storage-only proposal runner tests, not musical or native authority tests.

Existing storage TestCases are composed as temporary archive factories, never
inherited. Their tiny full XML IR is genuine; saved origins/policies/proposals
in this file are explicitly mock archival declarations, not inferred harmony.
"""
from copy import deepcopy
import gzip
from itertools import product
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import source_progression_proposal_trial as trial
import test_native_progression_policy_trial as fixtures


class SavedSourceProposalStorageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SavedPolicyStorageTests()
        factory = fixtures.fixtures.SavedContrastStorageTests
        prior_setup = factory.setUp
        def setup_archive(instance):
            prior_setup(instance)
            self.extend_temporary_panels(instance)
        with patch.object(factory, "setUp", setup_archive):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.parent = self.fixture.output
        self.parent_report, _ = self.fixture.run_mock()
        self.assertTrue(self.parent_report["computation_integrity_passed"])
        self.parent_plan = self.read(self.parent / "run-plan.json")
        self.parent_rows = self.read(self.parent / "context-index.json")
        self.output = self.root / "output/source-proposals"
        self.code = self.root / "new-source-proposal-fixture.txt"
        self.code.write_text("mock storage producer, no musical authority", encoding="utf-8")
        old_codes = [self.fixture.fixture.producer, self.fixture.code]
        for item in (patch.object(trial, "ROOT", self.root),
                patch.object(trial, "_code_paths", return_value=[*old_codes, self.code]),
                patch.object(trial, "_new_code_paths", return_value={self.code})):
            item.start()
            self.addCleanup(item.stop)

    def read(self, path):
        path = Path(path)
        with (gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")) as stream:
            return json.load(stream)

    def write(self, path, value):
        fixtures.fixtures.write(Path(path), value)

    def reseal(self, value):
        return fixtures.fixtures.seal({k: v for k, v in value.items()
            if k not in ("record_id", "record_sha256")}, trial.engine.PREFIX)

    def refresh_parent(self):
        for name, body in (("context-index.json", self.parent_rows), ("run-plan.json", self.parent_plan)):
            path = self.parent / name
            self.write(path, body)
            self.parent_report["artifact_hashes"][str(path)] = trial.old._file_sha(path)
        self.write(self.parent / "report.json", self.parent_report)

    def shape(self, assumption, eligible=False):
        return {"assumption": deepcopy(assumption), "source_shape_compatible": True if eligible else False,
            "target_shape_compatible": True if eligible else None, "shape_request_eligible": eligible,
            "function_kind_under_key": "applied" if eligible else "unassessed",
            "key_projection": {"target_coordinate": None, "chromatic_source_members": None,
                "unassessed_reasons": ["storage_fixture_no_inference"],
                "chromatic_is_not_applied_function_proof": True, "scale_form_is_not_motion_direction_rule": True},
            "blockers": [] if eligible else ["storage_fixture_no_inference"]}

    def extend_temporary_panels(self, archive):
        """Enrich only this test's fake archive before predecessor mocks run."""
        names = ("whole_hold", "nearest_half_two_slots", "nearest_thirds_three_slots")
        for row in archive.rows:
            info = row["panel"]
            panel = self.read(info["artifact"])
            lattice = self.read(row["native_lattice"]["artifact"])
            origins = {o["record_id"]: o for entry in lattice["catalog_inventory"] for o in entry["origins"]}
            points = sorted({trial.f(o["span"][field]) for o in origins.values() for field in ("start", "end")})
            intervals = [{"point_indices": [points.index(trial.f(entry["origins"][0]["span"][field]))
                for field in ("start", "end")], "proposals": [{"origin_ref": trial.sealed._ref(o)} for o in entry["origins"]]}
                for entry in lattice["catalog_inventory"]]
            panel["intervals"] = sorted(intervals, key=lambda i: i["point_indices"])
            seeds, seen = [], set()
            for selector in panel["selectors"]:
                ids = tuple(selector["origin_ids"])
                if ids in seen:
                    continue
                seen.add(ids)
                kind = names[len(ids) - 1]
                lane = sum(s["partition_kind"] == kind for s in seeds)
                seeds.append({"partition_kind": kind, "proposal_lane": lane, "origin_ids": list(ids)})
            panel["complete_proposal_paths"] = seeds
            panel["partitions"] = []
            for name in names:
                seed = next(s for s in seeds if s["partition_kind"] == name)
                selected = [origins[oid] for oid in seed["origin_ids"]]
                indices = [0, *[points.index(trial.f(o["span"]["end"])) for o in selected]]
                panel["partitions"].append({"partition_kind": name, "point_indices": indices})
            panel = fixtures.fixtures.seal({k: v for k, v in panel.items()
                if k not in ("record_id", "record_sha256")}, trial.engine.prior.PREFIX)
            self.write(info["artifact"], panel)
            info.update(record_ref=trial.sealed._ref(panel), sha256=trial.old._file_sha(info["artifact"]))
            archive.artifacts[info["artifact"]] = info["sha256"]
        archive.refresh()

    def proposal_fixture(self, scope, lattice, panel, *, work_budget, max_paths, max_selectors, additive=False):
        """Closed finite mock declarations, never call the actual proposal engine."""
        controls = deepcopy(panel["selectors"])
        held = work_budget == 0 or max_paths == 0 or max_selectors < len(controls)
        origins = {o["record_id"]: o for entry in lattice["catalog_inventory"] for o in entry["origins"]}
        points = sorted({trial.f(o["span"][field]) for o in origins.values() for field in ("start", "end")})
        intervals, paths, partitions, requests, aliases, additional = [], [], [], [], [], []
        q = trial.parent.parent.parent.q
        if not held:
            for entry in sorted(lattice["catalog_inventory"], key=lambda row:
                    (trial.f(row["origins"][0]["span"]["start"]), trial.f(row["origins"][0]["span"]["end"]))):
                span = deepcopy(entry["origins"][0]["span"])
                indices = [points.index(trial.f(span["start"])), points.index(trial.f(span["end"]))]
                proposals = [{"origin_ref": trial.sealed._ref(o), "eligible": True, "reasons": [],
                    "missing_guarded_member_spellings": 0, "guarded_pooled_member_note_time": q(4),
                    "guarded_root_note_time": q(4), "raw_note_time_by_support": {
                        "member": q(4), "nonmember": q(0), "unknown": q(0), "unsupported": q(0)},
                    "member_sound_evidence": [], "root": deepcopy(o["root"]), "members": deepcopy(o["members"]),
                    "source_ornaments_used": False, "source_annotation_labels_used": False,
                    "simultaneous_core_certified": False, "selected": None, "confidence": None} for o in entry["origins"]]
                intervals.append({"catalog_id": "fixture-catalog-" + str(indices), "point_indices": indices, "span": span,
                    "native_origins": len(proposals), "eligible_origins": len(proposals), "rejected_origins": 0,
                    "rejection_reason_occurrences": {}, "distinct_eligible_spelling_signatures": len(proposals),
                    "bucket_representatives": [{"bucket": {"kind": "nonordinary_or_unassessed", "quality": None,
                        "spelled_root": None, "classification_is_harmony_confirmation": False},
                        "eligible_origins": len(proposals), "representative_ref": proposals[0]["origin_ref"],
                        "distinct_ordered_signatures": len(proposals), "omitted_bucket_representative_origins": len(proposals) - 1}],
                    "proposals": proposals, "proposal_count": len(proposals), "omitted_eligible_origins": 0})
            names = ("whole_hold", "nearest_half_two_slots", "nearest_thirds_three_slots")
            by_pair = {tuple(i["point_indices"]): i for i in intervals}
            for old_partition in panel["partitions"]:
                name, indices = old_partition["partition_kind"], old_partition["point_indices"]
                pairs = list(zip(indices, indices[1:]))
                proposed = {}
                for seed in (p for p in panel["complete_proposal_paths"] if p["partition_kind"] == name):
                    ids = tuple(seed["origin_ids"])
                    proposed.setdefault(ids, []).append({"kind": "retained_seed", "proposal_lane": seed["proposal_lane"]})
                    for slot, pair in enumerate(pairs):
                        for proposal in by_pair[tuple(pair)]["proposals"]:
                            changed = list(ids)
                            changed[slot] = proposal["origin_ref"]["record_id"]
                            proposed.setdefault(tuple(changed), []).append({"kind": "single_slot_substitution",
                                "proposal_lane": seed["proposal_lane"], "slot": slot})
                for ids, provenance in proposed.items():
                    paths.append({"partition_kind": name, "point_indices": indices,
                        "origin_ids": list(ids), "origin_refs": [trial.sealed._ref(origins[oid]) for oid in ids],
                        "proposal_provenance": provenance})
                cartesian = 1
                for pair in pairs:
                    cartesian *= by_pair[tuple(pair)]["eligible_origins"]
                partitions.append({"partition_kind": name, "point_indices": indices, "proposed_paths": len(proposed),
                    "eligible_cartesian_origin_paths": cartesian,
                    "omitted_eligible_cartesian_origin_paths": cartesian - len(proposed),
                    "status": "computed_bounded_mixed_path_sample"})
            keys = sorted(lattice["keys"], key=lambda k: k["record_id"])
            for path_index, path in enumerate(paths):
                for key in keys:
                    cuts = []
                    for left, right in zip(path["origin_refs"], path["origin_refs"][1:]):
                        shapes = [self.shape({"family": family, "quality": quality},
                            additive and family == "V7" and quality == "m")
                            for family in trial.engine.kernels.FAMILIES for quality in ("M", "m")]
                        options = [None, *[s["assumption"] for s in shapes if s["shape_request_eligible"]]]
                        left_origin, right_origin = origins[left["record_id"]], origins[right["record_id"]]
                        cuts.append({"source_origin_ref": left, "target_origin_ref": right,
                            "same_spelling_signature": left_origin["root"] == right_origin["root"] and left_origin["members"] == right_origin["members"],
                            "checked_shapes": shapes, "request_options": options,
                            "resolution_support": None, "secondary_support": None,
                            "boundary_support": None, "same_completion_ref": None})
                    count = 1
                    for cut in cuts:
                        count *= len(cut["request_options"])
                    requests.append({"path_index": path_index, "key_ref": trial.sealed._ref(key),
                        "cuts": cuts, "complete_vector_count": count})
            seen = {trial.digest(selector): {"kind": "retained_control", "index": i} for i, selector in enumerate(controls)}
            for request_index, request in enumerate(requests):
                path = paths[request["path_index"]]
                for vector in product(*(c["request_options"] for c in request["cuts"])):
                    selector = {"origin_ids": deepcopy(path["origin_ids"]), "key_id": request["key_ref"]["record_id"],
                        "transition_assumptions": deepcopy(list(vector))}
                    fingerprint = trial.digest(selector)
                    if fingerprint in seen:
                        aliases.append({"request_index": request_index, "selector_fingerprint": fingerprint,
                            "existing_selector": deepcopy(seen[fingerprint])})
                    else:
                        seen[fingerprint] = {"kind": "additional", "index": len(additional)}
                        additional.append(selector)
        summary = {key: None for key in trial.engine.SUMMARY_KEYS}
        summary.update(requested_intervals=6, retained_control_selectors=len(controls))
        if not held:
            summary.update(assessed_origin_occurrences=12, eligible_origin_occurrences=12,
                rejected_origin_occurrences=0, proposal_origin_occurrences=12, omitted_eligible_origin_occurrences=0,
                complete_proposal_paths=len(paths), eligible_cartesian_origin_paths=14,
                omitted_eligible_cartesian_origin_paths=14 - len(paths), additional_selectors=len(additional),
                total_selectors=len(controls) + len(additional),
                shape_request_occurrences=sum(len(c["request_options"]) - 1 for r in requests for c in r["cuts"]))
        return self.reseal({"version": trial.engine.VERSION, "source_authority": trial.engine.AUTHORITY,
            "contract": trial.engine._contract(), "rules": trial.engine.RULES, "scope_ref": trial.sealed._ref(scope),
            "lattice_ref": trial.sealed._ref(lattice), "prior_panel_ref": trial.sealed._ref(panel),
            "binding": deepcopy(scope["binding"]), "analysis_span": deepcopy(scope["analysis_span"]),
            "logical_universe": deepcopy(lattice["universe"]),
            "resource_limits": {"work_budget": work_budget, "max_paths": max_paths, "max_selectors": max_selectors},
            "query_plan": {"input_visit_work": 100, "source_scan_and_sort_work": 100,
                "path_shape_vector_work": None if held else 100, "planned_work": None if held else 300,
                "semantics": "whole_request_logical_visit_allowance_not_CPU_RSS_accuracy"},
            "intervals": intervals, "partitions": partitions, "complete_proposal_paths": paths,
            "shape_request_groups": requests, "selector_aliases": aliases, "retained_control_selectors": controls,
            "additional_selectors": additional, "selectors": controls + additional, "summary": summary,
            "status": "whole_source_proposal_hold" if held else "computed_source_progression_proposals_not_evaluated",
            "reasons": ["storage_fixture_whole_hold"] if held else [], "flags": deepcopy(trial.engine.FLAGS),
            "selected": None, "rank": None, "confidence": None,
            "native_replay_status": "not_executed_requires_fresh_native_session", "limitations": ["mock storage only"]})

    def run_mock(self, **limits):
        with patch.object(trial.engine, "propose", side_effect=self.proposal_fixture) as proposer:
            report = trial.run(self.parent, self.output, **limits)
        return report, proposer

    def case_result(self, additive=False):
        case = trial.load_inputs(self.parent)["cases"][0]
        result = self.proposal_fixture(case["scope"], case["lattice"], case["panel"],
            **{key: trial.SETTINGS[key] for key in ("work_budget", "max_paths", "max_selectors")}, additive=additive)
        return case, result

    def invalid(self, result, case):
        with self.assertRaises((ValueError, KeyError, TypeError)):
            trial._validate_result(self.reseal(result), case, trial._settings({}))

    def test_exclusive_direct_output_and_all_closed_caps_before_loader(self):
        self.output.mkdir()
        with patch.object(trial, "load_inputs") as loader:
            for target in (self.output, self.root, self.root / "output/nested/new"):
                with self.assertRaises(ValueError):
                    trial.run(self.parent, target)
            self.output.rmdir()
            for key in trial.SETTINGS:
                for value in (True, -1, 1.5, "2", None):
                    with self.assertRaises(ValueError):
                        trial.run(self.parent, self.output, **{key: value})
            with self.assertRaises(ValueError):
                trial.run(self.parent, self.output, undeclared=1)
            loader.assert_not_called()

    def test_all_registered_origins_two_sources_four_controls_no_producers(self):
        forbidden = AssertionError("archival loader must not replay any producer")
        with patch.object(trial.parent, "load_inputs", side_effect=forbidden), \
                patch.object(trial.parent.policy, "evaluate", side_effect=forbidden), \
                patch.object(trial.parent.parent.engine, "compare", side_effect=forbidden), \
                patch.object(trial.parent.parent.parent.native, "prepare_lattice", side_effect=forbidden), \
                patch.object(trial.engine.kernels, "_function", side_effect=forbidden), \
                patch.object(trial.engine, "propose", side_effect=forbidden):
            data = trial.load_inputs(self.parent)
        self.assertEqual(len(data["cases"]), 2)
        self.assertEqual([len(c["parent_policy_rows"]) for c in data["cases"]], [2, 2])
        self.assertEqual([len(c["completion_controls"]) for c in data["cases"]], [2, 2])
        self.assertEqual([c["native_counts"]["native_origins"] for c in data["cases"]], [12, 12])
        self.assertEqual([len(i) for _, i in data["inventories"]], [7, 7, 148])
        self.assertFalse(self.output.exists())

    def test_whole_admission_caps_no_output_no_proposal_prefix(self):
        for limits in ({"max_file_bytes": 0}, {"max_decoded_file_bytes": 0}, {"max_total_decoded_bytes": 0},
                {"max_contexts": 1}, {"max_catalogs": 5}, {"max_origins": 11}):
            with patch.object(trial.engine, "propose") as proposer:
                with self.assertRaises(ValueError):
                    trial.run(self.parent, self.output, **limits)
                proposer.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_changed_registered_hash_and_extra_parent_file_are_rejected(self):
        path = Path(self.parent_rows[0]["policy"]["artifact"])
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaises(ValueError):
            trial.load_inputs(self.parent)
        (self.parent / "unregistered.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inventory"):
            trial.load_inputs(self.parent)

    def test_creation_conflict_and_retroactive_child_inventory_are_rejected(self):
        path = str(self.fixture.fixture.producer)
        self.parent_plan["code"][path] = "0" * 64
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "conflicting"):
            trial.load_inputs(self.parent)
        self.parent_plan["code"][path] = trial.old._file_sha(path)
        self.parent_plan["code"][str(self.code)] = trial.old._file_sha(self.code)
        self.refresh_parent()
        with self.assertRaisesRegex(ValueError, "historical"):
            trial.load_inputs(self.parent)

    def test_strict_duplicate_nonfinite_JSON_and_whole_gzip_cap(self):
        reader = trial.parent.parent.BoundedReader(trial._settings({}))
        path = self.root / "malformed.json"
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(ValueError):
                reader.read(path)
        path = self.root / "large.json.gz"
        self.write(path, {"value": "x" * 2000})
        with self.assertRaisesRegex(ValueError, "decoded"):
            trial.parent.parent.BoundedReader(trial._settings({"max_decoded_file_bytes": 20})).read(path)

    def test_parent_four_rows_must_preserve_source_snapshots_and_order(self):
        self.parent_rows[0]["original_source_files"] = []
        self.refresh_parent()
        with self.assertRaises(ValueError):
            trial.load_inputs(self.parent)

    def test_mock_dedup_once_per_source_six_files_all_four_replay_jobs(self):
        report, proposer = self.run_mock()
        self.assertTrue(report["computation_integrity_passed"], report["failures"])
        self.assertEqual(proposer.call_count, 2)
        self.assertEqual(report["registered_policy_completion_rows"], 4)
        self.assertEqual(report["parent_policy_summary"]["submitted_entries"], 200)
        self.assertEqual(report["admitted_native_inventory"]["native_origins"], 24)
        self.assertEqual(report["summary"]["retained_control_selectors"], 100)
        self.assertEqual(report["summary"]["additional_selectors"], 80)
        self.assertEqual(report["summary"]["omitted_eligible_cartesian_origin_paths"], 0)
        self.assertTrue(report["submitted_source_proposal_computation_complete"])
        self.assertEqual(len([p for p in self.output.rglob("*") if p.is_file()]), 6)
        replay = self.read(self.output / "native-replay-plan.json")
        self.assertEqual(replay["planned_completion_requests"], 4)
        self.assertEqual(replay["planned_selector_occurrences"], 360)
        self.assertEqual(replay["native_evaluations_performed"], 0)
        self.assertEqual(replay["fresh_native_sessions_prepared"], 0)
        self.assertTrue(all(j["execution_status"] == "not_executed_requires_fresh_native_session" for j in replay["jobs"]))
        self.assertTrue(all(report[k] is False for k in trial.POLICY_FALSE))
        self.assertEqual(report["denominators"], self.parent_report["denominators"])

    def test_mock_all_additive_shape_vectors_retained_not_native_evaluated(self):
        def additive(*args, **kwargs):
            return self.proposal_fixture(*args, **kwargs, additive=True)
        with patch.object(trial.engine, "propose", side_effect=additive):
            report = trial.run(self.parent, self.output)
        self.assertTrue(report["computation_integrity_passed"], report["failures"])
        self.assertEqual(report["summary"]["additional_selectors"], 360)
        self.assertEqual(report["summary"]["total_selectors"], 460)
        self.assertEqual(report["native_replay_planned_selector_occurrences"], 920)
        self.assertEqual(report["native_replay_evaluations_performed"], 0)
        for row in self.read(self.output / "context-index.json"):
            value = self.read(row["proposal"]["artifact"])
            self.assertEqual(len(value["retained_control_selectors"]), 50)
            self.assertEqual(len(value["additional_selectors"]), 180)
            self.assertEqual(len({s["key_id"] for s in value["selectors"]}), 5)

    def test_whole_hold_known_controls_unknown_new_counts_no_new_prefix(self):
        report, proposer = self.run_mock(work_budget=0)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertFalse(report["submitted_source_proposal_computation_complete"])
        self.assertEqual(proposer.call_count, 2)
        self.assertEqual(report["whole_source_proposal_holds"], 2)
        self.assertEqual(report["summary"]["retained_control_selectors"], 100)
        self.assertIsNone(report["summary"]["additional_selectors"])
        self.assertIsNone(report["native_replay_planned_selector_occurrences"])
        replay = self.read(self.output / "native-replay-plan.json")
        self.assertEqual(replay["retained_control_selector_occurrences"], 200)
        self.assertTrue(all(j["selector_field_pointer"] is None for j in replay["jobs"]))
        self.assertTrue(all(j["execution_status"] == "blocked_whole_source_proposal_hold" for j in replay["jobs"]))

    def test_mixed_whole_hold_is_unknown_not_zero_or_successful_prefix(self):
        calls = 0
        def mixed(*args, **kwargs):
            nonlocal calls
            calls += 1
            value = self.proposal_fixture(*args, **kwargs)
            if calls == 1:
                value = self.proposal_fixture(*args, **{**kwargs, "work_budget": 0})
                value["resource_limits"]["work_budget"] = kwargs["work_budget"]
                value = self.reseal(value)
            return value
        with patch.object(trial.engine, "propose", side_effect=mixed):
            report = trial.run(self.parent, self.output)
        self.assertTrue(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"]["total_selectors"])
        self.assertEqual(report["known_summary_subtotal"]["total_selectors"], 90)
        self.assertEqual(report["unknown_summary_context_occurrences"]["total_selectors"], 1)
        self.assertFalse(report["submitted_source_proposal_computation_complete"])

    def test_closed_summary_costs_boolean_and_unknown_computed_rejected(self):
        case, value = self.case_result()
        for field in trial.engine.SUMMARY_KEYS:
            damaged = deepcopy(value)
            damaged["summary"][field] = True
            self.invalid(damaged, case)
        for field in trial.PLAN_COUNT_FIELDS | trial.PLAN_NULLABLE_FIELDS:
            for bad in (True, None, -1, 0.5, "1"):
                damaged = deepcopy(value)
                damaged["query_plan"][field] = bad
                self.invalid(damaged, case)
        damaged = deepcopy(value)
        damaged["query_plan"]["planned_work"] = 200
        self.invalid(damaged, case)

    def test_ordered_controls_duplicates_foreign_origin_and_winner_rejected(self):
        case, value = self.case_result(additive=True)
        for mutate in (lambda r: r["retained_control_selectors"].reverse(),
                lambda r: r["additional_selectors"].append(deepcopy(r["additional_selectors"][0])),
                lambda r: r["selectors"][0]["origin_ids"].__setitem__(0, "foreign-origin"),
                lambda r: r.__setitem__("selected", 0),
                lambda r: r["flags"].__setitem__("winning_harmony_selected", True)):
            damaged = deepcopy(value)
            mutate(damaged)
            self.invalid(damaged, case)

    def test_shape_declarations_required_ordered_tristate_and_conjunction(self):
        case, value = self.case_result(additive=True)
        first = next(i for i, r in enumerate(value["shape_request_groups"]) if r["cuts"])
        for mutate in (lambda c: c.pop("checked_shapes"),
                lambda c: c["checked_shapes"].reverse(),
                lambda c: c["checked_shapes"][0].__setitem__("source_shape_compatible", 1),
                lambda c: c["checked_shapes"][0].__setitem__("shape_request_eligible", True),
                lambda c: c.__setitem__("resolution_support", True),
                lambda c: c["checked_shapes"][0]["key_projection"].__setitem__("chromatic_is_not_applied_function_proof", False)):
            damaged = deepcopy(value)
            mutate(damaged["shape_request_groups"][first]["cuts"][0])
            self.invalid(damaged, case)

    def test_alias_partition_bucket_and_interval_provenance_joins(self):
        case, value = self.case_result()
        for mutate in (lambda r: r["selector_aliases"][0]["existing_selector"].__setitem__("index", 49),
                lambda r: r["partitions"][0].__setitem__("eligible_cartesian_origin_paths", 999),
                lambda r: r["intervals"][0]["proposals"][0]["origin_ref"].__setitem__("record_sha256", "0" * 64),
                lambda r: r["intervals"][0]["bucket_representatives"][0]["bucket"].__setitem__("classification_is_harmony_confirmation", True),
                lambda r: r["complete_proposal_paths"][0].__setitem__("point_indices", [0, 1])):
            damaged = deepcopy(value)
            mutate(damaged)
            self.invalid(damaged, case)

    def test_returned_limits_ordered_intervals_and_retained_seed_paths_required(self):
        case, value = self.case_result()
        for mutate in (lambda r: r["resource_limits"].__setitem__("max_paths", True),
                lambda r: r["intervals"].reverse(),
                lambda r: r["complete_proposal_paths"].pop(0),
                lambda r: r["shape_request_groups"][0].__setitem__("complete_vector_count", 2)):
            damaged = deepcopy(value)
            mutate(damaged)
            self.invalid(damaged, case)

    def test_resealed_seed_lane_or_multislot_relabel_provenance_rejected(self):
        case, value = self.case_result()
        damaged = deepcopy(value)
        damaged["complete_proposal_paths"][0]["proposal_provenance"][0]["proposal_lane"] = 1
        self.invalid(damaged, case)
        damaged = deepcopy(value)
        path = next(p for p in damaged["complete_proposal_paths"] if len(p["origin_ids"]) == 3
            and p["proposal_provenance"][0]["kind"] == "retained_seed")
        original = path["origin_ids"][:]
        origins = {o["record_id"]: o for entry in case["lattice"]["catalog_inventory"] for o in entry["origins"]}
        for slot in (0, 1):
            path["origin_ids"][slot] = next(oid for oid, origin in origins.items()
                if origin["span"] == origins[original[slot]]["span"] and oid != original[slot])
        path["origin_refs"] = [trial.sealed._ref(origins[oid]) for oid in path["origin_ids"]]
        self.invalid(damaged, case)
        damaged = deepcopy(value)
        damaged["partitions"][1]["point_indices"] = [0, 1, 4]
        self.invalid(damaged, case)

    def test_resealed_false_literal_spelling_signature_rejected(self):
        case, value = self.case_result()
        cut = next(r["cuts"][0] for r in value["shape_request_groups"] if r["cuts"])
        cut["same_spelling_signature"] = not cut["same_spelling_signature"]
        self.invalid(value, case)

    def test_member_sound_refs_original_notes_full_span_and_exact_overlap_join(self):
        case, value = self.case_result()
        sound = case["scope"]["sound_facts"][0]
        proposal = value["intervals"][0]["proposals"][0]
        clip = value["intervals"][0]["span"]
        proposal["member_sound_evidence"] = [{"sound_ref": sound["sound_ref"],
            "source_note_refs": deepcopy(sound["source_note_refs"]), "full_sound_span": deepcopy(sound["span"]),
            "observed_span": deepcopy(clip)}]
        value = self.reseal(value)
        trial._validate_result(value, case, trial._settings({}))
        for mutate in (lambda e: e.__setitem__("sound_ref", "foreign-sound"),
                lambda e: e.__setitem__("source_note_refs", ["foreign-note"]),
                lambda e: e.__setitem__("full_sound_span", deepcopy(clip)),
                lambda e: e.__setitem__("observed_span", deepcopy(sound["span"]))):
            damaged = deepcopy(value)
            mutate(damaged["intervals"][0]["proposals"][0]["member_sound_evidence"][0])
            self.invalid(damaged, case)

    def test_validation_does_not_call_function_or_proposal_semantic_replay(self):
        case, value = self.case_result(additive=True)
        forbidden = AssertionError("storage joins must not execute music predicates")
        with patch.object(trial.engine, "propose", side_effect=forbidden), \
                patch.object(trial.engine.kernels, "_function", side_effect=forbidden), \
                patch.object(trial.engine, "_evidence", side_effect=forbidden), \
                patch.object(trial.engine, "_bucket", side_effect=forbidden):
            trial._validate_result(value, case, trial._settings({}))

    def test_input_mutation_cannot_be_saved_as_success_all_control_rows_retained(self):
        def mutate(scope, *args, **kwargs):
            value = self.proposal_fixture(scope, *args, **kwargs)
            scope["unexpected_mutation"] = True
            return value
        with patch.object(trial.engine, "propose", side_effect=mutate):
            report = trial.run(self.parent, self.output)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(len(report["failures"]), 2)
        rows = self.read(self.output / "context-index.json")
        self.assertEqual(sum(len(r["parent_policy_rows"]) for r in rows), 4)
        replay = self.read(self.output / "native-replay-plan.json")
        self.assertEqual(len(replay["jobs"]), 4)
        self.assertIsNone(replay["planned_selector_occurrences"])

    def test_creation_source_mutation_is_protected_until_report(self):
        def mutate(*args, **kwargs):
            value = self.proposal_fixture(*args, **kwargs)
            self.code.write_text("changed producer", encoding="utf-8")
            return value
        with patch.object(trial.engine, "propose", side_effect=mutate):
            report = trial.run(self.parent, self.output)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertFalse(report["inputs_and_code_unchanged"])
        self.assertIsNone(report["summary"])

    def test_output_byte_cap_never_saves_partial_proposal_or_drops_controls(self):
        report, proposer = self.run_mock(max_output_record_bytes=0)
        self.assertEqual(proposer.call_count, 2)
        self.assertFalse(report["computation_integrity_passed"])
        self.assertIsNone(report["summary"])
        self.assertEqual(len(report["failures"]), 2)
        self.assertEqual(len([p for p in self.output.rglob("*") if p.is_file()]), 4)
        replay = self.read(self.output / "native-replay-plan.json")
        self.assertEqual(replay["retained_control_selector_occurrences"], 200)
        self.assertIsNone(replay["planned_selector_occurrences"])


if __name__ == "__main__":
    unittest.main()
