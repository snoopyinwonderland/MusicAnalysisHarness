"""Leakage-resistant dataset manifests for harmony case libraries.

The manifest is operational metadata outside Canonical Music IR.  It groups
movements from the same work before assigning train/dev/holdout splits, while
preserving uncertainty when a work identity cannot be derived safely.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


VERSION = "harmony-dataset-manifest-0.1.0"
_MOVEMENT_SUFFIX = re.compile(r"^(?P<work>.+?)(?:[_-](?P<movement>\d{1,2}))$")
_CORELLI_MOVEMENT_SUFFIX = re.compile(r"^(?P<work>op\d+n\d+)(?P<movement>[a-z])$", re.IGNORECASE)


def _stable_token(*values: object, length: int = 16) -> str:
    payload = "\x1f".join(str(value) for value in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def _package_identity(folder: Path, source_root: Path, report: dict[str, Any]) -> dict[str, Any]:
    relative = folder.relative_to(source_root)
    parts = relative.parts
    collection = parts[0] if len(parts) > 1 else "unknown_collection"
    stem = Path(report["source_paths"]["score"]).stem
    match = _MOVEMENT_SUFFIX.match(stem)
    if collection.lower() == "corelli" and not match:
        match = _CORELLI_MOVEMENT_SUFFIX.match(stem)
    if match:
        work_key = match.group("work")
        movement = match.group("movement")
        method = "collection_naming_convention_movement_suffix"
        confidence = "derived_conservative"
    else:
        work_key = stem
        movement = None
        method = "score_stem_fallback"
        confidence = "unresolved_work_family"
    work_family_id = f"workfam_{_stable_token('dcmlab', collection, work_key)}"
    score_hash = report["source_sha256"]["score"]
    harmony_hash = report["source_sha256"]["harmonies"]
    return {
        "corpus_id": "dcmlab",
        "collection_id": collection,
        "work_family_id": work_family_id,
        "work_family_source_key": work_key,
        "work_family_method": method,
        "work_family_confidence": confidence,
        "movement_id": movement,
        "edition_id": None,
        "annotation_lineage_id": f"annlin_{_stable_token('dcmlab', collection, harmony_hash)}",
        "score_sha256": score_hash,
        "annotation_sha256": harmony_hash,
    }


def _balanced_group_splits(rows: list[dict[str, Any]], train_percent: int, dev_percent: int) -> dict[str, str]:
    """Assign whole work families while balancing expected exact case volume."""
    counts: Counter[str] = Counter()
    for row in rows:
        counts[row["work_family_id"]] += max(1, int(row["quality"]["exact_alignments"]))
    total = sum(counts.values())
    targets = {
        "train": total * train_percent / 100,
        "dev": total * dev_percent / 100,
        "holdout": total * (100 - train_percent - dev_percent) / 100,
    }
    assigned = Counter()
    result: dict[str, str] = {}
    groups = sorted(counts, key=lambda group: (-counts[group], _stable_token("split-order", group)))
    for group in groups:
        size = counts[group]
        split = max(
            ("train", "dev", "holdout"),
            key=lambda name: ((targets[name] - assigned[name]) / max(targets[name], 1), targets[name] - assigned[name], name),
        )
        result[group] = split
        assigned[split] += size
    minimum_eval_groups = min(3, max(1, len(groups) // 5))
    for split in ("dev", "holdout"):
        while sum(value == split for value in result.values()) < minimum_eval_groups:
            train_groups = [group for group, value in result.items() if value == "train"]
            if len(train_groups) <= 1:
                break
            group = min(
                train_groups,
                key=lambda candidate: (
                    abs((assigned[split] + counts[candidate]) - targets[split]),
                    counts[candidate],
                    _stable_token("rebalance", candidate),
                ),
            )
            result[group] = split
            assigned["train"] -= counts[group]
            assigned[split] += counts[group]
    return result


def build_harmony_dataset_manifest(
    source: str | Path,
    output: str | Path,
    *,
    train_percent: int = 70,
    dev_percent: int = 15,
) -> dict[str, Any]:
    source, output = Path(source).resolve(), Path(output)
    if train_percent < 1 or dev_percent < 1 or train_percent + dev_percent >= 100:
        raise ValueError("Split percentages must leave non-empty train, dev, and holdout ranges")
    folders = sorted(path.parent for path in source.rglob("canonical_music_ir.json"))
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for folder in folders:
        try:
            report = json.loads((folder / "preparation_report.json").read_text(encoding="utf-8"))
            identity = _package_identity(folder, source, report)
            exact = int(report.get("exact_alignments", 0))
            imported = int(report.get("imported_annotations", 0))
            rows.append({
                "manifest_entry_id": f"hds_{_stable_token(report['ir_document_id'], identity['annotation_lineage_id'])}",
                "package_path": str(folder),
                "score_source_path": report["source_paths"]["score"],
                "score_id": report["score_id"],
                "ir_document_id": report["ir_document_id"],
                **identity,
                "split_group_id": identity["work_family_id"],
                "quality": {
                    "imported_annotations": imported,
                    "exact_alignments": exact,
                    "exact_alignment_ratio": round(exact / imported, 6) if imported else 0.0,
                    "source_note_mapping_complete": bool(report.get("source_note_mapping", {}).get("complete", False)),
                },
                "eligibility": {
                    "case_retrieval": exact > 0,
                    "automatic_training": False,
                    "blind_evaluation": False,
                },
                "rights": {
                    "licence_status": "unverified",
                    "internal_research_use": True,
                    "model_training_approved": False,
                    "external_api_transmission_approved": False,
                    "redistribution_approved": False,
                },
            })
        except Exception as exc:
            errors.append({"package": str(folder), "error": f"{type(exc).__name__}: {exc}"})

    group_splits = _balanced_group_splits(rows, train_percent, dev_percent)
    for row in rows:
        row["split"] = group_splits[row["work_family_id"]]
        row["eligibility"]["blind_evaluation"] = row["split"] == "holdout" and row["eligibility"]["case_retrieval"]
    release_seed = "|".join(sorted(f'{row["score_sha256"]}:{row["annotation_sha256"]}' for row in rows))
    schema_path = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "harmony_dataset_manifest.schema.json"
    manifest = {
        "schema_name": "musicanote-harmony-dataset-manifest",
        "schema_version": "0.1.0",
        "builder_version": VERSION,
        "dataset_release_id": f'hdsrel_{_stable_token(release_seed, train_percent, dev_percent)}',
        "source_root": str(source),
        "split_policy": {
            "group_unit": "work_family_id",
            "assignment": "deterministic_whole_family_greedy_balance_by_exact_alignment_count",
            "train_percent": train_percent,
            "dev_percent": dev_percent,
            "holdout_percent": 100 - train_percent - dev_percent,
            "same_work_must_not_cross_splits": True,
            "unresolved_family_uses_score_stem_fallback": True,
            "release_is_immutable_input_to_evaluation": True,
            "minimum_dev_holdout_work_families": min(3, max(1, len({row["work_family_id"] for row in rows}) // 5)),
        },
        "entries": rows,
        "errors": errors,
        "summary": {
            "packages_discovered": len(folders),
            "entries": len(rows),
            "errors": len(errors),
            "work_families": len({row["work_family_id"] for row in rows}),
            "entries_by_split": dict(sorted(Counter(row["split"] for row in rows).items())),
            "work_families_by_split": dict(sorted(Counter(
                next(row["split"] for row in rows if row["work_family_id"] == family)
                for family in {row["work_family_id"] for row in rows}
            ).items())),
            "unresolved_work_family_entries": sum(
                row["work_family_confidence"] == "unresolved_work_family" for row in rows
            ),
        },
    }
    Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def load_manifest_index(path: str | Path) -> dict[str, dict[str, Any]]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    return {entry["ir_document_id"]: entry for entry in manifest["entries"]}


def validate_harmony_data_release(
    manifest_path: str | Path, case_library_path: str | Path, output: str | Path,
) -> dict[str, Any]:
    """Validate split isolation and case-to-manifest identity integrity."""
    manifest_path, case_library_path = Path(manifest_path), Path(case_library_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["entries"]
    by_ir = {entry["ir_document_id"]: entry for entry in entries}
    failures: list[dict[str, Any]] = []

    def single_split(field: str) -> int:
        values: dict[str, set[str]] = {}
        for entry in entries:
            values.setdefault(entry[field], set()).add(entry["split"])
        leaking = {key: sorted(splits) for key, splits in values.items() if len(splits) > 1}
        for key, splits in leaking.items():
            failures.append({"check": f"{field}_single_split", "value": key, "splits": splits})
        return len(leaking)

    duplicate_ir = len(entries) - len(by_ir)
    if duplicate_ir:
        failures.append({"check": "unique_ir_document_id", "duplicates": duplicate_ir})
    family_leaks = single_split("work_family_id")
    score_hash_leaks = single_split("score_sha256")
    annotation_hash_leaks = single_split("annotation_sha256")

    case_count = 0
    split_counts: Counter[str] = Counter()
    missing_manifest = 0
    identity_mismatches = 0
    unassigned = 0
    for line_number, line in enumerate(case_library_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case_count += 1
        case = json.loads(line)
        entry = by_ir.get(case["ir_document_id"])
        if not entry:
            missing_manifest += 1
            if missing_manifest <= 20:
                failures.append({"check": "case_has_manifest_entry", "line": line_number, "case_id": case.get("case_id")})
            continue
        identity = case.get("dataset_identity", {})
        expected = {
            "manifest_entry_id": entry["manifest_entry_id"],
            "work_family_id": entry["work_family_id"],
            "annotation_lineage_id": entry["annotation_lineage_id"],
            "split": entry["split"],
        }
        differences = {key: {"expected": value, "actual": identity.get(key)}
                       for key, value in expected.items() if identity.get(key) != value}
        if differences:
            identity_mismatches += 1
            if identity_mismatches <= 20:
                failures.append({"check": "case_identity_matches_manifest", "line": line_number,
                                 "case_id": case.get("case_id"), "differences": differences})
        split = identity.get("split", "unassigned")
        split_counts[split] += 1
        unassigned += split == "unassigned"

    report = {
        "schema_name": "musicanote-harmony-data-release-validation",
        "schema_version": "0.1.0",
        "dataset_release_id": manifest["dataset_release_id"],
        "artifacts": {
            "manifest": {"path": str(manifest_path), "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
            "case_library": {"path": str(case_library_path), "sha256": hashlib.sha256(case_library_path.read_bytes()).hexdigest()},
        },
        "status": "passed" if not failures and not unassigned else "failed",
        "checks": {
            "manifest_entries": len(entries),
            "unique_ir_document_id_failures": duplicate_ir,
            "work_family_split_leaks": family_leaks,
            "score_hash_split_leaks": score_hash_leaks,
            "annotation_hash_split_leaks": annotation_hash_leaks,
            "case_count": case_count,
            "cases_by_split": dict(sorted(split_counts.items())),
            "cases_missing_manifest": missing_manifest,
            "case_identity_mismatches": identity_mismatches,
            "unassigned_cases": unassigned,
        },
        "failures": failures,
        "policy": {
            "zero_leakage_required": True,
            "zero_unassigned_cases_required": True,
            "validation_does_not_grant_training_eligibility": True,
        },
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
