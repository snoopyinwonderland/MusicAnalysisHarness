"""Single fixed-pool calibration of two new interactions; old33 frozen."""
from collections import Counter
from fractions import Fraction as F

from . import harmony_member_role_scoring as score
from . import harmony_context_score_learning as sealed

VERSION = 'harmony-two-member-role-learning-0.1.0'
BOUND = F(1, 2)


def configuration():
    return {'epochs': sealed.EPOCHS, 'update_cap': score.q(sealed.UPDATE_CAP), 'bound': score.q(BOUND),
        'precision': sealed.PRECISION, 'initial_role_weights': {k: score.q(0) for k in score.FEATURES},
        'old26_and_old7_frozen': True, 'gradient_policy': 'jointly_available_whole_path_dimensions',
        'score_policy': 'known_local_terms_only', 'same_pool_each_epoch': True,
        'averaging': 'every_post_visit_including_no_update', 'dev_checkpoint_selection': False}


def validate_rows(rows, contract, manifest, parent_sha):
    approved = sealed.validate_use_contract(contract, manifest, parent_sha); seen = set()
    for r in rows:
        entry = r['entry']; key = entry['manifest_entry_id']
        if entry.get('split') != 'train' or key not in approved or approved[key]['manifest_entry_sha256'] != sealed.content_hash(entry):
            raise ValueError('unapproved_member_role_contrast')
        if r['contrast_id'] in seen:
            raise ValueError('duplicate_member_role_contrast')
        seen.add(r['contrast_id'])
        if any(set(r[k]) != set(score.FEATURES) for k in ('score_delta', 'gradient_delta', 'available')):
            raise ValueError('invalid_member_role_vector_keys')
        for k in score.FEATURES:
            v, g = score.f(r['score_delta'][k]), r['gradient_delta'][k]
            if type(r['available'][k]) is not bool:
                raise ValueError('invalid_member_role_availability')
            if r['available'][k]:
                if g is None or score.f(g) != v:
                    raise ValueError('member_role_gradient_mismatch')
            elif g is not None:
                raise ValueError('member_role_unknown_gradient_not_null')
        if score.f(r['loss']) < 0:
            raise ValueError('negative_member_role_loss')
        score.f(r['frozen33_gap'])
    if not rows:
        raise ValueError('no_member_role_contrasts')


def gap(row, weights):
    return score.f(row['frozen33_gap'])+sum((score.f(row['score_delta'][k])*weights[k] for k in score.FEATURES), F())


def fit(rows, frozen26, frozen7, contract, manifest, parent_sha, pool_sha):
    validate_rows(rows, contract, manifest, parent_sha)
    frozen26 = sealed.s.coefficients(frozen26); frozen7 = score.parent.sealed.coefficients(frozen7)
    rows = sorted(rows, key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    weights, totals = dict(score.ZERO), dict(score.ZERO); ticks = 0; history = []; updates = []
    for epoch in range(1, sealed.EPOCHS+1):
        statuses = Counter()
        for r in rows:
            before = score.f(r['loss'])-gap(r, weights)
            gradient = {k: score.f(v) if v is not None else F() for k, v in r['gradient_delta'].items()}
            norm = sum((v*v for v in gradient.values()), F())
            if before <= 0:
                statuses['margin_satisfied'] += 1
            elif norm == 0:
                statuses['known_feature_collision'] += 1
            else:
                tau = min(sealed.UPDATE_CAP, before/norm)
                new = score.coefficients({k: sealed.quantize(max(-BOUND, min(BOUND, weights[k]+tau*gradient[k]))) for k in weights})
                statuses['updated' if new != weights else 'bounded_no_change'] += 1
                if new != weights:
                    updates.append({'epoch': epoch, 'contrast_id': r['contrast_id'], 'tau': score.q(tau),
                        'before': score.q(before), 'after': score.q(score.f(r['loss'])-gap(r, new)),
                        'weights': {k: score.q(v) for k, v in new.items()}})
                weights = new
            ticks += 1
            for k in weights:
                totals[k] += weights[k]
        history.append({'epoch': epoch, 'statuses': dict(statuses), 'weights': {k: score.q(v) for k, v in weights.items()}})
    average = score.coefficients({k: sealed.quantize(v/ticks) for k, v in totals.items()})
    before = [max(F(), score.f(r['loss'])-gap(r, score.ZERO)) for r in rows]
    after = [max(F(), score.f(r['loss'])-gap(r, average)) for r in rows]
    model = {'version': VERSION, 'feature_version': score.VERSION, 'configuration': configuration(),
        'weights': {k: score.q(v) for k, v in average.items()},
        'frozen26': {k: score.q(v) for k, v in frozen26.items()}, 'frozen7': {k: score.q(v) for k, v in frozen7.items()},
        'training_dataset_content_sha256': sealed.content_hash(rows), 'sealed_pool_sha256': pool_sha,
        'training_contrasts': len(rows), 'averaging_ticks': ticks, 'epochs': history, 'updates': updates,
        'margin_sum_before': score.q(sum(before, F())), 'margin_sum_after': score.q(sum(after, F())),
        'margin_worse_pairs': sum(a > b for a, b in zip(after, before)), 'margin_is_not_accuracy': True,
        'use_contract_sha256': sealed.content_hash(contract), 'parent_recall_sha256': parent_sha,
        'purpose': 'local_noncommercial_research', 'restrictions': {k: False for k in sealed.RESTRICTIONS},
        'training_reference_labels_used': True, 'source_labels_used_at_inference': False,
        'dev_used': False, 'production_deployment': False, 'pool_complete': False, 'confidence_calibrated': False}
    model['model_id'] = 'member_role_'+sealed.content_hash(model)[:24]
    return model


def model_weights(model, frozen26, frozen7, contract, manifest, parent_sha, pool_sha):
    sealed.validate_use_contract(contract, manifest, parent_sha)
    body = {k: v for k, v in model.items() if k != 'model_id'}
    if (model.get('version') != VERSION or model.get('feature_version') != score.VERSION
            or model.get('configuration') != configuration()
            or model.get('model_id') != 'member_role_'+sealed.content_hash(body)[:24]
            or model.get('frozen26') != {k: score.q(v) for k, v in sealed.s.coefficients(frozen26).items()}
            or model.get('frozen7') != {k: score.q(v) for k, v in score.parent.sealed.coefficients(frozen7).items()}
            or model.get('use_contract_sha256') != sealed.content_hash(contract)
            or model.get('parent_recall_sha256') != parent_sha or model.get('sealed_pool_sha256') != pool_sha
            or model.get('restrictions') != {k: False for k in sealed.RESTRICTIONS}
            or model.get('purpose') != 'local_noncommercial_research'
            or model.get('dev_used') is not False or model.get('source_labels_used_at_inference') is not False
            or model.get('production_deployment') is not False):
        raise ValueError('invalid_member_role_model')
    weights = score.coefficients({k: score.f(v) for k, v in model['weights'].items()})
    if any(abs(v) > BOUND for v in weights.values()):
        raise ValueError('member_role_model_outside_trust_box')
    return weights
