"""Real formal-IR fixtures; conditional motion is never a musical verdict."""
from copy import deepcopy
from fractions import Fraction
from dataclasses import replace
import gc
import json
from tempfile import TemporaryDirectory
import unittest
import weakref
from unittest.mock import patch

from musicanote_harness import factor_functional_resolution as resolution
from musicanote_harness import factor_functional_overlay as overlay
from musicanote_harness import factor_musical_rules as nct
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_factorized_voice_paths as factors
from test_factor_musical_view import make_view, span, provenance
from test_factor_functional_overlay import harmony, key_segment, reseal
from test_musical_role_evidence import make_ir, event


class FunctionalResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        resolution._COMPILATION_CACHE.clear()
        resolution._COMPILATION_CACHE_BYTES = 0
        resolution._PREPARED_BUNDLES.clear()

    def fixture(self, lanes=None, *, keys=None, segments=None):
        lanes = lanes or [[event("B4", 0, 2), event("C5", 2, 2)]]
        padded = []
        for lane in lanes:
            end = max(r["onset"] + r["duration"] for r in lane)
            padded.append([*lane, *([event(None, end, 4 - end)] if end < 4 else [])])
        ir = make_ir(self.temp.name, padded)
        view = make_view(ir, span())
        path = common.make_path(view, segments or [harmony("v", 0, 2, "G", "Mm7"), harmony("i", 2, 4, "C", "M")], provenance())
        key = overlay.make_key_track(view, keys or [key_segment()], provenance())
        functions = overlay.compile_functions(view, path, key)
        graphs = [factors.factorize(ir, span(), [lane["part_id"], lane["voice_id"]]) for lane in view["raw_lanes"]]
        return ir, view, path, key, functions, graphs

    def compile(self, fixture, **kwargs):
        return resolution.compile_resolutions(*fixture[1:], **kwargs)

    def row(self, fixture, compiled, role="leading_tone", source=None):
        function = next(r for r in fixture[4]["rows"] if (r["source_segment_ref"], r["family"], r["target_quality"]) == ("v", "V7", "M"))
        return next(r for r in compiled["rules"] if r["function_ref"] == function["function_id"] and r["critical_role"] == role and (source is None or r["source_sound_ref"] == source))

    def request(self, compiled, row):
        return {"compiled_ref": common.ref(compiled), "resolution_id": row["resolution_id"]}

    def bundle(self, fixture, required=(), *, paths=None, graph_indices=None):
        view, path, graphs = fixture[1], fixture[2], fixture[5]
        entries = []
        for graph in graphs if graph_indices is None else [graphs[i] for i in graph_indices]:
            ids = {s["sounding_event_id"] for s in graph["events"]}
            links = [p for p in required if p[0] in ids]
            query = factors.query(graph, required_links=links)
            entries.append({"graph": graph, "query": query, "witness": factors.materialize_witness(graph, query)})
        return resolution.make_bundle(view, path if paths is None else paths, entries)

    def test_leading_tone_exact_identity_motion_and_full_fresh_replay(self):
        fx = self.fixture(); before = deepcopy(fx)
        compiled = self.compile(fx); row = self.row(fx, compiled)
        self.assertEqual(row["status"], "conditional_resolution_shape")
        obs = row["observations"][0]
        self.assertEqual(obs["motions"][0]["diatonic_steps"], 1)
        self.assertEqual(obs["motions"][0]["semitones"], common.q(1))
        self.assertEqual(obs["target_onset"], common.q(2))
        bundle = self.bundle(fx, obs["required_links"])
        assessed = resolution.evaluate_resolutions(*fx[1:], bundle)
        target = next(a for a in assessed["assessments"] if a["resolution_ref"] == row["resolution_id"])
        self.assertEqual(target["status"], "conditional_resolution_under_bundle")
        self.assertTrue(resolution.validate_resolutions(*fx[1:], compiled))
        self.assertTrue(resolution.validate_bundle(fx[1], fx[2], fx[5], bundle))
        self.assertTrue(resolution.validate_evaluation(*fx[1:], bundle, assessed))
        self.assertEqual(fx, before)
        self.assertFalse(assessed["function_confirmed"])

    def test_no_link_is_not_global_absence(self):
        fx = self.fixture(); compiled = self.compile(fx); row = self.row(fx, compiled)
        assessed = resolution.evaluate_resolutions(*fx[1:], self.bundle(fx))
        self.assertEqual(next(a["status"] for a in assessed["assessments"] if a["resolution_ref"] == row["resolution_id"]), "not_satisfied_under_this_bundle_not_global_absence")

    def test_octave_drop_is_not_leading_tone_resolution(self):
        fx = self.fixture([[event("B4", 0, 2), event("C4", 2, 2)]])
        row = self.row(fx, self.compile(fx))
        self.assertEqual(row["status"], "withheld")
        self.assertFalse(row["observations"][0]["actual_motion_matches_expected"])
        self.assertEqual(row["observations"][0]["motions"][0]["semitones"], common.q(-11))

    def test_seventh_downward_one_and_two_semitone_steps(self):
        for destination, expected in (("E4", -1), ("Eb4", -2)):
            fx = self.fixture([[event("F4", 0, 2), event(destination, 2, 2)]],
                              segments=[harmony("v", 0, 2, "G", "Mm7"), harmony("i", 2, 4, "C", "M" if destination == "E4" else "m")])
            compiled = self.compile(fx)
            function = next(r for r in fx[4]["rows"] if r["source_segment_ref"] == "v" and r["family"] == "V7" and r["target_quality"] == ("M" if destination == "E4" else "m"))
            row = next(r for r in compiled["rules"] if r["function_ref"] == function["function_id"] and r["critical_role"] == "seventh")
            self.assertEqual(row["status"], "conditional_resolution_shape")
            self.assertEqual(row["observations"][0]["motions"][0]["semitones"], common.q(expected))

    def test_same_pitch_delayed_carry_requires_every_edge(self):
        fx = self.fixture([[event("B4", 0, 2), event("B4", 2, 1), event("C5", 3, 1)]])
        compiled = self.compile(fx); row = self.row(fx, compiled); links = row["alternatives"][0]["required_links"]
        self.assertEqual(len(links), 2)
        observation = row["observations"][0]
        self.assertEqual(observation["harmonic_change_time"], common.q(2))
        self.assertEqual(observation["source_terminal_time"], common.q(2))
        self.assertEqual(observation["resolution_predecessor_terminal_time"], common.q(3))
        self.assertEqual(observation["resolution_predecessor_sound_ref"], observation["sound_refs"][-2])
        short = self.bundle(fx, links[1:]); complete = self.bundle(fx, links)
        a = resolution.evaluate_resolutions(*fx[1:], short)
        b = resolution.evaluate_resolutions(*fx[1:], complete)
        states = lambda r: next(x["status"] for x in r["assessments"] if x["resolution_ref"] == row["resolution_id"])
        self.assertEqual(states(a), "not_satisfied_under_this_bundle_not_global_absence")
        self.assertEqual(states(b), "conditional_resolution_under_bundle")

    def test_held_same_sound_boundary_carry_not_fake_reattack(self):
        fx = self.fixture([[event("B4", 0, 3), event("C5", 3, 1)]])
        row = self.row(fx, self.compile(fx))
        self.assertEqual(row["status"], "conditional_resolution_shape")
        self.assertEqual(row["observations"][0]["target_onset"], common.q(3))
        self.assertEqual(row["observations"][0]["harmonic_change_time"], common.q(2))
        self.assertEqual(row["observations"][0]["source_terminal_time"], common.q(3))
        self.assertEqual(row["observations"][0]["resolution_predecessor_terminal_time"], common.q(3))
        self.assertEqual(row["observations"][0]["source_terminal_sound_ref"], row["source_sound_ref"])
        self.assertEqual(len(row["alternatives"][0]["required_links"]), 1)

    def test_target_union_or_other_lane_held_tonic_is_not_destination_identity(self):
        fx = self.fixture([[event("B4", 0, 2), event(None, 2, 2)], [event("C5", 1, 3)]])
        row = self.row(fx, self.compile(fx))
        self.assertEqual(row["status"], "withheld")
        self.assertEqual(row["alternatives"], [])
        self.assertIsNone(row["observations"][0]["target_onset"])

    def test_broken_target_triad_missing_at_boundary_does_not_erase_motion(self):
        fx = self.fixture([[event("B4", 0, 2), event("C5", 2, 1), event("E5", 3, Fraction(1, 2)), event("G5", Fraction(7, 2), Fraction(1, 2))]])
        row = self.row(fx, self.compile(fx))
        self.assertEqual(row["status"], "conditional_resolution_shape")
        self.assertEqual(row["observations"][0]["sound_refs"][-1], next(s["sound_id"] for s in fx[1]["sounds"] if s["pitch"]["step"] == "C"))
        self.assertTrue(row["prerequisites"]["target_members_are_explicit_path_assumptions_not_observed_boundary_chord"])

    def test_unknown_key_preserves_motion_without_function_certification(self):
        fx = self.fixture(keys=[key_segment(tonic=None, mode="unknown", form="unknown")])
        row = self.row(fx, self.compile(fx))
        self.assertEqual(row["status"], "conditional_resolution_shape")
        self.assertEqual(row["prerequisites"]["function_snapshot"]["function_kind"], "unassessed")

    def test_source_clock_and_written_pitch_blockers_survive(self):
        fx = self.fixture(); ir = fx[0]
        first = next(n for n in ir["note_events"] if n["written_pitch"]["step"] == "B")
        first["tie_role"] = "stop"
        view = make_view(ir, span()); path = common.make_path(view, fx[2]["segments"], provenance())
        key = overlay.make_key_track(view, [key_segment()], provenance()); functions = overlay.compile_functions(view, path, key)
        graphs = [factors.factorize(ir, span(), g["lane"]) for g in fx[5]]
        changed = (ir, view, path, key, functions, graphs)
        row = self.row(changed, self.compile(changed))
        self.assertEqual(row["status"], "withheld")
        self.assertTrue(any(x.startswith("source_clock_not_passed") for x in row["blockers"]))
        self.assertTrue(row["observations"][0]["actual_motion_matches_expected"])

    def test_missing_lane_is_unknown_not_false(self):
        fx = self.fixture(); missing = (*fx[:5], [])
        row = self.row(missing, self.compile(missing))
        self.assertIn("missing_raw_lane_graph", row["blockers"])
        bundle = resolution.make_bundle(fx[1], fx[2], [])
        self.assertTrue(bundle["missing_lanes"])
        assessed = resolution.evaluate_resolutions(*missing[1:], bundle)
        self.assertTrue(all(a["status"] == "withheld" for a in assessed["assessments"]))

    def test_whole_candidate_and_chain_budget_no_partial_success(self):
        fx = self.fixture([[event("B4", 0, 2), event("B4", 2, 1), event("C5", 3, 1)]])
        full = self.compile(fx)
        held = self.compile(fx, max_candidates=int(full["total_candidates"]) - 1)
        self.assertEqual(held["status"], "candidate_budget_abstention")
        self.assertEqual(held["rules"], [])
        held = self.compile(fx, max_chain_edges=1)
        self.assertEqual(held["status"], "chain_budget_abstention")
        self.assertEqual(held["rules"], [])
        self.assertEqual(held["total_candidates"], full["total_candidates"])

    def test_two_leading_tone_doublings_compete_for_one_target(self):
        fx = self.fixture([[event(["B4", "B4"], 0, 2), event("C5", 2, 2)]])
        compiled = self.compile(fx)
        func = self.row(fx, compiled)["function_ref"]
        rows = [r for r in compiled["rules"] if r["function_ref"] == func and r["critical_role"] == "leading_tone"]
        self.assertEqual(len(rows), 2)
        for row in rows:
            single = resolution.solve_joint(*fx[1:], [self.request(compiled, row)])
            self.assertEqual(single["status"], "joint_possible")
        combined = resolution.solve_joint(*fx[1:], [self.request(compiled, r) for r in rows])
        self.assertEqual(combined["status"], "incompatible_joint_constraints")
        self.assertTrue(resolution.validate_joint(*fx[1:], combined))
        self.assertIsNone(combined["branches"][0]["completion_bundle"])

    def test_or_targets_remain_alternatives_and_whole_branch_budget(self):
        fx = self.fixture([[event("B4", 0, 2), event(["C5", "C5"], 2, 2)]])
        compiled = self.compile(fx); row = self.row(fx, compiled)
        self.assertEqual(len(row["alternatives"]), 2)
        solution = resolution.solve_joint(*fx[1:], [self.request(compiled, row)])
        self.assertEqual(len(solution["branches"]), 2)
        self.assertFalse(solution["branch_counts_may_be_summed"])
        self.assertTrue(all(len(b["queries"]) == 1 for b in solution["branches"]))
        held = resolution.solve_joint(*fx[1:], [self.request(compiled, row)], branch_budget=1)
        self.assertEqual(held["status"], "unassessed")
        self.assertEqual(held["branches"], [])

    def test_joint_canonical_nct_conflicts_with_leading_target_not_arbitrary_rule(self):
        # F-A-C and B-C chains share the C destination under the explicit path.
        fx = self.fixture([[event(["B4", "G4"], 0, 1), event(["B4", "A4"], 1, 1), event("C5", 2, 2)]],
                          segments=[harmony("v", 0, 2, "G", "Mm7"), harmony("i", 2, 4, "C", "M")])
        compiled = self.compile(fx); row = self.row(fx, compiled)
        # Canonical neighbor/passing evidence is graph/path dependent; a forged
        # caller row must never become a music-validated NCT request.
        record = nct.compile_rules(fx[1], fx[2], fx[5][0])
        bad = deepcopy(record); bad["rules"][0]["status"] = "conditional_shape"
        bad["rules"][0]["blockers"] = []
        bad = reseal(bad, "fmcr_")
        req = {"graph_ref": common.ref(fx[5][0]), "compiled": bad, "rule_id": bad["rules"][0]["rule_id"]}
        with self.assertRaises(ValueError):
            resolution.solve_joint(*fx[1:], [self.request(compiled, row)], [req])

    def test_actual_passing_and_leading_resolution_compete_for_same_source(self):
        fx = self.fixture([[event("B4", 0, 2), event(["C5", "A4"], 2, 1), event("G4", 3, 1)]])
        compiled = self.compile(fx); row = self.row(fx, compiled)
        record = nct.compile_rules(fx[1], fx[2], fx[5][0])
        passing = next(r for r in record["rules"] if r["family"] == "passing" and r["status"] == "conditional_shape")
        req = {"graph_ref": common.ref(fx[5][0]), "compiled": record, "rule_id": passing["rule_id"]}
        self.assertEqual(resolution.solve_joint(*fx[1:], [self.request(compiled, row)])["status"], "joint_possible")
        self.assertEqual(resolution.solve_joint(*fx[1:], (), [req])["status"], "joint_possible")
        combined = resolution.solve_joint(*fx[1:], [self.request(compiled, row)], [req])
        self.assertEqual(combined["status"], "incompatible_joint_constraints")
        self.assertTrue(resolution.validate_joint(*fx[1:], combined))

    def test_leading_and_seventh_two_lanes_share_one_bundle_and_one_query_each(self):
        fx = self.fixture([[event("B4", 0, 2), event("C5", 2, 2)], [event("F4", 0, 2), event("E4", 2, 2)]])
        compiled = self.compile(fx)
        rows = [self.row(fx, compiled, role) for role in ("leading_tone", "seventh")]
        solution = resolution.solve_joint(*fx[1:], [self.request(compiled, row) for row in rows])
        self.assertEqual(solution["status"], "joint_possible")
        self.assertEqual(len(solution["branches"][0]["queries"]), 2)
        bundle = solution["branches"][0]["completion_bundle"]
        assessed = resolution.evaluate_resolutions(*fx[1:], bundle)
        self.assertTrue(all(next(a["status"] for a in assessed["assessments"] if a["resolution_ref"] == row["resolution_id"]) == "conditional_resolution_under_bundle" for row in rows))
        changed = deepcopy(bundle)
        changed["entries"][0]["witness"] = deepcopy(bundle["entries"][1]["witness"])
        changed = reseal(changed, "fmcmb_")
        with self.assertRaises(ValueError):resolution.validate_bundle(fx[1], fx[2], fx[5], changed)

    def test_written_pitch_conflict_is_separate_from_clock_and_retains_motion(self):
        fx = self.fixture(); ir = fx[0]
        first = next(n for n in ir["note_events"] if n["written_pitch"]["step"] == "B")
        first["written_pitch"].update(step="A", spelling="A4", midi_pitch=69, pitch_class=9)
        view = make_view(ir, span()); path = common.make_path(view, fx[2]["segments"], provenance())
        key = overlay.make_key_track(view, [key_segment()], provenance()); functions = overlay.compile_functions(view, path, key)
        graphs = [factors.factorize(ir, span(), g["lane"]) for g in fx[5]]
        changed = (ir, view, path, key, functions, graphs)
        row = self.row(changed, self.compile(changed))
        self.assertEqual(row["status"], "withheld")
        self.assertTrue(row["observations"][0]["actual_motion_matches_expected"])
        self.assertTrue(row["observations"][0]["source_and_destination_snapshots"][0]["source_clock_passed"])
        self.assertFalse(row["observations"][0]["source_and_destination_snapshots"][0]["source_pitch_consistency_passed"])

    def test_grace_and_point_inventory_kept_with_unknown_graph_scope(self):
        fx = self.fixture([[event("B4", 0, 2), event("D5", 2, 0, grace=True), event("C5", 2, 2)]])
        compiled = self.compile(fx); row = self.row(fx, compiled)
        self.assertTrue(compiled["point_observations"])
        self.assertEqual(row["status"], "withheld")
        self.assertIn("factor_graph_not_ready", row["blockers"])

    def test_exact_rational_boundaries_and_original_tied_sound_identity(self):
        fx = self.fixture([[event("B4", 0, 1, tie_role="start"), event("B4", 1, 1, tie_role="stop"), event("C5", 2, 2)]])
        row = self.row(fx, self.compile(fx))
        self.assertEqual(row["status"], "conditional_resolution_shape")
        source = row["observations"][0]["source_and_destination_snapshots"][0]
        self.assertEqual(len(source["source_note_ids"]), 2)
        self.assertEqual(len(row["alternatives"][0]["required_links"]), 1)

    def test_no_source_observation_slots_are_retained_and_candidate_count_exact(self):
        fx = self.fixture([[event("G4", 0, 2), event("C5", 2, 2)]])
        compiled = self.compile(fx); row = self.row(fx, compiled)
        self.assertIsNone(row["source_sound_ref"])
        self.assertEqual(row["observations"][0]["sound_refs"], [])
        self.assertEqual(int(compiled["total_chain_observations"]), sum(len(r["observations"]) for r in compiled["rules"]))
        self.assertEqual(int(compiled["total_candidates"]), len(compiled["rules"]) + sum(len(r["observations"]) for r in compiled["rules"]))

    def test_one_bundle_multiple_paths_exact_registry_and_no_rebinding(self):
        fx = self.fixture(); compiled = self.compile(fx); row = self.row(fx, compiled)
        changed = deepcopy(fx[2]["segments"]); changed[0]["segment_id"] = "another-origin"
        other = common.make_path(fx[1], changed, provenance())
        bundle = self.bundle(fx, row["alternatives"][0]["required_links"], paths=[other, fx[2]])
        self.assertTrue(resolution.validate_bundle(fx[1], [fx[2], other], fx[5], bundle))
        with self.assertRaises(ValueError):resolution.validate_bundle(fx[1], fx[2], fx[5], bundle)
        functions = overlay.compile_functions(fx[1], other, fx[3])
        assessed = resolution.evaluate_resolutions(fx[1], other, fx[3], functions, fx[5], bundle)
        self.assertEqual(assessed["completion_bundle_ref"], common.ref(bundle))

    def test_graph_lane_duplicate_foreign_completion_and_resealed_tamper_fail(self):
        fx = self.fixture(); bundle = self.bundle(fx)
        with self.assertRaises(ValueError):
            resolution.compile_resolutions(*fx[1:5], [fx[5][0], fx[5][0]])
        changed = deepcopy(bundle); changed["entries"][0]["completion_id"] = "wrong"
        changed = reseal(changed, "fmcmb_")
        with self.assertRaises(ValueError):resolution.validate_bundle(fx[1], fx[2], fx[5], changed)
        changed = deepcopy(bundle["entries"][0]["witness"]); changed["assignment"]["links"] = [["foreign-a", "foreign-b"]]
        changed = reseal(changed, "vfwitness_")
        with self.assertRaises(ValueError):resolution.make_bundle(fx[1], fx[2], [{"graph": fx[5][0], "query": bundle["entries"][0]["query"], "witness": changed}])

    def test_json_replay_and_result_mutation_does_not_change_inputs(self):
        fx = self.fixture(); compiled = self.compile(fx); row = self.row(fx, compiled)
        solution = resolution.solve_joint(*fx[1:], [self.request(compiled, row)])
        self.assertTrue(resolution.validate_joint(*fx[1:], json.loads(json.dumps(solution))))
        changed = deepcopy(compiled); changed["rules"][0]["verdict"] = "confirmed"
        changed = reseal(changed, "fmres_")
        with self.assertRaises(ValueError):resolution.validate_resolutions(*fx[1:], changed)

    def test_source_annotations_do_not_enter_literal_motion_or_inventory(self):
        fx = self.fixture(); compiled = self.compile(fx)
        self.assertFalse(compiled["source_annotations_used"])
        with patch.object(factors, "factorize", side_effect=AssertionError("no factorize in evaluator")):
            self.assertTrue(resolution.validate_resolutions(*fx[1:], compiled))
            bundle = self.bundle(fx)
            self.assertTrue(resolution.validate_bundle(fx[1], fx[2], fx[5], bundle))

    def test_immutable_actual_content_memo_and_all_public_validators_are_fresh(self):
        fx = self.fixture()
        with patch.object(resolution, "_compile_fresh", wraps=resolution._compile_fresh) as fresh:
            compiled = self.compile(fx)
            pristine = deepcopy(compiled)
            compiled["rules"][0]["verdict"] = "caller mutation"
            self.assertEqual(self.compile(fx), pristine)
            self.assertEqual(fresh.call_count, 1)
            resolution.validate_resolutions(*fx[1:], pristine)
            self.assertEqual(fresh.call_count, 2)
            assessed = resolution.evaluate_resolutions(*fx[1:], self.bundle(fx))
            resolution.validate_evaluation(*fx[1:], self.bundle(fx), assessed)
            self.assertEqual(fresh.call_count, 3)
            solution = resolution.solve_joint(*fx[1:])
            resolution.validate_joint(*fx[1:], solution)
            self.assertEqual(fresh.call_count, 4)

    def test_memo_does_not_trust_caller_sha_and_schema_contents_invalidate(self):
        fx = self.fixture(); compiled = self.compile(fx)
        changed = deepcopy(fx[4]); root = changed["rows"][0]["target_root"]
        root["step"] = "C" if root["step"] != "C" else "D"
        with self.assertRaises(ValueError):resolution.compile_resolutions(*fx[1:4], changed, fx[5])
        with patch.object(resolution, "_compile_fresh", wraps=resolution._compile_fresh) as fresh:
            raw = common._schema_bytes()
            with patch.object(common, "_schema_bytes", return_value=raw + b"\n"):
                self.assertEqual(self.compile(fx), compiled)
            self.assertEqual(fresh.call_count, 1)

    def test_memo_entry_and_serialized_byte_caps_only_affect_recomputation(self):
        fx = self.fixture()
        with patch.object(resolution, "_COMPILATION_CACHE_BYTE_LIMIT", 1):
            a = self.compile(fx); b = self.compile(fx)
            self.assertEqual(a, b)
            self.assertEqual(len(resolution._COMPILATION_CACHE), 0)
        with patch.object(resolution, "_COMPILATION_CACHE_LIMIT", 1):
            self.compile(fx)
            p = deepcopy(provenance()); p["engine_version"] = "another-origin"
            other = common.make_path(fx[1], fx[2]["segments"], p)
            fn = overlay.compile_functions(fx[1], other, fx[3])
            resolution.compile_resolutions(fx[1], other, fx[3], fn, fx[5])
            self.assertEqual(len(resolution._COMPILATION_CACHE), 1)
            self.assertLessEqual(resolution._COMPILATION_CACHE_BYTES, resolution._COMPILATION_CACHE_BYTE_LIMIT)
            self.assertEqual(self.compile(fx), a)

    def test_private_memo_byte_corruption_fails_closed(self):
        fx = self.fixture(); self.compile(fx)
        key = next(iter(resolution._COMPILATION_CACHE))
        payload, sha, size = resolution._COMPILATION_CACHE[key]
        resolution._COMPILATION_CACHE[key] = payload + b" ", sha, size
        with self.assertRaisesRegex(ValueError, "private_compilation_memo_payload_changed"):
            self.compile(fx)

    def test_prepared_reuse_is_byte_equal_with_one_fresh_bundle_guard(self):
        fx = self.fixture(); bundle = self.bundle(fx)
        with patch.object(resolution, "validate_bundle", wraps=resolution.validate_bundle) as verified, \
             patch.object(resolution, "_compile_fresh", wraps=resolution._compile_fresh) as fresh:
            handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], bundle)
            first = resolution._assess_prepared(handle, *fx[2:5])
            second = resolution._assess_prepared(handle, *fx[2:5])
            self.assertEqual(verified.call_count, 1)
            self.assertEqual(fresh.call_count, 1)
            public = resolution.evaluate_resolutions(*fx[1:], bundle)
            self.assertEqual(resolution._encoded(first), resolution._encoded(public))
            self.assertEqual(first, second)
            self.assertEqual(verified.call_count, 2)
            resolution.validate_evaluation(*fx[1:], bundle, first)
            self.assertEqual(verified.call_count, 3)
            self.assertEqual(fresh.call_count, 2)

    def test_prepared_one_registry_multiple_keys_paths_and_distinct_completions(self):
        fx = self.fixture(); row = self.row(fx, self.compile(fx))
        other = common.make_path(fx[1], fx[2]["segments"], {**provenance(), "engine_version": "another-origin"})
        keys = [fx[3], overlay.make_key_track(fx[1], [key_segment(tonic=None, mode="unknown", form="unknown")], provenance())]
        bundles = [self.bundle(fx, paths=[other, fx[2]]),
                   self.bundle(fx, row["alternatives"][0]["required_links"], paths=[other, fx[2]])]
        handles = [resolution.prepare_bundle(fx[1], [fx[2], other], fx[5], b) for b in bundles]
        observations = []
        for handle, bundle in zip(handles, bundles):
            for path in (fx[2], other):
                for key in keys:
                    functions = overlay.compile_functions(fx[1], path, key)
                    prepared = resolution._assess_prepared(handle, path, key, functions)
                    public = resolution.evaluate_resolutions(fx[1], path, key, functions, fx[5], bundle)
                    self.assertEqual(resolution._encoded(prepared), resolution._encoded(public))
                    observations.append(prepared)
        self.assertNotEqual(observations[0]["assessments"], observations[4]["assessments"])
        self.assertNotEqual(observations[0]["completion_bundle_ref"], observations[4]["completion_bundle_ref"])

    def test_prepared_missing_completion_keeps_unknown_and_full_graph_inventory(self):
        fx = self.fixture([[event("B4", 0, 2), event("C5", 2, 2)],
                           [event("F4", 0, 2), event("E4", 2, 2)]])
        bundle = self.bundle(fx, graph_indices=[0])
        handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], bundle)
        prepared = resolution._assess_prepared(handle, *fx[2:5])
        public = resolution.evaluate_resolutions(*fx[1:], bundle)
        self.assertEqual(prepared, public)
        self.assertTrue(any("raw_lane_completion_missing_unknown" in a["blockers"] for a in prepared["assessments"]))

    def test_prepared_snapshot_and_returns_are_not_caller_mutable(self):
        fx = self.fixture(); bundle = self.bundle(fx); original = deepcopy([*fx[1:], bundle])
        handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], bundle)
        expected = resolution._assess_prepared(handle, *fx[2:5])
        self.assertEqual([*fx[1:], bundle], original)
        fx[1]["binding"]["score_id"] = "caller mutation"
        fx[5][0]["events"][0]["pitch"] = {"step": "A", "alter": common.q(0), "octave": 7}
        bundle["entries"][0]["witness"]["assignment"]["links"] = [["forged", "target"]]
        returned = resolution._assess_prepared(handle, *fx[2:5])
        self.assertEqual(returned, expected)
        returned["assessments"][0]["selected"] = "caller mutation"
        self.assertEqual(resolution._assess_prepared(handle, *fx[2:5]), expected)

    def test_prepared_fake_copied_foreign_and_stale_path_records_fail_closed(self):
        fx = self.fixture(); bundle = self.bundle(fx)
        handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], bundle)
        for fake in (resolution._PreparedBundle(), deepcopy(handle), None, {"verified": True}):
            with self.assertRaisesRegex(ValueError, "internally_issued_prepared_bundle_required"):
                resolution._assess_prepared(fake, *fx[2:5])
        changed = deepcopy(fx[2]); changed["segments"][0]["root"]["step"] = "A"
        for other in (changed, reseal(changed, "fmhp_")):
            with self.assertRaisesRegex(ValueError, "resolution_path_not_in_prepared_registry"):
                resolution._assess_prepared(handle, other, *fx[3:5])
        foreign = overlay.make_key_track(fx[1], [key_segment(tonic=None, mode="unknown", form="unknown")], provenance())
        with self.assertRaises(ValueError):resolution._assess_prepared(handle, fx[2], foreign, fx[4])
        changed = deepcopy(bundle); changed["entries"][0]["completion_id"] = "fake"
        with self.assertRaises(ValueError):
            resolution.prepare_bundle(fx[1], fx[2], fx[5], reseal(changed, "fmcmb_"))

    def test_prepared_internal_bytes_and_authenticated_state_tamper_fail_closed(self):
        fx = self.fixture(); handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], self.bundle(fx))
        state = resolution._PREPARED_BUNDLES[handle]
        resolution._PREPARED_BUNDLES[handle] = replace(state, payload=state.payload + b" ")
        with self.assertRaisesRegex(ValueError, "prepared_bundle_internal_content_changed"):
            resolution._assess_prepared(handle, *fx[2:5])
        resolution._PREPARED_BUNDLES[handle] = replace(state, payload_sha256="caller reseal")
        with self.assertRaisesRegex(ValueError, "prepared_bundle_contract_or_internal_state_changed"):
            resolution._assess_prepared(handle, *fx[2:5])
        resolution._PREPARED_BUNDLES[handle] = state
        self.assertEqual(resolution._assess_prepared(handle, *fx[2:5]),
                         resolution.evaluate_resolutions(*fx[1:], self.bundle(fx)))

    def test_prepared_schema_and_code_contract_changes_fail_closed(self):
        fx = self.fixture(); handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], self.bundle(fx))
        raw = common._schema_bytes()
        with patch.object(common, "_schema_bytes", return_value=raw + b"\n"):
            with self.assertRaisesRegex(ValueError, "prepared_bundle_contract_or_internal_state_changed"):
                resolution._assess_prepared(handle, *fx[2:5])
        with patch.object(resolution, "VERSION", "changed-code-contract"):
            with self.assertRaisesRegex(ValueError, "prepared_bundle_contract_or_internal_state_changed"):
                resolution._assess_prepared(handle, *fx[2:5])

    def test_theory_helper_actual_source_stamp_invalidates_memo_and_preparation(self):
        from pathlib import Path
        from musicanote_harness import seventh_context
        fx = self.fixture(); original = self.compile(fx)
        handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], self.bundle(fx))
        read_bytes = Path.read_bytes
        helper = Path(seventh_context.__file__)
        def changed(path):
            body = read_bytes(path)
            return body + b"\n" if path == helper else body
        with patch.object(Path, "read_bytes", changed), \
             patch.object(resolution, "_compile_fresh", wraps=resolution._compile_fresh) as fresh:
            self.assertEqual(self.compile(fx), original)
            self.assertEqual(fresh.call_count, 1)
            with self.assertRaisesRegex(ValueError, "prepared_bundle_contract_or_internal_state_changed"):
                resolution._assess_prepared(handle, *fx[2:5])

    def test_literal_motion_refs_resolve_to_one_exact_retained_payload(self):
        fx = self.fixture([[event("B4", 0, 2), event("B4", 2, 1), event("C5", 3, 1)]])
        assessed = resolution.evaluate_resolutions(*fx[1:], self.bundle(fx))
        expected = [{"resolution_ref": a["resolution_ref"], "observation_ref": o["observation_id"]}
                    for a in assessed["assessments"] for o in a["rule_snapshot"]["observations"]]
        self.assertEqual(assessed["literal_motion_observation_refs"], expected)
        self.assertNotIn("literal_motion_observations", assessed)

    def test_prepared_lifecycle_releases_fixed_context_and_graphs(self):
        fx = self.fixture(); handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], self.bundle(fx))
        self.assertEqual(len(resolution._PREPARED_BUNDLES), 1)
        reference = weakref.ref(handle)
        del handle
        gc.collect()
        self.assertIsNone(reference())
        self.assertEqual(len(resolution._PREPARED_BUNDLES), 0)

    def test_owned_compilation_seal_is_exact_and_has_no_caller_aliases(self):
        fx = self.fixture([[event("B4", 0, 2), event("B4", 2, 1), event("C5", 3, 1)],
                           [event("F4", 0, 2), event("E4", 2, 2)]])
        original = deepcopy(fx)
        compiled = self.compile(fx)
        def mutable_ids(value):
            found = set()
            if isinstance(value, dict):
                found.add(id(value))
                for child in value.values(): found.update(mutable_ids(child))
            elif isinstance(value, (list, tuple)):
                if isinstance(value, list): found.add(id(value))
                for child in value: found.update(mutable_ids(child))
            return found
        self.assertFalse(mutable_ids(compiled) & mutable_ids(fx))
        body = {k: v for k, v in compiled.items() if k not in ("record_id", "record_sha256")}
        self.assertEqual(compiled, common.seal(body, "fmres_"))
        canonical = resolution._encoded(compiled)
        compiled["rules"][0]["prerequisites"]["function_snapshot"]["source_root"]["step"] = "A"
        # Identity ordering is not an observation-presence ranking: a held
        # observation may legitimately have no source/destination snapshots.
        snapshots = [snapshot for rule in compiled["rules"] for observation in rule["observations"]
                     for snapshot in observation["source_and_destination_snapshots"]]
        self.assertTrue(snapshots, "fixture must exercise at least one owned literal snapshot")
        snapshots[0]["pitch"]["step"] = "A"
        self.assertEqual(fx, original)
        self.assertEqual(resolution._encoded(self.compile(fx)), canonical)

    def test_owned_public_evaluation_snapshots_are_isolated_and_freshly_replayed(self):
        fx = self.fixture([[event("B4", 0, 2), event("B4", 2, 1), event("C5", 3, 1)]])
        bundle = self.bundle(fx)
        supplied = [*fx[1:], bundle]
        original = deepcopy(supplied)
        compiled = self.compile(fx)
        compiled_bytes = resolution._encoded(compiled)
        evaluation = resolution.evaluate_resolutions(*fx[1:], bundle)
        body = {k: v for k, v in evaluation.items() if k not in ("record_id", "record_sha256")}
        self.assertEqual(evaluation, common.seal(body, "fmreval_"))
        canonical = resolution._encoded(evaluation)
        evaluation["assessments"][0]["rule_snapshot"]["prerequisites"]["function_snapshot"]["source_root"]["step"] = "A"
        self.assertEqual(supplied, original)
        self.assertEqual(resolution._encoded(compiled), compiled_bytes)
        self.assertEqual(resolution._encoded(resolution.evaluate_resolutions(*fx[1:], bundle)), canonical)
        with self.assertRaises(ValueError):
            resolution.validate_evaluation(*fx[1:], bundle, reseal(evaluation, "fmreval_"))

    def test_owned_prepared_evaluations_share_no_mutable_return_state(self):
        fx = self.fixture([[event("B4", 0, 2), event("C5", 2, 2)],
                           [event("F4", 0, 2), event("E4", 2, 2)]])
        bundle = self.bundle(fx)
        handle = resolution.prepare_bundle(fx[1], fx[2], fx[5], bundle)
        first = resolution._assess_prepared(handle, *fx[2:5])
        second = resolution._assess_prepared(handle, *fx[2:5])
        self.assertEqual(first, second)
        canonical = resolution._encoded(second)
        observed = next(row for row in first["assessments"]
                        if row["rule_snapshot"]["observations"][0]["source_and_destination_snapshots"])
        observed["rule_snapshot"]["observations"][0]["source_and_destination_snapshots"][0]["span"]["end"] = common.q(999)
        observed["blockers"].append("returned_record_mutation")
        self.assertEqual(resolution._encoded(second), canonical)
        self.assertEqual(resolution._encoded(resolution._assess_prepared(handle, *fx[2:5])), canonical)
        self.assertEqual(resolution._encoded(resolution.evaluate_resolutions(*fx[1:], bundle)), canonical)
        resolution.validate_evaluation(*fx[1:], bundle, second)


if __name__ == "__main__":
    unittest.main()
