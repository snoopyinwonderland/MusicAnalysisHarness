"""Train-only cheapest genuinely wrong path under the frozen 35-term score.

Extend the sealed three-run DP state by ONE monotone error bit. Different
raw IDs/partitions alone are not errors. Reference time/boundary mismatch is
used only to constrain this training miner, never as a score or prediction.
"""
from collections import defaultdict
from fractions import Fraction as F
from time import perf_counter

from . import harmony_context_joint_decoder as base
from .harmony_exact_frontier import canonical_edges
from .harmony_functional_scoring import six_four_surface
from .harmony_temporal_scoring import resolution_features
from .harmony_margin_learning import path_loss

VERSION = 'harmony-train-protection-search-0.1.0'
q, f = base.q, base.f


def check_loss(graph, loss):
    ids = {e.group_id for e in graph.edges}
    if (loss.start != graph.points[0] or loss.end != graph.points[-1]
            or set(loss.edge_time_error) != ids or set(loss.edge_internal_missed) != ids
            or type(loss.boundary_weight) is not F or loss.boundary_weight <= 0
            or type(loss.boundary_normalizer) is not int or loss.boundary_normalizer <= 0
            or any(type(v) is not F or v < 0 for v in loss.edge_time_error.values())
            or any(type(v) is not int or v < 0 for v in loss.edge_internal_missed.values())
            or any(not loss.start < b < loss.end for b in loss.boundaries)):
        raise ValueError('protection_training_loss_mismatch')


def error_pareto(current):
    """Never let a correct history dominate a wrong one (or vice versa)."""
    kept = {}; removed = 0
    for wrong in (False, True):
        subset = {(n, h): v for (n, h, flag), v in current.items() if flag is wrong}
        values, count = base.history_pareto(subset)
        kept.update({(n, h, wrong): v for (n, h), v in values.items()})
        removed += count
    return kept, removed


class WallBudget(Exception):
    pass


