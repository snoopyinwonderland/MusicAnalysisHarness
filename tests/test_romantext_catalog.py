import json
import tempfile
import unittest
from pathlib import Path

from musicanote_harness.romantext_catalog import CatalogApplication, load_catalog, search_catalog
from musicanote_harness.harmony_case_retrieval import build_case_records
from tests.test_harmony_case_retrieval import package


class RomanTextCatalogTest(unittest.TestCase):
    def test_case_retrieval_and_feedback_are_separate_from_source_review(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            records = folder / "records.jsonl"
            records.write_text(json.dumps({
                "analysis_path": str(folder / "analysis.rntxt"), "score_path": str(folder / "score.musicxml"),
                "corpus": "when-in-rome", "status": "aligned_complete",
                "status_counts": {"exact_coordinate": 1}, "roman_events": 1,
                "analysis_sha256": "1" * 64, "score_sha256": "2" * 64,
            }) + "\n", encoding="utf-8")
            candidate = build_case_records(package("candidate", [48, 52, 55], "V"))[0]
            candidate["dataset_identity"]["split"] = "train"
            candidate["dataset_identity"]["annotation_lineage_id"] = "candidate-lineage"
            library = folder / "cases.jsonl"
            library.write_text(json.dumps(candidate) + "\n", encoding="utf-8")
            application = CatalogApplication(records, folder / "output", case_library_path=library)
            identity = application.entries[0]["id"]
            destination = application.output / identity
            destination.mkdir(parents=True)
            query_package = package("query", [50, 54, 57], "I")
            (destination / "canonical_music_ir.json").write_text(json.dumps(query_package["ir"]), encoding="utf-8")
            (destination / "imported_annotations.jsonl").write_text(
                "\n".join(json.dumps(row) for row in query_package["annotations"]) + "\n", encoding="utf-8")
            (destination / "alignment_records.jsonl").write_text(
                "\n".join(json.dumps(row) for row in query_package["alignments"]) + "\n", encoding="utf-8")
            (destination / "source_harmony_evidence.json").write_text(json.dumps({"records": []}), encoding="utf-8")
            (destination / "preparation_report.json").write_text(json.dumps(query_package["report"]), encoding="utf-8")
            application.prepare = lambda _identity: {"cached": True}
            annotation_id = query_package["annotations"][0]["annotation_id"]
            result = application.retrieve_harmony_cases(identity, annotation_id)
            self.assertEqual(len(result["matches"]), 1)
            self.assertEqual(result["ui_policy"]["structure_influence"], "none")
            saved = application.save_harmony_case_review(identity, {
                "annotation_id": annotation_id, "query_id": result["query"]["query_id"],
                "case_id": candidate["case_id"], "verdict": "useful_analogy",
                "axis_ratings": {"surface": 4}, "note": "useful context",
            })
            self.assertFalse(saved["training_eligible"])
            self.assertTrue(application.case_review_path.is_file())

    def test_load_and_search_without_reparsing_scores(self):
        with tempfile.TemporaryDirectory() as folder_name:
            records = Path(folder_name) / "records.jsonl"
            rows = [
                {
                    "analysis_path": r"K:\data\openscore-lieder\scores\Beach,_Amy\Song_Set\analysis_automatic.rntxt",
                    "score_path": r"K:\data\openscore-lieder\scores\Beach,_Amy\Song_Set\score.musicxml",
                    "corpus": "openscore-lieder",
                    "status": "aligned_partial",
                    "status_counts": {"exact_coordinate": 30, "ambiguous": 6},
                    "roman_events": 36,
                    "score_measures": 29,
                    "analysis_sha256": "a" * 64,
                    "score_sha256": "b" * 64,
                },
                {
                    "analysis_path": r"K:\data\when-in-rome\Corpus\Keyboard\Bach,_Johann_Sebastian\WTC_I\01\analysis.rntxt",
                    "score_path": r"K:\data\when-in-rome\Corpus\Keyboard\Bach,_Johann_Sebastian\WTC_I\01\score.musicxml",
                    "corpus": "when-in-rome",
                    "status": "aligned_complete",
                    "status_counts": {"exact_coordinate": 37},
                    "roman_events": 37,
                    "score_measures": 35,
                    "analysis_sha256": "c" * 64,
                    "score_sha256": "d" * 64,
                },
            ]
            records.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            evidence_records = Path(folder_name) / "evidence.jsonl"
            evidence_records.write_text(json.dumps({
                "analysis_sha256": "a" * 64,
                "status": "complete",
                "support_band_counts": {
                    "strong": 20, "moderate": 5, "mixed": 3, "weak": 2, "unscorable": 0,
                },
                "review_candidate_count": 5,
            }), encoding="utf-8")
            catalog = load_catalog(records, evidence_records)
            self.assertEqual(len(catalog), 2)
            self.assertEqual(search_catalog(catalog, "bach")[0]["exact"], 37)
            self.assertEqual(len(search_catalog(catalog, "WTC I")), 1)
            self.assertEqual(catalog[1]["composer"], "Bach, Johann Sebastian")
            self.assertEqual(len(search_catalog(catalog, corpus="openscore-lieder")), 1)
            self.assertEqual(len(search_catalog(catalog, status="aligned_complete")), 1)
            self.assertEqual(len(search_catalog(catalog, evidence="weak")), 1)
            self.assertEqual(len(search_catalog(catalog, evidence="mixed_or_weak")), 1)
            self.assertEqual(len(search_catalog(catalog, evidence="strong_only")), 0)
            self.assertEqual(catalog[0]["support_band_counts"]["weak"], 2)
            self.assertEqual(catalog[1]["evidence_status"], "not_audited")

    def test_score_hash_bridge_preserves_multiple_interpretations(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            records = folder / "records.jsonl"
            common = {
                "score_path": str(folder / "score.musicxml"),
                "corpus": "when-in-rome",
                "status": "aligned_complete",
                "status_counts": {"exact_coordinate": 1},
                "roman_events": 1,
                "score_sha256": "b" * 64,
            }
            rows = [
                {**common, "analysis_path": str(folder / "one.rntxt"), "analysis_sha256": "1" * 64},
                {**common, "analysis_path": str(folder / "two.rntxt"), "analysis_sha256": "2" * 64},
            ]
            records.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            application = CatalogApplication(records, folder / "output")
            result = application.overlay_by_score_sha256("b" * 64)
            self.assertEqual(result["match_status"], "multiple")
            self.assertEqual(len(result["candidates"]), 2)
            self.assertEqual(
                {candidate["analysis_sha256"] for candidate in result["candidates"]},
                {"1" * 64, "2" * 64},
            )

    def test_score_hash_bridge_rejects_unknown_hash(self):
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            records = folder / "records.jsonl"
            records.write_text("", encoding="utf-8")
            application = CatalogApplication(records, folder / "output")
            with self.assertRaises(KeyError):
                application.overlay_by_score_sha256("f" * 64)


if __name__ == "__main__":
    unittest.main()
