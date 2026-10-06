"""Explicit tonal assumptions, unknowns and adversarial ordinary relations."""
from copy import deepcopy
from fractions import Fraction
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import factor_functional_overlay as overlay
from musicanote_harness import factor_musical_view as common
from musicanote_harness.applied_chords import hypothesis
from musicanote_harness.seventh_context import chord
from test_factor_musical_view import make_view, member, span, provenance
from test_musical_role_evidence import make_ir, event


def key_segment(name="key-c", start=0, end=4, tonic="C", mode="major", form="major", alter=0):
    return {"segment_id": name, "span": span(start, end),
            "tonic": None if tonic is None else member(tonic, alter), "mode": mode, "scale_form": form}


def harmony(name, start, end, root, quality, *, blockers=()):
    value = chord([root, 0], quality)
    return {"segment_id": name, "span": span(start, end), "root": member(root),
            "members": [member(*p) for p in value["members"]],
            "status": "blocked" if blockers else "usable", "blockers": list(blockers)}


def reseal(record, prefix):
    return common.seal({k: deepcopy(v) for k, v in record.items()
                       if k not in ("record_id", "record_sha256")}, prefix)


class FunctionalOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ir = make_ir(self.temp.name, [[event("G4", 0, 2), event("C4", 2, 2)]])
        self.view = make_view(self.ir, span())

    def compile(self, segments=None, keys=None, **kwargs):
        path = common.make_path(self.view, segments or [harmony("v", 0, 2, "G", "Mm7"),
                                                     harmony("i", 2, 4, "C", "M")], provenance())
        key = overlay.make_key_track(self.view, keys or [key_segment()], provenance())
        return path, key, overlay.compile_functions(self.view, path, key, **kwargs)

    def row(self, record, family="V7", quality="M", source="v"):
        return next(r for r in record["rows"] if (r["source_segment_ref"], r["family"], r["target_quality"])
                    == (source, family, quality))

    def test_primary_dominant_shape_exact_next_target_and_critical_spelling(self):
        before = deepcopy(self.view)
        path, key, record = self.compile()
        row = self.row(record)
        self.assertEqual(row["function_kind"], "primary")
        self.assertEqual(row["status"], "conditional_function_shape")
        self.assertTrue(row["shape_compatible"])
        self.assertTrue(row["target_shape_compatible"])
        self.assertEqual(row["leading_tone"], member("B"))
        self.assertEqual(row["seventh"], member("F"))
        self.assertEqual(row["target_segment_ref"], "i")
        self.assertEqual(row["target_span"], span(2, 4))
        self.assertEqual(row["target_basis"], "next_path_segment")
        self.assertEqual(row["prerequisites"]["actual_motion"], "unassessed")
        self.assertTrue(overlay.validate_functions(self.view, path, key, record))
        self.assertEqual(self.view, before)
        self.assertTrue(all(v is False for v in record["flags"].values()))
        self.assertEqual(record["total_candidates"], 20)

    def test_home_tonic_can_be_applied_dominant_of_four_not_function_truth(self):
        _, _, record = self.compile([harmony("v", 0, 2, "C", "M"), harmony("iv", 2, 4, "F", "M")])
        row = self.row(record, "V")
        self.assertEqual(row["function_kind"], "applied")
        self.assertEqual(row["target_root"], member("F"))
        self.assertEqual(row["leading_tone"], member("E"))
        self.assertEqual(row["prerequisites"]["chromatic_source_members"], [])
        self.assertEqual(row["status"], "conditional_function_shape")
        self.assertFalse(record["flags"]["function_confirmed"])

    def test_parallel_tonic_and_minor_primary_are_competing_assumptions(self):
        segments = [harmony("v", 0, 2, "G", "M"), harmony("i", 2, 4, "C", "m")]
        _, _, major = self.compile(segments)
        _, _, minor = self.compile(segments, [key_segment(mode="minor", form="harmonic_minor")])
        self.assertEqual(self.row(major, "V", "m")["function_kind"], "parallel")
        self.assertEqual(self.row(minor, "V", "m")["function_kind"], "primary")
        self.assertTrue(self.row(minor, "V", "m")["shape_compatible"])
        self.assertNotEqual(major["record_id"], minor["record_id"])

    def test_unknown_key_preserves_literal_source_and_next_shape(self):
        _, _, record = self.compile(keys=[key_segment(tonic=None, mode="unknown", form="unknown")])
        row = self.row(record)
        self.assertTrue(row["shape_compatible"])
        self.assertTrue(row["target_shape_compatible"])
        self.assertEqual(row["function_kind"], "unassessed")
        self.assertEqual(row["status"], "conditional_function_shape")
        self.assertFalse(row["prerequisites"]["key_projection_assessed"])
        self.assertIsNone(row["prerequisites"]["target_coordinate"])

    def test_no_next_target_is_held_not_fabricated_observation(self):
        _, _, record = self.compile([harmony("v", 0, 4, "G", "M")])
        row = self.row(record, "V")
        self.assertEqual(row["target_root"], member("C"))
        self.assertEqual(row["target_basis"], "derived_target_without_next")
        self.assertIsNone(row["target_segment_ref"])
        self.assertIsNone(row["target_span"])
        self.assertIn("next_target_segment_not_observed", row["blockers"])
        self.assertEqual(row["status"], "withheld")

    def test_actual_mismatching_target_is_not_replaced_by_expected_target(self):
        _, _, record = self.compile([harmony("v", 0, 2, "G", "Mm7"), harmony("other", 2, 4, "F", "M")])
        row = self.row(record)
        self.assertEqual(row["target_root"], member("C"))
        self.assertEqual(row["prerequisites"]["actual_target"]["root"], member("F"))
        self.assertEqual(row["target_segment_ref"], "other")
        self.assertFalse(row["target_shape_compatible"])
        self.assertIn("next_target_triad_core_shape_mismatch", row["blockers"])

    def test_all_ordinary_families_preserve_leading_tone_and_seventh(self):
        for family in overlay.FAMILIES:
            expected = hypothesis(["C", 0], "M", family)
            source = {"segment_id": "v", "span": span(0, 2), "root": member(*expected["chord"]["root"]),
                      "members": [member(*p) for p in expected["chord"]["members"]], "status": "usable", "blockers": []}
            _, _, record = self.compile([source, harmony("i", 2, 4, "C", "M")])
            with self.subTest(family=family):
                row = self.row(record, family)
                self.assertEqual(row["status"], "conditional_function_shape")
                self.assertEqual(row["leading_tone"], member("B"))
                self.assertEqual(row["seventh"], None if len(expected["chord"]["members"]) == 3
                                 else member(*expected["chord"]["members"][3]))

    def test_accidental_and_minor_profile_are_not_secondary_proof_or_prohibition(self):
        expected = hypothesis(["C", 0], "m", "vii_half7")
        source = {"segment_id": "v", "span": span(0, 2), "root": member(*expected["chord"]["root"]),
                  "members": [member(*p) for p in expected["chord"]["members"]], "status": "usable", "blockers": []}
        _, _, record = self.compile([source, harmony("i", 2, 4, "C", "m")],
                                   [key_segment(mode="minor", form="natural_minor")])
        row = self.row(record, "vii_half7", "m")
        self.assertEqual(row["function_kind"], "primary")
        self.assertEqual(row["prerequisites"]["textbook_profile"], "outside_basic_target_profile")
        self.assertFalse(row["prerequisites"]["profile_is_universal_prohibition"])
        self.assertTrue(row["prerequisites"]["chromatic_member_is_not_function_proof"])

    def test_explicit_minor_scale_forms_do_not_infer_direction_or_key(self):
        for form in ("natural_minor", "harmonic_minor", "melodic_minor_ascending", "unknown"):
            _, _, record = self.compile(keys=[key_segment(mode="minor", form=form)])
            row = self.row(record)
            with self.subTest(form=form):
                self.assertEqual(row["scale_form"], form)
                self.assertFalse(record["flags"]["key_inferred"])
                if form == "unknown":
                    self.assertIsNone(row["prerequisites"]["target_coordinate"])
                elif form == "melodic_minor_ascending":
                    self.assertIn("not_direction_rule", row["prerequisites"]["scale_form_reference_policy"])

    def test_key_span_change_does_not_duplicate_or_delete_source_shape(self):
        keys = [key_segment("left", 0, 1), key_segment("right", 1, 4, "G")]
        _, _, record = self.compile(keys=keys)
        rows = [r for r in record["rows"] if r["source_segment_ref"] == "v" and r["family"] == "V7"
                and r["target_quality"] == "M"]
        self.assertEqual(record["total_candidates"], 30)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["shape_compatible"] for r in rows))
        self.assertTrue(all(r["function_kind"] == "unassessed" for r in rows))
        self.assertEqual({r["key_segment_ref"] for r in rows}, {"left", "right"})

    def test_microtones_not_truncated_or_sent_to_old_helper(self):
        sources = [harmony("v", 0, 2, "G", "M"), harmony("i", 2, 4, "C", "M")]
        sources[0]["root"]["alter"] = common.q(Fraction(1, 2))
        sources[0]["members"][0]["alter"] = common.q(Fraction(1, 2))
        actual = overlay.hypothesis
        def guarded(root, *args, **kwargs):
            self.assertIs(type(root[1]), int)
            return actual(root, *args, **kwargs)
        with patch.object(overlay, "hypothesis", side_effect=guarded):
            _, _, record = self.compile(sources)
        row = self.row(record, "V")
        self.assertEqual(row["source_root"]["alter"], common.q(Fraction(1, 2)))
        self.assertIsNone(row["shape_compatible"])
        self.assertIsNone(row["target_root"])
        self.assertIn("microtonal_source_shape_not_supported", row["blockers"])
        _, _, micro_key = self.compile(keys=[key_segment(alter=Fraction(1, 2))])
        self.assertTrue(self.row(micro_key)["shape_compatible"])
        self.assertEqual(self.row(micro_key)["function_kind"], "unassessed")
        self.assertIn("microtonal_key_projection_not_supported", self.row(micro_key)["blockers"])

    def test_blocked_source_target_and_missing_root_retained(self):
        segments = [harmony("v", 0, 2, "G", "Mm7", blockers=["meter_unknown"]),
                    harmony("i", 2, 4, "C", "M", blockers=["silence"])]
        _, _, record = self.compile(segments)
        row = self.row(record)
        self.assertTrue(row["shape_compatible"])
        self.assertTrue(row["target_shape_compatible"])
        self.assertIn("source_harmony:meter_unknown", row["blockers"])
        self.assertIn("target_harmony:silence", row["blockers"])
        segments[0]["root"] = None
        _, _, unknown = self.compile(segments)
        self.assertIsNone(self.row(unknown)["source_root"])
        self.assertIn("source_root_not_supplied", self.row(unknown)["blockers"])
        self.assertEqual(len(record["rows"]), len(unknown["rows"]))

    def test_target_extra_members_are_preserved_not_silently_removed(self):
        segments = [harmony("v", 0, 2, "G", "Mm7"), harmony("i", 2, 4, "C", "MM7")]
        _, _, record = self.compile(segments)
        row = self.row(record)
        self.assertTrue(row["target_shape_compatible"])
        self.assertEqual(row["prerequisites"]["target_additional_members"], [member("B")])
        self.assertEqual(row["prerequisites"]["actual_target"]["members"], segments[1]["members"])
        self.assertTrue(row["prerequisites"]["target_quality_is_triad_core_assumption"])
        self.assertEqual(row["prerequisites"]["actual_target_identity"], "unassessed")

    def test_guarded_view_never_becomes_actual_resolution_or_source_certification(self):
        ir = deepcopy(self.ir)
        ir["sounding_events"][0]["pitch"] = deepcopy(ir["note_events"][1]["written_pitch"])
        guarded_view = make_view(ir, span())
        self.assertTrue(any(s["source_pitch_consistency_passed"] is False for s in guarded_view["sounds"]))
        path = common.make_path(guarded_view, [harmony("v", 0, 2, "G", "Mm7"),
                                             harmony("i", 2, 4, "C", "M")], provenance())
        key = overlay.make_key_track(guarded_view, [key_segment()], provenance())
        row = self.row(overlay.compile_functions(guarded_view, path, key))
        self.assertEqual(row["prerequisites"]["actual_motion"], "unassessed")
        self.assertEqual(row["prerequisites"]["source_clock_and_written_pitch"],
                         "required_per_involved_sound_by_resolution_consumer")
        self.assertFalse(any(guarded_view["use_policy"].values()))

    def test_budget_preflight_withholds_entire_inventory_before_hypothesis_calls(self):
        with patch.object(overlay, "hypothesis", side_effect=AssertionError("budget first")):
            path, key, record = self.compile(max_candidates=19)
        self.assertEqual(record["total_candidates"], 20)
        self.assertEqual(record["rows"], [])
        self.assertEqual(record["status"], "candidate_budget_abstention")
        self.assertTrue(overlay.validate_functions(self.view, path, key, record, max_candidates=19))
        for budget in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                overlay.compile_functions(self.view, path, key, max_candidates=budget)

    def test_key_partition_provenance_and_scale_mode_guards(self):
        invalid = [[key_segment(end=3)], [key_segment(end=2), key_segment(start=1)],
                   [key_segment("same", end=2), key_segment("same", start=2)],
                   [key_segment(mode="major", form="harmonic_minor")],
                   [key_segment(mode="minor", form="melodic_minor")],
                   [key_segment(tonic=None)], [key_segment(mode="dorian")]]
        for segments in invalid:
            with self.subTest(segments=segments), self.assertRaises(ValueError):
                overlay.make_key_track(self.view, segments, provenance())
        for field, value in (("kind", "source_annotation"), ("source_path", "some.rntxt"),
                             ("source_document_sha256", "a" * 64), ("status", "gold")):
            changed = provenance()
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                overlay.make_key_track(self.view, [key_segment()], changed)
        extra = key_segment()
        extra["key_signature"] = "C"
        with self.assertRaises(ValueError):
            overlay.make_key_track(self.view, [extra], provenance())

    def test_resealed_key_foreign_view_and_promoting_policy_rejected(self):
        path, key, _ = self.compile()
        for field, value in (("view_ref", common.ref(path)), ("binding", {}),
                             ("flags", {**key["flags"], "key_inferred": True}),
                             ("use_policy", {**common.POLICY, "generation_ready": True})):
            changed = deepcopy(key)
            changed[field] = value
            changed = reseal(changed, overlay.KEY_PREFIX)
            with self.subTest(field=field), self.assertRaises(ValueError):
                overlay.validate_key_track(self.view, changed)
        changed = deepcopy(key)
        changed["flags"]["selected"] = 0
        with self.assertRaises(ValueError):
            overlay.validate_key_track(self.view, reseal(changed, overlay.KEY_PREFIX))

    def test_resealed_key_partition_and_unknown_fields_still_rejected(self):
        _, key, _ = self.compile()
        changed = deepcopy(key)
        changed["segments"][0]["span"]["end"] = common.q(3)
        with self.assertRaises(ValueError):
            overlay.validate_key_track(self.view, reseal(changed, overlay.KEY_PREFIX))
        changed = deepcopy(key)
        changed["source_annotation"] = "V7"
        with self.assertRaises(ValueError):
            overlay.validate_key_track(self.view, reseal(changed, overlay.KEY_PREFIX))

    def test_function_tamper_reseal_foreign_inputs_and_json_roundtrip(self):
        path, key, record = self.compile()
        self.assertTrue(overlay.validate_functions(self.view, path, key, json.loads(json.dumps(record))))
        for field, value in (("target_root", member("F", Fraction(1, 2))), ("status", "truth"),
                             ("blockers", []), ("function_kind", "confirmed")):
            changed = deepcopy(record)
            row = next(r for r in changed["rows"] if r["blockers"]) if field == "blockers" else changed["rows"][0]
            row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                overlay.validate_functions(self.view, path, key, reseal(changed, overlay.PREFIX))
        _, other_key, _ = self.compile(keys=[key_segment(tonic="G")])
        with self.assertRaises(ValueError):
            overlay.validate_functions(self.view, path, other_key, record)
        other_path = common.make_path(self.view, [harmony("all", 0, 4, "C", "M")], provenance())
        with self.assertRaises(ValueError):
            overlay.validate_functions(self.view, other_path, key, record)
        changed = deepcopy(record)
        changed["flags"]["function_confirmed"] = True
        with self.assertRaises(ValueError):
            overlay.validate_functions(self.view, path, key, reseal(changed, overlay.PREFIX))


if __name__ == "__main__":
    unittest.main()
