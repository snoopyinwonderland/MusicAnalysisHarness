"""Timeboxed J3a: replay common metrics and audit metadata, not a blind trial."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_common_benchmark import (
    CONTRACT, VERSION as METRIC_VERSION, evaluate, identity_overlap, native_prediction,
    native_reference, readiness, summarize,
)
from .harmony_dataset_manifest import _package_identity
from .harmony_review_cohort import validate_split

VERSION = "harmony-benchmark-preparation-0.1.0"
BASELINE = "functional_supply_and_resolution"
LEARNED = "functional_run_learned"


def run(manifest_path, recall_path, baseline_path, learned_path, ledger_path, batch_path,
        output, *, expected_hashes, families_per_collection=2):
    started = perf_counter(); output = Path(output)
    if output.exists(): raise ValueError("output_exists_no_overwrite")
    if type(families_per_collection) is not int or families_per_collection < 1:
        raise ValueError("invalid_family_cap")
    inputs = {}
    def read(path, sha=None):
        p = Path(path); data = p.read_bytes(); actual = hashlib.sha256(data).hexdigest()
        if sha is not None and actual != sha: raise ValueError("input_sha_mismatch:"+str(p))
        key = str(p.resolve())
        if key in inputs and inputs[key] != actual: raise ValueError("input_changed_during_read")
        inputs[key] = actual
        return json.loads(data.decode("utf-8"))
    args = (manifest_path, recall_path, baseline_path, learned_path, ledger_path, batch_path)
    if len(expected_hashes) != len(args): raise ValueError("all_input_pins_required")
    manifest, recall, baseline, learned, ledger, batch = [read(p, h) for p, h in zip(args, expected_hashes)]
    validate_split(manifest["entries"])
    validate_split(recall["package_manifest"])
    if ledger.get("history_complete") is not False:
        raise ValueError("full_exposure_audit_not_implemented")
    for h in ledger["records"]:
        if type(h["musical_result_exposed"]) is not bool or not h["evidence_paths"]:
            raise ValueError("invalid_exposure_history")
        for evidence in h["evidence_paths"]:
            p = Path(evidence); data = p.read_bytes()
            inputs[str(p.resolve())] = hashlib.sha256(data).hexdigest()
    for parent in (recall, baseline, learned):
        if parent.get("complete") is not True: raise ValueError("incomplete_parent")
    if learned.get("source_labels_used_at_inference") is not False:
        raise ValueError("nonblind_parent_inference")
    if len({len(p["records"]) for p in (recall, baseline, learned)}) != 1:
        raise ValueError("cohort_count_changed")
    if families_per_collection != 2:
        raise ValueError("predeclared_metadata_schedule_cap_is_two")
    rows = []; candidate = defaultdict(Counter); seen = set()
    for gold, old, new in zip(recall["records"], baseline["records"], learned["records"]):
        identity = (gold["pair_id"], gold["plan_index"], gold["sample_id"])
        if identity in seen: raise ValueError("duplicate_context_identity")
        seen.add(identity)
        for key in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span", "reference_cells"):
            if not gold[key] == old[key] == new[key]: raise ValueError("cohort_identity_changed:"+key)
        reference = native_reference(gold)
        for arm, pred in ((BASELINE, old["selected_predictions"][BASELINE]), (LEARNED, new["selected_prediction"])):
            value = evaluate(reference, native_prediction(pred, gold["sample_span"]),
                             gold["sample_span"], selected=pred is not None)
            row = {"sample_id": gold["sample_id"], "pair_id": gold["pair_id"], "plan_index": gold["plan_index"],
                   "work_family_id": gold["work_family_id"], "split": gold["split"],
                   "sample_span": gold["sample_span"], "arm": arm, "evaluation": value,
                   "prediction_report": str(Path(baseline_path if arm == BASELINE else learned_path).resolve()),
                   "source_context_artifact": new["source_context_artifact"],
                   "source_context_sha256": new["source_context_sha256"]}
            rows.append(row)
            if value["fully_evaluable"]:
                hit = new["expanded_lattice_hit"]
                if hit is not None and type(hit) is not bool:
                    raise ValueError("invalid_candidate_ceiling_status")
                if value["selected_hit"] and hit is not True: raise ValueError("selected_match_outside_ceiling")
                status = "selected_correct" if value["selected_hit"] else (
                    "candidate_present_selection_error" if hit else (
                        "candidate_ceiling_missing" if hit is False else "candidate_ceiling_unavailable"))
                candidate[arm][status] += 1
            else: candidate[arm]["partial_reference"] += 1
    tables = {arm: summarize([r for r in rows if r["arm"] == arm]) for arm in (BASELINE, LEARNED)}
    for arm, parent in ((BASELINE, baseline), (LEARNED, learned)):
        table, previous = tables[arm], parent["summary"][arm]
        for key in ("contexts", "selected_contexts", "abstained_contexts", "fully_evaluable_contexts",
                    "selected_correct_contexts", "selected_context_agreement", "semantic_boundary_exact"):
            if table[key] != previous[key]: raise ValueError("common_metric_replay_mismatch:"+key)
        for field, key in (("root", "selected_root_time_agreement"),
                           ("root_members", "selected_root_members_time_agreement")):
            if table["components"][field]["time_agreement"] != previous[key]:
                raise ValueError("common_time_replay_mismatch:"+field)
        if table["components"]["root_members"]["eligible_time"] != previous["eligible_time"]:
            raise ValueError("common_time_denominator_changed")
        if table["components"]["root_members"]["work_family_macro"] != previous["work_family_macro_root_members_agreement"]:
            raise ValueError("family_macro_replay_mismatch")

    exposed = recall["package_manifest"]
    holdout = readiness(manifest["entries"], exposed, ledger["records"])
    # Read preparation metadata only, not IRs, XMLs or annotation JSONL/TSVs.
    # The cap is predeclared and the schedule does not confer blind eligibility.
    inventory = []; source_root = Path(batch_path).parent / "pairs"
    for item in batch["outcomes"]:
        prep_path = Path(item["report_path"])
        prep = read(prep_path)
        e = _package_identity(prep_path.parent, source_root, prep)
        overlap = identity_overlap(e, exposed)
        historical = any(h["work_family_id"] == e["work_family_id"] and h["musical_result_exposed"]
                         for h in ledger["records"])
        # Direct completeness from the metadata, not the misleading exact-only
        # ratio: verified staff transforms are valid alignment categories too.
        mapped = prep.get("source_note_mapping", {}).get("complete") is True
        aligned = (prep["imported_annotations"] > 0 and prep["ambiguous_alignments"] == 0
                   and prep["exact_alignments"] + prep["verified_transform_alignments"] == prep["imported_annotations"]
                   and not prep.get("measure_alignment_blocking_issues"))
        status = "known_exposure_excluded" if overlap or historical else (
            "work_family_unresolved" if e["work_family_confidence"] == "unresolved_work_family" else (
                "alignment_or_source_incomplete" if not mapped or not aligned else "metadata_candidate_exposure_unknown"))
        inventory.append({**e, "pair_id": item["pair_id"], "preparation_report": str(prep_path.resolve()),
                          "preparation_report_sha256": inputs[str(prep_path.resolve())],
                          "known_overlap_fields": overlap, "historical_exposure": historical,
                          "source_note_mapping_complete": mapped, "alignment_metadata_complete": aligned,
                          "status": status, "blind_evaluation_approved": False,
                          "training_approved": False, "original_split_changed": False})
    pools = defaultdict(lambda: defaultdict(list))
    for e in inventory:
        if e["status"] == "metadata_candidate_exposure_unknown":
            pools[e["collection_id"]][e["work_family_id"]].append(e)
    schedule = []
    for collection, groups in sorted(pools.items()):
        # Canonical identity ordering, no harmony outcomes, labels or durations.
        chosen = sorted(groups, key=lambda f: min(e["work_family_source_key"] for e in groups[f]))[:2]
        for family in chosen:
            schedule.append({"collection_id": collection, "work_family_id": family,
                "work_family_source_key": groups[family][0]["work_family_source_key"],
                "metadata_complete_packages": sorted(groups[family], key=lambda e: e["pair_id"]),
                "status": "staged_candidate_not_blind_test", "all_movements_same_family": True,
                "remaining_gates": ["full_historical_exposure_audit_across_corpora_and_viewer",
                    "source_annotation_sanitization", "IR_and_alignment_revision_binding",
                    "explicit_frozen_execution_policy", "checkpoint_training_overlap_audit"]})
    # Physical guards from the previous fully run experiment remain unchanged.
    for mapping in (learned["input_hashes"], learned["code_hashes"]):
        for path, sha in mapping.items():
            key = str(Path(path).resolve())
            if key in inputs and inputs[key] != sha: raise ValueError("parent_pin_conflict")
            inputs[key] = sha
    code_names = ("harmony_common_benchmark.py", Path(__file__).name, "harmony_dataset_manifest.py",
                  "harmony_review_cohort.py", "harmony_candidate_recall.py")
    codes = {str(Path(__file__).with_name(n).resolve()): hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest()
             for n in code_names}
    for path, sha in {**inputs, **codes}.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha: raise ValueError("frozen_input_changed:"+path)
    result = {"version": VERSION, "metric_version": METRIC_VERSION, "complete": True,
        "stage": "J3a_common_metric_replay_and_metadata_readiness_not_independent_accuracy",
        "contract": CONTRACT, "tables": tables, "candidate_diagnostics": {a: dict(v) for a, v in candidate.items()},
        "by_split": {s: {a: summarize([r for r in rows if r["split"] == s and r["arm"] == a])
                           for a in tables} for s in sorted({r["split"] for r in rows})},
        "original_holdout_audit": holdout,
        "inventory_summary": {"packages": len(inventory), "families": len({e["work_family_id"] for e in inventory}),
            "statuses": dict(Counter(e["status"] for e in inventory)),
            "staged_families": len(schedule), "staged_packages": sum(len(e["metadata_complete_packages"]) for e in schedule),
            "collections": len(pools), "historical_exposure_audit_complete": False},
        "public_model_readiness": {
            "ChordGNN": {"status": "not_executed_checkpoint_and_isolated_environment_pending",
                "training_overlap": "unknown_for_checkpoint", "revision_pin": None,
                "official_repo": "https://github.com/manoskary/ChordGNN",
                "clock_mapping": "partitura_onset_beat_is_not_assumed_global_quarter"},
            "AnalysisGNN": {"status": "not_executed_native_output_and_onset_aggregation_validation_pending",
                "training_overlap": "unknown_for_checkpoint", "revision_pin": None,
                "official_repo": "https://github.com/manoskary/analysisgnn"}},
        "source_hashes": inputs, "code_hashes": codes, "parent_guards_preserved": True,
        "label_free_metadata_schedule": True, "reserved_score_or_annotation_contents_read": False,
        "model_inference_executed": False, "training_performed": False,
        "independent_test_accuracy_measured": False, "paper_reproduction_executed": False,
        "production_modified": False, "original_rights_or_splits_modified": False,
        "elapsed_seconds": perf_counter()-started}
    output.mkdir(parents=True)
    (output/"report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output/"common-evaluation.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows), encoding="utf-8")
    (output/"independent-evaluation-plan.json").write_text(json.dumps({"version": VERSION,
        "families_per_collection": 2, "schedule": schedule, "inventory": inventory,
        "blind_approval_granted": False, "new_test_predictions": 0}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {k: v for k, v in result.items() if k not in ("source_hashes", "code_hashes", "original_holdout_audit")}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "recall", "baseline", "learned", "ledger", "batch"):
        p.add_argument("--"+name, required=True); p.add_argument("--"+name+"-sha", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    names = ("manifest", "recall", "baseline", "learned", "ledger", "batch")
    result = run(*(getattr(a, n) for n in names), a.output,
                 expected_hashes=[getattr(a, n+"_sha") for n in names])
    print(json.dumps({"complete": result["complete"], "stage": result["stage"],
                      "inventory_summary": result["inventory_summary"], "elapsed_seconds": result["elapsed_seconds"]},
                     ensure_ascii=False, indent=2))
