"""Internal, coordinate-only readiness audit for annotated orchestral sources.

No harmony prediction, dataset assignment, pitch normalization, or source
rewriting is performed.  The small catalog identifies diagnostic inputs, not
score-specific musical rules.  A compatible time grid is not edition identity.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import json
from pathlib import Path, PurePosixPath
from typing import Any, Callable
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from music21 import converter, stream

from .canonical import CanonicalIRBuilder
from .harmony_progression_evidence_trial import digest, write
from .romantext_alignment import align_romantext


VERSION = "harmony-orchestral-readiness-0.1.0"
MAX_XML_BYTES = 64 * 1024 * 1024
COORDINATE_FIELDS = (
    "printed_measure_number", "start_ql", "nominal_duration_ql",
    "actual_duration_ql", "time_signature", "padding_left_ql",
)


@dataclass(frozen=True)
class AuditCase:
    case_id: str
    family_source_key: str
    movement_source_key: str
    analysis_path: Path
    full_score_path: Path
    reduction_path: Path | None = None
    alternative_analysis_paths: tuple[Path, ...] = ()
    automatic_analysis_paths: tuple[Path, ...] = ()


def local_cases(corpus_root: Path) -> list[AuditCase]:
    """Explicit inventory: no downloading and no score-only folders counted."""
    corpus = corpus_root / "when-in-rome" / "Corpus"
    scores = corpus_root / "beethoven-symphonies" / "data"
    haydn = corpus / "Orchestral/Haydn,_Franz_Joseph/Symphony_104/1"
    brahms = corpus / "Orchestral/Brahms,_Johannes/Ein_deutsches_Requiem,_Op._45/1"
    bach = corpus / "Variations_and_Grounds/Bach,_Johann_Sebastian/B_Minor_mass,_BWV232/Crucifixus"
    return [
        AuditCase(
            "orchestral_haydn_104_1", "Haydn,_Franz_Joseph/Symphony_104", "1",
            haydn / "analysis.txt", scores / "Haydn,_Franz/Symphony_No.104/1/Haydn_104_1.mxl",
            haydn / "score.musicxml", automatic_analysis_paths=(haydn / "analysis_automatic.rntxt",),
        ),
        AuditCase(
            "orchestral_brahms_op45_1", "Brahms,_Johannes/Ein_deutsches_Requiem,_Op._45", "1",
            brahms / "analysis.txt", scores / "Brahms,_Johannes/Ein_Deutsches_Requiem,_Op.45/1/Brahms_Op.45_1.mxl",
            alternative_analysis_paths=(brahms / "analysis_DT.txt",),
        ),
        AuditCase(
            "orchestral_bach_bwv232_crucifixus", "Bach,_Johann_Sebastian/B_Minor_mass,_BWV232", "Crucifixus",
            bach / "analysis.txt", scores / "Bach,_Johann_Sebastian/B_Minor_Mass,_BWV.232/14/Bach_BWV.232_14.musicxml",
            bach / "score.musicxml", automatic_analysis_paths=(bach / "analysis_automatic.rntxt",),
        ),
    ]


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((element for element in parent if _tag(element) == name), None)


def _text(parent: ET.Element, name: str) -> str | None:
    child = _child(parent, name)
    return child.text.strip() if child is not None and child.text is not None else None


def _xml_payload(path: Path) -> tuple[bytes, str | None]:
    if path.suffix.lower() != ".mxl":
        if path.stat().st_size > MAX_XML_BYTES:
            raise ValueError("source_xml_size_limit")
        return path.read_bytes(), None
    with ZipFile(path) as archive:
        container_info = archive.getinfo("META-INF/container.xml")
        if container_info.file_size > 1024 * 1024:
            raise ValueError("container_xml_size_limit")
        container = ET.fromstring(archive.read(container_info))
        # Exporters may omit the optional media-type.  Still require one unique
        # candidate and a score-partwise payload; never guess between rootfiles.
        roots = [element.attrib.get("full-path", "") for element in container.iter()
                 if _tag(element) == "rootfile" and element.attrib.get("media-type") in
                 (None, "application/vnd.recordare.musicxml+xml")]
        if len(roots) != 1:
            raise ValueError("musicxml_rootfile_not_unique")
        member = PurePosixPath(roots[0])
        if not roots[0] or member.is_absolute() or ".." in member.parts or "\\" in roots[0] or ":" in roots[0]:
            raise ValueError("unsafe_musicxml_rootfile")
        info = archive.getinfo(roots[0])
        if info.file_size > MAX_XML_BYTES:
            raise ValueError("source_xml_size_limit")
        return archive.read(info), roots[0]


def inspect_source_score(path: Path) -> dict[str, Any]:
    """Read source part count and transpose declarations without changing pitch."""
    payload, member = _xml_payload(path)
    root = ET.fromstring(payload)
    if _tag(root) != "score-partwise":
        raise ValueError(f"unsupported_source_score_type:{_tag(root)}")
    part_list = _child(root, "part-list")
    declarations = [] if part_list is None else [item for item in part_list if _tag(item) == "score-part"]
    part_names = {item.attrib.get("id"): _text(item, "part-name") for item in declarations}
    parts = [item for item in root if _tag(item) == "part"]
    transposes = []
    for part in parts:
        for sequential_index, measure in enumerate(item for item in part if _tag(item) == "measure"):
            for attributes in (item for item in measure if _tag(item) == "attributes"):
                for transpose in (item for item in attributes if _tag(item) == "transpose"):
                    fields = {name: _text(transpose, name) for name in ("diatonic", "chromatic", "octave-change")}
                    invalid = []
                    nonzero = False
                    for name, value in fields.items():
                        if value is not None:
                            try:
                                nonzero |= Fraction(value) != 0
                            except (ValueError, ZeroDivisionError):
                                invalid.append(name)
                    if fields["chromatic"] is None:
                        invalid.append("missing_chromatic")
                    double = _child(transpose, "double")
                    transposes.append({
                        "source_part_id": part.attrib.get("id"),
                        "source_part_name": part_names.get(part.attrib.get("id")),
                        "sequential_measure_index": sequential_index,
                        "printed_measure_number": measure.attrib.get("number"),
                        "staff_number": transpose.attrib.get("number"),
                        "source_fields": fields,
                        "double": None if double is None else {"attributes": dict(double.attrib), "text": double.text},
                        "source_xml": ET.tostring(transpose, encoding="unicode"),
                        "nonzero_declared": nonzero,
                        "invalid_fields": invalid,
                    })
    return {
        "source_path": str(path), "source_sha256": digest(path),
        "musicxml_archive_member": member, "source_musicxml_version": root.attrib.get("version"),
        "movement_title": _text(root, "movement-title"),
        "source_part_count": len(parts), "declared_part_count": len(declarations),
        "source_parts": [{"source_part_id": item.attrib.get("id"), "part_name": part_names.get(item.attrib.get("id")),
                          "source_measure_count": sum(_tag(child) == "measure" for child in item)} for item in parts],
        "source_transpose_declarations": transposes,
        "nonzero_source_transpose_count": sum(bool(item["nonzero_declared"]) for item in transposes),
        "invalid_source_transpose_count": sum(bool(item["invalid_fields"]) for item in transposes),
        "source_double_transpose_count": sum(item["double"] is not None for item in transposes),
        "concert_normalization_verified": False,
        "absence_of_nonzero_transpose_is_not_concert_pitch_certification": True,
    }


def annotation_lineage(path: Path) -> dict[str, Any]:
    headers: dict[str, str] = {}
    for text in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = text.partition(":")
        if separator and key.strip().lower() in {"analyst", "proofreader", "composer", "title"}:
            headers[key.strip().lower()] = value.strip()
    analyst = headers.get("analyst", "")
    if "automatic" in path.name.lower():
        origin = "automatic_filename_declared"
    elif analyst and any(token in analyst.lower() for token in ("automation", "computer", "automatic")):
        origin = "human_with_automation_declared"
    elif analyst:
        origin = "human_analyst_declared"
    else:
        origin = "unknown"
    return {"path": str(path), "sha256": digest(path), "origin": origin, "headers": headers,
            "lineage_collection": "when-in-rome", "human_gold_validated": False,
            "same_work_exports_are_not_independent_annotations": True}


def compare_grids(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare ordinal/printed coordinates, never align/rewrite differing editions."""
    issues = []
    counts: Counter[str] = Counter()
    if len(left) != len(right):
        counts["measure_count_mismatch"] += 1
        issues.append({"reason": "measure_count_mismatch", "left": len(left), "right": len(right)})
    matching = 0
    for index, (first, second) in enumerate(zip(left, right)):
        different = [field for field in COORDINATE_FIELDS if first.get(field) != second.get(field)]
        if not different:
            matching += 1
        for field in different:
            counts[f"{field}_mismatch"] += 1
            if len(issues) < 30:
                issues.append({"sequential_measure_index": index, "reason": f"{field}_mismatch",
                               "left": first.get(field), "right": second.get(field)})
    return {"status": "coordinate_grid_compatible" if not counts else "coordinate_grid_mismatch",
            "left_measure_count": len(left), "right_measure_count": len(right),
            "matching_measure_count": matching, "diagnostic_counts": dict(counts), "examples": issues,
            "cross_edition_identity_validated": False, "harmonic_accuracy_measured": False}


