from copy import deepcopy
from fractions import Fraction as F
from dataclasses import replace
import itertools
import inspect
import unittest

from musicanote_harness.harmony_candidate_recall import rational
from musicanote_harness.harmony_evidence_scoring import (
    decode, key_alters, metric, prepare_with_evidence, run_features, score_path, source_evidence,
)
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.harmony_scored_decoder import prepare
import test_harmony_scored_decoder as old
from test_harmony_lattice_recall import C, D, span


def fixture(specs=((0, 2, C),), items=None, points=(0, 1, 2), fifths=0, meter=(4, 4), cap=6):
    items = items or [("c", ("C", 0), 0, 2), ("e", ("E", 0), 0, 2), ("g", ("G", 0), 0, 2)]
    events = []
    notes = []
    for eid, token, a, b in items:
        event = old.note(eid, token, a, b)
        pitch = event["pitch"]
        midi = F({"C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71}[token[0]])+token[1]
        pitch.update(octave=4, midi_pitch=int(midi) if midi.denominator == 1 else None)
        events.append(event)
        notes.append({"note_id": "note_"+eid, "global_onset_quarter": rational(F(a)),
                      "notated_duration_quarter": rational(F(b)-F(a)), "concert_pitch": deepcopy(pitch),
                      "part_id": "part", "voice_id": "v", "measure_id": "m"})
    b, s = old.native(specs, events, points, cap)
    ir = {"ir_document_id": "ir", "score": {"score_id": "score"}, "note_events": notes,
          "sounding_events": events, "measures": [{"global_start_quarter": rational(F(0)),
          "time_signature": {"beats": meter[0], "beat_type": meter[1]}, "key_signature": {"fifths": fifths, "mode_hint": "irrelevant"}}],
          "extensions": {}}
    bind(ir, b)
    return ir, b, s


def bind(ir, b):
    b.update(input_ir_content_sha256=_hash(ir), parent_ir_document_id=ir["ir_document_id"], score_id=ir["score"]["score_id"])


class EvidenceScoringTests(unittest.TestCase):
    def test_full_ir_hash_guard(self):
        ir, b, s = fixture(); ir["measures"][0]["key_signature"]["fifths"] = 2
        with self.assertRaisesRegex(ValueError, "full_ir_context_binding"):
            prepare_with_evidence(ir, b, s)

    def test_event_spelling_binding(self):
        ir, b, s = fixture(); ir["sounding_events"][0]["pitch"]["step"] = "B"; bind(ir, b)
        # Source/lattice synthetic fixtures share event objects, so detach first.
        b["stages"]["lattice"]["events"] = deepcopy(b["stages"]["lattice"]["events"])
        b["stages"]["lattice"]["events"][0]["pitch"]["step"] = "C"
        with self.assertRaisesRegex(ValueError, "clipped_event_source"):
            source_evidence(ir, b)

    def test_key_signature_prior_is_not_local_key(self):
        minor = (("F", 0), (("A", -1), ("C", 0), ("F", 0)))
        major = (("F", 0), (("A", 0), ("C", 0), ("F", 0)))
        ir, b, s = fixture(((0, 2, major), (0, 2, minor)), [("c", ("C", 0), 0, 2), ("f", ("F", 0), 0, 2)], fifths=-4)
        p, ev = prepare_with_evidence(ir, b, s)
        values = {e.signature: run_features(p, ev, e.start, e.end, e.signature)[0] for e in p.edges}
        self.assertEqual(values[major]["missing_member_fraction"], values[minor]["missing_member_fraction"])
        self.assertGreater(values[major]["key_signature_foreign_member"], values[minor]["key_signature_foreign_member"])
        self.assertEqual(decode(p, ev)["selected"]["segments"][0]["members"], minor[1])

    def test_unknown_key_and_meter_masks(self):
        ir, b, s = fixture(fifths=None, meter=(None, None)); p, ev = prepare_with_evidence(ir, b, s)
        f = run_features(p, ev, F(0), F(2), C)[0]
        self.assertIsNone(f["key_signature_foreign_member"])
        self.assertIsNone(f["metric_nonmember_exposure"])
        self.assertIsNone(f["conditional_step_ornament_exposure"])

    def test_different_mode_hint_and_extensions_not_used(self):
        ir, b, s = fixture(); p, ev = prepare_with_evidence(ir, b, s); original = decode(p, ev)
        ir["extensions"]["gold"] = {"local_key": "F_minor", "chord": "wrong"}
        ir["measures"][0]["key_signature"]["mode_hint"] = "minor"
        bind(ir, b); p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(original, decode(p, ev))

    def test_same_signature_partitions_have_exact_same_cost(self):
        ir, b, s = fixture(((0, 2, C), (0, 1, C), (1, 2, C)),
                          [("c", ("C", 0), 0, 1), ("e", ("E", 0), 1, 2), ("g", ("G", 0), 1, 2)])
        p, ev = prepare_with_evidence(ir, b, s)
        whole = [e.group_id for e in p.edges if (e.start_index, e.end_index) == (0, 2)]
        pieces = [next(e.group_id for e in p.edges if (e.start_index, e.end_index) == pair) for pair in ((0, 1), (1, 2))]
        for arm in (True, False):
            self.assertEqual(score_path(p, ev, whole, musical_evidence=arm), score_path(p, ev, pieces, musical_evidence=arm))
        self.assertEqual(len(decode(p, ev)["selected"]["harmonic_runs"]), 1)

    def test_same_signature_path_available_without_whole_edge(self):
        ir, b, s = fixture(((0, 1, C), (1, 2, C))); p, ev = prepare_with_evidence(ir, b, s)
        result = decode(p, ev); self.assertEqual(len(result["selected"]["segments"]), 2)
        self.assertEqual(len(result["selected"]["harmonic_runs"]), 1)
        self.assertEqual(result["selected"]["score_cost"], rational(score_path(p, ev, [x["semantic_group_ref"] for x in result["selected"]["segments"]])))

    def test_original_raw_cap_is_preserved(self):
        ir, b, s = fixture(((0, 1, C), (1, 2, C)), cap=1); p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(decode(p, ev)["status"], "no_complete_path_under_segment_cap")

    def test_blocker_not_removed_by_union(self):
        ir, b, s = fixture(); p, ev = prepare_with_evidence(ir, b, s)
        e = p.edges[0]; altered = replace(e, features=e.features | {"blocker_exposure": F(1)})
        q = replace(p, edges=(altered,))
        self.assertEqual(score_path(q, ev, [e.group_id])-score_path(p, ev, [e.group_id]), F(1, 4))

    def test_compound_meter_and_syncopation_not_beat_denominator_only(self):
        ir, b, s = fixture(meter=(6, 8)); _, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(metric(ev, F(3, 2)), (F(1), F(3, 2)))
        self.assertEqual(metric(ev, F(1, 2)), (F(1, 2), F(3, 2)))
        self.assertEqual(metric(ev, F(0))[0], 2)

    def test_strict_passing_geometry_bonus_not_exemption(self):
        ir, b, s = fixture(items=[("c", ("C", 0), 0, F(1, 2)), ("d", ("D", 0), F(1, 2), 1), ("e", ("E", 0), 1, 2)])
        p, ev = prepare_with_evidence(ir, b, s); f, patterns = run_features(p, ev, F(0), F(2), C)
        self.assertEqual(f["nonmember_exposure"], F(1, 4))
        self.assertEqual(f["conditional_step_ornament_exposure"], F(1, 4))
        self.assertEqual(patterns[0]["kind"], "passing_like")
        self.assertFalse(patterns[0]["confirmed_nct"]); self.assertFalse(patterns[0]["membership_exempted"])

    def test_neighbor_geometry_and_complete_extent(self):
        ir, b, s = fixture(items=[("c", ("C", 0), 0, F(1, 2)), ("d", ("D", 0), F(1, 2), 1), ("c2", ("C", 0), 1, 2)])
        p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(run_features(p, ev, F(0), F(2), C)[1][0]["kind"], "neighbor_like")
        self.assertEqual(run_features(p, ev, F(0), F(1), C)[1], [])

    def test_polyphonic_voice_has_no_fabricated_neighbor_chain(self):
        ir, b, s = fixture(items=[("c", ("C", 0), 0, F(1, 2)), ("g", ("G", 0), 0, F(1, 2)), ("d", ("D", 0), F(1, 2), 1), ("e", ("E", 0), 1, 2)])
        p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(run_features(p, ev, F(0), F(2), C)[1], [])
        self.assertIsNone(run_features(p, ev, F(0), F(2), C)[0]["conditional_step_ornament_exposure"])

    def test_inconsistent_clock_withholds_voice_evidence(self):
        ir, b, s = fixture(items=[("c", ("C", 0), 0, F(1, 2)), ("d", ("D", 0), F(1, 2), 1), ("e", ("E", 0), 1, 2)])
        ir["note_events"][1]["notated_duration_quarter"] = rational(F(1, 4)); bind(ir, b)
        p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(run_features(p, ev, F(0), F(2), C)[1], [])
        self.assertIn("source_clock_or_attack_inconsistent", ev.voice_statuses)

    def test_lowest_sound_observed_not_root(self):
        ir, b, s = fixture(items=[("d", ("D", 0), 0, 2), ("g", ("G", 0), 0, 2)])
        p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(run_features(p, ev, F(0), F(2), C)[0]["lowest_nonmember_exposure"], 1)

    def test_key_tables_and_unsupported(self):
        self.assertEqual(key_alters(-4)["A"], -1); self.assertEqual(key_alters(2)["F"], 1)
        self.assertIsNone(key_alters(8)); self.assertIsNone(key_alters(True))

    def test_exact_dag_matches_exhaustive_union_score(self):
        specs = tuple((a, b, sig) for a in range(3) for b in range(a+1, 4) for sig in (C, D))
        ir, b, s = fixture(specs, points=(0, 1, 2, 3)); p, ev = prepare_with_evidence(ir, b, s)
        paths = []
        def walk(at, ids):
            if at == 3:
                paths.append(ids); return
            for e in p.edges:
                if e.start_index == at: walk(e.end_index, ids+[e.group_id])
        walk(0, [])
        for arm in (True, False):
            expected = min((score_path(p, ev, path, musical_evidence=arm), tuple(path)) for path in paths)
            result = decode(p, ev, musical_evidence=arm)
            self.assertEqual(fraction_value(result["selected"]["score_cost"]), expected[0])
            self.assertEqual(tuple(z["semantic_group_ref"] for z in result["selected"]["segments"]), expected[1])

    def test_resource_abstention_no_approximate_winner(self):
        ir, b, s = fixture(((0, 1, C), (1, 2, C))); p, ev = prepare_with_evidence(ir, b, s)
        r = decode(p, ev, transition_budget=1)
        self.assertIsNone(r["selected"]); self.assertFalse(r["exact_optimum_under_declared_score"])

    def test_full_sound_extent_preserved_beyond_context(self):
        ir, b, s = fixture(items=[("c", ("C", 0), 0, 3)])
        p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(ev.events[0].end, 3)
        self.assertEqual(p.total_note_time, 2)

    def test_full_pitch_octave_binding_not_spelling_only(self):
        ir, b, s = fixture(); ir = deepcopy(ir)
        ir["sounding_events"][0]["pitch"]["octave"] = 5; bind(ir, b)
        with self.assertRaisesRegex(ValueError, "source_binding"):
            source_evidence(ir, b)

    def test_key_change_integrated_exactly(self):
        ir, b, s = fixture()
        ir["measures"].append({"global_start_quarter": rational(F(1)), "time_signature": {"beats": 4, "beat_type": 4}, "key_signature": {"fifths": 1}})
        bind(ir, b); p, ev = prepare_with_evidence(ir, b, s)
        sig = (("F", 0), (("F", 0), ("A", 0), ("C", 0)))
        self.assertEqual(run_features(p, ev, F(0), F(2), sig)[0]["key_signature_foreign_member"], F(1, 6))

    def test_simultaneous_conflicting_key_signatures_abstain(self):
        ir, b, s = fixture(); other = deepcopy(ir["measures"][0]); other["key_signature"]["fifths"] = 2
        ir["measures"].append(other); bind(ir, b); p, ev = prepare_with_evidence(ir, b, s)
        self.assertIsNone(run_features(p, ev, F(0), F(2), C)[0]["key_signature_foreign_member"])

    def test_rest_gap_is_not_step_resolution(self):
        ir, b, s = fixture(items=[("c", ("C", 0), 0, F(1, 4)), ("d", ("D", 0), F(1, 2), 1), ("e", ("E", 0), 1, 2)])
        p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(run_features(p, ev, F(0), F(2), C)[1], [])

    def test_noninteger_microtone_retained_and_unknown(self):
        ir, b, s = fixture(items=[("c", ("C", F(1, 2)), 0, 2)])
        p, ev = prepare_with_evidence(ir, b, s); f = run_features(p, ev, F(0), F(2), C)[0]
        self.assertEqual(f["unresolved_spelling_exposure"], 1)
        self.assertIsNone(f["missing_member_fraction"]); self.assertIsNone(f["lowest_nonmember_exposure"])

    def test_inference_interface_has_no_reference_or_key_answer(self):
        self.assertEqual(tuple(inspect.signature(prepare_with_evidence).parameters), ("ir", "bundle", "search"))
        self.assertNotIn("reference", inspect.signature(decode).parameters)

    def test_inputs_not_mutated(self):
        ir, b, s = fixture(); before = deepcopy((ir, b, s)); p, ev = prepare_with_evidence(ir, b, s)
        decode(p, ev); self.assertEqual((ir, b, s), before)

    def test_cache_reuse_and_cold_recomputation_identical(self):
        ir, b, s = fixture(((0, 2, C), (0, 1, D), (1, 2, C))); p, ev = prepare_with_evidence(ir, b, s)
        first = decode(p, ev); self.assertTrue(ev._feature_cache); self.assertTrue(ev._metric_cache)
        self.assertEqual(first, decode(p, ev))
        ev._feature_cache.clear(); ev._metric_cache.clear()
        self.assertEqual(first, decode(p, ev))

    def test_triplet_grid_integer_score_is_exact_not_quantized(self):
        specs = ((0, 2, C), (0, 1, C), (1, 2, D))
        ir, b, s = fixture(specs, points=(0, F(1, 3), 1), items=[
            ("c", ("C", 0), 0, F(1, 3)), ("d", ("D", 0), F(1, 3), F(2, 3)), ("e", ("E", 0), F(2, 3), 1)])
        p, ev = prepare_with_evidence(ir, b, s); r = decode(p, ev)
        ids = [z["semantic_group_ref"] for z in r["selected"]["segments"]]
        self.assertEqual(fraction_value(r["selected"]["score_cost"]), score_path(p, ev, ids))

    def test_tied_preparation_full_clock_consistency(self):
        ir, b, s = fixture(items=[("c", ("C", 0), 0, F(1, 2)), ("d", ("D", 0), F(1, 2), 1), ("e", ("E", 0), 1, 2)])
        n = ir["note_events"][0]; second = deepcopy(n)
        n["notated_duration_quarter"] = rational(F(1, 4))
        second.update(note_id="tie_c", global_onset_quarter=rational(F(1, 4)), notated_duration_quarter=rational(F(1, 4)))
        ir["note_events"].append(second); ir["sounding_events"][0]["source_note_ids"].append("tie_c")
        bind(ir, b); p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(run_features(p, ev, F(0), F(2), C)[1][0]["kind"], "passing_like")
        second["voice_id"] = "other"; bind(ir, b); p, ev = prepare_with_evidence(ir, b, s)
        self.assertEqual(run_features(p, ev, F(0), F(2), C)[1], [])


def fraction_value(v):
    return F(v["numerator"], v["denominator"])
