"""Replay factored joint search and validate immutable paired controls."""
import argparse
from copy import deepcopy
from pathlib import Path

from musicanote_harness.harmony_batched_frontier import infer
from musicanote_harness.harmony_bounded_recovery_trial import load
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_expanded_benchmark import digest, write, write_packet
from musicanote_harness.harmony_progression_search import _hash
from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness.harmony_exact_frontier import RunIndex
from musicanote_harness.harmony_evidence_scoring import run_features


def run(folder, output, replay=False):
    folder, output = Path(folder), Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    report = load(folder/"report.json"); contract = load(folder/"run-contract.json")
    if report["complete"] is not True or report["source_labels_used_at_inference"] is not False: raise ValueError("invalid_report")
    guards = report["input_hashes"] | report["code_hashes"] | report["artifact_hashes"]
    for path, sha in guards.items():
        if digest(path) != sha: raise ValueError("guard_changed:"+path)
    baseline_folder = Path(contract["baseline_source"])
    baseline = load(baseline_folder/"report.json"); plan = load(Path(contract["frozen_plan_source"])/"frozen-plan.json")
    original = {(r["pair_id"], r["sample_id"]): r for r in baseline["records"]}
    planned = {(p["entry"]["pair_id"], s["sample"]["sample_id"]): (p, s["sample"])
               for p in plan["packages"] for s in p["plan"]["selected_samples"]}
    observed = {(r["pair_id"], r["sample_id"]) for r in report["records"]}
    if len(observed) != len(report["records"]) or observed != set(original) or observed != set(planned): raise ValueError("denominator_changed")
    sealed = load(folder/"prediction-freeze.json")
    if sealed["contexts"] != len(observed) or sealed["labels_read"] is not False: raise ValueError("invalid_seal")
    cases = []; controls = replays = feature_checks = 0
    output.mkdir(parents=True); (output/"cases").mkdir()
    for row in report["records"]:
        key = row["pair_id"], row["sample_id"]; old = original[key]; p, sample = planned[key]
        if row["sample_span"] != sample["span"] or row["plan_index"] != old["plan_index"]: raise ValueError("scope_changed")
        packet = load(row["prediction_artifact"])
        if digest(row["prediction_artifact"]) != sealed["prediction_hashes"][row["prediction_artifact"]]: raise ValueError("prediction_changed")
        if any(row[k] != v for k, v in packet.items()): raise ValueError("post_reference_prediction_changed")
        if row["reference_cells"] != old["reference_cells"]: raise ValueError("reference_or_unknown_mask_changed")
        actual = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
                          row["sample_span"], selected=row["selected_prediction"] is not None)
        if actual != row["evaluation"]: raise ValueError("metric_replay_mismatch")
        if old["selected_prediction"] is not None:
            if row["frontier_attempted"] or row["selected_prediction"] != old["selected_prediction"]: raise ValueError("control_prediction_changed")
            controls += 1
        if p["blockers"] and (row["frontier_attempted"] or row["selected_prediction"] is not None): raise ValueError("source_gate_bypassed")
        if row["frontier_attempted"]:
            for field in ("tile_plan", "grace_projection", "link_withholding", "lattice_edge_count",
                          "candidate_origin_groups", "functional_candidate_receipts"):
                if _hash(row[field]) != _hash(old[field]): raise ValueError("source_graph_or_gate_changed:"+field)
            ir = load(p["observation_ir_path"])
            if replay:
                rebuilt, graph = infer(ir, sample)
                if any(_hash(row[k]) != _hash(v) for k, v in rebuilt.items()): raise ValueError("fresh_inference_replay_mismatch")
                view, grace = bounded.grace_projection(ir)
                evidence, _, _ = bounded.bound_evidence(view, sample["span"], grace)
                indexer = RunIndex(graph, evidence)
                signatures = sorted({e.signature for e in graph.edges}, key=repr)
                intervals = [(a, b) for i, a in enumerate(graph.points) for b in graph.points[i+1:]]
                # Fixed source-geometry samples, never selected using gold/errors.
                for n in range(64):
                    a, b = intervals[(n*179+13) % len(intervals)]
                    sig = signatures[(n*31+7) % len(signatures)]
                    if indexer.features(a, b, sig) != run_features(graph, evidence, a, b, sig):
                        raise ValueError("real_case_feature_integral_mismatch")
                    feature_checks += 1
                replays += 1
                print(f"[fresh inference replay {replays}] {key}: exact", flush=True)
            source = Path(p["preparation"]["source_paths"]["score"])
            if digest(source) != p["entry"]["score_sha256"]: raise ValueError("physical_case_source_changed")
            xml_path = output/"cases"/(p["entry"]["score_sha256"][:20]+".musicxml")
            if not xml_path.exists(): xml_path.write_bytes(source.read_bytes())
            ir_path = output/"cases"/(_hash(key)[:20]+"-observation-ir.json.gz")
            write_packet(ir_path, ir)
            cases.append({"pair_id": key[0], "sample_id": key[1], "span": sample["span"],
                "baseline_status": old["status"], "frontier_status": row["status"],
                "before": old["evaluation"], "after": row["evaluation"],
                "selected_prediction": deepcopy(row["selected_prediction"]),
                "tile_plan": deepcopy(row.get("tile_plan")), "grace_projection": deepcopy(row.get("grace_projection")),
                "search_diagnostics": deepcopy(row.get("search_diagnostics")),
                "reference_cells": deepcopy(row["reference_cells"]),
                "full_score_xml_path": str(xml_path.resolve()), "full_score_xml_sha256": digest(xml_path),
                "full_observation_ir_path": str(ir_path.resolve()), "full_observation_ir_sha256": digest(ir_path),
                "posthoc_reproduction_case_not_training_or_new_accuracy_sample": True})
    if summarize(report["records"]) != report["table"] or summarize(baseline["records"]) != report["baseline_table"]:
        raise ValueError("aggregate_replay_mismatch")
    for path, sha in guards.items():
        if digest(path) != sha: raise ValueError("guard_changed_during_audit")
    result = {"complete": True, "report_sha256": digest(folder/"report.json"), "auditor_sha256": digest(__file__),
        "guarded_unique_files": len(guards), "all_guards_unchanged": True, "exact_metric_replay": True,
        "same_contexts": len(observed), "immutable_selected_controls": controls, "fresh_inference_replays": replays,
        "real_case_original_feature_comparisons": feature_checks,
        "baseline_table": report["baseline_table"], "table": report["table"], "cases": cases,
        "production_modified": False, "independent_blind_test_accuracy": False}
    write(output/"audit.json", result)
    print({k: v for k, v in result.items() if k not in ("cases", "baseline_table", "table")}, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True); p.add_argument("--output", required=True); p.add_argument("--replay", action="store_true")
    a = p.parse_args(); run(a.source, a.output, a.replay)
