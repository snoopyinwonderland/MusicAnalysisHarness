"""Authentic adjacent-slot boundary explanations, never harmony verdicts."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_boundary_explanations as boundary
from musicanote_harness import factor_temporal_explanations as temporal
from musicanote_harness import factor_grounded_relations as grounded
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_musical_view as common
from test_factor_temporal_explanations import TemporalExplanationFixture
from test_factor_expanded_hypotheses import event, span
from test_factor_musical_view import reseal


class BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = TemporalExplanationFixture()
        cls.factory.addCleanup = cls.addClassCleanup
        cls.factory.setUp()
        cls.cache = {}

    def case(self, name="held", **caps):
        if name not in self.cache:
            source = [event("F4", 0, 3), event("E4", 3, 1)]
            harmony = [[event("B-3", 0, 2), event("C3", 2, 2)],
                [event("D4", 0, 2), event("G4", 2, 2)]]
            if name == "reattack":
                source = [event("F4", 0, 2), event("F4", 2, Fraction(1, 2)),
                    event("F4", Fraction(5, 2), Fraction(1, 2)), event("E4", 3, 1)]
            elif name in ("anticipation", "anticipation_reattack"):
                source = [event("D4", 0, 3), event("D4", 3, 1)] if name == "anticipation" else [event("D4", 0, 2), event("D4", 2, 2)]
                harmony = [[event(["C3", "E3", "G3"], 0, 2), event(["D3", "F3", "A3"], 2, 2)]]
            elif name == "branch": source = [event("F4", 0, 3), event(["E4", "E-4"], 3, 1)]
            elif name == "terminal": source = [event("F4", 0, 4)]
            elif name == "wrong_direction": source = [event("F4", 0, 3), event("G4", 3, 1)]
            elif name == "leap": source = [event("F4", 0, 3), event("C4", 3, 1)]
            elif name == "different_register":
                source = [event("D4", 0, 2), event("D5", 2, 2)]
                harmony = [[event(["C3", "E3", "G3"], 0, 2), event(["D3", "F3", "A3"], 2, 2)]]
            elif name == "common":
                source = [event("G4", 0, 4)]
                harmony = [[event(["C3", "E3"], 0, 2), event(["C3", "E3"], 2, 2)]]
            elif name == "no_cut": source = [event(["C3", "E4", "G4"], 0, 4)]; harmony = []
            elif name == "gap": source = [event("F4", 0, 2), event(None, 2, 1), event("E4", 3, 1)]
            elif name != "held": raise AssertionError(name)
            case = self.factory.temporal_case(self.factory.make([source, *harmony]))
            t = temporal.build_explanations(*case)
            self.cache[name] = (*case, t)
        inputs = deepcopy(self.cache[name])
        supplier = boundary.prepare_inputs(*inputs)
        return inputs, supplier, boundary.build_explanations_prepared(supplier, **caps)

    def pair(self, inputs, record, left="B-", right="C", *, minor=False):
        group = next(p for p in record["pair_groups"] if common.f(p["cut"]) == 2)
        wanted = [{("B", Fraction(-1)), ("D", Fraction()), ("F", Fraction())} if left == "B-" else
            {(letter, Fraction()) for letter in "CEG"},
            {(letter, Fraction(-1) if minor and letter == "E" else Fraction()) for letter in ("CEG" if right == "C" else "DFA")}]
        by_id = {v["variant_id"]: v for v in inputs[3]["variant_inventory"]}
        refs = []
        for slot, members in zip(group["slots"], wanted):
            refs.append(next(ref for ref in slot["variant_ids"] if ref in by_id
                and not by_id[ref]["variant"]["blockers"] and by_id[ref]["variant"]["members"] is not None
                and {common.pitch_key(p) for p in by_id[ref]["variant"]["members"]} == members))
        return group["group_id"], *refs

    def query(self, inputs, supplier, record, *, logical=None, bundle=None):
        logical = logical or self.pair(inputs, record)
        session = boundary.prepare_explanations_prepared(supplier, record)
        bundles = record["inherited_bundle_inventory"] + record["bundle_inventory"]
        bundle = bundle or next(b["record_id"] for b in record["bundle_inventory"] if b["required_links"])
        return boundary.query_pair_prepared(session, *logical, bundle)

    def control(self, record):
        return next(b["record_id"] for b in record["inherited_bundle_inventory"] if not b["required_links"])

    def assert_time(self, result):
        for profile, account in zip(result["profiles"], result["boundary_accounts"]):
            self.assertEqual(account["raw_note_time"], profile["note_time_quarters"])
            self.assertEqual(sum((common.f(v) for v in account["note_time"].values()), Fraction()), common.f(profile["total_note_time_quarters"]))
            self.assertLessEqual(common.f(account["conditional_explanation_note_time"] or common.q(0)), common.f(profile["note_time_quarters"]["nonmember_not_confirmed_nct"]))

    def test_public_and_prepared_exact_identity_and_owned_inputs(self):
        inputs, supplier, record = self.case()
        before = deepcopy(inputs)
        self.assertTrue(record["record_id"].startswith("fmbe_"))
        self.assertEqual(record["temporal_ref"], common.ref(inputs[6]))
        self.assertEqual(boundary.build_explanations(*inputs), record)
        self.assertTrue(boundary.validate_explanations(*inputs, record))
        self.assertEqual(inputs, before)
        self.assertEqual(record["inherited_bundle_inventory"], inputs[6]["inherited_bundle_inventory"] + inputs[6]["bundle_inventory"])

    def test_held_suspension_requires_resolution_link_and_only_right_clip(self):
        inputs, supplier, record = self.case()
        result = self.query(inputs, supplier, record)
        self.assert_time(result)
        self.assertEqual(common.f(result["boundary_accounts"][0]["conditional_explanation_note_time"]), 0)
        self.assertEqual(common.f(result["boundary_accounts"][1]["conditional_explanation_note_time"]), 1)
        support = [g for g in record["geometry_inventory"] if common.ref(g) in result["supported_geometry_refs"]]
        self.assertTrue(any(g["family"] == "prepared_held_suspension" for g in support))
        self.assertEqual(self.query(inputs, supplier, record, bundle=self.control(record))["boundary_accounts"][1]["conditional_explanation_note_time"], common.q(0))

    def test_rearticulated_suspension_like_requires_all_three_links(self):
        inputs, supplier, record = self.case("reattack")
        geom = next(g for g in record["geometry_inventory"] if common.f(g["cut"]) == 2 and g["family"] == "rearticulated_suspension_like" and g["status"] == "conditional_boundary_geometry")
        self.assertEqual(geom["chain_edges"], 3)
        self.assertFalse(geom["actually_held_same_sound"])
        bundle = next(b["record_id"] for b in record["bundle_inventory"] if b["required_links"] == sorted(geom["required_links"]))
        result = self.query(inputs, supplier, record, bundle=bundle)
        self.assert_time(result)
        self.assertEqual(common.f(result["boundary_accounts"][1]["conditional_explanation_note_time"]), 1)
        self.assertEqual(common.f(self.query(inputs, supplier, record, bundle=self.control(record))["boundary_accounts"][1]["conditional_explanation_note_time"]), 0)

    def test_intrinsic_held_anticipation_can_credit_left_under_no_link(self):
        inputs, supplier, record = self.case("anticipation")
        result = self.query(inputs, supplier, record, logical=self.pair(inputs, record, "C", "D"), bundle=self.control(record))
        self.assert_time(result)
        self.assertEqual(common.f(result["boundary_accounts"][0]["conditional_explanation_note_time"]), 2)
        self.assertEqual(common.f(result["boundary_accounts"][1]["conditional_explanation_note_time"]), 0)
        self.assertTrue(any(not g["required_links"] and common.ref(g) in result["supported_geometry_refs"] for g in record["geometry_inventory"]))

    def test_rearticulation_anticipation_needs_edge_not_merely_same_pitch(self):
        inputs, supplier, record = self.case("anticipation_reattack")
        logical = self.pair(inputs, record, "C", "D")
        result = self.query(inputs, supplier, record, logical=logical)
        self.assertEqual(common.f(result["boundary_accounts"][0]["conditional_explanation_note_time"]), 2)
        self.assertEqual(common.f(self.query(inputs, supplier, record, logical=logical, bundle=self.control(record))["boundary_accounts"][0]["conditional_explanation_note_time"]), 0)

    def test_common_member_is_not_boundary_nonmember_or_extra_credit(self):
        inputs, supplier, record = self.case("common")
        result = self.query(inputs, supplier, record, logical=self.pair(inputs, record, "C", "C"), bundle=self.control(record))
        self.assert_time(result)
        self.assertTrue(all(common.f(a["conditional_explanation_note_time"]) == 0 for a in result["boundary_accounts"]))

    def test_competitor_minor_cannot_borrow_major_independent_witness(self):
        inputs, supplier, record = self.case("branch")
        major = self.pair(inputs, record); minor = self.pair(inputs, record, minor=True)
        session = boundary.prepare_explanations_prepared(supplier, record)
        found = []; minority = []
        for bundle in record["bundle_inventory"]:
            a = boundary.query_pair_prepared(session, *major, bundle["record_id"])
            b = boundary.query_pair_prepared(session, *minor, bundle["record_id"])
            if common.f(a["boundary_accounts"][1]["conditional_explanation_note_time"]) == 1:
                self.assertEqual(common.f(b["boundary_accounts"][1]["conditional_explanation_note_time"]), 0); found.append(bundle)
            if common.f(b["boundary_accounts"][1]["conditional_explanation_note_time"]) == 1:
                self.assertEqual(common.f(a["boundary_accounts"][1]["conditional_explanation_note_time"]), 0); minority.append(bundle)
        self.assertTrue(found)
        self.assertTrue(minority)
        universe = record["logical_universe"]
        combined = tuple(sorted({tuple(edge) for b in (found[0], minority[0]) for edge in b["required_links"]}))
        impossible = boundary._new_bundle(inputs[1], inputs[3], inputs[5], universe, combined, 100000)
        self.assertEqual(impossible["geometry_condition_status"], "impossible")
        self.assertTrue(any(e["query"]["possible_assignments"] == "0" for e in impossible["entries"]))

    def test_first_changed_wrong_direction_leap_and_terminal_retained_withheld(self):
        for name, code in (("terminal", "first_changed_resolution_not_observed_terminal_carry"),
            ("wrong_direction", "first_changed_resolution_not_downward_ordinary_spelled_step"),
            ("leap", "first_changed_resolution_not_downward_ordinary_spelled_step")):
            with self.subTest(name=name):
                _, _, record = self.case(name)
                geoms = [g for g in record["geometry_inventory"] if common.f(g["cut"]) == 2 and "suspension" in g["family"]]
                self.assertTrue(geoms); self.assertTrue(all(code in g["blockers"] for g in geoms if g["involved_sound_refs"][0] == geoms[0]["involved_sound_refs"][0]))

    def test_octave_change_is_not_identical_anticipation_reattack(self):
        _, _, record = self.case("different_register")
        self.assertTrue(any("anticipation_reattack_not_identical_written_register" in g["blockers"] for g in record["geometry_inventory"]))

    def test_silence_gap_does_not_create_carry_or_resolution_edge(self):
        _, _, record = self.case("gap")
        self.assertFalse(any(g["family"] == "prepared_held_suspension" and common.f(g["cut"]) == 2 for g in record["geometry_inventory"]))

    def test_no_cut_is_known_zero_not_unknown(self):
        _, _, record = self.case("no_cut", max_geometry_candidates=0, max_chain_edges=0, max_membership_relations=0, max_new_bundles=0)
        self.assertEqual(record["pair_groups"], [])
        for name in ("planned_geometry_candidates", "planned_membership_relations", "planned_new_bundles"):
            self.assertEqual(record["summary"][name], 0)

    def test_whole_geometry_cap_precounts_without_leaf_or_record_prefix(self):
        inputs, supplier, full = self.case("reattack")
        with patch.object(boundary, "_geometry_record", side_effect=AssertionError("no materialization")):
            held = boundary.build_explanations_prepared(supplier, max_geometry_candidates=0)
        self.assertEqual(held["summary"]["planned_geometry_candidates"], full["summary"]["planned_geometry_candidates"])
        self.assertEqual(held["geometry_inventory"], []); self.assertIsNone(held["summary"]["planned_membership_relations"])

    def test_chain_depth_hold_never_truncates_three_edges_into_shorter_path(self):
        _, supplier, full = self.case("reattack")
        held = boundary.build_explanations_prepared(supplier, max_chain_edges=2)
        self.assertEqual(held["summary"]["max_planned_chain_edges"], 3)
        self.assertEqual(held["geometry_inventory"], [])
        self.assertEqual(held["summary"]["planned_geometry_candidates"], full["summary"]["planned_geometry_candidates"])

    def test_whole_rectangle_cap_precounts_before_any_rectangle_seal(self):
        _, supplier, full = self.case()
        original = boundary._seal
        def checked(body, prefix):
            if prefix in (boundary.RELATION_PREFIX, boundary.PARTITION_PREFIX): raise AssertionError("no sealed rectangle prefix")
            return original(body, prefix)
        with patch.object(boundary, "_seal", checked): held = boundary.build_explanations_prepared(supplier, max_membership_relations=0)
        self.assertEqual(held["summary"]["planned_membership_relations"], full["summary"]["planned_membership_relations"])
        self.assertEqual(held["membership_partition_inventory"], []); self.assertEqual(held["membership_relation_inventory"], [])
        self.assertIsNone(held["summary"]["conditional_descriptor_pair_geometry_incidences"])

    def test_whole_new_bundle_cap_retains_all_requests_and_old_bundles(self):
        inputs, supplier, _ = self.case()
        held = boundary.build_explanations_prepared(supplier, max_new_bundles=0)
        self.assertTrue(held["bundle_requests"]); self.assertEqual(held["bundle_inventory"], [])
        self.assertTrue(all(r["bundle_ref"] is None for r in held["bundle_requests"]))
        self.assertEqual(held["inherited_bundle_inventory"], inputs[6]["inherited_bundle_inventory"] + inputs[6]["bundle_inventory"])

    def test_query_zero_budget_is_whole_hold_with_raw_profiles_retained(self):
        inputs, supplier, _ = self.case()
        held = boundary.build_explanations_prepared(supplier, query_work_budget=0)
        result = self.query(inputs, supplier, held, bundle=self.control(held))
        self.assertIsNone(result["boundary_accounts"]); self.assertIsNone(result["geometry_assessments"])
        self.assertTrue(all(result["profiles"])); self.assertGreater(result["planned_query_work_items"], 0)

    def test_held_role_inventory_query_does_not_report_empty_geometries_as_known_zero(self):
        inputs, supplier, _ = self.case()
        held = boundary.build_explanations_prepared(supplier, max_membership_relations=0)
        result = self.query(inputs, supplier, held, bundle=self.control(held))
        self.assertIsNone(result["planned_query_work_items"]); self.assertGreater(result["known_stored_query_work_subtotal"], 0)
        self.assertIsNone(result["supported_geometry_refs"])

    def test_all_partition_rectangles_preserve_descriptor_and_origin_key_products(self):
        inputs, _, record = self.case()
        parts = {p["record_id"]: p for p in record["membership_partition_inventory"]}
        pairs = {p["group_id"]: p for p in record["pair_groups"]}
        total = 0
        for rel in record["membership_relation_inventory"]:
            left, right = [parts[rel[k]["record_id"]] for k in ("left_partition_ref", "right_partition_ref")]
            self.assertEqual(rel["descriptor_pair_count"], left["descriptor_count"] * right["descriptor_count"])
            self.assertEqual(rel["origin_pair_key_count"], left["origin_count"] * right["origin_count"] * len(inputs[3]["keys"]))
            total += rel["descriptor_pair_count"]
        self.assertEqual(total, record["summary"]["known_descriptor_pair_geometry_incidence_subtotal"])
        for geom in record["geometry_inventory"]:
            pair = pairs[geom["group_id"]]
            self.assertEqual(sum(r["descriptor_pair_count"] for r in record["membership_relation_inventory"] if r["geometry_ref"] == common.ref(geom)),
                len(pair["descriptor_origin_incidence"][0]) * len(pair["descriptor_origin_incidence"][1]))

    def test_each_selected_origin_profile_restores_exact_frozen_oracle(self):
        inputs, supplier, record = self.case()
        logical = self.pair(inputs, record); result = self.query(inputs, supplier, record, logical=logical)
        by_id = {r["variant_id"]: r["variant"] for r in inputs[3]["variant_inventory"]}
        self.assertEqual(result["profiles"], [frozen._profile(inputs[1], by_id[ref]) for ref in logical[1:]])

    def test_numeric_boolean_and_foreign_limits_rejected_before_parent_reads(self):
        for name in boundary.CAPS:
            for value in (True, -1, 1.0, None, "1"):
                with self.subTest(name=name, value=value), patch.object(boundary, "prepare_inputs", side_effect=AssertionError("no inputs")), self.assertRaises(ValueError):
                    boundary.build_explanations(*([None] * 7), **{name: value})

    def test_resealed_lost_origin_partition_count_metadata_and_promotion_fail(self):
        inputs, _, record = self.case()
        for mutate in (lambda r: r.update(confidence=1), lambda r: r["summary"].update(pair_accounts_computed=False),
            lambda r: r["pair_groups"][0]["descriptor_origin_incidence"][0].pop(),
            lambda r: r["membership_relation_inventory"][0].update(descriptor_pair_count=0),
            lambda r: r["bundle_inventory"][0].update(symbolic_universe_ref=r["temporal_ref"])):
            bad = deepcopy(record); mutate(bad)
            with self.assertRaises(ValueError): boundary.validate_explanations(*inputs, reseal(bad, boundary.PREFIX))

    def test_typed_selectors_forbid_foreign_group_reversed_or_duplicate_origins(self):
        inputs, supplier, record = self.case(); logical = self.pair(inputs, record)
        session = boundary.prepare_explanations_prepared(supplier, record); bundle = self.control(record)
        for args in ((None, *logical[1:], bundle), (logical[0], logical[2], logical[1], bundle),
            (logical[0], logical[1], logical[1], bundle), (*logical, None), (*logical, "fake")):
            with self.assertRaises(ValueError): boundary.query_pair_prepared(session, *args)

    def test_current_source_bytes_and_forged_opaque_handles_are_rejected(self):
        inputs, supplier, record = self.case(); session = boundary.prepare_explanations_prepared(supplier, record)
        with self.assertRaises(ValueError): boundary.build_explanations_prepared(boundary._PreparedInputs())
        actual = Path.read_bytes
        def changed(path): return actual(path) + b"\n" if path == Path(boundary.__file__) else actual(path)
        with patch.object(Path, "read_bytes", changed), self.assertRaises(ValueError):
            boundary.query_pair_prepared(session, *self.pair(inputs, record), self.control(record))

    def test_prepared_inputs_and_session_detach_mutable_callers(self):
        inputs, supplier, record = self.case(); session = boundary.prepare_explanations_prepared(supplier, record)
        logical = self.pair(inputs, record); control = self.control(record)
        expected = boundary.query_pair_prepared(session, *logical, control)
        inputs[3]["variant_inventory"].clear(); record["geometry_inventory"].clear()
        self.assertEqual(boundary.query_pair_prepared(session, *logical, control), expected)
        self.assertTrue(boundary.build_explanations_prepared(supplier)["geometry_inventory"])

    def test_pair_query_does_not_rebuild_catalogue_profiles_or_geometry(self):
        inputs, supplier, record = self.case(); session = boundary.prepare_explanations_prepared(supplier, record)
        with patch.object(frozen, "_profile", side_effect=AssertionError("no profile regeneration")), \
             patch.object(boundary.geometry, "query", side_effect=AssertionError("no new completion")), \
             patch.object(boundary, "_body", side_effect=AssertionError("no body rebuild")):
            self.assert_time(boundary.query_pair_prepared(session, *self.pair(inputs, record), self.control(record)))

    def test_no_selection_full_nct_delayed_or_combined_local_account_claims(self):
        _, _, record = self.case()
        self.assertTrue(all(v is False for v in record["flags"].values()))
        self.assertIsNone(record["selected"]); self.assertIsNone(record["rank"]); self.assertIsNone(record["confidence"])
        self.assertEqual(record["functional_delayed_obligations"], "unassessed")
        self.assertEqual(record["local_plus_boundary_combined_accounting"], "unassessed")

    def test_source_predicate_table_does_not_allow_invalid_endpoint_to_borrow_healthy_support(self):
        inputs, _, record = self.case()
        geom = next(g for g in record["geometry_inventory"] if g["family"] == "prepared_held_suspension"
            and common.f(g["cut"]) == 2 and g["status"] == "conditional_boundary_geometry")
        pair = next(p for p in record["pair_groups"] if p["group_id"] == geom["group_id"])
        graph = next(g for g in inputs[1]["graphs"] if common.ref(g) == geom["graph_ref"])
        for field, value, code in (("source_clock_passed", False, "source_clock_passed_not_passed"),
            ("source_attack_consistency_passed", False, "source_attack_consistency_passed_not_passed"),
            ("source_pitch_consistency_passed", False, "source_pitch_consistency_passed_not_passed"),
            ("eligible_as_analysis_source", False, "source_not_eligible"),
            ("grace", True, "point_or_grace_positive_time_role_not_supported"),
            ("point", True, "point_or_grace_positive_time_role_not_supported"),
            ("source_diagnostics", ["raw_owner_ambiguous"], "raw_owner_ambiguous")):
            for sid in geom["involved_sound_refs"]:
                with self.subTest(field=field, endpoint=sid):
                    sounds = {s["sound_ref"]: deepcopy(s) for s in inputs[1]["sound_facts"]}
                    sounds[sid][field] = value
                    failed = boundary._geometry_record(inputs[1], pair, graph, geom["family"], tuple(geom["involved_sound_refs"]), True, sounds)
                    self.assertEqual(failed["status"], "withheld_boundary_geometry")
                    self.assertTrue(any(code in reason for reason in failed["blockers"]))
        sounds = {s["sound_ref"]: deepcopy(s) for s in inputs[1]["sound_facts"]}
        sounds[geom["involved_sound_refs"][-1]]["pitch"]["alter"] = common.q(Fraction(1, 2))
        failed = boundary._geometry_record(inputs[1], pair, graph, geom["family"], tuple(geom["involved_sound_refs"]), True, sounds)
        self.assertEqual(failed["status"], "withheld_boundary_geometry")

    def test_preparation_and_all_full_spans_inside_exact_pair_not_merely_clipped_observations(self):
        inputs, _, record = self.case()
        geom = next(g for g in record["geometry_inventory"] if g["family"] == "prepared_held_suspension"
            and common.f(g["cut"]) == 2 and g["status"] == "conditional_boundary_geometry")
        pair = next(p for p in record["pair_groups"] if p["group_id"] == geom["group_id"])
        graph = next(g for g in inputs[1]["graphs"] if common.ref(g) == geom["graph_ref"])
        for sid, changed_span, expected in ((geom["involved_sound_refs"][0], span(0, 3), "preparation_attack_not_in_left_slot"),
            (geom["involved_sound_refs"][-1], span(3, 5), "all_involved_full_sound_spans_not_inside_pair_envelope"),
            (geom["involved_sound_refs"][-1], span(4, 5), "resolution_attack_not_in_right_half_open_slot")):
            sounds = {s["sound_ref"]: deepcopy(s) for s in inputs[1]["sound_facts"]}
            sounds[sid]["span"] = changed_span
            local_pair = deepcopy(pair)
            if expected == "preparation_attack_not_in_left_slot": local_pair["pair_span"]["start"] = common.q(1)
            failed = boundary._geometry_record(inputs[1], local_pair, graph, geom["family"], tuple(geom["involved_sound_refs"]), True, sounds)
            self.assertIn(expected, failed["blockers"])

    def test_initial_held_boundary_with_later_reattacks_is_not_whole_chain_tie_claim(self):
        case = self.factory.temporal_case(self.factory.make([[event("F4", 0, 3),
            event("F4", 3, Fraction(1, 2)), event("E4", Fraction(7, 2), Fraction(1, 2))],
            [event("B-3", 0, 2), event("C3", 2, 2)], [event("D4", 0, 2), event("G4", 2, 2)]]))
        inputs = (*case, temporal.build_explanations(*case)); record = boundary.build_explanations(*inputs)
        geom = next(g for g in record["geometry_inventory"] if g["family"] == "prepared_held_suspension"
            and common.f(g["cut"]) == 2 and g["status"] == "conditional_boundary_geometry")
        self.assertTrue(geom["actually_held_same_sound"])
        self.assertEqual(geom["initial_boundary_presentation"], "one_physically_held_sound")
        self.assertFalse(geom["whole_chain_is_one_sounding_event"])
        self.assertEqual(geom["edge_kinds"], ["same_written_register_rearticulation_not_tie", "first_changed_endpoint"])

    def test_first_changed_wrong_pitch_cannot_skip_to_later_favorable_resolution(self):
        case = self.factory.temporal_case(self.factory.make([[event("F4", 0, 3), event("G4", 3, Fraction(1, 2)),
            event("E4", Fraction(7, 2), Fraction(1, 2))], [event("B-3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G3", 2, 2)]]))
        inputs = (*case, temporal.build_explanations(*case)); record = boundary.build_explanations(*inputs)
        sound = next(s for s in inputs[1]["sound_facts"] if s["pitch"]["spelling"] == "F4")
        geoms = [g for g in record["geometry_inventory"] if common.f(g["cut"]) == 2 and "suspension" in g["family"]
            and g["involved_sound_refs"][0] == sound["sound_ref"]]
        self.assertTrue(geoms); self.assertTrue(all(g["chain_edges"] == 1 for g in geoms))
        self.assertTrue(all("first_changed_resolution_not_downward_ordinary_spelled_step" in g["blockers"] for g in geoms))

    def test_upstream_max_variants_zero_keeps_valid_pair_ids_and_unknown_not_zero(self):
        case = self.factory.temporal_case(self.factory.make([[event(["C3", "E4", "G4"], 0, 2),
            event(["D3", "F4", "A4"], 2, 2)]], index_options={"max_variants": 0}))
        inputs = (*case, temporal.build_explanations(*case)); supplier = boundary.prepare_inputs(*inputs)
        record = boundary.build_explanations_prepared(supplier); session = boundary.prepare_explanations_prepared(supplier, record)
        pair = record["pair_groups"][0]; ids = [s["variant_ids"][0] for s in pair["slots"]]
        result = boundary.query_pair_prepared(session, pair["group_id"], *ids, None)
        self.assertEqual(result["origin_variant_ids"], ids); self.assertEqual(result["profiles"], [None, None])
        self.assertIsNone(result["boundary_accounts"]); self.assertIsNone(result["planned_query_work_items"])
        self.assertIsNone(record["summary"]["planned_membership_relations"])
        self.assertEqual(record["summary"]["logical_paths"], inputs[3]["summary"]["logical_paths"])

    def test_boundary_interval_credit_unions_overlapping_clauses_without_double_count(self):
        inputs, supplier, record = self.case(); logical = self.pair(inputs, record)
        result = self.query(inputs, supplier, record, logical=logical)
        geom = next(g for g in record["geometry_inventory"] if common.ref(g) in result["supported_geometry_refs"])
        origin = next(v for v in inputs[3]["variant_inventory"] if v["variant_id"] == logical[2])
        descriptor = next(d for d in inputs[3]["profile_inventory"] if common.ref(d) == origin["profile_ref"])
        sounds = {s["sound_ref"]: s for s in inputs[1]["sound_facts"]}
        account = boundary._side_account(result["profiles"][1], descriptor, sounds, geom["explained_items"] * 3, True)
        self.assertEqual(common.f(account["conditional_explanation_note_time"]), 1)
        self.assertEqual(sum((common.f(v) for v in account["note_time"].values()), Fraction()), common.f(account["total_note_time"]))

    def test_each_seven_authentic_but_foreign_parent_rejected(self):
        inputs, _, _ = self.case(); other, _, _ = self.case("anticipation")
        for position in range(7):
            with self.subTest(position=position):
                mixed = list(inputs); mixed[position] = other[position]
                with self.assertRaises(ValueError): boundary.prepare_inputs(*mixed)

    def test_empty_boundary_universe_is_known_zero_even_with_upstream_profile_hold(self):
        inputs, _, _ = self.case("no_cut")
        held = list(inputs)
        held[5] = grounded.build_grounding(*held[:5], max_profiles=0)
        held[6] = temporal.build_explanations(*held[:6])
        result = boundary.build_explanations(*held)
        self.assertFalse(held[6]["summary"]["literal_presentation_inventory_complete"])
        self.assertTrue(result["summary"]["membership_inventory_complete"])
        self.assertEqual(result["pair_groups"], [])
        for name in ("planned_geometry_candidates", "planned_membership_relations", "planned_new_bundles"):
            self.assertEqual(result["summary"][name], 0)

    def test_known_empty_pair_product_is_zero_despite_nonempty_withheld_other_slot(self):
        case = self.factory.temporal_case(self.factory.make([[event("C3", 0, 2), event(["C3", "E4", "G4"], 2, 2)]],
            index_options={"max_variants": 0}))
        inputs = (*case, temporal.build_explanations(*case)); result = boundary.build_explanations(*inputs)
        self.assertEqual(len(result["pair_groups"]), 1)
        pair = result["pair_groups"][0]
        self.assertEqual(pair["logical_path_count"], 0)
        self.assertEqual(pair["slots"][0]["variant_ids"], [])
        self.assertTrue(pair["slots"][1]["variant_ids"])
        self.assertEqual(result["summary"]["planned_membership_relations"], 0)
        self.assertEqual(result["summary"]["planned_new_bundles"], 0)


if __name__ == "__main__": unittest.main()
