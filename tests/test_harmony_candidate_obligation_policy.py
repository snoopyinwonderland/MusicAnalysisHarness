"""Genuine small XML/native fixtures, not corpus accuracy or human gold."""
from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import harmony_candidate_obligation_policy as policy
from musicanote_harness import native_progression_contrast as parent
from musicanote_harness import progression_evidence_review as review
from musicanote_harness import factor_native_role_explanations as roles
from musicanote_harness import factor_interval_lattice as native
from musicanote_harness import factor_expanded_hypotheses as kernels
from musicanote_harness.musical_pattern_observation import digest, f, q
import test_native_progression_contrast as factory
import test_factor_native_role_explanations as fixtures
from test_factor_expanded_hypotheses import span, event


class ObligationPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory.SavedProgressionContrastTests.setUpClass()
        cls.addClassCleanup(factory.SavedProgressionContrastTests.doClassCleanups)
        cls.fixture = factory.SavedProgressionContrastTests()
        cls.cache = {}

    def packet(self, name="ordinary", *, control=False, unknown=False, disconnect_seventh=False):
        cache_key = name, control, unknown, disconnect_seventh
        if cache_key not in self.cache:
            fx = self.fixture.fixture
            seven = fx.selector(name, unknown=unknown)
            triad = fx.selector(name, unknown=unknown, partitions=[
                (span(0, 2), ("G", Fraction()), fixtures.members("G", "B", "D")),
                (span(2, 4), ("C", Fraction()), fixtures.members("C", "E", "G"))],
                assumptions=[{"family": "V", "quality": "M"}])
            scope, lattice = fx.case(name)[0][1], fx.record(name)
            required = fx.links(name)[:3] + fx.links(name)[4:] if disconnect_seventh else None
            session, comparison, bundle = fx.comparison(name, control=control, required=required, selectors=[triad, seven])
            explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
            entries = [{"native_path": p, "role_path": r,
                "comparison_ref": kernels._ref(comparison), "explanation_ref": kernels._ref(explained)}
                for p, r in zip(comparison["paths"], explained["paths"])]
            bundles = {bundle["record_id"]: bundle}
            result = parent.compare(scope, lattice, entries, bundles=bundles)
            keys = {k["record_id"]: k for k in lattice["keys"]}
            rows = [{"original_selector_index": i, "review": review.review_facet(facet, keys[facet["key_ref"]["record_id"]])}
                    for i, facet in enumerate(result["facets"])]
            self.cache[cache_key] = rows, scope, bundles
        return deepcopy(self.cache[cache_key])

    def result(self, *args, **kwargs):
        return policy.compare_candidates(*self.packet(*args, **kwargs))

    def test_extra_member_is_not_deleted_or_automatically_NCT(self):
        result = self.result()
        pair = result["extension_pairs"][0]
        self.assertEqual(pair["extra_member"]["step"], "F")
        self.assertEqual(f(pair["additional_member_source_time_quarters"]), 2)
        self.assertEqual(f(pair["triad_additional_member_unexplained_quarters"]), 2)
        self.assertFalse(pair["fewer_obligations_selects_triad"])
        self.assertFalse(pair["extra_member_presence_selects_seventh"])
        self.assertIsNone(pair["selected"])

    def test_supported_leading_role_does_not_displace_seventh(self):
        result = self.result()
        self.assertEqual(result["summary"]["supported_leading_tone_contexts"], 2)
        self.assertEqual(result["summary"]["supported_seventh_contexts"], 1)
        self.assertEqual(len(result["candidate_paths"]), 2)
        self.assertTrue(all(p["harmony_confirmed"] is False for p in result["candidate_paths"]))

    def test_function_changes_are_explicit_not_fixed_premise(self):
        delta = self.result()["extension_pairs"][0]["transition_differences"][0]
        self.assertEqual(delta["triad_assumption"]["family"], "V")
        self.assertEqual(delta["seventh_assumption"]["family"], "V7")

    def test_no_link_is_strategy_gap_not_global_harmony_rejection(self):
        result = self.result(control=True)
        failures = [f for p in result["candidate_paths"] for r in p["ordinary_role_diagnostics"] for f in r["failed_occurrences"]]
        self.assertTrue(all(f["kind"] == "disconnected_in_this_witness" for f in failures))
        self.assertTrue(all(f["ordinary_strategy_failure_rejects_harmony"] is False for f in failures))
        self.assertFalse(result["extension_pairs"][0]["ordinary_failure_eliminates_seventh"])

    def test_adverse_first_change_is_not_skipped(self):
        result = self.result("ordinary_first_adverse")
        failed = result["candidate_paths"][1]["ordinary_role_diagnostics"][0]["failed_occurrences"][0]
        self.assertTrue(failed["failure_axes"]["adverse_first_changed_motion"])
        self.assertTrue(failed["failure_axes"]["endpoint_outside_target_or_nonmember"])
        self.assertEqual(failed["reappearance_probes"], [])

    def test_reappearance_downstream_route_does_not_bridge_original_gap(self):
        result = self.result("ordinary_reattack", disconnect_seventh=True)
        role = result["candidate_paths"][1]["ordinary_role_diagnostics"][1]
        failure = role["failed_occurrences"][0]
        self.assertFalse(role["supported_under_this_completion"])
        self.assertEqual(failure["kind"], "disconnected_in_this_witness")
        self.assertTrue(any(p["downstream_ordinary_seventh_shape_under_this_target"] for p in failure["reappearance_probes"]))
        self.assertTrue(all(p["connection_from_original_occurrence_proven"] is False
                            and p["resolution_credit_added"] is False for p in failure["reappearance_probes"]))

    def test_microtonal_spelling_is_retained_not_coerced(self):
        rows, _, _ = self.packet()
        slot = deepcopy(rows[1]["review"]["slots"][0])
        slot["members"][1]["alter"] = q(Fraction(1, 2))
        self.assertEqual(policy.chord_shape(slot)["kind"], "unsupported_spelling_or_microtone")

    def test_explicit_rest_gap_is_not_invented_as_voice_connection(self):
        # A fresh MusicXML/Core fixture with an actual rest, not a mutated
        # archive. Only the later F->E and B->C links enter the witness.
        fx = self.fixture.fixture.factory.fixture([
            [event("B4", 0, 2), event("C5", 2, 2)],
            [event("F4", 0, 2), event(None, 2, Fraction(1, 2)),
             event("F4", Fraction(5, 2), Fraction(1, 2)), event("E4", 3, 1)],
            [event(["G3", "D4"], 0, 2), event(["C3", "E3", "G3"], 2, 2)]],
            signatures=[{"fifths": 0, "mode_hint": None}])
        scope, lattice = fx[1], native.build_lattice(*fx)
        origin_ids = []
        for extent, root, names in ((span(0, 2), "G", ("G", "B", "D", "F")), (span(2, 4), "C", ("C", "E", "G"))):
            catalog = next(c for c in lattice["catalog_inventory"] if c["span"] == extent)
            origin = next(o for o in catalog["origins"] if o["root"] is not None and o["root"]["step"] == root
                and o["members"] is not None and {kernels._pitch_key(p) for p in o["members"]} == fixtures.members(*names))
            origin_ids.append(origin["record_id"])
        def sound(step, onset):
            return next(s["sound_ref"] for s in scope["sound_facts"] if s["pitch"]["step"] == step
                        and s["pitch"]["octave"] in (4, 5) and f(s["span"]["start"]) == onset)
        session = native.prepare_lattice(*fx, lattice)
        bundle = native.compile_bundle_prepared(session, [[sound("B", 0), sound("C", 2)],
                                                        [sound("F", Fraction(5, 2)), sound("E", 3)]])
        key = next(k for k in lattice["keys"] if k["segments"][0]["mode"] == "major")
        selector = {"origin_ids": origin_ids, "key_id": key["record_id"], "transition_assumptions": [{"family": "V7", "quality": "M"}]}
        comparison = native.compare_prepared(session, [selector], bundle["record_id"])
        explained = roles.explain_prepared(roles.prepare_explanations(session, comparison), query_work_budget=100000000)
        entry = {"native_path": comparison["paths"][0], "role_path": explained["paths"][0],
                 "comparison_ref": kernels._ref(comparison), "explanation_ref": kernels._ref(explained)}
        facet = parent.compare(scope, lattice, [entry], bundles={bundle["record_id"]: bundle})["facets"][0]
        result = policy.compare_candidates([{"original_selector_index": 0, "review": review.review_facet(facet, key)}],
                                           scope, {bundle["record_id"]: bundle})
        seventh = result["candidate_paths"][0]["ordinary_role_diagnostics"][1]
        probe = seventh["failed_occurrences"][0]["reappearance_probes"][0]
        self.assertEqual(probe["unconnected_interval"], span(2, Fraction(5, 2)))
        self.assertTrue(probe["downstream_ordinary_seventh_shape_under_this_target"])
        self.assertFalse(probe["connection_from_original_occurrence_proven"])
        self.assertFalse(seventh["supported_under_this_completion"])

    def test_actual_reattack_chain_not_labelled_tie(self):
        result = self.result("ordinary_reattack")
        role = result["candidate_paths"][1]["ordinary_role_diagnostics"][1]
        self.assertTrue(role["supported_under_this_completion"])
        self.assertTrue(all(o["tie_chain_ref"] is None for o in result["extension_pairs"][0]["additional_member_occurrences"]))

    def test_unknown_key_holds_even_with_supported_motion(self):
        result = self.result(unknown=True)
        self.assertTrue(all(p["path_evidence_axes"]["explicit_key_coordinate_available"] is False for p in result["candidate_paths"]))
        self.assertTrue(all(p["status"] == "held_path_evidence" for p in result["candidate_paths"]))

    def test_full_hold_does_not_need_vacuous_internal_function(self):
        scope, lattice, entries, bundles = self.fixture.inputs("single", "single")
        facet = parent.compare(scope, lattice, entries, bundles=bundles)["facets"][0]
        key = next(k for k in lattice["keys"] if k["record_id"] == facet["key_ref"]["record_id"])
        result = policy.compare_candidates([{"original_selector_index": 0, "review": review.review_facet(facet, key)}], scope, bundles)
        path = result["candidate_paths"][0]
        self.assertTrue(path["no_internal_transition_is_not_hold_failure"])
        self.assertIsNone(path["path_evidence_axes"]["all_internal_relations_conditionally_supported"])
        self.assertEqual(path["status"], "conditional_path_evidence_complete_not_selected")
        self.assertFalse(path["harmony_confirmed"])

    def test_no_cross_completion_or_cross_key_pair(self):
        rows, scope, bundles = self.packet()
        other, _, more = self.packet(control=True)
        combined = [rows[0], {**other[1], "original_selector_index": 1}]
        self.assertEqual(policy.compare_candidates(combined, scope, {**bundles, **more})["extension_pairs"], [])
        other, _, _ = self.packet(unknown=True)
        self.assertEqual(policy.compare_candidates([rows[0], other[1]], scope, bundles)["extension_pairs"], [])

    def test_no_mutation_or_producer_calls(self):
        packet = self.packet(); before = digest(packet)
        with patch.object(native, "compare_prepared", side_effect=AssertionError("replay")), \
             patch.object(roles, "explain_prepared", side_effect=AssertionError("replay")):
            policy.compare_candidates(*packet)
        self.assertEqual(before, digest(packet))

    def test_budget_is_whole_not_prefix_and_boolean_rejected(self):
        with self.assertRaisesRegex(ValueError, "no_prefix"):
            policy.compare_candidates(*self.packet(), max_pairs=0)
        with self.assertRaises(ValueError):
            policy.compare_candidates(*self.packet(), max_pairs=True)

    def test_literal_note_duration_or_tie_corruption_rejected(self):
        for key, value in (("source_note_time_quarters", q(99)), ("observations", [])):
            packet = self.packet()
            packet[0][1]["review"]["slots"][0]["member_observations"][-1][key] = value
            with self.assertRaises(ValueError):
                policy.compare_candidates(*packet)

    def test_borrowed_role_edge_rejected(self):
        rows, scope, bundles = self.packet(control=True)
        role = rows[1]["review"]["transitions"][0]["role_assessments"][-1]["occurrences"][0]
        role["actual_required_links"] = [["foreign", "edge"]]
        with self.assertRaisesRegex(ValueError, "actual_role_route"):
            policy.compare_candidates(rows, scope, bundles)

    def test_wide_pool_not_mistaken_for_triad_extension(self):
        rows, _, _ = self.packet()
        slot = deepcopy(rows[0]["review"]["slots"][0])
        slot["members"] += [{"step": "A", "alter": q(0)}, {"step": "C", "alter": q(0)}]
        self.assertEqual(policy.chord_shape(slot)["kind"], "other_pitch_pool")
        slot["members"] = list(reversed(rows[1]["review"]["slots"][0]["members"]))
        self.assertEqual(policy.chord_shape(slot)["kind"], "nontertian_or_unordered_pool")

    def test_duplicates_and_partial_path_rejected(self):
        rows, scope, bundles = self.packet()
        with self.assertRaises(ValueError):
            policy.compare_candidates([rows[0], rows[0]], scope, bundles)
        rows[0]["review"]["partition"].pop()
        with self.assertRaises(ValueError):
            policy.compare_candidates(rows, scope, bundles)


if __name__ == "__main__":
    unittest.main()
