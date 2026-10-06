"""One Train-only residual coefficient; all step67 coefficients stay frozen."""
from fractions import Fraction as F
from . import harmony_support_balance_learning as prior
from .harmony_recipe_balance import FEATURE, FEATURE_VERSION
from .harmony_temporal_scoring import bind

VERSION = "harmony-recipe-balance-learning-0.1.0"
FEATURES = (FEATURE,)
ZERO = {FEATURE: F()}


def coefficients(values=None):
    value = dict(ZERO if values is None else values)
    if set(value) != set(FEATURES) or type(value[FEATURE]) is not F or not 0 <= value[FEATURE] <= 1:
        raise ValueError("invalid_recipe_learning_coefficient")
    return value


def fit(rows, contract, manifest, parent_sha, **kwargs):
    return bind(prior.fit, {"FEATURES": FEATURES, "ZERO": ZERO, "coefficients": coefficients,
                           "VERSION": VERSION, "FEATURE_VERSION": FEATURE_VERSION})(
        rows, contract, manifest, parent_sha, **kwargs)


def model_weights(model, contract, manifest, parent_sha):
    return bind(prior.model_weights, {"VERSION": VERSION, "FEATURE_VERSION": FEATURE_VERSION,
                                     "coefficients": coefficients})(model, contract, manifest, parent_sha)
