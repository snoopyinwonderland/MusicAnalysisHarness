"""Paired computation-only replay of J3d; seal before reference comparison."""
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json

from .harmony_bounded_recovery_trial import load
from .harmony_window_workspace import infer, VERSION
from .harmony_common_benchmark import summarize
from .harmony_expanded_benchmark import digest, write, write_packet
from .harmony_candidate_recall import fraction
from .harmony_progression_search import _hash

BASELINE_REPORT_SHA = "d1f6b57e7297954c83e932b02e4418f1231874b67a4338c2404985f9c927f0f0"
UNCHANGED = ("status", "selected_prediction", "transitions", "search_diagnostics",
             "exact_optimum_under_declared_graph", "grace_projection", "tile_plan",
             "link_withholding", "lattice_edge_count", "functional_candidate_receipts",
             "candidate_origin_groups", "source_labels_used_at_inference",
             "production_modified", "formal_core_modified")


def tie_audit(ir):
    """Full-source clock audit, not a reconstruction from DCML `tied` rows."""
    notes = {n["note_id"]: n for n in ir["note_events"]}
    results = []
    for sound in ir["sounding_events"]:
        if len(sound["source_note_ids"]) < 2:
            continue
        reasons = []
        chain = [notes.get(n) for n in sound["source_note_ids"]]
        if not all(chain):
            reasons.append("missing_source_note")
        else:
            ordered = sorted(chain, key=lambda n: (fraction(n["global_onset_quarter"]), n["note_id"]))
            cursor = fraction(sound["span"]["start"])
            for n in ordered:
                onset, duration = fraction(n["global_onset_quarter"]), fraction(n["notated_duration_quarter"])
                if onset != cursor or duration <= 0: reasons.append("noncontiguous_clock")
                if n.get("concert_pitch") != sound["pitch"]: reasons.append("different_concert_pitch")
                cursor = onset + duration
            if cursor != fraction(sound["span"]["end"]): reasons.append("release_mismatch")
            if sound.get("attack_note_id") != ordered[0]["note_id"]: reasons.append("attack_mismatch")
            if fraction(sound["sounding_duration"]) != cursor-fraction(sound["span"]["start"]):
                reasons.append("duration_mismatch")
        results.append({"sounding_event_id": sound["sounding_event_id"],
                        "source_note_ids": sound["source_note_ids"], "span": sound["span"],
                        "passed": not reasons, "reasons": sorted(set(reasons))})
    return {"multi_note_sounds": len(results), "passed": sum(r["passed"] for r in results),
            "failed": sum(not r["passed"] for r in results), "records": results,
            "source_ir_sha256": _hash(ir), "original_clock_not_shortened": True}


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    started = perf_counter(); guards = {}; artifacts = {}
    def read(p, expected=None):
        p = Path(p); sha = digest(p)
        if expected is not None and sha != expected: raise ValueError("pinned_input_changed:"+str(p))
        guards[str(p.resolve())] = sha
        return load(p)
    contract = read(source/"run-contract.json"); freeze = read(source/"prediction-freeze.json")
    if freeze["labels_read"] or contract["source_labels_used_at_inference"]:
        raise ValueError("unsealed_baseline")
    code = {str(p.resolve()): digest(p) for p in Path(__file__).parent.glob("*.py")}
    if any(code.get(p) != h for p, h in contract["code_pins"].items()): raise ValueError("baseline_engine_changed")
    plan = read(Path(contract["frozen_plan_source"])/"frozen-plan.json")
    packets = [read(p, h) for p, h in sorted(freeze["prediction_hashes"].items())]
    old = {(r["pair_id"], r["sample_id"]): r for r in packets}
    if len(old) != freeze["contexts"]: raise ValueError("baseline_context_count")
    output.mkdir(parents=True); (output/"predictions").mkdir()
    def save(p, value, compressed=False):
        (write_packet if compressed else write)(p, value)
        artifacts[str(p.resolve())] = digest(p)
        return str(p.resolve())
    save(output/"run-contract.json", {"version": VERSION, "baseline_source": str(source.resolve()),
         "baseline_report_expected_sha256": BASELINE_REPORT_SHA, "code_pins": code,
         "replay_condition": "previous_frontier_attempted_without_reference_access",
         "same_frozen_windows": True, "new_predictions_sealed_before_reference_report_read": True,
         "candidate_inventory_scores_and_search_budget_unchanged": True,
         "cache_entries": 8, "source_labels_used_at_inference": False, "training_performed": False,
         "production_modified": False})
    rows = []; ties = []
    for item in plan["packages"]:
        pair = item["entry"]["pair_id"]; ir = read(item["observation_ir_path"])
        if _hash(ir) != item["observation_ir_content_sha256"]: raise ValueError("observation_ir_changed")
        ties.append({"pair_id": pair, **tie_audit(ir)})
        for planned in item["plan"]["selected_samples"]:
            sample = planned["sample"]; key = pair, sample["sample_id"]; baseline = old.pop(key)
            if baseline["sample_span"] != sample["span"] or baseline["plan_index"] != planned["plan_index"]:
                raise ValueError("paired_scope_changed")
            if "reference_cells" in baseline or "evaluation" in baseline: raise ValueError("reference_contamination")
            row = deepcopy(baseline); row.pop("prediction_artifact", None)
            row["workspace_attempted"] = bool(baseline["frontier_attempted"])
            row["workspace_baseline_elapsed_seconds"] = baseline["elapsed_seconds"]
            tick = perf_counter()
            if row["workspace_attempted"]:
                result, _ = infer(ir, sample)
                for field in UNCHANGED:
                    # Sealed JSON represents native tuples as arrays. Compare
                    # canonical JSON values, not tuple/list Python identity.
                    if _hash(result[field]) != _hash(baseline[field]):
                        raise ValueError("computation_replay_changed:"+field)
                row.update(result)
            row["workspace_elapsed_seconds"] = perf_counter()-tick
            row["unchanged_prediction_and_candidate_origins"] = True
            row["prediction_artifact"] = save(output/"predictions"/(_hash(key)[:20]+".json.gz"), row, True)
            rows.append(row)
            print(f"[workspace {len(rows)}] {pair} {sample['sample_id']}: {row['status']}", flush=True)
    if old or len(rows) != freeze["contexts"]: raise ValueError("denominator_changed")
    save(output/"prediction-freeze.json", {"version": VERSION, "labels_read": False, "contexts": len(rows),
         "prediction_hashes": {r["prediction_artifact"]: artifacts[r["prediction_artifact"]] for r in rows}})
    # Evaluation never influences caching, candidates, decoding or replay selection.
    baseline = read(source/"report.json", BASELINE_REPORT_SHA)
    for p, h in (baseline["input_hashes"] | baseline["code_hashes"] | baseline["artifact_hashes"]).items():
        if digest(p) != h: raise ValueError("baseline_artifact_changed:"+p)
        if p in guards and guards[p] != h: raise ValueError("guard_collision")
        guards[p] = h
    refs = {(r["pair_id"], r["sample_id"]): r for r in baseline["records"]}
    if set(refs) != {(r["pair_id"], r["sample_id"]) for r in rows}: raise ValueError("reference_scope_changed")
    for row in rows:
        ref = refs[row["pair_id"], row["sample_id"]]
        if _hash(row["selected_prediction"]) != _hash(ref["selected_prediction"]): raise ValueError("prediction_changed")
        for key in ("reference_cells", "evaluation", "candidate_ceiling"):
            row[key] = deepcopy(ref[key])
    if summarize(rows) != baseline["table"]: raise ValueError("accuracy_changed")
    save(output/"source-tie-audit.json", {"packages": ties,
         "multi_note_sounds": sum(t["multi_note_sounds"] for t in ties),
         "passed": sum(t["passed"] for t in ties), "failed": sum(t["failed"] for t in ties),
         "source_note_to_sound_mapping_used": "MusicXML Canonical IR, not DCML tied-column skyline"})
    for p, h in (guards | code | artifacts).items():
        if digest(p) != h: raise ValueError("guard_changed:"+p)
    tried = [r for r in rows if r["workspace_attempted"]]
    seconds = sum(r["workspace_elapsed_seconds"] for r in tried)
    previous = sum(r["workspace_baseline_elapsed_seconds"] for r in tried)
    report = {"version": VERSION, "complete": True, "contexts": len(rows), "replayed": len(tried),
        "unchanged_predictions": len(rows), "baseline_table": baseline["table"], "table": summarize(rows),
        "status_counts": dict(Counter(r["status"] for r in rows)), "attempted_elapsed_seconds": seconds,
        "baseline_attempted_elapsed_seconds": previous,
        "elapsed_reduction_fraction": 1-seconds/previous if previous else None,
        "timing_limit": "single paired sequential replay, no repeated controlled timing experiment",
        "records": rows, "input_hashes": guards, "code_hashes": code, "artifact_hashes": artifacts,
        "tie_audit_packages": len(ties), "tie_clock_failures": sum(t["failed"] for t in ties),
        "all_new_predictions_sealed_before_reference_report_read": True,
        "source_labels_used_at_inference": False, "weights_changed": False, "training_performed": False,
        "independent_accuracy_gain": False, "production_modified": False,
        "elapsed_seconds": perf_counter()-started}
    write(output/"report.json", report)
    return {k: v for k, v in report.items() if k not in ("records", "input_hashes", "code_hashes", "artifact_hashes")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True); p.add_argument("--output", required=True)
    args = p.parse_args()
    print(json.dumps(run(args.source, args.output), ensure_ascii=False, indent=2), flush=True)
