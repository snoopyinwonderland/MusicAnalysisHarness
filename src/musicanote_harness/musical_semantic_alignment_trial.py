"""Frozen local G1 pilot: explicit Pedal coordinates -> literal score windows.

Visits EVERY Pedal record in a completed G0 intake, retaining unselected,
unsupported, empty, erroneous and ambiguous attempts in the denominator.
Only sibling MusicXML/MXL scores are parsed. No title-based score matching,
training promotion, classifier, generator, old artifact rewrite, or UI change.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from time import perf_counter

from music21 import converter

from .canonical import CanonicalIRBuilder
from .formal_ir import FormalIRAdapter
from .musical_pattern_observation import digest, f, q, observe, reconstruct, validate_observation, validate_core
from .musical_semantic_alignment import align_statement, prepare_meter_index, validate_alignment
from .musical_semantic_enrichment import record_ref, validate_record

VERSION = "musical-semantic-alignment-trial-0.1.1"
ROOT = Path(__file__).resolve().parents[2]


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _snapshot(source, destination):
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())


def _choose_score(path):
    siblings = list(path.parent.iterdir())
    for suffix in (".musicxml", ".mxl"):
        candidates = sorted(item for item in siblings if item.is_file() and item.suffix.lower() == suffix)
        if candidates:
            return candidates[0]
    return None


def _context_span(ir, alignment):
    endpoints = alignment["endpoints"]
    start, end = endpoints[0]["sequential_measure_index"], endpoints[1]["sequential_measure_index"]
    measures = sorted(ir["measures"], key=lambda row: row["sequential_measure_index"])
    left = next(index for index, row in enumerate(measures) if row["sequential_measure_index"] == start)
    right = next(index for index, row in enumerate(measures) if row["sequential_measure_index"] == end)
    first, last = measures[max(0, left - 1)], measures[min(len(measures) - 1, right + 1)]
    return {"start": first["global_start_quarter"],
            "end": q(f(last["global_start_quarter"]) + f(last["actual_duration_quarter"]))}


def run(intake, output):
    started = perf_counter()
    intake, output = Path(intake).resolve(strict=True), Path(output).resolve()
    if output.exists() or output == ROOT or output.is_relative_to(intake) or not output.is_relative_to(ROOT / "output"):
        raise ValueError("output_must_be_new_workspace_output_directory")
    report_path, statements_path = intake / "report.json", intake / "source-statements.jsonl"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not report["complete"] or report["version"] != "musical-semantic-intake-trial-0.1.2":
        raise ValueError("completed_supported_intake_required")
    if file_digest(statements_path) != report["artifact_hashes"][str(statements_path)]:
        raise ValueError("intake_statement_artifact_changed")
    records = [json.loads(line) for line in statements_path.read_text(encoding="utf-8").splitlines()]
    pedals = [row for row in records if row["source_context"]["location"]["locator"]["native_tag"] == "Pedal"]
    sources = defaultdict(list)
    for record in pedals:
        validate_record(record)
        sources[record["source_context"]["location"]["locator"]["path"]].append(record)
    input_hashes = {str(report_path): file_digest(report_path), str(statements_path): file_digest(statements_path)}
    selection = []
    for name, statements in sorted(sources.items()):
        path = Path(name).resolve(strict=True)
        expected = statements[0]["source_context"]["source_sha256"]
        if any(row["source_context"]["source_sha256"] != expected for row in statements) or file_digest(path) != expected:
            raise ValueError("source_changed_since_intake:" + name)
        input_hashes[str(path)] = expected
        score = _choose_score(path)
        if score:
            input_hashes[str(score)] = file_digest(score)
        selection.append({"source_path": str(path), "source_sha256": expected,
                          "score_path": str(score) if score else None,
                          "score_sha256": file_digest(score) if score else None,
                          "source_statement_refs": [record_ref(row) for row in statements],
                          "selection_status": "sibling_musicxml_mxl" if score else "no_supported_sibling_score"})
    # Include transitively called parser/schema code, not just the new runner.
    code_paths = [*sorted((ROOT / "src/musicanote_harness").glob("*.py")),
                  *sorted((ROOT / "docs/harmony/schemas").glob("musical_*.schema.json")),
                  ROOT / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"]
    code_hashes = {str(path): file_digest(path) for path in code_paths}
    plan = {"version": VERSION, "intake_report_sha256": input_hashes[str(report_path)],
            "environment": {"python": sys.version, "packages": {name: importlib.metadata.version(name)
                              for name in ("music21", "jsonschema", "referencing")}},
            "selection_rule": "all_Pedal_records_then_unique_sibling_musicxml_preferred_over_mxl",
            "context_rule": "one_full_measure_before_and_after_endpoint_measures_plus_link_closure",
            "selection": selection, "inputs": input_hashes, "code": code_hashes,
            "research_only": True, "training_eligible": False, "gold_status": "not_established",
            "generation_ready": False, "musical_accuracy_measured": False}
    output.mkdir(parents=True, exist_ok=False)
    _new(output / "run-plan.json", plan)
    attempts, pattern_index, artifacts = [], [], {}
    for number, selection_row in enumerate(selection, 1):
        source = Path(selection_row["source_path"])
        records_for_file = sources[str(source)]
        if selection_row["score_path"] is None:
            attempts.extend({"source_statement_ref": record_ref(row), "status": "not_selected",
                             "reasons": ["no_supported_sibling_score"], "alignment": None,
                             "pattern_ref": None} for row in records_for_file)
            continue
        score = Path(selection_row["score_path"])
        key = digest([str(source), selection_row["source_sha256"], selection_row["score_sha256"]])[:24]
        folder = output / "cases" / key
        folder.mkdir(parents=True)
        _snapshot(source, folder / "analysis.txt")
        _snapshot(score, folder / ("score" + score.suffix.lower()))
        _new(folder / "source-statements.json", records_for_file)
        print(f"[{number}/{len(selection)}] {source.relative_to(source.parents[4])}", flush=True)
        try:
            if file_digest(source) != selection_row["source_sha256"] or file_digest(score) != selection_row["score_sha256"]:
                raise ValueError("input_changed_before_parse")
            parsed = converter.parse(score)
            legacy = CanonicalIRBuilder().build(parsed, score)
            ir = FormalIRAdapter().convert(legacy, score)
            validate_core(ir)
            if ir["source_files"][0]["sha256"] != selection_row["score_sha256"]:
                raise ValueError("core_source_hash_mismatch")
            meter_index = prepare_meter_index(source)
            _new(folder / "canonical-ir.json", ir)
            _new(folder / "source-meter-index.json", meter_index)
        except Exception as exc:
            _new(folder / "parse-error.json", {"exception": type(exc).__name__, "message": str(exc)})
            attempts.extend({"source_statement_ref": record_ref(row), "status": "file_blocked",
                             "reasons": [type(exc).__name__ + ":" + str(exc)], "alignment": None,
                             "pattern_ref": None} for row in records_for_file)
            continue
        for source_record in records_for_file:
            alignment = align_statement(source_record, ir, meter_index)
            validate_alignment(alignment, source=source_record, ir=ir, meter_index=meter_index)
            attempt = {"source_statement_ref": record_ref(source_record), "status": alignment["status"],
                       "reasons": alignment["reasons"], "alignment": alignment, "pattern_ref": None}
            if alignment["status"] == "exact_coordinate":
                scope = {**alignment["binding"], "case_id": source_record["case_id"],
                         "source_statement_ref": record_ref(source_record),
                         "alignment_ref": {"record_id": alignment["record_id"], "record_sha256": alignment["record_sha256"]},
                         "context_span": _context_span(ir, alignment)}
                observation = observe(ir, scope)
                validate_observation(observation, ir=ir, scope=scope)
                path = folder / (observation["record_id"] + ".json")
                _new(path, observation)
                attempt["pattern_ref"] = {"record_id": observation["record_id"], "record_sha256": observation["record_sha256"], "path": str(path)}
                recovered = reconstruct(observation)
                originals = {row.get("note_id", row.get("rest_id")): row for row in [*ir["note_events"], *ir["rest_events"]]}
                if any(row != originals[row.get("note_id", row.get("rest_id"))] for row in recovered):
                    raise ValueError("independent_original_event_projection_mismatch")
                pattern_index.append({**attempt["pattern_ref"], "source_path": str(source),
                    "raw_source_text": source_record["source_context"]["raw_text"],
                    "source_physical_line": source_record["source_context"]["location"]["locator"]["physical_line"],
                    "target_span": scope["target_span"], "context_span": scope["context_span"],
                    "target_events": sum(slot["target_relation"] != "linked_context_only" for slot in observation["slots"]),
                    "preserved_notes": sum(slot["event_kind"] == "note" for slot in observation["slots"]),
                    "preserved_rests": sum(slot["event_kind"] == "rest" for slot in observation["slots"]),
                    "tie_chains": len(observation["core_projection"]["tie_chains"]),
                    "raw_lanes": len(observation["raw_lanes"]), "musical_role_validated": False})
            attempts.append(attempt)
    _new(output / "alignment-attempts.json", attempts)
    _new(output / "pattern-index.json", pattern_index)
    counts = Counter(row["status"] for row in attempts)
    reasons = Counter(reason for row in attempts for reason in row["reasons"])
    if len(attempts) != len(pedals) or len({row["source_statement_ref"]["record_id"] for row in attempts}) != len(pedals):
        raise ValueError("source_attempt_denominator_mismatch")
    for path in output.rglob("*"):
        if path.is_file():
            artifacts[str(path)] = file_digest(path)
    changed = [path for path, expected in {**input_hashes, **code_hashes}.items() if file_digest(path) != expected]
    report = {"version": VERSION, "complete": not changed,
              "summary": {"source_pedal_statements": len(pedals), "source_files": len(selection),
                          "selected_score_files": sum(row["score_path"] is not None for row in selection),
                          "status_counts": dict(counts), "reason_counts": dict(reasons),
                          "literal_pattern_observations": len(pattern_index),
                          "score_files_with_patterns": len({row["source_path"] for row in pattern_index}),
                          "musical_role_validated": 0, "training_eligible": 0, "gold_eligible": 0,
                          "generation_ready": 0, "independent_piece_count": None},
              "artifact_hashes": artifacts, "changed_inputs_or_code": changed,
              "elapsed_seconds": perf_counter() - started,
              "source_modified": False, "previous_outputs_modified": False,
              "core_or_production_parser_modified": False, "score_viewer_modified": False,
              "external_transmission": False, "musical_accuracy_measured": False,
              "limits": ["Coordinate matches do not validate a pedal pitch/lane/role or source harmony.",
                         "Projection reproduces existing IR events, not independent MusicXML fidelity or concert transposition.",
                         "Note/Form prose is preserved in G0; this pilot does not align or classify it.",
                         "Implicit endpoints, rounded beats, pickups, irregular grids and duplicate IDs are held.",
                         "Literal slots are not chord-relative accompaniment templates, a generator, or completed G1."]}
    _new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.intake, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
