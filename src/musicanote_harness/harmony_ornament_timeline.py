"""Conditional ornament coverage on exact cells, with withheld claims separated."""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_segment_contrast import compare as segment_compare

VERSION = 'ornament-timeline-0.1.0'
BUCKETS = ('member', 'conditional_nonmember', 'withheld_nonmember', 'unexplained_nonmember', 'spelling_unresolved')


def policy(boundary):
    assessments = {p['pattern_ref']: p for p in boundary.get('boundary_assessment', {}).get('patterns', [])}
    withheld = {}
    for p in boundary.get('boundary_figures', {}).get('patterns', []):
        a = assessments.get(p['pattern_id'])
        if a and a['status'] == 'abstain':
            withheld[p['pattern_id']] = deepcopy(a['abstention_reasons'])
        elif p['kind'] == 'prepared_suspension_candidate':
            withheld[p['pattern_id']] = ['suspension_conditions_not_verified']
    return {'version': VERSION, 'status': boundary['status'], 'withheld_pattern_reasons': withheld,
            'confirmed_nct': False, 'selected': None}


def timeline(cells, base, active, withheld):
    items = []; note_time = {k: Fraction() for k in BUCKETS}; rows = []
    for item in base['items']:
        v = deepcopy(item); lo, hi = f(v['span']['start']), f(v['span']['end'])
        supporting = [p['pattern_id'] for p in active if p['affected_event_ref'] == v['event_ref']
                      and f(p['nonmember_span']['start']) <= lo and hi <= f(p['nonmember_span']['end'])]
        allowed = [pid for pid in supporting if pid not in withheld]
        blocked = [pid for pid in supporting if pid in withheld]
        v['conditional_pattern_refs'] = allowed; v['withheld_pattern_refs'] = blocked
        v['local_conditional_support'] = v['bucket'] == 'conditional_nonmember'
        if v['bucket'] == 'unexplained_nonmember':
            v['bucket'] = 'conditional_nonmember' if allowed else 'withheld_nonmember' if blocked else v['bucket']
        # An independently supported local explanation is not erased by another withheld claim.
        note_time[v['bucket']] += hi - lo; items.append(v)
    wall_time = {}
    for cell in cells:
        selected = [v for v in items if v['span'] == cell['span']]
        if sorted(v['event_ref'] for v in selected) != sorted(cell['event_refs']): raise ValueError('cell_event_mismatch')
        states = {v['bucket'] for v in selected}
        state = next((s for s in ('spelling_unresolved', 'unexplained_nonmember', 'withheld_nonmember', 'conditional_nonmember') if s in states), 'member' if states else 'silence')
        wall_time[state] = wall_time.get(state, Fraction()) + f(cell['span']['end']) - f(cell['span']['start'])
        rows.append({'span': deepcopy(cell['span']), 'state': state,
                     'event_buckets': {k: [v['event_ref'] for v in selected if v['bucket'] == k] for k in BUCKETS}})
    if q(sum(note_time.values(), Fraction())) != base['total_note_time']: raise ValueError('note_time_loss')
    return {'items': items, 'cells': rows, 'note_time': {k: q(v) for k, v in note_time.items()},
            'wall_time': {k: q(v) for k, v in wall_time.items()}, 'total_note_time': base['total_note_time'],
            'confirmed_nct': False}


def compare(result, boundary_index, hold_index, left_index, right_index, assignment_ref):
    base = segment_compare(result, boundary_index, hold_index, left_index, right_index, assignment_ref)
    b = result['boundaries'][boundary_index]; p = policy(b)
    active = [v for v in b.get('boundary_figures', {}).get('patterns', [])
              if left_index in v['left_reading_indices'] and right_index in v['right_reading_indices']
              and assignment_ref in v['supporting_assignment_refs']]
    if b['left']['readings'][left_index]['condition']['abstention_reasons'] or b['right']['readings'][right_index]['condition']['abstention_reasons']:
        active = []
    return {'version': VERSION, 'hold': timeline(b['cells'], base['hold'], [], {}),
            'split': timeline(b['cells'], base['split'], active, p['withheld_pattern_reasons']),
            'active_pattern_refs': [v['pattern_id'] for v in active], 'policy': p,
            'preferred': None, 'harmonic_change_confirmed': False,
            'limits': ['Conditional coverage is not verified NCT or a harmonic ranking score.',
                       'Hold uses existing local context; split additionally uses boundary geometry. Models are not symmetric.',
                       'Mixed cells retain every event and explanation; wall-time priority is for display, not deleting alternatives.']}


def augment(baseline):
    result = deepcopy(baseline)
    for b in result['boundaries']: b['ornament_timeline'] = policy(b)
    p = result.get('preview_selection')
    if p: result['ornament_timeline_preview'] = compare(result, p['boundary'], p['hold'], p['left'], p['right'], p['assignment'])
    result['ornament_timeline_version'] = VERSION
    return result
