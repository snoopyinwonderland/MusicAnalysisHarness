"""Prespecified finite Train grid, partial availability and margin protection."""
from collections import Counter
from fractions import Fraction as F
from itertools import product

from . import harmony_partial_support_scoring as score

VERSION='harmony-partial-support-grid-learning-0.1.0'
GRID=(F(),F(1,20),F(1,4),F(1),F(2))
REGULARIZATION=F(1,100)
q,f=score.q,score.f


def configuration():
    return dict(grid=[q(v) for v in GRID],configurations=len(GRID)**len(score.FEATURES),
        old35_frozen=True,new_dimensions=score.FEATURES,source_labels_for_features=False,
        prior_three_source_context_weights_frozen_zero=True,
        margin_floor='half_of_positive_frozen_old_gap',unknown_dimension_fit=False,
        regularization=q(REGULARIZATION),criterion='family_balanced_hinge_plus_L1',dev_used=False,
        no_fresh_decode_if_every_new_weight_zero=True)


def gap(row,weights,*,actual=False):
    values=row.get('scored_partial_delta',row['delta']) if actual else row['delta']
    return f(row['old_gap'])+sum((f(values[k])*weights[k] for k in score.FEATURES
                                if actual or row['available'][k]),F())


def objective(rows,weights):
    families=Counter(r['work_family_id'] for r in rows)
    return sum((max(F(),f(r['loss'])-gap(r,weights))/families[r['work_family_id']]
                for r in rows),F())/len(families)+REGULARIZATION*sum(map(abs,weights.values()))


def fit(rows):
    if not rows or any(r['split']!='train' for r in rows): raise ValueError('partial_support_fit_requires_train')
    if len({r['contrast_id'] for r in rows})!=len(rows): raise ValueError('duplicate_partial_support_contrast')
    usable=[r for r in rows if any(r['available'].values())]
    if not usable: raise ValueError('no_complete_partial_support_dimensions')
    protection=[r for r in rows if f(r['old_gap'])>0];evaluated=[];best=None
    for values in product(GRID,repeat=len(score.FEATURES)):
        weights=score.coefficients({k:v if i==0 else -v for i,(k,v) in enumerate(zip(score.FEATURES,values))})
        if any(gap(r,weights,actual=True)<f(r['old_gap'])/2 for r in protection): continue
        cost=objective(usable,weights);order=cost,sum(map(abs,weights.values())),values
        evaluated.append(dict(weights={k:q(v) for k,v in weights.items()},objective=q(cost)))
        if best is None or order<best[0]: best=order,weights
    if best is None: raise ValueError('no_feasible_partial_support_configuration')
    return dict(version=VERSION,configuration=configuration(),rows=len(rows),usable_rows=len(usable),
        unknown_rows_excluded=len(rows)-len(usable),
        unknown_dimensions_excluded=sum(not v for r in rows for v in r['available'].values()),
        positive_margin_protections=len(protection),feasible_configurations=len(evaluated),evaluated=evaluated,
        weights={k:q(v) for k,v in best[1].items()},objective_before=q(objective(usable,score.ZERO)),
        objective_after=q(best[0][0]),global_continuous_optimum_claimed=False,
        independent_accuracy_claimed=False,production_modified=False)
