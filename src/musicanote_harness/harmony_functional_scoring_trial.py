"""J2e source-bound functional supply/score comparison on frozen J2d cohort."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_candidate_recall import fraction
from .harmony_evidence_scoring import prepare_with_evidence, score_path as old_score_path
from .harmony_evidence_scoring_trial import load_ir
from .harmony_functional_scoring import (
    FEATURE_VERSION, PAIR_WEIGHTS, ROLE_COST, decode, prepare_functional_evidence, supply,
)
from .harmony_lattice_recall import cells_from_record, diagnose
from .harmony_progression_search import _hash
from .harmony_scored_decoder import evaluation_path
from .harmony_scored_decoder_trial import evaluate_selection, summarize
from .harmony_structured_learning_trial import digest
from .source_locator_revision_trial import validate_policy

VERSION = "harmony-functional-scoring-trial-0.1.0"
ARMS = {"functional_supply_control": False, "functional_supply_and_resolution": True}


def run(previous_path, recall_path, integration_path, output, *, expected_previous_sha,
        expected_recall_sha, expected_integration_sha, smoke_contexts=0):
    started = perf_counter(); output = Path(output)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    if type(smoke_contexts) is not int or smoke_contexts < 0:
        raise ValueError("invalid_smoke_context_count")
    inputs = {}
    def read(path, expected, compressed=False, raw=False):
        path = Path(path); data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
        if sha != expected:
            raise ValueError("input_sha_mismatch:"+str(path))
        inputs[str(path.resolve())] = sha
        return None if raw else json.loads((gzip.decompress(data) if compressed else data).decode("utf-8"))
    def guard(mapping):
        for path, sha in mapping.items():
            if digest(path) != sha:
                raise ValueError("frozen_input_changed:"+str(path))
            inputs[str(Path(path).resolve())] = sha
    previous = read(previous_path, expected_previous_sha)
    recall = read(recall_path, expected_recall_sha)
    integration = read(integration_path, expected_integration_sha)
    if (any(r.get("complete") is not True for r in (previous, recall, integration))
            or previous.get("source_labels_used_at_inference") is not False
            or previous.get("training_performed") is not False
            or previous.get("development_tuning_performed") is not False
            or integration.get("source_labels_used") is not False):
        raise ValueError("invalid_parent_contract")
    guard(previous["input_hashes"]); guard(previous["code_hashes"])
    code_names = (Path(__file__).name, "harmony_functional_scoring.py", "applied_chords.py", "seventh_context.py",
                  "tonal_foundations.py", "harmony_evidence_scoring_trial.py")
    code_hashes = {str(Path(__file__).with_name(n).resolve()): digest(Path(__file__).with_name(n)) for n in code_names}
    if len(previous["records"]) != len(recall["records"]):
        raise ValueError("parent_context_count_mismatch")
    selected_records = list(zip(previous["records"], recall["records"]))
    if smoke_contexts:
        selected_records = selected_records[:smoke_contexts]
    rows = []; seen = set(); cache = {}; statuses = {a: Counter() for a in ARMS}; total_new = 0
    for index, (old, ref) in enumerate(selected_records, 1):
        identity = tuple(ref[k] for k in ("pair_id", "plan_index", "sample_id"))
        if identity in seen or identity != tuple(old[k] for k in ("pair_id", "plan_index", "sample_id")):
            raise ValueError("duplicate_or_mismatched_context")
        seen.add(identity)
        packet = read(old["search_artifact"], old["search_artifact_sha256"], True)
        context = read(old["source_context_artifact"], old["source_context_sha256"], True)
        provenance = context["provenance"]; entry = packet["provenance"]["manifest_entry"]; validate_policy(entry)
        bundle, search = context["bundle"], packet["search"]
        if (context["pair_id"] != ref["pair_id"] or packet["pair_id"] != ref["pair_id"]
                or context["plan_index"] != ref["plan_index"] or packet["plan_index"] != ref["plan_index"]
                or entry not in recall["package_manifest"] or entry["split"] != ref["split"]
                or entry["work_family_id"] != ref["work_family_id"] or packet["sample"]["sample_id"] != ref["sample_id"]
                or packet["sample"]["span"] != ref["sample_span"] or packet["provenance"] != provenance
                or _hash(bundle) != packet["input_bundle_content_sha256"]
                or search["input_bundle_content_sha256"] != packet["input_bundle_content_sha256"]):
            raise ValueError("context_source_binding_mismatch")
        key = ref["pair_id"], bundle["input_ir_content_sha256"]
        if key not in cache:
            cache[key] = load_ir(dict(entry, pair_id=ref["pair_id"]), provenance, bundle, integration, read)
        ir = cache[key]; problem, source = prepare_with_evidence(ir, bundle, search)
        if source.source_ir_content_sha256 != old["full_ir_content_sha256"]:
            raise ValueError("previous_source_ir_changed")
        # Pinned old selection is not rerun/tuned, but every selected old path
        # is checked against the unchanged score and full source binding.
        chosen = old["selected_predictions"]["source_evidence_music"]
        if chosen is not None:
            ids = [s["semantic_group_ref"] for s in chosen["segments"]]
            if old_score_path(problem, source, ids) != fraction(chosen["score_cost"]):
                raise ValueError("old_selection_score_changed")
        ev = prepare_functional_evidence(ir, source); expanded, receipts = supply(problem, ev)
        if expanded.edges[:len(problem.edges)] != problem.edges or expanded.points != problem.points or expanded.max_segments != problem.max_segments:
            raise ValueError("original_candidate_contract_changed")
        results = {a: decode(expanded, ev, functional_evidence=enabled) for a, enabled in ARMS.items()}
        # First reference access for the new analysis is AFTER both predictions.
        cells = cells_from_record(ref); evaluations = dict(old["evaluations"])
        for a, result in results.items():
            statuses[a][result["status"]] += 1
            evaluations[a] = evaluate_selection(evaluation_path(result), cells)
        oracle_search = dict(search, semantic_groups=[{"group_id": e.group_id, "from": e.start_index, "to": e.end_index,
                              "span": {"start": {"numerator": e.start.numerator, "denominator": e.start.denominator},
                                       "end": {"numerator": e.end.numerator, "denominator": e.end.denominator}},
                              "root_spelling": e.signature[0], "members": e.signature[1]} for e in expanded.edges])
        ceiling = diagnose(oracle_search, cells, expanded.points if expanded.status == "ready" else None,
                           {"candidate_hit": False, "selected_hit": False})
        if old["lattice_hit"] is True and ceiling["lattice_hit"] is not True:
            raise ValueError("previous_candidate_ceiling_lost")
        row = {k: ref[k] for k in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span")}
        row.update(evaluations=evaluations, selected_predictions={a: r["selected"] for a, r in results.items()},
                   decoder_details={a: {k: r[k] for k in ("status", "transitions", "exact_optimum_under_declared_score")} for a, r in results.items()},
                   functional_candidate_receipts=receipts, old_edge_count=len(problem.edges), expanded_edge_count=len(expanded.edges),
                   old_lattice_hit=old["lattice_hit"], expanded_lattice_diagnosis=ceiling, reference_cells=ref["reference_cells"],
                   full_ir_content_sha256=source.source_ir_content_sha256, voice_clock_statuses=ev.voice_statuses,
                   source_context_artifact=old["source_context_artifact"], source_context_sha256=old["source_context_sha256"],
                   search_artifact=old["search_artifact"], search_artifact_sha256=old["search_artifact_sha256"])
        rows.append(row); total_new += len(receipts)
        if index % 20 == 0 or index == len(selected_records):
            print(f"[{index}/{len(selected_records)}] functional supply/score, scores={len(cache)}, added={total_new}", flush=True)
    arms = tuple(rows[0]["evaluations"]) if rows else ()
    summary = {a: summarize(rows, a) for a in arms}
    if not smoke_contexts and any(summary[a] != val for a, val in previous["summary"].items()):
        raise ValueError("historical_summary_changed")
    changes = []
    for arm in ARMS:
        deltas = [(fraction(r["evaluations"][arm]["selected_root_members_time"])-fraction(r["evaluations"]["source_evidence_music"]["selected_root_members_time"]), i)
                  for i, r in enumerate(rows) if r["evaluations"][arm]["fully_evaluable"]]
        selected = {i for d, i in sorted(deltas)[:3] if d < 0} | {i for d, i in sorted(deltas, reverse=True)[:3] if d > 0}
        for i in sorted(selected):
            changes.append({"arm": arm, "context": rows[i], "previous_predictions": selected_records[i][0]["selected_predictions"]})
    guard(dict(inputs)); guard(code_hashes)
    report = {"version": VERSION, "complete": not bool(smoke_contexts), "smoke_contexts": smoke_contexts,
              "feature_version": FEATURE_VERSION, "summary": summary, "arms": ARMS,
              "by_split": {s: {a: summarize([r for r in rows if r["split"] == s], a) for a in arms} for s in sorted({r["split"] for r in rows})},
              "candidate_coverage": {"contexts": len(rows), "packages": len(cache), "work_families": len({r["work_family_id"] for r in rows}),
                                     "fully_evaluable_contexts": sum(r["evaluations"]["source_evidence_music"]["fully_evaluable"] for r in rows),
                                     "old_lattice_hit_contexts": sum(r["old_lattice_hit"] is True for r in rows),
                                     "expanded_lattice_hit_contexts": sum(r["expanded_lattice_diagnosis"]["lattice_hit"] is True for r in rows),
                                     "added_functional_candidate_readings": total_new, "original_candidates_removed": 0,
                                     "contexts_with_additions": sum(bool(r["functional_candidate_receipts"]) for r in rows)},
              "weights": {k: str(v) for k, v in PAIR_WEIGHTS.items()} | {"functional_role_complexity": str(ROLE_COST)},
              "decoder_statuses": {a: dict(v) for a, v in statuses.items()}, "records": rows,
              "input_hashes": inputs, "code_hashes": code_hashes, "elapsed_seconds": perf_counter()-started,
              "training_performed": False, "source_labels_used_at_inference": False, "development_tuning_performed": False,
              "independent_test_accuracy_measured": False, "old_candidate_inventory_modified": False,
              "new_candidate_inventory_is_separate": True, "previous_predictions_modified": False, "eligibility_changed": False,
              "production_modified": False, "metric_scope": previous["metric_scope"],
              "limits": ["Absolute root+spelled members/time evaluation, not full Roman/inversion/NCT/cadence accuracy.",
                         "6-4 alternative preserves literal surface root; functional role remains hypothetical.",
                         "No global/local key supplied: dominant-to-target support is not proof of Secondary function.",
                         "No absence-of-resolution penalty, optimistic NCT exemption or latent polyphonic voice guessing.",
                         "Same exposed overlapping train/dev cohort; candidate witness is an evaluator oracle only.",
                         "Original resource cap and raw segment cap are unchanged; no production deployment."]}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("report.json", report), ("selection-changes.json", changes)):
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("previous", "recall", "integration", "output", "expected-previous-sha", "expected-recall-sha", "expected-integration-sha"):
        p.add_argument("--"+n, required=True)
    p.add_argument("--smoke-contexts", type=int, default=0)
    a = p.parse_args(); result = run(a.previous, a.recall, a.integration, a.output, expected_previous_sha=a.expected_previous_sha,
                                   expected_recall_sha=a.expected_recall_sha, expected_integration_sha=a.expected_integration_sha,
                                   smoke_contexts=a.smoke_contexts)
    print(json.dumps({"candidate_coverage": result["candidate_coverage"], "summary": {a: result["summary"][a] for a in ARMS},
                      "elapsed_seconds": result["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
