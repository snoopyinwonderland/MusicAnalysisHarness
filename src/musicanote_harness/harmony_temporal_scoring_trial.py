"""Fixed four-arm, same-graph ablation on ALL selected frozen J3 contexts.

Known development results, not an independent blind test. Never select a scope
by gold correctness. Freeze predictions before the annotation-bearing report.
Keep nine old abstentions and their denominators; do not force long recovery.
"""
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json

from . import harmony_bounded_recovery as bounded
from . import harmony_expanded_benchmark as expanded
from . import harmony_temporal_scoring as temporal
from .harmony_bounded_recovery_trial import load
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_source_clock import SourceClockGuard
from .harmony_window_workspace import WindowWorkspace
from .harmony_streaming_joint import encode_edge, decode_edge
from .harmony_scored_decoder import Problem
from .harmony_candidate_recall import fraction as f, rational as q
from .harmony_progression_search import _hash

VERSION = "harmony-temporal-scoring-trial-0.1.0"
BASELINE_REPORT_SHA = "9b241d30c26966741af1c4bcddfa4ba07e2c29a70def5e2648c02adb65973a60"


def graph_packet(problem):
    return {"points": [q(t) for t in problem.points], "edges": [encode_edge(e) for e in problem.edges],
        "max_segments": problem.max_segments, "total_note_time": q(problem.total_note_time),
        "status": problem.status, "zero_duration_event_ids": problem.zero_duration_event_ids}


def graph_from_packet(packet):
    return Problem(tuple(f(t) for t in packet["points"]), tuple(decode_edge(e) for e in packet["edges"]),
        packet["max_segments"], f(packet["total_note_time"]), packet["status"],
        tuple(packet["zero_duration_event_ids"]))


def path_ids(selected):
    return [s["semantic_group_ref"] for s in selected["segments"]]


def musical_value(selected):
    """No backend/proposal metadata: compare the actual chosen event contract."""
    return None if selected is None else {"cost": selected["score_cost"], "segments": selected["segments"]}


def prepare(ir, sample, baseline):
    """Reconstruct each historical graph by its original observation route.

60 short selections use original J3b candidates; the three bounded recoveries
use J3c candidates. No candidate algorithm or budget changes between arms.
"""
    if not baseline.get("recovery_attempted", False):
        stages = expanded.analyze_sample(ir, sample)
        bundle = expanded.bundle(ir, stages)
        search = expanded.search(bundle, max_segments=expanded.CONFIG["max_segments"],
            per_state_limit=expanded.CONFIG["per_state_limit"], max_complete_paths=expanded.CONFIG["max_complete_paths"],
            transition_budget=expanded.CONFIG["search_transition_budget"])
        problem, source = expanded.prepare_with_evidence(ir, bundle, search)
        ev = expanded.prepare_functional_evidence(ir, source)
        graph, receipts = expanded.supply(problem, ev)
        return graph, ev, {"route": "original_J3b", "functional_candidate_receipts": receipts,
            "search": search, "stage_summary": stages["summary"], "consumer_projection": None}
    view, grace = bounded.grace_projection(ir)
    plan = bounded.tile_plan(view, sample["span"])
    permitted = {"nonpositive_duration"} if grace["grace_sounding_events"] else set()
    remaining = sorted(set(sample.get("abstention_reasons", []))-permitted)
    if remaining: plan.update(status="sample_scope_abstention", blockers=remaining)
    source, ev, links = bounded.bound_evidence(view, sample["span"], grace)
    workspace = WindowWorkspace(view)
    graph, origins = workspace.build(plan, source)
    graph, receipts = expanded.supply(graph, ev)
    return graph, ev, {"route": "bounded_J3c", "functional_candidate_receipts": receipts,
        "candidate_origin_groups": origins, "tile_plan": plan, "link_withholding": links,
        "consumer_projection": grace, "window_reuse": workspace.receipt()}


