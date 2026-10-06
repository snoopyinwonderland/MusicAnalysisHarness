import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from musicanote_harness.harmony_orchestral_readiness import (
    AuditCase, annotation_lineage, audit_case, compare_grids, harmonic_use_gate,
    inspect_source_score, local_cases, read_score_grid, run_audit,
)


def score_xml(transpose="", part_count=1, measure_numbers=(1, 2), namespace=""):
    declarations = "".join(f'<score-part id="P{i}"><part-name>Part {i}</part-name></score-part>'
                           for i in range(1, part_count + 1))
    parts = ""
    for index in range(1, part_count + 1):
        measures = ""
        for ordinal, number in enumerate(measure_numbers):
            attributes = (f'<attributes><divisions>3</divisions><time><beats>4</beats><beat-type>4</beat-type></time>'
                          f'{transpose if index == 1 else ""}</attributes>') if ordinal == 0 else ""
            measures += (f'<measure number="{number}">{attributes}<note><rest/><duration>12</duration>'
                         '<type>whole</type></note></measure>')
        parts += f'<part id="P{index}">{measures}</part>'
    return (f'<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0"{namespace}>'
            f'<movement-title>Synthetic</movement-title><part-list>{declarations}</part-list>{parts}</score-partwise>')


def grid_row(label="1", start="0", actual="4"):
    return {"printed_measure_number": label, "start_ql": start, "nominal_duration_ql": "4",
            "actual_duration_ql": actual, "time_signature": "4/4", "padding_left_ql": "0"}


