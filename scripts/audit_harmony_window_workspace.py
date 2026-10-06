"""Post-seal proof: replay metrics/catalogs and preserve abnormal full tie cases."""
import argparse
from copy import deepcopy
from pathlib import Path
import json

from musicanote_harness import harmony_bounded_recovery as bounded
from musicanote_harness.harmony_window_workspace import WindowWorkspace
from musicanote_harness.harmony_candidate_catalog import propose
from musicanote_harness.harmony_window_workspace_trial import UNCHANGED, tie_audit
from musicanote_harness.harmony_bounded_recovery_trial import load
from musicanote_harness.harmony_common_benchmark import evaluate, native_prediction, native_reference, summarize
from musicanote_harness.harmony_expanded_benchmark import digest, write, write_packet
from musicanote_harness.harmony_progression_search import _hash


def run(root):
    root = Path(root); output = root/"diagnostics-r1"
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    report = load(root/"report.json"); contract = load(root/"run-contract.json")
    baseline_root = Path(contract["baseline_source"])
    freeze = load(baseline_root/"prediction-freeze.json")
    baseline_packets = [load(p) for p in freeze["prediction_hashes"]]
    previous = {(r["pair_id"], r["sample_id"]): r for r in baseline_packets}
    guards = report["input_hashes"] | report["code_hashes"] | report["artifact_hashes"]
    def check():
        for p, h in guards.items():
            if digest(p) != h: raise ValueError("guard_changed:"+p)
    check(); output.mkdir()
    recomputed = []
    for row in report["records"]:
        prior = previous.pop((row["pair_id"], row["sample_id"]))
        if row["sample_span"] != prior["sample_span"]: raise ValueError("scope_changed")
        fields = UNCHANGED if row["workspace_attempted"] else ("status", "selected_prediction")
        if any(_hash(row[k]) != _hash(prior[k]) for k in fields): raise ValueError("paired_value_changed")
        fresh = evaluate(native_reference(row), native_prediction(row["selected_prediction"], row["sample_span"]),
                         row["sample_span"], selected=row["selected_prediction"] is not None)
        if fresh != row["evaluation"]: raise ValueError("evaluation_replay_mismatch")
        recomputed.append(dict(row, evaluation=fresh))
    if previous or summarize(recomputed) != report["table"]: raise ValueError("metric_denominator_changed")
    baseline_contract = load(baseline_root/"run-contract.json")
    plan = load(Path(baseline_contract["frozen_plan_source"])/"frozen-plan.json")
    by_pair = {p["entry"]["pair_id"]: p for p in plan["packages"]}
    comparisons = []; abnormal = []
    for row in report["records"]:
        if not row["workspace_attempted"]: continue
        item = by_pair[row["pair_id"]]; ir = load(item["observation_ir_path"])
        view, _ = bounded.grace_projection(ir); workspace = WindowWorkspace(view)
        points = row["tile_plan"]["points"]
        intervals = [(i, j, tile["span"]) for tile in row["tile_plan"]["tiles"]
                     for i in range(tile["start_index"], tile["end_index"])
                     for j in range(i+1, tile["end_index"]+1)]
        # Source-order quantiles only, not agreement/label-dependent selection.
        for k in sorted({i*(len(intervals)-1)//11 for i in range(12)}):
            i, j, context = intervals[k]; span = {"start": points[i], "end": points[j]}
            cached = workspace.propose(span, context); original = propose(view, span, context)
            if _hash(cached) != _hash(original): raise ValueError("complete_catalog_mismatch")
            comparisons.append({"pair_id": row["pair_id"], "span": span, "context_span": context,
                                "catalog_sha256": _hash(original), "all_provider_candidates_equal": True})
    for item in plan["packages"]:
        ir = load(item["observation_ir_path"])
        for failed in tie_audit(ir)["records"]:
            if failed["passed"]: continue
            sound = next(s for s in ir["sounding_events"] if s["sounding_event_id"] == failed["sounding_event_id"])
            notes = [n for n in ir["note_events"] if n["note_id"] in sound["source_note_ids"]]
            start = max(0, bounded.f(sound["span"]["start"])-3); end = bounded.f(sound["span"]["end"])+3
            scope = {"start": bounded.q(start), "end": bounded.q(end)}
            view, grace = bounded.grace_projection(ir); ev, functional, _ = bounded.bound_evidence(view, scope, grace)
            frow = next(r for r in functional.rows if r["id"] == sound["sounding_event_id"])
            folder = output/"abnormal-ties"/sound["sounding_event_id"]; folder.mkdir(parents=True)
            source = Path(item["preparation"]["source_paths"]["score"])
            (folder/"source.musicxml").write_bytes(source.read_bytes())
            write_packet(folder/"canonical-ir.json.gz", ir)
            references = [r for r in ir["source_references"] if r["source_ref_id"] in {n["source_ref_id"] for n in notes}]
            record = {"pair_id": item["entry"]["pair_id"], "sound": sound, "notes": notes,
                "source_references": references, "context_span": scope, "audit": failed,
                "full_source_musicxml_sha256": digest(source), "full_ir_sha256": _hash(ir),
                "functional_clock_valid": frow["clock_valid"],
                "direct_functional_links_using_failed_sound": sum(any(r["id"] == sound["sounding_event_id"] for r in link) for link in functional.links),
                "conditional_ornament_neighbor_using_failed_sound": sound["sounding_event_id"] in ev.neighbors,
                "raw_harmonic_exposure_still_uses_stored_sound_span": True,
                "core_repaired": False, "musicomp_shortened_tie_bug_reproduced": False,
                "interpretation": "Noncontiguous source chain: stored sound bridges a gap, not a skipped-tail shortening. Existing voice-clock checks withhold melodic resolution, but raw harmonic exposure remains a separate risk."}
            write(folder/"case.json", record)
            abnormal.append({"case": str((folder/"case.json").resolve()), "pair_id": record["pair_id"],
                             "source_musicxml_sha256": digest(folder/"source.musicxml"),
                             "source_ir_sha256": digest(folder/"canonical-ir.json.gz")})
    check()
    audit = {"complete": True, "report_sha256": digest(root/"report.json"),
        "verified_unique_sha256_files": len(guards), "same_frozen_scopes_and_metrics": len(recomputed),
        "same_selected_predictions": report["unchanged_predictions"], "complete_catalog_comparisons": comparisons,
        "abnormal_full_source_cases": abnormal, "production_modified": False,
        "no_external_worktree_write": True, "source_annotations_and_rights_modified": False}
    write(output/"audit.json", audit)
    return {k: v for k, v in audit.items() if k != "complete_catalog_comparisons"} | {"catalogs_compared": len(comparisons)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", required=True)
    args = parser.parse_args(); print(json.dumps(run(args.root), ensure_ascii=False, indent=2))
