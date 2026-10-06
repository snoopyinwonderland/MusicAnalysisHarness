"""Explicit ordinary strategies and authentic same-completion accounts."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from musicanote_harness import factor_delayed_obligations as delayed
from musicanote_harness import factor_boundary_explanations as boundary
from musicanote_harness import factor_temporal_explanations as temporal
from musicanote_harness import factor_grounded_relations as grounded
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_expanded_scope as expanded
from musicanote_harness import factor_function_relations as relations
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_musical_view as common
from test_factor_temporal_explanations import TemporalExplanationFixture
from test_factor_expanded_hypotheses import event, span
from test_factor_musical_view import reseal


class DelayedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = TemporalExplanationFixture()
        cls.factory.addCleanup = cls.addClassCleanup
        cls.factory.setUp()
        cls.raw_cache = {}
        cls.ready_cache = {}

    def inputs(self, name="held"):
        if name not in self.raw_cache:
            leading = [event("B4", 0, 3), event("C5", 3, 1)]
            seventh = [event("F4", 0, 3), event("E4", 3, 1)]
            harmony = [[event("G3", 0, 2), event("C3", 2, 2)],
                       [event("D4", 0, 2), event("G4", 2, 2)]]
            extra = []
            if name == "direct":
                leading = [event("B4", 0, 2), event("C5", 2, 2)]
                seventh = [event("F4", 0, 2), event("E4", 2, 2)]
            elif name == "reattack":
                leading = [event("B4", 0, 2), event("B4", 2, Fraction(1, 2)),
                           event("B4", Fraction(5, 2), Fraction(1, 2)), event("C5", 3, 1)]
                seventh = [event("F4", 0, 2), event("F4", 2, Fraction(1, 2)),
                           event("F4", Fraction(5, 2), Fraction(1, 2)), event("E4", 3, 1)]
            elif name == "doubled":
                extra = [[event("B3", 0, 3), event("A3", 3, 1)]]
            elif name == "combined":
                extra = [[event("C5", 0, 2), event("C5", 2, Fraction(1, 2)),
                          event("D5", Fraction(5, 2), Fraction(1, 2)), event("E5", 3, 1)]]
            elif name == "firstwrong":
                leading = [event("B4", 0, 3), event("D5", 3, Fraction(1, 2)),
                           event("C5", Fraction(7, 2), Fraction(1, 2))]
            elif name == "terminal":
                leading = [event("B4", 0, 4)]
            elif name == "incompatible":
                seventh = [event("F4", 0, 3), event(["E4", "E-4"], 3, 1)]
            elif name in ("no_pair", "no_pair_profile_hold"):
                leading = [event(["C3", "E4", "G4"], 0, 4)]
                seventh = []; harmony = []
            elif name not in ("held", "shape_hold", "profile_hold", "index_hold"):
                raise AssertionError(name)
            lanes = [leading, *([seventh] if seventh else []), *harmony, *extra]
            frozen_case = self.factory.frozen_case(self.factory.make(lanes,
                **({"index_options": {"max_variants": 0}} if name == "index_hold" else {})),
                relation_options={"max_kernels": 0} if name == "shape_hold" else None)
            case = (*frozen_case[0], *frozen_case[1:])
            grounding = grounded.build_grounding(*case,
                **({"max_profiles": 0} if name in ("profile_hold", "no_pair_profile_hold") else {}))
            parent_inputs = (*case, grounding)
            local = temporal.build_explanations(*parent_inputs)
            boundary_inputs = (*parent_inputs, local)
            boundary_supplier = boundary.prepare_inputs(*boundary_inputs)
            border = boundary.build_explanations_prepared(boundary_supplier)
            self.raw_cache[name] = (*boundary_inputs, border)
        return deepcopy(self.raw_cache[name])

    def ready(self, name="held", **caps):
        inputs = self.inputs(name)
        signature = common.digest(delayed._contract())
        key = (name, signature, tuple(sorted(caps.items())))
        if key not in self.ready_cache:
            supplier = delayed.prepare_inputs(*inputs)
            record = delayed.build_obligations_prepared(supplier, **caps)
            self.ready_cache[key] = supplier, record
        supplier, record = self.ready_cache[key]
        return inputs, supplier, deepcopy(record)

    def selected(self, inputs, record, *, family="V7", quality="M"):
        logical = self.factory.target_logical((inputs[:2], *inputs[2:5]), quality)
        kernel = next(k for k in record["obligation_kernel_inventory"]
            if k["group_id"] == logical[0] and k["family"] == family and k["quality"] == quality
            and logical[1][0] in k["source_variant_ids"] and logical[1][1] in k["target_variant_ids"])
        return logical, kernel

    @staticmethod
    def roles(record, kernel):
        by_id = {r["record_id"]: r for r in record["role_option_inventory"]}
        return {by_id[ref["record_id"]]["role"]: by_id[ref["record_id"]] for ref in kernel["role_option_refs"]}

    @staticmethod
    def plan(record, kernel):
        return next(p for p in record["joint_plan_inventory"] if common.ref(p) == kernel["joint_plan_ref"])

    @staticmethod
    def control(record):
        return next(b["record_id"] for b in record["inherited_bundle_inventory"] if not b["required_links"])

    def query(self, inputs, supplier, record, *, kernel=None, bundle=None, **options):
        logical, actual = self.selected(inputs, record)
        kernel = kernel or actual
        if bundle is None:
            branch = next(b for b in self.plan(record, kernel)["branches"] if b["status"] == "possible")
            bundle = branch["bundle_ref"]["record_id"]
        session = delayed.prepare_obligations_prepared(supplier, record)
        return delayed.query_obligations_prepared(session, logical[0], *logical[1], logical[2],
            kernel["family"], kernel["quality"], bundle, **options)

    def compile(self, inputs, supplier, record, **options):
        logical, kernel = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        return delayed.compile_joint_prepared(session, logical[0], *logical[1], logical[2],
            kernel["family"], kernel["quality"], **options)

    def assert_accounts(self, result):
        self.assertEqual(len(result["combined_accounts"]), 2)
        for profile, account in zip(result["profiles"], result["combined_accounts"]):
            self.assertEqual(account["raw_note_time"], profile["note_time_quarters"])
            self.assertEqual(account["total_note_time"], profile["total_note_time_quarters"])
            self.assertEqual(set(account["note_time"]), set(delayed.CATEGORIES))
            self.assertEqual(sum((common.f(v) for v in account["note_time"].values()), Fraction()),
                common.f(profile["total_note_time_quarters"]))
            self.assertLessEqual(common.f(account["conditional_explanation_note_time"] or common.q(0)),
                common.f(profile["note_time_quarters"]["nonmember_not_confirmed_nct"]))

    def test_public_prepared_identity_and_all_eight_exact_bindings(self):
        inputs, supplier, record = self.ready("direct")
        before = deepcopy(inputs)
        self.assertEqual(delayed.build_obligations(*inputs), record)
        self.assertTrue(delayed.validate_obligations(*inputs, record))
        self.assertEqual(inputs, before)
        for field, parent in (("scope_ref", inputs[1]), ("hypotheses_ref", inputs[2]),
            ("index_ref", inputs[3]), ("relations_ref", inputs[4]), ("grounding_ref", inputs[5]),
            ("temporal_ref", inputs[6]), ("boundary_ref", inputs[7])):
            self.assertEqual(record[field], common.ref(parent))
        self.assertEqual(record["origin_inventory"], inputs[5]["origin_inventory"])
        self.assertEqual(record["descriptor_inventory"], inputs[3]["profile_inventory"])
        self.assertEqual(record["inherited_bundle_inventory"],
            inputs[7]["inherited_bundle_inventory"] + inputs[7]["bundle_inventory"])

    def test_held_leading_tone_and_seventh_are_conditional_without_direct_override(self):
        inputs, _, record = self.ready()
        _, kernel = self.selected(inputs, record)
        self.assertEqual(kernel["status"], "conditional")
        self.assertEqual(set(self.roles(record, kernel)), {"leading_tone", "seventh"})
        self.assertNotEqual(kernel["old_direct_status"], "conditional_joint_direct_motion_shape")
        routes = {r["record_id"]: r for r in record["route_inventory"]}
        for role in self.roles(record, kernel).values():
            options = [o for o in role["options"] if o["qualified"]]
            self.assertTrue(options)
            self.assertTrue(all(routes[o["route_ref"]["record_id"]]["source_physically_held_at_cut"] for o in options))
            self.assertTrue(all(routes[o["route_ref"]["record_id"]]["chain_edges"] == 1 for o in options))

    def test_reattacks_require_entire_three_edge_route_for_both_roles(self):
        inputs, _, record = self.ready("reattack")
        _, kernel = self.selected(inputs, record)
        routes = {r["record_id"]: r for r in record["route_inventory"]}
        plan = self.plan(record, kernel)
        self.assertTrue(plan["branches"])
        for branch in plan["branches"]:
            self.assertEqual(len(branch["required_links"]), 6)
            self.assertTrue(all(routes[r["record_id"]]["chain_edges"] == 3 for r in branch["route_refs"]))

    def test_doubling_physical_ledger_does_not_assign_universal_obligations(self):
        inputs, _, record = self.ready("doubled")
        _, kernel = self.selected(inputs, record)
        leading = self.roles(record, kernel)["leading_tone"]
        self.assertEqual(len(leading["matching_occurrence_refs"]), 2)
        self.assertEqual(sum(o["qualified"] for o in leading["options"]), 1)
        self.assertEqual(kernel["status"], "conditional")
        self.assertTrue(all(o["obligation_assignment"] == "not_assigned_by_physical_occurrence_alone"
                            for o in record["physical_occurrence_inventory"]))

    def test_first_wrong_changed_endpoint_cannot_skip_later_correct_pitch(self):
        inputs, _, record = self.ready("firstwrong")
        _, kernel = self.selected(inputs, record)
        leading = self.roles(record, kernel)["leading_tone"]
        self.assertTrue(leading["options"])
        self.assertFalse(any(o["qualified"] for o in leading["options"]))
        self.assertTrue(all("ordinary_leading_tone_strategy_motion_not_matched" in o["blockers"]
                            for o in leading["options"]))
        self.assertEqual(kernel["status"], "withheld")

    def test_terminal_occurrence_is_observed_but_ordinary_strategy_withheld(self):
        inputs, _, record = self.ready("terminal")
        _, kernel = self.selected(inputs, record)
        leading = self.roles(record, kernel)["leading_tone"]
        self.assertTrue(leading["matching_occurrence_refs"])
        self.assertTrue(all("first_changed_endpoint_not_observed_terminal" in o["blockers"] for o in leading["options"]))
        self.assertEqual(kernel["status"], "withheld")

    def test_individually_qualified_roles_need_one_compatible_joint_completion(self):
        inputs, _, record = self.ready("incompatible")
        _, kernel = self.selected(inputs, record)
        self.assertTrue(all(any(o["qualified"] for o in role["options"])
                            for role in self.roles(record, kernel).values()))
        plan = self.plan(record, kernel)
        self.assertGreater(plan["planned_joint_options"], 0)
        self.assertEqual(plan["supported_joint_options"], 1)
        logical, minor = self.selected(inputs, record, quality="m")
        alternate = self.plan(record, minor)
        self.assertEqual(alternate["supported_joint_options"], 1)
        required = tuple(sorted({tuple(e) for p in (plan, alternate) for b in p["branches"]
                                 if b["status"] == "possible" for e in b["required_links"]}))
        impossible = delayed._bundle({"scope": inputs[1], "index": inputs[3], "grounding": inputs[5]},
            record["logical_universe"], required, 100000)
        self.assertEqual(impossible["geometry_condition_status"], "impossible")
        self.assertTrue(any(e["query"]["possible_assignments"] == "0" for e in impossible["entries"]))

    def test_incomplete_cut_core_is_separate_from_qualified_later_endpoint(self):
        inputs, _, record = self.ready()
        _, kernel = self.selected(inputs, record)
        audit = kernel["literal_core_and_time_audit"]
        self.assertTrue(audit["target_cut_cell"]["source_guard_missing_spellings"])
        self.assertEqual(audit["right_eligible_complete_literal_core_spans"], [span(3, 4)])
        self.assertEqual(audit["right_fully_source_guarded_complete_literal_core_spans"], [span(3, 4)])
        self.assertTrue(audit["target_cut_full_guard_audit"]["full_source_guard_missing_spellings"])
        self.assertTrue(all(o["endpoint_membership"] == "member" for role in self.roles(record, kernel).values()
                            for o in role["options"] if o["qualified"]))
        self.assertEqual(kernel["status"], "conditional")
        self.assertFalse(audit["pooled_members_certify_harmony"])

    def test_all_functional_complements_and_weighted_denominators_survive(self):
        inputs, _, record = self.ready()
        summary = record["summary"]
        for name in ("logical_paths", "logical_path_key_tuples", "logical_function_rows", "unknown_product_groups"):
            self.assertEqual(summary[name], inputs[5]["summary"][name])
        self.assertEqual(sum(summary[n] for n in ("weighted_conditional_ordinary_template_function_rows",
            "weighted_withheld_ordinary_template_function_rows", "weighted_unassessed_ordinary_template_function_rows")),
            summary["logical_function_rows"])
        self.assertEqual(summary["ordinary_template_shape_eligible_function_rows"] +
            summary["shape_prerequisite_complement_function_rows"], summary["logical_function_rows"])
        for group, original in zip(record["path_groups"], inputs[4]["path_groups"]):
            for name, value in original.items():
                self.assertEqual(group[name], value)
            self.assertEqual(sum(group["delayed_strategy_weights"].values()), original["logical_function_count"])

    def test_whole_route_cap_precounts_and_keeps_physical_occurrences(self):
        _, supplier, full = self.ready()
        held = delayed.build_obligations_prepared(supplier, max_route_candidates=0)
        self.assertEqual(held["summary"]["planned_route_candidates"], full["summary"]["planned_route_candidates"])
        self.assertEqual(held["physical_occurrence_inventory"], full["physical_occurrence_inventory"])
        self.assertEqual(held["route_inventory"], [])
        self.assertIsNone(held["summary"]["planned_role_options"])
        self.assertEqual(held["role_option_inventory"], [])

    def test_chain_depth_hold_does_not_truncate_reattacks(self):
        _, supplier, full = self.ready("reattack")
        held = delayed.build_obligations_prepared(supplier, max_chain_edges=2)
        self.assertEqual(held["summary"]["max_planned_chain_edges"], 3)
        self.assertEqual(held["summary"]["planned_route_candidates"], full["summary"]["planned_route_candidates"])
        self.assertEqual(held["route_inventory"], [])

    def test_whole_kernel_cap_retains_exact_specs_and_origin_denominators(self):
        _, supplier, full = self.ready()
        held = delayed.build_obligations_prepared(supplier, max_obligation_kernels=0)
        self.assertEqual(held["obligation_specification_inventory"], full["obligation_specification_inventory"])
        self.assertEqual(held["summary"]["planned_obligation_kernels"], full["summary"]["planned_obligation_kernels"])
        self.assertEqual(held["obligation_kernel_inventory"], [])
        self.assertIsNone(held["summary"]["planned_role_options"])

    def test_whole_role_cap_does_not_seal_partial_role_inventory(self):
        _, supplier, full = self.ready()
        original = delayed._seal
        def checked(body, prefix):
            if prefix == delayed.ROLE_PREFIX:
                raise AssertionError("no partial role prefix")
            return original(body, prefix)
        with patch.object(delayed, "_seal", checked):
            held = delayed.build_obligations_prepared(supplier, max_role_options=0)
        self.assertEqual(held["summary"]["planned_role_options"], full["summary"]["planned_role_options"])
        self.assertEqual(held["role_option_inventory"], [])
        self.assertIsNone(held["summary"]["planned_joint_options"])

    def test_whole_joint_cap_precounts_without_prefix_or_bundle_queries(self):
        _, supplier, full = self.ready()
        with patch.object(delayed, "_bundle", side_effect=AssertionError("no joint prefix")):
            held = delayed.build_obligations_prepared(supplier, max_joint_options=0)
        self.assertEqual(held["summary"]["planned_joint_options"], full["summary"]["planned_joint_options"])
        self.assertEqual(held["joint_plan_inventory"], [])
        self.assertIsNone(held["summary"]["planned_new_bundles"])

    def test_whole_bundle_cap_preserves_all_requests_and_inherited_bundles(self):
        inputs, supplier, full = self.ready()
        held = delayed.build_obligations_prepared(supplier, max_new_bundles=0)
        self.assertEqual(held["summary"]["planned_new_bundles"], full["summary"]["planned_new_bundles"])
        self.assertTrue(held["bundle_requests"])
        self.assertTrue(all(request["bundle_ref"] is None for request in held["bundle_requests"]))
        self.assertEqual(held["bundle_inventory"], [])
        self.assertEqual(held["inherited_bundle_inventory"], inputs[7]["inherited_bundle_inventory"] + inputs[7]["bundle_inventory"])
        for plan in held["joint_plan_inventory"]:
            if plan["planned_joint_options"]:
                self.assertIsNone(plan["supported_joint_options"])
            else:
                self.assertEqual(plan["supported_joint_options"], 0)

    def test_zero_work_closed_form_geometry_does_not_invent_a_work_hold(self):
        _, supplier, _ = self.ready()
        held = delayed.build_obligations_prepared(supplier, query_work_budget=0)
        self.assertTrue(held["bundle_inventory"])
        chains = [bundle for bundle in held["bundle_inventory"] if bundle["required_links"]]
        self.assertTrue(chains)
        self.assertTrue(all(bundle["geometry_condition_status"] in ("possible", "impossible") for bundle in chains))
        self.assertTrue(all(plan["supported_joint_options"] is not None for plan in held["joint_plan_inventory"]))

    def test_no_pair_all_zero_caps_remain_known_zero(self):
        _, _, record = self.ready("no_pair", **{name: 0 for name in delayed.CAPS})
        for name in ("planned_physical_occurrences", "planned_route_candidates", "planned_obligation_kernels",
            "planned_role_options", "planned_joint_options", "planned_new_bundles"):
            self.assertEqual(record["summary"][name], 0, name)
        self.assertTrue(record["summary"]["route_inventory_complete"])

    def test_authentic_shape_kernel_parent_hold_stays_unknown_not_empty(self):
        inputs, _, record = self.ready("shape_hold")
        self.assertIsNone(inputs[5]["summary"]["planned_motion_kernels"])
        self.assertIsNone(record["summary"]["planned_obligation_kernels"])
        for name in ("planned_role_options", "planned_joint_options", "planned_new_bundles"):
            self.assertIsNone(record["summary"][name], name)
        self.assertFalse(record["summary"]["ordinary_template_inventory_complete"])
        self.assertEqual(record["summary"]["weighted_unassessed_ordinary_template_function_rows"],
            inputs[5]["summary"]["logical_function_rows"])

    def test_source_guards_and_full_pair_containment_reject_neutral_routes(self):
        inputs, _, record = self.ready()
        original = next(r for r in record["route_inventory"] if r["source_physically_held_at_cut"] and not r["blockers"])
        pair = next(p for p in inputs[7]["pair_groups"] if p["group_id"] == original["group_id"])
        for field, value, code in (("source_clock_passed", False, "source_clock_passed_not_passed"),
            ("source_attack_consistency_passed", False, "source_attack_consistency_passed_not_passed"),
            ("source_pitch_consistency_passed", False, "source_pitch_consistency_passed_not_passed"),
            ("eligible_as_analysis_source", False, "source_not_eligible"), ("grace", True, "point_or_grace"),
            ("point", True, "point_or_grace")):
            for sid in original["involved_sound_refs"]:
                with self.subTest(field=field, sid=sid):
                    scope = deepcopy(inputs[1])
                    sound = next(s for s in scope["sound_facts"] if s["sound_ref"] == sid)
                    sound[field] = value
                    _, routes, *_ = delayed._routes(scope, [pair], delayed.DEFAULTS)
                    route = next(r for r in routes if r["involved_sound_refs"] == original["involved_sound_refs"])
                    self.assertTrue(any(code in reason for reason in route["blockers"]))
        scope = deepcopy(inputs[1])
        sound = next(s for s in scope["sound_facts"] if s["sound_ref"] == original["involved_sound_refs"][-1])
        sound["span"] = span(3, 5)
        _, routes, *_ = delayed._routes(scope, [pair], delayed.DEFAULTS)
        self.assertTrue(any("all_full_sound_spans_not_inside_original_pair" in r["blockers"] for r in routes))

    def test_invalid_boolean_numeric_and_unknown_caps_rejected_before_inputs(self):
        for name in delayed.CAPS:
            for value in (True, False, -1, 1.0, None, "1"):
                with self.subTest(name=name, value=value), patch.object(delayed, "prepare_inputs", side_effect=AssertionError("no parent reads")), self.assertRaises(ValueError):
                    delayed.build_obligations(*([None] * 8), **{name: value})
        with patch.object(delayed, "prepare_inputs", side_effect=AssertionError("no parent reads")), self.assertRaises(TypeError):
            delayed.build_obligations(*([None] * 8), foreign_cap=1)

    def test_resealed_origin_lost_count_changed_or_promoting_body_rejected(self):
        _, supplier, record = self.ready()
        for change in (lambda r: r.update(confidence=1), lambda r: r["summary"].update(queried_origin_tuples=False),
            lambda r: r["origin_inventory"].pop(), lambda r: r["path_groups"].pop(),
            lambda r: r["bundle_inventory"][0].update(symbolic_universe_ref=r["boundary_ref"])):
            forged = deepcopy(record); change(forged)
            with self.assertRaises(ValueError):
                delayed.prepare_obligations_prepared(supplier, reseal(forged, delayed.PREFIX))

    def test_genuine_but_foreign_boundary_and_resealed_parent_rejected(self):
        inputs, _, _ = self.ready()
        other = self.inputs("direct")
        for position in range(8):
            with self.subTest(position=position):
                mixed = list(inputs); mixed[position] = other[position]
                with self.assertRaises(ValueError):
                    delayed.prepare_inputs(*mixed)
        border = deepcopy(inputs[7]); border["summary"]["pair_accounts_computed"] = 1
        with self.assertRaises(ValueError):
            delayed.prepare_inputs(*inputs[:7], reseal(border, boundary.PREFIX))

    def test_forged_handles_owned_hmac_and_current_source_rejected(self):
        _, supplier, record = self.ready()
        with self.assertRaises(ValueError):
            delayed.build_obligations_prepared(delayed._PreparedInputs())
        original = delayed._INPUTS[supplier]
        delayed._INPUTS[supplier] = replace(original, authentication=b"\0" * 32)
        try:
            with self.assertRaises(ValueError):
                delayed.build_obligations_prepared(supplier)
        finally:
            delayed._INPUTS[supplier] = original
        actual = Path.read_bytes
        def changed(path):
            return actual(path) + b"\n" if path == Path(delayed.__file__) else actual(path)
        with patch.object(Path, "read_bytes", changed), self.assertRaises(ValueError):
            delayed.build_obligations_prepared(supplier)

    def test_owned_frozen_inputs_detach_caller_and_thaw_without_aliases(self):
        inputs = self.inputs()
        supplier = delayed.prepare_inputs(*inputs)
        expected = delayed.build_obligations_prepared(supplier)
        inputs[3]["variant_inventory"].clear()
        inputs[7]["pair_groups"].clear()
        state = delayed._issued(supplier, delayed._INPUTS, delayed._PreparedInputs)
        thawed = indexed._thaw(state.data)
        thawed["scope"]["sound_facts"].clear()
        with self.assertRaises(TypeError):
            state.data["scope"] = None
        self.assertEqual(delayed.build_obligations_prepared(supplier), expected)

    def test_no_selection_training_final_truth_or_universal_motion_claims(self):
        _, _, record = self.ready()
        self.assertTrue(all(value is False for value in record["flags"].values()))
        for field in ("selected", "rank", "confidence"):
            self.assertIsNone(record[field])
        self.assertEqual(record["summary"]["queried_origin_tuples"], 0)
        self.assertEqual(record["summary"]["combined_accounts_computed"], 0)
        self.assertEqual(record["summary"]["exception_strategy_families_computed"], 0)

    def test_lazy_origin_profiles_and_function_restore_exact_frozen_oracles(self):
        inputs, supplier, record = self.ready()
        logical, _ = self.selected(inputs, record)
        result = self.query(inputs, supplier, record)
        variants = {v["variant_id"]: v["variant"] for v in inputs[3]["variant_inventory"]}
        self.assertEqual(result["profiles"], [frozen._profile(inputs[1], variants[v]) for v in logical[1]])
        key = next(k for k in inputs[3]["keys"] if k["record_id"] == logical[2])
        self.assertEqual(result["function"], frozen._function(inputs[1], variants[logical[1][0]],
            variants[logical[1][1]], key["segments"][0], "V7", "M"))
        self.assertEqual(result["origin_variant_ids"], logical[1])
        self.assert_accounts(result)

    def test_same_bundle_local_boundary_delayed_credit_is_union_not_sum(self):
        inputs, supplier, record = self.ready()
        result = self.query(inputs, supplier, record)
        self.assertIs(result["ordinary_strategy"]["ordinary_role_existential_satisfied"], True)
        self.assertIs(result["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        self.assert_accounts(result)
        self.assertEqual(common.f(result["combined_accounts"][0]["conditional_explanation_note_time"]), 0)
        self.assertEqual(common.f(result["combined_accounts"][1]["conditional_explanation_note_time"]), 2)
        supported = [a for a in result["explanation_assessments"] if a["status"].startswith("conditional")]
        self.assertTrue(any(a["stage"] == "boundary" for a in supported))
        self.assertEqual(sum(a["stage"] == "delayed_ordinary" for a in supported), 2)
        self.assertEqual(len(result["combined_accounts"][1]["credited_intervals_by_sound"]), 2)

    def test_no_link_control_does_not_borrow_delayed_or_boundary_witness(self):
        inputs, supplier, record = self.ready()
        result = self.query(inputs, supplier, record, bundle=self.control(record))
        self.assertIs(result["ordinary_strategy"]["ordinary_role_existential_satisfied"], False)
        self.assert_accounts(result)
        self.assertTrue(all(common.f(a["conditional_explanation_note_time"]) == 0 for a in result["combined_accounts"]))

    def test_declared_doublings_are_and_not_existential_success(self):
        inputs, supplier, record = self.ready("doubled")
        _, kernel = self.selected(inputs, record)
        roles = self.roles(record, kernel)
        declarations = [{"role": name, "sound_ref": sid} for name, role in roles.items()
            for sid in sorted({o["source_sound_ref"] for o in role["options"]})]
        existential = self.query(inputs, supplier, record)
        declared = self.query(inputs, supplier, record, strategy="declared_occurrence_set", declared_occurrences=declarations)
        self.assertIs(existential["ordinary_strategy"]["ordinary_role_existential_satisfied"], True)
        self.assertIs(declared["ordinary_strategy"]["required_role_coverage_complete"], True)
        self.assertIs(declared["ordinary_strategy"]["all_declared_obligations_satisfied"], False)
        self.assertIs(declared["ordinary_strategy"]["whole_ordinary_template_satisfied"], False)
        self.assertEqual(len(declared["ordinary_strategy"]["role_assessments"]), 3)
        self.assertEqual(self.compile(inputs, supplier, record, strategy="declared_occurrence_set",
            declared_occurrences=declarations)["summary"]["supported_joint_options"], 0)

    def test_partial_declared_set_may_satisfy_itself_but_not_whole_template(self):
        inputs, supplier, record = self.ready("doubled")
        _, kernel = self.selected(inputs, record)
        leading = self.roles(record, kernel)["leading_tone"]
        source = next(o["source_sound_ref"] for o in leading["options"] if o["qualified"])
        declarations = [{"role": "leading_tone", "sound_ref": source}]
        result = self.query(inputs, supplier, record, strategy="declared_occurrence_set",
            declared_occurrences=declarations, requested_explanations=[])
        ordinary = result["ordinary_strategy"]
        self.assertIs(ordinary["all_declared_obligations_satisfied"], True)
        self.assertIs(ordinary["required_role_coverage_complete"], False)
        self.assertIs(ordinary["whole_ordinary_template_satisfied"], False)
        self.assertIsNone(ordinary["ordinary_role_existential_satisfied"])
        self.assertIs(ordinary["declared_strategy_satisfied"], True)
        self.assertEqual(ordinary["status"], "conditional_partial_declared_strategy_not_whole_ordinary_template")
        self.assertTrue(any(o["role"] == "seventh" for o in ordinary["unrequested_critical_occurrences"]))
        ledger = result["physical_role_binding_ledger"]
        self.assertTrue(any(o["role"] == "seventh" and o["physical_role_match"] is True
            and o["individually_required"] is False for o in ledger))
        self.assertTrue(any(o["role"] == "leading_tone" and o["physical_role_match"] is True
            and o["source_sound_ref"] != source and o["individually_required"] is False for o in ledger))
        self.assertEqual(sum(o["individually_required"] for o in ledger), 1)
        self.assertEqual(result["finite_clause_coverage"], "explicit_requested_subset")
        self.assertEqual(common.f(result["combined_accounts"][1]["conditional_explanation_note_time"]), 1)

    def test_lazy_compiler_fresh_actual_bundle_and_assessments_are_append_only(self):
        inputs, supplier, record = self.ready()
        before = deepcopy(record)
        result = self.compile(inputs, supplier, record)
        self.assertTrue(result["record_id"].startswith(delayed.COMPILE_PREFIX))
        self.assertEqual(result["summary"]["supported_joint_options"], 1)
        self.assertEqual(result["summary"]["queried_origin_tuples"], 1)
        self.assertEqual(record, before)
        for bundle, assessment in zip(result["bundle_inventory"], result["assessments"]):
            self.assertEqual(assessment["bundle_ref"], common.ref(bundle))
            self.assertIs(assessment["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
            self.assertEqual(bundle["materialized_witness_links"], bundle["required_links"])
            self.assertEqual(bundle["covered_lanes"], sorted([[r["part_id"], r["voice_id"]] for r in inputs[1]["raw_lanes"]]))
            self.assert_accounts(assessment)
        self.assertIs(result["bulk_artifact_mutated"], False)

    def test_lazy_compile_requested_local_clause_shares_one_completion_with_roles(self):
        inputs, supplier, record = self.ready("combined")
        _, kernel = self.selected(inputs, record)
        descriptor = kernel["target_profile_ref"]["record_id"]
        relation = next(r for r in inputs[6]["membership_relation_inventory"] if descriptor in r["descriptor_ids"]
            and r["status"] == "conditional_contour_shape")
        request = {"stage": "local", "geometry_id": relation["geometry_ref"]["record_id"], "side": "right"}
        result = self.compile(inputs, supplier, record, requested_explanations=[request])
        self.assertEqual(result["summary"]["supported_joint_options"], 1)
        assessment = result["assessments"][0]
        self.assert_accounts(assessment)
        self.assertIs(assessment["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        self.assertEqual(common.f(assessment["combined_accounts"][1]["conditional_explanation_note_time"]), Fraction(5, 2))
        self.assertTrue(any(a.get("geometry_id") == request["geometry_id"] and a["status"].startswith("conditional")
                            for a in assessment["explanation_assessments"]))

    def test_competing_minor_bundle_cannot_satisfy_major_ordinary_strategy(self):
        inputs, supplier, record = self.ready("incompatible")
        logical, major = self.selected(inputs, record)
        _, minor = self.selected(inputs, record, quality="m")
        minor_bundle = next(b for b in self.plan(record, minor)["branches"] if b["status"] == "possible")["bundle_ref"]["record_id"]
        result = self.query(inputs, supplier, record, bundle=minor_bundle)
        self.assertIs(result["ordinary_strategy"]["whole_ordinary_template_satisfied"], False)
        self.assertIs(result["ordinary_strategy"]["ordinary_role_existential_satisfied"], False)
        self.assertEqual(self.compile(inputs, supplier, record)["summary"]["supported_joint_options"], 1)

    def test_lazy_joint_and_unique_bundle_caps_are_whole_holds(self):
        inputs, supplier, record = self.ready()
        logical, kernel = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        args = (logical[0], *logical[1], logical[2], kernel["family"], kernel["quality"])
        with patch.object(delayed, "_bundle", side_effect=AssertionError("no partial compiled witness")):
            joint = delayed.compile_joint_prepared(session, *args, max_joint_options=0)
            bundles = delayed.compile_joint_prepared(session, *args, max_new_bundles=0)
        self.assertGreater(joint["summary"]["planned_joint_options"], 0)
        self.assertIsNone(joint["summary"]["supported_joint_options"])
        self.assertEqual(joint["branches"], [])
        self.assertGreater(bundles["summary"]["planned_new_bundles"], 0)
        self.assertIsNone(bundles["summary"]["supported_joint_options"])
        self.assertTrue(bundles["branches"])
        self.assertTrue(all(b["bundle_ref"] is None for b in bundles["branches"]))
        self.assertEqual(bundles["bundle_inventory"], [])

    def test_lazy_zero_work_preserves_profiles_and_unknown_not_false(self):
        inputs, supplier, record = self.ready()
        result = self.compile(inputs, supplier, record, query_work_budget=0)
        self.assertEqual(result["summary"]["supported_joint_options"], 1)
        self.assertEqual(result["summary"]["unknown_bundles"], 0)
        for assessment in result["assessments"]:
            self.assertTrue(all(assessment["profiles"]))
            self.assertIsNone(assessment["combined_accounts"])
            self.assertIsNone(assessment["ordinary_strategy"]["whole_ordinary_template_satisfied"])

    def test_typed_ordered_selectors_and_registered_bundle_required(self):
        inputs, supplier, record = self.ready()
        logical, kernel = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        valid = [logical[0], *logical[1], logical[2], "V7", "M", self.control(record)]
        for position, value in ((0, None), (1, logical[1][1]), (2, logical[1][0]), (3, "foreign"),
            (4, "foreign"), (5, True), (6, None), (6, "foreign")):
            args = list(valid); args[position] = value
            with self.subTest(position=position, value=value), self.assertRaises(ValueError):
                delayed.query_obligations_prepared(session, *args)

    def test_declared_sets_and_optional_requests_are_closed_typed_and_nonduplicated(self):
        inputs, supplier, record = self.ready()
        _, kernel = self.selected(inputs, record)
        source = self.roles(record, kernel)["leading_tone"]["options"][0]["source_sound_ref"]
        declaration = {"role": "leading_tone", "sound_ref": source}
        for declared in (None, [], True, [dict(declaration, confidence=1)], [declaration, declaration],
            [{"role": "foreign", "sound_ref": source}], [{"role": "leading_tone", "sound_ref": "foreign"}]):
            with self.subTest(declared=declared), self.assertRaises(ValueError):
                self.query(inputs, supplier, record, strategy="declared_occurrence_set", declared_occurrences=declared)
        with self.assertRaises(ValueError):
            self.query(inputs, supplier, record, declared_occurrences=[declaration])
        for requested in (True, [{"stage": "local", "geometry_id": "foreign", "side": "right"}],
            [{"stage": "boundary", "geometry_id": "foreign", "side": "right", "confidence": 1}]):
            with self.subTest(requested=requested), self.assertRaises(ValueError):
                self.compile(inputs, supplier, record, requested_explanations=requested)

    def test_query_without_regenerating_profiles_body_or_geometry(self):
        inputs, supplier, record = self.ready()
        logical, _ = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        with patch.object(frozen, "_profile", side_effect=AssertionError("no profile rebuild")), \
            patch.object(delayed.geometry, "query", side_effect=AssertionError("no new geometry")), \
            patch.object(delayed, "_body", side_effect=AssertionError("no bulk rebuild")):
            result = delayed.query_obligations_prepared(session, logical[0], *logical[1], logical[2],
                "V7", "M", self.control(record))
        self.assert_accounts(result)

    def test_query_session_detaches_mutable_callers_and_guards_opaque_authentication(self):
        inputs, supplier, record = self.ready()
        logical, _ = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        args = (logical[0], *logical[1], logical[2], "V7", "M", self.control(record))
        expected = delayed.query_obligations_prepared(session, *args)
        inputs[3]["variant_inventory"].clear(); record["route_inventory"].clear()
        self.assertEqual(delayed.query_obligations_prepared(session, *args), expected)
        with self.assertRaises(ValueError):
            delayed.query_obligations_prepared(delayed._PreparedObligations(), *args)
        state = delayed._SESSIONS[session]
        delayed._SESSIONS[session] = replace(state, lookups=indexed._freeze({}))
        try:
            with self.assertRaises(ValueError):
                delayed.query_obligations_prepared(session, *args)
        finally:
            delayed._SESSIONS[session] = state

    def test_old_direct_equivalence_only_for_genuine_matching_new_route_guards(self):
        inputs, supplier, record = self.ready("direct")
        _, kernel = self.selected(inputs, record)
        self.assertEqual(kernel["old_direct_status"], "conditional_joint_direct_motion_shape")
        self.assertEqual(kernel["status"], "conditional")
        self.assertIs(self.query(inputs, supplier, record)["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        routes = {r["record_id"]: r for r in record["route_inventory"]}
        for role in self.roles(record, kernel).values():
            self.assertTrue(all(routes[o["route_ref"]["record_id"]]["timing"] == "direct_at_cut"
                                for o in role["options"] if o["qualified"]))

    def test_authentic_profile_hold_query_retains_origins_and_none_profiles(self):
        inputs, supplier, record = self.ready("profile_hold")
        logical = self.factory.target_logical((inputs[:2], *inputs[2:5]), "M")
        session = delayed.prepare_obligations_prepared(supplier, record)
        bundles = record["inherited_bundle_inventory"] + record["bundle_inventory"]
        bundle = bundles[0]["record_id"] if bundles else None
        result = delayed.query_obligations_prepared(session, logical[0], *logical[1], logical[2], "V7", "M", bundle)
        self.assertEqual(result["origin_variant_ids"], logical[1])
        self.assertEqual(result["profiles"], [None, None])
        self.assertIsNone(result["combined_accounts"])
        self.assertIsNone(result["planned_query_work_items"])
        self.assertIsNone(result["ordinary_strategy"]["whole_ordinary_template_satisfied"])

    def test_empty_pair_product_is_known_zero_despite_upstream_profile_hold(self):
        inputs, _, record = self.ready("no_pair_profile_hold", **{name: 0 for name in delayed.CAPS})
        self.assertFalse(inputs[5]["summary"]["literal_profiles_complete"])
        for name in ("planned_route_candidates", "planned_obligation_kernels", "planned_role_options",
            "planned_joint_options", "planned_new_bundles"):
            self.assertEqual(record["summary"][name], 0, name)
        self.assertTrue(record["summary"]["ordinary_template_inventory_complete"])

    def test_requested_competing_boundary_clause_does_not_borrow_its_other_hypothesis_witness(self):
        inputs, supplier, record = self.ready("incompatible")
        logical, _ = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        state = delayed._issued(session, delayed._SESSIONS, delayed._PreparedObligations)
        _, origins, *_ = delayed._selection(state, logical[0], *logical[1], logical[2], "V7", "M")
        clauses, *_ = delayed._explanation_clauses(state, logical[0], origins, None)
        geometries = {g["record_id"]: g for g in inputs[7]["geometry_inventory"]}
        sounds = {s["sound_ref"]: s for s in inputs[1]["sound_facts"]}
        bad = next(c for c in clauses if c["stage"] == "boundary" and c["side"] == "right"
            and "boundary_membership_prerequisites_not_met" in c["blockers"]
            and any(sounds[sid]["pitch"]["spelling"] == "E-4"
                for sid in geometries[c["geometry_id"]]["involved_sound_refs"]))
        request = {k: bad[k] for k in ("stage", "geometry_id", "side")}
        result = self.compile(inputs, supplier, record, requested_explanations=[request])
        self.assertEqual(result["summary"]["planned_joint_options"], 0)
        self.assertEqual(result["summary"]["supported_joint_options"], 0)
        self.assertTrue(result["requested_clause_blockers"])
        self.assertEqual(result["bundle_inventory"], [])
        with self.assertRaises(ValueError):
            self.compile(inputs, supplier, record, requested_explanations=[request, request])
        with self.assertRaises(ValueError):
            self.compile(inputs, supplier, record, requested_explanations=[dict(request, side="left")])

    def test_compile_all_boolean_caps_reject_before_session_authentication(self):
        for name in delayed.CAPS:
            for value in (True, False):
                with self.subTest(name=name, value=value), patch.object(delayed, "_issued", side_effect=AssertionError("no session read")), self.assertRaises(ValueError):
                    delayed.compile_joint_prepared(None, None, None, None, None, None, None, **{name: value})
        inputs, supplier, record = self.ready()
        logical, _ = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        for name in ("max_route_candidates", "max_chain_edges", "max_obligation_kernels", "max_role_options"):
            with self.subTest(upstream_cap=name), patch.object(delayed, "_bundle", side_effect=AssertionError("no partial override")):
                result = delayed.compile_joint_prepared(session, logical[0], *logical[1], logical[2], "V7", "M", **{name: 0})
            self.assertIsNone(result["summary"]["supported_joint_options"])
            self.assertEqual(result["bundle_inventory"], [])

    def unit_state(self, inputs, supplier, record):
        """Mutable truth-algebra copy, never issued or an authoritative parent."""
        session = delayed.prepare_obligations_prepared(supplier, record)
        state = delayed._issued(session, delayed._SESSIONS, delayed._PreparedObligations)
        return SimpleNamespace(data=indexed._thaw(state.data), lookups=indexed._thaw(state.lookups))

    def test_kleene_unit_known_route_or_unknown_doubling_remains_true(self):
        inputs, supplier, record = self.ready("doubled")
        _, kernel = self.selected(inputs, record)
        state = self.unit_state(inputs, supplier, record)
        leading = next(r for r in state.data["obligations"]["role_option_inventory"]
            if r["record_id"] == self.roles(record, kernel)["leading_tone"]["record_id"])
        failed_source = next(o["source_sound_ref"] for o in leading["options"] if not o["qualified"])
        unknown = next(o for o in state.data["obligations"]["physical_occurrence_inventory"]
            if o["group_id"] == kernel["group_id"] and o["source_sound_ref"] == failed_source)
        leading["unknown_pitch_occurrence_refs"] = [common.ref(unknown)]
        links = {tuple(e) for b in self.plan(record, kernel)["branches"] for e in b["required_links"]}
        result, choices = delayed._strategy(state, kernel, "ordinary_role_existential", None, links, True)
        assessment = next(a for a in result["role_assessments"] if a["role"] == "leading_tone")
        self.assertIs(assessment["choice_inventory_uncertain"], True)
        self.assertIs(assessment["satisfied"], True)
        self.assertIs(result["whole_ordinary_template_satisfied"], True)
        self.assertTrue(all(choices))

    def test_kleene_unit_false_role_and_unknown_role_is_false(self):
        inputs, supplier, record = self.ready()
        _, kernel = self.selected(inputs, record)
        state = self.unit_state(inputs, supplier, record)
        ids = {ref["record_id"] for ref in kernel["role_option_refs"]}
        for role in state.data["obligations"]["role_option_inventory"]:
            if role["record_id"] not in ids:
                continue
            for option in role["options"]:
                option["qualified"] = False
                option["blockers"] = ["ordinary_leading_tone_strategy_motion_not_matched"] if role["role"] == "leading_tone" else ["source_clock_passed_not_passed"]
        result, _ = delayed._strategy(state, kernel, "ordinary_role_existential", None, set(), True)
        self.assertEqual({a["role"]: a["satisfied"] for a in result["role_assessments"]},
            {"leading_tone": False, "seventh": None})
        self.assertIs(result["whole_ordinary_template_satisfied"], False)

    def test_impossible_all_lane_bundle_cannot_leak_surviving_lane_positive_role(self):
        inputs, supplier, record = self.ready("incompatible")
        logical, major = self.selected(inputs, record)
        _, minor = self.selected(inputs, record, quality="m")
        required = tuple(sorted({tuple(e) for k in (major, minor) for b in self.plan(record, k)["branches"]
            if b["status"] == "possible" for e in b["required_links"]}))
        impossible = delayed._bundle({"scope": inputs[1], "index": inputs[3], "grounding": inputs[5]},
            record["logical_universe"], required, 100000)
        self.assertEqual(impossible["geometry_condition_status"], "impossible")
        self.assertTrue(any(e["witness"] is not None for e in impossible["entries"]))
        session = delayed.prepare_obligations_prepared(supplier, record)
        state = delayed._issued(session, delayed._SESSIONS, delayed._PreparedObligations)
        result = delayed._query(state, logical[0], *logical[1], logical[2], "V7", "M", impossible)
        self.assertIs(result["completion_certified_impossible"], True)
        self.assertIs(result["ordinary_strategy"]["whole_ordinary_template_satisfied"], False)
        self.assertIs(result["ordinary_strategy"]["ordinary_role_existential_satisfied"], False)
        self.assertEqual(result["ordinary_strategy"]["known_matched_route_refs"], [])
        self.assertTrue(all(a["satisfied"] is not True for a in result["ordinary_strategy"]["role_assessments"]))

    def test_requested_clause_unit_unknown_plan_vs_known_false_and_unknown_zero(self):
        inputs, supplier, record = self.ready()
        logical, _ = self.selected(inputs, record)
        session = delayed.prepare_obligations_prepared(supplier, record)
        state = delayed._issued(session, delayed._SESSIONS, delayed._PreparedObligations)
        _, origins, *_ = delayed._selection(state, logical[0], *logical[1], logical[2], "V7", "M")
        _, descriptors, sounds, _ = delayed._explanation_clauses(state, logical[0], origins, None)
        # Isolate the three-valued clause-count composition; actual parent and
        # issued session remain untouched, and these are not saved artifacts.
        unknown = {"stage": "boundary", "geometry_id": "unit_unknown_clause", "side": "right",
            "qualified": False, "blockers": ["source_clock_passed_not_passed"], "required_links": [], "explained_items": []}
        false = dict(unknown, geometry_id="unit_false_clause", blockers=["boundary_membership_prerequisites_not_met"])
        self.assertIsNone(delayed._clause_truth(unknown))
        self.assertIs(delayed._clause_truth(false), False)
        mixed = dict(unknown, blockers=unknown["blockers"] + false["blockers"])
        self.assertIs(delayed._clause_truth(mixed), False)
        for clauses, expected in (([unknown], None), ([unknown, false], 0)):
            with self.subTest(expected=expected), patch.object(delayed, "_explanation_clauses",
                return_value=(clauses, descriptors, sounds, len(clauses))):
                result = delayed.compile_joint_prepared(session, logical[0], *logical[1], logical[2], "V7", "M")
            self.assertEqual(result["summary"]["planned_joint_options"], expected)
            self.assertEqual(result["summary"]["supported_joint_options"], expected)
            self.assertEqual(result["bundle_inventory"], [])

    def test_genuine_omitted_full_ir_source_keeps_physical_and_route_totals_unknown(self):
        from test_factor_expanded_scope import FactorExpandedScopeTests
        parents = FactorExpandedScopeTests.fixture(self.factory,
            [[event("C4", 0, 1, tie_role="start"), event("C4", 11, 1, tie_role="stop"),
              event("D4", 5, 1), event(None, 6, 4)]], extent=span(5, 6),
            clocks=[(0, 4), (4, 4), (8, 4)], pre_measures=0, post_measures=0)
        ready_graph_scope = expanded.prepare_scope(*parents)
        ready_graph_hypotheses = frozen.build_hypotheses(parents[0], ready_graph_scope, path_budget=1)
        ready_graph_index = indexed.build_index(parents[0], ready_graph_scope, ready_graph_hypotheses)
        # Phase18 correctly refuses to emit a parent when its graph references
        # an omitted snapshot. Exercise NEW neutral routing on that authentic
        # scope directly, then emit a real held-graph parent below.
        _, routes, planned, _, _, held = delayed._routes(ready_graph_scope,
            boundary._pair_groups(ready_graph_index), delayed.DEFAULTS)
        self.assertEqual(routes, [])
        self.assertIsNone(planned)
        self.assertTrue(held)
        scope = expanded.prepare_scope(*parents, max_events=0)
        self.assertFalse(scope["context_sound_inventory_complete"])
        self.assertTrue(expanded.check_scope(scope, ir=parents[0]))
        hypotheses = frozen.build_hypotheses(parents[0], scope, path_budget=1)
        index = indexed.build_index(parents[0], scope, hypotheses)
        shape = relations.build_relations(parents[0], scope, hypotheses, index)
        case = (parents[0], scope, hypotheses, index, shape)
        grounding = grounded.build_grounding(*case)
        local = temporal.build_explanations(*case, grounding)
        border = boundary.build_explanations(*case, grounding, local)
        record = delayed.build_obligations(*case, grounding, local, border)
        self.assertGreater(record["summary"]["touching_pair_groups"], 0)
        self.assertIsNone(record["summary"]["planned_physical_occurrences"])
        self.assertIsNone(record["summary"]["planned_route_candidates"])
        self.assertEqual(record["summary"]["known_physical_occurrence_subtotal"],
            len(record["physical_occurrence_inventory"]))
        self.assertGreater(record["summary"]["known_physical_occurrence_subtotal"], 0)
        self.assertEqual(record["route_inventory"], [])
        self.assertFalse(record["summary"]["route_inventory_complete"])
        self.assertEqual(record["origin_inventory"], grounding["origin_inventory"])
        _, _, planned, known, _, held = delayed._routes(scope, [], delayed.DEFAULTS)
        self.assertEqual(planned, 0)
        self.assertEqual(known, 0)
        self.assertFalse(held)

    def test_valid_source_with_index_cap_zero_keeps_physical_counts_known(self):
        inputs, _, record = self.ready("index_hold")
        self.assertTrue(inputs[1]["context_sound_inventory_complete"])
        self.assertEqual(inputs[3]["status"], "whole_index_budget_hold")
        self.assertGreater(record["summary"]["touching_pair_groups"], 0)
        self.assertGreater(record["summary"]["planned_physical_occurrences"], 0)
        self.assertGreater(record["summary"]["planned_route_candidates"], 0)
        self.assertEqual(record["summary"]["planned_physical_occurrences"],
            record["summary"]["known_physical_occurrence_subtotal"])
        self.assertTrue(record["summary"]["route_inventory_complete"])
        self.assertIsNone(record["summary"]["planned_obligation_kernels"])


if __name__ == "__main__":
    unittest.main()
