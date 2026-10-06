"""Frozen G1 pattern windows -> all-lane geometry and conditional roles.

Input inventory is verified before computation. Source harmony is one explicit
assumption, not a correct answer. Every window remains in the denominator.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from time import perf_counter

from .musical_harmony_assumption import import_romantext, validate_track
from .musical_pattern_observation import validate_observation
from .musical_role_evidence import analyze, ref, validate_evidence
from .musical_semantic_alignment import validate_alignment
from .musical_semantic_enrichment import validate_record

VERSION = "musical-role-evidence-trial-0.1.0"
ROOT = Path(__file__).resolve().parents[2]


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _inputs(alignment):
    report_path = alignment / "report.json"
    report = read(report_path)
    if report.get("version") != "musical-semantic-alignment-trial-0.1.1" or report.get("complete") is not True:
        raise ValueError("completed_supported_alignment_required")
    hashes = report["artifact_hashes"]
    actual = {str(p.resolve()) for p in alignment.rglob("*") if p.is_file() and p != report_path}
    if set(hashes) != actual:
        raise ValueError("upstream_artifact_inventory_mismatch")
    for name, expected in hashes.items():
        path = Path(name).resolve(strict=True)
        if not path.is_relative_to(alignment) or file_digest(path) != expected:
            raise ValueError("upstream_artifact_changed")
    hashes = {str(report_path): file_digest(report_path), **hashes}
    index = read(alignment / "pattern-index.json")
    if len(index) != report["summary"]["literal_pattern_observations"]:
        raise ValueError("upstream_pattern_denominator_mismatch")
    if len({row["record_id"] for row in index}) != len(index):
        raise ValueError("duplicate_pattern_index_id")
    for row in index:
        path = Path(row["path"]).resolve(strict=True)
        if not path.is_relative_to(alignment / "cases") or str(path) not in hashes:
            raise ValueError("unregistered_pattern_path")
        observation = read(path)
        if ref(observation) != {key: row[key] for key in ("record_id", "record_sha256")}:
            raise ValueError("pattern_index_identity_mismatch")
        for field in ("target_span", "context_span"):
            if row[field] != observation["scope"][field]:
                raise ValueError("pattern_index_scope_mismatch")
    return hashes, index


def _case(directory, input_hashes):
    ir, meter = read(directory / "canonical-ir.json"), read(directory / "source-meter-index.json")
    analysis = directory / "analysis.txt"
    if file_digest(analysis) != meter["source_sha256"]:
        raise ValueError("snapshot_analysis_meter_hash_mismatch")
    scores = [p for p in directory.iterdir() if p.is_file() and p.name in ("score.musicxml", "score.mxl")]
    if len(scores) != 1 or len(ir["source_files"]) != 1 or file_digest(scores[0]) != ir["source_files"][0]["sha256"]:
        raise ValueError("snapshot_ir_score_hash_mismatch")
    records = read(directory / "source-statements.json")
    for record in records:
        validate_record(record)
        if record["source_context"]["source_sha256"] != meter["source_sha256"]:
            raise ValueError("snapshot_source_statement_hash_mismatch")
    if any(str(p.resolve()) not in input_hashes for p in [analysis, scores[0], directory / "canonical-ir.json", directory / "source-meter-index.json", directory / "source-statements.json"]):
        raise ValueError("unregistered_case_input")
    return ir, meter, records


def run(alignment, output):
    start = perf_counter()
    alignment, output = Path(alignment).resolve(strict=True), Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / "output") or output.is_relative_to(alignment) or output == ROOT / "output":
        raise ValueError("output_must_be_new_workspace_output_directory")
    inputs, index = _inputs(alignment)
    attempts = read(alignment / "alignment-attempts.json")
    code_paths = [*sorted((ROOT / "src/musicanote_harness").glob("*.py")),
                  *sorted((ROOT / "docs/harmony/schemas").glob("*.json")),
                  ROOT / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"]
    code = {str(p): file_digest(p) for p in code_paths}
    plan = {"version": VERSION, "alignment": str(alignment), "inputs": inputs, "code": code,
            "pattern_refs": [{key: row[key] for key in ("record_id", "record_sha256", "path")} for row in index],
            "environment": {"python": sys.version, "packages": {name: importlib.metadata.version(name)
                            for name in ("music21", "jsonschema", "referencing")}},
            "source_annotation_is_assumption_not_answer": True, "external_transmission": False}
    output.mkdir(parents=True)
    write_new(output / "run-plan.json", plan)
    cached, results, counts = {}, [], Counter()
    for row in index:
        path = Path(row["path"])
        directory = path.parent
        destination = output / "cases" / directory.name
        destination.mkdir(parents=True, exist_ok=True)
        item = {"observation_ref": {key: row[key] for key in ("record_id", "record_sha256")},
                "input_path": str(path), "status": "blocked", "evidence_ref": None, "evidence_path": None,
                "assumption_ref": None, "assumption_path": None, "reasons": []}
        try:
            if directory not in cached:
                ir, meter, sources = _case(directory, inputs)
                try:
                    track = import_romantext(directory / "analysis.txt", ir, meter)
                    validate_track(track, ir=ir)
                    track_path = destination / (track["record_id"] + ".json")
                    write_new(track_path, track)
                    counts["source_assumption_tracks"] += 1
                    counts["usable_harmony_segments"] += sum(s["status"] == "usable" for s in track["segments"])
                    counts["blocked_harmony_segments"] += sum(s["status"] == "blocked" for s in track["segments"])
                    counts["held_harmony_import_events"] += len(track["import_diagnostics"])
                    cached[directory] = (ir, meter, sources, [track], str(track_path), [])
                except Exception as exc:
                    counts["harmony_import_failed_files"] += 1
                    cached[directory] = (ir, meter, sources, [], None, [f"{type(exc).__name__}:{exc}"])
            ir, meter, sources, tracks, track_path, reasons = cached[directory]
            observation = read(path)
            source_ref = observation["scope"]["source_statement_ref"]
            matches = [s for s in sources if ref(s) == source_ref]
            if len(matches) != 1:
                raise ValueError("missing_or_duplicate_observation_source_statement")
            aligned = [a["alignment"] for a in attempts if a["status"] == "exact_coordinate"
                       and ref(a["alignment"]) == observation["scope"]["alignment_ref"]]
            if len(aligned) != 1:
                raise ValueError("missing_or_duplicate_observation_alignment")
            validate_alignment(aligned[0], source=matches[0], ir=ir, meter_index=meter)
            expected_binding = {k: observation["scope"][k] for k in
                                ("score_id", "ir_document_id", "ir_content_sha256", "source_files", "target_span")}
            if aligned[0]["binding"] != expected_binding:
                raise ValueError("observation_alignment_binding_mismatch")
            validate_observation(observation, ir=ir)
            evidence = analyze(ir, observation, tracks)
            validate_evidence(evidence, ir=ir, observation=observation, tracks=tracks)
            evidence_path = destination / (evidence["record_id"] + ".json")
            write_new(evidence_path, evidence)
            item.update(status="conditional_evidence" if tracks else "literal_only", evidence_ref=ref(evidence),
                        evidence_path=str(evidence_path), assumption_ref=ref(tracks[0]) if tracks else None,
                        assumption_path=track_path, reasons=reasons)
            counts["literal_evidence_records"] += 1
            for field in ("sounds", "grace_points", "pitch_episodes", "onset_groups", "rests"):
                counts[field + "_instances"] += len(evidence["literal"][field])
            for ep in evidence["literal"]["pitch_episodes"]:
                counts[ep["mode"] + "_episode_instances"] += 1
            for condition in evidence["conditional"]:
                for profile in [*condition["pedal_profiles"], *condition["sequential_profiles"]]:
                    counts[profile["status"] + "_instances"] += 1
        except Exception as exc:
            item["reasons"].append(f"{type(exc).__name__}:{exc}")
        results.append(item)
    counts.update({"input_observations": len(index), "score_files": len({Path(row["path"]).parent for row in index})})
    statuses = dict(Counter(row["status"] for row in results))
    if len(results) != len(index) or len({r["observation_ref"]["record_id"] for r in results}) != len(index):
        raise ValueError("result_denominator_mismatch")
    write_new(output / "evidence-index.json", results)
    changed = [p for p, expected in {**inputs, **code}.items() if file_digest(p) != expected]
    artifacts = {str(p): file_digest(p) for p in output.rglob("*") if p.is_file()}
    report = {"version": VERSION, "complete": not changed, "summary": {**dict(counts), "status_counts": statuses,
              "human_validated": 0, "training_eligible": 0, "gold_eligible": 0, "generation_ready": 0,
              "independent_piece_count": None}, "artifact_hashes": artifacts, "changed_inputs_or_code": changed,
              "elapsed_seconds": perf_counter() - start, "source_modified": False, "previous_outputs_modified": False,
              "core_or_production_modified": False, "score_viewer_modified": False, "external_transmission": False,
              "musical_accuracy_measured": False, "limits": [
                  "Pedal-source sampling is biased and is not full annotation, work, instrumentation or role coverage.",
                  "Source RomanText harmony is a conditional hypothesis, not an independent target or correctness score.",
                  "Shape counts include overlapping windows, raw polyphonic lanes and unresolved alternatives.",
                  "Written IR pitch is not independently certified concert pitch; original sources and old evidence stay immutable.",
                  "No semantic voice assignment, winning chord, confirmed pedal/arpeggio, arrangement generator or production/UI migration."]}
    write_new(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.alignment, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
