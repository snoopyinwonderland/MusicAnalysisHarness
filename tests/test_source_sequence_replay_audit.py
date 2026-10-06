"""Synthetic/temp-only sequence replay guards; no local corpus dependency."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import source_sequence_replay_audit as replay
from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.dcml_import import parse_score_without_imported_harmony
from musicanote_harness.formal_ir import FormalIRAdapter, q


def pitched(step="C", duration="1", extras="", octave="4"):
    dur = "" if duration is None else f"<duration>{duration}</duration>"
    return (f"<note>{extras}<pitch><step>{step}</step><octave>{octave}</octave></pitch>"
            f"{dur}<voice>1</voice><type>quarter</type></note>")


def score_xml(content, divisions="1", number="1"):
    attributes = ("" if divisions is None else
                  f"<attributes><divisions>{divisions}</divisions>"
                  "<time><beats>4</beats><beat-type>4</beat-type></time></attributes>")
    return ('<score-partwise version="4.0"><part-list><score-part id="P1">'
            '<part-name>Piano</part-name></score-part></part-list><part id="P1">'
            f'<measure number="{number}">{attributes}{content}</measure>'
            '</part></score-partwise>')


def lane_row(fp, pitch="C", onset="0", duration="0", voice="1", chord=False,
             kind="note", part="P1", staff="1", measure=1, global_onset=None):
    return {"fingerprint": fp, "xpath": fp, "part": part, "measure_index": measure,
            "staff": staff, "voice": voice,
            "token": replay.token(onset, duration, None if kind == "rest" else (pitch, "0", 4),
                                  duration == "0" and kind == "note", "none"),
            "kind": kind, "chord_marker": chord,
            "global_onset": onset if global_onset is None else global_onset}


FIXTURE = score_xml(
    pitched() + pitched("E", extras="<chord/>") +
    '<note><grace slash="yes"/><pitch><step>D</step><octave>4</octave></pitch>'
    '<voice>1</voice><type>eighth</type></note>' +
    '<note><grace slash="no"/><pitch><step>D</step><octave>4</octave></pitch>'
    '<voice>1</voice><type>eighth</type></note>' +
    '<note><rest/><duration>1</duration><voice>1</voice><type>quarter</type></note>' +
    pitched("F", duration="2")
)


def make_parent(directory, xml=FIXTURE):
    source = Path(directory) / "fixture.musicxml"
    source.write_text(xml, encoding="utf-8")
    parsed, _, _ = parse_score_without_imported_harmony(source)
    parent = FormalIRAdapter().convert(CanonicalIRBuilder().build(parsed, source), source)
    return source, parent


class RawSequenceRowsTests(unittest.TestCase):
    def test_exact_triplet_cursor_backup_forward_and_chord(self):
        content = (pitched(duration="1") + pitched("E", "1", "<chord/>") +
                   '<note><rest/><duration>2</duration><voice>1</voice></note>' +
                   '<backup><duration>3</duration></backup>' +
                   '<forward><duration>1</duration></forward>' +
                   pitched("G", "1").replace("<voice>1</voice>", "<voice>2</voice>"))
        rows, measures = replay.raw_rows(score_xml(content, "3"))
        self.assertEqual([r["token"][0] for r in rows], ["0", "0", "1/3", "1/3"])
        self.assertEqual([r["token"][1] for r in rows], ["1/3", "1/3", "2/3", "1/3"])
        self.assertEqual([r["chord_marker"] for r in rows], [False, True, False, False])
        self.assertEqual(measures[0]["duration"], "1")
        self.assertEqual(rows[2]["kind"], "rest")
        self.assertEqual(rows[2]["xpath"], "/score-partwise/part[1]/measure[1]/note[3]")

    def test_absent_voice_is_unknown_not_defaulted(self):
        rows, _ = replay.raw_rows(score_xml(pitched().replace("<voice>1</voice>", "")))
        self.assertIsNone(rows[0]["voice"])
        self.assertEqual(rows[0]["staff"], "1")

    def test_blank_and_duplicate_fields_fail_closed(self):
        for name in ("voice", "staff", "duration"):
            for value in ("", " \n\t "):
                with self.subTest(field=name, value=value):
                    body = pitched()
                    if name == "staff": body = body.replace("</note>", f"<staff>{value}</staff></note>")
                    else: body = body.replace(f"<{name}>1</{name}>", f"<{name}>{value}</{name}>")
                    with self.assertRaisesRegex(ValueError, "empty_xml_field:" + name):
                        replay.raw_rows(score_xml(body))
            with self.subTest(duplicate=name):
                body = pitched().replace("</note>", f"<{name}>1</{name}></note>")
                if name == "staff": body = body.replace("</note>", "<staff>2</staff></note>")
                with self.assertRaisesRegex(ValueError, "duplicate_xml_field:" + name):
                    replay.raw_rows(score_xml(body))

    def test_blank_and_duplicate_divisions_fail_closed(self):
        for value in ("", " \n "):
            with self.assertRaisesRegex(ValueError, "empty_xml_field:divisions"):
                replay.raw_rows(score_xml(pitched(), value))
        with self.assertRaisesRegex(ValueError, "duplicate_xml_field:divisions"):
            replay.raw_rows(score_xml(pitched()).replace("</attributes>", "<divisions>1</divisions></attributes>"))

    def test_nonpositive_fractional_and_missing_divisions_rejected(self):
        for value in ("0", "-1", "1/2"):
            with self.subTest(divisions=value), self.assertRaisesRegex(ValueError, "invalid_xml_divisions"):
                replay.raw_rows(score_xml(pitched(), value))
        with self.assertRaisesRegex(ValueError, "missing_xml_duration_or_divisions"):
            replay.raw_rows(score_xml(pitched(), None))

    def test_missing_non_grace_duration_negative_duration_and_cursor_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing_xml_duration_or_divisions"):
            replay.raw_rows(score_xml(pitched(duration=None)))
        with self.assertRaisesRegex(ValueError, "negative_xml_duration"):
            replay.raw_rows(score_xml(pitched(duration="-1")))
        with self.assertRaisesRegex(ValueError, "negative_xml_cursor"):
            replay.raw_rows(score_xml('<backup><duration>1</duration></backup>' + pitched()))

    def test_grace_does_not_advance_cursor_or_realize_performance(self):
        rows, _ = replay.raw_rows(score_xml(pitched(duration="1") +
            pitched("D", None, '<grace steal-time-following="20"/>') + pitched("E", "1")))
        self.assertEqual([r["token"][0] for r in rows], ["0", "1", "1"])
        self.assertEqual(rows[1]["token"][1], "0")
        self.assertTrue(rows[1]["token"][3])

    def test_staff_lexeme_is_positive_integer_normalized(self):
        rows, _ = replay.raw_rows(score_xml(pitched(extras="<staff>+01</staff>")))
        self.assertEqual(rows[0]["staff"], "1")
        for value in ("0", "-1"):
            with self.assertRaisesRegex(ValueError, "nonpositive_xml_staff"):
                replay.raw_rows(score_xml(pitched(extras=f"<staff>{value}</staff>")))

    def test_orphan_chord_and_unsupported_rest_geometry_rejected(self):
        with self.assertRaisesRegex(ValueError, "orphan_chord_marker"):
            replay.raw_rows(score_xml(pitched(extras="<chord/>")))
        for extras in ("<grace/>", "<pitch><step>C</step><octave>4</octave></pitch>"):
            with self.subTest(extras=extras), self.assertRaisesRegex(ValueError, "unsupported_rest_geometry"):
                replay.raw_rows(score_xml(f"<note>{extras}<rest/><duration>1</duration><voice>1</voice></note>"))
        with self.assertRaisesRegex(ValueError, "unsupported_rest_tie"):
            replay.raw_rows(score_xml('<note><rest/><duration>1</duration><voice>1</voice><tie type="start"/></note>'))

    def test_pitched_chord_following_rest_is_not_a_pitched_anchor(self):
        content = '<note><rest/><duration>1</duration><voice>1</voice></note>' + pitched(extras="<chord/>")
        with self.assertRaisesRegex(ValueError, "orphan_chord_marker|unsupported_chord_anchor"):
            replay.raw_rows(score_xml(content))

    def test_unpitched_restless_event_and_invalid_tie_rejected(self):
        with self.assertRaisesRegex(ValueError, "unpitched_or_missing_pitch"):
            replay.raw_rows(score_xml('<note><unpitched/><duration>1</duration><voice>1</voice></note>'))
        for ties in ('<tie type="continue"/>', '<tie type="start"/><tie type="start"/>'):
            with self.subTest(ties=ties), self.assertRaisesRegex(ValueError, "invalid_xml_tie_roles"):
                replay.raw_rows(score_xml(pitched(extras=ties)))

    def test_namespace_part_ids_and_physical_measure_ordinals(self):
        xml = score_xml(pitched()).replace("<score-partwise ", '<score-partwise xmlns="http://www.musicxml.org/ns/musicxml" ')
        rows, _ = replay.raw_rows(xml)
        self.assertEqual(rows[0]["part"], "P1")
        self.assertEqual(rows[0]["measure_index"], 1)
        with self.assertRaisesRegex(ValueError, "duplicate_or_missing_xml_part_id"):
            replay.raw_rows(score_xml(pitched()).replace('<part id="P1">', '<part>'))
        duplicate = score_xml(pitched()).replace("</score-partwise>", '<part id="P1"><measure number="1"/></part></score-partwise>')
        with self.assertRaisesRegex(ValueError, "duplicate_or_missing_xml_part_id"):
            replay.raw_rows(duplicate)


class OrderedLaneReplayTests(unittest.TestCase):
    def test_repeated_identical_tokens_are_order_only_even_when_swapped(self):
        parsed = [lane_row("legacy_second"), lane_row("legacy_first")]
        original = [lane_row("xml_first"), lane_row("xml_second")]
        before = deepcopy((parsed, original))
        matched, rejected, lanes = replay.match_ordered_lanes(parsed, original)
        self.assertEqual([m["original"]["xpath"] for m in matched], ["xml_first", "xml_second"])
        self.assertTrue(all(m["occurrence_status"] == "reproducible_sequence_order_only" for m in matched))
        self.assertTrue(all(m["independent_occurrence_certified"] is False for m in matched))
        self.assertFalse(rejected)
        self.assertFalse(lanes[0]["contrapuntal_identity_certified"])
        self.assertEqual((parsed, original), before)

    def test_chord_marker_difference_cannot_hide_in_identical_pitch_tokens(self):
        p = [lane_row("a"), lane_row("b", chord=True)]
        r = [lane_row("x", chord=True), lane_row("y")]
        matched, rejected, _ = replay.match_ordered_lanes(p, r)
        self.assertFalse(matched)
        self.assertEqual([x["reason"] for x in rejected], ["full_lane_sequence_mismatch"] * 2)

    def test_chord_vs_standalone_repetition_is_not_order_only(self):
        p = [lane_row("a"), lane_row("b", chord=True)]
        r = [lane_row("x"), lane_row("y", chord=True)]
        matched, rejected, _ = replay.match_ordered_lanes(p, r)
        self.assertFalse(rejected)
        self.assertEqual([m["occurrence_status"] for m in matched], ["unique_token_in_source_lane"] * 2)

    def test_note_vs_rest_and_duration_spelling_tie_difference_reject_whole_lane(self):
        for mutate in (lambda r: r.update(kind="rest"),
                       lambda r: r.update(token=replay.token(0, 1, ("C", "0", 4), True, "none")),
                       lambda r: r.update(token=replay.token(0, 0, ("B", "1", 3), True, "none")),
                       lambda r: r.update(token=replay.token(0, 0, ("C", "0", 4), True, "start"))):
            r = lane_row("x"); mutate(r)
            matched, rejected, _ = replay.match_ordered_lanes([lane_row("a")], [r])
            self.assertFalse(matched)
            self.assertEqual(rejected[0]["reason"], "full_lane_sequence_mismatch")

    def test_global_mismatch_missing_event_and_reordered_notes_reject(self):
        matched, rejected, _ = replay.match_ordered_lanes([lane_row("a", global_onset="1")], [lane_row("x")])
        self.assertFalse(matched); self.assertEqual(rejected[0]["reason"], "global_timeline_mismatch")
        matched, rejected, _ = replay.match_ordered_lanes([lane_row("a")], [lane_row("x"), lane_row("y", "D")])
        self.assertFalse(matched); self.assertEqual(rejected[0]["reason"], "full_lane_sequence_mismatch")
        matched, rejected, _ = replay.match_ordered_lanes([lane_row("a"), lane_row("b", "D")], [lane_row("x", "D"), lane_row("y")])
        self.assertFalse(matched); self.assertEqual(len(rejected), 2)

    def test_unknown_container_voice_needs_exactly_one_raw_lane(self):
        matched, rejected, _ = replay.match_ordered_lanes([lane_row("a", voice=None)], [lane_row("x", voice="7")])
        self.assertEqual(len(matched), 1); self.assertFalse(rejected)
        matched, rejected, _ = replay.match_ordered_lanes([lane_row("a", voice=None)],
            [lane_row("x", voice="1"), lane_row("y", voice="2")])
        self.assertFalse(matched)
        self.assertEqual(rejected[0]["reason"], "ambiguous_or_missing_source_lane")

    def test_explicit_voice_conflict_never_uses_old_hints_or_xpath(self):
        p = lane_row("a", voice="9"); p.update(source_xpath="xml_hint", source_voice="1", legacy_voice="1")
        matched, rejected, _ = replay.match_ordered_lanes([p], [lane_row("xml_hint", voice="1")])
        self.assertFalse(matched)
        self.assertEqual(rejected[0]["reason"], "ambiguous_or_missing_source_lane")

    def test_raw_locator_collision_is_not_a_bijection(self):
        with self.assertRaisesRegex(ValueError, "source_locator_not_unique"):
            replay.match_ordered_lanes([lane_row("a"), lane_row("b", "D")],
                                      [lane_row("same"), lane_row("same", "D")])


class FullSourceReplayAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.source, self.parent = make_parent(self.tmp.name)

    def test_complete_note_rest_replay_is_nonmutating_and_not_certification(self):
        before = deepcopy(self.parent); source_bytes = self.source.read_bytes()
        result = replay.audit(self.parent, self.source)
        self.assertEqual(result["status"], "complete_replay")
        self.assertEqual(result["counts"]["matched_notes"], 5)
        self.assertEqual(result["counts"]["matched_rests"], 1)
        self.assertEqual(result["counts"]["source_events"], 6)
        self.assertEqual(result["counts"]["order_only_occurrences"], 2)
        self.assertTrue(result["fingerprint_reproduced"])
        for field in ("core_modified", "production_modified", "annotation_retargeted",
                      "source_labels_used", "accuracy_measured", "independent_occurrence_certified",
                      "contrapuntal_identity_certified", "performed_or_concert_time_verified"):
            self.assertIs(result[field], False)
        self.assertEqual(self.parent, before)
        self.assertEqual(self.source.read_bytes(), source_bytes)

    def test_stale_ref_locator_and_voice_hint_are_ignored_not_repaired(self):
        for ref in self.parent["source_references"]:
            ref.update(source_xpath="/wrong", source_voice="999", source_element_index=999,
                       source_staff=999, source_measure_number="wrong")
        for voice in self.parent["voices"]: voice["source_voice_number"] = "999"
        before = deepcopy(self.parent)
        result = replay.audit(self.parent, self.source)
        self.assertEqual(result["status"], "complete_replay")
        self.assertTrue(all(r["original"]["voice"] == "1" for r in result["observations"]))
        self.assertTrue(all(r["original"]["xpath"].startswith("/score-partwise/") for r in result["observations"]))
        self.assertEqual(self.parent, before)

    def test_unused_raw_lane_keeps_source_exclusions_and_partial_status(self):
        rows, measures = replay.raw_rows(self.source.read_bytes())
        extra = deepcopy(rows[0]); extra.update(voice="extra", staff="2", xpath="/extra")
        with patch.object(replay, "raw_rows", return_value=(rows + [extra], measures)):
            result = replay.audit(self.parent, self.source)
        self.assertEqual(result["status"], "partial_replay")
        self.assertEqual(result["unmatched_source_paths"], ["/extra"])
        self.assertEqual(result["counts"]["unmatched_source_events"], 1)
        self.assertEqual(result["counts"]["rejected_events"], 0)

    def test_frozen_local_onset_disagreement_is_recorded_not_rewritten(self):
        self.parent["note_events"][0]["onset_in_measure"] = q(99)
        before = deepcopy(self.parent)
        result = replay.audit(self.parent, self.source)
        self.assertEqual(result["status"], "complete_replay")
        self.assertEqual(result["counts"]["local_onset_mismatches"], 1)
        self.assertEqual(self.parent, before)

    def test_source_hash_mismatch_blocks_before_parsing(self):
        self.parent["source_files"][0]["sha256"] = "wrong"
        with patch.object(replay, "parse_score_without_imported_harmony") as parse:
            with self.assertRaisesRegex(ValueError, "source_hash_mismatch"):
                replay.audit(self.parent, self.source)
        parse.assert_not_called()

    def test_missing_fingerprint_or_note_cannot_be_silently_excluded(self):
        for mutate in (lambda p: p["source_references"][0].update(local_fingerprint="unknown"),
                       lambda p: p["note_events"].pop()):
            parent = deepcopy(self.parent); mutate(parent)
            result = replay.audit(parent, self.source)
            self.assertEqual(result["status"], "blocked")
            self.assertIn("parent_fingerprint_not_reproduced", result["blockers"])

    def test_duplicate_refs_shared_refs_events_and_parent_fingerprints_block(self):
        cases = []
        p = deepcopy(self.parent); p["source_references"].append(deepcopy(p["source_references"][0]))
        cases.append((p, "duplicate_source_ref_id"))
        p = deepcopy(self.parent); p["note_events"][1]["source_ref_id"] = p["note_events"][0]["source_ref_id"]
        cases.append((p, "duplicate_event_or_shared_source_ref"))
        p = deepcopy(self.parent); p["note_events"][1]["note_id"] = p["note_events"][0]["note_id"]
        cases.append((p, "duplicate_event_or_shared_source_ref"))
        p = deepcopy(self.parent); p["source_references"][1]["local_fingerprint"] = p["source_references"][0]["local_fingerprint"]
        cases.append((p, "duplicate_parent_fingerprint"))
        for parent, blocker in cases:
            with self.subTest(blocker=blocker):
                result = replay.audit(parent, self.source)
                self.assertEqual(result["status"], "blocked"); self.assertIn(blocker, result["blockers"])

    def test_event_id_swap_on_identical_graces_fails_recipe_guard(self):
        graces = [n for n in self.parent["note_events"] if n["grace"]["is_grace"]]
        graces[0]["note_id"], graces[1]["note_id"] = graces[1]["note_id"], graces[0]["note_id"]
        result = replay.audit(self.parent, self.source)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("event_identity_recipe_mismatch", result["blockers"])

    def test_protected_note_and_rest_material_changes_block(self):
        mutations = [(lambda p: p["note_events"][0].update(global_onset_quarter=q(1)), "parent_event_time_changed"),
                     (lambda p: p["rest_events"][0].update(notated_duration_quarter=q(2)), "parent_event_time_changed"),
                     (lambda p: p["note_events"][0]["written_pitch"].update(spelling="B#3"), "parent_event_pitch_changed"),
                     (lambda p: p["note_events"][0]["written_pitch"].update(midi_pitch=61), "parent_event_pitch_tie_or_grace_changed"),
                     (lambda p: p["note_events"][0].update(tie_role="start"), "parent_event_pitch_tie_or_grace_changed"),
                     (lambda p: p["note_events"][0]["grace"].update(is_grace=True), "parent_event_pitch_tie_or_grace_changed")]
        for mutate, blocker in mutations:
            with self.subTest(blocker=blocker):
                parent = deepcopy(self.parent); mutate(parent)
                result = replay.audit(parent, self.source)
                self.assertEqual(result["status"], "blocked"); self.assertIn(blocker, result["blockers"])

    def test_part_staff_and_source_file_lineage_conflicts_block(self):
        cases = [(lambda p: p["parts"][0].update(source_part_id="other"), "source_part_lineage_mismatch"),
                 (lambda p: p["staves"][0].update(part_id="other"), "staff_part_membership_mismatch"),
                 (lambda p: p["source_references"][0].update(source_file_id="other"), "source_file_identity_mismatch")]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                parent = deepcopy(self.parent); mutate(parent)
                result = replay.audit(parent, self.source)
                self.assertEqual(result["status"], "blocked"); self.assertIn(blocker, result["blockers"])

    def test_explicit_short_pickup_rest_and_special_measure_remain_source_timed(self):
        xml = score_xml(pitched(duration="3"))
        xml = xml.replace("</part></score-partwise>",
            '<measure number="X1" implicit="yes"><note><rest measure="yes"/>'
            '<duration>1</duration><voice>1</voice><type>quarter</type></note></measure></part></score-partwise>')
        source, parent = make_parent(self.tmp.name, xml)
        before = deepcopy(parent)
        result = replay.audit(parent, source)
        self.assertEqual(result["status"], "complete_replay")
        rest = next(r for r in result["observations"] if r["kind"] == "rest")
        self.assertEqual(rest["original"]["measure_label"], "X1")
        self.assertEqual(rest["original"]["measure_index"], 2)
        self.assertEqual(rest["original"]["global_onset"], "3")
        self.assertEqual(rest["original"]["token"][1], "1")
        self.assertEqual(parent, before)


if __name__ == "__main__":
    unittest.main()
