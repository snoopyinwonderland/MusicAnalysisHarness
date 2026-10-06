"""Frozen J2c time-only vs time+boundary margin ablation; no deployment."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_candidate_recall import fraction
from .harmony_lattice_recall import cells_from_record
from .harmony_margin_learning import fit, infer
from .harmony_progression_search import _hash
from .harmony_scored_decoder import FEATURE_VERSION, decode, evaluation_path, prepare
from .harmony_scored_decoder_trial import evaluate_selection, summarize
from .harmony_structured_learning import TrainingExample, content_hash, validate_use_contract
from .harmony_structured_learning_trial import digest
from .source_locator_revision_trial import validate_policy

VERSION = "harmony-margin-learning-trial-0.1.0"
ARMS = {"margin_time_only": Fraction(), "margin_time_boundary": Fraction(1, 4)}


def compact_prediction(prediction):
    if prediction is None:
        return None
    return {"proposal_id": prediction["proposal_id"], "score_cost": prediction["score_cost"],
            "segments": [{k: s[k] for k in ("semantic_group_ref", "span", "root_spelling", "members")}
                         for s in prediction["segments"]]}


def run(recall_path, lattice_path, baseline_path, learned_path, contract_path, output, *,
        expected_recall_sha, expected_lattice_sha, expected_baseline_sha,
        expected_learned_sha, expected_contract_sha):
    started = perf_counter(); output = Path(output)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    inputs = {}
    def read(path, expected, compressed=False):
        path = Path(path); data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
        if sha != expected:
            raise ValueError("input_sha_mismatch:"+str(path))
        inputs[str(path.resolve())] = sha
        return json.loads((gzip.decompress(data) if compressed else data).decode("utf-8"))
    def guard(hashes):
        for path, sha in hashes.items():
            if digest(path) != sha:
                raise ValueError("frozen_input_changed:"+str(path))
            inputs[str(Path(path).resolve())] = sha
    recall = read(recall_path, expected_recall_sha)
    contract = read(contract_path, expected_contract_sha)
    manifest = recall["package_manifest"]
    approvals = validate_use_contract(contract, manifest, expected_recall_sha)
    for a in approvals.values():
        evidence = a["source_license"]
        guard({evidence["local_license_path"]: evidence["local_license_sha256"],
               evidence["readme_path"]: evidence["readme_sha256"]})
    lattice = read(lattice_path, expected_lattice_sha)
    baseline = read(baseline_path, expected_baseline_sha)
    learned = read(learned_path, expected_learned_sha)
    if (any(p.get("complete") is not True for p in (recall, lattice, baseline, learned))
            or baseline.get("training_performed") is not False
            or learned.get("training_performed") is not True
            or baseline.get("feature_version") != FEATURE_VERSION
            or recall.get("source_labels_used_for_selection") is not False
            or learned.get("source_labels_used_at_inference") is not False
            or learned.get("development_labels_used_for_updates_or_checkpoint_selection") is not False
            or learned.get("use_contract_content_sha256") != content_hash(contract)):
        raise ValueError("invalid_frozen_parent_report")
    for parent in (baseline, learned):
        guard(parent["input_hashes"]); guard(parent["code_hashes"])
    guard({str(Path(__file__).with_name("harmony_candidate_recall.py")): recall["code_sha256"],
           str(Path(__file__).with_name("harmony_lattice_recall.py")): lattice["code_sha256"]})
    code_hashes = {str(p.resolve()): digest(p) for p in (
        Path(__file__), Path(__file__).with_name("harmony_margin_learning.py"))}
    if len({len(p["records"]) for p in (recall, lattice, baseline, learned)}) != 1:
        raise ValueError("parent_context_count_mismatch")
    family_splits = defaultdict(set)
    for entry in manifest:
        validate_policy(entry); family_splits[entry["work_family_id"]].add(entry["split"])
    if any(len(splits) != 1 for splits in family_splits.values()):
        raise ValueError("work_family_split_leakage")
    examples, prepared, seen = [], [], set()
    for index, (row, old, base, previous) in enumerate(zip(
            recall["records"], lattice["records"], baseline["records"], learned["records"]), 1):
        identity = tuple(row[k] for k in ("pair_id", "plan_index", "sample_id"))
        if identity in seen or any(identity != tuple(r[k] for k in ("pair_id", "plan_index", "sample_id"))
                                   for r in (old, base, previous)):
            raise ValueError("duplicate_or_mismatched_context")
        if any(previous["evaluations"].get(arm) != val for arm, val in base["evaluations"].items()):
            raise ValueError("historical_baseline_evaluation_changed")
        seen.add(identity)
        packet = read(old["search_artifact"], old["search_artifact_sha256"], True)
        context = read(old["source_context_artifact"], old["source_context_sha256"], True)
        entry = packet["provenance"]["manifest_entry"]
        bundle, search = context["bundle"], packet["search"]
        if (entry not in manifest or entry["split"] != row["split"]
                or entry["work_family_id"] != row["work_family_id"]
                or packet["pair_id"] != row["pair_id"] or context["pair_id"] != row["pair_id"]
                or packet["plan_index"] != row["plan_index"] or context["plan_index"] != row["plan_index"]
                or packet["sample"]["sample_id"] != row["sample_id"]
                or packet["sample"]["span"] != row["sample_span"]
                or context["provenance"] != packet["provenance"]
                or _hash(bundle) != packet["input_bundle_content_sha256"]
                or search["input_bundle_content_sha256"] != packet["input_bundle_content_sha256"]):
            raise ValueError("frozen_context_binding_mismatch")
        problem = prepare(bundle, search)
        fixed = decode(problem)  # NO labels; recompute rather than trust metrics.
        if content_hash(fixed["selected"]) != content_hash(base["selected_prediction"]):
            raise ValueError("fixed_baseline_prediction_changed")
        prepared.append((row, old, base, previous, entry, problem))
        if entry["split"] == "train" and entry["manifest_entry_id"] in approvals:
            examples.append(TrainingExample(row["sample_id"], entry, problem, tuple(cells_from_record(row))))
        if index % 40 == 0 or index == len(recall["records"]):
            print(f"[{index}/{len(recall['records'])}] prepared frozen features", flush=True)
        del packet, context, bundle, search
    models = {}
    for arm, boundary_weight in ARMS.items():
        models[arm] = fit(examples, contract, manifest, expected_recall_sha, boundary_weight=boundary_weight,
                          progress=lambda r, name=arm: print(
                              f"[{name} epoch {r['epoch']}/5] updates={r['updates']} statuses={r['statuses']}", flush=True))
    if len({content_hash(m["training_eligibility"]) for m in models.values()}) != 1:
        raise ValueError("ablation_training_eligibility_changed")
    rows, statuses = [], {arm: Counter() for arm in ARMS}
    for index, (row, old, base, previous, entry, problem) in enumerate(prepared, 1):
        predictions, details, evaluations = {}, {}, dict(previous["evaluations"])
        # Finish both label-blind inferences BEFORE reading evaluation labels.
        results = {arm: infer(problem, model) for arm, model in models.items()}
        cells = cells_from_record(row)
        for arm, result in results.items():
            statuses[arm][result["status"]] += 1
            predictions[arm] = result["selected"]
            details[arm] = {k: result[k] for k in ("status", "transitions", "exact_optimum_under_declared_score")}
            evaluations[arm] = evaluate_selection(evaluation_path(result), cells)
        rows.append({k: row[k] for k in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span")}
                    | {"selected_predictions": predictions, "decoder_details": details,
                       "evaluations": evaluations, "lattice_hit": old["diagnosis"]["lattice_hit"],
                       "lattice_diagnosis": old["diagnosis"]["outcome"],
                       "source_context_artifact": old["source_context_artifact"],
                       "source_context_sha256": old["source_context_sha256"],
                       "search_artifact": old["search_artifact"], "search_artifact_sha256": old["search_artifact_sha256"]})
        if index % 40 == 0 or index == len(prepared):
            print(f"[{index}/{len(prepared)}] evaluated BOTH margin arms", flush=True)
    arms = tuple(rows[0]["evaluations"])
    summary = {arm: summarize(rows, arm) for arm in arms}
    for arm, val in learned["summary"].items():
        if summary[arm] != val:
            raise ValueError("historical_summary_changed")
    # Posthoc diagnostic selection does NOT alter weights/epochs/arm choice.
    changes = []
    for arm in ARMS:
        differences = [(fraction(r["evaluations"][arm]["selected_root_members_time"])
                        - fraction(r["evaluations"]["direct_joint_music"]["selected_root_members_time"]), i)
                       for i, r in enumerate(rows) if r["evaluations"][arm]["fully_evaluable"]]
        indices = {i for d, i in sorted(differences)[:3] if d < 0}
        indices |= {i for d, i in sorted(differences, reverse=True)[:3] if d > 0}
        for i in sorted(indices):
            r, _, base, previous, entry, _ = prepared[i]
            result = rows[i]
            changes.append({"arm": arm, "sample_id": r["sample_id"], "split": r["split"],
                            "work_family_id": r["work_family_id"], "sample_span": r["sample_span"],
                            "entry": entry, "reference_cells": r["reference_cells"],
                            **{k: result[k] for k in ("source_context_artifact", "source_context_sha256", "search_artifact", "search_artifact_sha256")},
                            "predictions": {"direct_joint_music": compact_prediction(base["selected_prediction"]),
                                            "learned_joint_music": compact_prediction(previous["selected_prediction"]),
                                            arm: compact_prediction(result["selected_predictions"][arm])},
                            "evaluations": {k: result["evaluations"][k] for k in ("direct_joint_music", "learned_joint_music", arm)}})
    guard(dict(inputs)); guard(code_hashes)
    report = {"version": VERSION, "complete": True, "feature_version": FEATURE_VERSION,
              "summary": summary,
              "by_split": {split: {arm: summarize([r for r in rows if r["split"] == split], arm) for arm in arms}
                           for split in sorted({r["split"] for r in rows})},
              "models": {arm: {"model_ref": m["model_id"], "model_content_sha256": content_hash(m),
                               "configuration": m["configuration"], "updates": len(m["updates"]),
                               "feature_collisions": len(m["feature_collisions"])} for arm, m in models.items()},
              "use_contract_content_sha256": content_hash(contract), "training_performed": True,
              "training_reference_labels_used": True, "source_labels_used_at_inference": False,
              "development_labels_used_for_updates_or_checkpoint_selection": False,
              "independent_test_accuracy_measured": False, "eligibility_changed": False,
              "production_modified": False, "candidate_inventory_modified": False,
              "previous_predictions_modified": False, "commercial_legal_clearance": False,
              "research_only_restrictions": dict(next(iter(models.values()))["restrictions"]),
              "decoder_statuses": {arm: dict(val) for arm, val in statuses.items()}, "records": rows,
              "input_hashes": inputs, "code_hashes": code_hashes,
              "training_contexts_seen": next(iter(models.values()))["training_contexts_seen"],
              "reachable_complete_training_contexts": next(iter(models.values()))["reachable_complete_training_contexts"],
              "elapsed_seconds": perf_counter()-started,
              "metric_scope": "absolute_root_and_spelled_members_not_full_Roman_inversion_key_NCT_cadence",
              "limits": ["Previously exposed train/dev contexts, NOT independent test accuracy.",
                         "Same original eleven features/candidates; missing NCT/key evidence remains unavailable.",
                         "Time-only vs time+boundary isolates loss. Relative to J2b the UPDATE ALGORITHM also changes.",
                         "No dev tuning/checkpoint/arm selection; both predeclared arms reported.",
                         "No commercial deployment, external API or checkpoint redistribution."]}
    output.mkdir(parents=True, exist_ok=False)
    for arm, model in models.items():
        (output/(arm+"-model.json")).write_text(json.dumps(model, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    for name, value in (("report.json", report), ("selection-changes.json", changes)):
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("recall", "lattice", "baseline", "learned", "contract", "output", "expected-recall-sha",
                 "expected-lattice-sha", "expected-baseline-sha", "expected-learned-sha", "expected-contract-sha"):
        parser.add_argument("--"+name, required=True)
    args = parser.parse_args()
    result = run(args.recall, args.lattice, args.baseline, args.learned, args.contract, args.output,
                 expected_recall_sha=args.expected_recall_sha, expected_lattice_sha=args.expected_lattice_sha,
                 expected_baseline_sha=args.expected_baseline_sha, expected_learned_sha=args.expected_learned_sha,
                 expected_contract_sha=args.expected_contract_sha)
    print(json.dumps({"summary": {a: result["summary"][a] for a in ARMS},
                      "training_contexts": result["reachable_complete_training_contexts"],
                      "elapsed_seconds": result["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
