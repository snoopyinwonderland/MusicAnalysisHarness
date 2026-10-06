"""Cadence prerequisite observations are not musical cadence selections."""
from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch

from musicanote_harness import factor_cadence_prerequisites as cadence
from musicanote_harness import factor_functional_overlay as overlay
from musicanote_harness import factor_functional_resolution as resolution
from musicanote_harness import factor_musical_view as common
from musicanote_harness import harmony_factorized_voice_paths as factors
from test_factor_functional_comparison import SyntheticFixture
from test_factor_functional_overlay import harmony, key_segment
from test_factor_musical_view import provenance
from test_harmony_factorized_voice_paths import edges
from test_musical_role_evidence import event


def span(start=0, end=4):
    return {"start": common.q(Fraction(start)), "end": common.q(Fraction(end))}


def reseal(record, prefix=cadence.PREFIX):
    return common.seal({k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}, prefix)


class CadencePrerequisiteTests(SyntheticFixture, unittest.TestCase):
    def complete(self, lanes=None, segments=None, keys=None, *, context=None, mutate=None,
                 linked=True, missing_lanes=(), extra_paths=(), function_budget=512):
        if lanes is None:
            lanes = [[event("B4", 0, 2), event("C5", 2, 2)],
                     [event("F4", 0, 2), event("E4", 2, 2)],
                     [event("G3", 0, 2), event("C3", 2, 2)]]
        ir, view = self.fixture(lanes, context=context, mutate=mutate)
        segments = segments or [harmony("v", 0, 2, "G", "Mm7"), harmony("i", 2, 4, "C", "M")]
        paths = [common.make_path(view, rows, provenance()) for rows in [segments, *extra_paths]]
        specs = keys or [[key_segment()]]
        overlays = []
        for path in paths:
            for key in specs:
                track = overlay.make_key_track(view, key, provenance())
                functions = overlay.compile_functions(view, path, track, max_candidates=function_budget)
                overlays.append({"key_track": track, "functions": functions})
        graphs, entries = [], []
        for index, lane in enumerate(view["raw_lanes"]):
            graph = factors.factorize(ir, view["context_span"], [lane["part_id"], lane["voice_id"]])
            graphs.append(graph)
            if index in missing_lanes or graph["status"] != "ready":
                continue
            query = factors.query(graph, required_links=edges(graph) if linked else [])
            entries.append({"graph": graph, "query": query, "witness": factors.materialize_witness(graph, query)})
        bundle = resolution.make_bundle(view, paths, entries)
        return view, paths, overlays, bundle, graphs

    def observe(self, fixture, **kwargs):
        view, paths, overlays, bundle, graphs = fixture
        return cadence.observe_prerequisites(view, paths[0], overlays[0]["key_track"],
                                            overlays[0]["functions"], bundle, graphs, **kwargs)

    def bulk(self, fixture, **kwargs):
        view, paths, overlays, bundle, graphs = fixture
        return cadence.observe_all_prerequisites(view, paths, overlays, bundle, graphs, **kwargs)

    def boundary(self, record, time=2):
        return next(r for r in record["boundaries"] if common.f(r["boundary_time"]) == time)

    def test_all_start_internal_and_endpoint_boundaries_retained(self):
        record = self.observe(self.complete())
        self.assertEqual([common.f(r["boundary_time"]) for r in record["boundaries"]], [0, 2, 4])
        self.assertEqual(record["path_boundary_count"], 3)
        self.assertEqual(record["boundaries"][0]["before_extremes"]["rows"], [])
        self.assertEqual(record["boundaries"][-1]["arrival_extremes"]["rows"], [])
        self.assertFalse(record["flags"]["cadence_confirmed"])
        for boundary in record["boundaries"]:
            for name in ("PAC", "HC", "IAC"):
                row = boundary["cadence_prerequisites"][name]
                self.assertEqual(row["missing_premises"], cadence.MISSING_PREMISES)
                self.assertFalse(row["confirmed"])

    def test_same_member_split_is_a_declared_boundary_not_removed(self):
        segments = [harmony("a", 0, 1, "C", "M"), harmony("b", 1, 4, "C", "M")]
        record = self.observe(self.complete(segments=segments))
        self.assertEqual([common.f(r["boundary_time"]) for r in record["boundaries"]], [0, 1, 4])

    def test_root_position_observation_does_not_confirm_structural_bass(self):
        boundary = self.boundary(self.observe(self.complete()))
        row = next(r for r in boundary["arrival_extremes"]["rows"] if "lowest" in r["extreme_axes"])
        factor = row["candidate_factor"]
        self.assertEqual(factor["conditional_inversion_shape"], 0)
        self.assertEqual(factor["ordinary_shape"]["quality"], "major")
        self.assertFalse(factor["inversion_confirmed"])
        self.assertFalse(factor["structural_bass_confirmed"])
        self.assertEqual(row["candidate_scale_degree"]["coordinate"]["degree"], 1)

    def test_first_and_second_inversion_shapes_are_conditional(self):
        for bass, expected in (("E3", 1), ("G3", 2)):
            with self.subTest(bass=bass):
                fixture = self.complete(lanes=[[event(bass, 0, 4)], [event("C5", 0, 4)]],
                                        segments=[harmony("i", 0, 4, "C", "M")])
                row = self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"][0]
                lowest = next(r for r in self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"]
                              if "lowest" in r["extreme_axes"])
                self.assertEqual(lowest["candidate_factor"]["conditional_inversion_shape"], expected)
                self.assertFalse(row["candidate_factor"]["structural_bass_confirmed"])

    def test_seventh_third_inversion_shape(self):
        fixture = self.complete(lanes=[[event("F3", 0, 4)], [event("B4", 0, 4)]],
                                segments=[harmony("v", 0, 4, "G", "Mm7")])
        lowest = next(r for r in self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"]
                      if "lowest" in r["extreme_axes"])
        self.assertEqual(lowest["candidate_factor"]["conditional_inversion_shape"], 3)
        self.assertEqual(lowest["candidate_factor"]["ordinary_shape"]["quality"], "major_minor_seventh")

    def test_incomplete_or_extended_assumptions_do_not_invent_inversion(self):
        for members in (2, 5):
            segment = harmony("i", 0, 4, "C", "M")
            if members == 2:
                segment["members"] = segment["members"][:2]
            else:
                segment["members"] += [{"step": "B", "alter": common.q(0)}, {"step": "D", "alter": common.q(0)}]
            record = self.observe(self.complete(segments=[segment]))
            row = next(r for r in self.boundary(record, 0)["arrival_extremes"]["rows"] if "lowest" in r["extreme_axes"])
            self.assertIsNone(row["candidate_factor"]["conditional_inversion_shape"])
            self.assertIn("complete_ordinary_triad_or_seventh_shape_unestablished", row["candidate_factor"]["blockers"])

    def test_nonmember_lowest_is_not_automatically_NCT_or_removed(self):
        fixture = self.complete(lanes=[[event("D3", 0, 4)], [event("C5", 0, 4)]],
                                segments=[harmony("i", 0, 4, "C", "M")])
        row = next(r for r in self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"] if "lowest" in r["extreme_axes"])
        self.assertEqual(row["written_pitch"]["step"], "D")
        self.assertFalse(row["candidate_factor"]["spelled_member_of_assumption"])
        self.assertIsNone(row["candidate_factor"]["conditional_inversion_shape"])

    def test_equal_height_enharmonics_all_retained_no_first_lowest_choice(self):
        fixture = self.complete(lanes=[[event("B3", 0, 4)], [event("C-4", 0, 4)], [event("E5", 0, 4)]],
                                segments=[harmony("b", 0, 4, "B", "M")])
        rows = self.boundary(self.observe(fixture), 0)["arrival_extremes"]
        self.assertTrue(rows["lowest_spelling_ambiguous"])
        lows = [r for r in rows["rows"] if "lowest" in r["extreme_axes"]]
        self.assertEqual(len(lows), 2)
        self.assertEqual({r["written_pitch"]["step"] for r in lows}, {"B", "C"})
        self.assertTrue(all(r["candidate_factor"]["conditional_inversion_shape"] is None for r in lows))

    def test_same_height_unison_doubling_keeps_every_raw_extreme(self):
        fixture = self.complete(lanes=[[event("C3", 0, 4)], [event("C3", 0, 4)], [event("C5", 0, 4)]],
                                segments=[harmony("i", 0, 4, "C", "M")])
        rows = self.boundary(self.observe(fixture), 0)["arrival_extremes"]
        self.assertFalse(rows["lowest_spelling_ambiguous"])
        self.assertEqual(len([r for r in rows["rows"] if "lowest" in r["extreme_axes"]]), 2)

    def test_direct_links_only_use_same_raw_lane_same_supplied_bundle(self):
        record = self.observe(self.complete())
        pairs = self.boundary(record)["same_raw_lane_transitions"]
        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(r["status"] == "required_link_satisfied_under_this_bundle" for r in pairs))
        self.assertTrue(all(not r["true_voice_identity_confirmed"] for r in pairs))
        self.assertEqual(len({tuple(r["raw_lane"]) for r in pairs}), 2)
        self.assertTrue(all(r["required_links"] == [[r["source_sound_ref"], r["arrival_sound_ref"]]] for r in pairs))

    def test_unlinked_bundle_failure_is_not_global_absence(self):
        pairs = self.boundary(self.observe(self.complete(linked=False)))["same_raw_lane_transitions"]
        self.assertTrue(pairs)
        self.assertTrue(all(r["status"] == "not_satisfied_under_this_bundle_not_global_absence" for r in pairs))
        self.assertTrue(all(not r["absence_is_global"] for r in pairs))

    def test_same_sound_carry_needs_no_fabricated_self_link(self):
        fixture = self.complete(lanes=[[event("C4", 0, 4)]],
                                segments=[harmony("a", 0, 2, "C", "M"), harmony("b", 2, 4, "C", "M")])
        pair = self.boundary(self.observe(fixture))["same_raw_lane_transitions"][0]
        self.assertTrue(pair["same_sound_carry"])
        self.assertEqual(pair["required_links"], [])
        self.assertEqual(pair["status"], "literal_same_sound_carry_under_bundle")

    def test_polyphonic_raw_lane_preserves_all_extreme_pairs_not_one_voice(self):
        fixture = self.complete(lanes=[[event(["G3", "B4"], 0, 2), event(["C3", "C5"], 2, 2)]], linked=False)
        view, paths, overlays, bundle, graphs = fixture
        graph = graphs[0]
        required = [(factor["source_refs"][0], factor["target_refs"][0]) for factor in graph["factors"]]
        if graph["factors"] and len(graph["factors"][0]["source_refs"]) > 1:
            factor = graph["factors"][0]
            required.append((factor["source_refs"][1], factor["target_refs"][1]))
        query = factors.query(graph, required_links=required)
        fixed = resolution.make_bundle(view, paths, [{"graph": graph, "query": query,
                                                     "witness": factors.materialize_witness(graph, query)}])
        record = self.observe((view, paths, overlays, fixed, graphs))
        pairs = self.boundary(record)["same_raw_lane_transitions"]
        self.assertEqual(len(pairs), 4)
        self.assertEqual(sum(r["status"] == "required_link_satisfied_under_this_bundle" for r in pairs), 2)
        self.assertEqual(sum(r["status"] == "not_satisfied_under_this_bundle_not_global_absence" for r in pairs), 2)
        self.assertTrue(all(not r["true_voice_identity_confirmed"] for r in pairs))

    def test_missing_lane_completion_preserves_observation_and_unknown(self):
        fixture = self.complete()
        view, paths, overlays, bundle, graphs = fixture
        full_boundary = self.boundary(self.observe(fixture))
        # Raw lanes sort content-derived IDs, not score-part or pitch order.
        # Remove the actual bass lane from this SAME fixture, not index zero
        # (which can be the inner F4->E4 lane with no extreme transition).
        missing_lane = next(sound["lane"] for sound in view["sounds"]
                            if sound["pitch"]["spelling"] == "G3")
        entries = [{name: entry[name] for name in ("graph", "query", "witness")}
                   for entry in bundle["entries"] if entry["lane"] != missing_lane]
        partial = resolution.make_bundle(view, paths, entries)
        record = self.observe((view, paths, overlays, partial, graphs))
        self.assertTrue(record["missing_lanes"])
        self.assertEqual(record["missing_lanes"], [missing_lane])
        boundary = self.boundary(record)
        for name in ("before_extremes", "arrival_extremes"):
            self.assertEqual(boundary[name], full_boundary[name])
        pairs = boundary["same_raw_lane_transitions"]
        missing = [r for r in pairs if r["witness_ref"] is None]
        self.assertTrue(missing)
        self.assertTrue(all(r["raw_lane"] == missing_lane for r in missing))
        self.assertTrue(all(r["status"] == "unassessed_prerequisites" for r in missing))
        retained = [r for r in pairs if r["raw_lane"] != missing_lane]
        self.assertTrue(retained)
        self.assertTrue(all(r["status"] == "required_link_satisfied_under_this_bundle" for r in retained))

    def test_arrival_and_full_terminal_release_are_not_same_coordinate(self):
        fixture = self.complete(lanes=[[event("G3", 0, 2), event("C3", 2, 1), event(None, 3, Fraction(1, 2)),
                                        event("D3", Fraction(7, 2), Fraction(1, 2))],
                                       [event("B4", 0, 2), event("C5", 2, 1), event(None, 3, 1)]])
        boundary = self.boundary(self.observe(fixture))
        rows = boundary["arrival_extremes"]["rows"]
        self.assertTrue(rows)
        for row in rows:
            probe = row["terminal_probe"]
            self.assertEqual(common.f(probe["boundary_time"]), 2)
            self.assertEqual(common.f(probe["candidate_terminal_release_time"]), 3)
            self.assertTrue(probe["observed_following_same_raw_lane_rest_spans"])
            self.assertFalse(probe["no_observed_later_attack_is_phrase_closure"])
            self.assertFalse(probe["sustain_or_ornament_is_universal_cadence_counterevidence"])

    def test_full_tie_snapshots_and_release_are_not_clipped(self):
        fixture = self.complete(lanes=[[event("C4", 0, 2, tie_role="start"), event("C4", 2, 6, tie_role="stop")]],
                                context=span(0, 4), segments=[harmony("i", 0, 4, "C", "M")])
        row = self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"][0]
        self.assertEqual(len(row["source_note_snapshots"]), 2)
        self.assertIsNotNone(row["tie_chain_snapshot"])
        self.assertEqual(common.f(row["terminal_probe"]["candidate_terminal_release_time"]), 8)
        self.assertEqual(common.f(row["terminal_probe"]["full_sound_duration_quarters"]), 8)
        self.assertTrue(row["terminal_probe"]["release_beyond_observed_horizon"])
        self.assertEqual(row["terminal_probe"]["following_observation_status"], "unassessed_at_or_beyond_context_endpoint")

    def test_bad_full_source_tie_clock_is_not_hidden_by_good_active_clip(self):
        def gap(ir):
            ir["note_events"][1]["global_onset_quarter"] = common.q(3)
            ir["note_events"][1]["onset_in_measure"] = common.q(3)
        fixture = self.complete(lanes=[[event("C4", 0, 2, tie_role="start"), event("C4", 2, 2, tie_role="stop")]],
                                segments=[harmony("i", 0, 4, "C", "M")], mutate=gap)
        row = self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"][0]
        self.assertFalse(row["source_guards"]["source_clock_passed"])
        self.assertIsNone(row["candidate_factor"]["conditional_inversion_shape"])
        self.assertIn("source_clock_unestablished", row["candidate_factor"]["blockers"])

    def test_microtonal_literals_are_retained_but_ordinary_coordinates_withheld(self):
        def microtone(ir):
            for note in ir["note_events"]:
                for field in ("written_pitch", "concert_pitch"):
                    note[field].update(alter=common.q(Fraction(1, 2)), spelling="C~4", midi_pitch=None, pitch_class=None)
            for sound in ir["sounding_events"]:
                sound["pitch"].update(alter=common.q(Fraction(1, 2)), spelling="C~4", midi_pitch=None, pitch_class=None)
        fixture = self.complete(lanes=[[event("C4", 0, 4)]], segments=[harmony("i", 0, 4, "C", "M")], mutate=microtone)
        row = self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"][0]
        self.assertEqual(common.f(row["written_pitch"]["alter"]), Fraction(1, 2))
        self.assertIsNone(row["candidate_scale_degree"]["coordinate"])
        self.assertIn("ordinary_microtonal_scale_coordinate_unassessed", row["candidate_scale_degree"]["blockers"])
        self.assertIsNone(row["candidate_factor"]["conditional_inversion_shape"])

    def test_written_source_pitch_mismatch_does_not_fall_back_to_other_extreme(self):
        def mismatch(ir):
            sound = min(ir["sounding_events"], key=lambda s: s["pitch"]["midi_pitch"])
            sound["pitch"].update(step="C", alter=common.q(0), spelling="C3", midi_pitch=48, pitch_class=0)
        fixture = self.complete(lanes=[[event("D3", 0, 4)], [event("E4", 0, 4)]],
                                segments=[harmony("i", 0, 4, "C", "M")], mutate=mismatch)
        row = next(r for r in self.boundary(self.observe(fixture), 0)["arrival_extremes"]["rows"] if "lowest" in r["extreme_axes"])
        self.assertEqual(row["written_pitch"]["step"], "C")
        self.assertFalse(row["source_guards"]["source_pitch_consistency_passed"])
        self.assertIsNone(row["candidate_factor"]["conditional_inversion_shape"])

    def test_triplet_compound_and_pickup_do_not_certify_accent_or_grouping(self):
        def compound_pickup(ir):
            ir["measures"][0]["time_signature"] = {"beats": 6, "beat_type": 8}
            ir["measures"][0]["pickup"] = True
        fixture = self.complete(lanes=[[event("C4", 0, Fraction(1, 3)), event("D4", Fraction(1, 3), Fraction(11, 3))]],
                                segments=[harmony("a", 0, Fraction(1, 3), "C", "M"),
                                          harmony("b", Fraction(1, 3), 4, "C", "M")], mutate=compound_pickup)
        record = self.observe(fixture)
        first = self.boundary(record, 0)["arrival_extremes"]["rows"][0]
        ratio = first["terminal_probe"]["notated_duration_ratios"][0]
        self.assertEqual(common.f(ratio["full_sound_duration_in_notated_units"]), Fraction(2, 3))
        middle = self.boundary(record, Fraction(1, 3))["literal_boundary_snapshot"]["notated_metric"]["coordinates"][0]
        self.assertTrue(middle["pickup"])
        self.assertEqual(middle["perceived_accent"], "unassessed")
        self.assertFalse(record["flags"]["perceived_accent_certified"])

    def test_relative_duration_uses_notated_meter_not_fixed_note_threshold(self):
        values = []
        for beat_type in (4, 2):
            def meter(ir, denominator=beat_type):
                ir["measures"][0]["time_signature"] = {"beats": 4 if denominator == 4 else 2, "beat_type": denominator}
            fixture = self.complete(lanes=[[event("C4", 0, 4)]],
                                    segments=[harmony("i", 0, 4, "C", "M")], mutate=meter)
            record = self.observe(fixture)
            ratio = record["boundaries"][0]["arrival_extremes"]["rows"][0]["terminal_probe"]["notated_duration_ratios"][0]
            values.append(common.f(ratio["full_sound_duration_in_notated_units"]))
            self.assertFalse(record["flags"]["meter_source_certified"])
            self.assertIn("not_certified_XML_meter", record["meter_basis"])
        self.assertEqual(values, [4, 2])

    def test_unknown_key_preserves_factor_pitch_and_terminal_information(self):
        fixture = self.complete(keys=[[key_segment(tonic=None, mode="unknown", form="unknown")]])
        row = self.boundary(self.observe(fixture))["arrival_extremes"]["rows"][0]
        self.assertIsNone(row["candidate_scale_degree"]["coordinate"])
        self.assertTrue(row["written_pitch"])
        self.assertTrue(row["terminal_probe"])

    def test_key_change_boundary_uses_left_and_right_explicit_key_segments(self):
        fixture = self.complete(keys=[[key_segment(name="c", start=0, end=2),
                                       key_segment(name="d", start=2, end=4, tonic="D")]])
        boundary = self.boundary(self.observe(fixture))
        self.assertTrue(all(r["candidate_scale_degree"]["key_segment_ref"] == "c" for r in boundary["before_extremes"]["rows"]))
        self.assertTrue(all(r["candidate_scale_degree"]["key_segment_ref"] == "d" for r in boundary["arrival_extremes"]["rows"]))

    def test_whole_pair_budget_holds_every_transition_without_pruning_extremes(self):
        fixture = self.complete()
        full = self.observe(fixture)
        held = self.observe(fixture, max_pairs=0)
        self.assertGreater(full["planned_same_raw_lane_pairs"], 0)
        self.assertEqual(held["planned_same_raw_lane_pairs"], full["planned_same_raw_lane_pairs"])
        self.assertEqual(held["observed_same_raw_lane_pairs"], 0)
        self.assertTrue(all(not b["same_raw_lane_transitions"] for b in held["boundaries"]))
        self.assertEqual([b["arrival_extremes"] for b in held["boundaries"]], [b["arrival_extremes"] for b in full["boundaries"]])

    def test_unassessed_function_inventory_is_not_dropped_or_promoted(self):
        record = self.observe(self.complete(function_budget=0))
        self.assertEqual(record["function_inventory_status"], "candidate_budget_abstention")
        self.assertEqual(record["path_boundary_count"], 3)
        self.assertFalse(record["flags"]["function_confirmed"])

    def test_rest_only_keeps_all_boundaries_and_no_positive_extreme(self):
        record = self.observe(self.complete(lanes=[[event(None, 0, 4)]]))
        self.assertEqual(record["planned_same_raw_lane_pairs"], 0)
        self.assertTrue(all(not b["arrival_extremes"]["rows"] for b in record["boundaries"]))
        self.assertFalse(record["flags"]["cadence_confirmed"])

    def test_grace_is_separate_from_positive_extreme_and_performance_unknown(self):
        fixture = self.complete(lanes=[[event("D6", 2, 0, grace=True), event("C4", 2, 2)]])
        boundary = self.boundary(self.observe(fixture))
        self.assertTrue(boundary["literal_boundary_snapshot"]["point_sound_refs_at"])
        self.assertEqual({r["written_pitch"]["step"] for r in boundary["arrival_extremes"]["rows"]}, {"C"})
        self.assertFalse(boundary["cadence_prerequisites"]["PAC"]["confirmed"])

    def test_single_fresh_replay_rejects_resealed_semantic_promotion_and_refs(self):
        fixture = self.complete()
        original = self.observe(fixture)
        view, paths, overlays, bundle, graphs = fixture
        for mutate in (lambda r: r["flags"].update(cadence_confirmed=True),
                       lambda r: r["boundaries"][1]["cadence_prerequisites"]["PAC"].update(confirmed=True),
                       lambda r: r["boundaries"][1].update(arrival_assumed_segment_ref="fake"),
                       lambda r: r.update(confidence=1)):
            bad = deepcopy(original)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                cadence.validate_prerequisites(reseal(bad), view=view, path=paths[0], key_track=overlays[0]["key_track"],
                                               functions=overlays[0]["functions"], bundle=bundle, graphs=graphs)

    def test_foreign_graph_and_unregistered_path_are_rejected(self):
        fixture = self.complete()
        other = self.complete()
        view, paths, overlays, bundle, graphs = fixture
        with self.assertRaises(ValueError):
            cadence.observe_prerequisites(view, paths[0], overlays[0]["key_track"], overlays[0]["functions"], bundle, other[-1])
        different = common.make_path(view, [harmony("different", 0, 4, "C", "M")], provenance())
        functions = overlay.compile_functions(view, different, overlays[0]["key_track"])
        with self.assertRaisesRegex(ValueError, "not_in_explicit"):
            cadence.observe_prerequisites(view, different, overlays[0]["key_track"], functions, bundle, graphs)

    def test_single_input_and_output_alias_isolation(self):
        fixture = self.complete()
        before = deepcopy(fixture)
        record = self.observe(fixture)
        self.assertEqual(fixture, before)
        record["boundaries"][1]["arrival_extremes"]["rows"][0]["source_note_snapshots"][0]["written_pitch"]["step"] = "A"
        self.assertEqual(fixture, before)

    def test_bulk_exact_cartesian_inventory_and_single_output_equality(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="unknown", tonic=None, mode="unknown", form="unknown")]],
                                extra_paths=([harmony("whole", 0, 4, "C", "M")],))
        result = self.bulk(fixture)
        view, paths, overlays, bundle, graphs = fixture
        self.assertEqual(result["planned_records"], 4)
        self.assertEqual(len(result["records"]), 4)
        self.assertEqual(result["status"], "observed_prerequisite_inventory")
        expected = []
        path_map = {p["record_id"]: p for p in paths}
        for pair in sorted(overlays, key=lambda row: row["functions"]["record_id"]):
            expected.append(cadence.observe_prerequisites(view, path_map[pair["functions"]["path_ref"]["record_id"]],
                                                         pair["key_track"], pair["functions"], bundle, graphs))
        self.assertEqual(result["records"], expected)
        self.assertTrue(cadence.validate_all_prerequisites(result, view=view, paths=paths, overlays=overlays, bundle=bundle, graphs=graphs))

    def test_bulk_shared_bundle_and_boundaries_validate_once_not_per_overlay(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="unknown", tonic=None, mode="unknown", form="unknown")]])
        with patch.object(resolution, "prepare_bundle", wraps=resolution.prepare_bundle) as prepare:
            with patch.object(cadence.comparison, "boundary_evidence", wraps=cadence.comparison.boundary_evidence) as boundary:
                result = self.bulk(fixture)
        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(boundary.call_count, 3)
        self.assertEqual(len(result["records"]), 2)

    def test_bulk_whole_record_budget_keeps_declared_refs_without_favorable_subset(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="unknown", tonic=None, mode="unknown", form="unknown")]])
        result = self.bulk(fixture, max_records=1)
        self.assertEqual(result["planned_records"], 2)
        self.assertEqual(len(result["overlay_refs"]), 2)
        self.assertEqual(result["records"], [])
        self.assertEqual(result["status"], "withheld_whole_record_budget")

    def test_bulk_pair_guard_keeps_every_record_as_held_not_subset(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="unknown", tonic=None, mode="unknown", form="unknown")]])
        result = self.bulk(fixture, max_pairs=0)
        self.assertEqual(len(result["records"]), 2)
        self.assertTrue(all(r["status"] == "whole_record_pair_budget_abstention" for r in result["records"]))

    def test_bulk_missing_cartesian_cell_duplicate_or_path_registry_rejected(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="unknown", tonic=None, mode="unknown", form="unknown")]],
                                extra_paths=([harmony("whole", 0, 4, "C", "M")],))
        view, paths, overlays, bundle, graphs = fixture
        for declared_paths, declared_overlays in ((paths, overlays[:-1]), (paths, overlays + [overlays[0]]), (paths[:1], overlays)):
            with self.assertRaises(ValueError):
                cadence.observe_all_prerequisites(view, declared_paths, declared_overlays, bundle, graphs)

    def test_bulk_input_order_does_not_select_first_interpretation(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="unknown", tonic=None, mode="unknown", form="unknown")]],
                                extra_paths=([harmony("whole", 0, 4, "C", "M")],))
        view, paths, overlays, bundle, graphs = fixture
        first = self.bulk(fixture)
        second = cadence.observe_all_prerequisites(view, list(reversed(paths)), list(reversed(overlays)), bundle, list(reversed(graphs)))
        self.assertEqual(first, second)

    def test_bulk_fresh_replay_rejects_resealed_removed_record_or_promoted_flag(self):
        fixture = self.complete()
        result = self.bulk(fixture)
        view, paths, overlays, bundle, graphs = fixture
        for mutate in (lambda r: r.update(records=[]), lambda r: r["flags"].update(training_eligible=True),
                       lambda r: r["records"][0]["flags"].update(cadence_confirmed=True)):
            bad = deepcopy(result)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                cadence.validate_all_prerequisites(reseal(bad, cadence.BATCH_PREFIX), view=view, paths=paths,
                                                   overlays=overlays, bundle=bundle, graphs=graphs)

    def test_bulk_parent_and_sibling_record_alias_isolation(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="unknown", tonic=None, mode="unknown", form="unknown")]])
        before = deepcopy(fixture)
        result = self.bulk(fixture)
        second = deepcopy(result["records"][1])
        result["records"][0]["boundaries"][1]["arrival_extremes"]["rows"][0]["terminal_probe"]["phrase_terminal"] = "confirmed"
        self.assertEqual(fixture, before)
        self.assertEqual(result["records"][1], second)

    def test_bad_budget_is_rejected_before_shared_parent_work(self):
        fixture = self.complete()
        for value in (-1, True, 0.5, None):
            with self.subTest(value=value), patch.object(cadence, "_shared", side_effect=AssertionError("must_not_run")):
                with self.assertRaises(ValueError):
                    self.observe(fixture, max_pairs=value)
                with self.assertRaises(ValueError):
                    self.bulk(fixture, max_records=value)


if __name__ == "__main__":
    unittest.main()
