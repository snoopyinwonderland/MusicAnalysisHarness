"""Immutable local intake accounting, path guards, and honest legacy coverage."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from musicanote_harness import musical_semantic_enrichment as contract
from musicanote_harness import musical_semantic_intake_trial as trial
from test_musical_semantic_intake import source


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fixture(root: Path):
    corpus = root / "Corpus"
    paths = [source(corpus, b"Note: melody and bass\nm1 I\nForm: A\nm2 V\nPedal: C\n"),
             source(corpus, b"m1 I\n", "composer/other/analysis.txt")]
    return {"corpus": corpus, "sources": paths, "output": root / "NEW"}


def legacy_fixture(root: Path, *, with_manifest=False):
    previous = root / "legacy"
    previous.mkdir()
    # This intentionally is not a valid gzip. Intake must never decode it or
    # reinterpret its inherited hash as an immutable IR hash.
    artifact = previous / "bundle.json.gz"
    artifact.write_bytes(b"must not be read or decompressed by semantic intake")
    row = {"pair_id": "pair", "sample_id": "sample", "plan_index": 0,
           "working_ir_document_id": "working_ir", "artifact": str(artifact),
           "sha256": trial.digest(artifact), "status": "assembled", "previous_status": "prior_abstention"}
    old_contract = {"input_hashes": {}}
    if with_manifest:
        plan_path = root / "breadth" / "frozen-plan.json"
        entry = {"ir_document_id": "parent_ir", "score_id": "score", "score_sha256": "1" * 64,
                 "split": "holdout", "work_family_id": "family", "rights": {
                     "internal_research_use": True, "model_training_approved": False,
                     "external_api_transmission_approved": False, "redistribution_approved": False}}
        write_json(plan_path, {"packages": [{"pair_id": "pair", "source": {"manifest_entry": entry}}]})
        old_contract = {"breadth_trial": str(plan_path.parent), "input_hashes": {str(plan_path): trial.digest(plan_path)}}
    contract_path = previous / "run-contract.json"
    write_json(contract_path, old_contract)
    report = {"complete": True, "inputs_and_code_unchanged": True, "artifacts_unchanged": True,
              "contract_sha256": trial.digest(contract_path), "summary": {"packages": 1, "samples": 1, "work_families": 1},
              "measure_revisions": [{"pair_id": "pair", "parent_ir_document_id": "parent_ir", "working_ir_document_id": "working_ir"}],
              "records": [row], "artifact_hashes": {str(artifact): row["sha256"]}}
    report_path = previous / "report.json"
    write_json(report_path, report)
    return {"report": report_path, "artifact": artifact, "contract": contract_path,
            "plan": root / "breadth" / "frozen-plan.json"}


class MusicalSemanticIntakeTrialTests(unittest.TestCase):
    def test_new_trial_exact_counts_complete_snapshots_and_no_old_mutation(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            before = {path: path.read_bytes() for path in data["sources"]}
            result = trial.run(data["corpus"], data["output"])
            self.assertTrue(result["complete"])
            self.assertTrue(result["inputs_and_code_unchanged"])
            self.assertTrue(result["artifacts_unchanged"])
            self.assertEqual(result["summary"]["source_files"], 2)
            self.assertEqual(result["summary"]["source_files_with_statements"], 1)
            self.assertEqual(result["summary"]["source_statements"], 3)
            self.assertEqual(result["summary"]["statement_counts_by_native_tag"], {"Note": 1, "Form": 1, "Pedal": 1})
            self.assertEqual(result["summary"]["source_files_by_native_tag"], {"Note": 1, "Form": 1, "Pedal": 1})
            self.assertEqual(result["summary"]["aligned_source_statements"], 0)
            self.assertEqual(result["summary"]["human_validated_source_statements"], 0)
            self.assertIsNone(result["summary"]["independent_piece_count"])
            snapshot_manifest = read_json(data["output"] / "provenance-snapshot.json")
            snapshot_by_original = {row["original_path"]: row for row in snapshot_manifest["byte_identical_source_snapshots"]}
            for path, payload in before.items():
                self.assertEqual(path.read_bytes(), payload)
                mapping = snapshot_by_original[str(path.resolve())]
                self.assertEqual(Path(mapping["snapshot_path"]).read_bytes(), payload)
                self.assertEqual(mapping["relative_path"], path.relative_to(data["corpus"]).as_posix())
            records = contract.load_records(data["output"] / "source-statements.jsonl")
            self.assertEqual(len(records), 3)
            self.assertEqual([row["claim"]["term"] for row in records], [None, None, None])
            plan = read_json(data["output"] / "run-plan.json")
            independently_hashed_config = hashlib.sha256(json.dumps(plan["intake_configuration"],
                ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
            self.assertEqual(plan["intake_configuration_sha256"], independently_hashed_config)
            self.assertEqual(plan["intake_configuration"]["context_radius"], plan["context_radius"])
            for row in records:
                self.assertEqual(row["provenance"]["producer"]["name"], "musical-semantic-source-intake")
                self.assertEqual(row["provenance"]["producer"]["version"], plan["intake_version"])
                self.assertEqual(row["provenance"]["producer"]["config_sha256"], independently_hashed_config)
            for name, sha in result["artifact_hashes"].items():
                self.assertEqual(trial.digest(name), sha)
            self.assertEqual(result["plan_sha256"], trial.digest(data["output"] / "run-plan.json"))
            snapshot = read_json(data["output"] / "provenance-snapshot.json")
            self.assertEqual(len(snapshot["byte_identical_source_snapshots"]), 2)
            self.assertEqual(len(snapshot["implementation_hashes"]), 4)
            self.assertEqual(read_json(data["output"] / "legacy-case-descriptors.json"), [])
            for flag in ("training_promoted", "gold_promoted", "external_transmission", "source_or_core_modified",
                         "legacy_outputs_modified", "score_viewer_modified", "musical_accuracy_measured",
                         "keyword_music_classification_performed", "nlp_or_api_calls_performed"):
                self.assertFalse(result[flag])

    def test_long_relative_source_path_uses_short_flat_snapshot_and_exact_manifest_mapping(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "Corpus"
            # The original fits a conservative Windows path budget, while
            # copying its hierarchy below a longer trial root would not.
            component_size = 245 - len(str(corpus)) - len("/analysis.txt") - 1
            relative = "long_" + "a" * (component_size - len("long_")) + "/analysis.txt"
            payload = b"Note: complete original long-path source\ncontinued source text\n"
            original = source(corpus, payload, relative)
            output = root / "new-long-output-root-name"
            self.assertGreaterEqual(len(str(output / "source-snapshot" / relative)), 260)
            result = trial.run(corpus, output)
            self.assertTrue(result["complete"])
            mapping = read_json(output / "provenance-snapshot.json")["byte_identical_source_snapshots"][0]
            snapshot = Path(mapping["snapshot_path"])
            self.assertEqual(snapshot.parent, output / "source-snapshot")
            self.assertEqual(len(snapshot.name), 28)
            self.assertLess(len(str(snapshot)), 260)
            self.assertEqual(mapping["relative_path"], relative)
            self.assertEqual(mapping["original_path"], str(original.resolve()))
            self.assertEqual(mapping["source_sha256"], mapping["snapshot_sha256"])
            self.assertEqual(snapshot.read_bytes(), payload)
            self.assertEqual(original.read_bytes(), payload)
            self.assertEqual(read_json(output / "run-plan.json")["source_snapshot_layout"],
                             "flat_relative_path_and_content_hash_keyed")

    def test_byte_identical_sources_at_different_paths_get_distinct_stable_snapshot_keys(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "Corpus"
            payload = b"Note: duplicated source bytes\n"
            source(corpus, payload, "first/analysis.txt")
            source(corpus, payload, "second/analysis.txt")
            first_output = root / "first-new-output"
            second_output = root / "second-new-output"
            trial.run(corpus, first_output)
            trial.run(corpus, second_output)
            first = read_json(first_output / "provenance-snapshot.json")["byte_identical_source_snapshots"]
            second = read_json(second_output / "provenance-snapshot.json")["byte_identical_source_snapshots"]
            self.assertEqual(len({row["snapshot_key"] for row in first}), 2)
            self.assertEqual({row["source_sha256"] for row in first}, {trial.digest(corpus / "first" / "analysis.txt")})
            self.assertEqual({row["relative_path"]: row["snapshot_key"] for row in first},
                             {row["relative_path"]: row["snapshot_key"] for row in second})

    def test_legacy_is_missing_new_sidecars_not_missing_previous_music_or_ir_hash(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root)
            old = legacy_fixture(root)
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            result = trial.run(data["corpus"], data["output"], legacy_report=old["report"])
            descriptor = read_json(data["output"] / "legacy-case-descriptors.json")[0]
            self.assertIsNone(descriptor["ir_sha256"])
            self.assertEqual(descriptor["ir_ref"], "working_ir")
            self.assertEqual(descriptor["source_refs"][0]["source_sha256"], trial.digest(old["artifact"]))
            self.assertEqual(descriptor["legacy_artifact_hash_origin"], "inherited_report_manifest_not_recomputed")
            self.assertFalse(descriptor["legacy_bundle_bytes_reverified"])
            self.assertFalse(descriptor["legacy_musical_data_absent"])
            self.assertEqual(descriptor["rights_and_split_provenance"]["manifest_provenance_status"], "unknown_no_accessible_frozen_manifest")
            coverage = read_json(data["output"] / "legacy-coverage.json")[0]
            self.assertEqual(set(coverage["axis_states"].values()), {"not_assessed"})
            self.assertEqual(set(coverage["missing_axes"]), set(contract.AXES))
            self.assertEqual(result["summary"]["legacy_registration"]["registered_contexts"], 1)
            self.assertEqual(result["summary"]["legacy_registration"]["registered_packages"], 1)
            self.assertEqual(result["summary"]["source_file_coverage"]["cases"], 2)
            self.assertEqual(result["summary"]["legacy_context_coverage"]["cases"], 1)
            for path, payload in before.items():
                self.assertEqual(path.read_bytes(), payload)

    def test_accessible_hash_verified_manifest_rights_and_split_are_preserved_not_upgraded(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root)
            old = legacy_fixture(root, with_manifest=True)
            result = trial.run(data["corpus"], data["output"], legacy_report=old["report"])
            descriptor = read_json(data["output"] / "legacy-case-descriptors.json")[0]
            provenance = descriptor["rights_and_split_provenance"]
            self.assertEqual(provenance["manifest_entry"]["split"], "holdout")
            self.assertFalse(provenance["manifest_entry"]["rights"]["model_training_approved"])
            self.assertEqual(provenance["manifest_sha256"], trial.digest(old["plan"]))
            self.assertEqual(result["summary"]["legacy_registration"]["contexts_with_inherited_manifest"], 1)
            self.assertFalse(result["rights_or_split_changed"])
            self.assertFalse(result["training_promoted"])

    def test_no_overwrite_precedes_missing_input_reads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "marker"
            marker.write_bytes(b"keep")
            with self.assertRaisesRegex(ValueError, "output_exists_no_overwrite"):
                trial.run(root / "missing", root)
            self.assertEqual(marker.read_bytes(), b"keep")

    def test_output_may_not_overlap_readonly_corpus_or_implementation(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError, "output_overlaps_read_only_corpus"):
                trial.run(data["corpus"], data["corpus"] / "new")
            with self.assertRaisesRegex(ValueError, "output_overlaps_implementation_or_metadata"):
                trial.run(data["corpus"], trial._ROOT / "src" / "new-semantic-output")
            self.assertFalse((data["corpus"] / "new").exists())

    def test_empty_source_inventory_is_not_silently_successful(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty = root / "Corpus"
            empty.mkdir()
            with self.assertRaisesRegex(ValueError, "no_analysis_txt_sources_discovered"):
                trial.run(empty, root / "new")
            self.assertFalse((root / "new").exists())

    def test_new_output_cannot_be_created_inside_previous_trial(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root)
            old = legacy_fixture(root)
            destination = old["report"].parent / "nested-new"
            with self.assertRaisesRegex(ValueError, "output_overlaps_read_only_legacy_trial"):
                trial.run(data["corpus"], destination, legacy_report=old["report"])
            self.assertFalse(destination.exists())

    def test_legacy_report_contract_hash_and_context_denominator_are_checked_before_writes(self):
        mutations = [
            lambda value: value.update(complete=False),
            lambda value: value.update(contract_sha256="0" * 64),
            lambda value: value["summary"].update(samples=2),
            lambda value: value["records"].append(deepcopy(value["records"][0])),
            lambda value: value["records"][0].update(working_ir_document_id="unrelated"),
            lambda value: value["records"][0].update(sha256="0" * 64),
        ]
        for mutation in mutations:
            with TemporaryDirectory() as tmp:
                root = Path(tmp)
                data = fixture(root)
                old = legacy_fixture(root)
                value = read_json(old["report"])
                mutation(value)
                write_json(old["report"], value)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    trial.run(data["corpus"], data["output"], legacy_report=old["report"])
                self.assertFalse(data["output"].exists())

    def test_changed_frozen_provenance_cannot_be_inherited(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root)
            old = legacy_fixture(root, with_manifest=True)
            value = read_json(old["plan"])
            value["packages"][0]["source"]["manifest_entry"]["split"] = "train"
            write_json(old["plan"], value)
            with self.assertRaisesRegex(ValueError, "legacy_metadata_hash_mismatch"):
                trial.run(data["corpus"], data["output"], legacy_report=old["report"])
            self.assertFalse(data["output"].exists())

    def test_manifest_parent_binding_is_not_retargeted_to_working_ir(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture(root)
            old = legacy_fixture(root, with_manifest=True)
            value = read_json(old["plan"])
            value["packages"][0]["source"]["manifest_entry"]["ir_document_id"] = "working_ir"
            write_json(old["plan"], value)
            contract_value = read_json(old["contract"])
            contract_value["input_hashes"][str(old["plan"])] = trial.digest(old["plan"])
            write_json(old["contract"], contract_value)
            report_value = read_json(old["report"])
            report_value["contract_sha256"] = trial.digest(old["contract"])
            write_json(old["report"], report_value)
            with self.assertRaisesRegex(ValueError, "legacy_manifest_parent_binding_mismatch"):
                trial.run(data["corpus"], data["output"], legacy_report=old["report"])

    def test_bad_encoding_fails_before_any_output_write(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            data["sources"][0].write_bytes(b"Note: invalid \xff")
            with self.assertRaisesRegex(ValueError, "source_not_utf8"):
                trial.run(data["corpus"], data["output"])
            self.assertFalse(data["output"].exists())

    def test_each_artifact_is_exclusively_created_and_repeat_trial_refuses_output(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            trial.run(data["corpus"], data["output"])
            report_before = (data["output"] / "report.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "output_exists_no_overwrite"):
                trial.run(data["corpus"], data["output"])
            self.assertEqual((data["output"] / "report.json").read_bytes(), report_before)
            with self.assertRaises(FileExistsError):
                trial._write_new(data["output"] / "report.json", {"changed": True})
            self.assertEqual((data["output"] / "report.json").read_bytes(), report_before)

    def test_source_change_during_trial_cannot_mark_complete(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            original = trial._write_new
            def write_then_mutate(path, value, **kwargs):
                original(path, value, **kwargs)
                if path.name == "source-statements.jsonl":
                    data["sources"][0].write_bytes(b"Note: changed by outside test writer\n")
            with patch.object(trial, "_write_new", side_effect=write_then_mutate):
                result = trial.run(data["corpus"], data["output"])
            self.assertFalse(result["complete"])
            self.assertFalse(result["inputs_and_code_unchanged"])
            self.assertIn(str(data["sources"][0].resolve()), result["changed_input_paths"])

    def test_new_source_discovered_during_trial_is_not_omitted_from_postflight(self):
        with TemporaryDirectory() as tmp:
            data = fixture(Path(tmp))
            original = trial._write_new
            def write_then_add(path, value, **kwargs):
                original(path, value, **kwargs)
                if path.name == "source-statements.jsonl":
                    source(data["corpus"], b"Form: added\n", "later/analysis.txt")
            with patch.object(trial, "_write_new", side_effect=write_then_add):
                result = trial.run(data["corpus"], data["output"])
            self.assertFalse(result["complete"])
            self.assertIn(str((data["corpus"] / "later" / "analysis.txt").resolve()), result["changed_input_paths"])


if __name__ == "__main__":
    unittest.main()
