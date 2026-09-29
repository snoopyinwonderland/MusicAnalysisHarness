"""Fast, read-only DCML annotation-table preflight before full score alignment.

Passing this audit does not establish musical correctness or score linkage.
It deliberately avoids music21 and Canonical IR generation so the whole local
MusicXML candidate set can be inspected in one short run.
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any


REQUIRED = {
    "measures": {"mc", "mn", "quarterbeats", "duration_qb", "timesig"},
    "harmonies": {"mc", "mn", "quarterbeats", "duration_qb", "label", "chord", "globalkey", "localkey", "cadence", "phraseend"},
    "notes": {"mc", "quarterbeats", "duration_qb", "midi"},
}
VERSION = "dcml-fast-annotation-audit-0.2.0"


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _read_table(path: Path, kind: str) -> tuple[list[dict[str, str]], list[str]]:
    issues = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or [])
        missing = REQUIRED[kind] - columns
        if missing:
            issues.append(f"{kind}:missing_columns:{','.join(sorted(missing))}")
        rows = []
        for row in reader:
            if None in row:
                issues.append(f"{kind}:extra_columns")
            rows.append({key: value or "" for key, value in row.items() if key is not None})
    if not rows:
        issues.append(f"{kind}:empty")
    return rows, issues


def _score_measures(path: Path) -> tuple[int, list[str]]:
    """Read only first MusicXML part's measure labels, without expanding repeats."""
    if path.suffix.lower() == ".mscx":
        # MuseScore's native XML has <Score><Staff><Measure> rather than
        # MusicXML parts. Printed labels require the converter and are unknown.
        staff = ET.parse(path).getroot().find("./Score/Staff")
        return (len(staff.findall("Measure")), []) if staff is not None else (0, [])
    count = 0
    printed = []
    first_part = False
    for event, element in ET.iterparse(path, events=("start", "end")):
        tag = _tag(element)
        if event == "start" and tag == "part" and not first_part:
            first_part = True
        elif event == "end" and tag == "measure" and first_part:
            count += 1
            printed.append(element.attrib.get("number", ""))
            element.clear()
        elif event == "end" and tag == "part" and first_part:
            break
    return count, printed


def _fraction(value: str) -> Fraction:
    return Fraction(value.strip())


