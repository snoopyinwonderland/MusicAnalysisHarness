"""Research-only late identifying-member support, not retroactive sound.

Allow one local notated beat for distributed presentation. A later first
third/altered fifth/seventh is a soft cost, never a forced chord boundary.
Prepared, contiguous same-lane step resolution halves (not erases) this cost.
Absence stays with the sealed step67 features; unsupported shapes stay null.
"""
from bisect import bisect_right
from fractions import Fraction as F
from math import lcm

from . import harmony_support_balance as support
from .harmony_root_context_scoring import RootReturnContext
from .harmony_reading_voice_context import spelled_height
from .harmony_temporal_scoring import bind, beat_extent

VERSION = 'harmony-member-timing-0.1.0'
FEATURE_VERSION = 'first-identifying-member-local-beat-grace-0.1.0'
FEATURE = 'late_identifying_member_exposure'
FEATURES = (*support.FEATURES, FEATURE)
ZERO = support.ZERO | {FEATURE: F()}
ALLOWANCE_BEATS = F(1)
PREPARED_FACTOR = F(1, 2)


def coefficients(values=None):
    result = dict(ZERO if values is None else values)
    if set(result) != set(FEATURES): raise ValueError('invalid_member_timing_coefficients')
    support.coefficients({k: result[k] for k in support.FEATURES})
    if type(result[FEATURE]) is not F or not 0 <= result[FEATURE] <= 1:
        raise ValueError('invalid_member_timing_coefficients')
    return result


class TimingContext(RootReturnContext):
    def __init__(self, ev, **args):
        super().__init__(ev, **args)
        self.beats = {}; self.resolutions = {}
        self.predecessors = {}
        for p, n in ev.links: self.predecessors.setdefault(n['id'], []).append(p)
        self.starts_by_token = {}
        for r in self.rows:
            self.starts_by_token.setdefault(r['token'], {}).setdefault(r['start'], []).append(r)

    def extent(self, a, b):
        if a == b: return F()
        if (a, b) not in self.beats: self.beats[a, b] = beat_extent(self.source, a, b)
        return self.beats[a, b]

    def prepared(self, start, first, role, signature):
        key = start, first, role, signature
        if key not in self.resolutions:
            self.resolutions[key] = self._prepared(start, first, role, signature)
        return self.resolutions[key]

    def _prepared(self, start, first, role, signature):
        result = []
        for n in self.starts_by_token.get(role, {}).get(first, ()):
            if not n['clock_valid'] or n['identity'] is None: continue
            for p in self.predecessors.get(n['id'], ()):
                lane = n['identity']
                # A note introduced AFTER the proposed boundary is not a
                # prepared suspension merely because it steps into a member.
                if (not p['clock_valid'] or p['identity'] != lane or p['token'] is None
                        or p['token'] in signature[1] or not p['start'] < start < p['end']
                        or p['end'] != first): continue
                hp, hn = spelled_height(p['pitch_data']), spelled_height(n['pitch_data'])
                if hp is None or hn is None or abs(hn-hp) != 1 or not 0 < abs(n['pitch']-p['pitch']) <= 2:
                    continue
                if any(ident == lane and p['start'] <= t <= first for ident, t in self.graces): continue
                if any(p['start'] < t <= first for t in self.barriers): continue
                if self.history_gate is not None and not self.history_gate(p['start'], n['end']): continue
                result.append({'kind': 'prepared_step_resolution_candidate',
                    'source_event_ids': [p['id'], n['id']], 'original_explicit_lane': lane,
                    'preparation_span': {'start': support.q(p['start']), 'end': support.q(p['end'])},
                    'arrival_span': {'start': support.q(n['start']), 'end': support.q(n['end'])},
                    'direction': 'descending' if n['pitch'] < p['pitch'] else 'ascending',
                    'factor': support.q(PREPARED_FACTOR), 'confirmed_nct': False,
                    'voice_identity_confirmed': False, 'raw_nonmember_cost_removed': False,
                    'history_clock_gate_accepted': True if self.history_gate is not None else None})
        return result


