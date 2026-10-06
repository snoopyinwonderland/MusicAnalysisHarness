"""Additional run-local source evidence in the sealed exact joint search.

Private dependency bindings only. Preserve all 35 old costs and reconstruction
checks. New run costs depend on the completed union run, not its raw cuts.
"""
from fractions import Fraction as F
from types import MethodType

from . import harmony_exact_beat_cache as parent
from . import harmony_context_joint_decoder as joint
from . import harmony_full_score as old
from . import harmony_member_release as release
from . import harmony_terminal_context as terminal
from .harmony_joint_nct_scoring import completed_runs
from .harmony_temporal_scoring import bind

VERSION = 'harmony-source-context-joint-score-0.1.0'
FEATURES = (release.FEATURE, *terminal.FEATURES)
ZERO = dict.fromkeys(FEATURES, F())
q, f = terminal.q, joint.f


def coefficients(values):
    result = dict(values)
    if set(result) != set(FEATURES): raise ValueError('invalid_source_context_weight_keys')
    if any(type(v) is not F or not (0 <= v <= 2 if k == release.FEATURE else -2 <= v <= 0)
           for k, v in result.items()): raise ValueError('invalid_source_context_exact_weights')
    return result


class Delegate:
    def __init__(self, wrapped): self.wrapped = wrapped
    def __getattr__(self, name): return getattr(self.wrapped, name)


class CostView(Delegate):
    def __init__(self, weights): super().__init__(old); self.weights = weights
    def feature_cost(self, values, weights):
        base = old.feature_cost({k: v for k, v in values.items() if k not in FEATURES}, weights)
        return base+sum((self.weights[k]*values[k] for k in FEATURES if values.get(k) is not None), F())


class SourceView(Delegate):
    def __init__(self, scorer): super().__init__(scorer.original.source_scorer); self.sc = scorer
    def base_run(self, problem, source, a, b, sig):
        base, details = self.wrapped.base_run(problem, source, a, b, sig)
        return base | self.sc.observe(a, b, sig)[0], details


class Scorer(parent.Scorer):
    def __init__(self, graph, ev, weights, extra=ZERO, **kwargs):
        super().__init__(graph, ev, weights, **kwargs)
        self.extra_weights = coefficients(extra); self.extra_cache = {}
        self.history_gate = kwargs.get('history_gate')
        # The proxy's detailed receipt delegates to the unmodified full26
        # scorer. Reconstruction's original_decode remains the old scorer.
        source = SourceView(self); proxy = Delegate(self.original)
        proxy.source_scorer = source; self.original = proxy
        self._extra_delayed = MethodType(bind(joint.Scorer._delayed,
            {'old_score': CostView(self.extra_weights), 'resolution_features': self.beat_cache.resolution}), self)

    def observe(self, a, b, sig):
        key = a, b, sig
        if key not in self.extra_cache:
            value, evidence = release.observe(self.problem, self.ev, a, b, sig, history_gate=self.history_gate)
            vals, following = terminal.observe(self.problem, self.ev, a, b, sig, history_gate=self.history_gate)
            self.extra_cache[key] = ({release.FEATURE: value} | vals, [evidence, following])
        return self.extra_cache[key]

    def _delayed(self, budget): return self._extra_delayed(budget)

    def path_receipt(self, ids, *, target=False):
        receipt = super().path_receipt(ids, target=target)
        observations = [self.observe(a, b, sig) for a, b, sig in completed_runs(self.problem, ids)]
        known = {k: sum((v[k] for v, _ in observations if v[k] is not None), F()) for k in FEATURES}
        availability = {k: all(v[k] is not None for v, _ in observations) for k in FEATURES}
        terms = {k: known[k]*self.extra_weights[k] for k in FEATURES}; added = sum(terms.values(), F())
        return receipt | dict(source_context_version=VERSION, previous35_cost=receipt['cost'],
            source_context_cost=q(added), cost=q(f(receipt['cost'])+added),
            source_context=dict(features={k: q(known[k]) if availability[k] else None for k in FEATURES},
                scored_available_feature_sums={k: q(v) for k, v in known.items()}, availability=availability,
                coefficients={k: q(v) for k, v in self.extra_weights.items()},
                term_costs={k: q(v) for k, v in terms.items()}, observations=[r for _, rs in observations for r in rs]),
            candidate_graph_changed=False, source_labels_used=False, production_modified=False)

    def decode(self, **kwargs):
        if any(self.extra_weights.values()): kwargs['force_delayed'] = True
        result = super().decode(**kwargs)
        result['source_context_contract'] = dict(version=VERSION, same_sealed_dp_bytecode=True,
            private_run_cost_dependency_added=True, old35_weights_unchanged=True,
            completed_union_runs=True, same_candidates_and_raw_cap=True, source_labels_used=False,
            lookahead_observed_not_a_selected_successor=True, production_modified=False)
        result['exact_beat_cache_contract']['changed_dependency'] = 'run_cost_and_resolution_features.beat_extent'
        if result['selected']:
            result['selected']['proposal_id'] = 'source_context_'+result['selected']['proposal_id']
        return result
