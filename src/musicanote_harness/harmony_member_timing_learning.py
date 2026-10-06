"""One Train-only timing coefficient; sealed step67 weights stay frozen."""
from fractions import Fraction as F
from . import harmony_support_balance_learning as prior
from .harmony_member_timing import FEATURE, FEATURE_VERSION
from .harmony_temporal_scoring import bind

VERSION = 'harmony-member-timing-learning-0.1.0'
FEATURES = (FEATURE,)
ZERO = {FEATURE: F()}


def coefficients(values=None):
    result = dict(ZERO if values is None else values)
    if set(result) != set(FEATURES) or type(result[FEATURE]) is not F or not 0 <= result[FEATURE] <= 1:
        raise ValueError('invalid_member_timing_learning_coefficient')
    return result


def fit(rows, contract, manifest, parent_sha, **kwargs):
    return bind(prior.fit, {'FEATURES': FEATURES, 'ZERO': ZERO, 'coefficients': coefficients,
        'VERSION': VERSION, 'FEATURE_VERSION': FEATURE_VERSION})(rows, contract, manifest, parent_sha, **kwargs)


def model_weights(model, contract, manifest, parent_sha):
    return bind(prior.model_weights, {'VERSION': VERSION, 'FEATURE_VERSION': FEATURE_VERSION,
        'coefficients': coefficients})(model, contract, manifest, parent_sha)
