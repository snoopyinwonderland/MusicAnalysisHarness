"""Train-only exact adversary for the existing 26-feature, run-aware score.

Minimize ordinary cost minus reference time/boundary loss on the ORIGINAL
graph. Loss never enters Scorer.decode or analysis export. Same-signature
raw partitions still share a union run, but can miss a reference boundary.
"""
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F
from math import lcm

from . import harmony_full_score as s
from .harmony_exact_frontier import canonical_edges, pareto
from .harmony_functional_scoring import dominant_pairs, shapes, six_four_surface
from .harmony_margin_learning import path_loss
from .harmony_temporal_scoring import resolution_features

VERSION = 'harmony-full-score-adversary-0.1.0'


def decode(sc, loss, *, transition_budget=s.fresh.BUDGET):
    """TRAIN ONLY: exact argmin(cost - loss), NOT an inference prediction.

    Endpoint + raw-edge count + current run start + spelled signature is a
    sufficient state. Future run replacement and loss increments are identical
    for equal states. Existing Pareto/edge-equivalence reductions remain exact.
    The winner is independently reconstructed with the ordinary score.
    """
    graph, ev, weights = sc.problem, sc.ev, sc.weights
    if type(transition_budget) is not int or transition_budget <= 0:
        raise ValueError('invalid_transition_budget')
    stats = {'states_expanded': 0, 'peak_endpoint_states': 0,
        'pareto_states_removed': 0, 'unreachable_states_removed': 0,
        'cap_infeasible_arcs_skipped': 0, 'run_cost_evaluations': 0,
        'pair_cost_evaluations': 0, 'beam_pruning': False,
        'operation_unit': 'feasible_state_raw_edge_comparison',
        'ordinary_batched_operation_unit_is_different': True}
    def result(status, selected, transitions, exact):
        return {'version': VERSION, 'status': status, 'selected': selected,
            'transitions': transitions, 'exact_optimum_under_declared_score': exact,
            'search_diagnostics': stats, 'training_reference_labels_used': True,
            'target_only': True, 'analysis_export_allowed': False,
            'production_modified': False, 'candidate_policy_changed': False}
    if graph.status != 'ready': return result(graph.status, None, 0, False)
    if (len(graph.points) < 2 or any(a >= b for a, b in zip(graph.points, graph.points[1:]))
            or graph.total_note_time <= 0 or type(graph.max_segments) is not int or graph.max_segments <= 0):
        raise ValueError('invalid_frontier_problem')
    ids = {e.group_id for e in graph.edges}
    if (loss.start != graph.points[0] or loss.end != graph.points[-1]
            or set(loss.edge_time_error) != ids or set(loss.edge_internal_missed) != ids
            or type(loss.boundary_weight) is not F or loss.boundary_weight < 0
            or type(loss.boundary_normalizer) is not int or loss.boundary_normalizer <= 0
            or any(type(v) is not F or v < 0 for v in loss.edge_time_error.values())
            or any(type(v) is not int or v < 0 for v in loss.edge_internal_missed.values())
            or any(not loss.start < b < loss.end for b in loss.boundaries)):
        raise ValueError('training_loss_problem_mismatch')
    edges, equivalents = canonical_edges(graph)
    # Score-identical raw arcs must also be loss-identical for this reduction.
    for r in equivalents:
        rep = r['representative_group_id']
        if any((loss.edge_time_error[i], loss.edge_internal_missed[i]) !=
               (loss.edge_time_error[rep], loss.edge_internal_missed[rep])
               for i in r['equivalent_group_ids']):
            raise ValueError('edge_equivalence_training_loss_mismatch')
    stats.update(original_edges=len(graph.edges), representative_edges=len(edges),
                 equivalence_receipts=equivalents)
    # Preserve the original exact integer score scale and its changing-meter
    # enlargement. Add loss denominators only; never round a time or score.
    source = ev.source; scale_lcm = sc.chosen.__globals__['lcm']
    times = (*graph.points, *(t for e in source.events for t in (e.start, e.end)), *source._measure_times)
    time_scale = scale_lcm(*(t.denominator for t in times))
    mult = scale_lcm(*range(1, max(6, 2*max((len(e.signature[1]) for e in edges), default=0), len(source.events))+1))
    loss_scale = lcm(loss.boundary_normalizer*loss.boundary_weight.denominator,
                     *(loss.emission(e).denominator for e in edges))
    scale = (2*time_scale*graph.total_note_time.numerator*(graph.points[-1]-graph.points[0]).numerator
             *scale_lcm(*(v.denominator for v in weights.values()))*mult*loss_scale)
    def units(value):
        exact = value*scale
        if exact.denominator != 1: raise ValueError('adversary_score_scale_not_exact')
        return exact.numerator
    runs, pairs, transitions = {}, {}, {}
    def run(a, b, sig):
        key = a, b, sig
        if key not in runs:
            values = s.applicability(sc.source_scorer.base_run(graph, source, graph.points[a], graph.points[b], sig)[0])
            values = values | sc.source_scorer.member_features(graph, source, graph.points[a], graph.points[b], sig)[0]
            cost = s.feature_cost(values, weights)+weights['functional_role_complexity']*int(six_four_surface(sig) is not None)
            runs[key] = units(cost); stats['run_cost_evaluations'] += 1
        return runs[key]
    def pair(a, b, edge, previous):
        if not (six_four_surface(previous) and previous[0] == edge.signature[0]
                and any(q in ('M', 'Mm7') for q in shapes(edge.signature))) and not dominant_pairs(previous, edge.signature):
            return 0
        key = a, b, previous, edge.signature
        if key not in pairs:
            values = resolution_features(ev, graph.points[a], graph.points[b], edge.end, previous, edge.signature)[0]
            pairs[key] = units(s.feature_cost(values, weights)); stats['pair_cost_evaluations'] += 1
        return pairs[key]
    outgoing = defaultdict(list); by_id = {e.group_id: e for e in edges}
    for e in edges: outgoing[e.start_index].append(e)
    remaining = [graph.max_segments+1]*len(graph.points); remaining[-1] = 0
    for i in range(len(graph.points)-2, -1, -1):
        remaining[i] = min((1+remaining[e.end_index] for e in outgoing[i]), default=graph.max_segments+1)
    emissions = {e.group_id: units(weights['blocker_exposure']*e.features.get('blocker_exposure', F())-loss.emission(e)) for e in edges}
    states = [dict() for _ in graph.points]; states[0][0, None, None] = (0, ())
    visited = 0
    for index in range(len(states)-1):
        current = states[index]; stats['peak_endpoint_states'] = max(stats['peak_endpoint_states'], len(current))
        feasible = {k: v for k, v in current.items() if k[0]+remaining[index] <= graph.max_segments}
        stats['unreachable_states_removed'] += len(current)-len(feasible)
        current, removed = pareto(feasible); stats['pareto_states_removed'] += removed
        states[index] = {}; stats['states_expanded'] += len(current)
        for (count, a, previous), (cost, path) in current.items():
            for e in outgoing[index]:
                if count+1+remaining[e.end_index] > graph.max_segments:
                    stats['cap_infeasible_arcs_skipped'] += 1; continue
                if visited >= transition_budget:
                    return result('transition_budget_abstention', None, visited, False)
                visited += 1
                same = previous == e.signature; left = a if same else index
                increment = run(left, e.end_index, e.signature)+emissions[e.group_id]
                # Loss on EVERY raw onset includes a missed true boundary when
                # the signature stays the same. Musical transition cost does not.
                increment -= units(loss.transition(previous, e))
                if same: increment -= run(a, index, previous)
                else:
                    key = previous, e.signature, e.attack_spellings
                    if key not in transitions:
                        transitions[key] = units(s.feature_cost(s.transition(previous, e), weights))
                    increment += transitions[key]
                    if previous is not None: increment += pair(a, index, e, previous)
                key = count+1, left, e.signature; candidate = cost+increment, path+(e.group_id,)
                old = states[e.end_index].get(key)
                if old is None or candidate < old: states[e.end_index][key] = candidate
    if not states[-1]: return result('no_complete_path_under_segment_cap', None, visited, True)
    augmented, winner = min(states[-1].values())
    # Original decoder, restricted to this positive complete chain, supplies
    # the full source-linked packet. NO training-loss feature is exported.
    reconstruct = sc.chosen.__globals__['original_decode']
    reconstructed = reconstruct(replace(graph, edges=tuple(by_id[i] for i in winner)), ev,
        transition_budget=max(1, len(winner)))
    selected = reconstructed['selected']
    if selected is None or s.fresh.path_ids(selected) != winner:
        raise ValueError('adversary_winner_reconstruction_mismatch')
    ordinary_cost = sc.score_path(winner)
    details = path_loss(graph, reconstructed, loss)
    if (selected['score_cost'] != s.q(ordinary_cost)
            or F(augmented, scale) != ordinary_cost-s.f(details['total'])):
        raise ValueError('adversary_winner_cost_or_loss_mismatch')
    values, available = sc.path_features(winner)
    selected.update(proposal_id='train_adversary_'+selected['proposal_id'],
        full_score={'observed_feature_sums': {k: s.q(v) for k, v in values.items()},
            'availability': available, 'coefficients': {k: s.q(v) for k, v in weights.items()}},
        source_labels_used_for_selection=True, training_reference_labels_used=True,
        target_only=True, confidence=None, human_validated=False)
    stats['winner_checked_with_original_features_and_path_loss'] = True
    return result('selected_train_only_loss_augmented_path', selected, visited, True) | {
        'ordinary_cost': s.q(ordinary_cost), 'training_loss': details,
        'augmented_cost': s.q(F(augmented, scale))}
