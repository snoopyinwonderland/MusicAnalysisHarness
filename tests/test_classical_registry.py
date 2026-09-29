import json
import tempfile
import unittest
from pathlib import Path

from musicanote_harness.classical_registry import inventory_classical


class ClassicalRegistryTest(unittest.TestCase):
    def test_all_assets_are_registered_and_pairs_remain_unaligned(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "corpora"
            sub = root / "dcmlab" / "example"
            for relative in ("MS3/a.musicxml", "measures/a.measures.tsv", "notes/a.notes.tsv",
                             "harmonies/a.harmonies.tsv", "MS3/b.musicxml",
                             "MS3/c.mscx", "measures/c.measures.tsv", "notes/c.notes.tsv", "harmonies/c.harmonies.tsv"):
                path = sub / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")
            (root / "choco").mkdir()
            (root / "choco" / "x.jams").write_text("{}", encoding="utf-8")
            summary = inventory_classical(root, Path(folder) / "output")
            self.assertEqual(summary["asset_rows"], 10)
            self.assertEqual(summary["dcml_pair_candidates"], {
                "complete_files_unaligned": 1, "incomplete_files": 1, "complete_files_requires_conversion": 1,
            })
            pair_rows = [json.loads(line) for line in (Path(folder) / "output" / "dcml_pair_candidates.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(pair_rows[0]["status"], "complete_files_unaligned")
            self.assertEqual(pair_rows[0]["alignment_status"], "not_attempted")
            self.assertEqual(pair_rows[1]["missing"], ["measures", "notes", "harmonies"])
            self.assertEqual(pair_rows[2]["status"], "complete_files_requires_conversion")


if __name__ == "__main__":
    unittest.main()
