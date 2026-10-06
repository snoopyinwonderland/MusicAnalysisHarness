"""Frozen long-context trial. Labels are opened only after all predictions seal.

Only resource-only abstentions are attempted. Existing controls and semantic,
repeat and source-clock abstentions are not reinferred or silently repaired.
"""
import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from time import perf_counter
import json

from . import harmony_bounded_recovery as bounded
from . import harmony_streaming_joint as streaming
from .harmony_window_workspace import WindowWorkspace
from .harmony_source_clock import SourceClockGuard
from .harmony_bounded_recovery_trial import load
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_expanded_benchmark import digest, write, write_packet
from .harmony_progression_search import _hash

BASELINE_REPORT_SHA = "6a77673c46dd01fb92ebb91225d3a3ed071b97ad9f2a473480e1676dd830d216"


def eligible(item, sample, baseline, gate):
    return (baseline["status"] == "bounded_plan_abstention" and gate["accepted"]
            and not item.get("blockers") and not sample.get("abstention_reasons")
            and bool(baseline.get("tile_plan", {}).get("blockers"))
            and set(baseline["tile_plan"]["blockers"]) <= streaming.RESOURCE_BLOCKERS)


def attempt(ir, sample, folder, save):
    started = perf_counter(); before = _hash(ir)
    view, grace = bounded.grace_projection(ir)
    plan = streaming.streaming_plan(view, sample["span"])
    if plan["status"] != "ready": raise ValueError("attempt_not_resource_only")
    evidence, functional, links = bounded.bound_evidence(view, sample["span"], grace)
    problem = streaming.header(view, plan, evidence)
    ranges = [(t["start_index"], t["end_index"]) for t in plan["tiles"]]
    session = streaming.JointStream(problem, functional, ranges)
    workspace = WindowWorkspace(view); ledger = {}; pages = []; resume = None
    for tile in plan["tiles"]:
        print(f"[page build] {sample['sample_id']} {tile['tile_index']+1}/{len(ranges)}", flush=True)
        page_start = perf_counter()
        page, origins, receipts = streaming.build_page(workspace, plan, tile, evidence, functional)
        packet = {"version": streaming.VERSION, "binding_sha256": session.binding,
            "tile": tile, "points": plan["points"], "total_note_time": streaming.q(problem.total_note_time),
            "raw_cap": problem.max_segments, "status": page.status,
            "edges": [streaming.encode_edge(e) for e in page.edges],
            "origins": origins, "functional_receipts": receipts}
        page_path = save(folder/f"page-{tile['tile_index']:03d}.json.gz", packet, True)
        for e in page.edges:
            if e.group_id in ledger: raise ValueError("duplicate_ledger_id")
            ledger[e.group_id] = page_path
        page_sha = digest(page_path)
        progress = session.consume(page)
        info = {"tile_index": tile["tile_index"], "path": page_path, "sha256": page_sha,
                "candidate_edges": len(page.edges), "progress": progress,
                "elapsed_seconds": perf_counter()-page_start}
        if session.status == "stream_pending":
            checkpoint = session.snapshot()
            cp = save(folder/f"checkpoint-{tile['tile_index']:03d}.json.gz", checkpoint, True)
            info.update(checkpoint_path=cp, checkpoint_sha256=digest(cp),
                        frontier_states=len(checkpoint["frontier"]))
            # A real disk reload after the first page proves restart semantics;
            # all further checkpoints remain available without losing hot caches.
            if tile["tile_index"] == 0:
                restored = streaming.JointStream(problem, functional, ranges, checkpoint=load(cp))
                if restored.snapshot() != checkpoint: raise ValueError("checkpoint_disk_replay_changed")
                resume = {"checkpoint_path": cp, "checkpoint_sha256": digest(cp),
                          "operations_before": session.operations, "operations_after": restored.operations,
                          "binding_sha256": session.binding, "same_full_frontier": True}
                session = restored
        pages.append(info)
        print(f"[page done] {sample['sample_id']} {tile['tile_index']+1}/{len(ranges)}: "
              f"{len(page.edges)} edges, {session.operations} cumulative ops, {session.status}", flush=True)
        if session.status != "stream_pending": break

    page_hashes = {p["path"]: p["sha256"] for p in pages}
    def winning_edges(ids):
        # Only original winning pages are decoded, never tile winners or an
        # unpinned reconstruction. Every source candidate stays in the ledger.
        current_path = None; rows = {}
        for gid in ids:
            path = ledger[gid]
            if path != current_path:
                if digest(path) != page_hashes[path]: raise ValueError("winning_page_changed")
                rows = {e["group_id"]: e for e in load(path)["edges"]}; current_path = path
            yield streaming.decode_edge(rows[gid])
    result = session.finish(winning_edges)
    if _hash(ir) != before or _hash(view) != grace["consumer_view_sha256"]:
        raise ValueError("stream_inference_mutated_inputs")
    return {"version": streaming.VERSION, "status": result["status"],
        "selected_prediction": result["selected"], "transitions": result["operations"],
        "exact_optimum_under_declared_graph": result["exact_optimum_under_declared_score"],
        "search_diagnostics": result["statistics"], "stream_result": result,
        "grace_projection": grace, "tile_plan": plan, "link_withholding": links,
        "lattice_edge_count": result["statistics"]["original_edges"],
        "stream_pages": pages, "checkpoint_disk_resume": resume,
        "candidate_inventory_complete": len(pages) == len(ranges) and all(load(p["path"])["status"] == "ready" for p in pages),
        "window_reuse": workspace.receipt(), "elapsed_seconds": perf_counter()-started,
        "source_labels_used_at_inference": False, "weights_changed": False,
        "production_modified": False, "formal_core_modified": False}


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    started = perf_counter(); guards = {}; artifacts = {}
    def read(p, expected=None):
        p = Path(p); sha = digest(p)
        if expected is not None and sha != expected: raise ValueError("pinned_input_changed:"+str(p))
        guards[str(p.resolve())] = sha; return load(p)
    contract = read(source/"run-contract.json"); freeze = read(source/"prediction-freeze.json")
    if freeze["labels_read"] or contract["source_labels_used_at_inference"]: raise ValueError("unsealed_baseline")
    code = {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob("*.py")}
    for p in (Path("tests/test_harmony_streaming_joint.py"), Path("tests/test_harmony_streaming_joint_trial.py"),
              Path("scripts/audit_harmony_streaming_joint.py")):
        if p.exists(): code[str(p.resolve())] = digest(p)
    for p, sha in contract["code_pins"].items():
        if digest(p) != sha: raise ValueError("baseline_engine_changed:"+p)
    plan = read(Path(contract["frozen_plan_source"])/"frozen-plan.json")
    packets = [read(p, h) for p, h in sorted(freeze["prediction_hashes"].items())]
    old = {(r["pair_id"], r["sample_id"]): r for r in packets}
    if len(old) != freeze["contexts"]: raise ValueError("baseline_context_count")
    if any("reference_cells" in r or "evaluation" in r for r in packets): raise ValueError("reference_contamination")
    output.mkdir(parents=True); (output/"predictions").mkdir(); (output/"cases").mkdir()
    def save(p, value, compressed=False):
        (write_packet if compressed else write)(p, value)
        artifacts[str(p.resolve())] = digest(p); return str(p.resolve())
    save(output/"run-contract.json", {"version": streaming.VERSION, "baseline_source": str(source.resolve()),
        "frozen_plan_source": contract["frozen_plan_source"], "baseline_report_expected_sha256": BASELINE_REPORT_SHA,
        "code_pins": code, "resource_contract": streaming.CONFIG, "same_frozen_windows": True,
        "tile_winner_stitching": False, "source_labels_used_at_inference": False,
        "training_performed": False, "weights_changed": False, "production_modified": False})
    rows = []; cases = []
    for item in plan["packages"]:
        pair = item["entry"]["pair_id"]; ir = read(item["observation_ir_path"])
        if _hash(ir) != item["observation_ir_content_sha256"]: raise ValueError("observation_ir_changed")
        clock = SourceClockGuard(ir)
        for planned in item["plan"]["selected_samples"]:
            sample = planned["sample"]; key = pair, sample["sample_id"]; prior = old.pop(key)
            if prior["sample_span"] != sample["span"] or prior["plan_index"] != planned["plan_index"]:
                raise ValueError("paired_scope_changed")
            gate = clock.scope(sample["span"])
            if _hash(gate) != _hash(prior["source_clock_gate"]): raise ValueError("source_gate_changed")
            row = deepcopy(prior); row.pop("prediction_artifact", None)
            fresh = eligible(item, sample, prior, gate)
            row.update(streaming_attempted=fresh, baseline_prediction_reused=not fresh)
            if fresh:
                folder = output/"cases"/_hash(key)[:20]; folder.mkdir()
                irpath = save(folder/"canonical-ir.json.gz", ir, True)
                xml = Path(item["preparation"]["source_paths"]["score"])
                sha = digest(xml)
                if sha != item["preparation"]["source_sha256"]["score"]: raise ValueError("case_source_changed")
                guards[str(xml.resolve())] = sha; copy = folder/"source.musicxml"
                copy.write_bytes(xml.read_bytes()); artifacts[str(copy.resolve())] = digest(copy)
                if digest(copy) != sha: raise ValueError("case_copy_changed")
                row.update(attempt(ir, sample, folder, save))
                # No historical full graph/ceiling is advertised as this partial inventory.
                for field in ("functional_candidate_receipts", "candidate_origin_groups"):
                    row.pop(field, None)
                case = {"pair_id": pair, "sample_id": sample["sample_id"], "context_span": sample["span"],
                    "full_ir_content_sha256": _hash(ir), "canonical_ir_path": irpath,
                    "source_musicxml_path": str(copy.resolve()), "full_source_musicxml_sha256": sha,
                    "baseline_selected_prediction": prior["selected_prediction"], "baseline_status": prior["status"],
                    "result": deepcopy(row), "source_labels_used": False, "musical_feedback_needed": False}
                cases.append({"pair_id": pair, "sample_id": sample["sample_id"],
                              "case_path": save(folder/"case.json", case)})
            row["prediction_artifact"] = save(output/"predictions"/(_hash(key)[:20]+".json.gz"), row, True)
            rows.append(row)
        clock.check_source()
    if old or len(rows) != freeze["contexts"]: raise ValueError("denominator_changed")
    save(output/"prediction-freeze.json", {"version": streaming.VERSION, "labels_read": False, "contexts": len(rows),
        "prediction_hashes": {r["prediction_artifact"]: artifacts[r["prediction_artifact"]] for r in rows},
        "pre_reference_artifact_hashes": dict(artifacts)})
    # FIRST annotation-bearing read, after all new and reused packets seal.
    baseline = read(source/"report.json", BASELINE_REPORT_SHA)
    for p, sha in (baseline["input_hashes"] | baseline["code_hashes"] | baseline["artifact_hashes"]).items():
        if digest(p) != sha: raise ValueError("baseline_artifact_changed:"+p)
        if p in guards and guards[p] != sha: raise ValueError("guard_collision")
        guards[p] = sha
    refs = {(r["pair_id"], r["sample_id"]): r for r in baseline["records"]}
    if set(refs) != {(r["pair_id"], r["sample_id"]) for r in rows}: raise ValueError("reference_scope_changed")
    for row in rows:
        ref = refs[row["pair_id"], row["sample_id"]]
        if row["baseline_prediction_reused"] and _hash(row["selected_prediction"]) != _hash(ref["selected_prediction"]):
            raise ValueError("control_prediction_changed")
        row["reference_cells"] = deepcopy(ref["reference_cells"])
        row["historical_candidate_ceiling"] = deepcopy(ref["candidate_ceiling"])
        row["candidate_ceiling"] = None if row["streaming_attempted"] else deepcopy(ref["candidate_ceiling"])
        row["candidate_ceiling_recomputed"] = False
        row["evaluation"] = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
            row["sample_span"], selected=row["selected_prediction"] is not None)
    for p, sha in (guards | code | artifacts).items():
        if digest(p) != sha: raise ValueError("guard_changed:"+p)
    report = {"version": streaming.VERSION, "complete": True, "contexts": len(rows), "source_packages": len(plan["packages"]),
        "attempts": sum(r["streaming_attempted"] for r in rows),
        "unchanged_controls": sum(r["baseline_prediction_reused"] for r in rows),
        "new_selected_contexts": sum(r["streaming_attempted"] and r["selected_prediction"] is not None for r in rows),
        "status_counts": dict(Counter(r["status"] for r in rows)), "baseline_table": baseline["table"], "table": summarize(rows),
        "records": rows, "cases": cases, "input_hashes": guards, "code_hashes": code, "artifact_hashes": artifacts,
        "all_predictions_sealed_before_reference_report_read": True, "source_labels_used_at_inference": False,
        "weights_changed": False, "training_performed": False, "production_modified": False,
        "candidate_pruning": False, "tile_winner_stitching": False, "elapsed_seconds": perf_counter()-started}
    write(output/"report.json", report)
    return {k: v for k, v in report.items() if k not in ("records", "input_hashes", "code_hashes", "artifact_hashes")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); print(json.dumps(run(args.source, args.output), ensure_ascii=False, indent=2), flush=True)
