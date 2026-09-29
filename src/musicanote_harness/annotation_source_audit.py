"""Read-only provenance and shape audit of non-DCML annotation containers.

Neither a parseable RomanText file nor a parseable JAMS file is a gold label.
No score alignment or rights clearance is inferred here.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


VERSION = "annotation-source-shape-audit-0.1.0"
MEASURE_LINE = re.compile(r"^m\d+(?:\S*)?(?:\s|$)")
SCORE_SUFFIXES = {".musicxml", ".mxl", ".mscx", ".mscz", ".mei", ".krn"}


def _assets(registry_assets: Path, corpus: str, suffix: str) -> list[Path]:
    root = Path(json.loads((registry_assets.parent / "registry_summary.json").read_text(encoding="utf-8"))["root"])
    selected = []
    with registry_assets.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["corpus"] != corpus or row["suffix"] != suffix:
                continue
            relative = Path(row["relative_path"])
            if corpus == "choco" and "tests" in relative.parts:
                continue
            selected.append(root / relative)
    return selected


def audit_romantext(registry_assets: str | Path, output: str | Path) -> dict[str, Any]:
    registry_assets, output = Path(registry_assets), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    analysts: Counter[str] = Counter()
    by_corpus: dict[str, Counter[str]] = {}
    with (output / "romantext_records.jsonl").open("w", encoding="utf-8") as out:
        for corpus in ("openscore-lieder", "when-in-rome"):
            by_corpus[corpus] = Counter()
            for path in _assets(registry_assets, corpus, ".rntxt"):
                row: dict[str, Any] = {"path": str(path), "corpus": corpus, "source_kind": "romantext",
                                       "automatic_filename": path.name == "analysis_automatic.rntxt"}
                try:
                    lines = path.read_text(encoding="utf-8-sig").splitlines()
                    headers = {}
                    for line in lines[:25]:
                        if ":" in line and not MEASURE_LINE.match(line):
                            key, value = line.split(":", 1)
                            if key in {"Composer", "Title", "Analyst", "Proofreader", "Time Signature"}:
                                headers[key] = value.strip()
                    row["headers"] = headers
                    row["measure_line_count"] = sum(bool(MEASURE_LINE.match(line)) for line in lines)
                    row["sibling_score_files"] = sorted(
                        item.name for item in path.parent.iterdir()
                        if item.is_file() and item.suffix.lower() in SCORE_SUFFIXES
                    )
                    row["status"] = "shape_readable" if row["measure_line_count"] else "no_measure_lines"
                    analysts[headers.get("Analyst", "[missing]")] += 1
                except (OSError, UnicodeError) as error:
                    row["status"] = "read_error"
                    row["error"] = f"{type(error).__name__}: {error}"
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                counts[row["status"]] += 1
                by_corpus[corpus][row["status"]] += 1
                if row["automatic_filename"]:
                    counts["automatic_filename"] += 1
                if row.get("sibling_score_files"):
                    counts["has_sibling_score_candidate"] += 1
    summary = {
        "schema_name": "musicanote-romantext-shape-audit", "schema_version": "0.1.0",
        "audit_version": VERSION, "counts": dict(counts),
        "by_corpus": {name: dict(values) for name, values in by_corpus.items()},
        "analysts_top20": analysts.most_common(20),
        "interpretation": "Header/text shape and sibling-file presence only; no RomanText grammar proof, score alignment, human gold status or rights clearance",
    }
    (output / "romantext_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def audit_jams(registry_assets: str | Path, output: str | Path) -> dict[str, Any]:
    registry_assets, output = Path(registry_assets), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    statuses: Counter[str] = Counter()
    namespaces: Counter[str] = Counter()
    annotation_rows: Counter[str] = Counter()
    source_corpora: Counter[str] = Counter()
    annotation_tools: Counter[str] = Counter()
    identifier_keys: Counter[str] = Counter()
    with (output / "jams_records.jsonl").open("w", encoding="utf-8") as out:
        for path in _assets(registry_assets, "choco", ".jams"):
            row: dict[str, Any] = {"path": str(path), "corpus": "choco", "source_kind": "jams"}
            try:
                document = json.loads(path.read_text(encoding="utf-8-sig"))
                annotations = document.get("annotations", [])
                metadata = document.get("file_metadata", {})
                if not isinstance(annotations, list):
                    raise ValueError("annotations is not a list")
                annotation_counts: Counter[str] = Counter()
                row_counts: Counter[str] = Counter()
                invalid_time_rows = 0
                for annotation in annotations:
                    namespace = str(annotation.get("namespace", "[missing]"))
                    data = annotation.get("data", [])
                    if not isinstance(data, list):
                        raise ValueError("annotation data is not a list")
                    annotation_counts[namespace] += 1
                    row_counts[namespace] += len(data)
                    origin = annotation.get("annotation_metadata", {})
                    source_corpora[str(origin.get("corpus") or "[missing]")] += 1
                    annotation_tools[str(origin.get("annotation_tools") or "[missing]")] += 1
                    for event in data:
                        try:
                            if float(event["time"]) < 0 or float(event["duration"]) < 0:
                                invalid_time_rows += 1
                        except (KeyError, TypeError, ValueError):
                            invalid_time_rows += 1
                for key in (metadata.get("identifiers") or {}):
                    identifier_keys[str(key)] += 1
                namespaces.update(annotation_counts)
                annotation_rows.update(row_counts)
                row.update({
                    "status": "shape_readable" if not invalid_time_rows else "invalid_event_time",
                    "jams_version": metadata.get("jams_version"),
                    "title_present": bool(metadata.get("title")),
                    "identifier_keys": sorted((metadata.get("identifiers") or {}).keys()),
                    "annotation_counts": dict(annotation_counts),
                    "annotation_rows": dict(row_counts),
                    "invalid_event_time_rows": invalid_time_rows,
                })
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as error:
                row["status"] = "read_or_shape_error"
                row["error"] = f"{type(error).__name__}: {error}"
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            statuses[row["status"]] += 1
    summary = {
        "schema_name": "musicanote-jams-shape-audit", "schema_version": "0.1.0",
        "audit_version": VERSION, "file_status_counts": dict(statuses),
        "annotation_namespaces": dict(namespaces), "annotation_data_rows": dict(annotation_rows),
        "source_corpus_metadata": dict(source_corpora),
        "annotation_tools_top20": annotation_tools.most_common(20),
        "identifier_keys": dict(identifier_keys),
        "interpretation": "JAMS JSON/data shape only; Choco may reproduce other corpora and time units are not score-aligned; no human gold status or rights clearance",
    }
    (output / "jams_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
