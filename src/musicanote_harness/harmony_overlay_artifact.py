"""Build a renderer-neutral harmony overlay artifact for shared score viewers."""

from __future__ import annotations

from typing import Any


VERSION = "harmony-overlay-artifact-0.3.0"


def _review_metadata(surface: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Classify source-conditioned harmony spans for sparse human review.

    This is deliberately a triage policy, not a harmony conclusion.  It only
    decides which imported annotations deserve attention in the shared viewer.
    """
    band = surface.get("support_band", "unscorable")
    presence = surface.get("expected_tone_presence_ratio")
    duration = surface.get("chord_tone_duration_ratio")
    bass_match = surface.get("bass_matches_notated_inversion")
    possible_nct = context.get("possible_nct_resolution_count") or 0
    reasons: list[str] = []
    high = False

    if band in {"weak_evidence", "unscorable"}:
        reasons.append(f"support_{band}")
        high = band == "weak_evidence"
    elif band == "mixed_evidence":
        reasons.append("support_mixed_evidence")
    if isinstance(presence, (int, float)) and presence < 0.75:
        reasons.append("expected_tones_sparse")
        high = high or presence < 0.5
    if isinstance(duration, (int, float)) and duration < 0.55:
        reasons.append("chord_tone_duration_low")
        high = high or duration < 0.35
    if bass_match is False:
        reasons.append("bass_inversion_mismatch")
    if possible_nct > 0:
        reasons.append("possible_nct_resolution")

    return {
        "review_candidate": bool(reasons),
        "review_priority": "high" if reasons and high else "medium" if reasons else "none",
        "review_reasons": reasons,
    }


def build_harmony_overlay_artifact(package: dict[str, Any]) -> dict[str, Any]:
    ir = package["ir"]
    alignments = {row["annotation_id"]: row for row in package["alignments"]}
    surface = {row["annotation_id"]: row for row in package["source_evidence"]["records"]}
    context = {row["annotation_id"]: row for row in package["context_evidence"]["records"]}
    entries = []
    for annotation in package["annotations"]:
        alignment = alignments[annotation["annotation_id"]]
        if alignment["mapping_status"] != "exact" or not annotation.get("target"):
            continue
        evidence = surface.get(annotation["annotation_id"], {})
        boundary = context.get(annotation["annotation_id"], {})
        review = _review_metadata(evidence, boundary)
        entries.append({
            "overlay_item_id": f'harmony_{annotation["annotation_id"]}',
            "annotation_id": annotation["annotation_id"],
            "target": annotation["target"],
            "display_location": annotation["native_target"],
            "label": {
                "raw": annotation["raw_label"],
                "key_raw": annotation["components"].get("key", ""),
                "font_role": "harmony_symbol_campania",
            },
            "range_event_refs": alignment.get("sounding_event_ids", []),
            "attack_event_refs": alignment.get("attacked_sounding_event_ids", []),
            "surface_evidence": {
                "status": evidence.get("status", "unscorable"),
                "support_band": evidence.get("support_band", "unscorable"),
                "expected_tone_presence_ratio": evidence.get("expected_tone_presence_ratio"),
                "chord_tone_duration_ratio": evidence.get("chord_tone_duration_ratio"),
                "bass_matches_notated_inversion": evidence.get("bass_matches_notated_inversion"),
            },
            "context_evidence": {
                "status": boundary.get("status", "unavailable"),
                "previous_label": boundary.get("previous_raw_label"),
                "next_label": boundary.get("next_raw_label"),
                "observed_bass_motion_semitones": boundary.get("observed_bass_motion_semitones"),
                "stepwise_edge_count": boundary.get("stepwise_edge_count"),
                "possible_nct_resolution_count": boundary.get("possible_nct_resolution_count"),
            },
            **review,
            "provenance": {
                "kind": "imported_source_annotation",
                "author_origin": annotation["author_origin"],
                "source_review_status": annotation["source_review_status"],
                "source_asset_sha256": annotation["source_asset_sha256"],
                "source_locator": annotation["source_locator"],
            },
        })
    return {
        "schema_name": "musicanote-harmony-overlay-artifact",
        "schema_version": "0.1.0",
        "artifact_version": VERSION,
        "score_id": ir["score"]["score_id"],
        "ir_document_id": ir["ir_document_id"],
        "source_identity": {
            "score_sha256": package["report"]["source_sha256"]["score"],
            "analysis_sha256": package["report"]["source_sha256"]["analysis"],
        },
        "layer": {
            "layer_id": "source_harmony_review",
            "display_name": "화성 분석 · 모호 구간",
            "default_enabled": True,
            "interaction_mode": "ambiguity_review",
            "structure_influence": "none",
            "source_visibility": "source_annotation_conditioned",
        },
        "render_contract": {
            "time_coordinate": "global_quarter_rational",
            "span_semantics": "[start,end)",
            "range_color_role": "harmony_span",
            "start_color_role": "harmony_start",
            "end_color_role": "harmony_last_attack",
            "unknown_uses_harmony_font": False,
        },
        "items": entries,
        "interpretation": (
            "Display-only source-conditioned overlay; not a blind automatic harmony result "
            "and not an input to phrase, motif, cadence, or pillar scoring"
        ),
    }
