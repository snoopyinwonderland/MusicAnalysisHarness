from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from music21 import converter, meter, note, stream, tie
from jsonschema.exceptions import ValidationError

from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.formal_ir import FormalIRAdapter
from musicanote_harness import musical_pattern_observation as pattern


def make_ir(directory, *, grace=False):
    score = stream.Score()
    for part_index in range(2):
        part = stream.Part(id=f"P{part_index}")
        for number in range(1, 4):
            measure = stream.Measure(number=number)
            if number == 1:
                measure.append(meter.TimeSignature("4/4"))
            if part_index == 0:
                if grace and number == 2:
                    measure.append(note.Note("B3").getGrace())
                if number == 1:
                    event = note.Note("C4", quarterLength=4)
                    event.tie = tie.Tie("start")
                    measure.append(event)
                elif number == 2:
                    event = note.Note("C4", quarterLength=2)
                    event.tie = tie.Tie("stop")
                    measure.append(event)
                    measure.append(note.Note("F#4", quarterLength=2))
                else:
                    measure.append(note.Rest(quarterLength=4))
            else:
                measure.append(note.Note("G2", quarterLength=2))
                measure.append(note.Note("D3", quarterLength=2))
            part.append(measure)
        score.append(part)
    path = Path(directory) / "score.musicxml"
    score.write("musicxml", fp=path)
    parsed = converter.parse(path)
    return FormalIRAdapter().convert(CanonicalIRBuilder().build(parsed, path), path)


def scope_for(ir, start=4, end=6, context_start=4, context_end=8):
    return {"case_id": "synthetic-case", "score_id": ir["score"]["score_id"],
            "ir_document_id": ir["ir_document_id"], "ir_content_sha256": pattern.digest(ir),
            "source_files": deepcopy(ir["source_files"]),
            "source_statement_ref": {"record_id": "source-fixture", "record_sha256": "a" * 64},
            "alignment_ref": {"record_id": "alignment-fixture", "record_sha256": "b" * 64},
            "target_span": {"start": pattern.q(start), "end": pattern.q(end)},
            "context_span": {"start": pattern.q(context_start), "end": pattern.q(context_end)}}


class MusicalPatternObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ir = make_ir(self.temp.name)
        self.scope = scope_for(self.ir)

    def test_exact_projection_and_input_immutability(self):
        original = deepcopy(self.ir)
        observation = pattern.observe(self.ir, self.scope)
        pattern.validate_observation(observation, ir=self.ir, scope=self.scope)
        self.assertEqual(self.ir, original)
        for event in pattern.reconstruct(observation):
            self.assertIn(event, [*self.ir["note_events"], *self.ir["rest_events"]])
        self.assertEqual(pattern.observe(self.ir, self.scope), observation)

    def test_tie_outside_window_keeps_original_attack_context(self):
        observation = pattern.observe(self.ir, self.scope)
        first = next(slot for slot in observation["slots"] if slot["core_event"].get("tie_role") == "start")
        self.assertEqual(first["target_relation"], "linked_context_only")
        self.assertEqual(first["context_relation"], "linked_context_only")
        self.assertEqual(first["relative_onset_quarter"], pattern.q(-4))
        self.assertEqual(first["core_event"]["notated_duration_quarter"], pattern.q(4))
        self.assertEqual(len(observation["core_projection"]["tie_chains"]), 1)
        chain = observation["core_projection"]["tie_chains"][0]
        self.assertEqual(chain["source_note_ids"], self.ir["tie_chains"][0]["source_note_ids"])

    def test_exclusive_end_and_all_parts(self):
        observation = pattern.observe(self.ir, self.scope)
        end_note = next(slot for slot in observation["slots"] if slot["core_event"].get("written_pitch", {}).get("spelling") == "F#4")
        self.assertEqual(end_note["target_relation"], "linked_context_only")
        self.assertEqual(end_note["context_relation"], "overlap")
        self.assertEqual(len(observation["raw_lanes"]), 2)
        self.assertEqual({slot["core_event"]["part_id"] for slot in observation["slots"]}, {p["part_id"] for p in self.ir["parts"]})

    def test_fraction_overlap_does_not_shorten_original_duration(self):
        scope = scope_for(self.ir, Fraction(9, 2), Fraction(17, 3), 4, 8)
        observation = pattern.observe(self.ir, scope)
        slot = next(row for row in observation["slots"] if row["core_event"].get("tie_role") == "stop")
        self.assertEqual(slot["target_overlap"], scope["target_span"])
        self.assertEqual(slot["core_event"]["notated_duration_quarter"], pattern.q(2))

    def test_rests_preserved(self):
        observation = pattern.observe(self.ir, scope_for(self.ir, 8, 12, 4, 12))
        rests = [slot for slot in observation["slots"] if slot["event_kind"] == "rest"]
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0]["core_event"]["notated_duration_quarter"], pattern.q(4))

    def test_grace_point_included_not_a_sounding_duration_claim(self):
        ir = make_ir(self.temp.name, grace=True)
        observation = pattern.observe(ir, scope_for(ir))
        grace = [slot for slot in observation["slots"] if slot["core_event"].get("grace", {}).get("is_grace")]
        self.assertEqual(len(grace), 1)
        self.assertEqual(grace[0]["target_relation"], "point_inside")
        self.assertIsNone(grace[0]["target_overlap"])

    def test_stale_ir_and_source_hash_fail(self):
        scope = deepcopy(self.scope)
        scope["ir_content_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "stale_or_foreign_scope"):
            pattern.observe(self.ir, scope)
        scope = deepcopy(self.scope)
        scope["source_files"][0]["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "stale_or_foreign_scope"):
            pattern.observe(self.ir, scope)

    def test_duplicate_ids_and_dangling_refs_fail(self):
        for mode in ("duplicate", "source", "anchor", "time"):
            with self.subTest(mode=mode):
                ir = deepcopy(self.ir)
                if mode == "duplicate":
                    ir["note_events"].append(deepcopy(ir["note_events"][0]))
                elif mode == "source":
                    ir["note_events"][0]["source_ref_id"] = "missing-source"
                elif mode == "anchor":
                    ir["note_events"][0]["grace"]["anchor_note_id"] = "missing-anchor"
                else:
                    ir["note_events"][0]["global_onset_quarter"] = pattern.q(1)
                with self.assertRaises(ValueError):
                    pattern.observe(ir, scope_for(ir))

    def test_empty_outside_and_reversed_ranges_fail(self):
        for start, end in ((4, 4), (6, 4), (-1, 4), (4, 13)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                pattern.observe(self.ir, scope_for(self.ir, start, end, 0, 12))

    def test_tamper_and_resealed_omission_detected_by_replay(self):
        observation = pattern.observe(self.ir, self.scope)
        observation["slots"].pop()
        with self.assertRaisesRegex(ValueError, "seal_mismatch"):
            pattern.validate_observation(observation)
        payload = {k: v for k, v in observation.items() if k not in ("record_id", "record_sha256")}
        observation["record_sha256"] = pattern.digest(payload)
        observation["record_id"] = "mpo_" + observation["record_sha256"][:24]
        with self.assertRaisesRegex(ValueError, "reconstruction_mismatch"):
            pattern.validate_observation(observation, ir=self.ir)

    def test_roles_and_training_cannot_be_promoted(self):
        for field in ("roles_assigned", "chord_relative_degrees_assigned", "generation_ready"):
            observation = pattern.observe(self.ir, self.scope)
            observation["semantics"][field] = True
            with self.assertRaises(ValidationError):
                pattern.validate_observation(observation)

    def test_reconstructed_mutation_does_not_edit_observation(self):
        observation = pattern.observe(self.ir, self.scope)
        original = deepcopy(observation)
        pattern.reconstruct(observation)[0]["notation"] = {"changed": True}
        self.assertEqual(observation, original)


if __name__ == "__main__":
    unittest.main()
