"""Train-only full-score margin updates with refreshed exact adversaries.

Reuse the sealed PA/trust-box/averaging arithmetic, not its ordinary-winner
objective. Missing evidence never contributes a gradient. No Dev checkpoint.
"""
from . import harmony_online_score_learning as online

s = online.s
VERSION = 'harmony-adversarial-full-score-learning-0.1.0'
EPOCHS, UPDATE_CAP, TRUST_FACTOR = online.EPOCHS, online.UPDATE_CAP, online.TRUST_FACTOR
NEGATIVE = 'exact_loss_augmented_train_path'


def validate_observation(value, weights):
    if value['resource_abstention']:
        if 'feature_delta' in value: raise ValueError('partial_adversary_gradient')
        return
    if (value.get('negative_kind') != NEGATIVE
            or value.get('source_labels_used_for_negative_selection') is not True
            or value.get('target_training_reference_labels_used') is not True
            or value.get('analysis_export_allowed') is not False):
        raise ValueError('not_a_training_only_exact_adversary')
    delta = {k: s.f(v) for k, v in value['feature_delta'].items()}
    gap = s.feature_cost(delta, weights)
    if (gap != s.f(value['negative_cost'])-s.f(value['target_cost'])
            or s.f(value['margin_violation']) != s.f(value['loss'])-gap
            or s.f(value['margin_violation']) < 0):
        raise ValueError('adversarial_cost_or_margin_mismatch')


def fit(scopes, initial, contract, manifest, parent_sha, visit, *, progress=None):
    def checked(scope, weights, epoch):
        value = visit(scope, dict(weights), epoch)
        validate_observation(value, weights)
        return value
    # Only update/projection/order/averaging are reused; overwrite all objective
    # identity fields before computing the new model ID.
    model = online.fit(scopes, initial, contract, manifest, parent_sha, checked, progress=progress)
    model.pop('model_id')
    model['version'] = VERSION
    model['configuration'].update(negative_search='fresh_exact_loss_augmented_each_visit',
        loss_augmented_search=True, boundary_loss_weight=s.q(s.fresh.BOUNDARY_WEIGHT),
        max_raw_edges=6, transition_budget=s.fresh.BUDGET,
        adversary_operation_unit='feasible_state_raw_edge_comparison',
        initial_weights_policy='same_pre_online_initial_not_previous_frozen_model')
    model.update(exact_adversary_refreshed_each_visit=True,
        latent_reference_target_refreshed_each_visit=True, analysis_export_allowed=False,
        ordinary_correct_scopes_exempted=False)
    model['model_id'] = 'adversarial_score_'+online.content_hash(model)[:24]
    return model


def model_weights(model, initial, contract, manifest, parent_sha):
    online.validate_use_contract(contract, manifest, parent_sha)
    body = {k: v for k, v in model.items() if k != 'model_id'}
    configuration = model.get('configuration', {})
    if (model.get('version') != VERSION or model.get('feature_version') != s.FEATURE_VERSION
            or model.get('model_id') != 'adversarial_score_'+online.content_hash(body)[:24]
            or model.get('initial_weights') != {k: s.q(v) for k, v in s.coefficients(initial).items()}
            or model.get('use_contract_sha256') != online.content_hash(contract)
            or model.get('parent_recall_sha256') != parent_sha
            or model.get('purpose') != 'local_noncommercial_research'
            or model.get('restrictions') != {k: False for k in online.RESTRICTIONS}
            or any(model.get(k) is not False for k in ('dev_labels_used', 'source_labels_used_at_inference',
                'production_deployment', 'analysis_export_allowed', 'ordinary_correct_scopes_exempted'))
            or model.get('exact_adversary_refreshed_each_visit') is not True
            or model.get('latent_reference_target_refreshed_each_visit') is not True
            or configuration.get('loss_augmented_search') is not True
            or configuration.get('negative_search') != 'fresh_exact_loss_augmented_each_visit'
            or configuration.get('epochs') != EPOCHS
            or configuration.get('update_cap') != s.q(UPDATE_CAP)
            or configuration.get('initial_trust_factor') != s.q(TRUST_FACTOR)
            or configuration.get('model_selection') != 'average_all_visits_not_best_epoch'):
        raise ValueError('invalid_adversarial_score_model_contract')
    values = s.coefficients({k: s.f(v) for k, v in model['weights'].items()})
    if any(not online.trust_bounds(initial)[k][0] <= v <= online.trust_bounds(initial)[k][1] for k, v in values.items()):
        raise ValueError('adversarial_model_outside_initial_trust_box')
    return values
