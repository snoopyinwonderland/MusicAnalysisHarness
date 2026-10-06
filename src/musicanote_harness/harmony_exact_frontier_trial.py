"""Paired exact-resource recovery on the unchanged, sealed J3c windows.

Only transition-budget abstentions are retried. The 61 selected controls and
all source/context blockers are unchanged. Open reference-bearing reports
only after predictions have been physically sealed. No fitting or resampling.
"""
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json
import traceback

from .harmony_bounded_recovery_trial import load, oracle
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_exact_frontier import CONFIG, VERSION, infer
from .harmony_expanded_benchmark import digest, write, write_packet
from .harmony_candidate_recall import fraction
from .harmony_progression_search import _hash

BASELINE_REPORT_SHA = "a3bbd1ab7f6083e2ce5a3554396efb34f1620e51b72d1b8b36762dfa83f0d31f"


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    started = perf_counter(); guards = {}; artifacts = {}
    def read(path, expected=None):
        path = Path(path); sha = digest(path)
        if expected is not None and sha != expected: raise ValueError("pinned_input_changed:"+str(path))
        guards[str(path.resolve())] = sha
        return load(path)
    contract = read(source/"run-contract.json"); freeze = read(source/"prediction-freeze.json")
    if contract["source_labels_used_at_inference"] is not False or freeze["labels_read"] is not False:
        raise ValueError("baseline_phase_contract_invalid")
    code_pins = {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob("*.py")}
    if any(code_pins.get(p) != h for p, h in contract["code_pins"].items()): raise ValueError("baseline_engine_changed")
    plan = read(Path(contract["baseline_source"])/"frozen-plan.json")
    baseline_packets = [read(p, sha) for p, sha in sorted(freeze["prediction_hashes"].items())]
    packets = {(r["pair_id"], r["sample_id"]): r for r in baseline_packets}
    if len(packets) != freeze["contexts"]: raise ValueError("duplicate_or_missing_baseline_context")
    output.mkdir(parents=True); (output/"predictions").mkdir()
    def save(path, value, compressed=False):
        (write_packet if compressed else write)(path, value)
        artifacts[str(path.resolve())] = digest(path); return str(path.resolve())
    save(output/"run-contract.json", {"version": VERSION, "config": CONFIG,
        "baseline_source": str(source.resolve()), "frozen_plan_source": contract["baseline_source"],
        "baseline_report_expected_sha256": BASELINE_REPORT_SHA, "code_pins": code_pins,
        "same_frozen_windows": True, "resampling": False, "selected_controls_reused": True,
        "retry_condition": "transition_budget_abstention_only", "beam_pruning": False,
        "candidate_and_transition_budgets_unchanged": True, "weights_changed": False,
        "source_labels_used_at_inference": False, "training_performed": False,
        "new_prediction_seal_before_reference_report_read": True,
        "production_modified": False, "original_core_annotations_rights_splits_modified": False})
    records = []; graphs = {}
    for item in plan["packages"]:
        pair = item["entry"]["pair_id"]; ir = read(item["observation_ir_path"])
        if _hash(ir) != item["observation_ir_content_sha256"]: raise ValueError("frozen_observation_ir_changed")
        for planned in item["plan"]["selected_samples"]:
            sample = planned["sample"]; key = pair, sample["sample_id"]; old = packets.pop(key)
            if old["sample_span"] != sample["span"] or old["plan_index"] != planned["plan_index"]:
                raise ValueError("paired_window_changed")
            tick = perf_counter()
            row = deepcopy(old)
            row.pop("prediction_artifact", None); row.pop("elapsed_seconds", None)
            if "reference_cells" in row or "evaluation" in row: raise ValueError("unsealed_reference_contamination")
            row.update(previous_status=old["status"], frontier_attempted=False,
                       control_prediction_byte_value_preserved=old["selected_prediction"] is not None)
            if old["status"] == "transition_budget_abstention":
                if item["blockers"] or old["selected_prediction"] is not None: raise ValueError("invalid_retry_source_or_control")
                row["frontier_attempted"] = True
                try:
                    result, graph = infer(ir, sample); row.update(result); graphs[key] = graph
                except Exception as error:
                    row.update(status="execution_error", selected_prediction=None,
                        error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
            row["elapsed_seconds"] = perf_counter()-tick
            row["baseline_elapsed_seconds"] = old["elapsed_seconds"]
            row["prediction_artifact"] = save(output/"predictions"/(_hash(key)[:20]+".json.gz"), deepcopy(row), True)
            records.append(row)
            save(output/"progress.json", {"complete": False, "phase": "prediction_reference_report_unopened",
                "contexts": len(records), "last_status": row["status"], "elapsed_seconds": perf_counter()-started})
            print(f"[exact frontier {len(records)}] {pair} {sample['sample_id']}: {row['status']}", flush=True)
    if packets or len(records) != freeze["contexts"]: raise ValueError("context_denominator_changed")
    save(output/"prediction-freeze.json", {"version": VERSION, "labels_read": False, "contexts": len(records),
        "prediction_hashes": {r["prediction_artifact"]: artifacts[r["prediction_artifact"]] for r in records}})
    # Reference-bearing baseline is first opened AFTER the complete seal.
    baseline = read(source/"report.json", BASELINE_REPORT_SHA)
    for p, h in (baseline["input_hashes"] | baseline["code_hashes"] | baseline["artifact_hashes"]).items():
        if digest(p) != h: raise ValueError("baseline_source_or_artifact_changed:"+p)
        if p in guards and guards[p] != h: raise ValueError("baseline_guard_collision")
        guards[p] = h
    old_rows = {(r["pair_id"], r["sample_id"]): r for r in baseline["records"]}
    if set(old_rows) != {(r["pair_id"], r["sample_id"]) for r in records}: raise ValueError("baseline_keys_changed")
    for row in records:
        key = row["pair_id"], row["sample_id"]; old = old_rows[key]
        if not row["frontier_attempted"] and row["selected_prediction"] != old["selected_prediction"]:
            raise ValueError("control_prediction_changed")
        row["reference_cells"] = deepcopy(old["reference_cells"])
        row["evaluation"] = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
            row["sample_span"], selected=row["selected_prediction"] is not None)
        if key in graphs:
            cells = [{"start": fraction(c["span"]["start"]), "end": fraction(c["span"]["end"]),
                "signature": None if c["signature"] is None else
                (tuple(c["signature"][0]) if c["signature"][0] is not None else None,
                 tuple(tuple(m) for m in c["signature"][1]))} for c in row["reference_cells"]]
            row["candidate_ceiling"] = oracle(graphs.pop(key), cells, row["evaluation"]["selected_hit"])
        else: row["candidate_ceiling"] = deepcopy(old["candidate_ceiling"])
    if summarize(baseline["records"]) != baseline["table"]: raise ValueError("baseline_metric_replay_mismatch")
    for p, h in (guards | code_pins | artifacts).items():
        if digest(p) != h: raise ValueError("input_or_artifact_changed:"+p)
    tried = [r for r in records if r["frontier_attempted"]]
    report = {"version": VERSION, "complete": True, "baseline_table": baseline["table"], "table": summarize(records),
        "status_counts": dict(Counter(r["status"] for r in records)), "frontier_attempts": len(tried),
        "recovered_selections": sum(r["selected_prediction"] is not None for r in tried),
        "unchanged_selected_controls": sum(r["control_prediction_byte_value_preserved"] for r in records),
        "attempted_elapsed_seconds": sum(r["elapsed_seconds"] for r in tried),
        "baseline_attempted_elapsed_seconds": sum(r["baseline_elapsed_seconds"] for r in tried),
        "baseline_attempts_finished_exact_search": False,
        "by_collection": {c: summarize([r for r in records if r["collection_id"] == c]) for c in sorted({r["collection_id"] for r in records})},
        "records": records, "input_hashes": guards, "code_hashes": code_pins, "artifact_hashes": artifacts,
        "all_new_predictions_sealed_before_reference_report_read": True, "source_labels_used_at_inference": False,
        "weights_changed": False, "training_performed": False, "independent_test_accuracy_measured": False,
        "beam_pruning": False, "full_roman_accuracy_measured": False, "production_modified": False,
        "original_core_annotations_rights_splits_modified": False, "elapsed_seconds": perf_counter()-started}
    write(output/"report.json", report)
    return {k: v for k, v in report.items() if k not in ("records", "input_hashes", "code_hashes", "artifact_hashes", "by_collection")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True); p.add_argument("--output", required=True)
    args = p.parse_args(); result = run(args.source, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if result["status_counts"].get("execution_error"): raise SystemExit(1)