def read_score_grid(path: Path) -> dict[str, Any]:
    """Reuse existing rational grid semantics without building harmony atoms."""
    score = converter.parse(path)
    builder = CanonicalIRBuilder()
    parts = []
    for index, part in enumerate(score.parts):
        rows = builder._measure_grid(score, part, str(part.id or f"P{index + 1}"))
        measures = list(part.getElementsByClass(stream.Measure))
        for ordinal, (row, measure) in enumerate(zip(rows, measures)):
            row["printed_measure_number"] = str(measure.measureNumberWithSuffix())
            row["sequential_measure_index"] = ordinal
        parts.append({"parsed_part_index": index, "parsed_part_id": str(part.id), "grid": rows})
    if not parts or not parts[0]["grid"]:
        raise ValueError("empty_score_grid")
    reference = parts[0]["grid"]
    checks = [{"parsed_part_index": part["parsed_part_index"], **compare_grids(reference, part["grid"])}
              for part in parts[1:]]
    return {"grid_provider": "CanonicalIRBuilder._measure_grid", "parsed_part_count": len(parts),
            "reference_part_index": 0, "reference_measure_count": len(reference), "parts": parts,
            "cross_part_checks": checks,
            "cross_part_grid_compatible": all(check["status"] == "coordinate_grid_compatible" for check in checks),
            "canonical_ir_persisted": False, "concert_transposition_applied": False}


