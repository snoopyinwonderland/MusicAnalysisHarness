"""Diagnose missing membership and conditional NCT without relaxing gates.

Outside-interval availability is not boundary evidence or permission to merge.
Absence from a bounded parent context is not proof of an omitted chord tone.
"""
from collections import Counter
from copy import deepcopy
from .harmony_joint import f
from .formal_ir import q
from .harmony_catalog_resolution import pitch_pair
from .harmony_distributed_resolution import profile

VERSION = 'missing-evidence-audit-0.1.0'


def overlap(a, b):
    return f(a['start']) < f(b['end']) and f(a['end']) > f(b['start'])


def validate_ir(lattice, ir):
    source = {s['sounding_event_id']: s for s in ir['sounding_events']}
    events = {s['sounding_event_id']: s for s in lattice['events']}
    if len(source) != len(ir['sounding_events']) or len(events) != len(lattice['events']):
        raise ValueError('duplicate_event_id')
    expected = {sid for sid, s in source.items() if overlap(s['span'], lattice['plan']['context_span'])}
    if set(events) != expected: raise ValueError('ir_context_event_coverage_mismatch')
    for sid, s in events.items():
        for key in ('pitch', 'span', 'source_note_ids'):
            if s.get(key) != source[sid].get(key): raise ValueError('ir_event_identity_mismatch')


def role(member, root):
    if root is None: return 'unresolved_root'
    distance = ('CDEFGAB'.index(member[0]) - 'CDEFGAB'.index(root[0])) % 7
    return {0: 'root', 2: 'third', 4: 'fifth', 6: 'seventh'}.get(distance, 'other')


def pattern_check(pattern, readings, lattice):
    assignments = {a['assignment_id'] for a in lattice['assignments']}
    refs = pattern['supporting_assignment_refs']
    if not refs or not set(refs) <= assignments: raise ValueError('unknown_pattern_assignment')
    events = {s['sounding_event_id']: s for s in lattice['events']}
    if not set(pattern['event_refs']) <= events.keys(): raise ValueError('unknown_pattern_event')
    outside = []; conflicts = []
    pair_span = {'start': readings[0]['span']['start'], 'end': readings[1]['span']['end']}
    for requirement in pattern['requirements']:
        sid = requirement['event_ref']; span = requirement['span']
        if sid not in events: raise ValueError('unknown_requirement_event')
        if not f(events[sid]['span']['start']) <= f(span['start']) < f(span['end']) <= f(events[sid]['span']['end']):
            raise ValueError('requirement_outside_event')
        if f(span['start']) < f(pair_span['start']) or f(span['end']) > f(pair_span['end']):
            outside.append(deepcopy(requirement))
        for index, reading in enumerate(readings):
            if not overlap(span, reading['span']): continue
            state = 'member' if pitch_pair(events[sid]['pitch']) in reading['members'] else 'nonmember_not_confirmed_nct'
            if state != requirement['state'] or reading['abstention_reasons']:
                conflicts.append({'reading_index': index, 'requirement': deepcopy(requirement),
                                  'actual_state': state, 'candidate_blockers': reading['abstention_reasons']})
    withheld = lattice.get('withheld_pattern_reasons', {}).get(pattern['pattern_id'], [])
    status = ('membership_conflict' if conflicts else 'requires_external_candidate_context' if outside else
              'withheld_conditions' if withheld else 'conditional_pattern_compatible')
    return {'pattern_ref': pattern['pattern_id'], 'kind': pattern['kind'], 'status': status,
            'supporting_assignment_refs': deepcopy(refs), 'outside_requirements': outside,
            'conflicts': conflicts, 'withheld_reasons': deepcopy(withheld), 'confirmed_nct': False}


