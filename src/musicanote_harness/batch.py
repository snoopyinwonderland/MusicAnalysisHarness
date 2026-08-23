from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .canonical import IR_SCHEMA_VERSION

BATCH_RESULT_VERSION = f"batch-probe-0.2+{IR_SCHEMA_VERSION}"

def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _balanced_selection(files: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    eligible = [row for row in files if row["eligible_for_harmony_corpus"]]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        groups[row["category"]].append(row)
    ordered_groups = []
    for name in sorted(groups):
        rows = sorted(groups[name], key=lambda row: row["bytes"])
        # Interleave small, large, and middle files so a pilot is representative.
        reordered = []
        left, right = 0, len(rows) - 1
        while left <= right:
            reordered.append(rows[left])
            left += 1
            if left <= right:
                reordered.append(rows[right])
                right -= 1
        ordered_groups.append(reordered)
    selected = []
    index = 0
    while ordered_groups and (limit is None or len(selected) < limit):
        progressed = False
        for rows in ordered_groups:
            if index < len(rows) and (limit is None or len(selected) < limit):
                selected.append(rows[index])
                progressed = True
        if not progressed:
            break
        index += 1
    return selected


def validate_corpus(inventory_path: str | Path, output_dir: str | Path, limit: int | None = None, timeout_seconds: int = 60) -> dict[str, Any]:
    inventory_path = Path(inventory_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(inventory_path.read_text(encoding="utf-8"))
    root = Path(data["root"])
    selected = _balanced_selection(data["files"], limit)
    results_path = output_dir / "validation_results.jsonl"
    previous = _load_jsonl(results_path)
    completed = {row["relative_path"] for row in previous if row.get("parser_version") == BATCH_RESULT_VERSION}

    with results_path.open("a", encoding="utf-8") as handle:
        for record in selected:
            relative = record["relative_path"]
            if relative in completed:
                continue
            started = time.perf_counter()
            command = [sys.executable, "-m", "musicanote_harness.batch_probe", str(root / relative)]
            try:
                proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=timeout_seconds)
                lines = [line for line in proc.stdout.splitlines() if line.strip()]
                probe = json.loads(lines[-1]) if lines else {"status": "exception", "message": proc.stderr[-1000:]}
            except subprocess.TimeoutExpired:
                probe = {"status": "timeout", "seconds": round(time.perf_counter() - started, 4), "timeout_seconds": timeout_seconds}
            except Exception as exc:
                probe = {"status": "exception", "seconds": round(time.perf_counter() - started, 4), "exception": type(exc).__name__, "message": str(exc)[:1000]}
            row = {
                "parser_version": BATCH_RESULT_VERSION,
                "relative_path": relative, "category": record["category"], "bytes": record["bytes"], **probe,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()

    rows = _load_jsonl(results_path)
    selected_paths = {r["relative_path"] for r in selected}
    newest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["relative_path"] in selected_paths and row.get("parser_version") == BATCH_RESULT_VERSION:
            newest[row["relative_path"]] = row
    relevant = list(newest.values())
    status_counts = Counter(r["status"] for r in relevant)
    issue_counts = Counter(
        issue["code"] for row in relevant for issue in row.get("validation", {}).get("issues", [])
    )
    summary = {
        "schema_version": "musicanote-corpus-validation-summary-0.1",
        "parser_version": BATCH_RESULT_VERSION,
        "inventory": str(inventory_path.resolve()),
        "requested_files": len(selected), "completed_files": len(relevant),
        "status_counts": dict(status_counts), "issue_counts": dict(issue_counts),
        "total_seconds_reported": round(sum(float(r.get("seconds", 0)) for r in relevant), 3),
        "results_file": str(results_path.resolve()),
    }
    (output_dir / "validation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
