"""Bounded Train calibration with feasible ordinal protection, not accuracy.

Historical raw losses remain untouched. Already positively ranked mined
competitors need only half their initial gap (capped by raw loss); other rows
retain their original loss margin. Every update is checked against all feasible
protection floors using actual partial costs, never imputed unknown gradients.
"""
from collections import Counter
from fractions import Fraction as F

from . import harmony_joint_balance_learning as base

VERSION = 'harmony-ordinal-protection-learning-0.1.0'
FEATURES, TRAINABLE, FIXED = base.FEATURES, base.TRAINABLE, base.FIXED
q, f, use = base.q, base.f, base.use
MAX_HALVINGS = 20


def configuration():
    return base.configuration() | dict(
        protection_floor='min(raw_loss, initial_positive_gap/2)',
        nonpositive_initial_competitors='soft_original_loss_margin_not_hard_feasible',
        other_contrasts='original_loss_margin',
        guard='all_feasible_protection_actual_partial_cost_gaps_after_quantization',
        backtracking='first_safe_quantized_dyadic_step_or_no_update',
        maximum_halvings=MAX_HALVINGS,
        averaging='every_post_visit_including_rejection; quantize_if_safe_else_exact_average',
        raw_loss_changed=False, hard_guard_is_not_unseen_path_or_accuracy_guarantee=True)


def policy(rows, competitors, initial):
    by_id = {r['contrast_id']: r for r in rows}; seen = set(); protected = []
    for item in sorted(competitors, key=lambda r: r['sample_id']):
        key = item['active_contrast_id']
        if key not in by_id or key in seen:
            raise ValueError('ordinal_missing_or_duplicate_competitor')
        seen.add(key); row = by_id[key]
        if row['sample_id'] != item['sample_id'] or f(row['loss']) <= 0:
            raise ValueError('ordinal_competitor_scope_or_loss')
        gap = base.gap(row, initial)
        protected.append(item | dict(initial_gap=q(gap), raw_loss=row['loss'],
            hard_floor=q(min(f(row['loss']), gap/2)) if gap > 0 else None,
            status='feasible_ordinal_protection' if gap > 0 else 'nonpositive_gap_soft_repair'))
    return dict(configuration=configuration(), competitors=protected,
        missing_competitors_are_not_protected=True, reference_used_at_inference=False)


def guard(rows, spec):
    by_id = {r['contrast_id']: r for r in rows}
    return [(by_id[r['active_contrast_id']], f(r['hard_floor']))
            for r in spec['competitors'] if r['hard_floor'] is not None]


def safe(weights, floors):
    return all(base.gap(row, weights) >= floor for row, floor in floors)


def min_slack(weights, floors):
    return min((base.gap(row, weights)-floor for row, floor in floors), default=None)


def guarded_step(current, proposal, box, floors):
    # Re-quantize only changed dimensions: unknown and fixed non-grid values
    # must not be rounded as a side effect of another feature's update.
    changed = [k for k in TRAINABLE if current[k] != proposal[k]]
    for power in range(MAX_HALVINGS+1):
        alpha = F(1, 2**power); candidate = dict(current)
        for k in changed:
            low, high = box[k]
            candidate[k] = max(low, min(high, use.quantize(
                current[k]+alpha*(proposal[k]-current[k]))))
        base.coefficients(candidate)
        if safe(candidate, floors):
            return candidate, power
    return dict(current), None


def diagnostics(rows, weights, spec):
    floors = guard(rows, spec)
    margins = {r['active_contrast_id']: f(r['hard_floor']) for r in spec['competitors']
               if r['hard_floor'] is not None}
    raw = [max(F(), f(r['loss'])-base.gap(r, weights)) for r in rows]
    required = [max(F(), margins.get(r['contrast_id'], f(r['loss']))-base.gap(r, weights)) for r in rows]
    return dict(raw_loss_margin_sum=q(sum(raw, F())), policy_margin_sum=q(sum(required, F())),
        negative_cheaper_than_target=sum(base.gap(r, weights) < 0 for r in rows),
        protection_floors=len(floors), protection_floor_violations=sum(
            base.gap(r, weights) < v for r, v in floors),
        minimum_floor_slack=q(min_slack(weights, floors)) if floors else None,
        margins_are_not_musical_accuracy=True)


