"""Soft, source-bound extension/change interactions for joint research scoring.

An attacked new member can extend the PREVIOUS surface triad by a seventh,
or supply a durable, unexplained non-extension change. These are competing
score features, not confirmed harmony/NCT labels or seventh-preservation gates.
Old26 and old7 remain separate. Reuse the sealed three-run exact search.
"""
from fractions import Fraction as F
from functools import lru_cache

from . import harmony_context_scalar_index as parent
from .harmony_functional_scoring import shapes, six_four_surface
from .seventh_context import chord, QUALITIES
from .harmony_temporal_scoring import beat_extent

VERSION = 'harmony-member-role-interactions-0.1.0'
FEATURES = ('supported_surface_seventh_extension_attack_exposure',
            'durable_nonextension_change_attack_coverage')
ZERO = dict.fromkeys(FEATURES, F())
q, f = parent.sealed.q, parent.sealed.f


def coefficients(values):
    result = dict(values)
    if set(result) != set(FEATURES) or any(type(v) is not F or not -2 <= v <= 2 for v in result.values()):
        raise ValueError('invalid_member_role_coefficients')
    return result


@lru_cache(maxsize=8192)
def surface_roles(signature):
    """Literal shape and functional-root alternative coexist, never overwrite.

    An unsupported/non-tertian signature has unavailable extension semantics.
    A known seventh has an empty *triad-extension* domain, not a missing value.
    """
    root, members = signature
    literal = root
    qualities = shapes(signature)
    basis = 'literal_candidate_root'
    if not qualities and (surface := six_four_surface(signature)):
        literal, quality = surface
        qualities = (quality,)
        basis = 'six_four_surface_root_distinct_from_analysis_root'
    if not qualities:
        return None
    thirds, extensions = set(), set()
    if len(members) == 3:
        for quality in qualities:
            c = chord(literal, quality)
            thirds.add(tuple(c['members'][1]))
            for seventh_quality, intervals in QUALITIES.items():
                if len(intervals) != 3:
                    continue
                seven = chord(literal, seventh_quality)
                if tuple(sorted(map(tuple, seven['members'][:3]))) == members:
                    extensions.add(tuple(seven['members'][3]))
    return literal, tuple(sorted(thirds)), tuple(sorted(extensions)), basis


def union_width(intervals):
    end = None; total = F()
    for a, b in sorted(intervals):
        if a >= b:
            raise ValueError('nonpositive_member_role_interval')
        total += max(F(), b-max(a, end)) if end is not None else b-a
        end = b if end is None else max(end, b)
    return total


class RoleIndex:
    def __init__(self, scorer):
        self.sc = scorer
        self.cache = {}; self.beats = {}

    def observe(self, runs, index, *, detailed=False):
        sc = self.sc
        # Also validates contiguous, positive, in-scope two/three-run geometry.
        old = sc.scalar_values(runs, index)
        if sc.scalar_index is None:
            raise ValueError('missing_member_role_scalar_index')
        local = tuple(runs[index-1:index+2]); key = local
        if not detailed and key in self.cache:
            return self.cache[key]
        a, start, left = local[0]; _, end, right = local[1]
        si = sc.scalar_index; lm, rm = set(left[1]), set(right[1])
        if detailed:
            # Reconstruct with ORIGINAL detailed V2 explanation, not scalar IDs.
            explained = set(sc.transition_profile(runs, index)['explained_event_ids'])
            previous = tuple(e for e in sc.ev.source.events if e.start < start and a < e.end)
            observed = tuple(e for e in sc.ev.source.events if e.start < end and start < e.end)
        else:
            explained = set()
            for anchors, middle, affected, span in si.figure_domain(a, start, end, local[-1][1]):
                if not all(t in lm for t in anchors) or any(t in lm for t in middle):
                    continue
                if sc.context.history_gate is not None:
                    if span not in sc.context.history_cache:
                        sc.context.history_cache[span] = sc.context.history_gate(*span)
                    if not sc.context.history_cache[span]:
                        continue
                explained.update(affected)
            previous = si.domain(a, start)[0]; observed = si.domain(start, end)[0]
        zero_ids = sorted(e.event_id for e in (*previous, *observed) if e.start == e.end)
        previous = tuple(e for e in previous if max(e.start, a) < min(e.end, start))
        observed = tuple(e for e in observed if max(e.start, start) < min(e.end, end))
        roles = surface_roles(left)
        left_known = all(e.pitch is not None for e in previous)
        pattern_known = old['availability'][parent.sealed.FEATURES[0]] and left_known and roles is not None
        tokens = {e.pitch for e in previous if e.pitch is not None}
        supported = bool(roles and roles[0] in tokens and any(t in tokens for t in roles[1]))
        extensions = set(roles[2]) if supported else set()
        new = tuple(e for e in observed if start <= e.start < end and e.pitch in rm-lm
                    and e.event_id not in explained)
        extend = tuple(e for e in new if e.pitch in extensions)
        durable = []; unknown_duration = False
        for e in new:
            if e.pitch in extensions:
                continue
            k = e.start, e.end
            if k not in self.beats:
                self.beats[k] = beat_extent(sc.ev.source, *k)
            beats = self.beats[k]
            if beats is None:
                unknown_duration = True
            elif beats >= 1:
                durable.append(e)
        values = dict(zip(FEATURES, (
            sum((min(e.end, end)-max(e.start, start) for e in extend), F())/sc.total,
            union_width([(max(e.start, start), min(e.end, end)) for e in durable])/sc.width)))
        available = {FEATURES[0]: pattern_known,
                     FEATURES[1]: pattern_known and not unknown_duration}
        result = {'observed_feature_sums': values, 'availability': available,
                  'features': {k: v if available[k] else None for k, v in values.items()}}
        if detailed:
            def public(e, window_start=start, window_end=end):
                row = sc.context.rows.get(e.event_id, {})
                return {'sounding_event_id': e.event_id, 'source_note_ids': list(e.source_note_ids),
                    'spelling': e.pitch, 'source_span': {'start': q(e.start), 'end': q(e.end)},
                    'in_run_span': {'start': q(max(e.start, window_start)), 'end': q(min(e.end, window_end))},
                    'voice_identity': row.get('identity'), 'source_clock_valid': row.get('clock_valid', False),
                    'full_original_duration_beats': None if (v := beat_extent(sc.ev.source, e.start, e.end)) is None else q(v)}
            result |= {'left_signature': left, 'right_signature': right,
                'left_span': {'start': q(a), 'end': q(start)}, 'right_span': {'start': q(start), 'end': q(end)},
                'surface_roles': roles, 'surface_root_and_third_observed_in_left_union': supported,
                'left_union_is_vertical_stack': False,
                'support_source_events': [public(e, a, start) for e in previous if roles and e.pitch in {roles[0], *roles[1]}],
                'new_unexplained_exclusive_attacks': [public(e) for e in new],
                'potential_extension_events': [public(e) for e in extend],
                'durable_nonextension_events': [public(e) for e in durable],
                'zero_duration_source_ids_retained_not_scored': sorted(set(zero_ids)),
                'conditional_explained_ids': sorted(explained), 'confirmed_extension': False,
                'harmony_change_confirmed': False, 'nct_confirmed': False, 'source_labels_used': False,
                'seventh_always_held': False, 'doublings_inflate_durable_coverage': False}
        else:
            self.cache[key] = result
        return result


