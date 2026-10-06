"""Jointly adjustable existing musical costs; no new chord/NCT facts.

Research only. Keep all original candidates, clocks, nullable observations,
same-signature union runs and exact capped joint search. Module globals of
the sealed decoders are never modified.
"""
from fractions import Fraction as F

from . import harmony_fresh_train_negatives as fresh
from .harmony_evidence_scoring import BASE_WEIGHTS, EVIDENCE_WEIGHTS
from .harmony_functional_scoring import PAIR_WEIGHTS, ROLE_COST, six_four_surface
from .harmony_scored_decoder import DEFAULT_WEIGHTS, feature_cost, transition
from .harmony_temporal_scoring import bind, resolution_features, ROOT_WEIGHT

VERSION = 'harmony-full-score-0.1.0'
FEATURE_VERSION = 'existing-run-transition-function-and-support-vector-0.1.0'
BASE = BASE_WEIGHTS | {'root_deferred_presence': ROOT_WEIGHT}
FEATURES = tuple(BASE | EVIDENCE_WEIGHTS | fresh.timing.ZERO | PAIR_WEIGHTS |
                 {'functional_role_complexity': ROLE_COST})
FIXED = ('blocker_exposure', 'unresolved_spelling_exposure')
TRAINABLE = tuple(k for k in FEATURES if k not in FIXED)
q, f = fresh.q, fresh.f


def applicability(observations):
    """A known run with NO nonmembers has zero nonmember-ornament exposure.

This proves an empty domain, not the absence of any musical ornament or a
valid contrapuntal voice. All other unassessed cases remain unavailable.
The score is identical because the old None term also contributed nothing.
"""
    result = dict(observations)
    name = 'conditional_step_ornament_exposure'
    if (result.get(name) is None and result.get('nonmember_exposure') == 0
            and result.get('unresolved_spelling_exposure') == 0):
        result[name] = F()
    return result


def initial_weights(extra):
    return coefficients(BASE | EVIDENCE_WEIGHTS | fresh.timing.coefficients(extra) |
                        PAIR_WEIGHTS | {'functional_role_complexity': ROLE_COST})


def bounds(name):
    if name in FIXED:
        return DEFAULT_WEIGHTS[name], DEFAULT_WEIGHTS[name]
    if name in PAIR_WEIGHTS or name == 'conditional_step_ornament_exposure':
        return F(-2), F()
    if name == 'harmonic_run_count':
        return F(1, 10000), F(1, 4)
    if name not in FEATURES: raise ValueError('unknown_full_score_feature')
    return F(), F(2)


def coefficients(values):
    result = dict(values)
    if set(result) != set(FEATURES): raise ValueError('invalid_full_score_keys')
    for k, v in result.items():
        a, b = bounds(k)
        if type(v) is not F or not a <= v <= b:
            raise ValueError('invalid_full_score_coefficient:'+k)
    return result


