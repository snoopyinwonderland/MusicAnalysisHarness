"""Pinned local research fitting and full frozen train/dev comparison."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_lattice_recall import cells_from_record
from .harmony_progression_search import _hash
from .harmony_scored_decoder import FEATURE_VERSION, decode, evaluation_path, prepare
from .harmony_scored_decoder_trial import evaluate_selection, summarize
from .harmony_structured_learning import (
    RESTRICTIONS, USE_CONTRACT_VERSION, TrainingExample, content_hash, fit, infer,
    validate_use_contract,
)
from .source_locator_revision_trial import validate_policy

VERSION = "harmony-structured-learning-trial-0.1.0"
REPOSITORIES = {
    "beethoven-quartets": "https://github.com/DCMLab/ABC",
    "beethoven-sonatas": "https://github.com/DCMLab/beethoven_piano_sonatas",
    "chopin-mazurkas": "https://github.com/DCMLab/chopin_mazurkas",
    "corelli": "https://github.com/DCMLab/corelli",
    "mozart-sonatas": "https://github.com/DCMLab/mozart_piano_sonatas",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def research_contract(manifest, parent_sha, source_root, *, confirmation=None):
    """Draft by default. Only supplied HUMAN text confirms experimental scope.

    This records local license notices, not a commercial license clearance or
    a legal finding that any company's internal use is necessarily NC.
    """
    sources = {}
    for collection in sorted({e["collection_id"] for e in manifest}):
        root = Path(source_root)/collection
        licence, readme = root/"LICENSE", root/"README.md"
        if (not licence.read_text(encoding="utf-8").startswith("Attribution-NonCommercial-ShareAlike 4.0 International")
                or "https://creativecommons.org/licenses/by-nc-sa/4.0/" not in readme.read_text(encoding="utf-8")):
            raise ValueError("local_source_license_notice_mismatch")
        sources[collection] = {
            "spdx": "CC-BY-NC-SA-4.0", "reference_url": REPOSITORIES[collection],
            "local_license_path": str(licence.resolve()), "local_license_sha256": digest(licence),
            "readme_path": str(readme.resolve()), "readme_sha256": digest(readme),
            "attribution_reference": REPOSITORIES[collection]+"#citation",
        }
    return {"version": USE_CONTRACT_VERSION, "parent_recall_sha256": parent_sha,
            "purpose": "local_noncommercial_research",
            "human_scope_confirmation": confirmation or {"status": "pending", "source": "direct_user_message", "text": None},
            "restrictions": {k: False for k in RESTRICTIONS},
            "commercial_legal_clearance": False, "original_manifest_permissions_modified": False,
            "legal_note": "Internal use is not automatically noncommercial. Scope is bounded to a local research experiment; commercial rights and any checkpoint distribution remain unresolved.",
            "source_notices": sources,
            "approved_entries": [{"manifest_entry_id": e["manifest_entry_id"], "manifest_entry_sha256": content_hash(e),
                                  "source_license": sources[e["collection_id"]]}
                                 for e in manifest if e["split"] == "train"]}


def run(recall_path, lattice_path, baseline_path, contract_path, output, *,
        expected_recall_sha, expected_lattice_sha, expected_baseline_sha, expected_contract_sha):
    started = perf_counter(); output = Path(output)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    inputs = {}
    def read(path, expected, compressed=False):
        path = Path(path)
        data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
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
    # Fail before opening training references/artifacts, and before output.
    approvals = validate_use_contract(contract, manifest, expected_recall_sha)
    for approval in approvals.values():
        evidence = approval["source_license"]
        guard({evidence["local_license_path"]: evidence["local_license_sha256"],
               evidence["readme_path"]: evidence["readme_sha256"]})
    lattice = read(lattice_path, expected_lattice_sha)
    baseline = read(baseline_path, expected_baseline_sha)
    if (recall.get("complete") is not True or lattice.get("complete") is not True
            or baseline.get("complete") is not True or baseline.get("training_performed") is not False
            or baseline.get("feature_version") != FEATURE_VERSION
            or recall.get("source_labels_used_for_selection") is not False
            or baseline.get("source_labels_used_for_selection") is not False):
        raise ValueError("invalid_frozen_parent_report")
    guard(baseline["input_hashes"]); guard(baseline["code_hashes"])
    guard({str(Path(__file__).with_name("harmony_candidate_recall.py")): recall["code_sha256"],
           str(Path(__file__).with_name("harmony_lattice_recall.py")): lattice["code_sha256"]})
    code_hashes = {str(p.resolve()): digest(p) for p in (
        Path(__file__), Path(__file__).with_name("harmony_structured_learning.py"))}
    if not (len(recall["records"]) == len(lattice["records"]) == len(baseline["records"])):
        raise ValueError("parent_context_count_mismatch")
    family_splits = defaultdict(set)
    for entry in manifest:
        validate_policy(entry)
        family_splits[entry["work_family_id"]].add(entry["split"])
    if any(len(splits) != 1 for splits in family_splits.values()):
        raise ValueError("work_family_split_leakage")
    examples, prepared, seen = [], [], set()
    for index, (row, old, base) in enumerate(zip(recall["records"], lattice["records"], baseline["records"]), 1):
        identity = tuple(row[k] for k in ("pair_id", "plan_index", "sample_id"))
        if (identity in seen or identity != tuple(old[k] for k in ("pair_id", "plan_index", "sample_id"))
                or identity != tuple(base[k] for k in ("pair_id", "plan_index", "sample_id"))):
            raise ValueError("duplicate_or_mismatched_context")
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
        # Recompute the unchanged, label-blind fixed baseline before gold access.
        fixed = decode(problem)
        if content_hash(fixed["selected"]) != content_hash(base["selected_prediction"]):
            raise ValueError("fixed_baseline_prediction_changed")
        prepared.append((row, old, base, entry, problem))
        if entry["split"] == "train" and entry["manifest_entry_id"] in approvals:
            examples.append(TrainingExample(row["sample_id"], entry, problem, tuple(cells_from_record(row))))
        if index % 40 == 0 or index == len(recall["records"]):
            print(f"[{index}/{len(recall['records'])}] prepared frozen features", flush=True)
        del packet, context, bundle, search
    model = fit(examples, contract, manifest, expected_recall_sha,
                progress=lambda r: print(f"[epoch {r['epoch']}/5] updates={r['updates']}", flush=True))
    rows, statuses = [], Counter()
    for index, (row, old, base, entry, problem) in enumerate(prepared, 1):
        result = infer(problem, model)
        # Dev labels were not available to fit; evaluator only, after inference.
        evaluation = evaluate_selection(evaluation_path(result), cells_from_record(row))
        statuses[result["status"]] += 1
        rows.append({k: row[k] for k in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span")}
                    | {"selected_prediction": result["selected"], "decoder_status": result["status"],
                       "decoder_transitions": result["transitions"],
                       "exact_optimum_under_declared_score": result["exact_optimum_under_declared_score"],
                       "evaluations": {**base["evaluations"], "learned_joint_music": evaluation},
                       "lattice_hit": old["diagnosis"]["lattice_hit"],
                       "lattice_diagnosis": old["diagnosis"]["outcome"],
                       "source_context_artifact": old["source_context_artifact"],
                       "source_context_sha256": old["source_context_sha256"],
                       "search_artifact": old["search_artifact"], "search_artifact_sha256": old["search_artifact_sha256"]})
        if index % 40 == 0 or index == len(prepared):
            print(f"[{index}/{len(prepared)}] evaluated learned predictions", flush=True)
    arms = tuple(rows[0]["evaluations"])
    summary = {arm: summarize(rows, arm) for arm in arms}
    for arm in baseline["summary"]:
        if summary[arm] != baseline["summary"][arm]:
            raise ValueError("baseline_summary_changed")
    guard(dict(inputs)); guard(code_hashes)
    report = {"version": VERSION, "complete": True, "summary": summary,
              "by_split": {split: {arm: summarize([r for r in rows if r["split"] == split], arm) for arm in arms}
                           for split in sorted({r["split"] for r in rows})},
              "model_ref": model["model_id"], "model_content_sha256": content_hash(model),
              "use_contract_content_sha256": content_hash(contract), "training_performed": True,
              "training_reference_labels_used": True, "source_labels_used_at_inference": False,
              "development_labels_used_for_updates_or_checkpoint_selection": False,
              "independent_test_accuracy_measured": False, "eligibility_changed": False,
              "production_modified": False, "candidate_inventory_modified": False,
              "previous_predictions_modified": False, "commercial_legal_clearance": False,
              "research_only_restrictions": dict(model["restrictions"]),
              "decoder_statuses": dict(statuses), "records": rows,
              "input_hashes": inputs, "code_hashes": code_hashes,
              "training_contexts_seen": model["training_contexts_seen"],
              "reachable_complete_training_contexts": model["reachable_complete_training_contexts"],
              "elapsed_seconds": perf_counter()-started,
              "metric_scope": "absolute_root_and_spelled_members_not_full_Roman_inversion_key_NCT_cadence",
              "limits": ["Previously exposed development contexts; not an independent test.",
                         "No added candidates; unreachable/partial examples excluded from fitting, never from evaluation.",
                         "Learned feature costs are not calibrated probabilities or complete textbook reasoning.",
                         "Research-only weights: no commercial deployment, external API or checkpoint redistribution."]}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("model.json", model), ("report.json", report)):
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("recall", "lattice", "baseline", "contract", "output", "expected-recall-sha",
                 "expected-lattice-sha", "expected-baseline-sha", "expected-contract-sha"):
        parser.add_argument("--"+name, required=True)
    args = parser.parse_args()
    result = run(args.recall, args.lattice, args.baseline, args.contract, args.output,
                 expected_recall_sha=args.expected_recall_sha, expected_lattice_sha=args.expected_lattice_sha,
                 expected_baseline_sha=args.expected_baseline_sha, expected_contract_sha=args.expected_contract_sha)
    print(json.dumps({"summary": result["summary"]["learned_joint_music"],
                      "training_contexts": result["reachable_complete_training_contexts"],
                      "elapsed_seconds": result["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
