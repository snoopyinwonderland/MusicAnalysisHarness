"""Bounded attack/release context of frozen chord alternatives, not prolongation.

Membership outside the arrival is explicitly a counterfactual application of
the arrival candidate. It never extends that candidate's asserted time range.
"""
from collections import Counter
from fractions import Fraction
from itertools import product

from .formal_ir import q
from .harmony_joint import f
from .harmony_candidate_explanation import spelling_evidence
from .harmony_reading_voice_context import spelled_height

VERSION = 'attack-release-context-0.1.0'
BUCKETS = ('shared_member', 'left_member_only', 'right_member_only', 'neither_member', 'spelling_unresolved')


def observe(ir, contrast, contexts):
    sounds = {s['sounding_event_id']: s for s in ir['sounding_events']}
    notes = {n['note_id']: n for n in ir['note_events']}
    spans = sorted(set((f(c['start']), f(c['end'])) for c in contexts))
    if any(a < 0 or b <= a for a, b in spans):
        raise ValueError('invalid_context')
    meters = ir.get('measures', [])
    rows = []; units = {}

    def lane(s):
        ns = [notes.get(n) for n in s['source_note_ids']]
        keys = {(n.get('part_id'), n.get('voice_id')) for n in ns if n}
        return next(iter(keys)) if ns and all(ns) and len(keys) == 1 and all(next(iter(keys))) else None

    for row in contrast['records']:
        if 'comparison_span' not in row:
            rows.append({'path_id': row['path_id'], 'status': 'no_arrival_span', 'pairs': []})
            continue
        a, b = (f(row['comparison_span'][k]) for k in ('start', 'end'))
        current = [m for m in meters if f(m['global_start_quarter']) <= a]
        latest = max((f(m['global_start_quarter']) for m in current), default=None)
        signatures = {str(m.get('time_signature')) for m in current if f(m['global_start_quarter']) == latest}
        meter = next((m for m in current if f(m['global_start_quarter']) == latest), {})
        denom = meter.get('time_signature', {}).get('beat_type')
        base = {'path_id': row['path_id'], 'arrival_span': row['comparison_span'],
                'selected': None, 'used_for_ranking': False, 'pairs': []}
        containing = [(x, y) for x, y in spans if x <= a and b <= y]
        if not denom or denom <= 0 or len(signatures) != 1 or not containing:
            rows.append({**base, 'status': 'meter_or_frozen_context_unavailable'}); continue
        unit = Fraction(4, denom)
        want_a, want_b = a-unit, b+unit
        # Use ONE context, never stitch disjoint/overlapping frozen contexts.
        ca, cb = min(containing, key=lambda c: (-(min(c[1], want_b)-max(c[0], want_a)), c))
        x, y = max(ca, want_a), min(cb, want_b)
        full = x == want_a and y == want_b
        blockers = list(row.get('path_abstentions', []))
        if not full: blockers.append('one_denominator_beat_context_truncated')
        preceding = [m for m in meters if f(m['global_start_quarter']) <= x]
        preceding_start = max((f(m['global_start_quarter']) for m in preceding), default=None)
        if not preceding or any(m['time_signature'] != meter['time_signature'] for m in preceding if f(m['global_start_quarter']) == preceding_start):
            blockers.append('meter_change_or_unknown_before_arrival')
        for m in meters:
            t = f(m['global_start_quarter'])
            if x < t < y and m['time_signature'] != meter['time_signature']:
                blockers.append('meter_change')
            bar = m.get('repeat_barline') or {}
            bt = t + (0 if bar.get('location') == 'left' else f(m['actual_duration_quarter']))
            if x < bt < y and any(bar.get(k) for k in ('repeat_direction', 'ending_number')):
                blockers.append('repeat_or_ending_barrier')
        active = sorted((s for s in sounds.values() if f(s['span']['start']) < y and f(s['span']['end']) > x), key=lambda s: (f(s['span']['start']), s['sounding_event_id']))
        invalid = [s['sounding_event_id'] for s in active if f(s['span']['end']) <= f(s['span']['start']) or spelled_height(s['pitch']) is None]
        if invalid: blockers.append('unsupported_duration_or_pitch')
        grace = [n['note_id'] for n in notes.values() if n.get('grace', {}).get('is_grace') and x <= f(n['global_onset_quarter']) < y]
        if grace: blockers.append('grace_timing_unresolved')
        bounds = {'before': (x, a), 'arrival': (a, b), 'after': (b, y)}
        windows = {}
        for name, (lo, hi) in bounds.items():
            ids = [s['sounding_event_id'] for s in active if lo < hi and f(s['span']['start']) < hi and f(s['span']['end']) > lo]
            rests = [r['rest_id'] for r in ir.get('rest_events', []) if lo < hi and f(r['global_onset_quarter']) < hi and f(r['global_onset_quarter'])+f(r['notated_duration_quarter']) > lo]
            silence = []; cursor = lo
            for start, end in sorted((max(lo, f(sounds[i]['span']['start'])), min(hi, f(sounds[i]['span']['end']))) for i in ids):
                if start > cursor: silence.append({'start': q(cursor), 'end': q(start)})
                cursor = max(cursor, end)
            if cursor < hi: silence.append({'start': q(cursor), 'end': q(hi)})
            windows[name] = {'span': {'start': q(lo), 'end': q(hi)}, 'event_refs': ids,
                'available': lo < hi, 'complete_requested_window': name == 'arrival' or (lo == want_a if name == 'before' else hi == want_b),
                'rest_refs': rests, 'all_voice_notated_silence': silence}
        boundaries = []
        for name, t in [('arrival_start', a), ('arrival_end', b)]:
            buckets = {k: [] for k in ('held_across', 'released_at', 'attacked_at', 'released_before', 'attacked_after')}
            for s in active:
                lo, hi = f(s['span']['start']), f(s['span']['end']); sid = s['sounding_event_id']
                if lo < t < hi: buckets['held_across'].append(sid)
                if hi == t: buckets['released_at'].append(sid)
                if lo == t: buckets['attacked_at'].append(sid)
                if hi < t: buckets['released_before'].append(sid)
                if lo > t: buckets['attacked_after'].append(sid)
            # Reattack is not a held sound or confirmed contrapuntal identity.
            returns = []
            before = [s for s in active if f(s['span']['end']) <= t]
            after = [s for s in active if f(s['span']['start']) >= t]
            for src, dst in product(before, after):
                if lane(src) and lane(src) == lane(dst) and spelled_height(src['pitch']) is not None and spelled_height(src['pitch']) == spelled_height(dst['pitch']) and src['pitch']['midi_pitch'] == dst['pitch']['midi_pitch']:
                    returns.append({'event_refs': [src['sounding_event_id'], dst['sounding_event_id']],
                        'gap_quarters': q(f(dst['span']['start'])-f(src['span']['end'])), 'same_notated_lane': True,
                        'confirmed_voice_connection': False, 'continuous_sound': False})
            boundaries.append({'name': name, 'time': q(t), **buckets, 'same_spelled_pitch_reattack_pairs': returns})
        for s in active:
            sid = s['sounding_event_id']
            units[sid] = {'source_note_ids': s['source_note_ids'], 'pitch': s['pitch'], 'original_span': s['span'], 'independent_vote': False}
        # Freeze root spelling from arrival. New outside pitches cannot introduce
        # a convenient enharmonic root to manufacture additional support.
        conditions = {}
        context_span = {'start': q(x), 'end': q(y)}
        for c in row['conditions']:
            evidence = spelling_evidence(ir, context_span, c['candidate'])
            roots = [r for r in evidence['candidates'] if r['root_spelling'] in c['root_spelling_support']]
            members = {s['sounding_event_id'] for s in active if s['pitch']['midi_pitch'] % 12 in c['candidate']['pcs']}
            consistent = bool(roots) and any(members <= set(r['supported_event_refs']) for r in roots)
            support = set().union(*(set(r['supported_event_refs']) for r in roots))
            conditions[c['candidate_key']] = {'candidate': c['candidate'], 'root_spellings': [r['root_spelling'] for r in roots],
                'support': support, 'consistent': consistent}
        pairs = []
        for p in row['pairs']:
            l, r = conditions[p['left']], conditions[p['right']]
            memberships = {}
            for name, w in windows.items():
                buckets = {k: [] for k in BUCKETS}
                for sid in w['event_refs']:
                    pc = sounds[sid]['pitch']['midi_pitch'] % 12
                    lm, rm = pc in l['candidate']['pcs'], pc in r['candidate']['pcs']
                    uncertain = spelled_height(sounds[sid]['pitch']) is None or (lm and sid not in l['support']) or (rm and sid not in r['support'])
                    k = 'spelling_unresolved' if uncertain else 'shared_member' if lm and rm else 'left_member_only' if lm else 'right_member_only' if rm else 'neither_member'
                    buckets[k].append(sid)
                memberships[name] = buckets
            prior, following = memberships['before'], memberships['after']
            switch = ((bool(prior['left_member_only']) and not prior['right_member_only'] and bool(following['right_member_only']) and not following['left_member_only']) or
                      (bool(prior['right_member_only']) and not prior['left_member_only'] and bool(following['left_member_only']) and not following['right_member_only']))
            uncertain = not l['consistent'] or not r['consistent'] or any(v['spelling_unresolved'] for v in memberships.values())
            status = ('context_unresolved' if blockers else 'spelling_unresolved' if uncertain else 'exclusive_membership_switch_not_harmonic_change' if switch else 'observed_context_no_decision')
            pairs.append({'left': p['left'], 'right': p['right'], 'status': status,
                'window_memberships': memberships, 'outside_membership_is_counterfactual': True,
                'hypotheses': [{'type': 'harmonic_continuation', 'selected': None}, {'type': 'harmonic_change', 'selected': None}],
                'selected': None, 'ranking_weight': None, 'independent_vote': False})
        rows.append({**base, 'status': 'observed', 'context_span': context_span, 'frozen_context': {'start': q(ca), 'end': q(cb)},
            'beat_unit_quarter': q(unit), 'unit_kind': 'denominator_beat_not_inferred_tactus', 'windows': windows,
            'boundaries': boundaries, 'abstention_reasons': sorted(set(blockers)), 'grace_refs': grace,
            'unsupported_refs': invalid, 'pairs': pairs})
    return {'version': VERSION, 'records': rows, 'event_units': units,
        'summary': {'paths': len(rows), 'observed_paths': sum(r['status'] == 'observed' for r in rows),
            'pair_statuses_not_votes': dict(Counter(p['status'] for r in rows for p in r['pairs']))},
        'source_annotation_used': False, 'production_modified': False,
        'limits': ['Sounding duration is notated, not acoustic/pedal duration.',
            'Held sound does not prove harmonic prolongation; reattack does not prove change.',
            'Outside membership tests frozen arrival candidates counterfactually, not as labels of those windows.',
            'One denominator beat on each side; incomplete contexts never establish absence.',
            'No continuation/change winner, NCT classification, confidence or ranking weight.']}
