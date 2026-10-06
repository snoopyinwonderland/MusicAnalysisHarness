"""Source-clock eligibility replay; musical predictions are NOT retrained.

Reuse sealed predictions only after their complete-source clock gate passes.
Withhold affected windows before any candidate generation. Extra diagnostics
are selected from bad source clocks, never from harmony annotation labels.
"""
import argparse
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json

from . import harmony_bounded_recovery as bounded
from .harmony_bounded_recovery_trial import load
from .harmony_source_clock import SourceClockGuard, VERSION
from .harmony_window_workspace import infer as original_infer
from .harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from .harmony_expanded_benchmark import digest, write, write_packet
from .harmony_candidate_recall import fraction as f, rational as q
from .harmony_progression_search import _hash

BASELINE_REPORT_SHA = "1e0e9257214015536b00e9282b12def7157cb47b26a4d853ca2646d3e59ce6ac"


def request(span):
    return {"sample_id": "source-clock-diagnostic", "span": span, "lane": [],
            "seed_event_refs": [], "abstention_reasons": []}


def diagnose(ir, guard):
    """Prove quarantine and unchanged delegation using only source clocks.

    Old exposure is inspected solely as a diagnostic, not as a new prediction.
    A neighboring one-quarter control proves adapter equivalence, NOT musical
    correctness or satisfaction of other parser/repeat eligibility gates.
    """
    cases = []
    for failed in guard.report()["records"]:
        if failed["passed"] or failed["risk_span"] is None:
            continue
        a, b = f(failed["risk_span"]["start"]), f(failed["risk_span"]["end"])
        score_end = f(ir["score"]["duration_quarters"])
        context = {"start": q(max(0, a-3)), "end": q(min(score_end, b+3))}
        blocked, graph = guard.infer(request(context))
        if graph is not None or blocked["selected_prediction"] is not None or blocked["transitions"]:
            raise ValueError("invalid_clock_reached_decoder")
        gaps = []
        for left, right in zip(failed["source_notes"], failed["source_notes"][1:]):
            x, y = f(left["release"]), f(right["onset"])
            if x >= y: continue
            view, grace = bounded.grace_projection(ir)
            ev, _, _ = bounded.bound_evidence(view, {"start": q(x), "end": q(y)}, grace)
            exposure = sum(max(0, min(e.end, y)-max(e.start, x)) for e in ev.events
                           if e.event_id == failed["sounding_event_id"])
            gaps.append({"span": {"start": q(x), "end": q(y)},
                         "old_false_sounding_exposure_quarters": q(exposure)})
        control = None
        if b < score_end:
            target = {"start": q(b), "end": q(min(score_end, b+1))}
            if guard.scope(target)["accepted"]:
                expected, old_graph = original_infer(ir, request(target))
                actual, new_graph = guard.infer(request(target))
                actual.pop("source_clock_gate")
                if _hash(actual) != _hash(expected) or new_graph != old_graph:
                    raise ValueError("clean_clock_delegation_changed")
                control = {"span": target, "old_and_guarded_result_sha256": _hash(expected),
                           "same_entire_candidate_graph": True, "status": expected["status"],
                           "candidate_edges": expected["lattice_edge_count"],
                           "music_accuracy_evaluated": False, "other_eligibility_gates_certified": False}
        cases.append({"audit": failed, "context_span": context, "guarded_result": blocked,
                      "source_clock_gaps": gaps, "clean_neighbor_control": control,
                      "source_labels_used": False, "core_repaired": False})
    return cases


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
    for p in (Path("tests/test_harmony_source_clock.py"), Path("tests/test_harmony_source_clock_trial.py"),
              Path("scripts/audit_harmony_source_clock.py")):
        if p.exists(): code[str(p.resolve())] = digest(p)
    if any(code.get(p) != h for p, h in contract["code_pins"].items()):
        raise ValueError("baseline_engine_changed")
    prior = read(Path(contract["baseline_source"])/"run-contract.json")
    plan = read(Path(prior["frozen_plan_source"])/"frozen-plan.json")
    packets = [read(p, h) for p, h in sorted(freeze["prediction_hashes"].items())]
    old = {(r["pair_id"], r["sample_id"]): r for r in packets}
    if len(old) != freeze["contexts"]: raise ValueError("baseline_context_count")
    if any("reference_cells" in r or "evaluation" in r for r in packets):
        raise ValueError("reference_contamination")
    output.mkdir(parents=True); (output/"predictions").mkdir(); (output/"cases").mkdir()
    def save(p, value, compressed=False):
        (write_packet if compressed else write)(p, value)
        artifacts[str(p.resolve())] = digest(p)
        return str(p.resolve())
    save(output/"run-contract.json", {"version": VERSION, "baseline_source": str(source.resolve()),
        "frozen_plan_source": prior["frozen_plan_source"], "baseline_report_expected_sha256": BASELINE_REPORT_SHA,
        "code_pins": code, "same_frozen_windows": True, "accepted_predictions_reused_not_reinferred": True,
        "clock_diagnostics_before_reference_report_read": True, "source_labels_used_at_inference": False,
        "training_performed": False, "production_modified": False, "core_repaired": False})
    rows = []; audits = []; cases = []
    for item in plan["packages"]:
        pair = item["entry"]["pair_id"]; ir = read(item["observation_ir_path"])
        if _hash(ir) != item["observation_ir_content_sha256"]: raise ValueError("observation_ir_changed")
        clock = SourceClockGuard(ir)
        audits.append({"pair_id": pair, "observation_ir_path": item["observation_ir_path"], **clock.report()})
        for planned in item["plan"]["selected_samples"]:
            sample = planned["sample"]; key = pair, sample["sample_id"]; baseline = old.pop(key)
            if baseline["sample_span"] != sample["span"] or baseline["plan_index"] != planned["plan_index"]:
                raise ValueError("paired_scope_changed")
            row = deepcopy(baseline); row.pop("prediction_artifact", None)
            gate = clock.scope(sample["span"])
            row.update(source_clock_gate=gate, accepted_prediction_reused=gate["accepted"])
            if not gate["accepted"]:
                result, _ = clock.infer(sample); row.update(result)
                # Historical graph/ceiling is not a new graph produced behind this gate.
                for field in ("functional_candidate_receipts", "candidate_origin_groups", "tile_plan",
                              "search_diagnostics", "window_reuse"):
                    row.pop(field, None)
            row["prediction_artifact"] = save(output/"predictions"/(_hash(key)[:20]+".json.gz"), row, True)
            rows.append(row)
        for case in diagnose(ir, clock):
            case["pair_id"] = pair; case["full_ir_content_sha256"] = _hash(ir)
            folder = output/"cases"/_hash([pair, case["audit"]["sounding_event_id"]])[:20]
            folder.mkdir(); save(folder/"canonical-ir.json.gz", ir, True)
            path = Path(item["preparation"]["source_paths"]["score"])
            sha = digest(path)
            if sha != item["preparation"]["source_sha256"]["score"]:
                raise ValueError("case_source_changed")
            guards[str(path.resolve())] = sha
            copy = folder/"source.musicxml"; copy.write_bytes(path.read_bytes())
            artifacts[str(copy.resolve())] = digest(copy)
            if digest(copy) != sha: raise ValueError("case_copy_changed")
            notes = [n for n in ir["note_events"] if n["note_id"] in case["audit"]["source_note_ids"]]
            case.update(notes=notes, source_references=[r for r in ir.get("source_references", [])
                if r["source_ref_id"] in {n.get("source_ref_id") for n in notes}],
                full_source_musicxml_sha256=sha, source_musicxml_path=str(copy.resolve()),
                canonical_ir_path=str((folder/"canonical-ir.json.gz").resolve()))
            case_path = save(folder/"case.json", case)
            cases.append({"pair_id": pair, "case_path": case_path})
        clock.check_source()
        print(f"[clock {len(audits)}] {pair}: {audits[-1]['sounds']} sounds, {audits[-1]['failed']} invalid", flush=True)
    if old or len(rows) != freeze["contexts"]: raise ValueError("denominator_changed")
    save(output/"source-clock-audit.json.gz", {"version": VERSION, "packages": audits}, True)
    save(output/"prediction-freeze.json", {"version": VERSION, "labels_read": False, "contexts": len(rows),
         "prediction_hashes": {r["prediction_artifact"]: artifacts[r["prediction_artifact"]] for r in rows},
         "source_audit_and_case_hashes": {p: h for p, h in artifacts.items() if "/predictions/" not in p.replace("\\", "/")}})
    # First annotation-bearing read. It cannot change the sealed gate or prediction.
    baseline = read(source/"report.json", BASELINE_REPORT_SHA)
    for p, h in (baseline["input_hashes"] | baseline["code_hashes"] | baseline["artifact_hashes"]).items():
        if digest(p) != h: raise ValueError("baseline_artifact_changed:"+p)
        if p in guards and guards[p] != h: raise ValueError("guard_collision")
        guards[p] = h
    refs = {(r["pair_id"], r["sample_id"]): r for r in baseline["records"]}
    if set(refs) != {(r["pair_id"], r["sample_id"]) for r in rows}: raise ValueError("reference_scope_changed")
    unchanged = 0
    for row in rows:
        ref = refs[row["pair_id"], row["sample_id"]]
        if row["accepted_prediction_reused"]:
            if _hash(row["selected_prediction"]) != _hash(ref["selected_prediction"]):
                raise ValueError("accepted_prediction_changed")
            unchanged += 1
        row["reference_cells"] = deepcopy(ref["reference_cells"])
        row["historical_candidate_ceiling"] = deepcopy(ref["candidate_ceiling"])
        row["candidate_ceiling"] = deepcopy(ref["candidate_ceiling"]) if row["accepted_prediction_reused"] else None
        row["evaluation"] = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
                                     row["sample_span"], selected=row["selected_prediction"] is not None)
    for p, h in (guards | code | artifacts).items():
        if digest(p) != h: raise ValueError("guard_changed:"+p)
    report = {"version": VERSION, "complete": True, "contexts": len(rows), "source_packages": len(audits),
        "sounds_audited": sum(a["sounds"] for a in audits), "invalid_sounds": sum(a["failed"] for a in audits),
        "multi_note_sounds": sum(a["multi_note_sounds"] for a in audits),
        "zero_time_graces": sum(a["zero_time_graces"] for a in audits),
        "packages_with_global_blockers": sum(bool(a["global_blockers"]) for a in audits),
        "clock_eligible_frozen_contexts": unchanged, "new_clock_abstentions": len(rows)-unchanged,
        "status_counts": dict(Counter(r["status"] for r in rows)), "baseline_table": baseline["table"],
        "table": summarize(rows), "records": rows, "cases": cases,
        "input_hashes": guards, "code_hashes": code, "artifact_hashes": artifacts,
        "accepted_predictions_reused_not_reinferred": True, "all_predictions_sealed_before_reference_report_read": True,
        "source_labels_used_at_inference": False, "weights_changed": False, "training_performed": False,
        "independent_accuracy_gain": False, "raw_xml_independently_reparsed": False,
        "production_modified": False, "core_repaired": False, "elapsed_seconds": perf_counter()-started}
    write(output/"report.json", report)
    return {k: v for k, v in report.items() if k not in ("records", "input_hashes", "code_hashes", "artifact_hashes")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), ensure_ascii=False, indent=2), flush=True)
