"""Label-blind support of a selected harmonic transition, NOT a new score.

Keep actual sounding events, spelling, clocks and source IDs. Observe the
complete right run as well as its first local beat: a distributed chord need
not be a complete vertical stack at its onset. No hard filter, NCT label,
reference input, probability or weight change is introduced here.
"""
from fractions import Fraction as F

from .harmony_candidate_recall import rational as q
from .harmony_evidence_scoring import metric
from .harmony_functional_scoring import PAIR_WEIGHTS, pair_features
from .harmony_temporal_scoring import beat_extent, resolution_features

VERSION = 'harmony-transition-support-observation-0.1.0'


def first_beat_end(source, start, end):
    """Cap at the completed run, integrating changing local beat units."""
    if not start < end: raise ValueError('invalid_support_span')
    cuts = [start]+[t for t in source._measure_times if start < t < end]+[end]
    remaining = F(1)
    for a, b in zip(cuts, cuts[1:]):
        _, unit = metric(source, a)
        if unit is None: return None
        if (b-a)/unit >= remaining: return a+remaining*unit
        remaining -= (b-a)/unit
    return end


def window(ev, start, end, left, right):
    """Raw observed unions and exact time coverage; unknowns stay unavailable.

    Two members is an observation threshold, NOT a harmony confirmation gate.
    An octave doubling does not supply another spelled member. Empty sound is
    known zero; an unresolved pitch is not. All original events are retained.
    """
    if not start < end: raise ValueError('invalid_support_span')
    rows = {r['id']: r for r in ev.rows}
    events = sorted((e for e in ev.source.events if e.start < end and start < e.end),
                    key=lambda e: (e.start, e.end, e.event_id))
    lm, rm = set(left[1]), set(right[1]); exclusive = rm-lm
    cuts = sorted({start, end} | {t for e in events for t in (e.start, e.end) if start < t < end})
    totals = dict.fromkeys(('silence', 'left_two', 'right_two', 'right_only_two',
                            'left_only_two', 'exclusive_present', 'right_bass', 'left_bass'), F())
    unresolved = False; bass_unknown = False; cells = []
    observed = set(); max_exclusive = 0
    for a, b in zip(cuts, cuts[1:]):
        active = [e for e in events if e.start < b and a < e.end]
        tokens = {e.pitch for e in active if e.pitch is not None}; observed |= tokens
        known = not any(e.pitch is None for e in active); unresolved |= not known
        heights = {e.event_id: rows.get(e.event_id, {}).get('pitch') for e in active}
        bass_known = not active or all(v is not None for v in heights.values())
        bass_unknown |= not bass_known
        lowest = min(heights.values()) if active and bass_known else None
        bass_ids = sorted(k for k, v in heights.items() if lowest is not None and v == lowest)
        bass_tokens = {e.pitch for e in active if e.event_id in bass_ids and e.pitch is not None}
        nl, nr, nx = len(tokens & lm), len(tokens & rm), len(tokens & exclusive)
        max_exclusive = max(max_exclusive, nx)
        values = {'silence': not active, 'left_two': nl >= 2, 'right_two': nr >= 2,
                  'right_only_two': nr >= 2 and nl < 2, 'left_only_two': nl >= 2 and nr < 2,
                  'exclusive_present': nx > 0, 'right_bass': bool(bass_tokens & rm),
                  'left_bass': bool(bass_tokens & lm)}
        for k, yes in values.items(): totals[k] += (b-a)*yes
        cells.append({'span': {'start': q(a), 'end': q(b)},
            'active_sounding_event_ids': sorted(e.event_id for e in active),
            'observed_spelled_tokens': sorted(tokens), 'spelling_available': known,
            'lowest_sounding_event_ids': bass_ids, 'lowest_spelled_tokens': sorted(bass_tokens),
            'lowest_pitch_available': bass_known,
            'left_member_count': nl if known else None, 'right_member_count': nr if known else None,
            'right_exclusive_member_count': nx if known else None})
    coverage = {k: q(v/(end-start)) if not unresolved and (k not in ('left_bass', 'right_bass') or not bass_unknown)
                else None for k, v in totals.items()}
    return {'span': {'start': q(start), 'end': q(end)}, 'beat_extent':
        None if (beats := beat_extent(ev.source, start, end)) is None else q(beats),
        'spelling_available': not unresolved, 'observed_spelled_tokens': sorted(observed),
        'right_union_member_count': len(observed & rm) if not unresolved else None,
        'right_union_exclusive_count': len(observed & exclusive) if not unresolved else None,
        'right_missing_spelled_members': sorted(rm-observed) if not unresolved else None,
        'right_max_simultaneous_exclusive_count': max_exclusive if not unresolved else None,
        'coverage': coverage, 'cells': cells,
        'events': [{'sounding_event_id': e.event_id, 'source_note_ids': list(e.source_note_ids),
            'source_span': {'start': q(e.start), 'end': q(e.end)}, 'spelled_pitch': e.pitch,
            'source_identity': rows.get(e.event_id, {}).get('identity'),
            'explicit_voice_clock_available': rows.get(e.event_id, {}).get('clock_valid', False),
            'new_attack_in_window': start <= e.start < end,
            'held_across_window_start': e.start < start < e.end} for e in events]}


