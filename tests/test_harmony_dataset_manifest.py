import json
import tempfile
import unittest
from pathlib import Path

from musicanote_harness.harmony_dataset_manifest import build_harmony_dataset_manifest, validate_harmony_data_release
from musicanote_harness.harmony_case_retrieval import build_case_records


def write_package(root, collection, stem, index):
    folder = root / collection / stem
    folder.mkdir(parents=True)
    (folder / "canonical_music_ir.json").write_text("{}", encoding="utf-8")
    report = {
        "score_id": f"score-{index}", "ir_document_id": f"ir-{index}",
        "source_paths": {"score": str(root / collection / "MS3" / f"{stem}.musicxml")},
        "source_sha256": {"score": f"{index:064x}", "harmonies": f"{index + 100:064x}"},
        "imported_annotations": 10, "exact_alignments": 8,
        "source_note_mapping": {"complete": True},
    }
    (folder / "preparation_report.json").write_text(json.dumps(report), encoding="utf-8")


class HarmonyDatasetManifestTest(unittest.TestCase):
    def test_movements_of_same_work_share_family_and_split(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pairs"
            write_package(root, "quartets", "op18-1_01", 1)
            write_package(root, "quartets", "op18-1_02", 2)
            write_package(root, "quartets", "op59-1_01", 3)
            manifest = build_harmony_dataset_manifest(root, Path(temp) / "manifest.json")
            first, second, third = manifest["entries"]
            self.assertEqual(first["work_family_id"], second["work_family_id"])
            self.assertEqual(first["split"], second["split"])
            self.assertNotEqual(first["work_family_id"], third["work_family_id"])
            self.assertFalse(first["eligibility"]["automatic_training"])
            self.assertFalse(first["rights"]["external_api_transmission_approved"])

    def test_manifest_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pairs"
            write_package(root, "collection", "piece_01", 1)
            left = build_harmony_dataset_manifest(root, Path(temp) / "left.json")
            right = build_harmony_dataset_manifest(root, Path(temp) / "right.json")
            self.assertEqual(left["entries"], right["entries"])

    def test_corelli_letter_movements_share_one_work_family(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pairs"
            write_package(root, "corelli", "op01n01a", 1)
            write_package(root, "corelli", "op01n01b", 2)
            manifest = build_harmony_dataset_manifest(root, Path(temp) / "manifest.json")
            self.assertEqual(manifest["entries"][0]["work_family_id"], manifest["entries"][1]["work_family_id"])
            self.assertEqual(manifest["entries"][0]["movement_id"], "a")

    def test_release_validation_detects_no_leakage_for_linked_case(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pairs"
            write_package(root, "collection", "piece_01", 1)
            manifest_path = Path(temp) / "manifest.json"
            manifest = build_harmony_dataset_manifest(root, manifest_path)
            entry = manifest["entries"][0]
            package = {
                "ir": {"score": {"score_id": entry["score_id"]}, "ir_document_id": entry["ir_document_id"],
                       "sounding_events": [{"sounding_event_id": "s1", "pitch": {"midi_pitch": 60, "spelling": "C4"},
                                            "span": {"start": {"numerator": 0, "denominator": 1}, "end": {"numerator": 1, "denominator": 1}}}]},
                "annotations": [{"annotation_id": "a1", "raw_label": "I", "components": {"chord": "I", "key": "C"},
                                 "target": {"span": {"start": {"numerator": 0, "denominator": 1}, "end": {"numerator": 1, "denominator": 1}}},
                                 "source_asset_sha256": "a" * 64, "source_locator": {"path": "a.tsv", "line": 2},
                                 "author_origin": "human", "source_review_status": "unknown"}],
                "alignments": [{"annotation_id": "a1", "mapping_status": "exact"}],
                "report": {"source_sha256": {"score": entry["score_sha256"], "harmonies": entry["annotation_sha256"]},
                           "source_paths": {"score": entry["score_source_path"]}},
            }
            case = build_case_records(package, entry)[0]
            library = Path(temp) / "cases.jsonl"
            library.write_text(json.dumps(case) + "\n", encoding="utf-8")
            result = validate_harmony_data_release(manifest_path, library, Path(temp) / "validation.json")
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["checks"]["case_identity_mismatches"], 0)


if __name__ == "__main__":
    unittest.main()
