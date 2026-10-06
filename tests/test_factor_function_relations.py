"""Lossless conditional function relations, without motion or accuracy claims."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import product
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_expanded_scope as expanded
from musicanote_harness import factor_function_relations as relations
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_candidate_catalog as catalog
from test_factor_indexed_hypotheses import IndexedHypothesisFixture
from test_factor_expanded_hypotheses import event, span
from test_factor_musical_view import reseal


class FunctionRelationsFixture(IndexedHypothesisFixture):
    def related(self, case=None, **options):
        case = case or self.make()
        fx, hyp, idx = case
        return case, relations.build_relations(*fx, hyp, idx, **options)

    def session(self, case, record):
        fx, hyp, idx = case
        return relations.prepare_relations(*fx, hyp, idx, record)

    def function(self, case, record, logical=None, *, slot=0, family="V7", quality="M"):
        fx, hyp, idx = case
        logical = logical or self.first_tuple(hyp, idx)
        return relations.query_function(*fx, hyp, idx, record, *logical, slot, family, quality)

    def oracle(self, case, logical, slot, family, quality):
        fx, hyp, _ = case
        variants = self.variants(hyp)
        segments = [variants[ref] for ref in logical[1]]
        key = next(k for k in hyp["keys"] if k["record_id"] == logical[2])
        target = segments[slot + 1] if slot + 1 < len(segments) else None
        return frozen._function(fx[1], segments[slot], target, key["segments"][0], family, quality)

    def assert_function(self, case, logical, slot, family, quality, result):
        self.assertEqual(result["function"], self.oracle(case, logical, slot, family, quality))
        self.assertTrue(result["record_id"].startswith("fmfquery_"))
        self.assertEqual(result["function"]["family"], family)
        self.assertEqual(result["function"]["target_quality"], quality)
        self.assertIsNone(result["function"]["function_confirmed"])
        self.assertIsNone(result["function"]["tonicization"])
        self.assertIsNone(result["function"]["modulation"])
        self.assertIsNone(result["function"]["cadence"])
        self.assertNotIn("motion", result["function"])
        self.assertTrue(all(value is False for value in result["flags"].values()))

    @staticmethod
    def state(function):
        return "".join("U" if function[name] is None else "T" if function[name] else "F"
                       for name in ("shape_compatible", "target_shape_compatible"))

    def assert_weighted_counts(self, record, tallies):
        states, kinds, statuses = Counter(), Counter(), Counter()
        for group in record["path_groups"]:
            for slot in group["function_slots"]:
                tally = tallies[group["group_id"], slot["slot_index"]]
                self.assertEqual(slot["shape_state_counts"],
                                 {state: tally["states"][state] for state in relations.SHAPE_STATES})
                self.assertEqual(slot["status_counts"],
                                 {status: tally["statuses"][status] for status in ("conditional_function_shape", "withheld")})
                self.assertEqual(slot["function_kind_counts"],
                                 {kind: tally["kinds"][kind] for kind in relations.FUNCTION_KINDS})
                self.assertEqual(slot["key_function_kind_counts"],
                                 {key["record_id"]: {kind: tally["keys"][key["record_id"]][kind]
                                                     for kind in relations.FUNCTION_KINDS}
                                  for key in record["keys"]})
                denominator = sum(tally["states"].values())
                self.assertEqual(slot["logical_function_rows"], denominator)
                self.assertEqual(slot["terminal_target_rows"], denominator if slot["terminal_target"] else 0)
                states.update(tally["states"])
                kinds.update(tally["kinds"])
                statuses.update(tally["statuses"])
        self.assertEqual(record["summary"]["shape_state_counts"],
                         {state: states[state] for state in relations.SHAPE_STATES})
        self.assertEqual(record["summary"]["function_kind_counts"],
                         {kind: kinds[kind] for kind in relations.FUNCTION_KINDS})
        self.assertEqual(record["summary"]["conditional_function_shape_rows"], statuses["conditional_function_shape"])
        self.assertEqual(record["summary"]["withheld_function_shape_rows"], statuses["withheld"])
        self.assertEqual(record["summary"]["factored_function_rows"], sum(states.values()))


class FunctionRelationsTests(FunctionRelationsFixture, unittest.TestCase):
    def test_typed_reproducible_fresh_parent_record_and_no_input_aliases(self):
        case, record = self.related()
        fx, hyp, idx = case
        before = deepcopy((case, record))
        self.assertTrue(record["record_id"].startswith("fmfrel_"))
        self.assertEqual(relations.build_relations(*fx, hyp, idx), record)
        self.assertTrue(relations.validate_relations(*fx, hyp, idx, record))
        self.assertEqual((case, record), before)
        hyp["catalog_inventory"][0]["variants"][0]["blockers"].append("caller_mutation")
        idx["variant_inventory"][0]["variant"]["blockers"].append("other_mutation")
        self.assertEqual(record, before[1])

    def test_every_103_real_small_tuple_matches_all_1670_frozen_function_bodies(self):
        case, record = self.related(self.make([
            [event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]]))
        _, hyp, idx = case
        session = self.session(case, record)
        tuple_count = function_count = 0
        tallies = {(group["group_id"], position): {
            "states": Counter(), "statuses": Counter(), "kinds": Counter(),
            "keys": {key["record_id"]: Counter() for key in hyp["keys"]}}
            for group in idx["path_groups"] for position in range(len(group["slots"]))}
        for group in idx["path_groups"]:
            group_count = 0
            for ids in product(*(slot["variant_ids"] for slot in group["slots"])):
                for key in hyp["keys"]:
                    logical = (group["group_id"], list(ids), key["record_id"])
                    for slot in range(len(ids)):
                        for family in frozen.FAMILIES:
                            for quality in ("M", "m"):
                                result = relations.query_function_prepared(
                                    session, *logical, slot, family, quality)
                                self.assert_function(case, logical, slot, family, quality, result)
                                function = result["function"]
                                tally = tallies[group["group_id"], slot]
                                tally["states"][self.state(function)] += 1
                                tally["statuses"][function["status"]] += 1
                                tally["kinds"][function["function_kind"]] += 1
                                tally["keys"][key["record_id"]][function["function_kind"]] += 1
                                function_count += 1
                    tuple_count += 1
                    group_count += 1
            self.assertEqual(group_count, group["logical_tuple_count"])
        self.assertEqual(tuple_count, 103)
        self.assertEqual(function_count, 1670)
        self.assert_weighted_counts(record, tallies)

    def test_all_125_full_hold_key_tuples_match_1250_terminal_functions(self):
        case, record = self.related(self.make(signatures=[{"fifths": 0, "mode_hint": None}]))
        _, hyp, idx = case
        session = self.session(case, record)
        count = functions = 0
        tallies = {(group["group_id"], 0): {
            "states": Counter(), "statuses": Counter(), "kinds": Counter(),
            "keys": {key["record_id"]: Counter() for key in hyp["keys"]}}
            for group in idx["path_groups"]}
        for group in idx["path_groups"]:
            self.assertEqual(group["kind"], "full_hold")
            for variant_id in group["slots"][0]["variant_ids"]:
                for key in hyp["keys"]:
                    logical = (group["group_id"], [variant_id], key["record_id"])
                    for family in frozen.FAMILIES:
                        for quality in ("M", "m"):
                            result = relations.query_function_prepared(session, *logical, 0, family, quality)
                            self.assert_function(case, logical, 0, family, quality, result)
                            self.assertIsNone(result["function"]["target_segment_ref"])
                            self.assertIn("following_target_segment_not_observed", result["function"]["blockers"])
                            function = result["function"]
                            tally = tallies[group["group_id"], 0]
                            tally["states"][self.state(function)] += 1
                            tally["statuses"][function["status"]] += 1
                            tally["kinds"][function["function_kind"]] += 1
                            tally["keys"][key["record_id"]][function["function_kind"]] += 1
                            functions += 1
                    count += 1
        self.assertEqual(count, 125)
        self.assertEqual(functions, 1250)
        self.assert_weighted_counts(record, tallies)

    def test_positive_dominant_shape_is_conditional_not_motion_or_resolution(self):
        case, record = self.related(self.dominant())
        logical = self.dominant_tuple(case)
        result = self.function(case, record, logical)
        self.assert_function(case, logical, 0, "V7", "M", result)
        function = result["function"]
        self.assertTrue(function["shape_compatible"])
        self.assertTrue(function["target_shape_compatible"])
        self.assertEqual(function["status"], "conditional_function_shape")
        self.assertEqual(function["function_kind"], "unassessed")
        self.assertIn("explicit_key_unknown", function["key_projection"]["unassessed_reasons"])
        for field in ("profiles", "motion", "bundle_inventory", "same_bundle_assessments"):
            self.assertNotIn(field, result)

    def test_explicit_major_parallel_and_minor_scale_forms_match_frozen_projection(self):
        case, record = self.related(self.dominant(signatures=[{"fifths": 0, "mode_hint": None}]))
        _, hyp, _ = case
        logical = self.dominant_tuple(case)
        session = self.session(case, record)
        kinds = set()
        forms = set()
        for key in hyp["keys"]:
            current = (logical[0], logical[1], key["record_id"])
            forms.add(key["segments"][0]["scale_form"])
            for quality in ("M", "m"):
                result = relations.query_function_prepared(session, *current, 0, "V7", quality)
                self.assert_function(case, current, 0, "V7", quality, result)
                kinds.add(result["function"]["function_kind"])
        self.assertTrue({"primary", "parallel", "applied", "unassessed"} <= kinds)
        self.assertTrue({"major", "natural_minor", "harmonic_minor", "melodic_minor_ascending"} <= forms)

    def test_terminal_target_none_preserves_actual_source_span_and_reference(self):
        case, record = self.related(self.dominant())
        logical = self.dominant_tuple(case)
        result = self.function(case, record, logical, slot=1)
        self.assert_function(case, logical, 1, "V7", "M", result)
        source = self.variants(case[1])[logical[1][1]]
        self.assertEqual(result["function"]["source_segment_ref"], source["segment_id"])
        self.assertEqual(result["function"]["source_span"], span(2, 4))
        self.assertIsNone(result["function"]["target_span"])
        self.assertIsNone(result["function"]["actual_target_root"])
        self.assertIsNone(result["function"]["actual_target_members"])

    def test_unspelled_and_augmented_coordinate_do_not_invent_source_root(self):
        for lanes, predicate in (
                ([[event(["E3", "G3"], 0, 4)]], lambda v: v["members"] is None),
                ([[event(["A-3", "C4", "F#4"], 0, 4)]],
                 lambda v: v["provider"] == "augmented" and v["tonal_coordinate"] == ["C", 0])):
            case, record = self.related(self.make(lanes))
            _, hyp, idx = case
            variant = next(v for v in self.variants(hyp).values() if predicate(v))
            logical = (idx["path_groups"][0]["group_id"], [variant["record_id"]], hyp["keys"][0]["record_id"])
            result = self.function(case, record, logical)
            self.assert_function(case, logical, 0, "V7", "M", result)
            self.assertIsNone(result["function"]["derived_target_root"])
            self.assertEqual(result["function"]["expected_source_members"], [])
            self.assertIn("source_root_not_spelled", result["function"]["blockers"])

    def test_known_empty_catalogue_has_zero_products_and_no_neutral_tuple(self):
        case, record = self.related(self.make([[event("C3", 0, 4)]]))
        _, hyp, idx = case
        self.assertEqual(idx["summary"]["logical_paths"], 0)
        self.assertEqual(record["origin_inventory"], [])
        session = self.session(case, record)
        group = idx["path_groups"][0]
        with self.assertRaises(ValueError):
            relations.query_function_prepared(session, group["group_id"], [], hyp["keys"][0]["record_id"], 0, "V", "M")

    def test_whole_catalogue_hold_has_unknown_products_not_fake_zero(self):
        case, record = self.related(self.make([
            [event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]],
            build_options={"max_catalogs": 2, "path_budget": 1}))
        _, _, idx = case
        self.assertEqual(record["origin_inventory"], [])
        self.assertTrue(all(group["logical_path_count"] is None for group in idx["path_groups"]))
        self.assertTrue(all(group["logical_tuple_count"] is None for group in idx["path_groups"]))
        self.assertTrue(relations.validate_relations(*case[0], case[1], idx, record))

    def test_source_projection_hold_remains_unknown_and_unassessed(self):
        from test_factor_expanded_scope import FactorExpandedScopeTests
        parents = FactorExpandedScopeTests.fixture(self,
            [[event("C4", 0, 1, tie_role="start"), event("C4", 11, 1, tie_role="stop"),
              event("D4", 5, 1), event(None, 6, 4)]], extent=span(5, 6),
            clocks=[(0, 4), (4, 4), (8, 4)], pre_measures=0, post_measures=0)
        scope = expanded.prepare_scope(*parents)
        hyp = frozen.build_hypotheses(parents[0], scope, path_budget=1)
        idx = indexed.build_index(parents[0], scope, hyp)
        record = relations.build_relations(parents[0], scope, hyp, idx)
        self.assertFalse(scope["context_sound_inventory_complete"])
        self.assertEqual(record["origin_inventory"], [])
        self.assertTrue(all(group["logical_path_count"] is None for group in idx["path_groups"]))
        self.assertTrue(relations.validate_relations(parents[0], scope, hyp, idx, record))

    def test_no_profile_motion_index_query_or_supplier_reproposal_stage(self):
        case = self.dominant()
        with patch.object(frozen, "_profile", side_effect=AssertionError("profiles unassessed")), \
                patch.object(frozen, "_motion_options", side_effect=AssertionError("motion unassessed")), \
                patch.object(indexed, "query_prepared", side_effect=AssertionError("no tuple comparison")), \
                patch.object(catalog, "propose", side_effect=AssertionError("no supplier reconstruction")):
            case, record = self.related(case)
            session = self.session(case, record)
            logical = self.dominant_tuple(case)
            result = relations.query_function_prepared(session, *logical, 0, "V7", "M")
        self.assert_function(case, logical, 0, "V7", "M", result)

    def test_public_and_prepared_query_have_exact_replay_and_function_body(self):
        case, record = self.related(self.dominant())
        fx, hyp, idx = case
        logical = self.dominant_tuple(case)
        result = self.function(case, record, logical)
        self.assertEqual(relations.query_function_prepared(self.session(case, record), *logical, 0, "V7", "M"), result)
        self.assertTrue(relations.validate_function(*fx, hyp, idx, record, *logical, 0, "V7", "M", result))

    def test_group_slot_key_and_function_membership_are_exact(self):
        case, record = self.related(self.dominant())
        logical = self.dominant_tuple(case)
        session = self.session(case, record)
        wrong = [
            ("foreign", logical[1], logical[2], 0, "V7", "M"),
            (logical[0], list(reversed(logical[1])), logical[2], 0, "V7", "M"),
            (logical[0], logical[1][:-1], logical[2], 0, "V7", "M"),
            (logical[0], logical[1] + logical[1][:1], logical[2], 0, "V7", "M"),
            (*logical, -1, "V7", "M"), (*logical, 2, "V7", "M"),
            (*logical, True, "V7", "M"), (*logical, 0.0, "V7", "M"),
            (logical[0], logical[1], "foreign", 0, "V7", "M"),
            (*logical, 0, "I", "M"), (*logical, 0, "V7", "major")]
        for request in wrong:
            with self.subTest(request=request), self.assertRaises(ValueError):
                relations.query_function_prepared(session, *request)

    def test_resealed_query_function_body_provenance_and_flags_rejected(self):
        case, record = self.related()
        fx, hyp, idx = case
        logical = self.first_tuple(hyp, idx)
        original = self.function(case, record, logical)
        for kind in ("body", "source", "key", "promotion", "extra"):
            forged = deepcopy(original)
            if kind == "body": forged["function"]["status"] = "confirmed"
            elif kind == "source": forged["function"]["source_segment_ref"] = "foreign"
            elif kind == "key": forged["function"]["key_segment_ref"] = "foreign"
            elif kind == "promotion": forged["flags"]["harmony_confirmed"] = True
            else: forged["confidence"] = 0.99
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                relations.validate_function(*fx, hyp, idx, record, *logical, 0, "V7", "M", reseal(forged, "fmfquery_"))

    def test_foreign_source_scope_hypothesis_and_index_are_not_authority(self):
        case, record = self.related()
        fx, hyp, idx = case
        other = self.make()
        variants = [(*other[0], hyp, idx), (*fx, other[1], idx), (*fx, hyp, other[2])]
        changed_ir = deepcopy(fx[0])
        changed_ir["note_events"][0]["notation"]["new_literal_content"] = "changed"
        variants.append((changed_ir, fx[1], hyp, idx))
        for args in variants:
            with self.subTest(parent=args[0]["source_id"] if "source_id" in args[0] else "parent"), self.assertRaises(ValueError):
                relations.validate_relations(*args, record)

    def test_resealed_parent_index_count_alias_or_origin_tamper_rejected(self):
        case, _ = self.related()
        fx, hyp, original = case
        for kind in ("numeric", "origin", "slots", "extra"):
            forged = deepcopy(original)
            if kind == "numeric": forged["summary"]["profiles_materialized"] = False
            elif kind == "origin": forged["variant_inventory"][0]["variant"]["supplier_origin_pointer"] = "/foreign"
            elif kind == "slots": forged["path_groups"][0]["slots"][0]["variant_ids"].pop()
            else: forged["confidence"] = 0.99
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                relations.build_relations(*fx, hyp, reseal(forged, "fmiidx_"))

    def test_owned_session_and_returned_function_are_detached_from_all_inputs(self):
        case, record = self.related(self.dominant())
        fx, hyp, idx = case
        logical = self.dominant_tuple(case)
        session = self.session(case, record)
        original = relations.query_function_prepared(session, *logical, 0, "V7", "M")
        expected = deepcopy(original)
        original["function"]["blockers"].append("returned_mutation")
        original["function"]["actual_target_members"][0]["step"] = "A"
        fx[1]["sound_facts"][0]["pitch"]["step"] = "A"
        hyp["catalog_inventory"][0]["variants"][0]["blockers"].append("caller_mutation")
        idx["path_groups"][0]["slots"][0]["variant_ids"].clear()
        record["origin_inventory"].clear()
        self.assertEqual(relations.query_function_prepared(session, *logical, 0, "V7", "M"), expected)

    def test_unissued_session_is_not_authority(self):
        case, record = self.related()
        logical = self.first_tuple(case[1], case[2])
        with self.assertRaises(ValueError):
            relations.query_function_prepared(object(), *logical, 0, "V", "M")

    def test_current_code_hashes_guard_records_and_prepared_queries(self):
        case, record = self.related()
        fx, hyp, idx = case
        logical = self.first_tuple(hyp, idx)
        session = self.session(case, record)
        original = Path.read_bytes
        for module in (relations, indexed, frozen, expanded, catalog):
            target = Path(module.__file__)
            def changed(path):
                raw = original(path)
                return raw + b"\n" if path == target else raw
            with self.subTest(module=module.__name__), patch.object(Path, "read_bytes", changed):
                with self.assertRaises(ValueError): relations.validate_relations(*fx, hyp, idx, record)
                with self.assertRaises(ValueError): relations.query_function_prepared(session, *logical, 0, "V7", "M")

    def test_invalid_kernel_caps_rejected_before_input_reads(self):
        for value in (-1, True, 1.5, None, "1"):
            with self.subTest(value=value), patch.object(expanded, "check_scope", side_effect=AssertionError("no source read")):
                with self.assertRaises(ValueError):
                    relations.build_relations(None, None, None, None, max_kernels=value)

    def test_every_origin_and_exact_ordered_semantic_type_is_preserved(self):
        case, record = self.related(self.make([[event(
            ["C3", "E3", "B3", "B-3", "D4", "A-3", "F#4"], 0, 4)]]))
        _, hyp, idx = case
        variants = self.variants(hyp)
        self.assertEqual([row["variant_id"] for row in record["origin_inventory"]], list(variants))
        types = {row["record_id"]: row for row in record["type_inventory"]}
        first_types = []
        for old, row in zip(idx["variant_inventory"], record["origin_inventory"]):
            variant = variants[row["variant_id"]]
            self.assertEqual(row["variant_ref"], common.ref(variant))
            self.assertEqual(row["segment_ref"], variant["segment_id"])
            self.assertEqual(row["span"], variant["span"])
            self.assertEqual(row["profile_ref"], old["profile_ref"])
            for name in ("provider", "supplier_candidate_ref", "supplier_record_pointer",
                         "supplier_origin_pointer", "spelling_alternative_index", "provenance"):
                self.assertEqual(row[name], variant[name])
            type_id = row["type_ref"]["record_id"]
            self.assertEqual(types[type_id]["semantic"],
                             {name: variant[name] for name in ("root", "members", "blockers")})
            if type_id not in first_types: first_types.append(type_id)
        self.assertEqual(list(types), first_types)
        self.assertEqual({row["provider"] for row in record["origin_inventory"]},
                         {"base", "additional_seventh", "augmented", "extended"})
        self.assertGreater(len(record["origin_inventory"]), len(record["type_inventory"]))

    def test_catalogue_type_weights_sum_all_duplicate_origins_in_first_occurrence_order(self):
        case, record = self.related(self.make([
            [event(["C3", "E4", "G4"], 0, 2), event(["C3", "E4", "G4"], 2, 2)]]))
        _, _, idx = case
        origins = {row["variant_id"]: row for row in record["origin_inventory"]}
        for before, catalog_row in zip(idx["catalog_inventory"], record["catalog_inventory"]):
            counts = Counter(origins[ref]["type_ref"]["record_id"] for ref in before["variant_ids"])
            self.assertEqual(catalog_row["type_weights"],
                             [{"type_id": ref, "origin_count": count} for ref, count in counts.items()])
            self.assertEqual(sum(row["origin_count"] for row in catalog_row["type_weights"]), before["variant_count"])
        kernels = record["kernels"]
        self.assertEqual(len(kernels), len(record["type_inventory"]) * 10)
        self.assertEqual(len({(k["source_type_ref"]["record_id"], k["family"], k["quality"])
                              for k in kernels}), len(kernels))

    def test_terminal_right_slot_retains_every_left_origin_multiplicity(self):
        case, record = self.related(self.make([
            [event(["C3", "G4"], 0, 2), event(["D3", "A4"], 2, 2)]]))
        _, hyp, idx = case
        counts = []
        for old, group in zip(idx["path_groups"], record["path_groups"]):
            self.assertEqual(group["group_id"], old["group_id"])
            self.assertEqual(group["slots"], old["slots"])
            self.assertEqual(group["partition"], old["partition"])
            self.assertEqual(group["logical_path_count"], old["logical_path_count"])
            terminal = group["function_slots"][-1]
            opposite = 1 if len(old["slots"]) == 1 else len(old["slots"][0]["variant_ids"])
            expected = len(old["slots"][-1]["variant_ids"]) * opposite * len(hyp["keys"]) * 10
            self.assertEqual(terminal["opposite_slot_multiplicity"], opposite)
            self.assertEqual(terminal["terminal_target_rows"], expected)
            self.assertEqual(terminal["status_counts"], {"conditional_function_shape": 0, "withheld": expected})
            self.assertEqual(sum(terminal["shape_state_counts"].values()), expected)
            self.assertTrue(all(terminal["shape_state_counts"][state] == 0
                                for state in relations.SHAPE_STATES if not state.endswith("U")))
            counts.append(expected)
        self.assertEqual(counts, [390, 640])
        self.assertEqual(record["summary"]["terminal_target_rows"], 1030)

    def test_all_nine_zero_explicit_states_and_weighted_denominators_are_honest(self):
        case, record = self.related(self.dominant(signatures=[{"fifths": 0, "mode_hint": None}]))
        _, _, idx = case
        summary = record["summary"]
        self.assertEqual(summary["logical_paths"], idx["universe"]["logical_paths"])
        self.assertEqual(summary["logical_path_key_tuples"], idx["universe"]["logical_tuples"])
        self.assertEqual(summary["logical_function_rows"], sum(g["logical_function_count"] for g in idx["path_groups"]))
        self.assertEqual(summary["factored_function_rows"], summary["logical_function_rows"])
        self.assertEqual(summary["unassessed_function_rows"], 0)
        self.assertEqual(set(summary["shape_state_counts"]), {a + b for a in "TFU" for b in "TFU"})
        self.assertGreater(summary["shape_state_counts"]["TT"], 0)
        self.assertGreater(summary["shape_state_counts"]["FF"], 0)
        self.assertGreater(summary["shape_state_counts"]["UU"], 0)
        for group in record["path_groups"]:
            for slot in group["function_slots"]:
                self.assertEqual(sum(slot["shape_state_counts"].values()), group["logical_tuple_count"] * 10)
                self.assertEqual(sum(slot["status_counts"].values()), group["logical_tuple_count"] * 10)
                self.assertEqual(sum(slot["function_kind_counts"].values()), group["logical_tuple_count"] * 10)
        for name in ("queried_function_rows", "literal_profiles_computed", "actual_endpoint_pairs_computed",
                     "motion_groups_computed", "same_bundle_assessments_computed"):
            self.assertEqual(summary[name], 0)
        self.assertIsNone(record["selected"])
        self.assertIsNone(record["rank"])
        self.assertIsNone(record["confidence"])
        self.assertTrue(all(value is False for value in record["flags"].values()))

    def test_kernel_cap_exact_admission_one_less_and_zero_are_whole_inventory_holds(self):
        case, original = self.related()
        fx, hyp, idx = case
        planned = original["summary"]["planned_source_kernels"]
        self.assertGreater(planned, 0)
        exact = relations.build_relations(*fx, hyp, idx, max_kernels=planned)
        self.assertEqual(len(exact["kernels"]), planned)
        for cap in (0, planned - 1):
            with self.subTest(cap=cap):
                record = relations.build_relations(*fx, hyp, idx, max_kernels=cap)
                self.assertEqual(record["origin_inventory"], original["origin_inventory"])
                self.assertEqual(record["type_inventory"], original["type_inventory"])
                self.assertEqual(record["catalog_inventory"], original["catalog_inventory"])
                self.assertEqual(record["kernels"], [])
                self.assertEqual(record["target_relations"], [])
                self.assertEqual(record["key_projections"], [])
                self.assertEqual(record["summary"]["factored_function_rows"], 0)
                self.assertEqual(record["summary"]["unassessed_function_rows"], original["summary"]["logical_function_rows"])
                for group in record["path_groups"]:
                    for slot in group["function_slots"]:
                        self.assertIsNone(slot["shape_state_counts"])
                        self.assertIsNone(slot["status_counts"])
                        self.assertIsNone(slot["function_kind_counts"])
                result = self.function(case, record)
                self.assertIsNone(result["function"])
                self.assertEqual(result["computed_function_rows"], 0)
                self.assertEqual(result["status"], "withheld_relation_group")
                self.assertTrue(relations.validate_relations(*fx, hyp, idx, record))

    def test_index_inventory_hold_keeps_known_denominators_without_fabricated_types(self):
        case, record = self.related(self.make(index_options={"max_variants": 0}))
        _, _, idx = case
        self.assertEqual(record["origin_inventory"], [])
        self.assertEqual(record["type_inventory"], [])
        self.assertEqual(record["kernels"], [])
        self.assertEqual(record["summary"]["logical_paths"], idx["universe"]["logical_paths"])
        self.assertEqual(record["summary"]["unknown_product_groups"], 0)
        self.assertGreater(record["summary"]["unassessed_function_rows"], 0)
        for group in record["path_groups"]:
            self.assertTrue(all(slot["status_counts"] is None for slot in group["function_slots"]))
        result = self.function(case, record)
        self.assertIsNone(result["function"])
        self.assertEqual(result["computed_function_rows"], 0)

    def test_unknown_source_or_microtonal_source_kernel_does_not_reuse_root_only_template(self):
        case = self.make(signatures=[{"fifths": 0, "mode_hint": None}])
        fx, hyp, _ = case
        original = next(v for v in self.variants(hyp).values() if v["root"] is not None and v["members"] is not None)
        key = hyp["keys"][0]["segments"][0]
        for kind in ("members_unknown", "root_microtone", "member_microtone"):
            source = deepcopy(original)
            if kind == "members_unknown": source["members"] = None
            elif kind == "root_microtone": source["root"]["alter"] = common.q(Fraction(1, 2))
            else: source["members"][0]["alter"] = common.q(Fraction(1, 2))
            with self.subTest(kind=kind):
                type_record = relations._type(source)
                kernel = relations._kernel(fx[1], source, type_record, key, "V7", "M")
                oracle = frozen._function(fx[1], source, None, key, "V7", "M")
                self.assertEqual(kernel["source_template"]["expected_source_members"], oracle["expected_source_members"])
                self.assertEqual(kernel["source_template"]["expected_source_members"], [])
                self.assertIsNone(kernel["source_template"]["derived_target_root"])
                self.assertIsNone(kernel["source_template"]["shape_compatible"])
                self.assertIn("ordinary_source_spelling_unknown_or_microtonal", kernel["source_blockers"])

    def test_extended_target_preserves_exact_order_and_can_match_triad_core_not_inversion(self):
        case, record = self.related(self.make([
            [event(["G3", "B3", "D4", "F4"], 0, 2), event(["C3", "E4", "G4", "B-4", "D5"], 2, 2)]]))
        _, hyp, idx = case
        variants = self.variants(hyp)
        group = next(g for g in idx["path_groups"] if g["kind"] == "two_segment")
        source = next(variants[ref] for ref in group["slots"][0]["variant_ids"]
                      if variants[ref]["root"] == {"step": "G", "alter": common.q(0)}
                      and variants[ref]["members"] is not None
                      and {common.pitch_key(p) for p in variants[ref]["members"]} ==
                      {(letter, Fraction()) for letter in "GBDF"})
        target = next(variants[ref] for ref in group["slots"][1]["variant_ids"]
                      if variants[ref]["provider"] == "extended"
                      and variants[ref]["root"] == {"step": "C", "alter": common.q(0)}
                      and variants[ref]["members"] is not None and len(variants[ref]["members"]) > 4)
        logical = (group["group_id"], [source["record_id"], target["record_id"]], hyp["keys"][0]["record_id"])
        result = self.function(case, record, logical)
        self.assert_function(case, logical, 0, "V7", "M", result)
        self.assertTrue(result["function"]["target_shape_compatible"])
        self.assertEqual(result["function"]["actual_target_members"], target["members"])
        self.assertNotIn("inversion", result["function"])
        self.assertFalse(result["flags"]["actual_motion_evaluated"])

    def test_enharmonic_midi_equivalence_does_not_merge_spelled_target_or_core(self):
        case, record = self.related(self.make([
            [event(["C#3", "E#4", "G#4", "B4"], 0, 2), event(["G-3", "B-4", "D-5"], 2, 2)]]))
        _, hyp, idx = case
        variants = self.variants(hyp)
        group = next(g for g in idx["path_groups"] if g["kind"] == "two_segment")
        wanted = [({"step": "C", "alter": common.q(1)}, {("C", 1), ("E", 1), ("G", 1), ("B", 0)}),
                  ({"step": "G", "alter": common.q(-1)}, {("G", -1), ("B", -1), ("D", -1)})]
        ids = []
        for slot, (root, members) in zip(group["slots"], wanted):
            ids.append(next(ref for ref in slot["variant_ids"] if variants[ref]["root"] == root
                            and variants[ref]["members"] is not None
                            and {common.pitch_key(p) for p in variants[ref]["members"]} == members))
        logical = (group["group_id"], ids, hyp["keys"][0]["record_id"])
        result = self.function(case, record, logical)
        self.assert_function(case, logical, 0, "V7", "M", result)
        function = result["function"]
        self.assertTrue(function["shape_compatible"])
        self.assertFalse(function["target_shape_compatible"])
        pc = lambda p: (frozen.NATURAL[p["step"]] + common.f(p["alter"])) % 12
        self.assertEqual(pc(function["derived_target_root"]), pc(function["actual_target_root"]))
        self.assertEqual({pc(p) for p in function["derived_target_members"]},
                         {pc(p) for p in function["actual_target_members"]})
        self.assertNotEqual(function["derived_target_root"], function["actual_target_root"])
        self.assertIn("following_target_triad_core_mismatch", function["blockers"])

    def test_unresolved_following_target_is_unknown_not_terminal_or_false(self):
        case, record = self.related(self.make([
            [event(["G3", "B3", "D4", "F4"], 0, 2), event(["E4", "G4"], 2, 2)]]))
        _, hyp, idx = case
        variants = self.variants(hyp)
        group = next(g for g in idx["path_groups"] if g["kind"] == "two_segment")
        source_id = next(ref for ref in group["slots"][0]["variant_ids"]
                         if variants[ref]["root"] == {"step": "G", "alter": common.q(0)}
                         and variants[ref]["members"] is not None
                         and {common.pitch_key(p) for p in variants[ref]["members"]} ==
                         {(letter, Fraction()) for letter in "GBDF"})
        target_id = next(ref for ref in group["slots"][1]["variant_ids"]
                         if variants[ref]["members"] is None)
        logical = (group["group_id"], [source_id, target_id], hyp["keys"][0]["record_id"])
        result = self.function(case, record, logical)
        self.assert_function(case, logical, 0, "V7", "M", result)
        self.assertIsNone(result["function"]["target_shape_compatible"])
        self.assertIsNotNone(result["function"]["target_segment_ref"])
        self.assertIn("following_target_spelling_unresolved", result["function"]["blockers"])
        self.assertNotIn("following_target_segment_not_observed", result["function"]["blockers"])
        self.assertEqual(result["function"]["target_span"], span(2, 4))

    def test_exact_rational_half_open_segment_provenance_not_old_anchor(self):
        third = Fraction(1, 3)
        case, record = self.related(self.make([
            [event(["C3", "G4"], 0, third), event(["D3", "A4"], third, Fraction(11, 3))]]))
        _, hyp, idx = case
        group = next(g for g in idx["path_groups"] if g["kind"] == "two_segment")
        logical = (group["group_id"], [slot["variant_ids"][0] for slot in group["slots"]], hyp["keys"][0]["record_id"])
        result = self.function(case, record, logical)
        self.assert_function(case, logical, 0, "V7", "M", result)
        self.assertEqual(result["function"]["source_span"], span(0, third))
        self.assertEqual(result["function"]["target_span"], span(third, 4))
        self.assertEqual(record["analysis_span"], case[0][1]["analysis_span"])
        self.assertNotEqual(record["analysis_span"], case[0][1]["anchor_span"])

    def test_tie_clock_guard_is_retained_but_literal_eligibility_not_assessed_by_shape(self):
        case, record = self.related(self.make([
            [event("C4", 0, 1, tie_role="start"), event("C4", 3, 1, tie_role="stop")],
            [event("E4", 0, 4)], [event("G4", 0, 4)]]))
        sound = next(row for row in case[0][1]["sound_facts"] if len(row["source_note_refs"]) == 2)
        self.assertFalse(sound["source_clock_passed"])
        self.assertFalse(sound["eligible_as_analysis_source"])
        logical = self.first_tuple(case[1], case[2])
        result = self.function(case, record, logical)
        self.assert_function(case, logical, 0, "V7", "M", result)
        self.assertEqual(record["profiles_endpoints_motion_and_bundles"], "unassessed")
        self.assertFalse(result["flags"]["actual_endpoints_evaluated"])

    def test_point_grace_supplier_blocker_survives_source_and_resolved_target_branches(self):
        case, record = self.related(self.make([
            [event(["G3", "B3", "D4", "F4"], 0, 2), event(["C3", "E4", "G4"], 2, 2)],
            [event("A4", 0, 1), event("A4", 1, 0, grace=True), event("A4", 1, 3)]], extent=span(3, 4)))
        _, hyp, idx = case
        self.assertTrue(any(row["point"] for row in case[0][1]["sound_facts"]))
        blocked = next(v for v in self.variants(hyp).values() if v["blockers"])
        group = next(g for g in idx["path_groups"] if blocked["record_id"] in g["slots"][0]["variant_ids"])
        ids = [blocked["record_id"]] + [slot["variant_ids"][0] for slot in group["slots"][1:]]
        logical = (group["group_id"], ids, hyp["keys"][0]["record_id"])
        result = self.function(case, record, logical)
        self.assert_function(case, logical, 0, "V7", "M", result)
        self.assertTrue(set(blocked["blockers"]) <= set(result["function"]["blockers"]))
        self.assertEqual(result["function"]["status"], "withheld")

    def test_resealed_relations_closed_metadata_weight_counts_references_and_limits_rejected(self):
        case, original = self.related()
        fx, hyp, idx = case
        for kind in ("extra", "promotion", "origin", "type", "weight", "kernel", "target", "projection", "group", "summary", "limits"):
            forged = deepcopy(original)
            if kind == "extra": forged["score"] = 1
            elif kind == "promotion": forged["flags"]["harmony_confirmed"] = True
            elif kind == "origin": forged["origin_inventory"].pop()
            elif kind == "type": forged["type_inventory"].reverse()
            elif kind == "weight": forged["catalog_inventory"][0]["type_weights"][0]["origin_count"] += 1
            elif kind == "kernel": forged["kernels"].pop()
            elif kind == "target": forged["target_relations"][0]["true_type_ids"].append("foreign")
            elif kind == "projection": forged["key_projections"][0]["function_kind"] = "confirmed"
            elif kind == "group": forged["path_groups"][0]["function_slots"][0]["opposite_slot_multiplicity"] += 1
            elif kind == "summary": forged["summary"]["logical_function_rows"] += 1
            else: forged["resource_limits"]["max_kernels"] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                relations.validate_relations(*fx, hyp, idx, reseal(forged, "fmfrel_"))

    def test_resealed_numeric_aliases_are_not_canonical_relation_or_query_values(self):
        case, original = self.related()
        fx, hyp, idx = case
        for kind in ("zero_bool", "count_float", "shape_bool"):
            forged = deepcopy(original)
            if kind == "zero_bool": forged["summary"]["queried_function_rows"] = False
            elif kind == "count_float": forged["summary"]["origin_variants"] = float(forged["summary"]["origin_variants"])
            else: forged["path_groups"][0]["function_slots"][0]["shape_state_counts"]["TT"] = False
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                relations.prepare_relations(*fx, hyp, idx, reseal(forged, "fmfrel_"))
        logical = self.first_tuple(hyp, idx)
        result = self.function(case, original, logical)
        result["computed_function_rows"] = True
        with self.assertRaises(ValueError):
            relations.validate_function(*fx, hyp, idx, original, *logical, 0, "V7", "M", reseal(result, "fmfquery_"))

    def test_repeated_prepared_query_uses_existing_type_kernels_and_projections_only(self):
        case, record = self.related(self.dominant())
        logical = self.dominant_tuple(case)
        session = self.session(case, record)
        with patch.object(frozen, "_function", side_effect=AssertionError("do not redo function kernels")), \
                patch.object(frozen, "product", side_effect=AssertionError("no Cartesian paths")), \
                patch.object(indexed, "_body", side_effect=AssertionError("no index rebuild")), \
                patch.object(relations, "_body", side_effect=AssertionError("no relations rebuild")):
            first = relations.query_function_prepared(session, *logical, 0, "V7", "M")
            second = relations.query_function_prepared(session, *logical, 0, "V7", "M")
            competing = relations.query_function_prepared(session, *logical, 0, "vii7", "m")
        self.assertEqual(first, second)
        self.assert_function(case, logical, 0, "V7", "M", first)
        self.assert_function(case, logical, 0, "vii7", "m", competing)

    def test_prepared_state_cannot_be_swapped_or_unissued_forged_handle_used(self):
        case, record = self.related()
        logical = self.first_tuple(case[1], case[2])
        with self.assertRaises(ValueError):
            relations.query_function_prepared(relations._PreparedRelations(), *logical, 0, "V", "M")
        first = self.session(case, record)
        second = self.session(case, record)
        relations._SESSIONS[first] = relations._SESSIONS[second]
        with self.assertRaises(ValueError):
            relations.query_function_prepared(first, *logical, 0, "V", "M")

    def test_caller_mutation_during_owned_validation_is_detected_without_partial_record(self):
        case = self.make()
        fx, hyp, idx = case
        check = indexed._check_index_lineage
        def changed(*args):
            result = check(*args)
            hyp["catalog_inventory"][0]["variants"][0]["blockers"].append("during_validation")
            return result
        with patch.object(indexed, "_check_index_lineage", changed), self.assertRaises(ValueError):
            relations.build_relations(*fx, hyp, idx)

    def test_missing_required_relation_header_is_explicitly_rejected(self):
        case, original = self.related()
        fx, hyp, idx = case
        for name in ("contract", "origin_inventory", "path_groups", "summary", "resource_limits", "flags"):
            forged = deepcopy(original)
            del forged[name]
            with self.subTest(field=name), self.assertRaises(ValueError):
                relations.validate_relations(*fx, hyp, idx, reseal(forged, "fmfrel_"))
        for malformed in (None, [], "not_a_relation"):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                relations.prepare_relations(*fx, hyp, idx, malformed)

    def test_genuine_microtonal_full_ir_pitch_guard_is_retained_not_repaired(self):
        def microtone(ir):
            note = next(row for row in ir["note_events"] if row.get("written_pitch") is not None
                        and row["written_pitch"]["spelling"] == "C4")
            for name in ("written_pitch", "concert_pitch"):
                note[name].update(alter=common.q(Fraction(1, 2)), spelling="C-half-sharp4",
                                  midi_pitch=None, pitch_class=None)
            sound = next(row for row in ir["sounding_events"] if note["note_id"] in row["source_note_ids"])
            sound["pitch"] = deepcopy(note["written_pitch"])
        case, record = self.related(self.make([
            [event("C4", 0, 1), event(None, 1, 3)], [event("E4", 1, 3)], [event("G4", 1, 3)]],
            extent=span(2, 3), modify=microtone))
        scope = case[0][1]
        sound = next(row for row in scope["sound_facts"] if common.f(row["pitch"]["alter"]) == Fraction(1, 2))
        self.assertTrue(sound["source_pitch_consistency_passed"])
        self.assertTrue(sound["source_clock_passed"])
        self.assertFalse(sound["eligible_as_analysis_source"])
        self.assertEqual(sound["pitch"]["spelling"], "C-half-sharp4")
        self.assertEqual(record["scope_ref"], common.ref(scope))
        session = self.session(case, record)
        logical = self.first_tuple(case[1], case[2])
        result = relations.query_function_prepared(session, *logical, 0, "V7", "M")
        self.assert_function(case, logical, 0, "V7", "M", result)
        self.assertFalse(result["flags"]["literal_profiles_evaluated"])
        self.assertFalse(result["flags"]["actual_endpoints_evaluated"])
        self.assertNotIn("source_repair", result)

    def test_invalid_public_selectors_are_rejected_before_input_reads(self):
        for slot, family, quality in ((-1, "V", "M"), (True, "V", "M"), (0.0, "V", "M"),
                                      (None, "V", "M"), (0, "I", "M"), (0, True, "M"),
                                      (0, "V", "major"), (0, "V", None)):
            with self.subTest(slot=slot, family=family, quality=quality), \
                    patch.object(relations, "prepare_relations", side_effect=AssertionError("no input read")), \
                    self.assertRaises(ValueError):
                relations.query_function(None, None, None, None, None, None, None, None, slot, family, quality)


if __name__ == "__main__":
    unittest.main()