def completed_runs(problem, ids):
    by_id = {e.group_id: e for e in problem.edges}
    if not ids or len(ids) > problem.max_segments or any(i not in by_id for i in ids):
        raise ValueError('invalid_existing_support_path')
    edges = [by_id[i] for i in ids]
    if (edges[0].start != problem.points[0] or edges[-1].end != problem.points[-1]
            or any(a.end != b.start for a, b in zip(edges, edges[1:]))):
        raise ValueError('invalid_existing_support_path')
    runs = []
    for e in edges:
        if runs and runs[-1][2] == e.signature: runs[-1] = runs[-1][0], e.end, e.signature
        else: runs.append((e.start, e.end, e.signature))
    return runs


def observe_path(problem, ev, ids):
    """Scorer-independent evidence for complete ORIGINAL candidate paths."""
    runs = completed_runs(problem, ids); transitions = []
    for (a, b, left), (c, d, right) in zip(runs, runs[1:]):
        if b != c: raise ValueError('noncontiguous_completed_support_runs')
        raw, _ = pair_features(ev, a, b, d, left, right)
        credited, details = resolution_features(ev, a, b, d, left, right)
        arrival_end = first_beat_end(ev.source, b, d)
        full = window(ev, b, d, left, right)
        arrival = window(ev, b, arrival_end, left, right) if arrival_end is not None else None
        held_common = sorted(e.event_id for e in ev.source.events
            if e.start < b < e.end and e.pitch is not None and e.pitch in set(left[1]) & set(right[1]))
        transitions.append({'boundary': q(b), 'left_span': {'start': q(a), 'end': q(b)},
            'left_signature': left, 'right_signature': right,
            'raw_resolution_features': {k: q(raw[k]) for k in PAIR_WEIGHTS},
            'credited_resolution_features': {k: q(credited[k]) for k in PAIR_WEIGHTS},
            'resolution_details': details, 'right_first_beat': arrival, 'right_complete_run': full,
            'held_common_event_ids': held_common,
            'new_attacked_right_member_ids': sorted(e.event_id for e in ev.source.events
                if b <= e.start < d and e.pitch is not None and e.pitch in right[1]),
            'harmony_change_confirmed': False, 'nct_confirmed': False})
    return {'version': VERSION, 'source_ir_content_sha256': ev.source.source_ir_content_sha256,
        'completed_runs': [{'span': {'start': q(a), 'end': q(b)}, 'signature': sig} for a, b, sig in runs],
        'transitions': transitions, 'source_labels_used': False,
        'score_changed': False, 'source_modified': False,
        'arrival_contract': 'up_to_one_integrated_local_beat_capped_at_complete_right_run',
        'unknown_meter_policy': 'arrival_unavailable_complete_run_still_observed',
        'two_members_are_not_a_hard_harmony_gate': True}