def audit_pair(pair: dict[str, Any]) -> dict[str, Any]:
    issues: Counter[str] = Counter()
    examples: dict[str, list[Any]] = {}

    def flag(code: str, example: Any = None) -> None:
        issues[code] += 1
        if example is not None and len(examples.setdefault(code, [])) < 5:
            examples[code].append(example)

    paths = {key: Path(value) for key, value in pair["paths"].items()}
    result: dict[str, Any] = {
        "pair_id": pair["pair_id"], "score_format": pair["score_format"],
        "source_paths": pair["paths"], "audit_version": VERSION,
    }
    try:
        tables = {}
        for kind in ("measures", "notes", "harmonies"):
            tables[kind], errors = _read_table(paths[kind], kind)
            for error in errors:
                flag(error)
        score_count, score_labels = _score_measures(paths["score"])
        result["score_measure_count"] = score_count
        result["measure_rows"] = len(tables["measures"])
        result["note_rows"] = len(tables["notes"])
        result["harmony_rows"] = len(tables["harmonies"])
        if score_count != len(tables["measures"]):
            flag("score_measure_count_mismatch", {"score": score_count, "table": len(tables["measures"])})

        measures = tables["measures"]
        alternate = any(not row.get("quarterbeats") and row.get("quarterbeats_all_endings") for row in measures)
        time_column = "quarterbeats_all_endings" if alternate else "quarterbeats"
        result["coordinate_column"] = time_column
        result["alternate_ending_measure_rows"] = sum(
            not row.get("quarterbeats") and bool(row.get("quarterbeats_all_endings")) for row in measures
        )
        if alternate:
            for kind, rows in tables.items():
                if any(not row.get(time_column) for row in rows):
                    flag(f"{kind}:incomplete_all_endings_coordinates")

        measure_by_mc: dict[int, tuple[Fraction, Fraction, str]] = {}
        previous_end = None
        for index, row in enumerate(measures):
            try:
                mc = int(row["mc"])
                start = _fraction(row[time_column])
                duration = _fraction(row["duration_qb"])
            except (ValueError, KeyError, ZeroDivisionError):
                flag("measure:invalid_time_or_mc", index + 1)
                continue
            if mc != index + 1:
                flag("measure:nonsequential_mc", {"row": index + 1, "mc": mc})
            if mc in measure_by_mc:
                flag("measure:duplicate_mc", mc)
            if duration <= 0:
                flag("measure:nonpositive_duration", mc)
            if previous_end is not None and start != previous_end:
                flag("measure:noncontiguous_written_time", {"mc": mc, "gap": str(start - previous_end)})
            previous_end = start + duration
            measure_by_mc[mc] = (start, start + duration, row.get("mn", ""))
            if index < len(score_labels) and row.get("mn", "") != score_labels[index]:
                flag("score_printed_measure_mismatch", {"mc": mc, "score": score_labels[index], "table": row.get("mn", "")})

        for kind in ("notes", "harmonies"):
            for index, row in enumerate(tables[kind], 1):
                try:
                    mc = int(row["mc"])
                    start = _fraction(row[time_column])
                except (ValueError, KeyError, ZeroDivisionError):
                    flag(f"{kind}:invalid_time_or_mc", index)
                    continue
                if kind == "harmonies" and not row.get("duration_qb"):
                    # DCML sometimes leaves the harmonic extent unspecified,
                    # especially near endings. It is not automatically a point.
                    duration = None
                    flag("harmonies:missing_duration", index)
                else:
                    try:
                        duration = _fraction(row["duration_qb"])
                    except (ValueError, KeyError, ZeroDivisionError):
                        flag(f"{kind}:invalid_duration", index)
                        continue
                if duration is not None and duration < 0:
                    flag(f"{kind}:negative_duration", index)
                measure = measure_by_mc.get(mc)
                if measure is None:
                    flag(f"{kind}:unknown_mc", {"row": index, "mc": mc})
                    continue
                measure_start, measure_end, printed = measure
                if not (measure_start <= start < measure_end or (duration == 0 and start == measure_end)):
                    flag(f"{kind}:onset_outside_measure", {"row": index, "mc": mc, "onset": str(start)})
                if kind == "harmonies" and row.get("mn", "") != printed:
                    flag("harmonies:printed_measure_mismatch", {"row": index, "mc": mc})
                if kind == "notes" and row.get("midi"):
                    try:
                        midi = int(row["midi"])
                        if not 0 <= midi <= 127:
                            flag("notes:midi_outside_0_127", index)
                    except ValueError:
                        flag("notes:invalid_midi", index)
        result["cadence_nonempty_rows"] = sum(bool(row.get("cadence")) for row in tables["harmonies"])
        result["phraseend_nonempty_rows"] = sum(bool(row.get("phraseend")) for row in tables["harmonies"])
        result["label_nonempty_rows"] = sum(bool(row.get("label")) for row in tables["harmonies"])
        result["cadence_values"] = dict(Counter(row["cadence"] for row in tables["harmonies"] if row.get("cadence")))
        result["phraseend_values"] = dict(Counter(row["phraseend"] for row in tables["harmonies"] if row.get("phraseend")))
    except (OSError, UnicodeError, ET.ParseError) as error:
        flag("unreadable_asset", f"{type(error).__name__}: {error}")
    if pair["score_format"] == ".mscx":
        result["status"] = "table_consistent_requires_score_conversion" if not issues else "review_required_requires_score_conversion"
    else:
        result["status"] = "table_consistent_needs_score_alignment" if not issues else "review_required"
    result["issue_counts"] = dict(sorted(issues.items()))
    result["issue_examples"] = examples
    return result


def audit_all(pair_file: str | Path, output: str | Path) -> dict[str, Any]:
    pair_file, output = Path(pair_file), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in pair_file.read_text(encoding="utf-8").splitlines() if line]
    eligible = [row for row in rows if row["status"] in {
        "complete_files_unaligned", "complete_files_requires_conversion"
    }]
    status_counts: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()
    subcorpus_counts: Counter[str] = Counter()
    format_counts: Counter[str] = Counter()
    totals: Counter[str] = Counter()
    cadence_values: Counter[str] = Counter()
    phraseend_values: Counter[str] = Counter()
    with (output / "pair_audit.jsonl").open("w", encoding="utf-8") as handle:
        for pair in eligible:
            result = audit_pair(pair)
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            status_counts[result["status"]] += 1
            subcorpus_counts[pair["subcorpus"]] += 1
            format_counts[pair["score_format"]] += 1
            issue_counts.update(result["issue_counts"])
            cadence_values.update(result.get("cadence_values", {}))
            phraseend_values.update(result.get("phraseend_values", {}))
            for name in ("measure_rows", "note_rows", "harmony_rows", "cadence_nonempty_rows", "phraseend_nonempty_rows", "label_nonempty_rows"):
                totals[name] += result.get(name, 0)
    summary = {
        "schema_name": "musicanote-dcml-fast-annotation-audit", "schema_version": "0.1.0",
        "audit_version": VERSION, "pair_file": str(pair_file), "candidate_pairs": len(eligible),
        "status_counts": dict(status_counts), "issue_counts": dict(issue_counts),
        "subcorpus_counts": dict(subcorpus_counts), "score_format_counts": dict(format_counts),
        "totals": dict(totals),
        "cadence_values": dict(sorted(cadence_values.items())),
        "phraseend_values": dict(sorted(phraseend_values.items())),
        "interpretation": "TSV/XML structural preflight only; no note-level IR alignment, harmony accuracy, human review or rights clearance",
    }
    (output / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
