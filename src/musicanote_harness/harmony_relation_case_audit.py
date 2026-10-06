"""Recheck saved partial witnesses; never promote them to harmonic truth.

Complete membership, unexplained tones and competing origins are diagnostics,
not retroactive changes to the direct/temporal engine gates.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction

from .formal_ir import q
from .harmony_joint import f
from .harmony_missing_evidence import validate_ir
from .applied_chords import hypothesis

VERSION = 'relation-case-audit-0.1.2'
LETTERS = 'CDEFGAB'
NATURAL = dict(zip(LETTERS, (0, 2, 4, 5, 7, 9, 11)))
LEAD = 'leading_tone_to_target_root'
SEVENTH = 'seventh_down_step_to_target_member'


def pitch_identity(pitch):
    """No integer truncation of microtones, MIDI-only or enharmonic collapse."""
    step, octave = pitch.get('step'), pitch.get('octave')
    alter = pitch.get('alter')
    if step not in NATURAL or type(octave) is not int:
        raise ValueError('unsupported_spelling')
    # Integer alters in old synthetic fixtures are also exact, never floats.
    if type(alter) is int:
        accidental = Fraction(alter)
    elif isinstance(alter, dict):
        accidental = f(alter)
    else:
        raise ValueError('unsupported_spelling')
    if accidental.denominator != 1:
        raise ValueError('unsupported_spelling')
    midi = pitch.get('midi_pitch')
    if midi is None or isinstance(midi, bool) or midi != 12 * (octave + 1) + NATURAL[step] + accidental:
        raise ValueError('inconsistent_spelling_midi')
    return (step, int(accidental)), 7 * octave + LETTERS.index(step), midi


def profile(events, reading):
    """Exact spelling profile, with source event spans unchanged."""
    start, end = (f(reading['span'][k]) for k in ('start', 'end'))
    sounds = [s for s in events.values() if f(s['span']['start']) < end and f(s['span']['end']) > start]
    members = {tuple(m) for m in reading['members']}
    refs = {str(m): sorted(s['sounding_event_id'] for s in sounds if pitch_identity(s['pitch'])[0] == m)
            for m in sorted(members)}
    foreign = sorted(s['sounding_event_id'] for s in sounds if pitch_identity(s['pitch'])[0] not in members)
    points = sorted({start, end} | {max(start, f(s['span']['start'])) for s in sounds}
                    | {min(end, f(s['span']['end'])) for s in sounds})
    gaps = [[str(a), str(b)] for a, b in zip(points, points[1:])
            if not any(f(s['span']['start']) < b and f(s['span']['end']) > a for s in sounds)]
    return {'member_event_refs': refs, 'missing_members': [list(m) for m in sorted(members) if not refs[str(m)]],
            'unexplained_event_refs': foreign, 'silence_spans_quarters': gaps}


def _readings(lattice, item):
    readings = []
    for side in ('source', 'target'):
        choice = item['pair'][side]
        if any(type(choice[k]) is not int or choice[k] < 0 for k in ('edge', 'reading')):
            raise ValueError('invalid_candidate_index')
        reading = lattice['edges'][choice['edge']]['readings'][choice['reading']]
        if (reading['candidate_ref'] != item[side + '_candidate_ref'] or
                reading['alternative_index'] != item[side + '_alternative_index']):
            raise ValueError('candidate_origin_mismatch')
        readings.append(reading)
    if f(readings[0]['span']['end']) != f(readings[1]['span']['start']):
        raise ValueError('nonadjacent_pair')
    if item['parent_context_span'] != lattice['plan']['context_span']:
        raise ValueError('parent_span_mismatch')
    if item['local_context_span'] != {'start': readings[0]['span']['start'], 'end': readings[1]['span']['end']}:
        raise ValueError('local_span_mismatch')
    h = hypothesis(readings[1]['root_spelling'], item['pair']['target_quality'], item['pair']['family'])
    if (h['chord']['root'] != readings[0]['root_spelling'] or
            {tuple(m) for m in h['chord']['members']} != {tuple(m) for m in readings[0]['members']} or
            not {tuple(m) for m in h['target']['members']} <= {tuple(m) for m in readings[1]['members']}):
        raise ValueError('family_shape_mismatch')
    return readings, h


def _lanes(events, ir):
    notes = {n['note_id']: n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']):
        raise ValueError('duplicate_note_id')
    lanes = {}
    for sid, sound in events.items():
        refs = sound.get('source_note_ids', [])
        if not refs or any(n not in notes for n in refs):
            raise ValueError('broken_note_reference')
        identities = {(notes[n].get('part_id'), notes[n].get('voice_id')) for n in refs}
        if len(identities) != 1 or not all(next(iter(identities))):
            raise ValueError('missing_or_cross_voice_source_identity')
        lanes[sid] = next(iter(identities))
    return lanes


def _joint_links(links, events, lanes):
    edges = set()
    for link in links:
        if len(link) != 2 or any(sid not in events for sid in link):
            raise ValueError('unknown_witness_event')
        a, b = link
        if (lanes[a] != lanes[b] or f(events[a]['span']['end']) != f(events[b]['span']['start']) or
                f(events[a]['span']['start']) >= f(events[b]['span']['start'])):
            raise ValueError('witness_lane_or_timing_mismatch')
        edges.add((a, b))
    if len({a for a, b in edges}) != len(edges) or len({b for a, b in edges}) != len(edges):
        raise ValueError('witness_branch_or_merge')


def _motion(tag, a, b, h, target):
    pa, ha, ma = pitch_identity(a['pitch']); pb, hb, mb = pitch_identity(b['pitch'])
    if tag == LEAD:
        return pa == tuple(h['leading_tone']) and pb == tuple(h['target']['root']) and hb-ha == 1 and mb-ma == 1
    if tag == SEVENTH and len(h['chord']['members']) == 4:
        return pa == tuple(h['chord']['members'][3]) and list(pb) in target['members'] and hb-ha == -1 and mb-ma in (-1, -2)
    return False


def _boundary(events, reading, cut, terminal):
    active = [s for s in events.values() if
              (f(s['span']['start']) < cut <= f(s['span']['end']) if terminal else
               f(s['span']['start']) <= cut < f(s['span']['end']))]
    refs = {str(tuple(m)): sorted(s['sounding_event_id'] for s in active if pitch_identity(s['pitch'])[0] == tuple(m))
            for m in reading['members']}
    return refs, [m for m in reading['members'] if not refs[str(tuple(m))]]


def _result(query, positive):
    original = query.get('status') if query else None
    return {'original_status': original, 'status': 'conditional_witness_rechecked' if original == positive else
            'not_supported_in_saved_query', 'checks': {}, 'limitations': [], 'function_confirmed': False}


def audit_pair(lattice, item, ir):
    validate_ir(lattice, ir)
    readings, h = _readings(lattice, item)
    events = {s['sounding_event_id']: s for s in lattice['events']}
    direct = _result(item.get('query'), 'witness_exists')
    temporal = _result(item.get('temporal_query'), 'temporal_resolution_possible')
    row = {'version': VERSION, 'pair': deepcopy(item['pair']), 'local_context_span': deepcopy(item['local_context_span']),
           'parent_context_span': deepcopy(item['parent_context_span']), 'direct': direct, 'temporal': temporal,
           'diagnostics': {'sides': {}}, 'selected': None, 'function_confirmed': False, 'gate_changed': False,
           'global_voice_assignment': 'not_measured', 'confirmed_nct': False, 'accuracy_measured': False,
           'human_review': 'not_reviewed', 'gold_eligible': False, 'training_eligible': False}
    unsupported = []
    for sid, sound in events.items():
        a, b = f(sound['span']['start']), f(sound['span']['end'])
        left, right = f(item['local_context_span']['start']), f(item['local_context_span']['end'])
        if not (a < right and b > left or a == b and left <= a < right):
            continue
        try:
            pitch_identity(sound['pitch'])
        except (ValueError, KeyError, TypeError, ZeroDivisionError) as error:
            unsupported.append({'event_ref': sid, 'reason': str(error)})
        if f(sound['span']['end']) <= f(sound['span']['start']):
            unsupported.append({'event_ref': sid, 'reason': 'nonpositive_sound_duration'})
    if unsupported:
        row['unsupported_event_refs'] = unsupported
        for value in (direct, temporal):
            value['status'] = 'unsupported'
        return row
    # Parent identity is checked above, but a local witness cannot be blocked
    # by an unrelated earlier/later lane. Retain full metadata in the case.
    events = {sid: sound for sid, sound in events.items() if
              f(sound['span']['start']) < f(item['local_context_span']['end']) and
              f(sound['span']['end']) > f(item['local_context_span']['start'])}
    lanes = _lanes(events, ir)
    cut = f(readings[0]['span']['end'])
    roles = [LEAD] + ([SEVENTH] if len(h['chord']['members']) == 4 else [])
    for side, reading in zip(('source', 'target'), readings):
        observed = profile(events, reading)
        boundary, missing = _boundary(events, reading, cut, side == 'source')
        row['diagnostics']['sides'][side] = {'interval_profile': observed,
            'missing_boundary_members': deepcopy(missing), 'boundary_member_event_refs': boundary,
            'candidate_ref': reading['candidate_ref'], 'alternative_index': reading['alternative_index'],
            'first_member_observed_quarter': {key: q(max(f(reading['span']['start']),
                min(f(events[sid]['span']['start']) for sid in refs))) if refs else None
                for key, refs in observed['member_event_refs'].items()}}
        tq = item.get('temporal_query')
        if tq and side + '_profile' in tq and tq[side + '_profile'] != observed:
            raise ValueError('saved_profile_mismatch')
    dq = item.get('query')
    for query, value in ((dq, direct), (item.get('temporal_query'), temporal)):
        if value['status'] == 'conditional_witness_rechecked' and (query.get('family') != item['pair']['family'] or
                type(query.get('source_path_index')) is not int or type(query.get('target_path_index')) is not int or
                query.get('source_path_index') != 0 or query.get('target_path_index') != 1):
            raise ValueError('saved_positive_metadata_mismatch')
    if temporal['status'] == 'conditional_witness_rechecked' and item['temporal_query'].get('target_quality') != item['pair']['target_quality']:
        raise ValueError('saved_positive_metadata_mismatch')
    if direct['status'] == 'conditional_witness_rechecked':
        if any(r['abstention_reasons'] for r in readings):
            raise ValueError('witness_candidate_blocked')
        links = dq['links']; _joint_links(links, events, lanes)
        if not links or any(f(events[a]['span']['end']) != cut or f(events[b]['span']['start']) != cut for a, b in links):
            raise ValueError('direct_witness_not_at_cut')
        if set(dq['required_link_options']) != set(roles):
            raise ValueError('witness_role_mismatch')
        for tag in roles:
            if not any(link in dq['required_link_options'][tag] and _motion(tag, events[link[0]], events[link[1]], h, readings[1]) for link in links):
                raise ValueError('direct_witness_motion_mismatch')
        if len({tuple(link) for link in links}) != len(links) or any(not any(
                link in dq['required_link_options'][tag] and _motion(tag, events[link[0]], events[link[1]], h, readings[1])
                for tag in roles) for link in links):
            raise ValueError('direct_witness_noncritical_link')
        source_required = [h['leading_tone']]
        if len(h['chord']['members']) == 4:
            source_required.append(h['chord']['members'][3])
        else:
            source_required.append(h['chord']['root'] if item['pair']['family'] == 'V' else h['chord']['members'][2])
        for side, required in (('source', source_required), ('target', h['target']['members'][:2])):
            if any(not row['diagnostics']['sides'][side]['boundary_member_event_refs'][str(tuple(p))] for p in required):
                raise ValueError('direct_identity_prerequisite_missing')
        direct['checks'] = {'exact_ir_identity': True, 'same_explicit_lane': True, 'touching_at_cut': True,
                            'critical_motion': True, 'nonbranching_partial_matching': True}
        direct['limitations'] = ['full_membership_not_required', 'nonmembers_not_explained',
                                'not_actual_contrapuntal_voice', 'not_global_assignment']
        direct['selected_links'] = deepcopy(links)
    tq = item.get('temporal_query')
    if temporal['status'] == 'conditional_witness_rechecked':
        sides = row['diagnostics']['sides']
        if any(r['abstention_reasons'] for r in readings) or any(s['interval_profile']['missing_members'] or
                s['interval_profile']['silence_spans_quarters'] for s in sides.values()) or sides['source']['interval_profile']['unexplained_event_refs']:
            raise ValueError('temporal_identity_prerequisite_missing')
        witness = tq['witness']
        if len(witness) != len(roles) or {option['relation'] for option in witness} != set(roles):
            raise ValueError('witness_role_mismatch')
        edges = []; covered = set()
        for option in witness:
            tag = option['relation']; chain = option['carried_event_refs']; target = option['target_ref']
            if not chain or chain[0] != option['source_ref'] or any(sid not in events for sid in chain + [target]):
                raise ValueError('unknown_witness_event')
            expected = [list(e) for e in zip(chain, chain[1:] + [target])]
            if option['links'] != expected or option not in tq['required_path_options'][tag]:
                raise ValueError('temporal_chain_mismatch')
            a = events[chain[0]]; b = events[target]; at = f(b['span']['start'])
            if not f(a['span']['start']) < cut or f(a['span']['end']) <= f(readings[0]['span']['start']):
                raise ValueError('temporal_source_outside_interval')
            if not cut <= at < f(readings[1]['span']['end']) or f(option['arrival']) != at or option['delayed'] != (at > cut):
                raise ValueError('temporal_arrival_mismatch')
            if any(pitch_identity(events[sid]['pitch']) != pitch_identity(a['pitch']) for sid in chain):
                raise ValueError('temporal_carry_not_identical_pitch')
            if not _motion(tag, a, b, h, readings[1]):
                raise ValueError('temporal_witness_motion_mismatch')
            edges.extend(expected); covered.update(chain)
        _joint_links(edges, events, lanes)
        if not set(sides['target']['interval_profile']['unexplained_event_refs']) <= covered:
            raise ValueError('uncovered_temporal_target_nonmember')
        delayed = any(option['delayed'] for option in witness)
        if tq['has_delayed_arrival'] != delayed:
            raise ValueError('temporal_delayed_flag_mismatch')
        temporal.update(checks={'exact_ir_identity': True, 'complete_interval_membership': True,
            'same_pitch_carry': True, 'critical_motion': True, 'joint_paths': True,
            'all_target_nonmembers_carried': True}, has_delayed_arrival=delayed, selected_paths=deepcopy(witness),
            limitations=['not_actual_contrapuntal_voice', 'not_global_assignment'])
    used = {a for a, b in direct.get('selected_links', [])}
    row['diagnostics']['critical_source_events_not_in_direct_witness'] = sorted(sid for tag in roles
        for sid in row['diagnostics']['sides']['source']['boundary_member_event_refs'][
            str(tuple(h['leading_tone'] if tag == LEAD else h['chord']['members'][3]))] if sid not in used)
    row['diagnostics']['all_doubled_tendencies_resolved'] = 'not_measured'
    row['diagnostics']['diminished_fifth_resolution'] = 'not_measured'
    return row


def run(lattice, survey, ir):
    """Audit every exact-span competitor, retaining all original query indices."""
    out = {'version': VERSION, 'groups': [], 'inventory': [], 'summary': {}, 'survey_status': survey['status'],
           'selected': None, 'gate_changed': False, 'accuracy_measured': False, 'source_labels_used': False}
    results = survey.get('results', [])
    if survey['status'] == 'ready' and len(results) != len(survey['plan']['pairs']):
        raise ValueError('survey_incomplete')
    groups = defaultdict(list)
    for index, item in enumerate(results):
        if item['pair'] != survey['plan']['pairs'][index]:
            raise ValueError('pair_plan_mismatch')
        statuses = {name: item.get(field, {}).get('status') if item.get(field) else None
                    for name, field in (('direct', 'query'), ('temporal', 'temporal_query'))}
        out['inventory'].append({'query_index': index, 'pair': deepcopy(item['pair']), **statuses,
                                 'original_engine_status': item.get('status'),
                                 'unsupported_event_refs': deepcopy(item.get('unsupported_event_refs', []))})
        span = item['local_context_span']; cut = lattice['edges'][item['pair']['source']['edge']]['span']['end']
        groups[(f(span['start']), f(cut), f(span['end']))].append(index)
    counts = Counter()
    for key, indices in groups.items():
        positive = [i for i in indices if out['inventory'][i]['direct'] == 'witness_exists' or
                    out['inventory'][i]['temporal'] == 'temporal_resolution_possible']
        if not positive:
            continue
        audits = []
        for index in indices:
            row = audit_pair(lattice, results[index], ir); row['query_index'] = index; audits.append(row)
            for side in ('direct', 'temporal'):
                if row[side]['status'] == 'conditional_witness_rechecked':
                    counts[side + '_rechecked'] += 1
            if row['direct']['status'] == 'conditional_witness_rechecked':
                for side, value in row['diagnostics']['sides'].items():
                    if value['missing_boundary_members']: counts['direct_' + side + '_boundary_incomplete'] += 1
                    if value['interval_profile']['unexplained_event_refs']: counts['direct_' + side + '_nonmembers'] += 1
            if row['temporal'].get('has_delayed_arrival'): counts['actual_delayed_rechecked'] += 1
        out['groups'].append({'span': {'start': q(key[0]), 'cut': q(key[1]), 'end': q(key[2])},
            'query_indices': indices, 'positive_query_indices': positive,
            'control_query_indices': [i for i in indices if i not in positive], 'audits': audits,
            'control_scope': 'same exact source/cut/target intervals; not independently labelled negatives'})
    counts['supported_span_groups'] = len(out['groups'])
    counts['same_span_competing_queries'] = sum(len(g['control_query_indices']) for g in out['groups'])
    counts['inventoried_queries'] = len(out['inventory']); out['summary'] = dict(counts)
    return out
