"""Frozen parents are explicit; no SOURCE/alignment gate or legacy enumeration."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jsonschema.exceptions import ValidationError

from musicanote_harness import frozen_context_observation as frozen
from musicanote_harness import musical_pattern_observation as pattern
from musicanote_harness.harmony_breadth_trial import freeze_score
from musicanote_harness import source_physical_measure_revision as revision
from test_musical_pattern_observation import make_ir
from test_source_physical_measure_revision import package_for, split_xml
from test_source_sequence_replay_audit import make_parent, pitched


def fixture(parent, source_path, *, candidate=False, prefer_grace=False):
    """Real XML replay/revision, bookkeeping stored parents (not harmony)."""
    pair = "synthetic:frozen-context"
    entry = {"manifest_entry_id": "fixture_manifest", "score_id": parent["score"]["score_id"],
             "ir_document_id": parent["ir_document_id"], "score_sha256": parent["source_files"][0]["sha256"],
             "annotation_sha256": "e" * 64, "annotation_lineage_id": "fixture_annotation_lineage",
             "score_source_path": str(source_path), "work_family_id": "fixture_family",
             "split": "dev", "rights": {"internal_research_use": True}}
    proof = package_for(parent, source_path)
    proof["pair_id"] = pair
    proof["manifest_entry"] = deepcopy(entry)
    new, sidecar = revision.revise(parent, proof)
    if candidate:
        if new is None:
            raise AssertionError(sidecar)
        revision.validate_revision(parent, new, sidecar)
        ir = new
    else:
        if new is not None or sidecar["status"] != "not_required":
            raise AssertionError(sidecar)
        ir = parent
    plan = freeze_score(parent, per_lane=1)
    selected = plan["selected_samples"]
    if prefer_grace:
        sounds = {s["sounding_event_id"]: s for s in parent["sounding_events"]}
        chosen = next(r for r in selected if any(
            pattern.f(sounds[s]["span"]["start"]) == pattern.f(sounds[s]["span"]["end"])
            for s in r["sample"]["seed_event_refs"]))
    else:
        chosen = selected[0]
    pitch = {"harmonic_replay_allowed": True, "nonzero_source_transposition": False,
             "malformed_or_unsupported_transposition": False, "concert_pitch_normalization_verified": False}
    package = {"pair_id": pair, "source": {"pair_id": pair, "manifest_entry": entry,
               "source_files": {str(source_path): entry["score_sha256"], "fixture_annotation.txt": entry["annotation_sha256"]},
               "pitch_policy": pitch, "ir_sha256": "a" * 64}, "plan": plan}
    rr = {"pair_id": pair, "status": sidecar["status"], "parent_ir_document_id": parent["ir_document_id"],
          "working_ir_document_id": ir["ir_document_id"], "candidate_created": new is not None,
          "candidate_ir": "fixture_candidate_ir.json" if new is not None else None,
          "sidecar": "fixture_revision.json", "summary": deepcopy(sidecar.get("summary", sidecar.get("counts", {})))}
    sample = deepcopy(chosen["sample"])
    old = {"version": frozen.SELECTOR_VERSION, "sample": sample,
           "summary": {"status": "fixture_original_abstention", "source_labels_used": False, "accuracy_measured": False},
           "stages": {"frozen_sentinel": {"status": "fixture_original_abstention", "literal_label": "never interpreted"}},
           "selected": None, "production_modified": False}
    bundle = {"version": "harmony-context-bundle-0.1.0", "status": "fixture_assembled_not_verdict",
              "parent_ir_document_id": ir["ir_document_id"], "score_id": ir["score"]["score_id"],
              "input_ir_content_sha256": pattern.digest(ir), "input_sample_content_sha256": pattern.digest(old),
              "sample": deepcopy(sample), "stored_summary": deepcopy(old["summary"]),
              "stages": deepcopy(old["stages"]), "counts": {"retained_stages": 1}, "selected": None,
              "stage_statuses": {key: value["status"] for key, value in old["stages"].items()},
              **{name: False for name in ("ranking_performed", "confidence_generated", "harmonic_analysis_confirmed",
                 "source_labels_used", "production_modified", "annotation_retargeted", "gate_changed", "core_modified", "accuracy_measured")}}
    packet = {"version": "harmony-context-integration-trial-0.1.0", "pair_id": pair, "plan_index": chosen["plan_index"],
              "provenance": {"manifest_entry": deepcopy(entry), "pitch_policy": deepcopy(pitch),
                "historical_ir_document_id": parent["ir_document_id"], "working_ir_document_id": ir["ir_document_id"],
                "measure_revision_sidecar": rr["sidecar"], "measure_revision_status": sidecar["status"],
                "ir_use_scope": "note_rest_measure_core_only", "reused_stage_artifact": "fixture_original.json.gz",
                "reused_stage_sha256": "b" * 64,
                **{name: False for name in ("source_labels_used", "annotation_retargeted", "extensions_consumed",
                    "source_locator_revision_applied", "independent_source_occurrence_certified")}},
              "bundle": bundle, "selected": None, "musical_accuracy_measured": False, "production_modified": False}
    row = {"pair_id": pair, "plan_index": chosen["plan_index"], "sample_id": sample["sample_id"],
           "previous_status": old["summary"]["status"], "status": bundle["status"], "summary": deepcopy(bundle["counts"]),
           "working_ir_document_id": ir["ir_document_id"], "artifact": "fixture_integrated.json.gz", "sha256": "c" * 64}
    return ir, {"integration_index_row": row, "integration_packet": packet, "original_stored_packet": old,
                "frozen_plan_row": deepcopy(chosen), "package": package, "revision_row": rr,
                "revision_sidecar": sidecar, "parent_ir": parent}


def reseal(record):
    body = {k: v for k, v in record.items() if k not in ("record_id", "record_sha256")}
    record["record_sha256"] = pattern.digest(body)
    record["record_id"] = "mfco_" + record["record_sha256"][:24]
    return record


class FrozenContextObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        make_ir(cls.temp.name, grace=True)
        cls.source, cls.parent = make_parent(cls.temp.name,
            (Path(cls.temp.name) / "score.musicxml").read_text(encoding="utf-8"))
        cls.ir, cls.parents = fixture(cls.parent, cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.ir = deepcopy(self.__class__.ir)
        self.parents = deepcopy(self.__class__.parents)

    def observe(self):
        return frozen.observe(self.ir, **self.parents)

    def test_exact_new_identity_projection_and_immutable_inputs(self):
        before = pattern.digest([self.ir, self.parents])
        record = self.observe()
        self.assertTrue(frozen.validate_observation(record, ir=self.ir, scope=record["scope"], **self.parents))
        self.assertEqual(record, self.observe())
        self.assertEqual(pattern.digest([self.ir, self.parents]), before)
        self.assertTrue(record["record_id"].startswith("mfco_"))
        self.assertEqual(record["scope"]["target_span"], record["scope"]["context_span"])
        self.assertEqual(record["scope"]["target_span"], self.parents["frozen_plan_row"]["sample"]["span"])
        self.assertEqual(set(record["scope"]), frozen.SCOPE_KEYS)

    def test_sampled_lane_is_metadata_and_all_parts_rest_ties_preserved(self):
        record = self.observe()
        self.assertEqual({s["core_event"]["part_id"] for s in record["slots"]}, {p["part_id"] for p in self.ir["parts"]})
        self.assertEqual(len(record["raw_lanes"]), 2)
        expected = pattern._payload(self.ir, record["scope"])
        for key in ("slots", "raw_lanes", "core_projection"):
            self.assertEqual(record[key], expected[key])
        self.assertEqual(record["origin"]["sample"], self.parents["frozen_plan_row"]["sample"])
        self.assertTrue(record["origin"]["selector"]["sampled_lane_is_seed_metadata_only"])

    def test_grace_point_keeps_no_duration_and_exact_half_open_relation(self):
        ir, parents = fixture(self.ir, self.source, prefer_grace=True)
        record = frozen.observe(ir, **parents)
        grace = [s for s in record["slots"] if s["core_event"].get("grace", {}).get("is_grace")]
        self.assertEqual(len(grace), 1)
        self.assertEqual(grace[0]["target_relation"], "point_inside")
        self.assertIsNone(grace[0]["target_overlap"])
        self.assertEqual(record["scope"]["target_span"]["end"], pattern.q(8))
        self.assertFalse(any(s["core_event"]["global_onset_quarter"] == pattern.q(8)
                             and s["target_relation"] == "overlap" for s in record["slots"]))

    def test_label_independent_window_does_not_claim_annotation_free_cohort(self):
        record = self.observe()
        self.assertTrue(record["origin"]["selector"]["window_selection_label_independent"])
        self.assertFalse(record["origin"]["cohort_dependency"]["annotation_independent_cohort"])
        self.assertFalse(record["origin"]["source_statement_or_alignment_certified"])
        self.assertFalse(record["origin"]["source_file_bytes_checked_by_pure_function"])
        self.assertEqual(record["use_policy"], {"research_only": True, "training_eligible": False, "gold_status": "not_established"})
        self.assertFalse(record["semantics"]["generation_ready"])

    def test_parent_content_hashes_are_logical_not_gzip_or_file_hashes(self):
        record = self.observe()
        for name, value in self.parents.items():
            self.assertEqual(record["origin"]["parent_content_sha256"][name], pattern.digest(value))
        self.assertEqual(record["origin"]["artifact_references"]["integration_file_sha256"], "c" * 64)
        self.assertNotEqual(record["origin"]["parent_content_sha256"]["integration_packet"], "c" * 64)

    def test_resealed_scope_endpoint_mismatch_rejected(self):
        record = self.observe();record["scope"]["target_span"]["end"] = pattern.q(7)
        reseal(record)
        with self.assertRaisesRegex(ValueError, "scope_sample_mismatch"):
            frozen.validate_observation(record, ir=self.ir)

    def test_resealed_sample_or_plan_index_rejects_fresh_parent_validation(self):
        for key in ("plan_index", "lane_index"):
            with self.subTest(key=key):
                record = self.observe();record["origin"][key] += 1;reseal(record)
                with self.assertRaisesRegex(ValueError, "parent_origin_or_scope_mismatch"):
                    frozen.validate_observation(record, ir=self.ir, **self.parents)
        record = self.observe();record["origin"]["sample"]["seed_event_refs"].pop();reseal(record)
        with self.assertRaisesRegex(ValueError, "parent_origin_or_scope_mismatch"):
            frozen.validate_observation(record, ir=self.ir, **self.parents)

    def test_resealed_slot_lane_or_notation_loss_fails_ir_replay(self):
        for mode in ("slot", "lane", "duration"):
            with self.subTest(mode=mode):
                record = self.observe()
                if mode == "slot":record["slots"].pop()
                elif mode == "lane":record["raw_lanes"].pop()
                else:record["slots"][0]["core_event"]["notated_duration_quarter"] = pattern.q(1)
                reseal(record)
                with self.assertRaisesRegex(ValueError, "reconstruction_mismatch"):
                    frozen.validate_observation(record, ir=self.ir)

    def test_stale_parent_or_candidate_ir_never_selected_by_title(self):
        self.ir["score"]["title"] = "changed caller metadata"
        with self.assertRaisesRegex(ValueError, "parent_ir_swap_or_mutation"):
            self.observe()

    def test_index_sample_and_scope_mismatch_not_fixed_by_resealing(self):
        for mode in ("index", "packet", "stored", "row"):
            with self.subTest(mode=mode):
                parents = deepcopy(self.parents)
                if mode == "index":parents["integration_index_row"]["plan_index"] += 1
                elif mode == "packet":parents["integration_packet"]["bundle"]["sample"]["lane"].reverse()
                elif mode == "stored":parents["original_stored_packet"]["sample"]["span"]["end"] = pattern.q(7)
                else:parents["frozen_plan_row"]["lane_index"] += 1
                with self.assertRaises(ValueError):frozen.observe(self.ir, **parents)

    def test_mixed_or_fake_source_branch_and_old_schema_dispatch_rejected(self):
        record = self.observe()
        for mode in ("source_scope", "source_origin", "mixed"):
            with self.subTest(mode=mode):
                changed = deepcopy(record)
                if mode == "source_scope":changed["scope"]["source_statement_ref"] = {"record_id": "fake", "record_sha256": "a" * 64}
                elif mode == "source_origin":changed["origin"]["kind"] = "source_annotation"
                else:changed["origin"]["alignment_ref"] = {"record_id": "fake", "record_sha256": "a" * 64}
                reseal(changed)
                with self.assertRaises(ValidationError):frozen.validate_observation(changed)
        with self.assertRaises(ValidationError):pattern.validate_observation(record)

    def test_partial_parent_arguments_and_missing_ir_rejected(self):
        with self.assertRaisesRegex(ValueError, "all_explicit"):
            frozen.observe(self.ir, package=self.parents["package"])
        with self.assertRaisesRegex(ValueError, "all_explicit"):
            frozen.validate_observation(self.observe(), **self.parents)

    def test_stored_stage_omission_change_and_unapproved_labels_rejected(self):
        parents = deepcopy(self.parents)
        parents["integration_packet"]["bundle"]["stages"] = {}
        with self.assertRaisesRegex(ValueError, "stages_not_preserved"):
            frozen.observe(self.ir, **parents)
        parents = deepcopy(self.parents)
        parents["original_stored_packet"]["stages"]["frozen_sentinel"]["source_labels_used"] = True
        parents["integration_packet"]["bundle"]["stages"] = deepcopy(parents["original_stored_packet"]["stages"])
        parents["integration_packet"]["bundle"]["input_sample_content_sha256"] = pattern.digest(parents["original_stored_packet"])
        with self.assertRaisesRegex(ValueError, "not_label_blind"):
            frozen.observe(self.ir, **parents)

    def test_known_missing_evidence_addition_preserves_all_original_stages(self):
        parents = deepcopy(self.parents)
        parents["integration_packet"]["bundle"]["stages"]["missing_evidence"] = {
            "version": "missing-evidence-audit-0.1.0", "selected": None,
            "gate_changed": False, "accuracy_measured": False, "production_modified": False}
        parents["integration_packet"]["bundle"]["stage_statuses"]["missing_evidence"] = "no_stage_status"
        frozen.observe(self.ir, **parents)
        parents["integration_packet"]["bundle"]["stages"]["invented"] = {}
        with self.assertRaisesRegex(ValueError, "unknown_added_stage"):
            frozen.observe(self.ir, **parents)

    def test_added_missing_evidence_version_and_promotion_guard(self):
        for mode in ("version", "selected", "production"):
            with self.subTest(mode=mode):
                parents = deepcopy(self.parents)
                added = {"version": "missing-evidence-audit-0.1.0", "selected": None,
                         "gate_changed": False, "accuracy_measured": False, "production_modified": False}
                if mode == "version":added["version"] = "invented-provider"
                elif mode == "selected":added["selected"] = "winner"
                else:added["production_modified"] = True
                parents["integration_packet"]["bundle"]["stages"]["missing_evidence"] = added
                parents["integration_packet"]["bundle"]["stage_statuses"]["missing_evidence"] = "no_stage_status"
                with self.assertRaisesRegex(ValueError, "added_integration_stage"):
                    frozen.observe(self.ir, **parents)

    def test_split_rights_and_promotion_flags_do_not_inherit_readiness(self):
        for mode in ("split", "rights", "source", "verdict"):
            with self.subTest(mode=mode):
                parents = deepcopy(self.parents)
                if mode == "split":parents["package"]["source"]["manifest_entry"]["split"] = "holdout"
                elif mode == "rights":parents["package"]["source"]["manifest_entry"]["rights"]["internal_research_use"] = 1
                elif mode == "source":parents["integration_packet"]["provenance"]["source_labels_used"] = True
                else:parents["integration_packet"]["bundle"]["selected"] = {"winner": "invented"}
                with self.assertRaises(ValueError):frozen.observe(self.ir, **parents)

    def test_stage_status_inventory_cannot_be_resealed_as_different_counts(self):
        parents = deepcopy(self.parents)
        parents["integration_packet"]["bundle"]["stage_statuses"]["frozen_sentinel"] = "ready"
        with self.assertRaisesRegex(ValueError, "stage_status_inventory_mismatch"):
            frozen.observe(self.ir, **parents)

    def test_real_measure_revision_exact_selection_and_protected_content(self):
        with TemporaryDirectory() as tmp:
            xml = split_xml().replace("<backup><duration>1</duration>",
                pitched("A", "1") + pitched("B", "1") + "<backup><duration>3</duration>")
            source, parent = make_parent(tmp, xml)
            ir, parents = fixture(parent, source, candidate=True)
            record = frozen.observe(ir, **parents)
            self.assertEqual(record["origin"]["working_ir_selection"], "measure_core_candidate")
            self.assertNotEqual(record["scope"]["ir_document_id"], parent["ir_document_id"])
            frozen.validate_observation(record, ir=ir, **parents)
            with self.assertRaises(ValueError):frozen.observe(parent, **parents)
            wrong = deepcopy(ir);wrong["note_events"][0]["written_pitch"]["spelling"] = "changed"
            parents["revision_sidecar"]["candidate_content_sha256"] = pattern.digest(wrong)
            with self.assertRaisesRegex(ValueError, "protected_projection_changed"):
                frozen.observe(wrong, **parents)

    def test_tamper_and_reconstruct_return_independent_original_occurrences(self):
        record = self.observe();record["record_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "seal_mismatch"):
            frozen.validate_observation(record)
        record = self.observe();rows = frozen.reconstruct(record)
        self.assertEqual(rows, [s["core_event"] for s in record["slots"]])
        rows[0]["measure_id"] = "changed caller copy"
        self.assertNotEqual(rows[0], record["slots"][0]["core_event"])


if __name__ == "__main__":
    unittest.main()
