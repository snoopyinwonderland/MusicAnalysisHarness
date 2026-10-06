"""Exact unlabeled context sidecars; no SOURCE admission or musical verdicts."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from musicanote_harness import factor_context_observation as context
from musicanote_harness import factor_musical_view as common
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness import sounding_lineage_audit as lineage
from test_factor_musical_view import make_observation, reseal, span
from test_musical_role_evidence import event, make_ir


def physical_clocks(ir, clocks, labels=None):
    """Explicit synthetic IR clock fixture, not a parser or source repair.

    XML round-tripped events/IDs stay intact; the test-only measure catalog and
    corresponding event local coordinates model multiple physical clocks.
    Production inputs are never repartitioned by this helper.
    """
    template = ir["measures"][0]
    measures = []
    for index, (start, duration) in enumerate(clocks):
        row = deepcopy(template)
        row.update(measure_id="measure_fixture_%03d" % index,
                   printed_measure_number=str(index + 1) if labels is None else labels[index],
                   sequential_measure_index=index, global_start_quarter=common.q(start),
                   actual_duration_quarter=common.q(duration), nominal_duration_quarter=common.q(4))
        measures.append(row)
    ir["measures"] = measures
    ir["score"]["measure_count"] = len(measures)
    end = max(common.f(n["global_onset_quarter"]) + common.f(n["notated_duration_quarter"])
              for n in [*ir["note_events"], *ir["rest_events"]])
    ir["score"]["duration_quarters"] = common.q(end)
    for note in [*ir["note_events"], *ir["rest_events"]]:
        onset = common.f(note["global_onset_quarter"])
        candidates = [m for m in measures if common.f(m["global_start_quarter"]) <= onset]
        measure = max(candidates, key=lambda m: common.f(m["global_start_quarter"]))
        note["measure_id"] = measure["measure_id"]
        note["onset_in_measure"] = common.q(onset - common.f(measure["global_start_quarter"]))
    pattern.validate_core(ir)
    return ir


class FactorContextObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, lanes=None, *, extent=None, clocks=None, labels=None, modify=None):
        ir = make_ir(self.temp.name, lanes or [[event("C4", 0, 1), event("D4", 1, 1),
                                              event("E4", 2, 1), event("F4", 3, 1)]])
        if clocks is not None:
            physical_clocks(ir, clocks, labels)
        if modify is not None:
            modify(ir)
        extent = extent or span(1, 2)
        observation = make_observation(ir, extent)
        ids = [s["sounding_event_id"] for s in observation["core_projection"]["sounding_events"]]
        audit = lineage.audit_sounding_lineage(ir, sound_ids=ids, context_span=extent)
        view = common.prepare(ir, observation, audit)
        return ir, view, observation, audit

    def observe(self, fixture, **options):
        return context.observe_context(*fixture, **options)

    def validate(self, fixture, record, **options):
        return context.validate_context(record, ir=fixture[0], view=fixture[1],
                                        observation=fixture[2], audit=fixture[3], **options)

    def sounds(self, record, spelling):
        return [r for r in record["sound_facts"] if r["pitch"]["spelling"] == spelling]

    def old_seed(self, fixture, spelling):
        return next(s["sound_id"] for s in fixture[1]["sounds"] if s["pitch"]["spelling"] == spelling)

    def test_fresh_replay_typed_parents_exact_projection_and_no_promotions(self):
        fx = self.fixture(); before = deepcopy(fx)
        record = self.observe(fx)
        self.assertTrue(self.validate(fx, record))
        self.assertEqual(fx, before)
        self.assertEqual(record, self.observe(fx))
        self.assertEqual(record["original_view_ref"], common.ref(fx[1]))
        self.assertEqual(record["observation_ref"], common.ref(fx[2]))
        self.assertEqual(record["audit_ref"], common.ref(fx[3]))
        self.assertEqual(record["original_context_span"], span(1, 2))
        self.assertEqual(record["original_target_span"], span(1, 2))
        self.assertEqual(record["literal_observation"]["scope"]["target_span"], span(1, 2))
        self.assertNotIn("source_statement_ref", record["literal_observation"]["scope"])
        self.assertNotIn("alignment_ref", record["literal_observation"]["scope"])
        self.assertNotIn("record_id", record["literal_observation"])
        for field in ("harmony_confirmed", "resolution_confirmed", "cadence_confirmed", "function_confirmed",
                      "nct_confirmed", "training_eligible", "gold_eligible", "generation_ready",
                      "original_window_or_path_or_bundle_extended", "source_annotations_used",
                      "counts_are_confidence", "partial_relation_selection_performed"):
            self.assertIs(record[field], False)
        self.assertIsNone(record["selected"])
        self.assertIsNone(record["preferred"])

    def test_output_isolated_from_every_mutable_input_and_prior_output(self):
        fx = self.fixture(); original = deepcopy(fx)
        first = self.observe(fx); sealed = deepcopy(first)
        def mutable_ids(value):
            result = set()
            if isinstance(value, dict):
                result.add(id(value))
                for row in value.values(): result.update(mutable_ids(row))
            elif isinstance(value, (list, tuple)):
                if isinstance(value, list): result.add(id(value))
                for row in value: result.update(mutable_ids(row))
            return result
        self.assertFalse(mutable_ids(first) & mutable_ids(fx))
        first["snapshot_registry"]["note_events"][0]["written_pitch"]["step"] = "G"
        first["literal_observation"]["core_projection"]["measures"][0]["printed_measure_number"] = "999"
        first["sound_facts"][0]["source_clock_passed"] = False
        self.assertEqual(fx, original)
        self.assertEqual(self.observe(fx), sealed)

    def test_all_equal_onset_successors_and_equal_release_predecessors_retained(self):
        fx = self.fixture([[event(["C4", "E4"], 0, 1), event("D4", 1, 1),
                            event(["E4", "G4"], 2, 1), event("F4", 3, 1)]])
        record = self.observe(fx)
        row = record["neighbor_inventory"][0]
        self.assertEqual(len(row["predecessor_refs"]), 2)
        self.assertEqual(len(row["successor_refs"]), 2)
        self.assertEqual(len(record["relations"]), 4)
        self.assertEqual(record["counts"]["planned_relations"], 4)
        self.assertTrue(all(r["touching_full_endpoints"] for r in record["relations"]))
        self.assertTrue(all(r["voice_edge_established"] is False for r in record["relations"]))
        self.assertTrue(all(r["completion_condition_created"] is False for r in record["relations"]))
        self.assertEqual(len(record["snapshot_registry"]["chord_onset_groups"]), 2)

    def test_gap_and_rest_are_explicit_not_a_voice_bridge(self):
        fx = self.fixture([[event("C4", 0, 1), event(None, 1, 1), event("D4", 2, 1),
                            event(None, 3, 1), event("E4", 4, 1)]], extent=span(2, 3),
                          clocks=[(0, 4), (4, 1)])
        record = self.observe(fx)
        row = record["neighbor_inventory"][0]
        self.assertEqual(row["predecessor_gap"], common.q(1))
        self.assertEqual(row["successor_gap"], common.q(1))
        self.assertIn("gap_not_voice_edge", row["successor_status"])
        self.assertEqual(len(record["snapshot_registry"]["rest_events"]), 2)
        self.assertTrue(all(r["gap"] == common.q(1) and not r["voice_edge_established"] for r in record["relations"]))

    def test_other_part_and_voice_do_not_supply_successor_and_rest_lane_survives(self):
        fx = self.fixture([[event("C4", 0, 1), event(None, 1, 3)],
                           [event(None, 0, 1), event("D4", 1, 1), event("E4", 2, 2)]], extent=span(0, 1))
        record = self.observe(fx)
        plan = record["neighbor_inventory"][0]
        self.assertEqual(plan["successor_refs"], [])
        self.assertEqual(record["counts"]["old_positive_sounds"], 1)
        self.assertEqual(len(record["raw_lane_scope"]["original_lanes"]), 2)
        self.assertEqual(len(record["raw_lane_scope"]["envelope_lanes"]), 2)
        self.assertFalse(plan["missing_pitch_globally_proved"])

    def test_same_part_different_raw_voice_is_not_used_as_endpoint_successor(self):
        def merge_part_catalog_for_synthetic_fixture(ir):
            first = ir["parts"][0]["part_id"]
            second = ir["parts"][1]["part_id"]
            for row in [*ir["note_events"], *ir["rest_events"], *ir["voices"], *ir["staves"]]:
                if row["part_id"] == second:
                    row["part_id"] = first
        fx = self.fixture([[event("C4", 0, 1), event(None, 1, 3)],
                           [event(None, 0, 1), event("D4", 1, 3)]], extent=span(0, 1),
                          modify=merge_part_catalog_for_synthetic_fixture)
        record = self.observe(fx)
        self.assertEqual(len({r[0] for r in record["raw_lane_scope"]["original_lanes"]}), 1)
        self.assertEqual(len({r[1] for r in record["raw_lane_scope"]["original_lanes"]}), 2)
        self.assertEqual(record["neighbor_inventory"][0]["successor_refs"], [])

    def test_overlapping_held_sound_is_metadata_not_an_endpoint_successor(self):
        fx = self.fixture([[event("C4", 0, 4), event("D4", 1, 1)]], extent=span(1, 2))
        record = self.observe(fx)
        held_id = self.old_seed(fx, "C4")
        row = next(r for r in record["neighbor_inventory"] if r["seed_sound_ref"] == self.old_seed(fx, "D4"))
        self.assertEqual(row["held_at_attack_refs"], [held_id])
        self.assertEqual(row["held_at_release_refs"], [held_id])
        self.assertNotIn(held_id, row["successor_refs"])
        self.assertNotIn(held_id, row["predecessor_refs"])

    def test_unlocated_full_IR_sound_is_retained_unknown_not_silently_lane_filtered(self):
        def ambiguous_outside_old_span(ir):
            left = next(s for s in ir["sounding_events"] if s["pitch"]["spelling"] == "D4")
            other = next(n for n in ir["note_events"] if n["written_pitch"]["spelling"] == "E4")
            left["source_note_ids"].append(other["note_id"])
        fx = self.fixture([[event("C4", 0, 1), event(None, 1, 2), event("D4", 3, 1)],
                           [event(None, 0, 2), event("E4", 2, 1), event(None, 3, 1)]],
                          extent=span(0, 1), modify=ambiguous_outside_old_span)
        record = self.observe(fx)
        self.assertEqual(len(record["unlocated_full_IR_positive_sound_refs"]), 1)
        unknown = next(r for r in record["sound_facts"] if r["sound_ref"] in record["unlocated_full_IR_positive_sound_refs"])
        self.assertIsNone(unknown["lane"])
        self.assertFalse(unknown["eligible_as_envelope_source"])
        self.assertIn("ambiguous_raw_lane_ownership", unknown["diagnostics"])
        self.assertTrue(record["neighbor_inventory"][0]["full_raw_lane_lookup_has_unlocated_sound_unknowns"])
        self.assertFalse(record["neighbor_inventory"][0]["missing_pitch_globally_proved"])

    def test_point_and_grace_are_separate_and_not_ordinary_endpoint_successors(self):
        fx = self.fixture([[event("C4", 0, 1), event("D4", 1, 0, grace=True),
                            event("E4", 1, 1), event("F4", 2, 2)]], extent=span(0, 1))
        record = self.observe(fx)
        self.assertEqual(len(record["point_sound_refs"]), 1)
        point = next(r for r in record["sound_facts"] if r["point"])
        self.assertTrue(point["grace"])
        self.assertFalse(point["eligible_as_envelope_source"])
        successors = record["neighbor_inventory"][0]["successor_refs"]
        self.assertNotIn(point["sound_ref"], successors)
        self.assertEqual(len(successors), 1)
        self.assertFalse(point["source_clock_passed"])

    def test_full_tie_span_attack_and_source_note_closure_never_clipped(self):
        fx = self.fixture([[event("C4", 0, 1, tie_role="start"), event("C4", 1, 1, tie_role="stop"),
                            event("D4", 2, 1), event("E4", 3, 1)]], extent=span(Fraction(3, 2), 2))
        record = self.observe(fx)
        source = self.sounds(record, "C4")[0]
        self.assertEqual(source["span"], span(0, 2))
        self.assertEqual(len(source["source_note_refs"]), 2)
        self.assertEqual(source["placement"]["original_context"]["overlap"], span(Fraction(3, 2), 2))
        attacks = [r for r in record["snapshot_registry"]["attack_events"] if r["sounding_event_id"] == source["sound_ref"]]
        self.assertEqual(len(attacks), 1)
        self.assertEqual(record["neighbor_inventory"][0]["source_release"], common.q(2))
        self.assertTrue(source["source_clock_passed"])

    def test_source_clock_gap_even_outside_old_clip_never_becomes_passed(self):
        fx = self.fixture([[event("C4", 0, 1, tie_role="start"), event("C4", 3, 1, tie_role="stop")]], extent=span(0, 1))
        record = self.observe(fx)
        sound = self.sounds(record, "C4")[0]
        self.assertFalse(sound["source_clock_passed"])
        self.assertFalse(sound["eligible_as_envelope_source"])
        self.assertIn("full_source_timeline_gap", sound["diagnostics"])
        self.assertEqual(sound["span"], fx[1]["sounds"][0]["span"])

    def test_source_pitch_mismatch_not_fixed_or_reclassified(self):
        def change(ir):
            ir["sounding_events"][0]["pitch"] = deepcopy(ir["note_events"][-1]["written_pitch"])
        fx = self.fixture(modify=change)
        record = self.observe(fx)
        row = next(r for r in record["sound_facts"] if r["sound_ref"] == fx[0]["sounding_events"][0]["sounding_event_id"])
        self.assertFalse(row["source_pitch_consistency_passed"])
        self.assertFalse(row["eligible_as_envelope_source"])
        self.assertIn("source_written_pitch_mismatch", row["diagnostics"])
        self.assertEqual(row["pitch"], fx[0]["sounding_events"][0]["pitch"])

    def test_microtonal_motion_is_rational_not_tonal_resolution(self):
        def change(ir):
            note = ir["note_events"][1]
            for key in ("written_pitch", "concert_pitch"):
                note[key].update(alter=common.q(Fraction(1, 2)), spelling="D-half-sharp4", midi_pitch=None, pitch_class=None)
            sound = next(s for s in ir["sounding_events"] if note["note_id"] in s["source_note_ids"])
            sound["pitch"] = deepcopy(note["written_pitch"])
        fx = self.fixture(modify=change)
        record = self.observe(fx)
        motion = next(r["motion"] for r in record["relations"] if r["direction"] == "predecessor")
        self.assertEqual(motion["semitones"], common.q(Fraction(5, 2)))
        self.assertFalse(motion["integer_spelling_supported"])
        self.assertFalse(motion["tonal_resolution_evaluated"])
        self.assertIn("microtonal_motion_not_tonal_resolution_support", motion["diagnostics"])

    def test_neighbor_before_source_start_is_not_carried_into_original_target(self):
        fx = self.fixture([[event("A4", 0, 1), event("F4", 1, 1), event("E4", 2, 2)]])
        record = self.observe(fx)
        previous = self.sounds(record, "A4")[0]
        self.assertIsNone(previous["placement"]["original_target"]["overlap"])
        self.assertTrue(previous["placement"]["original_target"]["release_at_start"])
        self.assertFalse(previous["placement"]["original_target"]["active_at_start_right_limit"])
        self.assertFalse(record["resolution_confirmed"])

    def test_successor_at_target_end_is_outside_target_but_literal_neighbor(self):
        fx = self.fixture()
        record = self.observe(fx)
        successor = self.sounds(record, "E4")[0]
        self.assertFalse(successor["placement"]["original_target"]["onset_inside"])
        self.assertIsNone(successor["placement"]["original_target"]["overlap"])
        self.assertTrue(successor["placement"]["envelope"]["onset_inside"])
        self.assertFalse(successor["resolution_eligible"])

    def test_outside_envelope_neighbors_retained_exactly_as_metadata(self):
        fx = self.fixture([[event("C4", 0, 1), event(None, 1, 4), event("D4", 5, 1),
                            event(None, 6, 4), event("E4", 10, 2)]], extent=span(5, 6),
                          clocks=[(0, 4), (4, 4), (8, 4)])
        record = self.observe(fx, pre_measures=0, post_measures=0)
        self.assertEqual(record["envelope_span"], span(4, 8))
        previous, after = self.sounds(record, "C4")[0], self.sounds(record, "E4")[0]
        self.assertTrue(previous["outside_envelope_metadata_only"])
        self.assertTrue(after["outside_envelope_metadata_only"])
        self.assertFalse(previous["eligible_as_envelope_source"])
        self.assertFalse(after["eligible_as_envelope_source"])
        self.assertTrue(all(r["outside_envelope_metadata_only"] for r in record["relations"]))
        self.assertNotIn(after["sound_ref"], {s["sounding_event_id"] for s in record["literal_observation"]["core_projection"]["sounding_events"]})
        self.assertIn(after["sound_ref"], {s["sounding_event_id"] for s in record["snapshot_registry"]["sounding_events"]})

    def test_neighboring_physical_measure_clocks_not_printed_number_arithmetic(self):
        lanes = [[event("C4", 0, 4), event("D4", 4, 4), event("E4", 8, 4)]]
        fx = self.fixture(lanes, extent=span(5, 6), clocks=[(0, 4), (4, 4), (8, 4)], labels=["7a", "99", "-20"])
        record = self.observe(fx)
        self.assertEqual(record["envelope_span"], span(0, 12))
        none = self.observe(fx, pre_measures=0, post_measures=0)
        self.assertEqual(none["envelope_span"], span(4, 8))
        self.assertEqual([r["printed_measure_number"] for r in record["literal_observation"]["core_projection"]["measures"]], ["7a", "99", "-20"])
        self.assertEqual(record["measure_policy"]["clock_order"], "exact_global_start_then_actual_end_not_printed_number")

    def test_duplicate_and_overlapping_clocks_preserved_without_repair(self):
        fx = self.fixture([[event("C4", 0, 4), event("D4", 4, 4), event("E4", 8, 4)]],
                          extent=span(5, 6), clocks=[(0, 4), (4, 4), (4, 4), (3, 6), (8, 4)])
        record = self.observe(fx, pre_measures=0, post_measures=0)
        self.assertEqual(record["envelope_span"], span(3, 9))
        duplicate = next(r for r in record["measure_policy"]["clock_groups"] if r["span"] == span(4, 8))
        self.assertEqual(len(duplicate["measure_refs"]), 2)
        self.assertIn("overlapping_distinct_measure_clocks", record["measure_policy"]["diagnostics"])
        self.assertEqual(len(record["literal_observation"]["core_projection"]["measures"]), 5)

    def test_zero_clock_gap_and_score_clamp_are_explicit(self):
        fx = self.fixture([[event("C4", 0, 4), event("D4", 4, 4), event("E4", 8, 4)]],
                          extent=span(5, 6), clocks=[(0, 2), (3, 0), (4, 4), (8, 8)])
        record = self.observe(fx)
        self.assertEqual(record["envelope_span"], span(3, 12))
        codes = record["measure_policy"]["diagnostics"]
        self.assertIn("gap_between_physical_measure_clocks", codes)
        self.assertTrue(any(r.startswith("zero_duration_measure_clock:") for r in codes))
        self.assertTrue(any(r.startswith("measure_clock_exceeds_score_clamped_for_envelope:") for r in codes))
        self.assertEqual(fx[0]["measures"][-1]["actual_duration_quarter"], common.q(8))

    def test_original_context_in_clock_gap_kept_and_no_nominal_duration_fill(self):
        fx = self.fixture([[event("C4", 0, 4), event("D4", 4, 4), event("E4", 8, 4)]],
                          extent=span(5, 6), clocks=[(0, 2), (8, 4)])
        record = self.observe(fx, pre_measures=0, post_measures=0)
        self.assertEqual(record["envelope_span"], span(5, 6))
        self.assertIn("original_context_has_no_overlapping_measure_clock", record["measure_policy"]["diagnostics"])
        expanded = self.observe(fx)
        self.assertEqual(expanded["envelope_span"], span(0, 12))

    def test_event_budget_whole_hold_keeps_all_refs_and_snapshots_no_subset(self):
        fx = self.fixture()
        full = self.observe(fx)
        held = self.observe(fx, max_events=0)
        self.assertEqual(held["status"], "whole_budget_abstention")
        self.assertEqual(held["relations"], [])
        self.assertEqual(held["neighbor_inventory"], full["neighbor_inventory"])
        self.assertEqual(held["snapshot_registry"], full["snapshot_registry"])
        self.assertEqual(held["extended_source_audit"], full["extended_source_audit"])
        self.assertEqual(held["counts"]["planned_relations"], full["counts"]["planned_relations"])
        self.assertTrue(held["inventories_complete"])
        self.assertFalse(held["relations_complete"])
        self.assertFalse(held["truncated"])
        self.assertTrue(self.validate(fx, held, max_events=0))

    def test_relation_budget_whole_hold_retains_all_equal_time_alternatives(self):
        fx = self.fixture([[event(["C4", "E4"], 0, 1), event("D4", 1, 1),
                            event(["E4", "G4"], 2, 1), event("F4", 3, 1)]])
        held = self.observe(fx, max_relations=3)
        self.assertEqual(held["counts"]["planned_relations"], 4)
        self.assertEqual(held["counts"]["materialized_relations"], 0)
        self.assertEqual(len(held["neighbor_inventory"][0]["successor_refs"]), 2)
        self.assertEqual(len(held["neighbor_inventory"][0]["predecessor_refs"]), 2)
        self.assertFalse(held["partial_relation_selection_performed"])
        exact = self.observe(fx, max_relations=4)
        self.assertEqual(exact["counts"]["materialized_relations"], 4)

    def test_invalid_limits_rejected_before_core_or_original_parent_reads(self):
        for field in ("pre_measures", "post_measures", "max_events", "max_relations"):
            for value in (-1, True, 1.5, None, "1"):
                with self.subTest(field=field, value=value), patch.object(pattern, "validate_core", side_effect=AssertionError("no read")):
                    with self.assertRaisesRegex(ValueError, "nonnegative_integer"):
                        context.observe_context(None, None, None, None, **{field: value})

    def test_resealed_output_tamper_and_unknown_or_promoting_fields_rejected(self):
        fx = self.fixture(); record = self.observe(fx)
        for kind in ("relation", "source", "neighbor", "snapshot", "envelope", "promotion", "unknown"):
            forged = deepcopy(record)
            if kind == "relation": forged["relations"][0]["motion"]["diatonic_steps"] = 99
            elif kind == "source": forged["sound_facts"][0]["source_clock_passed"] = False
            elif kind == "neighbor": forged["neighbor_inventory"][0]["successor_refs"] = []
            elif kind == "snapshot": forged["snapshot_registry"]["sounding_events"].pop()
            elif kind == "envelope": forged["envelope_span"] = span(1, 2)
            elif kind == "promotion": forged["resolution_confirmed"] = True
            else: forged["confidence"] = 0.99
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                self.validate(fx, reseal(forged, context.PREFIX))

    def test_stale_full_IR_foreign_parent_and_resealed_clock_guard_fail_closed(self):
        fx = self.fixture(); record = self.observe(fx)
        for kind in ("ir", "observation", "audit", "view"):
            changed = deepcopy(fx)
            if kind == "ir": changed[0]["note_events"][0]["notation"]["new_prose"] = "changed"
            elif kind == "observation":
                changed[2]["slots"].pop(); changed = (*changed[:2], reseal(changed[2], "mfco_"), changed[3])
            elif kind == "audit":
                changed[3]["source_clock_consistency_passed"] = False; changed = (*changed[:3], reseal(changed[3], "msla_"))
            else:
                changed[1]["sounds"][0]["source_clock_passed"] = False; changed = (changed[0], reseal(changed[1]), *changed[2:])
            with self.subTest(kind=kind), self.assertRaises((ValueError, ValidationError)):
                self.validate(changed, record)

    def test_current_schema_and_actual_helper_source_stamps_invalidate_old_record(self):
        fx = self.fixture(); record = self.observe(fx)
        core = common._schema_bytes()
        with patch.object(common, "_schema_bytes", return_value=core + b"\n"):
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                self.validate(fx, record)
        original_read = Path.read_bytes
        target = Path(lineage.__file__)
        def changed_bytes(path):
            raw = original_read(path)
            return raw + b"\n" if path == target else raw
        with patch.object(Path, "read_bytes", changed_bytes):
            with self.assertRaisesRegex(ValueError, "stale_foreign_or_modified"):
                self.validate(fx, record)

    def test_public_validator_always_freshly_replays_exact_original_view(self):
        fx = self.fixture(); record = self.observe(fx)
        actual = common.validate_view
        with patch.object(common, "validate_view", wraps=actual) as fresh:
            self.validate(fx, record); self.validate(fx, record)
            bound = [call for call in fresh.call_args_list if call.kwargs.get("ir") is fx[0]]
            self.assertEqual(len(bound), 2)
            self.assertTrue(all(call.kwargs["observation"] is fx[2] and call.kwargs["audit"] is fx[3] for call in bound))

    def test_never_constructs_harmony_path_or_resolution_or_completion_graph(self):
        from musicanote_harness import factor_functional_resolution as resolution
        from musicanote_harness import harmony_factorized_voice_paths as factors
        fx = self.fixture()
        with patch.object(common, "make_path", side_effect=AssertionError("path forbidden")), \
             patch.object(resolution, "compile_resolutions", side_effect=AssertionError("analysis forbidden")), \
             patch.object(factors, "factorize", side_effect=AssertionError("old bundle extension forbidden")):
            record = self.observe(fx)
        self.assertFalse(record["original_window_or_path_or_bundle_extended"])
        self.assertFalse(record["relations"][0]["completion_condition_created"])


if __name__ == "__main__":
    unittest.main()
