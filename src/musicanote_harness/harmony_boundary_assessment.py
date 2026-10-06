"""Evidence-linked abstention; never turns geometric NCT candidates into truth."""
from copy import deepcopy
from .harmony_joint import f
from .harmony_path_contrast import token

VERSION = 'boundary-assessment-0.1.0'


def assess_support(profile, cells):
    """Distinguish late observation from no observation, without rejecting omissions."""
    rows = profile['cells']
    members = {tuple(m) for m in profile['members']}
    entry = {tuple(m) for m in rows[0]['present_members']} if rows else set()
    seen = set()
    first = []
    for row in rows:
        for member in sorted({tuple(m) for m in row['present_members']} - seen):
            first.append({'spelling': list(member), 'cell_index': row['cell_index'],
                          'first_observed_time': cells[row['cell_index']]['span']['start']})
            seen.add(member)
    unknown = any(not row['absence_certain_from_available_pitches'] for row in rows)
    status = ('unknown_pitch_limits_support' if unknown else
              'no_members_observed' if not seen else
              'partial_members_observed' if members - seen else
              'all_members_at_entry' if members <= entry else
              'all_members_observed_with_delay')
    return {'status': status, 'entry_members': [list(m) for m in sorted(entry)],
            'delayed_members': [list(m) for m in sorted(seen - entry)],
            'unobserved_members': [list(m) for m in sorted(members - seen)],
            'first_observations': first, 'absence_certain': not unknown,
            'arpeggiation_confirmed': False, 'candidate_rejected': False}


def observe(result, boundary_index):
    b = result['boundaries'][boundary_index]
    e = b.get('temporal_observations', {})
    out = {'version': VERSION, 'status': 'evidence_unavailable', 'selected': None,
           'ranking_performed': False, 'nct_confirmed': False, 'patterns': []}
    if result['status'] != 'ready' or b['status'] != 'ready' or e.get('status') != 'ready':
        return out
    profiles = {pid: assess_support(p, e['cells'])
                for pid, p in e['candidate_support_profiles'].items()}
    events = {s['sounding_event_id']: s for s in result['events']}
    for p in b.get('boundary_figures', {}).get('patterns', []):
        if p['kind'] != 'prepared_suspension_candidate':
            continue
        x, y = (events[sid] for sid in p['event_refs'])
        reasons = ['structural_bass_unconfirmed', 'preparation_consonance_unconfirmed',
                   'boundary_dissonance_unconfirmed', 'resolution_consonance_unconfirmed',
                   'accent_and_style_unconfirmed', 'harmonic_change_unconfirmed']
        if f(x['span']['end']) != f(y['span']['start']):
            reasons.append('resolution_not_contiguous')
        checkpoints = []
        for label, time, sid in [('preparation', x['span']['start'], p['affected_event_ref']),
                                 ('boundary', b['boundary'], p['affected_event_ref']),
                                 ('resolution', y['span']['start'], y['sounding_event_id'])]:
            idx = next((i for i, c in enumerate(e['cells']) if f(c['span']['start']) == f(time)), None)
            c = e['cells'][idx] if idx is not None else None
            checkpoints.append({'role': label, 'cell_index': idx,
                'event_ref': sid, 'intervals': [v for v in c['intervals_from_lowest'] if v['event_ref'] == sid] if c else [],
                'meter': deepcopy(c['meter']) if c else None})
            if c is None or c['bass_status'] != 'observed_lowest':
                reasons.append(label + '_lowest_pitch_unavailable')
        refs = {side: sorted({e['reading_profile_refs'][side][i] for i in p[side + '_reading_indices']})
                for side in ('left', 'right')}
        competing = {}
        for side, readings in [('hold', result['hold_readings']), ('right', b['right']['readings'])]:
            competing[side] = [i for i, r in enumerate(readings)
                if not r['condition']['abstention_reasons']
                and r['event_states'].get(p['affected_event_ref']) == 'member']
        out['patterns'].append({'assessment_id': 'assessment_' + token([VERSION, p['pattern_id']]),
            'pattern_ref': p['pattern_id'], 'status': 'abstain', 'abstention_reasons': reasons,
            'support_profile_refs': refs, 'checkpoints': checkpoints,
            'competing_member_reading_indices': competing,
            'supporting_assignment_refs': deepcopy(p['supporting_assignment_refs']),
            'confirmed': False, 'remove_note': False})
    out.update(status='ready', support_assessments=profiles,
        limits=['Delayed observation permits an arpeggiation hypothesis, not confirmation; omissions do not reject a chord.',
                'Competing member readings have different harmonic assumptions, not independent votes or corrections.',
                'Lowest sounding intervals and denominator position do not establish structural bass, consonance or accent.',
                'Prior conditional explanation totals remain unchanged; abstention is an additional assessment layer.'])
    return out


def augment(baseline):
    result = deepcopy(baseline)
    for i, b in enumerate(result['boundaries']):
        b['boundary_assessment'] = observe(result, i)
    result['boundary_assessment_version'] = VERSION
    return result
