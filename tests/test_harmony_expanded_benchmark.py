from copy import deepcopy
from fractions import Fraction
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from musicanote_harness import harmony_expanded_benchmark as trial
from musicanote_harness.formal_ir import q
from test_harmony_open_candidates import score


def entry(pair="dcml:collection:work-1"):
    return {"pair_id": pair, "work_family_id": "family", "score_sha256": "a"*64,
            "annotation_sha256": "b"*64, "annotation_lineage_id": "lineage",
            "known_overlap_fields": [], "historical_exposure": False,
            "status": "metadata_candidate_exposure_unknown"}


def schedule(e):
    return {"schedule": [{"work_family_id": e["work_family_id"], "metadata_complete_packages": [e]}]}


def gates():
    return ({"note_events": []}, {"status": "complete_replay"},
            {"status": "complete_parent_event_mapping", "counts": {}, "events": []},
            {"harmonic_replay_allowed": True})


class ExpandedBenchmarkTests(unittest.TestCase):
    def test_protected_holdout_not_overridden(self):
        e = entry(); old = dict(e, split="holdout", rights={"internal_research_use": True})
        selected, excluded = trial.execution_schedule(schedule(e), {"entries": [old]}, {"package_manifest": []})
        self.assertEqual(selected, [])
        self.assertIn("original_holdout_protected", excluded[0]["blockers"])
        self.assertEqual(old["split"], "holdout")

    def test_alias_holdout_also_excluded(self):
        e = entry(); old = dict(e, work_family_id="alias", split="holdout", rights={"internal_research_use": True})
        self.assertFalse(trial.execution_schedule(schedule(e), {"entries": [old]}, {"package_manifest": []})[0])

    def test_exposed_family_is_not_new(self):
        e = entry()
        selected, excluded = trial.execution_schedule(schedule(e), {"entries": []}, {"package_manifest": [dict(e)]})
        self.assertFalse(selected); self.assertIn("known_development_overlap", excluded[0]["blockers"])

    def test_unknown_history_is_development_not_permission_grant(self):
        e = entry()
        selected, excluded = trial.execution_schedule(schedule(e), {"entries": []}, {"package_manifest": []})
        self.assertFalse(excluded)
        self.assertFalse(selected[0]["blind_test_approved"]); self.assertFalse(selected[0]["training_approved"])

    def test_bad_staging_and_duplicates_rejected(self):
        e = entry(); p = schedule(e); p["schedule"][0]["metadata_complete_packages"].append(e)
        with self.assertRaisesRegex(ValueError, "duplicate"): trial.execution_schedule(p, {"entries": []}, {"package_manifest": []})
        e["historical_exposure"] = True
        with self.assertRaisesRegex(ValueError, "invalid_staged"): trial.execution_schedule(schedule(e), {"entries": []}, {"package_manifest": []})

    def test_core_projection_removes_interpretations_without_mutation(self):
        parent = {"score": {"score_id": "s", "title": "I7", "metadata": {"key": "G"}},
                  "ir_document_id": "ir", "measures": [{"key_signature": {"fifths": 1, "mode_hint": "Gmajor"}}],
                  "note_events": [{"note_id": "n"}], "extensions": {"harmony": {"answer": "V7"}},
                  "annotations": ["V7/V"]}
        before = deepcopy(parent); ir = trial.observation_ir(parent)
        self.assertEqual(parent, before); self.assertEqual(ir["note_events"], parent["note_events"])
        self.assertEqual(ir["extensions"], {}); self.assertNotIn("annotations", ir)
        self.assertIsNone(ir["score"]["title"]); self.assertEqual(ir["score"]["metadata"], {})
        self.assertEqual(ir["measures"][0]["key_signature"], {"fifths": 1})

    def test_source_gate_retains_replay_failures(self):
        p, r, m, t = gates(); r["status"] = "partial_replay"
        self.assertIn("source_note_rest_replay_not_complete", trial.source_gate(p, r, m, t))

    def test_source_gate_does_not_guess_measure_revision(self):
        p, r, m, t = gates(); m["events"] = [{"resolved_sequential_measure_index": 3, "legacy_referenced_sequence_indices": [2]}]
        self.assertIn("physical_measure_membership_revision_required", trial.source_gate(p, r, m, t))
        m["counts"]["duplicate_measure_id_groups"] = 1
        self.assertIn("duplicate_measure_ids_revision_required", trial.source_gate(p, r, m, t))

    def test_transposition_remains_blocked(self):
        p, r, m, t = gates(); t["harmonic_replay_allowed"] = False
        self.assertIn("written_concert_transposition_unverified", trial.source_gate(p, r, m, t))

    def test_prediction_before_gold_phase_is_explicit(self):
        source = inspect.getsource(trial.run)
        self.assertLess(source.index('save(output/"prediction-freeze.json"'), source.index('annotations = read('))
        self.assertEqual(tuple(inspect.signature(trial.infer).parameters), ("ir", "sample"))

    def test_real_small_inference_and_original_ir_unchanged(self):
        ir = score([("C3", 0, 3, "bass"), ("E3", 0, 3, "inner"), ("G3", 0, 3, "inner2"),
                    ("C4", 0, 1, "lead"), ("D4", 1, 2, "lead"), ("E4", 2, 3, "lead")])
        ir["ir_document_id"] = "small"; ir["score"] = {"score_id": "s", "duration_quarters": q(3)}
        for n, s in zip(ir["note_events"], ir["sounding_events"]):
            n.update(concert_pitch=deepcopy(s["pitch"]), global_onset_quarter=s["span"]["start"],
                     notated_duration_quarter=q(trial.fraction(s["span"]["end"])-trial.fraction(s["span"]["start"])))
            s["attack_note_id"] = n["note_id"]
            s["sounding_duration"] = n["notated_duration_quarter"]
        sample = {"sample_id": "s1", "lane": ["part1", "lead"], "attack_group_onsets": [q(0), q(1), q(2)],
                  "seed_event_refs": [], "span": {"start": q(0), "end": q(3)}, "abstention_reasons": []}
        # Use the actual logical lane generated by the existing test builder.
        lead = next(n for n in ir["note_events"] if n["concert_pitch"]["midi_pitch"] == 60)
        sample["lane"] = [lead["part_id"], lead["voice_id"]]
        before = deepcopy(ir)
        chosen, proposed, expanded, receipts, _, _ = trial.infer(ir, sample)
        self.assertEqual(ir, before); self.assertIsNotNone(chosen["selected"])
        self.assertFalse(chosen["selected"]["source_labels_used_for_selection"])
        self.assertLessEqual(len(proposed["proposals"]), 24)
        C = (("C", 0), (("C", 0), ("E", 0), ("G", 0)))
        cells = [{"start": Fraction(0), "end": Fraction(3), "signature": C}]
        retained, ceiling = trial.candidate_diagnostic(proposed, expanded, cells, sample["span"])
        self.assertTrue(ceiling["lattice_hit"])

    def test_artifact_roundtrip_and_no_overwrite(self):
        import gzip, json
        with TemporaryDirectory() as temp:
            p = Path(temp)/"sample.json.gz"; value = {"span": {"start": q(1), "end": q(Fraction(4, 3))}}
            trial.write_packet(p, value)
            self.assertEqual(json.loads(gzip.decompress(p.read_bytes())), value)
            with self.assertRaisesRegex(ValueError, "output_exists"): trial.run("x", "y", "z", temp)

    def disk_run(self, root, *, broken=False, tamper=False):
        """Exercise the real disk phase ordering with mocked expensive engines."""
        import json
        folder = root/"pairs"/"collection"/"work-1"; folder.mkdir(parents=True)
        xml = root/"source.musicxml"; xml.write_text("<score-partwise/>", encoding="utf-8")
        harmony = root/"harmonies.tsv"; harmony.write_text("POISON_NOT_AN_INFERENCE_ARGUMENT", encoding="utf-8")
        prep = {"source_paths": {"score": str(xml), "harmonies": str(harmony)},
                "source_sha256": {"score": trial.digest(xml), "harmonies": trial.digest(harmony)},
                "score_id": "s", "ir_document_id": "ir"}
        prep_path = folder/"preparation_report.json"; trial.write(prep_path, prep)
        parent = {"ir_document_id": "ir", "score": {"score_id": "s"}, "note_events": [], "measures": [], "extensions": {"gold": "I"}}
        trial.write(folder/"canonical_music_ir.json", parent)
        annotation = {"annotation_id": "a", "source_asset_sha256": prep["source_sha256"]["harmonies"],
                      "target": {"score_id": "s"}}
        (folder/"imported_annotations.jsonl").write_text(json.dumps(annotation)+"\n", encoding="utf-8")
        (folder/"alignment_records.jsonl").write_text("{}\n", encoding="utf-8")
        e = dict(trial._package_identity(folder, folder.parents[1], prep), pair_id="dcml:collection:work-1",
                 preparation_report=str(prep_path), preparation_report_sha256=trial.digest(prep_path),
                 status="metadata_candidate_exposure_unknown", known_overlap_fields=[], historical_exposure=False)
        plan_path, manifest_path, exposed_path = (root/n for n in ("plan.json", "manifest.json", "exposed.json"))
        trial.write(plan_path, schedule(e)); trial.write(manifest_path, {"entries": []}); trial.write(exposed_path, {"package_manifest": []})
        span = {"start": q(0), "end": q(1)}; sample = {"sample_id": "sample", "span": span}
        frozen = {"selected_samples": [{"sample": sample, "plan_index": 0}]}
        cells = [{"start": Fraction(), "end": Fraction(1), "signature": (("C", 0), (("C", 0), ("E", 0), ("G", 0))),
                  "reason": None, "annotation_id": "a"}]
        output = root/"new-run"
        def inference(ir, s):
            self.assertEqual(ir["extensions"], {}); self.assertFalse((output/"prediction-freeze.json").exists())
            if tamper: xml.write_text("CHANGED", encoding="utf-8")
            if broken: raise ValueError("synthetic_engine_failure")
            return ({"status": "unavailable", "selected": None, "transitions": 0},
                    {"proposals": []}, Mock(edges=[]), [], {}, {})
        def references(*args):
            receipt = json.loads((output/"prediction-freeze.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["contexts"], 1); self.assertFalse(receipt["labels_read"])
            for path, sha in receipt["prediction_hashes"].items(): self.assertEqual(trial.digest(path), sha)
            return deepcopy(cells)
        with ExitStack() as stack:
            for name, value in (("PLAN_SHA", trial.digest(plan_path)), ("MANIFEST_SHA", trial.digest(manifest_path)),
                                ("EXPOSED_SHA", trial.digest(exposed_path))): stack.enter_context(patch.object(trial, name, value))
            stack.enter_context(patch.object(trial, "Draft202012Validator"))
            stack.enter_context(patch.object(trial, "freeze_score", return_value=frozen))
            stack.enter_context(patch.object(trial, "replay_audit", return_value={"status": "complete_replay", "raw_measures": [], "observations": [], "counts": {}}))
            stack.enter_context(patch.object(trial, "measure_audit", return_value={"status": "complete_parent_event_mapping", "counts": {}, "events": []}))
            stack.enter_context(patch.object(trial, "source_transposition", return_value={"harmonic_replay_allowed": True}))
            stack.enter_context(patch.object(trial, "infer", side_effect=inference))
            stack.enter_context(patch.object(trial, "reference_cells", side_effect=references))
            stack.enter_context(patch.object(trial, "candidate_diagnostic", return_value=({"candidate_hit": None}, {"lattice_hit": None})))
            return trial.run(plan_path, manifest_path, exposed_path, output)

    def test_real_phase_sealing_and_missing_prediction_denominator(self):
        with TemporaryDirectory() as temp:
            result = self.disk_run(Path(temp))
            self.assertEqual(result["table"]["contexts"], 1)
            self.assertEqual(result["table"]["components"]["root_members"]["eligible_time"], q(1))
            self.assertEqual(result["table"]["components"]["root_members"]["time_agreement"], 0)
            self.assertFalse(result["training_performed"]); self.assertFalse(result["independent_test_accuracy_measured"])

    def test_execution_error_remains_in_score_denominator(self):
        with TemporaryDirectory() as temp:
            result = self.disk_run(Path(temp), broken=True)
            self.assertEqual(result["status_counts"], {"execution_error": 1})
            self.assertEqual(result["table"]["abstained_contexts"], 1)
            self.assertEqual(result["table"]["components"]["root_members"]["eligible_time"], q(1))

    def test_physical_file_tampering_rejected(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "input_changed|frozen_inputs"):
                self.disk_run(Path(temp), tamper=True)


if __name__ == "__main__": unittest.main()
