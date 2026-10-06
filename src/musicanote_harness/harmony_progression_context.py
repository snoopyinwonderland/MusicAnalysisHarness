"""Label-blind interval lattice; full-context NCT evidence for arbitrary chord paths.

This is an unranked hypothesis container, not a segmentation optimizer.
"""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_candidate_catalog import propose
from .harmony_catalog_resolution_trial import label
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .harmony_shared_context import catalog as geometry_catalog
from .harmony_ornament_timeline import timeline

VERSION = 'full-context-progression-0.2.0'
MAX_EDGES = 256


def plan(events, span):
    a, b = f(span['start']), f(span['end'])
    if not 0 <= a < b:
        raise ValueError('invalid_context')
    points = sorted({a,b} | {f(s['span'][k]) for s in events for k in ('start','end')
                             if a < f(s['span'][k]) < b})
    return {'context_span': deepcopy(span), 'points': [q(x) for x in points],
            'intervals': [{'from': i, 'to': j, 'span': {'start': q(x), 'end': q(points[j])}}
                          for i,x in enumerate(points[:-1]) for j in range(i+1,len(points))],
            'selection': 'all attack/release points; all contiguous intervals; no source labels',
            'source_labels_used': False}


def build(ir, baseline, max_edges=MAX_EDGES):
    if baseline['status'] != 'ready':
        return {'version': VERSION, 'status': 'baseline_not_ready', 'selected': None}
    events = baseline['events']; p = plan(events, baseline['span'])
    out = {'version': VERSION, 'status': 'ready', 'plan': p, 'edges': [], 'patterns': [],
           'events': deepcopy(events), 'assignments': deepcopy(baseline['assignments']),
           'withheld_pattern_reasons': {}, 'selected': None, 'source_labels_used': False,
           'ranking_performed': False, 'production_modified': False}
    if len(p['intervals']) > max_edges:
        return {**out, 'status': 'edge_budget_abstention_no_pruning', 'max_edges': max_edges}
    points = p['points']
    out['cells'] = [{'span': {'start': x, 'end': y}, 'event_refs': [s['sounding_event_id'] for s in events
                       if f(s['span']['start']) < f(y) and f(s['span']['end']) > f(x)]}
                    for x,y in zip(points,points[1:])]
    # Shape catalog reads the complete context, not each interval separately.
    # No reading indices are needed here; membership is tested on a chosen full path.
    dummy = {'status': 'ready', 'span': p['context_span'], 'events': events,
             'assignments': baseline['assignments'], 'hold_readings': [], 'boundaries': []}
    cuts = points[1:-1] or [q((f(points[0])+f(points[-1]))/2)]
    shapes = {}
    for cut in cuts:
        dummy['boundaries'] = [{'status': 'ready', 'boundary': cut,
                                'left': {'readings': []}, 'right': {'readings': []}}]
        c = geometry_catalog(dummy,0)
        for s in c['patterns']:
            for side in ('hold','left','right'): s.pop(side+'_reading_indices')
            shapes[s['pattern_id']] = s
        out['withheld_pattern_reasons'].update(c['withheld_pattern_reasons'])
    out['patterns'] = list(shapes.values())
    for interval in p['intervals']:
        cat = propose(ir, interval['span'], p['context_span'])
        rows = []
        for c in cat['candidates']:
            for ai, alt in enumerate(c['spelling_alternatives']):
                members = alt['members']; span = c['span']
                states = {s['sounding_event_id']: ('spelling_unresolved' if spelled_height(s['pitch']) is None
                          else 'member' if pitch_pair(s['pitch']) in members else 'nonmember_not_confirmed_nct')
                          for s in events if f(s['span']['start']) < f(span['end']) and f(s['span']['end']) > f(span['start'])}
                rows.append({'candidate_ref': c['candidate_id'], 'alternative_index': ai,
                    'origin_pointer': c['origin_pointer'], 'provider': c['provider'],
                    'display_label': label(cat,c,ai if alt.get('root_spelling') is not None else None),
                    'root_spelling': deepcopy(alt.get('root_spelling')),
                    'root_provenance': 'provider_spelling_alternative',
                    'span': deepcopy(span), 'members': deepcopy(members),
                    'missing_spellings': c['missing_spellings_by_alternative'][ai],
                    'abstention_reasons': c['abstention_reasons'], 'event_states': states})
        out['edges'].append({**interval, 'readings': rows,
            'unspelled_candidate_refs': [c['candidate_id'] for c in cat['candidates'] if not c['spelling_alternatives']]})
    out['limits'] = ['No winning path, local-key/function inference or pedal-role model.',
        'All-part membership; NCT geometry limited to baseline sampled voice assignments.',
        'Candidate providers retain their own gates; interval lattice is not proof of full harmonic coverage.',
        'Origin pointers refer to a reproducible candidate catalog for that interval/context, not this compact file.']
    return out


def evaluate(result, path, assignment_ref, evaluation_span=None):
    if result['status'] != 'ready': raise ValueError('lattice_not_ready')
    if assignment_ref not in {a['assignment_id'] for a in result['assignments']}:
        raise ValueError('unknown_assignment')
    p = result['plan']; span = p['context_span']; selected = []; cursor = 0
    for choice in path:
        ei, ri = choice['edge'], choice['reading']
        if type(ei) is not int or type(ri) is not int or ei < 0 or ri < 0: raise ValueError('invalid_choice')
        edge = result['edges'][ei]
        if edge['from'] != cursor or edge['to'] <= cursor: raise ValueError('invalid_path_partition')
        selected.append(edge['readings'][ri]); cursor = edge['to']
    if cursor != len(p['points'])-1: raise ValueError('incomplete_context_path')
    target = evaluation_span or span
    start,end=f(target['start']),f(target['end']); points={f(x) for x in p['points']}
    if not f(span['start']) <= start < end <= f(span['end']) or start not in points or end not in points:
        raise ValueError('evaluation_span_not_on_grid')
    def matches(shape):
        if assignment_ref not in shape['supporting_assignment_refs']: return False
        for req in shape['requirements']:
            for r in selected:
                if f(r['span']['start']) < f(req['span']['end']) and f(req['span']['start']) < f(r['span']['end']):
                    if r['abstention_reasons'] or r['event_states'].get(req['event_ref']) != req['state']: return False
        return True
    active=[s for s in result['patterns'] if matches(s)]
    cells=[c for c in result['cells'] if start <= f(c['span']['start']) and f(c['span']['end']) <= end]
    items=[]; total=Fraction()
    for cell in cells:
        x,y=f(cell['span']['start']),f(cell['span']['end'])
        r=next(r for r in selected if f(r['span']['start']) <= x and y <= f(r['span']['end']))
        for sid in cell['event_refs']:
            state=r['event_states'][sid]; total+=y-x
            items.append({'event_ref': sid, 'span': cell['span'], 'candidate_ref': r['candidate_ref'],
                          'bucket': 'unexplained_nonmember' if state=='nonmember_not_confirmed_nct' else state})
    answer=timeline(cells, {'items':items,'total_note_time':q(total)}, active, result['withheld_pattern_reasons'])
    return {**answer, 'path':deepcopy(path), 'assignment_ref':assignment_ref,
            'context_span':deepcopy(span), 'evaluation_span':deepcopy(target),
            'active_pattern_refs':[s['pattern_id'] for s in active], 'selected':None,
            'harmonic_progression_confirmed':False,
            'blocked_candidate_refs':[r['candidate_ref'] for r in selected if r['abstention_reasons']]}
