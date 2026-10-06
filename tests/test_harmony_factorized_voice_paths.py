"""Exact geometry universe, constrained counts and fresh replay controls."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_factorized_voice_paths as factors
from musicanote_harness.harmony_path_contrast import token
from musicanote_harness.harmony_voice_paths import observe, partition
from musicanote_harness.musical_pattern_observation import digest, f, q
from test_harmony_open_candidates import score as old_score
from test_musical_role_evidence import event, make_ir


LANE = ("part1", "v")


def score(rows):
    """Add literal binding/traceability to the existing small geometry fixture."""
    ir = old_score(rows)
    ir.update(ir_document_id="test-ir", score={"score_id": "test-score", "source_file_id": "test-source"},
              source_files=[{"source_file_id": "test-source", "sha256": "a" * 64}],
              source_references=[], tie_chains=[])
    for n in ir["note_events"]:
        n["source_ref_id"] = "source-" + n["note_id"]
        ir["source_references"].append({"source_ref_id": n["source_ref_id"],
                                         "source_file_id": "test-source", "source_note_id": n["note_id"]})
    return ir


def context(end=4, start=0):
    return {"start": q(start), "end": q(end)}


def run(rows, end=4, start=0, **caps):
    return factors.factorize(score(rows), context(end, start), LANE, **caps)


def edges(graph):
    return [(a, b) for row in graph["factors"] for a in row["source_refs"] for b in row["target_refs"]]


def reseal(record, prefix):
    body = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    record["record_sha256"] = digest(body)
    record["record_id"] = prefix + record["record_sha256"][:24]
    return record


class FactorizedVoicePathsTests(unittest.TestCase):
    def test_three_sequential_sounds_four_unenumerated_assignments(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 2, 3, "v")])
        self.assertEqual(graph["status"], "ready")
        self.assertEqual(graph["possible_assignments"], "4")
        self.assertEqual(len(graph["factors"]), 2)
        self.assertNotIn("assignments", graph)
        self.assertFalse(graph["global_product_enumerated"])
        result = factors.query(graph)
        self.assertEqual(result["possible_assignments"], "4")
        self.assertEqual(result["witness"]["links"], [])
        self.assertEqual(len(factors.materialize_witness(graph, result)["assignment"]["tracks"]), 3)

    def test_two_2_by_2_factors_preserve_all_49(self):
        rows = [(p, t, t + 1, "v") for t, ps in enumerate([("C4", "G4"), ("D4", "A4"), ("E4", "B4")]) for p in ps]
        ir = score(rows)
        graph = factors.factorize(ir, context(), LANE)
        old = observe(ir, context(), LANE)
        self.assertEqual(graph["possible_assignments"], "49")
        self.assertEqual(old["possible_assignments"], int(graph["possible_assignments"]))
        self.assertEqual([x["possible_assignments"] for x in graph["factors"]], ["7", "7"])

    def test_all_small_required_forbidden_counts_equal_full_enumeration(self):
        ir = score([(p, a, b, "v") for a, b, pitches in [(0, 1, ("C4", "E4")), (1, 2, ("D4", "F4"))] for p in pitches])
        graph = factors.factorize(ir, context(), LANE)
        assignments = observe(ir, context(), LANE)["assignments"]
        for states in product(range(3), repeat=4):
            required = [pair for pair, state in zip(edges(graph), states) if state == 1]
            forbidden = [pair for pair, state in zip(edges(graph), states) if state == 2]
            n = sum(set(required).issubset(map(tuple, a["links"])) and not set(forbidden).intersection(map(tuple, a["links"]))
                    for a in assignments)
            result = factors.query(graph, required_links=required, forbidden_links=forbidden)
            self.assertEqual(result["possible_assignments"], str(n), states)
            self.assertEqual(result["status"], "exact_count" if n else "unsatisfiable_constraints")
            factors.validate_query(graph, result, required_links=required, forbidden_links=forbidden)
            if n:
                witness = factors.materialize_witness(graph, result)
                aid = witness["assignment"]["legacy_geometry_id"]
                equivalent = next(a for a in assignments if a["assignment_id"] == aid)
                self.assertEqual(equivalent["links"], witness["assignment"]["links"])
                self.assertEqual(equivalent["tracks"], witness["assignment"]["tracks"])

    def test_cross_boundary_constraints_equal_old_assignments(self):
        ir = score([(p, t, t + 1, "v") for t, ps in enumerate([("C4", "G4"), ("D4", "A4"), ("E4", "B4")]) for p in ps])
        graph = factors.factorize(ir, context(), LANE)
        required = [edges(graph)[0], edges(graph)[4]]
        forbidden = [edges(graph)[3], edges(graph)[7]]
        old = observe(ir, context(), LANE)
        count = sum(set(required).issubset(map(tuple, a["links"])) and not set(forbidden).intersection(map(tuple, a["links"]))
                    for a in old["assignments"])
        result = factors.query(graph, required_links=required, forbidden_links=forbidden)
        self.assertEqual(result["possible_assignments"], str(count))

    def test_12_sounds_survive_old_2048_global_cap(self):
        ir = score([("C4", i, i + 1, "v") for i in range(12)])
        old = observe(ir, context(13), LANE)
        self.assertFalse(old["enumeration_complete"])
        graph = factors.factorize(ir, context(13), LANE)
        self.assertEqual(graph["status"], "ready")
        self.assertEqual(graph["possible_assignments"], "2048")
        result = factors.query(graph, required_links=edges(graph))
        self.assertEqual(result["possible_assignments"], "1")
        self.assertEqual(len(factors.materialize_witness(graph, result)["assignment"]["tracks"]), 1)

    def test_one_4_by_4_factor_has_209(self):
        graph = run([(p, 0, 1, "v") for p in ("C4", "D4", "E4", "F4")]
                    + [(p, 1, 2, "v") for p in ("G4", "A4", "B4", "C5")])
        self.assertEqual(graph["possible_assignments"], "209")
        self.assertEqual(graph["legal_edge_count"], 16)

    def test_5_by_5_analytic_universe_not_old_zero(self):
        ir = score([(p, 0, 1, "v") for p in ("C4", "D4", "E4", "F4", "G4")]
                   + [(p, 1, 2, "v") for p in ("A4", "B4", "C5", "D5", "E5")])
        old = observe(ir, context(), LANE)
        self.assertEqual(old["possible_assignments"], 0)  # old abstention artifact, not infeasibility
        with patch("musicanote_harness.harmony_polyphonic_links.partial_matchings", side_effect=AssertionError("no enumeration")):
            graph = factors.factorize(ir, context(), LANE)
            result = factors.query(graph)
        self.assertEqual(graph["possible_assignments"], "1546")
        self.assertEqual(result["possible_assignments"], "1546")
        self.assertEqual(graph["factors"][0]["edge_representation"], "complete_bipartite_endpoint_product")
        self.assertNotIn("choices", graph["factors"][0])

    def test_large_exact_decimal_conversion_avoids_global_int_limit(self):
        self.assertEqual(factors._decimal(10 ** 5000), "1" + "0" * 5000)

    def test_forbid_all_yields_one_all_isolated_completion(self):
        graph = run([(p, a, b, "v") for a, b, ps in [(0, 1, ("C4", "E4")), (1, 2, ("D4", "F4"))] for p in ps])
        result = factors.query(graph, forbidden_links=edges(graph))
        self.assertEqual(result["possible_assignments"], "1")
        witness = factors.materialize_witness(graph, result)
        self.assertEqual(witness["assignment"]["links"], [])
        self.assertTrue(all(len(t) == 1 for t in witness["assignment"]["tracks"]))

    def test_required_branch_merge_and_conflict_are_exact_unsat(self):
        graph = run([(p, a, b, "v") for a, b, ps in [(0, 1, ("C4", "E4")), (1, 2, ("D4", "F4"))] for p in ps])
        a, b, c, d = [s["sounding_event_id"] for s in graph["events"]]
        for req, forbidden, reason in [([(a, c), (a, d)], [], "required_branch_not_allowed"),
                                       ([(a, c), (b, c)], [], "required_merge_not_allowed"),
                                       ([(a, c)], [(a, c)], "required_and_forbidden_same_edge")]:
            result = factors.query(graph, required_links=req, forbidden_links=forbidden)
            self.assertEqual(result["status"], "unsatisfiable_constraints")
            self.assertEqual(result["possible_assignments"], "0")
            self.assertIn(reason, result["reasons"])
            with self.assertRaisesRegex(ValueError, "no_exact_query_witness"):
                factors.materialize_witness(graph, result)

    def test_duplicate_constraints_are_idempotent(self):
        graph = run([(p, a, b, "v") for a, b, ps in [(0, 1, ("C4", "E4")), (1, 2, ("D4", "F4"))] for p in ps])
        pair = edges(graph)[0]
        result = factors.query(graph, required_links=[pair, pair, list(pair)])
        self.assertEqual(result["possible_assignments"], "2")
        self.assertEqual(result["witness"]["links"], [list(pair)])

    def test_forbidden_occupied_rows_columns_do_not_reduce_count_again(self):
        graph = run([(p, a, b, "v") for a, b, ps in [(0, 1, ("C4", "E4")), (1, 2, ("D4", "F4"))] for p in ps])
        a, b, c, d = [s["sounding_event_id"] for s in graph["events"]]
        result = factors.query(graph, required_links=[(a, c)], forbidden_links=[(a, d), (b, c)], work_budget=0)
        self.assertEqual(result["possible_assignments"], "2")
        self.assertEqual(result["factor_results"][0]["effective_forbidden_links"], [])

    def test_two_consecutive_required_links_are_compatible(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 2, 3, "v")])
        result = factors.query(graph, required_links=[("s0", "s1"), ("s1", "s2")])
        self.assertEqual(result["possible_assignments"], "1")
        self.assertEqual(factors.materialize_witness(graph, result)["assignment"]["tracks"], [["s0", "s1", "s2"]])
        invalid = factors.query(graph, required_links=[("s0", "s2")])
        self.assertEqual(invalid["status"], "invalid_constraints")
        self.assertIsNone(invalid["possible_assignments"])
        self.assertEqual(result["constraint_semantics"], "direct_endpoint_edges_not_transitive_same_track")

    def test_unknown_malformed_backward_and_nonedge_not_negative_proofs(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        for pairs in [[("s0", "absent")], [("s1", "s0")], [("s0", "s0")], [("s0",)], "s0"]:
            result = factors.query(graph, forbidden_links=pairs)
            self.assertEqual(result["status"], "invalid_constraints")
            self.assertIsNone(result["possible_assignments"])
            self.assertIsNone(result["witness"])

    def test_rest_gap_never_bridged(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 2, 3, "v")])
        self.assertEqual(graph["factors"], [])
        self.assertEqual(graph["possible_assignments"], "1")
        self.assertEqual(factors.query(graph, required_links=[("s0", "s1")])["status"], "invalid_constraints")

    def test_held_sound_is_not_reconnected_and_full_span_is_preserved(self):
        graph = run([("C3", 0, 4, "v"), ("G4", 0, 1, "v"), ("A4", 1, 2, "v"), ("B4", 2, 3, "v")])
        self.assertTrue(all("s0" in row["held_refs"] for row in graph["factors"]))
        self.assertTrue(all("s0" not in pair for pair in edges(graph)))
        result = factors.query(graph, required_links=edges(graph))
        self.assertIn(["s0"], factors.materialize_witness(graph, result)["assignment"]["tracks"])

    def test_context_cuts_do_not_create_endpoints_or_clip_events(self):
        graph = run([("C4", 0, 3, "v"), ("G4", 1, 2, "v"), ("A4", 2, 3, "v")], end=2, start=1)
        self.assertEqual(graph["factors"], [])
        self.assertEqual(graph["total_observed_note_time"], q(2))
        self.assertEqual(graph["events"][0]["span"], context(3))
        self.assertEqual(graph["possible_assignments"], "1")

    def test_rational_one_third_no_float_alignment(self):
        graph = run([("C4", 0, F(1, 3), "v"), ("D4", F(1, 3), F(2, 3), "v"), ("E4", F(2, 3), 1, "v")])
        self.assertEqual([row["time"] for row in graph["factors"]], [q(F(1, 3)), q(F(2, 3))])
        self.assertEqual(graph["total_observed_note_time"], q(1))
        self.assertEqual(graph["possible_assignments"], "4")

    def test_cross_voice_and_part_links_are_invalid(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "other"), ("E4", 1, 2, "v")])
        ir["note_events"][2]["part_id"] = "part2"
        graph = factors.factorize(ir, context(), LANE)
        self.assertEqual(len(graph["events"]), 1)
        self.assertEqual(graph["possible_assignments"], "1")
        for pair in [("s0", "s1"), ("s0", "s2")]:
            self.assertEqual(factors.query(graph, required_links=[pair])["status"], "invalid_constraints")

    def test_cross_staff_same_raw_voice_still_admissible(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        ir["note_events"][0]["display_staff_id"] = "staff1"
        ir["note_events"][1]["display_staff_id"] = "staff2"
        self.assertEqual(factors.factorize(ir, context(), LANE)["possible_assignments"], "2")

    def test_points_including_context_start_retained_and_sampled_lane_abstains(self):
        ir = score([("C4", 0, 0, "v"), ("D4", 1, 1, "v"), ("E4", 1, 2, "v")])
        for n in ir["note_events"][:2]:
            n["grace"] = {"is_grace": True}
        graph = factors.factorize(ir, context(), LANE)
        self.assertEqual(graph["point_sound_refs"], ["s0", "s1"])
        self.assertEqual(graph["sampled_lane_point_sound_refs"], ["s0", "s1"])
        self.assertEqual(graph["status"], "abstention")
        self.assertIsNone(graph["possible_assignments"])
        self.assertEqual(factors.query(graph)["status"], "abstention")
        self.assertEqual(len(graph["point_sounding_events"]), 2)

    def test_known_other_lane_grace_is_metadata_not_sampled_constraint(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("B4", 1, 1, "other")])
        ir["note_events"][2]["grace"] = {"is_grace": True}
        graph = factors.factorize(ir, context(), LANE)
        self.assertEqual(graph["status"], "ready")
        self.assertEqual(graph["other_lane_point_sound_refs"], ["s2"])
        self.assertEqual(graph["point_sound_refs"], ["s2"])
        self.assertEqual(graph["possible_assignments"], "2")

    def test_unlocated_point_and_sound_preserved_no_silent_exclusion(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 1, 1, "other")])
        ir["note_events"][1]["voice_id"] = None
        ir["sounding_events"][2]["source_note_ids"] = ["missing-note"]
        graph = factors.factorize(ir, context(), LANE)
        self.assertEqual(graph["status"], "abstention")
        self.assertEqual(graph["unlocated_sound_refs"], ["s1", "s2"])
        self.assertEqual(graph["point_sound_refs"], ["s2"])
        self.assertEqual(graph["missing_source_note_refs"], ["missing-note"])
        self.assertEqual(len(graph["context_sounding_events"]), 3)
        self.assertEqual(factors.query(graph)["status"], "abstention")

    def test_empty_lane_preserves_other_context_observations(self):
        graph = run([("C4", 0, 1, "other")])
        self.assertEqual(graph["status"], "abstention")
        self.assertIn("empty_lane", graph["reasons"])
        self.assertEqual(len(graph["context_sounding_events"]), 1)
        self.assertIsNone(graph["possible_assignments"])

    def test_all_graph_resource_budgets_hold_without_pruning(self):
        rows = [("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 2, 3, "v")]
        for key, limit in [("max_events", 2), ("max_factors", 1), ("max_edges", 1)]:
            graph = run(rows, **{key: limit})
            self.assertEqual(graph["status"], "abstention")
            self.assertIn(key + "_exceeded_no_pruning", graph["reasons"])
            self.assertEqual(len(graph["events"]), 3)
            self.assertEqual(len(graph["factors"]), 2)
            self.assertEqual(graph["legal_edge_count"], 2)
            self.assertIsNone(graph["possible_assignments"])
            self.assertEqual(factors.query(graph)["status"], "abstention")

    def test_query_work_budget_not_partial_count_or_witness(self):
        graph = run([(p, a, b, "v") for a, b, ps in [(0, 1, ("C4", "E4")), (1, 2, ("D4", "F4"))] for p in ps])
        result = factors.query(graph, forbidden_links=[edges(graph)[0]], work_budget=1)
        self.assertEqual(result["status"], "abstention")
        self.assertIsNone(result["possible_assignments"])
        self.assertIsNone(result["witness"])
        self.assertLessEqual(result["work"]["state_visits"] + result["work"]["transition_attempts"], 1)
        self.assertEqual(factors.query(graph, work_budget=0)["possible_assignments"], "7")

    def test_one_shared_work_budget_across_factors(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 2, 3, "v")])
        result = factors.query(graph, forbidden_links=edges(graph), work_budget=2)
        self.assertEqual(result["status"], "abstention")
        self.assertEqual(len(result["factor_results"]), 1)
        self.assertIsNone(result["possible_assignments"])
        self.assertEqual(factors.query(graph, forbidden_links=edges(graph), work_budget=4)["possible_assignments"], "1")

    def test_small_side_dp_orientation_counts_equal(self):
        for left_size, right_size in [(1, 3), (3, 1), (2, 3), (3, 2)]:
            rows = [("C4", 0, 1, "v") for _ in range(left_size)] + [("D4", 1, 2, "v") for _ in range(right_size)]
            ir = score(rows)
            graph = factors.factorize(ir, context(), LANE)
            forbidden = [edges(graph)[0]]
            n = sum(not set(forbidden).intersection(map(tuple, a["links"])) for a in observe(ir, context(), LANE)["assignments"])
            self.assertEqual(factors.query(graph, forbidden_links=forbidden)["possible_assignments"], str(n))

    def test_fresh_ir_graph_query_json_roundtrip_and_witness(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        span = context()
        graph = factors.factorize(ir, span, LANE)
        self.assertTrue(factors.validate_graph(json.loads(json.dumps(graph)), ir=ir, span=span, lane=LANE))
        result = factors.query(graph, required_links=[("s0", "s1")])
        result = json.loads(json.dumps(result))
        self.assertTrue(factors.validate_query(graph, result, required_links=[("s0", "s1")]))
        witness = factors.materialize_witness(graph, result)
        self.assertEqual(witness["assignment"]["legacy_geometry_id"], "vpaths_" + token([LANE, span, [["s0", "s1"]]]))
        self.assertTrue(witness["assignment"]["completion_id"].startswith("vfcompletion_"))
        self.assertEqual(witness["assignment"]["assignment_id"], witness["assignment"]["completion_id"])
        self.assertIsNone(witness["assignment"]["local_choice_indices"])
        self.assertFalse(witness["existing_assignment_inventory_inserted"])
        self.assertFalse(witness["may_be_combined_with_other_query_witnesses"])
        self.assertEqual(witness["query_ref"]["record_sha256"], result["record_sha256"])

    def test_tampered_and_resealed_graph_counts_or_endpoint_inventory_fail(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        bad = deepcopy(graph)
        bad["possible_assignments"] = "1"
        with self.assertRaisesRegex(ValueError, "invalid_record_seal"):
            factors.query(bad)
        for change in [lambda x: x.update(possible_assignments="1"),
                       lambda x: x["factors"][0]["target_refs"].clear(),
                       lambda x: x["events"].pop(),
                       lambda x: x.update(selected_assignment="invented-winner")]:
            bad = deepcopy(graph)
            change(bad)
            reseal(bad, "vfgraph_")
            with self.assertRaisesRegex(ValueError, "stored_graph_geometry_or_contract"):
                factors.query(bad)

    def test_source_binding_mutation_stale_context_and_lane_fail_fresh(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        graph = factors.factorize(ir, context(), LANE)
        for changed in [deepcopy(ir), deepcopy(ir)]:
            if changed["source_files"][0]["sha256"] == "a" * 64:
                changed["source_files"][0]["sha256"] = "b" * 64
            with self.assertRaisesRegex(ValueError, "stale_or_foreign"):
                factors.validate_graph(graph, ir=changed, span=context(), lane=LANE)
        bad = deepcopy(graph)
        bad["binding"]["ir_content_sha256"] = "0" * 64
        reseal(bad, "vfgraph_")
        with self.assertRaisesRegex(ValueError, "stale_or_foreign"):
            factors.validate_graph(bad, ir=ir, span=context(), lane=LANE)
        for span, lane in [(context(3), LANE), (context(), ("part1", "other"))]:
            with self.assertRaisesRegex(ValueError, "stale_or_foreign"):
                factors.validate_graph(graph, ir=ir, span=span, lane=lane)

    def test_resealed_query_and_cross_graph_results_fail_replay(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        result = factors.query(graph)
        for change in [lambda x: x.update(possible_assignments="1"),
                       lambda x: x["witness"]["links"].append(["s0", "s1"]),
                       lambda x: x.update(selected_assignment="preferred")]:
            bad = deepcopy(result)
            change(bad)
            reseal(bad, "vfquery_")
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                factors.materialize_witness(graph, bad)
        other = run([("C4", 0, 1, "v"), ("E4", 1, 2, "v")])
        with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
            factors.validate_query(other, result)

    def test_annotation_and_pitch_do_not_change_geometry_or_count(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        graph = factors.factorize(ir, context(), LANE)
        annotated = deepcopy(ir)
        annotated["annotations"] = [{"label": "V7/V", "voice": "best"}]
        annotated["phrases"] = [{"start": 0, "end": 1}]
        newer = factors.factorize(annotated, context(), LANE)
        self.assertNotEqual(newer["binding"]["ir_content_sha256"], graph["binding"]["ir_content_sha256"])
        self.assertEqual(newer["factors"], graph["factors"])
        self.assertEqual(newer["possible_assignments"], graph["possible_assignments"])
        annotated["sounding_events"][0]["pitch"] = {"unusable": "no pitch needed for geometry"}
        self.assertEqual(factors.factorize(annotated, context(), LANE)["factors"], graph["factors"])

    def test_immutability_all_inputs_and_returned_objects(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        before = deepcopy(ir)
        span, lane = context(), list(LANE)
        graph = factors.factorize(ir, span, lane)
        graph_before = deepcopy(graph)
        req = [["s0", "s1"]]
        result = factors.query(graph, required_links=req)
        result_before = deepcopy(result)
        witness = factors.materialize_witness(graph, result)
        witness["assignment"]["links"].clear()
        self.assertEqual(graph, graph_before)
        self.assertEqual(result, result_before)
        self.assertEqual(ir, before)
        self.assertEqual(req, [["s0", "s1"]])
        graph["events"][0]["pitch"].clear()
        self.assertEqual(ir, before)

    def test_missing_source_and_tie_traceability_hold_not_guessed(self):
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        ir["note_events"][0]["source_ref_id"] = "missing"
        ir["sounding_events"][1]["tie_chain_id"] = "missing-tie"
        graph = factors.factorize(ir, context(), LANE)
        self.assertIn("sampled_source_traceability_missing", graph["reasons"])
        self.assertIn("sampled_tie_chain_reference_missing", graph["reasons"])
        self.assertEqual(graph["missing_tie_chain_refs"], ["missing-tie"])
        self.assertEqual(len(graph["events"]), 2)

    def test_missing_foreign_attack_and_mismatched_tie_lineage_abstain(self):
        for attack in [None, "absent", "n1"]:
            ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
            ir["sounding_events"][0]["attack_note_id"] = attack
            graph = factors.factorize(ir, context(), LANE)
            self.assertIn("sampled_attack_source_lineage_invalid", graph["reasons"])
            self.assertEqual(graph["attack_lineage_mismatch_sound_refs"], ["s0"])
        ir = score([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        ir["sounding_events"][0]["tie_chain_id"] = "chain"
        ir["tie_chains"] = [{"tie_chain_id": "chain", "source_note_ids": ["n1"], "span": context(1)}]
        graph = factors.factorize(ir, context(), LANE)
        self.assertIn("sampled_tie_source_lineage_invalid", graph["reasons"])
        self.assertEqual(graph["tie_lineage_mismatch_sound_refs"], ["s0"])

    def test_identical_legacy_linkset_different_query_has_distinct_bound_completion(self):
        graph = run([("C4", 0, 1, "v"), ("D4", 1, 2, "v")])
        result1 = factors.query(graph)
        result2 = factors.query(graph, forbidden_links=edges(graph))
        first = factors.materialize_witness(graph, result1)["assignment"]
        second = factors.materialize_witness(graph, result2)["assignment"]
        self.assertEqual(first["legacy_geometry_id"], second["legacy_geometry_id"])
        self.assertNotEqual(first["completion_id"], second["completion_id"])

    def test_real_formal_xml_tie_keeps_all_source_notes_outside_context(self):
        with TemporaryDirectory() as directory:
            ir = make_ir(directory, [[event("C4", 0, 1, tie_role="start"),
                                       event("C4", 1, 1, tie_role="stop"), event("D4", 2, 1)]])
        lane = (ir["note_events"][0]["part_id"], ir["note_events"][0]["voice_id"])
        span = context(3, 1)
        graph = factors.factorize(ir, span, lane)
        self.assertEqual(graph["status"], "ready")
        self.assertTrue(factors.validate_graph(graph, ir=ir, span=span, lane=lane))
        tied = next(s for s in graph["events"] if len(s["source_note_ids"]) == 2)
        self.assertEqual(tied["span"]["start"], q(0))
        self.assertEqual(len(graph["source_note_events"]), 3)
        self.assertEqual(len(graph["tie_chains"]), 1)
        self.assertEqual(len(graph["source_references"]), 3)
        self.assertEqual(graph["total_observed_note_time"], q(2))
        result = factors.query(graph, required_links=edges(graph))
        witness = factors.materialize_witness(graph, result)
        self.assertEqual(len(witness["assignment"]["tracks"]), 1)
        self.assertEqual(graph["binding"]["source_files"], ir["source_files"])
        self.assertEqual(graph["binding"]["ir_content_sha256"], digest(ir))

    def test_invalid_budgets_identifiers_and_geometry_fail_explicitly(self):
        rows = [("C4", 0, 1, "v"), ("D4", 1, 2, "v")]
        for option in [dict(max_events=-1), dict(max_edges=True), dict(max_factors=1.5)]:
            with self.assertRaisesRegex(ValueError, "invalid_nonnegative_integer"):
                run(rows, **option)
        for lane in [None, (), ("part1", None), "part1/v"]:
            with self.assertRaisesRegex(ValueError, "explicit_raw"):
                factors.factorize(score(rows), context(), lane)
        graph = run(rows)
        with self.assertRaisesRegex(ValueError, "invalid_nonnegative_integer"):
            factors.query(graph, work_budget=True)
        for mutation in [lambda x: x["sounding_events"].append(deepcopy(x["sounding_events"][0])),
                         lambda x: x["sounding_events"][0]["span"].update(end=q(-1))]:
            ir = score(rows)
            mutation(ir)
            with self.assertRaises(ValueError):
                factors.factorize(ir, context(), LANE)


if __name__ == "__main__":
    unittest.main()
