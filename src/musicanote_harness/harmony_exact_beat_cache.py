"""Exact source-local reuse of notated-beat integration, research only.

Do not change a score, candidate, DP state, operation cap or detailed receipt.
Use private dependency bindings of the sealed bytecode, never module patches.
The original (uncached) detailed winner still independently checks its cost.
"""
from types import MethodType

from . import harmony_context_joint_decoder as joint
from . import harmony_context_scalar_index as scalar
from . import harmony_joint_balance_trial as full35
from . import harmony_temporal_scoring as temporal

VERSION = 'harmony-exact-source-beat-cache-0.1.0'


class BeatCache:
    def __init__(self, source):
        self.source = source
        self.measure_times = source._measure_times
        self.measures = source.measures
        self.values = {}
        self.stats = dict(calls=0, hits=0, integrations=0)
        self._resolution = temporal.bind(temporal.resolution_features, {'beat_extent': self.extent})

    def extent(self, source, start, end):
        if (source is not self.source or source._measure_times is not self.measure_times
                or source.measures is not self.measures):
            raise ValueError('beat_cache_source_or_meter_changed')
        # Validate even on a hit; never turn a malformed interval into a value.
        if not start < end: raise ValueError('invalid_temporal_span')
        self.stats['calls'] += 1; key = start, end
        if key in self.values:
            self.stats['hits'] += 1; return self.values[key]
        value = temporal.beat_extent(source, start, end)
        self.values[key] = value; self.stats['integrations'] += 1
        return value

    def resolution(self, ev, *args, **kwargs):
        if ev.source is not self.source: raise ValueError('beat_cache_evidence_source_changed')
        return self._resolution(ev, *args, **kwargs)


class ScalarIndex(scalar.ScalarIndex):
    def __init__(self, scorer):
        super().__init__(scorer)
        self._values = MethodType(temporal.bind(scalar.ScalarIndex.values,
            {'resolution_features': scorer.beat_cache.resolution}), self)

    def values(self, runs, index): return self._values(runs, index)


class Scorer(full35.Scorer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.beat_cache = BeatCache(self.ev.source)
        self._cached_delayed = MethodType(temporal.bind(joint.Scorer._delayed,
            {'resolution_features': self.beat_cache.resolution}), self)

    def _delayed(self, budget): return self._cached_delayed(budget)

    def scalar_values(self, runs, index):
        if self.scalar_index is None: self.scalar_index = ScalarIndex(self)
        return self.scalar_index.values(runs, index)

    def decode(self, **kwargs):
        result = super().decode(**kwargs)
        result['exact_beat_cache_contract'] = dict(version=VERSION,
            same_sealed_dp_bytecode=True, changed_dependency='resolution_features.beat_extent',
            source_local_cache=True, harmonic_signature_not_in_beat_key=True,
            detailed_receipt_and_independent_winner_check_unchanged=True,
            unknown_meter_remains_null=True, new_candidates=False,
            coefficients_changed=False, production_modified=False)
        result['exact_beat_cache_diagnostics'] = dict(self.beat_cache.stats,
                                                    entries=len(self.beat_cache.values))
        return result
