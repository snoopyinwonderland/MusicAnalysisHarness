"""Three-completed-run hold/change feature contract, not confirmed NCT labels.

Compare the actually selected right chord with continuation of the actually
selected left chord. Explicit contiguous lanes supply passing/neighbor/double
neighbor geometry. Other voices remain in the residual: a melodic neighbor
does not imply that the harmony held. No duration/metric hard gate is imposed.
No candidate, source sound, existing cost, or annotation is changed.
"""
from collections import defaultdict
from fractions import Fraction as F

from .harmony_candidate_recall import fraction as f, rational as q
from .harmony_evidence_scoring import metric
from .harmony_reading_voice_context import spelled_height
from .harmony_transition_support import completed_runs, window
from .harmony_temporal_scoring import beat_extent, resolution_features

VERSION = 'harmony-three-run-context-competition-0.1.0'
FEATURES = ('hold_explained_step_exposure', 'hold_remaining_nonmember_exposure',
    'reclassified_ornament_member_exposure', 'selected_new_exclusive_unassigned_exposure',
    'continuing_left_member_exposure', 'continuing_left_lowest_coverage',
    'dominant_credit_with_hold_conflict')


def step(a, b):
    ha, hb = spelled_height(a['pitch_data']), spelled_height(b['pitch_data'])
    return (ha is not None and hb is not None and a['pitch'] is not None and b['pitch'] is not None
            and abs(hb-ha) == 1 and 0 < abs(b['pitch']-a['pitch']) <= 2)


def same_pitch(a, b):
    return a['token'] == b['token'] and a['pitch'] == b['pitch'] and (
        spelled_height(a['pitch_data']) == spelled_height(b['pitch_data']))


