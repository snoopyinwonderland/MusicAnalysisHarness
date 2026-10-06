from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jsonschema.exceptions import ValidationError
from music21 import chord, converter, meter, note, stream, tie

from musicanote_harness.canonical import CanonicalIRBuilder
from musicanote_harness.formal_ir import FormalIRAdapter
from musicanote_harness import musical_harmony_assumption as assumptions
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness import musical_role_evidence as roles


def event(pitch, onset, duration, *, tie_role=None, grace=False):
    return {"pitch": pitch, "onset": Fraction(onset), "duration": Fraction(duration),
            "tie_role": tie_role, "grace": grace}


def make_ir(directory, lanes):
    """Independent MusicXML round-trip, with no production corpus dependency.

    Separate Voice objects with the same source voice number make MusicXML
    backups preserve overlapping durations. The parser then restores one raw
    lane, rather than silently serializing those notes or assigning new roles.
    """
    score = stream.Score()
    for part_index, events in enumerate(lanes):
        part = stream.Part(id=f"P{part_index}")
        measure = stream.Measure(number=1)
        measure.append(meter.TimeSignature("4/4"))
        for spec in events:
            if spec["pitch"] is None:
                item = note.Rest(quarterLength=spec["duration"])
            elif isinstance(spec["pitch"], (list, tuple)):
                item = chord.Chord(spec["pitch"], quarterLength=spec["duration"])
            else:
                item = note.Note(spec["pitch"], quarterLength=spec["duration"])
            if spec["grace"]:
                item = item.getGrace()
            if spec["tie_role"] is not None:
                item.tie = tie.Tie(spec["tie_role"])
            voice = stream.Voice(id="1")
            voice.insert(spec["onset"], item)
            measure.insert(0, voice)
        part.append(measure)
        score.append(part)
    path = Path(directory) / "score.musicxml"
    score.write("musicxml", fp=path, makeNotation=False)
    parsed = converter.parse(path)
    ir = FormalIRAdapter().convert(CanonicalIRBuilder().build(parsed, path), path)
    pattern.validate_core(ir)
    return ir


def scope_for(ir, start=0, end=4, context_start=0, context_end=4):
    return {"case_id": "synthetic-role-case", "score_id": ir["score"]["score_id"],
            "ir_document_id": ir["ir_document_id"], "ir_content_sha256": pattern.digest(ir),
            "source_files": deepcopy(ir["source_files"]),
            "source_statement_ref": {"record_id": "source-fixture", "record_sha256": "a" * 64},
            "alignment_ref": {"record_id": "alignment-fixture", "record_sha256": "b" * 64},
            "target_span": {"start": pattern.q(start), "end": pattern.q(end)},
            "context_span": {"start": pattern.q(context_start), "end": pattern.q(context_end)}}


def pitch_member(step, alter=0):
    return {"step": step, "alter": pattern.q(alter)}


def segment(segment_id, start, end, root="C", members=None, *, status="usable", blockers=None):
    if members is None:
        members = [pitch_member("C"), pitch_member("E"), pitch_member("G")]
    return {"segment_id": segment_id,
            "span": {"start": pattern.q(start), "end": pattern.q(end)},
            "label": f"caller-{segment_id}", "root": pitch_member(root),
            "members": deepcopy(members), "status": status,
            "blockers": list(blockers or []), "source_locator": None}


def track_for(ir, segments):
    return assumptions.build_track(ir, segments, {
        "kind": "caller_hypothesis", "engine_version": "test-v1",
        "source_document_sha256": None, "source_path": None,
        "pitch_basis": "written_IR_not_concert_certified", "status": "hypothesis_not_gold"})


def reseal(record):
    payload = {key: value for key, value in record.items()
               if key not in ("record_id", "record_sha256")}
    record["record_sha256"] = pattern.digest(payload)
    prefix = record["record_id"].rsplit("_", 1)[0] + "_"
    record["record_id"] = prefix + record["record_sha256"][:24]
    return record


class MusicalRoleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, lanes, **scope_options):
        ir = make_ir(self.temp.name, lanes)
        observation = pattern.observe(ir, scope_for(ir, **scope_options))
        return ir, observation

    def episodes(self, record, spelling):
        return [row for row in record["literal"]["pitch_episodes"]
                if row["pitch"]["spelling"] == spelling]

    def episode_profile(self, record, condition_index, episode):
        return next(row for row in record["conditional"][condition_index]["pedal_profiles"]
                    if row["episode_id"] == episode["episode_id"])

    def test_exact_replay_immutability_and_research_only_contract(self):
        ir, observation = self.fixture([[event("C4", 0, 4)]])
        tracks = [track_for(ir, [segment("c", 0, 4)])]
        before = deepcopy((ir, observation, tracks))
        record = roles.analyze(ir, observation, tracks=tracks)
        roles.validate_evidence(record, ir=ir, observation=observation, tracks=tracks)
        self.assertEqual((ir, observation, tracks), before)
        self.assertEqual(roles.analyze(ir, observation, tracks=tracks), record)
        self.assertEqual(record["scope"], observation["scope"])
        self.assertEqual(record["observation_ref"]["record_id"], observation["record_id"])
        self.assertEqual(record["observation_ref"]["record_sha256"], observation["record_sha256"])
        self.assertEqual(record["semantics"], {
            "roles_validated": False, "melody_or_bass_selected": False,
            "chord_assumption_selected": False, "generation_ready": False})
        self.assertTrue(record["use_policy"]["research_only"])
        self.assertFalse(record["use_policy"]["training_eligible"])
        self.assertEqual(record["use_policy"]["gold_status"], "not_established")

    def test_tie_continuation_is_not_a_reattack_and_rest_is_not_bridged(self):
        tied_ir, tied_observation = self.fixture([[
            event("C4", 0, 2, tie_role="start"), event("C4", 2, 2, tie_role="stop")]])
        tied = roles.analyze(tied_ir, tied_observation)
        episode = self.episodes(tied, "C4")[0]
        self.assertEqual(episode["mode"], "single_sound")
        self.assertEqual(len(episode["sounding_event_ids"]), 1)
        self.assertEqual(len(episode["attack_note_ids_context"]), 1)
        self.assertEqual(len(episode["tie_continuation_note_ids"]), 1)
        self.assertEqual(len(episode["source_note_ids"]), 2)
        grouped_ids = {item for group in tied["literal"]["onset_groups"] for item in group["note_ids"]}
        self.assertTrue(set(episode["tie_continuation_note_ids"]).isdisjoint(grouped_ids))

        ir, observation = self.fixture([[
            event("C4", 0, 1), event("C4", 1, 1),
            event(None, 2, 1), event("C4", 3, 1)]])
        record = roles.analyze(ir, observation)
        episodes = self.episodes(record, "C4")
        self.assertEqual(len(episodes), 2)
        touching = next(row for row in episodes if len(row["sounding_event_ids"]) == 2)
        self.assertEqual(touching["mode"], "touching_reattacks")
        self.assertEqual(len(touching["attack_note_ids_context"]), 2)
        self.assertEqual(touching["tie_continuation_note_ids"], [])
        self.assertEqual(touching["original_span"], {"start": pattern.q(0), "end": pattern.q(2)})
        self.assertEqual(len(record["literal"]["rests"]), 1)
        self.assertEqual(record["literal"]["rests"][0]["span"],
                         {"start": pattern.q(2), "end": pattern.q(3)})
        self.assertEqual(record["conditional"], [])

    def test_octave_enharmonic_and_raw_lane_are_not_exact_pitch_identity(self):
        ir, observation = self.fixture([
            [event("C4", 0, 1), event("C5", 1, 1), event("B#4", 2, 1), event("C5", 3, 1)],
            [event("C4", 0, 4)]])
        record = roles.analyze(ir, observation)
        episodes = record["literal"]["pitch_episodes"]
        self.assertEqual(len(episodes), 5)
        self.assertEqual(len(self.episodes(record, "C4")), 2)
        self.assertEqual(len(self.episodes(record, "C5")), 2)
        self.assertEqual(len(self.episodes(record, "B#4")), 1)
        self.assertTrue(all(row["mode"] == "single_sound" for row in episodes))
        self.assertEqual(len({(row["lane"]["part_id"], row["lane"]["voice_id"])
                              for row in self.episodes(record, "C4")}), 2)

    def test_overlapping_same_pitch_is_recorded_as_ambiguous_not_unique_chain(self):
        ir, observation = self.fixture([[event("E4", 0, 2), event("E4", 1, 3)]])
        record = roles.analyze(ir, observation)
        episode = self.episodes(record, "E4")[0]
        self.assertEqual(episode["mode"], "overlapping_same_pitch")
        self.assertTrue(episode["overlap_ambiguous"])
        self.assertEqual(len(episode["sounding_event_ids"]), 2)
        self.assertEqual(len(episode["attack_note_ids_context"]), 2)

    def test_context_clipping_preserves_original_attack_and_exclusive_endpoint(self):
        ir, observation = self.fixture([
            [event("C4", 0, 2, tie_role="start"), event("C4", 2, 2, tie_role="stop")],
            [event("G4", 1, 0, grace=True), event("E4", 1, 1),
             event("B4", 3, 0, grace=True), event("F4", 3, 1)]],
            start=1, end=3, context_start=1, context_end=4)
        record = roles.analyze(ir, observation)
        episode = self.episodes(record, "C4")[0]
        self.assertEqual(episode["original_span"], {"start": pattern.q(0), "end": pattern.q(4)})
        self.assertEqual(episode["observed_span"], {"start": pattern.q(1), "end": pattern.q(4)})
        self.assertEqual(episode["target_overlap"], {"start": pattern.q(1), "end": pattern.q(3)})
        self.assertTrue(episode["context_clipped_start"])
        self.assertFalse(episode["context_clipped_end"])
        self.assertEqual(episode["attack_note_ids_context"], [])
        self.assertEqual(len(episode["tie_continuation_note_ids"]), 1)
        endpoint = self.episodes(record, "F4")[0]
        self.assertIsNone(endpoint["target_overlap"])
        grace_ids = {row["note_id"] for row in ir["note_events"] if row["grace"]["is_grace"]}
        self.assertEqual(len(record["literal"]["grace_points"]), len(grace_ids))
        episode_ids = {item for row in record["literal"]["pitch_episodes"] for item in row["source_note_ids"]}
        grouped_ids = {item for row in record["literal"]["onset_groups"] for item in row["note_ids"]}
        self.assertTrue(grace_ids.isdisjoint(episode_ids | grouped_ids))
        self.assertEqual(pattern.reconstruct(observation),
                         [deepcopy(slot["core_event"]) for slot in observation["slots"]])

    def test_simultaneous_chord_is_not_sequential_triplet_attacks(self):
        ir, observation = self.fixture([[event(["C4", "E4", "G4"], 0, 4)]])
        tracks = [track_for(ir, [segment("c", 0, 4)])]
        record = roles.analyze(ir, observation, tracks=tracks)
        groups = record["literal"]["onset_groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["note_ids"]), 3)
        profile = record["conditional"][0]["sequential_profiles"][0]
        self.assertEqual(profile["status"], "insufficient_shape")
        self.assertFalse(profile["arpeggio_confirmed"])

        ir, observation = self.fixture([[
            event("C4", 0, Fraction(1, 3)), event("E4", Fraction(1, 3), Fraction(1, 3)),
            event("G4", Fraction(2, 3), Fraction(10, 3))]])
        tracks = [track_for(ir, [segment("c", 0, 4)])]
        record = roles.analyze(ir, observation, tracks=tracks)
        self.assertEqual([row["onset"] for row in record["literal"]["onset_groups"]],
                         [pattern.q(0), pattern.q(Fraction(1, 3)), pattern.q(Fraction(2, 3))])
        profile = record["conditional"][0]["sequential_profiles"][0]
        self.assertEqual(profile["status"], "broken_chord_shape")
        self.assertEqual(profile["missing_members"], [])
        self.assertFalse(profile["arpeggio_confirmed"])
        degrees = {item: degree for group in profile["onset_groups"]
                   for item, degree in group["degree_by_note"].items()}
        self.assertEqual({n["written_pitch"]["spelling"]: degrees[n["note_id"]]
                          for n in ir["note_events"]}, {"C4": 1, "E4": 3, "G4": 5})

    def test_overlapping_durations_still_have_sequential_onsets(self):
        ir, observation = self.fixture([[
            event("C4", 0, 4), event("E4", Fraction(1, 3), Fraction(11, 3)),
            event("G4", Fraction(2, 3), Fraction(10, 3))]])
        self.assertEqual(len({n["voice_id"] for n in ir["note_events"]}), 1)
        self.assertEqual([n["global_onset_quarter"] for n in ir["note_events"]],
                         [pattern.q(0), pattern.q(Fraction(1, 3)), pattern.q(Fraction(2, 3))])
        record = roles.analyze(ir, observation, tracks=[track_for(ir, [segment("c", 0, 4)])])
        self.assertEqual(len(record["literal"]["onset_groups"]), 3)
        self.assertEqual(record["conditional"][0]["sequential_profiles"][0]["status"],
                         "broken_chord_shape")

    def test_inner_pedal_membership_is_conditional_on_competing_tracks(self):
        ir, observation = self.fixture([
            [event("E4", 0, 4)],
            [event("A2", 0, 1), event("D2", 1, 1), event("A2", 2, 2)]])
        d_members = [pitch_member("D"), pitch_member("F", 1), pitch_member("A")]
        e_members = [pitch_member("E"), pitch_member("G"), pitch_member("B")]
        tracks = [track_for(ir, [segment("c1", 0, 1),
                                segment("d", 1, 2, "D", d_members), segment("c2", 2, 4)]),
                  track_for(ir, [segment("e", 0, 4, "E", e_members)])]
        record = roles.analyze(ir, observation, tracks=tracks)
        self.assertEqual(len(record["conditional"]), 2)
        episode = self.episodes(record, "E4")[0]
        first = self.episode_profile(record, 0, episode)
        second = self.episode_profile(record, 1, episode)
        self.assertEqual([cell["membership"] for cell in first["cells"]],
                         ["member", "nonmember", "member"])
        self.assertEqual(first["status"], "anchored_pedal_shape")
        self.assertEqual([cell["membership"] for cell in second["cells"]], ["member"])
        self.assertEqual(second["status"], "no_pedal_shape")
        self.assertFalse(first["pedal_confirmed"])
        self.assertFalse(second["pedal_confirmed"])
        self.assertFalse(record["semantics"]["melody_or_bass_selected"])
        self.assertFalse(record["semantics"]["chord_assumption_selected"])

    def test_display_crop_uses_full_context_but_context_crop_withholds_anchor(self):
        ir, observation = self.fixture([[event("E4", 0, 4)]], start=1, end=2)
        d_members = [pitch_member("D"), pitch_member("F", 1), pitch_member("A")]
        tracks = [track_for(ir, [segment("c1", 0, 1),
                                segment("d", 1, 2, "D", d_members), segment("c2", 2, 4)])]
        record = roles.analyze(ir, observation, tracks=tracks)
        episode = self.episodes(record, "E4")[0]
        profile = self.episode_profile(record, 0, episode)
        self.assertEqual(episode["target_overlap"], {"start": pattern.q(1), "end": pattern.q(2)})
        self.assertEqual(profile["status"], "anchored_pedal_shape")
        self.assertEqual([row["membership"] for row in profile["cells"]],
                         ["member", "nonmember", "member"])
        cropped = pattern.observe(ir, scope_for(ir, 1, 2, Fraction(1, 2), 3))
        record = roles.analyze(ir, cropped, tracks=tracks)
        episode = self.episodes(record, "E4")[0]
        self.assertTrue(episode["context_clipped_start"])
        self.assertTrue(episode["context_clipped_end"])
        self.assertEqual(self.episode_profile(record, 0, episode)["status"], "unanchored_pedal_shape")

    def test_gap_blocked_segment_and_two_cell_shape_cannot_supply_return_anchor(self):
        ir, observation = self.fixture([[event("E4", 0, 4)]])
        d_members = [pitch_member("D"), pitch_member("F", 1), pitch_member("A")]
        tracks = [track_for(ir, [segment("c1", 0, 1), segment("c2", 2, 4)]),
                  track_for(ir, [segment("c1", 0, 1),
                                 segment("blocked", 1, 2, "D", d_members,
                                         status="blocked", blockers=["synthetic_unresolved"]),
                                 segment("c2", 2, 4)]),
                  track_for(ir, [segment("c", 0, 1), segment("d", 1, 4, "D", d_members)])]
        record = roles.analyze(ir, observation, tracks=tracks)
        episode = self.episodes(record, "E4")[0]
        gap, blocked, two_cells = [self.episode_profile(record, i, episode) for i in range(3)]
        self.assertEqual(gap["cells"][1]["span"], {"start": pattern.q(1), "end": pattern.q(2)})
        self.assertEqual(gap["cells"][1]["membership"], "unknown")
        self.assertIsNone(gap["cells"][1]["segment_id"])
        self.assertTrue(gap["blockers"])
        self.assertIn("synthetic_unresolved", blocked["blockers"])
        self.assertTrue(all(row["status"] != "anchored_pedal_shape"
                            for row in (gap, blocked, two_cells)))
        self.assertEqual(two_cells["status"], "unanchored_pedal_shape")
        self.assertTrue(all(not row["pedal_confirmed"] for row in (gap, blocked, two_cells)))

    def test_pitch_union_across_harmonic_change_is_not_one_broken_chord(self):
        ir, observation = self.fixture([[
            event("C4", 0, Fraction(1, 3)), event("E4", Fraction(1, 3), Fraction(1, 3)),
            event("G4", Fraction(2, 3), Fraction(10, 3))]])
        d_members = [pitch_member("D"), pitch_member("F", 1), pitch_member("A")]
        tracks = [track_for(ir, [segment("first", 0, Fraction(1, 3)),
                                segment("second", Fraction(1, 3), 4, "D", d_members)])]
        record = roles.analyze(ir, observation, tracks=tracks)
        profiles = record["conditional"][0]["sequential_profiles"]
        self.assertEqual({row["segment_id"] for row in profiles}, {"first", "second"})
        self.assertTrue(all(row["status"] == "insufficient_shape" for row in profiles))
        second = next(row for row in profiles if row["segment_id"] == "second")
        self.assertEqual(second["missing_members"], d_members)
        nonmembers = {item for group in second["onset_groups"] for item in group["nonmember_note_ids"]}
        self.assertEqual(nonmembers, {n["note_id"] for n in ir["note_events"]
                                     if n["written_pitch"]["spelling"] in ("E4", "G4")})

    def test_source_prose_does_not_choose_geometry_or_harmonic_role(self):
        ir, _ = self.fixture([[event("C4", 0, 1), event("C4", 1, 3)]])
        records = []
        for prose in ("Pedal: C", "Arpeggio: C", "No role description"):
            version = deepcopy(ir)
            version["score"]["metadata"]["source_prose"] = prose
            observation = pattern.observe(version, scope_for(version))
            tracks = [track_for(version, [segment("c", 0, 4)])]
            records.append(roles.analyze(version, observation, tracks=tracks))
        for record in records[1:]:
            self.assertEqual(record["literal"], records[0]["literal"])
            self.assertEqual(record["conditional"][0]["pedal_profiles"],
                             records[0]["conditional"][0]["pedal_profiles"])
            self.assertEqual(record["conditional"][0]["sequential_profiles"],
                             records[0]["conditional"][0]["sequential_profiles"])

    def test_stale_ir_and_resealed_observation_omission_are_rejected_by_replay(self):
        ir, observation = self.fixture([[event("C4", 0, 1), event("E4", 1, 3)]])
        record = roles.analyze(ir, observation)
        stale_ir = deepcopy(ir)
        stale_ir["score"]["metadata"]["changed_after_observation"] = True
        with self.assertRaises(ValueError):
            roles.analyze(stale_ir, observation)
        with self.assertRaises(ValueError):
            roles.validate_evidence(record, ir=stale_ir, observation=observation, tracks=[])
        omitted = deepcopy(observation)
        omitted["slots"].pop()
        reseal(omitted)
        pattern.validate_observation(omitted)
        with self.assertRaises(ValueError):
            roles.analyze(ir, omitted)
        with self.assertRaises(ValueError):
            roles.validate_evidence(record, ir=ir, observation=omitted, tracks=[])

    def test_resealed_feature_tampering_and_role_training_gold_promotions_fail(self):
        ir, observation = self.fixture([[event("C4", 0, 4)]])
        record = roles.analyze(ir, observation)
        altered = deepcopy(record)
        altered["literal"]["pitch_episodes"][0]["context_clipped_start"] = True
        reseal(altered)
        with self.assertRaises((ValueError, ValidationError)):
            roles.validate_evidence(altered, ir=ir, observation=observation, tracks=[])
        promotions = [("semantics", field, True) for field in
                      ("roles_validated", "melody_or_bass_selected", "chord_assumption_selected", "generation_ready")]
        promotions += [("use_policy", "training_eligible", True),
                       ("use_policy", "gold_status", "gold")]
        for container, field, value in promotions:
            with self.subTest(field=field):
                altered = deepcopy(record)
                altered[container][field] = value
                reseal(altered)
                with self.assertRaises((ValueError, ValidationError)):
                    roles.validate_evidence(altered)

    def test_mutating_returned_record_does_not_mutate_inputs_or_next_analysis(self):
        ir, observation = self.fixture([[event("C4", 0, 4)]])
        tracks = [track_for(ir, [segment("c", 0, 4)])]
        before = deepcopy((ir, observation, tracks))
        original = roles.analyze(ir, observation, tracks=tracks)
        altered = roles.analyze(ir, observation, tracks=tracks)
        altered["literal"]["pitch_episodes"][0]["pitch"]["spelling"] = "F#9"
        altered["scope"]["target_span"]["end"] = pattern.q(1)
        altered["conditional"][0]["pedal_profiles"][0]["cells"][0]["label"] = "mutated"
        self.assertEqual((ir, observation, tracks), before)
        self.assertEqual(roles.analyze(ir, observation, tracks=tracks), original)

    def test_structurally_valid_but_inconsistent_sound_contract_is_held(self):
        ir, _ = self.fixture([[event("C4", 0, 4)]])
        for mode, error in (("duration", "duration_span"), ("attack", "attack_reference"),
                            ("note_duration", "source_note_duration"), ("missing_sound", "sounding_membership")):
            changed = deepcopy(ir)
            if mode == "duration":
                changed["sounding_events"][0]["sounding_duration"] = pattern.q(3)
            elif mode == "attack":
                changed["attack_events"] = []
            elif mode == "note_duration":
                changed["note_events"][0]["notated_duration_quarter"] = pattern.q(3)
            else:
                changed["sounding_events"] = []
                changed["attack_events"] = []
            observation = pattern.observe(changed, scope_for(changed))
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, error):
                roles.analyze(changed, observation)

    def test_null_root_membership_and_attack_rhythm_are_explicit(self):
        ir, observation = self.fixture([[event("C4", 0, Fraction(1, 3)),
                                        event("E4", Fraction(1, 3), Fraction(1, 3)),
                                        event("G4", Fraction(2, 3), Fraction(10, 3))]])
        candidate = segment("unknown-root", 0, 4)
        candidate["root"] = None
        tracks = [track_for(ir, [candidate])]
        record = roles.analyze(ir, observation, tracks)
        profile = record["conditional"][0]["sequential_profiles"][0]
        self.assertEqual(profile["membership_scope"], "attacks_only")
        self.assertEqual(profile["onset_deltas_quarter"], [pattern.q(Fraction(1, 3))] * 2)
        self.assertEqual(profile["status"], "broken_chord_shape")
        self.assertTrue(all(d is None for g in profile["onset_groups"] for d in g["degree_by_note"].values()))
        with self.assertRaisesRegex(ValueError, "duplicate_harmony_track"):
            roles.analyze(ir, observation, [tracks[0], tracks[0]])

    def test_blocked_harmony_does_not_turn_unknown_into_nonmember_or_missing(self):
        ir, observation = self.fixture([[event("C4", 0, 1), event("E4", 1, 1), event("G4", 2, 2)]])
        blocked = segment("blocked", 0, 4, status="blocked", blockers=["source_not_aligned"])
        record = roles.analyze(ir, observation, [track_for(ir, [blocked])])
        profile = record["conditional"][0]["sequential_profiles"][0]
        self.assertIsNone(profile["missing_members"])
        self.assertIn("source_not_aligned", profile["blockers"])
        for group in profile["onset_groups"]:
            self.assertEqual(group["unknown_note_ids"], group["note_ids"])
            self.assertEqual(group["member_note_ids"], [])
            self.assertEqual(group["nonmember_note_ids"], [])


if __name__ == "__main__":
    unittest.main()
