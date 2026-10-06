"""One completion per hypothesis, exact time, no cross-witness exemption."""
from copy import deepcopy
from fractions import Fraction
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_musical_joint as joint
from musicanote_harness import factor_musical_view as views
from musicanote_harness import factor_musical_rules as rules
from musicanote_harness import harmony_factorized_voice_paths as factors
from musicanote_harness.musical_pattern_observation import digest, f, q
from test_harmony_factorized_voice_paths import score, context, LANE, edges
from test_musical_role_evidence import event, make_ir


def rule(rid, required=(), forbidden=(), *, alternatives=None, blockers=(), status="conditional_shape"):
    return {"rule_id": rid, "family": "explicit_test_clause", "involved_sound_refs": [], "note_refs": [],
            "explained_items": [], "prerequisites": {}, "blockers": list(blockers), "status": status,
            "alternatives": deepcopy(alternatives if alternatives is not None else [
                {"required_links": [list(x) for x in required], "forbidden_links": [list(x) for x in forbidden]}])}


def segment(sid, start, end, members="CEG", *, root="C", status="usable", blockers=()):
    return {"segment_id": sid, "span": {"start": q(start), "end": q(end)},
            "root": None if root is None else {"step": root, "alter": q(0)},
            "members": [{"step": step, "alter": q(0)} for step in members],
            "status": status, "blockers": list(blockers)}


PROVENANCE = {"kind": "caller_hypothesis", "engine_version": "joint-test-v1",
              "source_document_sha256": None, "source_path": None,
              "pitch_basis": "written_IR_not_concert_certified", "status": "hypothesis_not_gold"}


