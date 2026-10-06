from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_evidence_scoring_trial import run as evidence_run
from musicanote_harness.harmony_functional_scoring_trial import run as functional_run
from musicanote_harness.harmony_functional_learning_trial import ARM, run
from test_harmony_evidence_scoring_trial import setup
from test_harmony_structured_learning import contract


def prepared(folder):
    paths, _, ip, *_ = setup(folder)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    recall, base, margin, integration = paths
    # This is synthetic test data; assign its one family to TRAIN before any
    # parent experiment, not by overriding a real corpus split/permission.
    def train(value):
        if isinstance(value, list):
            return [train(v) for v in value]
        if isinstance(value, dict):
            return {k: "train" if k == "split" and v == "dev" else train(v) for k, v in value.items()}
        return value
    for p in (recall, base, margin):
        p.write_text(json.dumps(train(json.loads(p.read_text()))), encoding="utf-8")
    for p in (folder/"context.json.gz", folder/"search.json.gz"):
        p.write_bytes(gzip.compress(json.dumps(train(json.loads(gzip.decompress(p.read_bytes())))).encode()))
    body = json.loads(margin.read_text()); row = body["records"][0]
    row["source_context_sha256"] = digest(folder/"context.json.gz"); row["search_artifact_sha256"] = digest(folder/"search.json.gz")
    margin.write_text(json.dumps(body), encoding="utf-8")
    names = "expected_recall_sha", "expected_baseline_sha", "expected_margin_sha", "expected_integration_sha"
    evidence_run(*paths, folder/"evidence", **dict(zip(names, map(digest, paths))))
    ep = folder/"evidence/report.json"
    functional_run(ep, recall, integration, folder/"functional", expected_previous_sha=digest(ep),
                   expected_recall_sha=digest(recall), expected_integration_sha=digest(integration))
    c = contract(json.loads(recall.read_text())["package_manifest"]); c["parent_recall_sha256"] = digest(recall)
    lic, readme = folder/"LICENSE", folder/"README"
    lic.write_text("SYNTHETIC fixture license", encoding="utf-8"); readme.write_text("SYNTHETIC fixture attribution", encoding="utf-8")
    c["approved_entries"][0]["source_license"].update(local_license_path=str(lic), local_license_sha256=digest(lic),
                                                   readme_path=str(readme), readme_sha256=digest(readme))
    cp = folder/"contract.json"; cp.write_text(json.dumps(c), encoding="utf-8")
    new_paths = folder/"functional/report.json", recall, integration, cp
    new_names = "expected_previous_sha", "expected_recall_sha", "expected_integration_sha", "expected_contract_sha"
    return new_paths, dict(zip(new_names, map(digest, new_paths))), ip


class FunctionalLearningTrialTests(unittest.TestCase):
    def test_full_physical_runner_parent_preserved_and_no_overwrite(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip = prepared(folder); before = ip.read_bytes(); parent = paths[0].read_bytes()
            result = run(*paths, folder/"learned", **pins)
            self.assertEqual(result["reachable_complete_training_contexts"], 1)
            self.assertEqual(result["summary"][ARM]["selected_correct_contexts"], 1)
            self.assertFalse(result["candidate_inventory_changed_from_J2e"])
            self.assertFalse(result["development_labels_used_for_updates_or_checkpoint_selection"])
            self.assertEqual(ip.read_bytes(), before); self.assertEqual(paths[0].read_bytes(), parent)
            self.assertEqual(len(list((folder/"learned").iterdir())), 3)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(*paths, folder/"learned", **pins)

    def test_changed_source_and_licence_rejected_without_output(self):
        for name in ("ir.json", "LICENSE"):
            with TemporaryDirectory() as temp:
                folder = Path(temp); paths, pins, _ = prepared(folder); (folder/name).write_text("changed")
                with self.assertRaisesRegex(ValueError, "frozen_input_changed"):
                    run(*paths, folder/"learned", **pins)
                self.assertFalse((folder/"learned").exists())

    def test_inventory_receipt_tampering_rejected(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, _ = prepared(folder)
            body = json.loads(paths[0].read_text()); body["records"][0]["expanded_edge_count"] += 1
            paths[0].write_text(json.dumps(body)); pins["expected_previous_sha"] = hashlib.sha256(paths[0].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "inventory_changed"):
                run(*paths, folder/"learned", **pins)

    def test_pending_contract_rejected_before_loading_sources(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, ip = prepared(folder)
            c = json.loads(paths[3].read_text()); c["human_scope_confirmation"]["status"] = "pending"
            paths[3].write_text(json.dumps(c)); pins["expected_contract_sha"] = hashlib.sha256(paths[3].read_bytes()).hexdigest()
            ip.unlink()
            with self.assertRaisesRegex(ValueError, "scope_confirmation"):
                run(*paths, folder/"learned", **pins)

    def test_family_split_leakage_rejected_before_fit(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp); paths, pins, _ = prepared(folder)
            doc = json.loads(paths[1].read_text()); dev = deepcopy(doc["package_manifest"][0]); dev.update(manifest_entry_id="dev", split="dev")
            doc["package_manifest"].append(dev); paths[1].write_text(json.dumps(doc)); rs = hashlib.sha256(paths[1].read_bytes()).hexdigest()
            pins["expected_recall_sha"] = rs
            c = json.loads(paths[3].read_text()); c["parent_recall_sha256"] = rs; paths[3].write_text(json.dumps(c))
            pins["expected_contract_sha"] = hashlib.sha256(paths[3].read_bytes()).hexdigest()
            parent = json.loads(paths[0].read_text())
            parent["input_hashes"][str(paths[1].resolve())] = rs
            paths[0].write_text(json.dumps(parent)); pins["expected_previous_sha"] = hashlib.sha256(paths[0].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "family_split_leakage"):
                run(*paths, folder/"learned", **pins)


if __name__ == "__main__":
    unittest.main()
