import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from musicanote_harness.harmony_surface import analyze_surface
from musicanote_harness.harmony_unfolded import analyze_unfolded


def rat(value):
    return {"numerator": value, "denominator": 1}


def score_with_notes(note_specs):
    return {
        "score": {"score_id": "score_fixture"}, "ir_document_id": "ir_fixture",
        "measures": [{"measure_id": "m1", "sequential_measure_index": 0,
                      "global_start_quarter": rat(0), "actual_duration_quarter": rat(2),
                      "time_signature": {"beats": 2, "beat_type": 4}}],
        "sounding_events": [{"sounding_event_id": f"s{index}", "source_note_ids": [f"n{index}"],
                             "pitch": {"midi_pitch": midi}, "span": {"start": rat(start), "end": rat(end)}}
                            for index, (midi, start, end) in enumerate(note_specs)],
    }


class UnfoldedHarmonyTest(unittest.TestCase):
    def test_arpeggio_across_beats_recovers_complete_chord(self):
        ir = score_with_notes([(60, 0, 1), (64, 0, 1), (67, 1, 2)])
        self.assertEqual([w["status"] for w in analyze_surface(ir)["windows"]], ["abstained", "abstained"])
        unfolded = analyze_unfolded(ir)
        self.assertEqual(unfolded["input_policy"], "blind_canonical_ir_only")
        self.assertEqual(len(unfolded["segments"]), 1)
        self.assertEqual(unfolded["segments"][0]["span"], {"start": rat(0), "end": rat(2)})
        self.assertEqual(unfolded["segments"][0]["candidates"][0]["label"], "C:major")
        self.assertEqual(unfolded["segments"][0]["note_ids"], ["n0", "n1", "n2"])
        schema = json.loads((Path(__file__).resolve().parents[1] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "unfolded_harmony_pilot.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(unfolded)

    def test_clear_local_chord_change_is_not_smoothed_away(self):
        ir = score_with_notes([(60, 0, 1), (64, 0, 1), (67, 0, 1),
                               (55, 1, 2), (59, 1, 2), (62, 1, 2)])
        unfolded = analyze_unfolded(ir)
        self.assertEqual(len(unfolded["segments"]), 2)
        self.assertEqual([part["candidates"][0]["label"] for part in unfolded["segments"]], ["C:major", "G:major"])
        self.assertEqual(unfolded, analyze_unfolded({**ir, "imported_annotations": [{"label": "I"}]}))


if __name__ == "__main__":
    unittest.main()
