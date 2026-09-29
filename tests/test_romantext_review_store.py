import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from musicanote_harness.romantext_review_store import append_review, load_latest


class RomanTextReviewStoreTest(unittest.TestCase):
    def test_append_only_review_supersedes_without_becoming_gold(self):
        with tempfile.TemporaryDirectory() as folder_name:
            path = Path(folder_name) / "reviewer_annotations.jsonl"
            first = append_review(
                path, score_review_id="0123456789abcdef", annotation_id="ann_1",
                reason="non_chord_tone", note="passing tone candidate",
            )
            second = append_review(
                path, score_review_id="0123456789abcdef", annotation_id="ann_1",
                reason="cannot_judge", note="needs local-key context",
            )
            self.assertEqual(second["supersedes_review_id"], first["review_id"])
            self.assertFalse(second["training_eligible"])
            self.assertEqual(load_latest(path)["ann_1"]["reason"], "cannot_judge")
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)

            schema_path = (
                Path(__file__).resolve().parents[1] / "MUSICANOTE_Canonical_Music_IR" /
                "schemas" / "romantext_reviewer_annotation.schema.json"
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator(schema).validate(second)

    def test_unknown_reason_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder_name:
            with self.assertRaises(ValueError):
                append_review(
                    Path(folder_name) / "reviews.jsonl", score_review_id="score",
                    annotation_id="ann", reason="gold",
                )


if __name__ == "__main__":
    unittest.main()
