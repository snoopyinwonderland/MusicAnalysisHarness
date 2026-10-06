"""Post-seal replay of four-arm metrics, immutable hashes and winner costs."""
import argparse
from pathlib import Path
import json

from musicanote_harness import harmony_temporal_scoring_trial as trial
from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_progression_search import _hash


def compare_packet(packet, row):
    if "reference_cells" in packet or any("evaluation" in a for a in packet["arms"].values()):
        raise ValueError("reference_in_prediction")
    for k, v in packet.items():
        actual = row[k]
        if k == "arms": actual = {a: {n: val for n, val in r.items() if n != "evaluation"} for a, r in actual.items()}
        if _hash(v) != _hash(actual): raise ValueError("sealed_prediction_changed:"+k)


def run(root):
    root = Path(root); dest = root/"post-seal-audit.json"
    if dest.exists(): raise ValueError("output_exists_no_overwrite")
    report = trial.load(root/"report.json"); freeze = trial.load(root/"prediction-freeze.json")
    pins = report["input_hashes"] | report["code_hashes"] | report["artifact_hashes"]
    def check():
        for path, sha in pins.items():
            if trial.expanded.digest(path) != sha: raise ValueError("guard_changed:"+path)
    check()
    if freeze["labels_read"] is not False or freeze["contexts"] != report["contexts"]: raise ValueError("seal_changed")
    source = Path(trial.load(root/"run-contract.json")["baseline_source"])
    prior = {(r["pair_id"], r["sample_id"]): r for r in map(trial.load, trial.load(source/"prediction-freeze.json")["prediction_hashes"])}
    sealed = {(r["pair_id"], r["sample_id"]): r for r in map(trial.load, freeze["prediction_hashes"])}
    tables = {a: [] for a in trial.temporal.ARMS}; source_cache = {}; edges = 0; scores = 0
    for row in report["records"]:
        key = row["pair_id"], row["sample_id"]; old = prior.pop(key); packet = sealed.pop(key)
        compare_packet(packet, row)
        if row["sample_span"] != old["sample_span"] or row["plan_index"] != old["plan_index"]:
            raise ValueError("scope_changed")
        for arm, result in row["arms"].items():
            value = evaluate(native_reference(row), native_prediction(result["selected_prediction"], row["sample_span"]),
                row["sample_span"], selected=result["selected_prediction"] is not None)
            if value != result["evaluation"]: raise ValueError("evaluation_changed")
            tables[arm].append(row | result)
        if not row["attempted"]:
            if any(r["selected_prediction"] is not None or r["status"] != old["status"] for r in row["arms"].values()):
                raise ValueError("old_abstention_changed")
            continue
        if _hash(trial.musical_value(row["arms"]["baseline"]["selected_prediction"])) != _hash(trial.musical_value(old["selected_prediction"])):
            raise ValueError("baseline_prediction_changed")
        if trial.expanded.digest(row["graph_artifact"]) != row["graph_sha256"]: raise ValueError("graph_changed")
        saved = trial.load(row["graph_artifact"]); graph = trial.graph_from_packet(saved["problem"])
        if _hash(trial.graph_packet(graph)) != _hash(saved["problem"]): raise ValueError("graph_codec_changed")
        edges += len(graph.edges)
        source = saved["source"]; pair = row["pair_id"]
        if pair not in source_cache:
            ir = trial.load(source["canonical_ir_path"])
            if _hash(ir) != source["original_ir_content_sha256"]: raise ValueError("ir_case_changed")
            if trial.expanded.digest(source["source_musicxml_path"]) != source["original_musicxml_sha256"]:
                raise ValueError("xml_case_changed")
            view, grace = bounded.grace_projection(ir)
            source_cache[pair] = ir, view, grace
        ir, view, grace = source_cache[pair]
        gate = SourceClockGuard(ir).scope(row["sample_span"])
        if not gate["accepted"] or _hash(gate) != _hash(row["source_clock_gate"]): raise ValueError("clock_gate_changed")
        _, ev, _ = bounded.bound_evidence(view, row["sample_span"], grace)
        for arm, result in row["arms"].items():
            selected = result["selected_prediction"]
            if selected is None: continue
            if selected["confidence"] is not None or selected["human_validated"] is not False:
                raise ValueError("unsupported_confirmation")
            ids = trial.path_ids(selected)
            score = trial.temporal.score_path(graph, ev, ids, arm=arm)
            if trial.q(score) != selected["score_cost"]: raise ValueError("independent_winner_cost_changed")
            scores += 1
    if prior or sealed: raise ValueError("scope_denominator_changed")
    for arm, rows in tables.items():
        if summarize(rows) != report["tables"][arm]: raise ValueError("metric_table_changed")
    for saved in report["cases"]:
        case = trial.load(saved["case_path"]); graph = trial.graph_from_packet(trial.load(case["record"]["graph_artifact"])["problem"])
        ir, view, grace = source_cache[case["record"]["pair_id"]]
        _, ev, _ = bounded.bound_evidence(view, case["record"]["sample_span"], grace)
        if not case["reference_witness_never_used_for_inference"] or case["human_validated"]:
            raise ValueError("case_confirmation_changed")
        witness = case.get("reference_witness_scores")
        if witness:
            for arm, value in witness["costs"].items():
                if trial.q(trial.temporal.score_path(graph, ev, witness["existing_path_ids"], arm=arm)) != value:
                    raise ValueError("posthoc_reference_cost_changed")
    check()
    result = {"passed": True, "unique_hashes_checked": len(pins), "scopes": report["contexts"],
        "attempted_scopes": report["fresh_selected_scopes"], "full_source_packages": len(source_cache),
        "graph_edges_roundtripped": edges, "independent_winner_costs_checked": scores, "cases": len(report["cases"]),
        "metrics_replayed": list(tables), "new_inference_or_training_performed": False}
    trial.expanded.write(dest, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", required=True)
    args = parser.parse_args(); print(json.dumps(run(args.root), ensure_ascii=False, indent=2), flush=True)
