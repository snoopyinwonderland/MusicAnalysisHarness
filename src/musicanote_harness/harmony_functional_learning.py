"""J2f: train-only 20-feature harmonic-run/functional margin learning.

The J2e inventory, observations and feature definitions are reused unchanged.
Only weights change. Reference-derived loss is confined to a training wrapper;
ordinary inference has no reference/loss input. No production-use clearance.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction as F
from math import lcm

from .harmony_candidate_recall import fraction, rational
from .harmony_evidence_scoring import BASE_WEIGHTS, EVIDENCE_WEIGHTS, run_features
from .harmony_functional_scoring import (
    FEATURE_VERSION, PAIR_WEIGHTS, ROLE_COST, dominant_pairs, pair_features, shapes, six_four_surface,
)
from .harmony_margin_learning import LOSS_VERSION, path_loss, training_loss
from .harmony_scored_decoder import feature_cost, transition
from .harmony_structured_learning import (
    PRECISION, RESTRICTIONS, compatible_problem, content_hash, quantize, validate_use_contract,
)

VERSION = "harmony-functional-learning-0.1.0"
INITIAL_WEIGHTS = BASE_WEIGHTS | EVIDENCE_WEIGHTS | PAIR_WEIGHTS | {"functional_role_complexity": ROLE_COST}


@dataclass(frozen=True)
class TrainingExample:
    sample_id: str
    entry: dict
    problem: object
    evidence: object
    cells: tuple


def weights_contract(weights=None):
    result = dict(INITIAL_WEIGHTS if weights is None else weights)
    if set(result) != set(INITIAL_WEIGHTS) or any(type(v) is not F for v in result.values()):
        raise ValueError("invalid_functional_weights_contract")
    return result


def path_features(problem, ev, ids):
    """One vector per completed union run; None is masked, never imputed fact.

    Candidate blockers remain raw-edge additive. Pair evidence is attached to
    the completed LEFT run and selected next onset, not a proposed later label.
    """
    by_id = {e.group_id: e for e in problem.edges}; edges = [by_id[i] for i in ids]
    if (not edges or len(edges) > problem.max_segments or edges[0].start_index != 0
            or edges[-1].end_index != len(problem.points)-1
            or any(a.end_index != b.start_index for a, b in zip(edges, edges[1:]))):
        raise ValueError("not_complete_existing_path")
    values = dict.fromkeys(INITIAL_WEIGHTS, F()); runs = []
    def add(features):
        for k, v in features.items():
            if k in values and v is not None:
                values[k] += v
    for e in edges:
        values["blocker_exposure"] += e.features.get("blocker_exposure", F())
        if runs and runs[-1][2] == e.signature:
            runs[-1] = runs[-1][0], e.end, e.signature
        else:
            if runs:
                a, b, prev = runs[-1]
                add(transition(prev, e)); add(pair_features(ev, a, b, e.end, prev, e.signature)[0])
            runs.append((e.start, e.end, e.signature))
    for a, b, sig in runs:
        add(run_features(problem, ev.source, a, b, sig)[0])
        values["functional_role_complexity"] += int(six_four_surface(sig) is not None)
    return values


def _decode(problem, ev, weights, loss, transition_budget, explain):
    weights = weights_contract(weights)
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    if problem.status != "ready":
        return {"status": problem.status, "selected": None, "transitions": 0,
                "exact_optimum_under_declared_score": False}
    if loss is not None and (loss.start != problem.points[0] or loss.end != problem.points[-1]
            or set(loss.edge_time_error) != {e.group_id for e in problem.edges}
            or set(loss.edge_internal_missed) != {e.group_id for e in problem.edges}):
        raise ValueError("training_loss_problem_mismatch")
    source = ev.source
    times = (*problem.points, *(t for e in source.events for t in (e.start, e.end)), *source._measure_times)
    time_scale = lcm(*(t.denominator for t in times))
    max_members = max((len(e.signature[1]) for e in problem.edges), default=0)
    mult = lcm(*range(1, max(6, 2*max_members, len(source.events))+1))
    scale = (2*time_scale*problem.total_note_time.numerator*(problem.points[-1]-problem.points[0]).numerator
             *lcm(*(v.denominator for v in weights.values()))*mult)
    if loss is not None:
        scale = lcm(scale, *(loss.emission(e).denominator for e in problem.edges),
                    (loss.boundary_weight/loss.boundary_normalizer).denominator)
    def units(v):
        x = v*scale
        if x.denominator != 1:
            raise ValueError("score_scale_not_exact")
        return x.numerator
    runs = {}; pairs = {}; transitions = {}; outgoing = defaultdict(list); by_id = {}
    def run(a, b, sig):
        key = a, b, sig
        if key not in runs:
            values, _ = run_features(problem, source, problem.points[a], problem.points[b], sig)
            runs[key] = units(feature_cost(values, weights)+weights["functional_role_complexity"]*int(six_four_surface(sig) is not None))
        return runs[key]
    def pair(a, b, e, sig):
        if not (six_four_surface(sig) and sig[0] == e.signature[0] and any(q in ("M", "Mm7") for q in shapes(e.signature))) and not dominant_pairs(sig, e.signature):
            return 0
        key = a, b, sig, e.signature
        if key not in pairs:
            values, _ = pair_features(ev, problem.points[a], problem.points[b], e.end, sig, e.signature)
            pairs[key] = units(feature_cost(values, weights))
        return pairs[key]
    for e in problem.edges:
        outgoing[e.start_index].append(e); by_id[e.group_id] = e
    blockers = {e.group_id: units(weights["blocker_exposure"]*e.features.get("blocker_exposure", F())
                                  -(loss.emission(e) if loss else F())) for e in problem.edges}
    states = [dict() for _ in problem.points]; states[0][(0, None, None)] = (0, ())
    count_transitions = 0
    for index, current in enumerate(states):
        for (count, a, previous), (cost, ids) in current.items():
            if count >= problem.max_segments:
                continue
            for e in outgoing[index]:
                count_transitions += 1
                if count_transitions > transition_budget:
                    return {"status": "transition_budget_abstention", "selected": None,
                            "transitions": count_transitions-1, "exact_optimum_under_declared_score": False}
                same = previous == e.signature; left = a if same else index
                increment = run(left, e.end_index, e.signature)+blockers[e.group_id]
                if same:
                    increment -= run(a, index, previous)
                else:
                    key = previous, e.signature, e.attack_spellings
                    if key not in transitions:
                        transitions[key] = units(feature_cost(transition(previous, e), weights))
                    increment += transitions[key]
                    if previous is not None:
                        increment += pair(a, index, e, previous)
                if loss:
                    increment -= units(loss.transition(previous, e))
                key = count+1, left, e.signature; candidate = cost+increment, ids+(e.group_id,)
                old = states[e.end_index].get(key)
                if old is None or candidate < old:
                    states[e.end_index][key] = candidate
    if not states[-1]:
        return {"status": "no_complete_path_under_segment_cap", "selected": None,
                "transitions": count_transitions, "exact_optimum_under_declared_score": True}
    optimized, ids = min(states[-1].values())
    segments = [{"semantic_group_ref": gid, "span": {"start": rational(by_id[gid].start), "end": rational(by_id[gid].end)},
                 "root_spelling": by_id[gid].signature[0], "members": by_id[gid].signature[1],
                 "source_event_ids": by_id[gid].source_event_ids, "candidate_blockers": by_id[gid].blockers,
                 "interpretation": by_id[gid].adapter if gid.startswith("func64_") else None} for gid in ids]
    phi = path_features(problem, ev, ids); raw = feature_cost(phi, weights)
    result = {"status": "selected_training_adversary" if loss else "selected_weighted_research_hypothesis",
              "transitions": count_transitions, "exact_optimum_under_declared_score": True,
              "selected": {"proposal_id": "functional_weighted_"+content_hash([FEATURE_VERSION, ids])[:24],
                           "score_cost": rational(raw), "segments": segments, "feature_version": FEATURE_VERSION,
                           "confidence": None, "source_labels_used_for_selection": loss is not None,
                           "training_reference_labels_used": loss is not None,
                           "human_validated": False, "music_constraints_fully_validated": False}}
    expected = raw
    if loss:
        details = path_loss(problem, result, loss); expected -= fraction(details["total"])
        result.update(training_loss=details, augmented_cost=rational(F(optimized, scale)))
    if expected != F(optimized, scale):
        raise ValueError("nondecomposable_functional_run_score_or_loss")
    if explain:
        result["selected"]["feature_vector"] = {k: rational(v) for k, v in phi.items()}
        run_rows = []; pair_rows = []; union = []
        for gid in ids:
            e = by_id[gid]
            if union and union[-1][2] == e.signature:
                union[-1] = union[-1][0], e.end, e.signature
            else:
                if union:
                    a, b, sig = union[-1]; values, details = pair_features(ev, a, b, e.end, sig, e.signature)
                    if details:
                        pair_rows.append({"boundary": rational(b), "features": {k: rational(v) for k, v in values.items()},
                                          "score_cost": rational(feature_cost(values, weights)), "observations": details,
                                          "secondary_vs_primary": "unresolved_without_local_key", "function_confirmed": False, "cadence": None})
                union.append((e.start, e.end, e.signature))
        for a, b, sig in union:
            values, patterns = run_features(problem, source, a, b, sig); surface = six_four_surface(sig)
            run_rows.append({"span": {"start": rational(a), "end": rational(b)}, "root_spelling": sig[0], "members": sig[1],
                             "features": {k: None if v is None else rational(v) for k, v in values.items()},
                             "availability": {k: v is not None for k, v in values.items()}, "conditional_patterns": patterns,
                             "surface_root_spelling": surface[0] if surface else sig[0],
                             "role_hypothesis": "dominant_origin_six_four" if surface else None})
        result["selected"].update(harmonic_runs=run_rows, functional_pairs=pair_rows)
    return result


def decode(problem, ev, weights=None, *, transition_budget=2_000_000, explain=True):
    """Label-blind exact weighted decoder. No gold or loss argument."""
    return _decode(problem, ev, weights, None, transition_budget, explain)


def loss_augmented_decode(problem, ev, weights, loss, *, transition_budget=2_000_000):
    return _decode(problem, ev, weights, loss, transition_budget, False)


def fit(examples, contract, manifest, parent_sha, *, epochs=5, update_cap=F(1, 10),
        weight_bound=F(4), boundary_weight=F(1, 4), transition_budget=2_000_000, progress=None):
    if type(epochs) is not int or not 1 <= epochs <= 20:
        raise ValueError("invalid_learning_configuration")
    if any(type(v) is not F or v <= 0 for v in (update_cap, weight_bound)):
        raise ValueError("invalid_learning_configuration")
    if type(boundary_weight) is not F or boundary_weight < 0:
        raise ValueError("invalid_boundary_loss_weight")
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    approvals = validate_use_contract(contract, manifest, parent_sha)
    examples = sorted(examples, key=lambda x: (x.entry["work_family_id"], x.sample_id)); seen = set()
    for x in examples:
        key = x.entry["manifest_entry_id"]
        if x.entry.get("split") != "train" or key not in approvals:
            raise ValueError("unapproved_or_nontrain_learning_example")
        if approvals[key]["manifest_entry_sha256"] != content_hash(x.entry):
            raise ValueError("training_entry_binding_mismatch")
        if x.sample_id in seen:
            raise ValueError("duplicate_training_sample")
        seen.add(x.sample_id)
    weights = {k: quantize(max(-weight_bound, min(weight_bound, v))) for k, v in weights_contract().items()}
    eligibility = []; eligible = []
    for index, x in enumerate(examples, 1):
        gold, reason = compatible_problem(x.problem, x.cells)
        if gold is not None:
            result = decode(gold, x.evidence, weights, transition_budget=transition_budget, explain=False)
            reason = None if result["selected"] else result["status"]
        eligibility.append({"sample_id": x.sample_id, "work_family_id": x.entry["work_family_id"], "eligible": reason is None, "reason": reason})
        if reason is None:
            eligible.append((x, gold, training_loss(x.problem, x.cells, boundary_weight)))
        if progress and (index % 20 == 0 or index == len(examples)):
            progress({"phase": "eligibility", "completed": index, "total": len(examples), "reachable": len(eligible)})
    if not eligible:
        raise ValueError("no_reachable_complete_training_references")
    totals = dict.fromkeys(weights, F()); ticks = 0; epoch_records = []; updates = []; collisions = []
    for epoch in range(1, epochs+1):
        statuses = Counter(); before_sum = after_sum = F()
        for index, (x, gold, loss) in enumerate(eligible, 1):
            prediction = loss_augmented_decode(x.problem, x.evidence, weights, loss, transition_budget=transition_budget)
            target = decode(gold, x.evidence, weights, transition_budget=transition_budget, explain=False)
            if prediction["selected"] is None or target["selected"] is None:
                statuses["resource_abstention_no_update"] += 1
            else:
                pids = [s["semantic_group_ref"] for s in prediction["selected"]["segments"]]
                tids = [s["semantic_group_ref"] for s in target["selected"]["segments"]]
                pp = path_features(x.problem, x.evidence, pids); tp = path_features(gold, x.evidence, tids)
                delta = {k: pp[k]-tp[k] for k in weights}; loss_value = fraction(prediction["training_loss"]["total"])
                before = loss_value-feature_cost(delta, weights); after = before
                norm = sum((v*v for v in delta.values()), F())
                if before <= 0:
                    statuses["margin_satisfied_no_update"] += 1
                elif norm == 0:
                    statuses["feature_collision_positive_margin_no_update"] += 1
                    collisions.append({"epoch": epoch, "sample_id": x.sample_id, "loss": prediction["training_loss"],
                                       "violation": rational(before), "adversary_group_refs": pids, "target_group_refs": tids})
                else:
                    tau = min(update_cap, before/norm); raw = {k: weights[k]+tau*delta[k] for k in weights}
                    weights = {k: quantize(max(-weight_bound, min(weight_bound, raw[k]))) for k in weights}
                    after = loss_value-feature_cost(delta, weights); statuses["updated"] += 1
                    updates.append({"epoch": epoch, "sample_id": x.sample_id, "adversary_group_refs": pids,
                                    "training_target_group_refs": tids, "feature_delta": {k: rational(v) for k, v in delta.items()},
                                    "loss": prediction["training_loss"], "tau": rational(tau), "violation_before": rational(before),
                                    "same_pair_violation_after": rational(after), "clipped_weights": [k for k in weights if abs(raw[k]) > weight_bound]})
                before_sum += max(F(), before); after_sum += max(F(), after)
            ticks += 1
            for k in weights:
                totals[k] += weights[k]
            if progress and (index % 20 == 0 or index == len(eligible)):
                progress({"phase": "learning", "epoch": epoch, "epochs": epochs, "completed": index,
                          "total": len(eligible), "statuses": dict(statuses)})
        epoch_records.append({"epoch": epoch, "statuses": dict(statuses), "positive_pair_violation_before": rational(before_sum),
                              "positive_same_pair_violation_after": rational(after_sum), "weights": {k: rational(v) for k, v in weights.items()}})
    averaged = {k: quantize(v/ticks) for k, v in totals.items()}
    model = {"version": VERSION, "feature_version": FEATURE_VERSION, "loss_version": LOSS_VERSION,
             "weights": {k: rational(v) for k, v in averaged.items()}, "initial_weights": {k: rational(v) for k, v in INITIAL_WEIGHTS.items()},
             "weights_origin": "averaged_capped_passive_aggressive_latent_structured_margin_train_only",
             "purpose": "local_noncommercial_research", "restrictions": {k: False for k in RESTRICTIONS},
             "use_contract_sha256": content_hash(contract), "parent_recall_sha256": parent_sha, "training_performed": True,
             "configuration": {"epochs": epochs, "update_cap": rational(update_cap), "weight_bound": rational(weight_bound),
                               "weight_precision": PRECISION, "time_loss_weight": rational(F(1)), "boundary_loss_weight": rational(boundary_weight),
                               "boundary_normalizer": "max(1,reference_semantic_boundary_count)", "transition_budget": transition_budget,
                               "order": "family_then_sample_id", "dev_checkpoint_selection": False},
             "training_contexts_seen": len(examples), "reachable_complete_training_contexts": len(eligible), "averaging_ticks": ticks,
             "training_eligibility": eligibility, "epochs": epoch_records, "updates": updates, "feature_collisions": collisions,
             "confidence_calibrated": False, "gold_candidates_injected": False}
    model["model_id"] = "functional_margin_"+content_hash(model)[:24]
    return model


def infer(problem, ev, model, *, transition_budget=2_000_000):
    if (model.get("version") != VERSION or model.get("feature_version") != FEATURE_VERSION
            or model.get("purpose") != "local_noncommercial_research" or model.get("training_performed") is not True
            or any(model.get("restrictions", {}).get(k) is not False for k in RESTRICTIONS)):
        raise ValueError("unsupported_or_unrestricted_model")
    body = {k: v for k, v in model.items() if k != "model_id"}
    if model.get("model_id") != "functional_margin_"+content_hash(body)[:24]:
        raise ValueError("functional_model_content_mismatch")
    result = decode(problem, ev, weights_contract({k: fraction(v) for k, v in model["weights"].items()}), transition_budget=transition_budget)
    if result["selected"]:
        result["status"] = "selected_functional_learned_research_hypothesis"
        result["selected"].update(model_ref=model["model_id"], purpose=model["purpose"], restrictions=dict(model["restrictions"]))
    return result