class HarmonyOrchestralReadinessTest(unittest.TestCase):
    def test_source_metadata_preserves_actual_parts_and_transpose(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.musicxml"
            path.write_text(score_xml('<transpose number="1"><diatonic>-1</diatonic><chromatic>-2</chromatic></transpose>', 2), encoding="utf-8")
            result = inspect_source_score(path)
            self.assertEqual(result["source_part_count"], 2)
            self.assertEqual(result["declared_part_count"], 2)
            self.assertEqual(result["nonzero_source_transpose_count"], 1)
            declaration = result["source_transpose_declarations"][0]
            self.assertEqual(declaration["source_fields"]["chromatic"], "-2")
            self.assertEqual(declaration["printed_measure_number"], "1")
            self.assertEqual(declaration["source_part_name"], "Part 1")
            self.assertFalse(result["concert_normalization_verified"])
            self.assertEqual(len(result["source_sha256"]), 64)

    def test_mxl_reads_container_root_without_extraction(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.mxl"
            with ZipFile(path, "w") as archive:
                archive.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="scores/main.xml" media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>')
                archive.writestr("scores/main.xml", score_xml(part_count=3))
            result = inspect_source_score(path)
            self.assertEqual(result["source_part_count"], 3)
            self.assertEqual(result["musicxml_archive_member"], "scores/main.xml")
            self.assertFalse((Path(name) / "scores").exists())

    def test_unsafe_mxl_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "bad.mxl"
            with ZipFile(path, "w") as archive:
                archive.writestr("META-INF/container.xml", '<container><rootfile full-path="../score.xml" media-type="application/vnd.recordare.musicxml+xml"/></container>')
            with self.assertRaisesRegex(ValueError, "unsafe_musicxml_rootfile"):
                inspect_source_score(path)

    def test_unique_mxl_rootfile_without_optional_media_type_is_supported(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.mxl"
            with ZipFile(path, "w") as archive:
                archive.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="score.xml"/></rootfiles></container>')
                archive.writestr("score.xml", score_xml(part_count=2))
            self.assertEqual(inspect_source_score(path)["source_part_count"], 2)

    def test_multiple_mxl_rootfiles_are_not_guessed(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.mxl"
            with ZipFile(path, "w") as archive:
                archive.writestr("META-INF/container.xml", '<container><rootfile full-path="one.xml"/><rootfile full-path="two.xml"/></container>')
            with self.assertRaisesRegex(ValueError, "musicxml_rootfile_not_unique"):
                inspect_source_score(path)

    def test_namespaced_source_metadata_is_supported(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.musicxml"
            path.write_text(score_xml(namespace=' xmlns="urn:synthetic-musicxml"'), encoding="utf-8")
            self.assertEqual(inspect_source_score(path)["source_part_count"], 1)

    def test_invalid_or_missing_chromatic_stays_review_required(self):
        with tempfile.TemporaryDirectory() as name:
            for index, transpose in enumerate(("<transpose><chromatic>unknown</chromatic></transpose>",
                                               "<transpose><diatonic>1</diatonic></transpose>")):
                path = Path(name) / f"score{index}.musicxml"
                path.write_text(score_xml(transpose), encoding="utf-8")
                metadata = inspect_source_score(path)
                self.assertEqual(metadata["invalid_source_transpose_count"], 1)
                gate = harmonic_use_gate(metadata, {"cross_part_grid_compatible": True}, {"status": "aligned_complete"})
                self.assertIn("invalid_source_transpose_requires_review", gate["technical_blockers"])

    def test_nonzero_transposition_blocks_even_perfect_coordinate_alignment(self):
        gate = harmonic_use_gate({"nonzero_source_transpose_count": 2, "invalid_source_transpose_count": 0},
                                 {"cross_part_grid_compatible": True}, {"status": "aligned_complete"})
        self.assertFalse(gate["harmonic_use_eligible"])
        self.assertFalse(gate["technical_coordinate_ready"])
        self.assertIn("nonzero_source_transpose_requires_concert_normalization", gate["technical_blockers"])
        self.assertFalse(gate["source_transposition_repaired"])

    def test_no_transpose_does_not_promote_policy_gold_or_accuracy(self):
        gate = harmonic_use_gate({"nonzero_source_transpose_count": 0, "invalid_source_transpose_count": 0},
                                 {"cross_part_grid_compatible": True}, {"status": "aligned_complete"})
        self.assertTrue(gate["technical_coordinate_ready"])
        self.assertFalse(gate["harmonic_use_eligible"])
        self.assertFalse(gate["human_gold"])
        self.assertFalse(gate["automatic_training"])
        self.assertFalse(gate["blind_evaluation"])
        self.assertIn("cross_edition_identity_not_validated", gate["policy_and_identity_blockers"])

    def test_source_octave_doubling_is_not_silently_normalized(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.musicxml"
            path.write_text(score_xml('<transpose><chromatic>0</chromatic><double above="yes"/></transpose>'), encoding="utf-8")
            metadata = inspect_source_score(path)
            self.assertEqual(metadata["source_double_transpose_count"], 1)
            gate = harmonic_use_gate(metadata, {"cross_part_grid_compatible": True}, {"status": "aligned_complete"})
            self.assertIn("source_octave_doubling_requires_review", gate["technical_blockers"])
            self.assertFalse(gate["technical_coordinate_ready"])

    def test_grid_comparison_detects_measure_start_duration_and_meter(self):
        left = [grid_row(), grid_row("2", "4")]
        right = [grid_row(), {**grid_row("2", "3", "3"), "time_signature": "3/4"}]
        result = compare_grids(left, right)
        self.assertEqual(result["matching_measure_count"], 1)
        self.assertEqual(result["status"], "coordinate_grid_mismatch")
        self.assertEqual(result["diagnostic_counts"]["start_ql_mismatch"], 1)
        self.assertEqual(result["diagnostic_counts"]["actual_duration_ql_mismatch"], 1)
        self.assertFalse(result["cross_edition_identity_validated"])

    def test_grid_count_mismatch_and_printed_suffix_are_not_repaired(self):
        result = compare_grids([grid_row("1a")], [grid_row("1"), grid_row("2", "4")])
        self.assertEqual(result["diagnostic_counts"], {"measure_count_mismatch": 1, "printed_measure_number_mismatch": 1})

    def test_existing_rational_grid_provider_reads_multi_part_source(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "score.musicxml"
            path.write_text(score_xml(part_count=2), encoding="utf-8")
            result = read_score_grid(path)
            self.assertEqual(result["parsed_part_count"], 2)
            self.assertEqual(result["reference_measure_count"], 2)
            self.assertTrue(result["cross_part_grid_compatible"])
            self.assertEqual(result["parts"][0]["grid"][1]["start_ql"], "4")
            self.assertFalse(result["concert_transposition_applied"])

    def test_automatic_filename_and_assisted_human_lineage_remain_separate(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            automatic = folder / "analysis_automatic.rntxt"
            automatic.write_text("Analyst: Named Person\nm1 C: I\n", encoding="utf-8")
            assisted = folder / "analysis.txt"
            assisted.write_text("Analyst: Person, manually through judicious automation\nm1 C: I\n", encoding="utf-8")
            self.assertEqual(annotation_lineage(automatic)["origin"], "automatic_filename_declared")
            self.assertEqual(annotation_lineage(assisted)["origin"], "human_with_automation_declared")
            self.assertFalse(annotation_lineage(assisted)["human_gold_validated"])

    def test_real_alignment_api_is_coordinate_only_in_synthetic_audit(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            score = folder / "score.musicxml"
            score.write_text(score_xml(part_count=2), encoding="utf-8")
            analysis = folder / "analysis.rntxt"
            analysis.write_text("Analyst: Synthetic Test\nTime Signature: 4/4\n\nm1 C: I b3 V\nm2 I\n", encoding="utf-8")
            case = AuditCase("test_case", "synthetic_family", "1", analysis, score, score)
            result = audit_case(case)
            self.assertEqual(result["full_score_alignment"]["status"], "aligned_complete")
            self.assertEqual(result["full_score_alignment"]["roman_events"], 3)
            self.assertNotIn("ir", result["full_score_alignment"])
            self.assertEqual(result["reduction_full_score_grid_comparison"]["status"], "coordinate_grid_compatible")
            self.assertEqual(result["dataset_classification"], "unassigned_exploratory")
            self.assertFalse(result["harmonic_accuracy_measured"])

    def test_missing_inputs_preserve_stage_failures_and_hash_snapshot(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            case = AuditCase("missing_case", "synthetic_family", "1", folder / "missing.rntxt", folder / "missing.musicxml")
            output = folder / "output"
            report = run_audit([case], output)
            self.assertEqual(report["records"][0]["status"], "partial_error")
            self.assertTrue(report["input_hashes_unchanged"])
            self.assertFalse(report["records"][0]["harmonic_use_gate"]["technical_coordinate_ready"])
            contract = json.loads((output / "run-contract.json").read_text(encoding="utf-8"))
            self.assertTrue(all(value is None for value in contract["input_sha256"].values()))
            self.assertTrue(contract["existing_splits_rights_and_gold_unchanged"])
            with self.assertRaises(FileExistsError):
                run_audit([case], output)

    def test_existing_output_and_unsafe_case_paths_are_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            case = AuditCase("../escape", "synthetic_family", "1", folder / "missing", folder / "missing")
            with self.assertRaisesRegex(ValueError, "unsafe_case_id"):
                run_audit([case], folder / "output")
            self.assertFalse((folder / "output").exists())

    def test_changed_input_is_detected_and_report_is_retained(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            analysis = folder / "analysis.txt"
            analysis.write_text("before", encoding="utf-8")
            case = AuditCase("changing_case", "synthetic_family", "1", analysis, folder / "missing")
            def altered(_case, _progress):
                analysis.write_text("after", encoding="utf-8")
                return {"case_id": "changing_case", "full_score_source": {}, "full_score_alignment": {"status": "error"},
                        "harmonic_use_gate": {"technical_blockers": [], "technical_coordinate_ready": False},
                        "reduction_full_score_grid_comparison": {"status": "no_local_reduction"}}
            output = folder / "output"
            with patch("musicanote_harness.harmony_orchestral_readiness.audit_case", side_effect=altered):
                with self.assertRaisesRegex(ValueError, "input_hash_changed"):
                    run_audit([case], output)
            report = json.loads((output / "report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["input_hashes_unchanged"])
            self.assertEqual(report["changed_inputs"], [str(analysis)])

    def test_inventory_is_exactly_three_local_pairs_without_downloads(self):
        cases = local_cases(Path("synthetic_corpora_root"))
        self.assertEqual(len(cases), 3)
        self.assertEqual(len({case.family_source_key for case in cases}), 3)
        self.assertEqual(sum(case.reduction_path is not None for case in cases), 2)
        self.assertTrue(all("http" not in str(case.full_score_path) for case in cases))


if __name__ == "__main__":
    unittest.main()
