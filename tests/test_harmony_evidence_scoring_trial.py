from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_evidence_scoring_trial import load_ir, run
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness.harmony_scored_decoder import decode, evaluation_path, prepare
from musicanote_harness.harmony_scored_decoder_trial import evaluate_selection, summarize
from test_harmony_evidence_scoring import fixture
from test_harmony_lattice_recall import C, D, cell, span


def setup(folder, reference=C):
    """Physical files, SYNTHETIC receipts/score; not independent corpus proof."""
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def write(name, value):
        p = folder/name; p.write_text(json.dumps(value), encoding="utf-8"); return p
    ir, bundle, search = fixture()
    ip = write("ir.json", ir); xml = folder/"source.musicxml"; xml.write_bytes(b"synthetic score bytes")
    entry = {"manifest_entry_id": "m", "score_sha256": sha(xml), "work_family_id": "family", "split": "dev",
             "rights": {"internal_research_use": True}, "eligibility": {"automatic_training": False}}
    sidecar = {"status": "not_required", "parent_content_sha256": _hash(ir),
               "verification_payload": {"parent_snapshot": {"parent_ir": str(ip), "parent_ir_sha256": sha(ip), "source_xml": str(xml)}}}
    sp = write("sidecar.json", sidecar)
    provenance = {"manifest_entry": entry, "measure_revision_sidecar": str(sp), "measure_revision_status": "not_required", "working_ir_document_id": "ir"}
    integration = {"complete": True, "source_labels_used": False, "measure_revisions": [
        {"pair_id": "pair", "sidecar": str(sp), "status": "not_required", "parent_ir_document_id": "ir", "working_ir_document_id": "ir", "candidate_created": False, "candidate_ir": None}],
        "artifact_hashes": {str(sp): sha(sp)}}
    integration_path = write("integration.json", integration)
    search["input_bundle_content_sha256"] = _hash(bundle)
    context = folder/"context.json.gz"; packet = folder/"search.json.gz"
    context.write_bytes(gzip.compress(json.dumps({"pair_id": "pair", "plan_index": 0, "provenance": provenance, "bundle": bundle}).encode()))
    packet.write_bytes(gzip.compress(json.dumps({"pair_id": "pair", "plan_index": 0, "provenance": provenance, "sample": bundle["sample"], "search": search, "input_bundle_content_sha256": _hash(bundle)}).encode()))
    identity = {"pair_id": "pair", "plan_index": 0, "sample_id": "sample", "work_family_id": "family", "split": "dev", "sample_span": span(0, 2)}
    evaluation = evaluate_selection(evaluation_path(decode(prepare(bundle, search))), [cell(sig=reference)])
    evals = {"direct_joint_music": evaluation}
    recall = write("recall.json", {"complete": True, "package_manifest": [entry], "records": [identity | {"reference_cells": [{"span": span(0, 2), "signature": reference}]}]})
    baseline = write("baseline.json", {"complete": True, "records": [identity | {"evaluations": evals, "selected_prediction": decode(prepare(bundle, search))["selected"]}], "input_hashes": {}, "code_hashes": {}})
    row = identity | {"evaluations": evals, "source_context_artifact": str(context), "source_context_sha256": sha(context), "search_artifact": str(packet), "search_artifact_sha256": sha(packet), "lattice_hit": reference == C, "lattice_diagnosis": "synthetic"}
    margin = write("margin.json", {"complete": True, "source_labels_used_at_inference": False, "development_labels_used_for_updates_or_checkpoint_selection": False,
                   "input_hashes": {}, "code_hashes": {}, "records": [row], "summary": {"direct_joint_music": summarize([row], "direct_joint_music")}, "metric_scope": "synthetic"})
    paths = recall, baseline, margin, integration_path
    pins = dict(zip(("expected_recall_sha", "expected_baseline_sha", "expected_margin_sha", "expected_integration_sha"), map(sha, paths)))
    return paths, pins, ip, integration, entry, provenance, bundle


class EvidenceTrialTests(unittest.TestCase):
    def test_physical_runner_and_old_files_unchanged(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip, *_ = setup(folder)
            before = ip.read_bytes()
            result = run(*paths, folder/"out", **pins)
            self.assertEqual(result["summary"]["source_evidence_music"]["selected_correct_contexts"], 1)
            self.assertFalse(result["training_performed"]); self.assertFalse(result["production_modified"])
            self.assertEqual(before, ip.read_bytes()); self.assertEqual(len(list((folder/"out").iterdir())), 3)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(*paths, folder/"out", **pins)

    def test_parent_ir_physical_change_rejected(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip, *_ = setup(folder); ip.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "input_sha_mismatch"):
                run(*paths, folder/"out", **pins)
            self.assertFalse((folder/"out").exists())

    def test_reference_does_not_enter_inference(self):
        results = []
        with TemporaryDirectory() as temp:
            for name, ref in (("a", C), ("b", D)):
                folder = Path(temp)/name; folder.mkdir(); paths, pins, *_ = setup(folder, ref)
                results.append(run(*paths, folder/"out", **pins))
        self.assertEqual(results[0]["records"][0]["selected_predictions"], results[1]["records"][0]["selected_predictions"])
        self.assertNotEqual(results[0]["summary"], results[1]["summary"])

    def test_revision_working_hash_and_identity_must_match(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip, integ, entry, provenance, bundle = setup(folder)
            bundle["input_ir_content_sha256"] = "wrong"
            def read(p, sha, raw=False):
                return None if raw else json.loads(Path(p).read_bytes())
            with self.assertRaisesRegex(ValueError, "working_ir_bundle_binding"):
                load_ir(dict(entry, pair_id="pair"), provenance, bundle, integ, read)

    def test_duplicate_revision_is_rejected(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip, integ, entry, provenance, bundle = setup(folder)
            integ["measure_revisions"] *= 2
            with self.assertRaisesRegex(ValueError, "duplicate_ir_revision"):
                load_ir(dict(entry, pair_id="pair"), provenance, bundle, integ, lambda *a, **k: None)

    def test_source_xml_physical_change_rejected(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, *_ = setup(folder)
            (folder/"source.musicxml").write_bytes(b"changed score")
            with self.assertRaisesRegex(ValueError, "input_sha_mismatch"):
                run(*paths, folder/"out", **pins)
            self.assertFalse((folder/"out").exists())
