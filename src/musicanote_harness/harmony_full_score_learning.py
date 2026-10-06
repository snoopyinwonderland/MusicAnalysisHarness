"""Train-only masked-gradient calibration on the frozen current-winner pool.

NOT online/loss-augmented training. Unknown feature parts retain the old
score's omission policy, but never drive a gradient in this comparison.
"""
from collections import Counter
from fractions import Fraction as F

from . import harmony_full_score as s
from .harmony_structured_learning import validate_use_contract, content_hash, quantize, RESTRICTIONS, PRECISION
from .harmony_scored_decoder import feature_cost

VERSION = 'harmony-full-score-learning-0.1.0'


def fit(rows, initial, contract, manifest, parent_sha, *, epochs=5, update_cap=F(1, 10)):
    initial = s.coefficients(initial)
    approvals = validate_use_contract(contract, manifest, parent_sha)
    if type(epochs) is not int or not 1 <= epochs <= 20 or type(update_cap) is not F or not 0 < update_cap <= 1:
        raise ValueError('invalid_full_score_learning_configuration')
    rows = sorted(rows, key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    seen = set()
    for r in rows:
        e = r['entry']; key = e['manifest_entry_id']
        if e.get('split') != 'train' or key not in approvals: raise ValueError('unapproved_or_nontrain_full_score_contrast')
        if approvals[key]['manifest_entry_sha256'] != content_hash(e): raise ValueError('full_score_entry_binding_mismatch')
        if r['contrast_id'] in seen: raise ValueError('duplicate_full_score_contrast')
        seen.add(r['contrast_id'])
        if (set(r['feature_delta']) != set(s.FEATURES) or set(r['feature_available']) != set(s.FEATURES)
                or any(type(v) is not bool for v in r['feature_available'].values())):
            raise ValueError('invalid_full_score_feature_contract')
        if s.f(r['loss']) <= 0: raise ValueError('nonpositive_full_score_loss')
        if feature_cost({k: s.f(v) for k, v in r['feature_delta'].items()}, initial) != s.f(r['initial_score_gap']):
            raise ValueError('full_score_initial_gap_mismatch')
    if not rows: raise ValueError('no_full_score_contrasts')
    weights = dict(initial); totals = dict.fromkeys(s.FEATURES, F()); ticks = 0
    updates, history = [], []
    for epoch in range(1, epochs+1):
        counts = Counter()
        for r in rows:
            delta = {k: s.f(v) for k, v in r['feature_delta'].items()}
            gradient = {k: delta[k] if r['feature_available'][k] and k in s.TRAINABLE else F() for k in s.FEATURES}
            before = s.f(r['loss'])-feature_cost(delta, weights)
            norm = sum((v*v for v in gradient.values()), F())
            if before <= 0: counts['margin_satisfied'] += 1
            elif norm == 0: counts['known_feature_collision'] += 1
            else:
                tau = min(update_cap, before/norm)
                raw = {k: weights[k]+tau*gradient[k] for k in s.FEATURES}
                new = s.coefficients({k: quantize(max(s.bounds(k)[0], min(s.bounds(k)[1], v))) for k, v in raw.items()})
                counts['updated' if new != weights else 'bounded_no_change'] += 1
                after = s.f(r['loss'])-feature_cost(delta, new)
                if new != weights:
                    updates.append({'epoch': epoch, 'contrast_id': r['contrast_id'], 'before': s.q(before),
                        'after': s.q(after), 'tau': s.q(tau),
                        'gradient': {k: s.q(v) for k, v in gradient.items()},
                        'weights': {k: s.q(v) for k, v in new.items()}})
                weights = new
            ticks += 1
            for k, v in weights.items(): totals[k] += v
        history.append({'epoch': epoch, 'statuses': dict(counts), 'weights': {k: s.q(v) for k, v in weights.items()}})
    averaged = s.coefficients({k: quantize(v/ticks) for k, v in totals.items()})
    def violations(w):
        return [max(F(), s.f(r['loss'])-feature_cost({k: s.f(v) for k, v in r['feature_delta'].items()}, w)) for r in rows]
    before, after = violations(initial), violations(averaged)
    model = {'version': VERSION, 'feature_version': s.FEATURE_VERSION,
        'initial_weights': {k: s.q(v) for k, v in initial.items()}, 'weights': {k: s.q(v) for k, v in averaged.items()},
        'configuration': {'epochs': epochs, 'update_cap': s.q(update_cap), 'precision': PRECISION,
            'bounds': {k: [s.q(v) for v in s.bounds(k)] for k in s.FEATURES},
            'fixed': s.FIXED, 'trainable': s.TRAINABLE, 'gradient_policy': 'both_paths_available_only',
            'same_pool_each_epoch': True, 'dev_checkpoint_selection': False},
        'training_contrasts': len(rows), 'training_samples': len({r['sample_id'] for r in rows}),
        'training_families': sorted({r['entry']['work_family_id'] for r in rows}),
        'margin_violation_sum_before': s.q(sum(before, F())), 'margin_violation_sum_after': s.q(sum(after, F())),
        'margin_worse_pairs': sum(a > b for a, b in zip(after, before)), 'epochs': history, 'updates': updates,
        'purpose': 'local_noncommercial_research', 'restrictions': {k: False for k in RESTRICTIONS},
        'use_contract_sha256': content_hash(contract), 'parent_recall_sha256': parent_sha,
        'training_reference_labels_used': True, 'dev_labels_used': False,
        'fresh_adversary_search_during_fit': False, 'pool_complete': False,
        'source_labels_used_at_inference': False, 'production_deployment': False, 'confidence_calibrated': False}
    model['model_id'] = 'full_score_'+content_hash(model)[:24]
    return model


def model_weights(model, initial, contract, manifest, parent_sha):
    validate_use_contract(contract, manifest, parent_sha)
    body = {k: v for k, v in model.items() if k != 'model_id'}
    if (model.get('version') != VERSION or model.get('feature_version') != s.FEATURE_VERSION
            or model.get('model_id') != 'full_score_'+content_hash(body)[:24]
            or model.get('initial_weights') != {k: s.q(v) for k, v in s.coefficients(initial).items()}
            or model.get('use_contract_sha256') != content_hash(contract) or model.get('parent_recall_sha256') != parent_sha
            or model.get('purpose') != 'local_noncommercial_research'
            or model.get('restrictions') != {k: False for k in RESTRICTIONS}
            or model.get('dev_labels_used') is not False or model.get('source_labels_used_at_inference') is not False
            or model.get('production_deployment') is not False):
        raise ValueError('invalid_full_score_model_contract')
    return s.coefficients({k: s.f(v) for k, v in model['weights'].items()})
