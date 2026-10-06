"""Lossless logical products and explicitly queried, non-ranking comparisons."""
from copy import deepcopy
from fractions import Fraction
from itertools import product
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_expanded_scope as expanded
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_candidate_catalog as catalog
from test_factor_expanded_hypotheses import ExpandedHypothesisFixture, event, span
from test_factor_musical_view import reseal


class IndexedHypothesisFixture(ExpandedHypothesisFixture):
    def make(self, lanes=None, *, build_options=None, index_options=None, **options):
        fx = self.fixture(lanes, **options)
        hyp = frozen.build_hypotheses(*fx, **(build_options or {"path_budget": 1}))
        idx = indexed.build_index(*fx, hyp, **(index_options or {}))
        return fx, hyp, idx

    def prepare(self, case):
        fx, hyp, idx = case
        return indexed.prepare_index(*fx, hyp, idx)

    def variants(self, hyp):
        return {v["record_id"]: v for entry in hyp["catalog_inventory"]
                for v in entry["variants"]}

    def first_tuple(self, hyp, idx, *, kind=None):
        group = next(g for g in idx["path_groups"] if g["logical_path_count"]
                     and (kind is None or g["kind"] == kind))
        ids = [slot["variant_ids"][0] for slot in group["slots"]]
        return group["group_id"], ids, hyp["keys"][0]["record_id"]

    def query(self, case, logical=None, **options):
        fx, hyp, idx = case
        logical = logical or self.first_tuple(hyp, idx)
        return indexed.query(*fx, hyp, idx, *logical, **options)

    def dominant(self, **options):
        return self.make([[event("B4", 0, 2), event("C5", 2, 2)],
                          [event("F4", 0, 2), event("E4", 2, 2)],
                          [event("G3", 0, 2), event("C3", 2, 2)],
                          [event("D4", 0, 2), event("G4", 2, 2)]], **options)

    def dominant_tuple(self, case):
        _, hyp, idx = case
        group = next(g for g in idx["path_groups"] if g["kind"] == "two_segment" and g["cut"] == common.q(2))
        variants = self.variants(hyp)
        source_members = {("G", Fraction()), ("B", Fraction()),
                          ("D", Fraction()), ("F", Fraction())}
        target_members = {("C", Fraction()), ("E", Fraction()), ("G", Fraction())}
        wanted = [("G", source_members), ("C", target_members)]
        ids = []
        for slot, (root, members) in zip(group["slots"], wanted):
            ids.append(next(ref for ref in slot["variant_ids"]
                            if variants[ref]["root"] is not None
                            and common.pitch_key(variants[ref]["root"]) == (root, Fraction())
                            and variants[ref]["members"] is not None
                            and {common.pitch_key(p) for p in variants[ref]["members"]} == members))
        return group["group_id"], ids, hyp["keys"][0]["record_id"]

    def assert_oracle(self, scope, hyp, logical, actual, *, cap=65536):
        _, ids, key_id = logical
        variants = self.variants(hyp)
        segments = [variants[ref] for ref in ids]
        key = next(k for k in hyp["keys"] if k["record_id"] == key_id)
        profiles = [frozen._profile(scope, segment) for segment in segments]
        self.assertEqual(actual["profiles"], profiles)
        expected_functions = []
        for n, source in enumerate(segments):
            target = segments[n + 1] if n + 1 < len(segments) else None
            for family in frozen.FAMILIES:
                for quality in ("M", "m"):
                    row = frozen._function(scope, source, target, key["segments"][0], family, quality)
                    options, blockers, count, held = frozen._motion_options(
                        scope, row, source, target, profiles[n:n + 2], cap)
                    expected_functions.append((row, options, blockers, count, held))
        self.assertEqual(len(actual["functions"]), len(expected_functions))
        for function, (row, options, blockers, count, held) in zip(actual["functions"], expected_functions):
            body = {k: v for k, v in function.items() if k not in ("function_id", "motion")}
            self.assertEqual(body, row)
            motion = function["motion"]
            self.assertEqual(motion["edge_options"], options)
            self.assertEqual(motion["planned_endpoint_pairs"], count)
            self.assertTrue(set(blockers) <= set(motion["blockers"]))
            if held:
                self.assertIsNone(motion["total_joint_options"])
                self.assertEqual(motion["status"], "whole_group_budget_abstention")
                self.assertEqual(motion["joint_options"], [])
            else:
                joint_count = 1
                for edges in options.values():
                    joint_count *= sum(edge["qualified"] for edge in edges)
                self.assertEqual(motion["total_joint_options"], joint_count)


