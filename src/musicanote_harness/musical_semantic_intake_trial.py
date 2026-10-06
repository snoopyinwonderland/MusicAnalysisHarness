"""Create a new local-only musical-semantic source intake and coverage trial.

Existing Core, annotations, corpora, package outputs and score viewers are not
modified.  Counts concern source files/statements and frozen legacy contexts,
not independent pieces, human-approved analysis or music-analysis accuracy.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from time import perf_counter
from typing import Any

from . import musical_semantic_enrichment as contract
from . import musical_semantic_intake as intake


VERSION = "musical-semantic-intake-trial-0.1.2"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_METADATA_BYTES = 16 * 1024 * 1024
_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA = _ROOT / "docs" / "harmony" / "schemas" / "musical_semantic_enrichment.schema.json"


def digest(path: str | Path) -> str:
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _token(*values: object) -> str:
    return hashlib.sha256("\x1f".join(str(value) for value in values).encode("utf-8")).hexdigest()[:24]


def _read_metadata(path: Path, hashes: dict[str, str], expected: str | None = None) -> dict[str, Any]:
    path = path.resolve(strict=True)
    if not path.is_file() or path.suffix != ".json" or path.stat().st_size > _MAX_METADATA_BYTES:
        raise ValueError("legacy_metadata_not_small_json:" + str(path))
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if expected is not None and (not _SHA256.fullmatch(expected) or actual != expected):
        raise ValueError("legacy_metadata_hash_mismatch:" + str(path))
    key = str(path)
    if key in hashes and hashes[key] != actual:
        raise ValueError("legacy_metadata_changed_while_loading:" + key)
    hashes[key] = actual
    result = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError("legacy_metadata_not_object:" + key)
    return result


def _expected_hash(hashes: dict[str, Any], path: Path) -> str | None:
    matches = [value for name, value in hashes.items()
               if Path(name).resolve() == path.resolve()]
    if len(matches) > 1 or (matches and not _SHA256.fullmatch(str(matches[0]))):
        raise ValueError("legacy_metadata_ambiguous_expected_hash:" + str(path))
    return matches[0] if matches else None


def _legacy_descriptors(report_path: Path, hashes: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Index small frozen metadata; never decode or reparse bundle gzip files."""
    report_path = report_path.resolve(strict=True)
    report = _read_metadata(report_path, hashes)
    for field in ("complete", "inputs_and_code_unchanged", "artifacts_unchanged"):
        if report.get(field) is not True:
            raise ValueError("legacy_report_not_complete_or_frozen")
    rows = report.get("records")
    revisions = report.get("measure_revisions")
    summary = report.get("summary", {})
    if not isinstance(rows, list) or not isinstance(revisions, list) or not isinstance(summary, dict):
        raise ValueError("legacy_report_inventory_missing")
    parents = {}
    for row in revisions:
        pair = row.get("pair_id")
        if not isinstance(pair, str) or not pair or pair in parents:
            raise ValueError("legacy_package_inventory_mismatch")
        if not isinstance(row.get("working_ir_document_id"), str) or not row["working_ir_document_id"]:
            raise ValueError("legacy_working_ir_id_missing")
        parents[pair] = row
    if type(summary.get("packages")) is not int or summary["packages"] != len(parents):
        raise ValueError("legacy_package_inventory_mismatch")
    if type(summary.get("samples")) is not int or summary["samples"] != len(rows):
        raise ValueError("legacy_context_inventory_mismatch")

    inherited = {}
    provenance_status = "unknown_no_accessible_frozen_manifest"
    old_contract_path = report_path.parent / "run-contract.json"
    expected_contract = report.get("contract_sha256")
    old_contract = None
    if old_contract_path.is_file() and expected_contract is not None:
        old_contract = _read_metadata(old_contract_path, hashes, expected_contract)
        breadth = old_contract.get("breadth_trial")
        frozen_plan_path = Path(breadth) / "frozen-plan.json" if isinstance(breadth, str) else None
        if frozen_plan_path is not None and frozen_plan_path.is_file():
            expected_plan = _expected_hash(old_contract.get("input_hashes", {}), frozen_plan_path)
            if expected_plan is not None:
                plan = _read_metadata(frozen_plan_path, hashes, expected_plan)
                packages = plan.get("packages", [])
                if not isinstance(packages, list):
                    raise ValueError("legacy_frozen_plan_packages_invalid")
                for package in packages:
                    pair = package.get("pair_id")
                    if pair in inherited:
                        raise ValueError("legacy_frozen_plan_duplicate_package")
                    if pair not in parents:
                        continue
                    entry = package.get("source", {}).get("manifest_entry")
                    if not isinstance(entry, dict) or entry.get("ir_document_id") != parents[pair].get("parent_ir_document_id"):
                        raise ValueError("legacy_manifest_parent_binding_mismatch")
                    inherited[pair] = {
                        "manifest_entry": deepcopy(entry),
                        "manifest_ref": str(frozen_plan_path.resolve()),
                        "manifest_sha256": expected_plan,
                        "manifest_provenance_status": "inherited_hash_verified_metadata_not_new_permission",
                    }
                provenance_status = "inherited_where_frozen_parent_binding_is_verified"

    descriptors = []
    seen = set()
    seen_pairs = set()
    inherited_artifacts = report.get("artifact_hashes", {})
    if not isinstance(inherited_artifacts, dict):
        raise ValueError("legacy_artifact_hash_inventory_invalid")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("legacy_context_record_invalid")
        pair = row.get("pair_id")
        sample = row.get("sample_id")
        index = row.get("plan_index")
        if pair not in parents or not isinstance(sample, str) or not sample or type(index) is not int or index < 0:
            raise ValueError("legacy_context_identity_invalid")
        identity = pair, index, sample
        if identity in seen or row.get("working_ir_document_id") != parents[pair]["working_ir_document_id"]:
            raise ValueError("legacy_context_inventory_or_ir_binding_mismatch")
        seen.add(identity)
        seen_pairs.add(pair)
        artifact = row.get("artifact")
        sha256 = row.get("sha256")
        if not isinstance(artifact, str) or not artifact or not isinstance(sha256, str) or not _SHA256.fullmatch(sha256):
            raise ValueError("legacy_context_artifact_ref_invalid")
        if inherited_artifacts.get(artifact) != sha256:
            raise ValueError("legacy_context_artifact_manifest_mismatch")
        source_revision = "sha256:" + sha256
        descriptors.append({
            "case_id": "legacy_context_" + _token(*identity, sha256),
            "case_kind": "legacy_frozen_context_not_independent_piece",
            "case_sha256": sha256,
            "source_refs": [{"source_ref": artifact, "source_revision": source_revision, "source_sha256": sha256}],
            "pair_id": pair,
            "sample_id": sample,
            "plan_index": index,
            "ir_ref": row["working_ir_document_id"],
            "ir_sha256": None,
            "requires_alignment_before_bound": True,
            "new_sidecar_status": "not_assessed",
            "missing_reason": "new_musical_semantic_sidecar_not_yet_assessed",
            "legacy_musical_data_absent": False,
            "legacy_status_preserved": row.get("status"),
            "legacy_previous_status_preserved": row.get("previous_status"),
            "legacy_report_ref": str(report_path),
            "legacy_report_sha256": hashes[str(report_path)],
            "legacy_artifact_hash_origin": "inherited_report_manifest_not_recomputed",
            "legacy_bundle_bytes_reverified": False,
            "rights_and_split_provenance": deepcopy(inherited.get(pair, {
                "manifest_entry": None,
                "manifest_provenance_status": "unknown_no_accessible_frozen_manifest",
            })),
        })
    if seen_pairs != set(parents):
        raise ValueError("legacy_package_context_coverage_mismatch")
    return descriptors, {
        "report_ref": str(report_path),
        "report_sha256": hashes[str(report_path)],
        "registered_packages": len(parents),
        "registered_contexts": len(descriptors),
        "work_families_inherited_report_count": summary.get("work_families"),
        "new_sidecar_status": "not_assessed",
        "legacy_musical_data_absent": False,
        "provenance_status": provenance_status,
        "contexts_with_inherited_manifest": sum(row["pair_id"] in inherited for row in rows),
        "bundle_gzip_decoded": False,
        "bundle_bytes_reverified": False,
        "registered_contexts_are_independent_pieces": False,
    }


