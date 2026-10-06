"""Exact score-only projection of the sealed V2 context receipt.

The delayed DP, raw edges/cap, old26 and new7 coefficients do not change.
All winning-path explanations still use the ORIGINAL detailed implementation.
No float clock, inferred voice, unknown-as-zero, annotation or NCT decision.
"""
from bisect import bisect_right
from fractions import Fraction as F

from . import harmony_context_joint_decoder as sealed
from .harmony_temporal_scoring import beat_extent, resolution_features

VERSION = 'harmony-context-scalar-index-0.1.0'


class ScalarIndex:
    def __init__(self, scorer):
        self.sc = scorer; self.context = scorer.context; self.ev = scorer.ev
        if type(self.context) is not sealed.context_features.Context:
            raise ValueError('scalar_projection_requires_sealed_v2_context')
        a, b = scorer.problem.points[0], scorer.problem.points[-1]
        self.events = tuple(e for e in self.ev.source.events if e.start < b and a < e.end)
        cuts = sorted({a, b} | {t for e in self.events for t in (e.start, e.end) if a < t < b})
        self.cells = []
        for x, y in zip(cuts, cuts[1:]):
            active = [e for e in self.events if e.start < y and x < e.end]
            heights = {e.event_id: self.context.rows.get(e.event_id, {}).get('pitch') for e in active}
            known = not active or all(v is not None for v in heights.values())
            low = min(heights.values()) if active and known else None
            lowest = frozenset(k for k, v in heights.items() if low is not None and v == low)
            self.cells.append((x, y, known, lowest))
        self.starts = tuple(c[0] for c in self.cells)
        self.domains = {}; self.figures = {}; self.beats = {}; self.resolutions = {}; self.cache = {}
        self.stats = {'scalar_evaluations': 0, 'scalar_cache_hits': 0, 'domain_evaluations': 0,
                      'figure_domain_evaluations': 0, 'resolution_evaluations': 0,
                      'detailed_profiles_created_for_search': 0}

    def domain(self, start, end):
        key = start, end
        if key not in self.domains:
            observed = tuple(e for e in self.events if e.start < end and start < e.end)
            duration = {e.event_id: min(e.end, end)-max(e.start, start) for e in observed}
            cells = []
            i = max(0, bisect_right(self.starts, start)-1)
            while i < len(self.cells) and self.cells[i][0] < end:
                a, b, known, lowest = self.cells[i]
                if start < b: cells.append((min(b, end)-max(a, start), known, lowest))
                i += 1
            self.domains[key] = observed, duration, tuple(cells)
            self.stats['domain_evaluations'] += 1
        return self.domains[key]

    def local_beats(self, a, b):
        if (a, b) not in self.beats: self.beats[a, b] = beat_extent(self.ev.source, a, b)
        return self.beats[a, b]

    def figure_domain(self, a, start, end, context_end):
        key = a, start, end, context_end
        if key not in self.figures:
            found = []
            for _, seq in self.context.figures:
                if seq[0]['start'] < a or seq[-1]['end'] > context_end: continue
                anchors = (seq[0], seq[-1])
                if not all(r['start'] < context_end and a < r['end'] for r in anchors): continue
                affected = tuple(r['id'] for r in seq[1:-1] if r['start'] < end and start < r['end'])
                if not affected: continue
                found.append((tuple(r['token'] for r in anchors), tuple(r['token'] for r in seq[1:-1]),
                              affected, (seq[0]['start'], seq[-1]['end'])))
            self.figures[key] = tuple(found); self.stats['figure_domain_evaluations'] += 1
        return self.figures[key]

    def values(self, runs, index):
        if not 1 <= index < len(runs): raise ValueError('invalid_context_transition_index')
        local = tuple(runs[index-1:index+2])
        if (len(local) not in (2, 3) or any(a >= b for a, b, _ in local)
                or any(x[1] != y[0] for x, y in zip(local, local[1:]))
                or local[0][0] < self.sc.problem.points[0] or local[-1][1] > self.sc.problem.points[-1]):
            raise ValueError('scalar_projection_requires_contiguous_in_scope_runs')
        a, start, left = local[0]; _, end, selected = local[1]; context_end = local[-1][1]
        # V2's next signature affects explanations ONLY, not scalar membership
        # or vetoes. Preserve its complete end, not just its first raw edge.
        key = a, start, end, context_end, left, selected
        if key in self.cache:
            self.stats['scalar_cache_hits'] += 1; return self.cache[key]
        lm, rm = set(left[1]), set(selected[1]); explained = set()
        for anchors, middle, affected, span in self.figure_domain(a, start, end, context_end):
            if not all(t in lm for t in anchors) or any(t in lm for t in middle): continue
            if self.context.history_gate is not None:
                if span not in self.context.history_cache: self.context.history_cache[span] = self.context.history_gate(*span)
                if not self.context.history_cache[span]: continue
            explained.update(affected)
        observed, duration, cells = self.domain(start, end)
        pitch_known = all(e.pitch is not None for e in observed)
        voice_unknown = any(e.pitch not in lm and ((r := self.context.rows.get(e.event_id)) is None
            or not r['clock_valid'] or r['identity'] is None or r['id'] in self.context.ambiguous) for e in observed)
        foreign = {e.event_id for e in observed if e.pitch is not None and e.pitch not in lm}
        reassigned = {e.event_id for e in observed if e.event_id in explained and e.pitch in rm}
        new = {e.event_id for e in observed if start <= e.start < end and e.pitch in rm-lm and e.event_id not in explained}
        held = {e.event_id for e in observed if e.start < start < e.end and e.pitch in lm}
        bass_known = all(known for _, known, _ in cells)
        bass = sum((d for d, known, lowest in cells if known and lowest & held), F())
        credit = F()
        if explained:
            k = a, start, end, left, selected
            if k not in self.resolutions:
                self.resolutions[k] = resolution_features(self.ev, a, start, end, left, selected)
                self.stats['resolution_evaluations'] += 1
            pair_values, details = self.resolutions[k]
            suffixes = {'dominant_family_leading_tone': '_leading_tone_to_selected_target',
                        'dominant_family_seventh_step': '_seventh_to_selected_member'}
            credit = sum((pair_values[k] for k, suffix in suffixes.items()
                if any(set(p) & explained for d in details if d['kind'].endswith(suffix)
                       for p in d.get('source_event_pairs', ()))), F())
        pattern_known = pitch_known and not voice_unknown
        names = sealed.FEATURES
        observed_values = dict(zip(names, (
            sum((duration[i] for i in explained), F())/self.sc.total,
            sum((duration[i] for i in foreign-explained), F())/self.sc.total,
            sum((duration[i] for i in reassigned), F())/self.sc.total,
            sum((duration[i] for i in new), F())/self.sc.total,
            sum((duration[i] for i in held), F())/self.sc.total,
            bass/self.sc.width, credit)))
        available = {k: pattern_known if k in names[:4] else
            (pattern_known and self.local_beats(a, start) is not None) if k == names[-1] else
            (pitch_known and (bass_known if k == names[-2] else True)) for k in names}
        result = {'observed_feature_sums': observed_values, 'availability': available,
                  'features': {k: v if available[k] else None for k, v in observed_values.items()}}
        self.cache[key] = result; self.stats['scalar_evaluations'] += 1
        return result


class Scorer(sealed.Scorer):
    """Inherit the EXACT sealed DP; replace score projection only, lazily.

    Original path_receipt/transition_profile independently reconstruct the
    winner and assert its detailed cost equals the optimized search cost.
    """
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw); self.scalar_index = None

    def scalar_values(self, runs, index):
        if self.scalar_index is None: self.scalar_index = ScalarIndex(self)
        return self.scalar_index.values(runs, index)

    def transition_cost(self, runs, index):
        values = self.scalar_values(runs, index)['features']
        return sum((self.weights[k]*v for k, v in values.items() if v is not None), F())

    def decode(self, **kwargs):
        result = super().decode(**kwargs)
        result['scalar_projection_contract'] = {'version': VERSION, 'sealed_dp_unchanged': True,
            'raw_operation_unit_unchanged': True, 'detailed_winner_replay_unchanged': True,
            'candidate_graph_and_all_coefficients_unchanged': True, 'annotations_used': False,
            'unknowns_imputed_as_observed_zero': False, 'production_modified': False}
        result['scalar_projection_diagnostics'] = dict(self.scalar_index.stats) if self.scalar_index else {}
        return result
