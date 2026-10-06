"""Read-only cost decomposition. No tuning, decoding, or promotion.

Whole-path availability is separate from the known partial sum used by the
sealed scorer. Positive left-minus-right cost means the left path is dearer;
this is not a confidence, probability, or a musical correctness score.
"""
from fractions import Fraction as F
from copy import deepcopy

from . import harmony_full_score as old
from . import harmony_context_joint_decoder as context
from . import harmony_member_role_scoring as role

VERSION = 'harmony-score-balance-ledger-0.1.0'
FEATURES = (*old.FEATURES, *context.FEATURES, *role.FEATURES)
GROUPS = {
    'input_uncertainty': ('unresolved_spelling_exposure', 'blocker_exposure', 'unknown_root'),
    'member_support': ('missing_member_fraction', 'missing_root', 'root_deferred_presence',
                       'absent_third_exposure', 'absent_altered_fifth_exposure',
                       'absent_seventh_exposure', 'late_identifying_member_exposure'),
    'nonmember_explanation': ('nonmember_exposure', 'metric_nonmember_exposure',
                             'lowest_nonmember_exposure', 'conditional_step_ornament_exposure',
                             'durable_nonmember_exposure'),
    'parsimony_and_motion': ('extra_member_complexity', 'harmonic_run_count',
                            'functional_role_complexity', 'unanchored_change',
                            'root_motion_distance', 'member_turnover', 'key_signature_foreign_member'),
    'functional_resolution': ('six_four_surface_and_held_bass', 'six_four_direct_upper_paths',
                              'dominant_family_leading_tone', 'dominant_family_seventh_step'),
    'context_competition': context.FEATURES,
    'member_role_interactions': role.FEATURES,
}
q, f = old.q, old.f


def coefficients(model):
    weights = {k: f(v) for k, v in (model['frozen26'] | model['frozen7'] | model['weights']).items()}
    if set(weights) != set(FEATURES):
        raise ValueError('ledger_model_feature_mismatch')
    old.coefficients({k: weights[k] for k in old.FEATURES})
    context.coefficients({k: weights[k] for k in context.FEATURES})
    role.coefficients({k: weights[k] for k in role.FEATURES})
    return weights


def flatten(receipt, weights):
    """Recompute all 35 term products and all four cost identities."""
    if set(weights) != set(FEATURES):
        raise ValueError('ledger_coefficient_keys')
    grouped = [k for names in GROUPS.values() for k in names]
    if len(grouped) != len(FEATURES) or set(grouped) != set(FEATURES):
        raise ValueError('ledger_group_partition_mismatch')
    terms = {}; subtotals = []
    for name, names in (('legacy', old.FEATURES), ('context', context.FEATURES),
                        ('member_role', role.FEATURES)):
        block = receipt[name]
        values = block['observed_feature_sums'] if name == 'legacy' else block['scored_available_feature_sums']
        if any(set(block[k]) != set(names) for k in ('availability', 'observed_feature_sums', 'term_costs')) or set(values) != set(names):
            raise ValueError('ledger_receipt_feature_keys')
        if name != 'legacy' and ({k: f(v) for k, v in block['coefficients'].items()} != {k: weights[k] for k in names}):
            raise ValueError('ledger_receipt_coefficients_changed')
        subtotal = F()
        for k in names:
            available = block['availability'][k]
            if type(available) is not bool:
                raise ValueError('ledger_invalid_availability')
            observed, scored = f(block['observed_feature_sums'][k]), f(values[k])
            cost = scored*weights[k]
            if cost != f(block['term_costs'][k]):
                raise ValueError('ledger_term_product_mismatch:'+k)
            if available and observed != scored:
                raise ValueError('ledger_known_observed_scored_mismatch:'+k)
            terms[k] = {'known': available, 'value': q(scored) if available else None,
                        'observed_partial_sum': q(observed), 'scored_known_local_sum': q(scored),
                        'coefficient': q(weights[k]), 'cost': q(cost)}
            subtotal += cost
        subtotals.append(subtotal)
    expected = (f(receipt['legacy']['cost']), f(receipt['context_cost']), f(receipt['member_role_cost']))
    if tuple(subtotals) != expected or sum(subtotals[:2], F()) != f(receipt['parent_score_cost']) or sum(subtotals, F()) != f(receipt['cost']):
        raise ValueError('ledger_cost_identity_mismatch')
    return {'cost': receipt['cost'], 'terms': terms,
            'group_costs': {g: q(sum((f(terms[k]['cost']) for k in names), F())) for g, names in GROUPS.items()},
            'whole_unknown_is_not_zero': True}


def reweight_roles(receipt, weights):
    """Reuse immutable source observations, changing only the two role costs.

    The pool was observed with role coefficients zero. Old33 coefficients and
    features stay frozen; this does not re-run any search or construct a path.
    """
    result = deepcopy(receipt); block = result['member_role']
    block['coefficients'] = {k: q(weights[k]) for k in role.FEATURES}
    block['term_costs'] = {k: q(f(block['scored_available_feature_sums'][k])*weights[k]) for k in role.FEATURES}
    result['member_role_cost'] = q(sum((f(v) for v in block['term_costs'].values()), F()))
    result['cost'] = q(f(result['parent_score_cost'])+f(result['member_role_cost']))
    flatten(result, weights)
    return result


def compare(left, right, weights):
    a, b = flatten(left, weights), flatten(right, weights)
    terms = {}
    for k in FEATURES:
        x, y = a['terms'][k], b['terms'][k]; known = x['known'] and y['known']
        delta = f(x['scored_known_local_sum'])-f(y['scored_known_local_sum'])
        terms[k] = {'known_both': known, 'value_delta': q(delta) if known else None,
                    'scored_partial_delta': q(delta), 'cost_delta': q(f(x['cost'])-f(y['cost']))}
    gap = f(a['cost'])-f(b['cost'])
    if sum((f(v['cost_delta']) for v in terms.values()), F()) != gap:
        raise ValueError('ledger_gap_identity_mismatch')
    return {'version': VERSION, 'left_minus_right_cost': q(gap), 'positive_means_left_more_expensive': True,
            'terms': terms, 'group_deltas': {g: q(sum((f(terms[k]['cost_delta']) for k in names), F())) for g, names in GROUPS.items()},
            'candidate_set_complete': False, 'probability': None, 'new_fit_or_search': False}
