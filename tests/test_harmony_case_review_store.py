import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from musicanote_harness.harmony_case_review_store import append_case_review, load_latest


class HarmonyCaseReviewStoreTest(unittest.TestCase):
    def test_feedback_is_append_only_and_not_immediately_trainable(self):
        with tempfile.TemporaryDirectory() as folder_name:
            path = Path(folder_name) / "case_reviews.jsonl"
            first = append_case_review(
                path, query_id="query-1", case_id="case-1", engine_version="retrieval-0.1",
                verdict="similar_surface_different_function", axis_ratings={"surface": 4, "harmonic_function": 1},
            )
            second = append_case_review(
                path, query_id="query-1", case_id="case-1", engine_version="retrieval-0.1",
                verdict="cannot_judge", note="local key needed",
            )
            self.assertEqual(second["supersedes_review_id"], first["review_id"])
            self.assertFalse(second["training_eligible"])
            self.assertFalse(second["rule_update_eligible"])
            self.assertEqual(load_latest(path)["query-1|case-1"]["verdict"], "cannot_judge")
            schema = json.loads((Path(__file__).resolve().parents[1] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "harmony_case_review.schema.json").read_text(encoding="utf-8"))
            Draft202012Validator(schema).validate(second)

    def test_invalid_verdict_and_rating_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder_name:
            path = Path(folder_name) / "case_reviews.jsonl"
            with self.assertRaises(ValueError):
                append_case_review(path, query_id="q", case_id="c", engine_version="v", verdict="gold")
            with self.assertRaises(ValueError):
                append_case_review(path, query_id="q", case_id="c", engine_version="v", verdict="not_similar", axis_ratings={"surface": 5})


if __name__ == "__main__":
    unittest.main()
