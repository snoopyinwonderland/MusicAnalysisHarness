"""Read native RomanText prose labels without resolving musical targets.

The text, location and native tag are observations of an external source.  A
``Form:`` or ``Pedal:`` tag routes a statement to an axis; it neither validates
the author's interpretation nor identifies a score span.  ``Note:`` prose is
deliberately unclassified, even when it contains familiar musical terminology.
No score, XML, note, phrase or time alignment is attempted here.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .musical_semantic_enrichment import SCHEMA_NAME, SCHEMA_VERSION, build_source_claim, validate_records


VERSION = "musical-semantic-intake-0.1.2"
SOURCE_TAG_AXES: dict[str, str | None] = {
    "Note": None,
    "Form": "form_role",
    "Pedal": "harmonic_role",
}
_CANONICAL_TAGS = {tag.casefold(): tag for tag in SOURCE_TAG_AXES}
_STATEMENT = re.compile(r"^\s*(?P<tag>Note|Form|Pedal):(?P<value>.*)$", re.IGNORECASE)
_MEASURE_LINE = re.compile(r"^\s*m[0-9]+[A-Za-z]?(?=\s|-|$)")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _token(*values: object) -> str:
    return hashlib.sha256("\x1f".join(str(value) for value in values).encode("utf-8")).hexdigest()[:24]


def intake_configuration(context_radius: int = 2) -> dict[str, Any]:
    """Declare the actual deterministic source-intake policy, not musical facts."""
    if type(context_radius) is not int or context_radius < 0:
        raise ValueError("invalid_source_context_radius")
    return {
        "context_radius": context_radius,
        "native_tag_matching": "case_insensitive",
        "canonical_tag_routing": dict(SOURCE_TAG_AXES),
        "original_tag_spelling": "preserved",
        "physical_line_policy": "CRLF_LF_CR_original_terminators_preserved",
        "raw_value_policy": "exact_text_after_colon_without_normalization",
        "source_target_policy": "unaligned_measure_neighbors_are_context_not_target",
        "prose_classification": "none",
    }


def configuration_sha256(configuration: dict[str, Any]) -> str:
    encoded = json.dumps(configuration, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _physical_lines(text: str) -> list[dict[str, Any]]:
    """Split physical CR/LF lines only, retaining their original terminators."""
    if not text:
        return []
    pieces = re.split(r"(\r\n|\n|\r)", text)
    lines = []
    for offset in range(0, len(pieces), 2):
        raw = pieces[offset]
        ending = pieces[offset + 1] if offset + 1 < len(pieces) else ""
        if offset == len(pieces) - 1 and not raw and not ending:
            continue
        lines.append({"physical_line": len(lines) + 1, "raw_text": raw, "line_ending": ending})
    return lines


def prepare_source_statements(
    analysis_path: str | Path,
    *,
    corpus_root: str | Path,
    context_radius: int = 2,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Return all native statements plus exact per-file source accounting.

    ``preceding_measure_line`` and ``following_measure_line`` are *textual
    context*, not an asserted location.  They remain useful for future review
    and alignment without silently assigning the most recent measure as the
    statement's target.  Source bytes and source statements are never edited.
    """
    configuration = intake_configuration(context_radius)
    config_sha256 = configuration_sha256(configuration)
    provenance = {
        "kind": "imported_source",
        "actor_id": None,
        "producer": {
            "name": "musical-semantic-source-intake",
            "version": VERSION,
            "config_sha256": config_sha256,
            "model_ref": None,
            "schema_ref": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        },
    }
    root = Path(corpus_root).resolve(strict=True)
    path = Path(analysis_path).resolve(strict=True)
    if not root.is_dir() or not path.is_file():
        raise ValueError("source_path_not_regular_file_or_corpus_not_directory")
    if not path.is_relative_to(root):
        raise ValueError("source_path_outside_corpus_root")
    if path.name != "analysis.txt":
        raise ValueError("source_filename_not_analysis_txt")
    relative = path.relative_to(root).as_posix()
    payload = path.read_bytes()
    sha256 = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None:
        if not _SHA256.fullmatch(expected_sha256) or sha256 != expected_sha256:
            raise ValueError("source_input_hash_mismatch:" + relative)
    try:
        original = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("source_not_utf8:" + relative) from exc
    lines = _physical_lines(original)
    measure_indices = [index for index, row in enumerate(lines)
                       if _MEASURE_LINE.match(row["raw_text"])]
    source_ref = "romantext-file:" + relative
    source_revision = "sha256:" + sha256
    case_id = "source_case_" + _token(relative, sha256)
    records = []
    tags: Counter[str] = Counter()
    for index, row in enumerate(lines):
        # A BOM is still preserved in raw_text.  It is ignored only for native
        # tag recognition on the first physical line of a UTF-8 source.
        match_text = row["raw_text"].removeprefix("\ufeff") if index == 0 else row["raw_text"]
        match = _STATEMENT.match(match_text)
        if not match:
            continue
        source_tag_spelling = match.group("tag")
        tag = _CANONICAL_TAGS[source_tag_spelling.casefold()]
        before = bisect_left(measure_indices, index) - 1
        after = bisect_right(measure_indices, index)
        source_context = {
            "source_ref": source_ref,
            "source_revision": source_revision,
            "source_sha256": sha256,
            "raw_text": row["raw_text"],
            "location": {
                "kind": "source_statement",
                "locator": {
                    "path": str(path),
                    "relative_path": relative,
                    "physical_line": row["physical_line"],
                    "native_tag": tag,
                    "source_tag_spelling": source_tag_spelling,
                    "raw_value": match.group("value"),
                    "line_ending": row["line_ending"],
                    "context_lines": lines[max(0, index - context_radius):index + context_radius + 1],
                    "preceding_measure_line": lines[measure_indices[before]] if before >= 0 else None,
                    "following_measure_line": lines[measure_indices[after]] if after < len(measure_indices) else None,
                    "context_is_target": False,
                },
            },
        }
        records.append(build_source_claim(
            case_id=case_id,
            source_context=source_context,
            axis=SOURCE_TAG_AXES[tag],
            term=None,
            provenance=provenance,
            human_review={"status": "pending_review", "reviewer_id": None, "review_ref": None},
        ))
        tags[tag] += 1
    descriptor = {
        "case_id": case_id,
        "case_kind": "source_annotation_file_not_independent_piece",
        "source_refs": [{"source_ref": source_ref, "source_revision": source_revision, "source_sha256": sha256}],
        "source_path": str(path),
        "relative_path": relative,
        "rights": {"rights_status": "unknown", "training_status": "unknown"},
        "requires_alignment_before_bound": True,
        "score_ref": None,
        "score_xml_ref": None,
        "note_refs": [],
        "context_status": {
            "source_text": "preserved",
            "neighboring_source_measure_lines": "context_only_not_target",
            "full_score": "missing_not_aligned",
            "full_xml": "missing_not_aligned",
            "canonical_ir": "missing_not_aligned",
            "phrase_extent": "not_assessed",
        },
    }
    validate_records(records, legacy_cases=[descriptor])
    return {
        "version": VERSION,
        "configuration": configuration,
        "configuration_sha256": config_sha256,
        "case": descriptor,
        "records": records,
        "source": {
            "case_id": case_id,
            "path": str(path),
            "relative_path": relative,
            "sha256": sha256,
            "size_bytes": len(payload),
            "producer_version": VERSION,
            "producer_config_sha256": config_sha256,
            "physical_lines": len(lines),
            "source_statements": len(records),
            "statement_counts_by_native_tag": {tag: tags[tag] for tag in SOURCE_TAG_AXES},
            "routing_counts_by_axis": {
                "form_role": tags["Form"],
                "harmonic_role": tags["Pedal"],
                "unclassified_source_prose": tags["Note"],
            },
            "source_statements_are_independent_pieces": False,
            "native_tags_are_musical_truth": False,
            "score_xml_and_note_alignment_status": "missing_not_aligned",
        },
    }