def _discover(corpus_root: Path) -> list[Path]:
    paths = []
    for path in corpus_root.rglob("analysis.txt"):
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        if path.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError("source_reparse_point_not_supported:" + str(path))
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(corpus_root):
            raise ValueError("source_path_outside_corpus_root:" + str(path))
        if not resolved.is_file():
            raise ValueError("source_analysis_path_not_file:" + str(path))
        paths.append(resolved)
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate_resolved_source_paths")
    return sorted(paths, key=lambda path: path.relative_to(corpus_root).as_posix())


def _preflight(corpus_root: str | Path, output: str | Path) -> tuple[Path, Path, list[Path]]:
    raw_output = Path(output).absolute()
    if os.path.lexists(raw_output):
        raise ValueError("output_exists_no_overwrite")
    root = Path(corpus_root).resolve(strict=True)
    destination = raw_output.resolve()
    if not root.is_dir():
        raise ValueError("corpus_root_not_directory")
    if destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError("output_overlaps_read_only_corpus")
    for protected in (_ROOT / "src", _ROOT / "tests", _ROOT / "MUSICANOTE_Canonical_Music_IR",
                      _ROOT / ".git", _ROOT / ".agents", _ROOT / ".codex"):
        if destination.is_relative_to(protected.resolve()):
            raise ValueError("output_overlaps_implementation_or_metadata")
    files = _discover(root)
    if not files:
        raise ValueError("no_analysis_txt_sources_discovered")
    return root, destination, files