def timing_feature(problem, source, start, end, signature, *, context, index=None):
    if not problem.points[0] <= start < end <= problem.points[-1]: raise ValueError('invalid_member_timing_span')
    roles = support.roles(signature)
    total_beats = context.extent(problem.points[0], problem.points[-1])
    if index is None:
        active = [e for e in source.events if e.start < end and start < e.end]
        available = bool(active) and all(e.pitch is not None for e in active)
    else:
        i, j = index.positions[start], index.positions[end]
        available = index.unresolved[j] == index.unresolved[i] and any(p[j] > p[i] for p in index.presence.values())
    if roles is None or not available or total_beats is None:
        return None, [{'kind': 'member_entry_timing_unavailable', 'unsupported_shape': roles is None,
                       'pitch_available': available, 'meter_available': total_beats is not None}]
    identified = [(name, token) for name, token in zip(('third', 'altered_fifth', 'seventh'), roles) if token is not None]
    if not identified: return F(), []
    values = []; receipts = []
    for name, token in identified:
        if index is None:
            matching = [e for e in active if e.pitch == token]
            first = min((max(start, e.start) for e in matching), default=None)
        else:
            exposure = index.presence.get(token)
            first = (index.points[bisect_right(exposure, exposure[i], i+1, j+1)-1]
                     if exposure is not None and exposure[j] > exposure[i] else None)
        # Never-present members already pay the old absence feature. Do not
        # charge their full duration a second time under this new name.
        delay = context.extent(start, first) if first is not None else F()
        if delay is None: return None, []
        raw = max(F(), delay-ALLOWANCE_BEATS)/total_beats
        prepared = context.prepared(start, first, token, signature) if raw else []
        value = raw*(PREPARED_FACTOR if prepared else 1)
        values.append(value)
        if index is None:
            arrivals = [e for e in matching if max(start, e.start) == first]
            before = [e for e in active if first is not None and e.start < first <= e.end]
            after = [e for e in active if first is not None and e.start <= first < e.end]
            receipts.append({'kind': 'first_identifying_member_support', 'role': name, 'spelling': token,
                'span': {'start': support.q(start), 'end': support.q(end)},
                'first_positive_time': None if first is None else support.q(first),
                'arrival_event_ids': sorted(e.event_id for e in arrivals),
                'source_note_ids': {e.event_id: list(e.source_note_ids) for e in active},
                'delay_beats': support.q(delay), 'allowed_distributed_entry_beats': support.q(ALLOWANCE_BEATS),
                'normalized_raw_exposure': support.q(raw), 'normalized_exposure': support.q(value),
                'prepared_resolution_candidates': prepared,
                'held_across_arrival_ids': sorted({e.event_id for e in before} & {e.event_id for e in after}),
                'lost_spellings_at_arrival': sorted({e.pitch for e in before}-{e.pitch for e in after}),
                'gained_spellings_at_arrival': sorted({e.pitch for e in after}-{e.pitch for e in before}),
                'competing_explanations': ['distributed_or_omitted_member', 'later_harmony_change'] +
                    (['prepared_step_resolution'] if prepared else []),
                'member_never_observed': first is None, 'later_member_proves_earlier_sounding': False,
                'forced_boundary': False, 'pedal_confirmed': False, 'confirmed_nct': False,
                'source_labels_used': False, 'raw_nonmember_cost_removed': False})
    return sum(values, F())/len(identified), receipts


def features(problem, source, start, end, signature, *, context, index=None):
    old, details = support.support_features(problem, source, start, end, signature, index=index)
    new, receipt = timing_feature(problem, source, start, end, signature, context=context, index=index)
    return old | {FEATURE: new}, details+receipt


class Scorer(support.Scorer):
    def __init__(self, problem, ev, values=None, *, build_index=True, **args):
        self.timing_context = TimingContext(ev, **args)
        def bound_features(p, source, a, b, sig, *, index=None):
            return features(p, source, a, b, sig, context=self.timing_context, index=index)
        self.member_features = bound_features
        bind(support.Scorer.__init__, {'coefficients': coefficients, 'support_features': bound_features,
            'FEATURE_VERSION': FEATURE_VERSION})(self, problem, ev, values, build_index=build_index, **args)
        # The sealed integer decoder's scale covers quarter-normalized costs.
        # Beat-normalized costs across meter changes may add new denominators.
        # Enlarge only the private exact arithmetic scale, not the score.
        total = self.timing_context.extent(problem.points[0], problem.points[-1])
        units = [support.metric(ev.source, t)[1] for t in ev.source._measure_times]
        factor = lcm(total.numerator if total is not None else 1,
                     *(u.numerator for u in units if u is not None))
        def scale_lcm(*numbers): return lcm(*numbers, factor)
        reconstruction = bind(self.chosen.__globals__['original_decode'], {'lcm': scale_lcm})
        self.chosen = bind(self.chosen, {'lcm': scale_lcm, 'original_decode': reconstruction})

    def path_features(self, ids, *, indexed=False):
        return bind(support.Scorer.path_features, {'ZERO': ZERO, 'FEATURES': FEATURES,
            'support_features': self.member_features})(self, ids, indexed=indexed)

    def decode(self, *, transition_budget=2_000_000):
        result = bind(support.Scorer.decode, {'VERSION': VERSION, 'FEATURE_VERSION': FEATURE_VERSION})(
            self, transition_budget=transition_budget)
        result['member_timing_contract'] = {'version': VERSION, 'allowance_beats': support.q(ALLOWANCE_BEATS),
            'prepared_factor': support.q(PREPARED_FACTOR), 'raw_nonmember_cost_removed': False,
            'never_observed_members_charged_twice': False, 'recipe_penalty_used': False,
            'continuous_member_support_or_complete_nct_classifier': False,
            'same_original_candidates': True, 'source_labels_used': False, 'production_modified': False}
        return result
