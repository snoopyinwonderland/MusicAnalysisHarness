"""Exact capped joint search with delayed three-run context costs.

Research only. No new candidate, label lookup, fitted coefficient, guessed
voice, or production change. Keep the last THREE union runs until the
following run closes; flush the final two transitions at the score end.
Equal last-run-only states are NOT sufficient for this score.
"""
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F

from . import harmony_context_competition_v2 as context_features
from . import harmony_full_score as old_score
from .harmony_exact_frontier import canonical_edges
from .harmony_functional_scoring import six_four_surface
from .harmony_progression_search import _hash
from .harmony_temporal_scoring import resolution_features

VERSION = 'harmony-delayed-context-joint-decoder-0.1.0'
FEATURES = context_features.FEATURES
ZERO = dict.fromkeys(FEATURES, F())
q, f = context_features.q, context_features.f


def coefficients(values):
    result = dict(values)
    if set(result) != set(FEATURES): raise ValueError('invalid_context_coefficient_keys')
    if any(type(v) is not F or not -2 <= v <= 2 for v in result.values()):
        raise ValueError('invalid_exact_context_coefficient')
    return result


def history_pareto(current):
    """Same endpoint/last THREE runs: lower count and cost/ID dominates.

    Positive paths to the same endpoint cannot be proper prefixes. Their ID
    tie ordering survives a common suffix. Pending costs and future raw-run
    replacement depend on the SAME retained history, not an older run.
    No beam, coefficient sign assumption, or cross-history dominance.
    """
    groups = defaultdict(list)
    for (count, history), value in current.items(): groups[history].append((count, value))
    kept = {}; removed = 0
    for history, items in groups.items():
        best = None
        for count, value in sorted(items):
            if best is not None and best <= value: removed += 1
            else:
                kept[count, history] = value
                best = value if best is None else min(best, value)
    return kept, removed


