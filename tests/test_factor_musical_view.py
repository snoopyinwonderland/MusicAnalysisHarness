"""Literal view/path contracts; synthetic parents are not SOURCE admission."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from musicanote_harness import factor_musical_view as common
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness import frozen_context_observation as frozen
from musicanote_harness.sounding_lineage_audit import audit_sounding_lineage
from test_musical_role_evidence import event, make_ir


def span(start=0, end=4):
    return {"start": pattern.q(start), "end": pattern.q(end)}


def make_observation(ir, context):
    """Cheap literal mfco fixture, not a claim of real frozen-parent trust.

    This tests the common projection adapter, not cohort/selector admission.
    All origin metadata is explicit synthetic fixture data; no SOURCE record
    or source harmonic label exists. Production runners independently protect
    the real eight parent artifacts before supplying a frozen observation.
    """
    scope = {"score_id": ir["score"]["score_id"], "ir_document_id": ir["ir_document_id"],
             "ir_content_sha256": pattern.digest(ir), "source_files": deepcopy(ir["source_files"]),
             "target_span": deepcopy(context), "context_span": deepcopy(context)}
    body = pattern._payload(ir, scope)
    note = ir["note_events"][0] if ir["note_events"] else ir["rest_events"][0]
    start, end = pattern.span_bounds(context)
    sample = {"sample_id": "cont_" + "0" * 20, "lane": [note["part_id"], note["voice_id"]],
              "attack_group_onsets": [pattern.q(start + (end - start) * i / 3) for i in range(3)],
              "seed_event_refs": ["synthetic_fixture_seed"], "span": deepcopy(context), "abstention_reasons": []}
    body.update(schema_name=frozen.SCHEMA_NAME, schema_version=frozen.SCHEMA_VERSION, producer_version=frozen.VERSION)
    body["origin"] = {"kind": "frozen_context_window", "pair_id": "synthetic-fixture", "plan_index": 0, "lane_index": 0,
        "sample": sample, "target_policy": "full_frozen_context",
        "selector": {"version": frozen.SELECTOR_VERSION, "policy": frozen.SELECTOR_POLICY,
                     "window_selection_label_independent": True, "sampled_lane_is_seed_metadata_only": True, "all_parts_projected": True},
        "cohort_dependency": {"kind": "inherited_score_annotation_hash_pair_and_alignment_eligibility",
                              "annotation_independent_cohort": False, "manifest_entry_id": "synthetic-manifest",
                              "annotation_sha256": "a" * 64, "annotation_lineage_id": None,
                              "work_family_id": "synthetic-family", "split": "train"},
        "working_ir_selection": "historical_parent", "historical_ir_document_id": ir["ir_document_id"],
        "historical_ir_content_sha256": pattern.digest(ir),
        "parent_content_sha256": {name: "b" * 64 for name in frozen.PARENT_ARGUMENTS},
        "artifact_references": {"integration_artifact": "synthetic-integration", "integration_file_sha256": "c" * 64,
                                "original_stored_artifact": "synthetic-original", "original_stored_file_sha256": "d" * 64,
                                "revision_sidecar": "synthetic-revision", "historical_ir_file_sha256": "e" * 64},
        "parent_statuses": {"original": "fixture", "integration": "fixture", "measure_revision": "not_required"},
        "source_statement_or_alignment_certified": False, "source_file_bytes_checked_by_pure_function": False,
        "selector_and_revision_fresh_replay_required_by_runner": True, "annotation_or_parent_locator_retargeted": False}
    record = common.seal(body, "mfco_")
    frozen.validate_observation(record)
    return record


def make_view(ir, context):
    observation = make_observation(ir, context)
    ids = [s["sounding_event_id"] for s in observation["core_projection"]["sounding_events"]]
    audit = audit_sounding_lineage(ir, sound_ids=ids, context_span=context)
    return common.prepare(ir, observation, audit)


def provenance():
    return {"kind": "caller_hypothesis", "engine_version": "synthetic-test-v1",
            "source_document_sha256": None, "source_path": None,
            "pitch_basis": "written_IR_not_concert_certified", "status": "hypothesis_not_gold"}


def member(step, alter=0):
    return {"step": step, "alter": pattern.q(alter)}


def segment(identity="caller-c", start=0, end=4, *, members=None, root=None, status="usable", blockers=None):
    return {"segment_id": identity, "span": span(start, end), "root": root,
            "members": [member("C"), member("E"), member("G")] if members is None else members,
            "status": status, "blockers": [] if blockers is None else blockers}


def reseal(record, prefix=common.PREFIX):
    return common.seal({k: deepcopy(v) for k, v in record.items() if k not in ("record_id", "record_sha256")}, prefix)


class FactorMusicalViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ir = make_ir(self.temp.name, [[event("C4", 0, 1, tie_role="start"), event("C4", 1, 1, tie_role="stop"),
                                         event("E4", 2, 1), event("G4", 3, 1)], [event(None, 0, 4)]])
        self.observation = make_observation(self.ir, span())
        ids = [s["sounding_event_id"] for s in self.observation["core_projection"]["sounding_events"]]
        self.audit = audit_sounding_lineage(self.ir, sound_ids=ids, context_span=span())
        self.view = common.prepare(self.ir, self.observation, self.audit)

    def path(self, segments=None):
        return common.make_path(self.view, segments or [segment()], provenance())

    def test_exact_prepare_replay_and_immutability_and_all_false_policy(self):
        before = deepcopy((self.ir, self.observation, self.audit))
        self.assertTrue(common.validate_view(self.view))
        self.assertTrue(common.validate_view(self.view, ir=self.ir, observation=self.observation, audit=self.audit))
        self.assertEqual(common.prepare(self.ir, self.observation, self.audit), self.view)
        self.assertEqual((self.ir, self.observation, self.audit), before)
        self.assertEqual(self.view["binding"]["source_file_id"], self.ir["score"]["source_file_id"])
        self.assertEqual(self.view["observation_ref"], common.ref(self.observation))
        self.assertEqual(self.view["audit_ref"], common.ref(self.audit))
        self.assertEqual(len(self.view["raw_lanes"]), 2)
        self.assertTrue(all(value is False for value in self.view["use_policy"].values()))
        self.assertEqual(self.view["rest_snapshots"], self.ir["rest_events"])
        self.assertTrue(self.view["tie_chain_snapshots"])
        self.assertEqual(self.view["measure_snapshots"], self.ir["measures"])
        self.assertTrue(all(row["source_pitch_consistency_passed"] is True for row in self.view["sounds"]))

    def test_prepare_never_calls_full_Core_validator_per_context(self):
        actual = common.validate_observation
        def no_ir_validation(record, **kwargs):
            self.assertNotIn("ir", kwargs)
            return actual(record, **kwargs)
        with patch.object(pattern, "validate_core", side_effect=AssertionError("full Core forbidden")), patch.object(common, "validate_observation", side_effect=no_ir_validation):
            self.assertEqual(common.prepare(self.ir, self.observation, self.audit), self.view)

    def test_positive_content_cache_equals_uncached_validation_and_is_bounded(self):
        common._validate_intrinsic_cached.cache_clear()
        actual = common._payload
        with patch.object(common, "_payload", wraps=actual) as rebuild:
            self.assertTrue(common.validate_view(self.view))
            self.assertTrue(common.validate_view(deepcopy(self.view)))
            self.assertEqual(rebuild.call_count, 1)
            common._validate_intrinsic_cached.cache_clear()
            self.assertTrue(common.validate_view(self.view))
            self.assertEqual(rebuild.call_count, 2)
        self.assertEqual(common._validate_intrinsic_cached.cache_info().maxsize, 32)

    def test_positive_cache_never_waives_optional_fresh_original_replay(self):
        common.validate_view(self.view)
        actual = common.prepare
        with patch.object(common, "prepare", wraps=actual) as fresh:
            for _ in range(2):
                self.assertTrue(common.validate_view(self.view, ir=self.ir, observation=self.observation, audit=self.audit))
            self.assertEqual(fresh.call_count, 2)
            changed = deepcopy(self.ir)
            changed["note_events"][0]["notation"]["changed"] = True
            with self.assertRaisesRegex(ValueError, "IR_binding"):
                common.validate_view(self.view, ir=changed, observation=self.observation, audit=self.audit)
            self.assertEqual(fresh.call_count, 3)

    def test_positive_cache_keys_actual_serialized_content_not_claimed_seal(self):
        common.validate_view(self.view)
        changed = deepcopy(self.view)
        changed["sounds"][0]["source_clock_passed"] = False
        with self.assertRaisesRegex(ValueError, "record_seal"):
            common.validate_view(changed)
        with self.assertRaisesRegex(ValueError, "payload_reconstruction"):
            common.validate_view(reseal(changed))
        self.assertTrue(common.validate_view(self.view))

    def test_Core_schema_change_invalidates_positive_memo_and_literal_validators(self):
        original_bytes = common.CORE_SCHEMA_PATH.read_bytes()
        schema = json.loads(original_bytes)
        path = Path(self.temp.name) / "synthetic-core-schema.json"
        path.write_bytes(original_bytes)
        with patch.object(common, "CORE_SCHEMA_PATH", path):
            self.assertTrue(common.validate_view(self.view))
            schema["$defs"]["note"]["allOf"][1]["required"].append("missing_new_required_fixture_field")
            path.write_text(json.dumps(schema), encoding="utf-8")
            with self.assertRaises(ValidationError):
                common.validate_view(self.view)
            path.write_bytes(original_bytes)
            self.assertTrue(common.validate_view(self.view))

    def test_clipping_preserves_full_tie_geometry_and_exact_rationals(self):
        context = span(Fraction(1, 3), Fraction(5, 2))
        view = make_view(self.ir, context)
        tied = next(row for row in view["sounds"] if len(row["source_note_ids"]) == 2)
        self.assertEqual(tied["span"], span(0, 2))
        self.assertEqual(tied["observed_span"], span(Fraction(1, 3), 2))
        self.assertEqual(common.clipped(span(0, 1), span(1, 2)), None)
        self.assertEqual(common.clipped(span(Fraction(1, 3), Fraction(2, 3)), span(0, 1)), span(Fraction(1, 3), Fraction(2, 3)))

    def test_context_only_sound_preserved_without_active_extension(self):
        ir = make_ir(self.temp.name, [[event(["C4", "E4"], 0, 3), event(None, 3, 1)]])
        e = next(n for n in ir["note_events"] if n["written_pitch"]["step"] == "E")
        e["notated_duration_quarter"] = pattern.q(1)
        sound = next(s for s in ir["sounding_events"] if e["note_id"] in s["source_note_ids"])
        sound["span"]["end"] = pattern.q(1)
        sound["sounding_duration"] = pattern.q(1)
        view = make_view(ir, span(2, 3))
        self.assertEqual(len(view["linked_sound_snapshots"]), 2)
        self.assertEqual(len(view["sounds"]), 1)
        self.assertEqual(view["sounds"][0]["pitch"]["step"], "C")
        self.assertEqual(len(view["note_snapshots"]), 2)

    def test_grace_point_half_open_context_and_no_clock_promotion(self):
        ir = make_ir(self.temp.name, [[event("D4", 0, 1), event("E4", 1, 0, grace=True), event("F4", 1, 1), event(None, 2, 2)]])
        view = make_view(ir, span(1, 2))
        self.assertEqual(len(view["points"]), 1)
        point = view["points"][0]
        self.assertEqual(point["observed_span"], span(1, 1))
        self.assertFalse(point["source_clock_passed"])
        self.assertIn("grace_performed_timing_not_assessed", point["source_diagnostics"])
        previous = make_view(ir, span(0, 1))
        self.assertEqual(previous["points"], [])

    def test_clock_gap_outside_current_clip_still_blocks_active_sound(self):
        ir = make_ir(self.temp.name, [[event("C4", 0, 1, tie_role="start"), event("C4", 3, 1, tie_role="stop")]])
        view = make_view(ir, span(0, 1))
        self.assertEqual(view["sounds"][0]["observed_span"], span(0, 1))
        self.assertFalse(view["sounds"][0]["source_clock_passed"])
        self.assertIn("full_source_timeline_gap", view["sounds"][0]["source_diagnostics"])

    def test_pitch_mismatch_is_additive_not_a_clock_fix_and_resealed_guard_rejected(self):
        ir = deepcopy(self.ir)
        changed_sound = ir["sounding_events"][0]
        changed_sound["pitch"] = deepcopy(ir["note_events"][-1]["written_pitch"])
        if changed_sound.get("tie_chain_id"):
            next(t for t in ir["tie_chains"] if t["tie_chain_id"] == changed_sound["tie_chain_id"])["sounding_pitch"] = deepcopy(changed_sound["pitch"])
        view = make_view(ir, span())
        row = next(s for s in view["sounds"] if s["sound_id"] == changed_sound["sounding_event_id"])
        self.assertTrue(row["source_clock_passed"])
        self.assertFalse(row["source_pitch_consistency_passed"])
        self.assertEqual(row["pitch"], changed_sound["pitch"])
        self.assertIn("source_written_pitch_mismatch", row["source_diagnostics"])
        self.assertTrue(common.validate_view(view))
        forged = deepcopy(view)
        row = next(s for s in forged["sounds"] if s["sound_id"] == changed_sound["sounding_event_id"])
        row["source_pitch_consistency_passed"] = True
        row["source_diagnostics"].remove("source_written_pitch_mismatch")
        with self.assertRaisesRegex(ValueError, "payload_reconstruction"):
            common.validate_view(reseal(forged))

    def test_stale_IR_or_audit_or_foreign_observation_fails_closed(self):
        ir = deepcopy(self.ir)
        ir["note_events"][0]["notation"]["external_prose"] = "changed"
        with self.assertRaisesRegex(ValueError, "IR_binding"):
            common.prepare(ir, self.observation, self.audit)
        stale = deepcopy(self.audit)
        stale["source_clock_consistency_passed"] = False
        stale = reseal(stale, "msla_")
        with self.assertRaisesRegex(ValueError, "stale_foreign"):
            common.prepare(self.ir, self.observation, stale)
        with self.assertRaisesRegex(ValueError, "all_exact"):
            common.validate_view(self.view, ir=self.ir)

    def test_resealed_observation_omission_and_literal_tamper_rejected(self):
        for kind in ("slot", "sound", "attack", "tie", "measure"):
            observation = deepcopy(self.observation)
            if kind == "slot":
                observation["slots"].pop()
            else:
                collection = {"sound": "sounding_events", "attack": "attack_events", "tie": "tie_chains", "measure": "measures"}[kind]
                observation["core_projection"][collection].pop()
            observation = reseal(observation, "mfco_")
            with self.subTest(kind=kind), self.assertRaises((ValueError, ValidationError)):
                common.prepare(self.ir, observation, self.audit)

    def test_resealed_view_payload_flags_inventory_and_binding_are_not_authority(self):
        for kind in ("active", "clock", "note", "rest", "attack", "tie", "extra", "policy", "ref"):
            changed = deepcopy(self.view)
            if kind == "active": changed["sounds"].pop()
            elif kind == "clock": changed["sounds"][0]["source_clock_passed"] = False
            elif kind in ("note", "rest", "attack", "tie"):
                changed[{"note": "note_snapshots", "rest": "rest_snapshots", "attack": "attack_snapshots", "tie": "tie_chain_snapshots"}[kind]].pop()
            elif kind == "extra": changed["confidence"] = 1
            elif kind == "policy": changed["use_policy"]["training_eligible"] = True
            else: changed["observation_ref"]["record_id"] = "SOURCE_not_a_view"
            changed = reseal(changed)
            with self.subTest(kind=kind), self.assertRaises((ValueError, ValidationError)):
                common.validate_view(changed)

    def test_changed_literal_note_and_source_snapshots_require_fresh_original_replay(self):
        changed = deepcopy(self.view)
        changed["note_snapshots"][0]["notation"]["prose"] = "changed snapshot"
        changed = reseal(changed)
        self.assertTrue(common.validate_view(changed))
        with self.assertRaisesRegex(ValueError, "exact_replay"):
            common.validate_view(changed, ir=self.ir, observation=self.observation, audit=self.audit)

    def test_duplicate_ids_missing_source_and_mixed_lane_ownership_fail_closed(self):
        for kind in ("duplicate", "missing_source", "mixed_owner"):
            changed = deepcopy(self.view)
            if kind == "duplicate": changed["note_snapshots"].append(deepcopy(changed["note_snapshots"][0]))
            elif kind == "missing_source": changed["source_reference_snapshots"].pop()
            else:
                chained = next(s for s in changed["linked_sound_snapshots"] if len(s["source_note_ids"]) == 2)
                next(n for n in changed["note_snapshots"] if n["note_id"] == chained["source_note_ids"][1])["voice_id"] = "voice_synthetic_other"
            with self.subTest(kind=kind), self.assertRaises((ValueError, ValidationError)):
                common.validate_view(reseal(changed))

    def test_seals_are_deepcopied_and_namespaced_no_hidden_SOURCE(self):
        body = {"nested": {"unchanged": [1]}}
        record = common.seal(body, "fixture_")
        body["nested"]["unchanged"].append(2)
        self.assertEqual(common.check(record, "fixture_"), {"nested": {"unchanged": [1]}})
        with self.assertRaises(ValueError): common.check(record, "SOURCE_")
        with self.assertRaises(ValueError): common.seal(record, "fixture_")
        forged = deepcopy(self.view);forged["record_id"] = "SOURCE_" + forged["record_sha256"][:24]
        with self.assertRaises(ValueError): common.validate_view(forged)

    def test_path_is_explicit_complete_caller_hypothesis_and_immutable(self):
        segments, origin = [segment(root=member("C"))], provenance()
        before = deepcopy((self.view, segments, origin))
        path = common.make_path(self.view, segments, origin)
        self.assertTrue(common.validate_path(self.view, path))
        self.assertEqual((self.view, segments, origin), before)
        self.assertEqual(path["view_ref"], common.ref(self.view))
        self.assertEqual(path["binding"], self.view["binding"])
        self.assertEqual(path["segments"], segments)
        self.assertTrue(all(value is False for value in path["use_policy"].values()))

    def test_path_null_root_is_retained_never_defaulted_from_members(self):
        path = self.path()
        self.assertIsNone(path["segments"][0]["root"])
        self.assertEqual(common.membership(path, member("C"), span()), "member")

    def test_path_partition_gaps_overlaps_order_endpoints_and_duplicate_ids_rejected(self):
        variants = [[], [segment(end=3)], [segment(start=1)],
                    [segment("a", 0, 1), segment("b", 2, 4)],
                    [segment("a", 0, 3), segment("b", 2, 4)],
                    [segment("a", 2, 4), segment("b", 0, 2)],
                    [segment("a", 0, 2), segment("a", 2, 4)], [segment(start=0,end=0)]]
        for segments in variants:
            with self.subTest(segments=segments), self.assertRaises(ValueError):
                common.make_path(self.view, segments, provenance())

    def test_path_blocked_unknown_and_uniform_membership_across_segments(self):
        segments = [segment("a", 0, 2), segment("b", 2, 4, members=[member("D"), member("F"), member("A")])]
        path = self.path(segments)
        self.assertEqual(common.membership(path, member("C"), span(0, 2)), "member")
        self.assertEqual(common.membership(path, member("C"), span(2, 4)), "nonmember")
        self.assertEqual(common.membership(path, member("C"), span()), "unknown")
        self.assertEqual(common.membership(path, member("B"), span()), "nonmember")
        self.assertEqual(common.membership(path, member("C"), span(0, 5)), "unknown")
        blocked = self.path([segment("a", 0, 2), segment("b", 2, 4, members=[], status="blocked", blockers=["caller_missing_members"])])
        self.assertEqual(common.membership(blocked, member("C"), span()), "unknown")
        self.assertEqual(common.membership(blocked, member("C"), span(0, 2)), "member")

    def test_exact_enharmonic_octave_microtone_and_triplet_boundaries(self):
        microtone = member("C", Fraction(1, 2))
        path = self.path([segment("a", 0, Fraction(1, 3), members=[microtone]),
                          segment("b", Fraction(1, 3), 4, members=[member("D", -1)])])
        self.assertEqual(common.membership(path, microtone, span(0, Fraction(1, 3))), "member")
        self.assertEqual(common.membership(path, member("C", 1), span(Fraction(1, 3), 4)), "nonmember")
        self.assertEqual(common.membership(path, member("D", -1), span(Fraction(1, 3), 4)), "member")
        self.assertEqual(common.segment_at(path, pattern.q(Fraction(1, 3)))["segment_id"], "b")
        self.assertEqual(common.segment_at(path, Fraction(0))["segment_id"], "a")
        self.assertIsNone(common.segment_at(path, 4))
        with self.assertRaises(ValueError): common.segment_at(path, 1.0)
        self.assertNotEqual(common.pitch_key({**member("C"), "octave": 3}, octave=True),
                            common.pitch_key({**member("C"), "octave": 4}, octave=True))
        self.assertNotEqual(common.pitch_key(member("C",1)), common.pitch_key(member("D",-1)))

    def test_no_SOURCE_provenance_confidence_defaults_or_extra_path_fields(self):
        for kind in ("source", "locator", "missing_root", "confidence", "selected", "empty_members", "blocked_without_reason", "usable_with_blocker", "duplicate_member"):
            segments, origin = [segment()], provenance()
            if kind == "source": origin["kind"] = "source_annotation"
            elif kind == "locator": origin["source_path"] = "source-analysis.txt"
            elif kind == "missing_root": segments[0].pop("root")
            elif kind in ("confidence", "selected"): segments[0][kind] = 1
            elif kind == "empty_members": segments[0]["members"] = []
            elif kind == "blocked_without_reason": segments[0]["status"] = "blocked"
            elif kind == "usable_with_blocker": segments[0]["blockers"] = ["unknown"]
            else: segments[0]["members"].append(member("C"))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                common.make_path(self.view, segments, origin)

    def test_resealed_foreign_view_and_path_binding_and_promotion_rejected(self):
        original = self.path()
        for kind in ("view", "IR", "policy", "extra"):
            path = deepcopy(original)
            if kind == "view": path["view_ref"] = {"record_id": "fmview_" + "0" * 24, "record_sha256": "0" * 64}
            elif kind == "IR": path["binding"]["ir_content_sha256"] = "0" * 64
            elif kind == "policy": path["use_policy"]["gold_eligible"] = True
            else: path["selected"] = "synthetic"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                common.validate_path(self.view, reseal(path, common.PATH_PREFIX))

    def test_strict_rational_contracts_reject_bool_float_bad_denominator(self):
        for invalid in ({"numerator": True,"denominator":1}, {"numerator":1.0,"denominator":1},
                        {"numerator":1,"denominator":0}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                common.pitch_key({"step":"C","alter":invalid})
        for step in ("AB", "H", None):
            with self.assertRaises(ValueError): common.pitch_key({"step":step,"alter":pattern.q(0)})
        with self.assertRaises(ValueError): common.membership(self.path(), member("C"), span(1,1))


if __name__ == "__main__":
    unittest.main()