def path_receipt(problem, ev, ids):
    """Post-selection audit only, NOT a source of candidate/gold features."""
    ev = temporal.frontier.scoped_functional_evidence(problem, ev)
    lookup = {e.group_id: e for e in problem.edges}; edges = [lookup[i] for i in ids]
    runs = []
    for e in edges:
        if runs and runs[-1][2] == e.signature: runs[-1] = runs[-1][0], e.end, e.signature
        else: runs.append((e.start, e.end, e.signature))
    resolution = []
    for left, right in zip(runs, runs[1:]):
        values, details = temporal.resolution_features(ev, left[0], left[1], right[1], left[2], right[2])
        if details:
            resolution.append({"boundary": q(left[1]), "features": {k: q(v) for k, v in values.items()},
                "details": details})
    return {"existing_path_ids": ids, "raw_edges": len(ids), "harmonic_runs": len(runs),
        "costs": {a: q(temporal.score_path(problem, ev, ids, arm=a)) for a in temporal.ARMS},
        "resolution_observations": resolution,
        "root_observations": [d for a, b, sig in runs for d in temporal.deferred_root(problem, ev.source, a, b, sig)[1]],
        "source_labels_used_to_create_this_path": False}


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    started = perf_counter(); guards = {}; artifacts = {}
    def read(path, expected=None):
        p = Path(path); sha = expanded.digest(p)
        if expected is not None and sha != expected: raise ValueError("pinned_input_changed:"+str(p))
        if str(p.resolve()) in guards and guards[str(p.resolve())] != sha: raise ValueError("input_changed_during_read")
        guards[str(p.resolve())] = sha
        return load(p)
    contract = read(source/"run-contract.json"); freeze = read(source/"prediction-freeze.json")
    if freeze["labels_read"] is not False or contract["source_labels_used_at_inference"] is not False:
        raise ValueError("unsealed_baseline")
    for p, h in contract["code_pins"].items():
        if expanded.digest(p) != h: raise ValueError("baseline_engine_changed:"+p)
        guards[p] = h
    code = {str(p.resolve()): expanded.digest(p) for p in Path(__file__).parent.glob("*.py")}
    for p in (Path("tests/test_harmony_temporal_scoring.py"), Path("tests/test_harmony_temporal_scoring_trial.py")):
        if p.exists(): code[str(p.resolve())] = expanded.digest(p)
    plan = read(Path(contract["frozen_plan_source"])/"frozen-plan.json")
    packets = [read(p, h) for p, h in sorted(freeze["prediction_hashes"].items())]
    old = {(r["pair_id"], r["sample_id"]): r for r in packets}
    if len(old) != freeze["contexts"] or any("reference_cells" in r or "evaluation" in r for r in packets):
        raise ValueError("invalid_or_reference_bearing_prediction_packets")
    output.mkdir(parents=True)
    for name in ("predictions", "graphs", "sources", "cases"): (output/name).mkdir()
    def save(p, value, compressed=False):
        (expanded.write_packet if compressed else expanded.write)(p, value)
        artifacts[str(p.resolve())] = expanded.digest(p)
        return str(p.resolve())
    save(output/"run-contract.json", {"version": VERSION, "baseline_source": str(source.resolve()),
        "baseline_report_expected_sha256": BASELINE_REPORT_SHA, "code_pins": code,
        "frozen_plan_source": contract["frozen_plan_source"], "arms": temporal.ARMS,
        "replay_condition": "all_baseline_selected_contexts_independent_of_correctness",
        "same_72_scopes": True, "one_same_original_graph_per_scope_all_four_arms": True,
        "old_abstentions_not_retried": True, "new_feature_weight": q(temporal.ROOT_WEIGHT),
        "existing_weight_values_changed": False, "nonbaseline_scoring_contract_changed": True,
        "transition_budget": 2_000_000, "source_labels_used_at_inference": False,
        "training_performed": False, "parameter_sweep": False, "independent_test_accuracy_measured": False,
        "production_modified": False, "original_core_annotations_splits_rights_modified": False})
    rows = []; source_cases = {}; graph_paths = {}
    for item in plan["packages"]:
        pair = item["entry"]["pair_id"]; ir = read(item["observation_ir_path"])
        if _hash(ir) != item["observation_ir_content_sha256"]: raise ValueError("observation_ir_changed")
        clock = SourceClockGuard(ir)
        for planned in item["plan"]["selected_samples"]:
            sample = planned["sample"]; key = pair, sample["sample_id"]; baseline = old.pop(key)
            if baseline["sample_span"] != sample["span"] or baseline["plan_index"] != planned["plan_index"]:
                raise ValueError("paired_scope_changed")
            row = {k: deepcopy(baseline[k]) for k in ("pair_id", "sample_id", "sample_span", "plan_index",
                "collection_id", "work_family_id", "reference_binding_verified")}
            row.update(attempted=baseline["selected_prediction"] is not None,
                known_prior_diagnostic=bool(baseline.get("frontier_attempted")), source_clock_gate=clock.scope(sample["span"]))
            if row["source_clock_gate"] != baseline["source_clock_gate"]: raise ValueError("source_clock_gate_changed")
            if row["attempted"]:
                if item["blockers"] or not row["source_clock_gate"]["accepted"]: raise ValueError("ineligible_attempt")
                if pair not in source_cases:
                    folder = output/"sources"/_hash(pair)[:20]; folder.mkdir()
                    ir_path = save(folder/"canonical-ir.json.gz", ir, True)
                    src = Path(item["preparation"]["source_paths"]["score"])
                    sha = expanded.digest(src)
                    if sha != item["preparation"]["source_sha256"]["score"]: raise ValueError("case_source_changed")
                    guards[str(src.resolve())] = sha
                    dst = folder/"source.musicxml"; dst.write_bytes(src.read_bytes())
                    artifacts[str(dst.resolve())] = expanded.digest(dst)
                    if artifacts[str(dst.resolve())] != sha: raise ValueError("source_copy_changed")
                    source_cases[pair] = {"canonical_ir_path": ir_path, "source_musicxml_path": str(dst.resolve()),
                        "original_ir_content_sha256": _hash(ir), "original_musicxml_sha256": sha,
                        "full_score_saved_with_surrounding_context": True}
                tick = perf_counter(); graph, ev, receipt = prepare(ir, sample, baseline)
                row["graph_build_seconds"] = perf_counter()-tick
                packet = {"source": source_cases[pair], "pair_id": pair, "sample_id": sample["sample_id"],
                    "span": sample["span"], "problem": graph_packet(graph), "receipts": receipt}
                row["graph_artifact"] = save(output/"graphs"/(_hash(key)[:20]+".json.gz"), packet, True)
                row["graph_sha256"] = artifacts[row["graph_artifact"]]
                graph_paths[key] = row["graph_artifact"]
                historical = path_receipt(graph, ev, path_ids(baseline["selected_prediction"]))
                if historical["costs"]["baseline"] != baseline["selected_prediction"]["score_cost"]:
                    raise ValueError("historical_path_cost_changed")
                row["historical_selected_path_scores"] = historical
                row["arms"] = {}
                for arm in temporal.ARMS:
                    tick = perf_counter(); result = temporal.decode(graph, ev, arm=arm)
                    if arm == "baseline" and _hash(musical_value(result["selected"])) != _hash(musical_value(baseline["selected_prediction"])):
                        raise ValueError("fresh_same_graph_baseline_winner_changed")
                    row["arms"][arm] = {"status": result["status"], "selected_prediction": result["selected"],
                        "elapsed_seconds": perf_counter()-tick, "transitions": result["transitions"],
                        "exact_optimum_under_declared_score": result["exact_optimum_under_declared_score"],
                        "search_diagnostics": result["search_diagnostics"],
                        "temporal_scoring_contract": result["temporal_scoring_contract"]}
                    if result["selected"] is not None:
                        check = temporal.score_path(graph, ev, path_ids(result["selected"]), arm=arm)
                        if check != f(result["selected"]["score_cost"]): raise ValueError("winner_independent_cost_mismatch")
                row["fresh_baseline_winner_verified"] = True
            else:
                row["arms"] = {a: {"status": baseline["status"], "selected_prediction": None,
                    "elapsed_seconds": 0, "reused_old_abstention": True} for a in temporal.ARMS}
            clock.check_source()
            row["prediction_artifact"] = save(output/"predictions"/(_hash(key)[:20]+".json.gz"), row, True)
            rows.append(row)
            save(output/"progress.json", {"complete": False, "phase": "all_predictions_before_reference_read",
                "scopes": len(rows), "elapsed_seconds": perf_counter()-started})
            print(f"[temporal {len(rows)}/{freeze['contexts']}] {pair}: "+
                ", ".join(a+":"+r["status"] for a, r in row["arms"].items()), flush=True)
    if old or len(rows) != freeze["contexts"]: raise ValueError("denominator_changed")
    save(output/"prediction-freeze.json", {"version": VERSION, "labels_read": False, "contexts": len(rows),
        "prediction_hashes": {r["prediction_artifact"]: artifacts[r["prediction_artifact"]] for r in rows}})
    # First reference-bearing report read. Development cases have prior exposure,
    # so sealing is a leakage guard, NOT a claim of independent blind evaluation.
    baseline = read(source/"report.json", BASELINE_REPORT_SHA)
    for p, h in (baseline["input_hashes"] | baseline["code_hashes"] | baseline["artifact_hashes"]).items():
        if expanded.digest(p) != h: raise ValueError("baseline_artifact_changed:"+p)
        guards[p] = h
    refs = {(r["pair_id"], r["sample_id"]): r for r in baseline["records"]}
    if set(refs) != {(r["pair_id"], r["sample_id"]) for r in rows}: raise ValueError("reference_scope_changed")
    tables = {}; changed = []; cases = []
    for row in rows:
        key = row["pair_id"], row["sample_id"]; ref = refs[key]
        row["reference_cells"] = deepcopy(ref["reference_cells"])
        row["candidate_ceiling"] = deepcopy(ref["candidate_ceiling"])
        for arm, result in row["arms"].items():
            result["evaluation"] = evaluate(native_reference(row), native_prediction(result["selected_prediction"], row["sample_span"]),
                row["sample_span"], selected=result["selected_prediction"] is not None)
        base = row["arms"]["baseline"]["evaluation"]
        changed_arms = [a for a in temporal.ARMS if a != "baseline" and
            _hash(native_prediction(row["arms"][a]["selected_prediction"], row["sample_span"])) !=
            _hash(native_prediction(row["arms"]["baseline"]["selected_prediction"], row["sample_span"]))]
        if changed_arms:
            changed.append({"pair_id": row["pair_id"], "sample_id": row["sample_id"], "arms": changed_arms,
                "time_deltas": {a: q(f(row["arms"][a]["evaluation"]["components"]["root_members"]["matched"])-
                    f(base["components"]["root_members"]["matched"])) for a in changed_arms}})
        if row["attempted"] and (changed_arms or row["known_prior_diagnostic"]):
            graph_data = read(graph_paths[key]); graph = graph_from_packet(graph_data["problem"])
            ir = read(graph_data["source"]["canonical_ir_path"])
            view, grace = bounded.grace_projection(ir)
            _, ev, _ = bounded.bound_evidence(view, row["sample_span"], grace)
            case = {"source": graph_data["source"], "record": row, "changed_arms": changed_arms,
                "scored_selected_paths": {a: path_receipt(graph, ev, path_ids(v["selected_prediction"]))
                    for a, v in row["arms"].items() if v["selected_prediction"] is not None},
                "independent_test_case": False, "human_validated": False,
                "reference_witness_never_used_for_inference": True}
            witness = ref["candidate_ceiling"].get("oracle_reference_witness") if ref["candidate_ceiling"] else None
            if witness:
                case["reference_witness_scores"] = path_receipt(graph, ev, witness)
                case["reference_witness_scores"]["source_labels_used_to_create_this_path"] = True
            cases.append({"pair_id": row["pair_id"], "sample_id": row["sample_id"],
                "case_path": save(output/"cases"/(_hash(key)[:20]+".json.gz"), case, True)})
    for arm in temporal.ARMS:
        records = [r | r["arms"][arm] for r in rows]
        tables[arm] = summarize(records)
    if tables["baseline"] != baseline["table"]: raise ValueError("baseline_metric_changed")
    for p, h in (guards | code | artifacts).items():
        if expanded.digest(p) != h: raise ValueError("guard_changed:"+p)
    report = {"version": VERSION, "complete": True, "contexts": len(rows),
        "fresh_selected_scopes": sum(r["attempted"] for r in rows), "full_source_packages": len(source_cases),
        "known_diagnostic_scopes": sum(r["known_prior_diagnostic"] for r in rows),
        "tables": tables, "status_counts": {a: dict(Counter(r["arms"][a]["status"] for r in rows)) for a in temporal.ARMS},
        "changed": changed, "cases": cases, "records": rows,
        "input_hashes": guards, "code_hashes": code, "artifact_hashes": artifacts,
        "all_predictions_sealed_before_reference_report_read": True,
        "source_labels_used_at_inference": False, "training_performed": False, "parameter_sweep": False,
        "independent_test_accuracy_measured": False, "full_roman_accuracy_measured": False,
        "new_rules_adopted_for_production": False, "production_modified": False,
        "elapsed_seconds": perf_counter()-started}
    expanded.write(output/"report.json", report)
    return {k: v for k, v in report.items() if k not in ("records", "input_hashes", "code_hashes", "artifact_hashes", "tables", "changed")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), ensure_ascii=False, indent=2), flush=True)
