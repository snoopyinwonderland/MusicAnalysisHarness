from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from musicanote_harness.harmony_candidate_recall import (
    agreement, evaluate, fifths_spelling, fraction, paths_from_search,
    rational, reference_cells, run, select, source_signature, summarize,
)


def span(start=0, end=2):
    from fractions import Fraction
    return {"start": rational(Fraction(start)), "end": rational(Fraction(end))}


def annotation(aid="a", start=0, end=2, root="0", tones="0, 4, 1"):
    return {"annotation_id": aid, "source_asset_sha256": "annotation-source",
            "target": {"score_id": "score", "ir_document_id": "ir", "span": span(start, end)},
            "raw_fields": {"globalkey": "C", "localkey": "I", "localkey_is_minor": "0",
                           "root": root, "chord_tones": tones}}


def align(row):
    return {"annotation_id": row["annotation_id"], "target": deepcopy(row["target"]), "mapping_status": "exact"}


def search_fixture():
    groups, proposals = [], []
    for i, (root, members, raw) in enumerate(((["D", 0], [["D", 0], ["F", 0], ["A", 0]], 0),
                                             (["C", 0], [["C", 0], ["E", 0], ["G", 0]], 1))):
        adapter = {"edge": i, "reading": 0}
        groups.append({"group_id": str(i), "adapter_reading_key": adapter, "span": span(),
                       "root_spelling": root, "members": members})
        proposals.append({"proposal_id": "p" + str(i), "complete_context_path": True,
                          "semantic_group_refs": [str(i)], "path": [deepcopy(adapter)], "objective": {
                              "total_note_time": span(0, 6)["end"],
                              "raw_nonmember_note_time": span(0, raw)["end"],
                              "blocked_note_time": span(0, 0)["end"],
                              "spelling_unresolved_note_time": span(0, 0)["end"], "segment_count": 1}})
    return {"source_labels_used": False, "selected": None, "semantic_groups": groups, "proposals": proposals}