def decode(sc, loss, *, transition_budget=base.old_score.fresh.BUDGET,
           wall_seconds=20, timer=perf_counter):
    """Exact argmin ordinary cost among complete POSITIVE semantic-loss paths.

    Endpoint + raw count + last three runs + any-error bit is sufficient.
    All error increments are nonnegative. Final acceptance excludes ALL
    reference-equivalent paths, not just the stored target's raw IDs.
    """
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError('invalid_transition_budget')
    if type(wall_seconds) not in (int, float) or wall_seconds <= 0:
        raise ValueError('invalid_wall_seconds')
    graph, old, source = sc.problem, sc.original, sc.ev.source
    tick = timer(); visited = 0
    stats = dict(states_expanded=0, peak_endpoint_states=0, pareto_states_removed=0,
        unreachable_states_removed=0, cap_infeasible_arcs_skipped=0,
        run_cost_evaluations=0, pair_cost_evaluations=0, context_cost_evaluations=0,
        terminal_flush_evaluations=0, correct_terminal_states_excluded=0,
        beam_pruning=False, operation_unit='feasible_state_raw_edge_comparison')

    def guard():
        if timer()-tick >= wall_seconds:
            raise WallBudget()

    def result(status, ids=None, cost=None, receipt=None, exact=False):
        return dict(version=VERSION, status=status, path_ids=ids, ordinary_cost=cost,
            receipt=receipt, transitions=visited, search_diagnostics=stats,
            exact_optimum_among_positive_loss_paths=exact,
            training_reference_labels_used_for_constraint=True,
            loss_used_as_score=False, analysis_export_allowed=False,
            prediction=False, partial_winner_returned=False, production_modified=False,
            resource_guard=dict(wall_seconds=wall_seconds, elapsed_seconds=timer()-tick,
                transition_budget=transition_budget, raw_segment_cap=graph.max_segments))

    if graph.status != 'ready':
        return result(graph.status)
    if (type(graph.max_segments) is not int or graph.max_segments <= 0
            or graph.total_note_time <= 0 or len(graph.points) < 2
            or any(a >= b for a, b in zip(graph.points, graph.points[1:]))):
        raise ValueError('invalid_protection_problem')
    check_loss(graph, loss)
    edges, equivalent = canonical_edges(graph)
    for group in equivalent:
        rep = group['representative_group_id']
        if any((loss.edge_time_error[x], loss.edge_internal_missed[x]) !=
               (loss.edge_time_error[rep], loss.edge_internal_missed[rep])
               for x in group['equivalent_group_ids']):
            raise ValueError('protection_edge_equivalence_loss_mismatch')
    stats.update(original_edges=len(graph.edges), representative_edges=len(edges),
                 equivalence_receipts=equivalent)
    outgoing = defaultdict(list)
    for e in edges:
        outgoing[e.start_index].append(e)
    remaining = [graph.max_segments+1]*len(graph.points); remaining[-1] = 0
    for i in range(len(graph.points)-2, -1, -1):
        remaining[i] = min((1+remaining[e.end_index] for e in outgoing[i]),
                           default=graph.max_segments+1)
    runs, pairs, changes, contexts = {}, {}, {}, {}

    def run(a, b, sig):
        key = a, b, sig
        if key not in runs:
            guard()
            values = base.old_score.applicability(old.source_scorer.base_run(
                graph, source, graph.points[a], graph.points[b], sig)[0])
            values |= old.source_scorer.member_features(
                graph, source, graph.points[a], graph.points[b], sig)[0]
            runs[key] = (base.old_score.feature_cost(values, old.weights)
                + old.weights['functional_role_complexity']*int(six_four_surface(sig) is not None))
            stats['run_cost_evaluations'] += 1; guard()
        return runs[key]

    def pair(a, b, edge, sig):
        key = a, b, edge.end_index, sig, edge.signature
        if key not in pairs:
            guard()
            pairs[key] = base.old_score.feature_cost(resolution_features(sc.ev,
                graph.points[a], graph.points[b], edge.end, sig, edge.signature)[0], old.weights)
            stats['pair_cost_evaluations'] += 1; guard()
        return pairs[key]

    def change(previous, edge):
        key = previous, edge.signature, edge.attack_spellings
        if key not in changes:
            changes[key] = base.old_score.feature_cost(base.old_score.transition(previous, edge), old.weights)
        return changes[key]

    def context_cost(history, end, index):
        key = history, end, index
        if key not in contexts:
            guard()
            complete = [(graph.points[a], graph.points[history[j+1][0]]
                if j+1 < len(history) else graph.points[end], sig)
                for j, (a, sig) in enumerate(history)]
            contexts[key] = sc.transition_cost(complete, index)
            stats['context_cost_evaluations'] += 1; guard()
        return contexts[key]

    emissions = {e.group_id: old.weights['blocker_exposure']*
        e.features.get('blocker_exposure', F()) for e in edges}
    states = [dict() for _ in graph.points]; states[0][0, (), False] = (F(), ())
    try:
        for index in range(len(states)-1):
            guard(); current = states[index]
            stats['peak_endpoint_states'] = max(stats['peak_endpoint_states'], len(current))
            feasible = {k: v for k, v in current.items() if k[0]+remaining[index] <= graph.max_segments}
            stats['unreachable_states_removed'] += len(current)-len(feasible)
            current, removed = error_pareto(feasible)
            stats['pareto_states_removed'] += removed
            states[index] = {}; stats['states_expanded'] += len(current)
            for (count, history, wrong), (cost, path) in current.items():
                previous = history[-1][1] if history else None
                a = history[-1][0] if history else index
                for e in outgoing[index]:
                    guard()
                    if count+1+remaining[e.end_index] > graph.max_segments:
                        stats['cap_infeasible_arcs_skipped'] += 1; continue
                    if visited >= transition_budget:
                        return result('transition_budget_abstention')
                    visited += 1; same = previous == e.signature; left = a if same else index
                    increment = run(left, e.end_index, e.signature)+emissions[e.group_id]
                    if same:
                        increment -= run(a, index, previous); next_history = history
                    else:
                        increment += change(previous, e)
                        if previous is not None:
                            increment += pair(a, index, e, previous)
                        if len(history) == 3:
                            increment += context_cost(history, index, 1)
                        next_history = (history+((index, e.signature),))[-3:]
                    error = bool(wrong or loss.edge_time_error[e.group_id] > 0
                        or loss.edge_internal_missed[e.group_id] > 0 or loss.onset_error(previous, e))
                    key = count+1, next_history, error
                    candidate = cost+increment, path+(e.group_id,)
                    existing = states[e.end_index].get(key)
                    if existing is None or candidate < existing:
                        states[e.end_index][key] = candidate
        terminal = []
        for (_, history, wrong), (cost, path) in states[-1].items():
            guard()
            if not wrong:
                stats['correct_terminal_states_excluded'] += 1; continue
            extra = sum((context_cost(history, len(graph.points)-1, i)
                         for i in range(1, len(history))), F())
            terminal.append((cost+extra, path)); stats['terminal_flush_evaluations'] += 1
        if not terminal:
            return result('no_positive_loss_path_under_original_cap', exact=True)
        cost, ids = min(terminal)
        guard(); receipt = sc.path_receipt(ids); guard()
        details = path_loss(graph, {'selected': {'segments': [
            {'semantic_group_ref': x} for x in ids]}}, loss)
        if f(receipt['cost']) != cost or f(details['total']) <= 0:
            raise ValueError('protection_independent_cost_or_positive_loss_mismatch')
        stats['winner_checked_with_detailed_35_costs_and_semantic_loss'] = True
        return result('selected_train_only_wrong_competitor', list(ids), q(cost), receipt, True) | {
            'training_loss': details}
    except WallBudget:
        return result('protection_wall_budget_abstention')
