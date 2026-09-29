"""Appendix II evidence/proposal contract, NOT an automatic musical reduction.

Never removes Core events, infers a melody from the highest pitch, or treats a
projection/implied tone as a literal sounding event. No source labels enter observe.
"""
from collections import defaultdict
from copy import deepcopy
from .dominant_area_evidence import _exact
from .foundation_sonata_audit import pitch_tuple
from .formal_ir import q

VERSION = 'score-reduction-0.1.0'


def bounds(span):
    a, b = (_exact(span[k]) for k in ('start', 'end'))
    if not 0 <= a < b:
        raise ValueError('positive_span_required')
    return a, b


def observe(ir, span):
    """Exact same-spelling/octave doubling with identical attack AND release.

    This deliberately misses staggered doublings. A match is not dispensability.
    Full sounding spans, including ties across the requested range, are retained.
    """
    left, right = bounds(span)
    notes = {n['note_id']: n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']):
        raise ValueError('duplicate_note_id')
    rows, pending, seen = [], [], set()
    for event in ir['sounding_events']:
        sid = event['sounding_event_id']
        if sid in seen:
            raise ValueError('duplicate_sounding_id')
        seen.add(sid)
        a, b = (_exact(event['span'][k]) for k in ('start', 'end'))
        if not 0 <= a <= b:
            raise ValueError('invalid_sounding_time')
        if a >= right or b < left or (b == left and b > a):
            continue
        refs = event['source_note_ids']
        if not refs or len(set(refs)) != len(refs) or event['attack_note_id'] not in refs or any(n not in notes for n in refs):
            raise ValueError('broken_note_reference')
        pitch = list(pitch_tuple(event))
        row = {'event_id': sid, 'source_note_ids': list(refs),
               'attack_note_id': event['attack_note_id'], 'pitch': pitch,
               'span': deepcopy(event['span']),
               'part_voice_refs': [list(v) for v in sorted({(notes[n].get('part_id') or '', notes[n].get('voice_id') or '') for n in refs})],
               'structural_role': None}
        if any(notes[n].get('grace', {}).get('is_grace') for n in refs):
            pending.append(row)
            continue
        if a == b:
            raise ValueError('zero_duration_non_grace')
        rows.append(row)
    rows.sort(key=lambda r: (_exact(r['span']['start']), r['event_id']))
    groups = defaultdict(list)
    for row in rows:
        groups[(*row['pitch'][:2], *bounds(row['span']))].append(row)
    doubles = [{'event_ids': [r['event_id'] for r in group],
                'spelling_class': group[0]['pitch'][:2],
                'octaves': sorted({r['pitch'][2] for r in group}),
                'span': deepcopy(group[0]['span']),
                'kind': 'octave_doubling' if len({r['pitch'][2] for r in group}) > 1 else 'unison_doubling',
                'may_omit': None}
               for group in groups.values() if len(group) > 1]
    return {'version': VERSION, 'target_span': deepcopy(span), 'events': rows,
            'exact_doublings': doubles, 'grace_events_pending_role': pending,
            'selected_melody': None, 'selected_reduction': None,
            'production_enabled': False, 'basis': 'literal_geometry_not_redundancy_or_harmony'}


def proposal(ir, span, operations, boundary_refs):
    """Validate an external reduction hypothesis; does not execute it on Core.

    Explicit source event references + evidence are mandatory even for implied
    tones. Implied spans/pitches need not occur literally, but are marked inferred.
    Boundary refs are carried unchanged, not proof that boundaries are correct.
    """
    observation = observe(ir, span)
    rows = {r['event_id']: r for r in observation['events']}
    left, right = bounds(span)
    boundaries = deepcopy(boundary_refs)
    if len({r['id'] for r in boundaries}) != len(boundaries):
        raise ValueError('duplicate_boundary_id')
    for ref in boundaries:
        if not ref['id'] or ref.get('origin') not in ('source_annotation', 'analysis_hypothesis', 'human_annotation'):
            raise ValueError('boundary_origin_required')
        if not left <= _exact(ref['time']) <= right:
            raise ValueError('boundary_outside_target')
    result = []
    for op in operations:
        kind, refs = op['kind'], op['event_ids']
        if not refs or len(set(refs)) != len(refs) or any(i not in rows for i in refs):
            raise ValueError('invalid_operation_reference')
        if not op.get('evidence_refs') or not all(isinstance(x, str) and x for x in op['evidence_refs']):
            raise ValueError('evidence_required')
        item = {'kind': kind, 'event_ids': list(refs), 'evidence_refs': list(op['evidence_refs']),
                'status': 'unvalidated_hypothesis', 'source_events': deepcopy([rows[i] for i in refs])}
        if kind == 'retain':
            item['representation'] = 'literal'
        elif kind == 'group_doubling':
            if not any(set(refs) == set(g['event_ids']) for g in observation['exact_doublings']):
                raise ValueError('not_exact_doubling_group')
            item.update(representation='grouped_literal', may_omit=None)
        elif kind == 'register_transfer':
            shift = op['octave_shift']
            if type(shift) is not int or shift == 0:
                raise ValueError('nonzero_integer_octave_shift_required')
            item.update(representation='analytical_projection', octave_shift=shift,
                        projected_pitches=[[*rows[i]['pitch'][:2], rows[i]['pitch'][2]+shift] for i in refs])
        elif kind == 'implied_tone':
            a, b = bounds(op['span'])
            if not left <= a < b <= right:
                raise ValueError('implied_span_outside_target')
            pitch = list(pitch_tuple({'pitch': op['pitch']}))
            item.update(representation='inferred_not_sounded', pitch=pitch, span=deepcopy(op['span']))
        else:
            raise ValueError('unsupported_operation')
        result.append(item)
    return {'version': VERSION, 'target_span': deepcopy(span), 'operations': result,
            'boundary_refs': boundaries, 'boundary_merging_allowed': False,
            'unreferenced_event_ids': sorted(set(rows)-{i for op in operations for i in op['event_ids']}),
            'unreferenced_means_ornament': False, 'musically_validated': False,
            'production_enabled': False, 'training_eligible': False}


def notation_record(raw_label, profile, scope, source_ref):
    """Preserve notation dialect before interpretation; not a Roman parser."""
    if profile not in ('hvl_stufe_uppercase', 'dcml_case_sensitive'):
        raise ValueError('explicit_supported_profile_required')
    if scope not in ('local_chord', 'governing_span', 'interval_motion'):
        raise ValueError('explicit_scope_required')
    if not isinstance(raw_label, str) or not raw_label.strip() or not source_ref:
        raise ValueError('source_and_label_required')
    return {'raw_label': raw_label, 'notation_profile': profile, 'scope': scope,
            'source_ref': source_ref, 'quality': None, 'inversion': None,
            'policy': 'no_case_folding_no_figure_motion_to_inversion_conversion'}


def sequence_bass_form(pattern, inversions):
    """Appendix III taxonomy for an already supplied four-triad candidate."""
    if len(inversions) != 4 or any(type(i) is not int or i not in (0, 1) for i in inversions):
        return 'unsupported'
    inv = tuple(inversions)
    if pattern in ('descending_fifths', 'ascending_fifths'):
        return 'model' if inv == (0, 0, 0, 0) else 'variant' if inv in ((0, 1, 0, 1), (1, 0, 1, 0)) else 'unsupported'
    if pattern in ('descending_five_six', 'ascending_five_six'):
        return 'model' if inv == (0, 1, 0, 1) else 'variant' if inv == (0, 0, 0, 0) else 'unsupported'
    return 'unsupported'
