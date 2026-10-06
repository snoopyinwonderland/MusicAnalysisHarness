"""Factor identical future transitions while retaining the exact joint optimum.

At one endpoint, changing to the same spelled signature and actual attack set
has one best predecessor for each raw count, irrespective of the destination
edge's end. Union-run cost and blocker cost are then added for each original
edge. Same-signature extensions still retain their original run start.

The resource budget now counts factored operations, not expanded logical arc
visits. Both counts are reported. This is not a beam or candidate truncation.
"""
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F
from math import lcm

from . import harmony_bounded_recovery as bounded
from .harmony_exact_frontier import RunIndex, canonical_edges, pareto
from .harmony_evidence_scoring import BASE_WEIGHTS, EVIDENCE_WEIGHTS
from .harmony_functional_scoring import (
    PAIR_WEIGHTS, ROLE_COST, decode as original_decode, dominant_pairs,
    pair_features, role_cost, shapes, six_four_surface, supply,
)
from .harmony_scored_decoder import DEFAULT_WEIGHTS, feature_cost, transition
from .harmony_candidate_recall import rational
from .harmony_progression_search import _hash

VERSION = "harmony-batched-frontier-0.1.0"
CONFIG = dict(bounded.CONFIG)


def scoped_functional_evidence(problem, ev):
    """Index only rows capable of intersecting this run/boundary domain.

    Full original spans and source evidence/neighbor rows remain intact.
    Every possible pair boundary is strictly inside [a,b]; a direct link
    outside that domain cannot be consumed by pair_features. Retain carried
    sounds and destinations extending beyond b, without clipping them.
    """
    a, b = problem.points[0], problem.points[-1]
    rows = tuple(r for r in ev.rows if r["start"] < b and a < r["end"])
    links = tuple((p, n) for p, n in ev.links if a < p["end"] == n["start"] < b)
    return replace(ev, rows=rows, links=links, _surface_cache={}, _pair_cache={})


