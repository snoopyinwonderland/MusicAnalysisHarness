import json
import tempfile
import unittest
from pathlib import Path

from musicanote_harness.harmony_case_retrieval import build_case_records
from musicanote_harness.harmony_case_retrieval_eval import evaluate_case_retrieval_ablation
from tests.test_harmony_case_retrieval import package


class HarmonyCaseRetrievalEvalTest(unittest.TestCase):
    def test_ablation_uses_dev_queries_and_train_candidates(self):
        train = build_case_records(package("train", [48, 52, 55], "I"))[0]
        dev = build_case_records(package("dev", [50, 54, 57], "I"))[0]
        train["dataset_identity"]["split"] = "train"
        dev["dataset_identity"]["split"] = "dev"
        train["dataset_identity"]["annotation_lineage_id"] = "train-lineage"
        dev["dataset_identity"]["annotation_lineage_id"] = "dev-lineage"
        with tempfile.TemporaryDirectory() as temp:
            library = Path(temp) / "cases.jsonl"
            library.write_text("\n".join(json.dumps(row) for row in (train, dev)) + "\n", encoding="utf-8")
            report = evaluate_case_retrieval_ablation(library, Path(temp) / "report.json")
            self.assertEqual(report["query_count"], 1)
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(len(report["results"]), 5)
            self.assertTrue(all(row["family_top1_accuracy"] == 1.0 for row in report["results"]))


if __name__ == "__main__":
    unittest.main()
