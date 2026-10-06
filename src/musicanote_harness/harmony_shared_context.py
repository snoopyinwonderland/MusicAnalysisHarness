"""One geometry catalog and fixed context for hold and piecewise harmony."""
from copy import deepcopy
from .formal_ir import q
from .harmony_joint import f
from .harmony_path_contrast import token
from .harmony_reading_voice_context import spelled_height
from .counterpoint_evidence import melodic_geometry
from .harmony_voice_paths import partition
from .harmony_segment_contrast import compare as base_compare
from .harmony_ornament_timeline import timeline

VERSION = 'shared-harmonic-context-0.1.0'
MEMBER = 'member'
NONMEMBER = 'nonmember_not_confirmed_nct'


def catalog(result, boundary_index):
    b = result['boundaries'][boundary_index]
    out = {'version': VERSION, 'status': b['status'], 'patterns': [], 'withheld_pattern_reasons': {},
           'context_span': deepcopy(result['span']), 'selected': None, 'confirmed_nct': False}
    if result['status'] != 'ready' or b['status'] != 'ready': return out
    events = {s['sounding_event_id']: s for s in result['events']}
    a, z = f(result['span']['start']), f(result['span']['end']); cut = f(b['boundary'])
    lane_ids = {sid for track in result['assignments'][0]['tracks'] for sid in track}
    shapes = {}

    def full(sid):
        s = events[sid]
        return a <= f(s['span']['start']) < f(s['span']['end']) <= z and spelled_height(s['pitch']) is not None

    def requirement(sid, state, start=None, end=None):
        return {'event_ref': sid, 'state': state, 'span': {
            'start': deepcopy(events[sid]['span']['start']) if start is None else q(start),
            'end': deepcopy(events[sid]['span']['end']) if end is None else q(end)}}

    def add(kind, refs, affected, span, reqs, aid):
        pid = 'shared_nct_' + token([kind, refs, affected, span, reqs])
        if pid not in shapes:
            shapes[pid] = {'pattern_id': pid, 'kind': kind, 'event_refs': list(refs),
                'affected_event_ref': affected, 'nonmember_span': deepcopy(span),
                'requirements': reqs, 'supporting_assignment_refs': [], 'confirmed': False}
        shapes[pid]['supporting_assignment_refs'].append(aid)

    for assignment in result['assignments']:
        tracks = partition([events[sid] for sid in lane_ids], assignment['links'])
        if tracks != assignment['tracks']: raise ValueError('shared_track_partition_mismatch')
        aid = assignment['assignment_id']
        for track in tracks:
            for refs in zip(track, track[1:], track[2:]):
                if not all(full(sid) for sid in refs): continue
                ps = [events[sid]['pitch'] for sid in refs]
                shape = melodic_geometry([(p['step'], int(f(p['alter'])), p['octave']) for p in ps])['pattern']
                if shape:
                    add(shape.replace('_geometry', '_candidate'), refs, refs[1], events[refs[1]]['span'],
                        [requirement(sid, state) for sid, state in zip(refs, (MEMBER, NONMEMBER, MEMBER))], aid)
            for x, y in zip(track, track[1:]):
                if not full(x) or not full(y): continue
                xs, ys = events[x], events[y]; xp, yp = xs['pitch'], ys['pitch']
                if f(xs['span']['end']) == cut == f(ys['span']['start']) and xp['midi_pitch'] == yp['midi_pitch'] and spelled_height(xp) == spelled_height(yp):
                    add('anticipation_reattack_candidate', [x,y], x, xs['span'],
                        [requirement(x, NONMEMBER), requirement(y, MEMBER)], aid)
                if f(xs['span']['start']) < cut < f(xs['span']['end']) and spelled_height(yp)-spelled_height(xp) == -1 and yp['midi_pitch']-xp['midi_pitch'] in (-1,-2):
                    add('prepared_suspension_candidate', [x,y], x, {'start': q(cut), 'end': xs['span']['end']},
                        [requirement(x, MEMBER, end=cut), requirement(x, NONMEMBER, start=cut), requirement(y, MEMBER)], aid)
            for sid in track:
                if full(sid) and f(events[sid]['span']['start']) < cut < f(events[sid]['span']['end']):
                    add('anticipation_held_candidate', [sid], sid, {'start': events[sid]['span']['start'], 'end': q(cut)},
                        [requirement(sid, NONMEMBER, end=cut), requirement(sid, MEMBER, start=cut)], aid)

    def matches(reading, requirements):
        if reading['condition']['abstention_reasons']: return False
        for req in requirements:
            if f(reading['span']['start']) < f(req['span']['end']) and f(req['span']['start']) < f(reading['span']['end']):
                if reading['event_states'].get(req['event_ref']) != req['state']: return False
        return True

    for p in shapes.values():
        for side, rows in [('hold',result['hold_readings']), ('left',b['left']['readings']), ('right',b['right']['readings'])]:
            p[side+'_reading_indices'] = [i for i, r in enumerate(rows) if matches(r, p['requirements'])]
        if p['kind'] == 'prepared_suspension_candidate':
            out['withheld_pattern_reasons'][p['pattern_id']] = ['preparation_dissonance_resolution_accent_not_verified']
    out['patterns'] = list(shapes.values())
    out['limits'] = ['Same complete sounding-event scope, pitch geometry, tracks and membership requirements for both hypotheses.',
                     'Boundary-specific roles can apply only where membership changes; a constant hold need not support them.',
                     'No external context extension, new harmony candidates, NCT confirmation or ranking.']
    return out