class IndexedHypothesisTests(IndexedHypothesisFixture, unittest.TestCase):
    def test_new_typed_index_reproducible_exact_parents_and_no_aliases(self):
        case = self.make()
        fx, hyp, idx = case
        before = deepcopy(case)
        self.assertTrue(idx["record_id"].startswith("fmiidx_"))
        self.assertEqual(idx["scope_ref"], common.ref(fx[1]))
        self.assertEqual(idx["hypotheses_ref"], common.ref(hyp))
        self.assertEqual(indexed.build_index(*fx, hyp), idx)
        self.assertTrue(indexed.validate_index(*fx, hyp, idx))
        self.assertEqual(case, before)
        hyp["catalog_inventory"][0]["variants"][0]["blockers"].append("caller_mutation")
        self.assertEqual(idx, before[2])

    def test_full_catalogue_origins_and_every_variant_preserved_without_pc_dedup(self):
        case = self.make([[event(["C3", "E3", "B3", "B-3", "D4", "A-3", "F#4"], 0, 4)]])
        _, hyp, idx = case
        old = self.variants(hyp)
        inventory = idx["variant_inventory"]
        self.assertEqual([r["variant_id"] for r in inventory], list(old))
        self.assertEqual(len(inventory), hyp["summary"]["spelling_variants"])
        self.assertEqual({r["variant"]["provider"] for r in inventory},
                         {"base", "additional_seventh", "augmented", "extended"})
        for row in inventory:
            self.assertEqual(row["variant"], old[row["variant_id"]])
            self.assertEqual(row["segment_ref"], row["variant"]["segment_id"])

    def test_all_partitions_slots_order_and_logical_products_match_frozen_holds(self):
        case = self.make([[event(["C3", "E4", "G4"], 0, 2), event(["D3", "F4", "A4"], 2, 2)]])
        _, hyp, idx = case
        entries = {e["catalog_id"]: e for e in hyp["catalog_inventory"]}
        self.assertEqual(len(idx["path_groups"]), len(hyp["path_groups"]))
        for old, group in zip(hyp["path_groups"], idx["path_groups"]):
            self.assertEqual(group["group_id"], old["group_id"])
            self.assertEqual(group["partition"], old["partition"])
            self.assertEqual(group["old_status"], old["status"])
            self.assertEqual(group["old_reasons"], old["reasons"])
            self.assertEqual(group["logical_path_count"], old["planned_paths"])
            self.assertEqual(group["logical_tuple_count"], old["planned_paths"] * len(hyp["keys"]))
            self.assertEqual(group["logical_function_count"], group["logical_tuple_count"] * len(old["partition"]) * 10)
            for slot, catalog_id in zip(group["slots"], old["catalog_refs"]):
                self.assertEqual(slot["catalog_id"], catalog_id)
                self.assertEqual(slot["span"], entries[catalog_id]["span"])
                self.assertEqual(slot["variant_ids"], [v["record_id"] for v in entries[catalog_id]["variants"]])
            self.assertEqual(group["status"], "ready_factorized_group")
        self.assertTrue(all(g["paths"] == [] for g in hyp["path_groups"]))

    def test_lazy_descriptors_are_not_falsely_materialized_profiles_or_tuple_rows(self):
        fx, hyp, idx = self.make()
        self.assertTrue(idx["profile_inventory"])
        for profile in idx["profile_inventory"]:
            self.assertTrue(profile["record_id"].startswith("fmiprofile_"))
            self.assertIn("semantic_input", profile)
            self.assertNotIn("rows", profile)
            self.assertNotIn("cells", profile)
        self.assertTrue(all("rows" not in group and "paths" not in group for group in idx["path_groups"]))
        self.assertTrue(all(value is False for value in idx["flags"].values()))
        self.assertIsNone(idx["confidence"])

    def test_every_103_real_small_logical_tuple_matches_frozen_profile_function_and_motion(self):
        case = self.make([[event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]])
        fx, hyp, idx = case
        session = self.prepare(case)
        queried = 0
        for group in idx["path_groups"]:
            actual_count = 0
            for ids in product(*(slot["variant_ids"] for slot in group["slots"])):
                for key in hyp["keys"]:
                    logical = (group["group_id"], list(ids), key["record_id"])
                    result = indexed.query_prepared(session, *logical)
                    self.assert_oracle(fx[1], hyp, logical, result)
                    queried += 1
                    actual_count += 1
            self.assertEqual(actual_count, group["logical_tuple_count"])
        self.assertEqual(queried, 103)
        self.assertEqual(sum(g["logical_path_count"] for g in idx["path_groups"]), 103)

    def test_125_full_hold_key_tuples_match_frozen_eager_comparison(self):
        case = self.make(signatures=[{"fifths": 0, "mode_hint": None}], build_options={"path_budget": 4096})
        fx, hyp, idx = case
        eager = frozen.evaluate_hypotheses(*fx, hyp)
        session = self.prepare(case)
        old_paths = {p["record_id"]: p for g in hyp["path_groups"] for p in g["paths"]}
        count = 0
        for group in eager["groups"]:
            for old in group["rows"]:
                path = old_paths[old["path_ref"]["record_id"]]
                logical = (group["group_id"], [s["record_id"] for s in path["segments"]], old["key_ref"]["record_id"])
                result = indexed.query_prepared(session, *logical)
                self.assertEqual(result["profiles"], old["profiles"])
                self.assert_oracle(fx[1], hyp, logical, result)
                for new_fn, old_fn in zip(result["functions"], old["functions"]):
                    self.assertEqual({k: v for k, v in new_fn.items() if k not in ("function_id", "motion")},
                                     {k: v for k, v in old_fn.items() if k not in ("function_id", "motion")})
                    for field in ("edge_options", "total_joint_options", "planned_endpoint_pairs", "blockers", "status"):
                        self.assertEqual(new_fn["motion"][field], old_fn["motion"][field])
                count += 1
        self.assertEqual(count, 125)

    def test_public_query_does_not_regenerate_provider_or_eager_hypothesis_products(self):
        case = self.make()
        with patch.object(catalog, "propose", side_effect=AssertionError("provider regeneration forbidden")), \
             patch.object(frozen, "build_hypotheses", side_effect=AssertionError("path enumeration forbidden")), \
             patch.object(frozen, "evaluate_hypotheses", side_effect=AssertionError("eager comparison forbidden")):
            result = self.query(case)
        self.assertTrue(result["record_id"].startswith("fmiquery_"))

    def test_whole_variant_cap_retains_every_slot_denominator_no_prefix(self):
        fx, hyp, idx = self.make(index_options={"max_variants": 0})
        self.assertEqual(idx["variant_inventory"], [])
        self.assertEqual(idx["profile_inventory"], [])
        self.assertEqual(sum(len(slot["variant_ids"]) for g in idx["path_groups"] for slot in g["slots"]),
                         hyp["summary"]["spelling_variants"])
        self.assertEqual(idx["path_groups"][0]["logical_path_count"], hyp["path_groups"][0]["total_paths"])
        result = self.query(((fx[0], fx[1]), hyp, idx))
        self.assertEqual(result["profiles"], [])
        self.assertEqual(result["functions"], [])
        self.assertTrue(indexed.validate_index(*fx, hyp, idx))

    def test_supplier_catalogue_hold_not_lifted_by_new_index(self):
        fx, hyp, idx = self.make([[event(["C3", "E4", "G4"], 0, 2), event(["D3", "F4", "A4"], 2, 2)]],
                                 build_options={"max_catalogs": 2, "path_budget": 1})
        self.assertEqual(idx["variant_inventory"], [])
        self.assertTrue(all(g["status"] == "source_supplier_hold" and g["logical_path_count"] is None
                            for g in idx["path_groups"]))
        self.assertEqual(len(idx["catalog_inventory"]), 3)
        self.assertTrue(indexed.validate_index(*fx, hyp, idx))

    def test_empty_catalogue_product_is_zero_not_an_invented_neutral_path(self):
        fx, hyp, idx = self.make([[event("C3", 0, 4)]])
        self.assertEqual(idx["path_groups"][0]["logical_path_count"], 0)
        self.assertEqual(idx["path_groups"][0]["logical_tuple_count"], 0)
        self.assertEqual(idx["variant_inventory"], [])
        with self.assertRaises(ValueError):
            indexed.query(*fx, hyp, idx, idx["path_groups"][0]["group_id"], [], hyp["keys"][0]["record_id"])

    def test_wrong_group_key_slot_catalogue_reversed_or_duplicate_tuple_rejected(self):
        case = self.dominant()
        fx, hyp, idx = case
        logical = self.dominant_tuple(case)
        group, ids, key = logical
        invalid = (("fmehgroup_" + "0" * 24, ids, key),
                   (group, ids, "newkey_" + "0" * 24),
                   (group, ids[:1], key), (group, ids + ids[:1], key),
                   (group, list(reversed(ids)), key), (group, [ids[0], ids[0]], key),
                   (group, ["fmehseg_" + "0" * 24, ids[1]], key))
        session = self.prepare(case)
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                indexed.query_prepared(session, *args)

    def test_query_reproducibility_and_fresh_validation(self):
        case = self.make()
        fx, hyp, idx = case
        logical = self.first_tuple(hyp, idx)
        result = self.query(case, logical)
        self.assertEqual(result, self.query(case, logical))
        self.assertEqual(result, indexed.query_prepared(self.prepare(case), *logical))
        self.assertTrue(indexed.validate_query(*fx, hyp, idx, *logical, result))
        self.assertEqual(result["variant_ids"], logical[1])
        self.assertEqual(result["key_ref"]["record_id"], logical[2])

    def test_resealed_index_tamper_unknown_fields_promotion_or_missing_inventory_rejected(self):
        fx, hyp, original = self.make()
        for kind in ("unknown", "promotion", "group", "variant", "profile", "logical_count", "slot"):
            forged = deepcopy(original)
            if kind == "unknown": forged["confidence"] = 0.99
            elif kind == "promotion": forged["flags"]["harmony_confirmed"] = True
            elif kind == "group": forged["path_groups"].pop()
            elif kind == "variant": forged["variant_inventory"].pop()
            elif kind == "profile": forged["profile_inventory"].pop()
            elif kind == "logical_count": forged["path_groups"][0]["logical_tuple_count"] += 1
            else: forged["path_groups"][0]["slots"][0]["variant_ids"].pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                indexed.validate_index(*fx, hyp, reseal(forged, "fmiidx_"))

    def test_resealed_query_tamper_profiles_motion_bundle_or_promotions_rejected(self):
        case = self.make()
        fx, hyp, idx = case
        logical = self.first_tuple(hyp, idx)
        original = self.query(case, logical)
        for kind in ("unknown", "promotion", "profile", "function", "bundle", "tuple"):
            forged = deepcopy(original)
            if kind == "unknown": forged["confidence"] = 0.99
            elif kind == "promotion": forged["flags"]["resolution_confirmed"] = True
            elif kind == "profile": forged["profiles"][0]["total_note_time_quarters"] = common.q(999)
            elif kind == "function": forged["functions"][0]["motion"]["status"] = "confirmed"
            elif kind == "bundle": forged["bundle_inventory"].pop()
            else: forged["variant_ids"] = []
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                indexed.validate_query(*fx, hyp, idx, *logical, reseal(forged, "fmiquery_"))

    def test_resealed_foreign_scope_hypothesis_or_source_is_rejected(self):
        case = self.make()
        fx, hyp, idx = case
        other = self.make()
        with self.assertRaises(ValueError): indexed.validate_index(*other[0], hyp, idx)
        with self.assertRaises(ValueError): indexed.validate_index(*fx, other[1], idx)
        changed = deepcopy(fx[0])
        changed["note_events"][0]["notation"]["new_literal_content"] = "changed"
        with self.assertRaises(ValueError): indexed.query(changed, fx[1], hyp, idx, *self.first_tuple(hyp, idx))

    def test_resealed_frozen_cut_origin_variant_and_key_mutations_rejected_at_build(self):
        fx, original, _ = self.make([[event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]])
        for kind in ("cut", "origin", "variant", "key", "unknown"):
            forged = deepcopy(original)
            if kind == "cut": forged["cut_times"].pop()
            elif kind == "origin":
                v = forged["catalog_inventory"][0]["variants"][0]
                v["supplier_origin_pointer"] = "/foreign/provider/0"
                forged["catalog_inventory"][0]["variants"][0] = reseal(v, "fmehseg_")
            elif kind == "variant": forged["catalog_inventory"][0]["variants"].pop()
            elif kind == "key": forged["keys"].pop()
            else: forged["confidence"] = 0.99
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                indexed.build_index(*fx, reseal(forged, "fmeh_"))

    def test_current_index_supplier_and_frozen_kernel_code_hashes_guard_old_records_and_sessions(self):
        case = self.make()
        fx, hyp, idx = case
        session = self.prepare(case)
        logical = self.first_tuple(hyp, idx)
        original = Path.read_bytes
        for module in (indexed, frozen, catalog):
            target = Path(module.__file__)
            def changed(path):
                raw = original(path)
                return raw + b"\n" if path == target else raw
            with self.subTest(module=module.__name__), patch.object(Path, "read_bytes", changed):
                with self.assertRaises(ValueError): indexed.validate_index(*fx, hyp, idx)
                with self.assertRaises(ValueError): indexed.query_prepared(session, *logical)

    def test_invalid_caps_rejected_before_source_or_hypothesis_reads(self):
        for value in (-1, True, 1.5, None, "1"):
            with self.subTest(value=value), patch.object(expanded, "check_scope", side_effect=AssertionError("no source read")):
                with self.assertRaises(ValueError): indexed.build_index(None, None, None, max_variants=value)
        case = self.make()
        session = self.prepare(case)
        for value in (-1, True, 1.5, None, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                indexed.query_prepared(session, *self.first_tuple(case[1], case[2]), max_motion_pairs=value)
            with self.subTest(public_value=value), patch.object(indexed, "prepare_index", side_effect=AssertionError("no input read")):
                with self.assertRaises(ValueError):
                    indexed.query(None, None, None, None, None, None, None, max_motion_pairs=value)

    def test_unknown_key_preserves_all_shape_functions_without_key_projection_claim(self):
        case = self.make()
        result = self.query(case)
        self.assertEqual({r["family"] for r in result["functions"]}, set(frozen.FAMILIES))
        self.assertEqual({r["target_quality"] for r in result["functions"]}, {"M", "m"})
        self.assertTrue(all(r["function_kind"] == "unassessed" for r in result["functions"]))
        self.assertTrue(all("explicit_key_unknown" in r["key_projection"]["unassessed_reasons"] for r in result["functions"]))

    def test_extended_member_index_does_not_become_ordinary_inversion(self):
        case = self.make([[event(["C3", "E4", "G4", "B-4", "D5"], 0, 4)]])
        fx, hyp, idx = case
        v = next(v for v in self.variants(hyp).values() if v["provider"] == "extended"
                 and v["root"] == {"step": "C", "alter": common.q(0)}
                 and v["members"] is not None and len(v["members"]) > 4)
        logical = (idx["path_groups"][0]["group_id"], [v["record_id"]], hyp["keys"][0]["record_id"])
        result = self.query(case, logical)
        cell = result["profiles"][0]["cells"][0]
        self.assertEqual(cell["conditional_bass_member_indices"], [0])
        self.assertEqual(cell["conditional_inversions"], [])
        self.assertEqual(cell["inversion_basis"], "rootless_extended_or_nontertian_inversion_unassessed")
        self.assert_oracle(fx[1], hyp, logical, result)

    def test_zero_motion_cap_holds_entire_endpoint_group_no_favorable_prefix(self):
        case = self.dominant()
        logical = self.dominant_tuple(case)
        result = self.query(case, logical, max_motion_pairs=0)
        function = next(r for r in result["functions"] if r["family"] == "V7" and r["target_quality"] == "M"
                        and r["source_segment_ref"] == result["profiles"][0]["segment_ref"])
        motion = function["motion"]
        self.assertEqual(motion["planned_endpoint_pairs"], 2)
        self.assertIsNone(motion["total_joint_options"])
        self.assertTrue(all(not edges for edges in motion["edge_options"].values()))
        self.assertEqual(motion["joint_options"], [])
        self.assertEqual(motion["qualifying_bundle_refs"], [])
        self.assertEqual(motion["status"], "whole_group_budget_abstention")
        self.assert_oracle(case[0][1], case[1], logical, result, cap=0)

    def test_exact_variant_cap_admits_all_and_one_less_withholds_all(self):
        fx, hyp, original = self.make()
        count = hyp["summary"]["spelling_variants"]
        exact = indexed.build_index(*fx, hyp, max_variants=count)
        short = indexed.build_index(*fx, hyp, max_variants=count - 1)
        self.assertEqual(len(exact["variant_inventory"]), count)
        self.assertEqual(short["variant_inventory"], [])
        self.assertEqual(short["profile_inventory"], [])
        for left, right in zip(exact["path_groups"], short["path_groups"]):
            self.assertEqual(left["slots"], right["slots"])
            self.assertEqual(left["logical_path_count"], right["logical_path_count"])
            self.assertEqual(left["logical_tuple_count"], right["logical_tuple_count"])

    def test_owned_prepared_inputs_and_returned_profiles_have_no_caller_aliases(self):
        case = self.make()
        fx, hyp, idx = case
        logical = self.first_tuple(hyp, idx)
        session = self.prepare(case)
        first = indexed.query_prepared(session, *logical)
        expected = deepcopy(first)
        first["profiles"][0]["rows"][0]["pitch"]["step"] = "F"
        first["functions"][0]["blockers"].append("returned_mutation")
        fx[1]["sound_facts"][0]["pitch"]["step"] = "A"
        hyp["catalog_inventory"][0]["variants"][0]["blockers"].append("caller_mutation")
        idx["path_groups"][0]["slots"][0]["variant_ids"].clear()
        self.assertEqual(indexed.query_prepared(session, *logical), expected)

    def test_prepared_query_materializes_only_selected_profiles_not_entire_inventory(self):
        case = self.make([[event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]])
        session = self.prepare(case)
        logical = self.first_tuple(case[1], case[2], kind="two_segment")
        with patch.object(frozen, "_profile", wraps=frozen._profile) as observed:
            result = indexed.query_prepared(session, *logical)
        self.assertLessEqual(observed.call_count, 2)
        self.assertEqual(len(result["profiles"]), 2)
        self.assertLess(observed.call_count, len(case[2]["variant_inventory"]))

    def test_rational_cuts_ordered_slots_and_half_open_rows_use_exact_source_clips(self):
        case = self.make([[event(["C3", "E4", "G4"], 0, Fraction(1, 3)),
                           event(["D3", "F4", "A4"], Fraction(1, 3), Fraction(11, 3))]])
        fx, hyp, idx = case
        group = next(g for g in idx["path_groups"] if g["kind"] == "two_segment")
        self.assertEqual(group["cut"], common.q(Fraction(1, 3)))
        logical = self.first_tuple(hyp, idx, kind="two_segment")
        result = self.query(case, logical)
        sounds = {s["sound_ref"]: s for s in fx[1]["sound_facts"]}
        for n, profile in enumerate(result["profiles"]):
            a, b = common.span_bounds(group["partition"][n])
            for row in profile["rows"]:
                c, d = common.span_bounds(sounds[row["sound_ref"]]["span"])
                self.assertLess(max(a, c), min(b, d))
                self.assertEqual(row["full_span"], sounds[row["sound_ref"]]["span"])
                self.assertEqual(row["observed_span"], span(max(a, c), min(b, d)))
        self.assert_oracle(fx[1], hyp, logical, result)

    def test_full_tie_clock_failure_survives_index_and_raw_profile(self):
        case = self.make([[event("C4", 0, 1, tie_role="start"), event("C4", 3, 1, tie_role="stop")],
                          [event("E4", 0, 4)], [event("G4", 0, 4)]])
        fx, hyp, idx = case
        tied = next(s for s in fx[1]["sound_facts"] if len(s["source_note_refs"]) == 2)
        logical = self.first_tuple(hyp, idx)
        result = self.query(case, logical)
        row = next(r for p in result["profiles"] for r in p["rows"] if r["sound_ref"] == tied["sound_ref"])
        self.assertFalse(row["source_clock_passed"])
        self.assertFalse(row["eligible_as_analysis_source"])
        self.assertIn("full_source_timeline_gap", row["source_diagnostics"])
        self.assertEqual(row["full_span"], tied["span"])
        self.assert_oracle(fx[1], hyp, logical, result)

    def test_unspelled_candidate_and_augmented_tonal_coordinate_not_invented_roots(self):
        for lanes, predicate in (([[event(["E3", "G3"], 0, 4)]], lambda v: v["members"] is None),
                                 ([[event(["A-3", "C4", "F#4"], 0, 4)]],
                                  lambda v: v["provider"] == "augmented" and v["tonal_coordinate"] == ["C", 0])):
            case = self.make(lanes)
            fx, hyp, idx = case
            variant = next(v for v in self.variants(hyp).values() if predicate(v))
            self.assertIsNone(variant["root"])
            logical = (idx["path_groups"][0]["group_id"], [variant["record_id"]], hyp["keys"][0]["record_id"])
            result = self.query(case, logical)
            self.assertTrue(all("source_root_not_spelled" in r["blockers"] for r in result["functions"]))
            self.assertTrue(all(not c["conditional_inversions"] for c in result["profiles"][0]["cells"]))
            self.assert_oracle(fx[1], hyp, logical, result)

    def test_direct_critical_roles_use_one_complete_all_lane_bundle(self):
        case = self.dominant()
        fx, hyp, idx = case
        logical = self.dominant_tuple(case)
        result = self.query(case, logical)
        function = next(r for r in result["functions"] if r["family"] == "V7" and r["target_quality"] == "M"
                        and r["source_segment_ref"] == result["profiles"][0]["segment_ref"])
        motion = function["motion"]
        self.assertEqual(motion["status"], "conditional_joint_motion_shape")
        self.assertEqual(motion["total_joint_options"], 1)
        self.assertEqual(len(motion["joint_options"]), 1)
        joint = motion["joint_options"][0]
        self.assertEqual(set(joint["critical_roles"]), {"leading_tone", "seventh"})
        self.assertTrue(joint["all_critical_roles_in_same_bundle"])
        self.assertEqual(len(joint["required_links"]), 2)
        bundle = next(b for b in result["bundle_inventory"] if common.ref(b) == joint["bundle_ref"])
        self.assertTrue(bundle["record_id"].startswith("fmibundle_"))
        self.assertEqual(bundle["status"], "complete_all_lane_witness")
        self.assertEqual(bundle["required_links"], joint["required_links"])
        self.assertEqual(bundle["materialized_witness_links"], joint["required_links"])
        self.assertEqual(len(bundle["entries"]), len(fx[1]["raw_lanes"]))
        # Literal per-lane query completions match the frozen geometry kernel.
        expected = frozen._bundle(fx[1], [], hyp["keys"], joint["required_links"])
        for field in ("required_links", "materialized_witness_links", "entries", "covered_lanes", "status", "reasons"):
            self.assertEqual(bundle[field], expected[field])
        self.assertIsNone(function["function_confirmed"])
        self.assertIsNone(function["cadence"])
        self.assert_oracle(fx[1], hyp, logical, result)

    def test_bad_attack_critical_edge_not_rescued_by_healthy_same_spelled_doubling(self):
        def remove_bad_attack(ir):
            bad = next(s for s in ir["sounding_events"] if s["pitch"]["spelling"] == "B3")
            ir["attack_events"] = [r for r in ir["attack_events"] if r["sounding_event_id"] != bad["sounding_event_id"]]
        case = self.make([[event(["G3", "B3", "D4", "F4"], 0, 2), event(["C4", "E4", "G4"], 2, 2)],
                          [event("B4", 0, 2), event("C5", 2, 2)]],
                         extent=span(3, 4), modify=remove_bad_attack)
        fx, hyp, idx = case
        logical = self.dominant_tuple(case)
        result = self.query(case, logical)
        bad = next(s for s in fx[1]["sound_facts"] if s["pitch"]["spelling"] == "B3")
        healthy = next(s for s in fx[1]["sound_facts"] if s["pitch"]["spelling"] == "B4")
        function = next(r for r in result["functions"] if r["family"] == "V7" and r["target_quality"] == "M"
                        and r["source_segment_ref"] == result["profiles"][0]["segment_ref"])
        edges = function["motion"]["edge_options"]["leading_tone"]
        bad_edges = [e for e in edges if e["source_ref"] == bad["sound_ref"]]
        self.assertTrue(bad_edges)
        self.assertTrue(all(e["qualified"] is False for e in bad_edges))
        for edge in bad_edges:
            self.assertIn("involved_source_not_eligible:" + bad["sound_ref"], edge["blockers"])
            self.assertIn("source_attack_lineage_not_passed:" + bad["sound_ref"], edge["blockers"])
        self.assertTrue(any(e["source_ref"] == healthy["sound_ref"] and e["qualified"] for e in edges))
        for joint in function["motion"]["joint_options"]:
            self.assertTrue(all(pair[0] != bad["sound_ref"] for pair in joint["required_links"]))
        self.assert_oracle(fx[1], hyp, logical, result)

    def test_resealed_frozen_top_level_accounting_status_reasons_and_limits_are_exact(self):
        fx, original, _ = self.make()
        for kind in ("summary", "status", "reasons", "limits", "count_type", "unknown_group"):
            forged = deepcopy(original)
            if kind == "summary": forged["summary"]["complete_paths"] = 999
            elif kind == "status": forged["status"] = "ready"
            elif kind == "reasons": forged["reasons"] = []
            elif kind == "limits": forged["limits"] = []
            elif kind == "count_type": forged["catalog_inventory"][0]["candidate_count"] = float(forged["catalog_inventory"][0]["candidate_count"])
            else: forged["path_groups"][0]["score"] = 0.99
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                indexed.build_index(*fx, reseal(forged, "fmeh_"))

    def test_supplier_held_catalogue_and_group_status_cannot_be_resealed_ready(self):
        fx, original, _ = self.make([[event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]],
                                     build_options={"max_catalogs": 2, "path_budget": 1})
        for kind in ("entry_status", "entry_reasons", "group_status", "group_reasons"):
            forged = deepcopy(original)
            if kind.startswith("entry"):
                forged["catalog_inventory"][0]["status" if kind.endswith("status") else "reasons"] = "ready" if kind.endswith("status") else []
            else:
                forged["path_groups"][0]["status" if kind.endswith("status") else "reasons"] = "ready" if kind.endswith("status") else []
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                indexed.build_index(*fx, reseal(forged, "fmeh_"))

    def test_public_and_prepared_entry_guards_reject_numeric_type_aliases(self):
        case = self.make()
        fx, hyp, original = case
        logical = self.first_tuple(hyp, original)
        for kind in ("zero_bool", "count_float", "logical_float"):
            forged = deepcopy(original)
            if kind == "zero_bool": forged["summary"]["profiles_materialized"] = False
            elif kind == "count_float": forged["catalog_inventory"][0]["candidate_count"] = float(forged["catalog_inventory"][0]["candidate_count"])
            else: forged["path_groups"][0]["logical_path_count"] = float(forged["path_groups"][0]["logical_path_count"])
            forged = reseal(forged, "fmiidx_")
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError): indexed.validate_index(*fx, hyp, forged)
                with self.assertRaises(ValueError): indexed.prepare_index(*fx, hyp, forged)
                with self.assertRaises(ValueError): indexed.query(*fx, hyp, forged, *logical)

    def test_unissued_prepared_handle_and_cache_swaps_are_not_authority(self):
        case = self.make()
        logical = self.first_tuple(case[1], case[2])
        with self.assertRaises(ValueError): indexed.query_prepared(object(), *logical)
        with self.assertRaises(ValueError): indexed.query_prepared(indexed._PreparedIndex(), *logical)
        session = self.prepare(case)
        indexed.query_prepared(session, *logical)
        caches = indexed._PROFILE_CACHES[session]
        profile_id = next(iter(caches))
        original = caches[profile_id]
        caches[profile_id] = (original[0], b"forged_cache_seal")
        with self.assertRaises(ValueError): indexed.query_prepared(session, *logical)

    def test_point_grace_lane_hold_preserves_valid_lanes_but_blocks_complete_joint_witness(self):
        case = self.make([[event("B4", 0, 2), event("C5", 2, 2)],
                          [event("F4", 0, 2), event("E4", 2, 2)],
                          [event("G3", 0, 2), event("C3", 2, 2)],
                          [event("D4", 0, 2), event("G4", 2, 2)],
                          [event("A4", 0, 1), event("A4", 1, 0, grace=True), event("A4", 1, 3)]],
                         extent=span(3, 4))
        fx, hyp, idx = case
        logical = self.dominant_tuple(case)
        result = self.query(case, logical)
        point = next(s for s in fx[1]["sound_facts"] if s["point"])
        self.assertTrue(point["grace"])
        self.assertFalse(point["eligible_as_analysis_source"])
        self.assertTrue(all(point["sound_ref"] not in [r["sound_ref"] for r in p["rows"]]
                            for p in result["profiles"]))
        self.assertEqual(len(fx[1]["graphs"]), 5)
        self.assertTrue(any(g["status"] != "ready" for g in fx[1]["graphs"]))
        self.assertTrue(all(len(b["entries"]) == 5 for b in result["bundle_inventory"]))
        self.assertTrue(all(b["status"] == "all_lane_witness_withheld" for b in result["bundle_inventory"]))
        function = next(r for r in result["functions"] if r["family"] == "V7" and r["target_quality"] == "M"
                        and r["source_segment_ref"] == result["profiles"][0]["segment_ref"])
        self.assertEqual(function["motion"]["status"], "withheld")
        self.assertEqual(function["motion"]["qualifying_bundle_refs"], [])
        self.assertTrue(all(any(e["qualified"] for e in edges)
                            for edges in function["motion"]["edge_options"].values()))
        self.assertTrue(all(j["all_critical_roles_in_same_bundle"] is False
                            for j in function["motion"]["joint_options"]))
        assessed = indexed.assess(*fx, hyp, idx, result["bundle_inventory"][0], *logical)
        self.assertEqual(assessed["bundle_status"], "all_lane_witness_withheld")
        self.assertFalse(assessed["same_complete_bundle_for_all_function_assumptions"])
        self.assertEqual(assessed["joint_motion_shape_refs"], [])
        self.assertTrue(all("existing_complete_all_lane_bundle_withheld" in r["blockers"]
                            for r in assessed["rows"]))
        self.assert_oracle(fx[1], hyp, logical, result)

    def test_incomplete_projection_source_hold_preserves_all_unknown_denominators(self):
        # The scope fixture exposes explicit envelope width options; the usual
        # hypothesis fixture intentionally retains its default width.
        from test_factor_expanded_scope import FactorExpandedScopeTests
        parents = FactorExpandedScopeTests.fixture(self,
            [[event("C4", 0, 1, tie_role="start"), event("C4", 11, 1, tie_role="stop"),
              event("D4", 5, 1), event(None, 6, 4)]], extent=span(5, 6),
            clocks=[(0, 4), (4, 4), (8, 4)], pre_measures=0, post_measures=0)
        scope = expanded.prepare_scope(*parents)
        self.assertFalse(scope["context_sound_inventory_complete"])
        hyp = frozen.build_hypotheses(parents[0], scope, path_budget=1)
        idx = indexed.build_index(parents[0], scope, hyp)
        self.assertEqual(idx["variant_inventory"], [])
        self.assertTrue(all(g["logical_path_count"] is None and g["logical_tuple_count"] is None
                            and g["status"] == "source_supplier_hold" for g in idx["path_groups"]))
        self.assertEqual(idx["summary"]["unknown_product_groups"], len(hyp["path_groups"]))
        self.assertEqual(len(idx["catalog_inventory"]), len(hyp["catalog_inventory"]))
        self.assertTrue(indexed.validate_index(parents[0], scope, hyp, idx))

    def test_competitor_queries_assess_same_existing_joint_bundle_not_independent_favorable_bundles(self):
        case = self.dominant()
        fx, hyp, idx = case
        session = self.prepare(case)
        logical = self.dominant_tuple(case)
        result = indexed.query_prepared(session, *logical)
        function = next(r for r in result["functions"] if r["family"] == "V7" and r["target_quality"] == "M"
                        and r["source_segment_ref"] == result["profiles"][0]["segment_ref"])
        joint_ref = function["motion"]["qualifying_bundle_refs"][0]
        bundle = next(b for b in result["bundle_inventory"] if common.ref(b) == joint_ref)
        supported = indexed.assess_prepared(session, bundle, *logical)
        self.assertTrue(supported["record_id"].startswith("fmiassess_"))
        self.assertEqual(supported["bundle_ref"], joint_ref)
        self.assertIn(function["function_id"], supported["joint_motion_shape_refs"])
        row = next(r for r in supported["rows"] if r["function_id"] == function["function_id"])
        self.assertTrue(row["all_critical_roles_in_same_complete_bundle"])
        self.assertEqual(set(row["matched_actual_links_by_role"]), {"leading_tone", "seventh"})
        baseline = next(b for b in result["bundle_inventory"] if b["all_no_link_control"])
        control = indexed.assess_prepared(session, baseline, *logical)
        self.assertNotIn(function["function_id"], control["joint_motion_shape_refs"])
        control_row = next(r for r in control["rows"] if r["function_id"] == function["function_id"])
        self.assertFalse(control_row["all_critical_roles_in_same_complete_bundle"])
        self.assertTrue(all(not pairs for pairs in control_row["matched_actual_links_by_role"].values()))
        group = next(g for g in idx["path_groups"] if g["group_id"] == logical[0])
        variants = self.variants(hyp)
        unspelled_target = next(ref for ref in group["slots"][1]["variant_ids"] if variants[ref]["root"] is None)
        competitor = (logical[0], [logical[1][0], unspelled_target], logical[2])
        refused = indexed.assess_prepared(session, bundle, *competitor)
        self.assertEqual(refused["bundle_ref"], supported["bundle_ref"])
        self.assertEqual(refused["symbolic_universe_ref"], supported["symbolic_universe_ref"])
        self.assertEqual(refused["joint_motion_shape_refs"], [])
        self.assertTrue(all(not r["all_critical_roles_in_same_complete_bundle"] for r in refused["rows"]))
        for assessment in (supported, refused):
            self.assertEqual(assessment["computed_counts"]["compatibility_tuples"], 1)
            self.assertEqual(assessment["unqueried_logical_tuple_count"], idx["universe"]["logical_tuples"] - 1)
            self.assertEqual(assessment["unknown_product_groups"], 0)
            self.assertEqual(assessment["unqueried_tuple_compatibility"], "unassessed_not_false_not_materialized")
            self.assertTrue(all(value is False for value in assessment["flags"].values()))
        self.assertTrue(indexed.validate_assessment(*fx, hyp, idx, bundle, *logical, supported))

    def test_all_103_tuples_share_complete_no_link_control_with_exact_guarded_incidence(self):
        case = self.make([[event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]])
        _, hyp, idx = case
        session = self.prepare(case)
        first = indexed.query_prepared(session, *self.first_tuple(hyp, idx))
        bundle = first["bundle_inventory"][0]
        self.assertEqual(bundle["status"], "complete_all_lane_witness")
        self.assertEqual(bundle["materialized_witness_links"], [])
        self.assertEqual(bundle["symbolic_universe"], idx["universe"])
        count = 0
        for group in idx["path_groups"]:
            for ids in product(*(slot["variant_ids"] for slot in group["slots"])):
                for key in hyp["keys"]:
                    logical = (group["group_id"], list(ids), key["record_id"])
                    queried = indexed.query_prepared(session, *logical)
                    assessed = indexed.assess_prepared(session, bundle, *logical)
                    self.assertEqual(assessed["bundle_ref"], common.ref(bundle))
                    self.assertEqual(assessed["query_ref"], common.ref(queried))
                    self.assertEqual(assessed["logical_universe"], idx["universe"])
                    self.assertEqual(assessed["joint_motion_shape_refs"], [])
                    for row, function in zip(assessed["rows"], queried["functions"]):
                        self.assertEqual(row["function_id"], function["function_id"])
                        self.assertTrue(all(not links for links in row["matched_actual_links_by_role"].values()))
                        self.assertFalse(row["all_critical_roles_in_same_complete_bundle"])
                    count += 1
        self.assertEqual(count, 103)

    def test_existing_bundle_foreign_tampered_cross_lane_or_numeric_alias_rejected(self):
        case = self.dominant()
        fx, hyp, idx = case
        session = self.prepare(case)
        logical = self.dominant_tuple(case)
        query = indexed.query_prepared(session, *logical)
        original = query["bundle_inventory"][0]
        for kind in ("unknown", "universe", "lane", "status", "guard_type"):
            forged = deepcopy(original)
            if kind == "unknown": forged["extra_proof"] = True
            elif kind == "universe": forged["symbolic_universe"]["logical_tuples"] = 1
            elif kind == "lane": forged["entries"].pop()
            elif kind == "status": forged["status"] = "confirmed"
            else: forged["all_no_link_control"] = 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                indexed.assess_prepared(session, reseal(forged, "fmibundle_"), *logical)
        other = self.dominant()
        foreign = self.query(other, self.dominant_tuple(other))["bundle_inventory"][0]
        with self.assertRaises(ValueError): indexed.assess_prepared(session, foreign, *logical)
        with self.assertRaises(ValueError): indexed.assess_prepared(session, frozen._bundle(fx[1], [], hyp["keys"]), *logical)

    def test_existing_bundle_assessment_aliases_tamper_and_motion_cap_cannot_promote(self):
        case = self.dominant()
        fx, hyp, idx = case
        session = self.prepare(case)
        logical = self.dominant_tuple(case)
        query = indexed.query_prepared(session, *logical)
        bundle = next(b for b in query["bundle_inventory"] if b["required_links"])
        before = deepcopy(bundle)
        result = indexed.assess_prepared(session, bundle, *logical)
        self.assertEqual(bundle, before)
        original = deepcopy(result)
        result["rows"][0]["blockers"].append("caller_mutation")
        self.assertEqual(indexed.assess_prepared(session, bundle, *logical), original)
        held = indexed.assess_prepared(session, bundle, *logical, max_motion_pairs=0)
        row = next(r for r in held["rows"] if r["family"] == "V7" and r["target_quality"] == "M"
                   and r["source_segment_ref"] == query["profiles"][0]["segment_ref"])
        self.assertEqual(row["status"], "whole_group_budget_abstention")
        self.assertFalse(row["all_critical_roles_in_same_complete_bundle"])
        self.assertEqual(held["joint_motion_shape_refs"], [])
        for kind in ("confidence", "row", "denominator", "type"):
            forged = deepcopy(original)
            if kind == "confidence": forged["confidence"] = 0.99
            elif kind == "row": forged["rows"].pop()
            elif kind == "denominator": forged["unqueried_logical_tuple_count"] = 0
            else: forged["computed_counts"]["compatibility_tuples"] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                indexed.validate_assessment(*fx, hyp, idx, bundle, *logical, reseal(forged, "fmiassess_"))


if __name__ == "__main__":
    unittest.main()
