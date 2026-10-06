"""Complete original-path contrasts under one authentic actual completion.

The phase19 fixture is composed, not inherited: its 50 prior tests are not
silently counted as new phase20 coverage.  Real cold parent trials live in
the separately owned runner tests.
"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_progression_evidence as progression
from musicanote_harness import factor_delayed_obligations as delayed
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_musical_view as common
import test_factor_delayed_obligations as delayed_fixtures
from test_factor_musical_view import reseal


class ProgressionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = delayed_fixtures.DelayedTests()
        cls.helper.factory = delayed_fixtures.TemporalExplanationFixture()
        cls.helper.factory.addCleanup = cls.addClassCleanup
        cls.helper.factory.setUp()
        cls.helper.raw_cache, cls.helper.ready_cache = {}, {}
        cls.sessions = {}

    def ready(self, name="held", **caps):
        if name == "key" and name not in self.helper.raw_cache:
            make_event = delayed_fixtures.event
            case = self.helper.factory.frozen_case(self.helper.factory.make([
                [make_event("B4", 0, 3), make_event("C5", 3, 1)],
                [make_event("F4", 0, 3), make_event("E4", 3, 1)],
                [make_event("G3", 0, 2), make_event("C3", 2, 2)],
                [make_event("D4", 0, 2), make_event("G4", 2, 2)]],
                signatures=[{"fifths": 0, "mode_hint": None}]))
            flat = (*case[0], *case[1:])
            grounding = delayed_fixtures.grounded.build_grounding(*flat)
            parents = (*flat, grounding)
            local = delayed_fixtures.temporal.build_explanations(*parents)
            boundary_inputs = (*parents, local)
            supplier = delayed_fixtures.boundary.prepare_inputs(*boundary_inputs)
            border = delayed_fixtures.boundary.build_explanations_prepared(supplier)
            self.helper.raw_cache[name] = (*boundary_inputs, border)
        inputs, supplier, record = self.helper.ready(name, **caps)
        cache_key = (name, common.digest(delayed._contract()), tuple(sorted(caps.items())))
        if cache_key not in self.sessions:
            parent = delayed.prepare_obligations_prepared(supplier, record)
            self.sessions[cache_key] = parent, progression.prepare_comparison_prepared(parent)
        parent, session = self.sessions[cache_key]
        return inputs, supplier, record, parent, session

    def selector(self, inputs, record, *, quality="M", family="V7", key_id=None):
        logical, kernel = self.helper.selected(inputs, record, family=family, quality=quality)
        return {"group_id": logical[0], "variant_ids": list(logical[1]),
            "key_id": key_id or logical[2], "transition": {"family": family,
            "quality": quality, "strategy": "ordinary_role_existential",
            "declared_occurrences": None, "requested_explanations": None}}, kernel

    def fullhold(self, inputs, *, key_id=None):
        group = next(g for g in inputs[3]["path_groups"] if g["kind"] == "full_hold")
        return {"group_id": group["group_id"],
            "variant_ids": [group["slots"][0]["variant_ids"][0]],
            "key_id": key_id or inputs[2]["keys"][0]["record_id"], "transition": None}

    def bundle(self, record, kernel):
        return next(b["bundle_ref"]["record_id"] for b in self.helper.plan(record, kernel)["branches"]
                    if b["status"] == "possible")

    def compare(self, name="held", *, control=False, selectors=None, **options):
        inputs, supplier, record, parent, session = self.ready(name)
        candidate, kernel = self.selector(inputs, record)
        chosen = selectors or [candidate, self.fullhold(inputs)]
        bundle_id = self.helper.control(record) if control else self.bundle(record, kernel)
        return inputs, record, chosen, progression.compare_prepared(session, chosen, bundle_id, **options)

    def assert_raw_account(self, path):
        account = path["whole_path_account"]
        self.assertIsNotNone(account)
        total = sum((common.f(p["total_note_time_quarters"]) for p in path["profiles"]), Fraction())
        self.assertEqual(common.f(account["total_note_time"]), total)
        self.assertEqual(sum((common.f(v) for v in account["note_time"].values()), Fraction()), total)
        self.assertEqual(sum((common.f(v) for v in account["raw_note_time"].values()), Fraction()), total)

    def test_positive_and_fullhold_contrast_retain_complete_original_partitions(self):
        inputs, record, selectors, result = self.compare()
        self.assertEqual(len(result["hypotheses"]), 2)
        self.assertEqual(len(result["contrasts"]), 1)
        self.assertEqual([p["selector"] for p in result["hypotheses"]], selectors)
        self.assertNotEqual(selectors[0]["group_id"], selectors[1]["group_id"])
        original = {g["group_id"]: g for g in inputs[3]["path_groups"]}
        for path in result["hypotheses"]:
            self.assertEqual(path["partition"], original[path["selector"]["group_id"]]["partition"])
            self.assert_raw_account(path)
        self.assertEqual(result["logical_universe"], record["logical_universe"])
        self.assertEqual(result["analysis_span"], inputs[1]["analysis_span"])
        actual = result["hypotheses"][0]["transition_assessment"]
        self.assertIs(actual["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        self.assertEqual(result["hypotheses"][1]["transition_assessment"], None)

    def test_no_link_control_has_no_borrowed_delayed_credit(self):
        _, _, _, result = self.compare(control=True)
        candidate = result["hypotheses"][0]
        self.assertIs(candidate["transition_assessment"]["ordinary_strategy"]["whole_ordinary_template_satisfied"], False)
        self.assertEqual(common.f(candidate["whole_path_account"]["conditional_explanation_note_time"]), 0)
        self.assert_raw_account(candidate)

    def test_one_same_bundle_conditions_every_competitor(self):
        _, _, _, result = self.compare()
        bundle_ref = result["hypotheses"][0]["transition_assessment"]["bundle_ref"]
        self.assertEqual(result["bundle_ref"], bundle_ref)
        for path in result["hypotheses"]:
            if path["transition_assessment"] is not None:
                self.assertEqual(path["transition_assessment"]["bundle_ref"], bundle_ref)
        self.assertFalse(result["flags"].get("independent_completions_unioned", False))

    def test_fullhold_vs_onecut_have_identical_raw_note_time_denominator(self):
        _, _, _, result = self.compare()
        totals = [path["whole_path_account"]["total_note_time"] for path in result["hypotheses"]]
        self.assertEqual(totals[0], totals[1])
        for path in result["hypotheses"]:
            self.assert_raw_account(path)

    def test_all_function_shapes_and_terminal_complement_survive(self):
        inputs, _, _, result = self.compare()
        variants = {v["variant_id"]: v["variant"] for v in inputs[3]["variant_inventory"]}
        keys = {k["record_id"]: k for k in inputs[2]["keys"]}
        for path in result["hypotheses"]:
            ids = path["selector"]["variant_ids"]
            self.assertEqual(len(path["function_shapes"]), len(ids) * len(frozen.FAMILIES) * 2)
            expected = []
            for slot, sid in enumerate(ids):
                target = variants[ids[slot + 1]] if slot + 1 < len(ids) else None
                for family in frozen.FAMILIES:
                    for quality in ("M", "m"):
                        expected.append((slot, family, quality, frozen._function(inputs[1], variants[sid], target,
                            keys[path["selector"]["key_id"]]["segments"][0], family, quality)))
            for row, (slot, family, quality, oracle) in zip(path["function_shapes"], expected):
                self.assertEqual((row["slot"], row["family"], row["quality"]), (slot, family, quality))
                self.assertEqual(row["function"], oracle)
                if slot == len(ids) - 1:
                    self.assertIn("following_target_segment_not_observed", row["function"]["blockers"])

    def test_exact_origin_profiles_restore_frozen_oracle(self):
        inputs, _, _, result = self.compare()
        variants = {v["variant_id"]: v["variant"] for v in inputs[3]["variant_inventory"]}
        for path in result["hypotheses"]:
            ids = path["selector"]["variant_ids"]
            self.assertEqual(path["origin_refs"], [common.ref(variants[sid]) for sid in ids])
            self.assertEqual(path["profiles"], [frozen._profile(inputs[1], variants[sid]) for sid in ids])
            self.assertEqual(path["key_ref"]["record_id"], path["selector"]["key_id"])

    def test_different_registered_keys_remain_explicit_assumptions(self):
        inputs, _, record, _, session = self.ready("key")
        first, kernel = self.selector(inputs, record)
        second = deepcopy(first)
        second["key_id"] = next(k["record_id"] for k in inputs[2]["keys"] if k["record_id"] != first["key_id"])
        result = progression.compare_prepared(session, [first, second], self.bundle(record, kernel))
        self.assertEqual(len(result["hypotheses"]), 2)
        self.assertNotEqual(result["hypotheses"][0]["key_ref"], result["hypotheses"][1]["key_ref"])
        for path in result["hypotheses"]:
            for row in path["function_shapes"]:
                self.assertIsNone(row["function"]["function_confirmed"])
                self.assertIsNone(row["function"]["tonicization"])
                self.assertIsNone(row["function"]["modulation"])

    def test_incompatible_target_major_minor_do_not_exchange_role_paths(self):
        inputs, _, record, _, session = self.ready("incompatible")
        major, major_kernel = self.selector(inputs, record)
        minor, _ = self.selector(inputs, record, quality="m")
        result = progression.compare_prepared(session, [major, minor], self.bundle(record, major_kernel))
        answers = [p["transition_assessment"]["ordinary_strategy"]["whole_ordinary_template_satisfied"]
                   for p in result["hypotheses"]]
        self.assertEqual(answers, [True, False])
        for path in result["hypotheses"]:
            self.assert_raw_account(path)

    def test_wrong_ordinary_family_is_retained_not_auto_repaired(self):
        inputs, _, record, _, session = self.ready()
        ordinary, kernel = self.selector(inputs, record)
        mismatched = deepcopy(ordinary)
        mismatched["transition"]["family"] = "V"
        result = progression.compare_prepared(session, [ordinary, mismatched], self.bundle(record, kernel))
        wrong = result["hypotheses"][1]
        self.assertEqual(wrong["selector"], mismatched)
        self.assertIn("source_ordinary_family_shape_mismatch", wrong["transition_assessment"]["function"]["blockers"])
        self.assertIsNot(wrong["transition_assessment"]["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        explicit = next(r for r in wrong["function_shapes"] if r["explicit_transition_assumption"])
        self.assertFalse(explicit["motion_assessed"])

    def test_partial_declared_strategy_never_becomes_whole_template_success(self):
        inputs, _, record, _, session = self.ready("doubled")
        existential, kernel = self.selector(inputs, record)
        role = self.helper.roles(record, kernel)["leading_tone"]
        source = next(o["source_sound_ref"] for o in role["options"] if o["qualified"])
        partial = deepcopy(existential)
        partial["transition"].update(strategy="declared_occurrence_set",
            declared_occurrences=[{"role": "leading_tone", "sound_ref": source}])
        result = progression.compare_prepared(session, [existential, partial], self.bundle(record, kernel))
        ordinary = result["hypotheses"][1]["transition_assessment"]["ordinary_strategy"]
        self.assertIs(ordinary["declared_strategy_satisfied"], True)
        self.assertIs(ordinary["required_role_coverage_complete"], False)
        self.assertIs(ordinary["whole_ordinary_template_satisfied"], False)

    def test_result_preserves_source_inputs_and_prior_bulk_bytes(self):
        inputs, _, record, _, session = self.ready()
        selector, kernel = self.selector(inputs, record)
        selectors = [selector, self.fullhold(inputs)]
        before = deepcopy((inputs, record, selectors))
        progression.compare_prepared(session, selectors, self.bundle(record, kernel))
        self.assertEqual((inputs, record, selectors), before)

    def test_public_prepared_call_does_not_replay_profile_geometry_or_bulk(self):
        inputs, _, record, _, session = self.ready()
        selector, kernel = self.selector(inputs, record)
        with patch.object(frozen, "_profile", side_effect=AssertionError("no profile regeneration")), \
                patch.object(delayed.geometry, "query", side_effect=AssertionError("no geometry regeneration")), \
                patch.object(delayed, "_body", side_effect=AssertionError("no bulk regeneration")):
            result = progression.compare_prepared(session, [selector, self.fullhold(inputs)], self.bundle(record, kernel))
        self.assertEqual(len(result["hypotheses"]), 2)

    def test_invalid_caps_reject_booleans_and_unknown_names(self):
        for name in progression.CAPS:
            for value in (True, False, -1, 1.0, "1", None):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    progression.compare_prepared(None, [], None, **{name: value})
        with self.assertRaises(TypeError):
            progression.compare_prepared(None, [], None, undeclared_limit=1)

    def test_hypothesis_cap_is_whole_hold_not_favorable_prefix(self):
        inputs, _, record, _, session = self.ready()
        first, kernel = self.selector(inputs, record)
        selectors = [first, self.fullhold(inputs)]
        with patch.object(delayed, "_query", side_effect=AssertionError("no prefix assessment")):
            result = progression.compare_prepared(session, selectors, self.bundle(record, kernel), max_hypotheses=1)
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["contrasts"], [])
        self.assertEqual(result["selectors"], selectors)
        self.assertEqual(result["logical_universe"], record["logical_universe"])

    def test_contrast_cap_is_whole_hold_not_prefix(self):
        inputs, _, record, _, session = self.ready()
        first, kernel = self.selector(inputs, record)
        selectors = [first, self.fullhold(inputs)]
        with patch.object(delayed, "_query", side_effect=AssertionError("no contrast prefix")):
            result = progression.compare_prepared(session, selectors, self.bundle(record, kernel), max_comparisons=0)
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["contrasts"], [])
        self.assertEqual(result["selectors"], selectors)

    def test_zero_work_preserves_identities_and_whole_unassessed_complement(self):
        inputs, record, selectors, result = self.compare(query_work_budget=0)
        self.assertEqual(result["logical_universe"], record["logical_universe"])
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["contrasts"], [])
        self.assertEqual(result["selectors"], selectors)
        variants = {v["variant_id"]: v for v in inputs[3]["variant_inventory"]}
        for identity in result["selector_inventory"]:
            ids = identity["origin_variant_ids"]
            self.assertEqual(identity["origin_refs"], [common.ref(variants[sid]["variant"]) for sid in ids])
            self.assertEqual(identity["profile_refs"], [variants[sid]["profile_ref"] for sid in ids])
            self.assertEqual(identity["key_ref"]["record_id"], identity["selector"]["key_id"])
        self.assertGreater(result["summary"]["planned_query_work_items"], 0)
        self.assertEqual(result["summary"]["tested_logical_path_key_tuples"], 0)
        self.assertEqual(result["summary"]["tested_function_shapes"], 0)
        self.assertEqual(result["summary"]["unassessed_transition_function_rows"],
            record["logical_universe"]["logical_function_rows"])

    def test_profile_parent_hold_is_none_not_known_zero_or_missing_origin(self):
        inputs, _, record, _, session = self.ready("profile_hold")
        logical = self.helper.factory.target_logical((inputs[:2], *inputs[2:5]), "M")
        pair = {"group_id": logical[0], "variant_ids": logical[1], "key_id": logical[2],
            "transition": {"family": "V7", "quality": "M", "strategy": "ordinary_role_existential",
            "declared_occurrences": None, "requested_explanations": None}}
        bundles = record["inherited_bundle_inventory"] + record["bundle_inventory"]
        result = progression.compare_prepared(session, [pair, self.fullhold(inputs)],
            bundles[0]["record_id"] if bundles else None)
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["contrasts"], [])
        self.assertIsNone(result["summary"]["planned_query_work_items"])
        for identity in result["selector_inventory"]:
            self.assertTrue(all(ref is not None for ref in identity["origin_refs"]))
            self.assertTrue(all(ref is not None for ref in identity["profile_refs"]))
        self.assertEqual(result["summary"]["tested_logical_path_key_tuples"], 0)

    def test_selector_records_are_closed_and_typed(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        invalid = [None, True, [], dict(valid, winner=True)]
        for field in valid:
            item = deepcopy(valid)
            del item[field]
            invalid.append(item)
        for field, value in (("group_id", True), ("key_id", True), ("key_id", "foreign"),
                             ("variant_ids", tuple(valid["variant_ids"])), ("variant_ids", [True, True])):
            item = deepcopy(valid)
            item[field] = value
            invalid.append(item)
        for item in invalid:
            with self.subTest(selector=item), self.assertRaises(ValueError):
                progression.compare_prepared(session, [item, self.fullhold(inputs)], self.bundle(record, kernel))

    def test_incomplete_reordered_duplicate_and_wrong_slot_paths_rejected(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        for ids in (valid["variant_ids"][:1], valid["variant_ids"][::-1],
                    [valid["variant_ids"][0]] * 2,
                    valid["variant_ids"] + [self.fullhold(inputs)["variant_ids"][0]]):
            wrong = dict(valid, variant_ids=ids)
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                progression.compare_prepared(session, [wrong, self.fullhold(inputs)], self.bundle(record, kernel))

    def test_transition_records_closed_and_fullhold_cannot_claim_pair_obligation(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        changes = (None, True, dict(valid["transition"], confidence=1),
                   dict(valid["transition"], quality=True),
                   dict(valid["transition"], family="foreign"),
                   dict(valid["transition"], strategy="foreign"))
        for transition in changes:
            wrong = dict(valid, transition=transition)
            with self.subTest(transition=transition), self.assertRaises(ValueError):
                progression.compare_prepared(session, [wrong, self.fullhold(inputs)], self.bundle(record, kernel))
        wrong = self.fullhold(inputs)
        wrong["transition"] = valid["transition"]
        with self.assertRaises(ValueError):
            progression.compare_prepared(session, [valid, wrong], self.bundle(record, kernel))

    def test_nested_clause_requests_are_validated_even_under_whole_admission_hold(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        malformed = (True, [{"stage": "local", "geometry_id": "foreign", "side": "right"}],
            [{"stage": "boundary", "geometry_id": "foreign", "side": "right", "winner": True}])
        for requests in malformed:
            wrong = deepcopy(valid)
            wrong["transition"]["requested_explanations"] = requests
            for cap in (0, 64):
                with self.subTest(requests=requests, cap=cap), self.assertRaises(ValueError):
                    progression.compare_prepared(session, [wrong, self.fullhold(inputs)],
                        self.bundle(record, kernel), max_hypotheses=cap)

    def test_nested_declared_sets_are_validated_even_under_whole_admission_hold(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        malformed = (None, [], True,
            [{"role": "leading_tone", "sound_ref": "foreign"}],
            [{"role": "leading_tone", "sound_ref": "foreign", "winner": True}])
        for declarations in malformed:
            wrong = deepcopy(valid)
            wrong["transition"].update(strategy="declared_occurrence_set", declared_occurrences=declarations)
            for cap in (0, 64):
                with self.subTest(declarations=declarations, cap=cap), self.assertRaises(ValueError):
                    progression.compare_prepared(session, [wrong, self.fullhold(inputs)],
                        self.bundle(record, kernel), max_hypotheses=cap)

    def test_exact_duplicate_selectors_cannot_inflate_comparison_denominator(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        with self.assertRaises(ValueError):
            progression.compare_prepared(session, [valid, deepcopy(valid)], self.bundle(record, kernel))

    def test_function_alternative_selectors_do_not_duplicate_logical_tuple_counts(self):
        inputs, _, record, _, session = self.ready()
        ordinary, kernel = self.selector(inputs, record)
        alternate = deepcopy(ordinary)
        alternate["transition"]["family"] = "V"
        result = progression.compare_prepared(session, [ordinary, alternate], self.bundle(record, kernel))
        summary = result["summary"]
        self.assertEqual(summary["planned_hypotheses"], 2)
        self.assertEqual(summary["unique_requested_logical_tuples"], 1)
        self.assertEqual(summary["tested_logical_path_key_tuples"], 1)
        self.assertEqual(summary["tested_function_shapes"], 20)
        self.assertEqual(summary["assessed_transition_function_rows"], 1)
        self.assertEqual(summary["tested_logical_path_key_tuples"] +
            summary["unassessed_logical_path_key_tuples"], record["logical_universe"]["logical_path_key_tuples"])
        self.assertEqual(summary["tested_function_shapes"] + summary["unassessed_function_shapes"],
            record["logical_universe"]["logical_function_rows"])
        self.assertEqual(summary["assessed_transition_function_rows"] +
            summary["unassessed_transition_function_rows"], record["logical_universe"]["logical_function_rows"])
        self.assertTrue(all(p["whole_path_account"]["competing_function_credits_pooled"] is False
            for p in result["hypotheses"]))

    def test_canonical_declared_order_cannot_create_duplicate_hypotheses(self):
        inputs, _, record, _, session = self.ready()
        selector, kernel = self.selector(inputs, record)
        declarations = [{"role": name, "sound_ref": next(o["source_sound_ref"] for o in role["options"] if o["qualified"])}
            for name, role in self.helper.roles(record, kernel).items()]
        selector["transition"].update(strategy="declared_occurrence_set", declared_occurrences=declarations)
        permutation = deepcopy(selector)
        permutation["transition"]["declared_occurrences"].reverse()
        with self.assertRaises(ValueError):
            progression.compare_prepared(session, [selector, permutation], self.bundle(record, kernel))

    def test_empty_request_zero_caps_is_known_zero_not_inventory_unknown(self):
        _, _, record, _, session = self.ready()
        result = progression.compare_prepared(session, [], self.helper.control(record),
            **{name: 0 for name in progression.CAPS})
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["contrasts"], [])
        self.assertEqual(result["reasons"], [])
        for field in ("planned_hypotheses", "computed_hypotheses", "planned_comparisons",
                      "computed_comparisons", "planned_query_work_items", "tested_function_shapes"):
            self.assertEqual(result["summary"][field], 0, field)

    def test_fullhold_no_pair_has_known_zero_boundary_delayed_applicability(self):
        inputs, _, record, _, session = self.ready("no_pair", **{name: 0 for name in delayed.CAPS})
        bundles = record["inherited_bundle_inventory"] + record["bundle_inventory"]
        result = progression.compare_prepared(session, [self.fullhold(inputs)],
            bundles[0]["record_id"] if bundles else None)
        self.assertEqual(len(result["hypotheses"]), 1)
        path = result["hypotheses"][0]
        for axis in ("direct_motion_applicable", "boundary_explanation_applicable", "delayed_ordinary_applicable"):
            self.assertFalse(path["axes"][axis], axis)
        self.assertEqual(path["axes"]["registered_boundary_clause_count"], 0)
        self.assertEqual(path["axes"]["registered_delayed_transition_count"], 0)
        self.assertIsNone(path["transition_assessment"])
        self.assertFalse(any(r["motion_assessed"] for r in path["function_shapes"]))

    def test_pure_impossible_completion_is_known_false_without_partial_lane_credit(self):
        inputs, _, record, _, session = self.ready("incompatible")
        major, major_kernel = self.selector(inputs, record)
        _, minor_kernel = self.selector(inputs, record, quality="m")
        plans = (self.helper.plan(record, major_kernel), self.helper.plan(record, minor_kernel))
        required = tuple(sorted({tuple(e) for plan in plans for branch in plan["branches"]
            if branch["status"] == "possible" for e in branch["required_links"]}))
        impossible = delayed._bundle({"scope": inputs[1], "index": inputs[3], "grounding": inputs[5]},
            record["logical_universe"], required, 100000)
        self.assertEqual(impossible["geometry_condition_status"], "impossible")
        state = progression._issued(session)[1]
        selection = progression._selection_identity(state, major)
        path = progression._path(state, selection, progression._plan(state, selection), impossible, 100000)
        self.assertTrue(path["axes"]["completion_certified_impossible"])
        self.assertFalse(path["axes"]["same_complete_all_lane_bundle"])
        self.assertIs(path["transition_assessment"]["ordinary_strategy"]["whole_ordinary_template_satisfied"], False)
        self.assertIsNone(path["whole_path_account"]["conditional_explanation_note_time"])
        self.assertEqual(common.f(path["whole_path_account"]["note_time"]["conditional_combined_explained_nonmember"]), 0)
        self.assert_raw_account(path)
        with self.assertRaises(ValueError):
            progression.compare_prepared(session, [major, self.fullhold(inputs)], impossible["record_id"])

    def test_pure_unknown_completion_remains_none_not_false_or_borrowed_witness(self):
        inputs, _, record, _, session = self.ready()
        selector, kernel = self.selector(inputs, record)
        source = next(b for b in record["bundle_inventory"] if b["record_id"] == self.bundle(record, kernel))
        unknown = deepcopy(source)
        # This deliberately unregistered pure-helper fixture is not admitted
        # as public authority and does not pretend to be a geometry replay.
        unknown.update(status="all_lane_witness_withheld", geometry_condition_status="unknown",
            reasons=["pure_fixture_unassessed_lane"])
        unknown["entries"][0]["witness"] = None
        state = progression._issued(session)[1]
        selection = progression._selection_identity(state, selector)
        path = progression._path(state, selection, progression._plan(state, selection), unknown, 100000)
        self.assertFalse(path["axes"]["completion_certified_impossible"])
        self.assertFalse(path["axes"]["same_complete_all_lane_bundle"])
        self.assertIsNone(path["transition_assessment"]["ordinary_strategy"]["whole_ordinary_template_satisfied"])
        self.assertIsNone(path["whole_path_account"]["conditional_explanation_note_time"])
        self.assertEqual(common.f(path["whole_path_account"]["note_time"]["conditional_combined_explained_nonmember"]), 0)
        self.assert_raw_account(path)
        self.assertFalse(progression._contrast(path, path, 0, 1)["comparable"])

    def test_registered_bundle_id_not_caller_bundle_body_is_authority(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        for fake in (None, True, "foreign", {"record_id": self.bundle(record, kernel)}):
            with self.subTest(fake=fake), self.assertRaises(ValueError):
                progression.compare_prepared(session, [valid, self.fullhold(inputs)], fake)

    def test_preparation_requires_issued_authentic_delayed_handle(self):
        for fake in (None, True, object(), delayed._PreparedObligations()):
            with self.subTest(fake=type(fake).__name__), self.assertRaises(ValueError):
                progression.prepare_comparison_prepared(fake)

    def test_forged_comparison_and_owned_hmac_changes_are_rejected(self):
        inputs, _, record, _, session = self.ready()
        selector, kernel = self.selector(inputs, record)
        with self.assertRaises(ValueError):
            progression.compare_prepared(progression._PreparedComparison(),
                [selector, self.fullhold(inputs)], self.bundle(record, kernel))
        original = progression._SESSIONS[session]
        progression._SESSIONS[session] = replace(original, authentication=b"\0" * 32)
        try:
            with self.assertRaises(ValueError):
                progression.compare_prepared(session, [selector, self.fullhold(inputs)], self.bundle(record, kernel))
        finally:
            progression._SESSIONS[session] = original

    def test_owned_upstream_replacement_and_mutable_callers_do_not_bypass_authority(self):
        inputs, _, record, parent, session = self.ready()
        selector, kernel = self.selector(inputs, record)
        selectors = [selector, self.fullhold(inputs)]
        expected = progression.compare_prepared(session, selectors, self.bundle(record, kernel))
        inputs[3]["variant_inventory"].clear()
        record["origin_inventory"].clear()
        self.assertEqual(progression.compare_prepared(session, selectors, expected["bundle_id"]), expected)
        original = delayed._SESSIONS[parent]
        replacement = replace(original)
        object.__setattr__(replacement, "authentication", delayed._auth(parent, replacement))
        delayed._SESSIONS[parent] = replacement
        try:
            with self.assertRaises(ValueError):
                progression.compare_prepared(session, selectors, expected["bundle_id"])
        finally:
            delayed._SESSIONS[parent] = original

    def test_resealed_modified_delayed_record_is_not_authority(self):
        _, supplier, record, _, _ = self.ready()
        forged = deepcopy(record)
        forged["origin_inventory"].pop()
        with self.assertRaises(ValueError):
            parent = delayed.prepare_obligations_prepared(supplier, reseal(forged, delayed.PREFIX))
            progression.prepare_comparison_prepared(parent)

    def test_same_scope_rejects_a_foreign_complete_tuple(self):
        inputs, _, record, _, session = self.ready()
        valid, kernel = self.selector(inputs, record)
        other, _, other_record, _, _ = self.ready("direct")
        foreign, _ = self.selector(other, other_record)
        with self.assertRaises(ValueError):
            progression.compare_prepared(session, [valid, foreign], self.bundle(record, kernel))

    def test_no_winner_rank_confidence_or_final_music_verdict(self):
        _, _, _, result = self.compare()
        for record in [result, *result["hypotheses"], *result["contrasts"]]:
            for field in ("selected", "rank", "confidence"):
                self.assertIsNone(record.get(field))
        self.assertTrue(all(value is False for value in result["flags"].values()))

    def test_current_source_change_invalidates_issued_comparison_session(self):
        inputs, _, record, _, session = self.ready()
        selector, kernel = self.selector(inputs, record)
        actual = Path.read_bytes
        def changed(path):
            return actual(path) + b"\n" if path == Path(progression.__file__) else actual(path)
        with patch.object(Path, "read_bytes", changed), self.assertRaises(ValueError):
            progression.compare_prepared(session, [selector, self.fullhold(inputs)], self.bundle(record, kernel))


if __name__ == "__main__":
    unittest.main()
