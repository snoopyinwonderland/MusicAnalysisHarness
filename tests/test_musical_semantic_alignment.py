from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.musical_semantic_intake import prepare_source_statements
from musicanote_harness import musical_semantic_alignment as alignment
from musicanote_harness import musical_pattern_observation as pattern
from test_musical_pattern_observation import make_ir


class MusicalSemanticAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ir = make_ir(self.root)

    def prepare(self, text="Pedal: C m1 b1 m2 b2", signature="4/4"):
        path = self.root / "analysis.txt"
        path.write_text(f"Time Signature: {signature}\n{text}\nm1 C: I\nm2 V\nm3 I\n", encoding="utf-8")
        record = prepare_source_statements(path, corpus_root=self.root)["records"][0]
        index = alignment.prepare_meter_index(path)
        return record, index

    def test_exact_half_open_coordinates_not_role(self):
        source, index = self.prepare()
        original = deepcopy(source)
        result = alignment.align_statement(source, self.ir, index)
        self.assertEqual(result["status"], "exact_coordinate")
        self.assertEqual(result["binding"]["target_span"], {"start": pattern.q(0), "end": pattern.q(5)})
        self.assertFalse(result["semantics"]["pedal_lane_identified"])
        self.assertFalse(result["semantics"]["musical_role_validated"])
        self.assertEqual(source, original)
        alignment.validate_alignment(result, source=source, ir=self.ir, meter_index=index)
        self.assertEqual(alignment.align_statement(source, self.ir, index), result)

    def test_pitch_token_not_required_to_be_pitch_or_chord_degree(self):
        source, index = self.prepare("Pedal: 3 m1 b1 m2 b1")
        result = alignment.align_statement(source, self.ir, index)
        self.assertEqual(result["status"], "exact_coordinate")
        self.assertEqual(result["literal_pitch_token"], "3")

    def test_missing_beat_and_typos_are_not_repaired(self):
        for text in ("Pedal: C m1 m2 b1", "Pedal: C m1 b1 mm2 b2", "Pedal: C m1 b1 b2 b1"):
            source, index = self.prepare(text)
            result = alignment.align_statement(source, self.ir, index)
            self.assertEqual(result["status"], "deferred")
            self.assertIn("explicit_two_beats_required", result["reasons"][0])

    def test_empty_and_reversed_ranges_not_extended(self):
        for text in ("Pedal: C m1 b1 m1 b1", "Pedal: C m2 b1 m1 b1"):
            source, index = self.prepare(text)
            result = alignment.align_statement(source, self.ir, index)
            self.assertEqual(result["reasons"], ["empty_or_reversed_pedal_range"])

    def test_exact_decimal_and_rounded_triplets_differ(self):
        source, index = self.prepare("Pedal: C m1 b1.25 m2 b2.5")
        result = alignment.align_statement(source, self.ir, index)
        self.assertEqual(result["binding"]["target_span"], {"start": pattern.q(Fraction(1, 4)), "end": pattern.q(Fraction(11, 2))})
        for beat in ("1.33", "1.66", "1.67", "1.333"):
            source, index = self.prepare(f"Pedal: C m1 b{beat} m2 b1")
            self.assertEqual(alignment.align_statement(source, self.ir, index)["reasons"], ["rounded_or_nonbinary_beat_requires_review"])

    def test_simple_vs_compound_meter_grid(self):
        source, index = self.prepare("Pedal: C m1 b2 m2 b1", "6/8")
        ir = deepcopy(self.ir)
        for number, measure in enumerate(ir["measures"]):
            measure.update(time_signature={"beats": 6, "beat_type": 8}, global_start_quarter=pattern.q(3 * number),
                           actual_duration_quarter=pattern.q(3), nominal_duration_quarter=pattern.q(3))
        # Only the coordinate unit is under test; remove events/links to avoid
        # manufacturing a false 6/8 performance from the 4/4 fixture.
        for key in ("note_events", "rest_events", "sounding_events", "tie_chains", "attack_events", "chord_onset_groups"):
            ir[key] = []
        result = alignment.align_statement(source, ir, index)
        self.assertEqual(result["status"], "exact_coordinate")
        self.assertEqual(result["binding"]["target_span"]["start"], pattern.q(Fraction(3, 2)))

    def test_mismatched_missing_and_duplicate_measure_deferred(self):
        for kind in ("meter", "missing", "duplicate", "pickup", "irregular"):
            source, index = self.prepare()
            ir = deepcopy(self.ir)
            if kind == "meter":
                index["measures"][0]["numerator"] = 3
            elif kind == "missing":
                index["measures"].pop(0)
            elif kind == "duplicate":
                index["measures"].append(deepcopy(index["measures"][0]))
            elif kind == "pickup":
                ir["measures"][0]["pickup"] = True
            else:
                ir["measures"][0]["actual_duration_quarter"] = pattern.q(3)
            with self.subTest(kind=kind):
                self.assertEqual(alignment.align_statement(source, ir, index)["status"], "deferred")

    def test_free_prose_and_form_not_keyword_classified(self):
        for text, reason in (("Note: C m1 b1 m2 b1 arpeggio passing tone", "free_prose_requires_review"),
                             ("Form: accompaniment m1 m2", "form_anchor_not_complete_extent")):
            source, index = self.prepare(text)
            result = alignment.align_statement(source, self.ir, index)
            self.assertIsNone(result["binding"])
            self.assertEqual(result["reasons"], [reason])

    def test_stale_source_and_missing_source_meter(self):
        source, index = self.prepare()
        index["source_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "stale_meter_index"):
            alignment.align_statement(source, self.ir, index)
        source, index = self.prepare()
        index.update(status="missing_explicit_source_meter", measures=[])
        self.assertEqual(alignment.align_statement(source, self.ir, index)["reasons"], ["missing_explicit_source_meter"])

    def test_late_declaration_does_not_certify_parser_initial_default(self):
        path = self.root / "analysis.txt"
        path.write_text("Pedal: C m1 b1 m2 b1\nm1 C: I\nTime Signature: 3/4\nm2 V\n", encoding="utf-8")
        source = prepare_source_statements(path, corpus_root=self.root)["records"][0]
        index = alignment.prepare_meter_index(path)
        self.assertEqual(index["status"], "missing_initial_source_meter")
        self.assertEqual(alignment.align_statement(source, self.ir, index)["reasons"], ["missing_initial_source_meter"])

    def test_tamper_and_resealed_wrong_coordinate_rejected_by_replay(self):
        source, index = self.prepare()
        result = alignment.align_statement(source, self.ir, index)
        result["binding"]["target_span"]["end"] = pattern.q(6)
        with self.assertRaisesRegex(ValueError, "seal_mismatch"):
            alignment.validate_alignment(result)
        payload = {k: v for k, v in result.items() if k not in ("record_id", "record_sha256")}
        result["record_sha256"] = pattern.digest(payload)
        result["record_id"] = "msa_" + result["record_sha256"][:24]
        with self.assertRaisesRegex(ValueError, "replay_mismatch"):
            alignment.validate_alignment(result, source=source, ir=self.ir, meter_index=index)


if __name__ == "__main__":
    unittest.main()