class Context:
    def __init__(self, ev, *, grace_notes=(), context_barriers=(), history_gate=None):
        self.ev = ev; self.rows = {r['id']: r for r in ev.rows}
        if len(self.rows) != len(ev.rows): raise ValueError('duplicate_context_sound')
        self.links = {(a['id'], b['id']) for a, b in ev.links}
        self.graces = [((n.get('part_id'), n.get('voice_id')), f(n['global_onset_quarter'])) for n in grace_notes]
        self.barriers = tuple(context_barriers); self.history_gate = history_gate; self.history_cache = {}
        lanes = defaultdict(list)
        for r in ev.rows:
            if r['identity'] is not None: lanes[r['identity']].append(r)
        self.figures = []; self.ambiguous = set()
        for lane, rows in sorted(lanes.items()):
            rows.sort(key=lambda r: (r['start'], r['end'], r['id']))
            active = []
            for r in rows:
                active = [a for a in active if a['end'] > r['start']]
                if active:
                    self.ambiguous.add(r['id']); self.ambiguous.update(a['id'] for a in active)
                active.append(r)
            for size in (3, 4):
                for i in range(len(rows)-size+1):
                    seq = tuple(rows[i:i+size])
                    if any(not r['clock_valid'] or r['token'] is None or r['id'] in self.ambiguous for r in seq): continue
                    if any(a['end'] != b['start'] or (a['id'], b['id']) not in self.links for a, b in zip(seq, seq[1:])): continue
                    if any(ident == lane and seq[0]['start'] <= t <= seq[-1]['end'] for ident, t in self.graces): continue
                    if any(seq[0]['start'] < t < seq[-1]['end'] for t in self.barriers): continue
                    a, b = seq[0], seq[-1]
                    if size == 3 and step(a, seq[1]) and step(seq[1], b):
                        kind = 'neighbor_like' if same_pitch(a, b) else (
                            'passing_like' if (seq[1]['pitch']-a['pitch'])*(b['pitch']-seq[1]['pitch']) > 0 else None)
                    elif size == 4 and same_pitch(a, b) and step(a, seq[1]) and step(seq[2], b) and (
                            (seq[1]['pitch']-a['pitch'])*(seq[2]['pitch']-a['pitch']) < 0):
                        kind = 'double_neighbor_like'
                    else: kind = None
                    if kind: self.figures.append((kind, seq))

    @staticmethod
    def anchor_member(row, runs):
        """Full actual anchor overlap, not merely its attack or a borrowed chord."""
        relevant = [sig for a, b, sig in runs if row['start'] < b and a < row['end']]
        return bool(relevant) and all(row['token'] in sig[1] for sig in relevant)

    def conflict(self, runs, index, total):
        left_start, start, left = runs[index-1]; _, end, selected = runs[index]
        context_end = runs[index+1][1] if index+1 < len(runs) else end
        lm, rm = set(left[1]), set(selected[1]); compatible = []; explained = set()
        for kind, seq in self.figures:
            if seq[0]['start'] < left_start or seq[-1]['end'] > context_end: continue
            if not all(r['token'] in lm and self.anchor_member(r, runs) for r in (seq[0], seq[-1])): continue
            middle = seq[1:-1]
            if any(r['token'] in lm for r in middle): continue
            affected = [r for r in middle if r['start'] < end and start < r['end']]
            if not affected: continue
            if self.history_gate is not None:
                key = seq[0]['start'], seq[-1]['end']
                if key not in self.history_cache: self.history_cache[key] = self.history_gate(*key)
                if not self.history_cache[key]: continue
            # Exposures are unions of actual sounds, never figure counts.
            explained.update(r['id'] for r in affected)
            compatible.append({'kind': kind, 'event_ids': [r['id'] for r in seq],
                'source_note_ids': {r['id']: list(r['source_note_ids']) for r in seq},
                'source_spans': {r['id']: {'start': q(r['start']), 'end': q(r['end'])} for r in seq},
                'explicit_lane': seq[0]['identity'],
                'middle_ids_overlapping_compared_run': [r['id'] for r in affected],
                'metric_and_duration': [{'event_id': r['id'], 'metric_strength':
                    None if (m := metric(self.ev.source, r['start'])[0]) is None else q(m),
                    'duration_in_local_beats': None if (u := metric(self.ev.source, r['start'])[1]) is None else q((r['end']-r['start'])/u)} for r in affected],
                'confirmed_nct': False, 'harmony_held_confirmed': False})
        observed = [e for e in self.ev.source.events if e.start < end and start < e.end]
        duration = {e.event_id: min(e.end, end)-max(e.start, start) for e in observed}
        pitch_known = all(e.pitch is not None for e in observed)
        voice_unknown = sorted(e.event_id for e in observed if e.pitch not in lm and (
            (r := self.rows.get(e.event_id)) is None or not r['clock_valid']
            or r['identity'] is None or r['id'] in self.ambiguous))
        foreign = {e.event_id for e in observed if e.pitch is not None and e.pitch not in lm}
        unexplained = foreign-explained
        reassigned = {e.event_id for e in observed if e.event_id in explained and e.pitch in rm}
        new = {e.event_id for e in observed if start <= e.start < end and e.pitch in rm-lm and e.event_id not in explained}
        held = {e.event_id for e in observed if e.start < start < e.end and e.pitch in lm}
        w = window(self.ev, start, end, left, selected)
        bass = F(); bass_available = True
        for cell in w['cells']:
            if not cell['lowest_pitch_available']: bass_available = False; continue
            if set(cell['lowest_sounding_event_ids']) & held:
                bass += f(cell['span']['end'])-f(cell['span']['start'])
        pair_values, details = resolution_features(self.ev, left_start, start, end, left, selected)
        pair_conflicts = []
        for detail in details:
            for pair in detail.get('source_event_pairs', ()):
                if set(pair) & explained: pair_conflicts.append(list(pair))
        suffixes = {'dominant_family_leading_tone': '_leading_tone_to_selected_target',
                    'dominant_family_seventh_step': '_seventh_to_selected_member'}
        credit = sum((pair_values[k] for k, suffix in suffixes.items()
                      if any(set(p) & explained for d in details if d['kind'].endswith(suffix)
                             for p in d.get('source_event_pairs', ()))), F())
        # Unknown voice is NOT known zero for pattern-based terms. Partial sums
        # are receipts only and are excluded from gradient differences.
        pattern_available = pitch_known and not voice_unknown
        values = {
            'hold_explained_step_exposure': sum((duration[i] for i in explained), F())/total,
            'hold_remaining_nonmember_exposure': sum((duration[i] for i in unexplained), F())/total,
            'reclassified_ornament_member_exposure': sum((duration[i] for i in reassigned), F())/total,
            'selected_new_exclusive_unassigned_exposure': sum((duration[i] for i in new), F())/total,
            'continuing_left_member_exposure': sum((duration[i] for i in held), F())/total,
            'continuing_left_lowest_coverage': bass/(runs[-1][1]-runs[0][0]),
            'dominant_credit_with_hold_conflict': credit}
        availability = {k: pattern_available if k in FEATURES[:4] else
                        (pattern_available and beat_extent(self.ev.source, left_start, start) is not None) if k == FEATURES[-1] else
                        (pitch_known and (bass_available if k == FEATURES[-2] else True)) for k in FEATURES}
        return {'span': {'start': q(start), 'end': q(end)},
            'three_run_context_span': {'start': q(left_start), 'end': q(context_end)},
            'held_hypothesis_signature': left, 'selected_signature': selected,
            'next_selected_signature': runs[index+1][2] if index+1 < len(runs) else None,
            'conditional_figures': compatible, 'explained_event_ids': sorted(explained),
            'remaining_held_foreign_ids': sorted(unexplained),
            'new_exclusive_unassigned_ids': sorted(new), 'continuing_left_member_ids': sorted(held),
            'voice_or_clock_unavailable_ids': voice_unknown, 'source_window': w,
            'incoming_resolution_details': details, 'incoming_resolution_conflicting_pairs': pair_conflicts,
            'observed_feature_sums': {k: q(v) for k, v in values.items()}, 'availability': availability,
            'features': {k: q(values[k]) if availability[k] else None for k in FEATURES},
            'hold_hypothesis_is_not_inserted_into_candidate_graph': True,
            'confirmed_nct': False, 'harmony_held_confirmed': False, 'source_labels_used': False}


