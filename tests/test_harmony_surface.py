import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from musicanote_harness.harmony_surface import analyze_surface
from musicanote_harness.harmony_surface_eval import evaluate_simple_dcml


def rat(value):
    return {"numerator": value, "denominator": 1}


class SurfaceHarmonyTest(unittest.TestCase):
    def test_blind_beat_windows_and_explicit_rest(self):
        ir = {
            "score": {"score_id": "score_fixture"},
            "ir_document_id": "ir_fixture",
            "measures": [{
                "measure_id": "m1", "sequential_measure_index": 0,
                "global_start_quarter": rat(0), "actual_duration_quarter": rat(2),
                "time_signature": {"beats": 2, "beat_type": 4},
            }],
            "sounding_events": [{
                "sounding_event_id": f"s{pitch}", "source_note_ids": [f"n{pitch}"],
                "pitch": {"midi_pitch": pitch}, "span": {"start": rat(0), "end": rat(1)},
            } for pitch in (60, 64, 67)],
        }
        result = analyze_surface(ir)
        self.assertEqual(result["input_policy"], "blind_canonical_ir_only")
        self.assertEqual(result["summary"]["window_count"], 2)
        self.assertEqual(result["windows"][0]["status"], "candidate")
        self.assertEqual(result["windows"][0]["candidates"][0]["label"], "C:major")
        self.assertEqual(result["windows"][0]["candidates"][0]["fit_score"], 1.0)
        self.assertEqual(result["windows"][1]["status"], "rest")
        self.assertEqual(result["windows"][1]["span"]["start"], rat(1))
        self.assertEqual(result, analyze_surface({**ir, "imported_annotations": [{"label": "V7"}]}))
        schema = json.loads((Path(__file__).resolve().parents[1] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "surface_harmony_pilot.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(result)

    def test_two_pitch_classes_abstain_without_claiming_chord(self):
        ir = {
            "score": {"score_id": "score_fixture"}, "ir_document_id": "ir_fixture",
            "measures": [{"measure_id": "m1", "sequential_measure_index": 0,
                          "global_start_quarter": rat(0), "actual_duration_quarter": rat(1),
                          "time_signature": {"beats": 1, "beat_type": 4}}],
            "sounding_events": [{"sounding_event_id": f"s{midi}", "source_note_ids": [f"n{midi}"],
                                 "pitch": {"midi_pitch": midi}, "span": {"start": rat(0), "end": rat(1)}}
                                for midi in (60, 64)],
        }
        window = analyze_surface(ir)["windows"][0]
        self.assertEqual(window["status"], "abstained")
        self.assertEqual(window["abstention_reason"], "fewer_than_three_pitch_classes")
        self.assertIsNone(window["display_hint_index"])

    def test_source_labels_are_visible_only_to_separate_scorer(self):
        surface = {
            "score_id": "score_fixture", "input_policy": "blind_canonical_ir_only",
            "windows": [{
                "window_id": "w1", "span": {"start": rat(0), "end": rat(1)},
                "status": "candidate", "display_hint_index": 0,
                "candidates": [{"label": "F:major", "template_pitch_classes": [0, 5, 9]}],
            }],
        }
        annotations = [{
            "annotation_id": "a1", "target": {"span": {"start": rat(0), "end": rat(1)}},
            "components": {"chord": "I", "globalkey": "F", "localkey": "I"},
        }]
        alignments = [{"annotation_id": "a1", "mapping_status": "exact"}]
        report = evaluate_simple_dcml(surface, annotations, alignments)
        self.assertEqual(report["eligible_windows"], 1)
        self.assertEqual(report["top1_template_equal"], 1)
        self.assertEqual(report["scorer_input_policy"], "source_annotations_visible_to_scorer_only")
        alignments[0]["mapping_status"] = "ambiguous"
        self.assertEqual(evaluate_simple_dcml(surface, annotations, alignments)["eligible_windows"], 0)


if __name__ == "__main__":
    unittest.main()
