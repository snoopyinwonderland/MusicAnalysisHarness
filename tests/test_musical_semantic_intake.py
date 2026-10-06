"""Source annotations are preserved, never silently turned into musical facts."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness import musical_semantic_enrichment as contract
from musicanote_harness import musical_semantic_intake as intake
from musicanote_harness.musical_semantic_intake import prepare_source_statements


def source(root: Path, payload: bytes, relative: str = "composer/work/analysis.txt") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


class MusicalSemanticIntakeTests(unittest.TestCase):
    def test_actual_producer_version_and_declared_config_hash_are_not_contract_defaults(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = source(root, b"note: source only\nm1 I\nFORM: A\n")
            first = prepare_source_statements(path, corpus_root=root, context_radius=1)
            same = prepare_source_statements(path, corpus_root=root, context_radius=1)
            changed = prepare_source_statements(path, corpus_root=root, context_radius=2)
            expected_sha = hashlib.sha256(json.dumps(first["configuration"], sort_keys=True,
                ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
            self.assertEqual(first["configuration_sha256"], expected_sha)
            self.assertEqual(first["configuration_sha256"], same["configuration_sha256"])
            self.assertNotEqual(first["configuration_sha256"], changed["configuration_sha256"])
            self.assertEqual(first["configuration"]["native_tag_matching"], "case_insensitive")
            self.assertEqual(first["configuration"]["canonical_tag_routing"],
                             {"Note": None, "Form": "form_role", "Pedal": "harmonic_role"})
            for row in first["records"]:
                producer = row["provenance"]["producer"]
                self.assertEqual(producer["version"], intake.VERSION)
                self.assertNotEqual(producer["version"], contract.SCHEMA_VERSION)
                self.assertEqual(producer["config_sha256"], expected_sha)
                self.assertEqual(producer["schema_ref"], {"name": contract.SCHEMA_NAME, "version": contract.SCHEMA_VERSION})
                self.assertIsNone(producer["model_ref"])
            self.assertEqual(first["source"]["producer_version"], intake.VERSION)
            self.assertEqual(first["source"]["producer_config_sha256"], expected_sha)

    def test_every_native_statement_raw_value_hash_and_pending_source_state(self):
        payload = (b"\xef\xbb\xbfNote:  editorial instruction\r\n"
                   b"m1 I\r\n  Form: opening or continuation? \n"
                   b"Note: melody bass Alberti suspension sequence dynamics.\r"
                   b"m2 V\nPedal: C -- not a resolved assertion\nNote:\n")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = source(root, payload)
            prepared = prepare_source_statements(path, corpus_root=root)
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(prepared["source"]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(prepared["source"]["source_statements"], 5)
            self.assertEqual(prepared["source"]["statement_counts_by_native_tag"], {"Note": 3, "Form": 1, "Pedal": 1})
            self.assertEqual([row["claim"]["axis"] for row in prepared["records"]],
                             [None, "form_role", None, "harmonic_role", None])
            for row in prepared["records"]:
                self.assertEqual(row["record_kind"], "SOURCE")
                self.assertEqual(row["coverage_state"], "needs_alignment")
                self.assertIsNone(row["binding"])
                self.assertIsNone(row["source_claim_ref"])
                self.assertIsNone(row["claim"]["term"])
                self.assertIsNone(row["confidence"])
                self.assertEqual(row["human_review"], {"status": "pending_review", "reviewer_id": None, "review_ref": None})
                self.assertFalse(row["use_policy"]["training_eligible"])
                self.assertEqual(row["use_policy"]["gold_status"], "not_established")
                self.assertEqual(row["source_context"]["source_sha256"], prepared["source"]["sha256"])
                self.assertEqual(row["source_context"]["rights"]["rights_status"], "unknown")
                contract.validate_record(row)
            first = prepared["records"][0]["source_context"]
            self.assertEqual(first["raw_text"], "\ufeffNote:  editorial instruction")
            self.assertEqual(first["location"]["locator"]["raw_value"], "  editorial instruction")
            self.assertEqual(first["location"]["locator"]["physical_line"], 1)
            self.assertEqual(first["location"]["locator"]["line_ending"], "\r\n")
            self.assertEqual(prepared["records"][-1]["source_context"]["location"]["locator"]["raw_value"], "")

    def test_neighboring_measure_context_does_not_bind_most_recent_measure(self):
        payload = b"Note: preface\nm1 I\n\nForm: B\nprose continuation\nm9 V\nPedal: something\n"
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = prepare_source_statements(source(root, payload), corpus_root=root, context_radius=1)
            before = prepared["records"][0]["source_context"]["location"]["locator"]
            middle = prepared["records"][1]["source_context"]["location"]["locator"]
            after = prepared["records"][2]["source_context"]["location"]["locator"]
            self.assertIsNone(before["preceding_measure_line"])
            self.assertEqual(before["following_measure_line"]["physical_line"], 2)
            self.assertEqual(middle["preceding_measure_line"], {"physical_line": 2, "raw_text": "m1 I", "line_ending": "\n"})
            self.assertEqual(middle["following_measure_line"]["physical_line"], 6)
            self.assertEqual([row["physical_line"] for row in middle["context_lines"]], [3, 4, 5])
            self.assertEqual(after["preceding_measure_line"]["physical_line"], 6)
            self.assertIsNone(after["following_measure_line"])
            self.assertFalse(middle["context_is_target"])
            self.assertIsNone(prepared["case"]["score_ref"])
            self.assertIsNone(prepared["case"]["score_xml_ref"])
            self.assertEqual(prepared["case"]["note_refs"], [])
            self.assertEqual(prepared["case"]["context_status"]["full_xml"], "missing_not_aligned")

    def test_duplicate_text_remains_distinct_and_byte_identical_retry_is_stable(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = source(root, b"Note: repeat\nNote: repeat\n")
            first = prepare_source_statements(path, corpus_root=root)
            self.assertEqual(first, prepare_source_statements(path, corpus_root=root))
            ids = [row["record_id"] for row in first["records"]]
            self.assertEqual(len(set(ids)), 2)
            other = source(root, path.read_bytes(), "other/work/analysis.txt")
            second = prepare_source_statements(other, corpus_root=root)
            self.assertNotEqual(first["case"]["case_id"], second["case"]["case_id"])
            self.assertEqual(first["source"]["sha256"], second["source"]["sha256"])

    def test_physical_lines_do_not_split_unicode_line_separator_or_vertical_tab(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = "Note: first\u2028second\vthird\r\nForm: x".encode("utf-8")
            prepared = prepare_source_statements(source(root, payload), corpus_root=root, context_radius=0)
            self.assertEqual(prepared["source"]["physical_lines"], 2)
            self.assertEqual(prepared["records"][1]["source_context"]["location"]["locator"]["physical_line"], 2)
            self.assertEqual(prepared["records"][0]["source_context"]["raw_text"], "Note: first\u2028second\vthird")
            self.assertEqual(prepared["records"][1]["source_context"]["location"]["locator"]["line_ending"], "")

    def test_case_insensitive_native_tags_only_without_keyword_classification(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = ("note: bass\nFORM: opening\nPedal : C\nnot a Note: line\n"
                    "\u2003Note: sequence\nForm: gibberish\nPedal: editorial metadata\n")
            prepared = prepare_source_statements(source(root, text.encode()), corpus_root=root)
            self.assertEqual(prepared["source"]["statement_counts_by_native_tag"], {"Note": 2, "Form": 2, "Pedal": 1})
            locators = [row["source_context"]["location"]["locator"] for row in prepared["records"]]
            self.assertEqual([row["native_tag"] for row in locators], ["Note", "Form", "Note", "Form", "Pedal"])
            self.assertEqual([row["source_tag_spelling"] for row in locators], ["note", "FORM", "Note", "Form", "Pedal"])
            self.assertTrue(all(row["claim"]["term"] is None for row in prepared["records"]))
            coverage = contract.plan_coverage([prepared["case"]], prepared["records"])[0]
            self.assertEqual(coverage["axis_states"]["form_role"], "needs_alignment")
            self.assertEqual(coverage["axis_states"]["harmonic_role"], "needs_alignment")
            self.assertEqual(coverage["axis_states"]["voice_role"], "not_assessed")
            self.assertEqual(set(coverage["missing_axes"]), set(contract.AXES))

    def test_all_native_tag_case_variants_preserve_original_spelling_and_raw_lines(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "note: prose\nNOTE: prose\nnOtE: prose\nform: A\nFORM: B\npedal: C\nPEDAL: D\n"
            prepared = prepare_source_statements(source(root, text.encode()), corpus_root=root)
            self.assertEqual(prepared["source"]["source_statements"], 7)
            self.assertEqual(prepared["source"]["statement_counts_by_native_tag"], {"Note": 3, "Form": 2, "Pedal": 2})
            rows = prepared["records"]
            self.assertEqual([row["source_context"]["raw_text"] for row in rows], text.splitlines())
            self.assertEqual([row["source_context"]["location"]["locator"]["source_tag_spelling"] for row in rows],
                             ["note", "NOTE", "nOtE", "form", "FORM", "pedal", "PEDAL"])
            self.assertEqual([row["claim"]["axis"] for row in rows],
                             [None, None, None, "form_role", "form_role", "harmonic_role", "harmonic_role"])
            self.assertTrue(all(row["claim"]["term"] is None for row in rows))

    def test_no_statements_is_not_negative_musical_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = prepare_source_statements(source(root, b"m1 I\n"), corpus_root=root)
            self.assertEqual(prepared["records"], [])
            self.assertFalse(prepared["source"]["native_tags_are_musical_truth"])
            coverage = contract.plan_coverage([prepared["case"]], [])[0]
            self.assertEqual(set(coverage["axis_states"].values()), {"not_assessed"})

    def test_empty_source_has_zero_physical_lines_and_stable_file_case(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = prepare_source_statements(source(root, b""), corpus_root=root)
            self.assertEqual(prepared["source"]["physical_lines"], 0)
            self.assertEqual(prepared["source"]["source_statements"], 0)

    def test_unverified_encoding_and_changed_source_hash_fail_closed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = source(root, b"Note: \xff\n")
            with self.assertRaisesRegex(ValueError, "source_not_utf8"):
                prepare_source_statements(path, corpus_root=root)
            path.write_bytes(b"Note: safe\n")
            with self.assertRaisesRegex(ValueError, "source_input_hash_mismatch"):
                prepare_source_statements(path, corpus_root=root, expected_sha256="0" * 64)

    def test_scope_filename_and_configuration_checks(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "corpus"
            path = source(root, b"Note: safe\n")
            outside = source(base / "outside", b"Note: elsewhere\n")
            with self.assertRaisesRegex(ValueError, "source_path_outside_corpus_root"):
                prepare_source_statements(outside, corpus_root=root)
            wrong_name = root / "score.xml"
            wrong_name.write_bytes(path.read_bytes())
            with self.assertRaisesRegex(ValueError, "source_filename_not_analysis_txt"):
                prepare_source_statements(wrong_name, corpus_root=root)
            for radius in (-1, True, 1.5):
                with self.subTest(radius=radius), self.assertRaisesRegex(ValueError, "invalid_source_context_radius"):
                    prepare_source_statements(path, corpus_root=root, context_radius=radius)


if __name__ == "__main__":
    unittest.main()