class FactorMusicalJointSolverTests(unittest.TestCase):
    def graph(self, rows=None):
        rows = rows or [("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 2, 3, "v")]
        return factors.factorize(score(rows), context(), LANE)

    def test_empty_requested_subset_has_one_no_link_completion_not_selected(self):
        graph = self.graph()
        result = joint.solve_joint(graph, [])
        self.assertEqual(result["status"], "joint_possible")
        self.assertEqual(result["possible_branch_count"], "1")
        self.assertEqual(result["branches"][0]["query"]["possible_assignments"], "4")
        self.assertEqual(result["branches"][0]["witness"]["assignment"]["links"], [])
        self.assertIsNone(result["possible_assignments_union"])
        self.assertFalse(result["branch_counts_may_be_summed"])
        self.assertFalse(result["witnesses_may_be_unioned"])
        self.assertFalse(result["nct_confirmed"])
        joint.validate_solution(result, graph, [])

    def test_individually_possible_branching_clauses_jointly_impossible(self):
        graph = self.graph([("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 1, 2, "v")])
        a, b = edges(graph)
        first, second = rule("a", [a]), rule("b", [b])
        self.assertEqual(joint.solve_joint(graph, [first])["status"], "joint_possible")
        self.assertEqual(joint.solve_joint(graph, [second])["status"], "joint_possible")
        result = joint.solve_joint(graph, [first, second])
        self.assertEqual(result["status"], "incompatible_joint_constraints")
        self.assertIn("required_branch_not_allowed", result["branches"][0]["query"]["reasons"])
        self.assertIsNone(result["branches"][0]["witness"])

    def test_OR_is_not_flattened_into_AND_and_conflicting_branch_retained(self):
        graph = self.graph([("C4", 0, 1, "v"), ("D4", 1, 2, "v"), ("E4", 1, 2, "v")])
        a, b = edges(graph)
        alternatives = [{"required_links": [list(p)], "forbidden_links": []} for p in (a, b)]
        requested = [rule("OR", alternatives=alternatives), rule("only-a", [a])]
        result = joint.solve_joint(graph, requested)
        self.assertEqual(result["status"], "joint_possible")
        self.assertEqual([r["query"]["status"] for r in result["branches"]],
                         ["exact_count", "unsatisfiable_constraints"])
        self.assertEqual(result["branches"][0]["witness"]["assignment"]["links"], [list(a)])
        self.assertEqual(result["requested_rules"], requested)

    def test_overlapping_OR_counts_are_retained_separately_never_summed(self):
        graph = self.graph()
        alternatives = [{"required_links": [], "forbidden_links": []},
                        {"required_links": [list(edges(graph)[0])], "forbidden_links": []}]
        result = joint.solve_joint(graph, [rule("OR", alternatives=alternatives)])
        self.assertEqual([b["query"]["possible_assignments"] for b in result["branches"]], ["4", "2"])
        self.assertIsNone(result["possible_assignments_union"])

    def test_branch_budget_holds_entire_OR_product_before_any_query(self):
        graph = self.graph()
        alternatives = [{"required_links": [], "forbidden_links": []}] * 2
        requested = [rule("a", alternatives=alternatives), rule("b", alternatives=alternatives)]
        with patch.object(factors, "query", side_effect=AssertionError("no partial branch evaluation")):
            result = joint.solve_joint(graph, requested, branch_budget=3)
        self.assertEqual(result["possible_branch_count"], "4")
        self.assertEqual(result["status"], "unassessed")
        self.assertEqual(result["branches"], [])
        self.assertEqual(result["requested_rules"], requested)

    def test_withheld_clause_holds_entire_requested_conjunction(self):
        graph = self.graph()
        requested = [rule("unknown", blockers=["consonance_not_assessed"], status="withheld")]
        with patch.object(factors, "query", side_effect=AssertionError("no query on withheld rule")):
            result = joint.solve_joint(graph, requested)
        self.assertEqual(result["status"], "unassessed")
        self.assertEqual(result["withheld_requested_rule_refs"], ["unknown"])

    def test_one_DP_abstention_does_not_become_partial_success(self):
        graph = self.graph([("C4", 0, 1, "v"), ("G4", 0, 1, "v"),
                            ("D4", 1, 2, "v"), ("A4", 1, 2, "v")])
        alternatives = [{"required_links": [], "forbidden_links": []},
                        {"required_links": [], "forbidden_links": [list(edges(graph)[0])]}]
        result = joint.solve_joint(graph, [rule("OR", alternatives=alternatives)], work_budget=0)
        self.assertEqual([b["query"]["status"] for b in result["branches"]], ["exact_count", "abstention"])
        self.assertEqual(result["status"], "unassessed")
        self.assertFalse(result["all_requested_branches_assessed"])
        self.assertIsNotNone(result["branches"][0]["witness"])

    def test_dangling_and_transitive_only_direct_refs_are_unknown_not_unsat(self):
        graph = self.graph()
        a, b = edges(graph)
        chain = joint.solve_joint(graph, [rule("chain", [a, b])])
        self.assertEqual(chain["status"], "joint_possible")
        self.assertEqual(len(chain["branches"][0]["witness"]["assignment"]["tracks"]), 1)
        for wrong in [(a[0], b[1]), (a[0], "missing")]:
            result = joint.solve_joint(graph, [rule("direct", [wrong])])
            self.assertEqual(result["status"], "unassessed")
            self.assertEqual(result["branches"][0]["query"]["status"], "invalid_constraints")

    def test_required_forbidden_merge_conflicts_are_unsat(self):
        graph = self.graph([("C4", 0, 1, "v"), ("G4", 0, 1, "v"), ("D4", 1, 2, "v")])
        a, b = edges(graph)
        for requested in [[rule("both", [a], [a])], [rule("merge", [a, b])]]:
            result = joint.solve_joint(graph, requested)
            self.assertEqual(result["status"], "incompatible_joint_constraints")

    def test_graph_abstention_never_counts_requested_clauses(self):
        graph = factors.factorize(score([("C4", 0, 1, "v")]), context(), LANE, max_events=0)
        self.assertEqual(joint.solve_joint(graph, [rule("empty")])["status"], "unassessed")

    def test_duplicate_rule_ids_and_bad_budgets_fail_closed(self):
        graph = self.graph()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            joint.solve_joint(graph, [rule("same"), rule("same")])
        for value in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                joint.solve_joint(graph, [], branch_budget=value)

    def test_fresh_replay_tamper_and_input_immutability(self):
        graph = self.graph()
        requested = [rule("a", [edges(graph)[0]])]
        before = deepcopy((graph, requested))
        result = joint.solve_joint(graph, requested)
        self.assertEqual(result, joint.solve_joint(graph, requested))
        self.assertEqual((graph, requested), before)
        bad = deepcopy(result)
        bad["branches"][0]["query"]["possible_assignments"] = "999"
        bad = views.seal({k: v for k, v in bad.items() if k not in ("record_id", "record_sha256")}, "fmjs_")
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            joint.validate_solution(bad, graph, requested)

    def test_tuple_direct_edges_roundtrip_to_JSON_preserve_exact_replay(self):
        graph = self.graph()
        requested = [rule("tuple")]
        requested[0]["alternatives"][0]["required_links"] = (edges(graph)[0],)
        before = deepcopy(requested)
        result = joint.solve_joint(graph, requested)
        stored = json.loads(json.dumps(result))
        self.assertEqual(result, stored)
        self.assertTrue(joint.validate_solution(stored, graph, requested))
        self.assertEqual(requested, before)


class FactorMusicalJointComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, lanes, segments=None, *, span=None, lane_index=0):
        from test_factor_musical_view import make_view
        extent = span or context()
        finish = f(extent["end"])
        padded = deepcopy(lanes)
        for lane in padded:
            end = max(e["onset"] + e["duration"] for e in lane)
            if end < finish:
                lane.append(event(None, end, finish - end))
        ir = make_ir(self.temp.name, padded)
        # This fixture importer ends score duration at the final sounding
        # note, excluding a trailing rest. Retain the literal rest horizon
        # explicitly for this synthetic context; no source note is repaired.
        ir["score"]["duration_quarters"] = q(max(f(ir["score"]["duration_quarters"]), finish))
        view = make_view(ir, extent)
        original = next(n for n in ir["note_events"] if n["part_id"] == ir["parts"][lane_index]["part_id"])
        active_lane = [original["part_id"], original["voice_id"]]
        graph = factors.factorize(ir, extent, active_lane)
        path = views.make_path(view, segments or [segment("hold", 0, 4)], PROVENANCE)
        compiled = rules.compile_rules(view, path, graph)
        return ir, view, graph, path, compiled

    def completion(self, graph, links=()):
        query = factors.query(graph, required_links=links)
        return query, factors.materialize_witness(graph, query)

    def account(self, view, graph, paths, compilations, links=()):
        query, witness = self.completion(graph, links)
        return joint.compare_under_completion(view, paths, graph, query, witness, compilations)

    def test_passing_exact_account_and_fresh_replay(self):
        ir, view, graph, path, compiled = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        query, witness = self.completion(graph, edges(graph))
        before = deepcopy((ir, view, graph, path, compiled, query, witness))
        record = joint.compare_under_completion(view, [path], graph, query, witness, [compiled])
        account = record["accounts"][0]
        self.assertEqual(account["note_time"], {"member": q(2), "conditional_explained": q(1),
                         "unexplained": q(0), "unknown": q(0), "unsupported": q(0)})
        self.assertEqual(account["raw_note_time"], {"member": q(2), "nonmember": q(1), "unknown": q(0)})
        joint.validate_comparison(record, view, [path], graph, query, witness, [compiled])
        self.assertEqual((ir, view, graph, path, compiled, query, witness), before)
        middle = next(item for item in account["items"] if item["slot"]["pitch"]["step"] == "D")
        self.assertEqual(middle["category"], "conditional_explained")
        self.assertTrue(middle["conditional_rule_refs"])
        self.assertEqual(middle["slot"]["relative_pitch"]["written_root_relative_generic_degree"], 2)
        self.assertEqual(middle["slot"]["octave"], 4)
        self.assertEqual(middle["slot"]["original_sounding_duration"], q(1))
        self.assertTrue(middle["slot"]["source_reference_snapshots"])
        self.assertEqual(middle["slot"]["key"], "unassessed")
        self.assertFalse(record["harmony_confirmed"])
        self.assertFalse(record["nct_confirmed"])
        self.assertEqual(record["deltas"], [])

    def test_no_link_and_required_link_accounts_do_not_union(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        absent = self.account(view, graph, [path], [compiled])
        present = self.account(view, graph, [path], [compiled], edges(graph))
        self.assertEqual(absent["accounts"][0]["note_time"]["unexplained"], q(1))
        self.assertEqual(present["accounts"][0]["note_time"]["conditional_explained"], q(1))
        self.assertEqual(absent["accounts"][0]["raw_note_time"], present["accounts"][0]["raw_note_time"])
        statuses = {r["status"] for r in absent["accounts"][0]["rule_assessments"]}
        self.assertIn("not_satisfied_under_this_completion_not_global_absence", statuses)
        self.assertNotEqual(absent["shared_completion_ref"], present["shared_completion_ref"])

    def test_all_part_denominator_and_other_lane_nonmembers_preserved(self):
        _, view, graph, path, compiled = self.fixture([
            [event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)], [event("D3", 0, 4)]])
        record = self.account(view, graph, [path], [compiled], edges(graph))
        self.assertEqual(record["total_all_part_note_time"], q(7))
        self.assertEqual(record["sampled_evaluation_note_time"], q(3))
        account = record["accounts"][0]
        self.assertEqual(account["note_time"]["conditional_explained"], q(1))
        self.assertEqual(account["note_time"]["unexplained"], q(4))
        self.assertEqual(account["raw_note_time"]["nonmember"], q(5))
        self.assertTrue(all(item["category"] == "unexplained" and not item["conditional_rule_refs"]
                            for item in account["items"] if item["slot"]["octave"] == 3))
        self.assertTrue(all(row["structural_bass"] == "unassessed" for row in record["observed_lowest"]))

    def test_shared_grid_same_members_split_hold_invariance_not_accuracy(self):
        _, view, graph, hold, first = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        split = views.make_path(view, [segment("left", 0, Fraction(3, 2)),
                                      segment("right", Fraction(3, 2), 4)], PROVENANCE)
        second = rules.compile_rules(view, split, graph)
        record = self.account(view, graph, [hold, split], [first, second], edges(graph))
        a, b = record["accounts"]
        self.assertEqual(a["note_time"], b["note_time"])
        self.assertEqual(a["raw_note_time"], b["raw_note_time"])
        self.assertEqual([i["item_id"] for i in a["items"]], [i["item_id"] for i in b["items"]])
        self.assertEqual(len({i["item_id"] for i in a["items"]}), len(a["items"]))
        self.assertEqual(record["deltas"][0]["boundary_count_delta"], 1)
        self.assertTrue(all(f(t) == 0 for t in record["deltas"][0]["note_time_delta_second_minus_first"].values()))
        self.assertIsNone(record["deltas"][0]["preferred"])

    def test_two_harmony_paths_compared_under_one_completion(self):
        _, view, graph, first, compiled1 = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        second = views.make_path(view, [segment("all-members", 0, 4, "CDE", root="D")], PROVENANCE)
        compiled2 = rules.compile_rules(view, second, graph)
        record = self.account(view, graph, [first, second], [compiled1, compiled2], edges(graph))
        self.assertEqual(record["accounts"][0]["raw_note_time"]["nonmember"], q(1))
        self.assertEqual(record["accounts"][1]["raw_note_time"]["nonmember"], q(0))
        self.assertEqual(record["deltas"][0]["shared_completion_ref"], record["shared_completion_ref"])
        self.assertEqual(record["deltas"][0]["raw_note_time_delta_second_minus_first"]["member"], q(1))

    def test_fractional_duration_note_time_is_exact(self):
        third = Fraction(1, 3)
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, third),
                    event("D4", third, third), event("E4", 2 * third, third)]])
        record = self.account(view, graph, [path], [compiled], edges(graph))
        self.assertEqual(record["total_all_part_note_time"], q(1))
        self.assertEqual(record["accounts"][0]["note_time"]["conditional_explained"], q(third))
        self.assertEqual(sum(map(f, record["accounts"][0]["note_time"].values()), Fraction()), 1)

    def test_held_anticipation_explains_prefix_only_without_reattack(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 3)]],
            [segment("before", 0, 1, "FAD", root="F"), segment("after", 1, 4)])
        record = self.account(view, graph, [path], [compiled])
        account = record["accounts"][0]
        self.assertEqual(account["note_time"]["conditional_explained"], q(1))
        self.assertEqual(account["note_time"]["member"], q(2))
        self.assertEqual(record["sampled_evaluation_note_time"], q(3))
        held = [r for r in account["rule_assessments"] if r["family"] == "anticipation_held"]
        self.assertEqual(held[0]["status"], "conditional_shape_under_shared_completion")
        self.assertTrue(held[0]["rule"]["prerequisites"]["actually_held_same_sound"])
        self.assertFalse(record["pedal_confirmed"])

    def test_prepared_suspension_stays_withheld_no_nonmember_exemption(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 2), event("B3", 2, 1)]],
            [segment("before", 0, 1), segment("after", 1, 4, "GBDF", root="G")])
        record = self.account(view, graph, [path], [compiled], edges(graph))
        account = record["accounts"][0]
        self.assertEqual(account["note_time"]["unexplained"], q(1))
        self.assertEqual(account["note_time"]["conditional_explained"], q(0))
        suspension = next(r for r in account["rule_assessments"] if r["family"] == "prepared_held_suspension")
        self.assertEqual(suspension["status"], "withheld_prerequisites")
        self.assertIn("accent_not_verified", suspension["blockers"])

    def test_broken_chord_role_does_not_consume_or_certify_note_time(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 1), event("E4", 1, 1), event("G4", 2, 1)]])
        record = self.account(view, graph, [path], [compiled], edges(graph))
        account = record["accounts"][0]
        broken = next(r for r in account["rule_assessments"] if r["family"] == "broken_chord_shape")
        self.assertEqual(broken["status"], "conditional_shape_under_shared_completion")
        self.assertEqual(broken["rule"]["explained_items"], [])
        self.assertEqual(account["note_time"]["member"], q(3))
        self.assertEqual(account["note_time"]["conditional_explained"], q(0))
        self.assertFalse(record["arpeggio_confirmed"])
        self.assertFalse(record["alternative_roles_selected"])

    def test_blocked_segment_preserves_raw_membership_but_no_credit(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]],
            [segment("blocked", 0, 4, status="blocked", blockers=["candidate_root_unassessed"])])
        record = self.account(view, graph, [path], [compiled], edges(graph))
        account = record["accounts"][0]
        self.assertEqual(account["raw_note_time"], {"member": q(2), "nonmember": q(1), "unknown": q(0)})
        self.assertEqual(account["note_time"]["unsupported"], q(3))
        self.assertTrue(all(not item["conditional_rule_refs"] for item in account["items"]))

    def test_compilation_budget_is_complete_abstention_not_empty_evidence(self):
        _, view, graph, path, _ = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        held = rules.compile_rules(view, path, graph, max_candidates=0)
        record = self.account(view, graph, [path], [held], edges(graph))
        self.assertEqual(held["status"], "candidate_budget_abstention")
        self.assertEqual(record["accounts"][0]["note_time"]["unsupported"], q(3))
        self.assertEqual(record["accounts"][0]["raw_note_time"]["nonmember"], q(1))

    def test_foreign_query_completion_and_resealed_rule_tamper_fail_closed(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        query, witness = self.completion(graph, edges(graph))
        other_query, other_witness = self.completion(graph)
        with self.assertRaisesRegex(ValueError, "one_exact"):
            joint.compare_under_completion(view, [path], graph, query, other_witness, [compiled])
        bad = deepcopy(compiled)
        bad["rules"][0]["explained_items"] = [{"sound_id": view["sounds"][0]["sound_id"], "span": context()}]
        bad = views.seal({k: v for k, v in bad.items() if k not in ("record_id", "record_sha256")}, "fmcr_")
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            joint.compare_under_completion(view, [path], graph, query, witness, [bad])
        wrong = deepcopy(graph)
        wrong["binding"]["ir_content_sha256"] = "c" * 64
        wrong = factors._seal({k: v for k, v in wrong.items() if k not in ("record_id", "record_sha256")}, "vfgraph_")
        with self.assertRaises(ValueError):
            joint.compare_under_completion(view, [path], wrong, query, witness, [compiled])

    def test_source_clock_pass_pitch_mismatch_withholds_only_affected_sound(self):
        from test_factor_musical_view import make_view
        ir, _, _, _, _ = self.fixture([
            [event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)], [event("C3", 0, 4)]])
        note = next(n for n in ir["note_events"] if n["written_pitch"]["spelling"] == "C4")
        note["written_pitch"] = {**deepcopy(note["written_pitch"]), "octave": 5,
                                 "spelling": "C5", "midi_pitch": 72}
        view = make_view(ir, context())
        graph = factors.factorize(ir, context(), [note["part_id"], note["voice_id"]])
        path = views.make_path(view, [segment("hold", 0, 4)], PROVENANCE)
        compiled = rules.compile_rules(view, path, graph)
        record = self.account(view, graph, [path], [compiled], edges(graph))
        account = record["accounts"][0]
        affected = [item for item in account["items"] if item["slot"]["pitch"]["spelling"] == "C4"]
        self.assertTrue(all(i["slot"]["source_clock_passed"] for i in affected))
        self.assertTrue(all(not i["slot"]["source_pitch_consistency_passed"] for i in affected))
        self.assertTrue(all(i["category"] == "unsupported" for i in affected))
        self.assertEqual(account["note_time"]["unsupported"], q(1))
        self.assertEqual(account["note_time"]["member"], q(5))
        self.assertEqual(account["note_time"]["unexplained"], q(1))
        self.assertEqual(account["note_time"]["conditional_explained"], q(0))
        self.assertEqual(account["raw_note_time"], {"member": q(6), "nonmember": q(1), "unknown": q(0)})
        self.assertTrue(all(not i["conditional_rule_refs"] for i in affected))

    def test_attack_continuation_origin_is_not_hidden_by_continuous_coverage(self):
        _, view, graph, path, compiled = self.fixture([
            [event("C4", 0, 1), event("D4", 1, 1, tie_role="stop"), event("E4", 2, 1)],
            [event("C3", 0, 4)]])
        record = self.account(view, graph, [path], [compiled], edges(graph))
        account = record["accounts"][0]
        middle = next(i for i in account["items"] if i["slot"]["pitch"]["step"] == "D")
        self.assertFalse(middle["slot"]["source_clock_passed"])
        self.assertIn("source_clock_guard_not_passed", middle["blockers"])
        self.assertEqual(middle["category"], "unsupported")
        self.assertEqual(account["note_time"]["unsupported"], q(1))
        self.assertEqual(account["note_time"]["member"], q(6))

    def test_other_lane_grace_point_retained_not_counted_or_promoted(self):
        _, view, graph, path, compiled = self.fixture([
            [event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)],
            [event("C3", 0, 4), event("D3", 1, 0, grace=True)]])
        self.assertEqual(graph["status"], "ready")
        record = self.account(view, graph, [path], [compiled], edges(graph))
        self.assertEqual(len(record["point_observations"]), 1)
        self.assertEqual(record["total_all_part_note_time"], q(7))
        self.assertEqual(record["accounts"][0]["note_time"]["conditional_explained"], q(1))
        self.assertFalse(record["nct_confirmed"])

    def test_valid_clipped_span_does_not_bypass_full_source_clock_guard(self):
        from test_factor_musical_view import make_view
        ir, _, _, _, _ = self.fixture([[event("C4", 0, 1, tie_role="start"),
            event("C4", 1, 1, tie_role="continue"), event("C4", 2, 1, tie_role="stop")]])
        sound = ir["sounding_events"][0]
        self.assertEqual(len(sound["source_note_ids"]), 3)
        last = next(n for n in ir["note_events"] if n["note_id"] == sound["source_note_ids"][-1])
        last["notated_duration_quarter"] = q(Fraction(1, 2))
        view = make_view(ir, context(1))
        first = ir["note_events"][0]
        graph = factors.factorize(ir, context(1), [first["part_id"], first["voice_id"]])
        path = views.make_path(view, [segment("clip", 0, 1)], PROVENANCE)
        compiled = rules.compile_rules(view, path, graph)
        record = self.account(view, graph, [path], [compiled])
        self.assertEqual(record["total_all_part_note_time"], q(1))
        self.assertEqual(record["accounts"][0]["note_time"]["unsupported"], q(1))
        self.assertEqual(record["accounts"][0]["raw_note_time"]["member"], q(1))
        item = record["accounts"][0]["items"][0]
        self.assertEqual(item["slot"]["original_sounding_duration"], q(3))
        self.assertEqual(len(item["slot"]["tie_chain_snapshot"]["source_note_ids"]), 3)

    def test_resealed_duplicate_explanation_rule_cannot_multiply_time(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        bad = deepcopy(compiled)
        existing = next(r for r in bad["rules"] if r["status"] == "conditional_shape")
        duplicate = deepcopy(existing)
        duplicate["rule_id"] += "-duplicate"
        bad["rules"].append(duplicate)
        bad = views.seal({k: v for k, v in bad.items() if k not in ("record_id", "record_sha256")}, "fmcr_")
        query, witness = self.completion(graph, edges(graph))
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            joint.compare_under_completion(view, [path], graph, query, witness, [bad])

    def test_comparison_output_reseal_tamper_fresh_replay_fails(self):
        _, view, graph, path, compiled = self.fixture([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 1)]])
        query, witness = self.completion(graph, edges(graph))
        record = joint.compare_under_completion(view, [path], graph, query, witness, [compiled])
        record["accounts"][0]["note_time"]["conditional_explained"] = q(100)
        bad = views.seal({k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}, "fmcmp_")
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            joint.validate_comparison(bad, view, [path], graph, query, witness, [compiled])

    def test_declared_duration_conflict_preserves_declared_and_span_duration(self):
        from test_factor_musical_view import make_view
        ir, _, _, _, _ = self.fixture([[event("C4", 0, 2)]])
        ir["sounding_events"][0]["sounding_duration"] = q(9)
        view = make_view(ir, context())
        first = ir["note_events"][0]
        graph = factors.factorize(ir, context(), [first["part_id"], first["voice_id"]])
        path = views.make_path(view, [segment("hold", 0, 4)], PROVENANCE)
        compiled = rules.compile_rules(view, path, graph)
        record = self.account(view, graph, [path], [compiled])
        item = record["accounts"][0]["items"][0]
        self.assertEqual(item["slot"]["original_sounding_duration"], q(9))
        self.assertEqual(item["slot"]["span_duration"], q(2))
        self.assertEqual(item["category"], "unsupported")
        self.assertEqual(record["total_all_part_note_time"], q(2))


if __name__ == "__main__":
    unittest.main()