def harmonic_use_gate(metadata: dict[str, Any] | None, grid: dict[str, Any] | None,
                      alignment: dict[str, Any]) -> dict[str, Any]:
    reasons = ["dataset_policy_unassigned", "cross_edition_identity_not_validated"]
    technical = []
    if metadata is None:
        technical.append("source_metadata_unavailable")
    else:
        if metadata.get("nonzero_source_transpose_count", 0):
            technical.append("nonzero_source_transpose_requires_concert_normalization")
        if metadata.get("invalid_source_transpose_count", 0):
            technical.append("invalid_source_transpose_requires_review")
        if metadata.get("source_double_transpose_count", 0):
            technical.append("source_octave_doubling_requires_review")
    if grid is None:
        technical.append("score_grid_unavailable")
    elif not grid["cross_part_grid_compatible"]:
        technical.append("cross_part_score_grid_mismatch")
    if alignment.get("status") != "aligned_complete":
        technical.append("manual_annotation_coordinate_audit_not_complete")
    return {"status": "blocked", "harmonic_use_eligible": False,
            "technical_coordinate_ready": not technical, "technical_blockers": technical,
            "policy_and_identity_blockers": reasons, "automatic_training": False,
            "blind_evaluation": False, "human_gold": False, "external_api_transmission": False,
            "formal_ir_limitation": "written_pitch is copied to concert_pitch; concert_transposition is unavailable",
            "source_transposition_repaired": False}


