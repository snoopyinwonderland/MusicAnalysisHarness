"""Actual literal profiles and joint direct motion, never harmony decisions."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import product
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_expanded_scope as expanded
from musicanote_harness import factor_function_relations as shapes
from musicanote_harness import factor_grounded_relations as grounded
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_factorized_voice_paths as geometry
from musicanote_harness import harmony_candidate_catalog as catalog
from test_factor_indexed_hypotheses import IndexedHypothesisFixture
from test_factor_expanded_hypotheses import event, span
from test_factor_musical_view import reseal


class GroundedRelationsFixture(IndexedHypothesisFixture):
    def frozen_case(self, case=None, *, relation_options=None):
        case = case or self.make()
        fx, hyp, idx = case
        return fx, hyp, idx, shapes.build_relations(*fx, hyp, idx, **(relation_options or {}))

    def ready(self, name="default", **caps):
        cls = type(self)
        if name not in cls._cases:
            factory = cls._factory
            if name == "default": case = factory.make()
            elif name == "dominant": case = factory.dominant()
            elif name == "key": case = factory.dominant(signatures=[{"fifths": 0, "mode_hint": None}])
            elif name == "small": case = factory.make([[event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]])
            elif name == "incompatible":
                case = factory.make([[event("B4", 0, 2), event("C5", 2, 2)],
                    [event("F4", 0, 2), event(["E4", "E-4"], 2, 2)],
                    [event("G3", 0, 2), event("C3", 2, 2)],
                    [event("D4", 0, 2), event("G4", 2, 2)]])
            else: raise AssertionError("unknown fixture name")
            cls._cases[name] = factory.frozen_case(case)
        case = deepcopy(cls._cases[name])
        cache_key = (name, tuple(sorted(caps.items())))
        if cache_key not in cls._groundings:
            cls._groundings[cache_key] = grounded.build_grounding(*case[0], *case[1:], **caps)
        return case, deepcopy(cls._groundings[cache_key])

    def session(self, case, record):
        return grounded.prepare_grounding(*case[0], *case[1:], record)

    def logical(self, case, *, dominant=False):
        return self.dominant_tuple(case[:3]) if dominant else self.first_tuple(case[1], case[2])

    def query(self, case, record, logical=None):
        return grounded.query_grounded(*case[0], *case[1:], record, *(logical or self.logical(case)))

    @staticmethod
    def motion(result, *, slot=0, family="V7", quality="M"):
        return next(row for row in result["functions"] if row["slot_index"] == slot
                    and row["family"] == family and row["quality"] == quality)

    def assert_oracle(self, case, logical, result):
        fx, hyp, _, _ = case
        variants = self.variants(hyp)
        segments = [variants[ref] for ref in logical[1]]
        key = next(k for k in hyp["keys"] if k["record_id"] == logical[2])
        self.assertEqual(result["profiles"], [frozen._profile(fx[1], segment) for segment in segments])
        expected = []
        for position, source in enumerate(segments):
            target = segments[position + 1] if position + 1 < len(segments) else None
            for family in frozen.FAMILIES:
                for quality in ("M", "m"):
                    expected.append((position, family, quality,
                        frozen._function(fx[1], source, target, key["segments"][0], family, quality)))
        self.assertEqual(len(result["functions"]), len(expected))
        for row, (position, family, quality, function) in zip(result["functions"], expected):
            self.assertEqual((row["slot_index"], row["family"], row["quality"]), (position, family, quality))
            self.assertEqual(row["function"], function)
            self.assertEqual(row["conditional_NCT_and_delayed_resolution"], "unassessed")

    def target_logical(self, case, quality):
        _, hyp, idx, _ = case
        variants = self.variants(hyp)
        group = next(g for g in idx["path_groups"] if g["kind"] == "two_segment" and g["cut"] == common.q(2))
        desired = [("G", {("G", Fraction()), ("B", Fraction()), ("D", Fraction()), ("F", Fraction())}),
                   ("C", {("C", Fraction()), ("E", Fraction(0 if quality == "M" else -1)), ("G", Fraction())})]
        ids = []
        for slot, (root, members) in zip(group["slots"], desired):
            ids.append(next(ref for ref in slot["variant_ids"] if variants[ref]["root"] == {"step": root, "alter": common.q(0)}
                and variants[ref]["members"] is not None and {common.pitch_key(p) for p in variants[ref]["members"]} == members))
        return group["group_id"], ids, hyp["keys"][0]["record_id"]


class GroundedRelationsTests(GroundedRelationsFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._factory = GroundedRelationsFixture()
        cls._factory.addCleanup = cls.addClassCleanup
        cls._factory.setUp()
        cls._cases, cls._groundings = {}, {}

    def test_new_typed_grounding_reproducible_exact_bindings_and_no_aliases(self):
        case, record = self.ready()
        before = deepcopy((case, record))
        self.assertTrue(record["record_id"].startswith("fmgr_"))
        self.assertEqual(record["scope_ref"], common.ref(case[0][1]))
        self.assertEqual(record["index_ref"], common.ref(case[2]))
        self.assertEqual(record["relations_ref"], common.ref(case[3]))
        self.assertEqual(grounded.build_grounding(*case[0], *case[1:]), record)
        self.assertTrue(grounded.validate_grounding(*case[0], *case[1:], record))
        self.assertEqual((case, record), before)
        case[1]["catalog_inventory"][0]["variants"][0]["blockers"].append("caller_mutation")
        case[2]["variant_inventory"][0]["variant"]["blockers"].append("other_mutation")
        self.assertEqual(record, before[1])

    def test_every_descriptor_profile_is_materialized_exactly_once_with_exact_value_order(self):
        case, record = self.ready("small")
        scope, idx = case[0][1], case[2]
        variants = {row["variant_id"]: row["variant"] for row in idx["variant_inventory"]}
        representatives = {}
        for row in idx["variant_inventory"]: representatives.setdefault(row["profile_ref"]["record_id"], variants[row["variant_id"]])
        rows = {row["record_id"]: row for row in record["row_inventory"]}
        cells = {row["record_id"]: row for row in record["cell_inventory"]}
        self.assertEqual([p["descriptor_ref"] for p in record["profile_inventory"]],
                         [common.ref(p) for p in idx["profile_inventory"]])
        row_uses = cell_uses = 0
        for profile, descriptor in zip(record["profile_inventory"], idx["profile_inventory"]):
            expected = frozen._profile(scope, representatives[descriptor["record_id"]])
            self.assertEqual(profile["semantic_input"], descriptor["semantic_input"])
            self.assertEqual([rows[ref]["value"] for ref in profile["row_ids"]], expected["rows"])
            self.assertEqual([cells[ref]["value"] for ref in profile["cell_ids"]], expected["cells"])
            self.assertEqual(profile["profile_core"], {k: v for k, v in expected.items()
                if k not in ("rows", "cells", "segment_ref", "missing_spellings", "missing_pitch_classes", "supplier_event_states")})
            row_uses += len(expected["rows"])
            cell_uses += len(expected["cells"])
        self.assertEqual(record["summary"]["planned_profile_row_uses"], row_uses)
        self.assertEqual(record["summary"]["literal_profile_row_uses"], row_uses)
        self.assertEqual(record["summary"]["planned_profile_cell_uses"], cell_uses)
        self.assertEqual(record["summary"]["literal_profile_cell_uses"], cell_uses)
        self.assertEqual(len({shapes.digest(r["value"]) for r in rows.values()}), len(rows))
        self.assertEqual(len({shapes.digest(r["value"]) for r in cells.values()}), len(cells))

    def test_all_103_tuples_restore_exact_profiles_and_1670_function_bodies(self):
        case, record = self.ready("small")
        session = self.session(case, record)
        count = functions = 0
        for group in case[2]["path_groups"]:
            for ids in product(*(slot["variant_ids"] for slot in group["slots"])):
                for key in case[1]["keys"]:
                    logical = (group["group_id"], list(ids), key["record_id"])
                    result = grounded.query_grounded_prepared(session, *logical)
                    self.assert_oracle(case, logical, result)
                    count += 1
                    functions += len(result["functions"])
        self.assertEqual(count, 103)
        self.assertEqual(functions, 1670)

    def test_every_origin_supplier_metadata_and_segment_reference_is_restored(self):
        case, record = self.ready()
        session = self.session(case, record)
        variants = self.variants(case[1])
        group = case[2]["path_groups"][0]
        for vid in group["slots"][0]["variant_ids"]:
            logical = (group["group_id"], [vid], case[1]["keys"][0]["record_id"])
            result = grounded.query_grounded_prepared(session, *logical)
            self.assertEqual(result["profiles"][0], frozen._profile(case[0][1], variants[vid]))
            self.assertEqual(result["profiles"][0]["segment_ref"], variants[vid]["segment_id"])
        self.assertEqual(record["origin_inventory"], case[3]["origin_inventory"])

    def test_positive_direct_lt_and_seventh_use_one_complete_all_lane_bundle(self):
        case, record = self.ready("dominant")
        logical = self.logical(case, dominant=True)
        result = self.query(case, record, logical)
        self.assert_oracle(case, logical, result)
        motion = self.motion(result)["motion"]
        self.assertEqual(motion["status"], "conditional_joint_direct_motion_shape")
        self.assertEqual(set(motion["edge_options"]), {"leading_tone", "seventh"})
        self.assertEqual(motion["planned_endpoint_pairs"], 2)
        self.assertEqual(motion["planned_joint_options"], 1)
        self.assertEqual(len(motion["joint_options"]), 1)
        joint = motion["joint_options"][0]
        self.assertTrue(joint["all_critical_roles_in_same_complete_bundle"])
        self.assertEqual(len(joint["required_links"]), 2)
        bundle = next(b for b in record["bundle_inventory"] if common.ref(b) == joint["bundle_ref"])
        self.assertEqual(bundle["status"], "complete_all_lane_witness")
        self.assertEqual(bundle["materialized_witness_links"], joint["required_links"])
        self.assertEqual(len(bundle["entries"]), len(case[0][1]["raw_lanes"]))
        assessed = grounded.assess_grounded(*case[0], *case[1:], record, bundle, *logical)
        row = next(r for r in assessed["rows"] if r["slot_index"] == 0 and r["family"] == "V7" and r["quality"] == "M")
        self.assertTrue(row["all_critical_roles_in_same_complete_bundle"])
        self.assertTrue(all(row["matched_actual_links_by_role"].values()))
        self.assertIsNone(row["function_confirmed"])

    def test_competing_major_minor_independent_witnesses_cannot_be_combined(self):
        case, record = self.ready("incompatible")
        session = self.session(case, record)
        major, minor = (self.target_logical(case, q) for q in ("M", "m"))
        major_q = grounded.query_grounded_prepared(session, *major)
        minor_q = grounded.query_grounded_prepared(session, *minor)
        major_m = self.motion(major_q, quality="M")["motion"]
        minor_m = self.motion(minor_q, quality="m")["motion"]
        for motion in (major_m, minor_m): self.assertEqual(motion["status"], "conditional_joint_direct_motion_shape")
        bundles = {b["record_id"]: b for b in record["bundle_inventory"]}
        major_b = bundles[major_m["joint_options"][0]["bundle_ref"]["record_id"]]
        minor_b = bundles[minor_m["joint_options"][0]["bundle_ref"]["record_id"]]
        self.assertNotEqual(major_b["record_id"], minor_b["record_id"])
        supported = grounded.assess_grounded_prepared(session, major_b, *major)
        competing = grounded.assess_grounded_prepared(session, major_b, *minor)
        good = next(r for r in supported["rows"] if r["slot_index"] == 0 and r["family"] == "V7" and r["quality"] == "M")
        bad = next(r for r in competing["rows"] if r["slot_index"] == 0 and r["family"] == "V7" and r["quality"] == "m")
        self.assertTrue(good["all_critical_roles_in_same_complete_bundle"])
        self.assertFalse(bad["all_critical_roles_in_same_complete_bundle"])
        self.assertEqual(bad["status"], "not_satisfied_under_this_bundle_not_global_absence")
        self.assertEqual(bad["matched_actual_links_by_role"]["seventh"], [])
        all_links = major_b["required_links"] + minor_b["required_links"]
        conflicts = []
        for graph in case[0][1]["graphs"]:
            ids = {row["sounding_event_id"] for row in graph["events"]}
            required = [edge for edge in all_links if edge[0] in ids]
            result = geometry.query(graph, required_links=required)
            if result["status"] == "unsatisfiable_constraints": conflicts.extend(result["reasons"])
        self.assertIn("required_branch_not_allowed", conflicts)

    def test_no_link_control_does_not_borrow_a_direct_resolution_witness(self):
        case, record = self.ready("dominant")
        logical = self.logical(case, dominant=True)
        bundle = next(b for b in record["bundle_inventory"] if b["all_no_link_control"])
        self.assertEqual(bundle["materialized_witness_links"], [])
        result = grounded.assess_grounded_prepared(self.session(case, record), bundle, *logical)
        row = next(r for r in result["rows"] if r["slot_index"] == 0 and r["family"] == "V7" and r["quality"] == "M")
        self.assertFalse(row["all_critical_roles_in_same_complete_bundle"])
        self.assertEqual(row["matched_actual_links_by_role"], {"leading_tone": [], "seventh": []})

    def test_all_original_weighted_false_unknown_terminal_and_key_denominators_survive(self):
        case, record = self.ready("key")
        parent = case[3]["summary"]
        summary = record["summary"]
        for name in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "terminal_target_rows"):
            self.assertEqual(summary[name], parent[name])
        self.assertEqual(summary["motion_ineligible_function_prerequisite_rows"], parent["withheld_function_shape_rows"])
        self.assertEqual(summary["grounded_conditional_direct_motion_shape_rows"] + summary["grounded_withheld_direct_motion_rows"]
                         + summary["unassessed_direct_motion_rows"], summary["logical_function_rows"])
        self.assertEqual(record["parent_summary"], parent)
        self.assertEqual(record["keys"], case[1]["keys"])
        self.assertEqual(record["catalog_inventory"], case[3]["catalog_inventory"])
        self.assertEqual(len(record["keys"]), 5)
        for before, group in zip(case[3]["path_groups"], record["path_groups"]):
            self.assertEqual(group["slots"], before["slots"])
            self.assertEqual(group["function_slots"], before["function_slots"])
            n = group["grounding_counts"]
            self.assertEqual(n["conditional_direct_motion_shape_rows"] + n["withheld_direct_motion_rows"]
                             + n["unassessed_direct_motion_rows"], before["logical_function_count"])

    def test_motion_shared_across_keys_keeps_each_exact_unknown_and_reference_projection(self):
        case, record = self.ready("key")
        logical = self.logical(case, dominant=True)
        session = self.session(case, record)
        motion_refs = []
        for key in case[1]["keys"]:
            current = (logical[0], logical[1], key["record_id"])
            result = grounded.query_grounded_prepared(session, *current)
            self.assert_oracle(case, current, result)
            motion_refs.append(self.motion(result)["motion_kernel_ref"])
            if key["segments"][0]["mode"] == "unknown":
                self.assertEqual(self.motion(result)["function"]["function_kind"], "unassessed")
                self.assertIn("explicit_key_unknown", self.motion(result)["function"]["key_projection"]["unassessed_reasons"])
        self.assertTrue(all(ref == motion_refs[0] for ref in motion_refs))
        self.assertEqual(len(case[1]["keys"]), 5)

    def test_profile_budget_zero_and_one_less_withhold_whole_inventory_not_prefix(self):
        case, original = self.ready()
        count = len(case[2]["profile_inventory"])
        exact = grounded.build_grounding(*case[0], *case[1:], max_profiles=count)
        self.assertEqual(len(exact["profile_inventory"]), count)
        for cap in (0, count - 1):
            record = grounded.build_grounding(*case[0], *case[1:], max_profiles=cap)
            with self.subTest(cap=cap):
                for field in ("profile_inventory", "row_inventory", "cell_inventory"):
                    self.assertEqual(record[field], [])
                self.assertEqual(record["origin_inventory"], original["origin_inventory"])
                self.assertEqual(record["summary"]["planned_profile_row_uses"], original["summary"]["planned_profile_row_uses"])
                self.assertEqual(record["summary"]["planned_profile_cell_uses"], original["summary"]["planned_profile_cell_uses"])
                self.assertFalse(record["summary"]["literal_profiles_complete"])
                self.assertTrue(all(profile is None for profile in self.query(case, record)["profiles"]))

    def test_motion_kernel_budget_holds_every_kernel_but_keeps_all_profiles(self):
        case, original = self.ready("dominant")
        count = original["summary"]["planned_motion_kernels"]
        self.assertGreater(count, 0)
        exact = grounded.build_grounding(*case[0], *case[1:], max_motion_kernels=count)
        self.assertEqual(exact["summary"]["motion_kernels_computed"], count)
        for cap in (0, count - 1):
            record = grounded.build_grounding(*case[0], *case[1:], max_motion_kernels=cap)
            with self.subTest(cap=cap):
                self.assertEqual(record["profile_inventory"], original["profile_inventory"])
                self.assertEqual(record["summary"]["motion_kernels_computed"], 0)
                self.assertEqual(record["summary"]["unassessed_direct_motion_rows"], record["summary"]["logical_function_rows"])
                self.assertTrue(all(not k["motion_kernel_computed"] for k in record["motion_kernel_inventory"]))
                self.assertTrue(all(k["planned_joint_options"] is None for k in record["motion_kernel_inventory"]))

    def test_endpoint_budget_zero_is_unknown_joint_not_exact_zero(self):
        case, record = self.ready("dominant", max_motion_pairs=0)
        result = self.query(case, record, self.logical(case, dominant=True))
        motion = self.motion(result)["motion"]
        self.assertEqual(motion["planned_endpoint_pairs"], 2)
        self.assertIsNone(motion["planned_joint_options"])
        self.assertEqual(motion["joint_options"], [])
        self.assertEqual(motion["status"], "whole_endpoint_motion_budget_abstention")
        self.assertTrue(all(not edges for edges in motion["edge_options"].values()))

    def test_joint_budget_zero_holds_product_one_and_exact_one_admits_all(self):
        case, held = self.ready("dominant", max_joint_options=0)
        logical = self.logical(case, dominant=True)
        motion = self.motion(self.query(case, held, logical))["motion"]
        self.assertEqual(motion["planned_joint_options"], 1)
        self.assertEqual(motion["joint_options"], [])
        self.assertEqual(motion["status"], "whole_joint_motion_budget_abstention")
        ready = grounded.build_grounding(*case[0], *case[1:], max_joint_options=1)
        motion = self.motion(self.query(case, ready, logical))["motion"]
        self.assertEqual(motion["status"], "conditional_joint_direct_motion_shape")

    def test_known_empty_catalogue_is_exact_zero_without_fabricated_neutral_tuple(self):
        case = self.frozen_case(self.make([[event("C3", 0, 4)]]))
        record = grounded.build_grounding(*case[0], *case[1:], max_profiles=0, max_motion_kernels=0)
        self.assertEqual(record["summary"]["logical_function_rows"], 0)
        self.assertEqual(record["summary"]["unknown_product_groups"], 0)
        self.assertEqual(record["summary"]["planned_profiles"], 0)
        self.assertTrue(record["summary"]["literal_profiles_complete"])
        with self.assertRaises(ValueError):
            grounded.query_grounded_prepared(self.session(case, record), case[2]["path_groups"][0]["group_id"], [], case[1]["keys"][0]["record_id"])

    def test_whole_index_hold_has_known_products_but_no_admitted_profile_or_function(self):
        case = self.frozen_case(self.make(index_options={"max_variants": 0}))
        record = grounded.build_grounding(*case[0], *case[1:])
        self.assertGreater(record["summary"]["logical_function_rows"], 0)
        self.assertEqual(record["profile_inventory"], [])
        self.assertFalse(record["summary"]["literal_profiles_complete"])
        result = self.query(case, record)
        self.assertTrue(all(p is None for p in result["profiles"]))
        self.assertTrue(all(row["function"] is None for row in result["functions"]))

    def test_supplier_hold_keeps_unknown_group_denominators_distinct_from_zero(self):
        case = self.frozen_case(self.make([[event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]],
            build_options={"max_catalogs": 2, "path_budget": 1}))
        record = grounded.build_grounding(*case[0], *case[1:])
        self.assertGreater(record["summary"]["unknown_product_groups"], 0)
        self.assertFalse(record["summary"]["literal_profiles_complete"])
        self.assertIsNone(record["summary"]["planned_motion_kernels"])
        self.assertTrue(all(g["grounding_counts"]["logical_function_rows"] is None
                            and g["grounding_counts"]["unassessed_direct_motion_rows"] is None for g in record["path_groups"]))

    def test_invalid_caps_are_rejected_before_source_reads(self):
        for field in ("max_profiles", "max_motion_kernels", "max_motion_pairs", "max_joint_options"):
            for value in (-1, True, 1.5, None, "1"):
                with self.subTest(field=field, value=value), patch.object(expanded, "check_scope", side_effect=AssertionError("no source read")):
                    with self.assertRaises(ValueError): grounded.build_grounding(None, None, None, None, None, **{field: value})

    def test_qualified_motion_edges_match_frozen_endpoint_oracle_exactly(self):
        case, record = self.ready("dominant")
        logical = self.logical(case, dominant=True)
        result = self.query(case, record, logical)
        segments = [self.variants(case[1])[ref] for ref in logical[1]]
        for wrapper in result["functions"]:
            if wrapper["motion"] is None:
                continue
            options, blockers, count, held = frozen._motion_options(case[0][1], wrapper["function"],
                segments[0], segments[1], result["profiles"], 65536)
            self.assertEqual(wrapper["motion"]["edge_options"], options)
            self.assertEqual(wrapper["motion"]["planned_endpoint_pairs"], count)
            self.assertFalse(held)
            self.assertTrue(set(blockers) <= set(wrapper["motion"]["blockers"]))

    def test_incompatible_union_has_certified_geometry_zero_not_unknown(self):
        case, record = self.ready("incompatible")
        session = self.session(case, record)
        links = set()
        for quality in ("M", "m"):
            result = grounded.query_grounded_prepared(session, *self.target_logical(case, quality))
            motion = self.motion(result, quality=quality)["motion"]
            self.assertEqual(motion["supported_joint_options"], 1)
            links.update(tuple(pair) for pair in motion["joint_options"][0]["required_links"])
        bundle = grounded._bundle(case[0][1], case[2], case[3], record["logical_universe"], tuple(sorted(links)))
        self.assertEqual(bundle["geometry_condition_status"], "impossible")
        self.assertTrue(any(entry["query"]["possible_assignments"] == "0" for entry in bundle["entries"]))
        self.assertNotEqual(bundle["status"], "complete_all_lane_witness")
        self.assertFalse(bundle["flags"]["independent_witnesses_unioned"])

    def test_endpoint_and_joint_holds_have_null_supported_denominators(self):
        for cap in ({"max_motion_pairs": 0}, {"max_joint_options": 0}):
            case, record = self.ready("dominant", **cap)
            motion = self.motion(self.query(case, record, self.logical(case, dominant=True)))["motion"]
            self.assertIsNone(motion["supported_joint_options"])
            self.assertEqual(motion["qualifying_bundle_refs"], [])
            self.assertEqual(record["summary"]["grounded_conditional_direct_motion_shape_rows"], 0)

    def test_held_inventory_known_subtotals_do_not_claim_complete_zero(self):
        case = self.frozen_case(self.make(index_options={"max_variants": 0}))
        record = grounded.build_grounding(*case[0], *case[1:])
        for field in ("planned_profiles", "planned_profile_row_uses", "planned_profile_cell_uses", "planned_motion_kernels"):
            self.assertIsNone(record["summary"][field])
        self.assertEqual(record["summary"]["known_stored_profile_descriptors"], 0)
        self.assertEqual(record["summary"]["literal_profiles_computed"], 0)
        self.assertIsNone(record["baseline_bundle_ref"])
        self.assertEqual(record["bundle_inventory"], [])
        result = self.query(case, record)
        self.assertEqual(result["status"], "withheld_source_relation_tuple")
        self.assertEqual(result["computed_counts"]["pure_function_rows"], 0)

    def test_exact_half_open_profiles_do_not_move_boundary_attacks_or_releases(self):
        case, record = self.ready("dominant")
        result = self.query(case, record, self.logical(case, dominant=True))
        sounds = {s["sound_ref"]: s for s in case[0][1]["sound_facts"]}
        left, right = result["profiles"]
        self.assertTrue(all(common.f(sounds[row["sound_ref"]]["span"]["start"]) < 2 for row in left["rows"]))
        self.assertTrue(all(common.f(sounds[row["sound_ref"]]["span"]["end"]) > 2 for row in right["rows"]))
        for motion in (r["motion"] for r in result["functions"] if r["motion"] is not None):
            for edge in (e for edges in motion["edge_options"].values() for e in edges):
                self.assertEqual(common.f(sounds[edge["source_ref"]]["span"]["end"]), 2)
                self.assertEqual(common.f(sounds[edge["target_ref"]]["span"]["start"]), 2)

    def test_same_pitch_classes_in_distinct_spans_are_not_one_literal_profile(self):
        case = self.frozen_case(self.make([[event(["C3", "E4", "G4"], 0, 2), event(["C3", "E4", "G4"], 2, 2)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        semantic_groups = {}
        for row in record["profile_inventory"]:
            semantic = row["semantic_input"]
            key = shapes.digest({k: v for k, v in semantic.items() if k != "span"})
            semantic_groups.setdefault(key, []).append(row)
        reused = [rows for rows in semantic_groups.values() if len({shapes.digest(r["semantic_input"]["span"]) for r in rows}) > 1]
        self.assertTrue(reused)
        for rows in reused:
            self.assertEqual(len({r["record_id"] for r in rows}), len(rows))
            self.assertGreater(len({shapes.digest(r["profile_core"]) for r in rows}), 1)

    def test_tie_continuation_is_one_sound_not_a_new_direct_endpoint(self):
        case = self.frozen_case(self.make([[event("B4", 0, 1, tie_role="start"), event("B4", 1, 1, tie_role="stop"), event("C5", 2, 2)],
            [event("F4", 0, 2), event("E4", 2, 2)], [event("G3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G4", 2, 2)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        tied = next(s for s in case[0][1]["sound_facts"] if len(s["source_note_refs"]) == 2)
        result = self.query(case, record, self.logical(case, dominant=True))
        self.assert_oracle(case, self.logical(case, dominant=True), result)
        self.assertEqual(tied["span"], span(0, 2))
        self.assertEqual([r["sound_ref"] for r in result["profiles"][0]["rows"]].count(tied["sound_ref"]), 1)
        motion = self.motion(result)["motion"]
        self.assertEqual(motion["status"], "conditional_joint_direct_motion_shape")
        self.assertEqual(len([e for e in motion["edge_options"]["leading_tone"] if e["source_ref"] == tied["sound_ref"]]), 1)

    def test_silence_gap_is_not_bridged_or_reported_as_delayed_resolution(self):
        case = self.frozen_case(self.make([[event("B4", 0, 1), event(None, 1, 1), event("C5", 2, 2)],
            [event("F4", 0, 2), event("E4", 2, 2)], [event("G3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G4", 2, 2)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        result = self.query(case, record, self.logical(case, dominant=True))
        motion = self.motion(result)["motion"]
        self.assertEqual(motion["edge_options"]["leading_tone"], [])
        self.assertEqual(motion["planned_joint_options"], 0)
        self.assertEqual(motion["supported_joint_options"], 0)
        self.assertEqual(motion["status"], "withheld_direct_motion_prerequisites")
        self.assertIn("leading_tone_touching_source_member_endpoint_not_observed", motion["blockers"])
        self.assertEqual(result["conditional_NCT_and_delayed_resolution"], "unassessed")

    def test_cross_staff_same_raw_voice_remains_direct_motion_not_cross_voice_repair(self):
        def cross_staff(ir):
            originals = list(ir["staves"])
            second_staff = {}
            for staff in originals:
                additional = {**deepcopy(staff), "staff_id": staff["staff_id"] + "_cross", "staff_number": 2}
                ir["staves"].append(additional)
                second_staff[staff["staff_id"]] = additional["staff_id"]
                next(p for p in ir["parts"] if p["part_id"] == staff["part_id"])["staff_ids"].append(additional["staff_id"])
            for row in ir["note_events"]:
                if common.f(row["global_onset_quarter"]) == 2:
                    row["display_staff_id"] = second_staff[row["display_staff_id"]]
        case = self.frozen_case(self.dominant(modify=cross_staff))
        record = grounded.build_grounding(*case[0], *case[1:])
        result = self.query(case, record, self.logical(case, dominant=True))
        motion = self.motion(result)["motion"]
        self.assertEqual(motion["status"], "conditional_joint_direct_motion_shape")
        sounds = {s["sound_ref"]: s for s in case[0][1]["sound_facts"]}
        for edges in motion["edge_options"].values():
            for edge in edges:
                self.assertEqual(sounds[edge["source_ref"]]["lane"], sounds[edge["target_ref"]]["lane"])

    def test_different_raw_voices_do_not_supply_each_others_touching_endpoints(self):
        case = self.frozen_case(self.make([[event("B4", 0, 2), event(None, 2, 2)],
            [event(None, 0, 2), event("C5", 2, 2)], [event("F4", 0, 2), event("E4", 2, 2)],
            [event("G3", 0, 2), event("C3", 2, 2)], [event("D4", 0, 2), event("G4", 2, 2)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        motion = self.motion(self.query(case, record, self.logical(case, dominant=True)))["motion"]
        self.assertEqual(motion["edge_options"]["leading_tone"], [])
        self.assertEqual(motion["supported_joint_options"], 0)

    def test_nonmember_bass_is_not_reclassified_as_nct_or_harmonic_inversion(self):
        case = self.frozen_case(self.make([[event("B4", 0, 2), event("C5", 2, 2)],
            [event("F4", 0, 2), event("E4", 2, 2)], [event("G3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G4", 2, 2)], [event("F#2", 0, 4)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        result = self.query(case, record, self.logical(case, dominant=True))
        self.assertEqual(self.motion(result)["function"]["status"], "conditional_function_shape")
        motion = self.motion(result)["motion"]
        self.assertEqual(motion["status"], "withheld_direct_motion_prerequisites")
        self.assertEqual(motion["supported_joint_options"], 0)
        self.assertIn("source_actual_member_bass_unknown_or_nonmember", motion["blockers"])
        self.assertIn("target_actual_member_bass_unknown_or_nonmember", motion["blockers"])
        self.assertEqual(record["summary"]["conditional_NCT_rules_computed"], 0)

    def test_missing_source_attack_is_not_rescued_by_healthy_same_spelled_doubling(self):
        def missing_attack(ir):
            bad = next(s for s in ir["sounding_events"] if s["pitch"]["spelling"] == "B3")
            ir["attack_events"] = [a for a in ir["attack_events"] if a["sounding_event_id"] != bad["sounding_event_id"]]
        case = self.frozen_case(self.make([[event(["G3", "B3", "D4", "F4"], 0, 2), event(["C4", "E4", "G4"], 2, 2)],
            [event("B4", 0, 2), event("C5", 2, 2)]], extent=span(3, 4), modify=missing_attack))
        record = grounded.build_grounding(*case[0], *case[1:])
        bad = next(s for s in case[0][1]["sound_facts"] if s["pitch"]["spelling"] == "B3")
        result = self.query(case, record, self.logical(case, dominant=True))
        motion = self.motion(result)["motion"]
        edges = [e for e in motion["edge_options"]["leading_tone"] if e["source_ref"] == bad["sound_ref"]]
        self.assertTrue(edges)
        self.assertTrue(all(not e["qualified"] for e in edges))
        for edge in edges:
            self.assertIn("source_attack_lineage_not_passed:" + bad["sound_ref"], edge["blockers"])
        self.assertTrue(any(e["qualified"] for e in motion["edge_options"]["leading_tone"]))
        self.assertTrue(all(bad["sound_ref"] not in [link[0] for link in option["required_links"]] for option in motion["joint_options"]))

    def test_point_grace_raw_lane_keeps_literal_facts_but_whole_bundle_unknown(self):
        case = self.frozen_case(self.make([[event("B4", 0, 2), event("C5", 2, 2)],
            [event("F4", 0, 2), event("E4", 2, 2)], [event("G3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G4", 2, 2)],
            [event(None, 0, 1), event("A4", 1, 0, grace=True), event(None, 1, 3)]], extent=span(3, 4)))
        record = grounded.build_grounding(*case[0], *case[1:])
        points = [s["sound"] for s in record["source_inventory"] if s["sound"]["point"]]
        self.assertEqual(len(points), 1)
        self.assertTrue(points[0]["grace"])
        self.assertTrue(all(r["value"]["sound_ref"] != points[0]["sound_ref"] for r in record["row_inventory"]))
        self.assertTrue(record["bundle_inventory"])
        self.assertTrue(all(b["geometry_condition_status"] == "unknown" for b in record["bundle_inventory"]))
        self.assertEqual(record["summary"]["grounded_conditional_direct_motion_shape_rows"], 0)
        self.assertEqual(record["summary"]["conditional_NCT_rules_computed"], 0)

    def test_full_tie_clock_gap_guard_remains_visible_in_literal_rows(self):
        case = self.frozen_case(self.make([[event("C4", 0, 1, tie_role="start"), event("C4", 3, 1, tie_role="stop")],
            [event("E4", 0, 4)], [event("G4", 0, 4)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        tied = next(s for s in case[0][1]["sound_facts"] if len(s["source_note_refs"]) == 2)
        rows = [r["value"] for r in record["row_inventory"] if r["value"]["sound_ref"] == tied["sound_ref"]]
        self.assertTrue(rows)
        for row in rows:
            self.assertFalse(row["source_clock_passed"])
            self.assertEqual(row["full_span"], tied["span"])
            self.assertIn("full_source_timeline_gap", row["source_diagnostics"])

    def test_required_headers_and_literal_inventory_types_fail_explicitly(self):
        case, original = self.ready()
        for name in ("contract", "origin_inventory", "path_groups", "summary", "resource_limits", "flags"):
            forged = deepcopy(original)
            del forged[name]
            with self.subTest(field=name), self.assertRaises(ValueError):
                grounded.validate_grounding(*case[0], *case[1:], reseal(forged, grounded.PREFIX))
        for malformed in (None, [], "not_grounding"):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                self.session(case, malformed)
        forged = deepcopy(original)
        forged["profile_inventory"] = tuple(forged["profile_inventory"])
        with self.assertRaises(ValueError): self.session(case, reseal(forged, grounded.PREFIX))

    def test_resealed_profiles_rows_cells_origins_counters_and_promotions_fail(self):
        case, original = self.ready()
        changes = {
            "profile": lambda r: r["profile_inventory"][0]["profile_core"].update(status="confirmed"),
            "row": lambda r: r["row_inventory"][0]["value"].update(source_clock_passed=False),
            "cell": lambda r: r["cell_inventory"][0]["value"].update(bass_source_guards_passed=False),
            "origin": lambda r: r["origin_inventory"][0].update(segment_ref="foreign"),
            "counter": lambda r: r["summary"].update(logical_function_rows=0),
            "source": lambda r: r["source_inventory"][0]["sound"].update(eligible_as_analysis_source=False),
            "selection": lambda r: r.update(selected="winner"),
            "unknown": lambda r: r.update(undeclared=True),
        }
        for kind, change in changes.items():
            forged = deepcopy(original)
            change(forged)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.session(case, reseal(forged, grounded.PREFIX))

    def test_numeric_aliases_are_not_equivalent_canonical_records(self):
        case, original = self.ready()
        for value in (True, float(original["summary"]["origin_variants"])):
            forged = deepcopy(original)
            forged["summary"]["origin_variants"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                grounded.validate_grounding(*case[0], *case[1:], reseal(forged, grounded.PREFIX))
        forged = deepcopy(original)
        forged["resource_limits"]["max_profiles"] = 65536.0
        with self.assertRaises(ValueError): self.session(case, reseal(forged, grounded.PREFIX))

    def test_foreign_ir_scope_hypothesis_index_and_relations_cannot_reuse_grounding(self):
        case, record = self.ready()
        other = self.frozen_case(self.make())
        for position in range(5):
            inputs = [*case[0], *case[1:]]
            inputs[position] = [*other[0], *other[1:]][position]
            with self.subTest(position=position), self.assertRaises(ValueError):
                grounded.validate_grounding(*inputs, record)

    def test_prepared_session_is_detached_and_results_have_no_caller_aliases(self):
        case, record = self.ready("dominant")
        logical = self.logical(case, dominant=True)
        session = self.session(case, record)
        expected = grounded.query_grounded_prepared(session, *logical)
        case[0][0]["sounding_events"][0]["pitch"]["spelling"] = "foreign"
        case[0][1]["sound_facts"][0]["source_clock_passed"] = False
        case[1]["catalog_inventory"] = []
        record["profile_inventory"][0]["row_ids"].clear()
        actual = grounded.query_grounded_prepared(session, *logical)
        self.assertEqual(actual, expected)
        actual["profiles"][0]["rows"].clear()
        actual["functions"][0]["function"]["blockers"].append("caller")
        self.assertEqual(grounded.query_grounded_prepared(session, *logical), expected)

    def test_current_contract_changes_and_unissued_sessions_are_rejected(self):
        case, record = self.ready()
        session = self.session(case, record)
        logical = self.logical(case)
        for forged in (None, {}, grounded._PreparedGrounding()):
            with self.subTest(forged=forged), self.assertRaises(ValueError):
                grounded.query_grounded_prepared(forged, *logical)
        contract = deepcopy(grounded._contract())
        contract["source_sha256"] = "0" * 64
        with patch.object(grounded, "_contract", return_value=contract):
            with self.assertRaises(ValueError): grounded.query_grounded_prepared(session, *logical)
            with self.assertRaises(ValueError): self.session(case, record)

    def test_typed_complete_tuple_selectors_and_partition_membership_are_enforced(self):
        case, record = self.ready("dominant")
        session = self.session(case, record)
        group, ids, key = self.logical(case, dominant=True)
        invalid = [(True, ids, key), (group, ids, True), (group, ids[0], key),
                   (group, [True, ids[1]], key), (group, ids[:1], key),
                   (group, [ids[0], ids[0]], key), (group, list(reversed(ids)), key),
                   (group, ids, "foreign"), ("foreign", ids, key)]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                grounded.query_grounded_prepared(session, *args)

    def test_queries_assessments_and_existing_bundle_are_exact_fresh_sealed_snapshots(self):
        case, record = self.ready("dominant")
        logical = self.logical(case, dominant=True)
        query = self.query(case, record, logical)
        bundle = next(b for b in record["bundle_inventory"] if b["all_no_link_control"])
        assessment = grounded.assess_grounded(*case[0], *case[1:], record, bundle, *logical)
        self.assertTrue(grounded.validate_query(*case[0], *case[1:], record, *logical, query))
        self.assertTrue(grounded.validate_assessment(*case[0], *case[1:], record, bundle, *logical, assessment))
        for field in ("profiles", "functions", "flags"):
            forged = deepcopy(query)
            forged[field] = [] if field != "flags" else {**forged[field], "nct_evaluated": True}
            with self.subTest(field=field), self.assertRaises(ValueError):
                grounded.validate_query(*case[0], *case[1:], record, *logical, reseal(forged, grounded.QUERY_PREFIX))
        forged = deepcopy(assessment)
        forged["rows"][0]["function_confirmed"] = True
        with self.assertRaises(ValueError):
            grounded.validate_assessment(*case[0], *case[1:], record, bundle, *logical, reseal(forged, grounded.ASSESSMENT_PREFIX))
        forged = deepcopy(bundle)
        forged["symbolic_universe_ref"] = common.ref(case[2]["universe"])
        with self.assertRaises(ValueError):
            grounded.assess_grounded_prepared(self.session(case, record), reseal(forged, grounded.BUNDLE_PREFIX), *logical)

    def test_selected_prepared_queries_never_rebuild_profiles_suppliers_or_cartesian_paths(self):
        case, record = self.ready("dominant")
        logical = self.logical(case, dominant=True)
        session = self.session(case, record)
        expected = grounded.query_grounded_prepared(session, *logical)
        bundle = next(b for b in record["bundle_inventory"] if b["all_no_link_control"])
        with patch.object(frozen, "_profile", side_effect=AssertionError("no profile rebuild")), \
                patch.object(frozen, "_function", side_effect=AssertionError("no pure function rebuild")), \
                patch.object(frozen, "_motion_options", side_effect=AssertionError("no motion rebuild")), \
                patch.object(catalog, "propose", side_effect=AssertionError("no supplier rebuild")), \
                patch.object(indexed, "query_prepared", side_effect=AssertionError("no old tuple evaluator")), \
                patch.object(grounded, "product", side_effect=AssertionError("no Cartesian tuple materialization")):
            self.assertEqual(grounded.query_grounded_prepared(session, *logical), expected)
            assessed = grounded.assess_grounded_prepared(session, bundle, *logical)
            self.assertEqual(assessed["computed_counts"]["queried_tuples"], 1)

    def test_genuine_microtonal_literal_pitch_is_preserved_and_not_eligible(self):
        def microtone(ir):
            note = next(n for n in ir["note_events"] if n["written_pitch"]["spelling"] == "C4")
            for field in ("written_pitch", "concert_pitch"):
                note[field].update(alter=common.q(Fraction(1, 2)), spelling="C-half-sharp4", midi_pitch=None, pitch_class=None)
            sound = next(s for s in ir["sounding_events"] if note["note_id"] in s["source_note_ids"])
            sound["pitch"] = deepcopy(note["written_pitch"])
        case = self.frozen_case(self.make([[event("C4", 0, 1), event(None, 1, 3)],
            [event("E4", 1, 3)], [event("G4", 1, 3)]], extent=span(2, 3), modify=microtone))
        record = grounded.build_grounding(*case[0], *case[1:])
        sound = next(s for s in case[0][1]["sound_facts"] if common.f(s["pitch"]["alter"]) == Fraction(1, 2))
        retained = next(s["sound"] for s in record["source_inventory"] if s["sound"]["sound_ref"] == sound["sound_ref"])
        self.assertEqual(retained, sound)
        self.assertFalse(retained["eligible_as_analysis_source"])
        self.assertTrue(retained["source_pitch_consistency_passed"])
        rows = [r["value"] for r in record["row_inventory"] if r["value"]["sound_ref"] == sound["sound_ref"]]
        self.assertTrue(rows)
        self.assertTrue(all(r["pitch"]["alter"] == common.q(Fraction(1, 2)) for r in rows))
        self.assertFalse(record["flags"]["nct_evaluated"])

    def test_octave_equivalent_pitch_class_does_not_replace_direct_spelled_step(self):
        case = self.frozen_case(self.make([[event("B4", 0, 2), event("C4", 2, 2)],
            [event("F4", 0, 2), event("E4", 2, 2)], [event("G3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G4", 2, 2)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        motion = self.motion(self.query(case, record, self.logical(case, dominant=True)))["motion"]
        edges = motion["edge_options"]["leading_tone"]
        self.assertEqual(len(edges), 1)
        self.assertFalse(edges[0]["qualified"])
        self.assertEqual(common.f(edges[0]["motion"]["semitones"]), -11)
        self.assertEqual(motion["supported_joint_options"], 0)
        self.assertIn("leading_tone_direct_spelled_motion_not_met", edges[0]["blockers"])

    def test_extended_target_core_can_support_motion_without_ordinary_inversion_claim(self):
        case = self.frozen_case(self.make([[event("B4", 0, 2), event("C5", 2, 2)],
            [event("F4", 0, 2), event("E4", 2, 2)], [event("G3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G4", 2, 2)], [event(None, 0, 2), event(["B-3", "D5"], 2, 2)]]))
        record = grounded.build_grounding(*case[0], *case[1:])
        group, ids, key = self.logical(case, dominant=True)
        variants = self.variants(case[1])
        target_slot = next(g for g in case[2]["path_groups"] if g["group_id"] == group)["slots"][1]
        desired = {(step, Fraction()) for step in "CEGD"} | {("B", Fraction(-1))}
        target = next(ref for ref in target_slot["variant_ids"] if variants[ref]["root"] == {"step": "C", "alter": common.q(0)}
            and variants[ref]["members"] is not None and {common.pitch_key(p) for p in variants[ref]["members"]} == desired)
        logical = group, [ids[0], target], key
        result = self.query(case, record, logical)
        self.assert_oracle(case, logical, result)
        self.assertTrue(self.motion(result)["function"]["target_shape_compatible"])
        self.assertEqual(self.motion(result)["motion"]["status"], "conditional_joint_direct_motion_shape")
        target_cell = result["profiles"][1]["cells"][0]
        self.assertEqual(target_cell["conditional_inversions"], [])
        self.assertEqual(target_cell["inversion_basis"], "rootless_extended_or_nontertian_inversion_unassessed")
        self.assertTrue(target_cell["conditional_bass_member_indices"])

    def test_input_mutation_during_owned_build_cannot_produce_record(self):
        case, _ = self.ready()
        original = grounded._profiles
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            case[1]["flags"]["caller_mutation"] = True
            return result
        with patch.object(grounded, "_profiles", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "changed_during_build"):
                grounded.build_grounding(*case[0], *case[1:])

    def test_replaced_owned_session_state_cannot_inherit_another_authentication(self):
        case, record = self.ready()
        first, second = self.session(case, record), self.session(case, record)
        original = grounded._SESSIONS[first]
        try:
            grounded._SESSIONS[first] = grounded._SESSIONS[second]
            with self.assertRaisesRegex(ValueError, "owned_state_changed"):
                grounded.query_grounded_prepared(first, *self.logical(case))
        finally:
            grounded._SESSIONS[first] = original

    def test_admitted_zero_endpoint_product_stays_exact_zero_at_zero_caps(self):
        case = self.frozen_case(self.make([[event("B4", 0, 2), event(None, 2, 2)],
            [event(None, 0, 2), event("C5", 2, 2)], [event("F4", 0, 2), event(None, 2, 2)],
            [event(None, 0, 2), event("E4", 2, 2)], [event("G3", 0, 2), event("C3", 2, 2)],
            [event("D4", 0, 2), event("G4", 2, 2)]]))
        record = grounded.build_grounding(*case[0], *case[1:], max_motion_pairs=0, max_joint_options=0)
        motion = self.motion(self.query(case, record, self.logical(case, dominant=True)))["motion"]
        self.assertEqual(motion["planned_endpoint_pairs"], 0)
        self.assertEqual(motion["planned_joint_options"], 0)
        self.assertEqual(motion["supported_joint_options"], 0)
        self.assertEqual(motion["status"], "withheld_direct_motion_prerequisites")

    def test_source_written_pitch_mismatch_cannot_borrow_guard_of_healthy_doubling(self):
        def mismatch(ir):
            note = next(n for n in ir["note_events"] if n["written_pitch"]["spelling"] == "B3")
            replacement = next(n["written_pitch"] for n in ir["note_events"] if n["written_pitch"]["spelling"] == "D4")
            note["written_pitch"] = deepcopy(replacement)
            note["concert_pitch"] = deepcopy(replacement)
        case = self.frozen_case(self.make([[event(["G3", "B3", "D4", "F4"], 0, 2), event(["C4", "E4", "G4"], 2, 2)],
            [event("B4", 0, 2), event("C5", 2, 2)]], extent=span(3, 4), modify=mismatch))
        record = grounded.build_grounding(*case[0], *case[1:])
        bad = next(s for s in case[0][1]["sound_facts"] if s["pitch"]["spelling"] == "B3")
        self.assertFalse(bad["source_pitch_consistency_passed"])
        motion = self.motion(self.query(case, record, self.logical(case, dominant=True)))["motion"]
        edges = [e for e in motion["edge_options"]["leading_tone"] if e["source_ref"] == bad["sound_ref"]]
        self.assertTrue(edges)
        self.assertTrue(all(not e["qualified"] for e in edges))
        self.assertTrue(all("source_written_pitch_not_passed:" + bad["sound_ref"] in e["blockers"] for e in edges))
        self.assertTrue(any(e["qualified"] for e in motion["edge_options"]["leading_tone"]))


if __name__ == "__main__":
    unittest.main()