def compare(result, boundary_index, hold_index, left_index, right_index, assignment_ref):
    base = base_compare(result, boundary_index, hold_index, left_index, right_index, assignment_ref)
    b = result['boundaries'][boundary_index]; c = b.get('shared_context') or catalog(result, boundary_index)
    selected = {}
    for name in ('hold', 'split'):
        active = [p for p in c['patterns'] if assignment_ref in p['supporting_assignment_refs'] and
                  (hold_index in p['hold_reading_indices'] if name == 'hold' else
                   left_index in p['left_reading_indices'] and right_index in p['right_reading_indices'])]
        raw = deepcopy(base[name])
        # Recompute both sides from membership only: no legacy local-context advantage.
        for item in raw['items']:
            if item['bucket'] == 'conditional_nonmember': item['bucket'] = 'unexplained_nonmember'
        selected[name] = timeline(b['cells'], raw, active, c['withheld_pattern_reasons'])
        selected[name]['active_pattern_refs'] = [p['pattern_id'] for p in active]
    identical = all(sorted(result['hold_readings'][hold_index]['members']) == sorted(r['members'])
                    for r in (b['left']['readings'][left_index], b['right']['readings'][right_index]))
    unblocked = not any(r['condition']['abstention_reasons'] for r in
                       (result['hold_readings'][hold_index], b['left']['readings'][left_index], b['right']['readings'][right_index]))
    equality = selected['hold']['note_time'] == selected['split']['note_time'] and selected['hold']['cells'] == selected['split']['cells']
    if identical and unblocked and not equality: raise ValueError('same_harmony_partition_invariance_failed')
    return {'version': VERSION, **selected, 'same_harmony_invariant_applicable': identical and unblocked,
            'same_harmony_invariant_passed': equality if identical and unblocked else None,
            'context_span': c['context_span'], 'preferred': None, 'harmonic_change_confirmed': False}


def augment(baseline):
    result = deepcopy(baseline)
    for i,b in enumerate(result['boundaries']): b['shared_context'] = catalog(result, i)
    p = result.get('preview_selection')
    if p: result['shared_context_preview'] = compare(result, p['boundary'], p['hold'], p['left'], p['right'], p['assignment'])
    result['shared_context_version'] = VERSION
    return result
