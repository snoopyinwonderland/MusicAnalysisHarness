"""One bounded 28/35-cost Train calibration; no feature, target or Dev search.

Keep input uncertainty and functional-resolution costs fixed. The five other
groups may move at most 1/20 from the sealed Stage83 initial values, within
their original semantic bounds. Unknown whole-path dimensions never update.
"""
from collections import Counter
from fractions import Fraction as F

from . import harmony_score_balance_ledger as ledger
from . import harmony_context_score_learning as use

VERSION = 'harmony-joint-score-balance-learning-0.1.0'
FEATURES = ledger.FEATURES
FIXED = ledger.GROUPS['input_uncertainty']+ledger.GROUPS['functional_resolution']
TRAINABLE = tuple(k for k in FEATURES if k not in FIXED)
RADIUS = F(1, 20)
q, f = ledger.q, ledger.f


def configuration():
    return {'epochs': 3, 'update_cap': q(F(1, 20)), 'trust_radius': q(RADIUS),
        'trainable': list(TRAINABLE), 'fixed': list(FIXED), 'precision': use.PRECISION,
        'initialization': 'sealed_stage83_all_35_costs', 'same_pool_each_epoch': True,
        'gradient_policy': 'trainable_jointly_known_whole_path_dimensions',
        'score_policy': 'same_known_local_partial_terms',
        'averaging': 'every_post_visit_including_no_update',
        'fresh_negative_or_target_search_during_fit': False, 'dev_checkpoint_selection': False}


def coefficients(values):
    if set(values) != set(FEATURES): raise ValueError('joint_balance_weight_keys')
    ledger.old.coefficients({k: values[k] for k in ledger.old.FEATURES})
    ledger.context.coefficients({k: values[k] for k in ledger.context.FEATURES})
    ledger.role.coefficients({k: values[k] for k in ledger.role.FEATURES})
    return dict(values)


def bounds(initial):
    initial = coefficients(initial); result = {}
    for k, v in initial.items():
        low, high = ledger.old.bounds(k) if k in ledger.old.FEATURES else (-F(1, 2), F(1, 2))
        if not low <= v <= high: raise ValueError('joint_balance_initial_outside_semantic_bounds')
        result[k] = (v, v) if k in FIXED else (max(low, v-RADIUS), min(high, v+RADIUS))
    return result


def validate_rows(rows, contract, manifest, parent_sha):
    approved = use.validate_use_contract(contract, manifest, parent_sha); seen = set()
    for r in rows:
        entry = r['entry']; key = entry['manifest_entry_id']
        if entry.get('split') != 'train' or key not in approved or approved[key]['manifest_entry_sha256'] != use.content_hash(entry):
            raise ValueError('joint_balance_nontrain_or_unapproved_entry')
        if r['contrast_id'] in seen: raise ValueError('joint_balance_duplicate_contrast')
        seen.add(r['contrast_id'])
        if any(set(r[k]) != set(FEATURES) for k in ('score_delta', 'gradient_delta', 'available')):
            raise ValueError('joint_balance_vector_keys')
        for k in FEATURES:
            v, g, known = f(r['score_delta'][k]), r['gradient_delta'][k], r['available'][k]
            if type(known) is not bool: raise ValueError('joint_balance_known_mask')
            if known and (g is None or f(g) != v): raise ValueError('joint_balance_known_gradient')
            if not known and g is not None: raise ValueError('joint_balance_unknown_gradient')
        if f(r['loss']) < 0: raise ValueError('joint_balance_negative_loss')
    if not rows: raise ValueError('joint_balance_empty_pool')


def gap(row, weights):
    return sum((f(row['score_delta'][k])*weights[k] for k in FEATURES), F())