class Scorer(parent.Scorer):
    def __init__(self, original, context_weights, role_weights, **kwargs):
        super().__init__(original, context_weights, **kwargs)
        self.role_weights = coefficients(role_weights); self.role_index = RoleIndex(self)

    def transition_cost(self, runs, index):
        base = super().transition_cost(runs, index)
        values = self.role_index.observe(runs, index)['features']
        return base+sum((self.role_weights[k]*v for k, v in values.items() if v is not None), F())

    def path_receipt(self, ids, *, target=False):
        receipt = super().path_receipt(ids, target=target)
        runs = parent.sealed.context_features.control.completed_runs(self.problem, ids)
        profiles = [self.role_index.observe(runs, i, detailed=True) for i in range(1, len(runs))]
        known = {k: sum((p['features'][k] for p in profiles if p['features'][k] is not None), F()) for k in FEATURES}
        observed = {k: sum((p['observed_feature_sums'][k] for p in profiles), F()) for k in FEATURES}
        availability = {k: all(p['availability'][k] for p in profiles) for k in FEATURES}
        terms = {k: known[k]*self.role_weights[k] for k in FEATURES}; added = sum(terms.values(), F())
        for p in profiles:
            for key in ('features', 'observed_feature_sums'):
                p[key] = {k: None if v is None else q(v) for k, v in p[key].items()}
        receipt |= {'member_role_version': VERSION, 'parent_score_cost': receipt['cost'],
            'member_role_cost': q(added), 'cost': q(f(receipt['cost'])+added),
            'member_role': {'transitions': profiles, 'coefficients': {k: q(v) for k, v in self.role_weights.items()},
                'scored_available_feature_sums': {k: q(v) for k, v in known.items()},
                'observed_feature_sums': {k: q(v) for k, v in observed.items()},
                'availability': availability, 'features': {k: q(known[k]) if availability[k] else None for k in FEATURES},
                'term_costs': {k: q(v) for k, v in terms.items()}}, 'production_modified': False}
        return receipt

    def decode(self, **kwargs):
        if any(self.role_weights.values()):
            kwargs['force_delayed'] = True
        result = super().decode(**kwargs)
        result['member_role_contract'] = {'version': VERSION, 'old26_and_old7_frozen': True,
            'new_score_features': FEATURES, 'candidate_graph_unchanged': True, 'raw_cap_unchanged': True,
            'retained_union_runs': 3, 'source_labels_used': False, 'hard_seventh_preservation': False,
            'production_modified': False}
        # Parent projection is sealed; these two new terms are NOT unchanged coefficients.
        result['scalar_projection_contract']['candidate_graph_and_all_coefficients_unchanged'] = False
        if result['selected']:
            result['selected']['proposal_id'] = 'member_role_'+parent.sealed._hash(
                [result['selected']['context_score']['existing_path_ids'], {k: q(v) for k, v in self.role_weights.items()}])[:20]
        return result
