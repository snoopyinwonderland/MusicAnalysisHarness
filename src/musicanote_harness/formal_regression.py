from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .core import MusicHarness
from .engraving import musicxml_with_canonical_ids, render_musicxml_pages
from .formal_ir import FormalIRAdapter
from .source_enrichment import enrich_from_mapped_musicxml


def validate_formal_corpus(source: str | Path, destination: str | Path, limit: int = 10) -> dict[str, Any]:
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    all_files = sorted(
        path for path in source.iterdir()
        if path.is_file() and path.suffix.lower() in {".xml", ".musicxml"} and "melody" not in path.name.lower()
    )
    if limit and limit < len(all_files):
        # Deterministic coverage across the complete alphabetic corpus rather
        # than repeatedly validating only the first files.
        indices = [round(index * (len(all_files) - 1) / (limit - 1)) for index in range(limit)] if limit > 1 else [0]
        files = [all_files[index] for index in indices]
    else:
        files = all_files
    schema_path = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR" / "schemas" / "canonical_music_ir.schema.json"
    schema_validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    results: list[dict[str, Any]] = []
    for path in files:
        started = time.perf_counter()
        try:
            legacy = MusicHarness().parse(path)["score"]
            formal = FormalIRAdapter().convert(legacy, path)
            mapped_xml, source_mapping = musicxml_with_canonical_ids(path, formal)
            enrichment = enrich_from_mapped_musicxml(formal, mapped_xml)
            schema_errors = sorted(schema_validator.iter_errors(formal), key=lambda error: list(error.absolute_path))
            _, engraving = render_musicxml_pages(path, formal)
            result = {
                "file": path.name, "status": "ok", "score_id": formal["score"]["score_id"],
                "notes": len(formal["note_events"]), "rests": len(formal["rest_events"]),
                "tie_chains": len(formal["tie_chains"]), "measures": len(formal["measures"]),
                "source_mapping_complete": source_mapping["complete"],
                "schema_valid": not schema_errors,
                "schema_error_sample": [
                    {"path": "/".join(map(str, error.absolute_path)), "message": error.message}
                    for error in schema_errors[:8]
                ],
                "engraving_mapping_complete": engraving["complete"],
                "mapped_notes": engraving["rendered_canonical_id_count"],
                "source_mapping_diagnostics": {
                    "matched_count": source_mapping["matched_count"],
                    "unmatched_ir_count": len(source_mapping["unmatched_ir_note_ids"]),
                    "unmatched_xml_count": len(source_mapping["unmatched_xml_notes"]),
                    "unmatched_ir_sample": source_mapping["unmatched_ir_note_ids"][:8],
                    "unmatched_xml_sample": source_mapping["unmatched_xml_notes"][:8],
                },
                "engraving_mapping_diagnostics": {
                    "mei_note_count": engraving["mei_note_count"],
                    "semantic_mismatch_count": len(engraving["semantic_mismatches"]),
                    "semantic_mismatch_sample": engraving["semantic_mismatches"][:8],
                    "missing_rendered_count": len(engraving["missing_rendered_note_ids"]),
                    "missing_rendered_sample": engraving["missing_rendered_note_ids"][:8],
                },
                "musicxml_version": enrichment["musicxml_version"],
                "source_locators": enrichment["note_locator_count"],
                "clef_changes": enrichment["clef_change_count"], "directions": enrichment["direction_count"],
                "notation_counts": enrichment["notation_counts"],
            }
        except Exception as exc:
            result = {"file": path.name, "status": "error", "error_type": type(exc).__name__, "error": str(exc)}
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        results.append(result)
    summary = {
        "files": len(results), "ok": sum(row["status"] == "ok" for row in results),
        "errors": sum(row["status"] == "error" for row in results),
        "complete_source_mappings": sum(row.get("source_mapping_complete") is True for row in results),
        "schema_valid_files": sum(row.get("schema_valid") is True for row in results),
        "complete_engraving_mappings": sum(row.get("engraving_mapping_complete") is True for row in results),
        "elapsed_seconds": round(sum(row["elapsed_seconds"] for row in results), 3),
    }
    package = {
        "schema_version": "musicanote-formal-regression-0.1",
        "selection": {"strategy": "alphabetic-even-spacing", "eligible_files": len(all_files), "selected_files": len(files)},
        "summary": summary,
        "results": results,
    }
    (destination / "formal_regression.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    return package
