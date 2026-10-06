"""Research-only structured weight fitting; gold never enters inference.

The old manifest is immutable. A separately confirmed, source-bound research
use contract is necessary; internal_research_use alone is not training consent.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import json

from .harmony_candidate_recall import fraction, rational
from .harmony_scored_decoder import (
    DEFAULT_WEIGHTS, FEATURE_VERSION, Problem, decode, evaluation_path,
    transition, weights_contract,
)

VERSION = "harmony-structured-learning-0.1.0"
USE_CONTRACT_VERSION = "harmony-research-training-use-0.1.0"
PRECISION = 1_000_000
RESTRICTIONS = (
    "commercial_use", "production_deployment", "external_api_transmission",
    "checkpoint_redistribution",
)


@dataclass(frozen=True)
class TrainingExample:
    sample_id: str
    entry: dict
    problem: Problem
    cells: tuple


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_use_contract(contract, manifest, parent_sha):
    """Validate a human-confirmed scope, not grant legal rights or consent."""
    if contract.get("version") != USE_CONTRACT_VERSION or contract.get("parent_recall_sha256") != parent_sha:
        raise ValueError("training_contract_parent_mismatch")
    if contract.get("purpose") != "local_noncommercial_research":
        raise ValueError("unsupported_training_purpose")
    confirmation = contract.get("human_scope_confirmation", {})
    if (confirmation.get("status") != "confirmed" or confirmation.get("source") != "direct_user_message"
            or not isinstance(confirmation.get("text"), str) or not confirmation["text"].strip()
            or not confirmation.get("confirmed_at")):
        raise ValueError("research_scope_confirmation_required")
    if any(contract.get("restrictions", {}).get(k) is not False for k in RESTRICTIONS):
        raise ValueError("research_scope_restriction_missing")
    entries = {e["manifest_entry_id"]: e for e in manifest}
    if len(entries) != len(manifest):
        raise ValueError("duplicate_manifest_entry")
    approved = {}
    for approval in contract.get("approved_entries", []):
        key = approval["manifest_entry_id"]
        if key in approved or key not in entries:
            raise ValueError("duplicate_or_unknown_training_approval")
        entry = entries[key]
        if entry.get("split") != "train" or entry.get("rights", {}).get("internal_research_use") is not True:
            raise ValueError("protected_or_nonresearch_training_entry")
        if approval.get("manifest_entry_sha256") != content_hash(entry):
            raise ValueError("training_entry_binding_mismatch")
        evidence = approval.get("source_license", {})
        if (evidence.get("spdx") != "CC-BY-NC-SA-4.0" or not evidence.get("reference_url")
                or not evidence.get("local_license_path") or not evidence.get("local_license_sha256")
                or not evidence.get("readme_path") or not evidence.get("readme_sha256")
                or not evidence.get("attribution_reference")):
            raise ValueError("source_license_evidence_required")
        approved[key] = approval
    if not approved:
        raise ValueError("no_approved_training_entries")
    return approved


def compatible_problem(problem, cells):
    """Training-only latent gold path: filter EXISTING edges, never add gold."""
    if not cells:
        raise ValueError("empty_training_reference")
    cursor = cells[0]["start"]
    for cell in cells:
        if cell["start"] != cursor or cell["end"] <= cursor:
            raise ValueError("invalid_training_reference_partition")
        cursor = cell["end"]
    if problem.status != "ready":
        return None, "lattice_unavailable"
    if cells[0]["start"] != problem.points[0] or cursor != problem.points[-1]:
        raise ValueError("training_reference_context_mismatch")
    if any(c["signature"] is None for c in cells):
        return None, "partial_or_unsupported_reference"
    edges = tuple(e for e in problem.edges if all(
        c["signature"] == e.signature for c in cells
        if e.start < c["end"] and c["start"] < e.end
    ))
    return replace(problem, edges=edges), None


def path_features(problem, prediction):
    if prediction["selected"] is None:
        raise ValueError("no_selected_path_features")
    by_id = {e.group_id: e for e in problem.edges}
    result = {name: Fraction() for name in DEFAULT_WEIGHTS}
    previous = None
    for segment in prediction["selected"]["segments"]:
        edge = by_id[segment["semantic_group_ref"]]
        for features in (edge.features, transition(previous, edge)):
            for name, value in features.items():
                if name in result and value is not None:
                    result[name] += value
        previous = edge.signature
    return result


def quantize(value):
    """Bound denominator; round nearest, ties to even, no float conversion."""
    return Fraction(round(Fraction(value)*PRECISION), PRECISION)


def fit(examples, contract, manifest, parent_sha, *, epochs=5, rate=Fraction(1, 10),
        weight_bound=Fraction(4), transition_budget=2_000_000, progress=None):
    """Averaged structured perceptron in COST convention (lower is better).

    Predeclared deterministic order, fixed five epochs, train only. References
    choose the latent best compatible path during fitting, not during deploy.
    Availability=None remains missing, never becomes a factual false or NCT.
    """
    if type(epochs) is not int or not 1 <= epochs <= 20 or type(rate) is not Fraction or rate <= 0:
        raise ValueError("invalid_learning_configuration")
    if type(weight_bound) is not Fraction or weight_bound <= 0:
        raise ValueError("invalid_weight_bound")
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    approved_entries = validate_use_contract(contract, manifest, parent_sha)
    examples = sorted(examples, key=lambda x: (x.entry["work_family_id"], x.sample_id))
    seen = set()
    # Validate ALL entries before fitting even the first one.
    for example in examples:
        entry = example.entry
        key = entry["manifest_entry_id"]
        if entry.get("split") != "train" or key not in approved_entries:
            raise ValueError("unapproved_or_nontrain_learning_example")
        if approved_entries[key]["manifest_entry_sha256"] != content_hash(entry):
            raise ValueError("training_entry_binding_mismatch")
        if example.sample_id in seen:
            raise ValueError("duplicate_training_sample")
        seen.add(example.sample_id)
    weights = {k: quantize(max(-weight_bound, min(weight_bound, v)))
               for k, v in weights_contract().items()}
    totals = {k: Fraction() for k in weights}
    ticks = 0; epoch_records = []; updates = []; eligibility = []
    eligible = []
    for example in examples:
        gold, reason = compatible_problem(example.problem, example.cells)
        if gold is not None:
            check = decode(gold, weights, transition_budget=transition_budget)
            reason = None if check["selected"] else check["status"]
        eligibility.append({"sample_id": example.sample_id, "work_family_id": example.entry["work_family_id"],
                            "eligible": reason is None, "reason": reason})
        if reason is None:
            eligible.append((example, gold))
    if not eligible:
        raise ValueError("no_reachable_complete_training_references")
    for epoch in range(1, epochs+1):
        statuses = Counter(); update_count = 0
        for example, gold in eligible:
            prediction = decode(example.problem, weights, transition_budget=transition_budget)
            target = decode(gold, weights, transition_budget=transition_budget)
            if prediction["selected"] is None or target["selected"] is None:
                statuses["resource_abstention_no_update"] += 1
            else:
                pred_phi = path_features(example.problem, prediction)
                gold_phi = path_features(gold, target)
                delta = {k: pred_phi[k]-gold_phi[k] for k in weights}
                # Increase predicted cost relative to the compatible target.
                if any(delta.values()):
                    weights = {k: quantize(max(-weight_bound, min(weight_bound, weights[k]+rate*delta[k])))
                               for k in weights}
                    update_count += 1
                    updates.append({"epoch": epoch, "sample_id": example.sample_id,
                                    "predicted_group_refs": [s["semantic_group_ref"] for s in prediction["selected"]["segments"]],
                                    "training_target_group_refs": [s["semantic_group_ref"] for s in target["selected"]["segments"]],
                                    "feature_delta": {k: rational(v) for k, v in delta.items()}})
                    statuses["updated"] += 1
                else:
                    statuses["same_feature_vector_no_update"] += 1
            ticks += 1
            for key in weights:
                totals[key] += weights[key]
        epoch_records.append({"epoch": epoch, "updates": update_count, "statuses": dict(statuses),
                              "weights": {k: rational(v) for k, v in weights.items()}})
        if progress:
            progress(epoch_records[-1])
    averaged = {k: quantize(v/ticks) for k, v in totals.items()}
    model = {"version": VERSION, "feature_version": FEATURE_VERSION,
             "use_contract_sha256": content_hash(contract), "parent_recall_sha256": parent_sha,
             "weights": {k: rational(v) for k, v in averaged.items()},
             "weights_origin": "averaged_structured_perceptron_train_only",
             "training_performed": True, "purpose": "local_noncommercial_research",
             "restrictions": {k: False for k in RESTRICTIONS},
             "configuration": {"epochs": epochs, "learning_rate": rational(rate),
                               "weight_bound": rational(weight_bound), "weight_precision": PRECISION,
                               "transition_budget": transition_budget, "order": "family_then_sample_id",
                               "dev_checkpoint_selection": False},
             "training_contexts_seen": len(examples), "reachable_complete_training_contexts": len(eligible),
             "averaging_ticks": ticks, "epochs": epoch_records,
             "training_eligibility": eligibility, "updates": updates,
             "confidence_calibrated": False, "gold_candidates_injected": False}
    model["model_id"] = "learned_"+content_hash(model)[:24]
    return model


def infer(problem, model, *, transition_budget=2_000_000):
    """No reference/annotation argument. Local research use ONLY."""
    if (model.get("version") != VERSION or model.get("feature_version") != FEATURE_VERSION
            or model.get("purpose") != "local_noncommercial_research"
            or model.get("training_performed") is not True
            or any(model.get("restrictions", {}).get(k) is not False for k in RESTRICTIONS)):
        raise ValueError("unsupported_or_unrestricted_model")
    body = {k: v for k, v in model.items() if k != "model_id"}
    if model.get("model_id") != "learned_"+content_hash(body)[:24]:
        raise ValueError("learned_model_content_mismatch")
    weights = weights_contract({k: fraction(v) for k, v in model["weights"].items()})
    result = decode(problem, weights, transition_budget=transition_budget)
    if result["selected"] is not None:
        result["status"] = "selected_learned_research_hypothesis"
        result["selected"]["model_ref"] = model["model_id"]
        result["selected"]["model_feature_version"] = FEATURE_VERSION
        result["selected"]["purpose"] = "local_noncommercial_research"
        result["selected"]["restrictions"] = dict(model["restrictions"])
    return result
