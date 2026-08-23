from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


SUPPORTED_SUFFIXES = {".xml", ".musicxml", ".mxl"}


def category(path: Path) -> str:
    name = path.name.lower()
    logical_name = name
    while True:
        reduced = re.sub(r"\.(?:musicxml|xml|mxl)(?:\(\d+\))?$", "", logical_name)
        if reduced == logical_name:
            break
        logical_name = reduced
    if logical_name.rstrip(" ._-()").endswith("melody"):
        return "melody"
    for label, marker in (
        ("piano_solo", "piano solo"), ("duet", "duet"), ("trio", "trio"),
        ("quartet", "quartet"), ("orchestra", "orchestra"),
    ):
        if marker in name:
            return label
    return "other"


def inventory(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)
    first_by_hash: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = str(path.relative_to(root))
        kind = category(path)
        duplicate_of = first_by_hash.get(digest)
        if duplicate_of is None:
            first_by_hash[digest] = relative
        excluded_reason = "melody_file" if kind == "melody" else ("exact_duplicate" if duplicate_of else None)
        records.append({
            "relative_path": relative, "bytes": path.stat().st_size, "sha256": digest,
            "category": kind, "eligible_for_harmony_corpus": excluded_reason is None,
            "excluded_reason": excluded_reason, "duplicate_of": duplicate_of,
        })
    counts = Counter(r["category"] for r in records)
    excluded = Counter(r["excluded_reason"] for r in records if r["excluded_reason"])
    return {
        "schema_version": "musicanote-corpus-inventory-0.1",
        "root": str(root),
        "summary": {
            "total_files": len(records), "total_bytes": sum(r["bytes"] for r in records),
            "unique_content": len(first_by_hash), "eligible_files": sum(r["eligible_for_harmony_corpus"] for r in records),
            "categories": dict(counts), "excluded": dict(excluded),
        },
        "files": records,
    }


def write_inventory(data: dict[str, Any], destination: str | Path) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
