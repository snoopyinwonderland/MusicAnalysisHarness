"""Independent intake-accounting regressions, not music-quality tests."""

import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.musical_semantic_intake_audit import audit, _lines
from musicanote_harness.musical_semantic_intake_trial import run
from musicanote_harness.musical_semantic_enrichment import build_source_claim


class MusicalSemanticIntakeAuditTests(unittest.TestCase):
    def refresh_manifest(self, folder, path):
        report_path = folder / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["artifact_hashes"][str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        report_path.write_text(json.dumps(report), encoding="utf-8")

    def trial(self, directory):
        root = Path(directory) / "corpus"
        root.mkdir()
        (root / "analysis.txt").write_bytes(
            "\ufeffnote: rhythm\u2028not a physical line\r\nm1 I\rForm: opening\nPedal: C m1 m2\n".encode("utf-8"))
        folder = Path(directory) / "trial"
        run(root, folder)
        return folder

    def test_physical_lines_preserve_unicode_separator_and_line_endings(self):
        self.assertEqual(_lines("a\u2028b\r\nc\rd\n".encode("utf-8")),
                         [("a\u2028b", "\r\n"), ("c", "\r"), ("d", "\n")])

    def test_independent_audit_accepts_mixed_native_case_and_exact_snapshots(self):
        with TemporaryDirectory() as directory:
            folder = self.trial(directory)
            result = audit(folder)
            self.assertTrue(result["passed"])
            self.assertEqual(result["source_statements"], 3)
            self.assertEqual(result["noncanonical_source_tag_spellings_preserved"], 1)
            self.assertEqual(result["byte_identical_snapshots"], 1)
            self.assertFalse(result["musical_accuracy_measured"])

    def test_original_source_mutation_fails_audit(self):
        with TemporaryDirectory() as directory:
            folder = self.trial(directory)
            (Path(directory) / "corpus" / "analysis.txt").write_text("Note: changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source_input_hashes"):
                audit(folder)

    def test_false_summary_fails_even_if_record_artifacts_unchanged(self):
        with TemporaryDirectory() as directory:
            folder = self.trial(directory)
            report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
            report["summary"]["source_statements"] += 1
            (folder / "report.json").write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "total_statement_count"):
                audit(folder)

    def test_resealed_stale_producer_fails_independent_plan_comparison(self):
        with TemporaryDirectory() as directory:
            folder = self.trial(directory)
            path = folder / "source-statements.jsonl"
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
            old = records[0]
            provenance = old["provenance"]
            provenance["producer"]["version"] = "stale-producer-version"
            records[0] = build_source_claim(case_id=old["case_id"], source_context=old["source_context"],
                axis=old["claim"]["axis"], provenance=provenance, human_review=old["human_review"])
            path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
            self.refresh_manifest(folder, path)
            with self.assertRaisesRegex(ValueError, "source_producer_version_or_config"):
                audit(folder)

    def test_missing_artifact_hash_entry_is_not_complete_inventory(self):
        with TemporaryDirectory() as directory:
            folder = self.trial(directory)
            report_path = folder / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["artifact_hashes"].pop(str((folder / "source-inventory.json").resolve()))
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact_hash_inventory"):
                audit(folder)

    def test_duplicate_snapshot_mapping_cannot_collapse_to_a_valid_dictionary(self):
        with TemporaryDirectory() as directory:
            folder = self.trial(directory)
            path = folder / "provenance-snapshot.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["byte_identical_source_snapshots"].append(value["byte_identical_source_snapshots"][0])
            path.write_text(json.dumps(value), encoding="utf-8")
            self.refresh_manifest(folder, path)
            with self.assertRaisesRegex(ValueError, "snapshot_inventory_duplicates"):
                audit(folder)

    def test_resealed_context_omission_does_not_pass_original_line_accounting(self):
        with TemporaryDirectory() as directory:
            folder = self.trial(directory)
            path = folder / "source-statements.jsonl"
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
            old = records[0]
            context = old["source_context"]
            context["location"]["locator"]["context_lines"] = []
            records[0] = build_source_claim(case_id=old["case_id"], source_context=context,
                axis=old["claim"]["axis"], provenance=old["provenance"], human_review=old["human_review"])
            path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
            self.refresh_manifest(folder, path)
            with self.assertRaisesRegex(ValueError, "configured_context_omission"):
                audit(folder)


if __name__ == "__main__":
    unittest.main()
