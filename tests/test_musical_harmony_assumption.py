from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jsonschema.exceptions import ValidationError

from musicanote_harness import musical_harmony_assumption as assumption
from musicanote_harness.musical_pattern_observation import digest, q
from musicanote_harness.musical_semantic_alignment import prepare_meter_index
from test_musical_pattern_observation import make_ir


def pitch(step, alter=0):
    return {"step": step, "alter": q(alter)}


def segment(identifier="hypothesis-1", start=0, end=4, label="C major", root=None, members=None):
    return {"segment_id": identifier, "span": {"start": q(start), "end": q(end)},
            "label": label, "root": pitch("C") if root is None else root,
            "members": [pitch("C"), pitch("E"), pitch("G")] if members is None else members,
            "status": "usable", "blockers": [], "source_locator": None}


def provenance():
    return {"kind": "caller_hypothesis", "engine_version": "caller-test-1",
            "source_document_sha256": None, "source_path": None,
            "pitch_basis": "written_IR_not_concert_certified", "status": "hypothesis_not_gold"}


def reseal(record):
    payload = {key: value for key, value in record.items() if key not in ("record_id", "record_sha256")}
    record["record_sha256"] = digest(payload)
    record["record_id"] = "mha_" + record["record_sha256"][:24]
    return record


class MusicalHarmonyAssumptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ir = make_ir(self.root)

    def source(self, text="Time Signature: 4/4\nm1 C: I b3 V7\nm2 I\nm3 V\n"):
        path = self.root / "analysis.rntxt"
        path.write_text(text, encoding="utf-8")
        return path, prepare_meter_index(path)

    def test_competing_tracks_are_distinct_immutable_hypotheses(self):
        original = deepcopy(self.ir)
        segments, context = [segment()], provenance()
        first = assumption.build_track(self.ir, segments, context)
        competing = segment(label="A minor", root=pitch("A"), members=[pitch("A"), pitch("C"), pitch("E")])
        second = assumption.build_track(self.ir, [competing], context)
        self.assertNotEqual(first["record_id"], second["record_id"])
        self.assertEqual(first["binding"], second["binding"])
        self.assertEqual(first, assumption.build_track(self.ir, segments, context))
        segments[0]["members"][0]["step"] = "D"
        context["engine_version"] = "changed"
        self.assertEqual(first["segments"][0]["members"][0], pitch("C"))
        self.assertEqual(first["provenance"]["engine_version"], "caller-test-1")
        self.assertEqual(self.ir, original)
        assumption.validate_track(first, self.ir)
        assumption.validate_track(second, self.ir)

    def test_holes_and_blocked_segments_are_explicit(self):
        blocked = segment("blocked", 6, 8)
        blocked.update(status="blocked", blockers=["caller_uncertain"], root=None, members=[])
        track = assumption.build_track(self.ir, [segment(start=Fraction(1, 2), end=2), blocked,
                                                segment("late", 10, 12)], provenance())
        self.assertEqual(track["coverage_holes"], [{"start": q(0), "end": q(Fraction(1, 2))},
                                                   {"start": q(2), "end": q(10)}])
        self.assertEqual(assumption.build_track(self.ir, [], provenance())["coverage_holes"],
                         [{"start": q(0), "end": q(12)}])

    def test_schema_policy_cannot_promote_or_certify(self):
        track = assumption.build_track(self.ir, [segment()], provenance())
        self.assertEqual(track["schema_name"], "musicanote-musical-harmony-assumption")
        self.assertEqual(track["schema_version"], "0.1.0")
        self.assertEqual(track["producer_version"], "musical-harmony-assumption-0.1.0")
        self.assertRegex(track["record_id"], r"^mha_[0-9a-f]{24}$")
        for field, value in (("training_eligible", True), ("research_only", False),
                             ("gold_status", "gold"), ("generation_ready", True)):
            bad = deepcopy(track)
            bad["use_policy"][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                assumption.validate_track(reseal(bad))
        bad = deepcopy(track)
        bad["provenance"]["pitch_basis"] = "concert"
        with self.assertRaises(ValidationError):
            assumption.validate_track(reseal(bad))

    def test_duplicate_overlap_outside_and_bad_members_rejected(self):
        cases = [([segment(), segment()], "duplicate"),
                 ([segment(), segment("other", 3, 5)], "overlapping"),
                 ([segment(end=13)], "outside_score"),
                 ([segment(start=-1)], "invalid_positive"),
                 ([segment(members=[pitch("C"), {"step": "C", "alter": {"numerator": 0, "denominator": 2}}])], "duplicate_harmony_member")]
        for segments, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                assumption.build_track(self.ir, segments, provenance())
        for status, blockers in (("blocked", []), ("usable", ["not_resolved"])):
            bad = segment()
            bad.update(status=status, blockers=blockers)
            with self.assertRaises(ValueError):
                assumption.build_track(self.ir, [bad], provenance())

    def test_seal_stale_ir_and_bad_references_rejected(self):
        track = assumption.build_track(self.ir, [segment()], provenance())
        tampered = deepcopy(track)
        tampered["segments"][0]["label"] = "changed"
        with self.assertRaisesRegex(ValueError, "seal_mismatch"):
            assumption.validate_track(tampered)
        foreign = deepcopy(self.ir)
        foreign["score"]["title"] = "changed title"
        with self.assertRaisesRegex(ValueError, "stale_or_foreign"):
            assumption.validate_track(track, foreign)
        bad_ir = deepcopy(self.ir)
        bad_ir["note_events"][0]["source_ref_id"] = "missing-source"
        with self.assertRaisesRegex(ValueError, "dangling_event_reference"):
            assumption.build_track(bad_ir, [segment()], provenance())
        source_segment = segment()
        source_segment["source_locator"] = {"printed_measure_number": "99", "line_number": 1, "raw_line": "m99 C: I"}
        context = provenance()
        context["kind"] = "source_annotation"
        context.update(source_document_sha256="a" * 64, source_path="source.rntxt")
        with self.assertRaisesRegex(ValueError, "source_locator_measure_missing"):
            assumption.build_track(self.ir, [source_segment], context)

    def test_exact_RomanText_spans_all_spellings_and_provenance(self):
        path, index = self.source()
        original = deepcopy(self.ir)
        track = assumption.import_romantext(path, self.ir, index)
        self.assertEqual(len(track["segments"]), 4)
        first, dominant = track["segments"][:2]
        self.assertEqual(first["span"], {"start": q(0), "end": q(2)})
        self.assertEqual(dominant["span"], {"start": q(2), "end": q(4)})
        self.assertEqual(first["members"], [pitch("C"), pitch("E"), pitch("G")])
        self.assertEqual(dominant["members"], [pitch("G"), pitch("B"), pitch("D"), pitch("F")])
        self.assertEqual(dominant["root"], pitch("G"))
        self.assertEqual(first["source_locator"], {"printed_measure_number": "1", "line_number": 2,
                                                  "raw_line": "m1 C: I b3 V7"})
        self.assertEqual(track["provenance"]["source_document_sha256"], index["source_sha256"])
        self.assertEqual(track["provenance"]["pitch_basis"], "written_IR_not_concert_certified")
        self.assertEqual(track["coverage_holes"], [])
        self.assertEqual(track["import_diagnostics"], [])
        self.assertEqual(self.ir, original)
        assumption.validate_track(track, self.ir)
        path, index = self.source("Time Signature: 4/4\nm1 C: I b1.5 bII\nm2 I\nm3 V\n")
        fractional = assumption.import_romantext(path, self.ir, index)
        self.assertEqual(fractional["segments"][0]["span"]["end"], q(Fraction(1, 2)))
        self.assertEqual(fractional["segments"][1]["members"], [pitch("D", -1), pitch("F"), pitch("A", -1)])

    def test_source_meter_mismatch_is_held_not_defaulted(self):
        path, index = self.source("Time Signature: 3/4\nm1 C: I\nm2 V\nm3 I\n")
        track = assumption.import_romantext(path, self.ir, index)
        self.assertEqual(track["segments"], [])
        self.assertTrue(all(row["blockers"] == ["source_score_meter_mismatch"]
                            for row in track["import_diagnostics"]))
        path, index = self.source("m1 C: I\nm2 V\nm3 I\n")
        self.assertEqual(index["status"], "missing_explicit_source_meter")
        track = assumption.import_romantext(path, self.ir, index)
        self.assertEqual(track["segments"], [])
        index["status"] = "parsed_RomanText_meter"
        self.assertEqual(assumption.import_romantext(path, self.ir, index)["segments"], [])
        for beat in ("1.33", "1.66", "1.333"):
            path, index = self.source(f"Time Signature: 4/4\nm1 C: I b{beat} V\nm2 I\nm3 V\n")
            track = assumption.import_romantext(path, self.ir, index)
            self.assertFalse(any(row["span"]["start"] == q(0) for row in track["segments"]))
            self.assertTrue(any(row["blockers"] == ["rounded_or_nonbinary_beat_requires_review"]
                                for row in track["import_diagnostics"]))

    def test_initial_key_required_and_source_annotation_requires_document(self):
        for header in ("", "Key Signature: 1\n", "Key: G\n"):
            path, index = self.source(f"Time Signature: 4/4\n{header}m1 I\nm2 G: V\nm3 I\n")
            track = assumption.import_romantext(path, self.ir, index)
            self.assertEqual(track["segments"], [])
            self.assertTrue(all(row["blockers"] == ["missing_initial_explicit_source_key"]
                                for row in track["import_diagnostics"]))
        path, index = self.source("Time Signature: 4/4\nm1 F#: i\nm2 V\nm3 i\n")
        track = assumption.import_romantext(path, self.ir, index)
        self.assertEqual(track["segments"][0]["root"], pitch("F", 1))
        self.assertEqual(track["segments"][0]["members"], [pitch("F", 1), pitch("A"), pitch("C", 1)])
        self.assertEqual(track["import_diagnostics"], [])
        for field in ("source_document_sha256", "source_path"):
            bad = deepcopy(track)
            bad["provenance"][field] = None
            with self.subTest(field=field), self.assertRaises(ValidationError):
                assumption.validate_track(reseal(bad))
        for field in ("line_number", "raw_line"):
            bad = deepcopy(track)
            bad["segments"][0]["source_locator"][field] = None
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "requires_explicit_locator"):
                assumption.validate_track(reseal(bad))

    def test_pickup_irregular_padding_and_duplicate_measures_are_held(self):
        path, index = self.source()
        for kind in ("pickup", "irregular", "source_padding", "duplicate_IR_label", "duplicate_source_meter"):
            ir, source_index = deepcopy(self.ir), deepcopy(index)
            if kind == "pickup":
                ir["measures"][0]["pickup"] = True
            elif kind == "irregular":
                ir["measures"][0]["actual_duration_quarter"] = q(3)
            elif kind == "source_padding":
                source_index["measures"][0]["padding_left_quarter"] = q(1)
            elif kind == "duplicate_IR_label":
                ir["measures"][1]["printed_measure_number"] = "1"
            else:
                source_index["measures"].append(deepcopy(source_index["measures"][0]))
            with self.subTest(kind=kind):
                track = assumption.import_romantext(path, ir, source_index)
                self.assertFalse(any(row["source_locator"]["printed_measure_number"] == "1"
                                     for row in track["segments"] if row["source_locator"]))
                self.assertTrue(any(row["printed_measure_number"] == "1" for row in track["import_diagnostics"]))

    def test_copied_source_lines_have_no_full_provenance(self):
        path, index = self.source("Time Signature: 4/4\nm1 C: I\nm2 = m1\nm3 V7\n")
        track = assumption.import_romantext(path, self.ir, index)
        copied = next(row for row in track["segments"] if row["span"]["start"] == q(4))
        self.assertEqual(copied["status"], "blocked")
        self.assertIsNone(copied["source_locator"])
        self.assertEqual(copied["members"], [pitch("C"), pitch("E"), pitch("G")])
        self.assertEqual(track["coverage_holes"], [{"start": q(4), "end": q(8)}])
        path, index = self.source("Time Signature: 4/4\nm1 C: I\nm2 V\nm3-4 = m1-2\n")
        track = assumption.import_romantext(path, self.ir, index)
        generated = next(row for row in track["segments"] if row["span"]["start"] == q(8))
        self.assertEqual(generated["status"], "blocked")
        self.assertIsNone(generated["source_locator"])

    def test_stale_or_forged_source_meter_index_rejected_or_held(self):
        path, index = self.source()
        stale = deepcopy(index)
        stale["source_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "stale_meter_index_source"):
            assumption.import_romantext(path, self.ir, stale)
        forged = deepcopy(index)
        forged["measures"][0]["numerator"] = 3
        track = assumption.import_romantext(path, self.ir, forged)
        self.assertTrue(any(row["blockers"] == ["meter_index_parsed_source_mismatch"]
                            for row in track["import_diagnostics"]))

    def test_pedal_and_prose_are_never_chord_labels_or_answers(self):
        path, index = self.source("Time Signature: 4/4\nPedal: C m1 b1 m2 b1\nNote: tonic accompaniment winner\nm1 C: V7\nm2 I\nm3 V\n")
        track = assumption.import_romantext(path, self.ir, index)
        self.assertEqual([row["label"] for row in track["segments"]], ["V7", "I", "V"])
        self.assertEqual(track["segments"][0]["root"], pitch("G"))
        self.assertNotIn("winner", str(track))

    def test_resealed_bad_locator_and_holes_fail_ir_validation(self):
        path, index = self.source()
        track = assumption.import_romantext(path, self.ir, index)
        bad = deepcopy(track)
        bad["segments"][0]["source_locator"]["printed_measure_number"] = "2"
        with self.assertRaisesRegex(ValueError, "source_locator_outside"):
            assumption.validate_track(reseal(bad), self.ir)
        bad = deepcopy(track)
        bad["segments"].pop()
        with self.assertRaisesRegex(ValueError, "coverage_holes_mismatch"):
            assumption.validate_track(reseal(bad), self.ir)


if __name__ == "__main__":
    unittest.main()