class Scorer:
    def __init__(self, problem, ev, weights, **args):
        self.problem, self.ev = problem, ev
        self.weights = coefficients(weights)
        # Reuse exactly the sealed feature definitions and direct backend.
        self.source_scorer = fresh.direct_scorer(problem, ev, fresh.timing.ZERO, **args)
        base = {k: self.weights[k] for k in BASE}
        extra = {k: self.weights[k] for k in (*EVIDENCE_WEIGHTS, *fresh.timing.FEATURES)}
        pairs = {k: self.weights[k] for k in PAIR_WEIGHTS}
        role = self.weights['functional_role_complexity']
        def role_cost(sig): return role if six_four_surface(sig) is not None else F()
        replacements = {'BASE_WEIGHTS': base, 'EVIDENCE_WEIGHTS': extra,
            'PAIR_WEIGHTS': pairs, 'DEFAULT_WEIGHTS': DEFAULT_WEIGHTS,
            'ROLE_COST': role, 'role_cost': role_cost}
        original = self.source_scorer.chosen
        reconstruct = bind(original.__globals__['original_decode'], replacements)
        self.chosen = bind(original, replacements | {'original_decode': reconstruct})

    def path_features(self, ids):
        by_id = {e.group_id: e for e in self.problem.edges}
        if (not ids or len(ids) > self.problem.max_segments or any(i not in by_id for i in ids)):
            raise ValueError('not_complete_existing_full_score_path')
        edges = [by_id[i] for i in ids]
        if (edges[0].start_index != 0 or edges[-1].end_index != len(self.problem.points)-1
                or any(a.end_index != b.start_index for a, b in zip(edges, edges[1:]))):
            raise ValueError('not_complete_existing_full_score_path')
        values = dict.fromkeys(FEATURES, F())
        available = dict.fromkeys(FEATURES, True)
        def add(observations):
            for k, v in observations.items():
                if k not in values: raise ValueError('unexpected_full_score_feature:'+k)
                if v is None: available[k] = False
                else: values[k] += v
        runs = []
        for e in edges:
            values['blocker_exposure'] += e.features.get('blocker_exposure', F())
            if runs and runs[-1][2] == e.signature:
                runs[-1] = runs[-1][0], e.end, e.signature
            else:
                if runs:
                    a, b, sig = runs[-1]
                    add(transition(sig, e))
                    add(resolution_features(self.ev, a, b, e.end, sig, e.signature)[0])
                runs.append((e.start, e.end, e.signature))
        for a, b, sig in runs:
            add(applicability(self.source_scorer.base_run(self.problem, self.ev.source, a, b, sig)[0]))
            add(self.source_scorer.member_features(self.problem, self.ev.source, a, b, sig)[0])
            values['functional_role_complexity'] += int(six_four_surface(sig) is not None)
        return values, available

    def score_path(self, ids):
        # Unavailable portions are omitted by the OLD scoring policy. Values
        # remain observed sums, not a claim that an unknown quantity is zero.
        return feature_cost(self.path_features(ids)[0], self.weights)

    def receipt(self, ids, *, target=False):
        values, availability = self.path_features(ids)
        source = self.source_scorer
        return {'existing_path_ids': ids, 'cost': q(feature_cost(values, self.weights)),
            'observed_feature_sums': {k: q(v) for k, v in values.items()},
            'availability': availability,
            'term_costs': {k: q(v*self.weights[k]) for k, v in values.items()},
            'source_labels_used_to_create_this_path': target,
            'unknown_portions_policy': 'old_score_omits_unknown_not_observed_zero',
            'zero_nonmember_domain_is_known_zero_exposure': True,
            'source_support': [d for a, b, sig in fresh.timing.support.completed_runs(self.problem, ids)
                for d in (source.base_run(self.problem, self.ev.source, a, b, sig)[1] +
                          source.member_features(self.problem, self.ev.source, a, b, sig)[1])]}

    def decode(self, *, transition_budget=fresh.BUDGET):
        result = self.chosen(self.problem, self.ev, transition_budget=transition_budget)
        selected = result['selected']
        if selected is not None:
            ids = fresh.path_ids(selected)
            if q(self.score_path(ids)) != selected['score_cost']:
                raise ValueError('full_score_winner_cost_mismatch')
            values, available = self.path_features(ids)
            selected.update(proposal_id='full_score_'+selected['proposal_id'], feature_version=FEATURE_VERSION,
                full_score={'observed_feature_sums': {k: q(v) for k, v in values.items()},
                    'availability': available, 'coefficients': {k: q(v) for k, v in self.weights.items()}},
                confidence=None, human_validated=False, source_labels_used_for_selection=False)
        result['full_score_contract'] = {'version': VERSION, 'same_original_candidates': True,
            'raw_nonmember_cost_removed': False, 'confirmed_nct': False,
            'source_labels_used': False, 'production_modified': False,
            'unknowns_imputed_as_observed_zero': False}
        result['search_diagnostics']['score_weights_changed'] = True
        return result
