"""Auditable evidence vectors for full-context paths; no harmony ranking."""
from copy import deepcopy
from fractions import Fraction

from .formal_ir import q
from .harmony_joint import f
from .harmony_progression_context import evaluate
from .harmony_temporal_coherence import membership
from .harmony_catalog_resolution import pitch_pair

VERSION = 'progression-evidence-0.1.1'


def lowest(events):
    """Observed lowest MIDI, not structural bass or inferred chord root."""
    if not events:
        return {'status': 'silence', 'midi_pitch': None, 'event_refs': []}
    values = [s['pitch'].get('midi_pitch') for s in events]
    if any(type(v) not in (int, float) or not float('-inf') < v < float('inf') for v in values):
        return {'status': 'unknown_pitch', 'midi_pitch': None, 'event_refs': []}
    value = min(values)
    return {'status': 'observed_lowest', 'midi_pitch': value,
            'event_refs': sorted(s['sounding_event_id'] for s in events if s['pitch']['midi_pitch'] == value)}


def vector(result, path, assignment_ref, evaluation_span=None):
    accounting = evaluate(result, path, assignment_ref, evaluation_span)
    target = accounting['evaluation_span']; a, b = f(target['start']), f(target['end'])
    events = {s['sounding_event_id']: s for s in result['events']}
    rows = []; segments = []; boundaries = []
    for choice in path:
        edge = result['edges'][choice['edge']]; reading = edge['readings'][choice['reading']]
        x, y = max(a, f(edge['span']['start'])), min(b, f(edge['span']['end']))
        if x >= y:
            continue
        members = {tuple(m) for m in reading['members']}
        seen = set(); complete = None
        durations = {k: Fraction() for k in ('member_only', 'mixed', 'nonmember_only', 'unknown', 'silence')}
        refs = set(); foreign = set()
        for cell in result['cells']:
            c, d = f(cell['span']['start']), f(cell['span']['end'])
            if not x <= c < d <= y:
                continue
            active = [events[sid] for sid in cell['event_refs']]
            states = {s['sounding_event_id']: membership(s, members) for s in active}
            state = ('silence' if not active else 'unknown' if 'unknown' in states.values() else
                     'mixed' if len(set(states.values())) > 1 else
                     'member_only' if next(iter(states.values())) == 'member' else 'nonmember_only')
            durations[state] += d-c
            # Only validated spelling may support a spelled member.
            seen.update(tuple(pitch_pair(s['pitch'])) for s in active if states[s['sounding_event_id']] == 'member')
            if complete is None and members and members <= seen:
                complete = deepcopy(cell['span']['start'])
            refs.update(states); foreign.update(sid for sid, v in states.items() if v == 'nonmember')
            bass = lowest(active)
            bass['membership'] = {sid: states[sid] for sid in bass['event_refs']}
            row = {'span': deepcopy(cell['span']), 'event_refs': sorted(states),
                   'membership': states, 'texture_state': state, 'lowest': bass}
            rows.append(row)
        segments.append({'choice': deepcopy(choice), 'candidate_ref': reading['candidate_ref'],
            'alternative_index': reading['alternative_index'], 'assumed_span': deepcopy(edge['span']),
            'evaluated_span': {'start': q(x), 'end': q(y)}, 'members': deepcopy(reading['members']),
            'event_refs': sorted(refs), 'nonmember_event_refs': sorted(foreign),
            'cell_time': {k: q(v) for k, v in durations.items()},
            'first_complete_union_time_in_evaluation': complete,
            'complete_union_with_nonmembers': complete is not None and bool(foreign),
            'candidate_blockers': deepcopy(reading['abstention_reasons']),
            'missing_spellings': deepcopy(reading['missing_spellings']),
            'inversion_status': 'not_evaluated_in_membership_vector_use_separate_bass_roles',
            'arpeggiation_confirmed': False})
    for left, right in zip(segments, segments[1:]):
        cut = f(right['evaluated_span']['start'])
        lm, rm = {tuple(m) for m in left['members']}, {tuple(m) for m in right['members']}
        def exclusive(segment, own, other):
            return [sid for sid in segment['event_refs']
                    if membership(events[sid], own) == 'member' and membership(events[sid], other) == 'nonmember']
        held = [{'event_ref': sid, 'left': membership(s, lm), 'right': membership(s, rm)}
                for sid, s in sorted(events.items()) if f(s['span']['start']) < cut < f(s['span']['end'])]
        before = next(row['lowest'] for row in rows if f(row['span']['end']) == cut)
        after = next(row['lowest'] for row in rows if f(row['span']['start']) == cut)
        bass_change = (before['midi_pitch'] != after['midi_pitch']
                       if before['status'] == after['status'] == 'observed_lowest' else None)
        le, re = exclusive(left, lm, rm), exclusive(right, rm, lm)
        boundaries.append({'time': q(cut), 'same_member_sets': lm == rm,
            'left_exclusive_event_refs': le, 'right_exclusive_event_refs': re,
            'two_sided_differentiating_members': bool(le and re), 'held_memberships': held,
            'observed_lowest_changed': bass_change, 'lowest_before': before, 'lowest_after': after,
            'harmonic_change_confirmed': False,
            'withheld_reasons': ['exclusive_members_may_be_ornaments',
                                 'same_members_do_not_imply_same_inversion_or_function']})
    return {'version': VERSION, 'path': deepcopy(path), 'assignment_ref': assignment_ref,
            'context_span': deepcopy(accounting['context_span']), 'evaluation_span': deepcopy(target),
            'accounting': accounting, 'cells': rows, 'segments': segments, 'boundaries': boundaries,
            'evidence_groups': ['membership_and_duration_correlated', 'observed_lowest_not_structural_bass',
                                'conditional_ornament_depends_on_path_and_assignment'],
            'selected': None, 'ranking_performed': False, 'source_labels_used': False}


def compare(result, first_path, second_path, assignment_ref, evaluation_span=None):
    first = vector(result, first_path, assignment_ref, evaluation_span)
    second = vector(result, second_path, assignment_ref, evaluation_span)
    if first['accounting']['total_note_time'] != second['accounting']['total_note_time']:
        raise ValueError('comparison_note_time_mismatch')
    # No automatic winner: extra boundaries often turn ornamental tones into members.
    delta = {k: q(f(second['accounting']['note_time'][k])-f(v))
             for k, v in first['accounting']['note_time'].items()}
    return {'version': VERSION, 'first': first, 'second': second,
            'note_time_delta_second_minus_first': delta,
            'boundary_count_delta': len(second['boundaries'])-len(first['boundaries']),
            'interpretation': 'membership_gain_is_not_accuracy_gain',
            'preferred': None, 'production_modified': False}
