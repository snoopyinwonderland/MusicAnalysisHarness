from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any

from .canonical import as_fraction


def validate_ir(ir: dict[str, Any]) -> dict[str, Any]:
    issues = list(ir.get("parser_issues", []))
    segments = ir.get("notated_note_segments", [])
    required = {"segment_id", "part_id", "staff_id", "voice_id", "measure", "beat", "onset_ql", "duration_ql", "pitch_spelling"}
    seen: set[str] = set()
    for seg in segments:
        missing = sorted(required - seg.keys())
        if missing:
            issues.append({"code": "missing_segment_fields", "segment_id": seg.get("segment_id"), "fields": missing, "severity": "error"})
        if seg.get("segment_id") in seen:
            issues.append({"code": "duplicate_segment_id", "segment_id": seg.get("segment_id"), "severity": "error"})
        seen.add(seg.get("segment_id"))
        if as_fraction(seg["duration_ql"]) < 0:
            issues.append({"code": "negative_duration", "segment_id": seg["segment_id"], "severity": "error"})

    grids = {(m["part_id"], m["measure"]): m for m in ir.get("measure_grid", [])}
    coverage: dict[tuple[str, int, str, str], list[tuple[Fraction, Fraction]]] = defaultdict(list)
    for event in [*segments, *ir.get("rest_events", [])]:
        key = (event["part_id"], event["measure"], event["staff_id"], event["voice_id"])
        start = as_fraction(event["beat"]) - 1
        coverage[key].append((start, start + as_fraction(event["duration_ql"])))
    for (part_id, measure, staff_id, voice_id), intervals in coverage.items():
        grid = grids.get((part_id, measure))
        if not grid or grid["is_implicit_or_pickup"]:
            continue
        merged: list[list[Fraction]] = []
        for start, end in sorted(set(intervals)):
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        covered = sum((end - start for start, end in merged), Fraction(0))
        nominal = as_fraction(grid["nominal_duration_ql"])
        if covered != nominal:
            issues.append({
                "code": "voice_measure_duration_mismatch", "severity": "warning",
                "part_id": part_id, "measure": measure, "staff_id": staff_id, "voice_id": voice_id,
                "covered_ql": str(covered), "expected_ql": str(nominal),
            })
    errors = sum(i.get("severity") == "error" for i in issues)
    warnings = sum(i.get("severity") == "warning" for i in issues)
    return {"valid": errors == 0, "error_count": errors, "warning_count": warnings, "issues": issues}

