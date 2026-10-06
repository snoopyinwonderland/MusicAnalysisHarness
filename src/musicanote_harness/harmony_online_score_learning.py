"""Train-only current-winner refresh with a fixed initial-score trust box.

Ordinary competitors are reselected at every visit, including previously
correct scopes. This is NOT loss-augmented search or independent evaluation.
The full musical score/candidates/nullable evidence remain unchanged.
"""
from collections import Counter
from fractions import Fraction as F

from . import harmony_full_score as s
from .harmony_structured_learning import (validate_use_contract, content_hash,
    quantize, RESTRICTIONS, PRECISION)

VERSION = 'harmony-online-full-score-learning-0.1.0'
EPOCHS = 3
UPDATE_CAP = F(1, 50)
TRUST_FACTOR = F(2)


def trust_bounds(initial):
    initial = s.coefficients(initial)
    result = {}
    for k, v in initial.items():
        lo, hi = s.bounds(k)
        a, b = sorted((v/TRUST_FACTOR, v*TRUST_FACTOR))
        result[k] = (max(lo, a), min(hi, b))
    return result


def project(value, limit):
    lo, hi = limit
    # Quantization must not move a coefficient outside a rational trust box.
    # Snap inwards on the fixed grid, never relax the declared limits.
    grid_lo = F(-((-lo*PRECISION)//1), PRECISION)
    grid_hi = F((hi*PRECISION)//1, PRECISION)
    if grid_lo > grid_hi: raise ValueError('trust_box_has_no_quantized_value')
    return max(grid_lo, min(grid_hi, quantize(value)))


def update(weights, initial, delta, available, loss):
    """Known-both-paths PA update projected to the predeclared trust box."""
    weights, initial = s.coefficients(weights), s.coefficients(initial)
    limits = trust_bounds(initial)
    if any(not limits[k][0] <= v <= limits[k][1] for k, v in weights.items()):
        raise ValueError('online_weights_outside_initial_trust_box')
    if (set(delta) != set(s.FEATURES) or set(available) != set(s.FEATURES)
            or any(type(v) is not F for v in delta.values())
            or any(type(v) is not bool for v in available.values())
            or type(loss) is not F or loss < 0):
        raise ValueError('invalid_online_contrast')
    gradient = {k: delta[k] if available[k] and k in s.TRAINABLE else F() for k in s.FEATURES}
    before = loss-s.feature_cost(delta, weights)
    norm = sum((v*v for v in gradient.values()), F())
    tau = F(); changed = dict(weights)
    if loss == 0:
        status = 'current_winner_reference_agreement'
    elif before <= 0:
        status = 'margin_satisfied'
    elif norm == 0:
        status = 'known_feature_collision'
    else:
        tau = min(UPDATE_CAP, before/norm)
        changed = s.coefficients({k: project(v+tau*gradient[k], limits[k])
            for k, v in weights.items()})
        status = 'updated' if changed != weights else 'trust_box_no_change'
    return changed, {'status': status, 'loss': s.q(loss), 'violation_before': s.q(before),
        'same_pair_violation_after': s.q(loss-s.feature_cost(delta, changed)), 'tau': s.q(tau),
        'gradient': {k: s.q(v) for k, v in gradient.items()}}


def fit(scopes, initial, contract, manifest, parent_sha, visit, *, progress=None):
    """visit(scope, weights, epoch) MUST reselect ordinary and latent target.

    Correct-winner scopes are visited too; if they become wrong under the
    current weights, they generate a fresh contrast. No Dev/epoch selection.
    """
    initial = s.coefficients(initial)
    approvals = validate_use_contract(contract, manifest, parent_sha)
    scopes = sorted(scopes, key=lambda r: (r['work_family_id'], r['sample_id']))
    if not scopes or len({r['sample_id'] for r in scopes}) != len(scopes):
        raise ValueError('empty_or_duplicate_online_training_cohort')
    for r in scopes:
        e = r['entry']; key = e['manifest_entry_id']
        if r.get('split') != 'train' or e.get('split') != 'train' or key not in approvals:
            raise ValueError('unapproved_or_nontrain_online_scope')
        if (approvals[key]['manifest_entry_sha256'] != content_hash(e)
                or r['work_family_id'] != e['work_family_id']):
            raise ValueError('online_training_entry_binding_mismatch')
    weights = dict(initial); totals = dict.fromkeys(s.FEATURES, F()); ticks = 0
    visits = []; history = []
    for epoch in range(1, EPOCHS+1):
        counts = Counter()
        for r in scopes:
            before = dict(weights)
            # Supply a copy so the callback cannot mutate the learning state.
            observed = visit(r, dict(weights), epoch)
            if observed['resource_abstention']:
                receipt = {'status': 'resource_abstention_no_update'}
            else:
                weights, receipt = update(weights, initial,
                    {k: s.f(v) for k, v in observed['feature_delta'].items()},
                    observed['feature_available'], s.f(observed['loss']))
            counts[receipt['status']] += 1
            visits.append({'epoch': epoch, 'sample_id': r['sample_id'],
                'weights_before': {k: s.q(v) for k, v in before.items()},
                'observation': observed, 'update': receipt,
                'weights_after': {k: s.q(v) for k, v in weights.items()}})
            ticks += 1
            for k, v in weights.items(): totals[k] += v
            if progress: progress(epoch, r['sample_id'], receipt['status'], ticks)
        history.append({'epoch': epoch, 'statuses': dict(counts),
            'weights': {k: s.q(v) for k, v in weights.items()}})
    averaged = s.coefficients({k: project(v/ticks, trust_bounds(initial)[k]) for k, v in totals.items()})
    model = {'version': VERSION, 'feature_version': s.FEATURE_VERSION,
        'initial_weights': {k: s.q(v) for k, v in initial.items()},
        'weights': {k: s.q(v) for k, v in averaged.items()},
        'configuration': {'epochs': EPOCHS, 'update_cap': s.q(UPDATE_CAP),
            'initial_trust_factor': s.q(TRUST_FACTOR), 'precision': PRECISION,
            'trust_bounds': {k: [s.q(v) for v in b] for k, b in trust_bounds(initial).items()},
            'fixed': s.FIXED, 'trainable': s.TRAINABLE, 'gradient_policy': 'both_paths_available_only',
            'negative_search': 'fresh_ordinary_current_winner_each_visit',
            'loss_augmented_search': False, 'dev_checkpoint_selection': False,
            'model_selection': 'average_all_visits_not_best_epoch'},
        'training_samples': len(scopes), 'averaging_ticks': ticks,
        'training_families': sorted({r['work_family_id'] for r in scopes}),
        'epochs': history, 'visits': visits,
        'purpose': 'local_noncommercial_research', 'restrictions': {k: False for k in RESTRICTIONS},
        'use_contract_sha256': content_hash(contract), 'parent_recall_sha256': parent_sha,
        'training_reference_labels_used': True, 'source_labels_used_at_inference': False,
        'dev_labels_used': False, 'production_deployment': False, 'confidence_calibrated': False,
        'fresh_current_winner_search_during_fit': True, 'complete_negative_pool': False}
    model['model_id'] = 'online_score_'+content_hash(model)[:24]
    return model


def model_weights(model, initial, contract, manifest, parent_sha):
    validate_use_contract(contract, manifest, parent_sha)
    body = {k: v for k, v in model.items() if k != 'model_id'}
    if (model.get('version') != VERSION or model.get('feature_version') != s.FEATURE_VERSION
            or model.get('model_id') != 'online_score_'+content_hash(body)[:24]
            or model.get('initial_weights') != {k: s.q(v) for k, v in s.coefficients(initial).items()}
            or model.get('use_contract_sha256') != content_hash(contract)
            or model.get('parent_recall_sha256') != parent_sha
            or model.get('purpose') != 'local_noncommercial_research'
            or model.get('restrictions') != {k: False for k in RESTRICTIONS}
            or model.get('dev_labels_used') is not False
            or model.get('source_labels_used_at_inference') is not False
            or model.get('production_deployment') is not False):
        raise ValueError('invalid_online_score_model_contract')
    values = s.coefficients({k: s.f(v) for k, v in model['weights'].items()})
    if any(not trust_bounds(initial)[k][0] <= v <= trust_bounds(initial)[k][1] for k, v in values.items()):
        raise ValueError('model_outside_initial_trust_box')
    return values