def _safe_call(function: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
    try:
        return {"status": "readable", "result": function(*args)}
    except Exception as error:
        return {"status": "error", "error_type": type(error).__name__, "error": str(error)}


def _alignment(analysis: Path, score: Path) -> dict[str, Any]:
    row = _safe_call(align_romantext, analysis, score, False)
    if row["status"] == "readable":
        result = row.pop("result")
        row.update(result)
        row["status"] = "aligned_partial" if result["status_counts"].get("ambiguous", 0) else (
            "aligned_complete" if result["roman_events"] else "empty_annotation")
    row["include_events"] = False
    row["canonical_ir_persisted"] = False
    return row


def audit_case(case: AuditCase, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    progress = progress or (lambda message: None)
    record: dict[str, Any] = {
        "case_id": case.case_id, "family_source_key": case.family_source_key,
        "movement_source_key": case.movement_source_key,
        "family_identity_method": "explicit_local_source_inventory_not_validated_dataset_identity",
        "dataset_classification": "unassigned_exploratory", "source_policy_review_required": True,
        "human_gold_validated": False, "harmonic_accuracy_measured": False,
    }
    progress(f"{case.case_id}: source metadata and lineage")
    record["primary_annotation"] = _safe_call(annotation_lineage, case.analysis_path)
    record["alternative_annotations"] = [_safe_call(annotation_lineage, path) for path in case.alternative_analysis_paths]
    record["automatic_annotations"] = [_safe_call(annotation_lineage, path) for path in case.automatic_analysis_paths]
    record["full_score_source"] = _safe_call(inspect_source_score, case.full_score_path)
    progress(f"{case.case_id}: full-score rational measure grids")
    record["full_score_grid"] = _safe_call(read_score_grid, case.full_score_path)
    progress(f"{case.case_id}: primary manual annotation / full-score coordinate audit")
    record["full_score_alignment"] = _alignment(case.analysis_path, case.full_score_path)
    if case.reduction_path is not None:
        record["reduction_source"] = _safe_call(inspect_source_score, case.reduction_path)
        record["reduction_grid"] = _safe_call(read_score_grid, case.reduction_path)
        progress(f"{case.case_id}: primary manual annotation / reduction coordinate audit")
        record["reduction_alignment"] = _alignment(case.analysis_path, case.reduction_path)
        if record["reduction_grid"]["status"] == record["full_score_grid"]["status"] == "readable":
            first = record["reduction_grid"]["result"]["parts"][0]["grid"]
            second = record["full_score_grid"]["result"]["parts"][0]["grid"]
            record["reduction_full_score_grid_comparison"] = compare_grids(first, second)
        else:
            record["reduction_full_score_grid_comparison"] = {"status": "unavailable", "cross_edition_identity_validated": False}
    else:
        record["reduction_full_score_grid_comparison"] = {"status": "no_local_reduction", "cross_edition_identity_validated": False}
    metadata = record["full_score_source"].get("result")
    grid = record["full_score_grid"].get("result")
    record["harmonic_use_gate"] = harmonic_use_gate(metadata, grid, record["full_score_alignment"])
    stages = ["primary_annotation", "full_score_source", "full_score_grid", "full_score_alignment"]
    if case.reduction_path is not None:
        stages.extend(("reduction_source", "reduction_grid", "reduction_alignment"))
    failures = [name for name in stages
                if record[name]["status"] == "error"]
    record["failed_stages"] = failures
    record["status"] = "partial_error" if failures else "diagnostic_audit_complete_not_harmony_validated"
    return record


def run_audit(cases: list[AuditCase], output: Path, policy_references: tuple[Path, ...] = (),
              progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    """New-only artifacts; input hashes checked again even if a stage failed."""
    if not cases or len({case.case_id for case in cases}) != len(cases):
        raise ValueError("nonempty_unique_case_ids_required")
    for case in cases:
        if not case.case_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in case.case_id):
            raise ValueError("unsafe_case_id")
    sources = list(policy_references)
    for case in cases:
        sources.extend((case.analysis_path, case.full_score_path, *case.alternative_analysis_paths, *case.automatic_analysis_paths))
        if case.reduction_path is not None:
            sources.append(case.reduction_path)
    sources = sorted(set(sources), key=str)
    frozen = {str(path): digest(path) if path.is_file() else None for path in sources}
    output.mkdir(parents=True, exist_ok=False)
    code_files = [Path(__file__), Path(__file__).with_name("romantext_alignment.py"),
                  Path(__file__).with_name("canonical.py"), Path(__file__).with_name("formal_ir.py")]
    contract = {
        "version": VERSION, "input_sha256": frozen,
        "policy_references": [str(path) for path in policy_references],
        "code_sha256": {str(path): digest(path) for path in code_files},
        "scope": "local source metadata and exact rational coordinate diagnostics only",
        "source_inventory_selection": "three verified local annotation/full-score pairs; no all-corpus replay",
        "include_events": False, "harmonic_accuracy_measured": False, "canonical_ir_persisted": False,
        "production_modified": False, "dataset_manifest_modified": False,
        "existing_splits_rights_and_gold_unchanged": True, "source_files_modified": False,
        "external_transmission": False, "model_training": False, "ui_modified": False,
        "coordinate_compatibility_is_not_cross_edition_identity": True,
    }
    write(output / "run-contract.json", contract)
    records = []
    for case in cases:
        record = audit_case(case, progress)
        path = output / "cases" / f"{case.case_id}.json"
        write(path, record)
        records.append(record)
    changed = [str(path) for path in sources if (digest(path) if path.is_file() else None) != frozen[str(path)]]
    summary = {
        "audited_pairs": len(records), "distinct_inventory_work_families": len({case.family_source_key for case in cases}),
        "full_score_part_counts": {record["case_id"]: record["full_score_source"].get("result", {}).get("source_part_count") for record in records},
        "full_score_alignment_status_counts": dict(Counter(record["full_score_alignment"]["status"] for record in records)),
        "manual_full_score_roman_events": sum(record["full_score_alignment"].get("roman_events", 0) for record in records),
        "manual_full_score_exact_coordinates": sum(record["full_score_alignment"].get("status_counts", {}).get("exact_coordinate", 0) for record in records),
        "manual_full_score_ambiguous_coordinates": sum(record["full_score_alignment"].get("status_counts", {}).get("ambiguous", 0) for record in records),
        "nonzero_source_transposition_blocked_pairs": sum("nonzero_source_transpose_requires_concert_normalization" in record["harmonic_use_gate"]["technical_blockers"] for record in records),
        "technical_coordinate_ready_pairs": sum(record["harmonic_use_gate"]["technical_coordinate_ready"] for record in records),
        "harmonic_use_eligible_pairs": 0, "human_gold_pairs": 0, "harmonic_accuracy_measured": False,
        "reduction_comparison_status_counts": dict(Counter(record["reduction_full_score_grid_comparison"]["status"] for record in records)),
    }
    report = {"schema_name": "musicanote-harmony-orchestral-readiness", "schema_version": "0.1.0",
              "version": VERSION, "summary": summary, "input_hashes_unchanged": not changed,
              "changed_inputs": changed, "records": records,
              "limitations": ["No annotation semantic accuracy or cross-edition note identity validation.",
                              "New sources remain unassigned exploratory; rights and split review are required.",
                              "Written-to-concert normalization is unavailable in the current FormalIR adapter.",
                              "Automatic siblings and exports do not increase independent human annotation coverage."]}
    write(output / "report.json", report)
    if changed:
        raise ValueError("input_hash_changed_during_audit")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path)
    args = parser.parse_args()
    references = (args.corpus_root / "when-in-rome/README.md", args.corpus_root / "beethoven-symphonies/README.md")
    if args.dataset_manifest is not None:
        references += (args.dataset_manifest,)
    report = run_audit(local_cases(args.corpus_root), args.output, references,
                       progress=lambda message: print(message, flush=True))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