class Scorer:
    def __init__(self, original, extra, *, context=None, **kwargs):
        self.original = original; self.problem = original.problem; self.ev = original.ev
        self.weights = coefficients(extra)
        self.context = context or context_features.Context(self.ev, **kwargs)
        if not isinstance(self.context, context_features.Context) or self.context.ev is not self.ev:
            raise ValueError('context_joint_source_or_version_mismatch')
        self.total = sum((min(e.end, self.problem.points[-1])-max(e.start, self.problem.points[0])
                          for e in self.ev.source.events
                          if e.start < self.problem.points[-1] and self.problem.points[0] < e.end), F())
        self.width = self.problem.points[-1]-self.problem.points[0]
        if self.total <= 0 or self.width <= 0: raise ValueError('empty_context_joint_domain')
        self.transition_cache = {}

    def transition_profile(self, runs, index):
        """A two/three-run LOCAL view, preserving the original GLOBAL scale.

        V2 scalar features do not use the next selected signature as a veto.
        Its start/end still bound the lookahead. All original anchor spans,
        history checks and other-voice uncertainty remain in the receipt.
        """
        if not 1 <= index < len(runs): raise ValueError('invalid_context_transition_index')
        local = tuple(runs[index-1:index+2])
        key = local
        if key not in self.transition_cache:
            profile = self.context.conflict(local, 1, self.total)
            name = 'continuing_left_lowest_coverage'
            value = f(profile['observed_feature_sums'][name])*(local[-1][1]-local[0][0])/self.width
            profile['observed_feature_sums'][name] = q(value)
            profile['features'][name] = q(value) if profile['availability'][name] else None
            self.transition_cache[key] = profile
        return self.transition_cache[key]

    def transition_cost(self, runs, index):
        profile = self.transition_profile(runs, index)
        # An unavailable local term contributes no score, but remains null.
        # The observed partial sum is NOT used as a known value or gradient.
        return sum((self.weights[k]*f(v) for k, v in profile['features'].items() if v is not None), F())

    def path_receipt(self, ids, *, target=False):
        runs = context_features.control.completed_runs(self.problem, ids)
        profiles = [self.transition_profile(runs, i) for i in range(1, len(runs))]
        known = {k: sum((f(p['features'][k]) for p in profiles if p['features'][k] is not None), F()) for k in FEATURES}
        observed = {k: sum((f(p['observed_feature_sums'][k]) for p in profiles), F()) for k in FEATURES}
        availability = {k: all(p['availability'][k] for p in profiles) for k in FEATURES}
        terms = {k: known[k]*self.weights[k] for k in FEATURES}
        old = self.original.receipt(ids, target=target); extra = sum(terms.values(), F())
        return {'version': VERSION, 'existing_path_ids': ids, 'legacy': old,
            'context_feature_version': context_features.VERSION,
            'context_cost': q(extra), 'cost': q(f(old['cost'])+extra),
            'context': {'transitions': profiles, 'coefficients': {k: q(v) for k, v in self.weights.items()},
                'scored_available_feature_sums': {k: q(v) for k, v in known.items()},
                'observed_feature_sums': {k: q(v) for k, v in observed.items()},
                'availability': availability,
                'features': {k: q(known[k]) if availability[k] else None for k in FEATURES},
                'term_costs': {k: q(v) for k, v in terms.items()},
                'normalization_note_time': q(self.total), 'normalization_quarter_width': q(self.width)},
            'unknown_policy': 'omit_unavailable_local_terms_keep_null_and_partial_receipts_not_zero',
            'learning_policy': 'only_jointly_available_complete_path_dimensions',
            'source_labels_used': False, 'target_path_created_using_labels': target,
            'confirmed_nct': False, 'production_modified': False}

    def score_path(self, ids): return f(self.path_receipt(ids)['cost'])

    def decode(self, *, transition_budget=old_score.fresh.BUDGET, force_delayed=False):
        if type(transition_budget) is not int or transition_budget <= 0:
            raise ValueError('invalid_transition_budget')
        if type(force_delayed) is not bool: raise ValueError('invalid_force_delayed')
        # Exactly zero added score can safely use the sealed batched decoder.
        # A forced delayed zero arm is available for independent equivalence.
        if not force_delayed and not any(self.weights.values()):
            result = self.original.decode(transition_budget=transition_budget)
            result['context_joint_contract'] = self.contract('legacy_batched_zero_context')
            if result['selected'] is not None:
                ids = old_score.fresh.path_ids(result['selected'])
                result['selected']['context_score'] = self.path_receipt(ids)
            return result
        return self._delayed(transition_budget)

    @staticmethod
    def contract(backend):
        return {'version': VERSION, 'backend': backend, 'retained_union_runs': 3,
            'pending_transitions_at_end_flushed': True, 'source_labels_used': False,
            'same_original_candidates_and_raw_cap': True, 'beam_pruning': False,
            'new_held_candidate_inserted': False, 'confirmed_nct': False,
            'production_modified': False, 'fitted_weights_claimed': False}

    def _delayed(self, budget):
        graph = self.problem; sc = self.original; source = self.ev.source
        stats = {'states_expanded': 0, 'peak_endpoint_states': 0, 'pareto_states_removed': 0,
            'unreachable_states_removed': 0, 'cap_infeasible_arcs_skipped': 0,
            'run_cost_evaluations': 0, 'pair_cost_evaluations': 0,
            'context_cost_evaluations': 0, 'terminal_flush_evaluations': 0,
            'beam_pruning': False, 'operation_unit': 'feasible_state_raw_edge_comparison',
            'legacy_batched_operation_unit_is_different': True}
        def result(status, selected, visited, exact):
            return {'status': status, 'selected': selected, 'transitions': visited,
                'exact_optimum_under_declared_score': exact, 'search_diagnostics': stats,
                'context_joint_contract': self.contract('delayed_three_run_exact_fraction')}
        if graph.status != 'ready': return result(graph.status, None, 0, False)
        if (type(graph.max_segments) is not int or graph.max_segments <= 0 or graph.total_note_time <= 0
                or len(graph.points) < 2 or any(a >= b for a, b in zip(graph.points, graph.points[1:]))):
            raise ValueError('invalid_context_joint_problem')
        edges, equivalent = canonical_edges(graph)
        stats.update(original_edges=len(graph.edges), representative_edges=len(edges), equivalence_receipts=equivalent)
        outgoing = defaultdict(list); by_id = {e.group_id: e for e in edges}
        for e in edges: outgoing[e.start_index].append(e)
        remaining = [graph.max_segments+1]*len(graph.points); remaining[-1] = 0
        for i in range(len(graph.points)-2, -1, -1):
            remaining[i] = min((1+remaining[e.end_index] for e in outgoing[i]), default=graph.max_segments+1)
        runs, pairs, changes, contexts = {}, {}, {}, {}
        def run(a, b, sig):
            key = a, b, sig
            if key not in runs:
                values = old_score.applicability(sc.source_scorer.base_run(graph, source, graph.points[a], graph.points[b], sig)[0])
                values |= sc.source_scorer.member_features(graph, source, graph.points[a], graph.points[b], sig)[0]
                runs[key] = old_score.feature_cost(values, sc.weights)+sc.weights['functional_role_complexity']*int(six_four_surface(sig) is not None)
                stats['run_cost_evaluations'] += 1
            return runs[key]
        def pair(a, b, edge, sig):
            key = a, b, edge.end_index, sig, edge.signature
            if key not in pairs:
                pairs[key] = old_score.feature_cost(resolution_features(self.ev, graph.points[a], graph.points[b], edge.end, sig, edge.signature)[0], sc.weights)
                stats['pair_cost_evaluations'] += 1
            return pairs[key]
        def change(previous, edge):
            key = previous, edge.signature, edge.attack_spellings
            if key not in changes: changes[key] = old_score.feature_cost(old_score.transition(previous, edge), sc.weights)
            return changes[key]
        def context_cost(history, end, index):
            key = history, end, index
            if key not in contexts:
                complete = [(graph.points[a], graph.points[history[j+1][0]] if j+1 < len(history) else graph.points[end], sig)
                            for j, (a, sig) in enumerate(history)]
                contexts[key] = self.transition_cost(complete, index)
                stats['context_cost_evaluations'] += 1
            return contexts[key]
        emissions = {e.group_id: sc.weights['blocker_exposure']*e.features.get('blocker_exposure', F()) for e in edges}
        states = [dict() for _ in graph.points]; states[0][0, ()] = (F(), ())
        visited = 0
        for index in range(len(states)-1):
            current = states[index]; stats['peak_endpoint_states'] = max(stats['peak_endpoint_states'], len(current))
            feasible = {k: v for k, v in current.items() if k[0]+remaining[index] <= graph.max_segments}
            stats['unreachable_states_removed'] += len(current)-len(feasible)
            current, removed = history_pareto(feasible); stats['pareto_states_removed'] += removed
            states[index] = {}; stats['states_expanded'] += len(current)
            for (count, history), (cost, path) in current.items():
                previous = history[-1][1] if history else None
                a = history[-1][0] if history else index
                for e in outgoing[index]:
                    if count+1+remaining[e.end_index] > graph.max_segments:
                        stats['cap_infeasible_arcs_skipped'] += 1; continue
                    if visited >= budget: return result('transition_budget_abstention', None, visited, False)
                    visited += 1; same = previous == e.signature; left = a if same else index
                    increment = run(left, e.end_index, e.signature)+emissions[e.group_id]
                    if same:
                        increment -= run(a, index, previous); next_history = history
                    else:
                        increment += change(previous, e)
                        if previous is not None: increment += pair(a, index, e, previous)
                        if len(history) == 3: increment += context_cost(history, index, 1)
                        next_history = (history+((index, e.signature),))[-3:]
                    key = count+1, next_history; candidate = cost+increment, path+(e.group_id,)
                    old = states[e.end_index].get(key)
                    if old is None or candidate < old: states[e.end_index][key] = candidate
        if not states[-1]: return result('no_complete_path_under_segment_cap', None, visited, True)
        terminal = []
        for (_, history), (cost, path) in states[-1].items():
            extra = sum((context_cost(history, len(graph.points)-1, i) for i in range(1, len(history))), F())
            terminal.append((cost+extra, path)); stats['terminal_flush_evaluations'] += 1
        cost, ids = min(terminal)
        reconstruct = sc.chosen.__globals__['original_decode']
        restored = reconstruct(replace(graph, edges=tuple(by_id[i] for i in ids)), self.ev,
                               transition_budget=max(1, len(ids)))
        selected = restored['selected']; receipt = self.path_receipt(ids)
        if (selected is None or old_score.fresh.path_ids(selected) != ids
                or selected['score_cost'] != receipt['legacy']['cost'] or cost != f(receipt['cost'])):
            raise ValueError('context_joint_winner_independent_cost_mismatch')
        selected.update(legacy_score_cost=selected['score_cost'], score_cost=receipt['cost'],
            context_score=receipt, proposal_id='context_joint_'+_hash([ids, receipt['cost'], receipt['context']['coefficients']])[:20],
            source_labels_used_for_selection=False, confidence=None, human_validated=False)
        stats['winner_checked_with_original_and_full_path_context'] = True
        return result('selected_context_joint_research_path', selected, visited, True)
