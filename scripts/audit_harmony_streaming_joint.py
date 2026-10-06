"""Post-seal source, page, checkpoint, winner and metric verification."""
import argparse
from dataclasses import replace
from pathlib import Path
import json

from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness import harmony_streaming_joint as streaming
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_bounded_recovery_trial import load
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_expanded_benchmark import digest, write
from musicanote_harness.harmony_progression_search import _hash


def run(root):
    root = Path(root); destination = root/"post-seal-audit.json"
    if destination.exists(): raise ValueError("output_exists_no_overwrite")
    report = load(root/"report.json"); freeze = load(root/"prediction-freeze.json")
    hashes = report["input_hashes"] | report["code_hashes"] | report["artifact_hashes"]
    def check():
        for p, sha in hashes.items():
            if digest(p) != sha: raise ValueError("guard_changed:"+p)
    check()
    for p, sha in (freeze["prediction_hashes"] | freeze["pre_reference_artifact_hashes"]).items():
        if digest(p) != sha: raise ValueError("sealed_artifact_changed")
    if freeze["labels_read"] or freeze["contexts"] != report["contexts"]: raise ValueError("invalid_seal")
    baseline_root = Path(load(root/"run-contract.json")["baseline_source"])
    previous = {(r["pair_id"], r["sample_id"]): r for r in map(load, load(baseline_root/"prediction-freeze.json")["prediction_hashes"])}
    sealed = {(r["pair_id"], r["sample_id"]): r for r in map(load, freeze["prediction_hashes"])}
    metrics = []; controls = 0
    for row in report["records"]:
        key = row["pair_id"], row["sample_id"]; old = previous.pop(key); packet = sealed.pop(key)
        if "reference_cells" in packet or "evaluation" in packet: raise ValueError("reference_in_prediction")
        if row["sample_span"] != old["sample_span"]: raise ValueError("scope_changed")
        for field, value in packet.items():
            if field != "prediction_artifact" and _hash(row[field]) != _hash(value): raise ValueError("sealed_result_changed")
        if row["baseline_prediction_reused"]:
            for field, value in old.items():
                if field != "prediction_artifact" and _hash(row[field]) != _hash(value): raise ValueError("control_changed")
            controls += 1
        value = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
                         row["sample_span"], selected=row["selected_prediction"] is not None)
        if value != row["evaluation"]: raise ValueError("metric_changed")
        metrics.append(dict(row, evaluation=value))
    if previous or sealed or len(metrics) != freeze["contexts"] or summarize(metrics) != report["table"]:
        raise ValueError("denominator_or_table_changed")
    cases = []; total_pages = 0; total_edges = 0
    for saved in report["cases"]:
        case = load(saved["case_path"]); result = case["result"]; ir = load(case["canonical_ir_path"])
        if _hash(ir) != case["full_ir_content_sha256"] or digest(case["source_musicxml_path"]) != case["full_source_musicxml_sha256"]:
            raise ValueError("full_source_case_changed")
        gate = SourceClockGuard(ir).scope(case["context_span"])
        if not gate["accepted"] or _hash(gate) != _hash(result["source_clock_gate"]): raise ValueError("clock_gate_changed")
        view, grace = bounded.grace_projection(ir); plan = streaming.streaming_plan(view, case["context_span"])
        if _hash(plan) != _hash(result["tile_plan"]) or plan["blockers"]: raise ValueError("page_plan_changed")
        evidence, functional, _ = bounded.bound_evidence(view, case["context_span"], grace)
        problem = streaming.header(view, plan, evidence); ranges = [(t["start_index"], t["end_index"]) for t in plan["tiles"]]
        binding = streaming.JointStream(problem, functional, ranges).binding
        operations = 0; seen = {}; restored_count = 0
        for index, info in enumerate(result["stream_pages"]):
            if digest(info["path"]) != info["sha256"]: raise ValueError("page_changed")
            page = load(info["path"]); tile = plan["tiles"][index]
            if (page["binding_sha256"] != binding or page["tile"] != tile or page["points"] != plan["points"]
                    or page["raw_cap"] != problem.max_segments or page["total_note_time"] != streaming.q(problem.total_note_time)):
                raise ValueError("page_objective_changed")
            edges = tuple(streaming.decode_edge(e) for e in page["edges"])
            if len(edges) != info["candidate_edges"]: raise ValueError("page_edge_count_changed")
            if any(not tile["start_index"] <= e.start_index < e.end_index <= tile["end_index"] for e in edges):
                raise ValueError("page_crosses_partition")
            streaming.canonical_edges(replace(problem, edges=edges, status=page["status"]))
            for edge in edges:
                if edge.group_id in seen: raise ValueError("duplicate_page_id")
                seen[edge.group_id] = edge
            next_ops = info["progress"]["operations"]
            if not operations <= next_ops <= streaming.CONFIG["decoder_operations"]: raise ValueError("operation_budget_reset")
            operations = next_ops
            if "checkpoint_path" in info:
                if digest(info["checkpoint_path"]) != info["checkpoint_sha256"]: raise ValueError("checkpoint_changed")
                cp = load(info["checkpoint_path"])
                restored = streaming.JointStream(problem, functional, ranges, checkpoint=cp)
                if restored.snapshot() != cp or restored.operations != operations or restored.at != index+1:
                    raise ValueError("checkpoint_replay_changed")
                if set(restored.seen) != set(seen): raise ValueError("checkpoint_inventory_changed")
                restored_count += 1
            total_pages += 1; total_edges += len(edges)
        if operations != result["transitions"] or len(seen) != result["lattice_edge_count"]: raise ValueError("final_counter_changed")
        selected = result["selected_prediction"]
        if selected is not None:
            if len(result["stream_pages"]) != len(ranges): raise ValueError("partial_inventory_selected")
            cp = load(result["stream_pages"][-1]["checkpoint_path"])
            final = streaming.JointStream(problem, functional, ranges, checkpoint=cp).finish(lambda ids: [seen[gid] for gid in ids])
            if _hash(final["selected"]) != _hash(selected): raise ValueError("independent_winner_changed")
        elif result["exact_optimum_under_declared_graph"] and result["status"] != "no_complete_path_under_segment_cap":
            raise ValueError("abstention_claimed_exact")
        cases.append({"pair_id": saved["pair_id"], "sample_id": saved["sample_id"],
            "pages_verified": len(result["stream_pages"]), "checkpoints_restored": restored_count,
            "operations": operations, "selected": selected is not None, "status": result["status"],
            "full_source_and_fine_grid_preserved": True})
    check()
    summary = {"complete": True, "report_sha256": digest(root/"report.json"), "verified_unique_sha256_files": len(hashes),
        "scope_and_metric_replays": len(metrics), "immutable_control_replays": controls,
        "pages_verified": total_pages, "original_candidate_edges_verified": total_edges, "cases": cases,
        "same_table_as_baseline": report["table"] == report["baseline_table"],
        "production_modified": False, "weights_changed": False}
    write(destination, summary); return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", required=True)
    args = parser.parse_args(); print(json.dumps(run(args.root), ensure_ascii=False, indent=2))
