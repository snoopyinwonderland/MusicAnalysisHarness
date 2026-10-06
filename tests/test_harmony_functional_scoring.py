from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import inspect
import unittest

from musicanote_harness.harmony_candidate_recall import fraction
from musicanote_harness.harmony_evidence_scoring import prepare_with_evidence, decode as old_decode
from musicanote_harness.harmony_functional_scoring import (
    decode, dominant_pairs, interval_surface, pair_features, prepare_functional_evidence,
    score_path, shapes, six_four_surface, supply,
)
from musicanote_harness.seventh_context import chord
from test_harmony_evidence_scoring import bind, fixture


def sig(root, quality):
    return tuple(root), tuple(sorted(map(tuple, chord(root, quality)["members"])))


C = sig(("C", 0), "M"); G = sig(("G", 0), "M"); G7 = sig(("G", 0), "Mm7")
F64 = (("G", 0), C[1])


def example(specs=None, polyphonic=False, missing=False, lowest="G", points=(0, 1, 2)):
    items = [("bass", (lowest, 0), 0, 2), ("c", ("C", 0), 0, 1),
             ("e", ("E", 0), 0, 1), ("b", ("B", 0), 1, 2), ("d", ("D", 0), 1, 2)]
    if missing:
        items = [r for r in items if r[0] != "e"]
    ir, bundle, search = fixture(specs or ((0, 1, C), (1, 2, G)), items, points)
    octaves = {"bass": 3, "c": 4, "e": 4, "b": 3, "d": 4}
    voices = {"bass": "bass", "c": "v1", "b": "v1", "e": "v2", "d": "v2"}
    for sound in ir["sounding_events"]:
        eid = sound["sounding_event_id"]; pitch = sound["pitch"]
        pitch["octave"] = octaves[eid]
        pitch["midi_pitch"] = 12*(pitch["octave"]+1)+dict(zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11)))[pitch["step"]]
        n = next(n for n in ir["note_events"] if n["note_id"] == "note_"+eid)
        n["concert_pitch"] = deepcopy(pitch); n["voice_id"] = "poly" if polyphonic and eid != "bass" else voices[eid]
    bind(ir, bundle); p, source = prepare_with_evidence(ir, bundle, search)
    return ir, bundle, search, p, prepare_functional_evidence(ir, source)


