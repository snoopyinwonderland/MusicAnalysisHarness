"""Exact same-witness context joins, never inferred harmony or cadence.

Prior comparison/delayed fixture methods are composed, not inherited: no prior
test methods are silently counted as phase21 tests.  Tests named ``pure_`` use
unregistered helper inputs and do not claim public SOURCE or bundle authority.
"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_progression_context as context
from musicanote_harness import factor_progression_evidence as comparison
from musicanote_harness import factor_delayed_obligations as delayed
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_view as common
import test_factor_delayed_obligations as delayed_fixtures
import test_factor_progression_evidence as comparison_fixtures
from test_factor_musical_view import reseal


class ProgressionContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = comparison_fixtures.ProgressionEvidenceTests()
        cls.helper.helper = delayed_fixtures.DelayedTests()
        cls.helper.helper.factory = delayed_fixtures.TemporalExplanationFixture()
        cls.helper.helper.factory.addCleanup = cls.addClassCleanup
        cls.helper.helper.factory.setUp()
        cls.helper.helper.raw_cache, cls.helper.helper.ready_cache = {}, {}
        cls.helper.sessions = {}
        cls.prepared = {}

    def ready(self, name="held", *, control=False, selectors=None, **parent_caps):
        if name == "parallel_tonic" and name not in self.helper.helper.raw_cache:
            # Same literal G7 -> C-major pitch inventory, but an explicitly
            # registered C-minor candidate is supplied by a minor signature.
            # This is genuinely compiled through the parent chain, not a
            # re-sealed key or a pure helper pretending to be SOURCE authority.
            event = delayed_fixtures.event
            case = self.helper.helper.factory.frozen_case(self.helper.helper.factory.make([
                [event("B4", 0, 3), event("C5", 3, 1)],
                [event("F4", 0, 3), event("E4", 3, 1)],
                [event("G3", 0, 2), event("C3", 2, 2)],
                [event("D4", 0, 2), event("G4", 2, 2)]],
                signatures=[{"fifths": -3, "mode_hint": "minor"}]))
            flat = (*case[0], *case[1:])
            grounding = delayed_fixtures.grounded.build_grounding(*flat)
            parents = (*flat, grounding)
            local = delayed_fixtures.temporal.build_explanations(*parents)
            boundary_inputs = (*parents, local)
            supplier = delayed_fixtures.boundary.prepare_inputs(*boundary_inputs)
            border = delayed_fixtures.boundary.build_explanations_prepared(supplier)
            self.helper.helper.raw_cache[name] = (*boundary_inputs, border)
        inputs, supplier, record, parent, session = self.helper.ready(name)
        if selectors is None:
            if name in ("no_pair", "profile_hold", "no_pair_profile_hold"):
                selectors = [self.helper.fullhold(inputs)]
                bundles = record["inherited_bundle_inventory"] + record["bundle_inventory"]
                bundle_id = bundles[0]["record_id"] if bundles else None
            else:
                candidate, kernel = self.helper.selector(inputs, record)
                selectors = [candidate, self.helper.fullhold(inputs)]
                bundle_id = (self.helper.helper.control(record) if control else
                             self.helper.bundle(record, kernel))
        else:
            _, kernel = self.helper.selector(inputs, record)
            bundle_id = self.helper.helper.control(record) if control else self.helper.bundle(record, kernel)
        joined_parent = comparison.compare_prepared(session, selectors, bundle_id, **parent_caps)
        signature = (id(session), common.digest(joined_parent), common.digest(context._contract()))
        if signature not in self.prepared:
            self.prepared[signature] = context.prepare_context_prepared(session, joined_parent)
        return inputs, record, session, joined_parent, self.prepared[signature]

    def build(self, name="held", *, control=False, selectors=None, **caps):
        inputs, record, old_session, parent, session = self.ready(name, control=control, selectors=selectors)
        return inputs, parent, context.build_context_prepared(session, **caps)

    def test_preparation_requires_authentic_comparison_session_and_exact_record(self):
        _, _, session, parent, _ = self.ready()
        for fake in (None, True, object(), comparison._PreparedComparison()):
            with self.subTest(fake=type(fake).__name__), self.assertRaises(ValueError):
                context.prepare_context_prepared(fake, parent)
        changed = deepcopy(parent)
        changed["hypotheses"][0]["whole_path_account"]["total_note_time"] = common.q(1)
        with self.assertRaises(ValueError):
            context.prepare_context_prepared(session, reseal(changed, comparison.PREFIX))

    def test_resealed_comparison_semantic_promotions_cannot_grant_authority(self):
        _, _, session, parent, _ = self.ready()
        for mutate in (lambda r: r.update(selected=0),
                       lambda r: r["flags"].update(final_key_confirmed=True),
                       lambda r: r["hypotheses"].pop(),
                       lambda r: r["hypotheses"][0]["function_shapes"][0]["function"].update(function_confirmed=True),
                       lambda r: r.update(bundle_ref={"record_id": "foreign", "record_sha256": "a" * 64})):
            changed = deepcopy(parent)
            mutate(changed)
            with self.subTest(changed=common.digest(changed)), self.assertRaises(ValueError):
                context.prepare_context_prepared(session, reseal(changed, comparison.PREFIX))

    def test_foreign_same_type_comparison_record_is_not_rebound(self):
        _, _, held_session, _, _ = self.ready()
        _, _, _, direct_parent, _ = self.ready("direct")
        with self.assertRaises(ValueError):
            context.prepare_context_prepared(held_session, direct_parent)

    def test_closed_integer_cap_types_rejected_before_parent_work(self):
        names = ("max_hypotheses", "max_boundary_observations", "max_transition_pairs", "query_work_budget")
        for name in names:
            for bad in (True, False, -1, 1.0, "1", None):
                with self.subTest(name=name, value=bad), self.assertRaises(ValueError):
                    context.build_context_prepared(None, **{name: bad})
        with self.assertRaises(TypeError):
            context.build_context_prepared(None, undeclared_limit=1)

    def test_raw_caps_rejected_before_expensive_preparation(self):
        with patch.object(context, "prepare_context", side_effect=AssertionError("caps must precede cold parents")):
            for bad in (True, -1, 1.0, "0", None):
                with self.subTest(value=bad), self.assertRaises(ValueError):
                    context.build_context(*([None] * 10), query_work_budget=bad)

    def test_current_contract_change_invalidates_owned_preparation(self):
        _, _, _, _, session = self.ready()
        original = Path.read_bytes
        def changed(path):
            return original(path) + b"\n" if path == Path(context.__file__) else original(path)
        with patch.object(Path, "read_bytes", changed), self.assertRaises(ValueError):
            context.build_context_prepared(session)

    def test_owned_context_HMAC_replacement_cannot_grant_authority(self):
        _, _, _, _, session = self.ready()
        original = context._SESSIONS[session]
        try:
            context._SESSIONS[session] = replace(original, authentication=b"\0" * 32)
            with self.assertRaises(ValueError):
                context.build_context_prepared(session)
        finally:
            context._SESSIONS[session] = original

    def test_authenticated_upstream_state_replacement_breaks_exact_owned_identity(self):
        _, _, upstream, _, session = self.ready()
        original = comparison._SESSIONS[upstream]
        replacement = replace(original, authentication=b"")
        object.__setattr__(replacement, "authentication", comparison._auth(upstream, replacement))
        try:
            comparison._SESSIONS[upstream] = replacement
            with self.assertRaises(ValueError):
                context.build_context_prepared(session)
        finally:
            comparison._SESSIONS[upstream] = original

    def test_fresh_raw_public_reconstruction_and_validation_match_owned_join(self):
        # Synthetic MusicXML parents, not a corpus cold-load or a fabricated
        # compare record.  Public preparation genuinely replays all parents.
        inputs, record, _, parent, session = self.ready()
        expected = context.build_context_prepared(session)
        fresh = context.build_context(*inputs, record, parent)
        self.assertEqual(fresh, expected)
        self.assertIs(context.validate_context(*inputs, record, parent, fresh), True)

    def test_fresh_public_validator_rejects_resealed_context_semantic_promotion(self):
        inputs, record, _, parent, session = self.ready()
        result = context.build_context_prepared(session)
        result["paths"][0]["function_context"]["secondary_function_confirmed"] = True
        result["paths"][0]["function_context"] = reseal(result["paths"][0]["function_context"], context.FUNCTION_PREFIX)
        result["paths"][0] = reseal(result["paths"][0], context.PATH_PREFIX)
        promoted = reseal(result, context.PREFIX)
        with self.assertRaises(ValueError):
            context.validate_context(*inputs, record, parent, promoted)

    def test_build_is_reproducible_without_mutating_any_exact_parent(self):
        inputs, record, old_session, parent, session = self.ready()
        before = deepcopy((inputs, record, parent))
        first = context.build_context_prepared(session)
        self.assertEqual(context.build_context_prepared(session), first)
        self.assertEqual((inputs, record, parent), before)
        self.assertTrue(first["record_id"].startswith(context.PREFIX))
        self.assertEqual(first["version"], context.VERSION)

    def test_prepared_build_does_not_recompile_or_requery_old_progression(self):
        _, _, _, _, session = self.ready()
        with patch.object(comparison, "compare_prepared", side_effect=AssertionError("no old comparison replay in build")), \
                patch.object(frozen, "_profile", side_effect=AssertionError("no old membership reconstruction")), \
                patch.object(delayed, "_query", side_effect=AssertionError("no new ordinary or NCT inference")):
            result = context.build_context_prepared(session)
        self.assertTrue(result["record_id"].startswith(context.PREFIX))

    def test_output_mutation_cannot_change_parent_or_another_return(self):
        _, _, _, parent, session = self.ready()
        before = deepcopy(parent)
        first = context.build_context_prepared(session)
        expected = deepcopy(first)
        first["version"] = "caller_mutation"
        first["flags"]["cadence_confirmed"] = True
        self.assertEqual(parent, before)
        self.assertEqual(context.build_context_prepared(session), expected)

    def test_parent_caller_mutation_after_preparation_does_not_rebind_owned_record(self):
        inputs, record, _, parent, session = self.ready()
        expected = context.build_context_prepared(session)
        before_variants = deepcopy(inputs[3]["variant_inventory"])
        before_origins = deepcopy(record["origin_inventory"])
        try:
            parent["hypotheses"].clear()
            inputs[3]["variant_inventory"].clear()
            record["origin_inventory"].clear()
            self.assertEqual(context.build_context_prepared(session), expected)
        finally:
            inputs[3]["variant_inventory"][:] = before_variants
            record["origin_inventory"][:] = before_origins

    def test_no_selected_key_function_cadence_rank_confidence_or_training(self):
        _, _, result = self.build()
        for flag, value in result["flags"].items():
            self.assertIs(value, False, flag)
        for field in ("selected", "winner", "preferred", "rank", "confidence"):
            self.assertIsNone(result.get(field), field)

    def test_exact_original_tuple_key_origin_profile_and_bundle_join(self):
        inputs, parent, result = self.build()
        self.assertEqual(result["comparison_ref"], common.ref(parent))
        self.assertEqual(result["scope_ref"], common.ref(inputs[1]))
        self.assertEqual(result["index_ref"], common.ref(inputs[3]))
        self.assertEqual(result["analysis_span"], parent["analysis_span"])
        self.assertEqual(result["binding"], parent["binding"])
        self.assertEqual(result["logical_universe"], parent["logical_universe"])
        self.assertEqual(result["bundle_ref"], parent["bundle_ref"])
        self.assertEqual(result["selector_inventory"], parent["selector_inventory"])
        self.assertEqual(len(result["paths"]), len(parent["hypotheses"]))
        for path, old in zip(result["paths"], parent["hypotheses"]):
            self.assertEqual(path["progression_path_ref"], common.ref(old))
            for field in ("logical_tuple", "group_id", "indexed_group_id", "partition",
                          "origin_variant_ids", "origin_refs", "profile_refs", "key_ref", "bundle_ref"):
                self.assertEqual(path[field], old[field], field)

    def test_original_complete_function_inventory_and_terminal_complement_are_unchanged(self):
        _, parent, result = self.build()
        for path, old in zip(result["paths"], parent["hypotheses"]):
            self.assertEqual(path["function_shapes"], old["function_shapes"])
            terminal = [row for row in path["function_shapes"]
                        if row["slot"] == len(path["origin_variant_ids"]) - 1]
            self.assertEqual(len(terminal), len(frozen.FAMILIES) * 2)
            self.assertTrue(all(row["motion_assessed"] is False for row in terminal))
            self.assertTrue(all("following_target_segment_not_observed" in row["function"]["blockers"]
                                for row in terminal))

    def test_parent_account_is_referenced_without_recrediting_or_changing_raw_time(self):
        _, parent, result = self.build("combined")
        for path, old in zip(result["paths"], parent["hypotheses"]):
            self.assertEqual(path["whole_path_account_ref"], {
                "progression_path_ref": common.ref(old),
                "json_pointer": "/whole_path_account",
                "value_sha256": common.digest(old["whole_path_account"])})
            for field in ("total_note_time", "raw_note_time", "note_time", "conditional_explanation_note_time"):
                self.assertEqual(path["raw_time_snapshot"][field], old["whole_path_account"][field])
            self.assertEqual(path["bundle_ref"], parent["bundle_ref"])
            if old["transition_assessment"] is not None:
                self.assertEqual(path["function_context"]["ordinary_strategy"],
                                 old["transition_assessment"]["ordinary_strategy"])
                self.assertEqual(path["function_context"]["prerequisite_axes"]["literal_core_and_time_audit"],
                                 old["transition_assessment"]["literal_core_and_time_audit"])
        self.assertTrue(all(value is False for value in result["flags"].values()))

    def test_all_start_cut_endpoint_boundaries_are_preserved_without_new_partition(self):
        _, parent, result = self.build()
        inventory = {row["record_id"]: row for row in result["literal_boundary_inventory"]}
        for path, old in zip(result["paths"], parent["hypotheses"]):
            times = sorted({common.f(span[field]) for span in old["partition"] for field in ("start", "end")})
            self.assertEqual([common.f(row["boundary_time"]) for row in path["boundaries"]], times)
            self.assertEqual(path["partition"], old["partition"])
            for row in path["boundaries"]:
                literal = inventory[row["literal_boundary_ref"]["record_id"]]
                self.assertEqual(row["literal_boundary_ref"], common.ref(literal))
                self.assertEqual(row["boundary_time"], literal["boundary_time"])

    def test_held_same_sound_is_carry_not_reattack_or_fabricated_self_link(self):
        _, _, result = self.build()
        path = result["paths"][0]
        cut = next(row for row in path["boundaries"] if common.f(row["boundary_time"]) == 2)
        carries = [row for row in cut["same_raw_lane_transitions"] if row["same_sound_carry"]]
        self.assertTrue(carries)
        for row in carries:
            self.assertEqual(row["required_links"], [])
            self.assertEqual(row["source_sound_ref"], row["arrival_sound_ref"])
            self.assertIs(row["true_voice_identity_confirmed"], False)

    def test_direct_actual_extreme_link_uses_only_one_registered_bundle(self):
        _, _, result = self.build("direct")
        cut = next(row for row in result["paths"][0]["boundaries"] if common.f(row["boundary_time"]) == 2)
        paired = [row for row in cut["same_raw_lane_transitions"] if not row["same_sound_carry"]]
        self.assertTrue(paired)
        satisfied = [row for row in paired if row["status"] == "required_link_satisfied_under_this_same_bundle"]
        self.assertTrue(satisfied)
        for row in paired:
            self.assertEqual(row["required_links"], [[row["source_sound_ref"], row["arrival_sound_ref"]]])
            self.assertIs(row["absence_is_global"], False)
            self.assertIs(row["structural_motion_confirmed"], False)

    def test_no_link_control_does_not_borrow_a_supporting_ordinary_completion(self):
        _, parent, result = self.build("direct", control=True)
        self.assertEqual(result["bundle_ref"], parent["bundle_ref"])
        cut = next(row for row in result["paths"][0]["boundaries"] if common.f(row["boundary_time"]) == 2)
        pairs = [row for row in cut["same_raw_lane_transitions"] if not row["same_sound_carry"]]
        self.assertTrue(pairs)
        self.assertFalse(any(row["status"] == "required_link_satisfied_under_this_same_bundle" for row in pairs))
        self.assertIs(parent["hypotheses"][0]["transition_assessment"]["ordinary_strategy"]["whole_ordinary_template_satisfied"], False)

    def test_unknown_key_preserves_factors_terminal_and_motion_without_tonal_promotion(self):
        inputs, _, _, _, _ = self.ready("key")
        unknown = next(k["record_id"] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "unknown")
        _, _, record, _, _ = self.helper.ready("key")
        pair, _ = self.helper.selector(inputs, record, key_id=unknown)
        inputs, parent, result = self.build("key", selectors=[pair, self.helper.fullhold(inputs, key_id=unknown)])
        for path in result["paths"]:
            self.assertEqual(path["key_ref"]["record_id"], unknown)
            for row in path["function_shapes"]:
                self.assertEqual(row["function"]["function_kind"], "unassessed")
            for boundary in path["boundaries"]:
                for inventory in ("before_extremes", "arrival_extremes"):
                    for row in boundary[inventory]["rows"]:
                        self.assertIsNone(row["candidate_scale_degree"]["coordinate"])
                        self.assertTrue(row["candidate_factor"])
                        self.assertTrue(row["terminal_probe"])
        conditional = result["paths"][0]["function_context"]
        self.assertIs(conditional["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        self.assertIsNone(conditional["joint_conditional_functional_evidence"])
        self.assertIsNone(conditional["prerequisite_axes"]["known_explicit_key_coordinate"])
        self.assertIs(conditional["secondary_function_confirmed"], False)
        self.assertIs(result["paths"][0]["key_context"]["key_confirmed"], False)

    def test_explicit_primary_and_applied_keys_are_competing_coordinates_not_inferred_keys(self):
        inputs, _, record, _, _ = self.helper.ready("key")
        major = next(k["record_id"] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "major")
        minor = next(k["record_id"] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "minor")
        primary, _ = self.helper.selector(inputs, record, key_id=major)
        applied = deepcopy(primary)
        applied["key_id"] = minor
        _, parent, result = self.build("key", selectors=[primary, applied])
        projected = [next(row["function"]["function_kind"] for row in path["function_shapes"]
                          if row["explicit_transition_assumption"]) for path in result["paths"]]
        self.assertEqual(projected, ["primary", "applied"])
        self.assertEqual(result["paths"][0]["raw_time_snapshot"], result["paths"][1]["raw_time_snapshot"])
        self.assertEqual(result["paths"][0]["bundle_ref"], result["paths"][1]["bundle_ref"])
        self.assertIsNone(result["selected"])
        for path, old in zip(result["paths"], parent["hypotheses"]):
            joined = path["function_context"]
            self.assertIs(joined["joint_conditional_functional_evidence"], True)
            for name in ("source_shape_compatible", "target_triad_core_shape_compatible",
                         "function_shape_prerequisites_available", "known_explicit_key_coordinate",
                         "same_registered_complete_all_raw_lane_bundle", "guarded_pooled_literal_core_present",
                         "observed_lowest_source_guards_passed", "actual_ordinary_role_rows_available",
                         "whole_explicit_ordinary_template_satisfied"):
                self.assertIs(joined["prerequisite_axes"][name], True, name)
            self.assertEqual(joined["ordinary_strategy"], old["transition_assessment"]["ordinary_strategy"])
            self.assertEqual(joined["prerequisite_axes"]["literal_core_and_time_audit"],
                             old["transition_assessment"]["literal_core_and_time_audit"])
            for name in ("secondary_function_confirmed", "tonicization_confirmed", "modulation_confirmed", "cadence_confirmed"):
                self.assertIs(joined[name], False)

    def test_signature_candidate_provenance_is_retained_but_not_key_proof(self):
        inputs, _, record, _, _ = self.helper.ready("key")
        known = next(k["record_id"] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "major")
        unknown = next(k["record_id"] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "unknown")
        pair, _ = self.helper.selector(inputs, record, key_id=known)
        counterpart = deepcopy(pair)
        counterpart["key_id"] = unknown
        _, _, result = self.build("key", selectors=[pair, counterpart])
        projections = [p["key_context"] for p in result["paths"]]
        original_keys = {k["record_id"]: k for k in inputs[2]["keys"]}
        # An unknown tonal coordinate remains a signature-derived *candidate
        # alternative* here.  Unknown does not erase source provenance.
        for projected, key_id in zip(projections, (known, unknown)):
            original = original_keys[key_id]
            self.assertEqual(projected["registered_key_ref"], common.ref(original))
            self.assertEqual(projected["provenance"], original["provenance"])
            self.assertEqual(projected["signature_declarations"], original["declarations"])
            self.assertEqual(projected["signature_used_for_candidate_universe"],
                             original["provenance"]["kind"] == "literal_IR_measure_key_signature_interpretation")
        self.assertEqual([p["key_coordinate_prerequisites_available"] for p in projections], [True, False])
        for projected in projections:
            self.assertIs(projected["signature_is_not_key_proof"], True)
            self.assertIs(projected["key_confirmed"], False)

    def test_same_bundle_control_withholds_new_joint_function_without_global_music_verdict(self):
        inputs, _, record, _, _ = self.helper.ready("key")
        major = next(k["record_id"] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "major")
        pair, _ = self.helper.selector(inputs, record, key_id=major)
        _, parent, result = self.build("key", control=True, selectors=[pair])
        joined = result["paths"][0]["function_context"]
        self.assertIs(joined["joint_conditional_functional_evidence"], False)
        self.assertIs(joined["prerequisite_axes"]["known_explicit_key_coordinate"], True)
        self.assertIs(joined["prerequisite_axes"]["whole_explicit_ordinary_template_satisfied"], False)
        self.assertEqual(joined["bundle_ref"], parent["bundle_ref"])
        self.assertEqual(joined["ordinary_strategy"], parent["hypotheses"][0]["transition_assessment"]["ordinary_strategy"])
        self.assertEqual(joined["status"], "withheld_joint_functional_prerequisites_not_music_error")

    def test_known_key_wrong_shape_cannot_recover_joint_function_from_extremes(self):
        inputs, _, record, _, _ = self.helper.ready("key")
        major = next(k["record_id"] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "major")
        pair, _ = self.helper.selector(inputs, record, key_id=major)
        wrong = deepcopy(pair)
        wrong["transition"]["family"] = "V"
        _, _, result = self.build("key", selectors=[pair, wrong])
        joined = result["paths"][1]["function_context"]
        self.assertIs(joined["joint_conditional_functional_evidence"], False)
        self.assertIs(joined["prerequisite_axes"]["known_explicit_key_coordinate"], True)
        self.assertIs(joined["prerequisite_axes"]["source_shape_compatible"], False)
        self.assertIn("source_ordinary_family_shape_mismatch", joined["function_shape_blockers"])

    def test_partial_ordinary_role_strategy_cannot_become_whole_joint_function(self):
        inputs, _, record, _, _ = self.helper.ready("doubled")
        existential, kernel = self.helper.selector(inputs, record)
        role = self.helper.helper.roles(record, kernel)["leading_tone"]
        sound = next(option["source_sound_ref"] for option in role["options"] if option["qualified"])
        partial = deepcopy(existential)
        partial["transition"].update(strategy="declared_occurrence_set",
            declared_occurrences=[{"role": "leading_tone", "sound_ref": sound}])
        _, parent, result = self.build("doubled", selectors=[existential, partial])
        joined = result["paths"][1]["function_context"]
        self.assertEqual(joined["ordinary_strategy"], parent["hypotheses"][1]["transition_assessment"]["ordinary_strategy"])
        self.assertIs(joined["ordinary_strategy"]["declared_strategy_satisfied"], True)
        self.assertIs(joined["ordinary_strategy"]["required_role_coverage_complete"], False)
        self.assertIs(joined["prerequisite_axes"]["whole_explicit_ordinary_template_satisfied"], False)
        self.assertIs(joined["joint_conditional_functional_evidence"], False)

    def test_wrong_family_and_missing_target_are_not_filled_from_expected_chord(self):
        inputs, _, record, _, _ = self.helper.ready()
        pair, _ = self.helper.selector(inputs, record)
        wrong = deepcopy(pair)
        wrong["transition"]["family"] = "V"
        _, parent, result = self.build(selectors=[pair, wrong])
        wrong_path = result["paths"][1]
        explicit = next(row for row in wrong_path["function_shapes"] if row["explicit_transition_assumption"])
        self.assertFalse(explicit["motion_assessed"])
        self.assertIn("source_ordinary_family_shape_mismatch", explicit["function"]["blockers"])
        self.assertEqual(wrong_path["function_shapes"], parent["hypotheses"][1]["function_shapes"])

    def test_fullhold_without_pair_does_not_create_function_motion_or_new_cut(self):
        _, parent, result = self.build("no_pair")
        self.assertEqual(len(result["paths"]), 1)
        path = result["paths"][0]
        self.assertEqual(len(path["partition"]), 1)
        self.assertEqual([common.f(row["boundary_time"]) for row in path["boundaries"]], [0, 4])
        self.assertFalse(any(row["motion_assessed"] for row in path["function_shapes"]))
        self.assertEqual(path["function_shapes"], parent["hypotheses"][0]["function_shapes"])

    def test_every_cadence_is_missing_semantic_premises_not_a_geometry_verdict(self):
        _, _, result = self.build("direct")
        for path in result["paths"]:
            for boundary in path["boundaries"]:
                for name in ("PAC", "HC", "IAC"):
                    row = boundary["cadence_prerequisites"][name]
                    self.assertIs(row["confirmed"], False)
                    self.assertTrue(row["missing_premises"])
                for inventory in ("before_extremes", "arrival_extremes"):
                    self.assertEqual(boundary[inventory]["structural_bass"], "unassessed")
                    self.assertEqual(boundary[inventory]["structural_melody"], "unassessed")

    def test_analysis_start_dominant_is_not_an_ending_or_nominal_HC(self):
        _, _, result = self.build("direct")
        first = result["paths"][0]["boundaries"][0]
        self.assertEqual(first["boundary_role"], "analysis_start")
        for kind in ("PAC", "IAC", "HC"):
            axes = first["cadence_prerequisites"][kind]["literal_prerequisite_axes"]
            self.assertIsNone(axes["candidate_ending_root_coordinate"])
            self.assertIsNone(first["cadence_prerequisites"][kind]["nominal_harmonic_and_literal_extreme_prerequisites"])
            self.assertIs(first["cadence_prerequisites"][kind]["confirmed"], False)

    def test_parallel_major_tonic_under_minor_key_does_not_fill_home_cadence_quality(self):
        self.ready("parallel_tonic")
        # Retrieve the original delayed record for exact selector identity.
        inputs, _, delayed_record, _, _ = self.helper.ready("parallel_tonic")
        key = next(k["record_id"] for k in inputs[2]["keys"]
            if k["segments"][0]["mode"] == "minor" and k["segments"][0]["tonic"]["step"] == "C")
        pair, _ = self.helper.selector(inputs, delayed_record, key_id=key)
        _, _, result = self.build("parallel_tonic", selectors=[pair])
        internal = next(b for b in result["paths"][0]["boundaries"] if b["boundary_role"] == "internal_declared_transition")
        for kind in ("PAC", "IAC"):
            row = internal["cadence_prerequisites"][kind]
            self.assertIs(row["literal_prerequisite_axes"]["home_tonic_target_coordinate"], True)
            self.assertIs(row["literal_prerequisite_axes"]["home_tonic_target_quality"], False)
            self.assertIs(row["nominal_harmonic_and_literal_extreme_prerequisites"], False)
            self.assertIs(row["confirmed"], False)

    def test_whole_hypothesis_budget_does_not_keep_favorable_prefix(self):
        _, parent, result = self.build(max_hypotheses=1)
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["literal_boundary_inventory"], [])
        self.assertEqual(result["selector_inventory"], parent["selector_inventory"])
        self.assertEqual(result["logical_universe"], parent["logical_universe"])
        self.assertTrue(result["reasons"])

    def test_whole_boundary_budget_does_not_keep_first_or_supported_boundary(self):
        _, parent, result = self.build(max_boundary_observations=0)
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["literal_boundary_inventory"], [])
        self.assertEqual(result["selector_inventory"], parent["selector_inventory"])
        self.assertTrue(result["reasons"])

    def test_whole_transition_pair_budget_does_not_keep_easy_lane(self):
        _, parent, result = self.build(max_transition_pairs=0)
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["literal_boundary_inventory"], [])
        self.assertEqual(result["selector_inventory"], parent["selector_inventory"])
        self.assertTrue(result["reasons"])

    def test_zero_work_is_unassessed_whole_request_not_known_failed_music(self):
        _, parent, result = self.build(query_work_budget=0)
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["literal_boundary_inventory"], [])
        self.assertEqual(result["selector_inventory"], parent["selector_inventory"])
        self.assertTrue(result["reasons"])
        self.assertTrue(all(value is False for value in result["flags"].values()))

    def test_parent_profile_hold_does_not_invent_context_path_or_known_success(self):
        inputs, parent, result = self.build("profile_hold")
        self.assertEqual(parent["hypotheses"], [])
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["selector_inventory"], parent["selector_inventory"])
        self.assertIsNone(parent["summary"]["planned_query_work_items"])
        self.assertIsNone(result["summary"]["planned_query_work_items"])
        self.assertIsNone(result["summary"]["planned_transition_pairs"])
        self.assertEqual(result["summary"]["observed_transition_pairs"], 0)
        self.assertTrue(result["reasons"])

    def test_empty_authentic_parent_request_with_zero_caps_is_known_zero(self):
        _, _, _, parent, session = self.ready(selectors=[])
        self.assertEqual(parent["hypotheses"], [])
        result = context.build_context_prepared(session, max_hypotheses=0,
            max_boundary_observations=0, max_transition_pairs=0, query_work_budget=0)
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["literal_boundary_inventory"], [])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["selector_inventory"], [])
        for field in ("planned_hypotheses", "planned_boundary_observations", "planned_transition_pairs",
                      "planned_query_work_items", "known_transition_pair_subtotal", "known_stored_query_work_subtotal",
                      "planned_unique_literal_boundary_coordinates", "planned_unique_terminal_probes"):
            self.assertEqual(result["summary"][field], 0, field)

    def test_comparison_parent_whole_hold_is_preserved_without_new_evidence(self):
        _, _, _, parent, session = self.ready(query_work_budget=0)
        self.assertEqual(parent["hypotheses"], [])
        result = context.build_context_prepared(session)
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["selector_inventory"], parent["selector_inventory"])
        self.assertTrue(result["reasons"])

    def pure_scope(self, lanes, **options):
        """Fresh literal fixture only, not a registered progression completion."""
        return self.helper.helper.factory.fixture(lanes, **options)

    def ordinary_c_variant(self):
        inputs, _, _, _, _ = self.ready("no_pair")
        return deepcopy(next(row["variant"] for row in inputs[3]["variant_inventory"]
            if row["variant"]["root"] == {"step": "C", "alter": common.q(0)}
            and row["variant"]["members"] is not None
            and {common.pitch_key(p) for p in row["variant"]["members"]}
                == {("C", Fraction()), ("E", Fraction()), ("G", Fraction())}))

    def test_pure_conditional_inversions_follow_root_third_fifth_not_span_minimum(self):
        _, scope = self.pure_scope([[delayed_fixtures.event("C3", 0, 1),
                                    delayed_fixtures.event("E3", 1, 1),
                                    delayed_fixtures.event("G3", 2, 2)]])
        variant = self.ordinary_c_variant()
        shape = context._ordinary_shape(variant)
        facts = sorted(scope["sound_facts"], key=lambda r: common.f(r["span"]["start"]))
        values = [context._factor(sound, variant, shape, is_lowest=True,
                   lowest_spelling_ambiguous=False)["conditional_inversion_shape"] for sound in facts]
        self.assertEqual(values, [0, 1, 2])
        self.assertTrue(all(context._factor(sound, variant, shape, is_lowest=True,
            lowest_spelling_ambiguous=False)["structural_bass_confirmed"] is False for sound in facts))

    def test_pure_nonmember_bass_does_not_receive_inversion_or_NCT_exemption(self):
        _, scope = self.pure_scope([[delayed_fixtures.event("D3", 0, 4)]])
        variant = self.ordinary_c_variant()
        row = context._factor(scope["sound_facts"][0], variant, context._ordinary_shape(variant),
            is_lowest=True, lowest_spelling_ambiguous=False)
        self.assertIs(row["spelled_member_of_assumption"], False)
        self.assertIsNone(row["conditional_inversion_shape"])
        self.assertTrue(row["blockers"])

    def test_pure_source_failure_retains_observation_but_blocks_conditional_inversion(self):
        _, scope = self.pure_scope([[delayed_fixtures.event("C3", 0, 4)]])
        variant = self.ordinary_c_variant()
        sound = deepcopy(scope["sound_facts"][0])
        sound["source_clock_passed"] = False
        sound["source_pitch_consistency_passed"] = False
        sound["eligible_as_analysis_source"] = False
        row = context._factor(sound, variant, context._ordinary_shape(variant),
            is_lowest=True, lowest_spelling_ambiguous=False)
        self.assertIs(row["spelled_member_of_assumption"], True)
        self.assertIsNone(row["conditional_inversion_shape"])
        self.assertTrue(row["blockers"])

    def test_pure_equal_lowest_enharmonic_ambiguity_prevents_first_spelling_choice(self):
        _, scope = self.pure_scope([[delayed_fixtures.event(["G#3", "A-3", "C5"], 0, 4)]])
        variant = self.ordinary_c_variant()
        for sound in scope["sound_facts"]:
            if sound["pitch"]["octave"] == 3:
                row = context._factor(sound, variant, context._ordinary_shape(variant),
                    is_lowest=True, lowest_spelling_ambiguous=True)
                self.assertIsNone(row["conditional_inversion_shape"])
                self.assertIn("equal_lowest_enharmonic_spellings_unresolved", row["blockers"])

    def test_pure_unknown_scale_form_and_microtones_are_not_truncated_into_coordinates(self):
        inputs, _, _, _, _ = self.ready("key")
        known = deepcopy(next(k["segments"][0] for k in inputs[2]["keys"] if k["segments"][0]["mode"] == "major"))
        pitch = deepcopy(inputs[1]["sound_facts"][0]["pitch"])
        known["scale_form"] = "unknown"
        row = context._degree(pitch, known)
        self.assertIsNone(row["coordinate"])
        self.assertTrue(row["blockers"])
        known["scale_form"] = "major"
        pitch["alter"] = common.q(Fraction(1, 2))
        row = context._degree(pitch, known)
        self.assertIsNone(row["coordinate"])
        self.assertTrue(row["blockers"])

    def test_pure_rational_boundary_uses_distinct_left_right_attack_and_carry_sets(self):
        _, scope = self.pure_scope([[delayed_fixtures.event("C4", 0, Fraction(1, 3)),
                                    delayed_fixtures.event("D4", Fraction(1, 3), Fraction(11, 3))],
                                   [delayed_fixtures.event("G3", 0, 4)]])
        by_pitch = {r["pitch"]["spelling"]: r["sound_ref"] for r in scope["sound_facts"]}
        row = context._boundary(scope, Fraction(1, 3))
        self.assertEqual(row["boundary_time"], common.q(Fraction(1, 3)))
        self.assertEqual(set(row["positive_sound_refs_before"]), {by_pitch["C4"], by_pitch["G3"]})
        self.assertEqual(set(row["positive_sound_refs_at"]), {by_pitch["D4"], by_pitch["G3"]})
        self.assertEqual(row["full_sound_start_refs"], [by_pitch["D4"]])
        self.assertEqual(row["full_sound_end_refs"], [by_pitch["C4"]])
        self.assertEqual(row["full_sound_continuing_refs"], [by_pitch["G3"]])

    def test_pure_context_endpoint_is_not_a_following_observation(self):
        _, scope = self.pure_scope([[delayed_fixtures.event("C4", 0, 4)]])
        row = context._boundary(scope, Fraction(4))
        self.assertEqual(row["positive_sound_refs_at"], [])
        self.assertEqual(row["observation_status"], "analysis_endpoint_not_following_observation")
        self.assertEqual(row["following"]["phrase_closure"], "unassessed")
        with self.assertRaises(ValueError):
            context._boundary(scope, Fraction(13, 3))

    def test_pure_full_tie_release_and_source_snapshots_are_never_clipped_to_horizon(self):
        ir, observed = self.pure_scope([[delayed_fixtures.event("C4", 0, 2, tie_role="start"),
                                       delayed_fixtures.event("C4", 2, 6, tie_role="stop")]])
        # This explicitly unregistered observation horizon is a helper test;
        # it does not obtain a public fmpctx_ record or new completion witness.
        scope = deepcopy(observed)
        scope["analysis_span"] = delayed_fixtures.span(0, 4)
        sound = scope["sound_facts"][0]
        row = context._terminal(scope, sound, Fraction(2), context._boundary(scope, Fraction(2))["notated_metric"])
        self.assertEqual(row["full_sound_span"], sound["span"])
        self.assertEqual(common.f(row["candidate_terminal_release_time"]), 8)
        self.assertEqual(common.f(row["full_sound_duration_quarters"]), 8)
        self.assertTrue(row["release_beyond_observed_horizon"])
        self.assertEqual(row["following_observation_status"], "unassessed_at_or_beyond_context_endpoint")
        self.assertEqual(len(sound["source_note_ids"]), 2)
        self.assertEqual(len(ir["tie_chains"]), 1)

    def test_pure_following_rest_and_no_attack_do_not_certify_phrase_closure(self):
        _, scope = self.pure_scope([[delayed_fixtures.event("C5", 0, 1), delayed_fixtures.event(None, 1, 3)],
                                   [delayed_fixtures.event("G3", 0, 4)]])
        sound = next(r for r in scope["sound_facts"] if r["pitch"]["spelling"] == "C5")
        row = context._terminal(scope, sound, Fraction(0), context._boundary(scope, Fraction(0))["notated_metric"])
        self.assertTrue(row["observed_following_same_raw_lane_rest_spans"])
        self.assertFalse(row["no_observed_later_attack_is_phrase_closure"])
        self.assertFalse(row["sustain_or_ornament_is_universal_cadence_counterevidence"])
        self.assertEqual(row["phrase_terminal"], "unassessed")

    def test_pure_extrema_preserve_equal_height_spellings_without_structural_or_concert_proof(self):
        _, scope = self.pure_scope([[delayed_fixtures.event(["G#3", "A-3", "C5"], 0, 4)]])
        row = context._boundary(scope, Fraction(0))["lowest_highest_at"]
        self.assertEqual(len(row["lowest_sound_refs"]), 2)
        self.assertEqual(row["structural_bass"], "unassessed")
        self.assertEqual(row["structural_melody"], "unassessed")
        self.assertFalse(row["concert_pitch_certified"])


if __name__ == "__main__":
    unittest.main()
