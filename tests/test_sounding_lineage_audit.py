"""Exact IR clock counterexamples; no XML authority or voice/role certification."""
from copy import deepcopy
import unittest

from musicanote_harness import sounding_lineage_audit as audit
from musicanote_harness.musical_pattern_observation import digest, q


def span(a, b):
    return {"start": q(a), "end": q(b)}


def fixture(intervals=((0, 1), (1, 1)), extent=(0, 2), *, roles=None, grace=False):
    notes = [{"note_id": "n" + str(i), "global_onset_quarter": q(a),
              "notated_duration_quarter": q(d), "tie_role": (roles or ["start", "stop"])[i],
              "grace": {"is_grace": grace}, "written_pitch": {"spelling": "literal unchanged"},
              "source_ref_id": "ref" + str(i)} for i, (a, d) in enumerate(intervals)]
    sound = {"sounding_event_id": "sound", "source_note_ids": [n["note_id"] for n in notes],
             "span": span(*extent), "sounding_duration": q(extent[1] - extent[0]),
             "attack_note_id": notes[0]["note_id"], "tie_chain_id": "tie" if len(notes) > 1 else None,
             "pitch": {"spelling": "declared pitch not certified"}}
    return {"ir_document_id": "ir_fixture", "score": {"score_id": "score_fixture", "duration_quarters": q(30)},
            "source_files": [{"source_file_id": "source_fixture", "sha256": "a" * 64}],
            "note_events": notes, "sounding_events": [sound]}


def reseal(record):
    body = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    record["record_sha256"] = digest(body);record["record_id"] = audit.PREFIX + record["record_sha256"][:24]
    return record


