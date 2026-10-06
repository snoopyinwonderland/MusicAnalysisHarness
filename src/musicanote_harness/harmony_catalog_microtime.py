"""Attack/release anchored experiments, retaining delayed hypotheses as uncertain.

Denominator-beat windows are measurement windows, not detected harmonic spans.
No boundary, chord, voice matching, NCT or key is selected here.
"""
from copy import deepcopy
from fractions import Fraction
from .formal_ir import q
from .harmony_joint import f
from .harmony_candidate_catalog import propose
from .harmony_catalog_resolution import compare, pitch_pair
from .harmony_delayed_links import observe as delayed_links
from .harmony_link_counterevidence import assess as counterevidence

VERSION = 'catalog-microtime-0.1.0'


def plan(ir, span):
    a, b = f(span['start']), f(span['end'])
    if a < 0 or b <= a:
        raise ValueError('invalid_span')
    points = {}
    for s in ir['sounding_events']:
        for key in ('start', 'end'):
            t = f(s['span'][key])
            if a < t < b:
                points.setdefault(t, {'attack_refs': [], 'release_refs': []})[
                    'attack_refs' if key == 'start' else 'release_refs'].append(s['sounding_event_id'])
    windows, abstentions = [], []
    for t, refs in sorted(points.items()):
        meters = [m for m in ir['measures'] if f(m['global_start_quarter']) <= t
                  < f(m['global_start_quarter']) + f(m['actual_duration_quarter'])]
        denominators = {m.get('time_signature', {}).get('beat_type') for m in meters}
        if len(denominators) != 1 or None in denominators or next(iter(denominators)) <= 0:
            abstentions.append({'boundary': q(t), **refs, 'reason': 'missing_or_conflicting_meter'})
            continue
        unit = Fraction(4, next(iter(denominators)))
        windows.append({'boundary': q(t), 'unit_quarter': q(unit), **refs,
                        'left': {'start': q(max(a, t-unit)), 'end': q(t)},
                        'right': {'start': q(t), 'end': q(min(b, t+unit))},
                        'clipped_by_context': t-unit < a or t+unit > b})
    return {'version': VERSION, 'span': span, 'windows': windows, 'abstentions': abstentions,
            'policy': 'all sounding attacks/releases; one denominator beat each side; no harmony labels',
            'boundary_selected': False}


def arrival(edge):
    """Cumulative sightings and actual simultaneity are different observations."""
    sightings = {}
    cells = edge['target_time']['cells']
    for cell in cells:
        for role, refs in cell['required_role_refs'].items():
            if refs and role not in sightings:
                sightings[role] = {'time': cell['span']['start'], 'event_refs': list(refs)}
    complete = set(edge['target_time']['required_spellings']) <= sightings.keys()
    first_simultaneous = next((c['span']['start'] for c in cells if c['all_required_present']), None)
    return {'first_role_sightings': sightings,
            'cumulative_identity_time': max((v['time'] for v in sightings.values()), key=f) if complete else None,
            'first_simultaneous_identity_time': first_simultaneous,
            'identity_at_boundary': edge['target_identity_at_boundary'],
            'cumulative_is_sustained_chord': False, 'harmony_span_extended': False}


def enrich(ir, left, right):
    result = compare(ir, left, right)
    context = result['span']; boundary = f(left['span']['end'])
    observed = delayed_links(ir, [context])
    warnings = counterevidence(ir, observed, [context])
    audits = {(r['group_id'], tuple(r['source_refs'])): r for r in warnings['records']}
    candidates = [{c['candidate_id']: c for c in cat['candidates']} for cat in (left, right)]
    for edge in result['edges']:
        source = candidates[0][edge['source_candidate_ref']]
        target = candidates[1][edge['target_candidate_ref']]
        sa = source['spelling_alternatives'][edge['source_alternative_index']]
        ta = target['spelling_alternatives'][edge['target_alternative_index']]
        required = edge['source_time']['required_spellings']
        compatible = []
        for group in observed['groups']:
            for link in group['edges']:
                src, dst = link['source_refs']
                if not (f(link['source_span']['end']) <= boundary <= f(link['target_span']['start'])):
                    continue
                if source['event_states'].get(src) != 'member' or target['event_states'].get(dst) != 'member':
                    continue
                p1, p2 = pitch_pair(link['source_pitch']), pitch_pair(link['target_pitch'])
                if p1 not in sa['members'] or p2 not in ta['members']:
                    continue
                tags = []
                if p1 == required['leading_tone'] and p2 == edge['target_root'] and link['semitones'] == 1 and link['diatonic_steps'] == 1:
                    tags.append('leading_tone_endpoint_compatible')
                if p1 == required.get('seventh') and link['semitones'] in (-1, -2) and link['diatonic_steps'] == -1:
                    tags.append('seventh_endpoint_compatible')
                if tags:
                    compatible.append({'group_id': group['group_id'], 'source_refs': link['source_refs'],
                        'relations': tags, 'delay_quarters': link['delay_quarters'],
                        'source_pitch': link['source_pitch']['spelling'], 'target_pitch': link['target_pitch']['spelling'],
                        'audit': audits[(group['group_id'], tuple(link['source_refs']))],
                        'rest_refs': group['rest_refs'], 'rest_status': group['rest_status'],
                        'harmonic_context_blockers': edge['abstention_reasons'],
                        'eligible_as_direct_resolution': False, 'voice_connection_confirmed': False})
        edge['target_arrival'] = arrival(edge)
        edge['delayed_endpoint_hypotheses'] = compatible
        # Direct status deliberately stays byte-for-byte equivalent to compare().
    result.update(version=VERSION, direct_version=result['version'], delayed_observation=observed,
                  delayed_counterevidence=warnings,
                  microtime_limits=['No delayed relation changes direct status or confirms a voice.',
                    'All assignments and no-match alternatives remain in delayed_observation.',
                    'Cumulative root/third sightings need not form one sustained harmony.',
                    'One denominator beat is an audit radius, not inferred tactus or harmonic rhythm.'])
    return deepcopy(result)


def scan(ir, span):
    """Yield every planned window for bounded-memory serialization by callers."""
    for spec in plan(ir, span)['windows']:
        left, right = propose(ir, spec['left']), propose(ir, spec['right'])
        yield spec, left, right, enrich(ir, left, right)
