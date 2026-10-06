"""Recompute approved historical Train contrasts without using Dev labels."""
from . import harmony_recipe_balance_training as parent
from . import harmony_member_timing as scoring
from . import harmony_member_timing_learning as learning
from .harmony_temporal_scoring import bind

PINS, PARENT_SHA = parent.PINS, parent.PARENT_SHA
SUPPORT_MODEL, SUPPORT_MODEL_SHA = parent.SUPPORT_MODEL, parent.SUPPORT_MODEL_SHA
old_learning, prior = parent.old_learning, parent.prior


def contrast_row(item, entry, graph, ev, args, fixed, cells):
    base = scoring.support.Scorer(graph, ev, fixed, build_index=False, **args)
    checked = prior.contrast_row(item, entry, graph, ev, args, base, cells)
    scorer = scoring.Scorer(graph, ev, fixed | {scoring.FEATURE: scoring.F()}, build_index=False, **args)
    negative, na = scorer.path_features(item['negative_ids'])
    target, ta = scorer.path_features(item['target_ids'])
    available = na[scoring.FEATURE] and ta[scoring.FEATURE]
    return item | {'entry': entry, 'feature_delta': {scoring.FEATURE: scoring.support.q(negative[scoring.FEATURE]-target[scoring.FEATURE])},
        'feature_available': {scoring.FEATURE: available}, 'loss': checked['loss'],
        'negative_features': {scoring.FEATURE: scoring.support.q(negative[scoring.FEATURE])},
        'target_features': {scoring.FEATURE: scoring.support.q(target[scoring.FEATURE])},
        'frozen_support_feature_availability': checked['feature_available'],
        'base_cost_gap': scoring.support.q(base.score_path(item['negative_ids'])-base.score_path(item['target_ids'])),
        'base_score': 'step67_frozen_train_calibrated_with_nullable_support_observations'}


def prepare(read, save, output):
    # Reuse SHA-bound source/target/loss reconstruction, not the rejected
    # recipe feature or coefficient. Save the complete dataset, including
    # unavailable rows, and fit only the explicitly available comparisons.
    def fit_available(rows, contract, manifest, parent_sha):
        return learning.fit([r for r in rows if r['feature_available'][scoring.FEATURE]], contract, manifest, parent_sha)
    class Learner:
        fit = staticmethod(fit_available)
    model, use, manifest, dataset, fixed = bind(parent.prepare, {
        'contrast_row': contrast_row, 'learning': Learner})(read, save, output)
    # Parent returns truthful source counts but calls all stored rows eligible.
    # Correct that descriptor before finalizing both SHA-bound artifacts.
    dataset['counts']['stored_contrasts'] = len(dataset['rows'])
    dataset['counts']['unavailable_timing_contrasts'] = sum(not r['feature_available'][scoring.FEATURE] for r in dataset['rows'])
    dataset['counts']['eligible_contrasts'] = model['training_contrasts']
    dataset['counts']['eligible_samples'] = model['training_samples']
    dataset['feature_version'] = scoring.FEATURE_VERSION
    dataset['prepared_factor_is_probability'] = False
    save(output/'training-contrasts.json.gz', dataset, True)
    model['training_dataset_content_sha256'] = parent.content_hash(dataset)
    model['negative_pool'] = 'deduplicated_sealed_J2f_updates_and_collisions_available_timing_only'
    save(output/'model.json', model)
    return model, use, manifest, dataset, fixed
