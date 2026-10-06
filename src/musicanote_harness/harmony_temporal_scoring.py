"""Research ablation: meter-sized resolution credit and deferred root evidence.

Do NOT ban short chords, force root attacks, or overwrite the sealed engine.
The same candidate DAG is decoded jointly. A later root is not evidence that
it sounded earlier. Rootless/unknown cases and arpeggios remain possible.
"""
from bisect import bisect_right
from fractions import Fraction as F
from types import FunctionType, CodeType

from . import harmony_batched_frontier as frontier
from . import harmony_functional_scoring as functional
from .harmony_evidence_scoring import BASE_WEIGHTS, metric, run_features
from .harmony_exact_frontier import RunIndex
from .harmony_candidate_recall import rational as q

VERSION = "harmony-temporal-scoring-0.1.0"
FEATURE_VERSION = "source-bound-temporal-run-features-0.1.0"
# One fixed additional coefficient, reusing the existing missing-root scale.
# No fit, grid search, work IDs, home-key answers or annotation lookups.
ROOT_WEIGHT = BASE_WEIGHTS["missing_root"]
ARMS = {"baseline": (False, False), "meter_credit": (True, False),
        "deferred_root": (False, True), "combined": (True, True)}


def bind(original, replacements):
    """Private globals also serve nested scorer functions; validate usage.

The old workspace helper intentionally checks outer bytecode only. These
decoders define their run/pair scorers inside decode(), so include nested code
objects without rewriting bytecode or changing any module dictionary.
"""
    if not isinstance(original, FunctionType): raise ValueError("unsupported_scoring_callable")
    def names(code):
        result = set(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, CodeType): result.update(names(constant))
        return result
    if not set(replacements) <= names(original.__code__): raise ValueError("scoring_binding_dependency_not_used")
    if not set(replacements) <= original.__globals__.keys(): raise ValueError("scoring_binding_dependency_missing")
    env = original.__globals__ | replacements
    result = FunctionType(original.__code__, env, original.__name__, original.__defaults__, original.__closure__)
    result.__kwdefaults__ = original.__kwdefaults__
    return result


def beat_extent(source, start, end):
    """Integrate local notated beat units, including a changing meter.

Unknown meter stays unavailable, not a claim of zero musical support.
Compound 6/9/12 eighth meter uses the existing dotted-quarter beat contract.
"""
    if not start < end: raise ValueError("invalid_temporal_span")
    cuts = [start]+[t for t in source._measure_times if start < t < end]+[end]
    value = F()
    for a, b in zip(cuts, cuts[1:]):
        _, unit = metric(source, a)
        if unit is None: return None
        value += (b-a)/unit
    return value


def resolution_features(ev, start, boundary, end, left, right, *, attenuate=True):
    values, details = functional.pair_features(ev, start, boundary, end, left, right)
    if not attenuate: return values, details
    beats = beat_extent(ev.source, start, boundary)
    factor = min(F(1), beats) if beats is not None else F(1)
    # Unknown meter retains the old bounded credit; it does not manufacture
    # absence. Still record that proportional support could not be assessed.
    graded = {k: v*factor for k, v in values.items()}
    receipt = {"kind": "meter_proportional_resolution_credit", "left_span": {"start": q(start), "end": q(boundary)},
        "notated_beat_extent": None if beats is None else q(beats), "credit_factor": q(factor),
        "meter_available": beats is not None, "unknown_meter_policy": "retain_old_bounded_credit",
        "raw_features": {k: q(v) for k, v in values.items()}, "short_chord_rejected": False,
        "confirmed_nct": False, "function_confirmed": False}
    return graded, details+([receipt] if details else [])


def deferred_root(problem, source, start, end, sig):
    """First positive root evidence, not continuous vertical completeness.

Only a root eventually observed in THIS run has a deferred-presence value.
Never-seen roots already pay the original missing_root term: no double charge.
Once a root has sounded, its later release does not penalize an arpeggio.
"""
    root = sig[0]
    active = [e for e in source.events if e.start < end and start < e.end]
    if root is None or any(e.pitch is None for e in active): return None, []
    roots = [e for e in active if e.pitch == root]
    if not roots: return F(), []
    first = min(max(start, e.start) for e in roots)
    value = (first-start)/(problem.points[-1]-problem.points[0])
    details = [{"kind": "deferred_first_root_evidence", "root_spelling": root,
        "span": {"start": q(start), "end": q(end)}, "first_positive_root_time": q(first),
        "source_event_ids": sorted(e.event_id for e in roots if max(start, e.start) == first),
        "delay_quarters": q(first-start), "normalized_exposure": q(value),
        "rootless_harmony_rejected": False, "root_attack_required": False,
        "later_root_proves_earlier_root": False}]
    return value, details


