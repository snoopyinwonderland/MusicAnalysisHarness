"""Read-only independent physical-line/hash accounting for a semantic intake.

Does not use the intake parser to reconstruct expected statement locations.
Checks storage and provenance only, not musical truth or generation readiness.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any

from . import musical_semantic_enrichment as contract


VERSION = "musical-semantic-intake-audit-0.1.0"
_TAGS = {"note": "Note", "form": "Form", "pedal": "Pedal"}
_TAG = re.compile(r"^\s*(note|form|pedal):", re.IGNORECASE)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("semantic_intake_audit:" + message)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _lines(payload: bytes) -> list[tuple[str, str]]:
    # Universal physical CR/LF iteration; unlike splitlines(), Unicode text
    # separators inside the source prose are not additional physical lines.
    result = []
    with io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8", newline="") as stream:
        for text in stream:
            ending = "\r\n" if text.endswith("\r\n") else (
                "\n" if text.endswith("\n") else "\r" if text.endswith("\r") else "")
            result.append((text[:-len(ending)] if ending else text, ending))
    return result


def audit(directory: str | Path) -> dict[str, Any]:
    folder = Path(directory).resolve(strict=True)
    report = _read(folder / "report.json")
    plan = _read(folder / "run-plan.json")
    _require(report.get("complete") is True, "incomplete_run")
    _require(report.get("inputs_and_code_unchanged") is True, "input_postflight_failed")
    _require(report.get("artifacts_unchanged") is True, "artifact_postflight_failed")
    _require(_digest(folder / "run-plan.json") == report["plan_sha256"], "plan_hash")
    configuration = plan["intake_configuration"]
    configuration_sha256 = hashlib.sha256(json.dumps(configuration, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    _require(configuration_sha256 == plan["intake_configuration_sha256"], "intake_configuration_hash")
    _require(configuration["context_radius"] == plan["context_radius"], "context_radius_configuration")
    for group in ("source_input_hashes", "legacy_metadata_hashes", "implementation_hashes"):
        for path, expected in plan[group].items():
            _require(_digest(Path(path)) == expected, group + ":" + path)
    for path, expected in report["artifact_hashes"].items():
        target = Path(path).resolve(strict=True)
        _require(target.is_relative_to(folder), "artifact_outside_trial")
        _require(_digest(target) == expected, "artifact_hash:" + path)

    root = Path(plan["corpus_root"]).resolve(strict=True)
    inventory = _read(folder / "source-inventory.json")
    provenance = _read(folder / "provenance-snapshot.json")
    source_cases = _read(folder / "source-case-descriptors.json")
    legacy_cases = _read(folder / "legacy-case-descriptors.json")
    records = [json.loads(line) for line in (folder / "source-statements.jsonl").read_text(encoding="utf-8").split("\n") if line]
    snapshot_rows = provenance["byte_identical_source_snapshots"]
    snapshots = {row["relative_path"]: row for row in snapshot_rows}
    _require(len(snapshot_rows) == len(snapshots) == len(inventory), "snapshot_inventory_duplicates")
    _require(len({row["snapshot_path"] for row in snapshots.values()}) == len(snapshots), "snapshot_path_alias")
    discovered = {str(path.resolve()) for path in root.rglob("analysis.txt")}
    _require(discovered == set(plan["source_input_hashes"]), "discovery_inventory")
    _require(len(inventory) == len(discovered), "duplicate_source_inventory")
    _require({row["path"] for row in inventory} == discovered, "source_inventory")
    _require(len({row["case_id"] for row in source_cases}) == len(inventory), "source_case_inventory")
    _require({row["case_id"] for row in source_cases} == {row["case_id"] for row in inventory}, "source_case_ids")
    required_artifacts = {str((folder / name).resolve()) for name in (
        "run-plan.json", "source-inventory.json", "source-case-descriptors.json", "legacy-case-descriptors.json",
        "source-coverage.json", "legacy-coverage.json", "provenance-snapshot.json", "source-statements.jsonl")}
    required_artifacts.update(str(Path(row["snapshot_path"]).resolve()) for row in snapshot_rows)
    listed_artifacts = {str(Path(path).resolve()) for path in report["artifact_hashes"]}
    _require(len(listed_artifacts) == len(report["artifact_hashes"]) and listed_artifacts == required_artifacts, "artifact_hash_inventory")
    expected_provenance = [{key: row[key] for key in ("path", "relative_path", "sha256", "size_bytes")} for row in inventory]
    _require(provenance["source_inputs"] == expected_provenance, "source_provenance_inventory")

    expected = {}
    lines_by_relative = {}
    paths_by_relative = {}
    counts: Counter[str] = Counter()
    files_by_tag: Counter[str] = Counter()
    noncanonical_spelling = 0
    for item in inventory:
        path = Path(item["path"]).resolve(strict=True)
        _require(path.is_relative_to(root), "source_outside_corpus")
        relative = path.relative_to(root).as_posix()
        _require(relative == item["relative_path"], "source_relative_path")
        payload = path.read_bytes()
        _require(len(payload) == item["size_bytes"], "source_size")
        _require(hashlib.sha256(payload).hexdigest() == item["sha256"], "source_hash")
        snapshot = snapshots[relative]
        snapshot_path = Path(snapshot["snapshot_path"]).resolve(strict=True)
        _require(snapshot_path.is_relative_to(folder / "source-snapshot"), "snapshot_outside_trial")
        _require(snapshot_path.read_bytes() == payload, "snapshot_bytes")
        _require(snapshot["original_path"] == item["path"] and snapshot["source_sha256"] == item["sha256"], "snapshot_source_mapping")
        lines = _lines(payload)
        lines_by_relative[relative] = lines
        paths_by_relative[relative] = item["path"]
        local: Counter[str] = Counter()
        for number, (raw, ending) in enumerate(lines, 1):
            match_text = raw.removeprefix("\ufeff") if number == 1 else raw
            found = _TAG.match(match_text)
            if found is None:
                continue
            spelling = found.group(1)
            tag = _TAGS[spelling.lower()]
            expected[relative, number] = (raw, ending, tag, spelling, item["case_id"], item["sha256"])
            local[tag] += 1
            noncanonical_spelling += spelling != tag
        _require(item["physical_lines"] == len(lines), "physical_line_count")
        _require(item["source_statements"] == sum(local.values()), "per_file_statement_count")
        _require(item["statement_counts_by_native_tag"] == {tag: local[tag] for tag in _TAGS.values()}, "per_file_tag_count")
        counts.update(local)
        files_by_tag.update(tag for tag in local if local[tag])

    actual = set()
    for record in records:
        context = record["source_context"]
        locator = context["location"]["locator"]
        key = locator["relative_path"], locator["physical_line"]
        _require(key in expected and key not in actual, "missing_or_duplicate_physical_statement")
        actual.add(key)
        raw, ending, tag, spelling, case_id, sha256 = expected[key]
        _require(record["case_id"] == case_id and context["source_sha256"] == sha256, "statement_source_binding")
        _require(context["source_ref"] == "romantext-file:" + key[0] and context["source_revision"] == "sha256:" + sha256, "immutable_source_ref")
        _require(locator["path"] == paths_by_relative[key[0]] and locator["raw_value"] == raw.split(":", 1)[1], "source_locator_or_value")
        _require(context["raw_text"] == raw and locator["line_ending"] == ending, "raw_statement_bytes_text")
        _require(locator["native_tag"] == tag and locator.get("source_tag_spelling") == spelling, "source_tag_spelling")
        _require(locator["context_is_target"] is False and record["binding"] is None, "context_falsely_bound")
        for nearby in [*locator["context_lines"], locator["preceding_measure_line"], locator["following_measure_line"]]:
            if nearby is None:
                continue
            _require(lines_by_relative[key[0]][nearby["physical_line"] - 1] == (nearby["raw_text"], nearby["line_ending"]), "surrounding_prose_mutation")
        original_lines = lines_by_relative[key[0]]
        index = key[1] - 1
        radius = configuration["context_radius"]
        def context_row(position: int) -> dict[str, Any]:
            text, terminator = original_lines[position]
            return {"physical_line": position + 1, "raw_text": text, "line_ending": terminator}
        expected_context = [context_row(position) for position in range(max(0, index - radius), min(len(original_lines), index + radius + 1))]
        _require(locator["context_lines"] == expected_context, "configured_context_omission")
        measure_positions = [position for position, (text, _) in enumerate(original_lines)
                             if re.match(r"^\s*m[0-9]+[A-Za-z]?(?=\s|-|$)", text)]
        preceding = next((position for position in reversed(measure_positions) if position < index), None)
        following = next((position for position in measure_positions if position > index), None)
        _require(locator["preceding_measure_line"] == (context_row(preceding) if preceding is not None else None), "preceding_context_omission")
        _require(locator["following_measure_line"] == (context_row(following) if following is not None else None), "following_context_omission")
        _require(record["record_kind"] == "SOURCE" and record["claim"]["term"] is None, "source_became_inferred_term")
        _require(record["claim"]["axis"] == {"Note": None, "Form": "form_role", "Pedal": "harmonic_role"}[tag], "tag_routing")
        _require(record["confidence"] is None and record["human_review"]["status"] == "pending_review", "source_approval_or_confidence")
        producer = record["provenance"]["producer"]
        _require(record["provenance"]["kind"] == "imported_source" and producer["name"] == "musical-semantic-source-intake", "source_producer_kind")
        _require(record["provenance"]["actor_id"] is None and producer["model_ref"] is None, "source_actor_or_model_invented")
        _require(producer["version"] == plan["intake_version"] and producer["config_sha256"] == configuration_sha256, "source_producer_version_or_config")
        _require(producer["schema_ref"] == {"name": plan["contract_schema_name"], "version": plan["contract_schema_version"]}, "source_producer_schema")
        _require(record["use_policy"]["training_eligible"] is False, "training_promoted")
        _require(record["use_policy"]["research_only"] is True, "research_scope_changed")
    _require(actual == set(expected), "statement_omission")
    contract.validate_records(records, legacy_cases=[*source_cases, *legacy_cases])

    source_coverage = _read(folder / "source-coverage.json")
    legacy_coverage = _read(folder / "legacy-coverage.json")
    _require(len(source_coverage) == len(source_cases), "source_coverage_denominator")
    _require(len(legacy_coverage) == len(legacy_cases), "legacy_coverage_denominator")
    for row in [*source_coverage, *legacy_coverage]:
        _require(set(row["axis_states"]) == set(contract.AXES), "coverage_axis_inventory")
        _require(set(row["missing_axes"]) == set(contract.AXES), "false_full_coverage")
        _require(not row["assumption_groups"] and not row["stale_record_ids"], "unexpected_binding_or_stale")
    source_ids = {row["case_id"] for row in source_cases}
    _require({row["case_id"] for row in source_coverage} == source_ids, "source_coverage_ids")
    tags_by_case = {case_id: set() for case_id in source_ids}
    for _, _, tag, _, case_id, _ in expected.values():
        tags_by_case[case_id].add(tag)
    for row in source_coverage:
        for axis, state in row["axis_states"].items():
            aligned_pending = (axis == "form_role" and "Form" in tags_by_case[row["case_id"]]) or (
                axis == "harmonic_role" and "Pedal" in tags_by_case[row["case_id"]])
            _require(state == ("needs_alignment" if aligned_pending else "not_assessed"), "source_coverage_state")
    _require({row["case_id"] for row in legacy_coverage} == {row["case_id"] for row in legacy_cases}, "legacy_coverage_ids")
    _require(all(all(state == "not_assessed" for state in row["axis_states"].values()) for row in legacy_coverage), "legacy_false_assessment")
    legacy = plan["legacy_registration"]
    if legacy_cases:
        parent = _read(Path(legacy["report_ref"]))
        original_rows = {(row["pair_id"], row["plan_index"], row["sample_id"]): row for row in parent["records"]}
        indexed_rows = {(row["pair_id"], row["plan_index"], row["sample_id"]): row for row in legacy_cases}
        _require(len(original_rows) == len(parent["records"]) and len(indexed_rows) == len(legacy_cases), "duplicate_legacy_context_identity")
        _require(set(original_rows) == set(indexed_rows), "legacy_context_identity")
        for identity, row in indexed_rows.items():
            old = original_rows[identity]
            _require(row["ir_ref"] == old["working_ir_document_id"] and row["ir_sha256"] is None, "legacy_ir_hash_fabricated")
            _require(row["case_sha256"] == old["sha256"] and row["legacy_status_preserved"] == old["status"], "legacy_status_or_artifact_changed")
            _require(row["legacy_bundle_bytes_reverified"] is False and row["legacy_musical_data_absent"] is False, "legacy_payload_or_negative_claim")
    summary = report["summary"]
    canonical_counts = {tag: counts[tag] for tag in _TAGS.values()}
    canonical_files = {tag: files_by_tag[tag] for tag in _TAGS.values()}
    _require(summary["source_statements"] == len(expected) == len(records), "total_statement_count")
    _require(summary["source_files"] == len(inventory), "total_source_files")
    _require(summary["source_files_with_statements"] == sum(bool(tags) for tags in tags_by_case.values()), "nonempty_source_files")
    _require(summary["statement_counts_by_native_tag"] == canonical_counts, "summary_tag_counts")
    _require(summary["source_files_by_native_tag"] == canonical_files, "summary_tag_file_counts")
    for field in ("aligned_source_statements", "human_validated_source_statements", "training_eligible_source_statements", "gold_eligible_source_statements"):
        _require(summary[field] == 0, field)
    return {"version": VERSION, "passed": True, "source_files": len(inventory),
            "audit_implementation_sha256": _digest(Path(__file__)),
            "trial_report_sha256": _digest(folder / "report.json"),
            "trial_plan_sha256": report["plan_sha256"],
            "source_statements": len(records), "statement_counts_by_native_tag": canonical_counts,
            "source_files_by_native_tag": canonical_files, "noncanonical_source_tag_spellings_preserved": noncanonical_spelling,
            "byte_identical_snapshots": len(snapshots), "legacy_contexts": len(legacy_cases),
            "verified_artifact_hashes": len(report["artifact_hashes"]),
            "legacy_bundle_payloads_recomputed": False, "musical_accuracy_measured": False,
            "input_hash_groups": {field: len(plan[field]) for field in ("source_input_hashes", "legacy_metadata_hashes", "implementation_hashes")}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", required=True)
    parser.add_argument("--output", help="Optional NEW audit JSON; never overwrites an existing result")
    args = parser.parse_args()
    result = audit(args.trial)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with Path(args.output).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
