"""Authentic local contour/accounting hypotheses, never music verdicts."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_grounded_relations as grounded
from musicanote_harness import factor_indexed_hypotheses as indexed
from musicanote_harness import factor_musical_view as common
from musicanote_harness import factor_temporal_explanations as temporal
from musicanote_harness import harmony_factorized_voice_paths as geometry
from test_factor_grounded_relations import GroundedRelationsFixture
from test_factor_expanded_hypotheses import event, span
from test_factor_musical_view import reseal


class TemporalExplanationFixture(GroundedRelationsFixture):
    CAPS = ("max_geometry_candidates", "max_membership_relations", "max_new_bundles",
            "max_account_templates", "query_work_budget")

    def temporal_case(self, case=None):
        case = self.frozen_case(case)
        grounding = grounded.build_grounding(*case[0], *case[1:])
        return (*case[0], *case[1:], grounding)

    def ready(self, name="passing", **caps):
        cls = type(self)
        if name not in cls._cases:
            factory = cls._factory
            if name == "passing":
                case = factory.make([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                    [event("C3", 0, 4)], [event("G3", 0, 4)]])
            elif name == "neighbor":
                case = factory.make([[event("C4", 0, 1), event("D4", 1, 1), event("C4", 2, 2)],
                    [event("E3", 0, 4)], [event("G3", 0, 4)]])
            elif name == "branching":
                case = factory.make([[event("C4", 0, 1), event("D4", 1, 1), event(["C4", "E4"], 2, 2)],
                    [event("C3", 0, 4)], [event("G3", 0, 4)]])
            elif name == "fractional":
                case = factory.make([[event("C4", 0, Fraction(1, 3)), event("D4", Fraction(1, 3), Fraction(1, 3)),
                    event("E4", Fraction(2, 3), Fraction(10, 3))], [event("C3", 0, 4)], [event("G3", 0, 4)]])
            elif name == "member_competitor":
                case = factory.make([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                    [event("C3", 0, 4)], [event("G3", 0, 4)], [event("B-3", 0, 4)]])
            elif name == "pooled_not_simultaneous":
                case = factory.make([[event(["C4", "E4"], 0, 2), event(["G4", "B-4"], 2, 2)]])
            elif name == "broken_chord":
                case = factory.make([[event("C4", 0, 1), event("E4", 1, 1), event("G4", 2, 2)]])
            elif name == "no_triples":
                case = factory.make([[event(["C3", "E4", "G4"], 0, 4)]])
            elif name == "empty":
                case = factory.make([[event("C3", 0, 4)]])
            else:
                raise AssertionError("unknown fixture")
            cls._cases[name] = factory.temporal_case(case)
        case = deepcopy(cls._cases[name])
        cache_key = (name, tuple(sorted(caps.items())))
        if cache_key not in cls._explanations:
            cls._explanations[cache_key] = temporal.build_explanations(*case, **caps)
        return case, deepcopy(cls._explanations[cache_key])

    def session(self, case, record):
        return temporal.prepare_explanations(*case, record)

    def query(self, case, record, *, descriptor=None, bundle=None, session=None):
        descriptor = descriptor or self.descriptor(case, extent=span(0, 4))
        bundle = bundle or record["bundle_inventory"][0]["record_id"]
        return temporal.query_descriptor_prepared(session or self.session(case, record), descriptor, bundle)

    def real(self, lanes, **options):
        case = self.temporal_case(self.make(lanes, **options))
        return case, temporal.build_explanations(*case)

    def assert_partition(self, account):
        self.assertEqual(set(account["note_time"]), set(temporal.CATEGORIES))
        self.assertEqual(sum((common.f(v) for v in account["note_time"].values()), Fraction()),
                         common.f(account["total_note_time"]))
        self.assertEqual(sum((common.f(v) for v in account["raw_note_time"].values()), Fraction()),
                         common.f(account["total_note_time"]))

    @staticmethod
    def descriptor(case, *, extent=None, root="C", members=None, clean=True):
        members = {(letter, Fraction()) for letter in "CEG"} if members is None else members
        for row in case[3]["profile_inventory"]:
            semantic = row["semantic_input"]
            if (extent is not None and semantic["span"] != extent) or semantic["root"] is None:
                continue
            if common.pitch_key(semantic["root"]) != (root, Fraction()):
                continue
            if semantic["members"] is None or {common.pitch_key(p) for p in semantic["members"]} != members:
                continue
            if clean and semantic["blockers"]:
                continue
            return row["record_id"]
        raise AssertionError("genuine requested supplier descriptor absent")


class TemporalExplanationTests(TemporalExplanationFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._factory = TemporalExplanationFixture()
        cls._factory.addCleanup = cls.addClassCleanup
        cls._factory.setUp()
        cls._cases, cls._explanations = {}, {}

    def test_new_typed_reproducible_record_has_exact_parents_and_no_input_aliases(self):
        case, record = self.ready()
        before = deepcopy((case, record))
        self.assertTrue(record["record_id"].startswith("fmte_"))
        self.assertEqual(record["scope_ref"], common.ref(case[1]))
        self.assertEqual(record["index_ref"], common.ref(case[3]))
        self.assertEqual(record["relations_ref"], common.ref(case[4]))
        self.assertEqual(record["grounding_ref"], common.ref(case[5]))
        self.assertEqual(temporal.build_explanations(*case), record)
        self.assertTrue(temporal.validate_explanations(*case, record))
        self.assertEqual((case, record), before)
        case[1]["sound_facts"][0]["source_clock_passed"] = False
        case[5]["profile_inventory"][0]["row_ids"].clear()
        self.assertEqual(record, before[1])

    def test_invalid_whole_limits_rejected_before_any_parent_validation(self):
        for field in self.CAPS:
            for value in (-1, True, 1.5, "1", None):
                with self.subTest(field=field, value=value), \
                        patch.object(grounded, "prepare_grounding", side_effect=AssertionError("no parent read")):
                    with self.assertRaises(ValueError):
                        temporal.build_explanations(None, None, None, None, None, None, **{field: value})

    def test_foreign_full_ir_scope_hypothesis_index_relation_and_grounding_fail(self):
        case, record = self.ready()
        other = self.temporal_case(self.make([[event(["C3", "E4", "G4"], 0, 4)]]))
        for position in range(6):
            foreign = list(case)
            foreign[position] = other[position]
            with self.subTest(position=position), self.assertRaises(ValueError):
                temporal.validate_explanations(*foreign, record)

    def test_required_closed_headers_and_resealed_extra_fields_are_not_authority(self):
        case, record = self.ready()
        for name in ("contract", "resource_limits", "summary", "flags", "scope_ref", "grounding_ref"):
            forged = deepcopy(record)
            del forged[name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.session(case, reseal(forged, "fmte_"))
        forged = deepcopy(record)
        forged["undeclared"] = True
        with self.assertRaises(ValueError):
            self.session(case, reseal(forged, "fmte_"))
        for malformed in (None, [], "not_explanations"):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                self.session(case, malformed)

    def test_resealed_numeric_limit_aliases_are_rejected(self):
        case, record = self.ready()
        for field in self.CAPS:
            forged = deepcopy(record)
            forged["resource_limits"][field] = float(forged["resource_limits"][field])
            with self.subTest(field=field), self.assertRaises(ValueError):
                temporal.validate_explanations(*case, reseal(forged, "fmte_"))

    def test_actual_passing_requires_both_links_in_one_new_complete_all_lane_bundle(self):
        case, record = self.ready()
        geometry_row = record["geometry_inventory"][0]
        bundle = record["bundle_inventory"][0]
        result = self.query(case, record)
        self.assertEqual(geometry_row["family"], "passing")
        self.assertEqual(bundle["status"], "complete_all_lane_witness")
        self.assertEqual({tuple(p) for p in bundle["materialized_witness_links"]},
                         {tuple(p) for p in geometry_row["required_links"]})
        self.assertEqual(len(bundle["entries"]), len(case[1]["raw_lanes"]))
        self.assertTrue(result["same_complete_all_lane_bundle"])
        account = result["account"]
        self.assertEqual(account["conditional_explanation_note_time"], common.q(1))
        self.assertEqual(account["raw_note_time"]["nonmember_not_confirmed_nct"], common.q(1))
        self.assertEqual(account["raw_note_time"]["member"], common.q(11))
        self.assertEqual(account["supported_geometry_refs"], [common.ref(geometry_row)])
        self.assert_partition(account)

    def test_neighbor_is_conditional_middle_only_and_metric_consonance_unassessed(self):
        case, record = self.ready("neighbor")
        row = record["geometry_inventory"][0]
        result = self.query(case, record)
        self.assertEqual(row["family"], "neighbor")
        self.assertEqual(row["accent"], "unassessed")
        self.assertEqual(row["consonance"], "unassessed")
        self.assertEqual(row["metric_role"], "unassessed")
        self.assertEqual(result["account"]["explained_intervals_by_sound"],
            [{"sound_ref": row["explained_sound_ref"], "spans": [span(1, 2)]}])
        self.assertFalse(result["flags"]["nct_confirmed"])

    def test_inherited_no_link_control_is_verbatim_and_has_zero_conditional_credit(self):
        case, record = self.ready()
        self.assertEqual(record["inherited_bundle_inventory"], case[5]["bundle_inventory"])
        baseline = next(b for b in record["inherited_bundle_inventory"] if b["all_no_link_control"])
        result = self.query(case, record, bundle=baseline["record_id"])
        self.assertEqual(result["bundle_origin"], "inherited_grounding_not_retargeted")
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(0))
        self.assertEqual(result["account"]["unexplained_nonmember_note_time"], common.q(1))
        self.assertEqual(result["account"]["supported_geometry_refs"], [])
        self.assert_partition(result["account"])

    def test_branching_neighbor_and_passing_are_alternative_completions_not_union(self):
        case, record = self.ready("branching")
        self.assertEqual({g["family"] for g in record["geometry_inventory"]}, {"passing", "neighbor"})
        self.assertEqual(len(record["bundle_inventory"]), 2)
        session = self.session(case, record)
        supported = []
        for bundle in record["bundle_inventory"]:
            result = self.query(case, record, bundle=bundle["record_id"], session=session)
            self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(1))
            self.assertEqual(len(result["account"]["supported_geometry_refs"]), 1)
            supported.extend(result["account"]["supported_geometry_refs"])
            self.assert_partition(result["account"])
        self.assertEqual(len({r["record_id"] for r in supported}), 2)
        required = tuple(sorted({tuple(p) for g in record["geometry_inventory"] for p in g["required_links"]}))
        conflict = temporal._new_bundle(case[1], case[3], case[5], record["logical_universe"], required, 100000)
        self.assertEqual(conflict["geometry_condition_status"], "impossible")
        self.assertNotEqual(conflict["status"], "complete_all_lane_witness")
        with self.assertRaises(ValueError):
            self.query(case, record, bundle=conflict["record_id"], session=session)

    def test_fractional_explanation_and_union_are_exact_not_rounded_or_added(self):
        case, record = self.ready("fractional")
        result = self.query(case, record)
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(Fraction(1, 3)))
        self.assertEqual(result["account"]["total_note_time"], common.q(12))
        self.assert_partition(result["account"])
        self.assertEqual(temporal._union([span(0, 1), span(Fraction(1, 3), 2), span(2, 3), span(0, 0)]), [span(0, 3)])

    def test_same_bundle_chord_member_competitor_gets_no_nct_credit_or_raw_reclassification(self):
        case, record = self.ready("member_competitor")
        c7 = self.descriptor(case, extent=span(0, 4), members={common.pitch_key(p)
            for p in [{"step": s, "alter": common.q(a)} for s, a in (("C", 0), ("E", 0), ("G", 0), ("B", -1))]})
        c9 = self.descriptor(case, extent=span(0, 4), members={common.pitch_key(p)
            for p in [{"step": s, "alter": common.q(a)} for s, a in (("C", 0), ("E", 0), ("G", 0), ("B", -1), ("D", 0))]})
        session = self.session(case, record)
        bundle = record["bundle_inventory"][0]["record_id"]
        a, b = [self.query(case, record, descriptor=d, bundle=bundle, session=session) for d in (c7, c9)]
        self.assertEqual(a["bundle_ref"], b["bundle_ref"])
        self.assertEqual(a["account"]["conditional_explanation_note_time"], common.q(1))
        self.assertEqual(b["account"]["conditional_explanation_note_time"], common.q(0))
        self.assertEqual(a["account"]["raw_note_time"]["nonmember_not_confirmed_nct"], common.q(1))
        self.assertEqual(b["account"]["raw_note_time"]["nonmember_not_confirmed_nct"], common.q(0))

    def test_full_sound_spans_outside_partial_descriptor_are_not_clipped_into_rule_membership(self):
        case, record = self.ready()
        did = self.descriptor(case, extent=span(0, 2))
        result = self.query(case, record, descriptor=did)
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(0))
        self.assertTrue(any("all_three_full_sound_spans_not_inside_descriptor" in row["blockers"]
                            for row in result["relation_assessments"]))
        self.assertEqual(result["presentation"]["span"], span(0, 2))

    def test_pooled_presentation_is_not_simultaneous_harmony_arpeggio_or_persistence(self):
        case, record = self.ready("pooled_not_simultaneous")
        did = self.descriptor(case, extent=span(0, 4), members={(s, Fraction(a)) for s, a in (("C", 0), ("E", 0), ("G", 0), ("B", -1))})
        baseline = record["inherited_bundle_inventory"][0]["record_id"]
        result = self.query(case, record, descriptor=did, bundle=baseline)
        presentation = result["presentation"]
        self.assertTrue(presentation["pooled_written_member_presence_complete"])
        self.assertTrue(presentation["pooled_guarded_member_presence_complete"])
        self.assertEqual(presentation["simultaneous_raw_core_spans"], [])
        self.assertEqual(presentation["simultaneous_guarded_core_spans"], [])
        self.assertEqual(presentation["arpeggio_and_chord_persistence"], "unassessed")
        self.assertFalse(result["flags"]["pooled_members_certify_harmony"])
        self.assertFalse(result["flags"]["arpeggio_confirmed"])
        self.assertFalse(result["flags"]["chord_persistence_confirmed"])

    def test_all_member_broken_chord_preserves_member_time_without_nct_or_arpeggio_verdict(self):
        case, record = self.ready("broken_chord")
        result = self.query(case, record, bundle=record["inherited_bundle_inventory"][0]["record_id"])
        self.assertEqual(record["summary"]["planned_new_bundles"], 0)
        self.assertEqual(result["account"]["raw_note_time"]["member"], common.q(4))
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(0))
        self.assertTrue(result["presentation"]["pooled_written_member_presence_complete"])
        self.assertEqual(result["presentation"]["simultaneous_raw_core_spans"], [])

    def test_overlapping_doubled_members_use_presence_union_not_additive_note_time(self):
        case, record = self.real([[event(["C3", "C4", "E4", "G4"], 0, 4)]])
        result = self.query(case, record, bundle=record["inherited_bundle_inventory"][0]["record_id"])
        c = next(r for r in result["presentation"]["members"] if r["member"]["step"] == "C")
        self.assertEqual(c["raw_presence_union"], [span(0, 4)])
        self.assertEqual(c["raw_presence_duration"], common.q(4))
        self.assertEqual(c["raw_additive_note_time"], common.q(8))
        self.assertEqual(result["account"]["total_note_time"], common.q(16))
        self.assert_partition(result["account"])

    def test_every_origin_restores_exact_frozen_profile_and_all_duplicate_origins_survive(self):
        case, record = self.ready()
        session = self.session(case, record)
        baseline = record["inherited_bundle_inventory"][0]["record_id"]
        self.assertEqual(record["origin_inventory"], case[5]["origin_inventory"])
        self.assertEqual(record["catalog_inventory"], case[5]["catalog_inventory"])
        self.assertEqual(record["keys"], case[5]["keys"])
        by_descriptor = {}
        for row in case[3]["variant_inventory"]:
            result = temporal.query_origin_prepared(session, row["variant_id"], baseline)
            self.assertEqual(result["profile"], frozen._profile(case[1], row["variant"]))
            self.assertEqual(result["profile"]["segment_ref"], row["segment_ref"])
            self.assertEqual(result["descriptor_id"], row["profile_ref"]["record_id"])
            self.assert_partition(result["account"])
            by_descriptor.setdefault(result["descriptor_id"], []).append(row["variant_id"])
        self.assertTrue(any(len(ids) > 1 for ids in by_descriptor.values()))
        self.assertEqual(sum(len(ids) for ids in by_descriptor.values()), len(record["origin_inventory"]))

    def test_all_account_templates_and_weighted_groups_preserve_exact_raw_denominator(self):
        case, record = self.ready()
        accounts = {r["record_id"]: r for r in record["account_template_inventory"]}
        for account in accounts.values(): self.assert_partition(account)
        session = self.session(case, record)
        for item in record["bundle_weighted_accounts"]:
            bid = item["bundle_ref"]["record_id"]
            for group, stored in zip(record["path_groups"], item["accounts"]):
                raw = {state: Fraction() for state in frozen.catalog.STATES}
                note = {state: Fraction() for state in temporal.CATEGORIES}
                uses = 0
                for slot in group["temporal_descriptor_weights"]:
                    for row in slot["descriptor_weights"]:
                        weight = row["weighted_descriptor_uses"]
                        account = self.query(case, record, descriptor=row["descriptor_id"], bundle=bid, session=session)["account"]
                        uses += weight
                        for state in raw: raw[state] += common.f(account["raw_note_time"][state]) * weight
                        for state in note: note[state] += common.f(account["note_time"][state]) * weight
                self.assertEqual(stored["known_weighted_descriptor_uses"], uses)
                self.assertEqual(stored["weighted_raw_note_time"], {s: common.q(v) for s, v in raw.items()})
                self.assertEqual(stored["weighted_note_time"], {s: common.q(v) for s, v in note.items()})
                self.assertEqual(sum(raw.values()), sum(note.values()))
        self.assertEqual(record["summary"]["logical_paths"], case[5]["summary"]["logical_paths"])
        self.assertEqual(record["summary"]["logical_function_rows"], case[5]["summary"]["logical_function_rows"])

    def test_exact_ordered_members_and_span_identity_are_preserved_despite_same_pitch_classes(self):
        case, record = self.ready()
        original = {p["record_id"]: p for p in case[3]["profile_inventory"]}
        for row, presentation in zip(record["descriptor_inventory"], record["presentation_inventory"]):
            descriptor = original[row["descriptor_ref"]["record_id"]]
            self.assertEqual(row["semantic_input"], descriptor["semantic_input"])
            self.assertEqual(presentation["ordered_members"], descriptor["semantic_input"]["members"])
            self.assertEqual(presentation["span"], descriptor["semantic_input"]["span"])
        ids = [self.descriptor(case, extent=extent) for extent in (span(0, 4), span(0, 2))]
        self.assertNotEqual(*ids)

    def test_whole_geometry_budget_has_no_prefix_or_fake_empty_relation_denominator(self):
        case, full = self.ready("branching")
        count = full["summary"]["planned_geometry_candidates"]
        self.assertGreater(count, 1)
        for cap in (0, count - 1):
            record = temporal.build_explanations(*case, max_geometry_candidates=cap)
            self.assertEqual(record["summary"]["planned_geometry_candidates"], count)
            self.assertEqual(record["geometry_inventory"], [])
            self.assertEqual(record["membership_relation_inventory"], [])
            self.assertIsNone(record["summary"]["planned_membership_relations"])
            self.assertIsNone(record["summary"]["planned_new_bundles"])
            result = self.query(case, record, bundle=record["inherited_bundle_inventory"][0]["record_id"])
            self.assertIsNone(result["account"]["conditional_explanation_note_time"])
            self.assertEqual(result["account"]["note_time"]["unassessed_nonmember"], common.q(1))
            self.assert_partition(result["account"])
        exact = temporal.build_explanations(*case, max_geometry_candidates=count)
        self.assertEqual(len(exact["geometry_inventory"]), count)

    def test_whole_membership_relation_budget_retains_all_geometry_and_no_relation_prefix(self):
        case, full = self.ready()
        count = full["summary"]["planned_membership_relations"]
        for cap in (0, count - 1):
            held = temporal.build_explanations(*case, max_membership_relations=cap)
            self.assertEqual(held["geometry_inventory"], full["geometry_inventory"])
            self.assertEqual(held["membership_relation_inventory"], [])
            self.assertEqual(held["summary"]["planned_membership_relations"], count)
            self.assertIsNone(held["summary"]["conditional_contour_descriptor_pairs"])
            self.assertIsNone(held["summary"]["planned_new_bundles"])
        exact = temporal.build_explanations(*case, max_membership_relations=count)
        self.assertEqual(len(exact["membership_relation_inventory"]), count)

    def test_whole_new_bundle_budget_retains_every_request_without_favorable_prefix(self):
        case, full = self.ready("branching")
        count = full["summary"]["planned_new_bundles"]
        for cap in (0, count - 1):
            held = temporal.build_explanations(*case, max_new_bundles=cap)
            self.assertEqual(held["summary"]["planned_new_bundles"], count)
            self.assertEqual(held["bundle_inventory"], [])
            self.assertEqual(len(held["bundle_requests"]), count)
            self.assertTrue(all(r["bundle_ref"] is None for r in held["bundle_requests"]))
            self.assertEqual(held["inherited_bundle_inventory"], case[5]["bundle_inventory"])
        exact = temporal.build_explanations(*case, max_new_bundles=count)
        self.assertEqual(len(exact["bundle_inventory"]), count)

    def test_whole_account_budget_preserves_profiles_and_bundles_but_no_account_prefix(self):
        case, full = self.ready()
        count = full["summary"]["planned_account_templates"]
        for cap in (0, count - 1):
            held = temporal.build_explanations(*case, max_account_templates=cap)
            self.assertEqual(held["summary"]["planned_account_templates"], count)
            self.assertEqual(held["account_template_inventory"], [])
            self.assertEqual(held["bundle_inventory"], full["bundle_inventory"])
            result = self.query(case, held)
            self.assertIsNone(result["account"])
            self.assertIsNotNone(result["presentation"])
        exact = temporal.build_explanations(*case, max_account_templates=count)
        self.assertEqual(len(exact["account_template_inventory"]), count)

    def test_zero_query_work_budget_keeps_exact_closed_form_completion_not_false_unknown(self):
        case, record = self.ready(query_work_budget=0)
        self.assertEqual(record["summary"]["planned_new_bundles"], 1)
        self.assertEqual(record["summary"]["new_unknown_bundles"], 0)
        result = self.query(case, record)
        self.assertTrue(result["same_complete_all_lane_bundle"])
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(1))
        self.assert_partition(result["account"])

    def test_known_zero_geometry_and_empty_supplier_stay_zero_even_at_zero_caps(self):
        case, record = self.ready("no_triples", max_geometry_candidates=0, max_membership_relations=0,
                                  max_new_bundles=0)
        for name in ("planned_geometry_candidates", "planned_membership_pairs", "planned_membership_relations", "planned_new_bundles"):
            self.assertEqual(record["summary"][name], 0, name)
        empty, known = self.ready("empty", max_geometry_candidates=0, max_membership_relations=0,
                                  max_new_bundles=0, max_account_templates=0)
        self.assertEqual(known["summary"]["planned_profiles"], 0)
        self.assertEqual(known["summary"]["planned_account_templates"], 0)
        self.assertEqual(known["summary"]["origin_variants"], 0)
        self.assertTrue(known["summary"]["literal_presentation_inventory_complete"])

    def test_upstream_held_index_retains_known_origins_without_inventing_bundle_or_zero(self):
        case = self.temporal_case(self.make(index_options={"max_variants": 0}))
        record = temporal.build_explanations(*case)
        self.assertIsNone(record["summary"]["planned_profiles"])
        self.assertFalse(record["summary"]["literal_presentation_inventory_complete"])
        self.assertEqual(record["descriptor_inventory"], [])
        session = self.session(case, record)
        vid = next(v for g in case[3]["path_groups"] for slot in g["slots"] for v in slot["variant_ids"])
        self.assertEqual(record["inherited_bundle_inventory"], [])
        self.assertEqual(record["bundle_inventory"], [])
        self.assertEqual(record["summary"]["known_origin_variant_ids"],
                         len({v for g in case[3]["path_groups"] for slot in g["slots"] for v in slot["variant_ids"]}))
        self.assertIsNone(record["summary"]["planned_origin_variants"])
        result = temporal.query_origin_prepared(session, vid, None)
        self.assertIsNone(result["bundle_ref"])
        self.assertIsNone(result["descriptor_id"])
        self.assertIsNone(result["account"])
        self.assertIsNone(result["profile"])
        self.assertEqual(result["bundle_origin"], "no_admitted_actual_completion")
        self.assertFalse(result["same_complete_all_lane_bundle"])
        self.assertEqual(result["origin_variant_id"], vid)
        with self.assertRaisesRegex(ValueError, "registered_same_universe_bundle"):
            temporal.query_origin_prepared(session, vid, "unavailable-not-a-bundle")
        self.assertEqual(record["summary"]["logical_paths"], case[3]["summary"]["logical_paths"])

    def test_profile_budget_hold_retains_descriptor_ids_presentations_and_unknown_credit(self):
        case, _ = self.ready()
        case = list(case)
        case[5] = grounded.build_grounding(*case[:5], max_profiles=0)
        record = temporal.build_explanations(*case)
        self.assertEqual(len(record["descriptor_inventory"]), len(case[3]["profile_inventory"]))
        self.assertFalse(record["summary"]["literal_presentation_inventory_complete"])
        self.assertIsNone(record["summary"]["planned_membership_relations"])
        self.assertEqual(record["inherited_bundle_inventory"], [])
        self.assertEqual(record["account_template_inventory"], [])
        self.assertTrue(all(p["status"] == "upstream_literal_profile_unavailable" for p in record["presentation_inventory"]))
        self.assertTrue(all(p["members"] is None for p in record["presentation_inventory"]))
        session = self.session(case, record)
        result = temporal.query_descriptor_prepared(session, self.descriptor(case, extent=span(0, 4)), None)
        self.assertIsNone(result["account"])
        self.assertIsNone(result["bundle_ref"])
        self.assertEqual(result["presentation"]["status"], "upstream_literal_profile_unavailable")

    def test_silence_gap_has_no_fake_sorted_adjacency_chain(self):
        case, record = self.real([[event("C4", 0, 1), event(None, 1, 1), event("D4", 2, 1), event("E4", 3, 1)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)]])
        self.assertEqual(record["summary"]["planned_geometry_candidates"], 0)
        self.assertEqual(record["summary"]["planned_new_bundles"], 0)

    def test_cross_raw_lanes_do_not_repair_missing_chain_edges(self):
        case, record = self.real([[event("C4", 0, 1), event("D4", 1, 1), event(None, 2, 2)],
                                  [event(None, 0, 2), event("E4", 2, 2)], [event("C3", 0, 4)], [event("G3", 0, 4)]])
        self.assertEqual(record["summary"]["planned_geometry_candidates"], 0)
        self.assertEqual(record["summary"]["planned_new_bundles"], 0)

    def test_cross_staff_same_raw_voice_is_not_mistaken_for_cross_lane(self):
        def cross_staff(ir):
            second = {}
            for staff in list(ir["staves"]):
                extra = {**deepcopy(staff), "staff_id": staff["staff_id"] + "_cross", "staff_number": 2}
                ir["staves"].append(extra)
                second[staff["staff_id"]] = extra["staff_id"]
                next(p for p in ir["parts"] if p["part_id"] == staff["part_id"])["staff_ids"].append(extra["staff_id"])
            for note in ir["note_events"]:
                if common.f(note["global_onset_quarter"]) >= 1: note["display_staff_id"] = second[note["display_staff_id"]]
        case, record = self.real([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)]], modify=cross_staff)
        self.assertEqual(self.query(case, record)["account"]["conditional_explanation_note_time"], common.q(1))

    def test_full_tie_is_one_sound_and_continuation_is_not_a_new_attack(self):
        case, record = self.real([[event("C4", 0, 1, tie_role="start"), event("C4", 1, 1, tie_role="stop"),
                                  event("D4", 2, 1), event("E4", 3, 1)], [event("C3", 0, 4)], [event("G3", 0, 4)]], extent=span(2, 3))
        tied = next(s for s in case[1]["sound_facts"] if len(s["source_note_refs"]) == 2)
        self.assertEqual(tied["span"], span(0, 2))
        self.assertEqual(record["summary"]["planned_geometry_candidates"], 1)
        result = self.query(case, record)
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(1))
        observation = next(o for m in result["presentation"]["members"] for o in m["observations"] if o["sound_ref"] == tied["sound_ref"])
        self.assertEqual(observation["actual_attack_time"], common.q(0))
        self.assertEqual(observation["source_note_refs"], tied["source_note_refs"])

    def test_presentation_clip_start_does_not_relabel_full_source_attack_time(self):
        case, record = self.ready()
        did = self.descriptor(case, extent=span(1, 4))
        result = self.query(case, record, descriptor=did)
        bass = next(o for m in result["presentation"]["members"] for o in m["observations"]
                    if o["full_span"] == span(0, 4))
        self.assertEqual(bass["actual_attack_time"], common.q(0))
        self.assertEqual(bass["first_observed_time"], common.q(1))
        self.assertEqual(bass["observed_span"], span(1, 4))

    def test_wrong_register_enharmonic_and_chromatic_unison_remain_unsupported_geometry(self):
        for pitches in (("C4", "D5", "E4"), ("C4", "D4", "B#3"), ("C4", "C#4", "C4")):
            case, record = self.real([[event(pitches[0], 0, 1), event(pitches[1], 1, 1), event(pitches[2], 2, 2)],
                                      [event("C3", 0, 4)], [event("G3", 0, 4)]])
            with self.subTest(pitches=pitches):
                self.assertEqual(record["summary"]["planned_geometry_candidates"], 1)
                self.assertEqual(record["geometry_inventory"][0]["family"], "passing_neighbor_unsupported")
                self.assertEqual(record["summary"]["planned_new_bundles"], 0)

    def test_missing_middle_attack_is_not_rescued_by_healthy_doubled_pitch(self):
        def missing_attack(ir):
            bad = next(s for s in ir["sounding_events"] if s["pitch"]["spelling"] == "D4")
            ir["attack_events"] = [a for a in ir["attack_events"] if a["sounding_event_id"] != bad["sounding_event_id"]]
        case, record = self.real([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)], [event("D5", 0, 4)]],
                                 extent=span(2, 3), modify=missing_attack)
        bad = next(s for s in case[1]["sound_facts"] if s["pitch"]["spelling"] == "D4")
        self.assertFalse(bad["source_attack_consistency_passed"])
        geom = record["geometry_inventory"][0]
        self.assertTrue(any("source_attack" in reason for reason in geom["blockers"]))
        self.assertEqual(record["summary"]["planned_new_bundles"], 0)
        did = self.descriptor(case, extent=span(0, 4), clean=False)
        result = self.query(case, record, descriptor=did, bundle=record["inherited_bundle_inventory"][0]["record_id"])
        self.assertEqual(result["account"]["note_time"]["source_or_hypothesis_unsupported"], common.q(1))
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(0))

    def test_point_grace_lane_is_preserved_and_prevents_fake_complete_positive_bundle(self):
        case, record = self.real([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)],
                                  [event(None, 0, 1), event("A4", 1, 0, grace=True), event(None, 1, 3)]], extent=span(2, 3))
        points = [s["sound"] for s in record["source_inventory"] if s["sound"]["point"]]
        self.assertEqual(len(points), 1)
        self.assertTrue(points[0]["grace"])
        self.assertIsNone(record["summary"]["planned_geometry_candidates"])
        self.assertIsNone(record["summary"]["planned_new_bundles"])
        did = self.descriptor(case, extent=span(0, 4), clean=False)
        result = self.query(case, record, descriptor=did, bundle=record["inherited_bundle_inventory"][0]["record_id"])
        self.assertFalse(result["same_complete_all_lane_bundle"])
        self.assertIsNone(result["account"]["conditional_explanation_note_time"])
        self.assert_partition(result["account"])

    def test_owned_prepared_inputs_and_queries_are_detached_from_caller_mutations(self):
        case, record = self.ready()
        supplier = temporal.prepare_inputs(*case)
        session = self.session(case, record)
        bundle = record["bundle_inventory"][0]["record_id"]
        did = self.descriptor(case, extent=span(0, 4))
        expected = self.query(case, record, descriptor=did, bundle=bundle, session=session)
        case[1]["sound_facts"][0]["source_clock_passed"] = False
        case[5]["profile_inventory"].clear()
        record["account_template_inventory"].clear()
        built = temporal.build_explanations_prepared(supplier)
        self.assertEqual(built, self._explanations[("passing", ())])
        expected["account"]["raw_note_time"]["member"] = common.q(1000)
        fresh = temporal.query_descriptor_prepared(session, did, bundle)
        self.assertEqual(fresh["account"]["raw_note_time"]["member"], common.q(11))

    def test_prepared_session_must_be_internally_issued_and_owned_state_authenticated(self):
        case, record = self.ready()
        session = self.session(case, record)
        did, bid = self.descriptor(case, extent=span(0, 4)), record["bundle_inventory"][0]["record_id"]
        for fake in (None, {}, object(), temporal._PreparedExplanations()):
            with self.subTest(fake=type(fake).__name__), self.assertRaises(ValueError):
                temporal.query_descriptor_prepared(fake, did, bid)
        state = temporal._SESSIONS[session]
        changed = temporal._State(state.data, state.lookups, state.contract_sha256, b"not-authenticated")
        temporal._SESSIONS[session] = changed
        try:
            with self.assertRaises(ValueError): temporal.query_descriptor_prepared(session, did, bid)
        finally:
            temporal._SESSIONS[session] = state

    def test_strict_selector_types_and_foreign_bundle_descriptor_origin_fail(self):
        case, record = self.ready()
        session = self.session(case, record)
        did, bid = self.descriptor(case, extent=span(0, 4)), record["bundle_inventory"][0]["record_id"]
        vid = case[3]["variant_inventory"][0]["variant_id"]
        for value in (None, True, 1, 1.0, [], {}, "foreign"):
            with self.subTest(selector=value):
                with self.assertRaises(ValueError): temporal.query_descriptor_prepared(session, value, bid)
                with self.assertRaises(ValueError): temporal.query_descriptor_prepared(session, did, value)
                with self.assertRaises(ValueError): temporal.query_origin_prepared(session, value, bid)
        other, foreign = self.ready("neighbor")
        with self.assertRaises(ValueError): temporal.query_descriptor_prepared(session, did, foreign["bundle_inventory"][0]["record_id"])
        self.assertIsNotNone(temporal.query_origin_prepared(session, vid, bid)["profile"])

    def test_current_producer_bytes_invalidate_prepared_sessions_and_public_replay(self):
        case, record = self.ready()
        session = self.session(case, record)
        original = Path.read_bytes
        target = Path(temporal.__file__)
        def changed(path):
            raw = original(path)
            return raw + b"\n# simulated new producer" if path == target else raw
        with patch.object(Path, "read_bytes", changed):
            with self.assertRaises(ValueError): self.query(case, record, session=session)
            with self.assertRaises(ValueError): temporal.validate_explanations(*case, record)

    def test_caller_mutation_during_parent_validation_is_detected(self):
        case, _ = self.ready()
        original = grounded.prepare_grounding
        def mutate(*owned):
            result = original(*owned)
            case[0]["note_events"][0]["notation"]["temporal_test_mutation"] = True
            return result
        with patch.object(grounded, "prepare_grounding", side_effect=mutate), self.assertRaises(ValueError):
            temporal.prepare_inputs(*case)

    def test_resealed_geometry_membership_presentation_account_weights_and_bundle_metadata_fail(self):
        case, record = self.ready()
        changes = {
            "geometry": lambda r: r["geometry_inventory"][0]["required_links"].clear(),
            "membership": lambda r: r["membership_relation_inventory"][0]["descriptor_ids"].clear(),
            "presentation": lambda r: r["presentation_inventory"][0].update(
                pooled_written_member_presence_complete=not r["presentation_inventory"][0]["pooled_written_member_presence_complete"]),
            "account": lambda r: r["account_template_inventory"][0].update(total_note_time=common.q(1000)),
            "weights": lambda r: r["path_groups"][0]["temporal_descriptor_weights"][0]["descriptor_weights"][0].update(weighted_descriptor_uses=1000),
            "bundle": lambda r: r["bundle_inventory"][0].update(comparison_key_refs=[]),
            "origin": lambda r: r["origin_inventory"].pop(),
            "summary": lambda r: r["summary"].update(logical_paths=0),
            "source": lambda r: r["source_inventory"][0]["sound"].update(source_attack_consistency_passed=False),
            "flags": lambda r: r["flags"].update(nct_confirmed=True),
        }
        for name, change in changes.items():
            forged = deepcopy(record)
            change(forged)
            with self.subTest(name=name), self.assertRaises(ValueError):
                temporal.validate_explanations(*case, reseal(forged, "fmte_"))

    def test_resealed_query_or_foreign_result_cannot_promote_raw_or_supported_geometry(self):
        case, record = self.ready()
        did, bid = self.descriptor(case, extent=span(0, 4)), record["bundle_inventory"][0]["record_id"]
        result = self.query(case, record)
        self.assertTrue(temporal.validate_descriptor_query(*case, record, did, bid, result))
        changed = deepcopy(result)
        changed["account"]["conditional_explanation_note_time"] = common.q(2)
        with self.assertRaises(ValueError):
            temporal.validate_descriptor_query(*case, record, did, bid, reseal(changed, "fmtequery_"))

    def test_prepared_query_does_not_rebuild_profiles_candidate_paths_or_geometry(self):
        case, record = self.ready()
        session = self.session(case, record)
        with patch.object(frozen, "_profile", side_effect=AssertionError("profile rebuild")), \
                patch.object(indexed, "query_prepared", side_effect=AssertionError("path evaluation")), \
                patch.object(grounded, "prepare_grounding", side_effect=AssertionError("parent replay")), \
                patch.object(geometry, "query", side_effect=AssertionError("geometry re-evaluation")):
            result = self.query(case, record, session=session)
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(1))

    def test_no_selection_accuracy_training_boundary_delayed_or_full_path_claims(self):
        case, record = self.ready()
        self.assertIsNone(record["selected"])
        self.assertIsNone(record["rank"])
        self.assertIsNone(record["confidence"])
        self.assertEqual(record["summary"]["boundary_NCT_rules_computed"], 0)
        self.assertEqual(record["summary"]["delayed_chains_computed"], 0)
        self.assertEqual(record["summary"]["complete_path_harmony_evaluations"], 0)
        self.assertEqual(record["boundary_NCT_and_delayed_resolution"], "unassessed")
        self.assertTrue(all(value is False for value in record["flags"].values()))

    def test_genuine_microtone_is_retained_with_source_guards_and_no_ordinary_nct_credit(self):
        def microtone(ir):
            note = next(n for n in ir["note_events"] if n["written_pitch"]["spelling"] == "D4")
            for field in ("written_pitch", "concert_pitch"):
                note[field].update(alter=common.q(Fraction(1, 2)), spelling="D-half-sharp4", midi_pitch=None, pitch_class=None)
            sound = next(s for s in ir["sounding_events"] if note["note_id"] in s["source_note_ids"])
            sound["pitch"] = deepcopy(note["written_pitch"])
        case, record = self.real([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)]], extent=span(2, 3), modify=microtone)
        fact = next(s for s in case[1]["sound_facts"] if common.f(s["pitch"]["alter"]) == Fraction(1, 2))
        self.assertTrue(fact["source_pitch_consistency_passed"])
        self.assertFalse(fact["eligible_as_analysis_source"])
        self.assertEqual(next(s["sound"] for s in record["source_inventory"] if s["sound"]["sound_ref"] == fact["sound_ref"]), fact)
        self.assertEqual(record["summary"]["planned_geometry_candidates"], 1)
        self.assertEqual(record["summary"]["planned_new_bundles"], 0)
        self.assertNotEqual(record["geometry_inventory"][0]["status"], "conditional_contour_geometry")

    def test_full_source_tie_clock_gap_cannot_be_explained_by_locally_touching_geometry(self):
        case, record = self.real([[event("C4", 0, 1, tie_role="start"),
                                  event("C4", Fraction(3, 2), Fraction(1, 2), tie_role="stop"),
                                  event("D4", 2, 1), event("E4", 3, 1)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)]], extent=span(2, 3))
        tied = next(s for s in case[1]["sound_facts"] if len(s["source_note_refs"]) == 2)
        self.assertFalse(tied["source_clock_passed"])
        self.assertIn("full_source_timeline_gap", tied["source_diagnostics"])
        self.assertEqual(record["summary"]["planned_new_bundles"], 0)
        self.assertTrue(any("source_clock" in reason for g in record["geometry_inventory"] for reason in g["blockers"]))
        did = self.descriptor(case, extent=span(0, 4), clean=False)
        result = self.query(case, record, descriptor=did, bundle=record["inherited_bundle_inventory"][0]["record_id"])
        self.assertGreaterEqual(common.f(result["account"]["note_time"]["source_or_hypothesis_unsupported"]), 2)
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(0))
        self.assert_partition(result["account"])

    def test_full_source_written_pitch_mismatch_is_preserved_not_repaired(self):
        def mismatch(ir):
            sound = next(s for s in ir["sounding_events"] if s["pitch"]["spelling"] == "D4")
            sound["pitch"]["octave"] += 1
            sound["pitch"]["spelling"] = "D5"
            sound["pitch"]["midi_pitch"] += 12
        case, record = self.real([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)]], extent=span(2, 3), modify=mismatch)
        bad = next(s for s in case[1]["sound_facts"] if s["pitch"]["spelling"] == "D5")
        self.assertFalse(bad["source_pitch_consistency_passed"])
        self.assertFalse(bad["eligible_as_analysis_source"])
        self.assertEqual(next(s["sound"] for s in record["source_inventory"] if s["sound"]["sound_ref"] == bad["sound_ref"]), bad)
        self.assertTrue(any("pitch" in reason for g in record["geometry_inventory"] for reason in g["blockers"]))
        self.assertEqual(record["summary"]["planned_new_bundles"], 0)

    def test_genuine_unresolved_supplier_preserves_raw_unknown_time_without_false_membership(self):
        case, record = self.real([[event(["E4", "G4"], 0, 4)]])
        unknown = next(d for d in record["descriptor_inventory"] if d["semantic_input"]["members"] is None)
        result = self.query(case, record, descriptor=unknown["descriptor_ref"]["record_id"],
                            bundle=record["inherited_bundle_inventory"][0]["record_id"])
        self.assertIsNone(result["presentation"]["ordered_members"])
        self.assertIsNone(result["presentation"]["pooled_written_member_presence_complete"])
        self.assertEqual(result["account"]["raw_note_time"]["spelling_unresolved"], common.q(8))
        self.assertEqual(result["account"]["raw_note_time"]["member"], common.q(0))
        self.assertEqual(result["account"]["conditional_explanation_note_time"], common.q(0))
        self.assertEqual(result["account"]["note_time"]["source_or_hypothesis_unsupported"], common.q(8))
        self.assert_partition(result["account"])

    def test_five_declared_key_assumptions_survive_with_exact_weighted_multiplicity_not_collapsed(self):
        case, record = self.real([[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)],
                                  [event("C3", 0, 4)], [event("G3", 0, 4)]],
                                 signatures=[{"fifths": 0, "mode_hint": None}])
        self.assertEqual(len(record["keys"]), 5)
        self.assertEqual(record["keys"], case[3]["keys"])
        self.assertEqual(record["summary"]["logical_path_key_tuples"], record["summary"]["logical_paths"] * 5)
        self.assertEqual(record["bundle_inventory"][0]["comparison_key_refs"], [common.ref(k) for k in record["keys"]])
        session = self.session(case, record)
        for group in record["path_groups"]:
            for position, slot in enumerate(group["temporal_descriptor_weights"]):
                other = 1
                for j, original in enumerate(group["slots"]):
                    if position != j: other *= len(original["variant_ids"])
                for weight in slot["descriptor_weights"]:
                    self.assertEqual(weight["weighted_descriptor_uses"], weight["origin_multiplicity"] * other * 5)
        group = next(g for g in record["path_groups"] if g["kind"] == "full_hold")
        expected = Fraction()
        bid = record["bundle_inventory"][0]["record_id"]
        for weight in group["temporal_descriptor_weights"][0]["descriptor_weights"]:
            account = self.query(case, record, descriptor=weight["descriptor_id"], bundle=bid, session=session)["account"]
            expected += common.f(account["conditional_explanation_note_time"]) * weight["weighted_descriptor_uses"]
        stored = next(a for item in record["bundle_weighted_accounts"] if item["bundle_ref"]["record_id"] == bid
                      for a in item["accounts"] if a["group_id"] == group["group_id"])
        self.assertGreater(expected, 0)
        self.assertEqual(stored["weighted_note_time"]["conditional_explained_nonmember"], common.q(expected))
        self.assertEqual(record["summary"]["complete_path_harmony_evaluations"], 0)

    def test_known_empty_group_has_exact_zero_weighted_time_not_unknown_missing_source_time(self):
        case, record = self.ready("empty", max_account_templates=0)
        self.assertEqual(record["summary"]["logical_paths"], 0)
        self.assertEqual(record["summary"]["logical_path_key_tuples"], 0)
        self.assertEqual(len(record["source_inventory"]), 1)
        self.assertEqual(record["source_inventory"], case[5]["source_inventory"])
        self.assertTrue(record["bundle_weighted_accounts"])
        for item in record["bundle_weighted_accounts"]:
            for account in item["accounts"]:
                self.assertEqual(account["logical_path_count"], 0)
                self.assertIsNotNone(account["weighted_note_time"])
                self.assertTrue(all(common.f(v) == 0 for v in account["weighted_note_time"].values()))
                self.assertTrue(all(common.f(v) == 0 for v in account["weighted_raw_note_time"].values()))
        held = self.temporal_case(self.make(index_options={"max_variants": 0}))
        unknown = temporal.build_explanations(*held)
        self.assertIsNone(unknown["summary"]["planned_profiles"])
        self.assertIsNone(unknown["summary"]["planned_descriptor_bundle_pairs"])
        self.assertFalse(unknown["summary"]["literal_presentation_inventory_complete"])


if __name__ == "__main__":
    unittest.main()
