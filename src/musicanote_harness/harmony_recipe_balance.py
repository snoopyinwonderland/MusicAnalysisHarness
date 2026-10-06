"""Soft, explicitly incomplete recipe coverage for every declared pitch set.

Unknown shape is NOT an observed zero omission. Retain the four nullable
support observations and add a separate, train-calibrated recipe residual.
No pitch is removed, no NCT is confirmed, and extensions are not prohibited.
"""
from fractions import Fraction as F
from functools import lru_cache

from . import harmony_support_balance as support
from .harmony_functional_scoring import six_four_surface
from .harmony_temporal_scoring import bind
from .seventh_context import chord, QUALITIES

VERSION = "harmony-recipe-balance-0.1.0"
FEATURE_VERSION = "soft-declared-recipe-residual-0.1.0"
FEATURE = "outside_supported_recipe_exposure"
FEATURES = (*support.FEATURES, FEATURE)
ZERO = support.ZERO | {FEATURE: F()}
VOCABULARY = tuple(QUALITIES)


def coefficients(values=None):
    result = dict(ZERO if values is None else values)
    if set(result) != set(FEATURES):
        raise ValueError("invalid_recipe_coefficients")
    support.coefficients({k: result[k] for k in support.FEATURES})
    if type(result[FEATURE]) is not F or not 0 <= result[FEATURE] <= 1:
        raise ValueError("invalid_recipe_coefficients")
    return result


@lru_cache(maxsize=4096)
def recipe(signature):
    """Minimum *declaration* residual, not fit to a gold chord or local key.

    A rooted signature compares with the same-root triad/seventh vocabulary.
    Root-unknown signatures compare all declared roots but remain root-unknown.
    The established functional 6-4 alternative is also an exact recipe.
    Absent template pitches are NOT inserted in either the source or signature.
    """
    root, tokens = signature
    members = frozenset(tokens)
    if not members or len(members) != len(tokens):
        raise ValueError("empty_or_duplicate_recipe_members")
    if six_four_surface(signature) is not None:
        return F(), (("functional_six_four_surface", root, tuple(sorted(members)), ()),)
    comparisons = []
    for origin in (root,) if root is not None else tuple(sorted(members)):
        for quality in VOCABULARY:
            model = frozenset(map(tuple, chord(origin, quality)["members"]))
            residual = tuple(sorted(members-model))
            comparisons.append((F(len(residual), len(members)),
                                (quality, origin, tuple(sorted(model)), residual)))
    best = min(x[0] for x in comparisons)
    return best, tuple(item for value, item in comparisons if value == best)


def recipe_feature(problem, start, end, signature):
    if not problem.points[0] <= start < end <= problem.points[-1]:
        raise ValueError("invalid_recipe_span")
    fraction, _ = recipe(signature)
    return fraction * (end-start)/(problem.points[-1]-problem.points[0])


def features(problem, source, start, end, signature, *, index=None):
    values, details = support.support_features(problem, source, start, end, signature, index=index)
    value = recipe_feature(problem, start, end, signature)
    if index is None:
        fraction, alternatives = recipe(signature)
        details += [{"kind": "declared_recipe_residual", "span": {"start": support.q(start), "end": support.q(end)},
            "normalized_value": support.q(value), "residual_fraction": support.q(fraction),
            "root_available": signature[0] is not None,
            "equally_close_recipes": [{"quality": quality, "root": root, "template_members": members,
                                       "outside_declared_members": residual}
                                      for quality, root, members, residual in alternatives],
            "interpretation": "vocabulary_distance_not_confirmed_nonchord_tones",
            "omitted_template_members_invented": False, "full_harmony_vocabulary": False,
            "confirmed_nct": False, "candidate_removed": False, "source_labels_used": False}]
    return values | {FEATURE: value}, details


class Scorer(support.Scorer):
    def __init__(self, problem, ev, values=None, *, build_index=True, **args):
        bind(support.Scorer.__init__, {"coefficients": coefficients, "support_features": features,
                                     "FEATURE_VERSION": FEATURE_VERSION})(
            self, problem, ev, values, build_index=build_index, **args)

    def path_features(self, ids, *, indexed=False):
        return bind(support.Scorer.path_features, {"ZERO": ZERO, "FEATURES": FEATURES,
                                                  "support_features": features})(self, ids, indexed=indexed)

    def decode(self, *, transition_budget=2_000_000):
        result = bind(support.Scorer.decode, {"VERSION": VERSION, "FEATURE_VERSION": FEATURE_VERSION})(
            self, transition_budget=transition_budget)
        result["recipe_balance_contract"] = {"version": VERSION, "vocabulary": VOCABULARY,
            "full_harmony_vocabulary": False, "unsupported_shapes_banned": False,
            "unknown_omission_features_imputed_zero": False, "recipe_residual_is_nct_label": False,
            "same_original_candidates": True, "source_labels_used": False, "production_modified": False}
        return result
