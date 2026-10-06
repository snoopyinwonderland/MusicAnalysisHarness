"""Research-only seven-term calibration; the existing 26 costs stay frozen.

This is a SEALED fixed-pool calibration, not refreshed adversarial learning.
Unknown path dimensions cannot drive gradients. Known local terms may still
contribute a partial score: that accumulator is not an observed unknown=0.
"""
from collections import Counter
from fractions import Fraction as F

from . import harmony_context_joint_decoder as joint
from .harmony_structured_learning import (
    validate_use_contract, content_hash, quantize, RESTRICTIONS, PRECISION,
)

s = joint.old_score
VERSION = 'harmony-context-only-score-learning-0.1.0'
EPOCHS, UPDATE_CAP, BOUND = 3, F(1, 20), F(1, 2)


def configuration():
    return {'epochs': EPOCHS, 'update_cap': s.q(UPDATE_CAP), 'bound': s.q(BOUND),
        'precision': PRECISION, 'initial_context_weights': {k: s.q(0) for k in joint.FEATURES},
        'existing_26_frozen': True, 'gradient_policy': 'jointly_available_whole_path_dimensions',
        'score_policy': 'known_local_terms_only_unknown_partial_observations_not_scored',
        'same_pool_each_epoch': True, 'averaging': 'every_post_visit_including_no_update',
        'dev_checkpoint_selection': False}


def validate_rows(rows, contract, manifest, parent_sha):
    approved = validate_use_contract(contract, manifest, parent_sha)
    seen = set()
    for r in rows:
        e = r['entry']; key = e['manifest_entry_id']
        if e.get('split') != 'train' or key not in approved:
            raise ValueError('unapproved_or_nontrain_context_contrast')
        if approved[key]['manifest_entry_sha256'] != content_hash(e):
            raise ValueError('context_entry_binding_mismatch')
        if r['contrast_id'] in seen: raise ValueError('duplicate_context_contrast')
        seen.add(r['contrast_id'])
        if (set(r['score_delta']) != set(joint.FEATURES)
                or set(r['gradient_delta']) != set(joint.FEATURES)
                or set(r['available']) != set(joint.FEATURES)
                or any(type(v) is not bool for v in r['available'].values())):
            raise ValueError('invalid_context_training_vector')
        for k in joint.FEATURES:
            v = s.f(r['score_delta'][k]); g = r['gradient_delta'][k]
            if r['available'][k]:
                if g is None or s.f(g) != v: raise ValueError('context_known_gradient_mismatch')
            elif g is not None: raise ValueError('context_unknown_gradient_must_be_null')
        if s.f(r['loss']) < 0: raise ValueError('negative_context_training_loss')
        s.f(r['legacy_gap'])
    if not rows: raise ValueError('no_context_contrasts')


def gap(row, weights):
    return s.f(row['legacy_gap'])+sum((s.f(row['score_delta'][k])*weights[k] for k in joint.FEATURES), F())


def fit(rows, frozen, contract, manifest, parent_sha, pool_sha):
    frozen = s.coefficients(frozen)
    rows = sorted(rows, key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    validate_rows(rows, contract, manifest, parent_sha)
    weights = dict(joint.ZERO); totals = dict(joint.ZERO); ticks = 0
    updates, history = [], []
    for epoch in range(1, EPOCHS+1):
        statuses = Counter()
        for row in rows:
            before = s.f(row['loss'])-gap(row, weights)
            gradient = {k: s.f(v) if v is not None else F() for k, v in row['gradient_delta'].items()}
            norm = sum((v*v for v in gradient.values()), F())
            if before <= 0: statuses['margin_satisfied'] += 1
            elif norm == 0: statuses['known_feature_collision'] += 1
            else:
                tau = min(UPDATE_CAP, before/norm)
                new = joint.coefficients({k: quantize(max(-BOUND, min(BOUND, weights[k]+tau*gradient[k]))) for k in weights})
                statuses['updated' if new != weights else 'bounded_no_change'] += 1
                if new != weights:
                    updates.append({'epoch': epoch, 'contrast_id': row['contrast_id'], 'before': s.q(before),
                        'after': s.q(s.f(row['loss'])-gap(row, new)), 'tau': s.q(tau),
                        'weights': {k: s.q(v) for k, v in new.items()}})
                weights = new
            ticks += 1
            for k in weights: totals[k] += weights[k]
        history.append({'epoch': epoch, 'statuses': dict(statuses), 'weights': {k: s.q(v) for k, v in weights.items()}})
    average = joint.coefficients({k: quantize(v/ticks) for k, v in totals.items()})
    def violations(w): return [max(F(), s.f(r['loss'])-gap(r, w)) for r in rows]
    before, after = violations(joint.ZERO), violations(average)
    model = {'version': VERSION, 'context_feature_version': joint.context_features.VERSION,
        'decoder_version': joint.VERSION, 'configuration': configuration(),
        'frozen_existing_weights': {k: s.q(v) for k, v in frozen.items()},
        'weights': {k: s.q(v) for k, v in average.items()}, 'training_performed': True,
        'training_contrasts': len(rows), 'training_samples': len({r['sample_id'] for r in rows}),
        'training_families': sorted({r['entry']['work_family_id'] for r in rows}),
        'averaging_ticks': ticks, 'epochs': history, 'updates': updates,
        'training_dataset_content_sha256': content_hash(rows), 'sealed_pool_report_sha256': pool_sha,
        'margin_violation_sum_before': s.q(sum(before, F())), 'margin_violation_sum_after': s.q(sum(after, F())),
        'margin_worse_pairs': sum(a > b for a, b in zip(after, before)),
        'use_contract_sha256': content_hash(contract), 'parent_recall_sha256': parent_sha,
        'purpose': 'local_noncommercial_research', 'restrictions': {k: False for k in RESTRICTIONS},
        'training_reference_labels_used': True, 'source_labels_used_at_inference': False,
        'dev_labels_used': False, 'fresh_adversary_search_during_fit': False,
        'pool_complete': False, 'confidence_calibrated': False, 'production_deployment': False}
    model['model_id'] = 'context_score_'+content_hash(model)[:24]
    return model


def model_weights(model, frozen, contract, manifest, parent_sha, pool_sha):
    validate_use_contract(contract, manifest, parent_sha)
    body = {k: v for k, v in model.items() if k != 'model_id'}
    if (model.get('version') != VERSION or model.get('context_feature_version') != joint.context_features.VERSION
            or model.get('decoder_version') != joint.VERSION or model.get('configuration') != configuration()
            or model.get('model_id') != 'context_score_'+content_hash(body)[:24]
            or model.get('frozen_existing_weights') != {k: s.q(v) for k, v in s.coefficients(frozen).items()}
            or model.get('sealed_pool_report_sha256') != pool_sha or model.get('parent_recall_sha256') != parent_sha
            or model.get('use_contract_sha256') != content_hash(contract)
            or model.get('purpose') != 'local_noncommercial_research'
            or model.get('restrictions') != {k: False for k in RESTRICTIONS}
            or model.get('training_performed') is not True or model.get('dev_labels_used') is not False
            or model.get('source_labels_used_at_inference') is not False or model.get('production_deployment') is not False):
        raise ValueError('invalid_context_learned_model')
    weights = joint.coefficients({k: s.f(v) for k, v in model['weights'].items()})
    if any(abs(v) > BOUND for v in weights.values()): raise ValueError('context_model_outside_trust_box')
    return weights
