"""Import score-aligned RomanText as external annotations, never Core facts."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .canonical import stable_id
from .formal_ir import q
from .harmony_context import build_source_harmony_context
from .harmony_overlay_artifact import VERSION as OVERLAY_VERSION, build_harmony_overlay_artifact
from .romantext_alignment import VERSION as ALIGNMENT_VERSION, align_romantext
from .romantext_context_evidence import VERSION as CONTEXT_EVIDENCE_VERSION, evaluate_contextual_evidence
from .romantext_evidence import VERSION as EVIDENCE_VERSION, evaluate_source_harmony


IMPORT_VERSION = "romantext-import-0.1.0"
SCHEMA_DIR = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _span_contains(start: Fraction, end: Fraction, sound_start: Fraction, sound_end: Fraction) -> bool:
    return sound_start < end and start < sound_end


def prepare_romantext(analysis_path: str | Path, score_path: str | Path) -> dict[str, Any]:
    analysis_path, score_path = Path(analysis_path), Path(score_path)
    aligned = align_romantext(analysis_path, score_path, include_events=True)
    ir = aligned.pop("ir")
    events = aligned.pop("events")
    analysis_hash, score_hash = _sha256(analysis_path), _sha256(score_path)
    track_id = f"romantext_{analysis_hash[:20]}"
    automatic = analysis_path.name == "analysis_automatic.rntxt"
    author_origin = "machine" if automatic else "unknown"
    review_status = "machine_generated_unreviewed" if automatic else "provenance_unverified_not_gold"

    annotations = []
    alignments = []
    for event in events:
        annotation_id = f"ann_{stable_id(analysis_hash, event['event_index'])}"
        diagnostics = list(event["diagnostics"])
        if event["line"] is None:
            diagnostics.append("source_line_missing")
        usable = event["status"] == "exact_coordinate" and not diagnostics
        target = None
        start = end = None
        if usable and event["target"]:
            start = Fraction(event["target"]["start_quarter"])
            end = Fraction(event["target"]["end_quarter"])
            target = {
                "score_id": ir["score"]["score_id"],
                "ir_document_id": ir["ir_document_id"],
                "span": {"start": q(start), "end": q(end)},
            }
        annotation = {
            "annotation_id": annotation_id,
            "track_id": track_id,
            "source_asset_sha256": analysis_hash,
            "source_locator": {"path": str(analysis_path), "line": event["line"] or 2},
            "raw_label": event["figure"],
            "raw_fields": {
                "figure": event["figure"], "key": event["key"],
                "measure": event["measure"],
                "local_onset_quarter": event["local_onset_quarter"],
                "duration_quarter": event["duration_quarter"],
            },
            "components": {"chord": event["figure"], "key": event["key"], "source_format": "romantext"},
            "native_target": {
                "measure": event["measure"],
                "local_onset_quarter": event["local_onset_quarter"],
                "duration_quarter": event["duration_quarter"],
            },
            "author_origin": author_origin,
            "source_review_status": review_status,
            "source_confidence": None,
            "target": target,
        }
        sounding_ids = []
        attacked_ids = []
        if target is not None and start is not None and end is not None:
            for sound in ir["sounding_events"]:
                sound_start = Fraction(sound["span"]["start"]["numerator"], sound["span"]["start"]["denominator"])
                sound_end = Fraction(sound["span"]["end"]["numerator"], sound["span"]["end"]["denominator"])
                if _span_contains(start, end, sound_start, sound_end):
                    sounding_ids.append(sound["sounding_event_id"])
                    if start <= sound_start < end:
                        attacked_ids.append(sound["sounding_event_id"])
        alignment = {
            "alignment_id": f"align_{annotation_id}",
            "annotation_id": annotation_id,
            "ir_document_id": ir["ir_document_id"],
            "mapping_status": "exact" if target is not None else "ambiguous",
            "method_version": f"{IMPORT_VERSION}+{ALIGNMENT_VERSION}",
            "measure_id": event["measure_id"],
            "target": target,
            "sounding_event_ids": sounding_ids,
            "attacked_sounding_event_ids": attacked_ids,
            "diagnostics": diagnostics,
        }
        annotations.append(annotation)
        alignments.append(alignment)

    imported_schema = json.loads((SCHEMA_DIR / "imported_annotation.schema.json").read_text(encoding="utf-8"))
    alignment_schema = json.loads((SCHEMA_DIR / "alignment_record.schema.json").read_text(encoding="utf-8"))
    for record in annotations:
        Draft202012Validator(imported_schema).validate(record)
    for record in alignments:
        Draft202012Validator(alignment_schema).validate(record)

    exact = sum(row["mapping_status"] == "exact" for row in alignments)
    report = {
        "import_version": IMPORT_VERSION,
        "alignment_version": ALIGNMENT_VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "annotation_track_id": track_id,
        "source_paths": {"analysis": str(analysis_path), "score": str(score_path)},
        "source_sha256": {"analysis": analysis_hash, "score": score_hash},
        "automatic_filename": automatic,
        "author_origin": author_origin,
        "source_review_status": review_status,
        "imported_annotations": len(annotations),
        "exact_alignments": exact,
        "ambiguous_alignments": len(alignments) - exact,
        "annotation_input_policy": "source_annotation_conditioned_only",
        "interpretation": "Imported RomanText source labels; not independent predictions or human gold",
    }
    package = {"ir": ir, "annotations": annotations, "alignments": alignments, "report": report}
    package["source_evidence"] = evaluate_source_harmony(package)
    evidence_schema = json.loads((SCHEMA_DIR / "romantext_source_evidence.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(evidence_schema).validate(package["source_evidence"])
    package["context_evidence"] = evaluate_contextual_evidence(package, package["source_evidence"])
    context_evidence_schema = json.loads(
        (SCHEMA_DIR / "romantext_context_evidence.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(context_evidence_schema).validate(package["context_evidence"])
    report["evidence_version"] = EVIDENCE_VERSION
    report["context_evidence_version"] = CONTEXT_EVIDENCE_VERSION
    report["source_evidence_summary"] = package["source_evidence"]["summary"]
    report["context_evidence_summary"] = package["context_evidence"]["summary"]
    package["viewer_overlay"] = build_harmony_overlay_artifact(package)
    overlay_schema = json.loads((SCHEMA_DIR / "harmony_overlay_artifact.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(overlay_schema).validate(package["viewer_overlay"])
    report["overlay_artifact_version"] = OVERLAY_VERSION
    return package


def write_romantext_package(package: dict[str, Any], output: str | Path) -> None:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "canonical_music_ir.json").write_text(json.dumps(package["ir"], ensure_ascii=False, indent=2), encoding="utf-8")
    for name, rows in (("imported_annotations.jsonl", package["annotations"]),
                       ("alignment_records.jsonl", package["alignments"])):
        (output / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    (output / "preparation_report.json").write_text(json.dumps(package["report"], ensure_ascii=False, indent=2), encoding="utf-8")
    context = build_source_harmony_context(package)
    (output / "source_harmony_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "source_harmony_evidence.json").write_text(
        json.dumps(package["source_evidence"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "source_harmony_context_evidence.json").write_text(
        json.dumps(package["context_evidence"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "harmony_overlay_artifact.json").write_text(
        json.dumps(package["viewer_overlay"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
