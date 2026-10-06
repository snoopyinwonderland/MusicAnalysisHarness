"""Independent XML/IR controls for conditional progression/role linking."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import gc
from hashlib import sha256
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import weakref

from musicanote_harness import musical_pattern_observation as observation_module
from musicanote_harness import musical_progression_role_link as links
from musicanote_harness.harmony_context_bundle import bundle
from musicanote_harness.harmony_progression_context import build
from musicanote_harness.harmony_progression_search import search
from musicanote_harness.harmony_voice_paths import observe as voice_observe
from musicanote_harness.musical_pattern_observation import digest, f, q
from test_musical_role_evidence import event, make_ir, scope_for


MEMBERS = [(["C", 0], [["C", 0], ["E", 0], ["G", 0]]),
           (["F", 0], [["F", 0], ["A", 0], ["C", 0]]),
           (["D", 0], [["D", 0], ["F", 1], ["A", 0]])]


def provider_for(candidates):
    def provide(ir, span, context):
        return {"candidates": [{"candidate_id": "candidate-" + str(index),
            "origin_pointer": "/authored-catalog/" + str(index), "provider": "authored-test",
            "span": deepcopy(span), "spelling_alternatives": [{"root_spelling": deepcopy(root), "members": deepcopy(members)}],
            "missing_spellings_by_alternative": [[]], "abstention_reasons": []}
            for index, (root, members) in enumerate(candidates)]}
    return provide


def path_for(lattice, pieces):
    return [{"edge": next(i for i, edge in enumerate(lattice["edges"])
                          if (edge["from"], edge["to"]) == (a, b)), "reading": reading}
            for a, b, reading in pieces]


def reseal(record):
    record["record_sha256"] = digest({key: value for key, value in record.items()
                                      if key not in ("record_id", "record_sha256")})
    record["record_id"] = "mprl_" + record["record_sha256"][:24]
    return record


class MusicalProgressionRoleLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def fixture(self, lanes=None, *, candidates=None, lane_index=0, **scope_options):
        lanes = lanes or [[event("C4", 0, 1), event("D4", 1, 1), event("E4", 2, 2)]]
        ir = make_ir(self.temp.name, lanes)
        observation = observation_module.observe(ir, scope_for(ir, **scope_options))
        context = observation["scope"]["context_span"]
        raw_lanes = [(row["part_id"], row["voice_id"]) for row in observation["raw_lanes"]]
        part_id = ir["score"]["part_ids"][lane_index]
        lane = next(row for row in raw_lanes if row[0] == part_id)
        voices = voice_observe(ir, context, lane)
        self.assertTrue(voices["enumeration_complete"])
        sounds = [s for s in ir["sounding_events"]
                  if f(s["span"]["start"]) < f(context["end"]) and f(s["span"]["end"]) > f(context["start"])]
        with (patch("musicanote_harness.harmony_progression_context.propose", side_effect=provider_for(candidates or MEMBERS)),
              patch("musicanote_harness.harmony_progression_context.label", side_effect=lambda cat, c, ai: "stored-" + c["candidate_id"])):
            lattice = build(ir, {"status": "ready", "span": deepcopy(context), "events": sounds,
                                 "assignments": voices["assignments"]})
        sample = {"sample_id": "independent-xml-fixture", "span": deepcopy(context), "lane": list(lane)}
        stored = {"sample": sample, "summary": {"source_labels_used": False}, "stages": {
            "lattice": lattice, "relations": {"status": "ready", "plan": {"pairs": []}, "results": []},
            "hold_change": {"status": "ready", "chain_comparisons": []}}}
        context_bundle = bundle(ir, stored)
        last = len(lattice["plan"]["points"]) - 1
        proposal = {"proposal_id": "explicit-authored-path", "path": path_for(lattice, [(0, last, 0)]),
                    "complete_context_path": True, "provenance": {"kind": "authored_test_path_not_source_label"}}
        assignment = max(lattice["assignments"], key=lambda row: len(row["links"]))["assignment_id"]
        policy = {"harmonic_replay_allowed": True, "pitch_basis": "written_IR_not_concert_certified",
            "ir_content_sha256": digest(ir), "source_sha256": ir["source_files"][0]["sha256"],
            "source_path": self.temp.name + "/score.musicxml", "source_transpose_elements": [],
            "nonzero_source_transposition": False, "malformed_or_unsupported_transposition": False,
            "concert_pitch_normalization_verified": False}
        return ir, observation, context_bundle, proposal, assignment, policy

    def call(self, data, *, search_result=None):
        ir, observation, context_bundle, proposal, aid, policy = data
        return links.link(ir, observation, context_bundle, proposal, aid, pitch_policy=policy, search_result=search_result)

    def validate(self, record, data, *, search_result=None):
        ir, observation, context_bundle, proposal, aid, policy = data
        links.validate_link(record, ir=ir, observation=observation, bundle=context_bundle,
                            proposal=proposal, assignment_ref=aid, pitch_policy=policy, search_result=search_result)

    def test_formal_ir_fresh_replay_seal_exact_sources_and_immutability(self):
        data = self.fixture(); before = deepcopy(data)
        record = self.call(data); self.validate(record, data)
        self.assertEqual(data, before)
        self.assertEqual(self.call(data), record)
        self.assertEqual(record["input_refs"]["bundle_content_sha256"], digest(data[2]))
        self.assertEqual(record["input_refs"]["pitch_policy_content_sha256"], digest(data[5]))
        self.assertEqual(record["pitch_policy"], data[5])
        self.assertTrue(record["use_policy"]["research_only"])
        self.assertFalse(record["use_policy"]["training_eligible"])
        self.assertEqual(record["use_policy"]["gold_status"], "not_established")
        self.assertTrue(all(value is False for value in record["semantics"].values()))
        self.assertTrue(record["sound_source_refs"])
        source_refs = {s["source_ref_id"]: s for s in data[0]["source_references"]}
        for sound in record["sound_source_refs"]:
            for note_ref in sound["note_refs"]:
                self.assertEqual(note_ref["source_ref"], source_refs[note_ref["source_ref_id"]])
        for item in record["note_time_source_refs"]:
            self.assertTrue(item["notated_note_overlap_refs"])
            self.assertEqual(sum(f(r["span"]["end"]) - f(r["span"]["start"])
                                 for r in item["notated_note_overlap_refs"]),
                             f(item["span"]["end"]) - f(item["span"]["start"]))

    def test_assignment_specific_nct_never_changes_track_or_raw_membership(self):
        data = self.fixture(); record = self.call(data)
        none = next(a["assignment_id"] for a in data[2]["stages"]["lattice"]["assignments"] if not a["links"])
        second_data = (*data[:4], none, data[5]); second = self.call(second_data)
        self.assertEqual(record["harmony_assumption_track"], second["harmony_assumption_track"])
        self.assertEqual(record["raw_note_time"], second["raw_note_time"])
        self.assertEqual(record["progression_evidence"]["accounting"]["note_time"]["conditional_nonmember"], q(1))
        self.assertEqual(second["progression_evidence"]["accounting"]["note_time"]["unexplained_nonmember"], q(1))
        self.assertEqual(second["active_pattern_links"], [])
        self.assertTrue(record["active_pattern_links"])
        self.assertEqual(record["active_pattern_links"][0]["shared_assignment_ref"], data[4])
        self.assertFalse(record["active_pattern_links"][0]["confirmed_nct"])
        profiles = record["role_evidence"]["conditional"][0]["sequential_profiles"]
        self.assertEqual(profiles[0]["status"], "insufficient_shape")
        self.assertIn("nonmember_or_unknown_attacks_present", profiles[0]["blockers"])
        foreign = [r for r in record["note_time_source_refs"] if r["conditional_bucket"] == "conditional_nonmember"]
        self.assertTrue(foreign)
        self.assertTrue(all(r["raw_membership"] == "nonmember" for r in foreign))

    def test_blocked_segment_remains_unknown_role_and_has_no_nct_exemption(self):
        data = self.fixture(); choice = data[3]["path"][0]
        reading = data[2]["stages"]["lattice"]["edges"][choice["edge"]]["readings"][choice["reading"]]
        reading["abstention_reasons"] = ["grace_timing_not_supported"]
        record = self.call(data)
        segment = record["harmony_assumption_track"]["segments"][0]
        self.assertEqual(segment["status"], "blocked")
        self.assertEqual(segment["blockers"], ["grace_timing_not_supported"])
        self.assertEqual(record["active_pattern_links"], [])
        profile = record["role_evidence"]["conditional"][0]["pedal_profiles"][0]
        self.assertTrue(all(cell["membership"] == "unknown" for cell in profile["cells"]))

    def test_prepared_shape_keeps_withheld_reasons_and_exact_foreign_time(self):
        data = self.fixture([[event("E4", 0, 2), event("D4", 2, 2)],
                             [event("G3", 0, 1), event("F#3", 1, 3)]])
        lattice = data[2]["stages"]["lattice"]
        data[3]["path"] = path_for(lattice, [(0, 1, 0), (1, 3, 2)])
        record = self.call(data)
        self.assertEqual(record["progression_evidence"]["accounting"]["note_time"]["withheld_nonmember"], q(1))
        self.assertEqual(record["progression_evidence"]["accounting"]["note_time"]["conditional_nonmember"], q(0))
        withheld = next(row for row in record["active_pattern_links"] if row["withheld_reasons"])
        self.assertIn("preparation_dissonance_resolution_accent_not_verified", withheld["withheld_reasons"])
        self.assertEqual(withheld["pattern"]["kind"], "prepared_suspension_candidate")
        for index in withheld["accounting_item_indices"]:
            row = record["note_time_source_refs"][index]
            self.assertEqual(row["raw_membership"], "nonmember")
            self.assertEqual(row["conditional_bucket"], "withheld_nonmember")
        self.assertFalse(withheld["raw_membership_exemption"])

    def test_null_root_and_explicit_display_label_are_not_inferred(self):
        data = self.fixture(candidates=[(None, MEMBERS[0][1])]); record = self.call(data)
        segment = record["harmony_assumption_track"]["segments"][0]
        self.assertIsNone(segment["root"])
        self.assertEqual(segment["label"], "stored-candidate-0")
        self.assertEqual(segment["members"][0], {"step": "C", "alter": q(0)})

    def test_exact_thirds_and_time_references_are_never_float_rounded(self):
        data = self.fixture([[event("C4", 0, Fraction(1, 3)), event("D4", Fraction(1, 3), Fraction(1, 3)),
                              event("E4", Fraction(2, 3), Fraction(10, 3))]])
        record = self.call(data)
        self.assertEqual(record["progression_evidence"]["accounting"]["note_time"]["conditional_nonmember"], q(Fraction(1, 3)))
        self.assertEqual(record["raw_note_time"]["nonmember_not_confirmed_nct"], q(Fraction(1, 3)))

    def test_tied_notation_is_one_sound_one_attack_and_retains_both_source_notes(self):
        data = self.fixture([[event("C4", 0, 2, tie_role="start"), event("C4", 2, 2, tie_role="stop")]])
        record = self.call(data)
        self.assertEqual(len(record["sound_source_refs"]), 1)
        self.assertEqual(len(record["sound_source_refs"][0]["source_note_ids"]), 2)
        episode = record["role_evidence"]["literal"]["pitch_episodes"][0]
        self.assertEqual(episode["mode"], "single_sound")
        self.assertEqual(len(episode["attack_note_ids_context"]), 1)

    def test_grace_point_in_unsampled_lane_retains_literal_source_without_note_time(self):
        data = self.fixture([[event("C4", 0, 4)],
                             [event("G4", 1, 0, grace=True), event("E4", 1, 3)]])
        record = self.call(data)
        points = record["role_evidence"]["literal"]["grace_points"]
        self.assertEqual(len(points), 1)
        point = points[0]
        source = next(row for row in record["sound_source_refs"] if row["sounding_event_id"] == point["sounding_event_id"])
        self.assertEqual(source["sounding_duration"], q(0))
        self.assertEqual(source["note_refs"][0]["notated_duration_quarter"], q(0))
        self.assertTrue(all(row["event_ref"] != point["sounding_event_id"] for row in record["note_time_source_refs"]))
        self.assertEqual(record["progression_evidence"]["accounting"]["total_note_time"], q(7))

    def test_grace_in_sampled_lane_has_no_positive_duration_partition(self):
        # The current progression vocabulary intentionally refuses this scope;
        # the standalone literal role observation remains available separately.
        ir = make_ir(self.temp.name, [[event("G4", 1, 0, grace=True), event("C4", 1, 3)]])
        observation = observation_module.observe(ir, scope_for(ir))
        self.assertTrue(observation["core_projection"]["sounding_events"])
        lanes = [[row["part_id"], row["voice_id"]] for row in observation["raw_lanes"]]
        voices = voice_observe(ir, observation["scope"]["context_span"], lanes[0])
        self.assertFalse(voices["enumeration_complete"])
        self.assertIn("nonpositive_duration", voices["abstention_reasons"])

    def test_same_members_split_changes_boundaries_not_raw_membership(self):
        data = self.fixture(); hold = self.call(data); lattice = data[2]["stages"]["lattice"]
        split_data = deepcopy(data)
        split_data[3]["path"] = path_for(lattice, [(0, 1, 0), (1, 2, 0), (2, 3, 0)])
        split = self.call(split_data)
        self.assertEqual(hold["raw_note_time"], split["raw_note_time"])
        self.assertEqual(hold["progression_evidence"]["accounting"]["note_time"],
                         split["progression_evidence"]["accounting"]["note_time"])
        self.assertEqual(len(split["harmony_assumption_track"]["segments"]), 3)
        self.assertFalse(split["semantics"]["harmony_selected"])

    def test_sequential_shape_stays_unresolved_arpeggio_or_chord_tone_melody(self):
        data = self.fixture([[event("C4", 0, 1), event("E4", 1, 1), event("G4", 2, 2)]])
        record = self.call(data)
        profile = record["role_evidence"]["conditional"][0]["sequential_profiles"][0]
        self.assertEqual(profile["status"], "broken_chord_shape")
        self.assertEqual(profile["alternatives"], ["arpeggio", "chord_tone_melody", "other_texture"])
        self.assertFalse(profile["arpeggio_confirmed"])
        self.assertIsNone(record["unresolved_role_links"][-1]["role_selected"])

    def test_pedal_shape_can_be_nonlowest_and_does_not_exempt_nonmembers(self):
        data = self.fixture([[event("C5", 0, 4)],
                             [event("C3", 0, 1), event("D3", 1, 1), event("E3", 2, 2)]], lane_index=1)
        lattice = data[2]["stages"]["lattice"]
        data[3]["path"] = path_for(lattice, [(0, 1, 0), (1, 2, 2), (2, 3, 0)])
        record = self.call(data)
        profiles = record["role_evidence"]["conditional"][0]["pedal_profiles"]
        self.assertTrue(any(p["status"] == "anchored_pedal_shape" for p in profiles))
        self.assertTrue(all(p["pedal_confirmed"] is False for p in profiles))
        self.assertEqual(record["raw_note_time"]["nonmember_not_confirmed_nct"], q(1))
        self.assertEqual(record["progression_evidence"]["accounting"]["note_time"]["unexplained_nonmember"], q(1))

    def test_profile_accounting_links_do_not_leak_held_tail_outside_segment(self):
        data = self.fixture([[event("C4", 0, 4)], [event("C3", 0, 2), event("D3", 2, 2)]])
        lattice = data[2]["stages"]["lattice"]
        data[3]["path"] = path_for(lattice, [(0, 1, 0), (1, 2, 2)])
        record = self.call(data)
        for profile in record["unresolved_role_links"]:
            a, b = f(profile["profile_span"]["start"]), f(profile["profile_span"]["end"])
            for row in profile["accounting_extent_links"]:
                self.assertLessEqual(a, f(row["overlap_span"]["start"]))
                self.assertLessEqual(f(row["overlap_span"]["end"]), b)
        sequential = [p for p in record["unresolved_role_links"] if p["profile_kind"] == "sequential_profile"]
        self.assertTrue(sequential)
        for profile in sequential:
            for index in profile["accounting_item_indices"]:
                item = record["progression_evidence"]["accounting"]["items"][index]
                self.assertLess(f(item["span"]["start"]), f(profile["profile_span"]["end"]))
                self.assertLess(f(profile["profile_span"]["start"]), f(item["span"]["end"]))

    def test_local_context_keeps_outside_track_coverage_holes(self):
        data = self.fixture(context_start=1, context_end=3, start=1, end=3)
        record = self.call(data)
        self.assertEqual(record["harmony_assumption_track"]["coverage_holes"],
                         [{"start": q(0), "end": q(1)}, {"start": q(3), "end": q(4)}])
        self.assertEqual(record["progression_evidence"]["context_span"], data[1]["scope"]["context_span"])

    def test_unknown_assignment_and_missing_lane_fail_closed(self):
        data = self.fixture()
        with self.assertRaisesRegex(ValueError, "unknown_or_duplicate"):
            self.call((*data[:4], "not-a-stored-assignment", data[5]))
        del data[2]["sample"]["lane"]
        with self.assertRaisesRegex(ValueError, "invalid_explicit_sample_lane"): self.call(data)

    def test_assignment_tracks_cannot_omit_isolated_events(self):
        data = self.fixture(); assignment = next(a for a in data[2]["stages"]["lattice"]["assignments"] if a["assignment_id"] == data[4])
        assignment["tracks"] = []
        with self.assertRaisesRegex(ValueError, "sampled_assignment_partition_mismatch"): self.call(data)

    def test_duplicate_assignment_and_branching_links_are_rejected(self):
        original = self.fixture()
        data = deepcopy(original); lattice = data[2]["stages"]["lattice"]
        lattice["assignments"].append(deepcopy(lattice["assignments"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate_assignment|unknown_or_duplicate"): self.call(data)
        data = deepcopy(original); assignment = next(a for a in data[2]["stages"]["lattice"]["assignments"] if a["assignment_id"] == data[4])
        assignment["links"].append(deepcopy(assignment["links"][0]))
        with self.assertRaisesRegex(ValueError, "branch_or_merge_not_allowed"): self.call(data)

    def test_cross_raw_lane_link_is_not_a_semantic_voice(self):
        data = self.fixture([[event("C4", 0, 2), event("E4", 2, 2)], [event("G3", 2, 2)]])
        lattice = data[2]["stages"]["lattice"]
        foreign = next(s["sounding_event_id"] for s in lattice["events"]
                       if all(n["part_id"] != data[2]["sample"]["lane"][0] for n in data[0]["note_events"] if n["note_id"] in s["source_note_ids"]))
        assignment = next(a for a in lattice["assignments"] if a["assignment_id"] == data[4])
        assignment["links"][0][1] = foreign
        with self.assertRaisesRegex(ValueError, "missing_event_reference"): self.call(data)

    def test_no_rest_bridging_in_a_sampled_assignment(self):
        data = self.fixture([[event("C4", 0, 1), event(None, 1, 1), event("E4", 2, 2)]])
        lattice = data[2]["stages"]["lattice"]
        assignment = next(a for a in lattice["assignments"] if a["assignment_id"] == data[4])
        assignment["links"] = [[lattice["events"][0]["sounding_event_id"], lattice["events"][1]["sounding_event_id"]]]
        with self.assertRaisesRegex(ValueError, "gap_overlap_or_backward_connection"): self.call(data)

    def test_raw_reading_state_tampering_cannot_cook_nct_bucket(self):
        data = self.fixture(); lattice = data[2]["stages"]["lattice"]
        reading = lattice["edges"][data[3]["path"][0]["edge"]]["readings"][0]
        sid = next(sid for sid, state in reading["event_states"].items() if state != "member")
        reading["event_states"][sid] = "member"
        with self.assertRaisesRegex(ValueError, "selected_reading_raw_membership_mismatch"): self.call(data)

    def test_interval_cell_and_event_geometry_mismatches_fail_closed(self):
        original = self.fixture()
        for mutation, expected in ((lambda lattice: lattice["cells"][0]["event_refs"].clear(), "stored_cell"),
                                   (lambda lattice: lattice["plan"]["points"].pop(), "stored_interval_plan|incomplete_context_path"),
                                   (lambda lattice: lattice["events"][0]["span"].update(end=q(3)), "ir_event_identity")):
            with self.subTest(expected=expected):
                data = deepcopy(original); mutation(data[2]["stages"]["lattice"])
                with self.assertRaisesRegex(ValueError, expected): self.call(data)

    def test_nct_geometry_and_support_are_replayed_not_trusted(self):
        original = self.fixture()
        for field in ("kind", "supporting_assignment_refs", "requirements"):
            with self.subTest(field=field):
                data = deepcopy(original); shape = data[2]["stages"]["lattice"]["patterns"][0]
                if field == "kind": shape[field] = "made-up-nct"
                elif field == "requirements": shape[field] = []
                else: shape[field] = []
                with self.assertRaisesRegex(ValueError, "progression_pattern_geometry_replay_mismatch"): self.call(data)

    def test_missing_uncertain_or_foreign_pitch_policy_fails_closed(self):
        original = self.fixture()
        fields = ("pitch_basis", "ir_content_sha256", "source_sha256", "nonzero_source_transposition",
                  "malformed_or_unsupported_transposition", "concert_pitch_normalization_verified")
        for field in fields:
            with self.subTest(field=field):
                data = deepcopy(original); del data[5][field]
                with self.assertRaises(ValueError): self.call(data)
        for field, value in (("harmonic_replay_allowed", 1), ("source_sha256", "f" * 64),
                             ("ir_content_sha256", "f" * 64), ("pitch_basis", "concert"),
                             ("nonzero_source_transposition", True), ("concert_pitch_normalization_verified", True)):
            with self.subTest(field=field, value=value):
                data = deepcopy(original); data[5][field] = value
                with self.assertRaises(ValueError): self.call(data)

    def test_source_label_flags_selected_path_and_context_mismatch_rejected(self):
        original = self.fixture()
        for target in ("bundle", "stage", "proposal"):
            data = deepcopy(original)
            if target == "bundle": data[2]["source_labels_used"] = True
            elif target == "stage": data[2]["stages"]["lattice"]["source_annotation_used"] = True
            else: data[3]["selected"] = "preferred"
            with self.subTest(target=target), self.assertRaises(ValueError): self.call(data)
        data = deepcopy(original); data[2]["sample"]["span"] = {"start": q(1), "end": q(4)}
        with self.assertRaisesRegex(ValueError, "context_mismatch"): self.call(data)

    def test_same_metadata_identity_without_full_working_ir_hash_is_rejected(self):
        original = self.fixture()
        for field, value in (("parent_ir_document_id", "other-document"), ("score_id", "other-score"),
                             ("input_ir_content_sha256", "f" * 64)):
            data = deepcopy(original); data[2][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "stale_or_foreign"): self.call(data)

    def test_roles_replay_source_note_geometry_even_when_bundle_hash_is_current(self):
        data = list(self.fixture([[event("C4", 0, 2, tie_role="start"), event("C4", 2, 2, tie_role="stop")]]))
        data[0]["note_events"][1]["global_onset_quarter"] = q(1)
        data[0]["note_events"][1]["onset_in_measure"] = q(1)
        data[1] = observation_module.observe(data[0], scope_for(data[0]))
        data[2]["input_ir_content_sha256"] = digest(data[0]); data[5]["ir_content_sha256"] = digest(data[0])
        with self.assertRaisesRegex(ValueError, "noncontiguous_sounding_source_notes"): self.call(data)

    def test_unknown_display_label_is_not_replaced_from_pitch_or_function(self):
        data = self.fixture(); choice = data[3]["path"][0]
        reading = data[2]["stages"]["lattice"]["edges"][choice["edge"]]["readings"][0]
        reading["display_label"] = "unknown"
        self.assertEqual(self.call(data)["harmony_assumption_track"]["segments"][0]["label"], "unknown")
        reading["display_label"] = ""
        with self.assertRaisesRegex(ValueError, "missing_explicit_candidate_display_label"): self.call(data)

    def test_incomplete_gap_overlap_or_bool_path_is_not_complete_context(self):
        original = self.fixture(); lattice = original[2]["stages"]["lattice"]
        for pieces in ([(0, 1, 0)], [(0, 1, 0), (2, 3, 0)], [(0, 2, 0), (1, 3, 0)]):
            data = deepcopy(original); data[3]["path"] = path_for(lattice, pieces)
            with self.subTest(pieces=pieces), self.assertRaises(ValueError): self.call(data)
        data = deepcopy(original); data[3]["path"][0]["reading"] = False
        with self.assertRaises(ValueError): self.call(data)

    def test_pitch_pair_requires_single_step_integer_alter(self):
        original = self.fixture()
        for bad in (["CDE", 0], [None, 0], ["C", True], ["C", 0.5]):
            data = deepcopy(original); choice = data[3]["path"][0]
            data[2]["stages"]["lattice"]["edges"][choice["edge"]]["readings"][0]["root_spelling"] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "unsupported_progression_pitch_pair"): self.call(data)

    def test_same_midi_enharmonic_sound_is_not_written_pitch_compatible(self):
        data = list(self.fixture([[event("C4", 0, 4)]])); ir = data[0]
        ir["sounding_events"][0]["pitch"].update(step="B", alter=q(1), octave=3, spelling="B#3")
        data[1] = observation_module.observe(ir, scope_for(ir))
        data[2]["stages"]["lattice"]["events"][0]["pitch"] = deepcopy(ir["sounding_events"][0]["pitch"])
        data[2]["input_ir_content_sha256"] = digest(ir); data[5]["ir_content_sha256"] = digest(ir)
        with self.assertRaisesRegex(ValueError, "progression_written_pitch_basis_mismatch"): self.call(data)

    def test_attack_source_reference_is_not_silently_replaced(self):
        data = self.fixture(); data[2]["stages"]["lattice"]["events"][0]["attack_note_id"] = data[0]["note_events"][1]["note_id"]
        with self.assertRaisesRegex(ValueError, "attack_note_reference_mismatch"): self.call(data)

    def test_tampered_or_resealed_promotion_is_rejected_by_fresh_replay(self):
        data = self.fixture(); record = self.call(data)
        broken = deepcopy(record); broken["semantics"]["harmony_selected"] = True
        with self.assertRaisesRegex(ValueError, "seal_mismatch"): self.validate(broken, data)
        for field in ("harmony_selected", "roles_validated", "pedal_confirmed", "arpeggio_confirmed", "generation_ready"):
            broken = deepcopy(record); broken["semantics"][field] = True; reseal(broken)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "replay_mismatch"): self.validate(broken, data)
        broken = deepcopy(record); broken["use_policy"]["training_eligible"] = True; reseal(broken)
        with self.assertRaisesRegex(ValueError, "replay_mismatch"): self.validate(broken, data)

    def test_bound_search_preserves_all_identical_origin_alternatives(self):
        data = self.fixture(candidates=MEMBERS + [MEMBERS[0]])
        proposals = search(data[2], max_complete_paths=8, max_segments=2, per_state_limit=8)
        proposal = next(p for p in proposals["proposals"] if len(p["path"]) == 1
                        and data[2]["stages"]["lattice"]["edges"][p["path"][0]["edge"]]["readings"][p["path"][0]["reading"]]["root_spelling"] == ["C", 0])
        data = (*data[:3], proposal, *data[4:]); record = self.call(data, search_result=proposals)
        self.validate(record, data, search_result=proposals)
        group = record["candidate_origins"][0]
        self.assertEqual(len(group["origins"]), 2)
        self.assertEqual({row["candidate_ref"] for row in group["origins"]}, {"candidate-0", "candidate-3"})
        self.assertFalse(group["representative_origin_preferred"])
        self.assertEqual(record["input_refs"]["search_result_content_sha256"], digest(proposals))

    def test_search_binding_group_origin_loss_or_proposal_change_rejected(self):
        original = self.fixture(candidates=MEMBERS + [MEMBERS[0]])
        proposals = search(original[2], max_complete_paths=8, max_segments=2, per_state_limit=8)
        proposal = next(p for p in proposals["proposals"] if len(p["path"]) == 1
                        and len(next(g for g in proposals["semantic_groups"] if g["group_id"] == p["semantic_group_refs"][0])["origins"]) == 2)
        data = (*original[:3], proposal, *original[4:])
        with self.assertRaisesRegex(ValueError, "require_bound_search_result"): self.call(data)
        changed = deepcopy(proposals); changed["input_bundle_content_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "search_bundle_binding_mismatch"): self.call(data, search_result=changed)
        changed = deepcopy(proposals); changed["proposals"].append(deepcopy(proposal))
        with self.assertRaisesRegex(ValueError, "duplicate_or_changed"): self.call(data, search_result=changed)
        changed = deepcopy(proposals); group = next(g for g in changed["semantic_groups"] if g["group_id"] == proposal["semantic_group_refs"][0])
        group["origin_reading_keys"] = [deepcopy(proposal["path"][0])]
        with self.assertRaisesRegex(ValueError, "search_semantic_group_origin_loss"): self.call(data, search_result=changed)

    def test_search_origin_text_and_nonblind_flag_tampering_rejected(self):
        original = self.fixture(candidates=MEMBERS + [MEMBERS[0]])
        proposals = search(original[2], max_complete_paths=8, max_segments=2, per_state_limit=8)
        proposal = next(p for p in proposals["proposals"] if len(p["path"]) == 1)
        data = (*original[:3], proposal, *original[4:])
        changed = deepcopy(proposals); group = next(g for g in changed["semantic_groups"] if g["group_id"] == proposal["semantic_group_refs"][0])
        group["origins"][0]["display_label"] = "human-corrected-label"
        with self.assertRaisesRegex(ValueError, "search_origin_provenance_mismatch"): self.call(data, search_result=changed)
        changed = deepcopy(proposals); changed["source_labels_used"] = True
        with self.assertRaisesRegex(ValueError, "nonblind_or_promoted_search"): self.call(data, search_result=changed)

    def prepare(self, data, *, search_result=None):
        return links.prepare_context(*data[:3], pitch_policy=data[5], search_result=search_result)

    def test_prepared_all_assignments_are_byte_equal_to_public_fresh_replay(self):
        data = self.fixture(); before = deepcopy(data); prepared = self.prepare(data)
        assignments = data[2]["stages"]["lattice"]["assignments"]
        records = []
        for assignment in assignments:
            aid = assignment["assignment_id"]
            changed = (*data[:4], aid, data[5])
            record = links.link_prepared(prepared, data[3], aid)
            self.assertEqual(links._encoded(record), links._encoded(self.call(changed)))
            self.validate(record, changed)
            links.validate_link_prepared(record, prepared, data[3], aid)
            records.append(record)
        self.assertEqual(data, before)
        self.assertEqual(len({r["harmony_assumption_track"]["record_sha256"] for r in records}), 1)
        self.assertGreater(len({digest(r["progression_evidence"]["accounting"]["note_time"]) for r in records}), 1)

    def test_prepared_context_guards_and_literal_once_track_role_once_per_proposal(self):
        data = self.fixture(); n = len(data[2]["stages"]["lattice"]["assignments"])
        with (patch.object(links, "_context_guards", wraps=links._context_guards) as guards,
              patch.object(links, "_validate_lattice", wraps=links._validate_lattice) as lattice_check,
              patch.object(links, "_validate_assignments", wraps=links._validate_assignments) as assignment_check,
              patch.object(links, "_validate_patterns", wraps=links._validate_patterns) as patterns,
              patch.object(links.role_module, "_geometry", wraps=links.role_module._geometry) as geometry,
              patch.object(links, "_proposal_guards", wraps=links._proposal_guards) as proposal_check,
              patch.object(links, "_verified_track", wraps=links._verified_track) as tracks,
              patch.object(links, "_verified_roles", wraps=links._verified_roles) as roles,
              patch.object(links, "vector", wraps=links.vector) as vectors):
            prepared = self.prepare(data)
            for assignment in data[2]["stages"]["lattice"]["assignments"]:
                record = links.link_prepared(prepared, data[3], assignment["assignment_id"])
                links.validate_link_prepared(record, prepared, data[3], assignment["assignment_id"])
        for called in (guards, lattice_check, assignment_check, patterns, geometry, proposal_check, tracks, roles):
            self.assertEqual(called.call_count, 1)
        self.assertEqual(vectors.call_count, 2 * n)

    def test_prepared_bound_search_also_preserves_full_origin_lineage(self):
        data = self.fixture(candidates=MEMBERS + [MEMBERS[0]])
        proposals = search(data[2], max_complete_paths=8, max_segments=2, per_state_limit=8)
        prepared = self.prepare(data, search_result=proposals)
        for proposal in proposals["proposals"]:
            changed = (*data[:3], proposal, *data[4:])
            record = links.link_prepared(prepared, proposal, data[4])
            self.assertEqual(links._encoded(record), links._encoded(self.call(changed, search_result=proposals)))
            self.validate(record, changed, search_result=proposals)

    def test_prepared_caller_snapshot_is_private_and_returned_records_do_not_poison_cache(self):
        data = self.fixture(); before = deepcopy(data); prepared = self.prepare(data)
        first = links.link_prepared(prepared, data[3], data[4]); saved = deepcopy(first)
        first["harmony_assumption_track"]["segments"][0]["members"].clear()
        first["role_evidence"]["literal"]["pitch_episodes"].clear()
        first["progression_evidence"]["accounting"]["items"].clear()
        first["candidate_origins"][0]["origins"].clear()
        data[0]["score"]["metadata"]["after_prepare"] = "caller-edit"
        data[1]["slots"].clear(); data[2]["stages"]["lattice"]["patterns"].clear()
        data[5]["harmonic_replay_allowed"] = False
        second = links.link_prepared(prepared, before[3], before[4])
        self.assertEqual(second, saved)
        self.validate(second, before)
        with self.assertRaisesRegex(ValueError, "seal_mismatch"):
            links.validate_link_prepared(first, prepared, before[3], before[4])

    def test_prepared_same_proposal_id_changed_meaning_is_not_a_cache_key(self):
        data = self.fixture(); prepared = self.prepare(data)
        other = deepcopy(data[3]); other["path"][0]["reading"] = 1
        with patch.object(links, "_verified_roles", wraps=links._verified_roles) as roles:
            first = links.link_prepared(prepared, data[3], data[4])
            second = links.link_prepared(prepared, other, data[4])
            again = links.link_prepared(prepared, data[3], data[4])
        self.assertEqual(roles.call_count, 2)
        self.assertEqual(first, again)
        self.assertNotEqual(first["raw_note_time"], second["raw_note_time"])
        self.assertEqual(second, self.call((*data[:3], other, *data[4:])))

    def test_prepared_wrong_assignment_or_foreign_context_record_cannot_be_reused(self):
        first_data = self.fixture(); first_context = self.prepare(first_data)
        first = links.link_prepared(first_context, first_data[3], first_data[4])
        with self.assertRaisesRegex(ValueError, "unknown_or_duplicate_shared_assignment"):
            links.link_prepared(first_context, first_data[3], "unstored-assignment")
        second_data = self.fixture([[event("G4", 0, 4)]]); second_context = self.prepare(second_data)
        with self.assertRaisesRegex(ValueError, "replay_mismatch"):
            links.validate_link_prepared(first, second_context, second_data[3], second_data[4])

    def test_prepared_factory_still_rejects_pitch_geometry_lane_and_search_blockers(self):
        original = self.fixture()
        for target in ("pitch", "cells", "tracks", "patterns", "lane"):
            data = deepcopy(original)
            if target == "pitch": data[5]["source_sha256"] = "f" * 64
            elif target == "cells": data[2]["stages"]["lattice"]["cells"][0]["event_refs"].clear()
            elif target == "tracks": data[2]["stages"]["lattice"]["assignments"][0]["tracks"].clear()
            elif target == "patterns": data[2]["stages"]["lattice"]["patterns"][0]["kind"] = "invented"
            else: del data[2]["sample"]["lane"]
            with self.subTest(target=target), self.assertRaises(ValueError): self.prepare(data)
        proposals = search(original[2]); proposals["input_bundle_content_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "search_bundle_binding_mismatch"):
            self.prepare(original, search_result=proposals)

    def test_prepared_selected_path_validation_is_not_skipped(self):
        data = self.fixture(); prepared = self.prepare(data)
        bad = deepcopy(data[3]); bad["path"][0]["reading"] = False
        with self.assertRaisesRegex(ValueError, "invalid_choice"): links.link_prepared(prepared, bad, data[4])
        bad = deepcopy(data[3]); bad["selected"] = "winner"
        with self.assertRaisesRegex(ValueError, "selected_proposal_forbidden"): links.link_prepared(prepared, bad, data[4])
        tampered = deepcopy(data); choice = tampered[3]["path"][0]
        reading = tampered[2]["stages"]["lattice"]["edges"][choice["edge"]]["readings"][0]
        sid = next(sid for sid, state in reading["event_states"].items() if state != "member")
        reading["event_states"][sid] = "member"
        other = self.prepare(tampered)
        with self.assertRaisesRegex(ValueError, "selected_reading_raw_membership_mismatch"):
            links.link_prepared(other, tampered[3], tampered[4])

    def test_prepared_fake_handles_skip_flags_and_null_group_refs_fail_closed(self):
        data = self.fixture()
        for forged in ({"validated": True, "bundle_hash": digest(data[2])}, links.PreparedContext(), object()):
            with self.subTest(forged=type(forged)), self.assertRaisesRegex(ValueError, "unregistered_internal"):
                links.link_prepared(forged, data[3], data[4])
        bad = deepcopy(data[3]); bad["semantic_group_refs"] = None
        with self.assertRaisesRegex(ValueError, "invalid_explicit_semantic_group_refs"):
            links.link_prepared(self.prepare(data), bad, data[4])

    def test_prepared_internal_bytes_or_rehashed_cache_contamination_is_detected(self):
        data = self.fixture(); prepared = self.prepare(data)
        record = links.link_prepared(prepared, data[3], data[4])
        state = links._PREPARED_CONTEXTS[prepared]
        changed = json.loads(state.context.body); changed["geometry"]["pitch_episodes"].clear()
        body = links._encoded(changed)
        # Caller recomputing a public checksum still cannot manufacture a
        # privately authenticated previously validated context/cache entry.
        forged = replace(state.context, body=body, sha256=sha256(body).hexdigest())
        links._PREPARED_CONTEXTS[prepared] = replace(state, context=forged)
        with self.assertRaisesRegex(ValueError, "prepared_context_"):
            links.link_prepared(prepared, data[3], data[4])
        links._PREPARED_CONTEXTS[prepared] = state
        key = digest(data[3]); old = state.proposals[key]
        changed = json.loads(old.body); changed["roles"]["semantics"]["roles_validated"] = True
        body = links._encoded(changed)
        state.proposals[key] = replace(old, body=body, sha256=sha256(body).hexdigest())
        with self.assertRaisesRegex(ValueError, "internal_content_mutation"):
            links.validate_link_prepared(record, prepared, data[3], data[4])

    def test_prepared_registry_state_cannot_be_swapped_from_another_handle(self):
        data = self.fixture(); left, right = self.prepare(data), self.prepare(data)
        links._PREPARED_CONTEXTS[left] = links._PREPARED_CONTEXTS[right]
        with self.assertRaisesRegex(ValueError, "prepared_context_contract_changed"):
            links.link_prepared(left, data[3], data[4])

    def test_prepared_actual_schema_bytes_change_invalidates_contract(self):
        data = self.fixture(); prepared = self.prepare(data)
        schema = links.role_module.SCHEMA_PATH
        path_type = type(schema)
        original = path_type.read_bytes
        def changed(path):
            payload = original(path)
            return payload + b"\n" if path == schema else payload
        with patch.object(path_type, "read_bytes", changed):
            with self.assertRaisesRegex(ValueError, "prepared_context_contract_changed"):
                links.link_prepared(prepared, data[3], data[4])

    def test_prepared_cache_has_weak_lifecycle_and_no_global_strong_snapshots(self):
        data = self.fixture(); prepared = self.prepare(data)
        links.link_prepared(prepared, data[3], data[4])
        reference = weakref.ref(prepared)
        before = len(links._PREPARED_CONTEXTS)
        del prepared; gc.collect()
        self.assertIsNone(reference())
        self.assertEqual(len(links._PREPARED_CONTEXTS), before - 1)

    def test_prepared_resealed_role_or_nct_promotion_is_not_accepted(self):
        data = self.fixture(); prepared = self.prepare(data)
        record = links.link_prepared(prepared, data[3], data[4])
        changed = deepcopy(record); changed["semantics"]["roles_validated"] = True; reseal(changed)
        with self.assertRaisesRegex(ValueError, "replay_mismatch"):
            links.validate_link_prepared(changed, prepared, data[3], data[4])
        changed = deepcopy(record)
        changed["progression_evidence"]["accounting"]["note_time"]["conditional_nonmember"] = q(0)
        reseal(changed)
        with self.assertRaisesRegex(ValueError, "replay_mismatch"):
            links.validate_link_prepared(changed, prepared, data[3], data[4])


if __name__ == "__main__":
    unittest.main()