class SoundingLineageAuditTests(unittest.TestCase):
    def row(self, ir, **kwargs):
        return audit.audit_sounding_lineage(ir, sound_ids=["sound"], **kwargs)["sounding_audits"][0]

    def test_contiguous_chain_exact_snapshots_seal_and_input_immutability(self):
        ir = fixture();before = deepcopy(ir)
        record = audit.audit_sounding_lineage(ir, sound_ids=["sound"], context_span=span(0, 2))
        self.assertTrue(audit.validate_audit(record, ir=ir, sound_ids=["sound"], context_span=span(0, 2)))
        self.assertEqual(ir, before)
        row = record["sounding_audits"][0]
        self.assertTrue(record["source_clock_consistency_passed"])
        self.assertEqual(row["source_note_snapshots"], ir["note_events"])
        self.assertEqual(row["sounding_event_snapshot"], ir["sounding_events"][0])
        self.assertEqual(row["full_chain"]["source_duration_sum"], q(2))
        self.assertEqual(row["full_chain"]["gaps"], [])
        self.assertTrue(row["context_clipped"]["coverage_consistency_passed"])

    def test_normal_single_note_has_no_tie_assumption(self):
        row = self.row(fixture(((2, 3),), (2, 5), roles=["none"]))
        self.assertTrue(row["source_clock_consistency_passed"])
        self.assertFalse(row["attack_origin"]["continuation_origin"])

    def test_gap_outside_context_does_not_disappear_in_clipped_success(self):
        ir = fixture(((0, 3), (3, 3), (12, 3), (15, 3)), (0, 18), roles=["start", "continue", "continue", "stop"])
        row = self.row(ir, context_span=span(0, 4))
        self.assertEqual(row["full_chain"]["source_duration_sum"], q(12))
        self.assertEqual(row["full_chain"]["span_duration"], q(18))
        self.assertEqual(row["full_chain"]["gaps"], [span(6, 12)])
        self.assertFalse(row["source_clock_consistency_passed"])
        self.assertTrue(row["context_clipped"]["coverage_consistency_passed"])
        self.assertEqual(row["context_clipped"]["covered_duration"], q(4))

    def test_overlap_and_gap_detected_even_if_duration_sum_equals_span(self):
        row = self.row(fixture(((0, 3), (2, 2)), (0, 5)))
        self.assertEqual(row["full_chain"]["source_duration_sum"], q(5))
        self.assertEqual(row["full_chain"]["source_union_duration"], q(4))
        self.assertEqual(row["full_chain"]["gaps"], [span(4, 5)])
        self.assertEqual(row["full_chain"]["overlaps"][0]["span"], span(2, 3))
        self.assertFalse(row["source_clock_consistency_passed"])

    def test_exact_fraction_overlap_is_not_float_rounded(self):
        from fractions import Fraction as F
        row = self.row(fixture(((F(1, 3), F(1, 3)), (F(2, 3), F(1, 3))), (F(1, 3), 1)))
        self.assertTrue(row["source_clock_consistency_passed"])
        self.assertEqual(row["full_chain"]["source_duration_sum"], q(F(2, 3)))

    def test_outside_source_extent_and_onset_order_are_diagnostics(self):
        row = self.row(fixture(((0, 2), (2, 2)), (1, 3)))
        self.assertEqual([r["span"] for r in row["full_chain"]["outside_source_extents"]], [span(0, 1), span(3, 4)])
        self.assertIn("source_extent_outside_sound_span", row["diagnostics"])
        ir = fixture();ir["sounding_events"][0]["source_note_ids"].reverse()
        self.assertIn("source_onsets_not_in_stored_order", self.row(ir)["diagnostics"])

    def test_attack_source_origin_and_continuation_are_not_certified_voices(self):
        ir = fixture();ir["sounding_events"][0]["attack_note_id"] = "n1"
        row = self.row(ir)
        self.assertIn("attack_onset_differs_from_sound_start", row["diagnostics"])
        self.assertIn("attack_is_tie_continuation_or_stop_origin", row["diagnostics"])
        ir["sounding_events"][0]["attack_note_id"] = "missing"
        self.assertIn("missing_attack_note_reference", self.row(ir)["diagnostics"])
        self.assertIn("attack_note_not_source_member", self.row(ir)["diagnostics"])

    def test_missing_source_note_preserves_null_snapshot_and_unknown_coverage(self):
        ir = fixture();ir["note_events"].pop()
        row = self.row(ir)
        self.assertEqual(row["missing_source_note_refs"], ["n1"])
        self.assertIsNone(row["source_note_snapshots"][1])
        self.assertFalse(row["full_chain"]["timeline_complete"])
        self.assertFalse(row["source_clock_consistency_passed"])

    def test_declared_sounding_duration_does_not_override_source_clock(self):
        ir = fixture();ir["sounding_events"][0]["sounding_duration"] = q(9)
        self.assertIn("declared_sounding_duration_differs_from_span", self.row(ir)["diagnostics"])
        self.assertEqual(self.row(ir)["full_chain"]["declared_sounding_duration"], q(9))

    def test_grace_point_half_open_selection_and_unknown_performed_timing(self):
        ir = fixture(((2, 0),), (2, 2), roles=["none"], grace=True)
        record = audit.audit_sounding_lineage(ir, span=span(2, 3))
        self.assertEqual(record["summary"]["selected_sounds"], 1)
        row = record["sounding_audits"][0]
        self.assertEqual(row["timing_status"], "grace_point_performed_timing_unknown")
        self.assertTrue(row["context_clipped"]["point_in_context"])
        self.assertFalse(row["context_clipped"]["coverage_assessed"])
        self.assertFalse(row["source_clock_consistency_passed"])
        self.assertEqual(audit.audit_sounding_lineage(ir, span=span(1, 2))["summary"]["selected_sounds"], 0)

    def test_linked_outside_sound_is_audited_not_filtered_by_clip(self):
        row = self.row(fixture(), context_span=span(10, 11))
        self.assertTrue(row["source_clock_consistency_passed"])
        self.assertIsNone(row["context_clipped"]["span"])
        self.assertFalse(row["context_clipped"]["coverage_assessed"])

    def test_empty_and_unknown_id_selection_remain_in_denominator(self):
        ir = fixture();empty = audit.audit_sounding_lineage(ir, sound_ids=[])
        self.assertEqual(empty["status"], "empty_selection_not_assessed")
        self.assertEqual(empty["summary"]["selected_sounds"], 0)
        self.assertFalse(empty["source_clock_consistency_passed"])
        missing = audit.audit_sounding_lineage(ir, sound_ids=["missing", "sound"])
        self.assertEqual(missing["summary"]["selected_sounds"], 2)
        self.assertEqual(missing["summary"]["audited_sounds"], 1)
        self.assertEqual(missing["summary"]["missing_selected_sound_refs"], ["missing"])
        self.assertFalse(missing["source_clock_consistency_passed"])

    def test_duplicate_source_reference_is_not_silently_deduplicated(self):
        ir = fixture();ir["sounding_events"][0]["source_note_ids"].append("n0")
        row = self.row(ir)
        self.assertEqual(len(row["source_note_snapshots"]), 3)
        self.assertIn("duplicate_source_note_reference", row["diagnostics"])
        self.assertFalse(row["source_clock_consistency_passed"])

    def test_selector_context_guards_and_no_automatic_all_score_selection(self):
        ir = fixture()
        for kwargs in ({}, {"span": span(0, 2), "sound_ids": []}, {"sound_ids": ["sound", "sound"]},
                       {"sound_ids": "sound"}, {"sound_ids": [], "context_span": span(1, 1)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                audit.audit_sounding_lineage(ir, **kwargs)

    def test_stale_ir_resealed_omission_foreign_context_and_gate_forgery_rejected(self):
        ir = fixture();record = audit.audit_sounding_lineage(ir, sound_ids=["sound"], context_span=span(0, 2))
        changed = deepcopy(ir);changed["note_events"][0]["written_pitch"]["spelling"] = "different"
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            audit.validate_audit(record, ir=changed, sound_ids=["sound"], context_span=span(0, 2))
        for key in ("sounding_audits", "semantic_eligible"):
            forged = deepcopy(record)
            if key == "sounding_audits":forged[key] = []
            else:forged[key] = True
            reseal(forged)
            with self.assertRaisesRegex(ValueError, "stale_foreign"):
                audit.validate_audit(forged, ir=ir, sound_ids=["sound"], context_span=span(0, 2))
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            audit.validate_audit(record, ir=ir, sound_ids=["sound"], context_span=span(0, 1))

    def test_nonpositive_negative_time_and_all_certification_flags_false(self):
        ir = fixture(((0, 0),), (0, 0), roles=["none"])
        self.assertEqual(self.row(ir)["timing_status"], "unsupported_nonpositive")
        ir = fixture(((0, -1),), (0, 1), roles=["none"])
        self.assertIn("negative_notated_source_time", self.row(ir)["diagnostics"])
        record = audit.audit_sounding_lineage(fixture(), sound_ids=["sound"])
        for key in ("semantic_eligible", "generation_ready", "source_xml_certified", "voice_identity_certified",
                    "performed_timing_certified", "concert_pitch_certified", "input_modified"):
            self.assertIs(record[key], False)


if __name__ == "__main__":
    unittest.main()