def _write_new(path: Path, value: Any, *, jsonl: bool = False) -> None:
    """Exclusive creation, including within this new immutable trial directory."""
    if jsonl:
        text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in value)
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def _coverage_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_axis: dict[str, Counter[str]] = {}
    for row in rows:
        for axis, state in row["axis_states"].items():
            # Planner state values are part of the contract, not a new inference.
            name = state if isinstance(state, str) else state["state"]
            by_axis.setdefault(axis, Counter())[name] += 1
    return {
        "cases": len(rows),
        "axis_states": {axis: dict(sorted(states.items())) for axis, states in sorted(by_axis.items())},
        "missing_axes": dict(sorted(Counter(axis for row in rows for axis in row["missing_axes"]).items())),
        "scope": "new_musical_semantic_contract_coverage_only_not_absence_of_legacy_music_analysis",
    }


def run(
    corpus_root: str | Path,
    output: str | Path,
    *,
    context_radius: int = 2,
    legacy_report: str | Path | None = None,
) -> dict[str, Any]:
    configuration = intake.intake_configuration(context_radius)
    config_sha256 = intake.configuration_sha256(configuration)
    root, destination, files = _preflight(corpus_root, output)
    started = perf_counter()
    source_hashes = {str(path): digest(path) for path in files}
    metadata_hashes: dict[str, str] = {}
    legacy_cases, legacy_summary = ([], {"registered_packages": 0, "registered_contexts": 0,
                                      "new_sidecar_status": "not_assessed", "legacy_report_supplied": False})
    if legacy_report is not None:
        legacy_path = Path(legacy_report).resolve(strict=True)
        if destination.is_relative_to(legacy_path.parent):
            raise ValueError("output_overlaps_read_only_legacy_trial")
        legacy_cases, legacy_summary = _legacy_descriptors(legacy_path, metadata_hashes)
    schema_path = Path(getattr(contract, "SCHEMA_PATH", _SCHEMA)).resolve(strict=True)
    code_paths = [Path(__file__).resolve(), Path(intake.__file__).resolve(), Path(contract.__file__).resolve(), schema_path]
    code_hashes = {str(path): digest(path) for path in sorted(code_paths)}
    records, source_cases, inventory = [], [], []
    for number, path in enumerate(files, 1):
        prepared = intake.prepare_source_statements(path, corpus_root=root, context_radius=context_radius,
                                                  expected_sha256=source_hashes[str(path)])
        if prepared["configuration"] != configuration or prepared["configuration_sha256"] != config_sha256:
            raise ValueError("source_intake_configuration_mismatch")
        records.extend(prepared["records"])
        source_cases.append(prepared["case"])
        inventory.append(prepared["source"])
        if number % 200 == 0 or number == len(files):
            print(f"[{number}/{len(files)}] source files; {len(records)} preserved native statements", flush=True)
    all_cases = source_cases + legacy_cases
    if len({row["case_id"] for row in all_cases}) != len(all_cases):
        raise ValueError("duplicate_intake_case_ids")
    contract.validate_records(records, legacy_cases=all_cases)
    source_coverage = contract.plan_coverage(source_cases, records)
    legacy_coverage = contract.plan_coverage(legacy_cases, records) if legacy_cases else []
    counts = {tag: sum(row["statement_counts_by_native_tag"][tag] for row in inventory)
              for tag in intake.SOURCE_TAG_AXES}
    if sum(counts.values()) != len(records):
        raise ValueError("source_statement_accounting_mismatch")
    plan = {
        "version": VERSION,
        "intake_version": intake.VERSION,
        "intake_configuration": configuration,
        "intake_configuration_sha256": config_sha256,
        "contract_version": contract.VERSION,
        "contract_schema_name": contract.SCHEMA_NAME,
        "contract_schema_version": contract.SCHEMA_VERSION,
        "vocabulary_version": contract.VOCABULARY_VERSION,
        "corpus_root": str(root),
        "output": str(destination),
        "selection": "all discovered analysis.txt files; all case-insensitive native Note:/Form:/Pedal: physical source statement lines",
        "source_input_hashes": source_hashes,
        "legacy_metadata_hashes": metadata_hashes,
        "implementation_hashes": code_hashes,
        "context_radius": context_radius,
        "source_snapshot_layout": "flat_relative_path_and_content_hash_keyed",
        "source_files": len(files),
        "source_statements": len(records),
        "statement_counts_by_native_tag": counts,
        "source_files_by_native_tag": {tag: sum(row["statement_counts_by_native_tag"][tag] > 0 for row in inventory)
                                      for tag in intake.SOURCE_TAG_AXES},
        "legacy_registration": legacy_summary,
        "tag_routing_policy": {"Form": "form_role", "Pedal": "harmonic_role", "Note": "unclassified_source_prose"},
        "native_tag_matching": "case_insensitive_canonical_routing_original_spelling_preserved",
        "native_tags_are_observations_not_new_human_approved_analysis": True,
        "measure_neighbors_are_context_not_target": True,
        "full_score_xml_context_status": "missing_not_aligned",
        "training_promoted": False,
        "gold_promoted": False,
        "rights_or_split_changed": False,
        "external_transmission": False,
        "source_or_core_modified": False,
        "legacy_outputs_modified": False,
        "score_viewer_modified": False,
        "musical_accuracy_measured": False,
        "keyword_music_classification_performed": False,
        "nlp_or_api_calls_performed": False,
    }
    # No write happens before all path, source/hash, schema and legacy metadata
    # checks above succeed.  Failed postflight checks retain only a NEW local
    # artifact marked incomplete; no existing path is ever cleaned or replaced.
    destination.mkdir(parents=True, exist_ok=False)
    values = {
        "run-plan.json": plan,
        "source-inventory.json": inventory,
        "source-case-descriptors.json": source_cases,
        "legacy-case-descriptors.json": legacy_cases,
        "source-coverage.json": source_coverage,
        "legacy-coverage.json": legacy_coverage,
        "provenance-snapshot.json": {
            "version": VERSION,
            "source_inputs": [{"path": row["path"], "relative_path": row["relative_path"],
                               "sha256": row["sha256"], "size_bytes": row["size_bytes"]} for row in inventory],
            "legacy_metadata_hashes": metadata_hashes,
            "implementation_hashes": code_hashes,
            "snapshot_kind": "read_only_original_path_and_full_bytes_hash_no_source_rewrite",
        },
    }
    artifact_hashes = {}
    source_snapshots = []
    for row in inventory:
        # Preserve complete byte-identical files for multiline prose and future
        # alignment, not just the immediate line snippets in SOURCE records.
        # A corpus-relative hierarchy can fit at its original root but exceed
        # Windows MAX_PATH under a longer trial root.  Keep filenames short and
        # deterministic, with the complete original hierarchy in the manifest.
        # Include relative path as well as content hash: duplicated source bytes
        # at distinct original locations remain distinct snapshot mappings.
        snapshot_key = _token(row["relative_path"], row["sha256"])
        snapshot_path = destination / "source-snapshot" / (snapshot_key + ".txt")
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = Path(row["path"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ValueError("source_changed_before_snapshot:" + row["path"])
        with snapshot_path.open("xb") as stream:
            stream.write(payload)
        snapshot_sha256 = digest(snapshot_path)
        if snapshot_sha256 != row["sha256"]:
            raise ValueError("source_snapshot_not_byte_identical:" + row["path"])
        artifact_hashes[str(snapshot_path)] = snapshot_sha256
        source_snapshots.append({"original_path": row["path"], "relative_path": row["relative_path"],
                                 "source_sha256": row["sha256"], "snapshot_path": str(snapshot_path),
                                 "snapshot_key": snapshot_key, "snapshot_sha256": snapshot_sha256,
                                 "size_bytes": row["size_bytes"]})
    values["provenance-snapshot.json"]["byte_identical_source_snapshots"] = source_snapshots
    values["provenance-snapshot.json"]["snapshot_kind"] = "byte_identical_local_source_copies_plus_original_paths_and_full_bytes_hashes"
    for name, value in values.items():
        path = destination / name
        _write_new(path, value)
        artifact_hashes[str(path)] = digest(path)
    record_path = destination / "source-statements.jsonl"
    _write_new(record_path, records, jsonl=True)
    artifact_hashes[str(record_path)] = digest(record_path)
    tracked = {**source_hashes, **metadata_hashes, **code_hashes}
    changed_inputs = [name for name, expected in tracked.items()
                      if not Path(name).is_file() or digest(name) != expected]
    discovered_after = {str(path) for path in _discover(root)}
    changed_inputs.extend(sorted(discovered_after.symmetric_difference(source_hashes)))
    changed_artifacts = [name for name, expected in artifact_hashes.items()
                         if not Path(name).is_file() or digest(name) != expected]
    report = {
        "version": VERSION,
        "complete": not changed_inputs and not changed_artifacts,
        "summary": {
            "source_files": len(files),
            "source_files_with_statements": sum(row["source_statements"] > 0 for row in inventory),
            "source_statements": len(records),
            "statement_counts_by_native_tag": counts,
            "source_files_by_native_tag": plan["source_files_by_native_tag"],
            "unclassified_source_prose": counts["Note"],
            "source_file_coverage": _coverage_summary(source_coverage),
            "legacy_context_coverage": _coverage_summary(legacy_coverage),
            "legacy_registration": legacy_summary,
            "aligned_source_statements": 0,
            "human_validated_source_statements": 0,
            "training_eligible_source_statements": 0,
            "gold_eligible_source_statements": 0,
            "independent_piece_count": None,
        },
        "plan_sha256": artifact_hashes[str(destination / "run-plan.json")],
        "artifact_hashes": artifact_hashes,
        "inputs_and_code_unchanged": not changed_inputs,
        "artifacts_unchanged": not changed_artifacts,
        "changed_input_paths": sorted(set(changed_inputs)),
        "changed_artifact_paths": changed_artifacts,
        **{field: plan[field] for field in ("training_promoted", "gold_promoted", "rights_or_split_changed",
                                           "external_transmission", "source_or_core_modified",
                                           "legacy_outputs_modified", "score_viewer_modified",
                                           "musical_accuracy_measured", "keyword_music_classification_performed",
                                           "nlp_or_api_calls_performed")},
        "elapsed_seconds": perf_counter() - started,
        "limits": [
            "Native source tags are routing observations, not newly approved music analysis.",
            "Note prose remains unclassified and may concern multiple axes or non-musical metadata.",
            "Nearby measure lines are context only; no notes, phrases, score spans or XML targets were assigned.",
            "Full score/XML context is not aligned; future binding must retain the original immutable source statements.",
            "Legacy not_assessed means missing new-contract sidecars, not absence of previous musical evidence.",
            "Source files/statements and legacy contexts are not counts of independent pieces or accuracy.",
            "No rights, training, gold, external-sharing, production Core or viewer permission is granted.",
        ],
    }
    _write_new(destination / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--context-radius", type=int, default=2)
    parser.add_argument("--legacy-report")
    args = parser.parse_args()
    report = run(args.corpus_root, args.output, context_radius=args.context_radius, legacy_report=args.legacy_report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
