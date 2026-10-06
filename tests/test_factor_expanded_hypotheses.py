"""Fresh-envelope candidate inventories and conditional comparisons, not verdicts."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_context_observation as context
from musicanote_harness import factor_expanded_hypotheses as hypotheses
from musicanote_harness import factor_expanded_scope as expanded
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_candidate_catalog as catalog
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness import sounding_lineage_audit as lineage
from test_factor_context_observation import physical_clocks
from test_factor_musical_view import make_observation, reseal, span
from test_musical_role_evidence import event, make_ir


class ExpandedHypothesisFixture:
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case_count = 0

    def fixture(self, lanes=None, *, extent=None, clocks=None, signatures=None,
                modify=None, caps=None):
        lanes = lanes or [[event(["C3", "E4", "G4"], 0, 4)]]
        self.case_count += 1
        directory = Path(self.temp.name) / str(self.case_count)
        directory.mkdir()
        ir = make_ir(directory, lanes)
        if clocks is not None:
            physical_clocks(ir, clocks)
        if signatures is not None:
            for measure, declaration in zip(ir["measures"], signatures):
                measure["key_signature"] = deepcopy(declaration)
        if modify is not None:
            modify(ir)
        extent = extent or span(1, 2)
        observation = make_observation(ir, extent)
        ids = [s["sounding_event_id"] for s in observation["core_projection"]["sounding_events"]]
        audit = lineage.audit_sounding_lineage(ir, sound_ids=ids, context_span=extent)
        view = common.prepare(ir, observation, audit)
        extension = context.observe_context(ir, view, observation, audit)
        scope = expanded.prepare_scope(ir, view, observation, audit, extension, **(caps or {}))
        return ir, scope

    def build(self, fixture, **options):
        return hypotheses.build_hypotheses(*fixture, **options)

    def evaluate(self, fixture, record, **options):
        return hypotheses.evaluate_hypotheses(*fixture, record, **options)


class ExpandedHypothesisBuildTests(ExpandedHypothesisFixture, unittest.TestCase):
    def test_fresh_expanded_span_typed_binding_reproducibility_and_immutability(self):
        fx = self.fixture()
        before = deepcopy(fx)
        result = self.build(fx)
        self.assertTrue(result["record_id"].startswith("fmeh_"))
        self.assertEqual(result["scope_ref"], common.ref(fx[1]))
        self.assertEqual(result["analysis_span"], span())
        self.assertEqual(self.build(fx), result)
        self.assertEqual(fx, before)
        self.assertTrue(hypotheses.validate_hypotheses(*fx, result))

    def test_every_observed_internal_attack_and_release_not_metric_grid_is_a_cut(self):
        fx = self.fixture([[event("C3", 0, 1), event("D3", 1, 1), event("E3", 2, 2)],
                           [event("G4", 0, Fraction(3, 2)), event(None, Fraction(3, 2), Fraction(1, 2)),
                            event(None, 2, 2)]])
        result = self.build(fx)
        self.assertEqual(result["cut_times"], [common.q(1), common.q(Fraction(3, 2)), common.q(2)])
        self.assertEqual(len(result["catalog_inventory"]), 7)
        self.assertEqual(len(result["path_groups"]), 4)

    def test_rational_triplet_boundaries_remain_exact_no_rounding(self):
        fx = self.fixture([[event("C3", 0, Fraction(1, 3)),
                           event("D3", Fraction(1, 3), Fraction(1, 3)),
                           event("E3", Fraction(2, 3), Fraction(10, 3))]])
        result = self.build(fx)
        self.assertEqual(result["cut_times"], [common.q(Fraction(1, 3)), common.q(Fraction(2, 3))])
        self.assertEqual(len(result["catalog_inventory"]), 5)

    def test_no_internal_event_endpoints_produces_only_full_hold(self):
        result = self.build(self.fixture())
        self.assertEqual(result["cut_times"], [])
        self.assertEqual(len(result["catalog_inventory"]), 1)
        self.assertEqual([g["kind"] for g in result["path_groups"]], ["full_hold"])

    def test_whole_catalog_budget_keeps_every_planned_span_and_no_partial_paths(self):
        fx = self.fixture([[event(["C3", "E4", "G4"], 0, 2), event(["D3", "F4", "A4"], 2, 2)]])
        full = self.build(fx)
        held = self.build(fx, max_catalogs=2)
        self.assertEqual(held["cut_times"], full["cut_times"])
        self.assertEqual([c["span"] for c in held["catalog_inventory"]],
                         [c["span"] for c in full["catalog_inventory"]])
        self.assertTrue(all(not g["paths"] for g in held["path_groups"]))
        self.assertTrue(hypotheses.validate_hypotheses(*fx, held))

    def test_suppliers_replay_all_parts_exact_spans_and_original_records(self):
        fx = self.fixture([[event(["C3", "E4"], 0, 4)],
                           [event("G4", 0, 2), event("B4", 2, 2)]])
        result = self.build(fx)
        expected_spans = [span(), span(0, 2), span(2, 4)]
        self.assertCountEqual([row["span"] for row in result["catalog_inventory"]], expected_spans)
        for row in result["catalog_inventory"]:
            supplier = catalog.propose(fx[0], row["span"], fx[1]["analysis_span"])
            self.assertEqual(row["supplier_catalog"], supplier)
            self.assertEqual(row["candidate_count"], len(supplier["candidates"]))
            self.assertEqual(row["variant_count"], len(row["variants"]))
            self.assertGreaterEqual(row["variant_count"], row["candidate_count"])

    def test_base_augmented_extended_and_additional_seventh_all_survive(self):
        fx = self.fixture([[event(["C3", "E3", "B3", "B-3", "D4", "A-3", "F#4"], 0, 4)]])
        row = self.build(fx)["catalog_inventory"][0]
        self.assertEqual({c["provider"] for c in row["supplier_catalog"]["candidates"]},
                         {"base", "additional_seventh", "augmented", "extended"})
        self.assertEqual(row["candidate_count"], len(row["supplier_catalog"]["candidates"]))
        self.assertGreaterEqual(len(row["variants"]), row["candidate_count"])

    def test_build_never_rebinds_old_fmview_path_key_or_completion_bundle(self):
        from musicanote_harness import factor_functional_overlay as old_functions
        from musicanote_harness import factor_functional_resolution as old_resolution
        fx = self.fixture()
        with patch.object(common, "make_path", side_effect=AssertionError("old path forbidden")), \
             patch.object(old_functions, "make_key_track", side_effect=AssertionError("old key forbidden")), \
             patch.object(old_resolution, "make_bundle", side_effect=AssertionError("old bundle forbidden")):
            record = self.build(fx)
        self.assertEqual(record["scope_ref"], common.ref(fx[1]))
        self.assertTrue(all(v is False for v in record["flags"].values()))

    def test_current_supplier_source_bytes_invalidate_existing_hypothesis_record(self):
        fx = self.fixture()
        record = self.build(fx)
        actual = Path.read_bytes
        target = Path(catalog.__file__)
        def changed_bytes(path):
            raw = actual(path)
            return raw + b"\n" if path == target else raw
        with patch.object(Path, "read_bytes", changed_bytes), self.assertRaises(ValueError):
            hypotheses.validate_hypotheses(*fx, record)

    def test_all_research_flags_false_neither_winner_nor_source_authority(self):
        result = self.build(self.fixture())
        self.assertTrue(all(value is False for value in result["flags"].values()))
        self.assertIsNone(result.get("selected"))
        self.assertIsNone(result.get("preferred"))
        self.assertNotIn("confidence", result)

    def test_invalid_build_limits_rejected_before_scope_or_core_reads(self):
        for name, values in (("max_catalogs", (-1, True, 1.5, None, "1")),
                             ("path_budget", (0, -1, True, 1.5, None, "1"))):
            for value in values:
                with self.subTest(name=name, value=value), \
                     patch.object(expanded, "check_scope", side_effect=AssertionError("no scope read")):
                    with self.assertRaises(ValueError):
                        hypotheses.build_hypotheses(None, None, **{name: value})

    def test_stale_current_IR_rejected_even_when_only_notation_changes(self):
        fx = self.fixture()
        changed = deepcopy(fx[0])
        changed["note_events"][0]["notation"]["unrelated_prose"] = "new literal content"
        with self.assertRaises(ValueError):
            hypotheses.build_hypotheses(changed, fx[1])

    def test_resealed_foreign_scope_ref_is_not_authority(self):
        fx = self.fixture()
        result = self.build(fx)
        result["scope_ref"] = {"record_id": "fmes_" + "0" * 24, "record_sha256": "0" * 64}
        with self.assertRaises(ValueError):
            hypotheses.validate_hypotheses(*fx, reseal(result, "fmeh_"))

    def test_resealed_cut_omission_and_unknown_or_promoting_fields_rejected(self):
        fx = self.fixture([[event(["C3", "E4", "G4"], 0, 2), event(["D3", "F4", "A4"], 2, 2)]])
        original = self.build(fx)
        for kind in ("cut", "catalog", "promotion", "unknown"):
            forged = deepcopy(original)
            if kind == "cut": forged["cut_times"].pop()
            elif kind == "catalog": forged["catalog_inventory"].pop()
            elif kind == "promotion": forged["flags"]["cadence_confirmed"] = True
            else: forged["confidence"] = 0.99
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                hypotheses.validate_hypotheses(*fx, reseal(forged, "fmeh_"))

    def test_every_provider_candidate_and_spelling_alternative_has_exact_variant_origin(self):
        row = self.build(self.fixture())["catalog_inventory"][0]
        supplier = row["supplier_catalog"]
        variants = row["variants"]
        self.assertEqual(len(variants), sum(max(1, len(c["spelling_alternatives"]))
                                            for c in supplier["candidates"]))
        for index, candidate in enumerate(supplier["candidates"]):
            retained = [v for v in variants if v["supplier_candidate_ref"] == candidate["candidate_id"]]
            self.assertEqual(len(retained), max(1, len(candidate["spelling_alternatives"])))
            for variant in retained:
                self.assertEqual(variant["provider"], candidate["provider"])
                self.assertEqual(variant["supplier_origin_pointer"], candidate["origin_pointer"])
                self.assertEqual(variant["supplier_record_pointer"], "/candidates/" + str(index))
                self.assertEqual(catalog.resolve(supplier, variant["supplier_record_pointer"]), candidate)
                self.assertEqual(variant["supplier_event_states"], candidate["event_states"])

    def test_unspelled_supplier_candidate_is_preserved_unknown_not_invented(self):
        fx = self.fixture([[event(["E3", "G3"], 0, 4)]])
        row = self.build(fx)["catalog_inventory"][0]
        raw = next(c for c in row["supplier_catalog"]["providers"]["base"]["candidates"]
                   if c["label"] == "C:major")
        variant = next(v for v in row["variants"] if v["supplier_candidate_ref"] == raw["candidate_id"])
        self.assertIsNone(variant["root"])
        self.assertIsNone(variant["members"])
        self.assertIsNone(variant["spelling_alternative_index"])
        self.assertIn("supplier_spelling_unresolved_no_root_invented", variant["blockers"])
        self.assertIsNone(variant["provenance"]["source_statement_ref"])
        self.assertIsNone(variant["provenance"]["source_path"])

    def test_augmented_tonic_coordinate_never_becomes_a_tertian_root(self):
        row = self.build(self.fixture([[event(["A-3", "C4", "F#4"], 0, 4)]]))["catalog_inventory"][0]
        variants = [v for v in row["variants"] if v["provider"] == "augmented"
                    and v["tonal_coordinate"] == ["C", 0]]
        self.assertTrue(variants)
        self.assertTrue(all(v["root"] is None and v["members"] is not None for v in variants))

    def test_path_budget_whole_preflight_keeps_counts_no_top_k_prefix(self):
        fx = self.fixture([[event(["C3", "E4", "G4"], 0, 2), event(["D3", "F4", "A4"], 2, 2)]])
        full = self.build(fx, path_budget=4096)
        counts = [g["total_paths"] for g in full["path_groups"]]
        self.assertTrue(all(len(g["paths"]) == g["total_paths"] for g in full["path_groups"]))
        held = self.build(fx, path_budget=1)
        self.assertEqual([g["total_paths"] for g in held["path_groups"]], counts)
        self.assertEqual(held["catalog_inventory"], full["catalog_inventory"])
        self.assertTrue(all(g["status"] == "whole_group_budget_abstention"
                            and g["paths"] == [] for g in held["path_groups"]))
        exact = self.build(fx, path_budget=counts[0])
        self.assertEqual(len(exact["path_groups"][0]["paths"]), counts[0])

    def test_every_materialized_path_has_complete_partition_and_new_sealed_segments(self):
        fx = self.fixture([[event(["C3", "E4", "G4"], 0, 2), event(["D3", "F4", "A4"], 2, 2)]])
        result = self.build(fx, path_budget=4096)
        for group in result["path_groups"]:
            self.assertEqual(group["partition"][0]["start"], result["analysis_span"]["start"])
            self.assertEqual(group["partition"][-1]["end"], result["analysis_span"]["end"])
            for left, right in zip(group["partition"], group["partition"][1:]):
                self.assertEqual(left["end"], right["start"])
            for path in group["paths"]:
                self.assertTrue(path["record_id"].startswith("fmehpath_"))
                self.assertEqual(path["partition"], group["partition"])
                self.assertEqual(path["scope_ref"], common.ref(fx[1]))
                self.assertEqual([s["span"] for s in path["segments"]], group["partition"])
                for segment in path["segments"]:
                    self.assertTrue(segment["segment_id"].startswith("fmehseg_"))
                    self.assertEqual(segment["scope_ref"], common.ref(fx[1]))
                    common.check(segment, "fmehseg_")

    def test_unambiguous_signature_five_new_keys_including_unknown_and_no_key_proof(self):
        fx = self.fixture(signatures=[{"fifths": 2, "mode_hint": "major"}])
        keys = self.build(fx)["keys"]
        self.assertEqual(len(keys), 5)
        self.assertEqual([k["segments"][0]["scale_form"] for k in keys],
                         ["major", "natural_minor", "harmonic_minor", "melodic_minor_ascending", "unknown"])
        self.assertEqual(keys[0]["segments"][0]["tonic"], {"step": "D", "alter": common.q(0)})
        self.assertEqual(keys[1]["segments"][0]["tonic"], {"step": "B", "alter": common.q(0)})
        self.assertIsNone(keys[-1]["segments"][0]["tonic"])
        for key in keys:
            self.assertTrue(key["record_id"].startswith("newkey_"))
            self.assertEqual(key["scope_ref"], common.ref(fx[1]))
            self.assertEqual(key["segments"][0]["span"], fx[1]["analysis_span"])
            self.assertFalse(key["provenance"]["mode_hint_used_as_key"])
            self.assertTrue(all(v is False for v in key["flags"].values()))

    def test_absent_changing_or_overlapping_key_clocks_preserve_unknown_only(self):
        configurations = (
            {},
            {"clocks": [(0, 2), (2, 2)],
             "signatures": [{"fifths": 0, "mode_hint": None}, {"fifths": 1, "mode_hint": None}]},
            {"clocks": [(0, 4), (1, 3)],
             "signatures": [{"fifths": 0, "mode_hint": None}, {"fifths": 0, "mode_hint": None}]},
        )
        for options in configurations:
            fx = self.fixture(**options)
            keys = self.build(fx)["keys"]
            with self.subTest(options=options):
                self.assertEqual(len(keys), 1)
                self.assertEqual(keys[0]["segments"][0]["mode"], "unknown")
                self.assertIsNone(keys[0]["segments"][0]["tonic"])


class ExpandedHypothesisEvaluationTests(ExpandedHypothesisFixture, unittest.TestCase):
    def dominant_transition(self):
        # Four explicit raw lanes provide fully sounded source/target shapes.
        # Continuity edges are still hypotheses, not certified musical voices.
        fx = self.fixture([[event("B4", 0, 2), event("C5", 2, 2)],
                           [event("F4", 0, 2), event("E4", 2, 2)],
                           [event("G3", 0, 2), event("C3", 2, 2)],
                           [event("D4", 0, 2), event("G4", 2, 2)]])
        return fx, self.build(fx, path_budget=4096)

    def dominant_row(self, proposed, result):
        expected_source = {("G", Fraction(0)), ("B", Fraction(0)),
                           ("D", Fraction(0)), ("F", Fraction(0))}
        expected_target = {("C", Fraction(0)), ("E", Fraction(0)), ("G", Fraction(0))}
        def members(segment):
            return None if segment["members"] is None else {common.pitch_key(p) for p in segment["members"]}
        group = next(g for g in proposed["path_groups"] if g["kind"] == "two_segment")
        path = next(p for p in group["paths"]
                    if p["segments"][0]["root"] is not None
                    and common.pitch_key(p["segments"][0]["root"]) == ("G", Fraction(0))
                    and members(p["segments"][0]) == expected_source
                    and p["segments"][1]["root"] is not None
                    and common.pitch_key(p["segments"][1]["root"]) == ("C", Fraction(0))
                    and members(p["segments"][1]) == expected_target)
        comparison = next(r for g in result["groups"] for r in g["rows"]
                          if r["path_ref"] == common.ref(path))
        function = next(f for f in comparison["functions"] if f["family"] == "V7"
                        and f["target_quality"] == "M"
                        and f["source_segment_ref"] == path["segments"][0]["segment_id"])
        return comparison, function

    def test_one_fresh_shared_bundle_registered_for_every_path_key_competitor(self):
        fx = self.fixture(signatures=[{"fifths": 0, "mode_hint": None}])
        proposed = self.build(fx)
        before = deepcopy((fx, proposed))
        result = self.evaluate(fx, proposed)
        baseline = result["baseline_bundle_ref"]
        self.assertTrue(result["record_id"].startswith("fmehc_"))
        self.assertEqual(result["scope_ref"], common.ref(fx[1]))
        self.assertEqual(result["hypotheses_ref"], common.ref(proposed))
        self.assertTrue(all(row["shared_bundle_ref"] == baseline for g in result["groups"] for row in g["rows"]))
        self.assertEqual(len(result["bundle_inventory"]), 1)
        bundle = result["bundle_inventory"][0]
        self.assertTrue(bundle["record_id"].startswith("fmehbundle_"))
        self.assertEqual(bundle["comparison_path_refs"], [common.ref(p) for g in proposed["path_groups"] for p in g["paths"]])
        self.assertEqual(bundle["comparison_key_refs"], [common.ref(k) for k in proposed["keys"]])
        self.assertEqual(bundle["covered_lanes"], sorted([[r["part_id"], r["voice_id"]] for r in fx[1]["raw_lanes"]]))
        self.assertTrue(bundle["all_no_link_control"])
        self.assertEqual((fx, proposed), before)
        self.assertTrue(hypotheses.validate_evaluation(*fx, proposed, result))

    def test_all_path_key_pairs_and_function_shapes_materialized_at_exact_budgets(self):
        fx = self.fixture(signatures=[{"fifths": 0, "mode_hint": None}])
        proposed = self.build(fx)
        count = proposed["path_groups"][0]["total_paths"] * len(proposed["keys"])
        result = self.evaluate(fx, proposed, pair_budget=count, overlay_pair_budget=count * 10)
        group = result["groups"][0]
        self.assertEqual(group["total_path_key_pairs"], count)
        self.assertEqual(group["total_function_shapes"], count * 10)
        self.assertEqual(len(group["rows"]), count)
        self.assertEqual(sum(len(row["functions"]) for row in group["rows"]), count * 10)

    def test_pair_and_overlay_budget_holds_keep_denominators_and_no_partial_rows(self):
        fx = self.fixture()
        proposed = self.build(fx)
        full = self.evaluate(fx, proposed)
        for options in ({"pair_budget": 0}, {"overlay_pair_budget": 0}):
            held = self.evaluate(fx, proposed, **options)
            with self.subTest(options=options):
                self.assertEqual([g["total_path_key_pairs"] for g in held["groups"]],
                                 [g["total_path_key_pairs"] for g in full["groups"]])
                self.assertEqual([g["total_function_shapes"] for g in held["groups"]],
                                 [g["total_function_shapes"] for g in full["groups"]])
                self.assertTrue(all(g["rows"] == [] and g["status"] == "whole_group_budget_abstention"
                                    for g in held["groups"]))
                self.assertTrue(hypotheses.validate_evaluation(*fx, proposed, held))

    def test_raw_membership_accounts_every_all_part_sound_without_rank_or_nct_verdict(self):
        fx = self.fixture([[event("C3", 0, 4)], [event("E4", 0, 4)], [event("G5", 0, 4)]])
        proposed = self.build(fx)
        result = self.evaluate(fx, proposed)
        for group in result["groups"]:
            for row in group["rows"]:
                self.assertEqual(row["profiles"][0]["total_note_time_quarters"], common.q(12))
                self.assertEqual(len(row["profiles"][0]["rows"]), 3)
                self.assertIsNone(row["selected"])
                self.assertIsNone(row["rank"])
                self.assertIsNone(row["cadence"])
                self.assertIsNone(row["NCT"])
        self.assertTrue(all(v is False for v in result["flags"].values()))

    def test_unknown_key_does_not_erase_shape_inventory_or_invent_projection(self):
        fx = self.fixture()
        proposed = self.build(fx)
        functions = self.evaluate(fx, proposed)["groups"][0]["rows"][0]["functions"]
        self.assertEqual({f["family"] for f in functions}, {"V", "V7", "vii", "vii7", "vii_half7"})
        self.assertEqual({f["target_quality"] for f in functions}, {"M", "m"})
        self.assertTrue(all(f["function_kind"] == "unassessed" for f in functions))
        self.assertTrue(all("explicit_key_unknown" in f["key_projection"]["unassessed_reasons"] for f in functions))

    def test_extended_catalog_member_index_is_not_ordinary_tertian_inversion(self):
        fx = self.fixture([[event(["C3", "E4", "G4", "B-4", "D5"], 0, 4)]])
        proposed = self.build(fx)
        result = self.evaluate(fx, proposed)
        paths = proposed["path_groups"][0]["paths"]
        c_root = {"step": "C", "alter": common.q(0)}
        extended_path = next(p for p in paths if p["segments"][0]["provider"] == "extended"
                             and p["segments"][0]["root"] == c_root
                             and len(p["segments"][0]["members"]) > 4)
        ordinary_path = next(p for p in paths if p["segments"][0]["root"] == c_root
                             and p["segments"][0]["members"] is not None
                             and {common.pitch_key(m) for m in p["segments"][0]["members"]}
                             == {("C", Fraction(0)), ("E", Fraction(0)), ("G", Fraction(0))})
        profiles = {r["path_ref"]["record_id"]: r["profiles"][0] for g in result["groups"] for r in g["rows"]}
        extended_cell = profiles[extended_path["record_id"]]["cells"][0]
        self.assertEqual(extended_cell["conditional_bass_member_indices"], [0])
        self.assertEqual(extended_cell["conditional_inversions"], [])
        self.assertEqual(extended_cell["inversion_basis"], "rootless_extended_or_nontertian_inversion_unassessed")
        ordinary_profile = profiles[ordinary_path["record_id"]]
        self.assertEqual(ordinary_profile["cells"][0]["conditional_bass_member_indices"], [0])
        self.assertEqual(ordinary_profile["cells"][0]["conditional_inversions"], [0])
        self.assertEqual(ordinary_profile["cells"][0]["inversion_basis"],
                         "conditional_complete_ordinary_tertian_template")
        self.assertEqual(sum(r["state"] == "nonmember_not_confirmed_nct" for r in ordinary_profile["rows"]), 2)

    def test_add_six_quartal_and_unordered_member_lists_are_not_ordinary_inversion_templates(self):
        def pc(step):
            return {"step": step, "alter": common.q(0)}
        # These minimal caller dictionaries probe only shape eligibility; they
        # are neither supplier records nor source harmonic annotations.
        ordinary = {"root": pc("C"), "members": [pc("C"), pc("E"), pc("G")]}
        self.assertTrue(hypotheses._ordinary_tertian(ordinary))
        for members in ([pc("C"), pc("E"), pc("G"), pc("A")],
                        [pc("C"), pc("F"), pc("G")],
                        [pc("G"), pc("C"), pc("E")]):
            with self.subTest(members=members):
                self.assertFalse(hypotheses._ordinary_tertian({"root": pc("C"), "members": members}))

    def test_direct_leading_tone_and_seventh_require_one_complete_joint_all_lane_bundle(self):
        fx, proposed = self.dominant_transition()
        result = self.evaluate(fx, proposed)
        comparison, function = self.dominant_row(proposed, result)
        self.assertTrue(function["shape_compatible"])
        self.assertTrue(function["target_shape_compatible"])
        motion = function["motion"]
        self.assertEqual(motion["status"], "conditional_joint_motion_shape")
        self.assertEqual(set(motion["edge_options"]), {"leading_tone", "seventh"})
        self.assertEqual(motion["total_joint_options"], 1)
        joint = motion["joint_options"][0]
        self.assertTrue(joint["all_critical_roles_in_same_bundle"])
        self.assertEqual(set(joint["critical_roles"]), {"leading_tone", "seventh"})
        self.assertEqual(len(joint["required_links"]), 2)
        bundle = next(b for b in result["bundle_inventory"] if common.ref(b) == joint["bundle_ref"])
        self.assertEqual(bundle["required_links"], joint["required_links"])
        self.assertEqual(bundle["materialized_witness_links"], joint["required_links"])
        self.assertEqual(len(bundle["entries"]), len(fx[1]["raw_lanes"]))
        self.assertEqual(bundle["status"], "complete_all_lane_witness")
        assessments = {r["bundle_ref"]["record_id"]: r for r in result["same_bundle_assessments"]}
        for record in assessments.values():
            self.assertFalse(record["optional_unrequired_links_present"])
            row = next(r for r in record["rows"] if r["path_ref"] == comparison["path_ref"]
                       and r["key_ref"] == comparison["key_ref"])
            if record["bundle_ref"] == result["baseline_bundle_ref"]:
                self.assertNotIn(function["function_id"], row["joint_motion_shape_refs"])
            if record["bundle_ref"] == joint["bundle_ref"]:
                self.assertIn(function["function_id"], row["joint_motion_shape_refs"])
        self.assertIsNone(function["function_confirmed"])
        self.assertIsNone(function["cadence"])

    def test_zero_motion_budget_preflights_all_endpoints_keeps_no_favorable_subset(self):
        fx, proposed = self.dominant_transition()
        result = self.evaluate(fx, proposed, max_motion_pairs=0)
        _, function = self.dominant_row(proposed, result)
        motion = function["motion"]
        self.assertEqual(motion["planned_endpoint_pairs"], 2)
        self.assertEqual(motion["status"], "whole_group_budget_abstention")
        self.assertIsNone(motion["total_joint_options"])
        self.assertTrue(all(not edges for edges in motion["edge_options"].values()))
        self.assertEqual(motion["joint_options"], [])
        self.assertEqual(motion["qualifying_bundle_refs"], [])
        self.assertEqual(len(result["bundle_inventory"]), 1)
        self.assertIn("complete_endpoint_motion_pair_group_exceeds_budget_no_pruning", motion["blockers"])

    def test_complete_all_bundle_pair_preflight_withholds_whole_group_not_some_bundles(self):
        fx, proposed = self.dominant_transition()
        path_count = next(g["total_paths"] for g in proposed["path_groups"] if g["kind"] == "two_segment")
        result = self.evaluate(fx, proposed, pair_budget=path_count)
        group = next(g for g in result["groups"] if g["kind"] == "two_segment")
        self.assertGreater(len(result["bundle_inventory"]), 1)
        self.assertEqual(group["total_path_key_pairs"], path_count)
        self.assertEqual(group["planned_same_bundle_assessments"], len(result["bundle_inventory"]) * path_count)
        self.assertEqual(group["status"], "whole_group_budget_abstention")
        self.assertEqual(group["rows"], [])
        self.assertIn("complete_all_bundle_comparison_group_exceeds_budget_no_pruning", group["reasons"])
        for assessment in result["same_bundle_assessments"]:
            self.assertIn(group["group_id"], assessment["budget_held_comparison_groups"])
            self.assertTrue(all(row["path_ref"] not in [common.ref(p) for g in proposed["path_groups"]
                                                       if g["kind"] == "two_segment" for p in g["paths"]]
                                for row in assessment["rows"]))

    def test_full_source_guard_is_retained_in_raw_profiles_not_fixed_by_new_scope(self):
        fx = self.fixture([[event("C4", 0, 1, tie_role="start"),
                            event("C4", 3, 1, tie_role="stop")],
                           [event("E4", 0, 4)], [event("G4", 0, 4)]])
        proposed = self.build(fx)
        result = self.evaluate(fx, proposed)
        tied = next(s for s in fx[1]["sound_facts"] if len(s["source_note_refs"]) == 2)
        rows = [s for g in result["groups"] for r in g["rows"] for p in r["profiles"]
                for s in p["rows"] if s["sound_ref"] == tied["sound_ref"]]
        self.assertTrue(rows)
        self.assertTrue(all(s["source_clock_passed"] is False for s in rows))
        self.assertTrue(all("full_source_timeline_gap" in s["source_diagnostics"] for s in rows))
        self.assertTrue(all(s["full_span"] == tied["span"] for s in rows))

    def test_missing_attack_critical_edge_not_rescued_by_healthy_same_spelled_doubling(self):
        def missing_new_source_attack(ir):
            bad = next(s for s in ir["sounding_events"] if s["pitch"]["spelling"] == "B3")
            ir["attack_events"] = [r for r in ir["attack_events"]
                                   if r["sounding_event_id"] != bad["sounding_event_id"]]
        # The old extent contains only the destination. The bad source is new
        # envelope evidence, never an attempt to weaken old fmview admission.
        fx = self.fixture([[event(["G3", "B3", "D4", "F4"], 0, 2),
                            event(["C4", "E4", "G4"], 2, 2)],
                           [event("B4", 0, 2), event("C5", 2, 2)]],
                          extent=span(3, 4), modify=missing_new_source_attack)
        proposed = self.build(fx, path_budget=4096)
        result = self.evaluate(fx, proposed, pair_budget=65536)
        comparison, function = self.dominant_row(proposed, result)
        bad = next(s for s in fx[1]["sound_facts"] if s["pitch"]["spelling"] == "B3")
        healthy = next(s for s in fx[1]["sound_facts"] if s["pitch"]["spelling"] == "B4")
        self.assertFalse(bad["source_attack_consistency_passed"])
        self.assertFalse(bad["eligible_as_analysis_source"])
        self.assertTrue(healthy["source_attack_consistency_passed"])
        self.assertTrue(healthy["eligible_as_analysis_source"])
        # Both B spellings were observed, and the healthy one establishes the
        # eligible core. Its guard cannot be transferred to the other edge.
        self.assertEqual(comparison["profiles"][0]["cells"][-1]["source_guard_missing_spellings"], [])
        edges = function["motion"]["edge_options"]["leading_tone"]
        bad_edges = [e for e in edges if e["source_ref"] == bad["sound_ref"]]
        self.assertTrue(bad_edges)
        self.assertTrue(all(e["qualified"] is False for e in bad_edges))
        for edge in bad_edges:
            self.assertIn("source_attack_lineage_not_passed:" + bad["sound_ref"], edge["blockers"])
            self.assertIn("involved_source_not_eligible:" + bad["sound_ref"], edge["blockers"])
        self.assertTrue(any(e["source_ref"] == healthy["sound_ref"] and e["qualified"] is True
                            for e in edges))
        self.assertTrue(function["motion"]["qualifying_bundle_refs"])
        for joint in function["motion"]["joint_options"]:
            self.assertTrue(all(link[0] != bad["sound_ref"] for link in joint["required_links"]))

    def test_invalid_evaluation_limits_precede_hypothesis_reads(self):
        for name in ("pair_budget", "overlay_pair_budget", "max_motion_pairs"):
            for value in (-1, True, 1.5, None, "1"):
                with self.subTest(name=name, value=value), \
                     patch.object(hypotheses, "validate_hypotheses", side_effect=AssertionError("no input read")):
                    with self.assertRaises(ValueError):
                        hypotheses.evaluate_hypotheses(None, None, None, **{name: value})

    def test_resealed_evaluation_row_bundle_or_promotion_tamper_rejected(self):
        fx = self.fixture()
        proposed = self.build(fx)
        original = self.evaluate(fx, proposed)
        for kind in ("row", "bundle", "promotion", "unknown"):
            forged = deepcopy(original)
            if kind == "row": forged["groups"][0]["rows"].pop()
            elif kind == "bundle": forged["bundle_inventory"].pop()
            elif kind == "promotion": forged["flags"]["resolution_confirmed"] = True
            else: forged["confidence"] = 0.99
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                hypotheses.validate_evaluation(*fx, proposed, reseal(forged, "fmehc_"))


if __name__ == "__main__":
    unittest.main()