def audit_pair(lattice, item):
    readings = []
    for side in ('source', 'target'):
        choice = item['pair'][side]
        reading = lattice['edges'][choice['edge']]['readings'][choice['reading']]
        if reading['candidate_ref'] != item[side+'_candidate_ref'] or reading['alternative_index'] != item[side+'_alternative_index']:
            raise ValueError('candidate_origin_mismatch')
        readings.append(reading)
    if readings[0]['span']['end'] != readings[1]['span']['start']: raise ValueError('nonadjacent_pair')
    if item['parent_context_span'] != lattice['plan']['context_span']: raise ValueError('parent_span_mismatch')
    if item['local_context_span'] != {'start':readings[0]['span']['start'],'end':readings[1]['span']['end']}:
        raise ValueError('local_span_mismatch')
    query = item.get('temporal_query')
    base = {'pair': deepcopy(item['pair']), 'parent_context_span': deepcopy(item['parent_context_span']),
            'local_context_span': deepcopy(item['local_context_span']), 'sides': {}, 'gate_changed': False}
    if not query or 'source_profile' not in query:
        return {**base, 'status': 'not_auditable', 'original_status': query['status'] if query else item['status']}
    events = {s['sounding_event_id']: s for s in lattice['events']}
    for side, reading in zip(('source', 'target'), readings):
        observed = profile(events, reading)
        if observed != query[side+'_profile']: raise ValueError('saved_profile_mismatch')
        missing = []
        for pitch in observed['missing_members']:
            available = [s for s in events.values() if pitch_pair(s['pitch']) == pitch
                         and f(s['span']['end']) > f(s['span']['start'])]
            missing.append({'pitch': deepcopy(pitch), 'member_role': role(pitch, reading.get('root_spelling')),
                'status': 'available_elsewhere_in_parent' if available else 'not_observed_in_parent',
                'outside_event_refs': [s['sounding_event_id'] for s in available],
                'outside_event_spans': [deepcopy(s['span']) for s in available],
                'omission_confirmed': False, 'boundary_extension_authorized': False})
        nonmembers = []
        for sid in observed['unexplained_event_refs']:
            sound = events[sid]
            span = {'start':q(max(f(sound['span']['start']),f(reading['span']['start']))),
                    'end':q(min(f(sound['span']['end']),f(reading['span']['end'])))}
            alternatives = []
            for pattern in lattice['patterns']:
                if pattern['affected_event_ref'] != sid or not overlap(pattern['nonmember_span'], span): continue
                checked = pattern_check(pattern, readings, lattice)
                a,b = max(f(span['start']),f(pattern['nonmember_span']['start'])), min(f(span['end']),f(pattern['nonmember_span']['end']))
                alternatives.append({**checked, 'covered_span': {'start':q(a),'end':q(b)},
                                     'covers_entire_nonmember_span': a==f(span['start']) and b==f(span['end'])})
            nonmembers.append({'event_ref':sid,'pitch':deepcopy(sound['pitch']),'span':span,
                               'pattern_alternatives':alternatives,'confirmed_nct':False})
        base['sides'][side] = {'candidate_ref':reading['candidate_ref'],'alternative_index':reading['alternative_index'],
                              'span':deepcopy(reading['span']),'missing':missing,'nonmembers':nonmembers}
    return {**base,'status':'audited'}


def run(lattice, survey, ir):
    out = {'version':VERSION,'status':survey['status'],'results':[], 'gate_changed':False,
           'selected':None,'accuracy_measured':False,'production_modified':False}
    if survey['status'] != 'ready': return out
    validate_ir(lattice, ir)
    if len(survey['results']) != len(survey['plan']['pairs']): raise ValueError('survey_incomplete')
    counts = Counter()
    for planned, item in zip(survey['plan']['pairs'],survey['results']):
        if planned != item['pair']: raise ValueError('pair_plan_mismatch')
        row = audit_pair(lattice, item); out['results'].append(row); counts[row['status']]+=1
        for side in row['sides'].values():
            for m in side['missing']:
                counts['missing:'+m['status']]+=1; counts['missing_role:'+m['member_role']]+=1
            for n in side['nonmembers']:
                counts['nonmember_instances']+=1
                if not n['pattern_alternatives']: counts['nonmember_without_stored_pattern']+=1
                for p in n['pattern_alternatives']: counts['pattern:'+p['status']]+=1
    out.update(summary=dict(counts),limits=[
        'Counts are repeated candidate/event instances, not unique notes or independent cases.',
        'Nearby pitch availability is not evidence for merging chords; absence is not omission proof.',
        'NCT compatibility remains assignment-conditional; alternatives cannot be unioned into a global interpretation.',
        'Existing pattern vocabulary/sampled lanes only; lack of pattern is not lack of musical NCT.'])
    return out
