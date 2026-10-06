from copy import deepcopy
from fractions import Fraction as F
import unittest
from unittest.mock import Mock

from musicanote_harness import harmony_source_clock as clock
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.formal_ir import q
from test_harmony_bounded_recovery import fixture, sample, add_grace


def span(a=0, b=4):
    return {"start": q(a), "end": q(b)}


def tied():
    ir = fixture([("C4", 0, 1, "lead"), ("C4", 1, 2, "lead"), ("E4", 2, 4, "lead")])
    head, tail = ir["sounding_events"][:2]
    head.update(source_note_ids=head["source_note_ids"]+tail["source_note_ids"],
                span=span(0, 2), sounding_duration=q(2), tie_chain_id="test-tie")
    ir["sounding_events"].remove(tail)
    return ir


class SourceClockTests(unittest.TestCase):
    def test_single_and_contiguous_tied_clocks_pass_without_mutation(self):
        for ir in (fixture(), tied()):
            before = deepcopy(ir); guard = clock.SourceClockGuard(ir)
            self.assertTrue(guard.scope(span())["accepted"])
            self.assertEqual(guard.report()["failed"], 0)
            self.assertEqual(ir, before)

    def test_gap_is_withheld_before_catalog_or_exposure(self):
        ir = tied(); ir["note_events"][1]["global_onset_quarter"] = q(F(3, 2))
        guard = clock.SourceClockGuard(ir); delegate = Mock(side_effect=AssertionError("must not compute"))
        result, graph = guard.infer(sample(), delegate=delegate)
        self.assertEqual(result["status"], "source_clock_abstention")
        self.assertEqual(result["transitions"], 0); self.assertIsNone(graph); delegate.assert_not_called()
        self.assertIn("noncontiguous_source_clock", result["source_clock_gate"]["affected_sounds"][0]["reasons"])

    def test_whole_invalid_envelope_and_half_open_endpoints(self):
        ir = tied(); ir["note_events"][1]["global_onset_quarter"] = q(2)
        guard = clock.SourceClockGuard(ir)
        # Stored release is 2, actual source tail ends at 3; neither may be used.
        self.assertFalse(guard.scope(span(1, 2))["accepted"])
        self.assertFalse(guard.scope(span(2, 3))["accepted"])
        self.assertTrue(guard.scope(span(3, 4))["accepted"])

    def test_unaffected_scope_delegates_unchanged_original_core(self):
        ir = tied(); ir["note_events"][1]["global_onset_quarter"] = q(2)
        guard = clock.SourceClockGuard(ir); before = _hash(ir)
        def delegate(received, s):
            self.assertIs(received, ir); s["extra"] = "private copy"
            return {"version": "old", "status": "selected", "selected_prediction": {"same": True}}, "graph"
        request = {"span": span(3, 4)}
        result, graph = guard.infer(request, delegate=delegate)
        self.assertEqual(result["version"], "old"); self.assertEqual(graph, "graph")
        self.assertNotIn("extra", request); self.assertEqual(_hash(ir), before)

    def test_same_pitch_not_enough_when_source_clock_overlaps(self):
        ir = tied(); ir["note_events"][1]["global_onset_quarter"] = q(F(1, 2))
        self.assertFalse(clock.SourceClockGuard(ir).scope(span())["accepted"])

    def test_different_concert_pitch_and_octave_are_not_ties(self):
        for field, value in (("step", "D"), ("octave", 5), ("alter", q(F(1, 2)))):
            ir = tied(); ir["note_events"][1]["concert_pitch"][field] = value
            row = clock.audit(ir)["records"][0]
            self.assertFalse(row["passed"]); self.assertIn("different_spelled_concert_pitch", row["reasons"])

    def test_enharmonic_and_pitch_class_equality_do_not_erase_spelling(self):
        ir = tied(); ir["sounding_events"][0]["pitch"].update(step="C", alter=q(1))
        for n in ir["note_events"][:2]: n["concert_pitch"].update(step="D", alter=q(-1))
        self.assertFalse(clock.SourceClockGuard(ir).scope(span())["accepted"])

    def test_rational_representation_and_triplet_tie_are_exact(self):
        ir = tied()
        for n, start in zip(ir["note_events"][:2], (0, F(1, 3))):
            n.update(global_onset_quarter=q(start), notated_duration_quarter=q(F(1, 3)))
        ir["sounding_events"][0].update(span=span(0, F(2, 3)), sounding_duration=q(F(2, 3)))
        ir["note_events"][0]["concert_pitch"]["alter"] = {"numerator": 0, "denominator": 2}
        self.assertTrue(clock.SourceClockGuard(ir).scope(span())["accepted"])

    def test_release_duration_attack_and_negative_clock_each_withheld(self):
        changes = (("span", span(0, 3)), ("sounding_duration", q(3)),
                   ("attack_note_id", "not-head"), ("sounding_duration", q(-1)))
        for field, value in changes:
            ir = tied(); ir["sounding_events"][0][field] = value
            self.assertFalse(clock.SourceClockGuard(ir).scope(span())["accepted"], field)

    def test_negative_or_zero_non_grace_note_duration_withheld(self):
        for dur in (0, -1):
            ir = tied(); ir["note_events"][0]["notated_duration_quarter"] = q(dur)
            self.assertFalse(clock.SourceClockGuard(ir).scope(span())["accepted"])

    def test_verified_zero_grace_remains_present_and_allowed(self):
        ir = fixture(); note, sound = add_grace(ir)
        guard = clock.SourceClockGuard(ir)
        self.assertTrue(guard.scope(span())["accepted"]); self.assertEqual(guard.report()["zero_time_graces"], 1)
        self.assertIn(note, ir["note_events"]); self.assertIn(sound, ir["sounding_events"])

    def test_invalid_zero_grace_affects_point_not_previous_exclusive_end(self):
        ir = fixture(); note, _ = add_grace(ir); note["grace"]["is_grace"] = False
        guard = clock.SourceClockGuard(ir)
        self.assertTrue(guard.scope(span(0, 1))["accepted"])
        self.assertFalse(guard.scope(span(1, 2))["accepted"])

    def test_cross_staff_and_cross_voice_do_not_invent_bad_clock(self):
        ir = tied(); ir["note_events"][1].update(display_staff_id="other", voice_id="other-voice")
        guard = clock.SourceClockGuard(ir)
        self.assertTrue(guard.scope(span())["accepted"])
        self.assertIn("multiple_normalized_voice_ids", guard.report()["records"][0]["warnings"])

    def test_cross_part_chain_is_withheld(self):
        ir = tied(); ir["note_events"][1]["part_id"] = "other-part"
        self.assertFalse(clock.SourceClockGuard(ir).scope(span())["accepted"])

    def test_missing_duplicate_and_empty_source_ids_fail_closed(self):
        variants = []
        for ids in (["missing"], [], ["n0", "n0"]):
            ir = fixture(); ir["sounding_events"][0]["source_note_ids"] = ids; variants.append(ir)
        ir = fixture(); ir["note_events"].append(deepcopy(ir["note_events"][0])); variants.append(ir)
        ir = fixture(); ir["sounding_events"].append(deepcopy(ir["sounding_events"][0])); variants.append(ir)
        for ir in variants:
            self.assertFalse(clock.SourceClockGuard(ir).scope(span())["accepted"])

    def test_missing_source_note_and_unlocatable_clock_block_even_distant_scope(self):
        for field, value in (("source_note_ids", ["missing"]), ("span", {"start": q(0), "end": .3})):
            ir = fixture(); ir["sounding_events"][0][field] = value
            guard = clock.SourceClockGuard(ir); self.assertFalse(guard.scope(span(9, 10))["accepted"])

    def test_shared_source_note_invalidates_both_owners(self):
        ir = fixture(); ir["sounding_events"][1]["source_note_ids"] = ir["sounding_events"][0]["source_note_ids"][:]
        report = clock.audit(ir)
        self.assertEqual(sum("note_shared_between_sounds" in r["reasons"] for r in report["records"]), 2)

    def test_unordered_chain_preserves_ids_but_uses_physical_attack(self):
        ir = tied(); ir["sounding_events"][0]["source_note_ids"].reverse()
        before = deepcopy(ir); self.assertTrue(clock.SourceClockGuard(ir).scope(span())["accepted"])
        self.assertEqual(before, ir)

    def test_scope_and_audit_defensive_copy_source_mutation_invalidates(self):
        ir = tied(); guard = clock.SourceClockGuard(ir)
        report = guard.report(); report["records"].clear()
        self.assertEqual(len(guard.report()["records"]), 2)
        ir["note_events"][0]["notated_duration_quarter"] = q(2)
        with self.assertRaisesRegex(ValueError, "changed"): guard.scope(span())
        self.assertFalse(guard.valid)

    def test_delegate_mutation_invalidates_even_on_exception(self):
        ir = fixture(); guard = clock.SourceClockGuard(ir)
        def bad(received, s):
            received["score"]["duration_quarters"] = q(2); raise RuntimeError("unrelated")
        with self.assertRaisesRegex(ValueError, "changed"): guard.infer(sample(), delegate=bad)

    def test_invalid_scope_and_float_coordinates_are_rejected(self):
        guard = clock.SourceClockGuard(fixture())
        for value in (span(2, 1), span(-1, 1), {"start": .1, "end": q(2)}):
            with self.assertRaises(ValueError): guard.scope(value)

    def test_real_unchanged_catalog_scores_and_prediction_on_clean_fixture(self):
        ir = fixture(); expected, graph = clock.original_infer(ir, sample())
        actual, guarded_graph = clock.SourceClockGuard(ir).infer(sample())
        self.assertEqual(graph, guarded_graph)
        for key in expected: self.assertEqual(actual[key], expected[key], key)

    def test_title_annotations_and_key_labels_are_not_gate_features(self):
        ir = tied(); base = clock.audit(ir)
        ir["score"].update(title="special", composer="any"); ir["extensions"] = {"gold": "V7/V"}
        later = clock.audit(ir)
        self.assertEqual(base["records"], later["records"])
        self.assertEqual(base["global_blockers"], later["global_blockers"])


if __name__ == "__main__": unittest.main()
