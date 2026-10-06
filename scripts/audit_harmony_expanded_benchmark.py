"""Independently replay J3b metrics and save bounded, post-hoc error receipts."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

from musicanote_harness.harmony_candidate_recall import fraction
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith(".gz") else data)


def run(source, output):
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError("choose_new_audit_output")
    report = load(source/"report.json"); plan = load(source/"frozen-plan.json")
    if report["complete"] is not True or report["source_labels_used_at_inference"] is not False:
        raise ValueError("invalid_prediction_report")
    guards = report["input_hashes"]|report["code_hashes"]|report["artifact_hashes"]
    for path, sha in guards.items():
        if digest(path) != sha: raise ValueError("source_or_artifact_changed:"+path)
    records = report["records"]; by_pair = {p["entry"]["pair_id"]: p for p in plan["packages"]}
    expected = {(p["entry"]["pair_id"], s["sample"]["sample_id"], s["plan_index"])
                for p in plan["packages"] for s in p["plan"]["selected_samples"]}
    observed = {(r["pair_id"], r["sample_id"], r["plan_index"]) for r in records}
    if expected != observed or len(observed) != len(records): raise ValueError("sample_denominator_changed")
    freeze = load(source/"prediction-freeze.json")
    if freeze["contexts"] != len(records) or freeze["labels_read"] is not False:
        raise ValueError("prediction_freeze_mismatch")
    for r in records:
        saved = load(r["prediction_artifact"])
        if digest(r["prediction_artifact"]) != freeze["prediction_hashes"][r["prediction_artifact"]]:
            raise ValueError("sealed_prediction_changed")
        if any(saved[k] != r[k] for k in saved): raise ValueError("post_reference_prediction_changed")
        actual = evaluate(native_reference(r), native_prediction(r["selected_prediction"], r["sample_span"]),
                          r["sample_span"], selected=r["selected_prediction"] is not None)
        if actual != r["evaluation"]: raise ValueError("metric_replay_mismatch")
        if actual["selected_hit"] is True and r["candidate_ceiling"]["lattice_hit"] is not True:
            raise ValueError("selected_match_outside_candidate_ceiling")
    if summarize(records) != report["table"]: raise ValueError("aggregate_replay_mismatch")
    full = [r for r in records if r["evaluation"]["fully_evaluable"]]
    ceiling = Counter(str(r["candidate_ceiling"]["lattice_hit"]) for r in full)
    reasons = Counter(r["candidate_ceiling"]["outcome"] for r in full)
    selected_cases = []
    # Post-hoc examples for explaining results, NOT new test-window selection.
    def matched(r):
        c = r["evaluation"]["components"]["root_members"]
        return fraction(c["matched"])/fraction(c["eligible"])
    for category, pool in (
        ("candidate_present_selection_error", [r for r in full if r["candidate_ceiling"]["lattice_hit"] is True and not r["evaluation"]["selected_hit"]]),
        ("local_candidate_missing", [r for r in full if r["candidate_ceiling"]["outcome"] == "local_spelled_signature_absent"]),
        ("selected_correct", [r for r in full if r["evaluation"]["selected_hit"]]),
        ("resource_or_source_abstention", [r for r in records if r["selected_prediction"] is None])):
        for r in sorted(pool, key=lambda r: (matched(r) if r["evaluation"]["fully_evaluable"] else 0, r["pair_id"], r["sample_id"]))[:2]:
            p = by_pair[r["pair_id"]]
            selected_cases.append({"category": category, "record": r,
                "score_source_path": p["preparation"]["source_paths"]["score"],
                "score_source_sha256": p["entry"]["score_sha256"],
                "observation_ir_path": p["observation_ir_path"],
                "observation_ir_sha256": report["artifact_hashes"][p["observation_ir_path"]],
                "context_policy": "full score snapshot includes before/after context; display/evidence range is frozen sample span",
                "example_is_posthoc_not_training_or_new_accuracy_sample": True})
    diagnostics = {"version": "harmony-expanded-benchmark-audit-0.1.0", "complete": True,
        "report_sha256": digest(source/"report.json"), "auditor_sha256": digest(__file__),
        "all_guards_unchanged": True, "guarded_unique_files": len(guards),
        "exact_metric_replay": True, "frozen_prediction_packets": len(records),
        "attempted_families": len({p["entry"]["work_family_id"] for p in plan["packages"]}),
        "source_ready_families": len({p["entry"]["work_family_id"] for p in plan["packages"] if not p["blockers"]}),
        "supported_reference_families": report["table"]["components"]["root_members"]["supported_work_families"],
        "candidate_ceiling_statuses_full_reference": dict(ceiling), "candidate_ceiling_outcomes_full_reference": dict(reasons),
        "fully_evaluable_contexts": len(full), "retained24_hits": report["retained24"]["hits"],
        "retained24_recall": report["retained24"]["hits"]/len(full) if full else None,
        "expanded_lattice_recall": ceiling["True"]/len(full) if full else None,
        "unsupported_reference_reason_counts": report["reference_reason_counts"],
        "source_replay_event_counts": dict(sum((Counter(p["source_event_counts"]) for p in plan["packages"]), Counter())),
        "work_families": [{"family": f, "table": summarize([r for r in records if r["work_family_id"] == f])}
                          for f in sorted({r["work_family_id"] for r in records})],
        "examples": selected_cases, "examples_selected_after_evaluation": True,
        "not_independent_test_or_Roman_accuracy": True, "production_modified": False}
    # Small immutable XML snapshots make the error cases reproducible even if
    # the external source folder is later updated; they are local-only output.
    output.mkdir(parents=True, exist_ok=False); (output/"source-scores").mkdir()
    for case in selected_cases:
        path = Path(case["score_source_path"]); data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != case["score_source_sha256"]: raise ValueError("case_source_changed")
        snapshot = output/"source-scores"/(case["score_source_sha256"][:20]+".musicxml")
        if snapshot.exists() and snapshot.read_bytes() != data: raise ValueError("snapshot_collision")
        snapshot.write_bytes(data)
        case["frozen_xml_path"] = str(snapshot.resolve()); case["frozen_xml_sha256"] = digest(snapshot)
    (output/"audit.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in diagnostics.items() if k not in ("examples", "work_families")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--source", required=True); p.add_argument("--output", required=True)
    a = p.parse_args(); run(a.source, a.output)
