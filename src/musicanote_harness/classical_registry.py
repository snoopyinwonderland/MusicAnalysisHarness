"""Read-only file registry for heterogeneous local classical corpora.

An inventory row is not a validated work, score/annotation alignment, licence,
human label, or permission to train. This avoids promoting file counts to gold.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


VERSION = "classical-corpora-asset-registry-0.1.0"
SCORE_SUFFIXES = {".musicxml", ".mxl", ".mei", ".krn"}


def _role(corpus: str, relative: Path) -> str:
    name = relative.name.lower()
    suffix = relative.suffix.lower()
    parts = {part.lower() for part in relative.parts}
    if corpus == "dcmlab":
        if "harmonies" in parts and suffix == ".tsv":
            return "harmony_annotation_track"
        if "reviewed" in parts and suffix == ".tsv":
            return "reviewed_analysis_table_unverified_origin"
        if "notes" in parts and suffix == ".tsv":
            return "derived_note_table"
        if "measures" in parts and suffix == ".tsv":
            return "derived_measure_table"
        if "chords" in parts and suffix == ".tsv":
            return "derived_chord_table"
    if corpus == "when-in-rome" and suffix == ".rntxt":
        return "roman_annotation_track"
    if suffix == ".rntxt":
        return "roman_annotation_track_unverified_origin"
    if corpus == "choco" and suffix == ".jams":
        return "jams_annotation_track_unverified_coordinate"
    if suffix == ".jams":
        return "jams_annotation_track_unverified_coordinate"
    if corpus == "tavern" and suffix == ".krn":
        return "mixed_score_and_analysis"
    if corpus == "taking-form" and suffix == ".csv":
        return "form_annotation_candidate"
    if corpus == "ycacl" and suffix == ".csv":
        return "pitch_slice_and_key_estimate"
    if corpus == "asap-dataset" and suffix in {".mid", ".midi"}:
        return "performance_midi"
    if corpus == "maestro-piano-midi" and suffix in {".mid", ".midi"}:
        return "performance_midi"
    if suffix in {".ly", ".mscx", ".mscz"}:
        return "score_source_candidate_other_format"
    if suffix in {".lab", ".xlab", ".har", ".clt"}:
        return "label_track_unverified_semantics"
    if suffix in SCORE_SUFFIXES or (suffix == ".xml" and corpus != "freischuetz-digital"):
        return "score_candidate"
    if suffix == ".xml" and corpus == "freischuetz-digital":
        return "mei_score_candidate_not_musicxml"
    if suffix in {".mid", ".midi"}:
        return "midi_candidate"
    if suffix in {".wav", ".mp3", ".flac"}:
        return "audio_candidate"
    if suffix in {".tsv", ".csv", ".json", ".txt"}:
        return "unclassified_data_or_metadata"
    if suffix in {".md", ".pdf", ".html"} or name.startswith("license"):
        return "documentation_or_licence_candidate"
    return "other_asset"


def inventory_classical(root: str | Path, output: str | Path) -> dict[str, Any]:
    """Stream every asset path; only DCML basename pairs are proposed, not approved."""
    root = Path(root).resolve()
    output = Path(output)
    if not root.is_dir():
        raise NotADirectoryError(root)
    output.mkdir(parents=True, exist_ok=True)
    assets_path = output / "assets.jsonl"
    pairs_path = output / "dcml_pair_candidates.jsonl"
    counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    error_count = 0
    error_examples: list[str] = []
    total_bytes = 0
    dcml_scores: dict[tuple[str, str], Path] = {}
    score_preference = {".musicxml": 0, ".mxl": 1, ".mscx": 2, ".mscz": 3}
    def walk_error(error: OSError) -> None:
        nonlocal error_count
        error_count += 1
        if len(error_examples) < 20:
            error_examples.append(str(error))

    with assets_path.open("w", encoding="utf-8") as handle:
        for directory, subdirs, filenames in os.walk(root, onerror=walk_error):
            subdirs[:] = sorted(name for name in subdirs if name not in {".git", ".github", "__pycache__", "node_modules"})
            for filename in sorted(filenames):
                path = Path(directory) / filename
                relative = path.relative_to(root)
                corpus = relative.parts[0] if len(relative.parts) > 1 else "_root"
                try:
                    size = path.stat().st_size
                except OSError as error:
                    if os.name == "nt" and len(str(path)) >= 240:
                        try:
                            size = Path("\\\\?\\" + str(path)).stat().st_size
                        except OSError:
                            error_count += 1
                            if len(error_examples) < 20:
                                error_examples.append(f"{path}: {error}")
                            continue
                    else:
                        error_count += 1
                        if len(error_examples) < 20:
                            error_examples.append(f"{path}: {error}")
                        continue
                role = _role(corpus, relative)
                counts[corpus] += 1
                suffix_counts[path.suffix.lower() or "[none]"] += 1
                role_counts[role] += 1
                total_bytes += size
                record = {
                    "relative_path": relative.as_posix(), "corpus": corpus,
                    "bytes": size, "suffix": path.suffix.lower(), "role_candidate": role,
                    "content_sha256": None, "work_family_id": None,
                    "edition_id": None, "annotation_lineage_id": None,
                    "human_review_status": "unverified", "licence_status": "unverified",
                    "alignment_status": "not_attempted",
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                if corpus == "dcmlab" and path.suffix.lower() in score_preference and "MS3" in relative.parts:
                    pair_key = (relative.parts[1], path.stem)
                    previous = dcml_scores.get(pair_key)
                    if previous is None or score_preference[path.suffix.lower()] < score_preference[previous.suffix.lower()]:
                        dcml_scores[pair_key] = path

    pair_counts: Counter[str] = Counter()
    with pairs_path.open("w", encoding="utf-8") as handle:
        for (subcorpus, stem), score in sorted(dcml_scores.items()):
            base = root / "dcmlab" / subcorpus
            paths = {
                "score": score,
                "measures": base / "measures" / f"{stem}.measures.tsv",
                "notes": base / "notes" / f"{stem}.notes.tsv",
                "harmonies": base / "harmonies" / f"{stem}.harmonies.tsv",
            }
            missing = [kind for kind, path in paths.items() if not path.is_file()]
            status = ("incomplete_files" if missing else
                      "complete_files_unaligned" if score.suffix.lower() == ".musicxml" else
                      "complete_files_requires_conversion")
            pair_counts[status] += 1
            handle.write(json.dumps({
                "pair_id": f"dcml:{subcorpus}:{stem}",
                "subcorpus": subcorpus, "stem": stem,
                "score_format": score.suffix.lower(),
                "paths": {kind: str(path) for kind, path in paths.items()},
                "missing": missing, "status": status,
                "annotation_origin": "unverified", "licence_status": "unverified",
                "alignment_status": "not_attempted",
            }, ensure_ascii=False) + "\n")

    summary = {
        "schema_name": "musicanote-classical-asset-registry",
        "schema_version": "0.1.0", "builder_version": VERSION,
        "root": str(root), "asset_rows": sum(counts.values()),
        "total_bytes": total_bytes, "scan_errors": error_count,
        "scan_error_examples": error_examples,
        "files_by_corpus": dict(sorted(counts.items())),
        "files_by_suffix": dict(sorted(suffix_counts.items())),
        "files_by_candidate_role": dict(sorted(role_counts.items())),
        "dcml_pair_candidates": dict(sorted(pair_counts.items())),
        "status_note": "File inventory only; no hashes, rights clearance, work deduplication, annotation origin, or score alignment implied",
    }
    (output / "registry_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