def fit(rows, competitors, initial, contract, manifest, parent_sha, pool_sha):
    base.validate_rows(rows, contract, manifest, parent_sha)
    initial = base.coefficients(initial); box = base.bounds(initial)
    rows = sorted(rows, key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id']))
    spec = policy(rows, competitors, initial); floors = guard(rows, spec)
    margins = {r['active_contrast_id']: f(r['hard_floor']) for r in spec['competitors']
               if r['hard_floor'] is not None}
    if not safe(initial, floors): raise ValueError('ordinal_initial_infeasible')
    weights = dict(initial); totals = dict.fromkeys(FEATURES, F())
    ticks = 0; updates = []; epochs = []
    for epoch in range(1, 4):
        statuses = Counter()
        for row in rows:
            required = margins.get(row['contrast_id'], f(row['loss']))
            violation = required-base.gap(row, weights)
            gradient = {k: f(row['gradient_delta'][k]) if row['available'][k] else F() for k in TRAINABLE}
            norm = sum((v*v for v in gradient.values()), F())
            if violation <= 0: statuses['required_margin_satisfied'] += 1
            elif norm == 0: statuses['known_trainable_collision'] += 1
            else:
                tau = min(F(1, 20), violation/norm); proposed = dict(weights)
                for k, g in gradient.items():
                    if not g: continue
                    low, high = box[k]
                    proposed[k] = max(low, min(high, use.quantize(weights[k]+tau*g)))
                new, power = guarded_step(weights, proposed, box, floors)
                statuses['guard_rejected' if power is None else
                         'updated' if new != weights else 'bounded_or_quantized_no_change'] += 1
                if new != weights:
                    updates.append(dict(epoch=epoch, contrast_id=row['contrast_id'], tau=q(tau),
                        halvings=power, required_margin=q(required), raw_loss=row['loss'],
                        before=q(violation), after=q(required-base.gap(row, new)),
                        minimum_protection_slack=q(min_slack(new, floors)) if floors else None,
                        weights={k: q(v) for k, v in new.items()}))
                weights = new
            if not safe(weights, floors): raise ValueError('ordinal_post_visit_not_safe')
            ticks += 1
            for k in FEATURES: totals[k] += weights[k]
        epochs.append(dict(epoch=epoch, statuses=dict(statuses), weights={k: q(v) for k, v in weights.items()}))
    exact = {k: totals[k]/ticks for k in FEATURES}
    rounded = {k: initial[k] if exact[k] == initial[k] else
               max(box[k][0], min(box[k][1], use.quantize(exact[k]))) for k in FEATURES}
    average = rounded if safe(rounded, floors) else exact
    base.coefficients(average)
    if not safe(average, floors): raise ValueError('ordinal_average_not_safe')
    model = dict(version=VERSION, feature_version=base.ledger.role.VERSION,
        configuration=configuration(), policy=spec,
        initial_weights={k: q(v) for k, v in initial.items()}, weights={k: q(v) for k, v in average.items()},
        bounds={k: [q(a), q(b)] for k, (a, b) in box.items()},
        training_contrasts=len(rows), averaging_ticks=ticks, epochs=epochs, updates=updates,
        final_average_quantized=average == rounded,
        training_dataset_content_sha256=use.content_hash(rows), sealed_pool_sha256=pool_sha,
        competitors_content_sha256=use.content_hash(competitors),
        before=diagnostics(rows, initial, spec), after=diagnostics(rows, average, spec),
        use_contract_sha256=use.content_hash(contract), parent_recall_sha256=parent_sha,
        purpose='local_noncommercial_research', restrictions={k: False for k in use.RESTRICTIONS},
        training_reference_labels_used=True, source_labels_used_at_inference=False, dev_used=False,
        production_deployment=False, pool_complete=False, confidence_calibrated=False)
    model['model_id'] = 'ordinal_protection_'+use.content_hash(model)[:24]
    return model


def model_weights(model, rows, competitors, initial, contract, manifest, parent_sha, pool_sha):
    base.validate_rows(rows, contract, manifest, parent_sha); box = base.bounds(initial)
    body = {k: v for k, v in model.items() if k != 'model_id'}
    if (model.get('version') != VERSION or model.get('feature_version') != base.ledger.role.VERSION
            or model.get('configuration') != configuration()
            or model.get('model_id') != 'ordinal_protection_'+use.content_hash(body)[:24]
            or model.get('policy') != policy(rows, competitors, initial)
            or model.get('initial_weights') != {k: q(v) for k, v in initial.items()}
            or model.get('training_dataset_content_sha256') != use.content_hash(sorted(
                rows, key=lambda r: (r['entry']['work_family_id'], r['sample_id'], r['contrast_id'])))
            or model.get('sealed_pool_sha256') != pool_sha
            or model.get('competitors_content_sha256') != use.content_hash(competitors)
            or model.get('bounds') != {k: [q(a), q(b)] for k, (a, b) in box.items()}
            or model.get('use_contract_sha256') != use.content_hash(contract)
            or model.get('parent_recall_sha256') != parent_sha
            or model.get('purpose') != 'local_noncommercial_research'
            or model.get('restrictions') != {k: False for k in use.RESTRICTIONS}
            or any(model.get(k) is not False for k in ('dev_used', 'production_deployment', 'source_labels_used_at_inference'))):
        raise ValueError('ordinal_model_contract')
    result = base.coefficients({k: f(v) for k, v in model['weights'].items()})
    if any(not box[k][0] <= result[k] <= box[k][1] for k in FEATURES) or not safe(result, guard(rows, model['policy'])):
        raise ValueError('ordinal_model_box_or_guard')
    return result
