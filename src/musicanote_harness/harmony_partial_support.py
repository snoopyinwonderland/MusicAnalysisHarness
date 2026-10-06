"""Independent temporal member, lowest-pitch and following-motion evidence.

Research hypotheses only. A union is not a simultaneous or selected chord,
lowest pitch is not structural bass, and a step is not a confirmed NCT label.
All clocks, spellings and source IDs are original; no reference labels enter.
"""
from fractions import Fraction as F

from .harmony_candidate_recall import rational as q
from .harmony_functional_scoring import interval_surface, six_four_surface
from .harmony_reading_voice_context import spelled_height
from .harmony_support_balance import roles
from .harmony_temporal_scoring import beat_extent
from .harmony_terminal_context import horizon
from .seventh_context import chord

VERSION = 'harmony-independent-partial-support-0.1.0'
FEATURES = ('observed_defining_member_window_dropout',
            'terminal_six_four_lowest_root_coverage',
            'terminal_six_four_following_member_fraction',
            'terminal_six_four_independent_upper_steps')
WINDOW_BEATS = F(2)


class Context:
    """Source-local immutable observations, cached by exact union-run span."""
    def __init__(self, problem, ev, *, history_gate=None):
        self.problem, self.ev, self.history_gate = problem, ev, history_gate
        self.span_cache = {}
        self.extent_cache = {}

    def extent(self, start, end):
        key = start, end
        if key not in self.extent_cache:
            self.extent_cache[key] = beat_extent(self.ev.source, start, end)
        return self.extent_cache[key]

    def span(self, start, end):
        key = start, end
        if key not in self.span_cache:
            active = tuple(r for r in self.ev.rows if r['start'] < r['end']
                           and r['start'] < end and start < r['end'])
            known = all(r['clock_valid'] and r['token'] is not None for r in active)
            if self.history_gate is not None and not self.history_gate(start, end): known = False
            cells = interval_surface(self.ev, start, end) if known else ()
            union = set().union(*(c[2] for c in cells)) if cells else set()
            self.span_cache[key] = active, known, cells, union
        return self.span_cache[key]

    def observe(self, start, end, signature):
        p, ev = self.problem, self.ev
        if not p.points[0] <= start < end <= p.points[-1]:
            raise ValueError('invalid_partial_support_span')
        values = dict.fromkeys(FEATURES, F())
        active, known, cells, union = self.span(start, end)
        receipt = dict(version=VERSION, span=dict(start=q(start), end=q(end)),
            signature=signature, source_ir_content_sha256=ev.source.source_ir_content_sha256,
            source_event_ids=sorted(r['id'] for r in active),
            source_note_ids={r['id']: list(r['source_note_ids']) for r in active},
            windows=[], following_span=None, following_event_ids=[], upper_event_pairs=[],
            source_labels_used=False, confirmed_nct=False, confirmed_boundary=False,
            function_confirmed=False, confirmed_cadence=False, held_bass_confirmed=False,
            structural_bass_confirmed=False, score_scope_extended=False,
            following_harmony_selected=False, union_is_simultaneous=False,
            member_window_beats=q(WINDOW_BEATS), feature_reasons={})

        def reason(keys, text, unavailable=False):
            for k in keys:
                receipt['feature_reasons'][k] = text
                if unavailable: values[k] = None

        defining = roles(signature)
        total = self.extent(p.points[0], p.points[-1])
        if defining is None:
            reason(FEATURES[:1], 'unsupported_literal_defining_roles', True)
        elif not known or total is None:
            reason(FEATURES[:1], 'unknown_source_pitch_clock_or_meter', True)
        else:
            expected = tuple(t for t in defining if t is not None)
            # Never-observed members already pay the old absence features.
            # Charge temporal dropout only for defining members heard here.
            observed = set(expected) & union
            receipt.update(defining_members=expected, observed_defining_members=sorted(observed),
                           never_heard_members_not_charged_again=sorted(set(expected)-union),
                           normalization_scope_beats=q(total))
            cursor = start
            while cursor < end:
                remaining = self.extent(cursor, end)
                limit = end if remaining is not None and remaining <= WINDOW_BEATS else horizon(ev.source, cursor, WINDOW_BEATS)
                if limit is None:
                    reason(FEATURES[:1], 'unknown_window_meter', True); break
                stop = min(end, limit)
                rows, valid, window_cells, tokens = self.span(cursor, stop)
                if not valid:
                    reason(FEATURES[:1], 'unknown_window_source', True); break
                missing = observed-tokens
                beats = self.extent(cursor, stop)
                contribution = (beats/total*F(len(missing), len(expected))
                                if tokens and expected else F())
                values[FEATURES[0]] += contribution
                receipt['windows'].append(dict(span=dict(start=q(cursor), end=q(stop)),
                    beats=q(beats), observed_spellings=sorted(tokens),
                    missing_previously_observed_defining_members=sorted(missing),
                    source_event_ids=sorted(r['id'] for r in rows),
                    feature=q(contribution), silence_not_charged=not bool(tokens),
                    performed_pedal_inferred=False))
                cursor = stop
            if FEATURES[0] not in receipt['feature_reasons']:
                reason(FEATURES[:1], 'two_beat_positive_sounding_union_windows_not_a_chord_ban')

        if end != p.points[-1]:
            reason(FEATURES[1:], 'internal_run_retains_old_selected_pair_evidence')
        elif six_four_surface(signature) is None:
            reason(FEATURES[1:], 'not_functional_six_four')
        else:
            limit = horizon(ev.source, end, WINDOW_BEATS)
            if limit is None or not known or self.extent(start, end) is None:
                reason(FEATURES[1:], 'unknown_terminal_source_or_meter', True)
            elif max((r['end'] for r in ev.rows if r['start'] < r['end']), default=end) < limit:
                reason(FEATURES[1:], 'source_ends_before_following_horizon', True)
            else:
                following, valid, next_cells, next_union = self.span(end, limit)
                receipt.update(following_span=dict(start=q(end), end=q(limit)),
                    following_event_ids=sorted(r['id'] for r in following))
                receipt['source_note_ids'].update({r['id']: list(r['source_note_ids']) for r in following})
                if not valid:
                    reason(FEATURES[1:], 'unknown_following_pitch_or_clock', True)
                else:
                    scale = min(F(1), self.extent(start, end))
                    root, members = signature
                    major = tuple(map(tuple, chord(root, 'M')['members']))
                    third, fifth = major[1:]
                    def coverage(surface, a, b):
                        return sum((y-x for x,y,tokens,low,rows in surface if low == {root}), F())/(b-a)
                    left_cov = coverage(cells, start, end)
                    right_cov = coverage(next_cells, end, limit)
                    values[FEATURES[1]] = scale*min(left_cov, right_cov)
                    values[FEATURES[2]] = scale*F(len(set(major)&next_union), len(major))
                    receipt.update(credit_scale=q(scale), left_lowest_root_coverage=q(left_cov),
                        following_lowest_root_coverage=q(right_cov),
                        expected_following_major_members=major,
                        observed_following_major_members=sorted(set(major)&next_union),
                        absent_following_major_members=sorted(set(major)-next_union),
                        all_support_dimensions_required=False)
                    four = next(t for t in members if ('CDEFGAB'.index(t[0])-'CDEFGAB'.index(root[0])) % 7 == 3)
                    six = next(t for t in members if ('CDEFGAB'.index(t[0])-'CDEFGAB'.index(root[0])) % 7 == 5)
                    upper = tuple(r for r in active if r['token'] in (four,six))
                    # Explicit polyphonic lanes cannot supply a unique path.
                    # Other dimensions remain known when this one is unknown.
                    ambiguous = any(r['identity'] == z['identity'] and r['id'] != z['id']
                        and r['start'] < z['end'] and z['start'] < r['end']
                        for r in upper for z in (*active,*following))
                    pairs = [(a,b) for a,b in ev.links
                        if start <= a['start'] < end <= b['start'] < limit
                        and (a['token'],b['token']) in ((four,third),(six,fifth))
                        and b['pitch']-a['pitch'] in (-1,-2)
                        and spelled_height(b['pitch_data'])-spelled_height(a['pitch_data']) == -1]
                    if ambiguous:
                        reason(FEATURES[3:], 'polyphonic_lane_direct_steps_unavailable', True)
                    else:
                        values[FEATURES[3]] = scale*F(len({a['token'] for a,b in pairs}),2)
                        receipt['upper_event_pairs'] = [[a['id'],b['id']] for a,b in pairs]
                        reason(FEATURES[3:], 'independent_direct_steps_not_gated_by_bass_or_complete_union')
                    reason(FEATURES[1:3], 'independent_partial_lowest_and_following_member_observations')
        receipt.update(features={k:None if v is None else q(v) for k,v in values.items()},
                       availability={k:v is not None for k,v in values.items()})
        return values, receipt


def observe(problem, ev, start, end, signature, *, history_gate=None):
    """Uncached source scan entry point for independent receipt checks."""
    return Context(problem, ev, history_gate=history_gate).observe(start,end,signature)
