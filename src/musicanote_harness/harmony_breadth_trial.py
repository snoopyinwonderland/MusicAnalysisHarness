"""Fresh, label-blind development replay over explicitly authorized packages.

This is a breadth/compatibility audit, not an accuracy evaluation. Source
annotations supply identity hashes only. Protected/unknown policies remain
blocked; neither dataset splits nor musical verdicts are changed.
"""
from __future__ import annotations

import argparse
import gzip
import json
import hashlib
import traceback
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from fractions import Fraction
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from shutil import copyfile
from time import perf_counter
from xml.etree import ElementTree as ET

from jsonschema import Draft202012Validator

from .formal_ir import q
from .harmony_joint import f
from .harmony_path_contrast import token
from .harmony_progression_evidence_trial import digest, load, write
from . import harmony_continuous_survey as continuous
from . import harmony_segment_contrast as contrast
from . import harmony_progression_context as progression
from . import harmony_candidate_relation_survey as relations
from . import harmony_hold_change_context as hold_change
from .harmony_missing_evidence import validate_ir as validate_event_coverage

VERSION = "harmony-breadth-trial-0.1.1"


def cohort(tracks, manifest):
    """Pure inventory; policy is inherited only from a unique exact hash pair."""
    by_hash = defaultdict(list)
    groups = {key: defaultdict(set) for key in
              ("work_family_id", "score_sha256", "annotation_sha256")}
    for entry in manifest["entries"]:
        by_hash[(entry.get("score_sha256"), entry.get("annotation_sha256"))].append(entry)
        for key, values in groups.items():
            if entry.get(key):
                values[entry[key]].add(entry.get("split"))
    ids = [r["pair_id"] for r in tracks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_prepared_pair_id")
    rows = []
    for track in tracks:
        hashes = track.get("source_sha256", {})
        matches = by_hash.get((hashes.get("score"), hashes.get("harmonies")), [])
        entry = matches[0] if len(matches) == 1 else None
        reasons = []
        if entry is None:
            reasons.append("unknown_or_nonunique_manifest_hash_pair")
        else:
            parts = track["pair_id"].split(":")
            corpus_alias = {"dcmlab": "dcml"}.get(entry.get("corpus_id"), entry.get("corpus_id"))
            if (len(parts) != 3 or parts[0] != corpus_alias
                or parts[1] != entry.get("collection_id")
                or parts[2] != Path(entry.get("score_source_path", "")).stem
                or track.get("score_id") != entry.get("score_id")
                or track.get("ir_document_id") != entry.get("ir_document_id")):
                reasons.append("manifest_identity_mismatch")
            if not entry.get("work_family_id") or entry.get("work_family_confidence") == "unresolved_work_family":
                reasons.append("unresolved_work_family")
            for key, values in groups.items():
                splits = values.get(entry.get(key), set())
                if len(splits) != 1 or not splits <= {"train", "dev", "holdout"}:
                    reasons.append(key + "_split_conflict")
            if entry.get("split") == "holdout":
                reasons.append("protected_holdout")
            elif entry.get("split") not in {"train", "dev"}:
                reasons.append("unknown_split")
            if entry.get("rights", {}).get("internal_research_use") is not True:
                reasons.append("internal_research_not_approved")
        if track.get("alignment_eligible") is not True or track.get("alignment_quality") not in {"validated_complete", "validated_partial"}:
            reasons.append("alignment_quarantined_or_not_eligible")
        rows.append({"pair_id": track["pair_id"], "track": deepcopy(track),
                     "manifest_entry": deepcopy(entry), "blockers": sorted(set(reasons)),
                     "replay_eligible": not reasons,
                     "evaluation_kind": "nonblind_internal_development_compatibility",
                     "gold_eligible": False, "training_promoted": False})
    return {"rows": sorted(rows, key=lambda r: r["pair_id"]),
            "inventory_packages": len(rows),
            "eligible_packages": sum(r["replay_eligible"] for r in rows),
            "blocker_counts": dict(Counter(b for r in rows for b in r["blockers"])),
            "policy_changed": False}


def freeze_score(ir, per_lane=2):
    """Freeze entire-score attack inventory before any chord computation.

    Select interior equally spaced indices independently per explicit lane;
    never prefer a shape, label, or a window that later passes a budget.
    """
    if type(per_lane) is not int or per_lane < 1:
        raise ValueError("positive_integer_samples_per_lane_required")
    sounds = ir["sounding_events"]
    if not sounds:
        return {"status": "empty_score", "selected_samples": [], "planned_samples": 0}
    end = f(ir["score"]["duration_quarters"])
    scope = {"start": q(0), "end": q(end)}
    p = continuous.plan(ir, scope)
    lanes = defaultdict(list)
    for index, sample in enumerate(p["samples"]):
        lanes[tuple(sample["lane"])].append((index, sample))
    selected = []; lane_rows = []
    for lane, items in sorted(lanes.items()):
        count = min(per_lane, len(items))
        indices = sorted({((i + 1) * len(items)) // (count + 1) for i in range(count)})
        lane_rows.append({"lane": list(lane), "available_windows": len(items),
                          "selected_lane_indices": indices})
        for index in indices:
            original_index, sample = items[index]
            selected.append({"plan_index": original_index, "lane_index": index,
                             "sample": deepcopy(sample)})
    selected.sort(key=lambda row: row["plan_index"])
    return {"version": VERSION, "status": "planned", "scope": scope,
            "planned_samples": len(p["samples"]), "lane_inventory": lane_rows,
            "skipped_sounds": p["skipped_sounds"], "selected_samples": selected,
            "selection": "interior quantile indices per explicit lane over full score",
            "samples_per_lane": per_lane, "source_labels_used": False,
            "independent_samples": False, "all_windows_analyzed": False}


def analyze_sample(ir, sample):
    """Execute real gates; an abstention is not bypassed or replaced by ready."""
    ir_hash = _object_hash(ir)
    stages = {}; summary = {"sample_id": sample["sample_id"],
                            "lane": sample["lane"], "span": sample["span"],
                            "accuracy_measured": False, "source_labels_used": False}
    raw = continuous.analyze(ir, sample); stages["continuous"] = raw
    summary["continuous_status"] = raw["status"]
    summary["condition_assignment_count"] = raw.get("condition_assignment_count", 0)
    summary["possible_voice_assignments"] = raw.get("voices", {}).get("possible_assignments")
    base = contrast.build(ir, raw); stages["contrast"] = base
    summary["contrast_status"] = base["status"]
    if base["status"] == "ready":
        validate_event_coverage({"plan": {"context_span": base["span"]},
                                 "events": base["events"]}, ir)
        summary.update(all_part_event_coverage_verified=True,
                       all_part_event_count=len(base["events"]),
                       all_part_note_time=base["total_note_time"])
    lattice = progression.build(ir, base); stages["lattice"] = lattice
    summary["lattice_status"] = lattice["status"]
    if lattice["status"] == "ready":
        validate_event_coverage(lattice, ir)
        summary.update(interval_count=len(lattice["edges"]),
                       spelled_reading_count=sum(len(e["readings"]) for e in lattice["edges"]),
                       geometry_pattern_count=len(lattice["patterns"]))
    survey = relations.run(lattice, ir, temporal=True); stages["relations"] = survey
    summary.update(relation_status=survey["status"],
                   planned_relation_pairs=len(survey["plan"]["pairs"]),
                   executed_relation_pairs=len(survey["results"]),
                   relation_summary=survey.get("summary", {}),
                   temporal_summary=survey.get("temporal_summary", {}))
    final = hold_change.run(lattice, survey, ir); stages["hold_change"] = final
    summary.update(status=final["status"],
                   repeated_bass_chains=len(final.get("chain_comparisons", [])),
                   hold_change_summary=final.get("summary", {}))
    if _object_hash(ir) != ir_hash:
        raise ValueError("analyzer_mutated_canonical_ir")
    return {"version": VERSION, "sample": deepcopy(sample), "summary": summary,
            "stages": stages, "selected": None, "production_modified": False}


def source_transposition(score):
    """Preflight XML only: this runner does not repair written/concert pitches."""
    root = ET.parse(score).getroot()
    rows = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "transpose":
            continue
        row = {child.tag.rsplit("}", 1)[-1]: child.text for child in node}
        rows.append(row)
    nonzero = False; malformed = False
    for row in rows:
        if not row or not set(row) <= {"chromatic", "diatonic", "octave-change", "double"} or "double" in row:
            malformed = True
        for name, value in row.items():
            if name not in {"chromatic", "diatonic", "octave-change"}:
                continue
            try:
                number = Fraction(value.strip())
                if number.denominator != 1:
                    malformed = True
                nonzero |= number != 0
            except (AttributeError, ValueError, ZeroDivisionError):
                malformed = True
    return {"source_transpose_elements": rows, "nonzero_source_transposition": nonzero,
            "malformed_or_unsupported_transposition": malformed,
            "concert_pitch_normalization_verified": False,
            "harmonic_replay_allowed": not (nonzero or malformed),
            "policy": "no nonzero source transpose permitted with current written-to-concert adapter"}


def _object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _freeze_package(row, output, schema):
    track = row["track"]; entry = row["manifest_entry"]
    prep_path = Path(track["report_path"]).resolve()
    prep = load(prep_path)
    if (prep["source_sha256"]["score"] != entry["score_sha256"]
        or prep["source_sha256"]["harmonies"] != entry["annotation_sha256"]
        or prep["score_id"] != entry["score_id"]
        or prep["ir_document_id"] != entry["ir_document_id"]):
        raise ValueError("preparation_identity_changed")
    source_paths = {key: Path(prep["source_paths"][key]).resolve() for key in ("score", "harmonies")}
    for key, path in source_paths.items():
        if digest(path) != prep["source_sha256"][key]:
            raise ValueError("source_" + key + "_hash_changed")
    ir_path = Path(track["canonical_ir_path"]).resolve(); ir = load(ir_path)
    schema.validate(ir)
    if ir["score"]["score_id"] != entry["score_id"] or ir["ir_document_id"] != entry["ir_document_id"]:
        raise ValueError("canonical_ir_identity_changed")
    pitch_policy = source_transposition(source_paths["score"])
    frozen = {"pair_id": row["pair_id"], "manifest_entry": deepcopy(entry),
              "source_files": {str(path): digest(path) for path in source_paths.values()},
              "preparation_path": str(prep_path), "preparation_sha256": digest(prep_path),
              "original_ir_path": str(ir_path), "ir_sha256": digest(ir_path),
              "schema_validated": True, "part_count": len(ir["parts"]),
              "measure_count": len(ir["measures"]), "note_events": len(ir["note_events"]),
              "sounding_events": len(ir["sounding_events"]), "pitch_policy": pitch_policy}
    package = output / "sources" / token(row["pair_id"])
    package.mkdir(parents=True, exist_ok=False)
    snapshot = package / "canonical_music_ir.json"
    copyfile(ir_path, snapshot)
    if digest(snapshot) != frozen["ir_sha256"]:
        raise ValueError("snapshot_hash_mismatch")
    frozen["frozen_ir_path"] = str(snapshot.resolve())
    write(package / "provenance.json", frozen)
    return ir, frozen


def _execute_package(job):
    item, output = job
    output = Path(output); source = item["source"]
    if digest(Path(source["frozen_ir_path"])) != source["ir_sha256"]:
        raise ValueError("frozen_ir_changed")
    ir = load(Path(source["frozen_ir_path"])); records = []
    for chosen in item["plan"]["selected_samples"]:
        sample = chosen["sample"]; start = perf_counter()
        try:
            result = analyze_sample(deepcopy(ir), sample)
            artifact = output / "samples" / (token([item["pair_id"], sample["sample_id"]]) + ".json.gz")
            artifact.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            artifact.write_bytes(gzip.compress(payload, mtime=0))
            row = {**result["summary"], "pair_id": item["pair_id"],
                   "plan_index": chosen["plan_index"], "artifact": str(artifact.resolve()),
                   "sha256": digest(artifact), "elapsed_seconds": round(perf_counter() - start, 3)}
        except Exception as exc:
            row = {"pair_id": item["pair_id"], "sample_id": sample["sample_id"],
                   "plan_index": chosen["plan_index"], "span": sample["span"],
                   "status": "execution_error", "error_type": type(exc).__name__, "error": str(exc),
                   "traceback": traceback.format_exc(),
                   "elapsed_seconds": round(perf_counter() - start, 3)}
        records.append(row)
    return records


def run(prepared_tracks, manifest, output, per_lane=2, workers=1):
    if type(per_lane) is not int or per_lane < 1:
        raise ValueError("positive_integer_samples_per_lane_required")
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError("worker_count_must_be_integer_1_to_4")
    prepared_tracks, manifest, output = map(Path, (prepared_tracks, manifest, output))
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    tracks = [json.loads(line) for line in prepared_tracks.read_text(encoding="utf-8").splitlines() if line.strip()]
    inventory = cohort(tracks, load(manifest))
    schema_path = Path(__file__).resolve().parents[2] / "MUSICANOTE_Canonical_Music_IR/schemas/canonical_music_ir.schema.json"
    schema = Draft202012Validator(load(schema_path))
    output.mkdir(parents=True, exist_ok=False)
    write(output / "inventory.json", inventory)
    contract = {"version": VERSION,
                "input_hashes": {str(p.resolve()): digest(p) for p in (prepared_tracks, manifest, schema_path)},
                "code_hashes": {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob("*.py")},
                "selection": "all exact authorized nonholdout alignment-eligible packages; no family limit",
                "samples_per_lane": per_lane, "workers": workers, "source_labels_used": False,
                "accuracy_measured": False, "policy_changed": False,
                "production_modified": False, "external_transmission": False,
                "limits": ["Nonblind train/dev development diagnostics, not heldout accuracy.",
                           "All parts contribute to chord evidence; sampled lane supplies bounded geometry.",
                           "Source annotation is hashed for identity only; no annotation labels in analysis.",
                           "Budgets and unsupported windows are retained without pruning or replacement.",
                           "New orchestral families require separate readiness/edition/transposition checks."]}
    # No harmonic engine is called before every planned package is frozen.
    planned = []; preflight = []
    for row in inventory["rows"]:
        if not row["replay_eligible"]:
            continue
        try:
            ir, source = _freeze_package(row, output, schema)
            if not source["pitch_policy"]["harmonic_replay_allowed"]:
                preflight.append({"pair_id": row["pair_id"], "status": "source_transposition_blocked", "source": source})
                continue
            p = freeze_score(ir, per_lane)
            planned.append({"pair_id": row["pair_id"], "source": source, "plan": p})
        except Exception as exc:
            preflight.append({"pair_id": row["pair_id"], "status": "preflight_error",
                              "error_type": type(exc).__name__, "error": str(exc)})
    frozen_plan = {"version": VERSION, "packages": planned, "preflight": preflight,
                   "source_labels_used": False, "harmony_calculated_during_planning": False}
    write(output / "frozen-plan.json", frozen_plan)
    contract["frozen_plan_sha256"] = digest(output / "frozen-plan.json")
    write(output / "run-contract.json", contract)
    records = []; started = perf_counter()
    jobs = [(item, str(output.resolve())) for item in planned]
    with ProcessPoolExecutor(max_workers=workers) if workers > 1 else nullcontext() as executor:
        results = executor.map(_execute_package, jobs) if executor else map(_execute_package, jobs)
        for position, (item, local_records) in enumerate(zip(planned, results), 1):
            records.extend(local_records)
            print(f"[{position}/{len(planned)}] {item['pair_id']}: {len(local_records)} frozen windows", flush=True)
            # Intermediate report is explicitly incomplete and may be read while running.
            write(output / "progress.json", {"complete": False, "completed_packages": position,
                                             "records": records, "elapsed_seconds": round(perf_counter() - started, 3)})
    changed = []
    for path, expected in {**contract["input_hashes"], **contract["code_hashes"],
                           str((output / "frozen-plan.json").resolve()): contract["frozen_plan_sha256"]}.items():
        if digest(Path(path)) != expected:
            changed.append(path)
    for item in planned:
        source = item["source"]
        for path, expected in {**source["source_files"], source["original_ir_path"]: source["ir_sha256"],
                               source["frozen_ir_path"]: source["ir_sha256"],
                               source["preparation_path"]: source["preparation_sha256"]}.items():
            if digest(Path(path)) != expected:
                changed.append(path)
    families = {i["source"]["manifest_entry"]["work_family_id"] for i in planned}
    collection_counts = Counter(i["source"]["manifest_entry"]["collection_id"] for i in planned)
    report = {"version": VERSION, "complete": True, "inventory": {k: v for k, v in inventory.items() if k != "rows"},
              "frozen_packages": len(planned), "unique_work_families": len(families),
              "collection_packages": dict(collection_counts),
              "existing_split_packages": dict(Counter(i["source"]["manifest_entry"]["split"] for i in planned)),
              "planned_windows": sum(i["plan"]["planned_samples"] for i in planned),
              "executed_windows": len(records), "status_counts": dict(Counter(r["status"] for r in records)),
              "all_part_conservation_windows": sum(r.get("all_part_event_coverage_verified", False) for r in records),
              "stage_status_counts": {key: dict(Counter(r.get(key, "not_reached") for r in records))
                                      for key in ("continuous_status", "contrast_status", "lattice_status", "relation_status")},
              "executed_relation_pairs": sum(r.get("executed_relation_pairs", 0) for r in records),
              "hold_change_comparisons": sum(r.get("hold_change_summary", {}).get("comparisons", 0) for r in records),
              "accuracy_measured": False, "human_reviewed_windows": 0, "source_labels_used": False,
              "preflight": preflight, "records": records, "changed_input_paths": changed,
              "inputs_unchanged": not changed, "elapsed_seconds": round(perf_counter() - started, 3)}
    write(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-tracks", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples-per-lane", type=int, default=2)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    result = run(args.prepared_tracks, args.manifest, args.output, args.samples_per_lane, args.workers)
    print(json.dumps({k: result[k] for k in ("frozen_packages", "unique_work_families", "executed_windows", "status_counts", "inputs_unchanged")}, ensure_ascii=False))
    if result["changed_input_paths"] or any(r["status"] == "execution_error" for r in result["records"]) or any(r["status"] == "preflight_error" for r in result["preflight"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
