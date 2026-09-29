"""Build a whole-score, source-linked harmony context from prepared annotations.

This layer is a queryable input to later harmony, structure, and generation
engines. Imported labels are never presented as independent predictions.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from .canonical import stable_id
from .formal_ir import q


CONTEXT_VERSION = "source-harmony-context-0.1.0"


def _fraction(value: dict[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def build_source_harmony_context(package: dict[str, Any]) -> dict[str, Any]:
    """Cover the entire written score; keep unannotated gaps explicit."""
    ir = package["ir"]
    score_end = max(
        (_fraction(m["global_start_quarter"]) + _fraction(m["actual_duration_quarter"]) for m in ir["measures"]),
        default=Fraction(0),
    )
    approved = {record["annotation_id"]: record for record in package["annotations"]
                if record["target"] is not None}
    aligned = [record for record in package["alignments"]
               if record["mapping_status"] in {"exact", "verified_transform"}
               and record["annotation_id"] in approved]
    alignment_by_annotation = {record["annotation_id"]: record for record in aligned}
    spans: list[tuple[Fraction, Fraction, dict[str, Any]]] = []
    points: list[tuple[Fraction, dict[str, Any]]] = []
    edges = {Fraction(0), score_end}
    for alignment in aligned:
        annotation = approved[alignment["annotation_id"]]
        target = alignment["target"]
        if "span" in target:
            start = _fraction(target["span"]["start"])
            end = _fraction(target["span"]["end"])
            if not (Fraction(0) <= start < end <= score_end):
                continue
            edges.update((start, end))
            spans.append((start, end, annotation))
        else:
            at = _fraction(target["point"])
            if Fraction(0) <= at <= score_end:
                edges.add(at)
                points.append((at, annotation))

    sound_spans = [
        (_fraction(item["span"]["start"]), _fraction(item["span"]["end"]), item["sounding_event_id"])
        for item in ir["sounding_events"]
    ]
    segments = []
    covered = Fraction(0)
    for start, end in zip(sorted(edges), sorted(edges)[1:]):
        if start == end:
            continue
        active = [item for a, b, item in spans if a < end and start < b]
        harmonic = [item for item in active if item["components"].get("chord") or item["components"].get("special")]
        if harmonic:
            covered += end - start
        sounding = [sid for a, b, sid in sound_spans if a < end and start < b]
        segments.append({
            "segment_id": f"ctx_{stable_id(ir['ir_document_id'], start, end)}",
            "span": {"start": q(start), "end": q(end)},
            "status": "source_annotated" if harmonic else "unannotated",
            "active_annotation_ids": [item["annotation_id"] for item in active],
            "harmony_annotation_ids": [item["annotation_id"] for item in harmonic],
            "source_labels": [{
                "annotation_id": item["annotation_id"],
                "raw_label": item["raw_label"],
                "chord_raw": item["components"].get("chord", ""),
                "global_key_raw": item["components"].get("globalkey", ""),
                "local_key_raw": item["components"].get("localkey", ""),
                "source_asset_sha256": item["source_asset_sha256"],
                "source_locator": item["source_locator"],
                "alignment_status": alignment_by_annotation[item["annotation_id"]]["mapping_status"],
            } for item in harmonic],
            "sounding_event_ids": sounding,
        })

    all_marks = []
    for annotation in (item for _, _, item in spans):
        start = _fraction(annotation["target"]["span"]["start"])
        if annotation["components"].get("cadence") or annotation["components"].get("phraseend"):
            all_marks.append((start, annotation))
    all_marks.extend(points)
    marks = [{
        "annotation_id": item["annotation_id"],
        "point": q(at),
        "cadence_raw": item["components"].get("cadence", ""),
        "phrase_mark_raw": item["components"].get("phraseend", ""),
    } for at, item in sorted(all_marks, key=lambda pair: (pair[0], pair[1]["annotation_id"]))
             if item["components"].get("cadence") or item["components"].get("phraseend")]
    return {
        "schema_name": "musicanote-source-harmony-context",
        "schema_version": "0.1.0",
        "builder_version": CONTEXT_VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "annotation_track_id": package["report"]["annotation_track_id"],
        "annotation_input_policy": "source_annotation_conditioned",
        "score_span": {"start": q(0), "end": q(score_end)},
        "annotated_duration_quarter": q(covered),
        "unannotated_duration_quarter": q(score_end - covered),
        "segments": segments,
        "cadence_phrase_marks": marks,
        "excluded_ambiguous_annotation_ids": [
            row["annotation_id"] for row in package["alignments"] if row["mapping_status"] == "ambiguous"
        ],
        "interpretation_origin": "imported_annotation_not_automatic_prediction",
    }


def context_at(context: dict[str, Any], quarter: Fraction | int) -> dict[str, Any] | None:
    """Find the source-linked harmony segment at one exact written-score time."""
    quarter = Fraction(quarter)
    for segment in context["segments"]:
        if _fraction(segment["span"]["start"]) <= quarter < _fraction(segment["span"]["end"]):
            return segment
    return None
