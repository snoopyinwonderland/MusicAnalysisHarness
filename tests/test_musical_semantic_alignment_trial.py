from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import musical_semantic_alignment_trial as trial
from musicanote_harness.musical_semantic_intake import prepare_source_statements
from test_musical_pattern_observation import make_ir


class MusicalSemanticAlignmentTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(dir=trial.ROOT / "output")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        source = self.corpus / "paired"
        source.mkdir()
        make_ir(source)
        (source / "analysis.txt").write_text("Time Signature: 4/4\nPedal: C m1 b1 m2 b1\nPedal: C m1 m2\nPedal: C m2 b1 m2 b1\nm1 C: I\nm2 V\nm3 I\n", encoding="utf-8")
        unpaired = self.corpus / "unpaired"
        unpaired.mkdir()
        (unpaired / "analysis.txt").write_text("Pedal: C m1 b1 m2 b1\n", encoding="utf-8")
        self.records = []
        for path in self.corpus.rglob("analysis.txt"):
            self.records += prepare_source_statements(path, corpus_root=self.corpus)["records"]
        self.intake = self.root / "intake"
        self.intake.mkdir()
        statements = self.intake / "source-statements.jsonl"
        statements.write_text("\n".join(json.dumps(row) for row in self.records) + "\n", encoding="utf-8")
        (self.intake / "report.json").write_text(json.dumps({"complete": True,
            "version": "musical-semantic-intake-trial-0.1.2",
            "artifact_hashes": {str(statements): trial.file_digest(statements)}}), encoding="utf-8")

    def test_all_attempts_preserved_and_outputs_replayable(self):
        originals = {str(p): p.read_bytes() for p in self.corpus.rglob("*") if p.is_file()}
        report = trial.run(self.intake, self.root / "run")
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["source_pedal_statements"], 4)
        self.assertEqual(report["summary"]["status_counts"], {"exact_coordinate": 1, "deferred": 2, "not_selected": 1})
        self.assertEqual(report["summary"]["literal_pattern_observations"], 1)
        self.assertEqual(report["summary"]["musical_role_validated"], 0)
        for path, payload in originals.items():
            self.assertEqual(Path(path).read_bytes(), payload)
        for path, expected in report["artifact_hashes"].items():
            self.assertEqual(trial.file_digest(path), expected)
        index = json.loads((self.root / "run/pattern-index.json").read_text(encoding="utf-8"))
        self.assertTrue(Path(index[0]["path"]).is_file())
        self.assertFalse(index[0]["musical_role_validated"])

    def test_new_output_required_and_no_overwrite(self):
        destination = self.root / "run"
        destination.mkdir()
        marker = destination / "marker.txt"
        marker.write_text("original", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "new_workspace_output"):
            trial.run(self.intake, destination)
        self.assertEqual(marker.read_text(encoding="utf-8"), "original")

    def test_input_edit_rejected_before_any_artifact_write(self):
        path = self.corpus / "paired/analysis.txt"
        path.write_text(path.read_text(encoding="utf-8") + "Note: edited\n", encoding="utf-8")
        destination = self.root / "run"
        with self.assertRaisesRegex(ValueError, "source_changed_since_intake"):
            trial.run(self.intake, destination)
        self.assertFalse(destination.exists())

    def test_statement_edit_rejected_before_any_artifact_write(self):
        path = self.intake / "source-statements.jsonl"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        destination = self.root / "run"
        with self.assertRaisesRegex(ValueError, "statement_artifact_changed"):
            trial.run(self.intake, destination)
        self.assertFalse(destination.exists())

    def test_parse_failure_retains_denominator(self):
        with patch.object(trial.converter, "parse", side_effect=ValueError("synthetic parse failure")):
            report = trial.run(self.intake, self.root / "run")
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"]["status_counts"], {"file_blocked": 3, "not_selected": 1})
        self.assertEqual(report["summary"]["literal_pattern_observations"], 0)
        self.assertEqual(report["summary"]["source_pedal_statements"], 4)

    def test_incomplete_intake_refused(self):
        path = self.intake / "report.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["complete"] = False
        path.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "completed_supported_intake"):
            trial.run(self.intake, self.root / "run")


if __name__ == "__main__":
    unittest.main()
