"""Train-only, exact time/boundary loss augmentation and research margin fitting.

The inference decoder and original eleven observable features are unchanged.
Reference-derived loss exists only in the training adversary, never inference.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from .harmony_candidate_recall import fraction, rational
from .harmony_scored_decoder import (
    FEATURE_VERSION, decode, feature_cost, transition, weights_contract,
)
from .harmony_structured_learning import (
    PRECISION, RESTRICTIONS, compatible_problem, content_hash, path_features,
    quantize, validate_use_contract,
)

VERSION = "harmony-margin-learning-0.1.0"
LOSS_VERSION = "normalized-spelled-time-semantic-boundary-0.1.0"


@dataclass(frozen=True)
class TrainingLoss:
    start: Fraction
    end: Fraction
    boundary_weight: Fraction
    boundary_normalizer: int
    boundaries: frozenset
    edge_time_error: dict
    edge_internal_missed: dict

    def emission(self, edge):
        return (self.edge_time_error[edge.group_id]
                + self.boundary_weight*self.edge_internal_missed[edge.group_id]/self.boundary_normalizer)

    def onset_error(self, previous, edge):
        if edge.start == self.start:
            return 0
        change = previous != edge.signature
        return int(change != (edge.start in self.boundaries))

    def transition(self, previous, edge):
        return self.boundary_weight*self.onset_error(previous, edge)/self.boundary_normalizer


def training_loss(problem, cells, boundary_weight=Fraction(1, 4)):
    if type(boundary_weight) is not Fraction or boundary_weight < 0:
        raise ValueError("invalid_boundary_loss_weight")
    # Reuse the strict partition/context/availability check, not its edge filter.
    _, reason = compatible_problem(problem, cells)
    if reason is not None:
        raise ValueError("training_loss_requires_complete_ready_reference:"+reason)
    start, end = problem.points[0], problem.points[-1]
    boundaries = frozenset(a["end"] for a, b in zip(cells, cells[1:])
                           if a["signature"] != b["signature"])
    time_error, missed = {}, {}
    for edge in problem.edges:
        time_error[edge.group_id] = sum((
            max(Fraction(), min(edge.end, c["end"])-max(edge.start, c["start"]))
            for c in cells if c["signature"] != edge.signature), Fraction())/(end-start)
        # Strict interior only. A boundary AT onset belongs to transition loss.
        missed[edge.group_id] = sum(edge.start < x < edge.end for x in boundaries)
    return TrainingLoss(start, end, boundary_weight, max(1, len(boundaries)),
                        boundaries, time_error, missed)


def path_loss(problem, prediction, loss):
    if prediction["selected"] is None:
        raise ValueError("training_path_loss_requires_complete_path")
    by_id = {e.group_id: e for e in problem.edges}
    time_error = Fraction(); boundary_errors = 0; previous = None
    for segment in prediction["selected"]["segments"]:
        edge = by_id[segment["semantic_group_ref"]]
        time_error += loss.edge_time_error[edge.group_id]
        boundary_errors += loss.edge_internal_missed[edge.group_id]+loss.onset_error(previous, edge)
        previous = edge.signature
    boundary_error = Fraction(boundary_errors, loss.boundary_normalizer)
    return {"normalized_time_error": rational(time_error),
            "semantic_boundary_errors": boundary_errors,
            "boundary_normalizer": loss.boundary_normalizer,
            "normalized_boundary_error": rational(boundary_error),
            "total": rational(time_error+loss.boundary_weight*boundary_error)}


def loss_augmented_decode(problem, weights, loss, *, transition_budget=2_000_000):
    """TRAINING ONLY: argmin(w.phi - loss), not an analysis prediction.

    Endpoint, segment count and previous spelled signature are all in state.
    Same-signature partition edges incur no semantic boundary false positives.
    """
    weights = weights_contract(weights)
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    if problem.status != "ready":
        return {"status": problem.status, "selected": None, "transitions": 0,
                "exact_optimum_under_declared_score": False}
    if (loss.start != problem.points[0] or loss.end != problem.points[-1]
            or set(loss.edge_time_error) != {e.group_id for e in problem.edges}):
        raise ValueError("training_loss_problem_mismatch")
    outgoing = [[] for _ in problem.points]
    emissions = {}
    for edge in problem.edges:
        outgoing[edge.start_index].append(edge)
        emissions[edge.group_id] = feature_cost(edge.features, weights)-loss.emission(edge)
    states = [dict() for _ in problem.points]
    states[0][(0, None)] = (Fraction(), ())
    transitions = 0; transition_cache = {}
    for index, current in enumerate(states):
        for (count, previous), (cost, ids) in sorted(current.items(), key=lambda item: repr(item[0])):
            if count >= problem.max_segments:
                continue
            for edge in outgoing[index]:
                transitions += 1
                if transitions > transition_budget:
                    return {"status": "transition_budget_abstention", "selected": None,
                            "transitions": transitions-1, "exact_optimum_under_declared_score": False}
                tkey = previous, edge.signature, edge.attack_spellings, edge.start
                if tkey not in transition_cache:
                    transition_cache[tkey] = (feature_cost(transition(previous, edge), weights)
                                              - loss.transition(previous, edge))
                candidate = cost+emissions[edge.group_id]+transition_cache[tkey], ids+(edge.group_id,)
                key = count+1, edge.signature
                existing = states[edge.end_index].get(key)
                if existing is None or candidate < existing:
                    states[edge.end_index][key] = candidate
    if not states[-1]:
        return {"status": "no_complete_path_under_segment_cap", "selected": None,
                "transitions": transitions, "exact_optimum_under_declared_score": True}
    augmented, ids = min(states[-1].values())
    result = {"status": "selected_training_adversary", "transitions": transitions,
              "exact_optimum_under_declared_score": True,
              "selected": {"segments": [{"semantic_group_ref": gid} for gid in ids]}}
    raw = feature_cost(path_features(problem, result), weights)
    details = path_loss(problem, result, loss)
    if raw-fraction(details["total"]) != augmented:
        raise ValueError("nondecomposable_training_loss")
    result["selected"]["score_cost"] = rational(raw)
    result["training_loss"] = details
    result["augmented_cost"] = rational(augmented)
    return result


def fit(examples, contract, manifest, parent_sha, *, boundary_weight=Fraction(1, 4),
        epochs=5, update_cap=Fraction(1, 10), weight_bound=Fraction(4),
        transition_budget=2_000_000, progress=None):
    """Averaged, capped passive-aggressive latent structured-margin update.

    violation = target_cost - adversary_cost + loss;
    delta = adversary_phi - target_phi; tau=min(cap, violation/||delta||^2).
    Clipping/quantization can leave residual margin; log actual before/after.
    """
    if type(epochs) is not int or not 1 <= epochs <= 20:
        raise ValueError("invalid_learning_configuration")
    for value in (update_cap, weight_bound):
        if type(value) is not Fraction or value <= 0:
            raise ValueError("invalid_learning_configuration")
    if type(boundary_weight) is not Fraction or boundary_weight < 0:
        raise ValueError("invalid_boundary_loss_weight")
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    approvals = validate_use_contract(contract, manifest, parent_sha)
    examples = sorted(examples, key=lambda x: (x.entry["work_family_id"], x.sample_id))
    seen = set()
    for x in examples:
        key = x.entry["manifest_entry_id"]
        if x.entry.get("split") != "train" or key not in approvals:
            raise ValueError("unapproved_or_nontrain_learning_example")
        if approvals[key]["manifest_entry_sha256"] != content_hash(x.entry):
            raise ValueError("training_entry_binding_mismatch")
        if x.sample_id in seen:
            raise ValueError("duplicate_training_sample")
        seen.add(x.sample_id)
    weights = {k: quantize(max(-weight_bound, min(weight_bound, v)))
               for k, v in weights_contract().items()}
    eligibility, eligible = [], []
    for x in examples:
        gold, reason = compatible_problem(x.problem, x.cells)
        if gold is not None:
            check = decode(gold, weights, transition_budget=transition_budget)
            reason = None if check["selected"] else check["status"]
        eligibility.append({"sample_id": x.sample_id, "work_family_id": x.entry["work_family_id"],
                            "eligible": reason is None, "reason": reason})
        if reason is None:
            eligible.append((x, gold, training_loss(x.problem, x.cells, boundary_weight)))
    if not eligible:
        raise ValueError("no_reachable_complete_training_references")
    totals = {k: Fraction() for k in weights}; ticks = 0
    epoch_records, updates, collisions = [], [], []
    for epoch in range(1, epochs+1):
        statuses = Counter(); before_sum = after_sum = Fraction()
        for x, gold, loss in eligible:
            prediction = loss_augmented_decode(x.problem, weights, loss, transition_budget=transition_budget)
            target = decode(gold, weights, transition_budget=transition_budget)
            if prediction["selected"] is None or target["selected"] is None:
                statuses["resource_abstention_no_update"] += 1
            else:
                pred_phi = path_features(x.problem, prediction)
                target_phi = path_features(gold, target)
                delta = {k: pred_phi[k]-target_phi[k] for k in weights}
                loss_value = fraction(prediction["training_loss"]["total"])
                before = loss_value-feature_cost(delta, weights)
                after = before
                norm = sum((v*v for v in delta.values()), Fraction())
                if before <= 0:
                    statuses["margin_satisfied_no_update"] += 1
                elif norm == 0:
                    statuses["feature_collision_positive_margin_no_update"] += 1
                    collisions.append({"epoch": epoch, "sample_id": x.sample_id,
                                       "loss": prediction["training_loss"], "violation": rational(before),
                                       "adversary_group_refs": [s["semantic_group_ref"] for s in prediction["selected"]["segments"]],
                                       "target_group_refs": [s["semantic_group_ref"] for s in target["selected"]["segments"]]})
                else:
                    tau = min(update_cap, before/norm)
                    raw = {k: weights[k]+tau*delta[k] for k in weights}
                    weights = {k: quantize(max(-weight_bound, min(weight_bound, raw[k]))) for k in weights}
                    after = loss_value-feature_cost(delta, weights)
                    statuses["updated"] += 1
                    updates.append({"epoch": epoch, "sample_id": x.sample_id,
                                    "adversary_group_refs": [s["semantic_group_ref"] for s in prediction["selected"]["segments"]],
                                    "training_target_group_refs": [s["semantic_group_ref"] for s in target["selected"]["segments"]],
                                    "feature_delta": {k: rational(v) for k, v in delta.items()},
                                    "loss": prediction["training_loss"], "tau": rational(tau),
                                    "violation_before": rational(before), "same_pair_violation_after": rational(after),
                                    "clipped_weights": [k for k in weights if abs(raw[k]) > weight_bound]})
                before_sum += max(Fraction(), before); after_sum += max(Fraction(), after)
            ticks += 1
            for k in weights:
                totals[k] += weights[k]
        epoch_records.append({"epoch": epoch, "updates": statuses["updated"], "statuses": dict(statuses),
                              "positive_pair_violation_before": rational(before_sum),
                              "positive_same_pair_violation_after": rational(after_sum),
                              "weights": {k: rational(v) for k, v in weights.items()}})
        if progress:
            progress(epoch_records[-1])
    averaged = {k: quantize(v/ticks) for k, v in totals.items()}
    model = {"version": VERSION, "feature_version": FEATURE_VERSION, "loss_version": LOSS_VERSION,
             "use_contract_sha256": content_hash(contract), "parent_recall_sha256": parent_sha,
             "weights": {k: rational(v) for k, v in averaged.items()},
             "weights_origin": "averaged_capped_passive_aggressive_latent_structured_margin_train_only",
             "training_performed": True, "purpose": "local_noncommercial_research",
             "restrictions": {k: False for k in RESTRICTIONS},
             "configuration": {"epochs": epochs, "update_cap": rational(update_cap),
                               "time_loss_weight": rational(Fraction(1)), "boundary_loss_weight": rational(boundary_weight),
                               "boundary_normalizer": "max(1,reference_semantic_boundary_count)",
                               "weight_bound": rational(weight_bound), "weight_precision": PRECISION,
                               "transition_budget": transition_budget, "order": "family_then_sample_id",
                               "dev_checkpoint_selection": False},
             "training_contexts_seen": len(examples), "reachable_complete_training_contexts": len(eligible),
             "averaging_ticks": ticks, "epochs": epoch_records, "training_eligibility": eligibility,
             "updates": updates, "feature_collisions": collisions,
             "confidence_calibrated": False, "gold_candidates_injected": False}
    model["model_id"] = "margin_"+content_hash(model)[:24]
    return model


def infer(problem, model, *, transition_budget=2_000_000):
    """Label-blind ordinary decoder. NO reference or training loss parameter."""
    if (model.get("version") != VERSION or model.get("feature_version") != FEATURE_VERSION
            or model.get("purpose") != "local_noncommercial_research"
            or model.get("training_performed") is not True
            or any(model.get("restrictions", {}).get(k) is not False for k in RESTRICTIONS)):
        raise ValueError("unsupported_or_unrestricted_model")
    body = {k: v for k, v in model.items() if k != "model_id"}
    if model.get("model_id") != "margin_"+content_hash(body)[:24]:
        raise ValueError("margin_model_content_mismatch")
    weights = weights_contract({k: fraction(v) for k, v in model["weights"].items()})
    result = decode(problem, weights, transition_budget=transition_budget)
    if result["selected"] is not None:
        result["status"] = "selected_margin_research_hypothesis"
        result["selected"].update(model_ref=model["model_id"], model_feature_version=FEATURE_VERSION,
                                  purpose="local_noncommercial_research", restrictions=dict(model["restrictions"]))
    return result