class CandidateRecallTests(unittest.TestCase):
    def test_exact_rational_and_spelling(self):
        self.assertEqual(fraction({"numerator": 1, "denominator": 3}) * 3, 1)
        self.assertEqual(fifths_spelling(-8), ("F", -1))
        self.assertEqual(fifths_spelling(7), ("C", 1))
        with self.assertRaises(ValueError):
            fraction({"numerator": True, "denominator": 1})

    def test_dcml_major_minor_and_applied_fifths(self):
        self.assertEqual(source_signature(annotation()), (("C", 0), (("C", 0), ("E", 0), ("G", 0))))
        row = annotation(root="2", tones="2, 6, 3, 1")
        row["raw_fields"].update(relativeroot="V", numeral="V", globalkey="F")
        self.assertEqual(source_signature(row)[0], ("G", 0))
        row = annotation(root="0", tones="0, -3, 1")
        row["raw_fields"].update(globalkey="f", localkey="i", localkey_is_minor="1")
        self.assertEqual(source_signature(row), (("F", 0), (("A", -1), ("C", 0), ("F", 0))))

    def test_pedal_not_silently_flattened(self):
        row = annotation(); row["raw_fields"]["pedal"] = "V"
        with self.assertRaisesRegex(ValueError, "pedal"):
            source_signature(row)

    def test_reference_gap_overlap_and_unverified_remain_in_denominator(self):
        row = annotation(end=1)
        cells = reference_cells(span(), [row], [align(row)])
        self.assertEqual([c["reason"] for c in cells], [None, "annotation_gap"])
        a, b = annotation(), annotation("b")
        self.assertEqual(reference_cells(span(), [a, b], [align(a), align(b)])[0]["reason"], "annotation_overlap")
        invalid = align(a); invalid["mapping_status"] = "ambiguous"
        self.assertEqual(reference_cells(span(), [a], [invalid])[0]["reason"], "unverified_or_mismatched_alignment")

    def test_reference_alignment_target_must_match(self):
        row = annotation(); mapped = align(row); mapped["target"]["span"] = span(1, 2)
        self.assertIsNone(reference_cells(span(), [row], [mapped])[0]["signature"])

    def test_candidate_present_but_baseline_wrong(self):
        row = annotation(); cells = reference_cells(span(), [row], [align(row)])
        paths = paths_from_search(search_fixture(), span())
        score = evaluate(paths, cells)
        self.assertTrue(score["candidate_hit"])
        self.assertFalse(score["selected_hit"])
        self.assertEqual(score["outcome"], "selection_error_with_reference_in_candidates")
        self.assertEqual(select(paths)["proposal_id"], "p0")

    def test_candidate_absent_and_zero_proposals_are_distinct(self):
        row = annotation(); cells = reference_cells(span(), [row], [align(row)])
        paths = paths_from_search(search_fixture(), span())[:1]
        self.assertFalse(evaluate(paths, cells)["candidate_hit"])
        self.assertEqual(evaluate(paths, cells)["outcome"], "reference_not_in_retained_candidates")
        self.assertEqual(evaluate([], cells)["outcome"], "no_proposals")

    def test_partial_reference_hit_is_null_not_false_or_true(self):
        row = annotation(end=1); cells = reference_cells(span(), [row], [align(row)])
        score = evaluate(paths_from_search(search_fixture(), span()), cells)
        self.assertIsNone(score["candidate_hit"])
        self.assertEqual(fraction(score["eligible_time"]), 1)
        self.assertEqual(fraction(score["context_time"]), 2)

    def test_enharmonic_member_set_does_not_match(self):
        row = annotation(); cells = reference_cells(span(), [row], [align(row)])
        paths = paths_from_search(search_fixture(), span())[1:]
        paths[0]["segments"][0]["signature"] = (("C", 0), (("C", 0), ("F", -1), ("G", 0)))
        root, members = agreement(paths[0], cells)
        self.assertEqual(root, 2); self.assertEqual(members, 0)

    def test_boundary_mismatch_lowers_time_agreement(self):
        left = annotation(end=1)
        right = annotation("b", 1, 2, root="2", tones="2, -1, 3")
        cells = reference_cells(span(), [left, right], [align(left), align(right)])
        paths = paths_from_search(search_fixture(), span())
        self.assertEqual(fraction(evaluate(paths, cells)["oracle_root_members_time"]), 1)

    def test_gold_cannot_change_selection(self):
        paths = paths_from_search(search_fixture(), span())
        for row in (annotation(), annotation(root="2", tones="2, -1, 3")):
            score = evaluate(paths, reference_cells(span(), [row], [align(row)]))
            self.assertEqual(score["selected_proposal_id"], "p0")

    def test_partition_references_and_cap_validated(self):
        fixture = search_fixture(); fixture["semantic_groups"][0]["span"] = span(1, 2)
        with self.assertRaisesRegex(ValueError, "partition"):
            paths_from_search(fixture, span())
        fixture = search_fixture(); fixture["proposals"] *= 13
        with self.assertRaisesRegex(ValueError, "24"):
            paths_from_search(fixture, span())
        fixture = search_fixture(); fixture["proposals"][0]["path"][0]["reading"] = 1
        with self.assertRaisesRegex(ValueError, "reference"):
            paths_from_search(fixture, span())

    def test_summary_denominators_and_all_abstention(self):
        row = annotation(); score = evaluate([], reference_cells(span(), [row], [align(row)]))
        summary = summarize([{"pair_id": "pair", "work_family_id": "family", "evaluation": score}])
        self.assertEqual(summary["recall_at_24"], 0)
        self.assertEqual(summary["selected_root_time_agreement"], 0)
        self.assertEqual(summarize([])["recall_at_24"], None)

    def test_runner_frozen_input_and_not_blind_test(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); previous = root / "previous"; previous.mkdir(); package = root / "package"; package.mkdir()
            row = annotation()
            (package / "imported_annotations.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            (package / "alignment_records.jsonl").write_text(json.dumps(align(row)) + "\n", encoding="utf-8")
            entry = {"package_path": str(package), "score_id": "score", "score_sha256": "score-source",
                     "annotation_sha256": "annotation-source", "work_family_id": "family", "split": "dev",
                     "rights": {"internal_research_use": True}}
            packet = {"pair_id": "pair", "plan_index": 0, "sample": {"sample_id": "sample", "span": span()},
                      "source_labels_used": False, "search": search_fixture(), "provenance": {
                          "manifest_entry": entry, "measure_revision_status": "not_required"}}
            artifact = previous / "sample.json.gz"; artifact.write_bytes(gzip.compress(json.dumps(packet).encode()))
            contract = previous / "run-contract.json"; contract.write_text(json.dumps({"search_config": {"max_complete_paths": 24}}))
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            record = {"pair_id": "pair", "plan_index": 0, "sample_id": "sample", "artifact": str(artifact), "sha256": digest(artifact)}
            report = previous / "report.json"; report.write_text(json.dumps({"complete": True, "source_labels_used": False,
                "inputs_and_code_unchanged": True, "artifacts_unchanged": True, "contract_sha256": digest(contract),
                "records": [record], "summary": {"samples": 1, "packages": 1, "work_families": 1}}))
            result = run(previous, root / "output", digest(report))
            self.assertEqual(result["summary"]["recall_at_24"], 1)
            self.assertFalse(result["blind_test_accuracy_measured"])
            self.assertFalse(result["source_labels_used_for_selection"])
            self.assertFalse(result["training_performed"])
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(previous, root / "output", digest(report))
            packet["provenance"]["manifest_entry"]["split"] = "holdout"
            artifact.write_bytes(gzip.compress(json.dumps(packet).encode()))
            data = json.loads(report.read_text()); data["records"][0]["sha256"] = digest(artifact); report.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "protected"):
                run(previous, root / "protected", digest(report))


if __name__ == "__main__":
    unittest.main()
