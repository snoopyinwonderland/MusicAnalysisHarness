"""Paired recovery on the SAME J3b windows, never reference-guided resampling.

Previously selected hypotheses are immutable controls. Recover only engine
abstentions; source-preflight failures remain blocked. Seal all new prediction
packets before opening the old post-reference report. No weight fitting.
"""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
import traceback

from .harmony_bounded_recovery import infer, VERSION, CONFIG
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_expanded_benchmark import digest, write, write_packet
from .harmony_lattice_recall import diagnose
from .harmony_progression_search import _hash

BASELINE_REPORT_SHA = "71926c9155b81fd1d9792ec6cf1b79c31a1b9aa2e45c636e31e227990f3bf182"


def load(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith(".gz") else data)


def oracle(problem, cells, selected_hit):
    proposal = {"lattice_status": problem.status, "budgets": {"max_segments": problem.max_segments},
        "unspelled_candidates": [], "semantic_groups": [{"group_id": e.group_id, "from": e.start_index, "to": e.end_index,
            "span": {"start": {"numerator": e.start.numerator, "denominator": e.start.denominator},
                     "end": {"numerator": e.end.numerator, "denominator": e.end.denominator}},
            "root_spelling": e.signature[0], "members": e.signature[1]} for e in problem.edges]}
    result = diagnose(proposal, cells, problem.points if problem.status == "ready" else None,
                      {"candidate_hit": False, "selected_hit": selected_hit})
    if result["lattice_hit"] is True:
        result["outcome"] = "selected_correct" if selected_hit else "reference_reachable_selection_error"
    result["retained24_measured"] = False
    return result


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    started = perf_counter(); guards = {}; artifacts = {}
    def read(path, expected=None):
        path = Path(path); sha = digest(path)
        if expected is not None and sha != expected: raise ValueError("pinned_input_changed:"+str(path))
        guards[str(path.resolve())] = sha
        return load(path)
    plan = read(source/"frozen-plan.json"); freeze = read(source/"prediction-freeze.json")
    contract = read(source/"run-contract.json")
    if freeze["labels_read"] is not False or contract["source_labels_used_at_inference"] is not False:
        raise ValueError("baseline_phase_contract_invalid")
    code_pins = {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob("*.py")}
    if any(code_pins.get(p) != h for p, h in contract["code_pins"].items()): raise ValueError("baseline_engine_changed")
    output.mkdir(parents=True); (output/"predictions").mkdir()
    def save(path, data, compressed=False):
        (write_packet if compressed else write)(path, data)
        artifacts[str(path.resolve())] = digest(path)
        return str(path.resolve())
    save(output/"run-contract.json", {"version": VERSION, "config": CONFIG, "baseline_source": str(source.resolve()),
        "baseline_report_expected_sha256": BASELINE_REPORT_SHA, "code_pins": code_pins,
        "paired_same_72_windows": True, "resampling": False, "previously_selected_predictions_reused": True,
        "new_prediction_seal_before_reference_report_read": True, "weights_changed": False,
        "source_labels_used_at_inference": False, "training_performed": False, "independent_blind_test": False,
        "production_modified": False, "original_core_annotations_rights_splits_modified": False})
    records = []; problems = {}
    baseline_packets = [read(path, sha) for path, sha in sorted(freeze["prediction_hashes"].items())]
    packets = {(r["pair_id"], r["sample_id"]): r for r in baseline_packets}
    if len(packets) != freeze["contexts"]: raise ValueError("duplicate_or_missing_baseline_context")
    for item in plan["packages"]:
        pair = item["entry"]["pair_id"]; ir = read(item["observation_ir_path"])
        if _hash(ir) != item["observation_ir_content_sha256"]: raise ValueError("frozen_observation_ir_changed")
        for planned in item["plan"]["selected_samples"]:
            sample = planned["sample"]; key = pair, sample["sample_id"]
            old = packets.pop(key); tick = perf_counter()
            if old["sample_span"] != sample["span"] or old["plan_index"] != planned["plan_index"]:
                raise ValueError("paired_window_changed")
            row = {k: deepcopy(old[k]) for k in ("pair_id", "work_family_id", "collection_id", "sample_id",
                "sample_span", "plan_index", "reference_binding_verified")}
            row["baseline_status"] = old["status"]
            if item["blockers"]:
                if old["status"] != "source_preflight_abstention": raise ValueError("source_blocker_mismatch")
                row.update(status=old["status"], selected_prediction=None, recovery_attempted=False, blockers=item["blockers"])
            elif old["selected_prediction"] is not None:
                row.update(status=old["status"], selected_prediction=deepcopy(old["selected_prediction"]),
                           recovery_attempted=False, control_prediction_byte_value_preserved=True)
            else:
                row["recovery_attempted"] = True
                try:
                    recovery, problem = infer(ir, sample)
                    row.update(recovery); problems[key] = problem
                except Exception as error:
                    row.update(status="execution_error", selected_prediction=None,
                               error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
            row["elapsed_seconds"] = perf_counter()-tick
            name = _hash(key)[:20]+".json.gz"
            row["prediction_artifact"] = save(output/"predictions"/name, deepcopy(row), True)
            records.append(row)
            save(output/"progress.json", {"complete": False, "phase": "prediction_reference_report_unopened",
                "contexts": len(records), "last_status": row["status"], "elapsed_seconds": perf_counter()-started})
            print(f"[recovery {len(records)}] {pair} {sample['sample_id']}: {row['status']}", flush=True)
    if packets or len(records) != freeze["contexts"]: raise ValueError("context_denominator_changed")
    save(output/"prediction-freeze.json", {"version": VERSION, "labels_read": False, "contexts": len(records),
        "prediction_hashes": {r["prediction_artifact"]: artifacts[r["prediction_artifact"]] for r in records}})
    # No report with reference labels was opened before this physical seal.
    baseline = read(source/"report.json", BASELINE_REPORT_SHA)
    for path, sha in (baseline["input_hashes"] | baseline["code_hashes"] | baseline["artifact_hashes"]).items():
        if digest(path) != sha: raise ValueError("baseline_source_or_artifact_changed:"+path)
        if path in guards and guards[path] != sha: raise ValueError("baseline_guard_collision")
        guards[path] = sha
    original = {(r["pair_id"], r["sample_id"]): r for r in baseline["records"]}
    for row in records:
        old = original[row["pair_id"], row["sample_id"]]
        row["reference_cells"] = deepcopy(old["reference_cells"])
        row["evaluation"] = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
                                     row["sample_span"], selected=row["selected_prediction"] is not None)
        key = row["pair_id"], row["sample_id"]
        if key in problems:
            from .harmony_candidate_recall import fraction
            cells = [{"start": fraction(c["span"]["start"]), "end": fraction(c["span"]["end"]),
                      "signature": None if c["signature"] is None else
                      (tuple(c["signature"][0]) if c["signature"][0] is not None else None, tuple(tuple(m) for m in c["signature"][1]))}
                     for c in row["reference_cells"]]
            row["candidate_ceiling"] = oracle(problems.pop(key), cells, row["evaluation"]["selected_hit"])
        else: row["candidate_ceiling"] = deepcopy(old["candidate_ceiling"])
    for p, h in (guards | code_pins | artifacts).items():
        if digest(p) != h: raise ValueError("input_or_artifact_changed:"+p)
    if summarize(baseline["records"]) != baseline["table"]: raise ValueError("baseline_metric_replay_mismatch")
    result = {"version": VERSION, "complete": True, "baseline_table": baseline["table"], "table": summarize(records),
        "status_counts": dict(Counter(r["status"] for r in records)),
        "recovery_attempts": sum(r["recovery_attempted"] for r in records),
        "recovered_selections": sum(r["recovery_attempted"] and r["selected_prediction"] is not None for r in records),
        "unchanged_selected_controls": sum(r.get("control_prediction_byte_value_preserved", False) for r in records),
        "by_collection": {c: summarize([r for r in records if r["collection_id"] == c]) for c in sorted({r["collection_id"] for r in records})},
        "records": records, "input_hashes": guards, "code_hashes": code_pins, "artifact_hashes": artifacts,
        "all_new_predictions_sealed_before_reference_report_read": True, "source_labels_used_at_inference": False,
        "training_performed": False, "weights_changed": False, "independent_test_accuracy_measured": False,
        "full_roman_accuracy_measured": False, "production_modified": False,
        "original_core_annotations_rights_splits_modified": False, "elapsed_seconds": perf_counter()-started}
    write(output/"report.json", result)
    return {k: v for k, v in result.items() if k not in ("records", "input_hashes", "code_hashes", "artifact_hashes", "by_collection")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True); p.add_argument("--output", required=True)
    args = p.parse_args(); result = run(args.source, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if result["status_counts"].get("execution_error"): raise SystemExit(1)
