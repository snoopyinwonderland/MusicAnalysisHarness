"""Post-seal replay of source-clock receipts, cases and common evaluation."""
import argparse
from pathlib import Path
import json

from musicanote_harness.harmony_bounded_recovery_trial import load
from musicanote_harness.harmony_source_clock import SourceClockGuard
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_expanded_benchmark import digest, write
from musicanote_harness.harmony_candidate_recall import fraction as f, rational as q
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
    if freeze["labels_read"] or freeze["contexts"] != report["contexts"]:
        raise ValueError("invalid_prediction_freeze")
    for p, sha in (freeze["prediction_hashes"] | freeze["source_audit_and_case_hashes"]).items():
        if digest(p) != sha: raise ValueError("sealed_artifact_changed")
    source_audits = load(root/"source-clock-audit.json.gz")["packages"]
    guards = {}
    for packet in source_audits:
        ir = load(packet["observation_ir_path"]); guard = SourceClockGuard(ir)
        fresh = guard.report()
        if any(_hash(packet[k]) != _hash(v) for k, v in fresh.items()):
            raise ValueError("source_clock_replay_changed")
        guards[packet["pair_id"]] = guard
    baseline_root = Path(load(root/"run-contract.json")["baseline_source"])
    prior_freeze = load(baseline_root/"prediction-freeze.json")
    previous = {(r["pair_id"], r["sample_id"]): r for r in map(load, prior_freeze["prediction_hashes"])}
    metrics = []; sealed_keys = set()
    sealed = {(r["pair_id"], r["sample_id"]): r for r in map(load, freeze["prediction_hashes"])}
    for row in report["records"]:
        key = row["pair_id"], row["sample_id"]; old = previous.pop(key); packet = sealed.pop(key)
        if "reference_cells" in packet or "evaluation" in packet: raise ValueError("reference_in_sealed_prediction")
        if key in sealed_keys or row["sample_span"] != old["sample_span"]: raise ValueError("scope_changed")
        sealed_keys.add(key)
        for field, value in packet.items():
            if field != "prediction_artifact" and _hash(row[field]) != _hash(value):
                raise ValueError("sealed_prediction_or_gate_changed")
        fresh_gate = guards[row["pair_id"]].scope(row["sample_span"])
        if _hash(fresh_gate) != _hash(row["source_clock_gate"]): raise ValueError("gate_replay_changed")
        if fresh_gate["accepted"]:
            if _hash(row["selected_prediction"]) != _hash(old["selected_prediction"]):
                raise ValueError("clean_prediction_changed")
        elif row["selected_prediction"] is not None or row["transitions"] or row["lattice_edge_count"]:
            raise ValueError("invalid_source_was_decoded")
        evaluation = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
                              row["sample_span"], selected=row["selected_prediction"] is not None)
        if evaluation != row["evaluation"]: raise ValueError("metric_replay_changed")
        metrics.append(dict(row, evaluation=evaluation))
    if previous or sealed or len(metrics) != freeze["contexts"] or summarize(metrics) != report["table"]:
        raise ValueError("denominator_or_table_changed")
    cases = []
    for saved in report["cases"]:
        case = load(saved["case_path"]); ir = load(case["canonical_ir_path"])
        if digest(case["source_musicxml_path"]) != case["full_source_musicxml_sha256"]:
            raise ValueError("source_copy_changed")
        if _hash(ir) != case["full_ir_content_sha256"]: raise ValueError("full_ir_copy_changed")
        guard = SourceClockGuard(ir); result, graph = guard.infer({"span": case["context_span"]})
        if _hash(result) != _hash(case["guarded_result"]) or graph is not None:
            raise ValueError("blocked_diagnostic_changed")
        # Independent rational clock computation, not the trial's gap/exposure helper.
        sound = next(s for s in ir["sounding_events"] if s["sounding_event_id"] == case["audit"]["sounding_event_id"])
        notes = sorted((n for n in ir["note_events"] if n["note_id"] in sound["source_note_ids"]),
                       key=lambda n: f(n["global_onset_quarter"]))
        holes = []
        for left, right in zip(notes, notes[1:]):
            a = f(left["global_onset_quarter"])+f(left["notated_duration_quarter"])
            b = f(right["global_onset_quarter"])
            if a < b:
                holes.append({"span": {"start": q(a), "end": q(b)},
                    "old_false_sounding_exposure_quarters": q(max(0, min(f(sound["span"]["end"]), b)-max(f(sound["span"]["start"]), a)))})
        if holes != case["source_clock_gaps"]: raise ValueError("independent_gap_clock_changed")
        cases.append({"pair_id": saved["pair_id"], "case_path": saved["case_path"],
                      "blocked_before_candidate_generation": True, "independent_clock_gaps": holes})
    check()
    summary = {"complete": True, "report_sha256": digest(root/"report.json"),
        "verified_unique_sha256_files": len(hashes), "full_source_clock_audits_replayed": len(source_audits),
        "frozen_scope_gate_and_metric_replays": len(metrics), "cases": cases,
        "same_table_as_baseline": report["table"] == report["baseline_table"],
        "independent_accuracy_gain": False, "production_modified": False, "core_repaired": False}
    write(destination, summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", required=True)
    args = parser.parse_args(); print(json.dumps(run(args.root), ensure_ascii=False, indent=2))
