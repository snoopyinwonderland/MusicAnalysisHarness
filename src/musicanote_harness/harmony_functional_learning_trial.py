"""Frozen J2f: one predeclared train-only 20-feature model versus J2e.

No candidate regeneration beyond the identical J2e supply; no dev tuning.
    python -m musicanote_harness.harmony_functional_learning_trial --help
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .harmony_candidate_recall import fraction
from .harmony_evidence_scoring import prepare_with_evidence
from .harmony_evidence_scoring_trial import load_ir
from .harmony_functional_learning import INITIAL_WEIGHTS, TrainingExample, fit, infer, path_features
from .harmony_functional_scoring import FEATURE_VERSION, prepare_functional_evidence, supply
from .harmony_lattice_recall import cells_from_record
from .harmony_progression_search import _hash
from .harmony_scored_decoder import evaluation_path, feature_cost
from .harmony_scored_decoder_trial import evaluate_selection, summarize
from .harmony_structured_learning import content_hash, validate_use_contract
from .harmony_structured_learning_trial import digest
from .source_locator_revision_trial import validate_policy

VERSION = "harmony-functional-learning-trial-0.1.0"
ARM = "functional_run_learned"
BASELINE = "functional_supply_and_resolution"


def run(previous_path, recall_path, integration_path, contract_path, output, *,
        expected_previous_sha, expected_recall_sha, expected_integration_sha, expected_contract_sha):
    started = perf_counter(); output = Path(output)
    if output.exists():
        raise ValueError("output_exists_no_overwrite")
    inputs = {}
    def read(path, expected, compressed=False, raw=False):
        path = Path(path); data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
        if sha != expected:
            raise ValueError("input_sha_mismatch:"+str(path))
        inputs[str(path.resolve())] = sha
        return None if raw else json.loads((gzip.decompress(data) if compressed else data).decode("utf-8"))
    def guard(mapping):
        for path, sha in mapping.items():
            if digest(path) != sha:
                raise ValueError("frozen_input_changed:"+str(path))
            inputs[str(Path(path).resolve())] = sha
    previous = read(previous_path, expected_previous_sha); recall = read(recall_path, expected_recall_sha)
    contract = read(contract_path, expected_contract_sha); manifest = recall["package_manifest"]
    approvals = validate_use_contract(contract, manifest, expected_recall_sha)
    for a in approvals.values():
        lic = a["source_license"]
        guard({lic["local_license_path"]: lic["local_license_sha256"], lic["readme_path"]: lic["readme_sha256"]})
    integration = read(integration_path, expected_integration_sha)
    if (any(r.get("complete") is not True for r in (previous, recall, integration))
            or previous.get("feature_version") != FEATURE_VERSION
            or previous.get("training_performed") is not False
            or previous.get("source_labels_used_at_inference") is not False
            or previous.get("development_tuning_performed") is not False
            or integration.get("source_labels_used") is not False):
        raise ValueError("invalid_parent_contract")
    guard(previous["input_hashes"]); guard(previous["code_hashes"])
    code_names = (Path(__file__).name, "harmony_functional_learning.py", "harmony_margin_learning.py",
                  "harmony_structured_learning.py", "harmony_structured_learning_trial.py")
    code_hashes = {str(Path(__file__).with_name(n).resolve()): digest(Path(__file__).with_name(n)) for n in code_names}
    if len(previous["records"]) != len(recall["records"]):
        raise ValueError("parent_context_count_mismatch")
    families = defaultdict(set)
    for entry in manifest:
        validate_policy(entry); families[entry["work_family_id"]].add(entry["split"])
    if any(len(s) != 1 for s in families.values()):
        raise ValueError("work_family_split_leakage")
    seen = set(); ir_cache = {}; geometry = {}; prepared = []; examples = []
    for index, (old, ref) in enumerate(zip(previous["records"], recall["records"]), 1):
        identity = tuple(ref[k] for k in ("pair_id", "plan_index", "sample_id", "split", "work_family_id"))
        if identity in seen or identity != tuple(old[k] for k in ("pair_id", "plan_index", "sample_id", "split", "work_family_id")):
            raise ValueError("duplicate_or_mismatched_context")
        if old["reference_cells"] != ref["reference_cells"] or old["sample_span"] != ref["sample_span"]:
            raise ValueError("previous_reference_or_span_changed")
        seen.add(identity)
        packet = read(old["search_artifact"], old["search_artifact_sha256"], True)
        context = read(old["source_context_artifact"], old["source_context_sha256"], True)
        provenance = context["provenance"]; entry = packet["provenance"]["manifest_entry"]
        bundle, search = context["bundle"], packet["search"]
        if (entry not in manifest or entry["split"] != ref["split"] or entry["work_family_id"] != ref["work_family_id"]
                or context["pair_id"] != ref["pair_id"] or packet["pair_id"] != ref["pair_id"]
                or context["plan_index"] != ref["plan_index"] or packet["plan_index"] != ref["plan_index"]
                or packet["sample"]["sample_id"] != ref["sample_id"] or packet["sample"]["span"] != ref["sample_span"]
                or provenance != packet["provenance"] or _hash(bundle) != packet["input_bundle_content_sha256"]
                or search["input_bundle_content_sha256"] != packet["input_bundle_content_sha256"]):
            raise ValueError("context_source_binding_mismatch")
        key = ref["pair_id"], bundle["input_ir_content_sha256"]
        if key not in ir_cache:
            ir_cache[key] = load_ir(dict(entry, pair_id=ref["pair_id"]), provenance, bundle, integration, read)
        ir = ir_cache[key]; problem, source = prepare_with_evidence(ir, bundle, search)
        if source.source_ir_content_sha256 != old["full_ir_content_sha256"]:
            raise ValueError("previous_source_ir_changed")
        ev = prepare_functional_evidence(ir, source); expanded, receipts = supply(problem, ev)
        if (expanded.edges[:len(problem.edges)] != problem.edges or expanded.points != problem.points
                or expanded.max_segments != problem.max_segments or len(problem.edges) != old["old_edge_count"]
                or len(expanded.edges) != old["expanded_edge_count"]
                or content_hash(receipts) != content_hash(old["functional_candidate_receipts"])):
            raise ValueError("frozen_functional_candidate_inventory_changed")
        chosen = old["selected_predictions"][BASELINE]
        if chosen:
            ids = [s["semantic_group_ref"] for s in chosen["segments"]]
            if feature_cost(path_features(expanded, ev, ids), INITIAL_WEIGHTS) != fraction(chosen["score_cost"]):
                raise ValueError("previous_functional_selection_score_changed")
        # Intern validated, context-independent source geometry by full IR SHA.
        # Each bundle is still validated above; its observations/caches stay local.
        if key in geometry:
            rows, neighbors, erows, links = geometry[key]
            source.rows = rows; source.neighbors = neighbors; ev.rows = erows; ev.links = links
        else:
            geometry[key] = source.rows, source.neighbors, ev.rows, ev.links
        prepared.append((old, ref, entry, expanded, ev))
        if entry["split"] == "train" and entry["manifest_entry_id"] in approvals:
            examples.append(TrainingExample(ref["sample_id"], entry, expanded, ev, tuple(cells_from_record(ref))))
        if index % 20 == 0 or index == len(previous["records"]):
            print(f"[{index}/{len(previous['records'])}] pinned J2e inventory verified; scores={len(ir_cache)}", flush=True)
    model = fit(examples, contract, manifest, expected_recall_sha,
                progress=lambda r: print(json.dumps(r, ensure_ascii=False), flush=True))
    rows = []; statuses = Counter(); changes = []
    for index, (old, ref, entry, problem, ev) in enumerate(prepared, 1):
        result = infer(problem, ev, model)  # NO reference input, no model changes.
        cells = cells_from_record(ref); evaluations = dict(old["evaluations"])
        evaluations[ARM] = evaluate_selection(evaluation_path(result), cells); statuses[result["status"]] += 1
        row = {k: ref[k] for k in ("pair_id", "plan_index", "sample_id", "work_family_id", "split", "sample_span")}
        row.update(evaluations=evaluations, selected_prediction=result["selected"],
                   decoder_details={k: result[k] for k in ("status", "transitions", "exact_optimum_under_declared_score")},
                   expanded_lattice_hit=old["expanded_lattice_diagnosis"]["lattice_hit"],
                   reference_cells=ref["reference_cells"], full_ir_content_sha256=old["full_ir_content_sha256"],
                   candidate_inventory_content_sha256=content_hash([[e.group_id, e.start_index, e.end_index, e.signature, e.blockers] for e in problem.edges]),
                   **{k: old[k] for k in ("source_context_artifact", "source_context_sha256", "search_artifact", "search_artifact_sha256")})
        rows.append(row)
        # Release only derived caches after final inference for this context.
        ev.source._feature_cache.clear(); ev._surface_cache.clear(); ev._pair_cache.clear()
        if index % 20 == 0 or index == len(prepared):
            print(f"[{index}/{len(prepared)}] label-blind learned prediction evaluated", flush=True)
    arms = tuple(rows[0]["evaluations"]); summary = {a: summarize(rows, a) for a in arms}
    if any(summary[a] != v for a, v in previous["summary"].items()):
        raise ValueError("historical_summary_changed")
    deltas = [(fraction(r["evaluations"][ARM]["selected_root_members_time"])
               - fraction(r["evaluations"][BASELINE]["selected_root_members_time"]), i)
              for i, r in enumerate(rows) if r["evaluations"][ARM]["fully_evaluable"]]
    picks = {i for d, i in sorted(deltas)[:4] if d < 0} | {i for d, i in sorted(deltas, reverse=True)[:4] if d > 0}
    for i in sorted(picks):
        old, ref, entry, problem, ev = prepared[i]
        changes.append({"context": rows[i], "entry": entry, "baseline_prediction": old["selected_predictions"][BASELINE]})
    guard(dict(inputs)); guard(code_hashes)
    report = {"version": VERSION, "complete": True, "feature_version": FEATURE_VERSION, "summary": summary,
              "by_split": {s: {a: summarize([r for r in rows if r["split"] == s], a) for a in arms} for s in sorted({r["split"] for r in rows})},
              "candidate_coverage": previous["candidate_coverage"], "decoder_statuses": dict(statuses), "records": rows,
              "model_ref": model["model_id"], "model_content_sha256": content_hash(model), "configuration": model["configuration"],
              "training_contexts_seen": model["training_contexts_seen"], "reachable_complete_training_contexts": model["reachable_complete_training_contexts"],
              "updates": len(model["updates"]), "feature_collisions": len(model["feature_collisions"]),
              "use_contract_content_sha256": content_hash(contract), "research_only_restrictions": model["restrictions"],
              "training_performed": True, "training_reference_labels_used": True, "source_labels_used_at_inference": False,
              "development_labels_used_for_updates_or_checkpoint_selection": False, "independent_test_accuracy_measured": False,
              "candidate_inventory_changed_from_J2e": False, "cohort_eligibility_changed": False,
              "training_reachability_recomputed_on_J2e_inventory": True, "previous_predictions_modified": False,
              "production_modified": False, "commercial_legal_clearance": False, "metric_scope": previous["metric_scope"],
              "input_hashes": inputs, "code_hashes": code_hashes, "elapsed_seconds": perf_counter()-started,
              "limits": ["One predeclared model; exposed train/dev, NOT independent test accuracy or dev checkpoint choice.",
                         "Same J2e source observations/expanded inventory/raw segment and transition cap.",
                         "Root+spelled-members/time, not complete Roman/inversion/NCT/key/cadence accuracy.",
                         "None observations remain unavailable; count features do not prove musical function.",
                         "Local noncommercial research only; no production/API/checkpoint redistribution."]}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("model.json", model), ("report.json", report), ("selection-changes.json", changes)):
        (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("previous", "recall", "integration", "contract", "output", "expected-previous-sha", "expected-recall-sha",
              "expected-integration-sha", "expected-contract-sha"):
        p.add_argument("--"+n, required=True)
    a = p.parse_args()
    result = run(a.previous, a.recall, a.integration, a.contract, a.output,
                 expected_previous_sha=a.expected_previous_sha, expected_recall_sha=a.expected_recall_sha,
                 expected_integration_sha=a.expected_integration_sha, expected_contract_sha=a.expected_contract_sha)
    print(json.dumps({"summary": result["summary"][ARM], "reachable_training_contexts": result["reachable_complete_training_contexts"],
                      "updates": result["updates"], "elapsed_seconds": result["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
