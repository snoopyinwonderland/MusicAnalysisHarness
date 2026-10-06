"""Fixed, source-bound J2d ablation on the same frozen 322 contexts.

    python -m musicanote_harness.harmony_evidence_scoring_trial --help

Weights are declared in code BEFORE evaluation. No training, dev tuning,
candidate addition, old prediction rewrite, UI deployment or gold inference.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_candidate_recall import fraction
from .harmony_evidence_scoring import (
    BASE_WEIGHTS, EVIDENCE_WEIGHTS, FEATURE_VERSION, LIMITS, decode,
    prepare_with_evidence, run_features,
)
from .harmony_lattice_recall import cells_from_record
from .harmony_progression_search import _hash
from .harmony_scored_decoder import decode as baseline_decode, evaluation_path
from .harmony_scored_decoder_trial import evaluate_selection, summarize
from .harmony_structured_learning_trial import digest
from .source_locator_revision_trial import validate_policy

VERSION = "harmony-evidence-scoring-trial-0.1.0"
ARMS = {"harmonic_run_only": False, "source_evidence_music": True}


def load_ir(entry, provenance, bundle, integration, read):
    """Select only the previously explicit measure revision; no fresh parsing."""
    matches = [r for r in integration["measure_revisions"] if r["pair_id"] == entry["pair_id"]]
    if len(matches) != 1:
        raise ValueError("missing_or_duplicate_ir_revision")
    row = matches[0]; path = row["sidecar"]
    if path != provenance["measure_revision_sidecar"] or row["status"] != provenance["measure_revision_status"]:
        raise ValueError("revision_provenance_mismatch")
    sidecar = read(path, integration["artifact_hashes"][path])
    snap = sidecar["verification_payload"]["parent_snapshot"]
    parent = read(snap["parent_ir"], snap["parent_ir_sha256"])
    if (_hash(parent) != sidecar["parent_content_sha256"]
            or parent["ir_document_id"] != row["parent_ir_document_id"]):
        raise ValueError("parent_ir_revision_binding_mismatch")
    # Read bytes/hash, not source label/text content, to guard the score origin.
    read(snap["source_xml"], entry["score_sha256"], raw=True)
    if row["candidate_created"] is True:
        path = row["candidate_ir"]
        working = read(path, integration["artifact_hashes"][path])
        if _hash(working) != sidecar["candidate_content_sha256"]:
            raise ValueError("candidate_ir_revision_binding_mismatch")
    elif row["candidate_created"] is False and row["candidate_ir"] is None and sidecar["status"] == "not_required":
        working = parent
    else:
        raise ValueError("unsupported_revision_selection")
    if (working["ir_document_id"] != row["working_ir_document_id"]
            or working["ir_document_id"] != provenance["working_ir_document_id"]
            or _hash(working) != bundle["input_ir_content_sha256"]):
        raise ValueError("working_ir_bundle_binding_mismatch")
    return working


def run(recall_path, baseline_path, margin_path, integration_path, output, *,
        expected_recall_sha, expected_baseline_sha, expected_margin_sha, expected_integration_sha):
    started = perf_counter(); output = Path(output)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    inputs = {}
    def read(path, expected, compressed=False, raw=False):
        path = Path(path); data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
        if sha != expected:
            raise ValueError("input_sha_mismatch:"+str(path))
        inputs[str(path.resolve())] = sha
        if raw:
            return None
        return json.loads((gzip.decompress(data) if compressed else data).decode("utf-8"))
    def guard(mapping):
        for path, sha in mapping.items():
            if digest(path) != sha:
                raise ValueError("frozen_input_changed:"+str(path))
            inputs[str(Path(path).resolve())] = sha
    recall = read(recall_path, expected_recall_sha)
    baseline = read(baseline_path, expected_baseline_sha)
    margin = read(margin_path, expected_margin_sha)
    integration = read(integration_path, expected_integration_sha)
    if (any(r.get("complete") is not True for r in (recall, baseline, margin, integration))
            or margin.get("source_labels_used_at_inference") is not False
            or integration.get("source_labels_used") is not False
            or margin.get("development_labels_used_for_updates_or_checkpoint_selection") is not False):
        raise ValueError("invalid_parent_contract")
    for report in (baseline, margin):
        guard(report["input_hashes"]); guard(report["code_hashes"])
    code_hashes = {str(Path(__file__).resolve()): digest(__file__),
                   str(Path(__file__).with_name("harmony_evidence_scoring.py").resolve()): digest(Path(__file__).with_name("harmony_evidence_scoring.py"))}
    if len({len(r["records"]) for r in (recall, baseline, margin)}) != 1:
        raise ValueError("parent_context_count_mismatch")
    rows, seen, ir_cache, statuses = [], set(), {}, {a: Counter() for a in ARMS}
    source_receipts, collisions, collision_count = {}, [], 0
    for index, (ref, base, previous) in enumerate(zip(recall["records"], baseline["records"], margin["records"]), 1):
        identity = tuple(ref[k] for k in ("pair_id", "plan_index", "sample_id"))
        if identity in seen or any(identity != tuple(r[k] for k in ("pair_id", "plan_index", "sample_id")) for r in (base, previous)):
            raise ValueError("duplicate_or_mismatched_context")
        if any(previous["evaluations"].get(a) != val for a, val in base["evaluations"].items()):
            raise ValueError("historical_evaluation_changed")
        seen.add(identity)
        context = read(previous["source_context_artifact"], previous["source_context_sha256"], True)
        packet = read(previous["search_artifact"], previous["search_artifact_sha256"], True)
        provenance = context["provenance"]; entry = packet["provenance"]["manifest_entry"]
        validate_policy(entry)
        bundle, search = context["bundle"], packet["search"]
        if (context["pair_id"] != ref["pair_id"] or packet["pair_id"] != ref["pair_id"]
                or context["plan_index"] != ref["plan_index"] or packet["plan_index"] != ref["plan_index"]
                or entry not in recall["package_manifest"] or entry["split"] != ref["split"]
                or entry["work_family_id"] != ref["work_family_id"]
                or packet["sample"]["sample_id"] != ref["sample_id"]
                or packet["sample"]["span"] != ref["sample_span"]
                or packet["provenance"] != provenance or _hash(bundle) != packet["input_bundle_content_sha256"]):
            raise ValueError("context_source_binding_mismatch")
        cache_key = ref["pair_id"], bundle["input_ir_content_sha256"]
        if cache_key not in ir_cache:
            ir_cache[cache_key] = load_ir(dict(entry, pair_id=ref["pair_id"]), provenance, bundle, integration, read)
        ir = ir_cache[cache_key]
        problem, evidence = prepare_with_evidence(ir, bundle, search)
        fixed = baseline_decode(problem)
        if _hash(fixed["selected"]) != _hash(base["selected_prediction"]):
            raise ValueError("original_prediction_changed")
        # Both arm selections finish BEFORE any reference is read for evaluation.
        results = {a: decode(problem, evidence, musical_evidence=enabled) for a, enabled in ARMS.items()}
        cells = cells_from_record(ref)
        evaluations = dict(previous["evaluations"])
        for arm, result in results.items():
            statuses[arm][result["status"]] += 1
            evaluations[arm] = evaluate_selection(evaluation_path(result), cells)
        rows.append({k: ref[k] for k in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span")}
                    | {"selected_predictions": {a: r["selected"] for a, r in results.items()},
                       "decoder_details": {a: {k: r[k] for k in ("status", "transitions", "exact_optimum_under_declared_score")} for a, r in results.items()},
                       "evaluations": evaluations, "reference_cells": ref["reference_cells"],
                       "source_context_artifact": previous["source_context_artifact"], "source_context_sha256": previous["source_context_sha256"],
                       "search_artifact": previous["search_artifact"], "search_artifact_sha256": previous["search_artifact_sha256"],
                       "full_ir_content_sha256": evidence.source_ir_content_sha256,
                       "lattice_hit": previous["lattice_hit"], "lattice_diagnosis": previous["lattice_diagnosis"]})
        source_receipts[ref["pair_id"]] = {"score_id": ir["score"]["score_id"], "full_ir_content_sha256": evidence.source_ir_content_sha256,
                                         "clock_identity_statuses": evidence.voice_statuses,
                                         "unique_contiguous_neighbor_triplets": len(evidence.neighbors)}
        # Label-blind diagnostics: identical old emission features, distinct
        # signatures in the SAME interval, now distinguishable by observations.
        old_vectors = {}
        for edge in problem.edges:
            vector = (edge.start_index, edge.end_index, tuple(sorted((k, v) for k, v in edge.features.items())))
            old_vectors.setdefault(vector, []).append(edge)
        for group in old_vectors.values():
            if len({e.signature for e in group}) < 2:
                continue
            values = [(e, run_features(problem, evidence, e.start, e.end, e.signature)[0]) for e in group]
            vectors = {tuple((k, v) for k, v in f.items() if k in EVIDENCE_WEIGHTS) for _, f in values}
            if len(vectors) < 2:
                continue
            collision_count += 1
            if len(collisions) < 12:
                collisions.append({"sample_id": ref["sample_id"], "pair_id": ref["pair_id"], "split": ref["split"],
                                   "span": {"start": group[0].start.__str__(), "end": group[0].end.__str__()},
                                   "new_features": [{"group_id": e.group_id, "root_spelling": e.signature[0], "members": e.signature[1],
                                                     "features": {k: None if v is None else str(v) for k, v in f.items() if k in EVIDENCE_WEIGHTS}} for e, f in values],
                                   "old_emission_features_identical": True, "musical_truth_established": False})
        if index % 40 == 0 or index == len(recall["records"]):
            print(f"[{index}/{len(recall['records'])}] source-bound inference + evaluation, scores={len(ir_cache)}", flush=True)
        del packet, context, bundle, search
    arms = tuple(rows[0]["evaluations"])
    summary = {a: summarize(rows, a) for a in arms}
    if any(summary[a] != val for a, val in margin["summary"].items()):
        raise ValueError("historical_summary_changed")
    changes = []
    for arm in ARMS:
        deltas = [(fraction(r["evaluations"][arm]["selected_root_members_time"])-fraction(r["evaluations"]["direct_joint_music"]["selected_root_members_time"]), i)
                  for i, r in enumerate(rows) if r["evaluations"][arm]["fully_evaluable"]]
        chosen = {i for d, i in sorted(deltas)[:3] if d < 0} | {i for d, i in sorted(deltas, reverse=True)[:3] if d > 0}
        for i in sorted(chosen):
            r = rows[i]; changes.append({"arm": arm, "context": r, "fixed_prediction": baseline["records"][i]["selected_prediction"]})
    guard(dict(inputs)); guard(code_hashes)
    report = {"version": VERSION, "complete": True, "feature_version": FEATURE_VERSION,
              "summary": summary, "by_split": {s: {a: summarize([r for r in rows if r["split"] == s], a) for a in arms} for s in sorted({r["split"] for r in rows})},
              "weights": {k: str(v) for k, v in (BASE_WEIGHTS | EVIDENCE_WEIGHTS).items()},
              "arms": ARMS, "decoder_statuses": {a: dict(v) for a, v in statuses.items()},
              "source_receipts": source_receipts, "old_emission_collision_groups_now_distinguishable": collision_count,
              "records": rows, "input_hashes": inputs, "code_hashes": code_hashes,
              "elapsed_seconds": perf_counter()-started,
              "training_performed": False, "source_labels_used_at_inference": False,
              "development_tuning_performed": False, "independent_test_accuracy_measured": False,
              "candidate_inventory_modified": False, "previous_predictions_modified": False,
              "eligibility_changed": False, "production_modified": False,
              "metric_scope": margin["metric_scope"],
              "limits": LIMITS+["Fixed exploratory weights, no dev tuning/arm selection/deployment.",
                                 "Same previously exposed train/dev windows, not independent full-score evaluation.",
                                 "Semantic run invariance applies to identical candidate blocker exposure; blockers stay additive."]}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("report.json", report), ("selection-changes.json", changes), ("feature-separation.json", collisions)):
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("recall", "baseline", "margin", "integration", "output", "expected-recall-sha", "expected-baseline-sha", "expected-margin-sha", "expected-integration-sha"):
        p.add_argument("--"+name, required=True)
    a = p.parse_args()
    r = run(a.recall, a.baseline, a.margin, a.integration, a.output,
            expected_recall_sha=a.expected_recall_sha, expected_baseline_sha=a.expected_baseline_sha,
            expected_margin_sha=a.expected_margin_sha, expected_integration_sha=a.expected_integration_sha)
    print(json.dumps({"summary": {a: r["summary"][a] for a in ARMS}, "elapsed_seconds": r["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
