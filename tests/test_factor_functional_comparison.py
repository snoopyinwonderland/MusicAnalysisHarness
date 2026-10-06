"""Synthetic literal axes and one-bundle functional hypotheses, not verdicts."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_functional_comparison as comparison
from musicanote_harness import factor_musical_view as common
from musicanote_harness.musical_pattern_observation import q, f
from test_factor_musical_view import make_view
from test_musical_role_evidence import make_ir, event
from test_factor_functional_overlay import harmony, key_segment
from test_factor_musical_view import provenance
from test_harmony_factorized_voice_paths import edges
from musicanote_harness import factor_functional_overlay as functional
from musicanote_harness import factor_functional_resolution as resolution
from musicanote_harness import harmony_factorized_voice_paths as factors


def span(start=0, end=4):
    return {"start": q(Fraction(start)), "end": q(Fraction(end))}


def reseal(record, prefix):
    return common.seal({k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}, prefix)


class SyntheticFixture:
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case_count = 0

    def fixture(self, lanes, context=None, mutate=None):
        context = context or span()
        padded = deepcopy(lanes)
        for lane in padded:
            end = max(e["onset"] + e["duration"] for e in lane)
            if end < f(context["end"]):
                lane.append(event(None, end, f(context["end"]) - end))
        self.case_count += 1
        directory = Path(self.temp.name) / str(self.case_count)
        directory.mkdir()
        ir = make_ir(directory, padded)
        # A synthetic trailing-rest horizon is explicit, not a source repair.
        ir["score"]["duration_quarters"] = q(max(f(ir["score"]["duration_quarters"]), f(context["end"])))
        if mutate:
            mutate(ir)
        return ir, make_view(ir, context)


class FunctionalBoundaryEvidenceTests(SyntheticFixture, unittest.TestCase):

    def test_literal_height_never_selects_structural_bass_or_melody(self):
        _, view = self.fixture([[event("C3", 0, 4)], [event("E4", 0, 4)], [event("G5", 0, 4)]])
        before = deepcopy(view)
        record = comparison.boundary_evidence(view, 1)
        self.assertEqual(record["lowest_highest_at"]["lowest_written_height"], q(48))
        self.assertEqual(record["lowest_highest_at"]["highest_written_height"], q(79))
        for name in ("structural_bass", "structural_melody", "consonance"):
            self.assertEqual(record["lowest_highest_at"][name], "unassessed")
        self.assertIsNone(record["flags"]["selected"])
        self.assertFalse(record["flags"]["cadence_confirmed"])
        self.assertEqual(view, before)
        self.assertTrue(comparison.validate_boundary_evidence(record, view, q(1)))

    def test_all_equal_extremes_are_retained_not_first_lane_selected(self):
        _, view = self.fixture([[event("B3", 0, 4)], [event("C-4", 0, 4)], [event("E5", 0, 4)]])
        record = comparison.boundary_evidence(view, 0)
        self.assertEqual(len(record["lowest_highest_at"]["lowest_sound_refs"]), 2)
        self.assertEqual(record["lowest_highest_at"]["lowest_written_height"], q(59))
        self.assertFalse(record["lowest_highest_at"]["concert_pitch_certified"])

    def test_exclusive_boundary_distinguishes_left_limit_attack_and_carry(self):
        _, view = self.fixture([[event("G3", 0, 2), event("C3", 2, 2)], [event("E4", 0, 4)]])
        record = comparison.boundary_evidence(view, 2)
        sounds = {r["sound_id"]: r for r in view["sounds"]}
        self.assertEqual({sounds[x]["pitch"]["step"] for x in record["positive_sound_refs_before"]}, {"G", "E"})
        self.assertEqual({sounds[x]["pitch"]["step"] for x in record["positive_sound_refs_at"]}, {"C", "E"})
        self.assertEqual(len(record["full_sound_start_refs"]), 1)
        self.assertEqual(len(record["full_sound_end_refs"]), 1)
        self.assertEqual(len(record["full_sound_continuing_refs"]), 1)
        self.assertEqual(len(record["attack_note_refs_at"]), 1)

    def test_triplet_metric_is_exact_not_perceived_accent(self):
        _, view = self.fixture([[event("C4", 0, Fraction(1, 3)), event("D4", Fraction(1, 3), Fraction(1, 3)),
                                 event("E4", Fraction(2, 3), Fraction(10, 3))]])
        record = comparison.boundary_evidence(view, Fraction(1, 3))
        coordinate = record["notated_metric"]["coordinates"][0]
        self.assertEqual(coordinate["notated_beat_coordinate"], q(Fraction(4, 3)))
        self.assertFalse(coordinate["at_notated_measure_start"])
        self.assertEqual(coordinate["perceived_accent"], "unassessed")
        self.assertFalse(record["notated_metric"]["perceived_accent_certified"])

    def test_compound_meter_coordinate_does_not_guess_accent_grouping(self):
        def compound(ir):
            # Fixture metadata supplies a notated meter, never XML certification.
            ir["measures"][0]["time_signature"] = {"beats": 6, "beat_type": 8}
        _, view = self.fixture([[event("C4", 0, 4)]], mutate=compound)
        record = comparison.boundary_evidence(view, Fraction(1, 2))
        metric = record["notated_metric"]["coordinates"][0]
        self.assertEqual(metric["notated_beat_unit_quarter"], q(Fraction(1, 2)))
        self.assertEqual(metric["notated_beat_coordinate"], q(2))
        self.assertEqual(metric["perceived_accent"], "unassessed")
        self.assertFalse(record["notated_metric"]["key_signature_used"])

    def test_generic_six_four_is_observation_not_consonance(self):
        _, view = self.fixture([[event("G3", 0, 4)], [event("C4", 0, 4)], [event("E4", 0, 4)]])
        record = comparison.boundary_evidence(view, 1)
        self.assertTrue(record["lowest_highest_at"]["generic_fourth_and_sixth_present"])
        self.assertEqual(record["lowest_highest_at"]["consonance"], "unassessed")
        self.assertFalse(record["flags"]["consonance_certified"])

    def test_context_endpoint_absence_does_not_certify_closure(self):
        _, view = self.fixture([[event("C4", 0, 8)]], context=span(0, 4))
        record = comparison.boundary_evidence(view, 4)
        self.assertEqual(record["positive_sound_refs_at"], [])
        self.assertTrue(record["full_sound_continuing_refs"])
        self.assertTrue(record["following"]["known_full_sound_refs_extending_beyond_context"])
        self.assertTrue(record["following"]["no_observed_positive_after_boundary"])
        self.assertEqual(record["following"]["phrase_closure"], "unassessed")
        self.assertFalse(record["flags"]["phrase_closure_certified"])

    def test_rest_only_context_is_no_positive_evidence_not_success(self):
        _, view = self.fixture([[event(None, 0, 4)]])
        record = comparison.boundary_evidence(view, 2)
        self.assertEqual(record["lowest_highest_at"]["lowest_sound_refs"], [])
        self.assertEqual(len(record["following"]["observed_following_rest_spans"]), 1)
        self.assertIsNone(record["lowest_highest_at"]["lowest_written_height"])
        self.assertFalse(record["flags"]["cadence_confirmed"])

    def test_point_is_separate_from_positive_height_and_keeps_timing_guard(self):
        _, view = self.fixture([[event("D6", 1, 0, grace=True), event("C4", 1, 3)]])
        record = comparison.boundary_evidence(view, 1)
        self.assertEqual(len(record["point_sound_refs_at"]), 1)
        self.assertEqual(record["lowest_highest_at"]["highest_written_height"], q(60))
        point = next(r for r in record["source_guards"] if r["sound_ref"] in record["point_sound_refs_at"])
        self.assertFalse(point["source_clock_passed"])
        self.assertIn("grace_performed_timing_not_assessed", point["source_diagnostics"])

    def test_bad_clock_outside_active_clip_is_not_removed(self):
        def gap(ir):
            source = ir["note_events"][1]
            source["global_onset_quarter"] = q(3)
            source["onset_in_measure"] = q(3)
        _, view = self.fixture([[event("C4", 0, 2, tie_role="start"), event("C4", 2, 2, tie_role="stop")]],
                               context=span(0, 1), mutate=gap)
        record = comparison.boundary_evidence(view, Fraction(1, 2))
        self.assertTrue(record["source_guards"])
        self.assertFalse(record["source_guards"][0]["source_clock_passed"])
        self.assertTrue(record["source_guards"][0]["source_diagnostics"])

    def test_fresh_replay_rejects_resealed_extra_or_forged_axis(self):
        _, view = self.fixture([[event("C4", 0, 4)]])
        original = comparison.boundary_evidence(view, 1)
        for mutate in (lambda r: r.update(confidence=1),
                       lambda r: r["flags"].update(cadence_confirmed=True),
                       lambda r: r["lowest_highest_at"].update(structural_bass="confirmed"),
                       lambda r: r["notated_metric"]["coordinates"][0].update(notated_beat_coordinate=q(99))):
            bad = deepcopy(original)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                comparison.validate_boundary_evidence(reseal(bad, comparison.BOUNDARY_PREFIX), view, 1)

    def test_outside_context_and_inexact_times_rejected(self):
        _, view = self.fixture([[event("C4", 0, 4)]])
        for time in (-1, 5, True, 0.5, {"numerator": 1, "denominator": 0}):
            with self.subTest(time=time), self.assertRaises(ValueError):
                comparison.boundary_evidence(view, time)


class FunctionalComparisonTests(SyntheticFixture, unittest.TestCase):
    def complete(self, lanes=None, segments=None, keys=None, *, linked=True, extra_paths=None,
                 mutate=None, missing_lanes=()):
        lanes = lanes or [[event("B4", 0, 2), event("C5", 2, 2)],
                          [event("F4", 0, 2), event("E4", 2, 2)],
                          [event("G3", 0, 2), event("C3", 2, 2)]]
        ir, view = self.fixture(lanes, mutate=mutate)
        first = common.make_path(view, segments or [harmony("v", 0, 2, "G", "Mm7"),
                                                     harmony("i", 2, 4, "C", "M")], provenance())
        paths = [first] + [common.make_path(view, s, provenance()) for s in extra_paths or []]
        key_specs = keys or [[key_segment()]]
        overlays = []
        for path in paths:
            for specs in key_specs:
                track = functional.make_key_track(view, specs, provenance())
                overlays.append({"key_track": track, "functions": functional.compile_functions(view, path, track)})
        entries = []
        for index, lane in enumerate(view["raw_lanes"]):
            if index in missing_lanes:
                continue
            graph = factors.factorize(ir, view["context_span"], [lane["part_id"], lane["voice_id"]])
            if graph["status"] != "ready":
                continue
            query = factors.query(graph, required_links=edges(graph) if linked else [])
            witness = factors.materialize_witness(graph, query)
            entries.append({"graph": graph, "query": query, "witness": witness})
        bundle = resolution.make_bundle(view, paths, entries)
        return ir, view, paths, overlays, bundle

    def result(self, fixture, **kwargs):
        _, view, paths, overlays, bundle = fixture
        return comparison.compare_functional(view, paths, overlays, bundle, **kwargs)

    def boundary(self, record, time=2, vector_index=0):
        row = next(r for r in record["evidence_vectors"][vector_index]["boundary_evidence"]
                   if f(r["boundary_time"]) == time)
        literal = next(r for r in record["boundary_registry"] if common.ref(r) == row["boundary_ref"])
        return {**row, "literal": literal}

    def test_one_bundle_all_lanes_have_separate_not_additive_all_part_accounts(self):
        fixture = self.complete()
        before = deepcopy(fixture)
        record = self.result(fixture)
        _, view, paths, overlays, bundle = fixture
        self.assertEqual(record["raw_membership_by_path"][0]["total_all_part_note_time"], q(12))
        self.assertEqual(len(record["lane_comparisons"]), 3)
        self.assertEqual([r["comparison"]["total_all_part_note_time"] for r in record["lane_comparisons"]], [q(12)] * 3)
        self.assertFalse(record["flags"]["all_part_lane_accounts_summed"])
        self.assertEqual(record["completion_bundle_ref"], common.ref(bundle))
        self.assertEqual(record["completion_registry"], [{k: e[k] for k in
                         ("lane", "graph_ref", "query_ref", "witness_ref", "completion_id")} for e in bundle["entries"]])
        self.assertEqual(fixture, before)
        self.assertTrue(comparison.validate_comparison(record, view=view, paths=paths, overlays=overlays, bundle=bundle))

    def test_actual_LT_and_seventh_links_are_separate_from_tonic_arrival_and_PAC(self):
        record = self.result(self.complete())
        boundary = self.boundary(record)
        resolutions = boundary["leading_tone_and_seventh_assessments"]
        satisfied = [r for r in resolutions if r["status"] == "conditional_resolution_under_bundle"]
        self.assertEqual({r["critical_role"] for r in satisfied}, {"leading_tone", "seventh"})
        self.assertTrue(all(r["satisfied_observation_refs"] for r in satisfied))
        profile = boundary["functional_profiles"]["compatibility"]["tonic_arrival"]
        self.assertTrue(profile["raw_assumed_shape_compatible"])
        self.assertFalse(profile["cadence_confirmed"])
        for name in ("PAC", "HC"):
            self.assertFalse(boundary["functional_profiles"]["cadence_premises"][name]["confirmed"])
        self.assertFalse(record["flags"]["structural_melody_confirmed"])
        self.assertFalse(record["flags"]["structural_bass_confirmed"])

    def test_missing_links_under_this_bundle_are_not_global_resolution_absence(self):
        fixture = self.complete(linked=False)
        record = self.result(fixture)
        rows = self.boundary(record)["leading_tone_and_seventh_assessments"]
        self.assertIn("not_satisfied_under_this_bundle_not_global_absence", {r["status"] for r in rows})
        self.assertNotIn("conditional_resolution_under_bundle", {r["status"] for r in rows})
        self.assertTrue(record["raw_membership_by_path"])
        self.assertFalse(record["flags"]["cadence_confirmed"])

    def test_same_path_alternate_keys_preserve_raw_and_NCT_but_not_key_projection(self):
        keys = [[key_segment()], [key_segment(name="a-minor", tonic="A", mode="minor", form="harmonic_minor")]]
        record = self.result(self.complete(keys=keys))
        self.assertEqual(len(record["evidence_vectors"]), 2)
        first, second = record["evidence_vectors"]
        self.assertEqual(first["raw_membership"], second["raw_membership"])
        self.assertEqual(first["nct_accounts_by_lane"], second["nct_accounts_by_lane"])
        self.assertEqual(record["pairwise_differences"][0]["raw_note_time_difference"],
                         {"member": q(0), "nonmember": q(0), "unknown": q(0)})
        self.assertNotEqual(self.boundary(record, vector_index=0)["functional_profiles"]["assumed_harmony_and_key"],
                            self.boundary(record, vector_index=1)["functional_profiles"]["assumed_harmony_and_key"])
        self.assertFalse(record["flags"]["ranked"])
        self.assertIsNone(record["flags"]["preferred"])

    def test_different_paths_share_exact_registered_bundle_and_every_lane_completion(self):
        alternative = [harmony("hold", 0, 4, "C", "M")]
        fixture = self.complete(extra_paths=[alternative])
        record = self.result(fixture)
        self.assertEqual(len(record["path_refs"]), 2)
        self.assertTrue(all(len(row["comparison"]["accounts"]) == 2 for row in record["lane_comparisons"]))
        self.assertEqual({r["completion_bundle_ref"]["record_id"] for r in record["resolution_evaluations"]},
                         {fixture[-1]["record_id"]})
        self.assertEqual(len(record["evidence_vectors"]), 2)
        self.assertTrue(any(f(row) != 0 for row in record["pairwise_differences"][0]["raw_note_time_difference"].values()))

    def test_active_blocked_path_preserves_raw_membership_while_qualified_unknown(self):
        blocked = [harmony("hold", 0, 4, "C", "M", blockers=["stored_meter_guard"])]
        record = self.result(self.complete(lanes=[[event("C4", 0, 4)]], segments=blocked))
        raw = record["raw_membership_by_path"][0]["raw_note_time"]
        self.assertEqual(raw, {"member": q(4), "nonmember": q(0), "unknown": q(0)})
        account = record["lane_comparisons"][0]["comparison"]["accounts"][0]
        self.assertEqual(account["raw_note_time"], raw)
        self.assertEqual(account["note_time"]["unsupported"], q(4))
        self.assertTrue(all(row["qualified_membership"] == "unknown" for row in account["items"]))
        profiles = self.boundary(record, 0)["functional_profiles"]["compatibility"]
        self.assertEqual(profiles["tonic_arrival"]["status"], "withheld_prerequisites")

    def test_unknown_key_preserves_raw_sounds_and_function_inventory_without_fake_signature(self):
        unknown = [[key_segment(tonic=None, mode="unknown", form="unknown")]]
        record = self.result(self.complete(keys=unknown))
        boundary = self.boundary(record)
        self.assertIsNone(boundary["functional_profiles"]["compatibility"]["tonic_arrival"]["raw_assumed_shape_compatible"])
        self.assertIn("explicit_local_key_unassessed", boundary["functional_profiles"]["compatibility"]["tonic_arrival"]["blockers"])
        self.assertTrue(boundary["functional_profiles"]["all_candidate_function_refs"])
        self.assertFalse(record["flags"]["key_signature_used"])

    def test_internal_dominant_arrival_with_following_attacks_is_not_HC(self):
        segments = [harmony("i", 0, 1, "C", "M"), harmony("v", 1, 3, "G", "Mm7"), harmony("i2", 3, 4, "C", "M")]
        lanes = [[event("C3", 0, 1), event("G3", 1, 2), event("C3", 3, 1)],
                 [event("G4", 0, 1), event("B4", 1, 2), event("C5", 3, 1)]]
        record = self.result(self.complete(lanes=lanes, segments=segments))
        boundary = self.boundary(record, 1)
        self.assertTrue(boundary["functional_profiles"]["compatibility"]["dominant_arrival"]["raw_assumed_shape_compatible"])
        self.assertTrue(boundary["literal"]["following"]["observed_later_attack_note_refs"])
        hc = boundary["functional_profiles"]["cadence_premises"]["HC"]
        self.assertFalse(hc["confirmed"])
        self.assertIn("dominant_arrival_alone_is_not_half_cadence", hc["blockers"])

    def test_deceptive_like_root_shape_keeps_inherited_target_blockers_not_cadence_truth(self):
        segments = [harmony("v", 0, 2, "G", "Mm7"), harmony("vi", 2, 4, "A", "m")]
        record = self.result(self.complete(segments=segments))
        profile = self.boundary(record)["functional_profiles"]["compatibility"]["deceptive_like_arrival"]
        self.assertTrue(profile["raw_assumed_shape_compatible"])
        self.assertEqual(profile["status"], "withheld_prerequisites")
        self.assertIn("next_target_triad_core_shape_mismatch", profile["blockers"])
        self.assertFalse(profile["cadence_confirmed"])

    def test_NCT_explanation_and_raw_membership_remain_different_axes(self):
        lanes = [[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)], [event("G3", 0, 4)]]
        segments = [harmony("i", 0, 4, "C", "M")]
        record = self.result(self.complete(lanes=lanes, segments=segments))
        raw = record["raw_membership_by_path"][0]
        self.assertEqual(raw["raw_note_time"]["nonmember"], q(1))
        self.assertEqual(raw["total_all_part_note_time"], q(8))
        lane_accounts = record["evidence_vectors"][0]["nct_accounts_by_lane"]
        self.assertIn(q(1), [r["note_time"]["conditional_explained"] for r in lane_accounts])
        self.assertTrue(all(r["raw_note_time"] == raw["raw_note_time"] for r in lane_accounts))
        self.assertTrue(all(r["lane_accounts_are_not_additive"] for r in lane_accounts))

    def test_missing_lane_and_empty_selection_preserve_unknown_not_false_or_approval(self):
        partial = self.result(self.complete(missing_lanes=(0,)))
        self.assertEqual(len(partial["missing_lanes"]), 1)
        self.assertEqual(len(partial["lane_comparisons"]), 2)
        rows = self.boundary(partial)["leading_tone_and_seventh_assessments"]
        self.assertTrue(any("raw_lane_completion_missing_unknown" in r["blockers"] for r in rows))
        empty = self.result(self.complete(lanes=[[event(None, 0, 4)]], linked=False))
        self.assertEqual(empty["raw_membership_by_path"][0]["total_all_part_note_time"], q(0))
        self.assertEqual(empty["lane_comparisons"], [])
        self.assertEqual(len(empty["missing_lanes"]), 1)
        self.assertFalse(empty["flags"]["cadence_confirmed"])

    def test_resolution_whole_budget_abstention_keeps_raw_and_every_interpretation(self):
        record = self.result(self.complete(), max_resolution_candidates=0)
        self.assertEqual(record["resolution_evaluations"][0]["status"], "unassessed")
        self.assertEqual(record["resolution_evaluations"][0]["assessments"], [])
        self.assertEqual(len(record["evidence_vectors"]), 1)
        self.assertEqual(record["raw_membership_by_path"][0]["total_all_part_note_time"], q(12))
        self.assertTrue(record["lane_comparisons"])

    def test_pitch_guard_does_not_change_clock_or_repair_raw_pitch(self):
        def corrupt(ir):
            sound = next(s for s in ir["sounding_events"] if s["pitch"]["step"] == "C")
            sound["pitch"]["step"] = "D"
        record = self.result(self.complete(mutate=corrupt))
        guards = self.boundary(record)["literal"]["source_guards"]
        mismatch = [r for r in guards if r["source_pitch_consistency_passed"] is False]
        self.assertTrue(mismatch)
        self.assertTrue(all(r["source_clock_passed"] for r in mismatch))
        self.assertIn("involved_source_written_pitch_not_established",
                      self.boundary(record)["functional_profiles"]["compatibility"]["tonic_arrival"]["blockers"])
        self.assertFalse(record["flags"]["function_confirmed"])

    def test_source_prose_and_key_signature_do_not_change_raw_or_choose_function(self):
        first = self.result(self.complete())
        def prose(ir):
            ir["parser_manifest"].setdefault("options", {})["original_RN"] = "G major gold HC, select dominant"
            ir["measures"][0]["key_signature"] = {"fifths": 5, "mode_hint": "major"}
        second = self.result(self.complete(mutate=prose))
        self.assertEqual(first["raw_membership_by_path"][0]["raw_note_time"], second["raw_membership_by_path"][0]["raw_note_time"])
        for profile in ("tonic_arrival", "dominant_arrival", "deceptive_like_arrival"):
            self.assertEqual(self.boundary(first)["functional_profiles"]["compatibility"][profile]["raw_assumed_shape_compatible"],
                             self.boundary(second)["functional_profiles"]["compatibility"][profile]["raw_assumed_shape_compatible"])
        self.assertFalse(second["flags"]["source_labels_used"])
        self.assertFalse(second["flags"]["key_signature_used"])
        self.assertIsNone(second["flags"]["selected"])

    def test_foreign_registry_missing_path_or_resealed_bundle_witness_rejected(self):
        fixture = self.complete(extra_paths=[[harmony("i", 0, 4, "C", "M")]])
        _, view, paths, overlays, bundle = fixture
        entries = [{k: e[k] for k in ("graph", "query", "witness")} for e in bundle["entries"]]
        partial = resolution.make_bundle(view, paths[:1], entries)
        with self.assertRaises(ValueError):
            comparison.compare_functional(view, paths, overlays, partial)
        bad = deepcopy(bundle)
        bad["entries"][0]["witness"]["assignment"]["links"] = []
        bad = reseal(bad, "fmcmb_")
        with self.assertRaises(ValueError):
            comparison.compare_functional(view, paths, overlays, bad)

    def test_fresh_comparison_replay_rejects_resealed_refs_axes_flags_and_extra_fields(self):
        fixture = self.complete()
        _, view, paths, overlays, bundle = fixture
        original = self.result(fixture)
        mutations = [lambda r: r.update(confidence=1), lambda r: r["flags"].update(cadence_confirmed=True),
                     lambda r: r["raw_membership_by_path"][0]["raw_note_time"].update(member=q(999)),
                     lambda r: r["completion_registry"][0].update(completion_id="wrong"),
                     lambda r: r["evidence_vectors"][0]["boundary_evidence"][0]["functional_profiles"]["cadence_premises"]["PAC"].update(confirmed=True)]
        for mutate in mutations:
            bad = deepcopy(original)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                comparison.validate_comparison(reseal(bad, comparison.PREFIX), view=view, paths=paths, overlays=overlays, bundle=bundle)

    def test_duplicate_hypotheses_and_inexact_budgets_rejected_no_hidden_selection(self):
        _, view, paths, overlays, bundle = self.complete()
        with self.assertRaisesRegex(ValueError, "duplicate_competing"):
            comparison.compare_functional(view, paths * 2, overlays, bundle)
        with self.assertRaisesRegex(ValueError, "duplicate_functional"):
            comparison.compare_functional(view, paths, overlays * 2, bundle)
        for value in (True, -1, 1.5):
            with self.assertRaises(ValueError):
                comparison.compare_functional(view, paths, overlays, bundle, max_resolution_candidates=value)

    def test_path_and_interpretation_order_do_not_select_a_first_reading(self):
        _, view, paths, overlays, bundle = self.complete(extra_paths=[[harmony("i", 0, 4, "C", "M")]])
        first = comparison.compare_functional(view, paths, overlays, bundle)
        second = comparison.compare_functional(view, list(reversed(paths)), list(reversed(overlays)), bundle)
        self.assertEqual(first, second)
        self.assertFalse(first["flags"]["ranked"])
        self.assertIsNone(first["flags"]["selected"])

    def test_shared_boundaries_project_once_and_all_thin_refs_resolve_exactly(self):
        keys = [[key_segment()], [key_segment(name="a", tonic="A", mode="minor", form="harmonic_minor")]]
        fixture = self.complete(keys=keys, extra_paths=[[harmony("i", 0, 4, "C", "M")]])
        with patch.object(comparison, "_boundary_payload", wraps=comparison._boundary_payload) as project:
            record = self.result(fixture)
        self.assertEqual(project.call_count, 3)
        self.assertEqual(len(record["boundary_registry"]), 3)
        registry = {r["record_id"]: r for r in record["boundary_registry"]}
        evaluations = {r["record_id"]: r for r in record["resolution_evaluations"]}
        all_functions = {r["function_id"] for p in fixture[3] for r in p["functions"]["rows"]}
        for vector in record["evidence_vectors"]:
            for boundary in vector["boundary_evidence"]:
                self.assertNotIn("literal", boundary)
                literal = registry[boundary["boundary_ref"]["record_id"]]
                self.assertEqual(boundary["boundary_ref"], common.ref(literal))
                self.assertEqual(boundary["boundary_time"], literal["boundary_time"])
                self.assertTrue(set(boundary["functional_profiles"]["all_candidate_function_refs"]) <= all_functions)
                evaluation = evaluations[boundary["resolution_evaluation_ref"]["record_id"]]
                source = {r["resolution_ref"]: r for r in evaluation["assessments"]}
                for assessment in boundary["leading_tone_and_seventh_assessments"]:
                    self.assertNotIn("rule_snapshot", assessment)
                    self.assertEqual(assessment["rule_snapshot_ref"],
                                     {"evaluation_ref": common.ref(evaluation), "resolution_ref": assessment["resolution_ref"]})
                    self.assertEqual(assessment["literal_motion_observation_refs"],
                        [o["observation_id"] for o in source[assessment["resolution_ref"]]["rule_snapshot"]["observations"]])

    def test_every_resolution_result_equals_independent_public_fresh_evaluation(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(tonic=None, mode="unknown", form="unknown")]])
        _, view, paths, overlays, bundle = fixture
        record = self.result(fixture)
        graphs = [entry["graph"] for entry in bundle["entries"]]
        path_map = {p["record_id"]: p for p in paths}
        evaluations = {r["functions_ref"]["record_id"]: r for r in record["resolution_evaluations"]}
        for pair in overlays:
            functions = pair["functions"]
            public = resolution.evaluate_resolutions(view, path_map[functions["path_ref"]["record_id"]],
                pair["key_track"], functions, graphs, bundle)
            self.assertEqual(evaluations[functions["record_id"]], public)

    def test_prepared_bundle_validates_once_and_every_interpretation_remains_assessed(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(tonic=None, mode="unknown", form="unknown")]],
                                extra_paths=[[harmony("i", 0, 4, "C", "M")]])
        _, view, paths, overlays, bundle = fixture
        before = deepcopy(fixture)
        with patch.object(resolution, "prepare_bundle", wraps=resolution.prepare_bundle) as prepare, \
             patch.object(resolution, "_assess_prepared", wraps=resolution._assess_prepared) as assess, \
             patch.object(resolution, "evaluate_resolutions", side_effect=AssertionError("repeated_public_bundle_validation")):
            record = self.result(fixture)
        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(assess.call_count, len(overlays))
        self.assertEqual({r["functions_ref"]["record_id"] for r in record["resolution_evaluations"]},
                         {p["functions"]["record_id"] for p in overlays})
        self.assertEqual(fixture, before)
        with patch.object(resolution, "prepare_bundle", wraps=resolution.prepare_bundle) as prepare:
            self.assertTrue(comparison.validate_comparison(record, view=view, paths=paths, overlays=overlays, bundle=bundle))
        self.assertEqual(prepare.call_count, 1)

    def test_fake_prepared_handle_cannot_authorize_comparison(self):
        fixture = self.complete()
        with patch.object(resolution, "prepare_bundle", return_value=object()):
            with self.assertRaisesRegex(ValueError, "internally_issued_prepared_bundle_required"):
                self.result(fixture)

    def test_caller_mutation_after_preparation_cannot_change_sealed_experiment(self):
        fixture = self.complete()
        _, _, _, _, bundle = fixture
        actual_prepare = resolution.prepare_bundle
        def mutate_after_prepare(*args):
            handle = actual_prepare(*args)
            bundle["selected"] = "caller_mutated"
            return handle
        with patch.object(resolution, "prepare_bundle", side_effect=mutate_after_prepare):
            with self.assertRaisesRegex(ValueError, "functional_comparison_inputs_mutated"):
                self.result(fixture)

    def test_resealed_thin_refs_registry_or_prerequisite_promotion_fail_fresh_replay(self):
        fixture = self.complete()
        _, view, paths, overlays, bundle = fixture
        original = self.result(fixture)
        mutations = [lambda r: r["boundary_registry"].pop(),
                     lambda r: r["evidence_vectors"][0]["boundary_evidence"][0].update(boundary_ref=common.ref(r["boundary_registry"][-1])),
                     lambda r: r["evidence_vectors"][0]["boundary_evidence"][1]["functional_profiles"]["candidate_function_prerequisites"][0].update(key_projection_assessed=True, blockers=[])]
        for mutate in mutations:
            bad = deepcopy(original)
            mutate(bad)
            if bad == original:
                continue
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                comparison.validate_comparison(reseal(bad, comparison.PREFIX), view=view, paths=paths, overlays=overlays, bundle=bundle)

    def test_locally_owned_output_seal_has_no_mutable_caller_aliases(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(tonic=None, mode="unknown", form="unknown")]],
                                extra_paths=[[harmony("hold", 0, 4, "C", "M")]])
        before = deepcopy(fixture)
        record = self.result(fixture)
        def mutable_ids(value):
            found, stack = set(), [value]
            while stack:
                item = stack.pop()
                if isinstance(item, dict):
                    if id(item) in found:continue
                    found.add(id(item));stack.extend(item.values())
                elif isinstance(item, (list, tuple)):
                    if isinstance(item, list):found.add(id(item))
                    stack.extend(item)
            return found
        self.assertFalse(mutable_ids(record) & mutable_ids(fixture))
        body = {k:v for k,v in record.items() if k not in ("record_id", "record_sha256")}
        self.assertEqual(common.seal(body, comparison.PREFIX), record)
        encoded = json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(",", ":"))
        record["resolution_evaluations"][0]["assessments"][0]["blockers"].append("returned mutation")
        record["lane_comparisons"][0]["comparison"]["accounts"][0]["items"][0]["slot"]["pitch"]["step"] = "returned mutation"
        self.assertEqual(fixture, before)
        repeated = self.result(fixture)
        self.assertEqual(json.dumps(repeated,sort_keys=True,ensure_ascii=False,separators=(",", ":")), encoded)

    def test_lookup_sharing_preserves_overlay_order_all_pairs_and_exact_differences(self):
        fixture = self.complete(keys=[[key_segment()], [key_segment(name="a-minor",tonic="A",mode="minor",form="harmonic_minor")],
                                     [key_segment(tonic=None,mode="unknown",form="unknown")]],
                                extra_paths=[[harmony("hold",0,4,"C","M")],
                                             [harmony("hold",0,4,"D","m")]])
        _,view,paths,overlays,bundle = fixture
        record = self.result(fixture)
        reversed_record = comparison.compare_functional(view,list(reversed(paths)),list(reversed(overlays)),bundle)
        self.assertEqual(record,reversed_record)
        vectors=record["evidence_vectors"]
        expected=[]
        from itertools import combinations
        for first,second in combinations(vectors,2):
            expected.append({"first_functions_ref":first["functions_ref"],"second_functions_ref":second["functions_ref"],
                "raw_note_time_difference":{name:q(f(second["raw_membership"]["raw_note_time"][name])-
                                                   f(first["raw_membership"]["raw_note_time"][name]))
                                            for name in ("member","nonmember","unknown")},
                "difference_is_preference":False,"axes_not_weighted_or_combined":True})
        self.assertEqual(record["pairwise_differences"],expected)
        self.assertEqual(len(expected),len(overlays)*(len(overlays)-1)//2)
        pathmap={p["record_id"]:p for p in paths};overlaymap={o["functions"]["record_id"]:o for o in overlays}
        boundaries={r["record_id"]:r for r in record["boundary_registry"]}
        for vector in vectors:
            pair=overlaymap[vector["functions_ref"]["record_id"]]
            for boundary in vector["boundary_evidence"]:
                projected=comparison._profiles(view,pathmap[vector["path_ref"]["record_id"]],pair["key_track"],pair["functions"],
                                               f(boundary["boundary_time"]),boundaries[boundary["boundary_ref"]["record_id"]])
                self.assertEqual(boundary["functional_profiles"],projected)

    def test_same_member_split_and_key_change_indices_do_not_mix_evidence(self):
        segments=[harmony("left",0,2,"G","Mm7"),harmony("right",2,4,"C","M")]
        keys=[[key_segment(name="known-left",start=0,end=2),
               key_segment(name="unknown-right",start=2,end=4,tonic=None,mode="unknown",form="unknown")]]
        fixture=self.complete(segments=segments,keys=keys,
                              extra_paths=[[harmony("split-left",0,1,"C","M"),harmony("split-right",1,4,"C","M")]])
        record=self.result(fixture);_,view,paths,overlays,bundle=fixture
        evaluations={r["record_id"]:r for r in record["resolution_evaluations"]}
        for vector in record["evidence_vectors"]:
            evaluation=evaluations[vector["resolution_evaluation_ref"]["record_id"]]
            function=next(p["functions"] for p in overlays if common.ref(p["functions"])==vector["functions_ref"])
            for boundary in vector["boundary_evidence"]:
                active={r["function_id"] for r in function["rows"] if r["function_id"] in boundary["functional_profiles"]["all_candidate_function_refs"]
                        and f(r["source_span"]["end"])==f(boundary["boundary_time"])}
                self.assertEqual([r["resolution_ref"] for r in boundary["leading_tone_and_seventh_assessments"]],
                                 [r["resolution_ref"] for r in evaluation["assessments"] if r["function_ref"] in active])
        self.assertTrue(comparison.validate_comparison(record,view=view,paths=paths,overlays=overlays,bundle=bundle))


if __name__ == "__main__":
    unittest.main()
