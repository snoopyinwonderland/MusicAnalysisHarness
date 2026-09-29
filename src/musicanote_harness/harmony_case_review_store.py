"""Append-only reviewer feedback for retrieved harmony analogies."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


SCHEMA_NAME = "musicanote-harmony-case-review"
SCHEMA_VERSION = "0.1.0"
VERDICTS = {"useful_analogy", "similar_surface_different_function", "not_similar", "cannot_judge"}
AXES = {"surface", "bass_motion", "voice_leading", "harmonic_function", "nct_context", "phrase_role"}


def load_latest(path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(path)
    latest = {}
    if not path.is_file():
        return latest
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        latest[f'{record.get("query_id")}|{record.get("case_id")}'] = record
    return latest


def append_case_review(
    path: str | Path, *, query_id: str, case_id: str, engine_version: str, verdict: str,
    axis_ratings: dict[str, int] | None = None, note: str = "", reviewer_id: str = "local_reviewer",
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"Unsupported case-review verdict: {verdict}")
    ratings = axis_ratings or {}
    if any(axis not in AXES for axis in ratings):
        raise ValueError("Unsupported case-review axis")
    if any(not isinstance(value, int) or not 0 <= value <= 4 for value in ratings.values()):
        raise ValueError("Axis ratings must be integers from 0 to 4")
    timestamp = datetime.now(timezone.utc).isoformat()
    seed = f"{query_id}|{case_id}|{engine_version}|{verdict}|{ratings}|{note}|{timestamp}"
    key = f"{query_id}|{case_id}"
    previous = load_latest(path).get(key)
    record = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "review_id": f'crev_{sha256(seed.encode()).hexdigest()[:16]}',
        "query_id": query_id,
        "case_id": case_id,
        "engine_version": engine_version,
        "reviewer_id": reviewer_id,
        "verdict": verdict,
        "axis_ratings": ratings,
        "note": note.strip(),
        "created_at": timestamp,
        "supersedes_review_id": previous.get("review_id") if previous else None,
        "training_eligible": False,
        "rule_update_eligible": False,
        "interpretation": "Retrieval feedback only; requires adjudication and holdout evaluation before changing ranking rules",
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