def observe_path(problem, ev, ids, *, context=None, **kwargs):
    runs = completed_runs(problem, ids)
    total = sum((min(e.end, runs[-1][1])-max(e.start, runs[0][0]) for e in ev.source.events
                 if e.start < runs[-1][1] and runs[0][0] < e.end), F())
    if total <= 0: raise ValueError('empty_context_sound_domain')
    ctx = context or Context(ev, **kwargs)
    if ctx.ev is not ev: raise ValueError('context_competition_source_mismatch')
    transitions = [ctx.conflict(runs, i, total) for i in range(1, len(runs))]
    values = {k: sum((f(t['observed_feature_sums'][k]) for t in transitions), F()) for k in FEATURES}
    available = {k: all(t['availability'][k] for t in transitions) for k in FEATURES}
    return {'version': VERSION, 'source_ir_content_sha256': ev.source.source_ir_content_sha256,
        'completed_runs': [{'span': {'start': q(a), 'end': q(b)}, 'signature': sig} for a, b, sig in runs],
        'transitions': transitions, 'normalization_note_time': q(total),
        'observed_feature_sums': {k: q(v) for k, v in values.items()}, 'availability': available,
        'features': {k: q(values[k]) if available[k] else None for k in FEATURES},
        'source_labels_used': False, 'weights_changed': False, 'selection_changed': False,
        'existing_costs_changed': False, 'source_modified': False,
        'empty_transition_domain_known_zero': not transitions,
        'requires_future_complete_run_for_joint_search': True,
        'limits': ['Geometry is conditional compatibility, not an NCT decision.',
            'Residual retains all other voices; melodic neighbors can accompany real chord changes.',
            'No guessed voice, invented attack, new chord candidate or annotation lookup.',
            'Three/four contiguous sounds only; gaps, grace barriers and overlaps are not bridged.',
            'Suspension/anticipation/long pedal and nonadjacent decorated resolution remain separate unfinished work.',
            'This vector is not yet weighted or integrated in the exact joint decoder.']}
