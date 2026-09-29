import json
import tempfile
import unittest
from pathlib import Path

from musicanote_harness.annotation_source_audit import audit_jams, audit_romantext


class AnnotationSourceAuditTest(unittest.TestCase):
    def _registry(self, folder: Path, assets: list[tuple[str, str, str]]) -> Path:
        registry = folder / "registry"
        registry.mkdir()
        (registry / "registry_summary.json").write_text(json.dumps({"root": str(folder)}), encoding="utf-8")
        (registry / "assets.jsonl").write_text(
            "".join(json.dumps({"relative_path": relative, "corpus": corpus, "suffix": suffix}) + "\n"
                    for relative, corpus, suffix in assets), encoding="utf-8"
        )
        return registry / "assets.jsonl"

    def test_romantext_records_automatic_origin_without_gold_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            song = root / "when-in-rome" / "song"
            song.mkdir(parents=True)
            (song / "analysis_automatic.rntxt").write_text(
                "Analyst: AutoTest\nTime Signature: 4/4\n\nm1 C: I b3 V\n", encoding="utf-8"
            )
            (song / "score.musicxml").write_text("<score-partwise/>", encoding="utf-8")
            assets = self._registry(root, [("when-in-rome/song/analysis_automatic.rntxt", "when-in-rome", ".rntxt")])
            result = audit_romantext(assets, root / "out")
            self.assertEqual(result["counts"]["shape_readable"], 1)
            self.assertEqual(result["counts"]["automatic_filename"], 1)
            self.assertEqual(result["counts"]["has_sibling_score_candidate"], 1)

    def test_jams_namespaces_and_rows_are_only_shape_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "choco" / "partitions" / "example"
            parent.mkdir(parents=True)
            (parent / "one.jams").write_text(json.dumps({
                "file_metadata": {"title": "Example", "jams_version": "0.3.4", "identifiers": {}},
                "annotations": [{"namespace": "chord", "annotation_metadata": {"corpus": "sample"},
                                 "data": [{"time": 0, "duration": 4, "value": "C:maj"}]}],
            }), encoding="utf-8")
            assets = self._registry(root, [("choco/partitions/example/one.jams", "choco", ".jams")])
            result = audit_jams(assets, root / "out")
            self.assertEqual(result["file_status_counts"]["shape_readable"], 1)
            self.assertEqual(result["annotation_namespaces"]["chord"], 1)
            self.assertEqual(result["annotation_data_rows"]["chord"], 1)


if __name__ == "__main__":
    unittest.main()
