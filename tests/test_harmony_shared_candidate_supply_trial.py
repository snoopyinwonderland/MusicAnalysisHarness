"""Storage/selection guards, not extra music accuracy or native trial tests."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import harmony_shared_candidate_supply_trial as trial
from musicanote_harness.formal_ir import q


class SharedSupplyTrialGuards(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def document(self, name="input.json", value=None):
        path = self.root / name
        text = json.dumps({"marker": "구간"} if value is None else value)
        if name.endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def test_conflict_checked_protection_never_replaces_expected_SHA(self):
        path = self.document(); original = trial.file_sha(path); inventory = {}
        trial.protect(inventory, str(path), original)
        trial.protect(inventory, str(path), original)
        with self.assertRaisesRegex(ValueError, "conflicting_protected_SHA"):
            trial.protect(inventory, str(path), "a" * 64 if original != "a" * 64 else "b" * 64)
        self.assertEqual(inventory, {str(path): original})

    def test_noncanonical_relative_path_and_non_SHA_rejected(self):
        path = self.document()
        for name, sha in ((str(path), "bad"), ("input.json", "a" * 64),
                          (str(path.parent / ".." / path.parent.name / path.name), trial.file_sha(path))):
            with self.subTest(name=name), self.assertRaises((ValueError, FileNotFoundError)):
                trial.protect({}, name, sha)

    def test_registered_gzip_is_read_without_fabricating_IR_or_authority(self):
        path = self.document("input.json.gz")
        info = {"artifact": str(path), "sha256": trial.file_sha(path)}
        protected = {}
        self.assertEqual(trial.registered(info, protected), {"marker": "구간"})
        self.assertEqual(protected, {str(path): info["sha256"]})

    def test_registered_SHA_mismatch_does_not_register_new_expected_value(self):
        path = self.document(); protected = {}
        with self.assertRaisesRegex(ValueError, "registered_input_SHA_mismatch"):
            trial.registered({"artifact": str(path), "sha256": "0" * 64}, protected)
        self.assertEqual(protected, {})

    def test_nested_output_and_parent_of_input_refused_before_reads_or_writes(self):
        for output in (self.root, self.root / "child", self.root.parent):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "append_only"):
                trial.run(self.root, output)
        self.assertFalse((self.root / "child").exists())

    def test_existing_disjoint_output_refused(self):
        parent, output = self.root / "parent", self.root / "output"
        parent.mkdir(); output.mkdir()
        with self.assertRaisesRegex(ValueError, "append_only"):
            trial.run(parent, output)
        self.assertEqual(list(output.iterdir()), [])

    def test_observed_grid_thirds_and_duplicate_preserve_source_and_raw_context(self):
        context = {"start": q(0), "end": q(4)}
        ir = {"sounding_events": [{"span": {"start": q(a), "end": q(b)}}
                                   for a, b in ((0, 1), (1, 2), (2, 3), (3, 4))]}
        before = deepcopy((ir, context))
        spans = trial.selected_spans(ir, context)
        self.assertEqual(spans, [context, {"start": q(0), "end": q(1)},
                                {"start": q(1), "end": q(2)},
                                {"start": q(2), "end": q(4)},
                                {"start": q(0), "end": q(1)}])
        self.assertEqual((ir, context), before)

    def test_grid_insufficient_for_three_nonempty_segments_is_not_synthesized(self):
        with self.assertRaisesRegex(ValueError, "three_nonempty"):
            trial.selected_spans({"sounding_events": []}, {"start": q(0), "end": q(4)})


if __name__ == "__main__":
    unittest.main()