def decode(problem, ev, *, functional_evidence=True, transition_budget=2_000_000):
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError("invalid_transition_budget")
    stats = {"operation_unit": "predecessor_comparison_or_factored_edge_emission_or_same_run_extension",
        "logical_transitions_represented": 0, "pareto_states_removed": 0,
        "cap_infeasible_operations_skipped": 0, "states_expanded": 0, "peak_endpoint_states": 0,
        "run_cost_evaluations": 0, "pair_cost_evaluations": 0, "beam_pruning": False,
        "score_weights_changed": False, "numeric_budget_unchanged_operation_unit_changed": True}
    operations = 0
    def result(status, selected, exact):
        return {"status": status, "selected": selected, "transitions": operations,
            "exact_optimum_under_declared_score": exact, "search_diagnostics": stats}
    if problem.status != "ready": return result(problem.status, None, False)
    if (len(problem.points) < 2 or any(a >= b for a, b in zip(problem.points, problem.points[1:]))
            or problem.total_note_time <= 0 or type(problem.max_segments) is not int or problem.max_segments <= 0):
        raise ValueError("invalid_frontier_problem")
    edges, aliases = canonical_edges(problem)
    stats.update(original_edges=len(problem.edges), representative_edges=len(edges), equivalence_receipts=aliases)
    original_ev = ev; ev = scoped_functional_evidence(problem, ev)
    stats.update(full_functional_rows=len(original_ev.rows), indexed_functional_rows=len(ev.rows),
                 full_direct_links=len(original_ev.links), indexed_direct_links=len(ev.links))
    indexer = RunIndex(problem, ev.source); weights = BASE_WEIGHTS | EVIDENCE_WEIGHTS
    times = (*problem.points, *(t for e in ev.source.events for t in (e.start, e.end)), *ev.source._measure_times)
    mult = lcm(*range(1, max(6, 2*max((len(e.signature[1]) for e in edges), default=0), len(ev.source.events))+1))
    scale = (2*lcm(*(t.denominator for t in times))*problem.total_note_time.numerator
        *(problem.points[-1]-problem.points[0]).numerator
        *lcm(*(v.denominator for v in (*weights.values(), *PAIR_WEIGHTS.values(), ROLE_COST)))*mult)
    def units(value):
        value *= scale
        if value.denominator != 1: raise ValueError("score_scale_not_exact")
        return value.numerator
    runs = {}; pairs = {}; transition_costs = {}; outgoing = defaultdict(list); by_id = {}
    def run(a, b, sig):
        key = a, b, sig
        if key not in runs:
            values, _ = indexer.features(problem.points[a], problem.points[b], sig)
            runs[key] = units(feature_cost(values, weights)+role_cost(sig)); stats["run_cost_evaluations"] += 1
        return runs[key]
    def pair(a, b, e, previous):
        if not (six_four_surface(previous) and previous[0] == e.signature[0]
                and any(q in ("M", "Mm7") for q in shapes(e.signature))) and not dominant_pairs(previous, e.signature): return 0
        key = a, b, previous, e.signature
        if key not in pairs:
            pairs[key] = units(feature_cost(pair_features(ev, problem.points[a], problem.points[b], e.end, previous, e.signature)[0], PAIR_WEIGHTS))
            stats["pair_cost_evaluations"] += 1
        return pairs[key]
    def transition_cost(previous, e):
        key = previous, e.signature, e.attack_spellings
        if key not in transition_costs: transition_costs[key] = units(feature_cost(transition(previous, e), weights))
        return transition_costs[key]
    for e in edges:
        outgoing[e.start_index].append(e); by_id[e.group_id] = e
    remaining = [problem.max_segments+1]*len(problem.points); remaining[-1] = 0
    for i in range(len(problem.points)-2, -1, -1):
        remaining[i] = min((1+remaining[e.end_index] for e in outgoing[i]), default=problem.max_segments+1)
    blockers = {e.group_id: units(DEFAULT_WEIGHTS["blocker_exposure"]*e.features.get("blocker_exposure", F())) for e in edges}
    states = [dict() for _ in problem.points]; states[0][0, None, None] = (0, ())
    def put(end, key, value):
        old = states[end].get(key)
        if old is None or value < old: states[end][key] = value
    for index in range(len(states)-1):
        stats["peak_endpoint_states"] = max(stats["peak_endpoint_states"], len(states[index]))
        feasible = {key: val for key, val in states[index].items() if key[0]+remaining[index] <= problem.max_segments}
        current, n = pareto(feasible); stats["pareto_states_removed"] += n
        stats["states_expanded"] += len(current); states[index] = {}
        groups = defaultdict(list)
        for e in outgoing[index]: groups[e.signature, e.attack_spellings].append(e)
        by_previous = defaultdict(list)
        for key, value in current.items(): by_previous[key[2]].append((key, value))
        for (sig, attacks), group in groups.items():
            prototype = group[0]; shortest = min(remaining[e.end_index] for e in group)
            best = {}; source_counts = defaultdict(int)
            for (count, a, previous), (cost, ids) in current.items():
                if previous == sig: continue
                if count+1+shortest > problem.max_segments:
                    stats["cap_infeasible_operations_skipped"] += 1; continue
                if operations >= transition_budget: return result("transition_budget_abstention", None, False)
                operations += 1; source_counts[count] += 1
                increment = transition_cost(previous, prototype)
                if previous is not None and functional_evidence: increment += pair(a, index, prototype, previous)
                value = cost+increment, ids
                if count not in best or value < best[count]: best[count] = value
            for e in group:
                for count, (cost, ids) in best.items():
                    if count+1+remaining[e.end_index] > problem.max_segments:
                        stats["cap_infeasible_operations_skipped"] += 1; continue
                    if operations >= transition_budget: return result("transition_budget_abstention", None, False)
                    operations += 1; stats["logical_transitions_represented"] += source_counts[count]
                    put(e.end_index, (count+1, index, sig),
                        (cost+run(index, e.end_index, sig)+blockers[e.group_id], ids+(e.group_id,)))
                # Extending an existing run cannot collapse its different starts.
                for (count, a, _), (cost, ids) in by_previous.get(sig, ()):
                    if count+1+remaining[e.end_index] > problem.max_segments:
                        stats["cap_infeasible_operations_skipped"] += 1; continue
                    if operations >= transition_budget: return result("transition_budget_abstention", None, False)
                    operations += 1; stats["logical_transitions_represented"] += 1
                    put(e.end_index, (count+1, a, sig),
                        (cost+run(a, e.end_index, sig)-run(a, index, sig)+blockers[e.group_id], ids+(e.group_id,)))
    if not states[-1]: return result("no_complete_path_under_segment_cap", None, True)
    cost, ids = min(states[-1].values())
    checked = original_decode(replace(problem, edges=tuple(by_id[gid] for gid in ids)), original_ev,
        functional_evidence=functional_evidence, transition_budget=max(1, len(ids)))
    selected = checked["selected"]
    if (selected is None or selected["score_cost"] != rational(F(cost, scale))
            or tuple(s["semantic_group_ref"] for s in selected["segments"]) != ids):
        raise ValueError("indexed_winner_score_or_path_mismatch")
    stats["winner_checked_with_original_features"] = True
    return result(checked["status"], selected, True)


def infer(ir, sample):
    before = _hash(ir); view, grace = bounded.grace_projection(ir)
    permissible = {"nonpositive_duration"} if grace["grace_sounding_events"] else set()
    remaining = sorted(set(sample.get("abstention_reasons", []))-permissible)
    plan = bounded.tile_plan(view, sample["span"])
    if remaining: plan.update(status="sample_scope_abstention", blockers=remaining)
    ev, functional, links = bounded.bound_evidence(view, sample["span"], grace)
    graph, origins = bounded.build_problem(view, plan, ev); graph, receipts = supply(graph, functional)
    chosen = decode(graph, functional, transition_budget=CONFIG["decoder_transition_budget"])
    if _hash(ir) != before or _hash(view) != grace["consumer_view_sha256"]: raise ValueError("frontier_mutated_inputs")
    return {"version": VERSION, "status": chosen["status"], "selected_prediction": chosen["selected"],
        "transitions": chosen["transitions"], "exact_optimum_under_declared_graph": chosen["exact_optimum_under_declared_score"],
        "search_diagnostics": chosen["search_diagnostics"], "grace_projection": grace, "tile_plan": plan,
        "link_withholding": links, "lattice_edge_count": len(graph.edges),
        "functional_candidate_receipts": receipts, "candidate_origin_groups": origins,
        "source_labels_used_at_inference": False, "production_modified": False, "formal_core_modified": False}, graph