def fit(rows, initial, contract, manifest, parent_sha, pool_sha):
    validate_rows(rows, contract, manifest, parent_sha); initial = coefficients(initial); box = bounds(initial)
    rows = sorted(rows, key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    weights = dict(initial); totals = dict.fromkeys(FEATURES, F()); ticks = 0; updates = []; history = []
    for epoch in range(1, 4):
        statuses = Counter()
        for row in rows:
            violation = f(row['loss'])-gap(row, weights)
            gradient = {k: f(row['gradient_delta'][k]) if row['available'][k] else F() for k in TRAINABLE}
            norm = sum((v*v for v in gradient.values()), F())
            if violation <= 0: statuses['margin_satisfied'] += 1
            elif norm == 0: statuses['known_trainable_collision'] += 1
            else:
                tau = min(F(1, 20), violation/norm)
                new = dict(weights)
                for k in TRAINABLE:
                    if not gradient[k]: continue
                    low, high = box[k]
                    new[k] = use.quantize(max(low, min(high, weights[k]+tau*gradient[k])))
                    # Clamp after quantization too; never cross a non-grid endpoint.
                    new[k] = max(low, min(high, new[k]))
                coefficients(new)
                statuses['updated' if new != weights else 'bounded_no_change'] += 1
                if new != weights:
                    updates.append({'epoch': epoch, 'contrast_id': row['contrast_id'], 'tau': q(tau),
                        'before': q(violation), 'after': q(f(row['loss'])-gap(row, new)),
                        'weights': {k: q(v) for k, v in new.items()}})
                weights = new
            ticks += 1
            for k in FEATURES: totals[k] += weights[k]
        history.append({'epoch': epoch, 'statuses': dict(statuses), 'weights': {k: q(v) for k, v in weights.items()}})
    average = {k: initial[k] if k in FIXED or totals[k]/ticks == initial[k]
               else max(box[k][0], min(box[k][1], use.quantize(totals[k]/ticks))) for k in FEATURES}
    coefficients(average)
    before = [max(F(), f(r['loss'])-gap(r, initial)) for r in rows]
    after = [max(F(), f(r['loss'])-gap(r, average)) for r in rows]
    model = {'version': VERSION, 'feature_version': ledger.role.VERSION, 'configuration': configuration(),
        'initial_weights': {k: q(v) for k, v in initial.items()}, 'weights': {k: q(v) for k, v in average.items()},
        'bounds': {k: [q(a), q(b)] for k, (a, b) in box.items()},
        'training_contrasts': len(rows), 'averaging_ticks': ticks, 'epochs': history, 'updates': updates,
        'training_dataset_content_sha256': use.content_hash(rows), 'sealed_pool_report_sha256': pool_sha,
        'margin_sum_before': q(sum(before, F())), 'margin_sum_after': q(sum(after, F())),
        'margin_worse_pairs': sum(a > b for a, b in zip(after, before)), 'margin_is_not_accuracy': True,
        'use_contract_sha256': use.content_hash(contract), 'parent_recall_sha256': parent_sha,
        'purpose': 'local_noncommercial_research', 'restrictions': {k: False for k in use.RESTRICTIONS},
        'training_reference_labels_used': True, 'source_labels_used_at_inference': False,
        'dev_used': False, 'production_deployment': False, 'pool_complete': False, 'confidence_calibrated': False}
    model['model_id'] = 'joint_balance_'+use.content_hash(model)[:24]
    return model


def model_weights(model, initial, contract, manifest, parent_sha, pool_sha):
    use.validate_use_contract(contract, manifest, parent_sha); initial = coefficients(initial); box = bounds(initial)
    body = {k: v for k, v in model.items() if k != 'model_id'}
    if (model.get('version') != VERSION or model.get('feature_version') != ledger.role.VERSION
            or model.get('configuration') != configuration() or model.get('model_id') != 'joint_balance_'+use.content_hash(body)[:24]
            or model.get('initial_weights') != {k: q(v) for k, v in initial.items()}
            or model.get('bounds') != {k: [q(a), q(b)] for k, (a, b) in box.items()}
            or model.get('use_contract_sha256') != use.content_hash(contract)
            or model.get('parent_recall_sha256') != parent_sha or model.get('sealed_pool_report_sha256') != pool_sha
            or model.get('purpose') != 'local_noncommercial_research' or model.get('restrictions') != {k: False for k in use.RESTRICTIONS}
            or model.get('dev_used') is not False or model.get('source_labels_used_at_inference') is not False
            or model.get('production_deployment') is not False):
        raise ValueError('joint_balance_model_contract')
    result = coefficients({k: f(v) for k, v in model['weights'].items()})
    if any(not box[k][0] <= result[k] <= box[k][1] for k in FEATURES): raise ValueError('joint_balance_model_trust_box')
    return result