class FunctionalScoringTests(unittest.TestCase):
    def test_surface_vocabulary_and_no_functional_root_erasure(self):
        self.assertEqual(shapes(C), ("M",))
        self.assertEqual(six_four_surface(F64), (("C", 0), "M"))
        self.assertIsNone(six_four_surface(C))

    def test_original_edges_points_cap_and_ir_preserved(self):
        ir, _, _, p, ev = example(); original = deepcopy(ir)
        q, receipts = supply(p, ev)
        self.assertEqual(q.edges[:len(p.edges)], p.edges); self.assertEqual(q.points, p.points)
        self.assertEqual(q.max_segments, p.max_segments); self.assertEqual(ir, original)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["surface_root_spelling"], ("C", 0))
        self.assertFalse(receipts[0]["function_confirmed"])

    def test_lowest_fifth_required_not_pitch_class_only(self):
        _, _, _, p, ev = example(lowest="C")
        self.assertEqual(supply(p, ev)[1], [])

    def test_complete_observed_union_required(self):
        _, _, _, p, ev = example(missing=True)
        self.assertEqual(supply(p, ev)[1], [])

    def test_spelling_preserved(self):
        ir, b, s, *_ = example()
        event = next(r for r in ir["sounding_events"] if r["sounding_event_id"] == "c")
        event["pitch"].update(step="B", octave=3, alter={"numerator": 1, "denominator": 1})
        next(n for n in ir["note_events"] if n["note_id"] == "note_c")["concert_pitch"] = deepcopy(event["pitch"])
        # Fresh native membership receipt for the changed observation.
        import test_harmony_scored_decoder as old
        b2, s2 = old.native(((0, 1, C), (1, 2, G)), ir["sounding_events"], (0, 1, 2))
        bind(ir, b2); p, source = prepare_with_evidence(ir, b2, s2)
        self.assertEqual(supply(p, prepare_functional_evidence(ir, source))[1], [])

    def test_six_four_direct_geometry_changes_actual_selection(self):
        _, _, _, p, ev = example(); q, _ = supply(p, ev)
        f, details = pair_features(ev, F(0), F(1), F(2), F64, G)
        self.assertEqual(f["six_four_surface_and_held_bass"], 1)
        self.assertEqual(f["six_four_direct_upper_paths"], 1)
        result = decode(q, ev)
        self.assertEqual(result["selected"]["segments"][0]["root_spelling"], ("G", 0))
        self.assertEqual(result["selected"]["harmonic_runs"][0]["surface_root_spelling"], ("C", 0))
        self.assertFalse(result["selected"]["functional_pairs"][0]["function_confirmed"])
        self.assertIsNone(result["selected"]["functional_pairs"][0]["cadence"])

    def test_polyphonic_upper_voice_is_not_guessed(self):
        _, _, _, p, ev = example(polyphonic=True)
        f, _ = pair_features(ev, F(0), F(1), F(2), F64, G)
        self.assertEqual(f["six_four_surface_and_held_bass"], 1)
        self.assertEqual(f["six_four_direct_upper_paths"], 0)
        self.assertEqual(ev.links, ())

    def test_next_raw_edge_cut_does_not_censor_arrival_evidence(self):
        _, _, _, _, ev = example()
        self.assertEqual(pair_features(ev, F(0), F(1), F(2), F64, G),
                         pair_features(ev, F(0), F(1), F(3, 2), F64, G))

    def test_source_clock_mismatch_withholds_direct_upper_link(self):
        ir, b, s, *_ = example()
        next(n for n in ir["note_events"] if n["note_id"] == "note_c")["notated_duration_quarter"] = {"numerator": 1, "denominator": 2}
        bind(ir, b); p, source = prepare_with_evidence(ir, b, s); ev = prepare_functional_evidence(ir, source)
        f, _ = pair_features(ev, F(0), F(1), F(2), F64, G)
        self.assertEqual(f["six_four_direct_upper_paths"], 0)
        self.assertIn("unavailable_voice_clock", ev.voice_statuses)

    def test_literal_surface_without_following_resolution_remains_alternative(self):
        _, _, _, p, ev = example(specs=((0, 2, C),))
        q, receipt = supply(p, ev)
        self.assertEqual(len(receipt), 1)
        chosen = decode(q, ev)
        self.assertEqual(chosen["selected"]["segments"][0]["root_spelling"], C[0])
        self.assertEqual(chosen["selected"]["functional_pairs"], [])

    def test_actual_leading_tone_and_seventh_paths(self):
        items = [("g", ("G", 0), 0, 1), ("b", ("B", 0), 0, 1), ("d", ("D", 0), 0, 1), ("f", ("F", 0), 0, 1),
                 ("c3", ("C", 0), 1, 2), ("c4", ("C", 0), 1, 2), ("g4", ("G", 0), 1, 2), ("e", ("E", 0), 1, 2)]
        ir, b, s = fixture(((0, 1, G7), (1, 2, C)), items)
        lanes = {"g": "bass", "c3": "bass", "b": "v1", "c4": "v1", "d": "v2", "g4": "v2", "f": "v3", "e": "v3"}
        for sound in ir["sounding_events"]:
            eid = sound["sounding_event_id"]; pitch = sound["pitch"]
            pitch["octave"] = 3 if eid in ("g", "b", "c3") else 4
            pitch["midi_pitch"] = 12*(pitch["octave"]+1)+dict(zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11)))[pitch["step"]]
            n = next(n for n in ir["note_events"] if n["note_id"] == "note_"+eid)
            n["voice_id"] = lanes[eid]; n["concert_pitch"] = deepcopy(pitch)
        bind(ir, b); p, source = prepare_with_evidence(ir, b, s); ev = prepare_functional_evidence(ir, source)
        f, detail = pair_features(ev, F(0), F(1), F(2), G7, C)
        self.assertEqual(f["dominant_family_leading_tone"], 1)
        self.assertEqual(f["dominant_family_seventh_step"], 1)
        r = decode(p, ev)
        self.assertEqual(r["selected"]["functional_pairs"][0]["secondary_vs_primary"], "unresolved_without_local_key")
        self.assertTrue(all(not d["function_confirmed"] for d in detail))

    def test_chosen_next_chord_not_possible_next_receipt_drives_bonus(self):
        _, _, _, p, ev = example()
        f, detail = pair_features(ev, F(0), F(1), F(2), F64, C)
        self.assertTrue(all(v == 0 for v in f.values())); self.assertEqual(detail, [])

    def test_no_direct_resolution_is_not_negative_evidence(self):
        _, _, _, _, ev = example(polyphonic=True)
        f, _ = pair_features(ev, F(0), F(1), F(2), G7, C)
        self.assertEqual(f["dominant_family_leading_tone"], 0)
        self.assertTrue(all(v >= 0 for v in f.values()))

    def test_applied_vocabulary_uses_minor_targets_and_inversions(self):
        self.assertEqual(dominant_pairs(G7, C)[0][0], "V7")
        cm = sig(("C", 0), "m")
        self.assertEqual(dominant_pairs(G7, cm)[0][0], "V7")
        leading = sig(("B", 0), "o7")
        self.assertEqual(dominant_pairs(leading, cm)[0][0], "vii7")
        # Same MIDI but wrong spelling cannot be a leading-tone family.
        enharmonic = (("C", -1), leading[1])
        self.assertEqual(dominant_pairs(enharmonic, cm), ())

    def test_seventh_chord_can_be_selected_target(self):
        self.assertEqual(dominant_pairs(G7, sig(("C", 0), "Mm7"))[0][0], "V7")
        self.assertEqual(dominant_pairs(sig(("B", 0), "o"), sig(("C", 0), "Mm7"))[0][0], "vii")
        self.assertEqual(dominant_pairs(G7, sig(("C", 0), "mm7"))[0][0], "V7")

    def test_full_source_binding(self):
        ir, _, _, _, ev = example(); ir["score"]["title"] = "different"
        with self.assertRaisesRegex(ValueError, "functional_source_ir_binding"):
            prepare_functional_evidence(ir, ev.source)

    def test_supply_is_deterministic_and_deduplicated(self):
        _, _, _, p, ev = example(); q, r = supply(p, ev)
        self.assertEqual((q, r), supply(p, ev)); self.assertEqual(supply(q, ev)[1], [])

    def test_nonready_status_is_preserved(self):
        _, _, _, p, ev = example(); p = replace(p, status="edge_budget_abstention")
        self.assertEqual(supply(p, ev), (p, [])); self.assertIsNone(decode(p, ev)["selected"])

    def test_blocker_remains_on_functional_alternative(self):
        _, _, _, p, ev = example(); first = p.edges[0]
        p = replace(p, edges=(replace(first, blockers=("unknown",), features=first.features | {"blocker_exposure": F(1)}),)+p.edges[1:])
        q, _ = supply(p, ev)
        added = q.edges[-1]
        self.assertEqual(added.blockers, ("unknown",)); self.assertEqual(added.features["blocker_exposure"], 1)

    def test_budget_abstains_without_approximate_selection(self):
        _, _, _, p, ev = example(); q, _ = supply(p, ev)
        result = decode(q, ev, transition_budget=1)
        self.assertIsNone(result["selected"]); self.assertEqual(result["transitions"], 1)
        self.assertFalse(result["exact_optimum_under_declared_score"])

    def test_raw_cap_not_bypassed(self):
        _, _, _, p, ev = example(); q, _ = supply(replace(p, max_segments=1), ev)
        self.assertEqual(decode(q, ev)["status"], "no_complete_path_under_segment_cap")

    def test_exact_decoder_matches_exhaustive_paths(self):
        specs = ((0, 1, C), (0, 1, G7), (1, 2, C), (1, 2, G), (0, 2, C), (0, 2, G7))
        _, _, _, p, ev = example(specs); q, _ = supply(p, ev); paths = []
        def walk(at, ids):
            if at == len(q.points)-1:
                paths.append(ids); return
            for e in q.edges:
                if e.start_index == at: walk(e.end_index, ids+[e.group_id])
        walk(0, [])
        for enabled in (False, True):
            expected = min((score_path(q, ev, ids, functional_evidence=enabled), tuple(ids)) for ids in paths)
            result = decode(q, ev, functional_evidence=enabled)
            self.assertEqual(fraction(result["selected"]["score_cost"]), expected[0])
            self.assertEqual(tuple(s["semantic_group_ref"] for s in result["selected"]["segments"]), expected[1])

    def test_split_left_run_has_same_score(self):
        specs = ((0, 1, C), (1, 2, C), (0, 2, C), (2, 3, G))
        _, _, _, p, ev = example(specs, points=(0, F(1, 2), 1, 2)); q, _ = supply(p, ev)
        select = lambda a, b, s: next(e.group_id for e in q.edges if (e.start_index, e.end_index, e.signature) == (a, b, s))
        whole = [select(0, 2, F64), select(2, 3, G)]
        split = [select(0, 1, F64), select(1, 2, F64), select(2, 3, G)]
        self.assertEqual(score_path(q, ev, whole), score_path(q, ev, split))

    def test_extensions_mode_and_title_not_inference_inputs(self):
        ir, b, s, p, ev = example(); q, _ = supply(p, ev); before = decode(q, ev)
        ir["extensions"]["answers"] = {"local_key": "anything", "chord": "anything"}
        ir["score"]["title"] = "secret answer"; ir["measures"][0]["key_signature"]["mode_hint"] = "minor"
        bind(ir, b); p, source = prepare_with_evidence(ir, b, s); ev = prepare_functional_evidence(ir, source); q, _ = supply(p, ev)
        self.assertEqual(before, decode(q, ev))

    def test_no_new_features_control_reproduces_old_cost_when_no_new_candidate(self):
        _, _, _, p, ev = example(lowest="C"); q, receipts = supply(p, ev)
        self.assertEqual(receipts, [])
        original = old_decode(p, ev.source)
        actual = decode(q, ev, functional_evidence=False)
        self.assertEqual(original["selected"]["score_cost"], actual["selected"]["score_cost"])
        self.assertEqual([s["semantic_group_ref"] for s in original["selected"]["segments"]], [s["semantic_group_ref"] for s in actual["selected"]["segments"]])


if __name__ == "__main__":
    unittest.main()
