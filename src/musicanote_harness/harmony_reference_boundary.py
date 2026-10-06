"""Post-hoc source-reference diagnostics. Never labels the blind analyzer input."""
from .harmony_joint import f
from .formal_ir import q
from .cadential_six_four_audit import source_key
from .seventh_context import source_chord
from .harmony_shared_context import compare

VERSION = 'reference-boundary-diagnostic-0.1.0'
IDENTITY = ('globalkey', 'localkey', 'localkey_is_minor', 'numeral', 'form',
            'figbass', 'chord_type', 'changes', 'added_tones', 'relativeroot', 'pedal', 'special')


def identity(a):
    raw = a['raw_fields']
    return tuple(raw.get(k, '') for k in IDENTITY)


def classify(span, cut, annotations, verified_ids):
    """Cover every subcell; never bridge gaps or silently skip unsupported records."""
    start, end, cut = f(span['start']), f(span['end']), f(cut)
    if not start < cut < end:
        raise ValueError('cut_outside_span')
    rows = [a for a in annotations if a.get('target', {}).get('span') and
            f(a['target']['span']['start']) < end and f(a['target']['span']['end']) > start]
    points = sorted({start, end, cut, *[max(start, f(a['target']['span']['start'])) for a in rows],
                     *[min(end, f(a['target']['span']['end'])) for a in rows]})
    sides = {'left': [], 'right': []}
    out = {'status': 'ready', 'annotation_refs': [a['annotation_id'] for a in rows],
           'source_class': None, 'musical_gold': False,
           'source_annotations': rows}
    for x, y in zip(points, points[1:]):
        active = [a for a in rows if f(a['target']['span']['start']) <= x < f(a['target']['span']['end'])]
        reason = ('annotation_gap' if not active else 'annotation_overlap' if len(active) != 1 else
                  'unverified_alignment' if active[0]['annotation_id'] not in verified_ids else
                  'missing_chord_identity' if not active[0]['raw_fields'].get('numeral') else None)
        if reason:
            return {**out, 'status': reason, 'problem_span': {'start': q(x), 'end': q(y)}}
        sides['left' if y <= cut else 'right'].append(active[0])
    if any(len({identity(a) for a in rs}) != 1 for rs in sides.values()):
        return {**out, 'status': 'multiple_reference_changes_within_side'}
    left, right = sides['left'][0], sides['right'][0]
    out.update(left_annotation=left, right_annotation=right)
    same = identity(left) == identity(right)
    out['source_class'] = 'source_hold' if same else 'source_change'
    try:
        chords = [source_chord(a, *source_key(a)) for a in (left, right)]
    except (ValueError, TypeError, KeyError):
        chords = [None, None]
    if any(c is None for c in chords):
        return {**out, 'status': 'unsupported_reference_chord',
                'unsupported_features': sorted({k for a in (left, right)
                    for k in ('changes','added_tones','relativeroot','pedal','special')
                    if a['raw_fields'].get(k)}) or ['unsupported_key_or_chord_encoding']}
    out['reference_chords'] = chords
    members = [sorted(c['members']) for c in chords]
    if not same:
        out['source_class'] = ('source_same_members_semantic_change' if members[0] == members[1]
                               else 'source_member_change')
    return out


def diagnose(result, bi, reference):
    """Reference-matched candidate coverage and note-time contrasts, not predictions."""
    if reference['status'] != 'ready':
        return {'status': 'reference_not_evaluable', 'comparisons': []}
    b = result['boundaries'][bi]
    if result['status'] != 'ready' or b['status'] != 'ready':
        return {'status': 'analyzer_not_ready', 'comparisons': []}
    members = [sorted(c['members']) for c in reference['reference_chords']]
    def indices(rows, member):
        return [i for i, r in enumerate(rows) if sorted(r['members']) == member and
                not r['condition']['abstention_reasons']]
    left = indices(b['left']['readings'], members[0])
    right = indices(b['right']['readings'], members[1])
    holds = sorted(set(indices(result['hold_readings'], members[0])[:1] +
                       indices(result['hold_readings'], members[1])[:1]))
    out = {'status': 'ready', 'left_candidate_indices': left, 'right_candidate_indices': right,
           'hold_candidate_indices': holds, 'comparisons': [], 'preferred': None,
           'selection': 'first unblocked matching member set; min/max link assignment; not exhaustive',
           'functional_or_inversion_accuracy_measured': False}
    if not left or not right or not holds:
        return {**out, 'status': 'reference_members_missing_from_candidates'}
    assignments = result['assignments']
    aids = sorted({min(assignments, key=lambda a: len(a['links']))['assignment_id'],
                   max(assignments, key=lambda a: len(a['links']))['assignment_id']})
    for hi in holds:
        for aid in aids:
            c = compare(result, bi, hi, left[0], right[0], aid)
            out['comparisons'].append({'hold': hi, 'left': left[0], 'right': right[0],
                'assignment_ref': aid, 'hold_note_time': c['hold']['note_time'],
                'split_note_time': c['split']['note_time'],
                'split_minus_hold_unexplained': q(f(c['split']['note_time']['unexplained_nonmember']) -
                                                  f(c['hold']['note_time']['unexplained_nonmember'])),
                'same_harmony_invariant_passed': c['same_harmony_invariant_passed']})
    return out
