"""Label-free, bounded source continuation of a terminal functional 6/4.

Evaluation scope ends are not necessarily musical boundaries. This evidence
uses the original following sounds, never the reference's following label.
It is a soft hypothesis score, not a cadence, modulation or inversion label.
"""
from fractions import Fraction as F

from .harmony_candidate_recall import rational as q
from .harmony_evidence_scoring import metric
from .harmony_functional_scoring import six_four_surface, interval_surface
from .harmony_reading_voice_context import spelled_height
from .harmony_temporal_scoring import beat_extent
from .seventh_context import chord

VERSION = 'harmony-terminal-source-context-0.1.0'
FEATURES = ('terminal_six_four_following_major_support',
            'terminal_six_four_following_upper_steps')
LOOKAHEAD_BEATS = F(2)


def horizon(source, start, beats):
    """Advance by exact local beats; no guessing an unknown meter."""
    now = start; remaining = beats
    for cut in sorted(t for t in source._measure_times if t > start):
        _, unit = metric(source, now)
        if unit is None: return None
        size = (cut-now)/unit
        if size >= remaining: return now+remaining*unit
        now = cut; remaining -= size
    _, unit = metric(source, now)
    return None if unit is None else now+remaining*unit


def observe(problem, ev, start, end, signature, *, history_gate=None):
    if not problem.points[0] <= start < end <= problem.points[-1]:
        raise ValueError('invalid_terminal_context_span')
    values = dict.fromkeys(FEATURES, F())
    receipt = dict(version=VERSION, span=dict(start=q(start), end=q(end)), signature=signature,
        source_ir_content_sha256=ev.source.source_ir_content_sha256,
        following_span=None, following_event_ids=[], source_note_ids={}, upper_event_pairs=[],
        following_union_is_simultaneous=False, selected_successor_used=False,
        source_labels_used=False, confirmed_function=False, confirmed_cadence=False,
        lookahead_beats=q(LOOKAHEAD_BEATS), score_scope_not_extended=True)
    def done(reason, unknown=False):
        if unknown: values.update(dict.fromkeys(FEATURES, None))
        receipt.update(reason=reason, features={k: None if v is None else q(v) for k, v in values.items()},
                       availability={k: v is not None for k, v in values.items()})
        return values, receipt
    if end != problem.points[-1]: return done('nonterminal_run_uses_selected_pair_context')
    surface = six_four_surface(signature)
    if surface is None: return done('not_a_functional_six_four_hypothesis')
    limit = horizon(ev.source, end, LOOKAHEAD_BEATS)
    if limit is None: return done('unknown_following_meter', True)
    receipt['following_span'] = dict(start=q(end), end=q(limit))
    # Full observation horizon required. A silent but covered horizon is known
    # absence; a truncated source cannot be presented as negative evidence.
    if max((r['end'] for r in ev.rows if r['start'] < r['end']), default=end) < limit:
        return done('source_ends_before_context_horizon', True)
    before = tuple(r for r in ev.rows if r['start'] < end and start < r['end'])
    following = tuple(r for r in ev.rows if r['start'] < limit and end < r['end'])
    receipt.update(following_event_ids=sorted(r['id'] for r in following),
        source_note_ids={r['id']: list(r['source_note_ids']) for r in (*before, *following)})
    if (any(not r['clock_valid'] or r['token'] is None for r in (*before, *following))
            or history_gate is not None and not history_gate(start, limit)):
        return done('unknown_full_source_pitch_voice_or_clock', True)
    root, members = signature; major = chord(root, 'M')
    third, fifth = map(tuple, major['members'][1:])
    left_cells = interval_surface(ev, start, end)
    right_cells = interval_surface(ev, end, limit)
    left_union = set().union(*(c[2] for c in left_cells)) if left_cells else set()
    right_union = set().union(*(c[2] for c in right_cells)) if right_cells else set()
    left_bass = any(c[3] == {root} for c in left_cells)
    right_bass = any(c[3] == {root} for c in right_cells)
    supported = set(members) <= left_union and {root, third, fifth} <= right_union and left_bass and right_bass
    receipt.update(surface_root_spelling=surface[0], analysis_root_spelling=root,
        expected_following_major_members=major['members'], left_surface_union_supported=set(members) <= left_union,
        left_root_lowest_observed=left_bass, following_root_lowest_observed=right_bass,
        following_major_union_supported={root, third, fifth} <= right_union,
        held_bass_confirmed=False, following_harmony_selected=False)
    if not supported: return done('insufficient_spelled_surface_bass_or_following_union')
    extent = beat_extent(ev.source, start, end)
    if extent is None: return done('unknown_left_meter', True)
    # Same one-beat saturation convention as old pair credit. A short run
    # receives proportional support, never a ban or a forced minimum length.
    scale = min(F(1), extent)
    values[FEATURES[0]] = scale
    four = next(p for p in members if ('CDEFGAB'.index(p[0])-'CDEFGAB'.index(root[0])) % 7 == 3)
    six = next(p for p in members if ('CDEFGAB'.index(p[0])-'CDEFGAB'.index(root[0])) % 7 == 5)
    # Existing links are unique, clock-consistent, nonoverlapping explicit
    # part/voice links. Do not invent a soprano line from polyphonic chords.
    pairs = [(p, n) for p, n in ev.links if start <= p['start'] < end <= n['start'] < limit
        and (p['token'], n['token']) in ((four, third), (six, fifth))
        and n['pitch']-p['pitch'] in (-1, -2)
        and spelled_height(n['pitch_data'])-spelled_height(p['pitch_data']) == -1]
    distinct = {p['token'] for p, n in pairs}
    values[FEATURES[1]] = scale*F(len(distinct), 2)
    receipt.update(upper_event_pairs=[[p['id'], n['id']] for p, n in pairs],
        distinct_upper_step_count=len(distinct), credit_scale=q(scale))
    return done('bounded_following_source_support_not_selected_harmony')