class TemporalIndex(RunIndex):
    def features(self, start, end, sig):
        values, patterns = super().features(start, end, sig)
        i, j = self.positions[start], self.positions[end]
        root = sig[0]; exposure = self.presence.get(root)
        value = None
        if root is not None and self.unresolved[j] == self.unresolved[i]:
            value = F()
            if exposure is not None and exposure[j] > exposure[i]:
                k = bisect_right(exposure, exposure[i], i+1, j+1)
                value = (self.points[k-1]-start)/(self.points[-1]-self.points[0])
        return values | {"root_deferred_presence": value}, patterns


def make_decoder(arm):
    if arm not in ARMS: raise ValueError("unknown_temporal_arm")
    meter_credit, root_evidence = ARMS[arm]
    if arm == "baseline": return frontier.decode
    weights = dict(BASE_WEIGHTS)
    if root_evidence: weights["root_deferred_presence"] = ROOT_WEIGHT
    def run(problem, ev, start, end, sig):
        values, patterns = run_features(problem, ev, start, end, sig)
        if root_evidence:
            value, _ = deferred_root(problem, ev, start, end, sig)
            values = values | {"root_deferred_presence": value}
        return values, patterns
    def pair(ev, start, boundary, end, left, right):
        return resolution_features(ev, start, boundary, end, left, right, attenuate=meter_credit)
    # Private dependency dictionaries, original bytecode. No module global
    # patches; old reports/tests/production can still call their original engine.
    reconstruction = bind(functional.decode, {"BASE_WEIGHTS": weights, "run_features": run,
        "pair_features": pair, "FEATURE_VERSION": FEATURE_VERSION})
    return bind(frontier.decode, {"BASE_WEIGHTS": weights,
        "RunIndex": TemporalIndex if root_evidence else RunIndex,
        "pair_features": pair, "original_decode": reconstruction})


def decode(problem, ev, *, arm="combined", functional_evidence=True, transition_budget=2_000_000):
    result = make_decoder(arm)(problem, ev, functional_evidence=functional_evidence, transition_budget=transition_budget)
    result["temporal_scoring_contract"] = {"version": VERSION, "arm": arm,
        "meter_credit": ARMS[arm][0], "deferred_root": ARMS[arm][1],
        "new_feature_weight": q(ROOT_WEIGHT) if ARMS[arm][1] else None,
        "existing_weight_values_changed": False, "scoring_contract_changed": arm != "baseline",
        "training_performed": False, "source_labels_used": False}
    result["search_diagnostics"]["score_weights_changed"] = arm != "baseline"
    if result["selected"] is not None and arm != "baseline":
        result["selected"]["proposal_id"] = "temporal_"+arm+"_"+result["selected"]["proposal_id"]
        result["selected"]["temporal_observations"] = [detail
            for r in result["selected"]["harmonic_runs"]
            for detail in deferred_root(problem, ev.source, F(r["span"]["start"]["numerator"], r["span"]["start"]["denominator"]),
                F(r["span"]["end"]["numerator"], r["span"]["end"]["denominator"]),
                (tuple(r["root_spelling"]) if r["root_spelling"] is not None else None,
                 tuple(tuple(m) for m in r["members"])))[1]] if ARMS[arm][1] else []
    return result


def score_path(problem, ev, ids, *, arm="combined", functional_evidence=True):
    if arm not in ARMS: raise ValueError("unknown_temporal_arm")
    meter_credit, root_evidence = ARMS[arm]
    def run(p, source, a, b, sig):
        values, patterns = run_features(p, source, a, b, sig)
        return (values | {"root_deferred_presence": deferred_root(p, source, a, b, sig)[0]}
                if root_evidence else values), patterns
    def pair(evidence, a, b, c, left, right):
        return resolution_features(evidence, a, b, c, left, right, attenuate=meter_credit)
    weights = BASE_WEIGHTS | ({"root_deferred_presence": ROOT_WEIGHT} if root_evidence else {})
    return bind(functional.score_path, {"BASE_WEIGHTS": weights, "run_features": run, "pair_features": pair})(
        problem, ev, ids, functional_evidence=functional_evidence)
