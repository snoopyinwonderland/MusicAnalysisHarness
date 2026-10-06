"""Small, prespecified Train-only calibration of three new evidence costs.

All 35 old weights stay fixed. Compare 125 exact rational configurations;
protect already-positive old margins to at least half their original value.
This is finite-grid calibration, not a globally optimal statistical model.
"""
from collections import Counter
from fractions import Fraction as F
from itertools import product

from . import harmony_source_context_scoring as score

VERSION = 'harmony-source-context-grid-learning-0.1.0'
GRID = (F(), F(1,4), F(1,2), F(1), F(2))
REGULARIZATION = F(1,100)
q, f = score.q, score.f


def configuration():
    return dict(grid=[q(v) for v in GRID], configurations=len(GRID)**3,
        old35_frozen=True, new_dimensions=score.FEATURES, source_labels_for_features=False,
        margin_floor='half_of_positive_frozen_old_gap', unknown_dimension_fit=False,
        regularization=q(REGULARIZATION), criterion='family_balanced_hinge_plus_L1',
        dev_used=False, fitted_on_existing_and_fresh_frozen_train_contrasts=True)


def gap(row, weights):
    return f(row['old_gap'])+sum((f(row['delta'][k])*weights[k] for k in score.FEATURES if row['available'][k]), F())


def actual_gap(row, weights):
    values = row.get('scored_partial_delta', row['delta'])
    return f(row['old_gap'])+sum((f(values[k])*weights[k] for k in score.FEATURES), F())


def objective(rows, weights):
    families = Counter(r['work_family_id'] for r in rows)
    return sum((max(F(), f(r['loss'])-gap(r, weights))/families[r['work_family_id']] for r in rows), F())/len(families)+REGULARIZATION*sum(map(abs, weights.values()))


def fit(rows):
    if not rows or any(r['split'] != 'train' for r in rows): raise ValueError('source_context_fit_requires_train')
    ids = [r['contrast_id'] for r in rows]
    if len(set(ids)) != len(ids): raise ValueError('duplicate_source_context_contrast')
    # Do not optimize through a partial observation. Availability is per
    # complete path/dimension, just as in the previous score-learning contract.
    usable = [r for r in rows if any(r['available'].values())]
    if not usable: raise ValueError('no_complete_source_context_learning_rows')
    protections = [r for r in rows if f(r['old_gap']) > 0]
    evaluated = []; best = None
    for values in product(GRID, repeat=3):
        weights = score.coefficients(dict(zip(score.FEATURES, (values[0], -values[1], -values[2]))))
        if any(actual_gap(r, weights) < f(r['old_gap'])/2 for r in protections): continue
        cost = objective(usable, weights); order = cost, sum(map(abs,weights.values())), values
        evaluated.append(dict(weights={k:q(v) for k,v in weights.items()}, objective=q(cost)))
        if best is None or order < best[0]: best = order, weights
    if best is None: raise ValueError('source_context_no_feasible_configuration')
    return dict(version=VERSION, configuration=configuration(), rows=len(rows), usable_rows=len(usable),
        unknown_rows_excluded=len(rows)-len(usable),
        unknown_dimensions_excluded=sum(not v for r in rows for v in r['available'].values()),
        positive_margin_protections=len(protections),
        feasible_configurations=len(evaluated), evaluated=evaluated,
        weights={k:q(v) for k,v in best[1].items()}, objective_before=q(objective(usable, score.ZERO)),
        objective_after=q(best[0][0]), global_continuous_optimum_claimed=False,
        independent_accuracy_claimed=False, production_modified=False)
