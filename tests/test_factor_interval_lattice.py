"""Native interval suppliers and whole-scope multi-slot hypotheses.

The fixture mixin has no inherited tests.  Each cached fixture genuinely writes
synthetic MusicXML and parses it into Core before obtaining an expanded scope.
No source harmony labels, phrase results, corpus cold loads, or final musical
verdicts are inputs.  New native IDs are not fabricated legacy path authority.
"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from itertools import combinations
from math import prod
from pathlib import Path
import unittest
from unittest.mock import patch

from musicanote_harness import factor_interval_lattice as lattice
from musicanote_harness import factor_expanded_hypotheses as frozen
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_candidate_catalog as catalog
from test_factor_expanded_hypotheses import ExpandedHypothesisFixture, event, span
from test_factor_musical_view import reseal


class IntervalLatticeTests(ExpandedHypothesisFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = ExpandedHypothesisFixture()
        cls.factory.addCleanup = cls.addClassCleanup
        cls.factory.setUp()
        cls.cases, cls.records, cls.sessions = {}, {}, {}

    def setUp(self):
        # Composing the fixture avoids counting any old TestCase tests.
        pass

    def fixture(self, *args, **kwargs):
        return self.factory.fixture(*args, **kwargs)

    def case(self, name="three"):
        if name not in self.cases:
            first, second, end = Fraction(1), Fraction(2), Fraction(4)
            if name == "rational":
                first, second = Fraction(1, 3), Fraction(2, 3)
            durations = first, second - first, end - second
            lanes = [
                [event("D3", 0, durations[0]), event("D3", first, durations[1]), event("G3", second, durations[2])],
                [event("A3", 0, durations[0]), event("A3", first, durations[1]), event("D4", second, durations[2])],
                [event("F4", 0, durations[0]), event("F#4", first, durations[1]), event("G4", second, durations[2])],
                [event("D5", 0, durations[0]), event("C5", first, durations[1]), event("B4", second, durations[2])],
            ]
            if name == "tie":
                lanes.append([event("D4", 0, 1, tie_role="start"),
                              event("D4", 1, 1, tie_role="continue"),
                              event("D4", 2, 2, tie_role="stop")])
            elif name == "held":
                # Same sounding inventory as the tie fixture, fewer Core notes.
                lanes.append([event("D4", 0, 4)])
            elif name == "repeated":
                lanes = [[event(["C3", "E4", "G4"], 0, 1),
                          event(["C3", "E4", "G4"], 1, 1),
                          event(["C3", "E4", "G4"], 2, 2)]]
            elif name == "empty":
                # A single observed PC does not invent an inclusive chord origin.
                lanes = [[event("C3", 0, 4)]]
            elif name == "foreign":
                lanes[2][1] = event("F4", 1, 1)
            elif name == "fork":
                lanes[3][1] = event(["C5", "D5"], 1, 1)
            elif name == "first_wrong":
                lanes[2] = [event("F4", 0, 1), event("F#4", 1, 1),
                            event("A4", 2, Fraction(1, 2)), event("G4", Fraction(5, 2), Fraction(3, 2))]
            elif name not in ("three", "rational", "bad_attack"):
                raise AssertionError(name)
            def remove_critical_attack(ir):
                critical = next(s for s in ir["sounding_events"] if s["pitch"]["spelling"] == "F#4")
                ir["attack_events"] = [r for r in ir["attack_events"]
                                       if r["sounding_event_id"] != critical["sounding_event_id"]]
            self.cases[name] = self.fixture(lanes, signatures=[{"fifths": 0, "mode_hint": None}],
                                            extent=span(3, 4) if name == "bad_attack" else span(1, 2),
                                            modify=remove_critical_attack if name == "bad_attack" else None)
        return self.cases[name]

    def record(self, name="three", **caps):
        signature = (name, common.digest(lattice._contract()), tuple(sorted(caps.items())))
        if signature not in self.records:
            self.records[signature] = lattice.build_lattice(*self.case(name), **caps)
        return deepcopy(self.records[signature])

    def session(self, name="three"):
        signature = (name, common.digest(lattice._contract()))
        if signature not in self.sessions:
            self.sessions[signature] = lattice.prepare_lattice(*self.case(name), self.record(name))
        return self.sessions[signature]

    @staticmethod
    def pitch_key(value):
        return value["step"], common.f(value["alter"])

    @staticmethod
    def counted_rows(record):
        return {row["slots"]: row for row in record["universe"]["by_slot_count"]}

    def origins(self, record):
        return {o["record_id"]: o for e in record["catalog_inventory"] for o in e["origins"]}

    def origin(self, record, extent, root=None, members=None):
        entry = next(e for e in record["catalog_inventory"] if e["span"] == extent)
        if members is None:
            return entry["origins"][0]
        return next(o for o in entry["origins"] if o["root"] is not None
                    and self.pitch_key(o["root"]) == (root, Fraction())
                    and o["members"] is not None
                    and {self.pitch_key(p) for p in o["members"]} == members)

    def selector(self, name="three", *, unknown=False, quality="M"):
        record = self.record(name)
        first, second = (Fraction(1, 3), Fraction(2, 3)) if name == "rational" else (Fraction(1), Fraction(2))
        specifications = [(span(0, first), "D", {("D", Fraction()), ("F", Fraction()), ("A", Fraction())}),
                          (span(first, second), "D", {("D", Fraction()), ("F", Fraction(1)),
                                                       ("A", Fraction()), ("C", Fraction())}),
                          (span(second, 4), "G", {("G", Fraction()), ("B", Fraction()), ("D", Fraction())})]
        origins = [self.origin(record, extent, root, members) for extent, root, members in specifications]
        key = next(k for k in record["keys"]
                   if k["segments"][0]["mode"] == ("unknown" if unknown else "major"))
        return {"origin_ids": [o["record_id"] for o in origins], "key_id": key["record_id"],
                "transition_assumptions": [None, {"family": "V7", "quality": quality}]}

    def sound(self, name, spelling, onset):
        return next(s for s in self.case(name)[1]["sound_facts"] if s["pitch"]["spelling"] == spelling
                    and common.f(s["span"]["start"]) == onset)

    def required(self, name="three"):
        first, second = (Fraction(1, 3), Fraction(2, 3)) if name == "rational" else (Fraction(1), Fraction(2))
        return [[self.sound(name, "F#4", first)["sound_ref"], self.sound(name, "G4", second)["sound_ref"]],
                [self.sound(name, "C5", first)["sound_ref"], self.sound(name, "B4", second)["sound_ref"]]]

    def bundle(self, name="three", *, control=False, required=None, **caps):
        return lattice.compile_bundle_prepared(self.session(name),
                                               [] if control else self.required(name) if required is None else required,
                                               **caps)

    def compare(self, name="three", *, control=False, selectors=None, bundle=None, **caps):
        bundle = bundle or self.bundle(name, control=control)
        return lattice.compare_prepared(self.session(name), selectors or [self.selector(name)],
                                        bundle["record_id"], **caps)

    def test_native_lattice_reproducible_exact_scope_and_source_binding(self):
        case = self.case()
        before = deepcopy(case)
        record = self.record()
        self.assertTrue(record["record_id"].startswith("fmilat_"))
        self.assertEqual(record["scope_ref"], common.ref(case[1]))
        self.assertEqual(record["binding"], case[1]["binding"])
        self.assertEqual(record["analysis_span"], case[1]["analysis_span"])
        self.assertEqual(lattice.build_lattice(*case), record)
        self.assertEqual(case, before)
        self.assertIs(lattice.validate_lattice(*case, record), True)

    def test_all_literal_cut_coordinates_not_invented_metric_points(self):
        record = self.record()
        self.assertEqual(record["coordinate_times"], [common.q(t) for t in (0, 1, 2, 4)])
        self.assertNotIn(common.q(3), record["coordinate_times"])

    def test_every_positive_interval_has_a_fresh_exact_supplier(self):
        ir, scope = self.case()
        record = self.record()
        self.assertCountEqual([entry["span"] for entry in record["catalog_inventory"]],
                              [span(a, b) for a, b in combinations((0, 1, 2, 4), 2)])
        for entry in record["catalog_inventory"]:
            with self.subTest(interval=entry["span"]):
                expected = catalog.propose(ir, entry["span"], scope["analysis_span"])
                self.assertEqual(entry["supplier_catalog"], expected)
                self.assertEqual(entry["candidate_count"], len(expected["candidates"]))
                self.assertIs(catalog.validate(expected)["passed"], True)

    def test_interior_interval_is_not_a_trimmed_prefix_or_suffix_catalog(self):
        case = self.case()
        old = frozen.build_hypotheses(*case, path_budget=1)
        middle = next(e for e in self.record()["catalog_inventory"] if e["span"] == span(1, 2))
        self.assertNotIn(middle["span"], [e["span"] for e in old["catalog_inventory"]])
        self.assertEqual(middle["supplier_catalog"], catalog.propose(case[0], span(1, 2), span(0, 4)))
        self.assertEqual(len(old["catalog_inventory"]), 5)
        self.assertEqual(len(self.record()["catalog_inventory"]), 6)

    def test_one_and_two_slot_supplier_music_equivalence_not_native_id_aliasing(self):
        old = frozen.build_hypotheses(*self.case(), path_budget=1)
        native = {common.digest(e["span"]): e for e in self.record()["catalog_inventory"]}
        for entry in old["catalog_inventory"]:
            self.assertEqual(native[common.digest(entry["span"])]["supplier_catalog"], entry["supplier_catalog"])
            self.assertEqual(native[common.digest(entry["span"])]["variant_count"], entry["variant_count"])
            self.assertNotEqual(native[common.digest(entry["span"])]["catalog_id"], entry["catalog_id"])

    def test_exact_rational_cuts_and_interior_span_survive(self):
        record = self.record("rational")
        self.assertEqual(record["coordinate_times"], [common.q(t) for t in (0, Fraction(1, 3), Fraction(2, 3), 4)])
        self.assertIn(span(Fraction(1, 3), Fraction(2, 3)), [e["span"] for e in record["catalog_inventory"]])

    def test_weighted_slot_dp_equals_independent_tiny_partition_oracle(self):
        record = self.record()
        times = [common.f(t) for t in record["coordinate_times"]]
        counts = {(common.f(e["span"]["start"]), common.f(e["span"]["end"])): e["variant_count"]
                  for e in record["catalog_inventory"]}
        rows = self.counted_rows(record)
        self.assertEqual(set(rows), {1, 2, 3})
        for slots in rows:
            skeletons = list(combinations(times[1:-1], slots - 1))
            paths = 0
            for cuts in skeletons:
                boundaries = [times[0], *cuts, times[-1]]
                paths += prod(counts[a, b] for a, b in zip(boundaries, boundaries[1:]))
            with self.subTest(slot_count=slots):
                self.assertEqual(rows[slots]["partition_skeletons"], len(skeletons))
                self.assertEqual(rows[slots]["logical_paths"], paths)
                self.assertEqual(rows[slots]["logical_path_keys"], paths * len(record["keys"]))
                self.assertEqual(rows[slots]["slot_occurrences"], paths * slots)
                self.assertEqual(rows[slots]["internal_transition_occurrences"], paths * (slots - 1))
                self.assertEqual(rows[slots]["internal_function_shape_rows"],
                                 paths * len(record["keys"]) * (slots - 1) * 10)
                self.assertEqual(rows[slots]["terminal_inclusive_function_shape_rows"],
                                 paths * len(record["keys"]) * slots * 10)

    def test_complete_partition_skeletons_not_candidate_or_key_counts(self):
        rows = self.counted_rows(self.record())
        self.assertEqual([rows[k]["partition_skeletons"] for k in (1, 2, 3)], [1, 2, 1])
        self.assertEqual(sum(r["partition_skeletons"] for r in rows.values()), 4)

    def test_known_empty_supplier_product_is_zero_not_unknown_or_neutral_origin(self):
        record = self.record("empty")
        self.assertEqual(record["coordinate_times"], [common.q(0), common.q(4)])
        entry = record["catalog_inventory"][0]
        self.assertEqual(entry["candidate_count"], 0)
        self.assertEqual(entry["variant_count"], 0)
        self.assertEqual(entry["origins"], [])
        row = self.counted_rows(record)[1]
        self.assertEqual(row["partition_skeletons"], 1)
        self.assertEqual(row["logical_paths"], 0)
        self.assertEqual(row["logical_path_keys"], 0)

    def test_unknown_supplier_weights_keep_known_skeletons_not_exact_zero_paths(self):
        record = self.record(max_catalogs=0)
        rows = self.counted_rows(record)
        self.assertEqual([rows[k]["partition_skeletons"] for k in (1, 2, 3)], [1, 2, 1])
        self.assertTrue(all(row["logical_paths"] is None and row["logical_path_keys"] is None
                            for row in rows.values()))
        self.assertEqual(record["universe"]["known_path_subtotal"], 0)
        self.assertEqual(record["universe"]["unknown_nonzero_skeletons"], 4)

    def test_zero_dp_budget_does_not_leave_an_admitted_origin_or_count_prefix(self):
        record = self.record(max_dp_work=0)
        self.assertTrue(record["reasons"])
        self.assertEqual(record["catalog_inventory"], [])
        self.assertEqual(record["universe"]["by_slot_count"], [])
        self.assertEqual(record["universe"]["partition_skeletons"], 4)
        self.assertIsNone(record["universe"]["logical_paths"])

    def test_signature_key_candidates_and_unknown_keep_exact_original_provenance(self):
        ir, scope = self.case()
        record = self.record()
        self.assertEqual(record["keys"], frozen._key_candidates(ir, scope))
        self.assertEqual(len(record["keys"]), 5)
        self.assertEqual(sum(k["segments"][0]["mode"] == "unknown" for k in record["keys"]), 1)
        for key in record["keys"]:
            self.assertIs(key["provenance"]["signature_is_not_key_proof"], True)
            self.assertIs(key["provenance"]["mode_hint_used_as_key"], False)

    def test_builder_integer_caps_reject_numeric_type_aliases_before_source_reads(self):
        for name in ("max_cut_coordinates", "max_catalogs", "max_variants", "max_dp_work"):
            for bad in (True, False, -1, 1.0, "1", None):
                with self.subTest(name=name, value=bad), self.assertRaises(ValueError):
                    lattice.build_lattice(None, None, **{name: bad})

    def test_builder_rejects_undeclared_limit_names(self):
        with self.assertRaises(TypeError):
            lattice.build_lattice(None, None, favorable_prefix=1)

    def test_catalog_preflight_hold_calls_no_supplier_and_keeps_every_interval(self):
        case = self.case()
        with patch.object(catalog, "propose", side_effect=AssertionError("catalog preflight precedes suppliers")):
            record = lattice.build_lattice(*case, max_catalogs=0)
        self.assertEqual(record["catalog_inventory"], [])
        self.assertEqual(record["planned_catalogs"], 6)
        self.assertEqual(record["catalog_inventory_representation"], "all_positive_coordinate_pairs_i_less_than_j")
        self.assertEqual(record["materialized_origins"], 0)
        self.assertTrue(record["reasons"])

    def test_variant_hold_preserves_all_suppliers_but_no_origin_prefix(self):
        record = self.record(max_variants=0)
        self.assertEqual(len(record["catalog_inventory"]), 6)
        self.assertTrue(all(e["supplier_catalog"] is not None for e in record["catalog_inventory"]))
        self.assertTrue(all(e["origins"] == [] for e in record["catalog_inventory"]))
        self.assertTrue(record["reasons"])
        for entry in record["catalog_inventory"]:
            self.assertEqual(entry["candidate_count"], len(entry["supplier_catalog"]["candidates"]))

    def test_cut_coordinate_hold_never_retains_a_favorable_interval_prefix(self):
        record = self.record(max_cut_coordinates=0)
        self.assertEqual(record["coordinate_times"], self.record()["coordinate_times"])
        self.assertTrue(record["reasons"])
        self.assertEqual(record["catalog_inventory"], [])
        self.assertEqual(record["planned_catalogs"], 6)
        self.assertIsNone(record["universe"]["logical_paths"])

    def test_prepare_caps_reject_aliases_before_any_owned_parent_is_created(self):
        for bad in (True, False, -1, 1.0, "0", None):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                lattice.prepare_lattice(None, None, max_catalogs=bad)

    def test_comparison_caps_reject_aliases_before_authentication_or_source_work(self):
        for name in ("max_hypotheses", "max_slots", "query_work_budget"):
            for bad in (True, False, -1, 1.0, "0", None):
                with self.subTest(name=name, value=bad), self.assertRaises(ValueError):
                    lattice.compare_prepared(None, [], None, **{name: bad})

    def test_geometry_bundle_budget_types_are_closed_integers(self):
        for bad in (True, False, -1, 1.0, "0", None):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                lattice.compile_bundle_prepared(None, geometry_work_budget=bad)

    def test_unissued_prepared_handle_has_no_authority(self):
        for forged in (None, True, object()):
            with self.subTest(forged=type(forged).__name__), self.assertRaises(ValueError):
                lattice.compare_prepared(forged, [], None)

    def test_resealed_lattice_cannot_promote_or_delete_an_interval(self):
        case = self.case()
        record = self.record()
        for mutate in (lambda r: r["catalog_inventory"].pop(),
                       lambda r: r["coordinate_times"].pop(1),
                       lambda r: r["keys"].pop(),
                       lambda r: r["flags"].update(final_harmony_confirmed=True)):
            forged = deepcopy(record)
            mutate(forged)
            with self.subTest(changed=common.digest(forged)), self.assertRaises(ValueError):
                lattice.prepare_lattice(*case, reseal(forged, lattice.PREFIX))

    def test_foreign_ir_scope_cannot_rebind_saved_native_lattice(self):
        with self.assertRaises(ValueError):
            lattice.prepare_lattice(*self.case("foreign"), self.record())

    def test_current_contract_source_change_invalidates_issued_session(self):
        session = self.session()
        original = Path.read_bytes
        def changed(path):
            return original(path) + b"\n" if path == Path(lattice.__file__) else original(path)
        with patch.object(Path, "read_bytes", changed), self.assertRaises(ValueError):
            lattice.compile_bundle_prepared(session)

    def test_lattice_builder_outputs_do_not_alias_inputs_or_previous_result(self):
        case = self.case()
        before = deepcopy(case)
        expected = self.record()
        output = lattice.build_lattice(*case)
        output["catalog_inventory"].clear()
        output["keys"].clear()
        self.assertEqual(case, before)
        self.assertEqual(lattice.build_lattice(*case), expected)

    def test_native_lattice_does_not_claim_final_music_or_source_annotation_truth(self):
        record = self.record()
        self.assertTrue(record["flags"])
        self.assertTrue(all(value is False for value in record["flags"].values()))
        for field in ("selected", "preferred", "winner", "rank", "confidence"):
            self.assertIsNone(record.get(field), field)
        self.assertTrue(all(e["supplier_catalog"]["source_labels_used"] is False
                            for e in record["catalog_inventory"]))

    def test_all_provider_origins_and_spelling_alternatives_have_exact_native_pointers(self):
        record = self.record()
        for entry in record["catalog_inventory"]:
            expected = [(candidate, n, alternative) for n, candidate in enumerate(entry["supplier_catalog"]["candidates"])
                        for alternative in (range(len(candidate["spelling_alternatives"]))
                                            if candidate["spelling_alternatives"] else [None])]
            self.assertEqual(len(entry["origins"]), len(expected))
            self.assertEqual(entry["variant_count"], len(expected))
            for origin, (candidate, index, alternative) in zip(entry["origins"], expected):
                self.assertTrue(origin["record_id"].startswith("fmilorigin_"))
                self.assertEqual(origin["span"], entry["span"])
                self.assertEqual(origin["catalog_id"], entry["catalog_id"])
                self.assertEqual(origin["supplier_candidate_ref"], candidate["candidate_id"])
                self.assertEqual(origin["supplier_record_pointer"], "/candidates/" + str(index))
                self.assertEqual(catalog.resolve(entry["supplier_catalog"], origin["supplier_record_pointer"]), candidate)
                self.assertEqual(origin["supplier_origin_pointer"], candidate["origin_pointer"])
                self.assertEqual(origin["spelling_alternative_index"], alternative)
                self.assertIs(origin["legacy_origin_rebound"], False)
                self.assertIs(origin["provenance"]["source_annotation_labels_used"], False)

    def test_equal_chord_spellings_at_distinct_spans_keep_distinct_native_origins(self):
        record = self.record("repeated")
        members = {("C", Fraction()), ("E", Fraction()), ("G", Fraction())}
        left = self.origin(record, span(0, 1), "C", members)
        middle = self.origin(record, span(1, 2), "C", members)
        self.assertEqual(left["root"], middle["root"])
        self.assertEqual(left["members"], middle["members"])
        self.assertNotEqual(common.ref(left), common.ref(middle))
        self.assertNotEqual(left["segment_id"], middle["segment_id"])

    def test_exact_lattice_caps_admit_every_origin_without_prefix_selection(self):
        full = self.record()
        exact = self.record(max_cut_coordinates=2, max_catalogs=6,
                            max_variants=full["origin_count"], max_dp_work=10)
        self.assertEqual(exact["status"], "ready_native_interval_lattice")
        self.assertEqual(exact["materialized_origins"], full["origin_count"])
        self.assertEqual(exact["catalog_inventory"], full["catalog_inventory"])
        self.assertEqual(exact["universe"], full["universe"])

    def test_owned_session_authentication_cannot_be_replaced_by_caller_state(self):
        session = self.session()
        original = lattice._SESSIONS[session]
        try:
            for forged in (replace(original), replace(original, authentication=b"\0" * 32),
                           replace(original, data={}), replace(original, lookups={})):
                lattice._SESSIONS[session] = forged
                with self.subTest(forgery=id(forged)), self.assertRaises(ValueError):
                    lattice.lattice_prepared(session)
        finally:
            lattice._SESSIONS[session] = original

    def test_preparation_rejects_input_mutation_after_genuine_validation_before_issuance(self):
        real_validate = lattice.validate_lattice
        for target in ("ir", "scope", "record"):
            ir, scope = deepcopy(self.case())
            record = self.record()
            before_sessions = set(lattice._SESSIONS)
            def validate_then_mutate(actual_ir, actual_scope, actual_record):
                result = real_validate(actual_ir, actual_scope, actual_record)
                {"ir": actual_ir, "scope": actual_scope, "record": actual_record}[target]["mutated_during_preparation"] = True
                return result
            with self.subTest(target=target), patch.object(lattice, "validate_lattice", validate_then_mutate):
                with self.assertRaisesRegex(ValueError, "inputs_or_contract_changed_during_preparation"):
                    lattice.prepare_lattice(ir, scope, record)
            self.assertEqual(set(lattice._SESSIONS), before_sessions)

    def test_source_size_budget_counts_tied_core_closure_not_only_same_sound_count(self):
        held, tied = self.compare("held"), self.compare("tie")
        held_scope, tied_scope = self.case("held")[1], self.case("tie")[1]
        self.assertEqual(len(held_scope["sound_facts"]), len(tied_scope["sound_facts"]))
        self.assertEqual(self.record("held")["coordinate_times"], self.record("tie")["coordinate_times"])
        held_plan, tied_plan = held["query_plan"], tied["query_plan"]
        for field in ("planned_boundary_observations", "planned_same_raw_lane_pairs", "planned_extreme_row_occurrences",
                      "planned_terminal_probe_occurrences", "planned_function_shape_rows",
                      "profile_intersection_visit_upper_bound", "ordinary_actual_route_visit_upper_bound"):
            self.assertEqual(held_plan[field], tied_plan[field], field)
        self.assertGreater(tied_plan["source_snapshot_inventory_items"], held_plan["source_snapshot_inventory_items"])
        self.assertGreater(tied_plan["source_snapshot_visit_units"], held_plan["source_snapshot_visit_units"])
        self.assertGreater(tied_plan["planned_query_work"], held_plan["planned_query_work"])
        held_capped = self.compare("held", query_work_budget=held_plan["planned_query_work"])
        tied_capped = self.compare("tie", query_work_budget=held_plan["planned_query_work"])
        self.assertEqual(len(held_capped["paths"]), 1)
        self.assertEqual(tied_capped["status"], "whole_comparison_hold")
        self.assertEqual(tied_capped["paths"], [])
        self.assertIn("whole_query_work_request_exceeds_budget_no_prefix", tied_capped["reasons"])
        self.assertEqual(tied_capped["logical_universe"], tied["logical_universe"])
        self.assertEqual(tied_capped["query_plan"], tied_plan)

    def test_comparison_rejects_selector_request_mutation_after_actual_path_computation(self):
        session, bundle = self.session(), self.bundle()
        selections = [self.selector()]
        unknown_key = self.selector(unknown=True)["key_id"]
        real_path = lattice._path
        def path_then_mutate(*args):
            result = real_path(*args)
            selections[0]["key_id"] = unknown_key
            return result
        with patch.object(lattice, "_path", path_then_mutate):
            with self.assertRaisesRegex(ValueError, "selector_request_changed_during_comparison"):
                lattice.compare_prepared(session, selections, bundle["record_id"])
        self.assertEqual(lattice.lattice_prepared(session), self.record())

    def test_one_registered_native_completion_covers_every_actual_raw_lane(self):
        bundle = self.bundle()
        scope = self.case()[1]
        self.assertTrue(bundle["record_id"].startswith("fmilbundle_"))
        self.assertEqual(bundle["status"], "complete_all_lane_witness")
        self.assertEqual(bundle["lattice_ref"], common.ref(self.record()))
        self.assertCountEqual(bundle["covered_lanes"], [[r["part_id"], r["voice_id"]] for r in scope["raw_lanes"]])
        self.assertEqual(len(bundle["entries"]), 4)
        self.assertCountEqual(bundle["materialized_witness_links"], self.required())
        actual = [pair for entry in bundle["entries"] for pair in entry["witness"]["assignment"]["links"]]
        self.assertCountEqual(actual, self.required())

    def test_genuine_three_chord_path_has_same_bundle_applied_resolution_premises(self):
        bundle = self.bundle()
        selection = self.selector()
        result = self.compare(bundle=bundle, selectors=[selection])
        path = result["paths"][0]
        self.assertEqual(path["partition"], [span(0, 1), span(1, 2), span(2, 4)])
        self.assertEqual(path["origin_refs"], [common.ref(self.origins(self.record())[ref]) for ref in selection["origin_ids"]])
        self.assertEqual(path["bundle_ref"], common.ref(bundle))
        arrival = path["transition_contexts"][1]
        self.assertEqual(arrival["function_shape"]["function_kind"], "applied")
        self.assertIs(arrival["joint_conditional_functional_evidence"], True)
        self.assertIs(arrival["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        roles = arrival["ordinary_strategy"]["role_assessments"]
        self.assertEqual({r["role"] for r in roles}, {"leading_tone", "seventh"})
        self.assertTrue(all(r["satisfied_under_this_bundle"] is True for r in roles))
        self.assertTrue(all(r["bundle_ref"] == common.ref(bundle) for r in path["transition_contexts"]))

    def test_ii_to_applied_dominant_step_is_not_forced_into_an_ordinary_resolution_rule(self):
        path = self.compare()["paths"][0]
        first = path["transition_contexts"][0]
        self.assertIsNone(first["function_shape"])
        self.assertIsNone(first["ordinary_strategy"])
        self.assertIsNone(first["joint_conditional_functional_evidence"])
        self.assertEqual(path["undeclared_transition_count"], 1)
        self.assertIs(path["all_transitions_functionally_assessed"], False)
        self.assertIs(path["all_declared_functional_prerequisites_under_same_bundle"], True)

    def test_unknown_registered_key_preserves_ordinary_routes_without_tonal_confirmation(self):
        path = self.compare(selectors=[self.selector(unknown=True)])["paths"][0]
        arrival = path["transition_contexts"][1]
        self.assertIs(arrival["ordinary_strategy"]["whole_ordinary_template_satisfied"], True)
        self.assertIsNone(arrival["joint_conditional_functional_evidence"])
        self.assertIsNone(arrival["prerequisite_axes"]["known_explicit_key_coordinate"])
        for boundary in path["boundaries"]:
            for inventory in (boundary["before_extremes"], boundary["arrival_extremes"]):
                self.assertTrue(all(r["candidate_scale_degree"]["coordinate"] is None for r in inventory["rows"]))

    def test_no_link_control_cannot_borrow_a_supporting_bundle_at_any_transition(self):
        good = self.compare()["paths"][0]
        control = self.bundle(control=True)
        held = self.compare(bundle=control)["paths"][0]
        self.assertEqual(control["materialized_witness_links"], [])
        arrival = held["transition_contexts"][1]
        self.assertIs(arrival["ordinary_strategy"]["whole_ordinary_template_satisfied"], False)
        self.assertIs(arrival["joint_conditional_functional_evidence"], False)
        self.assertNotEqual(good["bundle_ref"], held["bundle_ref"])
        self.assertEqual(held["whole_path_account"], good["whole_path_account"])

    def test_wrong_target_quality_is_retained_and_fails_shape_not_auto_repaired(self):
        path = self.compare(selectors=[self.selector(quality="m")])["paths"][0]
        arrival = path["transition_contexts"][1]
        self.assertEqual(arrival["function_shape"]["target_quality"], "m")
        self.assertIs(arrival["function_shape"]["target_shape_compatible"], False)
        self.assertIs(arrival["joint_conditional_functional_evidence"], False)

    def test_multi_slot_accounts_do_not_credit_provider_ornaments_as_joint_nct(self):
        result = self.compare()
        account = result["paths"][0]["whole_path_account"]
        self.assertIsNone(account["NCT_credited_note_time_quarters"])
        self.assertEqual(account["conditional_NCT_evaluation"], "not_integrated_into_native_lattice_yet")
        self.assertIs(account["provider_ornament_flags_are_not_explanation_credit"], True)
        self.assertIs(result["flags"]["provider_ornaments_used_as_joint_NCT_proof"], False)

    def test_fullhold_onecut_three_slot_competitors_conserve_same_whole_raw_note_time(self):
        record = self.record()
        three = self.selector()
        full = {"origin_ids": [self.origin(record, span(0, 4))["record_id"]],
                "key_id": three["key_id"], "transition_assumptions": []}
        two = {"origin_ids": [self.origin(record, span(0, 2))["record_id"],
                               self.origin(record, span(2, 4))["record_id"]],
               "key_id": three["key_id"], "transition_assumptions": [None]}
        result = self.compare(selectors=[full, two, three])
        self.assertEqual(len(result["paths"]), 3)
        for path in result["paths"]:
            account = path["whole_path_account"]
            self.assertEqual(account["raw_total_note_time_quarters"], common.q(16))
            self.assertEqual(account["slot_total_note_time_quarters"], common.q(16))
            self.assertIs(account["raw_time_conserved"], True)
            self.assertEqual(sum(map(common.f, account["raw_state_note_time_quarters"].values())), 16)
        self.assertIs(result["summary"]["raw_time_equal_between_competitors"], True)

    def test_one_tied_sound_crosses_two_boundaries_without_new_attacks_or_double_duration(self):
        scope = self.case("tie")[1]
        tied = next(s for s in scope["sound_facts"] if len(s["source_note_refs"]) == 3)
        path = self.compare("tie")["paths"][0]
        self.assertEqual(tied["span"], span(0, 4))
        self.assertEqual(path["whole_path_account"]["per_sound_slot_intersections"][tied["sound_ref"]],
                         [span(0, 1), span(1, 2), span(2, 4)])
        self.assertEqual(path["whole_path_account"]["raw_total_note_time_quarters"], common.q(20))
        rows = [row for profile in path["profiles"] for row in profile["rows"] if row["sound_ref"] == tied["sound_ref"]]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["full_span"] == span(0, 4) and row["state"] == "member" for row in rows))
        self.assertEqual(sum(common.f(row["observed_span"]["end"]) - common.f(row["observed_span"]["start"]) for row in rows), 4)
        for boundary in path["boundaries"][1:3]:
            literal = boundary["literal_observation"]
            self.assertIn(tied["sound_ref"], literal["full_sound_continuing_refs"])
            self.assertNotIn(tied["attack_note_ref"], literal["attack_note_refs_at"])

    def test_joint_branch_conflict_is_not_combined_from_individually_possible_requests(self):
        source = self.sound("fork", "D5", 0)["sound_ref"]
        first = self.sound("fork", "C5", 1)["sound_ref"]
        second = self.sound("fork", "D5", 1)["sound_ref"]
        left = self.bundle("fork", required=[[source, first]])
        right = self.bundle("fork", required=[[source, second]])
        both = self.bundle("fork", required=[[source, first], [source, second]])
        self.assertEqual(left["status"], "complete_all_lane_witness")
        self.assertEqual(right["status"], "complete_all_lane_witness")
        self.assertEqual(both["status"], "all_lane_witness_withheld")
        self.assertIn("required_branch_not_allowed", both["reasons"])
        path = self.compare("fork", bundle=both)["paths"][0]
        self.assertIs(path["transition_contexts"][1]["joint_conditional_functional_evidence"], False)

    def test_required_link_cannot_cross_raw_lanes_or_use_foreign_sound_ids(self):
        cross_lane = [self.sound("three", "F#4", 1)["sound_ref"], self.sound("three", "B4", 2)["sound_ref"]]
        foreign = ["sound_foreign", self.sound("three", "G4", 2)["sound_ref"]]
        for links in ([cross_lane], [foreign]):
            with self.subTest(links=links), self.assertRaises(ValueError):
                self.bundle(required=links)

    def test_closed_selector_and_transition_vectors_reject_aliases_and_missing_fields(self):
        selection = self.selector()
        bundle = self.bundle()
        malformed = []
        for modify in (lambda s: s.update(unknown=True), lambda s: s.pop("key_id"),
                       lambda s: s.update(origin_ids=tuple(s["origin_ids"])),
                       lambda s: s.update(transition_assumptions=[None]),
                       lambda s: s["transition_assumptions"].__setitem__(1, {"family": "V7", "quality": "M", "confirmed": True}),
                       lambda s: s["transition_assumptions"].__setitem__(1, {"family": "unsupported", "quality": "M"})):
            changed = deepcopy(selection)
            modify(changed)
            malformed.append(changed)
        for bad in malformed:
            with self.subTest(selector=bad), self.assertRaises(ValueError):
                self.compare(selectors=[bad], bundle=bundle, max_hypotheses=0)

    def test_complete_partition_rejects_gaps_reordering_overlaps_duplicates_and_foreign_origins(self):
        original = self.selector()
        record = self.record()
        cases = [list(reversed(original["origin_ids"])), original["origin_ids"][1:],
                 original["origin_ids"][:-1], [original["origin_ids"][0], original["origin_ids"][0], original["origin_ids"][2]],
                 [self.origin(record, span(0, 2))["record_id"], *original["origin_ids"][1:]],
                 ["fmilorigin_foreign", *original["origin_ids"][1:]]]
        for ids in cases:
            changed = {**deepcopy(original), "origin_ids": ids, "transition_assumptions": [None] * (len(ids) - 1)}
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.compare(selectors=[changed])

    def test_whole_comparison_caps_keep_request_and_universe_without_favorable_path_prefix(self):
        full = self.compare()
        work = full["summary"]["planned_query_work"]
        for caps in ({"max_hypotheses": 0}, {"max_slots": 2}, {"query_work_budget": 0},
                     {"query_work_budget": work - 1}):
            result = self.compare(**caps)
            with self.subTest(caps=caps):
                self.assertEqual(result["status"], "whole_comparison_hold")
                self.assertEqual(result["paths"], [])
                self.assertEqual(result["selectors"], full["selectors"])
                self.assertEqual(result["logical_universe"], full["logical_universe"])
                self.assertEqual(result["summary"]["planned_query_work"], work)
        exact = self.compare(max_hypotheses=1, max_slots=3, query_work_budget=work)
        self.assertEqual(exact["paths"], full["paths"])

    def test_raw_public_comparison_and_validator_reproduce_same_native_registered_bundle(self):
        record, bundle = self.record(), self.bundle()
        selectors = [self.selector()]
        expected = self.compare(selectors=selectors, bundle=bundle)
        result = lattice.compare(*self.case(), record, selectors, bundle)
        self.assertEqual(result, expected)
        self.assertIs(lattice.validate_comparison(*self.case(), record, selectors, bundle, result), True)
        changed = deepcopy(result)
        changed["paths"][0]["flags"]["cadence_confirmed"] = True
        with self.assertRaises(ValueError):
            lattice.validate_comparison(*self.case(), record, selectors, bundle,
                                        reseal(changed, lattice.COMPARISON_PREFIX))

    def test_registered_bundle_snapshot_not_mutable_return_or_foreign_session_body_is_authority(self):
        bundle = self.bundle()
        expected = self.compare(bundle=bundle)
        bundle["materialized_witness_links"].clear()
        self.assertEqual(self.compare(bundle=bundle), expected)
        with self.assertRaises(ValueError):
            lattice.compare_prepared(self.session("foreign"), [self.selector("foreign")], bundle["record_id"])
        original = lattice._BUNDLES[self.session()][bundle["record_id"]]
        try:
            lattice._BUNDLES[self.session()][bundle["record_id"]] = original[0], b"\0" * 32
            with self.assertRaises(ValueError):
                self.compare(bundle=bundle)
        finally:
            lattice._BUNDLES[self.session()][bundle["record_id"]] = original

    def test_prepared_owned_lattice_and_scope_are_detached_from_later_caller_mutation(self):
        session = self.session()
        expected = lattice.lattice_prepared(session)
        case = self.case()
        selection, bundle = self.selector(), self.bundle()
        before = deepcopy(case[1]["sound_facts"])
        try:
            case[1]["sound_facts"].clear()
            self.assertEqual(lattice.lattice_prepared(session), expected)
            result = lattice.compare_prepared(session, [selection], bundle["record_id"])
            self.assertEqual(result["paths"][0]["whole_path_account"]["raw_total_note_time_quarters"], common.q(16))
        finally:
            case[1]["sound_facts"][:] = before

    def test_first_adverse_changed_pitch_cannot_skip_a_later_correct_resolution(self):
        name = "first_wrong"
        links = [[self.sound(name, "F#4", 1)["sound_ref"], self.sound(name, "A4", 2)["sound_ref"]],
                 [self.sound(name, "A4", 2)["sound_ref"], self.sound(name, "G4", Fraction(5, 2))["sound_ref"]],
                 [self.sound(name, "C5", 1)["sound_ref"], self.sound(name, "B4", 2)["sound_ref"]]]
        bundle = self.bundle(name, required=links)
        path = self.compare(name, bundle=bundle)["paths"][0]
        role = next(r for r in path["transition_contexts"][1]["ordinary_strategy"]["role_assessments"]
                    if r["role"] == "leading_tone")
        occurrence = role["occurrences"][0]
        self.assertEqual(occurrence["endpoint_sound_ref"], self.sound(name, "A4", 2)["sound_ref"])
        self.assertNotIn(self.sound(name, "G4", Fraction(5, 2))["sound_ref"], occurrence["route_sound_refs"])
        self.assertIn("ordinary_role_first_change_motion_not_satisfied", occurrence["blockers"])
        self.assertIs(path["transition_contexts"][1]["joint_conditional_functional_evidence"], False)

    def test_missing_critical_source_attack_is_not_repaired_by_candidate_spellings(self):
        path = self.compare("bad_attack")["paths"][0]
        arrival = path["transition_contexts"][1]
        leading = next(r for r in arrival["ordinary_strategy"]["role_assessments"] if r["role"] == "leading_tone")
        self.assertIs(leading["satisfied_under_this_bundle"], False)
        self.assertTrue(leading["occurrences"][0]["blockers"])
        self.assertIs(arrival["joint_conditional_functional_evidence"], False)

    def test_cadence_shape_and_function_support_remain_distinct_unconfirmed_axes(self):
        good = self.compare()["paths"][0]
        control = self.compare(control=True)["paths"][0]
        for path in (good, control):
            self.assertEqual(len(path["function_shapes"]), 3)
            self.assertTrue(all(len(row["alternatives"]) == 10 for row in path["function_shapes"]))
            self.assertIs(path["function_shapes"][-1]["terminal"], True)
            self.assertEqual([b["boundary_time"] for b in path["boundaries"]], [common.q(t) for t in (0, 1, 2, 4)])
            self.assertTrue(all(c["confirmed"] is False for b in path["boundaries"] for c in b["cadence_prerequisites"].values()))
            self.assertIs(path["boundaries"][2]["cadence_prerequisites"]["HC"]["nominal_harmonic_and_literal_extreme_prerequisites"], True)
            self.assertTrue(all(value is False for value in path["flags"].values()))
            for boundary in path["boundaries"]:
                for inventory in (boundary["before_extremes"], boundary["arrival_extremes"]):
                    self.assertEqual(inventory["structural_bass"], "unassessed")
                    self.assertEqual(inventory["structural_melody"], "unassessed")

    def test_raw_comparison_caps_are_checked_before_expensive_preparation(self):
        with patch.object(lattice, "prepare_lattice", side_effect=AssertionError("raw caps before parents")):
            for bad in (True, -1, 1.0, "0", None):
                with self.subTest(value=bad), self.assertRaises(ValueError):
                    lattice.compare(None, None, None, None, None, query_work_budget=bad)

    def test_empty_selector_request_at_zero_caps_is_known_empty_not_whole_hold(self):
        bundle = self.bundle(control=True)
        result = lattice.compare_prepared(self.session(), [], bundle["record_id"],
                                          max_hypotheses=0, max_slots=0, query_work_budget=0)
        self.assertEqual(result["status"], "computed_native_multi_slot_comparison_not_selected")
        self.assertEqual(result["selectors"], [])
        self.assertEqual(result["paths"], [])
        self.assertEqual(result["summary"]["planned_query_work"], 0)
        self.assertEqual(result["logical_universe"], self.record()["universe"])


if __name__ == "__main__":
    unittest.main()
