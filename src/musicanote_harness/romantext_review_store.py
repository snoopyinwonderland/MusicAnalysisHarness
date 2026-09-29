"""Append-only local reviewer decisions for RomanText source evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


SCHEMA_NAME = "musicanote-romantext-reviewer-annotation"
SCHEMA_VERSION = "0.1.0"
REASONS = {
    "surface_compatible",
    "non_chord_tone",
    "inversion_or_bass",
    "local_key_or_tonicization",
    "alignment_or_timeline",
    "source_label_suspect",
    "cannot_judge",
}


def load_latest(path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(path)
    latest: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return latest
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        annotation_id = record.get("annotation_id")
        if annotation_id:
            latest[str(annotation_id)] = record
    return latest


def append_review(
    path: str | Path, *, score_review_id: str, annotation_id: str, reason: str,
    note: str = "", reviewer_id: str = "local_reviewer",
) -> dict[str, Any]:
    if reason not in REASONS:
        raise ValueError(f"Unsupported review reason: {reason}")
    timestamp = datetime.now(timezone.utc).isoformat()
    seed = f"{score_review_id}|{annotation_id}|{reason}|{note}|{timestamp}"
    record = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "review_id": f"rev_{sha256(seed.encode()).hexdigest()[:16]}",
        "score_review_id": score_review_id,
        "annotation_id": annotation_id,
        "reviewer_id": reviewer_id,
        "status": "reviewed",
        "reason": reason,
        "note": note.strip(),
        "created_at": timestamp,
        "supersedes_review_id": None,
        "training_eligible": False,
        "interpretation": "Reviewer triage only; not gold until separately adjudicated",
    }
    previous = load_latest(path).get(annotation_id)
    if previous:
        record["supersedes_review_id"] = previous.get("review_id")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
