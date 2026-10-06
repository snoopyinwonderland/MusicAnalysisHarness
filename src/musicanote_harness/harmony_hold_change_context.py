"""Same-event hold/change diagnostics under one explicit partial assignment.

The bounded assignment universe contains neighbor-contour link unions, the
empty assignment, and optional repeated-bass constraints. It is NOT an exhaustive
contrapuntal analysis. Coverage is conditional evidence, never a ranking score.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import product
from math import prod
import json

from .formal_ir import q
from .harmony_joint import f
from .harmony_missing_evidence import overlap
from .harmony_omission_voice_context import run as voice_context, neighbor_returns
from .harmony_ornament_timeline import timeline
from .harmony_voice_paths import partition

VERSION = 'hold-change-shared-assignment-0.1.0'


def budget(value):
    if type(value) is not int or value < 1:
        raise ValueError('invalid_comparison_budget')


def sound_map(lattice):
    events = {s['sounding_event_id']: s for s in lattice['events']}
    if len(events) != len(lattice['events']):
        raise ValueError('duplicate_sound_id')
    return events


def spelled_pair(sound):
    """Do not int-cast microtonal alterations into a false ordinary spelling."""
    pitch = sound.get('pitch') or {}
    if pitch.get('step') not in 'C D E F G A B'.split() or pitch.get('alter') is None:
        return None
    alter = f(pitch['alter'])
    if alter.denominator != 1: return None
    return [pitch['step'], int(alter)]


def observations(events, reading):
    sounds = {sid: s for sid, s in events.items() if overlap(s['span'], reading['span'])}
    members = {tuple(p) for p in reading['members']}
    observed = {str(p): sorted(sid for sid, s in sounds.items() if spelled_pair(s) == list(p)) for p in sorted(members)}
    unresolved = sorted(sid for sid, s in sounds.items() if spelled_pair(s) is None)
    foreign = sorted(sid for sid, s in sounds.items() if spelled_pair(s) is not None and tuple(spelled_pair(s)) not in members)
    return {'member_event_refs': observed, 'missing_members': [list(p) for p in sorted(members) if not observed[str(p)]],
            'unexplained_event_refs': foreign, 'spelling_unresolved_event_refs': unresolved}


def assignments(events, graph, catalog, bass_links, assignment_budget=256):
    """All contour subsets, with AND without bass; retain a truly empty baseline."""
    budget(assignment_budget)
    base = {'assignments': [], 'conflicts': [], 'selected': None,
            'exhaustive_contrapuntal_assignments': False}
    if graph['status'] != 'ready' or catalog['status'] != 'ready':
        return {**base, 'status': 'geometry_or_catalog_abstention'}
    options = catalog['options']
    planned = 2 * (2 ** len(options))
    if planned > assignment_budget:
        return {**base, 'status': 'assignment_budget_abstention_no_subset',
                'planned_constraint_sets': planned}
    allowed = {tuple(e) for e in graph['links']}
    refs = set(graph['event_refs'])
    if not {tuple(e) for e in bass_links} <= allowed:
        raise ValueError('bass_constraint_outside_geometry')
    scoped = [events[sid] for sid in sorted(refs)]
    seen = {}
    for forced in (False, True):
        for flags in product((False, True), repeat=len(options)):
            indices = [i for i, flag in enumerate(flags) if flag]
            links = {tuple(e) for i in indices for e in options[i]['links']}
            if forced: links.update(tuple(e) for e in bass_links)
            if not links <= allowed: raise ValueError('contour_outside_geometry')
            origin = {'contour_indices': indices, 'bass_constraint_required': forced}
            try:
                tracks = partition(scoped, sorted(links))
            except ValueError as error:
                if str(error) != 'branch_or_merge_not_allowed': raise
                base['conflicts'].append({**origin, 'reason': str(error)})
                continue
            key = tuple(sorted(links))
            if key in seen:
                seen[key]['constraint_origins'].append(origin)
                continue
            aid = 'context_assignment_' + sha256(json.dumps({'events': sorted(refs), 'links': key}).encode()).hexdigest()[:16]
            row = {'assignment_id': aid, 'links': [list(e) for e in key],
                   'tracks': tracks, 'constraint_origins': [origin],
                   'is_empty_assignment': not links, 'preferred': False}
            seen[key] = row; base['assignments'].append(row)
    return {**base, 'status': 'ready', 'planned_constraint_sets': planned}


def validate_path(path, span):
    if not path or f(span['start']) >= f(span['end']): raise ValueError('invalid_comparison_span')
    cursor = f(span['start'])
    for reading in path:
        a, b = f(reading['span']['start']), f(reading['span']['end'])
        if a != cursor or b <= a: raise ValueError('path_gap_overlap_or_order')
        cursor = b
    if cursor != f(span['end']): raise ValueError('path_does_not_cover_comparison')


def cells(events, span, path):
    a, b = f(span['start']), f(span['end'])
    points = {a, b} | {f(r['span'][k]) for r in path for k in ('start', 'end')}
    for sound in events.values():
        if overlap(sound['span'], span):
            points.update((max(a, f(sound['span']['start'])), min(b, f(sound['span']['end']))))
    points = sorted(points)
    return [{'span': {'start': q(lo), 'end': q(hi)},
             'event_refs': sorted(sid for sid, s in events.items()
                                  if f(s['span']['start']) < hi and f(s['span']['end']) > lo)}
            for lo, hi in zip(points, points[1:])]


def member_state(sound, path):
    """Evaluate the FULL sound extent, not a clipped favorable endpoint."""
    if (f(sound['span']['start']) < f(path[0]['span']['start']) or
            f(sound['span']['end']) > f(path[-1]['span']['end'])):
        return None, ['external_harmonic_context_unassigned']
    pair = spelled_pair(sound)
    if pair is None: return None, ['spelling_unresolved_or_microtonal_model_unsupported']
    relevant = [r for r in path if overlap(r['span'], sound['span'])]
    reasons = sorted({reason for r in relevant for reason in r.get('candidate_blockers', [])})
    if reasons: return None, reasons
    states = {pair in r['members'] for r in relevant}
    return next(iter(states)) if len(states) == 1 else None, []


def reading_timeline(events, grid, path, assignment, catalog):
    links = {tuple(e) for e in assignment['links']}
    active = []; withheld = {}; roles = []
    for index, option in enumerate(catalog['options']):
        pid = 'neighbor_context_' + str(index)
        if not {tuple(e) for e in option['links']} <= links:
            roles.append({'pattern_id': pid, 'status': 'links_not_in_shared_assignment'})
            continue
        refs = option['event_refs']
        states = []; reasons = []
        for sid in refs:
            state, why = member_state(events[sid], path)
            states.append(state); reasons.extend(why)
        expected = [True] + [False] * (len(refs) - 2) + [True]
        status = 'withheld' if reasons else 'conditional_neighbor' if states == expected else 'not_neighbor_under_this_harmony'
        roles.append({'pattern_id': pid, 'event_refs': deepcopy(refs),
                      'membership_sequence': states, 'status': status,
                      'reasons': sorted(set(reasons)), 'confirmed_nct': False})
        # A known member or mixed membership cannot become NCT on another cell.
        # Withheld coverage is only display provenance, never a licensed claim.
        if status not in ('withheld', 'conditional_neighbor'): continue
        for sid in refs[1:-1]:
            active.append({'pattern_id': pid, 'affected_event_ref': sid,
                           'nonmember_span': deepcopy(events[sid]['span'])})
        if reasons: withheld[pid] = sorted(set(reasons))
    items = []; total = Fraction()
    for cell in grid:
        lo, hi = f(cell['span']['start']), f(cell['span']['end'])
        reading = next(r for r in path if f(r['span']['start']) <= lo and hi <= f(r['span']['end']))
        for sid in cell['event_refs']:
            sound = events[sid]
            pair = spelled_pair(sound)
            bucket = 'spelling_unresolved' if pair is None else 'member' if pair in reading['members'] else 'unexplained_nonmember'
            items.append({'event_ref': sid, 'span': deepcopy(cell['span']), 'bucket': bucket})
            total += hi - lo
    result = timeline(grid, {'items': items, 'total_note_time': q(total)}, active, withheld)
    result['neighbor_roles'] = roles
    result['candidate_profiles'] = [
        {'candidate_ref': r['candidate_ref'], 'alternative_index': r['alternative_index'],
         'span': deepcopy(r['span']), 'members': deepcopy(r['members']),
         'candidate_blockers': deepcopy(r.get('candidate_blockers', [])),
         'observations': observations(events, r)} for r in path]
    return result


def compare(lattice, graph, span, hold, path, assignment, catalog):
    """No automatic path selection: one explicit, identical assignment per side."""
    events = sound_map(lattice)
    validate_path([hold], span); validate_path(path, span)
    if graph['status'] != 'ready' or catalog['status'] != 'ready': raise ValueError('geometry_not_ready')
    scoped = [events[sid] for sid in graph['event_refs']]
    if not {sid for sid, s in events.items() if overlap(s['span'], span)} <= set(graph['event_refs']):
        raise ValueError('geometry_event_loss')
    if not {tuple(e) for e in assignment['links']} <= {tuple(e) for e in graph['links']}:
        raise ValueError('assignment_outside_geometry')
    tracks = partition(scoped, assignment['links'])
    grid = cells(events, span, path)
    one = reading_timeline(events, grid, [hold], assignment, catalog)
    many = reading_timeline(events, grid, path, assignment, catalog)
    if one['total_note_time'] != many['total_note_time']: raise ValueError('unequal_note_time')
    return {'version': VERSION, 'span': deepcopy(span), 'shared_cells': grid,
            'assignment_id': assignment['assignment_id'], 'shared_links': deepcopy(assignment['links']),
            'shared_tracks': tracks, 'hold': one, 'change': many, 'preferred': None,
            'harmonic_change_confirmed': False, 'pedal_confirmed': False,
            'full_counterpoint_identified': False, 'source_labels_used': False}


def augment_chain(lattice, chain, comparison_budget=2048, assignment_budget=256):
    """Replay the already-eligible triples; other path factors remain unchanged."""
    budget(comparison_budget); budget(assignment_budget)
    out = deepcopy(chain)
    if chain['status'] != 'ready': return out
    graph = chain['voice_geometry']; events = sound_map(lattice)
    whole = chain['interval_tables'][chain['whole_interval_ref']]
    counts = Counter()
    for index, comp in enumerate(out['comparisons']):
        info = {'comparisons': [], 'selected': None,
                'path_scope': 'existing_conditional_return_triples_only_not_all_harmonic_paths',
                'other_path_factors_retained': True, 'invariance_checks': 0}
        comp['hold_change_context'] = info
        if graph['status'] != 'ready': info['status'] = 'geometry_abstention'; continue
        catalog = neighbor_returns(events, graph, comp['cut_times'])
        aset = assignments(events, graph, catalog, comp['voice_context_comparison']['forced_bass_links'], assignment_budget)
        info['neighbor_catalog'] = catalog; info['assignment_set'] = aset
        if aset['status'] != 'ready': info['status'] = aset['status']; continue
        groups = comp['omission_comparison']['reading_groups']
        combinations = prod(len(group) for group in groups)
        if len(groups) != 3 or combinations != comp['omission_comparison']['combination_count']:
            raise ValueError('conditional_combination_count_mismatch')
        planned = len(whole['readings']) * len(aset['assignments']) * combinations
        info['planned_comparisons'] = planned
        if planned > comparison_budget:
            info['status'] = 'comparison_budget_abstention_no_subset'; continue
        if not all(groups): info['status'] = 'no_eligible_conditional_triple'; continue
        for hold_index, hold_row in enumerate(whole['readings']):
            hold = {**hold_row, 'span': whole['span']}
            for assignment in aset['assignments']:
                # The same fixed harmony on either partition must produce the
                # same conditional note-time, including true no-link contexts.
                neutral = [{**hold, 'span': chain['interval_tables'][ref]['span']}
                           for ref in comp['interval_refs']]
                check = compare(lattice, graph, chain['span'], hold, neutral, assignment, catalog)
                for field in ('items', 'cells', 'note_time', 'wall_time', 'neighbor_roles'):
                    if check['hold'][field] != check['change'][field]: raise ValueError('same_harmony_partition_invariance_failed')
                info['invariance_checks'] += 1
                for indices in product(*groups):
                    path = [{**chain['interval_tables'][ref]['readings'][i],
                             'span': chain['interval_tables'][ref]['span']}
                            for ref, i in zip(comp['interval_refs'], indices)]
                    answer = compare(lattice, graph, chain['span'], hold, path, assignment, catalog)
                    answer.update(hold_reading_index=hold_index, change_reading_indices=list(indices),
                                  assumption_refs=[{'interval_ref': ref, 'reading_index': i}
                                                   for ref, i in zip(comp['interval_refs'], indices)
                                                   if i in comp['omission_comparison']['assumption_reading_groups'][comp['interval_refs'].index(ref)]])
                    info['comparisons'].append(answer)
        info['status'] = 'audited'
        counts['comparisons'] += len(info['comparisons']); counts['same_harmony_invariance_checks'] += info['invariance_checks']
        counts['empty_assignment_comparisons'] += sum(not c['shared_links'] for c in info['comparisons'])
    out['hold_change_summary'] = dict(counts)
    return out


def run(lattice, survey, ir):
    base = voice_context(lattice, survey, ir)
    out = {**base, 'version': VERSION, 'baseline_version': base['version'],
           'baseline_summary': deepcopy(base.get('summary', {}))}
    if base['status'] != 'ready': return out
    out['chain_comparisons'] = [augment_chain(lattice, c) for c in base['chain_comparisons']]
    counts = Counter()
    for chain in out['chain_comparisons']:
        counts.update(chain.get('hold_change_summary', {}))
        for comp in chain['comparisons']:
            counts['partition:' + comp['hold_change_context']['status']] += 1
    out['summary'] = dict(counts)
    out['hold_change_limits'] = [
        'Same rational cells, all sounding events and one identical assignment per comparison; no favorable witness union.',
        'Conditional neighbors only; passing, suspension, double-neighbor, pedal and long-range NCT remain unsupported here.',
        'Full outer and middle sound extents require harmonic coverage; clipped external membership is withheld.',
        'Assignment universe is bounded contour subsets with and without bass, not all possible contrapuntal voices.',
        'Only pre-existing eligible return triples are replayed; all other interval factors remain visible but uncomputed.',
        'Missing constituents and candidate blockers remain explicit; no coverage winner, quality, omission, key, cadence or accuracy claim.',
        'No Canonical Core, source annotation, production or UI promotion.']
    return out
