"""Observed cross-cut motion for incomplete-chord alternatives.

Queries only critical-note motion and partial matching consistency. Neither a
contour return nor an existential matching explains all notes or selects harmony.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations, product
from .applied_chords import hypothesis, FAMILIES
from .seventh_context import chord
from .harmony_joint import f
from .harmony_catalog_resolution import pitch_pair
from .harmony_reading_voice_context import spelled_height
from .harmony_missing_evidence import validate_ir, overlap
from .harmony_distributed_resolution import joint_paths
from .harmony_incomplete_triads import run as incomplete

VERSION = 'omission-voice-context-0.1.0'


def geometry(lattice, ir, span, edge_budget=8192):
    if type(edge_budget) is not int or edge_budget < 1:
        raise ValueError('invalid_edge_budget')
    validate_ir(lattice, ir)
    notes = {n['note_id']: n for n in ir['note_events']}
    if len(notes) != len(ir['note_events']): raise ValueError('duplicate_note_id')
    events = {s['sounding_event_id']: s for s in lattice['events'] if overlap(s['span'], span)}
    lanes = {}; withheld = {}
    for sid, sound in events.items():
        ns = [notes.get(n) for n in sound['source_note_ids']]
        keys = {(n.get('part_id'), n.get('voice_id')) for n in ns if n}
        if f(sound['span']['end']) <= f(sound['span']['start']):
            withheld[sid] = 'nonpositive_timing'
        elif spelled_height(sound['pitch']) is None:
            withheld[sid] = 'pitch_unresolved'
        elif not ns or not all(ns) or len(keys) != 1 or not all(next(iter(keys))):
            withheld[sid] = 'lane_unresolved'
        else: lanes[sid] = next(iter(keys))
    base = {'span': deepcopy(span), 'event_refs': sorted(events),
            'withheld_events': withheld, 'uses_harmonic_labels': False, 'links': []}
    if withheld: return {**base, 'status': 'geometry_abstention'}
    links = []
    for x, a in sorted(events.items()):
        for y, b in sorted(events.items()):
            if lanes[x] == lanes[y] and f(a['span']['end']) == f(b['span']['start']):
                links.append([x, y])
                if len(links) > edge_budget:
                    return {**base, 'status': 'edge_budget_abstention', 'edge_budget': edge_budget}
    return {**base, 'status': 'ready', 'links': links,
            'lane_by_event': {sid: list(lane) for sid, lane in lanes.items()}}


def movement(events, x, y, kind='touching'):
    a, b = events[x], events[y]
    return {'source_ref': x, 'target_ref': y, 'kind': kind,
            'source_pitch': deepcopy(a['pitch']), 'target_pitch': deepcopy(b['pitch']),
            'diatonic_steps': spelled_height(b['pitch']) - spelled_height(a['pitch']),
            'semitones': b['pitch']['midi_pitch'] - a['pitch']['midi_pitch']}


def cut_movements(events, graph, cut):
    at = f(cut)
    held = [movement(events, sid, sid, 'held_sound') for sid, s in sorted(events.items())
            if f(s['span']['start']) < at < f(s['span']['end'])]
    touching = [movement(events, x, y) for x, y in graph['links']
                if f(events[y]['span']['start']) == at]
    return {'time': deepcopy(cut), 'held_sounds': held, 'touching_options': touching,
            'voice_assignment_selected': False}


def neighbor_returns(events, graph, cuts, budget=4096):
    """Exact step-out/step-back contours, including middle same-pitch reattacks."""
    if type(budget) is not int or budget < 1: raise ValueError('invalid_path_budget')
    first, second = map(f, cuts); outgoing = defaultdict(list)
    for x, y in graph['links']: outgoing[x].append(y)
    options = []; checks = 0
    for x, y in graph['links']:
        if f(events[y]['span']['start']) != first: continue
        m = movement(events, x, y)
        if (abs(m['diatonic_steps']) != 1 or abs(m['semitones']) not in (1, 2)
                or m['diatonic_steps'] * m['semitones'] <= 0): continue
        stack = [[x, y]]
        while stack:
            path = stack.pop(); middle = events[y]
            for dest in outgoing[path[-1]]:
                if checks >= budget:
                    return {'status': 'path_budget_abstention', 'options': [], 'checks': checks}
                checks += 1; d = events[dest]; at = f(d['span']['start'])
                if at > second: continue
                if at < second:
                    if pitch_pair(d['pitch']) == pitch_pair(middle['pitch']) and d['pitch']['midi_pitch'] == middle['pitch']['midi_pitch']:
                        stack.append(path + [dest])
                    continue
                if pitch_pair(d['pitch']) != pitch_pair(events[x]['pitch']) or d['pitch']['midi_pitch'] != events[x]['pitch']['midi_pitch']:
                    continue
                full = path + [dest]
                options.append({'event_refs': full, 'links': [list(e) for e in zip(full, full[1:])],
                                'direction': 'upper_neighbor_contour' if m['diatonic_steps'] == 1 else 'lower_neighbor_contour',
                                'carried_event_refs': [], 'confirmed_nct': False})
    return {'status': 'ready', 'options': options, 'checks': checks,
            'contour_is_nct_evidence_by_itself': False}


def constrain_neighbors(neighbors, bass_option, query_budget=4096, pair_budget=256):
    """Keep alternatives, but do not let contours steal a repeated-bass voice."""
    if type(pair_budget) is not int or pair_budget < 1: raise ValueError('invalid_pair_budget')
    if type(query_budget) is not int or query_budget < 1: raise ValueError('invalid_query_budget')
    out = deepcopy(neighbors); out['coexistence_queries'] = []
    if neighbors['status'] != 'ready': return out
    def constraint(option):
        # Do not embed a mutable option in its own query witness. Geometry
        # constraints carry no NCT coverage and no previously derived queries.
        return {'links': deepcopy(option['links']), 'carried_event_refs': []}
    for option in out['options']:
        option['bass_constrained_query'] = joint_paths(
            {'forced_bass': [constraint(bass_option)], 'contour': [constraint(option)]}, set(), query_budget)
    pairs = list(combinations(range(len(out['options'])), 2))
    if len(pairs) > pair_budget:
        out['coexistence_status'] = 'pair_budget_abstention_no_subset'
        out['planned_pair_count'] = len(pairs)
        return out
    for i, j in pairs:
        answer = joint_paths({'forced_bass': [constraint(bass_option)], 'one': [constraint(out['options'][i])],
                              'two': [constraint(out['options'][j])]}, set(), query_budget)
        out['coexistence_queries'].append({'option_indices': [i, j], 'query': answer})
    out['coexistence_status'] = 'audited'
    return out


def relation_options(events, graph, source, target, path_budget=4096):
    """Exact ordinary-family shapes; missing notes never become motion witnesses."""
    if type(path_budget) is not int or path_budget < 1: raise ValueError('invalid_path_budget')
    root = target['root_spelling']; relations = []
    if root is None or source['root_spelling'] is None: return relations
    outgoing = defaultdict(list)
    for x, y in graph['links']: outgoing[x].append(y)
    for quality in ('M', 'm'):
        core = chord(root, quality)['members']
        if not {tuple(p) for p in core} <= {tuple(p) for p in target['members']}: continue
        for family in FAMILIES:
            h = hypothesis(root, quality, family)
            if source['root_spelling'] != h['chord']['root'] or {tuple(p) for p in source['members']} != {tuple(p) for p in h['chord']['members']}: continue
            roles = {'leading_tone_to_target_root': h['leading_tone']}
            if len(h['chord']['members']) == 4: roles['seventh_down_step_to_target_member'] = h['chord']['members'][3]
            groups = {tag: [] for tag in roles}; checks = 0; exhausted = False
            cut, stop = f(source['span']['end']), f(target['span']['end'])
            for tag, pitch in roles.items():
                for sid, sound in sorted(events.items()):
                    if not overlap(sound['span'], source['span']) or pitch_pair(sound['pitch']) != pitch: continue
                    stack = [[sid]]
                    while stack and not exhausted:
                        chain = stack.pop()
                        for dest in outgoing[chain[-1]]:
                            if checks >= path_budget: exhausted = True; break
                            checks += 1; d = events[dest]; at = f(d['span']['start'])
                            if at >= stop: continue
                            m = movement(events, sid, dest)
                            if pitch_pair(d['pitch']) == pitch and m['semitones'] == 0:
                                stack.append(chain + [dest]); continue
                            if at < cut: continue
                            matches = (pitch_pair(d['pitch']) == root and m['semitones'] == 1 and m['diatonic_steps'] == 1) if tag.startswith('leading') else (
                                pitch_pair(d['pitch']) in target['members'] and m['semitones'] in (-1, -2) and m['diatonic_steps'] == -1)
                            if matches:
                                full = chain + [dest]
                                groups[tag].append({'relation': tag, 'event_refs': full,
                                    'links': [list(e) for e in zip(full, full[1:])], 'carried_event_refs': [],
                                    'arrival': deepcopy(d['span']['start']), 'delayed': at > cut})
            critical_moves = [movement(events, x, y) for x, y in graph['links']
                              if pitch_pair(events[x]['pitch']) in roles.values()
                              and overlap(events[x]['span'], source['span'])
                              and cut <= f(events[y]['span']['start']) < stop]
            observed_target = {tuple(pitch_pair(s['pitch'])) for s in events.values() if overlap(s['span'], target['span'])}
            relations.append({'family': family, 'target_quality': quality, 'target_root': deepcopy(root),
                'source_candidate_ref': source['candidate_ref'], 'target_candidate_ref': target['candidate_ref'],
                'target_root_and_third_observed': all(tuple(p) in observed_target for p in core[:2]),
                'required_path_options': groups if not exhausted else {},
                'observed_critical_departures': critical_moves, 'path_checks': checks,
                'status': 'path_budget_abstention' if exhausted else 'motion_options_recorded',
                'function_confirmed': False})
    return relations


def contextual_neighbors(options, readings, events):
    out = []
    for option in options:
        refs = option['event_refs']
        states = [pitch_pair(events[refs[0]]['pitch']) in readings[0]['members'],
                  all(pitch_pair(events[sid]['pitch']) in readings[1]['members'] for sid in refs[1:-1]),
                  pitch_pair(events[refs[-1]]['pitch']) in readings[2]['members']]
        out.append({'event_refs': deepcopy(refs), 'outer_member_and_middle_nonmember': states == [True, False, True],
                    'membership_sequence': states, 'confirmed_nct': False})
    return out


def augment_chain(lattice, chain, bass, ir, combination_budget=256, edge_budget=8192, path_budget=4096, query_budget=4096):
    for value in (combination_budget, query_budget):
        if type(value) is not int or value < 1: raise ValueError('invalid_comparison_budget')
    out = deepcopy(chain)
    if chain['status'] != 'ready': return out
    graph = geometry(lattice, ir, chain['span'], edge_budget)
    out['voice_geometry'] = graph
    events = {s['sounding_event_id']: s for s in lattice['events'] if s['sounding_event_id'] in graph['event_refs']}
    bass_option = {'links': [list(e) for e in zip(bass['event_refs'], bass['event_refs'][1:])], 'carried_event_refs': []}
    if graph['status'] == 'ready' and not {tuple(e) for e in bass_option['links']} <= {tuple(e) for e in graph['links']}:
        raise ValueError('bass_constraint_outside_geometry')
    cache = {}; neighbor_cache = {}
    for comp in out['comparisons']:
        audit = {'status': graph['status'], 'combinations': [], 'selected': None,
                 'full_voice_assignment_verified': False, 'nonmember_coverage_verified': False,
                 'quality_confirmed': False, 'omission_confirmed': False, 'pedal_confirmed': False,
                 'forced_bass_links': deepcopy(bass_option['links']), 'bass_nonmembers_explained': False}
        comp['voice_context_comparison'] = audit
        if graph['status'] != 'ready': continue
        audit['boundary_observations'] = [cut_movements(events, graph, t) for t in comp['cut_times']]
        key = tuple(comp['cut_indices'])
        neighbor_cache[key] = constrain_neighbors(neighbor_returns(events, graph, comp['cut_times'], path_budget),
                                                 bass_option, query_budget)
        audit['neighbor_return_geometry'] = neighbor_cache[key]
        # All pairwise shape diagnostics, including blocked and unsupported
        # omission competitors, are retained as factors, not preferred triples.
        refs = comp['interval_refs']; audit['pair_diagnostic_refs'] = []
        for left, right in zip(refs, refs[1:]):
            pair_key = left + ':' + right; audit['pair_diagnostic_refs'].append(pair_key)
            if pair_key in cache: continue
            rows = []
            for a in chain['interval_tables'][left]['readings']:
                for b in chain['interval_tables'][right]['readings']:
                    relations = relation_options(events, graph, {**a, 'span': chain['interval_tables'][left]['span']},
                                                 {**b, 'span': chain['interval_tables'][right]['span']}, path_budget)
                    if relations: rows.append({'source_reading': a['reading_index'], 'target_reading': b['reading_index'], 'relations': relations})
            cache[pair_key] = rows
        count = comp['omission_comparison']['combination_count']
        if count > combination_budget:
            audit.update(status='combination_budget_abstention_no_subset', planned_combinations=count); continue
        if not count: audit.update(status='no_eligible_conditional_triple'); continue
        for indices in product(*comp['omission_comparison']['reading_groups']):
            readings = [chain['interval_tables'][ref]['readings'][i] for ref, i in zip(refs, indices)]
            groups = {'forced_repeated_bass': [bass_option]}; relations = []
            blockers = sorted({b for r in readings for b in r['candidate_blockers']})
            reasons = []; uncertain = False
            for side, pair_key in enumerate(audit['pair_diagnostic_refs']):
                row = next((r for r in cache[pair_key] if (r['source_reading'], r['target_reading']) == indices[side:side+2]), None)
                for rel in row['relations'] if row else []:
                    relations.append({'side': side, **deepcopy(rel)})
                    if rel['status'] == 'path_budget_abstention': uncertain = True
                    if not rel['target_root_and_third_observed']: reasons.append('target_root_or_third_not_observed')
                    for tag, opts in rel['required_path_options'].items(): groups[str(side) + ':' + rel['family'] + ':' + tag] = opts
            answer = {'status': 'blocked_context', 'witness': None} if blockers else (
                {'status': 'path_budget_abstention', 'witness': None} if uncertain else (
                {'status': 'target_identity_abstention', 'witness': None} if reasons else (
                {'status': 'no_applicable_ordinary_resolution_relation', 'witness': None} if not relations else joint_paths(groups, set(), query_budget))))
            if answer['status'] == 'temporal_resolution_possible': answer['status'] = 'critical_motion_matching_possible'
            audit['combinations'].append({'reading_indices': list(indices), 'relations': relations,
                'blockers': blockers, 'reasons': reasons, 'critical_motion_query': answer,
                'neighbor_roles': contextual_neighbors(neighbor_cache[key]['options'], readings, events),
                'witness_is_preferred': False, 'function_confirmed': False})
        audit['status'] = 'audited'
    out['voice_pair_diagnostics'] = cache
    return out


def run(lattice, survey, ir):
    base = incomplete(lattice, survey, ir)
    out = {**base, 'version': VERSION, 'baseline_version': base['version'], 'baseline_summary': deepcopy(base.get('summary', {}))}
    if base['status'] != 'ready': return out
    basses = {c['chain_id']: c for c in base['geometry']['chains']}
    out['chain_comparisons'] = [augment_chain(lattice, c, basses[c['chain_ref']], ir) for c in base['chain_comparisons']]
    counts = Counter()
    for chain in out['chain_comparisons']:
        for comp in chain['comparisons']:
            audit = comp['voice_context_comparison']; counts['comparison:' + audit['status']] += 1
            for item in audit['combinations']: counts['critical:' + item['critical_motion_query']['status']] += 1
            options = audit.get('neighbor_return_geometry', {}).get('options', [])
            counts['neighbor_contour_options'] += len(options)
            for option in options:
                counts['neighbor_matching:' + option['bass_constrained_query']['status']] += 1
    out['summary'] = dict(counts)
    out['voice_context_limits'] = [
        'Only same explicit part/voice touching partial matchings; source XML voice is not proven contrapuntal identity.',
        'Both adjacent critical-motion requirements and the bass constraint share one matching; independent witnesses are not unioned.',
        'Forced bass and neighbor contour links explain no nonmembers, assign no NCTs and confirm no pedal.',
        'A contour return is descriptive; chord changes can contain the same shape. No harmonies or qualities are ranked.',
        'Missing notes are never path endpoints; omitted fifth stays an assumption, not observed resolution evidence.',
        'All same-interval reading competitors remain in interval tables and pair diagnostics; unsupported is not rejected.',
        'No score-wide optimization, cadence, key, independent accuracy or production/UI changes.']
    return out
